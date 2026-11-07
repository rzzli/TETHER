"""Synthetic lifecycle tests: every subprocess and socket probe is mocked."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError
from tools.science import registry_content_transport as transport


class RegistryContentTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='b0transport-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'restore'
        (self.root / 'pgdata').mkdir(parents=True)
        secret = self.root / '.local-postgres-secrets/password.txt'
        secret.parent.mkdir()
        secret.write_text('never-log-this-password', encoding='utf-8')
        self.sql = self.base / 'query.sql'
        sql = 'BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSELECT 1;\nROLLBACK;'
        self.sql.write_bytes(sql.encode())
        proof = self.base / 'source-proof.txt'
        proof.write_bytes(b'synthetic source ancestor')
        self.job = {'snapshot_date': '2025-01-01', 'restore_root': str(self.root),
                    'expected_studies': 5, 'port': 55440, 'pins': [self.pin(proof)],
                    'query': {**self.pin(self.sql), 'request': {'sql': sql, 'max_output_bytes': 128}}}
        self.folder = self.base / 'output'
        self.journal = RunJournal(self.base / 'journal', kind='build')
        self.addCleanup(self.journal.close)
        self.commands = []
        self.behaviors = {}
        self.held = set()
        self.release_count = 0
        self.enter_count = 0

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    @contextmanager
    def lease(self, root):
        if root in self.held:
            raise FileExistsError('mock concurrent lease')
        self.held.add(root)
        self.enter_count += 1
        try:
            yield
        finally:
            self.held.remove(root)
            self.release_count += 1

    def create_owner(self, *, external='1234', cluster='1234'):
        (self.root / 'pgdata/postmaster.pid').write_text(
            f'{cluster}\n{self.root / "pgdata"}\n1234567\n55440\n', encoding='utf-8')
        if external is not None:
            (self.folder / 'owned-postmaster.pid').write_text(external, encoding='utf-8')

    def fake_run(self, args, *, env, stdout, stderr, timeout, creationflags):
        name = Path(stdout.name).name.removesuffix('.stdout.log')
        self.commands.append(name)
        self.assertNotIn('never-log-this-password', repr(args))
        behavior = self.behaviors.get(name)
        if behavior:
            return behavior(args, env, stdout, stderr)
        if name in ('status-before', 'status-after'):
            return subprocess.CompletedProcess(args, 3)
        if name == 'start':
            self.assertIn('-WindowStyle Hidden', args[-1])
            self.assertIn('default_transaction_read_only=on', args[-1])
            self.create_owner()
        elif name == 'stop':
            (self.root / 'pgdata/postmaster.pid').unlink()
        elif name == 'metadata':
            self.assertEqual('never-log-this-password', env['PGPASSWORD'])
            self.assertEqual('127.0.0.1', env['PGHOST'])
            stdout.write(json.dumps({'database': 'aact_snapshot', 'studies': 5,
                                    'directory': str(self.root / 'pgdata'), 'port': '55440',
                                    'read_only': 'on'}).encode())
        elif name in ('first', 'repeat'):
            self.assertEqual(str(self.sql), args[-1])
            self.assertIn('default_transaction_read_only=on', env['PGOPTIONS'])
            stdout.write(b'opaque-result-bytes\n')  # No outcome parser belongs here.
        return subprocess.CompletedProcess(args, 0)

    def execute(self, port_side_effect=None):
        def fake_popen(args, **kwargs):
            completed = self.fake_run(args, timeout=330, **kwargs)
            kwargs['stdout'].flush()
            kwargs['stderr'].flush()
            return Mock(poll=Mock(return_value=completed.returncode),
                        wait=Mock(return_value=completed.returncode))
        with patch.object(transport, 'source_lease', self.lease), \
                patch.object(transport.subprocess, 'run', side_effect=self.fake_run), \
                patch.object(transport.subprocess, 'Popen', side_effect=fake_popen), \
                patch.object(transport, '_port_open', side_effect=port_side_effect or [False, False]):
            return transport.run_source(self.job, self.base / 'pg', self.folder, self.journal)

    def lifecycle(self):
        return json.loads((self.folder / 'lifecycle.json').read_text())

    def test_success_two_exact_reads_owned_cleanup_and_no_secret_journal(self):
        result = self.execute()
        self.assertEqual(['status-before', 'start', 'metadata', 'first', 'repeat', 'stop', 'status-after'], self.commands)
        self.assertTrue(result['repeat_identical'])
        self.assertEqual(result['first']['sha256'], result['repeat']['sha256'])
        self.assertTrue(self.lifecycle()['server_stopped'])
        self.assertTrue(self.lifecycle()['port_closed'])
        self.assertEqual(1, self.release_count)
        self.assertFalse(self.held)
        events = read_chain(self.base / 'journal/journal.jsonl')
        self.assertTrue(any(e['details'].get('status') == 'source_reads_complete' for e in events))
        self.assertNotIn('never-log-this-password', (self.base / 'journal/journal.jsonl').read_text())

    def test_existing_running_server_is_never_stopped(self):
        self.behaviors['status-before'] = lambda args, *_: subprocess.CompletedProcess(args, 0)
        with self.assertRaises(ContractError):
            self.execute()
        self.assertEqual(['status-before'], self.commands)
        self.assertFalse(self.lifecycle()['startup_attempted'])
        self.assertEqual(1, self.release_count)

    def test_occupied_port_prevents_start_and_shutdown(self):
        with self.assertRaises(ContractError):
            self.execute([True])
        self.assertEqual(['status-before'], self.commands)

    def test_exclusive_output_prevents_reexecution(self):
        self.folder.mkdir()
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual([], self.commands)
        self.assertEqual(0, self.enter_count)

    def test_concurrent_lease_refuses_dispatch(self):
        self.held.add(self.root)
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual([], self.commands)
        self.assertEqual(0, self.release_count)
        self.assertEqual({self.root}, self.held)
        self.assertEqual('FileExistsError', json.loads((self.folder / 'failure.json').read_text())['error_class'])

    def test_changed_sql_or_source_prevents_start(self):
        self.sql.write_bytes(b'changed')
        with self.assertRaises(ContractError):
            self.execute()
        self.assertEqual([], self.commands)
        self.assertEqual(1, self.release_count)

    def test_invalid_metadata_stops_owned_server_before_results(self):
        def wrong(args, env, stdout, stderr):
            stdout.write(b'{"database":"foreign"}')
            return subprocess.CompletedProcess(args, 0)
        self.behaviors['metadata'] = wrong
        with self.assertRaises(ContractError):
            self.execute()
        self.assertNotIn('first', self.commands)
        self.assertEqual(['stop', 'status-after'], self.commands[-2:])

    def test_query_timeout_stops_owned_server_no_retry(self):
        def timeout(args, *_):
            raise subprocess.TimeoutExpired(args, 330)
        self.behaviors['first'] = timeout
        with self.assertRaises(subprocess.TimeoutExpired):
            self.execute()
        self.assertEqual(1, self.commands.count('first'))
        self.assertNotIn('repeat', self.commands)
        self.assertTrue(self.lifecycle()['server_stopped'])
        self.assertEqual(1, self.release_count)

    def test_keyboard_interrupt_stops_owned_server_no_retry(self):
        def interrupt(*_):
            raise KeyboardInterrupt()
        self.behaviors['first'] = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.execute()
        self.assertEqual('KeyboardInterrupt', self.lifecycle()['primary_error_class'])
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_failed_start_with_owned_pid_cleans_up(self):
        def timeout(args, *_):
            self.create_owner()
            raise subprocess.TimeoutExpired(args, 90)
        self.behaviors['start'] = timeout
        with self.assertRaises(subprocess.TimeoutExpired):
            self.execute()
        self.assertEqual(['status-before', 'start', 'stop', 'status-after'], self.commands)
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_delayed_startup_ownership_settles_before_cleanup(self):
        def interrupt(*_):
            raise KeyboardInterrupt()
        self.behaviors['start'] = interrupt
        with patch.object(transport.time, 'sleep', side_effect=lambda _: self.create_owner()):
            with self.assertRaises(KeyboardInterrupt):
                self.execute()
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_foreign_pid_is_never_stopped(self):
        def foreign(args, *_):
            self.create_owner(external='9999')
            return subprocess.CompletedProcess(args, 0)
        self.behaviors['start'] = foreign
        with self.assertRaises(ContractError):
            self.execute()
        self.assertNotIn('stop', self.commands)
        self.assertEqual('ContractError', self.lifecycle()['cleanup_error_class'])
        self.assertEqual(1, self.release_count)

    def test_first_oversize_read_stops_before_repeat(self):
        def oversize(args, env, stdout, stderr):
            stdout.write(b'x' * 129)
            return subprocess.CompletedProcess(args, 0)
        self.behaviors['first'] = oversize
        with self.assertRaises(ContractError):
            self.execute()
        self.assertNotIn('repeat', self.commands)
        self.assertEqual(129, (self.folder / 'first.stdout.log').stat().st_size)
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_mismatching_reads_fail_and_preserve_both(self):
        def different(args, env, stdout, stderr):
            stdout.write(b'different')
            return subprocess.CompletedProcess(args, 0)
        self.behaviors['repeat'] = different
        with self.assertRaises(ContractError):
            self.execute()
        self.assertTrue((self.folder / 'first.stdout.log').is_file())
        self.assertTrue((self.folder / 'repeat.stdout.log').is_file())
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_sql_changed_during_read_fails_before_repeat(self):
        def change(args, env, stdout, stderr):
            stdout.write(b'opaque-result-bytes\n')
            self.sql.write_bytes(b'changed-during-dispatch')
            return subprocess.CompletedProcess(args, 0)
        self.behaviors['first'] = change
        with self.assertRaises(ContractError):
            self.execute()
        self.assertNotIn('repeat', self.commands)
        self.assertTrue(self.lifecycle()['server_stopped'])

    def test_cleanup_failure_cannot_report_success(self):
        self.behaviors['stop'] = lambda args, *_: subprocess.CompletedProcess(args, 1)
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertFalse(self.lifecycle()['server_stopped'])
        self.assertEqual('RuntimeError', self.lifecycle()['cleanup_error_class'])

    def test_primary_failure_retained_when_cleanup_also_fails(self):
        def timeout(args, *_):
            raise subprocess.TimeoutExpired(args, 330)
        self.behaviors['first'] = timeout
        self.behaviors['stop'] = lambda args, *_: subprocess.CompletedProcess(args, 1)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.execute()
        state = self.lifecycle()
        self.assertEqual('TimeoutExpired', state['primary_error_class'])
        self.assertEqual('RuntimeError', state['cleanup_error_class'])

    def test_port_still_open_after_stop_blocks_success(self):
        with self.assertRaises(ContractError):
            self.execute([False, True])
        self.assertFalse(self.lifecycle()['port_closed'])

    def test_live_output_growth_kills_and_reaps_query_process(self):
        stdout_path, stderr_path = self.base / 'large.out', self.base / 'large.err'
        child = Mock()
        child.poll.return_value = None
        child.wait.return_value = -9
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            stdout.write(b'x' * 129)
            stdout.flush()
            with patch.object(transport.subprocess, 'Popen', return_value=child):
                with self.assertRaises(ContractError):
                    transport._run_bounded(['fake-psql'], env={}, stdout=stdout,
                                           stderr=stderr, timeout=330, cap=128)
        child.kill.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=10)

    def test_live_process_timeout_is_killed_and_reaped(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.return_value = -9
        with (self.base / 'timeout.out').open('wb') as stdout, (self.base / 'timeout.err').open('wb') as stderr:
            with patch.object(transport.subprocess, 'Popen', return_value=child), \
                    patch.object(transport.time, 'monotonic', side_effect=[0, 331]):
                with self.assertRaises(subprocess.TimeoutExpired):
                    transport._run_bounded(['fake-psql'], env={}, stdout=stdout,
                                           stderr=stderr, timeout=330, cap=128)
        child.kill.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=10)

    def test_live_keyboard_interrupt_kills_and_reaps_query(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.return_value = -9
        with (self.base / 'interrupt.out').open('wb') as stdout, (self.base / 'interrupt.err').open('wb') as stderr:
            with patch.object(transport.subprocess, 'Popen', return_value=child), \
                    patch.object(transport.time, 'sleep', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    transport._run_bounded(['fake-psql'], env={}, stdout=stdout,
                                           stderr=stderr, timeout=330, cap=128)
        child.kill.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=10)

    def test_loopback_probe_is_bounded_and_closed(self):
        probe = Mock()
        probe.connect_ex.return_value = 0
        context = Mock()
        context.__enter__ = Mock(return_value=probe)
        context.__exit__ = Mock(return_value=False)
        with patch.object(transport.socket, 'socket', return_value=context):
            self.assertTrue(transport._port_open(55440))
        probe.settimeout.assert_called_once_with(1)
        probe.connect_ex.assert_called_once_with(('127.0.0.1', 55440))
        context.__exit__.assert_called_once()


if __name__ == '__main__':
    unittest.main()
