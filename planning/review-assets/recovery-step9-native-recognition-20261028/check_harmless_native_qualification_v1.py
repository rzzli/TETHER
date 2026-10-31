"""Pure own-C++ qualifier checks; no real SDK constructor or EXE execution."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"qualify_harmless_native_worker_v1.py"
SOURCE_SHA="c5756bd173e1a613f883713c39891a5709631fdb9edcac4164f43b725e807697"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
spec=importlib.util.spec_from_file_location("owned_harmless_launcher_pure",SOURCE)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
sdk=q.load_sdk()  # Frozen declarations only; no Kernel32 constructor.
denied=[]


def audit(event,args):
    if event in ("ctypes.dlopen","subprocess.Popen","os.system","socket.__new__","socket.getaddrinfo","socket.connect"):
        denied.append(event);raise RuntimeError("Pure checks cannot load/dispatch/network")


sys.addaudithook(audit)
ROOT=q.ROOT/"data/cache"/("r09-harmless-native-qualification-pure-"+str(time.time_ns()))
ROOT.mkdir()


def snapshot(total=0,active=0,pids=()):
    a,p=sdk.ACCOUNTING(),sdk.PID_LIST();a.TotalProcesses=total;a.ActiveProcesses=active
    p.NumberOfAssignedProcesses=p.NumberOfProcessIdsInList=len(pids)
    for i,pid in enumerate(pids):p.ProcessIdList[i]=pid
    return dict(query_started_monotonic_ns=1,query_finished_monotonic_ns=2,
        accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=bytes(a).hex(),decoded={n:int(getattr(a,n)) for n,_ in a._fields_}),
        pid_list=dict(ok=True,error=0,returned_bytes=136,raw_hex=bytes(p).hex(),assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))


class FakeApi:
    """Explicit fake outputs/SDK handles; never runs the pinned own EXE."""
    def __init__(self,config,expected,late=False):
        self.config,self.expected,self.late=config,expected,late
        self.next_lease=100;self.calls=[];self.closed=[];self.dead=False;self.assigned=False
    def create_job(self):self.dead=False;self.assigned=False;self.resumed=False;self.queries=0;self.calls.append("create_job");return 10
    def configure_job(self,job):self.calls.append("configure_job")
    def verify_limits(self,job):
        self.calls.append("verify_limits");return dict(flags=sdk.JOB_FLAGS,active_limit=1,process_commit=268435456,job_commit=268435456)
    def job_snapshot(self,job):
        self.queries+=1
        self.calls.append("snapshot_finished" if self.dead else "snapshot_live")
        if self.dead and self.mode=="resources" and self.queries>=4:return snapshot(2,0)
        return snapshot(1,0) if self.dead else snapshot(1,1,[20]) if self.assigned else snapshot()
    def make_stdio(self,owned):owned.update(stdin=11,stdout_read=12,stdout_write=13,stderr_read=14,stderr_write=15)
    def create_suspended(self,argv,command,environment,cwd,owned,pi,job,creation,event):
        self.mode,self.child=argv[1],Path(argv[2]);self.queue={12:b"",14:b""}
        event("abi_CreateProcessW_reserved",attribute_count=2,attribute_keys=[sdk.HANDLE_LIST_ATTRIBUTE,sdk.JOB_LIST_ATTRIBUTE])
        creation.update(api_attempt_reserved=True,return_observed=True,returned_success=True)
        pi.hProcess,pi.hThread,pi.dwProcessId,pi.dwThreadId=21,22,20,23;self.assigned=True
    def in_job(self,job,process):return True
    def identity(self,pi,exe):return dict(pid=20,thread_id=23,image=str(exe),synthetic=True)
    def resume(self,thread):
        self.resumed=True;self.calls.append("resume")
        q.write_new(self.child/"worker-started.json",dict(pid=20,mode=self.mode,protocol_sha256=self.expected,executable=str(q.OWN_EXE),synthetic=True))
        if self.mode=="resources":
            value=dict(small_control_bytes=65536,small_control_released=True,memory_rejected=True,
                       descendant_spawn_attempts=1,spawn=dict(rejected=True,winerror=1816,child_pid=None,thread_id=None),
                       target_library_calls=0,model_calls=0,network_requests=0,synthetic=True)
            q.write_new(self.child/"worker-result.json",value);self.queue[12]=q.canonical(value)+b"\n";self.dead=True
        elif self.mode=="overflow":self.queue[12]=b"x"*(65536+8192)
        return 1
    def wait(self,process,ms):
        if self.mode=="sleep" and self.resumed and not self.dead:
            raise TimeoutError("Declared ABI parent/child deadline exceeded")  # Synthetic timer trigger only.
        return self.dead
    def terminate_job(self,job):self.dead=True;self.calls.append("terminate_job")
    def terminate_process(self,process):self.dead=True;self.calls.append("terminate_process")
    def exit_code(self,process):return 0 if self.mode=="resources" else 125
    def available(self,handle):return len(self.queue[handle]) if self.queue[handle] else None
    def read(self,handle,count):value=self.queue[handle][:count];self.queue[handle]=self.queue[handle][count:];return value
    def close(self,handle):
        if handle==100 and self.late:raise OSError("Synthetic original-lease close failure")
        self.closed.append(handle);self.calls.append("close_"+str(handle))
    def read_lease(self,item,deadline,ownership):
        assert q.pin(item["path"])==item
        record=dict(path=item["path"],handle=self.next_lease,closed=False,validation="passed",cleanup_errors=[])
        self.next_lease+=1;ownership.append(record);return record


def config(name):
    inputs=[q.pin(path) for path in (SOURCE,q.SDK_SOURCE,q.SEALER,q.WORKER,q.SOURCE_COPY,q.OWN_EXE,q.BASE,q.DEFAULT,
        q.BUILD_VERIFICATION,q.BUILD_PROTOCOL,q.BUILD/"terminal-seal.json",*q.SYSTEM_DLL_PINS)]
    return q.configuration(ROOT/name,inputs)


class FakeCall:
    def __init__(self):self.calls=[]
    def __call__(self,*args):self.calls.append(args);return 0


class FakeLibrary:
    def __init__(self):self.functions={}
    def __getattr__(self,name):return self.functions.setdefault(name,FakeCall())


class PureChecks(unittest.TestCase):
    def test_native_exact_five_argument_own_exe_launch(self):
        c=config("native-argv");expected="a"*64
        argv,command,environment=q.launch_argv(c,expected,c["cases"][0])
        self.assertEqual(argv,[str(q.OWN_EXE),"resources",c["cases"][0]["child_output"],c["child_protocol"],expected])
        self.assertNotIn("-I",argv);self.assertNotIn("-B",argv)
        self.assertNotIn(str(q.BASE),argv);self.assertNotIn(str(sdk.EXE),argv)
    def test_native_input_closure_rejects_upstream_and_missing_system_pin(self):
        for path in (sdk.EXE,sdk.RUNTIME/"llama.dll",Path(r"C:\Windows\System32\other.dll")):
            c=config("native-extra-"+path.name)
            c["inputs"].append(dict(path=str(path),bytes=0,sha256="0"*64))
            with self.assertRaises(RuntimeError):q.validate_role(c)
        c=config("native-missing-system")
        c["inputs"]=[item for item in c["inputs"] if item["path"]!=next(iter(q.SYSTEM_DLL_PINS))]
        with self.assertRaises(RuntimeError):q.validate_role(c)
    def test_native_build_and_system_role_mismatch_rejected(self):
        c=config("native-bad-build");c["build_verification_sha256"]="0"*64
        with self.assertRaises(RuntimeError):q.validate_role(c)
        c=config("native-bad-system");c["system_dll_pins"]=[{**item,"sha256":"0"*64} for item in c["system_dll_pins"]]
        with self.assertRaises(RuntimeError):q.validate_role(c)
    def test_resource_final_policy_exact_and_generic_unchanged(self):
        value=snapshot(2,0)
        before=json.dumps(value,sort_keys=True)
        self.assertIsNone(q.resource_finished_problem(sdk,value))
        self.assertEqual(before,json.dumps(value,sort_keys=True))
        self.assertIsNotNone(sdk.job_snapshot_problem(value,"finished",20))
        self.assertIsNone(sdk.job_snapshot_problem(snapshot(1,0),"finished",20))
        for total,active,pids in ((1,0,()),(3,0,()),(2,1,(20,)),(2,2,(20,99)),(2,0,(99,))):
            with self.subTest(total=total,active=active,pids=pids):
                self.assertIsNotNone(q.resource_finished_problem(sdk,snapshot(total,active,pids)))
    def test_resource_policy_malformed_and_native_errors_fail_closed(self):
        for modify in (lambda x:x["accounting"].update(raw_hex="00"),
                       lambda x:x["accounting"].update(returned_bytes=47),
                       lambda x:x["accounting"].update(error=5),
                       lambda x:x["pid_list"].update(raw_hex="zz"),
                       lambda x:x["pid_list"].update(pids=[99]),
                       lambda x:x["accounting"]["decoded"].update(TotalProcesses=1)):
            value=snapshot(2,0);modify(value)
            self.assertIsInstance(q.resource_finished_problem(sdk,value),str)
        for value in (None,{},[],{"accounting":None}):
            self.assertIsInstance(q.resource_finished_problem(sdk,value),str)
    def test_resource_override_is_final_only_and_retains_raw_before_rejection(self):
        class OnlyTwo:
            def job_snapshot(self,job):return snapshot(2,0)
        events=[]
        owner=q.owner_for_case(sdk,OnlyTwo(),lambda name,**details:events.append((name,details)),"resources")
        owner.job=10;owner.pi.dwProcessId=20
        with self.assertRaises(RuntimeError):owner.observe_job("harmless_running_first","running_or_finished")
        self.assertEqual(events[-1][1]["snapshot"]["accounting"]["decoded"]["TotalProcesses"],2)
        self.assertEqual(len(events),1)
        value=owner.observe_job("harmless_after_wait","finished")
        self.assertEqual(value["accounting"]["decoded"]["TotalProcesses"],2)
        other=q.owner_for_case(sdk,OnlyTwo(),lambda *a,**k:None,"overflow")
        self.assertIs(type(other),sdk.OwnedLaunch)
    def test_original_sdk_stays_hard_disabled(self):
        self.assertIs(sdk.NATIVE_EXECUTION_ENABLED,False)
        with self.assertRaisesRegex(RuntimeError,"construction is disabled"):sdk.Kernel32()
        with self.assertRaisesRegex(RuntimeError,"execution disabled"):sdk.execute_draft({})
    def test_role_rejects_target_and_wrong_worker_or_cases(self):
        for field,value in (("executable",str(sdk.EXE)),("worker_sha256","0"*64),("limits",{}),("kind","abi")):
            c=config("invalid-"+field);c[field]=value
            with self.assertRaises(RuntimeError):q.validate_role(c)
        c=config("invalid-case");c["cases"].reverse()
        with self.assertRaises(RuntimeError):q.validate_role(c)
    def test_exact_constructor_and_once_only_case_gate(self):
        c=config("binding");expected="a"*64;library=FakeLibrary()
        with patch.object(sdk.C,"WinDLL",return_value=library) as factory:
            api=q.api_class(sdk)(c,expected)
            self.assertEqual(factory.call_count,1)
            args,command,env=q.launch_argv(c,expected,c["cases"][0])
            wrong=list(args);wrong[0]=str(sdk.EXE)
            with self.assertRaises(RuntimeError):api.create_suspended(wrong,command,env,Path(c["output"]),{},None,10,{},lambda *a,**k:None)
            with patch.object(sdk.Kernel32,"create_suspended",return_value=None) as inherited:
                api.create_suspended(args,command,env,Path(c["output"]),{},None,10,{},lambda *a,**k:None)
                with self.assertRaisesRegex(RuntimeError,"already attempted"):
                    api.create_suspended(args,command,env,Path(c["output"]),{},None,10,{},lambda *a,**k:None)
                self.assertEqual(inherited.call_count,1)
            self.assertIs(sdk.NATIVE_EXECUTION_ENABLED,False)
    def test_constructor_rejects_synthetic_configuration_before_binding(self):
        c=config("reject-synthetic");c["pure_fixture"]=True
        with patch.object(sdk.C,"WinDLL") as factory:
            with self.assertRaisesRegex(RuntimeError,"Synthetic configuration"):q.api_class(sdk)(c,"a"*64)
            factory.assert_not_called()
    def test_binding_specs_match_frozen_sdk_exactly(self):
        def specs(tree,cls):
            node=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name==cls)
            return next(n.value for n in ast.walk(node) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="specs" for t in n.targets))
        class Unprefix(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=="sdk":return ast.Name(id=node.attr,ctx=ast.Load())
                return self.generic_visit(node)
        a=specs(ast.parse(q.SDK_SOURCE.read_text()),"Kernel32")
        b=Unprefix().visit(specs(ast.parse(SOURCE.read_text()),"HarmlessKernel32"))
        self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
    def test_qualification_sealer_differs_only_in_success_literal(self):
        original=next(n for n in ast.parse(q.SDK_SOURCE.read_text()).body
                      if isinstance(n,ast.FunctionDef) and n.name=="seal_post_lease_cleanup")
        copied=next(n for n in ast.walk(ast.parse(q.SEALER.read_text()))
                    if isinstance(n,ast.FunctionDef) and n.name=="seal_post_lease_cleanup")
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self,node):
                if node.value=="harmless_launch_qualification_passed":
                    return ast.Constant(value="ABI_observations_retained_independent_qualification_pending")
                return node
        self.assertEqual(ast.dump(original,include_attributes=False),
                         ast.dump(Normalize().visit(copied),include_attributes=False))
    def full_fake(self,name,late=False):
        c=config(name);c["pure_fixture"]=True
        protocol=ROOT/(name+"-protocol.json");protocol.write_bytes(q.canonical(c)+b"\n")
        expected=hashlib.sha256(protocol.read_bytes()).hexdigest();api=FakeApi(c,expected,late)
        with patch.object(q,"PROTOCOL",protocol),patch.object(q,"api_class",return_value=lambda *_:api):
            result=q.execute(c,expected)
        return c,api,result
    def test_full_fake_four_cases_real_journal_and_seal(self):
        c,api,result=self.full_fake("fake-complete")
        self.assertEqual(result["status"],"four_harmless_cases_retained_independent_review_pending")
        self.assertEqual(result["terminal_status"],"harmless_launch_qualification_passed")
        self.assertEqual(result["remaining_not_attempted"],[])
        modes={x["mode"]:x for x in result["cases"]}
        self.assertEqual(modes["overflow"]["captures"]["stdout"]["retained_bytes"],65536)
        self.assertGreater(modes["overflow"]["captures"]["stdout"]["observed_bytes_at_least"],65536)
        self.assertFalse(modes["suspended_abort"]["resumption"]["resume_attempted"])
        self.assertFalse((Path(c["cases"][-1]["child_output"])/"worker-started.json").exists())
        self.assertLess(api.calls.index("snapshot_finished"),api.calls.index("close_21"))
        from asof.journal import read_chain
        chain=read_chain(Path(c["output"])/"execution/journal.jsonl")
        injected=[e for e in chain if e["event"]=="harmless_injected_suspended_abort"]
        self.assertEqual(len(injected),1)
        self.assertIs(sdk.NATIVE_EXECUTION_ENABLED,False)
    def test_case_publication_failure_does_not_relabel_activity_unattempted(self):
        c=config("fake-case-publication");c["pure_fixture"]=True
        protocol=ROOT/"fake-case-publication-protocol.json";protocol.write_bytes(q.canonical(c)+b"\n")
        expected=hashlib.sha256(protocol.read_bytes()).hexdigest();api=FakeApi(c,expected)
        original=q.write_new
        def fail_case_report(path,value):
            if Path(path).name=="case-report.json":raise OSError("Synthetic case-report publication failure")
            return original(path,value)
        with patch.object(q,"PROTOCOL",protocol),patch.object(q,"api_class",return_value=lambda *_:api),patch.object(q,"write_new",side_effect=fail_case_report):
            result=q.execute(c,expected)
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["remaining_not_attempted"],["overflow","sleep","suspended_abort"])
        self.assertEqual(result["case_attempts"][0]["mode"],"resources")
        self.assertEqual(result["case_attempts"][0]["status"],"reserved_case_return_not_observed")
        self.assertIn("resume",api.calls)
        from asof.journal import read_chain
        events=read_chain(Path(c["output"])/"execution/journal.jsonl")
        self.assertEqual(sum(e["event"]=="harmless_case_call_reserved" for e in events),1)
        self.assertEqual(sum(e["event"]=="abi_resume_returned" for e in events),1)
        self.assertEqual(result["terminal_status"],"failed")
    def test_expected_stop_wrong_exit_is_rejected(self):
        c=config("fake-wrong-stop-exit");c["pure_fixture"]=True
        protocol=ROOT/"fake-wrong-stop-exit-protocol.json";protocol.write_bytes(q.canonical(c)+b"\n")
        expected=hashlib.sha256(protocol.read_bytes()).hexdigest()
        class WrongExit(FakeApi):
            def exit_code(self,process):return 0
        api=WrongExit(c,expected)
        with patch.object(q,"PROTOCOL",protocol),patch.object(q,"api_class",return_value=lambda *_:api):
            result=q.execute(c,expected)
        self.assertEqual(result["status"],"failed")
        overflow=result["cases"][1]
        self.assertEqual(overflow["mode"],"overflow")
        self.assertEqual(overflow["stopped_returncode"],0)
        self.assertIn("termination125",overflow["failure"]["error"])
        self.assertEqual(result["remaining_not_attempted"],["sleep","suspended_abort"])
    def test_full_fake_late_lease_failure_vetoes_early_success(self):
        c,api,result=self.full_fake("fake-late-close",late=True)
        self.assertEqual(result["status"],"four_harmless_cases_retained_independent_review_pending")
        self.assertEqual(result["terminal_status"],"failed")
        root=Path(c["output"])
        self.assertTrue((root/"late-failure.json").exists())
        cleanup=json.loads((root/"post-lease-cleanup.json").read_bytes())
        self.assertEqual(len(cleanup["close_errors"]),1)
        self.assertEqual(cleanup["close_errors"][0]["handle"],100)
        self.assertEqual(cleanup["close_errors"][0]["error_class"],"OSError")
        self.assertIn("original-lease close failure",cleanup["close_errors"][0]["error"])


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PureChecks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(schema_version=1,status="passed_native_own_worker_pure_checks" if result.wasSuccessful() else "failed",
        helper_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),output=str(ROOT),real_sdk_constructions=0,
        actual_children=0,target_library_calls=0,model_calls=0,network_requests=0,original_sdk_enabled=sdk.NATIVE_EXECUTION_ENABLED,
        denied_real_operations=denied,scope="Synthetic API/worker/timer results with real accepted journal and terminal sealing; no flag toggles or real SDK construction")
    with (HERE/"HARMLESS-NATIVE-QUALIFICATION-PURE-CHECKS-v1.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
