"""Prospective trusted-platform ABI parent v1; source/pure only, build-unbound.

Existing typed child only: --abi RUNTIME CHILD_OUTPUT. Original SDK gates remain
False; no prepare_config, compiler, backend/registry/model/vocabulary/grammar path.
Authority, configuration, collection and preparation reject until a separately versioned binding.
The preserved execute body is unreachable through this draft. No dispatch permission is created.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import sys
import subprocess  # Windows list2cmdline only; never Popen.
import time
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASIS=HERE/"qualify_detached_native_worker_v1.py"
BASIS_SHA="6be0634f9bc9ea89eff1e54cbb963c355853eacc9ad9bbe63496b2f1aa50fea9"
def sha(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
if sha(BASIS)!=BASIS_SHA:raise RuntimeError("Detached qualifier source basis changed")
spec=util.spec_from_file_location("qualified_detached_basis_for_fixed_abi",BASIS)
q=util.module_from_spec(spec);spec.loader.exec_module(q)
sdk=q.load_sdk()  # Declaration import only; original Kernel32 constructor stays disabled.
safe,pin,canonical,write_new,require=q.safe,q.pin,q.canonical,q.write_new,q.require
SDK_SHA="3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
QUALIFICATION=HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json"
QUALIFICATION_SHA="7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961"
EXE=None  # Deliberately no future executable/build binding.
EXE_SHA=None
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
PROTOCOL=None
EXECUTION_AUTHORIZED=False
CONTRACT=HERE/"TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json"
CONTRACT_SHA="5d7b30f66c86abd5b7c1c5d0aed6389986ff2cf900e739ca5fc475125e54ccf7"
TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
POLICY_SOURCE=HERE/"trusted_system32_module_policy_v1.py"
POLICY_SOURCE_SHA="77e39b3bb82fb83049aba9956da0251b4a8d914f167dc6d6512d554ad7bfb3a8"
POLICY_ID="trusted-System32-platform-v1"
POLICY_SHA="807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589"
TERMINAL_POLICY=dict(capture_drain_seconds=0.25,maximum_capture_polls=64,
    physical_pipe_EOF_is_not_child_exit=True,unknown_creation_is_not_final=True,
    skip_new_observations_and_input_rechecks_after_interruption=True,late_returned_bytes_retained=True)
LIMITS=dict(parent_seconds=60,child_seconds=30,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=4194304,row_bytes=65536)
RUNTIME_EXPECTED={
    "libomp.dll":dict(bytes=768000,sha256="a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c"),
    "ggml-base.dll":dict(bytes=803840,sha256="84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3"),
    "ggml.dll":dict(bytes=78848,sha256="2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba"),
    "llama.dll":dict(bytes=3581952,sha256="166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d")}


def authority():
    raise RuntimeError("Unbound trusted-platform ABI source: no verified future build/executable/runtime authority")


def policy_matcher():
    require(sha(POLICY_SOURCE)==POLICY_SOURCE_SHA,"Frozen mathematical module policy changed")
    spec=util.spec_from_file_location("trusted_platform_ABI_pure_policy_v1",POLICY_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.POLICY_ID==POLICY_ID and module.POLICY_SHA256==POLICY_SHA,"Policy semantic fingerprint differs")
    return module



def terminal_observer():
    require(sha(TERMINAL_SOURCE)==TERMINAL_SHA,"Terminal observation component changed")
    spec=util.spec_from_file_location("fixed_ABI_terminal_observation_v3",TERMINAL_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.CAPTURE_DRAIN_SECONDS==TERMINAL_POLICY["capture_drain_seconds"]
            and module.MAX_CAPTURE_POLLS==TERMINAL_POLICY["maximum_capture_polls"],
            "Terminal observation policy differs")
    return module.observe_terminal


def api_class():
    class FixedABIKernel32(sdk.Kernel32):
        def __init__(self,config,expected):
            validate_role(config)
            require(not config.get("pure_fixture"),"Synthetic ABI configuration cannot bind real SDK")
            require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK execution gate changed")
            self.config,self.expected,self.attempted=config,expected,False
            sdk.layouts();C=sdk.C;ptr=C.POINTER
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
                "GetFinalPathNameByHandleW":([sdk.HANDLE,ptr(sdk.WCHAR),sdk.DWORD,sdk.DWORD],sdk.DWORD)}
            for name,(args,result) in specs.items():
                method=getattr(self.k,name);method.argtypes,method.restype=args,result
        def create_suspended(self,argv,command,environment,cwd,handles,pi,job,creation,event):
            validate_role(self.config)
            require((argv,command)==abi_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child")
                    and environment==sdk.effective_environment(Path(self.config["output"]))
                    and Path(cwd)==Path(self.config["output"]),"Exact detached ABI-only launch required")
            require(not self.attempted,"ABI attempt already reserved; no repeat");self.attempted=True
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
    return FixedABIKernel32


def exact(actual,expected):
    """Compare JSON structures without bool/int or field-set coercion."""
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):
        return set(actual)==set(expected) and all(exact(actual[key],value) for key,value in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected) and all(exact(a,b) for a,b in zip(actual,expected))
    return actual==expected


def json_value(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,"Duplicate ABI JSON key");result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(RuntimeError("Nonfinite ABI JSON")))


def runtime_pins():
    return {str(RUNTIME/name):dict(path=str(RUNTIME/name),**value) for name,value in RUNTIME_EXPECTED.items()}


def validate_modules(rows):
    require(EXE is not None,"Unbound ABI context is not an approved self executable")
    return policy_matcher().match_modules(rows,expected_self=str(EXE),expected_runtime=str(RUNTIME))



def validate_child_rows(rows,*,contract,expected_self,expected_runtime):
    """Pure complete-wire validation using externally prevalidated fixed native context.

    Context identity must come from live original-path native leases in a future
    qualified parent, never from child-supplied verified flags or platform paths.
    """
    require(type(rows) is list and len(rows)==5,"ABI row count differs")
    require([row.get("event") if type(row) is dict else None for row in rows]==contract["child_artifacts"]["result_events"],
            "ABI event sequence differs")
    require(exact(rows[0],dict(event="before_explicit_required_OpenMP_dependency_load",dependency_native_initialization_possible=True)),
            "OpenMP initialization row differs")
    require(set(rows[1])=={"event","modules","layouts","module_policy_id","module_policy_sha256"} and exact(rows[1]["layouts"],contract["expected_layouts"]),
            "Compiled x64 layout fields/types/offsets differ")
    require(type(rows[1]["module_policy_id"]) is str and rows[1]["module_policy_id"]==POLICY_ID
            and type(rows[1]["module_policy_sha256"]) is str and rows[1]["module_policy_sha256"]==POLICY_SHA,
            "Compiled module policy identifier/fingerprint differs")
    classified=policy_matcher().match_modules(rows[1]["modules"],expected_self=expected_self,expected_runtime=expected_runtime)
    observed=rows[2];require(set(observed)=={"event","version","defaults","no_backend_or_model_call_so_far"},"Typed observation fields differ")
    version=observed["version"]
    require(type(version) is str and 1<=len(version)<=255 and all(32<=ord(char)<=126 for char in version),"Invalid first ABI version observation")
    require(exact(observed["defaults"],contract["expected_defaults"])
            and observed["no_backend_or_model_call_so_far"] is True,"Typed defaults/scope differ")
    require(exact(rows[3],dict(event="abi_observations_returned",version_expected_previously_known=False,
        backend_init_called=False,registry_called=False,model_called=False,
        scope="typed version/defaults observation; independent ABI acceptance pending")),"ABI explicit-call scope differs")
    require(set(rows[4])=={"event","mode","elapsed_ms","parent_qualification_required"}
            and rows[4]["mode"]=="--abi" and type(rows[4]["elapsed_ms"]) is int
            and 0<=rows[4]["elapsed_ms"]<=30000 and rows[4]["parent_qualification_required"] is True,
            "ABI completion/time scope differs")
    return dict(version=version,version_expected_previously_known=False,defaults=observed["defaults"],
        layouts=rows[1]["layouts"],raw_modules=rows[1]["modules"],module_classification=classified,result_rows=5,
        module_policy_id=POLICY_ID,module_policy_sha256=POLICY_SHA,
        independent_ABI_acceptance="pending",scientific_validation="not_established",
        module_inventory_scope="Reported before explicit version/default calls; trusted platform context, not image authentication or lifetime attestation")



def validate_child_artifacts(child,config=None):
    """Strict data-only validator; no DLL, process, model or archived code call."""
    contract=authority();child=safe(child,output=True)
    require({path.name for path in child.iterdir()}=={"attempt.json","result.jsonl"},"Unexpected/incomplete ABI child files")
    attempt,result=safe(child/"attempt.json",output=True),safe(child/"result.jsonl",output=True)
    require(attempt.is_file() and result.is_file(),"ABI artifacts must be regular non-reparse files")
    require(0<attempt.stat().st_size<=4096 and 0<result.stat().st_size<=4194304,"ABI child file cap")
    require(exact(json_value(attempt.read_bytes()),contract["child_artifacts"]["exact_attempt_claim"]),"ABI child attempt claim")
    raw=result.read_bytes();require(raw.endswith(b"\n"),"Unterminated ABI result")
    lines=raw.split(b"\n")[:-1];require(len(lines)==5 and all(0<len(line)<=65536 for line in lines),"ABI row count/cap")
    rows=[json_value(line) for line in lines]

    require(EXE is not None,"Unbound ABI executable context")
    return validate_child_rows(rows,contract=contract,expected_self=str(EXE),expected_runtime=str(RUNTIME))



def abi_argv(exe,runtime,child):
    """Same Windows formatting bounds, independently bound to this new own EXE."""
    argv=[str(safe(exe)),"--abi",str(safe(runtime)),str(safe(child,output=True))]
    require(Path(argv[0])==EXE and Path(argv[2])==RUNTIME and len(argv)==4,
            "Exact new ABI-only executable/runtime/argv required")
    require(all("\0" not in value for value in argv),"NUL argv")
    command=subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le"))//2+1<=32767,"Command line cap")
    return argv,command


def configuration(output,inputs):
    authority()  # Always fails: no executable, closure, output or dispatch is authorized.



def validate_role(config):
    authority()  # Always fails: no executable, closure, output or dispatch is authorized.



def collect_inputs():
    authority()  # Always fails: no executable, closure, output or dispatch is authorized.



def prepare():
    authority()  # Always fails: no executable, closure, output or dispatch is authorized.



def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"ABI output consumed; never restart")
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Accepted installed -I -B ABI parent required")
    started=time.monotonic();parent_end=started+60;child=output/"execution/child"
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;owner=None;leases=[]
    sinks=ExitStack();failure=None;failure_object=None;child_start=None;child_end=None;interrupted=False
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(schema_version=1,status="failed",automatic_retry=False,captures=captures,finalization_errors=[],
        parent_GGUF_reads=0,model_paths_supplied_to_child=False,explicit_bridge_call_policy=dict(
            llama_version=1,llama_model_default_params=1,model_API=0,vocabulary_API=0,backend_init_API=0,
            GGML_registry_API=0,tokenizer_API=0,grammar_API=0),counters_instrumented=False,
        dependency_initializers_may_have_effects=True,attempt_reserved=False,call_return_observed=False)
    def event(name,**details):journal.append(name,**details)
    def note_interruption(error,phase):
        nonlocal interrupted
        if isinstance(error,(KeyboardInterrupt,SystemExit)):
            interrupted=True
            report.setdefault("interruptions",[]).append(dict(phase=phase,error_class=type(error).__name__,identity_checked=True))
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        event("detached_ABI_attempt_reserved",protocol_sha256=expected,limits=LIMITS)
        report["attempt_reserved"]=True
        child.mkdir();write_new(output/"effective-protocol.json",config)
        require(sha(output/"effective-protocol.json")==expected,"ABI protocol archive differs")
        api=api_class()(config,expected)
        for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
            sdk.finite_deadline(parent_end-5);api.read_lease(item,parent_end-5,leases)
        owner=sdk.OwnedLaunch(api,event)
        streams={name:sinks.enter_context((output/(name+".bin")).open("xb")) for name in captures}
        child_start=time.monotonic();child_end=min(child_start+30,parent_end-5)
        check=lambda:sdk.finite_deadline(child_end-2)
        owner.start(config["argv"],config["command_line"],config["environment"],output,check)
        owner.observe_job("running_first","running_or_finished");last=time.monotonic()
        while True:
            check();sdk.capture_poll(owner,captures,streams)
            if api.wait(owner.pi.hProcess,0):break
            if time.monotonic()-last>=.9:owner.observe_job("running_periodic","running_or_finished");last=time.monotonic()
            time.sleep(.01)
        report["returncode"]=api.exit_code(owner.pi.hProcess);report["call_return_observed"]=True
        require(report["returncode"]==0,"ABI child failed")
    except BaseException as error:
        failure_object=error;failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
        note_interruption(error,"execution")
    finally:
        if not reservation["owned"]:raise failure_object or RuntimeError("No exclusive ABI output ownership")
        if owner:
            # Preserve the original execution failure, then observe still-open
            # owned handles independently before unchanged Owner cleanup.
            try:
                if interrupted:
                    terminal=dict(status="not_attempted_due_to_preexisting_interruption",complete=False,
                        interrupted=True,exit_observed=False,scope="skipped_due_to_interruption",
                        physical_pipe_EOF_does_not_establish_child_exit=True,observations=dict(
                            job_snapshot=dict(status="not_attempted",reason="Preexisting interruption"),
                            memory_limits_and_peaks=dict(status="not_attempted",reason="Preexisting interruption")),errors=[])
                    report["terminal_observation"]=terminal;report["terminal_observation_errors"]=terminal["errors"]
                else:
                    terminal=terminal_observer()(owner,report,captures,locals().get("streams",{}),
                        sdk=sdk,event=event,work_deadline=min((child_end or parent_end)-2,parent_end-5),
                        drain_seconds=TERMINAL_POLICY["capture_drain_seconds"])
                if terminal.get("interrupted") is True:
                    interrupted=True;report["interrupted_cleanup_only"]=True
                observed=terminal["observations"]
                snapshot=observed["job_snapshot"]
                if terminal["exit_observed"] and snapshot.get("return_observed"):
                    report["final_job_snapshot"]=snapshot["raw"]
                peaks=observed["memory_limits_and_peaks"]
                if peaks.get("return_observed"):report["memory_limits_and_peaks"]=peaks["value"]
                if not terminal["complete"] and failure is None:
                    failure=dict(error_class="TerminalObservationIncomplete",error="See independent terminal outcomes/errors")
            except BaseException as error:
                detail=dict(phase="terminal_observation_unexpected_error",error_class=type(error).__name__,error=str(error)[:512])
                report["finalization_errors"].append(detail);failure=failure or detail
                note_interruption(error,"terminal_observation_binding_or_call")
            if failure is None:
                try:
                    require(report["call_return_observed"] and report["returncode"]==0,"No successful observed ABI exit")
                    report["observations"]=validate_child_artifacts(child,config)
                    report["status"]="ABI_observations_retained_independent_qualification_pending"
                except BaseException as error:
                    failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
                    note_interruption(error,"child_artifact_validation")
            try:owner.cleanup(min(child_end or parent_end,parent_end))
            except BaseException as error:
                report["owned_cleanup_exception"]=dict(error_class=type(error).__name__,error=str(error)[:512])
                failure=failure or report["owned_cleanup_exception"]
                note_interruption(error,"owned_cleanup")
            if any(row.get("error_class") in ("KeyboardInterrupt","SystemExit") for row in owner.cleanup_errors):
                interrupted=True;report["interruption_recorded_by_unchanged_cleanup_metadata"]=True
            report.update(reaped=owner.reaped,resumption=owner.resumption_record(),cleanup_errors=owner.cleanup_errors)
            if (not owner.reaped or owner.cleanup_errors) and failure is None:
                failure=dict(error_class="OwnedCleanupFailure",error="See retained owned cleanup")
        try:
            try:
                for stream in locals().get("streams",{}).values():stream.flush();os.fsync(stream.fileno())
            finally:sinks.close()
            report["child_full_process_elapsed_seconds"]=None if child_start is None else time.monotonic()-child_start
            require(child_start is None or report["child_full_process_elapsed_seconds"]<=30,"ABI child including cleanup exceeded30s")
            if api and interrupted:
                report["final_input_recheck"]=dict(status="skipped_due_to_interruption",new_read_leases=0,
                    new_eligibility_claim=False,original_lease_cleanup_still_required=True)
            elif api:
                report["final_input_recheck"]=dict(status="in_progress",new_read_leases=0,closed_recheck_leases=0,outcomes=[])
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    report["final_input_recheck"]["new_read_leases"]+=1
                    outcome=dict(path=item["path"],read_lease_reserved=True,return_observed=False,close_return_observed=False)
                    report["final_input_recheck"]["outcomes"].append(outcome)
                    record=api.read_lease(item,parent_end,leases);outcome.update(return_observed=True,handle=record["handle"])
                    record["final_recheck_close_attempted"]=True
                    try:
                        api.close(record["handle"]);record["closed"]=True;record["final_recheck_close_return_observed"]=True
                        outcome["close_return_observed"]=True;report["final_input_recheck"]["closed_recheck_leases"]+=1
                    except BaseException as error:
                        detail=dict(phase="final_input_recheck_close",error_class=type(error).__name__,error=str(error)[:512])
                        record["cleanup_errors"].append(detail);record["final_recheck_close_return_observed"]=False
                        outcome["close_error"]=detail
                        report["finalization_errors"].append(dict(path=record["path"],handle=record["handle"],**detail));raise
                report["final_input_recheck"]["status"]="completed"
            else:
                report["final_input_recheck"]=dict(status="not_attempted",reason="No SDK API instance",new_read_leases=0)
            sdk.finite_deadline(parent_end)
        except BaseException as error:
            detail=dict(phase="final_input_recheck_or_cleanup",error_class=type(error).__name__,error=str(error)[:2048])
            report["finalization_errors"].append(detail);failure=failure or detail
            note_interruption(error,"final_input_recheck_or_cleanup")
            recheck=report.setdefault("final_input_recheck",dict(status="not_attempted",new_read_leases=0))
            if recheck["status"]=="in_progress":
                recheck.update(status="interrupted" if isinstance(error,(KeyboardInterrupt,SystemExit)) else "failed",error=detail)
            elif recheck["status"]=="not_attempted":recheck["reason"]="Earlier finalization failure prevented input recheck"
        try:
            if failure:
                report.update(status="failed",failure=failure)
                if not (output/"failure.json").exists():write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
            try:
                if journal:event("detached_ABI_terminal",status=report["status"],failure=failure)
            finally:
                if journal:journal.close()
            report["lease_ownership"]=leases;report["elapsed_before_early_receipt_seconds"]=time.monotonic()-started
            write_new(output/"parent-report.json",report);sdk.finite_deadline(parent_end)
            outputs={}
            for path in sorted(output.rglob("*")):
                sdk.finite_deadline(parent_end)
                if path.is_file():outputs[path.relative_to(output).as_posix()]={key:pin(path)[key] for key in ("bytes","sha256")}
            write_new(output/"receipt.json",dict(schema_version=1,status=report["status"],outputs=outputs,
                protocol_sha256=expected,failure_veto="Every authoritative failure marker or missing/failed terminal seal vetoes"))
            sdk.finite_deadline(parent_end)
        except BaseException as error:
            detail=dict(phase="terminal_publication",error_class=type(error).__name__,error=str(error)[:512])
            report["finalization_errors"].append(detail);failure=failure or detail
            try:write_new(output/"terminal-publication-error.json",dict(authoritative=True,automatic_retry=False,
                publication_error=detail,primary_failure=failure,finalization_errors=report["finalization_errors"]))
            except BaseException:pass
            if not (output/"failure.json").exists():
                try:write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
                except BaseException:pass
        finally:
            terminal=sdk.seal_post_lease_cleanup(output,api,leases,failure,report["status"],started,parent_end)
            report["status"]=terminal["status"];report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Qualified detached SDK gate changed")
    return report


if __name__=="__main__":
    raise SystemExit("Source/pure-only unbound draft; no prepare or execute command is available")

