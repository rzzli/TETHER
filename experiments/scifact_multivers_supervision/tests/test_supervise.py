"""Owned tiny-child controls only; no model imports, downloads or GPU work."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

from experiments.scifact_multivers_supervision.supervise import Events, ROOT, SupervisionError, pin, supervise


CHILD = '''import argparse,json,time,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--mode');a=p.parse_args()
if a.mode=='prestart_hang': time.sleep(10)
if a.mode=='import_failure': print('invented import failure',file=sys.stderr);sys.exit(17)
root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
f=(root/'events.jsonl').open('xb',buffering=0)
def event(kind,**kw):
    f.write((json.dumps(dict(event=kind,monotonic_seconds=time.monotonic(),**kw))+'\\n').encode())
event('started');event('model_load_started');event('models_loaded')
for cid in ('a','b','c'):
    if cid=='b' and a.mode=='partial_start':
        f.write(b'{"event":"case_started","case_id":"b"');time.sleep(10)
    event('case_started',case_id=cid)
    if cid=='b' and a.mode=='case_hang':time.sleep(10)
    time.sleep(.01)
    event('case_completed',case_id=cid)
    if cid=='a' and a.mode=='between_hang':time.sleep(10)
if a.mode!='missing_terminal':event('completed',status='passed')
f.close()
'''


class SupervisorTests(unittest.TestCase):
    def fixture(self, mode, process_seconds=1.2, case_seconds=.35):
        base = Path(os.environ['SUPERVISION_TEST_ROOT']) / self._testMethodName
        base.mkdir(parents=True, exist_ok=False)
        child = base/'child.py'
        child.write_text(CHILD, encoding='utf-8', newline='\n')
        launch, result = base/'launch', base/'result'
        supervisor = ROOT/'experiments/scifact_multivers_supervision/supervise.py'
        manifest = {'schema_version':1,'kind':'multivers_qualification_supervision',
                    'schedule':['a','b','c'],'limits':{'process_seconds':process_seconds,'case_seconds':case_seconds,'poll_seconds':.01},
                    'launch_output':str(launch),'qualification_output':str(result),'cwd':str(ROOT),
                    'command':[sys.executable,'-I','-B',str(child),'--mode',mode,'--output',str(result)],
                    'pins':[pin(sys.executable),pin(child),pin(supervisor)]}
        path = base/'MANIFEST.json'
        path.write_text(json.dumps(manifest,sort_keys=True)+'\n',encoding='utf-8')
        return path, hashlib.sha256(path.read_bytes()).hexdigest(), launch, result

    def run_mode(self, mode, **kwargs):
        manifest, digest, launch, child = self.fixture(mode, **kwargs)
        result = supervise(manifest,digest)
        self.assertEqual(json.loads((launch/'OUTCOME.json').read_text(encoding='utf-8')),result)
        self.assertTrue(result['all_frozen_pins_unchanged'])
        self.assertIsNotNone(result['exit_code'])
        return result

    def test_success_retains_three_cases_command_and_freeze(self):
        result = self.run_mode('success')
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['exit_code'],0)
        self.assertEqual([x['status'] for x in result['cases']],['completed']*3)

    def test_initial_import_or_setup_hang_is_inside_outer_deadline(self):
        result = self.run_mode('prestart_hang',process_seconds=.6,case_seconds=.25)
        self.assertEqual(result['status'],'timeout')
        self.assertEqual([x['status'] for x in result['cases']],['unexecuted']*3)
        self.assertLess(result['observed_child_phase_seconds'],3)

    def test_hang_between_cases_keeps_completed_and_unexecuted(self):
        result = self.run_mode('between_hang',process_seconds=.7,case_seconds=.25)
        self.assertEqual(result['status'],'timeout')
        self.assertEqual([x['status'] for x in result['cases']],['completed','unexecuted','unexecuted'])

    def test_active_case_has_independent_deadline(self):
        result = self.run_mode('case_hang',process_seconds=2,case_seconds=.25)
        self.assertEqual(result['status'],'timeout')
        self.assertEqual([x['status'] for x in result['cases']],['completed','timeout','unexecuted'])
        self.assertLess(result['observed_child_phase_seconds'],1.5)

    def test_import_failure_retains_stderr_and_never_creates_successful_nei(self):
        result = self.run_mode('import_failure')
        self.assertEqual(result['status'],'failure')
        self.assertEqual(result['exit_code'],17)
        self.assertEqual([x['status'] for x in result['cases']],['unexecuted']*3)

    def test_controller_interruption_stops_owned_child_and_retains_active_case(self):
        manifest,digest,launch,child = self.fixture('case_hang',process_seconds=2,case_seconds=1)
        def interrupted():
            events=child/'events.jsonl'
            return events.exists() and '"case_id": "b"' in events.read_text(encoding='utf-8')
        result=supervise(manifest,digest,interrupt_check=interrupted)
        self.assertEqual(result['status'],'interrupted')
        self.assertEqual([x['status'] for x in result['cases']],['completed','interrupted','unexecuted'])
        self.assertIsNotNone(result['exit_code'])

    def test_manifest_mismatch_fails_before_any_launch_output(self):
        manifest,digest,launch,child=self.fixture('success')
        with self.assertRaisesRegex(SupervisionError,'hash'):
            supervise(manifest,'0'*64)
        self.assertFalse(launch.exists());self.assertFalse(child.exists())

    def test_existing_launch_is_not_clobbered(self):
        manifest,digest,launch,child=self.fixture('success')
        launch.mkdir();(launch/'sentinel').write_bytes(b'keep')
        with self.assertRaises(SupervisionError):supervise(manifest,digest)
        self.assertEqual((launch/'sentinel').read_bytes(),b'keep')
        self.assertFalse(child.exists())

    def test_missing_terminal_is_failure_even_after_all_cases(self):
        result = self.run_mode('missing_terminal')
        self.assertEqual(result['status'],'failure')
        self.assertEqual([x['status'] for x in result['cases']],['completed']*3)

    def test_incomplete_start_line_is_retained_as_unknown(self):
        result = self.run_mode('partial_start',process_seconds=.6,case_seconds=.25)
        self.assertEqual(result['status'],'timeout')
        self.assertEqual([x['status'] for x in result['cases']],['completed','unknown_start','unexecuted'])
        self.assertGreater(result['partial_event_bytes'],0)

    def test_child_script_must_be_pinned(self):
        manifest,digest,launch,child=self.fixture('success')
        value=json.loads(manifest.read_text(encoding='utf-8'))
        value['pins']=[x for x in value['pins'] if not x['path'].endswith('child.py')]
        manifest.write_text(json.dumps(value)+'\n',encoding='utf-8')
        digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
        with self.assertRaisesRegex(SupervisionError,'entrypoint'):
            supervise(manifest,digest)
        self.assertFalse(launch.exists());self.assertFalse(child.exists())

    def test_late_case_completion_is_timeout_relevant_even_if_observed_together(self):
        events=Events(['a'],100,1)
        events.accept({'event':'case_started','case_id':'a','monotonic_seconds':101},101)
        with self.assertRaisesRegex(SupervisionError,'deadline'):
            events.accept({'event':'case_completed','case_id':'a','monotonic_seconds':102.1},102.1)
        self.assertEqual(events.active,'a');self.assertEqual(events.completed,[])

    def test_wrong_order_and_post_terminal_events_fail(self):
        events=Events(['a'],100,1)
        with self.assertRaises(SupervisionError):
            events.accept({'event':'case_started','case_id':'b','monotonic_seconds':100.1},100.1)
        events=Events(['a'],100,1)
        events.accept({'event':'case_started','case_id':'a','monotonic_seconds':100.1},100.1)
        events.accept({'event':'case_completed','case_id':'a','monotonic_seconds':100.2},100.2)
        events.accept({'event':'completed','status':'passed','monotonic_seconds':100.3},100.3)
        with self.assertRaises(SupervisionError):
            events.accept({'event':'completed','status':'passed','monotonic_seconds':100.4},100.4)


if __name__=='__main__':
    unittest.main(verbosity=2)
