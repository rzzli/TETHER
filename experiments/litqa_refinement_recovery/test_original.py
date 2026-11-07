"""Invented failed parent, strict historical adoption and source/native negatives."""
import copy
from datetime import datetime,timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import encode
from experiments.litqa_refinement import envelopes as e,pipeline
from experiments.litqa_refinement import test_envelopes as fixture_module
from experiments.litqa_refinement.test_envelopes import write,proof,inventory,chain
from experiments.litqa_refinement_recovery import original as o


class FailedFixture:
    """Only fictional source/native captures; no live transport, model or keys."""
    complete_history=True
    failed_ordinal=0

    def phase(self,phase):
        if phase in o.PREFIX:return super().phase(phase)
        if phase=='removal':return
        pr=self.root/phase;pr.mkdir();wr=pr/'worker'
        base=Path(self.f.baseline.root);br=e.decode((base/'RECEIPT.json').read_bytes())
        grants={str(base/'RECEIPT.json'):proof(base/'RECEIPT.json')}
        for name in br['files']:grants[str(base/name)]=proof(base/name)
        for row in self.baseline['role_files']:grants[row['proof']['path']]=row['proof']
        grants.update(self.grants['pair_prepare'])
        job=dict(phase=phase,frame_sha256=self.fp['sha256'],parents={'pair_prepare':self.anchors['pair_prepare']},
            input_files=[grants[k] for k in sorted(grants)],model_bindings=self.model['bindings'],cutoff=None)
        write(pr/'JOB.json',job);jp=proof(pr/'JOB.json');journal=RunJournal(wr,kind='build')
        write(wr/'CONFIG.json',dict(frame_sha256=self.fp['sha256'],job_sha256=jp['sha256'],phase=phase,purpose='fictional_qualification',
            worker_pid=os.getpid(),python_version=sys.version,coordinator_grants=job['input_files']))
        write(wr/'MODEL.json',self.model);write(wr/'server/server-command.json',self.model['spec'])
        (wr/'server/server.stdout.log').write_bytes(b'');(wr/'server/server.stderr.log').write_bytes(b'')
        journal.append('server_started',pid=12345);journal.append('server_ready',pid=12345)
        original_body=self.history.fixture.native.f.native_body
        def limit_body(**kwargs):
            body=e.decode(original_body(**kwargs));body.update(tokens_predicted=256,stop_type='limit',stop=True,stopping_word='')
            for key in ('stopped_limit','stopped_word','stopped_eos'):body.pop(key,None)
            return e.canonical(body)
        caller=self.f.fake_model
        def selected_call(descriptor,output,deadline):
            if descriptor['query']['id']==self.frame['schedule'][self.failed_ordinal]:
                with patch.object(self.history.fixture.native.f,'native_body',side_effect=limit_body):return caller(descriptor,output,deadline)
            return caller(descriptor,output,deadline)
        with self.assertRaisesRegex(ValueError,'Unqualified native completion cause'):
            pipeline.execute('repair',self.f.baseline,wr/'phase',purpose='fictional_qualification',seconds=getattr(self,'repair_stage_seconds',120),
                parents={'pair_prepare':dict(root=str(Path(self.anchors['pair_prepare']['root'])/'worker/phase'),receipt_sha256=self.anchors['pair_prepare']['stage_receipt_sha256'])},
                model_provenance=self.model['provenance'],call_model=selected_call)
        elapsed=e.decode((wr/'phase/STAGE-RECEIPT.json').read_bytes())['seal_elapsed_seconds']+2
        terminal_server=dict(started=True,server_stopped=True,pid=12345,exit_code=1,secondary_failures=[],elapsed_seconds=elapsed-1,error_class='ContractError')
        journal.append('server_terminal',**terminal_server)
        journal.append('build_failed',error_class='ContractError',message='Unqualified native completion cause',stage='phase_execution');journal.close()
        write(wr/'FAILURE.json',dict(automatic_retry=False,error_type='ContractError',message='Unqualified native completion cause',
            stage='phase_execution',server_terminal=terminal_server,wall_seconds=elapsed))
        audit=[dict(path=jp['path'],mode='r',flags=0,allowed=True,basis='coordinator_input',role='coordinator')]
        for n in range(self.failed_ordinal+1):
            cell=wr/'phase/products'/f'{n:04d}'
            audit.extend([dict(event='actor_entered',role=phase,output=str(cell),coordinator_inputs_granted=False),
                dict(path=str(cell/('FAILURE.json' if n==self.failed_ordinal else 'SUMMARY.json')),mode='w',flags=os.O_WRONLY,allowed=True,basis='role_output',role=phase),
                dict(event='actor_exited',role=phase,output=str(cell))])
        (wr/'io-audit.jsonl').write_bytes(b''.join(e.canonical(r)+b'\n' for r in audit))
        command=[self.frame['interpreter']['path'],'-I','-B','-c',e.LAUNCHER,str(e.REPO),str(e.REPO/'src'),str(e.REPO/'packages/tether/src'),
            '--worker','--frame',self.fp['path'],'--frame-sha256',self.fp['sha256'],'--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(wr)]
        limits=dict(timeout_seconds=660,max_output_bytes=4*1024**2)
        write(pr/'COMMAND.json',command);(pr/'stdout.bin').write_bytes(b'');(pr/'stderr.bin').write_bytes(b'')
        self.process=dict(returncode=1,supervision=dict(schema_version=1,method='tether.process_envelope.v1',limits=limits,
            termination_reason='exited',process_started=True,process_reaped=True,pipe_eof=dict(stdout=True,stderr=True),cleanup_errors=[],
            observed_counts_are_lower_bounds=False,retained_stdout_bytes=0,observed_stdout_bytes=0,retained_stderr_bytes=0,observed_stderr_bytes=0,
            execution_elapsed_seconds=elapsed+1,total_elapsed_seconds=elapsed+1))
        write(pr/'PROCESS.json',self.process)
        self.root_events.append(('refinement_phase_reserved',dict(phase=phase,job=jp,command=command,limits=limits)))

    def reseal(self):
        elapsed=1+sum(e.decode((self.root/p/'PROCESS.json').read_bytes())['supervision']['execution_elapsed_seconds'] for p in (*o.PREFIX,'repair'))
        write(self.root/'FAILURE.json',dict(automatic_retry=False,completed_phases=self.anchors,error_type='ValueError',
            message='Refinement worker failed; no automatic retry',stage='repair',wall_seconds=elapsed))
        chain(self.root/'journal.jsonl',self.root_events+[('build_failed',dict(error_class='ValueError',message='Refinement worker failed; no automatic retry',stage='repair'))])
        self.frozen=self.base/'frozen';self.frozen.mkdir()
        write(self.frozen/'FRAME.json',self.frame);write(self.frozen/'FAILURE.json',dict(status='fictional_failed'))
        process=copy.deepcopy(self.process);process['supervision'].update(limits=dict(timeout_seconds=43200,max_output_bytes=4*1024**2),
            execution_elapsed_seconds=elapsed+1,total_elapsed_seconds=elapsed+1)
        write(self.frozen/'launch/PROCESS.json',process)
        (self.frozen/'launch/stdout.bin').write_bytes(b'');(self.frozen/'launch/stderr.bin').write_bytes(b'')
        archive=self.base/'source-archive';archive.mkdir();pins={}
        for i,p in enumerate(self.frame['code_files']):
            target=archive/f'{i:04d}.source';target.write_bytes(Path(p['path']).read_bytes())
            pins[Path(p['path']).relative_to(e.REPO).as_posix()]=proof(target)
        write(archive/'MANIFEST.json',dict(schema_version=1,kind='sc04_executed_source_archive_v1',original_repository_root=str(e.REPO),files=pins))
        self.archive=proof(archive/'MANIFEST.json');self.inspection=self.inspect_new('inspection')

    def inspect_new(self,name):
        folder=self.base/name;folder.mkdir()
        for file,root in (('ORIGINAL-INVENTORY.json',self.root),('FREEZE-INVENTORY.json',self.frozen)):
            write(folder/file,dict(root=str(root),files=inventory(root),directories=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())))
        write(folder/'RESULT.json',dict(kind='sc05_failed_production_metadata_forensics_v1',status='metadata_and_byte_inventory_verified',
            original_root=str(self.root),freeze_root=str(self.frozen),original_frame=proof(self.root/'FRAME.json'),original_failure=proof(self.root/'FAILURE.json')))
        write(folder/'RECEIPT.json',dict(kind='sc05_failed_production_metadata_audit_receipt_v1',status='complete',files=inventory(folder)))
        return proof(folder/'RECEIPT.json')

    def verify_parent(self,inspection=None):
        return o.reconstruct(inspection or self.inspection,self.archive,baseline_acceptance=self.acceptance)


