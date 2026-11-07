"""Invented model-free controller, seal-order and arithmetic replay controls."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, parse_json
from . import calibration as c, evaluate as e
from .test_inputs import proof,write
from .test_outcomes import fixture


def build(root):
    first=root/'calibration';second=root/'development';first.mkdir();second.mkdir()
    calibration_path,calibration,prepared=fixture(first,'calibration')
    development_path,development,_=fixture(second,'dev')
    development['preparation_transition']=calibration['preparation_transition'];development['sealed_mapping']=None
    source=parse_json((prepared/'manifest.json').read_bytes())
    admission=development['producer']['admission'];old_frame_path=Path(admission['frame']['path'])
    old_frame=parse_json(old_frame_path.read_bytes());old_frame['references']=proof(prepared/'restricted/references_dev.jsonl')
    admission['frame']=write(old_frame_path,old_frame)
    check_path=Path(admission['checks']['path']);checks=parse_json(check_path.read_bytes())
    for item in checks:
        request=item['candidate']['request'];request['release_sha256']=source['archive']['sha256']
        item['candidate']['envelope']['request_sha256']=e.digest(canonical(request))
    admission['checks']=write(check_path,checks);receipt_path=Path(admission['receipt']['path']);receipt=parse_json(receipt_path.read_bytes())
    receipt['frame_sha256']=admission['frame']['sha256'];receipt['files']['CHECKS.json']=admission['checks']
    admission['receipt']=write(receipt_path,receipt);write(development_path,development)
    code={path:proof(path) for path in e.required_code()}
    for child in (calibration,development):
        for item in child['code_files']:code[Path(item['path'])]=item
    frame=dict(schema_version=1,kind=e.KIND,purpose='evaluate',mode='fictional_qualification',
        calibration_frame=proof(calibration_path),development_template=proof(development_path),
        code_files=[code[path] for path in sorted(code)],environment=e.environment(),limits=dict(phase_seconds=120,output_bytes=64*1024**2),
        output=str(root/'evaluated'))
    path=root/'evaluation-frame.json';write(path,frame)
    return path,frame


def reseal(root):
    """Re-anchor a corrupted invented output to test semantic reconstruction."""
    receipt=parse_json((root/'RECEIPT.json').read_bytes());receipt['files']={
        p.relative_to(root).as_posix():proof(p) for p in root.rglob('*') if p.is_file() and p.name!='RECEIPT.json'}
    return write(root/'RECEIPT.json',receipt)['sha256']


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        folder=e.ROOT/'tmp';folder.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path,self.frame=build(self.root);self.output=Path(self.frame['output'])
    def execute(self,**kwargs):return e.execute(self.path,proof(self.path)['sha256'],output=self.output,**kwargs)
    def reframe(self):write(self.path,self.frame)
    def verify(self):return e.verify(self.output,proof(self.output/'RECEIPT.json')['sha256'])
    def test_complete_actual_format_fixture_and_read_only_reconstruction(self):
        original=e.outcomes.reconstruct_partition;order=[]
        def observed(path,sha):
            value=parse_json(Path(path).read_bytes());order.append(value['partition'])
            if value['partition']=='dev':
                self.assertTrue((self.output/'MAPPING-RECEIPT.json').is_file())
                self.assertEqual(value['sealed_mapping'],proof(self.output/'MAPPING.json'))
                events=e._journal((self.output/'journal.jsonl').read_bytes())
                self.assertEqual(events[-1]['event'],'development_open_authorized')
            return original(path,sha)
        with patch.object(e.outcomes,'reconstruct_partition',side_effect=observed):result=self.execute()
        self.assertEqual(order,['calibration','dev']);self.assertEqual(result['status'],'complete')
        self.assertEqual(result['fits'],result['calibration_components']+1);self.assertEqual(result['bootstrap_replicates'],10000)
        before={p:proof(p) for p in self.output.rglob('*') if p.is_file()}
        with patch.object(c,'fit_coefficients',side_effect=AssertionError('Verifier refitted')),patch.object(c,'fit_calibration',side_effect=AssertionError('Verifier refitted')):
            verified=self.verify()
        self.assertTrue(verified['arithmetic_consistency']);self.assertFalse(verified['independent_biological_validation'])
        self.assertEqual(before,{p:proof(p) for p in self.output.rglob('*') if p.is_file()})
    def test_missing_calibration_pair_blocks_all_fits_and_dev_reads(self):
        original=e.outcomes.reconstruct_partition;calls=[]
        def missing(path,sha):
            value=original(path,sha);calls.append(value.partition)
            confidence=replace(value.rows[0].confidence,status='unavailable',score=None,logit=None,reason='Invented missing pair')
            return replace(value,rows=(replace(value.rows[0],confidence=confidence),*value.rows[1:]))
        with patch.object(e.outcomes,'reconstruct_partition',side_effect=missing),patch.object(c,'fit_coefficients') as fit:
            with self.assertRaises(ValueError):self.execute()
            fit.assert_not_called()
        self.assertEqual(calls,['calibration']);self.assertFalse((self.output/'MAPPING.json').exists())
        self.assertTrue((self.output/'CALIBRATION-INPUTS.json').exists());self.assertTrue((self.output/'FAILURE.json').exists())
    def test_failed_deletion_retains_all_attempts_and_no_applicable_map(self):
        original=c.fit_coefficients;attempts=[]
        def failed(*args,**kwargs):
            attempts.append(1)
            return c.FitResult('failed','Invented fold failure',None,None,None,None,1,1.,.01,False,False,False) if len(attempts)==2 else original(*args,**kwargs)
        with patch.object(c,'fit_coefficients',side_effect=failed):
            with self.assertRaisesRegex(ValueError,'All fixed'):self.execute()
        suite=parse_json((self.output/'CALIBRATION-SUITE.json').read_bytes())
        self.assertEqual(len(attempts),len(suite['attempts']));self.assertEqual(len(suite['attempts']),len(suite['component_assignments'])+1)
        self.assertIsNone(suite['main']);self.assertFalse((self.output/'MAPPING-RECEIPT.json').exists())
        self.assertFalse((self.output/'DEVELOPMENT-FRAME.json').exists());self.assertFalse((self.output/'RECEIPT.json').exists())
    def test_interruption_leaves_reserved_fit_and_never_repeats_directory(self):
        with patch.object(c,'fit_coefficients',side_effect=KeyboardInterrupt('Invented interruption')):
            with self.assertRaises(KeyboardInterrupt):self.execute()
        self.assertTrue((self.output/'fits/000-reserved.json').is_file());self.assertFalse((self.output/'fits/000-result.json').exists())
        failure=parse_json((self.output/'FAILURE.json').read_bytes());self.assertEqual(failure['status'],'interrupted')
        with patch.object(c,'fit_coefficients') as fit:
            with self.assertRaises(ValueError):self.execute()
            fit.assert_not_called()
    def test_map_seal_write_failure_cannot_open_dev(self):
        original=e.atomic.publish_bytes;read=e.outcomes.reconstruct_partition;partitions=[]
        def writer(path,raw,**kwargs):
            if Path(path).name=='MAPPING-RECEIPT.json':raise OSError('Invented seal write failure')
            return original(path,raw,**kwargs)
        def reader(path,sha):
            value=read(path,sha);partitions.append(value.partition);return value
        with patch.object(e.atomic,'publish_bytes',side_effect=writer),patch.object(e.outcomes,'reconstruct_partition',side_effect=reader):
            with self.assertRaises(OSError):self.execute()
        self.assertEqual(partitions,['calibration']);self.assertTrue((self.output/'FAILURE.json').exists())
        self.assertFalse((self.output/'RECEIPT.json').exists())
    def test_source_environment_output_overlap_and_production_count_fail_before_reservation(self):
        tests=[('environment',dict(self.frame['environment'],python='different')),('mode','production')]
        for key,value in tests:
            previous=self.frame[key];self.frame[key]=value;self.reframe()
            with self.subTest(key=key),self.assertRaises(ValueError):self.execute()
            self.assertFalse(self.output.exists());self.frame[key]=previous
        calibration=parse_json(Path(self.frame['calibration_frame']['path']).read_bytes())
        self.output=Path(calibration['producer']['root'])/'nested-evaluation';self.frame['output']=str(self.output);self.reframe()
        with self.assertRaisesRegex(ValueError,'overlaps original'):self.execute()
        self.assertFalse(self.output.exists())
    def test_deadline_before_outcomes_retains_failure_without_scoring(self):
        ticks=iter([0.,121.,121.])
        with patch.object(e.outcomes,'reconstruct_partition') as reconstruct:
            with self.assertRaisesRegex(ValueError,'deadline'):self.execute(_clock=lambda:next(ticks))
            reconstruct.assert_not_called()
        self.assertTrue((self.output/'FAILURE.json').exists());self.assertFalse((self.output/'RECEIPT.json').exists())
    def test_concurrent_output_has_one_execution(self):
        entered=threading.Event();release=threading.Event();original=e.outcomes.reconstruct_partition;calls=[]
        def reader(path,sha):
            calls.append(path)
            if len(calls)==1:entered.set();self.assertTrue(release.wait(10))
            return original(path,sha)
        with patch.object(e.outcomes,'reconstruct_partition',side_effect=reader),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.execute);self.assertTrue(entered.wait(10))
            try:
                with self.assertRaises((ValueError,FileExistsError)):self.execute()
            finally:release.set()
            self.assertEqual(first.result(timeout=30)['status'],'complete')
        self.assertEqual(len(calls),2)
    def test_resealed_statistics_and_accounting_corruption_are_rejected(self):
        self.execute()
        for name,mutate in (('BOOTSTRAP.json',lambda v:v.update(completed_replicates=9999)),
                            ('POINT-SUMMARY.json',lambda v:v.update(scheduled=99)),
                            ('REPORT.json',lambda v:v.update(fits=1)),
                            ('MAPPING.json',lambda v:v.update(a=v['a']+1))):
            path=self.output/name;original=path.read_bytes();value=parse_json(original);mutate(value);write(path,value)
            sha=reseal(self.output)
            with self.subTest(name=name),self.assertRaises(ValueError):e.verify(self.output,sha)
            path.write_bytes(original);reseal(self.output)
    def test_resealed_journal_order_and_failure_marker_override_receipt(self):
        self.execute();path=self.output/'journal.jsonl';events=e._journal(path.read_bytes())
        sealed=next(i for i,r in enumerate(events) if r['event']=='mapping_sealed');events[sealed],events[sealed+1]=events[sealed+1],events[sealed]
        previous=None
        for index,event in enumerate(events):
            event.pop('sha256');event['sequence']=index;event['previous_sha256']=previous;previous=e.digest(canonical(event));event['sha256']=previous
        path.write_bytes(b''.join(canonical(event)+b'\n' for event in events));sha=reseal(self.output)
        with self.assertRaises(ValueError):e.verify(self.output,sha)
        write(self.output/'FAILURE.json',dict(status='failed'));sha=reseal(self.output)
        with self.assertRaisesRegex(ValueError,'Failure marker'):e.verify(self.output,sha)
    def test_cli_imports_in_isolated_interpreter(self):
        result=subprocess.run([sys.executable,'-I','-B',e.__file__,'--help'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'execute',result.stdout)
    def test_cli_has_one_source_identity_with_and_without_isolated_parent(self):
        # Create each anchored frame in the source environment used by the
        # documented command. Do not relabel installed-module proofs as source
        # proofs: that would conceal exactly the import mismatch tested here.
        script = '''
import json, subprocess, sys
from pathlib import Path
sys.path[:0] = sys.argv[1:4]
from experiments.scifact_calibration.test_evaluate import EvaluationTests, e, proof
import tether_engine
assert Path(tether_engine.__file__).resolve().is_relative_to(e.ROOT/'src')
fixture=EvaluationTests('runTest')
try:
    fixture.setUp()
    result=subprocess.run([sys.executable,'-I','-B',e.__file__,'execute',
        '--frame',str(fixture.path),'--frame-sha256',proof(fixture.path)['sha256'],
        '--output',str(fixture.output)],capture_output=True,timeout=40)
    assert result.returncode==0,result.stderr.decode()
    assert json.loads(result.stdout)['status']=='complete'
    assert fixture.verify()['source_consistency']
finally:
    fixture.doCleanups()
'''
        paths=[str(e.ROOT),str(e.ROOT/'src'),str(e.ROOT/'packages/tether/src')]
        for flags,hash_seed in (([],'1'),(['-I'],'2')):
            with self.subTest(flags=flags,hash_seed=hash_seed):
                environment=dict(os.environ,PYTHONHASHSEED=hash_seed)
                result=subprocess.run([sys.executable,*flags,'-B','-c',script,*paths],
                                      capture_output=True,timeout=55,env=environment)
                self.assertEqual(result.returncode,0,result.stderr.decode())
    def test_proof_inventory_order_is_not_an_outcome_order(self):
        partition=e.outcomes.reconstruct_partition(self.frame['calibration_frame']['path'],
            self.frame['calibration_frame']['sha256'])
        self.assertEqual(e._partition_payload(partition),
                         e._partition_payload(replace(partition,proofs=tuple(reversed(partition.proofs)))))


if __name__=='__main__':unittest.main()
