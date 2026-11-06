"""Regressions for the four independently reproduced native integration gaps."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from fixtures import source
from inspect_ai.model import ChatMessageUser, GenerateConfig, ModelOutput
from experiments.inspect_policy.records import CaseRecord, canonical, publish
from experiments.inspect_policy.accounting import Accounting
from experiments.inspect_policy.archive import execute_archive_case
from experiments.inspect_policy.evidence import EvidenceContext
from experiments.inspect_policy.task import archive_scorer
from experiments.inspect_policy.runtime import ACTIVE, CONFIG, ScriptedProvider, runtime_scorer


def immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError("Direct fixture unexpectedly required event-loop scheduling")


class NativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "data/cache/inspect-policy-boundary-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_archive_scorer_rejects_different_case_record_before_oracle(self):
        result = {"control_id": "fiction-B", "status": "completed", "decision": {"control_id": "fiction-B", "decision": "accept", "observables": {}}}
        record = CaseRecord(self.root / "B", {"control_id": "fiction-B"})
        receipt = record.finish(result)["receipt"]
        state = SimpleNamespace(sample_id="fiction-A", metadata={"policy_record": {"path": str(record.path), "receipt": receipt}},
                                output=ModelOutput.from_content("none", canonical(result).decode()))
        with self.assertRaisesRegex(ValueError, "identities differ"):
            immediate(archive_scorer(str(self.root / "nonexistent-oracle"), {})(state, None))

    def test_runtime_scorer_rejects_different_case_record_before_oracle(self):
        record = CaseRecord(self.root / "B", {"id": "fiction-B"})
        receipt = record.finish({"control_id": "fiction-B", "last_response_content": None})["receipt"]
        state = SimpleNamespace(sample_id="fiction-A", metadata={"policy_record": {"path": str(record.path), "receipt": receipt}})
        with self.assertRaisesRegex(ValueError, "identities differ"):
            immediate(runtime_scorer(str(self.root / "nonexistent-oracle"), {})(state, None))

    def test_changed_temperature_does_not_dispatch(self):
        record = CaseRecord(self.root / "configuration", {"id": "fiction"})
        account = Accounting(record, {"max_calls": 1, "max_input_tokens": 100, "max_output_tokens": 100,
                                      "max_cost_usd": 0.0, "max_seconds": 10.0})
        request = {"case_id": "fiction", "offered_observation_ids": []}
        ticket = account.reserve(request, {"input_tokens": 10, "output_tokens": 10, "cost_usd": 0.0})
        active = {"record": record, "account": account, "ticket": ticket, "entries": 0, "dispatched": 0}
        provider = ScriptedProvider(model_name="fictional", config=GenerateConfig(**CONFIG))
        token = ACTIVE.set(active)
        try:
            with self.assertRaisesRegex(ValueError, "configuration differs"):
                immediate(provider.generate([ChatMessageUser(content=canonical(request).decode())], [], "none",
                                            GenerateConfig(**{**CONFIG, "temperature": 0.9, "max_tokens": 10})))
        finally:
            ACTIVE.reset(token)
        self.assertEqual(active["dispatched"], 0)

    def test_nested_output_is_denied_before_protected_file_creation(self):
        row = source(self.root / "source")
        nested = Path(row["bundle_root"]) / "nested-output"
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            execute_archive_case(row, nested)
        self.assertEqual(list(nested.iterdir()), [])

    def test_duplicate_cross_step_claim_rejected(self):
        context = EvidenceContext(source(self.root / "source"))
        record = CaseRecord(self.root / "commits", {})
        first = context.commit(["obs-1"], "genetics", record, clock=lambda: 0, deadline=1)
        with self.assertRaisesRegex(ValueError, "Previously committed"):
            context.commit(["obs-1"], "genetics", record, clock=lambda: 0, deadline=1)
        self.assertEqual(len(first["claims"]), 1)


if __name__ == "__main__":
    unittest.main()
