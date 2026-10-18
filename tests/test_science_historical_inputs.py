from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import json
import builtins
from unittest.mock import patch

from asof.serde import ContractError, sha256_file
from tools.science.historical_inputs import ORIGIN, PROJECTIONS, availability, integrity_map, project, save_new, verify_manifest


class HistoricalInputTests(unittest.TestCase):
    def test_projection_discards_clinical_and_unknown_columns(self):
        row = {"id": "CHEMBLfixture", "name": "fixture", "maximumClinicalTrialPhase": 4,
            "hasBeenWithdrawn": True, "isApproved": True, "indications": ["outcome"],
            "clinicalTrials": ["future"], "unexpected": "future"}
        result = project(row, "molecule")
        self.assertEqual(result["id"], "CHEMBLfixture")
        for key in ("maximumClinicalTrialPhase", "hasBeenWithdrawn", "isApproved", "indications", "clinicalTrials", "unexpected"):
            self.assertNotIn(key, result)
        self.assertIsNone(result["parentId"])

    def test_only_preapproved_nonclinical_products(self):
        for product in ("knownDrugsAggregated", "indication", "associationByOverallDirect", "evidence"):
            with self.assertRaises(ContractError):
                project({}, product)

    def test_publisher_integrity_manifest_paths_and_conflicts(self):
        digest = "a" * 40
        self.assertEqual(integrity_map(digest + "  ./output/file.parquet"), {"output/file.parquet": digest})
        for payload in ("HTTP 200", digest + "  ../bad", digest + "  C:/bad", digest + "  \\bad",
                        digest + "  same\n" + "b" * 40 + "  same"):
            with self.assertRaises(ContractError):
                integrity_map(payload)

    def test_availability_is_release_day_bound_and_rejects_other_release(self):
        notice = {"post_stream": {"posts": [{"created_at": "2024-09-18T13:36:32.754Z", "cooked": "Released 24.09"}]}}
        self.assertEqual(availability(notice), "2024-09-19T00:00:00Z")
        future = deepcopy(notice); future["post_stream"]["posts"][0]["created_at"] = "2025-09-18T00:00:00Z"
        with self.assertRaises(ContractError):
            availability(future)
        with self.assertRaises(ContractError):
            availability({"post_stream": {"posts": []}})

    def test_archived_receipts_never_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            save_new(path, {"sha256": "original"})
            with self.assertRaises(FileExistsError):
                save_new(path, {"sha256": "replacement"})
            self.assertIn("original", path.read_text())

    def fixture_manifest(self, directory):
        root = Path(directory); source = root / "raw.json"; source.write_text("{}")
        receipt = root / "receipt.json"
        save_new(receipt, {"sha256": sha256_file(source), "source_url": "fixture"})
        parent = {"path": str(source), "sha256": sha256_file(source), "bytes": 2,
            "receipt_path": str(receipt), "receipt_sha256": sha256_file(receipt), "source_url": "fixture"}
        products = []
        for product in PROJECTIONS:
            path = root / (product + ".jsonl")
            path.write_text(json.dumps({"record": project({}, product), "source": {"sha256": parent["sha256"]}}) + "\n")
            schema = root / (product + "schema.json"); schema.write_text("[]")
            products.append({"product": product, "path": str(path), "sha256": sha256_file(path),
                "schema_path": str(schema), "schema_sha256": sha256_file(schema), "rows": 1,
                "approved_columns": list(PROJECTIONS[product])})
        manifest = {"release_id": "24.09", "origin_at": ORIGIN, "available_by": "2024-09-19T00:00:00Z",
            "availability_source": {"kind": "test_fixture", "available_by": "2024-09-19T00:00:00Z"},
            "future_fallback": False, "clinical_outcome_queries": 0, "metadata": [], "files": [parent], "products": products}
        path = root / "manifest.json"; save_new(path, manifest)
        return path, manifest

    def test_physical_tampering_and_future_dates_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            self.assertEqual(verify_manifest(path)["projected_rows"], 4)
            manifest["available_by"] = "2025-09-01T00:00:00Z"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ContractError):
                verify_manifest(path)
            manifest["available_by"] = "2024-09-19T00:00:00Z"; path.write_text(json.dumps(manifest))
            Path(manifest["files"][0]["path"]).write_text('{"future":1}')
            with self.assertRaises(ContractError):
                verify_manifest(path)

    def test_projection_cannot_admit_outcome_field_even_rehashed(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            product = manifest["products"][2]; projection = Path(product["path"])
            row = json.loads(projection.read_text()); row["record"]["maximumClinicalTrialPhase"] = 4
            projection.write_text(json.dumps(row) + "\n"); product["sha256"] = sha256_file(projection)
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ContractError):
                verify_manifest(path)

    def test_complete_ancestor_pins_and_core_without_pyarrow(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            expected = sha256_file(path)
            original_import = builtins.__import__
            def no_pyarrow(name, *args, **kwargs):
                if name.startswith("pyarrow"):
                    raise AssertionError("core verifier must not import pyarrow")
                return original_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=no_pyarrow):
                result = verify_manifest(path, expected_manifest_sha256=expected)
            self.assertEqual(result["manifest_sha256"], expected)
            self.assertEqual(result["manifest_final_sha256"], expected)
            # Manifest + one original + one receipt + four projections + four schemas.
            self.assertEqual(len(result["ancestor_pins"]), 11)
            self.assertEqual({p["role"] for p in result["ancestor_pins"]},
                {"historical_manifest", "historical_raw_data", "historical_receipt", "historical_projection", "historical_schema"})
            for pin in result["ancestor_pins"]:
                self.assertEqual(sha256_file(Path(pin["path"])), pin["sha256"])
                self.assertEqual(Path(pin["path"]).stat().st_size, pin["bytes"])

    def test_each_ancestor_byte_tamper_is_rejected(self):
        for kind in ("raw", "receipt", "projection", "schema", "manifest"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                path, manifest = self.fixture_manifest(directory)
                expected = sha256_file(path)
                target = {"raw": manifest["files"][0]["path"],
                    "receipt": manifest["files"][0]["receipt_path"],
                    "projection": manifest["products"][0]["path"],
                    "schema": manifest["products"][0]["schema_path"], "manifest": str(path)}[kind]
                with Path(target).open("ab") as stream:
                    stream.write(b" ")
                with self.assertRaises(ContractError):
                    verify_manifest(path, expected_manifest_sha256=expected)

    def test_changed_manifest_after_parse_is_rejected(self):
        from tools.science import historical_inputs as module
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            expected = sha256_file(path); original_parse = module.parse_json
            first = True
            def change_after_parse(payload):
                nonlocal first
                result = original_parse(payload)
                if first:
                    first = False
                    path.write_bytes(path.read_bytes() + b" ")
                return result
            with patch.object(module, "parse_json", side_effect=change_after_parse):
                with self.assertRaises(ContractError):
                    verify_manifest(path, expected_manifest_sha256=expected)

    def test_changed_raw_after_initial_read_is_rejected_at_closure(self):
        from tools.science import historical_inputs as module
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            original_parse = module.parse_json; calls = 0
            def change_after_parent_read(payload):
                nonlocal calls
                result = original_parse(payload); calls += 1
                if calls == 2: # Parsing the already-read raw parent's receipt.
                    Path(manifest["files"][0]["path"]).write_bytes(b"[]")
                return result
            with patch.object(module, "parse_json", side_effect=change_after_parent_read):
                with self.assertRaisesRegex(ContractError, "during verification"):
                    verify_manifest(path)

    def test_retained_official_notice_recomputes_available_by(self):
        from tools.science.historical_inputs import NOTICE
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            notice_path = Path(directory) / "notice.json"
            save_new(notice_path, {"post_stream": {"posts": [{"created_at": "2024-09-18T13:36:32.754Z", "cooked": "Released 24.09"}]}})
            receipt_path = Path(directory) / "notice-receipt.json"
            save_new(receipt_path, {"sha256": sha256_file(notice_path), "source_url": NOTICE})
            manifest["metadata"] = [{"path": str(notice_path), "bytes": notice_path.stat().st_size,
                "sha256": sha256_file(notice_path), "source_url": NOTICE,
                "receipt_path": str(receipt_path), "receipt_sha256": sha256_file(receipt_path)}]
            path.write_text(json.dumps(manifest))
            self.assertEqual(verify_manifest(path)["availability_basis"], "retained_official_release_notice")
            manifest["available_by"] = "2024-10-01T00:00:00Z"; path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ContractError, "availability differs"):
                verify_manifest(path)

    def test_absent_official_notice_has_no_implicit_availability_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture_manifest(directory)
            del manifest["availability_source"]
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ContractError, "retained official notice"):
                verify_manifest(path)


if __name__ == "__main__":
    unittest.main()
