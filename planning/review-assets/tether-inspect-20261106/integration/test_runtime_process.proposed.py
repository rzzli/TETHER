"""Proposed maintained tests; apply to tests/ after the source HOLD closes."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import publish
from experiments.inspect_policy.witnesses import make_source, make_row
from experiments.inspect_policy.process_witnesses import interruption, concurrent_reservation


class NativeProcessWitnessTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "data/cache/inspect-policy-process-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_real_interrupt_after_reservation_retains_unexecuted_case(self):
        first = make_row(make_source(self.root / "first-source", "IX06-first"), call_seconds=20.0)
        first["steps"][0]["script"].update(behavior="sleep", delay_seconds=10.0)
        second = make_row(make_source(self.root / "second-source", "IX06-second"))
        oracle = self.root / "oracle.json"
        pin = publish(oracle, {"cases": [{"control_id": first["id"], "fields": {}}, {"control_id": second["id"], "fields": {}}]})
        result = interruption(self.root / "interrupted", [first, second], oracle, pin)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["outstanding_quote"], first["steps"][0]["quote"])
        self.assertEqual(result["dispositions"][1]["status"], "unexecuted")
        self.assertTrue(result["process_reaped"])

    def test_two_actual_native_workers_only_one_owner_dispatches(self):
        row = make_row(make_source(self.root / "source", "IX08-owner"))
        oracle = self.root / "oracle.json"
        pin = publish(oracle, {"cases": [{"control_id": row["id"], "fields": {"status": "completed"}}]})
        result = concurrent_reservation(self.root / "race", row, oracle, pin)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["provider_dispatches"], 1)
        self.assertEqual(sorted(result["native_sample_errors"]), [False, True])
        self.assertTrue(result["processes_reaped"])


if __name__ == "__main__":
    unittest.main()
