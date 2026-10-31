"""Focused pure metadata/ownership vectors; never imports a native launcher.

Only the query method and Observer class AST are extracted from the diagnostic.
All API objects, deadline hooks and publication failures are Python fakes.
"""
import ast
import copy
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import types
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "diagnose_native_job_iocp_v1.py"
OUTPUT = HERE / "IOCP-METADATA-ADVERSARIAL-PROOF-v1.json"
RAW = SOURCE.read_bytes()
SOURCE_SHA = hashlib.sha256(RAW).hexdigest()
TREE = ast.parse(RAW.decode("utf-8"))
QUERY = next(n for n in ast.walk(TREE)
             if isinstance(n, ast.FunctionDef) and n.name == "query_reported")
OBSERVER = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "Observer")
QUERY_ORDER = ["GetProcessId", "QueryFullProcessImageNameW", "IsProcessInJob_exact_job",
               "WaitForSingleObject_0", "GetProcessTimes"]
DENIED = []


def guard(event, args):
    if event == "ctypes.dlopen" or event == "subprocess.Popen" or event == "os.system" or event.startswith("socket."):
        DENIED.append(event)
        raise AssertionError("No real API, child or network is permitted: " + event)


sys.addaudithook(guard)


class FILETIME(C.Structure):
    _fields_ = [("low", C.c_uint32), ("high", C.c_uint32)]


class FakeC:
    """Typed buffers/pointers with fake last-error storage; no DLL access."""
    def __init__(self):
        self.error = 0

    def set_last_error(self, value):
        self.error = value

    def get_last_error(self):
        return self.error

    byref = staticmethod(C.byref)
    create_unicode_buffer = staticmethod(C.create_unicode_buffer)


class Deadline:
    def __init__(self, fail_at=None):
        self.calls = 0
        self.fail_at = fail_at

    def __call__(self, deadline):
        self.calls += 1
        if self.calls == self.fail_at:
            raise TimeoutError("Synthetic finite-query deadline")


class FakeK:
    def __init__(self, ffi, *, returned_pid=42, wait=0, failure=None,
                 image_length=None, image_surrogate=False, member=True, explode=None):
        self.ffi, self.returned_pid, self.wait = ffi, returned_pid, wait
        self.failure, self.image_length, self.image_surrogate = failure, image_length, image_surrogate
        self.member, self.explode, self.calls = member, explode, []

    def hit(self, name):
        self.calls.append(name)
        if self.explode == name:
            raise OSError("Synthetic query exception")
        if self.failure == name:
            self.ffi.error = 5
            return False
        return True

    def GetProcessId(self, handle):
        return self.returned_pid if self.hit("GetProcessId") else 0

    def QueryFullProcessImageNameW(self, handle, flags, buffer, size):
        assert flags == 0 and size._obj.value == 32768
        ok = self.hit("QueryFullProcessImageNameW")
        image = "\ud800" if self.image_surrogate else r"D:\synthetic\only-a-path-string.exe"
        for i, char in enumerate(image):
            buffer[i] = char
        size._obj.value = len(image) if self.image_length is None else self.image_length
        return int(ok)

    def IsProcessInJob(self, handle, job, answer):
        answer._obj.value = int(self.member)
        return int(self.hit("IsProcessInJob_exact_job"))

    def WaitForSingleObject(self, handle, timeout):
        assert timeout == 0
        ok = self.hit("WaitForSingleObject_0")
        if not ok or self.wait == 0xffffffff:
            self.ffi.error = 6
            return 0xffffffff
        return self.wait

    def GetProcessTimes(self, handle, creation, exit_time, kernel, user):
        for pointer, value in zip([creation, exit_time, kernel, user], [0x100000001, 0x200000002, 0x300000003, 0x400000004]):
            pointer._obj.low = value & 0xffffffff
            pointer._obj.high = value >> 32
        return int(self.hit("GetProcessTimes"))


