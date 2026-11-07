"""Fictional controller tests: local process boundaries and transports are mocked.

Synthetic model bytes are never executed. These tests do not constitute native
server or production qualification; the external certificate must say so.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether._process import EngineResult
from tether_engine.serde import encode
from experiments.labbench.tests import test_model as model_fixture
from experiments.litqa_comparison.tests import test_replay as native_fixture
from experiments.litqa_comparison import transport
from experiments.litqa_recovery import run as r, test_plan as plan_fixture


def success(limits, *, code=0, stdout=b"fictional child\n", stderr=b""):
    return EngineResult(returncode=code, stdout=stdout, stderr=stderr, supervision=dict(
        schema_version=1, method="tether.process_envelope.v1", limits=limits.payload(), termination_reason="exited",
        execution_elapsed_seconds=.01, total_elapsed_seconds=.02, retained_stdout_bytes=len(stdout),
        retained_stderr_bytes=len(stderr), observed_stdout_bytes=len(stdout), observed_stderr_bytes=len(stderr),
        observed_counts_are_lower_bounds=False, pipe_eof=dict(stdout=True, stderr=True), process_started=True,
        process_reaped=True, cleanup_errors=[]))


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.f = plan_fixture.RecoveryPlanTests("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.n = native_fixture.ReplayTests("runTest")
        self.n.setUp()
        self.addCleanup(self.n.doCleanups)
        self.top = self.f.top
        self.output = self.top / "recovered"
        self.pins = {"experiments/litqa_recovery/run.py": r.c.capture(r.__file__)[0]["sha256"]}
        self.patcher = patch.object(r, "source_pins", return_value=self.pins)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        license_path = self.top / "MODEL-LICENSE.txt"
        license_path.write_bytes(b"Fictional unit fixture; no real model.")
        self.model = dict(model_receipt=r.c.capture(self.n.f.receipt)[0], model_license=r.c.capture(license_path)[0],
            port=55598, alias=self.n.alias, model_spec=self.n.info["spec"], model_provenance=encode(self.n.info["provenance"]))
        original_source = self.top / "archive/files/0001.py"
        original_source.parent.mkdir(parents=True)
        original_source.write_bytes(b"# fictional historical producer, never executed\n")
        original_pins = {"experiments/original.py": r.c.capture(original_source)[0]["sha256"]}
        self.f.frame.update(model=self.model, generation_configuration=encode(r.codecs.CONFIG), code_pins=original_pins,
                            primary_execution=None)
        self._reframe()
        self.reserved = self.f.reserve()
        self.parent = self.f.inspect()
        self.authority = Path(self.reserved["authority"]["path"]).parent
        archive = r.c.publish(self.top / "archive/MANIFEST.json", dict(schema_version=1,
            kind="sc04_executed_source_archive_v1", original_repository_root=str(r.ROOT),
            files={"experiments/original.py": r.c.capture(original_source)[0]}))
        primary_root = self.top / "primary"
        primary_root.mkdir()
        complete = r.c.publish(primary_root / "COMPLETE.json", dict(status="primary_execution_complete",
                                                                  purpose="fictional_qualification"))
        primary_receipt = r.c.publish(primary_root / "ROOT-RECEIPT.json", dict(status="primary_execution_complete",
            frame_sha256="a"*64, files={"COMPLETE.json": complete}))
        replay = r.c.publish(self.top / "PRIMARY-REPLAY.json", dict(status="fictional_pass"))
        acceptance = r.c.publish(self.top / "ACCEPTANCE.json", dict(status="passed",
            primary_execution_anchor=primary_receipt["sha256"], scientific_correctness_scored=False, primary_replay=replay))
        parity = r.c.publish(self.top / "PARITY.json", dict(scope="Fictional namespace transition control only"))
        qualification = r.c.publish(self.top / "QUALIFICATION.json", dict(schema_version=2,
            kind="sc04_recovery_controller_qualification_v2", status="PASS", tests=1, failures=0, errors=0, skipped=0,
            code_pins=self.pins, scope="Mocked controller unit fixture, not production qualification"))
        self.certificate = dict(schema_version=2, kind="sc04_recovery_transition_certificate_v2", status="PASS",
            purpose="fictional_qualification", original_supplied_frame=self.parent["original_frame"],
            primary=dict(root=str(primary_root), root_receipt_sha256=primary_receipt["sha256"]), primary_acceptance=acceptance,
            source_archive=dict(path=archive["path"], sha256=archive["sha256"]), original_repository_root=str(r.ROOT),
            current_code_pins=self.pins, parity_proof=parity, qualification=qualification)
        self.certificate_proof = r.c.publish(self.top / "TRANSITION.json", self.certificate)
        self.collection_qualification = r.c.publish(self.top / "COLLECTION-QUALIFICATION.json", dict(schema_version=2,
            kind="sc04_recovery_collection_qualification_v2", status="PASS", tests=1, failures=0, errors=0, skipped=0,
            code_pins=r.c.source_pins(), scope="Fictional unit fixture"))
        self.frame = r.make_frame(self.reserved["frame"], self.reserved["authority"], self.certificate_proof,
                                 self.collection_qualification, self.output, self.top,
                                 collect_seconds=600, answer_seconds=600, replay_seconds=300)
        self.frame_proof = r.c.publish(self.top / "EXECUTION.json", self.frame)
        self.dispatched, self.server_calls = [], 0

    def _reframe(self):
        plan_fixture.write(self.f.frame_path, self.f.frame)
        plan_fixture.write(self.f.root / "FRAME.json", self.f.frame)
        self.f.frame_sha = r.c.capture(self.f.frame_path)[0]["sha256"]
        path = self.f.root / "collect/JOB.json"
        job = json.loads(path.read_bytes())
        job["frame_sha256"] = self.f.frame_sha
        plan_fixture.write(path, job)
        path = self.f.root / "collect/COMMAND.json"
        command = json.loads(path.read_bytes())
        command["command"][command["command"].index("--frame-sha256")+1] = self.f.frame_sha
        command["command"][command["command"].index("--job-sha256")+1] = r.c.capture(self.f.root / "collect/JOB.json")[0]["sha256"]
        plan_fixture.write(path, command)
        plan_fixture.write(self.f.root / "collect/worker/CONFIG.json", dict(frame_sha256=self.f.frame_sha,
            job=job, purpose="fictional_qualification"))
        self.f.anchor()
        policy = json.loads(self.f.registry_policy_path.read_bytes())
        policy["parent_identity"] = self.f.inspect()["parent_identity"]
        plan_fixture.write(self.f.registry_policy_path, policy)
        self.f.registry_policy_sha = r.c.capture(self.f.registry_policy_path)[0]["sha256"]

    def changed_frame(self, change, name="CHANGED.json"):
        frame = deepcopy(self.frame)
        change(frame)
        return frame, r.c.publish(self.top / name, frame)

    @contextmanager
    def owner(self, spec, bindings, *, output, journal, parent_deadline):
        self.assertTrue((self.authority / "answer-execution/CLAIM.json").is_file())
        self.server_calls += 1
        self.n.f.owner.terminal_record = dict(pid=12345, server_stopped=False)
        journal.append("server_started", pid=12345)
        journal.append("server_ready", pid=12345)
        try:
            yield self.n.f.owner
        finally:
            self.n.f.owner.terminal_record["server_stopped"] = True
            journal.append("server_terminal", **self.n.f.owner.terminal_record)

    def fetch(self, url, **limits):
        self.assertIn("10.1234%2Fthree", url)
        return dict(body=b'{"hitCount":0,"resultList":{"result":[]}}', status=200, final_url=url, headers={})

    def child(self, command, *, limits):
        mode = command[6]
        options = dict(zip(command[7::2], command[8::2]))
        self.dispatched.append((mode, Path(options["--job"]).parent.name))
        operation = r.worker if mode == "worker" else r.review_worker
        audits = []
        with ExitStack() as stack:
            stack.enter_context(patch.object(r, "contain_process_tree", return_value=object()))
            stack.enter_context(patch.object(r, "DeadlineWatchdog", side_effect=lambda *a, **k: nullcontext()))
            stack.enter_context(patch.object(r, "empty_import_cache"))
            stack.enter_context(patch.object(r.WorkerAudit, "activate", autospec=True, side_effect=lambda a: audits.append(a)))
            stack.enter_context(patch.object(r.model, "owned_server", side_effect=self.owner))
            stack.enter_context(patch.object(r.c.resolver.legacy, "fetch_http", side_effect=self.fetch))
            stack.enter_context(patch.object(transport.native, "_check_owner", return_value=12345))
            stack.enter_context(patch.object(transport.native, "_watchdog", return_value=model_fixture.Timer()))
            stack.enter_context(patch.object(transport.model, "tokenize_once", side_effect=self.n.tokenize))
            stack.enter_context(patch.object(r.model.http.client, "HTTPConnection", side_effect=lambda *a, **k:
                model_fixture.Connection(model_fixture.Response(self.n.f.native_body(
                    content='{"answer_index":1,"evidence_ids":[]}')), self.n.f.calls)))
            try:
                operation(options["--frame"], options["--frame-sha256"], options["--job"], options["--job-sha256"],
                          output=Path(options["--output"]))
            finally:
                for audit in audits: audit.stream.close()
        return success(limits)

    def execute(self, child=None):
        with patch.object(r, "supervise_command", side_effect=self.child if child is None else child), \
             patch.object(r, "contain_process_tree", return_value=object()), \
             patch.object(r, "DeadlineWatchdog", side_effect=lambda *a, **k: nullcontext()):
            return r.execute(self.frame_proof["path"], self.frame_proof["sha256"], output=self.output)

    def test_read_only_frame_validation_binds_archive_model_qualifications_and_schedule(self):
        result = r.verify_frame(self.frame_proof["path"], self.frame_proof["sha256"], self.output)
        self.assertEqual(result[3]["answer_queries"], self.f.queries)
        self.assertEqual(result[2]["maximum_answer_calls"], 3)
        self.assertFalse(self.output.exists())
        self.assertFalse((self.authority / "answer-execution").exists())

    def test_model_caps_source_or_external_anchor_change_fail_before_dispatch(self):
        changes = [lambda f: f.update(call_seconds=121), lambda f: f["model"].update(alias="replacement"),
                   lambda f: f.update(maximum_answer_calls=2), lambda f: f.update(code_pins={}),
                   lambda f: f["generation_configuration"].update(n_predict=257)]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                _, proof = self.changed_frame(change, f"BAD-{index}.json")
                with patch.object(r, "supervise_command") as dispatch, self.assertRaises(ValueError):
                    r.verify_frame(proof["path"], proof["sha256"], self.output)
                dispatch.assert_not_called()
        with self.assertRaisesRegex(ValueError, "anchor"):
            r.verify_frame(self.frame_proof["path"], "f"*64)

    def test_qualification_or_parity_bytes_change_rejected(self):
        path = Path(self.certificate["parity_proof"]["path"])
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            r.verify_frame(self.frame_proof["path"], self.frame_proof["sha256"])

    def test_untrusted_parent_cannot_create_failure_inside_original(self):
        target = self.f.root / "unwanted"
        _, proof = self.changed_frame(lambda f: f.update(output=str(target)), "OVERLAP.json")
        before = r.plan._inventory(self.f.root)
        with self.assertRaisesRegex(ValueError, "protected"):
            r.execute(proof["path"], proof["sha256"], output=target)
        self.assertEqual(before, r.plan._inventory(self.f.root))
        self.assertFalse(target.exists())

    def test_answer_claim_is_permanent_and_concurrent_outputs_cannot_reserve(self):
        other = dict(self.frame, output=str(self.top / "alternative"))
        def reserve(frame):
            try: return r.reserve_answers(self.frame_proof, frame, self.parent, self.authority)
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, [self.frame, other]))
        self.assertEqual(sum(v is not None for v in results), 1)
        with self.assertRaises(FileExistsError):
            r.reserve_answers(self.frame_proof, self.frame, self.parent, self.authority)

    def test_supervisor_timeout_retains_streams_and_reap_record_without_retry(self):
        root = self.top / "supervision"
        root.mkdir()
        limits = r.ProcessLimits(timeout_seconds=1, max_output_bytes=1024)
        error = TimeoutError("Fictional timeout")
        error.tether_engine_result = success(limits, code=-1, stdout=b"partial", stderr=b"timed out")
        with patch.object(r, "supervise_command", side_effect=error) as dispatch:
            with self.assertRaises(TimeoutError): r.supervised(["fictional"], limits, root, "execution")
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual((root / "execution-stdout.txt").read_bytes(), b"partial")
        self.assertEqual(json.loads((root / "execution-SUPERVISION.json").read_bytes())["returncode"], -1)

    def test_failed_collection_never_claims_or_starts_answer(self):
        def failed(command, *, limits): return success(limits, code=1, stderr=b"fictional collect failure")
        with self.assertRaisesRegex(ValueError, "worker failed"): self.execute(failed)
        self.assertFalse((self.authority / "answer-execution").exists())
        self.assertFalse((self.output / "ROOT-RECEIPT.json").exists())
        self.assertTrue((self.output / "FAILURE.json").is_file())
        self.assertTrue((self.output / "collect/execution-SUPERVISION.json").is_file())

    def test_interrupted_supervision_does_not_retry_and_preserves_root(self):
        calls = []
        def stop(command, *, limits):
            calls.append(command)
            raise KeyboardInterrupt("Fictional operator stop")
        with self.assertRaises(KeyboardInterrupt): self.execute(stop)
        self.assertEqual(len(calls), 1)
        failure = json.loads((self.output / "FAILURE.json").read_bytes())
        self.assertEqual(failure["error_type"], "KeyboardInterrupt")
        self.assertFalse(failure["automatic_retry"])
        with self.assertRaises(FileExistsError): self.execute(stop)
        self.assertEqual(len(calls), 1)

    def test_worker_audit_denies_parent_mutation_and_offline_dispatch(self):
        root = self.top / "audit"
        root.mkdir()
        audit = r.WorkerAudit(inputs=[], output=root, code_roots=[], claim_root=self.authority / "collection-execution", offline=True)
        self.addCleanup(audit.stream.close)
        with self.assertRaises(PermissionError): audit.hook("os.remove", (str(self.f.root / "FRAME.json"), -1))
        with self.assertRaises(PermissionError): audit.hook("socket.connect", (object(), ("127.0.0.1", 123)))
        with self.assertRaises(PermissionError): audit.hook("subprocess.Popen", ("fictional", [], None, None))
        with self.assertRaises(PermissionError): audit.hook("open", (str(audit.claim_root / "CLAIM.json"), "w", os.O_WRONLY | os.O_TRUNC))

    def test_claim_write_failure_leaves_non_reusable_reservation(self):
        with patch.object(r.c, "publish", side_effect=OSError("Invented write failure")):
            with self.assertRaises(OSError): r.reserve_answers(self.frame_proof, self.frame, self.parent, self.authority)
        self.assertTrue((self.authority / "answer-execution").is_dir())
        with self.assertRaises(FileExistsError): r.reserve_answers(self.frame_proof, self.frame, self.parent, self.authority)

    def test_resealed_terminal_contradictions_are_rejected(self):
        self.execute()
        baseline = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        def write(path, value): path.write_bytes(r.c.canonical(value) + b"\n")
        def seal():
            complete = json.loads((self.output / "COMPLETE.json").read_bytes())
            pairs = []
            for event in r.c._chain((self.output / "journal.jsonl").read_bytes()):
                details = deepcopy(event["details"])
                if event["event"] == "phase_accepted": details["descriptor"] = complete["phases"][details["phase"]]
                if event["event"] == "controller_completed": details["complete"] = r.c.capture(self.output / "COMPLETE.json")[0]
                pairs.append((event["event"], details))
            plan_fixture.journal(self.output / "journal.jsonl", pairs)
            receipt = json.loads((self.output / "ROOT-RECEIPT.json").read_bytes())
            receipt["files"] = r.c.inventory(self.output, omit=("ROOT-RECEIPT.json",))[0]
            write(self.output / "ROOT-RECEIPT.json", receipt)
            return r.c.capture(self.output / "ROOT-RECEIPT.json")[0]["sha256"]
        for corruption in ("negative_wall", "failure_marker", "failed_review"):
            with self.subTest(corruption=corruption):
                for name, raw in baseline.items(): (self.output / name).write_bytes(raw)
                marker = self.output / "FAILURE.json"
                if marker.exists(): marker.unlink()
                if corruption == "negative_wall":
                    path = self.output / "COMPLETE.json"
                    value = json.loads(path.read_bytes()); value["wall_seconds"] = -1; write(path, value)
                elif corruption == "failure_marker":
                    write(marker, dict(error_type="KeyboardInterrupt", automatic_retry=False))
                else:
                    path = self.output / "answer/review/journal.jsonl"
                    events = r.c._chain(path.read_bytes())
                    pairs = [(e["event"], e["details"]) for e in events]
                    pairs[-1] = ("execution_failed", dict(error_type="KeyboardInterrupt", automatic_retry=False))
                    plan_fixture.journal(path, pairs)
                    package_path = self.output / "answer/PACKAGE-RECEIPT.json"
                    package = json.loads(package_path.read_bytes())
                    package["files"] = r.c.inventory(package_path.parent, omit=("PACKAGE-RECEIPT.json",))[0]
                    write(package_path, package)
                    complete_path = self.output / "COMPLETE.json"
                    complete = json.loads(complete_path.read_bytes())
                    complete["phases"]["answer"]["receipt"] = r.c.capture(package_path)[0]
                    write(complete_path, complete)
                with self.assertRaises(ValueError): r.replay(self.output, seal())

    def test_complete_mocked_children_real_source_and_native_replay_never_redispatch(self):
        before = r.plan._inventory(self.f.root)
        result = self.execute()
        self.assertEqual(self.dispatched, [("worker", "collect"), ("review-worker", "collect"),
                                          ("worker", "answer"), ("review-worker", "answer")])
        self.assertEqual(self.server_calls, 1)
        self.assertEqual(len(self.n.f.calls), 3)
        with patch.object(r, "supervise_command", side_effect=AssertionError("Replay cannot dispatch")), \
             patch.object(r.model, "owned_server", side_effect=AssertionError("Replay cannot own model")), \
             patch.object(r, "reserve_answers", side_effect=AssertionError("Replay cannot reserve")), \
             patch.object(r.c.resolver.legacy, "fetch_http", side_effect=AssertionError("Replay cannot fetch")):
            checked = r.replay(self.output, result["receipt"]["sha256"])
        self.assertEqual(checked["status"], "verified")
        self.assertFalse(checked["model_or_http_execution_performed"])
        self.assertEqual(before, r.plan._inventory(self.f.root))
        self.assertEqual(checked["phases"]["answer"]["summary"]["questions"], 3)
        (self.output / "answer/execution-stdout.txt").write_bytes(b"substituted")
        with self.assertRaisesRegex(ValueError, "inventory"):
            r.replay(self.output, result["receipt"]["sha256"])

    def test_worker_serializes_real_immutable_server_terminal_without_redispatch(self):
        # Construct the real owner solely to exercise its immutable record API;
        # its process/HTTP entry point is never called by this fixture.
        terminals = []
        make_owner = r.model.owned_server
        @contextmanager
        def immutable_owner(spec, bindings, *, output, journal, parent_deadline):
            owner = make_owner(spec, bindings, output=output, journal=journal,
                               parent_deadline=parent_deadline)
            owner._record.update(started=True, pid=12345, server_stopped=False)
            journal.append("server_started", pid=12345)
            journal.append("server_ready", pid=12345)
            try:
                yield owner
            finally:
                owner._record.update(server_stopped=True, exit_code=0)
                terminals.append(owner.terminal_record)
                journal.append("server_terminal", **encode(owner.terminal_record))
        with patch.object(self, "owner", side_effect=immutable_owner):
            result = self.execute()
        self.assertEqual(len(terminals), 1)
        with self.assertRaises(TypeError): terminals[0]["server_stopped"] = False
        complete = json.loads((self.output / "answer/worker/COMPLETE.json").read_bytes())
        self.assertEqual(complete["server_terminal"], encode(terminals[0]))
        self.assertEqual(complete["accounting"]["generation_calls"], 3)
        self.assertEqual(len(self.n.f.calls), 3)
        with patch.object(r, "supervise_command", side_effect=AssertionError("Replay cannot dispatch")):
            self.assertEqual(r.replay(self.output, result["receipt"]["sha256"])["status"], "verified")


class NativeSupervisorTests(unittest.TestCase):
    """Real bounded Python children, with no model assets or network access."""
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_real_python_child_exit_and_streams_are_retained(self):
        limits = r.ProcessLimits(timeout_seconds=15, max_output_bytes=1024)
        result = r.supervised([sys.executable, "-I", "-B", "-c",
            "import sys; print('fictional child'); print('diagnostic',file=sys.stderr)"], limits, self.root, "execution")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.supervision["process_reaped"])
        self.assertIn(b"fictional child", (self.root / "execution-stdout.txt").read_bytes())
        self.assertIn(b"diagnostic", (self.root / "execution-stderr.txt").read_bytes())

    def test_failure_retains_deeply_immutable_native_terminal(self):
        fixture = model_fixture.ModelTests("runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        # No __enter__: construction cannot launch a server or read model bytes.
        owner = r.model.owned_server(fixture.spec, fixture.bindings, output=self.root / "server",
                                    journal=None, parent_deadline=None)
        owner._record.update(started=True, pid=12345, server_stopped=True)
        owner._record["secondary_failures"].append(dict(stage="fictional_cleanup", error_class="OSError"))
        terminal = owner.terminal_record
        with self.assertRaises(TypeError): terminal["secondary_failures"][0]["stage"] = "changed"
        journal = r.c.Journal(self.root)
        self.addCleanup(journal.close)
        error = RuntimeError("Fictional failure after native cleanup")
        r._failure(self.root, journal, error, phase="answer", server_terminal=terminal)
        failure = json.loads((self.root / "FAILURE.json").read_bytes())
        self.assertEqual(failure["server_terminal"], encode(terminal))
        self.assertEqual(failure["error_type"], "RuntimeError")
        self.assertFalse(failure["automatic_retry"])
        self.assertFalse(getattr(error, "__notes__", []))

    def test_full_source_closure_matches_selected_installed_packages(self):
        pins = r.source_pins()
        self.assertEqual(pins["experiments/litqa_recovery/run.py"], r.c.capture(r.__file__)[0]["sha256"])
        self.assertIn("experiments/litqa_recovery/admission.py", pins)
        self.assertIn("experiments/litqa_analysis/native_records.py", pins)
        self.assertNotIn("experiments/litqa_recovery/test_run.py", pins)

    def test_isolated_cli_bootstrap_keeps_frozen_installed_environment(self):
        program = "import runpy,json; scope=runpy.run_path(" + repr(str(Path(r.__file__).absolute())) + "); print(json.dumps(scope['environment']()))"
        result = r.supervised([sys.executable, "-I", "-B", "-c", program],
                             r.ProcessLimits(timeout_seconds=30, max_output_bytes=16384), self.root, "bootstrap")
        self.assertEqual(json.loads(result.stdout), r.environment())

    def test_real_python_timeout_is_reaped_and_not_repeated(self):
        limits = r.ProcessLimits(timeout_seconds=.25, max_output_bytes=1024)
        with self.assertRaises(Exception):
            r.supervised([sys.executable, "-I", "-B", "-c", "import time; print('entered',flush=True); time.sleep(10)"],
                         limits, self.root, "execution")
        terminal = json.loads((self.root / "execution-SUPERVISION.json").read_bytes())
        self.assertTrue(terminal["supervision"]["process_reaped"])
        self.assertNotEqual(terminal["supervision"]["termination_reason"], "exited")
        self.assertNotEqual(terminal["returncode"], 0)

    def test_audit_rejects_dot_dot_mutation_aliases(self):
        audit = r.WorkerAudit(inputs=[], output=self.root, code_roots=[])
        self.addCleanup(audit.stream.close)
        escape = self.root / ".." / "outside"
        for event, args in (("os.mkdir", (str(escape), 511, -1)), ("os.remove", (str(escape), -1)),
                            ("os.rename", (str(self.root / "inside"), str(escape), -1, -1))):
            with self.subTest(event=event), self.assertRaises(PermissionError): audit.hook(event, args)


if __name__ == "__main__":
    unittest.main()
