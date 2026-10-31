"""Pure fake-API IOCP bounds/ownership/orchestration; no real SDK/child."""
import ast
import hashlib
from importlib import util
import json
from pathlib import Path
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"diagnose_native_job_iocp_v1.py"
spec=util.spec_from_file_location("own_iocp_pure",SOURCE)
d=util.module_from_spec(spec);spec.loader.exec_module(d)
sdk=d.sdk
denied=[]
def guard(event,args):
    if event in ("ctypes.dlopen","subprocess.Popen","os.system","socket.__new__","socket.connect","socket.getaddrinfo"):
        denied.append(event);raise RuntimeError("No real operation during pure checks")
sys.addaudithook(guard)
ROOT=d.ROOT/"data/cache"/("r09-native-job-iocp-pure-"+str(time.time_ns()));ROOT.mkdir()


def snapshot(total=0,active=0,pids=()):
    a,p=sdk.ACCOUNTING(),sdk.PID_LIST();a.TotalProcesses=total;a.ActiveProcesses=active
    p.NumberOfAssignedProcesses=p.NumberOfProcessIdsInList=len(pids)
    for i,pid in enumerate(pids):p.ProcessIdList[i]=pid
    return dict(query_started_monotonic_ns=1,query_finished_monotonic_ns=2,
        accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=bytes(a).hex(),decoded={n:int(getattr(a,n)) for n,_ in a._fields_}),
        pid_list=dict(ok=True,error=0,returned_bytes=136,raw_hex=bytes(p).hex(),assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))


def packet(message=6,pid=20,ok=True,key=d.COMPLETION_KEY,error=None):
    return dict(started_monotonic_ns=1,finished_monotonic_ns=2,ok=ok,error=error,
                raw_number_of_bytes=message,raw_completion_key=key,raw_overlapped_value=pid)


class MemoryJournal:
    def __init__(self):self.rows=[]
    def append(self,name,**details):self.rows.append((name,json.loads(json.dumps(details))))


