"""Author exact metadata-only recognition authority and a narrow bound successor.

This author never follows CPU/model/pack descriptors. The future execution
protocol is deliberately absent until the bound parent's focused checks pass.
"""
import ast
import ctypes  # declarations before the audit hook; no WinDLL construction.
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=HERE/'run_recognition_observation_v7.py'
AUTHORITY=HERE/'RECOGNITION-STATIC-AUTHORITY-v1.json'
CHECKER=HERE/'check_recognition_binding_v1.py'
PURE=HERE/'RECOGNITION-BINDING-PURE-PROOF-v1.json'
PROTOCOL=HERE/'RECOGNITION-EXECUTION-PROTOCOL-v1.json'
PREPARATION=ROOT/'data/cache/r09-recognition-preparation-v1-20261029.json'
BUILD_PROOF=HERE/'RECOGNITION-BUILD-RESULT-VERIFICATION-v1.json'
BUILD_SHA='78a4d8c378836be294334801b42d6be16e0ef6c6ed49152014d2d5ded5319ddf'
OLD_STATIC=HERE/'SELF-MODULE-CENSUS-STATIC-AUTHORITY-v2.json'
OLD_SHA='70efee36da8aa73845fee25ba2eea495895a84b4cd9676c98ae9777ce084b42c'
BASE=HERE/'run_recognition_observation_v6.py'
BASE_SHA='e1901097dca195b0c92deb144a226c885dbfb54b50cdba62ddba50fd59160917'
CONTRACT=HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
PACK_METADATA=HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'
START=time.monotonic()
DEADLINE=START+60
DENIED=[]
PAYLOAD_KEYS=set()

def key(path):return str(path).replace('/','\\').lower()
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('Metadata author cannot construct native/process/network APIs')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and key(args[0]) in PAYLOAD_KEYS:
        DENIED.append('payload_open');raise AssertionError('Descriptor-only payload cannot be opened')
sys.addaudithook(guard)

def tick():
    if time.monotonic()>=DEADLINE:raise TimeoutError('Metadata-author60s deadline')
def sha(path):
    tick();raw=Path(path).read_bytes();tick();return hashlib.sha256(raw).hexdigest()
def load(path,expected=None):
    raw=Path(path).read_bytes()
    if expected is not None:assert hashlib.sha256(raw).hexdigest()==expected
    return json.loads(raw)
def pin(path):
    tick();path=Path(path).absolute()
    assert key(path) not in PAYLOAD_KEYS
    assert path.drive.casefold()!='e:' and path.suffix.casefold() not in ('.gguf','.pyd','.obj','.lib')
    assert path.name.casefold() not in ('apphelp.dll','ggml-cpu-x64.dll','ggml-cpu.dll','cl.exe','link.exe')
    assert path not in (PARENT,AUTHORITY,CHECKER,PURE,PROTOCOL,PREPARATION)
    for part in (path,*path.parents):
        tick();assert not getattr(part.lstat(),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT
    assert path.is_file() and path.stat().st_size<=128*1024**2
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path))
def verified(row):
    assert type(row) is dict and set(row)=={'path','bytes','sha256'} and pin(row['path'])==row
    return Path(row['path'])
def write(path,value):
    with path.open('xb') as stream:stream.write((json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))

