from copy import deepcopy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import supplied_collection as s
from experiments.litqa_analysis.test_collection import reseal
from experiments.litqa_supplied import resolver as producer
from experiments.litqa_supplied.qualification_fixtures import DOI, fetch


class SuppliedCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)/'diagnostic'
        self.plan=s.decode(producer.canonical(producer.plan(DOI)))

    def build(self,transport=fetch):
        with patch.object(producer.legacy,'fetch_http',side_effect=transport):
            producer.acquire(self.plan,self.root,deadline=time.monotonic()+60)
        self.sha=s.digest((self.root/'RECEIPT.json').read_bytes())

    def result(self):return s.reconstruct(self.root,self.sha,self.plan)

    def test_exact_metadata_unknown_xml_doi_remains_explicit(self):
        self.build(); result=self.result()
        self.assertTrue(result['coverage']['article_retained'])
        self.assertFalse(result['manifest']['plan']['ordinary_retrieval'])
        self.assertEqual(result['source']['xml_dois'],[])
        self.assertEqual(result['articles']['PMC7000001']['doi_basis'],'metadata_only')
        self.assertIsNotNone(result['source']['xml_doi_unknown_reason'])

    def test_metadata_ambiguity_retained_without_arbitrary_choice(self):
        def ambiguous(url,**limits):
            response=fetch(url,**limits)
            if '/search?' in url:
                data=s.decode(response['body']);data['resultList']['result'].append(dict(data['resultList']['result'][0],pmcid='PMC7000002'));data['hitCount']=2
                response['body']=s.canonical(data)
            return response
        self.build(ambiguous); result=self.result()
        self.assertIsNone(result['source']);self.assertEqual(result['decisions'][-1]['reason'],'ambiguous_pmc_identity')

    def test_incomplete_metadata_does_not_resolve(self):
        def incomplete(url,**limits):
            response=fetch(url,**limits)
            if '/search?' in url:
                data=s.decode(response['body']);data['hitCount']=11;response['body']=s.canonical(data)
            return response
        self.build(incomplete); result=self.result()
        self.assertFalse(result['coverage']['exact_doi_resolved']); self.assertEqual(result['decisions'][-1]['reason'],'truncated_or_unknown_complete_metadata')

    def test_wrong_front_doi_rejected(self):
        def different(url,**limits):
            response=fetch(url,**limits)
            if '/fullTextXML' in url:response['body']=response['body'].replace(b'<permissions>',b'<article-id pub-id-type="doi">10.1234/wrong</article-id><permissions>')
            return response
        self.build(different); result=self.result()
        self.assertTrue(result['coverage']['exact_doi_resolved']);self.assertFalse(result['coverage']['article_retained'])
        self.assertEqual(result['decisions'][-1]['reason'],'identity_rights_or_xml_rejected')

    def test_failed_transfer_reservation_not_measured_zero(self):
        def failed(url,**limits):raise TimeoutError('Invented')
        self.build(failed);result=self.result()
        self.assertEqual(result['accounting']['unknown_transfer_upper_bytes'],1048576)
        self.assertEqual(result['accounting']['measured_response_bytes'],0)
        self.assertFalse(result['coverage']['exact_doi_resolved'])

    def test_substituted_source_fails_even_with_new_receipt(self):
        self.build(); path=self.root/'MANIFEST.json';data=s.decode(path.read_bytes())
        data['source']['title']='Substituted title';path.write_bytes(s.canonical(data));self.sha=reseal(self.root)
        with self.assertRaisesRegex(ValueError,'source/decision/coverage'):self.result()

    def test_missing_original_fails(self):
        self.build();(self.root/'responses/001.body').unlink()
        with self.assertRaisesRegex(ValueError,'inventory'):self.result()

    def test_expected_diagnostic_identity_bound(self):
        self.build();other=deepcopy(self.plan);other['doi']='10.1234/other'
        with self.assertRaisesRegex(ValueError,'phase diagnostic plan'):s.reconstruct(self.root,self.sha,other)

    def test_doi_literal_sici_and_role(self):
        plan=s.decode(producer.canonical(producer.plan('10.1002/(sici)1097-0177(200006)218:2<235::aid-dvdy2>3.0.co;2-g')))
        self.assertEqual(s.query_plan(plan),plan['metadata_url'])
        plan['ordinary_retrieval']=True
        with self.assertRaisesRegex(ValueError,'role'):s.query_plan(plan)


if __name__=='__main__':unittest.main()
