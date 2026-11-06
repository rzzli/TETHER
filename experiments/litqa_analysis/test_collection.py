"""Invented collection controls; the reader under test imports no producer code."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import collection as c
from experiments.litqa_comparison import acquisition as producer
from experiments.litqa_comparison.qualification_fixtures import fetch, queries


def reseal(root):
    """Re-sign the fabricated local tree to test semantic, not only hash, checks."""
    events=[c.decode(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
    events[-1]['details']['manifest_sha256']=c.digest((root/'MANIFEST.json').read_bytes())
    previous=None
    for event in events:
        event.pop('sha256'); event['previous_sha256']=previous
        event['sha256']=c.digest(c.canonical(event)); previous=event['sha256']
    (root/'journal.jsonl').write_bytes(b''.join(c.canonical(e)+b'\n' for e in events))
    inventory={p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=c.digest(p.read_bytes())) for p in root.rglob('*') if p.is_file() and p.name!='RECEIPT.json'}
    (root/'RECEIPT.json').write_bytes(c.canonical(dict(status='complete',files=inventory)))
    return c.digest((root/'RECEIPT.json').read_bytes())


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)/'collection'
        query={k:queries()[0][k] for k in ('id','question')}
        self.plan=c.decode(producer.canonical(producer.plan(query,'lexical')))

    def build(self,transport=fetch):
        with patch.object(producer.legacy,'fetch_http',side_effect=transport):
            producer.acquire(self.plan,self.root,deadline=time.monotonic()+60)
        self.sha=c.digest((self.root/'RECEIPT.json').read_bytes())
        return self.sha

    def result(self):return c.reconstruct(self.root,self.sha,self.plan)

    def mutate(self,change):
        path=self.root/'MANIFEST.json'; manifest=c.decode(path.read_bytes()); change(manifest)
        path.write_bytes(c.canonical(manifest)); self.sha=reseal(self.root)

    def test_complete_original_collection(self):
        self.build(); result=self.result()
        self.assertEqual(result['manifest']['coverage']['retained_articles'],1)
        self.assertEqual(len(result['manifest']['pool']['pool']),2)
        self.assertEqual(result['retained_dois'],[])
        self.assertEqual(result['accounting']['provider_cost_usd'],0)

    def test_failed_transfer_is_unknown_not_zero_cost(self):
        def failed(url,**limits):raise TimeoutError('Invented timeout')
        self.build(failed); result=self.result()
        self.assertEqual(result['accounting']['measured_response_bytes'],0)
        self.assertEqual(result['accounting']['unknown_transfer_upper_bytes'],2*1048576)
        self.assertEqual(result['manifest']['coverage']['retained_articles'],0)

    def test_resealed_pool_text_substitution_rejected(self):
        self.build()
        def corrupt(m):
            m['pool']['pool'][0]['text']='An invented but different conclusion.'
            m['pool']['pool'][0]['sha256']=c.digest(m['pool']['pool'][0]['text'].encode())
        self.mutate(corrupt)
        with self.assertRaisesRegex(ValueError,'raw-pool'):self.result()

    def test_resealed_coverage_inflation_rejected(self):
        self.build(); self.mutate(lambda m:m['coverage'].update(retained_articles=9))
        with self.assertRaisesRegex(ValueError,'coverage'):self.result()

    def test_resealed_source_license_substitution_rejected(self):
        self.build(); self.mutate(lambda m:m['sources'][0].update(metadata_license='cc0'))
        with self.assertRaisesRegex(ValueError,'source/decision'):self.result()

    def test_resealed_extra_artifact_rejected(self):
        self.build(); (self.root/'UNEXPECTED.json').write_bytes(b'{}'); self.sha=reseal(self.root)
        with self.assertRaisesRegex(ValueError,'Unexpected collection artifact'):self.result()

    def test_missing_original_proof_rejected(self):
        self.build(); (self.root/'responses/002.body').unlink()
        with self.assertRaisesRegex(ValueError,'inventory'):self.result()

    def test_expected_plan_mismatch_rejected(self):
        self.build(); different=deepcopy(self.plan); different['question']['id']='another'
        with self.assertRaisesRegex(ValueError,'phase query plan'):c.reconstruct(self.root,self.sha,different)

    def test_balanced_metadata_order_and_conflicts(self):
        def hit(pmc,title='same'):return dict(pmcid=pmc,title=title,isOpenAccess='Y',license='cc by',firstPublicationDate=None)
        records=[dict(request_id=str(i),transport_status='captured',http_status=200) for i in range(2)]
        bodies={'0':c.canonical(dict(resultList=dict(result=[hit('PMC1'),hit('PMC2'),hit('PMC3')]))),
            '1':c.canonical(dict(resultList=dict(result=[hit('PMC4'),hit('PMC2','conflict'),hit('PMC5')])))}
        eligible,decisions=c.discover(records,bodies,self.plan['policy'])
        self.assertEqual([x['candidate']['pmcid'] for x in eligible],['PMC1','PMC4','PMC3','PMC5'])
        self.assertEqual(decisions,[dict(stage='metadata',pmcid='PMC2',reason='conflicting_duplicate_metadata')])

    def test_future_unknown_and_restricted_metadata_are_distinct(self):
        base=dict(pmcid='PMC1',isOpenAccess='Y',license='cc by')
        self.assertIsNone(c.metadata_candidate(base,self.plan['policy'])[1])
        self.assertEqual(c.metadata_candidate(dict(base,firstPublicationDate='2999-01-01'),self.plan['policy'])[1],'future_or_invalid_publication_date')
        self.assertEqual(c.metadata_candidate(dict(base,license='cc by-nc'),self.plan['policy'])[1],'unsupported_or_unknown_metadata_license')

    def test_restricted_original_xml_becomes_explicit_exclusion(self):
        def restricted(url,**limits):
            response=fetch(url,**limits)
            if '/fullTextXML' in url: response['body']=response['body'].replace(b'Creative Commons Attribution License.',b'Creative Commons Attribution License. Non-commercial only.')
            return response
        self.build(restricted); result=self.result()
        self.assertEqual(result['manifest']['sources'],[])
        self.assertEqual(result['manifest']['decisions'][-1]['reason'],'identity_rights_or_xml_rejected')

    def test_unicode_chunk_bound_offsets_and_selection_permutation(self):
        text='αβγ '*900
        source=dict(source_id='PMC1',original=dict(sha256='a'*64),spans=[dict(evidence_id='PMC1:body:p0000',text=text,text_sha256=c.digest(text.encode()))])
        result=c.pool(dict(question='Which αβγ change?'),[source]); items=result['pool']
        self.assertTrue(all(len(p['text'].encode())<=1000 for p in items))
        self.assertEqual(''.join(text[b['character_start']:b['character_end']] for b in result['bindings']),text)
        selected=c.selection(items,[p['rank_id'] for p in reversed(items)])
        self.assertEqual(selected[0]['text'],items[-1]['text'])
        with self.assertRaisesRegex(ValueError,'permutation'):c.selection(items,['p00']*len(items))


if __name__=='__main__':unittest.main()
