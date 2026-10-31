"""Create one acyclic static manifest from selected retained leaves only; never execute code/assets."""
import hashlib
import json
from pathlib import Path
import stat
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=HERE/"run_self_module_census_v2.py"
AUTHORITY=HERE/"SELF-MODULE-CENSUS-STATIC-AUTHORITY-v2.json"
PROTOCOL=HERE/"SELF-MODULE-CENSUS-EXECUTION-PROTOCOL-v1.json"
CHECKER=HERE/"check_self_module_census_binding_v2.py"
PURE=HERE/"SELF-MODULE-CENSUS-BINDING-PURE-PROOF-v2.json"
PREVIOUS=HERE.parent/"recovery-step9-generation-contract-20261028"
BUILD_PROOF=HERE/"SELF-MODULE-CENSUS-BUILD-RESULT-VERIFICATION-v1.json"
BUILD_SHA="51c255ec00aaf050a833682f4a41abd27f6b82fe6ffadef18a8e1a92d6756306"
DEFAULT=ROOT/"data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe"
BASE=Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
CORE=("libomp.dll","ggml-base.dll","ggml.dll","llama.dll")
SYSTEM=("ntdll.dll","kernel32.dll","kernelbase.dll","ucrtbase.dll","msvcp140.dll","vcruntime140.dll",
        "vcruntime140_1.dll","advapi32.dll","psapi.dll","sechost.dll","rpcrt4.dll","msvcrt.dll",
        "bcrypt.dll","bcryptprimitives.dll","cryptbase.dll","cryptsp.dll")
SDK_HEADERS=("processthreadsapi.h","winbase.h","winnt.h","fileapi.h","namedpipeapi.h","jobapi2.h")
PUBLIC_HEADERS=("llama.h","ggml.h","ggml-cpu.h","ggml-backend.h","ggml-opt.h","gguf.h","ggml-alloc.h")
PHASE_NAMES=(
    "qualify_detached_native_worker_v1.py","detached_parent_launch_draft_v1.py","abi_parent_launch_draft_v3.py",
    "DETACHED-POLICY-CONTRACT-v1.json","DETACHED-POLICY-DESIGN-v1.md",
    "DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json","DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json",
    "detached_abi_terminal_observation_v3.py","DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v3.json",
    "module_census_status_seal_v1.py","SELF-MODULE-CENSUS-SEALER-PURE-PROOF-v1.json",
    "module_census_validation_v1.py","SELF-MODULE-CENSUS-VALIDATION-PURE-PROOF-v1.json",
    "SELF-MODULE-CENSUS-PARSER-INDEPENDENT-PROOF-v1.json","SELF-MODULE-CENSUS-CONTRACT-v1.json",
    "SELF-MODULE-CENSUS-DESIGN-v1.md","SELF-MODULE-CENSUS-IMPLEMENTATION-ROOT-DECISION-v1.json",
    "SELF-MODULE-CENSUS-DESIGN-PEER-REVIEW-v1.json","SELF-MODULE-CENSUS-BINDING-FINDINGS-v1.json",
    "SELF-MODULE-CENSUS-BUILD-PROTOCOL-v1.json","TYPED-ABI-BUILD-PROTOCOL-v5.json",
    "HEADER-CLOSURE-FOLLOWUP.json","run_self_module_census_v1.py",
    "SELF-MODULE-CENSUS-PARENT-MECHANICS-PEER-v1.json","SELF-MODULE-CENSUS-PARENT-PURE-PROOF-v1.json",
    "SELF-MODULE-CENSUS-ARTIFACT-PURE-PROOF-v1.json","census_fixture_v1.py",
    "check_module_census_sealer_v1.py","check_module_census_validation_v1.py",
    "DETACHED-ABI-V3-RESULT-VERIFICATION.json",
)


