"""Relocation failures use invented bytes; never open actual provider inputs."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.science.prepare_p09_relocated_inputs import copy_exact, prepare


class RelocationTests(unittest.TestCase):
    def test_copy_readback_and_existing_target_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "copied"
            source.write_bytes(b"fictional source")
            copy_exact(source, target, hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            source.write_bytes(b"changed")
            with self.assertRaises(FileExistsError):
                copy_exact(source, target, "0" * 64, 7)
            self.assertEqual(target.read_bytes(), b"fictional source")

    def test_changed_bytes_and_length_fail_without_deleting_failure(self):
        for expected, length in (("0" * 64, 3), (hashlib.sha256(b"abc").hexdigest(), 2)):
            with self.subTest(length=length), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "source").write_bytes(b"abc")
                with self.assertRaises(ValueError):
                    copy_exact(root / "source", root / "partial", expected, length)
                self.assertTrue((root / "partial").exists())
                self.assertEqual((root / "source").read_bytes(), b"abc")

    def test_unapproved_output_rejected_before_bundle_or_sources_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "asof-p09-wrong-parent"
            with self.assertRaisesRegex(ValueError, "approved C:"):
                prepare(root / "absent-bundle", "0" * 64, root / "absent-originals", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
