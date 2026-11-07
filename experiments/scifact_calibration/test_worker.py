"""Invented bounded worker controls; no model weights or native references."""
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, ContractError
from experiments.scifact_calibration.test_inputs import ROOT, proof, write


def worker_fixture(root):
    requests=[dict(id=1,claim='Fictional observation.',documents=[dict(doc_id=i,title='Document',abstract=['A fictional sentence.']) for i in range(1,6)])]
    request_path=root/'requests.jsonl';request_path.write_bytes(b''.join(canonical(x)+b'\n' for x in requests))
    model=root/'model';model.mkdir(); asset=model/'tokenizer.json';asset.write_bytes(b'{}')
    receipt=model/'RECEIPT.json'
    write(receipt,dict(status='PASS',files=[dict(path=str(asset),relative_path='tokenizer.json',bytes=2,sha256=proof(asset)['sha256'],status='completed')]))
    files=[p for folder in ('src/tether_engine','experiments/scifact_calibration','experiments/scifact_comparison','experiments/scifact_multivers')
           for p in (ROOT/folder).glob('*.py') if not p.name.startswith('test_')]
    recipe=dict(schema_version=1,kind='sc05_calibration_worker_v1',purpose='calibrate',mode='qualification',
        requests=proof(request_path),schedule=[1],model=dict(acquisition_root=str(model),receipt=proof(receipt),assets=[proof(asset)]),
        code_files=[proof(p) for p in sorted(files)],runtime_roots=sorted({str(Path(sys.prefix).resolve()),str(Path(sys.base_prefix).resolve())}),
        device='cuda:0',pair_seconds=120,phase_seconds=300,output_bytes=2*1024**3)
    path=root/'recipe.json';write(path,recipe)
    return path,recipe,requests


