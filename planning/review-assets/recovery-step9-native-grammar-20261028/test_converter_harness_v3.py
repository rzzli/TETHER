"""Focused operator-harness regressions. One harmless Python child, no llama code."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('author_converter_harness_v3',HERE/'run_finite_converter_probe_v3.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
OUT=ROOT/'data/cache'/('r09-converter-harness-v3-regressions-'+str(time.time_ns()))
OUT.mkdir(exist_ok=False)
guard=h.install_guards(dict(execution_claim=str(OUT/'unused-claim.json'),bridge=dict(path=sys.executable)),'execute',OUT)
observations={}


def fresh_state():
    return dict(dispatches=0,spawned_children=0,devnull_opens=0,denied=[],active_argv=None,active_cwd=None)


class HarnessV3Tests(unittest.TestCase):
    def test_01_exact_devnull_launch_reap_and_other_writes_rejected(self):
        root=OUT/'devnull';journal=h.RunJournal(root,kind='build')
        directory=root/'stage';directory.mkdir()
        argv=[sys.executable,'-I','-B','-c',"import sys; assert sys.stdin.buffer.read() == b''; sys.stdout.buffer.write(b'synthetic-devnull-ok\\n')"]
        stage=dict(mode='roundtrip',cwd=str(directory),argv=argv,input=dict(sha256='0'*64))
        try:record=h.run_child(stage,journal,guard,time.monotonic()+20)
        finally:journal.close()
        self.assertTrue(record['spawn_succeeded'] and record['reaped'])
        self.assertEqual(record['exit_code'],0)
        self.assertEqual((directory/'stdout.bin').read_bytes(),b'synthetic-devnull-ok\n')
        self.assertEqual((directory/'stderr.bin').read_bytes(),b'')
        self.assertEqual(guard['dispatches'],1);self.assertEqual(guard['spawned_children'],1)
        self.assertEqual(guard['devnull_opens'],1);self.assertEqual(guard['denied'],[])
        forbidden=OUT.parent/('never-create-'+OUT.name+'.txt')
        guard['active_argv'],guard['active_cwd']=argv,str(directory)
        try:
            with self.assertRaises(RuntimeError):os.open(forbidden,os.O_RDWR|os.O_CREAT)
            with self.assertRaises(RuntimeError):os.open(os.devnull,os.O_WRONLY)
            with self.assertRaises(RuntimeError):os.open(str(directory/'nul'),os.O_RDWR)
        finally:guard['active_argv']=guard['active_cwd']=None
        self.assertFalse(forbidden.exists())
        self.assertEqual(len(guard['denied']),3)
        observations['devnull']=dict(raw_os_devnull=os.devnull,normalized_os_devnull=h.normal(os.devnull),
            record=record,expected_rejected_writes=copy.deepcopy(guard['denied']))

    def test_02_inventory_overrun_before_receipt_fails_closed(self):
        root=OUT/'inventory-overrun';journal=h.RunJournal(root,kind='build')
        (root/'payload.txt').write_text('author-owned synthetic payload',encoding='ascii')
        started=time.monotonic();end=started+120;expired=False
        original_hash=h.hash_file;original_check=h.deadline_check
        def hash_with_overrun(path,deadline):
            nonlocal expired
            result=original_hash(path,deadline)
            if Path(path).name=='payload.txt':expired=True
            return result
        def check(deadline):
            if expired:raise TimeoutError('Synthetic inventory-hash overrun')
            return original_check(deadline)
        state=fresh_state()
        with patch.object(h,'hash_file',side_effect=hash_with_overrun),patch.object(h,'deadline_check',side_effect=check):
            with self.assertRaises(TimeoutError):h.finalize(root,journal,dict(status='synthetic_fixture'), '0'*64,[],state,started,end)
        self.assertFalse((root/'receipt.json').exists())
        failure=json.loads((root/'failure.json').read_bytes())
        self.assertTrue(failure['authoritative']);self.assertEqual(failure['phase'],'finalization')
        self.assertEqual(failure['status'],'failed_not_qualified')
        observations['inventory_overrun']=failure

    def test_03_post_receipt_overrun_keeps_receipt_but_failure_vetoes(self):
        root=OUT/'post-receipt-overrun';journal=h.RunJournal(root,kind='build')
        (root/'payload.txt').write_text('author-owned synthetic payload',encoding='ascii')
        started=time.monotonic();original_check=h.deadline_check;state=fresh_state()
        def check(deadline):
            if (root/'receipt.json').exists():raise TimeoutError('Synthetic post-receipt-write overrun')
            return original_check(deadline)
        with patch.object(h,'deadline_check',side_effect=check):
            with self.assertRaises(TimeoutError):h.finalize(root,journal,dict(status='synthetic_fixture'),'0'*64,[],state,started,started+120)
        self.assertTrue((root/'receipt.json').exists())
        self.assertFalse((root/'seal-state.json').exists())
        failure=json.loads((root/'failure.json').read_bytes())
        self.assertTrue(failure['authoritative'] and failure['receipt_present'])
        self.assertEqual(failure['status'],'failed_not_qualified')
        self.assertIn('overrides',failure['receipt_authority'])
        observations['post_receipt_overrun']=failure


suite=unittest.defaultTestLoader.loadTestsFromTestCase(HarnessV3Tests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
report=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',
    role='author_owned_synthetic_harness_regressions_not_native_observations',
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
    harmless_python_children=guard['spawned_children'],expected_harmless_python_children=1,
    actual_converter_children=0,llama_dlls_loaded=0,model_calls=0,servers=0,
    output=str(OUT),helper_sha256=h.sha(HERE/'run_finite_converter_probe_v3.py'),
    test_source_sha256=h.sha(__file__),observations=observations)
h.write_new(OUT/'regression-report.json',report)
print(json.dumps(dict(status=report['status'],tests=report['tests_run'],output=str(OUT),actual_converter_children=0)))
raise SystemExit(0 if result.wasSuccessful() else 1)
