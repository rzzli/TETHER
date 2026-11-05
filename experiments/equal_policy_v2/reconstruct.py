"""Independent v2 reconstruction; no execution/producer/validator imports.

Frozen-v2 anchors and versioned worker identities are checked here. Byte I/O,
observable interpretation, resource aggregation and statistical primitives reuse
the separately qualified, unchanged v1 independent evaluator, pinned below.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy import reconstruct as shared
from equal_policy.reconstruct import (
    ARMS, DECISIONS, DISPOSITIONS, MISSING, ReconstructionError,
    require, canonical, equal, read_json, file_pin, checked_pin, child,
    directory_inventory, check_installed_manifest, installed_inventory,
    get_path, observable, score_cell, tally, rates, statistics_for,
    source_size, root_concordance,
)

SHARED_EVALUATOR_SHA256 = 'a62b9019e4d820b485bcc6918a17b6c627a523df50ab8c833caafafb5ffbed65'
SUPPORTED_PAIRS = {('0.5.1', '0.3.12'), ('0.5.2', '0.3.13')}
EXECUTION_SOURCE_CLOSURE = {
    'experiments/equal_policy/' + name for name in (
        'worker.py', 'reference.py', 'run_comparison.py', 'cases.py', 'materialize.py',
        'policy_cases.py', 'controls.py', 'independent.py', 'independent_schema.py',
        'independent_local.py', 'independent_render.py', 'independent_policy.py', 'independent_runtime.py')
} | {'experiments/equal_policy_v2/' + name for name in (
    'worker.py', 'reference.py', 'run_comparison.py', 'cases.py', 'materialize.py',
    'independent.py', 'independent_runtime.py')}
QUALIFICATION_RECEIPTS = {
    'planning/review-assets/tether-equal-policy-result-review-20261105/CORPUS-V2-QUALIFICATION.json': (
        'PASS_CONSTRUCTION_AND_ADMISSION_ONLY', (
            'experiments/equal_policy_v2/cases.py', 'experiments/equal_policy_v2/test_cases.py',
            'planning/review-assets/tether-equal-policy-result-review-20261105/corpus-v2-red01.log',
            'planning/review-assets/tether-equal-policy-result-review-20261105/corpus-v2-green02.log',
            'planning/review-assets/tether-ce-fixes-20261102/integration/full-gate-04.log',
            'planning/review-assets/tether-ce-fixes-20261102/integration/full-gate-04.source-bracket.json',
            'tests/test_ce02_usage_accounting.py')),
    'planning/review-assets/tether-equal-policy-result-review-20261105/INDEPENDENT-V2-QUALIFICATION.json': (
        'PASS_COMPONENT_QUALIFICATION', (
            'experiments/equal_policy_v2/independent.py', 'experiments/equal_policy_v2/independent_runtime.py',
            'experiments/equal_policy_v2/test_independent.py',
            'planning/review-assets/tether-equal-policy-result-review-20261105/independent-v2-unit01.log',
            'planning/review-assets/tether-equal-policy-result-review-20261105/independent-v2-native01.log')),
    'planning/review-assets/tether-equal-policy-v2-20261105/runner/QUALIFICATION-CLOSURE-20261105.json': (
        'PASS_RUNNER_QUALIFICATION', (
            'experiments/equal_policy_v2/run_comparison.py', 'experiments/equal_policy_v2/worker.py',
            'experiments/equal_policy_v2/reference.py', 'experiments/equal_policy_v2/test_runner.py',
            'experiments/equal_policy_v2/test_reference_worker.py',
            'planning/review-assets/tether-equal-policy-v2-20261105/runner/qualify_runner_closure.py',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/QUALIFICATION.json',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/unit.stdout',
            'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03/unit.stderr')),
}


def qualification_anchors(project, frozen):
    references = set()
    for relative, (status, mandatory) in QUALIFICATION_RECEIPTS.items():
        require(relative in frozen['sources'], 'Qualification receipt omitted from freeze')
        document = read_json(child(project, relative))
        require(equal(document.get('schema_version'), 1) and document.get('status') == status,
                'Qualification status/schema differs')
        rows = document.get('pins')
        require(type(rows) is list and rows, 'Qualification evidence absent')
        declared = set()
        for row in rows:
            name = row['path']
            require(name not in declared and name != relative, 'Duplicate/self-referential qualification pin')
            declared.add(name)
            require(name in frozen['sources'], 'Qualification input omitted from freeze')
            proof = checked_pin(child(project, name), row)
            require(equal(frozen['sources'][name], proof), 'Qualification/freeze input pin differs')
        require(set(mandatory) <= declared, 'Qualification source/log closure incomplete')
        references.update(declared)
    return dict(qualification_receipts=len(QUALIFICATION_RECEIPTS), qualification_input_files=len(references))


def runtime_anchors(project, frozen, trusted):
    versions = trusted['versions']
    require(type(versions) is dict and set(versions) == {'asof', 'tether'}
            and (versions['tether'], versions['asof']) in SUPPORTED_PAIRS,
            'Unsupported version pair')
    require(equal(frozen['runtime_versions'], versions), 'Frozen/trusted versions differ')
    qualification = Path(trusted['qualification']['path']).resolve()
    require(qualification.is_relative_to(project), 'Qualification escaped project')
    environment = qualification.parent / 'environment'
    require(Path(frozen['python']['path']).resolve() == environment / 'Scripts/python.exe',
            'Frozen interpreter is not the declared qualified interpreter')
    document = read_json(qualification)
    require(document.get('status') == 'PASS', 'Qualification did not pass')
    require(equal(document.get('versions'), {name + '-target-agents': version for name, version in versions.items()}),
            'Qualification/package versions differ')
    expected = {str(qualification): file_pin(qualification)}
    require(expected[str(qualification)]['sha256'] == trusted['qualification']['sha256'],
            'Qualification/trusted pin differs')
    wheels = trusted['wheels']
    require(type(wheels) is list and len(wheels) == 2, 'Expected exactly two trusted wheels')
    declared = document.get('wheel_proofs')
    require(type(declared) is list and len(declared) == 2, 'Expected two qualification wheel proofs')
    wheel_paths = []
    for row in wheels:
        name = row['filename']
        require(type(name) is str and Path(name).name == name and name.endswith('.whl'), 'Unsafe wheel filename')
        path = qualification.parent / 'wheels' / name
        expected[str(path)] = checked_pin(path, row)
        wheel_paths.append(path.resolve())
    require(len(set(wheel_paths)) == 2 and set(wheel_paths) ==
            {p.resolve() for p in (qualification.parent / 'wheels').glob('*.whl')},
            'Qualified wheel inventory changed')
    require({Path(row['path']).resolve() for row in declared} == set(wheel_paths),
            'Qualification wheel paths differ')
    for package in ('asof', 'tether'):
        proofs = [row for row in declared if row.get('distribution') == package + '-target-agents']
        require(len(proofs) == 1 and proofs[0].get('record_verified') is True,
                'Missing verified wheel distribution')
        proof = proofs[0]
        checked_pin(Path(proof['path']), proof)
        entry = Path(trusted['runtime_paths'][package + '_file']).resolve()
        require(entry.is_relative_to(environment) and entry.name == '__init__.py',
                'Package entry escaped qualified environment')
        assignments = [node.value.value for node in ast.parse(entry.read_text(encoding='utf-8-sig')).body
            if isinstance(node, ast.Assign) and any(isinstance(item, ast.Name) and item.id == '__version__' for item in node.targets)
            and isinstance(node.value, ast.Constant)]
        require(assignments == [versions[package]], 'Actual package literal version differs')
        actual = {package + '/' + relative: item['sha256']
                  for relative, item in frozen['installed_runtime'][package]['files'].items()}
        wanted = {name: digest for name, digest in proof['source_sha256'].items()
                  if name.startswith(package + '/') and name.endswith('.py')}
        require(equal(actual, wanted), 'Installed source differs from qualified wheel proof')
    require(equal(frozen['runtime_proofs'], expected), 'Frozen qualification/wheel inventory differs')
    for path, proof in frozen['runtime_proofs'].items():
        require(Path(path).is_absolute() and Path(path).resolve().is_relative_to(qualification.parent),
                'Runtime anchor escaped qualified installation')
        checked_pin(Path(path), proof)
    return dict(versions=versions, qualification=str(qualification), runtime_proof_files=len(expected))


def frozen_inputs(project, output, frozen):
    require(file_pin(shared.__file__)['sha256'] == SHARED_EVALUATOR_SHA256,
            'Qualified shared evaluator changed')
    require(equal(frozen.get('schema_version'), 2) and equal(frozen.get('corpus_version'), 2)
            and frozen.get('status') == 'frozen' and equal(frozen.get('implementations'), list(ARMS)),
            'Unsupported or unfrozen version-two comparison')
    checked_pin(output / 'oracle.json', frozen['oracle_pin'])
    checked_pin(output / 'trusted-runtime.json', frozen['trusted_runtime_pin'])
    sources = frozen['sources']
    require(type(sources) is dict and EXECUTION_SOURCE_CLOSURE <= sources.keys(),
            'Missing transitive execution source pin')
    for relative, expected in sources.items():
        checked_pin(child(project, relative), expected)
    inventory = directory_inventory(output / 'bundles')
    require(equal(inventory['files'], frozen['bundles']), 'Bundle file inventory changed')
    require(equal(inventory['directories'], frozen['bundle_directories']), 'Bundle directory inventory changed')
    python = Path(frozen['python']['path']).resolve()
    require(python.is_relative_to(project), 'Pinned interpreter escaped project')
    checked_pin(python, frozen['python'])
    check_installed_manifest(project, frozen['installed_runtime'])
    anchors = runtime_anchors(project, frozen, read_json(output / 'trusted-runtime.json'))
    qualifications = qualification_anchors(project, frozen)
    return dict(source_files=len(sources), bundle_files=len(inventory['files']),
        bundle_directories=len(inventory['directories']),
        bundle_bytes=sum(value['bytes'] for value in inventory['files'].values()), python=str(python),
        **anchors, **qualifications)


def implementation_identity(project, frozen, trusted, record, output, descriptor):
    arm, runtime = record['implementation'], record['runtime']
    require(runtime.get('isolated') is True and runtime.get('repository_product_source_on_path') is False,
            'Worker does not establish isolated installed imports')
    require(Path(runtime['python']).resolve() == Path(frozen['python']['path']).resolve(), 'Worker interpreter changed')
    module = {'tether': 'equal_policy_v2/reference.py', 'independent': 'equal_policy_v2/independent.py',
              'hash_schema': 'equal_policy/controls.py', 'reject_all': 'equal_policy/controls.py'}[arm]
    require(Path(runtime['implementation_file']).resolve() == (project / 'experiments' / module).resolve(),
            'Versioned implementation module differs')
    loaded = runtime['loaded_product_modules']
    if arm == 'tether':
        require(set(loaded) == {'asof', 'tether'}, 'Reference worker omitted product identity')
        for name in loaded:
            require(Path(loaded[name]).resolve() == Path(trusted['runtime_paths'][name + '_file']).resolve(),
                    'Reference product import escaped pinned installation')
    else:
        require(loaded == {}, 'Independent/control imported product validator')
    argv = record['argv']
    require(type(argv) is list and len(argv) == 12 and argv[1:3] == ['-I', '-B'], 'Worker invocation differs')
    require(Path(argv[0]).resolve() == Path(frozen['python']['path']).resolve(), 'Worker invocation interpreter differs')
    require(Path(argv[3]).resolve() == (project / 'experiments/equal_policy_v2/worker.py').resolve(), 'Worker launcher differs')
    require(argv[4::2] == ['--implementation', '--root', '--descriptor', '--scratch'], 'Worker options differ')
    require(argv[5] == arm and Path(argv[7]).resolve() == child(output, descriptor['descriptor']).parent.resolve()
            and argv[9] == Path(descriptor['descriptor']).name, 'Worker input binding differs')
    require(Path(argv[11]).resolve() == (output / 'comparison' / record['cell'] / 'scratch').resolve(),
            'Worker scratch binding differs')


def footprint(project, frozen, installation):
    # Classification partitions distinct files. Shared helpers are counted once,
    # not once per importing wrapper/arm; files are not a minimal executed slice.
    report = shared.footprint(project, frozen, installation)
    infrastructure = report['groups'].get('comparison_infrastructure')
    if infrastructure:
        qualifiers = [row for row in infrastructure['files'] if row['path'].startswith('planning/')]
        if qualifiers:
            for name, rows in (
                ('qualification_orchestration', qualifiers),
                ('comparison_infrastructure', [row for row in infrastructure['files'] if row not in qualifiers]),
            ):
                report['groups'][name] = dict(file_count=len(rows), files=rows,
                    **{key: sum(row[key] for row in rows) for key in (
                        'bytes', 'physical_lines', 'nonblank_noncomment_lines', 'functions', 'classes')})
    seen = set()
    for group, summary in report['groups'].items():
        by_origin = defaultdict(list)
        for row in summary['files']:
            path = row['path']
            key = (group, path) if group.startswith('installed_') else path
            require(key not in seen, 'Footprint source counted twice')
            seen.add(key)
            origin = ('version_two_delta' if path.startswith('experiments/equal_policy_v2/') else
                      'shared_original' if path.startswith('experiments/equal_policy/') else
                      'installed_whole_package' if group.startswith('installed_') else 'retained_evidence')
            row['origin'] = origin
            by_origin[origin].append(row)
        summary['by_origin'] = {origin: dict(file_count=len(rows), bytes=sum(r['bytes'] for r in rows),
            physical_lines=sum(r['physical_lines'] for r in rows)) for origin, rows in by_origin.items()}
    report['limitations'].extend([
        'Shared-original modules and version-two wrappers are separately labeled; each distinct file is counted once.',
        'Helper modules can serve several arms. Classification is an inventory partition, not exclusive runtime or development-cost attribution.',
        'Whole installed packages include functionality outside this validation endpoint; comparing their LOC with comparator modules does not prove a minimal implementation advantage.',
    ])
    return report


def resource_row(record, cell):
    """Reconcile reported logical input volume against the frozen real files."""
    if record['disposition'] == 'returned':
        bundle = Path(record['argv'][7])
        inventory = directory_inventory(bundle)
        unique = {}
        for relative, proof in inventory['files'].items():
            path = child(bundle, relative)
            info = path.stat()
            identity = (info.st_dev, info.st_ino) if info.st_ino else ('path', str(path.resolve()))
            unique[identity] = proof['bytes']
        reported = record['metrics']['bundle_inventory']
        wanted = dict(file_count=len(inventory['files']),
            logical_file_bytes=sum(row['bytes'] for row in inventory['files'].values()),
            unique_logical_bytes=sum(unique.values()), skipped_nonregular_or_link_paths=[])
        require(all(equal(reported.get(key), value) for key, value in wanted.items()),
                'Reported logical input volume differs from frozen files')
    return shared.resource_row(record, cell)


def reconstruct(project, output, *, require_primary=True):
    project, output = Path(project).resolve(), Path(output).resolve()
    require(output.is_relative_to(project), 'Comparison must be inside project')
    frozen = read_json(output / 'FROZEN.json')
    integrity = frozen_inputs(project, output, frozen)
    trusted = read_json(output / 'trusted-runtime.json')
    installation = installed_inventory(project, trusted)
    require(Path(trusted['runtime_paths']['python']).resolve() == Path(frozen['python']['path']).resolve(),
            'Trusted and frozen interpreter anchors disagree')
    for name in ('asof', 'tether'):
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
    return dict(schema_version=1, comparison_protocol_version=2, status='reconstructed', completed_at_utc=datetime.now(timezone.utc).isoformat(),
        independent_evaluator=dict(path=str(Path(__file__).resolve()), **file_pin(__file__),
            method='Version-two independent reconstruction; reuses pinned v1 evaluator primitives and aggregates only; no runner, validator, producer or oracle-helper imports',
            shared_evaluator=dict(path=str(Path(shared.__file__).resolve()), **file_pin(shared.__file__))),
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
