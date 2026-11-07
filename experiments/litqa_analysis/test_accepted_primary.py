"""Byte-only adoption controls using one genuinely reconstructed invented run.

The original pipeline, sources, native answers and independent reconstruction are
real fixture formats. All data/model responses and supervision are fictional; no
model, network, archived code or reference-key access is permitted by the loader.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from . import accepted_primary as a, envelopes as e, reconstruct_run as r
from .invented_run_fixtures import InventedRuns, chain, write


class AcceptedPrimaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = InventedRuns()
        cls.addClassCleanup(cls.fixture.close)
        cls.original = e.load(cls.fixture.primary_path / 'FRAME.json')
        cls.producer = cls.archive('producer-archive', cls.original['code_pins'])
        # This is the only full independent semantic reconstruction in this suite.
        cls.report = r.reconstruct(cls.fixture.primary_path, cls.fixture.primary_sha, source_archive=cls.producer)
        cls.replay = cls.fixture.root / 'accepted-replay'
        cls.replay.mkdir()
        (cls.replay / 'worker').mkdir()
        runner = cls.fixture.root / 'fictional-replay-runner.py'
        runner.write_text('# Fictional wrapper metadata; this file is never executed.\n', encoding='utf-8')
        names = ('experiments/litqa_analysis/reconstruct_run.py', 'experiments/litqa_analysis/envelopes.py',
                 'experiments/litqa_analysis/native_records.py', 'experiments/litqa_analysis/source_archive.py')
        code = {name: e.proof(e.REPO / name) for name in names}
        cls.analyzer = cls.archive('analyzer-archive', {n: p['sha256'] for n, p in code.items()})
        cls.frame = dict(kind='sc04_primary_independent_replay_v1', primary_root=str(cls.fixture.primary_path),
            primary_root_sha256=cls.fixture.primary_sha, archive=cls.producer, runner=e.proof(runner),
            code_proofs=code, environment=dict(executable=e.proof(sys.executable)), seconds=1800,
            automatic_retry=False, scientific_scoring=False, new_http_calls=0, new_model_calls=0)
        write(cls.replay / 'FRAME.json', cls.frame)
        write(cls.replay / 'worker/RECONSTRUCTION.json', cls.report)
        write(cls.replay / 'worker/RESOURCES.json', dict(wall_seconds=.01, process={}, new_model_calls=0,
                                                       new_http_calls=0, scientific_scoring=False))
        cls.seal()
        cls.baseline = {p: p.read_bytes() for p in cls.replay.rglob('*') if p.is_file()}

    @classmethod
    def archive(cls, folder, pins):
        root = cls.fixture.root / folder
        root.mkdir()
        files = {}
        for index, name in enumerate(pins):
            path = root / f'{index:04d}.py'
            path.write_bytes((e.REPO / name).read_bytes())
            files[name] = e.proof(path)
        path = root / 'MANIFEST.json'
        write(path, dict(schema_version=1, kind='sc04_executed_source_archive_v1',
                        original_repository_root=str(e.REPO), files=files))
        return dict(path=str(path), sha256=e.proof(path)['sha256'])

    @classmethod
    def seal(cls):
        frame_sha = e.proof(cls.replay / 'FRAME.json')['sha256']
        frame = e.load(cls.replay / 'FRAME.json')
        chain(cls.replay / 'worker/journal.jsonl', [
            ('analysis_reserved', dict(owner_pid=42, created_at_utc='2026-11-07T00:00:00+00:00')),
            ('source_inclusive_reconstruction_started', dict(primary_root_sha256=frame['primary_root_sha256'])),
            ('source_inclusive_reconstruction_complete', dict(questions=2, records=8))])
        write(cls.replay / 'worker/RECEIPT.json', dict(status='complete', frame_sha256=frame_sha,
              files=e.inventory(cls.replay / 'worker', omit=('RECEIPT.json',))))
        worker = e.proof(cls.replay / 'worker/RECEIPT.json')
        write(cls.replay / 'stdout.log', dict(status='complete', receipt=worker))
        (cls.replay / 'stderr.log').write_bytes(b'')
        limits = dict(timeout_seconds=1800, max_output_bytes=4 * 1024 ** 2)
        write(cls.replay / 'COMMAND.json', dict(argv=[frame['environment']['executable']['path'], '-I', '-B',
            frame['runner']['path'], 'worker', str(cls.replay / 'FRAME.json'), frame_sha], limits=limits))
        size = (cls.replay / 'stdout.log').stat().st_size
        write(cls.replay / 'SUPERVISION.json', dict(schema_version=1, method='fictional_supervision',
            limits=limits, process_started=True, process_reaped=True, termination_reason='exited',
            cleanup_errors=[], observed_counts_are_lower_bounds=False, pipe_eof=dict(stdout=True, stderr=True),
            observed_stdout_bytes=size, retained_stdout_bytes=size, observed_stderr_bytes=0,
            retained_stderr_bytes=0, execution_elapsed_seconds=.02, total_elapsed_seconds=.02))
        chain(cls.replay / 'journal.jsonl', [
            ('analysis_reserved', dict(owner_pid=41, created_at_utc='2026-11-07T00:00:00+00:00')),
            ('worker_dispatch', dict(frame_sha256=frame_sha)), ('worker_accepted', dict(receipt=worker))])
        write(cls.replay / 'RECEIPT.json', dict(status='complete', files=e.inventory(cls.replay, omit=('RECEIPT.json',))))
        cls.sha = e.proof(cls.replay / 'RECEIPT.json')['sha256']

    def tearDown(self):
        for path in self.replay.rglob('*'):
            if path.is_file() and path not in self.baseline:
                path.unlink()
        for path, raw in self.baseline.items():
            path.write_bytes(raw)
        type(self).sha = e.proof(self.replay / 'RECEIPT.json')['sha256']

    @contextmanager
    def changed(self, path, raw):
        path = Path(path)
        original = path.read_bytes()
        path.write_bytes(raw)
        try:
            yield
        finally:
            path.write_bytes(original)

    def adopted(self, *, archive=None, sha=None):
        with patch.object(r, 'reconstruct', side_effect=AssertionError('No semantic rerun')), \
             patch.object(e, 'verify_run', side_effect=AssertionError('No current-interpreter envelope rerun')), \
             patch.object(socket, 'create_connection', side_effect=AssertionError('No network')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('No process')):
            return a.load(self.replay, sha or self.sha, analyzer_archive=archive or self.analyzer)

    def test_preserves_report_and_explicitly_limits_adoption_scope(self):
        result = self.adopted()
        self.assertEqual(result['status'], a.STATUS)
        self.assertEqual(result['report'], self.report)
        self.assertEqual(result['adoption']['questions'], 2)
        self.assertEqual(result['adoption']['answer_records'], 8)
        self.assertFalse(result['adoption']['semantic_reconstruction_recomputed'])
        self.assertFalse(result['adoption']['archived_code_executed'])
        self.assertFalse(result['adoption']['scientific_correctness_scored'])

    def test_external_replay_receipt_is_required(self):
        with self.assertRaises(ValueError):
            self.adopted(sha='0' * 64)

    def test_original_raw_or_native_answer_mutation_invalidates_adoption(self):
        manifest_path = next((self.fixture.primary_path / 'collect/worker/phase').rglob('MANIFEST.json'))
        request = next(row for row in e.load(manifest_path)['requests'] if row['transport_status'] == 'captured')
        raw = manifest_path.parent / request['body_path']
        native = next((self.fixture.primary_path / 'answer/worker/phase').rglob('native-response.bin'))
        terminal = native.parent / 'result.json'
        for path in (raw, native, terminal):
            with self.subTest(path=path.name), self.changed(path, path.read_bytes() + b'changed'), self.assertRaises(ValueError):
                self.adopted()

    def test_external_query_and_model_metadata_changes_are_rejected(self):
        for proof in (self.original['query_products']['answer_queries'], self.original['model_receipt']):
            path = Path(proof['path'])
            with self.subTest(path=path.name), self.changed(path, path.read_bytes() + b' '), self.assertRaises(ValueError):
                self.adopted()

    def test_archived_producer_or_analyzer_source_change_is_rejected(self):
        for descriptor in (self.producer, self.analyzer):
            value = e.load(descriptor['path'])
            path = Path(next(iter(value['files'].values()))['path'])
            with self.subTest(archive=path.parent.name), self.changed(path, path.read_bytes() + b'\n'), self.assertRaises(ValueError):
                self.adopted()

    def test_missing_analyzer_pin_is_rejected_even_with_new_archive_anchor(self):
        path = Path(self.analyzer['path'])
        value = e.load(path)
        value['files'].pop(next(iter(value['files'])))
        with self.changed(path, e.canonical(value)):
            descriptor = dict(path=str(path), sha256=e.proof(path)['sha256'])
            with self.assertRaises(ValueError):
                self.adopted(archive=descriptor)

    def test_reordered_report_is_rejected_after_internal_reseal(self):
        value = deepcopy(self.report)
        value['records']['L/O'].reverse()
        write(self.replay / 'worker/RECONSTRUCTION.json', value)
        self.seal()
        with self.assertRaises(ValueError):
            self.adopted()

    def test_wrong_primary_binding_is_rejected_after_internal_reseal(self):
        value = deepcopy(self.frame)
        value['primary_root_sha256'] = '0' * 64
        write(self.replay / 'FRAME.json', value)
        self.seal()
        with self.assertRaises(ValueError):
            self.adopted()

    def test_new_original_or_replay_files_are_not_ignored(self):
        for root in (self.fixture.primary_path, self.fixture.primary_path / 'answer', self.replay):
            path = root / 'UNDECLARED.txt'
            path.write_text('new unbound content', encoding='utf-8')
            try:
                with self.subTest(root=root.name), self.assertRaises(ValueError):
                    self.adopted()
            finally:
                path.unlink()

    def test_changed_report_without_new_external_anchor_is_rejected(self):
        path = self.replay / 'worker/RECONSTRUCTION.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.adopted()

    def test_extra_phase_or_replay_directories_are_rejected(self):
        for root in (self.fixture.primary_path / 'answer', self.replay):
            path = root / 'unknown-empty-directory'
            path.mkdir()
            try:
                with self.subTest(root=root.name), self.assertRaises(ValueError):
                    self.adopted()
            finally:
                path.rmdir()

    def test_hash_checked_bytes_are_used_for_report_parse(self):
        original = a.read
        target = str(self.replay / 'worker/RECONSTRUCTION.json')
        count = 0
        def transient(path, limit=32 * 1024 ** 2):
            nonlocal count
            raw = original(path, limit)
            if str(path) == target:
                count += 1
                if count == 2:
                    return raw + b' '
            return raw
        with patch.object(a, 'read', side_effect=transient), self.assertRaises(ValueError):
            self.adopted()


if __name__ == '__main__':
    unittest.main()
