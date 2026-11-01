"""Offline P04b checks: fictional literals and injected non-network transport."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.journal import read_chain
from asof.serde import ContractError, canonical, parse_json

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("p04b_qualification_under_test", HERE / "qualify_prompt.py")
Q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)


def protocol():
    return parse_json((HERE / "PROTOCOL-DRAFT-v1.json").read_bytes())


def temporary_directory():
    return tempfile.TemporaryDirectory(prefix=".p04b-test-", dir=HERE)


class FakeServer:
    p04b_mock_only = True
    pid = 1234

    def __init__(self, *, cleanup=True, owned=True, startup_error=None):
        self.cleanup, self.owned, self.startup_error = cleanup, owned, startup_error
        self.stopped, self.entered = False, False
        self.ready_checks, self.owner_checks = 0, 0

    def __enter__(self):
        self.entered = True
        if self.startup_error:
            self.stopped = self.cleanup
            raise self.startup_error
        return self

    def __exit__(self, *_):
        self.stopped = self.cleanup

    def assert_ready(self):
        self.ready_checks += 1
        if not self.owned:
            raise ContractError("Mock owner unavailable")

    def owner(self, pid, host, port):
        self.owner_checks += 1
        return self.owned and pid == self.pid and host == "127.0.0.1" and port == 55591

    @property
    def terminal_record(self):
        return dict(started=self.entered, server_stopped=self.stopped, exit_code=0 if self.stopped else None)


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return "http://127.0.0.1:55591/completion"

    def read(self, maximum):
        return self.body[:maximum]


class FakeOpener:
    p04b_mock_only = True

    def __init__(self, control, calls, mode="valid"):
        self.control, self.calls, self.mode = control, calls, mode

    def open(self, request, *, timeout):
        payload = parse_json(request.data)
        self.calls.append(dict(control_id=self.control["control_id"], payload=payload, timeout=timeout))
        if self.mode == "timeout":
            raise TimeoutError("Fictional timeout")
        if self.mode == "unknown":
            return FakeResponse(b"not-json")
        candidate = deepcopy(self.control["expected"])
        if self.mode == "source_id":
            candidate["facts"][0]["source"] = candidate["facts"][0]["source"]["source_id"]
        if self.mode == "wrong_type":
            candidate["facts"][1]["value"] = str(candidate["facts"][1]["value"])
        native = dict(content=canonical(candidate).decode(), prompt=payload["prompt"], model="fictional-mock",
                      generation_settings={key: payload[key] for key in ("seed", "temperature", "n_predict", "stop", "stream")},
                      tokens_evaluated=12, tokens_predicted=17, truncated=False, stop=True,
                      stop_type="limit" if self.mode == "limit" else "eos", stopping_word="")
        return FakeResponse(canonical(native))


class QualificationTests(unittest.TestCase):
    def run_mock(self, output, *, server=None, mode="valid", clock=None):
        server = server or FakeServer()
        calls = []
        kwargs = dict(server=server, opener_factory=lambda control: FakeOpener(control, calls, mode))
        if clock is not None:
            kwargs["monotonic"] = clock
        return Q.exercise_mock(protocol(), output, **kwargs), calls, server

    def test_two_originals_expected_from_native_input(self):
        controls = Q.controls()
        self.assertEqual([len(c["expected"]["facts"]) for c in controls], [2, 8])
        self.assertEqual(canonical(controls), canonical(Q.controls()))
        for control in controls:
            self.assertTrue(control["original_input"]["artificial"])
            self.assertEqual(control["original_sha256"], Q.fingerprint(control["original_input"]))
            row = control["original_input"]["rows"][0]
            for fact, slot in zip(control["expected"]["facts"], control["view"]["fact_skeleton"]):
                original = row[slot["field"]]
                self.assertEqual(fact["source"], slot["source"])
                self.assertEqual(fact["value"], None if original in (None, "") else original)
                if original not in (None, ""):
                    self.assertIs(type(fact["value"]), type(original))
        self.assertIs(controls[1]["expected"]["facts"][3]["value"], False)
        self.assertEqual(controls[1]["expected"]["facts"][4]["value"], ["b", "a"])

    def test_prompt_only_source_and_value_free_slots(self):
        for control in Q.controls():
            rendered = Q.prompt(control)
            self.assertIn(Q._GUIDE + Q.REFINEMENT, rendered)
            self.assertIn("source member is an OBJECT", rendered)
            self.assertIn("Never emit partial with facts=[]", rendered)
            self.assertIn("row_group:nonnegative integer", rendered)
            payload = parse_json(rendered.split("<|im_start|>user\n", 1)[1].split("<|im_end|>", 1)[0].encode())
            self.assertEqual(set(payload), {"source_input", "stage"})
            self.assertEqual(payload["stage"], "plain")
            self.assertNotIn("expected", payload["source_input"])
            self.assertTrue(all("value" not in slot for slot in payload["source_input"]["fact_skeleton"]))
            self.assertLessEqual(len(rendered.encode()) + 2048 + 32, 16384)
        control = Q.controls()[1]
        original_prompt = Q.prompt(control)
        original_request = canonical(Q.prepare_completion(original_prompt, 2048, 0))
        control["expected"]["facts"][0]["source"]["locator"]["pointer"] = "/fictional-changed"
        control["expected"]["facts"][4]["value"].append("fictional-extra")
        control["expected"]["facts"][5]["value"]["mark"] = "fictional-changed"
        self.assertEqual(Q.prompt(control), original_prompt)
        self.assertEqual(canonical(Q.prepare_completion(Q.prompt(control), 2048, 0)), original_request)

    def test_actual_draft_fixtures_and_prompt_pins(self):
        draft = protocol()
        Q.validate(draft)
        self.assertEqual(canonical(draft["controls"]), canonical(Q.controls()))
        self.assertFalse(draft["execution_allowed"])
        self.assertEqual(draft["status"], "DRAFT")
        for control in Q.controls():
            self.assertEqual(draft["prompt_sha256"][control["control_id"]], Q.digest(Q.prompt(control).encode()))

    def test_fixture_and_schedule_mutations_rejected(self):
        for mutate in (
            lambda p: p["controls"][0]["original_input"]["rows"][0].update(toy_count=8),
            lambda p: p["controls"][0]["expected"]["facts"][0].update(value="other"),
            lambda p: p["scheduled_cells"].append(deepcopy(p["scheduled_cells"][0])),
            lambda p: p["scheduled_cells"][0].update(stage="proposal"),
            lambda p: p["scheduled_cells"].reverse(),
        ):
            with self.subTest(mutate=mutate):
                draft = protocol()
                mutate(draft)
                with self.assertRaises(ContractError):
                    Q.validate(draft)

    def test_literal_caps_wire_runtime_mutations_rejected(self):
        for key, value in (("seed", 1), ("seed", False), ("maximum_output_tokens_per_call", 4096),
                           ("setup_seconds", 901), ("startup_seconds", 181), ("wire_format", "other"),
                           ("retry_policy", "once"), ("fallback_policy", "sequential")):
            with self.subTest(key=key, value=value):
                draft = protocol()
                draft[key] = value
                with self.assertRaises(ContractError):
                    Q.validate(draft)
        for group, key, value in (("budgets_per_cell", "max_calls", 2), ("budgets_per_cell", "max_cost_usd", 1),
                                  ("server", "port", 55592), ("model", "revision", "changed")):
            draft = protocol()
            draft[group][key] = value
            with self.assertRaises(ContractError):
                Q.validate(draft)

    def test_dry_qualification_has_no_server_or_http(self):
        with patch.object(Q, "OwnedServer", side_effect=AssertionError("Must not instantiate")), \
             patch.object(Q, "TypedReportingClient", side_effect=AssertionError("Must not instantiate")):
            result = Q.dry_qualification(protocol())
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(result["server_port"], 55591)
        self.assertEqual(result["pinned_assets"], 55)

    def test_draft_execute_denied_before_side_effects(self):
        with patch.object(Q, "OwnedServer", side_effect=AssertionError("Must not instantiate")), \
             patch.object(Q, "TypedReportingClient", side_effect=AssertionError("Must not instantiate")), \
             patch.object(Q, "BoundedJournal", side_effect=AssertionError("Must not reserve")):
            with self.assertRaises(ContractError):
                Q.main(["--execute"])

    def test_existing_adapter_source_and_status_invariants(self):
        control = Q.controls()[0]
        for mutate in (
            lambda out: out["facts"][0].update(source=out["facts"][0]["source"]["source_id"]),
            lambda out: out.update(status="partial", facts=[], reason="Fictional missing"),
            lambda out: out["facts"][0]["source"]["locator"].update(pointer=123),
        ):
            candidate = deepcopy(control["expected"])
            mutate(candidate)
            result = Q.grade(control, canonical(candidate))
            self.assertEqual(result["terminal"], "malformed")
            self.assertFalse(result["passed"])

    def test_exact_native_values_and_source_binding_required(self):
        control = Q.controls()[0]
        for mutate in (
            lambda out: out["facts"][1].update(value="7"),
            lambda out: out["facts"][0]["source"].update(sha256="a" * 64),
            lambda out: out["facts"].reverse(),
        ):
            candidate = deepcopy(control["expected"])
            mutate(candidate)
            self.assertFalse(Q.grade(control, canonical(candidate))["passed"])

    def test_success_exact_two_calls_plain_seed_cap_cleanup_order(self):
        with temporary_directory() as temporary:
            output = Path(temporary) / "attempt"
            server = FakeServer()
            real_grade = Q.grade
            with patch.object(Q, "grade", side_effect=lambda *args: real_grade(*args) if server.stopped else self.fail("Grading before cleanup")):
                report, calls, _ = self.run_mock(output, server=server)
            self.assertEqual(report["status"], "mock_passed")
            self.assertEqual(report["actual_calls"], 2)
            self.assertEqual([c["control_id"] for c in calls], ["fictional-two", "fictional-eight"])
            self.assertEqual(server.owner_checks, 2)
            self.assertTrue(all(c["payload"]["n_predict"] == 2048 and c["payload"]["seed"] == 0
                                and c["payload"]["temperature"] == 0 for c in calls))
            self.assertTrue(all(0 < c["timeout"] <= 300 for c in calls))
            self.assertTrue(all(c["measured_usage"] == dict(input_tokens=12, output_tokens=17, cost_usd=0.0)
                                and not c["usage_unknown"] for c in report["cells"]))
            events = read_chain(output / "journal.jsonl")
            names = [e["event"] for e in events]
            self.assertEqual(names.count("attempt"), 2)
            self.assertEqual(names.count("transport_terminal"), 2)
            self.assertLess(names.index("generation_ceased"), names.index("graded"))

    def test_unknown_envelope_retained_estimate_not_zero_and_no_retry(self):
        with temporary_directory() as temporary:
            output = Path(temporary) / "attempt"
            report, calls, _ = self.run_mock(output, mode="unknown")
            self.assertEqual(len(calls), 1)
            first, second = report["cells"]
            self.assertEqual(first["terminal"], "failed")
            self.assertTrue(first["usage_unknown"])
            self.assertIsNone(first["measured_usage"])
            self.assertEqual(first["estimated_upper_usage"]["output_tokens"], 2048)
            self.assertGreater(first["estimated_upper_usage"]["input_tokens"], 0)
            self.assertEqual(second["terminal"], "unexecuted")
            self.assertEqual((output / first["cell_id"] / "raw-envelope.bin").read_bytes(), b"not-json")
            self.assertFalse(report["model_scale_allowed"])

    def test_timeout_retained_and_second_cell_unexecuted(self):
        with temporary_directory() as temporary:
            report, calls, _ = self.run_mock(Path(temporary) / "attempt", mode="timeout")
        self.assertEqual(len(calls), 1)
        self.assertEqual([c["terminal"] for c in report["cells"]], ["timeout", "unexecuted"])
        self.assertTrue(report["cells"][0]["usage_unknown"])

    def test_stop_limit_never_graded_or_rescued(self):
        with temporary_directory() as temporary:
            output = Path(temporary) / "attempt"
            with patch.object(Q, "grade", side_effect=AssertionError("Limited output must not grade")):
                report, calls, _ = self.run_mock(output, mode="limit")
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["cells"][0]["terminal"], "failed")
            self.assertFalse(report["cells"][0]["usage_unknown"])
            self.assertTrue((output / report["cells"][0]["cell_id"] / "content.bin").exists())

    def test_malformed_source_retained_without_binding_repair(self):
        with temporary_directory() as temporary:
            output = Path(temporary) / "attempt"
            report, calls, _ = self.run_mock(output, mode="source_id")
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(c["terminal"] == "malformed" and not c["passed"] for c in report["cells"]))
            for cell in report["cells"]:
                retained = parse_json((output / cell["cell_id"] / "content.bin").read_bytes())
                self.assertIs(type(retained["facts"][0]["source"]), str)

    def test_cleanup_not_affirmed_blocks_all_grading(self):
        with temporary_directory() as temporary:
            with patch.object(Q, "grade", side_effect=AssertionError("Cleanup gate violated")):
                report, calls, _ = self.run_mock(Path(temporary) / "attempt", server=FakeServer(cleanup=False))
        self.assertEqual(len(calls), 2)
        self.assertFalse(report["grading_allowed"])
        self.assertTrue(all(not c["passed"] for c in report["cells"]))

    def test_startup_and_ownership_failure_retains_unexecuted_cells(self):
        for server in (FakeServer(startup_error=TimeoutError("Fictional startup")), FakeServer(owned=False)):
            with self.subTest(server=server), temporary_directory() as temporary:
                report, calls, _ = self.run_mock(Path(temporary) / "attempt", server=server)
                self.assertEqual(calls, [])
                self.assertEqual(report["actual_calls"], 0)
                self.assertTrue(all(c["terminal"] == "unexecuted" for c in report["cells"]))
                self.assertTrue(report["errors"])

    def test_exclusive_outputs_and_explicit_mock_requirements(self):
        with temporary_directory() as temporary:
            output = Path(temporary) / "attempt"
            self.run_mock(output)
            original = (output / "report.json").read_bytes()
            with self.assertRaises(FileExistsError):
                self.run_mock(output)
            self.assertEqual((output / "report.json").read_bytes(), original)
            with self.assertRaises(ContractError):
                Q.exercise_mock(protocol(), Path(temporary) / "denied", server=object(), opener_factory=lambda _: None)
            self.assertFalse((Path(temporary) / "denied").exists())

    def test_bounded_journal_rejects_oversized_and_excess_events(self):
        with temporary_directory() as temporary:
            journal = Q.BoundedJournal(Path(temporary) / "attempt")
            try:
                with self.assertRaises(ContractError):
                    journal.append("oversized", text="x" * 65537)
                with patch.object(Q, "JOURNAL_MAX_EVENTS", 4):
                    for _ in range(3):
                        journal.append("finite")
                    with self.assertRaises(ContractError):
                        journal.append("overflow")
                with patch.object(Q, "JOURNAL_MAX_BYTES", journal._durable_size + 1):
                    with self.assertRaises(ContractError):
                        journal.append("byte_bound")
            finally:
                journal.close()

    def test_production_guards_deny_before_output_server_or_transport(self):
        with temporary_directory() as temporary:
            draft = protocol()
            draft_path = Path(temporary) / "draft.json"
            draft_path.write_bytes(canonical(draft))
            ready = deepcopy(draft)
            ready.update(status="READY", execution_allowed=True)
            ready_path = Path(temporary) / "ready.json"
            ready_path.write_bytes(canonical(ready))
            with patch.object(Q, "BoundedJournal", side_effect=AssertionError("Must not reserve")), \
                 patch.object(Q, "OwnedServer", side_effect=AssertionError("Must not launch")), \
                 patch.object(Q, "TypedReportingClient", side_effect=AssertionError("Must not dispatch")):
                for path, pin, execute in (
                    (draft_path, Q.digest(draft_path.read_bytes()), True),
                    (ready_path, "0" * 64, True),
                    (ready_path, Q.digest(ready_path.read_bytes()), False),
                ):
                    with self.subTest(path=path, execute=execute), self.assertRaises(ContractError):
                        Q.run_qualification(path, pin, Path(temporary) / "denied", execute=execute)
            self.assertFalse((Path(temporary) / "denied").exists())

    def test_deadline_reservation_retention_and_actual_dispatch_bounds(self):
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

        with self.subTest(case="expired_opener"):
            clock, calls = Clock(), []
            clock.now = 300
            opener = Q.DeadlineOpener(FakeOpener(Q.controls()[0], calls), 300, clock)
            with self.assertRaises(ContractError):
                opener.open(object(), timeout=100)
            self.assertEqual(calls, [])

        with self.subTest(case="remaining_timeout"):
            clock, guard = Clock(), Q.helpers()
            real_write = guard.write_bytes

            def delayed_write(path, raw):
                proof = real_write(path, raw)
                if Path(path).name == "raw-request.bin":
                    clock.now += 250
                return proof

            with temporary_directory() as temporary, patch.object(Q, "helpers", return_value=guard), \
                 patch.object(guard, "write_bytes", side_effect=delayed_write):
                report, calls, _ = self.run_mock(Path(temporary) / "attempt", clock=clock)
            self.assertEqual(report["actual_calls"], 2)
            self.assertTrue(all(call["timeout"] == 50 for call in calls))

        with self.subTest(case="expired_before_dispatch"):
            clock, guard = Clock(), Q.helpers()
            real_write = guard.write_bytes

            def expired_write(path, raw):
                proof = real_write(path, raw)
                if Path(path).name == "raw-request.bin":
                    clock.now += 300
                return proof

            with temporary_directory() as temporary, patch.object(Q, "helpers", return_value=guard), \
                 patch.object(guard, "write_bytes", side_effect=expired_write):
                report, calls, _ = self.run_mock(Path(temporary) / "attempt", clock=clock)
            self.assertEqual(calls, [])
            self.assertEqual(report["actual_calls"], 0)
            self.assertEqual(report["cells"][1]["terminal"], "unexecuted")
            self.assertFalse(report["grading_allowed"])

        with self.subTest(case="retention_failed_after_dispatch"):
            guard = Q.helpers()
            real_write = guard.write_bytes

            def broken_write(path, raw):
                if Path(path).name == "raw-envelope.bin":
                    raise OSError("Fictional evidence retention failure")
                return real_write(path, raw)

            with temporary_directory() as temporary, patch.object(Q, "helpers", return_value=guard), \
                 patch.object(guard, "write_bytes", side_effect=broken_write), \
                 patch.object(Q, "grade", side_effect=AssertionError("Retention failure must block grading")):
                report, calls, _ = self.run_mock(Path(temporary) / "attempt")
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["actual_calls"], 1)
            self.assertEqual(report["cells"][1]["terminal"], "unexecuted")
            self.assertFalse(report["grading_allowed"])
            self.assertTrue(report["errors"])

        with self.subTest(case="final_receipt_failed"):
            guard = Q.helpers()
            real_write = guard.write_bytes

            def missing_receipt(path, raw):
                if Path(path).name == "receipt.json":
                    raise OSError("Fictional final receipt failure")
                return real_write(path, raw)

            with temporary_directory() as temporary, patch.object(Q, "helpers", return_value=guard), \
                 patch.object(guard, "write_bytes", side_effect=missing_receipt):
                output = Path(temporary) / "attempt"
                report, calls, _ = self.run_mock(output)
                self.assertEqual(len(calls), 2)
                self.assertEqual(report["status"], "failed_branch_closed")
                self.assertEqual(parse_json((output / "failure-receipt.json").read_bytes())["status"], "failed_branch_closed")
                self.assertFalse((output / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
