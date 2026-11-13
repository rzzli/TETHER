"""Fictional portable runs, including filesystem and semantic tampering controls."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine import bundle
from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import write_run
from tether_engine.bundle_files import _bounded, _windows_member_allowed, logical_parts, read_local
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, canonical, decode, parse_json, read_json
from tether_engine.workflow import run_workflow


FIXTURE = Path(__file__).resolve().parents[1] / "src" / "tether_engine" / "demo" / "v2"


class CanonicalizationTests(unittest.TestCase):
    def test_invented_canonical_vectors(self):
        vectors = read_json(Path(__file__).parent / "fixtures" / "portable_bundle_canonical.json")["vectors"]
        self.assertGreaterEqual(len(vectors), 4)
        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                payload = canonical(vector["input"])
                self.assertEqual(payload.decode("utf-8"), vector["canonical_json"])
                self.assertEqual(payload.hex(), vector["utf8_hex"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), vector["sha256"])

    def test_native_receipt_separator_is_portable_without_rewriting_bytes(self):
        self.assertEqual(bundle._receipt_relative(r"raw\provider\source.parquet"), "raw/provider/source.parquet")
        for path in (r"E:\raw\source.parquet", r"raw\..\source.parquet", r"\\host\share\source.parquet"):
            with self.subTest(path=path), self.assertRaises(ContractError):
                bundle._receipt_relative(path)


class PortableBundleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.source = self.root / "native source"
        self.run = self.root / "native run"
        self.output = self.root / "new bundle"
        shutil.copytree(FIXTURE, self.source)

    def produce_run(self):
        case = decode(Case, read_json(self.source / "case.json"))
        store = load_snapshot(self.source / "snapshot.json", case)
        scorer = decode(ScorerArtifact, read_json(self.source / "scorer.json"))
        self.digest = write_run(self.run, run_workflow(case, store, ExtractiveBackend(), scorer), store, scorer)

    def export(self, **kwargs):
        if not self.run.exists():
            self.produce_run()
        return bundle.export_bundle(self.run, self.output, source_roots=[self.source],
                                    receipt_sha256=self.digest, **kwargs)

    def edit(self, name, change):
        manifest_path = self.output / "bundle.json"
        manifest = read_json(manifest_path)
        item = manifest["objects"][name]
        value = read_json(self.output / bundle._cas(item["sha256"]))
        change(value)
        payload = canonical(value)
        sha = hashlib.sha256(payload).hexdigest()
        (self.output / bundle._cas(sha)).write_bytes(payload)
        manifest["objects"][name] = {"sha256": sha, "bytes": len(payload)}
        manifest_path.write_bytes(canonical(manifest))

    def test_move_with_original_paths_unavailable(self):
        result = self.export()
        self.source.rename(self.root / "originals-disabled")
        self.run.rename(self.root / "run-disabled")
        moved = self.root / "移転 données β"
        self.output.rename(moved)
        checked = bundle.verify_bundle(moved, result["manifest_sha256"])
        self.assertEqual(checked["byte_integrity"], "verified")
        self.assertEqual(checked["source_inclusive_consistency"], "verified")
        self.assertEqual(checked["external_anchor"], "matched")
        self.assertEqual(checked["exact_producer_replay"], "not_performed_portable_export")
        self.assertEqual(checked["external_authenticity"], "not_established")
        for file in (moved / "objects" / "sha256").iterdir():
            self.assertNotIn(str(self.root).encode(), file.read_bytes())
        with self.assertRaisesRegex(ContractError, "anchor mismatch"):
            bundle.inspect_bundle(moved, "0" * 64)

    def test_omitted_originals_are_explicit(self):
        self.export(include_originals=False)
        checked = bundle.verify_bundle(self.output)
        self.assertEqual(checked["source_inclusive_consistency"], "unavailable_raw_originals_omitted")
        self.assertEqual(checked["supported_derivation_replay"], "unavailable_raw_originals_omitted")

    def test_portable_snapshot_preserves_producer_presentation_order(self):
        from tether_engine.serde import write_json
        path = self.source / "snapshot.json"
        snapshot = read_json(path)
        snapshot["coverage"].update(interpretation_scope="resource_annotation_only",
            hypothesis_qualification={"z_field": {"value": "before"}, "a_field": {"value": "after"}})
        write_json(path, snapshot)
        self.export()
        self.assertEqual(bundle.verify_bundle(self.output)["source_inclusive_consistency"], "verified")

    def test_bytes_only_is_independent_of_semantic_failure(self):
        self.export()
        self.edit("run.json", lambda run: run.update(calls=42))
        with self.assertRaisesRegex(ContractError, "accounting"):
            bundle.verify_bundle(self.output)
        checked = bundle.verify_bundle(self.output, replay=False)
        self.assertEqual(checked["byte_integrity"], "verified")
        self.assertEqual(checked["source_inclusive_consistency"], "not_checked_bytes_only")

    def test_unknown_policy_preserves_byte_check(self):
        self.export()
        path = self.output / "bundle.json"
        value = read_json(path)
        value["admission_policy"] = "tether.future_policy"
        value["producer"]["code"]["changed_comment.py"] = "1" * 64
        path.write_bytes(canonical(value))
        checked = bundle.verify_bundle(self.output)
        self.assertEqual(checked["source_inclusive_consistency"], "unavailable_unknown_policy")
        self.assertEqual(checked["byte_integrity"], "verified")

    def test_unsafe_paths_and_malformed_manifests(self):
        self.export()
        path = self.output / "bundle.json"
        initial = path.read_bytes()
        for value in (b'[]', b'{"format":1,"format":2}', b'{"x":1e999}'):
            with self.subTest(value=value):
                path.write_bytes(value)
                with self.assertRaises(ContractError):
                    bundle.inspect_bundle(self.output)
        for unsafe in ("../x", "lineage/NUL.txt", "packets/COM¹", "packets/a:stream", "packets/a\\b",
                       "packets/a/./b", "packets/a /b", "packets/a\ud800", "packets/e\u0301"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ContractError):
                logical_parts(unsafe)
        value = parse_json(initial)
        value["objects"]["PACKETS/../evidence.json"] = {"sha256": "0" * 64, "bytes": 1}
        path.write_bytes(canonical(value))
        with self.assertRaises(ContractError):
            bundle.verify_bundle(self.output)

    def test_corrupt_member_fails_even_when_replay_is_disabled(self):
        self.export()
        manifest = read_json(self.output / "bundle.json")
        object_path = self.output / bundle._cas(manifest["objects"]["dossier.md"]["sha256"])
        value = object_path.read_bytes()
        object_path.write_bytes(b"!" + value[1:])
        self.assertEqual(bundle.inspect_bundle(self.output)["byte_integrity"], "not_checked")
        with self.assertRaisesRegex(ContractError, "object integrity failure"):
            bundle.verify_bundle(self.output, replay=False)

    def test_no_follow_rejects_hardlinks_and_directory_aliases(self):
        self.export()
        manifest = self.output / "bundle.json"
        alias = self.root / "manifest-hardlink"
        try:
            os.link(manifest, alias)
        except PermissionError:
            # Windows app-container policies can block creation of the control.
            # Exercise the same fail-closed identity check without that capability.
            linked_info = SimpleNamespace(st_mode=manifest.stat().st_mode, st_nlink=2)
            with self.assertRaisesRegex(ContractError, "single-link"):
                _bounded(None, linked_info, 1024)
        else:
            with self.assertRaises(ContractError):
                bundle.inspect_bundle(self.output)
            alias.unlink()
        linked = self.root / "linked-bundle"
        if os.name == "nt":
            # Both paths are fixed names in the isolated temporary directory.
            outcome = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(linked), str(self.output)],
                                     capture_output=True, check=False)
            if outcome.returncode:
                self.assertFalse(linked.exists(), outcome.stderr.decode(errors="replace"))
                self.assertFalse(_windows_member_allowed(0x410, True, 1, 0, 1024))
                return
        else:
            linked.symlink_to(self.output, target_is_directory=True)
        try:
            with self.assertRaises(ContractError):
                bundle.verify_bundle(linked)
        finally:
            if os.name == "nt":
                linked.rmdir()
            else:
                linked.unlink()

    def test_replacing_regular_file_before_open_is_rejected(self):
        path = self.root / "readme.txt"
        path.write_bytes(b"wanted")
        if os.name == "nt":
            with self.assertRaises(ContractError):
                read_local(path, 5)
        else:
            original = os.open
            alternate = self.root / "alternate"
            alternate.write_bytes(b"forged")

            def swap(member, *args, **kwargs):
                if member == path.name:
                    alternate.replace(path)
                return original(member, *args, **kwargs)

            with patch.object(os, "open", swap), patch.object(os, "supports_dir_fd", {swap}):
                with self.assertRaisesRegex(ContractError, "changed before open"):
                    read_local(path, 10)

    def test_preflight_failures_leave_originals_unchanged(self):
        self.produce_run()
        before = (self.run / "receipt.json").read_bytes()
        with self.assertRaisesRegex(ContractError, "authorization"):
            bundle.export_bundle(self.run, self.output, source_roots=[self.run])
        self.assertFalse(self.output.exists())
        self.export()
        with self.assertRaisesRegex(ContractError, "fresh directory"):
            self.export()
        self.assertEqual((self.run / "receipt.json").read_bytes(), before)

    def test_original_size_limits_are_checked_before_copy(self):
        with patch.object(bundle, "TOTAL_LIMIT", 1):
            with self.assertRaisesRegex(ContractError, "byte limit"):
                self.export()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
