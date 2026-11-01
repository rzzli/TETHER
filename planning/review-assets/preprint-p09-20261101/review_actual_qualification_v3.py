"""Sealed-output metadata review only; no source replay or provider file access."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import time

ROOT = Path(__file__).resolve().parents[3]
SEALED_ROOT = ROOT / "data/derived/preprint-p09-installed-20261101T205500Z"
ARCHIVE = SEALED_ROOT / "revision2"
READY = "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529"
COMPARISON = "1fc123d3c368d355c1f3d66a76eeaacea9ae954c6a6fad9aa3d05390d225cce0"
CASES = tuple(f"p05-{n:02d}" for n in range(1, 13))
CONTROLS = tuple([f"C{n:02d}" for n in range(1, 5)] + [f"F{n:02d}" for n in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run():
    started = time.monotonic()
    checks, findings = [], []
    byte_count = 0

    def need(name, condition):
        checks.append(dict(check=name, passed=bool(condition)))
        if not condition: findings.append(name)

    def read(path):
        nonlocal byte_count
        need("sealed_archive_read_boundary", path.resolve().is_relative_to(SEALED_ROOT.resolve()))
        raw = path.read_bytes(); byte_count += len(raw)
        return raw

    def document(path): return json.loads(read(path))

    def relative(root, name):
        p = PurePosixPath(name)
        need("portable_sealed_member_" + name, not p.is_absolute() and ".." not in p.parts and ":" not in name and "\\" not in name)
        target = root.joinpath(*p.parts)
        need("contained_sealed_member_" + name, target.resolve().is_relative_to(root.resolve()) and not target.is_symlink())
        return target

    sealed = {}
    for operation, folder, filename, terminal in (("reconstruct", "reconstruction-v2", "reconstruction.json", "reconstruction_completed"),
                                                  ("audit", "audit-v2", "audit.json", "audit_completed")):
        base = ARCHIVE / folder
        receipt_raw = read(base / "receipt.json"); receipt = json.loads(receipt_raw)
        need(operation + "_qualified_receipt", wire({k: receipt[k] for k in ("schema_version", "method", "operation", "status", "protocol_sha256")}) ==
             wire(dict(schema_version=1, method="p09.reconstruction_receipt.v1", operation=operation, status="SEALED_SUCCESS", protocol_sha256=READY)))
        actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
        need(operation + "_complete_final_set", actual == set(receipt["files"]) | {"receipt.json"})
        need(operation + "_no_failure_artifact", not {"failure.json", "failure-seal.json"} & actual)
        for name, descriptor in receipt["files"].items():
            raw = read(relative(base, name))
            need(operation + "_final_exact_bytes_" + name, len(raw) == descriptor["bytes"] and sha(raw) == descriptor["sha256"])
        report_raw = read(base / filename); report = json.loads(report_raw)
        journal_raw = read(base / "journal.jsonl")
        events = [json.loads(line) for line in journal_raw.splitlines()]
        previous = None
        for i, event in enumerate(events):
            need(operation + "_journal_chain_" + str(i), event["sequence"] == i and event["previous_sha256"] == previous
                 and event["sha256"] == sha(wire({k: v for k, v in event.items() if k != "sha256"})))
            previous = event["sha256"]
        need(operation + "_terminal_report_byte_binding", events[0]["event"] == "build_reserved" and events[-1]["event"] == terminal
             and events[-1]["details"]["report_sha256"] == sha(report_raw)
             and not any("failed" in e["event"] or "interrupted" in e["event"] for e in events))
        admitted = [e for e in events if e["event"] == "protocol_admitted"]
        need(operation + "_external_READY_journal", len(admitted) == 1 and admitted[0]["details"] == dict(operation=operation, protocol_sha256=READY))
        sealed[operation] = dict(root=base, report=report, receipt=receipt, events=events, report_sha256=sha(report_raw),
            receipt_sha256=sha(receipt_raw), journal_sha256=sha(journal_raw), file_count=len(actual))
    r, a = sealed["reconstruct"]["report"], sealed["audit"]["report"]
    need("external_v2_reconstruction_report_pin", sealed["reconstruct"]["report_sha256"] == "a0f4e0e76ad5dfd746664c69023549cb0bf23fd74316b02a40ef85c54bfd8acb")
    need("external_v2_audit_report_pin", sealed["audit"]["report_sha256"] == "b7e8bdd49fe0a29a78277a65ba627e405b652b6aa5e060f930796421958f62ca")
    rr, ar = sealed["reconstruct"]["receipt"], sealed["audit"]["receipt"]
    rroot = sealed["reconstruct"]["root"]
    need("archive_expected156_plus3_files", sealed["reconstruct"]["file_count"] == 156 and sealed["audit"]["file_count"] == 3)
    need("reconstruction_status_and_scope", r["status"] == "COMPLETED_PENDING_AUDIT" and r["protocol_sha256"] == READY
         and r["method"] == "p09.source_inclusive_reconstruction.v1" and r["scientific_validation"] == "not_established"
         and r["historical_archive_integrity"] == "not_provided_by_public_reconstruction"
         and r["historical_output_comparison"] == "all_38_exact_byte_hashes_and_all_90_decisions"
         and all(type(r[k]) is int and r[k] == 0 for k in ("model_calls", "network_calls", "new_downloads", "provider_spending_usd")))
    seal_raw = read(rroot / "output-seal.json"); seal = json.loads(seal_raw)
    need("precomparison_seal_scope", seal["method"] == "p09.reconstructed_output_seal.v1" and seal["protocol_sha256"] == READY
         and seal["comparison_inputs_parsed"] is False and type(seal["model_calls"]) is int and seal["model_calls"] == 0
         and seal["scientific_validation"] == "not_established")
    need("new_output_seal_exact_crossanchors", sha(seal_raw) == r["output_seal_sha256"] == rr["output_seal_sha256"] == a["subject"]["output_seal_sha256"])
    need("final_reconstruction_byte_crossanchors", sealed["reconstruct"]["report_sha256"] == rr["reconstruction_sha256"] == a["subject"]["reconstruction_sha256"])
    need("audit_subject_matches_exact_receipt", a["subject"]["receipt_sha256"] == sealed["reconstruct"]["receipt_sha256"] and a["subject"]["protocol_sha256"] == READY)
    need("audit_receipt_optional_reconstruction_fields_are_null", ar["output_seal_sha256"] is None and ar["reconstruction_sha256"] is None)
    need("all_precomparison_files_sealed", set(seal["files"]) == set(rr["files"]) - {"reconstruction.json", "output-seal.json", "journal.jsonl"})
    for name, anchor in seal["files"].items():
        need("precomparison_final_anchor_" + name, wire(anchor) == wire(rr["files"][name]))
    events = sealed["reconstruct"]["events"]
    si = [i for i, e in enumerate(events) if e["event"] == "outputs_sealed"]
    ci = [i for i, e in enumerate(events) if e["event"] == "comparison_started"]
    need("seal_precedes_historical_comparator", len(si) == len(ci) == 1 and 0 < si[0] < ci[0] < len(events)-1
         and events[si[0]]["details"]["output_seal_sha256"] == sha(seal_raw)
         and events[si[0]-1]["sha256"] == seal["journal_prefix_sha256"]
         and events[ci[0]]["details"]["comparison_sha256"] == COMPARISON)

    need("independent_audit_PASS_with_all_checks", a["method"] == "p09.independent_source_inclusive_reconstruction_audit.v1"
         and a["status"] == "PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT" and a["check_count"] == len(a["checks"]) == 6862
         and all(c["pass"] is True for c in a["checks"]) and a["unresolved_findings"] == []
         and a["source_inclusive"] is True and a["independent_projection"] is True and a["producer_policy_baseline_controls_imports"] == 0
         and a["scientific_validation"] == a["study_independence"] == "not_established" and a["old_private_archive_G0"] == "unavailable")
    check_names = {c["check"] for c in a["checks"]}
    need("auditor_retains_all38_historical_checks", sum(n.startswith("historical_output_metadata_") for n in check_names) == 38)
    need("auditor_retains_all90_historical_decision_checks", sum(n.startswith("historical_decision_") for n in check_names) == 90)
    coverage_raw = read(rroot / "source-coverage.json"); coverage = json.loads(coverage_raw)
    proofs = coverage["source_proofs"]
    need("coverage_all137_original_proofs", len(proofs) == len({p["artifact_id"] for p in proofs}) == 137 and all(not p["parents"] for p in proofs)
         and Counter(p["role"] for p in proofs) == dict(agent_evidence=136, reference=1))
    need("coverage_fixed12_dispositions", coverage["coverage"]["original_files"] == a["originals_verified"] == 137
         and coverage["coverage"]["selected_cases"] == 12 and set(coverage["dispositions"]) == set(CASES)
         and all(d["status"] == "ready_for_base_compile" and d["blocked_reason"] is None for d in coverage["dispositions"].values()))
    need("coverage_mapping_and_full_physical_counts", wire(coverage["coverage"]["mapping_rows"]) == wire(a["mapping_row_counts"])
         and a["native_physical_row_counts"] == dict(credible_set=2862043, gwas_credible_sets=1753850))
    need("coverage_resource_counter_crossbinding", wire(coverage["resources"]) == wire(r["resources"]))
    refs, availability, reference_pins = {}, Counter(), {}
    need("all12_reference_descriptors", set(r["native_references"]) == set(CASES))
    for cid in CASES:
        item = r["native_references"][cid]
        need("reference_fixed_relative_path_" + cid, item["path"] == "references/" + cid + ".json")
        raw = read(relative(rroot, item["path"])); ref = json.loads(raw); refs[cid] = ref
        need("reference_canonical_identity_" + cid, sha(wire(ref)) == item["fingerprint"] and sha(wire(ref["method"]["task"])) == ref["task_sha256"] == item["task_sha256"])
        projected = deepcopy(ref); del projected["method"]["catalog_sha256"]
        need("reference_exact_catalog_only_projection_" + cid, sha(wire(projected)) == item["projection_sha256"])
        need("reference_original_proofs_and_eval_role_" + cid, wire(ref["source_proofs"]) == wire(proofs) and ref["role"] == "evaluation_only" and ref["agent_visible"] is False
             and ref["method"]["scientific_validation"] == "not_established")
        requested = Counter(f["family"] for f in ref["facts"])
        answered = Counter(f["family"] for f in ref["facts"] if f["value"] is not None)
        m = [f for f in ref["facts"] if f["family"] == "reported_measurement" and f["value"] is not None]
        counts = dict(requested_facts=len(ref["facts"]), measurement_answerable_facts=len(m), measurement_answerable_groups=len({(f["record_key"],f["group"]) for f in m}))
        need("reference_source_denominators_" + cid, wire(counts) == wire(item["counts"]) and requested == dict(identity_linkage=11, reported_measurement=4))
        need("reference_native_nulls_and_types_" + cid, all((f["value"] is None and f["unknown_reason"] == "null_source_value") or
             (f["value"] is not None and f["unknown_reason"] is None and type(f["value"]) in ((int,float) if f["family"] == "reported_measurement" else (str,))) for f in ref["facts"]))
        availability.update(identity_requested=requested["identity_linkage"], identity_answerable=answered["identity_linkage"],
                            measurement_requested=requested["reported_measurement"], measurement_answerable=answered["reported_measurement"],
                            native_nulls=sum(f["value"] is None for f in ref["facts"]), absent=0, empty=0)
        reference_pins[cid] = dict(byte_sha256=sha(raw), canonical_sha256=item["fingerprint"], projection_sha256=item["projection_sha256"], task_sha256=item["task_sha256"])

    plans = [dict(cell_id=f"N-{arm}-{cid}", case_id=cid, arm=arm, stratum="native") for cid in CASES for arm in ("L", "A")]
    plans += [dict(cell_id="S-"+key, case_id=key, arm="fixture", stratum="fictional_json_core") for key in CONTROLS]
    outputs, decisions = r["output_cells"], r["decision_cells"]
    need("exact38_output_schedule", [{k: row[k] for k in ("cell_id","case_id","arm","stratum")} for row in outputs] == plans)
    dplans = [dict(decision_id="D-"+p["cell_id"]+"-"+policy, policy=policy, output_cell_id=p["cell_id"]) for p in plans for policy in (("FULL",) if p["arm"] == "A" else POLICIES)]
    need("exact90_decision_schedule", [{k: d[k] for k in ("decision_id","policy")} for d in decisions] == [{k:d[k] for k in ("decision_id","policy")} for d in dplans])
    need("all38_guard_records", set(r["guards"]) == {p["cell_id"] for p in plans})
    for output in outputs:
        cid = output["cell_id"]
        need("output_fixed_raw_path_"+cid, output["raw_path"] == "raw/"+cid+".json")
        raw = read(relative(rroot, output["raw_path"]))
        need("output_exact_raw_byte_metadata_"+cid, len(raw) == output["raw_bytes"] and sha(raw) == output["raw_sha256"])
        if output["stratum"] == "native":
            ref = refs[output["case_id"]]; task = ref["method"]["task"]; doc = json.loads(raw)
            need("native_task_and_new_ref_score_binding_"+cid, doc["task_sha256"] == ref["task_sha256"] and output["core_score"]["reference_sha256"] == r["native_references"][output["case_id"]]["fingerprint"])
            fields = [{k:f[k] for k in ("fact_id","value","unit","source","unknown_reason")} for f in ref["facts"]]
            need("native_wire_ref_consistency_"+cid, doc["status"] == ("answered" if output["arm"] == "L" else "abstained")
                 and wire(doc["facts"]) == wire(fields if output["arm"] == "L" else []) and output["core_score"]["critical_errors"] == [])
    for plan, decision in zip(dplans, decisions):
        guards = r["guards"][plan["output_cell_id"]]
        required = ["G0","G4_schema_only"] if plan["policy"] == "WIRE_ONLY" else ["G0","G1","G3","G4"] if plan["policy"] == "WITHOUT_WRAPPER" else ["G0","G1","G2","G3","G4"]
        observed = [(g, guards["G4"]["schema_status"] if g == "G4_schema_only" else guards[g]["status"]) for g in required]
        failed = next(("G4" if g == "G4_schema_only" else g for g,v in observed if v == "rejected"), None)
        verdict = "rejected" if failed else "admitted" if all(v == "pass" for _,v in observed) else "no_decision"
        need("paired_policy_from_retained_guards_"+plan["decision_id"], decision["required_stages"] == required and decision["verdict"] == verdict
             and decision["first_failure_stage"] == failed and decision["terminal"] == ("unexecuted" if verdict == "no_decision" else "returned"))
    literal = [o for o in outputs if o["arm"] == "L"]; abstain = [o for o in outputs if o["arm"] == "A"]
    measures = {p: {(d["decision_id"].removesuffix("-"+p)):d["verdict"] for d in decisions if d["policy"] == p and d["decision_id"].startswith("D-S-")} for p in POLICIES}
    counts = dict(planned_output_cells=len(outputs), planned_decisions=len(decisions), output_terminal_counts=dict(Counter(o["terminal"] for o in outputs)),
        decision_verdict_counts=dict(Counter(d["verdict"] for d in decisions)), core_scored_outputs=sum(o["core_score"] is not None for o in outputs),
        native_literal=dict(cases=len(literal), verified_exact=sum(o["full_verified_exact"] for o in literal),
            **{"complete_"+t:sum(o["core_score"]["primary"]["passes"][t] is True for o in literal) for t in ("60","80","100")},
            critical_errors=sum(len(o["core_score"]["critical_errors"]) for o in literal)),
        native_abstain=dict(cases=len(abstain), completion_80=sum(o["core_score"]["completion"] for o in abstain), emitted_facts=sum(o["core_score"]["emitted_facts"] for o in abstain), critical_errors=sum(len(o["core_score"]["critical_errors"]) for o in abstain)),
        native_availability=dict(availability), controls=dict(scenarios=len(CONTROLS),valid=sum(k.startswith("C") for k in CONTROLS),invalid=sum(k.startswith("F") for k in CONTROLS),
            invalid_admissions={p:sum(key.startswith("D-S-F") and value == "admitted" for key,value in measures[p].items()) for p in POLICIES},
            valid_rejections={p:sum(key.startswith("D-S-C") and value == "rejected" for key,value in measures[p].items()) for p in POLICIES}),
        paired_control_discordance={p+"__"+q:sum(v != measures[q][key] for key,v in measures[p].items()) for p,q in (("FULL","WITHOUT_WRAPPER"),("FULL","WIRE_ONLY"),("WITHOUT_WRAPPER","WIRE_ONLY"))})
    need("recomputed_all_descriptive_counts", wire(counts) == wire(r["analysis_counts"]) == wire(a["analysis_counts"]))
    need("operation_costs_separate_and_unknowns_retained", all(o["physical_io_bytes"] is None and o["platform_cost_usd"] is None for o in (r["operation_resources"],a["operation_resources"]))
         and r["resources"]["logical_original_compressed_bytes_scanned"] == a["resources"]["logical_original_compressed_bytes_scanned"] == 2866248239)

    previous_root = SEALED_ROOT / "reconstruction-v1"
    previous = json.loads(read(previous_root / "reconstruction.json"))
    previous_receipt = json.loads(read(previous_root / "receipt.json"))
    need("original_v1_reconstruction_retained", sha(read(previous_root / "reconstruction.json")) == "8d29f8dcf27985acfe021548657d0c69c5e6d007913008f4cb061c352ae15db3"
         and previous["protocol_sha256"] == "650859b151bee4a98d6da8c779a7b498720929bfe1e7218d5e6f426f78cea123")
    need("same156_reconstruction_file_names", set(previous_receipt["files"]) == set(rr["files"]))
    changed = []
    for name in sorted(set(rr["files"]) | {"receipt.json"}):
        if read(relative(previous_root, name)) != read(relative(rroot, name)):
            changed.append(name)
    scenarios = {"fictional/" + key + "/scenario.json" for key in CONTROLS}
    need("only_runtime_authority_cost_and_seal_records_differ", set(changed) == {"receipt.json", "journal.jsonl", "output-seal.json", "reconstruction.json", "source-coverage.json"} | scenarios)
    for name in sorted(scenarios):
        old_doc = json.loads(read(relative(previous_root, name)))
        new_doc = json.loads(read(relative(rroot, name)))
        for key in ("generation_snapshot", "evaluation_snapshot"):
            old_value, new_value = old_doc[key]["raw_root"], new_doc[key]["raw_root"]
            need("scenario_runtime_root_configuration_" + name + "_" + key,
                 type(old_value) is str and type(new_value) is str and Path(old_value).is_absolute() and Path(new_value).is_absolute()
                 and Path(old_value).parts[-3:] == Path(new_value).parts[-3:] == ("fictional", name.split("/")[1], "originals"))
            old_doc[key]["raw_root"] = new_doc[key]["raw_root"] = None
        need("scenario_only_runtime_root_delta_" + name, wire(old_doc) == wire(new_doc))
    need("all38_raw_and12_reference_bytes_identical_across_revisions", not any(n.startswith(("raw/", "references/")) for n in changed))
    for key in ("output_cells", "decision_cells", "native_references", "analysis_counts"):
        need("same_individual_v1_v2_" + key, wire(previous[key]) == wire(r[key]))
    def guard_semantics(guards):
        return {cid: {stage: {k: v for k, v in item.items() if k not in ("cpu_seconds", "wall_seconds")}
                      for stage, item in stages.items()} for cid, stages in guards.items()}
    need("same_individual_v1_v2_guard_semantics", wire(guard_semantics(previous["guards"])) == wire(guard_semantics(r["guards"])))
    need("guard_deltas_only_measured_timing_fields", all(set(previous["guards"][cid][stage]) == set(item)
         and all(type(item[k]) in (int, float) and math.isfinite(item[k]) and item[k] >= 0
                 for k in ("cpu_seconds", "wall_seconds") if k in item)
         for cid, stages in r["guards"].items() for stage, item in stages.items()))
    previous_coverage = json.loads(read(previous_root / "source-coverage.json"))
    for key in ("source_proofs", "coverage", "dispositions"):
        need("same_original_v1_v2_" + key, wire(previous_coverage[key]) == wire(coverage[key]))

    projected = dict(schema_version=1, method="p09.installed_native_reconstruction_qualification.v1", status="PASS_NATIVE_RECONSTRUCTION_AND_INDEPENDENT_AUDIT",
        protocol_sha256=READY, platform=dict(os="Windows x64",python="3.11.15",pyarrow="21.0.0"),
        reconstruction=dict(report_sha256=sealed["reconstruct"]["report_sha256"],receipt_sha256=sealed["reconstruct"]["receipt_sha256"],journal_sha256=sealed["reconstruct"]["journal_sha256"],
            output_seal_sha256=sha(seal_raw),source_coverage_sha256=sha(coverage_raw),status=r["status"],files=sealed["reconstruct"]["file_count"],operation_resources=r["operation_resources"]),
        independent_audit=dict(report_sha256=sealed["audit"]["report_sha256"],receipt_sha256=sealed["audit"]["receipt_sha256"],journal_sha256=sealed["audit"]["journal_sha256"],status=a["status"],checks=a["check_count"],
            source_inclusive=True,independent_projection=True,unresolved_findings=[],operation_resources=a["operation_resources"]),
        original_file_count=a["originals_verified"],native_reference_count=len(refs),analysis_counts=counts,
        policy_session_counters=dict(r["resources"],scope="Policy session only; repeated reference-compiler/caller source reads are excluded, so this is not total reconstruction I/O."),
        model_calls=0,network_calls=0,new_downloads=0,provider_spending_usd=0,scientific_validation="not_established",study_independence="not_established",
        old_private_archive_integrity="not_provided_by_public_reconstruction",reference_comparison_projection="remove_only_method_catalog_sha256.v1",
        other_test_lanes=dict(installed82=dict(status="PASS_ROOT_REPORTED",wall_seconds=182.260,command_uses_B=True,pristine_bundle_files=312,
            provenance="Root terminal report; no separate test-log reread in this sealed-output review."),main_core="PENDING_SECOND_TERMINAL_EVIDENCE",main_full="PENDING_SECOND_TERMINAL_EVIDENCE"))
    owner = re.compile(r"(?i)(?:zzric|[A-Z]:[\\/]Users[\\/]|[A-Z]:[\\/]Projects(?:_data)?[\\/]|/Users/|/home/|drug_target_agents_data)")
    need("public_status_projection_no_private_root_or_values", not owner.search(wire(projected).decode().replace("\\\\","\\"))
         and not any(k in wire(projected).decode() for k in ('"facts":','"source_records":','"native_references":')))
    return dict(schema="p09.actual_qualification_peer_review.v2",status="PASS_SEALED_ACTUAL_QUALIFICATION_METADATA_REVIEW" if not findings else "FAIL_SEALED_ACTUAL_QUALIFICATION_METADATA_REVIEW",
        check_count=len(checks),checks=checks,unresolved_findings=findings,external_READY_sha256=READY,
        archive_relative_path=ARCHIVE.relative_to(ROOT).as_posix(),file_counts={k:v["file_count"] for k,v in sealed.items()},reference_hashes=reference_pins,
        recomputed_descriptive_counts=counts,proposed_public_status_projection=projected,
        public_projection_review="Metadata/counts/hashes only; no private root or expected native fact values. Pending second main test lanes must be updated only from separate terminal evidence.",
        revision_comparison=dict(original_READY="650859b151bee4a98d6da8c779a7b498720929bfe1e7218d5e6f426f78cea123",final_READY=READY,
            all38_raw_bytes_identical=True,all12_reference_bytes_identical=True,individual_outputs_decisions_guards_and_denominators_identical=True,
            unchanged_files=156-len(changed),changed_files=changed,source_coverage_original_proofs_dispositions_identical=True,
            runtime_metadata_deltas="Fourteen local scenario documents differ only generation/evaluation raw_root. Guard metadata differs only measured cpu_seconds/wall_seconds; all status/schema/decision semantics match. This run-metadata comparison adds no exception to the catalog-only reference comparison.",
            private_runtime_scenario_documents="Contain execution roots; keep in ignored private archives, outside the public qualification projection and frozen neutral bundle.",
            README_revision_review="DRAFT-BUNDLE-REVIEW-v2.json proves README-only161byte correction;310othermembers and100packagepayloads/fourtests unchanged.",
            original_temporary_cache_files="Root-reported four unlisted pyc files in original temporary C: test copy remain preserved; canonical frozen bundle and sealed v1 archives are retained.",
            main_gates="Initial full1941/3errors and core1941/10errors were not successful; tests-only corrections precede still-pending second gates at commit31a98ed.",
            primary_P06_wall_seconds=dict(production=203.828,source_audit=7.125),source_reread_for_this_review=False),
        limitations=["This is an independent sealed-output consistency review, not a new provider-source replay. The already sealed source-inclusive audit supplies source-projection attestation.",
            "READY exact byte SHA is externally supplied and matched across retained reports/journals; protocol bytes were not reread under this sealed-output-only task.",
            "No copy comparison back to the original C: execution root was performed here; archive exact receipt/file/journal bindings were verified.",
            "Policy logical hash/scan counters exclude repeated compiler/caller reads; total physical I/O and platform cost remain unknown.",
            "Model/science/independence claims remain limited. A native positive reconstruction is not future external URL availability or scientific validation."],
        resources=dict(wall_seconds=time.monotonic()-started,logical_sealed_output_bytes_read=byte_count),provider_originals_opened=0,production_files_modified=0,scientific_validation="not_established")


if __name__ == "__main__":
    report=run(); out=Path(__file__).with_name("ACTUAL-QUALIFICATION-CHECKS-v3.json")
    with out.open("xb") as stream: stream.write(json.dumps(report,indent=2,ensure_ascii=False).encode()+b"\n")
    print(json.dumps({k:report[k] for k in ("status","check_count","unresolved_findings","file_counts","resources")},indent=2))
