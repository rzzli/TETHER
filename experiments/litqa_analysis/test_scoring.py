"""Invented score controls and parity against the retained native scorer."""
import copy
import random
import unittest

from experiments.labbench.evaluate import evaluate_schedule, source_annotation_metrics
from experiments.litqa_analysis.scoring import score_arm, paper_metrics, factorial, transitions


def fixture(n=8):
    ids = [f'00000000-0000-0000-0000-{i:012d}' for i in range(n)]
    q = [dict(id=i, question='Invented comparison?', choices=[
        '(A) Up', '(B) Down', '(C) Insufficient information to answer the question']) for i in ids]
    r = [dict(id=i, answer_index=0, unsure_index=2) for i in ids]
    rows = [dict(id=i, producer_status='produced', check_status='accepted',
        prediction=dict(answer_index=0, evidence_ids=['s0']), reason=None) for i in ids]
    return q, r, rows, {i: ['s0'] for i in ids}


def failure(row, status='parse_failure', reason='codec_failure'):
    row.update(producer_status=status, check_status='not_run', prediction=None, reason=reason)


class ScoringTests(unittest.TestCase):
    def test_mixed_outcomes_and_full_denominator(self):
        q, refs, rows, offered = fixture()
        rows[1]['prediction']['answer_index'] = 1
        rows[2]['prediction']['answer_index'] = 2
        failure(rows[3]); failure(rows[4], 'input_unavailable', 'capacity')
        rows[5].update(check_status='rejected', reason='lineage')
        rows[6].update(check_status='error', reason='verification interrupted')
        rows[7].update(check_status='not_run', reason='not checked')
        got = score_arm(q, refs, rows, offered)
        self.assertEqual(got['counts']['raw_correct'], 4)
        self.assertEqual(got['counts']['correct_and_admitted'], 1)
        self.assertEqual(got['counts']['native_unsure'], 1)
        self.assertEqual(got['counts']['producer_failures'], 2)
        self.assertEqual(got['raw_metrics'], dict(accuracy=.5, precision=.8, coverage=5/8))
        self.assertEqual(got['checked_metrics'], dict(accuracy=1/8, precision=.5, coverage=2/8))
        native = evaluate_schedule(q, refs, rows, evidence_ids_by_query=offered)
        for key in ('counts', 'raw_metrics', 'checked_metrics', 'producer_status_counts', 'check_status_counts'):
            self.assertEqual(got[key], dict(native[key]))

    def test_zero_attempts_not_zero_scientific_precision(self):
        q, refs, rows, offered = fixture(2)
        rows[0]['prediction']['answer_index'] = 2; failure(rows[1])
        got = score_arm(q, refs, rows, offered)
        self.assertEqual(got['raw_metrics']['precision'], 0)
        self.assertFalse(got['raw_precision_defined'])
        self.assertIsNone(got['statistical_raw_precision'])
        self.assertEqual(got['case_results'][0]['native_unsure'], True)
        self.assertIsNone(got['case_results'][1]['native_unsure'])

    def test_missing_duplicate_and_reordered_rows_fail(self):
        q, refs, rows, offered = fixture(3)
        for bad in (rows[:-1], rows[::-1], [rows[0], rows[0], rows[2]]):
            with self.assertRaises(ValueError): score_arm(q, refs, bad, offered)

    def test_bad_reference_choice_and_unoffered_citation(self):
        q, refs, rows, offered = fixture(2)
        for kind in ('bool', 'unknown', 'duplicate', 'wrong_unsure'):
            r, rs = copy.deepcopy(refs), copy.deepcopy(rows)
            if kind == 'bool': rs[0]['prediction']['answer_index'] = True
            if kind == 'unknown': rs[0]['prediction']['evidence_ids'] = ['not-offered']
            if kind == 'duplicate': rs[0]['prediction']['evidence_ids'] = ['s0', 's0']
            if kind == 'wrong_unsure': r[0]['unsure_index'] = 1
            with self.assertRaises(ValueError): score_arm(q, r, rs, offered)

    def test_failure_cannot_be_admitted_or_relabelled_unsure(self):
        q, refs, rows, offered = fixture(1)
        failure(rows[0]); rows[0]['check_status'] = 'accepted'
        with self.assertRaises(ValueError): score_arm(q, refs, rows, offered)

    def test_random_invented_native_parity(self):
        q, refs, rows, offered = fixture(199); rng = random.Random(19)
        for row in rows:
            choice = rng.randrange(10)
            if choice < 3: failure(row, ['parse_failure','unexecuted','timeout'][choice], 'invented failure')
            else:
                row['prediction']['answer_index'] = rng.randrange(3)
                if choice < 6: row.update(check_status='rejected', reason='invented rejection')
        got = score_arm(q, refs, rows, offered)
        native = evaluate_schedule(q, refs, rows, evidence_ids_by_query=offered)
        for key in ('counts','raw_metrics','checked_metrics','producer_status_counts','check_status_counts',
                    'raw_precision_defined','checked_precision_defined'):
            self.assertEqual(got[key], native[key])
        for actual, expected in zip(got['case_results'], native['case_results']):
            for key in ('id','native_unsure','raw_correct','correct_and_admitted','raw_answered','checked_answered'):
                self.assertEqual(actual[key], expected[key])

    def test_paper_matches_preserve_unknowns_and_multi_paper_denominator(self):
        ids = ['a','b','c']; gold = {'a':['d1','d2'], 'b':['d1'], 'c':[]}
        found = {'a':['d1','unannotated'], 'b':['d1'], 'c':['d3']}
        got = paper_metrics(ids, gold, found); native = source_annotation_metrics(ids, gold, found)
        for k in ('annotated_source_count','matched_annotated_source_count','annotated_source_recall',
                  'questions_with_annotations','questions_without_annotations','questions_with_any_annotated_source_hit',
                  'questions_with_all_annotated_sources'):
            self.assertEqual(got[k],native[k])
        self.assertEqual(got['all_hit_per_scheduled'],1/3)
        self.assertEqual(got['annotated_source_recall'],2/3)
        self.assertIsNone(got['case_results'][2]['annotated_source_recall'])

    def test_all_six_paired_contrasts_and_repaired_damaged(self):
        q, refs, rows, offered = fixture(4)
        before = copy.deepcopy(rows); before[0]['prediction']['answer_index'] = 1
        after = copy.deepcopy(rows); failure(after[1])
        a = score_arm(q, refs, before, offered); b = score_arm(q, refs, after, offered)
        change = transitions(a, b)
        self.assertEqual(change['incorrect_to_correct'],1)
        self.assertEqual(change['correct_to_incorrect'],1)
        result = factorial({'L/O':a,'E/O':a,'L/R':b,'E/R':b}, [[r['id']] for r in rows],replicates=30)
        self.assertEqual(set(result['metrics']), {'raw_accuracy','correct_and_admitted_yield'})
        for metric in result['metrics'].values():
            self.assertEqual(len(metric['publication_components']['contrasts']),6)
            self.assertEqual(metric['publication_components'],metric['question_sensitivity'])


if __name__ == '__main__': unittest.main()
