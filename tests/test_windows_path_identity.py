"""Windows resolved-path spelling must not change containment decisions."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.ingest import _archive_receipts
from tether_engine.serde import ContractError, safe_child, _windows_path_spelling


@dataclass(frozen=True)
class ReceiptNode:
    receipt_sha256: str
    receipt_path: str = 'transport/original.json'


class WindowsPathIdentityTests(unittest.TestCase):
    def test_extended_candidate_normal_root(self):
        self.assertEqual(_windows_path_spelling(r'\\?\D:\approved\child'), r'D:\approved\child')
        if os.name != 'nt': return
        with patch.object(Path, 'resolve', side_effect=[Path(r'\\?\D:\approved\child'), Path(r'D:\approved')]):
            self.assertEqual(safe_child(Path(r'D:\approved'), 'child'), Path(r'D:\approved\child'))

    def test_normal_candidate_extended_root(self):
        self.assertEqual(_windows_path_spelling(r'D:\approved\child'), r'D:\approved\child')
        self.assertEqual(_windows_path_spelling(r'\\?\D:\approved'), r'D:\approved')
        if os.name != 'nt': return
        with patch.object(Path, 'resolve', side_effect=[Path(r'D:\approved\child'), Path(r'\\?\D:\approved')]):
            self.assertEqual(safe_child(Path(r'D:\approved'), 'child'), Path(r'D:\approved\child'))

    def test_unc_equivalence(self):
        self.assertEqual(_windows_path_spelling(r'\\?\UNC\server\share\approved\child'), r'\\server\share\approved\child')
        if os.name != 'nt': return
        with patch.object(Path, 'resolve', side_effect=[Path(r'\\?\UNC\server\share\approved\child'), Path(r'\\server\share\approved')]):
            self.assertEqual(safe_child(Path(r'\\server\share\approved'), 'child'), Path(r'\\server\share\approved\child'))

    def test_extended_resolved_escape_rejected(self):
        child = PureWindowsPath(_windows_path_spelling(r'\\?\D:\outside\child'))
        root = PureWindowsPath(_windows_path_spelling(r'D:\approved'))
        self.assertFalse(child.is_relative_to(root))
        if os.name != 'nt': return
        with patch.object(Path, 'resolve', side_effect=[Path(r'\\?\D:\outside\child'), Path(r'D:\approved')]):
            with self.assertRaises(ContractError): safe_child(Path(r'D:\approved'), 'child')

    def test_unsupported_device_roots_rejected_before_resolution(self):
        for root in (r'\\.\C:\approved', r'\\?\GLOBALROOT\Device\HarddiskVolume1', r'\\?\Volume{abc}\approved', r'\??\C:\approved'):
            with self.subTest(root=root):
                with self.assertRaises(ContractError): _windows_path_spelling(root)
            if os.name != 'nt': continue
            with self.subTest(root=root), patch.object(Path, 'resolve', return_value=Path(r'D:\approved\child')) as resolve:
                with self.assertRaises(ContractError): safe_child(Path(root), 'child')
                resolve.assert_not_called()

    def test_non_equivalent_extended_names_rejected(self):
        for root in (r'\\?\D:\approved.', r'\\?\D:\approved ', r'\\?\D:\approved\..', r'\\?\UNC\server:stream\share'):
            with self.subTest(root=root):
                with self.assertRaises(ContractError): _windows_path_spelling(root)
                if os.name == 'nt':
                    with self.assertRaises(ContractError): safe_child(Path(root), 'child')

    def test_concurrent_first_receipt_directory_initialization(self):
        raw = b'exact receipt bytes\r\n'
        node = ReceiptNode(hashlib.sha256(raw).hexdigest())
        with tempfile.TemporaryDirectory() as temporary:
            for iteration in range(40):
                root = Path(temporary)/str(iteration)
                root.mkdir()
                def attempt(_):
                    item = {'receipt_bytes': raw, 'node': node}
                    _archive_receipts(root, [item])
                    return item['node'].receipt_path
                with ThreadPoolExecutor(max_workers=8) as pool:
                    paths = list(pool.map(attempt, range(16)))
                self.assertEqual(len(set(paths)), 1)
                self.assertEqual((root/paths[0]).read_bytes(), raw)
                self.assertEqual(list(root.rglob('.receipt-*')), [])


if __name__ == '__main__': unittest.main()
