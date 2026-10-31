"""Pure exact-role and typed fake-read regressions; no WinDLL or payload operation."""
import ctypes as C
from datetime import datetime,timezone
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'recognition_runtime_roles_v1.py'
CONTRACT=HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
REPORT=HERE/'RECOGNITION-RUNTIME-ROLES-PURE-PROOF-v1.json'
spec=util.spec_from_file_location('pure_recognition_roles',SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)
contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
manifest=json.loads((HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json').read_text(encoding='utf-8'))
CPU,SHARDS,PACK=contract['CPU_descriptor'],contract['ordered_shard_descriptors'],manifest['pack']
DENIED=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No real operation in role/fake-read checks')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.gguf','.dll','.pyd')):
        DENIED.append('payload_open');raise AssertionError('No payload open')
sys.addaudithook(guard)

class FakeAPI:
    def __init__(self,body,check,*,fail_read=False,interrupt=False):
        self.body,self.offset,self.calls,self.fail_read,self.interrupt=body,0,[],fail_read,interrupt
        self.k=types.SimpleNamespace(GetFileSizeEx=self.size,ReadFile=self.read)
        self.sdk=types.SimpleNamespace(C=C,LARGE_INTEGER=C.c_longlong,DWORD=C.c_uint32,finite_deadline=check)
    def size(self,handle,size):self.calls.append('size');size._obj.value=len(self.body);return 1
    def read(self,handle,memory,count,got,overlapped):
        self.calls.append('read')
        if self.interrupt:raise KeyboardInterrupt('synthetic interrupted ReadFile')
        block=self.body[self.offset:self.offset+count];self.offset+=len(block)
        C.memmove(memory,block,len(block));got._obj.value=len(block)
        return 0 if self.fail_read else 1
    def win(self,value,message):
        if not value:raise OSError(message)

