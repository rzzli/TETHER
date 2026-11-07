"""Invented envelopes and resealed adversarial controls; no model/HTTP calls.

Isolated negatives mock historical adoption. The full integration additionally
authors and independently reconstructs an entire invented original execution,
then uses the strict real acceptance loader and new source/native evaluators.
"""
import copy
from datetime import datetime, timezone
import inspect
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import encode
from experiments.litqa_refinement import envelopes as e, pipeline, collection
from experiments.litqa_refinement import test_pipeline as pipeline_fixtures
from experiments.litqa_refinement.test_collection import fetcher

FICTIONAL_TEXT=('In the invented Lumarin experiment, treatment increased cobalt uptake relative to vehicle. '
                'In the invented Vesprine experiment, treatment reduced amber uptake relative to vehicle.')


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(e.canonical(value))


def proof(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=e.digest(raw))


def inventory(root,omit=()):
    return {p.relative_to(root).as_posix():proof(p) for p in sorted(root.rglob('*')) if p.is_file() and p.relative_to(root).as_posix() not in omit}


def chain(path,events):
    rows=[];previous=None
    for n,(name,details) in enumerate(events):
        value=dict(sequence=n,previous_sha256=previous,event=name,details=details);previous=e.fingerprint(value)
        rows.append(dict(value,sha256=previous))
    path.write_bytes(b''.join(e.canonical(row)+b'\n' for row in rows))


