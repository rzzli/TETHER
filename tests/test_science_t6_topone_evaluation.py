import unittest
import copy
from asof.serde import ContractError
from tools.science.t6_topone_evaluation import score_task, verify_execution_transcript


class TopOneEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.task = {'task_id': 't', 'case_id': 'c', 'category': 'genetics', 'offered_candidate_ids': ['a', 'b']}
        self.result = {'arm': 'asof', 'status': 'completed', 'claims': [{'observation_id': 'a'}],
            'coverage': {'genetics': {'status': 'completed'}}, 'calls': 1,
            'measured_usage': {}, 'estimated_usage': {}, 'elapsed_seconds': 1}
        self.reference = {'candidates': [{'observation_id': 'a', 'applicability': 'uncertain'},
            {'observation_id': 'b', 'applicability': 'context_mismatch'}],
            'admissible_best_ids': ['a'], 'none_sufficient': False, 'reference_uncertainty': 'high'}

    def test_best_and_mismatch_are_distinct(self):
        row = score_task(self.task, self.result, self.reference)
        self.assertTrue(row['decision_agreement'])
        self.assertFalse(row['context_mismatch'])
        self.result['claims'] = [{'observation_id': 'b'}]
        row = score_task(self.task, self.result, self.reference)
        self.assertFalse(row['decision_agreement'])
        self.assertTrue(row['context_mismatch'])

    def test_inapplicable_and_failed_are_not_correct_abstentions(self):
        self.result['claims'] = []
        for status in ('inapplicable', 'budget_exhausted', 'failed'):
            self.result['coverage']['genetics']['status'] = status
            row = score_task(self.task, self.result, self.reference)
            self.assertIsNone(row['decision_agreement'])
            self.assertFalse(row['abstained'])

    def test_none_sufficient_and_ties(self):
        self.result['claims'] = []
        self.reference.update(admissible_best_ids=[], none_sufficient=True)
        self.assertTrue(score_task(self.task, self.result, self.reference)['decision_agreement'])
        self.reference.update(admissible_best_ids=['a', 'b'], none_sufficient=False)
        self.result['claims'] = [{'observation_id': 'b'}]
        self.assertTrue(score_task(self.task, self.result, self.reference)['all_candidates_tied'])

    def test_foreign_or_multiple_selections_fail(self):
        for ids in (['foreign'], ['a', 'b']):
            self.result['claims'] = [{'observation_id': identity} for identity in ids]
            with self.assertRaises(ContractError):
                score_task(self.task, self.result, self.reference)

    def test_deleted_reordered_and_changed_launcher_events_fail(self):
        execution={'status':'all_topone_runs_verified','tasks':[{'task_id':'t','arms':[
            {'arm':'asof','result':{'sha256':'a'*64}}]}]}
        events=[{'event':name,'details':details} for name,details in [
            ('build_reserved',{}),('model_verification_started',{}),('server_started',{'pid':123}),
            ('arm_started',{'task_id':'t','arm':'asof'}),
            ('arm_verified',{'task_id':'t','arm':'asof','result_sha256':'a'*64}),
            ('execution_terminal',{'status':'all_topone_runs_verified','server_stopped':True})]]
        verify_execution_transcript(events,execution)
        variants=[events[:3]+events[4:]]
        changed=copy.deepcopy(events); changed[3],changed[4]=changed[4],changed[3]; variants.append(changed)
        changed=copy.deepcopy(events); changed[4]['details']['result_sha256']='b'*64; variants.append(changed)
        changed=copy.deepcopy(events); changed[-1]['details']['server_stopped']=False; variants.append(changed)
        for variant in variants:
            with self.assertRaises(ContractError): verify_execution_transcript(variant,execution)
