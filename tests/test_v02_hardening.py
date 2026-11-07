import io
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend, ReplayBackend, Usage
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.cli import main
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal, inspect_run
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, encode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import Budget, run_workflow

ROOT = Path(__file__).resolve().parents[1]


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(ROOT / "src/tether_engine/demo/v2", self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.fixture / "scorer.json"))

    def tearDown(self):
        self.temp.cleanup()

    def store(self):
        return load_snapshot(self.fixture / "snapshot.json", self.case)

    def edit(self, change, packet_change=None):
        if packet_change:
            packet = read_json(self.fixture / "evidence.json")
            packet_change(packet)
            write_json(self.fixture / "evidence.json", packet)
        snapshot = read_json(self.fixture / "snapshot.json")
        snapshot["artifacts"][0]["sha256"] = sha256_file(self.fixture / "evidence.json")
        change(snapshot)
        write_json(self.fixture / "snapshot.json", snapshot)

    def test_v1_execution_rejected(self):
        legacy = decode(Case, read_json(ROOT / "src/tether_engine/demo/case.json"))
        with self.assertRaisesRegex(ContractError, "v2"):
            legacy.validate()

    def test_nested_parameters_coverage_trace_features_and_contributions_are_frozen(self):
        def modify(packet):
            packet["observations"][0]["method"]["parameters"] = {"nested": {"items": [{"value": 1}]}}
        self.edit(lambda _: None, modify)
        store = self.store()
        result = run_workflow(self.case, store, ExtractiveBackend(), self.model)
        parameter = store.lookup("demo-genetics-1").observation.method.parameters
        with self.assertRaises(TypeError):
            parameter["nested"]["items"][0]["value"] = 2
        with self.assertRaises(TypeError):
            result.coverage["genetics"]["status"] = "fake"
        with self.assertRaises(TypeError):
            result.trace[-1]["details"]["status"] = "fake"
        with self.assertRaises(TypeError):
            result.features.values["genetic_support"] = None
        with self.assertRaises(TypeError):
            result.prediction.contributions["genetic_support"] = None
        with self.assertRaises(TypeError):
            result.claims[0].evidence.observation.features["genetic_support"] = 1

    def test_mismatched_modality_tissue_and_program_measurement_scope(self):
        store = self.store()
        for hypothesis in (replace(self.case.hypothesis, modality="antibody"),
                           replace(self.case.hypothesis, tissue="different tissue")):
            case = replace(self.case, hypothesis=hypothesis)
            result = run_workflow(case, store, ExtractiveBackend())
            self.assertIsNone(result.features.values["direction_alignment"].value)
            self.assertIn("outside_applicability", result.features.values["direction_alignment"].missing_reasons)
        other = replace(self.case, program=replace(self.case.program, program_id="other-program"))
        self.assertFalse(store.query(other, __import__("tether_engine.contracts", fromlist=["Category"]).Category.CLINICAL))

    def test_new_computed_result_uses_old_input_eligibility(self):
        def modify(packet):
            observation = packet["observations"][0]
            observation["source_kind"] = "computed"
            observation["computed_at"] = "2026-10-10T00:00:00+00:00"
            observation["availability"]["record_public_at"] = "2026-10-10"
        self.edit(lambda _: None, modify)
        result = run_workflow(self.case, self.store(), ExtractiveBackend(), self.model)
        self.assertEqual(result.features.values["genetic_support"].value, 0.8)

    def test_missing_lineage_cycle_and_evaluator_parent_are_denied(self):
        original = read_json(self.fixture / "snapshot.json")
        changes = (
            lambda doc: doc["artifacts"][0].update(input_refs=["missing"]),
            lambda doc: doc["sources"][0].update(parents=["demo-original-input"],
                computed_at="2026-10-10T00:00:00+00:00", method_id="fake-method", method_version="1"),
            lambda doc: doc["sources"][0].update(role="evaluation_only"))
        for change in changes:
            with self.subTest(change=change):
                write_json(self.fixture / "snapshot.json", original)
                self.edit(change)
                with self.assertRaises(ContractError):
                    self.store()

    def test_future_input_annotation_excludes_computation(self):
        self.edit(lambda doc: doc["sources"][0]["availability"].update(annotation_public_at="2024-01-01"))
        self.assertFalse(self.store().source_proofs)

    def test_replay_is_bound_to_request(self):
        replay = ReplayBackend(self.fixture / "replay.json")
        case = replace(self.case, case_id="different-request")
        result = run_workflow(case, self.store(), replay)
        self.assertNotEqual(result.status, "completed")
        self.assertEqual(result.calls, 0)

    def test_semantic_verification_rejects_rehashed_inconsistent_outputs(self):
        store = self.store()
        result = run_workflow(self.case, store, ExtractiveBackend(), self.model)
        output = self.root / "run"
        write_run(output, result, store, self.model)
        feature = read_json(output / "features.json")
        feature["values"]["genetic_support"]["value"] = 0.1
        write_json(output / "features.json", feature)
        receipt = read_json(output / "receipt.json")
        receipt["outputs"]["features.json"] = sha256_file(output / "features.json")
        write_json(output / "receipt.json", receipt)
        with self.assertRaisesRegex(ContractError, "Semantic"):
            verify_run(output)

    def test_usage_reservation_survives_keyboard_interrupt_and_inspection_never_retries(self):
        class Interrupted(ExtractiveBackend):
            def quote(self, request):
                return Usage(10, 5, 0.5)
            def select(self, request):
                raise KeyboardInterrupt()
        output = self.root / "run"
        journal = RunJournal(output)
        try:
            result = run_workflow(self.case, self.store(), Interrupted(), self.model,
                                  Budget(max_cost_usd=1), journal=journal)
            self.assertEqual(result.status, "interrupted")
            self.assertEqual(result.calls, 1)
            self.assertEqual(result.estimated_usage.cost_usd, 0.5)
            write_run(output, result, self.store(), self.model, journal)
        finally:
            journal.close()
        inspection = inspect_run(output)
        self.assertEqual(inspection["estimated_upper_usage"]["cost_usd"], 0.5)
        self.assertFalse(inspection["unresolved_attempts"])

    def test_unresolved_durable_attempt_is_conservatively_accounted(self):
        output = self.root / "run"
        journal = RunJournal(output)
        journal.append("dispatch", attempt_id="pending", reserved=Usage(10, 5, 0.5))
        journal.close()
        before = (output / "journal.jsonl").read_bytes()
        self.assertEqual(inspect_run(output)["estimated_upper_usage"]["cost_usd"], 0.5)
        self.assertEqual((output / "journal.jsonl").read_bytes(), before)

    def test_exclusive_reservation_prevents_duplicate_dispatch(self):
        output = self.root / "run"
        journal = RunJournal(output)
        try:
            with self.assertRaises(FileExistsError):
                RunJournal(output)
        finally:
            journal.close()

    def test_write_failure_leaves_readable_journal_and_no_receipt(self):
        original = RunJournal.append
        def faulty(journal, event, **details):
            if event == "review":
                raise OSError("injected write failure")
            return original(journal, event, **details)
        output = self.root / "cli-run"
        arguments = ["run", "--case", str(self.fixture / "case.json"), "--snapshot",
                     str(self.fixture / "snapshot.json"), "--output", str(output)]
        with patch.object(RunJournal, "append", faulty), patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(main(arguments), 2)
        inspection = inspect_run(output)
        self.assertEqual(inspection["last_event"], "run_failed")
        self.assertFalse(inspection["receipt_present"])

