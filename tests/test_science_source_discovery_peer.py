"""Independent discovery chain and physical-original identity regressions, offline."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError
from tools.science.source_retrieval import fetch_control
from tools.science.source_discovery import official_links, candidate_routes, qualify_original


class FakeResponse(io.BytesIO):
    def __init__(self, body, url):
        super().__init__(body)
        self.url = url
        self.status = 200
        self.headers = {'Content-Length': str(len(body)), 'Content-Type': 'application/pdf'}

    def geturl(self):
        return self.url


class SourceDiscoveryPeerTests(unittest.TestCase):
    nct = 'NCT01234001'
    url = 'https://medical.example.org/reports/Frozen_Poster.pdf'

    def route(self):
        return {'route_id': 'sponsor_poster', 'host': 'medical.example.org', 'path_prefix': '/reports',
                'required_terms': ['frozen', 'poster'], 'bridge_sha256': 'a' * 64}

    def candidate(self, nct_present=False):
        item = {'title': 'Frozen Poster', 'url': self.url,
                'excerpt': self.nct if nct_present else 'Official poster package'}
        return candidate_routes(self.nct, [item], [self.route()])[0]

    def fetched(self, root, body=b'%PDF-1.7\nOriginal fixture NCT01234001'):
        output = root / 'attempt'
        digest = hashlib.sha256(body).hexdigest()
        control = {'nct_id': self.nct, 'url': self.url, 'allowed_hosts': ['medical.example.org'],
                   'max_bytes': 4096, 'expected_sha256': digest, 'expected_format': 'pdf'}
        receipt = fetch_control(control, output, open_response=lambda _: FakeResponse(body, self.url))
        return output, receipt, digest

    def test_only_actual_approved_anchor_links_are_followable(self):
        html = '''<script>const p="https://medical.example.org/reports/script.pdf";</script>
            <p>https://medical.example.org/reports/body.pdf</p>
            <a href="../reports/Frozen_Poster.pdf">poster</a>
            <a href="https://medical.example.org/reports/Frozen_Poster.pdf">duplicate</a>
            <a href="https://medical.example.org.evil.invalid/reports/Frozen_Poster.pdf">fake</a>
            <a href="https://user:password@medical.example.org/reports/Frozen_Poster.pdf">secret</a>
            <a href="https://medical.example.org/reports/Frozen_Poster.pdf?token=secret">signed</a>
            <a href="http://medical.example.org/reports/old.pdf">plain</a>
            <a href="javascript:alert(1)">script</a>'''
        self.assertEqual(official_links(html, 'https://medical.example.org/landing/index.html',
                                        ['medical.example.org']), [self.url])

    def test_html_base_tag_and_script_anchors_cannot_change_link_authority(self):
        html = '''<base href="https://evil.invalid/">
                  <script>"<a href='https://medical.example.org/reports/invented.pdf'>x</a>"</script>
                  <a href="/reports/Frozen_Poster.pdf">poster</a>'''
        self.assertEqual(official_links(html, 'https://medical.example.org/index.html',
                                        ['medical.example.org']), [self.url])

    def test_preapproved_report_can_be_candidate_without_identifier_but_never_identity(self):
        candidate = self.candidate()
        self.assertEqual(candidate['status'], 'official_candidate_unverified')
        self.assertFalse(candidate['exact_nct_in_return'])
        self.assertFalse(candidate['primary_document_identity_qualified'])
        self.assertEqual(candidate['url'], self.url)
        self.assertTrue(self.candidate(True)['exact_nct_in_return'])

    def test_query_echo_and_prefix_or_host_impostors_are_not_candidates(self):
        items = [
            {'title': 'Other trial', 'url': self.url, 'excerpt': 'nothing', 'query': f'{self.nct} Frozen Poster'},
            {'title': 'Frozen Poster', 'url': self.url.replace('/reports/', '/reports-extra/'), 'excerpt': self.nct},
            {'title': 'Frozen Poster', 'url': self.url.replace('medical.example.org', 'medical.example.org.evil.invalid'), 'excerpt': self.nct},
        ]
        # The approved filename itself contains both required terms. Use a neutral
        # URL for the query-only canary so the terms occur solely in query metadata.
        items[0]['url'] = 'https://medical.example.org/reports/neutral.pdf'
        self.assertEqual(candidate_routes(self.nct, items, [self.route()]), [])

    def test_routes_need_commitment_and_safe_boundary_prefix(self):
        for key, value in [('bridge_sha256', None), ('bridge_sha256', 'not-a-digest'),
                           ('path_prefix', 'https://evil.invalid/reports'),
                           ('path_prefix', '/reports/../private'), ('path_prefix', '/reports?token=x')]:
            with self.subTest(key=key, value=value):
                route = self.route()
                route[key] = value
                with self.assertRaises(ContractError):
                    candidate_routes(self.nct, [], [route])

    def test_exact_physical_original_can_pass_identity_without_scientific_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, receipt, digest = self.fetched(Path(tmp))
            result = qualify_original(self.nct, self.candidate(), receipt, digest, output)
            self.assertEqual(result['status'], 'exact_original_identity')
            self.assertFalse(result['historical_availability_qualified'])
            self.assertFalse(result['clinical_scope_qualified'])
            self.assertFalse(result['clinical_label_contribution'])
            result = qualify_original(self.nct, self.candidate(), receipt, 'b' * 64, output)
            self.assertEqual(result['status'], 'different_bytes_requires_review')

    def test_forged_receipt_identity_url_hash_or_size_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, receipt, digest = self.fetched(Path(tmp))
            for field, value in [('nct_id', 'NCT99999999'), ('requested_url', 'https://medical.example.org/reports/other.pdf'),
                                 ('http_status', 403)]:
                with self.subTest(field=field):
                    forged = copy.deepcopy(receipt)
                    forged[field] = value
                    with self.assertRaises(ContractError):
                        qualify_original(self.nct, self.candidate(), forged, digest, output)
            for field, value in [('sha256', 'b' * 64), ('bytes', receipt['body']['bytes'] + 1)]:
                with self.subTest(body_field=field):
                    forged = copy.deepcopy(receipt)
                    forged['body'][field] = value
                    with self.assertRaises(ContractError):
                        qualify_original(self.nct, self.candidate(), forged, digest, output)

    def test_body_outside_approved_output_or_changed_after_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output, receipt, digest = self.fetched(root)
            other = root / 'outside.pdf'
            other.write_bytes(Path(receipt['body']['path']).read_bytes())
            forged = copy.deepcopy(receipt)
            forged['body']['path'] = str(other)
            with self.assertRaises(ContractError):
                qualify_original(self.nct, self.candidate(), forged, digest, output)
            Path(receipt['body']['path']).write_bytes(b'%PDF-1.7\nChanged fixture')
            with self.assertRaises(ContractError):
                qualify_original(self.nct, self.candidate(), receipt, digest, output)

    def test_forged_candidate_url_bridge_control_or_receipt_cannot_qualify(self):
        for attack in ('http_url', 'query_url', 'response_url', 'missing_bridge', 'invalid_bridge',
                       'changed_control_file', 'changed_receipt_file'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                output, receipt, digest = self.fetched(Path(tmp))
                candidate = self.candidate()
                if attack == 'http_url':
                    candidate['url'] = candidate['url'].replace('https:', 'http:')
                    receipt['requested_url'] = candidate['url']
                elif attack == 'query_url':
                    candidate['url'] += '?token=secret'
                    receipt['requested_url'] = candidate['url']
                elif attack == 'response_url':
                    receipt['response_url'] = 'https://evil.invalid/report.pdf'
                elif attack == 'missing_bridge':
                    candidate.pop('bridge_sha256', None)
                elif attack == 'invalid_bridge':
                    candidate['bridge_sha256'] = 'not-a-commitment'
                elif attack == 'changed_control_file':
                    control_path = output / 'control.json'
                    control = json.loads(control_path.read_text(encoding='utf-8'))
                    control['allowed_hosts'].append('evil.invalid')
                    control_path.write_text(json.dumps(control), encoding='utf-8')
                elif attack == 'changed_receipt_file':
                    receipt_path = output / 'receipt.json'
                    archived = json.loads(receipt_path.read_text(encoding='utf-8'))
                    archived['requested_url'] = 'https://evil.invalid/report.pdf'
                    receipt_path.write_text(json.dumps(archived), encoding='utf-8')
                with self.assertRaises(ContractError):
                    qualify_original(self.nct, candidate, receipt, digest, output)
