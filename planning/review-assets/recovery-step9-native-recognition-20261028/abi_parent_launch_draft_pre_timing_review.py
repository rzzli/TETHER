"""Prospective one-shot ABI parent. Hard-disabled: no native command-line route.

Public Windows SDK layouts only. Import/layout/argument/fake-API checks are
permitted; any real Windows API construction or target execution is held.
No subprocess, private _winapi/Nt API, target import, model or network adapter.
"""
from contextlib import ExitStack
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess  # list2cmdline only; Popen is never used.
import sys
import time

NATIVE_EXECUTION_ENABLED = False
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BUILD = ROOT / "data/cache/r09-public-c-bridge-build-20261028T175036Z"
PREPARED = ROOT / "data/cache/r09-public-c-bridge-preparation-20261028T175036Z"
EXE = BUILD / "typed_public_c_recognizer_abi.exe"
RUNTIME = ROOT / "data/cache/approved-native-mirror-20261028T004531Z/runtime"
EXE_SHA = "9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696"
BUILD_RECEIPT_SHA = "ebae856c74554b200b8d486cc5ce958fa530dc75499035bf82a9133114ae7c72"
BUILD_PROTOCOL_SHA = "5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e"
LIMITS = dict(child_seconds=30, parent_seconds=60, finalization_reserve_seconds=5,
              commit_bytes=256 * 1024**2, active_processes=1, maximum_job_pids=16,
              stream_bytes=65536, result_jsonl_bytes=4 * 1024**2,
              row_bytes=65536, attempt_bytes=4096, maximum_children=1)

DWORD, WORD, BOOL = C.c_uint32, C.c_uint16, C.c_int32
HANDLE, PVOID, SIZE_T = C.c_void_p, C.c_void_p, C.c_size_t
WCHAR, LPWSTR = C.c_wchar, C.c_wchar_p
QWORD, LARGE_INTEGER = C.c_uint64, C.c_int64
CREATE_FLAGS = 0x00000004 | 0x08000000 | 0x00080000 | 0x00000400
JOB_FLAGS = 0x00002000 | 0x00000100 | 0x00000200 | 0x00000008
WAIT_OBJECT_0, WAIT_TIMEOUT, INVALID = 0, 258, C.c_void_p(-1).value


class SECURITY_ATTRIBUTES(C.Structure):
    _fields_ = [("nLength", DWORD), ("lpSecurityDescriptor", PVOID), ("bInheritHandle", BOOL)]


class STARTUPINFOW(C.Structure):
    _fields_ = [("cb", DWORD), ("lpReserved", LPWSTR), ("lpDesktop", LPWSTR),
                ("lpTitle", LPWSTR)]
    _fields_ += [(name, DWORD) for name in ("dwX", "dwY", "dwXSize", "dwYSize",
                "dwXCountChars", "dwYCountChars", "dwFillAttribute", "dwFlags")]
    _fields_ += [("wShowWindow", WORD), ("cbReserved2", WORD), ("lpReserved2", PVOID),
                 ("hStdInput", HANDLE), ("hStdOutput", HANDLE), ("hStdError", HANDLE)]


