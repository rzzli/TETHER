"""Durable six-case/full199 barriers; invented outcomes and no inference."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from tether_engine.serde import canonical, encode
from . import stage as s

IDS = tuple(str(UUID(int=i + 1)) for i in range(6))


class StageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'stage'

    def stage(self, **kwargs):
        return s.Stage(IDS, 'repair', self.root, purpose='fictional_qualification', seconds=60, **kwargs)

    def operation(self, slot, end):
        self.assertEqual(s.read_chain(self.root / 'journal.jsonl')[-1]['event'], 'evidence_first_slot_reserved')
        return dict(status='capacity', reason='capacity', product=dict(id=slot['id']), accounting=s.zero_accounting())

    def verify(self):
        raw = (self.root / 'STAGE-RECEIPT.json').read_bytes()
        return s.verify(self.root, s.contracts.codecs.digest(raw), expected_ids=IDS,
                        expected_phase='repair', purpose='fictional_qualification')

    def complete(self):
        stage = self.stage()
        for _ in IDS: stage.call(self.operation)
        return stage.finish()

    def test_complete_all_scheduled_and_independent_byte_journal_agreement(self):
        report = self.complete()
        self.assertEqual(report, self.verify()['report'])
        self.assertEqual((report['scheduled'], report['entered'], report['unexecuted']), (6, 6, 0))
        self.assertEqual(report['accounting']['known_totals']['generation_calls'], 0)
        with self.assertRaises(FileExistsError): self.stage()

    def test_unknown_failure_stops_and_keeps_five_unexecuted(self):
        stage = self.stage()
        with self.assertRaises(TimeoutError):
            stage.call(lambda *args: (_ for _ in ()).throw(TimeoutError('invented timeout')))
        with self.assertRaises(ValueError): stage.call(self.operation)
        report = stage.finish()
        self.assertEqual(report, self.verify()['report'])
        self.assertEqual([r['status'] for r in report['rows']], ['failed'] + ['unexecuted'] * 5)
        self.assertEqual(report['accounting']['uncertain_cells'], (IDS[0],))
        self.assertFalse(report['accounting']['measurements_complete'])

    def test_interruption_cannot_be_promoted_to_capacity(self):
        stage = self.stage()
        with self.assertRaises(KeyboardInterrupt):
            stage.call(lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertEqual(stage.finish()['rows'][0]['status'], 'interrupted')
        self.assertEqual(self.verify()['report']['status'], 'incomplete')

    def test_completed_generation_cannot_claim_zero_generation_usage(self):
        stage = self.stage()
        with self.assertRaises(ValueError):
            stage.call(lambda *args: dict(status='completed', reason=None, product={}, accounting=s.zero_accounting()))
        stage.finish(); self.assertEqual(self.verify()['report']['status'], 'incomplete')

    def test_no_hidden_source_requests(self):
        usage = encode(s.zero_accounting()); usage['source_http_requests'] = 1
        with self.assertRaises(ValueError): s.accounting(usage, 'repair', status='capacity')

    def test_concurrent_output_has_one_owner(self):
        def attempt(_):
            try: return self.stage()
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(attempt, range(2)))
        winners = [x for x in results if x is not None]
        self.assertEqual(len(winners), 1); winners[0].finish()

    def test_semantic_accounting_tampering_even_after_receipt_reseal(self):
        self.complete()
        report = encode(self.verify()['report']); report['accounting']['known_totals']['generation_calls'] = 4
        (self.root / 'REPORT.json').write_bytes(canonical(report))
        receipt = s.parse_json((self.root / 'STAGE-RECEIPT.json').read_bytes())
        receipt['files']['REPORT.json'] = s.hash_file(self.root / 'REPORT.json', s.time.monotonic() + 30)
        (self.root / 'STAGE-RECEIPT.json').write_bytes(canonical(receipt))
        with self.assertRaises(ValueError): self.verify()

    def test_write_failure_retains_uncertain_slot(self):
        stage = self.stage(); real = s.publish_bytes; fired = False
        def failing(path, raw):
            nonlocal fired
            if 'slots' in path.parts and not fired:
                fired = True; raise OSError('invented write failure')
            return real(path, raw)
        with patch.object(s, 'publish_bytes', side_effect=failing), self.assertRaises(OSError):
            stage.call(self.operation)
        self.assertEqual(stage.finish()['status'], 'incomplete'); self.verify()

    def test_clock_expiry_cannot_advance_or_seal_success(self):
        tick = [10.0]; stage = self.stage(clock=lambda: tick[0])
        tick[0] = 71.0
        with self.assertRaises(ValueError): stage.call(self.operation)
        self.assertEqual(stage.finish()['status'], 'incomplete')


if __name__ == '__main__': unittest.main()
