"""Reason-specific conformance and scientific missingness denominators."""
import unittest
from tether_engine.serde import ContractError
from tools.review.conformance import score_conformance


class ReportingTests(unittest.TestCase):
    oracle = [dict(case_id='valid', decision='accept', reason_code=None),
              dict(case_id='invalid', decision='reject', reason_code='future_annotation')]

    def test_reject_all_gets_zero_valid_acceptance_and_cannot_qualify(self):
        result = score_conformance(self.oracle, [dict(case_id=row['case_id'], decision='reject', reason_code='deny_all') for row in self.oracle])
        self.assertEqual(result['valid_acceptance']['rate'], 0)
        self.assertEqual(result['reason_correct_rejection']['rate'], 0)
        self.assertFalse(result['qualification_passed'])

    def test_right_verdict_wrong_reason_gets_no_rejection_credit(self):
        actual = [self.oracle[0], dict(case_id='invalid', decision='reject', reason_code='parser_error')]
        result = score_conformance(self.oracle, actual)
        self.assertEqual(result['strict_case_agreement']['rate'], .5)
        self.assertEqual(result['reason_correct_rejection']['rate'], 0)
        self.assertFalse(result['qualification_passed'])

    def test_valid_acceptance_and_specific_rejection_pass_together(self):
        self.assertTrue(score_conformance(self.oracle, self.oracle)['qualification_passed'])

    def test_omissions_stay_in_scheduled_denominator(self):
        result = score_conformance(self.oracle, [])
        self.assertEqual(result['strict_case_agreement'], {'numerator': 0, 'denominator': 2, 'rate': 0})

    def test_legacy_oracle_without_reason_is_not_upgraded(self):
        with self.assertRaisesRegex(ContractError, 'specific rejection reason'):
            score_conformance([dict(case_id='legacy', decision='reject')], [])

    def test_only_negative_controls_cannot_qualify(self):
        result = score_conformance(self.oracle[1:], self.oracle[1:])
        self.assertIsNone(result['balanced_rate'])
        self.assertFalse(result['qualification_passed'])

    def test_identifiers_do_not_make_unknown_scientific_context_answerable(self):
        from tether_engine.study.source_fact_evaluation import _families
        facts = [dict(fact_id='id', record_key='r', family='identity_linkage', group='g', value='GENE'),
                 dict(fact_id='context', record_key='r', family='reported_context', group='g', value=None)]
        scores, _ = _families(facts, {'id'}, scorable=True)
        self.assertEqual(scores['identity_linkage']['coverage'], 1)
        self.assertEqual(scores['reported_context']['answerable_facts'], 0)
        self.assertIsNone(scores['reported_context']['coverage'])

    def test_empty_null_partial_complete_denominators(self):
        from tether_engine.study.source_fact_evaluation import _families
        def fact(key, value):
            return dict(fact_id=key, record_key='r', family='reported_measurement', group='g', value=value)
        for facts, matched, count, coverage in (([], set(), 0, None), ([fact('a', None)], set(), 0, None),
                ([fact('a', 1), fact('b', 2)], {'a'}, 2, .5),
                ([fact('a', 1), fact('b', 2)], {'a', 'b'}, 2, 1)):
            with self.subTest(count=count, coverage=coverage):
                score = _families(facts, matched, scorable=True)[0]['reported_measurement']
                self.assertEqual(score['answerable_facts'], count)
                self.assertEqual(score['coverage'], coverage)
