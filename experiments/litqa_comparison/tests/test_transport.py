"""Fictional HTTP responses through the real native capture/replay implementation."""
import json
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode
from experiments.labbench.tests import test_model as fixtures
from experiments.litqa_comparison import transport as t


class StructuredTransportTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ModelTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.q=dict(id='fictional',question='Which color is the fictional orb?')
        self.r,self.p=t.make_request('expand',self.q,self.f.model)
        self.f.request,self.f.payload=self.r,self.p
        self.out=self.f.root/'structured'
        self.raw=self.f.native_body(content='{"queries":[["orb","color"],["orb","hue"]]}')

    def backend(self):
        return t.StructuredBackend(owner=self.f.owner,request=self.r,payload=self.p,
            tokenization=self.f.quote(),output=self.f.output,deadline=time.monotonic()+10,alias='fictional-mcq')

    def execute(self,raw=None):
        with patch.object(t.native,'_check_owner',return_value=12345), \
             patch.object(t.native,'_watchdog',return_value=fixtures.Timer()), \
             patch.object(t.model,'tokenize_once',return_value=self.f.quote()), \
             self.f.transport(fixtures.Response(self.raw if raw is None else raw)):
            return t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                                  deadline=time.monotonic()+10,alias='fictional-mcq')

    def test_native_capture_and_replay(self):
        result=self.execute()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['measured_usage']['input_tokens'],50)
        self.assertEqual(len(self.f.calls),1)
        self.assertTrue((self.out/'native-response.bin').exists())
        replay=t.verify_response(self.r,self.p,self.f.quote(),(self.out/'native-response.bin').read_bytes(),
                                 alias='fictional-mcq',server_spec=self.f.spec,bindings=self.f.bindings)
        self.assertEqual(replay['decoded'],result['decoded'])

    def test_common_answer_contract_replays_native_index(self):
        q=dict(id='00000000-0000-0000-0000-000000000001',question='Which color?',
               choices=['(A) Green','(B) Insufficient information to answer the question','(C) Red'])
        self.r,self.p=t.make_answer_request(q,self.f.sources,self.f.model)
        self.f.request,self.f.payload=self.r,self.p
        result=self.execute(self.f.native_body(content='{"answer_index":0,"evidence_ids":["fixture:p0001"]}'))
        self.assertEqual(result['decoded']['answer_index'],0)
        changed=encode(self.r);changed['sources'][0]['text']='modified'
        with self.assertRaises(ValueError):t.validate_binding(changed,self.p)

    def test_wrong_request_and_token_owner(self):
        q=encode(self.r);q['query']['question']='changed'
        with self.assertRaises(ValueError):t.validate_binding(q,self.p)
        with patch.object(t.native,'_check_owner',return_value=12345):
            quote=self.f.quote();quote['owner_pid']=111
            with self.assertRaises(ValueError):
                t.StructuredBackend(owner=self.f.owner,request=self.r,payload=self.p,tokenization=quote,
                    output=self.f.output,deadline=time.monotonic()+10,alias='fictional-mcq')
        self.assertFalse(self.f.calls)

    def test_cannot_repeat_backend(self):
        with patch.object(t.native,'_check_owner',return_value=12345),patch.object(t.native,'_watchdog',return_value=fixtures.Timer()):
            b=self.backend()
            with self.f.transport(fixtures.Response(self.raw)):
                b.generate(self.r,self.p,timeout_seconds=2)
                with self.assertRaises(ValueError):b.generate(self.r,self.p,timeout_seconds=2)
        self.assertEqual(len(self.f.calls),1)

    def test_exclusive_directory_no_second_dispatch(self):
        self.execute()
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(len(self.f.calls),1)

    def test_malformed_response_preserves_usage_and_bytes(self):
        with self.assertRaises(t.OutputCodecError):self.execute(self.f.native_body(content='{"queries":[["a"]]}'))
        failure=json.loads((self.out/'failure.json').read_bytes())
        self.assertEqual(failure['stage'],'verification')
        self.assertEqual(failure['measured_usage']['input_tokens'],50)
        self.assertTrue(failure['generation_entered'])
        self.assertTrue((self.out/'native-response.bin').exists())

    def test_token_mismatch_rejected(self):
        with self.assertRaises(ValueError) as caught:self.execute(self.f.native_body(content='{"queries":[["a"],["b"]]}',tokens_evaluated=51))
        self.assertNotIsInstance(caught.exception,t.OutputCodecError)

    def test_interrupt_retained_and_not_retried(self):
        with patch.object(t.model,'tokenize_once',side_effect=KeyboardInterrupt('fixture')):
            with self.assertRaises(KeyboardInterrupt):
                t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                    deadline=time.monotonic()+10,alias='fictional-mcq')
        failure=json.loads((self.out/'failure.json').read_bytes())
        self.assertEqual(failure['status'],'interrupted')
        self.assertFalse(failure['generation_entered'])
        self.assertFalse(self.f.calls)

    def test_deadline_before_dispatch_retained(self):
        with self.assertRaises(Exception):
            t.execute_once(self.f.owner,self.r,self.p,output=self.out,journal=self.f.journal,
                           deadline=time.monotonic()-1,alias='fictional-mcq')
        failure=json.loads((self.out/'failure.json').read_bytes())
        self.assertFalse(failure['generation_entered'])
        self.assertFalse(self.f.calls)

    def test_journal_failure_prevents_generation(self):
        def fail(event,**kw):
            if event=='structured_generation_attempt':raise OSError('fixture write failure')
        self.f.journal.append=fail
        with self.assertRaises(OSError):self.execute()
        failure=json.loads((self.out/'failure.json').read_bytes())
        self.assertFalse(failure['generation_entered'])
        self.assertFalse(self.f.calls)


if __name__=='__main__':unittest.main()
