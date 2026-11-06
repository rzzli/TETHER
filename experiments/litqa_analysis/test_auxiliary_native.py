from pathlib import Path
import time
import unittest

from experiments.litqa_analysis import auxiliary_native as a, native_records as n
from experiments.litqa_comparison.tests import test_replay as fixtures
from experiments.litqa_comparison import pipeline,codecs


class AuxiliaryNativeTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReplayTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.query=self.f.q;self.code=pipeline.proof(Path(codecs.__file__))
        self.pool=[dict(rank_id=f'p{i:02d}',source_id=f'invented:{i}',text=text,sha256=n.digest(text.encode()))
                   for i,text in enumerate(('Cobalt uptake increased.','Vehicle controls were stable.'))]

    def reconstruct(self,root,task):
        return a.reconstruct(root,self.query,task=task,model_provenance=self.f.info['provenance'],alias=self.f.alias,
            owner_pid=12345,configuration=codecs.CONFIG,code_proof=self.code)

    def test_original_expansion_reconstructs(self):
        root=self.f.root/'expand';self.f.call('expand',self.query,[],root,time.monotonic()+10)
        result=self.reconstruct(root,'expand')
        self.assertEqual(result['prediction'],dict(queries=[['protein','transport'],['chlorophyll']]))
        self.assertEqual(result['summary']['usage']['input_tokens'],50)

    def test_original_ranking_reconstructs(self):
        root=self.f.root/'rank';self.f.call('rank',self.query,self.pool,root,time.monotonic()+10)
        result=self.reconstruct(root,'rank');self.assertEqual(result['prediction'],['p01','p00']);self.assertEqual(result['pool'],self.pool)

    def test_codec_failures_retain_original_usage(self):
        self.f.bad_codec=True
        for task,pool in (('expand',[]),('rank',self.pool)):
            root=self.f.root/task;self.f.call(task,self.query,pool,root,time.monotonic()+10)
            result=self.reconstruct(root,task)
            self.assertEqual(result['summary']['status'],'codec_failure');self.assertEqual(result['summary']['usage']['output_tokens'],12)

    def test_unicode_capacity_requires_no_native_response(self):
        self.query=dict(self.query,question='é'*4900);root=self.f.root/'capacity'
        pipeline.model_call('expand',self.query,[],root,time.monotonic()+10,owner=None,model_provenance=self.f.info['provenance'],alias=self.f.alias)
        result=self.reconstruct(root,'expand');self.assertEqual(result['summary']['status'],'capacity');self.assertFalse((root/'native').exists())

    def test_expansion_forbids_unsafe_duplicate_empty_extra_terms(self):
        for value in ({'queries':[['IL6R','il6r'],['T cells']]},{'queries':[['x:y'],['x']]},
                      {'queries':[[],['x']]},{'queries':[['a  b'],['x']]},{'queries':[['a'],['b']], 'answer':'secret'}):
            with self.assertRaises(ValueError):a.decode_expansion(n.canonical(value).decode())

    def test_ranking_requires_exact_permutation(self):
        for order in (['p00','p00'],['p01'],['p00','p02']):
            with self.assertRaises(ValueError):a.decode_ranking(n.canonical(dict(order=order)).decode(),self.pool)

    def test_answer_choices_cannot_enter_auxiliary_query(self):
        with self.assertRaisesRegex(ValueError,'question-only'):a.question(dict(self.query,choices=['secret']))

    def test_pool_hash_order_and_size_rejected(self):
        for change in (dict(rank_id='p09'),dict(sha256='0'*64),dict(text='x'*1001)):
            pool=[dict(self.pool[0],**change),self.pool[1]]
            with self.assertRaises(ValueError):a.validate_pool(pool)

    def test_raw_summary_substitution_rejected(self):
        root=self.f.root/'rank';self.f.call('rank',self.query,self.pool,root,time.monotonic()+10)
        path=root/'SUMMARY.json';value=n.load(path);value['decoded']=['p00','p01'];path.write_bytes(n.canonical(value))
        with self.assertRaisesRegex(ValueError,'summary'):self.reconstruct(root,'rank')

    def test_pinned_prompt_source_required(self):
        root=self.f.root/'expand';self.f.call('expand',self.query,[],root,time.monotonic()+10);self.code=dict(self.code,sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'Byte proof'):self.reconstruct(root,'expand')


if __name__=='__main__':unittest.main()