def run_fake(body,*,check=lambda _:None,fail_read=False,interrupt=False,item=None,event_fail=False):
    item=item or dict(path=r'D:\qualified\software.txt',bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    role=h.validate_record(item,software_records=[item],CPU=CPU,shards=SHARDS,pack=PACK)
    api=FakeAPI(body,check,fail_read=fail_read,interrupt=interrupt);records=[];events=[]
    def event(name,**details):
        events.append(dict(event=name,**details))
        if event_fail:raise OSError('synthetic reservation publication failure')
    try:h.hash_lease(api,api.sdk,7,item,10.0,role=role,records=records,event=event)
    except BaseException as error:return api,records,events,error
    return api,records,events,None

class Checks(unittest.TestCase):
    def test_only_exact_three_model_descriptors_have_large_caps_no_stat_or_open(self):
        with patch('builtins.open',side_effect=AssertionError('No descriptor opens')),patch.object(Path,'stat',side_effect=AssertionError('No descriptor stat')):
            for row in SHARDS:
                result=h.validate_record(row,software_records=[],CPU=CPU,shards=SHARDS,pack=PACK)
                self.assertEqual((result['role'],result['cap']),('model',row['bytes']))
            for field,value in [('path',r'D:\arbitrary.gguf'),('bytes',SHARDS[0]['bytes']+1),('sha256','0'*64),('bytes',True)]:
                bad=dict(SHARDS[0],**{field:value})
                with self.assertRaises(RuntimeError):h.validate_record(bad,software_records=[],CPU=CPU,shards=SHARDS,pack=PACK)
            with self.assertRaisesRegex(RuntimeError,'Software cannot'):
                h.validate_record(SHARDS[0],software_records=[SHARDS[0]],CPU=CPU,shards=SHARDS,pack=PACK)
            small=dict(path=r'D:\unlisted-small.gguf',bytes=4,sha256='0'*64)
            with self.assertRaisesRegex(RuntimeError,'suffix'):h.validate_record(small,software_records=[small],CPU=CPU,shards=SHARDS,pack=PACK)
    def test_role_collisions_and_software_cap_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'collision'):h.validate_record(CPU,software_records=[CPU],CPU=CPU,shards=SHARDS,pack=PACK)
        with self.assertRaisesRegex(RuntimeError,'Exactly three'):h.validate_record(CPU,software_records=[],CPU=CPU,shards=SHARDS[:2],pack=PACK)
        for size in (128*1024**2+1,-1,True):
            bad=dict(path=r'D:\bad.txt',bytes=size,sha256='0'*64)
            with self.assertRaises(RuntimeError):h.validate_record(bad,software_records=[bad],CPU=CPU,shards=SHARDS,pack=PACK)
    def test_small_hash_zero_and_exact_boundaries_are_counted(self):
        for body in (b'',b'a',b'a'*65536,b'a'*65537):
            api,records,events,error=run_fake(body)
            self.assertIsNone(error);self.assertTrue(records[0]['hash_complete'])
            self.assertEqual(records[0]['known_returned_bytes'],len(body))
            self.assertEqual(records[0]['read_attempts'],(len(body)+65535)//65536)
            self.assertEqual(records[0]['read_attempts'],records[0]['read_returns'])
            self.assertEqual([e['event'] for e in events],['recognition_file_hash_reserved','recognition_file_hash_returned'])
    def test_known_late_bytes_accounted_before_post_read_deadline(self):
        calls=[]
        def check(_):
            calls.append(1)
            if len(calls)==4:raise TimeoutError('synthetic post-read cutoff')
        api,records,events,error=run_fake(b'returned-bytes',check=check)
        self.assertIsInstance(error,TimeoutError);self.assertEqual(api.calls,['size','read'])
        self.assertEqual(records[0]['known_returned_bytes'],14);self.assertEqual(records[0]['hash_updated_bytes'],14)
        self.assertTrue(records[0]['last_read_return_observed']);self.assertFalse(records[0]['pending_read'])
        self.assertFalse(records[0]['hash_complete']);self.assertEqual(len(events),1)
    def test_unreturned_or_failed_read_is_unknown_not_zero_proof(self):
        for fail,interrupt in ((True,False),(False,True)):
            api,records,events,error=run_fake(b'unknown',fail_read=fail,interrupt=interrupt)
            self.assertIsNotNone(error);self.assertFalse(records[0]['hash_complete'])
            self.assertEqual(records[0]['read_attempts'],1)
            self.assertEqual(records[0]['read_returns'],0 if interrupt else 1)
            if interrupt:self.assertTrue(records[0]['pending_read'])
            else:self.assertFalse(records[0]['last_count_defined'])
            self.assertEqual(len(events),1)
    def test_publication_and_pre_call_deadline_fail_closed_before_API(self):
        api,records,events,error=run_fake(b'x',event_fail=True)
        self.assertIsInstance(error,OSError);self.assertEqual(api.calls,[]);self.assertEqual(len(records),1)
        def expired(_):raise TimeoutError('pre-call expired')
        api,records,events,error=run_fake(b'x',check=expired)
        self.assertIsInstance(error,TimeoutError);self.assertEqual(api.calls,[])
    def test_runtime_path_requires_finite_current_owner_deadline_before_ancestry(self):
        for deadline in (None,True,float('nan'),float('inf')):
            with patch.object(Path,'lstat',side_effect=AssertionError('No ancestry before finite deadline')):
                with self.assertRaises(RuntimeError):h.runtime_path(SHARDS[0],role=dict(role='model'),deadline=deadline,check=lambda _:None)

if __name__=='__main__':
    assert not REPORT.exists(),'Preserve prior evidence'
    original=hashlib.sha256(SOURCE.read_bytes()).hexdigest();started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==original
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],
        source_sha256=original,source_path=str(SOURCE),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        elapsed_seconds=time.monotonic()-started,recorded_at_utc=datetime.now(timezone.utc).isoformat(),denied_real_operations=DENIED,
        activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,children=0,compiler_calls=0),
        scope='Pure descriptors and fake typed buffer writes; no payload/API access, live lease, OS ownership or runtime qualification')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=str(REPORT),sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest())))
    raise SystemExit(0 if result.wasSuccessful() else 1)
