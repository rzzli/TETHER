from pathlib import Path
import time
import unittest

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


if __name__=='__main__':unittest.main()
