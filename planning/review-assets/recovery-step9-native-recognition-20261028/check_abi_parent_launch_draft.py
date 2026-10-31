"""Pure draft checks: layout, arguments, memory captures and fake ownership.

Never constructs Kernel32, creates a process, loads a target DLL, imports AsOf
runtime, reads a GGUF, or uses a network connection. ctypes sizes only.
"""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "abi_parent_launch_draft.py"
spec = importlib.util.spec_from_file_location("r09_abi_parent_draft_pure", SOURCE)
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


class FakeApi:
    def __init__(self, failure=None, anomalous=False):
        self.failure, self.anomalous = failure, anomalous
        self.calls, self.closed, self.dead = [], [], False
        self.assigned = False

    def call(self, name):
        self.calls.append(name)
        if self.failure == name:
            raise RuntimeError("fixture_" + name)

    def create_job(self):
        self.call("create_job"); return 10

    def configure_job(self, job):
        self.call("configure_job")

    def verify_limits(self, job):
        self.call("verify_limits"); return dict(active_limit=1, process_commit=256*1024**2, job_commit=256*1024**2)

    def job_snapshot(self, job):
        self.call("job_snapshot")
        if not self.assigned:
            return dict(total=0, active=0, terminated=0, pids=[])
        return dict(total=2 if self.anomalous else 1, active=1, terminated=0, pids=[20])

    def make_stdio(self, owned):
        self.call("make_stdio")
        owned.update(stdin=11, stdout_read=12, stdout_write=13, stderr_read=14, stderr_write=15)

    def create_suspended(self, argv, command, environment, cwd, owned, pi):
        self.call("create_suspended")
        pi.hProcess, pi.hThread, pi.dwProcessId, pi.dwThreadId = 21, 22, 20, 23
        if self.failure == "interrupt_after_create":
            raise KeyboardInterrupt("fixture interruption after output struct populated")

    def assign(self, job, process):
        self.call("assign"); self.assigned = True

    def in_job(self, job, process):
        self.call("in_job"); return self.failure != "membership_false"

    def identity(self, pi, exe):
        self.call("identity"); return dict(pid=int(pi.dwProcessId), thread_id=int(pi.dwThreadId), image=str(exe))

    def resume(self, thread):
        self.call("resume")
        if self.failure == "interrupt_in_resume":
            raise KeyboardInterrupt("fixture unknown actual resumption")
        return {"resume_zero":0, "resume_two":2, "resume_error":0xffffffff}.get(self.failure, 1)

    def wait(self, process, ms):
        self.call("wait"); return self.dead

    def terminate_process(self, process):
        self.call("terminate_process"); self.dead = True

    def terminate_job(self, job):
        self.call("terminate_job"); self.dead = True

    def close(self, handle):
        self.call("close")
        self.closed.append(handle)