def sha(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def safe_leaf(path):
    path=Path(path).absolute()
    assert path.drive.casefold()!="e:" and path.suffix.casefold() not in {".gguf",".pyd",".lib",".obj"}
    assert path.name.casefold() not in {"apphelp.dll","ggml-cpu-x64.dll","ggml-cpu.dll"}
    assert path not in {PARENT,AUTHORITY,PROTOCOL,CHECKER,PURE}
    assert "\\data\\benchmark\\" not in str(path).casefold()
    for part in (path,*path.parents):
        info=part.lstat()
        assert not info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    assert path.is_file() and path.stat().st_size<=128*1024**2
    return path


def pin(path):
    path=safe_leaf(path)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path))


def verify(record):
    assert set(record)=={"path","bytes","sha256"}
    assert pin(record["path"])==record


def main():
    assert not AUTHORITY.exists(),"Static authority already exists; preserve it"
    assert sha(BUILD_PROOF)==BUILD_SHA
    build=json.loads(BUILD_PROOF.read_bytes())
    assert build["status"]=="VERIFIED_module_census_bridge_compiled_recognition_disabled_NOT_EXECUTED"
    assert build["executable"]["sha256"]=="559e4e9a654c9487679c551eebf73d6a279416d0990f491d0918d99cdb6f6183"
    files=[Path(__file__).resolve(),BUILD_PROOF,*(HERE/name for name in PHASE_NAMES),DEFAULT,BASE,DEFAULT.parent.parent/"pyvenv.cfg",
           PREVIOUS/"acceptance.json",PREVIOUS/"WHEEL-ENVIRONMENTS.json"]
    for key in ("executable","source","compiled_source_copy","header","protocol","receipt","terminal",
                "root_decision","child_pure_proof","child_regression_proof","source_peer","wire"):
        verify(build[key]);files.append(Path(build[key]["path"]))
    build_root=Path(build["output_directory"])
    for name in ("build-report.json","post-lease-cleanup.json"):
        row=next(r for r in build["outputs"] if r["path"]==name)
        record=dict(row,path=str(build_root/name));verify(record);files.append(Path(record["path"]))
    prepared=Path(build["header"]["path"]).parent
    files.extend(prepared/"headers"/name for name in PUBLIC_HEADERS)
    closure=json.loads((HERE/"HEADER-CLOSURE-FOLLOWUP.json").read_bytes())
    assert closure["header_count"]==7 and not closure["unresolved_quoted_includes"]
    assert {Path(row["local_path"]).name for row in closure["headers"]}==set(PUBLIC_HEADERS)
    files.extend(Path(row["local_path"]) for row in closure["headers"])
    qualifier=json.loads((HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json").read_bytes())
    assert sha(HERE/"DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json")=="7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961"
    qualify_protocol=HERE/"DETACHED-NATIVE-QUALIFICATION-PROTOCOL-v1.json"
    assert sha(qualify_protocol)==qualifier["protocol"]["sha256"]
    qualified=json.loads(qualify_protocol.read_bytes())
    sdk_root=Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um")
    selected=[r for r in qualified["inputs"] if Path(r["path"]).parent==sdk_root and Path(r["path"]).name in SDK_HEADERS]
    assert len(selected)==6
    for row in selected:verify(row);files.append(Path(row["path"]))
    metadata=json.loads((HERE/"TYPED-ABI-BUILD-PROTOCOL-v5.json").read_bytes())
    assert sha(HERE/"TYPED-ABI-BUILD-PROTOCOL-v5.json")=="371b1791ba413173ecfab132ea6f9a22994a0d601981367553a3a94cf8d85222"
    allowed_dlls={str(RUNTIME/name) for name in CORE}|{str(Path(r"C:\Windows\System32")/name) for name in SYSTEM}
    dll_pins=[r for r in metadata["inputs"] if r["path"] in allowed_dlls]
    assert len(dll_pins)==20
    for row in dll_pins:verify(row);files.append(Path(row["path"]))
    acceptance=json.loads((PREVIOUS/"acceptance.json").read_bytes())
    assert sha(PREVIOUS/"acceptance.json")=="491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
    wheel_file=PREVIOUS/"WHEEL-ENVIRONMENTS.json"
    assert {k:pin(wheel_file)[k] for k in ("bytes","sha256")}==acceptance["evidence_files"][wheel_file.relative_to(ROOT).as_posix()]
    wheel=json.loads(wheel_file.read_bytes());wheel_path=Path(wheel["wheel"])
    assert sha(wheel_path)==wheel["wheel_sha256"]=="b0d7573be994e3f44e3d942a1944cddb2e43e1306a64cfd6480dd05e3415a276"
    assert Path(wheel["default_python"])==DEFAULT
    files.append(wheel_path)
    with ZipFile(wheel_path) as archive:
        members=[name for name in archive.namelist() if name.startswith("asof/") and not name.endswith("/")]
        assert len(members)==len(set(members))==85
        for name in members:
            assert all(part not in (".","..") for part in name.split("/"))
            installed=DEFAULT.parent.parent/"Lib/site-packages"/name
            assert sha(installed)==hashlib.sha256(archive.read(name)).hexdigest();files.append(installed)
        # These are the known distribution leaves used for accepted metadata/version provenance.
        for suffix in ("METADATA","WHEEL","entry_points.txt"):
            matches=[name for name in archive.namelist() if ".dist-info/" in name and name.endswith("/"+suffix)]
            assert len(matches)==1
            installed=DEFAULT.parent.parent/"Lib/site-packages"/matches[0]
            assert sha(installed)==hashlib.sha256(archive.read(matches[0])).hexdigest();files.append(installed)
    unique={str(Path(path).absolute()):Path(path).absolute() for path in files}
    assert len(unique)==len({s.casefold() for s in unique})
    assert not(set(unique)&{str(PARENT),str(AUTHORITY),str(PROTOCOL),str(CHECKER),str(PURE)})
    allowed_exes={str(DEFAULT),str(BASE),build["executable"]["path"]}
    for path in unique.values():
        if path.suffix.casefold()==".dll":assert str(path) in allowed_dlls
        if path.suffix.casefold()==".exe":assert str(path) in allowed_exes
    records=[pin(unique[name]) for name in sorted(unique,key=str.casefold)]
    value=dict(schema_version=1,status="verified_build_static_basis_not_execution_permission",mode="--module-census",
        executable=build["executable"],verified_build=pin(BUILD_PROOF),ABI_eligibility_established=False,execution_authorized=False,
        static_inputs=records,
        closure_scope="Exact selected build/source/public-header/SDK-declaration/accepted85+distribution/interpreter/wheel and core4/System32-16 leaves; not complete CPython, Windows dependency or initializer attestation",
        forbidden_dynamic_dependencies=["current parent bytes","this manifest's own bytes","current parent-dependent pure/review/binding reports","execution protocol","future output tree"])
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    with AUTHORITY.open("xb") as stream:stream.write(raw);stream.flush()
    authority_sha=hashlib.sha256(raw).hexdigest()
    parent=PARENT.read_text(encoding="utf-8")
    assert parent.count('EXECUTION_AUTHORITY_SHA="PENDING_STATIC_AUTHORITY"')==1
    parent=parent.replace('EXECUTION_AUTHORITY_SHA="PENDING_STATIC_AUTHORITY"','EXECUTION_AUTHORITY_SHA="'+authority_sha+'"')
    line='STATIC_PATHS=()  # Replaced before freeze by one explicit reviewed finite path tuple.'
    assert parent.count(line)==1
    parent=parent.replace(line,"STATIC_PATHS=(\n"+"".join("    "+repr(row["path"])+",\n" for row in records)+")")
    with PARENT.open("w",encoding="utf-8",newline="\n") as stream:stream.write(parent)
    print(json.dumps(dict(status="static_manifest_created_no_constructor_or_protocol",static_inputs=len(records),
        authority_sha256=authority_sha,parent_sha256=sha(PARENT),SDK_header_count=6,public_header_count=14,
        accepted_runtime_members=85,distribution_metadata_leaves=3,core_DLLs=4,system_DLLs=16)))


if __name__=="__main__":main()
