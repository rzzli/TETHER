"""Focused new synthetic captures only; no original archive or payload replay."""
import ast
import copy
import dataclasses
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'captured_archive_v3.py'
FIXTURES=HERE/'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json'
CONTRACT=HERE/'CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json'
PROOF=HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json'
M=None;OLD=None;CASES=None;OBS=[];REGRESSIONS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=sha(raw))
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def docs(v):return canonical(v)+b'\n'
def capture(case):
    c=case['captured'];return M.CapturedArchive(None if c['protocol_hex'] is None else bytes.fromhex(c['protocol_hex']),
        None if c['authority_hex'] is None else bytes.fromhex(c['authority_hex']),tuple((x['locator'],bytes.fromhex(x['raw_hex'])) for x in c['run_files']))
def bindings(case):
    b=case['bindings'];p=lambda x:M.MetadataPin(**x)
    return M.ArchiveBindings(b['policy_id'],b['run_root'],p(b['protocol_pin']),p(b['authority_pin']),p(b['helper_pin']),
        tuple(map(p,b['static_software_pins'])),tuple(M.DynamicPin(x['role'],p(x['pin'])) for x in b['dynamic_pins']),tuple(map(p,b['payload_descriptors'])))
def base():return capture(CASES[0]),bindings(CASES[0])

def rebound(c,b,files,protocol=None):
    """Rebuild only the synthetic dependency maps affected by one mutation."""
    files=dict(files)
    def short(raw):return dict(bytes=len(raw),sha256=sha(raw))
    def full(name):return dict(path=b.run_root+'\\'+name.replace('/','\\'),**short(files[name]))
    if protocol is not None:
        raw=docs(protocol)
        c=dataclasses.replace(c,protocol_bytes=raw)
        b=dataclasses.replace(b,protocol_pin=dataclasses.replace(b.protocol_pin,**short(raw)))
        files['effective-protocol.json']=raw
        journal=[json.loads(row) for row in files['execution/journal.jsonl'].splitlines()]
        journal[1]['details']['protocol_sha256']=sha(raw)
        journal[1]['sha256']=sha(canonical({k:v for k,v in journal[1].items() if k!='sha256'}))
        files['execution/journal.jsonl']=b''.join(docs(row) for row in journal)
        receipt=json.loads(files['receipt.json']);receipt['protocol_sha256']=sha(raw);files['receipt.json']=docs(receipt)
    receipt=json.loads(files['receipt.json'])
    receipt['outputs']={name:short(files[name]) for name in receipt['outputs']}
    files['receipt.json']=docs(receipt)
    cleanup=json.loads(files['post-lease-cleanup.json']);cleanup['earlier_receipt']=full('receipt.json')
    files['post-lease-cleanup.json']=docs(cleanup)
    seal=json.loads(files['terminal-seal.json']);seal['earlier_receipt']=full('receipt.json');seal['cleanup_artifact']=full('post-lease-cleanup.json')
    seal['outputs']={name:short(files[name]) for name in seal['outputs']};files['terminal-seal.json']=docs(seal)
    assert all(item==short(files[name]) for name,item in receipt['outputs'].items())
    assert all(item==short(files[name]) for name,item in seal['outputs'].items())
    assert cleanup['earlier_receipt']==full('receipt.json') and seal['cleanup_artifact']==full('post-lease-cleanup.json')
    assert b.protocol_pin.bytes==len(c.protocol_bytes) and b.protocol_pin.sha256==sha(c.protocol_bytes)
    return dataclasses.replace(c,run_files=tuple(files.items())),b

def legacy(c,b):
    p=lambda x:OLD.MetadataPin(**dataclasses.asdict(x))
    old_c=OLD.CapturedArchive(c.protocol_bytes,c.authority_bytes,c.run_files)
    old_b=OLD.ArchiveBindings(b.policy_id,b.run_root,p(b.protocol_pin),p(b.authority_pin),p(b.helper_pin),
        tuple(map(p,b.static_software_pins)),tuple(OLD.DynamicPin(x.role,p(x.pin)) for x in b.dynamic_pins),tuple(map(p,b.payload_descriptors)))
    return old_c,old_b
def replace_file(c,name,raw):
    return dataclasses.replace(c,run_files=tuple((key,raw if key==name else value) for key,value in c.run_files))
def project(test,actual,expected):
    for key,value in expected.items():test.assertIn(key,actual);test.assertIs(type(actual[key]),type(value));test.assertEqual(actual[key],value)