PHASE_NAMES=(
    'qualify_detached_native_worker_v1.py','detached_parent_launch_draft_v1.py','abi_parent_launch_draft_v3.py',
    'harmless_launch_seal_v2.py','DETACHED-POLICY-CONTRACT-v1.json','DETACHED-POLICY-DESIGN-v1.md',
    'DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json','DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json',
    'detached_abi_terminal_observation_v3.py','DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json','HEADER-CLOSURE-FOLLOWUP.json',
    'TRUSTED-PLATFORM-ABI-ACCEPTANCE-v1.json','TRUSTED-PLATFORM-ABI-RESULT-VERIFICATION-v1.json',
    'RECOGNITION-SOURCE-ROOT-DECISION-v1.json','RECOGNITION-BINDING-ROOT-DECISION-v1.json','RECOGNITION-BINDING-CHECKLIST-v1.json',
    'RECOGNITION-EXECUTION-CONTRACT-v1.json','RECOGNITION-EXPECTED-PACK-METADATA-v1.json','PACK-V2-RESULT-VERIFICATION.json',
    'recognition_module_policy_v1.py','RECOGNITION-MODULE-POLICY-v1.json','RECOGNITION-MODULE-VECTORS-v1.json',
    'RECOGNITION-MODULE-POLICY-PURE-PROOF-v1.json','trusted_system32_module_policy_v1.py',
    'recognition_runtime_roles_v2.py','RECOGNITION-RUNTIME-ROLES-PURE-PROOF-v2.json',
    'recognition_validation_v3.py','RECOGNITION-VALIDATION-PURE-PROOF-v3.json',
    'recognition_status_seal_v1.py','RECOGNITION-SEALER-PURE-PROOF-v1.json','RECOGNITION-CHILD-WIRE-v2.json',
    'recognition_runtime_pins_v1.hpp','RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json',
    'run_recognition_observation_v6.py','RECOGNITION-PARENT-ROLE-PURE-PROOF-v6.json',
    'RECOGNITION-PARENT-INTEGRATION-PURE-PROOF-v6.json','RECOGNITION-PARENT-SOURCE-PEER-REVIEW-v2.json',
    'RECOGNITION-PARENT-SOURCE-PREPARATION-v1.json',
)

