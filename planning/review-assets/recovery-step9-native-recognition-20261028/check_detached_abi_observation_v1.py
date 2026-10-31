"""Pure fixed ABI parent lifecycle/role faults; no DLL or EXE execution."""
import ast
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"run_detached_abi_observation_v1.py"
spec=util.spec_from_file_location("own_fixed_abi_pure",SOURCE)
p=util.module_from_spec(spec);spec.loader.exec_module(p);sdk=p.sdk
denied=[]
def guard(event,args):
    if event in ("ctypes.dlopen","subprocess.Popen","os.system","socket.__new__","socket.connect","socket.getaddrinfo"):
        denied.append(event);raise RuntimeError("Pure ABI test cannot perform real operation")
sys.addaudithook(guard)
ROOT=p.ROOT/"data/cache"/("r09-fixed-ABI-pure-"+str(time.time_ns()));ROOT.mkdir()


def snapshot(total=0,active=0,pids=()):
    a,b=sdk.ACCOUNTING(),sdk.PID_LIST();a.TotalProcesses=total;a.ActiveProcesses=active
    b.NumberOfAssignedProcesses=b.NumberOfProcessIdsInList=len(pids)
    for i,pid in enumerate(pids):b.ProcessIdList[i]=pid
    return dict(accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=bytes(a).hex(),decoded={k:int(getattr(a,k)) for k,_ in a._fields_}),
        pid_list=dict(ok=True,error=0,returned_bytes=136,raw_hex=bytes(b).hex(),assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))


def valid_child(child):
    c=p.authority();child.mkdir(parents=True,exist_ok=True)
    modules=[dict(name=p.EXE.name,path=str(p.EXE))]+[dict(name=Path(path).name,path=path) for path in p.runtime_pins()]
    modules+=[dict(name=Path(path).name,path=path) for path in list(p.SYSTEM_PINS)[:3]]
    rows=[dict(event=c["child_artifacts"]["result_events"][0],dependency_native_initialization_possible=True),
        dict(event=c["child_artifacts"]["result_events"][1],modules=modules,layouts=c["expected_layouts"]),
        dict(event=c["child_artifacts"]["result_events"][2],version="synthetic-ABI-fixture",defaults=c["expected_defaults"],no_backend_or_model_call_so_far=True),
        dict(event=c["child_artifacts"]["result_events"][3],version_expected_previously_known=False,backend_init_called=False,registry_called=False,
             model_called=False,scope="typed version/defaults observation; independent ABI acceptance pending"),
        dict(event=c["child_artifacts"]["result_events"][4],mode="--abi",elapsed_ms=1,parent_qualification_required=True)]
    (child/"attempt.json").write_bytes(p.canonical(c["child_artifacts"]["exact_attempt_claim"])+b"\n")
    (child/"result.jsonl").write_bytes(b"".join(p.canonical(row)+b"\n" for row in rows))


