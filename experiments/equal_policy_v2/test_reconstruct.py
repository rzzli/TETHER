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
from equal_policy_v2 import reconstruct as audit


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else json.dumps(value, sort_keys=True).encode('utf-8') + b'\n')


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[2] / 'data/cache/bg02-v2-reconstruction-tests'
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.output = self.project / 'fictional-run'
        self.output.mkdir()
        self.python = self.project / 'qualification/environment/Scripts/python.exe'
        write(self.python, b'Fictional executable never run')
        self.sources = {}
        for relative in audit.EXECUTION_SOURCE_CLOSURE:
            path = self.project / relative
            write(path, b'# Invented source for file-pin tests\ndef fictional():\n    return 1\n')
            self.sources[path.relative_to(self.project).as_posix()] = audit.file_pin(path)
        installed = {}
        roots = {}
        for name in ('tether_engine', 'tether'):
            root = self.project / 'qualification/environment/Lib/site-packages' / name
            write(root / '__init__.py', ("__version__ = " + repr({'tether_engine': '0.4.0', 'tether': '0.6.0'}[name]) + '\n').encode())
            roots[name] = root
            installed[name] = dict(root=str(root), files={'__init__.py': audit.file_pin(root / '__init__.py')})
        metadata = self.project / 'qualification/environment/Lib/site-packages'
        for package in ('tether_target_engine-0.4.0', 'tether_target_agents-0.6.0'):
            write(metadata / (package + '.dist-info') / 'METADATA', b'Fictional metadata only\n')
        installed['distribution_metadata'] = dict(root=str(metadata), files={
            path.relative_to(metadata).as_posix(): audit.file_pin(path) for path in metadata.glob('*.dist-info/METADATA')})
        qualification = self.project / 'qualification/QUALIFICATION.json'
        wheel_proofs, trusted_wheels = [], []
        for name in ('tether_engine', 'tether'):
            wheel = qualification.parent / 'wheels' / (name + '.whl')
            write(wheel, b'Fictional wheel bytes, never installed')
            trusted_wheels.append(dict(filename=wheel.name, **audit.file_pin(wheel)))
            wheel_proofs.append(dict(path=str(wheel), distribution={'tether_engine': 'tether-target-engine', 'tether': 'tether-target-agents'}[name],
                record_verified=True, **audit.file_pin(wheel), source_sha256={
                    name + '/' + relative: proof['sha256'] for relative, proof in installed[name]['files'].items()}))
        write(qualification, dict(status='PASS', versions={'tether-target-engine': '0.4.0',
            'tether-target-agents': '0.6.0'}, wheel_proofs=wheel_proofs))
        self.trusted = dict(schema_version=1, versions=dict(tether_engine='0.4.0', tether='0.6.0'),
            runtime_paths=dict(python=str(self.python), tether_engine_file=str(roots['tether_engine'] / '__init__.py'),
                               tether_file=str(roots['tether'] / '__init__.py')),
            core_code_sha256={name: pin['sha256'] for name, pin in installed['tether_engine']['files'].items()},
            launcher_proof=dict(core_version='0.4.0', facade_version='0.6.0',
                code={name: dict(path=name, **pin) for name, pin in installed['tether']['files'].items()}),
            qualification=dict(path=str(qualification), sha256=audit.file_pin(qualification)['sha256']),
            wheels=trusted_wheels)
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
        self.frozen = dict(schema_version=2, corpus_version=2, implementations=list(audit.ARMS),
            runtime_versions=self.trusted['versions'], runtime_proofs={str(qualification): audit.file_pin(qualification),
                **{str(qualification.parent / 'wheels' / row['filename']): {k: row[k] for k in ('sha256','bytes')} for row in trusted_wheels}},
            status='frozen', cases=schedule,
            settings=dict(repetitions=1, stdout_cap_bytes=1024 * 1024, stderr_cap_bytes=1024 * 1024),
            sources=self.sources, bundles=inventory['files'], bundle_directories=inventory['directories'],
            oracle_pin=audit.file_pin(self.output / 'oracle.json'), trusted_runtime_pin=audit.file_pin(self.output / 'trusted-runtime.json'),
            python=dict(path=str(self.python), **audit.file_pin(self.python)), installed_runtime=installed)
        for relative, (status, mandatory) in audit.QUALIFICATION_RECEIPTS.items():
            pins = []
            for name in mandatory:
                path = self.project / name
                if not path.exists():
                    write(path, b'# Invented qualification fixture\n')
                proof = audit.file_pin(path)
                self.frozen['sources'][name] = proof
                pins.append(dict(path=name, **proof))
            write(self.project / relative, dict(schema_version=1, status=status, pins=pins))
            self.frozen['sources'][relative] = audit.file_pin(self.project / relative)
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
                    os_process_memory=dict(peak_bytes=1000), bundle_inventory=dict(
                        unique_logical_bytes=(self.output / 'bundles' / row['control_id'] / 'descriptor.json').stat().st_size,
                        logical_file_bytes=(self.output / 'bundles' / row['control_id'] / 'descriptor.json').stat().st_size,
                        skipped_nonregular_or_link_paths=[], file_count=1))
                module = {'tether': 'reference.py', 'independent': 'independent.py', 'hash_schema': 'controls.py', 'reject_all': 'controls.py'}[arm]
                runtime = dict(isolated=True, repository_product_source_on_path=False, python=str(self.python),
                    implementation_file=str(self.project / 'experiments' / ('equal_policy_v2' if arm in ('tether','independent') else 'equal_policy') / module),
                    loaded_product_modules={name: self.trusted['runtime_paths'][name + '_file'] for name in ('tether_engine', 'tether')} if arm == 'tether' else {})
                worker = dict(schema_version=1, implementation=arm, result=result, metrics=metrics, runtime=runtime)
                write(cell / 'stdout.json', worker)
                write(cell / 'stderr.txt', b'')
                argv = [str(self.python), '-I', '-B', str(self.project / 'experiments/equal_policy_v2/worker.py'),
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

    def test_shared_and_delta_footprints_count_each_file_once(self):
        groups = audit.footprint(self.project, self.frozen, {})['groups']
        independent = groups['independent_validator']
        self.assertEqual(independent['file_count'], 8)
        self.assertEqual(independent['by_origin']['shared_original']['file_count'], 6)
        self.assertEqual(independent['by_origin']['version_two_delta']['file_count'], 2)
        paths = [row['path'] for group in groups.values() for row in group['files']]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(independent['bytes'], sum(row['bytes'] for row in independent['files']))
        self.assertFalse(any(Path(row['path']).name == 'independent_runtime.py'
            for row in groups['comparison_infrastructure']['files']))
        self.assertEqual(groups['qualification_orchestration']['file_count'], 1)
        self.assertFalse(any(row['path'].startswith('planning/')
            for row in groups['comparison_infrastructure']['files']))

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

    def test_evaluator_imports_only_qualified_shared_analysis(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding='utf-8'))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(name.name for name in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module)
                if node.module == 'equal_policy':
                    self.assertEqual([item.name for item in node.names], ['reconstruct'])
        self.assertFalse(any(name.split('.')[0] in ('tether_engine','tether','experiments','run_comparison','cases','materialize')
                             for name in imports))
        self.assertTrue(set(name for name in imports if name.startswith('equal_policy')) <=
                        {'equal_policy','equal_policy.reconstruct'})
        self.assertEqual(audit.file_pin(audit.shared.__file__)['sha256'], audit.SHARED_EVALUATOR_SHA256)

    def refreeze(self):
        write(self.output / 'FROZEN.json', self.frozen)
        write(self.output / 'comparison/STARTED.json', dict(freeze_pin=audit.file_pin(self.output / 'FROZEN.json')))

    def test_missing_transitive_source_pin_fails(self):
        self.frozen['sources'].pop('experiments/equal_policy/independent_runtime.py')
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'transitive'):
            self.reconstruct()

    def test_missing_qualification_anchor_fails_even_if_other_pins_match(self):
        self.frozen['runtime_proofs'].pop(self.trusted['qualification']['path'])
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'inventory differs'):
            self.reconstruct()

    def test_extra_runtime_anchor_is_not_silently_accepted(self):
        other = self.project / 'qualification/unrelated.txt'
        write(other, b'unrelated')
        self.frozen['runtime_proofs'][str(other)] = audit.file_pin(other)
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'inventory differs'):
            self.reconstruct()

    def test_changed_wheel_is_detected(self):
        write(self.project / 'qualification/wheels/tether_engine.whl', b'changed')
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_changed_qualification_is_detected(self):
        write(Path(self.trusted['qualification']['path']), dict(status='FAILED'))
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_runtime_version_label_must_match_actual_pinned_pair(self):
        self.frozen['runtime_versions'] = dict(tether='0.5.2', tether_engine='0.3.13')
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'versions differ'):
            self.reconstruct()

    def test_old_launcher_cannot_pass_corrected_run_identity(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row: row['argv'].__setitem__(3,
            str(self.project / 'experiments/equal_policy/worker.py')))
        with self.assertRaisesRegex(audit.ReconstructionError, 'launcher differs'):
            self.reconstruct()

    def test_old_full_validator_module_cannot_pass_versioned_identity(self):
        self.rewrite_cell('UNIT-A-r1-independent', lambda row: row['runtime'].__setitem__(
            'implementation_file', str(self.project / 'experiments/equal_policy/independent.py')))
        with self.assertRaisesRegex(audit.ReconstructionError, 'implementation module differs'):
            self.reconstruct()

    def test_changed_versioned_arm_grid_is_rejected(self):
        self.frozen['implementations'] = ['tether', 'independent']
        self.refreeze()
        with self.assertRaises(audit.ReconstructionError): self.reconstruct()

    def test_reported_input_volume_is_checked_against_actual_frozen_files(self):
        self.rewrite_cell('UNIT-A-r1-tether', lambda row:
            row['metrics']['bundle_inventory'].__setitem__('unique_logical_bytes', 1))
        with self.assertRaisesRegex(audit.ReconstructionError, 'input volume differs'):
            self.reconstruct()

    def test_missing_component_qualification_receipt_is_rejected(self):
        self.frozen['sources'].pop(next(iter(audit.QUALIFICATION_RECEIPTS)))
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'receipt omitted'):
            self.reconstruct()

    def test_qualification_leaf_omitted_from_freeze_is_rejected(self):
        leaf = 'planning/review-assets/tether-equal-policy-result-review-20261105/corpus-v2-green02.log'
        self.frozen['sources'].pop(leaf)
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'input omitted'):
            self.reconstruct()

    def test_consistently_rehashed_failed_component_qualification_is_rejected(self):
        relative = next(iter(audit.QUALIFICATION_RECEIPTS))
        document = audit.read_json(self.project / relative)
        document['status'] = 'FAILED'
        write(self.project / relative, document)
        self.frozen['sources'][relative] = audit.file_pin(self.project / relative)
        self.refreeze()
        with self.assertRaisesRegex(audit.ReconstructionError, 'status/schema'):
            self.reconstruct()


if __name__ == '__main__':
    unittest.main(verbosity=2)
