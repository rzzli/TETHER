"""Independent execute-AST fake lifecycle checks; no native construction/child."""
import ast
import copy
import ctypes  # stdlib declarations before the no-dlopen audit guard.
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import struct
import sys
import time
import types
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/"run_detached_abi_observation_v3.py"
COMPONENT=HERE/"detached_abi_terminal_observation_v3.py"
SDK_SOURCE=HERE/"detached_parent_launch_draft_v1.py"
REPORT=HERE/"DETACHED-ABI-NEGATIVE-INTEGRATION-PROOF-v3.json"
EXE=ROOT/"data/cache/r09-typed-ABI-build-v4-20261028T231155Z/typed_public_c_recognizer_abi.exe"
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
SOURCE_RAW=None
SDK_RAW=SDK_SOURCE.read_bytes()
assert hashlib.sha256(SDK_RAW).hexdigest()=="3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
COMPONENT_RAW=COMPONENT.read_bytes()
assert hashlib.sha256(COMPONENT_RAW).hexdigest()=="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
SPEC=json.loads((HERE/"DETACHED-ABI-EXECUTION-CONTRACT-v1.json").read_bytes())
DENIED=[]
FIXTURES=[]


def require(value,message):
    if not value:raise RuntimeError(message)


def pin(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def guard(event,args):
    if event=="ctypes.dlopen" or event in ("subprocess.Popen","os.system") or event.startswith("socket."):
        DENIED.append(event);raise AssertionError("No real API or child: "+event)


class Clock:
    def __init__(self):self.value=100.0
    def monotonic(self):return self.value
    def monotonic_ns(self):return int(self.value*1e9)
    def sleep(self,seconds):self.value+=seconds


def snapshot(total=1,active=0,pids=()):
    d=dict(TotalUserTime=0,TotalKernelTime=0,ThisPeriodTotalUserTime=0,ThisPeriodTotalKernelTime=0,
           TotalPageFaultCount=0,TotalProcesses=total,ActiveProcesses=active,TotalTerminatedProcesses=0)
    return dict(accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=struct.pack("<qqqqIIII",*d.values()).hex(),decoded=d),
       pid_list=dict(ok=True,error=0,returned_bytes=8+8*len(pids),raw_hex=struct.pack("<II16Q",len(pids),len(pids),*pids,*([0]*(16-len(pids)))).hex(),
                     assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))


def child_rows():
    return [dict(event=SPEC["child_artifacts"]["result_events"][0],dependency_native_initialization_possible=True),
            dict(event=SPEC["child_artifacts"]["result_events"][1],modules=[dict(name=EXE.name,path=str(EXE))]+[
                 dict(name=Path(row["path"]).name,path=row["path"]) for row in SPEC["runtime_pins"]],layouts=copy.deepcopy(SPEC["expected_layouts"])),
            dict(event=SPEC["child_artifacts"]["result_events"][2],version="synthetic-v3-ABI",defaults=copy.deepcopy(SPEC["expected_defaults"]),no_backend_or_model_call_so_far=True),
            dict(event=SPEC["child_artifacts"]["result_events"][3],version_expected_previously_known=False,backend_init_called=False,registry_called=False,
                 model_called=False,scope="typed version/defaults observation; independent ABI acceptance pending"),
            dict(event=SPEC["child_artifacts"]["result_events"][4],mode="--abi",elapsed_ms=1,parent_qualification_required=True)]


