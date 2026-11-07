"""Adversarial producer fixtures for the additional TETHER v0.4.1 boundary."""
from contextlib import redirect_stderr
from dataclasses import replace
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether_engine.agents import ExtractiveBackend, Selection, Usage
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category
from tether_engine.ledger import EvidenceLedger
from tether_engine.scorer import ScorerArtifact, abstain
from tether_engine.serde import ContractError, decode, encode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import Budget, run_workflow
from tether import _cli, _presentation as layer


class SemanticBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tether-semantic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(ROOT / "src/tether_engine/demo/v2", self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.fixture / "scorer.json"))
        self.store = load_snapshot(self.fixture / "snapshot.json", self.case)
        self.result = self.run_case()

    def run_case(self, backend=None, **kwargs):
        return run_workflow(self.case, self.store, backend or ExtractiveBackend(), self.model, **kwargs)

    def write(self, result=None, name="run"):
        target = self.root / name
        digest = write_run(target, result or self.result, self.store, self.model)
        return target, digest

    def rechain(self, events):
        previous = None
        for index, event in enumerate(events):
            event.pop("sha256", None)
            event["sequence"] = index
            event["previous_sha256"] = previous
            event["sha256"] = previous = fingerprint(event)
        return events

    def test_real_completed_run_is_reconstructed(self):
        target, digest = self.write()
        result = layer.verify_engine(target, digest)
        self.assertEqual(result["tether_semantics"]["dossier_reconstruction"], "verified")
        self.assertTrue(result["external_anchor_checked"])

    def test_failed_absent_and_unknown_coverage_statuses_reject(self):
        for status in ("failed", "biologically_absent", "invented_status", "disabled"):
            with self.subTest(status=status):
                coverage = encode(self.result.coverage)
                coverage["genetics"]["status"] = status
                target, digest = self.write(replace(self.result, coverage=coverage), status)
                # A valid original producer receipt demonstrates the legacy gap.
                self.assertEqual(verify_run(target, digest)["semantic_consistency"], "verified")
                with self.assertRaisesRegex(ContractError, "coverage status"):
                    layer.verify_engine(target, digest)

    def test_review_selection_cannot_differ_from_committed_claims(self):
        events = encode(self.result.trace)
        next(e for e in events if e["event"] == "review")["details"]["selected"] = []
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "claim was not selected"):
            layer.verify_engine(target, digest)

    def test_claims_cannot_follow_rejected_review(self):
        events = encode(self.result.trace)
        next(e for e in events if e["event"] == "review")["details"]["problems"] = ["fictional rejection"]
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "accepted active review"):
            layer.verify_engine(target, digest)

    def test_review_usage_must_match_accounted_usage(self):
        events = encode(self.result.trace)
        next(e for e in events if e["event"] == "review")["details"]["usage"]["output_tokens"] = 1
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "review/accounted usage"):
            layer.verify_engine(target, digest)

    def test_resealed_unbound_dossier_prose_rejects(self):
        target, original = self.write()
        with (target / "dossier.md").open("ab") as stream:
            stream.write(b"\nUnbound fictional biological conclusion.\n")
        receipt = read_json(target / "receipt.json")
        receipt["outputs"]["dossier.md"] = sha256_file(target / "dossier.md")
        write_json(target / "receipt.json", receipt)
        with self.assertRaisesRegex(ContractError, "dossier prose"):
            layer.verify_engine(target, sha256_file(target / "receipt.json"))
        with self.assertRaisesRegex(ContractError, "anchored receipt"):
            layer.verify_engine(target, original)

    def test_valid_partial_fatal_and_interrupted_runs_remain_verifiable(self):
        for error, status in ((TimeoutError, "partial"), (RecursionError, "partial"),
                              (OSError, "failed"), (KeyboardInterrupt, "interrupted")):
            class Failing(ExtractiveBackend):
                def select(self, request):
                    raise error("fictional")
            result = self.run_case(Failing())
            self.assertEqual(result.status, status)
            target, digest = self.write(result, error.__name__)
            self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_fatal_failure_cannot_continue_to_later_specialists(self):
        class Failing(ExtractiveBackend):
            def select(self, request):
                raise TimeoutError("fictional")
        result = self.run_case(Failing())
        events = encode(result.trace)
        next(e for e in events if e["event"] == "backend_failed")["details"]["error_class"] = "OSError"
        # An impossible continued execution can still be sealed by the frozen
        # producer; the additional boundary must reject before dossier replay.
        events[-1]["details"]["status"] = "failed"
        target, digest = self.write(replace(result, status="failed", trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "terminal failure"):
            layer.verify_engine(target, digest)

    def test_no_observed_and_disabled_categories_remain_valid(self):
        result = self.run_case(disabled=tuple(Category))
        target, digest = self.write(result)
        self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_request_denial_and_usage_overage_remain_valid(self):
        denied = self.run_case(budget=Budget(max_calls=0))
        target, digest = self.write(denied, "denied")
        self.assertIn("tether_semantics", layer.verify_engine(target, digest))
        class Overage(ExtractiveBackend):
            def select(self, request):
                return Selection((), Usage(1, 0, 0))
        target, digest = self.write(self.run_case(Overage()), "overage")
        self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_deadline_during_claim_commit_preserves_partial_prefix(self):
        clock = [0.0]
        original = EvidenceLedger.append
        def delayed(ledger, category, observation_id):
            claim = original(ledger, category, observation_id)
            clock[0] = 2.0
            return claim
        with patch("tether_engine.workflow.time.monotonic", side_effect=lambda: clock[0]), patch.object(EvidenceLedger, "append", delayed):
            result = self.run_case(budget=Budget(max_seconds=1))
        target, digest = self.write(result)
        self.assertEqual(len(result.claims), 1)
        self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_deadline_after_response_preserves_failed_category(self):
        clock = [0.0]
        class Slow(ExtractiveBackend):
            def select(self, request):
                clock[0] = 2.0
                return super().select(request)
        with patch("tether_engine.workflow.time.monotonic", side_effect=lambda: clock[0]):
            result = self.run_case(Slow(), budget=Budget(max_seconds=1))
        target, digest = self.write(result)
        self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_quote_failures_and_empty_retrieval_remain_valid(self):
        class BadQuote(ExtractiveBackend):
            def quote(self, request):
                raise ValueError("fictional")
        class Empty(ExtractiveBackend):
            def prepare_request(self, request):
                return replace(request, evidence=()), {"selected_ids": [], "reason": "fictional empty retrieval"}
        for name, backend in (("quote", BadQuote()), ("retrieval", Empty())):
            target, digest = self.write(self.run_case(backend), name)
            self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_rejected_review_retry_and_valid_empty_selection(self):
        class Retry(ExtractiveBackend):
            def __init__(self):
                self.seen = set()
            def select(self, request):
                if request.category not in self.seen:
                    self.seen.add(request.category)
                    return Selection(("fictional-not-admitted",), Usage(0, 0, 0))
                return super().select(request)
        class Empty(ExtractiveBackend):
            def select(self, request):
                return Selection((), Usage(0, 0, 0))
        for name, backend in (("retry", Retry()), ("empty", Empty())):
            target, digest = self.write(self.run_case(backend), name)
            self.assertIn("tether_semantics", layer.verify_engine(target, digest))

    def test_current_cli_rejects_bad_legacy_run_without_dispatch(self):
        coverage = encode(self.result.coverage)
        coverage["genetics"]["status"] = "failed"
        target, digest = self.write(replace(self.result, coverage=coverage))
        with patch.object(layer, "invoke_engine", side_effect=AssertionError("no redispatch")), redirect_stderr(io.StringIO()):
            self.assertEqual(_cli.main(["verify", "--run-dir", str(target), "--receipt-sha256", digest]), 2)

    def test_outer_cannot_finalize_inconsistent_engine_producer(self):
        coverage = encode(self.result.coverage)
        coverage["genetics"]["status"] = "failed"
        bad = replace(self.result, coverage=coverage)
        calls = []
        def producer(argv):
            calls.append(argv)
            write_run(Path(argv[-1]), bad, self.store, self.model)
            return layer.EngineResult(0)
        target = self.root / "outer"
        with self.assertRaisesRegex(ContractError, "coverage status"):
            layer.create_outer(target, ["demo", "--output", str(target)], engine=producer)
        self.assertEqual(len(calls), 1)
        self.assertTrue((target / layer.FAILURE).is_file())
        self.assertFalse((target / layer.RECEIPT).exists())

    def test_review_selection_must_be_within_recorded_bounded_request(self):
        class Bounded(ExtractiveBackend):
            def prepare_request(self, request):
                return request, {"selected_ids": [item.observation_id for item in request.evidence]}
        result = self.run_case(Bounded())
        events, coverage = encode(result.trace), encode(result.coverage)
        first = next(event for event in events if event["event"] == "bounded_retrieval"
                     and len(event["details"]["selected_ids"]) > 1)
        first["details"]["selected_ids"] = first["details"]["selected_ids"][1:]
        coverage[first["details"]["category"]]["retrieval"]["selected_ids"] = first["details"]["selected_ids"]
        target, digest = self.write(replace(result, trace=self.rechain(events), coverage=coverage))
        with self.assertRaisesRegex(ContractError, "outside the bounded request"):
            layer.verify_engine(target, digest)

    def test_terminal_status_requires_matching_execution_evidence(self):
        prediction = abstain(self.case, "run_incomplete", self.model)
        for status in ("invented_status", "budget_exhausted", "partial"):
            events = encode(self.result.trace)
            events[-1]["details"].update(status=status, prediction_sha256=fingerprint(prediction))
            target, digest = self.write(replace(self.result, status=status, prediction=prediction,
                                               trace=self.rechain(events)), status)
            with self.assertRaisesRegex(ContractError, "terminal status|lacks|partial run"):
                layer.verify_engine(target, digest)

    def test_backend_failure_is_terminal_for_its_category(self):
        events = encode(self.result.trace)
        index = next(i for i, event in enumerate(events) if event["event"] == "review")
        events.insert(index, {"event": "backend_failed", "details": {
            "category": events[index]["details"]["category"], "error_class": "TimeoutError"}})
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "terminal backend failure"):
            layer.verify_engine(target, digest)

    def test_quote_failure_is_terminal_for_its_category(self):
        events = encode(self.result.trace)
        index = next(i for i, event in enumerate(events) if event["event"] == "dispatch")
        events.insert(index, {"event": "backend_quote_failed", "details": {
            "category": events[index]["details"]["category"], "error_class": "ValueError"}})
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "terminal backend failure"):
            layer.verify_engine(target, digest)

    def test_accounted_attempt_requires_review_or_terminal_disposition(self):
        events = encode(self.result.trace)
        review = next(i for i, event in enumerate(events) if event["event"] == "review")
        del events[review]
        # No accepted review can license the immediately following claims.
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "accepted active review|disposition"):
            layer.verify_engine(target, digest)

    def test_attempt_numbers_cannot_skip_first_attempt(self):
        events = encode(self.result.trace)
        dispatch = next(event for event in events if event["event"] == "dispatch")
        old = dispatch["details"]["attempt_id"]
        new = old[:-1] + "2"
        dispatch["details"]["attempt"] = 2
        for event in events:
            if event["details"].get("attempt_id") == old:
                event["details"]["attempt_id"] = new
        target, digest = self.write(replace(self.result, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "attempt sequence"):
            layer.verify_engine(target, digest)

    def test_disabled_review_retries_cannot_be_forged(self):
        class Retry(ExtractiveBackend):
            def __init__(self):
                self.seen = set()
            def select(self, request):
                if request.category not in self.seen:
                    self.seen.add(request.category)
                    return Selection(("fictional-not-admitted",), Usage(0, 0, 0))
                return super().select(request)
        result = self.run_case(Retry())
        config, events = encode(result.configuration), encode(result.trace)
        config["review_enabled"] = False
        next(e for e in events if e["event"] == "plan")["details"]["configuration"] = config
        target, digest = self.write(replace(result, configuration=config, trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "terminal backend failure"):
            layer.verify_engine(target, digest)

    def test_known_timeout_cannot_be_reported_as_interruption(self):
        class Timeout(ExtractiveBackend):
            def select(self, request):
                raise TimeoutError("fictional")
        result = self.run_case(Timeout())
        events = encode(result.trace)
        events[-1]["details"]["status"] = "interrupted"
        target, digest = self.write(replace(result, status="interrupted", trace=self.rechain(events)))
        with self.assertRaisesRegex(ContractError, "possible interruption"):
            layer.verify_engine(target, digest)
