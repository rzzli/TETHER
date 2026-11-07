"""Invented retained native/source integration through original paired requests.

No source HTTP, model generation, evaluator keys or archived code execute. The
original-history admission and new reserved-cell/source validation are genuine;
only transport/native process responses are explicit fictional fixtures.
"""
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import sys
import os
import time
import traceback
import unittest
from unittest.mock import patch
from tether_engine.serde import canonical,encode,parse_json
from experiments.litqa_refinement import test_envelopes as envelope_fixtures
from . import original,run as r,contracts as c
from . import test_original as parent_fixtures


def author_complete_recovery(failed_fixture,output):
    """Genuine controller/admission/cells; explicit invented OS/transport only.

    The input fixture must use repair_stage_seconds=500 and purpose fictional.
    Files persist for the caller's independent reader. Nothing is downloaded or
    inferred and no source/admission gate is replaced by a fake result.
    """
    from . import plan
    from experiments.labbench import model as nm
    from experiments.litqa_refinement import pipeline
    from experiments.litqa_refinement.test_evaluation import native_caller
    f=failed_fixture;output=Path(output).resolve();base=output.parent
    descriptor=dict(inspection=f.inspection,source_archive=f.archive,baseline_acceptance=f.acceptance)
    value=plan.prepare(descriptor);registry=c.authority_registry(original_root=value['original_root'],purpose=value['purpose']);registry.mkdir(exist_ok=True)
    reserved=plan.reserve(value,registry,base/(output.name+'-planning'))
    frame=dict(schema_version=2,kind=r.KIND,purpose='fictional_qualification',parent=descriptor,plan=reserved['plan'],authority=reserved['authority'],
        code_files=r.code_files(),qualification=None,output=str(output))
    fp=r.write(base/(output.name+'-FRAME.json'),frame)
    native_class=pipeline.NativeCaller;audits=[]
    real_audit=r.RoleAudit
    def audited(**kwargs):
        value=real_audit(**kwargs);audits.append(value);return value
    @contextmanager
    def owner(spec,bindings,*,output,journal,parent_deadline):
        started=time.monotonic();terminal=dict(started=True,server_stopped=False,pid=12345,exit_code=None,secondary_failures=[],elapsed_seconds=0)
        obj=SimpleNamespace(spec=spec,bindings=bindings,terminal_record=terminal,assert_ready=lambda:None)
        r.write(output/'server-command.json',encode(spec));(output/'server.stdout.log').write_bytes(b'');(output/'server.stderr.log').write_bytes(b'')
        journal.append('server_started',pid=12345);journal.append('server_ready',pid=12345)
        try:yield obj
        finally:
            terminal.update(server_stopped=True,exit_code=0,elapsed_seconds=time.monotonic()-started);journal.append('server_terminal',**terminal)
    class ActorCaller:
        def __init__(self,owner,alias,audit):self.owner,self.alias,self.audit=owner,alias,audit
        def __call__(self,descriptor,output,deadline):
            with self.audit.actor(descriptor['task'],output),patch.object(pipeline,'NativeCaller',native_class):
                return native_caller(f.history.fixture.native,owner=self.owner,alias=self.alias)(descriptor,output,deadline)
    def supervise(command,limits,where):
        # Actual subprocess timeout/output behavior is independently covered in
        # test_run. Here the OS records are expressly invented, as in the
        # accepted historical fixture; the complete worker code really runs.
        started=time.monotonic();where=Path(where);ret=0;stderr=b''
        def argument(flag):return command[command.index(flag)+1]
        try:
            phase=Path(argument('--job')).parent.name;ordinal=('repair','removal').index(phase)
            if '--admission' in command:
                with patch.object(os,'getpid',return_value=920001+ordinal):
                    r.admit(argument('--frame'),argument('--frame-sha256'),argument('--job'),argument('--job-sha256'),argument('--output'))
            else:
                before=len(audits)
                try:
                    with patch.object(os,'getpid',return_value=910001+ordinal):
                        r.worker(argument('--frame'),argument('--frame-sha256'),argument('--job'),argument('--job-sha256'),argument('--output'))
                finally:
                    for audit in audits[before:]:audit.active=False;audit.stream.close()
        except BaseException:
            ret=1;stderr=traceback.format_exc().encode()
        elapsed=time.monotonic()-started
        supervision=dict(schema_version=1,method='tether.process_envelope.v1',limits=limits.payload(),termination_reason='exited',process_started=True,process_reaped=True,
            pipe_eof=dict(stdout=True,stderr=True),cleanup_errors=[],observed_counts_are_lower_bounds=False,
            retained_stdout_bytes=0,observed_stdout_bytes=0,retained_stderr_bytes=len(stderr),observed_stderr_bytes=len(stderr),execution_elapsed_seconds=elapsed,total_elapsed_seconds=elapsed)
        (where/'stdout.bin').write_bytes(b'');(where/'stderr.bin').write_bytes(stderr);r.write(where/'PROCESS.json',dict(returncode=ret,supervision=supervision))
        return SimpleNamespace(returncode=ret,stdout=b'',stderr=stderr,supervision=supervision)
    with patch.object(r,'contain_process_tree',return_value=None),patch.object(r,'RoleAudit',side_effect=audited),\
         patch.object(pipeline,'NativeCaller',ActorCaller),patch.object(nm,'owned_server',side_effect=owner),patch.object(r.previous,'supervised',side_effect=supervise):
        try:result=r.execute(fp['path'],fp['sha256'],output=output)
        except BaseException as error:
            for phase in ('repair','removal'):
                for relative in ('stderr.bin','admission/stderr.bin','worker/FAILURE.json','admission/worker/FAILURE.json'):
                    target=output/phase/relative
                    if target.is_file():error.add_note(str(target)+'\n'+target.read_bytes().decode('utf-8','replace')[-8000:])
            raise
    return encode(result)


