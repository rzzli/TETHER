"""Bounded native-worker utilities for the isolated LAB-Bench experiment.

Windows job containment is qualified separately from ordinary process limits.
Python file auditing is a trusted-code access log, not an OS security sandbox.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import sys
import threading
import time

from tether_engine.serde import ContractError, canonical


def need(condition, message):
    if not condition:
        raise ContractError(message)


def empty_import_cache(*, expected=None, cache_root=None):
    need(sys.dont_write_bytecode and sys.flags.isolated == 1 and isinstance(sys.pycache_prefix,str)
         and sys.pycache_prefix, "Worker requires -I -B -X pycache_prefix=<fresh empty path>")
    path=Path(sys.pycache_prefix).resolve()
    if cache_root is not None:
        need(path.is_relative_to(Path(cache_root).resolve()), "Import cache prefix outside authorized cache root")
    if expected is not None:
        need(path == Path(expected).resolve(), "Worker import cache prefix differs")
    path.mkdir(parents=True,exist_ok=True)
    need(not any(path.iterdir()), "Import cache prefix is not empty")
    return path


def contain_process_tree():
    """Assign this worker to a non-inheritable kill-on-close Windows job.

    Keep the returned handle open until process exit. Closing it manually kills
    this worker too. Assignment failure must block all child process launches.
    """
    need(os.name == "nt", "Native process containment requires Windows")
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p,w.LPCWSTR]; api.CreateJobObjectW.restype=w.HANDLE
    api.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];api.SetInformationJobObject.restype=w.BOOL
    api.GetCurrentProcess.restype=w.HANDLE
    api.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];api.AssignProcessToJobObject.restype=w.BOOL
    api.SetHandleInformation.argtypes=[w.HANDLE,w.DWORD,w.DWORD];api.SetHandleInformation.restype=w.BOOL
    api.CloseHandle.argtypes=[w.HANDLE];api.CloseHandle.restype=w.BOOL
    handle=api.CreateJobObjectW(None,None)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    value=Extended();value.BasicLimitInformation.LimitFlags=0x2000
    assigned=False
    try:
        if not api.SetHandleInformation(handle,1,0): raise ctypes.WinError(ctypes.get_last_error())
        if not api.SetInformationJobObject(handle,9,ctypes.byref(value),ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not api.AssignProcessToJobObject(handle,api.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
        assigned=True
    finally:
        if not assigned: api.CloseHandle(handle)
    return handle


def process_sample(pid):
    if os.name != "nt": return None
    from ctypes import wintypes as w
    class Memory(ctypes.Structure):
        _fields_=[("cb",w.DWORD),("PageFaultCount",w.DWORD)]+[(name,ctypes.c_size_t) for name in
            ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage",
             "QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
    api=ctypes.WinDLL("kernel32",use_last_error=True)
    api.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];api.OpenProcess.restype=w.HANDLE
    api.CloseHandle.argtypes=[w.HANDLE]
    api.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];api.GetProcessTimes.restype=w.BOOL
    memapi=ctypes.WinDLL("psapi",use_last_error=True).GetProcessMemoryInfo
    memapi.argtypes=[w.HANDLE,ctypes.POINTER(Memory),w.DWORD];memapi.restype=w.BOOL
    handle=api.OpenProcess(0x0410,False,pid)
    if not handle:return None
    try:
        value=Memory();value.cb=ctypes.sizeof(value)
        memory_ok=memapi(handle,ctypes.byref(value),value.cb)
        created,ended,kernel,user=(w.FILETIME() for _ in range(4))
        time_ok=api.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
        ticks=lambda f:(f.dwHighDateTime<<32)+f.dwLowDateTime
        return dict(working_set_bytes=int(value.WorkingSetSize) if memory_ok else None,
                    process_peak_working_set_bytes=int(value.PeakWorkingSetSize) if memory_ok else None,
                    cpu_seconds=(ticks(kernel)+ticks(user))/10**7 if time_ok else None)
    finally:api.CloseHandle(handle)


class ProcessSamples:
    """Sample observed CPU/RAM; unknown measurements stay null, not zero."""
    def __init__(self,pid,interval=.5):
        self.pid,self.interval,self.values=pid,interval,[]
        self.stop=threading.Event();self.thread=threading.Thread(target=self.poll,daemon=True)
    def capture(self):
        try:value,error=process_sample(self.pid),None
        except Exception as exc:value,error=None,type(exc).__name__
        self.values.append(dict(monotonic=time.monotonic(),value=value,error_class=error))
    def poll(self):
        while not self.stop.wait(self.interval):self.capture()
    def __enter__(self):self.capture();self.thread.start();return self
    def __exit__(self,*unused):self.capture();self.stop.set();self.thread.join(2)


class InputAudit:
    """One-way Python open audit; only exact granted data or runtime roots allowed."""
    def __init__(self,*,inputs,output,code_roots):
        self.inputs={str(Path(p).resolve()).casefold() for p in inputs}
        self.output=Path(output).resolve();self.code_roots=tuple(Path(p).resolve() for p in code_roots)
        self.local=threading.local();self.denials=0;self.opens=0
        self.stream=(self.output/"io-audit.jsonl").open("xb",buffering=0)
    def hook(self,event,args):
        if event!="open" or getattr(self.local,"busy",False):return
        self.local.busy=True
        try:
            name,mode,flags=args
            if isinstance(name,int):
                record=dict(path=None,descriptor=name,mode=mode,flags=flags,allowed=True,basis="existing_descriptor")
            else:
                path=Path(os.fsdecode(name)).resolve()
                write=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
                out=path.is_relative_to(self.output)
                allowed=out or (not write and (str(path).casefold() in self.inputs or
                            any(path.is_relative_to(root) for root in self.code_roots)))
                record=dict(path=str(path),mode=mode,flags=flags,allowed=allowed,
                            basis="output" if out else "explicit_data_or_runtime" if allowed else "denied")
            self.stream.write(canonical(record)+b"\n");self.opens+=1
            if not record["allowed"]:
                self.denials+=1;os.fsync(self.stream.fileno())
                raise PermissionError("Native generation denied undeclared file: "+record["path"])
        finally:self.local.busy=False
    def activate(self):sys.addaudithook(self.hook)
    def flush(self):self.stream.flush();os.fsync(self.stream.fileno())


class DeadlineWatchdog:
    """Best-effort durable timeout marker followed by immediate process exit.

    Call contain_process_tree before entering: process exit then terminates owned
    children too. A supervising parent supplies an independent hard deadline.
    Marker writes can fail; that must never suppress the terminating exit.
    """
    def __init__(self,deadline,marker,*,poll_seconds=.025,exit_code=124):
        import math
        need(type(deadline) in (int,float) and math.isfinite(deadline),"Invalid watchdog deadline")
        need(type(poll_seconds) in (int,float) and 0<poll_seconds<=1,"Invalid watchdog polling period")
        need(type(exit_code) is int and 1<=exit_code<=255,"Invalid watchdog exit code")
        self.deadline,self.marker,self.poll_seconds,self.exit_code=deadline,Path(marker),poll_seconds,exit_code
        self.stop=threading.Event();self.thread=threading.Thread(target=self.poll,daemon=True)
    def expire(self):
        from datetime import datetime,timezone
        try:
            self.marker.parent.mkdir(parents=True,exist_ok=True)
            payload=canonical({"status":"deadline_exceeded","owner_pid":os.getpid(),
                "deadline_monotonic":self.deadline,"observed_monotonic":time.monotonic(),
                "observed_at_utc":datetime.now(timezone.utc).isoformat(),"exit_code":self.exit_code})+b"\n"
            with self.marker.open("xb") as stream:
                stream.write(payload);stream.flush();os.fsync(stream.fileno())
        except BaseException:
            pass
        finally:
            os._exit(self.exit_code)
    def poll(self):
        while not self.stop.wait(max(0.0,min(self.poll_seconds,self.deadline-time.monotonic()))):
            if time.monotonic()>=self.deadline:self.expire()
    def __enter__(self):
        if time.monotonic()>=self.deadline:self.expire()
        self.thread.start();return self
    def __exit__(self,*unused):
        if time.monotonic()>=self.deadline:self.expire()
        self.stop.set();self.thread.join(2)
