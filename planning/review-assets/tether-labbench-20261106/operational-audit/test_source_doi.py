"""Invented DOI normalization/denominator controls, before actual annotation joins."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('independent_doi',Path(__file__).with_name('source_doi.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class DOITests(unittest.TestCase):
    def test_original_line_proof_includes_physical_line_ending(self):
        raw=b'{"id":"fictional","question":"Q?","sources":[],"ideal":"evaluator-only"}\r\n'
        result=audit.annotation_rows(raw)
        self.assertEqual(result,[{'id':'fictional','question':'Q?','sources':[],'raw_line_sha256':audit.A.sha(raw)}])

    def test_explicit_supported_formats(self):
        for value in ('10.1234/ABC.1','doi:10.1234/ABC.1','https://doi.org/10.1234%2FABC.1?tracking=1','http://dx.doi.org/10.1234/abc.1'):
            self.assertEqual(audit.doi(value),'10.1234/abc.1')
        self.assertEqual(audit.doi('10.1234/part(2).'),'10.1234/part(2).')

    def test_aliases_not_guessed_from_publisher_or_pmid(self):
        for value in ('https://publisher.example/article/10.1234/x','https://pubmed.ncbi.nlm.nih.gov/12345/','PMC12345',
                      'https://doi.org.evil.example/10.1234/x','10.1234/contains space',None):
            self.assertIsNone(audit.doi(value))

    def test_missing_metadata_does_not_remove_denominator(self):
        result=audit.compare(['10.1234/a','10.1234/b','https://doi.org/10.1234/a'],
            [{'id':'PMC1','metadata_dois':['10.1234/a'],'xml_dois':['10.1234/a']}],{'PMC1'})
        self.assertEqual(result['annotated_doi_count'],2)
        self.assertEqual(result['retained_metadata_hit_count'],1)
        self.assertEqual(result['selected_metadata_hit_count'],1)
        self.assertEqual(result['unresolved_annotation_value_count'],0)

    def test_xml_can_add_identity_but_conflicts_are_explicit(self):
        docs=[{'id':'PMC1','metadata_dois':[],'xml_dois':['10.1234/a']},
            {'id':'PMC2','metadata_dois':['10.1234/b'],'xml_dois':['10.1234/c']}]
        result=audit.compare(['10.1234/a','10.1234/b'],docs,{'PMC1'})
        self.assertEqual(result['retained_metadata_hit_count'],1)
        self.assertEqual(result['selected_metadata_hit_count'],0)
        self.assertEqual(result['selected_nonconflicting_hit_count'],1)
        self.assertEqual(result['conflicting_article_count'],1)

    def test_xml_does_not_treat_citation_doi_as_article_identity(self):
        xml=b'<article><front><article-meta><article-id pub-id-type="doi">10.1234/SELF</article-id></article-meta></front><back><ref-list><ref><pub-id pub-id-type="doi">10.1234/CITED</pub-id></ref></ref-list></back></article>'
        self.assertEqual(audit.xml_dois(xml),{'10.1234/self'})
        with self.assertRaises(ValueError):audit.xml_dois(b'<!ENTITY x "expanded"><article/>')


if __name__=='__main__':unittest.main(verbosity=2)
