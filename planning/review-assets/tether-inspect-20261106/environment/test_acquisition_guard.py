import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import acquire_environment_v2 as guard


class GuardTests(unittest.TestCase):
    def test_missing_temporary_subtree_is_eligible_empty_snapshot(self):
        self.assertEqual(guard.size_tree(guard.base.ROOT/"data/cache/nonexistent-inspect-guard-fixture"), 0)

    def test_file_removed_between_enumeration_and_stat(self):
        with tempfile.TemporaryDirectory(dir=guard.base.ROOT/"data/cache") as directory:
            path = Path(directory)
            (path/"stable").write_bytes(b"fixture")
            with patch.object(guard.os, "walk", return_value=iter([(directory, [], ["stable", "disappeared"])])):
                self.assertEqual(guard.size_tree(path), 7)

    def test_other_monitor_errors_fail_closed(self):
        guard.walk_error(FileNotFoundError("concurrent deletion"))
        with self.assertRaises(PermissionError):
            guard.walk_error(PermissionError("not a deletion race"))


if __name__ == "__main__":
    unittest.main()
