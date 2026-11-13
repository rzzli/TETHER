"""Production metrics require exact cohort and producer bindings, never bare numbers."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import write_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, encode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import Budget, run_workflow


FIXTURES = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class EvaluationBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fixture = self.root / 'fixture'
        shutil.copytree(FIXTURES, self.fixture)
        base = decode(Case, read_json(self.fixture/'case.json'))
        self.cases = [replace(base, case_id='fictional-a'), replace(base, case_id='fictional-b')]
        self.model = decode(ScorerArtifact, read_json(self.fixture/'scorer.json'))
        self.cohort = dict(schema_version=1, kind='fixed_horizon_binary_cohort', cohort_id='fictional-cohort',
            label_freeze='2026-01-01', policy=dict(schema_version=1, endpoint=base.endpoint.name,
            horizon_months=base.endpoint.horizon_months, reporting_lag_days=0),
            members=[dict(case_id=case.case_id, case_fingerprint=fingerprint(case), origin=case.origin.isoformat(),
                endpoint=case.endpoint.name, horizon_months=case.endpoint.horizon_months,
                cluster_id='fictional-dependent-group') for case in self.cases])
        self.cohort_path = self.root/'cohort.json'
        write_json(self.cohort_path, self.cohort)
        self.producer = dict(schema_version=1, kind='tether_run_predictions', arm_id='fictional-arm',
            cohort_sha256=sha256_file(self.cohort_path), records=[self.make_run(case) for case in self.cases])
        self.producer_path = self.root/'producer.json'
        self.labels = dict(schema_version=1, label_freeze='2026-01-01', outcomes=[dict(case_id=case.case_id,
            origin=case.origin.isoformat(), endpoint=case.endpoint.name, horizon_months=case.endpoint.horizon_months,
            status='resolved', value=index, event_at='2024-01-01' if index else None,
            observed_until='2025-01-01', label_available_at='2025-02-01', cluster_id='fictional-dependent-group')
            for index, case in enumerate(self.cases)])
        self.labels_path = self.root/'labels.json'
        self.seal()

    def make_run(self, case, *, name=None, model=True, partial=False, durable=True):
        output = self.root/(name or case.case_id)
        store = load_snapshot(self.fixture/'snapshot.json', case)
        journal = RunJournal(output) if durable else None
        try:
            result = run_workflow(case, store, ExtractiveBackend(), self.model if model else None,
                                  budget=Budget(max_calls=1) if partial else None, journal=journal)
            receipt = write_run(output, result, store, self.model if model else None, journal)
            run_id = journal.events[0]['details']['run_id'] if journal else '00000000-0000-4000-8000-000000000000'
        finally:
            if journal:
                journal.close()
        return dict(case_id=case.case_id, state='sealed_run', run_dir=output.name,
                    run_id=run_id, receipt_sha256=receipt, prediction_sha256=sha256_file(output/'prediction.json'))

    def seal(self):
        write_json(self.producer_path, self.producer)
        write_json(self.labels_path, self.labels)
        self.labels_hash = sha256_file(self.labels_path)

    def evaluate(self, **kwargs):
        from tether_engine.evaluation_binding import evaluate_bound
        return evaluate_bound(self.cohort_path, sha256_file(self.cohort_path),
                              self.producer_path, sha256_file(self.producer_path),
                              self.labels_path, self.labels_hash,
                              allow_synthetic=kwargs.pop('allow_synthetic', True), **kwargs)

    def test_source_inclusive_production_bindings_and_all_case_accounting(self):
        result = self.evaluate()
        self.assertEqual(result['kind'], 'producer_bound_evaluation')
        self.assertEqual(result['metrics']['cohort_size'], 2)
        self.assertEqual(result['metrics']['scored_cases'], 2)
        self.assertEqual(len(result['cases']), 2)
        self.assertEqual(result['binding']['prediction_provenance'], 'source_inclusive_tether_run_receipts')
        self.assertFalse(result['binding']['independent_authentication'])
        self.assertFalse(result['binding']['prelabel_registration_verified'])
        self.assertEqual(result['binding']['scientific_validity'], 'not_established')

    def test_hand_typed_prediction_cannot_replace_a_receipt_bound_result(self):
        path = self.root/self.producer['records'][0]['run_dir']/'prediction.json'
        value = read_json(path)
        value['probability'] = 0.999
        write_json(path, value)
        self.producer['records'][0]['prediction_sha256'] = sha256_file(path)
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate()

    def test_resealed_forged_probability_still_fails_semantic_reconstruction(self):
        row = self.producer['records'][0]
        directory = self.root/row['run_dir']
        prediction = read_json(directory/'prediction.json')
        prediction['probability'] = 0.999
        write_json(directory/'prediction.json', prediction)
        receipt = read_json(directory/'receipt.json')
        receipt['outputs']['prediction.json'] = sha256_file(directory/'prediction.json')
        write_json(directory/'receipt.json', receipt)
        row.update(receipt_sha256=sha256_file(directory/'receipt.json'),
                   prediction_sha256=sha256_file(directory/'prediction.json'))
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate()

    def test_wrong_run_uuid_case_fingerprint_endpoint_or_cohort_rejected(self):
        original = deepcopy(self.producer)
        for name in ('uuid', 'case', 'cohort', 'prediction'):
            self.producer = deepcopy(original)
            if name == 'uuid':
                self.producer['records'][0]['run_id'] = '00000000-0000-4000-8000-000000000000'
            elif name == 'case':
                self.producer['records'][0]['case_id'] = self.cases[1].case_id
            elif name == 'cohort':
                self.producer['cohort_sha256'] = '0'*64
            else:
                self.producer['records'][0]['prediction_sha256'] = '0'*64
            self.seal()
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.evaluate()
        self.producer = original
        for name, value in (('case_fingerprint', '0'*64), ('endpoint', 'different_endpoint'), ('horizon_months', 12)):
            cohort = deepcopy(self.cohort)
            cohort['members'][0][name] = value
            write_json(self.cohort_path, cohort)
            self.producer['cohort_sha256'] = sha256_file(self.cohort_path)
            self.seal()
            with self.subTest(field=name), self.assertRaises(ContractError):
                self.evaluate()

    def test_missing_and_duplicate_manifest_members_are_rejected(self):
        original = deepcopy(self.producer)
        for records in (original['records'][:1], original['records'] + original['records'][:1]):
            self.producer['records'] = records
            self.seal()
            with self.assertRaises(ContractError):
                self.evaluate()

    def test_declared_missing_is_retained_without_execution_or_probability_claim(self):
        self.producer['records'][1] = dict(case_id=self.cases[1].case_id, state='declared_missing', reason='No retained attempt')
        self.seal()
        result = self.evaluate()
        self.assertEqual(result['metrics']['cohort_size'], 2)
        self.assertEqual(result['metrics']['scored_cases'], 1)
        row = result['cases'][1]
        self.assertEqual(row['provenance'], 'unverified_missing_declaration')
        self.assertIsNone(row['probability'])
        self.assertEqual(row['status'], 'abstained')
        self.producer['records'][1]['probability'] = 0.7
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate()

    def test_receipt_bound_abstention_and_incomplete_run_remain_in_denominator(self):
        self.producer['records'] = [self.make_run(self.cases[0], name='abstain', model=False),
                                    self.make_run(self.cases[1], name='partial', partial=True)]
        self.seal()
        result = self.evaluate()
        self.assertEqual(result['metrics']['cohort_size'], 2)
        self.assertEqual(result['metrics']['scored_cases'], 0)
        self.assertTrue(all(row['provenance'] == 'source_inclusive_tether_run_receipt' for row in result['cases']))

    def test_legacy_receipt_and_missing_durable_run_identity_do_not_qualify(self):
        original = deepcopy(self.producer)
        directory = self.root/self.producer['records'][0]['run_dir']
        receipt = read_json(directory/'receipt.json')
        receipt.update(software_version='0.4.0')
        receipt.pop('admission_policy')
        write_json(directory/'receipt.json', receipt)
        self.producer['records'][0]['receipt_sha256'] = sha256_file(directory/'receipt.json')
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate()
        self.producer = original
        self.producer['records'][0] = self.make_run(self.cases[0], name='nondurable', durable=False)
        self.seal()
        with self.assertRaisesRegex(ContractError, 'reservation|run identity'):
            self.evaluate()

    def test_engine_source_change_and_synthetic_default_are_rejected(self):
        with self.assertRaises(ContractError):
            self.evaluate(allow_synthetic=False)
        (self.fixture/'evidence.json').write_bytes(b'{}')
        with self.assertRaises(ContractError):
            self.evaluate()

    def test_labels_are_not_opened_when_producer_binding_is_invalid(self):
        self.producer['records'][0]['prediction_sha256'] = '0'*64
        self.seal()
        original = Path.open
        def guarded(path, *args, **kwargs):
            if path == self.labels_path:
                raise AssertionError('Labels opened before producer qualification')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded), self.assertRaises(ContractError):
            self.evaluate()

    def test_input_mutation_after_source_verification_is_rejected(self):
        import tether_engine.evaluation_binding as binding
        original = binding.verify_run
        target = self.root/self.producer['records'][0]['run_dir']/'prediction.json'
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            if Path(args[0]) == target.parent:
                target.write_bytes(target.read_bytes() + b' ')
            return result
        with patch.object(binding, 'verify_run', side_effect=mutate), self.assertRaises(ContractError):
            self.evaluate()

    def test_source_check_scope_does_not_claim_a_final_exclusive_source_lock(self):
        import tether_engine.evaluation_binding as binding
        original = binding.verify_run
        last = self.root/self.producer['records'][-1]['run_dir']
        def later_source_change(*args, **kwargs):
            result = original(*args, **kwargs)
            if Path(args[0]) == last:
                (self.fixture/'evidence.json').write_bytes(b'{}')
            return result
        with patch.object(binding, 'verify_run', side_effect=later_source_change):
            result = self.evaluate()
        self.assertEqual(result['binding']['verified_sealed_runs'], 2)
        self.assertEqual(result['binding']['source_verification_scope'], 'at_each_source_inclusive_run_check')
        self.assertEqual(result['binding']['final_reread_scope'], 'captured_evaluation_inputs_and_declared_run_artifacts')
        self.assertFalse(result['binding']['exclusive_or_transactional_source_ownership'])

    def test_outputs_only_verification_cannot_qualify_production(self):
        import tether_engine.evaluation_binding as binding
        original = binding.verify_run
        def outputs_only(output, receipt_hash, **kwargs):
            self.assertTrue(kwargs['verify_sources'])
            return original(output, receipt_hash, verify_sources=False)
        with patch.object(binding, 'verify_run', side_effect=outputs_only), self.assertRaisesRegex(ContractError, 'scope is insufficient'):
            self.evaluate()

    def test_supplied_manifest_and_label_anchors_are_enforced(self):
        from tether_engine.evaluation_binding import evaluate_bound
        paths = (self.cohort_path, self.producer_path, self.labels_path)
        hashes = [sha256_file(path) for path in paths]
        for path in paths:
            payload = path.read_bytes()
            path.write_bytes(payload + b' ')
            try:
                with self.subTest(path=path.name), self.assertRaisesRegex(ContractError, 'SHA-256 differs'):
                    evaluate_bound(paths[0], hashes[0], paths[1], hashes[1], paths[2], hashes[2], allow_synthetic=True)
            finally:
                path.write_bytes(payload)

    def test_producer_code_declaration_may_differ_from_current_unreleased_build(self):
        row = self.producer['records'][0]
        path = self.root/row['run_dir']/'receipt.json'
        receipt = read_json(path)
        receipt['code']['evaluation.py'] = '0'*64
        write_json(path, receipt)
        row['receipt_sha256'] = sha256_file(path)
        self.seal()
        result = self.evaluate()
        verified = result['cases'][0]['engine_verification']
        self.assertFalse(verified['code_matches_current'])
        self.assertEqual(verified['semantic_consistency'], 'verified')

    def test_reused_run_uuid_is_rejected_even_before_second_run_validation(self):
        self.producer['records'][1]['run_id'] = self.producer['records'][0]['run_id']
        self.seal()
        with self.assertRaisesRegex(ContractError, 'Duplicate.*run identity'):
            self.evaluate()

    def baseline(self):
        rows = [dict(case_id=member['case_id'], case_fingerprint=member['case_fingerprint'], origin=member['origin'],
            endpoint=member['endpoint'], horizon_months=member['horizon_months'], status='scored', probability=0.5,
            reason=None) for member in self.cohort['members']]
        path = self.root/'external-predictions.json'
        write_json(path, dict(schema_version=1, records=rows))
        return dict(schema_version=1, kind='external_baseline_predictions', arm_id='fictional-baseline',
            cohort_sha256=sha256_file(self.cohort_path), prediction_file=dict(path=path.name, sha256=sha256_file(path)),
            producer=dict(method_id='constant', method_version='1', synthetic=True,
                references=[dict(role=role, reference=None, sha256=None,
                    reason='Fictional fixture: reference not supplied' if role != 'model' else 'No model: untrained constant')
                    for role in ('code', 'configuration', 'model')],
                chronology=dict(training_cutoff=None, calibration_cutoff=None, generated_at=None,
                                unknown_reason='Fictional untrained constant baseline; time not authenticated')))

    def test_external_baseline_is_separately_declared_without_fictitious_runs(self):
        self.producer = self.baseline()
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate()
        result = self.evaluate(expected_producer_kind='external_baseline_predictions')
        self.assertEqual(result['metrics']['scored_cases'], 2)
        self.assertEqual(result['binding']['prediction_provenance'], 'external_producer_declaration')
        self.assertFalse(result['binding']['independent_authentication'])
        self.assertTrue(all(row['provenance'] == 'external_producer_declaration' for row in result['cases']))
        completeness = result['binding']['producer_declaration']['completeness']
        self.assertTrue(completeness['all_required_roles_documented'])
        self.assertFalse(completeness['reference_bytes_verified'])
        self.assertEqual(completeness['references_with_declared_hash'], 0)

    def test_external_roles_and_unknown_explanations_cannot_disappear(self):
        original = self.baseline()
        for kind in ('missing_role', 'duplicate_role', 'missing_reason'):
            self.producer = deepcopy(original)
            references = self.producer['producer']['references']
            if kind == 'missing_role':
                references.pop()
            elif kind == 'duplicate_role':
                references[1]['role'] = references[0]['role']
            else:
                references[0]['reason'] = None
            self.seal()
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                self.evaluate(expected_producer_kind='external_baseline_predictions')

    def test_external_chronology_is_declared_and_contradictions_are_rejected(self):
        self.producer = self.baseline()
        chronology = self.producer['producer']['chronology']
        chronology.update(training_cutoff='2025-01-01', calibration_cutoff='2025-02-01',
                          generated_at='2025-03-01T00:00:00Z', unknown_reason=None)
        self.seal()
        result = self.evaluate(expected_producer_kind='external_baseline_predictions')
        qualification = result['binding']['producer_declaration']['chronology_qualification']
        self.assertEqual(qualification['status'], 'declared_only_not_historically_qualified')
        self.assertEqual(qualification['training_reaches_origin'], [case.case_id for case in self.cases])
        for field in ('training_cutoff', 'calibration_cutoff'):
            previous = chronology[field]
            chronology[field] = '2025-04-01'
            self.seal()
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, 'after.*generation'):
                self.evaluate(expected_producer_kind='external_baseline_predictions')
            chronology[field] = previous

    def test_external_same_day_cutoffs_are_not_presented_as_pre_origin(self):
        self.producer = self.baseline()
        self.producer['producer']['chronology'].update(training_cutoff=self.cases[0].origin.isoformat(),
            calibration_cutoff=self.cases[0].origin.isoformat(), generated_at='2025-03-01T00:00:00Z', unknown_reason=None)
        self.seal()
        result = self.evaluate(expected_producer_kind='external_baseline_predictions')
        qualification = result['binding']['producer_declaration']['chronology_qualification']
        expected = [case.case_id for case in self.cases]
        self.assertEqual(qualification['training_reaches_origin'], expected)
        self.assertEqual(qualification['calibration_reaches_origin'], expected)
        self.assertEqual(qualification['status'], 'declared_only_not_historically_qualified')

    def test_baseline_requires_exact_file_and_full_case_identity(self):
        self.producer = self.baseline()
        self.seal()
        path = self.root/self.producer['prediction_file']['path']
        value = read_json(path)
        value['records'][0]['case_fingerprint'] = '0'*64
        write_json(path, value)
        with self.assertRaises(ContractError):
            self.evaluate(expected_producer_kind='external_baseline_predictions')
        self.producer['prediction_file']['sha256'] = sha256_file(path)
        self.seal()
        with self.assertRaises(ContractError):
            self.evaluate(expected_producer_kind='external_baseline_predictions')

    def test_unknown_fields_and_invalid_types_cannot_claim_binding(self):
        for extra in ({'independently_verified': True}, {'schema_version': True}, {'arm_id': ''}):
            original = deepcopy(self.producer)
            self.producer.update(extra)
            self.seal()
            with self.subTest(extra=extra), self.assertRaises(ContractError):
                self.evaluate()
            self.producer = original

    def test_changed_label_freeze_or_clusters_are_rejected(self):
        for field, value in (('label_freeze', '2026-01-02'), ('cluster_id', 'different-cluster')):
            original = deepcopy(self.labels)
            if field == 'label_freeze':
                self.labels[field] = value
            else:
                self.labels['outcomes'][0][field] = value
            self.seal()
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.evaluate()
            self.labels = original