@unittest.skipUnless(os.name=='nt','native held-handle test requires Windows')
class RecoveryNativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_type=type('RecoveryOriginalFixture',(parent_fixtures.FailedFixture,envelope_fixtures.EnvelopeTests),{})
        cls.f=fixture_type('runTest');cls.addClassCleanup(cls.f.doCleanups);cls.f.setUp()
        cls.parent=cls.f.verify_parent()
        cls.snapshot=r.inventory(cls.f.root,omit=())

    def operation(self,slot,end,stage,caller):
        f=self.f;index=slot['ordinal']
        return r._operation(slot,end,case=f.f.baseline.cases[index],product=self.parent.payload['pair_prepare']['products'][index],
            caller=caller,root=stage.root/'products'/f'{index:04d}',provenance=f.model['provenance'],alias=f.model['alias'],server_spec=f.model['spec'],bindings=f.model['bindings'])

    def stage(self,phase,ordinals):
        value=self.parent.payload
        old=tuple(row['execution_id'] for row in value['repair_rows']) if phase=='repair' else (None,None)
        out=self.f.base/(self._testMethodName+'-'+phase)
        return r.RecoveryStage(value['schedule'],phase,ordinals,out,purpose='fictional_qualification',seconds=120,original_slots=old)

    def test_untouched_repair_and_all_removal_use_original_pair_without_new_sources(self):
        self.assertEqual(self.parent.payload['untouched_repair_ordinals'],(1,))
        for phase,ordinals in [('repair',(1,)),('removal',(0,1))]:
            stage=self.stage(phase,ordinals)
            for _ in ordinals:stage.call(lambda slot,end:self.operation(slot,end,stage,self.f.f.fake_model))
            report=stage.finish();self.assertEqual(report['status'],'complete')
            replay=r.verify_stage(stage.root,r.proof(stage.root/'STAGE-RECEIPT.json')['sha256'],ids=self.parent.payload['schedule'],phase=phase,
                ordinals=ordinals,purpose='fictional_qualification',original_slots=tuple(row['execution_id'] for row in self.parent.payload['repair_rows']) if phase=='repair' else (None,None))
            self.assertEqual(replay['report'],report)
            for row in report['rows']:
                frozen=c.read(self.parent.payload['pair_prepare']['products'][row['ordinal']][phase])
                cell=stage.root/'products'/f'{row["ordinal"]:04d}'
                self.assertEqual(parse_json((cell/'native/request.json').read_bytes()),encode(frozen['request']))
                self.assertEqual(parse_json((cell/'native/payload.json').read_bytes()),encode(frozen['payload']))
                if phase=='removal':self.assertEqual(parse_json((cell/'INPUT.json').read_bytes())['sources'],[])
            self.assertEqual(report['accounting']['known_totals']['source_http_requests'],0)
        self.assertEqual(r.inventory(self.f.root,omit=()),self.snapshot);self.assertTrue(original.revalidate(self.parent))

    def test_new_exact_limit_failure_stays_null_and_capture_remains_replayable(self):
        f=self.f;nf=f.history.fixture.native;body_builder=nf.f.native_body;stage=self.stage('removal',(0,1))
        def limited(**kwargs):
            value=parse_json(body_builder(**kwargs));value.update(tokens_predicted=256,stop_type='limit',stop=True,stopping_word='')
            for key in ('stopped_limit','stopped_word','stopped_eos'):value.pop(key,None)
            return canonical(value)
        class Caller:
            owner=SimpleNamespace(terminal_record={'pid':12345})
            def __call__(self,descriptor,output,deadline):return f.f.fake_model(descriptor,output,deadline)
        with patch.object(nf.f,'native_body',side_effect=limited):
            first=stage.call(lambda slot,end:self.operation(slot,end,stage,Caller()))
        stage.call(lambda slot,end:self.operation(slot,end,stage,Caller()));report=stage.finish()
        self.assertEqual(first['status'],'authenticated_limit_failure');self.assertIsNone(first['product']['disposition']['prediction'])
        proof=first['product']['limit_failure'];descriptor=c.read(proof)
        self.assertEqual(descriptor['raw_reported_usage']['output_tokens'],256);self.assertIsNone(descriptor['qualified_usage'])
        self.assertEqual(set(r.inventory(stage.root/'products/0000',omit=())),r.native_failure.FILES)
        frozen=c.read(self.parent.payload['pair_prepare']['products'][0]['removal']);cell=stage.root/'products/0000'
        checked=r.native_failure.verify_cell_limit_failure(cell,files=descriptor['original_proofs'],expected_inputs=parse_json((cell/'INPUT.json').read_bytes()),
            expected_request=frozen['request'],expected_payload=frozen['payload'],execution_id=first['execution_id'],owner_pid=12345,alias=f.model['alias'],server_spec=f.model['spec'],bindings=f.model['bindings'])
        self.assertEqual(checked,descriptor);self.assertEqual(report['accounting']['authenticated_limit_generation_calls'],1)
        self.assertEqual(report['accounting']['known_totals']['generation_calls'],1);self.assertFalse(report['accounting']['measurements_complete'])
        self.assertEqual(r.inventory(self.f.root,omit=()),self.snapshot)


