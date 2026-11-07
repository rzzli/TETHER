"""Prepare, freeze and run the complete BG02 schedule without implicit retries."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy import cases, materialize

PROJECT = Path(__file__).resolve().parents[2]
EVIDENCE = PROJECT / 'planning/review-assets/tether-equal-policy-20261102'
QUALIFIED = PROJECT / 'data/cache/tether-051-installed-qualification-attempt02'
PYTHON = QUALIFIED / 'environment/Scripts/python.exe'
IMPLEMENTATIONS = ('tether', 'independent', 'hash_schema', 'reject_all')
SETTINGS = dict(repetitions=3, deadline_seconds=90, stdout_cap_bytes=4 * 1024 * 1024,
                stderr_cap_bytes=1024 * 1024, provider_cost_usd=0,
                order='rotate four implementations by (case_index + repetition) modulo four',
                timings='descriptive; fresh process each cell, no automatic retries')


def utc():
    return datetime.now(timezone.utc).isoformat()


def publish(path, value):
    with Path(path).open('xb') as stream:
        stream.write(materialize.canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def pin(path):
    return dict(sha256=materialize.file_hash(path), bytes=Path(path).stat().st_size)


def tree(root):
    return {path.relative_to(root).as_posix(): pin(path) for path in sorted(root.rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts}


def directories(root):
    result = []
    for path in sorted(root.rglob('*')):
        if '__pycache__' in path.parts:
            continue
        if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
            raise RuntimeError('Unexpected link/reparse point in frozen corpus: ' + str(path))
        if path.is_dir():
            result.append(path.relative_to(root).as_posix())
    return result


def installed_inventory(trusted):
    """Actual compared product payloads, not an OS/stdlib attestation."""
    paths = trusted['runtime_paths']
    result = {}
    for product in ('tether_engine', 'tether'):
        root = Path(paths[product + '_file']).parent
        result[product] = dict(root=str(root), files={
            path.relative_to(root).as_posix(): pin(path) for path in sorted(root.rglob('*.py'))})
    metadata = {}
    site_packages = Path(paths['tether_engine_file']).parent.parent
    for pattern in ('tether_target_engine-*.dist-info', 'tether_target_agents-*.dist-info'):
        for directory in sorted(site_packages.glob(pattern)):
            for path in sorted(directory.rglob('*')):
                if path.is_file():
                    metadata[path.relative_to(site_packages).as_posix()] = pin(path)
    result['distribution_metadata'] = dict(root=str(site_packages), files=metadata)
    return result


def check_trusted_installation(trusted, installed):
    actual_core = {name: proof['sha256'] for name, proof in installed['tether_engine']['files'].items()}
    actual_facade = {name: proof['sha256'] for name, proof in installed['tether']['files'].items()}
    expected_facade = {name: proof['sha256'] for name, proof in trusted['launcher_proof']['code'].items()}
    if actual_core != trusted['core_code_sha256'] or actual_facade != expected_facade:
        raise RuntimeError('Actual installed product payload differs from trusted runtime manifest')


def source_pins():
    # Independent result reconstruction is separately versioned after execution;
    # it is never imported by a validator or used to determine expected answers.
    paths = [path for path in Path(__file__).parent.glob('*.py')
             if path.name not in ('reconstruct.py', 'test_reconstruct.py')]
    paths += [EVIDENCE / name for name in ('POLICY-SPEC.md', 'policy-spec.json', 'COVERAGE.md',
        'COVERAGE-v1.md', 'COVERAGE-QUALIFICATION-v2.md', 'CASE-PROTOCOL.md',
        'EXECUTION-PROTOCOL.md', 'RUNTIME-WITNESSES.md', 'RUNTIME-WITNESSES.json',
        'runtime-witnesses-02.log', 'runtime-witness-tests-01.log',
        'independent/RESUMPTION-QUALIFICATION-20261105.json',
        'independent/CURRENT-RUNTIME-QUALIFICATION-20261105.json',
        'independent/worker-current-runtime-green01.json',
        'independent/worker-current-runtime-green01.log',
        'independent/policy-peer-current-runtime01.json',
        'independent/policy-peer-current-runtime01.log',
        'independent-policy/unit-current-runtime-green01.json',
        'independent-policy/unit-current-runtime-green01.log',
        'independent-policy/native-current-runtime-green01.json',
        'independent-policy/native-current-runtime-green01.log')]
    coverage = PROJECT / 'planning/review-assets/tether-equal-policy-coverage-20261105'
    paths += [coverage / name for name in ('EVIDENCE-INDEX.json', 'DOCUMENTATION-VALIDATION.json',
                                          'V1-SCOPE-CONTROL.json')]
    paths.append(PROJECT / 'data/cache/tether-equal-policy-runtime-witnesses-20261102-02/RUNTIME-WITNESSES.json')
    return {p.relative_to(PROJECT).as_posix(): pin(p) for p in sorted(paths)}


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    (output / 'bundles').mkdir()
    (output / 'temporary').mkdir()
    os.environ.update(TEMP=str(output / 'temporary'), TMP=str(output / 'temporary'))
    specs = cases.case_specs()
    publish(output / 'case-preparation-schedule.json', dict(schema_version=1, cases=specs))
    publish(output / 'oracle.json', cases.oracle_manifest())
    started = dict(started_at_utc=utc(), sources=source_pins(), cases=len(specs))
    publish(output / 'PREPARATION-STARTED.json', started)
    command = [str(PYTHON), '-I', '-B', str(Path(__file__).with_name('reference.py')),
               '--trusted-runtime', str(QUALIFIED)]
    captured = subprocess.run(command, capture_output=True, check=False, timeout=90)
    (output / 'trusted-runtime.stdout').write_bytes(captured.stdout)
    (output / 'trusted-runtime.stderr').write_bytes(captured.stderr)
    if captured.returncode:
        publish(output / 'PREPARATION.json', dict(status='FAILED', stage='trusted_runtime',
                                                returncode=captured.returncode))
        return False
    trusted = json.loads(captured.stdout)
    publish(output / 'trusted-runtime.json', trusted)
    records = []
    for spec in specs:
        root = output / 'bundles' / spec['control_id']
        record = dict(control_id=spec['control_id'], started_at_utc=utc(), status='preparing')
        try:
            descriptor, pending = cases.write_source_bundle(root, spec, trusted_runtime='trusted-runtime.json')
            publish(root / 'trusted-runtime.json', trusted)
            if pending:
                descriptor = materialize.prepare_sealed_case(root, spec, descriptor, python=PYTHON)
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
                  started=started, finished_at_utc=utc(), records=records,
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
    for filename in ('cases.py', 'materialize.py', 'reference.py', 'policy_cases.py'):
        key = 'experiments/equal_policy/' + filename
        if prepared['started']['sources'][key] != pin(PROJECT / key):
            raise RuntimeError('Producer changed after preparation: ' + key)
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
    installed = installed_inventory(trusted)
    check_trusted_installation(trusted, installed)
    publish(output / 'FROZEN.json', dict(schema_version=1, frozen_at_utc=utc(), status='frozen',
        cases=records, settings=SETTINGS, sources=source_pins(),
        oracle_pin=pin(output / 'oracle.json'), trusted_runtime_pin=pin(output / 'trusted-runtime.json'),
        bundles=tree(output / 'bundles'), bundle_directories=directories(output / 'bundles'),
        python=dict(path=str(PYTHON), **pin(PYTHON)),
        installed_runtime=installed,
        exposure='Synthetic; authors exposed to policy, code and unit controls. No natural fault prevalence claim.'))


def check_frozen(output, frozen):
    return dict(sources_unchanged=all(pin(PROJECT / path) == expected for path, expected in frozen['sources'].items()),
                bundles_unchanged=tree(output / 'bundles') == frozen['bundles'],
                bundle_directories_unchanged=directories(output / 'bundles') == frozen['bundle_directories'],
                oracle_unchanged=pin(output / 'oracle.json') == frozen['oracle_pin'],
                trusted_runtime_unchanged=pin(output / 'trusted-runtime.json') == frozen['trusted_runtime_pin'],
                installed_runtime_unchanged=installed_inventory(materialize.load(output / 'trusted-runtime.json')) == frozen['installed_runtime'],
                python_unchanged=pin(PYTHON) == {k: frozen['python'][k] for k in ('sha256', 'bytes')})


def execute(output):
    frozen = materialize.load(output / 'FROZEN.json')
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
                    command = [str(PYTHON), '-I', '-B', str(Path(__file__).with_name('worker.py')),
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


def observable_projection(observed, name):
    if name in ('admitted_observation_ids', 'eligible_observation_ids', 'selected_observation_ids', 'scorer_preflight'):
        return observed.get(name, {'observable_missing': name})
    prediction = observed.get('prediction', {})
    if name == 'prediction_status':
        return prediction.get('status', {'observable_missing': name})
    if name == 'probability_is_null':
        return prediction['probability'] is None if 'probability' in prediction else 'missing'
    if name == 'prediction_reason':
        return prediction.get('reason', {'observable_missing': name})
    if name in ('feature_values', 'feature_status', 'dependency_groups'):
        field = {'feature_values': 'value', 'feature_status': 'status', 'dependency_groups': 'dependency_groups'}[name]
        return {key: value.get(field, {'observable_missing': name}) for key, value in observed.get('features', {}).get('values', {}).items()}
    if name == 'exclusion_reasons':
        return [row['reason'] for row in observed.get('exclusions', [])]
    if name == 'dispatches':
        return observed.get('calls')
    if name == 'accounting_basis':
        bases = sorted({row['basis'] for row in observed.get('accounting', [])})
        return bases[0] if len(bases) == 1 else bases
    if name == 'later_dispatches':
        # These declared controls breach on the first dispatch. This quantity
        # is specific to those controls, not a generic failure-order inference.
        return len(observed['dispatches']) - 1 if observed.get('dispatches') else 'missing'
    recovery = observed.get('recovery', {})
    if name == 'unresolved_attempts':
        return recovery.get('unresolved_attempts')
    if name == 'recovery_may_dispatch':
        action = recovery.get('recovery_action', '')
        return False if action.startswith('inspect only;') and 'never automatically repeat' in action else 'unqualified'
    raise ValueError('Unimplemented oracle observable: ' + name)


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
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(PROJECT / 'data/benchmark'):
        parser.error('Use an isolated fresh path under project data/benchmark')
    functions = dict(prepare=prepare, freeze=freeze, run=execute, analyze=analyze)
    result = functions[args.command](output)
    return 1 if result is False else 0


if __name__ == '__main__':
    raise SystemExit(main())