def prepare_accepted_history(output, *, one_absent=False):
    """Persist an invented original and strict acceptance for a later rehearsal.

    Every original source/native body and process record is explicitly invented.
    Independent reconstruction is genuine and all archived files remain data.
    Caller owns the fresh output; this helper never removes its retained files.
    """
    from experiments.litqa_analysis import test_accepted_primary as accepted_fixtures
    from experiments.litqa_refinement import projection
    from experiments.litqa_comparison import qualification_fixtures
    output=Path(output).absolute();output.mkdir(parents=True,exist_ok=False);scratch=[]
    class RetainedScratch:
        def __init__(self,*args,**kwargs):
            folder=output/f'scratch-{len(scratch):04d}';folder.mkdir();scratch.append(folder);self.name=str(folder)
        def cleanup(self):pass
        def __enter__(self):return self.name
        def __exit__(self,*args):pass
    fixture=type('RetainedAcceptedHistory',(accepted_fixtures.AcceptedPrimaryTests,),{})
    original_fetch=qualification_fixtures.fetch
    search_ordinal=0
    def selected_fetch(url,**kwargs):
        nonlocal search_ordinal
        if '/search?' in url:
            ordinal=search_ordinal;search_ordinal+=1
            # Original collection order is Q1/L,Q1/E,Q2/L,Q2/E, each with
            # two metadata requests. The first lexical query is shared across
            # these invented questions, so term matching cannot isolate Q2/L.
            if one_absent and ordinal in (4,5):
                return dict(status=200,body=e.canonical(dict(resultList=dict(result=[]))),final_url=url,
                    headers={'X-TETHER-Fixture':'invented-empty-second-lexical-case-no-http-dispatch'})
        return original_fetch(url,**kwargs)
    with patch.object(tempfile,'TemporaryDirectory',RetainedScratch),patch.object(qualification_fixtures,'fetch',side_effect=selected_fetch):
        fixture.setUpClass()
    acceptance=dict(replay_root=str(fixture.replay),receipt_sha256=fixture.sha,analyzer_archive=fixture.analyzer)
    adopted=e._adopt(acceptance)
    descriptor=dict(kind='sc05_original_execution_v1',role='original_sc04_execution',root=str(fixture.fixture.primary_path),
                    root_receipt_sha256=fixture.fixture.primary_sha)
    baseline=projection.prepare_baseline(descriptor,proof(fixture.replay/'RECEIPT.json'),output/'projection')
    if one_absent:
        assert baseline.cases[0]['original_selected_sources'] and not baseline.cases[1]['original_selected_sources']
    scope=dict(kind='sc05_invented_accepted_history_fixture_v1',purpose='fictional_qualification',
        original_sources='invented',original_native_responses='invented',original_process_records='invented',
        independent_original_reconstruction=True,external_acceptance_byte_recheck=True,
        archived_code_executed=False,real_model_calls=0,real_http_calls=0,questions=2,second_lexical_case_explicitly_empty=one_absent,
        empty_metadata_request_ordinals=[4,5] if one_absent else [],
        baseline=dict(root=baseline.root,receipt_sha256=baseline.receipt_sha256),baseline_acceptance=acceptance)
    write(output/'FIXTURE-SCOPE.json',scope)
    return dict(baseline=baseline,baseline_acceptance=acceptance,adopted=adopted,scope=proof(output/'FIXTURE-SCOPE.json')),fixture


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.f=pipeline_fixtures.PipelineTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.base=self.f.base;self.root=self.base/'envelope';self.root.mkdir()
        self.baseline=encode(self.f.baseline.manifest)
        self.acceptance=dict(replay_root=str(self.base/'accepted'),receipt_sha256='a'*64,
            analyzer_archive=dict(path=str(self.base/'archive/MANIFEST.json'),sha256='b'*64))
        self.adopted=dict(status=e.accepted_primary.STATUS,adoption=dict(status=e.accepted_primary.STATUS,semantic_reconstruction_recomputed=False),report=dict(
            root=self.baseline['execution_descriptor']['root'],root_sha256=self.baseline['execution_descriptor']['root_receipt_sha256'],
            frame_sha256=self.baseline['original_frame_sha256'],purpose='fictional_qualification',queries=self.baseline['queries'],
            records={'L/O':[c['original_disposition'] for c in self.baseline['cases']]},
            evidence_ids={'L/O':{c['id']:[s['source_id'] for s in c['original_selected_sources']] for c in self.baseline['cases']}},
            resources=dict(physical_model=dict(generation_calls=8),physical_http=dict(requests=4)),
            source_cases={'L/O':[dict(id=c['id'],logical_model_usage=dict(generation_calls=1,measured_input_tokens=10,measured_output_tokens=20,
                reserved_input_tokens=50,reserved_output_tokens=256,provider_cost_usd=0),logical_http_usage=dict(requests=2,
                measured_response_bytes=10,safety_accounted_bytes=10,unknown_transfer_upper_bytes=0)) for c in self.baseline['cases']]}))
        if getattr(self,'complete_history',False):
            info,self.history=prepare_accepted_history(self.base/'full-history',one_absent=True)
            self.f.baseline=info['baseline'];self.baseline=encode(self.f.baseline.manifest)
            self.acceptance=info['baseline_acceptance'];self.adopted=info['adopted']
        modelroot=self.base/'model';modelroot.mkdir();write(modelroot/'LICENSE',{})
        receipt=dict(root=str(modelroot),model_id='fictional-native',revision='fictional',items=[dict(name='weights.gguf',sha256='a'*64,bytes=1)],
                     runtime_files=[dict(path='runtime/llama-server.exe',sha256='b'*64,bytes=1)])
        write(modelroot/'acquisition.json',receipt);mr=proof(modelroot/'acquisition.json')
        entries=[dict(logical_id='weights.gguf',sha256='a'*64,bytes=1),dict(logical_id='runtime/llama-server.exe',sha256='b'*64,bytes=1),
                 dict(logical_id='acquisition.json',sha256=mr['sha256'],bytes=mr['bytes'])]
        bindings={p['logical_id']:str(modelroot/p['logical_id']) for p in entries};alias='tether-sc05-refinement-qwen14b-v1'
        spec=dict(argv=[bindings['runtime/llama-server.exe'],'--model',bindings['weights.gguf'],'--host','127.0.0.1','--port','55631',
            '--alias',alias,'--ctx-size','16384','--parallel','1','--threads','8','--n-gpu-layers','99','--offline','--no-webui'],
            executable=entries[1],required_inputs=[entries[0],entries[2]],host='127.0.0.1',port=55631,startup_seconds=180,terminate_seconds=30,kill_seconds=10)
        provenance=dict(weights_sha256={'weights.gguf':'a'*64},runtime_sha256='b'*64,asset_manifest_sha256=mr['sha256'],model_id='fictional-native',revision='fictional')
        license_proof=proof(modelroot/'LICENSE')
        if getattr(self,'complete_history',False):
            from experiments.labbench import model as native_model
            from experiments.litqa_refinement.test_evaluation import native_caller
            nf=self.history.fixture.native;mr=proof(nf.f.receipt)
            native_spec,native_bindings,native_provenance=native_model.make_server_spec(nf.f.receipt,mr['sha256'],port=55598,alias=alias)
            spec=encode(native_spec);bindings={k:str(v) for k,v in native_bindings.items()};provenance=encode(native_provenance)
            license_proof=proof(nf.f.asset/'LICENSE.fixture.txt')
            owner=SimpleNamespace(spec=native_spec,bindings=native_bindings,terminal_record={'pid':12345},assert_ready=lambda:None)
            self.f.fake_model=native_caller(nf,owner=owner,alias=alias)
        self.model=dict(spec=spec,bindings=bindings,provenance=provenance,alias=alias)
        self.frame=dict(schema_version=1,kind='sc05_refinement_execution_v1',purpose='fictional_qualification',schedule=self.baseline['schedule'],
            baseline=dict(root=self.f.baseline.root,receipt_sha256=self.f.baseline.receipt_sha256),interpreter=proof(Path(sys.executable)),
            code_files=e._closure(e.accepted_primary._Inputs()),phase_seconds={p:600 for p in e.PHASES},port=spec['port'],alias=alias,
            model_receipt=mr,model_license=license_proof,model_spec=spec,model_provenance=provenance,
            generation_configuration=e.CONFIGURATION,qualification=None,provider_spend_usd=0,automatic_retry=False,output=str(self.root))
        write(self.root/'FRAME.json',self.frame);self.fp=proof(self.root/'FRAME.json');self.root_events=[];self.anchors={};self.grants={}
        self.reserved=dict(run_id='00000000-0000-0000-0000-000000000123',owner_pid=os.getpid(),created_at_utc=datetime.now(timezone.utc).isoformat())
        self.root_events.append(('build_reserved',self.reserved))
        self.addCleanup(patch.stopall)
        patch.object(e,'MODEL_RECEIPT',mr['sha256']).start()
        if not getattr(self,'complete_history',False):
            self.adoption_mock=patch.object(e.accepted_primary,'load',side_effect=lambda *a,**k:copy.deepcopy(self.adopted)).start()
        for phase in e.PHASES:self.phase(phase)
        self.reseal()

    def phase(self,phase):
        pr=self.root/phase;pr.mkdir();wr=pr/'worker'
        base=Path(self.f.baseline.root);br=e.decode((base/'RECEIPT.json').read_bytes())
        grants={str(base/'RECEIPT.json'):proof(base/'RECEIPT.json')}
        for name in br['files']:grants[str(base/name)]=proof(base/name)
        for row in self.baseline['role_files']:grants[row['proof']['path']]=row['proof']
        for parent in e.PARENTS[phase]:grants.update(self.grants[parent])
        job=dict(phase=phase,frame_sha256=self.fp['sha256'],parents={n:self.anchors[n] for n in e.PARENTS[phase]},
            input_files=[grants[k] for k in sorted(grants)],model_bindings=self.model['bindings'],cutoff=datetime.now(timezone.utc).isoformat() if phase=='pair_prepare' else None)
        write(pr/'JOB.json',job);jp=proof(pr/'JOB.json')
        journal=RunJournal(wr,kind='build')
        write(wr/'CONFIG.json',dict(frame_sha256=self.fp['sha256'],job_sha256=jp['sha256'],phase=phase,purpose='fictional_qualification',
            worker_pid=os.getpid(),python_version=sys.version,coordinator_grants=job['input_files']))
        write(wr/'MODEL.json',self.model)
        terminal_server=None
        if phase in e.MODEL_PHASES:
            terminal_server=dict(started=True,server_stopped=True,pid=12345,exit_code=0,secondary_failures=[],elapsed_seconds=1)
            journal.append('server_started',pid=12345);journal.append('server_ready',pid=12345)
            write(wr/'server/server-command.json',self.model['spec'])
            (wr/'server/server.stdout.log').write_bytes(b'');(wr/'server/server.stderr.log').write_bytes(b'')
            write(wr/'SERVER-RESOURCE-SAMPLES.json',[dict(monotonic=1,value=None,error_class=None)])
        text=FICTIONAL_TEXT if getattr(self,'complete_history',False) else 'Fictional Lumarin is cobalt.'
        with patch.object(collection.acquisition.legacy,'fetch_http',side_effect=fetcher(('PMC8',),text=text)):
            pipeline.execute(phase,self.f.baseline,wr/'phase',purpose='fictional_qualification',seconds=120,
                parents={n:dict(root=str(Path(a['root'])/'worker/phase'),receipt_sha256=a['stage_receipt_sha256']) for n,a in job['parents'].items()},
                cutoff=job['cutoff'],model_provenance=self.model['provenance'],call_model=self.f.fake_model)
        if terminal_server is not None:journal.append('server_terminal',**terminal_server)
        audit=[dict(path=jp['path'],mode='r',flags=0,allowed=True,basis='coordinator_input',role='coordinator')]
        if phase in e.MODEL_PHASES:
            for n in range(2):
                cell=wr/'phase/products'/f'{n:04d}'
                audit.extend([dict(event='actor_entered',role=phase,output=str(cell),coordinator_inputs_granted=False),
                    dict(path=str(cell/'SUMMARY.json'),mode='w',flags=os.O_WRONLY,allowed=True,basis='role_output',role=phase),
                    dict(event='actor_exited',role=phase,output=str(cell))])
        (wr/'io-audit.jsonl').write_bytes(b''.join(e.canonical(x)+b'\n' for x in audit))
        worker_seconds=max(3,e.decode((wr/'phase/STAGE-RECEIPT.json').read_bytes())['seal_elapsed_seconds']+1)
        terminal=dict(status='complete',phase=phase,purpose='fictional_qualification',frame_sha256=self.fp['sha256'],
            stage_receipt=proof(wr/'phase/STAGE-RECEIPT.json'),wall_seconds=worker_seconds,worker_memory=None,server_terminal=terminal_server,
            audit_denials=0,provider_cost_usd=0,reference_keys_read=False,scientific_scoring_performed=False)
        write(wr/'COMPLETE.json',terminal);journal.append('refinement_worker_completed',terminal_sha256=e.fingerprint(terminal));journal.close()
        command=[self.frame['interpreter']['path'],'-I','-B','-c',e.LAUNCHER,str(e.REPO),str(e.REPO/'src'),str(e.REPO/'packages/tether/src'),
            '--worker','--frame',self.fp['path'],'--frame-sha256',self.fp['sha256'],'--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(wr)]
        limits=dict(timeout_seconds=660,max_output_bytes=4*1024**2)
        write(pr/'COMMAND.json',command);(pr/'stdout.bin').write_bytes(b'');(pr/'stderr.bin').write_bytes(b'')
        write(pr/'PROCESS.json',dict(returncode=0,supervision=dict(schema_version=1,method='tether.process_envelope.v1',limits=limits,
            termination_reason='exited',process_started=True,process_reaped=True,pipe_eof=dict(stdout=True,stderr=True),cleanup_errors=[],
            observed_counts_are_lower_bounds=False,retained_stdout_bytes=0,observed_stdout_bytes=0,retained_stderr_bytes=0,observed_stderr_bytes=0,
            execution_elapsed_seconds=worker_seconds+1,total_elapsed_seconds=worker_seconds+1)))
        write(pr/'PACKAGE-RECEIPT.json',dict(kind='sc05_refinement_phase_receipt_v1',status='complete',phase=phase,frame_sha256=self.fp['sha256'],
            files=inventory(pr,('PACKAGE-RECEIPT.json',))))
        anchor=dict(root=str(pr),package_sha256=proof(pr/'PACKAGE-RECEIPT.json')['sha256'],stage_receipt_sha256=terminal['stage_receipt']['sha256'])
        self.anchors[phase]=anchor;write(self.root/(phase+'-ANCHOR.json'),anchor)
        self.grants[phase]=dict(grants);self.grants[phase].update({p['path']:p for p in inventory(pr).values()})
        self.root_events.extend([('refinement_phase_reserved',dict(phase=phase,job=jp,command=command,limits=limits)),('refinement_phase_completed',dict(phase=phase,anchor=anchor))])

    def reseal(self):
        elapsed=1+sum(e.decode((self.root/phase/'PROCESS.json').read_bytes())['supervision']['execution_elapsed_seconds'] for phase in e.PHASES)
        write(self.root/'COMPLETE.json',dict(status='refinement_execution_complete',purpose='fictional_qualification',phases=self.anchors,scheduled=2,
            wall_seconds=elapsed,provider_cost_usd=0,scientific_scoring_performed=False,automatic_retry=False))
        chain(self.root/'journal.jsonl',self.root_events+[('refinement_execution_completed',dict(phases=list(e.PHASES)))])
        self.rootseal()

    def rootseal(self):
        write(self.root/'ROOT-RECEIPT.json',dict(kind='sc05_refinement_root_receipt_v1',status='refinement_execution_complete',frame_sha256=self.fp['sha256'],
            files=inventory(self.root,('ROOT-RECEIPT.json',))))
        self.descriptor=dict(root=str(self.root),receipt_sha256=proof(self.root/'ROOT-RECEIPT.json')['sha256'])

    def lastseal(self):
        phase='removal';pr=self.root/phase
        write(pr/'PACKAGE-RECEIPT.json',dict(kind='sc05_refinement_phase_receipt_v1',status='complete',phase=phase,frame_sha256=self.fp['sha256'],
            files=inventory(pr,('PACKAGE-RECEIPT.json',))))
        self.anchors[phase]['package_sha256']=proof(pr/'PACKAGE-RECEIPT.json')['sha256']
        write(self.root/(phase+'-ANCHOR.json'),self.anchors[phase]);self.reseal()

    def reconstruct(self):return e.reconstruct(self.descriptor,baseline_acceptance=self.acceptance)

    def test_full_fictional_envelope_and_byte_recheck(self):
        result=self.reconstruct()
        self.assertTrue(result['supervised_root_verified'] and result['actor_roles_verified'] and result['baseline_verified'])
        self.assertEqual(list(result['phases']),list(e.PHASES));self.assertEqual(result['started_at_utc'],self.reserved['created_at_utc'])
        self.assertEqual(len(result['resources']['baseline_resources']),2);self.assertTrue(e.revalidate(result))
        self.assertEqual(self.adoption_mock.call_args.args,(self.acceptance['replay_root'],self.acceptance['receipt_sha256']))

    def test_external_receipt_and_acceptance_required(self):
        self.descriptor['receipt_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'anchor'):self.reconstruct()
        with self.assertRaises(ValueError):e._adopt(dict(self.acceptance,evaluator_keys='forbidden'))

    def test_resealed_failure_and_orphan_membership_rejected(self):
        write(self.root/'removal/worker/DEADLINE.json',{})
        self.lastseal()
        with self.assertRaisesRegex(ValueError,'terminal failure'):self.reconstruct()

    def test_unknown_empty_directory_rejected(self):
        (self.root/'removal/worker/orphan').mkdir()
        with self.assertRaisesRegex(ValueError,'directories'):self.reconstruct()

    def test_resealed_role_escalation_rejected(self):
        p=self.root/'removal/worker/io-audit.jsonl';rows=[e.decode(x) for x in p.read_bytes().splitlines()]
        rows[2].update(path=str(Path(self.f.baseline.root)/'BASELINE.json'),flags=0,mode='r',basis='coordinator_input')
        p.write_bytes(b''.join(e.canonical(x)+b'\n' for x in rows));self.lastseal()
        with self.assertRaisesRegex(ValueError,'reclassification'):self.reconstruct()

    def test_resealed_actor_slot_reentry_rejected(self):
        p=self.root/'removal/worker/io-audit.jsonl';rows=[e.decode(x) for x in p.read_bytes().splitlines()]
        rows[-3:]=copy.deepcopy(rows[1:4]);p.write_bytes(b''.join(e.canonical(x)+b'\n' for x in rows));self.lastseal()
        with self.assertRaisesRegex(ValueError,'scheduled cell'):self.reconstruct()

    def test_resealed_stream_accounting_rejected(self):
        p=self.root/'removal/PROCESS.json';value=e.decode(p.read_bytes());value['supervision']['observed_stdout_bytes']=1;write(p,value);self.lastseal()
        with self.assertRaisesRegex(ValueError,'stream accounting'):self.reconstruct()

    def test_resealed_root_timing_rejected(self):
        p=self.root/'COMPLETE.json';value=e.decode(p.read_bytes());value['wall_seconds']=1;write(p,value);self.rootseal()
        with self.assertRaisesRegex(ValueError,'wall/process'):self.reconstruct()

    def test_resealed_stage_cannot_outlast_worker(self):
        worker=self.root/'removal/worker';p=worker/'COMPLETE.json';terminal=e.decode(p.read_bytes())
        terminal['wall_seconds']=0;terminal['server_terminal']['elapsed_seconds']=0;write(p,terminal)
        events=[e.decode(line) for line in (worker/'journal.jsonl').read_bytes().splitlines()]
        for row in events:
            if row['event']=='server_terminal':row['details']=terminal['server_terminal']
            if row['event']=='refinement_worker_completed':row['details']=dict(terminal_sha256=e.fingerprint(terminal))
        chain(worker/'journal.jsonl',[(row['event'],row['details']) for row in events]);self.lastseal()
        with self.assertRaisesRegex(ValueError,'elapsed'):self.reconstruct()

    def test_resealed_worker_cannot_outlast_process(self):
        p=self.root/'removal/PROCESS.json';value=e.decode(p.read_bytes())
        value['supervision']['execution_elapsed_seconds']=0;value['supervision']['total_elapsed_seconds']=0
        write(p,value);self.lastseal()
        with self.assertRaisesRegex(ValueError,'elapsed'):self.reconstruct()

    def test_resealed_process_exact_deadline_is_not_success(self):
        p=self.root/'removal/PROCESS.json';value=e.decode(p.read_bytes());duration=value['supervision']['limits']['timeout_seconds']
        value['supervision']['execution_elapsed_seconds']=duration;value['supervision']['total_elapsed_seconds']=duration
        write(p,value);self.lastseal()
        terminal_path=self.root/'COMPLETE.json';terminal=e.decode(terminal_path.read_bytes())
        terminal['wall_seconds']=1+sum(e.decode((self.root/phase/'PROCESS.json').read_bytes())['supervision']['execution_elapsed_seconds'] for phase in e.PHASES)
        write(terminal_path,terminal);self.rootseal()
        with self.assertRaisesRegex(ValueError,'resource bounds'):self.reconstruct()

    def test_resealed_stage_accounting_and_journal_contradiction_rejected(self):
        sr=self.root/'removal/worker/phase';p=sr/'REPORT.json';value=e.decode(p.read_bytes());value['accounting']['known_totals']['generation_calls']=0;write(p,value)
        seal=e.decode((sr/'STAGE-RECEIPT.json').read_bytes());seal['files']={n:{k:v[k] for k in ('bytes','sha256')} for n,v in inventory(sr,('STAGE-RECEIPT.json',)).items()}
        write(sr/'STAGE-RECEIPT.json',seal);terminal=e.decode((sr.parent/'COMPLETE.json').read_bytes());terminal['stage_receipt']=proof(sr/'STAGE-RECEIPT.json');write(sr.parent/'COMPLETE.json',terminal)
        self.anchors['removal']['stage_receipt_sha256']=terminal['stage_receipt']['sha256'];self.lastseal()
        with self.assertRaisesRegex(ValueError,'accounting differs'):self.reconstruct()

    def test_wrong_accepted_original_binding_rejected(self):
        self.adopted['report']['records']['L/O'][0]['prediction']['answer_index']=1
        with self.assertRaisesRegex(ValueError,'disposition/source'):self.reconstruct()

    def test_capability_mutation_and_late_file_mutation_rejected(self):
        result=self.reconstruct();result['actor_roles_verified']=False
        with self.assertRaisesRegex(ValueError,'capability'):e.revalidate(result)
        result=self.reconstruct();(self.root/'removal/stdout.bin').write_bytes(b'late')
        with self.assertRaises(ValueError):e.revalidate(result)
        with self.assertRaisesRegex(ValueError,'capability'):e.revalidate(dict(result))


class AuditPathTests(unittest.TestCase):
    def test_interpreter_runtime_alias_is_resolved_to_its_exact_target(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);runtime=base/'runtime-real';runtime.mkdir();module=runtime/'codec.py';module.write_text('')
            worker=base/'worker';worker.mkdir();alias=base/'runtime-alias'
            raw=e.canonical(dict(path=str(module),mode='r',flags=0,allowed=True,basis='code_model_runtime',role='coordinator'))+b'\n'
            inputs=SimpleNamespace(bound=lambda proof:raw);resolve=Path.resolve
            def resolved(value,*args,**kwargs):return runtime if value==alias else resolve(value,*args,**kwargs)
            frame=dict(model_receipt={'path':'receipt'},model_license={'path':'license'},code_files=[])
            with patch.object(sys,'prefix',str(alias)),patch.object(sys,'base_prefix',str(alias)),patch.object(Path,'resolve',resolved):
                audit=e._audit(worker,'pair_prepare',frame,{'input_files':[]},{'path':'frame'},{'path':'job'},
                    {'bindings':{}},[],inputs,{})
            self.assertEqual(audit['denied_operations'],0)

    def test_cutoff_is_between_original_root_and_pair_worker_reservations(self):
        started='2026-11-07T00:00:00+00:00'; entered='2026-11-07T00:01:00+00:00'
        for cutoff in ('2026-11-06T23:59:59+00:00','2026-11-07T00:01:01+00:00'):
            with self.subTest(cutoff=cutoff),self.assertRaisesRegex(ValueError,'cutoff'):
                e._chronology(started,entered,'pair_prepare',{'cutoff':cutoff})
        e._chronology(started,entered,'pair_prepare',{'cutoff':'2026-11-07T00:00:30+00:00'})

    def test_copied_capability_internals_cannot_issue_a_verified_result(self):
        forged=e.VerifiedEnvelope(baseline_acceptance={})
        forged._inputs=SimpleNamespace(unchanged=lambda:None)
        forged._fingerprint=e.fingerprint(dict(forged));forged._adopted_fingerprint=e.fingerprint({})
        with patch.object(e,'_adopt',return_value={}),self.assertRaisesRegex(ValueError,'capability'):
            e.revalidate(forged)

    def test_unavailable_local_drive_does_not_loop_or_grant_access(self):
        fake=Path(__file__).resolve().parents[2]
        row=dict(path=str(fake/'absent/file'),mode='r',flags=0,allowed=True,basis='coordinator_input',role='coordinator')
        raw=e.canonical(row)+b'\n';inputs=SimpleNamespace(bound=lambda proof:raw)
        frame=dict(model_receipt={'path':'receipt'},model_license={'path':'license'},code_files=[])
        with patch.object(Path,'exists',return_value=False),self.assertRaisesRegex(ValueError,'no existing local ancestor'):
            e._audit(fake,'pair_prepare',frame,{'input_files':[]},{'path':'frame'},{'path':'job'},
                {'bindings':{}},[],inputs,{})


class CompleteIntegrationTests(unittest.TestCase):
    def test_strict_original_adoption_envelope_and_new_native_source_join(self):
        from experiments.litqa_refinement import evaluation
        from experiments.labbench import evaluate as native_scoring
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);authority_root=Path(temp.name)
        note=authority_root/'protocol.md';note.write_text('Invented two-question integration protocol.')
        addendum=authority_root/'endpoints.md';addendum.write_text('Invented prospective endpoint declaration.')
        endpoint=authority_root/'ENDPOINTS.json'
        write(endpoint,evaluation.endpoint_contract(datetime.now(timezone.utc).isoformat(),proof(note),proof(addendum)))
        fixture=EnvelopeTests('runTest');fixture.complete_history=True
        self.addCleanup(fixture.doCleanups);fixture.setUp()
        value=evaluation.reconstruct(fixture.descriptor,baseline_acceptance=fixture.acceptance)
        self.assertTrue(value.report['native_calls_checked'] and value.report['source_lineage_checked'])
        self.assertEqual(value.report['incremental_resources']['physical_totals']['generation_calls'],6)
        self.assertEqual(len(value.report['records']['repair']),2)
        self.assertEqual(value.envelope['baseline_adoption']['questions'],2)
        self.assertFalse(value.envelope['baseline_adoption']['semantic_reconstruction_recomputed'])
        self.assertTrue(value.envelope['supervised_root_verified'] and value.envelope['actor_roles_verified'])
        self.assertIs(evaluation.revalidate(value),value)
        keys=authority_root/'KEYS.json';queries=encode(value.report['queries'])
        write(keys,dict(kind='sc05_fictional_evaluation_inputs_v1',role='evaluation_only',queries=queries,
            references=[dict(id=q['id'],answer_index=0,unsure_index=1) for q in queries],
            groups=[[q['id']] for q in queries],annotations={q['id']:[] for q in queries}))
        scorer=native_scoring.evaluate_schedule
        deps={inspect.getsourcefile(scorer.__globals__[name]) for name in
              ('freeze','evidence_ids','validate_prediction','validate_query','visible_unsure_index')}
        authority=authority_root/'AUTHORITY.json'
        write(authority,dict(kind='sc05_refinement_evaluation_authority_v1',role='evaluation_only',purpose='fictional_qualification',
            created_at_utc=datetime.now(timezone.utc).isoformat(),producer=fixture.descriptor,baseline_acceptance=fixture.acceptance,
            original_inputs=proof(keys),endpoint_freeze=proof(endpoint),native_scorer=proof(Path(native_scoring.__file__)),
            native_scorer_dependencies=[proof(Path(p)) for p in sorted(deps)],native_scorer_archive=None))
        scored=evaluation.evaluate(value,proof(authority),native_scorer=scorer)
        self.assertTrue(scored['provenance_validated'])
        self.assertEqual(scored['native_agreement']['generated_conditions_checked'],3)
        self.assertEqual(scored['logical_condition_resources']['conditions']['repair']['model_usage']['generation_calls'],6)


if __name__=='__main__':unittest.main()
