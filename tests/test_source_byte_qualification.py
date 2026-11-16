"""Byte qualification must not promote evaluator data or hide partial reads."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, read_json, ContractError
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
