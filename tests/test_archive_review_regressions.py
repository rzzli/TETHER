"""Independent archive IO regressions; no live roots, inference or label payloads."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.archive.interpretation import _Context
from tether_engine.archive.paths import ArchiveResolver
from tether_engine.serde import ContractError, canonical, fingerprint, freeze


class ArchiveReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.logical_root = 'Q:/unavailable/archive-review'

    def resolver_for(self, name, content):
        physical = self.root / name
        physical.write_bytes(content)
        identity = self.logical_root + '/' + name
        row = dict(logical_path=identity, root_id='restored', relative_path=name,
                   sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
        resolver = ArchiveResolver(
            [dict(root_id='restored', logical_root=self.logical_root,
                  physical_root=str(self.root))], [row])
        return resolver, identity, physical

    @staticmethod
    def journal(run_id):
        entry = dict(sequence=0, event='build_reserved',
                     details=dict(run_id=run_id), previous_sha256=None)
        entry['sha256'] = fingerprint(entry)
        return canonical(entry) + b'\n'

    def test_nested_immutable_journal_pin_accepts_matching_bytes(self):
        payload = b'{"preserved":true}'
        resolver, identity, _ = self.resolver_for('report.json', payload)
        event = freeze(dict(details=dict(report=dict(
            path=identity, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)))))
        context = _Context(resolver, {})
        self.assertEqual(context.pin(event['details']['report']), context.logical(identity))
        # Mapping acceptance must not weaken the authenticated hash contract.
        invalid = freeze(dict(path=identity, sha256='0' * 64, bytes=len(payload)))
        with self.assertRaises(ContractError):
            context.pin(invalid)

    def test_chain_parses_verified_buffer_even_if_path_changes_after_read(self):
        original = self.journal('authenticated-original')
        replacement = self.journal('untrusted-replacement')
        resolver, identity, physical = self.resolver_for('journal.jsonl', original)
        context = _Context(resolver, {})
        checked_read = resolver.read_bytes

        def change_after_checked_read(logical_path, **kwargs):
            authenticated = checked_read(logical_path, **kwargs)
            physical.write_bytes(replacement)
            return authenticated

        with patch.object(resolver, 'read_bytes', change_after_checked_read):
            records = context.chain(context.logical(identity))
        self.assertEqual(records[0]['details']['run_id'], 'authenticated-original')
        self.assertEqual(physical.read_bytes(), replacement)
        # A later independent read must reject the now-unanchored bytes.
        with self.assertRaises(ContractError):
            resolver.read_bytes(identity)


if __name__ == '__main__':
    unittest.main()
