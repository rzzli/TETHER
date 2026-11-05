"""Read-only BG02 evidence inventory; never executes the paired corpus."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EP = ROOT / 'planning/review-assets/tether-equal-policy-20261102'
BG = ROOT / 'planning/review-assets/tether-ce-fixes-20261102/integration'
PREP = ROOT / 'data/benchmark/tether-equal-policy-20261102-attempt03'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    failures = []
    def check(condition, label):
        if not condition:
            failures.append(label)
        return bool(condition)
    prep = read(PREP / 'PREPARATION.json')
    schedule = read(PREP / 'case-preparation-schedule.json')['cases']
    spec = read(EP / 'policy-spec.json')
    check(prep['status'] == 'prepared', 'preparation not complete')
    check(len(schedule) == len(prep['records']) == 108, 'unexpected primary inventory')
    check(len({r['control_id'] for r in schedule}) == 108, 'duplicate primary ID')
    producer = {}
    for filename in ('cases.py', 'materialize.py', 'reference.py', 'policy_cases.py'):
        name = 'experiments/equal_policy/' + filename
        expected = prep['started']['sources'][name]
        actual = pin(ROOT / name)
        wanted = expected['sha256'] if isinstance(expected, dict) else expected
        producer[name] = {**actual, 'expected_sha256': wanted,
                          'matches': check(actual['sha256'] == wanted, 'producer changed: ' + name)}
    descriptor_checks = []
    for record in prep['records']:
        actual = pin(PREP / record['descriptor'])
        ok = (record['status'] == 'prepared' and actual['sha256'] == record['descriptor_pin']['sha256']
              and actual['bytes'] == record['descriptor_pin']['bytes'])
        descriptor_checks.append({'control_id': record['control_id'], **actual,
                                  'matches': check(ok, 'descriptor changed: ' + record['control_id'])})
    strata = Counter((row['operation'], row['variant'], row['construction_stratum']) for row in schedule)
    families = {row['id']: [] for row in spec['obligations']}
    for row in schedule:
        for obligation in row['oracle']['obligation_ids']:
            check(obligation in families, 'unknown obligation ' + obligation)
            families[obligation].append(row['control_id'])
    reference_pins = {}
    for filename in ('POLICY-SPEC.md', 'policy-spec.json'):
        name = (EP / filename).relative_to(ROOT).as_posix()
        check(sha(ROOT / name) == prep['started']['sources'][name]['sha256'], 'normative contract changed: ' + name)
    for name, expected in spec['reference_source_sha256'].items():
        actual = sha(ROOT / name)
        reference_pins[name] = {'sha256': actual, 'matches': check(actual == expected, 'reference changed: ' + name)}
    bracket = read(BG / 'full-gate-04.source-bracket.json')
    gate = read(BG / 'full-gate-04.json')
    check(bracket['status'] == 'PASS' and not bracket['changed_sources'], 'full gate unstable')
    check(sha(BG / 'full-gate-04.json') == bracket['report_sha256'], 'full gate report hash')
    check(sha(BG / 'full-gate-04.log') == bracket['log_sha256'], 'full gate log hash')
    check(gate['tests'] == {'run': 2020, 'failures': 0, 'errors': 0, 'skipped': []}, 'full gate test result')
    trusted = read(PREP / 'trusted-runtime.json')
    qualification = Path(trusted['qualification']['path'])
    check(sha(qualification) == trusted['qualification']['sha256'], 'installed qualification anchor')
    q = read(qualification)
    installed = {}
    for package, information in q['installed']['packages'].items():
        folder = Path(information['root'])
        prefix = 'src/' if package == 'asof' else 'packages/tether/src/'
        paths = {p.relative_to(folder.parent).as_posix(): p for p in folder.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py', '.json'}}
        expected = q['source_manifest']['sources'][package]
        check(set(paths) == set(expected), 'installed namespace inventory: ' + package)
        for name, path in paths.items():
            actual = sha(path)
            checkout_name = prefix + name
            gate_pin = bracket['after_sources'][checkout_name]['sha256']
            installed[checkout_name] = {'installed_path': str(path), 'sha256': actual,
                'matches_qualification': check(actual == expected[name], 'installed qualification mismatch ' + name),
                'matches_gate': check(actual == gate_pin == sha(ROOT / checkout_name), 'gate/current runtime mismatch ' + name)}
    witness = read(EP / 'RUNTIME-WITNESSES.json')
    check(sha(ROOT / witness['result_path']) == witness['result_sha256'], 'runtime witness result hash')
    check(sha(EP / witness['console_log']) == witness['console_log_sha256'], 'runtime witness log hash')
    check(sha(EP / witness['launcher_tests']['log']) == witness['launcher_tests']['log_sha256'], 'runtime launcher log hash')
    check(witness['status'] == 'PASS' and witness['control_count'] == 10 and
          witness['launcher_tests']['run'] == 3 and witness['installed_runtime_unchanged'], 'runtime witness result')
    package_log = BG / 'package-tests-02.log'
    check('Ran 138 tests' in package_log.read_text() and package_log.read_text().rstrip().endswith('OK'), 'facade package test result')
    evidence = [EP / name for name in ['POLICY-SPEC.md', 'policy-spec.json', 'RUNTIME-WITNESSES.md',
        'RUNTIME-WITNESSES.json', 'runtime-witnesses-02.log', 'runtime-witness-tests-01.log',
        'independent/RESUMPTION-QUALIFICATION-20261105.json']]
    evidence += [BG / name for name in ['full-gate-04.json', 'full-gate-04.log',
        'full-gate-04.source-bracket.json', 'package-tests-02.log', 'platform-scope.json']]
    evidence += [PREP / name for name in ['PREPARATION.json', 'case-preparation-schedule.json', 'trusted-runtime.json']]
    evidence += [qualification, ROOT / witness['result_path']]
    output = {'schema_version': 1, 'status': 'PASS' if not failures else 'FAIL',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Read-only inventory and prior evidence reuse; no paired-corpus validator execution',
        'primary_case_count': len(schedule), 'outcomes': dict(Counter(row['oracle']['decision'] for row in schedule)),
        'strata': [{'operation': k[0], 'variant': k[1], 'exposure': k[2], 'count': v} for k, v in sorted(strata.items())],
        'family_labels': families, 'label_limit': 'Authored family tags, not proof of clause coverage or observed parity',
        'descriptor_checks': descriptor_checks, 'producer_checks': producer, 'reference_spec_checks': reference_pins,
        'installed_payload_checks': installed, 'evidence': [pin(p) for p in evidence], 'failures': failures,
        'checker_sha256': sha(Path(__file__)),
        'limits': ['Package-tests-02 is a prior retained checkout test log; the full-gate source bracket and present installed payload match establish code reuse, not a new installed test run.',
                   'Independent qualification source pins may change during pre-freeze development and must be requalified by their owner before freeze.',
                   'No scientific data, evaluator outcomes, human returns, model, network or scored-corpus execution was used.']}
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(output, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': output['status'], 'primary_cases': len(schedule),
                      'installed_payloads': len(installed), 'failures': failures, 'output': str(args.output)}))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
