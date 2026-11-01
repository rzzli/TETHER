"""Fictional fixed bundle fixtures; no original data, installs or network."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/science"))
import package_p09_release as p


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "data/cache")
        self.base = Path(self.temporary.name).resolve()
        assert self.base.is_relative_to((ROOT / "data/cache").resolve())
        self.addCleanup(self.temporary.cleanup)
        self.bundle = self.base / "bundle"
        self.bundle.mkdir()
        self.payloads = {"source/example.py": b"# Fictional source code may discuss D:\\private\\example and api_key=value.\n",
            "included-originals/invented.tsv": b"invented\tfixture\n", "config/neutral.json": b'{"fictional":true}\n'}
        files = {}
        for name, raw in self.payloads.items():
            target = self.bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            files[name] = dict(path=name, sha256=p.sha(raw), bytes=len(raw), role="invented_test_payload")
        self.protocol = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1", status="READY",
            actual_reconstruction_authorized=True, frozen_at_utc="2026-11-01T20:48:03.123456+00:00", files=files)
        self.readme = self.base / "outer.md"
        self.readme.write_text("# Invented release fixture\nUse relative artifact paths. https://example.invalid/source\n", encoding="utf-8")
        self.qualification = self.base / "public.json"
        self.qual = {**p.QUALIFICATION, "fictional_test_fixture": True, "gates": {"invented": "PASS"}}
        self.resign()
        self.output = self.base / "release.zip"

    def resign(self):
        raw = p._wire(self.protocol)
        (self.bundle / "protocol.json").write_bytes(raw)
        self.pin = p.sha(raw)
        self.qual["protocol_sha256"] = self.pin
        self.qualification.write_bytes(p._wire(self.qual))

    def run_package(self, output=None):
        return p.package(self.bundle, self.pin, self.readme, self.qualification, output or self.output)

    def partial(self):
        return self.output.with_name(self.output.name + ".partial")

    def test_exact_allowlist_roles_manifest_and_source_privacy_scope(self):
        (self.bundle / "unlisted-private-placeholder.txt").write_bytes(b"Fictional excluded marker")
        result = self.run_package()
        expected = {"artifact/" + key for key in self.payloads} | {"artifact/protocol.json", "README.md", "qualification.json", "RELEASE-MANIFEST.json"}
        self.assertEqual(result["archive_sha256"], p.sha(self.output.read_bytes()))
        self.assertEqual(result["status"], "PACKAGED_AND_READBACK_VERIFIED")
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), sorted(expected))
            manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
            self.assertEqual(set(manifest["files"]), expected - {"RELEASE-MANIFEST.json"})
            self.assertEqual(manifest["protocol_sha256"], self.pin)
            self.assertEqual(manifest["public_qualification_sha256"], p.sha(self.qualification.read_bytes()))
            self.assertFalse(manifest["publication_authorized"])
            for name, proof in manifest["files"].items():
                raw = archive.read(name)
                self.assertEqual((proof["sha256"], proof["bytes"]), (p.sha(raw), len(raw)))
                self.assertTrue(proof["role"])
        self.assertFalse(self.partial().exists())

    def test_repeated_archives_are_identical_and_timestamp_floors_to_two_seconds(self):
        first = self.run_package()
        other = self.base / "second.zip"
        second = self.run_package(other)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        with zipfile.ZipFile(other) as archive:
            self.assertTrue(all(member.date_time == (2026, 11, 1, 20, 48, 2) for member in archive.infolist()))
            self.assertTrue(all(member.compress_type == zipfile.ZIP_STORED for member in archive.infolist()))

    def test_protocol_hash_tamper_fails_before_payload_access(self):
        with (self.bundle / "protocol.json").open("ab") as stream:
            stream.write(b" ")
        original = p._source_path
        visited = []
        def source(root, relative):
            visited.append(relative)
            return original(root, relative)
        with patch.object(p, "_source_path", side_effect=source), self.assertRaises(ValueError): self.run_package()
        self.assertEqual(visited, ["protocol.json"])
        self.assertFalse(self.output.exists())

    def test_draft_boolean_schema_and_nonboolean_authorization_fail(self):
        for key, value in (("schema_version", True), ("status", "DRAFT_ROOT_AUTHORIZATION_PENDING"), ("actual_reconstruction_authorized", 1), ("actual_reconstruction_authorized", False)):
            with self.subTest(key=key, value=value):
                saved = deepcopy(self.protocol)
                self.protocol[key] = value
                self.resign()
                with self.assertRaises(ValueError): self.run_package()
                self.protocol = saved
                self.resign()

    def test_frozen_timestamp_must_be_explicit_utc_and_zip_representable(self):
        for value in (None, "2026-11-01", "2026-11-01T20:48:03", "2026-11-01T20:48:03+01:00", "1979-01-01T00:00:00Z"):
            self.protocol["frozen_at_utc"] = value
            self.resign()
            with self.assertRaises(ValueError): self.run_package()

    def test_changed_missing_and_false_size_members_fail(self):
        name = "config/neutral.json"
        target = self.bundle / name
        target.write_bytes(b'{"fictional":"changed"}\n')
        with self.assertRaises(ValueError): self.run_package()
        target.unlink()
        with self.assertRaises(FileNotFoundError): self.run_package()
        target.write_bytes(self.payloads[name])
        self.protocol["files"][name]["bytes"] = True
        self.resign()
        with self.assertRaises(ValueError): self.run_package()
        self.assertFalse(self.partial().exists())

    def test_unsafe_case_aliased_and_reserved_members_fail(self):
        for name in ("../outside", "/absolute", "C:/absolute", "path\\alias", "a//b", "CON.txt", "trailing.", "protocol.json"):
            with self.subTest(name=name):
                saved = deepcopy(self.protocol)
                self.protocol["files"][name] = dict(path=name, sha256="a" * 64, bytes=1, role="fictional")
                self.resign()
                with self.assertRaises(ValueError): self.run_package()
                self.protocol = saved
        self.protocol["files"]["SOURCE/example.py"] = {**self.protocol["files"]["source/example.py"], "path": "SOURCE/example.py"}
        self.resign()
        with self.assertRaises(ValueError): self.run_package()

    def test_duplicate_json_keys_and_descriptor_extra_fields_fail(self):
        raw = p._wire(self.protocol).rstrip()[:-1] + b',"schema_version":1}\n'
        (self.bundle / "protocol.json").write_bytes(raw)
        self.pin = p.sha(raw)
        with self.assertRaises(ValueError): self.run_package()
        self.protocol["files"]["config/neutral.json"]["unapproved"] = "field"
        self.resign()
        with self.assertRaises(ValueError): self.run_package()

    def test_public_qualification_mandatory_fields_and_types_are_strict(self):
        for key, value in (("schema_version", True), ("role", "agent_evidence"), ("agent_visible", 0), ("publication_authorized", 0),
                ("scientific_validation", "established"), ("study_independence", "established"), ("owner_declarations", "completed"),
                ("status", "PASS"), ("protocol_sha256", "f" * 64)):
            with self.subTest(key=key):
                changed = {**self.qual, key: value}
                self.qualification.write_bytes(p._wire(changed))
                with self.assertRaises(ValueError): self.run_package()
        changed = dict(self.qual); del changed["publication_authorized"]
        self.qualification.write_bytes(p._wire(changed))
        with self.assertRaises(ValueError): self.run_package()

    def test_nonfinite_public_numbers_are_rejected_including_exponent_overflow(self):
        for token in (b"NaN", b"Infinity", b"1e999"):
            self.qualification.write_bytes(p._wire(self.qual).rstrip()[:-1] + b',"unapproved_number":' + token + b'}\n')
            with self.assertRaises(ValueError): self.run_package()

    def test_private_paths_and_credentials_in_only_public_outer_inputs_fail(self):
        for private in (r"D:\owner\private", "/home/owner/private", r"\\server\share\private", "https://example.invalid/?token=invented", "Authorization: Basic invented", "OPENAI_API_KEY=invented"):
            with self.subTest(value=private):
                self.qualification.write_bytes(p._wire({**self.qual, "unapproved_note": private}))
                with self.assertRaises(ValueError): self.run_package()
                self.qualification.write_bytes(p._wire(self.qual))
                self.readme.write_text("# Fictional\n" + private, encoding="utf-8")
                with self.assertRaises(ValueError): self.run_package()
                self.readme.write_text("# Fictional public documentation\n", encoding="utf-8")
        self.qualification.write_bytes(p._wire({**self.qual, "credentials": "invented"}))
        with self.assertRaises(ValueError): self.run_package()

    def test_existing_output_or_partial_never_replaced(self):
        self.output.write_bytes(b"Earlier artifact")
        with patch.object(p, "_read", side_effect=AssertionError("No input reads needed")), self.assertRaises(FileExistsError): self.run_package()
        self.assertEqual(self.output.read_bytes(), b"Earlier artifact")
        self.output.unlink()
        self.partial().write_bytes(b"Earlier failed staging")
        with self.assertRaises(FileExistsError): self.run_package()
        self.assertEqual(self.partial().read_bytes(), b"Earlier failed staging")

    def test_concurrent_destination_preserved_and_valid_partial_retained(self):
        def concurrent(source, target):
            Path(target).write_bytes(b"Concurrent existing artifact")
            raise FileExistsError("Concurrent reservation")
        with patch.object(p.os, "rename" if p.os.name == "nt" else "link", side_effect=concurrent), self.assertRaises(FileExistsError): self.run_package()
        self.assertEqual(self.output.read_bytes(), b"Concurrent existing artifact")
        with zipfile.ZipFile(self.partial()) as archive: self.assertIsNone(archive.testzip())

    def test_readback_failure_retains_readable_partial_without_final_or_success_output(self):
        stdout = io.StringIO()
        with patch.object(p, "_verify_zip", side_effect=OSError("Injected readback fault")), redirect_stdout(stdout), self.assertRaises(OSError):
            p.main(["--bundle-root", str(self.bundle), "--protocol-sha256", self.pin, "--readme", str(self.readme),
                "--qualification", str(self.qualification), "--output", str(self.output)])
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(self.output.exists())
        with zipfile.ZipFile(self.partial()) as archive: self.assertIsNone(archive.testzip())

    def test_write_failure_and_keyboard_interrupt_leave_inspectable_partial(self):
        original = p._write_member
        for error in (OSError("Injected write failure"), KeyboardInterrupt()):
            count = [0]
            def write(*args):
                count[0] += 1
                if count[0] == 2: raise error
                return original(*args)
            with patch.object(p, "_write_member", side_effect=write), self.assertRaises(type(error)): self.run_package()
            self.assertFalse(self.output.exists())
            with zipfile.ZipFile(self.partial()) as archive: self.assertEqual(len(archive.namelist()), 1)
            self.partial().unlink()

    def test_close_failure_never_publishes(self):
        original = zipfile.ZipFile.close
        def fail_after_close(archive):
            inject = archive.mode == "w" and archive.fp is not None
            original(archive)
            if inject: raise OSError("Injected close fault")
        with patch.object(zipfile.ZipFile, "close", fail_after_close), self.assertRaises(OSError): self.run_package()
        self.assertFalse(self.output.exists())
        with zipfile.ZipFile(self.partial()) as archive: self.assertIsNone(archive.testzip())

    def test_zip_readback_rejects_extra_duplicate_timestamp_and_trailing_bytes(self):
        self.run_package()
        with zipfile.ZipFile(self.output) as archive: entries = {name: archive.read(name) for name in archive.namelist()}
        timestamp = p._timestamp(self.protocol["frozen_at_utc"])
        for mutation in ("extra", "duplicate", "timestamp", "trailing"):
            path = self.base / (mutation + ".zip")
            with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as archive:
                warnings.simplefilter("ignore", UserWarning)
                for name in sorted(entries): p._write_member(archive, name, entries[name], timestamp if mutation != "timestamp" else (2026, 1, 1, 0, 0, 0))
                if mutation == "extra": p._write_member(archive, "unapproved.txt", b"Fictional", timestamp)
                if mutation == "duplicate": p._write_member(archive, "README.md", entries["README.md"], timestamp)
            if mutation == "trailing":
                with path.open("ab") as stream: stream.write(b"Unlisted trailing marker")
            with self.assertRaises((ValueError, zipfile.BadZipFile)): p._verify_zip(path, entries, timestamp)

    def test_output_must_be_in_existing_ignored_workspace_parent(self):
        with self.assertRaises(ValueError): self.run_package(ROOT / "tmp" / "outside-release.zip")
        with self.assertRaises(FileNotFoundError): self.run_package(self.base / "missing-parent" / "release.zip")
        with self.assertRaises(ValueError): self.run_package(self.base / "release.txt")

    def test_output_cannot_mutate_frozen_bundle_tree(self):
        before = {path.relative_to(self.bundle).as_posix(): path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()}
        with self.assertRaises(ValueError): self.run_package(self.bundle / "release.zip")
        after = {path.relative_to(self.bundle).as_posix(): path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
