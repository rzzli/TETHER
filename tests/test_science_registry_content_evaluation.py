import copy
import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError, fingerprint
from tools.science.registry_content_evaluation import audit_native_rows, compare_states, dependence_diagnostics
from tools.science.registry_content_workflow import pin


class RegistryContentEvaluationTests(unittest.TestCase):
    def fixture(self, n=10):
        members = [f'NCT{i:08d}' for i in range(1, n + 1)]
        def states(when, state):
            return {'records': [{'nct_id': m, 'snapshot_date': when, 'state': state, 'reasons': []}
                                for m in members]}
        return members, states('2025-01-01', 'absent_in_snapshot'), {
            '2026-01-01': states('2026-01-01', 'absent_in_snapshot'),
            '2026-04-01': states('2026-04-01', 'absent_in_snapshot')}

    def test_all_absent_stops_prediction_without_clinical_failure(self):
        result = compare_states(*self.fixture())
        self.assertEqual('stop_operational_prediction_expansion', result['decision'])
        self.assertTrue(result['coverage_pass'])
        self.assertFalse(result['both_classes_observed'])
        self.assertFalse(result['clinical_activation'])
        self.assertFalse(result['training_allowed'])
        self.assertIsNone(result['probabilities'])

    def test_both_classes_and_coverage_allow_only_a_larger_feasibility_design(self):
        members, origin, frames = self.fixture()
        frames['2026-01-01']['records'][0]['state'] = 'present'
        result = compare_states(members, origin, frames)
        self.assertEqual('larger_feasibility_design_only', result['decision'])
        self.assertEqual(1, result['views']['2026-01-01']['appearance'])
        self.assertFalse(result['training_allowed'])

    def test_unknowns_remain_in_denominator_at_fixed_threshold(self):
        members, origin, frames = self.fixture()
        records = frames['2026-01-01']['records']
        records[0]['state'] = 'present'
        records[1].update(state='unknown', reasons=['missing_nct_record'])
        result = compare_states(members, origin, frames)
        self.assertTrue(result['coverage_pass'])  # exactly .9
        self.assertEqual(10, result['views']['2026-01-01']['selected_denominator'])
        records[2].update(state='unknown', reasons=['posting_conflict'])
        result = compare_states(members, origin, frames)
        self.assertFalse(result['coverage_pass'])
        self.assertEqual('stop_operational_prediction_expansion', result['decision'])
        self.assertEqual(2, result['views']['2026-01-01']['unknown'])

    def test_april_appearance_cannot_change_primary_decision(self):
        members, origin, frames = self.fixture()
        frames['2026-04-01']['records'][0]['state'] = 'present'
        result = compare_states(members, origin, frames)
        self.assertEqual(0, result['views']['2026-01-01']['appearance'])
        self.assertEqual(1, result['views']['2026-04-01']['appearance'])
        self.assertEqual('stop_operational_prediction_expansion', result['decision'])

    def test_duplicates_extra_members_and_substituted_dates_fail(self):
        for mode in ('duplicate', 'extra', 'date', 'missing'):
            members, origin, frames = self.fixture()
            rows = frames['2026-01-01']['records']
            if mode == 'duplicate':
                rows.append(copy.deepcopy(rows[0]))
            elif mode == 'extra':
                rows[0]['nct_id'] = 'NCT99999999'
            elif mode == 'date':
                rows[0]['snapshot_date'] = '2026-04-01'
            else:
                frames.pop('2026-01-01')
            with self.subTest(mode=mode), self.assertRaises(ContractError):
                compare_states(members, origin, frames)

    def test_nonrisk_origin_and_invalid_membership_cap_fail(self):
        members, origin, frames = self.fixture()
        origin['records'][0]['state'] = 'present'
        with self.assertRaises(ContractError):
            compare_states(members, origin, frames)
        for size in (0, 33):
            with self.assertRaises(ContractError):
                compare_states(*self.fixture(size))

    def test_native_source_byte_locator_and_row_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'rows.jsonl'
            nct = 'NCT00000001'
            native = {'study': {'nct_id': nct}, 'table_counts': {'outcomes': 0, 'result_groups': 0, 'outcome_measurements': 0},
                      'outcomes': [], 'result_groups': [], 'outcome_measurements': []}
            path.write_bytes((json.dumps(native) + '\n').encode())
            state = {'nct_id': nct, 'state': 'absent_in_snapshot', 'source_record_sha256': fingerprint(native), 'reasons': []}
            frames = {'2025-01-01': {'source': pin(path), 'states': {'records': [state]}}}
            result = audit_native_rows([nct], frames)
            self.assertEqual({'line_1based': 1, 'byte_offset': 0, 'byte_length': path.stat().st_size}, result[0]['native_locator'])
            self.assertEqual([], result[0]['native_row_ids']['outcome_measurements'])
            state['source_record_sha256'] = '0' * 64
            with self.assertRaises(ContractError):
                audit_native_rows([nct], frames)

    def test_missing_native_record_is_unknown_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'empty.jsonl'
            path.write_bytes(b'')
            nct = 'NCT00000001'
            state = {'nct_id': nct, 'state': 'unknown', 'reasons': ['missing_nct_record']}
            frames = {'2026-01-01': {'source': pin(path), 'states': {'records': [state]}}}
            result = audit_native_rows([nct], frames)
            self.assertIsNone(result[0]['native_locator'])
            state['state'] = 'absent_in_snapshot'
            with self.assertRaises(ContractError):
                audit_native_rows([nct], frames)

    def test_origin_dependency_keys_are_descriptive_not_independent_counts(self):
        members = ['NCT00000001', 'NCT00000002', 'NCT00000003']
        candidates = [{'nct_id': n, 'program': {'dependence_keys': {
            'target': ['target:shared'] if index < 2 else [],
            'sponsor_verbatim': ['sponsor:shared'] if index > 0 else []}}}
            for index, n in enumerate(members)]
        result = dependence_diagnostics(members, candidates)
        self.assertEqual(1, result['observed_joint_key_components'])
        self.assertEqual(1, result['dimensions']['target']['members_with_missing_keys'])
        self.assertIsNone(result['effective_sample_size'])

    def test_dependency_context_cannot_silently_drop_a_selected_member(self):
        with self.assertRaises(ContractError):
            dependence_diagnostics(['NCT00000001'], [])


if __name__ == '__main__':
    unittest.main()
