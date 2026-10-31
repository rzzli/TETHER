"""Bounded software/descriptor/acylcic publication checks; no runtime or payload I/O."""
import ast
import copy
import ctypes  # stdlib declarations only, before the dlopen denial hook.
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'run_recognition_observation_v7.py'
OLD=HERE/'run_recognition_observation_v6.py'
REPORT=HERE/'RECOGNITION-BINDING-PURE-PROOF-v1.json'
CACHE=ROOT/'data/cache'/('r09-recognition-binding-pure-'+str(time.time_ns()));CACHE.mkdir()
CONTRACT=json.loads((HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json').read_text(encoding='utf-8'))
MANIFEST=json.loads((HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json').read_text(encoding='utf-8'))
PAYLOADS=[CONTRACT['CPU_descriptor'],*CONTRACT['ordered_shard_descriptors'],MANIFEST['pack']]
def key(path):return str(path).replace('/','\\').lower()
PAYLOAD_KEYS={key(r['path']) for r in PAYLOADS}
DENIED=[];PAYLOAD_OPERATIONS=[];VECTORS=[];FIXTURES=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No SDK/child/native/network in binding checks')
    if event=='open' and args and isinstance(args[0],(str,bytes)):
        if key(args[0]) in PAYLOAD_KEYS:
            PAYLOAD_OPERATIONS.append('open');raise AssertionError('Descriptor-only payload opened')
        if str(args[0]).lower().endswith('apphelp.dll'):
            DENIED.append('reported-platform-open');raise AssertionError('Reported platform image is not an input')
sys.addaudithook(guard)
ORIGINAL_PATH={name:getattr(Path,name) for name in ('stat','lstat','resolve','open')}
def guarded_path(name):
    def call(path,*args,**kwargs):
        if key(path) in PAYLOAD_KEYS:
            PAYLOAD_OPERATIONS.append(name);raise AssertionError('Descriptor-only payload '+name)
        return ORIGINAL_PATH[name](path,*args,**kwargs)
    return call
for NAME in ORIGINAL_PATH:setattr(Path,NAME,guarded_path(NAME))
spec=util.spec_from_file_location('recognition_acyclic_binding_pure',SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)
STATIC=json.loads(h.EXECUTION_AUTHORITY.read_text(encoding='utf-8'))['software_inputs']
COUNT=len(STATIC)
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def evidence(name):
    path=CACHE/(name+'.json')
    path.write_text(json.dumps(dict(status='passed',helper_sha256=pin(SOURCE)['sha256'],checker_sha256=pin(Path(__file__))['sha256'],
        actual_children=0,actual_SDK_constructors=0,payload_path_operations=0)),encoding='utf-8')
    return path
def nodes(path):
    return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
def combined():return STATIC+[h.pin(p) for p in h.dynamic_paths()]
def log(name):VECTORS.append(name)

class Checks(unittest.TestCase):
    def test_exact_acyclic_roster_and_verified_build(self):
        with patch.object(h,'PURE',evidence('roster')):
            value=h.authority()
            self.assertEqual(value['static_inputs'],STATIC);self.assertEqual(len(value['software_inputs']),COUNT+4)
            self.assertEqual(set(h.STATIC_PATHS),{r['path'] for r in STATIC})
            self.assertFalse(set(h.STATIC_PATHS)&{str(p) for p in h.dynamic_paths()})
            self.assertNotIn(str(h.PROTOCOL),h.STATIC_PATHS)
            raw=h.EXECUTION_AUTHORITY.read_text(encoding='utf-8')
            self.assertNotIn(pin(SOURCE)['sha256'],raw);self.assertFalse(value['execution_authorized'])
            self.assertFalse(value['runtime_qualified']);self.assertEqual(value['executable'],pin(h.EXE))
            self.assertEqual(value['executable']['sha256'],'382754c8d947e68541262905c9289a3c80cdb2efdc505efead7f0219f628482b')
            self.assertEqual(value['payload_descriptors'],PAYLOADS)
        log('exact-static-four-dynamic-five-descriptor-acyclic-build')
    def test_bad_static_schema_scope_aliases_and_cycles_before_leaf_access(self):
        cases=[('missing',copy.deepcopy(STATIC[:-1])),('extra',copy.deepcopy(STATIC)+[dict(path=str(CACHE/'extra.json'),bytes=0,sha256='0'*64)])]
        paths=[SOURCE,h.EXECUTION_AUTHORITY,h.CHECKER,h.PURE,h.PROTOCOL,h.PREPARATION,CACHE/'future-output.json',
            Path(r'C:\Windows\System32\apphelp.dll'),Path(PAYLOADS[0]['path']),Path(PAYLOADS[1]['path']),Path(PAYLOADS[-1]['path']),
            ROOT/'data/cache/r09-trusted-platform-bridge-build-v2-20261029T024601Z/typed_public_c_recognizer_abi.exe']
        for path in paths:
            bad=copy.deepcopy(STATIC);bad[0]['path']=str(path);cases.append(('scope-'+path.name,bad))
        for field,value in [('bytes',True),('bytes',-1),('bytes',128*1024**2+1),('sha256','A'*64),('sha256','0'*63),('path',True)]:
            bad=copy.deepcopy(STATIC);bad[0][field]=value;cases.append(('field-'+field,bad))
        bad=copy.deepcopy(STATIC);bad[0]['extra']=0;cases.append(('extra-key',bad))
        bad=copy.deepcopy(STATIC);bad[1]=copy.deepcopy(bad[0]);cases.append(('duplicate',bad))
        bad=copy.deepcopy(STATIC);bad[0]['path']=bad[0]['path'].swapcase();cases.append(('case-alias',bad))
        with patch.object(h,'software_pin',side_effect=AssertionError('Rejected static path must not be accessed')):
            for name,bad in cases:
                with self.subTest(name=name),self.assertRaises(RuntimeError):h.validate_static_records(bad)
                log('static-'+name)
        for path in (*h.dynamic_paths(),h.PROTOCOL,*[Path(r['path']) for r in PAYLOADS]):
            bad=copy.deepcopy(STATIC);bad[0]['path']=str(path)
            scope=list(h.STATIC_PATHS);scope[0]=str(path)
            with patch.object(h,'STATIC_PATHS',tuple(scope)),self.assertRaisesRegex(RuntimeError,'cycle'):
                h.validate_static_records(bad)
            log('full-shape-cycle-'+path.name)
    def test_dynamic_schema_current_hash_and_collisions(self):
        with patch.object(h,'PURE',evidence('dynamic')):
            good=combined();self.assertEqual(h.validate_software_inputs(good,STATIC),good)
            for field,value in [('bytes',True),('bytes',-1),('sha256','x'*64),('sha256','0'*63),('path',str(CACHE/'extra-current.py'))]:
                bad=copy.deepcopy(good);bad[-1][field]=value
                with self.assertRaises(RuntimeError):h.validate_software_inputs(bad,STATIC)
                log('dynamic-'+field)
            for change in ('missing','duplicate','extra','extra-key','case-alias'):
                bad=copy.deepcopy(good)
                if change=='missing':bad.pop()
                elif change=='duplicate':bad[-1]=copy.deepcopy(bad[-2])
                elif change=='extra':bad.append(dict(path=str(CACHE/'extra.py'),bytes=0,sha256='0'*64))
                elif change=='extra-key':bad[-1]['extra']=0
                else:bad[-1]['path']=bad[-1]['path'].swapcase()
                with self.assertRaises(RuntimeError):h.validate_software_inputs(bad,STATIC)
                log('dynamic-'+change)
            Path(h.PURE).write_bytes(b'{"status":"changed"}\n')
            with self.assertRaisesRegex(RuntimeError,'Dynamic'):h.validate_software_inputs(good,STATIC)
        log('current-dynamic-bytes-rehashed')
    def test_current_software_hashes_are_checked_and_payloads_never_read(self):
        target=STATIC[0]['path'];original=h.software_pin;calls=[]
        def changed(path):
            calls.append(str(path));row=original(path)
            if str(path)==target:row['sha256']='0'*64
            return row
        with patch.object(h,'PURE',evidence('hash-change')),patch.object(h,'software_pin',side_effect=changed):
            with self.assertRaisesRegex(RuntimeError,'Current software input differs'):h.collect_inputs()
        self.assertIn(target,calls)
        with patch.object(h,'PURE',evidence('full-collection')):
            rows=h.collect_inputs();self.assertEqual(len(rows),COUNT+9);self.assertEqual(rows[-5:],PAYLOADS)
        self.assertEqual(PAYLOAD_OPERATIONS,[])
        for row in PAYLOADS:
            with self.assertRaisesRegex(RuntimeError,'outside exact software roster'):h.software_pin(row['path'])
        log('all-current-software-verified-five-payloads-descriptor-only')
    def test_payload_tampering_order_and_cross_role_aliases_rejected(self):
        with patch.object(h,'PURE',evidence('payload-tamper')):
            software=combined();good=software+PAYLOADS
            self.assertEqual(h.validate_role_inputs(good,software),good)
            for index in range(5):
                for field,value in [('bytes',PAYLOADS[index]['bytes']+1),('sha256','0'*64),('path',PAYLOADS[index]['path'].swapcase())]:
                    bad=copy.deepcopy(good);bad[-5+index][field]=value
                    with self.assertRaises(RuntimeError):h.validate_role_inputs(bad,software)
                    log('payload-'+str(index)+'-'+field)
            badsoftware=copy.deepcopy(software);badsoftware[0]=dict(PAYLOADS[0],path=PAYLOADS[0]['path'].swapcase())
            with self.assertRaises(RuntimeError):h.validate_software_inputs(badsoftware,STATIC)
            # Fixed nine-argument ordering is checked independently of set-based input admission.
            args=[h.EXE,h.RUNTIME,CACHE/'future/execution/child',PAYLOADS[-1]['path'],'ggml-cpu-x64.dll',[r['path'] for r in CONTRACT['ordered_shard_descriptors']]]
            argv,_=h.recognition_argv(*args);self.assertEqual(argv[-3:],args[-1])
            args[-1]=list(reversed(args[-1]))
            with self.assertRaises(RuntimeError):h.recognition_argv(*args)
        log('payload-model-order-and-canonical-role-collision')
    def test_actual_format_build_output_locators_and_identity_rejections(self):
        build=json.loads(h.VERIFIED_BUILD.read_text(encoding='utf-8'))
        for relative in ('build-report.json','receipt.json','terminal-seal.json','post-lease-cleanup.json'):
            row=h.build_output_record(build,relative);self.assertEqual(row['path'],str(h.EXE.parent/relative))
        for bad in ('../build-report.json','./build-report.json','x/build-report.json','x\\build-report.json',r'D:\build-report.json','BUILD-REPORT.JSON','bridge.obj'):
            with self.assertRaises(RuntimeError):h.build_output_record(build,bad)
            log('build-locator-'+bad)
        for mutation in ('root','duplicate','extra-key','boolean-size'):
            bad=copy.deepcopy(build)
            if mutation=='root':bad['output_directory']=str(CACHE)
            else:
                row=next(r for r in bad['outputs'] if r['path']=='build-report.json')
                if mutation=='duplicate':bad['outputs'].append(copy.deepcopy(row))
                elif mutation=='extra-key':row['extra']=0
                else:row['bytes']=True
            with self.assertRaises(RuntimeError):h.build_output_record(bad,'build-report.json')
            log('build-output-'+mutation)
        original=h.verified_metadata
        for kind in ('old-status','wrong-exe','wrong-header','wrong-source','disabled-recognition','authorized','version','policy'):
            def changed(path,expected,kind=kind):
                value=original(path,expected)
                if Path(path)==h.VERIFIED_BUILD:
                    if kind=='old-status':value['status']='VERIFIED_trusted_platform_bridge_compiled_recognition_disabled_NOT_EXECUTED'
                    elif kind=='wrong-exe':value['executable']['sha256']='0'*64
                    elif kind=='wrong-header':value['header']['sha256']='0'*64
                    elif kind=='wrong-source':value['source']['sha256']='0'*64
                    elif kind=='disabled-recognition':value['policy']['recognition_enabled']=False
                    elif kind=='authorized':value['policy']['runtime_execution_authorized']=True
                    elif kind=='version':value['policy']['expected_version']='other'
                    else:value['policy']['semantic_sha256']='0'*64
                return value
            with patch.object(h,'PURE',evidence('build-'+kind)),patch.object(h,'verified_metadata',side_effect=changed),self.assertRaises(RuntimeError):h.authority()
            log('build-identity-'+kind)
    def test_bound_configuration_exact_scope_argv_and_constructor_guard(self):
        with patch.object(h,'PURE',evidence('role')):
            rows=combined()+PAYLOADS;value=h.configuration(CACHE/'role-future',rows)
            self.assertEqual(h.validate_role(value),CACHE/'role-future');self.assertEqual(len(value['argv']),9)
            self.assertEqual(value['executable'],pin(h.EXE));self.assertEqual(value['contract_sha256'],h.CONTRACT_SHA)
            for field,replacement in [('mode','--abi'),('mode','--module-census'),('maximum_attempts',2),('automatic_retry',True),
                ('full_vocabulary_mask',True),('inference',True),('cooperative_work_ms',120000),('parent_seconds',301),('child_seconds',121),
                ('module_policy_sha256','0'*64),('execution_authorized_by_preparation',True),('creation_flags',0x8080004)]:
                bad=copy.deepcopy(value);bad[field]=replacement
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                log('role-'+field)
            for index,replacement in [(0,str(CACHE/'old.exe')),(1,'--abi'),(4,str(CACHE/'subset.pack')),(5,'ggml-vulkan.dll')]:
                bad=copy.deepcopy(value);bad['argv'][index]=replacement
                with self.assertRaises(RuntimeError):h.validate_role(bad)
                log('argv-'+str(index))
        with patch.object(h,'validate_role',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Synthetic recognition'):h.api_class()({'pure_fixture':True},'0'*64)
        self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED);log('bound-role-no-real-constructor')
    def test_finite_software_universe_has_no_old_exe_compiler_or_payloads(self):
        paths=set(h.STATIC_PATHS)
        self.assertEqual(len([p for p in paths if '\\Lib\\site-packages\\asof\\' in p]),85)
        self.assertEqual(len([p for p in paths if '.dist-info\\' in p]),3)
        self.assertEqual(len([p for p in paths if '\\Windows Kits\\10\\Include\\' in p]),6)
        self.assertEqual(len([p for p in paths if p.lower().endswith('.dll')]),20)
        self.assertEqual({p for p in paths if p.lower().endswith('.exe')},{str(h.q.DEFAULT),str(h.q.BASE),str(h.EXE)})
        self.assertFalse(any(p.lower().endswith(('.gguf','.pyd','.obj','.lib')) for p in paths))
        self.assertFalse(any(Path(p).name.lower() in ('cl.exe','link.exe','apphelp.dll','ggml-cpu-x64.dll') for p in paths))
        self.assertFalse(PAYLOAD_KEYS&{key(p) for p in paths});log('finite-software188-and-five-separate-descriptors')
    def test_full_prepare_publication_both_outputs_repeat_and_no_dispatch(self):
        protocol=CACHE/'prepare-protocol.json';report=CACHE/'prepare-report.json'
        self.assertTrue(h.PREPARATION.is_relative_to(ROOT/'data/cache'))
        with patch.object(h,'PURE',evidence('prepare')),patch.object(h,'PROTOCOL',protocol),patch.object(h,'PREPARATION',report):
            h.prepare();before=protocol.read_bytes()
            with self.assertRaisesRegex(RuntimeError,'already consumed'):h.prepare()
        value=json.loads(report.read_text(encoding='utf-8'));config=json.loads(protocol.read_text(encoding='utf-8'))
        self.assertEqual(value['protocol'],pin(protocol));self.assertTrue(value['output_absent'])
        self.assertEqual(value['status'],'prepared_singleton_recognition_metadata_not_execution_authority')
        self.assertEqual((value['actual_children'],value['actual_SDK_constructors'],value['payload_path_operations']),(0,0,0))
        self.assertFalse(value['execution_authorized']);self.assertEqual(config['payload_inputs'],PAYLOADS)
        self.assertEqual(protocol.read_bytes(),before);self.assertIsNone(h._OWNER_DEADLINE)
        FIXTURES.append(dict(case='full-prepare',protocol=pin(protocol),report=pin(report),repeat_rejected=True));log('full-prepare-two-publications-no-repeat')
    def test_failed_publication_preserves_protocol_and_clock_and_preexisting_veto(self):
        protocol=CACHE/'failed-prepare-protocol.json';report=CACHE/'failed-prepare-report.json';original=h.write_new
        def fail(path,value):
            if Path(path)==report:raise OSError('Synthetic preparation report write failure')
            return original(path,value)
        with patch.object(h,'PURE',evidence('report-failure')),patch.object(h,'PROTOCOL',protocol),patch.object(h,'PREPARATION',report),patch.object(h,'write_new',side_effect=fail):
            with self.assertRaisesRegex(OSError,'Synthetic'):h.prepare()
            before=protocol.read_bytes()
            with self.assertRaisesRegex(RuntimeError,'already consumed'):h.prepare()
        self.assertEqual(protocol.read_bytes(),before);self.assertFalse(report.exists());self.assertIsNone(h._OWNER_DEADLINE)
        FIXTURES.append(dict(case='report-write-failure',protocol=pin(protocol),report_absent=True,repeat_rejected=True))
        protocol2=CACHE/'never-written-protocol.json';report2=CACHE/'preexisting-report.json';report2.write_bytes(b'original marker')
        with patch.object(h,'PROTOCOL',protocol2),patch.object(h,'PREPARATION',report2),self.assertRaisesRegex(RuntimeError,'already consumed'):h.prepare()
        self.assertFalse(protocol2.exists());self.assertEqual(report2.read_bytes(),b'original marker')
        FIXTURES.append(dict(case='preexisting-report',report=pin(report2),protocol_absent=True));log('exclusive-publication-failure-no-retry-clock-released')
    def test_runtime_components_and_source_clock_are_preserved(self):
        old,now=nodes(OLD),nodes(SOURCE)
        unchanged=('execute','api_class','recognition_argv','configuration','validate_role','validate_role_inputs','role_of',
            'validate_child_artifacts','terminal_observer','parent_payload_observations','status_sealer','policy_matcher','source_contract',
            'expected_pack','payload_records','metadata_path','check_owner_clock','sha','pin','own_source','verified_metadata',
            'roles','exact','json_value')
        for name in unchanged:self.assertEqual(now[name],old[name],name)
        self.assertIn('owner_started',ast.get_source_segment(SOURCE.read_text(encoding='utf-8'),next(n for n in ast.parse(SOURCE.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='execute')))
        self.assertFalse(h.sdk.NATIVE_EXECUTION_ENABLED);self.assertEqual(PAYLOAD_OPERATIONS,[])
        log('24-runtime-role-parser-clock-components-unchanged')

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve earlier proof'
    original=pin(SOURCE);started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[dict(test=str(c),trace=t) for c,t in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        helper=original,helper_sha256=original['sha256'],checker_sha256=pin(Path(__file__))['sha256'],
        static_authority=pin(h.EXECUTION_AUTHORITY),static_software=COUNT,software_inputs=COUNT+4,payload_descriptors=5,
        total_inputs=COUNT+9,elapsed_seconds=time.monotonic()-started,vector_labels=VECTORS,publication_fixtures=FIXTURES,
        unchanged_runtime_components=24,original_parent=pin(OLD),source_contract=pin(h.CONTRACT),expected_pack_metadata=pin(h.EXPECTED_PACK),
        actual_children=0,actual_SDK_constructors=0,real_sdk_constructions=0,compiler_calls=0,payload_path_operations=len(PAYLOAD_OPERATIONS),
        denied_real_operations=DENIED,actual_execution_protocols_created=0,
        scope='Current software/descriptor binding and private cache publication fixtures only. No candidate protocol, SDK/Job/process constructor or CPU/GGUF/pack path inspected.')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)['sha256'],vectors=len(VECTORS),fixtures=len(FIXTURES))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
