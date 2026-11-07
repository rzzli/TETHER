"""Source-reference sampler tests use invented provider-shaped local fixtures."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.ingest import build_snapshot
from tether_engine.journal import inspect_run, read_chain
from tether_engine.serde import ContractError, read_json, sha256_file, write_json
from tests import test_v02_ingest as fixtures
from tools.science import reference_packets as reference


def candidate(number, category="genetics", provider="provider", study=None):
    return {"observation_id": "fixture-" + str(number), "category": category, "study_id": study,
        "source_locator": {"source_id": "raw-fixture", "row_group": 0, "row": number, "datasource_id": provider},
        "source_metrics": {"score": number / 100}, "features": {}, "unmodified_field": [None, {"nested": True}]}


class ReferenceSelectionTests(unittest.TestCase):
    def test_deterministic_order_invariant_diversity_without_score_ranking(self):
        observations = [candidate(i, category, "provider-" + str(i % 3), "study-" + str(i))
            for i, category in enumerate(("genetics", "genetics", "expression", "perturbation", "pathway", "literature", "literature"))]
        selected = reference.select_observations(observations, "fixture-case")
        reversed_selected = reference.select_observations(list(reversed(observations)), "fixture-case")
        self.assertEqual(selected, reversed_selected)
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({row["category"] for row in selected}), 5)
        changed = copy.deepcopy(observations)
        for i, row in enumerate(changed):
            row["source_metrics"]["score"] = 1000 - i
        self.assertEqual([row["observation_id"] for row in selected],
            [row["observation_id"] for row in reference.select_observations(changed, "fixture-case")])
        self.assertEqual(selected[0]["unmodified_field"], [None, {"nested": True}])

    def test_provider_and_known_study_diversity_break_remaining_ties(self):
        observations = [candidate(0, provider="one", study="study-a"),
            candidate(1, provider="two", study="study-b"), candidate(2, provider="three", study="study-c"),
            candidate(3, provider="one", study="study-d")]
        selected = reference.select_observations(observations, "fixture", maximum=3)
        self.assertEqual(len({row["source_locator"]["datasource_id"] for row in selected}), 3)

    def test_duplicates_bad_locators_and_invalid_limits_fail(self):
        bad_sets = [[candidate(0), candidate(0)], [candidate(0), {**candidate(1), "source_locator": candidate(0)["source_locator"]}],
            [{**candidate(0), "source_locator": {"source_id": "x", "row_group": False, "row": 0}}]]
        for observations in bad_sets:
            with self.subTest(observations=observations), self.assertRaises(ContractError):
                reference.select_observations(observations, "fixture")
        for maximum in (0, 6, True, 1.5):
            with self.subTest(maximum=maximum), self.assertRaises(ContractError):
                reference.select_observations([candidate(0)], "fixture", maximum=maximum)
        self.assertEqual(reference.select_observations([], "fixture"), [])


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for source-audit tests")
class ReferencePacketBuildTests(unittest.TestCase):
    setUp = fixtures.IngestTests.setUp
    tearDown = fixtures.IngestTests.tearDown
    save_manifest = fixtures.IngestTests.save_manifest
    receipt = fixtures.IngestTests.receipt
    evidence = fixtures.IngestTests.evidence

    def make_build(self, zero=False):
        self.case_pack = self.root / "cases.json"
        write_json(self.case_pack, {"schema_version": 1, "cases": [{"symbol": "CD276", "disease_id": "EFO_0003060",
            "intended_action": "inhibit", "modality": "antibody", "tissue": None,
            "target_id": fixtures.GENES["CD276"], "hgnc_id": "HGNC:fictional-0"}]})
        if zero:
            self.evidence(self.rows[1:])
        self.bundle = self.root / "bundle"
        report = build_snapshot(self.manifest, self.catalog, self.bundle, cases_path=self.case_pack,
                                cases_sha256=sha256_file(self.case_pack), packet_layout="bounded")
        self.case_id = report["cases"][0]["case_id"]
        self.case_folder = self.bundle / self.case_id
        return report

    def prepare(self, output="reference", **kwargs):
        # The production function's immutable protocol anchor is replaced only
        # inside this invented fixture test, never in production audit code.
        with patch.object(reference, "CASE_PACK_SHA256", sha256_file(self.case_pack)):
            return reference.build_reference_packets(self.bundle, self.root / output,
                case_pack=self.case_pack, catalog_path=self.catalog,
                case_pack_sha256=sha256_file(self.case_pack), **kwargs)

    def reseal_packet(self, alter):
        report = read_json(self.bundle / "build-report.json")
        snapshot = read_json(self.case_folder / "snapshot.json")
        path = self.case_folder / "evidence.json"
        packet = read_json(path)
        alter(packet["observations"])
        write_json(path, packet, compact=True)
        digest, size = sha256_file(path), path.stat().st_size
        report["cases"][0]["observations"] = len(packet["observations"])
        report["cases"][0]["packet_bytes"] = size
        report["cases"][0]["packet_sha256"] = digest
        report["cases"][0]["packets"][0].update(sha256=digest, bytes=size, observations=len(packet["observations"]))
        snapshot["artifacts"][0]["sha256"] = digest
        snapshot["coverage"]["matching_observations"] = len(packet["observations"])
        write_json(self.bundle / "build-report.json", report)
        write_json(self.case_folder / "snapshot.json", snapshot)

    def test_complete_original_row_audit_retains_whole_observation_and_unknowns(self):
        self.make_build()
        source_packet = read_json(self.case_folder / "evidence.json")
        report = self.prepare()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["audited_rows"], 1)
        self.assertFalse(report["absence_claim"])
        self.assertEqual(read_json(self.root / "reference" / self.case_id / "source-packet.json"), source_packet)
        context = read_json(self.root / "reference" / self.case_id / "reference-context.json")
        self.assertFalse(context["absence_claim"])
        self.assertEqual(context["scientific_validation"], "not_established")
        audit = read_json(self.root / "reference" / self.case_id / "raw-row-audit.json")[0]
        self.assertEqual(audit["technical_result"], "passed")
        self.assertEqual(audit["physical_locator"]["row_group"], 0)
        self.assertEqual(audit["physical_locator"]["row"], 0)
        self.assertIn("species", audit["missingness"])
        self.assertTrue(audit["source"]["source_url"].startswith("https://ftp.ebi.ac.uk/"))
        self.assertEqual(read_chain(self.root / "reference" / "journal.jsonl")[-1]["event"], "reference_completed")

    def test_zero_evidence_has_explicit_coverage_without_absence_claim(self):
        self.make_build(zero=True)
        report = self.prepare()
        self.assertEqual(report["audited_rows"], 0)
        self.assertTrue(report["cases"][0]["zero_evidence"])
        context = read_json(self.root / "reference" / self.case_id / "reference-context.json")
        self.assertTrue(context["zero_evidence"])
        self.assertFalse(context["absence_claim"])
        self.assertEqual(context["available_observations"], 0)
        self.assertEqual(read_json(self.root / "reference" / self.case_id / "source-packet.json")["observations"], [])

    def test_byte_tampering_and_wrong_external_build_anchor_fail_durably(self):
        self.make_build()
        with self.assertRaisesRegex(ContractError, "externally supplied"):
            self.prepare("bad-anchor", build_report_sha256="0" * 64)
        evidence = self.case_folder / "evidence.json"
        evidence.write_bytes(evidence.read_bytes() + b" \n")
        with self.assertRaisesRegex(ContractError, "artifact integrity"):
            self.prepare("bad-packet")
        failure = read_json(self.root / "bad-packet" / "reference-failure.json")
        self.assertEqual(failure["stage"], "artifact_validation")
        self.assertEqual(inspect_run(self.root / "bad-packet")["last_event"], "build_failed")

    def test_resealed_duplicate_and_invalid_locator_are_rejected(self):
        self.make_build()
        self.reseal_packet(lambda rows: rows.append(copy.deepcopy(rows[0])))
        with self.assertRaisesRegex(ContractError, "Duplicate"):
            self.prepare("duplicate")
        self.reseal_packet(lambda rows: (rows.pop(), rows[0]["source_locator"].update(row=999999)))
        with self.assertRaisesRegex(ContractError, "outside row group"):
            self.prepare("bad-locator")

    def test_resealed_metrics_missingness_and_projection_tampering_are_rejected(self):
        self.make_build()
        original = read_json(self.case_folder / "evidence.json")["observations"][0]
        changes = [lambda row: row["source_metrics"].update(score=0.99),
                   lambda row: row["missingness"].pop("species"),
                   lambda row: row["method"]["parameters"]["projection"].append("clinicalStatus"),
                   lambda row: row["method"]["parameters"].update(source_row_sha256="0" * 64),
                   lambda row: row["context"].update(tissue="inferred lung")]
        for number, change in enumerate(changes):
            def mutate(rows):
                rows[0] = copy.deepcopy(original)
                change(rows[0])
            self.reseal_packet(mutate)
            with self.subTest(change=number), self.assertRaises(ContractError):
                self.prepare("tampered-" + str(number))

    def test_scope_change_features_and_missing_lineage_fail(self):
        self.make_build()
        original = read_json(self.case_folder / "case.json")
        altered = copy.deepcopy(original)
        altered["hypothesis"]["intended_action"] = "activate"
        write_json(self.case_folder / "case.json", altered)
        with self.assertRaisesRegex(ContractError, "frozen scope"):
            self.prepare("wrong-scope")
        write_json(self.case_folder / "case.json", original)
        self.reseal_packet(lambda rows: rows[0]["input_refs"].pop())
        with self.assertRaises(ContractError):
            self.prepare("missing-lineage")

    def test_no_overwrite_and_interruptions_leave_records_without_success_report(self):
        self.make_build()
        self.prepare()
        before = (self.root / "reference" / "journal.jsonl").read_bytes()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual((self.root / "reference" / "journal.jsonl").read_bytes(), before)
        with patch.object(reference.SourceAudit, "parquet_row", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.prepare("interrupted")
        self.assertFalse((self.root / "interrupted" / "reference-report.json").exists())
        failure = read_json(self.root / "interrupted" / "reference-failure.json")
        self.assertEqual(failure["status"], "interrupted")
        self.assertEqual(inspect_run(self.root / "interrupted")["last_event"], "build_interrupted")
