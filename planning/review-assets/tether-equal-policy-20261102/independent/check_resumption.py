"""Check current unscored qualification records without running the corpus."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
TARGET = Path(__file__).parent
SOURCES = (
    ('worker-resume-green01.json', 53),
    ('../independent-policy/unit-resume01.json', 17),
    ('../independent-policy/native-resume01.json', 5),
    ('policy-peer01.json', 6),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = TARGET / 'RESUMPTION-QUALIFICATION-20261105.json'
    if destination.exists():
        raise SystemExit('Retained qualification index already exists')
    records, failures = [], []
    for relative, expected in SOURCES:
        path = (TARGET / relative).resolve()
        value = json.loads(path.read_bytes())
        log = path.with_suffix('.log')
        payload = log.read_bytes()
        summaries = re.findall(rb'Ran (\d+) tests? in [^\r\n]+', payload)
        checks = dict(
            status=value.get('status') == 'PASS',
            count=value.get('tests_run') == expected and summaries == [str(expected).encode('ascii')],
            no_failures=value.get('failures', 0) == 0,
            no_errors=value.get('errors', 0) == 0,
            no_skips=value.get('skips', 0) == 0,
            terminal_ok=payload.rstrip().endswith(b'OK'),
            log_hash=sha(log) == value['log_sha256'],
            source_bracket=value.get('source_unchanged') is True,
            current_sources=all(sha(ROOT / key) == digest for key, digest in value['source_sha256'].items()),
        )
        if not all(checks.values()):
            failures.append(dict(record=relative, failed=[key for key, passed in checks.items() if not passed]))
        records.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
            log_sha256=sha(log), tests=expected, checks=checks, source_sha256=value['source_sha256']))
    red_path = TARGET / 'worker-resume-red01.json'
    red = json.loads(red_path.read_bytes())
    preserved = TARGET / 'independent-before-required-policy-fields.py.txt'
    red_valid = (red['status'] == 'FAIL' and red['tests_run'] == 53 and red['failures'] == 8
        and red['errors'] == 0 and red['skips'] == 0
        and sha(red_path.with_suffix('.log')) == red['log_sha256']
        and sha(preserved) == red['source_sha256']['experiments/equal_policy/independent.py'])
    if not red_valid:
        failures.append(dict(record=red_path.name, failed=['red_evidence_binding']))
    result = dict(schema_version=1, status='PASS' if not failures else 'FAIL', checked_at_utc=datetime.now(timezone.utc).isoformat(),
        qualification_scope='Unscored component, policy, native-format and peer qualification; no paired corpus execution',
        records=records, defect=dict(description='Missing required artifact-policy preparation descriptor fields were not rejected before file I/O',
            red_record=red_path.relative_to(ROOT).as_posix(), red_sha256=sha(red_path), failed_subcontrols=8,
            preserved_source=preserved.relative_to(ROOT).as_posix(), preserved_source_sha256=sha(preserved),
            corrected_source_sha256=sha(ROOT / 'experiments/equal_policy/independent.py'), red_evidence_valid=red_valid),
        failures=failures, checker_sha256=sha(Path(__file__)),
        limitations=['Counts describe overlapping method scopes and are not summed into independent observations',
            'Native integration uses installed TETHER solely to prepare fictional originals; independent validation calls no product helper',
            'Finite qualification does not establish complete policy parity or scientific validation',
            'Clause-level coverage review, frozen paired execution and independently reconstructed analysis remain required'])
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], records=len(records), failures=failures,
                          result_path=str(destination), sha256=sha(destination))))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
