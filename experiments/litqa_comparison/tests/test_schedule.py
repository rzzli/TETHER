import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import canonical,encode
from experiments.litqa_comparison import schedule as s


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'run';self.tick=0

    def stage(self,ids=('q1','q2'),kind='answer'):
        return s.Stage(ids,kind,self.root,seconds=100,clock=lambda:self.tick)

    def ok(self,slot,deadline):return dict(status='completed',reason=None,product=dict(fictional=slot['ordinal']))

    def test_full_199_stage_denominators(self):
        ids=[f'fictional-{i}' for i in range(199)]
        self.assertEqual({k:len(s.slots(ids,k)) for k in s.STAGES},
                         dict(expand=199,collect=398,rank=398,answer=796,supplied=199))
        self.assertEqual([x['branch'] for x in s.slots(ids,'answer')[:4]],list(s.ARMS))

    def test_complete_reconstructs_every_product(self):
        stage=self.stage()
        for _ in range(8):stage.call(self.ok)
        report=stage.finish();self.assertEqual(report['status'],'complete')
        check=s.verify(self.root,s.digest((self.root/'STAGE-RECEIPT.json').read_bytes()))
        self.assertEqual(check['rows'],report['rows'])

    def test_failure_preserves_all_unexecuted_slots_and_prevents_retry(self):
        stage=self.stage();stage.call(self.ok);calls=[]
        def fail(slot,deadline):calls.append(slot['ordinal']);raise TimeoutError('fictional')
        with self.assertRaises(TimeoutError):stage.call(fail)
        with self.assertRaises(ValueError):stage.call(fail)
        report=stage.finish()
        self.assertEqual(report['scheduled'],8);self.assertEqual(report['unexecuted'],6)
        self.assertEqual(calls,[1]);self.assertEqual(report['status'],'partial')
        self.assertEqual(s.inspect(self.root)['rows'][1]['status'],'failed')

    def test_interruption_is_not_an_automatic_retry(self):
        stage=self.stage()
        def interrupt(slot,deadline):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):stage.call(interrupt)
        report=stage.finish();self.assertEqual(report['rows'][0]['status'],'interrupted')
        self.assertEqual(s.inspect(self.root)['rows'][0]['status'],'interrupted')

    def test_deadline_before_dispatch_leaves_unexecuted(self):
        stage=self.stage();self.tick=101
        with self.assertRaises(ValueError):stage.call(self.ok)
        self.assertEqual(stage.finish()['entered'],0)

    def test_exact_directory_cannot_resume(self):
        stage=self.stage();stage.finish()
        with self.assertRaises(FileExistsError):self.stage()

    def test_uncertain_journal_recovery_never_infers_completion(self):
        stage=self.stage();stage.journal.append('slot_reserved',**stage.schedule[0]);stage.journal.close()
        result=s.inspect(self.root)
        self.assertFalse(result['finalized']);self.assertEqual(result['rows'][0]['status'],'uncertain')
        self.assertEqual(result['rows'][1]['status'],'unexecuted')

    def test_resealed_report_product_substitution_is_rejected(self):
        stage=self.stage(ids=('q1',),kind='expand');stage.call(self.ok);stage.finish()
        p=self.root/'REPORT.json';report=json.loads(p.read_bytes());report['rows'][0]['product']={'fictional':'changed'}
        p.write_bytes(canonical(report))
        j=self.root/'journal.jsonl';events=[json.loads(l) for l in j.read_bytes().splitlines()]
        events[-1]['details']['report_sha256']=s.digest(p.read_bytes())
        events[-1]['sha256']=s.digest(canonical({k:v for k,v in events[-1].items() if k!='sha256'}))
        j.write_bytes(b''.join(canonical(e)+b'\n' for e in events))
        with self.assertRaisesRegex(ValueError,'Report/journal states'):s.inspect(self.root)

    def test_extra_nested_receipt_not_hidden_from_inventory(self):
        stage=self.stage();stage.finish();(self.root/'extra').mkdir()
        (self.root/'extra/STAGE-RECEIPT.json').write_text('{}')
        with self.assertRaises(ValueError):s.verify(self.root,s.digest((self.root/'STAGE-RECEIPT.json').read_bytes()))

    def test_fallback_is_explicit_and_counted(self):
        stage=self.stage(ids=('q1',),kind='expand')
        stage.call(lambda slot,end:dict(status='fallback',reason='malformed expansion',product=dict(method='lexical',generation_entered=True)))
        report=stage.finish();self.assertEqual(report['status'],'complete')
        self.assertEqual(s.inspect(self.root)['rows'][0]['status'],'fallback')


if __name__=='__main__':unittest.main()
