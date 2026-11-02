"""Independent interruption and unpersisted-delegate diagnostic checks."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether import _process as process, _presentation as layer, _cli as cli


def main():
    run = HERE / ("interrupt-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir()
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
        if not value:
            raise AssertionError(name)
    marker = run / "interrupt.marker"
    original = process._read_ready
    injected = []
    def interrupt(stream, maximum):
        if marker.exists() and not injected:
            injected.append(True)
            raise KeyboardInterrupt("fictional user interruption")
        return original(stream, maximum)
    try:
        with patch.object(process, "_read_ready", interrupt):
            process.supervise_command([sys.executable, "-I", str(HERE / "child_fixture.py"), "block", "--marker", str(marker)],
                limits=process.ProcessLimits(timeout_seconds=2, max_output_bytes=128))
    except process.EngineInterrupted as error:
        interrupted = error.tether_engine_result.supervision
        check("original interruption remains cause", isinstance(error.__cause__, KeyboardInterrupt))
        check("interruption classified", interrupted["termination_reason"] == "interrupted")
        check("interrupted child reaped", interrupted["process_reaped"] is True)
        check("one interrupted dispatch", marker.read_bytes() == b"dispatch\n")
    else:
        raise AssertionError("interruption lost")
    delegated = run / "delegate-target"
    delegated.mkdir()
    calls = []
    def invoke(argv, *, limits):
        calls.append(argv)
        return process.supervise_command([sys.executable, "-I", str(HERE / "child_fixture.py"), "trickle"], limits=limits)
    stream, output = io.StringIO(), io.StringIO()
    with patch.object(layer, "invoke_engine", invoke), redirect_stderr(stream), redirect_stdout(output):
        status = cli.main(["inspect-run", "--run-dir", str(delegated), "--process-timeout-seconds=.3", "--process-output-bytes=128"])
    diagnostic = json.loads(stream.getvalue().splitlines()[-1])["tether_process_failure"]
    check("delegate timeout returns failure", status == 2)
    check("delegate emits bounded reason", diagnostic["termination_reason"] == "deadline_exceeded")
    check("delegate emits cleanup disposition", diagnostic["process_reaped"] is True)
    check("delegate never retries", len(calls) == 1)
    check("delegate does not fabricate durable output", list(delegated.iterdir()) == [])
    check("wrapper flags removed from engine args", not any(x.startswith("--process-") for x in calls[0]))
    report = dict(schema_version=1, status="passed", checks=checks,
                  interruption=interrupted, delegate_diagnostic=diagnostic)
    (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="passed", checks=len(checks), report=str(run / "report.json"))))


if __name__ == "__main__":
    main()
