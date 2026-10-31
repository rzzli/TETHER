"""Pure v2 regression fixtures: files/BytesIO only, no worker or Windows API."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from threading import Event
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "probe_job_accounting_v2.py"
HELPER_SHA = "a6c91bea13a42b9c53b2c5296ff6d2bba687e34da062f1b599fc8e3ad51dff1d"
need = lambda condition, message: None if condition else (_ for _ in ()).throw(AssertionError(message))
need(sys.flags.isolated and sys.dont_write_bytecode, "Isolated no-bytecode fixture required")
need(hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA, "Helper changed")
denied = []


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "ctypes.dlopen", "socket.__new__",
                 "socket.getaddrinfo", "socket.connect"):
        denied.append(event)
        raise RuntimeError("Pure fixtures cannot dispatch, load or network")


sys.addaudithook(audit)
spec = importlib.util.spec_from_file_location("owned_accounting_v2_pure_fixture", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
output = ROOT / "data/cache" / ("r09-job-accounting-v2-pure-checks-" + str(time.time_ns()))
output.mkdir(exist_ok=False)
cases = []
partial = output / "partial"
partial.mkdir()
marker = partial / "started.json"
original_write = helper.write_new


def interrupted_write(path, value):
    payload = helper.canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(payload[:len(payload)//2])
        stream.flush()
        os.fsync(stream.fileno())
        need(not marker.exists(), "Partial marker became visible to parent")
        raise InterruptedError("Synthetic interrupted pending-file write")


helper.write_new = interrupted_write
try:
    try:
        helper.publish_marker(marker, dict(pid=1234, parent_pid=5678, note="pending-only"))
    except InterruptedError:
        pass
    else:
        raise AssertionError("Interrupted publication did not raise")
finally:
    helper.write_new = original_write
need(not marker.exists() and marker.with_name("started.json.pending").stat().st_size > 0,
     "Interrupted marker must stay unpublished with retained partial")
cases.append(dict(name="interrupted_marker_not_visible", status="passed"))

success = output / "success"
success.mkdir()
ready = success / "ready.json"
payload = dict(pid=1234, parent_pid=5678, note="complete")
helper.publish_marker(ready, payload)
need(json.loads(ready.read_bytes()) == payload and not ready.with_name("ready.json.pending").exists(),
     "Successful publication did not expose exact complete payload")
original_hash = hashlib.sha256(ready.read_bytes()).hexdigest()
try:
    helper.publish_marker(ready, dict(note="replacement forbidden"))
except RuntimeError:
    pass
else:
    raise AssertionError("Existing marker was replaced")
need(hashlib.sha256(ready.read_bytes()).hexdigest() == original_hash,
     "Existing marker bytes changed")
cases.append(dict(name="complete_atomic_marker_and_existing_destination_preserved", status="passed"))


def record():
    return dict(observed_bytes_at_least=0, retained_bytes=0, truncated=False, error_class=None)


for name, data, overflow in (("below_cap", b"small-output", False),
                             ("overflow", b"x" * (65536 + 17), True)):
    path = output / (name + ".bin")
    state, stop = record(), Event()
    with path.open("xb") as sink:
        helper.drain_capture(io.BytesIO(data), sink, state, stop)
    need(path.read_bytes() == data[:65536], "Retained bytes differ from bounded prefix")
    need(state["retained_bytes"] == path.stat().st_size <= 65536,
         "Retained-byte cap/accounting mismatch")
    need(state["observed_bytes_at_least"] == len(data) and state["truncated"] is overflow
         and stop.is_set() is overflow and state["error_class"] is None,
         "Overflow signal or measured capture accounting mismatch")
    cases.append(dict(name=name, status="passed", **state, stop_signalled=stop.is_set()))


class BrokenPipe:
    def __init__(self):
        self.calls = 0
    def read1(self, size):
        self.calls += 1
        if self.calls == 1:
            return b"abc"
        raise OSError("Synthetic capture read failure")


state, stop = record(), Event()
with (output / "read_error.bin").open("xb") as sink:
    helper.drain_capture(BrokenPipe(), sink, state, stop)
need((output / "read_error.bin").read_bytes() == b"abc" and state["retained_bytes"] == 3
     and state["observed_bytes_at_least"] == 3 and state["error_class"] == "OSError"
     and stop.is_set(), "Capture read error was not accounted/signalled")
cases.append(dict(name="read_error_signalled_with_partial_accounting", status="passed", **state))

sdk = helper.SDK / "winnt.h"
physical = sdk.read_text(encoding="utf-8").split("\n")
need(physical[13791].startswith("typedef struct _IO_COUNTERS")
     and physical[14133].startswith("typedef struct _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION")
     and physical[14604].startswith("typedef enum _JOBOBJECTINFOCLASS")
     and "JobObjectExtendedLimitInformation" in physical[14613],
     "Physical SDK landmarks or class9 line differ")
cases.append(dict(name="physical_lf_sdk_line_anchors_include_class9", status="passed",
                  sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest()))
need(denied == [], "A forbidden fixture operation was attempted")
need(hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA, "Helper changed during fixtures")
manifest = {path.relative_to(output).as_posix(): dict(bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for path in output.rglob("*") if path.is_file()}
report = dict(schema_version=1, status="passed_atomic_markers_and_capped_capture_pure_fixtures",
              helper_sha256=HELPER_SHA, fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              output=str(output), cases=cases, artifact_hashes=manifest,
              actual_children=0, network_requests=0, windows_api_calls=0, denied=denied,
              scope="Pure owned function checks only; no real pipes, threads, OS Job calls or diagnostic worker")
with (HERE / "JOB-ACCOUNTING-V2-FAULT-CHECKS.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps(dict(status=report["status"], cases=len(cases), actual_children=0,
                     network_requests=0, windows_api_calls=0)))
