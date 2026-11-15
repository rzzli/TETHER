"""Owned Windows process-tree controller for trusted local execution.

Uses a suspended initial thread and a non-breakaway kill-on-close Job Object.
Only handles obtained for the Popen instance created here are controlled.
"""
from __future__ import annotations
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import math
import os
import subprocess
import time

_SYSTEM_POPEN = subprocess.Popen


def process_tree_for(factory, *, monotonic=time.monotonic, sleep=time.sleep):
    """Contain the native Windows launcher; injected factories own their lifecycle.

    Trusted test/process factories and non-Windows execution retain the existing
    single-child semantics. No recorded request can choose this factory.
    """
    return WindowsJob(monotonic=monotonic, sleep=sleep) if os.name == 'nt' and factory is _SYSTEM_POPEN else None


class WindowsJob:
    def __init__(self, *, monotonic=time.monotonic, sleep=time.sleep):
        if os.name != 'nt':
            raise OSError('Windows Job Objects require Windows')
        self._kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self._handle = None
        self.process = None
        self._attached = False
        self.cleanup_deadline = None
        self.monotonic, self.sleep = monotonic, sleep
        def api(name, args, result):
            fn = getattr(self._kernel, name)
            fn.argtypes, fn.restype = args, result
            return fn
        self._close = api('CloseHandle', [wintypes.HANDLE], wintypes.BOOL)
        self._create = api('CreateJobObjectW', [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE)
        self._set_info = api('SetInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL)
        self._assign = api('AssignProcessToJobObject', [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL)
        self._terminate = api('TerminateJobObject', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL)
        self._query = api('QueryInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL)
        self._snapshot = api('CreateToolhelp32Snapshot', [wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE)
        self._open_thread = api('OpenThread', [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE)
        self._thread_owner = api('GetProcessIdOfThread', [wintypes.HANDLE], wintypes.DWORD)
        self._resume = api('ResumeThread', [wintypes.HANDLE], wintypes.DWORD)

        class Limits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                ('active_limit', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Limits), ('io', ctypes.c_ulonglong * 6),
                ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]
        class Accounting(ctypes.Structure):
            _fields_ = [('user', ctypes.c_longlong), ('kernel', ctypes.c_longlong),
                ('period_user', ctypes.c_longlong), ('period_kernel', ctypes.c_longlong),
                ('faults', wintypes.DWORD), ('total', wintypes.DWORD),
                ('active', wintypes.DWORD), ('terminated', wintypes.DWORD)]
        class Thread(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('uses', wintypes.DWORD),
                ('tid', wintypes.DWORD), ('pid', wintypes.DWORD),
                ('priority', wintypes.LONG), ('delta', wintypes.LONG), ('flags', wintypes.DWORD)]
        self._accounting_type, self._thread_type = Accounting, Thread
        self._first_thread = api('Thread32First', [wintypes.HANDLE, ctypes.POINTER(Thread)], wintypes.BOOL)
        self._next_thread = api('Thread32Next', [wintypes.HANDLE, ctypes.POINTER(Thread)], wintypes.BOOL)
        self._handle = self._create(None, None)
        self._need(self._handle)
        try:
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway flags.
            self._need(self._set_info(self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException as primary:
            try:
                self.close()
            except BaseException as error:
                primary.add_note('Job initialization cleanup: ' + type(error).__name__)
            raise

    @staticmethod
    def _need(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def _deadline(self, deadline):
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Absolute process-tree deadline required')
        if self.monotonic() >= deadline:
            raise TimeoutError('Process-tree deadline expired')

    @contextmanager
    def _held(self, handle):
        try:
            yield handle
        except BaseException as primary:
            try:
                self._need(self._close(handle))
            except BaseException as error:
                primary.add_note('Process-tree handle close: ' + type(error).__name__)
            raise
        else:
            self._need(self._close(handle))

    def _resume_initial_thread(self, deadline):
        snapshot = self._snapshot(4, 0)  # TH32CS_SNAPTHREAD
        if not snapshot or snapshot == ctypes.c_void_p(-1).value:
            self._need(False)
        with self._held(snapshot):
            entry = self._thread_type()
            entry.size = ctypes.sizeof(entry)
            available = self._first_thread(snapshot, ctypes.byref(entry))
            while available:
                self._deadline(deadline)
                if entry.pid == self.process.pid:
                    handle = self._open_thread(0x0802, False, entry.tid)
                    self._need(handle)
                    with self._held(handle):
                        if self._thread_owner(handle) != self.process.pid:
                            raise OSError('Initial thread owner differs')
                        count = self._resume(handle)
                        if count == 0xFFFFFFFF:
                            self._need(False)
                        if count != 1:
                            raise OSError('Unexpected initial thread suspension state')
                        return
                available = self._next_thread(snapshot, ctypes.byref(entry))
            raise OSError('Owned suspended process has no initial thread')

    def launch(self, command, *, deadline, **kwargs):
        self._deadline(deadline)
        if self.process is not None or self._handle is None:
            raise RuntimeError('Process-tree controller is one-use')
        flags = kwargs.pop('creationflags', 0)
        if flags & 0x01000000:  # CREATE_BREAKAWAY_FROM_JOB
            raise ValueError('Process-tree breakaway is forbidden')
        try:
            self.process = subprocess.Popen(command, creationflags=flags | 0x08000004, **kwargs)
            self._deadline(deadline)
            # CPython Windows Popen retains this owned process handle. Never look
            # up a process by port/name or pass a caller-supplied PID to assignment.
            self._need(self._assign(self._handle, int(self.process._handle)))
            self._attached = True
            self._resume_initial_thread(deadline)
            return self.process
        except BaseException as primary:
            try:
                self.cleanup_deadline = self.monotonic() + 5
            except BaseException as error:
                primary.add_note('Process-tree cleanup clock: ' + type(error).__name__)
            for action in (self.terminate, self.close):
                try:
                    action()
                except BaseException as error:
                    primary.add_note('Process-tree launch cleanup: ' + type(error).__name__)
            if self.process is not None:
                try:
                    timeout = 5 if self.cleanup_deadline is None else max(0, self.cleanup_deadline-self.monotonic())
                    self.process.wait(timeout=timeout)
                except BaseException as error:
                    primary.add_note('Process-tree launch reaping: ' + type(error).__name__)
            raise

    def active_processes(self):
        if self._handle is None:
            raise RuntimeError('Job handle is closed')
        info = self._accounting_type()
        self._need(self._query(self._handle, 1, ctypes.byref(info), ctypes.sizeof(info), None))
        return info.active

    @property
    def closed(self):
        return self._handle is None

    def terminate(self):
        if self._attached and self._handle is not None:
            self._need(self._terminate(self._handle, 1))
        elif self.process is not None and self.process.poll() is None:
            self.process.kill()  # Owned suspended process, assignment never completed.

    def finish(self, deadline):
        """Stop any remaining job members and confirm zero active processes."""
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Absolute process-tree cleanup deadline required')
        if self.cleanup_deadline is not None:
            deadline = min(deadline, self.cleanup_deadline)
        self.cleanup_deadline = deadline
        if self.closed:
            return
        primary = None
        try:
            if self.active_processes():
                self.terminate()
            while self.active_processes():
                self._deadline(deadline)
                self.sleep(min(.01, max(0, deadline-self.monotonic())))
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                self.close()
            except BaseException as error:
                if primary is None:
                    raise
                primary.add_note('Process-tree final close: ' + type(error).__name__)

    def close(self):
        if self._handle is not None:
            self._need(self._close(self._handle))
            self._handle = None
