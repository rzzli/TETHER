"""Artificial correctness controls for the bounded P02 feasibility prototype.

These fixtures test projection and scoring mechanics. They are not biomedical
cases, source references, generated answers, or additions to study denominators.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("prototype.py")
SPEC = importlib.util.spec_from_file_location("preprint_p02_prototype", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Cannot load prototype module at {MODULE_PATH}")
prototype = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prototype)


class PrototypeCorrectnessTests(unittest.TestCase):
    def setUp(self):
        # Deliberately fictional values; no retained answer or reference is read.
        self.record = {
            "id": "control-record-A",
            "targetId": "CONTROL_TARGET_A",
            "diseaseId": "CONTROL_DISEASE_A",
            "datasourceId": "control-provider",
            "datatypeId": "control-type",
            "literature": ["control-article-A"],
            "pmcIds": ["control-repository-A"],
            "publicationDate": "2001-02-03",
            "publicationYear": 2001,
            "evidenceDate": "2001-02-03",
        }
        self.locator = {
            "source_id": "control-source-A",
            "row_group": 0,
            "row": 11,
        }
        self.slots = prototype.make_slots(self.record, self.locator)
        self.answers = [
            {
                "slot_id": slot["slot_id"],
                "value": copy.deepcopy(slot["value"]),
                "unit": slot["unit"],
                "source": copy.deepcopy(slot["source"]),
            }
            for slot in self.slots
            if slot["value"] is not None
        ]

    def answer_index(self, family, value_type=None):
        eligible_ids = {
            slot["slot_id"]
            for slot in self.slots
            if slot["family"] == family
            and slot["value"] is not None
            and (value_type is None or type(slot["value"]) is value_type)
        }
        return next(
            index
            for index, answer in enumerate(self.answers)
            if answer["slot_id"] in eligible_ids
        )

    def test_slot_families_preserve_all_unknown_scientific_fields(self):
        self.assertEqual(len(self.slots), 44)
        self.assertEqual(len({slot["slot_id"] for slot in self.slots}), 44)
        counts = {
            family: sum(slot["family"] == family for slot in self.slots)
            for family in ("identity", "context", "scientific")
        }
        self.assertEqual(counts, {"identity": 7, "context": 3, "scientific": 34})
        for slot in self.slots:
            self.assertIsNone(slot["unit"])
            for field in ("source_id", "row_group", "row"):
                self.assertEqual(slot["source"][field], self.locator[field])
            self.assertTrue(slot["source"]["field"])
            if slot["family"] == "scientific":
                self.assertIsNone(slot["value"])
                self.assertTrue(slot["unknown_reason"])

    def test_exact_projection_scores_known_families_without_zero_over_zero_pass(self):
        result = prototype.score_slots(self.slots, self.answers)
        self.assertEqual(result["critical_errors"], [])
        for family, count in (("identity", 7), ("context", 3)):
            with self.subTest(family=family):
                score = result["family_scores"][family]
                self.assertEqual(score["answerable"], count)
                self.assertEqual(score["matched"], count)
                self.assertEqual(score["coverage"], 1.0)
        scientific = result["family_scores"]["scientific"]
        self.assertEqual(scientific["answerable"], 0)
        self.assertEqual(scientific["matched"], 0)
        self.assertIsNone(scientific["coverage"])

    def test_omitted_fact_lowers_coverage_without_becoming_a_matched_unknown(self):
        answers = copy.deepcopy(self.answers)
        del answers[self.answer_index("context")]
        result = prototype.score_slots(self.slots, answers)
        context = result["family_scores"]["context"]
        self.assertEqual(context["answerable"], 3)
        self.assertEqual(context["matched"], 2)
        self.assertAlmostEqual(context["coverage"], 2 / 3)
        self.assertEqual(result["critical_errors"], [])

    def test_wrong_numeric_value_is_critical_and_not_credited(self):
        answers = copy.deepcopy(self.answers)
        numeric_index = self.answer_index("context", int)
        answers[numeric_index]["value"] += 1
        result = prototype.score_slots(self.slots, answers)
        self.assertTrue(result["critical_errors"])
        self.assertEqual(result["family_scores"]["context"]["matched"], 2)

    def test_json_boolean_does_not_equal_integer_and_list_does_not_equal_string(self):
        for value_type, replacement in ((int, True), (list, "control-article-A")):
            with self.subTest(value_type=value_type.__name__):
                family = "context" if value_type is int else "identity"
                slots = copy.deepcopy(self.slots)
                answers = copy.deepcopy(self.answers)
                answer = answers[self.answer_index(family, value_type)]
                if value_type is int:
                    # True == 1 in Python: this distinguishes strict JSON type
                    # comparison from ordinary equality, rather than merely
                    # comparing a boolean against a different numeric value.
                    expected = next(slot for slot in slots if slot["slot_id"] == answer["slot_id"])
                    expected["value"] = 1
                answer["value"] = replacement
                result = prototype.score_slots(slots, answers)
                self.assertTrue(result["critical_errors"])
                expected = 2 if family == "context" else 6
                self.assertEqual(result["family_scores"][family]["matched"], expected)

    def test_wrong_unit_and_each_wrong_source_component_are_rejected(self):
        changes = (
            ("unit", "people"),
            ("source_id", "control-source-B"),
            ("row_group", 1),
            ("row_group", False),
            ("row", 12),
            ("row", 11.0),
            ("field", "nonexistent_control_field"),
        )
        for field, replacement in changes:
            with self.subTest(field=field):
                answers = copy.deepcopy(self.answers)
                answer = answers[self.answer_index("context", int)]
                if field == "unit":
                    answer[field] = replacement
                else:
                    answer["source"][field] = replacement
                result = prototype.score_slots(self.slots, answers)
                self.assertTrue(result["critical_errors"])
                self.assertEqual(result["family_scores"]["context"]["matched"], 2)

    def test_asserted_value_for_unknown_scientific_field_is_critical(self):
        scientific = next(slot for slot in self.slots if slot["family"] == "scientific")
        answers = copy.deepcopy(self.answers)
        answers.append(
            {
                "slot_id": scientific["slot_id"],
                "value": 17,
                "unit": scientific["unit"],
                "source": copy.deepcopy(scientific["source"]),
            }
        )
        result = prototype.score_slots(self.slots, answers)
        self.assertTrue(result["critical_errors"])
        score = result["family_scores"]["scientific"]
        self.assertEqual(score["answerable"], 0)
        self.assertEqual(score["matched"], 0)
        self.assertIsNone(score["coverage"])

    def test_explicit_unknown_preserves_unknown_without_critical_error(self):
        scientific = next(slot for slot in self.slots if slot["family"] == "scientific")
        answers = copy.deepcopy(self.answers)
        answers.append(
            {
                "slot_id": scientific["slot_id"],
                "value": None,
                "unit": None,
                "source": copy.deepcopy(scientific["source"]),
            }
        )
        result = prototype.score_slots(self.slots, answers)
        self.assertEqual(result["critical_errors"], [])
        score = result["family_scores"]["scientific"]
        self.assertEqual(score["answerable"], 0)
        self.assertEqual(score["matched"], 0)
        self.assertIsNone(score["coverage"])

    def test_duplicate_and_unknown_slot_ids_are_critical_without_inflation(self):
        answers = copy.deepcopy(self.answers)
        answers.append(copy.deepcopy(answers[0]))
        unknown = copy.deepcopy(answers[0])
        unknown["slot_id"] = "nonexistent_control_slot"
        answers.append(unknown)
        result = prototype.score_slots(self.slots, answers)
        self.assertGreaterEqual(len(result["critical_errors"]), 2)
        for score in result["family_scores"].values():
            self.assertLessEqual(score["matched"], score["answerable"])

    def test_missing_input_requires_exact_collection_bounded_status_and_no_assertions(self):
        accepted = "insufficient_input_in_selected_collection"
        self.assertTrue(prototype.missing_input_result(accepted, []))
        self.assertFalse(prototype.missing_input_result(accepted, self.answers[:1]))
        for status in (
            "no_biological_association",
            "collection_incomplete",
            "no_evidence_exists",
            "completed",
            "",
        ):
            with self.subTest(status=status):
                self.assertFalse(prototype.missing_input_result(status, []))


if __name__ == "__main__":
    unittest.main()
