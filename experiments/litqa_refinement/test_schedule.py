from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,encode,parse_json
from experiments.litqa_refinement import schedule as s

IDS=('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002')


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'stage'

    def stage(self,phase='pair_prepare',**kwargs):
        return s.Stage(IDS,phase,self.root,purpose='fictional_qualification',seconds=60,**kwargs)

    def operation(self,slot,end):
        self.assertTrue((self.root/'journal.jsonl').exists())
        self.assertEqual(s.read_chain(self.root/'journal.jsonl')[-1]['event'],'refinement_slot_reserved')
        return dict(status='completed',reason=None,product=dict(id=slot['id']),accounting=s.zero_accounting())

    def verify(self):
        raw=(self.root/'STAGE-RECEIPT.json').read_bytes()
        return s.verify(self.root,s.contracts.codecs.digest(raw),expected_ids=IDS,expected_phase='pair_prepare',purpose='fictional_qualification')

    def test_exclusive_full_schedule_receipt_and_zero_new_work(self):
        stage=self.stage()
        for _ in IDS:stage.call(self.operation)
        report=stage.finish();self.assertEqual(report['status'],'complete')
        self.assertEqual((report['scheduled'],report['entered'],report['unexecuted']),(2,2,0))
        self.assertEqual(report,self.verify()['report'])
        self.assertEqual(report['accounting']['known_totals']['generation_calls'],0)
        self.assertEqual(len({row['execution_id'] for row in report['rows']}),2)
        with self.assertRaises(FileExistsError):self.stage()

    def test_failure_keeps_remaining_rows_and_uncertain_reservation(self):
        stage=self.stage()
        def broken(slot,end):raise TimeoutError('fictional operation timeout')
        with self.assertRaises(TimeoutError):stage.call(broken)
        with self.assertRaises(ValueError):stage.call(self.operation)
        report=stage.finish();self.assertEqual(report,self.verify()['report'])
        self.assertEqual([r['status'] for r in report['rows']],['failed','unexecuted'])
        self.assertEqual(report['accounting']['uncertain_cells'],(IDS[0],))
        self.assertFalse(report['accounting']['measurements_complete'])
        self.assertIsNone(report['rows'][0]['accounting'])

    def test_interruption_is_not_ordinary_unavailable(self):
        stage=self.stage()
        with self.assertRaises(KeyboardInterrupt):stage.call(lambda *args:(_ for _ in ()).throw(KeyboardInterrupt()))
        report=stage.finish();self.assertEqual(report['rows'][0]['status'],'interrupted')
        self.assertEqual(self.verify()['report']['status'],'incomplete')

    def test_unknown_status_and_excessive_budget_stop(self):
        stage=self.stage()
        bad=dict(status='unavailable',reason='invented',product={},accounting=s.zero_accounting())
        with self.assertRaises(ValueError):stage.call(lambda *args:bad)
        stage.finish();self.assertEqual(self.verify()['report']['status'],'incomplete')
        usage=encode(s.zero_accounting());usage.update(generation_calls=1,reserved_input_tokens=10,reserved_output_tokens=256)
        with self.assertRaises(ValueError):s.accounting(usage,'pair_prepare')

    def test_completed_model_status_cannot_claim_zero_generation(self):
        stage=self.stage('critic')
        self.addCleanup(stage.journal.close)
        with self.assertRaisesRegex(ValueError,'generation'):
            stage.call(lambda *args:dict(status='completed',reason=None,product={},accounting=s.zero_accounting()))
        stage.finish()
        usage=encode(s.zero_accounting());usage['source_http_requests']=1
        with self.assertRaises(ValueError):s.accounting(usage,'refinement_collect',status='unavailable')
        with self.assertRaises(ValueError):s.accounting(s.zero_accounting(),'refinement_collect',status='completed')

    def test_all199_membership_and_phase_specific_caps(self):
        ids=tuple(f'00000000-0000-0000-0000-{i:012d}' for i in range(1,200))
        slots=s.slots(ids,'refinement_collect',purpose='production',execution_namespace='11111111-1111-1111-1111-111111111111')
        self.assertEqual(len(slots),199);self.assertEqual(s.limits('refinement_collect')['source_http_requests'],5)
        with self.assertRaises(ValueError):s.slots(ids[:-1],'critic',purpose='production',execution_namespace='11111111-1111-1111-1111-111111111111')
        with self.assertRaises(ValueError):s.slots(IDS,'answer',purpose='fictional_qualification',execution_namespace='11111111-1111-1111-1111-111111111111')

    def test_concurrent_output_has_one_owner(self):
        def attempt(_):
            try:return self.stage()
            except FileExistsError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
        winners=[x for x in results if x is not None];self.assertEqual(len(winners),1);winners[0].finish()

    def test_changed_row_or_extra_output_rejected(self):
        stage=self.stage()
        for _ in IDS:stage.call(self.operation)
        stage.finish();path=self.root/'slots/0000.json';old=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaises(ValueError):self.verify()
        path.write_bytes(old);(self.root/'extra').write_bytes(b'extra')
        with self.assertRaises(ValueError):self.verify()

    def test_write_failure_and_expired_stage_are_retained(self):
        stage=self.stage();real=s.publish_bytes;failed=False
        def one_failure(path,raw):
            nonlocal failed
            if 'slots' in path.parts and not failed:failed=True;raise OSError('fictional write failure')
            return real(path,raw)
        with patch.object(s,'publish_bytes',side_effect=one_failure),self.assertRaises(OSError):stage.call(self.operation)
        report=stage.finish();self.assertEqual(report['status'],'incomplete');self.verify()


if __name__=='__main__':unittest.main()
