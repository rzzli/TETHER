"""Purpose and wrong-original guards for the amended retrieval route."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.science.source_discovery import candidate_routes,qualify_original,official_links
from tests import test_science_source_discovery_peer as fixture


class DiscoveryPurposeTests(unittest.TestCase):
    def test_different_report_with_same_trial_never_becomes_exact_original(self):
        helper=fixture.SourceDiscoveryPeerTests()
        with tempfile.TemporaryDirectory() as tmp:
            out,receipt,digest=helper.fetched(Path(tmp))
            result=qualify_original(helper.nct,helper.candidate(),receipt,hashlib.sha256(b'other report').hexdigest(),out)
            self.assertEqual('different_bytes_requires_review',result['status'])
            self.assertFalse(result['primary_document_identity_qualified'])
            self.assertFalse(result['clinical_scope_qualified'])

    def test_matching_consent_bytes_do_not_qualify_protocol_or_success_rule(self):
        helper=fixture.SourceDiscoveryPeerTests()
        with tempfile.TemporaryDirectory() as tmp:
            out,receipt,digest=helper.fetched(Path(tmp))
            result=qualify_original(helper.nct,helper.candidate(),receipt,digest,out)
            self.assertTrue(result['primary_document_identity_qualified'])
            self.assertFalse(result['clinical_scope_qualified'])
            self.assertFalse(result['clinical_label_contribution'])
            self.assertFalse(result['historical_availability_qualified'])

    def test_corporate_link_must_be_explicit_not_investor_subdomain_suffix(self):
        self.assertEqual([],official_links('<p>https://investors.sponsor.example/</p>',
            'https://sponsor.example/',['investors.sponsor.example']))
        self.assertEqual(['https://investors.sponsor.example/'],official_links(
            '<a href="https://investors.sponsor.example/">Investors</a>',
            'https://sponsor.example/',['investors.sponsor.example']))


if __name__=='__main__':unittest.main()