class FakeApi:
    def __init__(self,config,expected,counter=1,late=False,recheck=False,timeout=False):
        self.config,self.expected=config,expected;self.counter,self.late,self.recheck,self.timeout=counter,late,recheck,timeout
        self.next_lease=100;self.closed=[];self.counts={};self.failed_once=False;self.events=[]
        self.assigned=False;self.dead=False;self.resumed=False
    def create_job(self):return 10
    def configure_job(self,job):pass
    def verify_limits(self,job):return dict(flags=sdk.JOB_FLAGS,active_limit=1,process_commit=268435456,job_commit=268435456)
    def job_snapshot(self,job):return snapshot(self.counter,0) if self.dead else snapshot(1,1,[20]) if self.assigned else snapshot()
    def make_stdio(self,owned):owned.update(stdin=11,stdout_read=12,stdout_write=13,stderr_read=14,stderr_write=15)
    def create_suspended(self,argv,command,environment,cwd,owned,pi,job,creation,event):
        self.child=Path(argv[3]);self.streams={12:b"",14:b""}
        creation.update(api_attempt_reserved=True,return_observed=True,returned_success=True)
        event("abi_CreateProcessW_reserved",attribute_count=2,attribute_keys=[sdk.HANDLE_LIST_ATTRIBUTE,sdk.JOB_LIST_ATTRIBUTE])
        pi.hProcess,pi.hThread,pi.dwProcessId,pi.dwThreadId=21,22,20,23;self.assigned=True;self.events.append("create")
    def in_job(self,job,process):return True
    def identity(self,pi,exe):return dict(pid=20,image=str(exe),synthetic=True)
    def resume(self,thread):
        self.resumed=True;self.events.append("resume");valid_child(self.child)
        self.streams[12]=b'{"status":"child_returned_results_require_parent_review"}\n'
        self.dead=not self.timeout;return 1
    def wait(self,process,ms):
        if self.timeout and self.resumed and not self.dead:raise TimeoutError("Synthetic child deadline")
        return self.dead
    def exit_code(self,process):return 0
    def terminate_job(self,job):self.dead=True;self.events.append("terminate_job")
    def terminate_process(self,process):self.dead=True;self.events.append("terminate_process")
    def available(self,handle):return len(self.streams[handle]) if self.streams[handle] else None
    def read(self,handle,count):value=self.streams[handle][:count];self.streams[handle]=self.streams[handle][count:];return value
    def close(self,handle):
        self.counts[handle]=self.counts.get(handle,0)+1
        if handle==100 and self.late:raise OSError("Synthetic original lease close error")
        if handle==100+len(self.config["inputs"])+2 and self.recheck and not self.failed_once:
            self.failed_once=True;raise OSError("Synthetic recheck close error")
        self.closed.append(handle);self.events.append("close_"+str(handle))
    def read_lease(self,item,deadline,ownership):
        assert p.pin(item["path"])==item
        row=dict(path=item["path"],handle=self.next_lease,closed=False,validation="passed",cleanup_errors=[])
        ownership.append(row);self.next_lease+=1;return row


def config(name):
    files=(SOURCE,p.BASIS,p.q.SDK_SOURCE,p.QUALIFICATION,p.CONTRACT,p.DESIGN,p.EXE,*p.runtime_pins(),*p.SYSTEM_PINS)
    value=p.configuration(ROOT/name,[p.pin(path) for path in files]);value["pure_fixture"]=True;return value


