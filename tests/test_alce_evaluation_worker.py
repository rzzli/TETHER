"""Invented captures and dependencies only; no released data or model loads.

Generation ownership verification is explicitly substituted by invented metadata
here; source/capture assembly and selected native metric bodies remain genuine.
"""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch

from experiments.alce import evaluation_worker as w
from tether_engine.serde import ContractError,canonical,encode,freeze
from tests import test_alce_evaluation as joins,test_alce_native_worker as workers
from tests.test_alce_native_runtime import Model,proof,put
from tests.test_alce_native_metrics import InventedMean,sentences


class InventedRNG:
    def __init__(self):self.seed_value=0
    def seed(self,value):self.seed_value=value
    def get_state(self):return ('invented-RNG',NS(tolist=lambda:[self.seed_value]),0,0,0.0)


def invented_execute(p,*,fail=False,wrong_import=False,deny=False):
    job=json.loads(Path(p['path']).read_bytes());plan=json.loads(Path(job['join_plan']['path']).read_bytes())
    generation=dict(job['generation'],report={k:plan[k] for k in ('preparation','expected_counts','generation','owners','attempts')},
        source_projection_verified=True,wire_usage_verified=True)
    path=Path(next(iter(job['lexical_sources'].values()),next(iter(job['runtime_sources'].values()),job['interpreter']))['path'])
    modules=workers.invented_modules(path,fail)
    modules['torch'].float32='fp32'
    modules['transformers'].AutoModelForQuestionAnswering=NS(from_pretrained=Mock(return_value=(Model('fp32'),
        dict(missing_keys=[],unexpected_keys=[],mismatched_keys=[],error_msgs=[]))))
    modules['transformers'].pipeline=Mock(return_value=Mock(return_value={'answer':'invented','score':1.0}))
    if job['group']=='mauve':modules['mauve']=NS(__file__=str(path))
    def lexical(names):
        result={}
        for name in names:
            if name=='np':value=NS(mean=InventedMean.mean,random=InventedRNG())
            elif name=='sent_tokenize':value=NS(sent_tokenize=sentences,data=NS(path=[]))
            else:raise AssertionError('Unexpected invented optional lexical dependency')
            value.__file__=str(path if not wrong_import else Path(__file__).resolve());result[name]=value
        return result
    assets=lambda *args,**kw:NS(product=args[1],root=Path(job['acquisition_receipt']['path']).parent,
        revalidate=Mock(),provenance=lambda:dict(product=args[1],invented=True))
    if deny:
        old=lexical
        def lexical(names):
            import socket
            socket.getaddrinfo('invented.invalid',80)
            return old(names)
    class InventedMauve(w.runtime._Runtime):
        def metric(self,rows,sources):
            assert len(rows)==2 and all('\n' not in row['output'] and '[1]' not in row['output'] for row in rows)
            assert all(row['output'].startswith(' ') for row in rows)
            return self.call('mauve',rows,lambda:dict(native_value=50.0,scope='Invented feature backend',count=len(rows)))
    original=w.runtime.MauveRuntime
    with patch.object(w,'verify_generation',return_value=freeze(generation)),patch.object(w.runtime,'MauveRuntime',
        InventedMauve if job['group']=='mauve' else original):
        return w.execute(p,module_loader=lambda **kw:modules,lexical_loader=lexical,asset_loader=assets,resource_sampler=workers.sample)


