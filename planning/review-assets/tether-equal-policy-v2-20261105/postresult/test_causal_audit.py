"""Small invented-outcome controls; never reads a real comparison result."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('causal_audit_under_test', Path(__file__).with_name('causal_audit.py'))
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def fictional_cell(cid='EP075', decision='reject', reason='Replay/request fingerprint mismatch',
                    expected='reject', conformant=True, disposition='returned', arm='tether', mismatches=None):
    record = dict(implementation=arm, repetition=1, disposition=disposition,
        result=dict(decision=decision, reason=reason, observables={}))
    oracle = dict(control_id=cid, decision=expected)
    primary = dict(expected_decision=expected, observed_decision=decision,
        fully_conformant=conformant, observable_mismatches=mismatches or {})
    return record, oracle, primary


class SupplementalReviewTests(unittest.TestCase):
    def test_replay_correct_and_wrong_causes_are_distinguished(self):
        good = AUDIT.review_cell(*fictional_cell())
        wrong = AUDIT.review_cell(*fictional_cell(reason='Dossier prose differs from deterministic rendering'))
        self.assertEqual(good['causal_review'], 'first_reported_reason_matches_intended_fault')
        self.assertTrue(wrong['primary_fully_conformant'])
        self.assertEqual(wrong['causal_review'], 'manual_review_unmatched_rejection_reason')

    def test_false_admission_is_retained_without_expectation_of_parity(self):
        row = AUDIT.review_cell(*fictional_cell(decision='accept', conformant=False, reason=''))
        self.assertEqual(row['causal_review'], 'intended_rejection_not_observed')
        self.assertFalse(row['primary_fully_conformant'])

    def test_error_and_unsupported_are_not_correct_rejections(self):
        for decision, disposition in [('error', 'crash'), ('unsupported', 'returned')]:
            with self.subTest(decision=decision):
                row = AUDIT.review_cell(*fictional_cell(decision=decision, disposition=disposition, conformant=False))
                self.assertEqual(row['causal_review'], 'execution_or_interface_failure')

    def test_valid_recorded_parent_preserves_primary_observable_failure(self):
        mismatch = {'dispatches': {'expected': 1, 'actual': 0}}
        row = AUDIT.review_cell(*fictional_cell(cid='EP109', decision='accept', expected='accept',
            conformant=False, mismatches=mismatch))
        self.assertEqual(row['causal_review'], 'valid_control_mismatch')
        self.assertEqual(row['primary_observable_mismatches'], mismatch)

    def test_corrupt_chain_and_lineage_escape_have_specific_causes(self):
        for cid, reason in [('EP023', 'Observation lineage escapes packet'), ('EP077', 'Journal chain mismatch')]:
            self.assertEqual(AUDIT.review_cell(*fictional_cell(cid=cid, reason=reason))['causal_review'],
                'first_reported_reason_matches_intended_fault')
        self.assertEqual(AUDIT.review_cell(*fictional_cell(cid='EP023', reason='Source byte mismatch'))['causal_review'],
            'manual_review_unmatched_rejection_reason')

    def test_weak_control_rejection_does_not_establish_full_policy(self):
        self.assertEqual(AUDIT.review_cell(*fictional_cell(arm='reject_all'))['causal_review'],
            'diagnostic_control_not_full_policy_witness')

    def test_primary_decision_cannot_diverge_from_actual(self):
        record, oracle, primary = fictional_cell()
        primary['observed_decision'] = 'accept'
        with self.assertRaisesRegex(ValueError, 'Primary row decision differs'):
            AUDIT.review_cell(record, oracle, primary)

    def test_terminal_gate_rejects_missing_duplicate_and_unexposed_cases(self):
        cases = [dict(control_id=f'EP{n:03}') for n in range(1, 110)]
        frozen = dict(cases=cases, implementations=list(AUDIT.ARMS), settings={'repetitions': 3})
        oracle = [dict(**c, construction_stratum='exposed_authored_construction') for c in cases]
        refs = [dict(cell=f'{c["control_id"]}-r{rep}-{arm}') for c in cases for rep in (1, 2, 3) for arm in AUDIT.ARMS]
        execution = dict(status='executed', expected_cells=1308, terminal_cells=1308, records=refs, after_checks={'frozen': True})
        self.assertEqual(len(AUDIT.terminal_grid(frozen, execution, oracle)), 1308)
        for mutation in [dict(records=refs[:-1]), dict(records=refs[:-1] + [refs[0]]),
                         dict(status='incomplete_or_changed'), dict(after_checks={'frozen': False})]:
            with self.subTest(mutation=list(mutation)):
                with self.assertRaises(ValueError):
                    AUDIT.terminal_grid(frozen, execution | mutation, oracle)
        oracle[-1]['construction_stratum'] = 'held_out'
        with self.assertRaisesRegex(ValueError, 'Exposure differs'):
            AUDIT.terminal_grid(frozen, execution, oracle)


if __name__ == '__main__':
    unittest.main(verbosity=2)
