"""Invented no-retry scheduling, stage sealing and process boundaries."""
from pathlib import Path
from types import SimpleNamespace
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from tether_engine.serde import canonical,encode,parse_json
from tether._process import EngineDeadlineExceeded
from . import contracts as c,run as r
from .test_contracts import payload

IDS=('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002')
OLD=('original-0','original-1')


def capacity(*_):return dict(status='capacity',reason='capacity',product={},accounting=encode(r.schedule.zero_accounting()))


class RecoveryStageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()

    def stage(self,ordinals=(1,),**kw):
        return r.RecoveryStage(IDS,'repair',ordinals,self.root/'stage',purpose='fictional_qualification',seconds=60,original_slots=OLD,**kw)

    def preflight_plan(self,planning,original,seconds):
        inspection=planning/'inspection';inspection.mkdir()
        rp=c.write(inspection/'RESULT.json',dict(kind='sc05_failed_production_metadata_forensics_v1',status='metadata_and_byte_inventory_verified',
            original_root=str(original),freeze_root=str(self.root/'original-freeze')))
        ip=c.write(inspection/'RECEIPT.json',dict(kind='sc05_failed_production_metadata_audit_receipt_v1',status='complete',files={'RESULT.json':rp}))
        archive=planning/'source-archive';archive.mkdir();ap=c.write(archive/'MANIFEST.json',{})
        replay=planning/'baseline-replay';replay.mkdir();analysis=planning/'analyzer-archive';analysis.mkdir();an=c.write(analysis/'MANIFEST.json',{})
        parent=dict(inspection=ip,source_archive=ap,baseline_acceptance=dict(replay_root=str(replay),receipt_sha256='0'*64,analyzer_archive=an))
        pp=c.write(planning/'PLAN.json',dict(parent=parent,original_root=str(original),budgets=dict(phase_remaining_seconds={'repair':seconds},outer_remaining_seconds=1000)))
        return pp,parent

    def verify(self,stage):
        return r.verify_stage(stage.root,c.capture(stage.root/'STAGE-RECEIPT.json')[0]['sha256'],ids=IDS,phase='repair',
            ordinals=stage.config['dispatch_ordinals'],purpose='fictional_qualification',original_slots=OLD)

    def test_only_untouched_original_ordinals_are_dispatched_and_replayed(self):
        stage=self.stage();seen=[];stage.call(lambda slot,end:(seen.append(slot['ordinal']) or capacity()));result=stage.finish()
        self.assertEqual(seen,[1]);self.assertEqual(result['scheduled'],1);self.assertEqual(self.verify(stage)['report'],result)
        with self.assertRaises(ValueError):stage.call(capacity)

    def test_uncertain_failure_stops_next_slot_and_retains_null_accounting(self):
        stage=self.stage((0,1));called=[]
        def failure(slot,end):called.append(slot['ordinal']);raise TimeoutError('invented uncertain transport')
        with self.assertRaises(TimeoutError):stage.call(failure)
        with self.assertRaises(ValueError):stage.call(failure)
        result=stage.finish();self.assertEqual(called,[0]);self.assertEqual(result['status'],'incomplete')
        self.assertEqual(result['rows'][1]['status'],'unexecuted');self.assertIsNone(result['rows'][0]['accounting'])
        self.assertTrue((stage.root/'failures/0000.json').is_file())

    def test_interruption_is_not_codec_failure(self):
        stage=self.stage()
        with self.assertRaises(KeyboardInterrupt):stage.call(lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
        result=stage.finish();self.assertEqual(result['rows'][0]['status'],'interrupted')

    def test_positively_authenticated_limit_has_null_measurement_and_next_slot(self):
        stage=self.stage((0,1))
        def failure(slot,end):
            proof=r.write(stage.root/'limit_failures/0000.json',dict(status='authenticated_limit_failure',prediction=None,qualified_usage=None,execution_id=slot['execution_id']))
            return dict(status='authenticated_limit_failure',reason='native_completion_limit',product=dict(limit_failure=proof),accounting=None)
        stage.call(failure);stage.call(capacity);result=stage.finish();accounting=result['accounting']
        self.assertEqual(accounting['authenticated_limit_generation_calls'],1);self.assertFalse(accounting['measurements_complete'])
        self.assertEqual(accounting['known_totals']['generation_calls'],0);self.assertEqual(self.verify(stage)['report'],result)

    def test_unbound_limit_descriptor_rejected_and_stops(self):
        stage=self.stage()
        with self.assertRaises((ValueError,KeyError)):
            stage.call(lambda *_:dict(status='authenticated_limit_failure',reason='limit',product={},accounting=None))
        self.assertEqual(stage.finish()['status'],'incomplete')

    def test_post_call_deadline_cannot_claim_success(self):
        clock=[0.0];stage=self.stage(clock=lambda:clock[0])
        def late(*_):clock[0]=61;return capacity()
        with self.assertRaises(ValueError):stage.call(late)
        self.assertEqual(stage.finish()['status'],'incomplete')

    def test_changed_row_even_with_new_receipt_rejected(self):
        stage=self.stage();stage.call(capacity);stage.finish();row=stage.root/'slots/0001.json'
        value=parse_json(row.read_bytes());value['id']=IDS[0];row.write_bytes(canonical(value))
        receipt=parse_json((stage.root/'STAGE-RECEIPT.json').read_bytes());receipt['files']=encode(r.inventory(stage.root,omit=('STAGE-RECEIPT.json',)))
        (stage.root/'STAGE-RECEIPT.json').write_bytes(canonical(receipt))
        with self.assertRaises(ValueError):self.verify(stage)

    def test_exclusive_output_collision_does_not_dispatch(self):
        stage=self.stage();stage.finish()
        with self.assertRaises(FileExistsError):self.stage()

    def test_actual_subprocess_success_and_timeout_preserve_output_without_retry(self):
        success=self.root/'success';success.mkdir()
        result=r.previous.supervised([sys.executable,'-I','-B','-c','print("invented terminal",flush=True)'],r.ProcessLimits(10,1024),success)
        self.assertEqual(result.returncode,0);self.assertEqual((success/'stdout.bin').read_bytes().strip(),b'invented terminal')
        failure=self.root/'timeout';failure.mkdir()
        with self.assertRaises(EngineDeadlineExceeded):
            r.previous.supervised([sys.executable,'-I','-B','-c','import time;print("reserved",flush=True);time.sleep(5)'],r.ProcessLimits(.5,1024),failure)
        self.assertTrue(parse_json((failure/'PROCESS.json').read_bytes())['supervision']['process_reaped'])

    def test_missing_worker_anchor_does_not_reserve_any_output(self):
        out=self.root/'output'
        with self.assertRaises(FileNotFoundError):r.worker(self.root/'absent','0'*64,self.root/'job','0'*64,out)
        self.assertFalse(out.exists())

    def test_stage_worker_process_clock_order_is_not_resealable(self):
        stage=dict(config={'seconds':60},seal_elapsed_seconds=50);terminal={'wall_seconds':55}
        process=dict(execution_elapsed_seconds=56,total_elapsed_seconds=57);job=dict(seconds=100,stage_seconds=60)
        r.worker_timing(stage,terminal,process,job)
        for wall in (10,-1,float('nan'),True):
            with self.subTest(wall=wall),self.assertRaises(ValueError):r.worker_timing(stage,{'wall_seconds':wall},process,job)
        with self.assertRaises(ValueError):r.worker_timing(stage,terminal,dict(execution_elapsed_seconds=56,total_elapsed_seconds=101),job)

    def test_phase_and_original_stage_verification_time_is_charged(self):
        value=dict(budgets=dict(phase_remaining_seconds=dict(repair=6419,removal=7200),outer_remaining_seconds=39018,repair_stage_remaining_seconds=6413))
        self.assertEqual(r.remaining_job_budgets(value,'repair',phase_elapsed=200,outer_elapsed=200),(6219,6129))
        self.assertEqual(r.remaining_job_budgets(value,'removal',phase_elapsed=50,outer_elapsed=1000),(7150,7060))
        with self.assertRaises(ValueError):r.remaining_job_budgets(value,'repair',phase_elapsed=6400,outer_elapsed=6400)

    def test_independent_stage_cap_does_not_charge_pre_stage_setup_twice(self):
        value=dict(budgets=dict(phase_remaining_seconds=dict(repair=6419,removal=7200),outer_remaining_seconds=39018,repair_stage_remaining_seconds=100))
        self.assertEqual(r.remaining_job_budgets(value,'repair',phase_elapsed=200,outer_elapsed=200),(6219,100))

    def test_parent_preflight_failure_is_retained_before_authority_or_dispatch(self):
        root=self.root/'data';root.mkdir();out=root/'recovery';planning=self.root/'planning';planning.mkdir()
        pp,parent=self.preflight_plan(planning,self.root/'original',600)
        authority=c.write(planning/'AUTHORITY.json',{})
        frame=dict(schema_version=2,kind=r.KIND,purpose='fictional_qualification',parent=parent,plan=pp,authority=authority,code_files=[],qualification=None,output=str(out))
        fp=c.write(planning/'FRAME.json',frame)
        with patch.object(r,'ROOT',self.root),patch.object(r,'load_frame',side_effect=ValueError('invented semantic rejection')),patch.object(r,'contain_process_tree'),patch.object(r,'DeadlineWatchdog') as watch,patch.object(r.previous,'supervised') as dispatch:
            with self.assertRaisesRegex(ValueError,'semantic rejection'):r.execute(fp['path'],fp['sha256'],output=out)
        dispatch.assert_not_called();self.assertTrue((out/'REQUEST.json').is_file());self.assertTrue((out/'FAILURE.json').is_file())
        self.assertFalse((planning/'EXECUTION').exists());self.assertEqual(watch.call_count,2)
        events=r.read_chain(out/'journal.jsonl');self.assertEqual(events[1]['event'],'recovery_preflight_started')

    def test_admission_allocation_reserves_startup_cleanup_and_one_cell(self):
        self.assertEqual(r.admission_seconds('production',5000),3600)
        self.assertEqual(r.admission_seconds('production',2000),1610)
        self.assertEqual(r.admission_seconds('fictional_qualification',5000),600)
        with self.assertRaises(ValueError):r.admission_seconds('production',390)

    def test_actual_preflight_watchdog_retains_request_before_slow_semantics(self):
        root=self.root/'data';root.mkdir();out=root/'slow';planning=self.root/'planning';planning.mkdir()
        pp,parent=self.preflight_plan(planning,self.root/'original',1)
        authority=c.write(planning/'AUTHORITY.json',{})
        frame=dict(schema_version=2,kind=r.KIND,purpose='fictional_qualification',parent=parent,plan=pp,authority=authority,code_files=[],qualification=None,output=str(out))
        fp=c.write(planning/'FRAME.json',frame);capture=self.root/'process';capture.mkdir()
        script='import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from experiments.litqa_refinement_recovery import run as r;'
        # Keep the actual subprocess/watchdog/retained timeout test portable.
        # Windows also exercises the real Job Object; other platforms mock only
        # that explicitly unsupported containment capability, never the timer.
        if os.name!='nt':script+='r.contain_process_tree=lambda:None;'
        script+='r.ROOT=Path(sys.argv[2]);r.load_frame=lambda *a,**kw:time.sleep(30);r.execute(sys.argv[3],sys.argv[4],output=sys.argv[5])'
        result=r.previous.supervised([sys.executable,'-I','-B','-c',script,str(r.ROOT),str(self.root),fp['path'],fp['sha256'],str(out)],r.ProcessLimits(10,4096),capture)
        self.assertEqual(result.returncode,124,result.stderr.decode('utf-8','replace'));self.assertTrue((out/'REQUEST.json').is_file());self.assertTrue((out/'repair-DEADLINE.json').is_file())
        self.assertFalse((out/'COMPLETE.json').exists());self.assertFalse((out/'ROOT-RECEIPT.json').exists())
        self.assertEqual(r.read_chain(out/'journal.jsonl')[1]['event'],'recovery_preflight_started')

    def test_unsupported_runtime_containment_still_fails_closed(self):
        from experiments.labbench import runtime
        with patch.object(runtime,'os',SimpleNamespace(name='posix')):
            with self.assertRaisesRegex(ValueError,'Native process containment requires Windows'):
                r.contain_process_tree()

    def test_early_reservation_never_writes_under_original_or_authority(self):
        data=self.root/'data';data.mkdir();original=data/'original';original.mkdir();registry=data/'registry';registry.mkdir()
        planning=data/'planning';planning.mkdir()
        pp,parent=self.preflight_plan(planning,original,600)
        authority=c.write(registry/'AUTHORITY.json',{})
        for index,protected in enumerate((original,registry,Path(parent['source_archive']['path']).parent,
                Path(parent['baseline_acceptance']['replay_root']),Path(parent['baseline_acceptance']['analyzer_archive']['path']).parent)):
            out=protected/'intrusion';frame=dict(schema_version=2,kind=r.KIND,purpose='fictional_qualification',parent=parent,plan=pp,authority=authority,code_files=[],qualification=None,output=str(out))
            fp=c.write(planning/f'FRAME-{index}.json',frame)
            with patch.object(r,'ROOT',self.root),patch.object(r,'load_frame',side_effect=ValueError('late rejection')),patch.object(r,'contain_process_tree'),patch.object(r,'DeadlineWatchdog'):
                with self.assertRaises(ValueError):r.execute(fp['path'],fp['sha256'],output=out)
            self.assertFalse(out.exists(),'protected parent must remain byte-for-byte untouched')

    def test_original_frame_metadata_is_an_explicit_coordinator_grant(self):
        from experiments.litqa_refinement.phase_checks import _Captured
        baseline_root=self.root/'baseline';baseline_root.mkdir();r.write(baseline_root/'RECEIPT.json',{'files':{}})
        baseline=SimpleNamespace(root=str(baseline_root),manifest={'role_files':[]})
        original_root=self.root/'original';original_root.mkdir();fp=r.write(original_root/'FRAME.json',{'purpose':'fictional_qualification'})
        pair=original_root/'pair_prepare';pair.mkdir();pp=r.write(pair/'PACKAGE-RECEIPT.json',{});r.write(pair/'JOB.json',{'input_files':[]})
        with patch.object(r.previous,'verify_package',return_value={'files':{}}):
            grants=r.coordinator_grants(baseline,{'root':str(pair),'package_sha256':pp['sha256']},fp)
        output=self.root/'audited';output.mkdir()
        audit=r.RoleAudit(inputs=[p['path'] for p in grants],code_files=[],runtime_roots=(sys.prefix,sys.base_prefix),model_files=[],output=output)
        audit.activate()
        try:
            # This is the real external FRAME read performed by phase_checks.
            _Captured(pair,{},time.monotonic()+10).external(original_root/'FRAME.json',fp['sha256'])
        finally:audit.active=False;audit.stream.close()
        self.assertEqual(audit.denials,0)


class RecoveryWorkerAdmissionTests(unittest.TestCase):
    """Explicit invented metadata; no real parent or native execution."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall);patch.object(c,'ROOT',self.base).start()
        from . import original,plan
        self.plan=plan;self.parent=payload(self.base)
        self.parent['frame'].update(baseline=dict(root=str(self.base/'baseline'),receipt_sha256='a'*64),interpreter=r.proof(sys.executable),
            generation_configuration=encode(r.model.CONFIG),model_provenance={})
        framepath=Path(self.parent['frame_proof']['path']);framepath.write_bytes(canonical(self.parent['frame']));self.parent['frame_proof']=r.proof(framepath)
        patch.object(original,'reconstruct',return_value=SimpleNamespace(payload=freeze(self.parent))).start();patch.object(original,'revalidate',return_value=True).start()
        self.descriptor=dict(inspection={},source_archive={},baseline_acceptance={});self.value=plan.prepare(self.descriptor)
        registry=c.authority_registry(original_root=self.parent['original_root'],purpose='fictional_qualification');registry.mkdir(parents=True)
        self.reserved=plan.reserve(self.value,registry,self.base/'planning');self.root=self.base/'recovery';self.root.mkdir();(self.root/'repair').mkdir()
        self.pins=[r.proof(r.__file__)];patch.object(r,'code_files',return_value=self.pins).start()
        self.frame=dict(schema_version=2,kind=r.KIND,purpose='fictional_qualification',parent=self.descriptor,plan=self.reserved['plan'],authority=self.reserved['authority'],code_files=self.pins,qualification=None,output=str(self.root))
        self.fp=r.write(self.root/'FRAME.json',self.frame);execution=Path(self.reserved['authority']['path']).parent/'EXECUTION';execution.mkdir()
        self.claim=r.write(execution/'CLAIM.json',dict(kind='sc05_recovery_execution_claim_v2',frame_sha256=self.fp['sha256'],output=str(self.root),automatic_retry=False))
        seconds,stage=r.remaining_job_budgets(self.value,'repair',phase_elapsed=1,outer_elapsed=1)
        self.job=dict(phase='repair',frame_sha256=self.fp['sha256'],input_files=[],model_bindings={},parent_pair={},baseline=self.parent['frame']['baseline'],dispatch_ordinals=[1],
            seconds=seconds,stage_seconds=stage,original_slots=self.value['original_repair_slots'],execution_claim=self.claim,phase_preflight_seconds=1,outer_preflight_seconds=1)
        self.jp=r.write(self.root/'repair/JOB.json',self.job);self.output=self.root/'repair/worker'
        self.authorization=execution/'repair-AUTHORIZED-JOB.json';r.write(self.authorization,dict(frame_sha256=self.fp['sha256'],job=self.jp,output=str(self.output)))

    def preflight(self):return r.worker_preflight(self.fp['path'],self.fp['sha256'],self.jp['path'],self.jp['sha256'],self.output)

    def test_worker_claim_only_after_separate_parent_admission(self):
        expected=r.admission_projection(freeze(self.frame),freeze(self.fp),freeze(self.job),freeze(self.jp),self.value)
        with patch.object(r,'admit_supervised',return_value=expected) as admission:self.preflight()
        self.assertEqual(admission.call_count,1);self.assertTrue((self.authorization.parent/'repair-WORKER-CLAIM.json').is_file())
        with patch.object(r,'admit_supervised',return_value=expected),self.assertRaises(FileExistsError):self.preflight()

    def test_separate_admission_denial_never_claims_or_starts_model(self):
        with patch.object(r,'admit_supervised',side_effect=ValueError('forged parent')),patch.object(r.native_model,'owned_server') as model:
            with self.assertRaisesRegex(ValueError,'forged parent'):self.preflight()
        model.assert_not_called();self.assertFalse(self.output.exists());self.assertFalse((self.authorization.parent/'repair-WORKER-CLAIM.json').exists())

    def test_worker_scope_resealed_after_root_authorization_rejected(self):
        self.job['dispatch_ordinals']=[0,1];Path(self.jp['path']).write_bytes(canonical(self.job));self.jp=r.proof(self.jp['path'])
        with patch.object(r,'admit_supervised') as admission,self.assertRaises(ValueError):self.preflight()
        admission.assert_not_called();self.assertFalse((self.authorization.parent/'repair-WORKER-CLAIM.json').exists())

    def test_separate_actual_subprocess_rejects_invalid_parent_and_retains_failure(self):
        # The child has no fixture mocks: strict parent admission rejects the
        # deliberately empty inspection descriptor before any native setup.
        with self.assertRaisesRegex(ValueError,'admission failed'):
            r.admit_supervised(self.fp,self.jp,self.root/'repair/admission',seconds=20)
        root=self.root/'repair/admission'
        self.assertTrue((root/'FAILURE.json').is_file());self.assertTrue((root/'worker/FAILURE.json').is_file())
        process=parse_json((root/'PROCESS.json').read_bytes());self.assertEqual(process['returncode'],1)
        self.assertTrue(process['supervision']['process_reaped']);self.assertFalse((self.authorization.parent/'repair-WORKER-CLAIM.json').exists())

    def test_separate_timeout_retains_envelope_and_no_admission_success(self):
        output=self.root/'repair/admission'
        def timeout(command,limits,where):
            return r.previous.supervised_original([sys.executable,'-I','-B','-c','import time;print("admission",flush=True);time.sleep(5)'],r.ProcessLimits(.5,1024),where)
        actual=r.previous.supervised
        with patch.object(r.previous,'supervised_original',actual,create=True),patch.object(r.previous,'supervised',side_effect=timeout),self.assertRaises(EngineDeadlineExceeded):
            r.admit_supervised(self.fp,self.jp,output,seconds=20)
        self.assertTrue((output/'PROCESS.json').is_file());self.assertTrue((output/'FAILURE.json').is_file());self.assertFalse((output/'COMPLETE.json').exists())


from tether_engine.serde import freeze
if __name__=='__main__':unittest.main()
