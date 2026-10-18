from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError, sha256_file
from tools.science.crosswalk import compare, hypothesis_key, pinned, source_identity


def fixture():
    hypothesis = {"target_id": "ENSGfixture", "indication_id": "EFO_fixture",
        "target_namespace_version": "fixture-v1", "indication_namespace_version": "fixture-v1",
        "intended_action": "inhibit", "modality": "antibody", "tissue": None}
    observation = {"observation_id": "fixture-observation", "statement": "Fictional association.",
        "source_locator": {"source_id": "fixture-source", "row_group": 0, "row": 3,
            "evidence_id": "fictional-evidence", "datasource_id": "fixture"},
        "context": {"tissue": None}, "method": {"version": "fixture-v1",
            "parameters": {"source_row_sha256": "a" * 64}}, "source_metrics": {"score": .2}}
    source = {"source_id": "fixture-source", "dataset_id": "fixture-dataset",
        "release_id": "fixture-v1", "sha256": "b" * 64, "path": "fixture.parquet"}
    return hypothesis, observation, source


class ScienceCrosswalkTests(unittest.TestCase):
    def test_exact_applicability_does_not_copy_or_promote_ratings(self):
        h, o, s = fixture(); original = deepcopy(o)
        result = compare(h, h, o, deepcopy(o), s, s)
        self.assertEqual(result["applicability"], "exact_match")
        self.assertTrue(result["new_assessment_required"])
        self.assertFalse(result["copied_ratings"])
        self.assertFalse(result["independent_gold"])
        self.assertNotIn("assessment", result)
        self.assertNotIn("ratings", result)
        self.assertEqual(o, original)

    def test_changed_context_and_normalization_are_stale_even_same_assertion(self):
        h, o, s = fixture()
        for mutate in (lambda n: n["context"].update(tissue="liver"),
                       lambda n: n["method"].update(version="fixture-v2"),
                       lambda n: n.update(program_id="different-program"),
                       lambda n: n.update(category="different-category"),
                       lambda n: n.update(input_refs=["new-annotation-parent"]),
                       lambda n: n["source_metrics"].update(directionOnTrait="decreased")):
            new = deepcopy(o); mutate(new)
            result = compare(h, h, o, new, s, s)
            self.assertEqual(result["applicability"], "same_statement_changed_context")
            self.assertTrue(result["changed_scientific_fields"])

    def test_changed_statement_and_source_are_distinct(self):
        h, o, s = fixture(); new = deepcopy(o); new["statement"] += " New wording."
        self.assertEqual(compare(h, h, o, new, s, s)["applicability"], "same_source_changed_statement")
        for field in ("release_id", "sha256", "path"):
            newer = deepcopy(s); newer[field] += "changed"
            self.assertEqual(compare(h, h, o, o, s, newer)["applicability"], "source_version_changed")
        new = deepcopy(o); new["source_locator"]["row"] = 4
        self.assertEqual(compare(h, h, o, new, s, s)["applicability"], "source_version_changed")

    def test_action_modality_tissue_and_namespace_changes_prevent_reuse(self):
        h, o, s = fixture()
        for field, value in (("intended_action", "activate"), ("modality", "adc"),
                ("tissue", "liver"), ("target_namespace_version", "fixture-v2"),
                ("indication_namespace_version", "fixture-v2")):
            new = deepcopy(h); new[field] = value
            self.assertNotEqual(hypothesis_key(h), hypothesis_key(new))
            self.assertEqual(compare(h, new, o, o, s, s)["applicability"], "hypothesis_changed")

    def test_missing_record_is_unmatched_and_changed_observation_id_is_rejected(self):
        h, o, s = fixture()
        self.assertEqual(compare(h, h, o, None, s, None)["applicability"], "unmatched")
        new = deepcopy(o); new["observation_id"] = "different"
        with self.assertRaises(ContractError): compare(h, h, o, new, s, s)

    def test_missing_or_unresolved_parent_locator_fails(self):
        _, o, s = fixture()
        del o["source_locator"]["row"]
        with self.assertRaises(ContractError): source_identity(o, s)
        _, o, s = fixture(); s["source_id"] = "different"
        with self.assertRaises(ContractError): source_identity(o, s)

    def test_pins_detect_mutation_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / "receipt.json"; path.write_bytes(b"fixture")
            digest = sha256_file(path)
            self.assertEqual(pinned(root, "receipt.json", digest), path)
            path.write_bytes(b"changed")
            with self.assertRaises(ContractError): pinned(root, "receipt.json", digest)
            with self.assertRaises(ContractError): pinned(root, "../outside", digest)

    def test_only_compute_time_change_does_not_rewrite_scientific_relevance(self):
        h, o, s = fixture(); new = deepcopy(o)
        new["computed_at"] = "2026-10-18T00:00:00Z"
        self.assertEqual(compare(h, h, o, new, s, s)["applicability"], "exact_match")


if __name__ == "__main__":
    unittest.main()
