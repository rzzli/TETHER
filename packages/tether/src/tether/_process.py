"""Bounded supervision of one owned child; not process-tree containment."""
from dataclasses import dataclass
import math
import os
import select
import subprocess
import time

from tether_engine.serde import ContractError, canonical

CHUNK_BYTES = 16 * 1024
POLL_SECONDS = 0.01
CLEANUP_SECONDS = 5.0
MAX_OUTPUT_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class ProcessLimits:
    timeout_seconds: float = 3600.0
    max_output_bytes: int = 16 * 1024 * 1024

    def validate(self):
        if (type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            raise ContractError("Process timeout must be a positive finite number")
        if type(self.max_output_bytes) is not int or not 1 <= self.max_output_bytes <= MAX_OUTPUT_BYTES:
            raise ContractError("Process aggregate output cap must be 1..67108864 bytes")

    def payload(self):
        self.validate()
        return dict(timeout_seconds=self.timeout_seconds, max_output_bytes=self.max_output_bytes)


@dataclass(frozen=True)
class EngineResult:
    returncode: int | None
    stdout: bytes = b""
    stderr: bytes = b""
    supervision: dict | None = None


class EngineInterrupted(KeyboardInterrupt):
    def __init__(self, result):
        super().__init__("engine interrupted; inspect the retained attempt when available")
        self.result = result


class EngineDeadlineExceeded(ContractError):
    pass


class EngineOutputLimitExceeded(ContractError):
    pass


def _read_ready(stream, maximum):
    """Return at most maximum bytes, None if not ready, b'' at EOF.

    Intended CLI use has one reader and no shared handles. On Windows we poll
    PeekNamedPipe for Python 3.11, where os.set_blocking lacks pipe support.
    Synchronous Windows handles are not universally nonblocking when embedded
    in arbitrary multithreaded applications; that context is not qualified.
    FileIO is unbuffered, so closing has no concurrent reader/buffer lock.
    """
    fd = stream.fileno()
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        peek = kernel.PeekNamedPipe
        peek.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                         ctypes.POINTER(wintypes.DWORD)]
        peek.restype = wintypes.BOOL
        available = wintypes.DWORD()
        if not peek(msvcrt.get_osfhandle(fd), None, 0, None, ctypes.byref(available), None):
            error = ctypes.get_last_error()
            if error in (109, 232):  # ERROR_BROKEN_PIPE / ERROR_NO_DATA
                return b""
            raise ctypes.WinError(error)
        if not available.value:
            return None
        maximum = min(maximum, available.value)
    elif not select.select([fd], [], [], 0)[0]:
        return None
    return os.read(fd, maximum)


