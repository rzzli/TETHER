"""Independent reconstruction tests with invented files, never scored corpus."""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy import reconstruct as audit


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else json.dumps(value, sort_keys=True).encode('utf-8') + b'\n')


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[2] / 'data/cache/bg02-reconstruction-tests'
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.output = self.project / 'fictional-run'
        self.output.mkdir()
        self.python = self.project / 'qualification/python.exe'
        write(self.python, b'Fictional executable never run')
        self.sources = {}
        for name in ('worker.py', 'reference.py', 'independent.py', 'controls.py'):
            path = self.project / 'experiments/equal_policy' / name
            write(path, b'# Invented source for file-pin tests\ndef fictional():\n    return 1\n')
            self.sources[path.relative_to(self.project).as_posix()] = audit.file_pin(path)
        installed = {}
        roots = {}
        for name in ('tether_engine', 'tether'):
            root = self.project / 'qualification/site-packages' / name
            write(root / '__init__.py', b'# Fictional package, never imported\n')
            roots[name] = root
            installed[name] = dict(root=str(root), files={'__init__.py': audit.file_pin(root / '__init__.py')})
        metadata = self.project / 'qualification/site-packages'
        for package in ('tether_target_engine-0.4.0', 'tether_target_agents-0.6.0'):
            write(metadata / (package + '.dist-info') / 'METADATA', b'Fictional metadata only\n')
        installed['distribution_metadata'] = dict(root=str(metadata), files={
            path.relative_to(metadata).as_posix(): audit.file_pin(path) for path in metadata.glob('*.dist-info/METADATA')})
        qualification = self.project / 'qualification/QUALIFICATION.json'
        write(qualification, dict(fictional=True))
        wheel = self.project / 'qualification/wheels/fictional.whl'
        write(wheel, b'Fictional wheel bytes, never installed')
        self.trusted = dict(schema_version=1, versions=dict(tether_engine='0.4.0', tether='0.6.0'),
            runtime_paths=dict(python=str(self.python), tether_engine_file=str(roots['tether_engine'] / '__init__.py'),
                               tether_file=str(roots['tether'] / '__init__.py')),
            core_code_sha256={name: pin['sha256'] for name, pin in installed['tether_engine']['files'].items()},
            launcher_proof=dict(core_version='0.4.0', facade_version='0.6.0',
                code={name: dict(path=name, **pin) for name, pin in installed['tether']['files'].items()}),
            qualification=dict(path=str(qualification), sha256=audit.file_pin(qualification)['sha256']),
            wheels=[dict(filename=wheel.name, **audit.file_pin(wheel))])
        write(self.output / 'trusted-runtime.json', self.trusted)
        self.oracle = [
            dict(control_id='UNIT-A', decision='accept', operation='prepare_run', variant='core_v2_catalog1',
                 observables=dict(scorer_preflight=None), obligation_ids=['EP-WIRE-01', 'EP-SCORER-01'], construction_stratum='new_synthetic_construction'),
            dict(control_id='UNIT-B', decision='reject', operation='prepare_run', variant='core_v2_catalog1',
                 observables={}, obligation_ids=['EP-WIRE-01'], construction_stratum='exposed_regression'),
            dict(control_id='UNIT-I', decision='inspect_only', operation='inspect_run', variant='core_v2_catalog1',
                 observables=dict(unresolved_attempts=['genetics:1'], recovery_may_dispatch=False),
                 obligation_ids=['EP-FAIL-01'], construction_stratum='new_synthetic_construction'),
        ]
        write(self.output / 'oracle.json', dict(schema_version=1, cases=self.oracle))
        schedule = []
        for row in self.oracle:
            relative = 'bundles/' + row['control_id'] + '/descriptor.json'
            descriptor = dict(schema_version=1, control_id=row['control_id'], operation=row['operation'],
                              variant=row['variant'], paths={}, options={}, anchors={})
            write(self.output / relative, descriptor)
            schedule.append(dict(control_id=row['control_id'], operation=row['operation'], variant=row['variant'], descriptor=relative))
        (self.output / 'bundles/UNIT-A/empty-directory-input').mkdir()
        inventory = audit.directory_inventory(self.output / 'bundles')
        self.frozen = dict(schema_version=1, status='frozen', cases=schedule,
            settings=dict(repetitions=1, stdout_cap_bytes=1024 * 1024, stderr_cap_bytes=1024 * 1024),
            sources=self.sources, bundles=inventory['files'], bundle_directories=inventory['directories'],
            oracle_pin=audit.file_pin(self.output / 'oracle.json'), trusted_runtime_pin=audit.file_pin(self.output / 'trusted-runtime.json'),
            python=dict(path=str(self.python), **audit.file_pin(self.python)), installed_runtime=installed)
        write(self.output / 'FROZEN.json', self.frozen)
        comparison = self.output / 'comparison'
        write(comparison / 'STARTED.json', dict(freeze_pin=audit.file_pin(self.output / 'FROZEN.json')))
        self.records = []
        for index, row in enumerate(self.oracle):
            arms = list(audit.ARMS[index:]) + list(audit.ARMS[:index])
            for arm in arms:
                cell_name = row['control_id'] + '-r1-' + arm
                cell = comparison / cell_name
                (cell / 'scratch').mkdir(parents=True)
                observed = dict(scorer_preflight=None) if row['decision'] == 'accept' else dict(recovery=dict(
                    unresolved_attempts=['genetics:1'], recovery_action='inspect only; never automatically repeat unresolved calls')) if row['decision'] == 'inspect_only' else {}
                decision = 'reject' if arm == 'reject_all' else 'accept' if arm == 'hash_schema' else row['decision']
                result = dict(schema_version=1, control_id=row['control_id'], decision=decision, stage=row['operation'],
                              violated_obligations=[], checked_scope=[row['operation']], observables=observed)
                metrics = dict(import_wall_seconds=0.1, operation_wall_seconds=0.2,
                    import_cpu_seconds=0.05, operation_cpu_seconds=0.1, import_traced_peak_bytes=500,
                    operation_traced_peak_bytes=900, operation_traced_peak_above_start_bytes=300,
                    os_process_memory=dict(peak_bytes=1000), bundle_inventory=dict(unique_logical_bytes=42, file_count=1))
                module = {'tether': 'reference.py', 'independent': 'independent.py', 'hash_schema': 'controls.py', 'reject_all': 'controls.py'}[arm]
                runtime = dict(isolated=True, repository_product_source_on_path=False, python=str(self.python),
                    implementation_file=str(self.project / 'experiments/equal_policy' / module),
                    loaded_product_modules={name: self.trusted['runtime_paths'][name + '_file'] for name in ('tether_engine', 'tether')} if arm == 'tether' else {})
                worker = dict(schema_version=1, implementation=arm, result=result, metrics=metrics, runtime=runtime)
                write(cell / 'stdout.json', worker)
                write(cell / 'stderr.txt', b'')
                argv = [str(self.python), '-I', '-B', str(self.project / 'experiments/equal_policy/worker.py'),
                        '--implementation', arm, '--root', str(self.output / 'bundles' / row['control_id']),
                        '--descriptor', 'descriptor.json', '--scratch', str(cell / 'scratch')]
                record = dict(schema_version=1, control_id=row['control_id'], repetition=1, implementation=arm,
                    disposition='returned', exit_code=0, result=result, metrics=metrics, runtime=runtime,
                    stdout_pin=audit.file_pin(cell / 'stdout.json'), stderr_pin=audit.file_pin(cell / 'stderr.txt'),
                    argv=argv, launcher_wall_seconds=0.4)
                write(cell / 'RESULT.json', record)
                self.records.append(dict(cell=cell_name, **audit.file_pin(cell / 'RESULT.json')))
        self.execution = dict(schema_version=1, status='executed', expected_cells=12, terminal_cells=12, records=self.records)
        write(comparison / 'EXECUTION.json', self.execution)

    def reconstruct(self):
        return audit.reconstruct(self.project, self.output, require_primary=False)

    def rewrite_cell(self, name, callback, *, worker_too=True):
        cell = self.output / 'comparison' / name
        record = audit.read_json(cell / 'RESULT.json')
        callback(record)
        if worker_too:
            write(cell / 'stdout.json', {key: record[key] for key in ('schema_version', 'implementation', 'result', 'metrics', 'runtime')})
            record['stdout_pin'] = audit.file_pin(cell / 'stdout.json')
        write(cell / 'RESULT.json', record)
        next(row for row in self.records if row['cell'] == name).update(audit.file_pin(cell / 'RESULT.json'))
        write(self.output / 'comparison/EXECUTION.json', self.execution)

    def test_complete_grid_decisions_and_resource_boundaries(self):
        result = self.reconstruct()
        self.assertEqual((result['unique_cases'], result['terminal_cells']), (3, 12))
        self.assertEqual(result['totals']['tether']['fully_conformant'], 3)
        self.assertEqual(result['totals']['reject_all']['false_rejection'], 1)
        self.assertEqual(result['totals']['hash_schema']['false_admission'], 1)
        self.assertAlmostEqual(result['resource_summaries']['tether']['python_total_wall_seconds']['median'], 0.3)
        self.assertEqual(result['resource_summaries']['tether']['retained_scratch_bytes']['median'], 0)
        self.assertEqual(result['rates']['reject_all']['false_rejection']['denominator'], 1)

    def test_independent_runtime_counts_as_validator_not_infrastructure(self):
        for name in ('independent_runtime.py', 'runtime_witnesses.py', 'test_independent_runtime.py'):
            path = self.project / 'experiments/equal_policy' / name
            write(path, b'# Invented footprint-only source\ndef check():\n    return True\n')
            self.frozen['sources'][path.relative_to(self.project).as_posix()] = audit.file_pin(path)
        groups = audit.footprint(self.project, self.frozen, {})['groups']
        independent = groups['independent_validator']
        self.assertEqual(independent['file_count'], 2)
        self.assertEqual({Path(row['path']).name for row in independent['files']},
                         {'independent.py', 'independent_runtime.py'})
        self.assertNotIn('independent_runtime.py',
                         {Path(row['path']).name for row in groups['comparison_infrastructure']['files']})
        self.assertEqual(groups['runtime_only_witnesses']['file_count'], 1)
        self.assertEqual(groups['frozen_experiment_tests']['file_count'], 1)
        self.assertEqual(independent['bytes'], sum(row['bytes'] for row in independent['files']))

    def test_duplicate_cell_cannot_replace_missing_cell(self):
        self.execution['records'][1] = copy.deepcopy(self.execution['records'][0])
        write(self.output / 'comparison/EXECUTION.json', self.execution)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_short_inventory_cannot_claim_complete_counts(self):
        self.execution['records'].pop()
        write(self.output / 'comparison/EXECUTION.json', self.execution)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_unlisted_attempt_directory_is_not_ignored(self):
        (self.output / 'comparison/hidden-retry').mkdir()
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_empty_directory_is_detected(self):
        (self.output / 'bundles/UNIT-A/empty-directory-input').rmdir()
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_installed_code_is_detected(self):
        write(Path(self.trusted['runtime_paths']['tether_engine_file']), b'# modified\n')
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_installed_metadata_is_detected(self):
        root = Path(self.frozen['installed_runtime']['distribution_metadata']['root'])
        write(next(root.glob('*.dist-info/METADATA')), b'changed')
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_oracle_and_changed_source_are_detected(self):
        write(self.output / 'oracle.json', dict(cases=[]))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_execution_source_is_detected(self):
        write(self.project / 'experiments/equal_policy/worker.py', b'# changed\n')
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_added_empty_directory_is_detected(self):
        (self.output / 'bundles/UNIT-A/unlisted-empty-directory').mkdir()
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_boolean_terminal_schema_is_rejected(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row: row.update(schema_version=True))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_duplicate_json_field_and_nonfinite_metadata_are_rejected(self):
        path = self.project / 'malformed.json'
        for contents in (b'{"field": 1, "field": 2}', b'{"field": NaN}'):
            with self.subTest(contents=contents):
                write(path, contents)
                with self.assertRaises(audit.ReconstructionError): audit.read_json(path)

    def test_valid_cells_in_wrong_order_are_rejected(self):
        self.execution['records'][:2] = reversed(self.execution['records'][:2])
        write(self.output / 'comparison/EXECUTION.json', self.execution)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_trusted_and_frozen_interpreter_disagreement_is_rejected(self):
        self.trusted['runtime_paths']['python'] = str(self.project / 'other-python.exe')
        write(self.output / 'trusted-runtime.json', self.trusted)
        self.frozen['trusted_runtime_pin'] = audit.file_pin(self.output / 'trusted-runtime.json')
        write(self.output / 'FROZEN.json', self.frozen)
        write(self.output / 'comparison/STARTED.json', dict(freeze_pin=audit.file_pin(self.output / 'FROZEN.json')))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_stream_pin_and_result_projection_are_both_checked(self):
        name = 'UNIT-A-r1-tether'
        self.rewrite_cell(name, lambda row: row['result'].update(decision='reject'), worker_too=False)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_errors_and_unsupported_are_never_correct_rejections(self):
        self.rewrite_cell('UNIT-B-r1-tether', lambda row: row['result'].update(decision='error'))
        self.rewrite_cell('UNIT-B-r1-independent', lambda row: row['result'].update(decision='unsupported'))
        result = self.reconstruct()
        self.assertEqual(result['totals']['tether']['decision_correct'], 2)
        self.assertEqual(result['totals']['independent']['decision_unsupported'], 1)
        self.assertEqual(result['totals']['tether'].get('false_rejection', 0), 0)

    def test_failed_invocation_cannot_claim_policy_rejection(self):
        self.rewrite_cell('UNIT-B-r1-tether', lambda row: row.update(disposition='crash', exit_code=2), worker_too=False)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_missing_null_observable_remains_missing(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row: row['result'].update(observables={}))
        result = self.reconstruct()
        item = next(row for row in result['rows'] if row['cell'] == 'UNIT-A-r1-tether')
        self.assertFalse(item['fully_conformant'])
        self.assertEqual(set(item['observable_mismatches']), {'scorer_preflight'})
        self.assertIsNone(audit.observable({'scorer_preflight': None}, 'scorer_preflight', None))

    def test_invalid_inspection_is_separately_counted(self):
        self.rewrite_cell('UNIT-B-r1-tether', lambda row: row['result'].update(decision='inspect_only'))
        result = self.reconstruct()
        self.assertEqual(result['totals']['tether']['invalid_inspection_acceptance'], 1)
        self.assertEqual(result['totals']['tether'].get('false_admission', 0), 0)

    def test_missing_resource_measurement_is_not_zero(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row: row['metrics'].update(operation_wall_seconds=None))
        result = self.reconstruct()
        values = result['resource_summaries']['tether']['python_total_wall_seconds']
        self.assertEqual((values['observations'], values['unavailable']), (2, 1))
        with self.assertRaises(audit.ReconstructionError): audit.statistics_for([True])
        with self.assertRaises(audit.ReconstructionError): audit.statistics_for([-0.1])

    def test_product_import_in_independent_worker_invalidates_comparison(self):
        self.rewrite_cell('UNIT-A-r1-independent', lambda row: row['runtime'].update(loaded_product_modules={'tether_engine': 'wrong'}))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_worker_invocation_input_binding_is_checked(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row: row['argv'].__setitem__(9, 'other.json'))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_resource_copy_volume_is_actual_retained_scratch(self):
        path = self.output / 'comparison/UNIT-A-r1-tether/scratch/copied.json'
        write(path, b'12345')
        result = self.reconstruct()
        row = next(row for row in result['resource_rows'] if row['cell'] == 'UNIT-A-r1-tether')
        self.assertEqual((row['retained_scratch_bytes'], row['retained_scratch_files']), (5, 1))

    def test_native_observable_types_and_unknown_fields(self):
        expected = {'support': 1}
        actual = {'features': {'values': {'support': {'value': 1.0}}}}
        self.assertFalse(audit.equal(audit.observable(actual, 'feature_values', expected), expected))
        with self.assertRaises(audit.ReconstructionError): audit.observable({}, 'unknown_feature', None)

    def test_primary_analysis_is_compared_without_importing_its_evaluator(self):
        result = self.reconstruct()
        primary = dict(cells=result['terminal_cells'], rows=result['rows'], totals=result['totals'])
        write(self.output / 'ANALYSIS.json', primary)
        result = audit.reconstruct(self.project, self.output)
        self.assertEqual(result['primary_analysis_concordance']['status'], 'agrees')
        primary['totals']['tether']['fully_conformant'] += 1
        write(self.output / 'ANALYSIS.json', primary)
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_evaluator_has_no_product_runner_or_producer_imports(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding='utf-8'))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): roots.update(name.name.split('.')[0] for name in node.names)
            if isinstance(node, ast.ImportFrom): roots.add((node.module or '').split('.')[0])
        self.assertFalse(roots & {'tether_engine', 'tether', 'experiments', 'equal_policy', 'run_comparison', 'cases', 'materialize'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