class FakeApi:
    def __init__(self,config=None,expected="a"*64,counter=1,held_effect=False,setup_fail=False,terminate_ok=True,recheck_fail=False):
        self.config,self.expected=config,expected;self.counter=counter;self.held_effect=held_effect
        self.setup_fail,self.terminate_ok,self.recheck_fail=setup_fail,terminate_ok,recheck_fail
        self.closed=[];self.events=[];self.next_lease=100;self.observer=None;self.queue=[]
        self.assigned=False;self.dead=False;self.queries=0;self.opened=[];self.close_attempts={};self.failed_once=False
    def create_job(self):self.events.append("create_job");return 10
    def configure_job(self,job):self.events.append("configure_job");self.observer.setup_job(job)
    def create_port(self,observer):observer.port=40;observer.port_create=dict(ok=True,handle=40,registered_before_other_calls=True)
    def associate_port(self,job,port):return dict(ok=not self.setup_fail,error=5 if self.setup_fail else None,job=job,port=port,key=d.COMPLETION_KEY)
    def verify_limits(self,job):return dict(flags=sdk.JOB_FLAGS,active_limit=1,process_commit=268435456,job_commit=268435456)
    def job_snapshot(self,job):
        self.events.append("snapshot")
        if not self.assigned:return snapshot()
        if not self.dead:return snapshot(1,1,[20])
        active=1 if self.held_effect and self.observer.outstanding() else 0
        return snapshot(self.counter,active,[20] if active else [])
    def make_stdio(self,owned):owned.update(stdin=11,stdout_read=12,stdout_write=13,stderr_read=14,stderr_write=15)
    def create_suspended(self,argv,command,environment,cwd,owned,pi,job,creation,event):
        self.events.append("create_suspended");self.child=Path(argv[2]);self.streams={12:b"",14:b""}
        event("abi_CreateProcessW_reserved",attribute_count=2,attribute_keys=[sdk.HANDLE_LIST_ATTRIBUTE,sdk.JOB_LIST_ATTRIBUTE])
        creation.update(api_attempt_reserved=True,return_observed=True,returned_success=True)
        pi.hProcess,pi.hThread,pi.dwProcessId,pi.dwThreadId=21,22,20,23;self.assigned=True;self.queue.append(packet())
    def in_job(self,job,process):return True
    def identity(self,pi,exe):return dict(pid=20,image=str(exe),synthetic=True)
    def resume(self,thread):
        self.events.append("resume");self.streams[12]=b"x"*73728
        d.write_new(self.child/"worker-started.json",dict(pid=20,mode="overflow",executable=str(d.q.OWN_EXE),protocol_sha256=self.expected))
        return 1
    def queue_call(self,port):
        return self.queue.pop(0) if self.queue else packet(999,0,False,123,258)
    def open_reported(self,pid,row):
        self.opened.append(pid);row.update(open_attempted=True,open_ok=True,open_error=None,handle=2000+pid,
            closed=False,handle_registered_immediately=True,open_started_monotonic_ns=1,open_finished_monotonic_ns=2)
    def query_reported(self,handle,pid,job,outcomes=None):
        rows=[] if outcomes is None else outcomes
        names=("GetProcessId","QueryFullProcessImageNameW","IsProcessInJob_exact_job","WaitForSingleObject_0","GetProcessTimes")
        for name in names:
            rows.append(dict(query=name,ok=True,error=None,output_defined=True,started_monotonic_ns=1,finished_monotonic_ns=2,
                raw_output=dict(job=job,is_member=True) if name==names[2] else pid if name==names[0] else 258,
                matches_reported_pid=True if name==names[0] else None))
        return rows
    def observed_terminate(self,job):
        self.events.append("observed_terminate");self.dead=True;self.queue.extend([packet(7),packet(4,0)])
        return dict(attempted=True,return_observed=True,ok=self.terminate_ok,error=None if self.terminate_ok else 5)
    def terminate_job(self,job):self.events.append("cleanup_terminate_job");self.dead=True
    def terminate_process(self,process):self.events.append("cleanup_terminate_process");self.dead=True
    def wait(self,process,ms):return self.dead
    def exit_code(self,process):return 125
    def available(self,handle):return len(self.streams[handle]) if self.streams[handle] else None
    def read(self,handle,count):value=self.streams[handle][:count];self.streams[handle]=self.streams[handle][count:];return value
    def close(self,handle):
        self.close_attempts[handle]=self.close_attempts.get(handle,0)+1
        if self.recheck_fail and handle==100+len(self.config["inputs"])+2 and not self.failed_once:
            self.failed_once=True;raise OSError("Injected recheck close failure")
        self.closed.append(handle);self.events.append("close_"+str(handle))
    def read_lease(self,item,deadline,ownership):
        assert d.pin(item["path"])==item
        row=dict(path=item["path"],handle=self.next_lease,closed=False,validation="passed",cleanup_errors=[])
        self.next_lease+=1;ownership.append(row);return row


def config(name):
    paths=(SOURCE,d.BASIS,d.q.SDK_SOURCE,d.q.WORKER,d.q.SOURCE_COPY,d.q.OWN_EXE,d.q.BUILD_VERIFICATION,
           d.SEALER,d.CONTRACT,d.DESIGN,*d.q.SYSTEM_DLL_PINS)
    return d.configuration(ROOT/name,[d.pin(path) for path in paths])


