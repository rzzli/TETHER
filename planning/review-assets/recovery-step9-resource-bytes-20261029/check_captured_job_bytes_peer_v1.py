"""Independent pure byte/phase review. No actual Job/API/source-input replay."""
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
SOURCE=HERE/'captured_job_bytes_v1.py'
FIXTURES=HERE/'CAPTURED-JOB-BYTES-FIXTURES-v1.json'
CONTRACT=HERE/'CAPTURED-JOB-BYTES-CONTRACT-v2.json'
PROOF=HERE/'CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json'
SOURCE_SHA='fd655c8bcec6091565492dbaafdd59f0e5d5ce87520d83edc8b94caaa9a7a8bd'
NAMES=('TotalUserTime','TotalKernelTime','ThisPeriodTotalUserTime','ThisPeriodTotalKernelTime','TotalPageFaultCount','TotalProcesses','ActiveProcesses','TotalTerminatedProcesses')
M=None;V=None;COUNTS=dict(literal_captures=0,literal_phases=0,independent_vectors=0)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def capture(values=(0,0,0,0,0,1,1,0),pids=(54321,),returned=None,tail=None):
    a=b''.join(v.to_bytes(8,'little',signed=True) for v in values[:4])+b''.join(v.to_bytes(4,'little') for v in values[4:])
    filler=list(tail or (0,)*(16-len(pids)));assert len(filler)==16-len(pids)
    p=len(pids).to_bytes(4,'little')*2+b''.join(v.to_bytes(8,'little') for v in list(pids)+filler)
    assert len(a)==48 and len(p)==136
    return dict(query_started_monotonic_ns=1,query_finished_monotonic_ns=1,
        accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=a.hex(),decoded=dict(zip(NAMES,values))),
        pid_list=dict(ok=True,error=0,returned_bytes=8+8*len(pids) if returned is None else returned,raw_hex=p.hex(),assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))
def subset(test,actual,expected):
    test.assertIs(type(actual),type(expected))
    if type(expected) is dict:
        for key,value in expected.items():test.assertIn(key,actual);subset(test,actual[key],value)
    elif type(expected) is list:
        test.assertEqual(len(actual),len(expected))
        for a,b in zip(actual,expected):subset(test,a,b)
    else:test.assertEqual(actual,expected)

