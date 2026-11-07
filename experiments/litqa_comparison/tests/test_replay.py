import base64
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical,encode
from experiments.labbench.tests import test_model as model_fixtures,test_retrieval as source_fixtures
from experiments.litqa_comparison import pipeline as p,replay,transport as t,acquisition as a
from experiments.labbench.retrieval import DEFAULT_POLICY


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.f=model_fixtures.ModelTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.root/'pipeline';self.root.mkdir()
        self.q=dict(id='00000000-0000-0000-0000-000000000001',question=source_fixtures.QUESTION)
        self.alias='fictional-mcq';self.bad_codec=False
        self.info=dict(provenance=self.f.model,spec=encode(self.f.spec),bindings={k:str(v) for k,v in self.f.bindings.items()},
                       owner_pid=12345,alias=self.alias)

    def tokenize(self,owner,payload,*,output,journal,deadline):
        self.f.payload=payload;quote=self.f.quote()
        output=Path(output);output.mkdir()
        request=quote['tokenizer_request'];body=base64.b64decode(quote['body_base64'])
        publish_bytes(output/'request.json',canonical(request));publish_bytes(output/'body.bin',body)
        publish_bytes(output/'result.json',canonical(quote))
        journal.append('mcq_tokenize_attempt',payload_sha256=p.codecs.digest(canonical(payload)),
                       request_sha256=p.codecs.digest(canonical(request)),owner_pid=12345)
        journal.append('mcq_tokenize_terminal',proof_sha256=p.codecs.digest(canonical(quote)),token_count=50,error_class=None,elapsed_seconds=.01)
        return quote

    def call(self,task,query,items,output,deadline):
        if task=='answer':request,payload=t.make_answer_request(query,items,self.f.model)
        else:request,payload=t.make_request(task,query,self.f.model,items)
        self.f.payload=payload
        decoded=(dict(queries=[['protein','transport'],['chlorophyll']]) if task=='expand' else
                 dict(order=[x['rank_id'] for x in reversed(items)]) if task=='rank' else
                 dict(answer_index=0 if items else 1,evidence_ids=[items[0]['source_id']] if items else []))
        body=self.f.native_body(content='malformed' if self.bad_codec else canonical(decoded).decode())
        with patch.object(t.native,'_check_owner',return_value=12345),patch.object(t.native,'_watchdog',return_value=model_fixtures.Timer()),\
             patch.object(t.model,'tokenize_once',side_effect=self.tokenize),self.f.transport(model_fixtures.Response(body)):
            return p.model_call(task,query,items,output,deadline,owner=self.f.owner,model_provenance=self.f.model,alias=self.alias)

    def test_complete_model_cell_reconstructs(self):
        cell=self.root/'cell';actual=self.call('expand',self.q,(),cell,time.monotonic()+10)
        self.assertEqual(replay.model_cell(cell,'expand',self.q,(),self.info),actual)

    def test_codec_failure_reconstructs_without_changing_usage(self):
        self.bad_codec=True;cell=self.root/'cell';actual=self.call('expand',self.q,(),cell,time.monotonic()+10)
        self.assertEqual(actual['summary']['status'],'codec_failure')
        self.assertEqual(replay.model_cell(cell,'expand',self.q,(),self.info),actual)
        self.assertEqual(actual['summary']['usage']['input_tokens'],50)

    def test_usage_corruption_and_extra_event_rejected(self):
        cell=self.root/'cell';self.call('expand',self.q,(),cell,time.monotonic()+10)
        path=cell/'SUMMARY.json';original=path.read_bytes();value=load(path);value['usage']['input_tokens']=49
        path.write_bytes(canonical(value))
        with self.assertRaisesRegex(ValueError,'summary'):replay.model_cell(cell,'expand',self.q,(),self.info)
        path.write_bytes(original)
        j=cell/'journal.jsonl';events=[load_line(line) for line in j.read_bytes().splitlines()]
        event=dict(sequence=len(events),previous_sha256=events[-1]['sha256'],event='structured_call_failed',details={})
        event['sha256']=p.codecs.digest(canonical(event));j.write_bytes(j.read_bytes()+canonical(event)+b'\n')
        with self.assertRaisesRegex(ValueError,'event sequence'):replay.model_cell(cell,'expand',self.q,(),self.info)

    def test_declared_owner_must_match_captured_response(self):
        cell=self.root/'cell';self.call('expand',self.q,(),cell,time.monotonic()+10)
        with self.assertRaisesRegex(ValueError,'owner mismatch'):
            replay.model_cell(cell,'expand',self.q,(),dict(self.info,owner_pid=999))

    def test_capacity_is_recomputed_without_tokenizer_or_generation(self):
        q=dict(self.q,question='é'*4900);cell=self.root/'cell'
        # Payload creation must be inside the real model_call so its typed
        # capacity outcome is retained. No mocked transport is necessary.
        actual=p.model_call('expand',q,(),cell,time.monotonic()+10,owner=self.f.owner,model_provenance=self.f.model,alias=self.alias)
        self.assertEqual(actual['summary']['status'],'capacity')
        self.assertEqual(replay.model_cell(cell,'expand',q,(),self.info),actual)

    def test_whole_four_phase_native_and_source_replay(self):
        parents={};cutoff=datetime.now(timezone.utc)+timedelta(minutes=1)
        for kind in ('expand','collect','rank','answer'):
            required={'expand':(),'collect':('expand',),'rank':('collect',),'answer':('collect','rank')}[kind]
            bindings={k:parents[k] for k in required}
            queries=[dict(self.q,choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])] if kind=='answer' else [self.q]
            root=self.root/kind
            with patch.object(a.legacy,'fetch_http',side_effect=source_fixtures.transport):
                p.execute(kind,queries,root,seconds=120,parents=bindings,policy=DEFAULT_POLICY,
                          cutoff=cutoff,model_provenance=self.f.model,call_model=self.call)
            result=replay.phase(root,p.codecs.digest((root/'STAGE-RECEIPT.json').read_bytes()),kind,queries,
                                parents=bindings,policy=DEFAULT_POLICY,model_info=self.info,cutoff=cutoff)
            parents[kind]=result['rows']
        self.assertEqual(len(parents['answer']),4)
        self.assertTrue(all(r['product']['disposition']['check_status']=='accepted' for r in parents['answer'].values()))


def load_line(value):return __import__('json').loads(value)
def load(path):return load_line(Path(path).read_bytes())


if __name__=='__main__':unittest.main()
