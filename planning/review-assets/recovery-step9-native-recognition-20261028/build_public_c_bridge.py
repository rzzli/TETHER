"""Prepare/build only the pinned ABI-disabled public-C bridge; never execute it."""

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from threading import Event, Thread
import time
from zipfile import ZipFile

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode
from asof.study.stable_read import deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GRAMMAR = HERE.parent / "recovery-step9-native-grammar-20261028"
GENERATION = HERE.parent / "recovery-step9-generation-contract-20261028"
SOURCE = HERE / "typed_public_c_recognizer_v3.cpp"
SOURCE_SHA = "0d6d7c8bf7495d35811fda56df805dba4e0cf7aa5470776df0903cd5215ad9f4"
DESIGN = HERE / "BRIDGE-DRAFT-DESIGN-v3.md"
DESIGN_SHA = "d94671e7d885d0c8929d68848631c27dc810730d5fed19c2520def2e1b024ceb"
PROTOCOL = HERE / "BUILD-PROTOCOL.json"
PREPARATION = HERE / "BUILD-PREPARATION.json"
QUALIFICATION = HERE / "SOURCE-QUALIFICATION.json"
QUALIFICATION_SHA = "ace2041e0da3830945317b39e3970afaf440e44693d48bff8a746cb984f34f0c"
ACCEPTANCE = GENERATION / "acceptance.json"
ACCEPTANCE_SHA = "491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
FILTERED_SHA = "b6777f390be6e92041f557c6217531725ef3096249bfc80960f9145a88159cff"
RUNTIME = ROOT / "data/cache/approved-native-mirror-20261028T004531Z/runtime"
TOOLROOT = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231")
SDKROOT = Path(r"C:\Program Files (x86)\Windows Kits\10")
SDKVER = "10.0.26100.0"
SYSTEM = Path(os.environ["SystemRoot"]) / "System32"
INITIAL_ENV = dict(os.environ)
PYBASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
LIMITS = dict(total_seconds=60, compile_seconds=45, link_seconds=10,
              finalization_reserve_seconds=5, stdout_bytes=262144, stderr_bytes=262144,
              maximum_children=2, execute_result=False)


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def safe(path, within=ROOT):
    path = Path(path).absolute()
    need(path.is_relative_to(Path(within).absolute())
         and path.resolve().is_relative_to(Path(within).resolve()), "Path escapes approved root")
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        need(not item.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400),
             "Reparse path rejected: " + str(item))
    return path


