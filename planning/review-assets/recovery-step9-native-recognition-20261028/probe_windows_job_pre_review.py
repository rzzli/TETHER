"""Own-source OS-only containment probe. Never imports/loads llama or a model.

Direct pinned Python child waits for the parent to assign its job before doing
bounded memory/process fixtures. This is not a native-library qualification.
"""
from ctypes import WinDLL, Structure, POINTER, byref, sizeof, c_size_t, get_last_error
from ctypes.wintypes import BOOL, DWORD, HANDLE, LARGE_INTEGER, LPVOID, ULONG
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
BASE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"
CAP = 64 * 1024 * 1024
SIZE_T = c_size_t


def write_new(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


class BasicLimit(Structure):
    _fields_ = [("PerProcessUserTimeLimit", LARGE_INTEGER),
                ("PerJobUserTimeLimit", LARGE_INTEGER), ("LimitFlags", DWORD),
                ("MinimumWorkingSetSize", SIZE_T), ("MaximumWorkingSetSize", SIZE_T),
                ("ActiveProcessLimit", DWORD), ("Affinity", SIZE_T),
                ("PriorityClass", DWORD), ("SchedulingClass", DWORD)]


class IoCounters(Structure):
    _fields_ = [(name, LARGE_INTEGER) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class ExtendedLimit(Structure):
    _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
                ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]


class Accounting(Structure):
    _fields_ = [(name, LARGE_INTEGER) for name in (
        "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime")]
    _fields_ += [(name, DWORD) for name in (
        "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")]


def api():
    dll = WinDLL("kernel32", use_last_error=True)
    specs = {
        "CreateJobObjectW": ([LPVOID, LPVOID], HANDLE),
        "SetInformationJobObject": ([HANDLE, DWORD, LPVOID, DWORD], BOOL),
        "QueryInformationJobObject": ([HANDLE, DWORD, LPVOID, DWORD, POINTER(DWORD)], BOOL),
        "AssignProcessToJobObject": ([HANDLE, HANDLE], BOOL),
        "TerminateJobObject": ([HANDLE, ULONG], BOOL),
        "CloseHandle": ([HANDLE], BOOL),
    }
    for name, (args, result) in specs.items():
        func = getattr(dll, name)
        func.argtypes, func.restype = args, result
    return dll


def need(value, detail):
    if not value:
        raise RuntimeError(f"{detail}; winerror={get_last_error()}")


def query(k, job):
    limits, accounting = ExtendedLimit(), Accounting()
    need(k.QueryInformationJobObject(job, 9, byref(limits), sizeof(limits), None), "Query limits")
    need(k.QueryInformationJobObject(job, 1, byref(accounting), sizeof(accounting), None), "Query accounting")
    return dict(limit_flags=limits.BasicLimitInformation.LimitFlags,
                active_limit=limits.BasicLimitInformation.ActiveProcessLimit,
                process_commit_limit=limits.ProcessMemoryLimit,
                peak_process_commit=limits.PeakProcessMemoryUsed,
                peak_job_commit=limits.PeakJobMemoryUsed,
                total_processes=accounting.TotalProcesses,
                active_processes=accounting.ActiveProcesses,
                terminated_processes=accounting.TotalTerminatedProcesses)


def child(directory, mode):
    started = time.monotonic()
    write_new(directory / "started.json", dict(pid=os.getpid(), parent_pid=os.getppid(), mode=mode))
    while not (directory / "assigned.json").exists():
        if time.monotonic() - started > 5:
            raise TimeoutError("No job-assignment authorization")
        time.sleep(.01)
    identity = json.loads((directory / "assigned.json").read_bytes())
    need(identity["pid"] == os.getpid() and identity["parent_pid"] == os.getppid(), "Assignment identity")
    if mode == "limits":
        memory_rejected = False
        try:
            value = bytearray(96 * 1024 * 1024)
            del value
        except MemoryError:
            memory_rejected = True
        descendant = None
        try:
            descendant = subprocess.Popen([str(BASE), "-I", "-B", "-c", "pass"],
                creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env={"SystemRoot": os.environ["SystemRoot"]})
        except OSError as error:
            spawn = dict(rejected=True, error_class=type(error).__name__, winerror=error.winerror)
        else:
            try:
                descendant.wait(timeout=3)
                spawn = dict(rejected=False, pid=descendant.pid, exit_code=descendant.returncode)
            finally:
                if descendant.poll() is None:
                    descendant.kill()
                    descendant.wait(timeout=3)
        write_new(directory / "child-result.json", dict(memory_rejected=memory_rejected, spawn=spawn))
        need(memory_rejected and spawn["rejected"], "OS resource fixtures did not reject")
    elif mode in ("timeout", "close"):
        write_new(directory / "ready-for-kill.json", dict(pid=os.getpid()))
        time.sleep(30)
        raise RuntimeError("Parent timeout did not kill")
    else:
        raise ValueError("Unknown fixture")


def parent():
    need(os.name == "nt" and sizeof(c_size_t) == 8 and sys.flags.isolated and sys.dont_write_bytecode,
         "Windows x64 isolated no-bytecode probe required")
    need(hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA, "Base interpreter differs")
    need(sizeof(BasicLimit) == 64 and sizeof(ExtendedLimit) == 144 and sizeof(Accounting) == 48,
         "Unexpected Windows x64 ctypes layouts")
    directory = ROOT / "data/cache" / ("r09-windows-job-probe-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    directory.mkdir()
    k = api()
    report = dict(schema_version=1, status="failed", output=str(directory),
                  scope="Own Python/Windows OS fixtures only", native_target_calls=0, gguf_reads=0,
                  model_calls=0, network_requests=0, provider_spend_usd=0, attempts=[])
    try:
        for mode in ("limits", "timeout", "close"):
            leaf = directory / mode
            leaf.mkdir()
            job = k.CreateJobObjectW(None, None)
            need(job, "Create unnamed job")
            process = None
            attempt = dict(mode=mode)
            report["attempts"].append(attempt)
            try:
                limits = ExtendedLimit()
                limits.BasicLimitInformation.LimitFlags = 0x2000 | 0x100 | 0x8  # kill-on-close, commit, active
                limits.BasicLimitInformation.ActiveProcessLimit = 1
                limits.ProcessMemoryLimit = CAP
                need(k.SetInformationJobObject(job, 9, byref(limits), sizeof(limits)), "Set finite job")
                with (leaf / "stdout.bin").open("xb") as out, (leaf / "stderr.bin").open("xb") as err:
                    process = subprocess.Popen([str(BASE), "-I", "-B", str(Path(__file__).resolve()),
                        "--child", str(leaf), mode], cwd=str(ROOT), env={"SystemRoot": os.environ["SystemRoot"]},
                        stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
                    attempt["pid"] = process.pid
                    need(k.AssignProcessToJobObject(job, HANDLE(int(process._handle))), "Assign owned worker")
                    attempt["assigned_before_authorization"] = True
                    write_new(leaf / "assigned.json", dict(pid=process.pid, parent_pid=os.getpid()))
                    started = time.monotonic()
                    if mode in ("timeout", "close"):
                        while not (leaf / "ready-for-kill.json").exists():
                            need(process.poll() is None and time.monotonic() - started < 5, "Wait timeout fixture")
                            time.sleep(.01)
                        attempt["before_termination"] = query(k, job)
                        if mode == "timeout":
                            need(k.TerminateJobObject(job, 87), "Terminate owned timeout job")
                        else:
                            need(k.CloseHandle(job), "Close last owned job handle")
                            job = None
                            attempt["last_job_handle_closed_before_wait"] = True
                    process.wait(timeout=7)
                    attempt.update(exit_code=process.returncode, reaped=True, elapsed_seconds=time.monotonic() - started)
                identity = json.loads((leaf / "started.json").read_bytes())
                need(identity == dict(pid=process.pid, parent_pid=os.getpid(), mode=mode), "Direct worker identity")
                if job is not None:
                    attempt["job_accounting"] = query(k, job)
                    need(attempt["job_accounting"]["active_processes"] == 0, "Worker remains active")
                if mode == "limits":
                    attempt["result"] = json.loads((leaf / "child-result.json").read_bytes())
                    need(process.returncode == 0 and attempt["result"]["memory_rejected"]
                         and attempt["result"]["spawn"]["rejected"], "Limit fixtures failed")
                elif mode == "timeout":
                    need(process.returncode == 87, "Timeout job did not supply expected exit")
                else:
                    need(attempt["last_job_handle_closed_before_wait"]
                         and attempt["elapsed_seconds"] < 5, "Last-handle close did not promptly reap sleeping child")
            finally:
                if process is not None and process.poll() is None:
                    if job is not None:
                        k.TerminateJobObject(job, 88)
                    else:
                        process.kill()
                    process.wait(timeout=5)
                    attempt.update(reaped=True, forced_cleanup=True)
                if job is not None:
                    need(k.CloseHandle(job), "Close owned job")
        report["status"] = "passed_commit_process_limit_owned_job_termination_and_last_handle_close"
    except BaseException as error:
        report["failure"] = dict(error_class=type(error).__name__, error=str(error))
        raise
    finally:
        write_new(directory / "report.json", report)
        print(json.dumps({k: report[k] for k in ("status", "output")}))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        child(Path(sys.argv[2]), sys.argv[3])
    elif len(sys.argv) == 1:
        parent()
    else:
        raise SystemExit("No arguments for own-source OS-only parent probe")
