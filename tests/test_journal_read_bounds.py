"""Native journal/trace reads need limits even without the public wrapper."""
from pathlib import Path
import io
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.cli import main
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal, read_chain
from tether_engine import journal as journal_module
from tether_engine.serde import ContractError, decode, read_json, sha256_file
from tether_engine.workflow import run_workflow


class JournalReadBoundsTests(unittest.TestCase):
    def test_oversized_chain_fails_with_limit_reason_even_during_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'journal.jsonl'
            path.write_bytes(b' ' * 257)
            for recovery in (False, True):
                with self.subTest(recovery=recovery), \
                        patch('tether_engine.journal.MAX_JOURNAL_BYTES', 256, create=True):
                    with self.assertRaisesRegex(ContractError, 'Journal exceeds byte limit'):
                        read_chain(path, allow_incomplete_tail=recovery)

    def test_growth_after_stat_still_has_a_bounded_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'journal.jsonl'
            path.write_bytes(b' ' * 257)
            with patch('tether_engine.journal.MAX_JOURNAL_BYTES', 256, create=True), \
                    patch.object(Path, 'stat', return_value=SimpleNamespace(st_size=1)):
                with self.assertRaisesRegex(ContractError, 'Journal exceeds byte limit'):
                    read_chain(path)

    def test_append_over_limit_preserves_the_last_durable_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            journal = RunJournal(Path(temporary) / 'run')
            try:
                before = journal.path.read_bytes()
                with patch('tether_engine.journal.MAX_JOURNAL_BYTES', len(before) + 10):
                    with self.assertRaisesRegex(ContractError, 'Journal exceeds byte limit'):
                        journal.append('oversized', data='X' * 1000)
                self.assertEqual(journal.path.read_bytes(), before)
                self.assertEqual(len(journal.events), 1)
                self.assertEqual(read_chain(journal.path), journal.events)
                with self.assertRaisesRegex(ContractError, 'Journal hash differs from expected bytes'):
                    read_chain(journal.path, expected_sha256='0' * 64)
            finally:
                journal.close()

    def test_hashing_stops_at_limit_and_accepts_exact_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'file'
            path.write_bytes(b'x' * 256)
            self.assertEqual(sha256_file(path, max_bytes=256), sha256_file(path))
            with self.assertRaisesRegex(ContractError, 'File exceeds hash byte limit'):
                sha256_file(path, max_bytes=255)
            for invalid in (-1, True, 0.5):
                with self.subTest(limit=invalid), self.assertRaisesRegex(ContractError, 'Invalid file hash byte limit'):
                    sha256_file(path, max_bytes=invalid)

    def test_native_output_limit_precedes_hashing_oversized_dossier(self):
        fixture = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'
        case = decode(Case, read_json(fixture / 'case.json'))
        store = load_snapshot(fixture / 'snapshot.json', case)
        result = run_workflow(case, store, ExtractiveBackend())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            write_run(output, result, store, None)
            limit = (output / 'ledger.json').stat().st_size + 1
            (output / 'dossier.md').write_bytes(b' ' * (limit + 1))
            def guarded(path, **kwargs):
                if path.name == 'dossier.md':
                    raise AssertionError('Oversized dossier was hashed')
                return sha256_file(path, **kwargs)
            with patch('tether_engine.artifacts.MAX_LEDGER_JSON_BYTES', limit), \
                    patch('tether_engine.artifacts.sha256_file', side_effect=guarded):
                with self.assertRaisesRegex(ContractError, 'Run output exceeds byte limit: dossier.md'):
                    verify_run(output, source_roots=((output).parent,))

    def test_full_journal_returns_failure_without_overwriting_durable_prefix(self):
        fixture = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'
        original = RunJournal.append
        def fill_before_plan(journal, event, **details):
            if event == 'plan':
                journal_module.MAX_JOURNAL_BYTES = journal._durable_size
            return original(journal, event, **details)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            with patch.object(journal_module, 'MAX_JOURNAL_BYTES', journal_module.MAX_JOURNAL_BYTES), \
                    patch.object(RunJournal, 'append', new=fill_before_plan), \
                    patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                status = main(['run', '--case', str(fixture / 'case.json'), '--snapshot',
                               str(fixture / 'snapshot.json'), '--output', str(output)])
            self.assertEqual(status, 2)
            self.assertFalse((output / 'receipt.json').exists())
            events = read_chain(output / 'journal.jsonl')
            self.assertEqual(events[-1]['event'], 'inputs_archived')
            self.assertFalse(any(event['event'] == 'dispatch' for event in events))


if __name__ == '__main__':
    unittest.main()