class FakeAPI:
    def __init__(self,clock,*,exit_code=2,fault=None):
        self.clock,self.code,self.fault=clock,exit_code,fault
        self.events=[];self.assigned=False;self.dead=False;self.exit_observed=False
        self.counts={};self.next_lease=100;self.expiry_injected=False
        self.streams={12:b"synthetic failure\n",14:b""}
    def create_job(self):self.events.append("create_job");return 10
    def configure_job(self,job):self.events.append("configure_job")
    def verify_limits(self,job):
        self.events.append("terminal_peaks" if self.exit_observed else "initial_limits")
        if self.exit_observed and self.fault=="peaks":raise OSError("Synthetic peak query failure")
        return dict(flags=8968,active_limit=1,process_commit=268435456,job_commit=268435456,peak_process_commit=1234,peak_job_commit=2345)
    def job_snapshot(self,job):
        self.events.append("terminal_snapshot" if self.exit_observed else "preterminal_snapshot")
        if self.exit_observed and self.fault=="snapshot":raise OSError("Synthetic final snapshot failure")
        if not self.assigned:return snapshot(0,0)
        return snapshot(2 if self.exit_observed and self.fault=="counter" else 1,0 if self.dead else 1,() if self.dead else (20,))
    def make_stdio(self,owned):owned.update(stdin=11,stdout_read=12,stdout_write=13,stderr_read=14,stderr_write=15)
    def create_suspended(self,argv,command,environment,cwd,handles,pi,job,creation,event):
        self.events.append("create");self.child=Path(argv[3])
        creation.update(api_attempt_reserved=True,return_observed=False,returned_success=None)
        event("abi_CreateProcessW_reserved",attribute_count=2,attribute_keys=[0x20002,0x2000D])
        if self.fault in ("KeyboardInterrupt","SystemExit","unknown_creation"):
            self.events.append("unknown_creation_fault")
            error={"KeyboardInterrupt":KeyboardInterrupt,"SystemExit":SystemExit,"unknown_creation":OSError}[self.fault]
            raise error("Synthetic unknown creation")
        pi.hProcess,pi.hThread,pi.dwProcessId,pi.dwThreadId=21,22,20,23
        creation.update(return_observed=True,returned_success=True);self.assigned=True
    def in_job(self,job,process):return True
    def identity(self,pi,exe):return dict(pid=20,image=str(exe),synthetic=True)
    def resume(self,thread):
        self.events.append("resume")
        self.child.mkdir(exist_ok=True)
        (self.child/"attempt.json").write_text(json.dumps(SPEC["child_artifacts"]["exact_attempt_claim"]),encoding="utf-8")
        if self.code==0:
            (self.child/"result.jsonl").write_text("".join(json.dumps(row)+"\n" for row in child_rows()),encoding="utf-8")
        else:(self.child/"failure.json").write_text('{"status":"synthetic_failed"}',encoding="utf-8")
        self.dead=self.fault!="deadline";return 1
    def wait(self,handle,milliseconds):
        if self.fault=="deadline" and not self.expiry_injected:
            self.expiry_injected=True;self.clock.value+=28.01;self.events.append("work_cutoff_fault")
            raise TimeoutError("Synthetic work deadline")
        return self.dead
    def exit_code(self,handle):self.exit_observed=True;self.events.append("exit_observed");return self.code
    def terminate_job(self,job):self.events.append("terminate_job");self.dead=True
    def terminate_process(self,handle):self.events.append("terminate_process");self.dead=True
    def available(self,handle):
        self.events.append("terminal_available" if self.exit_observed else "preterminal_available")
        if self.exit_observed and self.fault=="drain" and handle==12:raise OSError("Synthetic terminal drain failure")
        return len(self.streams[handle]) if self.streams[handle] else None
    def read(self,handle,count):
        self.events.append("read");b=self.streams[handle][:count];self.streams[handle]=self.streams[handle][count:];return b
    def read_lease(self,item,deadline,ownership):
        require(pin(item["path"])==item,"Synthetic input changed")
        row=dict(path=item["path"],handle=self.next_lease,closed=False,validation="passed",cleanup_errors=[])
        ownership.append(row);self.next_lease+=1;return row
    def close(self,handle):
        self.counts[handle]=self.counts.get(handle,0)+1;self.events.append("close_"+str(handle))
        if self.fault=="late_close" and handle==100:raise OSError("Synthetic original lease close error")
        if self.fault=="recheck_close" and handle==103 and self.counts[handle]==1:raise OSError("Synthetic first recheck close error")


