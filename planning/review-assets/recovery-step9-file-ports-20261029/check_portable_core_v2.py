"""Behavioral portable ownership tests with synthetic bytes/API/clock only."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'portable_file_ports_v2.py'
PROOF=HERE/'PORTABLE-FILE-PORTS-CORE-PURE-PROOF-v2.json'
s=importlib.util.spec_from_file_location('ports_core_v2',SOURCE);p=importlib.util.module_from_spec(s);sys.modules[s.name]=p;s.loader.exec_module(p)

def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

class Rig:
    def __init__(self,seed=(),assume=True):
        self.now=0;self.calls=[];self.overrides={};self.hooks={};self.paths={101:r'D:\Fixture\input.bin',201:r'D:\Fixture\output\receipt.json'};self.written=[];self.read_offset=0
        self.spec=p.FileSpec(r'D:\Fixture\input.bin',3,hashlib.sha256(b'abc').hexdigest())
        def build(origin):
            owner=p.PortableOwner(origin,self.api,self.hook,files=(self.spec,),output=r'D:\Fixture\output')
            slots=tuple((i,k,h,self.spec if k=='original_file' else None) for i,k,h in seed)
            owner.seed_for_tests(namespace_owned=True,reservation_ready=True,slots=slots)
            if assume:
                for identity,kind,_,_ in slots:
                    if kind in ('original_file','output_file'):owner.assume_seed_identity_for_tests(identity)
            return owner
        self.owner=p.begin_injected(lambda:self.now,build)
    @staticmethod
    def raw(value,count=None,buffer=b'',defined=False):return p.RawReturn(value,0,False,count,count is not None,buffer,defined)
    def api(self,name,args):
        self.calls.append((name,dict(args)))
        if name in self.overrides:return self.overrides[name](args)
        if name=='CreateFileW':
            h=101 if args['desired_access']==2147483648 else 201;self.paths[h]=args['path'];return self.raw(h)
        if name=='GetFileType':return self.raw(1)
        if name=='GetFileInformationByHandleEx':return self.raw(1,buffer=bytes(8),defined=True)
        if name=='GetFinalPathNameByHandleW':
            value='\\\\?\\'+self.paths[args['handle']];units=value.encode('utf-16-le');return self.raw(len(units)//2,buffer=(units+b'\0\0').ljust(8202,b'\0'),defined=True)
        if name=='GetFileSizeEx':return self.raw(1,buffer=(3 if args['handle']==101 else 0).to_bytes(8,'little',signed=True),defined=True)
        if name=='ReadFile':
            b=b'abc'[self.read_offset:self.read_offset+args['requested']];self.read_offset+=len(b);return self.raw(1,len(b),b,True)
        if name=='WriteFile':
            b=bytes.fromhex(args['data_hex']);self.written.append(b);return self.raw(1,len(b))
        if name in ('FlushFileBuffers','CloseHandle','FindClose'):return self.raw(1)
        raise AssertionError(name)
    def hook(self,name):
        if name in self.hooks:self.hooks[name]()
    def run(self,action):return self.owner.run(action).to_dict()
    def names(self):return [n for n,_ in self.calls]

class Checks(unittest.TestCase):
    def test_caught_failed_original_identity_blocks_content(self):
        r=Rig();r.overrides['GetFileType']=lambda a:r.raw(3)
        def action(o):
            try:o.open_original(r.spec)
            except p.PortError:pass
            o.hash_capture('o0')
        out=r.run(action);self.assertEqual(out['primary'],'four_query_identity_required');self.assertNotIn('ReadFile',r.names());self.assertEqual(r.names().count('CloseHandle'),1)
    def test_caught_failed_output_identity_blocks_content(self):
        r=Rig();r.overrides['GetFileType']=lambda a:r.raw(3)
        def action(o):
            try:o.open_output('receipt.json','w0')
            except p.PortError:pass
            o.write_record('w0',b'ABCD')
        out=r.run(action);self.assertEqual(out['primary'],'four_query_identity_required');self.assertNotIn('WriteFile',r.names());self.assertNotIn('FlushFileBuffers',r.names())
    def test_boolean_or_serialized_identity_cannot_admit_content(self):
        for forged in (None,True,{'identity_ok':True}):
            r=Rig(seed=(('o0','original_file',101),),assume=False);r.owner._slot('o0').identity_ok=True
            r.owner._identities['o0']=forged
            out=r.run(lambda o:o.hash_capture('o0'));self.assertEqual(out['primary'],'four_query_identity_required');self.assertNotIn('ReadFile',r.names())
    def test_foreign_owner_witness_rejected(self):
        a=Rig();a.owner.open_original(a.spec);w=a.owner._identities['o0'];b=Rig(seed=(('o0','original_file',101),),assume=False);b.owner._identities['o0']=w
        out=b.run(lambda o:o.hash_capture('o0'));self.assertEqual(out['primary'],'four_query_identity_required');self.assertNotIn('ReadFile',b.names());a.run(lambda o:None)
    def test_four_queries_then_real_hash_copy(self):
        r=Rig();out=r.run(lambda o:(o.open_original(r.spec),o.hash_capture('o0')))
        self.assertEqual(r.names(),['CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle'])
        self.assertEqual((out['known_read_bytes'],out['hashed_bytes'],out['captured_bytes']),(3,3,3));self.assertEqual(bytes(r.owner._slot('o0').capture),b'abc')
    def test_output_pin_uses_actual_written_hash_and_known_close(self):
        r=Rig();pins=[]
        def action(o):o.open_output('receipt.json','w0');o.write_record('w0',b'ABCD');o.close_slot('w0');pins.append(o.output_pin('w0'))
        out=r.run(action);self.assertEqual(dict(pins[0]),dict(path=r'D:\Fixture\output\receipt.json',bytes=4,sha256=hashlib.sha256(b'ABCD').hexdigest()));self.assertEqual(out['known_write_bytes'],4);self.assertEqual(r.names().count('CloseHandle'),1)
    def test_harness_assumption_is_bound_frozen_and_not_query_proof(self):
        r=Rig(seed=(('o0','original_file',101),),assume=False);token=r.owner.assume_seed_identity_for_tests('o0')
        with self.assertRaises((AttributeError,TypeError)):token.handle=909
        self.assertFalse(r.owner._slot('o0').identity_ok);self.assertEqual(r.owner._identities,{})
        foreign=Rig(seed=(('o0','original_file',101),),assume=False);foreign.owner._harness_identities['o0']=token
        self.assertEqual(foreign.run(lambda o:o.hash_capture('o0'))['primary'],'four_query_identity_required')
        out=r.run(lambda o:o.hash_capture('o0'));self.assertEqual(out['harness_identity_assumptions'],1);self.assertFalse(out['originals_authenticated'])
    def test_harness_cannot_lift_opened_or_failed_identity(self):
        r=Rig();r.owner.open_original(r.spec)
        with self.assertRaises(p.PortError):r.owner.assume_seed_identity_for_tests('o0')
        r.run(lambda o:None)
        r=Rig();r.overrides['GetFileType']=lambda a:r.raw(3)
        try:r.owner.open_original(r.spec)
        except p.PortError:pass
        with self.assertRaises(p.PortError):r.owner.assume_seed_identity_for_tests('o0')
        r.run(lambda o:None)
    def test_write_nonreturn_preserves_exception_and_unknown_once(self):
        for error in (RuntimeError('write'),KeyboardInterrupt('write'),SystemExit('write')):
            r=Rig(seed=(('w0','output_file',201),));r.overrides['WriteFile']=lambda a,e=error:(_ for _ in ()).throw(e)
            out=r.run(lambda o:o.write_record('w0',b'ABCD'));self.assertTrue(out['write_count_unknown']);self.assertIs(r.owner._primary_object,error);self.assertEqual(out['known_write_bytes'],0);self.assertEqual(r.names(),['WriteFile','CloseHandle'])
    def test_late_write_known_bytes_no_hash_flush_or_guess(self):
        r=Rig(seed=(('w0','output_file',201),))
        def write(a):r.now=301;return r.raw(2,4)
        r.overrides['WriteFile']=write;out=r.run(lambda o:o.write_record('w0',b'ABCD'))
        self.assertEqual((out['known_write_bytes'],out['write_hash_bytes'],out['flushed_known_bytes']),(4,0,0));self.assertFalse(out['write_count_unknown']);self.assertEqual(r.names(),['WriteFile']);self.assertEqual(out['slots'][0]['close_state'],'not_dispatched_deadline')
    def test_no_write_dispatch_means_no_unknown_write_tail(self):
        r=Rig(seed=(('w0','output_file',201),));r.now=300;out=r.run(lambda o:o.write_record('w0',b'ABCD'));self.assertFalse(out['write_count_unknown']);self.assertEqual(r.calls,[])
    def test_no_read_dispatch_means_no_unknown_read_tail(self):
        r=Rig(seed=(('o0','original_file',101),));r.now=295;out=r.run(lambda o:o.hash_capture('o0'));self.assertFalse(out['read_count_unknown']);self.assertEqual(out['api_attempts']['ReadFile'],0);self.assertEqual(r.names(),['CloseHandle'])
        self.assertEqual(r.owner._slot('o0').read_attempts,0);self.assertFalse(r.owner._slot('o0').pending_read)
    def test_entered_malformed_read_count_is_unknown(self):
        for raw in (Rig.raw(True,3,b'abc',True),Rig.raw(1,True,b'abc',True),Rig.raw(1,-1,b'abc',True),Rig.raw(1,4,b'abcd',True),Rig.raw(1,None,b'abc',True),object()):
            r=Rig(seed=(('o0','original_file',101),));r.overrides['ReadFile']=lambda a,value=raw:value
            out=r.run(lambda o:o.hash_capture('o0'));self.assertTrue(out['read_count_unknown']);self.assertEqual(out['known_read_bytes'],0);self.assertEqual(r.names(),['ReadFile','CloseHandle'])
    def test_read_nonreturn_preserves_exception_and_unknown_once(self):
        for error in (RuntimeError('read'),KeyboardInterrupt('read'),SystemExit('read')):
            r=Rig(seed=(('o0','original_file',101),));r.overrides['ReadFile']=lambda a,e=error:(_ for _ in ()).throw(e)
            out=r.run(lambda o:o.hash_capture('o0'));self.assertTrue(out['read_count_unknown']);self.assertIs(r.owner._primary_object,error);self.assertEqual(out['known_read_bytes'],0);self.assertEqual(r.names(),['ReadFile','CloseHandle'])
    def test_late_read_known_bytes_but_no_hash_copy(self):
        r=Rig(seed=(('o0','original_file',101),))
        def read(a):r.now=296;return r.raw(-1,3,b'abc',True)
        r.overrides['ReadFile']=read;out=r.run(lambda o:o.hash_capture('o0'))
        self.assertEqual((out['known_read_bytes'],out['hashed_bytes'],out['captured_bytes']),(3,0,0));self.assertFalse(out['read_count_unknown']);self.assertEqual(r.names(),['ReadFile','CloseHandle'])
    def test_hook_failures_preserve_known_hash_copy_distinction(self):
        for hook,expected in (('hash_update',(3,0,0)),('copy_bytes',(3,3,0))):
            r=Rig(seed=(('o0','original_file',101),));error=RuntimeError(hook);r.hooks[hook]=lambda e=error:(_ for _ in ()).throw(e)
            out=r.run(lambda o:o.hash_capture('o0'));self.assertEqual((out['known_read_bytes'],out['hashed_bytes'],out['captured_bytes']),expected);self.assertIs(r.owner._primary_object,error)
    def test_actual_hash_update_fault_preserves_primary(self):
        r=Rig(seed=(('o0','original_file',101),));error=MemoryError('hash allocation/update');old=p._new_hasher
        class BadHash:
            def update(self,b):raise error
        try:
            p._new_hasher=lambda:BadHash();out=r.run(lambda o:o.hash_capture('o0'))
        finally:p._new_hasher=old
        self.assertIs(r.owner._primary_object,error);self.assertEqual((out['known_read_bytes'],out['hashed_bytes'],out['captured_bytes']),(3,0,0));self.assertTrue(r.owner._slot('o0').hash_pending)
    def test_close_unknown_not_retried_and_primary_retained(self):
        r=Rig(seed=(('w0','output_file',201),));primary=RuntimeError('work');close=KeyboardInterrupt('close')
        r.overrides['CloseHandle']=lambda a:(_ for _ in ()).throw(close)
        out=r.run(lambda o:(_ for _ in ()).throw(primary));self.assertIs(r.owner._primary_object,primary);self.assertEqual(r.names(),['CloseHandle']);self.assertEqual(out['slots'][0]['close_state'],'entered_return_unknown');self.assertEqual(out['secondary'],['close_unknown'])
    def test_snapshot_deep_detachment_and_origin_immutable(self):
        r=Rig(seed=(('w0','output_file',201),));out=r.run(lambda o:None);out['slots'][0]['handle']=999;out['api_attempts']['CloseHandle']=999;out['secondary'].append('foreign')
        again=r.owner.observe().to_dict();self.assertEqual(again['slots'][0]['handle'],201);self.assertEqual(again['api_attempts']['CloseHandle'],1);self.assertEqual(again['secondary'],[])
        with self.assertRaises(TypeError):r.owner.origin._start=123
    def test_signed_noncanonical_BOOL_success_preserved(self):
        for value in (2,-1):
            r=Rig(seed=(('o0','original_file',101),));r.overrides['ReadFile']=lambda a,v=value:r.raw(v,3,b'abc',True);out=r.run(lambda o:o.hash_capture('o0'))
            self.assertEqual(out['known_read_bytes'],3);self.assertEqual(r.owner._slot('o0').raw_reads[0].value,value)
    def test_owner_once_and_no_qualification_lift(self):
        r=Rig();out=r.run(lambda o:None)
        with self.assertRaises(p.PortError):r.owner.run(lambda o:None)
        for key in ('profile_qualified','runtime_authorized','originals_authenticated','terminal_ack','FFI_registration_proven','production_owner_bound'):self.assertIs(out[key],False)

def main():
    assert not PROOF.exists();start=pin(SOURCE);suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks);result=unittest.TestResult();suite.run(result)
    record=dict(schema_version=1,status='PASS' if result.wasSuccessful() else 'FAIL_PRESERVED',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=start,checker=pin(Path(__file__)),tests=result.testsRun,
        failures=[dict(test=str(t),trace=trace) for t,trace in result.failures],errors=[dict(test=str(t),trace=trace) for t,trace in result.errors],source_unchanged=pin(SOURCE)==start,
        scope='Actual portable source logic on new synthetic bytes/clock/API only. Private fault injection and harness seed assumptions are test-only, never production identity/eligibility.',profile_qualified=False,runtime_authorized=False,actual_API_calls=0)
    with PROOF.open('x',encoding='utf-8') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))))
if __name__=='__main__':main()