BINDING_CODE=r'''
def dynamic_paths():
    return (Path(__file__).resolve(),EXECUTION_AUTHORITY,CHECKER,PURE)


def validate_static_records(records):
    require(type(records) is list and len(records)==len(STATIC_PATHS),"Exact static software count required")
    rr=roles();expected=set(STATIC_PATHS);seen=set();keys=set()
    forbidden={rr.collision_key(str(p)) for p in (*dynamic_paths(),PROTOCOL,PREPARATION)}
    forbidden.update(rr.collision_key(r["path"]) for r in payload_records())
    for row in records:
        rr.strict_pin(row);path=row["path"];identity=rr.collision_key(path)
        require(path in expected and path not in seen and identity not in keys,"Static software addition/alias/duplicate")
        require(identity not in forbidden,"Static/dynamic/payload/protocol dependency cycle")
        require(row["bytes"]<=128*1024**2,"Software cannot use payload size exception")
        seen.add(path);keys.add(identity)
    require(seen==expected,"Missing exact static software")
    return records


def validate_software_inputs(records,static):
    validate_static_records(static)
    require(type(records) is list and len(records)==len(static)+4,"Exact static plus four dynamic software inputs required")
    rr=roles();expected={r["path"]:r for r in static};dynamic={str(p) for p in dynamic_paths()};seen=set();keys=set()
    require(len(dynamic)==4 and not(set(expected)&dynamic),"Static/dynamic authority dependency cycle")
    forbidden={rr.collision_key(r["path"]) for r in payload_records()}
    forbidden.update(rr.collision_key(str(p)) for p in (PROTOCOL,PREPARATION))
    for row in records:
        rr.strict_pin(row);path=row["path"];identity=rr.collision_key(path)
        require(row["bytes"]<=128*1024**2 and path in set(expected)|dynamic and path not in seen and identity not in keys,
            "Software outside exact finite static/dynamic roster")
        require(identity not in forbidden,"Software/payload/owner authority collision")
        require(path not in expected or row==expected[path],"Static software pin changed")
        seen.add(path);keys.add(identity)
    require(seen==set(expected)|dynamic,"Missing software metadata")
    # All role/schema/collision checks precede the first current dynamic leaf read.
    by_path={r["path"]:r for r in records}
    require(all(by_path[str(p)]==pin(p) for p in dynamic_paths()),"Dynamic parent/authority/checker/proof bytes changed")
    return records


def software_pin(path):
    # Only this reviewed software universe can bypass metadata_path's DLL ban.
    # Payload descriptors are screened as strings before any safe/stat/open call.
    require(type(path) in (str,type(Path())),"Software path required")
    path=Path(path);allowed=set(STATIC_PATHS)|{str(p) for p in dynamic_paths()}
    require(str(path) in allowed,"File outside exact software roster")
    forbidden={roles().collision_key(r["path"]) for r in payload_records()}
    require(roles().collision_key(str(path)) not in forbidden,"Descriptor-only payload cannot be software")
    check_owner_clock();path=safe(path);before=path.stat()
    require(path.is_file() and before.st_size<=128*1024**2,"Bounded regular software leaf required")
    digest=hashlib.sha256();total=0
    with path.open("rb") as stream:
        while True:
            check_owner_clock();block=stream.read(65536)
            if not block:break
            total+=len(block);require(total<=128*1024**2,"Software grew beyond cap")
            digest.update(block);check_owner_clock()
    after=path.stat();require(before.st_size==total==after.st_size,"Software changed size during hash")
    check_owner_clock();return dict(path=str(path),bytes=total,sha256=digest.hexdigest())


def build_output_record(build,relative):
    require(type(relative) is str and relative in ("build-report.json","receipt.json","terminal-seal.json","post-lease-cleanup.json"),
        "Unselected build-output locator")
    require(type(build["output_directory"]) is str and build["output_directory"]==str(EXE.parent),"Exact verified build output root required")
    matches=[r for r in build["outputs"] if type(r) is dict and r.get("path")==relative]
    require(len(matches)==1,"Missing/duplicate selected build output")
    row=matches[0]
    require(set(row)=={"path","bytes","sha256"} and Path(row["path"]).name==row["path"]
        and row["path"] not in (".","..") and ":" not in row["path"] and "\\" not in row["path"] and "/" not in row["path"],
        "Canonical relative build locator required before filesystem access")
    result=dict(row,path=str(EXE.parent/row["path"]));roles().strict_pin(result);return result


def authority():
    value=verified_metadata(EXECUTION_AUTHORITY,EXECUTION_AUTHORITY_SHA)
    require(type(value) is dict and set(value)=={"schema_version","status","mode","execution_authorized","runtime_qualified",
        "executable","verified_build","source","compiled_source_copy","runtime_pin_header","execution_contract","expected_pack_metadata",
        "module_policy_id","module_policy_sha256","software_inputs","payload_descriptors","closure_scope","dynamic_dependencies"},
        "Exact recognition authority schema required")
    require(type(value["schema_version"]) is int and value["schema_version"]==1
        and value["status"]=="verified_build_software_and_descriptor_basis_not_execution_permission" and value["mode"]=="--recognize"
        and value["execution_authorized"] is False and value["runtime_qualified"] is False,"Metadata authority cannot grant execution or runtime qualification")
    static=value["software_inputs"];validate_static_records(static);by_path={r["path"]:r for r in static}
    require(value["payload_descriptors"]==payload_records(),"Exact five descriptor-only payload records required")
    require(value["executable"]==by_path[str(EXE)] and value["executable"]["sha256"]==EXE_SHA
        and value["verified_build"]==by_path[str(VERIFIED_BUILD)] and value["verified_build"]["sha256"]==VERIFIED_BUILD_SHA
        and value["execution_contract"]==by_path[str(CONTRACT)] and value["execution_contract"]["sha256"]==CONTRACT_SHA
        and value["expected_pack_metadata"]==by_path[str(EXPECTED_PACK)] and value["expected_pack_metadata"]["sha256"]==EXPECTED_PACK_SHA,
        "Exact executable/build/contract/pack-METADATA bindings differ")
    require(value["module_policy_id"]==POLICY_ID and value["module_policy_sha256"]==POLICY_SHA
        and value["dynamic_dependencies"]==["current_parent","current_authority","current_binding_checker","current_binding_proof"],
        "Exact policy and acyclic dynamic split required")
    build=verified_metadata(VERIFIED_BUILD,VERIFIED_BUILD_SHA)
    require(build["status"]=="VERIFIED_recognition_enabled_bridge_compiled_NOT_EXECUTED_runtime_unqualified"
        and build["executable"]==value["executable"] and build["source"]==value["source"]
        and build["compiled_source_copy"]==value["compiled_source_copy"] and build["header"]==value["runtime_pin_header"],
        "Verified recognition build identity/status changed")
    require(build["source"]["sha256"]==build["compiled_source_copy"]["sha256"]==SOURCE_SHA
        and build["header"]["sha256"]==HEADER_SHA and build["policy"]["recognition_enabled"] is True
        and build["policy"]["runtime_execution_authorized"] is False
        and build["policy"]["expected_version"]=="0.7.0-dev"
        and build["policy"]["semantic_sha256"]==POLICY_SHA,"Recognition source/header/version/policy differs")
    for name in ("source","compiled_source_copy","header","protocol","receipt","terminal","cleanup"):
        require(build[name]==by_path[build[name]["path"]],"Required verified build leaf absent or altered")
    for name in ("build-report.json","receipt.json","terminal-seal.json","post-lease-cleanup.json"):
        row=build_output_record(build,name);require(row==by_path[row["path"]],"Selected actual-format build output differs")
    require(sdk.NATIVE_EXECUTION_ENABLED is False,"Original SDK general gate changed")
    software=static+[pin(p) for p in dynamic_paths()]
    validate_software_inputs(software,static)
    return dict(value,static_inputs=static,software_inputs=software)


def collect_inputs():
    binding=authority();software=binding["software_inputs"]
    validate_software_inputs(software,binding["static_inputs"])
    # Only screened software leaves are touched. Five payload records are appended
    # as metadata, without resolve/safe/lstat/stat/open or content hashing.
    for row in software:require(software_pin(row["path"])==row,"Current software input differs: "+row["path"])
    result=software+payload_records();validate_role_inputs(result,software);return result


def prepare():
    global _OWNER_DEADLINE
    started=time.monotonic();require(_OWNER_DEADLINE is None,"Preparation clock already active")
    _OWNER_DEADLINE=started+60
    try:
        require(os.name=="nt" and sys.flags.isolated and sys.dont_write_bytecode and Path(sys.executable)==q.DEFAULT
            and metadata.version("asof-target-agents")=="0.3.11","Pinned accepted -I -B metadata-preparation interpreter required")
        require(not PROTOCOL.exists() and not PREPARATION.exists(),"Recognition preparation already consumed")
        proof=verified_metadata(PURE,sha(PURE))
        require(proof["status"]=="passed" and proof["helper_sha256"]==sha(__file__)
            and proof["checker_sha256"]==sha(CHECKER) and proof["actual_children"]==0
            and proof["actual_SDK_constructors"]==0 and proof["payload_path_operations"]==0,
            "Exact current binding pure proof required")
        inputs=collect_inputs()
        output=safe(ROOT/"data/cache"/("r09-recognition-observation-v1-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),output=True)
        require(not output.exists(),"Exclusive future recognition output already exists")
        config=configuration(output,inputs);validate_role(config);check_owner_clock()
        with PROTOCOL.open("xb") as stream:stream.write(canonical(config)+b"\n");stream.flush();os.fsync(stream.fileno())
        check_owner_clock()
        write_new(PREPARATION,dict(schema_version=1,status="prepared_singleton_recognition_metadata_not_execution_authority",
            helper=pin(__file__),authority=pin(EXECUTION_AUTHORITY),protocol=pin(PROTOCOL),static_inputs=len(STATIC_PATHS),
            dynamic_inputs=4,payload_descriptor_inputs=5,inputs=len(inputs),output=str(output),output_absent=not output.exists(),
            actual_children=0,actual_SDK_constructors=0,payload_path_operations=0,compiler_calls=0,
            elapsed_seconds=time.monotonic()-started,preparation_budget_seconds=60,SDK_general_gate=False,execution_authorized=False))
        check_owner_clock();print(json.dumps(dict(status="prepared_singleton_recognition_metadata_not_execution_authority",
            helper_sha256=sha(__file__),protocol_sha256=sha(PROTOCOL),static_inputs=len(STATIC_PATHS),inputs=len(inputs),output=str(output))))
    finally:_OWNER_DEADLINE=None
'''

