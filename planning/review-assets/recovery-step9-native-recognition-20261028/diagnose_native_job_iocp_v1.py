"""UNFROZEN: one own-worker overflow diagnostic; never qualification or ABI.

No execution is authorized by this source. Prepare/pure/peer/root gates precede
the separately decided once-only attempt. The original SDK stays disabled.
"""
from contextlib import ExitStack
import ast
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import subprocess  # list2cmdline only
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASIS=HERE/"qualify_harmless_native_worker_v1.py"
BASIS_SHA="c5756bd173e1a613f883713c39891a5709631fdb9edcac4164f43b725e807697"
def sha(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
if sha(BASIS)!=BASIS_SHA:raise RuntimeError("Frozen harmless source basis changed")
spec=util.spec_from_file_location("frozen_native_qualifier_for_iocp",BASIS)
q=util.module_from_spec(spec);spec.loader.exec_module(q)
sdk=q.load_sdk()  # declarations only; no real Kernel32 constructor
safe,pin,canonical,write_new,require=q.safe,q.pin,q.canonical,q.write_new,q.require
CONTRACT=HERE/"JOB-IOCP-OBSERVER-CONTRACT-v1.json"
CONTRACT_SHA="5e8c41b6ef6aecc30e40d855cf966bf69086f32160d81f2aadca059e05c12a7d"
DESIGN=HERE/"JOB-IOCP-OBSERVER-DESIGN-v1.md"
DESIGN_SHA="7709b18ee65b5d726faa313cfb311ea0521fba4dd147662031ab39d681050acd"
PRIOR_PROTOCOL_SHA="e29a7bf8a141ba02d41248c0e693a441c2e2fa3731fb360e833325435af0c652"
FAILURE_PROOF=HERE/"HARMLESS-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json"
FAILURE_PROOF_SHA="939a78fca943ab19a7c3774ea08a9456882cdd0bd14986c5c228711b51df7f1f"
PROTOCOL=HERE/"NATIVE-JOB-IOCP-PROTOCOL-v1.json"
PURE=HERE/"NATIVE-JOB-IOCP-PURE-CHECKS-v4.json"
CHECKER=HERE/"check_native_job_iocp_v4.py"
SEALER=HERE/"job_iocp_status_seal_v1.py"
SEALER_SHA="5dfb709fe1ccdf80ed62ec4670e4ad2852005a7708579fa7de5c920c31a8e4cb"
COMPLETION_KEY=0x52303949
ACCESS=0x00101000
PID_MESSAGES={2,6,7,8,9,10,11}
MESSAGES={1:"END_OF_JOB_TIME",2:"END_OF_PROCESS_TIME",3:"ACTIVE_PROCESS_LIMIT",4:"ACTIVE_PROCESS_ZERO",
          6:"NEW_PROCESS",7:"EXIT_PROCESS",8:"ABNORMAL_EXIT_PROCESS",9:"PROCESS_MEMORY_LIMIT",
          10:"JOB_MEMORY_LIMIT",11:"NOTIFICATION_LIMIT"}
BOUNDARIES=("before_terminate","after_terminate_return_before_wait",
            "after_owned_reap_observer_handles_held","after_observer_pid_release_before_job_close")
LIMITS=dict(parent_seconds=60,case_seconds=8,cleanup_reserve_seconds=2,finalization_reserve_seconds=5,
    commit_bytes=268435456,active_processes=1,stream_bytes=65536,maximum_children=1,
    snapshots=40,pre_stop_snapshots=36,reserved_stop_snapshots=4,job_pids=16,
    packets=64,pid_records=16,queue_calls=1024,batch_packets=8,queue_timeout_ms=0,pid_wait_ms=0)


class ASSOCIATE_COMPLETION_PORT(sdk.C.Structure):
    _fields_=[("CompletionKey",sdk.PVOID),("CompletionPort",sdk.HANDLE)]


class ObservationStop(RuntimeError):pass


def observer_layouts():
    require(sdk.C.sizeof(sdk.SIZE_T)==8 and sdk.C.sizeof(ASSOCIATE_COMPLETION_PORT)==16
            and ASSOCIATE_COMPLETION_PORT.CompletionKey.offset==0
            and ASSOCIATE_COMPLETION_PORT.CompletionPort.offset==8,"IOCP x64 layout mismatch")


class Observer:
    """Own port plus query-only handles; never owns a PID mutation capability."""
    def __init__(self,api,journal,deadline):
        self.api,self.journal,self.deadline=api,journal,deadline
        self.owner=None;self.job=None;self.port=None;self.port_closed=False
        self.calls=[];self.packets=0;self.pids={};self.snapshots=[];self.boundaries={}
        self.errors=[];self.incomplete=[];self.findings=[];self.drain_ends=[]
        self.termination=dict(attempted=False,return_observed=False)
        self.wait_state="not_waited";self.no_new_opens=False
    def event(self,name,**details):self.journal.append(name,**details)
    def error(self,phase,error):
        self.errors.append(dict(phase=phase,error_class=type(error).__name__,error=str(error)[:2048]))
    def cleanup_event(self,name,**details):
        try:self.event(name,**details)
        except BaseException as error:self.error("publication_"+name,error)
    def outstanding(self):
        return [dict(pid=pid,handle=row["handle"]) for pid,row in self.pids.items()
                if row.get("handle") and not row.get("closed")]
    def budgets(self):return dict(calls=len(self.calls),packets=self.packets,pid_records=len(self.pids))
    def setup_job(self,job):
        self.job=job
        self.api.create_port(self)
        self.event("iocp_port_created",handle=self.port,noninheritable=True)
        result=self.api.associate_port(job,self.port)
        self.event("iocp_association_returned",**result)
        require(result["ok"],"IOCP association failed before child creation")
    def record_snapshot(self,stage,expected,*,boundary=False,enforce=True):
        require(self.owner is not None and self.owner.job,"No owned Job for raw snapshot")
        cap=40 if boundary else 36
        require(self.owner.snapshot_count<cap,"Diagnostic snapshot budget reached")
        if boundary:require(stage in BOUNDARIES and stage not in self.boundaries,"Duplicate/unknown stop boundary")
        started=time.monotonic_ns();raw=self.api.job_snapshot(self.owner.job);finished=time.monotonic_ns()
        self.owner.snapshot_count+=1
        row=dict(stage=stage,ordinal=self.owner.snapshot_count,parent_monotonic_interval=[started,finished],
            raw_sdk_snapshot=raw,generic_total1_predicate_problem=None,predicate_evaluated=False,raw_durable=False,
            observer_open_pid_handles=len(self.outstanding()),observer_pid_handles_still_outstanding=self.outstanding(),
            termination_attempt_state=dict(self.termination),owned_child_wait_state=self.wait_state,queue_budget_state=self.budgets())
        self.snapshots.append(row)
        if boundary:self.boundaries[stage]=row["ordinal"]
        self.event("iocp_raw_job_snapshot",**row)
        row["raw_durable"]=True
        problem=sdk.job_snapshot_problem(raw,expected,int(self.owner.pi.dwProcessId))
        row.update(generic_total1_predicate_problem=problem,predicate_evaluated=True)
        if problem:self.findings.append(dict(stage=stage,ordinal=row["ordinal"],problem=problem))
        self.event("iocp_snapshot_predicate_evaluated",stage=stage,ordinal=row["ordinal"],problem=problem)
        if problem and enforce:raise ObservationStop("Strict generic counter/PID finding: "+problem)
        return row
    def start_event(self,name,**details):
        self.event(name,**details)
        if name=="abi_job_snapshot_observed":
            stage=details["stage"];expected={"configured_empty":"empty","before_resume":"assigned"}[stage]
            problem=sdk.job_snapshot_problem(details["snapshot"],expected,int(self.owner.pi.dwProcessId))
            if problem:self.findings.append(dict(stage=stage,ordinal=details["ordinal"],problem=problem))
        if name=="abi_assigned_before_resume":self.drain("after_creation_before_resume")
    def pid(self,pid,sequence,allow_open):
        if pid in self.pids:
            self.pids[pid]["all_packet_sequences_within_packet_cap"].append(sequence);return
        if len(self.pids)>=16:
            self.incomplete.append("PID metadata record cap reached");raise ObservationStop("PID metadata record cap reached")
        row=dict(pid=pid,first_packet_sequence=sequence,all_packet_sequences_within_packet_cap=[sequence],
            open_attempted=False,open_access=ACCESS,open_inherit=False,open_ok=None,open_error=None,
            handle_registered_immediately=False,handle=None,closed=False,query_outcomes=[],historical_identity_confirmed=False,
            pid_reuse_before_open_possible=True,close_outcome=None)
        self.pids[pid]=row
        if not allow_open or self.no_new_opens:
            row["not_queried_reason"]="not_queried_terminal_drain";self.incomplete.append("Late PID not opened: "+str(pid))
            self.event("iocp_pid_not_opened",record=row);return
        self.api.open_reported(pid,row)  # Registers the returned handle before any query/publication.
        self.event("iocp_pid_open_returned",record=row)
        if not row["open_ok"]:
            self.incomplete.append("Reported PID unavailable: "+str(pid));return
        try:self.api.query_reported(row["handle"],pid,self.job,outcomes=row["query_outcomes"])
        except BaseException:
            self.cleanup_event("iocp_pid_queries_partial",record=row);raise
        names=("GetProcessId","QueryFullProcessImageNameW","IsProcessInJob_exact_job","WaitForSingleObject_0","GetProcessTimes")
        complete=tuple(item["query"] for item in row["query_outcomes"])==names and all(
            item["ok"] and item["output_defined"] for item in row["query_outcomes"])
        matched=bool(row["query_outcomes"]) and row["query_outcomes"][0].get("matches_reported_pid") is True
        member=len(row["query_outcomes"])>2 and row["query_outcomes"][2]["raw_output"].get("is_member") is True
        row["same_handle_query_set_complete"]=complete and matched and member
        if not row["same_handle_query_set_complete"]:self.incomplete.append("Reported PID query uncertainty: "+str(pid))
        self.event("iocp_pid_queries_returned",record=row)
    def drain(self,phase,*,allow_open=True):
        packets=0
        for _ in range(8):
            sdk.finite_deadline(self.deadline)
            if len(self.calls)>=1024 or self.packets>=64:
                self.incomplete.append("Queue observation budget reached");raise ObservationStop("Queue observation budget reached")
            raw=self.api.queue_call(self.port)
            packet=bool(raw["ok"] or raw["raw_overlapped_value"]!=0)
            if packet:self.packets+=1;packets+=1
            no_packet=(not raw["ok"] and raw["raw_overlapped_value"]==0 and raw["error"]==258)
            row=dict(sequence=len(self.calls),phase=phase,timeout_ms=0,**raw,packet_dequeued=packet,
                number_and_key_defined=packet,message_name=MESSAGES.get(raw["raw_number_of_bytes"]) if raw["ok"] else None,
                pid_interpretation="not_interpreted_before_durable_call_record",
                drain_termination="current_empty" if no_packet else None,
                packet_budget_used=self.packets,call_budget_used=len(self.calls)+1)
            self.calls.append(row);self.event("iocp_queue_call",**row)
            if len(self.calls)>=1024:
                self.incomplete.append("Queue call budget reached");raise ObservationStop("Queue call budget reached")
            if no_packet:
                self.drain_ends.append(dict(phase=phase,reason="current_empty",sequence=row["sequence"]));return packets
            if not raw["ok"]:raise ObservationStop("Failed IOCP result retained; no PID interpretation")
            require(raw["raw_completion_key"]==COMPLETION_KEY,"Unexpected IOCP completion key")
            message,payload=raw["raw_number_of_bytes"],raw["raw_overlapped_value"]
            require(message in MESSAGES,"Unclassified Job message")
            if message in PID_MESSAGES:
                if 0<payload<=0xffffffff:
                    self.event("iocp_pid_interpretation",call_sequence=row["sequence"],pid=payload,documented_message=message)
                    self.pid(payload,row["sequence"],allow_open)
                else:
                    self.incomplete.append("Null/out-of-range PID payload")
                    self.event("iocp_pid_interpretation",call_sequence=row["sequence"],status="unusable_pid_value",raw_payload=payload)
            else:
                self.event("iocp_pid_interpretation",call_sequence=row["sequence"],status="documented_no_pid",message=message)
                require(payload==0,"Unexpected payload on documented non-PID message")
            if self.packets>=64 or len(self.calls)>=1024:
                self.incomplete.append("Queue observation budget reached");raise ObservationStop("Queue observation budget reached")
        self.drain_ends.append(dict(phase=phase,reason="batch_yield",packets=packets))
        return packets
    def close_pids(self):
        self.no_new_opens=True
        for pid,row in self.pids.items():
            if not row.get("handle") or row.get("closed"):continue
            outcome=dict(attempted=True,started_monotonic_ns=time.monotonic_ns(),ok=False,error=None)
            try:self.api.close(row["handle"]);row["closed"]=True;outcome["ok"]=True
            except BaseException as error:
                outcome["error"]=dict(error_class=type(error).__name__,error=str(error)[:512]);self.error("close_reported_pid",error)
            outcome["finished_monotonic_ns"]=time.monotonic_ns();row["close_outcome"]=outcome
            self.cleanup_event("iocp_pid_close_returned",pid=pid,handle=row["handle"],outcome=outcome)
    def close_port(self):
        if self.port and not self.port_closed:
            try:self.api.close(self.port);self.port_closed=True
            except BaseException as error:self.error("close_completion_port",error)
            self.cleanup_event("iocp_port_close_returned",handle=self.port,closed=self.port_closed)


def api_class():
    class DiagnosticKernel32(sdk.Kernel32):
        def __init__(self,config,expected):
            validate_role(config);require(not config.get("pure_fixture"),"Synthetic configuration cannot construct real SDK")
            self.config,self.expected,self.attempted,self.observer=config,expected,False,None
            require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK changed")
            sdk.layouts();observer_layouts();C=sdk.C;ptr=C.POINTER
            self.k=C.WinDLL(r"C:\Windows\System32\kernel32.dll",use_last_error=True)
            specs={
                "CreateJobObjectW":([sdk.PVOID,sdk.LPWSTR],sdk.HANDLE),
                "SetInformationJobObject":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD],sdk.BOOL),
                "QueryInformationJobObject":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD)],sdk.BOOL),
                "IsProcessInJob":([sdk.HANDLE,sdk.HANDLE,ptr(sdk.BOOL)],sdk.BOOL),
                "CreatePipe":([ptr(sdk.HANDLE),ptr(sdk.HANDLE),ptr(sdk.SECURITY_ATTRIBUTES),sdk.DWORD],sdk.BOOL),
                "SetHandleInformation":([sdk.HANDLE,sdk.DWORD,sdk.DWORD],sdk.BOOL),
                "InitializeProcThreadAttributeList":([sdk.PVOID,sdk.DWORD,sdk.DWORD,ptr(sdk.SIZE_T)],sdk.BOOL),
                "UpdateProcThreadAttribute":([sdk.PVOID,sdk.DWORD,sdk.SIZE_T,sdk.PVOID,sdk.SIZE_T,sdk.PVOID,ptr(sdk.SIZE_T)],sdk.BOOL),
                "DeleteProcThreadAttributeList":([sdk.PVOID],None),
                "CreateProcessW":([sdk.LPWSTR,ptr(sdk.WCHAR),sdk.PVOID,sdk.PVOID,sdk.BOOL,sdk.DWORD,sdk.PVOID,sdk.LPWSTR,ptr(sdk.STARTUPINFOW),ptr(sdk.PROCESS_INFORMATION)],sdk.BOOL),
                "ResumeThread":([sdk.HANDLE],sdk.DWORD),"WaitForSingleObject":([sdk.HANDLE,sdk.DWORD],sdk.DWORD),
                "GetExitCodeProcess":([sdk.HANDLE,ptr(sdk.DWORD)],sdk.BOOL),
                "TerminateProcess":([sdk.HANDLE,sdk.DWORD],sdk.BOOL),"TerminateJobObject":([sdk.HANDLE,sdk.DWORD],sdk.BOOL),
                "CloseHandle":([sdk.HANDLE],sdk.BOOL),"GetProcessId":([sdk.HANDLE],sdk.DWORD),
                "GetThreadId":([sdk.HANDLE],sdk.DWORD),"GetProcessIdOfThread":([sdk.HANDLE],sdk.DWORD),
                "QueryFullProcessImageNameW":([sdk.HANDLE,sdk.DWORD,ptr(sdk.WCHAR),ptr(sdk.DWORD)],sdk.BOOL),
                "GetProcessTimes":([sdk.HANDLE,ptr(sdk.FILETIME),ptr(sdk.FILETIME),ptr(sdk.FILETIME),ptr(sdk.FILETIME)],sdk.BOOL),
                "PeekNamedPipe":([sdk.HANDLE,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD),ptr(sdk.DWORD),ptr(sdk.DWORD)],sdk.BOOL),
                "ReadFile":([sdk.HANDLE,sdk.PVOID,sdk.DWORD,ptr(sdk.DWORD),sdk.PVOID],sdk.BOOL),
                "CreateFileW":([sdk.LPWSTR,sdk.DWORD,sdk.DWORD,ptr(sdk.SECURITY_ATTRIBUTES),sdk.DWORD,sdk.DWORD,sdk.HANDLE],sdk.HANDLE),
                "GetFileSizeEx":([sdk.HANDLE,ptr(sdk.LARGE_INTEGER)],sdk.BOOL),
                "GetFileInformationByHandleEx":([sdk.HANDLE,sdk.DWORD,sdk.PVOID,sdk.DWORD],sdk.BOOL),
                "GetFinalPathNameByHandleW":([sdk.HANDLE,ptr(sdk.WCHAR),sdk.DWORD,sdk.DWORD],sdk.DWORD),
                "CreateIoCompletionPort":([sdk.HANDLE,sdk.HANDLE,sdk.SIZE_T,sdk.DWORD],sdk.HANDLE),
                "GetQueuedCompletionStatus":([sdk.HANDLE,ptr(sdk.DWORD),ptr(sdk.SIZE_T),ptr(sdk.PVOID),sdk.DWORD],sdk.BOOL),
                "OpenProcess":([sdk.DWORD,sdk.BOOL,sdk.DWORD],sdk.HANDLE)}
            for name,(args,result) in specs.items():
                method=getattr(self.k,name);method.argtypes,method.restype=args,result
        def create_suspended(self,argv,command,environment,cwd,handles,pi,job,creation,event):
            require((argv,command,environment)==launch_argv(self.config,self.expected)
                    and Path(cwd)==Path(self.config["output"]),"Exact one overflow argv required")
            require(not self.attempted,"Diagnostic attempt already reserved; no repeat");self.attempted=True
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
        def configure_job(self,job):
            super().configure_job(job);require(self.observer is not None,"Observer not registered")
            self.observer.setup_job(job)
        def create_port(self,observer):
            start=time.monotonic_ns();sdk.C.set_last_error(0)
            observer.port=self.k.CreateIoCompletionPort(sdk.INVALID,None,0,1)
            observer.port_create=dict(started_monotonic_ns=start,finished_monotonic_ns=time.monotonic_ns(),
                ok=observer.port not in (None,0,sdk.INVALID),error=None if observer.port else sdk.C.get_last_error(),
                handle=observer.port,registered_before_other_calls=True)
            require(observer.port not in (None,0,sdk.INVALID),"CreateIoCompletionPort failed")
            require(self.k.SetHandleInformation(observer.port,1,0),"Port noninheritability failed")
        def associate_port(self,job,port):
            value=ASSOCIATE_COMPLETION_PORT(COMPLETION_KEY,port);sdk.C.set_last_error(0);start=time.monotonic_ns()
            ok=bool(self.k.SetInformationJobObject(job,7,sdk.C.byref(value),sdk.C.sizeof(value)))
            error=None if ok else sdk.C.get_last_error()
            return dict(ok=ok,error=error,started_monotonic_ns=start,finished_monotonic_ns=time.monotonic_ns(),
                        job=job,port=port,key=COMPLETION_KEY,info_class=7,raw_struct_hex=bytes(value).hex())
        def queue_call(self,port):
            number,key,payload=sdk.DWORD(),sdk.SIZE_T(),sdk.PVOID();sdk.C.set_last_error(0);start=time.monotonic_ns()
            ok=bool(self.k.GetQueuedCompletionStatus(port,sdk.C.byref(number),sdk.C.byref(key),sdk.C.byref(payload),0))
            error=None if ok else sdk.C.get_last_error()
            return dict(started_monotonic_ns=start,finished_monotonic_ns=time.monotonic_ns(),ok=ok,error=error,
                raw_number_of_bytes=int(number.value),raw_completion_key=int(key.value),raw_overlapped_value=int(payload.value or 0))
        def open_reported(self,pid,row):
            row.update(open_attempted=True,open_started_monotonic_ns=time.monotonic_ns())
            sdk.C.set_last_error(0);handle=self.k.OpenProcess(ACCESS,False,pid)
            if handle:row.update(handle=int(handle),closed=False,handle_registered_immediately=True)
            row.update(open_ok=bool(handle),open_error=None if handle else sdk.C.get_last_error(),
                       open_finished_monotonic_ns=time.monotonic_ns())
        def query_reported(self,handle,pid,job,outcomes=None):
            C=sdk.C;rows=[] if outcomes is None else outcomes
            def call(name,action,good,raw):
                sdk.finite_deadline(self.observer.deadline)
                C.set_last_error(0);start=time.monotonic_ns();value=action();ok=good(value)
                error=None if ok else C.get_last_error();end=time.monotonic_ns()
                row=dict(query=name,started_monotonic_ns=start,finished_monotonic_ns=end,ok=ok,error=error,
                         raw_output=raw(value),output_defined=ok);rows.append(row)
                sdk.finite_deadline(self.observer.deadline)
                return value,row
            value,row=call("GetProcessId",lambda:self.k.GetProcessId(handle),lambda x:x!=0,lambda x:int(x))
            row["matches_reported_pid"]=value==pid
            buffer=C.create_unicode_buffer(32768);size=sdk.DWORD(32768)
            value,row=call("QueryFullProcessImageNameW",lambda:self.k.QueryFullProcessImageNameW(handle,0,buffer,C.byref(size)),
                bool,lambda x:dict(returned_length=int(size.value),raw_utf16le_hex=bytes(buffer).hex()))
            row["output_defined"]=bool(value) and 0<size.value<32768
            image=None
            if row["output_defined"]:
                try:image=buffer[:size.value];image.encode("utf-8","strict")
                except UnicodeError:row["output_defined"]=False;image=None
            row["image_path_string"]=image  # Never opened, hashed or executed.
            member=sdk.BOOL()
            call("IsProcessInJob_exact_job",lambda:self.k.IsProcessInJob(handle,job,C.byref(member)),bool,
                 lambda x:dict(job=job,is_member=bool(member.value)))
            wait,wait_row=call("WaitForSingleObject_0",lambda:self.k.WaitForSingleObject(handle,0),lambda x:x in (0,258),lambda x:int(x))
            times=[sdk.FILETIME() for _ in range(4)]
            value,row=call("GetProcessTimes",lambda:self.k.GetProcessTimes(handle,*[C.byref(t) for t in times]),bool,
                lambda x:dict(zip(("creation_filetime","exit_filetime_raw","kernel_filetime","user_filetime"),
                                 [(int(t.high)<<32)|int(t.low) for t in times])))
            row["exit_filetime_defined_only_if_signaled"]=bool(value) and wait_row["ok"] and wait==0
            return rows
        def observed_terminate(self,job):
            require(self.observer is not None and job==self.observer.job,"Only owned diagnostic Job may terminate")
            sdk.C.set_last_error(0);start=time.monotonic_ns();ok=bool(self.k.TerminateJobObject(job,125))
            error=None if ok else sdk.C.get_last_error()
            return dict(attempted=True,return_observed=True,ok=ok,error=error,exit_code=125,
                        started_monotonic_ns=start,finished_monotonic_ns=time.monotonic_ns())
    return DiagnosticKernel32


