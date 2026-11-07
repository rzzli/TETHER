"""Controller boundaries: metadata first, terminal failures, no redispatch."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
from tether._process import EngineDeadlineExceeded,EngineOutputLimitExceeded

from tether_engine.serde import canonical,encode,parse_json
from . import run as r


class ControllerTests(unittest.TestCase):
    def setUp(self):
        folder=r.ROOT/'data/cache/sc05-refinement-controller-controls';folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.output=self.root/'attempt'
        self.ids=['00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002']
        self.pins=[r.proof(r.__file__)]
        self.frame=dict(schema_version=1,kind=r.KIND,purpose='fictional_qualification',schedule=self.ids,
            baseline=dict(root=str(self.root/'baseline'),receipt_sha256='a'*64),interpreter=r.proof(sys.executable),
            code_files=self.pins,phase_seconds={p:600 for p in r.schedule.PHASES},port=55631,
            alias='tether-sc05-refinement-qwen14b-v1',model_receipt=dict(path=str(self.root/'acquisition.json'),bytes=1,sha256=r.MODEL_RECEIPT),
            model_license=dict(path=str(self.root/'LICENSE'),bytes=1,sha256='b'*64),model_spec={},model_provenance={},
            generation_configuration=encode(r.model.CONFIG),qualification=None,provider_spend_usd=0,
            automatic_retry=False,output=str(self.output))
        self.path=self.root/'FRAME.json'

    def load(self):
        self.path.write_bytes(canonical(self.frame))
        with patch.object(r,'code_files',return_value=self.pins):
            return r.load_frame(self.path,r.proof(self.path)['sha256'],self.output)

    def test_frame_loading_never_reads_task_data(self):
        with patch.object(r.projection,'verify_baseline_projection',side_effect=AssertionError('Unexpected task read')):
            frame,_,_=self.load()
        self.assertEqual(frame['schedule'],tuple(self.ids));self.assertFalse(self.output.exists())

    def test_unknown_role_missing_schedule_and_invalid_budget_fail_before_launch(self):
        changes=[('purpose','evaluate'),('schedule',self.ids[:1]),('provider_spend_usd',1),
                 ('automatic_retry',True),('phase_seconds',{p:True for p in r.schedule.PHASES})]
        for field,value in changes:
            previous=self.frame[field];self.frame[field]=value
            with patch.object(r,'supervise_command') as dispatch,self.assertRaises(ValueError):self.load()
            dispatch.assert_not_called();self.assertFalse(self.output.exists());self.frame[field]=previous

    def test_existing_output_does_not_restart(self):
        self.output.mkdir();(self.output/'original.txt').write_text('preserved')
        with self.assertRaisesRegex(ValueError,'already exists'):self.load()
        self.assertEqual((self.output/'original.txt').read_text(),'preserved')

    def test_source_mutation_rejected(self):
        self.frame['code_files']=[]
        with self.assertRaisesRegex(ValueError,'code changed'):self.load()

    def test_supervision_failure_preserves_result_and_is_not_retried(self):
        error=TimeoutError('invented uncertain child')
        error.result=SimpleNamespace(stdout=b'partial stdout',stderr=b'partial stderr',returncode=124,
            supervision=dict(termination_reason='deadline_exceeded',process_reaped=True))
        with patch.object(r,'supervise_command',side_effect=error) as dispatch:
            with self.assertRaises(TimeoutError):r.supervised(['fictional'],r.ProcessLimits(1,1024),self.root)
        self.assertEqual(dispatch.call_count,1)
        self.assertEqual((self.root/'stdout.bin').read_bytes(),b'partial stdout')
        self.assertTrue(parse_json((self.root/'PROCESS.json').read_bytes())['supervision']['process_reaped'])

    def test_actor_runtime_grants_never_include_repository_root(self):
        # Broad repository roots would let a model actor open evaluator files.
        from .access import RoleAudit
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'runtime root'):
            RoleAudit(inputs=[],code_files=[],runtime_roots=(r.ROOT,),model_files=[],output=self.output)

    def test_actual_supervisor_timeout_and_overflow_keep_partial_output(self):
        for name,command,limits,error in (
            ('timeout',[sys.executable,'-I','-B','-c','import time;print("entered",flush=True);time.sleep(5)'],r.ProcessLimits(.3,1024),EngineDeadlineExceeded),
            ('overflow',[sys.executable,'-I','-B','-c','print("X"*100000,flush=True)'],r.ProcessLimits(10,100),EngineOutputLimitExceeded),
        ):
            output=self.root/name;output.mkdir()
            with self.assertRaises(error):r.supervised(command,limits,output)
            record=parse_json((output/'PROCESS.json').read_bytes())
            self.assertTrue(record['supervision']['process_reaped'])
            self.assertLessEqual(len((output/'stdout.bin').read_bytes())+len((output/'stderr.bin').read_bytes()),limits.max_output_bytes)

    def test_invalid_worker_authority_does_not_create_output(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            r.worker(self.root/'missing.json','0'*64,self.root/'job.json','0'*64,self.output)
        self.assertFalse(self.output.exists())

    def test_late_changed_or_added_phase_bytes_cannot_enter_final_seal(self):
        first=dict(path='/invented/critic/worker/COMPLETE.json',bytes=3,sha256='a'*64)
        expected={'critic':{'worker/COMPLETE.json':first}}
        clean={'critic/worker/COMPLETE.json':first,'FRAME.json':{'bytes':1,'sha256':'b'*64}}
        r.verify_final_packages(clean,expected)
        for changed in (dict(clean,**{'critic/worker/COMPLETE.json':dict(first,sha256='0'*64)}),
                        dict(clean,**{'critic/extra.json':first})):
            with self.assertRaisesRegex(ValueError,'changed before final'):r.verify_final_packages(changed,expected)

    def test_coordinator_grants_reconstruct_actual_projection_role_entries(self):
        from .test_projection import ProjectionTests
        fixture=ProjectionTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        baseline=fixture.prepare()
        granted=r._grants(baseline,{})
        for entry in baseline.manifest['role_files']:
            self.assertIn(encode(entry['proof']),granted)
        self.assertFalse(any(Path(p['path']).name=='COORDINATOR.json' for p in granted))
        self.assertEqual(len(granted),len({p['path'] for p in granted}))


if __name__=='__main__':unittest.main()