def harness(name,*,exit_code=2,fault=None):
    clock=Clock();sdk_ns=dict(__file__=str(SDK_SOURCE),__name__="sdk_fake_integration")
    sdk_tree=ast.parse(SDK_RAW.decode());sdk_tree.body=[n for n in sdk_tree.body if not(isinstance(n,ast.ClassDef) and n.name=="Kernel32")]
    exec(compile(sdk_tree,str(SDK_SOURCE),"exec"),sdk_ns)
    sdk_ns["time"]=clock;sdk=types.SimpleNamespace(**sdk_ns)
    api=FakeAPI(clock,exit_code=exit_code,fault=fault)
    tree=ast.parse(SOURCE_RAW.decode());names={"execute","exact","json_value","runtime_pins","validate_modules","validate_child_artifacts"}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    require({n.name for n in nodes}==names,"Expected source components missing")
    system_metadata=json.loads((HERE/"BUILD-PROTOCOL.json").read_bytes())
    sysnames={x.casefold() for x in SPEC["System32_candidate_names"]}
    systempins={x["path"]:x for x in system_metadata["inputs"] if Path(x["path"]).parent==Path(r"C:\Windows\System32") and Path(x["path"]).name.casefold() in sysnames}
    component_ns={"__name__":"fake_terminal_integration"};exec(compile(COMPONENT_RAW,str(COMPONENT),"exec"),component_ns)
    def terminal():
        def wrapped(*args,**kwargs):return component_ns["observe_terminal"](*args,**kwargs,now=clock.monotonic,sleep=clock.sleep)
        return wrapped
    output=TEST_ROOT/name;protocol=TEST_ROOT/(name+"-protocol.json")
    real_write=sdk.write_new
    def write(path,value):
        if fault=="publication" and Path(path).name=="parent-report.json":raise OSError("Synthetic terminal publication failure")
        result=real_write(path,value)
        if fault=="after_seal" and Path(path).name=="terminal-seal.json":clock.value=161
        return result
    if fault=="after_seal":sdk_ns["write_new"]=write
    ns=dict(__file__=str(SOURCE),Path=Path,ExitStack=ExitStack,os=os,sys=sys,time=clock,metadata=metadata,json=json,
        sdk=sdk,q=types.SimpleNamespace(DEFAULT=Path(sys.executable)),require=require,pin=pin,sha=lambda path:pin(path)["sha256"],
        PROTOCOL=protocol,LIMITS=dict(parent_seconds=60,child_seconds=30,child_cleanup_reserved_seconds=2),
        TERMINAL_POLICY=dict(capture_drain_seconds=.25),terminal_observer=terminal,
        validate_role=lambda config:sdk.safe(config["output"],output=True),api_class=lambda:lambda *_:api,
        write_new=write,authority=lambda:copy.deepcopy(SPEC),EXE=EXE,RUNTIME=RUNTIME,SYSTEM_PINS=systempins,
        RUNTIME_EXPECTED={Path(x["path"]).name:{k:x[k] for k in ["bytes","sha256"]} for x in SPEC["runtime_pins"]})
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE)+"::<pure execute AST>","exec"),ns)
    if fault=="raw_publication":
        original=sdk_ns["reserve_parent_journal"]
        class Proxy:
            def __init__(self,journal):self.journal=journal
            def append(self,name,**details):
                if name=="abi_job_snapshot_observed" and details.get("stage")=="after_wait":raise OSError("Synthetic terminal raw publication failure")
                return self.journal.append(name,**details)
            def close(self):return self.journal.close()
        sdk.reserve_parent_journal=lambda *a,**k:Proxy(original(*a,**k))
    argv,command=sdk.abi_argv(EXE,RUNTIME,output/"execution/child")
    config=dict(output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),inputs=[pin(SOURCE)])
    protocol.write_bytes(sdk.canonical(config)+b"\n");result=ns["execute"](config,pin(protocol)["sha256"])
    FIXTURES.append(dict(case=name,output=str(output),status=result["status"],files=[pin(q) for q in sorted(output.rglob('*')) if q.is_file()]))
    return api,result,output,clock


