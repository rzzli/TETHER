"""Development qualification of the adapter/materializer, not benchmark scores."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

# Only experiment modules are added. The product comes from the installed
# qualification environment under Python -I, never src/ or facade/src/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy import cases, reference, materialize
from equal_policy.policy_cases import prepare_policy_sources


class ReferenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bg02-reference-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.counter = 0

    def bundle(self, *, task='core_t1', recipe=None):
        self.counter += 1
        spec = cases._spec('UNIT-' + str(self.counter), 'Adapter unit control', [],
                           base=task, recipe=recipe or {})
        root = self.directory / ('bundle-' + str(self.counter))
        descriptor, _ = cases.write_source_bundle(root, spec)
        return root, descriptor, spec

    def test_installed_identity_is_not_checkout(self):
        identity = reference.runtime_identity()
        self.assertEqual(identity['tether_version'], '0.5.1')
        self.assertEqual(identity['asof_version'], '0.3.12')
        self.assertIn('site-packages', identity['asof_file'])
        self.assertIn('site-packages', identity['tether_file'])

    def test_prepare_never_quotes_selects_or_scores(self):
        root, descriptor, _ = self.bundle()
        with patch('asof.agents.ExtractiveBackend.quote', side_effect=AssertionError('quote forbidden')), \
             patch('asof.agents.ExtractiveBackend.select', side_effect=AssertionError('select forbidden')), \
             patch('asof.scorer.score', side_effect=AssertionError('score forbidden')):
            result = reference.validate_bundle(root, descriptor)
        self.assertEqual(result['decision'], 'accept', result)
        self.assertEqual(result['observables']['eligible_observation_ids'], ['obs-1'])
        self.assertNotIn('prediction', result['observables'])

    def test_future_program_rejects_and_zero_budget_prepares(self):
        root, descriptor, _ = self.bundle(task='core_t6')
        value = materialize.load(root / 'input/case.json')
        value['program']['availability'] = cases.availability('2025-01-01')
        materialize.save(root / 'input/case.json', value)
        self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'reject')
        root, descriptor, _ = self.bundle(recipe={'budget': {'max_calls': 0}})
        self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'accept')

    def test_unknown_implementation_failure_is_error(self):
        root, descriptor, _ = self.bundle()
        with patch('equal_policy.reference._core_prepare', side_effect=KeyError('implementation bug')):
            self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'error')

    def test_core_materialization_and_source_inclusive_verification(self):
        root, descriptor, _ = self.bundle()
        descriptor = reference.materialize_core(root, descriptor, 'valid_scored')
        descriptor['operation'] = 'verify_run'
        result = reference.validate_bundle(root, descriptor)
        self.assertEqual(result['decision'], 'accept', result)
        self.assertEqual(result['observables']['prediction']['status'], 'scored')
        self.assertEqual(result['observables']['selected_observation_ids'], ['obs-1'])

    def test_semantic_mutations_preserve_byte_receipts_but_reject(self):
        for mutation in ('omit_raw_parent_proof_reseal', 'journal_claim_differs_reseal',
                         'run_call_count_reseal', 'feature_value_reseal',
                         'prediction_contribution_reseal', 'trace_fingerprint_reseal',
                         'claim_fingerprint_reseal'):
            with self.subTest(mutation=mutation):
                root, descriptor, _ = self.bundle()
                descriptor = reference.materialize_core(root, descriptor, 'valid_scored')
                descriptor['operation'] = 'verify_run'
                materialize.mutate_core(root, descriptor, mutation)
                receipt = materialize.load(root / 'run/receipt.json')
                self.assertTrue(all(materialize.file_hash(root / 'run' / key) == value
                                    for key, value in receipt['outputs'].items()))
                self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'reject')

    def test_scripted_failure_accounting_is_verifiable(self):
        for producer in ('known_overquote', 'unknown_timeout', 'malformed_usage',
                         'unknown_selection', 'duplicate_selection'):
            with self.subTest(producer=producer):
                root, descriptor, _ = self.bundle()
                descriptor = reference.materialize_core(root, descriptor, producer)
                descriptor['operation'] = 'verify_run'
                result = reference.validate_bundle(root, descriptor)
                self.assertEqual(result['decision'], 'accept', result)
                self.assertIsNone(result['observables']['prediction']['probability'])
                self.assertEqual(result['observables']['selected_observation_ids'], [])

    def test_local_transport_is_fictional_and_retains_native_archive(self):
        for producer in ('local_valid', 'local_malformed_response', 'local_known_overquote'):
            with self.subTest(producer=producer):
                root, descriptor, _ = self.bundle(recipe={'local_config': True})
                with patch('socket.socket.connect', side_effect=AssertionError('No network authorized for fixtures')):
                    descriptor = reference.materialize_core(root, descriptor, producer)
                descriptor['operation'] = 'verify_run'
                self.assertTrue((root / 'run/backend-execution.json').is_file())
                result = reference.validate_bundle(root, descriptor)
                self.assertEqual(result['decision'], 'accept', result)
                measured = result['observables']['measured_usage']
                if producer == 'local_known_overquote':
                    self.assertEqual(measured['output_tokens'], 65)
                    self.assertEqual(result['observables']['calls'], 1)

    def test_local_archive_mutations_reject(self):
        for mutation in ('local_request_fingerprint_reseal', 'local_response_usage_reseal'):
            root, descriptor, _ = self.bundle(recipe={'local_config': True})
            descriptor = reference.materialize_core(root, descriptor, 'local_valid')
            descriptor['operation'] = 'verify_run'
            materialize.mutate_core(root, descriptor, mutation)
            self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'reject')

    def test_recovery_never_infers_completed_call(self):
        root, descriptor, _ = self.bundle()
        descriptor = reference.materialize_core(root, descriptor, 'unresolved_dispatch')
        descriptor['operation'] = 'inspect_run'
        result = reference.validate_bundle(root, descriptor)
        self.assertEqual(result['decision'], 'inspect_only')
        self.assertEqual(result['observables']['recovery']['unresolved_attempts'], ['genetics:1'])
        materialize.mutate_core(root, descriptor, 'journal_chain')
        self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'reject')

    def test_native_outer_code_and_process_proofs(self):
        for mutation in ('none', 'process_supervision_reseal', 'outer_code_proof_reseal'):
            root, descriptor, _ = self.bundle()
            descriptor = reference.materialize_outer(root, descriptor)
            descriptor['operation'] = 'verify_run'
            materialize.mutate_outer(root, descriptor, mutation)
            result = reference.validate_bundle(root, descriptor)
            self.assertEqual(result['decision'], 'accept' if mutation == 'none' else 'reject', result)

    def test_policy_preflight_retains_checked_copies_without_dispatch(self):
        root, descriptor, spec = self.bundle(task='policy_t6', recipe={'policy_recipe': 'none'})
        descriptor['variant'] = spec['variant'] = 'artifact_policy_v2'
        descriptor, pending = prepare_policy_sources(root, spec, descriptor)
        self.assertIsNone(pending)
        with patch('asof.agents.ExtractiveBackend.select', side_effect=AssertionError('No dispatch')):
            result = reference.validate_bundle(root, descriptor, scratch_dir=self.directory)
        self.assertEqual(result['decision'], 'accept', result)
        prepared = Path(result['observables']['preparation_evidence']['directory'])
        self.assertTrue((prepared / 'catalog-policy/binding.json').is_file())

    def test_variant_cannot_promote_schema1_outer_into_artifact_authorization(self):
        root, descriptor, _ = self.bundle()
        descriptor = reference.materialize_outer(root, descriptor)
        descriptor['variant'] = 'artifact_policy_v2'
        self.assertEqual(reference.validate_bundle(root, descriptor)['decision'], 'reject')

    def test_policy_outer_native_and_control_mutations(self):
        for mutation in ('valid_outer', 'copied_control_reseal', 'projection_reseal', 'dossier_reseal'):
            root, descriptor, spec = self.bundle(task='policy_t6', recipe={'policy_recipe': mutation})
            descriptor['variant'] = spec['variant'] = 'artifact_policy_v2'
            descriptor['operation'] = spec['operation'] = 'verify_run'
            descriptor, _ = prepare_policy_sources(root, spec, descriptor)
            descriptor = reference.materialize_outer(root, descriptor)
            materialize.mutate_outer(root, descriptor, mutation)
            result = reference.validate_bundle(root, descriptor)
            self.assertEqual(result['decision'], 'accept' if mutation == 'valid_outer' else 'reject', result)

    def test_materializer_failure_retains_attempt(self):
        root, descriptor, spec = self.bundle(recipe={'sealed_producer': 'undeclared'})
        # A declared producer error is retained by native workflow, but an
        # invalid preflight input cannot produce a sealed run.
        value = materialize.load(root / 'input/case.json')
        value['schema_version'] = 1
        materialize.save(root / 'input/case.json', value)
        with self.assertRaises(RuntimeError):
            materialize.prepare_sealed_case(root, spec, descriptor, python=sys.executable)
        self.assertTrue((root / 'producer-execution.json').is_file())
        self.assertNotEqual(materialize.load(root / 'producer-execution.json')['returncode'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