@unittest.skipUnless(os.name=='nt','native held-handle test requires Windows')
class CompleteRecoveryControllerTests(unittest.TestCase):
    def test_complete_invented_controller_uses_separate_admission_and_role_audits(self):
        fixture_type=type('CompleteRecoveryOriginalFixture',(parent_fixtures.FailedFixture,envelope_fixtures.EnvelopeTests),{'repair_stage_seconds':500})
        fixture=fixture_type('runTest');self.addCleanup(fixture.doCleanups);fixture.setUp()
        result=author_complete_recovery(fixture,fixture.base/'recovered-controller')
        root=Path(result['root']);receipt=parse_json((root/'ROOT-RECEIPT.json').read_bytes())
        self.assertEqual(r.proof(root/'ROOT-RECEIPT.json')['sha256'],result['receipt_sha256'])
        self.assertEqual(receipt['status'],'recovery_execution_complete')
        self.assertEqual(parse_json((root/'COMPLETE.json').read_bytes())['new_scheduled'],3)
        for phase,count in [('repair',1),('removal',2)]:
            report=parse_json((root/phase/'worker/phase/REPORT.json').read_bytes())
            self.assertEqual(report['scheduled'],count);self.assertEqual(report['accounting']['known_totals']['generation_calls'],count)
            self.assertEqual(report['accounting']['known_totals']['source_http_requests'],0)
            admitted=parse_json((root/phase/'admission/worker/REPORT.json').read_bytes())
            self.assertFalse(admitted['scientific_answers_returned']);self.assertFalse(admitted['model_or_http_execution_performed'])
            audit=[parse_json(line) for line in (root/phase/'worker/io-audit.jsonl').read_bytes().splitlines()]
            self.assertFalse(any(row.get('allowed') is False for row in audit))
            entered=[row for row in audit if row.get('event')=='actor_entered'];self.assertEqual(len(entered),count)
            self.assertTrue(all(row['role']==phase and row['coordinator_inputs_granted'] is False for row in entered))


if __name__=='__main__':unittest.main()
