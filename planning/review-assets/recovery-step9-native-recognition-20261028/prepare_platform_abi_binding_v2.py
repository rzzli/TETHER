"""Select an exact acyclic runtime basis and author one bound parent; no target execution."""
import ast
import hashlib
import json
from pathlib import Path
import stat

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=HERE/'run_platform_abi_observation_v2.py'
AUTHORITY=HERE/'TRUSTED-PLATFORM-ABI-STATIC-AUTHORITY-v1.json'
CONTRACT=HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v2.json'
PROOF=HERE/'TRUSTED-PLATFORM-BUILD-RESULT-VERIFICATION-v2.json'
PROOF_SHA='057c0fb212a9b7488f71a442182808c0f728c0b54f7a0fc83eaa13b400e51580'
CHECKER=HERE/'check_platform_abi_binding_v2.py'
PURE=HERE/'TRUSTED-PLATFORM-ABI-BINDING-PURE-PROOF-v2.json'
PROTOCOL=HERE/'TRUSTED-PLATFORM-ABI-EXECUTION-PROTOCOL-v1.json'
PREPARATION=ROOT/'data/cache/r09-trusted-platform-ABI-preparation-v2-20261029.json'
OLD_STATIC=HERE/'SELF-MODULE-CENSUS-STATIC-AUTHORITY-v2.json'
OLD_STATIC_SHA='70efee36da8aa73845fee25ba2eea495895a84b4cd9676c98ae9777ce084b42c'
PHASE_NAMES=(
    'qualify_detached_native_worker_v1.py','detached_parent_launch_draft_v1.py','abi_parent_launch_draft_v3.py',
    'DETACHED-POLICY-CONTRACT-v1.json','DETACHED-POLICY-DESIGN-v1.md',
    'DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json','DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json',
    'detached_abi_terminal_observation_v3.py','DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json',
    'HEADER-CLOSURE-FOLLOWUP.json','POST-CENSUS-PLATFORM-POLICY-ROOT-DECISION-v1.json',
    'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json','trusted_system32_module_policy_v1.py',
    'TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json','TRUSTED-SYSTEM32-PARENT-MATCHER-PURE-PROOF-v1.json',
    'check_trusted_system32_module_policy_v1.py','TRUSTED-SYSTEM32-PARENT-MATCHER-PEER-REVIEW-v1.json',
    'TRUSTED-SYSTEM32-CHILD-SOURCE-PEER-REVIEW-v1.json','TRUSTED-SYSTEM32-CHILD-SOURCE-PURE-PROOF-v1.json',
    'BRIDGE-SYMBOL-OWNERS-PURE-PROOF-v5.json','run_platform_abi_observation_v1.py',
    'TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json','check_platform_abi_parent_v3.py',
    'TRUSTED-SYSTEM32-ABI-PARENT-PURE-PROOF-v3.json','run_detached_abi_observation_v6.py',
)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def safe_leaf(path):
    path=Path(path).absolute()
    assert path.drive.casefold()!='e:' and path.suffix.casefold() not in {'.gguf','.pyd','.lib','.obj'}
    assert path.name.casefold() not in {'apphelp.dll','ggml-cpu-x64.dll','ggml-cpu.dll'}
    assert path not in {PARENT,AUTHORITY,CHECKER,PURE,PROTOCOL,PREPARATION}
    for part in (path,*path.parents):
        assert not part.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    assert path.is_file() and path.stat().st_size<=128*1024**2
    return path

def pin(path):
    path=safe_leaf(path);return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path))

def verified(record):
    assert type(record) is dict and set(record)=={'path','bytes','sha256'}
    assert pin(record['path'])==record
    return Path(record['path'])

def write(path,value):
    with path.open('xb') as stream:stream.write((json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))

