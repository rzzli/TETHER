"""Independent synthetic B0 contract checks; no retained outcomes or dispatch."""
import copy
import unittest

from tether_engine.serde import ContractError
from tools.science.registry_content import (
    FIELDS, TABLES, appearance, classify_content, content_query,
)


class RegistryContentPeerTests(unittest.TestCase):
    def schema(self):
        return {table: list(columns) for table, columns in FIELDS.items()}

    def envelope(self, nct='NCT00000001', present=False):
        study = dict.fromkeys(FIELDS['studies'])
        study.update(nct_id=nct, last_update_posted_date='2024-12-20',
                     last_update_posted_date_type='ACTUAL')
        row = {'study': study, **{table: [] for table in TABLES}}
        if present:
            study.update(results_first_posted_date='2024-12-10',
                         results_first_posted_date_type='ACTUAL')
            row['outcomes'] = [{'id': 11, 'nct_id': nct}]
            row['result_groups'] = [{'id': 22, 'nct_id': nct, 'outcome_id': 11,
                                     'ctgov_group_code': None}]
            row['outcome_measurements'] = [{'id': 33, 'nct_id': nct,
                                           'outcome_id': 11, 'result_group_id': 22,
                                           'ctgov_group_code': None}]
        row['table_counts'] = {table: len(row[table]) for table in TABLES}
        return row

    def test_every_missing_required_column_blocks_binary_state(self):
        for table, columns in FIELDS.items():
            for column in columns:
                with self.subTest(table=table, column=column):
                    schema = self.schema()
                    schema[table].remove(column)
                    if table == 'studies' and column == 'nct_id':
                        with self.assertRaises(ContractError):
                            content_query(['NCT00000001'], '2025-01-01', schema)
                        continue
                    request = content_query(['NCT00000001'], '2025-01-01', schema)
                    row = self.envelope()
                    if table == 'studies':
                        del row['study'][column]
                    else:
                        row[table] = None
                        row['table_counts'][table] = None
                    state = classify_content([row], request)['records'][0]
                    self.assertEqual('unknown', state['state'])
                    self.assertIn('missing_required_columns:' + table, state['reasons'])

    def test_missing_member_is_retained_in_canonical_order(self):
        members = ['NCT00000003', 'NCT00000002', 'NCT00000001']
        request = content_query(members, '2025-01-01', self.schema())
        records = classify_content([self.envelope('NCT00000001'),
                                    self.envelope('NCT00000003')], request)['records']
        self.assertEqual(sorted(members), [row['nct_id'] for row in records])
        self.assertEqual(['absent_in_snapshot', 'unknown', 'absent_in_snapshot'],
                         [row['state'] for row in records])

    def test_later_content_with_old_posting_date_is_not_recast_as_new_publication(self):
        origin_query = content_query(['NCT00000001'], '2025-01-01', self.schema())
        endpoint_query = content_query(['NCT00000001'], '2026-01-01', self.schema())
        origin = classify_content([self.envelope()], origin_query)['records'][0]
        endpoint = classify_content([self.envelope(present=True)], endpoint_query)['records'][0]
        contrast = appearance(origin, endpoint, endpoint_snapshot='2026-01-01')
        # The old posting date may reflect a changed/backfilled registry record.
        # B0 measures retained source content, not first-ever public disclosure.
        self.assertEqual(1, contrast['operational_value'])
        self.assertEqual('january_primary', contrast['view'])
        self.assertIsNone(contrast['clinical_label'])
        self.assertFalse(contrast['transport_provenance_verified'])

    def test_posting_after_record_update_is_unknown_even_before_snapshot(self):
        row = self.envelope(present=True)
        row['study']['results_first_posted_date'] = '2024-12-21'
        request = content_query(['NCT00000001'], '2025-01-01', self.schema())
        state = classify_content([row], request)['records'][0]
        self.assertEqual('unknown', state['state'])
        self.assertIn('unqualified_results_posting_date', state['reasons'])

    def test_unreferenced_orphan_group_overrides_valid_measurement(self):
        row = self.envelope(present=True)
        row['result_groups'].append({'id': 23, 'nct_id': 'NCT00000001',
                                     'outcome_id': 999, 'ctgov_group_code': None})
        row['table_counts']['result_groups'] = 2
        original = copy.deepcopy(row)
        request = content_query(['NCT00000001'], '2025-01-01', self.schema())
        state = classify_content([row], request)['records'][0]
        self.assertEqual('unknown', state['state'])
        self.assertIn('orphan_group_outcome', state['reasons'])
        self.assertEqual(original, row)

    def test_empty_child_tables_do_not_override_missing_record_date(self):
        row = self.envelope()
        row['study']['last_update_posted_date'] = None
        request = content_query(['NCT00000001'], '2025-01-01', self.schema())
        state = classify_content([row], request)['records'][0]
        self.assertEqual('unknown', state['state'])
        self.assertIn('unqualified_record_version_date', state['reasons'])


if __name__ == '__main__':
    unittest.main()