class FakeJournal:
    def __init__(self, fail_name=None):
        self.fail_name, self.rows = fail_name, []

    def append(self, name, **details):
        if name == self.fail_name:
            raise OSError("Synthetic publication failure")
        self.rows.append(dict(event=name, details=copy.deepcopy(details)))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def environment(**options):
    ffi, deadline = FakeC(), Deadline(options.pop("fail_at", None))
    fake_sdk = types.SimpleNamespace(C=ffi, DWORD=C.c_uint32, BOOL=C.c_int32,
                                     FILETIME=FILETIME, finite_deadline=deadline)
    namespace = dict(sdk=fake_sdk, time=time, require=require, ACCESS=0x00101000,
                     BOUNDARIES=("before_terminate", "after_terminate_return_before_wait",
                                 "after_owned_reap_observer_handles_held", "after_observer_pid_release_before_job_close"),
                     ObservationStop=RuntimeError)
    body = ast.Module(body=[copy.deepcopy(QUERY), copy.deepcopy(OBSERVER)], type_ignores=[])
    exec(compile(ast.fix_missing_locations(body), str(SOURCE) + "::<pure AST only>", "exec"), namespace)
    api = types.SimpleNamespace(k=FakeK(ffi, **options), closed=[], queried=False)
    api.query_reported = types.MethodType(namespace["query_reported"], api)
    journal = FakeJournal()
    observer = namespace["Observer"](api, journal, time.monotonic() + 10)
    observer.job = 900
    api.observer = observer

    def open_reported(pid, row):
        row.update(open_attempted=True, open_ok=True, open_error=None,
                   handle=777, closed=False, handle_registered_immediately=True)

    api.open_reported = open_reported
    api.close = api.closed.append
    return api, observer, journal, deadline


