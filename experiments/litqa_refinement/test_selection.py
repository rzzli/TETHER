from pathlib import Path
import unittest

from tether_engine.serde import encode
from experiments.litqa_comparison import selection as original
from experiments.litqa_refinement import selection as s
from experiments.litqa_refinement import test_contracts as f


def article(pmc='PMC1',text='Fictional Lumarin is cobalt.'):
    return dict(source_id=pmc,title='Invented',doi=None,publication_date='2020-01-01',
        metadata_license='cc by',xml_license=[dict(text='CC BY',links=[])],
        original=dict(path='responses/002.body',sha256=s.codecs.digest(text.encode()),bytes=len(text.encode()),receipt_path='responses/002.receipt.json'),
        spans=[dict(source_id=pmc,evidence_id=pmc+':body:p0000',text=text,text_sha256=s.codecs.digest(text.encode()),
                    locator=dict(xml_path='.//body//p',paragraph_index=0))],discovery_request_id='000')


def bundle(rows,tag='original'):
    return dict(root=str(Path.cwd()/('fictional-'+tag)),receipt_sha256=('1' if tag=='original' else '2')*64,sources=rows)


class SelectionTests(unittest.TestCase):
    def test_six_source_merge_matches_existing_chunk_semantics(self):
        rows=[article('PMC'+str(i),text=('Lumarin é cobalt '*110)+str(i)) for i in range(1,7)]
        merged=s.merge_sources(bundle(rows[:3]),bundle(rows[3:],'new'))
        result=s.build_pool(dict(id=f.query()['id'],question=f.query()['question']),merged)
        self.assertEqual(len(merged['sources']),6)
        self.assertLessEqual(len(result['pool']),16);self.assertLessEqual(result['coverage']['pool_text_bytes'],10000)
        self.assertLessEqual(len(s.select_raw(result)['sources']),8)
        self.assertLessEqual(s.select_raw(result)['selected_bytes'],8000)
        # The same <=3 original inputs retain exact old pool/order/span slices.
        three=s.build_pool(dict(id=f.query()['id'],question=f.query()['question']),s.merge_sources(bundle(rows[:3])))
        legacy=original.build_pool(dict(id=f.query()['id'],question=f.query()['question']),rows[:3])
        self.assertEqual(three['pool'],legacy['pool'])
        self.assertEqual(three['coverage'],legacy['coverage'])
        for binding in three['bindings']:
            doc=next(x for x in rows if x['source_id']==binding['document_id'])
            span=doc['spans'][0]
            chunk=next(p for p in three['pool'] if p['source_id']==binding['source_id'])
            self.assertEqual(chunk['text'],span['text'][binding['character_start']:binding['character_end']])
            self.assertEqual(binding['original_locator'],span['locator'])

    def test_aliases_preserve_both_receipts_original_first(self):
        row=article();merged=s.merge_sources(bundle([row]),bundle([row],'new'))
        self.assertEqual(len(merged['sources']),1)
        self.assertEqual([x['branch'] for x in merged['sources'][0]['receipt_aliases']],['original','refinement'])
        self.assertEqual(merged['sources'][0]['receipt_aliases'][1]['collection_receipt_sha256'],'2'*64)
        with self.assertRaises(TypeError):merged['sources'][0]['receipt_aliases'][0]['original']['sha256']='a'*64

    def test_conflicting_versions_rights_and_identity_excluded_completely(self):
        for change in ('body','rights','doi'):
            other=article()
            if change=='body':other['original']['sha256']='a'*64
            elif change=='rights':other['metadata_license']='cc0'
            else:other['doi']='10.0000/fictional'
            merged=s.merge_sources(bundle([article()]),bundle([other],'new'))
            self.assertEqual(merged['sources'],());self.assertEqual(len(merged['exclusions']),1)

    def test_distinct_publications_and_original_tie_order(self):
        merged=s.merge_sources(bundle([article('PMC2')]),bundle([article('PMC1')],'new'))
        pool=s.build_pool(dict(id=f.query()['id'],question=f.query()['question']),merged)
        self.assertTrue(pool['pool'][0]['source_id'].startswith('PMC2:'))
        self.assertEqual(len(pool['pool']),2)
        with self.assertRaises(ValueError):s.merge_sources(bundle([article()]*4))

    def test_semantic_withholding_separate_from_native_candidate(self):
        before=f.prior();good=f.context()
        self.assertEqual(s.select_original(f.query(),before,good)['decision'],'keep')
        for support in ('contradicted','insufficient','not_assessable'):
            value=f.critic();value['support']=support
            context=s.contracts.critique(f.query(),before,f.sources(),value,native_status='completed',native_call_sha256='2'*64)
            result=s.select_original(f.query(),before,context)
            self.assertEqual(result['decision'],'withhold');self.assertTrue(result['native_candidate_unchanged'])
        rejected=f.prior(status='rejected')
        context=s.contracts.critique(f.query(),rejected,f.sources(),f.critic(),native_status='completed',native_call_sha256='2'*64)
        self.assertEqual(s.select_original(f.query(),rejected,context)['reason'],'original_not_admitted')
        unsure=f.prior(index=2)
        context=s.contracts.critique(f.query(),unsure,f.sources(),f.critic(),native_status='completed',native_call_sha256='2'*64)
        self.assertEqual(s.select_original(f.query(),unsure,context)['reason'],'original_native_unsure')


if __name__=='__main__':unittest.main()