def main():
    assert not PARENT.exists() and not AUTHORITY.exists()
    contract=load(CONTRACT,'30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861')
    manifest=load(PACK_METADATA,'096e1234e239d04c3b276295e7176f5886f139a4064c3fc5f207745f8938f64d')
    payload=[contract['CPU_descriptor'],*contract['ordered_shard_descriptors'],manifest['pack']]
    PAYLOAD_KEYS.update(key(r['path']) for r in payload)
    build=load(BUILD_PROOF,BUILD_SHA);old=load(OLD_STATIC,OLD_SHA)['static_inputs']
    assert build['status']=='VERIFIED_recognition_enabled_bridge_compiled_NOT_EXECUTED_runtime_unqualified'
    protocol=load(verified(build['protocol']))
    default=ROOT/'data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe'
    site=default.parent.parent/'Lib/site-packages';sdkroot=Path(r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um')
    public={r['local_path'] for r in load(HERE/'HEADER-CLOSURE-FOLLOWUP.json')['headers']}
    generation=HERE.parent/'recovery-step9-generation-contract-20261028'
    fixed={str(default),str(default.parent.parent/'pyvenv.cfg'),str(Path(r'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe')),
        str(generation/'acceptance.json'),str(generation/'WHEEL-ENVIRONMENTS.json'),
        str(ROOT/'data/cache/recovery-step9-generation-wheel-20261028/dist/asof_target_agents-0.3.11-py3-none-any.whl')}
    files=[]
    for row in old:
        path=Path(row['path'])
        if (str(path) in fixed or str(path) in public or path.parent==sdkroot or path.parent==Path(r'C:\Windows\System32')
            or (site in path.parents and ('asof' in path.parts or path.name in {'METADATA','WHEEL','entry_points.txt'}))):files.append(verified(row))
    files.extend([Path(__file__).resolve(),BUILD_PROOF,*(HERE/n for n in PHASE_NAMES)])
    for name in ('executable','source','compiled_source_copy','header','protocol','receipt','terminal','cleanup','root_decision',
        'build_peer','source_peer','child_pure_proof','descriptor','descriptor_proof','policy_contract','shared_vectors','execution_contract','wire'):
        files.append(verified(build[name]))
    prepared=Path(build['header']['path']).parent
    copies=[verified(r) for r in protocol['inputs'] if Path(r['path']).parent==prepared/'headers']
    assert len(copies)==7;files.extend(copies)
    runtime=ROOT/'data/cache/approved-native-mirror-20261028T004531Z/runtime'
    for row in protocol['inputs']:
        if Path(row['path']).parent==runtime and Path(row['path']).name in ('libomp.dll','ggml-base.dll','ggml.dll','llama.dll'):files.append(verified(row))
    report=next(r for r in build['outputs'] if r['path']=='build-report.json')
    assert set(report)=={'path','bytes','sha256'};files.append(verified(dict(report,path=str(Path(build['output_directory'])/report['path']))))
    unique={str(p.absolute()):p.absolute() for p in files};assert len(unique)==len({key(p) for p in unique})
    allowed_dlls={str(runtime/name) for name in ('libomp.dll','ggml-base.dll','ggml.dll','llama.dll')}
    allowed_dlls.update(row['path'] for row in old if Path(row['path']).parent==Path(r'C:\Windows\System32'))
    allowed_exes={str(default),str(Path(r'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe')),build['executable']['path']}
    for name,path in unique.items():
        if path.suffix.casefold()=='.dll':assert name in allowed_dlls
        if path.suffix.casefold()=='.exe':assert name in allowed_exes
    records=[pin(unique[n]) for n in sorted(unique,key=str.casefold)]
    assert len([r for r in records if str(site/'asof')+'\\' in r['path']])==85
    assert len([r for r in records if '.dist-info\\' in r['path']])==3
    assert len([r for r in records if r['path'] in allowed_dlls])==20
    assert len([r for r in records if Path(r['path']).parent==sdkroot])==6
    value=dict(schema_version=1,status='verified_build_software_and_descriptor_basis_not_execution_permission',mode='--recognize',
        execution_authorized=False,runtime_qualified=False,executable=build['executable'],verified_build=pin(BUILD_PROOF),source=build['source'],
        compiled_source_copy=build['compiled_source_copy'],runtime_pin_header=build['header'],execution_contract=pin(CONTRACT),expected_pack_metadata=pin(PACK_METADATA),
        module_policy_id=contract['module_policy_id'],module_policy_sha256=contract['module_policy_sha256'],software_inputs=records,payload_descriptors=payload,
        closure_scope='Exact accepted85+3/interpreters/wheel/public14/SDK6/current compiled build/core4/System16 plus reviewed recognition mechanics and technical evidence. System16 is lease provenance only; reported platform images never become leaves. Payloads are descriptors only.',
        dynamic_dependencies=['current_parent','current_authority','current_binding_checker','current_binding_proof'])
    write(AUTHORITY,value)
    source=BASE.read_text(encoding='utf-8');assert hashlib.sha256(source.encode('utf-8')).hexdigest()==BASE_SHA
    tree=ast.parse(source);replacements={n.name:n for n in ast.parse(BINDING_CODE).body if isinstance(n,ast.FunctionDef)}
    source_lines=source.splitlines(keepends=True)
    for n in sorted((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in replacements),key=lambda n:n.lineno,reverse=True):
        code=ast.get_source_segment(BINDING_CODE,replacements.pop(n.name))+'\n'
        source_lines[n.lineno-1:n.end_lineno]=[code]
    source=''.join(source_lines)
    source=source.replace('Prospective nine-argument recognition parent v6; source/pure only, asset/build-unbound.',
        'Nine-argument recognition parent v7; exact acyclic software/descriptor metadata preparation.')
    source=source.replace('Authority, configuration, collection and preparation reject until a separately versioned binding.\nThe preserved execute body is unreachable through this draft. No dispatch permission is created.',
        'The CLI only prepares metadata. Calling execute requires a separately reviewed exact root once-decision and audited driver. Static authority and preparation grant no asset-read or execution permission.')
    source=source.replace('EXE=None  # No future recognition executable/build or asset verification is bound.',f'EXE=Path({build["executable"]["path"]!r})')
    source=source.replace('EXE_SHA=None',f'EXE_SHA={build["executable"]["sha256"]!r}')
    source=source.replace('PROTOCOL=None',f'PROTOCOL=HERE/{PROTOCOL.name!r}')
    source=source.replace('if __name__=="__main__":\n    raise SystemExit("Source/pure-only unbound recognition parent; no prepare or execute CLI")',
        'if __name__=="__main__":\n    if sys.argv[1:]==["--prepare"]:prepare()\n    else:raise SystemExit("Metadata-preparation CLI only; execution requires separate exact root authority and audited driver")')
    insertion=f'''\nEXECUTION_AUTHORITY=HERE/{AUTHORITY.name!r}\nEXECUTION_AUTHORITY_SHA={sha(AUTHORITY)!r}\nVERIFIED_BUILD=HERE/{BUILD_PROOF.name!r}\nVERIFIED_BUILD_SHA={BUILD_SHA!r}\nSOURCE_SHA={build['source']['sha256']!r}\nHEADER_SHA={build['header']['sha256']!r}\nCHECKER=HERE/{CHECKER.name!r}\nPURE=HERE/{PURE.name!r}\nPREPARATION=ROOT/{PREPARATION.relative_to(ROOT).as_posix()!r}\nSTATIC_PATHS={tuple(r['path'] for r in records)!r}\n'''
    marker='def metadata_path(path):';source=source.replace(marker,insertion+'\n'+marker)
    missing='\n\n'.join(ast.get_source_segment(BINDING_CODE,n) for n in replacements.values())
    source=source.replace('def authority():',missing+'\n\n\ndef authority():')
    ast.parse(source)
    with PARENT.open('x',encoding='utf-8',newline='\n') as out:out.write(source)
    print(json.dumps(dict(status='metadata_authority_and_bound_source_written_no_protocol_or_dispatch',parent_sha256=sha(PARENT),authority_sha256=sha(AUTHORITY),
        static_software=len(records),software_bytes=sum(r['bytes'] for r in records),dynamic_software=4,payload_descriptors=5,payload_path_operations=0,
        actual_children=0,actual_SDK_constructors=0,denied_operations=DENIED,elapsed_seconds=time.monotonic()-START)))

if __name__=='__main__':main()