class Tests(unittest.TestCase):
    def run_check(self,c,b):return M.check_archive(c,b,check=lambda:None).to_dict()
    def test_01_all_thirtytwo_frozen_graph_expectations(self):
        self.assertEqual(len(CASES),32)
        for case in CASES:
            with self.subTest(case=case['id']):
                result=self.run_check(capture(case),bindings(case));OBS.append(dict(id=case['id'],result=result));project(self,result,case['expected_projection'])

    def test_02_earlier_bytes_early_unknown_and_exception_supplement(self):
        by={c['id']:c for c in CASES};positive=dict(capture(by['complete_positive_captured_graph']).run_files)
        pub=dict(capture(by['publication_after_receipt']).run_files)
        self.assertEqual(positive['parent-report.json'],pub['parent-report.json']);self.assertEqual(positive['receipt.json'],pub['receipt.json'])
        exception=dict(capture(by['exception_after_terminal']).run_files);self.assertEqual(positive['terminal-seal.json'],exception['terminal-seal.json'])
        early=capture(by['early_initialization']);report=json.loads(dict(early.run_files)['parent-report.json'])
        self.assertNotIn('returncode',report);self.assertNotIn('reaped',report);self.assertEqual(json.loads(dict(early.run_files)['post-lease-cleanup.json'])['outcomes'],[])
        self.assertEqual(self.run_check(early,bindings(by['early_initialization']))['source_terminal_disposition'],'source_negative')
        c,b=base();empty=dataclasses.replace(c,run_files=());result=self.run_check(empty,b)
        self.assertEqual(result['captured_graph_status'],'incomplete_captured_graph');self.assertEqual(result['source_terminal_disposition'],'unresolved');self.assertIn('receipt.json',result['missing_nodes'])

    def test_03_strict_JSON_bool_fields_and_filename_veto(self):
        c,b=base();original=json.loads(dict(c.run_files)['parent-report.json'])
        for mode in ('duplicate','nonfinite','BOM','CRLF','surrogate','depth','nodes','bool_version','bool_returncode'):
            report=copy.deepcopy(original)
            if mode=='duplicate':raw=docs(report)[:-2]+b',"status":"failed"}\n'
            elif mode=='nonfinite':raw=docs(report).replace(b'"schema_version":1',b'"schema_version":NaN')
            elif mode=='BOM':raw=b'\xef\xbb\xbf'+docs(report)
            elif mode=='CRLF':raw=docs(report)[:-1]+b'\r\n'
            elif mode=='surrogate':raw=docs(report)[:-2]+b',"unknown":"\\ud800"}\n'
            elif mode=='depth':
                value=0
                for _ in range(33):value=[value]
                report['nested']=value;raw=docs(report)
            elif mode=='nodes':report['extra']=[0]*100001;raw=docs(report)
            else:report['schema_version' if mode=='bool_version' else 'returncode']=True;raw=docs(report)
            result=self.run_check(replace_file(c,'parent-report.json',raw),b)
            self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph',mode)
        raw=b'{"authoritative":false,"ready":true}\n'
        marker=M.CapturedArchive(c.protocol_bytes,c.authority_bytes,c.run_files+(('failure.json',raw),))
        result=self.run_check(marker,b);self.assertEqual(result['source_terminal_disposition'],'source_negative');self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph')

    def test_04_maps_graph_cycles_and_missing_nodes(self):
        c,b=base()
        for name,target in [('receipt.json','terminal-seal.json'),('receipt.json','post-lease-cleanup.json'),('terminal-seal.json','terminal-seal.json')]:
            data=json.loads(dict(c.run_files)[name]);data['outputs'][target]={'bytes':0,'sha256':sha(b'')}
            result=self.run_check(replace_file(c,name,docs(data)),b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph')
            self.assertTrue(any('future_or_self_map_edge' in x for x in result['issues']))
        data=json.loads(dict(c.run_files)['terminal-seal.json']);data['cleanup_artifact']['path']='D:\\other\\post-lease-cleanup.json'
        result=self.run_check(replace_file(c,'terminal-seal.json',docs(data)),b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph')
        a=M._Analysis(lambda:None);a.edge('a','b');a.edge('b','c');a.edge('c','a')
        with self.assertRaises(M._Bad):a.cycles()
        a=M._Analysis(lambda:None)
        for i in range(4096):a.edge('root','leaf'+str(i))
        with self.assertRaises(M._Bad):a.edge('root','overflow')
        # A missing receipt is an incomplete captured dependency, not an empty receipt.
        missing=dataclasses.replace(c,run_files=tuple((k,v) for k,v in c.run_files if k!='receipt.json'))
        result=self.run_check(missing,b);self.assertNotEqual(result['captured_graph_status'],'consistent_captured_graph')

    def test_05_unsupported_locators_role_collisions_and_pin_shapes(self):
        c,b=base()
        for name in ('journal.jsonl','../result.jsonl','D:/escape','execution\\child\\result.jsonl','receipt.json/','RECEIPT.JSON','after-seal-failure.json '):
            result=self.run_check(dataclasses.replace(c,run_files=c.run_files+((name,b''),)),b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph')
        result=self.run_check(dataclasses.replace(c,run_files=c.run_files+(c.run_files[0],)),b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph')
        alias=dataclasses.replace(b,static_software_pins=b.static_software_pins+(dataclasses.replace(b.dynamic_pins[0].pin,path=b.dynamic_pins[0].pin.path.swapcase()),))
        self.assertEqual(self.run_check(c,alias)['captured_graph_status'],'inconsistent_captured_graph')
        malformed=dataclasses.replace(b,protocol_pin=dataclasses.replace(b.protocol_pin,bytes=True))
        self.assertEqual(self.run_check(c,malformed)['captured_graph_status'],'inconsistent_captured_graph')

    def test_06_caps_are_admitted_before_hash_and_bounded_parse(self):
        c,b=base()
        with self.assertRaises(ValueError):M.CapturedArchive(c.protocol_bytes,c.authority_bytes,tuple(('stdout.bin',b'') for _ in range(65)))
        too_big=dataclasses.replace(c,run_files=(('stdout.bin',b'0'*16777217),('stderr.bin',b'0'*16777217)))
        result=self.run_check(too_big,b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph');self.assertIn('total_captured_byte_cap',result['issues'])
        for name,raw in [('stdout.bin',b'x'*65537),('execution/child/attempt.json',b'x'*65537),('parent-report.json',b'x'*4194305)]:
            result=self.run_check(replace_file(c,name,raw),b);self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph');self.assertTrue(any('captured_leaf_byte_cap' in x for x in result['issues']))

    def test_07_required_deadline_callback_propagates_at_all_boundaries(self):
        c,b=base();calls=[0]
        def count():calls[0]+=1
        M.check_archive(c,b,check=count);self.assertGreater(calls[0],100)
        for threshold in (1,8,40,calls[0]//2,calls[0]-1,calls[0]):
            marker=KeyboardInterrupt('synthetic owner cutoff');seen=[0]
            def cutoff():
                seen[0]+=1
                if seen[0]==threshold:raise marker
            try:M.check_archive(c,b,check=cutoff)
            except BaseException as error:self.assertIs(error,marker)
            else:self.fail('Deadline converted into a graph result')
        with self.assertRaises(TypeError):M.check_archive(c,b,check=None)
        with self.assertRaises(TypeError):M.check_archive({},b,check=lambda:None)

    def test_08_ordinary_immutability_and_fresh_serialization(self):
        c,b=base();r=M.check_archive(c,b,check=lambda:None)
        with self.assertRaises(dataclasses.FrozenInstanceError):c.protocol_bytes=b'changed'
        with self.assertRaises(dataclasses.FrozenInstanceError):b.protocol_pin.bytes=2
        with self.assertRaises(TypeError):r._data['node_digests']['receipt.json']['bytes']=0
        copy1=r.to_dict();copy1['node_digests']['receipt.json']['bytes']=0;copy1['failure_vetoes'].append('forged')
        copy2=r.to_dict();self.assertNotEqual(copy2['node_digests']['receipt.json']['bytes'],0);self.assertNotIn('forged',copy2['failure_vetoes'])
        self.assertFalse(r.profile_qualified);self.assertFalse(r.source_qualified);self.assertFalse(r.actual_directory_complete);self.assertFalse(r.originals_authenticated)

    def test_09_source_scope_no_filesystem_or_API(self):
        c,b=base()
        with mock.patch('builtins.open',side_effect=AssertionError('Pure checker must not open named paths')):
            self.assertEqual(M.check_archive(c,b,check=lambda:None).to_dict()['captured_graph_status'],'consistent_captured_graph')
        imports=[]
        for node in ast.walk(ast.parse(SOURCE.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(imports,['dataclasses','datetime','hashlib','json','math','re','types'])

    def test_10_before_witness_callback_and_marker_framing_regressions(self):
        c,b=base();total=[0]
        def counter():total[0]+=1
        M.check_archive(c,b,check=counter)
        for exception in (ValueError,UnicodeError,RecursionError,RuntimeError,KeyboardInterrupt,SystemExit,M._Bad):
            for threshold in (1,8,60,total[0]//2,total[0]):
                seen=[0];marker=exception('synthetic callback identity')
                def stop():
                    seen[0]+=1
                    if seen[0]==threshold:raise marker
                try:M.check_archive(c,b,check=stop)
                except BaseException as error:self.assertIs(error,marker);self.assertEqual(seen[0],threshold)
                else:self.fail('One-shot callback swallowed')
        files=dict(c.run_files);files['execution/child/attempt.json']+=b'\n'
        def metadata(raw):return dict(bytes=len(raw),sha256=sha(raw))
        def anchored(name):return dict(path=b.run_root+'\\'+name.replace('/','\\'),**metadata(files[name]))
        receipt=json.loads(files['receipt.json']);receipt['outputs']={key:metadata(files[key]) for key in receipt['outputs']};files['receipt.json']=docs(receipt)
        cleanup=json.loads(files['post-lease-cleanup.json']);cleanup['earlier_receipt']=anchored('receipt.json');files['post-lease-cleanup.json']=docs(cleanup)
        seal=json.loads(files['terminal-seal.json']);seal['earlier_receipt']=anchored('receipt.json');seal['cleanup_artifact']=anchored('post-lease-cleanup.json');seal['outputs']={key:metadata(files[key]) for key in seal['outputs']};files['terminal-seal.json']=docs(seal)
        result=self.run_check(dataclasses.replace(c,run_files=tuple(files.items())),b)
        self.assertEqual(result['captured_graph_status'],'inconsistent_captured_graph');self.assertTrue(any('JSON_LF_or_BOM:execution/child/attempt.json' in x for x in result['issues']))

    def test_11_source_nullable_already_closed_before_and_after(self):
        c,b=base();files=dict(c.run_files);cleanup=json.loads(files['post-lease-cleanup.json'])
        source_state=dict(closed_before=True,close_attempted=False,close_return_observed=False,close_success=None,close_error=None,closed_after=True)
        cleanup['outcomes'][0].update(source_state);files['post-lease-cleanup.json']=docs(cleanup)
        candidate,binding=rebound(c,b,files)
        old=OLD.check_archive(*legacy(candidate,binding),check=lambda:None).to_dict()
        new=self.run_check(candidate,binding)
        self.assertEqual(old['captured_graph_status'],'inconsistent_captured_graph');self.assertIn('cleanup_outcome_bool',old['issues'])
        self.assertEqual(new['captured_graph_status'],'consistent_captured_graph');self.assertEqual(new['source_terminal_disposition'],'source_positive_observations_pending')
        REGRESSIONS.append(dict(id='already_closed_source_null',before=old,after=new,source_outcome=source_state))
        for key,value in [('closed_before',False),('close_attempted',True),('close_return_observed',True),('closed_after',False),('close_error',{'error_class':'RuntimeError','error':'synthetic'})]:
            variant=json.loads(files['post-lease-cleanup.json']);variant['outcomes'][0][key]=value
            changed=dict(files);changed['post-lease-cleanup.json']=docs(variant)
            bad_c,bad_b=rebound(c,b,changed);actual=self.run_check(bad_c,bad_b)
            self.assertEqual(actual['captured_graph_status'],'inconsistent_captured_graph',key)
            self.assertIn('cleanup_unattempted_close_null',actual['issues'])
        for value in (0,1,'null'):
            variant=json.loads(files['post-lease-cleanup.json']);variant['outcomes'][0]['close_success']=value
            changed=dict(files);changed['post-lease-cleanup.json']=docs(variant)
            bad_c,bad_b=rebound(c,b,changed)
            self.assertEqual(self.run_check(bad_c,bad_b)['captured_graph_status'],'inconsistent_captured_graph')

    def test_12_numeric_boundary_before_after_and_exact_types(self):
        c,b=base();config=json.loads(c.protocol_bytes);config['periodic_job_seconds']=10**1000
        candidate,binding=rebound(c,b,dict(c.run_files),protocol=config)
        with self.assertRaises(OverflowError) as before:
            OLD.check_archive(*legacy(candidate,binding),check=lambda:None)
        after=self.run_check(candidate,binding)
        self.assertEqual(after['captured_graph_status'],'inconsistent_captured_graph')
        self.assertIn('configuration_periodic_interval',after['issues'])
        REGRESSIONS.append(dict(id='1001_digit_periodic_interval',before_exception=type(before.exception).__name__,after=after,
            protocol_bytes=len(candidate.protocol_bytes),synthetic_protocol_sha256=sha(candidate.protocol_bytes),dependent_maps_rebound=True))
        for value in (True,False,0,-1,121,10**1000,-10**1000,'3.5',None):
            mutated=dict(config);mutated['periodic_job_seconds']=value
            candidate,binding=rebound(c,b,dict(c.run_files),protocol=mutated)
            actual=self.run_check(candidate,binding)
            self.assertEqual(actual['captured_graph_status'],'inconsistent_captured_graph',repr(value)[:32])
            self.assertIn('configuration_periodic_interval',actual['issues'])
        for value in (1,3.5,120):
            mutated=dict(config);mutated['periodic_job_seconds']=value
            candidate,binding=rebound(c,b,dict(c.run_files),protocol=mutated)
            self.assertEqual(self.run_check(candidate,binding)['captured_graph_status'],'consistent_captured_graph')
        self.assertTrue(M._number(10**1000));self.assertFalse(M._number(-10**1000))
        for value in (True,False,float('nan'),float('inf'),-float('inf')):self.assertFalse(M._number(value))

    def test_13_callback_OverflowError_is_not_numeric_data_failure(self):
        c,b=base();total=[0]
        def count():total[0]+=1
        M.check_archive(c,b,check=count)
        for target in (1,8,60,total[0]//2,total[0]):
            marker=OverflowError('synthetic callback identity');calls=[0]
            def stop():
                calls[0]+=1
                if calls[0]==target:raise marker
            try:M.check_archive(c,b,check=stop)
            except BaseException as error:self.assertIs(error,marker);self.assertEqual(calls[0],target)
            else:self.fail('Callback OverflowError converted into data failure')
        marker=OverflowError('synthetic JSON callback identity');fired=[False]
        def inside_JSON():
            frame=sys._getframe(2)
            if not fired[0] and frame.f_code.co_name=='json' and 'value' in frame.f_locals:
                fired[0]=True;raise marker
        try:M.check_archive(c,b,check=inside_JSON)
        except BaseException as error:self.assertIs(error,marker)
        else:self.fail('JSON-region callback OverflowError swallowed')
        self.assertTrue(fired[0])

def main():
    global M,OLD,CASES
    start=time.monotonic();assert not PROOF.exists(),'Preserve first implementation check'
    paths=[SOURCE,CONTRACT,FIXTURES,HERE/'CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json',HERE/'ARCHIVE-CHECKER-SOURCE-ROOT-DECISION-v1.json',
        HERE/'ARCHIVE-CHECKER-CORRECTION-ROOT-DECISION-v3.json',HERE/'captured_archive_v2.py',
        HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json',HERE/'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json',
        HERE/'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PROBES-v3.json']
    before={p.name:pin(p) for p in paths}
    assert before[CONTRACT.name]['sha256']=='ce077d5bfd2e12bd5de7a84d17094572a15286e0cb44bdc224513206f305e3d2'
    assert before[FIXTURES.name]['sha256']=='3e75447d4d3a01c56833d089bf23dab52e5e53bc49a9ea33e9de689eef9b5dcd'
    CASES=json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
    spec=importlib.util.spec_from_file_location('captured_archive_under_test',SOURCE);M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
    oldspec=importlib.util.spec_from_file_location('captured_archive_preserved_v2',HERE/'captured_archive_v2.py');OLD=importlib.util.module_from_spec(oldspec);sys.modules[oldspec.name]=OLD;oldspec.loader.exec_module(OLD)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    stable=before=={p.name:pin(p) for p in paths}
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() and stable else 'failed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=before,
        checker=pin(Path(__file__)),methods=result.testsRun,frozen_case_results=OBS,focused_before_after=REGRESSIONS,
        failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],
        elapsed_seconds=time.monotonic()-start,inputs_unchanged=stable,profile_qualified=False,originals_authenticated=False,actual_directory_complete=False,source_qualified=False,
        actual_old_archive_capture_or_replay=False,SDK_OS_native_model_operations=0,CPU_GGUF_oldpack_reads=0,
        preserved_v1_source=pin(HERE/'captured_archive_v1.py'),preserved_v1_proof=pin(HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v1.json'),
        before_regressions=pin(HERE/'CAPTURED-NATIVE-ARCHIVE-SELF-REVIEW-BEFORE-v2.json'),
        correction_scope='Only source-valid unattempted already-closed close_success null and noncoercing exact integer/float finite-number predicate. v2 callback/LF fixes preserved. Full cleanup/resource qualification stays delegated.',
        scope='Only frozen synthetic source-format captures. Graph/conditional maps/declarations are checked; actual originals/directory/owner/wholechain/resources/profile remain unqualified.')
    with PROOF.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=proof['status'],methods=result.testsRun,frozen_cases=len(OBS))))
    return 0 if proof['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
