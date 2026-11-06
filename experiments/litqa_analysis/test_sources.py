from pathlib import Path
import tempfile
import unittest

from experiments.litqa_analysis import sources as s

XML='''<article><front><article-meta><article-id pub-id-type="pmcid">PMC7000001</article-id>
<article-id pub-id-type="doi">10.1234/invented</article-id></article-meta></front>
<body><p>α increased <italic>cobalt</italic> uptake.</p></body></article>'''


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        raw=XML.encode();(self.root/'article.xml').write_bytes(raw);text='α increased cobalt uptake.'
        self.source=dict(source_id='PMC7000001',doi='10.1234/invented',
            original=dict(path='article.xml',bytes=len(raw),sha256=s.digest(raw)),
            spans=[dict(evidence_id='PMC7000001:body:p0000',text=text,text_sha256=s.digest(text.encode()))])

    def test_raw_paragraph_markup_and_doi_match(self):
        article=s.read_article(self.root,self.source)
        self.assertEqual(article['paragraphs']['PMC7000001:body:p0000'],'α increased cobalt uptake.')
        self.assertEqual(article['doi_basis'],'metadata_and_xml')

    def test_missing_metadata_doi_can_be_filled_only_as_explicit_xml_identity(self):
        self.source['doi']=None;article=s.read_article(self.root,self.source)
        self.assertEqual(article['reconciled_doi'],'10.1234/invented');self.assertEqual(article['doi_basis'],'xml_only')

    def test_metadata_xml_conflict_not_silently_overwritten(self):
        self.source['doi']='10.1234/other';article=s.read_article(self.root,self.source)
        self.assertIsNone(article['reconciled_doi']);self.assertEqual(article['doi_unknown_reason'],'metadata_xml_doi_conflict')

    def test_original_unicode_character_offsets(self):
        article=s.read_article(self.root,self.source);span=article['paragraphs']['PMC7000001:body:p0000'];part=span[:11]
        item=dict(source_id='chunk',text=part,sha256=s.digest(part.encode()))
        binding=dict(source_id='chunk',document_id='PMC7000001',span_id='PMC7000001:body:p0000',character_start=0,character_end=11,
                     parent_text_sha256=s.digest(span.encode()),original_sha256=article['original_sha256'])
        result=s.selected_passages([item],[binding],{'PMC7000001':article})
        self.assertEqual(result['selected_bytes'],len(part.encode()));self.assertFalse(result['semantic_support_verified'])
        binding['character_end']=10
        with self.assertRaisesRegex(ValueError,'characters'):s.selected_passages([item],[binding],{'PMC7000001':article})

    def test_reported_paragraph_cannot_replace_original(self):
        self.source['spans'][0]['text']='Substituted scientific statement'
        with self.assertRaisesRegex(ValueError,'paragraphs'):s.read_article(self.root,self.source)

    def test_duplicate_manifest_paragraph_rejected(self):
        self.source['spans'].append(dict(self.source['spans'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate manifest'):s.read_article(self.root,self.source)

    def test_legacy_doi_identifiers_and_unrelated_urls(self):
        self.assertEqual(s.doi('http://dx.doi.org/10.1002/Abc<123>'),'10.1002/abc<123>')
        self.assertIsNone(s.doi('https://publisher.example/article/123'))
        self.assertIsNone(s.doi('https://doi.org.evil.example/10.1234/a'))


if __name__=='__main__':unittest.main()
