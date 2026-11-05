"""Retain isolated unit qualification; this never scores benchmark controls."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    repository = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repository))
    target = Path(__file__).resolve().parent
    phase = sys.argv[1]
    log_path, result_path = target / (phase + '.log'), target / (phase + '.json')
    if log_path.exists() or result_path.exists():
        raise SystemExit('Refusing to overwrite retained qualification')
    sources = [repository / 'tests/test_equal_policy_independent.py'] + [repository / 'experiments/equal_policy' / name
        for name in ('independent.py', 'independent_schema.py', 'independent_local.py', 'independent_render.py')]
    pins_before = {path.relative_to(repository).as_posix(): sha(path) for path in sources}
    output = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_equal_policy_independent')
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    elapsed = time.perf_counter() - started
    payload = output.getvalue().encode('utf-8')
    with log_path.open('xb') as stream:
        stream.write(payload)
    pins_after = {path.relative_to(repository).as_posix(): sha(path) for path in sources}
    record = dict(status='PASS' if result.wasSuccessful() and pins_before == pins_after else 'FAIL',
        purpose='Fictional component unit qualification; not benchmark scoring or held-out performance',
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
        elapsed_seconds=elapsed, source_sha256=pins_before, source_unchanged=pins_before == pins_after,
        test_log_sha256=sha(log_path), driver_sha256=sha(Path(__file__)), python=sys.version,
        executable=sys.executable)
    with result_path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
