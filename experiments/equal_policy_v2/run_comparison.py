"""Corrected BG02: explicit version-qualified, independently frozen four-arm runs.

Original execution sources and results remain immutable. Shared v1 helpers are
read-only; no module globals are reassigned to select a product installation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy import run_comparison as legacy
from equal_policy import materialize as wire
from equal_policy_v2 import cases, materialize

PROJECT = Path(__file__).resolve().parents[2]
EVIDENCE = PROJECT / 'planning/review-assets/tether-equal-policy-v2-20261105'
IMPLEMENTATIONS = ('tether', 'independent', 'hash_schema', 'reject_all')
SETTINGS = dict(legacy.SETTINGS)
utc, publish, pin = legacy.utc, legacy.publish, legacy.pin
tree, directories = legacy.tree, legacy.directories
installed_inventory = legacy.installed_inventory
check_trusted_installation = legacy.check_trusted_installation
observable_projection = legacy.observable_projection

# These receipts reference immutable sources/logs, never their own output hash.
# The execution freeze binds both receipt bytes and the sources they qualify.
QUALIFICATION_REQUIREMENTS = {
    'corpus': dict(
        path='planning/review-assets/tether-equal-policy-result-review-20261105/CORPUS-V2-QUALIFICATION.json',
        status='PASS_CONSTRUCTION_AND_ADMISSION_ONLY',
        required=('experiments/equal_policy_v2/cases.py', 'experiments/equal_policy_v2/test_cases.py',
            'planning/review-assets/tether-equal-policy-result-review-20261105/corpus-v2-red01.log',
            'planning/review-assets/tether-equal-policy-result-review-20261105/corpus-v2-green02.log',
            'planning/review-assets/tether-ce-fixes-20261102/integration/full-gate-04.log',
            'planning/review-assets/tether-ce-fixes-20261102/integration/full-gate-04.source-bracket.json',
            'tests/test_ce02_usage_accounting.py')),
    'independent': dict(
        path='planning/review-assets/tether-equal-policy-result-review-20261105/INDEPENDENT-V2-QUALIFICATION.json',
        status='PASS_COMPONENT_QUALIFICATION',
        required=('experiments/equal_policy_v2/independent.py',
            'experiments/equal_policy_v2/independent_runtime.py', 'experiments/equal_policy_v2/test_independent.py',
            'planning/review-assets/tether-equal-policy-result-review-20261105/independent-v2-unit01.log',
            'planning/review-assets/tether-equal-policy-result-review-20261105/independent-v2-native01.log')),
    'runner': dict(
        path='planning/review-assets/tether-equal-policy-v2-20261105/runner/QUALIFICATION-CLOSURE-20261105.json',
        status='PASS_RUNNER_QUALIFICATION',
        required=('experiments/equal_policy_v2/run_comparison.py', 'experiments/equal_policy_v2/worker.py',
            'experiments/equal_policy_v2/reference.py', 'experiments/equal_policy_v2/test_runner.py',
            'experiments/equal_policy_v2/test_reference_worker.py',
            'planning/review-assets/tether-equal-policy-v2-20261105/runner/qualify_runner_closure.py',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/QUALIFICATION.json',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/unit.stdout',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/unit.stderr')),
}


def qualification_evidence():
    """Validate and return the explicit source-linked qualification closure."""
    result = {}
    for role, requirement in QUALIFICATION_REQUIREMENTS.items():
        receipt_path = PROJECT / requirement['path']
        document = wire.load(receipt_path)
        if document.get('schema_version') != 1 or document.get('status') != requirement['status']:
            raise RuntimeError('Invalid qualification receipt: ' + role)
        rows = document.get('pins')
        if type(rows) is not list or not rows:
            raise RuntimeError('Qualification lacks source-linked evidence: ' + role)
        named = set()
        for row in rows:
            relative = row.get('path') if type(row) is dict else None
            if (type(relative) is not str or not relative or Path(relative).is_absolute()
                    or ':' in relative or any(part in ('', '.', '..') for part in relative.replace('\\', '/').split('/'))):
                raise RuntimeError('Unsafe qualification evidence path: ' + role)
            relative = Path(relative).as_posix()
            path = (PROJECT / relative).resolve()
            if not path.is_relative_to(PROJECT.resolve()) or relative in named or relative == requirement['path']:
                raise RuntimeError('Duplicate, escaping or self-referential qualification evidence: ' + role)
            named.add(relative)
            expected = {key: row[key] for key in ('sha256', 'bytes')}
            if pin(path) != expected:
                raise RuntimeError('Qualification evidence changed: ' + relative)
            if relative in result and result[relative] != expected:
                raise RuntimeError('Conflicting qualification evidence: ' + relative)
            result[relative] = expected
        if not set(requirement['required']) <= named:
            raise RuntimeError('Qualification evidence closure is incomplete: ' + role)
        result[requirement['path']] = pin(receipt_path)
    return result


def source_pins():
    # Complete immutable v1 closure plus explicitly versioned delta modules.
    result = legacy.source_pins()
    paths = [p for p in Path(__file__).parent.glob('*.py')
             if p.name not in ('reconstruct.py', 'test_reconstruct.py')]
    paths += [EVIDENCE / name for name in ('CORRECTED-PROTOCOL.md', 'corpus-deltas.json')]
    result.update({p.relative_to(PROJECT).as_posix(): pin(p) for p in sorted(paths)})
    for relative, proof in qualification_evidence().items():
        if relative in result and result[relative] != proof:
            raise RuntimeError('Execution/qualification source disagreement: ' + relative)
        result[relative] = proof
    return result


def runtime_pins(trusted):
    qualification = Path(trusted['qualification']['path'])
    root = qualification.parent
    result = {str(qualification): pin(qualification)}
    if result[str(qualification)]['sha256'] != trusted['qualification']['sha256']:
        raise RuntimeError('Qualified installation evidence changed')
    for wheel in trusted['wheels']:
        filename = wheel['filename']
        if Path(filename).name != filename:
            raise RuntimeError('Wheel proof must name one qualification-local file')
        path = root / 'wheels' / filename
        proof = pin(path)
        if proof != {k: wheel[k] for k in ('sha256', 'bytes')}:
            raise RuntimeError('Qualified wheel bytes changed')
        result[str(path)] = proof
    return result


def runtime_python(trusted):
    root = Path(trusted['qualification']['path']).resolve().parent
    python = Path(trusted['runtime_paths']['python']).resolve()
    if python != root / 'environment/Scripts/python.exe':
        raise RuntimeError('Interpreter differs from explicitly qualified installation')
    return python


def prepare(output, qualification):
    qualification = Path(qualification).resolve()
    python = qualification / 'environment/Scripts/python.exe'
    if not python.is_file() or not (qualification / 'QUALIFICATION.json').is_file():
        raise FileNotFoundError('Qualified installed interpreter/evidence is missing')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'bundles').mkdir()
    (output / 'temporary').mkdir()
    os.environ.update(TEMP=str(output / 'temporary'), TMP=str(output / 'temporary'))
    specs = cases.case_specs()
    publish(output / 'case-preparation-schedule.json', dict(schema_version=1, cases=specs))
    publish(output / 'oracle.json', cases.oracle_manifest())
    started = dict(started_at_utc=utc(), sources=source_pins(), cases=len(specs))
    publish(output / 'PREPARATION-STARTED.json', started)
    command = [str(python), '-I', '-B', str(Path(__file__).with_name('reference.py')),
               '--trusted-runtime', str(qualification)]
    try:
        captured = subprocess.run(command, capture_output=True, check=False, timeout=90)
        (output / 'trusted-runtime.stdout').write_bytes(captured.stdout)
        (output / 'trusted-runtime.stderr').write_bytes(captured.stderr)
        if captured.returncode:
            raise RuntimeError('Trusted-runtime capture exited ' + str(captured.returncode))
        trusted = json.loads(captured.stdout)
        if runtime_python(trusted) != python:
            raise RuntimeError('Captured interpreter differs from preparation interpreter')
        captured_runtime_pins = runtime_pins(trusted)
    except BaseException as error:
        for name, payload in (('trusted-runtime.stdout', getattr(error, 'stdout', None)),
                              ('trusted-runtime.stderr', getattr(error, 'stderr', None))):
            path = output / name
            if not path.exists():
                path.write_bytes(payload if isinstance(payload, bytes) else b'')
        publish(output / 'PREPARATION.json', dict(status='FAILED', stage='trusted_runtime',
            argv=command, started=started, error_class=type(error).__name__, reason=str(error),
            finished_at_utc=utc()))
        if not isinstance(error, Exception):
            raise
        return False
    publish(output / 'trusted-runtime.json', trusted)
    records = []
    for spec in specs:
        root = output / 'bundles' / spec['control_id']
        record = dict(control_id=spec['control_id'], started_at_utc=utc(), status='preparing')
        try:
            descriptor, pending = cases.write_source_bundle(root, spec, trusted_runtime='trusted-runtime.json')
            publish(root / 'trusted-runtime.json', trusted)
            if pending:
                descriptor = materialize.prepare_sealed_case(root, spec, descriptor, python=python)
            publish(root / 'descriptor.json', descriptor)
            record.update(status='prepared', descriptor=str((root / 'descriptor.json').relative_to(output)),
                          descriptor_pin=pin(root / 'descriptor.json'))
        except Exception as error:
            record.update(status='FAILED', error_class=type(error).__name__, reason=str(error),
                          traceback=traceback.format_exc())
        record['finished_at_utc'] = utc()
        records.append(record)
        publish(output / ('prepare-' + spec['control_id'] + '.json'), record)
        print(json.dumps({k: record[k] for k in ('control_id', 'status')}), flush=True)
    result = dict(schema_version=1, status='prepared' if all(r['status'] == 'prepared' for r in records) else 'FAILED',
                  started=started, runtime_proofs=captured_runtime_pins, finished_at_utc=utc(), records=records,
                  scope='unscored native preparation; no oracle decision inferred from validators')
    publish(output / 'PREPARATION.json', result)
    return result['status'] == 'prepared'


def freeze(output):
    prepared = materialize.load(output / 'PREPARATION.json')
    if prepared['status'] != 'prepared':
        raise RuntimeError('Cannot freeze incomplete preparation')
    if (output / 'FROZEN.json').exists():
        raise FileExistsError('Never replace an existing freeze')
    declared = materialize.load(output / 'case-preparation-schedule.json')['cases']
    oracle = materialize.load(output / 'oracle.json')['cases']
    authored_oracle = [dict(control_id=row['control_id'], operation=row['operation'], variant=row['variant'],
        construction_stratum=row['construction_stratum'], **row['oracle']) for row in declared]
    if materialize.digest(oracle) != materialize.digest(authored_oracle):
        raise RuntimeError('Oracle decisions/observables differ from the independently authored schedule')
    if [x['control_id'] for x in declared] != [x['control_id'] for x in oracle]:
        raise RuntimeError('Oracle/schedule case inventory differs')
    declared_ids = [row['control_id'] for row in declared]
    if (len(set(declared_ids)) != len(declared_ids)
            or [row['control_id'] for row in prepared['records']] != declared_ids
            or any(r['status'] != 'prepared' for r in prepared['records'])):
        raise RuntimeError('Some scheduled cases were not prepared')
    if materialize.digest(declared) != materialize.digest(cases.case_specs()):
        raise RuntimeError('Case construction changed after preparation; use fresh complete preparation')
    current_sources = source_pins()
    if prepared['started']['sources'] != current_sources:
        raise RuntimeError('Execution source/policy closure changed after preparation')
    records = []
    for row in prepared['records']:
        descriptor_path = (output / row['descriptor']).resolve()
        if not descriptor_path.is_relative_to(output / 'bundles' / row['control_id']) or pin(descriptor_path) != row['descriptor_pin']:
            raise RuntimeError('Preparation descriptor path/hash differs: ' + row['control_id'])
        descriptor = materialize.load(descriptor_path)
        spec = declared[len(records)]
        if any(descriptor[key] != spec[key] for key in ('control_id', 'operation', 'variant')):
            raise RuntimeError('Prepared descriptor identity differs from schedule')
        records.append(dict(control_id=row['control_id'], descriptor=row['descriptor'],
                            operation=descriptor['operation'], variant=descriptor['variant']))
    trusted = materialize.load(output / 'trusted-runtime.json')
    python = runtime_python(trusted)
    if prepared['runtime_proofs'] != runtime_pins(trusted):
        raise RuntimeError('Qualified runtime evidence changed after preparation')
    installed = installed_inventory(trusted)
    check_trusted_installation(trusted, installed)
    publish(output / 'FROZEN.json', dict(schema_version=2, corpus_version=2, implementations=list(IMPLEMENTATIONS),
        runtime_versions=trusted['versions'], runtime_proofs=runtime_pins(trusted), frozen_at_utc=utc(), status='frozen',
        cases=records, settings=SETTINGS, sources=source_pins(),
        oracle_pin=pin(output / 'oracle.json'), trusted_runtime_pin=pin(output / 'trusted-runtime.json'),
        bundles=tree(output / 'bundles'), bundle_directories=directories(output / 'bundles'),
        python=dict(path=str(python), **pin(python)),
        installed_runtime=installed,
        exposure='Synthetic; authors exposed to policy, code and unit controls. No natural fault prevalence claim.'))


def check_frozen(output, frozen):
    qualifications = qualification_evidence()
    return dict(sources_unchanged=all(pin(PROJECT / path) == expected for path, expected in frozen['sources'].items()),
                qualification_closure_unchanged=all(frozen['sources'].get(path) == expected
                    for path, expected in qualifications.items()),
                bundles_unchanged=tree(output / 'bundles') == frozen['bundles'],
                bundle_directories_unchanged=directories(output / 'bundles') == frozen['bundle_directories'],
                oracle_unchanged=pin(output / 'oracle.json') == frozen['oracle_pin'],
                trusted_runtime_unchanged=pin(output / 'trusted-runtime.json') == frozen['trusted_runtime_pin'],
                installed_runtime_unchanged=installed_inventory(materialize.load(output / 'trusted-runtime.json')) == frozen['installed_runtime'],
                python_unchanged=pin(Path(frozen['python']['path'])) == {k: frozen['python'][k] for k in ('sha256', 'bytes')},
                runtime_proofs_unchanged=all(pin(Path(path)) == proof for path, proof in frozen['runtime_proofs'].items()),
                versioned_grid_unchanged=frozen.get('schema_version') == 2 and frozen.get('corpus_version') == 2
                    and frozen.get('implementations') == list(IMPLEMENTATIONS))


def execute(output):
    frozen = materialize.load(output / 'FROZEN.json')
    python = Path(frozen['python']['path'])
    before = check_frozen(output, frozen)
    if not all(before.values()):
        raise RuntimeError('Frozen inputs changed before execution: ' + str(before))
    result_root = output / 'comparison'
    result_root.mkdir(exist_ok=False)
    publish(result_root / 'STARTED.json', dict(started_at_utc=utc(), freeze_pin=pin(output / 'FROZEN.json'), checks=before))
    results = []
    interrupted = False
    try:
        for repetition in range(frozen['settings']['repetitions']):
            for index, row in enumerate(frozen['cases']):
                shift = (index + repetition) % len(IMPLEMENTATIONS)
                order = IMPLEMENTATIONS[shift:] + IMPLEMENTATIONS[:shift]
                for implementation in order:
                    name = f"{row['control_id']}-r{repetition + 1}-{implementation}"
                    cell = result_root / name
                    cell.mkdir()
                    scratch = cell / 'scratch'
                    temporary = cell / 'temporary'
                    temporary.mkdir()
                    bundle = output / Path(row['descriptor']).parent
                    command = [str(python), '-I', '-B', str(Path(__file__).with_name('worker.py')),
                        '--implementation', implementation, '--root', str(bundle),
                        '--descriptor', 'descriptor.json', '--scratch', str(scratch)]
                    record = dict(schema_version=1, control_id=row['control_id'], repetition=repetition + 1,
                                  implementation=implementation, argv=command, started_at_utc=utc())
                    publish(cell / 'STARTED.json', record)
                    start = time.perf_counter()
                    process = None
                    try:
                        with (cell / 'stdout.json').open('xb') as stdout, (cell / 'stderr.txt').open('xb') as stderr:
                            environment = dict(os.environ, TEMP=str(temporary), TMP=str(temporary), PYTHONDONTWRITEBYTECODE='1')
                            process = subprocess.Popen(command, cwd=cell, env=environment, stdout=stdout, stderr=stderr)
                            reason = None
                            while process.poll() is None:
                                if time.perf_counter() - start > frozen['settings']['deadline_seconds']:
                                    reason = 'timeout'
                                elif ((cell / 'stdout.json').stat().st_size > frozen['settings']['stdout_cap_bytes'] or
                                      (cell / 'stderr.txt').stat().st_size > frozen['settings']['stderr_cap_bytes']):
                                    reason = 'output_limit'
                                if reason:
                                    process.kill()
                                    break
                                time.sleep(0.02)
                            record['exit_code'] = process.wait(timeout=10)
                        # A fast child can finish before the first polling check.
                        # These are qualification thresholds, not hard write caps.
                        if ((cell / 'stdout.json').stat().st_size > frozen['settings']['stdout_cap_bytes'] or
                                (cell / 'stderr.txt').stat().st_size > frozen['settings']['stderr_cap_bytes']):
                            reason = reason or 'output_limit'
                        record['launcher_wall_seconds'] = time.perf_counter() - start
                        if reason:
                            record.update(disposition=reason, result=dict(decision='error', reason=reason))
                        elif record['exit_code']:
                            record.update(disposition='crash', result=dict(decision='error', reason='nonzero worker exit'))
                        else:
                            answer = materialize.load(cell / 'stdout.json')
                            if (answer.get('implementation') != implementation or answer.get('schema_version') != 1
                                    or answer.get('result', {}).get('control_id') != row['control_id']
                                    or answer['result'].get('decision') not in ('accept', 'reject', 'inspect_only', 'unsupported', 'error')):
                                raise ValueError('Malformed or mismatched worker result')
                            record.update(disposition='returned', **{key: answer[key] for key in ('result', 'metrics', 'runtime')})
                    except Exception as error:
                        if process is not None and process.poll() is None:
                            process.kill()
                            process.wait(timeout=10)
                        record.update(disposition='runner_error', result=dict(decision='error', reason=str(error)),
                                      error_class=type(error).__name__)
                    finally:
                        if process is not None and process.poll() is None:
                            process.kill()
                            process.wait(timeout=10)
                    record.update(finished_at_utc=utc(), stdout_pin=pin(cell / 'stdout.json'), stderr_pin=pin(cell / 'stderr.txt'))
                    publish(cell / 'RESULT.json', record)
                    results.append(dict(cell=name, **pin(cell / 'RESULT.json')))
                print(json.dumps(dict(repetition=repetition + 1, completed_case=row['control_id'], terminal_cells=len(results))), flush=True)
    except BaseException:
        interrupted = True
        raise
    finally:
        expected = len(frozen['cases']) * len(IMPLEMENTATIONS) * frozen['settings']['repetitions']
        after = check_frozen(output, frozen)
        publish(result_root / 'EXECUTION.json', dict(schema_version=1,
            status='executed' if len(results) == expected and all(after.values()) and not interrupted else 'incomplete_or_changed',
            expected_cells=expected, terminal_cells=len(results), records=results, after_checks=after, finished_at_utc=utc()))


def analyze(output):
    frozen = materialize.load(output / 'FROZEN.json')
    if not all(check_frozen(output, frozen).values()):
        raise RuntimeError('Frozen source, oracle or bundle changed before analysis')
    started = materialize.load(output / 'comparison/STARTED.json')
    if started['freeze_pin'] != pin(output / 'FROZEN.json'):
        raise RuntimeError('Execution freeze anchor changed')
    oracle = {row['control_id']: row for row in materialize.load(output / 'oracle.json')['cases']}
    execution = materialize.load(output / 'comparison/EXECUTION.json')
    expected_grid = {f"{row['control_id']}-r{rep}-{implementation}": (row['control_id'], rep, implementation)
        for row in frozen['cases'] for rep in range(1, frozen['settings']['repetitions'] + 1)
        for implementation in IMPLEMENTATIONS}
    record_ids = [row['cell'] for row in execution['records']]
    if (execution['status'] != 'executed' or execution['expected_cells'] != len(expected_grid)
            or execution['terminal_cells'] != len(expected_grid) or len(record_ids) != len(expected_grid)
            or set(record_ids) != set(expected_grid)):
        raise RuntimeError('Incomplete or changed execution cannot yield completed comparison')
    rows = []
    totals = {name: Counter() for name in IMPLEMENTATIONS}
    for reference in execution['records']:
        path = output / 'comparison' / reference['cell'] / 'RESULT.json'
        if pin(path) != {k: reference[k] for k in ('sha256', 'bytes')}:
            raise RuntimeError('Terminal record changed: ' + reference['cell'])
        result = materialize.load(path)
        if (result['control_id'], result['repetition'], result['implementation']) != expected_grid[reference['cell']]:
            raise RuntimeError('Terminal cell identity differs from frozen schedule')
        expected = oracle[result['control_id']]
        decision = result['result']['decision']
        mismatches = {}
        for name, value in expected['observables'].items():
            actual = observable_projection(result['result'].get('observables', {}), name)
            if isinstance(value, dict) and isinstance(actual, dict):
                actual = {key: actual.get(key, 'missing') for key in value}
            if materialize.digest(value) != materialize.digest(actual):
                mismatches[name] = dict(expected=value, actual=actual)
        counter = totals[result['implementation']]
        counter.update(cells=1)
        counter['oracle_' + expected['decision']] += 1
        counter['decision_' + decision] += 1
        if decision == 'accept' and expected['decision'] == 'reject':
            counter['false_admission'] += 1
        if decision == 'inspect_only' and expected['decision'] == 'reject':
            counter['invalid_inspection_acceptance'] += 1
        if decision == 'reject' and expected['decision'] == 'accept':
            counter['false_rejection'] += 1
        conformant = decision == expected['decision'] and not mismatches
        counter['fully_conformant'] += int(conformant)
        counter['decision_correct'] += int(decision == expected['decision'])
        rows.append(dict(cell=reference['cell'], control_id=result['control_id'],
            implementation=result['implementation'], repetition=result['repetition'],
            expected_decision=expected['decision'], observed_decision=decision, fully_conformant=conformant,
            observable_mismatches=mismatches, obligation_ids=expected['obligation_ids'],
            construction_stratum=expected['construction_stratum']))
    publish(output / 'ANALYSIS.json', dict(schema_version=1, status='analysis_complete_not_independently_reconstructed',
        unique_cases=len(frozen['cases']), repetitions=frozen['settings']['repetitions'], cells=len(rows),
        totals={key: dict(value) for key, value in totals.items()}, rows=rows,
        scope='Finite fictional conformance controls; repeated cells are not independent samples',
        qualification='Observed policy failures remain failures; BG02 closure requires independent reconstruction and full coverage review'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'freeze', 'run', 'analyze'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, help='Required only for fresh preparation')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(PROJECT / 'data/benchmark'):
        parser.error('Use an isolated fresh path under project data/benchmark')
    if args.command == 'prepare':
        if args.qualification is None:
            parser.error('--qualification is required for preparation')
        qualification = args.qualification.resolve()
        if not qualification.is_relative_to(PROJECT / 'data/cache'):
            parser.error('Use an existing qualified installation under project data/cache')
        result = prepare(output, qualification)
    else:
        if args.qualification is not None:
            parser.error('Frozen commands use their retained installation; do not supply --qualification')
        result = dict(freeze=freeze, run=execute, analyze=analyze)[args.command](output)
    return 1 if result is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
