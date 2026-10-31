"""Shared phase-policy vectors and pure regression proof; no CPU/image/SDK access."""
import ast
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'recognition_module_policy_v1.py'
ABI=HERE/'trusted_system32_module_policy_v1.py'
CONTRACT=HERE/'RECOGNITION-MODULE-POLICY-v1.json'
VECTORS=HERE/'RECOGNITION-MODULE-VECTORS-v1.json'
REPORT=HERE/'RECOGNITION-MODULE-POLICY-PURE-PROOF-v1.json'
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(name,path):
    spec=util.spec_from_file_location(name,path);module=util.module_from_spec(spec);spec.loader.exec_module(module);return module
DENIED=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('Pure phase policy only')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.gguf','.dll','.pyd')):
        DENIED.append('binary_open');raise AssertionError('No binary/model payload opens')
sys.addaudithook(guard)
m=load('pure_recognition_phase_policy',SOURCE);old=load('preserved_ABI_phase_policy',ABI)
contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
base=json.loads((HERE/'TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json').read_text(encoding='utf-8'))
CASES=[]
for row in base['cases']:
    item=copy.deepcopy(row);item['id']='pre_cpu/'+row['id'];item['phase']='pre_cpu';CASES.append(item)
CONTEXT=dict(expected_self=r'D:\qualified\recognition\bridge.exe',expected_runtime=r'D:\qualified\recognition\runtime')
NATIVE=[dict(name='bridge.exe',path=CONTEXT['expected_self']),
    *[dict(name=n,path=CONTEXT['expected_runtime']+'\\'+n) for n in contract['semantic_policy']['core_names']]]
CPU=dict(name='ggml-cpu-x64.dll',path=CONTEXT['expected_runtime']+'\\ggml-cpu-x64.dll')
PLATFORM=dict(name='apphelp.dll',path=r'C:\Windows\System32\apphelp.dll')
def add(name,rows,accepted,*,phase='post_cpu',reason=None,context=CONTEXT):
    case=dict(id=name,context=copy.deepcopy(context),phase=phase,modules=copy.deepcopy(rows),accepted=accepted)
    if accepted:
        case['expected_classes']=['self_executable' if r['name']=='bridge.exe' else
            'pinned_runtime' if r['name'] in m.SEMANTICS['declared_runtime_names'] else 'trusted_platform_context' for r in rows]
    if reason:case['reason_if_isolated']=reason
    CASES.append(case)
add('post_cpu/exact-native-and-platform',NATIVE+[CPU,PLATFORM],True)
add('post_cpu/missing-CPU',NATIVE+[PLATFORM],False,reason='missing_required_reports')
add('post_cpu/duplicate-CPU',NATIVE+[CPU,CPU],False,reason='duplicate_report')
add('pre_cpu/CPU-exact-still-forbidden',NATIVE+[CPU],False,phase='pre_cpu',reason='protected_native_not_eligible')
for name,path in [('CPU-under-System32',r'C:\Windows\System32\ggml-cpu-x64.dll'),('CPU-wrong-native-dir',r'D:\wrong\ggml-cpu-x64.dll')]:
    add('post_cpu/'+name,NATIVE+[dict(name=CPU['name'],path=path)],False,reason='protected_native_not_eligible')
