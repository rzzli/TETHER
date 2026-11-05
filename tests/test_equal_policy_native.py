"""Unscored native-file integration under the qualified installed interpreter.

Only experiment code is added to the path. Product imports occur solely in the
native fixture producer/reference adapter; independent modules import no product.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
QUALIFIED = REPOSITORY / 'data/cache/tether-051-installed-qualification-attempt02'
sys.path.insert(0, str(REPOSITORY / 'experiments'))
from equal_policy import cases, independent, materialize, policy_cases, reference


class NativeIndependentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        identity = reference.runtime_identity()
        if not sys.flags.isolated or not all('site-packages' in identity[k] for k in ('asof_file', 'tether_file')):
            raise RuntimeError('Run this suite with the pinned installed interpreter and -I')
        if Path(identity['python']).resolve() != (QUALIFIED / 'environment/Scripts/python.exe').resolve():
            raise RuntimeError('Wrong qualification environment')
        cls.trusted = reference.trusted_runtime(QUALIFIED)

    def setUp(self):
        cache = REPOSITORY / 'data/cache/equal-policy-native-unit'
        cache.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.counter = 0

    def fixture(self, policy=False, task='core_t1'):
        self.counter += 1
        root = self.directory / ('UNIT-' + str(self.counter))
        spec = dict(control_id='UNIT-NATIVE-' + str(self.counter), operation='prepare_run',
            variant='artifact_policy_v2' if policy else 'core_v2_catalog1',
            preparation=dict(base='policy_t6' if policy else task, changes=[], after_seal=[],
                recipe=dict(policy_recipe='none', omit_scorer=True) if policy else {}))
        descriptor, _ = cases.write_source_bundle(root, spec, trusted_runtime='trusted-runtime.json')
        materialize.save(root / 'trusted-runtime.json', self.trusted)
        if policy: descriptor, _ = policy_cases.prepare_policy_sources(root, spec, descriptor)
        return root, descriptor

    def assertAccepted(self, root, descriptor):
        result = independent.validate_bundle(root, descriptor)
        self.assertEqual(result['decision'], 'accept', result)
        return result

    def test_native_core_scored_and_recorded_are_source_verified(self):
        for producer in ('valid_scored', 'valid_recorded'):
            with self.subTest(producer=producer):
                root, descriptor = self.fixture()
                descriptor = reference.materialize_core(root, descriptor, producer)
                result = self.assertAccepted(root, descriptor)
                self.assertTrue(result['observables']['code_matches_current'])
                self.assertEqual(result['observables']['prediction']['status'], 'scored')
                self.assertEqual(result['observables']['selected_observation_ids'], ['obs-1'])

    def test_policy_preflight_copies_native_inputs_without_dispatch(self):
        root, descriptor = self.fixture(policy=True)
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        scratch = self.directory / 'independent-scratch'; scratch.mkdir()
        with patch('asof.agents.ExtractiveBackend.quote', side_effect=AssertionError('No quote')), \
             patch('asof.agents.ExtractiveBackend.select', side_effect=AssertionError('No dispatch')):
            independent_result = independent.validate_bundle(root, descriptor, scratch_dir=scratch)
            reference_result = reference.validate_bundle(root, descriptor, scratch_dir=self.directory)
        self.assertEqual(independent_result['decision'], 'accept', independent_result)
        self.assertEqual(reference_result['decision'], 'accept', reference_result)
        for key in ('admitted_observation_ids', 'eligible_observation_ids', 'exclusions', 'scorer_preflight'):
            self.assertEqual(independent_result['observables'][key], reference_result['observables'][key])
        self.assertTrue((scratch / 'independent-policy/retention.json').is_file())
        self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_native_schema1_and_schema2_outer_verify_complete_bindings(self):
        for is_policy in (False, True):
            with self.subTest(policy=is_policy):
                root, descriptor = self.fixture(policy=is_policy)
                descriptor = reference.materialize_outer(root, descriptor)
                result = self.assertAccepted(root, descriptor)
                self.assertEqual(result['observables']['semantic_consistency'], 'verified')
                self.assertTrue(result['observables']['code_matches_current'])
                self.assertTrue(result['observables']['verification']['external_anchor_checked'])
                if is_policy:
                    self.assertEqual(result['observables']['verification']['artifact_policy']['status'], 'artifact_policy_consistency_verified')
                mismatch = copy.deepcopy(descriptor)
                mismatch['variant'] = 'core_v2_catalog1' if is_policy else 'artifact_policy_v2'
                self.assertEqual(independent.validate_bundle(root, mismatch)['decision'], 'reject')

    def test_resealed_native_control_projection_and_dossier_mutations_reject(self):
        for mutation in ('copied_control_reseal', 'projection_reseal', 'dossier_reseal'):
            with self.subTest(mutation=mutation):
                root, descriptor = self.fixture(policy=True)
                descriptor = reference.materialize_outer(root, descriptor)
                self.assertAccepted(root, descriptor)
                materialize.mutate_outer(root, descriptor, mutation)
                result = independent.validate_bundle(root, descriptor)
                self.assertEqual(result['decision'], 'reject', result)

    def test_native_unresolved_dispatch_is_inspection_only(self):
        root, descriptor = self.fixture()
        descriptor = reference.materialize_core(root, descriptor, 'unresolved_dispatch')
        result = independent.validate_bundle(root, descriptor)
        self.assertEqual(result['decision'], 'inspect_only', result)
        self.assertEqual(result['observables']['recovery']['unresolved_attempts'], ['genetics:1'])
        self.assertFalse((root / 'run/receipt.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