class PureChecks(unittest.TestCase):
    def fake(self,name,**options):
        c=config(name);protocol=ROOT/(name+"-protocol.json");protocol.write_bytes(p.canonical(c)+b"\n")
        expected=p.sha(protocol);api=FakeApi(c,expected,**options)
        with patch.object(p,"PROTOCOL",protocol),patch.object(p,"api_class",return_value=lambda *_:api):result=p.execute(c,expected)
        return c,api,result
    def test_actual_format_narrow_collection(self):
        rows=p.collect_inputs();dlls=[Path(row["path"]).name.casefold() for row in rows if Path(row["path"]).suffix.casefold()==".dll"]
        self.assertEqual(len(dlls),20);self.assertNotIn("ggml-cpu-x64.dll",dlls)
        self.assertFalse(any(Path(row["path"]).suffix.casefold()==".gguf" for row in rows))
        self.assertFalse(any(Path(row["path"]).name.casefold() in ("cl.exe","link.exe","harmless_launch_worker.exe") for row in rows))
    def test_exact_role_only_abi_four_args(self):
        c=config("role");self.assertEqual(len(c["argv"]),4);self.assertEqual(c["argv"][1],"--abi")
        c["argv"][1]="--recognize"
        with self.assertRaises(RuntimeError):p.validate_role(c)
        c=config("CPU");c["inputs"].append(dict(path=str(p.RUNTIME/"ggml-cpu-x64.dll"),bytes=0,sha256="0"*64))
        with self.assertRaises(RuntimeError):p.validate_role(c)
    def test_binding_table_unchanged_and_both_gates_false(self):
        self.assertFalse(sdk.NATIVE_EXECUTION_ENABLED)
        def specs(path,cls):
            node=next(n for n in ast.walk(ast.parse(path.read_bytes())) if isinstance(n,ast.ClassDef) and n.name==cls)
            return next(n.value for n in ast.walk(node) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="specs" for t in n.targets))
        self.assertEqual(ast.dump(specs(p.BASIS,"HarmlessKernel32"),include_attributes=False),
                         ast.dump(specs(SOURCE,"FixedABIKernel32"),include_attributes=False))
        with self.assertRaises(RuntimeError):sdk.execute_draft({})
        with self.assertRaises(RuntimeError):p.api_class()(config("reject-constructor"),"a"*64)
    def test_full_fake_strict_results_real_journal_and_seal(self):
        c,a,r=self.fake("ordinary")
        self.assertEqual(r["status"],"ABI_observations_retained_independent_qualification_pending")
        self.assertEqual(r["observations"]["version"],"synthetic-ABI-fixture");self.assertTrue(r["reaped"])
        self.assertFalse(r["observations"]["version_expected_previously_known"])
        self.assertTrue(all(record["closed"] for record in r["lease_ownership"]))
    def test_raw_counter_negative_primary_plus_recheck_error_retry(self):
        c,a,r=self.fake("counter-recheck",counter=2,recheck=True)
        self.assertEqual(r["status"],"failed");self.assertTrue(r["finalization_errors"])
        affected=[row for row in r["lease_ownership"] if row["cleanup_errors"]]
        self.assertEqual(len(affected),1);self.assertTrue(affected[0]["closed"]);self.assertEqual(a.counts[affected[0]["handle"]],2)
        from asof.journal import read_chain
        chain=read_chain(Path(c["output"])/"execution/journal.jsonl")
        self.assertTrue(any(e["event"]=="abi_job_snapshot_observed" and e["details"]["snapshot"]["accounting"]["decoded"]["TotalProcesses"]==2 for e in chain))
    def test_late_original_lease_error_veto(self):
        c,a,r=self.fake("late",late=True);self.assertEqual(r["status"],"failed")
        self.assertTrue((Path(c["output"])/"late-failure.json").exists())
    def test_timeout_owned_cleanup_and_no_retry(self):
        c,a,r=self.fake("timeout",timeout=True);self.assertEqual(r["status"],"failed");self.assertTrue(r["reaped"])
        self.assertEqual(a.events.count("create"),1);self.assertIn("terminate_job",a.events)
    def test_publication_after_resume_preserves_attempt_and_owned_cleanup(self):
        original=sdk.reserve_parent_journal
        class Proxy:
            def __init__(self,delegate):self.delegate=delegate
            def append(self,name,**details):
                if name=="abi_resume_returned":raise OSError("Synthetic resume publication fault")
                return self.delegate.append(name,**details)
            def close(self):return self.delegate.close()
        with patch.object(sdk,"reserve_parent_journal",side_effect=lambda *a,**k:Proxy(original(*a,**k))):c,a,r=self.fake("resume-fault")
        self.assertEqual(r["status"],"failed");self.assertTrue(r["attempt_reserved"]);self.assertTrue(r["reaped"])
        self.assertEqual(a.events.count("create"),1)
    def test_primary_plus_terminal_publication_error_is_retained(self):
        original=p.write_new
        def fail_report(path,value):
            if Path(path).name=="parent-report.json":raise OSError("Synthetic parent report fault")
            return original(path,value)
        with patch.object(p,"write_new",side_effect=fail_report):c,a,r=self.fake("report-fault",counter=2)
        self.assertEqual(r["status"],"failed")
        extra=json.loads((Path(c["output"])/"terminal-publication-error.json").read_bytes())
        self.assertIn("publication_error",extra);self.assertIn("primary_failure",extra)


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureChecks))
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",helper_sha256=p.sha(SOURCE),
        checker_sha256=p.sha(__file__),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        actual_children=0,real_sdk_constructions=0,target_DLL_loads=0,model_calls=0,denied_real_operations=denied,
        output=str(ROOT),scope="Own authored JSON/SDK/worker/timer fixtures; no native-target claim")
    with (HERE/"DETACHED-ABI-OBSERVATION-PURE-CHECKS-v1.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
