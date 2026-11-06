from pathlib import Path
import unittest

from experiments.scifact_comparison.statistics import case_counts, metrics, total, paired_bootstrap, percentile
from experiments.scifact.evaluate import official_metrics, strict_correct

SCORER = Path(__file__).resolve().parents[3]/'data/reference/scifact-evaluator-66feffc5/evaluator/eval.py'


def gold(evidence):
    return dict(id=1,evidence=evidence)


class StatisticsTests(unittest.TestCase):
    def test_native_boundary_parity(self):
        cases = [
            ({},{}),
            ({},{'9':dict(label='SUPPORT',sentences=[0])}),
            ({'9':[dict(label='SUPPORT',sentences=[1])]},{}),
            ({'9':[dict(label='SUPPORT',sentences=[1])]}, {'9':dict(label='SUPPORT',sentences=[0,1,2])}),
            ({'9':[dict(label='SUPPORT',sentences=[1])]}, {'9':dict(label='CONTRADICT',sentences=[1])}),
            ({'9':[dict(label='SUPPORT',sentences=[3])]}, {'9':dict(label='SUPPORT',sentences=[0,1,2,3])}),
            ({'9':[dict(label='SUPPORT',sentences=[0,1,2,3])]}, {'9':dict(label='SUPPORT',sentences=[0,1,2,3])}),
            ({'9':[dict(label='SUPPORT',sentences=[0,1])]}, {'9':dict(label='SUPPORT',sentences=[0])}),
            ({'9':[dict(label='SUPPORT',sentences=[0]),dict(label='SUPPORT',sentences=[1,2])]},
             {'9':dict(label='SUPPORT',sentences=[0,1,2,3])}),
            ({'9':[dict(label='SUPPORT',sentences=[0,1]),dict(label='SUPPORT',sentences=[2,3])]},
             {'9':dict(label='SUPPORT',sentences=[0,2,3])}),
        ]
        for reference,predicted in cases:
            with self.subTest(reference=reference,predicted=predicted):
                g,p = gold(reference),gold(predicted)
                observed = metrics(case_counts(g,p))
                native = official_metrics([g],[p],evaluator_path=SCORER)
                for key,value in native.items():
                    self.assertAlmostEqual(observed[key],value,places=14)
                self.assertEqual(bool(observed['strict_correct_per_scheduled']),strict_correct(g,p))

    def test_failure_never_correct_nei(self):
        empty = gold({})
        self.assertEqual(metrics(case_counts(empty,empty,produced=False,admitted=False))['strict_correct_per_scheduled'],0.)
        self.assertEqual(metrics(case_counts(empty,empty,produced=True,admitted=False))['strict_correct_per_scheduled'],0.)

    def test_bootstrap_exact_null_with_shared_components(self):
        v = case_counts(gold({}),gold({}))
        arms = {1:v,2:v,3:v}
        result = paired_bootstrap(arms,arms,{1:'a',2:'a',3:'b'},replicates=100)
        self.assertEqual(result['components'],2)
        for value in result['metrics'].values():
            self.assertEqual((value['difference'],value['lower'],value['upper']),(0.,0.,0.))

    def test_single_component_known_difference(self):
        good = case_counts(gold({}),gold({}))
        failed = case_counts(gold({}),gold({}),produced=False,admitted=False)
        result = paired_bootstrap({1:failed,2:failed},{1:good,2:good},{1:'a',2:'a'},replicates=20)
        self.assertEqual(result['metrics']['strict_correct_per_scheduled'],dict(baseline=0.,new=1.,difference=1.,lower=1.,upper=1.))

    def test_bootstrap_seed_reproducible(self):
        good = case_counts(gold({}),gold({}))
        failed = case_counts(gold({}),gold({}),produced=False,admitted=False)
        args = ({1:good,2:failed},{1:failed,2:good},{1:'a',2:'b'})
        self.assertEqual(paired_bootstrap(*args,replicates=100),paired_bootstrap(*args,replicates=100))

    def test_membership_and_counts_rejected(self):
        v = case_counts(gold({}),gold({}))
        with self.assertRaises(ValueError):
            paired_bootstrap({1:v},{2:v},{1:'a'})
        with self.assertRaises(ValueError):
            metrics([-1]*10)

    def test_linear_percentile(self):
        self.assertEqual(percentile([0.,10.],.25),2.5)


if __name__ == '__main__':
    unittest.main()