class Peer(unittest.TestCase):
    def test_frozen_captures_and_phases(self):
        for case in V['captures']:
            with self.subTest(case=case['id']):
                result=M.decode_job_snapshot(case['snapshot']);subset(self,result.to_dict(),case['expected_projection']);COUNTS['literal_captures']+=1
                for phase in case['phase_checks']:
                    observed=M.check_snapshot_phase(result,phase['expected_phase'],phase['own_pid']).to_dict()
                    subset(self,observed,{k:v for k,v in phase.items() if k!='own_pid'});COUNTS['literal_phases']+=1

    def test_explicit_offsets_signed_unsigned_and_endianness(self):
        values=(-2**63,-1,0,2**63-1,2**32-1,1,1,0)
        raw=capture(values);got=M.decode_job_snapshot(raw)
        self.assertEqual(got.accounting.to_dict()['fields'],dict(zip(NAMES,values)))
        self.assertEqual(bytes.fromhex(raw['accounting']['raw_hex'])[32:36],b'\xff'*4)
        self.assertEqual(M.check_snapshot_phase(got,'assigned',54321).status,'matched_selected_source_phase')
        COUNTS['independent_vectors']+=1
        raw['pid_list']['raw_hex']='00000001'+raw['pid_list']['raw_hex'][8:]
        self.assertEqual(M.decode_job_snapshot(raw).pid_list.status,'malformed');COUNTS['independent_vectors']+=1
        pids=tuple([0,1,2**32-1,2**32,2**63,2**64-1]+list(range(10,20)))
        got=M.decode_job_snapshot(capture(pids=pids))
        self.assertTrue(got.raw_complete);self.assertEqual(got.pid_list.to_dict()['fields']['pids'],list(pids))
        self.assertEqual(M.check_snapshot_phase(got,'assigned',54321).status,'counter_or_PID_mismatch');COUNTS['independent_vectors']+=1

    def test_variable_return_lengths_and_nonzero_unused_tail(self):
        for n,lengths in ((0,(8,9,16,136)),(1,(16,17,24,136)),(16,(136,))):
            pids=tuple(range(1,n+1));tail=tuple(2**64-1-i for i in range(16-n))
            for returned in lengths:
                got=M.decode_job_snapshot(capture(pids=pids,returned=returned,tail=tail))
                self.assertTrue(got.raw_complete);self.assertEqual(got.pid_list.to_dict()['fields']['pids'],list(pids));COUNTS['independent_vectors']+=1
        for returned in (0,7,15,137,True):
            got=M.decode_job_snapshot(capture(returned=returned));self.assertFalse(got.raw_complete);self.assertIsNone(got.pid_list.fields);COUNTS['independent_vectors']+=1

    def test_failed_missing_and_source_view_bool_drift(self):
        for which in ('accounting','pid_list'):
            raw=capture();raw[which]['ok']=False;raw[which]['error']=0
            got=M.decode_job_snapshot(raw);self.assertEqual(getattr(got,which).status,'undefined');self.assertIsNone(getattr(got,which).fields)
            self.assertEqual(M.check_snapshot_phase(got,'assigned',54321).status,'unresolved');COUNTS['independent_vectors']+=1
            raw=capture();raw[which]=None;got=M.decode_job_snapshot(raw)
            self.assertIsNone(getattr(got,which));self.assertFalse(got.raw_complete);COUNTS['independent_vectors']+=1
        for field in NAMES:
            raw=capture();raw['accounting']['decoded'][field]=bool(raw['accounting']['decoded'][field]);got=M.decode_job_snapshot(raw)
            self.assertTrue(got.raw_complete);self.assertIs(got.source_views_consistent,False)
            self.assertEqual(M.check_snapshot_phase(got,'assigned',54321).status,'unresolved');COUNTS['independent_vectors']+=1
        for field,value in [('assigned_count',True),('listed_count',True),('pids',[True])]:
            raw=capture();raw['pid_list'][field]=value;got=M.decode_job_snapshot(raw)
            self.assertTrue(got.raw_complete);self.assertIs(got.source_views_consistent,False);COUNTS['independent_vectors']+=1
        self.assertFalse(M.decode_job_snapshot(None).capture_present)

    def test_phase_matrix_nonatomicity_and_typed_boundary(self):
        vectors=[('empty',capture(values=(0,0,0,0,0,0,0,0),pids=()),None,'matched_selected_source_phase'),
            ('assigned',capture(),54321,'matched_selected_source_phase'),('finished',capture(values=(0,0,0,0,0,1,0,0),pids=()),54321,'matched_selected_source_phase'),
            ('running_or_finished',capture(values=(0,0,0,0,0,1,0,0),pids=()),54321,'matched_selected_source_phase'),
            ('assigned',capture(pids=()),54321,'counter_or_PID_mismatch'),
            ('finished',capture(values=(0,0,0,0,0,2,0,0),pids=()),54321,'counter_or_PID_mismatch'),
            ('finished',capture(values=(0,0,0,0,0,1,0,1),pids=()),54321,'counter_or_PID_mismatch')]
        for phase,raw,pid,status in vectors:
            result=M.check_snapshot_phase(M.decode_job_snapshot(raw),phase,pid)
            self.assertEqual(result.status,status);self.assertFalse(result.resource_qualified);self.assertTrue(result.non_atomic_race_possible);COUNTS['independent_vectors']+=1
        for bad in ({'raw_complete':True,'source_views_consistent':True},True,None):
            with self.assertRaises(TypeError):M.check_snapshot_phase(bad,'assigned',54321)
        for pid in (True,False,None,0,-1,2**32):
            with self.assertRaises(ValueError):M.check_snapshot_phase(M.decode_job_snapshot(capture()),'assigned',pid)
        for phase in ('ready','qualified',True):
            with self.assertRaises(ValueError):M.check_snapshot_phase(M.decode_job_snapshot(capture()),phase,54321)

    def test_malformed_bounds_window_independent_channels(self):
        for field,value in [('ok',1),('error',True),('returned_bytes',False),('raw_hex','ff'*200000),('raw_hex','00 '*48),('raw_hex','AB'*48)]:
            raw=capture();raw['accounting'][field]=value;got=M.decode_job_snapshot(raw)
            self.assertEqual(got.accounting.status,'malformed');self.assertEqual(got.pid_list.status,'decoded')
            self.assertIsNone(got.accounting.to_dict()[field]);self.assertLess(len(json.dumps(got.to_dict())),3000);COUNTS['independent_vectors']+=1
        raw=capture();raw['pid_list']['pids']=[123]*10000
        got=M.decode_job_snapshot(raw);self.assertIs(got.source_views_consistent,False);self.assertLess(len(json.dumps(got.to_dict())),3000)
        for start,end in ((True,1),(0,False),(-1,0),(10,9)):
            raw=capture();raw.update(query_started_monotonic_ns=start,query_finished_monotonic_ns=end);got=M.decode_job_snapshot(raw)
            self.assertFalse(got.raw_complete);self.assertIs(got.source_views_consistent,True);self.assertEqual(got.accounting.status,'decoded');COUNTS['independent_vectors']+=1

    def test_deep_detachment_and_no_IO_scope(self):
        raw=capture();before=copy.deepcopy(raw)
        with mock.patch('builtins.open',side_effect=AssertionError('Decoder must not open files')):
            got=M.decode_job_snapshot(raw);phase=M.check_snapshot_phase(got,'assigned',54321)
        self.assertEqual(raw,before)
        with self.assertRaises(dataclasses.FrozenInstanceError):got.capture_present=False
        with self.assertRaises(dataclasses.FrozenInstanceError):got.pid_list.status='qualified'
        exported=got.to_dict();exported['pid_list']['fields']['pids'].clear();exported['accounting']['fields']['ActiveProcesses']=0
        raw['pid_list']['pids'].clear();self.assertEqual(got.pid_list.to_dict()['fields']['pids'],[54321])
        value=phase.to_dict();value['observed_state']['pids'].clear();self.assertEqual(phase.to_dict()['observed_state']['pids'],[54321])
        imports=[]
        for node in ast.walk(ast.parse(SOURCE.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(imports,['dataclasses','re','struct']);self.assertFalse(got.resource_qualified);self.assertFalse(got.atomic_snapshot)

def main():
    global M,V
    start=time.monotonic();assert not PROOF.exists(),'Preserve first peer result'
    before={n:pin(HERE/n) for n in ['captured_job_bytes_v1.py','CAPTURED-JOB-BYTES-CONTRACT-v2.json','CAPTURED-JOB-BYTES-FIXTURES-v1.json','CAPTURED-JOB-BYTES-FIXTURE-FREEZE-v1.json','CAPTURED-JOB-BYTES-PURE-PROOF-v1.json','check_captured_job_bytes_v1.py']}
    assert before['captured_job_bytes_v1.py']['sha256']==SOURCE_SHA
    assert before['CAPTURED-JOB-BYTES-FIXTURES-v1.json']['sha256']=='e7a7668c190995b518983b3de3b573aca0ba9f6208ec531e0cef99b7b5b0e6ec'
    V=json.loads(FIXTURES.read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('independent_job_bytes_under_test',SOURCE);M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Peer))
    stable=before=={n:pin(HERE/n) for n in before};elapsed=time.monotonic()-start
    proof=dict(schema_version=1,status='passed' if result.wasSuccessful() and stable and elapsed<20 else 'failed',inputs=before,
        checker=pin(Path(__file__)),methods=result.testsRun,failures=[dict(test=str(t),traceback=s) for t,s in result.failures],
        errors=[dict(test=str(t),traceback=s) for t,s in result.errors],counts=COUNTS,elapsed_seconds=elapsed,maximum_seconds=20,
        source_pins_unchanged=stable,SDK_OS_native_calls=0,CPU_GGUF_oldpack_operations=0,actual_old_report_replay=False,
        original_source_qualification=False,resource_qualified=False,hostile_Python_security_claim=False,
        scope='Independent frozen literal expectations plus own int.to_bytes offset/extreme/tail/boolean/type vectors; no actual Job, full resource gate or source provenance qualification.')
    with PROOF.open('x',encoding='utf-8') as out:json.dump(proof,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=proof['status'],methods=result.testsRun,counts=COUNTS)))
    return 0 if proof['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
