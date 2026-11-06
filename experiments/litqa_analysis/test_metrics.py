import unittest
from unittest.mock import patch
from experiments.litqa_analysis import metrics as m


class MetricsTests(unittest.TestCase):
    def test_transitive_publication_groups_preserve_unannotated_cases(self):
        ids=('a','b','c','d','e')
        groups=m.publication_components(ids,dict(a=['doi1'],b=['doi1','doi2'],c=['doi2'],d=[],e=['doi3']))
        self.assertEqual(groups,(('a','b','c'),('d',),('e',)))

    def test_components_do_not_depend_on_annotation_order(self):
        ids=('a','b','c')
        one=m.publication_components(ids,dict(a=['x','y'],b=['y'],c=['x']))
        two=m.publication_components(ids,dict(a=['y','x'],b=['y'],c=['x']))
        self.assertEqual(one,two)

    def test_declared_factorial_contrasts(self):
        result=m.contrasts({'L/O':.2,'E/O':.3,'L/R':.4,'E/R':.8})
        self.assertAlmostEqual(result['interaction'],.3)
        self.assertAlmostEqual(result['marginal_expansion'],.25)
        self.assertAlmostEqual(result['marginal_ranking'],.35)

    def test_paired_constant_effect_has_exact_interval(self):
        ids=('a','b','c');flags={arm:[int(arm=='E/R')]*3 for arm in m.ARMS}
        result=m.paired_bootstrap(ids,flags,(('a',),('b','c')),replicates=100)
        self.assertEqual(result['contrasts']['combined_vs_lexical']['ci95'],[1.0,1.0])
        self.assertEqual(result['contrasts']['marginal_expansion']['ci95'],[.5,.5])

    def test_unequal_cluster_sizes_use_questions_as_denominator(self):
        ids=('a','b','c');flags={arm:[0,0,1] for arm in m.ARMS}
        result=m.paired_bootstrap(ids,flags,(('a','b'),('c',)),replicates=200)
        self.assertEqual(result['rates']['L/O'],1/3)
        self.assertEqual(result['contrasts']['interaction']['ci95'],[0.0,0.0])

    def test_mixed_cluster_draw_recomputes_ratio_not_mean_cluster_accuracy(self):
        ids=('a','b','c');flags={arm:[0,0,0] for arm in m.ARMS};flags['E/R']=[0,0,1]
        class Draw:
            def __init__(self):self.values=iter((0,1))
            def randrange(self,count):return next(self.values)
        with patch.object(m.random,'Random',return_value=Draw()):
            result=m.paired_bootstrap(ids,flags,(('a','b'),('c',)),replicates=1)
        self.assertEqual(result['contrasts']['combined_vs_lexical']['ci95'],[1/3,1/3])

    def test_seed_is_reproducible_for_nonconstant_pairing(self):
        ids=('a','b','c');flags={arm:[int(i==j%3) for i in range(3)] for j,arm in enumerate(m.ARMS)}
        self.assertEqual(m.paired_bootstrap(ids,flags,((x,) for x in ids),replicates=100,seed=3),
                         m.paired_bootstrap(ids,flags,((x,) for x in ids),replicates=100,seed=3))

    def test_one_group_does_not_claim_zero_uncertainty(self):
        result=m.paired_bootstrap(('a','b'),{arm:[0,1] for arm in m.ARMS},(('a','b'),),replicates=100)
        self.assertFalse(result['uncertainty_estimable']);self.assertEqual(result['completed_replicates'],0)
        self.assertIsNone(result['contrasts']['interaction']['ci95'])

    def test_group_omission_or_duplicate_rejected(self):
        flags={arm:[0,1] for arm in m.ARMS}
        for groups in ((('a',),),(('a','b'),('a',))):
            with self.assertRaises(ValueError):m.paired_bootstrap(('a','b'),flags,groups)

    def test_unknown_and_nonbinary_outcomes_rejected(self):
        flags={arm:[0,1] for arm in m.ARMS};flags['E/R']=[0,None]
        with self.assertRaises(ValueError):m.paired_bootstrap(('a','b'),flags,(('a',),('b',)))

    def test_zero_attempt_precision_preserves_native_and_undefined_ratio(self):
        self.assertEqual(m.precision_ratio(0,0),dict(native_precision=0.,precision_defined=False,statistical_precision=None))
        self.assertEqual(m.precision_ratio(2,4)['statistical_precision'],.5)


if __name__=='__main__':unittest.main()
