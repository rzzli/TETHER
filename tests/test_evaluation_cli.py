"""Public evaluation routes against a real fictional offline engine run."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tether_engine.cli import main
from tether_engine.journal import read_chain
from tether_engine.serde import fingerprint, read_json, sha256_file, write_json


class EvaluationCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"
        self.assertEqual(self.invoke(["demo", "--output", str(self.run)]), 0)
        self.case = read_json(self.run / "inputs.json")["case"]
        self.cohort = self.root / "cohort.json"
        self.producer = self.root / "producer.json"
        self.labels = self.root / "labels.json"
        self.output = self.root / "metrics.json"
        endpoint = self.case["endpoint"]
        member = {"case_id": self.case["case_id"], "case_fingerprint": fingerprint(self.case),
                  "origin": self.case["origin"], "endpoint": endpoint["name"],
                  "horizon_months": endpoint["horizon_months"], "cluster_id": "fictional-cluster"}
        write_json(self.cohort, {"schema_version": 1, "kind": "fixed_horizon_binary_cohort",
                   "cohort_id": "fictional-cohort", "label_freeze": "2026-01-01",
                   "policy": {"schema_version": 1, "endpoint": endpoint["name"],
                              "horizon_months": endpoint["horizon_months"], "reporting_lag_days": 30},
                   "members": [member]})
        write_json(self.producer, {"schema_version": 1, "kind": "tether_run_predictions",
                   "arm_id": "fictional-offline", "cohort_sha256": sha256_file(self.cohort),
                   "records": [{"case_id": self.case["case_id"], "state": "sealed_run",
                                "run_dir": str(self.run),
                                "run_id": read_chain(self.run / "journal.jsonl")[0]["details"]["run_id"],
                                "receipt_sha256": sha256_file(self.run / "receipt.json"),
                                "prediction_sha256": sha256_file(self.run / "prediction.json")}]})
        write_json(self.labels, {"schema_version": 1, "label_freeze": "2026-01-01",
                   "outcomes": [{key: value for key, value in member.items() if key != "case_fingerprint"}
                                | {"status": "resolved", "value": 1, "event_at": "2024-01-01",
                                   "observed_until": "2025-01-01", "label_available_at": "2025-02-01"}]})

    @staticmethod
    def invoke(arguments):
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            return main(arguments)

    def arguments(self, command="evaluate", synthetic=True):
        args = [command, "--output", str(self.output)]
        for name in ("cohort", "producer", "labels"):
            path = getattr(self, name)
            args += ["--" + name, str(path), "--" + name + "-sha256", sha256_file(path)]
        return args + (["--allow-synthetic"] if synthetic else [])

    def test_source_inclusive_production_round_trip(self):
        self.assertEqual(self.invoke(self.arguments()), 0)
        report = read_json(self.output)
        self.assertEqual(report["kind"], "producer_bound_evaluation")
        self.assertEqual(report["producer_kind"], "tether_run_predictions")
        self.assertEqual(report["metrics"]["cohort_size"], 1)
        self.assertEqual(report["metrics"]["scored_cases"], 1)
        self.assertEqual(report["metrics"]["prediction_provenance"], "not_checked_by_metrics_function")

    def test_modified_prediction_never_publishes_evaluation(self):
        prediction = read_json(self.run / "prediction.json")
        prediction["probability"] = 0.987654
        write_json(self.run / "prediction.json", prediction)
        self.assertEqual(self.invoke(self.arguments()), 2)
        self.assertFalse(self.output.exists())

    def test_synthetic_prediction_requires_opt_in(self):
        self.assertEqual(self.invoke(self.arguments(synthetic=False)), 2)
        self.assertFalse(self.output.exists())

    def test_external_route_rejects_tether_producer(self):
        self.assertEqual(self.invoke(self.arguments(command="evaluate-baseline")), 2)
        self.assertFalse(self.output.exists())

    def test_external_baseline_cli_preserves_declaration_scope(self):
        member = read_json(self.cohort)["members"][0]
        predictions = self.root / "external.json"
        write_json(predictions, {"schema_version": 1, "records": [
            {key: value for key, value in member.items() if key != "cluster_id"}
            | {"status": "scored", "probability": 0.5, "reason": None}]})
        write_json(self.producer, {"schema_version": 1, "kind": "external_baseline_predictions",
                   "arm_id": "fictional-constant", "cohort_sha256": sha256_file(self.cohort),
                   "prediction_file": {"path": str(predictions), "sha256": sha256_file(predictions)},
                   "producer": {"method_id": "fictional-constant", "method_version": "1", "synthetic": True,
                                "references": [{"role": role, "reference": None, "sha256": None,
                                                "reason": "Unqualified fictional test declaration"}
                                               for role in ("code", "configuration", "model")],
                                "chronology": {"training_cutoff": None, "calibration_cutoff": None,
                                               "generated_at": None, "unknown_reason": "Fictional fixture"}}})
        self.assertEqual(self.invoke(self.arguments(command="evaluate-baseline")), 0)
        report = read_json(self.output)
        self.assertEqual(report["binding"]["prediction_provenance"], "external_producer_declaration")
        self.assertFalse(report["binding"]["independent_authentication"])
        self.assertEqual(report["metrics"]["scored_cases"], 1)

    def test_existing_result_is_preserved_before_verification(self):
        original = b"original result\n"
        self.output.write_bytes(original)
        # Missing source files must not be opened after output preflight fails.
        arguments = self.arguments()
        self.producer.unlink()
        self.assertEqual(self.invoke(arguments), 2)
        self.assertEqual(self.output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
