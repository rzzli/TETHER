"""Independent adversarial source transport checks; no network or registry queries."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request

from tether_engine.serde import ContractError
from tools.science.source_retrieval import (
    BoundRedirect, fetch_control, public_url, registry_document_refs, triage_hits,
)


class FakeResponse(io.BytesIO):
    def __init__(self, body, *, status=200, headers=None, url='https://cdn.clinicaltrials.gov/large-docs/01/NCT01234001/Prot_000.pdf'):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}
        self.url = url

    def geturl(self):
        return self.url


class SourceRetrievalPeerTests(unittest.TestCase):
    nct = 'NCT01234001'
    url = 'https://cdn.clinicaltrials.gov/large-docs/01/NCT01234001/Prot_000.pdf'

    def listing(self):
        return {'protocolSection': {'identificationModule': {'nctId': self.nct}},
                'resultsSection': {'secretClinicalOutcome': 'DO_NOT_PROJECT'},
                'documentSection': {'largeDocumentModule': {'largeDocs': [
                    {'filename': 'Prot_000.pdf', 'typeAbbrev': 'PROT', 'label': 'Study Protocol',
                     'date': '2024-01-01', 'uploadDate': '2026-02-01', 'size': 1024,
                     'hasProtocol': True, 'hasSap': False, 'hasIcf': False}]}}}

    def control(self, body):
        return {'nct_id': self.nct, 'url': self.url, 'allowed_hosts': ['cdn.clinicaltrials.gov'],
                'max_bytes': 1024, 'expected_sha256': hashlib.sha256(body).hexdigest(), 'expected_format': 'pdf'}

    def test_query_echo_is_not_a_result_hit(self):
        result = triage_hits(self.nct, [{'query': self.nct, 'title': 'SAP guidance',
                                       'url': 'https://example.org/guidance', 'excerpt': 'NCT99999999'}])[0]
        self.assertEqual(result['status'], 'rejected_no_exact_identifier')

    def test_identifier_boundaries_and_background_mentions_do_not_qualify_documents(self):
        for token, expected in [('NCT012340010', False), ('XNCT01234001', False),
                                ('NCT01234001_suffix', False), ('(NCT01234001)', True),
                                ('review table: NCT01234001 NCT99999999', True)]:
            with self.subTest(token=token):
                result = triage_hits(self.nct, [{'excerpt': token}])[0]
                self.assertEqual(result['exact_requested_identifier_observed'], expected)
                self.assertIs(result['primary_document_identity_qualified'], False)
                self.assertIs(result['historical_availability_qualified'], False)
                self.assertIs(result['clinical_label_contribution'], False)

    def test_structured_identity_and_document_projection_omit_results(self):
        result = registry_document_refs(self.nct, self.listing())
        self.assertNotIn('DO_NOT_PROJECT', json.dumps(result))
        self.assertEqual(result['document_refs'][0]['url'], self.url)
        self.assertEqual(result['temporal_classification'], 'contemporary_only')
        self.assertFalse(result['absence_claim'])
        wrong = self.listing()
        wrong['protocolSection']['identificationModule']['nctId'] = 'NCT99999999'
        with self.assertRaises(ContractError):
            registry_document_refs(self.nct, wrong)

    def test_projection_rejects_nested_outcome_payload_in_scalar_metadata(self):
        for key in ('date', 'uploadDate', 'label', 'typeAbbrev', 'hasProtocol', 'hasSap', 'hasIcf'):
            with self.subTest(key=key):
                payload = self.listing()
                payload['documentSection']['largeDocumentModule']['largeDocs'][0][key] = {'secretClinicalOutcome': 'DO_NOT_PROJECT'}
                with self.assertRaises(ContractError):
                    registry_document_refs(self.nct, payload)

    def test_document_paths_duplicates_and_caps_fail(self):
        for filename in ('../Prot_000.pdf', 'https://evil.invalid/a.pdf', 'Prot_000.pdf?token=secret', 'Prot_000.PDF'):
            with self.subTest(filename=filename):
                payload = self.listing()
                payload['documentSection']['largeDocumentModule']['largeDocs'][0]['filename'] = filename
                with self.assertRaises(ContractError):
                    registry_document_refs(self.nct, payload)
        for count in (2, 101):
            payload = self.listing()
            payload['documentSection']['largeDocumentModule']['largeDocs'] *= count
            with self.assertRaises(ContractError):
                registry_document_refs(self.nct, payload)

    def test_empty_listing_cannot_establish_document_absence(self):
        payload = self.listing()
        payload.pop('documentSection')
        result = registry_document_refs(self.nct, payload)
        self.assertEqual(result['document_refs'], [])
        self.assertFalse(result['absence_claim'])

    def test_public_url_rejects_credentials_tokens_fragments_and_nonpublic_targets(self):
        bad = [self.url + '?token=secret', self.url + '#fragment',
               self.url.replace('https://', 'http://'),
               self.url.replace('https://', 'https://user:password@'),
               self.url.replace('clinicaltrials.gov', 'clinicaltrials.gov.evil.invalid'),
               'https://127.0.0.1/private', 'https://localhost/private']
        for url in bad:
            with self.subTest(url=url):
                with self.assertRaises((ContractError, ValueError)):
                    public_url(url, ['cdn.clinicaltrials.gov', '127.0.0.1', 'localhost'])

    def test_redirect_bound_and_host_change_are_rejected(self):
        handler = BoundRedirect(['cdn.clinicaltrials.gov'])
        request = Request(self.url)
        with self.assertRaises(ContractError):
            handler.redirect_request(request, None, 302, 'Found', {}, 'https://evil.invalid/Prot_000.pdf')
        handler = BoundRedirect(['cdn.clinicaltrials.gov'])
        for _ in range(5):
            handler.redirect_request(request, None, 302, 'Found', {}, self.url)
        with self.assertRaises(ContractError):
            handler.redirect_request(request, None, 302, 'Found', {}, self.url)

    def test_success_keeps_history_scope_and_labels_unqualified(self):
        body = b'%PDF-1.7\nfixture'
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'attempt'
            receipt = fetch_control(self.control(body), out, open_response=lambda _: FakeResponse(
                body, headers={'Content-Length': str(len(body)), 'Set-Cookie': 'secret', 'Authorization': 'secret'}))
            self.assertTrue(receipt['transport_control_passed'])
            self.assertFalse(receipt['historical_availability_qualified'])
            self.assertFalse(receipt['clinical_scope_qualified'])
            self.assertFalse(receipt['clinical_label_contribution'])
            self.assertNotIn('secret', json.dumps(receipt))
            self.assertFalse(receipt['automatic_retry'])
            with self.assertRaises((FileExistsError, ContractError)):
                fetch_control(self.control(body), out, open_response=lambda _: self.fail('duplicate dispatch'))

    def test_http_error_and_wrong_body_never_pass(self):
        for status, body in ((403, b'%PDF-1.7\nfixture'), (200, b'<html>challenge</html>')):
            with self.subTest(status=status, body=body), tempfile.TemporaryDirectory() as tmp:
                receipt = fetch_control(self.control(body), Path(tmp) / 'attempt',
                                        open_response=lambda _: FakeResponse(body, status=status))
                self.assertFalse(receipt['transport_control_passed'])
                self.assertFalse(receipt['clinical_label_contribution'])

    def test_hash_mismatch_and_oversize_retain_no_qualification(self):
        body = b'%PDF-1.7\nfixture'
        with tempfile.TemporaryDirectory() as tmp:
            control = self.control(body)
            control['expected_sha256'] = '0' * 64
            receipt = fetch_control(control, Path(tmp) / 'hash', open_response=lambda _: FakeResponse(body))
            self.assertFalse(receipt['transport_control_passed'])
            control = self.control(body)
            control['max_bytes'] = 5
            out = Path(tmp) / 'size'
            with self.assertRaises(ContractError):
                fetch_control(control, out, open_response=lambda _: FakeResponse(body))
            self.assertTrue((out / 'failure.json').exists())
            self.assertFalse((out / 'receipt.json').exists())

    def test_malformed_length_and_redirect_failure_preserve_failure(self):
        body = b'%PDF-1.7\nfixture'
        for headers, url in (({'Content-Length': 'abc'}, self.url),
                             ({'Content-Length': '2'}, self.url),
                             ({}, 'https://evil.invalid/Prot_000.pdf')):
            with self.subTest(headers=headers, url=url), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'attempt'
                with self.assertRaises(ContractError):
                    fetch_control(self.control(body), out,
                                  open_response=lambda _: FakeResponse(body, headers=headers, url=url))
                self.assertTrue((out / 'failure.json').exists())
                self.assertFalse((out / 'receipt.json').exists())

    def test_timeout_and_interruption_are_recorded_without_retry(self):
        body = b'%PDF-1.7\nfixture'
        for error in (TimeoutError('fixture timeout'), KeyboardInterrupt('fixture interruption')):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'attempt'
                calls = []
                def open_response(request):
                    calls.append(request.full_url)
                    raise error
                with self.assertRaises(type(error)):
                    fetch_control(self.control(body), out, open_response=open_response)
                self.assertEqual(len(calls), 1)
                failure = json.loads((out / 'failure.json').read_text(encoding='utf-8'))
                self.assertEqual(failure['error_class'], type(error).__name__)
                self.assertFalse(failure['automatic_retry'])
                self.assertFalse((out / 'receipt.json').exists())

    def test_mutating_caller_control_during_transport_cannot_change_commitment(self):
        body = b'%PDF-1.7\nfixture'
        with tempfile.TemporaryDirectory() as tmp:
            control = self.control(body)
            def open_response(request):
                control['expected_sha256'] = '0' * 64
                control['nct_id'] = 'NCT99999999'
                control['allowed_hosts'].append('evil.invalid')
                return FakeResponse(body)
            receipt = fetch_control(control, Path(tmp) / 'attempt', open_response=open_response)
            self.assertTrue(receipt['transport_control_passed'])
            self.assertEqual(receipt['nct_id'], self.nct)
            self.assertEqual(receipt['expected_sha256'], hashlib.sha256(body).hexdigest())
