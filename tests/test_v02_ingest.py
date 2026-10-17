import csv
import importlib.util
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from asof.agents import ExtractiveBackend
from asof.artifacts import verify_run, write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.ingest import PILOT, InputFile, InputManifest, build_snapshot, inspect_sources
from asof.journal import inspect_run, read_chain
from asof.serde import ContractError, canonical, decode, read_json, sha256_file, write_json
from asof.workflow import run_workflow

GENES = {"CD276": "ENSG00000103855", "OSMR": "ENSG00000145623", "ERBB2": "ENSG00000141736",
         "PCSK9": "ENSG00000169174", "IL6R": "ENSG00000160712", "CFTR": "ENSG00000001626",
         "GLP1R": "ENSG00000112164", "SCN9A": "ENSG00000169432"}


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for adapter tests")
class IngestTests(unittest.TestCase):
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.pa, self.pq = pa, pq
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.catalog = self.root / "catalog.json"
        write_json(self.catalog, {"schema_version": 1, "datasets": [
            {"dataset_id": key, "roles": ["reference"] if key == "hgnc_symbols" else ["agent_evidence"]}
            for key in ("ot_target", "ot_disease", "ot_evidence", "hgnc_symbols", "asof_normalized_packets")]})
        target = [{"id": value, "approvedSymbol": key, "approvedName": "Fictional fixture", "biotype": "protein_coding"}
                  for key, value in GENES.items()]
        disease = [{"id": key, "name": "Fictional disease label " + key} for key in sorted({row[1] for row in PILOT})]
        self.pq.write_table(self.pa.Table.from_pylist(target), self.raw / "target.parquet")
        self.pq.write_table(self.pa.Table.from_pylist(disease), self.raw / "disease.parquet")
        self.rows = [{"id": f"fictional-{i}", "targetId": GENES[symbol], "diseaseId": disease,
                      "datasourceId": "eva", "datatypeId": "genetic_association", "score": 0.25 + i / 100,
                      "studyId": None, "cohortId": None, "ancestry": None, "cellType": None,
                      "publicationYear": None,
                      "clinicalStatus": "FORBIDDEN_OUTCOME_CONTENT", "studyStopReason": "FORBIDDEN_SAFETY_LABEL"}
                     for i, (symbol, disease, action, modality) in enumerate(PILOT)]
        self.pq.write_table(self.pa.Table.from_pylist(self.rows), self.raw / "evidence.parquet")
        with (self.raw / "hgnc.tsv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["hgnc_id", "symbol", "status", "ensembl_gene_id"], delimiter="\t")
            writer.writeheader()
            for i, (symbol, gene_id) in enumerate(GENES.items()):
                writer.writerow({"hgnc_id": f"HGNC:fictional-{i}", "symbol": symbol, "status": "Approved", "ensembl_gene_id": gene_id})
        self.manifest = self.root / "inputs.json"
        self.entries = [InputFile(dataset, release, filename, filename + ".receipt.json") for dataset, release, filename in (
            ("ot_target", "25.09", "target.parquet"), ("ot_disease", "25.09", "disease.parquet"),
            ("ot_evidence", "25.09", "evidence.parquet"), ("hgnc_symbols", "snapshot_2026-10-10", "hgnc.tsv"))]
        for entry in self.entries:
            self.receipt(entry)
        self.save_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def save_manifest(self, expected=None):
        write_json(self.manifest, InputManifest(2, str(self.raw), tuple(self.entries), expected or {
            entry.dataset_id: 1 for entry in self.entries}))

    def receipt(self, entry):
        path = self.raw / entry.relative_path
        write_json(self.raw / entry.receipt_path, {"status": "completed", "dataset_id": entry.dataset_id,
                   "release_id": entry.release_id, "relative_path": entry.relative_path,
                   "sha256": sha256_file(path), "bytes": path.stat().st_size,
                   "url": "https://ftp.ebi.ac.uk/fictional-fixture/" + path.name,
                   "completed_at_utc": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                   "fixture": "Invented format/contract test; not a real provider acquisition"})

    def evidence(self, rows):
        self.pq.write_table(self.pa.Table.from_pylist(rows), self.raw / "evidence.parquet")
        self.receipt(self.entries[2])

    def build(self):
        output = self.root / "snapshot"
        report = build_snapshot(self.manifest, self.catalog, output)
        return output, report

    def test_actual_format_fixtures_build_all_ten_and_verify_semantics(self):
        inspected = inspect_sources(self.manifest, self.catalog)
        self.assertEqual(inspected["selected_files"], 4)
        output, report = self.build()
        self.assertEqual(len(report["cases"]), 10)
        self.assertFalse(report["blocked_cases"])
        for case_summary in report["cases"]:
            directory = output / case_summary["case_id"]
            case = decode(Case, read_json(directory / "case.json"))
            store = load_snapshot(directory / "snapshot.json", case, self.catalog)
            result = run_workflow(case, store, ExtractiveBackend())
            self.assertIsNone(result.prediction.probability)
            self.assertTrue(all(feature.value is None for feature in result.features.values.values()))
            run = self.root / ("run-" + case.case_id)
            digest = write_run(run, result, store, None)
            self.assertEqual(verify_run(run, digest)["semantic_consistency"], "verified")

    def test_clinical_columns_do_not_enter_packets_and_unknowns_stay_null(self):
        output, report = self.build()
        directory = output / report["cases"][0]["case_id"]
        payload = (directory / "evidence.json").read_text(encoding="utf-8")
        for value in ("clinicalStatus", "studyStopReason", "FORBIDDEN_OUTCOME", "FORBIDDEN_SAFETY"):
            self.assertNotIn(value, payload)
        observation = read_json(directory / "evidence.json")["observations"][0]
        self.assertIsNone(observation["context"]["species"])
        self.assertIsNone(observation["study_id"])
        self.assertIsNone(observation["quantitative"]["effect"])
        self.assertEqual(observation["source_metrics"]["score"], 0.25)
        self.assertEqual(observation["features"], {})

    def test_opt_in_bounded_packets_preserve_all_records_and_verify(self):
        original, baseline = self.build()
        before = {r["case_id"]: read_json(original / r["case_id"] / "evidence.json")["observations"]
                  for r in baseline["cases"]}
        limit = max(len(canonical({"schema_version": 2, "observations": [r]}))
                    for rows in before.values() for r in rows) + 128
        output = self.root / "bounded"
        with patch("asof.ingest.MAX_NORMALIZED_JSON_BYTES", limit):
            report = build_snapshot(self.manifest, self.catalog, output, packet_layout="bounded")
        self.assertEqual(report["normalization_recipe"]["packet_layout"], "bounded")
        multiple = []
        for item in report["cases"]:
            directory = output / item["case_id"]
            snapshot = read_json(directory / "snapshot.json")
            rows = []
            for packet, artifact in zip(item["packets"], snapshot["artifacts"]):
                path = directory / packet["path"]
                self.assertEqual(packet["sha256"], sha256_file(path))
                self.assertEqual(artifact["sha256"], packet["sha256"])
                self.assertLessEqual(path.stat().st_size, limit)
                rows.extend(read_json(path)["observations"])
            self.assertEqual(rows, before[item["case_id"]])
            self.assertEqual(sum(p["bytes"] for p in item["packets"]), item["packet_bytes"])
            if len(item["packets"]) > 1:
                multiple.append(directory)
                self.assertIsNone(item["packet_sha256"])
        self.assertTrue(multiple)
        directory = multiple[0]
        case = decode(Case, read_json(directory / "case.json"))
        store = load_snapshot(directory / "snapshot.json", case, self.catalog)
        result = run_workflow(case, store, ExtractiveBackend())
        run = self.root / "bounded-run"
        anchor = write_run(run, result, store, None)
        self.assertEqual(verify_run(run, anchor)["semantic_consistency"], "verified")
        second = read_json(directory / "snapshot.json")["artifacts"][1]
        (directory / second["path"]).write_text("{}", encoding="utf-8")
        with self.assertRaises(ContractError):
            verify_run(run, anchor)

    def test_oversized_single_record_still_fails_with_bounded_layout(self):
        with patch("asof.ingest.MAX_NORMALIZED_JSON_BYTES", 100):
            with self.assertRaisesRegex(ContractError, "single observation"):
                build_snapshot(self.manifest, self.catalog, self.root / "too-large", packet_layout="bounded")
        failure = read_json(self.root / "too-large" / "build-failure.json")
        self.assertEqual(failure["stage"], "packet_finalization")

    def test_single_packet_default_does_not_implicitly_shard(self):
        with patch("asof.ingest.MAX_NORMALIZED_JSON_BYTES", 100):
            with self.assertRaisesRegex(ContractError, "Oversized evidence packet"):
                build_snapshot(self.manifest, self.catalog, self.root / "single-large")
        self.assertEqual(read_json(self.root / "single-large" / "build-failure.json")["status"], "failed")

    def test_future_unknown_datatype_and_known_drug_records_are_excluded(self):
        rows = self.rows + [dict(self.rows[0], id="future", publicationYear=2099),
                            dict(self.rows[0], id="unsupported", datatypeId="mystery"),
                            dict(self.rows[0], id="clinical", datasourceId="chembl", datatypeId="known_drug")]
        self.evidence(rows)
        output, report = self.build()
        for reason in ("publication_after_origin", "unsupported_datatype", "excluded_clinical_evidence"):
            self.assertEqual(report["counters"][reason], 1)

    def test_future_source_release_date_is_excluded(self):
        self.evidence([dict(row, releaseDate=None) for row in self.rows] +
                      [dict(self.rows[0], id="future-release", releaseDate="2099-01-01")])
        _, report = self.build()
        self.assertEqual(report["counters"]["publication_after_origin"], 1)

    def test_identical_duplicate_coalesces_and_conflicting_duplicate_fails(self):
        self.evidence(self.rows + [dict(self.rows[0])])
        _, report = self.build()
        self.assertEqual(report["counters"]["identical_duplicates_coalesced"], 1)
        self.evidence(self.rows + [dict(self.rows[0], score=0.99)])
        with self.assertRaisesRegex(ContractError, "Conflicting duplicate"):
            build_snapshot(self.manifest, self.catalog, self.root / "conflicting")

    def test_missing_inputs_are_not_biological_absence(self):
        self.save_manifest({"ot_target": 1, "ot_disease": 1, "hgnc_symbols": 1, "ot_evidence": 2})
        output, report = self.build()
        snapshot = read_json(output / report["cases"][0]["case_id"] / "snapshot.json")
        self.assertEqual(snapshot["coverage"]["source_completeness"], "selected_subset")
        self.assertFalse(snapshot["coverage"]["absence_claim"])

    def test_missing_canonical_identifier_blocks_cases_without_replacement(self):
        target = self.pq.read_table(self.raw / "target.parquet").to_pylist()
        target = [row for row in target if row["approvedSymbol"] != "CD276"]
        self.pq.write_table(self.pa.Table.from_pylist(target), self.raw / "target.parquet")
        self.receipt(self.entries[0])
        _, report = self.build()
        self.assertEqual(len(report["cases"]), 9)
        self.assertEqual(len(report["blocked_cases"]), 1)
        self.assertTrue(report["blocked_cases"][0]["case_id"].startswith("cd276"))

    def test_bad_hash_receipt_identity_and_raw_schema_fail_closed(self):
        receipt_path = self.raw / self.entries[0].receipt_path
        original = read_json(receipt_path)
        for change in ({"sha256": "0" * 64}, {"dataset_id": "vbt_labels"}):
            with self.subTest(change=change):
                write_json(receipt_path, {**original, **change})
                with self.assertRaises(ContractError):
                    inspect_sources(self.manifest, self.catalog)
        write_json(receipt_path, original)
        self.pq.write_table(self.pa.Table.from_pylist([{"targetId": "wrong-column"}]), self.raw / "target.parquet")
        self.receipt(self.entries[0])
        with self.assertRaisesRegex(ContractError, "columns missing"):
            inspect_sources(self.manifest, self.catalog)

    def test_wrong_release_path_escape_and_evaluator_source_are_denied(self):
        original = read_json(self.manifest)
        for change in ({"release_id": "26.01"}, {"relative_path": "../outside.parquet"}, {"dataset_id": "vbt_labels"}):
            with self.subTest(change=change):
                document = {**original, "files": [dict(row) for row in original["files"]]}
                document["files"][0].update(change)
                write_json(self.manifest, document)
                with self.assertRaises(ContractError):
                    inspect_sources(self.manifest, self.catalog)

    def test_missing_evidence_file_reports_partial_coverage(self):
        (self.raw / "evidence.parquet").unlink()
        inspected = inspect_sources(self.manifest, self.catalog)
        self.assertIn("evidence.parquet", inspected["missing_inputs"])
        output, report = self.build()
        self.assertEqual(len(report["cases"]), 10)
        self.assertTrue(all(case["observations"] == 0 for case in report["cases"]))

    def test_scientific_source_context_is_preserved_without_tissue_inference(self):
        context = {"cellType": "source cell type", "biosamplesFromSource": [{"biosampleId": "fixture-organ", "biosampleName": "Reported organ"}],
                   "diseaseCellLines": [{"id": "fixture-cell", "name": "Reported cell line"}],
                   "biologicalModelId": "fixture-mouse", "biologicalModelAllelicComposition": "reported genotype",
                   "targetInModelMgiId": "MGI:fixture", "variantId": "1_100_A_G", "variantRsId": "rs-fixture",
                   "variantFunctionalConsequenceId": "SO:fixture", "variantEffect": "increased_gene_product_level",
                   "directionOnTrait": "risk", "alleleOrigins": ["germline"]}
        self.evidence([dict(self.rows[0], **context)] + self.rows[1:])
        output, report = self.build()
        observation = read_json(output / report["cases"][0]["case_id"] / "evidence.json")["observations"][0]
        for key, value in context.items():
            self.assertEqual(observation["source_metrics"][key], value)
        self.assertIsNone(observation["context"]["tissue"])
        self.assertIsNone(observation["context"]["species"])
        self.assertIn("tissue", observation["missingness"])
        self.assertEqual(observation["features"], {})
        self.assertEqual(observation["mechanism_direction"], "uncertain")

    def test_arrow_filter_preserves_physical_batch_and_row_group_offsets(self):
        rows = [dict(self.rows[0], id="unselected", targetId="ENSG_OUTSIDE_PILOT") for _ in range(70005)]
        selected = (0, 65536, 70001)
        for number in selected:
            rows[number] = dict(self.rows[0], id=f"selected-{number}")
        rows[1] = dict(rows[1], targetId=None)
        self.pq.write_table(self.pa.Table.from_pylist(rows), self.raw / "evidence.parquet", row_group_size=70000)
        self.receipt(self.entries[2])
        output, report = self.build()
        observations = read_json(output / report["cases"][0]["case_id"] / "evidence.json")["observations"]
        self.assertEqual([(row["source_locator"]["row_group"], row["source_locator"]["row"]) for row in observations],
                         [(0, 0), (0, 65536), (1, 1)])
        self.assertEqual(report["counters"]["physical_rows_scanned"], 70005)
        self.assertEqual(report["counters"]["selected_rows"], 3)
        self.assertEqual(report["counters"]["accepted_source_rows"], 3)

    def test_archived_receipts_retain_exact_inspected_bytes_after_transport_rewrite(self):
        from asof import ingest
        originals = {entry.receipt_path: (self.raw / entry.receipt_path).read_bytes() for entry in self.entries}
        archive = ingest._archive_receipts

        def rewrite_transport(root, files):
            for entry in self.entries:
                receipt = read_json(self.raw / entry.receipt_path)
                write_json(self.raw / entry.receipt_path, {**receipt, "retry_note": "transport changed after inspection"})
            return archive(root, files)

        with patch("asof.ingest._archive_receipts", side_effect=rewrite_transport):
            output, report = self.build()
        directory = output / report["cases"][0]["case_id"]
        snapshot = read_json(directory / "snapshot.json")
        for node in snapshot["sources"]:
            archived = self.raw / node["receipt_path"]
            self.assertIn("manifests/receipt-archive/", node["receipt_path"])
            self.assertEqual(archived.name, node["receipt_sha256"] + ".json")
            self.assertIn(archived.read_bytes(), originals.values())
            self.assertEqual(sha256_file(archived), node["receipt_sha256"])
        case = decode(Case, read_json(directory / "case.json"))
        load_snapshot(directory / "snapshot.json", case, self.catalog)

    def test_inspection_failure_and_interruption_leave_durable_terminal_records(self):
        for error, expected in ((ContractError("fixture bad receipt"), "build_failed"),
                                (KeyboardInterrupt(), "build_interrupted")):
            with self.subTest(error=type(error).__name__):
                output = self.root / expected
                with patch("asof.ingest._inspect", side_effect=error):
                    with self.assertRaises(type(error)):
                        build_snapshot(self.manifest, self.catalog, output)
                inspected = inspect_run(output)
                self.assertEqual(inspected["last_event"], expected)
                self.assertEqual(inspected["stage"], "inspection")
                self.assertEqual(inspected["failure"]["error_class"], type(error).__name__)
                self.assertTrue((output / "build-failure.json").is_file())
                self.assertEqual(read_chain(output / "journal.jsonl")[0]["event"], "build_reserved")

    def test_packet_write_failure_retains_progress_and_failure(self):
        from asof import ingest
        real_write = ingest.write_json

        def fail_packet(path, value, **kwargs):
            if path.name == "evidence.json":
                raise OSError("fixture full disk")
            return real_write(path, value, **kwargs)

        with patch("asof.ingest.write_json", side_effect=fail_packet):
            with self.assertRaisesRegex(OSError, "full disk"):
                self.build()
        inspected = inspect_run(self.root / "snapshot")
        self.assertEqual(inspected["last_event"], "build_failed")
        self.assertEqual(inspected["failure"]["stage"], "packet_finalization")
        self.assertEqual(inspected["progress"]["counters"]["physical_rows_scanned"], len(self.rows))
        self.assertFalse(inspected["build_report_present"])

    def test_concurrent_build_reservation_never_reuses_output(self):
        output = self.root / "concurrent"
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(build_snapshot, self.manifest, self.catalog, output) for _ in range(2)]
            succeeded, failed = [], []
            for future in futures:
                try:
                    succeeded.append(future.result())
                except FileExistsError as error:
                    failed.append(error)
        self.assertEqual(len(succeeded), 1)
        self.assertEqual(len(failed), 1)
        self.assertEqual(inspect_run(output)["last_event"], "build_completed")
        self.assertEqual(len(succeeded[0]["cases"]), 10)

