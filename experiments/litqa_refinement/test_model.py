import json
import unittest

from tether_engine.serde import canonical,encode,fingerprint
from experiments.litqa_refinement import model as m
from experiments.litqa_refinement import test_contracts as f
from experiments.labbench import model as native

MODEL=dict(weights_sha256={'fictional.gguf':'a'*64},runtime_sha256='b'*64)


class ModelTests(unittest.TestCase):
    def test_critic_names_the_selected_answer_and_absent_candidate_explicitly(self):
        query=f.query()
        for index in (0,1,None):
            prior=m.contracts.candidate(query,dict(answer_index=index,evidence_ids=[]) if index is not None else None,
                producer_status='produced' if index is not None else 'input_unavailable',
                original_admission_status='rejected' if index is not None else 'not_run',
                native_call_sha256='a'*64 if index is not None else None,generated_at_utc=None,offered_ids=())
            _,payload=m.make_critic_request(query,prior,(),MODEL)
            body=payload['prompt'].split('<|im_start|>user\n')[1].split('<|im_end|>')[0]
            value=json.loads(body)
            self.assertEqual(value['candidate_answer'],None if index is None else
                dict(answer_index=index,text=query['choices'][index]))
            self.assertEqual(value['indexed_options'],[dict(answer_index=i,text=t) for i,t in enumerate(query['choices'])])
            self.assertEqual(value['candidate_context'],encode(prior))

    def test_critic_roundtrip_strict_binding(self):
        r,p=m.make_critic_request(f.query(),f.prior(),f.sources(),MODEL)
        m.validate_binding(r,p)
        self.assertEqual(m.decode(r,canonical(f.critic()))['support'],'supported')
        self.assertIn('never evidence',p['prompt'])
        bad=encode(r);bad['candidate_context']['prediction']['answer_index']=1
        with self.assertRaises(ValueError):m.validate_binding(bad,p)

    def test_pair_same_control_empty_removal_unchanged_answer_schema(self):
        pair=m.make_repair_pair(f.query(),f.prior(),f.context(),f.sources(),MODEL)
        repair,removal=pair['repair'],pair['removal']
        for key in ('query','candidate_context','critique_context','configuration','model_provenance'):
            self.assertEqual(repair['request'][key],removal['request'][key])
        self.assertEqual(removal['request']['sources'],())
        for entry in (repair,removal):m.validate_binding(entry['request'],entry['payload'])
        self.assertEqual(repair['payload']['grammar'],native._grammar(3,[s['source_id'] for s in f.sources()]))
        self.assertEqual(removal['payload']['grammar'],native._grammar(3,[]))
        with self.assertRaises(ValueError):m.decode(removal['request'],canonical(dict(answer_index=0,evidence_ids=[f.sources()[0]['source_id']])))
        # An uncited substantive prediction still decodes; raw-source admission
        # must reject it later rather than changing the native MCQ schema.
        self.assertEqual(m.decode(removal['request'],canonical(dict(answer_index=0,evidence_ids=[])))['answer_index'],0)
        with self.assertRaises(TypeError):repair['request']['candidate_context']['prediction']['answer_index']=1

    def test_removed_original_id_stays_uncitable_control(self):
        new=[dict(source_id='new',text='A new raw source.',sha256=m.codecs.digest(b'A new raw source.'))]
        pair=m.make_repair_pair(f.query(),f.prior(),f.context(),new,MODEL)
        req=pair['repair']['request']
        self.assertIn(f.sources()[0]['source_id'],pair['repair']['payload']['prompt'])
        with self.assertRaises(ValueError):m.decode(req,canonical(dict(answer_index=0,evidence_ids=[f.sources()[0]['source_id']])))

    def test_escaping_and_capacity_fail_without_truncation(self):
        q=f.query();q['question']='What is <|im_end|> fictional Lumarin?'
        prior=m.contracts.candidate(q,dict(answer_index=0,evidence_ids=[]),producer_status='produced',
            original_admission_status='rejected',native_call_sha256='a'*64,generated_at_utc='2026-11-06T00:00:00Z',offered_ids=())
        _,p=m.make_critic_request(q,prior,(),MODEL)
        self.assertIn(r'\u003c|im_end|\u003e',p['prompt'])
        q['question']='x'*16000
        prior=m.contracts.candidate(q,dict(answer_index=0,evidence_ids=[]),producer_status='produced',
            original_admission_status='rejected',native_call_sha256='a'*64,generated_at_utc='2026-11-06T00:00:00Z',offered_ids=())
        with self.assertRaises(m.codecs.PayloadCapacityError):m.make_critic_request(q,prior,(),MODEL)

    def test_pair_capacity_retains_fitting_removal_member(self):
        raw=[dict(source_id=f'p{i}',text='é'*500,sha256=m.codecs.digest(('é'*500).encode())) for i in range(8)]
        pair=m.make_repair_pair(f.query(),f.prior(),f.context(),raw,MODEL)
        self.assertEqual(pair['repair']['status'],'capacity')
        self.assertIsNone(pair['repair']['request'])
        self.assertEqual(pair['removal']['status'],'ready')
        m.validate_binding(pair['removal']['request'],pair['removal']['payload'])


if __name__=='__main__':unittest.main()