class MetadataTests(unittest.TestCase):
    def outcomes(self, **options):
        api, observer, journal, deadline = environment(**options)
        rows = []
        returned = api.query_reported(777, 42, 900, outcomes=rows)
        self.assertIs(returned, rows)
        self.assertEqual([row["query"] for row in rows], QUERY_ORDER)
        self.assertEqual(api.k.calls, QUERY_ORDER)
        self.assertEqual(deadline.calls, 10)
        for row in rows:
            self.assertLessEqual(row["started_monotonic_ns"], row["finished_monotonic_ns"])
            self.assertTrue(set(["ok", "error", "raw_output", "output_defined"]).issubset(row))
        return rows

    def test_typed_order_and_signaled_exit_time(self):
        rows = self.outcomes(wait=0)
        self.assertTrue(all(row["ok"] and row["output_defined"] for row in rows))
        self.assertTrue(rows[0]["matches_reported_pid"])
        self.assertEqual(rows[0]["raw_output"], 42)
        self.assertEqual(rows[2]["raw_output"], dict(job=900, is_member=True))
        self.assertTrue(rows[4]["exit_filetime_defined_only_if_signaled"])
        self.assertEqual(rows[4]["raw_output"], dict(creation_filetime=0x100000001,
                         exit_filetime_raw=0x200000002, kernel_filetime=0x300000003,
                         user_filetime=0x400000004))

    def test_timeout_retains_raw_exit_but_does_not_define_it(self):
        rows = self.outcomes(wait=258)
        self.assertTrue(rows[3]["ok"] and rows[3]["output_defined"])
        self.assertEqual(rows[3]["raw_output"], 258)
        self.assertFalse(rows[4]["exit_filetime_defined_only_if_signaled"])
        self.assertEqual(rows[4]["raw_output"]["exit_filetime_raw"], 0x200000002)

    def test_failed_wait_never_defines_exit_even_if_times_succeeds(self):
        rows = self.outcomes(wait=0xffffffff)
        self.assertFalse(rows[3]["ok"] or rows[3]["output_defined"])
        self.assertEqual(rows[3]["error"], 6)
        self.assertTrue(rows[4]["ok"])
        self.assertFalse(rows[4]["exit_filetime_defined_only_if_signaled"])

    def test_each_metadata_failure_preserves_raw_and_unknown(self):
        for name in QUERY_ORDER:
            with self.subTest(query=name):
                rows = self.outcomes(failure=name)
                row = rows[QUERY_ORDER.index(name)]
                self.assertFalse(row["ok"] or row["output_defined"])
                self.assertIn(row["error"], (5, 6))
                self.assertIsNotNone(row["raw_output"])
                if name == "GetProcessTimes":
                    self.assertFalse(row["exit_filetime_defined_only_if_signaled"])

    def test_zero_and_full_image_lengths_remain_unavailable(self):
        for size in [0, 32768]:
            with self.subTest(returned_length=size):
                image = self.outcomes(image_length=size)[1]
                self.assertTrue(image["ok"])
                self.assertFalse(image["output_defined"])
                self.assertIsNone(image["image_path_string"])
                self.assertEqual(image["raw_output"]["returned_length"], size)

    def test_unpaired_path_code_unit_kept_as_raw_not_serialization_failure(self):
        image = self.outcomes(image_surrogate=True)[1]
        self.assertFalse(image["output_defined"])
        self.assertIsNone(image["image_path_string"])
        self.assertTrue(image["raw_output"]["raw_utf16le_hex"].startswith("00d8"))

    def test_positive_queries_do_not_claim_historical_identity(self):
        api, observer, journal, deadline = environment()
        observer.pid(42, 0, True)
        row = observer.pids[42]
        self.assertTrue(row["same_handle_query_set_complete"])
        self.assertFalse(row["historical_identity_confirmed"])
        self.assertTrue(row["pid_reuse_before_open_possible"])

    def test_pid_mismatch_with_all_other_metadata_valid_is_incomplete(self):
        api, observer, journal, deadline = environment(returned_pid=99)
        observer.pid(42, 0, True)
        row = observer.pids[42]
        self.assertTrue(all(item["ok"] and item["output_defined"] for item in row["query_outcomes"]))
        self.assertFalse(row["query_outcomes"][0]["matches_reported_pid"])
        self.assertFalse(row["same_handle_query_set_complete"])
        self.assertTrue(observer.incomplete)
        self.assertFalse(row["historical_identity_confirmed"])

    def test_nonmembership_is_retained_uncertainty(self):
        api, observer, journal, deadline = environment(member=False)
        observer.pid(42, 0, True)
        self.assertFalse(observer.pids[42]["query_outcomes"][2]["raw_output"]["is_member"])
        self.assertFalse(observer.pids[42]["same_handle_query_set_complete"])
        self.assertTrue(observer.incomplete)

    def test_open_ownership_survives_publication_error(self):
        api, observer, journal, deadline = environment()
        journal.fail_name = "iocp_pid_open_returned"
        with self.assertRaisesRegex(OSError, "publication"):
            observer.pid(42, 0, True)
        self.assertEqual(observer.outstanding(), [dict(pid=42, handle=777)])
        self.assertEqual(api.k.calls, [])
        observer.close_pids()
        self.assertEqual(api.closed, [777])
        self.assertEqual(observer.outstanding(), [])

    def test_post_query_deadline_keeps_partial_rows_and_owned_handle(self):
        api, observer, journal, deadline = environment(fail_at=2)
        with self.assertRaisesRegex(TimeoutError, "finite-query"):
            observer.pid(42, 0, True)
        row = observer.pids[42]
        self.assertEqual(len(row["query_outcomes"]), 1)
        self.assertEqual(row["query_outcomes"][0]["raw_output"], 42)
        self.assertEqual(api.k.calls, ["GetProcessId"])
        self.assertEqual(observer.outstanding(), [dict(pid=42, handle=777)])
        observer.close_pids()
        self.assertEqual(api.closed, [777])

    def test_unexpected_query_exception_propagates_without_hiding_handle(self):
        api, observer, journal, deadline = environment(explode="GetProcessTimes")
        with self.assertRaisesRegex(OSError, "query exception"):
            observer.pid(42, 0, True)
        self.assertEqual(len(observer.pids[42]["query_outcomes"]), 4)
        self.assertEqual(observer.outstanding(), [dict(pid=42, handle=777)])
        observer.close_pids()
        self.assertEqual(api.closed, [777])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MetadataTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA, "Source changed during pure check"
    report = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Focused adversarial pure AST-extracted metadata/ownership checks; not native qualification",
                  source=dict(path=str(SOURCE), sha256=SOURCE_SHA),
                  checker=dict(path=str(Path(__file__).resolve()), sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
                  tests=result.testsRun, failures=[str(case) for case, _ in result.failures],
                  errors=[str(case) for case, _ in result.errors], denied_real_operations=DENIED,
                  status="passed" if result.wasSuccessful() else "failed",
                  activity=dict(real_SDK_calls=0, children=0, DLL_loads=0, network=0, path_string_file_opens=0))
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
