"""Finite metadata/role/publication checks. No constructor, child or DLL load."""
import ast
import copy
import ctypes  # stdlib declarations before the dlopen denial hook.
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'run_platform_abi_observation_v2.py'
OLD=HERE/'run_platform_abi_observation_v1.py'
REPORT=HERE/'TRUSTED-PLATFORM-ABI-BINDING-PURE-PROOF-v2.json'
CACHE=HERE.parents[2]/'data/cache'/('r09-platform-ABI-binding-pure-'+str(time.time_ns()))
CACHE.mkdir()
VECTORS=[];FIXTURES=[];DENIED=[]
def guard(event,args):
    if event in ('subprocess.Popen','os.system','ctypes.dlopen') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No native operation in metadata-only checks')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith('apphelp.dll'):
        DENIED.append('reported_image_open');raise AssertionError('Reported platform image is not an input')
sys.addaudithook(guard)
spec=util.spec_from_file_location('bound_trusted_platform_ABI_metadata',SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)
STATIC=json.loads(h.EXECUTION_AUTHORITY.read_text(encoding='utf-8'))['static_inputs']
COUNT=len(STATIC);assert COUNT==173

def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def evidence(name):
    path=CACHE/(name+'.json')
    path.write_text(json.dumps(dict(status='passed',helper_sha256=h.sha(SOURCE),checker_sha256=h.sha(Path(__file__)),
        actual_children=0,actual_SDK_constructors=0)),encoding='utf-8')
    return path

def nodes(path):
    return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}

