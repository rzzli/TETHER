"""Invented process/audit envelopes with real two-slot stage verification."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, encode, fingerprint, parse_json
from experiments.litqa_comparison.pipeline import proof
from experiments.litqa_comparison.run import inventory
from . import phase_checks as p, schedule


IDS = ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002')


class PhaseChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(canonical(value)+b'\n')

    def fixture(self,phase='critic'):
        output=self.base/phase
        package=output/phase
        package.mkdir(parents=True)
        frame=dict(kind='sc05_refinement_execution_v1',output=str(output),schedule=IDS,
            purpose='fictional_qualification',phase_seconds={name:600 for name in schedule.PHASES},
            interpreter=dict(path=str(Path(sys.executable).absolute()),bytes=0,sha256='a'*64),
            provider_spend_usd=0,automatic_retry=False,code_files=[],
            model_receipt=dict(path=str(self.base/'model-receipt.json'),bytes=0,sha256='b'*64),
            model_license=dict(path=str(self.base/'LICENSE'),bytes=0,sha256='c'*64),
            model_spec={'fictional':True},model_provenance={'fictional':True},alias='invented-model',
            baseline=dict(root=str(self.base/'baseline'),receipt_sha256='d'*64))
        self.write(output/'FRAME.json',frame)
        frame_sha=proof(output/'FRAME.json')['sha256']
        parents={}
        for name in schedule.PARENTS[phase]:
            parent=output/name
            self.write(parent/'worker/phase/STAGE-RECEIPT.json',{'fictional':True})
            parent_receipt=dict(status='complete',phase=name,frame_sha256=frame_sha,
                files={'worker/phase/STAGE-RECEIPT.json':proof(parent/'worker/phase/STAGE-RECEIPT.json')})
            self.write(parent/'PACKAGE-RECEIPT.json',parent_receipt)
            parents[name]=dict(root=str(parent),package_sha256=proof(parent/'PACKAGE-RECEIPT.json')['sha256'],
                stage_receipt_sha256=proof(parent/'worker/phase/STAGE-RECEIPT.json')['sha256'])
        job=dict(phase=phase,frame_sha256=frame_sha,parents=parents,input_files=[],model_bindings={},
                 cutoff='2099-01-01T00:00:00+00:00' if phase=='pair_prepare' else None)
        self.write(package/'JOB.json',job)
        job_sha=proof(package/'JOB.json')['sha256']
        if phase=='removal':
            repair=output/'repair';other=dict(job,phase='repair')
            self.write(repair/'JOB.json',other)
            self.write(repair/'PACKAGE-RECEIPT.json',dict(status='complete',phase='repair',frame_sha256=frame_sha,
                files={'JOB.json':proof(repair/'JOB.json')}))
            self.write(output/'repair-ANCHOR.json',dict(root=str(repair),package_sha256=proof(repair/'PACKAGE-RECEIPT.json')['sha256'],
                                                      stage_receipt_sha256='f'*64))
        worker=package/'worker'
        journal=RunJournal(worker,kind='build')
        config=dict(frame_sha256=frame_sha,job_sha256=job_sha,phase=phase,purpose=frame['purpose'],
                    worker_pid=os.getpid(),python_version=sys.version,coordinator_grants=[])
        self.write(worker/'CONFIG.json',config)
        self.write(worker/'MODEL.json',dict(spec=frame['model_spec'],bindings={},provenance=frame['model_provenance'],alias=frame['alias']))
        stage=schedule.Stage(IDS,phase,worker/'phase',purpose='fictional_qualification',seconds=500)
        self.write(worker/'phase/INPUTS.json',dict(baseline=frame['baseline'],
            parents={name:dict(root=str(output/name/'worker/phase'),receipt_sha256=value['stage_receipt_sha256']) for name,value in parents.items()},
            cutoff=job['cutoff'],model_provenance=frame['model_provenance'],reference_keys_available=False,scoring_performed=False))
        for _ in IDS:
            def operation(slot,end):
                usage=encode(schedule.zero_accounting())
                if phase in p.MODELS:
                    usage.update(generation_calls=1,reserved_input_tokens=50,reserved_output_tokens=256,
                                 measured_input_tokens=10,measured_output_tokens=20)
                elif phase=='refinement_collect':
                    usage.update(source_http_requests=2,measured_response_bytes=12,safety_accounted_bytes=12)
                return dict(status='completed',reason=None,product={},accounting=usage)
            stage.call(operation)
        stage.finish()
        server=None
        if phase in p.MODELS:
            server=dict(started=True,server_stopped=True,exit_code=0,secondary_failures=[],
                peak_native_memory_bytes=None,peak_native_memory_reason='Not instrumented',pid=123,elapsed_seconds=1)
            journal.append('server_started',pid=123);journal.append('server_ready',pid=123)
            journal.append('server_terminal',**server)
        terminal=dict(status='complete',phase=phase,purpose=frame['purpose'],frame_sha256=frame_sha,
            stage_receipt=proof(worker/'phase/STAGE-RECEIPT.json'),wall_seconds=5,worker_memory=None,
            server_terminal=server,audit_denials=0,provider_cost_usd=0,reference_keys_read=False,scientific_scoring_performed=False)
        self.write(worker/'COMPLETE.json',terminal)
        journal.append('refinement_worker_completed',terminal_sha256=fingerprint(terminal));journal.close()
        audit=[dict(path=str(worker/'MODEL.json'),mode='r',flags=os.O_RDONLY,allowed=True,basis='role_output',role='coordinator')]
        if phase in p.MODELS:
            for ordinal in range(2):
                target=worker/'phase/products'/f'{ordinal:04d}'
                audit.extend([dict(event='actor_entered',role=phase,output=str(target),coordinator_inputs_granted=False),
                    dict(path=str(target/'INPUT.json'),mode='w',flags=os.O_WRONLY|os.O_CREAT|os.O_TRUNC,
                         allowed=True,basis='role_output',role=phase),
                    dict(event='actor_exited',role=phase,output=str(target))])
        (worker/'io-audit.jsonl').write_bytes(b''.join(canonical(row)+b'\n' for row in audit))
        (package/'stdout.bin').write_bytes(b'fictional process completed\n')
        (package/'stderr.bin').write_bytes(b'')
        process=dict(returncode=0,supervision=dict(schema_version=1,method='tether.process_envelope.v1',
            limits=dict(timeout_seconds=660,max_output_bytes=4*1024**2),termination_reason='exited',
            execution_elapsed_seconds=6,total_elapsed_seconds=6,retained_stdout_bytes=28,retained_stderr_bytes=0,
            observed_stdout_bytes=28,observed_stderr_bytes=0,observed_counts_are_lower_bounds=False,
            pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[]))
        process['supervision']['retained_stdout_bytes']=process['supervision']['observed_stdout_bytes']=len((package/'stdout.bin').read_bytes())
        self.write(package/'PROCESS.json',process)
        repository=Path(p.__file__).resolve().parents[2]
        self.write(package/'COMMAND.json',[frame['interpreter']['path'],'-I','-B','-c',p.LAUNCHER,str(repository),str(repository/'src'),
            str(repository/'packages/tether/src'),'--worker','--frame',str(output/'FRAME.json'),'--frame-sha256',frame_sha,
            '--job',str(package/'JOB.json'),'--job-sha256',job_sha,'--output',str(worker)])
        return package,frame,job

    def verify(self,root):
        frame_sha=proof(root.parent/'FRAME.json')['sha256']
        receipt=dict(phase=root.name,frame_sha256=frame_sha,files=inventory(root))
        stage=schedule.verify(root/'worker/phase',proof(root/'worker/phase/STAGE-RECEIPT.json')['sha256'],
                              expected_ids=IDS,expected_phase=root.name,purpose='fictional_qualification')
        return p.verify_phase(root,receipt,stage)

    def mutate(self,path,fn):
        value=parse_json(path.read_bytes());fn(value);self.write(path,value)

    def test_real_child_stages_all_five_phases_reconcile_without_dispatch(self):
        for phase in schedule.PHASES:
            with self.subTest(phase=phase):
                root,_,_=self.fixture(phase)
                checked=self.verify(root)
                self.assertEqual(checked['scheduled'],2)
                self.assertEqual(checked['audit']['completed_actor_scopes'],2 if phase in p.MODELS else 0)
                self.assertFalse(checked['scientific_source_validation'])

    def test_nonzero_process_bad_reap_and_stream_accounting_are_rejected(self):
        root,_,_=self.fixture();path=root/'PROCESS.json';original=path.read_bytes()
        changes=(lambda x:x.update(returncode=3),lambda x:x['supervision'].update(process_reaped=False),
                 lambda x:x['supervision'].update(observed_stdout_bytes=0),
                 lambda x:x['supervision'].update(termination_reason='deadline_exceeded'),
                 lambda x:x['supervision']['limits'].update(timeout_seconds=900))
        for fn in changes:
            path.write_bytes(original);self.mutate(path,fn)
            with self.assertRaises(ValueError):self.verify(root)

    def test_worker_elapsed_cannot_exceed_its_supervised_process(self):
        root,_,_=self.fixture()
        self.mutate(root/'PROCESS.json',lambda value:value['supervision'].update(
            execution_elapsed_seconds=4,total_elapsed_seconds=4))
        with self.assertRaisesRegex(ValueError,'Worker elapsed exceeds supervised process'):
            self.verify(root)

    def test_negative_overtime_nonfinite_worker_time_and_server_failure_rejected(self):
        root,_,_=self.fixture();path=root/'worker/COMPLETE.json';original=path.read_bytes()
        changes=(lambda x:x.update(wall_seconds=-1),lambda x:x.update(wall_seconds=600),
                 lambda x:x['server_terminal'].update(secondary_failures=[{'stage':'stop'}]),
                 lambda x:x['server_terminal'].update(server_stopped=False))
        for fn in changes:
            path.write_bytes(original);self.mutate(path,fn)
            with self.assertRaises(ValueError):self.verify(root)
        with self.assertRaises(ValueError):p._finite(float('nan'),'not finite')

    def test_hash_valid_failed_journal_and_changed_terminal_binding_rejected(self):
        root,_,_=self.fixture();path=root/'worker/journal.jsonl';original=path.read_bytes()
        events=[parse_json(line) for line in original.splitlines()]
        events[-1]['event']='build_failed';events[-1]['details']={'stage':'finalization','error_class':'OSError'}
        events[-1].pop('sha256');events[-1]['sha256']=fingerprint(events[-1])
        path.write_bytes(b''.join(canonical(row)+b'\n' for row in events))
        with self.assertRaisesRegex(ValueError,'journal'):self.verify(root)
        path.write_bytes(original)
        self.mutate(root/'worker/COMPLETE.json',lambda x:x.update(worker_memory={'invented':True}))
        with self.assertRaisesRegex(ValueError,'fingerprint'):self.verify(root)

    def test_actual_denial_and_false_allowed_input_read_under_actor_rejected(self):
        root,_,_=self.fixture();path=root/'worker/io-audit.jsonl';original=path.read_bytes()
        rows=[parse_json(line) for line in original.splitlines()]
        for change in (dict(allowed=False),dict(path=str(root/'JOB.json'),basis='coordinator_input',mode='r',flags=0),
                       dict(path=str(root/'worker/phase/products/0001/INPUT.json')),
                       dict(mode='r'),dict(role='coordinator')):
            changed=[dict(row) for row in rows];changed[2].update(change)
            path.write_bytes(b''.join(canonical(row)+b'\n' for row in changed))
            with self.assertRaises(ValueError):self.verify(root)

    def test_missing_duplicate_misordered_unclosed_actor_scopes_rejected(self):
        root,_,_=self.fixture();path=root/'worker/io-audit.jsonl';rows=[parse_json(x) for x in path.read_bytes().splitlines()]
        for changed in (rows[:1],rows+rows[1:4],rows[:1]+rows[4:]+rows[1:4],rows[:-1],[]):
            path.write_bytes(b''.join(canonical(row)+b'\n' for row in changed))
            with self.assertRaises(ValueError):self.verify(root)

    def test_config_job_command_and_parent_roles_rejected_after_resealing(self):
        root,_,_=self.fixture('pair_prepare')
        for name,fn in (('worker/CONFIG.json',lambda x:x.update(job_sha256='0'*64)),
                        ('COMMAND.json',lambda x:x.__setitem__(-1,str(root/'other'))),
                        ('JOB.json',lambda x:x['parents'].update(repair=x['parents']['critic']))):
            path=root/name;old=path.read_bytes();self.mutate(path,fn)
            with self.assertRaises(ValueError):self.verify(root)
            path.write_bytes(old)

    def test_raw_removal_requires_identical_pre_generation_parent(self):
        root,_,_=self.fixture('removal');other=root.parent/'repair/JOB.json'
        self.mutate(other,lambda x:x['parents']['pair_prepare'].update(stage_receipt_sha256='0'*64))
        package=root.parent/'repair/PACKAGE-RECEIPT.json'
        self.mutate(package,lambda x:x['files'].update({'JOB.json':proof(other)}))
        self.mutate(root.parent/'repair-ANCHOR.json',lambda x:x.update(package_sha256=proof(package)['sha256']))
        with self.assertRaisesRegex(ValueError,'share exact'):self.verify(root)

    def test_failure_marker_dominates_success_and_missing_audit_is_not_success(self):
        root,_,_=self.fixture();self.write(root/'worker/FINALIZATION-FAILED.json',{'error':'invented'})
        with self.assertRaisesRegex(ValueError,'Failure marker'):self.verify(root)
        (root/'worker/FINALIZATION-FAILED.json').unlink();(root/'worker/io-audit.jsonl').unlink()
        with self.assertRaisesRegex(ValueError,'artifact missing'):self.verify(root)

    def test_child_membership_cannot_be_substituted_in_parent_summary(self):
        root,frame,_=self.fixture()
        receipt=dict(phase=root.name,frame_sha256=proof(root.parent/'FRAME.json')['sha256'],files=inventory(root))
        stage=encode(schedule.verify(root/'worker/phase',proof(root/'worker/phase/STAGE-RECEIPT.json')['sha256']))
        stage['config']['ids']=list(reversed(frame['schedule']))
        with self.assertRaisesRegex(ValueError,'retained stage bytes'):p.verify_phase(root,receipt,stage)


if __name__=='__main__':unittest.main()
