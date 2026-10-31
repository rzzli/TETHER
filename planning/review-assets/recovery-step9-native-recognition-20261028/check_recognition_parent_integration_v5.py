"""Actual-format synthetic files and fake lifecycle; no native SDK/model/child."""
import ast
import copy
import ctypes
from contextlib import ExitStack
import hashlib
from importlib import metadata,util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'run_recognition_observation_v5.py'
REPORT=HERE/'RECOGNITION-PARENT-INTEGRATION-PURE-PROOF-v5.json'
CACHE=ROOT/'data/cache'/('r09-recognition-parent-integration-pure-'+str(time.time_ns()));CACHE.mkdir()
DENIED=[];FIXTURES=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('Fake lifecycle cannot load/connect/dispatch')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.gguf','.dll','.pyd')):
        DENIED.append('payload_open');raise AssertionError('No model/CPU payload')
sys.addaudithook(guard)
def load(name,path):
    spec=util.spec_from_file_location(name,path);module=util.module_from_spec(spec);spec.loader.exec_module(module);return module
h=load('unbound_parent_for_fake_integration',SOURCE)
fixture=load('independent_synthetic_wire_fixture',HERE/'check_recognition_validation_v3.py')
legacy=load('legacy_fake_owner_primitives_only',HERE/'check_detached_abi_negative_integration_v6.py')
RAW=SOURCE.read_bytes();TREE=ast.parse(RAW.decode('utf-8'))
contract=h.source_contract();manifest=h.expected_pack()
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write_child(child,*,malformed=False):
    child.mkdir(parents=True,exist_ok=True)
    (child/'attempt.json').write_text(json.dumps(dict(schema_version=1,mode='--recognize',status='claimed_before_native_load',draft=True)),encoding='utf-8')
    rows=copy.deepcopy(fixture.BASE)
    if malformed:rows[1]['module_policy_phase']='post_cpu'
    (child/'result.jsonl').write_bytes(b''.join(json.dumps(row,separators=(',',':'),allow_nan=False).encode('utf-8')+b'\n' for row in rows))

