"""Pure nine-argument/owner-clock/lease-failure integration checks; no real SDK."""
import ast
import copy
import ctypes
import hashlib
from importlib import util
import json
import math
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'run_recognition_observation_v4.py'
REPORT=HERE/'RECOGNITION-PARENT-ROLE-PURE-PROOF-v4.json'
CACHE=ROOT/'data/cache'/('r09-recognition-parent-role-pure-'+str(time.time_ns()));CACHE.mkdir()
DENIED=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No real constructor/child/network')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.gguf','.dll','.pyd')):
        DENIED.append('payload_open');raise AssertionError('No payload open')
sys.addaudithook(guard)
spec=util.spec_from_file_location('unbound_recognition_parent_role_pure',SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)
contract=h.source_contract();manifest=h.expected_pack();roles=h.roles()
RAW=SOURCE.read_bytes();TREE=ast.parse(RAW.decode('utf-8'))
NODES={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
def require(value,message):
    if not value:raise RuntimeError(message)
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

class Checks(unittest.TestCase):
    def test_observed_payload_IO_and_unknown_path_delivery_are_derived(self):
        models=contract['ordered_shard_descriptors'];path=models[0]['path']
        stages=[dict(path=path,status='failed',known_returned_bytes=65536,read_attempts=2,read_returns=1,hash_complete=False)]
        opens=[dict(path=path,attempt_reserved=True,return_observed=False,returned_success=None)]
        creation=dict(api_attempt_reserved=True,return_observed=False,returned_success=None)
        value=h.parent_payload_observations(stages,opens,models,creation,dict(state='unknown_may_have_run'))
        self.assertEqual(value['known_parent_model_hash_read_bytes'],65536)
        self.assertEqual(value['parent_model_hash_read_attempts'],2);self.assertEqual(value['parent_model_hash_read_returns'],1)
        self.assertEqual(value['unknown_or_incomplete_hash_stages'],1);self.assertEqual(value['reserved_model_open_outcomes_unobserved'],1)
        self.assertIsNone(value['model_path_delivery']['creation_success_if_observed'])
        self.assertIsNone(value['model_path_delivery']['successful_CreateProcess_call_included_declared_paths'])
        self.assertFalse(value['zero_weight_IO_claim'])
        value=h.parent_payload_observations([],[],models,dict(api_attempt_reserved=True,return_observed=True,returned_success=True),dict(state='observed_resumed'))
        self.assertTrue(value['model_path_delivery']['successful_CreateProcess_call_included_declared_paths'])
        self.assertEqual(value['model_path_delivery']['actual_child_model_file_use'],'not_inferred_from_declared_paths_or_creation')
        source=ast.get_source_segment(RAW.decode('utf-8'),NODES['execute'])
        self.assertNotIn('parent_GGUF_reads=0',source);self.assertNotIn('model_paths_supplied_to_child=False',source)
        self.assertNotIn('counters_instrumented=False',source)
    def test_owned_protocol_records_remain_exact_and_not_static_role_expansion(self):
        protocol=CACHE/'candidate-protocol.json';output=CACHE/'candidate-run'
        record=dict(path=str(protocol),bytes=12,sha256='a'*64)
        with patch.object(h,'PROTOCOL',protocol):
            role=h.role_of(record,dict(output=str(output),software_inputs=[]),'a'*64)
            self.assertEqual(role['role'],'software')
            with self.assertRaisesRegex(RuntimeError,'driver-bound'):h.role_of(dict(record,sha256='b'*64),dict(output=str(output),software_inputs=[]),'a'*64)
            with self.assertRaises(RuntimeError):h.role_of(dict(record,path=str(CACHE/'unlisted.json')),dict(output=str(output),software_inputs=[]),'a'*64)
    def test_unbound_operational_routes_fail_before_constructor_or_payload(self):
        for name,args in [('authority',()),('configuration',(CACHE/'future',[])),('validate_role',({},)),('collect_inputs',()),('prepare',())]:
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'Unbound recognition source'):getattr(h,name)(*args)
        with self.assertRaisesRegex(RuntimeError,'Unbound recognition source'):h.api_class()({},'0'*64)
        self.assertIsNone(h.EXE);self.assertEqual(h.VALIDATOR_SHA,'9a2086ab226a5a7ae70a35b5eec1bf4d4e6f6d2fe9dedfc96092241186380c09');self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED)
    def test_source_preparation_model_CPU_records_are_metadata_only(self):
        software=[dict(path=str(CACHE/'software.txt'),bytes=1,sha256='0'*64)]
        inputs=software+h.payload_records()
        with patch.object(h,'source_contract',return_value=contract),patch.object(h,'expected_pack',return_value=manifest),patch.object(h,'roles',return_value=roles), \
             patch('builtins.open',side_effect=AssertionError('No descriptor opens')),patch.object(Path,'stat',side_effect=AssertionError('No descriptor stats')):
            self.assertEqual(h.validate_role_inputs(inputs,software),inputs)
            for field,value in [('bytes',contract['ordered_shard_descriptors'][0]['bytes']+1),('path',r'D:\unlisted.gguf'),('sha256','0'*64)]:
                bad=copy.deepcopy(inputs);bad[2][field]=value
                with self.assertRaises(RuntimeError):h.validate_role_inputs(bad,software)
    def test_exact_nine_arguments_reject_alternate_paths_mode_and_shard_order(self):
        exe=CACHE/'fixture_not_executed.exe';exe.write_bytes(b'own synthetic text, never executed')
        args=[exe,h.RUNTIME,CACHE/'future/execution/child',manifest['pack']['path'],'ggml-cpu-x64.dll',
            [r['path'] for r in contract['ordered_shard_descriptors']]]
        with patch.object(h,'EXE',exe):
            argv,command=h.recognition_argv(*args)
            self.assertEqual(len(argv),9);self.assertEqual(argv[1],'--recognize');self.assertEqual(argv[-3:],args[-1])
            for index,value in [(0,CACHE/'wrong.exe'),(1,CACHE/'wrong-runtime'),(3,str(CACHE/'wrong.pack')),(4,'ggml-vulkan.dll'),(5,list(reversed(args[5])))]:
                bad=copy.deepcopy(args);bad[index]=value
                with self.assertRaises(RuntimeError):h.recognition_argv(*bad)
    def test_exact_role_configuration_rejects_new_authority_or_scope(self):
        exe=CACHE/'role_not_executed.exe';exe.write_bytes(b'own synthetic role fixture')
        software=[pin(exe)];binding=dict(executable=pin(exe),software_inputs=software)
        with patch.object(h,'EXE',exe),patch.object(h,'authority',return_value=binding):
            inputs=software+h.payload_records();value=h.configuration(CACHE/'future-role',inputs)
            self.assertEqual(h.validate_role(value),CACHE/'future-role')
            for key,replacement in [('mode','--abi'),('mode','--module-census'),('maximum_attempts',2),('automatic_retry',True),
                ('full_vocabulary_mask',True),('inference',True),('cooperative_work_ms',120000),('parent_seconds',301),
                ('module_policy_sha256','0'*64),('execution_authorized_by_preparation',True)]:
                bad=copy.deepcopy(value);bad[key]=replacement
                with self.assertRaises(RuntimeError):h.validate_role(bad)
    def test_owner_start_and_deadline_precede_all_role_validation(self):
        events=[]
        def validate(_):events.append('validate');raise ValueError('synthetic stop before reservation')
        def deadline(value):events.append(('deadline',value))
        ns=dict(require=require,math=math,time=types.SimpleNamespace(monotonic=lambda:105.0),
            sdk=types.SimpleNamespace(finite_deadline=deadline),validate_role=validate,
            _OWNER_STARTED=None,_OWNER_DEADLINE=None)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(NODES['execute'])],type_ignores=[])),str(SOURCE)+'::<pure execute>','exec'),ns)
        with self.assertRaisesRegex(ValueError,'synthetic stop'):ns['execute']({},'0'*64,owner_started=100.0)
        self.assertEqual(events,[('deadline',395.0),'validate']);self.assertEqual(ns['_OWNER_STARTED'],100.0)
        self.assertEqual(ns['_OWNER_DEADLINE'],395.0)
        with self.assertRaisesRegex(RuntimeError,'already consumed'):ns['execute']({},'0'*64,owner_started=100.0)
    def test_expired_or_invalid_owner_clock_cannot_start_validation(self):
        for start in (None,True,float('nan'),float('inf'),106.0,100.0):
            events=[]
            def expired(_):events.append('deadline');raise TimeoutError('expired')
            ns=dict(require=require,math=math,time=types.SimpleNamespace(monotonic=lambda:105.0),
                sdk=types.SimpleNamespace(finite_deadline=expired),validate_role=lambda _:events.append('validate'),
                _OWNER_STARTED=None,_OWNER_DEADLINE=None)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(NODES['execute'])],type_ignores=[])),str(SOURCE)+'::<clock-only>','exec'),ns)
            with self.assertRaises((RuntimeError,TimeoutError)):ns['execute']({},'0'*64,owner_started=start)
            self.assertNotIn('validate',events)
    def test_lease_ownership_and_both_validation_close_failures_are_preserved(self):
        api=h.api_class().__new__(h.api_class());api.config={};api.expected='0'*64
        api.record_event=lambda *a,**k:None;api.role_hash_records=[];api.role_lease_attempts=[]
        api.k=types.SimpleNamespace(CreateFileW=lambda *a:42)
        api.win=lambda ok,message:require(ok,message)
        def bad_validation(*args):raise ValueError('primary exact input failure')
        def bad_close(*args):raise OSError('secondary close failure')
        api.validate_lease=bad_validation;api.close=bad_close
        fake_roles=types.SimpleNamespace(runtime_path=lambda *a,**k:Path(r'D:\qualified\fixed.gguf'))
        owners=[]
        with patch.object(h,'role_of',return_value=dict(role='model',cap=4000000000)),patch.object(h,'roles',return_value=fake_roles):
            with self.assertRaisesRegex(ValueError,'primary exact'):api.read_lease(dict(path=r'D:\qualified\fixed.gguf'),10.0,owners)
        self.assertEqual(len(owners),1);self.assertEqual(owners[0]['handle'],42)
        self.assertEqual(owners[0]['primary_error']['error_class'],'ValueError')
        self.assertEqual(owners[0]['cleanup_errors'][0]['error_class'],'OSError');self.assertFalse(owners[0]['closed'])
    def test_final_bulk_recheck_deadline_and_publication_reserve_are_explicit(self):
        source=ast.get_source_segment(RAW.decode('utf-8'),NODES['execute'])
        self.assertIn('record=api.read_lease(item,parent_end-5,leases)',source)
        self.assertNotIn('read_lease(item,parent_end,leases)',source)
        self.assertIn('_OWNER_DEADLINE=parent_end',source)
        self.assertLess(source.index('record=api.read_lease(item,parent_end-5,leases)'),source.index('_OWNER_DEADLINE=parent_end'))
        self.assertEqual(h.LIMITS['parent_seconds'],300);self.assertEqual(h.LIMITS['child_seconds'],120)
        self.assertEqual(h.PERIODIC_JOB_SECONDS,3.5)

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve prior proof';started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert SOURCE.read_bytes()==RAW
    value=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        helper=pin(SOURCE),checker=pin(Path(__file__)),elapsed_seconds=time.monotonic()-started,
        actual_children=0,real_SDK_constructions=0,CPU_binary_reads=0,GGUF_reads=0,compiler_calls=0,
        denied_real_operations=DENIED,scope='Unbound parent role/clock source and fake typed lease failures only; not full lifecycle, final wire parser, OS/API or payload qualification')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
