"""Invented native HTTP records qualify single-use refinement transport."""
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.labbench.tests import test_model as fixtures
from experiments.litqa_refinement import contracts, model, transport as t


class RefinementTransportTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ModelTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.q = self.f.query
        self.prior = contracts.candidate(self.q,
            dict(answer_index=0, evidence_ids=['fixture:p0001']),
            producer_status='produced', original_admission_status='accepted',
            native_call_sha256='a'*64, generated_at_utc='2026-11-06T00:00:00Z',
            offered_ids=['fixture:p0001'])
        self.r, self.p = model.make_critic_request(self.q,self.prior,self.f.sources,self.f.model)
        self.f.request,self.f.payload = self.r,self.p
        self.out = self.f.root/'refinement'
        self.answer = dict(support='supported',evidence_ids=['fixture:p0001'],
                           criticism='The passage supplies the answer.',queries=[['orb'],['color']])
        self.raw = self.f.native_body(content=canonical(self.answer).decode())

    def execute(self,raw=None,deadline=None):
        with patch.object(t.native,'_check_owner',return_value=12345), \
             patch.object(t.native,'_watchdog',return_value=fixtures.Timer()), \
             patch.object(t.mcq,'tokenize_once',return_value=self.f.quote()), \
             self.f.transport(fixtures.Response(self.raw if raw is None else raw)):
            return t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                deadline=time.monotonic()+20 if deadline is None else deadline,
                alias='fictional-mcq',execution_id='invented-critic-001')

    def failure(self):
        return json.loads((self.out/'failure.json').read_bytes())

    def test_critic_native_bytes_usage_and_independent_replay(self):
        result=self.execute()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['execution_id'],'invented-critic-001')
        self.assertEqual(result['decoded']['support'],'supported')
        self.assertEqual(result['measured_usage']['input_tokens'],50)
        self.assertEqual(len(self.f.calls),1)
        replay=t.verify_response(self.r,self.p,self.f.quote(),(self.out/'native-response.bin').read_bytes(),
            alias='fictional-mcq',server_spec=self.f.spec,bindings=self.f.bindings)
        self.assertEqual(replay['decoded'],result['decoded'])
        with self.assertRaises(TypeError): result['decoded']['queries'][0][0]='changed'

    def test_repair_and_removed_raw_input_have_distinct_bound_requests(self):
        critic=contracts.critique(self.q,self.prior,self.f.sources,self.answer,
                                 native_status='completed',native_call_sha256='b'*64)
        pair=model.make_repair_pair(self.q,self.prior,critic,self.f.sources,self.f.model)
        requests=[]
        for task in ('repair','removal'):
            self.out=self.f.root/task
            self.r,self.p=pair[task]['request'],pair[task]['payload']
            self.f.request,self.f.payload=self.r,self.p
            citations=['fixture:p0001'] if task=='repair' else []
            result=self.execute(self.f.native_body(content=canonical(dict(answer_index=0,evidence_ids=citations)).decode()))
            self.assertEqual(result['decoded']['answer_index'],0)
            requests.append(self.r)
        self.assertNotEqual(canonical(requests[0]),canonical(requests[1]))
        self.assertEqual(requests[0]['candidate_context'],requests[1]['candidate_context'])
        self.assertEqual(requests[0]['critique_context'],requests[1]['critique_context'])
        self.assertFalse(requests[1]['sources'])
        self.assertEqual(len(self.f.calls),2)

    def test_tampered_context_fails_before_directory_or_network(self):
        changed=encode(self.r);changed['candidate_context']['prediction']['answer_index']=1
        self.r=changed
        with self.assertRaises(ValueError): self.execute()
        self.assertFalse(self.out.exists())
        self.assertFalse(self.f.calls)

    def test_owner_token_quote_is_bound_before_generation(self):
        quote=self.f.quote();quote['owner_pid']=99
        with patch.object(t.native,'_check_owner',return_value=12345):
            with self.assertRaises(ValueError):
                t.RefinementBackend(owner=self.f.owner,request=self.r,payload=self.p,
                    tokenization=quote,output=self.f.output,deadline=time.monotonic()+10,
                    alias='fictional-mcq')
        self.assertFalse(self.f.calls)

    def test_same_output_cannot_dispatch_twice(self):
        self.execute()
        with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(len(self.f.calls),1)

    def test_concurrent_directory_reservation_has_one_dispatch(self):
        with patch.object(t.native,'_check_owner',return_value=12345), \
             patch.object(t.native,'_watchdog',return_value=fixtures.Timer()), \
             patch.object(t.mcq,'tokenize_once',return_value=self.f.quote()), \
             self.f.transport(fixtures.Response(self.raw)):
            def invoke():
                try:
                    return t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                        deadline=time.monotonic()+10,alias='fictional-mcq',execution_id='concurrent-001')['status']
                except FileExistsError: return 'already_reserved'
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses=list(pool.map(lambda _:invoke(),range(2)))
        self.assertCountEqual(statuses,['completed','already_reserved'])
        self.assertEqual(len(self.f.calls),1)

    def test_codec_failure_is_distinct_from_transport_integrity(self):
        with self.assertRaises(t.OutputCodecError):self.execute(self.f.native_body(content='{"support":"supported"}'))
        state=self.failure()
        self.assertEqual(state['stage'],'verification')
        self.assertEqual(state['measured_usage']['input_tokens'],50)
        self.assertTrue(state['generation_entered'])
        self.assertTrue((self.out/'native-response.bin').exists())
        self.out=self.f.root/'mismatch'
        with self.assertRaises(ValueError) as caught:
            self.execute(self.f.native_body(content=canonical(self.answer).decode(),tokens_evaluated=51))
        self.assertNotIsInstance(caught.exception,t.OutputCodecError)

    def test_interrupt_before_tokenization_leaves_attempt(self):
        with patch.object(t.mcq,'tokenize_once',side_effect=KeyboardInterrupt('invented')):
            with self.assertRaises(KeyboardInterrupt):
                t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                    deadline=time.monotonic()+10,alias='fictional-mcq',execution_id='interrupted-001')
        self.assertEqual(self.failure()['status'],'interrupted')
        self.assertFalse(self.failure()['generation_entered'])

    def test_expired_or_invalid_deadline_retains_no_dispatch(self):
        for i,deadline in enumerate((time.monotonic()-1,float('nan'),True)):
            self.out=self.f.root/('deadline-'+str(i))
            with self.assertRaises(Exception):self.execute(deadline=deadline)
            self.assertFalse(self.failure()['generation_entered'])
        self.assertFalse(self.f.calls)

    def test_generation_journal_failure_prevents_call(self):
        def fail(event,**kwargs):
            if event=='refinement_generation_attempt':raise OSError('invented journal write failure')
        self.f.journal.append=fail
        with self.assertRaises(OSError):self.execute()
        self.assertFalse(self.failure()['generation_entered'])
        self.assertFalse(self.f.calls)

    def test_capture_write_failure_keeps_measured_usage_and_no_retry(self):
        publish=t.publish_bytes
        def fail(path,raw):
            if path.name=='native-response.bin': raise OSError('invented full disk')
            return publish(path,raw)
        with patch.object(t,'publish_bytes',side_effect=fail):
            with self.assertRaises(OSError):self.execute()
        self.assertTrue(self.failure()['generation_entered'])
        self.assertEqual(self.failure()['measured_usage']['input_tokens'],50)
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(len(self.f.calls),1)


if __name__=='__main__':unittest.main()
