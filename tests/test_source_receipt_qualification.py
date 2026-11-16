"""Receipt adaptation preserves provenance and cannot grant actor access."""
import copy
import hashlib
import unittest

from tether_engine.serde import ContractError, canonical
from tools.science.source_receipts import qualify_receipt


class SourceReceiptTests(unittest.TestCase):
    def setUp(self):
        self.payload = b'fictional source bytes'
        digest = hashlib.sha256(self.payload).hexdigest()
        self.entry = dict(bytes=len(self.payload), sha256=digest, release='24.09',
                          source='gene_burden', relative_path='24.09/output/evidence/part.parquet',
                          url='https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/24.09/output/evidence/part.parquet',
                          publisher_algorithm='sha256', publisher_digest=digest,
                          request_sha256='a'*64)
        self.receipt = dict(schema_version=1, status='payload_verified', role='evaluation_only',
                            entry={k: self.entry[k] for k in ('release', 'source', 'relative_path', 'url',
                                                            'publisher_algorithm', 'publisher_digest')},
                            bytes=len(self.payload), sha256=digest, publisher_hash_verified=True,
                            observed_publisher_digest=digest, response_bytes_exact=True, error_class=None,
                            request_sha256='a'*64, finished_at_utc='2026-11-13T11:00:00Z',
                            transport=dict(status='response_complete', http_status=200,
                                           response_bytes_read=len(self.payload), content_length=len(self.payload),
                                           error_class=None))

    def check(self):
        raw = canonical(self.receipt)
        entry = {**self.entry, 'receipt_sha256': hashlib.sha256(raw).hexdigest()}
        return qualify_receipt(raw, self.payload, entry)

    def current(self):
        self.entry.update(receipt_id='fixture-current', dataset_id='ot_evidence', release='25.09')
        self.receipt = dict(status='completed', receipt_id='fixture-current', dataset_id='ot_evidence',
                            release_id='25.09', relative_path=self.entry['relative_path'],
                            url=self.entry['url'], bytes=len(self.payload), sha256=self.entry['sha256'],
                            completed_at_utc='2026-10-11T02:11:32.3798602+00:00',
                            publisher_hash_verified=False)

    def test_historical_preserves_role_and_never_invents_availability(self):
        before = copy.deepcopy(self.receipt)
        result = self.check()
        self.assertEqual(result['receipt_format'], 'historical_partition_v1')
        self.assertEqual(result['collection_role'], 'evaluation_only')
        self.assertFalse(result['actor_access_granted'])
        self.assertIsNone(result['historical_available_by'])
        self.assertEqual(result['retrieved_at'], self.receipt['finished_at_utc'])
        self.assertEqual(self.receipt, before)

    def test_standard_missing_role_stays_unknown(self):
        self.current()
        result = self.check()
        self.assertEqual(result['receipt_format'], 'download_completed_v1')
        self.assertIsNone(result['collection_role'])
        self.assertFalse(result['actor_access_granted'])
        self.assertFalse(result['receipt_claimed_publisher_verified'])
        self.assertTrue(result['publisher_digest_matches_payload'])

    def test_source_and_receipt_hashes_checked_independently(self):
        raw = canonical(self.receipt)
        with self.assertRaisesRegex(ContractError, 'receipt hash'):
            qualify_receipt(raw, self.payload, {**self.entry, 'receipt_sha256': '0'*64})
        self.payload = b'changed source'
        with self.assertRaisesRegex(ContractError, 'payload'):
            self.check()

    def test_acquisition_identity_and_request_are_bound(self):
        for key in ('release', 'source', 'relative_path', 'url', 'publisher_digest'):
            with self.subTest(key=key):
                saved = self.receipt['entry'][key]
                self.receipt['entry'][key] = 'different'
                with self.assertRaises(ContractError): self.check()
                self.receipt['entry'][key] = saved
        self.receipt['request_sha256'] = 'b'*64
        with self.assertRaisesRegex(ContractError, 'request'): self.check()

    def test_transport_failures_cannot_be_adapted_as_complete(self):
        for key, bad in (('status', 'failed'), ('http_status', 206),
                         ('response_bytes_read', 0), ('content_length', 0), ('error_class', 'TimeoutError')):
            with self.subTest(key=key):
                saved = self.receipt['transport'][key]
                self.receipt['transport'][key] = bad
                with self.assertRaisesRegex(ContractError, 'transport'): self.check()
                self.receipt['transport'][key] = saved

    def test_publisher_digest_recomputed_not_trusted(self):
        self.entry['publisher_digest'] = '0'*64
        self.receipt['entry']['publisher_digest'] = '0'*64
        self.receipt['observed_publisher_digest'] = '0'*64
        with self.assertRaisesRegex(ContractError, 'Publisher digest'): self.check()

    def test_sha1_publisher_and_unknown_length_are_supported(self):
        digest = hashlib.sha1(self.payload).hexdigest()
        self.entry.update(publisher_algorithm='sha1', publisher_digest=digest)
        self.receipt['entry'].update(publisher_algorithm='sha1', publisher_digest=digest)
        self.receipt['observed_publisher_digest'] = digest
        self.receipt['transport']['content_length'] = None
        self.assertTrue(self.check()['publisher_digest_matches_payload'])

    def test_boolean_sizes_and_non_utc_dates_are_rejected(self):
        for value in (True, -1, 2.5):
            self.receipt['bytes'] = value
            with self.assertRaises(ContractError): self.check()
        self.receipt['bytes'] = len(self.payload)
        for value in ('2026-11-13', '2026-11-13T12:00:00+01:00', None):
            self.receipt['finished_at_utc'] = value
            with self.assertRaisesRegex(ContractError, 'UTC'): self.check()

    def test_standard_identity_and_relative_path_are_bound(self):
        self.current()
        self.receipt['relative_path'] = self.entry['relative_path'].replace('/', '\\')
        self.check()
        for key in ('receipt_id', 'dataset_id', 'release_id', 'url', 'relative_path'):
            with self.subTest(key=key):
                saved = self.receipt[key]
                self.receipt[key] = 'different'
                with self.assertRaises(ContractError): self.check()
                self.receipt[key] = saved

    def test_unsupported_status_and_path_traversal_fail(self):
        self.receipt['status'] = 'retrieved_unreviewed'
        with self.assertRaisesRegex(ContractError, 'Unsupported'): self.check()
        self.receipt['status'] = 'payload_verified'
        self.entry['relative_path'] = '../escape'
        self.receipt['entry']['relative_path'] = '../escape'
        with self.assertRaises(ContractError): self.check()

    def test_evaluator_role_is_retained_in_both_formats(self):
        self.current()
        self.receipt['role'] = 'evaluation_only'
        self.assertEqual(self.check()['collection_role'], 'evaluation_only')
        self.assertFalse(self.check()['actor_access_granted'])


if __name__ == '__main__':
    unittest.main()
