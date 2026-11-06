import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from asof.serde import canonical,encode
from experiments.labbench.tests import test_retrieval as fixtures
from experiments.litqa_comparison import acquisition as a


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'run'
        self.q=dict(id='fictional',question=fixtures.QUESTION)
        self.plan=a.plan(self.q,'lexical')
        self.calls=[]

    def fetch(self,url,**kwargs):
        self.calls.append(url)
        if '/search?' in url:
            number=sum('/search?' in x for x in self.calls)
            ids=['PMC123','PMC456','PMC789'] if number==1 else ['PMC999','PMC456']
            body=canonical(dict(resultList=dict(result=[fixtures.metadata(pmcid=x) for x in ids])))
        else:
            pmcid=url.split('/')[-2]
            body=fixtures.xml(pmcid)
        return dict(body=body,status=200,final_url=url,headers={})

    def run_acquire(self,fetch=None):
        with patch.object(a.legacy,'fetch_http',side_effect=fetch or self.fetch):
            return a.acquire(self.plan,self.root,deadline=time.monotonic()+30)

    def verify(self):
        return a.verify(self.root,a.digest((self.root/'RECEIPT.json').read_bytes()),self.plan)

    def test_balanced_fulltext_and_reconstruction(self):
        actual=self.run_acquire()
        self.assertEqual([s['source_id'] for s in actual['sources']],['PMC123','PMC999','PMC456'])
        self.assertEqual(self.verify(),actual)
        self.assertEqual(len(self.calls),5)
        self.assertGreater(actual['pool']['coverage']['pool_chunks'],0)

    def test_question_or_plan_substitution_fails_before_dispatch(self):
        value=encode(self.plan);value['queries'][0]='different query'
        with self.assertRaises(ValueError):a.acquire(value,self.root,deadline=time.monotonic()+10)
        with self.assertRaises(ValueError):a.plan(dict(self.q,choices=['a']),'lexical')
        self.assertFalse(self.calls)

    def test_expanded_terms_do_not_become_raw_query_operators(self):
        value=a.plan(self.q,'expanded',expansion=dict(queries=[['chlorophyll','transport'],['alias']]))
        self.assertIn('"chlorophyll" AND "transport"',value['queries'][0])
        self.assertIn('FIRST_PDATE:',value['queries'][1])
        with self.assertRaises(ValueError):a.plan(self.q,'expanded',expansion=dict(queries=[['x:*'],['alias']]))

    def test_http_failures_keep_reservation_and_full_schedule(self):
        actual=self.run_acquire(lambda *a,**k: (_ for _ in ()).throw(TimeoutError('fictional')))
        self.assertEqual(len(actual['requests']),2)
        self.assertEqual(actual['accounting']['measured_response_bytes'],0)
        self.assertEqual(actual['accounting']['unknown_transfer_upper_bytes'],2*1024**2)
        self.assertEqual(actual['sources'],())
        self.assertEqual(actual,self.verify())

    def test_interrupt_accounts_uncertain_dispatch_and_stops(self):
        with self.assertRaises(KeyboardInterrupt):self.run_acquire(lambda *a,**k: (_ for _ in ()).throw(KeyboardInterrupt()))
        failure=json.loads((self.root/'FAILURE.json').read_bytes())
        self.assertEqual(failure['attempted_requests'],1)
        self.assertEqual(failure['safety_accounted_bytes'],1024**2)
        self.assertFalse((self.root/'RECEIPT.json').exists())

    def test_existing_directory_never_resumes(self):
        self.run_acquire();count=len(self.calls)
        with self.assertRaises(FileExistsError):self.run_acquire()
        self.assertEqual(len(self.calls),count)

    def test_changed_body_or_extra_file_rejected(self):
        self.run_acquire()
        p=self.root/'responses/000.body';old=p.read_bytes();p.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.verify()
        p.write_bytes(old);(self.root/'extra.json').write_text('{}')
        with self.assertRaises(ValueError):self.verify()

    def test_resealed_changed_sources_still_rejected(self):
        self.run_acquire()
        p=self.root/'MANIFEST.json';m=json.loads(p.read_bytes());m['sources'][0]['title']='invented replacement'
        p.write_bytes(canonical(m))
        # Even when all byte/journal anchors are coherently resealed, semantic
        # source reconstruction must reject the changed title.
        events=[json.loads(line) for line in (self.root/'journal.jsonl').read_bytes().splitlines()]
        events[-1]['details']['manifest_sha256']=a.digest(p.read_bytes())
        events[-1]['sha256']=a.digest(canonical({k:v for k,v in events[-1].items() if k!='sha256'}))
        (self.root/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))
        self.reseal()
        with self.assertRaisesRegex(ValueError,'Source/pool/coverage'):self.verify()

    def reseal(self):
        r=self.root/'RECEIPT.json';d=json.loads(r.read_bytes())
        for name in d['files']:
            raw=(self.root/name).read_bytes();d['files'][name]=dict(sha256=a.digest(raw),bytes=len(raw))
        r.write_bytes(canonical(d))

    def test_resealed_extra_terminal_event_rejected(self):
        self.run_acquire();p=self.root/'journal.jsonl'
        events=[json.loads(line) for line in p.read_bytes().splitlines()]
        extra=dict(sequence=len(events),previous_sha256=events[-1]['sha256'],event='http_terminal',details={})
        extra['sha256']=a.digest(canonical(extra))
        p.write_bytes(p.read_bytes()+canonical(extra)+b'\n');self.reseal()
        with self.assertRaisesRegex(ValueError,'Exact acquisition event'):self.verify()

    def test_duplicate_conflicting_metadata_excluded(self):
        def fetch(url,**kw):
            result=self.fetch(url,**kw)
            if '/search?' in url:
                result['body']=canonical(dict(resultList=dict(result=[fixtures.metadata(pmcid='PMC123',title=str(len(self.calls)))])))
            return result
        actual=self.run_acquire(fetch)
        self.assertEqual(actual['sources'],())
        self.assertIn('conflicting_duplicate_metadata',[r['reason'] for r in actual['decisions']])
        self.assertEqual(actual,self.verify())

    def test_restricted_xml_is_missingness_not_source(self):
        def fetch(url,**kw):
            result=self.fetch(url,**kw)
            if '/fullTextXML' in url:result['body']=result['body'].replace(b'/by/',b'/by-nc/')
            return result
        actual=self.run_acquire(fetch)
        self.assertEqual(actual['sources'],())
        self.assertEqual(actual['coverage']['attempted_fulltext_articles'],3)
        self.assertEqual(actual,self.verify())


if __name__=='__main__':unittest.main()
