from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.archive import compare_result, observable


class ArchiveProjectionTests(unittest.TestCase):
    def test_expected_dictionary_is_declared_subset_not_full_feature_inventory(self):
        observed = {"decision": "accept", "observables": {"features": {"values": {
            "genetics_strength": {"value": 0.7}, "expression_support": {"value": None}}}}}
        expected = {"decision": "accept", "observables": {"feature_values": {"genetics_strength": 0.7}}}
        self.assertTrue(compare_result(observed, expected)["full_match"])

    def test_missing_is_distinct_from_explicit_null(self):
        expected = {"decision": "accept", "observables": {"feature_values": {"genetics_strength": None}}}
        observed = {"decision": "accept", "observables": {"features": {"values": {}}}}
        self.assertFalse(compare_result(observed, expected)["full_match"])
        observed["observables"]["features"]["values"]["genetics_strength"] = {"value": None}
        self.assertTrue(compare_result(observed, expected)["full_match"])

    def test_error_and_unsupported_never_match_rejection(self):
        for decision in ("error", "unsupported"):
            result = compare_result({"decision": decision, "observables": {}}, {"decision": "reject", "observables": {}})
            self.assertFalse(result["has_verdict"])
            self.assertFalse(result["full_match"])

    def test_bool_does_not_equal_numeric_value(self):
        result = compare_result({"decision": "accept", "observables": {"calls": True}},
                                {"decision": "accept", "observables": {"dispatches": 1}})
        self.assertFalse(result["full_match"])


if __name__ == "__main__":
    unittest.main()
