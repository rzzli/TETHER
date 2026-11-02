"""Adversarial Windows replacement controls; invented files, no providers."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ctypes
from ctypes import wintypes
import errno
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import sys
from threading import Barrier, Event, Thread, current_thread
import time
import traceback
from unittest.mock import patch

from asof import atomic, serde

ROOT = Path(__file__).resolve().parents[5]
EXPECTED_SERDE = "fa910ce74c0766240eac3a64443b4b4baf7b6b64b064a1b028cda4ace66eb79c"
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                              wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL
INVALID = ctypes.c_void_p(-1).value
REAL_SLEEP, REAL_REPLACE = time.sleep, os.replace


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def open_handle(path, share_delete=False):
    handle = kernel.CreateFileW(str(path), 0x80000000, 3 | (4 if share_delete else 0), None, 3, 128, None)
    if handle == INVALID:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def close_handle(handle):
    if not kernel.CloseHandle(handle):
        raise ctypes.WinError(ctypes.get_last_error())


def observed_replace(calls, callback=None):
    def operation(source, target):
        entry = dict(source=str(source), sha256=sha(source))
        calls.append(entry)
        try:
            REAL_REPLACE(source, target)
        except OSError as error:
            entry["winerror"] = getattr(error, "winerror", None)
            if callback:
                callback(error)
            raise
        entry["success"] = True
    return operation


def released_handle(root):
    target = root / "target.json"
    write(target, {"old": True})
    handle = open_handle(target)
    failed, released = Event(), Event()
    close_errors, calls = [], []
    value = {"payload": ["before-first-attempt"]}
    expected = serde.canonical(value)
    def on_failure(error):
        value["payload"].append("mutation-after-serialization")
        failed.set()
    def release():
        try:
            failed.wait(timeout=2)
            REAL_SLEEP(0.015)
            close_handle(handle)
        except BaseException as error:
            close_errors.append(str(error))
        finally:
            released.set()
    thread = Thread(target=release)
    thread.start()
    started = time.monotonic()
    try:
        with patch.object(serde.os, "replace", observed_replace(calls, on_failure)):
            serde.write_json(target, value, compact=True)
    finally:
        thread.join(timeout=3)
    assert released.is_set() and not close_errors and not thread.is_alive()
    assert 2 <= len(calls) <= 3 and calls[0]["winerror"] in (5, 32, 33) and calls[-1]["success"]
    assert len({c["source"] for c in calls}) == len({c["sha256"] for c in calls}) == 1
    assert target.read_bytes() == expected and not list(root.glob(".writing-*"))
    return dict(attempts=calls, seconds=time.monotonic()-started,
                same_staged_bytes=True, caller_mutation_not_reserialized=True)


def persistent_handle(root):
    target = root / "target.json"
    write(target, {"old": True})
    original = target.read_bytes()
    handle = open_handle(target)
    calls, sleeps = [], []
    def sleep(delay):
        sleeps.append(delay)
        REAL_SLEEP(delay)
    started = time.monotonic()
    try:
        with patch.object(serde.os, "replace", observed_replace(calls)), patch.object(serde.time, "sleep", sleep):
            try:
                serde.write_json(target, {"new": True})
            except OSError as error:
                failure = dict(type=type(error).__name__, winerror=error.winerror, notes=getattr(error, "__notes__", []))
            else:
                raise AssertionError("Persistent denied-delete handle unexpectedly replaced")
    finally:
        close_handle(handle)
    assert len(calls) == 3 and sleeps == [0.05, 0.1]
    assert target.read_bytes() == original and not list(root.glob(".writing-*"))
    assert len({c["source"] for c in calls}) == len({c["sha256"] for c in calls}) == 1
    return dict(attempts=calls, sleeps=sleeps, failure=failure, seconds=time.monotonic()-started,
                destination_unchanged=True)


def noneligible_and_interrupt(root):
    cases = []
    for name, error in (("native2", ctypes.WinError(2)), ("native87", ctypes.WinError(87)),
                        ("errno_without_native", PermissionError(errno.EACCES, "no native code")),
                        ("interrupt", KeyboardInterrupt("fictional interrupt"))):
        target = root / (name + ".json")
        write(target, {"old": True})
        before = target.read_bytes()
        with patch.object(serde.os, "replace", side_effect=error) as replace, patch.object(serde.time, "sleep") as sleep:
            try:
                serde.write_json(target, {"new": True})
            except BaseException as captured:
                assert captured is error
            else:
                raise AssertionError(name + " did not fail")
        assert replace.call_count == 1 and sleep.call_count == 0 and target.read_bytes() == before
        cases.append(dict(name=name, replace_calls=replace.call_count, sleeps=sleep.call_count))
    target = root / "sleep-interrupt.json"
    write(target, {"old": True})
    interrupt = KeyboardInterrupt("during bounded backoff")
    with patch.object(serde.os, "replace", side_effect=ctypes.WinError(5)) as replace, \
            patch.object(serde.time, "sleep", side_effect=interrupt) as sleep:
        try:
            serde.write_json(target, {"new": True})
        except KeyboardInterrupt as captured:
            assert captured is interrupt
        else:
            raise AssertionError("Sleep interruption was swallowed")
    assert replace.call_count == sleep.call_count == 1 and json.loads(target.read_bytes()) == {"old": True}
    cases.append(dict(name="sleep-interrupt", replace_calls=1, sleeps=1))
    target = root / "non-windows-mode.json"
    write(target, {"old": True})
    with patch.object(serde, "_WINDOWS_REPLACE_RETRY", False), \
            patch.object(serde.os, "replace", side_effect=ctypes.WinError(5)) as replace, \
            patch.object(serde.time, "sleep") as sleep:
        try:
            serde.write_json(target, {"new": True})
        except OSError:
            pass
    assert replace.call_count == 1 and sleep.call_count == 0
    cases.append(dict(name="non-windows-flag-control", replace_calls=1, sleeps=0))
    assert not list(root.glob(".writing-*"))
    return dict(cases=cases)


def cleanup_preserves_primary(root):
    rows = []
    for name, primary in (("io", OSError(errno.EIO, "primary io")), ("interrupt", KeyboardInterrupt("primary interrupt"))):
        target = root / (name + ".json")
        write(target, {"old": True})
        cleanup = PermissionError(errno.EACCES, "fictional cleanup denial")
        with patch.object(serde.os, "replace", side_effect=primary) as replace, \
                patch.object(Path, "unlink", side_effect=cleanup):
            try:
                serde.write_json(target, {"new": True})
            except BaseException as error:
                assert error is primary
            else:
                raise AssertionError("Primary was lost")
        assert replace.call_count == 1 and json.loads(target.read_bytes()) == {"old": True}
        assert any("cleanup failed" in note for note in primary.__notes__)
        rows.append(dict(name=name, primary_preserved=True, notes=primary.__notes__))
    return dict(cases=rows, intentional_retained_staging=[str(p) for p in root.glob(".writing-*")])


def no_clobber_unchanged(root):
    target = root / "immutable.json"
    write(target, {"keep": True})
    before = target.read_bytes()
    real_rename = os.rename
    with patch.object(atomic.os, "rename", wraps=real_rename) as rename, \
            patch.object(serde.os, "replace", side_effect=AssertionError("Mutable replacement reached")) as replace, \
            patch.object(serde.time, "sleep") as sleep:
        try:
            atomic.publish_bytes(target, b'{"unexpected":true}')
        except OSError:
            pass
        else:
            raise AssertionError("No-clobber publication overwrote input")
    assert rename.call_count == 1 and replace.call_count == sleep.call_count == 0
    assert target.read_bytes() == before and not list(root.glob(".publishing-*"))
    return dict(rename_calls=1, replace_calls=0, sleeps=0, destination_unchanged=True)


def concurrent_complete_json(root):
    target = root / "shared.json"
    initial = {"writer": -1, "sequence": -1, "payload": "initial"}
    write(target, initial)
    documents = [{"writer": writer, "sequence": sequence, "payload": str(writer) * 4096}
                 for writer in range(4) for sequence in range(4)]
    expected = {json.dumps(value, sort_keys=True) for value in [initial, *documents]}
    barrier, observations = Barrier(5), []
    def writer(index):
        barrier.wait()
        for value in documents[index*4:index*4+4]:
            serde.write_json(target, value)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(writer, i) for i in range(4)]
        barrier.wait()
        while not all(f.done() for f in futures):
            handle = open_handle(target, share_delete=True)
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            with os.fdopen(descriptor, "rb") as stream:
                document = json.loads(stream.read())
            assert json.dumps(document, sort_keys=True) in expected
            observations.append((document["writer"], document["sequence"]))
            REAL_SLEEP(0.001)
        for future in futures:
            future.result()
    assert json.dumps(json.loads(target.read_bytes()), sort_keys=True) in expected
    assert not list(root.glob(".writing-*"))
    return dict(writers=4, completed_writes=16, observed_complete_documents=len(observations),
                observations=observations, semantics="Atomic mutable replacement; no version-order guarantee")


def stale_writer_semantics(root):
    target = root / "mutable.json"
    write(target, {"generation": 0})
    old_blocked, new_committed = Event(), Event()
    attempts, errors = [], []
    first = True
    def replace(source, destination):
        nonlocal first
        attempts.append(current_thread().name)
        if current_thread().name == "older-writer" and first:
            first = False
            old_blocked.set()
            raise ctypes.WinError(5)
        return REAL_REPLACE(source, destination)
    def sleep(delay):
        assert new_committed.wait(timeout=2)
        REAL_SLEEP(delay)
    def older():
        try:
            serde.write_json(target, {"generation": 1})
        except BaseException as error:
            errors.append(str(error))
    with patch.object(serde.os, "replace", replace), patch.object(serde.time, "sleep", sleep):
        thread = Thread(target=older, name="older-writer")
        thread.start()
        assert old_blocked.wait(timeout=2)
        serde.write_json(target, {"generation": 2})
        observed_new = json.loads(target.read_bytes())
        new_committed.set()
        thread.join(timeout=3)
    assert not errors and not thread.is_alive() and observed_new == {"generation": 2}
    assert json.loads(target.read_bytes()) == {"generation": 1}
    return dict(attempt_order=attempts, observed_new_generation=2, final_generation=1,
                classification="Existing last-writer-wins semantics; retry is not compare-and-swap or version ordering")


def main():
    assert os.name == "nt" and sha(Path(serde.__file__)) == EXPECTED_SERDE
    root = Path(sys.argv[1]).absolute()
    assert root.is_relative_to(ROOT / "data/cache")
    root.mkdir(parents=True, exist_ok=False)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in (Path(serde.__file__), Path(atomic.__file__), ROOT / "src/asof/maintenance.py")}
    start = dict(source_pins=pins, interpreter=sys.executable, script_sha256=sha(Path(__file__)),
                 scope="Invented local files; real Windows sharing controls plus labeled injected errors; no provider or model")
    write(root / "START.json", start)
    records = []
    for check in (released_handle, persistent_handle, noneligible_and_interrupt, cleanup_preserves_primary,
                  no_clobber_unchanged, concurrent_complete_json, stale_writer_semantics):
        leaf = root / check.__name__
        leaf.mkdir()
        try:
            result = dict(name=check.__name__, status="PASS", details=check(leaf))
        except BaseException as error:
            result = dict(name=check.__name__, status="FAILED", type=type(error).__name__, message=str(error),
                          traceback=traceback.format_exc())
        write(root / (check.__name__ + ".json"), result)
        records.append(result)
        if result["status"] != "PASS":
            break
    assert pins == {p:sha(ROOT/p) for p in pins}, "Reviewed sources changed"
    result = dict(status="PASS" if len(records)==7 and all(r["status"]=="PASS" for r in records) else "FAILED",
                  start=start, controls=records, source_stability="verified",
                  limits="No diagnosis of the full-gate WinError5 cause; no hard wall-time bound or stale-writer ordering guarantee")
    write(root / "RESULTS.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
