"""Build author-owned actual-DLL typed bridge; never execute resulting program."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'data/cache' / ('r09-typed-converter-bridge-build-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
REPORT = HERE / 'TYPED-CONVERTER-BRIDGE-BUILD-v3.json'
assert not REPORT.exists()
probe_path = HERE / 'TOOLCHAIN-LOCAL-PROBE-v2.json'
probe = json.loads(probe_path.read_bytes())
assert probe['status'] == 'installed_x64_toolchain_probe_passed'
closure_path = HERE / 'CONVERTER-HEADER-CLOSURE.json'
closure = json.loads(closure_path.read_bytes())
assert closure['status'] == 'five_converter_references_and_consumer_header_closure_verified'
mirror_path = HERE.parent / 'recovery-step9-native-integration-20261027/NATIVE-MODEL-MIRROR.json'
mirror = json.loads(mirror_path.read_bytes())
native = Path(mirror['target']) / 'runtime'
common = native / 'llama-common.dll'
common_pin = next(p for p in mirror['items'] if p['relative_path'] == 'runtime/llama-common.dll')
source_path = HERE / 'typed_converter_bridge.cpp'
contract = HERE / 'CONVERTER-BRIDGE-BUILD-CONTRACT.md'
commands, denied = [], []
current_command = None
INITIAL_ENV = dict(os.environ)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path, root):
    try:
        return os.path.commonpath([normalized(path), normalized(root)]) == normalized(root)
    except ValueError:
        return False


def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.__new__', 'os.system', 'ctypes.dlopen'):
        denied.append(event)
        raise RuntimeError('No network, system shell or DLL execution')
    if event == 'subprocess.Popen':
        expected = subprocess.list2cmdline(current_command) if current_command else None
        if current_command is None or args[1] != expected or args[0] not in (None, current_command[0]) or normalized(args[2]) != normalized(OUT):
            denied.append(dict(event=event, executable=str(args[0])))
            raise RuntimeError('Only fixed lib/compiler build commands allowed')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(args[0])
        if path.startswith('e:') or '\\data\\benchmark\\' in path or path.endswith('.gguf'):
            denied.append(dict(event=event, path=path))
            raise RuntimeError('No external/model/evaluation payloads')
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (isinstance(mode, str) and any(c in mode for c in 'wax+'))
        if writing and not (under(path, OUT) or path == normalized(REPORT)):
            denied.append(dict(event=event, path=path))
            raise RuntimeError('Writes limited to fresh build output and one report')


sys.addaudithook(audit)


class PE:
    def __init__(self, raw):
        self.raw = raw
        assert raw[:2] == b'MZ'
        pe = struct.unpack_from('<I', raw, 0x3c)[0]
        assert raw[pe:pe+4] == b'PE\0\0'
        self.machine, count = struct.unpack_from('<HH', raw, pe+4)
        opt = pe+24
        self.optional_size = struct.unpack_from('<H', raw, pe+20)[0]
        assert struct.unpack_from('<H', raw, opt)[0] == 0x20b and self.machine == 0x8664
        self.directories = opt+112
        self.sections = []
        for i in range(count):
            vsize, va, size, pointer = struct.unpack_from('<IIII', raw, opt+self.optional_size+40*i+8)
            assert pointer+size <= len(raw)
            self.sections.append((va, vsize, size, pointer))

    def offset(self, rva):
        for va, vsize, size, pointer in self.sections:
            if va <= rva < va+max(vsize, size):
                assert rva-va < size
                return pointer+rva-va
        raise ValueError('RVA is not file backed')

    def string(self, rva):
        start = self.offset(rva)
        end = self.raw.find(b'\0', start, min(len(self.raw), start+65536))
        assert end >= start
        return self.raw[start:end].decode('ascii')

    def directory(self, index):
        return struct.unpack_from('<II', self.raw, self.directories+8*index)

    def exports(self):
        rva, size = self.directory(0)
        assert rva and size
        directory = self.offset(rva)
        count, table_rva = struct.unpack_from('<II', self.raw, directory+24)
        # AddressOfNames follows AddressOfFunctions, not NumberOfNames.
        table_rva = struct.unpack_from('<I', self.raw, directory+32)[0]
        table = self.offset(table_rva)
        assert count < 100000 and table+4*count <= len(self.raw)
        return [self.string(struct.unpack_from('<I', self.raw, table+4*i)[0]) for i in range(count)]

    def thunks(self, rva):
        table = self.offset(rva)
        names = []
        for i in range(100000):
            value = struct.unpack_from('<Q', self.raw, table+8*i)[0]
            if value == 0:
                return names
            assert not value & (1 << 63), 'Ordinal imports not approved for this bridge'
            names.append(self.string(value+2))
        raise ValueError('Thunk count exceeds bound')

    def imports(self):
        rva, size = self.directory(1)
        found = {}
        if not rva:
            return found
        table = self.offset(rva)
        for i in range(4096):
            row = struct.unpack_from('<IIIII', self.raw, table+20*i)
            if not any(row):
                return found
            original, timestamp, chain, name, first = row
            found[self.string(name)] = self.thunks(original or first)
        raise ValueError('Import descriptor count exceeds bound')

    def delays(self):
        rva, size = self.directory(13)
        found = {}
        if not rva:
            return found
        table = self.offset(rva)
        for i in range(4096):
            row = struct.unpack_from('<IIIIIIII', self.raw, table+32*i)
            if not any(row):
                return found
            attrs, name, hmod, iat, int_table, bound, unload, timestamp = row
            assert attrs == 1, 'Expected RVA-based delay descriptors'
            found[self.string(name)] = self.thunks(int_table)
        raise ValueError('Delay descriptor count exceeds bound')


def run(label, argv, env):
    global current_command
    current_command = list(map(str, argv))
    started = time.monotonic()
    try:
        result = subprocess.run(current_command, cwd=OUT, env=env, capture_output=True, timeout=90,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    finally:
        current_command = None
    assert len(result.stdout)+len(result.stderr) < 2*1024*1024
    (OUT/(label+'.stdout')).write_bytes(result.stdout)
    (OUT/(label+'.stderr')).write_bytes(result.stderr)
    commands.append(dict(label=label, argv=list(map(str, argv)), cwd=str(OUT), exit_code=result.returncode,
                         elapsed_seconds=time.monotonic()-started,
                         stdout=pin(OUT/(label+'.stdout')), stderr=pin(OUT/(label+'.stderr'))))
    assert result.returncode == 0, (label, result.returncode)


report = dict(schema_version=1, status='started', output=str(OUT),
              role='build_only_no_native_execution_authorized', installs=0, downloads=0,
              resulting_bridge_executions=0, native_libraries_loaded=0, model_calls=0, servers=0,
              vocabulary_loads=0, gguf_reads=0, network_calls=0, provider_spend_usd=0,
              compilation_is_not_abi_qualification=True, native_grammar_conformance='unverified')
started = time.monotonic()
try:
    assert all(sha(r['path']) == r['sha256'] for r in probe['input_proofs'])
    env_proof = probe['filtered_environment']
    assert sha(env_proof['path']) == env_proof['sha256']
    filtered = json.loads(Path(env_proof['path']).read_bytes())
    assert set(filtered) <= set(probe['scoped_environment_keys']) and filtered['VSCMD_ARG_TGT_ARCH'] == 'x64'
    env = dict(os.environ)
    for key in ('CL', '_CL_', 'LINK', '_LINK_'):
        env.pop(key, None)
    env.update(filtered, TEMP=str(OUT), TMP=str(OUT), VSCMD_SKIP_SENDTELEMETRY='1')
    compiler = Path(probe['compiler'])
    library_tool = compiler.parent/'lib.exe'
    delay_library = Path(filtered['VCToolsInstallDir'])/'lib/x64/delayimp.lib'
    sdk = Path(filtered['WindowsSdkDir'])
    sdk_version = filtered['WindowsSDKVersion'].rstrip('\\/')
    bcrypt_library = sdk/f'Lib/{sdk_version}/um/x64/bcrypt.lib'
    tool_inputs = [pin(p) for p in (compiler, library_tool, Path(probe['linker']), delay_library, bcrypt_library)]
    headers = []
    header_dir = OUT/'headers'
    header_dir.mkdir()
    assert len(closure['converter_consumer_headers']) == 3
    for row in closure['converter_consumer_headers']:
        source = ROOT/row['relative_path']
        assert sha(source) == row['sha256']
        destination = header_dir/Path(row['path']).name
        with destination.open('xb') as stream:
            stream.write(source.read_bytes())
        assert sha(destination) == row['sha256']
        headers.append(dict(source=pin(source), copied=pin(destination)))
    assert common.stat().st_size == common_pin['bytes'] and sha(common) == common_pin['sha256']
    actual_exports = PE(common.read_bytes()).exports()
    patterns = {
        'parse': lambda n: n.startswith('?parse@common_json@@'),
        'dump': lambda n: n.startswith('?dump@common_json@@'),
        'destructor': lambda n: n.startswith('??1common_json@@'),
        'convert': lambda n: n.startswith('?json_schema_to_grammar@@') and 'AEBVcommon_json@@_N' in n,
    }
    selected = {}
    for name, match in patterns.items():
        matches = [n for n in actual_exports if match(n)]
        assert len(matches) == 1, (name, matches)
        selected[name] = matches[0]
    assert len(set(selected.values())) == 4
    (OUT/'actual-typed-exports.json').write_text(json.dumps(selected, indent=2), encoding='utf-8')
    definition = OUT/'llama-common-typed.def'
    assert all(not any(c.isspace() or c in '\"=,;#' for c in n) for n in selected.values())
    definition.write_text('LIBRARY llama-common.dll\nEXPORTS\n'+''.join('    '+n+'\n' for n in selected.values()), encoding='ascii')
    runtime_pins = [p for p in mirror['items'] if p['relative_path'].startswith('runtime/') and p['relative_path'].lower().endswith('.dll')]
    manifest = OUT/'approved_runtime.hpp'
    manifest.write_text('#pragma once\n#include <cstddef>\nstruct ModulePin { const wchar_t* name; const char* sha256; std::size_t bytes; };\n'
                        'inline constexpr ModulePin APPROVED_RUNTIME_DLLS[] = {\n'+
                        ''.join('    {L"'+Path(p['relative_path']).name+'", "'+p['sha256']+'", '+str(p['bytes'])+'},\n' for p in runtime_pins)+'};\n', encoding='ascii')
    source = OUT/'typed_converter_bridge.cpp'
    with source.open('xb') as stream:
        stream.write(source_path.read_bytes())
    assert sha(source) == sha(source_path)
    import_library = OUT/'llama-common-typed.lib'
    run('create-narrow-importlib', [library_tool, '/nologo', '/machine:x64', '/def:'+str(definition), '/out:'+str(import_library)], env)
    import_bytes = import_library.read_bytes()
    assert b'llama-common.dll\0' in import_bytes
    for name in selected.values():
        assert (name+'\0').encode('ascii') in import_bytes
        assert ('"'+name+'"').encode('ascii') not in import_bytes
    exe, obj = OUT/'typed_converter_bridge.exe', OUT/'typed_converter_bridge.obj'
    run('compile-link-only', [compiler, '/nologo', '/Bv', '/std:c++17', '/MD', '/O2', '/DNDEBUG', '/D_ITERATOR_DEBUG_LEVEL=0',
        '/EHsc', '/W4', '/WX', '/utf-8', '/I'+str(header_dir), '/I'+str(OUT), source, '/Fo'+str(obj), '/Fe'+str(exe),
        '/Fd'+str(OUT/'bridge.pdb'), '/link', '/MACHINE:X64', '/INCREMENTAL:NO', '/DELAYLOAD:llama-common.dll',
        str(import_library), str(delay_library), str(bcrypt_library)], env)
    binary = PE(exe.read_bytes())
    ordinary = binary.imports()
    delayed = binary.delays()
    assert not any('llama' in n.lower() or 'ggml' in n.lower() for n in ordinary)
    assert set(delayed) == {'llama-common.dll'}
    assert set(delayed['llama-common.dll']) == set(selected.values())
    disallowed_functions = ('llama_model_', 'llama_init_', 'llama_decode', 'llama_encode', 'llama_sampler_', 'llama_tokenize', 'socket', 'connect', 'CreateProcess', 'ShellExecute', 'WinHttp', 'InternetOpen')
    assert not any(any(bad in n for bad in disallowed_functions) for names in ordinary.values() for n in names)
    assert sha(common) == common_pin['sha256']
    assert all(sha(r['path']) == r['sha256'] for r in probe['input_proofs']+tool_inputs)
    assert all(sha(r['source']['path']) == r['source']['sha256'] and sha(r['copied']['path']) == r['copied']['sha256'] for r in headers)
    assert os.environ == INITIAL_ENV and not denied
    report.update(status='typed_actual_converter_bridge_built_not_executed', elapsed_seconds=time.monotonic()-started,
                  contract=pin(contract), helper=pin(__file__), authored_source=pin(source_path), compiled_source=pin(source),
                  closure_report=pin(closure_path), source_commit='848bbda9041decd87904f7eb5a2990863ecce03b',
                  headers=headers, toolchain_probe=pin(probe_path), filtered_environment=env_proof,
                  tools=tool_inputs, existing_tool_inputs=probe['input_proofs'],
                  approved_common_dll=pin(common), model_mirror_report=pin(mirror_path),
                  approved_runtime_manifest=pin(manifest), native_runtime_dll_count=len(runtime_pins),
                  import_definition=pin(definition), imported_methods=selected, import_library=pin(import_library),
                  executable=pin(exe), object=pin(obj), static_ordinary_imports=ordinary, static_delay_imports=delayed,
                  commands=commands, guards=denied, global_environment_unchanged=True,
                  diagnostics_policy='Any native stderr warnings fail future external qualification',
                  source_limits=dict(max_input_bytes=2*1024*1024, max_output_bytes=4*1024*1024, max_native_dll_bytes=128*1024*1024),
                  force_gbnf=False, execution_authorization='Not granted by this report')
except BaseException as error:
    report.update(status='failed', error_class=type(error).__name__, message=str(error),
                  elapsed_seconds=time.monotonic()-started, commands=commands, guards=denied)
    with REPORT.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    raise
with REPORT.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({k:report[k] for k in ('status','output','resulting_bridge_executions','native_libraries_loaded','executable')}))
