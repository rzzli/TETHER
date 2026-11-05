"""Retain fictional units/native integration, never the frozen scored corpus."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parents[4]
    target = Path(__file__).parent
    mode, phase = sys.argv[1:]
    if mode not in ('unit', 'native') or not re.fullmatch(r'[A-Za-z0-9_-]+', phase):
        raise SystemExit('Usage: run_qualification.py unit|native fresh-label')
    log_path, result_path = target / (phase + '.log'), target / (phase + '.json')
    if log_path.exists() or result_path.exists(): raise SystemExit('Refusing to overwrite retained evidence')
    source = root / 'experiments/equal_policy'
    names = ('independent.py', 'independent_schema.py', 'independent_local.py', 'independent_render.py',
             'independent_policy.py', 'test_independent_policy.py', 'reference.py', 'cases.py', 'policy_cases.py', 'materialize.py')
    files = [source / name for name in names] + [root / 'tests/test_equal_policy_native.py']
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    before = {p.relative_to(root).as_posix(): sha(p) for p in files}
    if mode == 'native':
        python = root / 'data/cache/tether-051-installed-qualification-attempt02/environment/Scripts/python.exe'
        argv = [str(python), '-I', '-B', str(root / 'tests/test_equal_policy_native.py')]
    else:
        python = root / 'data/cache/tether-051-dev/Scripts/python.exe'
        argv = [str(python), '-B', '-m', 'unittest', 'experiments.equal_policy.test_independent_policy', '-v']
    started = datetime.now(timezone.utc).isoformat(); tick = time.perf_counter()
    completed = subprocess.run(argv, cwd=root, capture_output=True, timeout=180)
    payload = completed.stdout + completed.stderr
    with log_path.open('xb') as stream: stream.write(payload)
    after = {p.relative_to(root).as_posix(): sha(p) for p in files}
    count = re.search(rb'Ran (\d+) tests? in ', payload)
    ok = completed.returncode == 0 and count and payload.rstrip().endswith(b'OK') and before == after
    record = dict(schema_version=1, status='PASS' if ok else 'FAIL', mode=mode, argv=argv,
        started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-tick,
        returncode=completed.returncode, tests_run=int(count[1]) if count else None, source_sha256=before,
        source_unchanged=before == after, source_after_sha256=after, log_sha256=sha(log_path), driver_sha256=sha(Path(__file__)),
        qualification_scope='Unscored fictional tests; no corpus oracle or scored paired comparison',
        native_production=mode == 'native', production_science_data=False, network_or_model_execution=False,
        unit_inner_verifier_stub='Outer unit isolation only' if mode == 'unit' else 'None; full native bytes independently verified')
    with result_path.open('x', encoding='utf-8') as stream: json.dump(record, stream, indent=2); stream.write('\n')
    print(json.dumps(record))
    return 0 if ok else 1


if __name__ == '__main__': raise SystemExit(main())
