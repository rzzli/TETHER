"""Check current per-call runtime and inspection qualification evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
TARGET = Path(__file__).parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = TARGET / 'CURRENT-RUNTIME-QUALIFICATION-20261105.json'
    if destination.exists():
        raise SystemExit('Refusing to overwrite retained qualification')
    records, failures = [], []
    for name, count in (
        ('worker-current-runtime-green01.json', 55),
        ('../independent-policy/unit-current-runtime-green01.json', 18),
        ('../independent-policy/native-current-runtime-green01.json', 5),
        ('policy-peer-current-runtime01.json', 6),
    ):
        path = (TARGET / name).resolve(); value = json.loads(path.read_bytes())
        log = path.with_suffix('.log'); payload = log.read_bytes()
        checks = dict(status=value['status'] == 'PASS',
            count=value['tests_run'] == count and re.findall(rb'Ran (\d+) tests? in ', payload) == [str(count).encode()],
            no_failures=value.get('failures', 0) == value.get('errors', 0) == value.get('skips', 0) == 0,
            terminal_ok=payload.rstrip().endswith(b'OK'), log_hash=sha(log) == value['log_sha256'],
            unchanged=value['source_unchanged'] is True,
            current_sources=all(sha(ROOT / source) == pin for source, pin in value['source_sha256'].items()))
        if not all(checks.values()): failures.append(dict(record=name, failed=[k for k, v in checks.items() if not v]))
        records.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), tests=count,
            log_sha256=sha(log), checks=checks, source_sha256=value['source_sha256']))
    defects = []
    for name, count, old_sources in (
        ('worker-current-runtime-red01.json', 55, {'experiments/equal_policy/independent.py': 'independent-before-current-runtime.py.txt'}),
        ('../independent-policy/unit-current-runtime-red01.json', 18,
            {'experiments/equal_policy/independent.py': 'independent-before-current-runtime.py.txt',
             'experiments/equal_policy/independent_policy.py': 'independent-policy-before-current-runtime.py.txt'}),
    ):
        path = (TARGET / name).resolve(); value = json.loads(path.read_bytes()); payload = path.with_suffix('.log').read_bytes()
        valid = (value['status'] == 'FAIL' and value['tests_run'] == count and value['source_unchanged'] is True
                 and b'FAILED (failures=4, errors=1)' in payload and sha(path.with_suffix('.log')) == value['log_sha256']
                 and all(sha(TARGET / saved) == value['source_sha256'][source] for source, saved in old_sources.items()))
        if not valid: failures.append(dict(record=name, failed=['red_evidence']))
        defects.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), valid=valid,
            preserved_sources={saved: sha(TARGET / saved) for saved in old_sources.values()}))
    result = dict(schema_version=1, status='PASS' if not failures else 'FAIL',
        checked_at_utc=datetime.now(timezone.utc).isoformat(), records=records, red_evidence=defects, failures=failures,
        checker_sha256=sha(Path(__file__)),
        scope='Unscored per-call actual code qualification, single-buffer core inspection and relocated native integration',
        limitations=['Finite fictional controls do not establish universal policy parity',
            'Method counts overlap and are not independent observations',
            'Fake package changes never modified the installed qualified runtime',
            'No corpus freeze, scored paired comparison, provider call or scientific validation occurred'])
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(dict(status=result['status'], failures=failures, path=str(destination), sha256=sha(destination))))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
