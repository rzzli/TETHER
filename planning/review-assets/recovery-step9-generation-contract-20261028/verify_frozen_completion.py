"""Amendment-2 preparation and once-only completion of 038/039/0310.

Uses only the accepted installed0.3.10 parent. --prepare dispatches nothing;
--execute requires independent review of the resulting protocol SHA256.
The failed primary attempt and seven successful records are never rewritten.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode
from asof.study.stable_read import deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIMARY = HERE / "FROZEN-VERIFIER-CHECKS.json"
PRIMARY_SHA = "c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50"
FAILURE = ROOT / "data/cache/r09-generation-frozen-20261028/failure.json"
FAILURE_SHA = "f1824a909e74a94a28de5562fbf40b4175e1e337890f0eaa3e792ab021805229"
CHECKPOINT = ROOT / "data/cache/recovery-step9-generation-validation-20261028/code-validation.json"
CHECKPOINT_SHA = "de5b773c4d2e6ff093b87e8ba1d16e10911f188147d08d17d0823b9c228bfc57"
AMENDMENT = HERE / "AMENDMENT-2-FROZEN-VERIFICATION-RECOVERY.md"
AMENDMENT_SHA = "1bf138d7209bc88b2d4eb7e8e6d6daec89c9a9c332b742d5cecff6f6fe4de74c"
DECISION = HERE / "AMENDMENT-2-ROOT-DECISION.json"
DECISION_SHA = "1c39b715310bae31926403b5b2a723ba4564ec71472eee58f479d31d93db0af6"
ACCEPTED = HERE.parent / "recovery-step9-native-grammar-20261028/FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json"
ACCEPTED_SHA = "a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0"
PROTOCOL = HERE / "FROZEN-COMPLETION-PROTOCOL.json"
OUTPUT = ROOT / "data/cache/r09-generation-frozen-completion-20261028"
REPORT = OUTPUT / "completion-report.json"
COMBINED = HERE / "FROZEN-VERIFIER-COMBINED.json"
VERSIONS = {"038": "0.3.8", "039": "0.3.9", "0310": "0.3.10"}
REUSED = ["031", "032", "033", "034", "035", "036", "037"]
LIMITS = dict(per_replay_seconds=360, metadata_seconds=10, aggregate_seconds=1200,
              finalization_reserve_seconds=30, max_stdout_bytes=1048576, max_stderr_bytes=1048576,
              maximum_metadata_children=3, maximum_replay_children=3, scientific_case_seconds_unchanged=300)


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def payload_ok(payload, row):
    need(payload["status"] == row["expected_status"], "Unexpected verifier status: " + row["version"])
    for key, value in payload.items():
        if key == "guards" or key.endswith("attempts"):
            values = value.values() if isinstance(value, dict) else (value,)
            need(all(v == [] for v in values), "Guard attempts: " + row["version"])
    for obj in (payload, payload.get("result", {})):
        if isinstance(obj, dict):
            for key in ("actual_model_calls", "native_processes", "model_calls", "tokenizer_calls", "network_calls"):
                if key in obj:
                    need(obj[key] == 0, "Unexpected actual calls: " + row["version"])


def authorities():
    need(sys.flags.isolated and metadata.version("asof-target-agents") == "0.3.10", "Use isolated accepted installed0.3.10 parent")
    for path, expected in ((PRIMARY, PRIMARY_SHA), (FAILURE, FAILURE_SHA), (CHECKPOINT, CHECKPOINT_SHA),
                           (AMENDMENT, AMENDMENT_SHA), (DECISION, DECISION_SHA), (ACCEPTED, ACCEPTED_SHA)):
        need(sha(path) == expected, "Changed authority: " + str(path))
    accepted = json.loads(ACCEPTED.read_bytes())["accepted_software"]
    need(Path(sys.executable).resolve() == Path(accepted["installed_python"]).resolve(), "Wrong accepted parent interpreter")
    decision = json.loads(DECISION.read_bytes())
    need(decision["remaining_versions"] == list(VERSIONS) and decision["reused_success_versions"] == REUSED
         and decision["whole_process_seconds_each"] == 360 and decision["aggregate_verification_seconds"] == 1200,
         "Wrong amendment decision")
    primary = json.loads(PRIMARY.read_bytes())
    need(primary["status"] == "failed_or_incomplete" and primary["failure"]["error_class"] == "TimeoutExpired"
         and primary["failure"]["completed_versions"] == REUSED, "Original attempt must remain failed")
    need([r["version"] for r in primary["records"]] == REUSED + list(VERSIONS), "Original version set changed")
    checkpoint = json.loads(CHECKPOINT.read_bytes())
    need(len(checkpoint["source_pins"]) == 327, "Wrong source checkpoint")
    return primary, checkpoint, accepted


def retained_ok(primary, checkpoint, deadline):
    for original in primary["records"][:7]:
        deadline_check(deadline)
        need(sha(original["report"]) == original["report_sha256"], "Changed retained successful report")
        need(sha(original["helper"]) == original["helper_sha256"] and sha(original["python"]) == original["python_sha256"],
             "Changed retained helper/interpreter")
        need(original["status"] == original["expected_status"], "Retained record was not passed")
        payload_ok(json.loads(Path(original["report"]).read_bytes()), original)
    for relative, expected in checkpoint["source_pins"].items():
        deadline_check(deadline)
        need(sha(ROOT / relative) == expected, "Changed working source: " + relative)


def prepare():
    primary, checkpoint, accepted = authorities()
    need(not PROTOCOL.exists() and not OUTPUT.exists() and not COMBINED.exists(), "Existing completion protocol/output; no replacement")
    rows = []
    files = [pin(path) for path in (PRIMARY, FAILURE, CHECKPOINT, AMENDMENT, DECISION, ACCEPTED,
             HERE / "FROZEN-VERIFIER-ATTEMPT.json", HERE / "verify_frozen_all.py", __file__, sys.executable)]
    files.extend(accepted["installed_files"])
    files.extend([accepted["wheel"], accepted["acceptance"]])
    files.extend(pin(ROOT / relative) for relative in checkpoint["source_pins"])
    for original in primary["records"]:
        need(sha(original["helper"]) == original["helper_sha256"] and sha(original["python"]) == original["python_sha256"],
             "Original matching helper/interpreter changed")
        files.extend([pin(original["helper"]), pin(original["python"])])
        if original["version"] in REUSED:
            files.append(pin(original["report"]))
    for original in primary["records"][7:]:
        version = original["version"]
        args = list(original["args"])
        if version == "038":
            report = OUTPUT / version / "guarded-installed-verification.json"
            args[-1] = str(report)
            for name in ("materialization.json", "envelope.json"):
                files.append(pin(Path(args[0]) / name))
        else:
            report = OUTPUT / (version + "-report.json")
            args[0], args[1] = str(report), str(OUTPUT / version)
            helper_phase = Path(original["helper"]).parent
            for name in ("SIMULATION-QUALIFICATION.json", "SIMULATION-PROTOCOL.json", "NATIVE-MODEL-MIRROR.json"):
                files.append(pin(helper_phase / name))
            inputs = json.loads((helper_phase / "SIMULATION-PROTOCOL.json").read_bytes())
            files.append(pin(ROOT / inputs["source_authority"]["path"]))
        need(not report.exists(), "Fresh report exists")
        rows.append(dict(version=version, expected_version=VERSIONS[version], python=original["python"],
            python_sha256=original["python_sha256"], helper=original["helper"], helper_sha256=original["helper_sha256"],
            args=args, primary_args=original["args"], report=str(report), expected_status=original["expected_status"],
            replay_timeout_seconds=360))
    files = list({os.path.normcase(item["path"]): item for item in files}.values())
    need(len(files) <= 500 and sum(item["bytes"] for item in files) <= 32 * 1024 * 1024, "Completion pin inventory exceeds scope")
    deadline = time.monotonic() + 60
    with stable_files([Path(item["path"]) for item in files], deadline=deadline):
        for item in files:
            need(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Preparation pin changed")
        retained_ok(primary, checkpoint, deadline)
        protocol = dict(schema_version=1, kind="remaining_three_matching_installed_verifiers_v1", execution_authorized=False,
            helper=pin(__file__), amendment=pin(AMENDMENT), root_decision=pin(DECISION),
            failed_primary=pin(PRIMARY), primary_failure=pin(FAILURE), source_checkpoint=pin(CHECKPOINT), source_pin_count=327,
            accepted_parent=accepted, pinned_files=files, reused_versions=REUSED, reused_records=primary["records"][:7],
            remaining_versions=list(VERSIONS), records=rows, limits=LIMITS, cwd=str(ROOT), output=str(OUTPUT),
            completion_report=str(REPORT), combined_report=str(COMBINED),
            reused_reports_never_rerun=True, input_scope="unchanged helper arguments and receipt-bound authority manifests; original helpers replay full original inputs",
            original_primary_outcome="failed at0.3.8 outer timeout; retained unchanged", restart_allowed=False)
        write_new(PROTOCOL, protocol)
    print(json.dumps(dict(status="prepared_no_children", protocol=str(PROTOCOL), protocol_sha256=sha(PROTOCOL),
                         pinned_files=len(files), metadata_children=0, replay_children=0)))


def run_child(row, stage, argv, cap, journal, deadline):
    start = time.monotonic()
    end = min(start + cap, deadline - LIMITS["finalization_reserve_seconds"])
    deadline_check(end)
    record = dict(version=row["version"], stage=stage, argv=argv, cwd=str(ROOT),
        started_at_utc=datetime.now(timezone.utc).isoformat(), pid=None, spawned=False,
        declared_seconds=cap, effective_seconds=end-start, timed_out=False, reaped=False,
        capture_overflow=False, cleanup_errors=[], streams={})
    row[stage] = record
    process, threads, stop = None, [], Event()
    captures = ExitStack()
    try:
        journal.append("completion_child_attempt", **record)
        sinks = {name: captures.enter_context((OUTPUT / (row["version"] + "-" + stage + "." + name + ".log")).open("xb"))
                 for name in ("stdout", "stderr")}
        def drain(name, pipe):
            item = record["streams"][name]
            try:
                while True:
                    data = pipe.read(65536)
                    if not data:
                        break
                    item["observed_bytes_at_least"] += len(data)
                    remaining = LIMITS["max_" + name + "_bytes"] - item["retained_bytes"]
                    if remaining:
                        sinks[name].write(data[:remaining])
                        item["retained_bytes"] += min(remaining, len(data))
                    if len(data) > remaining:
                        item["truncated"] = True
                        stop.set()
                        break
            except BaseException as error:
                item["error_class"] = type(error).__name__
                stop.set()
            finally:
                try:
                    sinks[name].flush()
                    os.fsync(sinks[name].fileno())
                except BaseException as error:
                    item["error_class"] = type(error).__name__
                    stop.set()
        process = subprocess.Popen(argv, cwd=ROOT, shell=False, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        record.update(pid=process.pid, spawned=True)
        process.stdin.close()
        journal.append("completion_child_started", version=row["version"], stage=stage, pid=process.pid)
        for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
            record["streams"][name] = dict(retained_bytes=0, observed_bytes_at_least=0, truncated=False, error_class=None)
            thread = Thread(target=drain, args=(name, pipe), daemon=True)
            thread.start()
            threads.append(thread)
        while process.poll() is None:
            if stop.is_set() or time.monotonic() >= end:
                record["timed_out"] = time.monotonic() >= end
                process.kill()
                break
            time.sleep(0.02)
        process.wait(timeout=max(0.1, min(5, deadline-time.monotonic())))
        record["reaped"] = True
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=max(0.1, min(5, deadline-time.monotonic())))
                record.update(reaped=True, returncode=process.poll())
            except BaseException as error:
                record["cleanup_errors"].append(type(error).__name__)
            for thread in threads:
                thread.join(timeout=max(0.1, min(3, deadline-time.monotonic())))
            if any(thread.is_alive() for thread in threads):
                record["cleanup_errors"].append("CaptureThreadUnresolved")
            for pipe in (process.stdout, process.stderr):
                if pipe is not None and not any(thread.is_alive() for thread in threads):
                    pipe.close()
        try:
            captures.close()
        except BaseException as error:
            record["cleanup_errors"].append(type(error).__name__)
        record["full_process_elapsed_seconds"] = time.monotonic()-start
        record["capture_overflow"] = any(item["truncated"] for item in record["streams"].values())
        for name in ("stdout", "stderr"):
            path = OUTPUT / (row["version"] + "-" + stage + "." + name + ".log")
            if path.exists():
                record[name] = pin(path)
        write_new(OUTPUT / (row["version"] + "-" + stage + "-attempt.json"), record)
        journal.append("completion_child_terminal", **record)
    need(record["spawned"] and record["reaped"] and record.get("returncode") == 0
         and not record["timed_out"] and not record["capture_overflow"] and not record["cleanup_errors"]
         and not any(item["error_class"] for item in record["streams"].values()), "Child failed: " + row["version"] + " " + stage)
    deadline_check(deadline-LIMITS["finalization_reserve_seconds"])


def execute(expected):
    primary, checkpoint, _ = authorities()
    need(sha(PROTOCOL) == expected, "External completion-protocol hash differs")
    protocol = json.loads(PROTOCOL.read_bytes())
    need(protocol["kind"] == "remaining_three_matching_installed_verifiers_v1" and protocol["limits"] == LIMITS
         and protocol["helper"]["sha256"] == sha(__file__) and protocol["reused_records"] == primary["records"][:7]
         and protocol["remaining_versions"] == list(VERSIONS) and protocol["reused_versions"] == REUSED
         and [row["version"] for row in protocol["records"]] == list(VERSIONS) and protocol["output"] == str(OUTPUT)
         and protocol["combined_report"] == str(COMBINED), "Completion protocol changed")
    need(not OUTPUT.exists() and not COMBINED.exists(), "Completion attempt consumed; no automatic restart")
    for row, original in zip(protocol["records"], primary["records"][7:]):
        need(all(row[key] == original[key] for key in ("version", "python", "python_sha256", "helper", "helper_sha256", "expected_status"))
             and row["primary_args"] == original["args"], "Remaining verifier identity or original arguments changed")
        expected_args = list(original["args"])
        if row["version"] == "038":
            report = OUTPUT / "038/guarded-installed-verification.json"
            expected_args[-1] = str(report)
        else:
            report = OUTPUT / (row["version"] + "-report.json")
            expected_args[0], expected_args[1] = str(report), str(OUTPUT / row["version"])
        need(row["args"] == expected_args and row["report"] == str(report), "Only approved new output paths may differ")
    journal = RunJournal(OUTPUT, kind="build")
    start, failure = time.monotonic(), None
    deadline = start + LIMITS["aggregate_seconds"]
    rows = protocol["records"]
    summary = dict(schema_version=1, status="failed_or_incomplete", protocol_sha256=expected,
        primary_attempt_sha256=PRIMARY_SHA, original_primary_status="failed_or_incomplete", records=rows,
        reused_versions=REUSED, source_checkpoint_sha256=CHECKPOINT_SHA, source_pin_count=327,
        limits=LIMITS, verification_only=True, model_calls=0, native_target_calls=0, automatic_restart=False)
    leases = ExitStack()
    try:
        write_new(OUTPUT / "effective-protocol.json", protocol)
        journal.append("completion_protocol_reserved", protocol_sha256=expected, reused_versions=REUSED,
                       remaining_versions=list(VERSIONS), original_primary_sha256=PRIMARY_SHA)
        pins = protocol["pinned_files"] + [pin(PROTOCOL)]
        leases.enter_context(stable_files([Path(item["path"]) for item in pins], deadline=deadline))
        for item in pins:
            need(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Completion input/code pin changed")
        retained_ok(primary, checkpoint, deadline)
        code = ("from importlib.metadata import version; import sys,json; actual=version('asof-target-agents'); "
                "print(json.dumps({'actual':actual,'expected':sys.argv[1],'isolated':bool(sys.flags.isolated)})); "
                "sys.exit(0 if actual==sys.argv[1] and sys.flags.isolated else 2)")
        for row in rows:
            need(row["expected_version"] == VERSIONS[row["version"]], "Wrong explicit installed version")
            run_child(row, "metadata", [row["python"], "-I", "-c", code, row["expected_version"]], 10, journal, deadline)
            row["version_check_exit_code"] = 0
        journal.append("completion_remaining_metadata_verified", versions=list(VERSIONS))
        for row in rows:
            argv = [row["python"], "-I", row["helper"], *row["args"]]
            run_child(row, "replay", argv, 360, journal, deadline)
            payload = json.loads(Path(row["report"]).read_bytes())
            payload_ok(payload, row)
            row.update(argv=argv, exit_code=0, status=payload["status"], report_sha256=sha(row["report"]))
            journal.append("completion_version_verified", version=row["version"], report=row["report"], report_sha256=row["report_sha256"])
            print(json.dumps(dict(version=row["version"], status=row["status"])), flush=True)
        for item in pins:
            need(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Final completion pin changed")
        retained_ok(primary, checkpoint, deadline)
        need(len(rows) == 3 and [row["version"] for row in rows] == list(VERSIONS), "Missing completion version")
        summary.update(status="verified_remaining_three_matching_installed_versions", elapsed_seconds=time.monotonic()-start,
                       source_pins_unchanged=327, retained_success_reports_rechecked=7)
        journal.append("completion_remaining_three_verified", versions=list(VERSIONS))
    except BaseException as error:
        failure = dict(error_class=type(error).__name__, message=str(error))
        summary["failure"] = failure
        journal.fail(error, "matching_installed_completion")
    finally:
        try:
            summary["elapsed_seconds_before_finalization"] = time.monotonic()-start
            if time.monotonic() >= deadline:
                summary["status"] = "failed_aggregate_deadline"
            journal.append("completion_attempt_terminal", status=summary["status"], elapsed_seconds=time.monotonic()-start)
        finally:
            journal.close()
        try:
            if summary["status"] != "verified_remaining_three_matching_installed_versions":
                write_new(OUTPUT / "failure.json", dict(authoritative=True, **summary))
            write_new(REPORT, summary)
            read_chain(OUTPUT / "journal.jsonl")
            deadline_check(deadline)
            if not (OUTPUT / "failure.json").exists():
                retained_ok(primary, checkpoint, deadline)
                records = primary["records"][:7] + rows
                need(len(records) == len({row["version"] for row in records}) == 10, "Combined qualification needs ten distinct versions")
                for row in records:
                    deadline_check(deadline)
                    need(sha(row["report"]) == row["report_sha256"], "Combined report anchor changed")
                combined = dict(schema_version=1,
                    status="verified_all_ten_matching_installed_versions_across_retained_attempts",
                    current_source_version_under_test="0.3.11", verification_only=True, records=records,
                    record_origins={row["version"]: "failed_primary_retained_success" if row["version"] in REUSED else "declared_remaining_three_completion" for row in records},
                    primary_attempt=dict(**pin(PRIMARY), status="failed_or_incomplete", failed_at_version="038", failure=pin(FAILURE), outcome_preserved=True),
                    completion_attempt=dict(protocol=pin(PROTOCOL), report=pin(REPORT), journal=pin(OUTPUT / "journal.jsonl"),
                        status=summary["status"], failure_marker=str(OUTPUT / "failure.json")),
                    source_checkpoint=dict(**pin(CHECKPOINT), source_pins=327, unchanged=True),
                    amendment=pin(AMENDMENT), root_decision=pin(DECISION), scientific_case_budget_seconds_unchanged=300,
                    model_calls=0, native_target_calls=0, automatic_restart=False,
                    authority_rule="Completion failure.json overrides this combined record; original primary attempt remains failed")
                deadline_check(deadline)
                write_new(COMBINED, combined)
                deadline_check(deadline)
        except BaseException as error:
            failure = dict(error_class=type(error).__name__, message=str(error))
            if not (OUTPUT / "failure.json").exists():
                write_new(OUTPUT / "failure.json", dict(status="failed_finalization", authoritative=True, **failure,
                    combined_record_present=COMBINED.exists(), automatic_restart=False))
        finally:
            try:
                leases.close()
            except BaseException as error:
                failure = dict(error_class=type(error).__name__, message=str(error))
                if not (OUTPUT / "failure.json").exists():
                    write_new(OUTPUT / "failure.json", dict(status="failed_lease_cleanup", authoritative=True, **failure,
                        combined_record_present=COMBINED.exists(), automatic_restart=False))
    print(json.dumps(dict(status=summary["status"], authoritative_failure=(OUTPUT / "failure.json").exists(),
        completion_report=str(REPORT), combined_report=str(COMBINED) if COMBINED.exists() else None,
        elapsed_seconds=time.monotonic()-start)))
    return 0 if not failure and not (OUTPUT / "failure.json").exists() and COMBINED.exists() else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif len(sys.argv) == 3 and sys.argv[1] == "--execute":
        raise SystemExit(execute(sys.argv[2]))
    else:
        raise SystemExit("Use --prepare; independently review its hash before --execute SHA256")
