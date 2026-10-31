"""Pure draft checks: layout, arguments, memory captures and fake ownership.

Never constructs Kernel32, creates a process, loads a target DLL, imports AsOf
runtime, reads a GGUF, or uses a network connection. ctypes sizes only.
"""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "abi_parent_launch_draft_v3.py"
spec = importlib.util.spec_from_file_location("r09_abi_parent_draft_v3_pure", SOURCE)
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


def snapshot(total=0, active=0, terminated=0, pids=(), *, truncated=False):
    a, p = draft.ACCOUNTING(), draft.PID_LIST()
    a.TotalProcesses, a.ActiveProcesses, a.TotalTerminatedProcesses = total, active, terminated
    p.NumberOfAssignedProcesses = p.NumberOfProcessIdsInList = len(pids)
    for i, pid in enumerate(pids[:16]):
        p.ProcessIdList[i] = pid
    return dict(query_started_monotonic_ns=100, query_finished_monotonic_ns=101,
        accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=bytes(a).hex(),
            decoded={name:int(getattr(a,name)) for name,_ in a._fields_}),
        pid_list=dict(ok=True,error=0,returned_bytes=8 if truncated else 136,raw_hex=bytes(p).hex(),
            assigned_count=len(pids),listed_count=len(pids),pids=list(pids)))


class FakeApi:
    def __init__(self, failure=None, anomalous=False):
        self.failure, self.anomalous = failure, anomalous
        self.calls, self.closed, self.dead = [], [], False
        self.assigned = False

    def call(self, name):
        self.calls.append(name)
        if self.failure == name:
            raise RuntimeError("fixture_" + name)

    def create_job(self):
        self.call("create_job"); return 10

    def configure_job(self, job):
        self.call("configure_job")

    def verify_limits(self, job):
        self.call("verify_limits"); return dict(active_limit=1, process_commit=256*1024**2, job_commit=256*1024**2)

    def job_snapshot(self, job):
        self.call("job_snapshot")
        if not self.assigned:
            return snapshot()
        return snapshot(total=2 if self.anomalous else 1,active=2 if self.anomalous else 1,
                        pids=[20,99] if self.anomalous else [20])

    def make_stdio(self, owned):
        self.call("make_stdio")
        owned.update(stdin=11, stdout_read=12, stdout_write=13, stderr_read=14, stderr_write=15)

    def create_suspended(self, argv, command, environment, cwd, owned, pi, job, creation, event):
        self.call("create_suspended")
        if self.failure == "attribute_update":
            raise RuntimeError("fixture_JOB_LIST_update_failure")
        event("abi_CreateProcessW_reserved",attribute_count=2,
              attribute_keys=[draft.HANDLE_LIST_ATTRIBUTE,draft.JOB_LIST_ATTRIBUTE])
        creation["api_attempt_reserved"] = True
        if self.failure == "interrupt_inside_create":
            raise KeyboardInterrupt("fixture unknown CreateProcessW outcome")
        pi.hProcess, pi.hThread, pi.dwProcessId, pi.dwThreadId = 21, 22, 20, 23
        self.assigned = True
        if self.failure == "interrupt_after_create":
            raise KeyboardInterrupt("fixture interruption after output struct populated")
        creation.update(return_observed=True,returned_success=True)

    def in_job(self, job, process):
        self.call("in_job"); return self.failure != "membership_false"

    def identity(self, pi, exe):
        self.call("identity"); return dict(pid=int(pi.dwProcessId), thread_id=int(pi.dwThreadId), image=str(exe))

    def resume(self, thread):
        self.call("resume")
        if self.failure == "interrupt_in_resume":
            raise KeyboardInterrupt("fixture unknown actual resumption")
        return {"resume_zero":0, "resume_two":2, "resume_error":0xffffffff}.get(self.failure, 1)

    def wait(self, process, ms):
        self.call("wait"); return self.dead

    def terminate_process(self, process):
        self.call("terminate_process"); self.dead = True

    def terminate_job(self, job):
        self.call("terminate_job"); self.dead = True

    def close(self, handle):
        self.call("close")
        self.closed.append(handle)


