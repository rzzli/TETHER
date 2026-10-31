"""Prospective strict ABI-wire/policy adapter tests; pure ASTs, no SDK import."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'run_platform_abi_observation_v1.py'
OLD=HERE/'run_detached_abi_observation_v6.py'
CONTRACT=HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json'
MATCHER=HERE/'trusted_system32_module_policy_v1.py'
VECTORS=HERE/'TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json'
REPORT=HERE/'TRUSTED-SYSTEM32-ABI-PARENT-PURE-PROOF-v3.json'
SPEC=json.loads(CONTRACT.read_text(encoding='utf-8'))
RAW=SOURCE.read_bytes();TREE=ast.parse(RAW.decode('utf-8'))
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
OLD_TREE=ast.parse(OLD.read_text(encoding='utf-8'))
OLD_FUNCTIONS={n.name:n for n in OLD_TREE.body if isinstance(n,ast.FunctionDef)}
PRESERVED=('sha','terminal_observer','api_class','exact','json_value','runtime_pins','abi_argv','execute')
PURE=('exact','json_value','validate_child_rows','validate_child_artifacts','validate_modules',
      'authority','configuration','validate_role','collect_inputs','prepare')
DENIED=[]
def audit(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','socket.__new__','os.system'):
        DENIED.append(event);raise AssertionError('No actual SDK/child/network in pure source checks')
sys.addaudithook(audit)
spec=util.spec_from_file_location('platform_ABI_policy_for_pure_tests',MATCHER)
m=util.module_from_spec(spec);spec.loader.exec_module(m)
CORE_NAMES=SPEC['semantic_policy']['core_names']
assert type(CORE_NAMES) is list and len(CORE_NAMES)==len(set(CORE_NAMES))==4
assert CORE_NAMES==m.SEMANTICS['core_names']

def require(value,message):
    if not value:raise RuntimeError(message)

CONTEXT=dict(expected_self=r'D:\qualified\future\typed_public_c_recognizer_abi.exe',
             expected_runtime=r'D:\qualified\future\runtime')
NS=dict(json=json,require=require,policy_matcher=lambda:m,Path=Path,EXE=None,
        POLICY_ID=m.POLICY_ID,POLICY_SHA=m.POLICY_SHA256)
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(FUNCTIONS[n]) for n in PURE],type_ignores=[])),
             str(SOURCE)+'::<pure AST only>','exec'),NS)

def valid_modules(context=CONTEXT):
    return [dict(name='typed_public_c_recognizer_abi.exe',path=context['expected_self']),
        *[dict(name=name,path=context['expected_runtime']+'\\'+name) for name in CORE_NAMES],
        dict(name='apphelp.dll',path=r'C:\Windows\System32\apphelp.dll')]

def rows():
    return [dict(event='before_explicit_required_OpenMP_dependency_load',dependency_native_initialization_possible=True),
        dict(event='exact_core_modules_loaded_exports_resolved',modules=valid_modules(),
             layouts=copy.deepcopy(SPEC['expected_layouts']),module_policy_id=m.POLICY_ID,module_policy_sha256=m.POLICY_SHA256),
        dict(event='typed_version_and_defaults_observed',version='synthetic-only-v1',
             defaults=copy.deepcopy(SPEC['expected_defaults']),no_backend_or_model_call_so_far=True),
        dict(event='abi_observations_returned',version_expected_previously_known=False,
             backend_init_called=False,registry_called=False,model_called=False,
             scope='typed version/defaults observation; independent ABI acceptance pending'),
        dict(event='child_normal_completion',mode='--abi',elapsed_ms=0,parent_qualification_required=True)]

def validate(value,context=CONTEXT):
    return NS['validate_child_rows'](value,contract=SPEC,**context)

def changed(value):
    if type(value) is bool:return int(value)
    if type(value) is int:return value+1
    if type(value) is float:return value+1
    if value is None:return False
    if type(value) is str:return value+'-changed'
    raise AssertionError(type(value))

VECTORS_RUN=[]
def reject(label,value,context=CONTEXT):
    try:validate(value,context)
    except (ValueError,RuntimeError):VECTORS_RUN.append(dict(id=label,rejected=True));return
    raise AssertionError('Unexpected acceptance: '+label)

def leaves(value,prefix=()):
    if type(value) is dict:
        for key,item in value.items():yield from leaves(item,(*prefix,key))
    else:yield prefix,value

def set_leaf(value,path,replacement):
    target=value
    for key in path[:-1]:target=target[key]
    target[path[-1]]=replacement

class Checks(unittest.TestCase):
    def test_preserved_eight_runtime_component_ASTs(self):
        for name in PRESERVED:
            with self.subTest(name=name):self.assertEqual(ast.dump(FUNCTIONS[name]),ast.dump(OLD_FUNCTIONS[name]))
    def test_unbound_authority_rejects_every_operational_entry(self):
        for name,args in [('authority',()),('configuration',(None,None)),('validate_role',({},)),('collect_inputs',()),('prepare',())]:
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'Unbound trusted-platform ABI source'):
                NS[name](*args)
        with self.assertRaisesRegex(RuntimeError,'Unbound ABI context'):NS['validate_modules'](valid_modules())
        self.assertIs(SPEC['execution_authorized'],False);self.assertIsNone(SPEC['verified_bridge_executable'])
        self.assertIsNone(SPEC['verified_build_proof'])
    def test_new_positive_wire_keeps_native_default_layout_types_and_scope(self):
        result=validate(rows())
        self.assertEqual(result['module_policy_sha256'],m.POLICY_SHA256)
        self.assertEqual([r['policy_class'] for r in result['module_classification']['reports']],
                         ['self_executable']+['pinned_runtime']*4+['trusted_platform_context'])
        self.assertEqual(result['independent_ABI_acceptance'],'pending')
        self.assertEqual(result['scientific_validation'],'not_established')
    def test_old_or_forged_policy_wire_is_rejected(self):
        for key in ('module_policy_id','module_policy_sha256'):
            value=rows();del value[1][key];reject('missing-'+key,value)
            for replacement in ('wrong',False,1,None):
                value=rows();value[1][key]=replacement;reject('wrong-'+key+'-'+repr(replacement),value)
        value=rows();value[1]['modules'][5]['verified']=True;reject('serialized-verified',value)
        value=rows();value[1]['modules'][5]['policy_class']='trusted_platform_context';reject('child-policy-class',value)
    def test_each_native_default_and_layout_leaf_retains_exact_comparison(self):
        for field,index in [('defaults',2),('layouts',1)]:
            for path,value in leaves(SPEC['expected_'+field]):
                item=rows();set_leaf(item[index][field],path,changed(value));reject(field+'-'+'.'.join(path),item)
            item=rows();item[index][field]['invented']=0;reject(field+'-extra-key',item)
            item=rows();del item[index][field][next(iter(item[index][field]))];reject(field+'-missing-key',item)
    def test_all73_shared_module_vectors_are_enforced_inside_five_row_parser(self):
        vectors=json.loads(VECTORS.read_text(encoding='utf-8'))['cases']
        self.assertEqual(len(vectors),73)
        for vector in vectors:
            value=rows();value[1]['modules']=copy.deepcopy(vector['modules'])
            with self.subTest(id=vector['id']):
                if vector['accepted']:
                    result=validate(value,vector['context'])
                    self.assertEqual([r['policy_class'] for r in result['module_classification']['reports']],vector['expected_classes'])
                    VECTORS_RUN.append(dict(id='wire-'+vector['id'],accepted=True))
                else:reject('wire-'+vector['id'],value,vector['context'])
    def test_version_sequence_scope_and_JSON_authority_not_coerced(self):
        for version in ('','x'*256,'a\x00b','é',True,3):
            value=rows();value[2]['version']=version;reject('version-'+repr(version),value)
        for version in ('x','x'*255,' !~'):
            value=rows();value[2]['version']=version;validate(value)
        for index,key in [(0,'dependency_native_initialization_possible'),(2,'no_backend_or_model_call_so_far'),
                          (3,'backend_init_called'),(3,'registry_called'),(3,'model_called'),(4,'parent_qualification_required')]:
            value=rows();value[index][key]=changed(value[index][key]);reject('scope-'+key,value)
        for elapsed in (-1,30001,False,0.5):
            value=rows();value[4]['elapsed_ms']=elapsed;reject('elapsed-'+repr(elapsed),value)
        for elapsed in (0,30000):value=rows();value[4]['elapsed_ms']=elapsed;validate(value)
        for value in (rows()[:-1],rows()+[rows()[-1]],list(reversed(rows()))):reject('event-count-or-order',value)
        for raw in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','{"a":-Infinity}'):
            with self.assertRaises(RuntimeError):NS['json_value'](raw)
    def test_reported_platform_paths_have_no_filesystem_operation(self):
        value=rows()
        with mock.patch('builtins.open',side_effect=AssertionError('Reported path opened')), \
             mock.patch.object(Path,'open',side_effect=AssertionError('Reported path opened')), \
             mock.patch.object(Path,'stat',side_effect=AssertionError('Reported path stat')), \
             mock.patch.object(Path,'resolve',side_effect=AssertionError('Reported path resolve')):
            result=validate(value)
        self.assertEqual(result['module_classification']['platform_image_authentication'],'not_established')

def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

if __name__=='__main__':
    started=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    require(SOURCE.read_bytes()==RAW,'Parent source mutated during pure checks')
    proof=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,failures=[str(c) for c,_ in result.failures],
        errors=[dict(test=str(c),trace=t) for c,t in result.errors],elapsed_seconds=time.monotonic()-started,
        helper=pin(SOURCE),helper_sha256=pin(SOURCE)['sha256'],contract=pin(CONTRACT),matcher=pin(MATCHER),vectors=pin(VECTORS),
        checker=pin(Path(__file__)),preserved_runtime_ASTs={n:hashlib.sha256(ast.dump(FUNCTIONS[n]).encode()).hexdigest() for n in PRESERVED},
        pure_component_ASTs={n:hashlib.sha256(ast.dump(FUNCTIONS[n]).encode()).hexdigest() for n in PURE},
        checks=VECTORS_RUN,actual_children=0,real_sdk_constructions=0,compiler_calls=0,reported_image_operations=0,
        denied_operations=DENIED,scope='Source/pure-only unbound parent adapter. Preserved runtime ASTs reuse prior mechanics evidence; no new runtime/ABI qualification.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)['sha256'],tests=result.testsRun,checks=len(VECTORS_RUN))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
