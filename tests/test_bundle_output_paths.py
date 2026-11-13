"""Export path preflight must reject unsafe paths before creating anything."""
from pathlib import Path
import os
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine import bundle_files
from tether_engine.serde import ContractError


class BundleOutputPathTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).absolute()
        self.original = self.root / 'original'
        self.original.mkdir()

    def test_safe_fresh_output_and_missing_parents_do_not_create_files(self):
        output = self.root / 'fresh' / 'nested'
        self.assertEqual(bundle_files.checked_output(output, (self.original,)), output)
        self.assertFalse(output.parent.exists())
        self.assertEqual(bundle_files.checked_root(self.original), self.original)

    def test_parent_traversal_is_rejected_before_any_output(self):
        side = self.root / 'side'
        side.mkdir()
        unsafe = side / '..' / 'original' / 'export'
        with self.assertRaises(ContractError):
            bundle_files.checked_output(unsafe, (self.original,))
        self.assertEqual(list(self.original.iterdir()), [])
        with self.assertRaises(ContractError):
            bundle_files.checked_root(side / '..' / 'original')

    def test_output_beneath_forbidden_roots_is_rejected(self):
        with self.assertRaises(ContractError):
            bundle_files.checked_output(self.original / 'export', (self.original,))
        self.assertFalse((self.original / 'export').exists())

    def test_existing_output_or_file_ancestor_is_rejected(self):
        with self.assertRaises(ContractError):
            bundle_files.checked_output(self.original)
        existing_file = self.root / 'file'
        existing_file.write_bytes(b'unchanged')
        with self.assertRaises(ContractError):
            bundle_files.checked_output(existing_file / 'child')
        self.assertEqual(existing_file.read_bytes(), b'unchanged')

    def test_missing_source_root_is_rejected_without_creation(self):
        missing = self.root / 'missing'
        with self.assertRaises(ContractError):
            bundle_files.checked_root(missing)
        self.assertFalse(missing.exists())

    def test_linked_parent_is_rejected_without_following_it(self):
        real_lstat = Path.lstat
        def linked(path):
            if path == self.original:
                return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_file_attributes=0)
            return real_lstat(path)
        with patch.object(Path, 'lstat', linked):
            with self.assertRaises(ContractError):
                bundle_files.checked_output(self.original / 'export')
            with self.assertRaises(ContractError):
                bundle_files.checked_root(self.original)
        self.assertFalse((self.original / 'export').exists())

    def test_windows_reparse_parent_is_rejected(self):
        real_lstat = Path.lstat
        def reparsed(path):
            if path == self.original:
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o777,
                                       st_file_attributes=0x400)
            return real_lstat(path)
        with patch.object(Path, 'lstat', reparsed):
            with self.assertRaises(ContractError):
                bundle_files.checked_output(self.original / 'export')
            with self.assertRaises(ContractError):
                bundle_files.checked_root(self.original)

    def test_noncanonical_physical_path_is_rejected(self):
        for name in ('NUL.txt', 'side ', 'name:stream', 'e\u0301'):
            with self.subTest(name=name), self.assertRaises(ContractError):
                bundle_files.checked_output(self.root / name)
        if os.name == 'nt':
            with self.assertRaises(ContractError):
                bundle_files.checked_output(Path(r'\\server\share\new'))


if __name__ == '__main__':
    unittest.main()