class Checks(unittest.TestCase):
    def test_acyclic_static_authority_exact_selected_roster(self):
        value=h.authority();self.assertEqual(value['static_inputs'],STATIC)
        self.assertEqual(set(h.STATIC_PATHS),{r['path'] for r in STATIC})
        self.assertFalse(set(h.STATIC_PATHS)&{str(p) for p in h.dynamic_paths()})
        self.assertNotIn(str(h.PROTOCOL),h.STATIC_PATHS)
        raw=h.EXECUTION_AUTHORITY.read_text(encoding='utf-8')
        self.assertNotIn(h.sha(SOURCE),raw)
        self.assertFalse(value['execution_authorized']);self.assertEqual(value['verified_bridge_executable'],pin(h.EXE))
        VECTORS.append('173-exact-acyclic-static-inputs')
    def test_bad_static_scope_schema_and_alias_rejected_before_leaf_read(self):
        cases=[('missing',copy.deepcopy(STATIC[:-1])),('extra',copy.deepcopy(STATIC)+[dict(path=str(CACHE/'extra.json'),bytes=0,sha256='0'*64)])]
        for name,path in [('self',SOURCE),('authority',h.EXECUTION_AUTHORITY),('checker',h.CHECKER),('proof',h.PURE),
            ('protocol',h.PROTOCOL),('output',CACHE/'output.json'),('unknown-platform',Path(r'C:\Windows\System32\apphelp.dll')),
            ('old-census-EXE',HERE.parents[2]/'data/cache/r09-module-census-build-v1-20261029T011510Z/typed_public_c_recognizer_abi.exe')]:
            value=copy.deepcopy(STATIC);value[0]['path']=str(path);cases.append((name,value))
        for field,replacement in [('bytes',True),('bytes',-1),('sha256','g'*64),('sha256','A'*64),('path',True)]:
            value=copy.deepcopy(STATIC);value[0][field]=replacement;cases.append(('malformed-'+field,value))
        value=copy.deepcopy(STATIC);value[1]=copy.deepcopy(value[0]);cases.append(('duplicate',value))
        value=copy.deepcopy(STATIC);value[0]['extra']=0;cases.append(('extra-field',value))
        with patch.object(h,'pin',side_effect=AssertionError('No leaf reads before scope')):
            for name,value in cases:
                with self.subTest(name=name),self.assertRaises(RuntimeError):h.validate_static_records(value)
                VECTORS.append('static-'+name)
    def test_dynamic_cycle_guard_reached_with_full_combined_shape(self):
        for path in h.dynamic_paths():
            value=copy.deepcopy(STATIC);value[0]['path']=str(path)
            paths=list(h.STATIC_PATHS);paths[0]=str(path)
            with patch.object(h,'STATIC_PATHS',tuple(paths)),patch.object(h,'pin',side_effect=AssertionError('No cycle reads')):
                combined=value+[dict(path=str(p),bytes=0,sha256='0'*64) for p in h.dynamic_paths()]
                with self.assertRaisesRegex(RuntimeError,'cycle'):h.validate_inputs(combined,value)
            VECTORS.append('dynamic-collision-'+path.name)
    def test_current_bytes_are_rehashed_not_trusted_by_manifest_status(self):
        target=STATIC[0]['path'];original=h.pin;calls=[]
        def changed(path):
            calls.append(str(path));value=original(path)
            if str(path)==target:value['sha256']='0'*64
            return value
        with patch.object(h,'PURE',evidence('current-bytes')),patch.object(h,'pin',side_effect=changed):
            with self.assertRaisesRegex(RuntimeError,'Current static input differs'):h.collect_inputs()
        self.assertIn(target,calls);VECTORS.append('current-static-hash-check')
    def test_dynamic_pins_schema_and_changed_bytes(self):
        path=evidence('dynamic')
        with patch.object(h,'PURE',path):
            records=h.collect_inputs();self.assertEqual(len(records),177)
            for field,value in [('bytes',True),('bytes',-1),('sha256','x'*64),('sha256','0'*63)]:
                bad=copy.deepcopy(records);bad[-1][field]=value
                with self.assertRaises(RuntimeError):h.validate_inputs(bad,STATIC)
                VECTORS.append('dynamic-'+field)
            bad=copy.deepcopy(records);bad[-1]['extra']=0
            with self.assertRaises(RuntimeError):h.validate_inputs(bad,STATIC)
            path.write_bytes(b'{"status":"changed"}\n')
            with self.assertRaisesRegex(RuntimeError,'Dynamic'):h.validate_inputs(records,STATIC)
    def test_exact_role_and_argv_reject_new_actions_or_trust_claims(self):
        with patch.object(h,'PURE',evidence('role')):
            records=STATIC+[h.pin(p) for p in h.dynamic_paths()]
            config=h.configuration(CACHE/'future-run',records)
            self.assertEqual(h.validate_role(config),CACHE/'future-run')
            for field,value in [('mode','--module-census'),('mode','--recognize'),('module_policy_sha256','0'*64),
                ('platform_image_authentication','verified'),('reported_platform_path_filesystem_operations',1),
                ('recognition_enabled',True),('no_model_or_CPU_paths_supplied',False),('maximum_attempts',2),
                ('automatic_retry',True),('execution_authorized_by_preparation',True),('explicit_target_calls',['llama_backend_init']),
                ('creation_flags',0x08080004)]:
                bad=copy.deepcopy(config);bad[field]=value
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                VECTORS.append('role-'+field)
            for index,value in [(0,str(CACHE/'wrong.exe')),(1,'--module-census'),(2,str(CACHE/'wrong-runtime'))]:
                bad=copy.deepcopy(config);bad['argv'][index]=value
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                VECTORS.append('argv-'+str(index))
    def test_runtime_closure_excludes_old_exe_and_compiler_model_provider_inputs(self):
        paths=set(h.STATIC_PATHS)
        self.assertTrue({str(h.q.DEFAULT),str(h.q.BASE),str(h.q.DEFAULT.parent.parent/'pyvenv.cfg')}<=paths)
        self.assertEqual(len([p for p in paths if '\\Lib\\site-packages\\asof\\' in p]),85)
        self.assertEqual(len([p for p in paths if '.dist-info\\' in p]),3)
        self.assertEqual(len([p for p in paths if '\\Windows Kits\\10\\Include\\' in p]),6)
        self.assertEqual(len([p for p in paths if p.lower().endswith('.dll')]),20)
        self.assertEqual({p for p in paths if p.lower().endswith('.exe')},{str(h.q.DEFAULT),str(h.q.BASE),str(h.EXE)})
        self.assertFalse(any(p.lower().endswith(('.gguf','.pyd','.obj','.lib')) for p in paths))
        self.assertFalse(any(Path(p).name.lower() in ('cl.exe','link.exe','apphelp.dll','ggml-cpu-x64.dll') for p in paths))
        VECTORS.append('finite-ABI-only-leaves')
    def test_full_prepare_publishes_both_outputs_without_candidate_dispatch(self):
        self.assertTrue(h.PREPARATION.is_relative_to(h.ROOT/'data/cache'))
        protocol=CACHE/'prepare-protocol.json';report=CACHE/'prepare-report.json'
        with patch.object(h,'PURE',evidence('prepare')),patch.object(h,'PROTOCOL',protocol),patch.object(h,'PREPARATION',report):h.prepare()
        value=json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(value['protocol'],pin(protocol));self.assertEqual(value['status'],'prepared_ABI_only_not_execution_authority')
        self.assertFalse(value['execution_authorized']);self.assertTrue(value['output_absent'])
        self.assertEqual((value['actual_children'],value['actual_SDK_constructors']),(0,0))
        FIXTURES.append(dict(case='full-prepare',protocol=pin(protocol),report=pin(report)))
        VECTORS.append('full-prepare-two-exclusive-publications')
    def test_report_publication_failure_preserves_protocol_and_blocks_repeat(self):
        protocol=CACHE/'failed-prepare-protocol.json';report=CACHE/'failed-prepare-report.json';original=h.write_new
        def fail(path,value):
            if Path(path)==report:raise OSError('Synthetic report write failure')
            return original(path,value)
        with patch.object(h,'PURE',evidence('prepare-failure')),patch.object(h,'PROTOCOL',protocol),patch.object(h,'PREPARATION',report),patch.object(h,'write_new',side_effect=fail):
            with self.assertRaisesRegex(OSError,'Synthetic'):h.prepare()
            before=protocol.read_bytes()
            with self.assertRaisesRegex(RuntimeError,'already consumed'):h.prepare()
        self.assertEqual(protocol.read_bytes(),before);self.assertFalse(report.exists())
        FIXTURES.append(dict(case='report-write-failure',protocol=pin(protocol),report_absent=True,repeat_rejected=True))
        VECTORS.append('failed-report-no-repeat')
    def test_source_identical_runtime_parser_and_pure_constructor_rejection(self):
        old,now=nodes(OLD),nodes(SOURCE)
        names=('sha','terminal_observer','api_class','exact','json_value','runtime_pins','abi_argv','execute',
               'policy_matcher','validate_modules','validate_child_rows','validate_child_artifacts')
        for name in names:self.assertEqual(now[name],old[name],name)
        with patch.object(h,'validate_role',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Synthetic ABI configuration'):h.api_class()({'pure_fixture':True},'0'*64)
        self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED)
        VECTORS.append('12-components-unchanged-no-real-constructor')

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve prior evidence'
    original=pin(SOURCE);started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        elapsed_seconds=time.monotonic()-started,helper=original,helper_sha256=original['sha256'],checker_sha256=pin(Path(__file__))['sha256'],
        static_authority=pin(h.EXECUTION_AUTHORITY),static_inputs=COUNT,combined_inputs=COUNT+4,vector_labels=VECTORS,
        unchanged_runtime_parser_functions=12,old_parent=pin(OLD),publication_fixtures=FIXTURES,
        actual_children=0,actual_SDK_constructors=0,real_sdk_constructions=0,compiler_calls=0,reported_platform_image_operations=0,
        actual_execution_protocols_created=0,denied_real_operations=DENIED,
        scope='Exact acyclic metadata preparation and unchanged qualified mechanics. Patched private cache publication fixtures only; no candidate protocol, SDK constructor or child dispatched.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)['sha256'],vectors=len(VECTORS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
