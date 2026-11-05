"""Native computation accounting and audited IO for trusted SciFact workers.

The Python audit hook and polling watchdog are not a hostile-code or OS sandbox.
The parent additionally uses the qualified TETHER child deadline/output wrapper.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

from asof.serde import ContractError, canonical


def memory_bytes():
    if os.name != "nt":
        return None, None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
            "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    api.restype = wintypes.BOOL
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if not api(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        return None, None
    return int(value.WorkingSetSize), int(value.PeakWorkingSetSize)


def measured(started, cpu_started, *, input_bytes, output_bytes, examples):
    _, peak = memory_bytes()
    return {"wall_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started,
            "peak_memory_bytes": peak, "memory_method": "windows_process_lifetime_peak" if peak is not None else "unavailable",
            "input_bytes": input_bytes, "output_bytes": output_bytes, "examples": examples,
            "model_input_tokens": None, "model_output_tokens": None, "tokenizer_identity": None,
            "provider_usage": None, "token_usage_reason": "not_applicable_non_llm", "provider_cost_usd": 0}


class IOAudit:
    """Install once in an owned worker; log managed-Python file opens and denials."""
    def __init__(self, allowed_inputs, output, code_roots):
        self.inputs = {str(Path(p).resolve()).casefold() for p in allowed_inputs}
        self.output = Path(output).resolve()
        self.code_roots = tuple(Path(p).resolve() for p in code_roots)
        self.events = []
        self.reentrant = threading.local()
        self.stream = (self.output / "io-audit.jsonl").open("xb", buffering=0)

    def hook(self, event, args):
        if event != "open" or getattr(self.reentrant, "busy", False):
            return
        self.reentrant.busy = True
        try:
            name, mode, flags = args
            if isinstance(name, int):
                # Descriptor opens are recorded but do not establish a new path grant.
                record = {"path": None, "descriptor": name, "mode": mode, "flags": flags,
                          "allowed": True, "basis": "existing_descriptor"}
            else:
                path = Path(os.fsdecode(name)).resolve()
                write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                output_path = path.is_relative_to(self.output)
                allowed = output_path or (not write and (
                    str(path).casefold() in self.inputs or
                    any(path.is_relative_to(root) for root in self.code_roots)))
                record = {"path": str(path), "mode": mode, "flags": flags, "allowed": allowed,
                          "basis": "output" if output_path else "declared_input_or_runtime" if allowed else "denied"}
            self.stream.write(canonical(record) + b"\n")
            self.events.append(record)
            if not record["allowed"]:
                os.fsync(self.stream.fileno())
                raise PermissionError("Native worker denies undeclared input or output: " + record["path"])
        finally:
            self.reentrant.busy = False

    def activate(self):
        sys.addaudithook(self.hook)

    def flush(self):
        self.stream.flush()
        os.fsync(self.stream.fileno())


class Watchdog:
    """Polling guard for this worker; abrupt exits deliberately preserve unresolved calls."""
    def __init__(self, output, *, memory_limit=8 * 1024**3, sample_seconds=0.5, call_seconds=60):
        self.output = Path(output)
        self.memory_limit, self.sample_seconds, self.call_seconds = memory_limit, sample_seconds, call_seconds
        self.active_started = None
        self.stop = threading.Event()
        self.peak_sample = 0
        self.samples = 0
        self.thread = threading.Thread(target=self._poll, daemon=True)

    def _poll(self):
        while not self.stop.wait(self.sample_seconds):
            current, _ = memory_bytes()
            self.samples += 1
            if current is not None:
                self.peak_sample = max(self.peak_sample, current)
            elapsed = None if self.active_started is None else time.perf_counter() - self.active_started
            reason = "memory_limit_observed" if current is not None and current > self.memory_limit else (
                "call_deadline_observed" if elapsed is not None and elapsed > self.call_seconds else None)
            if reason:
                with (self.output / "WATCHDOG-STOP.json").open("x", encoding="utf-8") as f:
                    json.dump({"reason": reason, "current_working_set_bytes": current,
                               "active_elapsed_seconds": elapsed, "sampling_seconds": self.sample_seconds,
                               "enforcement": "trusted_worker_poll_not_kernel_limit"}, f)
                    f.flush()
                    os.fsync(f.fileno())
                os._exit(124 if reason == "call_deadline_observed" else 125)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *unused):
        self.stop.set()
        self.thread.join(timeout=2)


def load_input(proof):
    path = Path(proof["path"])
    if not path.is_file() or path.is_symlink() or path.stat().st_size != proof["bytes"]:
        raise ContractError("Native worker input size/path differs")
    with path.open("rb") as f:
        raw = f.read(proof["bytes"] + 1)
    if len(raw) != proof["bytes"] or hashlib.sha256(raw).hexdigest() != proof["sha256"]:
        raise ContractError("Native worker input binding differs")
    return raw
