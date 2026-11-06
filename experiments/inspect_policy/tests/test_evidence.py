from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from fixtures import source
from experiments.inspect_policy.evidence import EvidenceContext
from experiments.inspect_policy.records import CaseRecord, digest, thaw


class EvidenceCommitTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "data/cache/inspect-policy-evidence-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_two_claims_commit_positive_and_expiring_prefix(self):
        row = source(self.root / "source")
        context = EvidenceContext(row)
        record = CaseRecord(self.root / "positive", {"input": row})
        complete = context.commit(["obs-1", "obs-2"], "genetics", record, clock=lambda: 0.0, deadline=1.0)
        self.assertEqual(len(complete["claims"]), 2)
        self.assertEqual(complete["status"], "completed")
        for claim in complete["claims"]:
            self.assertEqual(claim["claim_id"], "claim-" + digest({"case": context.case["case_id"], "evidence": claim["evidence"]})[:20])
        ticks = iter([0.0, 1.0])
        record = CaseRecord(self.root / "expired", {"input": row})
        partial = context.commit(["obs-1", "obs-2"], "genetics", record, clock=lambda: next(ticks), deadline=1.0)
        self.assertEqual(len(partial["claims"]), 1)
        self.assertEqual(partial["prediction"]["reason"], "run_incomplete")
        self.assertIsNone(partial["prediction"]["probability"])

    def test_mutating_telemetry_cannot_alter_private_source_or_claim(self):
        context = EvidenceContext(source(self.root / "source"))
        before = digest(context.records)
        view = thaw(context.records)
        view["obs-1"]["observation"]["method"]["parameters"]["fictional"] = False
        self.assertEqual(digest(context.records), before)
        with self.assertRaises(TypeError):
            context.records["obs-1"]["observation"]["features"]["genetic_support"] = 0.1
        result = context.commit(["obs-1"], "genetics", CaseRecord(self.root / "case", {}), clock=lambda: 0, deadline=1)
        with self.assertRaises(TypeError):
            result["claims"][0]["evidence"]["observation"]["statement"] = "changed"

    def test_duplicates_unoffered_and_wrong_category_rejected(self):
        context = EvidenceContext(source(self.root / "source"))
        for selected, category in ((["obs-1", "obs-1"], "genetics"), (["unknown"], "genetics"), (["obs-1"], "expression")):
            with self.assertRaises(ValueError):
                context.review(selected, category)

    def test_action_modality_tissue_change_suppresses_features_not_context(self):
        for index, (key, value) in enumerate((("intended_action", "activate"), ("modality", "antibody"), ("tissue", "another invented tissue"))):
            def mutate(documents):
                documents["case"]["hypothesis"][key] = value
            context = EvidenceContext(source(self.root / str(index), mutate=mutate))
            self.assertEqual(context.offered("genetics"), ("obs-1", "obs-2"))
            committed = context.commit(["obs-1"], "genetics", CaseRecord(self.root / ("case" + str(index)), {}), clock=lambda: 0, deadline=1)
            self.assertEqual(len(committed["claims"]), 1)
            self.assertIsNone(committed["features"]["values"]["genetic_support"]["value"])
            self.assertIn("outside_applicability", committed["features"]["values"]["genetic_support"]["missing_reasons"])

    def test_future_program_and_scorer_dates_fail_preflight(self):
        def future_program(documents):
            documents["case"]["task"] = "T6"
            documents["case"]["program"]["availability"]["record_public_at"] = "2025-01-01"
        def future_scorer(documents):
            documents["scorer"]["training_label_available_max"] = "2025-01-01"
        for index, mutate in enumerate((future_program, future_scorer)):
            with self.assertRaises(ValueError):
                EvidenceContext(source(self.root / str(index), mutate=mutate))


if __name__ == "__main__":
    unittest.main()