def main():
    assert not any(p.exists() for p in (PARENT,AUTHORITY,CONTRACT)),'Bound artifacts already exist'
    assert sha(PROOF)==PROOF_SHA and sha(OLD_STATIC)==OLD_STATIC_SHA
    build=json.loads(PROOF.read_text(encoding='utf-8'))
    assert build['status']=='VERIFIED_trusted_platform_bridge_compiled_recognition_disabled_NOT_EXECUTED'
    assert build['executable']['sha256']=='2feffe29d916f9345067d9458714525eb73a2554824f3567383856562c2b2464'
    protocol=json.loads(verified(build['protocol']).read_text(encoding='utf-8'))
    original=json.loads(OLD_STATIC.read_text(encoding='utf-8'))['static_inputs']
    default=ROOT/'data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe'
    site=default.parent.parent/'Lib/site-packages'
    public=json.loads((HERE/'HEADER-CLOSURE-FOLLOWUP.json').read_text(encoding='utf-8'))['headers']
    public_paths={row['local_path'] for row in public};assert len(public_paths)==7
    sdk_root=Path(r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um')
    generation=HERE.parent/'recovery-step9-generation-contract-20261028'
    fixed={str(default),str(default.parent.parent/'pyvenv.cfg'),
        str(Path(r'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe')),
        str(generation/'acceptance.json'),str(generation/'WHEEL-ENVIRONMENTS.json'),
        str(ROOT/'data/cache/recovery-step9-generation-wheel-20261028/dist/asof_target_agents-0.3.11-py3-none-any.whl')}
    selected=[]
    for row in original:
        path=Path(row['path'])
        if (str(path) in fixed or str(path) in public_paths or path.parent==sdk_root
            or path.parent==Path(r'C:\Windows\System32') or path.parent==Path(protocol['header']['path']).parents[1]/'runtime'
            or (site in path.parents and ('asof' in path.parts or path.name in {'METADATA','WHEEL','entry_points.txt'}))):
            selected.append(verified(row))
    assert len([p for p in selected if site/'asof' in p.parents])==85
    assert len([p for p in selected if p.parent==sdk_root])==6
    assert len([p for p in selected if p.parent==Path(r'C:\Windows\System32')])==16
    files=selected+[Path(__file__).resolve(),PROOF,*(HERE/name for name in PHASE_NAMES)]
    for key in ('executable','source','compiled_source_copy','header','protocol','receipt','terminal','cleanup',
                'root_decision','build_peer','source_peer','child_pure_proof','matcher_peer','matcher_proof','shared_vectors','policy_contract'):
        files.append(verified(build[key]))
    prepared=Path(build['header']['path']).parent
    copies=[Path(row['path']) for row in protocol['header_copies']]
    assert len(copies)==7 and {p.name for p in copies}=={Path(p).name for p in public_paths}
    files.extend(copies)
    for row in protocol['inputs']:
        path=Path(row['path'])
        if path.parent==ROOT/'data/cache/approved-native-mirror-20261028T004531Z/runtime':files.append(verified(row))
    build_root=Path(build['output_directory'])
    report=next(row for row in build['outputs'] if row['path']=='build-report.json')
    files.append(verified(dict(path=str(build_root/report['path']),bytes=report['bytes'],sha256=report['sha256'])))
    contract=json.loads((HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json').read_text(encoding='utf-8'))
    contract.update(status='prospective_verified_build_trusted_platform_ABI_contract_not_execution_permission',
        verified_bridge_executable=build['executable'],verified_build_proof=pin(PROOF),
        compiled_source=build['source'],compiled_source_copy=build['compiled_source_copy'],runtime_pin_header=build['header'],
        build_protocol=build['protocol'],build_receipt=build['receipt'],build_terminal=build['terminal'],
        build_cleanup=build['cleanup'],module_guard_scope='Bounded current-process reported metadata at the ABI guard; not complete lifetime dependency attestation')
    write(CONTRACT,contract);files.append(CONTRACT)
    unique={str(Path(p).absolute()):Path(p).absolute() for p in files}
    assert len(unique)==len({p.casefold() for p in unique})
    allowed_dlls={str(ROOT/'data/cache/approved-native-mirror-20261028T004531Z/runtime'/name)
        for name in contract['semantic_policy']['core_names']}|{row['path'] for row in original if Path(row['path']).parent==Path(r'C:\Windows\System32')}
    allowed_exes={str(default),str(Path(r'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe')),build['executable']['path']}
    for path in unique.values():
        if path.suffix.casefold()=='.dll':assert str(path) in allowed_dlls
        if path.suffix.casefold()=='.exe':assert str(path) in allowed_exes
    records=[pin(unique[name]) for name in sorted(unique,key=str.casefold)]
    assert len([r for r in records if r['path'] in allowed_dlls])==20
    manifest=dict(schema_version=1,status='verified_build_static_basis_not_execution_permission',mode='--abi',
        executable=build['executable'],verified_build=pin(PROOF),ABI_contract=pin(CONTRACT),
        module_policy_id=contract['module_policy_id'],module_policy_sha256=contract['module_policy_sha256'],
        ABI_eligibility_established=False,execution_authorized=False,static_inputs=records,
        closure_scope='Exact selected interpreter/accepted85+3/wheel/SDK6/public14/qualified mechanics/new build/core4 and prior System16 pins. System16 are original lease context, not platform eligibility or complete dependency authentication.',
        forbidden_dynamic_dependencies=['current parent bytes','this manifest own bytes','current parent-dependent checker/proof/review','execution protocol','future output'])
    write(AUTHORITY,manifest)
    base=(HERE/'run_platform_abi_observation_v1.py').read_text(encoding='utf-8')
    census=(HERE/'run_self_module_census_v3.py').read_text(encoding='utf-8')
    funcs=lambda text:{n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    before,old=funcs(base),funcs(census)
    base=base[:base.index('def authority():')]
    base=base.replace('Prospective trusted-platform ABI parent v1; source/pure only, build-unbound.',
        'Trusted-platform ABI parent v2; exact acyclic runtime metadata preparation only.')
    base=base.replace('Authority, configuration, collection and preparation reject until a separately versioned binding.\nThe preserved execute body is unreachable through this draft. No dispatch permission is created.',
        'Preparation grants no execution permission. Only a separately reviewed root driver and exact once-only decision may call execute. The original SDK gate remains false.')
    base=base.replace('EXE=None  # Deliberately no future executable/build binding.',f'EXE=Path({build["executable"]["path"]!r})')
    base=base.replace('EXE_SHA=None',f'EXE_SHA={build["executable"]["sha256"]!r}')
    base=base.replace('PROTOCOL=None',f'PROTOCOL=HERE/{PROTOCOL.name!r}')
    base=base.replace('CONTRACT=HERE/"TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json"',f'CONTRACT=HERE/{CONTRACT.name!r}')
    old_contract_sha=sha(HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json')
    base=base.replace(f'CONTRACT_SHA="{old_contract_sha}"',f'CONTRACT_SHA={sha(CONTRACT)!r}')
    base+=f'''\nEXECUTION_AUTHORITY=HERE/{AUTHORITY.name!r}
EXECUTION_AUTHORITY_SHA={sha(AUTHORITY)!r}
VERIFIED_BUILD=HERE/{PROOF.name!r}
VERIFIED_BUILD_SHA={PROOF_SHA!r}
CHECKER=HERE/{CHECKER.name!r}
PURE=HERE/{PURE.name!r}
PREPARATION=ROOT/{PREPARATION.relative_to(ROOT).as_posix()!r}
STATIC_PATHS={tuple(r['path'] for r in records)!r}
'''
    authority='''def authority():
    require(bool(STATIC_PATHS) and sha(EXECUTION_AUTHORITY)==EXECUTION_AUTHORITY_SHA,"Exact acyclic static authority changed")
    value=json_value(EXECUTION_AUTHORITY.read_bytes())
    require(type(value) is dict and set(value)=={"schema_version","status","mode","executable","verified_build","ABI_contract",
        "module_policy_id","module_policy_sha256","ABI_eligibility_established","execution_authorized","static_inputs","closure_scope","forbidden_dynamic_dependencies"},
        "Exact trusted-platform static authority schema required")
    require(type(value["schema_version"]) is int and value["schema_version"]==1
        and value["status"]=="verified_build_static_basis_not_execution_permission" and value["mode"]=="--abi"
        and value["execution_authorized"] is False and value["ABI_eligibility_established"] is False,
        "Static basis cannot grant execution or ABI eligibility")
    validate_static_records(value["static_inputs"])
    by_path={r["path"]:r for r in value["static_inputs"]}
    require(value["executable"]==by_path[str(EXE)] and value["executable"]["sha256"]==EXE_SHA
        and value["verified_build"]==by_path[str(VERIFIED_BUILD)] and value["verified_build"]["sha256"]==VERIFIED_BUILD_SHA
        and value["ABI_contract"]==by_path[str(CONTRACT)] and value["ABI_contract"]["sha256"]==CONTRACT_SHA,
        "Verified executable/build/contract static bindings differ")
    require(value["module_policy_id"]==POLICY_ID and value["module_policy_sha256"]==POLICY_SHA,
        "Static module policy fingerprint differs")
    require(sha(VERIFIED_BUILD)==VERIFIED_BUILD_SHA and sha(CONTRACT)==CONTRACT_SHA
        and sha(q.SDK_SOURCE)==SDK_SHA and sdk.NATIVE_EXECUTION_ENABLED is False,"Critical build/contract/SDK boundary changed")
    contract=json_value(CONTRACT.read_bytes());build=json_value(VERIFIED_BUILD.read_bytes())
    require(contract["verified_bridge_executable"]==value["executable"]==build["executable"]
        and contract["verified_build_proof"]==value["verified_build"]
        and build["status"]=="VERIFIED_trusted_platform_bridge_compiled_recognition_disabled_NOT_EXECUTED"
        and contract["module_policy_id"]==POLICY_ID and contract["module_policy_sha256"]==POLICY_SHA
        and contract["execution_authorized"] is False,"Current bound ABI contract differs")
    return dict(contract,static_inputs=value["static_inputs"])
'''
    configuration='''def configuration(output,inputs):
    binding=authority();output=safe(output,output=True);validate_inputs(inputs,binding["static_inputs"])
    argv,command=abi_argv(EXE,RUNTIME,output/"execution/child")
    return dict(schema_version=1,kind="detached_trusted_platform_ABI_observation_v1",helper=pin(__file__),
        authority=pin(EXECUTION_AUTHORITY),executable=binding["verified_bridge_executable"],verified_build=binding["verified_build_proof"],
        contract_sha256=CONTRACT_SHA,runtime_pins=list(runtime_pins().values()),mode="--abi",module_policy_id=POLICY_ID,
        module_policy_sha256=POLICY_SHA,platform_image_authentication="not_established",reported_platform_path_filesystem_operations=0,
        output=str(output),argv=argv,command_line=command,environment=sdk.effective_environment(output),inputs=inputs,
        limits=LIMITS,creation_flags=0x0008040C,maximum_attempts=1,automatic_retry=False,
        explicit_target_calls=["llama_version","llama_model_default_params"],recognition_enabled=False,
        no_model_or_CPU_paths_supplied=True,initializer_effects_instrumented=False,expected_version="",
        version_expected_previously_known=False,execution_authorized_by_preparation=False,
        qualified_sdk_sha256=SDK_SHA,qualified_harmless_sha256=QUALIFICATION_SHA,terminal_component=pin(TERMINAL_SOURCE),terminal_policy=TERMINAL_POLICY)
'''
    role='''def validate_role(config):
    binding=authority();validate_inputs(config["inputs"],binding["static_inputs"])
    require(exact(config,configuration(config["output"],config["inputs"])),"Exact trusted-platform ABI-only role/configuration required")
    return safe(config["output"],output=True)
'''
    prepare=old['prepare'].replace('Census','Trusted-platform ABI').replace('census','trusted-platform ABI')
    prepare=prepare.replace('r09-self-module-trusted-platform ABI-v1-','r09-trusted-platform-ABI-observation-v1-')
    prepare=prepare.replace('prepared_trusted-platform ABI_only_not_execution_authority','prepared_ABI_only_not_execution_authority')
    names=('validate_static_records','dynamic_paths','validate_inputs','collect_inputs')
    blocks=[old[n] for n in names]+[authority]
    for name in ('policy_matcher','terminal_observer','api_class','exact','json_value','runtime_pins','validate_modules','validate_child_rows','validate_child_artifacts','abi_argv'):
        blocks.append(before[name])
    blocks.extend((configuration,role,before['execute'],prepare,
        'if __name__=="__main__":\n    if sys.argv[1:]==["--prepare"]:prepare()\n    else:raise SystemExit("Preparation-only CLI; constructor/dispatch requires separate exact root decision and audited driver")'))
    with PARENT.open('x',encoding='utf-8',newline='\n') as stream:stream.write(base+'\n\n'+'\n\n\n'.join(blocks)+'\n')
    ast.parse(PARENT.read_text(encoding='utf-8'))
    print(json.dumps(dict(status='bound_source_static_authority_written_no_preparation_or_dispatch',parent=pin(PARENT) if False else dict(path=str(PARENT),sha256=sha(PARENT)),
        authority=pin(AUTHORITY) if False else dict(path=str(AUTHORITY),sha256=sha(AUTHORITY)),contract=pin(CONTRACT),static_inputs=len(records),bytes=sum(r['bytes'] for r in records),children=0,SDK_constructors=0)))

if __name__=='__main__':main()
