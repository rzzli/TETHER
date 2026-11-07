from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode,parse_json
from experiments.litqa_supplied import resolver as r

DOI='10.1234/invented'
XML=b'''<article><front><article-meta><article-id pub-id-type="pmcid">PMC7000001</article-id>
<article-id pub-id-type="doi">10.1234/invented</article-id><permissions><license>
<license-p>Creative Commons Attribution License.</license-p></license></permissions></article-meta></front>
<body><p>An explicitly invented source reports increased cobalt uptake.</p></body></article>'''


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'doi';self.calls=[];self.xml=XML;self.error=None
        self.hits=[dict(doi=DOI,pmcid='PMC7000001',title='Invented source',isOpenAccess='Y',license='cc by',firstPublicationDate='2020-01-01')]
        self.total=None

    def fetch(self,url,**kwargs):
        self.calls.append(url)
        if self.error:raise self.error
        metadata=dict(hitCount=len(self.hits) if self.total is None else self.total,resultList=dict(result=self.hits))
        return dict(status=200,body=canonical(metadata) if '/search?' in url else self.xml,final_url=url,headers={})

    def acquire(self):
        value=r.plan(DOI)
        with patch.object(r.legacy,'fetch_http',side_effect=self.fetch):
            manifest=r.acquire(value,self.root,deadline=time.monotonic()+30)
        checked=r.verify(self.root,r.digest((self.root/'RECEIPT.json').read_bytes()),value)
        self.assertEqual(manifest,checked);return checked

    def test_exact_doi_two_requests_source_replay(self):
        manifest=self.acquire();self.assertEqual(len(self.calls),2)
        self.assertEqual(manifest['source']['xml_dois'],(DOI,))
        self.assertFalse(manifest['plan']['ordinary_retrieval'])
        self.assertEqual(manifest['coverage']['article_retained'],True)

    def test_missing_doi_no_fulltext_call(self):
        self.hits[0]['doi']='10.1234/different'
        manifest=self.acquire();self.assertEqual(len(self.calls),1);self.assertIsNone(manifest['source'])

    def test_restricted_or_future_metadata_does_not_fetch(self):
        self.hits[0]['license']='cc by-nc'
        manifest=self.acquire();self.assertEqual(len(self.calls),1);self.assertIsNone(manifest['source'])

    def test_ambiguous_identity_does_not_choose_arbitrary_paper(self):
        self.hits.append(dict(self.hits[0],pmcid='PMC7000002'))
        manifest=self.acquire();self.assertEqual(len(self.calls),1)
        self.assertEqual(manifest['decisions'][-1]['reason'],'ambiguous_pmc_identity')

    def test_conflicting_duplicate_metadata_rejected(self):
        self.hits.append(dict(self.hits[0],title='Conflicting title'))
        manifest=self.acquire();self.assertEqual(manifest['decisions'][-1]['reason'],'conflicting_duplicate_metadata')

    def test_partial_metadata_does_not_claim_unique_resolution(self):
        self.total=11;manifest=self.acquire();self.assertEqual(len(self.calls),1)
        self.assertEqual(manifest['decisions'][-1]['reason'],'truncated_or_unknown_complete_metadata')

    def test_conflicting_xml_doi_rejected(self):
        self.xml=XML.replace(b'10.1234/invented',b'10.1234/wrong')
        manifest=self.acquire();self.assertEqual(len(self.calls),2);self.assertIsNone(manifest['source'])

    def test_xml_license_restriction_rejected(self):
        self.xml=XML.replace(b'Creative Commons Attribution License.',b'Creative Commons Attribution NonCommercial License.')
        manifest=self.acquire();self.assertIsNone(manifest['source'])

    def test_timeout_charged_as_unknown_not_retried(self):
        self.error=TimeoutError('invented')
        manifest=self.acquire();self.assertEqual(len(self.calls),1)
        self.assertEqual(manifest['accounting']['unknown_transfer_upper_bytes'],1024**2)
        self.assertEqual(manifest['accounting']['measured_response_bytes'],0)

    def test_interrupt_preserves_attempt_without_receipt_or_retry(self):
        self.error=KeyboardInterrupt()
        with patch.object(r.legacy,'fetch_http',side_effect=self.fetch):
            with self.assertRaises(KeyboardInterrupt):r.acquire(r.plan(DOI),self.root,deadline=time.monotonic()+30)
        self.assertEqual(len(self.calls),1);self.assertFalse((self.root/'RECEIPT.json').exists())
        self.assertFalse(parse_json((self.root/'FAILURE.json').read_bytes())['automatic_retry'])

    def test_changed_source_and_extra_file_rejected(self):
        self.acquire();expected=r.digest((self.root/'RECEIPT.json').read_bytes())
        (self.root/'unexpected.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'inventory'):r.verify(self.root,expected,r.plan(DOI))

    def test_resealed_changed_source_is_not_matching_derived_result(self):
        self.acquire();body=self.root/'responses/001.body';body.write_bytes(XML.replace(b'increased cobalt',b'decreased cobalt'))
        receipt=parse_json((self.root/'RECEIPT.json').read_bytes())
        receipt['files']['responses/001.body']=dict(sha256=r.digest(body.read_bytes()),bytes=body.stat().st_size)
        (self.root/'RECEIPT.json').write_bytes(canonical(receipt))
        with self.assertRaisesRegex(ValueError,'captured bytes'):
            r.verify(self.root,r.digest(canonical(receipt)),r.plan(DOI))

    def test_second_reservation_never_repeats_request(self):
        self.acquire()
        with patch.object(r.legacy,'fetch_http',side_effect=AssertionError('No second dispatch')):
            with self.assertRaises(FileExistsError):r.acquire(r.plan(DOI),self.root,deadline=time.monotonic()+30)

    def test_literal_legacy_doi_remains_encoded_within_fixed_origin(self):
        value=r.plan('10.1002/(sici)1097-0177(200006)218:2<235::aid-dvdy2>3.0.co;2-g')
        self.assertIn('%3C235%3A%3A',value['metadata_url'])
        with self.assertRaises(ValueError):r.plan('10.1234/a" OR anything')


if __name__=='__main__':unittest.main()