def safe_input(path):
    path = Path(path).absolute()
    if path.is_relative_to(ROOT):
        return safe(path)
    if path == PYBASE:
        return safe(path,PYBASE.parent)
    for parent in (TOOLROOT.parents[3],SDKROOT,SYSTEM,
                   Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer")):
        if path.is_relative_to(parent):
            return safe(path,parent)
    raise RuntimeError("Unapproved build input root")


class PE:
    """Bounded static PE64 reader; never loads the inspected module."""
    def __init__(self, raw):
        self.raw = raw
        need(len(raw) >= 256 and raw[:2] == b"MZ", "Not PE")
        pe = self.unpack("<I", 60)[0]
        need(raw[pe:pe+4] == b"PE\0\0", "PE signature")
        machine, count = self.unpack("<HH", pe+4)
        optional_size = self.unpack("<H", pe+20)[0]
        opt = pe+24
        need(machine == 0x8664 and self.unpack("<H", opt)[0] == 0x20b
             and 0 < count <= 128 and optional_size >= 240, "Expected AMD64 PE32+")
        self.directories = opt+112
        self.sections = []
        for i in range(count):
            size, address, stored, offset = self.unpack("<IIII", opt+optional_size+40*i+8)
            need(offset+stored <= len(raw), "PE section range")
            self.sections.append((address, size, stored, offset))

    def unpack(self, kind, offset):
        need(0 <= offset <= len(self.raw)-struct.calcsize(kind), "Truncated PE field")
        return struct.unpack_from(kind, self.raw, offset)

    def offset(self, rva):
        for address, size, stored, offset in self.sections:
            if address <= rva < address+max(size, stored):
                need(rva-address < stored, "PE RVA not file-backed")
                return offset+rva-address
        raise RuntimeError("Unknown PE RVA")

    def string(self, rva, skip=0):
        at = self.offset(rva)+skip
        end = self.raw.find(b"\0", at, min(len(self.raw), at+65536))
        need(end >= at, "Unterminated PE string")
        return self.raw[at:end].decode("ascii")

    def imports(self, delay=False):
        index, width = (13, 32) if delay else (1, 20)
        rva, size = self.unpack("<II", self.directories+8*index)
        result = {}
        if not rva:
            return result
        at = self.offset(rva)
        for i in range(4096):
            row = self.unpack("<"+"I"*(width//4), at+width*i)
            if not any(row):
                return result
            if delay:
                need(row[0] == 1, "Unsupported delay address mode")
                name, thunks = row[1], row[4]
            else:
                name, thunks = row[3], row[0] or row[4]
            dll = self.string(name)
            need(dll.casefold() not in {n.casefold() for n in result}, "Duplicate PE import descriptor")
            names, table = [], self.offset(thunks)
            for j in range(100000):
                item = self.unpack("<Q", table+8*j)[0]
                if not item:
                    break
                names.append("#"+str(item & 65535) if item & (1 << 63) else self.string(item, 2))
            else:
                raise RuntimeError("PE thunk cap")
            result[dll] = names
        raise RuntimeError("PE import descriptor cap")


def accepted_inputs():
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode,
         "Accepted installed Python with -I -B required")
    need(metadata.version("asof-target-agents") == "0.3.11" and util.find_spec("pyarrow") is None,
         "Accepted dependency-free package required")
    need(sha(PYBASE) == "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1",
         "Pinned canonical Python base changed")
    need(sha(ACCEPTANCE) == ACCEPTANCE_SHA and sha(QUALIFICATION) == QUALIFICATION_SHA
         and sha(SOURCE) == SOURCE_SHA and sha(DESIGN) == DESIGN_SHA, "Build anchors changed")
    probe_path = GRAMMAR / "TOOLCHAIN-LOCAL-PROBE-v2.json"
    probe = json.loads(probe_path.read_bytes())
    need(probe["status"] == "installed_x64_toolchain_probe_passed"
         and Path(probe["compiler"]) == TOOLROOT / "bin/Hostx64/x64/cl.exe"
         and Path(probe["linker"]) == TOOLROOT / "bin/Hostx64/x64/link.exe", "Toolchain changed")
    filtered = Path(probe["filtered_environment"]["path"])
    need(sha(filtered) == FILTERED_SHA, "Filtered environment changed")
    environment = json.loads(filtered.read_bytes())
    need(environment["VCToolsVersion"] == "14.51.36231"
         and environment["WindowsSDKVersion"].rstrip("\\/") == SDKVER
         and environment["VSCMD_ARG_TGT_ARCH"] == environment["VSCMD_ARG_HOST_ARCH"] == "x64",
         "Wrong toolchain architecture/version")
    inputs = [pin(p) for p in (ACCEPTANCE, QUALIFICATION, SOURCE, DESIGN, probe_path, filtered,
        HERE / "BRIDGE-PEER-REVIEW.json", HERE / "BRIDGE-PEER-REVIEW.md",
        HERE / "BRIDGE-V3-PEER-REVIEW.json", HERE / "BRIDGE-V3-PEER-REVIEW.md",
        HERE / "BRIDGE-OPENMP-PEER-REVIEW.json", HERE / "BRIDGE-OPENMP-PEER-REVIEW.md",
        HERE / "BUILD-STATIC-NEGATIVE.json", HERE / "typed_public_c_recognizer.cpp",
        HERE / "typed_public_c_recognizer_v2.cpp", HERE / "BRIDGE-DRAFT-DESIGN.md",
        HERE / "BRIDGE-DRAFT-DESIGN-v2.md",
        HERE / "HEADER-CLOSURE-FOLLOWUP.json", HERE / "MODEL-ARCHITECTURE-EVIDENCE.json",
        HERE / "EXPLICIT-CPU-REVIEW.json", HERE / "BACKEND-RESULT-VERIFICATION.json", __file__,
        sys.executable, Path(sys.prefix) / "pyvenv.cfg", PYBASE)]
    wheel_report = GENERATION / "WHEEL-ENVIRONMENTS.json"
    wheel = json.loads(wheel_report.read_bytes())
    need(Path(sys.executable).resolve() == Path(wheel["default_python"]).resolve(), "Wrong installed interpreter")
    need(sha(wheel["wheel"]) == "b0d7573be994e3f44e3d942a1944cddb2e43e1306a64cfd6480dd05e3415a276",
         "Accepted wheel differs")
    inputs.extend([pin(wheel_report),pin(wheel["wheel"])])
    with ZipFile(wheel["wheel"]) as archive:
        members = [name for name in archive.namelist() if name.startswith("asof/") and not name.endswith("/")]
        need(len(members) == 85, "Accepted installed closure differs")
        for name in members:
            path = Path(sys.prefix) / "Lib/site-packages" / name
            need(sha(path) == hashlib.sha256(archive.read(name)).hexdigest(), "Accepted installed file changed")
            inputs.append(pin(path))
    need(sha(HERE / "BRIDGE-PEER-REVIEW.json") == "62d8fde49f4fe623519a1ccf081dde233bb5289567e85500f775a7f3502dafd8",
         "Original static checkpoint changed")
    need(sha(HERE / "BRIDGE-V3-PEER-REVIEW.json") == "c3cdb7b9f00011231566b33e568e9488633f108b917fdc2a86d855b906e68494",
         "Scoped pack-revision text review changed")
    need(sha(HERE / "BRIDGE-OPENMP-PEER-REVIEW.json") == "8ab0cbba0c9d85030ebf1de70a1838ea03887c37ede5ebce947e634c53106446",
         "Scoped OpenMP correction review changed")
    for item in probe["input_proofs"]:
        need(pin(item["path"]) == item, "Existing compiler/SDK proof changed")
        inputs.append(item)
    # Direct SDK/STL leaves and selected link libraries; not a transitive toolchain closure.
    stl = ["algorithm","array","cmath","cstddef","cstdint","cwctype","filesystem","iomanip",
           "iostream","initializer_list","limits","memory","sstream","stdexcept","string",
           "type_traits","utility","vector"]
    extras = [TOOLROOT / "include" / name for name in stl]
    extras += [SDKROOT / f"Include/{SDKVER}/um/TlHelp32.h",
               SDKROOT / f"Include/{SDKVER}/shared/bcrypt.h"]
    extras += [SDKROOT / f"Lib/{SDKVER}/um/x64/{name}" for name in ("bcrypt.lib","kernel32.lib")]
    extras += [TOOLROOT / "lib/x64" / name for name in ("msvcprt.lib","msvcrt.lib","vcruntime.lib")]
    inputs.extend(pin(p) for p in extras)
    closure = json.loads((HERE / "HEADER-CLOSURE-FOLLOWUP.json").read_bytes())
    need(closure["header_count"] == 7 and not closure["unresolved_quoted_includes"], "Public closure incomplete")
    for item in closure["headers"]:
        need(pin(item["local_path"]) == dict(path=item["local_path"],sha256=item["sha256"],bytes=item["bytes"]),
             "Public header changed")
        inputs.append(pin(item["local_path"]))
    return probe, environment, closure, inputs


def build_environment(filtered, output):
    allowed = {k:v for k,v in filtered.items() if k != "PATH"}
    allowed.update(SystemRoot=str(SYSTEM.parent), WINDIR=str(SYSTEM.parent), SystemDrive=SYSTEM.drive,
        PATH=";".join(map(str,(TOOLROOT / "bin/Hostx64/x64",SDKROOT / f"bin/{SDKVER}/x64",SYSTEM))),
        TEMP=str(output), TMP=str(output), VSCMD_SKIP_SENDTELEMETRY="1")
    need(not {"CL","_CL_","LINK","_LINK_","PYTHONPATH"} & set(allowed), "Injected compiler flags")
    return allowed


def audit(state, output=None):
    def guard(event, args):
        if event in ("socket.__new__","socket.connect","socket.getaddrinfo","os.system"):
            state["denied"].append(event)
            raise RuntimeError("No network/shell in build helper")
        if event == "ctypes.dlopen" and str(args[0]).casefold() != "kernel32":
            state["denied"].append(event)
            raise RuntimeError("Only accepted Windows file-lease API allowed")
        if event == "subprocess.Popen":
            active = state.get("active")
            need(active is not None and state["dispatches"] < 2
                 and args[0] in (None,active[0]) and args[1] == subprocess.list2cmdline(active)
                 and Path(args[2]) == output and args[3] == state["environment"], "Unapproved build child")
            state["dispatches"] += 1
        if event == "open" and args and isinstance(args[0],(str,bytes,os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            need(path.drive.casefold() != "e:" and path.suffix.casefold() != ".gguf"
                 and "\\data\\benchmark\\" not in str(path).casefold(), "No model/evaluation reads")
            mode = args[1] if len(args)>1 else None
            flags = args[2] if len(args)>2 and isinstance(args[2],int) else 0
            writing = bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)) or (
                isinstance(mode,str) and any(c in mode for c in "wax+"))
            need(not writing or path in state["write_files"] or any(path.is_relative_to(p) for p in state["write_roots"]),
                 "Parent write outside reserved build artifacts")
    sys.addaudithook(guard)


def static_runtime():
    mirror_path = HERE.parent / "recovery-step9-native-duration-20261028/NATIVE-MODEL-MIRROR.json"
    need(sha(mirror_path) == "5ec132da880d016ecc36a0e0207386d1c802964bbaead7fe392bbdf617839b8d", "Mirror metadata changed")
    mirror = json.loads(mirror_path.read_bytes())
    need(Path(mirror["target"]) / "runtime" == RUNTIME, "Wrong approved mirror")
    records, inputs = [], [pin(mirror_path)]
    for name in ("ggml-base.dll","ggml.dll","llama.dll","ggml-cpu-x64.dll","libomp.dll"):
        item = next(p for p in mirror["items"] if p["relative_path"] == "runtime/"+name)
        path = safe(RUNTIME / name)
        proof = pin(path)
        need(proof["sha256"] == item["sha256"] and proof["bytes"] == item["bytes"], "Runtime bytes differ")
        binary = PE(path.read_bytes())
        records.append(dict(name=name,pin=proof,ordinary=binary.imports(),delay=binary.imports(True)))
        inputs.append(proof)
    requires_omp = any("libomp.dll" in {n.casefold() for n in r[k]} for r in records if r["name"] != "libomp.dll" for k in ("ordinary","delay"))
    need(requires_omp, "Expected retained base OpenMP dependency missing")
    # Deliberately finite prospective names: fixed imports/CRT hosts/startup and SHA provider.
    names = ("ntdll.dll","kernel32.dll","kernelbase.dll","ucrtbase.dll","msvcp140.dll",
             "vcruntime140.dll","vcruntime140_1.dll","advapi32.dll","psapi.dll","sechost.dll",
             "rpcrt4.dll","msvcrt.dll","bcrypt.dll","bcryptprimitives.dll","cryptbase.dll","cryptsp.dll")
    system = []
    for name in names:
        path = safe(SYSTEM / name, SYSTEM)
        proof = pin(path)
        binary = PE(path.read_bytes())
        system.append(dict(name=name,pin=proof,ordinary=list(binary.imports()),delay=list(binary.imports(True)),
            basis="Prospective fixed import/CRT host/Windows startup or BCrypt provider candidate; not observed loaded inventory"))
        inputs.append(proof)
    ordinary_missing = {n.casefold() for r in system for n in r["ordinary"]
        if not n.casefold().startswith(("api-ms-","ext-ms-")) and n.casefold() not in set(names)}
    need(not ordinary_missing,"Fixed prospective System32 list misses an ordinary real-DLL dependency")
    old_run = ROOT / "data/cache/r09-finite-converter-execution-20261028T043655Z"
    old_receipt = json.loads((old_run / "receipt.json").read_bytes())
    observed = old_run / "stages/00-roundtrip/stdout.bin"
    need(sha(observed) == old_receipt["outputs"]["stages/00-roundtrip/stdout.bin"]["sha256"], "Old native observation changed")
    old = json.loads(observed.read_bytes())
    need(old["native_modules_before"] == old["native_modules_after"], "Prior native inventory differs")
    inputs.extend([pin(old_run / "receipt.json"),pin(observed)])
    return mirror, records, system, requires_omp, inputs, dict(
        native_modules=old["native_modules_before"],complete_System32_inventory_available=False,
        limitation="Old converter records native package modules only; four CRT preparation hashes are not loaded-system attestation")


def header_text(runtime, system, requires_omp, mirror):
    def literal(value):
        return json.dumps(str(value),ensure_ascii=True)
    architecture = json.loads((HERE / "MODEL-ARCHITECTURE-EVIDENCE.json").read_bytes())
    need(sha(HERE / "MODEL-ARCHITECTURE-EVIDENCE.json") == "596d0e6f8353a82d273f93156efd3fe06685f14ca9d08d3da05f70b8ebec5bf7", "Model metadata changed")
    shards = []
    for recorded in architecture["recorded_shards"]:
        name = Path(recorded["path"]).name
        item = next(p for p in mirror["items"] if p["relative_path"] == name)
        need(item["sha256"] == recorded["sha256"] and item["bytes"] == recorded["bytes"], "Recorded shard identity differs")
        shards.append(dict(path=str(RUNTIME.parent/name),sha256=recorded["sha256"],bytes=recorded["bytes"]))
    need(len(shards) == 3, "Exactly three recorded model identities required")
    lines = ["#pragma once","// ABI-only data header. No model or pack reads are authorized.",
        "inline constexpr ModulePin APPROVED_RUNTIME_DLLS[] = {"]
    for r in runtime:
        if r["name"] != "libomp.dll" or requires_omp:
            lines.append("    {L"+literal(r["name"])+", "+literal(r["pin"]["sha256"])+", "+str(r["pin"]["bytes"])+"ull},")
    lines += ["};","inline constexpr wchar_t R09_RUNTIME_DIRECTORY[] = L"+literal(RUNTIME)+";",
        'inline constexpr wchar_t R09_CPU_BASENAME[] = L"ggml-cpu-x64.dll";',
        "inline constexpr bool R09_LIBOMP_REQUIRED = "+str(requires_omp).lower()+";",
        'inline constexpr char R09_CPU_REGISTRY_NAME[] = "CPU";',
        'inline constexpr char R09_CPU_DEVICE_NAME[] = "CPU";',
        'inline constexpr char R09_EXPECTED_LLAMA_VERSION[] = "";',
        "// Prospective finite System32 prediction; no complete historical loaded inventory.",
        "inline constexpr const wchar_t* R09_SYSTEM_DLL_NAMES[] = {"]
    lines += ["    L"+literal(r["name"])+"," for r in system]
    lines += ["};",'inline constexpr FilePin R09_PACK = {L"", "'+"0"*64+'", 0ull};',
        "inline constexpr FilePin R09_SHARDS[3] = {"]
    lines += ["    {L"+literal(r["path"])+", "+literal(r["sha256"])+", "+str(r["bytes"])+"ull}," for r in shards]
    lines += ["};","inline constexpr bool R09_RECOGNITION_ENABLED = false;"]
    return "\n".join(lines)+"\n", shards


def commands(prepared, output, probe):
    source = prepared / "typed_public_c_recognizer.cpp"
    obj, exe = output / "bridge.obj", output / "typed_public_c_recognizer_abi.exe"
    return [dict(stage="compile",seconds=45,argv=[probe["compiler"],"/nologo","/Bv","/std:c++17",
        "/MD","/O2","/DNDEBUG","/D_ITERATOR_DEBUG_LEVEL=0","/EHsc","/Zp8","/Gd","/W4","/WX","/utf-8","/c",
        '/DR09_PIN_HEADER="recognizer_runtime_pins.hpp"',"/I"+str(prepared/"headers"),"/I"+str(prepared),
        str(source),"/Fo"+str(obj),"/Fd"+str(output/"compiler.pdb")]),
        dict(stage="link",seconds=10,argv=[probe["linker"],"/NOLOGO","/MACHINE:X64","/SUBSYSTEM:CONSOLE",
        "/INCREMENTAL:NO","/MANIFEST:NO","/DYNAMICBASE","/NXCOMPAT","/HIGHENTROPYVA",
        "/OUT:"+str(exe),str(obj),str(SDKROOT/f"Lib/{SDKVER}/um/x64/bcrypt.lib"),
        str(SDKROOT/f"Lib/{SDKVER}/um/x64/kernel32.lib")])]


def prepare():
    need(not PROTOCOL.exists() and not PREPARATION.exists(), "Preparation already exists")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prepared = safe(ROOT / "data/cache" / ("r09-public-c-bridge-preparation-"+stamp))
    output = safe(ROOT / "data/cache" / ("r09-public-c-bridge-build-"+stamp))
    need(not prepared.exists() and not output.exists(), "Exclusive directory already exists")
    state = dict(active=None,environment=None,dispatches=0,denied=[],write_roots=[prepared],
        write_files={PROTOCOL,PREPARATION,HERE/"BUILD-STATIC-PE.json"})
    audit(state)
    probe, filtered, closure, inputs = accepted_inputs()
    mirror, runtime, system, requires_omp, proofs, old = static_runtime()
    inputs += proofs
    prepared.mkdir()
    (prepared / "headers").mkdir()
    copied = []
    for item in closure["headers"]:
        source = Path(item["local_path"])
        destination = prepared / "headers" / source.name
        with destination.open("xb") as stream:
            stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
        need(sha(destination) == item["sha256"], "Copied public header changed")
        copied.append(dict(source=pin(source),copied=pin(destination)))
        inputs.append(pin(destination))
    source_copy = prepared / "typed_public_c_recognizer.cpp"
    with source_copy.open("xb") as stream:
        stream.write(SOURCE.read_bytes());stream.flush();os.fsync(stream.fileno())
    need(sha(source_copy) == SOURCE_SHA, "Copied bridge changed")
    generated, shards = header_text(runtime,system,requires_omp,mirror)
    pin_header = prepared / "recognizer_runtime_pins.hpp"
    with pin_header.open("x",encoding="ascii",newline="\n") as stream:
        stream.write(generated);stream.flush();os.fsync(stream.fileno())
    inputs += [pin(source_copy),pin(pin_header)]
    static_report = dict(schema_version=1,status="static_PE_dependency_facts_no_ABI_execution",
        runtime=runtime,system_candidates=system,old_converter_observation=old,
        original_bridge_static_negative=dict(source_sha256="3f7e13ec7695bd5257e3e58d627ae71c1a2cdcaea7dbec8aad869424a0f5188b",
            issue="ggml-base imports libomp; old ABI-mode allowlist excluded it",actual_failed_ABI=False),
        requires_libomp=requires_omp,no_target_calls=True,no_model_reads=True,
        System32_prediction_scope="Finite fixed ordinary-import/startup/CRT/BCrypt candidates; no recursive or dynamic dependency closure",
        unresolved_System32_delay_names=sorted({n.casefold() for r in system for n in r["delay"]
            if not n.casefold().startswith(("api-ms-","ext-ms-")) and n.casefold() not in {x["name"] for x in system}}))
    write_new(HERE/"BUILD-STATIC-PE.json",static_report)
    inputs.append(pin(HERE/"BUILD-STATIC-PE.json"))
    inputs = list({os.path.normcase(r["path"]):r for r in inputs}.values())
    for r in inputs:
        safe_input(r["path"])
    environment = build_environment(filtered,output)
    deadline = time.monotonic()+60
    with stable_files([Path(r["path"]) for r in inputs],deadline=deadline):
        for r in inputs:
            need(encode(hash_file(r["path"],deadline)) == {k:r[k] for k in ("bytes","sha256")}, "Preparation pin differs")
        value = dict(schema_version=1,kind="abi_only_public_c_bridge_build_v1",helper=pin(__file__),
            source=pin(SOURCE),design=pin(DESIGN),source_qualification=pin(QUALIFICATION),
            accepted_software_sha256=ACCEPTANCE_SHA,prepared=str(prepared),output=str(output),
            source_reviews=dict(original=pin(HERE/"BRIDGE-PEER-REVIEW.json"),
                OpenMP_delta=pin(HERE/"BRIDGE-OPENMP-PEER-REVIEW.json"),
                pack_v2_delta=pin(HERE/"BRIDGE-V3-PEER-REVIEW.json")),
            review_scope="Composed scoped AI text reviews; no whole-bridge independent human or runtime claim",
            commands=commands(prepared,output,probe),environment=environment,limits=LIMITS,
            inputs=inputs,headers=copied,pin_header=pin(pin_header),runtime_pins=runtime,
            prospective_System32_allowlist=[r["name"] for r in system],
            System32_inventory_is_observed=False,recorded_model_metadata_only=shards,
            recognition_enabled=False,expected_version="",pack_descriptor_unused_in_ABI=True,
            execute_result=False,build_authorized_by_preparation=False,
            process_scope="Only launched compiler/linker handles; no OS process-tree, resource-job or system-wide write attestation",
            source_compile_scope="Own bridge and seven public headers only; fetched implementations never compile",
            toolchain_scope="Pinned tools/direct SDK-STL leaves/libs; not a complete transitive compiler/SDK closure",
            activity=dict(children=0,compiles=0,links=0,target_calls=0,model_reads=0,network_requests=0))
        write_new(PROTOCOL,value)
    need(state["dispatches"] == 0 and not state["denied"] and dict(os.environ)==INITIAL_ENV,
         "Preparation performed forbidden action/environment mutation")
    write_new(PREPARATION,dict(schema_version=1,status="prepared_not_built_or_executed",protocol=pin(PROTOCOL),
        helper=pin(__file__),source=pin(SOURCE),design=pin(DESIGN),pin_header=pin(pin_header),
        inputs=len(inputs),headers=copied,output_absent=not output.exists(),limits=LIMITS,
        requires_libomp=requires_omp,recognition_enabled=False,expected_version="",activity=value["activity"],
        global_environment_unchanged=True,source_reviews=value["source_reviews"],
        next_gate="Exact root and peer review plus separate build authorization; native runtime gates remain separate"))
    print(json.dumps(dict(status="prepared_not_built_or_executed",protocol_sha256=sha(PROTOCOL),
        helper_sha256=sha(__file__),inputs=len(inputs),prepared=str(prepared))))


def run_tool(step, output, environment, journal, state, deadline, records):
    started = time.monotonic()
    end = min(started+step["seconds"],deadline-LIMITS["finalization_reserve_seconds"])
    deadline_check(end)
    record = dict(stage=step["stage"],argv=step["argv"],pid=None,spawned=False,reaped=False,
        returncode=None,timed_out=False,streams={},cleanup_errors=[],
        effective_seconds=end-started,process_scope="Launched compiler/linker handle only; descendants not independently attested")
    records.append(record)  # Preserve failed/interrupted attempts in the terminal accounting too.
    journal.append("build_tool_reserved",**record)
    process, threads, stop = None, [], Event()
    sinks = ExitStack()
    def drain(name, pipe, stream):
        item = record["streams"][name]
        try:
            while True:
                block = pipe.read(65536)
                if not block:
                    break
                item["observed_bytes_at_least"] += len(block)
                remaining = LIMITS[name+"_bytes"]-item["retained_bytes"]
                if remaining:
                    stream.write(block[:remaining]);item["retained_bytes"] += min(remaining,len(block))
                if len(block)>remaining:
                    item["truncated"]=True;stop.set();break
        except BaseException as error:
            item["error_class"]=type(error).__name__;stop.set()
        finally:
            try:
                stream.flush();os.fsync(stream.fileno())
            except BaseException as error:
                item["error_class"]=type(error).__name__;stop.set()
    try:
        streams={name:sinks.enter_context((output/(step["stage"]+"."+name+".bin")).open("xb")) for name in ("stdout","stderr")}
        state["active"]=step["argv"]
        process=subprocess.Popen(step["argv"],cwd=output,env=environment,shell=False,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        record.update(pid=process.pid,spawned=True)
        process.stdin.close()
        journal.append("build_tool_started",stage=step["stage"],pid=process.pid)
        for name,pipe in (("stdout",process.stdout),("stderr",process.stderr)):
            record["streams"][name]=dict(retained_bytes=0,observed_bytes_at_least=0,truncated=False,error_class=None)
            thread=Thread(target=drain,args=(name,pipe,streams[name]),daemon=True)
            thread.start();threads.append(thread)
        while process.poll() is None:
            if stop.is_set() or time.monotonic()>=end:
                record["timed_out"]=time.monotonic()>=end
                process.kill();break
            time.sleep(0.02)
    except BaseException as error:
        record.update(error_class=type(error).__name__,error=str(error)[:1024])
        if isinstance(error,KeyboardInterrupt):
            record["interrupted"]=True
    finally:
        state["active"]=None
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=max(0.1,min(2,deadline-time.monotonic())))
                record.update(reaped=True,returncode=process.poll())
            except BaseException as error:
                record["cleanup_errors"].append(type(error).__name__)
            for thread in threads:
                thread.join(timeout=max(0.1,min(1,deadline-time.monotonic())))
            if any(thread.is_alive() for thread in threads):
                record["cleanup_errors"].append("CaptureThreadUnresolved")
            else:
                for pipe in (process.stdout,process.stderr):
                    if pipe is not None:
                        pipe.close()
        try:
            sinks.close()
        except BaseException as error:
            record["cleanup_errors"].append(type(error).__name__)
        record["full_process_elapsed_seconds"]=time.monotonic()-started
        for name in ("stdout","stderr"):
            path=output/(step["stage"]+"."+name+".bin")
            if path.exists():
                record[name]=pin(path)
        write_new(output/(step["stage"]+"-attempt.json"),record)
        journal.append("build_tool_terminal",**record)
    need(record["spawned"] and record["reaped"] and record["returncode"]==0
         and "error_class" not in record and "interrupted" not in record
         and not record["timed_out"] and not record["cleanup_errors"]
         and record["full_process_elapsed_seconds"]<=record["effective_seconds"]
         and all(not row["truncated"] and row["error_class"] is None for row in record["streams"].values()),
         "Compiler/linker attempt failed; never retry automatically")
    deadline_check(deadline-LIMITS["finalization_reserve_seconds"])
    return record


def build(expected):
    need(len(expected)==64 and sha(PROTOCOL)==expected,"Explicit reviewed protocol hash required")
    protocol=json.loads(PROTOCOL.read_bytes())
    need(protocol["kind"]=="abi_only_public_c_bridge_build_v1" and protocol["helper"]["sha256"]==sha(__file__)
         and protocol["limits"]==LIMITS and protocol["recognition_enabled"] is False
         and protocol["expected_version"]=="" and protocol["execute_result"] is False,
         "Build protocol scope differs")
    output=safe(protocol["output"],ROOT/"data/cache")
    prepared=safe(protocol["prepared"],ROOT/"data/cache")
    need(not output.exists(),"Build already reserved; no automatic restart")
    started=time.monotonic();deadline=started+60
    journal=RunJournal(output,kind="build")
    state=dict(active=None,environment=protocol["environment"],dispatches=0,denied=[],write_roots=[output],write_files=set())
    audit(state,output)
    leases=ExitStack();failure=None
    result=dict(schema_version=1,status="failed",protocol_sha256=expected,commands=[],
        executable_executions=0,target_dll_loads=0,model_reads=0,network_requests=0,
        recognition_enabled=False,source_qualification_sha256=QUALIFICATION_SHA,
        compiler_process_scope=protocol["process_scope"])
    def fail(error,phase):
        nonlocal failure
        failure=dict(error_class=type(error).__name__,message=str(error)[:2048],phase=phase)
        result.update(status="failed",failure=failure)
        try:
            if not (output/"failure.json").exists():
                write_new(output/"failure.json",dict(authoritative=True,**failure,automatic_retry=False))
        except BaseException as marker_error:
            result["failure_marker_error_class"]=type(marker_error).__name__
    try:
        probe,filtered,_,_=accepted_inputs()
        need(protocol["commands"]==commands(prepared,output,probe)
             and protocol["environment"]==build_environment(filtered,output),"Command/environment differs")
        write_new(output/"effective-protocol.json",protocol)
        inputs=protocol["inputs"]+[pin(PROTOCOL)]
        leases.enter_context(stable_files([Path(r["path"]) for r in inputs],deadline=deadline))
        for r in inputs:
            need(encode(hash_file(r["path"],deadline))=={k:r[k] for k in ("bytes","sha256")},"Build input changed")
        for step in protocol["commands"]:
            run_tool(step,output,protocol["environment"],journal,state,deadline,result["commands"])
        exe=safe(output/"typed_public_c_recognizer_abi.exe",output)
        obj=safe(output/"bridge.obj",output)
        need(0<exe.stat().st_size<=16*1024*1024,"Executable size cap")
        need(0<obj.stat().st_size<=128*1024*1024,"Object size cap")
        leases.enter_context(stable_files([exe,obj],deadline=deadline))
        binary=PE(exe.read_bytes());ordinary=binary.imports();delayed=binary.imports(True)
        need(not delayed and not any(any(tag in name.casefold() for tag in ("llama","ggml","ws2_32","winhttp","wininet","urlmon")) for name in ordinary),
             "Upstream/network static import forbidden")
        forbidden=("CreateProcess","ShellExecute","WinHttp","InternetOpen","WSAStartup")
        need(not any(any(tag in name for tag in forbidden) for names in ordinary.values() for name in names),
             "Process/network static export forbidden")
        for r in inputs:
            need(encode(hash_file(r["path"],deadline))=={k:r[k] for k in ("bytes","sha256")},"Final build input changed")
        need(not state["denied"] and state["dispatches"]==2 and dict(os.environ)==INITIAL_ENV,
             "Build dispatch accounting/environment differs")
        result.update(status="ABI_disabled_public_C_bridge_built_not_executed",executable=pin(exe),
            object=pin(obj),ordinary_imports=ordinary,delay_imports=delayed,
            generated_executable_and_object_read_leased_during_static_checks=True,
            global_environment_unchanged=True)
    except BaseException as error:
        fail(error,"build_or_static_qualification")
    finally:
        try:
            result.update(guards={k:v for k,v in state.items() if k in ("dispatches","denied")},
                elapsed_seconds_before_finalization=time.monotonic()-started)
            try:
                journal.append("public_C_build_terminal",status=result["status"],dispatches=state["dispatches"])
            finally:
                journal.close()
            write_new(output/"build-report.json",result)
            deadline_check(deadline)
            outputs={}
            for path in sorted(output.rglob("*")):
                deadline_check(deadline)
                if path.is_file():
                    need(path.stat().st_size<=128*1024*1024,"Generated artifact cap")
                    outputs[path.relative_to(output).as_posix()]=encode(hash_file(path,deadline))
            chain=read_chain(output/"journal.jsonl")
            write_new(output/"receipt.json",dict(schema_version=1,status=result["status"],outputs=outputs,
                journal_tip_sha256=chain[-1]["sha256"],protocol_sha256=expected,
                failure_veto="failure.json overrides any built status or receipt"))
            deadline_check(deadline)
        except BaseException as error:
            fail(error,"finalization")
        finally:
            try:
                leases.close();deadline_check(deadline)
            except BaseException as error:
                fail(error,"lease_cleanup_or_global_deadline")
    print(json.dumps(dict(status=result["status"],output=str(output),
        authoritative_failure=(output/"failure.json").exists(),elapsed_seconds=time.monotonic()-started)))
    return 0 if failure is None and not (output/"failure.json").exists() and result["status"]=="ABI_disabled_public_C_bridge_built_not_executed" else 1


if __name__=="__main__":
    if sys.argv[1:]==["--prepare"]:
        prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--build":
        raise SystemExit(build(sys.argv[2]))
    else:
        raise SystemExit("Only --prepare now; build requires separately approved --build PROTOCOL_SHA256")