def configuration(output,inputs):
    output=safe(output,output=True)
    return dict(schema_version=1,kind="native_own_worker_iocp_diagnostic_v1",helper=pin(__file__),
        source_basis_sha256=BASIS_SHA,sdk_sha256=q.SDK_SHA,worker_source_sha256=q.WORKER_SHA,
        executable=str(q.OWN_EXE),executable_sha256=q.OWN_EXE_SHA,build_verification_sha256=q.BUILD_VERIFICATION_SHA,
        system_dll_pins=list(q.SYSTEM_DLL_PINS.values()),seal_helper_sha256=SEALER_SHA,
        contract_sha256=CONTRACT_SHA,design_sha256=DESIGN_SHA,completion_key=COMPLETION_KEY,
        output=str(output),child_protocol=str(output/"effective-protocol.json"),
        cases=[dict(worker_mode="overflow",child_output=str(output/"execution/overflow/child"))],
        limits=LIMITS,inputs=inputs,accepted_version="0.3.11",automatic_retry=False,
        no_qualification_established=True,preparation_authorizes_execution=False)


def validate_role(config):
    q.verified_build_scope()
    require(sha(BASIS)==BASIS_SHA and sha(CONTRACT)==CONTRACT_SHA and sha(DESIGN)==DESIGN_SHA
            and sha(SEALER)==SEALER_SHA,"Frozen diagnostic source basis changed")
    require(config["schema_version"]==1 and config["kind"]=="native_own_worker_iocp_diagnostic_v1"
        and config["helper"]==pin(__file__) and config["source_basis_sha256"]==BASIS_SHA
        and config["sdk_sha256"]==q.SDK_SHA and config["worker_source_sha256"]==q.WORKER_SHA
        and config["executable"]==str(q.OWN_EXE) and config["executable_sha256"]==q.OWN_EXE_SHA
        and config["build_verification_sha256"]==q.BUILD_VERIFICATION_SHA
        and config["system_dll_pins"]==list(q.SYSTEM_DLL_PINS.values())
        and config["seal_helper_sha256"]==SEALER_SHA and config["contract_sha256"]==CONTRACT_SHA
        and config["design_sha256"]==DESIGN_SHA and config["completion_key"]==COMPLETION_KEY
        and config["limits"]==LIMITS and config["automatic_retry"] is False
        and config["no_qualification_established"] is True,"Exact one-case diagnostic role required")
    output=safe(config["output"],output=True)
    require(config["cases"]==[dict(worker_mode="overflow",child_output=str(output/"execution/overflow/child"))]
            and config["child_protocol"]==str(output/"effective-protocol.json"),"Only exact overflow output allowed")
    seen=set()
    for item in config["inputs"]:
        path=safe(item["path"]);require(str(path) not in seen,"Duplicate diagnostic input");seen.add(str(path))
        require(path.suffix.casefold()!=".pyd"
            and (path.suffix.casefold()!=".dll" or q.SYSTEM_DLL_PINS.get(str(path))==item)
            and (path.suffix.casefold()!=".exe" or path in (q.OWN_EXE,q.BASE,q.DEFAULT)),"Unapproved binary input")
    require({str(q.OWN_EXE),str(q.WORKER),str(q.SOURCE_COPY),str(q.BUILD_VERIFICATION),str(q.SDK_SOURCE),
             str(BASIS),str(SEALER),str(CONTRACT),str(DESIGN),str(Path(__file__).resolve()),*q.SYSTEM_DLL_PINS}<=seen,
            "Mandatory diagnostic input missing")
    return output


