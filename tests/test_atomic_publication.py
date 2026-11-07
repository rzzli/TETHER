"""Atomic publication must never depend on hard-link support on Windows."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tether_engine.ingest import _archive_receipts
from tether_engine.atomic import ensure_directory
from tether_engine.maintenance import write_new_json
from tether_engine.serde import ContractError


@dataclass(frozen=True)
class ReceiptNode:
    receipt_sha256: str
    receipt_path: str = 'transport/original.json'


class AtomicPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_directory_initialization_uses_shared_lock(self):
        class CheckedLock:
            def __init__(self):
                self.lock = threading.Lock()
                self.owner = None
                self.entries = 0
            def __enter__(self):
                self.lock.acquire()
                self.owner = threading.get_ident()
                self.entries += 1
            def __exit__(self, *args):
                self.owner = None
                self.lock.release()
        checked = CheckedLock()
        def mkdir(*args, **kwargs):
            self.assertEqual(checked.owner, threading.get_ident())
            self.assertEqual(kwargs, {'parents': True, 'exist_ok': True})
        with patch('tether_engine.atomic._directory_initialization_lock', checked), patch.object(Path, 'mkdir', side_effect=mkdir):
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(ensure_directory, [self.root/'new'] * 32))
        self.assertEqual(checked.entries, 32)

    def test_directory_permission_failure_propagates_without_retry(self):
        with patch.object(Path, 'mkdir', side_effect=PermissionError('denied')) as mkdir:
            with self.assertRaises(PermissionError): ensure_directory(self.root/'new')
            self.assertEqual(mkdir.call_count, 1)

    def test_json_without_hardlinks_windows_or_fail_closed_posix(self):
        target = self.root/'report.json'
        value = {'text':'original Unicode \u03b1', 'value':3}
        with patch('os.link',side_effect=PermissionError('hard links unsupported')):
            if os.name == 'nt':
                write_new_json(target,value)
                self.assertEqual(target.read_bytes(),(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
            else:
                with self.assertRaises(PermissionError):write_new_json(target,value)
                self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.publishing-*')),[])

    def test_receipt_without_hardlinks_preserves_exact_transport_bytes(self):
        raw=b'{ "status": "completed" }\r\n'
        source=self.root/'transport.json';source.write_bytes(raw)
        node=ReceiptNode(hashlib.sha256(raw).hexdigest())
        item={'receipt_bytes':raw,'node':node}
        with patch('os.link',side_effect=PermissionError('hard links unsupported')):
            if os.name=='nt':
                _archive_receipts(self.root,[item])
                self.assertEqual((self.root/item['node'].receipt_path).read_bytes(),raw)
            else:
                with self.assertRaises(PermissionError):_archive_receipts(self.root,[item])
                self.assertEqual(item['node'],node)
        self.assertEqual(source.read_bytes(),raw)
        self.assertEqual(list(self.root.rglob('.receipt-*')),[])

    def test_concurrent_json_publication_has_one_winner(self):
        target=self.root/'report.json'
        def attempt(i):
            try:write_new_json(target,{'winner':i});return i
            except FileExistsError:return None
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(16)))
        winners=[i for i in results if i is not None]
        self.assertEqual(len(winners),1)
        self.assertEqual(json.loads(target.read_bytes()),{'winner':winners[0]})
        self.assertEqual(list(self.root.glob('.publishing-*')),[])

    def test_existing_target_never_changes(self):
        target=self.root/'report.json';target.write_bytes(b'original bytes')
        with self.assertRaises(FileExistsError):write_new_json(target,{'replacement':True})
        self.assertEqual(target.read_bytes(),b'original bytes')
        self.assertEqual(list(self.root.glob('.publishing-*')),[])

    def test_write_failure_cleans_temporary_and_keeps_original(self):
        target=self.root/'report.json';target.write_bytes(b'original')
        with patch('os.fsync',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):write_new_json(target,{'replacement':True})
        self.assertEqual(target.read_bytes(),b'original')
        self.assertEqual(list(self.root.glob('.publishing-*')),[])

    def test_unsupported_publication_primitive_fails_closed(self):
        target=self.root/'unpublished.json'
        primitive='os.rename' if os.name=='nt' else 'os.link'
        with patch(primitive,side_effect=OSError('filesystem primitive unavailable')):
            with self.assertRaises(OSError):write_new_json(target,{'value':1})
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.publishing-*')),[])

    def test_receipt_concurrent_publication_and_conflict(self):
        # Exercise competing publication into an initialized receipt archive.
        # Directory-tree initialization has a separate path-containment contract.
        (self.root/'manifests/receipt-archive').mkdir(parents=True)
        raw=b'exact original receipt\r\n';node=ReceiptNode(hashlib.sha256(raw).hexdigest())
        def attempt(_):
            item={'receipt_bytes':raw,'node':node};_archive_receipts(self.root,[item]);return item
        with ThreadPoolExecutor(max_workers=8) as pool:items=list(pool.map(attempt,range(16)))
        target=self.root/items[0]['node'].receipt_path
        self.assertEqual(target.read_bytes(),raw)
        with self.assertRaises(ContractError):
            _archive_receipts(self.root,[{'receipt_bytes':b'conflicting','node':node}])
        self.assertEqual(target.read_bytes(),raw)
        self.assertEqual(list(self.root.rglob('.receipt-*')),[])

    def test_receipt_write_failure_does_not_update_node(self):
        node=ReceiptNode(hashlib.sha256(b'raw').hexdigest());item={'receipt_bytes':b'raw','node':node}
        with patch('os.fsync',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):_archive_receipts(self.root,[item])
        self.assertIs(item['node'],node)
        self.assertEqual(list(self.root.rglob('*.json')),[])
        self.assertEqual(list(self.root.rglob('.receipt-*')),[])


if __name__=='__main__':unittest.main()
