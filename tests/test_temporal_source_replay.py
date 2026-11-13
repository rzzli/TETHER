"""Invented Parquet only; no provider originals or registry records."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical
from experiments.temporal_audit import replay_open_targets as audit


@unittest.skipUnless(importlib.util.find_spec('pyarrow'), 'install the ingest extra for source-audit tests')
class TemporalSourceReplayTests(unittest.TestCase):
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.pa, self.pq = pa, pq
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.parts = []
        for release, source in audit.ROLES:
            rows = [dict(targetId='T_SECRET', diseaseId='D_SECRET', evidenceDate='2022-11-24', publicationDate=None),
                    dict(targetId='T_SECRET', diseaseId='D_SECRET', evidenceDate='2022', publicationDate='2024-09'),
                    dict(targetId=None, diseaseId='D_SECRET', evidenceDate=None, publicationDate='bad-secret'),
                    dict(targetId='OTHER', diseaseId='OTHER', evidenceDate='2024-09-19', publicationDate='2022-11-24')]
            name = audit.provider_prefix(release, source) + 'part-00000.parquet'
            path = self.root / name; path.parent.mkdir(parents=True)
            table = pa.Table.from_pylist([{**row, 'clinicalStatus': 'FORBIDDEN'} for row in rows])
            pq.write_table(table, path, row_group_size=2)
            self.parts.append(dict(release=release, source=source, files=[self.file(path, name)]))
        self.manifest = self.root / 'manifest.json'
        self.seal()

    def file(self, path, provider_path):
        raw = path.read_bytes()
        return dict(path=path.relative_to(self.root).as_posix(), provider_path=provider_path,
                    sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

    def seal(self):
        body = canonical(dict(schema_version=1, kind='ot_temporal_replay_manifest_v1', partitions=self.parts))
        self.manifest.write_bytes(body); self.pin = hashlib.sha256(body).hexdigest()

    def replay(self):
        return audit.replay(self.manifest, self.pin, self.root)

    def test_known_release_partition_layouts(self):
        for release in ('22.11', '24.09'):
            self.assertEqual(audit.provider_prefix(release, 'gene_burden'),
                             f'{release}/output/etl/parquet/evidence/sourceId=gene_burden/')
        self.assertEqual(audit.provider_prefix('25.09', 'gene_burden'),
                         '25.09/output/evidence/sourceId=gene_burden/')

    def test_aggregate_counts_duplicate_pairs_and_no_identifiers(self):
        result = self.replay()
        self.assertEqual(result['file_count'], 9)
        self.assertEqual(result['physical_rows'], 36)
        full = next(v for v in result['views'] if v['release']=='25.09' and v['source']=='gene_burden' and v['view']=='full')
        self.assertEqual(full['pairs'], dict(valid_key_rows=3, invalid_key_rows=1, unique_keys=2))
        self.assertEqual(full['date_views']['evidenceDate']['2022-11-25'],
                         dict(entirely_before=1, at_or_after=1, crossing=1, missing_column=0, null=1, empty=0, malformed=0, unsupported=0))
        comparison = next(c for c in result['comparisons'] if c['source']=='gene_burden' and c['left_release']=='22.11' and c['right_view']=='literal:evidenceDate:2022-11-25')
        self.assertEqual(comparison['pairs']['shared'], 1)
        self.assertEqual(comparison['pairs']['union'], 2)
        self.assertEqual(comparison['pairs']['jaccard'], .5)
        for token in ('T_SECRET', 'D_SECRET', 'bad-secret', 'FORBIDDEN'):
            self.assertNotIn(token, json.dumps(result))
        self.assertEqual(len(result['views']), 21)
        self.assertEqual(len(result['comparisons']), 21)

    def test_only_four_columns_are_projected(self):
        original = self.pq.ParquetFile
        class Guard:
            def __init__(guard, stream): guard.file = original(stream)
            @property
            def schema_arrow(guard): return guard.file.schema_arrow
            @property
            def metadata(guard): return guard.file.metadata
            def iter_batches(guard, **kwargs):
                self.assertEqual(kwargs['columns'], list(audit.COLUMNS))
                return guard.file.iter_batches(**kwargs)
        with patch.object(self.pq, 'ParquetFile', Guard): self.replay()

    def test_absent_dates_and_null_pairs_stay_explicit(self):
        part = self.parts[0]; path = self.root / part['files'][0]['path']
        self.pq.write_table(self.pa.table({'targetId':[None,None], 'diseaseId':['D','D']}), path)
        part['files'] = [self.file(path, part['files'][0]['provider_path'])]; self.seal()
        row = self.replay()['views'][0]
        self.assertEqual(row['pairs']['invalid_key_rows'], 2)
        self.assertEqual(row['date_views']['evidenceDate']['2022-11-25']['missing_column'], 2)

    def test_all_projected_columns_missing_preserves_row_denominator(self):
        part = self.parts[0]; path = self.root / part['files'][0]['path']
        self.pq.write_table(self.pa.table({'unselected':['FORBIDDEN','FORBIDDEN']}), path)
        part['files'] = [self.file(path, part['files'][0]['provider_path'])]; self.seal()
        row = self.replay()['views'][0]
        self.assertEqual(row['rows']['physical_rows'], 2)
        self.assertEqual(row['pairs']['invalid_key_rows'], 2)
        self.assertEqual(row['date_views']['publicationDate']['2024-09-19']['missing_column'], 2)

    def test_direct_script_runs_without_pythonpath_and_never_overwrites(self):
        out_root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        output = out_root / 'report.json'
        command = [sys.executable, '-I', '-B', str(Path(audit.__file__).resolve()),
                   '--manifest', str(self.manifest), '--manifest-sha256', self.pin,
                   '--root', str(self.root), '--output', str(output)]
        first = subprocess.run(command, capture_output=True, text=True, timeout=30, cwd=out_root)
        self.assertEqual(first.returncode, 0, first.stderr)
        original = output.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True, timeout=30, cwd=out_root)
        self.assertEqual(second.returncode, 1)
        self.assertEqual(output.read_bytes(), original)

    def test_output_under_input_root_rejected_before_source_decoding(self):
        with patch.object(audit, 'replay', side_effect=AssertionError('must not read sources')):
            status = audit.main(['--manifest', str(self.manifest), '--manifest-sha256', self.pin,
                                 '--root', str(self.root), '--output', str(self.root/'report.json')])
        self.assertEqual(status, 1)
        self.assertFalse((self.root/'report.json').exists())

    def test_missing_and_duplicate_roles_fail_before_decoding(self):
        for parts in (self.parts[:-1], self.parts + [self.parts[0]]):
            saved = self.parts; self.parts = parts; self.seal()
            with patch.object(self.pq, 'ParquetFile', side_effect=AssertionError('must not decode')):
                with self.assertRaises(ContractError): self.replay()
            self.parts = saved

    def test_duplicate_file_and_cross_role_provider_path_rejected(self):
        self.parts[0]['files'].append(dict(self.parts[0]['files'][0])); self.seal()
        with self.assertRaises(ContractError): self.replay()
        self.parts[0]['files'].pop()
        self.parts[0]['files'][0]['provider_path'] = self.parts[1]['files'][0]['provider_path']; self.seal()
        with self.assertRaises(ContractError): self.replay()

    def test_wrong_anchor_missing_original_and_hash_mismatch_fail(self):
        with self.assertRaises(ContractError): audit.replay(self.manifest, '0'*64, self.root)
        path = self.root / self.parts[0]['files'][0]['path']; raw = path.read_bytes()
        path.unlink()
        with self.assertRaises(ContractError): self.replay()
        path.write_bytes(b'!' + raw[1:])
        with patch.object(self.pq, 'ParquetFile', side_effect=AssertionError('must not decode')):
            with self.assertRaises(ContractError): self.replay()

    def test_traversal_and_unlisted_fields_rejected(self):
        self.parts[0]['files'][0]['path'] = '../outside.parquet'; self.seal()
        with self.assertRaises(ContractError): self.replay()
        self.parts[0]['files'][0]['path'] = self.parts[0]['files'][0]['provider_path']
        self.parts[0]['extra'] = True; self.seal()
        with self.assertRaises(ContractError): self.replay()

    def test_empty_union_is_null_and_row_budget_fails(self):
        self.assertIsNone(audit.pair_counts(set(), set())['jaccard'])
        with patch.object(audit, 'MAX_ROWS', 3), self.assertRaises(ContractError): self.replay()


if __name__ == '__main__': unittest.main()
