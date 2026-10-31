"""UNFROZEN parent-v2 integration draft; verified new build authority is pending.

Existing typed child only: --abi RUNTIME CHILD_OUTPUT. Original SDK gates remain
False; no prepare_config, compiler, backend/registry/model/vocabulary/grammar path.
Actual dispatch requires new exact protocol, independent peer and root decision.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import sys
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
EXE=ROOT/"data/cache/r09-public-c-bridge-build-20261028T175036Z/typed_public_c_recognizer_abi.exe"
EXE_SHA="9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696"
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
PREPARED=ROOT/"data/cache/r09-public-c-bridge-preparation-20261028T175036Z"
BUILD_PROTOCOL=HERE/"BUILD-PROTOCOL.json"
BUILD_PROTOCOL_SHA="5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e"
PROTOCOL=HERE/"DETACHED-ABI-OBSERVATION-PROTOCOL-v2.json"
PURE=HERE/"DETACHED-ABI-OBSERVATION-PURE-CHECKS-v3.json"
CHECKER=HERE/"check_detached_abi_observation_v3.py"
CONTRACT=HERE/"DETACHED-ABI-EXECUTION-CONTRACT-v1.json"
CONTRACT_SHA="2be3241b97ca3a4f0f237ebb6cbcff4884366f37d10303608c09366c4e709457"
DESIGN=HERE/"DETACHED-ABI-EXECUTION-CHECKLIST-v1.md"
DESIGN_SHA="eea8e52dbc55215039fa5ee78305a0ac823c2d008a1626a961b8c5d78e415806"
NEW_BUILD_PROOF=None  # Not executable/preparable until exact verified v4 build is bound.
NEW_BUILD_PROOF_SHA=None
TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
TERMINAL_POLICY=dict(capture_drain_seconds=0.25,maximum_capture_polls=64,
    physical_pipe_EOF_is_not_child_exit=True,unknown_creation_is_not_final=True)
LIMITS=dict(parent_seconds=60,child_seconds=30,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=4194304,row_bytes=65536)
RUNTIME_EXPECTED={
    "libomp.dll":dict(bytes=768000,sha256="a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c"),
    "ggml-base.dll":dict(bytes=803840,sha256="84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3"),
    "ggml.dll":dict(bytes=78848,sha256="2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba"),
    "llama.dll":dict(bytes=3581952,sha256="166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d")}
if sha(BUILD_PROTOCOL)!=BUILD_PROTOCOL_SHA:raise RuntimeError("Retained ABI build protocol changed")
_build_metadata=json.loads(BUILD_PROTOCOL.read_bytes())
_system_names={name.casefold() for name in _build_metadata["prospective_System32_allowlist"]}
SYSTEM_PINS={item["path"]:item for item in _build_metadata["inputs"]
             if Path(item["path"]).parent==Path(r"C:\Windows\System32")
             and Path(item["path"]).name.casefold() in _system_names}
require(len(_system_names)==len(SYSTEM_PINS)==16,"Finite sixteen-System32 basis differs")


def authority():
    require(NEW_BUILD_PROOF is not None and NEW_BUILD_PROOF_SHA is not None,
            "Unfrozen parent-v2: verified new bridge build is not yet bound")
    require(sha(TERMINAL_SOURCE)==TERMINAL_SHA,"Terminal observation component changed")
    require(CONTRACT is not None and DESIGN is not None and CONTRACT_SHA is not None and DESIGN_SHA is not None,
            "Unfrozen ABI source: exact contract is pending")
    require(sha(CONTRACT)==CONTRACT_SHA and sha(DESIGN)==DESIGN_SHA
            and sha(QUALIFICATION)==QUALIFICATION_SHA and sha(q.SDK_SOURCE)==SDK_SHA
            and sha(EXE)==EXE_SHA and sha(BUILD_PROTOCOL)==BUILD_PROTOCOL_SHA,
            "ABI source/qualification/build authority changed")
    contract=json.loads(Path(CONTRACT).read_bytes())
    require(set(name.casefold() for name in contract["System32_candidate_names"])==_system_names
            and contract["harmless_prerequisite"]["sha256"]==QUALIFICATION_SHA
            and contract["sdk"]["sha256"]==SDK_SHA and contract["bridge_executable"]["sha256"]==EXE_SHA,
            "ABI machine contract bindings differ")
    return contract


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
            require((argv,command)==sdk.abi_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child")
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
    require(type(rows) is list and 5<=len(rows)<=21,"ABI module inventory count")
    allowed={os.path.normcase(str(EXE)):pin(EXE),
             **{os.path.normcase(path):item for path,item in runtime_pins().items()},
             **{os.path.normcase(path):item for path,item in SYSTEM_PINS.items()}}
    required={os.path.normcase(str(EXE)),*[os.path.normcase(path) for path in runtime_pins()]}
    seen,names=set(),set()
    for row in rows:
        require(type(row) is dict and set(row)=={"name","path"} and type(row["name"]) is str
                and type(row["path"]) is str,"Malformed ABI module row")
        path=Path(row["path"]);normalized=os.path.normcase(str(path));name=row["name"].casefold()
        require(path.is_absolute() and normalized in allowed and name==path.name.casefold()
                and normalized not in seen and name not in names,"Unapproved/duplicate ABI module path/name")
        require(os.path.normcase(row["path"])==normalized,"Noncanonical ABI module path spelling")
        seen.add(normalized);names.add(name)
    require(required<=seen,"Required EXE/core DLL module missing")
    return rows


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
    require([row.get("event") if type(row) is dict else None for row in rows]==contract["child_artifacts"]["result_events"],
            "ABI event sequence differs")
    require(exact(rows[0],dict(event="before_explicit_required_OpenMP_dependency_load",dependency_native_initialization_possible=True)),
            "OpenMP initialization row differs")
    require(set(rows[1])=={"event","modules","layouts"} and exact(rows[1]["layouts"],contract["expected_layouts"]),
            "Compiled x64 layout fields/types/offsets differ")
    validate_modules(rows[1]["modules"])
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
        layouts=rows[1]["layouts"],raw_modules=rows[1]["modules"],result_rows=5,
        independent_ABI_acceptance="pending",scientific_validation="not_established",
        module_inventory_scope="Reported before explicit version/default calls; no parent/global loaded-module attestation")


def configuration(output,inputs):
    output=safe(output,output=True);argv,command=sdk.abi_argv(EXE,RUNTIME,output/"execution/child")
    return dict(schema_version=1,kind="detached_typed_public_C_ABI_observation_v2",helper=pin(__file__),
        qualified_sdk_sha256=SDK_SHA,qualified_harmless_sha256=QUALIFICATION_SHA,source_basis_sha256=BASIS_SHA,
        executable=pin(EXE),runtime_pins=list(runtime_pins().values()),system_candidates=list(SYSTEM_PINS.values()),
        contract_sha256=CONTRACT_SHA,design_sha256=DESIGN_SHA,limits=LIMITS,creation_flags=0x0008040C,
        terminal_component=pin(TERMINAL_SOURCE),terminal_policy=TERMINAL_POLICY,
        output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),inputs=inputs,
        mode="--abi",expected_version="",version_expected_previously_known=False,maximum_attempts=1,automatic_retry=False,
        explicit_target_calls=["llama_version","llama_model_default_params"],recognition_enabled=False,
        no_model_or_CPU_paths_supplied=True,initializer_effects_instrumented=False)


def validate_role(config):
    authority()
    require(config["schema_version"]==1 and config["kind"]=="detached_typed_public_C_ABI_observation_v2"
        and config["helper"]==pin(__file__) and config["qualified_sdk_sha256"]==SDK_SHA
        and config["qualified_harmless_sha256"]==QUALIFICATION_SHA and config["source_basis_sha256"]==BASIS_SHA
        and config["executable"]==pin(EXE) and config["runtime_pins"]==list(runtime_pins().values())
        and config["system_candidates"]==list(SYSTEM_PINS.values()) and config["contract_sha256"]==CONTRACT_SHA
        and config["design_sha256"]==DESIGN_SHA and config["limits"]==LIMITS and config["creation_flags"]==0x0008040C
        and config["terminal_component"]==pin(TERMINAL_SOURCE) and config["terminal_policy"]==TERMINAL_POLICY
        and config["mode"]=="--abi" and config["expected_version"]=="" and config["version_expected_previously_known"] is False
        and config["maximum_attempts"]==1 and config["automatic_retry"] is False
        and config["explicit_target_calls"]==["llama_version","llama_model_default_params"]
        and config["recognition_enabled"] is False and config["no_model_or_CPU_paths_supplied"] is True
        and config["initializer_effects_instrumented"] is False,
        "Exact fixed ABI observation role required")
    output=safe(config["output"],output=True);argv,command=sdk.abi_argv(EXE,RUNTIME,output/"execution/child")
    require(config["argv"]==argv and config["command_line"]==command
            and config["environment"]==sdk.effective_environment(output),"ABI argv/environment differs")
    allowed_dlls={**runtime_pins(),**SYSTEM_PINS};seen=set()
    for item in config["inputs"]:
        path=safe(item["path"]);require(str(path) not in seen,"Duplicate ABI input");seen.add(str(path))
        require(path.suffix.casefold()!=".pyd"
            and (path.suffix.casefold()!=".dll" or allowed_dlls.get(str(path))==item)
            and (path.suffix.casefold()!=".exe" or path in (EXE,q.DEFAULT,q.BASE)),"Binary outside fixed ABI role")
    require({str(Path(__file__).resolve()),str(EXE),str(BASIS),str(q.SDK_SOURCE),str(QUALIFICATION),str(CONTRACT),str(DESIGN),
             str(TERMINAL_SOURCE),*runtime_pins(),*SYSTEM_PINS}<=seen,"Mandatory ABI input missing")
    return output


def collect_inputs():
    contract=authority()
    files=[Path(__file__).resolve(),TERMINAL_SOURCE,
        HERE/"DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json",HERE/"check_detached_abi_terminal_component_v3.py",
        BASIS,q.SDK_SOURCE,q.ORIGINAL_SDK_SOURCE,QUALIFICATION,
        HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.md",
        HERE/"DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json",HERE/"DETACHED-NATIVE-QUALIFICATION-PEER-REVIEW-v1.json",
        q.DETACHED_POLICY,q.DETACHED_DESIGN,CONTRACT,DESIGN,EXE,BUILD_PROTOCOL,
        HERE/"BUILD-RESULT-VERIFICATION.json",HERE/"BUILD-RESULT-VERIFICATION.md",
        EXE.parent/"receipt.json",EXE.parent/"build-report.json",
        HERE/"typed_public_c_recognizer_v3.cpp",PREPARED/"typed_public_c_recognizer.cpp",
        PREPARED/"recognizer_runtime_pins.hpp",q.DEFAULT,q.DEFAULT.parent.parent/"pyvenv.cfg",q.BASE,
        q.PREVIOUS/"acceptance.json",q.PREVIOUS/"WHEEL-ENVIRONMENTS.json",
        HERE/"DETACHED-ABI-OBSERVATION-PURE-CHECKS-v1.json",HERE/"check_detached_abi_observation_v1.py",
        HERE/"run_detached_abi_observation_pre_final.py",HERE/"check_detached_abi_results_v1.py",
        HERE/"DETACHED-ABI-RESULTS-ADVERSARIAL-PROOF-v1.json"]
    for item in (contract["bridge_source"],contract["bridge_pin_header"],contract["independent_build_proof"]):
        require(pin(item["path"])==item,"Retained typed bridge proof differs")
    require(sha(PREPARED/"typed_public_c_recognizer.cpp")==contract["bridge_source"]["sha256"],"Compiled source copy differs")
    build_proof=json.loads((HERE/"BUILD-RESULT-VERIFICATION.json").read_bytes())
    selected_outputs={str(EXE.parent/item["path"]):dict(path=str(EXE.parent/item["path"]),
                     bytes=item["bytes"],sha256=item["sha256"]) for item in build_proof["outputs"]}
    for path in (EXE,EXE.parent/"build-report.json"):
        require(pin(path)==selected_outputs[str(path)],"Selected compiled artifact/receipt differs from independent proof")
    require(pin(EXE.parent/"receipt.json")==build_proof["receipt"],"Independent ABI build receipt differs")
    for path,item in {**runtime_pins(),**SYSTEM_PINS}.items():
        require(pin(path)==item,"Selected ABI DLL candidate differs");files.append(Path(path))
    # Source metadata may contain CPU/GGUF names. Only seven public header files
    # are selected here; no compiler, CPU backend, pack or weight file is opened.
    closure_path=HERE/"HEADER-CLOSURE-FOLLOWUP.json";files.append(closure_path)
    closure=json.loads(closure_path.read_bytes())
    require(closure["header_count"]==7 and not closure["unresolved_quoted_includes"],"Typed public header closure incomplete")
    for item in closure["headers"]:
        path=Path(item["local_path"])
        require({key:pin(path)[key] for key in ("bytes","sha256")}=={key:item[key] for key in ("bytes","sha256")},"Public header differs")
        files.append(path)
    acceptance_path=q.PREVIOUS/"acceptance.json";accepted=json.loads(acceptance_path.read_bytes())
    require(sha(acceptance_path)=="491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b","Accepted runtime anchor changed")
    wheel_path=q.PREVIOUS/"WHEEL-ENVIRONMENTS.json";wheel=json.loads(wheel_path.read_bytes())
    require({key:pin(wheel_path)[key] for key in ("bytes","sha256")}==accepted["evidence_files"][wheel_path.relative_to(ROOT).as_posix()]
            and sha(wheel["wheel"])==accepted["wheel"]["sha256"]==wheel["wheel_sha256"]
            and Path(wheel["default_python"])==q.DEFAULT,"Accepted wheel provenance changed")
    files.append(Path(wheel["wheel"]))
    with ZipFile(wheel["wheel"]) as archive:
        members=[name for name in archive.namelist() if name.startswith("asof/") and not name.endswith("/")]
        require(len(members)==85,"Accepted runtime closure differs")
        for name in members:
            path=q.DEFAULT.parent.parent/"Lib/site-packages"/name
            require(sha(path)==hashlib.sha256(archive.read(name)).hexdigest(),"Installed runtime file differs");files.append(path)
    return list({str(path):pin(path) for path in files}.values())


def execute(config,expected):
    output=validate_role(config);require(not output.exists(),"ABI output consumed; never restart")
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Accepted installed -I -B ABI parent required")
    started=time.monotonic();parent_end=started+60;child=output/"execution/child"
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;owner=None;leases=[]
    sinks=ExitStack();failure=None;failure_object=None;child_start=None;child_end=None
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(schema_version=1,status="failed",automatic_retry=False,captures=captures,finalization_errors=[],
        parent_GGUF_reads=0,model_paths_supplied_to_child=False,explicit_bridge_call_policy=dict(
            llama_version=1,llama_model_default_params=1,model_API=0,vocabulary_API=0,backend_init_API=0,
            GGML_registry_API=0,tokenizer_API=0,grammar_API=0),counters_instrumented=False,
        dependency_initializers_may_have_effects=True,attempt_reserved=False,call_return_observed=False)
    def event(name,**details):journal.append(name,**details)
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
    finally:
        if not reservation["owned"]:raise failure_object or RuntimeError("No exclusive ABI output ownership")
        if owner:
            # Preserve the original execution failure, then observe still-open
            # owned handles independently before unchanged Owner cleanup.
            try:
                terminal=terminal_observer()(owner,report,captures,locals().get("streams",{}),
                    sdk=sdk,event=event,work_deadline=min((child_end or parent_end)-2,parent_end-5),
                    drain_seconds=TERMINAL_POLICY["capture_drain_seconds"])
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
            if failure is None:
                try:
                    require(report["call_return_observed"] and report["returncode"]==0,"No successful observed ABI exit")
                    report["observations"]=validate_child_artifacts(child,config)
                    report["status"]="ABI_observations_retained_independent_qualification_pending"
                except BaseException as error:
                    failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
            try:owner.cleanup(min(child_end or parent_end,parent_end))
            except BaseException as error:
                report["owned_cleanup_exception"]=dict(error_class=type(error).__name__,error=str(error)[:512])
                failure=failure or report["owned_cleanup_exception"]
            report.update(reaped=owner.reaped,resumption=owner.resumption_record(),cleanup_errors=owner.cleanup_errors)
            if (not owner.reaped or owner.cleanup_errors) and failure is None:
                failure=dict(error_class="OwnedCleanupFailure",error="See retained owned cleanup")
        try:
            try:
                for stream in locals().get("streams",{}).values():stream.flush();os.fsync(stream.fileno())
            finally:sinks.close()
            report["child_full_process_elapsed_seconds"]=None if child_start is None else time.monotonic()-child_start
            require(child_start is None or report["child_full_process_elapsed_seconds"]<=30,"ABI child including cleanup exceeded30s")
            if api:
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    record=api.read_lease(item,parent_end,leases);record["final_recheck_close_attempted"]=True
                    try:api.close(record["handle"]);record["closed"]=True;record["final_recheck_close_return_observed"]=True
                    except BaseException as error:
                        detail=dict(phase="final_input_recheck_close",error_class=type(error).__name__,error=str(error)[:512])
                        record["cleanup_errors"].append(detail);record["final_recheck_close_return_observed"]=False
                        report["finalization_errors"].append(dict(path=record["path"],handle=record["handle"],**detail));raise
            sdk.finite_deadline(parent_end)
        except BaseException as error:
            detail=dict(phase="final_input_recheck_or_cleanup",error_class=type(error).__name__,error=str(error)[:2048])
            report["finalization_errors"].append(detail);failure=failure or detail
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


def prepare():
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11","Accepted -I -B parent required")
    require(not PROTOCOL.exists(),"ABI preparation already exists")
    proof=json.loads(PURE.read_bytes())
    require(proof["status"]=="passed" and proof["helper_sha256"]==sha(__file__)
            and proof["actual_children"]==0 and proof["real_sdk_constructions"]==0,"Fresh ABI pure checks required")
    inputs=collect_inputs()+[pin(PURE),pin(CHECKER)]
    output=safe(ROOT/"data/cache"/("r09-detached-ABI-observation-v2-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
    require(not output.exists(),"Exclusive ABI output exists")
    config=configuration(output,inputs);validate_role(config)
    with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(status="prepared_no_native_or_child",helper_sha256=sha(__file__),protocol_sha256=sha(PROTOCOL),inputs=len(inputs),output=str(output))))


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--execute":
        q.guard();expected=sys.argv[2];require(sha(PROTOCOL)==expected,"Exact separately reviewed ABI protocol required")
        result=execute(json.loads(PROTOCOL.read_bytes()),expected)
        print(json.dumps(dict(status=result["status"],output=result["terminal_seal"]["path"])))
        raise SystemExit(0 if result["status"]=="ABI_observations_retained_independent_qualification_pending" else 1)
    else:raise SystemExit("Prepare, peer-review and obtain separate root decision before --execute SHA256")
