"""Review regressions: written against the reviewed implementation before fixes."""
import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from asof.agents import ExtractiveBackend
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.scorer import ScorerArtifact
from asof.serde import ContractError, decode, read_json
from asof.workflow import run_workflow


FIXTURES = Path(__file__).resolve().parents[1] / "src/asof/demo/v2"


class Counter(ExtractiveBackend):
    def __init__(self, exception=None):
        self.calls = 0
        self.exception = exception

    def select(self, request):
        self.calls += 1
        if self.exception:
            raise self.exception("fixture failure")
        return super().select(request)


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "fixture"
        shutil.copytree(FIXTURES, self.root)
        self.case = decode(Case, read_json(self.root / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.root / "scorer.json"))
        self.store = load_snapshot(self.root / "snapshot.json", self.case)

    def tearDown(self):
        self.temp.cleanup()

    def test_future_program_is_rejected_for_t6_before_dispatch(self):
        case = replace(self.case, task="T6", endpoint=None, program=replace(self.case.program,
                       availability=replace(self.case.program.availability, record_public_at=date(2024, 1, 1))))
        backend = Counter()
        with self.assertRaises(ContractError):
            run_workflow(case, self.store, backend)
        self.assertEqual(backend.calls, 0)

    def test_admitted_nested_maps_are_immutable(self):
        observation = self.store.lookup("demo-genetics-1").observation
        with self.assertRaises(TypeError):
            observation.features["genetic_support"] = 1.0
        with self.assertRaises(TypeError):
            observation.method.parameters["unapproved"] = {"future": True}

    def test_opposite_action_cannot_reuse_case_conditioned_features(self):
        case = replace(self.case, hypothesis=replace(self.case.hypothesis, intended_action="activate"))
        model = replace(self.model, intended_actions=("inhibit", "activate"))
        result = run_workflow(case, self.store, Counter(), model)
        self.assertIsNone(result.features.values["direction_alignment"].value)
        self.assertIsNone(result.prediction.probability)

    def test_provider_errors_return_accounted_incomplete_results(self):
        for kind in (TimeoutError, ValueError):
            with self.subTest(kind=kind):
                backend = Counter(kind)
                result = run_workflow(self.case, self.store, backend, self.model)
                self.assertNotEqual(result.status, "completed")
                self.assertGreaterEqual(result.calls, 1)
                self.assertIsNone(result.prediction.probability)

    def test_invalid_scorer_cutoff_fails_before_calls(self):
        backend = Counter()
        model = replace(self.model, training_label_available_max=date(2024, 1, 1))
        with self.assertRaises(ContractError):
            run_workflow(self.case, self.store, backend, model)
        self.assertEqual(backend.calls, 0)

