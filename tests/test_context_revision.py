"""Regression cases from the AI-assisted review; all biology here is fictional."""
import importlib.util
import copy
import unittest
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import dossier
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case
from tether_engine.ingest import REVIEW_CONTEXT_COLUMNS
from tether_engine.serde import ContractError, canonical, decode, read_json
from tether_engine.workflow import run_workflow
from tests import test_v02_ingest as fixtures
from tools.framework.compare_context_revision import compare_observation


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for adapter tests")
class ContextRevisionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IngestTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_passages_and_variant_classifications_preserve_exact_source_context(self):
        fields = {"textMiningSentences": [{"text": "Fictional background citation, not a treatment experiment.",
                  "section": "discussion", "tStart": 0, "tEnd": 9, "dStart": 10, "dEnd": 20}],
                  "pmcIds": ["PMC-fixture"], "studyOverview": "Fictional diagnostic study",
                  "clinicalSignificances": ["uncertain significance", "likely pathogenic"]}
        self.fixture.evidence([dict(row, **fields) for row in self.fixture.rows])
        output, report = self.fixture.build()
        observation = read_json(output / report["cases"][0]["case_id"] / "evidence.json")["observations"][0]
        for key, value in fields.items():
            self.assertEqual(observation["source_metrics"].get(key), value)
            self.assertIn(key, observation["method"]["parameters"]["projection"])
        self.assertEqual(observation["method"]["version"], "2.2")
        self.assertEqual(observation["method"]["parameters"]["interpretation_scope"], "resource_annotation_only")
        self.assertEqual(observation["features"], {})
        self.assertEqual(observation["mechanism_direction"], "uncertain")
        self.assertNotIn("clinicalStatus", observation["source_metrics"])
        self.assertNotIn("studyStopReason", observation["source_metrics"])
        packet = output / report["cases"][0]["case_id"] / "evidence.json"
        self.assertEqual(packet.read_bytes(), canonical(read_json(packet)))

    def test_context_only_conflicts_cannot_be_coalesced(self):
        self.fixture.evidence([dict(self.fixture.rows[0], clinicalSignificances=["uncertain significance"]),
                               dict(self.fixture.rows[0], clinicalSignificances=["pathogenic"])])
        with self.assertRaisesRegex(ContractError, "Conflicting duplicate"):
            self.fixture.build()

    def test_null_context_and_case_qualifications_stay_unresolved(self):
        self.fixture.evidence([dict(row, clinicalSignificances=None, textMiningSentences=None,
                                   pmcIds=None, studyOverview=None) for row in self.fixture.rows])
        output, report = self.fixture.build()
        for item in report["cases"]:
            directory = output / item["case_id"]
            observation = read_json(directory / "evidence.json")["observations"][0]
            self.assertIn("clinicalSignificances", observation["source_metrics"])
            self.assertIsNone(observation["source_metrics"]["clinicalSignificances"])
            coverage = read_json(directory / "snapshot.json")["coverage"]
            self.assertEqual(coverage["interpretation_scope"], "resource_annotation_only")
            qualifications = coverage["hypothesis_qualification"]
            self.assertTrue(qualifications)
            self.assertTrue(all(value["value"] is None for value in qualifications.values()))
            self.assertFalse(coverage["hypothesis_refined"])
            self.assertEqual(coverage["therapeutic_relevance"], "not_assessed")
        # Same target/disease context is reusable, but action/modality hypotheses differ.
        self.assertNotEqual(report["cases"][2]["hypothesis_key"], report["cases"][3]["hypothesis_key"])
        self.assertEqual((output / report["cases"][2]["case_id"] / "evidence.json").read_bytes(),
                         (output / report["cases"][3]["case_id"] / "evidence.json").read_bytes())

    def test_dossier_surfaces_relevance_boundary_and_missing_qualifications(self):
        output, report = self.fixture.build()
        directory = output / report["cases"][7]["case_id"]
        case = decode(Case, read_json(directory / "case.json"))
        store = load_snapshot(directory / "snapshot.json", case, self.fixture.catalog)
        result = run_workflow(case, store, ExtractiveBackend())
        text = dossier(result, store)
        self.assertIn("Therapeutic relevance: not assessed", text)
        self.assertIn("genotype", text)
        self.assertIn("unspecified", text)
        self.assertIn("Resource annotation", text)
        self.assertIsNone(result.prediction.probability)

    def test_comparison_rejects_scientific_or_source_mutation(self):
        self.fixture.evidence([dict(row, clinicalSignificances=["uncertain significance"])
                               for row in self.fixture.rows])
        output, report = self.fixture.build()
        after = read_json(output / report["cases"][0]["case_id"] / "evidence.json")["observations"][0]
        before = copy.deepcopy(after)
        before["method"]["version"] = "2.1"
        before["method"]["parameters"].pop("interpretation_scope")
        before["method"]["parameters"]["projection"] = [field for field in
            before["method"]["parameters"]["projection"] if field not in REVIEW_CONTEXT_COLUMNS]
        for key in REVIEW_CONTEXT_COLUMNS:
            before["source_metrics"].pop(key, None)
        self.assertEqual(compare_observation(before, after), ["clinicalSignificances"])
        changes = (lambda row: row.update(statement="invented efficacy"),
                   lambda row: row["source_metrics"].update(score=0.99),
                   lambda row: row["source_locator"].update(row=999),
                   lambda row: row["source_metrics"].update(clinicalStatus="trial outcome"),
                   lambda row: row["method"].update(qc_status="not_run"),
                   lambda row: row["method"]["parameters"].pop("interpretation_scope"))
        for change in changes:
            with self.subTest(change=change):
                changed = copy.deepcopy(after)
                change(changed)
                with self.assertRaises(ContractError):
                    compare_observation(before, changed)

    def test_oversized_packet_still_fails_without_truncation(self):
        with patch("tether_engine.ingest.canonical", return_value=b" " * (64 * 1024 * 1024 + 1)):
            with self.assertRaisesRegex(ContractError, "Oversized evidence packet"):
                self.fixture.build()
        failure = read_json(self.fixture.root / "snapshot" / "build-failure.json")
        self.assertEqual(failure["stage"], "packet_finalization")
        self.assertFalse((self.fixture.root / "snapshot" / "build-report.json").exists())


if __name__ == "__main__":
    unittest.main()
