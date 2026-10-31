"""Generic-core controls on synthetic refs/bytes only; no literal fixtures."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'raw_adoption_core_v1.py'
PROOF=HERE/'RAW-ADOPTION-OWNER-CONTROLS-PROOF-v1.json'
s=importlib.util.spec_from_file_location('raw_owner_controls_v1',SOURCE);p=importlib.util.module_from_spec(s);sys.modules[s.name]=p;s.loader.exec_module(p)
def pin(path):
    b=path.read_bytes();return dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def setup(kind='original_file',owned=True,buffer=True):
    f=p.HarnessFactory();r={k:f.ref(t) for k,t in zip(p.Context.__dataclass_fields__,p.CONTEXT_KINDS)};r['early_context']=None
    o=f.owner(p.Context(**r));o.declare_slot('slot',kind,handle=101 if owned else p.UNOBSERVED,closer='FindClose' if kind=='search' else None if kind=='namespace' else 'CloseHandle',identity_ref=f.ref('file_identity') if owned and kind in ('original_file','output_file') else None)
    b=f.ref('buffer')
    if buffer:o.declare_buffer(b,3,b'abc')
    return f,o,b

def read(o,b,ordinal=0,scalar=1,count=3):
    c=o.reserve(ordinal,'ReadFile','slot',3,b);o.invoke(c);o.store_scalar(c,scalar);o.store_count(c,count);return c

class Checks(unittest.TestCase):
    def test_first_scalar_precedes_failed_auxiliary_fold(self):
        f,o,b=setup(owned=False,buffer=False);c=o.reserve(0,'CreateFileW','slot');o.invoke(c);original=p.Owner._fold;error=MemoryError('fold stopped after first store')
        try:
            p.Owner._fold=lambda self,call:(_ for _ in ()).throw(error)
            try:o.store_scalar(c,202)
            except MemoryError as caught:self.assertIs(caught,error);o.raise_exception(c,error,'after_scalar_before_aux')
        finally:p.Owner._fold=original
        snap=o.snapshot().to_dict();self.assertEqual(snap['counters']['known_scalar_returns'],1);self.assertEqual(snap['counters']['portable_wrapper_returns'],0);self.assertFalse(snap['records'][0]['scalar_aux_ack']);self.assertEqual(snap['slots'][0]['close_right'],'available');self.assertIs(o.primary,error)
    def test_incremental_field_fold_and_duplicate_fact_once(self):
        f,o,b=setup();c=o.reserve(0,'ReadFile','slot',3,b);o.invoke(c);o.store_scalar(c,2);o.reconcile(c,o.context.owner)
        self.assertEqual(o.snapshot().to_dict()['records'][0]['count_state'],'pending');o.store_count(c,3);o.store_count(c,3);o.reconcile(c,o.context.owner);o.reconcile(c,o.context.owner)
        d=o.snapshot().to_dict();self.assertEqual(d['known_read_bytes'],3);self.assertEqual(d['counters']['known_count_values'],1);self.assertEqual(d['counters']['unique_reconciled_ordinals'],1);self.assertEqual(c.folded_bytes,3)
    def test_false_zero_is_not_defined_zero(self):
        for scalar,unknown,defined in ((0,True,False),(-1,False,True),(2,False,True)):
            f,o,b=setup();c=read(o,b,scalar=scalar,count=0);o.wrapper_return(c);o.reconcile(c,o.context.owner);d=o.snapshot().to_dict()
            self.assertEqual(d['read_count_unknown'],unknown);self.assertEqual(d['records'][0]['count_defined'],defined);self.assertEqual(d['counters']['known_count_values'],1);self.assertEqual(d['known_read_bytes'],0)
    def test_unobserved_null_and_numeric_zero_not_collapsed(self):
        for value,tag,returns in ((p.UNOBSERVED,'UNOBSERVED',0),(None,'NULL',1),(0,'HANDLE',1)):
            f,o,b=setup(owned=False,buffer=False);c=o.reserve(0,'CreateFileW','slot');o.invoke(c)
            if value is not p.UNOBSERVED:o.store_scalar(c,value)
            d=o.snapshot().to_dict();self.assertEqual(d['records'][0]['raw_scalar']['tag'],tag);self.assertEqual(d['counters']['known_scalar_returns'],returns);self.assertEqual(d['slots'][0]['close_right'],'none')
    def test_malformed_count_and_BOOL_do_not_overwrite_first_fact(self):
        for invalid in (True,-1,2**32):
            f,o,b=setup();c=o.reserve(0,'ReadFile','slot',3,b);o.invoke(c);o.store_scalar(c,1)
            with self.assertRaises(p.AdoptionError):o.store_count(c,invalid)
            self.assertIs(c.raw_count,p.UNOBSERVED);self.assertEqual(o.snapshot().to_dict()['known_read_bytes'],0)
        f,o,b=setup();c=o.reserve(0,'ReadFile','slot',3,b);o.invoke(c)
        with self.assertRaises(p.AdoptionError):o.store_scalar(c,True)
        self.assertIs(c.raw_scalar,p.UNOBSERVED)
    def test_conflicting_second_fact_retains_original(self):
        f,o,b=setup();c=read(o,b)
        with self.assertRaises(p.AdoptionError):o.store_count(c,2)
        self.assertEqual(c.raw_count,3);self.assertEqual(o.snapshot().to_dict()['known_read_bytes'],3)
    def test_close_fact_survives_wrapper_stop_and_cannot_repeat(self):
        f,o,b=setup(buffer=False);c=o.reserve(0,'CloseHandle','slot');o.invoke(c);o.store_scalar(c,-1);error=KeyboardInterrupt('wrapper');o.raise_exception(c,error,'close_wrapper')
        again=o.reserve(1,'CloseHandle','slot')
        with self.assertRaises(p.AdoptionError):o.invoke(again)
        d=o.snapshot().to_dict();self.assertEqual(d['slots'][0]['close_invocations'],1);self.assertIs(d['slots'][0]['close_success'],True);self.assertEqual(d['counters']['FFI_invocations_reserved'],1);self.assertIs(o.primary,error)
    def test_copy_hash_faults_keep_known_raw_bytes(self):
        for component in ('copy','hash'):
            f,o,b=setup();c=read(o,b);o.wrapper_return(c);error=MemoryError(component)
            with self.assertRaises(MemoryError):getattr(o,component)(c,before=lambda:(_ for _ in ()).throw(error))
            d=o.snapshot().to_dict();self.assertEqual(d['known_read_bytes'],3);self.assertEqual(d['captured_bytes'],0);self.assertEqual(d['hashed_bytes'],0);self.assertFalse(d['buffers'][0]['reusable']);self.assertIs(o.primary,error)
    def test_buffer_generation_lifetime_and_real_digest(self):
        f,o,b=setup();c=read(o,b);o.wrapper_return(c);o.copy(c);o.hash(c)
        self.assertEqual(c.copied_bytes,b'abc');self.assertEqual(c.digest,hashlib.sha256(b'abc').hexdigest());o.reuse_buffer(b,1,b'xyz')
        self.assertEqual(c.copied_bytes,b'abc');self.assertEqual(c.digest,hashlib.sha256(b'abc').hexdigest());self.assertEqual(o.snapshot().to_dict()['buffers'][0]['generation'],1)
    def test_reserved_or_failed_buffer_cannot_be_reused(self):
        for stop in (False,True):
            f,o,b=setup();c=o.reserve(0,'ReadFile','slot',3,b)
            if stop:o.invoke(c);o.store_scalar(c,1);o.store_count(c,3);o.raise_exception(c,RuntimeError('stop'),'buffer_copy')
            with self.assertRaises(p.AdoptionError):o.reuse_buffer(b,1,b'xyz')
            snap=o.snapshot().to_dict();self.assertEqual(snap['buffers'][0]['hex'],'616263');self.assertEqual(snap['buffers'][0]['generation'],0)
    def test_no_work_after_cutoff_preserves_prior_raw_facts(self):
        f,o,b=setup();c=read(o,b);o.wrapper_return(c);o.advance(295000000000)
        called=[]
        with self.assertRaises(p.AdoptionError):o.hash(c,before=lambda:called.append(1))
        d=o.snapshot().to_dict();self.assertEqual(called,[]);self.assertEqual(d['known_read_bytes'],3);self.assertEqual(d['hashed_bytes'],0)
    def test_snapshot_containers_and_refs_are_immutable(self):
        f,o,b=setup();c=read(o,b);snap=o.snapshot();d=snap.to_dict();d['records'][0]['raw_count']['value']=909;d['counters']['known_count_values']=909
        self.assertEqual(snap.to_dict()['records'][0]['raw_count']['value'],3);self.assertEqual(o.snapshot().to_dict()['counters']['known_count_values'],1)
        with self.assertRaises(TypeError):o.context.origin.now_ns=1
        with self.assertRaises((TypeError,AttributeError)):o.context.owner.kind='port'
    def test_live_open_slot_cannot_be_overwritten_and_setup_seals(self):
        f,o,b=setup(owned=False,buffer=False);c=o.reserve(0,'CreateFileW','slot');o.invoke(c);o.store_scalar(c,202);o.wrapper_return(c);o.reconcile(c,o.context.owner)
        d=o.reserve(1,'CreateFileW','slot')
        with self.assertRaises(p.AdoptionError):o.invoke(d)
        self.assertEqual(o.snapshot().to_dict()['slots'][0]['handle_fact']['value'],202)
        with self.assertRaises(p.AdoptionError):o.declare_slot('other','original_file',closer='CloseHandle')

def main():
    assert not PROOF.exists();source=pin(SOURCE);suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks);result=unittest.TestResult();suite.run(result)
    r=dict(schema_version=1,status='PASS' if result.wasSuccessful() else 'FAIL_PRESERVED_BEFORE_CORRECTION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=source,checker=pin(Path(__file__)),methods=result.testsRun,
        failures=[dict(test=str(t),trace=trace) for t,trace in result.failures],errors=[dict(test=str(t),trace=trace) for t,trace in result.errors],source_unchanged=source==pin(SOURCE),
        scope='Generic methods on fresh synthetic typed refs/bytes only. No fixture/case/expected read, native FFI, file/API or live engine. Private fold fault injection is solely a first-assignment regression.',
        profile_qualified=False,runtime_authorized=False,actual_API_calls=0)
    with PROOF.open('x',encoding='utf-8') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),methods=result.testsRun,failures=len(result.failures),errors=len(result.errors))))
if __name__=='__main__':main()
