"""Byte qualification must not promote evaluator data or hide partial reads."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, read_json, ContractError, fingerprint
from tether_engine.journal import read_chain
from tools.science.qualify_source_bytes import qualify


class ByteQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'original.bin'
        self.source.write_bytes(b'fictional original')
        self.manifest = self.root / 'screen.json'
        self.document = {'files': [{'path': str(self.source), 'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                         'bytes': self.source.stat().st_size, 'receipt_role': 'evaluation_only'}], 'metadata_pins': []}
        self.pin()
        self.output = self.root / 'verification'

    def pin(self):
        raw = canonical(self.document)
        self.manifest.write_bytes(raw)
        self.anchor = hashlib.sha256(raw).hexdigest()

    def run_check(self, **kwargs):
        return qualify(self.manifest, self.anchor, self.output, source_roots=(self.root,), **kwargs)

    def test_success_is_byte_only_and_receipted(self):
        result = self.run_check()
        self.assertEqual(result['files_verified'], 1)
        self.assertEqual(result['actor_input_qualification'], 'not_established')
        self.assertEqual(read_json(self.output/'report.json')['declared_receipt_roles'], {'evaluation_only': 1})
        seal = read_json(self.output/'terminal-seal.json')
        self.assertEqual(seal['report_sha256'], hashlib.sha256((self.output/'report.json').read_bytes()).hexdigest())
        self.assertEqual(seal['journal_head'], read_chain(self.output/'journal.jsonl')[-1]['sha256'])

    def test_wrong_screen_anchor_fails_before_output(self):
        with self.assertRaisesRegex(ContractError, 'screen hash'):
            qualify(self.manifest, '0'*64, self.output, source_roots=(self.root,))
        self.assertFalse(self.output.exists())

    def test_unauthorized_path_stops_before_payload_read(self):
        self.document['files'][0]['path'] = str(self.root.parent/'outside.bin'); self.pin()
        with self.assertRaisesRegex(ContractError, 'source-root'):
            self.run_check()
        self.assertFalse(self.output.exists())

    def test_same_size_corruption_retains_failure(self):
        self.source.write_bytes(b'X'*self.source.stat().st_size)
        with self.assertRaisesRegex(ContractError, 'fingerprint'):
            self.run_check()
        self.assertFalse((self.output/'terminal-seal.json').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')

    def test_interruption_has_failure_journal_and_no_retry(self):
        with patch('tether_engine.source_access.SourceFiles.digest_size', side_effect=KeyboardInterrupt) as read:
            with self.assertRaises(KeyboardInterrupt): self.run_check()
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['details']['error_class'], 'KeyboardInterrupt')

    def test_duplicate_paths_and_byte_cap_fail_before_output(self):
        self.document['files'] *= 2; self.pin()
        with self.assertRaisesRegex(ContractError, 'Duplicate'): self.run_check()
        self.assertFalse(self.output.exists())
        self.document['files'] = self.document['files'][:1]; self.pin()
        with self.assertRaisesRegex(ContractError, 'byte cap'): self.run_check(max_bytes=1)
        self.assertFalse(self.output.exists())

    def test_output_collision_never_replaces_receipt(self):
        self.run_check()
        before = (self.output/'terminal-seal.json').read_bytes()
        with self.assertRaises(FileExistsError): self.run_check()
        self.assertEqual((self.output/'terminal-seal.json').read_bytes(), before)

    def test_grown_file_rejected_before_hashing_or_output(self):
        self.source.write_bytes(b'X'*1000)
        with patch('tether_engine.source_access.SourceFiles.digest_size', side_effect=AssertionError('Read over cap')):
            with self.assertRaisesRegex(ContractError, 'size differs'): self.run_check()
        self.assertFalse(self.output.exists())

    def test_seal_publication_failure_cannot_claim_completion(self):
        with patch('tether_engine.journal.RunJournal.seal', side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError): self.run_check()
        self.assertFalse((self.output/'terminal-seal.json').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')

    def receipt_fixture(self):
        receipt = self.root/'receipt.json'
        row = self.document['files'][0]
        row.update(receipt_id='fixture', dataset_id='ot_evidence', release='25.09',
                   source='gene_burden', url='https://example.invalid/fixture',
                   relative_path='fixture', publisher_algorithm='sha256', publisher_digest=row['sha256'])
        value = {key: row[key] for key in ('receipt_id', 'dataset_id', 'url', 'relative_path', 'bytes', 'sha256')}
        value.update(release_id='25.09', status='completed', role='evaluation_only',
                     completed_at_utc='2026-10-10T00:00:00Z')
        receipt.write_bytes(canonical(value))
        row.update(receipt_path=str(receipt), receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        self.document['metadata_pins'] = [dict(path=str(receipt), bytes=receipt.stat().st_size,
                                               sha256=row['receipt_sha256'])]
        self.pin()
        return receipt

    def test_integrated_receipt_observations_are_sealed_without_actor_grants(self):
        receipt = self.receipt_fixture()
        result = self.run_check(inspect_receipts=True)
        self.assertEqual(result['receipts'][0]['collection_role'], 'evaluation_only')
        self.assertFalse(result['receipts'][0]['actor_access_granted'])
        self.assertEqual(result['supplemental_receipt_bytes_hashed'], receipt.stat().st_size)
        self.assertEqual(result['total_bytes_hashed'], self.source.stat().st_size + 2*receipt.stat().st_size)
        events = read_chain(self.output/'journal.jsonl')
        self.assertEqual(sum(e['event'] == 'source_receipt_verified' for e in events), 1)

    def test_receipt_must_be_separately_pinned_before_open(self):
        self.receipt_fixture()
        self.document['metadata_pins'] = []; self.pin()
        with self.assertRaisesRegex(ContractError, 'pinned metadata'):
            self.run_check(inspect_receipts=True)
        self.assertFalse(self.output.exists())

    def test_receipt_replay_counts_towards_byte_cap(self):
        receipt = self.receipt_fixture()
        with self.assertRaisesRegex(ContractError, 'receipt replay exceeds byte cap'):
            self.run_check(inspect_receipts=True, max_bytes=self.source.stat().st_size+receipt.stat().st_size)
        self.assertFalse(self.output.exists())

    def test_corrupt_receipt_preserves_failure_without_success_seal(self):
        receipt = self.receipt_fixture()
        receipt.write_bytes(receipt.read_bytes().replace(b'completed', b'corrupted'))
        with self.assertRaisesRegex(ContractError, 'receipt hash'):
            self.run_check(inspect_receipts=True)
        self.assertFalse((self.output/'terminal-seal.json').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')

    def parquet_fixture(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(pa.table({'id': ['fixture-a', 'fixture-b']}), self.source)
        row = self.document['files'][0]
        row.update(sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(), bytes=self.source.stat().st_size,
                   footer_rows=2, footer_row_groups=1,
                   schema_sha256=fingerprint([{'name': 'id', 'type': 'string', 'nullable': True, 'children': []}]))
        self.pin()

    def test_parquet_footers_verified_without_row_decode(self):
        import pyarrow.parquet as pq
        self.parquet_fixture()
        with patch.object(pq.ParquetFile, 'iter_batches', side_effect=AssertionError('Row read')):
            result = self.run_check(inspect_parquet=True)
        self.assertEqual(result['footer_rows'], 2)
        self.assertEqual(result['row_values_read'], 0)
        self.assertEqual(len(result['schemas']), 1)

    def test_forged_footer_and_schema_fail_even_with_correct_payload_hash(self):
        self.parquet_fixture()
        self.document['files'][0]['schema_sha256'] = '0'*64; self.pin()
        with self.assertRaisesRegex(ContractError, 'schema/footer'):
            self.run_check(inspect_parquet=True)
        self.assertFalse((self.output/'terminal-seal.json').exists())
