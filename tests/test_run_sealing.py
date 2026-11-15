"""A completed receipt is an immutable boundary, including presentation errors."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import RUN_FILES, dossier, verify_run, write_run
from tether_engine.atomic import publish_bytes
from tether_engine.chrono import load_snapshot
from tether_engine.cli import main
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal, inspect_run
from tether_engine.serde import ContractError, decode, read_json, sha256_file
from tether_engine.workflow import run_workflow


FIXTURE = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class RunSealingTests(unittest.TestCase):
    def test_intermediate_receipt_does_not_seal_an_unrelated_journal_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            journal = RunJournal(Path(temporary) / 'run')
            try:
                publish_bytes(journal.output / 'receipt.json', b'{"kind":"intermediate"}')
                journal.append('capture_completed')
                self.assertFalse(journal.sealed)
                self.assertEqual(journal.events[-1]['event'], 'capture_completed')
            finally:
                journal.close()

    def test_append_after_receipt_cannot_mutate_a_sealed_run(self):
        case = decode(Case, read_json(FIXTURE / 'case.json'))
        store = load_snapshot(FIXTURE / 'snapshot.json', case)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            journal = RunJournal(output)
            try:
                result = run_workflow(case, store, ExtractiveBackend(), journal=journal)
                anchor = write_run(output, result, store, None, journal)
                before = {name: sha256_file(output / name) for name in (*RUN_FILES, 'receipt.json')}
                with self.assertRaisesRegex(ContractError, 'sealed'):
                    journal.append('run_failed', error_class='OSError', stage='presentation')
                self.assertFalse(journal.fail(OSError('presentation failed'), 'presentation'))
                with self.assertRaisesRegex(ContractError, 'already sealed'):
                    write_run(output, result, store, None, journal)
                self.assertEqual(before, {name: sha256_file(output / name) for name in before})
                self.assertEqual((output / 'dossier.md').read_bytes(), dossier(result, store).encode('utf-8'))
                self.assertNotIn(b'\r\n', (output / 'dossier.md').read_bytes())
                self.assertEqual(verify_run(output, anchor, source_roots=(output.parent, FIXTURE))['semantic_consistency'], 'verified')
            finally:
                journal.close()

    def test_console_failure_or_interrupt_cannot_invalidate_the_receipt(self):
        for failure, expected in ((OSError('broken output'), 2), (KeyboardInterrupt(), 130)):
            with self.subTest(error=type(failure).__name__), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / 'run'
                def broken_print(*args, **kwargs):
                    if kwargs.get('file') is not sys.stderr:
                        raise failure
                with patch('tether_engine.cli.print', side_effect=broken_print), patch('sys.stderr', io.StringIO()):
                    status = main(['run', '--case', str(FIXTURE / 'case.json'), '--snapshot',
                                   str(FIXTURE / 'snapshot.json'), '--output', str(output)])
                self.assertEqual(status, expected)
                receipt = read_json(output / 'receipt.json')
                for name, digest in receipt['outputs'].items():
                    self.assertEqual(sha256_file(output / name), digest, name)
                self.assertEqual(verify_run(output, source_roots=(output.parent, FIXTURE))['semantic_consistency'], 'verified')

    def test_sync_failure_prevents_receipt_and_retains_unsealed_failure(self):
        for filename in ('trace.jsonl', 'dossier.md', 'receipt.json'):
            with self.subTest(output=filename), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / 'run'
                def fail_sync(path, payload):
                    if path.name == filename:
                        with patch('tether_engine.atomic.os.fsync', side_effect=OSError('sync failed')):
                            return publish_bytes(path, payload)
                    return publish_bytes(path, payload)
                with patch('tether_engine.artifacts.publish_bytes', side_effect=fail_sync), \
                        patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                    status = main(['run', '--case', str(FIXTURE / 'case.json'), '--snapshot',
                                   str(FIXTURE / 'snapshot.json'), '--output', str(output)])
                self.assertEqual(status, 2)
                self.assertFalse((output / 'receipt.json').exists())
                inspection = inspect_run(output)
                self.assertEqual(inspection['last_event'], 'run_failed')
                self.assertFalse(inspection['unresolved_attempts'])

    def test_error_immediately_after_receipt_publication_preserves_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            def after_publish(path, payload):
                publish_bytes(path, payload)
                if path.name == 'receipt.json':
                    raise OSError('post-publication cleanup failed')
            with patch('tether_engine.artifacts.publish_bytes', side_effect=after_publish), \
                    patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                status = main(['run', '--case', str(FIXTURE / 'case.json'), '--snapshot',
                               str(FIXTURE / 'snapshot.json'), '--output', str(output)])
            self.assertEqual(status, 2)
            self.assertEqual(inspect_run(output)['last_event'], 'finalize')
            self.assertEqual(verify_run(output, source_roots=(output.parent, FIXTURE))['semantic_consistency'], 'verified')


if __name__ == '__main__':
    unittest.main()