def harness(name,*,exit_code=2,fault=None):
    clock=legacy.Clock();sdk_ns=dict(__file__=str(legacy.SDK_SOURCE),__name__='recognition_fake_SDK')
    tree=ast.parse(legacy.SDK_RAW.decode('utf-8'));tree.body=[n for n in tree.body if not(isinstance(n,ast.ClassDef) and n.name=='Kernel32')]
    exec(compile(tree,str(legacy.SDK_SOURCE),'exec'),sdk_ns);sdk_ns['time']=clock;sdk=types.SimpleNamespace(**sdk_ns)
    api=legacy.FakeAPI(clock,exit_code=exit_code,fault=fault);api.role_hash_records=[];api.role_lease_attempts=[]
    def resume(thread):
        api.events.append('resume')
        if exit_code==0:write_child(api.child,malformed=fault=='malformed')
        else:(api.child/'failure.json').write_text('{"status":"synthetic_failed"}',encoding='utf-8')
        api.dead=fault!='deadline';return 1
    api.resume=resume
    if fault=='deadline':
        def wait(handle,milliseconds):
            if not api.expiry_injected:
                api.expiry_injected=True;clock.value+=118.01;raise TimeoutError('Synthetic recognition work deadline')
            return api.dead
        api.wait=wait
    component={};exec(compile(legacy.COMPONENT_RAW,str(legacy.COMPONENT),'exec'),component)
    def terminal():return lambda *a,**kw:component['observe_terminal'](*a,**kw,now=clock.monotonic,sleep=clock.sleep)
    output=CACHE/name;protocol=CACHE/(name+'-protocol.json');real_write=sdk.write_new
    def write(path,value):
        if fault=='publication' and Path(path).name=='parent-report.json':raise OSError('Synthetic publication failure')
        result=real_write(path,value)
        if fault=='after_seal' and Path(path).name=='terminal-seal.json':clock.value=401.0
        return result
    if fault=='after_seal':sdk_ns['write_new']=write
    sealer_ns={};exec(compile((HERE/'recognition_status_seal_v1.py').read_bytes(),str(HERE/'recognition_status_seal_v1.py'),'exec'),sealer_ns)
    sealer_ns['time']=clock
    # The sealer captures fake SDK writer at construction, never mutates SDK code.
    fake_sealer_sdk=types.SimpleNamespace(**{**sdk_ns,'write_new':write})
    seal=sealer_ns['make_sealer'](fake_sealer_sdk)
    ns=dict(__file__=str(SOURCE),Path=Path,ExitStack=ExitStack,os=os,sys=sys,time=clock,metadata=metadata,json=json,math=math,
        sdk=sdk,q=types.SimpleNamespace(DEFAULT=Path(sys.executable)),require=legacy.require,pin=pin,sha=lambda path:pin(path)['sha256'],
        PROTOCOL=protocol,LIMITS=h.LIMITS,PERIODIC_JOB_SECONDS=3.5,TERMINAL_POLICY=h.TERMINAL_POLICY,terminal_observer=terminal,
        validate_role=lambda config:sdk.safe(config['output'],output=True),api_class=lambda:lambda *_:api,write_new=write,
        _OWNER_STARTED=None,_OWNER_DEADLINE=None,SEAL_POST_LEASE_CLEANUP=seal)
    nodes=[copy.deepcopy(n) for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in ('execute','parent_payload_observations')]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE)+'::<fake AST only>','exec'),ns)
    if fault in ('metadata_runtime','metadata_KI'):
        def metadata_fault(*args):
            raise (KeyboardInterrupt if fault=='metadata_KI' else RuntimeError)('Synthetic report derivation fault')
        ns['parent_payload_observations']=metadata_fault
    def validate(child,config):
        with patch.object(h,'EXE',Path(fixture.CONTEXT['expected_self'])),patch.object(h,'RUNTIME',Path(fixture.CONTEXT['expected_runtime'])),patch.object(h,'authority',return_value={}):
            return h.validate_child_artifacts(child,config)
    ns['validate_child_artifacts']=validate
    argv=[fixture.CONTEXT['expected_self'],'--recognize',fixture.CONTEXT['expected_runtime'],str(output/'execution/child'),manifest['pack']['path'],
          'ggml-cpu-x64.dll',*[r['path'] for r in contract['ordered_shard_descriptors']]]
    config=dict(output=str(output),argv=argv,command_line=subprocess.list2cmdline(argv),environment=sdk.effective_environment(output),
        inputs=[pin(SOURCE)],payload_inputs=h.payload_records())
    protocol.write_bytes(sdk.canonical(config)+b'\n');result=ns['execute'](config,pin(protocol)['sha256'],owner_started=clock.monotonic())
    FIXTURES.append(dict(case=name,status=result['status'],output=str(output),files=[pin(p) for p in sorted(output.rglob('*')) if p.is_file()]))
    return api,result,output,clock

