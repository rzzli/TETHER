"""Independent mixed follow-up probes; synthetic rows only, no database reads."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, sha256_file, write_json
from tether_engine.journal import RunJournal, read_chain
from tools.science.outcome_extract import extract, validate_plan
from tools.science.outcome_inputs import study_query
from tools.science.outcome_inputs import validate_study_rows
from tools.science.outcome_results import RESULT_FIELDS, STUDY_FIELDS, results_query, validate_result_rows
from tests import test_science_outcome_inputs as metadata_fixture


class EndpointFollowupPeerTests(unittest.TestCase):
    def setUp(self):
        self.ids = [f'NCT{i:08d}' for i in range(1, 13)]
        self.schema = metadata_fixture.schema()
        self.schema['studies'] = list(dict.fromkeys(self.schema['studies'] + list(STUDY_FIELDS)))
        self.schema.update({table: list(fields) for table, fields in RESULT_FIELDS.items()})

    def rows(self, day='2026-04-01'):
        study_request = study_query(self.ids, day, self.schema, max_ids=12)
        result_request = results_query(self.ids, day, self.schema)
        studies, results = [], []
        for nct in self.ids:
            metadata = metadata_fixture.study(study_request, nct,
                last_update_posted_date='2025-11-10', last_update_posted_date_type='ACTUAL',
                study_first_posted_date='2023-01-02', results_first_posted_date='2025-11-10',
                results_first_posted_date_type='ACTUAL')
            studies.append(metadata)
            results.append({'study': {field: metadata['study'][field] for field in result_request['projection']['studies']},
                **{table: [] for table in RESULT_FIELDS}})
        return studies, results, study_request, result_request

    def join(self, *args):
        from tools.science.endpoint_followup import join_snapshot
        return join_snapshot(*args)

    def plan(self, folder):
        jobs = []
        for day, count in [('2026-01-01', 563840), ('2026-04-01', 578527)]:
            queries = []
            for name, request in [('studies', study_query(self.ids, day, self.schema, max_ids=12)),
                    ('results', results_query(self.ids, day, self.schema))]:
                path = folder / (day + '-' + name + '.sql')
                path.write_text(request['sql'], encoding='utf-8')
                queries.append({'name': name, 'path': str(path), 'request': request})
            jobs.append({'snapshot_date': day, 'port': 55441 + len(jobs),
                'expected_studies': count, 'pins': [{'path': 'source', 'sha256': '0' * 64}], 'queries': queries})
        return {'schema_version': 1, 'protocol_id': 'endpoint-followup-inputs-v1',
            'phase': 'endpoint_followup', 'role': 'evaluation_only', 'provider_spend_usd': 0,
            'clinical_activation': False, 'origin_at': '2025-01-01T00:00:00Z',
            'horizon_at': '2026-01-01T00:00:00Z', 'ascertainment_at': '2026-04-01T00:00:00Z',
            'nct_ids': self.ids, 'jobs': jobs}

    def test_explicit_mixed_phase_accepts_only_fixed_followup_dates(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = self.plan(Path(temporary))
            validate_plan(plan)
            for change in ('reorder', 'origin', 'eleven', 'activation', 'cutoff'):
                changed = copy.deepcopy(plan)
                if change == 'reorder': changed['jobs'].reverse()
                if change == 'origin': changed['jobs'][0]['snapshot_date'] = '2025-01-01'
                if change == 'eleven': changed['nct_ids'].pop()
                if change == 'activation': changed['clinical_activation'] = True
                if change == 'cutoff': changed['ascertainment_at'] = '2026-04-02T00:00:00Z'
                with self.subTest(change=change), self.assertRaises(ContractError):
                    validate_plan(changed)

    def test_shared_version_contradiction_is_rejected_before_adjudication(self):
        for field, value in [('last_update_posted_date', '2025-11-11'),
                ('last_update_posted_date_type', 'ESTIMATED'),
                ('study_first_posted_date', '2023-01-03'),
                ('results_first_posted_date', None),
                ('results_first_posted_date_type', None)]:
            args = self.rows()
            args[1][0]['study'][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError): self.join(*args)

    def test_membership_cannot_be_changed_by_matching_rehashed_requests(self):
        studies, results, study_request, _ = self.rows()
        replaced = self.ids[:-1] + ['NCT99999999']
        result_request = results_query(replaced, '2026-04-01', self.schema)
        with self.assertRaises(ContractError): self.join(studies, results, study_request, result_request)

    def test_join_requires_same_source_snapshot_and_cutoff(self):
        studies, results, study_request, _ = self.rows()
        earlier = results_query(self.ids, '2026-01-01', self.schema)
        with self.assertRaises(ContractError): self.join(studies, results, study_request, earlier)

    def test_raw_result_canary_and_duplicate_envelope_are_rejected(self):
        for change in ('canary', 'duplicate', 'cross_trial'):
            args = self.rows()
            if change == 'canary': args[1][0]['inferred_success'] = True
            if change == 'duplicate': args[1].append(copy.deepcopy(args[1][0]))
            if change == 'cross_trial': args[1][0]['study']['nct_id'] = 'NCT99999999'
            with self.subTest(change=change), self.assertRaises(ContractError): self.join(*args)

    def test_changed_plan_fails_without_process_dispatch_and_retains_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'plan.json'
            write_json(path, self.plan(root))
            with patch('tools.science.outcome_extract.subprocess.run') as dispatch:
                with self.assertRaises(ContractError): extract(path, '0' * 64, root / 'failed')
                dispatch.assert_not_called()
            self.assertEqual('build_failed', read_chain(root / 'failed/journal.jsonl')[-1]['event'])
            self.assertTrue((root / 'failed/failure.json').is_file())

    def test_absent_both_envelopes_preserves_frozen_member_and_unknown_label(self):
        studies, results, sr, rr = self.rows()
        joined = self.join(studies[:-1], results[:-1], sr, rr)
        self.assertEqual(self.ids, [m['nct_id'] for m in joined['members']])
        self.assertEqual('missing_both_source_envelopes', joined['members'][-1]['status'])
        self.assertIsNone(joined['members'][-1]['clinical_label'])
        self.assertFalse(joined['members'][-1]['absence_claim'])
        self.assertEqual(0, joined['clinical_labels_assigned'])
        self.assertFalse(joined['clinical_activation'])

    def test_one_sided_missing_envelope_cannot_be_silently_joined(self):
        studies, results, sr, rr = self.rows()
        for left, right in [(studies[:-1], results), (studies, results[:-1])]:
            with self.assertRaises(ContractError): self.join(left, right, sr, rr)

    def populated_rows(self):
        args = self.rows()
        outcome = dict.fromkeys(RESULT_FIELDS['outcomes'])
        outcome.update(id=1, nct_id=self.ids[0], outcome_type='PRIMARY', title='Response')
        args[1][0]['outcomes'] = [outcome]
        return args

    def test_unqualified_or_future_first_result_posting_is_context_hold(self):
        for updates in [dict(results_first_posted_date=None),
                dict(results_first_posted_date_type=None),
                dict(results_first_posted_date_type='ESTIMATED'),
                dict(results_first_posted_date='2026-04-01', last_update_posted_date='2026-04-01')]:
            args = self.populated_rows()
            args[0][0]['study'].update(updates)
            args[1][0]['study'].update(updates)
            joined = self.join(*args)
            self.assertEqual('held_source_context', joined['members'][0]['status'])
            self.assertTrue(joined['members'][0]['holds'])
            self.assertIsNone(joined['members'][0]['clinical_label'])
            self.assertFalse(joined['members'][0]['absence_claim'])

    def retained(self, root):
        """Construct a successful local receipt without any database process."""
        plan = self.plan(root)
        output = root / 'retained'
        journal = RunJournal(output, kind='build')
        source = Path(__file__).resolve().parents[1] / 'tools/science/outcome_extract.py'
        code = {'path': str(source), 'sha256': sha256_file(source), 'bytes': source.stat().st_size}
        plan['executed_code'] = [code]; plan['parents'] = []
        archived = output / 'executed-code/tools/science/outcome_extract.py'
        archived.parent.mkdir(parents=True); archived.write_bytes(source.read_bytes())
        (output / 'executed-runner.py').write_bytes(source.read_bytes())
        write_json(output / 'executed-code-proofs.json', [{'source': code,
            'archive_path': str(archived), 'sha256': code['sha256']}])
        write_json(output / 'effective-plan.json', plan)
        snapshots = []
        for job in plan['jobs']:
            date = job['snapshot_date']; folder = output / date; folder.mkdir()
            restore_root = root / ('restore-' + date)
            job['restore_root'] = str(restore_root)
            studies, results, sr, rr = self.rows(date)
            committed = []
            for query, rows in zip(job['queries'], (studies, results)):
                raw = ''.join(json.dumps(row) + '\n' for row in rows).encode('utf-8')
                first = folder / (query['name'] + '-first.stdout.log')
                first.write_bytes(raw)
                (folder / (query['name'] + '-repeat.stdout.log')).write_bytes(raw)
                validation = validate_study_rows(rows, query['request']) if query['name'] == 'studies' else validate_result_rows(rows, query['request'])
                write_json(folder / (query['name'] + '-validation.json'), validation)
                committed.append({'name': query['name'], 'path': str(first),
                    'sha256': sha256_file(first), 'bytes': len(raw), 'repeat_identical': True})
            metadata = {'database': 'aact_snapshot', 'studies': job['expected_studies'],
                'directory': str(restore_root / 'pgdata'), 'port': str(job['port']), 'read_only': 'on'}
            write_json(folder / 'metadata.stdout.log', metadata)
            write_json(folder / 'lifecycle.json', {'ownership_acquired': True,
                'server_stopped': True, 'port': job['port'], 'automatic_retry': False})
            snapshots.append({'snapshot_date': date, 'queries': committed, 'metadata': metadata})
        write_json(output / 'effective-plan.json', plan)
        plan_sha = sha256_file(output / 'effective-plan.json')
        report = {'schema_version': 1, 'status': 'source_reads_complete_pending_scientific_validation',
            'role': 'evaluation_only', 'phase': 'endpoint_followup', 'protocol_sha256': plan_sha,
            'snapshots': snapshots, 'clinical_labels_assigned': 0, 'provider_spend_usd': 0,
            'clinical_activation': False}
        write_json(output / 'report.json', report)
        report_sha = sha256_file(output / 'report.json')
        journal.append('build_completed', report_sha256=report_sha); journal.close()
        return output, plan_sha, report_sha

    def verify_retained(self, output, plan_sha, report_sha):
        from tools.science.endpoint_followup import verify_extraction
        with patch('tools.science.endpoint_followup.validate_endpoint_binding'):
            return verify_extraction(output, plan_sha, report_sha)

    def test_retained_verifier_accepts_exact_synthetic_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, plan_sha, report_sha = self.retained(Path(temporary).resolve())
            self.assertEqual(2, len(self.verify_retained(output, plan_sha, report_sha)))

    def test_retained_normalized_validation_cannot_disagree_with_raw_bytes(self):
        for name in ('studies', 'results'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                output, plan_sha, report_sha = self.retained(Path(temporary).resolve())
                write_json(output / '2026-01-01' / (name + '-validation.json'), {'clinical_label': 1})
                with self.assertRaises(ContractError): self.verify_retained(output, plan_sha, report_sha)

    def test_retained_source_identity_and_lifecycle_cannot_be_forged(self):
        for name, field, value in [('metadata.stdout.log', 'read_only', 'off'),
                ('metadata.stdout.log', 'studies', 3), ('lifecycle.json', 'port', 60000),
                ('lifecycle.json', 'automatic_retry', True)]:
            with self.subTest(name=name, field=field), tempfile.TemporaryDirectory() as temporary:
                output, plan_sha, report_sha = self.retained(Path(temporary).resolve())
                target = output / '2026-01-01' / name
                content = json.loads(target.read_text(encoding='utf-8')); content[field] = value
                write_json(target, content)
                with self.assertRaises(ContractError): self.verify_retained(output, plan_sha, report_sha)

    def binding_fixture(self, root):
        from tools.science import endpoint_followup as module
        from tools.science.outcome_extract import APPROVED_BASE, APPROVED_RESTORES
        plan = self.plan(root)
        policy = json.loads(module.POLICY.read_text(encoding='utf-8'))
        policy_pin = {'path': str(module.POLICY), 'sha256': sha256_file(module.POLICY)}
        seal_pin = {'path': str(root / 'pack-freeze.json'), 'sha256': module.PACK_SHA}
        readiness_pin = {'path': str(root / 'readiness.json'), 'sha256': module.READINESS_SHA}
        documents = {str(module.POLICY.resolve()): policy}
        files = []
        for nct in self.ids:
            pin = {'path': str(root / 'packets' / (nct + '.json')), 'sha256': 'a' * 64}
            files.append(pin); documents[str(Path(pin['path']).resolve())] = {'origin_scope': {'nct_id': nct}}
        pack = {'selected_distinct_trials': 12, 'clinical_labels_assigned': 0,
            'followup_sources_read': False, 'clinical_ready': False, 'files': files,
            'direct_parents': [{'path': str(root / 'old-plan.json'), 'sha256': 'b' * 64}],
            'ancestor_pins': [{'path': str(root / 'immutable-original.py'), 'sha256': 'c' * 64}]}
        review = {'pack_freeze': {'sha256': module.PACK_SHA}, 'followup_sources_read': False,
            'members': [{'nct_id': nct} for nct in self.ids], 'membership_modified': False}
        documents[str(Path(seal_pin['path']).resolve())] = pack
        documents[str(Path(readiness_pin['path']).resolve())] = review
        plan.update(followup_policy=policy_pin, selection=seal_pin, origin_readiness=readiness_pin,
            parents=[policy_pin, seal_pin, readiness_pin] + files + pack['direct_parents'] + pack['ancestor_pins'])
        for job in plan['jobs']:
            restore = (APPROVED_BASE / APPROVED_RESTORES[job['snapshot_date']]).resolve()
            job['restore_root'] = str(restore)
            names = ('extracted/postgres.dmp', 'archive-inspection.json', 'dump-toc-pg17.txt', 'technical-audit.json', 'setup.py')
            job['pins'] = [{'path': str(restore / name), 'sha256': 'd' * 64} for name in names]
            documents[str(restore / 'archive-inspection.json')] = {'members': [{'name': 'postgres.dmp', 'sha256': 'd' * 64}]}
            documents[str(restore / 'technical-audit.json')] = {'status': 'completed',
                'study_id_check': {'rows': job['expected_studies']},
                'columns': [{'table_schema': 'ctgov', 'table_name': table, 'column_name': field}
                    for table, fields in self.schema.items() for field in fields]}
        return plan, documents

    def bind_synthetic(self, plan, documents):
        from tools.science.endpoint_followup import validate_endpoint_binding
        def bound(path, expected): return copy.deepcopy(documents[str(Path(path).resolve())]), expected
        with patch('tools.science.endpoint_followup.read_bound_json', side_effect=bound), \
                patch('tools.science.outcome_extract.check_pins'):
            return validate_endpoint_binding(plan)

    def test_binding_accepts_immutable_origin_archives_without_nested_live_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan, documents = self.binding_fixture(Path(temporary).resolve())
            self.assertEqual('endpoint-followup-feasibility-v0.1', self.bind_synthetic(plan, documents)['protocol_id'])

    def test_binding_rejects_critical_policy_mutations_even_with_new_self_hash(self):
        changes = [('provider_spend_usd', False), ('automatic_labels', True),
            ('max_rows_per_trial', 99999), ('max_output_bytes_per_query', 2**30),
            ('origin_pack_sha256', 'f' * 64), ('source_snapshots', ['2026-04-01'])]
        from tools.science.endpoint_followup import POLICY
        for key, value in changes:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                plan, documents = self.binding_fixture(Path(temporary).resolve())
                documents[str(POLICY.resolve())][key] = value
                plan['followup_policy']['sha256'] = 'e' * 64
                with self.assertRaises(ContractError): self.bind_synthetic(plan, documents)

    def test_binding_rejects_membership_missing_parents_caps_query_order_and_source_path(self):
        for change in ('member', 'parent', 'cap', 'sql', 'order', 'duplicate', 'root'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                plan, documents = self.binding_fixture(Path(temporary).resolve())
                job = plan['jobs'][0]
                if change == 'member': plan['nct_ids'][-1] = 'NCT99999999'
                if change == 'parent': plan['parents'].pop()
                if change == 'cap': job['queries'][1]['request'] = results_query(self.ids, job['snapshot_date'], self.schema, max_rows_per_trial=1)
                if change == 'sql': Path(job['queries'][0]['path']).write_text(job['queries'][0]['request']['sql'].replace('ROLLBACK;', 'COMMIT;'), encoding='utf-8')
                if change == 'order': job['queries'].reverse()
                if change == 'duplicate': job['queries'].append(copy.deepcopy(job['queries'][0]))
                if change == 'root': job['restore_root'] = str(Path(temporary) / 'other-database')
                with self.assertRaises(ContractError): self.bind_synthetic(plan, documents)


if __name__ == '__main__':
    unittest.main()