class EvaluationWorkerTests(unittest.TestCase):
    def setUp(self):
        self.join=joins.EvaluationTests();self.join.setUp();self.addCleanup(self.join.doCleanups)
        self.base=workers.WorkerTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.root=self.base.root;gen=self.root/'generation';gen.mkdir()
        report=put(gen/'REPORT.json',{'invented_process_capture':True})
        rp=put(gen/'RECEIPT.json',{'files':{'REPORT.json':report}})
        self.job=dict(schema_version=2,kind='alce_evaluation_worker_job_v2',family='asqa',group='true',
            join_plan=self.join.pp,generation=dict(root=str(gen),receipt_sha256=rp['sha256']),output=str(self.root/'metric-worker'),
            interpreter=self.base.job['interpreter'],offline=self.base.job['offline'],limits=dict(self.base.job['limits'],
                seconds=40,finalization_seconds=120,max_calls=20,input_bytes=16*1024**2,output_bytes=16*1024**2),placement=self.base.job['placement'],
            acquisition_receipt=self.base.job['acquisition_receipt'],runtime_sources=self.base.job['runtime_sources'],
            lexical_sources={n:proof(self.base.module) for n in ('np','sent_tokenize')},punkt={},rng_seed=None,code_pins=w.source_pins(),
            package_context=w.package_context(time.monotonic()+30))
        for name in w.PUNKT:self.job['punkt'][name]=put(self.root/name,{'invented_table':name})
        self.jp=put(self.root/'METRIC-JOB.json',self.job)

    def write(self):self.jp=put(self.root/'METRIC-JOB.json',self.job)

    def test_legacy_job_rejected_before_dispatch_or_output(self):
        self.job.update(schema_version=1,kind='alce_evaluation_worker_job_v1')
        self.job.pop('package_context',None);self.write()
        with patch.object(w.base.processes,'supervise_command',side_effect=AssertionError('Legacy job dispatched')) as child:
            with self.assertRaises(ContractError):w.load_job(self.jp)
            with self.assertRaises(ContractError):w.supervise(self.jp,self.root/'legacy-outer')
            child.assert_not_called()
        self.assertFalse(Path(self.job['output']).exists());self.assertFalse((self.root/'legacy-outer').exists())

    def test_package_origin_and_source_context_tamper_rejects_before_dispatch(self):
        original=copy.deepcopy(self.job);context=original['package_context'];key=next(iter(context['source_identities']))
        copied=self.root/'copied-package';copied.mkdir();initializer=copied/'__init__.py'
        initializer.write_bytes(Path(context['package_origins']['tether_engine']['path']).read_bytes())
        changes=(lambda c:c['package_origins']['tether_engine'].update(sha256='0'*64),
            lambda c:c['package_origins'].update(tether_engine=proof(initializer)),
            lambda c:c['package_origins'].pop('tether'),
            lambda c:c['source_identities'][key].update(sha256='0'*64),
            lambda c:c['code_files'].pop(),lambda c:c.update(extra=True))
        for change in changes:
            self.job=copy.deepcopy(original);change(self.job['package_context']);self.write()
            with self.subTest(change=change),patch.object(w.base.processes,'supervise_command',side_effect=AssertionError('Invalid origins dispatched')) as child:
                with self.assertRaises(ContractError):w.supervise(self.jp,self.root/'bad-origin')
                child.assert_not_called()
            self.assertFalse((self.root/'bad-origin').exists());self.assertFalse(Path(self.job['output']).exists())

    def test_actual_production_bootstrap_uses_origins_then_stops_at_invented_admission(self):
        # The real fixed command, without a replacement worker/main, must pass
        # origin admission and then fail at the deliberately wrong generation
        # receipt before any asset loader, model import or scoring.
        self.job['generation']['receipt_sha256']='0'*64
        self.job['limits'].update(process_bytes=512*1024**2,minimum_available_host_bytes=1);self.write()
        command=w._command(self.job,self.jp)
        self.assertEqual(command[1:5],['-I','-B','-c',w.WORKER_BOOTSTRAP])
        self.assertEqual(json.loads(command[6]),self.job['package_context']['package_origins'])
        result=w.base.processes.supervise_command(command,limits=w.base.processes.ProcessLimits(30,1024**2))
        self.assertNotEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        self.assertTrue(result.supervision['process_reaped'])
        output=Path(self.job['output']);self.assertTrue((output/'REQUEST.json').is_file(),result.stderr.decode(errors='replace'))
        failure=json.loads((output/'FAILURE.json').read_bytes())
        self.assertEqual(failure['stage'],'admission');self.assertIn('External generation receipt required',failure['reason'])
        self.assertFalse((output/'WORKER-RECEIPT.json').exists());self.assertFalse((output/'results').exists())

    def test_actual_bootstrap_rejects_changed_initializer_before_worker_output(self):
        changed=copy.deepcopy(self.job);changed['package_context']['package_origins']['tether_engine']['sha256']='0'*64
        command=w._command(changed,self.jp)
        result=w.base.processes.supervise_command(command,limits=w.base.processes.ProcessLimits(30,1024**2))
        self.assertNotEqual(result.returncode,0);self.assertTrue(result.supervision['process_reaped'])
        self.assertIn(b'Package initializer differs from admitted origin',result.stderr)
        self.assertFalse(Path(self.job['output']).exists())

    def execute(self,**kw):return invented_execute(self.jp,**kw)
    def replay(self):return w.verify_worker(Path(self.job['output']),self.jp,self.job,
        tuple(n for n in w.join.RECIPES[self.job['family']] if n in w.join.GROUPS[self.job['group']]),time.monotonic()+30)
    def reseal(self,complete=None):
        root=Path(self.job['output'])
        if complete is not None:put(root/'COMPLETE.json',complete)
        receipt={'kind':'alce_metric_worker_receipt_v1','status':'completed','files':w._inventory(root,time.monotonic()+30)}
        return put(root/'WORKER-RECEIPT.json',receipt)

    def test_resealed_legacy_or_extended_job_rejected_by_independent_replay(self):
        self.execute();root=Path(self.job['output']);original=copy.deepcopy(self.job)
        request=json.loads((root/'REQUEST.json').read_bytes());complete=json.loads((root/'COMPLETE.json').read_bytes())
        for change in (lambda j:j.update(kind='alce_evaluation_worker_job_v1',schema_version=1),lambda j:j.update(extra=True)):
            self.job=copy.deepcopy(original);change(self.job);self.write()
            request['job']=self.jp;complete['job']=self.jp;put(root/'REQUEST.json',request);self.reseal(complete)
            with self.subTest(change=change),self.assertRaises(ContractError):self.replay()

    def test_resident_true_full_family_branching_and_durable_native_calls(self):
        rp=self.execute();self.assertEqual(self.replay(),rp)
        complete=json.loads((Path(self.job['output'])/'COMPLETE.json').read_bytes())
        self.assertEqual(complete['metrics'],['citations']);self.assertEqual(len(complete['call_files']),6)
        self.assertEqual(len(complete['bridge_calls']),6);self.assertEqual(len(complete['native']['calls']),6)
        self.assertIsNone(complete['rng']);self.assertEqual(complete['offline']['denied_network_attempts'],0)

    def test_lexical_worker_never_loads_model_and_reports_explicit_rng(self):
        self.job.update(family='qampari',group='lexical',runtime_sources={},acquisition_receipt=None,placement={},
            lexical_sources={'np':proof(self.base.module)},punkt={},rng_seed=73)
        self.job['limits']['gpu_bytes']=0;self.write()
        with patch.object(w.runtime,'TrueRuntime',side_effect=AssertionError('Model loaded')):
            rp=self.execute()
        self.assertEqual(self.replay(),rp)
        c=json.loads((Path(self.job['output'])/'COMPLETE.json').read_bytes())
        self.assertEqual(c['metrics'],['length','str_em','qampari']);self.assertEqual(c['call_files'],[])
        self.assertIsNone(c['native']);self.assertEqual(c['rng']['seed'],73);self.assertEqual(c['rng']['seeded']['keys'],[73])

    def test_native_singleton_qa_failure_is_retained_without_repair_or_retry(self):
        self.job.update(group='qa',lexical_sources={'np':proof(self.base.module)},punkt={});self.write()
        with self.assertRaises(TypeError):self.execute()
        root=Path(self.job['output']);failure=json.loads((root/'FAILURE.json').read_bytes())
        self.assertEqual(failure['stage'],'metrics');self.assertEqual(len(failure['native']['calls']),1)
        self.assertEqual(len(failure['completed_call_files']),1);self.assertFalse((root/'WORKER-RECEIPT.json').exists())
        with self.assertRaises(ContractError):self.execute()

    def test_mauve_gets_one_complete_native_normalized_family(self):
        self.job.update(group='mauve',lexical_sources={},punkt={})
        self.job['runtime_sources']['mauve']=proof(self.base.module);self.write()
        rp=self.execute();self.assertEqual(self.replay(),rp)
        complete=json.loads((Path(self.job['output'])/'COMPLETE.json').read_bytes())
        self.assertEqual(len(complete['native']['calls']),1);self.assertEqual(len(complete['call_files']),1)
        self.assertEqual(complete['metrics'],['mauve']);self.assertEqual(complete['bridge_calls'],[])

    def test_native_error_keeps_failed_physical_attempt_without_retry(self):
        with self.assertRaises(RuntimeError):self.execute(fail=True)
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertEqual(len(failure['native']['calls']),1);self.assertEqual(failure['native']['calls'][0]['status'],'failed')
        self.assertEqual(failure['completed_call_files'],[])

    def test_invalid_job_source_scope_seed_or_overlap_rejects_before_output(self):
        baseline=copy.deepcopy(self.job)
        for defect in ('source','group','seed','output','interpreter'):
            self.job=copy.deepcopy(baseline)
            if defect=='source':self.job['code_pins']={}
            elif defect=='group':self.job['group']='qa'
            elif defect=='seed':self.job['rng_seed']=True
            elif defect=='interpreter':self.job['interpreter']=proof(self.base.module)
            else:self.job['output']=str(Path(self.job['generation']['root'])/'nested')
            self.write()
            with self.subTest(defect=defect),self.assertRaises(ContractError):self.execute()
            self.assertFalse(Path(self.job['output']).exists())

    def test_generation_owner_disagreement_stops_before_model_load(self):
        with patch.object(w,'verify_generation',return_value={'root':'wrong'}),self.assertRaises(ContractError):
            w.execute(self.jp,resource_sampler=workers.sample,module_loader=Mock(side_effect=AssertionError('model import')))
        self.assertTrue((Path(self.job['output'])/'FAILURE.json').is_file())

    def test_physical_call_cap_and_native_failure_stop_without_success(self):
        self.job['limits']['max_calls']=1;self.write()
        with self.assertRaises(ContractError):self.execute()
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertEqual(len(failure['native']['calls']),1);self.assertEqual(len(failure['completed_call_files']),1)
        self.assertFalse((Path(self.job['output'])/'WORKER-RECEIPT.json').exists())

    def test_wrong_actual_import_rejects_before_native_call(self):
        with self.assertRaises(ContractError):self.execute(wrong_import=True)
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertIsNone(failure['native']);self.assertEqual(failure['completed_call_files'],[])

    def test_network_denial_is_retained_and_no_metric_success(self):
        with self.assertRaises(PermissionError):self.execute(deny=True)
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertEqual(failure['offline']['denied_network_attempts'],1)
        self.assertFalse((Path(self.job['output'])/'WORKER-RECEIPT.json').exists())

    def test_output_write_failure_keeps_attempt_and_never_repeats(self):
        original=w.base.OutputBudget.write
        def write(budget,path,value):
            if path.parent.name=='calls':raise OSError('Invented durable result write failure')
            return original(budget,path,value)
        with patch.object(w.base.OutputBudget,'write',write),self.assertRaises(OSError):self.execute()
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertEqual(len(failure['native']['calls']),1);self.assertEqual(len(failure['completed_call_files']),0)

    def test_resealed_result_resource_native_or_clock_changes_rejected(self):
        self.execute();root=Path(self.job['output']);baseline=json.loads((root/'COMPLETE.json').read_bytes())
        for change in (lambda c:c.update(wall_seconds=-1),lambda c:c['resource_samples'][0].update(process_bytes=101),
                       lambda c:c['native']['gpu'].update(peak_allocated_bytes=99999),lambda c:c['native']['calls'][0].update(request_sha256='0'*64),
                       lambda c:c['offline'].update(denied_network_attempts=1)):
            value=copy.deepcopy(baseline);change(value);self.reseal(value)
            with self.assertRaises(ContractError):self.replay()
        self.reseal(baseline)
        path=root/'calls/000000.json';row=json.loads(path.read_bytes());row['result']=0;put(path,row)
        baseline['call_files'][0]=proof(path);self.reseal(baseline)
        with self.assertRaises(ContractError):self.replay()

    def test_unknown_members_markers_and_late_generation_bytes_reject(self):
        self.execute();root=Path(self.job['output'])
        for name in ('FAILURE.json','DEADLINE.json','RESOURCE-LIMIT.json'):
            path=root/name;put(path,{'invented':True})
            with self.assertRaises(ContractError):self.replay()
            path.unlink()
        extra=root/'unregistered';extra.mkdir();self.reseal()
        with self.assertRaises(ContractError):self.replay()
        extra.rmdir();self.reseal()
        (Path(self.job['generation']['root'])/'REPORT.json').write_bytes(b'late mutation')
        with self.assertRaises(ContractError):self.replay()

    def test_resealed_bridge_calls_and_source_metadata_must_match_native_results(self):
        self.execute();root=Path(self.job['output']);baseline=json.loads((root/'COMPLETE.json').read_bytes())
        for change in (lambda c:c['bridge_calls'][0].update(entailment=0),
                       lambda c:c['bridge']['sources']['eval.py'].update(sha256='0'*64)):
            complete=copy.deepcopy(baseline);change(complete);self.reseal(complete)
            with self.assertRaises(ContractError):self.replay()

    def test_real_model_free_child_supervision_and_read_only_replay(self):
        # Keep the actual initializer bootstrap and replace only the final main
        # with an explicitly invented native dependency boundary.
        tail='from experiments.alce.evaluation_worker import main\nmain()\n'
        self.assertTrue(w.WORKER_BOOTSTRAP.endswith(tail))
        code=w.WORKER_BOOTSTRAP[:-len(tail)]+"from tests.test_alce_evaluation_worker import invented_execute,proof\n"+\
            "p=invented_execute(proof(Path(sys.argv[3])))\nprint('Invented native feature timing: 0.1s')\nprint(json.dumps(dict(status='completed',receipt=p)),flush=True)\nprint('  ')\n"
        original=w.base.processes.supervise_command
        def launch(command,*,limits):
            self.assertEqual(command,w._command(self.job,self.jp));command=list(command);command[4]=code
            return original(command,limits=limits)
        with patch.object(w.base,'contain_process_tree',return_value=object()),patch.object(w.base.processes,'supervise_command',side_effect=launch):
            try:p=w.supervise(self.jp,self.root/'outer')
            except BaseException as error:
                stderr=self.root/'outer/stderr.bin'
                if stderr.is_file():error.add_note('Retained invented child stderr: '+stderr.read_text(errors='replace')[:8000])
                raise
        value=w.verify_execution(dict(root=str(self.root/'outer'),receipt_sha256=p['sha256']))
        self.assertEqual(value['worker_receipt'],self.replay())
        self.assertFalse(value['scientific_metric_truth_independently_recomputed'])
        root=self.root/'outer';terminal=(root/'stdout.bin').read_bytes()
        self.assertIn(b'Invented native feature timing',terminal)
        original_complete=json.loads((root/'COMPLETE.json').read_bytes())
        for changed in (terminal+b'not-json\n',terminal+canonical(dict(status='completed',receipt={'sha256':'0'*64}))+b'\n'):
            (root/'stdout.bin').write_bytes(changed)
            process=json.loads((root/'PROCESS.json').read_bytes())
            process['supervision']['retained_stdout_bytes']=len(changed);process['supervision']['observed_stdout_bytes']=len(changed)
            put(root/'PROCESS.json',process)
            r=put(root/'RECEIPT.json',dict(kind='alce_metric_execution_receipt_v1',status='verified',
                files={x.name:proof(x) for x in root.iterdir() if x.name!='RECEIPT.json'}))
            with self.assertRaises(ContractError):w.verify_execution(dict(root=str(root),receipt_sha256=r['sha256']))
        (root/'stdout.bin').write_bytes(terminal)
        process['supervision']['retained_stdout_bytes']=len(terminal);process['supervision']['observed_stdout_bytes']=len(terminal)
        put(root/'PROCESS.json',process)
        original_complete['timing']['finalization_seconds']+=1;put(root/'COMPLETE.json',original_complete)
        r=put(root/'RECEIPT.json',dict(kind='alce_metric_execution_receipt_v1',status='verified',
            files={x.name:proof(x) for x in root.iterdir() if x.name!='RECEIPT.json'}))
        with self.assertRaises(ContractError):w.verify_execution(dict(root=str(root),receipt_sha256=r['sha256']))

    def test_finalization_limit_required_and_strict_before_child_dispatch(self):
        baseline=copy.deepcopy(self.job)
        for value in (None,0,True,-1,1.5,86401):
            self.job=copy.deepcopy(baseline)
            if value is None:self.job['limits'].pop('finalization_seconds',None)
            else:self.job['limits']['finalization_seconds']=value
            self.write()
            with self.subTest(value=value),patch.object(w.base.processes,'supervise_command',side_effect=AssertionError('Invalid job dispatched')) as child:
                with self.assertRaises(ContractError):w.supervise(self.jp,self.root/'invalid-finalization')
                child.assert_not_called()
            self.assertFalse((self.root/'invalid-finalization').exists())
        self.job=copy.deepcopy(baseline);self.job['limits']['finalization_seconds']=120;self.write()
        self.assertEqual(w.load_job(self.jp)[0]['limits']['finalization_seconds'],120)

    def test_replay_reserve_is_separate_from_exhausted_child_budget(self):
        # Invented process clocks and a stubbed worker replay isolate supervisor
        # accounting; this is not a native/source acceptance capability.
        current=[time.monotonic()];start=current[0];worker=Path(self.job['output']);worker.mkdir()
        put(worker/'COMPLETE.json',{'wall_seconds':35})
        rp=put(worker/'WORKER-RECEIPT.json',{'invented_clock_only':True})
        self.job['limits']['finalization_seconds']=120
        def load(*args,**kw):current[0]+=5;return self.job,{},('citations',),worker,[]
        def child(command,*,limits):
            current[0]+=64
            stdout=canonical(dict(status='completed',receipt=rp))+b'\n'
            report=dict(schema_version=1,method='tether.process_envelope.v1',limits=limits.payload(),termination_reason='exited',
                execution_elapsed_seconds=63,total_elapsed_seconds=64,retained_stdout_bytes=len(stdout),retained_stderr_bytes=0,
                observed_stdout_bytes=len(stdout),observed_stderr_bytes=0,observed_counts_are_lower_bounds=False,
                pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[])
            return NS(returncode=0,stdout=stdout,stderr=b'',supervision=report)
        def replay(*args):
            current[0]+=5
            self.assertGreater(args[-1],current[0],'Post-child replay must have its declared independent reserve')
            return rp
        with patch.object(w,'time',NS(monotonic=lambda:current[0])),patch.object(w,'load_job',side_effect=load),\
             patch.object(w.base,'contain_process_tree',return_value=object()),patch.object(w.base,'DeadlineWatchdog',return_value=nullcontext()),\
             patch.object(w.base.processes,'supervise_command',side_effect=child),patch.object(w,'verify_worker',side_effect=replay):
            p=w.supervise(self.jp,self.root/'reserved-replay')
        self.assertEqual(current[0]-start,74)
        c=json.loads((self.root/'reserved-replay/COMPLETE.json').read_bytes())
        self.assertEqual(c['timing'],dict(predispatch_seconds=5,child_return_seconds=69,finalization_seconds=5))
        self.assertTrue(Path(p['path']).is_file())

    def test_finalization_clock_exhaustion_and_tampering_reject(self):
        limits=w.base.processes.ProcessLimits(65,4*1024**2)
        process=dict(execution_elapsed_seconds=63,total_elapsed_seconds=64)
        c=dict(wall_seconds=74,timing=dict(predispatch_seconds=5,child_return_seconds=69,finalization_seconds=5))
        w._check_timing(self.job,limits,process,c,35)
        changes=(lambda c:c.update(wall_seconds=189),lambda c:c['timing'].update(finalization_seconds=120),
            lambda c:c['timing'].update(predispatch_seconds=True),lambda c:c['timing'].update(predispatch_seconds=6),
            lambda c:c['timing'].update(child_return_seconds=70),lambda c:c['timing'].update(child_return_seconds=68),
            lambda c:c['timing'].update(finalization_seconds=float('nan')))
        for change in changes:
            changed=copy.deepcopy(c);change(changed)
            with self.subTest(change=change),self.assertRaises(ContractError):w._check_timing(self.job,limits,process,changed,35)
        for process in (dict(execution_elapsed_seconds=64.5,total_elapsed_seconds=65),
                        dict(execution_elapsed_seconds=34,total_elapsed_seconds=64)):
            with self.assertRaises(ContractError):w._check_timing(self.job,limits,process,c,35)
        process=dict(execution_elapsed_seconds=63,total_elapsed_seconds=64)
        c['wall_seconds']=189;c['timing']['finalization_seconds']=120
        with self.assertRaises(ContractError):w._check_timing(self.job,limits,process,c,35)
        c['wall_seconds']=188.5;c['timing']['finalization_seconds']=119.5
        w._check_timing(self.job,limits,process,c,35)

    def test_terminal_parser_uses_only_final_nonempty_utf8_line(self):
        terminal=dict(status='completed',receipt={'invented':'proof'})
        self.assertEqual(w._terminal(b'Native feature extraction\n'+canonical(terminal)+b'\n \t\n'),terminal)
        for raw in (b'',b' \n\t',canonical(terminal)+b'\nNative unfinished log',
                    canonical(terminal)+b'\n{',b'\xff\n'+canonical(terminal)):
            with self.subTest(raw=raw),self.assertRaises((ContractError,ValueError)):w._terminal(raw)

    def test_real_child_timeout_is_reaped_and_retained_without_retry(self):
        original=w.base.processes.supervise_command
        def launch(command,*,limits):return original([sys.executable,'-I','-B','-c','import time;time.sleep(10)'],
            limits=w.base.processes.ProcessLimits(.15,limits.max_output_bytes))
        with patch.object(w.base,'contain_process_tree',return_value=object()),patch.object(w.base.processes,'supervise_command',side_effect=launch),self.assertRaises(Exception):
            w.supervise(self.jp,self.root/'outer-timeout')
        root=self.root/'outer-timeout';process=json.loads((root/'PROCESS.json').read_bytes())
        self.assertTrue(process['supervision']['process_reaped']);self.assertTrue((root/'FAILURE.json').exists())
        self.assertFalse((root/'RECEIPT.json').exists());self.assertFalse(Path(self.job['output']).exists())

    def test_capture_write_failure_retains_process_and_preserves_primary_error(self):
        error=KeyboardInterrupt('Invented child interruption')
        error.tether_engine_result=NS(returncode=17,stdout=b'partial-out',stderr=b'partial-error',supervision={'invented':True})
        original=Path.open
        def fail_stdout(path,*args,**kwargs):
            if path.name=='stdout.bin':raise OSError('Invented stdout capture failure')
            return original(path,*args,**kwargs)
        with patch.object(w.base,'contain_process_tree',return_value=object()),patch.object(w.base.processes,'supervise_command',side_effect=error),patch.object(Path,'open',fail_stdout):
            with self.assertRaises(KeyboardInterrupt) as caught:w.supervise(self.jp,self.root/'outer-interrupted')
        self.assertIs(caught.exception,error);root=self.root/'outer-interrupted'
        self.assertEqual(json.loads((root/'PROCESS.json').read_bytes())['returncode'],17)
        self.assertEqual((root/'stderr.bin').read_bytes(),b'partial-error')
        self.assertIn('stdout',str(error.__notes__));self.assertFalse((root/'RECEIPT.json').exists())

    def test_nested_receipt_name_is_not_excluded_from_inventory_or_budget(self):
        self.execute();root=Path(self.job['output'])
        for directory in ('calls','results'):
            path=root/directory/'WORKER-RECEIPT.json';put(path,{'invented_extra':True})
            try:
                self.reseal()
                with self.assertRaises(ContractError):self.replay()
            finally:path.unlink()

    def test_copied_punkt_tables_must_match_the_qualified_original_bytes(self):
        self.execute();root=Path(self.job['output'])
        (root/'nltk_data/tokenizers/punkt_tab/english/abbrev_types.txt').write_bytes(b'altered table')
        self.reseal()
        with self.assertRaises(ContractError):self.replay()

    def test_terminal_journal_call_count_cannot_contradict_completed_records(self):
        self.execute();root=Path(self.job['output']);path=root/'journal.jsonl'
        events=list(w.base.journal_rows(proof(path),self.job['limits']['output_bytes'],time.monotonic()+30))
        path.unlink();journal=w.base.NativeJournal(path,w.base.OutputBudget(self.job['limits']['output_bytes']))
        for event in events:
            details=dict(event['details'])
            if event['event']=='evaluation_completed':details['physical_calls']=0
            journal.append(event['event'],**details)
        self.reseal()
        with self.assertRaises(ContractError):self.replay()


if __name__=='__main__':unittest.main()