def launch_argv(config,expected):
    output=validate_role(config)
    require(len(expected)==64 and all(c in "0123456789abcdef" for c in expected),"Protocol SHA required")
    argv=[str(q.OWN_EXE),"overflow",str(output/"execution/overflow/child"),config["child_protocol"],expected]
    command=subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le"))//2+1<=32767,"Command line cap")
    return argv,command,sdk.effective_environment(output)


def capture_cleanup(owner,captures,streams):
    # Preserve the true truncated/EOF state. A temporary skip view never reads
    # more of an exhausted stream or claims that it reached EOF.
    masked={name:(dict(state,eof=True) if state["truncated"] else state) for name,state in captures.items()}
    sdk.capture_poll(owner,masked,streams)


def run_case(api,config,expected,journal,parent_end,report):
    child=safe(config["cases"][0]["child_output"],output=True);child.mkdir(parents=True)
    started=time.monotonic();end=min(started+8,parent_end-5);work_end=end-2
    observer=Observer(api,journal,end);api.observer=observer
    owner=sdk.OwnedLaunch(api,observer.start_event);observer.owner=owner
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report.update(expected_cap_trigger=False,stop_reason=None,primary_failure=None,cleanup_errors=[],captures=captures,
                  no_qualification_established=True,owned_reaped=False,owned_exit_code=None)
    sinks=ExitStack();streams={}
    def boundary(stage,expected_state):
        try:observer.record_snapshot(stage,expected_state,boundary=True,enforce=False)
        except BaseException as error:observer.error("boundary_"+stage,error)
    try:
        streams={name:sinks.enter_context((child.parent/(name+".bin")).open("xb")) for name in captures}
        argv,command,environment=launch_argv(config,expected)
        owner.start(argv,command,environment,Path(config["output"]),lambda:sdk.finite_deadline(work_end))
        observer.record_snapshot("first_running","running_or_finished")
        observer.drain("after_resume");last=time.monotonic()
        while True:
            sdk.finite_deadline(work_end);sdk.capture_poll(owner,captures,streams)
            observed=observer.drain("running_poll")
            if observed:observer.record_snapshot("after_queue_batch","running_or_finished")
            if api.wait(owner.pi.hProcess,0):
                observer.wait_state="signaled_before_expected_stop"
                raise ObservationStop("Owned worker ended before overflow cap")
            if time.monotonic()-last>=.9:
                observer.record_snapshot("running_periodic","running_or_finished");last=time.monotonic()
            time.sleep(.01)
    except BaseException as error:
        if q.expected_trigger("overflow",error,captures,False):
            report.update(expected_cap_trigger=True,stop_reason="expected_stdout_cap")
        else:
            report.update(stop_reason="strict_running_finding" if observer.findings else "work_error",
                primary_failure=dict(error_class=type(error).__name__,error=str(error)[:2048]))
    finally:
        # None of the cleanup evidence/recording steps may suppress termination.
        if owner.job:
            expected_state="running_or_finished" if owner.creation["api_attempt_reserved"] else "empty"
            boundary("before_terminate",expected_state)
            observer.termination.update(attempted=True,return_observed=False)
            observer.cleanup_event("iocp_owned_job_termination_reserved",job=owner.job,exit_code=125)
            try:observer.termination=api.observed_terminate(owner.job)
            except BaseException as error:observer.error("owned_job_termination",error)
            observer.cleanup_event("iocp_owned_job_termination_returned",outcome=observer.termination)
            boundary("after_terminate_return_before_wait","running_or_finished")
            if not (observer.termination.get("attempted") is True and observer.termination.get("return_observed") is True
                    and observer.termination.get("ok") is True):
                observer.error("owned_job_termination_outcome",ObservationStop("Owned Job termination was not observed successful"))
        if owner.pi.hProcess:
            try:
                while not api.wait(owner.pi.hProcess,0):
                    sdk.finite_deadline(end)
                    try:observer.drain("owned_reap_poll")
                    except BaseException as error:observer.error("owned_reap_queue",error)
                    try:capture_cleanup(owner,captures,streams)
                    except BaseException as error:observer.error("owned_reap_capture",error)
                    time.sleep(.005)
                observer.wait_state="signaled";report["owned_reaped"]=True
                report["owned_exit_code"]=api.exit_code(owner.pi.hProcess)
                try:observer.drain("after_owned_reap")
                except BaseException as error:observer.error("after_owned_reap_queue",error)
            except BaseException as error:observer.error("owned_reap",error)
        try:
            identity=q.marker(child/"worker-started.json")
            require(identity["pid"]==int(owner.pi.dwProcessId) and identity["mode"]=="overflow"
                    and identity["protocol_sha256"]==expected and identity["executable"]==str(q.OWN_EXE),
                    "Own worker marker identity differs")
            report["worker_identity"]=identity
        except BaseException as error:observer.error("owned_worker_marker",error)
        if owner.job:boundary("after_owned_reap_observer_handles_held","finished")
        observer.close_pids()
        if observer.port:
            try:
                while True:
                    observer.drain("final_no_new_opens",allow_open=False)
                    if observer.drain_ends and observer.drain_ends[-1]["reason"]=="current_empty":break
            except BaseException as error:observer.error("terminal_queue_drain",error)
        if owner.job:boundary("after_observer_pid_release_before_job_close","finished")
        try:owner.cleanup(end)
        except BaseException as error:observer.error("owned_cleanup_exception",error)
        finally:observer.close_port()
        try:
            for stream in streams.values():stream.flush();os.fsync(stream.fileno())
        except BaseException as error:observer.error("capture_flush",error)
        finally:
            try:sinks.close()
            except BaseException as error:observer.error("capture_close",error)
        report.update(termination_call_outcome=observer.termination,
            first_strict_counter_problem=observer.findings[0] if observer.findings else None,
            strict_counter_findings=observer.findings,stop_boundary_snapshot_references=observer.boundaries,
            raw_snapshots=observer.snapshots,queue_calls=observer.calls,queue_call_and_packet_counts=observer.budgets(),
            pid_metadata_records=list(observer.pids.values()),pid_metadata_record_count=len(observer.pids),
            drain_end_reasons=observer.drain_ends,outstanding_handles=observer.outstanding(),observer_errors=observer.errors,
            observation_incomplete_reasons=observer.incomplete,port_handle=observer.port,port_closed=observer.port_closed,
            port_create=getattr(observer,"port_create",None),cleanup_errors=owner.cleanup_errors,
            resumption=owner.resumption_record(),whole_case_seconds=time.monotonic()-started)
        complete=(set(observer.boundaries)==set(BOUNDARIES) and len(observer.snapshots)>=4
            and all(row["raw_durable"] and row["predicate_evaluated"] for row in observer.snapshots)
            and not observer.errors and not observer.incomplete and not observer.outstanding() and observer.port_closed
            and not owner.cleanup_errors and report["whole_case_seconds"]<=8 and owner.reaped
            and owner.resumed and any(row["stage"]=="first_running" for row in observer.snapshots)
            and observer.termination.get("ok") is True and observer.termination.get("return_observed") is True
            and report.get("worker_identity") is not None and report["owned_reaped"] and report["owned_exit_code"]==125)
        report["diagnostic_completeness"]=complete
        report["terminal_outcome"]=("completed_bounded_diagnostic_observations_NOT_qualification" if complete and not observer.findings
                                    and report["expected_cap_trigger"] and not report["primary_failure"] else
                                    "failed_or_incomplete_diagnostic_observations_NOT_qualification")
        write_new(child.parent/"diagnostic-report.json",report)
        journal.append("iocp_case_terminal",outcome=report["terminal_outcome"],report=pin(child.parent/"diagnostic-report.json"))
    return report


