"""Invented schedules/HTTP/ownership only; no ALCE payloads or real model calls."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.alce import generation as g
from tests import test_alce_data_views as vf,test_alce_producer as pf
put,proof,Response=vf.put,vf.proof,pf.Response


class NoDeadline:
    def __init__(self,*args,**kwargs):pass
    def __enter__(self):return self
    def __exit__(self,*unused):pass


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.views=vf.ViewsTests('runTest');self.views.setUp();self.addCleanup(self.views.doCleanups)
        self.root=self.views.root;self.prepared=g.encode(self.views.prepare())
        self.producer=pf.ProducerTests('runTest');self.producer.setUp();self.addCleanup(self.producer.doCleanups)
        self.model_receipt=proof(self.producer.root/'assets/acquisition.json')
        self.configs={f:dict(self.producer.configuration,family=f,max_new_tokens=300,seed=20261107) for f in g.FAMILIES}
        self.gates={name:put(self.root/(name+'.json'),dict(kind='invented_gate',status='PASS'))
                    for name in ('free_text','true_baseline','qa','mauve','lexical')}
        self.limits=g.Limits(900,20,32*1024**2,20000,16384,180)
        self.pp=g.prepare_plan(self.prepared,self.root/'freeze',configurations=self.configs,model_receipt=self.model_receipt,
            port=55599,alias='invented-alce',limits=self.limits,purpose='invented_qualification',gate_receipts=self.gates)
        self.plan=g._read(self.pp,time.monotonic()+30)
        self.release=put(self.root/'RELEASE.json',dict(kind='alce_generation_release_v1',status='approved',plan=self.pp,
            qualification_receipts=self.gates,native_baselines_qualified=True,post_candidate_evaluator_gate_required=True,
            automatic_retries=0,provider_cost_usd=0,output=str(self.root/'parent')))

    def job(self,name='worker'):
        value={k:self.plan[k] for k in ('generation_files','ordered_ids','expected_counts','configurations','model_receipt',
            'model_provenance','port','alias','limits','code_files','source_identities','package_origins','interpreter')}
        value.update(kind='alce_generation_actor_job_v2',output=str(self.root/name),deadline_monotonic=time.monotonic()+800,plan_sha256=self.pp['sha256'])
        return put(self.root/(name+'-JOB.json'),value),value

    @contextmanager
    def invented_runtime(self,*,fail_at=None):
        fixture=self.producer;calls=[];real_execute=g.producer.execute_once
        class Owner:
            def __init__(self,spec,bindings,output,journal,parent_deadline):
                self.spec,self.bindings,self.output,self.journal=spec,bindings,output,journal
                self.terminal_record=dict(pid=24680,started=True,server_stopped=False,secondary_failures=[])
            def assert_ready(self):pass
            def __enter__(self):
                # Explicitly invented OS transport evidence, not a real process.
                sys.audit('subprocess.Popen',g.encode(self.spec)['argv'][0],g.encode(self.spec)['argv'],None,None)
                put(self.output/'server-command.json',g.encode(self.spec))
                (self.output/'server.stdout.bin').write_bytes(b'');(self.output/'server.stderr.bin').write_bytes(b'')
                self.journal.append('server_started',pid=24680);self.journal.append('server_ready',pid=24680);return self
            def __exit__(self,error_type,error,tb):
                self.terminal_record['server_stopped']=True
                self.journal.append('server_terminal',**self.terminal_record)
        def execute(owner,call,payload,**kw):
            fixture.call,fixture.payload=call,payload;calls.append(call['request']['id'])
            if fail_at==len(calls)-1:raise TimeoutError('invented native uncertainty')
            with fixture.wire(generation=Response(fixture.body())):
                return real_execute(owner,call,payload,**kw)
        with patch.object(g.runtime,'contain_process_tree',return_value=object()),patch.object(g.runtime,'DeadlineWatchdog',NoDeadline), \
             patch.object(g.producer.shared,'owned_server',side_effect=Owner),patch.object(g.producer,'execute_once',side_effect=execute), \
             patch.object(g.runtime,'process_sample',return_value=None),patch.object(g,'_host_memory',return_value=None):
            yield calls

    def test_exact_full_source_metadata_and_required_staged_gates(self):
        self.assertEqual(self.plan['expected_counts'],dict(asqa=2,qampari=2,eli5=2))
        admitted=g._admit(self.plan,time.monotonic()+30)
        self.assertEqual(dict(admitted['counts']),self.plan['expected_counts'])
        g._release(self.release,self.pp,self.plan,time.monotonic()+30,output=self.root/'parent')
        bad=dict(self.plan,purpose='production');bp=put(self.root/'BAD-PLAN.json',bad)
        with self.assertRaises(g.ContractError):g.load_plan(bp,time.monotonic()+30)
        release=g._read(self.release,time.monotonic()+30);release['native_baselines_qualified']=False
        with self.assertRaises(g.ContractError):g._release(put(self.root/'BAD-RELEASE.json',release),self.pp,self.plan,time.monotonic()+30,output=self.root/'parent')
        with self.assertRaises(g.ContractError):g.launch(self.pp,self.release,self.root/'different-output')
        self.assertFalse((self.root/'different-output').exists())
        legacy=dict(self.plan,schema_version=1,kind='alce_generation_plan_v1')
        for key in ('source_identities','package_origins'):legacy.pop(key)
        with self.assertRaisesRegex(g.ContractError,'Exact v2 generation plan'):
            g.load_plan(put(self.root/'LEGACY.json',legacy),time.monotonic()+30)

    def test_actual_worker_bootstrap_preserves_parent_import_origins_before_reservation(self):
        jp,job=self.job('already-present');Path(job['output']).mkdir()
        command=g._command(job,jp)
        result=subprocess.run(command,capture_output=True,timeout=60)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'Fresh output under an existing parent required',result.stderr)
        self.assertNotIn(b'Current code/source origins differ',result.stderr)
        self.assertEqual(list(Path(job['output']).iterdir()),[])
        changed=copy.deepcopy(job);changed['package_origins']['tether_engine']['sha256']='0'*64
        rejected=subprocess.run(g._command(changed,jp),capture_output=True,timeout=60)
        self.assertNotEqual(rejected.returncode,0)
        self.assertIn(b'Package initializer differs',rejected.stderr)
        self.assertEqual(list(Path(job['output']).iterdir()),[])

    def test_resealed_source_projection_is_reconstructed_before_child(self):
        generation=Path(self.plan['generation_files']['asqa']['path']);rows=g.parse_json(generation.read_bytes())
        rows[0]['docs'][0]['text']='substituted source'
        changed=put(generation,rows)
        rp=Path(self.prepared['root'])/'RECEIPT.json';receipt=g.parse_json(rp.read_bytes());receipt['files']['generation/asqa.json']=changed
        descriptor=dict(root=self.prepared['root'],receipt_sha256=put(rp,receipt)['sha256'])
        with self.assertRaises(g.ContractError):g.data.verify_preparation(**descriptor)

    def test_actor_exact_source_grants_reject_reference_and_network_access(self):
        output=self.root/'audit';output.mkdir();allowed=Path(self.plan['generation_files']['asqa']['path'])
        guard=g.ActorAudit([allowed],output,55599,[sys.executable]);guard.active=True
        try:
            guard.hook('open',(str(allowed),'r',0))
            for path in (Path(self.prepared['root'])/'evaluation/asqa.json',self.views.archive,self.root/'RELEASE.json'):
                with self.subTest(path=path),self.assertRaises(PermissionError):guard.hook('open',(str(path),'r',0))
            with self.assertRaises(PermissionError):guard.hook('socket.connect',(object(),('example.invalid',443)))
            with self.assertRaises(PermissionError):guard.hook('subprocess.Popen',(sys.executable,[sys.executable,'-c','bad'],None,None))
        finally:guard.close()
        self.assertEqual(guard.denied,5)

    def test_worker_full_six_case_source_wire_and_accounting_replay(self):
        jp,job=self.job()
        with self.invented_runtime() as calls:receipt=g.worker(jp)
        self.assertEqual(calls,[i for family in g.FAMILIES for i in self.plan['ordered_ids'][family]])
        report=g.verify_worker(Path(job['output']),receipt,job,time.monotonic()+60)
        self.assertEqual(report['known_measured_usage'],dict(input_tokens=300,output_tokens=108,cost_usd=0.0))
        self.assertEqual(len(report['attempts']),6)
        self.assertTrue(all(r['disposition']=='completed' and r['output'] is None for r in report['attempts']))
        self.assertEqual(report['io_denials'],0)
        root=Path(job['output']);audit=root/'io-audit.jsonl';original_audit=audit.read_bytes()
        original_receipt=(root/'RECEIPT.json').read_bytes()
        job_path=Path(jp['path']);original_job=job_path.read_bytes()
        for bad_job in (dict(job,kind='alce_generation_actor_job_v1'),dict(job,undeclared_field=False)):
            changed_job=put(job_path,bad_job);changed_receipt=g.parse_json(original_receipt)
            changed_receipt['job']=changed_job
            resealed=put(root/'RECEIPT.json',changed_receipt)
            with self.subTest(job_kind=bad_job['kind'],fields=len(bad_job)),self.assertRaisesRegex(g.ContractError,'Exact v2 actor job'):
                g.verify_worker(root,resealed,bad_job,time.monotonic()+60)
        job_path.write_bytes(original_job);(root/'RECEIPT.json').write_bytes(original_receipt)
        def reseal():
            value=g.parse_json(original_receipt);value['files']=g._inventory(root,time.monotonic()+30,omit=('RECEIPT.json',))
            return put(root/'RECEIPT.json',value)
        for event in (dict(event='socket.connect',allowed=True,basis='declared_loopback',endpoint=['203.0.113.1',443]),
                      dict(event='subprocess.Popen',allowed=True,basis='owned_server',command=['foreign-command'],executable='foreign-command')):
            audit.write_bytes(original_audit+g.canonical(event)+b'\n');substitute=reseal()
            with self.subTest(event=event['event']),self.assertRaises(g.ContractError):
                g.verify_worker(root,substitute,job,time.monotonic()+60)
        audit.write_bytes(original_audit);(root/'RECEIPT.json').write_bytes(original_receipt)
        stream=root/'server/server.stdout.bin';original_stream=stream.read_bytes()
        stream.write_bytes(b'x'*job['limits']['output_bytes']);oversized=reseal()
        with self.subTest(event='resealed_aggregate_output_overflow'),self.assertRaises(g.ContractError):
            g.verify_worker(root,oversized,job,time.monotonic()+60)
        stream.write_bytes(original_stream);(root/'RECEIPT.json').write_bytes(original_receipt)
        original=g.producer.verify_attempt;changed=False
        def late_change(*args,**kwargs):
            nonlocal changed
            result=original(*args,**kwargs)
            if not changed:
                changed=True;path=Path(job['generation_files']['asqa']['path'])
                path.write_bytes(path.read_bytes()+b'\n')
            return result
        with patch.object(g.producer,'verify_attempt',side_effect=late_change),self.assertRaises(g.ContractError):
            g.verify_worker(Path(job['output']),receipt,job,time.monotonic()+60)

    def test_native_failure_stops_schedule_and_preserves_all_denominators(self):
        jp,job=self.job()
        with self.invented_runtime(fail_at=1) as calls,self.assertRaises(TimeoutError):g.worker(jp)
        self.assertEqual(len(calls),2)
        root=Path(job['output']);partial=g.parse_json((root/'PARTIAL.json').read_bytes())
        self.assertEqual([r['disposition'] for r in partial['attempts']],['completed','failed']+['unexecuted']*4)
        self.assertEqual(partial['known_measured_usage']['input_tokens'],50)
        self.assertTrue((root/'FAILURE.json').exists());self.assertFalse((root/'RECEIPT.json').exists())
        with self.invented_runtime() as repeated,self.assertRaises(g.ContractError):g.worker(jp)
        self.assertEqual(repeated,[])

    def test_parent_failed_child_retains_process_without_another_dispatch(self):
        result=g.processes.EngineResult(1,b'partial stdout',b'error',dict(invented=True))
        with patch.object(g.runtime,'contain_process_tree',return_value=object()),patch.object(g.runtime,'DeadlineWatchdog',NoDeadline), \
             patch.object(g.processes,'supervise_command',return_value=result) as execute:
            with self.assertRaises(g.ContractError):g.launch(self.pp,self.release,self.root/'parent')
        self.assertEqual(execute.call_count,1)
        self.assertEqual((self.root/'parent/stdout.bin').read_bytes(),b'partial stdout')
        self.assertTrue((self.root/'parent/FAILURE.json').exists());self.assertFalse((self.root/'parent/RECEIPT.json').exists())

    def test_primary_interruption_survives_both_failure_record_errors(self):
        output=self.root/'failure';journal=g.RunJournal(output,kind='build');error=KeyboardInterrupt('primary')
        with patch.object(g,'_write',side_effect=OSError('record')),patch.object(journal,'append',side_effect=OSError('journal')):
            g._failure(output,journal,error,'invented')
        journal.close();self.assertEqual(len(error.__notes__),2)

    def test_whole_invented_controller_source_actor_wire_and_process_reconstruction(self):
        def supervised(command,*,limits):
            self.assertEqual(command[:3],[self.plan['interpreter']['path'],'-I','-B'])
            path=Path(command[command.index('--job')+1]);jp=proof(path)
            self.assertEqual(jp['sha256'],command[-1])
            started=time.monotonic();receipt=g.worker(jp);elapsed=time.monotonic()-started
            stdout=g.canonical(dict(receipt=receipt))
            envelope=dict(schema_version=1,method='tether.process_envelope.v1',limits=limits.payload(),termination_reason='exited',
                execution_elapsed_seconds=elapsed,total_elapsed_seconds=elapsed,retained_stdout_bytes=len(stdout),retained_stderr_bytes=0,
                observed_stdout_bytes=len(stdout),observed_stderr_bytes=0,observed_counts_are_lower_bounds=False,
                pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[])
            return g.processes.EngineResult(0,stdout,b'',envelope)
        with self.invented_runtime() as calls,patch.object(g.processes,'supervise_command',side_effect=supervised):
            descriptor=g.launch(self.pp,self.release,self.root/'parent')
        self.assertEqual(len(calls),6)
        checked=g.verify_generation(descriptor)
        self.assertTrue(checked['source_projection_verified']);self.assertTrue(checked['wire_usage_verified'])
        self.assertFalse(checked['scientific_correctness_evaluated'])
        root=Path(descriptor['root']);command=g.parse_json((root/'COMMAND.json').read_bytes());command[-1]='0'*64
        changed=put(root/'COMMAND.json',command);receipt=g.parse_json((root/'RECEIPT.json').read_bytes())
        receipt['files']['COMMAND.json']=changed;rp=put(root/'RECEIPT.json',receipt)
        with self.assertRaisesRegex(g.ContractError,'Pinned actor command'):
            g.verify_generation(dict(root=str(root),receipt_sha256=rp['sha256']))

    def test_output_ceiling_and_monitor_failure_are_terminal(self):
        root=self.root/'oversize';root.mkdir();(root/'bytes').write_bytes(b'12345')
        self.assertEqual(g._size(root,5),5)
        with self.assertRaises(g.ContractError):g._size(root,4)
        monitor=g.OutputWatchdog(root,4)
        with patch.object(monitor.stop,'wait',return_value=False),patch.object(g.os,'_exit',side_effect=SystemExit(125)):
            with self.assertRaises(SystemExit):monitor.poll()
        self.assertTrue((root/'OUTPUT-LIMIT.json').is_file())

    def test_output_monitor_never_rewalks_completed_cells(self):
        root=self.root/'budget';root.mkdir();(root/'attempts').mkdir()
        budget=g.OutputWatchdog(root,100000);sealed=[]
        for i in range(100):
            cell=root/'attempts'/str(i);budget.begin(cell);cell.mkdir();(cell/'captured').write_bytes(b'x')
            budget.seal(cell);sealed.append(cell)
        original=Path.rglob
        def guarded(path,*args,**kwargs):
            if path in sealed or path==root/'attempts':raise AssertionError('Quadratic closed-cell walk')
            return original(path,*args,**kwargs)
        with patch.object(Path,'rglob',guarded):self.assertEqual(budget.check(),100)

    def test_atomic_staging_disappearing_during_monitor_sample_is_not_a_directory(self):
        root=self.root/'atomic-budget';root.mkdir();(root/'kept').write_bytes(b'123')
        staging=root/'.publishing-invented';budget=g.OutputWatchdog(root,100)
        original=Path.iterdir
        def raced(path):
            return iter([root/'kept',staging]) if path==root else original(path)
        with patch.object(Path,'iterdir',raced):self.assertEqual(budget.check(),3)

    def test_unknown_resource_peaks_are_null_and_cpu_scopes_distinct(self):
        rows=[dict(worker=None,server=None,host=None),dict(worker=None,server=None,host=None)]
        empty=g.resource_summary(rows)
        self.assertIsNone(empty['sampled_worker_plus_server_peak_bytes']);self.assertIsNone(empty['gpu_peak_bytes'])
        rows[0]['server']=dict(cpu_seconds=2,process_peak_working_set_bytes=100,working_set_bytes=80)
        rows[1]['server']=dict(cpu_seconds=5,process_peak_working_set_bytes=120,working_set_bytes=90)
        result=g.resource_summary(rows)
        self.assertEqual(result['observed_cpu_delta_seconds']['server'],3)
        self.assertEqual(result['server_observed_lifetime_cpu_seconds'],5)


class SourceOriginsTests(unittest.TestCase):
    """Real isolated imports; copies are invented install layouts, never models."""
    def setUp(self):
        directory=(g.ROOT/'data/cache').resolve();directory.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=directory,prefix='alce-generation-origins-')
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.packages=self.root/'installed';self.packages.mkdir()
        for name,relative in g.PACKAGES.items():
            shutil.copytree(g.ROOT/relative,self.packages/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))

    def invoke(self,body):
        code='import sys,json,time\nfrom pathlib import Path\n'
        code+=f'sys.path[:0]=[{str(self.packages)!r},{str(g.ROOT)!r}]\n'
        code+='from experiments.alce import generation as g\n'+body
        return subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,timeout=60)

    def test_noneditable_copies_have_equal_logical_identity_and_retained_distinct_origins(self):
        result=self.invoke("print(json.dumps(g.source_context(time.monotonic()+30)))")
        self.assertEqual(result.returncode,0,result.stderr.decode())
        observed=json.loads(result.stdout);current=g.source_context(time.monotonic()+30)
        self.assertEqual(observed['source_identities'],current['source_identities'])
        for name in g.PACKAGES:
            self.assertEqual(observed['package_origins'][name],proof(self.packages/name/'__init__.py'))
        self.assertIn(proof(self.packages/'tether_engine/agents.py'),observed['code_files'])

    def test_changed_installed_dependency_is_rejected(self):
        path=self.packages/'tether_engine/atomic.py';path.write_bytes(path.read_bytes()+b'\n# invented byte drift\n')
        result=self.invoke('g.source_context(time.monotonic()+30)')
        self.assertNotEqual(result.returncode,0);self.assertIn(b'Loaded dependency bytes differ',result.stderr)

    def test_undeclared_installed_source_member_is_rejected(self):
        (self.packages/'tether_engine/unlisted_invented.py').write_text('VALUE = 1\n')
        result=self.invoke('g.source_context(time.monotonic()+30)')
        self.assertNotEqual(result.returncode,0);self.assertIn(b'Installed package source membership differs',result.stderr)

    def test_same_byte_loaded_module_outside_admitted_package_is_rejected(self):
        result=self.invoke("g.producer.serde.__file__=str(g.ROOT/'src/tether_engine/serde.py')\n"
            "g.producer.serde.__spec__.origin=g.producer.serde.__file__\n"
            'g.source_context(time.monotonic()+30)')
        self.assertNotEqual(result.returncode,0);self.assertIn(b'Loaded module origin differs',result.stderr)


if __name__=='__main__':unittest.main()
