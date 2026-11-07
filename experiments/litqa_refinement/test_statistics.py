"""Invented fixed-estimand tests; no released task data or keys."""
import copy
import unittest

from experiments.litqa_analysis.test_scoring import fixture, failure
from experiments.litqa_analysis.metrics import paired_bootstrap as original_bootstrap
from experiments.litqa_refinement import statistics as s


def inputs():
    queries, references, baseline, offered = fixture(4)
    baseline[1]['prediction']['answer_index'] = 1
    baseline[2]['prediction']['answer_index'] = 2
    failure(baseline[3])
    repaired = copy.deepcopy(baseline)
    repaired[0]['prediction']['answer_index'] = 1
    repaired[1]['prediction']['answer_index'] = 0
    repaired[2]['prediction']['answer_index'] = 0
    repaired[3].update(producer_status='produced', check_status='accepted', reason=None,
                       prediction=dict(answer_index=0, evidence_ids=['s0']))
    removed = copy.deepcopy(repaired)
    for row in removed:
        row['prediction']['evidence_ids'] = []
        row.update(check_status='rejected', reason='raw_source_removal_mechanically_rejects_substantive_answer')
    critics = [dict(id=q['id'], native_status='completed', decoded=dict(support='insufficient')) for q in queries]
    return dict(queries=queries, references=references,
                records=dict(one_pass=baseline, repair=repaired, removal=removed),
                offered=dict(one_pass=offered, repair=offered, removal={q['id']: [] for q in queries}),
                critics=critics, groups=[(q['id'],) for q in queries], purpose='fictional_qualification')


class StatisticsTests(unittest.TestCase):
    def test_full_denominator_native_unchanged_selection_and_transition_categories(self):
        value = inputs()
        old = copy.deepcopy(value)
        out = s.summarize(**value)
        self.assertEqual(value, old)
        self.assertEqual(out['scheduled_count'], 4)
        self.assertEqual(out['native']['one_pass'], out['native']['critique_only'])
        self.assertEqual(out['conditions']['one_pass']['correct_retained'], 1)
        self.assertEqual(out['conditions']['critique_only']['correct_retained'], 0)
        self.assertIsNone(out['conditions']['critique_only']['statistical_retained_precision'])
        self.assertFalse(out['conditions']['critique_only']['retained_precision_defined'])
        self.assertEqual(out['semantic_selection']['false_withholding'], 1)
        self.assertEqual(out['repair_transitions']['counts'], dict(repaired_wrong_substantive=1,
            recovered_original_operational_failure=1, recovered_original_unsure=1, damaged_correct=1,
            persistent_wrong_substantive=0))
        self.assertEqual(out['native']['repair']['counts']['raw_correct'], 3)
        self.assertEqual(out['repair_transitions']['raw_answer_changes'], dict(
            both_produced=3, answer_index_changed=3, answer_index_unchanged=0, unavailable_pair=1))
        self.assertEqual(out['removal_diagnostic']['native']['counts']['correct_and_admitted'], 0)
        self.assertEqual(out['primary_contrasts']['critique_only_minus_one_pass']['raw_accuracy']
                         ['publication_components']['ci95'], [0, 0])
        self.assertEqual(out['primary_contrasts']['repair_minus_one_pass']['correct_retained_yield']
                         ['publication_components']['estimate'], .5)
        self.assertFalse(out['provenance_validated'])

    def test_adapter_uses_original_sampler_and_same_cluster_weighted_ratio(self):
        ids = ('a', 'b', 'c')
        left = (0, 0, 1)
        right = (1, 1, 1)
        groups = (('a', 'b'), ('c',))
        got = s.paired_bootstrap(ids, left, right, groups)
        old = original_bootstrap(ids, {'L/O': left, 'E/O': right, 'L/R': left, 'E/R': right}, groups)
        self.assertEqual(got['ci95'], old['contrasts']['expansion_at_lexical']['ci95'])
        self.assertAlmostEqual(got['estimate'], 2/3)
        self.assertEqual(got['group_sizes'], [2, 1])
        self.assertEqual(got['completed_replicates'], 10000)

    def test_one_group_has_no_invented_interval(self):
        got = s.paired_bootstrap(('a', 'b'), (False, False), (True, True), (('a', 'b'),))
        self.assertIsNone(got['ci95'])
        self.assertEqual(got['completed_replicates'], 0)
        self.assertFalse(got['uncertainty_estimable'])

    def test_production_exact_membership_and_duplicate_or_missing_group_rejected(self):
        ids = [str(i) for i in range(199)]
        groups = [[str(i)] for i in range(176)]
        groups += [[str(i), str(i+1)] for i in range(176, 190, 2)]
        groups += [[str(i), str(i+1), str(i+2)] for i in range(190, 199, 3)]
        s.membership(ids, groups, 'production')
        for bad in (groups[:-1], groups+[['0']], [[x] for x in ids]):
            with self.assertRaises(ValueError): s.membership(ids, bad, 'production')
        with self.assertRaises(ValueError): s.membership(('a', 'b'), [('a',), ('b',)], 'production')

    def test_unsupported_critique_cannot_resurrect_rejected_candidate(self):
        value = inputs()
        value['records']['one_pass'][0].update(check_status='rejected', reason='source_check')
        value['critics'][0]['decoded']['support'] = 'supported'
        out = s.summarize(**value)
        self.assertEqual(out['conditions']['critique_only']['retained'], 0)
        self.assertEqual(out['semantic_selection']['case_results'][0]['reason'], 'original_not_admitted')
        self.assertEqual(out['semantic_selection']['false_withholding'], 0)
        self.assertIsNone(out['semantic_selection']['false_withholding_rate'])

    def test_missing_reordered_and_fabricated_critic_statuses_fail(self):
        for change in ('missing', 'reorder', 'status', 'extra_field', 'invalid_support'):
            value = inputs()
            if change == 'missing': value['records']['repair'].pop()
            if change == 'reorder': value['critics'].reverse()
            if change == 'status': value['critics'][0]['native_status'] = 'withheld'
            if change == 'extra_field': value['critics'][0]['correct'] = True
            if change == 'invalid_support': value['critics'][0]['decoded']['support'] = 'probably'
            with self.subTest(change=change), self.assertRaises(ValueError): s.summarize(**value)

    def test_removal_cannot_admit_substantive_or_receive_sources(self):
        for change in ('admit', 'source'):
            value = inputs()
            if change == 'admit': value['records']['removal'][0].update(check_status='accepted', reason=None)
            else: value['offered']['removal'][value['queries'][0]['id']] = ['s0']
            with self.subTest(change=change), self.assertRaises(ValueError): s.summarize(**value)


if __name__ == '__main__':
    unittest.main()
