"""Actual-format Arrow fixtures for source-bound three-view qualification."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, fingerprint
from tools.science.research_parquet import stream_rows
from tools.science.research_views import ProjectedBatch, build_views
from tests import test_research_views as view_fixtures


class ResearchParquetTests(unittest.TestCase):
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixture = view_fixtures.ResearchViewTests(); fixture.setUp()
        self.frame = fixture.frame
        rows = [fixture.row(identity=f'row-{i}')['values'] for i in range(5)]
        rows[0]['targetId'] = 'outside'
        rows[2]['diseaseId'] = 'outside'
        rows[3]['targetId'] = 'outside'
        for row in rows: row.update(clinicalPhase=4, stoppedReason='fictional excluded column', score=1.0)
        rows[0]['publicationYear'] = 2026  # Unmatched row receives no scientific QC verdict.
        for row in rows[1:]: row['publicationYear'] = None
        self.original_rows = rows
        self.path = self.root/'source.parquet'
        pq.write_table(pa.Table.from_pylist(rows), self.path, row_group_size=3)
        self.descriptors = [dict(artifact_id='new', path=str(self.path), bytes=self.path.stat().st_size,
                                 sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())]
        self.frame['sources'][1]['sha256'] = self.descriptors[0]['sha256']

    def rows(self, **kwargs):
        return stream_rows(self.descriptors, self.frame['hypotheses'],
                           expected_descriptors_sha256=fingerprint(self.descriptors),
                           source_roots=(self.root,), batch_rows=2, **kwargs)

    def test_filter_before_conversion_preserves_original_groups_and_offsets(self):
        stats = {}
        batches = list(self.rows(stats=stats))
        selected = [row for batch in batches for row in batch.selected]
        self.assertEqual([(r['row_group'], r['row_index']) for r in selected], [(0, 1), (1, 1)])
        self.assertEqual(stats['physical_rows'], 5)
        self.assertEqual(stats['python_rows'], 2)
        self.assertEqual(stats['outside_candidate_mask'], 3)
        self.assertEqual(stats['status'], 'completed')
        self.assertFalse({'score', 'clinicalPhase', 'stoppedReason'} & set(selected[0]['values']))

    def test_streamed_batches_reconcile_three_view_coverage(self):
        result = build_views(self.frame, self.rows(), expected_frame_sha256=fingerprint(self.frame))
        coverage = result['views']['current_unfiltered']['coverage']
        self.assertEqual(coverage['physical_rows'], 5)
        self.assertEqual(coverage['selected_rows'], 2)
        self.assertEqual(coverage['outside_case_universe'], 3)
        self.assertEqual(coverage['accepted_rows'], 2)

    def test_unauthorized_path_and_wrong_descriptor_anchor_fail_before_read(self):
        with self.assertRaisesRegex(ContractError, 'anchor'):
            list(stream_rows(self.descriptors, self.frame['hypotheses'], expected_descriptors_sha256='0'*64,
                             source_roots=(self.root,)))
        self.descriptors[0]['path'] = str(self.root.parent/'unapproved.parquet')
        with self.assertRaisesRegex(ContractError, 'source-root'): list(self.rows())

    def test_wrong_source_hash_precedes_any_parquet_parse(self):
        self.descriptors[0]['sha256'] = '0'*64
        with patch('pyarrow.parquet.ParquetFile', side_effect=AssertionError('unverified parse')):
            with self.assertRaisesRegex(ContractError, 'payload hash'): list(self.rows())

    def test_file_growth_and_total_byte_budget_fail_before_payload_read(self):
        with self.assertRaisesRegex(ContractError, 'byte budget'): list(self.rows(max_bytes=1))
        with self.path.open('ab') as f: f.write(b'changed')
        with patch('tether_engine.source_access.SourceFiles.read', side_effect=AssertionError('oversized read')):
            with self.assertRaisesRegex(ContractError, 'size differs'): list(self.rows())

    def test_missing_identifier_schema_fails_explicitly(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(pa.table({'unrelated': [1]}), self.path)
        self.descriptors[0].update(bytes=self.path.stat().st_size,
                                   sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ContractError, 'columns are missing'): list(self.rows())

    def test_consumer_interruption_never_reports_complete(self):
        stats = {}; stream = self.rows(stats=stats)
        next(stream); stream.close()
        self.assertEqual(stats['status'], 'failed_or_interrupted')
        self.assertEqual(stats['error_class'], 'GeneratorExit')

    def test_batch_overlap_and_out_of_range_offsets_fail(self):
        batches = list(self.rows())
        with self.assertRaisesRegex(ContractError, 'Overlapping'):
            build_views(self.frame, [batches[0], batches[0]], expected_frame_sha256=fingerprint(self.frame))
        row = dict(batches[0].selected[0]); row['row_index'] = 999
        invalid = ProjectedBatch('new', 0, 0, 2, (row,), self.descriptors[0]['sha256'])
        with self.assertRaisesRegex(ContractError, 'locator'):
            build_views(self.frame, [invalid], expected_frame_sha256=fingerprint(self.frame))

    def test_physical_row_budget_counts_python_omitted_rows(self):
        self.frame['max_rows'] = 4
        with self.assertRaisesRegex(ContractError, 'row budget'):
            build_views(self.frame, self.rows(), expected_frame_sha256=fingerprint(self.frame))

    def test_forbidden_parent_prevents_source_iterator_dispatch(self):
        self.frame['sources'][2]['role'] = 'evaluation_only'
        with patch('tether_engine.source_access.SourceAccess.prepare', side_effect=AssertionError('unauthorized read')):
            with self.assertRaisesRegex(ContractError, 'Forbidden research ancestor'):
                build_views(self.frame, self.rows(), expected_frame_sha256=fingerprint(self.frame))

    def test_correctly_hashed_other_bytes_do_not_match_declared_frame_source(self):
        self.frame['sources'][1]['sha256'] = 'a'*64
        with self.assertRaisesRegex(ContractError, 'payload hash differs from frame'):
            build_views(self.frame, self.rows(), expected_frame_sha256=fingerprint(self.frame))

    def test_arrow_prefilter_and_full_python_stream_have_identical_reduction(self):
        rows = [dict(source_id='new', row_group=i//3, row_index=i%3, values=value)
                for i, value in enumerate(self.original_rows)]
        expected = build_views(self.frame, rows, expected_frame_sha256=fingerprint(self.frame))
        actual = build_views(self.frame, self.rows(), expected_frame_sha256=fingerprint(self.frame))
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