def supervise_command(command, *, limits=ProcessLimits()):
    """Launch once, fairly poll both pipes, preserve the primary failure.

    Deadline covers execution and pipe EOF. OS process creation itself cannot
    be preempted here; its elapsed time is checked when Popen returns. Cleanup
    gets a separate five-second wait budget. Only the owned child is terminated.
    """
    limits.validate()
    start = time.monotonic()
    deadline = start + limits.timeout_seconds
    process = None
    buffers = [bytearray(), bytearray()]
    observed = [0, 0]
    eof = [False, False]
    errors = []
    primary = None
    reaped = False
    reason = "exited"

    def drain_once():
        progress = False
        for index, stream in enumerate((process.stdout, process.stderr)):
            if eof[index]:
                continue
            remaining = limits.max_output_bytes - sum(map(len, buffers))
            # The single extra byte proves overflow; it is counted, not retained.
            chunk = _read_ready(stream, min(CHUNK_BYTES, remaining + 1))
            if chunk is None:
                continue
            progress = True
            if not chunk:
                eof[index] = True
                continue
            observed[index] += len(chunk)
            buffers[index].extend(chunk[:remaining])
            if len(chunk) > remaining:
                raise EngineOutputLimitExceeded("Engine aggregate stdout/stderr byte limit exceeded")
        return progress

    def problem(operation, error):
        errors.append(dict(operation=operation, error_class=type(error).__name__))

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, bufsize=0)
        while True:
            if time.monotonic() >= deadline:
                raise EngineDeadlineExceeded("Engine absolute process deadline exceeded")
            progress = drain_once()
            returncode = process.poll()
            # Do not allow an exit/last chunk observed after deadline to succeed.
            if time.monotonic() >= deadline:
                raise EngineDeadlineExceeded("Engine absolute process deadline exceeded")
            if returncode is not None and all(eof):
                process.wait(timeout=0)
                reaped = True
                break
            if not progress:
                time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))
    except BaseException as error:
        primary = error
        reason = ("deadline_exceeded" if isinstance(error, EngineDeadlineExceeded)
                  else "output_limit_exceeded" if isinstance(error, EngineOutputLimitExceeded)
                  else "interrupted" if isinstance(error, KeyboardInterrupt) else "supervisor_error")
    execution_elapsed = time.monotonic() - start
    if primary is not None and process is not None:
        cleanup_deadline = time.monotonic() + CLEANUP_SECONDS
        try:
            alive = process.poll() is None
        except BaseException as error:
            problem("process_poll", error)
            alive = True
        if alive:
            try:
                process.terminate()
            except BaseException as error:
                problem("process_terminate", error)
        # Draining cannot block; stop as soon as an over-cap byte is observed.
        # Never allocate more output during cleanup than the original cap.
        def bounded_wait(until):
            drain = sum(observed) <= limits.max_output_bytes
            while time.monotonic() < until:
                if drain:
                    try:
                        drain_once()
                    except BaseException as error:
                        problem("cleanup_drain", error)
                        drain = False
                if process.poll() is not None:
                    process.wait(timeout=0)
                    return True
                time.sleep(min(POLL_SECONDS, max(0.0, until - time.monotonic())))
            return False
        try:
            reaped = bounded_wait(min(cleanup_deadline, time.monotonic() + CLEANUP_SECONDS / 2))
        except BaseException as error:
            problem("terminate_wait", error)
        if not reaped:
            try:
                process.kill()
            except BaseException as error:
                problem("process_kill", error)
            try:
                reaped = bounded_wait(cleanup_deadline)
            except BaseException as error:
                problem("kill_wait", error)
        if not reaped:
            errors.append(dict(operation="process_reap", error_class="CleanupDeadlineExceeded"))
    if process is not None:
        for name in ("stdout", "stderr"):
            try:
                getattr(process, name).close()
            except BaseException as error:
                problem("close_" + name, error)
    if primary is None and errors:
        primary = ContractError("Engine stream cleanup failed")
        reason = "supervisor_error"
    report = dict(schema_version=1, method="tether.process_envelope.v1", limits=limits.payload(),
                  termination_reason=reason, execution_elapsed_seconds=execution_elapsed,
                  total_elapsed_seconds=time.monotonic() - start,
                  retained_stdout_bytes=len(buffers[0]), retained_stderr_bytes=len(buffers[1]),
                  observed_stdout_bytes=observed[0], observed_stderr_bytes=observed[1],
                  observed_counts_are_lower_bounds=not all(eof), pipe_eof=dict(stdout=eof[0], stderr=eof[1]),
                  process_started=process is not None, process_reaped=reaped, cleanup_errors=errors)
    result = EngineResult(process.returncode if process is not None else None,
                          bytes(buffers[0]), bytes(buffers[1]), report)
    if primary is not None:
        retained = EngineInterrupted(result) if isinstance(primary, KeyboardInterrupt) else primary
        retained.tether_engine_result = result
        retained.tether_cleanup_errors = errors
        retained.tether_process_reaped = reaped
        if retained is not primary:
            raise retained from primary
        raise retained
    return result


def validate_success_report(report, limits, stdout_bytes, stderr_bytes):
    """Validate the bounded success declaration against retained stream sizes."""
    limits.validate()
    keys = {"schema_version", "method", "limits", "termination_reason", "execution_elapsed_seconds",
            "total_elapsed_seconds", "retained_stdout_bytes", "retained_stderr_bytes", "observed_stdout_bytes",
            "observed_stderr_bytes", "observed_counts_are_lower_bounds", "pipe_eof", "process_started",
            "process_reaped", "cleanup_errors"}
    if (type(report) is not dict or set(report) != keys or type(report["schema_version"]) is not int
            or report["schema_version"] != 1 or report["method"] != "tether.process_envelope.v1"
            or canonical(report["limits"]) != canonical(limits.payload()) or report["termination_reason"] != "exited"
            or report["process_started"] is not True or report["process_reaped"] is not True
            or report["observed_counts_are_lower_bounds"] is not False
            or type(report["pipe_eof"]) is not dict or set(report["pipe_eof"]) != {"stdout", "stderr"}
            or any(value is not True for value in report["pipe_eof"].values()) or report["cleanup_errors"] != []):
        raise ContractError("TETHER successful process supervision declaration differs")
    for key in ("execution_elapsed_seconds", "total_elapsed_seconds"):
        if type(report[key]) not in (int, float) or not math.isfinite(report[key]) or report[key] < 0:
            raise ContractError("TETHER process timing is invalid")
    if not report["execution_elapsed_seconds"] < limits.timeout_seconds:
        raise ContractError("TETHER successful process exceeded its deadline")
    if report["total_elapsed_seconds"] < report["execution_elapsed_seconds"]:
        raise ContractError("TETHER process timing order differs")
    for name, expected in (("stdout", stdout_bytes), ("stderr", stderr_bytes)):
        for prefix in ("retained", "observed"):
            value = report[prefix + "_" + name + "_bytes"]
            if type(value) is not int or value != expected:
                raise ContractError("TETHER process stream accounting differs")
    if stdout_bytes + stderr_bytes > limits.max_output_bytes:
        raise ContractError("TETHER retained streams exceed aggregate process byte bound")
