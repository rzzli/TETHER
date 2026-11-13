"""The required review probe exercises qualified, temporally eligible computation."""

from pathlib import Path
import tempfile
import unittest

from tether_engine.serde import sha256_file
from tools.review.probe_framework import FIXTURES, new_computation_old_inputs


class ReviewComputationProbeTests(unittest.TestCase):
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