@unittest.skipUnless(os.name == 'nt', 'native held-handle test requires Windows')
class OriginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache=e.REPO/'data/cache';cache.mkdir(parents=True,exist_ok=True)
        fixture_type=type('FailedNativeFixture',(FailedFixture,fixture_module.EnvelopeTests),{})
        cls.f=fixture_type('runTest');cls.addClassCleanup(cls.f.doCleanups)
        with patch.object(tempfile,'tempdir',str(cache)):cls.f.setUp()

    def test_source_inclusive_parent_and_frozen_capability(self):
        value=self.f.verify_parent();p=value.payload
        self.assertEqual(p['schedule'],tuple(self.f.frame['schedule']))
        self.assertEqual(p['untouched_repair_ordinals'],(1,));self.assertEqual(p['untouched_removal_ordinals'],(0,1))
        self.assertEqual(p['failed_call']['producer_status'],'error');self.assertIsNone(p['failed_call']['prediction'])
        self.assertIsNone(p['failed_call']['qualified_usage']);self.assertFalse(p['failed_call']['original_usage_verified'])
        self.assertEqual(p['failed_call']['raw_reported_usage']['output_tokens'],256)
        with self.assertRaises(TypeError):p['failed_call']['raw_reported_usage']['output_tokens']=0
        self.assertTrue(o.revalidate(value))
        copied=o.VerifiedParent(value.payload,value._fingerprint,value._token)
        with self.assertRaisesRegex(ValueError,'Issued'):o.revalidate(copied)

    def test_wrong_external_inspection_and_archive(self):
        for which in ('inspection','archive'):
            args=[dict(self.f.inspection),dict(self.f.archive)];args[0 if which=='inspection' else 1]['sha256']='0'*64
            with self.subTest(which=which),self.assertRaises(ValueError):o.reconstruct(*args,baseline_acceptance=self.f.acceptance)

    def test_cleared_verifier_trackers_cannot_hide_changed_parent(self):
        value=self.f.verify_parent();state=o._state(value)
        mutable=state.get('inputs')
        if mutable is not None:
            mutable.proofs.clear();mutable.inventories.clear()
        target=self.f.root/'repair/worker/phase/products/0000/native/native-response.bin';raw=target.read_bytes()
        try:
            target.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):o.revalidate(value)
        finally:target.write_bytes(raw)

    def test_stale_source_inventory_cannot_be_resealed_implicitly(self):
        target=self.f.root/'repair/worker/server/server.stdout.log';raw=target.read_bytes()
        try:
            target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'inventory'):self.f.verify_parent()
        finally:target.write_bytes(raw)

    def test_resealed_extra_root_artifact_rejected(self):
        target=self.f.root/'EXTRA.json';target.write_bytes(b'{}')
        try:
            new=self.f.inspect_new('extra-inspection')
            with self.assertRaisesRegex(ValueError,'membership'):self.f.verify_parent(new)
        finally:target.unlink()

    def test_false_success_and_removal_presence_rejected(self):
        target=self.f.root/'COMPLETE.json';target.write_bytes(b'{}')
        try:
            new=self.f.inspect_new('false-success-inspection')
            with self.assertRaisesRegex(ValueError,'membership'):self.f.verify_parent(new)
        finally:target.unlink()

    def test_partial_stage_rejects_inserted_untouched_call(self):
        root=self.f.root/'repair/worker/phase';target=root/'products/0001';target.mkdir()
        try:
            inputs=e.accepted_primary._Inputs();sp=proof(root/'STAGE-RECEIPT.json');job=e.decode((self.f.root/'repair/JOB.json').read_bytes())
            with self.assertRaises(ValueError):o._partial_stage(root,sp,self.f.frame,job,inputs,100,101)
        finally:target.rmdir()

    def test_partial_stage_resealed_orphan_outside_schedule_rejected(self):
        import shutil
        temp=tempfile.TemporaryDirectory(dir=e.REPO/'data/cache');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve()/'copied-stage'
        shutil.copytree(self.f.root/'repair/worker/phase',root)
        write(root/'products/0999/unlisted-call.json',dict(scope='invented orphan outside complete schedule'))
        receipt=e.decode((root/'STAGE-RECEIPT.json').read_bytes())
        receipt['files']={n:{k:p[k] for k in ('bytes','sha256')} for n,p in inventory(root,omit=('STAGE-RECEIPT.json',)).items()}
        write(root/'STAGE-RECEIPT.json',receipt)
        job=e.decode((self.f.root/'repair/JOB.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'membership'):
            o._partial_stage(root,proof(root/'STAGE-RECEIPT.json'),self.f.frame,job,e.accepted_primary._Inputs(),100,101)

    def test_forged_capability_and_nonreaped_process_rejected(self):
        with self.assertRaises(ValueError):o.revalidate(o.VerifiedParent({},e.fingerprint({}),o._TOKEN))
        value=copy.deepcopy(self.f.process);value['supervision']['process_reaped']=False
        with self.assertRaisesRegex(ValueError,'cleanup'):o._terminated(value,self.f.root/'repair',{},None,value['supervision']['limits'],1)


if __name__=='__main__':unittest.main()
