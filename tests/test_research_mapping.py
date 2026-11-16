"""Complete fictional publisher membership, identifier and failure controls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, canonical, read_json
from tools.science.historical_inputs import BASE, NOTICE
from tools.science.research_mapping import build_index
from tests.research_fixtures import ResearchMappingFixture


class ResearchMappingTests(ResearchMappingFixture, unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec('pyarrow') is None:
            self.skipTest('install the ingest extra for source-audit tests')
        self.prepare(self.addCleanup)

    def test_complete_index_is_source_linked_and_sealed_without_use_grant(self):
        result = self.run_build()
        self.assertEqual(result['source_rows'], {'targets': 2, 'diseases': 2})
        self.assertEqual(result['indices']['targets']['targets-2']['row_group'], 1)
        self.assertEqual(result['indices']['targets']['targets-2']['row_index'], 0)
        self.assertIsNone(result['indices']['targets']['targets-2']['label'])
        self.assertFalse(result['actor_access_granted'])
        self.assertNotIn('clinicalPhase', json.dumps(result))
        seal = read_json(self.output/'terminal-seal.json')
        self.assertEqual(seal['index_sha256'], hashlib.sha256((self.output/'index.json').read_bytes()).hexdigest())
        self.assertEqual(seal['journal_head'], read_chain(self.output/'journal.jsonl')[-1]['sha256'])

    def test_wrong_manifest_anchor_has_durable_failure(self):
        with self.assertRaisesRegex(ContractError, 'anchor'):
            build_index(self.path, '0'*64, self.output, source_roots=(self.root,))
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_unauthorized_original_path_rejected_before_read(self):
        self.files[0]['path'] = str(self.root.parent/'unapproved.parquet'); self.pin()
        with self.assertRaisesRegex(ContractError, 'source-root'): self.run_build()

    def test_changed_source_hash_rejected_before_parquet_parse(self):
        path = Path(self.files[0]['path']); data = path.read_bytes(); path.write_bytes(b'X'+data[1:])
        with patch('pyarrow.parquet.ParquetFile', side_effect=AssertionError('unverified parse')):
            with self.assertRaisesRegex(ContractError, 'original hash'): self.run_build()

    def test_missing_or_added_publisher_partition_is_not_complete(self):
        self.manifest['products'][0]['parents'].append('output/etl/parquet/targets/missing.parquet'); self.pin()
        with self.assertRaisesRegex(ContractError, 'partition membership'): self.run_build()

    def test_declared_projection_count_must_match_original_rows(self):
        self.manifest['products'][0]['rows'] = 1; self.pin()
        with self.assertRaisesRegex(ContractError, 'row count'): self.run_build()

    def test_newer_availability_or_fallback_cannot_repair_history(self):
        self.manifest['available_by'] = '2026-10-18T00:00:00Z'; self.pin()
        with self.assertRaisesRegex(ContractError, 'availability'): self.run_build()

    def test_receipt_change_and_missing_http_completion_fail(self):
        path = Path(self.files[0]['receipt_path']); doc = read_json(path); doc['http_status'] = 503
        path.write_bytes(canonical(doc)); self.files[0]['receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest(); self.pin()
        with self.assertRaisesRegex(ContractError, 'transport receipt'): self.run_build()

    def test_output_collision_and_budget_do_not_replace_previous_seal(self):
        self.run_build(); before = (self.output/'terminal-seal.json').read_bytes()
        with self.assertRaises(FileExistsError): self.run_build()
        self.assertEqual(before, (self.output/'terminal-seal.json').read_bytes())
        self.output = self.root/'budget-failure'
        with self.assertRaisesRegex(ContractError, 'budget'): self.run_build(max_bytes=1)

    def test_interruption_preserves_a_readable_unsealed_journal(self):
        with patch('tether_engine.source_access.SourceFiles.read', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.run_build()
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_interrupted')
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_seal_write_failure_is_not_a_completed_build(self):
        with patch('tether_engine.journal.RunJournal.seal', side_effect=OSError('fixture disk full')):
            with self.assertRaises(OSError): self.run_build()
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_duplicate_canonical_ids_fail_even_with_fresh_valid_hashes(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        path = Path(self.files[0]['path'])
        pq.write_table(pa.table({'id': ['duplicated', 'duplicated'], 'approvedSymbol': ['first', 'second']}), path)
        replacement = self.item(path, self.files[0]['source_url'])
        replacement['publisher_sha1'] = hashlib.sha1(path.read_bytes()).hexdigest()
        self.files[0] = replacement
        listing_path = Path(self.manifest['metadata'][1]['path'])
        listing_path.write_text(''.join(item['publisher_sha1']+'  '+item['source_url'].removeprefix(BASE)+'\n'
                                        for item in self.files), encoding='utf-8')
        checksum_path = Path(self.manifest['metadata'][2]['path'])
        checksum_path.write_text(hashlib.sha1(listing_path.read_bytes()).hexdigest()+'  release_data_integrity\n', encoding='utf-8')
        self.manifest['metadata'][1] = self.item(listing_path, BASE+'release_data_integrity')
        self.manifest['metadata'][2] = self.item(checksum_path, BASE+'release_data_integrity.sha1')
        self.pin()
        with self.assertRaisesRegex(ContractError, 'Duplicate or conflicting'): self.run_build()

    def test_clinical_columns_are_never_requested_from_arrow(self):
        import pyarrow.parquet as pq
        original = pq.ParquetFile
        requested = []
        class Spy:
            def __init__(self, *args, **kwargs): self.actual = original(*args, **kwargs)
            def __enter__(self): self.actual.__enter__(); return self
            def __exit__(self, *args): return self.actual.__exit__(*args)
            def __getattr__(self, key): return getattr(self.actual, key)
            def iter_batches(self, **kwargs):
                requested.append(tuple(kwargs['columns']))
                return self.actual.iter_batches(**kwargs)
        with patch('pyarrow.parquet.ParquetFile', Spy): self.run_build()
        self.assertEqual(set(requested), {('id', 'approvedSymbol'), ('id', 'name')})

    def test_duplicate_parent_declaration_is_not_complete_membership(self):
        self.manifest['products'][0]['parents'] *= 2; self.pin()
        with self.assertRaisesRegex(ContractError, 'parent declaration'): self.run_build()


if __name__ == '__main__': unittest.main()
