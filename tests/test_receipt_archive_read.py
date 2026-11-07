"""Receipt verification tolerates bounded sharing contention, never changed bytes."""
from dataclasses import dataclass
import errno
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine import ingest
from tether_engine.serde import ContractError


@dataclass(frozen=True)
class ReceiptNode:
    receipt_sha256: str
    receipt_path: str = 'transport/original.json'


class ReceiptArchiveReadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.raw = b'exact inspected receipt\r\n'
        self.node = ReceiptNode(hashlib.sha256(self.raw).hexdigest())
        self.item = {'node': self.node, 'receipt_bytes': self.raw}

    def test_transient_windows_read_is_retried_without_republishing(self):
        original = Path.read_bytes
        attempts = []

        def read(path):
            attempts.append(path)
            if len(attempts) == 1:
                raise PermissionError(errno.EACCES, 'invented sharing contention')
            return original(path)

        with patch.object(ingest, 'os', SimpleNamespace(name='nt')), \
             patch.object(Path, 'read_bytes', read), \
             patch.object(ingest.time, 'sleep') as wait, \
             patch.object(ingest, 'publish_bytes', wraps=ingest.publish_bytes) as publish:
            ingest._archive_receipts(self.root, [self.item])
        self.assertEqual(len(attempts), 2)
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(wait.call_count, 1)
        self.assertEqual((self.root / self.item['node'].receipt_path).read_bytes(), self.raw)

    def test_persistent_windows_denial_is_bounded_and_preserves_original_node(self):
        with patch.object(ingest, 'os', SimpleNamespace(name='nt')), \
             patch.object(Path, 'read_bytes', side_effect=PermissionError(errno.EACCES, 'persistent denial')) as read, \
             patch.object(ingest.time, 'sleep') as wait, \
             patch.object(ingest, 'publish_bytes', wraps=ingest.publish_bytes) as publish:
            with self.assertRaises(PermissionError):
                ingest._archive_receipts(self.root, [self.item])
        self.assertEqual(read.call_count, 8)
        self.assertEqual(wait.call_count, 7)
        self.assertEqual(publish.call_count, 1)
        self.assertIs(self.item['node'], self.node)
        self.assertEqual(list(self.root.rglob('.receipt-*')), [])

    def test_non_windows_and_unrelated_errors_propagate_without_retry(self):
        for platform, error in (
            ('posix', PermissionError(errno.EACCES, 'denied')),
            ('nt', PermissionError(errno.EPERM, 'not permitted')),
            ('nt', OSError(errno.EIO, 'device error')),
        ):
            with self.subTest(platform=platform, error=error), \
                 patch.object(ingest, 'os', SimpleNamespace(name=platform)), \
                 patch.object(Path, 'read_bytes', side_effect=error) as read, \
                 patch.object(ingest.time, 'sleep') as wait:
                with self.assertRaises(type(error)):
                    ingest._archive_receipts(self.root, [self.item])
                self.assertEqual(read.call_count, 1)
                wait.assert_not_called()
                self.assertIs(self.item['node'], self.node)

    def test_changed_bytes_after_contention_still_fail_verification(self):
        with patch.object(ingest, 'os', SimpleNamespace(name='nt')), \
             patch.object(Path, 'read_bytes', side_effect=[PermissionError(errno.EACCES, 'sharing'), b'changed']), \
             patch.object(ingest.time, 'sleep'):
            with self.assertRaisesRegex(ContractError, 'conflicting bytes'):
                ingest._archive_receipts(self.root, [self.item])
        self.assertIs(self.item['node'], self.node)


if __name__ == '__main__':
    unittest.main()
