"""Independent fake-only terminal observation checks; no SDK constructor."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import time
import types
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "detached_abi_terminal_observation_v2.py"
REPORT = HERE / "DETACHED-ABI-TERMINAL-COMPONENT-PROOF-v2.json"
RAW = SOURCE.read_bytes()
SOURCE_SHA = hashlib.sha256(RAW).hexdigest()
SDK_SOURCE = HERE / "detached_parent_launch_draft_v1.py"
SDK_RAW = SDK_SOURCE.read_bytes()
assert hashlib.sha256(SDK_RAW).hexdigest() == "3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd"
SDK_TREE = ast.parse(SDK_RAW.decode("utf-8"))


def require(value, message):
    if not value:
        raise RuntimeError(message)


SDK_NS = dict(require=require)
SDK_NODES = [node for node in SDK_TREE.body if isinstance(node, ast.FunctionDef)
             and node.name in ("consume_capture", "job_snapshot_problem")]
exec(compile(ast.Module(body=SDK_NODES, type_ignores=[]), str(SDK_SOURCE)+"::<pure functions>", "exec"), SDK_NS)
NS = dict(__name__="pure_terminal_component")
exec(compile(RAW, str(SOURCE), "exec"), NS)  # stdlib-only module, no API or dispatch function.
DENIED = []
VECTORS = []


def guard(event, args):
    if event == "ctypes.dlopen" or event in ("subprocess.Popen", "os.system") or event.startswith("socket."):
        DENIED.append(event)
        raise AssertionError("No real operation allowed: " + event)


class Clock:
    def __init__(self, advance_sleep=True):
        self.value, self.advance_sleep = 100.0, advance_sleep
        self.sleep_calls = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleep_calls.append(seconds)
        if self.advance_sleep:
            self.value += seconds


def raw_snapshot(total=1, active=0, pids=()):
    decoded = dict(TotalUserTime=0, TotalKernelTime=0, ThisPeriodTotalUserTime=0,
                   ThisPeriodTotalKernelTime=0, TotalPageFaultCount=0, TotalProcesses=total,
                   ActiveProcesses=active, TotalTerminatedProcesses=0)
    return dict(accounting=dict(ok=True, error=0, returned_bytes=48,
                raw_hex=struct.pack("<qqqqIIII", *decoded.values()).hex(), decoded=decoded),
                pid_list=dict(ok=True, error=0, returned_bytes=8+8*len(pids), assigned_count=len(pids),
                listed_count=len(pids), pids=list(pids),
                raw_hex=struct.pack("<II16Q", len(pids), len(pids), *pids, *([0]*(16-len(pids)))).hex()))


class FakeAPI:
    def __init__(self, clock, order, *, fault=None, idle=False, total=1, live=False,
                 advance_available=0, advance_snapshot=0, advance_read=0):
        self.clock, self.order, self.fault = clock, order, fault
        self.idle, self.total, self.live = idle, total, live
        self.advance_available = advance_available
        self.advance_snapshot, self.advance_read = advance_snapshot, advance_read
        self.blocks = {12:b"tail-out\n",14:b"tail-err\n"}
        self.calls = []

    def hit(self, name):
        self.calls.append(name); self.order.append(name)
        if self.fault == name:
            raise OSError("Synthetic " + name + " failure")
        if self.fault == "interrupt_"+name:
            raise KeyboardInterrupt("Synthetic observation interruption")

    def available(self, handle):
        self.hit("available_"+str(handle))
        self.clock.value += self.advance_available
        if self.idle:
            return 0
        return len(self.blocks[handle]) if self.blocks[handle] else None

    def read(self, handle, count):
        self.hit("read_"+str(handle))
        result = self.blocks[handle][:count]; self.blocks[handle] = self.blocks[handle][count:]
        self.clock.value += self.advance_read
        return result

    def job_snapshot(self, job):
        self.hit("job_snapshot")
        self.clock.value += self.advance_snapshot
        return raw_snapshot(self.total, 1 if self.live else 0, (20,) if self.live else ())

    def verify_limits(self, job):
        self.hit("verify_limits")
        return dict(active_limit=1,process_commit=268435456,job_commit=268435456,
                    peak_process_commit=1234,peak_job_commit=2345)


def fixture(**options):
    clock = Clock(options.pop("advance_sleep",True));order=[]; events=[]
    api=FakeAPI(clock,order,**options)
    owner=types.SimpleNamespace(api=api,pi=types.SimpleNamespace(hProcess=21,dwProcessId=20),
        creation=dict(api_attempt_reserved=True,return_observed=True,returned_success=True),
        handles=dict(stdout_read=12,stderr_read=14),job=10,snapshot_count=3)
    report=dict(failure=dict(error_class="RuntimeError",error="Original child exit2"),
                call_return_observed=True,returncode=2,reaped=True)
    captures={name:dict(eof=False,truncated=False,retained_bytes=0,observed_bytes_at_least=0)
              for name in ("stdout","stderr")}
    streams={name:io.BytesIO() for name in captures}
    def predicate(raw,expected,pid):
        order.append("predicate");return SDK_NS["job_snapshot_problem"](raw,expected,pid)
    sdk=types.SimpleNamespace(LIMITS=dict(maximum_job_snapshots=40),
        consume_capture=SDK_NS["consume_capture"],job_snapshot_problem=predicate)
    def event(name,**details):
        order.append("event:"+name);events.append(dict(event=name,details=copy.deepcopy(details)))
    return types.SimpleNamespace(clock=clock,order=order,api=api,owner=owner,report=report,
                                 captures=captures,streams=streams,sdk=sdk,event=event,events=events)


class TerminalTests(unittest.TestCase):
    def run_case(self, f, *, deadline=110, event=None):
        primary=copy.deepcopy(f.report["failure"])
        result=NS["observe_terminal"](f.owner,f.report,f.captures,f.streams,sdk=f.sdk,
                 event=event or f.event,work_deadline=deadline,now=f.clock.now,sleep=f.clock.sleep)
        self.assertEqual(f.report["failure"],primary)
        self.assertIs(f.report["terminal_observation"],result)
        self.assertIs(f.report["terminal_observation_errors"],result["errors"])
        return result

    def test_nonzero_primary_retains_EOF_raw_final_and_peaks(self):
        f=fixture();s=self.run_case(f)
        self.assertTrue(s["complete"])
        self.assertEqual(f.report["returncode"],2)
        self.assertTrue(all(x["eof"] for x in f.captures.values()))
        self.assertEqual(f.streams["stdout"].getvalue(),b"tail-out\n")
        self.assertEqual(s["observations"]["job_snapshot"]["predicate"],"passed")
        self.assertEqual(s["observations"]["memory_limits_and_peaks"]["value"]["peak_job_commit"],2345)
        self.assertLess(f.order.index("event:abi_job_snapshot_observed"),f.order.index("predicate"))
        self.assertLess(f.order.index("predicate"),f.order.index("verify_limits"))

    def test_independent_stream_failures_do_not_suppress_other_observations(self):
        for fault in ["available_12","read_12","available_14","read_14"]:
            with self.subTest(fault=fault):
                f=fixture(fault=fault);s=self.run_case(f)
                self.assertFalse(s["complete"]);self.assertTrue(s["errors"])
                self.assertIn("job_snapshot",f.api.calls);self.assertIn("verify_limits",f.api.calls)
                other="stderr" if fault.endswith("12") else "stdout"
                self.assertTrue(f.captures[other]["eof"])

    def test_snapshot_query_failure_does_not_suppress_peaks(self):
        f=fixture(fault="job_snapshot");s=self.run_case(f)
        self.assertFalse(s["complete"])
        self.assertEqual(s["observations"]["job_snapshot"]["status"],"failed")
        self.assertEqual(s["observations"]["memory_limits_and_peaks"]["status"],"returned")
        self.assertEqual(f.owner.snapshot_count,4)
        self.assertTrue(s["observations"]["job_snapshot"]["attempt_reserved"])
        self.assertFalse(s["observations"]["job_snapshot"]["return_observed"])

    def test_peak_failure_does_not_erase_raw_snapshot(self):
        f=fixture(fault="verify_limits");s=self.run_case(f)
        self.assertEqual(s["observations"]["job_snapshot"]["raw"],raw_snapshot())
        self.assertEqual(s["observations"]["job_snapshot"]["predicate"],"passed")
        self.assertFalse(s["complete"])

    def test_raw_publication_failure_prevents_predicate_but_not_peaks(self):
        f=fixture()
        def event(name,**details):
            if name=="abi_job_snapshot_observed":raise OSError("Synthetic raw publication failure")
            f.event(name,**details)
        s=self.run_case(f,event=event);row=s["observations"]["job_snapshot"]
        self.assertEqual(row["raw"],raw_snapshot());self.assertEqual(row["raw_publication"],"failed")
        self.assertNotIn("predicate",f.order);self.assertIn("verify_limits",f.api.calls)

    def test_reservation_publication_failure_does_not_dispatch_that_query(self):
        f=fixture()
        def event(name,**details):
            if details.get("observation")=="terminal_job_snapshot":raise OSError("Synthetic reservation failure")
            f.event(name,**details)
        s=self.run_case(f,event=event)
        self.assertNotIn("job_snapshot",f.api.calls);self.assertIn("verify_limits",f.api.calls)
        self.assertFalse(s["observations"]["job_snapshot"]["call_attempted"])

    def test_counter_anomaly_retained_before_failed_predicate(self):
        f=fixture(total=2);s=self.run_case(f);row=s["observations"]["job_snapshot"]
        self.assertEqual(row["raw"]["accounting"]["decoded"]["TotalProcesses"],2)
        self.assertEqual(row["predicate"],"failed");self.assertFalse(s["complete"])
        self.assertLess(f.order.index("event:abi_job_snapshot_observed"),f.order.index("predicate"))
        self.assertIn("verify_limits",f.api.calls)

    def test_unknown_creation_even_with_handle_does_not_claim_finality(self):
        for unknown in ["creation","return"]:
            with self.subTest(unknown=unknown):
                f=fixture(live=True)
                if unknown=="creation":f.owner.creation["return_observed"]=False
                else:f.report["call_return_observed"]=False;f.report.pop("returncode")
                s=self.run_case(f)
                self.assertFalse(s["exit_observed"] or s["complete"])
                self.assertEqual(s["scope"],"pre_cleanup_creation_or_exit_unconfirmed")
                self.assertEqual(s["observations"]["job_snapshot"]["predicate"],"not_applicable_unconfirmed_exit")
                self.assertNotIn("predicate",f.order)
                self.assertTrue(s["physical_pipe_EOF_does_not_establish_child_exit"])

    def test_missing_owner_handles_are_unknown(self):
        f=fixture();f.owner.pi.hProcess=None;f.owner.job=None;f.owner.handles={}
        s=self.run_case(f)
        self.assertFalse(s["exit_observed"] or s["complete"])
        self.assertEqual(f.api.calls,[])
        self.assertEqual(s["observations"]["job_snapshot"]["status"],"not_attempted")

    def test_expired_work_cutoff_preserves_cleanup_reserve(self):
        f=fixture();s=self.run_case(f,deadline=100)
        self.assertFalse(s["complete"]);self.assertEqual(f.api.calls,[])
        self.assertTrue(all(not x["call_attempted"] for x in [s["observations"]["job_snapshot"],s["observations"]["memory_limits_and_peaks"]]))
        self.assertEqual(f.clock.value,100)

    def test_poll_limit_is_conservative_and_does_not_hide_other_queries(self):
        f=fixture(idle=True,advance_sleep=False);s=self.run_case(f)
        self.assertEqual(s["capture_polls_reserved"],64)
        self.assertEqual(sum(x.startswith("available_") for x in f.api.calls),64)
        self.assertTrue(all(x["status"]=="incomplete" for x in s["observations"]["capture_drain"].values()))
        self.assertIn("job_snapshot",f.api.calls);self.assertIn("verify_limits",f.api.calls)

    def test_capture_subdeadline_does_not_consume_main_work_cutoff(self):
        f=fixture(idle=True,advance_available=.1);s=self.run_case(f)
        self.assertLess(s["capture_polls_reserved"],64)
        self.assertLess(f.clock.value,110)
        self.assertIn("job_snapshot",f.api.calls);self.assertIn("verify_limits",f.api.calls)

    def test_late_snapshot_return_is_retained_without_finality(self):
        f=fixture(advance_snapshot=1);s=self.run_case(f,deadline=100.1)
        row=s["observations"]["job_snapshot"]
        self.assertEqual(f.owner.snapshot_count,4)
        self.assertTrue(row["attempt_reserved"] and row["call_attempted"] and row["return_observed"])
        self.assertEqual(row["value"],raw_snapshot())
        self.assertEqual(row["status"],"failed")
        self.assertEqual(row["raw_publication"],"not_attempted")
        self.assertEqual(row["predicate"],"not_evaluated")
        self.assertFalse(s["complete"]);self.assertNotIn("predicate",f.order)
        self.assertNotIn("verify_limits",f.api.calls)

    def test_late_read_return_preserves_known_bytes_and_bound(self):
        f=fixture(advance_read=1);s=self.run_case(f,deadline=100.1)
        call=s["observations"]["capture_drain"]["stdout"]["calls"][0]["read"]
        self.assertTrue(call["return_observed"])
        self.assertEqual(call["value"]["bytes"],len(b"tail-out\n"))
        self.assertEqual(f.captures["stdout"]["observed_bytes_at_least"],len(b"tail-out\n"))
        self.assertEqual(f.captures["stdout"]["retained_bytes"],len(b"tail-out\n"))
        self.assertEqual(f.streams["stdout"].getvalue(),b"tail-out\n")
        self.assertFalse(s["complete"])

    def test_capture_truncation_retains_bytes_error_and_other_stream(self):
        f=fixture();f.captures["stdout"].update(observed_bytes_at_least=65535,retained_bytes=65535)
        f.streams["stdout"]=io.BytesIO(b"x"*65535);f.streams["stdout"].seek(0,io.SEEK_END)
        s=self.run_case(f)
        self.assertEqual(f.captures["stdout"]["retained_bytes"],65536)
        self.assertEqual(f.captures["stdout"]["observed_bytes_at_least"],65535+len(b"tail-out\n"))
        self.assertTrue(f.captures["stdout"]["truncated"])
        self.assertEqual(len(f.streams["stdout"].getvalue()),65536)
        self.assertTrue(any(x["phase"]=="capture_consume_stdout" for x in s["errors"]))
        self.assertTrue(f.captures["stderr"]["eof"])
        self.assertIn("job_snapshot",f.api.calls);self.assertIn("verify_limits",f.api.calls)

    def test_snapshot_budget_and_capture_cap_are_not_bypassed(self):
        f=fixture();f.owner.snapshot_count=40;f.captures["stdout"].update(truncated=True,retained_bytes=65536)
        s=self.run_case(f)
        self.assertNotIn("job_snapshot",f.api.calls);self.assertNotIn("available_12",f.api.calls)
        self.assertIn("verify_limits",f.api.calls);self.assertFalse(s["complete"])

    def test_interrupt_stops_observation_without_erasing_primary(self):
        f=fixture(fault="interrupt_available_12");s=self.run_case(f)
        self.assertTrue(s["interrupted"]);self.assertFalse(s["complete"])
        self.assertNotIn("job_snapshot",f.api.calls);self.assertNotIn("verify_limits",f.api.calls)
        self.assertTrue(any(x["error_class"]=="KeyboardInterrupt" for x in s["errors"]))

    def test_malformed_deadlines_fail_before_any_API(self):
        for deadline in [float("nan"),float("inf"),True,"110"]:
            with self.subTest(deadline=repr(deadline)):
                f=fixture()
                with self.assertRaises(ValueError):self.run_case(f,deadline=deadline)
                self.assertEqual(f.api.calls,[])

    def test_component_has_no_cleanup_or_dispatch_capability(self):
        f=fixture();s=self.run_case(f)
        self.assertFalse(any("close" in name or "create" in name or "terminate" in name for name in f.api.calls))
        self.assertEqual(f.owner.snapshot_count,4)


if __name__=="__main__":
    sys.addaudithook(guard)
    started=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TerminalTests))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA,"Component changed during check"
    def pin(path):
        raw=Path(path).read_bytes();return dict(path=str(Path(path).resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    tree=ast.parse(RAW.decode());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="observe_terminal")
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(case) for case,_ in result.failures],errors=[str(case) for case,_ in result.errors],elapsed_seconds=time.monotonic()-started,
        component=pin(SOURCE),checker=pin(Path(__file__)),SDK_source=pin(SDK_SOURCE),
        component_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        scope="Independent fake terminal component only; parentv2 integration/late lease/seal path not covered yet",
        denied_real_operations=DENIED,activity=dict(SDK_constructors_or_API_calls=0,children_or_target_DLL_calls=0,model_or_protected_payload_reads=0))
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write("\n")
    print(json.dumps(dict(report=str(REPORT),sha256=pin(REPORT)["sha256"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
