import copy
import unittest

from experiments.litqa_analysis.aggregate import summarize, native_agreement
from experiments.litqa_analysis.test_scoring import fixture, failure
from experiments.labbench.evaluate import evaluate_schedule


class AggregateTests(unittest.TestCase):
    def setUp(self):
        q,refs,rows,evidence=fixture(3);ids=[r['id'] for r in rows]
        self.inputs=dict(queries=q,references=refs,annotations={i:['d'+str(n)] for n,i in enumerate(ids)},groups=[[i] for i in ids])
        usage=dict(generation_calls=1,measured_input_tokens=100,measured_output_tokens=10,reserved_input_tokens=1000,
                   reserved_output_tokens=256,provider_cost_usd=0)
        cases=[dict(id=i,retained_dois=['d'+str(n)],pool_dois=['d'+str(n)],selected_dois=['d'+str(n)],
            selected_bytes=50,selected_passages=1,native_status='completed',expansion_status='completed',ranking_status='completed',
            expansion_native_status='completed',ranking_native_status='completed',expansion_failure_reason=None,ranking_failure_reason=None,
            retained_original_bytes=100,extracted_paragraph_bytes=70,candidate_pool_bytes=60,
            logical_http_usage=dict(requests=2,measured_response_bytes=100,safety_accounted_bytes=100,unknown_transfer_upper_bytes=0),
            logical_model_usage=usage,source_coverage=dict(retained_articles=1,unknown_or_unavailable_inputs=[])) for n,i in enumerate(ids)]
        common=dict(status='independently_reconstructed',queries=q,source_lineage_checked=True,native_calls_checked=True,
                    cross_stage_products_checked=True,resources=dict(physical_calls=1))
        self.primary=dict(common,records={a:copy.deepcopy(rows) for a in ('L/O','E/O','L/R','E/R')},
            evidence_ids={a:copy.deepcopy(evidence) for a in ('L/O','E/O','L/R','E/R')},
            source_cases={a:copy.deepcopy(cases) for a in ('L/O','E/O','L/R','E/R')})
        self.supplied=dict(common,records={'supplied':copy.deepcopy(rows)},evidence_ids={'supplied':copy.deepcopy(evidence)},
            source_cases={'supplied':copy.deepcopy(cases)},diagnostic_resolutions=[])

    def summarize(self):return summarize(self.primary,self.supplied,self.inputs,expected_count=3,replicates=30)

    def test_full_family_and_native_agreement(self):
        summary=self.summarize()
        self.assertEqual(len(summary['arms']),5)
        self.assertEqual(len(summary['paired']['metrics']['raw_accuracy']['publication_components']['contrasts']),6)
        self.assertEqual(native_agreement(summary,self.primary,self.supplied,self.inputs,evaluate_schedule)['arms_checked'],5)
        self.assertEqual(summary['ranking_selection_changes']['L']['identical_selection'],3)

    def test_available_subset_separate_from_full_denominator(self):
        rows=self.supplied['source_cases']['supplied'];row=rows[0]
        row['source_coverage']=dict(retained_articles=0,unknown_or_unavailable_inputs=['d0'])
        for k in ('retained_dois','pool_dois','selected_dois'):row[k]=[]
        row.update(selected_bytes=0,selected_passages=0)
        self.supplied['records']['supplied'][0]['prediction']['answer_index']=2
        self.supplied['records']['supplied'][0]['prediction']['evidence_ids']=[]
        self.supplied['evidence_ids']['supplied'][row['id']]=[]
        summary=self.summarize()
        self.assertEqual(summary['arms']['supplied']['scheduled_count'],3)
        self.assertEqual(summary['arms']['supplied']['raw_metrics']['accuracy'],2/3)
        self.assertEqual(summary['supplied_source_subsets']['any_annotated_source_eligible']['scheduled_count'],2)

    def test_missing_arm_case_and_reconstruction_fail_closed(self):
        for kind in ('case','arm','verified'):
            original=copy.deepcopy(self.primary)
            if kind=='case':self.primary['records']['L/O'].pop()
            if kind=='arm':self.primary['records'].pop('E/R')
            if kind=='verified':self.primary['source_lineage_checked']=False
            with self.assertRaises(ValueError):self.summarize()
            self.primary=original

    def test_full_schedule_failure_cannot_improve_attempted_accuracy(self):
        failure(self.primary['records']['E/R'][0])
        summary=self.summarize()
        self.assertEqual(summary['arms']['E/R']['raw_metrics'],dict(accuracy=2/3,precision=1,coverage=2/3))
        self.assertEqual(summary['paired']['ranking_transitions']['E']['correct_to_incorrect'],1)

    def test_intervention_failures_remain_full_cohort_and_secondary_subsets(self):
        self.primary['source_cases']['E/O'][0].update(expansion_native_status='codec_failure',expansion_status='fallback',expansion_failure_reason='codec_failure')
        self.primary['source_cases']['L/R'][1].update(ranking_native_status='not_applicable',ranking_status='not_applicable',ranking_failure_reason='empty pool')
        got=self.summarize()
        self.assertEqual(got['scheduled_count'],3)
        self.assertEqual(got['available_intervention_subsets']['all_interventions_available']['scheduled_count'],1)
        self.assertEqual(got['logical_arm_accounting']['E/O']['expansion_failure_reason_counts'],{'codec_failure':1})
        self.assertEqual(got['logical_arm_accounting']['L/O']['logical_http_usage']['requests'],6)
        self.assertEqual(got['logical_arm_accounting']['L/O']['candidate_pool_bytes'],180)


if __name__=='__main__':unittest.main()