class Checks(unittest.TestCase):
    def test_report_derivation_error_or_interrupt_cannot_skip_original_lease_cleanup_or_seal(self):
        for fault in ('metadata_runtime','metadata_KI'):
            for code in (0,2):
                with self.subTest(fault=fault,code=code):
                    api,result,out,_=harness('report-'+fault+'-'+str(code),exit_code=code,fault=fault)
                    self.assertEqual(result['status'],'failed');self.assertGreaterEqual(api.counts.get(100,0),1)
                    seal=json.loads((out/'terminal-seal.json').read_text(encoding='utf-8'));self.assertEqual(seal['status'],'failed')
                    cleanup=json.loads((out/'post-lease-cleanup.json').read_text(encoding='utf-8'))
                    self.assertTrue(all(row['closed_after'] for row in cleanup['outcomes']))
                    self.assertTrue((out/'terminal-publication-error.json').is_file())
                    if code==2:self.assertEqual(result['failure']['error'],'Recognition child failed')
                    else:self.assertEqual(result['failure']['error'],'Synthetic report derivation fault')
                    if fault=='metadata_KI':self.assertTrue(any(row['error_class']=='KeyboardInterrupt' for row in result['interruptions']))
    def test_full_actual_format_parser_binding_and_nonreparse_entry_checks(self):
        child=CACHE/'actual-format/child';write_child(child)
        with patch.object(h,'EXE',Path(fixture.CONTEXT['expected_self'])),patch.object(h,'RUNTIME',Path(fixture.CONTEXT['expected_runtime'])),patch.object(h,'authority',return_value={}):
            value=h.validate_child_artifacts(child);self.assertEqual(value['case_results'],189)
            original=h.safe
            def safe(path,**kwargs):
                if Path(path)==child/'attempt.json':raise RuntimeError('Synthetic reparse artifact entry rejected')
                return original(path,**kwargs)
            with patch.object(h,'safe',side_effect=safe),self.assertRaisesRegex(RuntimeError,'reparse'):h.validate_child_artifacts(child)
        FIXTURES.append(dict(case='actual-format-parser',files=[pin(p) for p in child.iterdir()]))
    def test_child_failure_primary_retains_terminal_raw_EOF_memory_and_unknown_coverage(self):
        api,result,out,_=harness('negative')
        self.assertEqual(result['status'],'failed');self.assertEqual(result['failure']['error'],'Recognition child failed')
        self.assertTrue(result['terminal_observation']['complete']);self.assertTrue(result['reaped'])
        self.assertTrue(all(row['eof'] for row in result['captures'].values()))
        self.assertEqual(result['partial_coverage']['status'],'not_inspected_unknown')
        self.assertFalse(result['parent_payload_observations']['zero_weight_IO_claim'])
        self.assertEqual(api.events.count('create'),1)
    def test_interruptions_and_unknown_creation_do_not_fabricate_model_path_delivery(self):
        for fault in ('KeyboardInterrupt','SystemExit','unknown_creation'):
            api,result,out,_=harness('unknown-'+fault,fault=fault)
            self.assertEqual(result['status'],'failed');delivery=result['parent_payload_observations']['model_path_delivery']
            self.assertTrue(delivery['creation_attempt_reserved']);self.assertFalse(delivery['creation_return_observed'])
            self.assertIsNone(delivery['creation_success_if_observed']);self.assertIsNone(delivery['successful_CreateProcess_call_included_declared_paths'])
            if fault!='unknown_creation':self.assertEqual(result['final_input_recheck']['status'],'skipped_due_to_interruption')
    def test_work_timeout_cleanup_stays_within120_and_no_new_bulk_hash(self):
        api,result,out,_=harness('deadline',fault='deadline')
        self.assertEqual(result['status'],'failed');self.assertGreaterEqual(result['child_full_process_elapsed_seconds'],118)
        self.assertLessEqual(result['child_full_process_elapsed_seconds'],120);self.assertTrue(result['reaped'])
        self.assertFalse(result['terminal_observation']['complete'])
    def test_success_actual_format_and_malformed_phase_are_distinct(self):
        api,result,out,_=harness('positive',exit_code=0)
        self.assertEqual(result['status'],'recognition_observations_retained_independent_qualification_pending')
        self.assertEqual(result['observations']['case_results'],189)
        self.assertEqual(result['counter_scope']['child_snapshots'],'complete_source_bound_snapshots_validated')
        api,result,out,_=harness('malformed',exit_code=0,fault='malformed')
        self.assertEqual(result['status'],'failed');self.assertFalse(result['partial_coverage']['complete'])
    def test_late_close_publication_and_post_seal_errors_keep_failure_veto(self):
        for fault in ('late_close','publication','after_seal'):
            api,result,out,_=harness('late-'+fault,exit_code=0,fault=fault)
            self.assertEqual(result['status'],'failed')
            self.assertTrue(any((out/name).exists() for name in ('late-failure.json','terminal-publication-error.json','after-seal-failure.json')))

if __name__=='__main__':
    assert not REPORT.exists();original=pin(SOURCE);started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));assert pin(SOURCE)==original
    value=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],helper=original,checker=pin(Path(__file__)),
        validator=pin(HERE/'recognition_validation_v3.py'),wire=pin(HERE/'RECOGNITION-CHILD-WIRE-v2.json'),
        contract=pin(HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'),manifest=pin(HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'),
        role_helper=pin(HERE/'recognition_runtime_roles_v2.py'),legacy_fake_primitives=pin(HERE/'check_detached_abi_negative_integration_v6.py'),
        terminal_component=pin(legacy.COMPONENT),status_sealer=pin(HERE/'recognition_status_seal_v1.py'),
        SDK=pin(legacy.SDK_SOURCE),report_boundary_before=pin(HERE/'RECOGNITION-REPORT-SEAL-REGRESSION-BEFORE-v5b.json'),
        elapsed_seconds=time.monotonic()-started,fixtures=FIXTURES,
        actual_children=0,real_SDK_constructions=0,CPU_binary_reads=0,GGUF_reads=0,compiler_calls=0,
        denied_real_operations=DENIED,scope='Synthetic401-row byte-token files plus fake owned lifecycle only; fake clocks and fake source leases establish no native conformance/resource fit or asset qualification.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT),fixtures=len(FIXTURES))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
