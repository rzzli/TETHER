"""Regressions for the full-project audit, first run against the reviewed code."""
import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from asof.agents import ExtractiveBackend
from asof.artifacts import verify_run, write_run
from asof.chrono import load_snapshot
from asof.contracts import Case, Category
from asof.journal import RunJournal
from asof.ledger import EvidenceLedger
from asof.scorer import ScorerArtifact
from asof.serde import (ContractError, MAX_LEDGER_JSON_BYTES, canonical, decode, fingerprint,
                       read_json, read_ledger_json, sha256_file, write_json)
from asof.semantics import check_semantics
from asof.workflow import Budget, run_workflow


ROOT = Path(__file__).resolve().parents[1]


class AuditVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(ROOT / "src/asof/demo/v2", self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.fixture / "scorer.json"))
        self.store = load_snapshot(self.fixture / "snapshot.json", self.case)
        self.result = run_workflow(self.case, self.store, ExtractiveBackend(), self.model)
        self.output = self.root / "run"
        write_run(self.output, self.result, self.store, self.model)

    def tearDown(self):
        self.temp.cleanup()

    def rehash_outputs(self):
        receipt = read_json(self.output / "receipt.json")
        for name in receipt["outputs"]:
            receipt["outputs"][name] = sha256_file(self.output / name)
        write_json(self.output / "receipt.json", receipt)

    def test_rehashed_run_identity_and_accounting_are_rejected(self):
        original = read_json(self.output / "run.json")
        changes = {"case_id": "wrong-case", "snapshot_id": "wrong-snapshot", "profile": "wrong-profile",
                   "backend_id": "wrong-backend", "calls": 999,
                   "usage": {"input_tokens": 999, "output_tokens": 0, "cost_usd": 0},
                   "measured_usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 1},
                   "estimated_usage": {"input_tokens": 1, "output_tokens": 0, "cost_usd": 0},
                   "budget": {**original["budget"], "max_calls": 999}}
        for key, value in changes.items():
            with self.subTest(field=key):
                write_json(self.output / "run.json", {**original, key: value})
                self.rehash_outputs()
                with self.assertRaisesRegex(ContractError, "Semantic"):
                    verify_run(self.output)

    def test_rehashed_journal_claim_different_from_ledger_is_rejected(self):
        events = [__import__("json").loads(line) for line in (self.output / "trace.jsonl").read_text().splitlines()]
        event = next(item for item in events if item["event"] == "claim_committed")
        event["details"]["claim"]["evidence"]["observation"]["statement"] = "different journal claim"
        previous = None
        for item in events:
            item.pop("sha256")
            item["previous_sha256"] = previous
            item["sha256"] = previous = fingerprint(item)
        for name in ("trace.jsonl", "journal.jsonl"):
            (self.output / name).write_bytes(b"".join(canonical(item) + b"\n" for item in events))
        self.rehash_outputs()
        with self.assertRaisesRegex(ContractError, "Semantic"):
            verify_run(self.output)

    def test_omitted_raw_parent_proof_is_rejected_even_without_source_reads(self):
        receipt = read_json(self.output / "receipt.json")
        artifact_ids = {item.artifact_id for item in self.store.snapshot.artifacts}
        receipt["sources"] = [item for item in receipt["sources"] if item["artifact_id"] in artifact_ids]
        write_json(self.output / "receipt.json", receipt)
        for verify_sources in (True, False):
            with self.subTest(verify_sources=verify_sources):
                with self.assertRaisesRegex(ContractError, "Semantic"):
                    verify_run(self.output, verify_sources=verify_sources)

    def test_new_request_is_sealed_and_legacy_v2_without_auxiliary_remains_valid(self):
        self.assertEqual(verify_run(self.output)["semantic_consistency"], "verified")
        output = self.root / "with-request"
        journal = RunJournal(output)
        try:
            write_json(output / "request.json", {"case": self.case})
            result = run_workflow(self.case, self.store, ExtractiveBackend(), self.model, journal=journal)
            write_run(output, result, self.store, self.model, journal)
        finally:
            journal.close()
        self.assertEqual(verify_run(output)["auxiliary_outputs_checked"], 1)
        write_json(output / "request.json", {"case": "changed"})
        with self.assertRaisesRegex(ContractError, "auxiliary output integrity"):
            verify_run(output)

    def test_indexed_ledger_lookup_retains_capability_gates(self):
        ledger = EvidenceLedger(self.case, self.store)
        with patch.object(self.store, "query", side_effect=AssertionError("must not scan the store")):
            ledger.append(Category.GENETICS, "demo-genetics-1")
            with self.assertRaisesRegex(ContractError, "capability"):
                ledger.append(Category.EXPRESSION, "demo-genetics-1")

    def test_wall_time_expiry_during_commit_retains_claim_and_abstains(self):
        clock = [0.0]
        original = EvidenceLedger.append
        def slow_commit(ledger, category, observation_id):
            result = original(ledger, category, observation_id)
            clock[0] = 2.0
            return result
        with patch("asof.workflow.time.monotonic", side_effect=lambda: clock[0]), \
                patch.object(EvidenceLedger, "append", slow_commit):
            result = run_workflow(self.case, self.store, ExtractiveBackend(), self.model,
                                  Budget(max_seconds=1))
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(len(result.claims), 1)
        self.assertEqual(result.coverage["genetics"]["selected_observations"], 1)
        self.assertEqual(result.coverage["genetics"]["status"], "budget_exhausted")
        self.assertIsNone(result.prediction.probability)
        output = self.root / "budget-run"
        write_run(output, result, self.store, self.model)
        self.assertEqual(verify_run(output)["semantic_consistency"], "verified")

    def test_verification_reuses_publication_eligibility_gate(self):
        claim = self.result.claims[0]
        evidence = replace(claim.evidence, observation=replace(claim.evidence.observation,
                           publication_date=date(self.case.origin.year + 1, 1, 1)))
        changed = replace(claim, evidence=evidence, admitted_fingerprint=fingerprint(evidence),
                          claim_id="claim-" + fingerprint({"case": self.case.case_id, "evidence": evidence})[:20])
        admitted = {**self.store.admitted_fingerprints, evidence.observation.observation_id: fingerprint(evidence)}
        with self.assertRaisesRegex(ContractError, "ineligible information"):
            check_semantics(self.case, self.store.snapshot, (changed,) + self.result.claims[1:],
                            self.result.features, self.result.prediction, self.result.coverage,
                            self.result.configuration, self.result.status, self.model, admitted,
                            self.store.catalog_policy, self.store.snapshot_base, self.result.trace)

    def test_finalization_rejects_inconsistent_accounting(self):
        with self.assertRaisesRegex(ContractError, "accounting/journal"):
            write_run(self.root / "bad-final", replace(self.result, calls=999), self.store, self.model)

    def test_ledger_output_above_packet_limit_can_be_verified(self):
        # Valid trailing JSON whitespace exercises the real 64 MiB boundary without
        # manufacturing scientific claims or requiring a large provider fixture.
        path = self.output / "ledger.json"
        with path.open("ab") as stream:
            chunk = b" " * (1024 * 1024)
            while stream.tell() <= 64 * 1024 * 1024:
                stream.write(chunk)
        self.rehash_outputs()
        self.assertEqual(verify_run(self.output)["semantic_consistency"], "verified")
        with self.assertRaisesRegex(ContractError, "64 MiB"):
            read_json(path)

    def test_ledger_output_bound_is_finite_and_checked_before_reading(self):
        path = self.root / "oversized-ledger.json"
        with path.open("wb") as stream:
            stream.seek(MAX_LEDGER_JSON_BYTES)
            stream.write(b" ")
        with self.assertRaisesRegex(ContractError, "256 MiB"):
            read_ledger_json(path)