class PureDraftTests(unittest.TestCase):
    def owner(self, *, failure=None, anomalous=False, journal_failure=None):
        api, events = FakeApi(failure, anomalous), []
        def event(name, **fields):
            events.append(name)
            if name == journal_failure:
                raise OSError("fixture journal failure")
        owner = draft.OwnedLaunch(api, event)
        return api, owner, events

    def start(self, owner):
        argv = [str(draft.EXE), "--abi", str(draft.RUNTIME), str(draft.ROOT / "data/cache/pure-unused/child")]
        owner.start(argv, "fixture command only", dict(SystemRoot=r"C:\Windows"), draft.ROOT, lambda:None)

    def cleaned(self, owner, api):
        owner.cleanup(time.monotonic()+2)
        self.assertTrue(owner.reaped)
        self.assertEqual(owner.cleanup_errors, [])
        self.assertEqual(set(api.closed), set(range(10,16)) | {21,22})
        self.assertEqual(len(api.closed), 8)

    def test_public_sdk_x64_layouts(self):
        self.assertEqual(draft.layouts()["STARTUPINFOEXW"], 112)
        self.assertEqual(draft.ACCOUNTING.ActiveProcesses.offset, 40)
        self.assertEqual(draft.EXTENDED_LIMIT.PeakJobMemoryUsed.offset, 136)

    def test_finite_flags_no_breakaway(self):
        self.assertEqual(draft.CREATE_FLAGS, 0x08080404)
        self.assertFalse(draft.CREATE_FLAGS & 0x01000000)
        self.assertEqual(draft.JOB_FLAGS, 0x2308)
        self.assertEqual(draft.LIMITS["commit_bytes"], 268435456)

    def test_suspended_assign_verify_before_exact_resume(self):
        api, owner, events = self.owner()
        self.start(owner)
        self.assertLess(api.calls.index("create_suspended"), api.calls.index("assign"))
        self.assertLess(api.calls.index("assign"), api.calls.index("identity"))
        self.assertLess(api.calls.index("identity"), api.calls.index("resume"))
        self.assertEqual(api.calls.count("resume"), 1)
        self.assertLess(events.index("abi_assigned_before_resume"), events.index("abi_resume_reserved"))
        self.assertTrue(owner.assigned and owner.resumed)
        self.cleaned(owner, api)

    def test_assign_failure_never_resumes_unassigned_owned_process(self):
        api, owner, _ = self.owner(failure="assign")
        with self.assertRaisesRegex(RuntimeError, "fixture_assign"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)
        self.assertIn("terminate_process", api.calls)
        self.assertNotIn("terminate_job", api.calls)

    def test_membership_failure_never_resumes(self):
        api, owner, _ = self.owner(failure="membership_false")
        with self.assertRaisesRegex(RuntimeError, "not in exact Job"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)
        self.assertIn("terminate_job", api.calls)

    def test_job_anomaly_stops_before_resume(self):
        api, owner, _ = self.owner(anomalous=True)
        with self.assertRaisesRegex(RuntimeError, "accounting anomaly before resume"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)

    def test_resume_bad_previous_counts_have_no_second_attempt(self):
        for failure in ("resume_zero", "resume_two", "resume_error"):
            with self.subTest(failure=failure):
                api, owner, _ = self.owner(failure=failure)
                with self.assertRaisesRegex(RuntimeError, "exactly one suspension"):
                    self.start(owner)
                self.assertEqual(api.calls.count("resume"), 1)
                self.cleaned(owner, api)

    def test_interrupted_resume_records_unknown_not_zero_execution(self):
        api, owner, _ = self.owner(failure="interrupt_in_resume")
        with self.assertRaises(KeyboardInterrupt):
            self.start(owner)
        record=owner.resumption_record()
        self.assertTrue(record["resume_attempted"])
        self.assertFalse(record["resume_return_observed"])
        self.assertEqual(record["state"],"unknown_may_have_run")
        self.cleaned(owner,api)

    def test_journal_failure_before_resume_never_resumes(self):
        api, owner, _ = self.owner(journal_failure="abi_resume_reserved")
        with self.assertRaisesRegex(OSError, "journal failure"):
            self.start(owner)
        self.assertNotIn("resume", api.calls)
        self.cleaned(owner, api)

    def test_journal_failure_after_create_retains_process_for_cleanup(self):
        api, owner, _ = self.owner(journal_failure="abi_created_suspended")
        with self.assertRaisesRegex(OSError, "journal failure"):
            self.start(owner)
        self.assertNotIn("assign", api.calls)
        self.cleaned(owner, api)

    def test_interruption_after_create_retains_output_handles(self):
        api, owner, _ = self.owner(failure="interrupt_after_create")
        with self.assertRaises(KeyboardInterrupt):
            self.start(owner)
        self.assertNotIn("assign", api.calls)
        self.cleaned(owner, api)

    def test_configure_failure_closes_job_no_process(self):
        api, owner, _ = self.owner(failure="configure_job")
        with self.assertRaisesRegex(RuntimeError, "configure_job"):
            self.start(owner)
        owner.cleanup(time.monotonic()+2)
        self.assertEqual(api.closed, [10])
        self.assertNotIn("create_suspended", api.calls)

    def test_capture_exact_boundary_then_one_byte_overflow(self):
        sink = io.BytesIO()
        state = dict(observed_bytes_at_least=0, retained_bytes=0, truncated=False)
        draft.consume_capture(state, b"abcd", sink, cap=4)
        self.assertEqual(sink.getvalue(), b"abcd")
        with self.assertRaisesRegex(RuntimeError, "unknown further bytes"):
            draft.consume_capture(state, b"z", sink, cap=4)
        self.assertEqual(sink.getvalue(), b"abcd")
        self.assertEqual(state, dict(observed_bytes_at_least=5, retained_bytes=4, truncated=True))

    def test_environment_explicit_sorted_utf16_double_nul(self):
        text = draft.environment_block(dict(z="astral \U0001f642", A="two words"))
        self.assertEqual(text, "A=two words\0z=astral \U0001f642\0\0")
        self.assertTrue(text.encode("utf-16-le").endswith(b"\0\0\0\0"))
        env = draft.effective_environment(draft.ROOT / "data/cache/pure-unused")
        self.assertEqual(set(env), {"SystemRoot","WINDIR","SystemDrive","PATH","TEMP","TMP","OMP_NUM_THREADS","OMP_THREAD_LIMIT"})
        self.assertNotIn("GGML_BACKEND_PATH", env)

    def test_environment_rejects_ambiguous_nul_nonstring_and_surrogate(self):
        for env in ({"a":"x","A":"y"},{"a\0":"x"},{"a":"x\0"},{"a":1},{"a=b":"x"}):
            with self.subTest(env=repr(env)), self.assertRaises(RuntimeError):
                draft.environment_block(env)
        with self.assertRaises(UnicodeEncodeError):
            draft.environment_block({"a":"\ud800"})

    def test_exact_abi_arguments_runtime_binding_and_quoting(self):
        child = draft.ROOT / "data/cache/pure unused/child"
        args, command = draft.abi_argv(draft.EXE,draft.RUNTIME,child)
        self.assertEqual(args[1],"--abi")
        self.assertEqual(len(args),4)
        self.assertIn('"'+str(child)+'"',command)
        with self.assertRaisesRegex(RuntimeError,"Exact ABI-only"):
            draft.abi_argv(draft.EXE,draft.RUNTIME.parent,child)

    def test_deadlines_reject_nonfinite_expired_and_bool(self):
        for end in (float("inf"),float("nan"),True):
            with self.subTest(end=end),self.assertRaises(RuntimeError):
                draft.finite_deadline(end)
        with self.assertRaises(TimeoutError):
            draft.finite_deadline(time.monotonic()-1)

    def test_native_construction_and_entry_are_held(self):
        self.assertFalse(draft.NATIVE_EXECUTION_ENABLED)
        with self.assertRaisesRegex(RuntimeError,"construction is disabled"):
            draft.Kernel32()
        with self.assertRaisesRegex(RuntimeError,"execution disabled"):
            draft.execute_draft({})

    def test_no_subprocess_creation_private_api_or_network_import(self):
        tree=ast.parse(SOURCE.read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imports += [x.name for n in ast.walk(tree) if isinstance(n,ast.Import) for x in n.names]
        self.assertFalse(set(imports)&{"_winapi","socket","urllib.request","requests"})
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in {"Popen","run","check_output","system"} for n in calls))


def main():
    require_flags = sys.flags.isolated and sys.dont_write_bytecode
    if not require_flags:
        raise RuntimeError("Use accepted installed interpreter -I -B")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureDraftTests))
    report=dict(schema_version=1,status="passed_pure_draft_checks" if result.wasSuccessful() else "failed_pure_draft_checks",
                helper_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
                native_API_construction_enabled=False,actual_processes_created=0,target_native_calls=0,
                ctypes_kernel32_construction=0,network_requests=0,GGUF_reads=0,
                scope="Pure sizes/offsets, argv/environment/caps and fake-API ownership sequencing only; no Windows API qualification")
    target=HERE/"ABI-PARENT-PURE-CHECKS-v2.json"
    with target.open("xb") as f:f.write(json.dumps(report,sort_keys=True,indent=2).encode()+b"\n")
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":
    raise SystemExit(main())
