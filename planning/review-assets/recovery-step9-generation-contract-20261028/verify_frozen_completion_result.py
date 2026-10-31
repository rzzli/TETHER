"""Independent result-only verification; never invokes metadata/archive replays.

Reads the root-notified terminal result and exact external hashes. Imports only
stdlib and accepted installed0.3.10 read/journal primitives. Writes two new audit
files outside the execution's pinned inventory; target code is never executed.
"""
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import sys
import time

from asof.journal import read_chain
from asof.serde import encode
from asof.study.stable_read import deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL = HERE / "FROZEN-COMPLETION-PROTOCOL-v3.json"
PROTOCOL_SHA = "75b44d1b2bfbafb7910d8e894d77dba550aae4970b1c5931bcaa9e7f6da34087"
COMBINED = HERE / "FROZEN-VERIFIER-COMBINED.json"
COMBINED_SHA = "17afefc0ac2b83c76bc8974c68a366ea779379fb42199911c494da5967d9d5eb"
PRIMARY_SHA = "c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50"
FAILURE_SHA = "f1824a909e74a94a28de5562fbf40b4175e1e337890f0eaa3e792ab021805229"
OUTPUT = ROOT / "data/cache/r09-generation-frozen-completion-20261028"
REPORT = HERE / "FROZEN-COMPLETION-RESULT-VERIFICATION.json"
DOCUMENT = HERE / "FROZEN-COMPLETION-RESULT-VERIFICATION.md"
VERSIONS = ["031", "032", "033", "034", "035", "036", "037", "038", "039", "0310"]
REMAINING = VERSIONS[7:]
META_CODE = ("from importlib.metadata import version; import sys,json; actual=version('asof-target-agents'); "
             "print(json.dumps({'actual':actual,'expected':sys.argv[1],'isolated':bool(sys.flags.isolated)})); "
             "sys.exit(0 if actual==sys.argv[1] and sys.flags.isolated else 2)")


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def pinned(item, deadline):
    actual = encode(hash_file(item["path"], deadline))
    need(actual["sha256"] == item["sha256"], "Digest mismatch: " + item["path"])
    if "bytes" in item:
        need(actual["bytes"] == item["bytes"], "Size mismatch: " + item["path"])
    return dict(path=item["path"], **actual)


def guarded_payload(payload, expected_status):
    need(payload["status"] == expected_status, "Verifier result is not its expected passed status")
    for key, value in payload.items():
        if key == "guards" or key.endswith("attempts"):
            need(all(v == [] for v in value.values()) if isinstance(value,dict) else value == [], "Nonempty verifier guards")
    for obj in (payload, payload.get("result",{})):
        for key in ("actual_model_calls","native_processes","model_calls","tokenizer_calls","network_calls"):
            if isinstance(obj,dict) and key in obj:
                need(obj[key] == 0, "Unexpected actual call count")


