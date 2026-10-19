"""Peer lifecycle regression probes. Every process/socket is mocked.

Plan/schema/query validation has its own tests; bypass it here to isolate ownership
and durable failure reporting before any source-row extraction can happen.
"""
import contextlib
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tools.science.outcome_extract as runner
from asof.journal import read_chain
from asof.serde import ContractError, fingerprint, sha256_file, write_json
from tools.science.outcome_inputs import (candidate_query, schema_from_audit,
                                         study_query)


def executing_code_pins():
    project = Path(runner.__file__).resolve().parents[2]
    names = ('tools/science/outcome_extract.py', 'tools/science/outcome_inputs.py',
             'tools/science/ascertainment_policy.py', 'tools/science/origin_programs.py',
             'tools/science/reference_panel.py', 'src/asof/serde.py', 'src/asof/journal.py')
    return [{'path': str((project / name).resolve()),
             'sha256': sha256_file(project / name),
             'bytes': (project / name).stat().st_size} for name in names]


class LifecyclePeerTests(unittest.TestCase):
    def fixture(self, root):
        restore = root / 'restore'
        for folder in ('extracted', 'pgdata', '.local-postgres-secrets'):
            (restore / folder).mkdir(parents=True, exist_ok=True)
        (restore / '.local-postgres-secrets/password.txt').write_text('fixture-only')
        dump = restore / 'extracted/postgres.dmp'
        dump.write_bytes(b'fixture dump; never opened by PostgreSQL')
        toc = restore / 'dump-toc-pg17.txt'
        toc.write_text('; Archive created at 2025-01-01 00:00:00 UTC\n')
        query = root / 'query.sql'
        query.write_text('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSELECT 1;\nROLLBACK;\n')
        def pin(path):
            return {'path': str(path.resolve()), 'sha256': sha256_file(path),
                    'bytes': path.stat().st_size}
        plan = {
            'schema_version': 1, 'protocol_id': 'science4-outcome-inputs-v1',
            'role': 'evaluation_only', 'provider_spend_usd': 0,
            'clinical_activation': False, 'origin_at': '2025-01-01T00:00:00Z',
            'horizon_at': '2026-01-01T00:00:00Z',
            'ascertainment_at': '2026-04-01T00:00:00Z',
            'phase': 'origin_design', 'nct_ids': [f'NCT{i:08d}' for i in range(1, 13)],
            'parents': [], 'executed_code': executing_code_pins(),
            'pg_bin': str(root / 'fake-bin'),
            'jobs': [{'snapshot_date': '2025-01-01', 'port': 55439,
                      'expected_studies': 520688, 'restore_root': str(restore),
                      'pins': [pin(dump), pin(toc)],
                      'queries': [{**pin(query), 'name': 'fixture'}]}],
        }
        plan_path = root / 'plan.json'
        write_json(plan_path, plan)
        return plan_path, restore

    def run_failure(self, root, fake_dispatch, error=Exception):
        plan, restore = self.fixture(root)
        sock = MagicMock()
        sock.__enter__.return_value.connect_ex.return_value = 1
        lease_events = []
        @contextlib.contextmanager
        def lease(_):
            lease_events.append('entered')
            try:
                yield
            finally:
                lease_events.append('released')
        with patch.object(runner, 'validate_plan'), \
                patch.object(runner, 'validate_binding'), \
                patch.object(runner, 'source_lease', lease), \
                patch.object(runner.socket, 'socket', return_value=sock), \
                patch.object(runner.subprocess, 'run',
                             side_effect=lambda args, **kw: fake_dispatch(restore, args, kw)):
            with self.assertRaises(error):
                runner.extract(plan, sha256_file(plan), root / 'out')
        self.assertEqual(lease_events, ['entered', 'released'])
        self.assertTrue((root / 'out/failure.json').is_file())
        self.assertFalse((root / 'out/report.json').exists())
        self.assertEqual(read_chain(root / 'out/journal.jsonl')[-1]['event'], 'build_failed')
        return restore

    @staticmethod
    def write_postmaster(restore, pid='12345'):
        # PostgreSQL PID-file lines: pid, data directory, start epoch, port.
        (restore / 'pgdata/postmaster.pid').write_text(
            f'{pid}\n{restore / "pgdata"}\n1\n55439\n')

    @staticmethod
    def owned_start(restore, args):
        LifecyclePeerTests.write_postmaster(restore)
        # Support a per-run external PID file if the runner adds that ownership
        # commitment. This writes fixture bytes only, never a real process PID.
        command = ' '.join(str(x) for x in args)
        match = re.search(r'external_pid_file=([^\s\"\']+)', command)
        if match:
            token = Path(match.group(1))
            token.parent.mkdir(parents=True, exist_ok=True)
            token.write_text('12345\n')

    def test_existing_running_server_is_never_stopped(self):
        calls = []
        def dispatch(restore, args, kw):
            calls.append(args)
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            self.run_failure(Path(tmp), dispatch, ContractError)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-1], 'status')

    def test_metadata_failure_stops_owned_server_and_preserves_failure(self):
        calls = []
        def dispatch(restore, args, kw):
            calls.append(args)
            if args[-1] == 'status':
                return SimpleNamespace(returncode=3)
            if args[0] == 'powershell.exe':
                self.owned_start(restore, args)
            elif args[-1] == 'stop':
                (restore / 'pgdata/postmaster.pid').unlink()
            elif '-c' in args:
                kw['stdout'].write(json.dumps({
                    'database': 'wrong_database', 'studies': 520688,
                    'directory': str(restore / 'pgdata'), 'port': '55439',
                    'read_only': 'on'}).encode())
            else:
                self.fail('Source query dispatched after bad metadata')
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_failure(root, dispatch, ContractError)
            lifecycle = json.loads((root / 'out/2025-01-01/lifecycle.json').read_text())
            self.assertTrue(lifecycle['server_stopped'])
        self.assertEqual(sum(args[-1] == 'stop' for args in calls), 1)
        self.assertFalse(any('-f' in args for args in calls))

    def test_cleanup_failure_is_durable_and_cannot_be_a_success(self):
        def dispatch(restore, args, kw):
            if args[-1] == 'status':
                return SimpleNamespace(returncode=3)
            if args[0] == 'powershell.exe':
                self.owned_start(restore, args)
            elif args[-1] == 'stop':
                return SimpleNamespace(returncode=1)
            elif '-c' in args:
                kw['stdout'].write(b'not valid metadata JSON')
            else:
                self.fail('Unexpected source query')
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_failure(root, dispatch)
            events = read_chain(root / 'out/journal.jsonl')
            self.assertTrue(any(x['event'] == 'build_cleanup_failed' for x in events))
            lifecycle = json.loads((root / 'out/2025-01-01/lifecycle.json').read_text())
            self.assertFalse(lifecycle['server_stopped'])

    def test_failed_start_must_not_stop_unowned_same_port_postmaster(self):
        calls = []
        def dispatch(restore, args, kw):
            calls.append(args)
            if args[-1] == 'status':
                return SimpleNamespace(returncode=3)
            if args[0] == 'powershell.exe':
                # Another launcher won after status-before. Our startup fails,
                # and no per-run ownership token was created by our launch.
                self.write_postmaster(restore, pid='54321')
                return SimpleNamespace(returncode=1)
            if args[-1] == 'stop':
                return SimpleNamespace(returncode=0)
            self.fail('Query dispatched after failed startup')
        with tempfile.TemporaryDirectory() as tmp:
            self.run_failure(Path(tmp), dispatch)
        self.assertFalse(any(args[-1] == 'stop' for args in calls),
                         'A matching port does not prove this run owns the server')

    def test_changed_postmaster_pid_refuses_shutdown_even_with_owned_pid_file(self):
        calls = []
        def dispatch(restore, args, kw):
            calls.append(args)
            if args[-1] == 'status':
                return SimpleNamespace(returncode=3)
            if args[0] == 'powershell.exe':
                self.owned_start(restore, args)
                self.write_postmaster(restore, pid='54321')
            elif '-c' in args:
                kw['stdout'].write(b'invalid metadata')
            elif args[-1] == 'stop':
                self.fail('Different postmaster PID must not be shut down')
            else:
                self.fail('Unexpected query')
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_failure(root, dispatch)
            self.assertTrue(any(x['event'] == 'build_cleanup_failed'
                                for x in read_chain(root / 'out/journal.jsonl')))
            lifecycle = json.loads((root / 'out/2025-01-01/lifecycle.json').read_text())
            self.assertFalse(lifecycle['server_stopped'])
        self.assertFalse(any(args[-1] == 'stop' for args in calls))


