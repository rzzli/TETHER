"""Exactly-once, question-only source collection; no reference-container inputs.

The CLI is a child of the experiment supervisor. The API checks its monotonic
budget at boundaries and gives retrieval only the remaining budget. Hard process
termination belongs to the CLI watchdog/parent process guard; inspection never
resumes acquisition or repeats a possibly completed HTTP request.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    __package__ = "experiments.labbench"

from asof.atomic import publish_bytes
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, freeze, parse_json, safe_child
from asof.study.stable_read import read_file, stable_files
from . import data_views, retrieval

MAX_COLLECTION_JSON = 32 * 1024 * 1024
MAX_INVENTORY_FILES = 30000
STATES = frozenset({"completed", "failed", "interrupted", "unexecuted"})
_PROCESS_DEADLINE = None


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _now():
    return time.monotonic()


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _proof(path, payload):
    return {"path": path, "sha256": _sha(payload), "bytes": len(payload)}


def _publish(root, relative, value):
    payload = canonical(value) + b"\n"
    publish_bytes(safe_child(root, relative), payload)
    return _proof(relative, payload)


def _pins():
    return {"collect.py": _sha(data_views.bounded_bytes(Path(__file__))),
            "data_views.py": _sha(data_views.bounded_bytes(Path(data_views.__file__))),
            "retrieval.py": _sha(data_views.bounded_bytes(Path(retrieval.__file__))),
            "runtime.py": _sha(data_views.bounded_bytes(Path(__file__).with_name("runtime.py")))}


def _empty_accounting():
    return {"known_response_body_bytes": 0, "unknown_transfer_upper_bytes": 0,
            "safety_accounted_bytes": 0, "selected_text_bytes": 0,
            "basis": "no_source_dispatch"}


def _totals(cases):
    counts = Counter(case["status"] for case in cases)
    return {"scheduled": len(cases), "counts": {state: counts[state] for state in sorted(STATES)},
            "known_response_body_bytes": sum(c["byte_accounting"]["known_response_body_bytes"] for c in cases),
            "unknown_transfer_upper_bytes": sum(c["byte_accounting"]["unknown_transfer_upper_bytes"] for c in cases),
            "safety_accounted_bytes": sum(c["byte_accounting"]["safety_accounted_bytes"] for c in cases),
            "selected_text_bytes": sum(c["byte_accounting"]["selected_text_bytes"] for c in cases),
            "cases_with_sources": sum(c["status"] == "completed" and c["coverage"]["retained_articles"] > 0 for c in cases),
            "completed_without_sources": sum(c["status"] == "completed" and c["coverage"]["retained_articles"] == 0 for c in cases)}


def _inventory(root):
    records = {}
    for path in sorted(root.rglob("*")):
        _need(not path.is_symlink(), "Symlink in collection output")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {"journal.jsonl", "manifest.json", "SEALED.json", "COMPLETE.json", "PARTIAL.json", "FAILED.json"}:
            continue
        _need(len(records) < MAX_INVENTORY_FILES, "Collection file-count bound exceeded")
        payload = data_views.bounded_bytes(safe_child(root, relative), MAX_COLLECTION_JSON)
        records[relative] = {"sha256": _sha(payload), "bytes": len(payload)}
    return records


def collect(query_path, expected_query_sha256, output, policy, *, stage_seconds):
    """Seal every scheduled disposition. Ordinary failures produce partial output.

    Interruption/fatal errors stop further dispatch. Completed empty retrieval is
    a valid source result with explicit missingness, never biological absence.
    """
    started, cpu_started = _now(), time.process_time()
    journal = RunJournal(Path(output), kind="build")
    root = journal.output
    watchdog = None
    queries, cases, configuration, fatal = (), [], None, None
    try:
        if _PROCESS_DEADLINE is not None:
            from .runtime import DeadlineWatchdog
            watchdog = DeadlineWatchdog(_PROCESS_DEADLINE,root/"WATCHDOG.json")
            watchdog.__enter__()
        _need(type(stage_seconds) in (int,float) and math.isfinite(stage_seconds) and 0 < stage_seconds <= 86400,
              "Invalid collection stage budget")
        deadline = min(started+stage_seconds,_PROCESS_DEADLINE) if _PROCESS_DEADLINE is not None else started+stage_seconds
        policy = retrieval.validate_policy(policy)
        initial_pins = _pins()
        with stable_files((Path(query_path),), deadline=deadline):
            payload = read_file(Path(query_path), deadline, data_views.MAX_BYTES)
            _need(_sha(payload) == expected_query_sha256, "Source query hash mismatch")
            publish_bytes(root / "queries.json", payload)
        with stable_files((root / "queries.json",), deadline=deadline):
            queries = data_views.load_queries(root / "queries.json", expected_query_sha256)
        query_proof = _proof("queries.json", payload)
        configuration = {"schema_version": 1, "kind": "labbench_collection_configuration",
                         "queries": query_proof, "schedule": [query["id"] for query in queries],
                         "policy": policy, "stage_seconds": stage_seconds, "started_at_utc": _utc(),
                         "code_pins": initial_pins, "retries": 0, "input_roles": {"queries": "answerer_input"}}
        config_proof = _publish(root, "configuration.json", configuration)
        journal.append("collection_configured", configuration=config_proof, scheduled=len(queries))
        stop_reason = None
        for ordinal, query in enumerate(queries):
            case_root = f"cases/{ordinal:03d}"
            case = {"id": query["id"], "ordinal": ordinal, "query_sha256": _sha(canonical(query)),
                    "status": "unexecuted", "retrieval": None, "selected": None, "task_sources": None,
                    "effective_policy": None, "timing": {"elapsed_seconds": 0.0, "retrieval_seconds": None,
                    "verification_and_selection_seconds": None}, "byte_accounting": _empty_accounting(),
                    "coverage": None, "reason": None, "error_type": None, "started_at_utc": None,
                    "sealed_at_utc": None}
            if stop_reason is not None or _now() >= deadline:
                case["reason"] = stop_reason or "stage_deadline_before_dispatch"
                stop_reason = case["reason"]
            else:
                case_started = _now()
                case["started_at_utc"] = _utc()
                # Reserve before dispatch; recompute the effective remaining
                # timeout after durable reservation overhead has been charged.
                journal.append("collection_case_reserved", id=query["id"], ordinal=ordinal,
                               query_sha256=case["query_sha256"], maximum_body_bytes=policy["total_bytes"])
                remaining = deadline - _now()
                if remaining <= 0:
                    case["reason"] = stop_reason = "stage_deadline_after_reservation"
                else:
                    effective = dict(policy)
                    effective["question_seconds"] = min(policy["question_seconds"], remaining)
                    effective["request_seconds"] = min(policy["request_seconds"], effective["question_seconds"])
                    case["effective_policy"] = effective
                    case["byte_accounting"] = {"known_response_body_bytes": 0, "unknown_transfer_upper_bytes": policy["total_bytes"],
                        "safety_accounted_bytes": policy["total_bytes"], "selected_text_bytes": 0,
                        "basis": "conservative_whole_case_reservation_until_source_seal"}
                    retrieval_path = case_root + "/retrieval"
                    try:
                        # retrieve itself reserves/journals before its first HTTP
                        # call. Its manifest proves the actual effective policy.
                        retrieved = retrieval.retrieve(query["question"], safe_child(root,retrieval_path), policy=effective)
                        after_retrieval = _now()
                        case["timing"]["retrieval_seconds"] = after_retrieval-case_started
                        manifest_bytes = data_views.bounded_bytes(safe_child(root,retrieval_path+"/manifest.json"), MAX_COLLECTION_JSON)
                        manifest_sha = _sha(manifest_bytes)
                        case["retrieval"] = {"path": retrieval_path, "manifest_sha256": manifest_sha}
                        _need(canonical(parse_json(manifest_bytes)) == canonical(retrieved), "Returned retrieval differs from sealed bytes")
                        _need(_now() < deadline, "Stage deadline after retrieval")
                        verified = retrieval.verify_retrieval(safe_child(root,retrieval_path),manifest_sha,query["question"])
                        _need(canonical(verified["policy"]) == canonical(effective), "Effective retrieval policy mismatch")
                        selected = retrieval.select_passages(verified,query["question"])
                        _need(_now() < deadline, "Stage deadline after source verification")
                        case["selected"] = _publish(root,case_root+"/selected.json",selected)
                        case["task_sources"] = _publish(root,case_root+"/sources.json",selected["sources"])
                        case["byte_accounting"] = {"known_response_body_bytes": verified["costs"]["downloaded_bytes"],
                            "unknown_transfer_upper_bytes": verified["costs"]["unmeasured_transfer_upper_bytes"],
                            "safety_accounted_bytes": verified["costs"]["safety_accounted_bytes"],
                            "selected_text_bytes": selected["coverage"]["selected_text_bytes"], "basis": "verified_retrieval_and_passage_outputs"}
                        case["coverage"] = {"retained_articles": len(verified["sources"]), "selected_passages": len(selected["sources"]),
                            "source_coverage": verified["coverage"], "passage_coverage": selected["coverage"],
                            "retrieval_failures": len(verified["failures"]), "absence_of_evidence_claim": False}
                        case["timing"]["verification_and_selection_seconds"] = _now()-after_retrieval
                        _need(_now() < deadline, "Stage deadline after passage publication")
                        case["status"] = "completed"
                    except BaseException as exc:
                        case["status"] = "interrupted" if isinstance(exc,(KeyboardInterrupt,SystemExit)) else "failed"
                        case["error_type"] = type(exc).__name__
                        case["reason"] = "stage_deadline_during_case" if _now() >= deadline else "source_operation_failed"
                        stop_reason = "prior_case_interrupted" if case["status"] == "interrupted" else "prior_case_failed"
                        fatal = {"id":query["id"],"ordinal":ordinal,"error_type":type(exc).__name__,"reason":case["reason"]}
                        case["selected"] = case["task_sources"] = case["coverage"] = None
                        case["byte_accounting"] = {"known_response_body_bytes":0,"unknown_transfer_upper_bytes":policy["total_bytes"],
                            "safety_accounted_bytes":policy["total_bytes"],"selected_text_bytes":0,
                            "basis":"conservative_whole_case_reservation_until_source_seal"}
                        # Full or partial original source artifacts remain in the
                        # case folder; only completed case grants are consumable.
                    finally:
                        case["timing"]["elapsed_seconds"] = max(0.0,_now()-case_started)
            case["sealed_at_utc"] = _utc()
            case_proof = _publish(root,case_root+"/case.json",case)
            journal.append("collection_case_terminal", id=case["id"],ordinal=ordinal,status=case["status"],case=case_proof)
            cases.append(freeze(case))
        _need(initial_pins == _pins(), "Collection implementation changed during acquisition")
        inventory = _inventory(root)
        cutoff = _utc()  # after every source/passage/case output above is sealed
        if _now() >= deadline and fatal is None:
            fatal = {"error_type":"TimeoutError","reason":"stage_deadline_before_seal"}
        status = "completed" if fatal is None and all(case["status"] == "completed" for case in cases) else "partial"
        manifest = {"schema_version":1,"kind":"labbench_collection","status":status,"configuration":config_proof,
                    "queries":query_proof,"schedule":configuration["schedule"],"policy":policy,"stage_seconds":stage_seconds,
                    "cutoff":cutoff,"cases":cases,"totals":_totals(cases),"code_pins":initial_pins,"outputs":inventory,
                    "resources":{"wall_seconds":max(0.0,_now()-started),"controller_cpu_seconds":time.process_time()-cpu_started,
                                 "http_child_cpu_seconds":None,"peak_memory_bytes":None,"provider_usd":0.0,
                                 "wire_bytes_including_headers_and_tls":None},"fatal":fatal,
                    "recovery":"inspection only; no automatic acquisition retries or resume"}
        manifest_proof = _publish(root,"manifest.json",manifest)
        journal.append("collection_sealed",status=status,manifest=manifest_proof,cutoff=cutoff,scheduled=len(cases))
        seal = {"schema_version":1,"status":status,"manifest_sha256":manifest_proof["sha256"],
                "journal_sha256":_sha(data_views.bounded_bytes(journal.path,MAX_COLLECTION_JSON))}
        _publish(root,"SEALED.json",seal)
        _publish(root,"COMPLETE.json" if status == "completed" else "PARTIAL.json",seal)
        return freeze(manifest)
    except BaseException as exc:
        journal.fail(exc,"collection")
        _publish(root,"FAILED.json",{"error_type":type(exc).__name__,"scheduled":len(queries),"terminal_cases":len(cases),
                                    "recovery":"inspect only; do not rerun this output"})
        raise
    finally:
        journal.close()
        if watchdog is not None:
            watchdog.__exit__(None,None,None)


def _read_proof(root, proof, maximum=MAX_COLLECTION_JSON):
    payload = data_views.bounded_bytes(safe_child(root,proof["path"]),maximum)
    _need(len(payload) == proof["bytes"] and _sha(payload) == proof["sha256"], "Collection output proof mismatch")
    return payload


def verify_collection(root, expected_manifest_sha256, *, deadline=None, allow_partial=False):
    """Source-inclusive verification; never opens original benchmark references."""
    root = Path(root).resolve()
    deadline = _now()+3600 if deadline is None else deadline
    _need(_now() < deadline, "Collection verification deadline exceeded")
    raw = data_views.bounded_bytes(safe_child(root,"manifest.json"),MAX_COLLECTION_JSON)
    _need(_sha(raw) == expected_manifest_sha256,"Collection manifest anchor mismatch")
    manifest = parse_json(raw)
    _need(manifest.get("schema_version") == 1 and manifest.get("kind") == "labbench_collection", "Unknown collection contract")
    _need(manifest["status"] in ("completed","partial") and (allow_partial or manifest["status"] == "completed"),"Collection is not complete")
    _need(not (root/"FAILED.json").exists() and not (root/"WATCHDOG.json").exists(),"Collection has a terminal failure marker")
    _need(manifest["code_pins"] == _pins(),"Collection source code differs")
    seal = parse_json(data_views.bounded_bytes(safe_child(root,"SEALED.json"),4096))
    journal_bytes = data_views.bounded_bytes(safe_child(root,"journal.jsonl"),MAX_COLLECTION_JSON)
    _need(seal == {"schema_version":1,"status":manifest["status"],"manifest_sha256":expected_manifest_sha256,"journal_sha256":_sha(journal_bytes)},"Collection seal mismatch")
    flag = "COMPLETE.json" if manifest["status"] == "completed" else "PARTIAL.json"
    _need(not (root/("PARTIAL.json" if flag == "COMPLETE.json" else "COMPLETE.json")).exists(),"Contradictory collection flags")
    _need(parse_json(data_views.bounded_bytes(safe_child(root,flag),4096)) == seal,"Collection terminal flag differs")
    events = read_chain(root/"journal.jsonl")
    expected_terminal = {"status":manifest["status"],"manifest":_proof("manifest.json",raw),"cutoff":manifest["cutoff"],"scheduled":len(manifest["schedule"])}
    _need(events[-1]["event"] == "collection_sealed" and canonical(events[-1]["details"]) == canonical(expected_terminal),"Collection journal not consistently sealed")
    configuration = parse_json(_read_proof(root,manifest["configuration"]))
    _need(set(configuration) == {"schema_version","kind","queries","schedule","policy","stage_seconds","started_at_utc","code_pins","retries","input_roles"}
          and configuration["schema_version"] == 1 and configuration["kind"] == "labbench_collection_configuration"
          and configuration["retries"] == 0 and configuration["input_roles"] == {"queries":"answerer_input"},"Unexpected collection configuration fields or roles")
    queries = data_views.load_queries(safe_child(root,manifest["queries"]["path"]),manifest["queries"]["sha256"])
    _need(len(_read_proof(root,manifest["queries"])) <= data_views.MAX_BYTES,"Query bound exceeded")
    _need(manifest["queries"]["path"] == "queries.json" and manifest["configuration"]["path"] == "configuration.json","Unexpected collection input path")
    _need(manifest["schedule"] == [query["id"] for query in queries] == configuration["schedule"],"Collection schedule mismatch")
    configured = [event["details"] for event in events if event["event"] == "collection_configured"]
    _need(len(configured) == 1 and canonical(configured[0]) == canonical({"configuration":manifest["configuration"],"scheduled":len(queries)}),"Collection configuration/journal mismatch")
    for key in ("queries","policy","stage_seconds","code_pins"):
        _need(canonical(manifest[key]) == canonical(configuration[key]),"Collection configuration mismatch")
    policy = retrieval.validate_policy(manifest["policy"])
    _need(type(manifest["stage_seconds"]) in (int,float) and math.isfinite(manifest["stage_seconds"]) and 0<manifest["stage_seconds"]<=86400,"Invalid sealed stage budget")
    _need(canonical(_inventory(root)) == canonical(manifest["outputs"]),"Collection output inventory mismatch")
    try:
        cutoff = datetime.fromisoformat(manifest["cutoff"])
        _need(cutoff.tzinfo is not None,"Availability cutoff needs timezone")
    except (TypeError,ValueError) as exc:
        raise ContractError("Invalid collection availability cutoff") from exc
    terminals = [event["details"] for event in events if event["event"] == "collection_case_terminal"]
    reservations = [event["details"] for event in events if event["event"] == "collection_case_reserved"]
    expected_reservations = [{"id":case["id"],"ordinal":case["ordinal"],"query_sha256":case["query_sha256"],
                              "maximum_body_bytes":policy["total_bytes"]} for case in manifest["cases"] if case["started_at_utc"] is not None]
    _need(canonical(reservations) == canonical(expected_reservations),"Collection reservation/journal mismatch")
    _need(len(terminals) == len(queries) == len(manifest["cases"]),"Missing scheduled case dispositions")
    incomplete_seen = False
    for ordinal,(query,case,terminal) in enumerate(zip(queries,manifest["cases"],terminals)):
        _need(_now() < deadline,"Collection verification deadline exceeded")
        _need(case["id"] == query["id"] and case["ordinal"] == ordinal and case["query_sha256"] == _sha(canonical(query)),"Case/query identity mismatch")
        _need(case["status"] in STATES,"Unknown collection disposition")
        _need(terminal["id"] == case["id"] and terminal["ordinal"] == ordinal and terminal["status"] == case["status"],"Case/journal identity mismatch")
        _need(terminal["case"]["path"] == f"cases/{ordinal:03d}/case.json" and canonical(parse_json(_read_proof(root,terminal["case"]))) == canonical(case),"Case/journal content mismatch")
        _need(datetime.fromisoformat(case["sealed_at_utc"]) <= cutoff,"Availability cutoff precedes case seal")
        if incomplete_seen:
            _need(case["status"] == "unexecuted","Dispatch continued after terminal failure")
        if case["status"] != "completed":
            incomplete_seen = True
            _need(case["reason"] is not None,"Missing incomplete-case reason")
            if case["status"] == "unexecuted":
                _need(case["byte_accounting"] == _empty_accounting() and case["retrieval"] is None and case["task_sources"] is None and case["selected"] is None,"Unexecuted case has acquisition output")
            else:
                _need(case["selected"] is None and case["task_sources"] is None and case["coverage"] is None
                      and case["byte_accounting"] == {"known_response_body_bytes":0,"unknown_transfer_upper_bytes":policy["total_bytes"],
                      "safety_accounted_bytes":policy["total_bytes"],"selected_text_bytes":0,"basis":"conservative_whole_case_reservation_until_source_seal"},
                      "Incomplete source operation is missing its conservative reservation")
            continue
        _need(case["effective_policy"] is not None and case["retrieval"]["path"] == f"cases/{ordinal:03d}/retrieval","Invalid case retrieval grant")
        effective = retrieval.validate_policy(case["effective_policy"])
        for key in policy:
            _need(effective[key] <= policy[key] if key in ("question_seconds","request_seconds") else canonical(effective[key]) == canonical(policy[key]),"Case policy changed")
        retr_root = safe_child(root,case["retrieval"]["path"])
        verified = retrieval.verify_retrieval(retr_root,case["retrieval"]["manifest_sha256"],query["question"])
        _need(canonical(verified["policy"]) == canonical(effective),"Case source policy mismatch")
        selected = retrieval.select_passages(verified,query["question"])
        _need(case["selected"]["path"] == f"cases/{ordinal:03d}/selected.json" and canonical(parse_json(_read_proof(root,case["selected"]))) == canonical(selected),"Selected passage binding mismatch")
        _need(case["task_sources"]["path"] == f"cases/{ordinal:03d}/sources.json" and canonical(parse_json(_read_proof(root,case["task_sources"]))) == canonical(selected["sources"]),"Task source packet mismatch")
        expected_accounting = {"known_response_body_bytes":verified["costs"]["downloaded_bytes"],
            "unknown_transfer_upper_bytes":verified["costs"]["unmeasured_transfer_upper_bytes"],
            "safety_accounted_bytes":verified["costs"]["safety_accounted_bytes"],"selected_text_bytes":selected["coverage"]["selected_text_bytes"],
            "basis":"verified_retrieval_and_passage_outputs"}
        _need(case["byte_accounting"] == expected_accounting,"Case transfer accounting mismatch")
        expected_coverage = {"retained_articles":len(verified["sources"]),"selected_passages":len(selected["sources"]),
            "source_coverage":verified["coverage"],"passage_coverage":selected["coverage"],"retrieval_failures":len(verified["failures"]),"absence_of_evidence_claim":False}
        _need(canonical(case["coverage"]) == canonical(expected_coverage),"Case coverage mismatch")
        for request in verified["requests"]:
            if request["status"] == "completed":
                receipt = parse_json(data_views.bounded_bytes(safe_child(retr_root,request["receipt_path"]),65536))
                _need(datetime.fromisoformat(receipt["completed_at_utc"]) <= cutoff,"Availability cutoff precedes source receipt")
    _need(canonical(manifest["totals"]) == canonical(_totals(manifest["cases"])),"Collection total accounting mismatch")
    for key in ("wall_seconds","controller_cpu_seconds"):
        value=manifest["resources"][key]
        _need(type(value) in (int,float) and math.isfinite(value) and value>=0,"Invalid collection resource measurement")
    _need(manifest["resources"]["provider_usd"] == 0.0,"Unexpected provider charge")
    if manifest["status"] == "completed":
        _need(manifest["resources"]["wall_seconds"] < manifest["stage_seconds"],"Completed collection exceeds its stage budget")
    _need((manifest["status"] == "completed") == (manifest["fatal"] is None and all(case["status"] == "completed" for case in manifest["cases"])),"False collection completion status")
    return freeze(manifest)


def inspect_collection(root):
    """Inspect a forcibly interrupted directory without acquiring or repairing."""
    root = Path(root).resolve()
    events = read_chain(safe_child(root,"journal.jsonl"),allow_incomplete_tail=True)
    config_path = safe_child(root,"configuration.json")
    if not config_path.is_file():
        return freeze({"status":"incomplete_before_schedule","last_event":events[-1]["event"],"cases":[],"recovery":"inspect only"})
    configured = [event["details"] for event in events if event["event"] == "collection_configured"]
    _need(len(configured) == 1,"Configuration has no durable journal anchor")
    config = parse_json(_read_proof(root,configured[0]["configuration"]))
    started = {event["details"]["id"] for event in events if event["event"] == "collection_case_reserved"}
    terminals = {event["details"]["id"]:event["details"] for event in events if event["event"] == "collection_case_terminal"}
    cases = []
    for ordinal,ident in enumerate(config["schedule"]):
        if ident in terminals:
            case = parse_json(_read_proof(root,terminals[ident]["case"]))
            _need(case["id"] == ident and case["ordinal"] == ordinal,"Inspection case identity mismatch")
            cases.append(case)
        else:
            cases.append({"id":ident,"ordinal":ordinal,"status":"interrupted" if ident in started else "unexecuted",
                          "reason":"no_durable_case_terminal","retry_authorized":False})
    return freeze({"status":"seal_present_unverified" if (root/"SEALED.json").is_file() else "incomplete",
                   "last_event":events[-1]["event"],"cases":cases,"recovery":"inspection only; no automatic retries or resume"})


def main(argv=None):
    global _PROCESS_DEADLINE
    process_started = _now()
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries",required=True,type=Path)
    parser.add_argument("--query-sha256",required=True)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--policy",required=True,type=Path)
    parser.add_argument("--policy-sha256",required=True)
    parser.add_argument("--stage-seconds",required=True,type=float)
    args = parser.parse_args(argv)
    _need(type(args.stage_seconds) is float and math.isfinite(args.stage_seconds) and 0<args.stage_seconds<=86400,"Invalid CLI stage budget")
    _PROCESS_DEADLINE = process_started+args.stage_seconds
    from .runtime import contain_process_tree,empty_import_cache
    empty_import_cache()
    _job_handle = contain_process_tree()  # retain until process exit; never manually close
    policy_raw = data_views.bounded_bytes(args.policy,65536)
    _need(_sha(policy_raw) == args.policy_sha256,"CLI policy hash mismatch")
    policy = retrieval.validate_policy(parse_json(policy_raw))
    manifest = collect(args.queries,args.query_sha256,args.output,policy,stage_seconds=args.stage_seconds)
    print(canonical({"status":manifest["status"],"scheduled":len(manifest["schedule"]),
        "manifest_sha256":_sha(data_views.bounded_bytes(args.output/"manifest.json",MAX_COLLECTION_JSON))}).decode())
    return 0 if manifest["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
