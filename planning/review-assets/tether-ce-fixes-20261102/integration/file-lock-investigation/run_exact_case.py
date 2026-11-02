"""Three isolated fictional reproductions of a reported fixture replace error."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).parent
TEST = "tests.test_science_comparison_workflow.ComparisonWorkflowTests.test_rehashed_coverage_cannot_invent_source_count"
PINS = ("src/asof/serde.py", "src/asof/local_model.py", "src/asof/demo/v2/snapshot.json",
        "tests/test_science_comparison_workflow.py", "tools/science/comparison_workflow.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def single():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    suite = unittest.defaultTestLoader.loadTestsFromName(TEST)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = dict(test=TEST, tests=result.testsRun, success=result.wasSuccessful(),
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  duration_seconds=time.monotonic()-started,
                  failures_detail=[dict(test=str(test), traceback=trace) for test,trace in result.failures],
                  errors_detail=[dict(test=str(test), traceback=trace) for test,trace in result.errors],
                  interpreter=sys.executable, temporary_root=os.environ["TEMP"])
    write_new(Path(sys.argv[2]), record)
    raise SystemExit(not result.wasSuccessful())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        single()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = ROOT / "data/cache" / ("ce02-file-lock-investigation-" + stamp)
    run_root.mkdir(exist_ok=False)
    before = {name:sha(ROOT/name) for name in PINS}
    attempts = []
    for number in range(1, 4):
        leaf = run_root / ("attempt%02d" % number)
        leaf.mkdir()
        temporary = leaf / "tmp"
        temporary.mkdir()
        result_path = HERE / ("attempt%02d-%s.json" % (number, stamp))
        env = dict(os.environ, TEMP=str(temporary), TMP=str(temporary))
        completed = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                    "--single", str(result_path)], cwd=ROOT, env=env,
                                   capture_output=True, timeout=60)
        stdout = HERE / ("attempt%02d-%s.stdout.txt" % (number, stamp))
        stderr = HERE / ("attempt%02d-%s.stderr.txt" % (number, stamp))
        stdout.write_bytes(completed.stdout)
        stderr.write_bytes(completed.stderr)
        attempts.append(dict(number=number, returncode=completed.returncode, result=result_path.name,
                             stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)))
    after = {name:sha(ROOT/name) for name in PINS}
    passed = all(item["returncode"] == 0 for item in attempts) and before == after
    record = dict(status="UNREPRODUCED_IN_THREE_ISOLATED_ATTEMPTS" if passed else "REQUIRES_FURTHER_DIAGNOSIS",
                  checked_at_utc=datetime.now(timezone.utc).isoformat(), test=TEST,
                  root_reported_failure="full-gate02: setUp write_json(snapshot.json), os.replace PermissionError WinError5",
                  attempts=attempts, source_pins_before=before, source_pins_after=after,
                  source_unchanged=before==after, output=str(run_root),
                  cause="Not established; no AV/open-handle attribution is proved",
                  original_gate_paths_accessed=False, source_edits=False,
                  actual_model_calls=0, network_calls=0, provider_spending_usd=0)
    write_new(HERE / ("INVESTIGATION-" + stamp + ".json"), record)
    print(json.dumps(record, indent=2))
    raise SystemExit(not passed)


if __name__ == "__main__":
    main()
