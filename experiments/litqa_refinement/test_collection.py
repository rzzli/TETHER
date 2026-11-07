"""Invented HTTP fixtures through the existing acquisition engine; no network."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode,fingerprint
from experiments.labbench.tests import test_retrieval as raw_fixtures
from experiments.litqa_refinement import collection as c,contracts
from experiments.litqa_refinement import test_contracts as controls


def critic_for(query,sources):
    ids=[s['source_id'] for s in sources]
    prior=contracts.candidate(query,dict(answer_index=0,evidence_ids=ids[:1]),producer_status='produced',
        original_admission_status='accepted' if ids else 'rejected',native_call_sha256='1'*64,
        generated_at_utc=None,offered_ids=ids)
    decoded=dict(support='supported' if ids else 'insufficient',evidence_ids=ids[:1],criticism='Check the retained source.',
                 queries=[['Lumarin'],['color']])
    critique=contracts.critique(query,prior,sources,decoded,native_status='completed',native_call_sha256='2'*64)
    return prior,critique


def fetcher(ids=('PMC1',),*,text='Fictional Lumarin is cobalt.',publication='2020-01-01',rights='cc by',calls=None):
    def fetch(url,**kwargs):
        if calls is not None:calls.append(url)
        if '/search?' in url:
            body=canonical(dict(resultList=dict(result=[raw_fixtures.metadata(i,firstPublicationDate=publication,license=rights) for i in ids])))
        else:body=raw_fixtures.xml(url.split('/')[-2],body=text)
        return dict(body=body,status=200,final_url=url,headers={})
    return fetch


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'refinement';self.calls=[]
        self.query=controls.query();self.prior,self.critique=critic_for(self.query,controls.sources())
        self.projected=c.from_critic(self.query,self.prior,self.critique,controls.sources());self.plan=self.projected['plan']

    def acquire(self,fetch=None):
        with patch.object(c.acquisition.legacy,'fetch_http',side_effect=fetch or fetcher(('PMC1','PMC2','PMC3','PMC4'),calls=self.calls)):
            return c.acquire(self.plan,self.root,deadline=time.monotonic()+30)

    def verify(self):
        return c.verify(self.root,c.codecs.digest((self.root/'RECEIPT.json').read_bytes()),self.plan)

    def test_supported_critic_still_uses_exact_two_query_three_article_engine(self):
        result=self.acquire();self.assertEqual(result,self.verify())
        self.assertEqual(len(self.calls),5);self.assertEqual(result['request_count'],5)
        self.assertEqual(result['coverage']['retained_articles'],3)
        self.assertEqual(result['accounting']['provider_cost_usd'],0)
        self.assertEqual(result['accounting']['retries'],0)
        self.assertFalse(result['control_is_scientific_evidence'])

    def test_projection_does_not_expose_choices_prior_or_criticism(self):
        raw=canonical(self.plan).decode()
        for key in ('answer_index','choices','prediction','criticism','supported'):
            self.assertNotIn('"'+key+'"',raw)
        self.assertNotIn('Check the retained source.',raw)
        self.assertEqual(self.plan['control_provenance']['critic_context_sha256'],fingerprint(self.critique))
        self.assertEqual(self.plan['raw_plan']['policy']['cutoff_date'],'2026-11-06')
        self.assertIn('option_and_candidate_informed',self.plan['selection_scope'])

    def test_unknown_fields_unsafe_terms_and_wrong_control_fail_before_dispatch(self):
        bad=encode(self.plan);bad['choices']=self.query['choices']
        with patch.object(c.acquisition.legacy,'fetch_http',side_effect=AssertionError('must not call')):
            with self.assertRaises(ValueError):c.acquire(bad,self.root,deadline=time.monotonic()+10)
        self.assertFalse(self.root.exists())
        bad=encode(self.plan);bad['terms'][0]=['PMID123']
        with self.assertRaises(ValueError):c.validate_plan(bad)
        wrong=encode(self.critique);wrong['candidate_sha256']='f'*64
        with self.assertRaises(ValueError):c.from_critic(self.query,self.prior,wrong,controls.sources())

    def test_unavailable_critic_is_not_fabricated_empty_collection(self):
        for status,proof in (('capacity',None),('codec_failure','3'*64)):
            critique=contracts.critique(self.query,self.prior,controls.sources(),None,native_status=status,native_call_sha256=proof)
            result=c.from_critic(self.query,self.prior,critique,controls.sources())
            self.assertEqual(result['reason'],'refinement_query_unavailable');self.assertIsNone(result['plan'])
        self.assertFalse(self.root.exists())

    def test_transport_failures_remain_real_complete_empty_collection(self):
        result=self.acquire(lambda *a,**k:(_ for _ in ()).throw(TimeoutError('fictional')))
        self.assertEqual(result,self.verify());self.assertEqual(result['request_count'],2)
        self.assertEqual(result['coverage']['retained_articles'],0)
        self.assertEqual(result['accounting']['unknown_transfer_upper_bytes'],2*1024**2)

    def test_interruption_preserved_and_never_resumed(self):
        with self.assertRaises(KeyboardInterrupt):self.acquire(lambda *a,**k:(_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertTrue((self.root/'FAILURE.json').exists());self.assertFalse((self.root/'RECEIPT.json').exists())
        with self.assertRaises(FileExistsError):self.acquire()

    def test_changed_original_or_extra_wrapper_file_rejected(self):
        self.acquire();path=self.root/'raw/responses/000.body';original=path.read_bytes();path.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.verify()
        path.write_bytes(original);(self.root/'unexpected').write_bytes(b'extra')
        with self.assertRaises(ValueError):self.verify()


if __name__=='__main__':unittest.main()
