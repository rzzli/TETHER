"""Real invented subprocesses test calibration launch/failure accounting."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether._process import EngineDeadlineExceeded, EngineOutputLimitExceeded
from tether_engine.serde import canonical
from experiments.scifact_calibration import run as r

WORKER = '''
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--recipe');p.add_argument('--recipe-sha256');p.add_argument('--output')
a=p.parse_args();root=Path(a.output);root.mkdir()
raw=Path(a.recipe).read_bytes();assert hashlib.sha256(raw).hexdigest()==a.recipe_sha256
recipe=json.loads(raw);n=len(recipe['schedule'])
counts=dict(scheduled_claims=n,scheduled_pairs=5*n,completed_claims=n,
    complete_prediction_claims=n,completed_pairs=5*n,input_unavailable_pairs=0,
    overlength_pairs=0,unexpected_failed_pairs=0)
status=dict(schema_version=1,kind='sc05_calibration_worker_status_v1',status='completed',
    counts=counts,recipe_sha256=a.recipe_sha256,io_denials=0,hard_deadline=False,
    references_read=False,scientific_scoring_performed=False,automatic_retry=False,error=None,files={})
(root/'STATUS.json').write_text(json.dumps(status))
raw_status=(root/'STATUS.json').read_bytes()
receipt=dict(schema_version=1,kind='sc05_calibration_worker_receipt_v1',status='completed',
    recipe_sha256=a.recipe_sha256,files={'STATUS.json':{'path':str(root/'STATUS.json'),'bytes':len(raw_status),'sha256':hashlib.sha256(raw_status).hexdigest()}})
(root/'RECEIPT.json').write_text(json.dumps(receipt))
print('invented successful worker')
'''


class CalibrationSupervisorTests(unittest.TestCase):
    def setUp(self):
        folder=r.ROOT/'data/cache/sc05-supervision-controls'
        folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.worker=self.root/'fixture_worker.py'
        self.worker.write_text(WORKER,encoding='utf-8')
        self.recipe=self.root/'recipe.json'
        self.recipe.write_bytes(canonical(dict(schema_version=1,kind='sc05_calibration_worker_v1',
            purpose='calibrate',mode='qualification',schedule=[1,2],phase_seconds=10,output_bytes=1024**2,
            code_files=[r._proof(self.worker)])))
        self.output=self.root/'attempt'
        self.frame=self.root/'frame.json'
        self.spec=dict(schema_version=1,kind=r.KIND,purpose='calibrate',mode='qualification',
            recipe=r._proof(self.recipe),worker=r._proof(self.worker),interpreter=r._proof(Path(sys.executable)),
            code_files=[r._proof(Path(r.__file__)),r._proof(self.worker)],
            limits=dict(process_seconds=12,console_bytes=1024**2),output=str(self.output))

    def execute(self):
        self.frame.write_bytes(canonical(self.spec))
        return r.execute(self.frame,r.digest(self.frame.read_bytes()),output=self.output)

    def rewrite(self,text):
        self.worker.write_text(text,encoding='utf-8')
        self.spec['worker']=r._proof(self.worker)
        self.spec['code_files'][1]=self.spec['worker']
        recipe=json.loads(self.recipe.read_bytes());recipe['code_files']=[self.spec['worker']]
        self.recipe.write_bytes(canonical(recipe));self.spec['recipe']=r._proof(self.recipe)

    def test_success_pins_exact_child_and_retains_coverage(self):
        result=self.execute()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['worker_status']['counts']['completed_pairs'],10)
        self.assertEqual(result['scientific_validation'],'not_evaluated')
        receipt=json.loads((self.output/'RECEIPT.json').read_bytes())
        for name,proof in receipt['files'].items():
            raw=(self.output/name).read_bytes()
            self.assertEqual((len(raw),r.digest(raw)),(proof['bytes'],proof['sha256']))
        self.assertIn('worker/STATUS.json',receipt['files'])
        with self.assertRaises(ValueError):self.execute()

    def test_mutated_worker_pin_fails_before_process(self):
        self.worker.write_text(WORKER+'\n# changed',encoding='utf-8')
        with patch.object(r,'supervise_command') as launch:
            with self.assertRaises(ValueError):self.execute()
            launch.assert_not_called()
        failure=json.loads((self.output/'FAILURE.json').read_bytes())
        self.assertFalse(failure['worker_entered'])

    def test_mismatched_external_frame_fails_before_output(self):
        self.frame.write_bytes(canonical(self.spec))
        with self.assertRaises(ValueError):r.execute(self.frame,'0'*64,output=self.output)
        self.assertFalse(self.output.exists())

    def test_nonzero_exit_retains_streams_and_failure(self):
        self.rewrite("import sys\nprint('invented partial work')\nsys.exit(7)\n")
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(json.loads((self.output/'PROCESS.json').read_bytes())['returncode'],7)
        self.assertIn(b'invented partial work',(self.output/'stdout.bin').read_bytes())
        self.assertFalse((self.output/'RECEIPT.json').exists())

    def test_zero_exit_without_terminal_status_is_failure(self):
        self.rewrite("print('no status')\n")
        with self.assertRaises(FileNotFoundError):self.execute()
        self.assertTrue((self.output/'FAILURE.json').exists())

    def test_incomplete_schedule_cannot_be_promoted(self):
        self.rewrite(WORKER.replace("completed_pairs=5*n","completed_pairs=5*n-1"))
        with self.assertRaisesRegex(ValueError,'Incomplete calibration'):self.execute()
        self.assertFalse((self.output/'RECEIPT.json').exists())

    def test_hard_process_timeout_is_terminal_and_never_repeated(self):
        self.rewrite("import time\nprint('entered',flush=True)\ntime.sleep(10)\n")
        self.spec['limits']['process_seconds']=.3
        recipe=json.loads(self.recipe.read_bytes());recipe['phase_seconds']=.2
        self.recipe.write_bytes(canonical(recipe));self.spec['recipe']=r._proof(self.recipe)
        with self.assertRaises(EngineDeadlineExceeded):self.execute()
        report=json.loads((self.output/'PROCESS.json').read_bytes())
        self.assertEqual(report['supervision']['termination_reason'],'deadline_exceeded')
        self.assertTrue(report['supervision']['process_reaped'])
        with self.assertRaises(ValueError):self.execute()

    def test_console_overflow_keeps_bounded_output(self):
        self.rewrite("print('X'*50000,flush=True)\n")
        self.spec['limits']['console_bytes']=100
        with self.assertRaises(EngineOutputLimitExceeded):self.execute()
        self.assertLessEqual((self.output/'stdout.bin').stat().st_size+(self.output/'stderr.bin').stat().st_size,100)

    def test_production_cannot_substitute_qualification_script(self):
        self.spec['mode']='production'
        with self.assertRaisesRegex(ValueError,'Production must use'):self.execute()
        self.assertFalse(self.output.exists())

    def test_output_escape_or_role_substitution_precedes_dispatch(self):
        for field,value in (('purpose','predict'),('output',str(self.root/'different'))):
            original=self.spec[field];self.spec[field]=value
            with patch.object(r,'supervise_command') as launch:
                with self.assertRaises(ValueError):self.execute()
                launch.assert_not_called()
            self.spec[field]=original
        self.assertFalse(self.output.exists())

    def test_absolute_script_cli_imports_under_isolated_python(self):
        result=subprocess.run([sys.executable,'-I','-B',r.__file__,'--help'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertIn(b'--frame-sha256',result.stdout)

    def test_success_status_without_receipt_is_rejected(self):
        self.rewrite(WORKER+"\n(root/'RECEIPT.json').unlink()\n")
        with self.assertRaises((ValueError,FileNotFoundError)):self.execute()
        self.assertFalse((self.output/'RECEIPT.json').exists())

    def test_finalization_and_deadline_markers_dominate_worker_success(self):
        for i,name in enumerate(('DEADLINE.json','FINALIZATION-FAILED.json')):
            self.output=self.root/('marker-'+str(i));self.spec['output']=str(self.output)
            self.rewrite(WORKER+f"\n(root/'{name}').write_text('{{}}')\n")
            with self.assertRaisesRegex(ValueError,'terminal failure marker'):self.execute()

    def test_resealed_status_with_denied_io_or_deadline_cannot_succeed(self):
        for i,(before,after) in enumerate((('io_denials=0','io_denials=1'),('hard_deadline=False','hard_deadline=True'),
                                         ('automatic_retry=False','automatic_retry=True'))):
            self.output=self.root/('status-'+str(i));self.spec['output']=str(self.output)
            self.rewrite(WORKER.replace(before,after))
            with self.assertRaisesRegex(ValueError,'Worker execution policy'):self.execute()

    def test_worker_inventory_must_bind_every_output(self):
        self.rewrite(WORKER+"\n(root/'unlisted.txt').write_text('invented extra')\n")
        with self.assertRaisesRegex(ValueError,'Worker receipt inventory'):self.execute()

    def test_recipe_cannot_grant_code_outside_parent_pins(self):
        other=self.root/'other.py';other.write_text('# extra source\n')
        recipe=json.loads(self.recipe.read_bytes());recipe['code_files'].append(r._proof(other))
        self.recipe.write_bytes(canonical(recipe));self.spec['recipe']=r._proof(self.recipe)
        with patch.object(r,'supervise_command') as launch:
            with self.assertRaisesRegex(ValueError,'Worker source grants'):self.execute()
            launch.assert_not_called()

    def test_late_worker_mutation_cannot_replace_verified_terminal(self):
        original=r._proof;reads=0
        def mutate(path):
            nonlocal reads
            if Path(path)==self.output/'worker/STATUS.json':
                reads+=1
                if reads==3:
                    status=json.loads(Path(path).read_bytes())
                    status['counts']['completed_pairs']=9
                    Path(path).write_bytes(canonical(status))
            return original(path)
        with patch.object(r,'_proof',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'Verified worker'):
                self.execute()
        self.assertFalse((self.output/'RECEIPT.json').exists())

    def test_actual_worker_contract_integrates_with_supervisor_on_invented_solver(self):
        from experiments.scifact_calibration.test_worker import worker_fixture
        base=self.root/'actual-worker';base.mkdir()
        path,recipe,requests=worker_fixture(base)
        launcher=("import sys\nsys.path[:0]="+repr([str(r.ROOT),str(r.ROOT/'src')])+"\n"
            "import argparse\nfrom experiments.scifact_calibration.worker import run_calibration\n"
            "from experiments.scifact_calibration.test_worker import FakeSolver\n"
            "p=argparse.ArgumentParser()\np.add_argument('--recipe');p.add_argument('--recipe-sha256');p.add_argument('--output')\n"
            "a=p.parse_args()\nrun_calibration(a.recipe,a.recipe_sha256,a.output,"
            "_solver_factory=lambda *args,**kwargs:FakeSolver(),_memory_reader=lambda:{'fixture':True})\n")
        self.worker.write_text(launcher,encoding='utf-8')
        self.spec['worker']=r._proof(self.worker);self.spec['recipe']=r._proof(path)
        pins=recipe['code_files']+[r._proof(self.worker),r._proof(Path(r.__file__).with_name('test_worker.py'))]
        self.spec['code_files']=list({p['path']:p for p in pins}.values())
        self.spec['limits']['process_seconds']=recipe['phase_seconds']+2
        result=self.execute()
        self.assertEqual(result['worker_status']['counts']['completed_pairs'],5)
        self.assertEqual(result['worker_status']['io_denials'],0)
        self.assertEqual(result['worker_status']['status'],'completed')


if __name__=='__main__':unittest.main()
