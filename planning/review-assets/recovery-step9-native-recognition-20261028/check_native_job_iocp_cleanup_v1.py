"""Three supplemental pure IOCP ownership/boundary/snapshot-budget faults."""
from importlib import util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=util.spec_from_file_location("iocp_existing_pure_vectors",HERE/"check_native_job_iocp_v3.py")
v=util.module_from_spec(spec);spec.loader.exec_module(v)
d,sdk=v.d,v.sdk


class Supplement(unittest.TestCase):
    def setUp(self):self.base=v.PureChecks()
    def test_pid_and_port_close_failures_do_not_skip_owned_cleanup(self):
        class BadClose(v.FakeApi):
            def close(self,handle):
                if handle in (2020,40):raise OSError("Injected observer close fault "+str(handle))
                return super().close(handle)
        c,a,r=self.base.full_fake("supplement-close",api_type=BadClose)
        case=r["diagnostic"]
        self.assertIn("close_21",a.events);self.assertIn("close_10",a.events)
        self.assertFalse(case["port_closed"]);self.assertEqual(case["outstanding_handles"][0]["handle"],2020)
        self.assertTrue(any(x["phase"]=="close_reported_pid" for x in case["observer_errors"]))
        self.assertTrue(any(x["phase"]=="close_completion_port" for x in case["observer_errors"]))
        self.assertFalse(case["diagnostic_completeness"]);self.assertEqual(r["terminal_status"],"failed")
    def test_pretermination_publication_failure_still_terminates_and_reaps(self):
        original=sdk.reserve_parent_journal
        class Proxy:
            def __init__(self,journal):self.journal=journal;self.failed=False
            def append(self,name,**details):
                if name=="iocp_raw_job_snapshot" and details.get("stage")=="before_terminate" and not self.failed:
                    self.failed=True;raise OSError("Injected stop-boundary publication fault")
                return self.journal.append(name,**details)
            def close(self):return self.journal.close()
        with patch.object(sdk,"reserve_parent_journal",side_effect=lambda *a,**k:Proxy(original(*a,**k))):
            c,a,r=self.base.full_fake("supplement-boundary")
        case=r["diagnostic"]
        self.assertIn("observed_terminate",a.events);self.assertTrue(case["owned_reaped"]);self.assertIn("close_40",a.events)
        self.assertEqual(set(case["stop_boundary_snapshot_references"]),set(d.BOUNDARIES))
        before=next(x for x in case["raw_snapshots"] if x["stage"]=="before_terminate")
        self.assertFalse(before["raw_durable"]);self.assertEqual(r["terminal_status"],"failed")
    def test_36_work_plus_four_boundaries_and_no_41st_query(self):
        observer,api,journal=self.base.observer()
        observer.owner=SimpleNamespace(job=10,snapshot_count=0,pi=SimpleNamespace(dwProcessId=20))
        calls=[];original=api.job_snapshot
        def query(job):calls.append(job);return original(job)
        api.job_snapshot=query
        for i in range(36):observer.record_snapshot("work-"+str(i),"empty",enforce=False)
        with self.assertRaises(RuntimeError):observer.record_snapshot("extra-work","empty")
        self.assertEqual(len(calls),36)
        for stage in d.BOUNDARIES:observer.record_snapshot(stage,"empty",boundary=True,enforce=False)
        with self.assertRaises(RuntimeError):observer.record_snapshot("extra-boundary","empty",boundary=True)
        self.assertEqual(len(calls),40);self.assertEqual(observer.owner.snapshot_count,40)


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Supplement))
    report=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",helper_sha256=d.sha(v.SOURCE),
        checker_sha256=d.sha(__file__),vector_checker_sha256=d.sha(HERE/"check_native_job_iocp_v3.py"),
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),actual_children=0,
        real_sdk_constructions=0,output=str(v.ROOT),scope="Only fake API/worker/queue faults; no SDK or native child")
    with (HERE/"NATIVE-JOB-IOCP-CLEANUP-SUPPLEMENT-v1.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
