"""Installed deterministic reconstruction; no model, downloader or old-run retry."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

from asof.ingest import peak_memory_bytes
from asof.journal import RunJournal
from asof.serde import canonical, encode, fingerprint, parse_json
from asof.study.source_fact_sources import compile_reference, verify_reference
from asof.study.stable_read import checked_path, deadline_check

from .authority_v1 import load_authority, need, read_descriptor, sha
from .baseline_v1 import literal_report
from .controls_v1 import (evaluate_control, fact_accounting, generate_control,
                          prepare_controls, project_decision, reference_counts, report_exactness)
from .policy_v1 import policy_session

METHOD = "p09.source_inclusive_reconstruction.v1"
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")


def save(root, relative, value, *, raw=False):
    payload = value if raw else canonical(value) + b"\n"
    need(type(payload) is bytes and len(payload) <= 64 * 1024**2, "Retained product exceeds 64 MiB")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        remaining = memoryview(payload)
        while remaining:
            count = stream.write(remaining)
            need(count is not None and count > 0, "Retained product write made no progress")
            remaining = remaining[count:]
        stream.flush()
        __import__("os").fsync(stream.fileno())
    retained = path.read_bytes()
    need(retained == payload, "Retained bytes differ from the generated product")
    return dict(path=relative, sha256=sha(retained), bytes=len(retained))


def inventory(root, *, exclude=()):
    return {p.relative_to(root).as_posix(): dict(path=p.relative_to(root).as_posix(),
        sha256=sha(p.read_bytes()), bytes=p.stat().st_size) for p in sorted(root.rglob("*"))
        if p.is_file() and p.relative_to(root).as_posix() not in exclude}


def reference_projection(document):
    value = deepcopy(encode(document))
    del value["method"]["catalog_sha256"]
    return fingerprint(value)


def control_descriptor(scenario):
    snapshot = encode(scenario.evaluation_snapshot)
    snapshot["raw_root"] = None
    return dict(scenario_id=scenario.scenario_id, case=encode(scenario.case), task=encode(scenario.task),
        snapshot=snapshot, catalog=encode(scenario.catalog),
        originals_root="fictional/" + scenario.scenario_id + "/originals",
        original_source_anchors=encode(scenario.original_source_anchors))


def stage_passes(exact, schema="pass"):
    return {**{name: dict(status="pass", reason=None, error_class=None) for name in ("G0", "G1", "G2", "G3")},
            "G4": dict(status="pass" if exact else "rejected", schema_status=schema,
                       reason=None if exact else "not_complete_exact_report", error_class=None)}


def scored_output(cell_id, case_id, arm, stratum, raw, score, exact, accounting, source_admitted):
    return dict(cell_id=cell_id, case_id=case_id, arm=arm, stratum=stratum,
        terminal=score["terminal"] if score is not None else "returned",
        received_terminal="returned", raw_path="raw/" + cell_id + ".json", raw_sha256=sha(raw), raw_bytes=len(raw),
        core_score=encode(score) if score is not None else None, fact_accounting=accounting,
        full_source_admitted=source_admitted, full_verified_exact=bool(source_admitted and exact),
        strict_exact_report=exact)


def analysis_counts(outputs, decisions):
    literal = [x for x in outputs if x["cell_id"].startswith("N-L-")]
    abstain = [x for x in outputs if x["cell_id"].startswith("N-A-")]
    def errors(rows):
        return sum(len(x["core_score"]["critical_errors"]) for x in rows if x["core_score"] is not None)
    available = dict(identity_requested=0, identity_answerable=0, measurement_requested=0,
                     measurement_answerable=0, native_nulls=0, absent=0, empty=0)
    for cell in literal:
        families = cell["fact_accounting"]["families"]
        for name, prefix in (("identity_linkage", "identity"), ("reported_measurement", "measurement")):
            available[prefix + "_requested"] += families[name]["requested"]
            available[prefix + "_answerable"] += families[name]["answerable"]
        for row in families.values():
            reasons = row["expected_unknown_by_reason"]
            available["native_nulls"] += reasons.get("null_source_value", 0)
            available["absent"] += reasons.get("field_not_in_schema", 0)
            available["empty"] += reasons.get("empty_source_value", 0)
    controls = [d for d in decisions if d["decision_id"].startswith("D-S-")]
    invalid = {p: sum(d["policy"] == p and d["decision_id"].startswith("D-S-F") and d["verdict"] == "admitted"
                      for d in controls) for p in POLICIES}
    valid = {p: sum(d["policy"] == p and d["decision_id"].startswith("D-S-C") and d["verdict"] == "rejected"
                    for d in controls) for p in POLICIES}
    pairs = {}
    for left, right in (("FULL", "WITHOUT_WRAPPER"), ("FULL", "WIRE_ONLY"), ("WITHOUT_WRAPPER", "WIRE_ONLY")):
        l = {d["decision_id"].removesuffix("-" + left): d["verdict"] for d in controls if d["policy"] == left}
        r = {d["decision_id"].removesuffix("-" + right): d["verdict"] for d in controls if d["policy"] == right}
        need(set(l) == set(r), "Paired policy inventory differs")
        pairs[left + "__" + right] = sum(l[k] != r[k] for k in l)
    return dict(planned_output_cells=len(outputs), planned_decisions=len(decisions),
        output_terminal_counts=dict(Counter(x["terminal"] for x in outputs)),
        decision_verdict_counts=dict(Counter(d["verdict"] for d in decisions)),
        core_scored_outputs=sum(x["core_score"] is not None for x in outputs),
        native_literal=dict(cases=len(literal), verified_exact=sum(x["full_verified_exact"] for x in literal),
            **{"complete_" + t: sum(x["core_score"]["primary"]["passes"][t] is True for x in literal) for t in ("60", "80", "100")},
            critical_errors=errors(literal)),
        native_abstain=dict(cases=len(abstain), completion_80=sum(x["core_score"]["completion"] for x in abstain),
            emitted_facts=sum(x["core_score"]["emitted_facts"] for x in abstain), critical_errors=errors(abstain)),
        native_availability=available, controls=dict(scenarios=len(controls) // 3, valid=4, invalid=10,
            invalid_admissions=invalid, valid_rejections=valid), paired_control_discordance=pairs)


def compare_bridge(bridge, policy_sha, outputs, decisions, guards, references):
    need(bridge.get("method") == "p09.p05_comparison_bridge.v1" and bridge.get("role") == "evaluation_only"
         and bridge.get("agent_visible") is False and bridge["source_policy_sha256"] == policy_sha,
         "Evaluator bridge role/source-policy authority differs")
    need(len(outputs) == len(bridge["outputs"]) == 38 and len(decisions) == len(bridge["decisions"]) == 90,
         "Complete historical output/decision schedule required")
    expected_outputs = ["N-" + arm + "-p05-" + f"{i:02d}" for i in range(1, 13) for arm in ("L", "A")]
    expected_outputs += ["S-" + key for key in [*("C" + f"{i:02d}" for i in range(1, 5)), *("F" + f"{i:02d}" for i in range(1, 11))]]
    expected_decisions = ["D-" + cell + "-" + policy for cell in expected_outputs
                          for policy in (("FULL",) if cell.startswith("N-A-") else POLICIES)]
    need([x["cell_id"] for x in outputs] == [x["cell_id"] for x in bridge["outputs"]] == expected_outputs,
         "Independent unique complete output schedule differs")
    need([x["decision_id"] for x in decisions] == [x["decision_id"] for x in bridge["decisions"]] == expected_decisions,
         "Independent unique complete decision schedule differs")
    for actual, expected in zip(outputs, bridge["outputs"]):
        projected = {key: actual[key] for key in expected}
        if projected["core_score"] is not None:
            projected["core_score"] = deepcopy(projected["core_score"])
            del projected["core_score"]["reference_sha256"]
        need(canonical(projected) == canonical(expected), "Historical output/score projection differs: " + actual["cell_id"])
    for actual, expected in zip(decisions, bridge["decisions"]):
        need(canonical({k: actual[k] for k in expected}) == canonical(expected),
             "Historical policy decision differs: " + actual["decision_id"])
    actual_guards = {cid: {s: {k: v for k, v in outcome.items() if k in ("status", "schema_status")}
                          for s, outcome in stages.items()} for cid, stages in guards.items()}
    need(canonical(actual_guards) == canonical(bridge["guards"]), "Historical guard statuses differ")
    need(set(references) == set(bridge["native"]), "Full native reference inventory required")
    for cid, reference in references.items():
        prior = bridge["native"][cid]
        need(reference["projection_sha256"] == prior["reference_projection_sha256"],
             "Catalog-only reference projection differs: " + cid)
        need(reference["task_sha256"] == prior["task_sha256"] == prior["counts"]["task_sha256"] and
             prior["counts"]["case_id"] == cid and prior["counts"]["disposition"] == "compiled" and
             prior["counts"]["reference_sha256"] == prior["historical_reference_sha256"],
             "Historical native task/disposition bindings contradict each other: " + cid)
        count_keys = ("requested_facts", "measurement_answerable_facts", "measurement_answerable_groups")
        need(set(reference["counts"]) == set(count_keys) and
             canonical(reference["counts"]) == canonical({key: prior["counts"][key] for key in count_keys}),
             "Native answerable/requested count differs: " + cid)
    need(canonical(analysis_counts(outputs, decisions)) == canonical(analysis_counts(bridge["outputs"], bridge["decisions"])),
         "Historical complete descriptive count projection differs")


def reconstruct(authority, bundle_root, originals_root, output, journal, deadline):
    protocol = authority["document"]
    policy = parse_json(read_descriptor(bundle_root, protocol["source_policy"], deadline))
    outputs, decisions, guards, refs, native_docs, raw_outputs = [], [], {}, {}, {}, {}
    journal.append("build_stage", stage="complete_original_admission")
    def checkpoint():
        deadline_check(deadline)
        peak = peak_memory_bytes()
        limits = protocol["limits"]
        need(peak is None or peak <= limits["memory_bytes"], "Process peak exceeds reconstruction budget")
        need(sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) <= limits["output_bytes"],
             "Reconstruction output exceeds budget; no truncation")
    def progress(event, **details):
        checkpoint()
        journal.append("build_progress", stage="source_policy", source_event=event, **details)
    with policy_session(policy, originals_root, deadline, progress=progress) as session:
        coverage = {k: encode(session[k]) for k in ("source_proofs", "coverage", "dispositions", "resources")}
        save(output, "source-coverage.json", coverage)
        need(all(d["status"] == "ready_for_base_compile" for d in session["dispositions"].values()),
             "Fixed native case is blocked; retain coverage without replacement")
        journal.append("build_stage", stage="source_only_generation")
        for case in session["cases"]:
            checkpoint()
            cid = case["case_id"]
            for arm in ("L", "A"):
                cell_id = "N-" + arm + "-" + cid
                raw = literal_report(session["tasks"][cid], session["snapshot"], session["groups"][cid], always_abstain=arm == "A")
                save(output, "raw/" + cell_id + ".json", raw, raw=True)
                raw_outputs[cell_id] = raw
                journal.append("output_retained", cell_id=cell_id, raw_sha256=sha(raw), calls=0)
        scenarios = prepare_controls(output / "fictional", deadline)
        descriptors = {key: control_descriptor(s) for key, s in scenarios.items()}
        expected_controls = parse_json(read_descriptor(bundle_root, protocol["controls"], deadline))
        need(canonical(descriptors) == canonical(expected_controls), "Constructed source/config recipe differs from frozen descriptor")
        save(output, "control-descriptors.json", descriptors)
        for scenario in scenarios.values():
            checkpoint()
            raw = generate_control(scenario, deadline)
            save(output, "raw/" + scenario.cell_id + ".json", raw, raw=True)
            raw_outputs[scenario.cell_id] = raw
            journal.append("output_retained", cell_id=scenario.cell_id, raw_sha256=sha(raw), calls=0)
        journal.append("build_stage", stage="source_inclusive_reference_replay")
        for case in session["cases"]:
            checkpoint()
            cid = case["case_id"]
            task = session["tasks"][cid]
            compiled = compile_reference(task, session["snapshot"], originals_root, session["catalog"],
                deadline=deadline, approved_raw_root=originals_root)
            ref = verify_reference(encode(compiled.document), compiled.fingerprint, task, session["snapshot"],
                originals_root, session["catalog"], deadline=deadline, approved_raw_root=originals_root)
            desc = save(output, "references/" + cid + ".json", encode(ref.document))
            refs[cid] = dict(path=desc["path"], fingerprint=ref.fingerprint, projection_sha256=reference_projection(ref.document),
                task_sha256=ref.document["task_sha256"], counts=reference_counts(ref))
            native_docs[cid] = ref
        # Seal all reconstructed bytes before parsing any historical comparator.
        seal = dict(schema_version=1, method="p09.reconstructed_output_seal.v1",
            protocol_sha256=authority["byte_sha256"], files=inventory(output, exclude=("journal.jsonl",)),
            journal_prefix_sha256=journal.events[-1]["sha256"],
            comparison_inputs_parsed=False, model_calls=0, scientific_validation="not_established")
        seal_desc = save(output, "output-seal.json", seal)
        journal.append("outputs_sealed", output_seal_sha256=seal_desc["sha256"])
        journal.append("comparison_started", comparison_sha256=protocol["comparison"]["sha256"])
        bridge = parse_json(read_descriptor(bundle_root, protocol["comparison"], deadline))
        for case in session["cases"]:
            cid = case["case_id"]
            for arm in ("L", "A"):
                cell_id = "N-" + arm + "-" + cid
                raw = read_descriptor(output, seal["files"]["raw/" + cell_id + ".json"], deadline, maximum=524288)
                need(raw == raw_outputs[cell_id], "Sealed native bytes differ from generated source report")
                ref = native_docs[cid]
                exact, score = report_exactness(ref, raw, cell_id=cell_id)
                guards[cell_id] = stage_passes(exact)
                outputs.append(scored_output(cell_id, cid, arm, "native",
                    raw, score, exact, fact_accounting(ref, raw), True))
                for name in POLICIES if arm == "L" else ("FULL",):
                    decisions.append(project_decision(guards[cell_id], name, decision_id="D-" + cell_id + "-" + name))
        for scenario in scenarios.values():
            cell_id = scenario.cell_id
            raw = read_descriptor(output, seal["files"]["raw/" + cell_id + ".json"], deadline, maximum=524288)
            need(raw == raw_outputs[cell_id], "Sealed control bytes differ from generated report")
            result = evaluate_control(scenario, raw, deadline)
            guards[cell_id] = result["stages"]
            admitted = all(result["stages"][k]["status"] == "pass" for k in ("G0", "G1", "G2", "G3"))
            exact = result["stages"]["G4"]["status"] == "pass" if result["score"] is not None else None
            cell = scored_output(cell_id, scenario.scenario_id, "fixture", "fictional_json_core", raw, result["score"], exact,
                                 result["fact_accounting"], admitted)
            cell["terminal"] = result["raw_terminal"]
            outputs.append(cell)
            decisions.extend(result["decisions"])
        compare_bridge(bridge, protocol["source_policy"]["sha256"], outputs, decisions, guards, refs)
        checkpoint()
        counts = analysis_counts(outputs, decisions)
        resources = encode(session["resources"])
    deadline_check(deadline)
    return dict(schema_version=1, method=METHOD, status="COMPLETED_PENDING_AUDIT",
        protocol_sha256=authority["byte_sha256"], output_seal_sha256=seal_desc["sha256"],
        output_cells=outputs, decision_cells=decisions, guards=guards, native_references=refs,
        source_coverage_path="source-coverage.json", analysis_counts=counts, resources=resources,
        historical_output_comparison="all_38_exact_byte_hashes_and_all_90_decisions",
        historical_archive_integrity="not_provided_by_public_reconstruction",
        scientific_validation="not_established", model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("reconstruct", "audit"))
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--originals-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reconstruction-root", type=Path)
    args = parser.parse_args(argv)
    started, cpu = time.monotonic(), time.process_time()
    output = args.output.absolute()
    forbidden_outputs = [args.bundle_root.absolute().resolve(), args.originals_root.absolute().resolve()]
    if args.reconstruction_root is not None:
        forbidden_outputs.append(args.reconstruction_root.absolute().resolve())
    need(not any(output.resolve().is_relative_to(parent) for parent in forbidden_outputs),
         "Output must be separate from read-only bundle/original/reconstruction roots")
    journal = RunJournal(output, kind="build")
    stage, closed = "protocol_admission", False
    try:
        deadline = started + 3600
        authority = load_authority(args.protocol, args.protocol_sha256, args.bundle_root.absolute(), deadline)
        need(authority["document"]["limits"]["seconds"] <= 3600, "Protocol time cap exceeds public operation limit")
        deadline = min(deadline, started + authority["document"]["limits"]["seconds"])
        journal.append("protocol_admitted", protocol_sha256=authority["byte_sha256"], operation=args.operation)
        stage = args.operation
        if args.operation == "reconstruct":
            report = reconstruct(authority, args.bundle_root.absolute(), args.originals_root.absolute(), output, journal, deadline)
            report_name = "reconstruction.json"
        else:
            need(args.reconstruction_root is not None, "Audit needs an explicit completed reconstruction")
            from .audit_v1 import audit_reconstruction
            report = audit_reconstruction(authority, args.bundle_root.absolute(), args.originals_root.absolute(),
                                          args.reconstruction_root.absolute(), deadline)
            report_name = "audit.json"
        report["operation_resources"] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu,
            checkpoint_process_lifetime_peak_bytes=peak_memory_bytes(), physical_io_bytes=None, platform_cost_usd=None)
        report_desc = save(output, report_name, report)
        success = args.operation == "reconstruct" or report["status"] == "PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT"
        event = "reconstruction_completed" if args.operation == "reconstruct" else "audit_completed" if success else "audit_failed"
        journal.append(event, report_sha256=report_desc["sha256"])
        # Close inside the protected path before a qualified receipt exists.
        journal.close()
        closed = True
        files = inventory(output)
        receipt = dict(schema_version=1, method="p09.reconstruction_receipt.v1", operation=args.operation,
            status="SEALED_SUCCESS" if success else "SEALED_FAILED_AUDIT",
            protocol_sha256=authority["byte_sha256"], files=files,
            output_seal_sha256=report.get("output_seal_sha256"), reconstruction_sha256=report_desc["sha256"] if args.operation == "reconstruct" else None)
        save(output, "receipt.json", receipt)
        print(canonical(dict(status=report["status"], output=str(output), report_sha256=report_desc["sha256"],
                             receipt_sha256=sha((output / "receipt.json").read_bytes()))).decode())
        return 0 if success else 1
    except BaseException as error:
        recording_errors = []
        try:
            journal.fail(error, stage)
        except BaseException as recording_error:
            recording_errors.append(type(recording_error).__name__)
        try:
            save(output, "failure.json", dict(stage=stage, error_class=type(error).__name__, reason=str(error)[:600],
                 journal_failure_recording_errors=recording_errors, no_automatic_retry=True,
                 model_calls=0, scientifically_validated=False))
        except BaseException:
            pass  # An unwritable filesystem can prevent new evidence; old fsynced events remain.
        if isinstance(error, KeyboardInterrupt):
            raise
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 1
    finally:
        if not closed:
            try:
                journal.close()
            except BaseException:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
