"""Fictional fixed-grid, proper-score and clustered-uncertainty controls."""
from dataclasses import replace
import math
import random
import unittest

from . import calibration as c, statistics as s
from .test_calibration import row


def fixture():
    rows=(s.AnalysisRow(1,.9,.95,True,True,1),s.AnalysisRow(2,.8,.91,True,True,0),
          s.AnalysisRow(3,.7,.80,True,True,1),s.AnalysisRow(4,.6,.70,True,True,0))
    return rows,(1,2,3,4),{1:'a',2:'a',3:'a',4:'b'}


class PointTests(unittest.TestCase):
    def test_fixed_cutoffs_inclusive_selection_and_all_scheduled_denominators(self):
        rows,ids,groups=fixture();result=s.point_summary(rows,ids,groups,purpose='fictional_qualification')
        self.assertEqual(result['thresholds'],[0.,.5,.7,.9,.95]);self.assertEqual(result['primary_threshold'],.9)
        raw=result['conditions']['raw']['operating_points']
        self.assertEqual([p['accepted'] for p in raw],[4,4,3,1,0])
        self.assertEqual(raw[2]['coverage'],.75);self.assertEqual(raw[2]['strict_correct_yield'],.5)
        self.assertEqual(raw[2]['conditional_error'],1/3)
        self.assertIsNone(raw[-1]['conditional_error']);self.assertIsNone(raw[-1]['conditional_precision'])
        self.assertEqual((raw[-1]['coverage'],raw[-1]['strict_correct_yield']),(0,0))
        for point in raw:
            self.assertEqual(point['correct_accepted']+point['incorrect_accepted']+
                point['correct_withheld']+point['incorrect_withheld'],4)

    def test_admission_and_missingness_are_separate_from_numeric_threshold(self):
        rows,ids,groups=fixture()
        altered=(replace(rows[0],strict_success=0,admitted=False),replace(rows[1],raw=None,calibrated=None),
                 replace(rows[2],produced=False,admitted=False,strict_success=0,raw=None,calibrated=None),rows[3])
        result=s.point_summary(altered,ids,groups,purpose='fictional_qualification')
        zero=result['conditions']['raw']['operating_points'][0]
        self.assertEqual((zero['available'],zero['accepted'],zero['coverage']),(2,1,.25))
        self.assertEqual(result['operational']['produced_but_rejected'],1)
        self.assertEqual(result['operational']['unproduced'],1)
        self.assertFalse(result['proper_scores']['full_cohort']);self.assertEqual(result['proper_scores']['paired_available'],2)

    def test_proper_scores_are_paired_and_only_logloss_clips(self):
        rows=(s.AnalysisRow(1,0.,.25,True,True,1),s.AnalysisRow(2,1.,.75,True,True,0),
              s.AnalysisRow(3,.8,None,True,True,1))
        result=s.point_summary(rows,(1,2,3),{1:'a',2:'b',3:'c'},purpose='fictional_qualification')['proper_scores']
        self.assertEqual(result['paired_available'],2);self.assertEqual(result['conditions']['raw']['brier'],1.)
        self.assertEqual(result['conditions']['raw']['log_loss_clipped'],2)
        self.assertAlmostEqual(result['conditions']['raw']['log_loss'],-math.log(1e-6),places=8)
        self.assertAlmostEqual(result['conditions']['calibrated']['brier'],.75**2)
        self.assertEqual(result['conditions']['calibrated']['log_loss_clipped'],0)

    def test_five_bin_edges_empty_bins_and_final_closed_endpoint(self):
        self.assertEqual([s.bin_index(x) for x in (0,.199999,.2,.4,.6,.8,1.)],[0,0,1,2,3,4,4])
        rows=(s.AnalysisRow(1,0.,0.,True,True,0),s.AnalysisRow(2,1.,1.,True,True,1))
        result=s.point_summary(rows,(1,2),{1:'a',2:'b'},purpose='fictional_qualification')
        bins=result['conditions']['raw']['reliability_bins']
        self.assertEqual([b['count'] for b in bins],[1,0,0,0,1]);self.assertIsNone(bins[1]['mean_score'])
        self.assertTrue(bins[-1]['upper_inclusive']);self.assertEqual(result['conditions']['raw']['descriptive_ece'],0.)

    def test_nonfinite_wrong_groups_duplicate_or_incomplete_schedule_rejected(self):
        rows,ids,groups=fixture()
        mutations=[(rows[:-1],ids,groups),(rows,ids,{1:'a',2:'a',3:'a'}),
                   ((replace(rows[0],raw=math.nan),*rows[1:]),ids,groups),
                   ((replace(rows[0],admitted=False),*rows[1:]),ids,groups)]
        for values in mutations:
            with self.subTest(values=values),self.assertRaises(ValueError):s.point_summary(*values,purpose='fictional_qualification')
        with self.assertRaisesRegex(ValueError,'300-claim'):s.point_summary(rows,ids,groups)


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,cls.ids,cls.groups=fixture()
        cls.result=s.paired_bootstrap(cls.rows,cls.ids,cls.groups,purpose='fictional_qualification')

    def endpoint(self, key):
        return next(r for r in self.result['estimates'] if r['endpoint']==list(key))

    def test_whole_unequal_components_recompute_claim_weighted_ratios(self):
        rng=random.Random(20261106);draws=[];differences=[]
        for _ in range(10000):
            picks=[rng.randrange(2),rng.randrange(2)]
            # a has three claims; b has one. At t=.9 raw accepts one a
            # claim, calibrated accepts two. Do not average group rates.
            denominator=sum(3 if p==0 else 1 for p in picks)
            accepted=sum(p==0 for p in picks)
            draws.append(accepted/denominator);differences.append(accepted/denominator)
        actual=self.endpoint(('raw','selection',3,'coverage'))
        self.assertEqual(actual['estimate'],.25)
        self.assertEqual(actual['ci95'],[s.percentile(draws,.025),s.percentile(draws,.975)])
        difference=next(r for r in self.result['calibrated_minus_raw'] if r['endpoint']==['selection',3,'coverage'])
        self.assertEqual(difference['ci95'],[s.percentile(differences,.025),s.percentile(differences,.975)])
        self.assertEqual(actual['ci95'],[0.,1/3])
        self.assertEqual(self.result['component_sizes'],[3,1]);self.assertEqual(self.result['completed_replicates'],10000)

    def test_sparse_and_empty_denominators_are_undefined_not_zero_intervals(self):
        risk=self.endpoint(('raw','selection',3,'conditional_error'))
        self.assertEqual(risk['denominator_components'],1);self.assertIsNone(risk['ci95'])
        self.assertGreater(risk['undefined_replicates'],0)
        empty=self.endpoint(('raw','selection',4,'conditional_precision'))
        self.assertIsNone(empty['estimate']);self.assertIsNone(empty['ci95']);self.assertEqual(empty['undefined_replicates'],10000)
        empty_bin=self.endpoint(('raw','bin',0,'correctness'))
        self.assertEqual(empty_bin['undefined_replicates'],10000);self.assertIsNone(empty_bin['ci95'])

    def test_two_contributing_groups_still_require_every_draw_defined(self):
        rows=(s.AnalysisRow(1,.95,.95,True,True,1),s.AnalysisRow(2,.95,.95,True,True,0),
              s.AnalysisRow(3,.1,.1,True,True,0))
        result=s.paired_bootstrap(rows,(1,2,3),{1:'a',2:'b',3:'c'},purpose='fictional_qualification')
        risk=next(r for r in result['estimates'] if r['endpoint']==['raw','selection',3,'conditional_error'])
        self.assertEqual(risk['denominator_components'],2);self.assertGreater(risk['undefined_replicates'],0)
        self.assertIsNone(risk['ci95']);self.assertEqual(risk['undefined_reason'],'undefined_denominator_in_bootstrap_draws')

    def test_one_component_cannot_estimate_uncertainty_even_with_full_coverage(self):
        result=s.paired_bootstrap(self.rows,self.ids,{i:'only' for i in self.ids},purpose='fictional_qualification')
        coverage=next(r for r in result['estimates'] if r['endpoint']==['raw','selection',0,'coverage'])
        self.assertEqual(coverage['undefined_replicates'],0);self.assertIsNone(coverage['ci95'])
        self.assertEqual(coverage['undefined_reason'],'fewer_than_two_observed_denominator_components')

    def test_proper_score_differences_share_draws(self):
        rng=random.Random(20261106);samples=[];indices=((0,1,2),(3,))
        for _ in range(10000):
            chosen=[i for _ in range(2) for i in indices[rng.randrange(2)]]
            samples.append(math.fsum((self.rows[i].calibrated-self.rows[i].strict_success)**2-
                (self.rows[i].raw-self.rows[i].strict_success)**2 for i in chosen)/len(chosen))
        actual=next(r for r in self.result['calibrated_minus_raw'] if r['endpoint']==['proper','brier'])
        for observed,expected in zip(actual['ci95'],(s.percentile(samples,.025),s.percentile(samples,.975))):
            self.assertAlmostEqual(observed,expected,places=14)

    def test_full_invented300_and247_components_keep_every_endpoint(self):
        ids=tuple(range(1,301));groups={i:f'g{(i-1)%247:03d}' for i in ids}
        rows=tuple(s.AnalysisRow(i,.34+.66*(i%23)/22,.34+.66*(i%23)/22,True,True,int(i%3==0)) for i in ids)
        report=s.paired_bootstrap(rows,ids,groups)
        self.assertEqual((report['scheduled'],report['components'],report['completed_replicates']),(300,247,10000))
        self.assertEqual(len(report['estimates']),64);self.assertEqual(len(report['calibrated_minus_raw']),22)
        self.assertTrue(all(r['estimate']==0. for r in report['calibrated_minus_raw'] if r['estimate'] is not None))


