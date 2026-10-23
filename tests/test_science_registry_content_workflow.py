"""B0 source/selection guards using only synthetic local files and mocked dispatch."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, write_json
from tools.science.registry_content import FIELDS
from tools.science import registry_content_workflow as flow


class RegistryContentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='b0-binding-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def source_fixture(self):
        restore = self.root / 'restores' / 'origin'
        (restore / 'extracted').mkdir(parents=True)
        raw = self.root / 'raw' / 'archive.zip'
        raw.parent.mkdir()
        raw.write_bytes(b'archive fixture, not an actual zip')
        dump = restore / 'extracted/postgres.dmp'
        dump.write_bytes(b'fixture dump bytes')
        write_json(restore / 'archive-inspection.json', {
            'archive': str(raw), 'bytes': raw.stat().st_size, 'sha256': flow.pin(raw)['sha256'],
            'members': [{'name': 'postgres.dmp', 'sha256': flow.pin(dump)['sha256']}],
        })
        columns = [{'table_schema': 'ctgov', 'table_name': t, 'column_name': c}
                   for t, cols in FIELDS.items() for c in cols]
        write_json(restore / 'technical-audit.json', {
            'status': 'completed', 'study_id_check': {'rows': 520688}, 'columns': columns})
        (restore / 'dump-toc-pg17.txt').write_text('; Archive created at 2025-01-01 00:00:00\n')
        (restore / 'setup.py').write_text('# fixture\n')
        pins = [flow.pin(restore / n) for n in ['extracted/postgres.dmp', 'archive-inspection.json',
                'technical-audit.json', 'dump-toc-pg17.txt', 'setup.py']]
        prior = self.root / 'prior-plan.json'
        write_json(prior, {'jobs': [{'snapshot_date': '2025-01-01', 'restore_root': str(restore),
            'expected_studies': 520688, 'port': 55440, 'pins': pins}]})
        return restore, raw, dump, {'prior_request_plans': [flow.pin(prior)]}

    def source_patches(self):
        return (patch.object(flow, 'APPROVED_BASE', self.root / 'restores'),
                patch.object(flow, 'APPROVED_RESTORES', {'2025-01-01': 'origin'}),
                patch.object(flow, 'APPROVED_RAW', self.root / 'raw'))

    def test_original_source_closure_and_exact_projection(self):
        _, _, _, manifest = self.source_fixture()
        a, b, c = self.source_patches()
        with a, b, c:
            job = flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'query.sql')
        self.assertEqual('2025-01-01', job['snapshot_date'])
        self.assertEqual(6, len(job['pins']))
        self.assertFalse(job['query']['request']['execution_authorized'])
        self.assertEqual(['NCT00000001'], job['query']['request']['nct_ids'])

    def test_mutated_dump_cannot_be_blessed_by_live_prior_plan(self):
        _, _, dump, manifest = self.source_fixture()
        dump.write_bytes(b'corrupt')
        a, b, c = self.source_patches()
        with a, b, c, self.assertRaises(ContractError):
            flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'q.sql')

    def test_mutated_archive_fails_even_if_retained_dump_is_unchanged(self):
        _, raw, _, manifest = self.source_fixture()
        raw.write_bytes(b'changed archive')
        a, b, c = self.source_patches()
        with a, b, c, self.assertRaises(ContractError):
            flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'q.sql')

    def test_actual_followup_archive_receipt_field_layout_is_supported(self):
        restore, _, _, manifest = self.source_fixture()
        inspection = restore / 'archive-inspection.json'
        data = json.loads(inspection.read_text())
        data['archive_sha256'] = data.pop('sha256')
        data['archive_bytes'] = data.pop('bytes')
        inspection.write_text(json.dumps(data))
        prior_path = Path(manifest['prior_request_plans'][0]['path'])
        prior = json.loads(prior_path.read_text())
        prior['jobs'][0]['pins'] = [flow.pin(inspection) if Path(p['path']) == inspection else p
                                   for p in prior['jobs'][0]['pins']]
        prior_path.write_text(json.dumps(prior))
        manifest['prior_request_plans'][0] = flow.pin(prior_path)
        a, b, c = self.source_patches()
        with a, b, c:
            job = flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'q.sql')
        self.assertEqual(6, len(job['pins']))

    def test_missing_dump_proof_rejected_before_query_creation(self):
        _, _, _, manifest = self.source_fixture()
        path = Path(manifest['prior_request_plans'][0]['path'])
        prior = json.loads(path.read_text())
        prior['jobs'][0]['pins'] = [p for p in prior['jobs'][0]['pins'] if not p['path'].endswith('.dmp')]
        path.write_text(json.dumps(prior))
        manifest['prior_request_plans'][0] = flow.pin(path)
        a, b, c = self.source_patches()
        with a, b, c, self.assertRaises(ContractError):
            flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'q.sql')

    def test_wrong_restore_root_rejected(self):
        _, _, _, manifest = self.source_fixture()
        with self.assertRaises(ContractError):
            flow.source_job(manifest, '2025-01-01', ['NCT00000001'], self.root / 'q.sql')

    def test_original_order_exclusions_unknown_and_cap_preserved(self):
        ids = [f'NCT{i:08d}' for i in range(1, 44)]
        candidates = {'candidates': [{'nct_id': n} for n in ids[::-1]]}
        excluded = {ids[-1]}
        states = {'records': [{'nct_id': n, 'state': 'absent_in_snapshot'} for n in ids if n not in excluded]}
        states['records'][0]['state'] = 'unknown'
        states['records'][1]['state'] = 'present'
        context = ({}, {'candidate_freeze': {}, 'excluded_pack_pins': []}, {}, candidates, excluded)
        with patch.object(flow, 'verify_origin_run', return_value=({}, {}, states)), \
                patch.object(flow, 'origin_context', return_value=context), \
                patch.object(flow, 'pin', return_value={}):
            record = flow.membership_record(self.root / 'run')
        self.assertEqual(ids[-2:1:-1][:32], record['nct_ids'])
        self.assertEqual(43, len(record['screen']))
        self.assertEqual('excluded_prior_pilot', record['screen'][0]['disposition'])
        self.assertEqual('origin_unknown', record['screen'][-1]['disposition'])
        self.assertFalse(record['followup_used_for_selection'])
        self.assertFalse(record['protected_holdout'])

    def test_no_members_does_not_trigger_replacement(self):
        candidates = {'candidates': [{'nct_id': 'NCT00000001'}]}
        states = {'records': [{'nct_id': 'NCT00000001', 'state': 'unknown'}]}
        context = ({}, {'candidate_freeze': {}, 'excluded_pack_pins': []}, {}, candidates, set())
        with patch.object(flow, 'verify_origin_run', return_value=({}, {}, states)), \
                patch.object(flow, 'origin_context', return_value=context), \
                patch.object(flow, 'pin', return_value={}):
            self.assertEqual([], flow.membership_record(self.root / 'run')['nct_ids'])

    def test_failed_binding_leaves_journal_and_zero_dispatch(self):
        plan = self.root / 'plan.json'
        write_json(plan, {'protocol_id': 'forged'})
        with patch('tools.science.registry_content_transport.run_source') as dispatch:
            with self.assertRaises(ContractError):
                flow.run(flow.pin(plan), self.root / 'failed')
        dispatch.assert_not_called()
        self.assertEqual('build_failed', read_chain(self.root / 'failed/journal.jsonl')[-1]['event'])
        self.assertTrue((self.root / 'failed/failure.json').is_file())

    def test_self_pinned_membership_cannot_replace_reconstructed_origin(self):
        path = self.root / 'membership.json'
        value = {'status': 'source_bound_origin_membership', 'origin_run': str(self.root / 'run'),
                 'nct_ids': ['NCT00000001']}
        write_json(path, value)
        expected = copy.deepcopy(value)
        expected['nct_ids'] = ['NCT00000002']
        with patch.object(flow, 'membership_record', return_value=expected), self.assertRaises(ContractError):
            flow.verify_membership(flow.pin(path))

    def test_followup_without_seal_or_with_empty_membership_is_rejected(self):
        context = ({}, {}, {}, {}, set())
        with patch.object(flow, 'origin_context', return_value=context):
            with self.assertRaises(ContractError):
                flow.build_plan(self.root, 'followup')
            with patch.object(flow, 'verify_membership', return_value={'nct_ids': []}), \
                    self.assertRaises(ContractError):
                flow.build_plan(self.root, 'followup', {'path': 'unused'})

    def test_source_plan_modification_cannot_reauthorize_sql(self):
        path = self.root / 'plan.json'
        expected = {'protocol_id': 'registry-content-execution-v0.1', 'mode': 'origin',
                    'membership': None, 'sql': 'read only'}
        actual = {**expected, 'sql': 'DELETE FROM ctgov.studies'}
        with patch.object(flow, 'build_plan', return_value=expected), self.assertRaises(ContractError):
            flow.validate_plan(actual, path)

    def test_known_archived_origin_allowance_is_verification_only(self):
        path = self.root / 'old-plan.json'
        original = {'protocol_id': 'registry-content-execution-v0.1', 'mode': 'origin',
                    'membership': None, 'code': [{'known': 'original'}], 'runtime_pins': [], 'jobs': []}
        write_json(path, original)
        expected = {**original, 'code': [{'known': 'revised'}]}
        with patch.object(flow, 'ARCHIVED_ORIGIN_PLAN_SHA', flow.pin(path)['sha256']), \
                patch.object(flow, 'build_plan', return_value=copy.deepcopy(expected)), \
                patch.object(flow, 'check_pins') as checks:
            with self.assertRaises(ContractError):
                flow.validate_plan(original, path)  # dispatch/default remains strict
            flow.validate_plan(original, path, allow_frozen_legacy_origin=True)
            checks.assert_called_once_with([])

    def test_legacy_allowance_cannot_bless_another_object_or_changed_plan_bytes(self):
        path = self.root / 'old-plan.json'
        original = {'protocol_id': 'registry-content-execution-v0.1', 'mode': 'origin',
                    'membership': None, 'code': [{'known': 'original'}], 'runtime_pins': [], 'jobs': []}
        write_json(path, original)
        known = flow.pin(path)['sha256']
        expected = {**original, 'code': [{'known': 'revised'}]}
        with patch.object(flow, 'ARCHIVED_ORIGIN_PLAN_SHA', known), \
                patch.object(flow, 'build_plan', return_value=copy.deepcopy(expected)):
            forged = {**original, 'code': [{'known': 'substituted'}]}
            with self.assertRaises(ContractError):
                flow.validate_plan(forged, path, allow_frozen_legacy_origin=True)
            path.write_text(path.read_text() + '\n')
            with self.assertRaises(ContractError):
                flow.validate_plan(original, path, allow_frozen_legacy_origin=True)

    def test_archive_loader_rejects_missing_or_conflicting_identity(self):
        with patch.object(flow, 'APPROVED_RAW', self.root):
            valid = {'archive': str(self.root / 'x.zip'), 'sha256': 'a' * 64, 'bytes': 10}
            for changes in ({'archive_sha256': 'b' * 64, 'archive_bytes': 10},
                            {'archive_sha256': 'a' * 64, 'archive_bytes': 11}, {'bytes': True}):
                with self.subTest(changes=changes), self.assertRaises(ContractError):
                    flow.archive_proof({**valid, **changes})
            with self.assertRaises(ContractError):
                flow.archive_proof({'archive': str(self.root / 'x.zip')})

    def test_plan_output_reservation_is_exclusive(self):
        out = self.root / 'prepared'
        out.mkdir()
        with self.assertRaises(FileExistsError), patch.object(flow, 'build_plan') as build:
            flow.prepare(out, 'origin')
        build.assert_not_called()

    def test_failed_source_binding_is_retained_by_preparation(self):
        with patch.object(flow, 'build_plan', side_effect=ContractError('fixture ancestor failure')):
            with self.assertRaises(ContractError):
                flow.prepare(self.root / 'failed-preparation', 'origin')
        self.assertEqual('build_failed', read_chain(self.root / 'failed-preparation/journal.jsonl')[-1]['event'])


if __name__ == '__main__':
    unittest.main()
