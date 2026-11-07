"""Fictional worker/control qualification; no benchmark oracle or network."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from experiments.equal_policy import controls, independent, worker
from tests.test_equal_policy_independent import fixture, sealed_fixture, write_json


class WorkerControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / 'bundle'
        self.root.mkdir()
        case, snapshot = fixture(self.root)
        write_json(self.root / 'case.json', case)
        write_json(self.root / 'snapshot.json', snapshot)
        self.descriptor = dict(schema_version=1, control_id='worker-unit', operation='prepare_run',
            variant='core_v2_catalog1', paths=dict(case='case.json', snapshot='snapshot.json'), options={}, anchors={})
        write_json(self.root / 'descriptor.json', self.descriptor)

    def test_reject_all_is_explicit_and_not_equal_policy(self):
        result = controls.reject_all(self.root, self.descriptor)
        self.assertEqual(result['decision'], 'reject')
        self.assertEqual(result['observables'], {})
        self.assertIn('no policy', result['reason'])

    def test_hash_schema_accepts_temporally_invalid_case(self):
        case = independent.read_json(self.root / 'case.json')
        case['hypothesis']['availability']['annotation_public_at'] = '2026-01-01'
        write_json(self.root / 'case.json', case)
        self.assertEqual(controls.hash_schema(self.root, self.descriptor)['decision'], 'accept')
        self.assertEqual(independent.validate_bundle(self.root, self.descriptor)['decision'], 'reject')

    def test_hash_schema_detects_changed_packet_bytes(self):
        (self.root / 'evidence.json').write_text('{}', encoding='utf-8')
        self.assertEqual(controls.hash_schema(self.root, self.descriptor)['decision'], 'reject')

    def test_hash_schema_accepts_rehashed_accounting_error(self):
        run_dir, run, _, _ = sealed_fixture(self.root)
        run['calls'] = 77
        write_json(run_dir / 'run.json', run)
        receipt = independent.read_json(run_dir / 'receipt.json')
        receipt['outputs']['run.json'] = independent.file_digest(run_dir / 'run.json')
        write_json(run_dir / 'receipt.json', receipt)
        descriptor = self.descriptor | dict(operation='verify_run', paths=dict(run_dir='sealed'))
        self.assertEqual(controls.hash_schema(self.root, descriptor)['decision'], 'accept')
        self.assertEqual(independent.validate_bundle(self.root, descriptor)['decision'], 'reject')

    def test_inventory_is_logical_stat_bytes_not_read_traffic(self):
        result = worker.bundle_inventory(self.root)
        self.assertEqual(result['file_count'], 5)
        self.assertEqual(result['logical_file_bytes'], sum(path.stat().st_size for path in self.root.iterdir()))
        self.assertIsNone(result['open_read_bytes'])
        self.assertIsNone(result['physical_disk_bytes'])

    def test_network_and_oracle_audit_rejections_are_pure(self):
        for event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo'):
            with self.subTest(event=event), self.assertRaises(PermissionError):
                worker.forbid_network(event, ())
        for name in ('oracle.json', 'control_oracle.json', 'oracle-v1.json'):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                worker.forbid_network('open', (str(self.parent / name), 'r', 0))
        worker.forbid_network('open', (str(self.root / 'case.json'), 'r', 0))

    def test_invalid_validator_result_and_crash_are_errors(self):
        module = types.SimpleNamespace(__file__='fictional-unit-module')
        for validator in (lambda *a, **k: None, lambda *a, **k: (_ for _ in ()).throw(KeyError('bug'))):
            with self.subTest(validator=validator), patch.object(worker, '_implementation', return_value=(module, validator)):
                result = worker.run_worker('independent', self.root, self.descriptor, self.parent / 'scratch')
                self.assertEqual(result['result']['decision'], 'error')
                self.assertIsNotNone(result['metrics']['operation_wall_seconds'])

    def test_isolated_cli_emits_one_measured_result(self):
        path = Path(worker.__file__).resolve()
        result = subprocess.run([sys.executable, '-I', '-B', str(path), '--implementation', 'independent',
            '--root', str(self.root), '--descriptor', 'descriptor.json', '--scratch', str(self.parent / 'isolated-scratch')],
            capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        output = json.loads(result.stdout)
        self.assertEqual(output['result']['decision'], 'accept')
        self.assertTrue(output['runtime']['isolated'])
        self.assertFalse(output['runtime']['repository_product_source_on_path'])
        self.assertGreaterEqual(output['metrics']['operation_wall_seconds'], 0)
        self.assertGreater(output['metrics']['operation_traced_peak_bytes'], 0)
        self.assertGreater(output['metrics']['os_process_memory']['peak_bytes'], 0)

    def test_descriptor_guards_unknown_fields_and_types(self):
        changes = [dict(unexpected=True), dict(schema_version=True), dict(options={'review_enabled': 1}),
            dict(options={'process_limits': {'timeout_seconds': -1}}), dict(paths={'case': '../escape', 'snapshot': 'snapshot.json'}),
            dict(options={'budget': {'max_calls': True}}), dict(anchors={'receipt_sha256': 'not-a-hash'}),
            dict(options=[]), dict(anchors=[])]
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(independent.validate_bundle(self.root, self.descriptor | change)['decision'], 'reject')

    def test_only_optional_path_nulls_normalize_absent(self):
        request = deepcopy(self.descriptor)
        request['paths']['scorer'] = None
        self.assertEqual(independent.validate_bundle(self.root, request)['decision'], 'accept')
        for change in ({'options': None}, {'anchors': None}, {'options': {'review_enabled': None}}, {'options': {'budget': None}}):
            with self.subTest(change=change):
                self.assertEqual(independent.validate_bundle(self.root, request | change)['decision'], 'reject')


if __name__ == '__main__':
    unittest.main()
