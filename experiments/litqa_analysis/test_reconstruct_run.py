"""Cross-stage regression controls using the sealed two-question fictional runs.

These are retained local qualification fixtures, not production benchmark data.
No inference, acquisition, or scientific keys are involved.
"""
from copy import deepcopy
from pathlib import Path
import unittest

from experiments.litqa_analysis import reconstruct_run as r

ROOT=Path(__file__).resolve().parents[2]
PRIMARY=ROOT/'data/cache/sc04-controller-qualification-attempt01'
SUPPLIED=ROOT/'data/cache/sc04-supplied-controller-qualification-attempt01'
PRIMARY_SHA='8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0'
SUPPLIED_SHA='f9dd1f8b8d0a560730d0450cec03647ec8adcba5d23e0836c16e6af03c1cf19c'


class RunReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary=r.envelopes.verify_run(PRIMARY,PRIMARY_SHA)
        cls.supplied=r.envelopes.verify_run(SUPPLIED,SUPPLIED_SHA)

    def test_all_actual_fictional_arms_reconstruct(self):
        result=r.primary_verified(self.primary)
        self.assertEqual(set(result['records']),set(r.ARMS))
        self.assertTrue(all(len(rows)==2 for rows in result['records'].values()))
        self.assertEqual(result['source_cases']['L/O'][0]['logical_model_usage']['generation_calls'],1)
        self.assertEqual(result['source_cases']['E/R'][0]['logical_model_usage']['generation_calls'],3)
        self.assertEqual(result['records']['L/O'][1]['prediction']['answer_index'],1) # Retained false abstention, not rewritten.

    def test_all_actual_fictional_diagnostic_answers_reconstruct(self):
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
        with self.assertRaisesRegex(ValueError,'anchor'):r.reconstruct(PRIMARY,'0'*64)

    def test_logical_calls_cannot_exceed_declared_arm_cap(self):
        summary=dict(generation_entered=True,usage=dict(input_tokens=1,output_tokens=1,cost_usd=0),reservation_input_tokens=10,reservation_output_tokens=256)
        with self.assertRaisesRegex(ValueError,'Logical total model budget'):r.logical_usage([dict(summary=summary)]*4)


if __name__=='__main__':unittest.main()
