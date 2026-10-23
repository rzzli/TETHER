"""Independent synthetic origin-receipt attacks; no database/source outcomes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.journal import RunJournal
from asof.serde import ContractError, fingerprint, write_json
from tools.science.registry_content import FIELDS, classify_content, content_query
from tools.science import registry_content_workflow as flow


class RegistryContentWorkflowPeerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='b0receipt-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.run = self.base / 'run'
        self.stage = self.run / '2025-01-01'
        self.restore = self.base / 'restore'
        self.pg = self.base / 'pg'
        self.request = content_query(['NCT00000001'], '2025-01-01',
                                     {k: list(v) for k, v in FIELDS.items()})
        self.prepared = self.base / 'prepared'
        self.prepared.mkdir()
        self.sql = self.prepared / '2025-01-01.sql'
        self.sql.write_bytes(self.request['sql'].encode())
        self.code = self.base / 'runner.py'
        self.code.write_text('# synthetic code\n')
        self.plan = {'protocol_id': 'registry-content-execution-v0.1', 'mode': 'origin',
                     'pg_bin': str(self.pg), 'clinical_activation': False,
                     'scoring_activation': False, 'provider_spend_usd': 0, 'model_calls': 0,
                     'code': [flow.pin(self.code)], 'runtime_pins': [],
                     'jobs': [{'snapshot_date': '2025-01-01', 'restore_root': str(self.restore),
                               'port': 55440, 'expected_studies': 5,
                               'query': {**flow.pin(self.sql), 'request': self.request}}]}
        self.meta = {'database': 'aact_snapshot', 'studies': 5,
                     'directory': str(self.restore / 'pgdata'), 'port': '55440', 'read_only': 'on'}
        self.envelope = {'study': {'nct_id': 'NCT00000001', 'last_update_posted_date': '2024-12-20',
                                  'last_update_posted_date_type': 'ACTUAL',
                                  'results_first_posted_date': None, 'results_first_posted_date_type': None},
                         'outcomes': [], 'result_groups': [], 'outcome_measurements': [],
                         'table_counts': {'outcomes': 0, 'result_groups': 0, 'outcome_measurements': 0}}

    def fixture(self, mutate=None, command_order=None, wrong_query=False, corrupt_code=False,
                wrong_stdout_count=False, missing_stderr_count=False):
        journal = RunJournal(self.run, kind='build')
        self.stage.mkdir()
        plan_path = self.prepared / 'plan.json'
        write_json(plan_path, self.plan)
        write_json(self.run / 'effective-plan.json', self.plan)
        for name in ('first', 'repeat'):
            (self.stage / (name + '.stdout.log')).write_text(json.dumps(self.envelope) + '\n')
        write_json(self.stage / 'metadata.stdout.log', self.meta)
        lifecycle = {'startup_attempted': True, 'server_stopped': True, 'port_closed': True,
                     'port': 55440, 'automatic_retry': False,
                     'primary_error_class': None, 'cleanup_error_class': None}
        write_json(self.stage / 'lifecycle.json', lifecycle)
        write_json(self.stage / 'state-proposals.json', classify_content([self.envelope], self.request))
        archived = self.run / 'executed-code/runner.py'
        archived.parent.mkdir()
        archived.write_bytes(self.code.read_bytes())
        write_json(self.run / 'executed-code-proofs.json', [{'source': flow.pin(self.code), 'copy': flow.pin(archived)}])
        if corrupt_code:
            archived.write_bytes(b'changed executing code')
        result = {'snapshot_date': '2025-01-01', 'repeat_identical': True,
                  'first': flow.pin(self.stage / 'first.stdout.log'),
                  'repeat': flow.pin(self.stage / 'repeat.stdout.log'),
                  'metadata_file': flow.pin(self.stage / 'metadata.stdout.log'), 'metadata': self.meta,
                  'lifecycle': flow.pin(self.stage / 'lifecycle.json'),
                  'state_proposals': flow.pin(self.stage / 'state-proposals.json'),
                  'request_sha256': self.request['contract_sha256']}
        report = {'schema_version': 1, 'status': 'source_bound_snapshot_reads_completed',
                  'role': 'evaluation_only', 'mode': 'origin', 'plan': flow.pin(plan_path),
                  'effective_plan': flow.pin(self.run / 'effective-plan.json'), 'results': [result],
                  'executed_code_proofs': flow.pin(self.run / 'executed-code-proofs.json'),
                  'clinical_labels_assigned': 0, 'clinical_activation': False,
                  'provider_spend_usd': 0, 'model_calls': 0}
        if mutate:
            mutate(report)
        data = str(self.restore / 'pgdata')
        ctl = str(self.pg / 'pg_ctl.exe').replace("'", "''")
        options = (f'-p 55440 -c listen_addresses=127.0.0.1 -c default_transaction_read_only=on '
                   f'-c external_pid_file={(self.stage / "owned-postmaster.pid").as_posix()}')
        args = ['-D', data, '-l', str(self.stage / 'server.log'), '-o', options, '-w', '-t', '45', 'start']
        arglist = ','.join("'\"" + arg.replace("'", "''") + "\"'" for arg in args)
        metadata_sql = ("SELECT json_build_object('database',current_database(),"
                        "'studies',(SELECT count(*) FROM ctgov.studies),"
                        "'directory',current_setting('data_directory'),'port',current_setting('port'),"
                        "'read_only',current_setting('transaction_read_only'));")
        commands = {
            'status-before': [str(self.pg / 'pg_ctl.exe'), '-D', data, 'status'],
            'start': ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                      f"$b0Process=Start-Process -FilePath '{ctl}' -ArgumentList @({arglist}) "
                      '-WindowStyle Hidden -PassThru; $b0Process.WaitForExit(); exit $b0Process.ExitCode'],
            'metadata': [str(self.pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-c', metadata_sql],
            'first': [str(self.pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', str(self.sql)],
            'repeat': [str(self.pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', str(self.sql)],
            'stop': [str(self.pg / 'pg_ctl.exe'), '-D', data, '-m', 'fast', '-w', '-t', '45', 'stop'],
            'status-after': [str(self.pg / 'pg_ctl.exe'), '-D', data, 'status']}
        if wrong_query:
            commands['first'][-1] = str(self.base / 'different-query.sql')
        for name in command_order or commands:
            stdout_path = self.stage / (name + '.stdout.log')
            stderr_path = self.stage / (name + '.stderr.log')
            if not stdout_path.exists():
                stdout_path.write_bytes(b'')
            stderr_path.write_bytes(b'')
            journal.append('build_progress', stage='2025-01-01', command=name, status='started',
                           arguments=commands[name], timeout_seconds=330 if name in ('first', 'repeat') else 90)
            finished = {'stage': '2025-01-01', 'command': name, 'status': 'finished',
                        'returncode': 3 if name.startswith('status-') else 0,
                        'stdout_bytes': stdout_path.stat().st_size,
                        'stderr_bytes': stderr_path.stat().st_size}
            if wrong_stdout_count and name == 'first':
                finished['stdout_bytes'] += 1
            if missing_stderr_count and name == 'first':
                del finished['stderr_bytes']
            journal.append('build_progress', **finished)
        journal.append('build_progress', stage='2025-01-01', status='source_reads_complete',
                       server_stopped=True, port_closed=True)
        write_json(self.run / 'report.json', report)
        journal.append('build_completed', report=flow.pin(self.run / 'report.json'))
        journal.close()

    def verify(self):
        # Source validation is an orthogonal, previously reviewed boundary. This
        # fixture isolates what verify_origin_run adds after a plan is validated.
        with patch.object(flow, 'validate_plan'), patch.object(flow, 'ROOT', self.base):
            return flow.verify_origin_run(self.run)

    def test_valid_synthetic_receipt_is_accepted(self):
        self.fixture()
        _, _, states = self.verify()
        self.assertEqual('absent_in_snapshot', states['records'][0]['state'])

    def test_followup_plan_cannot_be_relabelled_origin_receipt(self):
        self.plan['mode'] = 'followup'
        self.plan['jobs'][0]['snapshot_date'] = '2026-01-01'
        self.request = content_query(['NCT00000001'], '2026-01-01',
                                     {k: list(v) for k, v in FIELDS.items()})
        self.sql = self.prepared / '2026-01-01.sql'
        self.sql.write_bytes(self.request['sql'].encode())
        self.plan['jobs'][0]['query'] = {**flow.pin(self.sql), 'request': self.request}
        april = copy.deepcopy(self.plan['jobs'][0])
        april['snapshot_date'] = '2026-04-01'
        request = content_query(['NCT00000001'], '2026-04-01',
                                {k: list(v) for k, v in FIELDS.items()})
        path = self.prepared / '2026-04-01.sql'
        path.write_bytes(request['sql'].encode())
        april['query'] = {**flow.pin(path), 'request': request}
        self.plan['jobs'].append(april)
        self.fixture()
        with self.assertRaises(ContractError):
            self.verify()

    def test_copied_metadata_receipt_locator_is_rejected(self):
        def move(report):
            foreign = self.base / 'foreign-metadata.json'
            write_json(foreign, self.meta)
            report['results'][0]['metadata_file'] = flow.pin(foreign)
        self.fixture(mutate=move)
        with self.assertRaises(ContractError):
            self.verify()

    def test_unrelated_query_command_is_rejected(self):
        self.fixture(wrong_query=True)
        with self.assertRaises(ContractError):
            self.verify()

    def test_commands_in_impossible_order_are_rejected(self):
        self.fixture(command_order=['status-before', 'stop', 'start', 'metadata', 'first', 'repeat', 'status-after'])
        with self.assertRaises(ContractError):
            self.verify()

    def test_conflicting_request_digest_is_rejected(self):
        self.fixture(mutate=lambda r: r['results'][0].update(request_sha256='0' * 64))
        with self.assertRaises(ContractError):
            self.verify()

    def test_changed_archived_execution_code_is_rejected(self):
        self.fixture(corrupt_code=True)
        with self.assertRaises(ContractError):
            self.verify()

    def test_wrong_lifecycle_port_is_rejected(self):
        def wrong(report):
            target = self.stage / 'lifecycle.json'
            state = json.loads(target.read_text())
            state['port'] = 55555
            write_json(target, state)
            report['results'][0]['lifecycle'] = flow.pin(target)
        self.fixture(mutate=wrong)
        with self.assertRaises(ContractError):
            self.verify()

    def test_activated_clinical_report_is_rejected(self):
        self.fixture(mutate=lambda r: r.update(clinical_activation=True, clinical_labels_assigned=1))
        with self.assertRaises(ContractError):
            self.verify()

    def test_self_resealed_unknown_cannot_be_promoted_to_eligible_absence(self):
        self.envelope['study']['last_update_posted_date'] = None
        def forge(report):
            path = self.stage / 'state-proposals.json'
            states = json.loads(path.read_text())
            states['records'][0]['state'] = 'absent_in_snapshot'
            states['records'][0]['reasons'] = []
            states['contract_sha256'] = fingerprint({k: v for k, v in states.items()
                                                     if k != 'contract_sha256'})
            write_json(path, states)
            report['results'][0]['state_proposals'] = flow.pin(path)
        self.fixture(mutate=forge)
        with self.assertRaises(ContractError):
            self.verify()

    def test_rehashed_repeat_cannot_replace_identical_read(self):
        def forge(report):
            path = self.stage / 'repeat.stdout.log'
            row = copy.deepcopy(self.envelope)
            row['study']['last_update_posted_date'] = '2024-12-19'
            path.write_text(json.dumps(row) + '\n')
            report['results'][0]['repeat'] = flow.pin(path)
        self.fixture(mutate=forge)
        with self.assertRaises(ContractError):
            self.verify()

    def test_first_stdout_count_must_match_retained_bytes(self):
        self.fixture(wrong_stdout_count=True)
        with self.assertRaises(ContractError):
            self.verify()

    def test_missing_stderr_count_cannot_claim_complete_command_receipt(self):
        self.fixture(missing_stderr_count=True)
        with self.assertRaises(ContractError):
            self.verify()


if __name__ == '__main__':
    unittest.main()