class FakeCreatorSDK:
    """Python stand-in for the actual typed method's public SDK calls."""
    def __init__(self, failed_attribute=None):
        self.failed_attribute=failed_attribute;self.calls=[];self.attrs={}

    def InitializeProcThreadAttributeList(self, memory, count, flags, size):
        self.calls.append(("initialize",count))
        assert count==2
        draft.C.cast(size,draft.C.POINTER(draft.SIZE_T)).contents.value=128
        if memory is None:
            draft.C.set_last_error(122);return 0
        return 1

    def UpdateProcThreadAttribute(self,memory,flags,key,value,size,previous,returned):
        self.calls.append(("update",key))
        count=size//draft.C.sizeof(draft.HANDLE)
        self.attrs[key]=(value,count)
        if key==self.failed_attribute:
            draft.C.set_last_error(87);return 0
        return 1

    def CreateProcessW(self,application,command,psa,tsa,inherit,flags,environment,cwd,startup,pi):
        self.calls.append(("create",flags))
        assert inherit and flags==0x08080404
        si=draft.C.cast(startup,draft.C.POINTER(draft.STARTUPINFOEXW)).contents
        assert si.StartupInfo.cb==112 and si.StartupInfo.dwFlags==0x100
        assert [si.StartupInfo.hStdInput,si.StartupInfo.hStdOutput,si.StartupInfo.hStdError]==[11,13,15]
        values={k:list(draft.C.cast(pointer,draft.C.POINTER(draft.HANDLE*count)).contents)
                for k,(pointer,count) in self.attrs.items()}
        assert values=={0x20002:[11,13,15],0x2000d:[10]}
        info=draft.C.cast(pi,draft.C.POINTER(draft.PROCESS_INFORMATION)).contents
        info.hProcess,info.hThread,info.dwProcessId,info.dwThreadId=21,22,20,23
        return 1

    def DeleteProcThreadAttributeList(self,memory):
        self.calls.append(("delete",0))


class FakeFullApi(FakeApi):
    """No SDK calls: synthesize fixed outputs to test parent finalization only."""
    def __init__(self,late_close_failure=False,invalid_observation=False):
        super().__init__()
        self.child=None;self.next_lease=100
        self.late_close_failure=late_close_failure;self.invalid_observation=invalid_observation

    def create_suspended(self,argv,command,environment,cwd,owned,pi,job,creation,event):
        self.child=Path(argv[-1])
        return super().create_suspended(argv,command,environment,cwd,owned,pi,job,creation,event)

    def resume(self,thread):
        result=super().resume(thread)
        claim=dict(schema_version=1,mode="--abi",status="claimed_before_native_load",draft=True)
        rows=[dict(event="before_explicit_required_OpenMP_dependency_load"),
              dict(event="exact_core_modules_loaded_exports_resolved",modules=[],layouts={"synthetic_fixture":True}),
              dict(event="typed_version_and_defaults_observed",version="FAKE_PURE_FIXTURE_NOT_NATIVE",
                   defaults={"synthetic_fixture":True},no_backend_or_model_call_so_far=True),
              dict(event="abi_observations_returned",version_expected_previously_known=False,
                   backend_init_called=self.invalid_observation,registry_called=False,model_called=False),
              dict(event="child_normal_completion",mode="--abi",parent_qualification_required=True)]
        (self.child/"attempt.json").write_bytes(draft.canonical(claim)+b"\n")
        (self.child/"result.jsonl").write_bytes(b"".join(draft.canonical(row)+b"\n" for row in rows))
        self.dead=True
        return result

    def job_snapshot(self,job):
        if self.dead:
            return snapshot(total=1,active=0,pids=[])
        return super().job_snapshot(job)

    def available(self,handle):return None
    def exit_code(self,process):return 0

    def read_lease(self,item,deadline,ownership):
        record=dict(handle=self.next_lease,path=item["path"],closed=False,validation="passed",cleanup_errors=[])
        self.next_lease+=1
        ownership.append(record)
        return record

    def close(self,handle):
        if handle==100 and self.late_close_failure:
            raise OSError("fixture late original lease Close failure")
        return super().close(handle)


