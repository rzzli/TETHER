"""CE02 regression witnesses: fictional responses, no server or model calls."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from asof.agents import Usage
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.local_model import LocalSelectionBackend, verify_backend_execution
from asof.serde import ContractError, canonical, decode, encode, fingerprint, freeze, read_json, write_json
from asof.workflow import BackendFailure, Budget, run_workflow


FIXTURES = Path(__file__).resolve().parents[1] / "src/asof/demo/v2"


class FictionalOpener:
    def __init__(self, changes=None, error=None):
        self.changes = changes or {}
        self.error = error
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        if self.error is not None:
            raise self.error
        schema = json.loads(request.data)["json_schema"]["properties"]["observation_ids"]
        response = {"content": json.dumps({"observation_ids": schema["items"]["enum"][:1]}),
                    "truncated": False, "tokens_evaluated": 50, "tokens_predicted": 1}
        response.update(self.changes)
        return io.BytesIO(canonical(response))


class CE02UsageAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.json"
        write_json(self.path, dict(schema_version=1, endpoint="http://127.0.0.1:55580",
            model_id="ce02-fictional-response-only", model_provenance={
                "weights_sha256": {"fictional": "a" * 64}, "runtime_sha256": "b" * 64},
            retrieval=dict(max_records=12, max_request_bytes=12000),
            max_output_tokens=256, timeout_seconds=2, seed=1))
        self.case = decode(Case, read_json(FIXTURES / "case.json"))

    def run_case(self, changes=None, error=None):
        backend = LocalSelectionBackend(self.path)
        backend.opener = FictionalOpener(changes, error)
        result = run_workflow(self.case, load_snapshot(FIXTURES / "snapshot.json", self.case),
                              backend, budget=Budget(max_input_tokens=100000, max_output_tokens=10000))
        return backend, result

    def archived(self, backend, result):
        return ({"schema_version": 1, "attempts": encode(backend.records)},
                encode(result.trace), encode(result.configuration))

    def test_overquote_reported_usage_survives_and_stops_dispatch(self):
        for changes, expected in (({"tokens_evaluated": 1000000}, Usage(1000000, 1, 0)),
                                  ({"tokens_predicted": 257}, Usage(50, 257, 0))):
            with self.subTest(changes=changes):
                backend, result = self.run_case(changes)
                self.assertEqual(result.calls, 1)
                self.assertEqual(backend.opener.calls, 1)
                self.assertEqual(result.status, "budget_exhausted")
                self.assertEqual(result.usage, expected)
                self.assertEqual(result.measured_usage, expected)
                self.assertEqual(result.estimated_usage, Usage(0, 0, 0))
                self.assertEqual(result.claims, ())
                self.assertEqual(sum(e["event"] == "backend_usage_contract_violated" for e in result.trace), 1)
                self.assertEqual(backend.records[0]["measured_usage"], expected)
                self.assertEqual(backend.records[0]["status"], "failed")
                verify_backend_execution(*self.archived(backend, result))

    def test_overquote_exception_carries_validated_usage(self):
        backend = LocalSelectionBackend(self.path)
        backend.opener = FictionalOpener({"tokens_evaluated": 1000000})
        from asof.agents import make_request
        from asof.contracts import Category
        store = load_snapshot(FIXTURES / "snapshot.json", self.case)
        request = make_request(self.case, Category.GENETICS, store.query(self.case, Category.GENETICS), ())
        request, _ = backend.prepare_request(request)
        with self.assertRaises(BackendFailure) as caught:
            backend.select(request)
        self.assertIsInstance(caught.exception, ContractError)
        self.assertEqual(caught.exception.usage, Usage(1000000, 1, 0))

    def test_failed_archive_rejects_quote_downgrade_of_validated_usage(self):
        backend, result = self.run_case({"tokens_evaluated": 1000000})
        document, trace, config = self.archived(backend, result)
        dispatches = [e["details"] for e in trace if e["event"] == "dispatch"]
        for account, dispatch in zip((e["details"] for e in trace if e["event"] == "attempt_accounted"), dispatches):
            account.update(usage=dispatch["reserved"], basis="quoted_upper_bound_not_measured")
        for entry in document["attempts"]:
            entry.pop("measured_usage", None)
            entry.pop("failure_kind", None)
        with self.assertRaises(ContractError):
            verify_backend_execution(document, trace, config)

    def test_failed_archive_rejects_changed_response_hash(self):
        backend, result = self.run_case({"content": "malformed"})
        document, trace, config = self.archived(backend, result)
        document["attempts"][0]["response"]["content"] = "different malformed content"
        with self.assertRaises(ContractError):
            verify_backend_execution(document, trace, config)

    def test_failed_archive_rejects_missing_or_extra_account(self):
        backend, result = self.run_case(error=TimeoutError("fictional timeout"))
        document, trace, config = self.archived(backend, result)
        accounts = [e for e in trace if e["event"] == "attempt_accounted"]
        for changed in ([e for e in trace if e is not accounts[-1]], trace + [deepcopy(accounts[-1])]):
            with self.subTest(account_count=sum(e["event"] == "attempt_accounted" for e in changed)):
                with self.assertRaises(ContractError):
                    verify_backend_execution(document, changed, config)

    def test_failed_archive_rejects_measured_usage_and_violation_tampering(self):
        backend, result = self.run_case({"tokens_evaluated": 1000000})
        document, trace, config = self.archived(backend, result)
        for field in ("tokens_evaluated", "tokens_predicted"):
            changed = deepcopy(document)
            changed["attempts"][0]["response"][field] += 1
            changed["attempts"][0]["response_sha256"] = fingerprint(changed["attempts"][0]["response"])
            with self.subTest(field=field), self.assertRaises(ContractError):
                verify_backend_execution(changed, trace, config)
        changed = deepcopy(document)
        changed["attempts"][0]["measured_usage"]["input_tokens"] = 1
        with self.assertRaises(ContractError):
            verify_backend_execution(changed, trace, config)
        changed_trace = [event for event in trace if event["event"] != "backend_usage_contract_violated"]
        with self.assertRaises(ContractError):
            verify_backend_execution(document, changed_trace, config)

    def test_failed_archive_rejects_later_dispatch_after_validated_breach(self):
        backend, result = self.run_case()
        document, trace, config = self.archived(backend, result)
        entry = document["attempts"][0]
        entry["response"]["tokens_evaluated"] = 1000000
        entry.update(status="failed", failure_kind="usage_reservation_exceeded",
                     response_sha256=fingerprint(entry["response"]), measured_usage=encode(Usage(1000000, 1, 0)))
        entry.pop("selection")
        account = next(event["details"] for event in trace if event["event"] == "attempt_accounted")
        account["usage"] = encode(Usage(1000000, 1, 0))
        trace.append({"event": "backend_usage_contract_violated", "details": {
            "category": entry["request"]["category"], "usage": encode(Usage(1000000, 1, 0))}})
        with self.assertRaisesRegex(ContractError, "dispatched after"):
            verify_backend_execution(document, trace, config)

    def test_unknown_usage_archive_rejects_wrong_quote_and_account_order(self):
        backend, result = self.run_case(error=TimeoutError("fictional timeout"))
        document, trace, config = self.archived(backend, result)
        for mutation in ("amount", "identity", "reservation"):
            changed = deepcopy(trace)
            if mutation == "reservation":
                next(event["details"] for event in changed if event["event"] == "dispatch")["reserved"]["input_tokens"] += 1
            else:
                account = next(event["details"] for event in changed if event["event"] == "attempt_accounted")
                if mutation == "amount":
                    account["usage"]["input_tokens"] += 1
                else:
                    account["attempt_id"] = "fictional-other-attempt"
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                verify_backend_execution(document, changed, config)

    def test_normal_usage_is_measured_and_archive_verifies(self):
        backend, result = self.run_case()
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.measured_usage, Usage(50 * result.calls, result.calls, 0))
        self.assertEqual(result.estimated_usage, Usage(0, 0, 0))
        verify_backend_execution(*self.archived(backend, result))

    def test_immutable_journal_forms_verify_for_success_failure_and_unknown(self):
        for changes in (None, {"tokens_evaluated": 1000000}, {"content": "not JSON"}):
            with self.subTest(changes=changes):
                backend, result = self.run_case(changes)
                document, trace, config = self.archived(backend, result)
                verify_backend_execution(document, freeze(trace), freeze(config))

    def test_malformed_content_or_counts_remain_unknown_estimates(self):
        cases = [{"content": "not JSON"}, {"truncated": True}]
        for field in ("tokens_evaluated", "tokens_predicted"):
            cases.extend({field: value} for value in (True, -1, 1.0, "12", None))
        for changes in cases:
            with self.subTest(changes=changes):
                backend, result = self.run_case(changes)
                self.assertEqual(result.measured_usage, Usage(0, 0, 0))
                self.assertGreater(result.estimated_usage.input_tokens, 0)
                self.assertTrue(all("measured_usage" not in record for record in backend.records))
                verify_backend_execution(*self.archived(backend, result))

    def test_transport_exception_retains_unknown_estimates(self):
        for error in (TimeoutError("fictional timeout"), ConnectionError("fictional failure")):
            with self.subTest(error=type(error).__name__):
                backend, result = self.run_case(error=error)
                self.assertEqual(result.measured_usage, Usage(0, 0, 0))
                self.assertEqual(result.calls, backend.opener.calls)
                self.assertGreater(result.estimated_usage.input_tokens, 0)
                verify_backend_execution(*self.archived(backend, result))


if __name__ == "__main__":
    unittest.main()
