"""Invented archive controls; no historical code is imported or executed."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import source_archive as archive


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest_path = self.root / "ARCHIVE.json"
        self.original = str(self.root / "original-repository")
        self.payload = b"raise RuntimeError('archived source must never execute')\n"
        self.source = self.root / "payload" / "source.py"
        self.source.parent.mkdir()
        self.source.write_bytes(self.payload)
        self.name = "experiments/example/source.py"
        self.pins = {self.name: hashlib.sha256(self.payload).hexdigest()}
        self.manifest = dict(schema_version=1, kind="sc04_executed_source_archive_v1",
                             original_repository_root=self.original,
                             files={self.name: dict(path=str(self.source), bytes=len(self.payload),
                                                    sha256=self.pins[self.name])})

    def write_manifest(self, raw=None):
        raw = json.dumps(self.manifest).encode() if raw is None else raw
        self.manifest_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def load(self, **changes):
        args = dict(path=self.manifest_path, sha=self.write_manifest(), code_pins=self.pins,
                    original_repository_root=self.original)
        args.update(changes)
        return archive.load_archive(**args)

    def test_exact_binding_returns_bytes_and_actual_archive_proofs(self):
        result = self.load()
        self.assertEqual(result.read(self.name), self.payload)
        self.assertEqual(result.proof(self.name), self.manifest["files"][self.name])
        self.assertEqual(result.manifest_proof, dict(path=str(self.manifest_path),
                         bytes=self.manifest_path.stat().st_size, sha256=self.write_manifest()))
        self.assertEqual(result.logical_names, (self.name,))
        self.assertEqual(result.original_repository_root, self.original)

    def test_windows_ambiguous_components_are_rejected_portably(self):
        for name in ('source.py.', 'source.py ', 'CON.py', 'aux', 'COM1.log', 'LPT2'):
            with self.subTest(name=name), self.assertRaises(archive.SourceArchiveError):
                archive._absolute(str(self.source.parent / name))

    def test_trailing_dot_cannot_alias_two_logical_sources(self):
        alias = str(self.source) + '.'
        if os.name != 'nt':
            Path(alias).write_bytes(self.payload)
        second = 'experiments/example/other.py'
        self.pins[second] = self.pins[self.name]
        self.manifest['files'][second] = dict(self.manifest['files'][self.name], path=alias)
        with self.assertRaises(archive.SourceArchiveError):
            self.load()

    def test_external_anchor_and_original_root_are_required(self):
        for changes in ({"sha": "0" * 64}, {"original_repository_root": str(self.root / "other")},
                        {"sha": "not-a-hash"}):
            with self.subTest(changes=changes), self.assertRaises(archive.SourceArchiveError):
                self.load(**changes)

    def test_exact_top_level_and_nested_schemas(self):
        for where, key, value in ((self.manifest, "extra", None),
                                  (self.manifest["files"][self.name], "logical_name", self.name)):
            where[key] = value
            with self.subTest(key=key), self.assertRaises(archive.SourceArchiveError): self.load()
            del where[key]
        for key in list(self.manifest):
            saved = self.manifest.pop(key)
            with self.subTest(missing=key), self.assertRaises(archive.SourceArchiveError): self.load()
            self.manifest[key] = saved

    def test_missing_extra_and_substituted_source_pins(self):
        for pins in ({}, {**self.pins, "extra.py": "0" * 64}, {self.name: "0" * 64}):
            with self.subTest(pins=pins), self.assertRaises(archive.SourceArchiveError):
                self.load(code_pins=pins)
        self.manifest["files"] = {}
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_duplicate_json_keys_and_noninteger_schema_are_rejected(self):
        raw = json.dumps(self.manifest).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1').encode()
        sha = self.write_manifest(raw)
        with self.assertRaises(archive.SourceArchiveError):
            archive.load_archive(self.manifest_path, sha, self.pins, self.original)
        self.manifest["schema_version"] = True
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_unsafe_logical_paths_are_rejected(self):
        original = self.manifest["files"][self.name]
        for name in ("../source.py", "/source.py", "folder/../source.py", "folder/./source.py",
                     "folder//source.py", "folder\\source.py", "C:/source.py", "source.py/"):
            self.manifest["files"] = {name: original}
            with self.subTest(name=name), self.assertRaises(archive.SourceArchiveError):
                self.load(code_pins={name: self.pins[self.name]})

    def test_unsafe_physical_paths_and_cross_archive_files_are_rejected(self):
        proof = self.manifest["files"][self.name]
        for path in ("payload/source.py", str(self.root / "payload") + "/../payload/source.py",
                     "//host/share/source.py", str(self.root.parent / "outside.py"), str(self.manifest_path)):
            proof["path"] = path
            with self.subTest(path=path), self.assertRaises(archive.SourceArchiveError): self.load()

    def test_nonregular_payload_is_rejected(self):
        self.manifest["files"][self.name]["path"] = str(self.source.parent)
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_size_and_content_are_checked_at_load(self):
        self.manifest["files"][self.name]["bytes"] -= 1
        with self.assertRaises(archive.SourceArchiveError): self.load()
        self.manifest["files"][self.name]["bytes"] += 1
        self.source.write_bytes(b"x" * len(self.payload))
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_hard_linked_payload_is_rejected(self):
        alias = self.root / "alias.py"
        os.link(self.source, alias)
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_links_and_windows_reparse_points_are_rejected(self):
        original = Path.lstat
        for target, attribute in ((self.source, "link"), (self.source.parent, "reparse"),
                                  (self.manifest_path, "reparse")):
            def intercepted(path, *, follow_symlinks=True):
                info = original(path)
                if path == target:
                    class Changed:
                        st_mode = stat.S_IFLNK if attribute == "link" else info.st_mode
                        st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT if attribute == "reparse" else 0
                    return Changed()
                return info
            with self.subTest(target=target, attribute=attribute), patch.object(Path, "lstat", intercepted), \
                    self.assertRaises(archive.SourceArchiveError): self.load()

    def test_manifest_file_count_individual_and_total_bounds(self):
        for key, maximum in (("MAX_FILES", 0), ("MAX_MANIFEST_BYTES", 1),
                             ("MAX_FILE_BYTES", len(self.payload)-1), ("MAX_TOTAL_BYTES", len(self.payload)-1)):
            with self.subTest(bound=key), patch.object(archive, key, maximum), \
                    self.assertRaises(archive.SourceArchiveError): self.load()
        self.manifest["files"][self.name]["bytes"] = True
        with self.assertRaises(archive.SourceArchiveError): self.load()

    def test_mutated_or_removed_payload_cannot_fall_back_to_working_source(self):
        result = self.load()
        self.source.write_bytes(b"x" * len(self.payload))
        for method in (result.read, result.proof):
            with self.assertRaises(archive.SourceArchiveError): method(self.name)
        self.source.unlink()
        with self.assertRaises(FileNotFoundError): result.read(self.name)
        with self.assertRaises(archive.SourceArchiveError): result.read("unbound.py")

    def test_binding_and_returned_proofs_cannot_be_mutated(self):
        result = self.load()
        self.pins[self.name] = "0" * 64
        self.manifest["files"][self.name]["path"] = "elsewhere.py"
        result.proof(self.name)["sha256"] = "0" * 64
        result.manifest_proof["sha256"] = "0" * 64
        with self.assertRaises(TypeError): result._files[self.name]["sha256"] = "0" * 64
        self.assertEqual(result.read(self.name), self.payload)

    def test_manifest_and_source_path_spellings_have_actual_physical_proofs(self):
        self.manifest["files"][self.name]["path"] = self.source.as_posix()
        result = self.load(path=self.manifest_path.as_posix())
        self.assertEqual(result.proof(self.name)["path"], str(self.source))
        self.assertEqual(result.manifest_proof["path"], str(self.manifest_path))

    def test_changed_file_identity_during_open_is_rejected(self):
        real = os.fstat
        def changed(fd):
            info = real(fd)
            class Different:
                st_dev = info.st_dev
                st_ino = info.st_ino + 1
                st_size = info.st_size
                st_mtime_ns = info.st_mtime_ns
                st_ctime_ns = info.st_ctime_ns
            return Different()
        sha = self.write_manifest()
        with patch.object(os, "fstat", changed), self.assertRaises(archive.SourceArchiveError):
            archive.load_archive(self.manifest_path, sha, self.pins, self.original)

    def test_physical_aliases_are_rejected(self):
        self.manifest["files"]["second.py"] = dict(self.manifest["files"][self.name])
        self.pins["second.py"] = self.pins[self.name]
        with self.assertRaises(archive.SourceArchiveError): self.load()


if __name__ == "__main__":
    unittest.main()
