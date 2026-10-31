"""Version-two qualification of the frozen SDK launcher, harmless Python only.

The original SDK constructor/execute_draft remain disabled. This module exposes
no ABI executable, target DLL, model, tokenizer, network or fallback launcher.
Prepare and review the exact protocol before the once-only --execute command.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import subprocess  # list2cmdline only
import sys
import time
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SDK_SOURCE = HERE / "abi_parent_launch_draft_v3.py"
SDK_SHA = "c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4"
SDK_DESIGN_SHA = "75b41cf2e60546f44626c057a0a278a29ff05066642a64e567aa6e492520af33"
SDK_PEER_SHA = "d6e327534a1eaf11534999814e896698d9ba86e91ea14f91701ab010d033d89b"
WORKER = HERE / "harmless_launch_worker.py"
WORKER_SHA = "dc388b9a83d11d76ed30403658ee31f8cbf91276ffeafca1b6f91f9b49eb9811"
BASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
BASE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"
PREVIOUS = HERE.parent / "recovery-step9-generation-contract-20261028"
DEFAULT = ROOT / "data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe"
PROTOCOL = HERE / "HARMLESS-LAUNCHER-QUALIFICATION-PROTOCOL-v2.json"
SEALER = HERE / "harmless_launch_seal_v2.py"
SEALER_SHA = "4cc94dd9ab5940f4f5e303d4c41ffbbb8d5032103eafb139113133d44cbb1dcb"
PURE = HERE / "HARMLESS-LAUNCHER-PURE-CHECKS-v2.json"
MODES = ("resources", "overflow", "sleep", "suspended_abort")
LIMITS = dict(parent_seconds=60, case_seconds=8, cleanup_reserve_seconds=2,
              finalization_reserve_seconds=5, process_commit_bytes=268435456,
              job_commit_bytes=268435456, active_processes=1, maximum_children=4,
              stream_bytes=65536, maximum_job_pids=16, maximum_snapshots_per_case=40)
_SDK = None


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def safe(path, *, output=False):
    path = Path(path).absolute()
    require(path.drive.casefold() != "e:" and path.suffix.casefold() != ".gguf"
            and "\\data\\benchmark\\" not in str(path).casefold(), "Protected payload forbidden")
    if output:
        base = ROOT / "data/cache"
        require(path.is_relative_to(base) and path.resolve().is_relative_to(base.resolve()), "Output outside cache")
    for part in (path, *path.parents):
        try:
            status = part.lstat()
        except FileNotFoundError:
            continue
        require(not part.is_symlink() and not getattr(status, "st_file_attributes", 0) & 0x400,
                "Reparse ancestry forbidden")
    return path


def pin(path):
    path = safe(path)
    require(path.stat().st_size <= 128*1024**2, "Input file cap")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def write_new(path, value):
    with safe(path, output=True).open("xb") as stream:
        stream.write(canonical(value)+b"\n");stream.flush();os.fsync(stream.fileno())


def load_sdk():
    global _SDK
    require(pin(SDK_SOURCE)["sha256"] == SDK_SHA, "Frozen SDK source changed")
    if _SDK is None:
        spec = util.spec_from_file_location("frozen_disabled_launcher_sdk_for_harmless", SDK_SOURCE)
        module = util.module_from_spec(spec);spec.loader.exec_module(module);_SDK = module
    require(_SDK.NATIVE_EXECUTION_ENABLED is False, "Original draft must stay disabled")
    return _SDK


def load_sealer(sdk):
    require(pin(SEALER)["sha256"]==SEALER_SHA,"Qualification sealer changed")
    spec=util.spec_from_file_location("owned_harmless_status_sealer",SEALER)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make_sealer(sdk)


def cases(output):
    return [dict(worker_mode=mode, child_output=str(output/"execution"/mode/"child")) for mode in MODES]


def configuration(output, inputs):
    output = safe(output, output=True)
    return dict(schema_version=1, kind="harmless_sdk_launch_qualification_v1", helper=pin(__file__),
        sdk_sha256=SDK_SHA, seal_helper_sha256=SEALER_SHA, worker_sha256=WORKER_SHA, executable=str(BASE), base_sha256=BASE_SHA,
        output=str(output), child_protocol=str(output/"effective-protocol.json"), cases=cases(output),
        limits=LIMITS, inputs=inputs, accepted_version="0.3.11", no_target_execution=True,
        automatic_retry=False, preparation_only=True)


def validate_role(config):
    require(type(config) is dict and config["kind"] == "harmless_sdk_launch_qualification_v1"
        and config["schema_version"] == 1 and config["sdk_sha256"] == SDK_SHA
        and config["seal_helper_sha256"] == SEALER_SHA and pin(SEALER)["sha256"] == SEALER_SHA
        and config["worker_sha256"] == WORKER_SHA and config["executable"] == str(BASE)
        and config["base_sha256"] == BASE_SHA and config["limits"] == LIMITS
        and config["no_target_execution"] is True and config["automatic_retry"] is False,
        "Exact harmless qualification role required")
    output = safe(config["output"], output=True)
    require(config["cases"] == cases(output) and config["child_protocol"] == str(output/"effective-protocol.json"),
            "Fixed four harmless cases/child protocol required")
    require(config["helper"] == pin(__file__) and pin(WORKER)["sha256"] == WORKER_SHA
            and pin(BASE)["sha256"] == BASE_SHA, "Pinned harmless source/base changed")
    seen=set()
    for item in config["inputs"]:
        path=safe(item["path"])
        require(str(path) not in seen, "Duplicate input pin");seen.add(str(path))
        require(path.suffix.casefold() not in (".dll", ".pyd") and
                (path.suffix.casefold() != ".exe" or path in (BASE, DEFAULT)),
                "No target executable/library input")
    require({str(BASE),str(WORKER),str(SDK_SOURCE),str(SEALER),str(Path(__file__).resolve())} <= seen,
            "Mandatory harmless source pins missing")
    return output


def launch_argv(config, expected, row):
    require(len(expected)==64 and all(c in "0123456789abcdef" for c in expected), "Protocol SHA256 required")
    output=validate_role(config)
    require(row in config["cases"], "Unbound case")
    child=safe(row["child_output"],output=True)
    argv=[str(BASE),"-I","-B",str(WORKER),row["worker_mode"],str(child),config["child_protocol"],expected]
    command=subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le"))//2+1<=32767, "Command cap")
    return argv,command,load_sdk().effective_environment(output)


def api_class(sdk):
    class HarmlessKernel32(sdk.Kernel32):
        """Separately authorized constructor; frozen original stays disabled."""
        def __init__(self,config,expected):
            validate_role(config);require(len(expected)==64,"Protocol identity required")
            require(config.get("pure_fixture") is not True,"Synthetic configuration cannot construct the real SDK")
            require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original draft changed")
            self.config,self.expected,self.attempted=config,expected,set()
            sdk.layouts();require(os.name=="nt","Windows required")
            C=sdk.C;ptr=C.POINTER
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
            matches=[row for row in self.config["cases"]
                     if launch_argv(self.config,self.expected,row)==(argv,command,environment)]
            require(len(matches)==1 and Path(cwd)==Path(self.config["output"]),"Only exact harmless worker argv")
            mode=matches[0]["worker_mode"];require(mode not in self.attempted,"Case already attempted; no retry")
            self.attempted.add(mode)
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
    return HarmlessKernel32


class ExpectedSuspendedAbort(RuntimeError):
    pass


def expected_trigger(mode,error,captures,injected):
    if mode=="suspended_abort":return isinstance(error,ExpectedSuspendedAbort) and injected
    if mode=="overflow":return (isinstance(error,RuntimeError) and
        str(error)=="ABI stream cap exceeded; unknown further bytes" and captures["stdout"]["truncated"]
        and captures["stdout"]["retained_bytes"]==65536 and captures["stdout"]["observed_bytes_at_least"]>65536)
    if mode=="sleep":return isinstance(error,TimeoutError) and str(error)=="Declared ABI parent/child deadline exceeded"
    return False


def marker(path,cap=4096):
    require(path.is_file() and 0<path.stat().st_size<=cap,"Missing/oversized harmless marker")
    return json.loads(path.read_bytes())


def run_case(sdk,api,config,expected,row,journal,parent_end):
    mode=row["worker_mode"];child=safe(row["child_output"],output=True);child.mkdir(parents=True)
    case_root=child.parent;started=time.monotonic();end=min(started+8,parent_end-5)
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(mode=mode,status="failed",captures=captures,injected_abort=False)
    owner=None;trigger=None;sinks=ExitStack()
    def event(name,**details):
        journal.append(name,qualification_case=mode,**details)
        if mode=="suspended_abort" and name=="abi_assigned_before_resume":
            journal.append("harmless_injected_suspended_abort",qualification_case=mode,after_membership_checks=True,before_resume=True)
            report["injected_abort"]=True
            raise ExpectedSuspendedAbort("Qualification stops assigned suspended worker before resume")
    check=lambda:sdk.finite_deadline(end-2)
    try:
        streams={name:sinks.enter_context((case_root/(name+".bin")).open("xb")) for name in captures}
        owner=sdk.OwnedLaunch(api,event);argv,command,environment=launch_argv(config,expected,row)
        try:
            owner.start(argv,command,environment,Path(config["output"]),check)
            owner.observe_job("harmless_running_first","running_or_finished");last=time.monotonic()
            while True:
                check();sdk.capture_poll(owner,captures,streams)
                if api.wait(owner.pi.hProcess,0):break
                if time.monotonic()-last>=.9:
                    owner.observe_job("harmless_running_periodic","running_or_finished");last=time.monotonic()
                time.sleep(.01)
            report["natural_returncode"]=api.exit_code(owner.pi.hProcess)
            while not all(record["eof"] for record in captures.values()):
                check();sdk.capture_poll(owner,captures,streams);time.sleep(.005)
        except BaseException as error:
            if not expected_trigger(mode,error,captures,report["injected_abort"]):raise
            trigger=error;report["expected_stop"]=dict(error_class=type(error).__name__,error=str(error))
            journal.append("harmless_expected_stop",qualification_case=mode,**report["expected_stop"])
            api.terminate_job(owner.job)
            require(api.wait(owner.pi.hProcess,max(0,min(2000,int((end-time.monotonic())*1000)))),"Expected-stop worker not reaped")
            report["stopped_returncode"]=api.exit_code(owner.pi.hProcess)
        require(mode=="resources" or trigger is not None,"Negative case ended without intended trigger")
        owner.observe_job("harmless_after_wait","finished")
        report["limits_and_peaks"]=api.verify_limits(owner.job)
        started_marker=child/"worker-started.json"
        if mode=="suspended_abort":
            require(not started_marker.exists() and not owner.resume_attempted and owner.assigned,
                    "Suspended abort worker ran or membership unproven")
        else:
            identity=marker(started_marker)
            require(identity["pid"]==int(owner.pi.dwProcessId) and identity["mode"]==mode
                    and identity["protocol_sha256"]==expected and identity["executable"]==str(BASE),"Harmless worker identity differs")
            report["worker_identity"]=identity
        if mode=="resources":
            result=marker(child/"worker-result.json")
            require(report["natural_returncode"]==0 and result["memory_rejected"] is True
                    and result["descendant_spawn_attempts"]==1 and result["spawn"]["rejected"] is True
                    and result["spawn"]["winerror"]==1816 and result["target_library_calls"]==result["model_calls"]==result["network_requests"]==0,
                    "Resource fixture did not produce exact bounded result")
            report["resource_result"]=result
        require(captures["stderr"]["retained_bytes"]==0,"Unexpected harmless stderr")
        report["status"]="expected_case_observation_retained"
    except BaseException as error:
        report["failure"]=dict(error_class=type(error).__name__,error=str(error)[:2048])
    finally:
        try:
            if owner:
                owner.cleanup(end);report.update(reaped=owner.reaped,resumption=owner.resumption_record(),cleanup_errors=owner.cleanup_errors)
            for stream in locals().get("streams",{}).values():stream.flush();os.fsync(stream.fileno())
        except BaseException as error:report["cleanup_failure"]=dict(error_class=type(error).__name__,error=str(error)[:512])
        finally:sinks.close()
        report["whole_case_seconds"]=time.monotonic()-started
        if (report["whole_case_seconds"]>8 or not report.get("reaped") or report.get("cleanup_errors") or report.get("cleanup_failure")):
            report.update(status="failed",failure=report.get("failure",dict(error_class="CaseCleanupOrDeadline",error="See retained cleanup/timing")))
        write_new(case_root/"case-report.json",report)
        journal.append("harmless_case_terminal",qualification_case=mode,status=report["status"],case_report=pin(case_root/"case-report.json"))
    return report


def collect_inputs():
    require(pin(SDK_SOURCE)["sha256"]==SDK_SHA and pin(WORKER)["sha256"]==WORKER_SHA
            and pin(BASE)["sha256"]==BASE_SHA,"Harmless pinned source changed")
    require(pin(HERE/"ABI-EXECUTION-DESIGN-v3.md")["sha256"]==SDK_DESIGN_SHA
            and pin(HERE/"ABI-LAUNCHER-DRAFT-PEER-REVIEW-v3.json")["sha256"]==SDK_PEER_SHA,
            "Frozen SDK basis changed")
    files=[Path(__file__).resolve(),SDK_SOURCE,SEALER,WORKER,BASE,DEFAULT,DEFAULT.parent.parent/"pyvenv.cfg",
        HERE/"ABI-EXECUTION-DESIGN-v3.md",HERE/"ABI-LAUNCHER-DRAFT-PEER-REVIEW-v3.json",
        HERE/"ABI-DRAFT-PREPARATION-v3.json",HERE/"ABI-PARENT-V3-PURE-CHECKS.json",
        HERE/"check_abi_parent_launch_draft_v3.py",HERE/"ABI-PARENT-V3-PURE-CHECKS.log",
        HERE/"JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json",HERE/"JOB-ACCOUNTING-DISPOSITION.json",
        PREVIOUS/"acceptance.json",PREVIOUS/"WHEEL-ENVIRONMENTS.json",
        HERE/"qualify_harmless_launcher.py",HERE/"HARMLESS-LAUNCHER-QUALIFICATION-PROTOCOL.json",
        HERE/"HARMLESS-LAUNCHER-QUALIFICATION-DESIGN.md",HERE/"HARMLESS-LAUNCHER-PURE-CHECKS.json",
        HERE/"check_harmless_launcher.py",HERE/"HARMLESS-LAUNCHER-HEADER-METADATA.json"]
    require(pin(PREVIOUS/"acceptance.json")["sha256"]=="491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
            and pin(HERE/"JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json")["sha256"]=="fd38eceb4d732fe3697c79715d93d59d21c6741137cbb5708172138976d78288","Accepted anchors changed")
    prep=json.loads((HERE/"ABI-DRAFT-PREPARATION-v3.json").read_bytes())
    for item in prep["SDK_headers"]:require(pin(item["path"])==item,"SDK header changed");files.append(Path(item["path"]))
    os_proof=json.loads((HERE/"JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json").read_bytes())
    for item in os_proof["anchors"]+os_proof["output_files"]:
        require(pin(item["path"])==item,"Verified OS input changed");files.append(Path(item["path"]))
    accepted=json.loads((PREVIOUS/"acceptance.json").read_bytes())
    wheel_path=PREVIOUS/"WHEEL-ENVIRONMENTS.json";wheel=json.loads(wheel_path.read_bytes())
    expected=accepted["evidence_files"][wheel_path.relative_to(ROOT).as_posix()]
    require({k:pin(wheel_path)[k] for k in ("bytes","sha256")}==expected
            and pin(wheel["wheel"])["sha256"]==wheel["wheel_sha256"]==accepted["wheel"]["sha256"]
            and Path(wheel["default_python"])==DEFAULT,"Accepted wheel/environment provenance differs")
    files.append(Path(wheel["wheel"]))
    with ZipFile(wheel["wheel"]) as archive:
        members=[n for n in archive.namelist() if n.startswith("asof/") and not n.endswith("/")]
        require(len(members)==85,"Accepted runtime closure differs")
        for name in members:
            path=DEFAULT.parent.parent/"Lib/site-packages"/name
            require(pin(path)["sha256"]==hashlib.sha256(archive.read(name)).hexdigest(),"Accepted installed source changed")
            files.append(path)
    return list({str(path):pin(path) for path in files}.values()),prep["SDK_headers"]


def prepare():
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode,"Windows -I -B required")
    require(metadata.version("asof-target-agents")=="0.3.11" and Path(sys.executable)==DEFAULT,"Accepted default environment required")
    require(not PROTOCOL.exists(),"Protocol already exists")
    proof=json.loads(PURE.read_bytes());require(proof["status"]=="passed_harmless_launcher_pure_checks"
        and proof["helper_sha256"]==pin(__file__)["sha256"] and proof["real_sdk_constructions"]==proof["actual_children"]==0,"Fresh pure checks required")
    inputs,headers=collect_inputs();inputs.extend([pin(PURE),pin(HERE/"check_harmless_launcher_v2.py"),pin(HERE/"HARMLESS-LAUNCHER-QUALIFICATION-DESIGN-v2.md")])
    output=safe(ROOT/"data/cache"/("r09-harmless-launcher-qualification-v2-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Output already exists")
    header=HERE/"HARMLESS-LAUNCHER-HEADER-METADATA-v2.json"
    with header.open("x",encoding="utf-8") as stream:
        json.dump(dict(schema_version=1,SDK_headers=headers,source_sha256=SDK_SHA,seal_helper_sha256=SEALER_SHA,
            creation_flags=0x08080404,attribute_keys=[0x20002,0x2000D],
            startup_sizes=dict(STARTUPINFOW=104,STARTUPINFOEXW=112,PROCESS_INFORMATION=24),
            original_draft_enabled=False,preparation_sdk_constructions=0,child_dispatches=0),stream,indent=2);stream.write("\n")
    inputs.append(pin(header))
    config=configuration(output,inputs);validate_role(config)
    with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(status="prepared_no_real_sdk_or_child",protocol_sha256=pin(PROTOCOL)["sha256"],helper_sha256=pin(__file__)["sha256"],inputs=len(inputs),output=str(output))))


def guard():
    def audit(event,args):
        if event in ("subprocess.Popen","os.system","socket.__new__","socket.getaddrinfo","socket.connect"):
            raise RuntimeError("No shell/subprocess/network in qualification parent")
        if event=="ctypes.dlopen":
            name=args[0];require(name is None or name=="kernel32" or os.path.normcase(str(name))==os.path.normcase(r"C:\Windows\System32\kernel32.dll"),"Only system SDK module")
        if event=="open" and args and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(args[0])).absolute()
            require(path.drive.casefold()!="e:" and path.suffix.casefold()!=".gguf" and "\\data\\benchmark\\" not in str(path).casefold(),"No protected payload")
    sys.addaudithook(audit)


def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"Attempt consumed; no restart")
    require(metadata.version("asof-target-agents")=="0.3.11" and Path(sys.executable)==DEFAULT,"Accepted default environment required")
    sdk=load_sdk();started=time.monotonic();end=started+60
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;leases=[];failure=None
    report=dict(schema_version=1,status="failed",role="harmless_sdk_launch_qualification",cases=[],
                remaining_not_attempted=list(MODES),pure_fixture=config.get("pure_fixture",False),
                no_target_execution=True,network_requests=0)
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        journal.append("harmless_qualification_reserved",protocol_sha256=expected,limits=LIMITS,sdk_draft_remains_disabled=True)
        write_new(output/"effective-protocol.json",config)
        require(pin(output/"effective-protocol.json")["sha256"]==expected,"Child protocol archive differs")
        api=api_class(sdk)(config,expected)
        for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
            sdk.finite_deadline(end-5);api.read_lease(item,end-5,leases)
        for row in config["cases"]:
            sdk.finite_deadline(end-5)
            result=run_case(sdk,api,config,expected,row,journal,end);report["cases"].append(result)
            report["remaining_not_attempted"].remove(row["worker_mode"])
            require(result["status"]=="expected_case_observation_retained","Harmless case did not qualify: "+row["worker_mode"])
        require(len(report["cases"])==4,"Incomplete harmless qualification")
        report["status"]="four_harmless_cases_retained_independent_review_pending"
    except BaseException as error:
        failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
    finally:
        require(reservation["owned"],"No exclusive output ownership")
        try:
            if api:
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    record=api.read_lease(item,end,leases);api.close(record["handle"]);record["closed"]=True
            sdk.finite_deadline(end)
        except BaseException as error:
            failure=failure or dict(error_class=type(error).__name__,error=str(error)[:2048])
        try:
            if failure:
                report.update(status="failed",failure=failure)
                if not (output/"failure.json").exists():
                    write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
            try:
                if journal:journal.append("harmless_qualification_terminal",status=report["status"],failure=failure)
            finally:
                if journal:journal.close()
            report["lease_ownership"]=leases;report["elapsed_before_early_receipt_seconds"]=time.monotonic()-started
            write_new(output/"parent-report.json",report);sdk.finite_deadline(end)
            outputs={}
            for path in sorted(output.rglob("*")):
                sdk.finite_deadline(end)
                if path.is_file():outputs[path.relative_to(output).as_posix()]={k:pin(path)[k] for k in ("bytes","sha256")}
            write_new(output/"receipt.json",dict(schema_version=1,status=report["status"],protocol_sha256=expected,outputs=outputs,failure_veto="Any failure marker overrides receipt"))
        except BaseException as error:
            failure=failure or dict(error_class=type(error).__name__,error=str(error)[:2048])
            report.update(status="failed",failure=failure)
            if not (output/"failure.json").exists():
                try:write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
                except BaseException:pass
        finally:
            terminal=load_sealer(sdk)(output,api,leases,failure,report["status"],started,end)
            report["terminal_status"]=terminal["status"]
            report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK flag changed")
    return report


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--execute":
        guard();expected=sys.argv[2];require(pin(PROTOCOL)["sha256"]==expected,"Exact protocol hash required")
        result=execute(json.loads(PROTOCOL.read_bytes()),expected)
        print(json.dumps(dict(status=result["status"],terminal_status=result["terminal_status"],output=result["terminal_seal"]["path"])))
        raise SystemExit(0 if result["status"]=="four_harmless_cases_retained_independent_review_pending" and result["terminal_status"]=="harmless_launch_qualification_passed" else 1)
    else:raise SystemExit("Prepare, review and obtain separate root decision before --execute SHA256")
