import copy
import unittest

from experiments.scifact_comparison.diagnostics import compare_condition
from experiments.scifact_comparison.inputs import build_condition


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.requests = [dict(id=1,claim='Fictional claim',documents=[dict(doc_id=2,title='Title',abstract=['Background','Evidence'])])]
        self.pair = dict(abstract_id=2,status='completed',prediction=dict(claim_id=1,abstract_id=2,predicted_label='SUPPORT',
            predicted_rationale=[1],label_probs=[.1,.2,.7]))

    def test_source_mapping_after_deletion(self):
        _,lineages = build_condition(self.requests,'rationale_only',expected_k=1,
            references=[dict(id=1,evidence={'2':[dict(sentences=[1],label='SUPPORT')]})])
        other = copy.deepcopy(self.pair)
        other['prediction']['predicted_rationale'] = [0]
        report = compare_condition({1:[self.pair]},{1:[other]},lineages)
        self.assertEqual(report['rows'][0]['rationale_jaccard'],1.)
        self.assertEqual(report['changed_labels'],0)

    def test_synthetic_selection_retained(self):
        _,lineages = build_condition(self.requests,'constructed_conflict',expected_k=1)
        other = copy.deepcopy(self.pair)
        other['prediction'].update(predicted_rationale=[2],predicted_label='CONTRADICT',label_probs=[.8,.1,.1])
        report = compare_condition({1:[self.pair]},{1:[other]},lineages)
        self.assertEqual(report['synthetic_sentences_selected'],1)
        self.assertEqual(report['changed_labels'],1)
        self.assertAlmostEqual(report['mean_primary_class_probability_change'],-.6)
        self.assertEqual(report['rows'][0]['condition_source_rationale_indices'],[])

    def test_inapplicable_gold_mask_not_in_applicable_aggregate(self):
        _,lineages = build_condition(self.requests,'evidence_removal',expected_k=1,references=[dict(id=1,evidence={})])
        report = compare_condition({1:[self.pair]},{1:[self.pair]},lineages)
        self.assertEqual(report['scheduled_pairs'],1)
        self.assertEqual(report['both_observed_pairs'],1)
        self.assertEqual(report['applicable_observed_pairs'],0)
        self.assertIsNone(report['mean_primary_class_probability_change'])

    def test_missing_prediction_not_a_label_change(self):
        _,lineages = build_condition(self.requests,'irrelevant_context',expected_k=1)
        report = compare_condition({1:[self.pair]},{1:[dict(abstract_id=2,status='overlength',prediction=None)]},lineages)
        self.assertEqual(report['scheduled_pairs'],1)
        self.assertEqual(report['both_observed_pairs'],0)
        self.assertEqual(report['changed_labels'],0)


if __name__ == '__main__':
    unittest.main()
