"""Fictional controls for the aggregate-only reported-calendar date profile."""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, parse_json, sha256_file
from tools.science import temporal_dates as dates
from tools.science import temporal_inventory as inventory
from tests import test_science_temporal_inventory as fixtures


class CalendarGrammarTests(unittest.TestCase):
    def test_year_month_and_day_preserve_intervals(self):
        year, month, day = [dates.calendar_interval(x) for x in (2024, "2024-02", "2024-02-29")]
        self.assertEqual(year["upper"] - year["lower"], 366)
        self.assertEqual(month["upper"] - month["lower"], 29)
        self.assertEqual(day["upper"] - day["lower"], 1)
        self.assertEqual([x["precision"] for x in (year, month, day)], ["year", "month", "day"])
        self.assertEqual(dates.calendar_interval("9999")["status"], "valid")
        self.assertEqual(dates.calendar_interval("9999-12-31")["status"], "valid")

    def test_null_empty_malformed_and_unsupported_are_distinct(self):
        for value, status in ((None, "null"), ("", "empty"), ("  ", "empty"),
                              ("2023-02-29", "malformed"), ("2024-13", "malformed"),
                              ("not a date", "malformed"), (True, "unsupported"),
                              (2024.0, "unsupported"), ([2024], "unsupported"),
                              ({"date": 2024}, "unsupported"), ("x" * 1000, "unsupported")):
            with self.subTest(type=type(value).__name__, status=status):
                result = dates.calendar_interval(value)
                self.assertEqual(result["status"], status)
                self.assertNotIn("raw", result)

    def test_datetime_presence_never_changes_reported_calendar_day(self):
        values = ["2024-01-01T00:30:00+14:00", "2024-01-01T23:30:00-12:00",
                  "2024-01-01T00:30", "2024-01-01T00:30:00.123456789Z"]
        parsed = [dates.calendar_interval(value) for value in values]
        self.assertTrue(all(item["lower"] == date(2024, 1, 1).toordinal() for item in parsed))
        self.assertEqual([item["timezone"] for item in parsed], ["present", "present", "absent", "present"])
        self.assertEqual(parsed[-1]["precision"], "datetime_fraction")
        self.assertEqual(dates.calendar_interval(date(2024, 1, 1))["precision"], "day")
        self.assertEqual(dates.calendar_interval(datetime(2024, 1, 1, tzinfo=timezone.utc))["timezone"], "present")

    def test_invalid_time_components_are_not_normalized(self):
        for value in ("2024-01-01T24:00", "2024-01-01T23:60", "2024-01-01T23:59:60",
                      "2024-01-01T00:00+14:99", "2024-01-01T00:00+24:00", "0000", 10000, -1):
            with self.subTest(value=value):
                self.assertEqual(dates.calendar_interval(value)["status"], "malformed")

    def test_zero_month_and_day_are_not_silently_imputed(self):
        for value in ("2024-00", "2024-00-01", "2024-01-00", "2024-00-00"):
            with self.subTest(value=value):
                self.assertEqual(dates.calendar_interval(value)["status"], "malformed")

    def test_cutoff_uses_whole_intervals_and_can_be_zero_difference(self):
        before = dates.calendar_interval("2023")
        at = dates.calendar_interval("2024")
        self.assertEqual(dates.compare_calendar(before, "2024-01-01"), "entirely_before")
        self.assertEqual(dates.compare_calendar(at, "2024-01-01"), "at_or_after")
        self.assertEqual(dates.compare_calendar(at, "2024-07-01"), "crossing")
        old = dates.calendar_interval("2000")
        self.assertEqual(dates.compare_calendar(old, "2024-01-01"), dates.compare_calendar(old, "2025-01-01"))

    def test_policy_is_immutable_and_has_only_the_frozen_projection(self):
        self.assertEqual(tuple(dates.POLICY["columns"]), ("datasourceId", "datatypeId", "publicationYear",
            "publicationDate", "evidenceDate", "releaseDate", "releaseVersion", "studyStartDate"))
        with self.assertRaises(TypeError):
            dates.POLICY["release"] = "26.01"
        self.assertEqual(dates.POLICY["sources"]["uniprot_literature"], "genetic_association")


class DateProfileTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TemporalInventoryTests(methodName="test_existing_output_rejected_without_touching_it")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.raw = self.fixture.root, self.fixture.raw
        self.inventory_dir = self.fixture.output
        self.output = self.root / "profile"
        self.rows = [{"datasourceId": "chembl", "datatypeId": "known_drug", "publicationYear": 2023,
                      "publicationDate": "2024-01-02", "evidenceDate": None, "releaseDate": "2025",
                      "releaseVersion": "DO_NOT_EXPORT_VERSION_7", "studyStartDate": "2022-06",
                      "id": "DO_NOT_DECODE_ID", "clinicalPhase": 3},
                     {"datasourceId": None, "datatypeId": "DO_NOT_EXPORT_DATATYPE", "publicationYear": None,
                      "publicationDate": "DO_NOT_EXPORT_INVALID_DATE", "evidenceDate": "", "releaseDate": "2024-02",
                      "releaseVersion": None, "studyStartDate": "2024-02-01T08:00Z",
                      "id": "DO_NOT_DECODE_ID", "clinicalPhase": 4}]
        self.present = list(dates.POLICY["columns"]) + ["id", "clinicalPhase"]
        self.requests = []
        outer = self
        class FakeFile:
            def __init__(self, stream, **kwargs):
                self.schema_arrow = [fixtures.fake_field(name) for name in outer.present]
                self.metadata = SimpleNamespace(num_rows=len(outer.rows))
                self.num_row_groups = 1

            def iter_batches(self, *, columns, batch_size, **kwargs):
                outer.requests.append(tuple(columns))
                if set(columns) - set(dates.POLICY["columns"]):
                    raise AssertionError("Disallowed source columns decoded")
                values = [{key: row.get(key) for key in columns} for row in outer.rows]
                yield SimpleNamespace(num_rows=len(values), nbytes=128, schema=SimpleNamespace(names=columns),
                                      to_pylist=lambda: values)
        self.fake_file = FakeFile
        self.fixture.arrow.return_value = SimpleNamespace(ParquetFile=FakeFile)
        self.date_arrow = self.enterContext(patch.object(dates, "arrow", return_value=SimpleNamespace(ParquetFile=FakeFile)))
        self.qualify()

    def qualify(self):
        # Exact fictional source metadata is produced by the actual inventory API.
        self.fixture.output = self.inventory_dir
        self.fixture.run_inventory()
        self.report_sha = sha256_file(self.inventory_dir / "report.json")

    def run_profile(self):
        return dates.profile_dates(self.inventory_dir, self.report_sha, self.output)

    def failure(self, pattern="Date profile"):
        with self.assertRaisesRegex((ContractError, OSError), pattern):
            self.run_profile()
        self.assertFalse((self.output / "report.json").exists())
        if self.output.exists():
            failure = parse_json((self.output / "failure.json").read_bytes())
            self.assertFalse(failure["labels_qualified"])
            self.assertNotIn("DO_NOT_EXPORT", json.dumps(failure))

    def test_only_eight_columns_and_aggregate_outputs(self):
        report = self.run_profile()
        self.assertEqual(report["rows_decoded"], 4)
        self.assertEqual(report["files_scanned_complete"], 2)
        self.assertEqual(report["files_selected"], 2)
        self.assertEqual(report["source_declarations"]["matched"], 2)
        self.assertEqual(report["source_declarations"]["null"], 2)
        self.assertEqual(report["datatype_declarations"]["unexpected_string"], 2)
        self.assertTrue(all(set(columns) == set(dates.POLICY["columns"]) for columns in self.requests))
        self.assertNotIn("DO_NOT_EXPORT", json.dumps(report))
        self.assertNotIn("DO_NOT_DECODE", json.dumps(report))
        self.assertFalse(report["historical_evidence_qualified"])
        self.assertFalse(report["labels_qualified"])
        self.assertEqual(report["fields"]["publicationYear"]["states"]["valid"], 2)
        self.assertEqual(sum(report["fields"]["publicationYear"]["states"].values()), 4)
        self.assertEqual(report["pairs"]["publicationYear|publicationDate"]["disjoint"], 2)
        self.assertEqual(report["pairs"]["publicationYear|publicationDate"]["not_comparable"], 2)
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_completed")

    def test_unqualified_source_semantics_are_not_availability(self):
        report = self.run_profile()
        self.assertEqual(report["comparison_basis"], "reported_calendar_intervals; no_UTC_availability_ordering")
        self.assertIn("declared_Arrow_resolution_retained_in_inventory_schema", report["precision_basis"])
        self.assertTrue(all(row["semantics"] == "unqualified_descriptive_only" for row in report["fields"].values()))
        self.assertEqual(report["fields"]["publicationYear"]["cutoffs"]["2024-01-01"]["entirely_before"], 2)

    def test_missing_columns_are_counted_for_all_rows(self):
        # Requalify separate bytes/schema inventory after omitting selected columns.
        self.present.remove("publicationDate")
        self.present.remove("datasourceId")
        self.inventory_dir = self.root / "missing-column-inventory"
        self.qualify()
        report = self.run_profile()
        self.assertEqual(report["fields"]["publicationDate"]["states"]["missing_column"], 4)
        self.assertEqual(report["source_declarations"]["missing_column"], 4)
        self.assertTrue(all("publicationDate" not in columns for columns in self.requests))

    def test_source_mismatch_fails_without_disclosing_value(self):
        self.rows[0]["datasourceId"] = "DO_NOT_EXPORT_WRONG_SOURCE"
        self.failure()

    def test_changed_raw_payload_fails_before_date_decoding(self):
        path = self.raw / self.fixture.entries[0]["relative_path"]
        path.write_bytes(path.read_bytes() + b"corrupt")
        self.failure()
        self.assertFalse(self.requests)

    def test_changed_original_receipt_fails_before_date_decoding(self):
        (self.raw / self.fixture.entries[0]["receipt_path"]).write_bytes(b"{}")
        self.failure()
        self.assertFalse(self.requests)

    def test_changed_captured_receipt_is_not_ignored(self):
        path = self.inventory_dir / "inputs/receipts" / (self.fixture.entries[0]["receipt_sha256"] + ".json")
        path.write_bytes(b"{}")
        self.failure()
        self.assertFalse(self.requests)

    def test_changed_report_and_journal_fail_without_output(self):
        (self.inventory_dir / "report.json").write_bytes(b"{}")
        self.failure("checksum")
        self.assertFalse(self.output.exists())

    def test_changed_journal_fails_before_rows(self):
        with (self.inventory_dir / "journal.jsonl").open("ab") as stream:
            stream.write(b"{}\n")
        self.failure("journal|Journal|chain")
        self.assertFalse(self.requests)

    def test_replaced_captured_manifest_fails_before_rows(self):
        (self.inventory_dir / "inputs/manifest.json").write_bytes(b"{}")
        self.failure("checksum")
        self.assertFalse(self.requests)

    def test_original_tree_and_inventory_output_paths_are_rejected_before_creation(self):
        for output in (self.raw / self.fixture.partition / "unsafe", self.inventory_dir / "unsafe"):
            self.output = output
            with self.subTest(output=output.name), self.assertRaises(ContractError):
                self.run_profile()
            self.assertFalse(output.exists())

    def test_late_terminal_write_failure_has_no_passed_report(self):
        original = dates.RunJournal.append
        def fail_completed(journal, event, **details):
            if event == "build_completed":
                raise OSError("terminal failure with DO_NOT_EXPORT_PAYLOAD")
            return original(journal, event, **details)
        with patch.object(dates.RunJournal, "append", new=fail_completed):
            self.failure()

    def test_interrupt_retains_partial_aggregate_accounting(self):
        original = self.fake_file.iter_batches
        def interrupted(file, **kwargs):
            yield from original(file, **kwargs)
            raise KeyboardInterrupt()
        with patch.object(self.fake_file, "iter_batches", new=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_profile()
        failed = parse_json((self.output / "failure.json").read_bytes())
        self.assertEqual(failed["rows_decoded"], 2)
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_interrupted")

    def test_footer_count_mismatch_fails(self):
        self.rows.append(deepcopy(self.rows[0]))
        self.failure()
        self.assertFalse(self.requests)

    def test_unexpected_projection_returned_by_backend_fails_before_conversion(self):
        def unsafe(file, **kwargs):
            yield SimpleNamespace(num_rows=2, nbytes=128, schema=SimpleNamespace(names=["clinicalPhase"]),
                to_pylist=lambda: self.fail("Unapproved rows converted"))
        with patch.object(self.fake_file, "iter_batches", new=unsafe):
            self.failure()

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "Optional real-format ingestion dependency")
    def test_actual_parquet_projection_keeps_clinical_canaries_out(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        for entry in self.fixture.entries:
            path = self.raw / entry["relative_path"]
            pq.write_table(pa.Table.from_pylist(self.rows), path)
            receipt_path = self.raw / entry["receipt_path"]
            receipt = json.loads(receipt_path.read_text())
            receipt.update(bytes=path.stat().st_size, sha256=sha256_file(path))
            fixtures.write_json(receipt_path, receipt)
            entry.update(bytes=path.stat().st_size, sha256=sha256_file(path), receipt_sha256=sha256_file(receipt_path))
        self.fixture.listing_path.write_text("".join(hashlib.sha1((self.raw / entry["relative_path"]).read_bytes()).hexdigest()
            + "  ./" + self.fixture.publisher_prefix + Path(entry["relative_path"]).name + "\n" for entry in self.fixture.entries))
        self.fixture.refresh_publisher()
        self.fixture.arrow.return_value = pq
        self.date_arrow.return_value = pq
        self.inventory_dir = self.root / "real-parquet-inventory"
        self.qualify()
        original = pq.ParquetFile.iter_batches
        observed = []
        def checked(file, **kwargs):
            observed.append(tuple(kwargs["columns"]))
            self.assertEqual(set(kwargs["columns"]), set(dates.POLICY["columns"]))
            return original(file, **kwargs)
        with patch.object(pq.ParquetFile, "iter_batches", new=checked), \
                patch.object(pq, "read_table", side_effect=AssertionError("broad reader")):
            report = self.run_profile()
        self.assertEqual(report["rows_decoded"], 4)
        self.assertEqual(len(observed), 2)
        self.assertNotIn("DO_NOT_EXPORT", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
