from pathlib import Path
import base64
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import native_records as n
from experiments.litqa_comparison.tests import test_replay as fixtures
from experiments.litqa_comparison import pipeline,codecs


class NativeRecordTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReplayTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.query=dict(self.f.q,choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])
        text='An invented source reports increased uptake.'
        self.sources=[dict(source_id='fictional:p1',text=text,sha256=n.digest(text.encode()))]
        self.code=pipeline.proof(Path(codecs.__file__))

    def reconstruct(self,root):
        return n.reconstruct(root,self.query,model_provenance=self.f.info['provenance'],alias=self.f.alias,owner_pid=12345,
                             configuration=codecs.CONFIG,code_proof=self.code)

    def test_original_native_request_prompt_usage_reconstructed(self):
        cell=self.f.root/'cell';result=self.f.call('answer',self.query,self.sources,cell,time.monotonic()+10)
        actual=self.reconstruct(cell)
        self.assertEqual(actual['summary']['usage'],dict(input_tokens=50,output_tokens=12,cost_usd=0.))
        self.assertEqual(actual['prediction']['answer_index'],0)
        self.assertFalse(actual['evidence_lineage_checked'])

    def test_malformed_native_output_is_retained_not_reinterpreted(self):
        self.f.bad_codec=True;cell=self.f.root/'cell';self.f.call('answer',self.query,self.sources,cell,time.monotonic()+10)
        actual=self.reconstruct(cell)
        self.assertEqual(actual['summary']['status'],'codec_failure');self.assertIsNone(actual['prediction'])
        self.assertEqual(actual['summary']['usage']['output_tokens'],12)

    def test_summary_usage_corruption_rejected(self):
        cell=self.f.root/'cell';self.f.call('answer',self.query,self.sources,cell,time.monotonic()+10)
        summary=n.load(cell/'SUMMARY.json');summary['usage']['input_tokens']=49
        (cell/'SUMMARY.json').write_bytes(n.canonical(summary))
        with self.assertRaisesRegex(ValueError,'summary'):self.reconstruct(cell)

    def test_unoffered_citation_or_duplicate_keys_fail_decoding(self):
        for text in ('{"answer_index":0,"evidence_ids":["unoffered"]}',
                     '{"answer_index":0,"answer_index":1,"evidence_ids":[]}'):
            with self.assertRaises(ValueError):n.prediction(text,self.query,self.sources)

    def test_capacity_reconstructed_without_native_call(self):
        self.query['question']='α'*5000;cell=self.f.root/'capacity'
        pipeline.model_call('answer',self.query,(),cell,time.monotonic()+10,owner=None,model_provenance=self.f.info['provenance'],alias=self.f.alias)
        actual=self.reconstruct(cell)
        self.assertEqual(actual['summary']['status'],'capacity');self.assertFalse(actual['summary']['generation_entered'])
        self.assertFalse((cell/'native').exists())

    def test_source_text_substitution_changes_expected_request(self):
        cell=self.f.root/'cell';self.f.call('answer',self.query,self.sources,cell,time.monotonic()+10)
        inp=n.load(cell/'INPUT.json');inp['items'][0]['text']='Different statement'
        inp['items'][0]['sha256']=n.digest(b'Different statement');(cell/'INPUT.json').write_bytes(n.canonical(inp))
        with self.assertRaisesRegex(ValueError,'context'):self.reconstruct(cell)

    def cell(self):
        root=self.f.root/'cell';self.f.call('answer',self.query,self.sources,root,time.monotonic()+10);return root

    def rewrite_events(self,root,mutate):
        events=n.journal(root/'journal.jsonl');mutate(events);previous=None
        for event in events:
            event.pop('sha256');event['previous_sha256']=previous;event['sha256']=n.digest(n.canonical(event));previous=event['sha256']
        (root/'journal.jsonl').write_bytes(b''.join(n.canonical(e)+b'\n' for e in events))

    def test_resealed_contradictory_reservation_event_rejected(self):
        root=self.cell()
        self.rewrite_events(root,lambda es:es[1]['details'].update(generation_entered=True,measured_usage=dict(input_tokens=999,output_tokens=999,cost_usd=123)))
        with self.assertRaisesRegex(ValueError,'reservation event'):self.reconstruct(root)

    def test_resealed_tokenizer_dispatch_and_terminal_events_rejected(self):
        root=self.cell();original=(root/'journal.jsonl').read_bytes()
        for index,key,value in ((2,'owner_pid',7),(3,'token_count',99),(5,'result_sha256','0'*64)):
            (root/'journal.jsonl').write_bytes(original)
            self.rewrite_events(root,lambda es:es[index]['details'].update({key:value}))
            with self.assertRaisesRegex(ValueError,'event differs'):self.reconstruct(root)

    def test_native_endpoint_non_loopback_and_tokenizer_mismatch_rejected(self):
        root=self.cell();path=root/'native/native-response.bin';wrapper=n.load(path)
        for endpoint in ('https://external.example.invalid','http://127.0.0.1:1234'):
            wrapper['endpoint']=endpoint;path.write_bytes(n.canonical(wrapper))
            with self.assertRaisesRegex(ValueError,'endpoint'):self.reconstruct(root)

    def test_expected_server_endpoint_is_enforced(self):
        root=self.cell()
        with self.assertRaisesRegex(ValueError,'Frozen native endpoint'):
            n.reconstruct(root,self.query,model_provenance=self.f.info['provenance'],alias=self.f.alias,owner_pid=12345,
                          configuration=codecs.CONFIG,code_proof=self.code,expected_endpoint='http://127.0.0.1:1234')

    def test_tokenizer_special_flags_rejected(self):
        root=self.cell();path=root/'native/tokenization/result.json';quote=n.load(path)
        quote['tokenizer_request'].update(add_special=False,parse_special=False)
        path.write_bytes(n.canonical(quote));(path.parent/'request.json').write_bytes(n.canonical(quote['tokenizer_request']))
        with self.assertRaisesRegex(ValueError,'special-token'):self.reconstruct(root)

    def test_contradictory_echoed_stream_and_stop_flags_rejected(self):
        root=self.cell();path=root/'native/native-response.bin';original=path.read_bytes()
        for kind in ('stream','stop','limit'):
            wrapper=n.decode(original);body=n.decode(base64.b64decode(wrapper['body_base64']))
            if kind=='stream':body['generation_settings']['stream']=True
            elif kind=='stop':body['generation_settings']['stop']=[]
            else:body['stopped_limit']=True
            raw=n.canonical(body);wrapper.update(body_base64=base64.b64encode(raw).decode(),body_sha256=n.digest(raw));path.write_bytes(n.canonical(wrapper))
            with self.assertRaisesRegex(ValueError,'echoed setting|stop causes'):self.reconstruct(root)

    def test_terminal_request_hash_rejected(self):
        root=self.cell();path=root/'native/result.json';terminal=n.load(path);terminal['request_sha256']='0'*64;path.write_bytes(n.canonical(terminal))
        with self.assertRaisesRegex(ValueError,'Terminal request'):self.reconstruct(root)

    def test_substituted_grammar_rejected_independently(self):
        root=self.cell();request=n.load(root/'native/request.json');payload=n.load(root/'native/payload.json')
        payload['grammar']='root ::= "invented"';request['payload_sha256']=n.digest(n.canonical(payload))
        (root/'native/request.json').write_bytes(n.canonical(request));(root/'native/payload.json').write_bytes(n.canonical(payload))
        with self.assertRaisesRegex(ValueError,'grammar differs'):self.reconstruct(root)

    def test_context_reservation_bound_rechecked(self):
        root=self.cell();request=n.load(root/'native/request.json');wrapper=n.load(root/'native/native-response.bin')
        config=dict(codecs.CONFIG,context_tokens=1);request['configuration']=config
        (root/'native/request.json').write_bytes(n.canonical(request));wrapper['request_sha256']=n.digest(n.canonical(request))
        (root/'native/native-response.bin').write_bytes(n.canonical(wrapper))
        with self.assertRaisesRegex(ValueError,'context reservation'):
            n.reconstruct(root,self.query,model_provenance=self.f.info['provenance'],alias=self.f.alias,owner_pid=12345,
                          configuration=config,code_proof=self.code)

    def test_parent_reparse_point_rejected_before_read(self):
        root=self.cell();original=Path.lstat
        def stat_for(path):
            if path==root:return SimpleNamespace(st_mode=0o040755,st_file_attributes=0x400)
            return original(path)
        with patch.object(Path,'lstat',stat_for):
            with self.assertRaisesRegex(ValueError,'reparse'):n.read(root/'SUMMARY.json')

    def test_changed_open_file_identity_rejected(self):
        root=self.cell();original=n.os.fstat
        def changed(fd):
            value=original(fd)
            return SimpleNamespace(st_dev=value.st_dev,st_ino=value.st_ino,st_size=value.st_size+1,st_mtime_ns=value.st_mtime_ns,st_ctime_ns=value.st_ctime_ns)
        with patch.object(n.os,'fstat',changed):
            with self.assertRaisesRegex(ValueError,'identity'):n.read(root/'SUMMARY.json')


if __name__=='__main__':unittest.main()
