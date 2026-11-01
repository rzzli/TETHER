"""Independent, terminal-only P04 mechanical audit. No model/network calls.

Writes only the explicitly named new audit JSON. Evaluator/candidate payloads
stay closed until every requested attempt has a pinned terminal receipt and an
affirmative generation/owned-server cleanup boundary. Scientific truth is not
an endpoint of this checker.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(r"D:\Projects\drug_target_agents")
ASSETS = ROOT / "planning/review-assets/preprint-p04-20261031"
PROTOCOL = ASSETS / "EXECUTION-PROTOCOL-READY-v1.json"
PROTOCOL_SHA = "9cc1f688624f8a4803c200fabccb390ab1ee45bfbe04d17a1a17a83ccdeceeb4"
ZERO = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)
TERMINALS = ("returned", "malformed", "failed", "timeout", "interrupted", "unexecuted")
PRIOR_TERMINALS = {
    "preprint-p04-typed-report-20261101T051718Z": {
        "receipt.json":"63c6900deab52c79bcba445713d79cdf2f14d09baeeb708d0157356a8171e490",
        "report.json":"09c5228ed523325750db4c2da714276aa3c4c4e6ff895b7164767ee7f01b3ff8",
        "journal.jsonl":"4b839df3d9b3b72c52da8b4654c433762e410b1a10c8b7f5435744dc192a4692"},
    "preprint-p04-typed-report-20261101T052735Z": {
        "receipt.json":"bee404e8a521b4edfc58cb228c2ac18b6144a604f546ea797c66b503dbecfbe3",
        "report.json":"1f7ebc9191f7b21466d77a54046422a6a9c2c3744697e5f6d555927c16dd55c2"}}
checks = []
observed_files = {}


def need(ok, name):
    checks.append({"check": name, "passed": bool(ok)})
    if not ok:
        raise RuntimeError("Mechanical audit failed: " + name)


def raw(path):
    return Path(path).read_bytes()


def document(path):
    return json.loads(raw(path).decode("utf-8-sig"))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def proof(path):
    value = raw(path)
    return {"bytes": len(value), "sha256": digest(value)}


def pinned(path, expected, name):
    expected = {k: expected[k] for k in ("bytes", "sha256")}
    need(proof(path) == expected, name)
    resolved = str(Path(path).resolve())
    need(resolved not in observed_files or observed_files[resolved] == expected, name + ": stable audit binding")
    observed_files[resolved] = expected


def within(root, name):
    candidate = (root / str(name).replace("\\", "/")).resolve()
    need(candidate.is_relative_to(root.resolve()), "path stays inside approved root")
    return candidate


def add(total, usage):
    for key in ZERO:
        total[key] += usage[key]


def terminal_metadata(run, protocol):
    """No source/reference member or candidate is read by this gate."""
    for name,expected in PRIOR_TERMINALS.get(run.name, {}).items():
        need(digest(raw(run / name)) == expected, run.name + ": preserved prior terminal pin " + name)
    receipt = document(run / "receipt.json")
    pinned(run / "report.json", receipt["report"], run.name + ": receipt/report bytes")
    report = document(run / "report.json")
    need(receipt["protocol_sha256"] == report["protocol_sha256"] == PROTOCOL_SHA,
         run.name + ": protocol binding")
    need(digest(raw(run / "journal.jsonl")) == receipt["journal_sha256"],
         run.name + ": journal exact bytes")
    from asof.journal import read_chain
    from asof.serde import canonical
    events = read_chain(run / "journal.jsonl")
    reserved = [e for e in events if e["event"] == "schedule_reserved"]
    need(len(reserved) == 1 and list(reserved[0]["details"]["planned_cells"]) == protocol["scheduled_cells"]
         and reserved[0]["details"]["protocol_sha256"] == PROTOCOL_SHA
         and reserved[0]["details"]["retry_policy"] == "none", run.name + ": frozen journal schedule")
    need(events[-1]["sha256"] == receipt["journal_terminal_sha256"]
         and events[-1]["event"] in ("run_completed", "run_partial"), run.name + ": terminal chain")
    need(events[-1]["details"]["report"] == receipt["report"], run.name + ": terminal report binding")
    need(receipt["status"] == report["status"]
         and (events[-1]["event"] == "run_completed") == (report["status"] == "completed"),
         run.name + ": terminal status agrees")
    ceased = [e for e in events if e["event"] == "generation_ceased"]
    need(len(ceased) == 1 and ceased[0]["details"]["evaluator_payloads_opened"] is False,
         run.name + ": explicit generation cessation")
    boundary = ceased[0]["sequence"]
    server = report["server"]
    starts = [e for e in events if e["event"] == "server_started"]
    stops = [e for e in events if e["event"] == "server_terminal"]
    if server is None:
        need(not starts and not stops, run.name + ": server never started")
    else:
        need(server.get("started") is False or server.get("server_stopped") is True,
             run.name + ": affirmative owned-server cleanup")
        need(len(stops) == 1 and canonical(stops[0]["details"]) == canonical(server)
             and stops[0]["sequence"] < boundary, run.name + ": cleanup precedes boundary")
    generation_events = {"cell_reserved", "stage_reserved", "dispatch", "attempt_accounted",
                         "report_structure_checked", "cell_terminal", "server_started", "server_terminal"}
    need(all(e["sequence"] < boundary for e in events if e["event"] in generation_events),
         run.name + ": no generation after boundary")
    replays = [e for e in events if e["event"] == "reference_replayed"]
    need(all(e["sequence"] > boundary for e in replays), run.name + ": evaluation follows cessation")
    need(len(replays) == 3 and {e["details"]["condition"] for e in replays}
         == {c["condition"] for c in protocol["scheduled_cells"]}, run.name + ": three evaluator replays")
    need(report["planned_cells"] == receipt["planned_cells"] == 12,
         run.name + ": complete planned denominator")
    return report, events, ceased[0]


def audit_archive(run, protocol):
    pinned(run / "protocol.json", proof(PROTOCOL), run.name + ": frozen protocol copy")
    for name, expected in protocol["code_bundle"].items():
        pinned(within(run / "code", name), expected, run.name + ": archived code " + name)
    for key in ("generation_manifest", "reference_manifest", "input_plan"):
        pinned(run / (key + ".json"), protocol[key], run.name + ": " + key)
    need(document(run / "environment.json") == protocol["environment"], run.name + ": frozen environment")
    if (run / "model-acquisition.json").exists():
        pinned(run / "model-acquisition.json", protocol["model"]["acquisition"], run.name + ": acquisition metadata")
    for phase, seal_name in (("source", "generation_seal_sha256"), ("reference", "reference_seal_sha256")):
        need(digest(raw(run / (phase + "-SEAL.json"))) == protocol[seal_name], run.name + ": " + phase + " seal")
        need(digest(raw(run / (phase + "-journal.jsonl"))) == protocol[phase + "_journal_sha256"],
             run.name + ": " + phase + " preparation journal")
    generation_seal = document(run / "source-SEAL.json")
    reference_seal = document(run / "reference-SEAL.json")
    for name, expected in generation_seal["files"].items():
        pinned(within(run / "generation-inputs", name), expected, run.name + ": generation file " + name)
    for name, expected in reference_seal["files"].items():
        need(expected["role"] == "evaluation_only" and expected["agent_visible"] is False,
             run.name + ": evaluator role " + name)
        pinned(within(run / "evaluation-only", name), expected, run.name + ": evaluator file " + name)
    return reference_seal


def audit_cells(run, protocol, report, events, ceased):
    schedule = protocol["scheduled_cells"]
    cells = report["cells"]
    need([c["cell_id"] for c in cells] == [c["cell_id"] for c in schedule], run.name + ": all twelve cells in order")
    final_cells = ceased["details"]["cells"]
    need([c["cell_id"] for c in final_cells] == [c["cell_id"] for c in schedule], run.name + ": cessation retains all cells")
    accounted = [e["details"] for e in events if e["event"] == "attempt_accounted"]
    intent_events = [e["details"] for e in events if e["event"] == "dispatch"]
    intents = {e["attempt_id"]:e for e in intent_events}
    need(len(intents) == len(intent_events), run.name + ": no duplicate dispatch intent")
    need(len({a["attempt_id"] for a in accounted}) == len(accounted), run.name + ": no duplicate attempt accounting")
    need(all(a["cell_id"] in {c["cell_id"] for c in schedule} for a in accounted), run.name + ": no unscheduled attempt")
    need(set(intents) <= {a["attempt_id"] for a in accounted}, run.name + ": no unresolved dispatch intent")
    measured, estimated, raws = dict(ZERO), dict(ZERO), {}
    for scheduled, cell, final in zip(schedule, cells, final_cells):
        identifier = cell["cell_id"]
        need(all(cell[k] == scheduled[k] for k in ("cell_id", "arm", "condition")), identifier + ": scheduled arm/condition")
        need(cell["terminal"] in TERMINALS and all(cell[k] == final[k] for k in
             ("terminal", "reason", "dispatches", "measured_usage", "estimated_usage", "raw_final_sha256")),
             identifier + ": cessation/report agrees")
        cell_measured, cell_estimated = dict(ZERO), dict(ZERO)
        attempts = [a for a in accounted if a["cell_id"] == identifier]
        allowed_stages = ([] if cell["arm"] in ("exact_literal_assembler","always_abstain") else
                          ["plain"] if cell["arm"] == "plain_same_model_typed_report" else ["proposal","audit"])
        stages = cell["stage_records"]
        need([s["stage"] for s in stages] == allowed_stages[:len(stages)]
             and len(stages) <= len(allowed_stages)
             and all(s["attempt_id"] == identifier + ":" + s["stage"] for s in stages), identifier + ": declared stages only")
        need({a["attempt_id"] for a in attempts} <= {s["attempt_id"] for s in stages}, identifier + ": accounted declared attempts")
        need(sum(a["dispatched"] is True for a in attempts) == cell["dispatches"], identifier + ": actual dispatches")
        for attempt in attempts:
            if attempt["dispatched"]:
                need(attempt["attempt_id"] in intents, identifier + ": dispatched request was retained")
            basis = attempt["basis"]
            need(basis in ("adapter_reported", "quoted_upper_bound_not_measured", "not_dispatched"), identifier + ": usage basis")
            usage = attempt["usage"]
            need(set(usage) == set(ZERO) and all(type(usage[k]) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens"))
                 and type(usage["cost_usd"]) in (int,float) and math.isfinite(usage["cost_usd"])
                 and usage["cost_usd"] == 0, identifier + ": finite nonnegative usage")
            if basis == "not_dispatched":
                need(attempt["dispatched"] is False and attempt["usage"] == ZERO, identifier + ": undispatched zero charge")
            elif basis == "adapter_reported":
                need(attempt["dispatched"] is True, identifier + ": measured charge was dispatched")
                add(cell_measured, attempt["usage"])
            else:
                need(attempt["dispatched"] is True, identifier + ": reservation charge was dispatched")
                need(attempt["usage"] == intents[attempt["attempt_id"]]["reserved"], identifier + ": reservation charge")
                add(cell_estimated, attempt["usage"])
            for expected in attempt["files"].values():
                pinned(within(run / identifier, expected["path"]), expected, identifier + ": journal stage file")
        for stage in cell["stage_records"]:
            related = [a for a in attempts if a["attempt_id"] == stage["attempt_id"]]
            if related:
                attempt = related[0]
                need(stage["dispatched"] == attempt["dispatched"] and stage["files"] == attempt["files"]
                     and stage["accounting_basis"] == attempt["basis"], identifier + ": stage/journal agreement")
            for expected in stage["files"].values():
                pinned(within(run / identifier, expected["path"]), expected, identifier + ": report stage file")
        need(cell_measured == cell["measured_usage"] and cell_estimated == cell["estimated_usage"], identifier + ": usage reconstruction")
        need(cell["dispatches"] <= protocol["budgets_per_arm_cell"]["max_calls"]
             and cell_measured["input_tokens"] + cell_estimated["input_tokens"] <= 32000
             and cell_measured["output_tokens"] + cell_estimated["output_tokens"] <= 8000
             and cell_measured["cost_usd"] == cell_estimated["cost_usd"] == 0, identifier + ": token/call/cost caps")
        if cell["terminal"] == "returned":
            need(cell["elapsed_seconds"] is not None and 0 <= cell["elapsed_seconds"] < 300,
                 identifier + ": returned inside wall-time cap")
        add(measured, cell_measured)
        add(estimated, cell_estimated)
        if cell["raw_final_sha256"] is not None:
            candidate = run / identifier / "final-response.bin"
            pinned(candidate, {"bytes":cell["raw_final_bytes"],"sha256":cell["raw_final_sha256"]}, identifier + ": exact final bytes")
            raws[identifier] = raw(candidate)
        else:
            need(cell["raw_final_bytes"] is None, identifier + ": absent final bytes explicitly unknown")
            raws[identifier] = None
    counts = dict.fromkeys(TERMINALS, 0)
    counts.update(Counter(c["terminal"] for c in cells))
    need(counts == report["terminal_counts"] == ceased["details"]["terminals"], run.name + ": terminal counts")
    need(sum(c["dispatches"] for c in cells) == report["actual_calls"] == sum(a["dispatched"] is True for a in accounted),
         run.name + ": all-cell actual calls")
    need(measured == report["measured_usage"] and estimated == report["estimated_upper_usage"], run.name + ": all-cell usage")
    return raws


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--output", default=str(ASSETS / "ATTEMPT-AUDIT-v1.json"))
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    protocol = document(PROTOCOL)
    need(digest(raw(PROTOCOL)) == PROTOCOL_SHA and protocol["status"] == "READY", "independent READY protocol")
    runs = [within(ROOT, name) for name in args.runs]
    need(len(set(runs)) == len(runs) and all(r.parent == ROOT / "runs" for r in runs), "distinct approved direct-child attempts")
    pending = [r.name for r in runs if not (r / "receipt.json").is_file() or not (r / "report.json").is_file()]
    if pending or args.preflight:
        print(json.dumps({"status":"PENDING_TERMINAL_RECEIPTS" if pending else "READY_FOR_TERMINAL_AUDIT", "pending":pending,
                          "candidate_or_evaluator_values_opened":False,"files_written":0}))
        return
    for name, expected in protocol["code_bundle"].items():
        pinned(within(ROOT, name), expected, "current frozen code " + name)
    from asof.serde import canonical, decode, fingerprint
    from asof.contracts import Snapshot
    from asof.study.source_fact_sources import verify_reference
    from asof.study.source_fact_evaluation import aggregate_cells, score_cell
    gated = [(run, *terminal_metadata(run, protocol)) for run in runs]
    terminal_pins = {str(run):{name:proof(run / name) for name in ("receipt.json","report.json","journal.jsonl")}
                     for run in runs}
    # All requested attempts have ended before any candidate/evaluator payload read.
    for run, report, events, ceased in gated:
        audit_archive(run, protocol)
    base = runs[0]
    manifest = document(base / "reference_manifest.json")
    snapshot_doc = document(base / "evaluation-only/source-snapshot.json")["source_snapshot"]
    need(fingerprint(snapshot_doc) == manifest["pins"]["source_snapshot_sha256"], "source snapshot pin")
    snapshot = decode(Snapshot, snapshot_doc)
    catalog_path = base / "evaluation-only/catalog-original.json"
    need(digest(raw(catalog_path)) == manifest["pins"]["catalog_sha256"], "original catalog pin")
    catalog = document(catalog_path)
    references, replay_resources = {}, []
    replay_started = time.monotonic()
    replay_deadline = replay_started + 3600
    for condition in dict.fromkeys(c["condition"] for c in protocol["scheduled_cells"]):
        pin = manifest["conditions"][condition]
        task = document(base / "generation-inputs" / (condition + ".task.json"))
        need(fingerprint(task) == pin["task_sha256"], condition + ": fixed task hash")
        start = time.monotonic()
        references[condition] = verify_reference(document(base / "evaluation-only" / pin["reference_path"]),
            pin["reference_sha256"], task, snapshot, ROOT, catalog, deadline=replay_deadline,
            approved_raw_root=Path(protocol["roots"]["approved_raw_root"]))
        replay_resources.append({"condition":condition,"source_graph_nodes":len(snapshot.sources),
                                 "elapsed_seconds":time.monotonic()-start})
    summaries = []
    for run, report, events, ceased in gated:
        raws = audit_cells(run, protocol, report, events, ceased)
        scored = [score_cell(references[s["condition"]], raws[s["cell_id"]], cell_id=s["cell_id"],
                            terminal=c["terminal"]) for s,c in zip(protocol["scheduled_cells"], report["cells"])]
        planned = [{k:c[k] for k in ("cell_id","task_id","task_sha256","reference_sha256")}
                   for c in protocol["scheduled_cells"]]
        aggregate = aggregate_cells(planned, scored)
        need(canonical(aggregate) == canonical(report["scores"]) == raw(run / "scores.json"), run.name + ": exact source-inclusive score reconstruction")
        need(report["scientific_validation"] == aggregate["scientific_validation"] == "not_established"
             and report["measurement_endpoint"] == "not_studied", run.name + ": claim boundary")
        summaries.append({"run":str(run.relative_to(ROOT)),"status":report["status"],"actual_calls":report["actual_calls"],
                          "terminal_counts":report["terminal_counts"],"measured_usage":report["measured_usage"],
                          "estimated_upper_usage":report["estimated_upper_usage"],"scorable_cells":aggregate["scorable_cells"],
                          "completion_count":aggregate["completion_count"],"completion_rate":aggregate["completion_rate"],
                          "correct_missing_input_count":aggregate["correct_missing_input_count"],
                          "receipt":proof(run / "receipt.json"),"report":proof(run / "report.json"),
                          "journal":proof(run / "journal.jsonl"),"scores":proof(run / "scores.json")})
    # Recheck fixed executing code and terminal metadata after replay.
    for name, expected in protocol["code_bundle"].items():
        pinned(within(ROOT, name), expected, "final frozen code " + name)
    for run, report, events, ceased in gated:
        terminal_metadata(run, protocol)
        need(all(proof(run / name) == expected for name,expected in terminal_pins[str(run)].items()),
             run.name + ": terminal bundle unchanged throughout independent replay")
    for name,expected in tuple(observed_files.items()):
        need(proof(name) == expected, "final audited file unchanged " + str(Path(name).relative_to(ROOT)))
    destination = Path(args.output).resolve()
    need(destination.parent == ASSETS.resolve(), "audit output owned directory")
    result = {"schema_version":1,"status":"PASS","computed_at_utc":datetime.now(timezone.utc).isoformat(),
              "role":"evaluation_only","agent_visible":False,"adjudicated_gold":False,
              "scope":"Mechanical source/report fidelity and terminal accounting only; no scientific or clinical truth claim",
              "temporal_evidence":"Frozen-controller control flow plus ordered hash-chained journal; no OS-wide file-open trace",
              "protocol":proof(PROTOCOL),"checker":proof(Path(__file__)),"attempts":summaries,
              "source_inclusive_replays":replay_resources,"shared_references_reused_across_exact_pinned_attempts":True,
              "audit_replay_resources":{"cap_seconds":3600,"elapsed_seconds":time.monotonic()-replay_started,
                  "estimated_logical_original_hash_bytes":2*len(references)*document(base / "generation_manifest.json")["inventory"]["source_bytes"],
                  "physical_io_bytes":None,"peak_native_rss_bytes":None,
                  "estimate_basis":"Two original-file hash passes per source-inclusive replay; excludes row parsing, receipt and artifact reads; cache state unmeasured"},
              "checks":checks,"checks_passed":len(checks),"network_calls":0,"model_calls":0,
              "new_reference_artifacts":0,"human_response_or_clinical_outcome_files_read":False}
    with destination.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status":"PASS","checks_passed":len(checks),"audit":str(destination),**proof(destination)}))


if __name__ == "__main__":
    main()