def main():
    need(sys.flags.isolated and metadata.version("asof-target-agents") == "0.3.10", "Use isolated accepted installed0.3.10 audit host")
    need(not REPORT.exists() and not DOCUMENT.exists(), "Preserve existing independent verification")
    started = time.monotonic()
    deadline = started + 120
    result = dict(schema_version=1,status="failed",scope="independent_terminal_artifact_checks_not_replay",
        combined_sha256=COMBINED_SHA,protocol_sha256=PROTOCOL_SHA,actual_children=0,metadata_reruns=0,
        archive_replays=0,native_target_calls=0,model_calls=0,original_primary_rewritten=False,
        native_conformance="unverified",scientific_validation="not_attempted",checks={},child_attempts=[])
    try:
        need(sha(PROTOCOL) == PROTOCOL_SHA and sha(COMBINED) == COMBINED_SHA, "Root external protocol/combined anchor mismatch")
        protocol = json.loads(PROTOCOL.read_bytes())
        combined = json.loads(COMBINED.read_bytes())
        need(protocol["preparation_revision"] == 3 and len(protocol["pinned_files"]) == 462, "Wrong completed protocol")
        need(Path(sys.executable).resolve() == Path(protocol["accepted_parent"]["installed_python"]).resolve(), "Wrong audit interpreter")
        need(combined["status"] == "verified_all_ten_matching_installed_versions_across_retained_attempts", "Combined status is not qualified")
        need([row["version"] for row in combined["records"]] == VERSIONS, "Combined version identities differ")
        need(not (OUTPUT/"failure.json").exists(), "Authoritative completion failure present")
        completion_path = Path(combined["completion_attempt"]["report"]["path"])
        completion = json.loads(completion_path.read_bytes())
        primary = json.loads(Path(combined["primary_attempt"]["path"]).read_bytes())
        checkpoint = json.loads(Path(combined["source_checkpoint"]["path"]).read_bytes())
        extras = [PROTOCOL,COMBINED,completion_path,OUTPUT/"journal.jsonl",OUTPUT/"effective-protocol.json"]
        for row in completion["records"]:
            extras.append(Path(row["report"]))
            for stage in ("metadata","replay"):
                extras.extend([OUTPUT/(row["version"]+"-"+stage+"-attempt.json"),
                    Path(row[stage]["stdout"]["path"]),Path(row[stage]["stderr"]["path"])])
        paths = [Path(item["path"]) for item in protocol["pinned_files"]] + extras
        with stable_files(paths,deadline=deadline):
            for item in protocol["pinned_files"]:
                pinned(item,deadline)
            result["checks"]["execution_pins_rehashed"] = 462
            need(sha(PROTOCOL) == PROTOCOL_SHA and sha(COMBINED) == COMBINED_SHA, "Terminal anchors changed during lease acquisition")
            need(sha(combined["primary_attempt"]["path"]) == PRIMARY_SHA
                 and sha(combined["primary_attempt"]["failure"]["path"]) == FAILURE_SHA, "Original failed attempt changed")
            need(primary["status"] == combined["primary_attempt"]["status"] == "failed_or_incomplete"
                 and primary["failure"]["error_class"] == "TimeoutExpired"
                 and combined["primary_attempt"]["failed_at_version"] == "038"
                 and combined["primary_attempt"]["outcome_preserved"], "Original timeout was not retained as failed")
            need(combined["records"][:7] == primary["records"][:7] == protocol["reused_records"], "Original seven records were altered")
            result["checks"]["failed_primary_preserved"] = True
            result["checks"]["retained_success_records_unchanged"] = 7
            for key in ("protocol","report","journal"):
                pinned(combined["completion_attempt"][key],deadline)
            need(combined["completion_attempt"]["protocol"]["sha256"] == PROTOCOL_SHA
                 and combined["completion_attempt"]["failure_marker"] == str(OUTPUT/"failure.json"), "Completion binding differs")
            need(sha(OUTPUT/"effective-protocol.json") == PROTOCOL_SHA, "Effective protocol differs")
            need(completion["status"] == "verified_remaining_three_matching_installed_versions"
                 and "failure" not in completion and completion["protocol_sha256"] == PROTOCOL_SHA
                 and completion["limits"] == protocol["limits"]
                 and completion["source_pins_unchanged"] == 327 and completion["retained_success_reports_rechecked"] == 7,
                 "Completion report is incomplete or failed")
            need(combined["records"][7:] == completion["records"] and [r["version"] for r in completion["records"]] == REMAINING,
                 "Remaining-three result records differ")
            for field in ("elapsed_seconds","elapsed_seconds_before_finalization"):
                need(type(completion[field]) in (int,float) and math.isfinite(completion[field]) and 0 <= completion[field] < 1200,
                     "Aggregate verification timing invalid")
            for row in combined["records"]:
                deadline_check(deadline)
                need(sha(row["report"]) == row["report_sha256"] and sha(row["helper"]) == row["helper_sha256"]
                     and sha(row["python"]) == row["python_sha256"], "Combined report/helper/interpreter identity changed")
                guarded_payload(json.loads(Path(row["report"]).read_bytes()),row["expected_status"])
                need(row["status"] == row["expected_status"], "Unpassed combined version")
            result["checks"]["matching_reports_helpers_interpreters"] = 10
            need(len(checkpoint["source_pins"]) == 327 and combined["source_checkpoint"]["unchanged"], "Wrong source checkpoint")
            for relative, expected in checkpoint["source_pins"].items():
                need(hash_file(ROOT/relative,deadline)["sha256"] == expected,"Working source changed: "+relative)
            result["checks"]["current_source_pins_rehashed"] = 327
            events = encode(read_chain(OUTPUT/"journal.jsonl"))
            expected_events = ["build_reserved","completion_protocol_reserved"]
            for version in REMAINING:
                expected_events.extend(["completion_child_attempt","completion_child_started","completion_child_terminal"])
            expected_events.append("completion_remaining_metadata_verified")
            for version in REMAINING:
                expected_events.extend(["completion_child_attempt","completion_child_started","completion_child_terminal","completion_version_verified"])
            expected_events.extend(["completion_remaining_three_verified","completion_attempt_terminal"])
            need([event["event"] for event in events] == expected_events, "Journal stage/order or failure differs")
            need(events[-1]["details"]["status"] == completion["status"], "Journal terminal status differs")
            attempts = [event["details"] for event in events if event["event"]=="completion_child_attempt"]
            starts = [event["details"] for event in events if event["event"]=="completion_child_started"]
            terminals = [event["details"] for event in events if event["event"]=="completion_child_terminal"]
            expected_stages = [(version,stage) for stage in ("metadata","replay") for version in REMAINING]
            need([(item["version"],item["stage"]) for item in terminals] == expected_stages,"Child stage identities differ")
            row_map = {row["version"]:row for row in completion["records"]}
            template_map = {row["version"]:row for row in protocol["records"]}
            for attempt, birth, terminal in zip(attempts,starts,terminals):
                version,stage = terminal["version"],terminal["stage"]
                row,template = row_map[version],template_map[version]
                need(all(row[key]==value for key,value in template.items()),"Completion request/options changed")
                need(row[stage] == terminal and birth["pid"] == terminal["pid"] and type(terminal["pid"]) is int and terminal["pid"]>0,
                     "Child PID/record/journal mismatch")
                for key in ("version","stage","argv","cwd","started_at_utc","declared_seconds","effective_seconds"):
                    need(attempt[key] == terminal[key], "Attempt/terminal immutable fields differ")
                need(terminal["spawned"] and terminal["reaped"] and terminal["returncode"]==0
                     and not terminal["timed_out"] and not terminal["capture_overflow"] and not terminal["cleanup_errors"],"Child failed or cleanup incomplete")
                cap = 10 if stage=="metadata" else 360
                need(terminal["declared_seconds"]==cap and 0 < terminal["effective_seconds"] <= cap
                     and 0 <= terminal["full_process_elapsed_seconds"] <= terminal["effective_seconds"],"Whole-process child limit exceeded")
                argv = [row["python"],"-I","-c",META_CODE,row["expected_version"]] if stage=="metadata" else [row["python"],"-I",row["helper"],*row["args"]]
                need(terminal["argv"]==argv and terminal["cwd"]==str(ROOT),"Child argv/input scope changed")
                attempt_path = OUTPUT/(version+"-"+stage+"-attempt.json")
                need(json.loads(attempt_path.read_bytes())==terminal,"Attempt file differs from hash-chained terminal")
                logs = {}
                for name in ("stdout","stderr"):
                    logs[name] = pinned(terminal[name],deadline)
                    stream = terminal["streams"][name]
                    need(not stream["truncated"] and stream["error_class"] is None
                         and stream["retained_bytes"] == stream["observed_bytes_at_least"] == logs[name]["bytes"] <= 1048576,
                         "Capture accounting/hash mismatch")
                need(logs["stderr"]["bytes"]==0,"Unreviewed child stderr diagnostics")
                stdout = json.loads(Path(logs["stdout"]["path"]).read_bytes())
                if stage=="metadata":
                    need(stdout==dict(actual=row["expected_version"],expected=row["expected_version"],isolated=True),"Metadata assertion result differs")
                else:
                    need(stdout["status"]==row["status"],"Replay stdout status differs")
                result["child_attempts"].append(dict(version=version,stage=stage,pid=terminal["pid"],reaped=True,
                    full_process_elapsed_seconds=terminal["full_process_elapsed_seconds"],declared_seconds=cap,
                    attempt=dict(path=str(attempt_path),sha256=sha(attempt_path)),logs=logs))
            need(len(result["child_attempts"])==6,"Missing child attempt")
            need(not (OUTPUT/"failure.json").exists(),"Late authoritative failure marker")
            result["checks"].update(journal_chain_events=len(events),child_attempts_and_log_pairs=6,metadata_checks_retained=3,
                completed_replays_retained=3,guard_attempts_empty=True,completion_failure_marker_absent=True)
            result.update(status="passed_independent_completion_result_verification",
                original_primary=dict(path=combined["primary_attempt"]["path"],sha256=PRIMARY_SHA,status="failed_or_incomplete",failure_sha256=FAILURE_SHA),
                completion_report=pinned(combined["completion_attempt"]["report"],deadline),
                journal=pinned(combined["completion_attempt"]["journal"],deadline),
                source_checkpoint=pinned(combined["source_checkpoint"],deadline),
                completion_elapsed_seconds_before_finalization=completion["elapsed_seconds_before_finalization"])
        deadline_check(deadline)
    except BaseException as error:
        result.update(status="failed_independent_completion_result_verification",failure=dict(error_class=type(error).__name__,message=str(error)))
    result["elapsed_seconds"] = time.monotonic()-started
    result["verifier_sha256"] = sha(__file__)
    with REPORT.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2)
        stream.write("\n")
    good = result["status"]=="passed_independent_completion_result_verification"
    text = ("# Independent recovery-result verification\n\n"
        +("Passed" if good else "Failed")+" result-only verification on 28 October 2026 UTC.\n\n"
        +"The root-supplied combined SHA-256 is `"+COMBINED_SHA+"`. Checks covered all 462 execution pins, "
        "327 current source files, the exact seven retained plus three new records, six owned-child attempt/log pairs, "
        "the 26-event journal chain, identities, process limits, empty guards and absence of a completion failure marker. "
        "The original failed attempt remains failed and unchanged.\n\n"
        +"See [machine result](FROZEN-COMPLETION-RESULT-VERIFICATION.json) for hashes, measured child intervals and checks. "
        "This verifier performed no metadata checks, archive replays, target-native/model calls or scientific evaluation. "
        "It checks retained evidence after root's terminal notification; it does not attest OS process behavior independently. "
        "Milestone acceptance remains root's separate decision.\n")
    if not good:
        text += "\nFailure: `"+result["failure"]["error_class"]+"`: "+result["failure"]["message"]+"\n"
    with DOCUMENT.open("x",encoding="utf-8") as stream:
        stream.write(text)
    print(json.dumps(dict(status=result["status"],checks=result["checks"],elapsed_seconds=result["elapsed_seconds"],failure=result.get("failure"))))
    return 0 if good else 1


if __name__=="__main__":
    raise SystemExit(main())
