"""Fictional per-cell accounting and stop controls; no real network or model."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, parse_json
from asof.study.source_fact_cell import run_reporting_cell
from asof.study import source_fact_cell
from asof.study.source_fact_reporting import literal_report
from asof.study.source_fact_transport import TypedReportingClient
from asof.workflow import Budget
if __package__:
    from .test_study_source_fact_reporting import packet
else:
    from test_study_source_fact_reporting import packet


PLAIN = "plain_same_model_typed_report"
ASOF = "asof_declared_two_stage_typed_report"


class Response:
    status = 200
    def __init__(self, raw):
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def geturl(self):
        return "http://127.0.0.1:55591/completion"
    def read(self, maximum):
        return self.raw[:maximum]


class Factory:
    def __init__(self, raw, *, outcomes=None, owner=True, journal=None):
        self.raw = raw
        self.outcomes = outcomes or {}
        self.owner = owner
        self.created = []
        self.opens = []
        self.journal = journal

    def __call__(self, stage, retain):
        self.created.append(stage)
        factory = self
        class Opener:
            def open(self, request, timeout):
                factory.opens.append((stage, request.data, timeout))
                if factory.journal is not None:
                    assert factory.journal.events[-1]["event"] == "dispatch"
                outcome = factory.outcomes.get(stage, {})
                if isinstance(outcome, BaseException):
                    raise outcome
                payload = parse_json(request.data)
                content = outcome.get("content", factory.raw)
                envelope = dict(content=content.decode("utf-8"), prompt=payload["prompt"],
                    model="fictional-model", truncated=False, tokens_evaluated=2,
                    tokens_predicted=3, generation_settings={k: payload[k]
                        for k in ("seed", "temperature", "n_predict", "stop", "stream")})
                envelope.update({k: v for k, v in outcome.items() if k != "content"})
                return Response(canonical(envelope))
        return TypedReportingClient("http://127.0.0.1:55591", expected_pid=1234,
            ownership_check=lambda *args: factory.owner, opener=Opener(), retain=retain)


class SourceFactCellTests(unittest.TestCase):
    def setUp(self):
        cache_root = Path(__file__).resolve().parents[1] / "data" / "cache"
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-cell-", dir=cache_root)
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to(cache_root.resolve()))
        self.journal = RunJournal(Path(self.temp.name) / "run")
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.journal.close)
        self.source = packet()
        self.raw = literal_report(self.source)

    def run_cell(self, arm=PLAIN, *, source=None, factory=None, cell_id="cell-a", **kwargs):
        if factory is None:
            factory = Factory(self.raw, journal=self.journal)
        result = run_reporting_cell(self.source if source is None else source, arm,
            cell_id=cell_id, output=self.journal.output / cell_id,
            journal=self.journal, client_factory=factory, **kwargs)
        return result, factory

    def test_deterministic_arms_make_no_calls_and_preserve_exact_output(self):
        for index, arm in enumerate(("exact_literal_assembler", "always_abstain")):
            result, factory = self.run_cell(arm, cell_id=f"control-{index}")
            self.assertEqual(result["terminal"], "returned")
            self.assertEqual(result["dispatches"], 0)
            self.assertEqual(factory.created, [])
            expected = literal_report(self.source, always_abstain=arm == "always_abstain")
            self.assertEqual(result["raw_final"], expected)
            self.assertEqual(result["measured_usage"]["input_tokens"], 0)
            self.assertEqual(result["estimated_usage"]["output_tokens"], 0)

    def test_plain_call_records_exact_files_before_open_and_accounts_measured_once(self):
        result, factory = self.run_cell()
        self.assertEqual(result["terminal"], "returned")
        self.assertEqual(result["raw_final"], self.raw)
        self.assertEqual(result["dispatches"], 1)
        self.assertEqual(result["measured_usage"]["input_tokens"], 2)
        self.assertEqual(result["measured_usage"]["output_tokens"], 3)
        self.assertEqual(result["estimated_usage"]["input_tokens"], 0)
        self.assertEqual(factory.created, ["plain"])
        stage = result["stage_records"][0]
        self.assertEqual((self.journal.output / "cell-a" / stage["files"]["raw_request"]["path"]).read_bytes(), factory.opens[0][1])
        self.assertEqual((self.journal.output / "cell-a" / "final-response.bin").read_bytes(), self.raw)
        events = read_chain(self.journal.path)
        self.assertEqual(sum(e["event"] == "dispatch" for e in events), 1)
        accounted = [e["details"] for e in events if e["event"] == "attempt_accounted"]
        self.assertEqual(len(accounted), 1)
        self.assertEqual(accounted[0]["basis"], "adapter_reported")
        self.assertTrue(accounted[0]["dispatched"])
        self.assertIsInstance(canonical(events), bytes)
        with self.assertRaises(TypeError):
            result["measured_usage"]["input_tokens"] = 99

    def test_asof_structural_proposal_then_audit_without_semantic_grading(self):
        wrong = parse_json(self.raw)
        wrong["facts"][0]["value"] = "invented-but-structurally-valid"
        factory = Factory(self.raw, outcomes={"proposal": dict(content=canonical(wrong))})
        result, factory = self.run_cell(ASOF, factory=factory)
        self.assertEqual(result["terminal"], "returned")
        self.assertEqual(factory.created, ["proposal", "audit"])
        self.assertEqual(result["dispatches"], 2)
        self.assertEqual(result["measured_usage"]["input_tokens"], 4)
        audit = parse_json(factory.opens[1][1])["prompt"]
        self.assertIn("prior_generated_not_evidence", audit)
        self.assertIn("invented-but-structurally-valid", audit)

    def test_stage_one_malformed_stops_without_audit_or_repair(self):
        factory = Factory(self.raw, outcomes={"proposal": dict(content=b"{}")})
        result, factory = self.run_cell(ASOF, factory=factory)
        self.assertEqual(result["terminal"], "malformed")
        self.assertIsNone(result["raw_final"])
        self.assertEqual(factory.created, ["proposal"])
        self.assertEqual(result["dispatches"], 1)

    def test_audit_failed_keeps_proposal_but_never_promotes_it_to_final(self):
        factory = Factory(self.raw, outcomes={"audit": TimeoutError("fictional timeout")})
        result, factory = self.run_cell(ASOF, factory=factory)
        self.assertEqual(result["terminal"], "timeout")
        self.assertIsNone(result["raw_final"])
        self.assertEqual(result["dispatches"], 2)
        self.assertEqual(result["measured_usage"]["input_tokens"], 2)
        self.assertGreater(result["estimated_usage"]["input_tokens"], 0)
        self.assertEqual(result["estimated_usage"]["output_tokens"], 2048)
        self.assertEqual(factory.created, ["proposal", "audit"])

    def test_missing_asof_is_source_only_preflight_without_client(self):
        source = packet(missing=True)
        result, factory = self.run_cell(ASOF, source=source)
        self.assertEqual(result["terminal"], "returned")
        self.assertEqual(parse_json(result["raw_final"])["status"], "insufficient_input")
        self.assertEqual(result["dispatches"], 0)
        self.assertEqual(factory.created, [])

    def test_call_or_token_budget_blocks_before_dispatch_and_does_not_bill(self):
        for index, budget in enumerate((Budget(max_calls=0), Budget(max_input_tokens=1),
                                       Budget(max_output_tokens=1))):
            result, factory = self.run_cell(cell_id=f"bounded-{index}", budget=budget)
            self.assertEqual(result["terminal"], "unexecuted")
            self.assertEqual(result["dispatches"], 0)
            self.assertEqual(factory.created, [])
            self.assertEqual(result["estimated_usage"]["input_tokens"], 0)
        result, factory = self.run_cell(ASOF, cell_id="only-proposal", budget=Budget(max_calls=1))
        self.assertEqual(result["terminal"], "failed")
        self.assertEqual(factory.created, ["proposal"])
        self.assertIsNone(result["raw_final"])

    def test_owned_listener_denial_records_zero_actual_dispatches_and_usage(self):
        result, factory = self.run_cell(factory=Factory(self.raw, owner=False))
        self.assertEqual(result["terminal"], "failed")
        self.assertEqual(result["dispatches"], 0)
        self.assertEqual(factory.opens, [])
        self.assertEqual(result["measured_usage"]["input_tokens"], 0)
        self.assertEqual(result["estimated_usage"]["input_tokens"], 0)
        accounted = [e["details"] for e in self.journal.events if e["event"] == "attempt_accounted"]
        self.assertEqual(accounted[0]["basis"], "not_dispatched")

    def test_over_quote_usage_is_preserved_and_prevents_audit(self):
        result, factory = self.run_cell(ASOF, factory=Factory(self.raw,
            outcomes={"proposal": dict(tokens_predicted=2049)}))
        self.assertEqual(result["terminal"], "failed")
        self.assertEqual(result["measured_usage"]["output_tokens"], 2049)
        self.assertEqual(result["estimated_usage"]["output_tokens"], 0)
        self.assertEqual(factory.created, ["proposal"])

    def test_write_failure_aborts_before_http_with_retained_cell_terminal(self):
        factory = Factory(self.raw)
        with patch("asof.study.source_fact_cell._write_exclusive", side_effect=OSError("fictional disk failure")):
            with self.assertRaises(OSError):
                self.run_cell(factory=factory)
        self.assertEqual(factory.opens, [])
        terminal = [e for e in self.journal.events if e["event"] == "cell_terminal"][-1]
        self.assertEqual(terminal["details"]["terminal"], "failed")
        self.assertEqual(terminal["details"]["dispatches"], 0)

    def test_interruption_retains_attempt_and_terminal_then_propagates(self):
        factory = Factory(self.raw, outcomes={"proposal": KeyboardInterrupt("fictional interrupt")})
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.run_cell(ASOF, factory=factory)
        self.assertEqual(factory.created, ["proposal"])
        terminal = [e["details"] for e in self.journal.events if e["event"] == "cell_terminal"][-1]
        self.assertEqual(terminal["terminal"], "interrupted")
        self.assertEqual(terminal["dispatches"], 1)
        self.assertGreater(terminal["estimated_usage"]["input_tokens"], 0)
        attached = caught.exception.reporting_cell_result
        self.assertEqual(attached["terminal"], "interrupted")
        self.assertEqual(attached["dispatches"], 1)
        self.assertGreater(attached["estimated_usage"]["input_tokens"], 0)
        with self.assertRaises(TypeError):
            attached["estimated_usage"]["input_tokens"] = 0

    def test_duplicate_output_and_unknown_arm_never_dispatch(self):
        self.run_cell()
        factory = Factory(self.raw)
        with self.assertRaises(FileExistsError):
            self.run_cell(factory=factory)
        with self.assertRaises(ContractError):
            self.run_cell("unknown-arm", cell_id="unknown", factory=factory)
        self.assertEqual(factory.created, [])

    def test_deadline_includes_rendering_and_each_stage_without_retry(self):
        values = iter((0, 0, 301, 301, 301, 301, 301, 301))
        result, factory = self.run_cell(monotonic=lambda: next(values))
        self.assertEqual(result["terminal"], "unexecuted")
        self.assertEqual(factory.created, [])
        self.assertGreaterEqual(result["elapsed_seconds"], 300)

    def test_deadline_expiring_during_factory_or_request_retention_never_opens(self):
        clock = [0]
        factory = Factory(self.raw)
        def slow_factory(stage, retain):
            client = factory(stage, retain)
            clock[0] = 301
            return client
        result, _ = self.run_cell(factory=slow_factory, monotonic=lambda: clock[0])
        self.assertEqual(result["terminal"], "unexecuted")
        self.assertEqual(factory.opens, [])
        clock[0] = 0
        factory = Factory(self.raw)
        original_write = source_fact_cell._write_exclusive
        def slow_write(path, raw):
            proof = original_write(path, raw)
            if path.name == "raw-request.bin":
                clock[0] = 301
            return proof
        with patch("asof.study.source_fact_cell._write_exclusive", side_effect=slow_write):
            result, _ = self.run_cell(cell_id="expired-retention", factory=factory,
                                      monotonic=lambda: clock[0])
        self.assertEqual(result["terminal"], "unexecuted")
        self.assertEqual(result["dispatches"], 0)
        self.assertEqual(factory.opens, [])

    def test_postdispatch_retention_failure_still_accounts_actual_usage_and_stops(self):
        factory = Factory(self.raw)
        original_write = source_fact_cell._write_exclusive
        def broken_content(path, raw):
            if path.name == "content.bin":
                raise OSError("fictional content retention failure")
            return original_write(path, raw)
        with patch("asof.study.source_fact_cell._write_exclusive", side_effect=broken_content):
            with self.assertRaises(OSError):
                self.run_cell(ASOF, factory=factory)
        self.assertEqual(factory.created, ["proposal"])
        terminal = [e["details"] for e in self.journal.events if e["event"] == "cell_terminal"][-1]
        self.assertEqual(terminal["dispatches"], 1)
        self.assertEqual(terminal["measured_usage"]["output_tokens"], 3)
        self.assertEqual(terminal["estimated_usage"]["output_tokens"], 0)
        accounted = [e["details"] for e in self.journal.events if e["event"] == "attempt_accounted"][-1]
        self.assertFalse(accounted["retention_complete"])

    def test_final_clock_sample_cannot_publish_a_late_completed_cell(self):
        values = iter((0, 0, 299, 301))
        result, _ = self.run_cell("always_abstain", monotonic=lambda: next(values))
        self.assertEqual(result["terminal"], "timeout")
        self.assertEqual(result["elapsed_seconds"], 301)
        terminal = [e["details"] for e in self.journal.events if e["event"] == "cell_terminal"][-1]
        self.assertEqual(terminal["terminal"], "timeout")

    def test_final_clock_interruption_is_recorded_as_interrupted(self):
        values = iter((0, 0, 0))
        def clock():
            try:
                return next(values)
            except StopIteration:
                raise KeyboardInterrupt("fictional final clock interruption")
        with self.assertRaises(KeyboardInterrupt):
            self.run_cell("always_abstain", monotonic=clock)
        terminal = [e["details"] for e in self.journal.events if e["event"] == "cell_terminal"][-1]
        self.assertEqual(terminal["terminal"], "interrupted")

    def test_terminal_journal_failure_attaches_known_usage_and_exact_final_bytes(self):
        original_append = self.journal.append
        def broken_terminal(event, **details):
            if event == "cell_terminal":
                raise OSError("fictional terminal write failure")
            return original_append(event, **details)
        with patch.object(self.journal, "append", side_effect=broken_terminal):
            with self.assertRaises(OSError) as caught:
                self.run_cell()
        attached = caught.exception.reporting_cell_result
        self.assertEqual(attached["terminal"], "failed")
        self.assertEqual(attached["raw_final"], self.raw)
        self.assertEqual(attached["dispatches"], 1)
        self.assertEqual(attached["measured_usage"]["input_tokens"], 2)
        self.assertEqual(attached["measured_usage"]["output_tokens"], 3)
        self.assertEqual(attached["estimated_usage"]["input_tokens"], 0)
        self.assertEqual(attached["stage_records"][0]["stage"], "plain")
        self.assertFalse(any(e["event"] == "cell_terminal" for e in self.journal.events))

    def test_exception_attachment_refusal_preserves_original_failure(self):
        class RefusesAttachment(OSError):
            def __setattr__(self, name, value):
                if name == "reporting_cell_result":
                    raise AttributeError("fictional attachment refusal")
                return super().__setattr__(name, value)
        original = RefusesAttachment("fictional factory failure")
        def broken_factory(stage, retain):
            raise original
        with self.assertRaises(RefusesAttachment) as caught:
            self.run_cell(factory=broken_factory)
        self.assertIs(caught.exception, original)
        self.assertEqual(self.journal.events[-1]["event"], "cell_terminal")


if __name__ == "__main__":
    unittest.main()