class SensitivityTests(unittest.TestCase):
    def test_changed_original_scores_labels_or_lineage_are_rejected(self):
        training=(row(1,.4,0),row(2,.5,0),row(3,.7,1),row(4,.8,1))
        suite=c.fit_calibration(training,(1,2,3,4),{1:'a',2:'a',3:'b',4:'c'},purpose='fictional_qualification')
        for changed in (row(1,1.,0),replace(training[0],strict_success=1),
                        replace(training[0],outcome_proof='0'*64)):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    s.held_out_summary((changed,*training[1:]),suite,purpose='fictional_qualification')

    def test_every_deletion_keeps_fixed_points_and_is_not_a_confidence_interval(self):
        training=(row(1,.4,0),row(2,.5,0),row(3,.7,1),row(4,.8,1))
        suite=c.fit_calibration(training,(1,2,3,4),{1:'a',2:'a',3:'b',4:'c'},purpose='fictional_qualification')
        rows,ids,groups=fixture();report=s.deletion_sensitivity(rows,ids,groups,suite,calibration_rows=training,purpose='fictional_qualification')
        self.assertEqual(report['maps'],3);self.assertFalse(report['confidence_interval'])
        self.assertEqual([p['threshold'] for p in report['operating_point_ranges']],list(s.THRESHOLDS))
        self.assertEqual(len(report['per_deletion']),3)
        held=s.held_out_summary(training,suite,purpose='fictional_qualification')
        self.assertEqual(held['summary']['scheduled'],4);self.assertEqual(held['summary']['proper_scores']['paired_available'],4)
        self.assertFalse(held['confidence_interval'])
        for i,point in enumerate(report['operating_point_ranges']):
            values=[r['operating_points'][i]['accepted'] for r in report['per_deletion']]
            self.assertEqual(point['metrics']['accepted']['minimum'],min(values))
            self.assertEqual(point['metrics']['accepted']['maximum'],max(values))
        with self.assertRaises(ValueError):s.deletion_sensitivity(rows,ids,groups,replace(suite,status='incomplete'),calibration_rows=training,purpose='fictional_qualification')


if __name__=='__main__':unittest.main()
