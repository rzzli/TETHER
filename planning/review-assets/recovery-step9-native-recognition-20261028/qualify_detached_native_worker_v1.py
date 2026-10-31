"""Unfrozen prospective DETACHED own-worker qualification; no IOCP/runtime/model.

The original SDK constructor/execute_draft remain disabled. This module exposes
no ABI executable, target DLL, model, tokenizer, network or fallback launcher.
The own build is unchanged. Peer policy must bind before pure/preparation freeze;
real launch still requires exact-source/protocol peer and root authorization.
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
SDK_SOURCE = HERE / "detached_parent_launch_draft_v1.py"
SDK_SHA = "3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
ORIGINAL_SDK_SOURCE = HERE / "abi_parent_launch_draft_v3.py"
ORIGINAL_SDK_SHA = "c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4"
DETACHED_POLICY = HERE / "DETACHED-POLICY-CONTRACT-v1.json"
DETACHED_POLICY_SHA = "387d0c686c7efb364cea9b21c6da36cb38b12015a4498239192da071f42edfdc"
DETACHED_DESIGN = HERE / "DETACHED-POLICY-DESIGN-v1.md"
DETACHED_DESIGN_SHA = "65353b41b45ce5d2dfa420cbe2855718f63757c64941039283326d01679907ae"
SDK_DESIGN_SHA = "75b41cf2e60546f44626c057a0a278a29ff05066642a64e567aa6e492520af33"
SDK_PEER_SHA = "d6e327534a1eaf11534999814e896698d9ba86e91ea14f91701ab010d033d89b"
WORKER = HERE / "harmless_launch_worker_native_v3.cpp"
WORKER_SHA = "11490803ed4a3e68937c7bf685f31a042752f3c8681347c67f2bf4cd46721be6"
BUILD = ROOT / "data/cache/r09-harmless-native-build-v3-20261028T210353Z"
OWN_EXE = BUILD / "harmless_launch_worker.exe"
SOURCE_COPY = ROOT / "data/cache/r09-harmless-native-preparation-v3-20261028T210353Z/harmless_launch_worker.cpp"
OWN_EXE_SHA = "0100ee6004531a41a28156385ad66fd5c0bded43c4840091a846573efe6d8e49"
BUILD_VERIFICATION = HERE / "HARMLESS-NATIVE-BUILD-V3-RESULT-VERIFICATION.json"
BUILD_VERIFICATION_SHA = "7f51e8606ba6cb624c5805ac295e5d5211ad8b5d185c619f4286ab1127c1cc21"
BUILD_PROTOCOL = HERE / "HARMLESS-NATIVE-BUILD-PROTOCOL-v3.json"
BUILD_PROTOCOL_SHA = "7cf13e529deb26f147bf0b9358cdc47fe91c4b21b2064a3381db9119f6953aea"
BUILD_TERMINAL_SHA = "73c2ac4236eecbf7295909f096a3dc20ebdd146adbb4a5d7d2351828ff2fc905"
SYSTEM_DLL_NAMES = ("kernel32.dll","bcrypt.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll",
                    "ucrtbase.dll","kernelbase.dll","ntdll.dll","bcryptprimitives.dll")
SYSTEM_DLL_PINS = {
    r"C:\Windows\System32\kernel32.dll":dict(path=r"C:\Windows\System32\kernel32.dll",bytes=861992,sha256="e132eba4166256e2f414b91fe7d5386590bc5ea8626aee5af9c9738383cf2ae1"),
    r"C:\Windows\System32\bcrypt.dll":dict(path=r"C:\Windows\System32\bcrypt.dll",bytes=195128,sha256="d0fc7863d7b034da33f34dc82b96a8604572598a217668a43fc9eca3a8e2a8e1"),
    r"C:\Windows\System32\msvcp140.dll":dict(path=r"C:\Windows\System32\msvcp140.dll",bytes=643512,sha256="7c26614e1d733892c2deac7e245ce115504b1d80592dd0a01b08e3e5a55f89ca"),
    r"C:\Windows\System32\vcruntime140.dll":dict(path=r"C:\Windows\System32\vcruntime140.dll",bytes=178616,sha256="d1f4225df2cd877dbf130d5668a021dce3f94118455ff5ec952061c30afc9ce7"),
    r"C:\Windows\System32\vcruntime140_1.dll":dict(path=r"C:\Windows\System32\vcruntime140_1.dll",bytes=50112,sha256="a7146c08f89fe5b04541ab507cdb59ff7b44534d4ba3c668a426c6450a03434e"),
    r"C:\Windows\System32\ucrtbase.dll":dict(path=r"C:\Windows\System32\ucrtbase.dll",bytes=1399656,sha256="dedb7611e1abc1ff3852dcac3d4c93a048d729e25b061973b9969f22698f14ca"),
    r"C:\Windows\System32\kernelbase.dll":dict(path=r"C:\Windows\System32\kernelbase.dll",bytes=4254784,sha256="5c29b73622ce0976e1ada566f31f2197ba0f8beaea89c3ec033366126172c3d0"),
    r"C:\Windows\System32\ntdll.dll":dict(path=r"C:\Windows\System32\ntdll.dll",bytes=2558392,sha256="651ac9041af8e6b5ebd331d53163244c0a27d36d1433f0f15cac1f28c5f2e82c"),
    r"C:\Windows\System32\bcryptprimitives.dll":dict(path=r"C:\Windows\System32\bcryptprimitives.dll",bytes=732800,sha256="f0dba794068893c9616b0b54bef1be8f904be89eb2cb09b575d3d7fb1b5000f8")}
BASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
BASE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"
PREVIOUS = HERE.parent / "recovery-step9-generation-contract-20261028"
DEFAULT = ROOT / "data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe"
PROTOCOL = HERE / "DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json"
SEALER = HERE / "harmless_launch_seal_v2.py"
SEALER_SHA = "4cc94dd9ab5940f4f5e303d4c41ffbbb8d5032103eafb139113133d44cbb1dcb"
PURE = HERE / "DETACHED-NATIVE-QUALIFICATION-PURE-CHECKS-v1.json"
MODES = ("resources", "overflow", "sleep", "suspended_abort")
LIMITS = dict(parent_seconds=60, case_seconds=8, cleanup_reserve_seconds=2,
              finalization_reserve_seconds=5, process_commit_bytes=268435456,
              job_commit_bytes=268435456, active_processes=1, maximum_children=4,
              stream_bytes=65536, maximum_job_pids=16, maximum_snapshots_per_case=40)
RESOURCE_FINAL_POLICY = dict(case="resources",stage="harmless_after_wait",expected="finished",
    allowed_TotalProcesses=[1,2],ActiveProcesses=0,TotalTerminatedProcesses=0,pids=[],
    raw_observation_retained_before_validation=True,
    prerequisites="Prospectively selected final totals only with exactly one failed quota1816 attempt, no child/handle metadata, allocation controls and natural exit0",
    attribution="Neither quota1816 nor either total identifies the private active-limit cause or another process without independent identity evidence",
    terminated_zero_scope="Selected observed-platform fixture expectation, not a universal counter rule",
    primary_doc="https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information",
    source_analysis_sha256="12da9836369b338b5ebc221394c92dab2ba3e8c3c268dc70d4939e4f3b25a14b")
_SDK = None
FAILED_SPAWN_NULL_FIELDS=("child_pid","thread_id","first_wait_result","terminate_attempted","terminate_ok",
    "terminate_winerror","final_wait_result","reaped","thread_handle_closed","thread_close_winerror",
    "process_handle_closed","process_close_winerror")


def detached_policy():
    require(DETACHED_POLICY is not None and DETACHED_DESIGN is not None
            and isinstance(DETACHED_POLICY_SHA,str) and isinstance(DETACHED_DESIGN_SHA,str),
            "Unfrozen draft: prospective detached policy is not bound yet")
    require(pin(DETACHED_POLICY)["sha256"]==DETACHED_POLICY_SHA
            and pin(DETACHED_DESIGN)["sha256"]==DETACHED_DESIGN_SHA
            and pin(ORIGINAL_SDK_SOURCE)["sha256"]==ORIGINAL_SDK_SHA,"Detached policy/original SDK changed")
    policy=json.loads(Path(DETACHED_POLICY).read_bytes())
    require(policy["new_creation_flags_hex"]=="0x0008040C"
            and policy["resources_final_policy"]["accepted_total_processes"]==[1,2]
            and policy["generic_policy"]["active2_accepted"] is False,"Detached policy scope differs")
    return policy


def validate_resource_result(result,returncode):
    try:
        spawn=result["spawn"]
        require(type(returncode) is int and returncode==0
                and type(result["small_control_bytes"]) is int and result["small_control_bytes"]==65536
                and result["small_control_released"] is True and result["memory_rejected"] is True
                and type(result["descendant_spawn_attempts"]) is int and result["descendant_spawn_attempts"]==1
                and spawn["rejected"] is True and type(spawn["winerror"]) is int and spawn["winerror"]==1816
                and set(spawn)=={"rejected","winerror",*FAILED_SPAWN_NULL_FIELDS}
                and all(spawn[field] is None for field in FAILED_SPAWN_NULL_FIELDS)
                and all(type(result[field]) is int and result[field]==0
                        for field in ("target_library_calls","model_calls","network_requests")),
                "Detached resource fixture did not meet every predeclared control/null field")
    except (KeyError,TypeError) as error:
        raise RuntimeError("Malformed detached resource fixture") from error


def verified_build_scope():
    require(type(OWN_EXE_SHA) is str and len(OWN_EXE_SHA)==64
            and BUILD_VERIFICATION is not None and type(BUILD_VERIFICATION_SHA) is str
            and len(BUILD_VERIFICATION_SHA)==64 and bool(SYSTEM_DLL_PINS),
            "Independently verified own build/CRT bindings are required")
    require(pin(OWN_EXE)["sha256"]==OWN_EXE_SHA and pin(WORKER)["sha256"]==WORKER_SHA
            and pin(SOURCE_COPY)["sha256"]==WORKER_SHA
            and pin(BUILD_VERIFICATION)["sha256"]==BUILD_VERIFICATION_SHA,
            "Exact own build/source/verification changed")
    require(set(SYSTEM_DLL_PINS)=={str(Path(r"C:\Windows\System32")/name) for name in SYSTEM_DLL_NAMES}
            and all(Path(path).parent==Path(r"C:\Windows\System32") and pin(path)==item
                    for path,item in SYSTEM_DLL_PINS.items()),"Finite exact System32 pins required")
    proof=json.loads(Path(BUILD_VERIFICATION).read_bytes())
    require(proof["status"]=="VERIFIED_compiled_x64_MD_harmless_worker_built_NOT_EXECUTED"
            and proof["artifacts"]["executable"]==pin(OWN_EXE)
            and proof["source"]["original"]==pin(WORKER) and proof["source"]["copied"]==pin(SOURCE_COPY)
            and proof["seals"]["terminal"]["sha256"]==BUILD_TERMINAL_SHA
            and proof["seals"]["no_failure_markers"] is True
            and pin(BUILD/"terminal-seal.json")["sha256"]==BUILD_TERMINAL_SHA
            and pin(BUILD_PROTOCOL)["sha256"]==BUILD_PROTOCOL_SHA
            and not any((BUILD/name).exists() for name in ("failure.json","late-failure.json","post-seal-failure.json")),
            "Independently verified own build/terminal scope differs")
    seal=json.loads((BUILD/"terminal-seal.json").read_bytes())
    require(seal["status"]=="own_harmless_native_worker_built_not_executed"
            and seal["complete_output_universe"] is True and seal["protocol_sha256"]==BUILD_PROTOCOL_SHA,
            "Own build terminal is incomplete or failed")
    for name in ("build-report.json","receipt.json","post-lease-cleanup.json"):
        current=pin(BUILD/name)
        require({key:current[key] for key in ("bytes","sha256")}==seal["outputs"][name],
                "Selected build proof changed: "+name)
    return proof


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
    detached_policy()
    verified_build_scope()
    output = safe(output, output=True)
    return dict(schema_version=1, kind="detached_native_own_worker_qualification_v1", helper=pin(__file__),
        sdk_sha256=SDK_SHA, seal_helper_sha256=SEALER_SHA, worker_sha256=WORKER_SHA,
        executable=str(OWN_EXE), executable_sha256=OWN_EXE_SHA, parent_base_sha256=BASE_SHA,
        build_verification_sha256=BUILD_VERIFICATION_SHA, system_dll_pins=list(SYSTEM_DLL_PINS.values()),
        detached_policy_sha256=DETACHED_POLICY_SHA,creation_flags=0x0008040C,
        output=str(output), child_protocol=str(output/"effective-protocol.json"), cases=cases(output),
        limits=LIMITS, resource_final_job_policy=RESOURCE_FINAL_POLICY, inputs=inputs, accepted_version="0.3.11", no_target_execution=True,
        automatic_retry=False, preparation_only=True)


def validate_role(config):
    detached_policy()
    verified_build_scope()
    require(type(config) is dict and config["kind"] == "detached_native_own_worker_qualification_v1"
        and config["schema_version"] == 1 and config["sdk_sha256"] == SDK_SHA
        and config["seal_helper_sha256"] == SEALER_SHA and pin(SEALER)["sha256"] == SEALER_SHA
        and config["worker_sha256"] == WORKER_SHA and config["executable"] == str(OWN_EXE)
        and config["executable_sha256"]==OWN_EXE_SHA and config["parent_base_sha256"] == BASE_SHA
        and config["build_verification_sha256"]==BUILD_VERIFICATION_SHA
        and config["detached_policy_sha256"]==DETACHED_POLICY_SHA and config["creation_flags"]==0x0008040C
        and config["system_dll_pins"]==list(SYSTEM_DLL_PINS.values()) and config["limits"] == LIMITS
        and config["resource_final_job_policy"] == RESOURCE_FINAL_POLICY
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
        require(path.suffix.casefold()!=".pyd"
                and (path.suffix.casefold()!=".dll" or SYSTEM_DLL_PINS.get(str(path))==item)
                and (path.suffix.casefold()!=".exe" or path in (OWN_EXE,BASE,DEFAULT)),
                "Only exact own EXE/parent interpreters and finite pinned System32 DLL inputs")
    require({str(OWN_EXE),str(BASE),str(WORKER),str(SOURCE_COPY),str(BUILD_VERIFICATION),str(BUILD_PROTOCOL),
             str(BUILD/"terminal-seal.json"),str(SDK_SOURCE),str(SEALER),str(Path(__file__).resolve()),
             str(DETACHED_POLICY),str(DETACHED_DESIGN),str(ORIGINAL_SDK_SOURCE),*SYSTEM_DLL_PINS} <= seen,
            "Mandatory harmless source pins missing")
    return output


def launch_argv(config, expected, row):
    require(len(expected)==64 and all(c in "0123456789abcdef" for c in expected), "Protocol SHA256 required")
    output=validate_role(config)
    require(row in config["cases"], "Unbound case")
    child=safe(row["child_output"],output=True)
    argv=[str(OWN_EXE),row["worker_mode"],str(child),config["child_protocol"],expected]
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


def resource_finished_problem(sdk,snapshot):
    """Selected quota fixture only; never modify raw or decoded evidence."""
    try:
        a,p=snapshot["accounting"],snapshot["pid_list"]
        if a["ok"] is not True or p["ok"] is not True or a["error"]!=0 or p["error"]!=0 or a["returned_bytes"]!=48:
            return "Resource final query/length mismatch"
        raw_a,raw_p=bytes.fromhex(a["raw_hex"]),bytes.fromhex(p["raw_hex"])
        if len(raw_a)!=48 or len(raw_p)!=136:return "Resource final raw buffer length mismatch"
        decoded=sdk.ACCOUNTING.from_buffer_copy(raw_a);ids=sdk.PID_LIST.from_buffer_copy(raw_p)
        if any(type(a["decoded"][n]) is not int or int(getattr(decoded,n))!=a["decoded"][n]
               for n,_ in decoded._fields_):return "Resource final raw/decoded accounting differs"
        if type(p["listed_count"]) is not int or type(p["assigned_count"]) is not int:
            return "Resource final PID count types"
        n=p["listed_count"]
        if not 0<=n<=16 or not 8+8*n<=p["returned_bytes"]<=136:
            return "Resource final PID response length mismatch"
        if int(ids.NumberOfAssignedProcesses)!=p["assigned_count"] or int(ids.NumberOfProcessIdsInList)!=n:
            return "Resource final raw/decoded PID counts differ"
        if (p["assigned_count"],n,p["pids"])!=(0,0,[]):return "Resource final PID list not empty"
        if (a["decoded"]["TotalProcesses"] not in (1,2)
                or (a["decoded"]["ActiveProcesses"],a["decoded"]["TotalTerminatedProcesses"])!=(0,0)):
            return "Resource final expected predeclared total1or2/active0/terminated0"
        return None
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return "Malformed resource final Job response"


def owner_for_case(sdk,api,event,mode):
    if mode!="resources":return sdk.OwnedLaunch(api,event)
    class ResourceOwnedLaunch(sdk.OwnedLaunch):
        def observe_job(self,stage,expected):
            if stage!="harmless_after_wait" or expected!="finished":
                return super().observe_job(stage,expected)
            require(self.snapshot_count<sdk.LIMITS["maximum_job_snapshots"],"Job snapshot budget exhausted before query")
            value=self.api.job_snapshot(self.job);self.snapshot_count+=1
            self.event("abi_job_snapshot_observed",stage=stage,ordinal=self.snapshot_count,snapshot=value,
                       qualification_policy=RESOURCE_FINAL_POLICY)
            problem=resource_finished_problem(sdk,value)
            require(problem is None,problem or "Unexpected resource final Job response")
            return value
    return ResourceOwnedLaunch(api,event)


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
        owner=owner_for_case(sdk,api,event,mode);argv,command,environment=launch_argv(config,expected,row)
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
            require(report["stopped_returncode"]==125,"Expected-stop worker exit differs from explicit Job termination125")
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
                    and identity["protocol_sha256"]==expected and identity["executable"]==str(OWN_EXE),"Harmless worker identity differs")
            report["worker_identity"]=identity
        if mode=="resources":
            result=marker(child/"worker-result.json")
            validate_resource_result(result,report["natural_returncode"])
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
    detached_policy()
    verified_build_scope()
    require(pin(SDK_SOURCE)["sha256"]==SDK_SHA and pin(WORKER)["sha256"]==WORKER_SHA
            and pin(BASE)["sha256"]==BASE_SHA,"Native harmless pinned source changed")
    require(pin(HERE/"ABI-EXECUTION-DESIGN-v3.md")["sha256"]==SDK_DESIGN_SHA
            and pin(HERE/"ABI-LAUNCHER-DRAFT-PEER-REVIEW-v3.json")["sha256"]==SDK_PEER_SHA,
            "Frozen SDK basis changed")
    # Explicit qualification closure only. Build receipts preserve upstream
    # provenance; their 237 compiler/runtime inputs are NOT reopened/inherited.
    files=[Path(__file__).resolve(),SDK_SOURCE,ORIGINAL_SDK_SOURCE,Path(DETACHED_POLICY),Path(DETACHED_DESIGN),
        SEALER,WORKER,SOURCE_COPY,OWN_EXE,
        Path(BUILD_VERIFICATION),BASE,DEFAULT,DEFAULT.parent.parent/"pyvenv.cfg",
        BUILD_PROTOCOL,HERE/"HARMLESS-NATIVE-BUILD-ROOT-DECISION-v3.json",BUILD/"build-report.json",
        BUILD/"receipt.json",BUILD/"post-lease-cleanup.json",BUILD/"terminal-seal.json",
        HERE/"HARMLESS-NATIVE-WORKER-DESIGN-v3.md",
        HERE/"HARMLESS-NATIVE-WORKER-SOURCE-PEER-v3.json",
        HERE/"ABI-EXECUTION-DESIGN-v3.md",HERE/"ABI-LAUNCHER-DRAFT-PEER-REVIEW-v3.json",
        HERE/"ABI-DRAFT-PREPARATION-v3.json",HERE/"JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json",
        PREVIOUS/"acceptance.json",PREVIOUS/"WHEEL-ENVIRONMENTS.json",
        HERE/"HARMLESS-V3-RESULT-VERIFICATION.json",HERE/"HARMLESS-V3-RESULT-VERIFICATION.md",
        HERE/"HARMLESS-LAUNCHER-V4-RESULT-VERIFICATION.json",HERE/"HARMLESS-V4-WORKER-SOURCE-DIAGNOSIS.md",
        HERE/"HARMLESS-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json",
        HERE/"NATIVE-JOB-IOCP-V1-RESULT-VERIFICATION.json",HERE/"NATIVE-JOB-IOCP-V1-POST-REVIEW-WARNING.json",
        HERE/"JOB-QUOTA-ACCOUNTING-SOURCE-ANALYSIS.json",HERE/"JOB-QUOTA-ACCOUNTING-SOURCE-ANALYSIS.md"]
    require(pin(HERE/"JOB-QUOTA-ACCOUNTING-SOURCE-ANALYSIS.json")["sha256"]==RESOURCE_FINAL_POLICY["source_analysis_sha256"]
            and pin(HERE/"HARMLESS-V3-RESULT-VERIFICATION.json")["sha256"]=="96d4d4d4fed3a2386d906d1d89e5952781e8d35d47680d2a07f50e7549a43018"
            and pin(HERE/"HARMLESS-LAUNCHER-V4-RESULT-VERIFICATION.json")["sha256"]=="42b8b38c6e582288d7f93b64663b2eb0482c033fd3ea44f7bc9d806c55af61a3",
            "Resource policy basis changed")
    require(pin(PREVIOUS/"acceptance.json")["sha256"]=="491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
            and pin(HERE/"JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json")["sha256"]=="fd38eceb4d732fe3697c79715d93d59d21c6741137cbb5708172138976d78288","Accepted anchors changed")
    require(pin(HERE/"NATIVE-JOB-IOCP-V1-RESULT-VERIFICATION.json")["sha256"]=="25c648a168c5d836acb44e080ba8c4219c2d38068d15174ab35a92701d5beec5"
            and pin(HERE/"NATIVE-JOB-IOCP-V1-POST-REVIEW-WARNING.json")["sha256"]=="f0840e3d5e0ca82c42092853e75d81839f9064fb52f9952d99405c53a846fdc0",
            "Retained IOCP evidence/warning changed")
    prep=json.loads((HERE/"ABI-DRAFT-PREPARATION-v3.json").read_bytes())
    for item in prep["SDK_headers"]:require(pin(item["path"])==item,"SDK header changed");files.append(Path(item["path"]))
    files.extend(Path(path) for path in SYSTEM_DLL_PINS)
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
    detached_policy()
    verified_build_scope()
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode,"Windows -I -B required")
    require(metadata.version("asof-target-agents")=="0.3.11" and Path(sys.executable)==DEFAULT,"Accepted default environment required")
    require(not PROTOCOL.exists(),"Protocol already exists")
    proof=json.loads(PURE.read_bytes());require(proof["status"]=="passed_detached_native_worker_pure_checks"
        and proof["helper_sha256"]==pin(__file__)["sha256"] and proof["real_sdk_constructions"]==proof["actual_children"]==0,"Fresh pure checks required")
    inputs,headers=collect_inputs();inputs.extend([pin(PURE),pin(HERE/"check_detached_native_qualification_v1.py")])
    output=safe(ROOT/"data/cache"/("r09-detached-native-qualification-v1-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Output already exists")
    header=HERE/"DETACHED-NATIVE-QUALIFICATION-HEADER-METADATA-v1.json"
    with header.open("x",encoding="utf-8") as stream:
        json.dump(dict(schema_version=1,SDK_headers=headers,source_sha256=SDK_SHA,seal_helper_sha256=SEALER_SHA,
            creation_flags=0x0008040C,attribute_keys=[0x20002,0x2000D],
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
    report=dict(schema_version=1,status="failed",role="detached_native_own_worker_qualification",cases=[],
                remaining_not_attempted=list(MODES),case_attempts=[],pure_fixture=config.get("pure_fixture",False),
                no_target_execution=True,network_requests=0,finalization_errors=[])
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
            mode=row["worker_mode"]
            journal.append("harmless_case_call_reserved",qualification_case=mode,
                           disposition="case call reserved; creation/resumption follow separately in journal")
            attempt=dict(mode=mode,status="reserved_case_return_not_observed")
            report["case_attempts"].append(attempt)
            report["remaining_not_attempted"].remove(mode)
            try:
                result=run_case(sdk,api,config,expected,row,journal,end)
            except BaseException as error:
                attempt["call_error"]=dict(error_class=type(error).__name__,error=str(error)[:1024])
                raise
            attempt["status"]="case_report_returned"
            report["cases"].append(result)
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
                    record=api.read_lease(item,end,leases);record["final_recheck_close_attempted"]=True
                    try:
                        api.close(record["handle"]);record["closed"]=True;record["final_recheck_close_return_observed"]=True
                    except BaseException as error:
                        detail=dict(phase="final_input_recheck_close",error_class=type(error).__name__,error=str(error)[:512])
                        record["cleanup_errors"].append(detail);record["final_recheck_close_return_observed"]=False
                        report["finalization_errors"].append(dict(path=record["path"],handle=record["handle"],**detail));raise
            sdk.finite_deadline(end)
        except BaseException as error:
            detail=dict(phase="final_input_recheck_or_deadline",error_class=type(error).__name__,error=str(error)[:2048])
            report["finalization_errors"].append(detail);failure=failure or detail
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