class BindingPeerTests(unittest.TestCase):
    """Synthetic source/schema receipts prove semantic binding, not just hashes."""

    @staticmethod
    def pin(path):
        return {'path': str(path.resolve()), 'sha256': sha256_file(path),
                'bytes': path.stat().st_size}

    def fixture(self, root):
        def json_file(name, value):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, value)
            return path
        ids = [f'NCT{i:08d}' for i in range(1, 13)]
        policy = json_file('policy.json', {'synthetic_fixture': True})
        packet_pins = [self.pin(json_file(f'packets/{nct}.json', {
            'origin_scope': {'nct_id': nct}})) for nct in ids]
        pack = json_file('pack.json', {'clinical_labels_assigned': 0,
            'selected_distinct_trials': 12, 'files': packet_pins})
        aliases = {nct: [f'fixture-product-{index}']
                   for index, nct in enumerate(ids)}
        alias_path = json_file('aliases.json', {
            'origin_pack_sha256': sha256_file(pack),
            'followup_sources_read': False, 'aliases_by_origin': aliases})
        amendment = json_file('amendment.json', {
            'parent_protocol_sha256': sha256_file(policy),
            'endpoint_cohort_queries_performed': 0,
            'new_caps': {'per_origin_trial': 5000,
                         'total_distinct_trials': 20000}})
        restore = root / 'restores/origin'
        (restore / 'extracted').mkdir(parents=True)
        dump = restore / 'extracted/postgres.dmp'
        dump.write_bytes(b'synthetic dump; never sent to any process')
        source_schema = {
            'studies': ['nct_id'],
            'interventions': ['id', 'nct_id', 'intervention_type', 'name'],
        }
        audit = {'status': 'completed', 'study_id_check': {'rows': 520688},
                 'columns': [{'table_schema': 'ctgov', 'table_name': table,
                              'column_name': column}
                             for table, columns in source_schema.items()
                             for column in columns]}
        for name, value in (
                ('archive-inspection.json', {'members': [{
                    'name': 'postgres.dmp', 'sha256': sha256_file(dump)}]}),
                ('technical-audit.json', audit)):
            write_json(restore / name, value)
        for name, text in (
                ('dump-toc-pg17.txt', '; Archive created at 2025-01-01 00:00:00 UTC\n'),
                ('schema-pg17.sql', '-- synthetic schema metadata\n'),
                ('setup.py', '# synthetic restoration provenance\n')):
            (restore / name).write_text(text)
        schema = schema_from_audit(audit)
        requests = {
            'studies': study_query(ids, '2025-01-01', schema, max_ids=12),
            'candidates': candidate_query(aliases, '2025-01-01', schema,
                                        per_origin_cap=5000, total_cap=20000),
        }
        queries = []
        for name, request in requests.items():
            q = root / (name + '.sql')
            q.write_text(request['sql'], encoding='utf-8')
            queries.append({**self.pin(q), 'name': name, 'request': request})
        source_names = ('extracted/postgres.dmp', 'archive-inspection.json',
                        'dump-toc-pg17.txt', 'technical-audit.json',
                        'schema-pg17.sql', 'setup.py')
        plan = {
            'schema_version': 1, 'protocol_id': 'science4-outcome-inputs-v1',
            'role': 'evaluation_only', 'provider_spend_usd': 0,
            'clinical_activation': False, 'origin_at': '2025-01-01T00:00:00Z',
            'horizon_at': '2026-01-01T00:00:00Z',
            'ascertainment_at': '2026-04-01T00:00:00Z',
            'phase': 'origin_design', 'nct_ids': ids,
            'review_policy': self.pin(policy), 'selection': self.pin(pack),
            'alias_dictionary': self.pin(alias_path),
            'cap_amendment': self.pin(amendment), 'parents': [],
            'executed_code': executing_code_pins(),
            'pg_bin': str(root / 'fake-bin'),
            'jobs': [{'snapshot_date': '2025-01-01', 'port': 55439,
                      'expected_studies': 520688, 'restore_root': str(restore),
                      'pins': [self.pin(restore / n) for n in source_names],
                      'queries': queries}],
        }
        patches = {'APPROVED_BASE': root / 'restores',
                   'APPROVED_RESTORES': {'2025-01-01': 'origin'},
                   'PACK_SHA256': sha256_file(pack),
                   'POLICY_SHA256': sha256_file(policy)}
        return plan, patches

    def replace_request(self, plan, name, request):
        query = next(q for q in plan['jobs'][0]['queries'] if q['name'] == name)
        path = Path(query['path'])
        path.write_text(request['sql'], encoding='utf-8')
        query.update(self.pin(path), request=request)

    def rejected_before_dispatch(self, root, plan, patches, message):
        plan_path = root / 'dispatch-plan.json'
        write_json(plan_path, plan)
        with patch.multiple(runner, **patches), \
                patch.object(runner.subprocess, 'run') as process:
            with self.assertRaisesRegex(ContractError, message):
                runner.extract(plan_path, sha256_file(plan_path), root / 'out')
            process.assert_not_called()
        self.assertFalse((root / 'out/report.json').exists())
        self.assertTrue((root / 'out/failure.json').is_file())
        self.assertEqual(read_chain(root / 'out/journal.jsonl')[-1]['event'], 'build_failed')

    def test_valid_synthetic_twelve_member_source_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, patches = self.fixture(Path(tmp))
            with patch.multiple(runner, **patches), \
                    patch.object(runner.subprocess, 'run') as process:
                runner.validate_plan(plan)
                runner.validate_binding(plan)
                process.assert_not_called()

    def test_rehashed_wrong_study_members_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            request = plan['jobs'][0]['queries'][0]['request']
            ids = list(plan['nct_ids']); ids[0] = 'NCT99999999'
            self.replace_request(plan, 'studies', study_query(
                ids, '2025-01-01', request['source_schema'], max_ids=12))
            self.rejected_before_dispatch(root, plan, patches, 'actual twelve members')

    def test_rehashed_wrong_request_snapshot_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            schema = plan['jobs'][0]['queries'][0]['request']['source_schema']
            self.replace_request(plan, 'studies', study_query(
                plan['nct_ids'], '2026-01-01', schema, max_ids=12))
            self.rejected_before_dispatch(root, plan, patches, 'schema/snapshot')

    def test_rehashed_changed_aliases_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            request = plan['jobs'][0]['queries'][1]['request']
            aliases = copy.deepcopy(request['aliases_by_origin'])
            aliases[plan['nct_ids'][0]] = ['different-valid-product']
            self.replace_request(plan, 'candidates', candidate_query(
                aliases, '2025-01-01', request['source_schema'],
                per_origin_cap=5000, total_cap=20000))
            self.rejected_before_dispatch(root, plan, patches, 'frozen aliases or explicit caps')

    def test_rehashed_changed_caps_rejected_before_process(self):
        for per_origin, total in ((20, 20000), (5000, 200)):
            with self.subTest(per_origin=per_origin, total=total), \
                    tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); plan, patches = self.fixture(root)
                request = plan['jobs'][0]['queries'][1]['request']
                self.replace_request(plan, 'candidates', candidate_query(
                    request['aliases_by_origin'], '2025-01-01',
                    request['source_schema'], per_origin_cap=per_origin,
                    total_cap=total))
                self.rejected_before_dispatch(root, plan, patches, 'frozen aliases or explicit caps')

    def test_rehashed_fabricated_schema_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            schema = copy.deepcopy(plan['jobs'][0]['queries'][0]['request']['source_schema'])
            schema['studies'].append('phase')
            self.replace_request(plan, 'studies', study_query(
                plan['nct_ids'], '2025-01-01', schema, max_ids=12))
            self.rejected_before_dispatch(root, plan, patches, 'schema/snapshot')

    def test_rehashed_free_sql_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            request = copy.deepcopy(plan['jobs'][0]['queries'][0]['request'])
            request['sql'] = request['sql'].replace('ROLLBACK;',
                'COMMIT; DELETE FROM ctgov.studies; ROLLBACK;')
            request['request_sha256'] = fingerprint({
                k: v for k, v in request.items() if k != 'request_sha256'})
            self.replace_request(plan, 'studies', request)
            self.rejected_before_dispatch(root, plan, patches, 'deterministic regeneration')

    def test_rehashed_reduced_projection_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); plan, patches = self.fixture(root)
            schema = plan['jobs'][0]['queries'][0]['request']['source_schema']
            self.replace_request(plan, 'studies', study_query(
                plan['nct_ids'], '2025-01-01', schema, max_ids=12,
                requested_columns={'studies': ['nct_id']}))
            self.rejected_before_dispatch(root, plan, patches, 'actual twelve members')


if __name__ == '__main__':
    unittest.main()
