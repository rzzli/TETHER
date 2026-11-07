"""Outer process-envelope boundaries with explicitly invented child records."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import encode
from experiments.litqa_comparison.run import inventory
from . import contracts as c, run, supervise
from . import test_run as fixtures, test_integration as integration


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ControllerTests('runTest')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root / 'data/wrapped'
        self.producer = self.root / 'producer'
        self.fp = self.fixture.new_frame(output=self.producer)
        self.calls = []

    def child(self, command, limits, root, *, returncode=0, marker=False, wall=.001, elapsed=.002):
        self.calls.append((command, limits))
        self.assertEqual(Path(root), self.root)
        self.assertNotIn('--job', command)
        self.assertNotIn('--worker', command)
        self.assertNotIn('--admission', command)
        if returncode == 0:
            self.producer.mkdir()
            c.write(self.producer / 'COMPLETE.json', dict(status='evidence_first_execution_complete', wall_seconds=wall))
            if marker: c.write(self.producer / 'FAILURE.json', dict(error_type='Invented failure'))
            c.write(self.producer / 'ROOT-RECEIPT.json', dict(kind='sc05_evidence_first_root_receipt_v1',
                status='evidence_first_execution_complete', frame_sha256=self.fp['sha256'], files=inventory(self.producer)))
        result = integration.process_result(returncode, b'invented stdout', b'', limits, elapsed)
        (root / 'stdout.bin').write_bytes(result.stdout)
        (root / 'stderr.bin').write_bytes(result.stderr)
        c.write(root / 'PROCESS.json', dict(returncode=returncode, supervision=result.supervision))
        return result

    def launch(self, child=None):
        with patch.object(run, 'contain_process_tree', return_value=object()), \
             patch.object(run, 'DeadlineWatchdog', fixtures.InertWatchdog), \
             patch.object(run.process_tools, 'supervised', side_effect=child or self.child):
            return supervise.launch(self.fp['path'], self.fp['sha256'], output=self.root)

    def test_completed_child_is_bound_to_outer_receipt_and_carried_clock(self):
        value = self.launch()
        self.assertEqual(set(value), {'root', 'receipt_sha256', 'controller'})
        self.assertEqual(value['root'], str(self.producer))
        self.assertEqual(value['controller']['root'], str(self.root))
        receipt = c.read(c.capture(self.root / 'RECEIPT.json')[0])
        self.assertEqual(encode(receipt['files']), encode(inventory(self.root, omit=('RECEIPT.json',))))
        self.assertEqual(receipt['files']['producer/ROOT-RECEIPT.json']['sha256'], value['receipt_sha256'])
        config = c.read(c.capture(self.root / 'CONFIG.json')[0])
        self.assertEqual(self.calls[0][1].timeout_seconds,
            int(config['outer_seconds'] - config['preflight_seconds'] - 60))
        self.assertEqual([event['event'] for event in read_chain(self.root / 'journal.jsonl')],
                         ['build_reserved', 'evidence_first_controller_reserved', 'evidence_first_controller_completed'])

    def test_failed_child_is_retained_and_never_retried(self):
        with self.assertRaisesRegex(ValueError, 'Controller failed'):
            self.launch(lambda *args: self.child(*args, returncode=7))
        self.assertTrue((self.root / 'PROCESS.json').exists())
        self.assertTrue((self.root / 'FAILURE.json').exists())
        self.assertFalse((self.root / 'RECEIPT.json').exists())
        with self.assertRaises(ValueError): self.launch()
        self.assertEqual(len(self.calls), 1)

    def test_failure_marker_wins_over_zero_exit(self):
        with self.assertRaisesRegex(ValueError, 'failure marker'):
            self.launch(lambda *args: self.child(*args, marker=True))
        self.assertFalse((self.root / 'RECEIPT.json').exists())

    def test_child_cannot_report_more_time_than_its_process(self):
        with self.assertRaisesRegex(ValueError, 'process lifetime'):
            self.launch(lambda *args: self.child(*args, wall=1, elapsed=.002))
        self.assertTrue((self.root / 'FAILURE.json').exists())

    def test_interrupt_preserves_failure_without_completion(self):
        def interrupted(*args): raise KeyboardInterrupt('invented interrupted child')
        with self.assertRaises(KeyboardInterrupt): self.launch(interrupted)
        self.assertEqual(c.read(c.capture(self.root / 'FAILURE.json')[0])['error_type'], 'KeyboardInterrupt')
        self.assertFalse((self.root / 'COMPLETE.json').exists())

    def test_receipt_write_failure_dominates_prior_terminal(self):
        write = run.write
        def failed(path, value):
            if path == self.root / 'RECEIPT.json': raise OSError('invented final write failure')
            return write(path, value)
        with patch.object(run, 'write', side_effect=failed), self.assertRaisesRegex(OSError, 'final write'):
            self.launch()
        self.assertTrue((self.root / 'COMPLETE.json').exists())
        self.assertTrue((self.root / 'FAILURE.json').exists())
        self.assertFalse((self.root / 'RECEIPT.json').exists())

    def test_wrong_producer_location_fails_before_output_reservation(self):
        self.fp = self.fixture.new_frame(output=self.fixture.root / 'data/elsewhere')
        with self.assertRaisesRegex(ValueError, 'nested producer'): self.launch()
        self.assertFalse(self.root.exists())
        self.assertEqual(self.calls, [])

    def test_protected_plan_overlap_fails_before_any_outer_write(self):
        protected = Path(self.fixture.anchor['path']).parent
        self.root = protected / 'new-wrapper'
        self.producer = self.root / 'producer'
        self.fp = self.fixture.new_frame(output=self.producer)
        before = inventory(protected)
        with self.assertRaisesRegex(ValueError, 'overlaps immutable inputs'):
            self.launch()
        self.assertFalse(self.root.exists())
        self.assertEqual(self.calls, [])
        self.assertEqual(inventory(protected), before)


if __name__ == '__main__':
    unittest.main()