class PureChecks(unittest.TestCase):
    def observer(self,packets=()):
        api=FakeApi();api.queue=list(packets);journal=MemoryJournal()
        observer=d.Observer(api,journal,time.monotonic()+20);observer.port=40;observer.job=10;api.observer=observer
        return observer,api,journal
    def full_fake(self,name,**options):
        c=config(name);c["pure_fixture"]=True;protocol=ROOT/(name+"-protocol.json")
        protocol.write_bytes(d.canonical(c)+b"\n");expected=d.sha(protocol);api=FakeApi(c,expected,**options)
        with patch.object(d,"PROTOCOL",protocol),patch.object(d,"api_class",return_value=lambda *_:api):result=d.execute(c,expected)
        return c,api,result
    def test_layout_and_exact_three_binding_delta(self):
        d.observer_layouts();self.assertFalse(sdk.NATIVE_EXECUTION_ENABLED)
        def specs(path,cls):
            node=next(n for n in ast.walk(ast.parse(path.read_bytes())) if isinstance(n,ast.ClassDef) and n.name==cls)
            return next(n.value for n in ast.walk(node) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="specs" for t in n.targets))
        a,b=specs(d.BASIS,"HarmlessKernel32"),specs(SOURCE,"DiagnosticKernel32")
        aa={key.value:ast.dump(value,include_attributes=False) for key,value in zip(a.keys,a.values)}
        bb={key.value:ast.dump(value,include_attributes=False) for key,value in zip(b.keys,b.values)}
        self.assertEqual(set(bb)-set(aa),{"CreateIoCompletionPort","GetQueuedCompletionStatus","OpenProcess"})
        self.assertTrue(all(bb[k]==v for k,v in aa.items()))
    def test_exact_role_overflow_only_and_five_args(self):
        c=config("role");argv,command,env=d.launch_argv(c,"a"*64)
        self.assertEqual(len(argv),5);self.assertEqual(argv[:2],[str(d.q.OWN_EXE),"overflow"])
        c["cases"].append(dict(worker_mode="sleep",child_output="unused"))
        with self.assertRaises(RuntimeError):d.validate_role(c)
    def test_empty_outputs_undefined_and_null_nonpid_no_open(self):
        o,a,j=self.observer([packet(3,0),packet(4,0)]);o.drain("test")
        self.assertEqual(a.opened,[]);self.assertFalse(o.calls[-1]["number_and_key_defined"])
        self.assertEqual(o.calls[-1]["raw_number_of_bytes"],999)
    def test_wrong_key_failed_io_unknown_and_unusable_pid(self):
        for row in (packet(key=1),packet(ok=False,error=5),packet(999,0)):
            o,a,j=self.observer([row])
            with self.assertRaises(RuntimeError):o.drain("test")
            self.assertEqual(a.opened,[]);self.assertEqual(len(o.calls),1)
        o,a,j=self.observer([packet(pid=0),packet(pid=2**40)]);o.drain("test");self.assertEqual(a.opened,[])
    def test_duplicate_pid_once_and_final_drain_no_open(self):
        o,a,j=self.observer([packet(),packet(7)]);o.drain("test")
        self.assertEqual(a.opened,[20]);self.assertEqual(o.pids[20]["all_packet_sequences_within_packet_cap"],[0,1])
        o.close_pids();a.queue=[packet(pid=99)];o.drain("final",allow_open=False)
        self.assertEqual(a.opened,[20]);self.assertEqual(o.pids[99]["not_queried_reason"],"not_queried_terminal_drain")
    def test_packet_pid_call_and_batch_budgets(self):
        o,a,j=self.observer([packet(3,0)]*65)
        with self.assertRaises(RuntimeError):
            while True:o.drain("test")
        self.assertEqual(o.packets,64);self.assertEqual(len(a.queue),1)
        o,a,j=self.observer([packet(pid=i) for i in range(1,18)])
        with self.assertRaises(RuntimeError):
            while True:o.drain("test")
        self.assertEqual(len(a.opened),16);self.assertEqual(len(o.pids),16)
        o,a,j=self.observer();o.calls=[{}]*1023
        with self.assertRaises(RuntimeError):o.drain("test")
        self.assertEqual(len(o.calls),1024)
        o,a,j=self.observer([packet(3,0)]*9);self.assertEqual(o.drain("test"),8);self.assertEqual(len(a.queue),1)
    def test_raw_snapshot_precedes_predicate_and_publication_failure_skips_check(self):
        o,a,j=self.observer();o.owner=SimpleNamespace(job=10,snapshot_count=0,pi=SimpleNamespace(dwProcessId=20))
        with patch.object(sdk,"job_snapshot_problem",side_effect=RuntimeError("checker")):
            with self.assertRaises(RuntimeError):o.record_snapshot("before_terminate","empty",boundary=True)
        self.assertEqual(j.rows[0][0],"iocp_raw_job_snapshot");self.assertTrue(o.snapshots[0]["raw_durable"])
        def fail(*args,**kwargs):raise OSError("publish")
        o,a,j=self.observer();o.owner=SimpleNamespace(job=10,snapshot_count=0,pi=SimpleNamespace(dwProcessId=20));j.append=fail
        with patch.object(sdk,"job_snapshot_problem") as check:
            with self.assertRaises(OSError):o.record_snapshot("before_terminate","empty",boundary=True)
            check.assert_not_called()
    def test_ordinary_single_case_boundaries_and_ordered_cleanup(self):
        c,a,r=self.full_fake("ordinary");case=r["diagnostic"]
        self.assertEqual(r["terminal_status"],"IOCP_diagnostic_observations_retained_not_qualification")
        self.assertTrue(case["diagnostic_completeness"]);self.assertTrue(r["no_qualification_established"])
        self.assertEqual(set(case["stop_boundary_snapshot_references"]),set(d.BOUNDARIES))
        self.assertLess(a.events.index("close_2020"),a.events.index("close_21"));self.assertLess(a.events.index("close_10"),a.events.index("close_40"))
        from asof.journal import read_chain
        events=read_chain(Path(c["output"])/"execution/journal.jsonl")
        reservation=next(i for i,x in enumerate(events) if x["event"]=="iocp_owned_job_termination_reserved")
        self.assertEqual(events[reservation-1]["event"],"iocp_snapshot_predicate_evaluated")
    def test_counter_finding_negative_with_held_released_raw_unchanged(self):
        c,a,r=self.full_fake("counter",counter=2,held_effect=True);case=r["diagnostic"]
        self.assertEqual(r["terminal_status"],"failed");self.assertTrue(case["diagnostic_completeness"])
        rows={x["stage"]:x for x in case["raw_snapshots"]}
        held=rows[d.BOUNDARIES[2]]["raw_sdk_snapshot"]["accounting"]["decoded"]
        released=rows[d.BOUNDARIES[3]]["raw_sdk_snapshot"]["accounting"]["decoded"]
        self.assertEqual((held["TotalProcesses"],held["ActiveProcesses"]),(2,1))
        self.assertEqual((released["TotalProcesses"],released["ActiveProcesses"]),(2,0))
    def test_failed_terminate_with_coincident125_cannot_complete(self):
        c,a,r=self.full_fake("bad-stop",terminate_ok=False)
        self.assertEqual(r["diagnostic"]["owned_exit_code"],125);self.assertFalse(r["diagnostic"]["diagnostic_completeness"])
        self.assertEqual(r["terminal_status"],"failed")
    def test_setup_failure_prevents_creation_but_closes_port_and_job(self):
        c,a,r=self.full_fake("setup",setup_fail=True)
        self.assertNotIn("create_suspended",a.events);self.assertIn("close_10",a.events);self.assertIn("close_40",a.events)
        self.assertEqual(r["terminal_status"],"failed")
    def test_primary_plus_recheck_close_failure_retained_after_successful_retry(self):
        c,a,r=self.full_fake("recheck",counter=2,recheck_fail=True)
        self.assertTrue(r["finalization_errors"]);self.assertTrue(a.failed_once);self.assertEqual(r["terminal_status"],"failed")
        failed=[x for x in r["lease_ownership"] if x["cleanup_errors"]]
        self.assertEqual(len(failed),1);self.assertTrue(failed[0]["closed"]);self.assertEqual(a.close_attempts[failed[0]["handle"]],2)


if __name__=="__main__":
    results=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureChecks))
    report=dict(schema_version=1,status="passed" if results.wasSuccessful() else "failed",helper_sha256=d.sha(SOURCE),
        checker_sha256=d.sha(__file__),tests=results.testsRun,failures=len(results.failures),errors=len(results.errors),
        actual_children=0,real_sdk_constructions=0,denied_real_operations=denied,output=str(ROOT),
        scope="Synthetic queue/SDK/worker/timers with real accepted journals and role-specific terminal sealing")
    with (HERE/"NATIVE-JOB-IOCP-PURE-CHECKS-v1.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if results.wasSuccessful() else 1)
