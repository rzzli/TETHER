"""Regression witness against frozen v1; synthetic return values only."""
import importlib.util
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("ownership_base_checks", HERE / "check_deterministic_verifier_v1.py")
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


class OpenContractChecks(unittest.TestCase):
    def test_untyped_null_never_closed(self):
        h = c.Harness(); h.files.open = lambda claim, deadline: None
        r = h.run()
        self.assertEqual(h.files.closed, [])
        self.assertFalse(r["verification_complete"])

    def test_foreign_object_never_closed(self):
        h = c.Harness(); h.files.open = lambda claim, deadline: object()
        r = h.run()
        self.assertEqual(h.files.closed, [])
        self.assertFalse(r["verification_complete"])

    def test_typed_null_never_closed(self):
        h = c.Harness(); h.files.open = lambda claim, deadline: c.v.OpenReturn(None, claim.size, claim.path)
        r = h.run()
        self.assertEqual(h.files.closed, [])
        self.assertFalse(r["verification_complete"])

    def test_late_valid_owned_return_closed_once(self):
        h = c.Harness(); h.files.open_hook = lambda handle: setattr(h.clock, "t", 296)
        r = h.run()
        self.assertEqual(len(h.files.closed), 1)
        self.assertEqual(r["status"], "INCOMPLETE_TIMEOUT")
        self.assertEqual(r["files"][0]["open_state"], "return_observed_owned")


if __name__ == "__main__":
    unittest.main(verbosity=2)
