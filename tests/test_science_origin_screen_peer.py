"""Independent origin-screen probes; no production database or outcome reads."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError
from tools.science.origin_maturity import maturity_reasons, select_candidates, select_mature
from tools.science.outcome_inputs import study_query, validate_study_rows
from tests import test_science_origin_review as source_fixture
from tests import test_science_outcome_inputs as row_fixture


class OriginScreenPeerTests(unittest.TestCase):
    def metadata(self, nct, measure='Prospective primary objective'):
        return {'study': {'nct_id': nct, 'primary_completion_month_year': 'June 2025',
            'primary_completion_date_type': 'ESTIMATED', 'last_update_posted_date': '2024-12-27',
            'last_update_posted_date_type': 'ACTUAL', 'study_first_posted_date': '2020-01-01'},
            'design_outcomes': [{'outcome_type': 'PRIMARY', 'measure': measure}]}

    def candidates(self):
        return [{'nct_id': f'NCT{i:08}', 'program_id': f'P{i}',
            'program': {'qualification_holds': ['same_program_scope_not_established']}}
            for i in range(1, 4)]

    def validation(self, candidates):
        return {'status': 'study_rows_validated', 'version_dispositions': [
            {'nct_id': c['nct_id'], 'version_eligibility': {'status': 'eligible_reconstructed_date_bound'}}
            for c in candidates], 'eligible_reconstructed_rows': [self.metadata(c['nct_id']) for c in candidates]}

    def test_blank_primary_objective_cannot_define_maturity(self):
        for measure in (' ', '\t\r\n', '\u2003'):
            with self.subTest(measure=repr(measure)):
                self.assertIn('no_recorded_planned_primary_outcome',
                    maturity_reasons(self.metadata('NCT00000001', measure))[0])

    def test_held_or_missing_disposition_cannot_carry_eligible_payload(self):
        candidates = self.candidates()
        for status in ('held_boundary_uncertain', None):
            validation = self.validation(candidates)
            if status is None:
                validation['version_dispositions'].pop(0)
            else:
                validation['version_dispositions'][0]['version_eligibility']['status'] = status
            with self.subTest(status=status), self.assertRaises(ContractError):
                select_mature(candidates, validation, requested=1)

    def test_forged_eligible_declaration_cannot_admit_future_or_boundary_source(self):
        candidates = self.candidates()
        for source_changes in ({'last_update_posted_date': '2025-01-01'},
                {'last_update_posted_date': '2025-02-01'},
                {'last_update_posted_date_type': None},
                {'last_update_posted_date_type': 'ESTIMATED'},
                {'study_first_posted_date': '2025-02-01'}):
            validation = self.validation(candidates)
            validation['eligible_reconstructed_rows'][0]['study'].update(source_changes)
            with self.subTest(source_changes=source_changes), self.assertRaises(ContractError):
                select_mature(candidates, validation, requested=1)

    def test_unknown_future_fields_cannot_enter_origin_maturity_envelope(self):
        for level, key in (('study', 'efficacy_success'), ('envelope', 'future_decision'),
                ('primary', 'p_value')):
            row = self.metadata('NCT00000001')
            if level == 'study':
                row['study'][key] = True
            elif level == 'primary':
                row['design_outcomes'][0][key] = 0.001
            else:
                row[key] = 'success'
            with self.subTest(level=level), self.assertRaises(ContractError):
                maturity_reasons(row)

    def test_actual_source_validator_holds_boundary_and_future_postings(self):
        candidates = self.candidates()
        request = study_query([c['nct_id'] for c in candidates], '2025-01-01', row_fixture.schema(), max_ids=128)
        rows = []
        for candidate, posted in zip(candidates, ('2024-12-27', '2025-01-01', '2025-02-01')):
            row = row_fixture.study(request, candidate['nct_id'], last_update_posted_date=posted,
                primary_completion_month_year='June 2025', primary_completion_date_type='Estimated')
            objective = dict.fromkeys(request['projection']['design_outcomes'])
            objective.update(id=1, nct_id=candidate['nct_id'], outcome_type='Primary', measure='Safety-only objective')
            row['design_outcomes'] = [objective]
            rows.append(row)
        validation = validate_study_rows(rows, request)
        selected, screen = select_mature(candidates, validation, requested=1)
        self.assertEqual('NCT00000001', selected[0]['candidate']['nct_id'])
        self.assertEqual(['origin_version_held'], screen[1]['reasons'])
        self.assertEqual(['origin_version_held'], screen[2]['reasons'])
        self.assertFalse(selected[0]['scientific_qualification'])
        self.assertIsNone(selected[0]['clinical_label'])

    def test_maturity_does_not_erase_scope_holds_or_exclude_safety_objectives(self):
        candidates = self.candidates()
        validation = self.validation(candidates)
        validation['eligible_reconstructed_rows'][0]['design_outcomes'][0]['measure'] = 'Safety/tolerability only'
        before = copy.deepcopy(candidates)
        selected, _ = select_mature(candidates, validation, requested=2)
        self.assertEqual(before, candidates)
        self.assertEqual(candidates[:2], [s['candidate'] for s in selected])
        self.assertEqual(['same_program_scope_not_established'],
            selected[0]['candidate']['program']['qualification_holds'])

    def test_raw_missing_or_year_precision_cannot_be_replaced_by_aact_day(self):
        row = self.metadata('NCT00000001')
        row['study'].update(primary_completion_month_year='2025', primary_completion_date='2026-02-01')
        reasons, interval = maturity_reasons(row)
        self.assertEqual([], reasons)
        self.assertEqual(('2025-01-01', '2025-12-31', 'year'),
            (interval['lower_date'], interval['upper_date'], interval['precision']))
        row['study']['primary_completion_month_year'] = None
        row['study']['primary_completion_date'] = '2025-06-01'
        self.assertIn('planned_primary_completion_not_wholly_calendar2025', maturity_reasons(row)[0])

    def test_new_128_projection_cannot_include_results_or_shift_cutoff(self):
        ids = [f'NCT{i:08}' for i in range(1, 129)]
        request = study_query(ids, '2025-01-01', row_fixture.schema(), max_ids=128)
        self.assertEqual(128, len(request['nct_ids']))
        self.assertNotIn('results_first_posted_date', request['sql'])
        self.assertNotIn('why_stopped', request['sql'])
        for kwargs in ({'cutoff_at': '2026-04-01T00:00:00Z'},
                {'requested_columns': {'studies': ['nct_id', 'results_first_posted_date']}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ContractError):
                study_query(ids, '2025-01-01', row_fixture.schema(), max_ids=128, **kwargs)

    def test_selection_proofs_locate_original_bytes_and_keep_all_scientific_holds(self):
        with tempfile.TemporaryDirectory(prefix='origin-screen-peer-') as temporary:
            root = Path(temporary).resolve()
            freeze, _, _ = source_fixture.OriginReviewTests().fixture(root, number=5)
            source = freeze.parent / 'origin-programs.jsonl'
            original = [json.loads(raw) for raw in source.read_bytes().splitlines()]
            selected, pool = select_candidates(source, [original[0]['nct_id']], salt='peer-fixed', maximum=3)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), pool['parent_program_sha256'])
            for selected_row in selected:
                proof = selected_row['program_row']
                with source.open('rb') as stream:
                    stream.seek(proof['byte_offset'])
                    raw = stream.read(proof['bytes'])
                self.assertEqual(proof['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(selected_row['program'], json.loads(raw))
                self.assertIn('same_program_scope_not_established', selected_row['program']['qualification_holds'])
                self.assertNotIn(original[0]['nct_id'], [c['nct_id'] for c in selected])


if __name__ == '__main__':
    unittest.main()
