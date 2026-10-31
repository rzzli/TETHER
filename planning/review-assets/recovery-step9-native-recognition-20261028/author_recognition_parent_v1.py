"""Author unbound nine-argument recognition parent from qualified mechanics; no target calls."""
import ast
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE/'run_platform_abi_observation_v1.py'
old=OLD.read_text(encoding='utf-8');tree=ast.parse(old)
funcs={n.name:ast.get_source_segment(old,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
SOURCE=HERE/'run_recognition_observation_v1.py'
prefix=old[:old.index('def authority():')]
prefix=prefix.replace('Prospective trusted-platform ABI parent v1; source/pure only, build-unbound.',
    'Prospective nine-argument recognition parent v1; source/pure only, asset/build-unbound.')
prefix=prefix.replace('import time','import time\nimport math\nimport types')
prefix=prefix.replace('EXE=None  # Deliberately no future executable/build binding.','EXE=None  # No future recognition executable/build or asset verification is bound.')
prefix=prefix.replace('CONTRACT=HERE/"TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json"','CONTRACT=HERE/"RECOGNITION-EXECUTION-CONTRACT-v1.json"')
prefix=prefix.replace('CONTRACT_SHA="5d7b30f66c86abd5b7c1c5d0aed6389986ff2cf900e739ca5fc475125e54ccf7"',
    'CONTRACT_SHA="30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"')
prefix=prefix.replace('trusted_system32_module_policy_v1.py','recognition_module_policy_v1.py')
prefix=prefix.replace('77e39b3bb82fb83049aba9956da0251b4a8d914f167dc6d6512d554ad7bfb3a8','5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12')
prefix=prefix.replace('trusted-System32-platform-v1','trusted-System32-recognition-v1')
prefix=prefix.replace('807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589','4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713')
prefix=prefix.replace('parent_seconds=60,child_seconds=30','parent_seconds=300,child_seconds=120')
prefix=prefix.replace('result_bytes=4194304','result_bytes=8388608')
roles_sha=hashlib.sha256((HERE/'recognition_runtime_roles_v1.py').read_bytes()).hexdigest()
prefix+=f'''\nROLES_SOURCE=HERE/"recognition_runtime_roles_v1.py"
ROLES_SHA={roles_sha!r}
EXPECTED_PACK=HERE/"RECOGNITION-EXPECTED-PACK-METADATA-v1.json"
EXPECTED_PACK_SHA="096e1234e239d04c3b276295e7176f5886f139a4064c3fc5f207745f8938f64d"
VALIDATOR_SOURCE=HERE/"recognition_validation_v1.py"
VALIDATOR_SHA=None  # Frozen only after coordinated child-wire/source review.
_OWNER_STARTED=None
_OWNER_DEADLINE=None
PERIODIC_JOB_SECONDS=3.5  # At most40 raw snapshots over the bounded120s child.
'''
helpers='''def metadata_path(path):
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


def source_contract():
    require(sha(CONTRACT)==CONTRACT_SHA,"Recognition source contract changed")
    value=json_value(CONTRACT.read_bytes());check_owner_clock();return value


def expected_pack():
    require(sha(EXPECTED_PACK)==EXPECTED_PACK_SHA,"Frozen expected pack metadata changed")
    value=json_value(EXPECTED_PACK.read_bytes());check_owner_clock();return value


def authority():
    raise RuntimeError("Unbound recognition source: no verified executable/build/asset authority or dispatch permission")


def roles():
    return own_source(ROLES_SOURCE,ROLES_SHA,"recognition_role_hash_primitives")


def payload_records():
    contract=source_contract();return [contract["CPU_descriptor"],*contract["ordered_shard_descriptors"],expected_pack()["pack"]]


def role_of(item,config):
    contract=source_contract()
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
    require(len(argv)==9 and all("\\0" not in value for value in argv),"Exact nine-argument recognition role required")
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


def validate_child_artifacts(child,config=None):
    contract=authority();child=safe(child,output=True)
    require(VALIDATOR_SHA is not None,"Recognition wire validator is not frozen")
    module=own_source(VALIDATOR_SOURCE,VALIDATOR_SHA,"pure_recognition_wire_validator")
    return module.validate_artifacts(child,contract=source_contract(),manifest=expected_pack(),
        expected_self=str(EXE),expected_runtime=str(RUNTIME),safe=safe,check=check_owner_clock)
'''
api=funcs['api_class'].replace('class FixedABIKernel32','class FixedRecognitionKernel32').replace('return FixedABIKernel32','return FixedRecognitionKernel32')
api=api.replace('abi_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child")',
    'recognition_argv(EXE,RUNTIME,Path(self.config["output"])/"execution/child",expected_pack()["pack"]["path"],"ggml-cpu-x64.dll",[r["path"] for r in source_contract()["ordered_shard_descriptors"]])')
api=api.replace('self.config,self.expected,self.attempted=config,expected,False','self.config,self.expected,self.attempted=config,expected,False\n            self.role_hash_records=[];self.record_event=None')
api=api.replace('    return FixedRecognitionKernel32','''        def read_lease(self,item,deadline,ownership):
            role=role_of(item,self.config);module=roles()
            path=module.runtime_path(item,role=role,deadline=deadline,check=sdk.finite_deadline)
            require(self.record_event is not None,"Runtime lease event sink required")
            self.record_event("recognition_lease_attempt_reserved",path=str(path),role=role["role"])
            handle=self.k.CreateFileW(str(path),0x80000000,1,None,3,0x00200000|0x80,None)
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
            roles().hash_lease(self,sdk,handle,item,deadline,role=role_of(item,self.config),records=self.role_hash_records,event=self.record_event)
    return FixedRecognitionKernel32''')
execute=funcs['execute']
execute=execute.replace('def execute(config,expected):','''def execute(config,expected,*,owner_started):
    global _OWNER_STARTED,_OWNER_DEADLINE
    require(type(owner_started) in (int,float) and not isinstance(owner_started,bool) and math.isfinite(owner_started)
        and owner_started<=time.monotonic(),"Trusted driver monotonic owner start required before import/validation")
    require(_OWNER_STARTED is None,"Recognition owner scope already consumed; no repeat")
    started=owner_started;parent_end=started+300
    _OWNER_STARTED,_OWNER_DEADLINE=started,parent_end-5
    sdk.finite_deadline(parent_end-5)''')
execute=execute.replace('started=time.monotonic();parent_end=started+60;child=output/"execution/child"','child=output/"execution/child"')
execute=execute.replace('api=api_class()(config,expected)','api=api_class()(config,expected);api.record_event=event;report["role_hash_records"]=api.role_hash_records')
execute=execute.replace('child_start+30','child_start+120').replace('time.monotonic()-last>=.9','time.monotonic()-last>=PERIODIC_JOB_SECONDS')
execute=execute.replace('report["child_full_process_elapsed_seconds"]<=30','report["child_full_process_elapsed_seconds"]<=120')
execute=execute.replace('exceeded30s','exceeded120s')
execute=execute.replace('record=api.read_lease(item,parent_end,leases)','sdk.finite_deadline(parent_end-5)\n                    record=api.read_lease(item,parent_end-5,leases)')
execute=execute.replace('ABI_observations_retained_independent_qualification_pending','recognition_observations_retained_independent_qualification_pending')
execute=execute.replace('llama_version=1,llama_model_default_params=1,model_API=0,vocabulary_API=0,backend_init_API=0,\n            GGML_registry_API=0,tokenizer_API=0,grammar_API=0',
    'scope="Exactly25 explicit bridge APIs, bounded by frozen per-API/aggregate contract",inference_API=0,full_vocabulary_mask=False')
blocks=[helpers,funcs['terminal_observer'],api,funcs['exact'],funcs['json_value'],execute,
    'if __name__=="__main__":\n    raise SystemExit("Source/pure-only unbound recognition parent; no prepare or execute CLI")']
with SOURCE.open('x',encoding='utf-8',newline='\n') as out:out.write(prefix+'\n\n'+'\n\n\n'.join(blocks)+'\n')
ast.parse(SOURCE.read_text(encoding='utf-8'))
print(str(SOURCE),hashlib.sha256(SOURCE.read_bytes()).hexdigest())
