"""Focused synthetic checks. Reads only the new component/frozen test assets."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from types import MappingProxyType
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'captured_journal_v1.py'
FIXTURES=HERE/'CAPTURED-JOURNAL-FIXTURES-v1.json'
CONTRACT=HERE/'CAPTURED-JOURNAL-CONTRACT-v1.json'
FREEZE=HERE/'CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json'
PROOF=HERE/'CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v1.json'
FROZEN_FIXTURES='1448873002dc5350be8ca835254ff283b734d04bda88382273b1c4b4319fe28c'
FROZEN_CONTRACT='2993cf83b8768f2324feb495bae65217d627135f0ce4d20fb341d537893d71ff'
FROZEN_RECORD='cd4f6b3f381a837d790dfcad84e92231111456e3eb6648a0ebd7617c84980140'
VECTORS=[];OBSERVATIONS=[];M=None

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def raw(case):
    if case['kind']=='literal':return bytes.fromhex(case['raw_hex'])
    return bytes.fromhex(case['recipe']['byte_hex'])*case['recipe']['repeat']
def base():return raw(VECTORS[0]),copy.deepcopy(VECTORS[0]['bindings'])
def events(data):return [(r['event'],r['details']) for r in (json.loads(line) for line in data.split(b'\n') if line)]
def chain(items):
    previous=None;out=[]
    for index,(event,details) in enumerate(items):
        record=dict(sequence=index,event=event,details=details,previous_sha256=previous)
        record['sha256']=sha(canonical(record));previous=record['sha256'];out.append(canonical(record)+b'\n')
    return b''.join(out)
def rebound(items,b):
    data=chain(items);b['journal_sha256']=sha(data);return data,b
def pin(path):
    data=path.read_bytes();return dict(path=str(path),bytes=len(data),sha256=sha(data))

class Tests(unittest.TestCase):
    def reject(self,data,b=None,family=None):
        with self.assertRaises(M.CapturedJournalError) as caught:
            if b is None:M.check_chain(data,check=lambda:None)
            else:M.check_native_v7(data,b,check=lambda:None)
        self.assertLessEqual(len(str(caught.exception)),512)
        if family:self.assertEqual(caught.exception.family,family)
        return caught.exception

    def test_01_all_frozen_literals_and_recipe(self):
        self.assertEqual(len(VECTORS),30)
        for case in VECTORS:
            with self.subTest(case=case['id']):
                data=raw(case);self.assertEqual(len(data),case['bytes']);self.assertEqual(sha(data),case['sha256'])
                observed=dict(id=case['id'])
                try:result=M.check_chain(data,check=lambda:None);observed['chain_valid']=True
                except M.CapturedJournalError as error:observed.update(chain_valid=False,chain_error_family=error.family)
                self.assertEqual(observed['chain_valid'],case['expected_chain_valid'])
                try:
                    result=M.check_native_v7(data,case['bindings'],check=lambda:None)
                    observed['native_complete']=True;self.assertIs(result['profile_qualified'],False)
                except M.CapturedJournalError as error:observed.update(native_complete=False,native_error_family=error.family)
                OBSERVATIONS.append(observed)
                self.assertEqual(observed['native_complete'],case['expected_native_complete'])
                if case['error_family']:
                    self.assertEqual(observed.get('native_error_family'),case['error_family'])

    def test_02_generic_negative_and_resource_scopes(self):
        data,b=base();generic=M.check_chain(data,check=lambda:None)
        self.assertIs(generic['source_order_validated'],False);self.assertIs(generic['profile_qualified'],False)
        negative=VECTORS[1];data=raw(negative)
        self.assertIn('\u2028'.encode(),data);self.assertIn('\u2029'.encode(),data);self.assertIn('\u0085'.encode(),data)
        result=M.check_native_v7(data,negative['bindings'],check=lambda:None)
        self.assertEqual(result['events'],64);self.assertEqual(result['source_terminal_status'],'failed')
        for key in ('profile_qualified','resource_semantics_validated','owner_context_provenance_established_by_this_function'):
            self.assertIs(result[key],False)
        # The raw-resource predicate is deliberately a separate gate.
        data,b=base();items=events(data);final=next(d for n,d in items if n=='abi_job_snapshot_observed' and d['stage']=='after_wait')['snapshot']
        final['accounting']['decoded']['ActiveProcesses']=99
        b['parent_report']['final_job_snapshot']=copy.deepcopy(final)
        job=b['parent_report']['terminal_observation']['observations']['job_snapshot'];job['raw']=copy.deepcopy(final);job['value']=copy.deepcopy(final)
        data,b=rebound(items,b);result=M.check_native_v7(data,b,check=lambda:None)
        self.assertIs(result['resource_semantics_validated'],False)

    def test_03_deep_immutability_and_input_detachment(self):
        data,b=base();a=M.check_chain(data,check=lambda:None);z=M.check_native_v7(data,b,check=lambda:None)
        with self.assertRaises(TypeError):a['records'][0]['details']['owner_pid']=2
        with self.assertRaises(TypeError):z['record_references'][0]['kind']='forged'
        with self.assertRaises(AttributeError):a['records'].append({})
        b['parent_report']['status']='modified';self.assertNotEqual(z['source_terminal_status'],'modified')
        self.assertIs(type(a),MappingProxyType)

    def test_04_deadline_exception_identity_and_final_copy(self):
        data,b=base()
        for native in (False,True):
            count=[0]
            def count_check():count[0]+=1
            fn=(lambda check:M.check_native_v7(data,b,check=check)) if native else (lambda check:M.check_chain(data,check=check))
            fn(count_check);self.assertGreater(count[0],100)
            for threshold in (1,8,60,count[0]-1,count[0]):
                marker=KeyboardInterrupt('synthetic owner cutoff');seen=[0]
                def stop():
                    seen[0]+=1
                    if seen[0]==threshold:raise marker
                try:fn(stop)
                except BaseException as error:self.assertIs(error,marker)
                else:self.fail('Deadline was hidden')

    def test_05_argument_and_binding_graph_bounds(self):
        data,b=base()
        for bad in (bytearray(data),memoryview(data),'a journal',None):self.reject(bad,family='argument')
        with self.assertRaises(M.CapturedJournalError):M.check_chain(data,check=None)
        cases=[]
        for key,value in [('unknown',True),('already_verified',True),('ready',True)]:
            x=copy.deepcopy(b);x[key]=value;cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['captures']['stdout']['ready']=True;cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'loop':x};cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'huge':'x'*(M.MAX_BINDING_BYTES+1)};cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'surrogate':'\ud800'};cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'nonfinite':float('inf')};cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'foreign':object()};cases.append(x)
        x=copy.deepcopy(b);nested=0
        for _ in range(65):nested=[nested]
        x['parent_report']['failure']={'nested':nested};cases.append(x)
        x=copy.deepcopy(b);x['parent_report']['failure']={'nodes':[None]*65536};cases.append(x)
        for bad in cases:self.reject(data,bad,'binding_schema')

    def test_06_strict_counters_and_source_bindings(self):
        data,b=base()
        mutations=[lambda x:x['parent_reservation'].update(owner_pid=True),lambda x:x['parent_limits'].update(active_processes=True),
            lambda x:x['ordered_files'][0].update(bytes=True),lambda x:x['parent_report'].update(returncode=False),
            lambda x:x['parent_report']['resumption'].update(previous_suspend_count=True),
            lambda x:x['parent_report']['final_input_recheck'].update(new_read_leases=True),
            lambda x:x['parent_report']['captures']['stdout'].update(retained_bytes=False),
            lambda x:x['parent_report']['terminal_observation'].update(complete=False),
            lambda x:x['parent_report']['role_hash_records'][0].update(expected_bytes=True),
            lambda x:x['ordered_files'][1].update(path=x['ordered_files'][0]['path'].swapcase()),
            lambda x:x.update(policy_id='future-unicode-policy'),lambda x:x.update(journal_sha256='0'*64)]
        for mutate in mutations:
            x=copy.deepcopy(b);mutate(x);self.reject(data,x)
        items=events(data)
        for event,key in [('abi_CreateProcessW_reserved','attribute_count'),('abi_created_suspended','thread_id'),('abi_resume_returned','previous_suspend_count')]:
            altered=copy.deepcopy(items);next(d for n,d in altered if n==event)[key]=True;d,x=rebound(altered,copy.deepcopy(b));self.reject(d,x)

    def test_07_terminal_capture_and_periodic_reference_order(self):
        data,b=base();items=events(data);report=b['parent_report'];obs=report['terminal_observation']['observations']
        def call(poll,value):return dict(poll=poll,attempt_reserved=True,call_attempted=True,return_observed=True,value=value)
        first=call(1,3);first['read']=dict(attempt_reserved=True,call_attempted=True,return_observed=True,value={'bytes':3})
        obs['capture_drain']['stdout'].update(calls=[first,call(3,None)],polls_reserved=2,status='observed_EOF')
        obs['capture_drain']['stderr'].update(calls=[call(2,None)],polls_reserved=1,status='observed_EOF')
        report['captures']['stdout'].update(retained_bytes=3,observed_bytes_at_least=3)
        at=next(i for i,(n,d) in enumerate(items) if n=='detached_ABI_terminal_call_reserved')
        labels=['capture_available_stdout','capture_read_stdout','capture_available_stderr','capture_available_stdout']
        periodic=copy.deepcopy(next(d for n,d in items if n=='abi_job_snapshot_observed' and d['stage']=='running_first'));periodic.update(stage='running_periodic',ordinal=4)
        items[at:at]=[('abi_job_snapshot_observed',periodic)]+[('detached_ABI_terminal_call_reserved',{'observation':s}) for s in labels]
        next(d for n,d in items if n=='abi_job_snapshot_observed' and d['stage']=='after_wait')['ordinal']=5
        obs['job_snapshot']['ordinal']=5;data,b=rebound(items,b)
        result=M.check_native_v7(data,b,check=lambda:None);self.assertEqual(result['snapshot_records'],5);self.assertEqual(result['terminal_capture_reservations'],4)
        for fault in ('missing_read','duplicate_poll','late_return','wrong_event','limit_read'):
            x=copy.deepcopy(b);e=copy.deepcopy(items)
            if fault=='missing_read':del x['parent_report']['terminal_observation']['observations']['capture_drain']['stdout']['calls'][0]['read']
            elif fault=='duplicate_poll':x['parent_report']['terminal_observation']['observations']['capture_drain']['stderr']['calls'][0]['poll']=1
            elif fault=='late_return':x['parent_report']['terminal_observation']['observations']['capture_drain']['stdout']['calls'][0]['return_observed']=False
            elif fault=='limit_read':x['parent_report']['terminal_observation']['observations']['capture_drain']['stdout']['calls'][0]['read']['value']['bytes']=4097
            else:next(d for n,d in e if n=='detached_ABI_terminal_call_reserved')['observation']='capture_read_stderr'
            d,x=rebound(e,x);self.reject(d,x)

    def test_08_unpaired_scalar_and_exact_row_boundary(self):
        data,b=base();items=events(data)
        # Literal escape is valid JSON syntax but not a Unicode scalar string.
        bad=b'{"details":{"s":"\\ud800"},"event":"synthetic","previous_sha256":null,"sequence":0,"sha256":"'+b'0'*64+b'"}\n'
        self.reject(bad,family='JSON')
        item=[('synthetic',{'pad':''})];overhead=len(chain(item))-1
        item[0][1]['pad']='a'*(65536-overhead);at_limit=chain(item)
        self.assertEqual(len(at_limit)-1,65536);self.assertEqual(M.check_chain(at_limit,check=lambda:None)['events'],1)
        item[0][1]['pad']+='a';self.reject(chain(item),family='row_cap')
        self.assertEqual(M.check_chain(chain([('synthetic',{})]*2048),check=lambda:None)['events'],2048)

    def test_09_no_path_or_loader_operations(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8'));imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(set(imports),{'datetime','hashlib','json','math','re','types'})
        data,b=base()
        with mock.patch('builtins.open',side_effect=AssertionError('No file open allowed')),mock.patch.object(Path,'open',side_effect=AssertionError('No Path I/O allowed')):
            self.assertTrue(M.check_native_v7(data,b,check=lambda:None)['source_order_validated'])

def main():
    global M,VECTORS
    started=time.monotonic()
    assert not PROOF.exists(),'Preserve first pure result'
    for path,expected in ((FIXTURES,FROZEN_FIXTURES),(CONTRACT,FROZEN_CONTRACT),(FREEZE,FROZEN_RECORD)):
        assert sha(path.read_bytes())==expected,'Frozen test asset differs'
    values=json.loads(FIXTURES.read_text(encoding='utf-8'));VECTORS=values['cases']
    spec=importlib.util.spec_from_file_location('captured_journal_under_test',SOURCE);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=2).run(suite)
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    components={node.name:sha(ast.dump(node,include_attributes=False).encode()) for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        source=pin(SOURCE),checker=pin(Path(__file__)),contract=pin(CONTRACT),fixture_freeze=pin(FREEZE),fixtures=pin(FIXTURES),
        methods=result.testsRun,failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],
        frozen_case_observations=OBSERVATIONS,component_AST_sha256=components,elapsed_seconds=time.monotonic()-started,
        profile_qualified=False,resource_semantics_validated=False,actual_old_run_replay=False,actual_original_file_rehashes=0,
        actual_children=0,real_SDK_constructions=0,CPU_GGUF_pack_reads=0,native_compiler_model_tokenizer_calls=0,
        scope='Synthetic captured bytes and metadata only; no actual archive/resource/profile qualification. Test harness reads only new source/contract/fixtures and writes this result.')
    with PROOF.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,ensure_ascii=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=proof['status'],methods=proof['methods'],elapsed_seconds=proof['elapsed_seconds'])))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