class IntegrationTests(unittest.TestCase):
    def test_nonzero_terminal_records_precede_owned_close_and_primary_survives(self):
        api,r,out,clock=harness("nonzero")
        self.assertEqual(r["status"],"failed");self.assertEqual(r["failure"]["error"],"ABI child failed")
        self.assertTrue(r["terminal_observation"]["complete"])
        self.assertEqual(r["final_job_snapshot"]["accounting"]["decoded"]["ActiveProcesses"],0)
        self.assertEqual(r["memory_limits_and_peaks"]["peak_job_commit"],2345)
        self.assertTrue(all(x["eof"] for x in r["captures"].values()))
        self.assertLess(api.events.index("terminal_snapshot"),api.events.index("close_21"))
        self.assertLess(api.events.index("terminal_peaks"),api.events.index("close_10"))
    def test_all_independent_observation_faults_preserve_primary_and_cleanup(self):
        for fault in ["drain","snapshot","peaks","counter","raw_publication"]:
            with self.subTest(fault=fault):
                api,r,out,clock=harness("fault-"+fault,fault=fault)
                self.assertEqual(r["failure"]["error"],"ABI child failed")
                self.assertTrue(r["terminal_observation_errors"])
                self.assertTrue(r["reaped"]);self.assertIn("close_10",api.events)
                self.assertEqual(api.events.count("create"),1)
                if fault!="peaks":self.assertIn("terminal_peaks",api.events)
    def test_preexisting_interrupts_admit_no_terminal_API(self):
        for error in ["KeyboardInterrupt","SystemExit"]:
            with self.subTest(error=error):
                api,r,out,clock=harness("interrupt-"+error,fault=error)
                self.assertEqual(r["failure"]["error_class"],error)
                later=api.events[api.events.index("unknown_creation_fault")+1:]
                self.assertFalse(any(x in ["terminal_available","preterminal_available","terminal_snapshot","preterminal_snapshot","terminal_peaks","initial_limits","read"] for x in later))
                self.assertIn("terminate_job",later);self.assertNotIn("final_job_snapshot",r)
    def test_unknown_creation_and_deadline_never_claim_final_state(self):
        for fault in ["unknown_creation","deadline"]:
            with self.subTest(fault=fault):
                api,r,out,clock=harness("unknown-"+fault,fault=fault)
                self.assertFalse(r["terminal_observation"]["exit_observed"])
                self.assertFalse(r["terminal_observation"]["complete"])
                self.assertNotIn("final_job_snapshot",r);self.assertIn("terminate_job",api.events)
                self.assertLessEqual(r["child_full_process_elapsed_seconds"],30)
                if fault=="deadline":self.assertGreaterEqual(r["child_full_process_elapsed_seconds"],28)
    def test_recheck_failed_close_then_sealer_retry_success_retains_both(self):
        api,r,out,clock=harness("recheck",fault="recheck_close")
        self.assertEqual(r["failure"]["error"],"ABI child failed")
        self.assertTrue(r["finalization_errors"]);self.assertEqual(api.counts[103],2)
        cleanup=json.loads((out/"post-lease-cleanup.json").read_bytes())
        row=next(x for x in cleanup["outcomes"] if x["handle"]==103)
        self.assertTrue(row["closed_after"]);self.assertTrue(row["prior_cleanup_errors"])
    def test_original_lease_failure_creates_late_veto_preserving_primary(self):
        api,r,out,clock=harness("late",fault="late_close")
        self.assertEqual(r["failure"]["error"],"ABI child failed")
        self.assertTrue((out/"late-failure.json").exists())
        self.assertEqual(json.loads((out/"terminal-seal.json").read_bytes())["status"],"failed")
    def test_terminal_publication_preserves_primary_plus_secondary(self):
        api,r,out,clock=harness("publication",fault="publication")
        record=json.loads((out/"terminal-publication-error.json").read_bytes())
        self.assertEqual(record["primary_failure"]["error"],"ABI child failed")
        self.assertTrue(record["publication_error"]);self.assertEqual(r["status"],"failed")
    def test_success_and_after_seal_veto(self):
        api,r,out,clock=harness("success",exit_code=0)
        self.assertEqual(r["status"],"ABI_observations_retained_independent_qualification_pending")
        self.assertEqual(r["observations"]["version"],"synthetic-v3-ABI")
        api,r,out,clock=harness("after-seal",exit_code=0,fault="after_seal")
        self.assertEqual(r["status"],"failed")
        self.assertTrue((out/"after-seal-failure.json").exists())


if __name__=="__main__":
    sys.addaudithook(guard)
    SOURCE_RAW=SOURCE.read_bytes();source_sha=hashlib.sha256(SOURCE_RAW).hexdigest()
    TEST_ROOT=ROOT/"data/cache"/("r09-independent-negative-integration-"+str(time.time_ns()));TEST_ROOT.mkdir()
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_sha,"Parent changed during fake integration"
    execute=next(n for n in ast.parse(SOURCE_RAW.decode()).body if isinstance(n,ast.FunctionDef) and n.name=="execute")
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(case) for case,_ in result.failures],errors=[str(case) for case,_ in result.errors],elapsed_seconds=time.monotonic()-started,
        source=pin(SOURCE),execute_AST_sha256=hashlib.sha256(ast.dump(execute,include_attributes=False).encode()).hexdigest(),
        component=pin(COMPONENT),checker=pin(Path(__file__)),qualified_SDK_source=pin(SDK_SOURCE),
        scope="Independent execute-AST + terminal component + original SDK pure owner/sealer with fake API; role/authority inputs are synthetic, strict result parser uses retained contract shape",
        fixtures=FIXTURES,denied_real_operations=DENIED,activity=dict(real_SDK_constructors_or_API_calls=0,children_or_target_DLL_calls=0,CPU_DLL_GGUF_or_protected_reads=0))
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)["sha256"],fixtures=len(FIXTURES))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
