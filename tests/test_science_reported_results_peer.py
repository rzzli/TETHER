"""Independent synthetic adversarial checks; no database or network dispatch."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.serde import ContractError, fingerprint, sha256_file, write_json
from tools.science import outcome_extract
from tools.science.outcome_results import (
    RESULT_FIELDS, STUDY_FIELDS, regenerate_results, results_query, validate_result_rows,
)


class ReportedResultsPeerTests(unittest.TestCase):
    def setUp(self):
        self.ids = [f'NCT{index:08d}' for index in range(1, 13)]
        self.schema = {'studies': list(STUDY_FIELDS),
                       **{table: list(fields) for table, fields in RESULT_FIELDS.items()}}
        self.request = results_query(self.ids, '2026-04-01', self.schema)

    def record(self):
        study = {field: None for field in STUDY_FIELDS}
        study.update(nct_id=self.ids[0], study_first_posted_date='2024-01-01',
                     last_update_posted_date='2026-02-01', last_update_posted_date_type='ACTUAL',
                     results_first_posted_date='2025-12-01', results_first_posted_date_type='ACTUAL')
        record = {'study': study}
        ids = {'outcomes': 11, 'result_groups': 22, 'outcome_analyses': 33,
               'outcome_analysis_groups': 44, 'outcome_counts': 55, 'outcome_measurements': 66}
        for table, fields in RESULT_FIELDS.items():
            row = {field: None for field in fields}
            row.update(id=ids[table], nct_id=self.ids[0])
            if 'outcome_id' in row: row['outcome_id'] = 11
            if 'result_group_id' in row: row['result_group_id'] = 22
            if 'outcome_analysis_id' in row: row['outcome_analysis_id'] = 33
            if 'ctgov_group_code' in row: row['ctgov_group_code'] = 'OG001'
            record[table] = [row]
        return record

    def test_float_and_boolean_foreign_keys_are_not_integer_identifiers(self):
        for table, field, value in (
            ('outcome_analyses', 'outcome_id', 11.0),
            ('outcome_counts', 'result_group_id', 22.0),
            ('outcome_analysis_groups', 'outcome_analysis_id', 33.0),
            ('result_groups', 'outcome_id', 11.0),
        ):
            row = self.record(); row[table][0][field] = value
            with self.subTest(table=table, field=field), self.assertRaises(ContractError):
                validate_result_rows([row], self.request)
        row = self.record(); row['outcomes'][0]['id'] = 1
        row['outcome_analyses'][0]['outcome_id'] = True
        row['result_groups'][0]['outcome_id'] = 1
        row['outcome_counts'][0]['outcome_id'] = 1
        row['outcome_measurements'][0]['outcome_id'] = 1
        with self.assertRaises(ContractError): validate_result_rows([row], self.request)

    def test_populated_group_codes_must_agree_with_the_referenced_group(self):
        for table in ('outcome_counts', 'outcome_measurements', 'outcome_analysis_groups'):
            row = self.record(); row[table][0]['ctgov_group_code'] = 'OG999'
            with self.subTest(table=table), self.assertRaises(ContractError):
                validate_result_rows([row], self.request)

    def test_future_or_contradictory_result_posting_cannot_enter_eligible_payload(self):
        for posted in ('2026-02-02', '2026-05-01'):
            row = self.record(); row['study']['results_first_posted_date'] = posted
            with self.subTest(posted=posted):
                try:
                    result = validate_result_rows([row], self.request)
                except ContractError:
                    continue
                self.assertEqual([], result['eligible_reconstructed_rows'])
                self.assertEqual([row], result['quarantined_rows'])

    def test_equal_civil_dates_do_not_invent_intraday_order_or_backdate_version(self):
        row = self.record()
        row['study']['results_first_posted_date'] = row['study']['last_update_posted_date']
        self.assertEqual([row], validate_result_rows([row], self.request)['eligible_reconstructed_rows'])
        row['study']['last_update_posted_date'] = '2026-04-01'
        row['study']['results_first_posted_date'] = '2025-01-01'
        self.assertEqual([], validate_result_rows([row], self.request)['eligible_reconstructed_rows'])

    def test_result_payload_is_distinct_from_planned_design_and_never_success(self):
        row = self.record()
        row['outcome_analyses'][0].update(p_value=0.000001, p_value_raw='<0.00001')
        result = validate_result_rows([row], self.request)
        self.assertIsNone(result['clinical_label'])
        self.assertFalse(result['clinical_activation'])
        self.assertFalse(result['prespecified_success_rule_checked'])
        self.assertNotIn('design_outcomes', self.request['projection'])
        self.assertEqual(row, result['eligible_reconstructed_rows'][0])

    def test_missing_or_unknown_result_context_is_retained_without_negative(self):
        row = self.record()
        for table in ('outcome_counts', 'outcome_measurements', 'outcome_analysis_groups'):
            row[table][0]['ctgov_group_code'] = None
        result = validate_result_rows([row], self.request)
        self.assertEqual(row, result['eligible_reconstructed_rows'][0])
        self.assertIsNone(result['clinical_label'])
        self.assertEqual(11, len(result['missing_nct_ids']))

    def test_row_cap_is_failure_and_no_sql_limit_can_silently_drop_results(self):
        request = results_query(self.ids, '2026-04-01', self.schema, max_rows_per_trial=5)
        self.assertNotIn(' LIMIT ', request['sql'])
        with self.assertRaises(ContractError): validate_result_rows([self.record()], request)
        with self.assertRaises(ContractError):
            validate_result_rows([{'overflow': True, 'nct_id': self.ids[0], 'result_rows': 6}], request)

    def test_mutated_request_self_hash_does_not_authorize_temporal_or_sql_changes(self):
        for field, value in [('nct_ids', self.ids[:-1] + ['NCT99999999']),
                             ('sql', self.request['sql'].replace('ROLLBACK;', 'COMMIT;')),
                             ('max_output_bytes', 10**20), ('cutoff_at', '2027-01-01T00:00:00Z')]:
            request = copy.deepcopy(self.request); request[field] = value
            request['request_sha256'] = fingerprint({key: value for key, value in request.items()
                                                     if key != 'request_sha256'})
            with self.subTest(field=field), self.assertRaises(ContractError): regenerate_results(request)

    def test_same_size_changed_ancestor_is_detected_before_any_source_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'; source.write_bytes(b'old')
            pin = {'path': str(source), 'sha256': sha256_file(source), 'bytes': 3}
            source.write_bytes(b'new')
            with patch.object(outcome_extract.subprocess, 'run') as process:
                with self.assertRaises(ContractError): outcome_extract.check_pins([pin])
                process.assert_not_called()

    def test_malformed_selected_results_plan_is_journaled_without_start_or_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'plan.json'
            write_json(path, {'schema_version': 1, 'phase': 'selected_results',
                              'protocol_id': 'science4-outcome-inputs-v1', 'role': 'agent_evidence'})
            with patch.object(outcome_extract.subprocess, 'run') as process:
                with self.assertRaises(ContractError):
                    outcome_extract.extract(path, sha256_file(path), root / 'output')
                process.assert_not_called()
            self.assertTrue((root / 'output' / 'failure.json').is_file())

    def test_exact_original_membership_binding_cannot_be_replaced_by_another_twelve(self):
        project = Path(outcome_extract.__file__).resolve().parents[2]
        policy_path = project / 'planning/protocols/clinical-label-readiness-v0.1.json'
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
        pack = {'clinical_labels_assigned': 0, 'selected_distinct_trials': 12,
                'files': [{'path': f'packets/{index}.json', 'sha256': 'a'*64}
                          for index in range(12)]}
        plan = {'phase': 'selected_results', 'review_policy': {'path': 'review.json', 'sha256': outcome_extract.POLICY_SHA256},
                'selection': {'path': 'pack.json', 'sha256': outcome_extract.PACK_SHA256},
                'results_policy': {'path': str(policy_path), 'sha256': sha256_file(policy_path)},
                'parents': [{'path': str(policy_path), 'sha256': sha256_file(policy_path)}],
                'jobs': [{'snapshot_date': '2026-01-01'}, {'snapshot_date': '2026-04-01'}],
                'nct_ids': self.ids[:-1] + ['NCT99999999'],
                **{key: policy[key] for key in ('origin_at', 'horizon_at', 'ascertainment_at')}}
        def source(path, expected):
            if path.name == 'review.json': return {}, None
            if path.name == 'pack.json': return pack, None
            if path == policy_path: return policy, None
            if path.parent.name == 'packets':
                return {'origin_scope': {'nct_id': self.ids[int(path.stem)]}}, None
            raise AssertionError('Unexpected source read')
        with patch.object(outcome_extract, 'read_bound_json', side_effect=source), \
                patch.object(outcome_extract, 'check_pins'), \
                patch.object(outcome_extract.subprocess, 'run') as process:
            with self.assertRaisesRegex(ContractError, 'actual sealed pilot'):
                outcome_extract.validate_binding(plan)
            process.assert_not_called()

    def test_policy_semantics_cannot_contradict_original_review_or_executing_bounds(self):
        project = Path(outcome_extract.__file__).resolve().parents[2]
        policy_path = project / 'planning/protocols/clinical-label-readiness-v0.1.json'
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
        pack = {'clinical_labels_assigned': 0, 'selected_distinct_trials': 12, 'files': []}
        plan = {'phase': 'selected_results',
                'review_policy': {'path': 'review.json', 'sha256': outcome_extract.POLICY_SHA256},
                'selection': {'path': 'pack.json', 'sha256': outcome_extract.PACK_SHA256},
                'results_policy': {'path': str(policy_path), 'sha256': sha256_file(policy_path)},
                'parents': [{'path': str(policy_path), 'sha256': sha256_file(policy_path)}],
                'jobs': [{'snapshot_date': '2026-01-01'}, {'snapshot_date': '2026-04-01'}],
                'nct_ids': self.ids,
                **{key: policy[key] for key in ('origin_at', 'horizon_at', 'ascertainment_at')}}
        for field, value in [('parent_review_policy_sha256', '0'*64),
                             ('source_snapshots', ['2026-04-01']),
                             ('max_result_output_bytes_per_snapshot', 10**20),
                             ('reported_tables', ['outcomes']),
                             ('automatic_label_assignment', True),
                             ('ascertainment_at', '2027-01-01T00:00:00Z')]:
            altered = copy.deepcopy(policy); altered[field] = value
            def source(path, expected):
                if path.name == 'review.json': return {}, None
                if path.name == 'pack.json': return pack, None
                if path == policy_path: return altered, None
                raise AssertionError('Policy should fail before any membership/source query')
            with self.subTest(field=field), \
                    patch.object(outcome_extract, 'read_bound_json', side_effect=source), \
                    patch.object(outcome_extract, 'check_pins'), \
                    patch.object(outcome_extract.subprocess, 'run') as process:
                with self.assertRaisesRegex(ContractError, 'policy differs'):
                    outcome_extract.validate_binding(plan)
                process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
