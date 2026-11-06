from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import patch

from asof.serde import encode
from experiments.litqa_comparison import acquisition as a,admission as adm
from experiments.litqa_comparison.tests import test_acquisition as fixtures


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.AcquisitionTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.q['id']='00000000-0000-0000-0000-000000000001'
        self.f.plan=a.plan(self.f.q,'lexical')
        self.manifest=self.f.run_acquire()
        self.query=dict(self.f.q,choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])
        self.model=dict(weights_sha256={'fixture.gguf':'a'*64},runtime_sha256='b'*64,asset_manifest_sha256='c'*64,
                        model_id='fictional',revision='pinned')
        self.sha=a.digest((self.f.root/'RECEIPT.json').read_bytes())
        self.cutoff=datetime.now(timezone.utc)+timedelta(seconds=1)

    def capture(self,**kw):
        return adm.capture(self.query,self.f.root,self.sha,self.f.plan,kw.pop('cutoff',self.cutoff),self.model,**kw)

    def test_real_graph_and_receipts_accept_captured_sources(self):
        ctx=self.capture()
        self.assertGreater(len(ctx.report['source_proofs']),0)
        pred=dict(answer_index=0,evidence_ids=[ctx.sources[0]['source_id']])
        self.assertTrue(adm.check(ctx,pred,ctx.request)['accepted'])
        self.assertEqual(ctx.report['semantic_support'],'unevaluated')
        with self.assertRaises(TypeError):ctx.sources[0]['text']='modify'

    def test_later_download_rejected_by_graph(self):
        with self.assertRaisesRegex(ValueError,'Ineligible evidence lineage'):
            self.capture(cutoff=self.cutoff-timedelta(days=1))

    def test_evaluator_only_catalog_rejected(self):
        catalog=encode(adm.DEFAULT_CATALOG)
        catalog['datasets'][0]['roles']=['evaluator_only']
        with self.assertRaises(ValueError):self.capture(catalog=catalog)

    def test_rank_order_changes_request_not_original_sources(self):
        ctx=self.capture();order=list(reversed(ctx.report['order']))
        reranked=self.capture(order=order)
        self.assertNotEqual(ctx.request,reranked.request)
        pred=dict(answer_index=0,evidence_ids=[ctx.sources[0]['source_id']])
        self.assertFalse(adm.check(ctx,pred,reranked.request)['accepted'])

    def test_unoffered_or_missing_evidence_not_admitted(self):
        ctx=self.capture()
        for ids in [[],['invented-id']]:
            self.assertFalse(adm.check(ctx,dict(answer_index=0,evidence_ids=ids),ctx.request)['accepted'])
        self.assertTrue(adm.check(ctx,dict(answer_index=1,evidence_ids=[]),ctx.request)['accepted'])

    def test_repeated_capture_reconstructs_same_report(self):
        a=self.capture();b=self.capture()
        self.assertEqual(a.report,b.report)
        self.assertEqual(a.request,b.request)

    def test_query_substitution_is_not_same_context(self):
        changed=dict(self.query,question='different')
        with self.assertRaises(ValueError):
            adm.capture(changed,self.f.root,self.sha,self.f.plan,self.cutoff,self.model)


if __name__=='__main__':unittest.main()
