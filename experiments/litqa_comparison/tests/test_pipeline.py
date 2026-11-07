from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical,encode
from experiments.labbench.retrieval import DEFAULT_POLICY
from experiments.labbench.tests import test_retrieval as fixtures
from experiments.litqa_comparison import pipeline as p,transport,acquisition as a,schedule


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.calls=[];self.fail_task=None
        self.queries=[dict(id=f'00000000-0000-0000-0000-{i:012d}',question=fixtures.QUESTION+f' Case {i}.') for i in (1,2)]
        self.answer_queries=[dict(q,choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced']) for q in self.queries]
        self.model=dict(weights_sha256={'fixture.gguf':'a'*64},runtime_sha256='b'*64,asset_manifest_sha256='c'*64,
                        model_id='fictional',revision='pinned')
        self.cutoff=datetime.now(timezone.utc)+timedelta(minutes=1)

    def fake_model(self,task,query,items,output,deadline):
        output=Path(output);output.mkdir()
        self.calls.append((task,query['id']))
        if task=='answer':request,_=transport.make_answer_request(query,items,self.model)
        else:request,_=transport.make_request(task,query,self.model,items)
        decoded=(dict(queries=[['protein','transport'],['chlorophyll']]) if task=='expand' else
                 [x['rank_id'] for x in reversed(items)] if task=='rank' else
                 dict(answer_index=0 if items else 1,evidence_ids=[items[0]['source_id']] if items else []))
        summary=dict(task=task,status='codec_failure' if task==self.fail_task else 'completed',decoded=None if task==self.fail_task else decoded,
            query_sha256=p.codecs.digest(canonical(query)),items_sha256=p.codecs.digest(canonical(items)),
            request_sha256=p.codecs.digest(canonical(request)),generation_entered=True,
            usage=dict(input_tokens=50,output_tokens=10,cost_usd=0),fixture_only=True)
        publish_bytes(output/'SUMMARY.json',canonical(summary))
        return dict(root=str(output),summary=summary,summary_proof=p.proof(output/'SUMMARY.json'))

    def fetch(self,url,**kw):return fixtures.transport(url,**kw)

    def phase(self,kind,parents=None):
        root=self.root/kind
        with patch.object(a.legacy,'fetch_http',side_effect=self.fetch):
            result=p.execute(kind,self.answer_queries if kind=='answer' else self.queries,root,seconds=120,
                parents=parents,policy=DEFAULT_POLICY,cutoff=self.cutoff,model_provenance=self.model,call_model=self.fake_model)
        rows=p.parent_rows(root,p.codecs.digest((root/'STAGE-RECEIPT.json').read_bytes()),kind,[q['id'] for q in self.queries])
        return result,rows

    def through_collection(self):
        _,expanded=self.phase('expand');_,collected=self.phase('collect',dict(expand=expanded))
        return expanded,collected

    def test_four_phases_complete_all_arms_without_references(self):
        expanded,collected=self.through_collection()
        _,ranked=self.phase('rank',dict(collect=collected))
        result,answered=self.phase('answer',dict(collect=collected,rank=ranked))
        self.assertEqual(result['scheduled'],8)
        self.assertEqual(len(answered),8)
        self.assertEqual(len(self.calls),2+4+8)
        self.assertTrue(all(r['product']['disposition']['check_status']=='accepted' for r in answered.values()))
        for q in self.queries:
            self.assertEqual(collected[(q['id'],'L')]['product']['plan']['strategy'],'lexical')
            self.assertEqual(collected[(q['id'],'E')]['product']['plan']['strategy'],'expanded')

    def test_expansion_failure_is_charged_fallback_not_retry(self):
        self.fail_task='expand';expanded,collected=self.through_collection()
        self.assertEqual(len(self.calls),2)
        self.assertTrue(all(r['status']=='fallback' for r in expanded.values()))
        self.assertTrue(all(r['product']['plan']['strategy']=='lexical' for r in collected.values()))
        self.assertTrue(all(not r['product']['expansion_available'] for r in collected.values()))

    def test_rank_failure_preserves_pool_order(self):
        _,collected=self.through_collection();self.fail_task='rank'
        _,ranked=self.phase('rank',dict(collect=collected))
        self.assertTrue(all(r['status']=='fallback' for r in ranked.values()))
        for key,row in ranked.items():
            manifest,_=p._collection(collected[key])
            self.assertEqual(row['product']['order'],tuple(x['rank_id'] for x in manifest['pool']['pool']))

    def test_integrity_failure_stops_not_fallback(self):
        def bad(*args):raise ValueError('source/model integrity failure')
        with self.assertRaises(ValueError):
            p.execute('expand',self.queries,self.root/'bad',seconds=30,call_model=bad)
        state=schedule.inspect(self.root/'bad')
        self.assertEqual([r['status'] for r in state['rows']],['failed','unexecuted'])

    def test_incomplete_parent_rejected_before_any_model_call(self):
        with self.assertRaisesRegex(ValueError,'Complete parent cohort'):
            p.execute('rank',self.queries,self.root/'bad',seconds=30,parents=dict(collect={}),call_model=self.fake_model)
        self.assertFalse(self.calls);self.assertFalse((self.root/'bad').exists())

    def test_input_choices_rejected_in_expansion(self):
        with self.assertRaises(ValueError):
            p.execute('expand',self.answer_queries,self.root/'bad',seconds=30,call_model=self.fake_model)
        self.assertFalse(self.calls)

    def test_substantive_answer_without_source_is_not_fabricated(self):
        self.fetch=lambda url,**kw:dict(body=b'{"resultList":{"result":[]}}',status=200,final_url=url,headers={})
        _,collected=self.through_collection();_,ranked=self.phase('rank',dict(collect=collected))
        self.assertTrue(all(r['status']=='not_applicable' for r in ranked.values()))
        _,answered=self.phase('answer',dict(collect=collected,rank=ranked))
        self.assertTrue(all(r['product']['disposition']['prediction']['answer_index']==1 for r in answered.values()))
        self.assertEqual(len(self.calls),2+8)


if __name__=='__main__':unittest.main()
