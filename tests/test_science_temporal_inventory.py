"""Evaluator-only technical inventory controls; fixtures contain no real outcomes."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, parse_json, sha256_file
from tools.science import temporal_inventory as inventory


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True).encode())


class FakeType:
    def __init__(self, name, children=()):
        self.name, self.children, self.num_fields = name, children, len(children)

    def __str__(self):
        return self.name

    def field(self, number):
        return self.children[number]


def fake_field(name, kind="string", nullable=True, children=()):
    return SimpleNamespace(name=name, nullable=nullable, type=FakeType(kind, children))


class FakeParquet:
    def __init__(self, stream, **kwargs):
        self.schema_arrow = [fake_field("id"), fake_field("context", "struct", children=(
            fake_field("date", "date32[day]", False),))]
        self.metadata = SimpleNamespace(num_rows=7)
        self.num_row_groups = 2

    def iter_batches(self, *args, **kwargs):
        raise AssertionError("Individual rows must not be read")

    read_row_group = iter_batches


class TemporalInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.raw = self.root / "data"
        self.raw.mkdir()
        self.partition = "raw/open_targets_platform/25.09/output/evidence/sourceId=chembl"
        self.publisher_prefix = "output/evidence/sourceId=chembl/"
        self.base_url = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/"
        self.entries, queue = [], []
        for i in range(2):
            name = f"part-{i:05d}.parquet"
            relative = self.partition + "/" + name
            path = self.raw / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"PAR1fictional" + bytes([i]) + b"PAR1")
            receipt_id = f"fixture-{i}"
            receipt_relative = "manifests/receipts/" + receipt_id + ".json"
            source_url = self.base_url + self.publisher_prefix + name
            receipt = {"receipt_id": receipt_id, "dataset_id": "ot_evidence", "release_id": "25.09",
                       "relative_path": relative.replace("/", "\\"), "url": source_url,
                       "status": "completed", "bytes": path.stat().st_size, "sha256": sha256_file(path),
                       "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                       "publisher_hash_verified": False, "format_check": "PAR1_header_and_footer_only",
                       "parse_status": "not_run", "scientific_validation": "not_run"}
            write_json(self.raw / receipt_relative, receipt)
            self.entries.append({"relative_path": relative, "receipt_id": receipt_id,
                                 "receipt_path": receipt_relative,
                                 "receipt_sha256": sha256_file(self.raw / receipt_relative),
                                 "bytes": path.stat().st_size, "sha256": sha256_file(path)})
            queue.append({"receipt_id": receipt_id, "dataset_id": "ot_evidence", "release_id": "25.09",
                          "relative_path": relative.replace("/", "\\"), "url": source_url,
                          "expected_bytes": None, "planning_upper_bytes": 999999999,
                          "expected_sha256": None, "format": "parquet", "required_header": None})
        self.queue_path = self.root / "queue.json"
        write_json(self.queue_path, {"batch_id": "fixture", "profile_note": "fictional", "files": queue})
        self.listing_path = self.root / "release_data_integrity"
        self.listing_path.write_text("".join(hashlib.sha1((self.raw / row["relative_path"]).read_bytes()).hexdigest()
             + "  ./" + self.publisher_prefix + Path(row["relative_path"]).name + "\n" for row in self.entries)
             + "0" * 40 + "  ./excluded/evidence/sourceId=chembl/unselected.parquet\n", encoding="utf-8")
        self.checksum_path = self.root / "release_data_integrity.sha1"
        self.checksum_path.write_text(hashlib.sha1(self.listing_path.read_bytes()).hexdigest()
                                      + "  release_data_integrity\n", encoding="utf-8")
        self.manifest = {"schema_version": 1, "kind": "opentargets_evaluator_partition_inventory",
                         "role": "evaluation_only", "agent_visible": False,
                         "dataset_id": "ot_evidence", "release_id": "25.09",
                         "approved_roots": [str(self.root)], "raw_root": str(self.raw),
                         "partition": self.partition,
                         "queue": {"path": str(self.queue_path), "sha256": sha256_file(self.queue_path)},
                         "publisher_listing": self.publisher_ref(self.listing_path),
                         "publisher_listing_checksum": self.publisher_ref(self.checksum_path),
                         "files": self.entries}
        self.manifest_path = self.root / "manifest.json"
        self.output = self.root / "inspection"
        self.arrow = self.enterContext(patch.object(inventory, "arrow", return_value=SimpleNamespace(ParquetFile=FakeParquet)))

    def publisher_ref(self, path):
        receipt_path = path.with_name(path.name + ".receipt.json")
        write_json(receipt_path, {"source_id": path.name, "url": self.base_url + path.name,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "role": "evaluation_only",
            "http_status": 200, "final_url": self.base_url + path.name, "status": "retrieved_unreviewed",
            "bytes": path.stat().st_size, "sha256": sha256_file(path), "content_type": None})
        return {"path": str(path), "sha256": sha256_file(path), "receipt_path": str(receipt_path),
                "receipt_sha256": sha256_file(receipt_path)}

    def refresh_publisher(self):
        self.checksum_path.write_text(hashlib.sha1(self.listing_path.read_bytes()).hexdigest()
                                      + "  release_data_integrity\n", encoding="utf-8")
        self.manifest["publisher_listing"] = self.publisher_ref(self.listing_path)
        self.manifest["publisher_listing_checksum"] = self.publisher_ref(self.checksum_path)

    def run_inventory(self, expected=None):
        write_json(self.manifest_path, self.manifest)
        return inventory.inspect_partition(self.manifest_path, expected or sha256_file(self.manifest_path), self.output)

    def failure(self, pattern):
        with self.assertRaisesRegex((ContractError, OSError), pattern):
            self.run_inventory()
        report = parse_json((self.output / "failure.json").read_bytes())
        self.assertEqual(report["status"], "technical_inventory_failed")
        self.assertFalse(report["agent_visible"])
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_failed")
        self.assertFalse((self.output / "report.json").exists())

    def test_exact_sets_footer_types_and_unknown_science_with_no_payload_reads(self):
        originals = {p: p.read_bytes() for p in self.raw.rglob("*") if p.is_file()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
                patch("tools.science.historical_inputs.collect", side_effect=AssertionError("collector")), \
                patch("subprocess.run", side_effect=AssertionError("subprocess")):
            report = self.run_inventory()
        self.assertEqual(report["status"], "technical_inventory_passed")
        self.assertEqual(report["file_count"], 2)
        self.assertEqual(report["footer_rows"], 14)
        self.assertEqual(report["row_payloads_decoded"], 0)
        self.assertEqual(report["scientific_eligibility"], "unassessed")
        self.assertEqual(report["historical_availability"], "unverified")
        self.assertFalse(report["labels_qualified"])
        self.assertEqual(report["schema_consistency"], "uniform")
        fields = report["schemas"][0]["fields"]
        self.assertEqual(fields[1]["children"][0]["type"], "date32[day]")
        self.assertFalse(fields[1]["children"][0]["nullable"])
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        for entry in self.entries:
            archived = self.output / "inputs/receipts" / (entry["receipt_sha256"] + ".json")
            self.assertEqual(archived.read_bytes(), (self.raw / entry["receipt_path"]).read_bytes())
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_completed")

    def test_unpinned_manifest_cannot_authorize_output_creation(self):
        with self.assertRaisesRegex(ContractError, "checksum mismatch"):
            self.run_inventory("0" * 64)
        self.assertFalse(self.output.exists())
        self.arrow.assert_not_called()

    def test_existing_output_rejected_without_touching_it(self):
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            self.run_inventory()
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_unsafe_output_is_rejected_before_any_original_tree_mutation(self):
        self.output = self.raw / self.partition / "unsafe-inspection"
        before = set((self.raw / self.partition).iterdir())
        with self.assertRaisesRegex(ContractError, "original source partition"):
            self.run_inventory()
        self.assertFalse(self.output.exists())
        self.assertEqual(set((self.raw / self.partition).iterdir()), before)

    def test_unapproved_output_is_rejected_before_reservation(self):
        with tempfile.TemporaryDirectory() as outside:
            self.output = Path(outside) / "unapproved"
            with self.assertRaisesRegex(ContractError, "approved root"):
                self.run_inventory()
            self.assertFalse(self.output.exists())

    def test_failed_terminal_journal_never_publishes_a_passed_report(self):
        original = inventory.RunJournal.append
        def fail_completed(journal, event, **details):
            if event == "build_completed":
                raise OSError("injected terminal journal failure")
            return original(journal, event, **details)
        with patch.object(inventory.RunJournal, "append", new=fail_completed):
            self.failure("injected terminal journal")

    def test_concurrent_output_reservation_has_one_winner(self):
        write_json(self.manifest_path, self.manifest)
        expected = sha256_file(self.manifest_path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(inventory.inspect_partition, self.manifest_path, expected, self.output)
                       for _ in range(2)]
            successes, rejected = [], []
            for future in futures:
                try:
                    successes.append(future.result())
                except FileExistsError as error:
                    rejected.append(error)
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(rejected), 1)
        self.assertFalse((self.output / "failure.json").exists())
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_completed")

    def test_evaluator_role_cannot_be_promoted(self):
        self.manifest["agent_visible"] = True
        with self.assertRaisesRegex(ContractError, "evaluator-only"):
            self.run_inventory()
        self.assertFalse(self.output.exists())
        self.arrow.assert_not_called()

    def test_missing_manifest_file_is_not_silently_dropped(self):
        self.manifest["files"].pop()
        self.failure("membership")

    def test_unexpected_disk_and_partial_files_are_explicit(self):
        (self.raw / self.partition / "extra.partial").write_bytes(b"partial")
        self.failure("membership")

    def test_missing_raw_file_leaves_membership_failure(self):
        (self.raw / self.entries[0]["relative_path"]).unlink()
        self.failure("membership")

    def test_duplicate_manifest_and_queue_identities_fail(self):
        self.manifest["files"].append(deepcopy(self.entries[0]))
        self.failure("Duplicate")

    def test_queue_release_mismatch_cannot_use_receipt_to_override(self):
        queue = json.loads(self.queue_path.read_text())
        queue["files"][0]["release_id"] = "26.01"
        write_json(self.queue_path, queue)
        self.manifest["queue"]["sha256"] = sha256_file(self.queue_path)
        self.failure("Queue identity")

    def test_planning_upper_bound_is_not_an_actual_size(self):
        self.entries[0]["bytes"] = 999999999
        self.failure("Receipt.*size|size.*receipt")

    def test_receipt_mutation_and_raw_mutation_are_rejected(self):
        (self.raw / self.entries[0]["receipt_path"]).write_bytes(b"{}")
        self.failure("checksum")

    def test_same_size_raw_corruption_is_rejected(self):
        path = self.raw / self.entries[0]["relative_path"]
        payload = path.read_bytes()
        path.write_bytes(payload[:-5] + b"X" + payload[-4:])
        self.failure("SHA-256")

    def test_publisher_checksum_disagrees_even_when_transport_hash_is_resealed(self):
        lines = self.listing_path.read_text().splitlines()
        lines[0] = "f" * 40 + lines[0][40:]
        self.listing_path.write_text("\n".join(lines) + "\n")
        self.refresh_publisher()
        self.failure("SHA-1")

    def test_listing_parent_checksum_is_required(self):
        self.checksum_path.write_text("f" * 40 + "  release_data_integrity\n")
        self.manifest["publisher_listing_checksum"] = self.publisher_ref(self.checksum_path)
        self.failure("Publisher listing SHA-1")

    def test_publisher_duplicate_paths_are_rejected(self):
        self.listing_path.write_text(self.listing_path.read_text() + self.listing_path.read_text().splitlines()[0] + "\n")
        self.refresh_publisher()
        self.failure("Duplicate publisher")

    def test_receipt_size_limit_is_checked_before_parsing(self):
        with patch.object(inventory, "MAX_RECEIPT_BYTES", 8):
            self.failure("size limit")

    def test_path_escape_fails_before_data_open(self):
        self.entries[0]["receipt_path"] = "../outside.json"
        self.failure("Unsafe|relative|escapes")

    def test_unapproved_metadata_path_is_rejected(self):
        self.manifest["approved_roots"] = [str(self.raw)]
        with self.assertRaisesRegex(ContractError, "approved root"):
            self.run_inventory()
        self.assertFalse(self.output.exists())

    def test_heterogeneous_schemas_are_reported_without_dropping_a_file(self):
        calls = 0
        def schema(stream, **kwargs):
            nonlocal calls
            calls += 1
            value = FakeParquet(stream)
            if calls == 2:
                value.schema_arrow[0] = fake_field("id", "int64")
            return value
        self.arrow.return_value = SimpleNamespace(ParquetFile=schema)
        report = self.run_inventory()
        self.assertEqual(report["schema_consistency"], "heterogeneous")
        self.assertEqual(len(report["schemas"]), 2)
        self.assertEqual(report["file_count"], 2)
        self.assertEqual(report["schema_compatibility"], "unassessed")

    def test_footer_failure_retains_completed_progress(self):
        calls = 0
        def corrupt(stream, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("bad parquet footer")
            return FakeParquet(stream)
        self.arrow.return_value = SimpleNamespace(ParquetFile=corrupt)
        self.failure("bad parquet footer")
        report = parse_json((self.output / "failure.json").read_bytes())
        self.assertEqual(report["verified_files"], 1)

    def test_receipt_change_during_footer_read_prevents_finalization(self):
        def mutate(stream, **kwargs):
            value = FakeParquet(stream)
            (self.raw / self.entries[0]["receipt_path"]).write_bytes(b"changed")
            return value
        self.arrow.return_value = SimpleNamespace(ParquetFile=mutate)
        self.failure("changed")

    def test_raw_identity_change_between_hash_and_footer_is_rejected(self):
        def mutate(stream, **kwargs):
            value = FakeParquet(stream)
            with Path(stream.name).open("ab") as writer:
                writer.write(b"changed")
            return value
        self.arrow.return_value = SimpleNamespace(ParquetFile=mutate)
        self.failure("changed during hash/footer")

    def test_interrupt_retains_terminal_journal_without_retrying(self):
        self.arrow.return_value = SimpleNamespace(ParquetFile=unittest.mock.Mock(side_effect=KeyboardInterrupt()))
        with self.assertRaises(KeyboardInterrupt):
            self.run_inventory()
        self.assertEqual(read_chain(self.output / "journal.jsonl")[-1]["event"], "build_interrupted")
        self.assertTrue((self.output / "failure.json").exists())

    def test_publication_failure_preserves_journal_and_does_not_publish_success(self):
        original = inventory.publish_bytes
        def fail_report(path, payload, **kwargs):
            if Path(path).name == "report.json":
                raise OSError("injected publication failure")
            return original(path, payload, **kwargs)
        with patch.object(inventory, "publish_bytes", side_effect=fail_report):
            self.failure("injected publication")

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "install the ingest extra for source-audit tests")
    def test_actual_parquet_footer_nested_types_without_row_readers(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        for entry in self.entries:
            path = self.raw / entry["relative_path"]
            schema = pa.schema([pa.field("id", pa.string(), nullable=False),
                                pa.field("nested", pa.list_(pa.struct([pa.field("year", pa.int32())])))])
            pq.write_table(pa.Table.from_pylist([{"id": "fixture", "nested": [{"year": 2020}]}], schema=schema), path)
            receipt_path = self.raw / entry["receipt_path"]
            receipt = json.loads(receipt_path.read_text())
            receipt.update(bytes=path.stat().st_size, sha256=sha256_file(path))
            write_json(receipt_path, receipt)
            entry.update(bytes=path.stat().st_size, sha256=sha256_file(path), receipt_sha256=sha256_file(receipt_path))
        self.listing_path.write_text("".join(hashlib.sha1((self.raw / row["relative_path"]).read_bytes()).hexdigest()
            + "  ./" + self.publisher_prefix + Path(row["relative_path"]).name + "\n" for row in self.entries))
        self.refresh_publisher()
        self.arrow.return_value = pq
        with patch.object(pq.ParquetFile, "iter_batches", side_effect=AssertionError("rows")), \
                patch.object(pq.ParquetFile, "read_row_group", side_effect=AssertionError("rows")), \
                patch.object(pq, "read_table", side_effect=AssertionError("rows")):
            report = self.run_inventory()
        self.assertEqual(report["footer_rows"], 2)
        self.assertFalse(report["schemas"][0]["fields"][0]["nullable"])
        self.assertEqual(report["schemas"][0]["fields"][1]["children"][0]["children"][0]["name"], "year")


if __name__ == "__main__":
    unittest.main()
