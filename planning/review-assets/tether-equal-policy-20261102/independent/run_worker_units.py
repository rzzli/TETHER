"""Retain fictional worker/control and core unit checks in exclusive files."""
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
TARGET = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    name = sys.argv[1]
    log, summary = TARGET / (name + '.log'), TARGET / (name + '.json')
    if log.exists() or summary.exists():
        raise SystemExit('Evidence already exists')
    paths = list((ROOT / 'experiments/equal_policy').glob('independent*.py')) + [ROOT / path for path in (
        'experiments/equal_policy/worker.py', 'experiments/equal_policy/controls.py',
        'tests/test_equal_policy_worker.py', 'tests/test_equal_policy_independent.py')]
    pins = {path.relative_to(ROOT).as_posix(): sha(path) for path in paths}
    stream = io.StringIO()
    start = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames([
        'tests.test_equal_policy_independent', 'tests.test_equal_policy_worker']))
    elapsed = time.perf_counter() - start
    with log.open('x', encoding='utf-8') as output:
        output.write(stream.getvalue())
    after = {path.relative_to(ROOT).as_posix(): sha(path) for path in paths}
    record = dict(status='PASS' if result.wasSuccessful() and after == pins else 'FAIL', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped), elapsed_seconds=elapsed,
        source_sha256=pins, source_unchanged=pins == after, log_sha256=sha(log), driver_sha256=sha(Path(__file__)),
        purpose='Fictional core/worker/control units; no scored corpus comparison')
    with summary.open('x', encoding='utf-8') as output:
        json.dump(record, output, indent=2)
        output.write('\n')
    print(json.dumps(record))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
