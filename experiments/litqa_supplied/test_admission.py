from datetime import datetime,timedelta,timezone
import unittest
import time
from unittest.mock import patch

from tether_engine.serde import encode
from experiments.litqa_supplied import resolver,admission as a,test_resolver as fixtures


class DiagnosticAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ResolverTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.acquire()
        self.query=dict(id='00000000-0000-0000-0000-000000000001',question='In the invented assay, what happened to cobalt uptake?',
                        choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])
        self.hint={k:self.query[k] for k in ('id','question')};self.hint['dois']=[fixtures.DOI]
        self.descriptors={fixtures.DOI:dict(root=str(self.f.root),receipt_sha256=resolver.digest((self.f.root/'RECEIPT.json').read_bytes()),
                                           plan=resolver.plan(fixtures.DOI))}
        self.model=dict(weights_sha256={'fixture.gguf':'a'*64},runtime_sha256='b'*64,asset_manifest_sha256='c'*64,
                        model_id='fictional',revision='pinned')
        self.cutoff=datetime.now(timezone.utc)+timedelta(seconds=1)

    def capture(self,**kwargs):
        return a.capture(self.query,self.hint,self.descriptors,self.f.root.parent,kwargs.pop('cutoff',self.cutoff),self.model,**kwargs)

    def test_public_information_lineage_and_explicit_privileged_selection(self):
        context=self.capture()
        self.assertTrue(context.report['diagnostic_only']);self.assertFalse(context.report['ordinary_retrieval'])
        self.assertTrue(context.report['selection_uses_reference_paper_identity'])
        self.assertEqual(len(context.sources),1);self.assertTrue(context.report['source_proofs'])
        self.assertTrue(a.check(context,dict(answer_index=0,evidence_ids=[context.sources[0]['source_id']]),context.request)['accepted'])
        self.assertEqual(context.report,self.capture().report)

    def test_future_downloads_rejected(self):
        with self.assertRaisesRegex(ValueError,'Ineligible diagnostic input lineage'):self.capture(cutoff=self.cutoff-timedelta(days=1))

    def test_evaluator_only_papers_cannot_be_laundered(self):
        catalog=encode(a.DEFAULT_CATALOG);catalog['datasets'][0]['roles']=['evaluator_only']
        with self.assertRaises(ValueError):self.capture(catalog=catalog)

    def test_missing_annotated_doi_cannot_be_silently_dropped(self):
        self.hint['dois'].append('10.1234/another')
        with self.assertRaisesRegex(ValueError,'Every annotated source'):self.capture()

    def test_source_hint_cannot_include_key_passage(self):
        self.hint['key-passage']='A secret answer'
        with self.assertRaisesRegex(ValueError,'identity'):self.capture()

    def test_declared_unavailable_source_preserves_missingness(self):
        self.f.root=self.f.root.parent/'unavailable';self.f.hits=[];self.f.acquire()
        self.descriptors[fixtures.DOI]=dict(root=str(self.f.root),receipt_sha256=resolver.digest((self.f.root/'RECEIPT.json').read_bytes()),plan=resolver.plan(fixtures.DOI))
        context=self.capture();self.assertFalse(context.sources)
        self.assertEqual(context.report['coverage']['unknown_or_unavailable_inputs'],(fixtures.DOI,))
        self.assertFalse(a.check(context,dict(answer_index=0,evidence_ids=[]),context.request)['accepted'])
        self.assertTrue(a.check(context,dict(answer_index=1,evidence_ids=[]),context.request)['accepted'])

    def test_two_papers_keep_both_original_receipt_roots(self):
        other='10.1234/second';second=self.f.root.parent/'second'
        self.f.hits[0].update(doi=other,pmcid='PMC7000002')
        self.f.xml=fixtures.XML.replace(b'10.1234/invented',other.encode()).replace(b'PMC7000001',b'PMC7000002')
        plan=resolver.plan(other)
        with patch.object(resolver.legacy,'fetch_http',side_effect=self.f.fetch):
            resolver.acquire(plan,second,deadline=time.monotonic()+30)
        self.hint['dois'].append(other)
        self.descriptors[other]=dict(root=str(second),receipt_sha256=resolver.digest((second/'RECEIPT.json').read_bytes()),plan=plan)
        context=self.capture()
        self.assertEqual(context.report['coverage']['retained_articles'],2)
        self.assertEqual(len(context.report['source_proofs']),6)
        self.assertEqual({s['source_id'].split(':')[0] for s in context.sources},{'PMC7000001','PMC7000002'})


if __name__=='__main__':unittest.main()
