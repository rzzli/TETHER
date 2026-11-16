"""No transport or models: persistence failures must not become source evidence."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

from tools.science import readiness_sources as sources
from tools.science import run_source_validation_experiment as experiment
from tether_engine.journal import RunJournal
from tether_engine.serde import read_json
from tether_engine.serde import ContractError, decode
from tether_engine.contracts import Snapshot
from tether_engine.provenance import InputGraph, catalog_index
from tests.source_validation_fixtures import author_controls


class UtilityFailureTests(unittest.TestCase):
    def test_evaluator_parent_control_has_an_otherwise_valid_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = author_controls(temporary)
            scenario = read_json(fixture / 'F02' / 'scenario.json')
            base = Path(scenario['snapshot']['raw_root'])
            with self.assertRaisesRegex(ContractError, 'role denied'):
                InputGraph(decode(Snapshot, scenario['snapshot']), base, catalog_index(scenario['catalog']))
            scenario['snapshot']['sources'][-1]['role'] = 'reference'
            scenario['catalog']['datasets'][-1]['roles'] = ['reference']
            graph = InputGraph(decode(Snapshot, scenario['snapshot']), base, catalog_index(scenario['catalog']))
            case = SimpleNamespace(cutoff=experiment.source_inputs.utc(experiment.CUTOFF))
            self.assertIsNone(graph.exclusion(tuple(graph.nodes), case))
            proofs = graph.verify(tuple(graph.nodes), {}, case=case)
            self.assertEqual(len(proofs), 4)

    def terminal_fixture(self, root):
        journal = RunJournal(root / 'attempt', kind='build')
        ledger = {'schema_version': 1, 'status': 'PASS_FICTIONAL_QUALIFICATION_ONLY',
                  'output_cells': [], 'decision_cells': [], 'failure': None}
        return journal.output, journal, ledger

    def test_close_failure_cannot_leave_a_pass_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, journal, ledger = self.terminal_fixture(Path(temporary))
            original = journal.close
            def broken():
                original()
                raise OSError('fixture close failure')
            with patch.object(journal, 'close', side_effect=broken):
                failed, errors = experiment.finalize_ledger(output, journal, ledger)
            self.assertTrue(failed)
            self.assertTrue(errors)
            self.assertEqual(read_json(output / 'ledger.json')['status'], 'PENDING_TERMINAL_SEAL')
            self.assertEqual(read_json(output / 'failure-seal.json')['status'], 'FAILED_PARTIAL_NOT_QUALIFIED')
            self.assertFalse((output / 'seal.json').exists())

    def test_success_is_in_the_bound_seal_not_a_premature_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, journal, ledger = self.terminal_fixture(Path(temporary))
            failed, errors = experiment.finalize_ledger(output, journal, ledger)
            self.assertFalse(failed)
            self.assertFalse(errors)
            saved = read_json(output / 'ledger.json')
            self.assertEqual(saved['status'], 'PENDING_TERMINAL_SEAL')
            self.assertEqual(saved['intended_status'], 'PASS_FICTIONAL_QUALIFICATION_ONLY')
            self.assertEqual(read_json(output / 'seal.json')['status'], saved['intended_status'])

    def attempt(self, root, client):
        self.events = []
        journal = SimpleNamespace(append=lambda event, **details: self.events.append((event, details)))
        now = datetime.fromisoformat(sources.SOURCE_DATE_R).replace(tzinfo=timezone.utc)
        request = {'url': 'https://example.invalid/fixture', 'max_response_bytes': 1024}
        with patch.object(sources, '_now', return_value=now):
            return sources._attempt(journal, root, request, client, 0, time.monotonic()+10, [1024])

    def test_local_open_failure_is_fatal_and_not_source_access_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            client = SimpleNamespace(stream=lambda *a, **k: self.fail('dispatch after local open failure'))
            original = Path.open
            def denied(path, *args, **kwargs):
                if path == root / '00-response.bin':
                    raise PermissionError('fixture disk permission')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'open', new=denied), self.assertRaises(PermissionError):
                self.attempt(root, client)
            self.assertEqual(self.events[-1][1]['hold_reason'], 'local_io_failure')

    def test_remote_access_failure_remains_a_source_failure(self):
        def unavailable(*args, **kwargs):
            raise OSError('fixture remote connection failed')
        with tempfile.TemporaryDirectory() as temporary:
            receipt = self.attempt(Path(temporary), SimpleNamespace(stream=unavailable))
        self.assertEqual(receipt['hold_reason'], 'access_failed')
        self.assertEqual(receipt['outcome'], 'failed')

    def test_local_sync_failure_is_fatal_and_retains_attempt(self):
        def stream(request, **kwargs):
            yield 'headers', {'status': 200, 'final_url': request['url'], 'headers': {}}
            yield 'body', b'fixture'
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(sources.os, 'fsync', side_effect=OSError('fixture disk full')):
                with self.assertRaises(OSError):
                    self.attempt(Path(temporary), SimpleNamespace(stream=stream))
        self.assertEqual(self.events[-1][1]['hold_reason'], 'local_io_failure')
