"""Independent reconstruction of BG02 terminal evidence (standard library only).

This module imports no runner, validator, corpus producer or oracle helper. It
reads the independently authored oracle as evaluator data, checks retained bytes,
rebuilds every scheduled disposition, and reports descriptive measurements. A
valid reconstruction may document implementation failures; it is not a claim
that either validator passed every policy control.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import statistics


ARMS = ('tether', 'independent', 'hash_schema', 'reject_all')
DECISIONS = {'accept', 'reject', 'inspect_only', 'unsupported', 'error'}
DISPOSITIONS = {'returned', 'timeout', 'output_limit', 'crash', 'runner_error'}
MISSING = {'independent_reconstruction_missing': True}
MAX_METADATA = 128 * 1024 * 1024


class ReconstructionError(ValueError):
    """Retained evidence is incomplete, changed or internally contradictory."""


def require(condition, message):
    if not condition:
        raise ReconstructionError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def equal(left, right):
    return canonical(left) == canonical(right)


def read_json(path):
    path = Path(path)
    require(path.is_file() and path.stat().st_size <= MAX_METADATA,
            'Missing or oversized JSON metadata: ' + str(path))

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON field: ' + key)
            result[key] = value
        return result

    def invalid(value):
        raise ReconstructionError('Nonfinite JSON constant: ' + value)

    try:
        return json.loads(path.read_bytes().decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReconstructionError('Malformed JSON: ' + str(path)) from error


def file_pin(path):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
            'Expected ordinary file: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    after = path.stat()
    require((info.st_size, info.st_mtime_ns, info.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'File changed during reconstruction: ' + str(path))
    return {'sha256': digest.hexdigest(), 'bytes': after.st_size}


def checked_pin(path, expected):
    require(type(expected) is dict and type(expected.get('bytes')) is int and expected['bytes'] >= 0
            and type(expected.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', expected['sha256']),
            'Malformed file pin: ' + str(path))
    observed = file_pin(path)
    require(equal(observed, {'sha256': expected['sha256'], 'bytes': expected['bytes']}),
            'File pin changed: ' + str(path))
    return observed


def child(root, relative):
    require(type(relative) is str and relative and not Path(relative).is_absolute(), 'Unsafe relative record path')
    parts = relative.replace('\\', '/').split('/')
    require(':' not in relative and all(part not in ('', '.', '..') for part in parts), 'Unsafe relative record path')
    root = Path(root).resolve()
    path = root.joinpath(*parts)
    require(path.resolve().is_relative_to(root), 'Record path escaped its root')
    return path


def directory_inventory(root):
    root = Path(root)
    require(root.is_dir(), 'Missing inventory root: ' + str(root))
    info = root.lstat()
    require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
            'Nonordinary inventory root: ' + str(root))
    files, directories = {}, []
    for current, children, names in os.walk(root, followlinks=False):
        children[:] = sorted(name for name in children if name != '__pycache__')
        for name in children:
            path = Path(current) / name
            info = path.lstat()
            require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Nonordinary inventory directory: ' + str(path))
            directories.append(path.relative_to(root).as_posix())
        for name in sorted(names):
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = file_pin(path)
    return dict(files=files, directories=sorted(directories))


def frozen_inputs(project, output, frozen):
    require(equal(frozen.get('schema_version'), 1) and frozen.get('status') == 'frozen', 'Unfrozen comparison')
    checked_pin(output / 'oracle.json', frozen['oracle_pin'])
    checked_pin(output / 'trusted-runtime.json', frozen['trusted_runtime_pin'])
    sources = frozen['sources']
    require(type(sources) is dict and sources, 'Empty implementation source inventory')
    for relative, expected in sources.items():
        checked_pin(child(project, relative), expected)
    inventory = directory_inventory(output / 'bundles')
    require(equal(inventory['files'], frozen['bundles']), 'Bundle file inventory changed')
    require(equal(inventory['directories'], frozen['bundle_directories']), 'Bundle directory inventory changed')
    python = Path(frozen['python']['path']).resolve()
    require(python.is_relative_to(project), 'Pinned interpreter lies outside the project qualification')
    checked_pin(python, frozen['python'])
    check_installed_manifest(project, frozen['installed_runtime'])
    return dict(source_files=len(sources), bundle_files=len(inventory['files']),
                bundle_directories=len(inventory['directories']),
                bundle_bytes=sum(value['bytes'] for value in inventory['files'].values()),
                python=str(python))


def check_installed_manifest(project, declaration):
    require(type(declaration) is dict and set(declaration) == {'tether_engine', 'tether', 'distribution_metadata'},
            'Installed runtime inventory lacks required groups')
    for name, group in declaration.items():
        base = Path(group['root']).resolve()
        require(base.is_relative_to(project), 'Installed runtime inventory escaped project')
        if name == 'distribution_metadata':
            paths = []
            for prefix in ('tether_target_engine-', 'tether_target_agents-'):
                for directory in base.glob(prefix + '*.dist-info'):
                    paths.extend(path for path in directory.rglob('*') if path.is_file())
        else:
            paths = [path for path in base.rglob('*.py') if '__pycache__' not in path.parts]
        actual = {path.relative_to(base).as_posix(): file_pin(path) for path in sorted(paths)}
        require(actual and equal(actual, group['files']), 'Installed runtime group changed: ' + name)


def installed_inventory(project, trusted):
    require(equal(trusted.get('schema_version'), 1), 'Invalid trusted runtime schema')
    paths = trusted['runtime_paths']
    versions = trusted['versions']
    proof = trusted['launcher_proof']
    require(proof['core_version'] == versions['tether_engine'] and proof['facade_version'] == versions['tether'],
            'Runtime version/proof contradiction')
    groups = {}
    for package, path_key, expected in (
        ('tether_engine', 'tether_engine_file', trusted['core_code_sha256']),
        ('tether', 'tether_file', {name: entry['sha256'] for name, entry in proof['code'].items()}),
    ):
        base = Path(paths[path_key]).resolve().parent
        require(base.is_relative_to(project) and expected, 'Unqualified or empty installed package inventory')
        actual = {path.relative_to(base).as_posix(): file_pin(path)
                  for path in sorted(base.rglob('*.py')) if '__pycache__' not in path.parts}
        require({name: value['sha256'] for name, value in actual.items()} == expected,
                'Installed package Python inventory changed: ' + package)
        if package == 'tether':
            for name, value in actual.items():
                require(value['bytes'] == proof['code'][name]['bytes'] and proof['code'][name]['path'] == name,
                        'Launcher code descriptor differs')
        groups[package] = dict(root=str(base), files=actual)
    qualification = Path(trusted['qualification']['path']).resolve()
    require(qualification.is_relative_to(project), 'Qualification anchor escaped project')
    require(file_pin(qualification)['sha256'] == trusted['qualification']['sha256'], 'Qualification receipt changed')
    for row in trusted['wheels']:
        require(Path(row['filename']).name == row['filename'], 'Unsafe wheel filename')
        checked_pin(qualification.parent / 'wheels' / row['filename'], row)
    return groups


def get_path(document, *path):
    current = document
    for key in path:
        if type(current) is not dict or key not in current:
            return MISSING
        current = current[key]
    return current


def observable(document, name, expected):
    """Direct interpretation of the predeclared observable semantics."""
    direct = {'admitted_observation_ids', 'eligible_observation_ids', 'selected_observation_ids', 'scorer_preflight'}
    if name in direct:
        return get_path(document, name)
    if name in ('prediction_status', 'prediction_reason'):
        return get_path(document, 'prediction', name.removeprefix('prediction_'))
    if name == 'probability_is_null':
        prediction = get_path(document, 'prediction')
        if type(prediction) is dict and 'probability' in prediction:
            return prediction['probability'] is None
        return MISSING
    feature_fields = {'feature_values': 'value', 'feature_status': 'status', 'dependency_groups': 'dependency_groups'}
    if name in feature_fields:
        require(type(expected) is dict, 'Feature oracle must specify named features')
        return {key: get_path(document, 'features', 'values', key, feature_fields[name]) for key in expected}
    if name == 'exclusion_reasons':
        values = get_path(document, 'exclusions')
        return [get_path(row, 'reason') for row in values] if type(values) is list else MISSING
    if name == 'dispatches':
        return get_path(document, 'calls')
    if name == 'accounting_basis':
        accounts = get_path(document, 'accounting')
        if type(accounts) is not list or not accounts or any(type(row) is not dict or 'basis' not in row for row in accounts):
            return MISSING
        values = set(row['basis'] for row in accounts)
        return next(iter(values)) if len(values) == 1 else sorted(values)
    if name == 'later_dispatches':
        # The authored overquote controls breach on their first attempt.
        dispatched = get_path(document, 'dispatches')
        return len(dispatched) - 1 if type(dispatched) is list and dispatched else MISSING
    if name == 'unresolved_attempts':
        return get_path(document, 'recovery', 'unresolved_attempts')
    if name == 'recovery_may_dispatch':
        action = get_path(document, 'recovery', 'recovery_action')
        if type(action) is str and action.startswith('inspect only;') and 'never automatically repeat' in action:
            return False
        return MISSING
    raise ReconstructionError('Unknown authored observable: ' + name)


def score_cell(result, oracle):
    require(type(result) is dict and result.get('decision') in DECISIONS, 'Invalid retained decision')
    mismatch = {}
    for name, expected in oracle['observables'].items():
        actual = observable(result.get('observables', {}), name, expected)
        if not equal(actual, expected):
            mismatch[name] = dict(expected=expected, actual=actual)
    decision = result['decision']
    return dict(expected_decision=oracle['decision'], observed_decision=decision,
                decision_correct=decision == oracle['decision'],
                fully_conformant=decision == oracle['decision'] and not mismatch,
                observable_mismatches=mismatch)


def tally(rows):
    counter = Counter()
    for row in rows:
        expected, observed = row['expected_decision'], row['observed_decision']
        counter['cells'] += 1
        counter['oracle_' + expected] += 1
        counter['decision_' + observed] += 1
        counter['decision_correct'] += int(row['decision_correct'])
        counter['fully_conformant'] += int(row['fully_conformant'])
        if expected == 'reject' and observed == 'accept':
            counter['false_admission'] += 1
        if expected == 'accept' and observed == 'reject':
            counter['false_rejection'] += 1
        if expected == 'reject' and observed == 'inspect_only':
            counter['invalid_inspection_acceptance'] += 1
    return dict(counter)


def rates(counts):
    def fraction(numerator, denominator):
        return dict(numerator=counts.get(numerator, 0), denominator=counts.get(denominator, 0),
                    fraction=counts.get(numerator, 0) / counts[denominator] if counts.get(denominator) else None)
    return dict(false_admission=fraction('false_admission', 'oracle_reject'),
                false_rejection=fraction('false_rejection', 'oracle_accept'),
                conformance=fraction('fully_conformant', 'cells'))


def statistics_for(values):
    present = [value for value in values if value is not None]
    require(all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in present),
            'Invalid nonnegative resource measurement')
    ordered = sorted(present)
    return dict(observations=len(present), unavailable=len(values) - len(present),
                minimum=min(present) if present else None, median=statistics.median(present) if present else None,
                maximum=max(present) if present else None, total=sum(present) if present else None,
                p95_nearest_rank=ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else None)


def resource_row(record, cell):
    metrics = record.get('metrics', {})
    def metric(*path):
        value = get_path(metrics, *path)
        return None if value == MISSING else value
    scratch = directory_inventory(cell / 'scratch') if (cell / 'scratch').exists() else dict(files={}, directories=[])
    result = dict(launcher_wall_seconds=record.get('launcher_wall_seconds'),
        import_wall_seconds=metric('import_wall_seconds'), operation_wall_seconds=metric('operation_wall_seconds'),
        import_cpu_seconds=metric('import_cpu_seconds'), operation_cpu_seconds=metric('operation_cpu_seconds'),
        python_import_peak_bytes=metric('import_traced_peak_bytes'),
        python_operation_peak_bytes=metric('operation_traced_peak_bytes'),
        python_operation_incremental_peak_bytes=metric('operation_traced_peak_above_start_bytes'),
        os_process_peak_bytes=metric('os_process_memory', 'peak_bytes'),
        logical_input_bytes=metric('bundle_inventory', 'unique_logical_bytes'),
        logical_input_files=metric('bundle_inventory', 'file_count'),
        retained_scratch_bytes=sum(value['bytes'] for value in scratch['files'].values()),
        retained_scratch_files=len(scratch['files']))
    for kind in ('wall', 'cpu'):
        first, second = result['import_' + kind + '_seconds'], result['operation_' + kind + '_seconds']
        result['python_total_' + kind + '_seconds'] = first + second if first is not None and second is not None else None
    for value in result.values():
        statistics_for([value])
    return result


def implementation_identity(project, frozen, trusted, record, output, descriptor):
    arm = record['implementation']
    runtime = record['runtime']
    require(runtime.get('isolated') is True and runtime.get('repository_product_source_on_path') is False,
            'Worker does not establish isolated installed imports')
    require(Path(runtime['python']).resolve() == Path(frozen['python']['path']).resolve(), 'Worker interpreter changed')
    wanted = {'tether': 'reference.py', 'independent': 'independent.py', 'hash_schema': 'controls.py', 'reject_all': 'controls.py'}[arm]
    require(Path(runtime['implementation_file']).resolve() == (project / 'experiments/equal_policy' / wanted).resolve(),
            'Worker implementation module differs')
    loaded = runtime['loaded_product_modules']
    if arm == 'tether':
        require(set(loaded) == {'tether_engine', 'tether'}, 'Reference worker omitted product identity')
        for name in loaded:
            require(Path(loaded[name]).resolve() == Path(trusted['runtime_paths'][name + '_file']).resolve(),
                    'Reference product import escaped pinned installation')
    else:
        require(loaded == {}, 'Independent/control worker imported product validator')
    argv = record['argv']
    require(type(argv) is list and len(argv) == 12 and argv[1:3] == ['-I', '-B'], 'Worker invocation differs')
    require(Path(argv[0]).resolve() == Path(frozen['python']['path']).resolve(), 'Worker invocation interpreter differs')
    require(Path(argv[3]).resolve() == (project / 'experiments/equal_policy/worker.py').resolve(), 'Worker launcher differs')
    require(argv[4::2] == ['--implementation', '--root', '--descriptor', '--scratch'], 'Worker option inventory differs')
    require(argv[5] == arm and Path(argv[7]).resolve() == child(output, descriptor['descriptor']).parent.resolve()
            and argv[9] == Path(descriptor['descriptor']).name, 'Worker input descriptor differs')
    require(Path(argv[11]).resolve() == (output / 'comparison' / record['cell'] / 'scratch').resolve(),
            'Worker scratch binding differs')


def footprint(project, frozen, installation):
    groups = defaultdict(list)
    independent_names = {'independent.py', 'independent_schema.py', 'independent_local.py',
                         'independent_render.py', 'independent_policy.py', 'independent_runtime.py'}
    for relative, pin in frozen['sources'].items():
        path = child(project, relative)
        if path.suffix != '.py':
            category = 'frozen_protocol_documentation'
        elif path.name in independent_names:
            category = 'independent_validator'
        elif path.name == 'reference.py':
            category = 'reference_adapter'
        elif path.name.startswith('test_'):
            category = 'frozen_experiment_tests'
        elif path.name in {'cases.py', 'policy_cases.py', 'materialize.py'}:
            category = 'fictional_corpus_construction'
        elif path.name == 'controls.py':
            category = 'diagnostic_controls'
        elif path.name == 'runtime_witnesses.py':
            category = 'runtime_only_witnesses'
        else:
            category = 'comparison_infrastructure'
        groups[category].append(source_size(path, relative, pin))
    for name, value in installation.items():
        for relative, pin in value['files'].items():
            path = Path(value['root']) / relative
            groups['installed_' + name + '_whole_package'].append(source_size(path, relative, pin))
    result = {}
    for group, files in sorted(groups.items()):
        result[group] = dict(file_count=len(files), bytes=sum(x['bytes'] for x in files),
            physical_lines=sum(x['physical_lines'] for x in files),
            nonblank_noncomment_lines=sum(x['nonblank_noncomment_lines'] for x in files),
            functions=sum(x['functions'] for x in files), classes=sum(x['classes'] for x in files), files=files)
    return dict(groups=result,
        scope='Pinned source inventory and complete installed Python inventories; package counts include archive/study modules outside this comparison',
        limitations=['Line/function counts are descriptive maintenance surface, not cyclomatic complexity or proof of simpler guarantees.',
                     'Frozen experiment tests exclude unpinned tests elsewhere in the repository; qualification logs supply their separate scope.',
                     'This evaluator and its tests are separately pinned and not charged to either implementation.',
                     'Python standard-library implementation bytes and operating-system dependencies are not counted.'])


def source_size(path, label, pin):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    functions = classes = 0
    if path.suffix == '.py':
        nodes = list(ast.walk(ast.parse('\n'.join(lines))))
        functions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in nodes)
        classes = sum(isinstance(node, ast.ClassDef) for node in nodes)
    return dict(path=label, **pin, physical_lines=len(lines),
                nonblank_noncomment_lines=sum(bool(line.strip()) and not line.lstrip().startswith('#') for line in lines),
                functions=functions, classes=classes)


def root_concordance(path, rows, totals):
    if not path.exists():
        return dict(status='not_available', reason='Primary analysis has not been retained')
    primary = read_json(path)
    require(primary['cells'] == len(rows) and len(primary['rows']) == len(rows), 'Primary analysis denominator differs')
    indexed = {row['cell']: row for row in primary['rows']}
    require(len(indexed) == len(rows) and set(indexed) == {row['cell'] for row in rows}, 'Primary analysis cell inventory differs')
    for row in rows:
        original = indexed[row['cell']]
        for key in ('control_id', 'implementation', 'repetition', 'expected_decision', 'observed_decision', 'fully_conformant',
                    'obligation_ids', 'construction_stratum'):
            require(equal(original[key], row[key]), 'Primary analysis disagrees on ' + row['cell'] + '/' + key)
        require(set(original['observable_mismatches']) == set(row['observable_mismatches']),
                'Primary observable mismatch inventory differs: ' + row['cell'])
    for arm in ARMS:
        original = primary['totals'][arm]
        ours = totals[arm]
        require(all(original.get(key, 0) == ours.get(key, 0) for key in set(original) | set(ours)),
                'Primary total counts disagree: ' + arm)
    return dict(status='agrees', primary_analysis_pin=file_pin(path),
                comparison='Every cell decision, conformance, mismatch-key set, grouping and total; missing-value sentinel formatting is evaluator-specific')


def reconstruct(project, output, *, require_primary=True):
    project, output = Path(project).resolve(), Path(output).resolve()
    require(output.is_relative_to(project), 'Comparison must be inside project')
    frozen = read_json(output / 'FROZEN.json')
    integrity = frozen_inputs(project, output, frozen)
    trusted = read_json(output / 'trusted-runtime.json')
    installation = installed_inventory(project, trusted)
    require(Path(trusted['runtime_paths']['python']).resolve() == Path(frozen['python']['path']).resolve(),
            'Trusted and frozen interpreter anchors disagree')
    for name in ('tether_engine', 'tether'):
        require(equal(installation[name], frozen['installed_runtime'][name]),
                'Trusted and frozen package inventories disagree: ' + name)
    started = read_json(output / 'comparison/STARTED.json')
    checked_pin(output / 'FROZEN.json', started['freeze_pin'])
    anchors = {name: file_pin(output / relative) for name, relative in (
        ('freeze', 'FROZEN.json'), ('execution', 'comparison/EXECUTION.json'),
        ('oracle', 'oracle.json'), ('trusted_runtime', 'trusted-runtime.json'))}
    execution = read_json(output / 'comparison/EXECUTION.json')
    require(equal(execution.get('schema_version'), 1) and execution.get('status') == 'executed', 'Comparison did not finish')
    schedule = frozen['cases']
    case_ids = [row['control_id'] for row in schedule]
    require(case_ids and len(case_ids) == len(set(case_ids)), 'Duplicate or empty frozen case schedule')
    oracle_rows = read_json(output / 'oracle.json')['cases']
    require([row['control_id'] for row in oracle_rows] == case_ids, 'Oracle case inventory differs')
    oracle = {row['control_id']: row for row in oracle_rows}
    descriptor_index = {row['control_id']: row for row in schedule}
    for row in schedule:
        require(oracle[row['control_id']]['decision'] in {'accept', 'reject', 'inspect_only'}, 'Unsupported oracle decision')
        require(all(row[key] == oracle[row['control_id']][key] for key in ('operation', 'variant')), 'Oracle operation/variant mismatch')
        descriptor = read_json(child(output, row['descriptor']))
        require(all(descriptor[key] == row[key] for key in ('control_id', 'operation', 'variant')), 'Descriptor/schedule mismatch')
    repetitions = frozen['settings']['repetitions']
    require(type(repetitions) is int and repetitions > 0, 'Invalid repetition count')
    order = []
    for repeat in range(1, repetitions + 1):
        for index, case_id in enumerate(case_ids):
            offset = (index + repeat - 1) % len(ARMS)
            for arm in ARMS[offset:] + ARMS[:offset]:
                order.append((f'{case_id}-r{repeat}-{arm}', case_id, repeat, arm))
    expected_names = [value[0] for value in order]
    records = execution['records']
    require(execution['expected_cells'] == len(order) == execution['terminal_cells'] == len(records), 'Terminal count differs from exact grid')
    require([row['cell'] for row in records] == expected_names, 'Terminal inventory/order differs from exact grid')
    actual_cell_directories = {path.name for path in (output / 'comparison').iterdir() if path.is_dir()}
    require(actual_cell_directories == set(expected_names), 'Unlisted or missing invocation directory')
    rows = []
    resource_rows = []
    for reference, expected_cell in zip(records, order):
        name, case_id, repeat, arm = expected_cell
        cell = child(output / 'comparison', name)
        record_path = cell / 'RESULT.json'
        checked_pin(record_path, reference)
        record = read_json(record_path)
        require(equal(record.get('schema_version'), 1), 'Invalid terminal schema')
        require(equal([record.get('control_id'), record.get('repetition'), record.get('implementation')], [case_id, repeat, arm]),
                'Terminal identity differs: ' + name)
        require(record['disposition'] in DISPOSITIONS, 'Unknown terminal disposition')
        checked_pin(cell / 'stdout.json', record['stdout_pin'])
        checked_pin(cell / 'stderr.txt', record['stderr_pin'])
        if record['disposition'] == 'returned':
            require(equal(record.get('exit_code'), 0), 'Returned worker has nonzero exit')
            worker = read_json(cell / 'stdout.json')
            require(equal(worker.get('schema_version'), 1) and worker.get('implementation') == arm, 'Worker output identity differs')
            for key in ('result', 'metrics', 'runtime'):
                require(equal(worker[key], record[key]), 'Worker/terminal projection differs: ' + name + '/' + key)
            result = record['result']
            require(equal(result.get('schema_version'), 1) and result.get('control_id') == case_id, 'Decision identity differs')
            required = {'schema_version', 'control_id', 'decision', 'stage', 'violated_obligations', 'checked_scope', 'observables'}
            require(required <= result.keys() and type(result['observables']) is dict, 'Incomplete decision contract')
            require(record['stdout_pin']['bytes'] <= frozen['settings']['stdout_cap_bytes']
                    and record['stderr_pin']['bytes'] <= frozen['settings']['stderr_cap_bytes'], 'Returned worker exceeded output qualification threshold')
            implementation_identity(project, frozen, trusted, {**record, 'cell': name}, output, descriptor_index[case_id])
        else:
            require(record['result']['decision'] == 'error', 'Failed invocation relabeled as policy success/rejection')
        evaluation = score_cell(record['result'], oracle[case_id])
        rows.append(dict(cell=name, control_id=case_id, repetition=repeat, implementation=arm,
            disposition=record['disposition'], operation=oracle[case_id]['operation'], variant=oracle[case_id]['variant'],
            obligation_ids=oracle[case_id]['obligation_ids'], construction_stratum=oracle[case_id]['construction_stratum'], **evaluation))
        resource_rows.append(dict(cell=name, control_id=case_id, repetition=repeat, implementation=arm,
            operation=oracle[case_id]['operation'], variant=oracle[case_id]['variant'], **resource_row(record, cell)))
    totals = {arm: tally([row for row in rows if row['implementation'] == arm]) for arm in ARMS}
    by_family, by_stratum, by_surface = {}, {}, {}
    for field, destination in (('obligation_ids', by_family), ('construction_stratum', by_stratum)):
        values = sorted({item for row in rows for item in (row[field] if type(row[field]) is list else [row[field]])})
        for value in values:
            subset = [row for row in rows if value in row[field]] if field == 'obligation_ids' else [row for row in rows if row[field] == value]
            destination[value] = {arm: tally([row for row in subset if row['implementation'] == arm]) for arm in ARMS}
    for operation, variant in sorted({(row['operation'], row['variant']) for row in rows}):
        subset = [row for row in rows if row['operation'] == operation and row['variant'] == variant]
        by_surface[operation + '/' + variant] = {arm: tally([row for row in subset if row['implementation'] == arm]) for arm in ARMS}
    measurements, measurements_by_surface = {}, {}
    identity_fields = {'cell', 'control_id', 'repetition', 'implementation', 'operation', 'variant'}
    for arm in ARMS:
        selected = [row for row in resource_rows if row['implementation'] == arm]
        measurements[arm] = {key: statistics_for([row[key] for row in selected]) for key in selected[0] if key not in identity_fields}
        for operation, variant in sorted({(row['operation'], row['variant']) for row in selected}):
            subset = [row for row in selected if row['operation'] == operation and row['variant'] == variant]
            measurements_by_surface.setdefault(operation + '/' + variant, {})[arm] = {
                key: statistics_for([row[key] for row in subset]) for key in subset[0] if key not in identity_fields}
    paired = []
    for case_id in case_ids:
        values = {}
        for arm in ('tether', 'independent'):
            selected = [row for row in resource_rows if row['control_id'] == case_id and row['implementation'] == arm]
            times = [row['python_total_wall_seconds'] for row in selected]
            complete = all(value is not None for value in times)
            values[arm] = statistics.median(times) if complete else None
        paired.append(dict(control_id=case_id, median_python_total_wall_seconds=values,
            tether_minus_independent_seconds=values['tether'] - values['independent'] if all(v is not None for v in values.values()) else None,
            tether_over_independent_ratio=values['tether'] / values['independent'] if values['tether'] is not None and values['independent'] else None,
            both_fully_conformant_all_repetitions=all(row['fully_conformant'] for row in rows
                if row['control_id'] == case_id and row['implementation'] in ('tether', 'independent'))))
    concordance = root_concordance(output / 'ANALYSIS.json', rows, totals)
    require(not require_primary or concordance['status'] == 'agrees', 'Primary analysis unavailable for required independent concordance')
    before = dict(integrity)
    require(equal(frozen_inputs(project, output, frozen), before), 'Inputs changed while reconstructing')
    for name, relative in (('freeze', 'FROZEN.json'), ('execution', 'comparison/EXECUTION.json'),
                           ('oracle', 'oracle.json'), ('trusted_runtime', 'trusted-runtime.json')):
        checked_pin(output / relative, anchors[name])
    return dict(schema_version=1, status='reconstructed', completed_at_utc=datetime.now(timezone.utc).isoformat(),
        independent_evaluator=dict(path=str(Path(__file__).resolve()), **file_pin(__file__),
            method='Separate standard-library implementation; no runner, validator or corpus-producer imports'),
        input_anchors=anchors,
        integrity=integrity, unique_cases=len(schedule), repetitions=repetitions, terminal_cells=len(rows),
        totals=totals, rates={arm: rates(totals[arm]) for arm in ARMS}, by_obligation=by_family,
        by_exposure=by_stratum, by_surface=by_surface, resource_summaries=measurements,
        resource_summaries_by_surface=measurements_by_surface, paired_case_timings=paired,
        resource_rows=resource_rows, rows=rows, primary_analysis_concordance=concordance,
        implementation_footprint=footprint(project, frozen, installation),
        limitations=[
            'All cases are artificial, authored with access to repository and policy. No natural fault prevalence or scientific efficacy inference.',
            'Repetitions are timing/replay observations, not additional independent cases; policy-family denominators overlap.',
            'An integrity reconstruction does not prove that either implementation fulfills every clause outside tested controls.',
            'Tracemalloc-instrumented timings include Python allocation instrumentation; fresh worker process startup is separate launcher wall time.',
            'OS peak memory covers the worker lifetime, including imports; Python allocation peaks omit non-Python allocations.',
            'Scratch bytes are a postrun retained-file inventory, not cumulative copy/write traffic or an execution-time peak.',
            'Logical input inventory includes all bundled preparation/control files, not solely bytes consumed by the validator.',
            'Actual logical read traffic and physical disk/cache behavior are unmeasured.',
            'Local consistency hashes and pinned environment files are not a signed external attestation of execution or filesystem ownership.',
        ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-missing-primary', action='store_true')
    args = parser.parse_args()
    destination = args.output.resolve()
    require(destination.is_relative_to(args.project.resolve()), 'Reconstruction output must be inside project')
    require(not destination.exists(), 'Never replace an existing reconstruction')
    report = reconstruct(args.project, args.run, require_primary=not args.allow_missing_primary)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(canonical(report) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(dict(status=report['status'], unique_cases=report['unique_cases'], terminal_cells=report['terminal_cells'],
                          totals=report['totals'], output=str(destination), output_pin=file_pin(destination)), indent=2))


if __name__ == '__main__':
    main()
