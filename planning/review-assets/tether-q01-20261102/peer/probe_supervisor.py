"""Independent local Windows process probes; no scientific reruns or downloads."""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether import _process as process
from tether import _presentation as presentation
from asof.serde import ContractError


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = HERE / ("run-" + stamp)
    run.mkdir()
    outcomes = []
    checks = []

    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
        if not condition:
            raise AssertionError(name)

    def exercise(mode, *, seconds=0.6, cap=128, terminate_error=False):
        marker = run / (mode + ("-cleanup" if terminate_error else "") + ".marker")
        command = [sys.executable, "-I", str(HERE / "child_fixture.py"), mode,
                   "--bytes", str(cap), "--marker", str(marker)]
        limits = process.ProcessLimits(timeout_seconds=seconds, max_output_bytes=cap)
        original = process.subprocess.Popen
        def damaged_terminate(*args, **kwargs):
            child = original(*args, **kwargs)
            def fail():
                raise PermissionError("fictional terminate failure")
            child.terminate = fail
            return child
        start = time.monotonic()
        with ExitStack() as stack:
            if terminate_error:
                stack.enter_context(patch.object(process.subprocess, "Popen", damaged_terminate))
                stack.enter_context(patch.object(process, "CLEANUP_SECONDS", 0.4))
            try:
                result = process.supervise_command(command, limits=limits)
                error = None
            except BaseException as problem:
                error = type(problem).__name__
                result = getattr(problem, "tether_engine_result", None)
                if result is None:
                    raise
        elapsed = time.monotonic() - start
        check(mode + ": one child launch", marker.read_bytes() == b"dispatch\n")
        check(mode + ": retained aggregate bound", len(result.stdout) + len(result.stderr) <= cap)
        check(mode + ": child reaped", result.supervision["process_reaped"] is True)
        check(mode + ": observed measured elapsed bound", elapsed < seconds + 2)
        if mode == "exact":
            check("exact cap accepted", error is None and result.returncode == 0)
            check("exact original streams", result.stdout == b"A" * (cap // 2)
                  and result.stderr == b"B" * (cap - cap // 2))
            process.validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        elif mode in ("overflow", "flood_stdout", "flood_stderr", "flood_both"):
            check(mode + ": explicit limit failure", error == "EngineOutputLimitExceeded")
            check(mode + ": exactly one sentinel counted",
                  result.supervision["observed_stdout_bytes"] + result.supervision["observed_stderr_bytes"] == cap + 1)
        elif mode == "nonzero":
            check("nonzero return retained", error is None and result.returncode == 7)
            check("nonzero both streams retained", result.stdout == b"retained output" and result.stderr == b"retained error")
        else:
            check(mode + ": explicit deadline failure", error == "EngineDeadlineExceeded")
            check(mode + ": deadline did not reset", elapsed < 2)
        if terminate_error:
            check("cleanup error remains secondary", any(e["operation"] == "process_terminate"
                  and e["error_class"] == "PermissionError" for e in result.supervision["cleanup_errors"]))
        outcomes.append(dict(mode=mode, terminate_error=terminate_error, error=error,
                             elapsed_seconds=elapsed, returncode=result.returncode,
                             supervision=result.supervision))
        return result

    try:
        exact = exercise("exact")
        for mode in ("overflow", "block", "trickle", "flood_stdout", "flood_stderr", "flood_both", "nonzero", "inherited_pipe"):
            exercise(mode)
        exercise("block", terminate_error=True)
        invalid = [dict(timeout_seconds=x) for x in (True, 0, -1, float("inf"), float("nan"))]
        invalid += [dict(max_output_bytes=x) for x in (True, 0, -1, 1.5, process.MAX_OUTPUT_BYTES + 1)]
        for index, kwargs in enumerate(invalid):
            with patch.object(process.subprocess, "Popen", side_effect=AssertionError("must not launch")) as launch:
                try:
                    process.supervise_command(["unused"], limits=process.ProcessLimits(**kwargs))
                except ContractError:
                    pass
                else:
                    raise AssertionError("invalid limit accepted")
                check(f"invalid limits {index}: no launch", launch.call_count == 0)

        for mode, accounted in (("block", False), ("accounted_block", True)):
            output = run / ("outer-" + mode)
            limits = process.ProcessLimits(timeout_seconds=0.6, max_output_bytes=128)
            calls = []
            def engine(argv):
                calls.append(argv)
                return process.supervise_command([sys.executable, "-I", str(HERE / "child_fixture.py"), mode,
                    "--engine-output", argv[-1], "--marker", str(output / "launch.marker")], limits=limits)
            try:
                presentation.create_outer(output, ["demo", "--output", str(output)], engine=engine, limits=limits)
            except process.EngineDeadlineExceeded:
                pass
            else:
                raise AssertionError("blocked outer completed")
            check(mode + ": no success receipt", not (output / presentation.RECEIPT).exists())
            check(mode + ": retained failure", (output / presentation.FAILURE).is_file())
            inspected = presentation.inspect_outer(output)
            check(mode + ": outer single dispatch", len(calls) == 1)
            check(mode + ": terminal failure journal", inspected["last_event"] == "run_failed")
            checked_engine = inspected["engine"]
            check(mode + ": pending accounting retained", checked_engine["unresolved_attempts"] == ([] if accounted else ["fictional:1"]))
            check(mode + ": measured accounting retained", checked_engine["measured_usage"] == dict(input_tokens=3 if accounted else 0, output_tokens=5 if accounted else 0, cost_usd=0))
            check(mode + ": estimate not double counted", checked_engine["estimated_upper_usage"] == dict(input_tokens=0 if accounted else 7, output_tokens=0 if accounted else 11, cost_usd=0))
            try:
                presentation.verify_outer(output)
            except ContractError:
                pass
            else:
                raise AssertionError("failed outer verified")
            check(mode + ": inspect/verify never redispatched", len(calls) == 1)
            outcomes.append(dict(mode="outer-" + mode, inspection=inspected))
        status = "passed"
    except BaseException as error:
        outcomes.append(dict(error_class=type(error).__name__, error=str(error)))
        status = "failed"
        raise
    finally:
        files = ["packages/tether/src/tether/_process.py", "packages/tether/src/tether/_presentation.py"]
        report = dict(schema_version=1, status=locals().get("status", "failed"), run_directory=str(run),
                      recorded_at_utc=datetime.now(timezone.utc).isoformat(), checks=checks, outcomes=outcomes,
                      code_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files})
        (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(status=report["status"], checks=len(checks), report=str(run / "report.json"))))


if __name__ == "__main__":
    main()