class FakeSolver:
    metadata={'fixture':True};device_info={'fixture':True};load_seconds=0
    def __init__(self,error=None):self.calls=0;self.error=error
    def predict(self,claims,corpus,*,pair_deadline_seconds,event):
        self.calls+=1;cid=claims[0]['id'];did=corpus[0]['doc_id']
        event(event='pair_started',claim_id=cid,abstract_id=did)
        if self.error:raise self.error
        pair=dict(claim_id=cid,abstract_id=did,predicted_label='SUPPORT',predicted_rationale=[0],label_probs=[0.,0.,1.],rationale_probs=[1.])
        event(event='pair_completed',claim_id=cid,abstract_id=did,prediction=pair)
        return dict(status='completed',pair_predictions=[pair],observations=[dict(token_count=10)])


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path,self.recipe,self.requests=worker_fixture(self.root)

    def run_worker(self,solver=None,**kwargs):
        from experiments.scifact_calibration.worker import run_calibration
        solver=solver or FakeSolver()
        return run_calibration(self.path,proof(self.path)['sha256'],self.root/'output',_solver_factory=lambda *a,**k:solver,**kwargs)

    def test_five_pairs_seal_exact_inventory_and_accounting(self):
        report=self.run_worker()
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['counts']['completed_pairs'],5)
        output=self.root/'output';receipt=json.loads((output/'RECEIPT.json').read_bytes())
        self.assertEqual(set(receipt['files']),{p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}-{'RECEIPT.json'})
        for name,item in receipt['files'].items():self.assertEqual(proof(output/name),item)
        self.assertEqual({p['state'] for p in report['pair_states']},{'completed'})
        journal=[json.loads(x) for x in (output/'journal.jsonl').read_bytes().splitlines()]
        self.assertEqual(journal[-1]['event'],'calibration_completed')

    def test_wrong_purpose_and_production_schedule_never_load_model(self):
        for field,value in (('purpose','predict'),('mode','production')):
            with self.subTest(field=field):
                self.recipe[field]=value;write(self.path,self.recipe)
                with self.assertRaises(ContractError):self.run_worker()
                status=json.loads((self.root/'output/STATUS.json').read_bytes())
                self.assertEqual(status['status'],'failed')
                # Each failure remains retained; the next probe uses a distinct folder.
                self.root=self.root/field;self.root.mkdir();self.path,self.recipe,self.requests=worker_fixture(self.root)

    def test_annotations_rejected_before_solver(self):
        self.requests[0]['reference']='SUPPORT';p=Path(self.recipe['requests']['path']);p.write_bytes(canonical(self.requests[0])+b'\n')
        self.recipe['requests']=proof(p);write(self.path,self.recipe);solver=FakeSolver()
        with self.assertRaises(ValueError):self.run_worker(solver)
        self.assertEqual(solver.calls,0)

    def test_timeout_preserves_entered_and_untouched_pairs(self):
        solver=FakeSolver(TimeoutError('invented timeout'))
        with self.assertRaises(TimeoutError):self.run_worker(solver)
        report=json.loads((self.root/'output/STATUS.json').read_bytes())
        self.assertEqual(solver.calls,1)
        self.assertEqual(report['pair_states'][0]['state'],'attempt_entered_no_terminal')
        self.assertEqual([p['state'] for p in report['pair_states'][1:]],['untouched']*4)

    def test_undeclared_read_is_denied_inside_solver(self):
        forbidden=self.root/'secret-reference.json';forbidden.write_bytes(b'{}')
        class Reader(FakeSolver):
            def predict(self,*a,**k):forbidden.read_bytes()
        with self.assertRaises(PermissionError):self.run_worker(Reader())
        events=[json.loads(line) for line in (self.root/'output/io-audit.jsonl').read_bytes().splitlines()]
        self.assertTrue(any(not row['allowed'] for row in events))

    def test_swallowed_permission_denial_cannot_finalize_success(self):
        forbidden=self.root/'secret-reference.json';forbidden.write_bytes(b'{}')
        class Swallows(FakeSolver):
            def predict(self,*a,**k):
                try:forbidden.read_bytes()
                except PermissionError:pass
                return super().predict(*a,**k)
        with self.assertRaises(ContractError):self.run_worker(Swallows())
        status=json.loads((self.root/'output/STATUS.json').read_bytes())
        self.assertEqual(status['status'],'failed');self.assertGreater(status['io_denials'],0)

    def test_committed_prediction_survives_write_failure(self):
        from experiments.scifact_comparison.worker import Writer
        original=Writer.publish
        def failed(writer,name,value):
            if name.startswith('pairs/'):raise OSError('invented write failure')
            return original(writer,name,value)
        solver=FakeSolver()
        with patch.object(Writer,'publish',failed),self.assertRaises(OSError):self.run_worker(solver)
        status=json.loads((self.root/'output/STATUS.json').read_bytes())
        self.assertEqual(status['pair_states'][0]['state'],'returned_uncommitted')
        self.assertEqual(solver.calls,1)

    def test_terminal_journal_write_failure_cannot_publish_success(self):
        from experiments.scifact_comparison.worker import Writer
        original=Writer.event
        def failed(writer,event,**details):
            if event=='calibration_completed':raise OSError('invented terminal write failure')
            return original(writer,event,**details)
        with patch.object(Writer,'event',failed),self.assertRaises(ContractError):self.run_worker()
        self.assertEqual(json.loads((self.root/'output/STATUS.json').read_bytes())['status'],'failed')

    def test_interruption_is_retained_without_retry(self):
        solver=FakeSolver(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):self.run_worker(solver)
        self.assertEqual(solver.calls,1)
        self.assertEqual(json.loads((self.root/'output/STATUS.json').read_bytes())['status'],'failed')

    def test_invalid_returned_probabilities_are_not_committed(self):
        class Invalid(FakeSolver):
            def predict(self,*a,**k):
                result=super().predict(*a,**k)
                result['pair_predictions'][0]['label_probs']=[.1,.1,.1]
                return result
        with self.assertRaises(ContractError):self.run_worker(Invalid())
        self.assertFalse((self.root/'output/pairs/1-1.json').exists())

    def test_overlength_full_schedule_is_retained_as_failed(self):
        from experiments.scifact_multivers.contracts import ContractError as NativeError
        solver=FakeSolver(NativeError('Input exceeds 4096 tokens; no truncation is permitted'))
        with self.assertRaises(ContractError):self.run_worker(solver)
        status=json.loads((self.root/'output/STATUS.json').read_bytes())
        self.assertEqual(status['counts']['overlength_pairs'],5)
        self.assertEqual(status['status'],'failed');self.assertEqual(solver.calls,5)

    def test_hard_pair_deadline_stops_real_invented_child(self):
        self.recipe['pair_seconds']=.15;self.recipe['phase_seconds']=10;write(self.path,self.recipe)
        code="""import sys,pathlib,time
sys.path[:0]=[sys.argv[1],str(pathlib.Path(sys.argv[1])/'src')]
from experiments.scifact_calibration.worker import run_calibration
class Hang:
 metadata={};device_info={};load_seconds=0
 def predict(self,claims,corpus,*,pair_deadline_seconds,event):
  event(event='pair_started',claim_id=claims[0]['id'],abstract_id=corpus[0]['doc_id'])
  while True:time.sleep(1)
run_calibration(sys.argv[2],sys.argv[3],sys.argv[4],_solver_factory=lambda *a,**k:Hang())
"""
        completed=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT),str(self.path),proof(self.path)['sha256'],str(self.root/'output')],
                                 capture_output=True,timeout=8)
        self.assertEqual(completed.returncode,124,completed.stderr.decode(errors='replace'))
        status=json.loads((self.root/'output/STATUS.json').read_bytes())
        self.assertEqual(status['status'],'failed');self.assertTrue(status['hard_deadline'])
        self.assertTrue((self.root/'output/DEADLINE.json').is_file())
        self.assertEqual(sum(p['attempt_reserved'] for p in status['pair_states']),1)

    def test_duplicate_output_does_not_repeat(self):
        solver=FakeSolver();self.run_worker(solver)
        with self.assertRaises(FileExistsError):self.run_worker(solver)
        self.assertEqual(solver.calls,5)

    def test_broad_runtime_root_rejected(self):
        self.recipe['runtime_roots'].append(str(ROOT));write(self.path,self.recipe)
        with self.assertRaises(ContractError):self.run_worker()


if __name__=='__main__':unittest.main()
