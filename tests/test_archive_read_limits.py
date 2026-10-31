"""Bound archive buffering without restricting streaming raw-source verification."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.archive.paths import ArchiveResolver
from asof.serde import ContractError


class ArchiveReadLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'payload'
        self.identity = 'Q:/missing/archive/payload'

    def prepare(self, content):
        self.path.write_bytes(content)
        return ArchiveResolver(
            [dict(root_id='raw', logical_root='Q:/missing/archive', physical_root=str(self.root))],
            [dict(logical_path=self.identity, root_id='raw', relative_path='payload',
                  sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))])

    def test_declared_size_over_limit_rejected_before_open(self):
        resolver = self.prepare(b'12345')
        with patch.object(Path, 'open', side_effect=AssertionError('Must not open oversized input')) as opened:
            with self.assertRaisesRegex(ContractError, 'read limit'):
                resolver.read_bytes(self.identity, maximum_bytes=4)
        opened.assert_not_called()

    def test_actual_size_over_limit_rejected_before_open(self):
        resolver = self.prepare(b'1234')
        self.path.write_bytes(b'12345678')
        with patch.object(Path, 'open', side_effect=AssertionError('Must not open oversized input')) as opened:
            with self.assertRaisesRegex(ContractError, 'read limit'):
                resolver.read_bytes(self.identity, maximum_bytes=4)
        opened.assert_not_called()

    def test_exact_and_under_limit_preserve_bytes_and_hash_checks(self):
        resolver = self.prepare(b'{"x":1}')
        self.assertEqual(resolver.read_bytes(self.identity, maximum_bytes=7), b'{"x":1}')
        self.assertEqual(resolver.read_bytes(self.identity, maximum_bytes=8), b'{"x":1}')
        self.path.write_bytes(b'{"x":2}')
        with self.assertRaisesRegex(ContractError, 'hash/size'):
            resolver.read_bytes(self.identity, maximum_bytes=7)

    def test_growth_between_stat_and_open_rejected_before_read(self):
        resolver = self.prepare(b'1234')
        original_open = Path.open
        reads = []

        def grow(path, *args, **kwargs):
            with original_open(path, 'ab') as append:
                append.write(b'5')
            stream = original_open(path, *args, **kwargs)
            original_read = stream.read
            stream.read = lambda size=-1: (reads.append(size), original_read(size))[1]
            return stream

        with patch.object(Path, 'open', grow):
            with self.assertRaisesRegex(ContractError, 'read limit'):
                resolver.read_bytes(self.identity, maximum_bytes=4)
        self.assertEqual(reads, [])

    def test_growth_during_read_uses_bounded_request_and_rejects(self):
        resolver = self.prepare(b'1234')
        original_open = Path.open
        reads = []

        def grow_during_read(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            original_read = stream.read

            def read(size=-1):
                reads.append(size)
                with original_open(path, 'ab') as append:
                    append.write(b'567890')
                return original_read(size)

            stream.read = read
            return stream

        with patch.object(Path, 'open', grow_during_read):
            with self.assertRaisesRegex(ContractError, 'read limit'):
                resolver.read_bytes(self.identity, maximum_bytes=4)
        self.assertEqual(reads, [5])

    def test_raw_verification_and_default_read_are_not_json_capped(self):
        payload = b'raw source beyond a tiny JSON test limit'
        resolver = self.prepare(payload)
        with self.assertRaises(ContractError):
            resolver.read_bytes(self.identity, maximum_bytes=4)
        self.assertEqual(resolver.verify_file(self.identity), self.path)
        self.assertEqual(resolver.read_bytes(self.identity), payload)

    def test_zero_limit_accepts_only_empty_bytes_and_invalid_limits_fail(self):
        resolver = self.prepare(b'')
        self.assertEqual(resolver.read_bytes(self.identity, maximum_bytes=0), b'')
        for invalid in (-1, True, 1.0, '4'):
            with self.subTest(invalid=invalid), self.assertRaises(ContractError):
                resolver.read_bytes(self.identity, maximum_bytes=invalid)


if __name__ == '__main__':
    unittest.main()
