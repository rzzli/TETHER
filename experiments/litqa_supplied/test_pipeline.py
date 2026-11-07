from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical
from experiments.litqa_comparison.tests import test_replay as native_fixtures
from experiments.litqa_supplied import pipeline as p,resolver,test_resolver as fixtures


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.native=native_fixtures.ReplayTests('runTest');self.native.setUp();self.addCleanup(self.native.doCleanups)
        self.source=fixtures.ResolverTests('runTest');self.source.setUp();self.addCleanup(self.source.doCleanups)
        self.root=self.native.root;self.cutoff=datetime.now(timezone.utc)+timedelta(minutes=1)
        self.query=dict(id='00000000-0000-0000-0000-000000000001',question='In the invented study, what happened to cobalt uptake?',
                        choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])
        self.hint={k:self.query[k] for k in ('id','question')};self.hint['dois']=[fixtures.DOI]

    def collect(self):
        root=self.root/'collection'
        with patch.object(resolver.legacy,'fetch_http',side_effect=self.source.fetch):
            report=p.collect([fixtures.DOI],root,seconds=120,policy=resolver.legacy.DEFAULT_POLICY)
        self.assertEqual(report['status'],'complete')
        return p.collection_rows(root,p.primary.proof(root/'STAGE-RECEIPT.json')['sha256'],[fixtures.DOI])

    def answer(self,collected):
        return p.answer([self.query],[self.hint],collected,self.root,self.root/'answer',seconds=120,cutoff=self.cutoff,
                        model_provenance=self.native.info['provenance'],call_model=self.native.call)

    def replay(self,collected):
        root=self.root/'answer'
        return p.replay_answers(root,p.primary.proof(root/'STAGE-RECEIPT.json')['sha256'],[self.query],[self.hint],collected,self.root,
                                cutoff=self.cutoff,model_info=self.native.info)

    def test_complete_diagnostic_native_and_source_replay(self):
        collected=self.collect();report=self.answer(collected)
        self.assertEqual(report['scheduled'],1);self.assertTrue(report['rows'][0]['product']['diagnostic_only'])
        self.assertEqual(report['rows'][0]['product']['disposition']['check_status'],'accepted')
        self.assertEqual(self.replay(collected)['status'],'verified')

    def test_unavailable_source_still_runs_full_answer_schedule(self):
        self.source.hits=[];collected=self.collect();report=self.answer(collected)
        self.assertEqual(report['rows'][0]['product']['disposition']['prediction']['answer_index'],1)
        self.assertEqual(self.replay(collected)['questions'],1)

    def test_malformed_answer_retains_native_usage_and_failure(self):
        collected=self.collect();self.native.bad_codec=True;report=self.answer(collected)
        product=report['rows'][0]['product']
        self.assertEqual(product['disposition']['producer_status'],'parse_failure')
        self.assertEqual(product['call']['summary']['usage']['input_tokens'],50)
        self.assertEqual(self.replay(collected)['status'],'verified')

    def test_incomplete_doi_cohort_blocks_before_model(self):
        with self.assertRaisesRegex(ValueError,'Complete unique DOI'):
            self.answer({})
        self.assertFalse((self.root/'answer').exists())


if __name__=='__main__':unittest.main()
