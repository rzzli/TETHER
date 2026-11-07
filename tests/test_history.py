"""Exact archival bytes remain testable without rewriting the current checkout."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import history


class HistoryTests(unittest.TestCase):
    def test_checkpoint_is_exact_and_preserved_failed_source_keeps_its_hash(self):
        self.assertEqual(history.CHECKPOINT, "b492a8fca9bb1aa500d2939b3e2d19242a55cb96")
        raw = history.read_checkpoint("planning/review-assets/recovery-step9-native-recognition-20261028/check_recognition_module_policy_v1_before_syntax.py")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "5aa964d861635aaf01c50ec05f83618d5bfb7307f6e591630991f34070d05253")

    def test_materialized_legacy_fixture_preserves_every_original_blob(self):
        prefix = "tests/fixtures/legacy-v1"
        with tempfile.TemporaryDirectory() as folder:
            destination = history.materialize_checkpoint(prefix, Path(folder) / "original")
            expected = history._entries(prefix)
            self.assertEqual(len(list(destination.iterdir())), len(expected))
            for name, _ in expected:
                self.assertEqual((destination / name[len(prefix)+1:]).read_bytes(), history.read_checkpoint(name))

    def test_single_file_materialization_never_overwrites(self):
        source = "tests/fixtures/legacy-v1/receipt.sha256"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "anchor"
            history.materialize_checkpoint(source, path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                history.materialize_checkpoint(source, path)
            self.assertEqual(path.read_bytes(), before)

    def test_unsafe_paths_are_rejected_before_git(self):
        with patch.object(history, "_git") as git:
            for path in ("", ".", "..", "a/../b", "a//b", "/absolute", "C:/absolute", "a\\b", ".git/config", "a\x00b"):
                with self.subTest(path=path), self.assertRaises(history.HistoryError):
                    history.read_checkpoint(path)
            git.assert_not_called()

    def test_git_is_argv_only_with_literal_paths_and_fixed_commit(self):
        value = b"100644 blob " + b"a"*40 + b"\tpath/file\0"
        with patch.object(history.subprocess, "check_output", return_value=value) as command:
            history._entries("path/file")
        args, options = command.call_args
        self.assertEqual(args[0][-3:], [history.CHECKPOINT, "--", "path/file"])
        self.assertIn("--no-replace-objects", args[0])
        self.assertIn("--literal-pathspecs", args[0])
        self.assertNotIn("shell", options)

    def test_nonregular_archive_entry_is_rejected(self):
        for mode in (b"120000", b"160000"):
            with patch.object(history, "_git", return_value=mode+b" blob "+b"a"*40+b"\tpath/file\0"):
                with self.assertRaises(history.HistoryError):
                    history.read_checkpoint("path/file")

    def test_changed_or_oversized_blob_cannot_pass_identity_check(self):
        with patch.object(history, "_git", side_effect=[b"3", b"bad"]):
            with self.assertRaisesRegex(history.HistoryError, "identity mismatch"):
                history._blob("a"*40)
        with patch.object(history, "_git", return_value=str(history.MAX_BLOB_BYTES+1).encode()) as command:
            with self.assertRaisesRegex(history.HistoryError, "read bound"):
                history._blob("a"*40)
            self.assertEqual(command.call_count, 1)


if __name__ == "__main__":
    unittest.main()
