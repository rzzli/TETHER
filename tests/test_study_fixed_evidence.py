"""Prospective fixed-evidence engineering invariants, no model or biological key."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode
from tether_engine.study.fixed_evidence import (
    PLAN_SHA256,
    RoleRecordedVerifier,
    load_plan,
    preflight,
    prepare_payload,
    prepare_stage,
)
from tether_engine.study.fixed_evidence_smoke import smoke, verify


class FixedEvidenceTests(unittest.TestCase):
    def test_plan_pin_and_shared_default_budget(self):
        plan = load_plan()
        self.assertEqual(plan["aggregate_budget"]["max_input_tokens"], 32000)
        self.assertEqual(len(PLAN_SHA256), 64)
        self.assertEqual(preflight("synthetic-context")["input_reservation"], 31717)
        self.assertEqual(preflight("synthetic-orientation")["input_reservation"], 28505)
        self.assertEqual(preflight("synthetic-context")["output_reservation"], 6144)
        with self.assertRaises(ContractError):
            preflight("real-case")

    def test_bad_resource_rejected(self):
        with patch("tether_engine.study.fixed_evidence.PLAN_SHA256", "0" * 64):
            with self.assertRaises(ContractError):
                load_plan()


class FixedEvidenceSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "comparison"
        cls.receipt = smoke(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_four_arms_verify(self):
        result = verify(self.root, self.receipt["receipt_sha256"])
        self.assertEqual(result["recorded_adapter_cells"], 12)
        self.assertEqual(result["actual_model_calls"], 0)
        self.assertEqual(result["pure_baseline_results"], 4)
        self.assertEqual(result["scientific_validation"], "not_attempted")

    def test_same_sources_no_prose_feedback_and_state_checks(self):
        run_id = self.receipt["run_id"]
        v = RoleRecordedVerifier(self.root, run_id)
        req = prepare_stage(
            self.root,
            run_id,
            "synthetic-context",
            "adapted_virtual_biotech_interpretation",
            4,
        )
        payload = prepare_payload(req)
        self.assertLessEqual(len(payload["prompt"].encode()) + 32, 6400)
        self.assertNotIn("prior_stage_proofs", payload["prompt"])
        self.assertTrue(
            all(set(x) == {"stage", "source_ids"} for x in req["history_projection"])
        )
        with self.assertRaises(ContractError):
            v.validate_response(
                req,
                canonical(
                    dict(
                        answer_status="partial",
                        claims=[],
                        unresolved=[],
                        abstention_reason=None,
                    )
                ),
            )

    def test_history_and_source_forgery_rejected(self):
        v = RoleRecordedVerifier(self.root, self.receipt["run_id"])
        req = v.prepare_stage(
            "synthetic-context", "adapted_virtual_biotech_interpretation", 1
        )
        for mutation in ("history", "run", "arm", "source"):
            bad = encode(req)
            if mutation == "history":
                bad["history_projection"][0]["source_ids"] = []
            if mutation == "run":
                bad["comparison_run_id"] = "other-run"
            if mutation == "arm":
                bad["arm"] = "tether_interpretation"
            if mutation == "source":
                bad["original_request"]["role"] = "evaluation_only"
            with self.assertRaises(ContractError):
                v.validate_payload(bad, prepare_payload(req))

    def test_no_repeat_and_anchor_required(self):
        with self.assertRaises(FileExistsError):
            smoke(self.root)
        with self.assertRaises(ContractError):
            verify(self.root, "0" * 64)

    def test_interrupted_and_expired_runs_retain_failure(self):
        path = Path(self.tmp.name) / "interrupted"
        with patch(
            "tether_engine.study.fixed_evidence_smoke._recorded_document",
            side_effect=KeyboardInterrupt("stop"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                smoke(path)
        self.assertTrue((path / "failure.json").exists())
        self.assertFalse((path / "receipt.json").exists())
        path = Path(self.tmp.name) / "expired"
        with patch(
            "tether_engine.study.fixed_evidence_smoke.time.monotonic", side_effect=[0.0, 301.0]
        ):
            with self.assertRaises(ContractError):
                smoke(path)
        self.assertTrue((path / "failure.json").exists())


if __name__ == "__main__":
    unittest.main()
