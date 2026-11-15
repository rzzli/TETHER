"""Seal publication is irreversible; failures before it retain a writable journal."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine import atomic
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError


class JournalSealBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = RunJournal(Path(self.temp.name) / 'run', kind='build')
        self.addCleanup(self.journal.close)

    def test_success_seal_keeps_exact_bytes_and_disallows_later_failure_event(self):
        payload = b'{"original":"bytes"}\n'
        anchor = self.journal.seal(payload)
        before = self.journal.path.read_bytes()
        self.assertEqual(anchor, hashlib.sha256(payload).hexdigest())
        self.assertEqual((self.journal.output / 'receipt.json').read_bytes(), payload)
        self.assertFalse(self.journal.fail(OSError('presentation'), 'presentation'))
        self.assertEqual(self.journal.path.read_bytes(), before)
        with self.assertRaisesRegex(ContractError, 'sealed'):
            self.journal.append('must_not_append')

    def test_expiry_during_staging_prevents_publication_and_retains_failure(self):
        now = [0.0]
        fsync = atomic.os.fsync
        def slow_sync(fd):
            fsync(fd)
            now[0] = 2.0
        with patch('time.monotonic', side_effect=lambda: now[0]), \
                patch.object(atomic.os, 'fsync', side_effect=slow_sync):
            with self.assertRaisesRegex(TimeoutError, 'seal deadline'):
                self.journal.seal(b'{}', deadline=1)
        self.assertFalse((self.journal.output / 'receipt.json').exists())
        self.journal.fail(TimeoutError('staging'), 'sealing')
        self.assertEqual(read_chain(self.journal.path)[-1]['event'], 'build_failed')
        self.assertEqual(sorted(p.name for p in self.journal.output.iterdir()), ['journal.jsonl'])

    def test_interruption_after_atomic_visibility_does_not_rewrite_journal(self):
        original = atomic.publish_bytes
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise KeyboardInterrupt('after publication')
        before = self.journal.path.read_bytes()
        with patch.object(atomic, 'publish_bytes', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.journal.seal(b'{}')
        self.assertTrue(self.journal.sealed)
        self.assertFalse(self.journal.fail(KeyboardInterrupt(), 'sealing'))
        self.assertEqual(self.journal.path.read_bytes(), before)

    def test_invalid_deadlines_and_seal_names_do_not_publish(self):
        for deadline in (float('nan'), float('inf'), True):
            with self.subTest(deadline=deadline), self.assertRaises(ContractError):
                self.journal.seal(b'{}', deadline=deadline)
        with self.assertRaises(ContractError):
            self.journal.seal(b'{}', name='../receipt.json')
        self.assertFalse(self.journal.sealed)

    def test_named_terminal_seal_uses_same_boundary(self):
        self.journal.seal(b'{}', name='terminal-seal.json')
        self.assertTrue(self.journal.sealed)
        self.assertFalse(self.journal.fail(OSError(), 'after_terminal_seal'))


if __name__ == '__main__':
    unittest.main()
