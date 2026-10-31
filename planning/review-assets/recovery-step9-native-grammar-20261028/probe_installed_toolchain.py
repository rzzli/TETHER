"""One author-written x64 C++ probe using scoped installed Build Tools env."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'data/cache' / ('r09-installed-toolchain-probe-' + STAMP)
OUT.mkdir(exist_ok=False)
REPORT = HERE / 'TOOLCHAIN-LOCAL-PROBE.json'
assert not REPORT.exists()
VSWHERE = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe')
CMD = Path(os.environ['SystemRoot']) / 'System32/cmd.exe'
BASE = dict(os.environ)
for key in ('CL', '_CL_', 'LINK', '_LINK_'):
    BASE.pop(key, None)
BASE.update(TEMP=str(OUT), TMP=str(OUT), VSCMD_SKIP_SENDTELEMETRY='1')
INITIAL_PROCESS_ENV = dict(os.environ)
commands, denied = [], []
current_command = None


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def under(path, root):
    try:
        return os.path.commonpath([normalized(path), normalized(root)]) == normalized(root)
    except ValueError:
        return False


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def proof(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size)


def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.__new__', 'os.system', 'ctypes.dlopen'):
        denied.append(event)
        raise RuntimeError('No network, shell-system dispatch or DLL probing')
    if event == 'subprocess.Popen':
        expected = subprocess.list2cmdline(current_command) if current_command else None
        if current_command is None or args[1] != expected or args[0] not in (None, current_command[0]) or normalized(args[2]) != normalized(OUT):
            denied.append(dict(event=event, executable=str(args[0])))
            raise RuntimeError('Unapproved probe child')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(os.fsdecode(args[0]))
        if path.startswith('e:') or '\\data\\benchmark\\' in path or '\\models\\' in path:
            denied.append(dict(event=event, path=path))
            raise RuntimeError('No model, external data or evaluation payload access')
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (isinstance(mode, str) and any(c in mode for c in 'wax+'))
        if writing and not (under(path, OUT) or path == normalized(REPORT)):
            denied.append(dict(event=event, path=path))
            raise RuntimeError('Probe writes limited to fresh cache and one report')


sys.addaudithook(audit)


def run(label, argv, env, timeout=60, expected=(0,)):
    global current_command
    current_command = list(map(str, argv))
    started = time.monotonic()
    try:
        result = subprocess.run(current_command, cwd=OUT, env=env, capture_output=True,
                                timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    finally:
        current_command = None
    assert len(result.stdout) + len(result.stderr) < 2 * 1024 * 1024
    (OUT / (label + '.stdout')).write_bytes(result.stdout)
    (OUT / (label + '.stderr')).write_bytes(result.stderr)
    row = dict(label=label, argv=list(map(str, argv)), cwd=str(OUT),
               exit_code=result.returncode, elapsed_seconds=time.monotonic() - started,
               stdout=proof(OUT / (label + '.stdout')), stderr=proof(OUT / (label + '.stderr')))
    commands.append(row)
    assert result.returncode in expected, (label, result.returncode)
    return result


report = dict(schema_version=1, status='started', recorded_at_utc=datetime.now(timezone.utc).isoformat(),
              output=str(OUT), report_scope='Compiler/SDK/STL/linker feasibility only; not llama ABI or grammar conformance',
              model_calls=0, servers=0, llama_dlls_loaded=0, installs=0, downloads=0,
              system_environment_changed=False, provider_spend_usd=0,
              guard_scope='Parent Python audit and reviewed fixed commands; not OS-wide attestation')
started = time.monotonic()
try:
    found = run('vswhere', [VSWHERE, '-all', '-products', '*', '-requires',
                'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-format', 'json', '-utf8'], BASE)
    instances = json.loads(found.stdout.decode('utf-8-sig'))
    assert len(instances) == 1 and instances[0]['isComplete'] and instances[0]['isLaunchable']
    instance = instances[0]
    installation = Path(instance['installationPath'])
    devcmd = installation / 'Common7/Tools/VsDevCmd.bat'
    assert devcmd.is_file()
    keys = ['PATH', 'INCLUDE', 'LIB', 'LIBPATH', 'VCINSTALLDIR', 'VCToolsInstallDir',
            'VCToolsVersion', 'VCToolsRedistDir', 'WindowsSdkDir', 'WindowsSDKVersion',
            'UniversalCRTSdkDir', 'UCRTVersion', 'VSINSTALLDIR', 'DevEnvDir', 'VSCMD_VER',
            'VSCMD_ARG_TGT_ARCH', 'VSCMD_ARG_HOST_ARCH']
    emit = OUT / 'emit_filtered_env.py'
    emit.write_text('import json, os, sys\nfrom pathlib import Path\nkeys=' + repr(keys) +
                    '\nPath(sys.argv[1]).write_text(json.dumps({k:os.environ[k] for k in keys if k in os.environ},indent=2),encoding="utf-8")\n', encoding='utf-8')
    env_file = OUT / 'filtered-build-environment.json'
    batch = OUT / 'initialize-x64.cmd'
    for path in (devcmd, Path(sys.executable), emit, env_file, OUT):
        assert not any(c in str(path) for c in ('"', '%', '\n', '\r', '&', '|', '<', '>'))
    batch.write_text('@echo off\ncall "' + str(devcmd) + '" -no_logo -arch=x64 -host_arch=x64 > "' +
                     str(OUT / 'environment-init.log') + '" 2>&1\nif errorlevel 1 exit /b %errorlevel%\n"' +
                     sys.executable + '" "' + str(emit) + '" "' + str(env_file) + '"\nexit /b %errorlevel%\n', encoding='ascii')
    run('environment-init', [CMD, '/d', '/s', '/c', str(batch)], BASE)
    filtered = json.loads(env_file.read_bytes())
    assert set(filtered) <= set(keys) and filtered['VSCMD_ARG_TGT_ARCH'] == 'x64'
    build_env = dict(BASE, **filtered)
    tools_root = Path(filtered['VCToolsInstallDir'])
    tool_bin = tools_root / 'bin/Hostx64/x64'
    compiler, linker = tool_bin / 'cl.exe', tool_bin / 'link.exe'
    assert compiler.is_file() and linker.is_file()
    assert normalized(shutil.which('cl.exe', path=filtered['PATH'])) == normalized(compiler)
    sdk = Path(filtered['WindowsSdkDir'])
    sdk_version = filtered['WindowsSDKVersion'].rstrip('\\/')
    inputs = [VSWHERE, devcmd, compiler, linker,
              tools_root / 'include/string', tools_root / 'include/vector', tools_root / 'include/yvals_core.h',
              tools_root / 'lib/x64/msvcprt.lib', tools_root / 'lib/x64/vcruntime.lib',
              sdk / f'Include/{sdk_version}/um/Windows.h',
              sdk / f'Include/{sdk_version}/ucrt/stdio.h',
              sdk / f'Lib/{sdk_version}/um/x64/kernel32.lib', sdk / f'Lib/{sdk_version}/ucrt/x64/ucrt.lib']
    for name in ('c1.dll', 'c1xx.dll', 'c2.dll', 'mspdbcore.dll', 'lib.exe'):
        if (tool_bin / name).is_file():
            inputs.append(tool_bin / name)
    input_proofs = [proof(path) for path in inputs]
    source = OUT / 'probe.cpp'
    source.write_text(r'''#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <iostream>
#include <string>
#include <vector>
#include <yvals_core.h>
#if !defined(_M_X64)
#error Expected an x64 compiler target
#endif
static_assert(sizeof(void*) == 8, "Expected x64 pointers");
int main() {
    SYSTEM_INFO info{};
    GetNativeSystemInfo(&info);
    LARGE_INTEGER frequency{};
    wchar_t module_path[MAX_PATH]{};
    bool api_ok = GetCurrentProcessId() > 0 && QueryPerformanceFrequency(&frequency) &&
        frequency.QuadPart > 0 && info.wProcessorArchitecture == PROCESSOR_ARCHITECTURE_AMD64 &&
        GetModuleFileNameW(nullptr, module_path, MAX_PATH) > 0;
    std::string text("AsOf");
    std::vector<int> values{1, 2, 3};
    bool stl_ok = text.size() == 4 && values.size() == 3 && values[0] + values[1] + values[2] == 6;
    bool llama_loaded = GetModuleHandleW(L"llama.dll") || GetModuleHandleW(L"llama-common.dll") ||
        GetModuleHandleW(L"llama-server-impl.dll");
    std::cout << std::boolalpha << "{\n"
        << "\"MSC_VER\":" << _MSC_VER << ",\n"
        << "\"MSC_FULL_VER\":" << _MSC_FULL_VER << ",\n"
        << "\"MSVC_STL_UPDATE\":" << _MSVC_STL_UPDATE << ",\n"
        << "\"MSVC_STL_VERSION\":" << _MSVC_STL_VERSION << ",\n"
        << "\"ITERATOR_DEBUG_LEVEL\":" << _ITERATOR_DEBUG_LEVEL << ",\n"
        << "\"sizeof_std_string\":" << sizeof(std::string) << ",\n"
        << "\"sizeof_std_vector_int\":" << sizeof(std::vector<int>) << ",\n"
        << "\"sizeof_void_ptr\":" << sizeof(void*) << ",\n"
        << "\"windows_sdk_api\":" << api_ok << ",\n"
        << "\"stl_operations\":" << stl_ok << ",\n"
        << "\"llama_modules_loaded\":" << llama_loaded << "\n}\n";
    return api_ok && stl_ok && !llama_loaded ? 0 : 1;
}
''', encoding='ascii')
    exe, obj = OUT / 'probe.exe', OUT / 'probe.obj'
    argv = [compiler, '/nologo', '/Bv', '/std:c++17', '/MD', '/O2', '/DNDEBUG', '/EHsc',
            '/W4', '/WX', '/utf-8', source, '/Fo' + str(obj), '/Fe' + str(exe),
            '/Fd' + str(OUT / 'probe.pdb'), '/link', '/MACHINE:X64', '/INCREMENTAL:NO']
    run('compile-link', argv, build_env, timeout=90)
    run('linker-version-help', [linker, '/?'], build_env)
    result = run('author-written-probe', [exe], build_env)
    measured = json.loads(result.stdout)
    assert measured['sizeof_void_ptr'] == 8 and measured['ITERATOR_DEBUG_LEVEL'] == 0
    assert measured['windows_sdk_api'] and measured['stl_operations'] and not measured['llama_modules_loaded']
    assert all(digest(p['path']) == p['sha256'] for p in input_proofs)
    assert os.environ == INITIAL_PROCESS_ENV and not denied
    report.update(status='installed_x64_toolchain_probe_passed', elapsed_seconds=time.monotonic() - started,
                  instance=instance, compiler=str(compiler), linker=str(linker), devcmd=str(devcmd),
                  environment_initialization=proof(batch), filtered_environment=proof(env_file),
                  scoped_environment_keys=keys, input_proofs=input_proofs, source=proof(source),
                  executable=proof(exe), object=proof(obj), measurements=measured,
                  reboot_required_by_installer=instance['isRebootRequired'],
                  restart_needed_for_this_probe=False, commands=commands, guards=denied,
                  helper=proof(__file__), global_environment_unchanged=True,
                  llama_abi_compatibility='unverified', native_grammar_conformance='unverified')
except BaseException as error:
    report.update(status='failed', error_class=type(error).__name__, message=str(error),
                  elapsed_seconds=time.monotonic() - started, commands=commands, guards=denied)
    with REPORT.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    raise
with REPORT.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({k: report[k] for k in ('status', 'output', 'compiler', 'linker', 'measurements', 'restart_needed_for_this_probe')}))