class PureDraftTests(unittest.TestCase):
    def owner(self, *, failure=None, anomalous=False, journal_failure=None):
        api, events = FakeApi(failure, anomalous), []
        def event(name, **fields):
            events.append(name)
            if name == journal_failure:
                raise OSError("fixture journal failure")
        owner = draft.OwnedLaunch(api, event)
        return api, owner, events

    def start(self, owner):
        argv = [str(draft.EXE), "--abi", str(draft.RUNTIME), str(draft.ROOT / "data/cache/pure-unused/child")]
        owner.start(argv, "fixture command only", dict(SystemRoot=r"C:\Windows"), draft.ROOT, lambda:None)

    def cleaned(self, owner, api):
        owner.cleanup(time.monotonic()+2)
        self.assertTrue(owner.reaped)
        self.assertEqual(owner.cleanup_errors, [])
        self.assertEqual(set(api.closed), set(range(10,16)) | {21,22})
        self.assertEqual(len(api.closed), 8)

    def test_public_sdk_x64_layouts(self):
        self.assertEqual(draft.layouts()["STARTUPINFOEXW"], 112)
        self.assertEqual(draft.ACCOUNTING.ActiveProcesses.offset, 40)
        self.assertEqual(draft.EXTENDED_LIMIT.PeakJobMemoryUsed.offset, 136)

    def test_finite_flags_no_breakaway(self):
        self.assertEqual(draft.CREATE_FLAGS, 0x08080404)
        self.assertFalse(draft.CREATE_FLAGS & 0x01000000)
        self.assertEqual(draft.JOB_FLAGS, 0x2308)
        self.assertEqual(draft.LIMITS["commit_bytes"], 268435456)

    def test_creation_time_job_verify_before_exact_resume(self):
        api, owner, events = self.owner()
        self.start(owner)
        self.assertNotIn("assign",api.calls)
        self.assertLess(api.calls.index("create_suspended"),api.calls.index("in_job"))
        self.assertLess(api.calls.index("in_job"),api.calls.index("identity"))
        self.assertLess(api.calls.index("identity"), api.calls.index("resume"))
        self.assertEqual(api.calls.count("resume"), 1)
        self.assertLess(events.index("abi_assigned_before_resume"), events.index("abi_resume_reserved"))
        self.assertTrue(owner.assigned and owner.resumed)
        self.cleaned(owner, api)

    def test_attribute_failure_never_creates_process_or_resumes(self):
        api, owner, _ = self.owner(failure="attribute_update")
        with self.assertRaisesRegex(RuntimeError, "JOB_LIST_update_failure"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        owner.cleanup(time.monotonic()+2)
        self.assertEqual(set(api.closed),set(range(10,16)))
        self.assertEqual(owner.pi.dwProcessId,0)
        self.assertFalse(owner.creation["api_attempt_reserved"])
        self.assertNotIn("terminate_job", api.calls)

    def test_membership_failure_never_resumes(self):
        api, owner, _ = self.owner(failure="membership_false")
        with self.assertRaisesRegex(RuntimeError, "not in exact Job"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)
        self.assertIn("terminate_job", api.calls)

    def test_job_anomaly_stops_before_resume(self):
        api, owner, _ = self.owner(anomalous=True)
        with self.assertRaisesRegex(RuntimeError, "accounting anomaly: assigned"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)

    def test_unknown_create_outcome_kills_only_own_job_no_resume(self):
        api,owner,_=self.owner(failure="interrupt_inside_create")
        with self.assertRaises(KeyboardInterrupt):
            self.start(owner)
        self.assertEqual(owner.resumption_record()["creation_state"],"unknown_CreateProcessW_outcome")
        owner.cleanup(time.monotonic()+2)
        self.assertIn("terminate_job",api.calls)
        self.assertNotIn("terminate_process",api.calls)
        self.assertNotIn("resume",api.calls)

    def temp_root(self):
        return Path(tempfile.mkdtemp(prefix="r09-abi-v3-pure-",dir=draft.ROOT/"data/cache"))

    def test_real_accepted_installed_journal_build_integration(self):
        from asof.journal import RunJournal,read_chain
        root=self.temp_root(); state=dict(owned=False,journal_reserved=False)
        journal=draft.reserve_parent_journal(root/"attempt",state)
        try:
            journal.append("abi_parent_attempt_reserved",qualification="pure_no_native_API")
        finally:
            journal.close()
        records=read_chain(root/"attempt/execution/journal.jsonl")
        self.assertEqual([x["event"] for x in records],["build_reserved","abi_parent_attempt_reserved"])
        self.assertTrue(state["owned"] and state["journal_reserved"])
        with self.assertRaisesRegex(ValueError,"Unknown journal kind"):
            RunJournal(root/"old-kind",kind="native_abi")

    def test_journal_constructor_failure_retains_owned_failure_marker(self):
        root=self.temp_root();state=dict(owned=False,journal_reserved=False)
        def broken(*args,**kwargs):
            self.assertEqual(kwargs["kind"],"build")
            raise OSError("fixture journal constructor failed")
        with self.assertRaisesRegex(OSError,"constructor failed"):
            draft.reserve_parent_journal(root/"attempt",state,journal_type=broken)
        failure=json.loads((root/"attempt/failure.json").read_bytes())
        self.assertEqual(failure["error_class"],"OSError")
        self.assertTrue(failure["authoritative"] and state["owned"])
        self.assertFalse(state["journal_reserved"])

    def test_existing_output_is_not_adopted_or_mutated(self):
        root=self.temp_root();state=dict(owned=False,journal_reserved=False)
        with self.assertRaises(FileExistsError):
            draft.reserve_parent_journal(root,state)
        self.assertFalse(state["owned"])
        self.assertEqual(list(root.iterdir()),[])

    def test_anomalous_raw_snapshot_durable_before_rejection(self):
        from asof.journal import read_chain
        root=self.temp_root();state=dict(owned=False,journal_reserved=False)
        journal=draft.reserve_parent_journal(root/"attempt",state)
        api=FakeApi(anomalous=True);owner=draft.OwnedLaunch(api,journal.append)
        try:
            with self.assertRaisesRegex(RuntimeError,"accounting anomaly: assigned"):
                self.start(owner)
        finally:
            owner.cleanup(time.monotonic()+2);journal.close()
        records=read_chain(root/"attempt/execution/journal.jsonl")
        observed=[x for x in records if x["event"]=="abi_job_snapshot_observed"]
        self.assertEqual(len(observed),2)
        raw=observed[-1]["details"]["snapshot"]
        self.assertEqual(observed[-1]["details"]["stage"],"before_resume")
        self.assertEqual(raw["accounting"]["decoded"]["ActiveProcesses"],2)
        self.assertEqual(list(raw["pid_list"]["pids"]),[20,99])
        self.assertEqual(len(bytes.fromhex(raw["accounting"]["raw_hex"])),48)
        self.assertEqual(len(bytes.fromhex(raw["pid_list"]["raw_hex"])),136)
        self.assertNotIn("resume",api.calls)

    def test_snapshot_write_failure_prevents_resume(self):
        api,owner,_=self.owner(journal_failure="abi_job_snapshot_observed")
        with self.assertRaisesRegex(OSError,"journal failure"):
            self.start(owner)
        owner.cleanup(time.monotonic()+2)
        self.assertNotIn("resume",api.calls)

    def test_lease_validation_and_close_failure_preserve_primary_and_owner(self):
        api=object.__new__(draft.Kernel32)
        api.k=SimpleNamespace(CreateFileW=lambda *args:77)
        owned=[]
        def validate(*args):
            self.assertEqual(len(owned),1)
            self.assertEqual(owned[0]["handle"],77)
            raise RuntimeError("fixture leased hash mismatch")
        def close(handle):
            self.assertEqual(handle,77)
            raise OSError("fixture CloseHandle failure")
        api.validate_lease,api.close=validate,close
        with self.assertRaisesRegex(RuntimeError,"leased hash mismatch"):
            api.read_lease(dict(path=str(SOURCE),bytes=0,sha256="0"*64),time.monotonic()+1,owned)
        self.assertFalse(owned[0]["closed"])
        self.assertEqual(owned[0]["primary_error"]["error_class"],"RuntimeError")
        self.assertEqual(owned[0]["cleanup_errors"][0]["error_class"],"OSError")

    def test_two_attribute_lists_keep_job_out_of_stdio_inheritance(self):
        values=draft.attribute_values(10,dict(stdin=11,stdout_write=13,stderr_write=15))
        self.assertEqual([x[0] for x in values],[0x20002,0x2000d])
        self.assertEqual([list(x[1]) for x in values],[[11,13,15],[10]])
        self.assertNotIn(10,list(values[0][1]))
        source=SOURCE.read_text()
        self.assertNotIn("AssignProcessToJobObject",source)
        self.assertIn("InitializeProcThreadAttributeList(None, 2",source)

    def concrete_creation(self,failed_attribute=None):
        api=object.__new__(draft.Kernel32);api.k=FakeCreatorSDK(failed_attribute)
        events=[];creation=dict(setup_attempted=True,api_attempt_reserved=False,return_observed=False,returned_success=None)
        pi=draft.PROCESS_INFORMATION()
        def event(name,**fields):events.append((name,fields))
        args=[str(draft.EXE),"--abi",str(draft.RUNTIME),str(draft.ROOT/"data/cache/pure-unused/child")]
        action=lambda:api.create_suspended(args,"fixture command",{"SystemRoot":r"C:\Windows"},draft.ROOT,
                  dict(stdin=11,stdout_write=13,stderr_write=15),pi,10,creation,event)
        return api,creation,pi,events,action

    def test_actual_typed_creation_method_uses_two_live_attribute_arrays(self):
        api,creation,pi,events,action=self.concrete_creation()
        action()
        self.assertEqual(pi.dwProcessId,20)
        self.assertTrue(creation["api_attempt_reserved"] and creation["return_observed"] and creation["returned_success"])
        self.assertEqual([x for x in api.k.calls if x[0]=="initialize"],[("initialize",2),("initialize",2)])
        self.assertEqual(api.k.calls[-1],("delete",0))
        self.assertEqual(events[0][1]["attribute_keys"],[0x20002,0x2000d])

    def test_failed_real_method_update_never_calls_create_or_resume(self):
        for key in (0x20002,0x2000d):
            with self.subTest(attribute=key):
                api,creation,pi,events,action=self.concrete_creation(key)
                with self.assertRaises(OSError):action()
                self.assertFalse(any(x[0]=="create" for x in api.k.calls))
                self.assertFalse(creation["api_attempt_reserved"])
                self.assertEqual(pi.dwProcessId,0)
                self.assertEqual(events,[])
                self.assertEqual(api.k.calls[-1],("delete",0))

    def test_failed_or_truncated_raw_snapshot_does_not_disappear(self):
        raw=snapshot(total=1,active=1,pids=[20],truncated=True)
        problem=draft.job_snapshot_problem(raw,"assigned",20)
        self.assertIn("Truncated",problem)
        self.assertEqual(raw["pid_list"]["returned_bytes"],8)
        raw["accounting"].update(ok=False,error=5)
        self.assertIn("query failed",draft.job_snapshot_problem(raw,"assigned",20))
        self.assertEqual(raw["accounting"]["error"],5)

    def test_preexisting_primary_and_late_close_error_both_retained(self):
        root=self.temp_root()
        primary=dict(authoritative=True,error_class="OriginalFixtureFailure",error="synthetic primary")
        draft.write_new(root/"failure.json",primary)
        draft.write_new(root/"receipt.json",dict(status="failed",synthetic_fixture=True))
        original_marker=(root/"failure.json").read_bytes();original_receipt=(root/"receipt.json").read_bytes()
        owned=[dict(path=str(SOURCE),handle=77,validation="passed",closed=False,cleanup_errors=[])]
        def failed_close(handle):
            self.assertEqual(handle,77)
            raise OSError("synthetic late CloseHandle failure")
        seal=draft.seal_post_lease_cleanup(root,SimpleNamespace(close=failed_close),owned,primary,"failed",
                   time.monotonic(),time.monotonic()+3)
        self.assertEqual((root/"failure.json").read_bytes(),original_marker)
        self.assertEqual((root/"receipt.json").read_bytes(),original_receipt)
        cleanup=json.loads((root/"post-lease-cleanup.json").read_bytes())
        late=json.loads((root/"late-failure.json").read_bytes())
        self.assertEqual(cleanup["primary_failure"]["error_class"],"OriginalFixtureFailure")
        self.assertEqual(cleanup["outcomes"][0]["close_error"]["error_class"],"OSError")
        self.assertTrue(late["authoritative"])
        self.assertEqual(seal["status"],"failed")
        self.assertEqual(seal["earlier_receipt"]["sha256"],hashlib.sha256(original_receipt).hexdigest())
        self.assertEqual(seal["cleanup_artifact"]["sha256"],hashlib.sha256((root/"post-lease-cleanup.json").read_bytes()).hexdigest())

    def fake_full_run(self,*,fail=False):
        root=self.temp_root()/"attempt";api=FakeFullApi(late_close_failure=fail,invalid_observation=fail)
        args,command=draft.abi_argv(draft.EXE,draft.RUNTIME,root/"execution/child")
        config=dict(output=str(root),argv=args,command_line=command,environment=draft.effective_environment(root),
                    inputs=[dict(path=str(SOURCE),bytes=SOURCE.stat().st_size,sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())],
                    pure_fixture=True,no_actual_SDK_or_child=True)
        # Only the injected fake factory is reachable during temporary fixture
        # enabling. The real Kernel32 constructor never executes.
        with patch.object(draft,"Kernel32",new=lambda:api),patch.object(draft,"prepare_config",new=lambda output:config),\
             patch.object(draft,"NATIVE_EXECUTION_ENABLED",new=True):
            result=draft.execute_draft(config)
        self.assertFalse(draft.NATIVE_EXECUTION_ENABLED)
        return root,api,result

    def test_fake_full_orchestration_success_requires_bound_terminal_seal(self):
        root,api,result=self.fake_full_run()
        self.assertEqual(result["status"],"ABI_observations_retained_independent_qualification_pending")
        self.assertTrue((root/"terminal-seal.json").is_file())
        self.assertFalse((root/"failure.json").exists())
        seal=json.loads((root/"terminal-seal.json").read_bytes())
        for name,item in seal["outputs"].items():
            raw=(root/name).read_bytes()
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(item["bytes"],item["sha256"]))
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(actual,set(seal["outputs"])|{"terminal-seal.json"})
        cleanup=json.loads((root/"post-lease-cleanup.json").read_bytes())
        self.assertEqual(len(cleanup["outcomes"]),2)
        self.assertTrue(all(x["closed_after"] for x in cleanup["outcomes"]))
        self.assertIn(100,api.closed)

    def test_fake_full_orchestration_primary_plus_late_failure_is_not_hidden(self):
        root,api,result=self.fake_full_run(fail=True)
        self.assertEqual(result["status"],"failed")
        primary=json.loads((root/"failure.json").read_bytes())
        self.assertEqual(primary["error_class"],"RuntimeError")
        self.assertIn("observation scope differs",primary["error"])
        late=json.loads((root/"late-failure.json").read_bytes())
        self.assertEqual(late["close_errors"][0]["error_class"],"OSError")
        seal=json.loads((root/"terminal-seal.json").read_bytes())
        self.assertEqual(seal["status"],"failed")
        self.assertEqual(seal["primary_failure_marker"]["sha256"],hashlib.sha256((root/"failure.json").read_bytes()).hexdigest())
        self.assertIn("late-failure.json",seal["outputs"])

    def test_resume_bad_previous_counts_have_no_second_attempt(self):
        for failure in ("resume_zero", "resume_two", "resume_error"):
            with self.subTest(failure=failure):
                api, owner, _ = self.owner(failure=failure)
                with self.assertRaisesRegex(RuntimeError, "exactly one suspension"):
                    self.start(owner)
                self.assertEqual(api.calls.count("resume"), 1)
                self.cleaned(owner, api)

    def test_interrupted_resume_records_unknown_not_zero_execution(self):
        api, owner, _ = self.owner(failure="interrupt_in_resume")
        with self.assertRaises(KeyboardInterrupt):
            self.start(owner)
        record=owner.resumption_record()
        self.assertTrue(record["resume_attempted"])
        self.assertFalse(record["resume_return_observed"])
        self.assertEqual(record["state"],"unknown_may_have_run")
        self.cleaned(owner,api)

    def test_journal_failure_before_resume_never_resumes(self):
        api, owner, _ = self.owner(journal_failure="abi_resume_reserved")
        with self.assertRaisesRegex(OSError, "journal failure"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)

    def test_journal_failure_after_create_retains_process_for_cleanup(self):
        api, owner, _ = self.owner(journal_failure="abi_created_suspended")
        with self.assertRaisesRegex(OSError, "journal failure"):
            self.start(owner)
        self.assertNotIn("assign", api.calls)
        self.cleaned(owner, api)

    def test_interruption_after_create_retains_output_handles(self):
        api, owner, _ = self.owner(failure="interrupt_after_create")
        with self.assertRaises(KeyboardInterrupt):
            self.start(owner)
        self.assertNotIn("assign", api.calls)
        self.cleaned(owner, api)

    def test_configure_failure_closes_job_no_process(self):
        api, owner, _ = self.owner(failure="configure_job")
        with self.assertRaisesRegex(RuntimeError, "configure_job"):
            self.start(owner)
        owner.cleanup(time.monotonic()+2)
        self.assertEqual(api.closed, [10])
        self.assertNotIn("create_suspended", api.calls)

    def test_capture_exact_boundary_then_one_byte_overflow(self):
        sink = io.BytesIO()
        state = dict(observed_bytes_at_least=0, retained_bytes=0, truncated=False)
        draft.consume_capture(state, b"abcd", sink, cap=4)
        self.assertEqual(sink.getvalue(), b"abcd")
        with self.assertRaisesRegex(RuntimeError, "unknown further bytes"):
            draft.consume_capture(state, b"z", sink, cap=4)
        self.assertEqual(sink.getvalue(), b"abcd")
        self.assertEqual(state, dict(observed_bytes_at_least=5, retained_bytes=4, truncated=True))

    def test_environment_explicit_sorted_utf16_double_nul(self):
        text = draft.environment_block(dict(z="astral \U0001f642", A="two words"))
        self.assertEqual(text, "A=two words\0z=astral \U0001f642\0\0")
        self.assertTrue(text.encode("utf-16-le").endswith(b"\0\0\0\0"))
        env = draft.effective_environment(draft.ROOT / "data/cache/pure-unused")
        self.assertEqual(set(env), {"SystemRoot","WINDIR","SystemDrive","PATH","TEMP","TMP","OMP_NUM_THREADS","OMP_THREAD_LIMIT"})
        self.assertNotIn("GGML_BACKEND_PATH", env)

    def test_environment_rejects_ambiguous_nul_nonstring_and_surrogate(self):
        for env in ({"a":"x","A":"y"},{"a\0":"x"},{"a":"x\0"},{"a":1},{"a=b":"x"}):
            with self.subTest(env=repr(env)), self.assertRaises(RuntimeError):
                draft.environment_block(env)
        with self.assertRaises(UnicodeEncodeError):
            draft.environment_block({"a":"\ud800"})

    def test_exact_abi_arguments_runtime_binding_and_quoting(self):
        child = draft.ROOT / "data/cache/pure unused/child"
        args, command = draft.abi_argv(draft.EXE,draft.RUNTIME,child)
        self.assertEqual(args[1],"--abi")
        self.assertEqual(len(args),4)
        self.assertIn('"'+str(child)+'"',command)
        with self.assertRaisesRegex(RuntimeError,"Exact ABI-only"):
            draft.abi_argv(draft.EXE,draft.RUNTIME.parent,child)

    def test_deadlines_reject_nonfinite_expired_and_bool(self):
        for end in (float("inf"),float("nan"),True):
            with self.subTest(end=end),self.assertRaises(RuntimeError):
                draft.finite_deadline(end)
        with self.assertRaises(TimeoutError):
            draft.finite_deadline(time.monotonic()-1)

    def test_native_construction_and_entry_are_held(self):
        self.assertFalse(draft.NATIVE_EXECUTION_ENABLED)
        with self.assertRaisesRegex(RuntimeError,"construction is disabled"):
            draft.Kernel32()
        with self.assertRaisesRegex(RuntimeError,"execution disabled"):
            draft.execute_draft({})

    def test_no_subprocess_creation_private_api_or_network_import(self):
        tree=ast.parse(SOURCE.read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imports += [x.name for n in ast.walk(tree) if isinstance(n,ast.Import) for x in n.names]
        self.assertFalse(set(imports)&{"_winapi","socket","urllib.request","requests"})
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in {"Popen","run","check_output","system"} for n in calls))


def main():
    require_flags = sys.flags.isolated and sys.dont_write_bytecode
    if not require_flags:
        raise RuntimeError("Use accepted installed interpreter -I -B")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureDraftTests))
    report=dict(schema_version=1,status="passed_pure_draft_checks" if result.wasSuccessful() else "failed_pure_draft_checks",
                helper_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
                native_API_construction_enabled=False,actual_processes_created=0,target_native_calls=0,
                ctypes_kernel32_construction=0,network_requests=0,GGUF_reads=0,
                scope="Pure sizes/offsets, argv/environment/caps and fake-API ownership sequencing only; no Windows API qualification")
    target=HERE/"ABI-PARENT-V3-PURE-CHECKS.json"
    with target.open("xb") as f:f.write(json.dumps(report,sort_keys=True,indent=2).encode()+b"\n")
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":
    raise SystemExit(main())