def load_sealer():
    require(sha(SEALER)==SEALER_SHA,"Diagnostic sealer changed")
    spec=util.spec_from_file_location("owned_iocp_status_sealer",SEALER)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make_sealer(sdk)


def collect_inputs():
    require(sha(q.PROTOCOL)==PRIOR_PROTOCOL_SHA and sha(FAILURE_PROOF)==FAILURE_PROOF_SHA,
            "Consumed qualification/failure proof changed")
    prior=json.loads(q.PROTOCOL.read_bytes());proof=json.loads(FAILURE_PROOF.read_bytes())
    require(len(prior["inputs"])==135,"Prior input closure differs")
    files=[Path(item["path"]) for item in prior["inputs"]]
    for item in prior["inputs"]:require(pin(item["path"])==item,"Consumed qualification input changed")
    require(len(proof["outputs"])==17,"Consumed failure file count differs")
    for item in proof["outputs"]:
        require(pin(item["path"])==item,"Consumed qualification output changed");files.append(Path(item["path"]))
    files.extend((Path(__file__).resolve(),BASIS,q.PROTOCOL,FAILURE_PROOF,
        HERE/"HARMLESS-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.md",
        HERE/"HARMLESS-NATIVE-QUALIFICATION-ROOT-DECISION-v1.json",CONTRACT,DESIGN,SEALER,
        HERE/"IOCP-STATUS-SEALER-PURE-PROOF-v1.json",
        HERE/"NATIVE-JOB-IOCP-PURE-CHECKS-v1.json",HERE/"check_native_job_iocp_v1.py",
        HERE/"NATIVE-JOB-IOCP-PURE-CHECKS-v2.json",HERE/"check_native_job_iocp_v2.py",
        HERE/"IOCP-METADATA-ADVERSARIAL-PROOF-v1.json",HERE/"IOCP-METADATA-COMPONENT-PROOF-v1.json",
        HERE/"check_iocp_metadata_adversarial_v1.py",HERE/"NATIVE-JOB-IOCP-CLEANUP-SUPPLEMENT-v1.json",
        HERE/"check_native_job_iocp_cleanup_v1.py",HERE/"NATIVE-JOB-IOCP-PREPARATION-FAILURE-v1.json",
        HERE/"diagnose_native_job_iocp_v1_before_preparation_fix.py"))
    for path in (Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um\ioapiset.h"),
                 Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um\processthreadsapi.h"),
                 Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\shared\basetsd.h")):
        files.append(path)
    return list({str(path):pin(path) for path in files}.values())


def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"Diagnostic attempt consumed; no restart")
    require(metadata.version("asof-target-agents")=="0.3.11" and Path(sys.executable)==q.DEFAULT,
            "Accepted dependency-free installed parent required")
    started=time.monotonic();end=started+60;api=None;journal=None;leases=[];failure=None
    reservation=dict(owned=False,journal_reserved=False)
    report=dict(schema_version=1,status="failed",automatic_retry=False,no_qualification_established=True,
        attempt_reserved=False,case_return_observed=False,diagnostic={},source_contract_sha256=CONTRACT_SHA,finalization_errors=[])
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        journal.append("iocp_diagnostic_parent_reserved",protocol_sha256=expected,limits=LIMITS,
                       original_sdk_disabled=True,qualification_established=False)
        write_new(output/"effective-protocol.json",config)
        require(sha(output/"effective-protocol.json")==expected,"Child protocol archive differs")
        api=api_class()(config,expected)
        for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
            sdk.finite_deadline(end-5);api.read_lease(item,end-5,leases)
        journal.append("iocp_single_case_reserved",mode="overflow");report["attempt_reserved"]=True
        run_case(api,config,expected,journal,end,report["diagnostic"]);report["case_return_observed"]=True
        diagnostic=report["diagnostic"]
        if diagnostic["terminal_outcome"]!="completed_bounded_diagnostic_observations_NOT_qualification":
            raise ObservationStop("Negative/incomplete diagnostic; strict counter findings remain failures")
        report["status"]="diagnostic_observations_retained_not_qualification"
    except BaseException as error:
        failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
    finally:
        require(reservation["owned"],"No exclusive diagnostic output ownership")
        try:
            if api:
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    record=api.read_lease(item,end,leases)
                    record["final_recheck_close_attempted"]=True
                    try:
                        api.close(record["handle"]);record["closed"]=True
                        record["final_recheck_close_return_observed"]=True
                    except BaseException as error:
                        detail=dict(phase="final_input_recheck_close",error_class=type(error).__name__,error=str(error)[:512])
                        record["cleanup_errors"].append(detail);record["final_recheck_close_return_observed"]=False
                        report["finalization_errors"].append(dict(path=record["path"],handle=record["handle"],**detail))
                        raise
            sdk.finite_deadline(end)
        except BaseException as error:
            detail=dict(phase="final_input_recheck_or_deadline",error_class=type(error).__name__,error=str(error)[:2048])
            report["finalization_errors"].append(detail);failure=failure or detail
        try:
            if failure:
                report.update(status="failed",failure=failure)
                if not (output/"failure.json").exists():write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
            try:
                if journal:journal.append("iocp_diagnostic_parent_terminal",status=report["status"],failure=failure)
            finally:
                if journal:journal.close()
            report["lease_ownership"]=leases
            report["elapsed_before_early_receipt_seconds"]=time.monotonic()-started
            write_new(output/"parent-report.json",report);sdk.finite_deadline(end)
            outputs={}
            for path in sorted(output.rglob("*")):
                sdk.finite_deadline(end)
                if path.is_file():outputs[path.relative_to(output).as_posix()]={key:pin(path)[key] for key in ("bytes","sha256")}
            write_new(output/"receipt.json",dict(schema_version=1,status=report["status"],protocol_sha256=expected,
                outputs=outputs,no_qualification_established=True,failure_veto="All failure markers or missing/failed seal veto"))
        except BaseException as error:
            failure=failure or dict(error_class=type(error).__name__,error=str(error)[:2048]);report.update(status="failed",failure=failure)
            if not (output/"failure.json").exists():
                try:write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
                except BaseException:pass
        finally:
            terminal=load_sealer()(output,api,leases,failure,report["status"],started,end)
            report["terminal_status"]=terminal["status"];report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK flag changed")
    return report


