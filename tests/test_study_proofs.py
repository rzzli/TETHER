"""Static package/data proof regressions, without executing any archived code."""

import hashlib
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, encode
from tether_engine.study import proofs
from tether_engine.study.stable_read import hash_file, read_file


class StudyProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "__init__.py").write_text(
            "raise RuntimeError('must never execute')\n"
        )
        (self.root / "template.json").write_bytes(b'{"prompt":"source only"}\r\n')
        self.resources = {"template_v1": "template.json"}
        self.required = ("template_v1",)
        self.package = patch.object(proofs, "_package_root", return_value=self.root)
        self.package.start()
        self.addCleanup(self.package.stop)

    def capture(self):
        return proofs.capture_package_proof(self.resources, self.required)

    def test_file_proof_exact_original_bytes_and_deep_immutability(self):
        path = self.root / "template.json"
        actual = proofs.capture_file(path, "data/template.json")
        self.assertEqual(
            actual["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
        )
        self.assertEqual(actual["bytes"], path.stat().st_size)
        proofs.verify_file(path, actual)
        with self.assertRaises(TypeError):
            actual["sha256"] = "a" * 64

    def test_wrong_external_file_anchor_and_boolean_size_reject(self):
        path = self.root / "template.json"
        proof = dict(proofs.capture_file(path, "template.json"))
        for changes in ({"sha256": "a" * 64}, {"bytes": True}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                proofs.verify_file(path, {**proof, **changes})

    def test_package_complete_inventory_resources_and_no_code_execution(self):
        (self.root / "nested").mkdir()
        (self.root / "nested" / "extra.py").write_text(
            "raise SystemExit('do not import')\n"
        )
        proof = self.capture()
        self.assertEqual(
            [p["logical_id"] for p in proof["code"]],
            ["tether_engine/__init__.py", "tether_engine/nested/extra.py"],
        )
        self.assertEqual(
            proof["resources"]["template_v1"]["proof"]["logical_id"],
            "tether_engine/template.json",
        )
        proofs.verify_package_proof(proof, required_resources=self.required)
        with self.assertRaises(TypeError):
            proof["resources"]["template_v1"]["proof"]["bytes"] = 0

    def test_changed_or_added_or_missing_python_file_rejects(self):
        proof = self.capture()
        path = self.root / "__init__.py"
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(proof, required_resources=self.required)
        path.write_bytes(original)
        (self.root / "new.py").write_text("x=1\n")
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(proof, required_resources=self.required)
        (self.root / "new.py").unlink()
        path.unlink()
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(proof, required_resources=self.required)

    def test_changed_resource_or_anchor_metadata_rejects(self):
        proof = self.capture()
        tampered = encode(proof)
        tampered["package_version"] = "invented"
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(tampered, required_resources=self.required)
        (self.root / "template.json").write_bytes(b"different resource")
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(proof, required_resources=self.required)

    def test_required_resources_cannot_be_omitted_duplicated_or_substituted(self):
        for resources, required in [
            ({}, self.required),
            (self.resources, ()),
            (self.resources, ("template_v1", "template_v1")),
            ({"x": "template.json", "y": "template.json"}, ("x", "y")),
            ({"x": "__init__.py"}, ("x",)),
        ]:
            with self.subTest(resources=resources), self.assertRaises(ContractError):
                proofs.capture_package_proof(resources, required)
        proof = encode(self.capture())
        proof["resources"].clear()
        with self.assertRaises(ContractError):
            proofs.verify_package_proof(proof, required_resources=self.required)

    def test_unsafe_logical_and_resource_paths_rejected(self):
        for value in (
            "../outside",
            "/absolute",
            "a//b",
            "a\\b",
            "C:/outside",
            "NUL",
            "x ",
            "x\0",
        ):
            with self.subTest(value=value), self.assertRaises(ContractError):
                proofs.capture_file(self.root / "template.json", value)
            with self.subTest(resource=value), self.assertRaises(ContractError):
                proofs.capture_package_proof({"x": value}, ("x",))

    def test_file_replacement_during_hash_rejects(self):
        original = proofs.os.fstat
        calls = 0

        def changing(descriptor):
            nonlocal calls
            calls += 1
            result = original(descriptor)
            values = {
                name: getattr(result, name)
                for name in (
                    "st_dev",
                    "st_ino",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            }
            if calls == 2:
                values["st_ino"] += 1
            if hasattr(result, 'st_birthtime_ns'):
                values['st_birthtime_ns'] = result.st_birthtime_ns
            return SimpleNamespace(**values)

        with patch.object(proofs.os, "fstat", side_effect=changing):
            with self.assertRaisesRegex(ContractError, "changed during"):
                proofs.capture_file(self.root / "template.json", "template.json")

    def windows_clocks(self, *, change_handle=False):
        """Reproduce the distinct path/handle ctime meanings without OS mutation."""
        original_stat, original_fstat = Path.stat, proofs.os.fstat
        calls = 0
        def fields(info, changed):
            values = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
            values.update(st_birthtime_ns=100, st_ctime_ns=changed)
            return SimpleNamespace(**values)
        def path_stat(path, **kwargs):
            return fields(original_stat(path, **kwargs), 100)
        def handle_stat(descriptor):
            nonlocal calls
            calls += 1
            return fields(original_fstat(descriptor), 201 if change_handle and calls > 1 else 200)
        return path_stat, handle_stat

    def test_windows_creation_and_handle_change_clocks_are_not_cross_compared(self):
        path = self.root / 'template.json'
        path_stat, handle_stat = self.windows_clocks()
        with patch.object(proofs, '_WINDOWS_IDENTITY', True, create=True), \
                patch.object(Path, 'stat', new=path_stat), patch.object(proofs.os, 'fstat', new=handle_stat):
            self.assertGreater(proofs.capture_file(path, 'template.json')['bytes'], 0)
            self.assertGreater(hash_file(path, time.monotonic() + 10)['bytes'], 0)
            self.assertEqual(read_file(path, time.monotonic() + 10, 1024), path.read_bytes())

    def test_changed_handle_clock_still_fails_windows_readers(self):
        path = self.root / 'template.json'
        for operation, reason in (
            (lambda: proofs.capture_file(path, 'template.json'), 'changed during read'),
            (lambda: hash_file(path, time.monotonic() + 10), 'changed while hashing'),
            (lambda: read_file(path, time.monotonic() + 10, 1024), 'changed while reading'),
        ):
            path_stat, handle_stat = self.windows_clocks(change_handle=True)
            with self.subTest(operation=reason), \
                    patch.object(proofs, '_WINDOWS_IDENTITY', True, create=True), \
                    patch.object(Path, 'stat', new=path_stat), patch.object(proofs.os, 'fstat', new=handle_stat):
                with self.assertRaisesRegex(ContractError, reason):
                    operation()

    def test_posix_change_clock_remains_part_of_file_identity(self):
        fields = dict(st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4, st_birthtime_ns=5)
        with patch.object(proofs, '_WINDOWS_IDENTITY', False, create=True):
            self.assertNotEqual(proofs._identity(SimpleNamespace(**fields, st_ctime_ns=6)),
                                proofs._identity(SimpleNamespace(**fields, st_ctime_ns=7)))

    def test_reparse_component_rejected_without_opening_file(self):
        original = Path.lstat

        def reparse(path):
            result = original(path)
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)

        with patch.object(Path, "lstat", reparse), patch.object(Path, "open") as opened:
            with self.assertRaisesRegex(ContractError, "symlink/reparse"):
                proofs.capture_file(self.root / "template.json", "template.json")
            opened.assert_not_called()

    def test_resource_binding_does_not_alias_caller_mapping(self):
        proof = self.capture()
        self.resources["template_v1"] = "new.json"
        self.assertEqual(
            proof["resources"]["template_v1"]["relative_path"], "template.json"
        )

    def test_large_file_is_hashed_in_bounded_chunks(self):
        path = self.root / "large.bin"
        path.write_bytes(b"x" * (2 * 1024 * 1024 + 11))
        original = Path.open
        reads = []

        class Stream:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.wrapped.close()

            def fileno(self):
                return self.wrapped.fileno()

            def read(self, count):
                reads.append(count)
                return self.wrapped.read(count)

        with patch.object(
            Path, "open", lambda p, *a, **k: Stream(original(p, *a, **k))
        ):
            proof = proofs.capture_file(path, "large.bin")
        self.assertEqual(proof["bytes"], 2 * 1024 * 1024 + 11)
        self.assertTrue(reads)
        self.assertEqual(set(reads), {1024 * 1024})


if __name__ == "__main__":
    unittest.main()
