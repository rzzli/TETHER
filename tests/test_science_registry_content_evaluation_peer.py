"""Synthetic B0 evaluator attacks; source admission is isolated with mocks."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, fingerprint, write_json
from tools.science.registry_content import FIELDS, classify_content, content_query
from tools.science import registry_content_evaluation as evaluation


class RegistryContentEvaluationPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='b0evalpeer-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'followup'
        self.prepared = self.base / 'prepared'
        self.prepared.mkdir()
        self.nct = 'NCT00000001'
        self.membership = {'nct_ids': [self.nct]}
        path = self.base / 'membership.json'
        write_json(path, self.membership)
        self.membership_pin = evaluation.pin(path)
        self.pg = self.base / 'pg'

    def envelope(self, snapshot, present=False):
        row = {'study': {'nct_id': self.nct, 'last_update_posted_date': '2025-12-20',
                         'last_update_posted_date_type': 'ACTUAL', 'results_first_posted_date': None,
                         'results_first_posted_date_type': None},
               'outcomes': [], 'result_groups': [], 'outcome_measurements': []}
        if present:
            row['study'].update(last_update_posted_date='2026-03-20',
                                results_first_posted_date='2026-02-20',
                                results_first_posted_date_type='ACTUAL')
            row['outcomes'] = [{'nct_id': self.nct, 'id': 1}]
            row['result_groups'] = [{'nct_id': self.nct, 'id': 2, 'outcome_id': 1,
                                     'ctgov_group_code': 'OG1'}]
            row['outcome_measurements'] = [{'nct_id': self.nct, 'id': 3, 'outcome_id': 1,
                                           'result_group_id': 2, 'ctgov_group_code': 'OG1'}]
        row['table_counts'] = {t: len(row[t]) for t in ('outcomes', 'result_groups', 'outcome_measurements')}
        return row

    def fixture(self, mutate=None, journal_attack=None):
        journal = RunJournal(self.root, kind='build')
        source = self.base / 'runner.py'
        source.write_text('# fake source\n')
        archive = self.root / 'executed-code/runner.py'
        archive.parent.mkdir()
        archive.write_bytes(source.read_bytes())
        write_json(self.root / 'executed-code-proofs.json',
                   [{'source': evaluation.pin(source), 'copy': evaluation.pin(archive)}])
        plan = {'mode': 'followup', 'membership': self.membership_pin, 'nct_ids': [self.nct],
                'pg_bin': str(self.pg), 'code': [evaluation.pin(source)], 'jobs': []}
        results = []
        logs = []
        for snapshot, count in [('2026-01-01', 100), ('2026-04-01', 200)]:
            folder = self.root / snapshot
            folder.mkdir()
            request = content_query([self.nct], snapshot, {k: list(v) for k, v in FIELDS.items()})
            sql = self.prepared / (snapshot + '.sql')
            sql.write_bytes(request['sql'].encode())
            job = {'snapshot_date': snapshot, 'restore_root': str(self.base / ('restore-' + snapshot)),
                   'port': 55441 if snapshot == '2026-01-01' else 55442, 'expected_studies': count,
                   'query': {**evaluation.pin(sql), 'request': request}}
            plan['jobs'].append(job)
            row = self.envelope(snapshot, present=snapshot == '2026-04-01')
            for repeat in ('first', 'repeat'):
                (folder / (repeat + '.stdout.log')).write_text(json.dumps(row) + '\n')
            meta = {'database': 'aact_snapshot', 'studies': count,
                    'directory': str(Path(job['restore_root']) / 'pgdata'),
                    'port': str(job['port']), 'read_only': 'on'}
            write_json(folder / 'metadata.stdout.log', meta)
            write_json(folder / 'lifecycle.json', {'startup_attempted': True, 'server_stopped': True,
                'port_closed': True, 'port': job['port'], 'automatic_retry': False,
                'primary_error_class': None, 'cleanup_error_class': None})
            write_json(folder / 'state-proposals.json', classify_content([row], request))
            result = {key: evaluation.pin(folder / name) for key, name in [
                ('first', 'first.stdout.log'), ('repeat', 'repeat.stdout.log'),
                ('metadata_file', 'metadata.stdout.log'), ('state_proposals', 'state-proposals.json'),
                ('lifecycle', 'lifecycle.json')]}
            result.update(snapshot_date=snapshot, repeat_identical=True, metadata=meta,
                          request_sha256=request['contract_sha256'])
            results.append(result)
            for name, args in evaluation.commands(job, self.pg, folder).items():
                stdout, stderr = folder / (name + '.stdout.log'), folder / (name + '.stderr.log')
                if not stdout.exists():
                    stdout.write_bytes(b'')
                stderr.write_bytes(b'')
                logs.append({'stage': snapshot, 'command': name, 'status': 'started',
                             'arguments': args, 'timeout_seconds': 330 if name in ('first', 'repeat') else 90})
                logs.append({'stage': snapshot, 'command': name, 'status': 'finished',
                             'returncode': 3 if name.startswith('status-') else 0,
                             'stdout_bytes': stdout.stat().st_size, 'stderr_bytes': stderr.stat().st_size})
        plan_path = self.prepared / 'plan.json'
        write_json(plan_path, plan)
        write_json(self.root / 'effective-plan.json', plan)
        report = {'status': 'source_bound_snapshot_reads_completed', 'mode': 'followup',
                  'role': 'evaluation_only', 'clinical_activation': False, 'clinical_labels_assigned': 0,
                  'provider_spend_usd': 0, 'model_calls': 0, 'plan': evaluation.pin(plan_path),
                  'effective_plan': evaluation.pin(self.root / 'effective-plan.json'),
                  'executed_code_proofs': evaluation.pin(self.root / 'executed-code-proofs.json'),
                  'results': results}
        if mutate:
            mutate(report, plan)
        if journal_attack:
            journal_attack(logs)
        for row in logs:
            journal.append('build_progress', **row)
        write_json(self.root / 'report.json', report)
        proof = evaluation.pin(self.root / 'report.json')
        journal.append('build_completed', report=proof)
        journal.close()
        return proof

    def verify(self, proof):
        with patch.object(evaluation, 'ROOT', self.base), \
                patch.object(evaluation, 'validate_plan'), \
                patch.object(evaluation, 'verify_membership', return_value=self.membership):
            return evaluation.verify_followup(proof, self.membership_pin)

    def test_valid_two_source_receipt_and_native_audit(self):
        frames, _ = self.verify(self.fixture())
        self.assertEqual(['2026-01-01', '2026-04-01'], list(frames))
        self.assertEqual('absent_in_snapshot', frames['2026-01-01']['states']['records'][0]['state'])
        self.assertEqual('present', frames['2026-04-01']['states']['records'][0]['state'])
        audit = evaluation.audit_native_rows([self.nct], frames)
        self.assertEqual(2, len(audit))
        self.assertTrue(all(row['native_locator']['line_1based'] == 1 for row in audit))

    def test_reversed_sources_rejected(self):
        proof = self.fixture(mutate=lambda r, _: r['results'].reverse())
        with self.assertRaises(ContractError):
            self.verify(proof)

    def test_april_receipt_cannot_supply_january_rows(self):
        def swap(report, _):
            report['results'][0]['first'] = report['results'][1]['first']
        with self.assertRaises(ContractError):
            self.verify(self.fixture(mutate=swap))

    def test_plan_cannot_use_other_membership_seal(self):
        def change(report, plan):
            other = self.base / 'different-membership.json'
            write_json(other, self.membership)
            plan['membership'] = evaluation.pin(other)
            path = Path(report['plan']['path'])
            write_json(path, plan)
            report['plan'] = evaluation.pin(path)
            write_json(self.root / 'effective-plan.json', plan)
            report['effective_plan'] = evaluation.pin(self.root / 'effective-plan.json')
        with self.assertRaises(ContractError):
            self.verify(self.fixture(mutate=change))

    def test_global_command_order_rejected(self):
        def reverse_sources(logs):
            logs[:] = logs[14:] + logs[:14]
        with self.assertRaises(ContractError):
            self.verify(self.fixture(journal_attack=reverse_sources))

    def test_wrong_sql_argument_rejected(self):
        def change(logs):
            first = next(r for r in logs if r['command'] == 'first' and r['status'] == 'started')
            first['arguments'][-1] = 'wrong.sql'
        with self.assertRaises(ContractError):
            self.verify(self.fixture(journal_attack=change))

    def test_wrong_command_byte_count_rejected(self):
        def change(logs):
            first = next(r for r in logs if r['command'] == 'first' and r['status'] == 'finished')
            first['stdout_bytes'] += 1
        with self.assertRaises(ContractError):
            self.verify(self.fixture(journal_attack=change))

    def test_self_resealed_positive_cannot_replace_source_absence(self):
        def change(report, _):
            path = Path(report['results'][0]['state_proposals']['path'])
            states = json.loads(path.read_text())
            states['records'][0]['state'] = 'present'
            states['contract_sha256'] = fingerprint({k: v for k, v in states.items() if k != 'contract_sha256'})
            write_json(path, states)
            report['results'][0]['state_proposals'] = evaluation.pin(path)
        with self.assertRaises(ContractError):
            self.verify(self.fixture(mutate=change))

    @staticmethod
    def states(members, when, values):
        return {'records': [{'nct_id': nct, 'snapshot_date': when, 'state': state,
                             'reasons': ['missing_nct_record'] if state == 'unknown' else []}
                            for nct, state in zip(members, values)]}

    def test_april_positive_never_changes_january_zero_or_gate(self):
        members = [self.nct]
        origin = self.states(members, '2025-01-01', ['absent_in_snapshot'])
        frames = {'2026-01-01': self.states(members, '2026-01-01', ['absent_in_snapshot']),
                  '2026-04-01': self.states(members, '2026-04-01', ['present'])}
        result = evaluation.compare_states(members, origin, frames)
        self.assertEqual(1, result['views']['2026-01-01']['absent'])
        self.assertEqual(1, result['views']['2026-04-01']['appearance'])
        self.assertEqual('stop_operational_prediction_expansion', result['decision'])
        self.assertFalse(result['clinical_activation'])

    def test_exact_ninety_percent_threshold_retains_unknown_denominator(self):
        members = [f'NCT{i:08d}' for i in range(1, 11)]
        origin = self.states(members, '2025-01-01', ['absent_in_snapshot'] * 10)
        values = ['present'] + ['absent_in_snapshot'] * 8 + ['unknown']
        frames = {when: self.states(members, when, values) for when in ('2026-01-01', '2026-04-01')}
        result = evaluation.compare_states(members, origin, frames)
        self.assertEqual(0.9, result['views']['2026-01-01']['observable_fraction'])
        self.assertEqual('larger_feasibility_design_only', result['decision'])
        self.assertFalse(result['training_allowed'])
        values[-2] = 'unknown'
        frames['2026-01-01'] = self.states(members, '2026-01-01', values)
        result = evaluation.compare_states(members, origin, frames)
        self.assertEqual('stop_operational_prediction_expansion', result['decision'])
        self.assertEqual(2, result['views']['2026-01-01']['unknown'])

    def test_origin_unknown_cannot_enter_selected_denominator(self):
        members = [self.nct]
        origin = self.states(members, '2025-01-01', ['unknown'])
        frames = {when: self.states(members, when, ['absent_in_snapshot'])
                  for when in ('2026-01-01', '2026-04-01')}
        with self.assertRaises(ContractError):
            evaluation.compare_states(members, origin, frames)

    def test_native_missing_row_only_supports_explicit_unknown(self):
        path = self.base / 'empty.jsonl'
        path.write_bytes(b'')
        states = self.states([self.nct], '2026-01-01', ['unknown'])
        frame = {'source': evaluation.pin(path), 'states': states}
        audit = evaluation.audit_native_rows([self.nct], {'2026-01-01': frame})
        self.assertIsNone(audit[0]['native_locator'])
        states['records'][0]['state'] = 'absent_in_snapshot'
        with self.assertRaises(ContractError):
            evaluation.audit_native_rows([self.nct], {'2026-01-01': frame})


if __name__ == '__main__':
    unittest.main()
