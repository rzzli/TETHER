import copy
from datetime import timedelta
from pathlib import Path
import unittest

from experiments.litqa_analysis import lineage as l, collection as c
from experiments.litqa_comparison.tests import test_admission as fixtures
from experiments.litqa_comparison.pipeline import proof
from experiments.labbench import tether_adapter
from tether_engine.serde import encode
from experiments.litqa_supplied import test_admission as supplied_fixtures
from experiments.litqa_analysis import supplied_collection


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AdmissionTests('runTest'); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f = self.fixture; self.ctx = encode(f.capture().report)
        self.rebuilt = c.reconstruct(f.f.root, f.sha, encode(f.f.plan))
        self.code = proof(Path(tether_adapter.__file__))

    def check(self, context=None, cutoff=None):
        f = self.fixture
        return l.primary(self.ctx if context is None else context, f.query, self.rebuilt, f.f.root, f.sha,
            self.ctx['order'], cutoff or f.cutoff.isoformat(), self.ctx['request_sha256'], self.code)

    def test_all_source_parents_reconstruct(self):
        result = self.check()
        self.assertTrue(result['source_lineage_checked'])
        self.assertFalse(result['scientific_support_verified'])
        self.assertEqual(result['context'],self.ctx)

    def test_missing_unused_parent_and_relabelled_role_fail(self):
        for transform in ('missing','role','parent'):
            context = copy.deepcopy(self.ctx)
            if transform == 'missing': context['source_proofs'].pop()
            if transform == 'role': context['source_proofs'][0]['role']='evaluation_only'
            if transform == 'parent': context['source_proofs'][0]['parents']=[]
            with self.assertRaises(ValueError): self.check(context)

    def test_future_parent_and_publication_fail(self):
        with self.assertRaisesRegex(ValueError,'availability'): self.check(cutoff=(self.fixture.cutoff-timedelta(days=1)).isoformat())
        self.rebuilt['manifest']['sources'][0]['publication_date']='2099-01-01'
        with self.assertRaisesRegex(ValueError,'publication'): self.check()

    def test_cited_passage_and_coverage_substitution_fail(self):
        for transform in ('coverage','text','cutoff'):
            ctx=copy.deepcopy(self.ctx)
            if transform=='coverage': ctx['coverage']['retained_articles'] += 1
            if transform=='text': ctx['selection']['sources'][0]['text']='Different text'
            if transform=='cutoff': ctx['cutoff']='2099-01-01T00:00:00+00:00'
            with self.assertRaises(ValueError): self.check(ctx)

    def test_substantive_missing_citation_rejected_but_unsure_allowed(self):
        native=dict(summary=dict(status='completed',request_sha256=self.ctx['request_sha256']),
                    prediction=dict(answer_index=0,evidence_ids=[]), sources=self.ctx['selection']['sources'])
        result=l.disposition(self.fixture.query,native,self.ctx)
        self.assertEqual(result['disposition']['check_status'],'rejected')
        native['prediction']['answer_index']=1
        self.assertEqual(l.disposition(self.fixture.query,native,self.ctx)['disposition']['check_status'],'accepted')


class SuppliedLineageTests(unittest.TestCase):
    def setUp(self):
        self.f=supplied_fixtures.DiagnosticAdmissionTests('runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.code=proof(Path(tether_adapter.__file__))

    def check(self, context=None):
        f=self.f; ctx=encode(f.capture().report) if context is None else context
        descriptors=encode(f.descriptors)
        rebuilt={doi:supplied_collection.reconstruct(d['root'],d['receipt_sha256'],d['plan']) for doi,d in descriptors.items()}
        return l.supplied(ctx,f.query,f.hint,rebuilt,descriptors,f.cutoff.isoformat(),ctx['request_sha256'],self.code)

    def test_privileged_source_and_original_parent_proofs(self):
        result=self.check()
        self.assertTrue(result['source_lineage_checked'])
        self.assertEqual(result['retained_dois'],self.f.hint['dois'])
        self.assertFalse(result['context']['ordinary_retrieval'])

    def test_omitted_raw_parent_and_privilege_laundering_rejected(self):
        for kind in ('parent','role','ordinary'):
            ctx=encode(self.f.capture().report)
            if kind=='parent':ctx['source_proofs'].pop(0)
            if kind=='role':ctx['source_proofs'][0]['role']='evaluation_only'
            if kind=='ordinary':ctx['ordinary_retrieval']=True
            with self.assertRaises(ValueError):self.check(ctx)

    def test_two_original_roots_and_unavailable_source(self):
        self.f.test_two_papers_keep_both_original_receipt_roots()
        result=self.check();self.assertEqual(len(result['context']['source_proofs']),6)
        self.assertEqual(len(result['retained_dois']),2)


if __name__=='__main__': unittest.main()
