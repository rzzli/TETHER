"""Prospective nine-argument recognition parent v6; source/pure only, asset/build-unbound.

Exact typed child: --recognize RUNTIME CHILD_OUTPUT PACK CPU SHARD1 SHARD2 SHARD3 (argc9). Original SDK gates remain
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
import math
import types
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
EXE=None  # No future recognition executable/build or asset verification is bound.
EXE_SHA=None
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
PROTOCOL=None
EXECUTION_AUTHORIZED=False
CONTRACT=HERE/"RECOGNITION-EXECUTION-CONTRACT-v1.json"
CONTRACT_SHA="30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"
TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
POLICY_SOURCE=HERE/"recognition_module_policy_v1.py"
POLICY_SOURCE_SHA="5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12"
POLICY_ID="trusted-System32-recognition-v1"
POLICY_SHA="4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
TERMINAL_POLICY=dict(capture_drain_seconds=0.25,maximum_capture_polls=64,
    physical_pipe_EOF_is_not_child_exit=True,unknown_creation_is_not_final=True,
    skip_new_observations_and_input_rechecks_after_interruption=True,late_returned_bytes_retained=True)
LIMITS=dict(parent_seconds=300,child_seconds=120,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=8388608,row_bytes=65536)
RUNTIME_EXPECTED={
    "libomp.dll":dict(bytes=768000,sha256="a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c"),
    "ggml-base.dll":dict(bytes=803840,sha256="84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3"),
    "ggml.dll":dict(bytes=78848,sha256="2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba"),
    "llama.dll":dict(bytes=3581952,sha256="166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d")}



ROLES_SOURCE=HERE/"recognition_runtime_roles_v2.py"
ROLES_SHA='97eb16d55ea84d9e8193e2195e977469e87acbef4d838ad049cc9771ea75a344'
EXPECTED_PACK=HERE/"RECOGNITION-EXPECTED-PACK-METADATA-v1.json"
EXPECTED_PACK_SHA="096e1234e239d04c3b276295e7176f5886f139a4064c3fc5f207745f8938f64d"
VALIDATOR_SOURCE=HERE/"recognition_validation_v3.py"
VALIDATOR_SHA='bbd98b162bf47ff035a945cca29b97c5290113b39c8b1efb7770abc89f0ca229'
WIRE=HERE/"RECOGNITION-CHILD-WIRE-v2.json"
WIRE_SHA='d578bc2179e55f7866dd7b2df3ec3169fdc3bcb0dee58629c2a31b8d366d0d01'
SEALER_SOURCE=HERE/"recognition_status_seal_v1.py"
SEALER_SHA='652b8ea5a7b612ef16636d114b3e9b8a24dc99b35aede10410ab0fac4f1595aa'
_OWNER_STARTED=None
_OWNER_DEADLINE=None
PERIODIC_JOB_SECONDS=3.5  # At most40 raw snapshots over the bounded120s child.


def metadata_path(path):
    path=Path(path)
    require(path.suffix.casefold() not in (".gguf",".dll",".pyd"),"Binary/model payload cannot enter metadata-only hashing")
    return safe(path)


def check_owner_clock():
    if _OWNER_DEADLINE is not None:sdk.finite_deadline(_OWNER_DEADLINE)


def sha(path):
    path=metadata_path(path);check_owner_clock()
    require(path.stat().st_size<=128*1024**2,"Small software/metadata hash cap")
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            check_owner_clock();block=stream.read(65536)
            if not block:break
            digest.update(block);check_owner_clock()
    check_owner_clock();return digest.hexdigest()


def pin(path):
    path=metadata_path(path);check_owner_clock();before=path.stat().st_size
    result=dict(path=str(path),bytes=before,sha256=sha(path))
    require(path.stat().st_size==before,"Metadata size changed while hashing");check_owner_clock()
    return result


def own_source(path,expected,name):
    path=metadata_path(path);check_owner_clock();require(path.stat().st_size<=2*1024**2,"Own-source cap")
    chunks=[]
    with path.open("rb") as stream:
        while True:
            check_owner_clock();block=stream.read(65536)
            if not block:break
            chunks.append(block);check_owner_clock()
    raw=b"".join(chunks);require(hashlib.sha256(raw).hexdigest()==expected,"Frozen own-source bytes changed")
    module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(raw,str(path),"exec"),module.__dict__);check_owner_clock()
    return module


def verified_metadata(path,expected):
    path=metadata_path(path);check_owner_clock()
    require(path.stat().st_size<=2*1024**2,"Bounded recognition metadata required")
    chunks=[];count=0
    with path.open("rb") as stream:
        while True:
            check_owner_clock();block=stream.read(65536)
            if not block:break
            count+=len(block);require(count<=2*1024**2,"Recognition metadata grew beyond cap")
            chunks.append(block);check_owner_clock()
    raw=b"".join(chunks)
    require(hashlib.sha256(raw).hexdigest()==expected,"Exact recognition metadata changed")
    value=json_value(raw);check_owner_clock();return value


def source_contract():
    return verified_metadata(CONTRACT,CONTRACT_SHA)


def expected_pack():
    return verified_metadata(EXPECTED_PACK,EXPECTED_PACK_SHA)


def authority():
    raise RuntimeError("Unbound recognition source: no verified executable/build/asset authority or dispatch permission")


def roles():
    return own_source(ROLES_SOURCE,ROLES_SHA,"recognition_role_hash_primitives")


def payload_records():
    contract=source_contract();return [contract["CPU_descriptor"],*contract["ordered_shard_descriptors"],expected_pack()["pack"]]


def role_of(item,config,expected_protocol_sha256=None):
    contract=source_contract()
    if expected_protocol_sha256 is not None:
        # These two exact metadata files are reserved by the owner after the
        # acyclic input manifest was frozen. They never enter that manifest.
        own_paths={str(PROTOCOL),str(Path(config["output"])/"effective-protocol.json")}
        if item["path"] in own_paths:
            roles().strict_pin(item)
            require(item["sha256"]==expected_protocol_sha256 and item["bytes"]<=128*1024**2,
                "Owned protocol metadata differs from the exact driver-bound hash")
            return dict(role="software",cap=128*1024**2,expected_bytes=item["bytes"])
    return roles().validate_record(item,software_records=config["software_inputs"],CPU=contract["CPU_descriptor"],
        shards=contract["ordered_shard_descriptors"],pack=expected_pack()["pack"])


def validate_role_inputs(records,software):
    require(type(records) is list and type(software) is list,"Explicit software/payload lists required")
    expected=software+payload_records()
    require(len(records)==len(expected),"Exact recognition input count required")
    require(len({r["path"] for r in expected})==len(expected),"Software/payload role collision")
    by_path={r["path"]:r for r in expected};seen=set()
    for item in records:
        roles().strict_pin(item)
        require(item["path"] in by_path and item==by_path[item["path"]] and item["path"] not in seen,
            "Recognition input outside exact declared role")
        role_of(item,dict(software_inputs=software));seen.add(item["path"])
    require(seen==set(by_path),"Missing recognition input descriptor")
    return records


def recognition_argv(exe,runtime,child,pack,cpu,shards):
    require(EXE is not None and exe==EXE,"Future exact recognition executable is unbound")
    contract=source_contract();manifest=expected_pack()
    require(str(runtime)==str(RUNTIME) and str(pack)==manifest["pack"]["path"]
        and type(cpu) is str and cpu=="ggml-cpu-x64.dll"
        and type(shards) is list and [str(p) for p in shards]==[r["path"] for r in contract["ordered_shard_descriptors"]],
        "Exact pack/CPU/three ordered original model paths required")
    # Payload paths are compared as recorded strings, never stat/open/resolved in preparation.
    argv=[str(safe(exe)),"--recognize",str(safe(runtime)),str(safe(child,output=True)),str(pack),cpu,*[str(p) for p in shards]]
    require(len(argv)==9 and all("\0" not in value for value in argv),"Exact nine-argument recognition role required")
    command=subprocess.list2cmdline(argv);require(len(command.encode("utf-16-le"))//2+1<=32767,"Command line cap")
    return argv,command


def configuration(output,inputs):
    binding=authority();output=safe(output,output=True);software=binding["software_inputs"]
    validate_role_inputs(inputs,software);contract=source_contract();manifest=expected_pack()
    argv,command=recognition_argv(EXE,RUNTIME,output/"execution/child",manifest["pack"]["path"],"ggml-cpu-x64.dll",
        [r["path"] for r in contract["ordered_shard_descriptors"]])
    return dict(schema_version=1,kind="detached_singleton_recognition_observation_v1",mode="--recognize",helper=pin(__file__),
        executable=binding["executable"],software_inputs=software,payload_inputs=payload_records(),inputs=inputs,
        output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),limits=LIMITS,
        creation_flags=0x0008040C,maximum_attempts=1,automatic_retry=False,module_policy_id=POLICY_ID,module_policy_sha256=POLICY_SHA,
        expected_version="0.7.0-dev",expected_pack_sha256=manifest["pack"]["sha256"],contract_sha256=CONTRACT_SHA,
        parent_seconds=300,child_seconds=120,cooperative_work_ms=117000,full_vocabulary_mask=False,inference=False,
        scientific_validation="not_established",execution_authorized_by_preparation=False,
        hash_pass_policy=dict(driver_model_passes=0,parent_initial=1,child=1,parent_final=1,external_verifier_separately_timed=True),
        periodic_job_seconds=PERIODIC_JOB_SECONDS,original_SDK_general_gate=False)


def validate_role(config):
    binding=authority();validate_role_inputs(config["inputs"],binding["software_inputs"])
    require(exact(config,configuration(config["output"],config["inputs"])),"Exact singleton recognition role/configuration required")
    return safe(config["output"],output=True)


def collect_inputs():
    authority()  # Later exact acyclic binding must distinguish descriptors from runtime asset validation.


def prepare():
    authority()  # No future output/protocol/constructor is authorized by this source-only draft.


def policy_matcher():
    module=own_source(POLICY_SOURCE,POLICY_SOURCE_SHA,"recognition_phase_math")
    require(module.POLICY_ID==POLICY_ID and module.POLICY_SHA256==POLICY_SHA,"Phase policy fingerprint changed")
    return module


def status_sealer():
    return own_source(SEALER_SOURCE,SEALER_SHA,"recognition_status_only_sealer").make_sealer(sdk)


def validate_child_artifacts(child,config=None):
    contract=authority();child=safe(child,output=True)
    require(VALIDATOR_SHA is not None,"Recognition wire validator is not frozen")
    module=own_source(VALIDATOR_SOURCE,VALIDATOR_SHA,"pure_recognition_wire_validator")
    manifest=expected_pack();check_owner_clock()
    # Only the separately leased small frozen pack is read here, never model data.
    record=manifest["pack"];path=safe(record["path"]);require(path.stat().st_size==record["bytes"]<=20*1024**2,"Pack size changed")
    chunks=[];count=0
    with path.open("rb") as stream:
        while True:
            check_owner_clock();block=stream.read(65536)
            if not block:break
            count+=len(block);require(count<=record["bytes"],"Pack grew beyond bound");chunks.append(block);check_owner_clock()
    raw=b"".join(chunks);require(hashlib.sha256(raw).hexdigest()==record["sha256"],"Frozen pack changed")
    return module.validate_artifacts(child,contract=source_contract(),manifest=manifest,wire=verified_metadata(WIRE,WIRE_SHA),
        expected_self=str(EXE),expected_runtime=str(RUNTIME),match_modules=policy_matcher().match_modules,
        pack_raw=raw,safe=safe,check=check_owner_clock)


def parent_payload_observations(hash_records,lease_attempts,models,creation,resumption):
    """Derive bounded known/unknown observations; no zero-I/O or path-use inference."""
    paths={item["path"] for item in models}
    hashes=[dict(row) for row in hash_records if row.get("path") in paths]
    opens=[dict(row) for row in lease_attempts if row.get("path") in paths]
    attempted=bool(creation.get("api_attempt_reserved"));observed=bool(creation.get("return_observed"))
    success=creation.get("returned_success") if observed else None
    return dict(expected_model_descriptors=models,parent_model_lease_attempts=opens,parent_model_hash_observations=hashes,
        known_parent_model_hash_read_bytes=sum(row.get("known_returned_bytes",0) for row in hashes),
        parent_model_hash_read_attempts=sum(row.get("read_attempts",0) for row in hashes),
        parent_model_hash_read_returns=sum(row.get("read_returns",0) for row in hashes),
        unknown_or_incomplete_hash_stages=sum(not row.get("hash_complete",False) or row.get("status")!="verified" for row in hashes),
        reserved_model_open_outcomes_unobserved=sum(not row.get("return_observed",False) for row in opens),
        model_path_delivery=dict(paths_declared_in_fixed_argv=[m["path"] for m in models],creation_attempt_reserved=attempted,
            creation_return_observed=observed,creation_success_if_observed=success,
            successful_CreateProcess_call_included_declared_paths=bool(success) if observed else None,
            resumption=dict(resumption),actual_child_model_file_use="not_inferred_from_declared_paths_or_creation"),
        scope="Only bridge-parent leased hashing and observed launch states; unknown tails and OS/read-ahead/child I/O are not zero",zero_weight_IO_claim=False)



def terminal_observer():
    require(sha(TERMINAL_SOURCE)==TERMINAL_SHA,"Terminal observation component changed")
    spec=util.spec_from_file_location("fixed_ABI_terminal_observation_v3",TERMINAL_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.CAPTURE_DRAIN_SECONDS==TERMINAL_POLICY["capture_drain_seconds"]
            and module.MAX_CAPTURE_POLLS==TERMINAL_POLICY["maximum_capture_polls"],
            "Terminal observation policy differs")
    return module.observe_terminal


def api_class():
    class FixedRecognitionKernel32(sdk.Kernel32):
        def __init__(self,config,expected):
            validate_role(config)
            require(not config.get("pure_fixture"),"Synthetic recognition configuration cannot bind real SDK")
            require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK execution gate changed")
            self.config,self.expected,self.attempted=config,expected,False
            self.role_hash_records=[];self.role_lease_attempts=[];self.record_event=None
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
            require((argv,command)==recognition_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child",expected_pack()["pack"]["path"],"ggml-cpu-x64.dll",[r["path"] for r in source_contract()["ordered_shard_descriptors"]])
                    and environment==sdk.effective_environment(Path(self.config["output"]))
                    and Path(cwd)==Path(self.config["output"]),"Exact detached singleton recognition-only launch required")
            require(not self.attempted,"Recognition attempt already reserved; no repeat");self.attempted=True
            return super().create_suspended(argv,command,environment,cwd,handles,pi,job,creation,event)
        def read_lease(self,item,deadline,ownership):
            role=role_of(item,self.config,self.expected);module=roles()
            path=module.runtime_path(item,role=role,deadline=deadline,check=sdk.finite_deadline)
            require(self.record_event is not None,"Runtime lease event sink required")
            self.record_event("recognition_lease_attempt_reserved",path=str(path),role=role["role"])
            attempt=dict(path=str(path),role=role["role"],attempt_reserved=True,return_observed=False,returned_success=None)
            self.role_lease_attempts.append(attempt)
            handle=self.k.CreateFileW(str(path),0x80000000,1,None,3,0x00200000|0x80,None)
            attempt.update(return_observed=True,returned_success=handle not in (None,0,sdk.INVALID))
            self.win(handle not in (None,0,sdk.INVALID),"Lease exact original recognition file")
            record=dict(handle=int(handle),path=str(path),closed=False,validation="pending",cleanup_errors=[])
            ownership.append(record)
            try:
                self.validate_lease(handle,path,item,deadline);record["validation"]="passed";return record
            except BaseException as primary:
                record.update(validation="failed",primary_error=dict(error_class=type(primary).__name__,error=str(primary)[:512]))
                try:self.close(handle);record["closed"]=True
                except BaseException as error:record["cleanup_errors"].append(dict(error_class=type(error).__name__,error=str(error)[:512]))
                raise
        def hash_lease(self,handle,item,deadline):
            roles().hash_lease(self,sdk,handle,item,deadline,role=role_of(item,self.config,self.expected),records=self.role_hash_records,event=self.record_event)
    return FixedRecognitionKernel32


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


def execute(config,expected,*,owner_started):
    global _OWNER_STARTED,_OWNER_DEADLINE
    require(type(owner_started) in (int,float) and not isinstance(owner_started,bool) and math.isfinite(owner_started)
        and owner_started<=time.monotonic(),"Trusted driver monotonic owner start required before import/validation")
    require(_OWNER_STARTED is None,"Recognition owner scope already consumed; no repeat")
    started=owner_started;parent_end=started+300
    _OWNER_STARTED,_OWNER_DEADLINE=started,parent_end-5
    sdk.finite_deadline(parent_end-5)
    output=validate_role(config);require(not output.exists(),"Recognition output consumed; never restart")
    require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode
            and Path(sys.executable)==q.DEFAULT and metadata.version("asof-target-agents")=="0.3.11",
            "Accepted installed -I -B recognition parent required")
    child=output/"execution/child"
    journal=None;reservation=dict(owned=False,journal_reserved=False);api=None;owner=None;leases=[]
    sinks=ExitStack();failure=None;failure_object=None;child_start=None;child_end=None;interrupted=False
    captures={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,eof=False) for name in ("stdout","stderr")}
    report=dict(schema_version=1,status="failed",automatic_retry=False,captures=captures,finalization_errors=[],
        parent_payload_observations_pending=True,explicit_bridge_call_policy=dict(
            scope="Exactly25 explicit bridge APIs, bounded by frozen per-API/aggregate contract",inference_API=0,full_vocabulary_mask=False),
        counter_scope=dict(parent_lease_and_hash_attempts=True,child_explicit_export_snapshots_expected=True,
            native_internal_OS_effects_instrumented=False,child_snapshots="unknown_until_validated"),
        partial_coverage=dict(status="not_inspected_unknown",expected_case_results=189,expected_prefix_results=6,no_absence_inference=True),
        dependency_initializers_may_have_effects=True,attempt_reserved=False,call_return_observed=False)
    def event(name,**details):journal.append(name,**details)
    def note_interruption(error,phase):
        nonlocal interrupted
        if isinstance(error,(KeyboardInterrupt,SystemExit)):
            interrupted=True
            report.setdefault("interruptions",[]).append(dict(phase=phase,error_class=type(error).__name__,identity_checked=True))
    try:
        journal=sdk.reserve_parent_journal(output,reservation)
        event("detached_recognition_attempt_reserved",protocol_sha256=expected,limits=LIMITS)
        report["attempt_reserved"]=True
        child.mkdir();write_new(output/"effective-protocol.json",config)
        require(sha(output/"effective-protocol.json")==expected,"Recognition protocol archive differs")
        api=api_class()(config,expected);api.record_event=event;report["role_hash_records"]=api.role_hash_records
        for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
            sdk.finite_deadline(parent_end-5);api.read_lease(item,parent_end-5,leases)
        owner=sdk.OwnedLaunch(api,event)
        streams={name:sinks.enter_context((output/(name+".bin")).open("xb")) for name in captures}
        child_start=time.monotonic();child_end=min(child_start+120,parent_end-5)
        check=lambda:sdk.finite_deadline(child_end-2)
        owner.start(config["argv"],config["command_line"],config["environment"],output,check)
        owner.observe_job("running_first","running_or_finished");last=time.monotonic()
        while True:
            check();sdk.capture_poll(owner,captures,streams)
            if api.wait(owner.pi.hProcess,0):break
            if time.monotonic()-last>=PERIODIC_JOB_SECONDS:owner.observe_job("running_periodic","running_or_finished");last=time.monotonic()
            time.sleep(.01)
        report["returncode"]=api.exit_code(owner.pi.hProcess);report["call_return_observed"]=True
        require(report["returncode"]==0,"Recognition child failed")
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
                    require(report["call_return_observed"] and report["returncode"]==0,"No successful observed recognition exit")
                    report["observations"]=validate_child_artifacts(child,config)
                    report["counter_scope"]["child_snapshots"]="complete_source_bound_snapshots_validated"
                    report["partial_coverage"]=dict(status="validated_complete",case_results=189,prefix_results=6)
                    report["status"]="recognition_observations_retained_independent_qualification_pending"
                except BaseException as error:
                    failure=dict(error_class=type(error).__name__,error=str(error)[:2048])
                    if hasattr(error,"coverage"):report["partial_coverage"]=error.coverage
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
            require(child_start is None or report["child_full_process_elapsed_seconds"]<=120,"Recognition child including cleanup exceeded120s")
            if api and interrupted:
                report["final_input_recheck"]=dict(status="skipped_due_to_interruption",new_read_leases=0,
                    new_eligibility_claim=False,original_lease_cleanup_still_required=True)
            elif api:
                report["final_input_recheck"]=dict(status="in_progress",new_read_leases=0,closed_recheck_leases=0,outcomes=[])
                for item in config["inputs"]+[pin(PROTOCOL),pin(output/"effective-protocol.json")]:
                    report["final_input_recheck"]["new_read_leases"]+=1
                    outcome=dict(path=item["path"],read_lease_reserved=True,return_observed=False,close_return_observed=False)
                    report["final_input_recheck"]["outcomes"].append(outcome)
                    sdk.finite_deadline(parent_end-5)
                    record=api.read_lease(item,parent_end-5,leases);outcome.update(return_observed=True,handle=record["handle"])
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
        # Bulk original-input work has ended. Only bounded metadata publication,
        # original handle closure and terminal sealing may use this final reserve.
        _OWNER_DEADLINE=parent_end
        try:
            report["clock_stage"]="reserved_finalization_no_new_payload_reads"
            report["parent_payload_observations"]=parent_payload_observations(
                getattr(api,"role_hash_records",[]),getattr(api,"role_lease_attempts",[]),
                [item for item in config["payload_inputs"] if item["path"].lower().endswith(".gguf")],
                dict(owner.creation) if owner else dict(api_attempt_reserved=False,return_observed=False,returned_success=None),
                owner.resumption_record() if owner else dict(state="not_attempted"))
            report["parent_payload_observations_pending"]=False
            if failure:
                report.update(status="failed",failure=failure)
                if not (output/"failure.json").exists():write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
            try:
                if journal:event("detached_recognition_terminal",status=report["status"],failure=failure)
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
            report.update(status="failed",failure=failure)
            note_interruption(error,"terminal_publication_or_derived_observations")
            try:write_new(output/"terminal-publication-error.json",dict(authoritative=True,automatic_retry=False,
                publication_error=detail,primary_failure=failure,finalization_errors=report["finalization_errors"]))
            except BaseException:pass
            if not (output/"failure.json").exists():
                try:write_new(output/"failure.json",dict(authoritative=True,automatic_retry=False,**failure))
                except BaseException:pass
        finally:
            try:
                # Idempotent close also covers failures before the normal
                # terminal-event/close block, including derived reporting.
                if journal:journal.close()
            except BaseException as error:
                detail=dict(phase="terminal_journal_close",error_class=type(error).__name__,error=str(error)[:512])
                report["finalization_errors"].append(detail);failure=failure or detail
                report.update(status="failed",failure=failure)
                note_interruption(error,"terminal_journal_close")
                try:write_new(output/"journal-close-error.json",dict(authoritative=True,automatic_retry=False,primary_failure=failure,cleanup_error=detail))
                except BaseException:pass
            finally:
                terminal=SEAL_POST_LEASE_CLEANUP(output,api,leases,failure,report["status"],started,parent_end)
                report["status"]=terminal["status"];report["terminal_seal"]=pin(output/"terminal-seal.json")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Qualified detached SDK gate changed")
    return report


SEAL_POST_LEASE_CLEANUP=status_sealer()  # Prebound own code before any attempted execution/interruption; no SDK mutation.


if __name__=="__main__":
    raise SystemExit("Source/pure-only unbound recognition parent; no prepare or execute CLI")
