"""Fictional neutral-metadata import boundaries; no original-source fixtures."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.serde import ContractError
from asof.serde import fingerprint
from tools.data.build_tether_policy import (MetadataImport, add_record, checked_json,
                                          check_frame_case, raw_artifact, receipt_archive_path)


class PolicyImportTests(unittest.TestCase):
    def test_receipt_archive_path_cannot_redirect_to_other_project_metadata(self):
        expected = "manifests/receipt-archive/" + "a"*64 + ".json"
        self.assertEqual(receipt_archive_path(dict(receipt_path=expected, receipt_sha256="a"*64)), expected)
        for path in ("D:/project/private.json", "../private.json", "metadata/other.json", expected.upper()):
            with self.subTest(path=path), self.assertRaises(ContractError):
                receipt_archive_path(dict(receipt_path=path, receipt_sha256="a"*64))

    def test_external_metadata_is_denied_before_content_read(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            importer = MetadataImport(base / "output", base / "approved")
            with patch("tools.data.build_tether_policy.ROOT", base / "project"), \
                 patch("tools.data.build_tether_policy.checked_json") as reader, self.assertRaises(ContractError):
                importer.load(base / "outside" / "sensitive.json")
            reader.assert_not_called()

    def test_canonical_label_cannot_hide_changed_hypothesis_or_omitted_packet(self):
        availability = dict(first_public_at=None, release_public_at=None, record_public_at=None,
            annotation_public_at=None, retrieved_at="2026-01-01", basis="fixture", uncertainty="fictional",
            known_public_by="2026-01-01T00:00:00Z", evidence_ref="fixture")
        hypothesis = dict(target_id="T", indication_id="D", target_namespace_version="v1",
            indication_namespace_version="v1", intended_action="inhibit", modality="antibody", tissue=None)
        case = dict(schema_version=2, case_id="one", task="T6", origin="2026-01-01",
            origin_at="2026-01-01T00:00:00Z", hypothesis=dict(hypothesis, availability=availability),
            program=None, endpoint=None)
        row = dict(case_id="one", hypothesis_key=fingerprint(hypothesis), input_sources=1,
                   packets=[dict(path="nested/p1.json"), dict(path="nested/p2.json")])
        report = dict(origin_at_utc=case["origin_at"], snapshot_id="snapshot")
        snapshot = dict(schema_version=2, snapshot_id="snapshot:one", profile="contemporary_assessment",
            origin=case["origin"], origin_at=case["origin_at"], allow_reconstructed=False,
            sources=[{}], artifacts=copy.deepcopy(row["packets"]))
        check_frame_case(row, case, snapshot, report)
        changed_case = copy.deepcopy(case)
        changed_case["hypothesis"]["intended_action"] = "activate"
        with self.assertRaises(ContractError):
            check_frame_case(row, changed_case, snapshot, report)
        for change in ({"artifacts": snapshot["artifacts"][:1]}, {"sources": []},
                       {"snapshot_id": "snapshot:other"}, {"profile": "historical_benchmark"}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                check_frame_case(row, case, dict(snapshot, **change), report)

    def test_stale_metadata_pin_and_duplicate_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            path.write_bytes(b'{"schema_version":1}')
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(checked_json(path, pin)[0]["schema_version"], 1)
            path.write_bytes(b'{"schema_version":2}')
            with self.assertRaises(ContractError):
                checked_json(path, pin)
            path.write_bytes(b'{"id":1,"id":2}')
            with self.assertRaises(ContractError):
                checked_json(path)

    def test_identical_identity_cannot_silently_replace_conflicting_context(self):
        records = {}
        original = {"artifact_id": "fixed", "availability": {"known_public_by": None}}
        add_record(records, original)
        add_record(records, copy.deepcopy(original))
        changed = copy.deepcopy(original)
        changed["availability"]["known_public_by"] = "2026-11-01"
        with self.assertRaises(ContractError):
            add_record(records, changed)
        self.assertEqual(records["fixed"], original)

    def test_receipt_node_url_path_and_identity_must_agree(self):
        node = dict(dataset_id="fixture", release_id="r1", path="raw/f.csv", sha256="a"*64,
            source_url="https://example.invalid/exact", receipt_path="receipt/a.json", receipt_sha256="b"*64,
            availability={}, temporal_classification="contemporary_only", parents=[], computed_at=None)
        receipt = dict(status="completed", dataset_id="fixture", release_id="r1", relative_path="raw/f.csv",
            sha256="a"*64, url=node["source_url"], bytes=10, receipt_id="request-1")
        proof = dict(path="receipt-copy.json", sha256="b"*64)
        valid = raw_artifact(node, receipt, proof)
        self.assertEqual(valid["provenance"]["receipt"]["receipt_id"], "request-1")
        self.assertIn("No new queue-to-receipt", valid["scope"])
        self.assertEqual(raw_artifact(node, dict(receipt, relative_path="raw\\f.csv"), proof), valid)
        for field, bad in [("dataset_id", "other"), ("release_id", "r2"),
                           ("relative_path", "raw/else.csv"), ("url", "https://example.invalid/EXACT"),
                           ("sha256", "c"*64), ("receipt_id", None), ("bytes", True),
                           ("relative_path", "raw/../f.csv"), ("relative_path", "RAW/f.csv")]:
            with self.subTest(field=field), self.assertRaises(ContractError):
                raw_artifact(node, dict(receipt, **{field: bad}), proof)

    def test_generated_input_cannot_be_relabelled_as_raw_receipt(self):
        with self.assertRaises(ContractError):
            raw_artifact({"computed_at": "2026-01-01T00:00:00Z"}, {}, {})


if __name__ == "__main__":
    unittest.main()
