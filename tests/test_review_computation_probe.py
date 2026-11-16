"""The required review probe exercises qualified, temporally eligible computation."""

from pathlib import Path
from contextlib import ExitStack, redirect_stdout
import io
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import read_json, sha256_file
from tools.review import probe_framework
from tools.review.probe_framework import FIXTURES, new_computation_old_inputs


class ReviewComputationProbeTests(unittest.TestCase):
    def run_profile(self, profile=None, failed=False):
        current = ('t6_future_program', 'immutable_evidence', 'hypothesis_binding',
                   'provider_failures', 'scorer_preflight', 'semantic_output_binding',
                   'archived_catalog_policy', 'missingness_feature_contract', 'new_computation_old_inputs')
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            for name in current:
                stack.enter_context(patch.object(probe_framework, name, return_value={
                    'passed': not (failed and name == 't6_future_program')}))
            legacy = stack.enter_context(patch.object(probe_framework, 'legacy_verification',
                                                      return_value={'passed': True}))
            history = stack.enter_context(patch.object(probe_framework, 'materialize_checkpoint',
                                                       side_effect=AssertionError('unexpected history access')))
            output = Path(temporary)/'probes.json'
            arguments = ['--output', str(output)] + ([] if profile is None else ['--profile', profile])
            with redirect_stdout(io.StringIO()):
                code = probe_framework.main(arguments)
            return code, read_json(output), legacy.call_count, history.call_count

    def test_maintained_probes_do_not_require_or_claim_historical_verification(self):
        code, report, legacy_calls, history_calls = self.run_profile('maintained')
        self.assertEqual((code, legacy_calls, history_calls), (0, 0, 0))
        self.assertEqual(len(report['probes']), 9)
        self.assertNotIn('legacy_verification', report['probes'])
        historical = report['historical_checks']['legacy_verification']
        self.assertEqual(historical['status'], 'not_executed_requires_pinned_history')
        self.assertNotIn('passed', historical)

    def test_default_still_requires_the_legacy_probe(self):
        code, report, legacy_calls, _ = self.run_profile()
        self.assertEqual((code, legacy_calls), (0, 1))
        self.assertEqual(len(report['probes']), 10)
        self.assertEqual(report['historical_checks'], {})

    def test_failed_current_probe_fails_either_profile(self):
        for profile in ('maintained', 'all-current'):
            code, report, _, _ = self.run_profile(profile, failed=True)
            self.assertEqual(code, 1)
            self.assertEqual(report['probes']['F01_t6_future_program']['status'], 'failed')

    def test_qualified_projection_and_future_parent_control_preserve_originals(self):
        originals = {path.name: sha256_file(path) for path in FIXTURES.iterdir() if path.is_file()}
        with tempfile.TemporaryDirectory() as temporary:
            result = new_computation_old_inputs(Path(temporary))
        self.assertTrue(result["passed"], result)
        observed = result["observed"]
        self.assertEqual(observed["feature_value"], 0.8)
        self.assertEqual(observed["derivation_verification"], "verified")
        self.assertGreater(observed["computed_at"], observed["origin_at"])
        self.assertTrue(observed["future_parent_excluded"])
        self.assertEqual(observed["future_parent_calls"], 0)
        self.assertEqual(
            {path.name: sha256_file(path) for path in FIXTURES.iterdir() if path.is_file()}, originals
        )


if __name__ == "__main__":
    unittest.main()
