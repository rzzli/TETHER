"""Once-only, bounded replay of ten unchanged matching installed verifiers.

PREPARED ONLY: execute separately after the 0.3.11 source/test freeze. This
operator helper imports no live AsOf source and never starts a native program.
The old helpers retain their original pure-replay input scopes and audit guards.
Their simulated model-file hashing is not weight loading or native execution.
An existing attempt marker forbids automatic restart, including after failure.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "recovery-step9-native-duration-20261028"
PRIOR = OLD / "FROZEN-VERIFIER-CHECKS.json"
PRIOR_SHA256 = "2c6ebaf22c4127a9ed7301acb3844bd55d2a5251cda4d12ba8a1fdf33e451824"
PYTHON_SHA256 = "43a8d6a15c6abed2f42d794b8f28d1c4b0e74bf11d42299304febe145f2ba52d"
CACHE = ROOT / "data/cache/r09-generation-frozen-20261028"
ATTEMPT = HERE / "FROZEN-VERIFIER-ATTEMPT.json"
REPORT = HERE / "FROZEN-VERIFIER-CHECKS.json"
OVERALL_SECONDS = 1200
FINALIZATION_RESERVE_SECONDS = 10
METADATA_SECONDS = 10
# Explicit mapping: 0310 is 0.3.10, never 0.3.0 or the last digit of an ID.
# Replay caps are ceilings; the remaining aggregate deadline can shorten them.
SPECS = {
    "031": ("0.3.1", 300, "6dff899eb75ec49e2a2f0027068ba7ed7e3cdbe7a2967ebe2037b01a71cf9361"),
    "032": ("0.3.2", 30, "045405f728ab70d19b923aac959274610b6259f7ee86695f1bed448f7927ff17"),
    "033": ("0.3.3", 60, "79a01b10c93d64a9c157c521e3d2fed81752e5b5b6aa5906ae29fcad0658999b"),
    "034": ("0.3.4", 30, "06943d3a186075e84c8c67f90abde351abe85b1c72aa72503a69108a1c01b6b5"),
    "035": ("0.3.5", 30, "b0c695c9a67bf32be60f1c3451222b0ddfdf975543feebee4e3ece817deafe2a"),
    "036": ("0.3.6", 90, "6ba36f67c7c5fa2db0e1ae08874cbe84e188c0a47fe6220cd14b0e475838ac65"),
    "037": ("0.3.7", 120, "0a2116dfb20a8d3d705072d71e2ccc07b5c6c0d545ffc2786e743d187d9dae3d"),
    "038": ("0.3.8", 60, "644bc6e2919bfa158c0ef774676629a74ca10a8cc905eac1173321b0b356535c"),
    "039": ("0.3.9", 150, "e9fb9d382b99e30ffe01a55438793e6fd1a80fb4c3732b20fc3539f36bc2ee3e"),
    "0310": ("0.3.10", 180, "7b4317c1a3982c6e86977127e6fd2b64f60afb0808e79e60c8ae432b2ccbd9e2"),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_new(path, payload):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")


def plan():
    require(sha(PRIOR) == PRIOR_SHA256, "Prior verifier index changed")
    previous = json.loads(PRIOR.read_bytes())
    require(previous["status"] == "passed_all_nine_matching_installed_verifiers", "Prior index is not passed")
    require([r["version"] for r in previous["records"]] == list(SPECS)[:-1], "Unexpected prior version order")
    rows = []
    for original in previous["records"]:
        version = original["version"]
        args = list(original["args"])
        report = HERE / f"FROZEN-{version}-AFTER.json"
        restored = CACHE / version
        if version in ("037", "039"):
            args[0], args[1] = str(report), str(restored)
        elif version == "038":
            report = restored / "guarded-installed-verification.json"
            args[-1] = str(report)
        else:
            args[-1] = str(report)
            if version in ("032", "033", "036"):
                args[2] = str(restored)
        rows.append(dict(version=version, python=original["python"], helper=original["helper"],
                         args=args, report=str(report), expected_status=original["status"]))
    rows.append(dict(version="0310",
                     python=str(ROOT / "data/cache/recovery-step9-duration-wheel-20261028/ingestion-environment/Scripts/python.exe"),
                     helper=str(OLD / "verify_native_installed.py"),
                     args=[str(HERE / "FROZEN-0310-AFTER.json"), str(CACHE / "0310")],
                     report=str(HERE / "FROZEN-0310-AFTER.json"),
                     expected_status="installed_native_simulation_relocation_verified"))
    for row in rows:
        expected, seconds, helper_sha = SPECS[row["version"]]
        row.update(expected_version=expected, replay_timeout_seconds=seconds,
                   helper_sha256=helper_sha, python_sha256=PYTHON_SHA256)
        require(not Path(row["report"]).exists(), f"Report already exists: {row['report']}")
        require(sha(row["helper"]) == helper_sha, f"Changed helper: {row['version']}")
        require(sha(row["python"]) == PYTHON_SHA256, f"Changed interpreter: {row['version']}")
    return rows


def check_payload(payload, row):
    require(payload["status"] == row["expected_status"], f"Unexpected status: {row['version']}")
    for key, value in payload.items():
        if key == "guards" or key.endswith("attempts"):
            values = value.values() if isinstance(value, dict) else (value,)
            require(all(v == [] for v in values), f"Nonempty guards: {row['version']} {key}")
    for obj in (payload, payload.get("result", {})):
        if isinstance(obj, dict):
            for key in ("actual_model_calls", "native_processes", "model_calls", "tokenizer_calls", "network_calls"):
                if key in obj:
                    require(obj[key] == 0, f"Unexpected actual call count: {row['version']} {key}")


def main():
    require(len(sys.argv) == 1 and sys.flags.isolated, "Run this helper with Python -I and no arguments")
    # An exclusive durable marker is reserved before any subprocess dispatch.
    # Do not remove it to restart a partially completed or failed attempt.
    require(not REPORT.exists() and not CACHE.exists(), "Existing output; no automatic restart")
    started = time.monotonic()
    deadline = started + OVERALL_SECONDS
    write_new(ATTEMPT, dict(schema_version=1, status="reserved_once_only",
                           started_at=datetime.now(timezone.utc).isoformat(), helper_sha256=sha(__file__),
                           overall_timeout_seconds=OVERALL_SECONDS, cache=str(CACHE), restart_allowed=False))
    rows = []
    failure = None
    progress = None
    cache_reserved = False
    summary = dict(schema_version=1, status="failed_or_incomplete", current_source_version_under_test="0.3.11",
                   verification_only=True, prior_index=str(PRIOR), prior_index_sha256=PRIOR_SHA256,
                   helper_sha256=sha(__file__), overall_timeout_seconds=OVERALL_SECONDS,
                   metadata_timeout_seconds=METADATA_SECONDS, finalization_reserve_seconds=FINALIZATION_RESERVE_SECONDS,
                   actual_native_execution_authorized=False, restart_allowed=False, records=rows)
    try:
        CACHE.mkdir(parents=True, exist_ok=False)
        cache_reserved = True
        progress = (CACHE / "progress.jsonl").open("x", encoding="utf-8")

        def event(kind, **fields):
            progress.write(json.dumps(dict(kind=kind, elapsed_seconds=time.monotonic() - started, **fields)) + "\n")
            progress.flush()

        def run_child(row, kind, argv, cap):
            remaining = deadline - time.monotonic() - FINALIZATION_RESERVE_SECONDS
            require(remaining > 0, "Aggregate deadline exhausted before dispatch")
            timeout = min(cap, remaining)
            output = CACHE / f"{row['version']}-{kind}.stdout.log"
            errors = CACHE / f"{row['version']}-{kind}.stderr.log"
            call = dict(argv=argv, timeout_seconds=timeout, stdout=str(output), stderr=str(errors),
                        pid=None, returncode=None, timed_out=False, reaped=False)
            row[kind] = call
            event("attempt", version=row["version"], stage=kind, call=call)
            with output.open("xb") as stdout, errors.open("xb") as stderr:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                         shell=False, cwd=ROOT,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                call["pid"] = child.pid
                event("dispatched", version=row["version"], stage=kind, pid=child.pid)
                try:
                    call["returncode"] = child.wait(timeout=timeout)
                except BaseException as error:
                    call["timed_out"] = isinstance(error, subprocess.TimeoutExpired)
                    if child.poll() is None:
                        child.kill()  # This exact owned child only; old helpers prohibit further dispatch.
                    call["returncode"] = child.wait(timeout=5)
                    call["reaped"] = True
                    event("child_interrupted_or_timed_out", version=row["version"], stage=kind, call=call)
                    raise
                call["reaped"] = True
            event("child_finished", version=row["version"], stage=kind, call=call)
            require(call["returncode"] == 0, f"Child failed: {row['version']} {kind}; see retained logs")
            require(time.monotonic() < deadline - FINALIZATION_RESERVE_SECONDS, "Aggregate deadline exhausted after child")
            return call

        rows.extend(plan())
        event("plan_frozen", versions=[r["expected_version"] for r in rows])
        # Complete all ten installed metadata assertions before the first replay.
        metadata_code = (
            "from importlib.metadata import version; import json,sys; "
            "actual=version('asof-target-agents'); expected=sys.argv[1]; "
            "print(json.dumps({'actual':actual,'expected':expected,'isolated':bool(sys.flags.isolated)})); "
            "sys.exit(0 if actual==expected and sys.flags.isolated else 2)"
        )
        for row in rows:
            run_child(row, "metadata", [row["python"], "-I", "-c", metadata_code, row["expected_version"]], METADATA_SECONDS)
            row["version_check_exit_code"] = 0
        event("all_metadata_assertions_passed")
        for row in rows:
            require(sha(row["helper"]) == row["helper_sha256"], f"Helper changed before replay: {row['version']}")
            argv = [row["python"], "-I", row["helper"], *row["args"]]
            run_child(row, "replay", argv, row["replay_timeout_seconds"])
            payload = json.loads(Path(row["report"]).read_bytes())
            check_payload(payload, row)
            require(sha(row["helper"]) == row["helper_sha256"], f"Helper changed during replay: {row['version']}")
            require(sha(row["python"]) == row["python_sha256"], f"Interpreter changed: {row['version']}")
            row.update(argv=argv, exit_code=0, status=payload["status"], report_sha256=sha(row["report"]))
            event("replay_verified", version=row["version"], status=row["status"], report_sha256=row["report_sha256"])
            print(json.dumps(dict(version=row["version"], expected_version=row["expected_version"], status=row["status"])), flush=True)
        require(time.monotonic() < deadline - FINALIZATION_RESERVE_SECONDS, "Aggregate deadline exhausted before finalization")
        summary["status"] = "passed_all_ten_matching_installed_verifiers"
    except BaseException as error:
        failure = dict(schema_version=1, status="failed_no_automatic_restart", error_class=type(error).__name__,
                       message=str(error), elapsed_seconds=time.monotonic() - started,
                       completed_versions=[r["version"] for r in rows if "status" in r])
        summary["failure"] = failure
        if cache_reserved:
            write_new(CACHE / "failure.json", failure)
    finally:
        if progress is not None:
            progress.close()
        summary["elapsed_seconds_before_report"] = time.monotonic() - started
        if summary["elapsed_seconds_before_report"] >= OVERALL_SECONDS:
            summary["status"] = "failed_aggregate_deadline"
        write_new(REPORT, summary)
        elapsed = time.monotonic() - started
        if elapsed >= OVERALL_SECONDS:
            # A late report cannot be mistaken for clean completion.
            write_new(HERE / "FROZEN-VERIFIER-FINALIZATION-FAILURE.json",
                      dict(status="failed_aggregate_deadline", authoritative=True, elapsed_seconds=elapsed,
                           report=str(REPORT), report_sha256=sha(REPORT), restart_allowed=False))
            failure = failure or dict(status="failed_aggregate_deadline")
    return 1 if failure or summary["status"] != "passed_all_ten_matching_installed_verifiers" else 0


if __name__ == "__main__":
    raise SystemExit(main())
