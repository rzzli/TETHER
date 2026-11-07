import copy
import unittest

from tether_engine.serde import ContractError, fingerprint
from tools.science.registry_content import (
    FIELDS, TABLES, appearance, classify_content, content_query, regenerate_query,
)


class RegistryContentTests(unittest.TestCase):
    def setUp(self):
        self.nct = 'NCT00000001'
        self.schema = {t: list(cols) for t, cols in FIELDS.items()}
        self.request = content_query([self.nct], '2025-01-01', self.schema)

    def record(self, present=False, snapshot='2025-01-01'):
        study = dict.fromkeys(FIELDS['studies'])
        study.update(nct_id=self.nct, last_update_posted_date='2024-12-20',
                     last_update_posted_date_type='ACTUAL')
        row = {'study': study, **{t: [] for t in TABLES}, 'table_counts': dict.fromkeys(TABLES, 0)}
        if present:
            study.update(results_first_posted_date='2024-12-01', results_first_posted_date_type='ACTUAL')
            row['outcomes'] = [{'id': 1, 'nct_id': self.nct}]
            row['result_groups'] = [{'id': 2, 'nct_id': self.nct, 'outcome_id': 1, 'ctgov_group_code': 'OG001'}]
            row['outcome_measurements'] = [{'id': 3, 'nct_id': self.nct, 'outcome_id': 1,
                                           'result_group_id': 2, 'ctgov_group_code': 'OG001'}]
        row['table_counts'] = {t: len(row[t]) for t in TABLES}
        return row

    def classified(self, row, request=None):
        return classify_content([row], request or self.request)['records'][0]

    def test_complete_empty_source_is_operational_absence_only(self):
        result = classify_content([self.record()], self.request)
        self.assertEqual('absent_in_snapshot', result['records'][0]['state'])
        self.assertFalse(result['transport_provenance_verified'])
        self.assertFalse(result['clinical_activation'])

    def test_partial_but_consistent_measurements_are_present(self):
        self.assertEqual('present', self.classified(self.record(True))['state'])
        row = self.record(True)
        row['result_groups'][0]['outcome_id'] = None  # shared result group, not necessarily outcome-specific
        self.assertEqual('present', self.classified(row)['state'])

    def test_read_only_minimal_projection_has_no_clinical_values_or_limits(self):
        sql = self.request['sql']
        self.assertTrue(sql.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;'))
        self.assertTrue(sql.endswith('ROLLBACK;'))
        for prohibited in ('SELECT *', ' LIMIT ', 'p_value', 'param_value', 'why_stopped', 'overall_status'):
            self.assertNotIn(prohibited, sql)
        self.assertIn('overflow', sql)
        self.assertFalse(self.request['execution_authorized'])

    def test_original_schema_and_rows_are_copied(self):
        original = copy.deepcopy(self.schema)
        request = content_query([self.nct], '2025-01-01', self.schema)
        self.schema['outcomes'].append('future_field')
        self.assertEqual(original, request['source_schema'])
        row = self.record(True)
        report = classify_content([row], request)
        digest = report['records'][0]['source_record_sha256']
        row['outcomes'][0]['id'] = 99
        self.assertEqual(digest, report['records'][0]['source_record_sha256'])

    def test_unrequested_and_duplicate_nct_envelopes_fail_batch(self):
        for rows in ([self.record(), self.record()], [self.record()]):
            if len(rows) == 1:
                rows[0]['study']['nct_id'] = 'NCT99999999'
            with self.subTest(rows=len(rows)), self.assertRaises(ContractError):
                classify_content(rows, self.request)

    def test_missing_nct_is_unknown_not_negative(self):
        item = classify_content([], self.request)['records'][0]
        self.assertEqual('unknown', item['state'])
        self.assertEqual(['missing_nct_record'], item['reasons'])

    def test_missing_table_or_linkage_column_never_becomes_empty_source(self):
        for table, column in [('outcome_measurements', None), ('result_groups', 'outcome_id')]:
            schema = copy.deepcopy(self.schema)
            if column is None:
                schema.pop(table)
            else:
                schema[table].remove(column)
            request = content_query([self.nct], '2025-01-01', schema)
            row = self.record()
            row[table] = None
            row['table_counts'][table] = None
            self.assertEqual('unknown', self.classified(row, request)['state'])
            row[table] = []
            row['table_counts'][table] = 0
            with self.assertRaises(ContractError):
                classify_content([row], request)

    def test_count_mismatch_missing_projection_and_overflow_fail_batch(self):
        for mode in ('count', 'extra', 'missing', 'overflow'):
            row = self.record()
            if mode == 'count':
                row['table_counts']['outcomes'] = 1
            elif mode == 'extra':
                row['study']['clinical_success'] = True
            elif mode == 'missing':
                del row['outcomes']
            else:
                row = {'overflow': True, 'nct_id': self.nct}
            with self.subTest(mode=mode), self.assertRaises(ContractError):
                classify_content([row], self.request)

    def test_cross_trial_child_and_boolean_ids_fail_batch(self):
        for field, value in [('nct_id', 'NCT00000002'), ('id', True)]:
            row = self.record(True)
            row['outcomes'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                classify_content([row], self.request)

    def test_orphan_measurements_and_group_scope_are_unknown_even_with_valid_row(self):
        for mode in ('orphan', 'group_outcome', 'group_code', 'group_orphan', 'bool_link'):
            row = self.record(True)
            extra = copy.deepcopy(row['outcome_measurements'][0])
            extra['id'] = 4
            row['outcome_measurements'].append(extra)
            row['table_counts']['outcome_measurements'] = 2
            if mode == 'orphan':
                extra['result_group_id'] = 999
            elif mode == 'group_outcome':
                row['outcomes'].append({'id': 99, 'nct_id': self.nct})
                row['table_counts']['outcomes'] = 2
                row['result_groups'][0]['outcome_id'] = 99
            elif mode == 'group_code':
                extra['ctgov_group_code'] = 'WRONG'
            elif mode == 'group_orphan':
                row['result_groups'][0]['outcome_id'] = 999
            else:
                extra['outcome_id'] = True
            with self.subTest(mode=mode):
                self.assertEqual('unknown', self.classified(row)['state'])

    def test_duplicate_source_keys_are_unknown_and_unsorted_rows_fail(self):
        row = self.record(True)
        row['outcomes'] *= 2
        row['table_counts']['outcomes'] = 2
        self.assertEqual('unknown', self.classified(row)['state'])
        row['outcomes'] = [{'id': 2, 'nct_id': self.nct}, {'id': 1, 'nct_id': self.nct}]
        with self.assertRaises(ContractError):
            classify_content([row], self.request)

    def test_result_flag_and_payload_disagreement_is_unknown(self):
        row = self.record()
        row['study'].update(results_first_posted_date='2024-12-01', results_first_posted_date_type='ACTUAL')
        self.assertIn('posting_date_without_measurements', self.classified(row)['reasons'])
        row = self.record(True)
        row['study'].update(results_first_posted_date=None, results_first_posted_date_type=None)
        self.assertIn('measurements_without_posting_date', self.classified(row)['reasons'])

    def test_missing_version_or_future_dates_are_unknown(self):
        for field, value in [('last_update_posted_date', None), ('last_update_posted_date', '2025-01-02'),
                             ('last_update_posted_date', '2024-02-30'),
                             ('last_update_posted_date_type', 'ESTIMATED'),
                             ('results_first_posted_date', '2025-01-02'),
                             ('results_first_posted_date', '2024-12'),
                             ('results_first_posted_date_type', 'ESTIMATED')]:
            row = self.record(True)
            row['study'][field] = value
            with self.subTest(field=field, value=value):
                self.assertEqual('unknown', self.classified(row)['state'])

    def test_missing_study_date_column_is_explicit_unknown(self):
        schema = copy.deepcopy(self.schema)
        schema['studies'].remove('results_first_posted_date_type')
        request = content_query([self.nct], '2025-01-01', schema)
        row = self.record()
        del row['study']['results_first_posted_date_type']
        self.assertEqual('unknown', self.classified(row, request)['state'])

    def test_self_hash_cannot_authorize_or_rewrite_sql(self):
        for field, value in [('execution_authorized', True), ('role', 'agent_evidence'),
                             ('sql', 'DELETE FROM ctgov.studies;'), ('max_output_bytes', 2**40)]:
            request = copy.deepcopy(self.request)
            request[field] = value
            request['contract_sha256'] = fingerprint({k: v for k, v in request.items() if k != 'contract_sha256'})
            with self.subTest(field=field), self.assertRaises(ContractError):
                regenerate_query(request)

    def test_stage_caps_and_injected_names_fail(self):
        ids = [f'NCT{i:08d}' for i in range(1, 130)]
        for members, snapshot in [(ids, '2025-01-01'), (ids[:33], '2026-01-01'),
                                  ([], '2025-01-01'), ([self.nct, self.nct], '2025-01-01'),
                                  (["NCT00000001'); DROP TABLE x;"], '2025-01-01'),
                                  ([self.nct], '2026-02-01')]:
            with self.subTest(snapshot=snapshot, count=len(members)), self.assertRaises(ContractError):
                content_query(members, snapshot, self.schema)
        for cap in (True, 0, 100001):
            with self.assertRaises(ContractError):
                content_query([self.nct], '2025-01-01', self.schema, max_rows_per_trial=cap)

    def test_unknown_schema_columns_are_never_interpolated(self):
        self.schema['studies'].append('x; DELETE FROM ctgov.studies')
        request = content_query([self.nct], '2025-01-01', self.schema)
        self.assertNotIn('DELETE', request['sql'])
        self.assertEqual(request, regenerate_query(request))

    def test_row_bound_cannot_silently_drop_measurements(self):
        request = content_query([self.nct], '2025-01-01', self.schema, max_rows_per_trial=2)
        with self.assertRaises(ContractError):
            classify_content([self.record(True)], request)

    def test_all_nine_state_combinations_preserve_origin_risk_and_unknowns(self):
        for origin in ('present', 'absent_in_snapshot', 'unknown'):
            for endpoint in ('present', 'absent_in_snapshot', 'unknown'):
                o = {'nct_id': self.nct, 'snapshot_date': '2025-01-01', 'state': origin}
                e = {'nct_id': self.nct, 'snapshot_date': '2026-01-01', 'state': endpoint}
                value = appearance(o, e, endpoint_snapshot='2026-01-01')
                expected = None if origin != 'absent_in_snapshot' or endpoint == 'unknown' else int(endpoint == 'present')
                self.assertEqual(expected, value['operational_value'])
                self.assertIsNone(value['clinical_label'])
                self.assertIsNone(value['probability'])
                self.assertEqual({}, value['features'])

    def test_april_view_never_backfills_january(self):
        origin = {'nct_id': self.nct, 'snapshot_date': '2025-01-01', 'state': 'absent_in_snapshot'}
        april = {'nct_id': self.nct, 'snapshot_date': '2026-04-01', 'state': 'present'}
        self.assertEqual('april_sensitivity', appearance(origin, april, endpoint_snapshot='2026-04-01')['view'])
        with self.assertRaises(ContractError):
            appearance(origin, april, endpoint_snapshot='2026-01-01')
        april['nct_id'] = 'NCT00000002'
        with self.assertRaises(ContractError):
            appearance(origin, april, endpoint_snapshot='2026-04-01')


if __name__ == '__main__':
    unittest.main()