class STARTUPINFOEXW(C.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", PVOID)]


class PROCESS_INFORMATION(C.Structure):
    _fields_ = [("hProcess", HANDLE), ("hThread", HANDLE), ("dwProcessId", DWORD), ("dwThreadId", DWORD)]


class IO_COUNTERS(C.Structure):
    _fields_ = [(name, QWORD) for name in ("ReadOperationCount", "WriteOperationCount",
                "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class BASIC_LIMIT(C.Structure):
    _fields_ = [("PerProcessUserTimeLimit", LARGE_INTEGER), ("PerJobUserTimeLimit", LARGE_INTEGER),
                ("LimitFlags", DWORD), ("MinimumWorkingSetSize", SIZE_T),
                ("MaximumWorkingSetSize", SIZE_T), ("ActiveProcessLimit", DWORD),
                ("Affinity", SIZE_T), ("PriorityClass", DWORD), ("SchedulingClass", DWORD)]


class EXTENDED_LIMIT(C.Structure):
    _fields_ = [("BasicLimitInformation", BASIC_LIMIT), ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
                ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]


class ACCOUNTING(C.Structure):
    _fields_ = [(name, LARGE_INTEGER) for name in ("TotalUserTime", "TotalKernelTime",
                "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime")]
    _fields_ += [(name, DWORD) for name in ("TotalPageFaultCount", "TotalProcesses",
                "ActiveProcesses", "TotalTerminatedProcesses")]


class PID_LIST(C.Structure):
    _fields_ = [("NumberOfAssignedProcesses", DWORD), ("NumberOfProcessIdsInList", DWORD),
                ("ProcessIdList", SIZE_T * 16)]


class FILETIME(C.Structure):
    _fields_ = [("low", DWORD), ("high", DWORD)]


class ATTRIBUTE_TAG(C.Structure):
    _fields_ = [("FileAttributes", DWORD), ("ReparseTag", DWORD)]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def layouts():
    types = dict(SECURITY_ATTRIBUTES=SECURITY_ATTRIBUTES, STARTUPINFOW=STARTUPINFOW,
                 STARTUPINFOEXW=STARTUPINFOEXW, PROCESS_INFORMATION=PROCESS_INFORMATION,
                 IO_COUNTERS=IO_COUNTERS, BASIC_LIMIT=BASIC_LIMIT, EXTENDED_LIMIT=EXTENDED_LIMIT,
                 ACCOUNTING=ACCOUNTING, PID_LIST=PID_LIST, FILETIME=FILETIME, ATTRIBUTE_TAG=ATTRIBUTE_TAG)
    result = {name: C.sizeof(cls) for name, cls in types.items()}
    require(C.sizeof(PVOID) == C.sizeof(SIZE_T) == 8 and C.sizeof(WCHAR) == 2, "Windows x64 required")
    require(result == dict(SECURITY_ATTRIBUTES=24, STARTUPINFOW=104, STARTUPINFOEXW=112,
            PROCESS_INFORMATION=24, IO_COUNTERS=48, BASIC_LIMIT=64, EXTENDED_LIMIT=144,
            ACCOUNTING=48, PID_LIST=136, FILETIME=8, ATTRIBUTE_TAG=8), "SDK size mismatch")
    require([STARTUPINFOW.hStdInput.offset, STARTUPINFOW.hStdOutput.offset,
             STARTUPINFOW.hStdError.offset, STARTUPINFOEXW.lpAttributeList.offset] == [80, 88, 96, 104],
            "SDK startup offsets mismatch")
    require(BASIC_LIMIT.ActiveProcessLimit.offset == 40 and EXTENDED_LIMIT.ProcessMemoryLimit.offset == 112
            and EXTENDED_LIMIT.JobMemoryLimit.offset == 120 and PID_LIST.ProcessIdList.offset == 8,
            "SDK Job offsets mismatch")
    return result


def finite_deadline(deadline):
    require(type(deadline) in (int, float) and math.isfinite(deadline), "Finite deadline required")
    if time.monotonic() >= deadline:
        raise TimeoutError("Declared ABI parent/child deadline exceeded")


def safe(path, *, output=False):
    path = Path(path).absolute()
    require(path.suffix.casefold() != ".gguf" and path.drive.casefold() != "e:"
            and "\\data\\benchmark\\" not in str(path).casefold(), "Protected/model path forbidden")
    if output:
        base = ROOT / "data/cache"
        require(path.is_relative_to(base) and path.resolve().is_relative_to(base.resolve()), "Output outside D cache")
    for part in (path, *path.parents):
        try:
            status = part.lstat()
        except FileNotFoundError:
            continue
        require(not part.is_symlink() and not getattr(status, "st_file_attributes", 0) & 0x400,
                "Reparse ancestry forbidden")
    return path


def file_pin(path):
    path = safe(path)
    require(path.stat().st_size <= 128 * 1024**2, "Input file cap")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def write_new(path, value):
    with safe(path, output=True).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def effective_environment(output):
    system = Path(r"C:\Windows")
    return dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive="C:",
                PATH=str(system / "System32"), TEMP=str(output), TMP=str(output),
                OMP_NUM_THREADS="1", OMP_THREAD_LIMIT="1")


def environment_block(environment):
    require(type(environment) is dict and environment, "Explicit environment required")
    lowered = set()
    for key, value in environment.items():
        require(type(key) is str and key and "=" not in key and "\0" not in key
                and type(value) is str and "\0" not in value, "Invalid environment entry")
        require(key.casefold() not in lowered, "Ambiguous Windows environment key")
        lowered.add(key.casefold())
        key.encode("utf-16-le"); value.encode("utf-16-le")
    text = "\0".join(key + "=" + environment[key] for key in sorted(environment, key=str.casefold)) + "\0\0"
    require(len(text.encode("utf-16-le")) <= 65536, "Environment cap")
    return text


def abi_argv(exe, runtime, child):
    argv = [str(safe(exe)), "--abi", str(safe(runtime)), str(safe(child, output=True))]
    require(Path(argv[0]) == EXE and Path(argv[2]) == RUNTIME and len(argv) == 4,
            "Exact ABI-only executable/runtime/argv required")
    require(all("\0" not in x for x in argv), "NUL argv")
    command = subprocess.list2cmdline(argv)
    require(len(command.encode("utf-16-le")) // 2 + 1 <= 32767, "Command line cap")
    return argv, command


class Kernel32:
    """Unqualified public-SDK binding. Constructor is deliberately held."""
    def __init__(self):
        require(NATIVE_EXECUTION_ENABLED, "DRAFT: native API construction is disabled")
        layouts()
        require(os.name == "nt", "Windows required")
        self.k = C.WinDLL(r"C:\Windows\System32\kernel32.dll", use_last_error=True)
        ptr = C.POINTER
        specs = {
            "CreateJobObjectW": ([PVOID, LPWSTR], HANDLE),
            "SetInformationJobObject": ([HANDLE, DWORD, PVOID, DWORD], BOOL),
            "QueryInformationJobObject": ([HANDLE, DWORD, PVOID, DWORD, ptr(DWORD)], BOOL),
            "AssignProcessToJobObject": ([HANDLE, HANDLE], BOOL),
            "IsProcessInJob": ([HANDLE, HANDLE, ptr(BOOL)], BOOL),
            "CreatePipe": ([ptr(HANDLE), ptr(HANDLE), ptr(SECURITY_ATTRIBUTES), DWORD], BOOL),
            "SetHandleInformation": ([HANDLE, DWORD, DWORD], BOOL),
            "InitializeProcThreadAttributeList": ([PVOID, DWORD, DWORD, ptr(SIZE_T)], BOOL),
            "UpdateProcThreadAttribute": ([PVOID, DWORD, SIZE_T, PVOID, SIZE_T, PVOID, ptr(SIZE_T)], BOOL),
            "DeleteProcThreadAttributeList": ([PVOID], None),
            "CreateProcessW": ([LPWSTR, ptr(WCHAR), PVOID, PVOID, BOOL, DWORD, PVOID, LPWSTR,
                                ptr(STARTUPINFOW), ptr(PROCESS_INFORMATION)], BOOL),
            "ResumeThread": ([HANDLE], DWORD),
            "WaitForSingleObject": ([HANDLE, DWORD], DWORD),
            "GetExitCodeProcess": ([HANDLE, ptr(DWORD)], BOOL),
            "TerminateProcess": ([HANDLE, DWORD], BOOL),
            "TerminateJobObject": ([HANDLE, DWORD], BOOL),
            "CloseHandle": ([HANDLE], BOOL),
            "GetProcessId": ([HANDLE], DWORD),
            "GetThreadId": ([HANDLE], DWORD),
            "GetProcessIdOfThread": ([HANDLE], DWORD),
            "QueryFullProcessImageNameW": ([HANDLE, DWORD, ptr(WCHAR), ptr(DWORD)], BOOL),
            "GetProcessTimes": ([HANDLE, ptr(FILETIME), ptr(FILETIME), ptr(FILETIME), ptr(FILETIME)], BOOL),
            "PeekNamedPipe": ([HANDLE, PVOID, DWORD, ptr(DWORD), ptr(DWORD), ptr(DWORD)], BOOL),
            "ReadFile": ([HANDLE, PVOID, DWORD, ptr(DWORD), PVOID], BOOL),
            "CreateFileW": ([LPWSTR, DWORD, DWORD, ptr(SECURITY_ATTRIBUTES), DWORD, DWORD, HANDLE], HANDLE),
            "GetFileSizeEx": ([HANDLE, ptr(LARGE_INTEGER)], BOOL),
            "GetFileInformationByHandleEx": ([HANDLE, DWORD, PVOID, DWORD], BOOL),
            "GetFinalPathNameByHandleW": ([HANDLE, ptr(WCHAR), DWORD, DWORD], DWORD),
        }
        for name, (args, result) in specs.items():
            method = getattr(self.k, name)
            method.argtypes, method.restype = args, result

    @staticmethod
    def win(ok, message):
        if not ok:
            raise OSError(C.get_last_error(), message)

    def close(self, handle):
        if handle not in (None, 0, INVALID):
            self.win(self.k.CloseHandle(handle), "Close owned handle")

    def create_job(self):
        h = self.k.CreateJobObjectW(None, None)
        self.win(h, "Create unnamed Job")
        return h

    def configure_job(self, job):
        info = EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = JOB_FLAGS
        info.BasicLimitInformation.ActiveProcessLimit = 1
        info.ProcessMemoryLimit = info.JobMemoryLimit = LIMITS["commit_bytes"]
        self.win(self.k.SetInformationJobObject(job, 9, C.byref(info), C.sizeof(info)), "Set finite Job limits")
        self.verify_limits(job)

    def verify_limits(self, job):
        info = EXTENDED_LIMIT()
        self.win(self.k.QueryInformationJobObject(job, 9, C.byref(info), C.sizeof(info), None), "Read Job limits")
        require(info.BasicLimitInformation.LimitFlags == JOB_FLAGS
                and info.BasicLimitInformation.ActiveProcessLimit == 1
                and info.ProcessMemoryLimit == info.JobMemoryLimit == LIMITS["commit_bytes"], "Job limit readback differs")
        return dict(flags=info.BasicLimitInformation.LimitFlags, active_limit=1,
                    process_commit=info.ProcessMemoryLimit, job_commit=info.JobMemoryLimit,
                    peak_process_commit=info.PeakProcessMemoryUsed, peak_job_commit=info.PeakJobMemoryUsed)

    def job_snapshot(self, job):
        a, ids, returned = ACCOUNTING(), PID_LIST(), DWORD()
        self.win(self.k.QueryInformationJobObject(job, 1, C.byref(a), C.sizeof(a), C.byref(returned)), "Read owned Job accounting")
        require(returned.value == C.sizeof(a), "Accounting returned length")
        self.win(self.k.QueryInformationJobObject(job, 3, C.byref(ids), C.sizeof(ids), C.byref(returned)), "Read bounded owned Job PIDs")
        n = ids.NumberOfProcessIdsInList
        require(n <= 16 and ids.NumberOfAssignedProcesses == n
                and 8 + 8*n <= returned.value <= C.sizeof(ids), "Truncated/anomalous Job PID list")
        return dict(total=a.TotalProcesses, active=a.ActiveProcesses, terminated=a.TotalTerminatedProcesses,
                    pids=[int(ids.ProcessIdList[i]) for i in range(n)])

    def make_stdio(self, owned):
        sa = SECURITY_ATTRIBUTES(C.sizeof(SECURITY_ATTRIBUTES), None, 1)
        h = self.k.CreateFileW("NUL", 0x80000000, 3, C.byref(sa), 3, 0x80, None)
        self.win(h != INVALID, "Open inherited NUL stdin")
        owned["stdin"] = h
        for name in ("stdout", "stderr"):
            read, write = HANDLE(), HANDLE()
            try:
                self.win(self.k.CreatePipe(C.byref(read), C.byref(write), C.byref(sa), 4096), "Create stdio pipe")
            finally:
                if read.value: owned[name + "_read"] = read.value
                if write.value: owned[name + "_write"] = write.value
            self.win(self.k.SetHandleInformation(read, 1, 0), "Exclude parent reader from inheritance")

    def create_suspended(self, argv, command, environment, cwd, handles, pi):
        count = SIZE_T()
        C.set_last_error(0)
        ok = self.k.InitializeProcThreadAttributeList(None, 1, 0, C.byref(count))
        require(not ok and C.get_last_error() == 122 and 0 < count.value <= 65536, "Attribute-list sizing response")
        memory = C.create_string_buffer(count.value)
        initialized = False
        try:
            self.win(self.k.InitializeProcThreadAttributeList(memory, 1, 0, C.byref(count)), "Initialize attribute list")
            initialized = True
            inherited = (HANDLE * 3)(handles["stdin"], handles["stdout_write"], handles["stderr_write"])
            require(len(set(inherited)) == 3 and all(x not in (None, 0, INVALID) for x in inherited), "Three distinct real stdio handles")
            self.win(self.k.UpdateProcThreadAttribute(memory, 0, 0x00020002, C.byref(inherited), C.sizeof(inherited), None, None), "Restrict inherited handle list")
            startup = STARTUPINFOEXW()
            startup.StartupInfo.cb = C.sizeof(startup)
            startup.StartupInfo.dwFlags = 0x100
            startup.StartupInfo.hStdInput = handles["stdin"]
            startup.StartupInfo.hStdOutput = handles["stdout_write"]
            startup.StartupInfo.hStdError = handles["stderr_write"]
            startup.lpAttributeList = C.cast(memory, PVOID)
            command_bytes = command.encode("utf-16-le") + b"\0\0"
            cmd = C.create_string_buffer(command_bytes, len(command_bytes))
            text = environment_block(environment)
            encoded = text.encode("utf-16-le")
            env = C.create_string_buffer(encoded, len(encoded))
            self.win(self.k.CreateProcessW(argv[0], C.cast(cmd, C.POINTER(WCHAR)), None, None, True, CREATE_FLAGS,
                     env, str(cwd), C.cast(C.byref(startup), C.POINTER(STARTUPINFOW)), C.byref(pi)), "Create exact suspended process")
        finally:
            if initialized:
                self.k.DeleteProcThreadAttributeList(memory)

    def assign(self, job, process):
        self.win(self.k.AssignProcessToJobObject(job, process), "Assign still-suspended process to owned Job")

    def in_job(self, job, process):
        answer = BOOL()
        self.win(self.k.IsProcessInJob(process, job, C.byref(answer)), "Verify exact Job membership")
        return bool(answer.value)

    def identity(self, pi, exe):
        require(self.k.GetProcessId(pi.hProcess) == pi.dwProcessId > 0
                and self.k.GetThreadId(pi.hThread) == pi.dwThreadId > 0
                and self.k.GetProcessIdOfThread(pi.hThread) == pi.dwProcessId, "Owned process/thread identity mismatch")
        size = DWORD(32768)
        text = C.create_unicode_buffer(size.value)
        self.win(self.k.QueryFullProcessImageNameW(pi.hProcess, 0, text, C.byref(size)), "Read exact owned process image")
        require(0 < size.value < 32768 and Path(text.value) == exe, "Owned image differs")
        times = [FILETIME() for _ in range(4)]
        self.win(self.k.GetProcessTimes(pi.hProcess, *(C.byref(x) for x in times)), "Read owned creation time")
        created = times[0].low | (times[0].high << 32)
        require(created > 0, "Empty owned creation time")
        return dict(pid=int(pi.dwProcessId), thread_id=int(pi.dwThreadId), image=text.value,
                    creation_filetime=created, directly_created_suspended=True)

    def resume(self, thread):
        return int(self.k.ResumeThread(thread))

    def wait(self, process, milliseconds):
        status = int(self.k.WaitForSingleObject(process, milliseconds))
        require(status in (WAIT_OBJECT_0, WAIT_TIMEOUT), "Owned process wait failed")
        return status == WAIT_OBJECT_0

    def terminate_process(self, process):
        self.win(self.k.TerminateProcess(process, 125), "Terminate newly owned process")

    def terminate_job(self, job):
        self.win(self.k.TerminateJobObject(job, 125), "Terminate newly owned Job")

    def exit_code(self, process):
        code = DWORD()
        self.win(self.k.GetExitCodeProcess(process, C.byref(code)), "Read owned exit code")
        return int(code.value)

    def available(self, handle):
        available = DWORD()
        ok = self.k.PeekNamedPipe(handle, None, 0, None, C.byref(available), None)
        if not ok and C.get_last_error() in (109, 233):
            return None  # EOF after all child/parent writers close.
        self.win(ok, "Peek owned output pipe")
        return int(available.value)

    def read(self, handle, count):
        require(0 < count <= 4096, "Bounded pipe read required")
        memory, got = C.create_string_buffer(count), DWORD()
        self.win(self.k.ReadFile(handle, memory, count, C.byref(got), None), "Read available owned pipe bytes")
        require(got.value <= count, "Pipe read size")
        return memory.raw[:got.value]

    def read_lease(self, item, deadline):
        path = safe(item["path"])
        h = self.k.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000 | 0x80, None)
        self.win(h != INVALID, "Lease original file read-only without write/delete sharing")
        try:
            info = ATTRIBUTE_TAG()
            self.win(self.k.GetFileInformationByHandleEx(h, 9, C.byref(info), C.sizeof(info)), "Lease file attributes")
            require(not info.FileAttributes & (0x400 | 0x10), "Lease is directory/reparse")
            text = C.create_unicode_buffer(32768)
            n = self.k.GetFinalPathNameByHandleW(h, text, len(text), 0)
            require(0 < n < len(text), "Lease canonical path unavailable")
            final = text.value[4:] if text.value.startswith("\\\\?\\") else text.value
            require(Path(final) == path, "Lease resolved outside original canonical path")
            self.hash_lease(h, item, deadline)
            return h
        except BaseException:
            self.close(h)
            raise

    def hash_lease(self, handle, item, deadline):
        # Fresh handles begin at zero. For final rechecks, use a second read-only
        # leased handle while the original lease remains held (see verify_pins).
        size = LARGE_INTEGER()
        self.win(self.k.GetFileSizeEx(handle, C.byref(size)), "Read leased size")
        require(size.value == item["bytes"] and 0 <= size.value <= 128 * 1024**2, "Leased size changed")
        digest, read = hashlib.sha256(), 0
        while read < size.value:
            finite_deadline(deadline)
            count = min(65536, size.value - read)
            memory, got = C.create_string_buffer(count), DWORD()
            self.win(self.k.ReadFile(handle, memory, count, C.byref(got), None), "Hash leased original file")
            require(0 < got.value <= count, "Leased read incomplete")
            digest.update(memory.raw[:got.value]); read += got.value
        require(digest.hexdigest() == item["sha256"], "Leased bytes changed")


class OwnedLaunch:
    """No async readers. Exact newly-created process/thread/Job handles only."""
    def __init__(self, api, event):
        self.api, self.event = api, event
        self.job, self.pi, self.handles = None, PROCESS_INFORMATION(), {}
        self.assigned = self.resumed = self.reaped = False
        self.cleanup_errors = []

    def close_stdio_writers(self):
        for name in ("stdin", "stdout_write", "stderr_write"):
            handle = self.handles.get(name)
            if handle:
                self.api.close(handle)
                del self.handles[name]

    def start(self, argv, command, environment, cwd, check):
        self.job = self.api.create_job()
        self.api.configure_job(self.job)
        empty = self.api.job_snapshot(self.job)
        require(empty == dict(total=0, active=0, terminated=0, pids=[]), "New Job is not empty")
        self.event("abi_job_configured_empty", snapshot=empty, limits=self.api.verify_limits(self.job))
        self.api.make_stdio(self.handles)
        check()
        self.event("abi_create_suspended_reserved", argv=argv, environment=environment, creation_flags=CREATE_FLAGS)
        self.api.create_suspended(argv, command, environment, cwd, self.handles, self.pi)
        require(self.pi.hProcess and self.pi.hThread and self.pi.dwProcessId, "Create did not bind owned handles")
        self.event("abi_created_suspended", pid=int(self.pi.dwProcessId), thread_id=int(self.pi.dwThreadId))
        self.close_stdio_writers()
        check()
        self.api.assign(self.job, self.pi.hProcess)
        self.assigned = True
        require(self.api.in_job(self.job, self.pi.hProcess), "Owned process not in exact Job")
        limits = self.api.verify_limits(self.job)
        identity = self.api.identity(self.pi, Path(argv[0]))
        snapshot = self.api.job_snapshot(self.job)
        require(snapshot == dict(total=1, active=1, terminated=0, pids=[int(self.pi.dwProcessId)]),
                "Job identity/accounting anomaly before resume")
        self.event("abi_assigned_before_resume", identity=identity, snapshot=snapshot, limits=limits)
        check()
        # This durable reservation is before the sole ResumeThread call.
        self.event("abi_resume_reserved", pid=int(self.pi.dwProcessId))
        previous = self.api.resume(self.pi.hThread)
        self.resumed = previous == 1
        self.event("abi_resume_returned", previous_suspend_count=previous)
        require(previous == 1, "ResumeThread did not consume exactly one suspension")
        check()

    def cleanup(self, deadline):
        """Best-effort independent steps; primary execution error stays primary."""
        def attempt(name, callback):
            try:
                callback()
            except BaseException as error:
                self.cleanup_errors.append(dict(step=name, error_class=type(error).__name__, error=str(error)[:512]))
        if self.pi.hProcess:
            try:
                done = self.api.wait(self.pi.hProcess, 0)
            except BaseException as error:
                done = False
                self.cleanup_errors.append(dict(step="initial_wait", error_class=type(error).__name__))
            if not done:
                if self.job and self.assigned:
                    attempt("terminate_job", lambda: self.api.terminate_job(self.job))
                try:
                    done = self.api.wait(self.pi.hProcess, 0)
                except BaseException:
                    done = False
                if not done:
                    attempt("terminate_owned_process", lambda: self.api.terminate_process(self.pi.hProcess))
                try:
                    remaining = max(0, min(2000, int((deadline-time.monotonic())*1000)))
                    done = self.api.wait(self.pi.hProcess, remaining)
                except BaseException as error:
                    self.cleanup_errors.append(dict(step="final_wait", error_class=type(error).__name__))
            self.reaped = bool(done)
            if not done:
                self.cleanup_errors.append(dict(step="final_wait", error_class="OwnedProcessNotReaped"))
        for name in list(self.handles):
            handle = self.handles.pop(name)
            attempt("close_" + name, lambda handle=handle: self.api.close(handle))
        for name in ("hThread", "hProcess"):
            handle = getattr(self.pi, name)
            if handle:
                attempt("close_" + name, lambda handle=handle: self.api.close(handle))
                setattr(self.pi, name, None)
        if self.job:
            job, self.job = self.job, None
            attempt("close_job_kill_on_close", lambda: self.api.close(job))


def consume_capture(state, block, sink, *, cap=65536):
    require(type(block) is bytes and type(cap) is int and cap > 0, "Capture type/cap")
    state["observed_bytes_at_least"] += len(block)
    available = max(0, cap - state["retained_bytes"])
    retained = block[:available]
    if retained:
        sink.write(retained)
        state["retained_bytes"] += len(retained)
    if len(block) > available:
        state["truncated"] = True
        raise RuntimeError("ABI stream cap exceeded; unknown further bytes")


def capture_poll(owner, captures, sinks):
    for name in ("stdout", "stderr"):
        state, handle = captures[name], owner.handles[name + "_read"]
        if state["eof"]:
            continue
        available = owner.api.available(handle)
        if available is None:
            state["eof"] = True
        elif available:
            block = owner.api.read(handle, min(4096, available))
            require(block, "Pipe advertised bytes but returned none")
            consume_capture(state, block, sinks[name], cap=LIMITS["stream_bytes"])


def prepare_config(output):
    """Read-only preparation, not a protocol decision or native qualification."""
    output = safe(output, output=True)
    require(not output.exists(), "Output already exists; no automatic restart")
    protocol_raw = (HERE / "BUILD-PROTOCOL.json").read_bytes()
    require(hashlib.sha256(protocol_raw).hexdigest() == BUILD_PROTOCOL_SHA, "Build protocol changed")
    protocol = json.loads(protocol_raw)
    require(file_pin(BUILD / "receipt.json")["sha256"] == BUILD_RECEIPT_SHA, "Build receipt changed")
    require(file_pin(EXE)["sha256"] == EXE_SHA and protocol["recognition_enabled"] is False
            and protocol["expected_version"] == "" and protocol["execute_result"] is False, "ABI-only build scope changed")
    inputs = {item["path"]: item for item in protocol["inputs"]}
    require(len(inputs) == 193, "Build pin universe changed")
    # Retain all earlier pins; adding reviewed build outputs and public SDK text
    # does not authorize compiling or running any source file.
    extra = [EXE, BUILD / "receipt.json", HERE / "BUILD-PROTOCOL.json", Path(__file__),
             HERE / "BUILD-ROOT-DECISION.json", HERE / "BUILD-RESULT-VERIFICATION.json"]
    sdk = Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um")
    extra += [sdk / name for name in ("processthreadsapi.h", "winbase.h", "winnt.h", "fileapi.h", "namedpipeapi.h", "jobapi2.h")]
    for path in extra:
        item = file_pin(path); inputs[item["path"]] = item
    for item in inputs.values():
        require(file_pin(item["path"]) == item, "Prospective input hash changed")
    header = (PREPARED / "recognizer_runtime_pins.hpp").read_text()
    require('R09_RECOGNITION_ENABLED = false' in header and 'R09_EXPECTED_LLAMA_VERSION[] = ""' in header,
            "Pin header no longer ABI-only")
    runtime = RUNTIME
    argv, command = abi_argv(EXE, runtime, output / "child")
    environment = effective_environment(output)
    return dict(schema_version=1, kind="prospective_abi_public_sdk_suspended_parent_v1",
                status="draft_native_execution_disabled", execution_authorized=False,
                output=str(output), argv=argv, command_line=command,
                environment=environment, environment_sha256=hashlib.sha256(canonical(environment)).hexdigest(),
                limits=dict(LIMITS), inputs=list(inputs.values()), layouts=layouts(),
                source_only_no_GGUF=True, no_process_dispatch=True,
                remaining_gates=["OS accounting diagnostic", "exact helper peer review", "harmless suspended-worker qualification",
                                 "exact prospective protocol/root execution decision"])


def validate_child_artifacts(child):
    require({p.name for p in child.iterdir()} == {"attempt.json", "result.jsonl"}, "Incomplete/unexpected ABI child files")
    attempt, result = child / "attempt.json", child / "result.jsonl"
    require(attempt.stat().st_size <= LIMITS["attempt_bytes"] and 0 < result.stat().st_size <= LIMITS["result_jsonl_bytes"], "Child artifact caps")
    claim = json.loads(attempt.read_bytes())
    require(claim == dict(schema_version=1, mode="--abi", status="claimed_before_native_load", draft=True), "Child mode claim differs")
    raw = result.read_bytes()
    require(raw.endswith(b"\n"), "Unterminated ABI result journal")
    rows = []
    def object_pairs(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "Duplicate child JSON key")
            out[key] = value
        return out
    for line in raw.split(b"\n")[:-1]:
        require(0 < len(line) <= LIMITS["row_bytes"], "ABI result row cap")
        rows.append(json.loads(line, object_pairs_hook=object_pairs,
                    parse_constant=lambda token: (_ for _ in ()).throw(RuntimeError("Nonfinite JSON"))))
    require([row.get("event") for row in rows] == ["before_explicit_required_OpenMP_dependency_load",
            "exact_core_modules_loaded_exports_resolved", "typed_version_and_defaults_observed",
            "abi_observations_returned", "child_normal_completion"], "ABI event sequence differs")
    observed, end = rows[2], rows[3]
    require(type(observed["version"]) is str and 0 < len(observed["version"]) <= 256
            and all(32 <= ord(c) <= 126 for c in observed["version"]), "Invalid version observation")
    require(observed["no_backend_or_model_call_so_far"] is True
            and all(end[key] is False for key in ("version_expected_previously_known", "backend_init_called", "registry_called", "model_called"))
            and rows[-1]["mode"] == "--abi" and rows[-1]["parent_qualification_required"] is True,
            "ABI-only observation scope differs")
    return dict(version=observed["version"], defaults=observed["defaults"], layouts=rows[1]["layouts"],
                raw_modules=rows[1]["modules"], independent_ABI_acceptance="pending", result_rows=len(rows))


def execute_draft(config):
    """Prospective orchestration, permanently held in this exact source version.

    A separately reviewed version/decision must provide harmless-worker and OS
    evidence before enabling real APIs. No CLI calls this function.
    """
    require(NATIVE_EXECUTION_ENABLED, "DRAFT: execution disabled; no target dispatch")
    from asof.journal import RunJournal, read_chain
    require(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode, "Windows -I -B required")
    require(config == prepare_config(config["output"]), "Prospective configuration changed")
    output = safe(config["output"], output=True)
    require(not output.exists(), "Attempt already consumed")
    started = time.monotonic(); parent_end = started + 60
    journal = RunJournal(output, kind="native_abi")
    child = output / "child"; child.mkdir()
    api, owner, leases = None, None, []
    sinks = ExitStack()
    captures = {name:dict(observed_bytes_at_least=0, retained_bytes=0, truncated=False, eof=False)
                for name in ("stdout", "stderr")}
    report = dict(status="failed", schema_version=1, automatic_retry=False, cleanup_errors=[],
                  model_reads=0, vocabulary_calls=0, backend_calls=0, registry_calls=0,
                  tokenizer_calls=0, grammar_calls=0, network_calls=0, captures=captures)
    failure = None; child_start = child_end = None
    def event(name, **details):
        journal.append(name, **details)
    try:
        event("abi_parent_attempt_reserved", helper_sha256=file_pin(__file__)["sha256"], limits=LIMITS)
        write_new(output / "effective-config.json", config)
        api = Kernel32()
        for item in config["inputs"]:
            finite_deadline(parent_end-5)
            leases.append(api.read_lease(item, parent_end-5))
        owner = OwnedLaunch(api, event)
        streams = {name:sinks.enter_context((output / (name + ".bin")).open("xb")) for name in captures}
        child_start = time.monotonic(); child_end = min(child_start + 30, parent_end-5)
        check = lambda: finite_deadline(child_end-2)  # two seconds reserved for owned termination/reap
        owner.start(config["argv"], config["command_line"], config["environment"], output, check)
        last_snapshot = time.monotonic()
        while True:
            check(); capture_poll(owner, captures, streams)
            if api.wait(owner.pi.hProcess, 0):
                break
            if time.monotonic()-last_snapshot >= .1:
                snapshot = api.job_snapshot(owner.job)
                require(snapshot == dict(total=1, active=1, terminated=0, pids=[int(owner.pi.dwProcessId)]), "Running Job accounting anomaly")
                last_snapshot = time.monotonic()
            time.sleep(.01)
        report["returncode"] = api.exit_code(owner.pi.hProcess)
        require(report["returncode"] == 0, "ABI child failed")
        while not all(record["eof"] for record in captures.values()):
            check(); capture_poll(owner, captures, streams); time.sleep(.005)
        snapshot = api.job_snapshot(owner.job)
        require(snapshot == dict(total=1, active=0, terminated=0, pids=[]), "Terminal Job accounting anomaly")
        report["final_job_snapshot"] = snapshot
        report["memory_limits_and_peaks"] = api.verify_limits(owner.job)
        report["observations"] = validate_child_artifacts(child)
        report["status"] = "ABI_observations_retained_independent_qualification_pending"
    except BaseException as error:
        failure = dict(error_class=type(error).__name__, error=str(error)[:2048])
    finally:
        if owner:
            owner.cleanup(min(child_end or parent_end, parent_end))
            report.update(reaped=owner.reaped, assigned_before_resume=owner.assigned,
                          resumed=owner.resumed, cleanup_errors=owner.cleanup_errors)
            if owner.cleanup_errors and failure is None:
                failure = dict(error_class="OwnedCleanupFailure", error="See retained cleanup_errors")
        try:
            for stream in locals().get("streams", {}).values():
                stream.flush(); os.fsync(stream.fileno())
            sinks.close()
            report["child_full_process_elapsed_seconds"] = None if child_start is None else time.monotonic()-child_start
            if child_start is not None and report["child_full_process_elapsed_seconds"] > 30 and failure is None:
                failure = dict(error_class="ChildWholeProcessDeadline", error="Child attempt including cleanup exceeded30s")
            if api:
                # Original leases stay held while independent second read-only
                # handles rehash every frozen file at its original path.
                for item in config["inputs"]:
                    handle = api.read_lease(item, parent_end)
                    api.close(handle)
            finite_deadline(parent_end)
        except BaseException as error:
            report["finalization_error"] = dict(error_class=type(error).__name__, error=str(error)[:512])
            if failure is None: failure = report["finalization_error"]
        report["parent_elapsed_before_sealing_seconds"] = time.monotonic()-started
        if time.monotonic() >= parent_end and failure is None:
            failure = dict(error_class="ParentDeadline", error="Whole parent exceeded60s")
        if failure:
            report.update(status="failed", failure=failure)
            try: write_new(output / "failure.json", dict(authoritative=True, automatic_retry=False, **failure))
            except BaseException as marker: report["failure_marker_error_class"] = type(marker).__name__
        try:
            try:
                event("abi_parent_terminal", status=report["status"], failure=failure)
            finally:
                journal.close()
            write_new(output / "parent-report.json", report)
            finite_deadline(parent_end)
            outputs = {}
            for path in sorted(output.rglob("*")):
                finite_deadline(parent_end)
                if path.is_file():
                    p = file_pin(path); outputs[path.relative_to(output).as_posix()] = {k:p[k] for k in ("bytes", "sha256")}
            chain = read_chain(output / "journal.jsonl")
            write_new(output / "receipt.json", dict(schema_version=1, status=report["status"], outputs=outputs,
                      journal_tip_sha256=chain[-1]["sha256"], failure_veto="Any failure.json overrides receipt/status"))
            finite_deadline(parent_end)
        except BaseException as error:
            if not (output / "failure.json").exists():
                write_new(output / "failure.json", dict(authoritative=True, automatic_retry=False,
                          error_class=type(error).__name__, error="ABI terminal sealing failed"))
            raise
        finally:
            # Keep original read leases through recheck and receipt publication.
            close_errors = []
            if api:
                for handle in reversed(leases):
                    try: api.close(handle)
                    except BaseException as error:
                        close_errors.append(dict(step="close_read_lease", error_class=type(error).__name__))
            if (close_errors or time.monotonic() >= parent_end) and not (output / "failure.json").exists():
                write_new(output / "failure.json", dict(authoritative=True, automatic_retry=False,
                          error_class="LeaseCleanupOrParentDeadline", cleanup_errors=close_errors,
                          error="Post-receipt lease cleanup/deadline failed; earlier receipt is not authoritative"))
                report["status"] = "failed"
    return report


if __name__ == "__main__":
    raise SystemExit("DRAFT ONLY: no execution command. Use separately reviewed pure checks.")
