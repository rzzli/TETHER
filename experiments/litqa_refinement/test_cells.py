"""Reserved model-cell accounting and per-member raw-evidence isolation."""
import json
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode
from experiments.labbench.tests import test_model as fixtures
from . import cells,contracts,model,test_transport as tf,transport


class CellTests(unittest.TestCase):
    def setUp(self):
        tf.RefinementTransportTests.setUp(self)
        self.critic=contracts.critique(self.q,self.prior,self.f.sources,self.answer,
                                      native_status='completed',native_call_sha256='b'*64)
        self.pair=model.make_repair_pair(self.q,self.prior,self.critic,self.f.sources,self.f.model)

    def execute(self,task='critic',*,raw=None,sources=None,member=None):
        kwargs=dict(owner=self.f.owner,output=self.out,deadline=time.monotonic()+10,
                    alias='fictional-mcq',execution_id='invented-'+task)
        if task!='critic':
            member=member or self.pair[task]
            sources=self.f.sources if sources is None and task=='repair' else (() if sources is None else sources)
            if member['request'] is not None:
                self.f.request,self.f.payload=member['request'],member['payload']
            raw=self.f.native_body(content='{"answer_index":0,"evidence_ids":[]}') if raw is None else raw
        else:raw=self.raw if raw is None else raw
        with patch.object(transport.native,'_check_owner',return_value=12345), \
             patch.object(transport.native,'_watchdog',return_value=fixtures.Timer()), \
             patch.object(transport.mcq,'tokenize_once',return_value=self.f.quote()), \
             self.f.transport(fixtures.Response(raw)):
            if task=='critic':return cells.call_critic(self.q,self.prior,self.f.sources,self.f.model,**kwargs)
            return cells.call_pair_member(self.q,self.prior,self.critic,sources,self.f.model,member,task,
                       control_sha256=self.pair['control_sha256'],**kwargs)

    def test_completed_critic_has_distinct_reservation_and_usage(self):
        result=self.execute()
        self.assertEqual(result['summary']['status'],'completed')
        self.assertEqual(result['summary']['usage']['input_tokens'],50)
        self.assertEqual(result['summary']['reservation_output_tokens'],256)
        self.assertTrue((self.out/'INPUT.json').exists())
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(len(self.f.calls),1)

    def test_complete_codec_failure_is_explicit_and_not_retried(self):
        result=self.execute(raw=self.f.native_body(content='{}'))
        self.assertEqual(result['summary']['status'],'codec_failure')
        self.assertIsNone(result['summary']['decoded'])
        self.assertEqual(result['summary']['usage']['input_tokens'],50)
        self.assertTrue((self.out/'native/failure.json').exists())
        self.assertEqual(len(self.f.calls),1)

    def test_capacity_is_recorded_inside_reserved_cell_without_dispatch(self):
        self.q=encode(self.q);self.q['question']='x'*16000
        self.prior=contracts.candidate(self.q,dict(answer_index=0,evidence_ids=[]),producer_status='produced',
            original_admission_status='rejected',native_call_sha256='a'*64,generated_at_utc=None,offered_ids=())
        result=self.execute()
        self.assertEqual(result['summary']['status'],'capacity')
        self.assertIsNone(result['summary']['usage'])
        self.assertFalse(result['summary']['generation_entered'])
        self.assertFalse(self.f.calls)
        self.assertTrue((self.out/'INPUT.json').exists())

    def test_integrity_failure_terminates_instead_of_becoming_codec_failure(self):
        raw=self.f.native_body(content=canonical(self.answer).decode(),tokens_evaluated=51)
        with self.assertRaises(ValueError):self.execute(raw=raw)
        self.assertTrue((self.out/'FAILURE.json').exists())
        self.assertFalse((self.out/'SUMMARY.json').exists())
        self.assertEqual(len(self.f.calls),1)

    def test_removal_cell_contains_no_factual_member_or_raw_passages(self):
        result=self.execute('removal')
        self.assertEqual(result['summary']['status'],'completed')
        inputs=json.loads((self.out/'INPUT.json').read_bytes())
        self.assertEqual(inputs['sources'],[])
        self.assertNotIn('prepared_pair',inputs)
        self.assertEqual(inputs['prepared_member']['request']['sources'],[])
        # Candidate and critique remain explicitly generated context by design.
        self.assertFalse(inputs['candidate_context']['is_scientific_evidence'])
        self.assertFalse(inputs['critique_context']['is_scientific_evidence'])

    def test_removal_cannot_receive_factual_sources_or_wrong_member(self):
        with self.assertRaises(ValueError):self.execute('removal',sources=self.f.sources)
        self.out=self.f.root/'second'
        with self.assertRaises(ValueError):self.execute('removal',member=self.pair['repair'])
        self.assertFalse(self.f.calls)

    def test_fabricated_capacity_fails_when_member_actually_fits(self):
        member=dict(status='capacity',request=None,payload=None)
        with self.assertRaises(ValueError):self.execute('removal',member=member)
        self.assertTrue((self.out/'FAILURE.json').exists())
        self.assertFalse(self.f.calls)

    def test_oversized_factual_member_preserves_fitting_removal(self):
        raw=[dict(source_id=f'p{i}',text='é'*500,sha256=model.codecs.digest(('é'*500).encode())) for i in range(8)]
        self.pair=model.make_repair_pair(self.q,self.prior,self.critic,raw,self.f.model)
        first=self.execute('repair',sources=raw,member=self.pair['repair'])
        self.assertEqual(first['summary']['status'],'capacity')
        self.out=self.f.root/'removal'
        second=self.execute('removal')
        self.assertEqual(second['summary']['status'],'completed')
        self.assertEqual(len(self.f.calls),1)


if __name__=='__main__':unittest.main()
