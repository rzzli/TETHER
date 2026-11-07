"""Current cross-stage controls built from invented HTTP/native responses.

No original captures, inference, acquisition or scientific answer keys are used.
"""
from copy import deepcopy
from pathlib import Path
import unittest

from experiments.litqa_analysis import reconstruct_run as r

from experiments.litqa_analysis.invented_run_fixtures import InventedRuns


class RunReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures=InventedRuns()
        cls.addClassCleanup(cls.fixtures.close)
        cls.primary=r.envelopes.verify_run(cls.fixtures.primary_path,cls.fixtures.primary_sha)
        cls.supplied=r.envelopes.verify_run(cls.fixtures.supplied_path,cls.fixtures.supplied_sha)

    def test_all_invented_arms_reconstruct(self):
        result=r.primary_verified(self.primary)
        self.assertEqual(set(result['records']),set(r.ARMS))
        self.assertTrue(all(len(rows)==2 for rows in result['records'].values()))
        self.assertEqual(result['source_cases']['L/O'][0]['logical_model_usage']['generation_calls'],1)
        self.assertEqual(result['source_cases']['E/R'][0]['logical_model_usage']['generation_calls'],3)
        self.assertEqual(result['records']['L/O'][1]['prediction']['answer_index'],1) # Deliberately invented unsure answer.

    def test_all_invented_diagnostic_answers_reconstruct(self):
        result=r.supplied_verified(self.supplied)
        self.assertEqual(len(result['records']['supplied']),2)
        self.assertEqual(len(result['diagnostic_resolutions']),1)
        self.assertTrue(result['diagnostic_resolutions'][0]['coverage']['article_retained'])
        self.assertEqual(result['source_cases']['supplied'][0]['selected_dois'],['10.1234/invented'])

    def test_changed_expansion_cannot_drive_collection(self):
        value=deepcopy(self.primary)
        value['phases']['expand']['rows'][0]['product']['expansion']['queries'][0]=['invented substitution']
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.primary_verified(value)

    def test_unbound_collection_parent_rejected(self):
        value=deepcopy(self.primary);value['phases']['collect']['rows'][0]['product']['expansion_parent_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.primary_verified(value)

    def test_changed_ranking_cannot_drive_answer(self):
        value=deepcopy(self.primary);value['phases']['rank']['rows'][0]['product']['order'].reverse()
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.primary_verified(value)

    def test_changed_answer_order_rejected(self):
        value=deepcopy(self.primary);value['phases']['answer']['rows'][0]['product']['order'].reverse()
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.primary_verified(value)

    def test_changed_admission_rejected(self):
        value=deepcopy(self.primary);value['phases']['answer']['rows'][0]['product']['decision']['accepted']=False
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.primary_verified(value)

    def test_changed_diagnostic_hint_hash_rejected(self):
        value=deepcopy(self.supplied);value['phases']['answer']['rows'][0]['product']['hint_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'cross-stage product'):r.supplied_verified(value)

    def test_changed_diagnostic_doi_rejected(self):
        value=deepcopy(self.supplied);value['phases']['collect']['rows'][0]['product']['plan']['doi']='10.1234/other'
        with self.assertRaisesRegex(ValueError,'resolution schedule'):r.supplied_verified(value)

    def test_external_anchor_required_before_any_join(self):
        with self.assertRaisesRegex(ValueError,'anchor'):r.reconstruct(self.fixtures.primary_path,'0'*64)

    def test_logical_calls_cannot_exceed_declared_arm_cap(self):
        summary=dict(generation_entered=True,usage=dict(input_tokens=1,output_tokens=1,cost_usd=0),reservation_input_tokens=10,reservation_output_tokens=256)
        with self.assertRaisesRegex(ValueError,'Logical total model budget'):r.logical_usage([dict(summary=summary)]*4)


if __name__=='__main__':unittest.main()
