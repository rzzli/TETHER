"""Fictional sealed-map recovery controls; never actual outcomes or inference."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical,parse_json
from . import recovery as r, evaluate as e, calibration as c
from .test_evaluate import build
from .test_inputs import proof,write


def inventory(root):return e._inventory(root,e.MAX_OUTPUT)


def failed_parent(root):
    path,frame=build(root);output=Path(frame['output']);reader=e.outcomes.reconstruct_partition
    def interrupted(path,sha):
        if parse_json(Path(path).read_bytes())['partition']=='dev':
            raise ValueError('Invented retained admission failure')
        return reader(path,sha)
    with patch.object(e.outcomes,'reconstruct_partition',side_effect=interrupted):
        try:e.execute(path,proof(path)['sha256'],output=output)
        except ValueError as error:
            if str(error)!='Invented retained admission failure':raise
        else:raise AssertionError('Original fixture must fail after mapping seal')
    launch=root/'launch';launch.mkdir();(launch/'stdout.bin').write_bytes(b'')
    (launch/'stderr.bin').write_bytes(b'Invented retained admission failure\n')
    failure=parse_json((output/'FAILURE.json').read_bytes());elapsed=failure['wall_seconds']+.1
    report=dict(schema_version=1,method='tether.process_envelope.v1',limits=dict(timeout_seconds=150,max_output_bytes=4*1024**2),
        termination_reason='exited',execution_elapsed_seconds=elapsed,total_elapsed_seconds=elapsed,
        retained_stdout_bytes=0,retained_stderr_bytes=(launch/'stderr.bin').stat().st_size,
        observed_stdout_bytes=0,observed_stderr_bytes=(launch/'stderr.bin').stat().st_size,
        observed_counts_are_lower_bounds=False,pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[])
    write(launch/'PROCESS.json',dict(returncode=1,supervision=report))
    command=[sys.executable,'-I','-B',str(e.ROOT/'experiments/scifact_calibration/evaluate.py'),'execute',
        '--frame',str(path),'--frame-sha256',proof(path)['sha256'],'--output',str(output)]
    write(launch/'COMMAND.json',command)
    snapshot_root=root/'snapshot';snapshot_root.mkdir();archive=[]
    for index,item in enumerate(frame['code_files']):
        target=snapshot_root/f'{index:03d}.bin';target.write_bytes(Path(item['path']).read_bytes())
        archive.append(dict(original=item,archived=proof(target)))
    snapshot=dict(schema_version=1,kind=r.SNAPSHOT,root=str(output),files=inventory(output),original_frame=proof(path),
        launch=dict(root=str(launch),files=inventory(launch)),executed_source=archive,
        scope='Invented failed-process fixture; no actual scientific outcomes or subprocess claim.')
    snap_path=snapshot_root/'SNAPSHOT.json';write(snap_path,snapshot)
    current=dict(frame,output=str(root/'recovered'));current_path=root/'current-evaluation.json';write(current_path,current)
    recovery=dict(schema_version=1,kind=r.KIND,purpose='evaluate',evaluation_frame=proof(current_path),parent_snapshot=proof(snap_path),
        code_files=[proof(p) for p in r.required_code()],environment=e.environment(),qualification=None,output=current['output'])
    recovery_path=root/'recovery-frame.json';write(recovery_path,recovery)
    return recovery_path,recovery,snap_path,snapshot


def reseal(root):
    value=parse_json((root/'RECEIPT.json').read_bytes());value['files']=inventory(root);value['files'].pop('RECEIPT.json')
    return write(root/'RECEIPT.json',value)['sha256']


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        folder=e.ROOT/'tmp';folder.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path,self.frame,self.snapshot_path,self.snapshot=failed_parent(self.root)
        self.output=Path(self.frame['output']);self.parent=Path(self.snapshot['root'])
    def execute(self,**kwargs):return r.execute(self.path,proof(self.path)['sha256'],output=self.output,**kwargs)
    def verify(self):return r.verify(self.output,proof(self.output/'RECEIPT.json')['sha256'])
    def anchor(self):
        write(self.snapshot_path,self.snapshot);self.frame['parent_snapshot']=proof(self.snapshot_path);write(self.path,self.frame)
    def resnapshot_parent(self):self.snapshot['files']=inventory(self.parent);self.anchor()
    def test_reuses_exact_map_without_any_refit_and_preserves_original_failure(self):
        before=inventory(self.parent);launch=inventory(Path(self.snapshot['launch']['root']))
        with (patch.object(c,'fit_coefficients',side_effect=AssertionError('Recovery refit')),
              patch.object(c,'fit_calibration',side_effect=AssertionError('Recovery refit')),
              patch.object(e,'_fit_partition',side_effect=AssertionError('Recovery refit'))):
            result=self.execute();verified=self.verify()
        self.assertEqual(result['new_fits'],0);self.assertEqual(result['model_calls'],0)
        self.assertTrue(verified['arithmetic_consistency']);self.assertTrue(verified['source_consistency'])
        self.assertEqual(result['original_fits_reused'],6)
        self.assertEqual(before,inventory(self.parent));self.assertEqual(launch,inventory(Path(self.snapshot['launch']['root'])))
        self.assertFalse((self.parent/'RECEIPT.json').exists());self.assertTrue((self.parent/'FAILURE.json').exists())
        self.assertFalse((self.output/'MAPPING.json').exists())
        derived=parse_json((self.output/'DEVELOPMENT-FRAME.json').read_bytes())
        self.assertEqual(derived['sealed_mapping'],proof(self.parent/'MAPPING.json'))
        self.assertEqual(parse_json((self.output/'BOOTSTRAP.json').read_bytes())['completed_replicates'],10000)
    def test_unanchored_parent_change_and_extra_file_block_before_reservation(self):
        target=self.parent/'MAPPING.json';before=target.read_bytes();target.write_bytes(before+b' ')
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.output.exists());target.write_bytes(before)
        (self.parent/'unexpected.txt').write_text('unexpected')
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse(self.output.exists())
    def test_missing_executed_source_or_terminal_capture_block_before_reservation(self):
        original=deepcopy(self.snapshot)
        for change in ('source','stderr','process'):
            self.snapshot=deepcopy(original)
            if change=='source':self.snapshot['executed_source'].pop()
            elif change=='stderr':self.snapshot['launch']['files'].pop('stderr.bin')
            else:
                path=Path(self.snapshot['launch']['files']['PROCESS.json']['path']);terminal=parse_json(path.read_bytes())
                terminal['returncode']=0;write(path,terminal);self.snapshot['launch']['files']=inventory(path.parent)
            self.anchor()
            with self.subTest(change=change),self.assertRaises(ValueError):self.execute()
            self.assertFalse(self.output.exists())
    def test_reanchored_incomplete_fit_fails_before_development(self):
        path=self.parent/'fits/001-result.json';value=parse_json(path.read_bytes());value['fit']['status']='failed';write(path,value)
        self.resnapshot_parent();reader=r.o.reconstruct_partition;seen=[]
        def watched(path,sha):
            seen.append(parse_json(Path(path).read_bytes())['partition']);return reader(path,sha)
        with patch.object(r.o,'reconstruct_partition',side_effect=watched):
            with self.assertRaisesRegex(ValueError,'fit artifact'):self.execute()
        self.assertEqual(seen,['calibration']);self.assertTrue((self.output/'FAILURE.json').exists())
        self.assertFalse((self.output/'DEVELOPMENT-FRAME.json').exists())
    def test_original_and_current_source_proof_closures_must_agree(self):
        reader=r.o.reconstruct_partition
        def omitted(path,sha):
            result=reader(path,sha);return replace(result,proofs=result.proofs[:-1])
        with patch.object(r.o,'reconstruct_partition',side_effect=omitted):
            with self.assertRaisesRegex(ValueError,'source proof closure'):
                r._adopt(r._metadata(self.path,proof(self.path)['sha256'],self.output))
    def test_reanchored_map_suite_or_seal_tampering_rejects(self):
        for filename,key,value in (('MAPPING.json','a',123),('CALIBRATION-SUITE.json','held_out_scores',[]),
                                   ('MAPPING-RECEIPT.json','fits',1)):
            with self.subTest(file=filename):
                path=self.parent/filename;before=path.read_bytes();data=parse_json(before);data[key]=value;write(path,data);self.resnapshot_parent()
                with self.assertRaises(ValueError):r._adopt(r._metadata(self.path,proof(self.path)['sha256'],self.output))
                path.write_bytes(before);self.resnapshot_parent()
    def test_reanchored_seal_order_cannot_be_changed(self):
        path=self.parent/'journal.jsonl';events=e._journal(path.read_bytes());events[-3],events[-2]=events[-2],events[-3];previous=None
        for index,event in enumerate(events):
            event.pop('sha256');event['sequence']=index;event['previous_sha256']=previous;previous=e.digest(canonical(event));event['sha256']=previous
        path.write_bytes(b''.join(canonical(row)+b'\n' for row in events));self.resnapshot_parent()
        with self.assertRaisesRegex(ValueError,'seal must precede'):self.execute()
        self.assertFalse((self.output/'DEVELOPMENT-FRAME.json').exists())
    def test_changed_scientific_partition_or_settings_fail_before_reservation(self):
        path=Path(self.frame['evaluation_frame']['path']);current=parse_json(path.read_bytes());current['limits']['phase_seconds']=121
        self.frame['evaluation_frame']=write(path,current);write(self.path,self.frame)
        with self.assertRaisesRegex(ValueError,'scientific evaluation settings'):self.execute()
        self.assertFalse(self.output.exists())
    def test_unexpected_or_changed_archive_bytes_reject_without_execution(self):
        archive=self.snapshot['executed_source'][0]['archived'];path=Path(archive['path']);path.write_bytes(b'raise AssertionError("never executed")\n')
        archive.update(proof(path));self.anchor()
        with self.assertRaisesRegex(ValueError,'Archived source byte identity'):self.execute()
        self.assertFalse(self.output.exists())
    def test_deadline_and_interruption_retain_terminal_without_fit_or_resume(self):
        ticks=iter([0.,121.,121.])
        with patch.object(c,'fit_coefficients') as fitting:
            with self.assertRaisesRegex(ValueError,'deadline'):self.execute(_clock=lambda:next(ticks))
            fitting.assert_not_called()
        self.assertTrue((self.output/'FAILURE.json').exists());self.assertFalse((self.output/'RECEIPT.json').exists())
        with self.assertRaisesRegex(ValueError,'fresh'):self.execute()
    def test_atomic_write_failure_preserves_parent_and_partial_failure(self):
        before=inventory(self.parent);publish=r.atomic.publish_bytes
        def failed(path,raw,**kwargs):
            if Path(path).name=='DEVELOPMENT-INPUTS.json':raise OSError('Invented output failure')
            return publish(path,raw,**kwargs)
        with patch.object(r.atomic,'publish_bytes',side_effect=failed):
            with self.assertRaises(OSError):self.execute()
        self.assertEqual(before,inventory(self.parent));self.assertTrue((self.output/'FAILURE.json').exists())
        self.assertFalse((self.output/'RECEIPT.json').exists())
    def test_interruption_leaves_no_success_and_cannot_repeat_output(self):
        with patch.object(r,'_adopt',side_effect=KeyboardInterrupt('Invented recovery interruption')):
            with self.assertRaises(KeyboardInterrupt):self.execute()
        failure=parse_json((self.output/'FAILURE.json').read_bytes())
        self.assertEqual(failure['status'],'interrupted');self.assertEqual(failure['new_fits'],0)
        self.assertFalse((self.output/'RECEIPT.json').exists())
        with self.assertRaises(ValueError):self.execute()
    def test_changed_original_external_frame_at_finalization_cannot_seal(self):
        reports=e._reports
        def changed(*args,**kwargs):
            result=reports(*args,**kwargs);path=Path(self.snapshot['original_frame']['path'])
            path.write_bytes(path.read_bytes()+b' ');return result
        with patch.object(e,'_reports',side_effect=changed):
            with self.assertRaises(ValueError):self.execute()
        self.assertTrue((self.output/'FAILURE.json').exists());self.assertFalse((self.output/'RECEIPT.json').exists())
    def test_concurrent_fresh_output_has_only_one_adoption(self):
        entered=threading.Event();release=threading.Event();adopt=r._adopt;calls=[]
        def watched(metadata):calls.append(1);entered.set();self.assertTrue(release.wait(15));return adopt(metadata)
        with patch.object(r,'_adopt',side_effect=watched),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.execute);self.assertTrue(entered.wait(15))
            try:
                with self.assertRaises((ValueError,FileExistsError)):self.execute()
            finally:release.set()
            self.assertEqual(first.result(timeout=45)['status'],'complete')
        self.assertEqual(calls,[1])
    def test_resealed_statistics_accounting_and_failure_cannot_claim_success(self):
        self.execute()
        for filename,key,value in (('REPORT.json','new_fits',1),('REPORT.json','wall_seconds',-1),
                                   ('BOOTSTRAP.json','completed_replicates',9999),('ADOPTION.json','original_attempt_remains_failed',False)):
            path=self.output/filename;before=path.read_bytes();data=parse_json(before);data[key]=value;write(path,data);sha=reseal(self.output)
            with self.subTest(file=filename,key=key),self.assertRaises(ValueError):r.verify(self.output,sha)
            path.write_bytes(before);reseal(self.output)
        write(self.output/'FAILURE.json',dict(status='failed'));sha=reseal(self.output)
        with self.assertRaisesRegex(ValueError,'Completed recovery'):r.verify(self.output,sha)
    def test_cli_isolated_imports(self):
        result=subprocess.run([sys.executable,'-I','-B',r.__file__,'--help'],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'verify',result.stdout)


if __name__=='__main__':unittest.main()
