"""Invented current-format controls; no actual model captures or dispatch."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import os
import shutil
import tempfile
import unittest

from experiments.litqa_analysis import envelopes as e

from experiments.litqa_analysis.invented_run_fixtures import InventedRuns


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(e.canonical(value))


def chain(path, values):
    previous = None
    output = []
    for i, (event, details) in enumerate(values):
        value = dict(sequence=i, previous_sha256=previous, event=event, details=details)
        previous = e.digest(e.canonical(value))
        output.append(dict(**value, sha256=previous))
    path.write_bytes(b''.join(e.canonical(v) + b'\n' for v in output))


class EnvelopeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = InventedRuns()
        cls.addClassCleanup(cls.fixtures.close)

    def setUp(self):
        parent = e.REPO / 'data/cache/sc04-envelope-tests'
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def synthetic_stage(self, *, change=None, extra_event=False):
        root = self.root / 'worker/phase'
        identity = dict(ordinal=0, id='invented', branch='shared')
        row = dict(**identity, status='completed', reason=None, product={'invented': True})
        config = dict(kind='sc04_stage_v1', stage='expand', ids=['invented'], schedule=[identity], seconds=100)
        report = dict(status='complete', scheduled=1, entered=1, unexecuted=0, rows=[row], wall_seconds=1)
        if change:
            change(config, report, row)
        write(root / 'CONFIG.json', config)
        write(root / 'REPORT.json', report)
        write(root / 'slots/0000.json', row)
        events = [('build_reserved', {}), ('stage_configured', dict(config_sha256=e.digest(e.raw(root / 'CONFIG.json')))),
                  ('slot_reserved', identity), ('slot_terminal', dict(ordinal=0, slot_sha256=e.digest(e.raw(root / 'slots/0000.json')),
                                                                     path='slots/0000.json', status=row['status'])),
                  ('stage_finalized', dict(status=report['status'], report_sha256=e.digest(e.raw(root / 'REPORT.json'))))]
        if extra_event:
            events.append(('ignored_claim', {}))
        chain(root / 'journal.jsonl', events)
        inv = e.inventory(self.root)
        write(root / 'STAGE-RECEIPT.json', dict(status='complete', files={k[len('worker/phase/'):]: dict(bytes=v['bytes'], sha256=v['sha256'])
                                                                      for k, v in inv.items()}))
        inv = e.inventory(self.root)
        return root, e.proof(root / 'STAGE-RECEIPT.json')['sha256'], inv

    def verify_stage(self, values):
        root, sha, inv = values
        return e._stage(root, sha, ['invented'], ('shared',), 'expand', inv)

    def test_complete_invented_schedule(self):
        self.assertEqual(len(self.verify_stage(self.synthetic_stage())), 1)

    def test_resealed_incomplete_accounting_rejected(self):
        values = self.synthetic_stage(change=lambda c, r, s: r.update(entered=0, unexecuted=1))
        with self.assertRaisesRegex(ValueError, 'Incomplete stage accounting'):
            self.verify_stage(values)

    def test_resealed_extra_journal_event_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Stage setup events'):
            self.verify_stage(self.synthetic_stage(extra_event=True))

    def test_resealed_wrong_task_schedule_rejected(self):
        values = self.synthetic_stage(change=lambda c, r, s: c.update(ids=['other']))
        with self.assertRaisesRegex(ValueError, 'Stage schedule'):
            self.verify_stage(values)

    def test_resealed_overtime_rejected(self):
        values = self.synthetic_stage(change=lambda c, r, s: r.update(wall_seconds=100))
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.verify_stage(values)

    def test_resealed_journal_slot_conflict_rejected(self):
        def corrupt(config, report, row):
            report['rows'] = [dict(row, reason='not in slot')]
        with self.assertRaisesRegex(ValueError, 'report/journal'):
            self.verify_stage(self.synthetic_stage(change=corrupt))

    def test_external_anchor_required(self):
        write(self.root / 'receipt.json', dict(status='complete'))
        with self.assertRaisesRegex(ValueError, 'External receipt'):
            e.anchored(self.root / 'receipt.json', '0' * 64)

    def test_traversal_rejected(self):
        for name in ('../outside', '/absolute', 'folder/../../outside', 'folder\\outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                e.child(self.root, name)

    def test_duplicate_json_rejected(self):
        (self.root / 'bad.json').write_bytes(b'{"status":1,"status":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            e.load(self.root / 'bad.json')

    def test_failed_http_is_unknown_not_zero(self):
        path = self.root / 'products/0000/MANIFEST.json'
        write(path, dict(requests=[dict(request_id='000', byte_reservation=100, transport_status='failed',
                                       measured_bytes=None, accounted_bytes=100, http_status=None)],
                         accounting=dict(measured_response_bytes=0, safety_accounted_bytes=100,
                                         unknown_transfer_upper_bytes=100, wire_bytes=None, retries=0, provider_cost_usd=0)))
        result = e._http_resources(self.root)
        self.assertEqual(result['failed_requests'], 1)
        self.assertEqual(result['unknown_transfer_upper_bytes'], 100)
        self.assertEqual(result['measured_response_bytes'], 0)

    def test_failed_http_zero_reservation_rejected(self):
        path = self.root / 'products/0000/MANIFEST.json'
        write(path, dict(requests=[dict(request_id='000', byte_reservation=100, transport_status='failed',
                                       measured_bytes=0, accounted_bytes=0, http_status=None)], accounting={}))
        with self.assertRaisesRegex(ValueError, 'uncertainty'):
            e._http_resources(self.root)

    def test_native_measured_corruption_rejected(self):
        destination = self.root / 'products/0000'
        shutil.copytree(self.fixtures.primary_path / 'expand/worker/phase/products/0000', destination)
        summary = e.load(destination / 'SUMMARY.json')
        summary['usage']['output_tokens'] += 1
        write(destination / 'SUMMARY.json', summary)
        with self.assertRaisesRegex(ValueError, 'Measured usage'):
            e._native_resources(self.root)

    def test_native_reservation_corruption_rejected(self):
        destination = self.root / 'products/0000'
        shutil.copytree(self.fixtures.primary_path / 'expand/worker/phase/products/0000', destination)
        summary = e.load(destination / 'SUMMARY.json')
        summary['reservation_input_tokens'] += 1
        write(destination / 'SUMMARY.json', summary)
        with self.assertRaisesRegex(ValueError, 'reservation mismatch'):
            e._native_resources(self.root)

    def test_native_capacity_has_no_measured_usage(self):
        write(self.root / 'products/0000/SUMMARY.json', dict(generation_entered=False, status='capacity', usage=None,
              reservation_input_tokens=0, reservation_output_tokens=0, provider_cost_usd=0))
        result, cells = e._native_resources(self.root)
        self.assertEqual(result['generation_calls'], 0)
        self.assertIsNone(cells[0]['usage'])

    def test_http_original_body_corruption_rejected(self):
        destination = self.root / 'products/0000'
        shutil.copytree(self.fixtures.supplied_path / 'collect/worker/phase/products/0000', destination)
        (destination / 'responses/000.body').write_bytes(b'changed original')
        with self.assertRaisesRegex(ValueError, 'HTTP measured bytes'):
            e._http_resources(self.root)

    def test_empty_package_inventory_no_hidden_files(self):
        (self.root / '.hidden').write_bytes(b'captured')
        self.assertEqual(set(e.inventory(self.root)), {'.hidden'})

    def test_owned_port_difference_does_not_change_producer(self):
        left = dict(host='127.0.0.1', port=55000, argv=['server', '--port', '55000', '--threads', '8'])
        right = dict(host='127.0.0.1', port=55001, argv=['server', '--port', '55001', '--threads', '8'])
        self.assertEqual(e.producer_spec(left), e.producer_spec(right))
        right['argv'][-1] = '4'
        self.assertNotEqual(e.producer_spec(left), e.producer_spec(right))

    def test_port_alias_conflict_rejected(self):
        with self.assertRaisesRegex(ValueError, 'port/command'):
            e.producer_spec(dict(host='127.0.0.1', port=55000, argv=['server', '--port', '55001']))

    def test_non_utc_chronology_rejected(self):
        for value in ('2026-11-06T00:00:00', '2026-11-06T00:00:00+03:00'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'UTC'):
                e.utc(value)

    def pair(self):
        # Invented metadata only; no actual captured run is read or relabelled.
        left = e.load(self.fixtures.primary_path / 'FRAME.json')
        right = e.load(self.fixtures.supplied_path / 'FRAME.json')
        left['purpose'] = right['purpose'] = 'production'
        write(self.root / 'invented-primary-frame.json', left)
        primary = dict(kind='primary', root=str(self.fixtures.primary_path), frame=left, root_sha256=self.fixtures.primary_sha,
                       frame_sha256=e.proof(self.root / 'invented-primary-frame.json')['sha256'],
                       complete=dict(source_cutoff=self.fixtures.cutoff.isoformat()))
        right['primary_frame'] = e.proof(self.root / 'invented-primary-frame.json')
        right['primary_execution'] = dict(root=str(self.fixtures.primary_path), receipt=e.proof(self.fixtures.primary_path / 'ROOT-RECEIPT.json'))
        right['created_at_utc'] = (self.fixtures.cutoff + timedelta(seconds=1)).isoformat()
        right['products']['answer_queries'] = left['query_products']['answer_queries']
        supplied = dict(kind='supplied', root=str(self.fixtures.supplied_path), frame=right, root_sha256=self.fixtures.supplied_sha,
                        complete=dict(source_cutoff=(self.fixtures.cutoff + timedelta(seconds=3)).isoformat()))
        return primary, supplied

    def test_pair_bindings_and_declared_order(self):
        self.assertEqual(e.verify_pair(*self.pair())['status'], 'verified')

    def test_pair_wrong_parent_anchor_rejected(self):
        left, right = self.pair()
        right['frame']['primary_execution']['receipt']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'different primary'):
            e.verify_pair(left, right)

    def test_pair_future_freeze_rejected(self):
        left, right = self.pair()
        right['frame']['created_at_utc'] = (self.fixtures.cutoff + timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError, 'chronology'):
            e.verify_pair(left, right)

    def test_pair_changed_generation_rejected(self):
        left, right = self.pair()
        right['frame']['generation_configuration']['temperature'] = 1.0
        with self.assertRaisesRegex(ValueError, 'configuration differs'):
            e.verify_pair(left, right)

    def audit(self, records):
        data = b''.join(e.canonical(r) + b'\n' for r in records)
        return e.audit_records(data, inputs=[self.root / 'source-query.json'], output=self.root / 'output',
                               code_roots=[self.root / 'code'])

    def event(self, path, *, allowed=True, basis='explicit_data_or_runtime', flags=os.O_RDONLY):
        return dict(path=str(self.root / path), allowed=allowed, basis=basis, flags=flags, mode='r')

    def test_role_specific_data_and_output_permissions(self):
        result = self.audit([self.event('source-query.json'), self.event('code/module.py'),
                             self.event('output/report.json', basis='output', flags=os.O_WRONLY | os.O_CREAT)])
        self.assertEqual((result['input_or_runtime_events'], result['output_events']), (2, 1))

    def test_answer_reference_cannot_masquerade_as_allowed_source(self):
        with self.assertRaisesRegex(ValueError, 'allowlist classification'):
            self.audit([self.event('reference-keys.json')])

    def test_writes_to_inputs_or_code_rejected(self):
        for path in ('source-query.json', 'code/module.py'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'allowlist classification'):
                self.audit([self.event(path, flags=os.O_RDWR)])

    def test_real_denial_cannot_be_hidden_by_complete_worker(self):
        with self.assertRaisesRegex(ValueError, 'Denied Python-open'):
            self.audit([self.event('reference-keys.json', allowed=False, basis='denied')])

    def test_existing_descriptor_scope_is_explicit(self):
        result = self.audit([dict(path=None, descriptor=5, allowed=True, basis='existing_descriptor', flags=os.O_RDONLY, mode='r')])
        self.assertEqual(result['existing_descriptor_events'], 1)

    def test_truncated_open_audit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete Python-open'):
            e.audit_records(e.canonical(self.event('source-query.json')), inputs=[], output=self.root/'output', code_roots=[])


class InventedRunQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = InventedRuns()
        cls.addClassCleanup(cls.fixtures.close)
        cls.primary = e.verify_run(cls.fixtures.primary_path, cls.fixtures.primary_sha, kind='primary')
        cls.supplied = e.verify_run(cls.fixtures.supplied_path, cls.fixtures.supplied_sha, kind='supplied')

    def test_primary_full_four_arm_schedule(self):
        self.assertEqual([r['branch'] for r in self.primary['phases']['answer']['rows']], list(e.ARMS) * 2)
        self.assertEqual(self.primary['resources']['physical_model']['generation_calls'], 14)

    def test_primary_native_usage_reconstructs(self):
        totals = self.primary['resources']['physical_model']
        self.assertEqual((totals['measured_input_tokens'], totals['measured_output_tokens']), (14 * 50, 14 * 12))
        self.assertGreater(totals['reserved_input_tokens'], totals['measured_input_tokens'])

    def test_supplied_separate_diagnostic_resources(self):
        totals = self.supplied['resources']['physical_model']
        self.assertEqual((totals['generation_calls'], totals['measured_input_tokens'], totals['measured_output_tokens']), (2, 2 * 50, 2 * 12))
        from experiments.litqa_supplied import qualification_fixtures as invented
        expected_bytes = sum(len(invented.fetch(url)['body']) for url in ('/search?fixture', '/article/fixture'))
        self.assertEqual(self.supplied['resources']['physical_http']['measured_response_bytes'], expected_bytes)
        self.assertEqual(self.supplied['kind'], 'supplied')

    def test_resource_and_scientific_limits_remain_explicit(self):
        for result in (self.primary, self.supplied):
            self.assertEqual(result['frame']['fixture_kind'], 'invented_no_inference_no_network_v1')
            self.assertEqual(result['frame']['real_model_calls'], 0)
            self.assertEqual(result['frame']['real_http_requests'], 0)
            self.assertIsNone(result['resources']['measured_gpu_memory_bytes'])
            self.assertIsNone(result['resources']['physical_http']['wire_bytes'])
            self.assertFalse(result['source_eligibility_reconstructed'])
            self.assertFalse(result['semantic_predictions_reconstructed'])

    def test_every_invented_phase_reconciles_its_io_audit(self):
        for run in (self.primary, self.supplied):
            for phase in run['resources']['phases'].values():
                self.assertGreater(phase['io_audit']['events'], 0)
                self.assertEqual(phase['io_audit']['denied_events'], 0)
                self.assertIn('Existing file descriptors remain opaque', phase['io_audit']['scope'])


if __name__ == '__main__':
    unittest.main()
