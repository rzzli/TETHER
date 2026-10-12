"""Independent original-row review checks using labeled, actual-format fixtures."""
import copy
import importlib.util
import unittest

from asof.agents import ExtractiveBackend
from asof.artifacts import write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.serde import ContractError, decode, read_json, write_json
from asof.workflow import run_workflow
from tests import test_v02_ingest as fixtures
from tools.framework.run_pilot import SourceAudit


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for source-audit tests")
class PilotAuditTests(unittest.TestCase):
    def setUp(self):
        # Composition deliberately avoids discovering the adapter tests a second time.
        self.fixture = fixtures.IngestTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        rows = []
        for index, original in enumerate(self.fixture.rows):
            for replicate in range(2):
                rows.append(dict(original, id=f"audit-fixture-{index:02d}-{replicate}",
                    studyId="fixture-study" if replicate == 0 else None,
                    cohortId="fixture-cohort" if replicate == 0 else None,
                    ancestry="fixture-ancestry" if replicate == 0 else None,
                    cellType="reported-cell-type" if index == replicate == 0 else None,
                    biosamplesFromSource=[{"biosampleId": "fixture-sample", "biosampleName": "Fixture sample"}]
                        if index == replicate == 0 else None,
                    variantEffect="increased_gene_product_level" if index == replicate == 0 else None,
                    directionOnTrait="risk" if index == replicate == 0 else None,
                    alleleOrigins=["germline"] if index == replicate == 0 else None))
        self.fixture.evidence(rows)
        self.bundle, self.build = self.fixture.build()

    def run_case(self, index=0):
        case_id = self.build["cases"][index]["case_id"]
        case_dir = self.bundle / case_id
        case = decode(Case, read_json(case_dir / "case.json"))
        store = load_snapshot(case_dir / "snapshot.json", case, self.fixture.catalog)
        result = run_workflow(case, store, ExtractiveBackend())
        run_dir = self.fixture.root / ("run-" + case_id)
        write_run(run_dir, result, store, None)
        return run_dir, case_dir

    def test_all_ten_cases_audit_twenty_distinct_original_rows_and_mappings(self):
        audit = SourceAudit()
        for index in range(10):
            audit.case(*self.run_case(index))
        report = audit.report()
        self.assertEqual(len(report["cases"]), 10)
        self.assertEqual(report["distinct_original_rows"], 20)
        self.assertTrue(all(case["audited_distinct_rows"] >= 2 for case in report["cases"]))
        self.assertEqual(len({(row["source_id"], row["row_group"], row["row"]) for row in report["rows"]}), 20)
        self.assertIn("biosamplesFromSource", report["reported_context_fields_checked"])
        self.assertIn("alleleOrigins", report["reported_context_fields_checked"])
        self.assertTrue(all(row["scientific_adjudication"] == "not_run" for row in report["rows"]))
        self.assertTrue(any("study_id" in row["unknown_fields"] for row in report["rows"]))

    def test_normalized_statement_metrics_locators_and_unknowns_cannot_be_tampered(self):
        run_dir, case_dir = self.run_case()
        original = read_json(run_dir / "ledger.json")
        changes = (
            lambda row: row.update(statement="Unsupported clinical assertion"),
            lambda row: row["source_metrics"].update(score=0.99),
            lambda row: row["source_locator"].update(row=1),
            lambda row: row["missingness"].pop("species"),
            lambda row: row["quantitative"].update(effect=0.99),
            lambda row: row["context"].update(species="Homo sapiens"),
            lambda row: row.update(study_id="invented-study"),
            lambda row: row.update(observation_id="invented-observation"),
        )
        for change in changes:
            with self.subTest(change=change):
                document = copy.deepcopy(original)
                change(document["claims"][0]["evidence"]["observation"])
                write_json(run_dir / "ledger.json", document)
                audit = SourceAudit()
                with self.assertRaises(ContractError):
                    audit.case(run_dir, case_dir)
                self.assertFalse(audit.rows)
                self.assertFalse(audit.seen)
                self.assertFalse(audit.contexts)
        write_json(run_dir / "ledger.json", original)
        audit.case(run_dir, case_dir)
        self.assertEqual(len(audit.rows), 2)

    def test_identifier_mapping_and_namespace_tampering_are_rejected(self):
        run_dir, case_dir = self.run_case()
        validation_path = case_dir / "identifier-validation.json"
        validation = read_json(validation_path)
        changed = copy.deepcopy(validation)
        changed["target"][0]["approvedSymbol"] = "WRONG"
        write_json(validation_path, changed)
        with self.assertRaisesRegex(ContractError, "Identifier audit"):
            SourceAudit().case(run_dir, case_dir)
        write_json(validation_path, validation)
        inputs = read_json(run_dir / "inputs.json")
        inputs["case"]["hypothesis"]["target_namespace_version"] = "wrong-release"
        write_json(run_dir / "inputs.json", inputs)
        with self.assertRaisesRegex(ContractError, "pinned development pack"):
            SourceAudit().case(run_dir, case_dir)

    def test_cached_source_hash_does_not_hide_later_file_changes(self):
        run_dir, _ = self.run_case()
        snapshot = read_json(run_dir / "inputs.json")["snapshot"]
        node = next(row for row in snapshot["sources"] if row["dataset_id"] == "ot_evidence")
        audit = SourceAudit()
        path = audit.source(node, snapshot["raw_root"])
        with path.open("ab") as stream:
            stream.write(b"modified-after-first-check")
        with self.assertRaisesRegex(ContractError, "raw hash mismatch"):
            audit.source(node, snapshot["raw_root"])

    def test_source_audit_reads_sealed_ledger_above_input_packet_limit(self):
        run_dir, case_dir = self.run_case()
        with (run_dir / "ledger.json").open("ab") as stream:
            chunk = b" " * (1024 * 1024)
            while stream.tell() <= 64 * 1024 * 1024:
                stream.write(chunk)
        audit = SourceAudit()
        audit.case(run_dir, case_dir)
        self.assertEqual(len(audit.rows), 2)

    def test_invalid_physical_locator_and_insufficient_distinct_rows_fail_explicitly(self):
        run_dir, case_dir = self.run_case()
        original = read_json(run_dir / "ledger.json")
        changed = copy.deepcopy(original)
        changed["claims"][0]["evidence"]["observation"]["source_locator"]["row_group"] = 999
        write_json(run_dir / "ledger.json", changed)
        with self.assertRaisesRegex(ContractError, "row locator"):
            SourceAudit().case(run_dir, case_dir)
        original["claims"] = original["claims"][:1]
        write_json(run_dir / "ledger.json", original)
        with self.assertRaisesRegex(ContractError, "Insufficient distinct rows"):
            SourceAudit().case(run_dir, case_dir)