def prepare():
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and metadata.version("asof-target-agents")=="0.3.11" and Path(sys.executable)==q.DEFAULT,
            "Accepted Windows -I -B parent required")
    require(not PROTOCOL.exists(),"Preparation exists; no overwrite")
    proof=json.loads(PURE.read_bytes())
    require(proof["status"]=="passed" and proof["helper_sha256"]==sha(__file__)
            and proof["actual_children"]==0 and proof["real_sdk_constructions"]==0,"Fresh pure checks required")
    tree=ast.parse(Path(__file__).read_bytes())
    components=json.loads((HERE/"IOCP-METADATA-COMPONENT-PROOF-v1.json").read_bytes())["tested_components"]
    for name in ("Observer","query_reported"):
        node=next(node for node in ast.walk(tree) if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name==name)
        digest=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
        require(digest==components[name]["normalized_AST_sha256"],"Metadata component differs from independent pure proof")
    inputs=collect_inputs()+[pin(PURE),pin(CHECKER)]
    output=safe(ROOT/"data/cache"/("r09-native-job-iocp-diagnostic-v1-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Exclusive diagnostic output exists")
    config=configuration(output,inputs);validate_role(config)
    with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(status="prepared_zero_sdk_or_child",protocol_sha256=sha(PROTOCOL),helper_sha256=sha(__file__),
                         inputs=len(inputs),output=str(output))))


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--execute":
        q.guard();expected=sys.argv[2];require(sha(PROTOCOL)==expected,"Exact separately reviewed protocol required")
        result=execute(json.loads(PROTOCOL.read_bytes()),expected)
        print(json.dumps(dict(status=result["status"],terminal_status=result["terminal_status"],output=result["terminal_seal"]["path"])))
        raise SystemExit(0 if result["status"]=="diagnostic_observations_retained_not_qualification"
                         and result["terminal_status"]=="IOCP_diagnostic_observations_retained_not_qualification" else 1)
    else:raise SystemExit("Prepare and obtain exact peer/root decision before one --execute SHA256")