for name in ('ggml-cpu-sapphirerapids.dll','ggml-vulkan.dll','ggml-rpc.dll','llama-backdoor.dll','libomp-alternate.dll'):
    add('post_cpu/extra-provider-'+name,NATIVE+[CPU,dict(name=name,path=r'C:\Windows\System32\'+name)],False,reason='protected_native_not_eligible')
for index,name in enumerate(m.SEMANTICS['core_names'],1):
    add('post_cpu/missing-'+name,[r for r in NATIVE+[CPU] if r['name']!=name],False,reason='missing_required_reports')
add('post_cpu/missing-self',NATIVE[1:]+[CPU],False,reason='missing_required_reports')
add('post_cpu/max64',NATIVE+[CPU]+[dict(name='platform_'+str(i)+'.dll',path=r'C:\Windows\System32\platform_'+str(i)+'.dll') for i in range(58)],True)
add('post_cpu/over65',NATIVE+[CPU]+[dict(name='platform_'+str(i)+'.dll',path=r'C:\Windows\System32\platform_'+str(i)+'.dll') for i in range(59)],False,reason='module_count_limit')
for phase in ('abi','post_cpu_ready',None,True,1):add('invalid-phase-'+repr(phase),NATIVE+[CPU],False,phase=phase,reason='invalid_phase')
for field,value in [('verified',True),('CPU_module_eligible',True),('policy_class','pinned_runtime')]:
    rows=NATIVE+[dict(CPU,**{field:value})];add('post_cpu/serialized-'+field,rows,False,reason='invalid_metadata')
add('post_cpu/duplicate-protected-precedence',NATIVE+[CPU,dict(name=CPU['name'],path=r'D:\wrong\ggml-cpu-x64.dll')],False,reason='duplicate_report')

class Checks(unittest.TestCase):
    def test_shared_phase_vectors(self):
        for row in CASES:
            with self.subTest(id=row['id']):
                try:value=m.match_modules(row['modules'],phase=row['phase'],**row['context'])
                except m.ModulePolicyError as error:
                    self.assertFalse(row['accepted'])
                    if 'reason_if_isolated' in row:self.assertEqual(error.reason,row['reason_if_isolated'])
                else:
                    self.assertTrue(row['accepted']);self.assertEqual([r['policy_class'] for r in value['reports']],row['expected_classes'])
    def test_fingerprint_matches_immutable_semantic_body(self):
        body=json.dumps(contract['semantic_policy'],sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
        self.assertEqual(hashlib.sha256(body).hexdigest(),m.POLICY_SHA256)
        self.assertEqual(contract['module_policy_sha256'],m.POLICY_SHA256)
        self.assertEqual(contract['semantic_policy'],m.SEMANTICS)
        self.assertNotEqual(old.POLICY_SHA256,m.POLICY_SHA256)
        self.assertEqual(old.POLICY_SHA256,contract['old_ABI_policy_sha256'])
    def test_exact_lexical_primitive_ASTs_preserve_ABI_grammar(self):
        def nodes(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
        before,now=nodes(ABI),nodes(SOURCE)
        for name in ('fail','scalar_length','fold','component','canonical_path','canonical_name'):self.assertEqual(before[name],now[name])
    def test_ABI_still_forbids_CPU_and_post_requires_exact_one(self):
        with self.assertRaises(old.ModulePolicyError):old.match_modules(NATIVE+[CPU],**CONTEXT)
        pre=m.match_modules(NATIVE,phase='pre_cpu',**CONTEXT)
        post=m.match_modules(NATIVE+[CPU],phase='post_cpu',**CONTEXT)
        self.assertFalse(pre['CPU_module_eligible']);self.assertTrue(post['CPU_module_eligible'])
        self.assertEqual(post['required_report_counts'][CPU['name']],1)
        self.assertFalse(post['model_access_authorized'])
    def test_metadata_classification_never_opens_reported_files_or_grants_execution(self):
        with patch('builtins.open',side_effect=AssertionError('No metadata opens')),patch.object(Path,'stat',side_effect=AssertionError('No path stat')),patch.object(Path,'resolve',side_effect=AssertionError('No path resolve')):
            result=m.match_modules(NATIVE+[CPU,PLATFORM],phase='post_cpu',**CONTEXT)
        self.assertEqual(result['platform_image_authentication'],'not_established')
        self.assertFalse(result['model_access_authorized']);self.assertFalse(contract['execution_authorized'])

if __name__=='__main__':
    assert not REPORT.exists() and not VECTORS.exists(),'Preserve existing shared evidence'
    original=pin(SOURCE);started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    vectors=dict(schema_version=1,module_policy_id=m.POLICY_ID,module_policy_sha256=m.POLICY_SHA256,cases=CASES,
        authority='Manual expected admission/category/isolated reason; 73 existing ABI vectors reused in pre_cpu phase only; no current/future code/proof hash in semantics')
    with VECTORS.open('x',encoding='utf-8') as out:json.dump(vectors,out,sort_keys=True,indent=2);out.write('\n')
    assert pin(SOURCE)==original
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        elapsed_seconds=time.monotonic()-started,source=original,ABI_source=pin(ABI),contract=pin(CONTRACT),vectors=pin(VECTORS),
        checker=pin(Path(__file__)),vector_count=len(CASES),module_policy_id=m.POLICY_ID,module_policy_sha256=m.POLICY_SHA256,
        activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,children=0,compiler_calls=0),
        denied_real_operations=DENIED,scope='Pure phase rule/source primitive checks only; no load, tokenization, native conformance or execution permission')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT),vectors=pin(VECTORS),cases=len(CASES))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
