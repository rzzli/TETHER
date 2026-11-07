"""Source receipt, time, role and raw-removal controls; fictional content only."""
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode,fingerprint
from experiments.litqa_comparison import acquisition,codecs
from experiments.litqa_refinement import admission as a,collection,model
from experiments.litqa_refinement import test_contracts as f,test_collection as fixtures
from experiments.litqa_refinement.test_model import MODEL


class FutureClock(datetime):
    @classmethod
    def now(cls,tz=None):return cls(2100,1,1,tzinfo=timezone.utc)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.query=f.query();self.cutoff='2099-01-01T00:00:00+00:00'
        self.original=self.make_original('original',('PMC1',))
        old=acquisition.verify(self.original['root'],self.original['receipt_sha256'],self.original['plan'])
        self.old_sources=codecs.select_order(old['pool']['pool'],[p['rank_id'] for p in old['pool']['pool']])['sources']
        self.prior,self.critique=fixtures.critic_for(self.query,self.old_sources)
        self.control=fingerprint(dict(query=self.query,candidate=self.prior,critique=self.critique))
        self.new=self.make_refinement('new',('PMC2',))

    def make_original(self,name,ids,**kwargs):
        root=self.root/name;plan=acquisition.plan(dict(id=self.query['id'],question=self.query['question']),'lexical')
        with patch.object(acquisition.legacy,'fetch_http',side_effect=fixtures.fetcher(ids,**kwargs)):
            acquisition.acquire(plan,root,deadline=time.monotonic()+30)
        return dict(root=str(root),receipt_sha256=codecs.digest((root/'RECEIPT.json').read_bytes()),plan=plan)

    def make_refinement(self,name,ids,**kwargs):
        root=self.root/name;plan=collection.from_critic(self.query,self.prior,self.critique,self.old_sources)['plan']
        with patch.object(acquisition.legacy,'fetch_http',side_effect=fixtures.fetcher(ids,**kwargs)):
            collection.acquire(plan,root,deadline=time.monotonic()+30)
        return dict(root=str(root),receipt_sha256=codecs.digest((root/'RECEIPT.json').read_bytes()),plan=plan)

    def capture(self,original=None,new='default',**kwargs):
        return a.capture(self.query,original or self.original,self.new if new=='default' else new,self.cutoff,
                         control_sha256=self.control,**kwargs)

    def requests(self,context):
        return model.make_repair_pair(self.query,self.prior,self.critique,context.sources,MODEL)

    def test_source_preflight_builds_no_model_request_and_keeps_raw_ancestry(self):
        with patch.object(model,'_request',side_effect=AssertionError('preflight must not prepare model')):
            context=self.capture()
        self.assertTrue(context.sources);self.assertEqual(context.report['publication_cutoff'],'2026-11-06')
        self.assertTrue(context.report['source_proofs'])
        self.assertTrue(all(p['dataset_id']=='labbench_retrieved_literature' and p['parents']==() for p in context.report['source_proofs']))
        self.assertTrue(all('/responses/' in p['path'].replace('\\','/') for p in context.report['source_proofs']))
        self.assertFalse(context.report['operational_proofs_citable']);self.assertFalse(context.report['control_is_scientific_evidence'])
        self.assertFalse(any(Path(p['path']).name in ('MANIFEST.json','PLAN.json') for p in context.report['source_proofs']))

    def test_factual_admission_and_empty_removal_mechanical_rejection(self):
        context=self.capture();pair=self.requests(context)
        actual=pair['repair'];prediction=dict(answer_index=0,evidence_ids=[context.sources[0]['source_id']])
        decision=a.check(context,prediction,actual['request'],task='repair',expected_control_sha256=self.control,payload=actual['payload'])
        self.assertTrue(decision['accepted'])
        removed=pair['removal'];prediction=dict(answer_index=0,evidence_ids=[])
        decision=a.check(context,prediction,removed['request'],task='removal',expected_control_sha256=self.control,payload=removed['payload'])
        self.assertFalse(decision['accepted']);self.assertTrue(decision['raw_removal_mechanical_rejection'])
        unsure=a.check(context,dict(answer_index=2,evidence_ids=[]),removed['request'],task='removal',expected_control_sha256=self.control)
        self.assertTrue(unsure['accepted'])

    def test_unavailable_refinement_is_explicit_without_receipt(self):
        with self.assertRaises(ValueError):self.capture(new=None)
        context=self.capture(new=None,unavailable_reason='refinement_query_unavailable')
        self.assertIsNone(context.report['refinement_descriptor']);self.assertIsNone(context.report['coverage']['refinement'])
        self.assertTrue(context.sources);self.assertEqual(context.report['merge']['coverage']['refinement_status'],'unavailable')

    def test_alias_and_conflicting_pmc_versions_keep_exact_original_span_proofs(self):
        identical=self.make_refinement('same',('PMC1',))
        context=self.capture(new=identical)
        self.assertEqual(len(context.report['merge']['sources']),1)
        self.assertEqual(len(context.report['bindings'][0]['receipt_aliases']),2)
        self.assertIn('original_locator',context.report['bindings'][0])
        conflict=self.make_refinement('conflict',('PMC1',),text='Fictional Lumarin is amber.')
        context=self.capture(new=conflict)
        self.assertEqual(context.sources,());self.assertEqual(len(context.report['merge']['exclusions']),1)
        pair=self.requests(context)
        decision=a.check(context,dict(answer_index=0,evidence_ids=[]),pair['repair']['request'],task='repair',expected_control_sha256=self.control)
        self.assertFalse(decision['accepted']);self.assertFalse(decision['raw_removal_mechanical_rejection'])

    def test_future_receipt_and_changed_publication_cutoff_fail(self):
        with patch.object(acquisition,'datetime',FutureClock):
            future=self.make_original('future',('PMC1',))
        with self.assertRaisesRegex(ValueError,'availability cutoff'):self.capture(original=future)
        wrong=encode(self.new);wrong['plan']['raw_plan']['policy']['cutoff_date']='2027-01-01'
        wrong['plan']=collection.plan(wrong['plan']['question'],wrong['plan']['terms'],wrong['plan']['control_provenance'],
                                      policy=wrong['plan']['raw_plan']['policy'])
        with self.assertRaisesRegex(ValueError,'publication cutoff differs'):self.capture(new=wrong)

    def test_future_publication_and_unlicensed_sources_are_exclusions_not_absence(self):
        for name,kwargs in (('future-publication',dict(publication='2099-01-01')),('restricted',dict(rights='cc by-nc'))):
            new=self.make_refinement(name,('PMC3',),**kwargs);context=self.capture(new=new)
            self.assertEqual(context.report['coverage']['refinement']['retained_articles'],0)
            self.assertIn('not biological absence',context.report['coverage']['missingness'])
            self.assertTrue(context.report['source_decisions']['refinement'])
            self.assertTrue(context.sources)

    def test_unknown_publication_is_preserved_with_reason(self):
        unknown=self.make_refinement('unknown-publication',('PMC3',),publication=None)
        context=self.capture(new=unknown)
        record=context.report['temporal']['refinement']['publications'][0]
        self.assertIsNone(record['publication_date']);self.assertIsNotNone(record['unknown_reason'])

    def test_role_denial_and_tampered_receipt_or_original_fail(self):
        catalog=encode(a.DEFAULT_CATALOG);catalog['datasets'][0]['roles']=['evaluation_only']
        with self.assertRaisesRegex(ValueError,'denies agent'):self.capture(catalog=catalog)
        path=Path(self.original['root'])/'responses/002.body';path.write_bytes(b'changed raw original')
        with self.assertRaises(ValueError):self.capture()

    def test_late_mutation_is_operational_failure_and_state_is_immutable(self):
        context=self.capture();pair=self.requests(context)
        with self.assertRaises(TypeError):context.report['bindings'][0]['receipt_aliases'][0]['original']['sha256']='a'*64
        with self.assertRaises(TypeError):context.sources[0]['text']='changed'
        fake=replace(context,_authority=None)
        with self.assertRaises(ValueError):a.revalidate(fake)
        path=Path(self.new['root'])/'raw/responses/002.body';path.write_bytes(b'changed after capture')
        with self.assertRaises(ValueError):
            a.check(context,dict(answer_index=2,evidence_ids=[]),pair['repair']['request'],task='repair',expected_control_sha256=self.control)

    def test_current_citations_control_identity_and_source_mutation_rejected(self):
        context=self.capture();pair=self.requests(context);request=pair['repair']['request']
        for prediction in (dict(answer_index=0,evidence_ids=['candidate_context']),dict(answer_index=0,evidence_ids=['request:000'])):
            self.assertFalse(a.check(context,prediction,request,task='repair',expected_control_sha256=self.control)['accepted'])
        self.assertFalse(a.check(context,dict(answer_index=2,evidence_ids=[]),request,task='repair',expected_control_sha256='e'*64)['accepted'])
        changed=encode(request);changed['sources']=[]
        self.assertFalse(a.check(context,dict(answer_index=2,evidence_ids=[]),changed,task='repair',expected_control_sha256=self.control)['accepted'])


if __name__=='__main__':unittest.main()
