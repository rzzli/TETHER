"""Authority composition regressions; no tokenizer or model execution."""

import unittest
from unittest.mock import patch
from tether_engine.serde import ContractError, canonical, encode
from tether_engine.study.authority_four_arm import baseline_policy, _schedule, _document
from tether_engine.study.preparation_payloads import prepare_actual_payload, prepare_payloads
from tether_engine.study.diagnostic import load_synthetic_request

import io
from pathlib import Path
import tempfile
import time
from tether_engine.study import authority_four_arm as composition
from tether_engine.study import tokenization as tok
from tether_engine.study.proofs import capture_file
from tether_engine.serde import fingerprint, parse_json
from tests import test_study_tokenization as token_helpers


class AuthorityFourArmTests(unittest.TestCase):
    def test_actual_history_matches_hypothetical_and_rejects_forgery(self):
        req = load_synthetic_request("synthetic-context")
        cells = prepare_payloads(req)
        for item in cells:
            actual = prepare_actual_payload(
                req,
                item["arm"],
                item["stage_index"],
                item["semantic_data"]["prior_source_id_feedback"],
            )
            self.assertEqual(canonical(actual["payload"]), canonical(item["payload"]))
        with self.assertRaises(ContractError):
            prepare_actual_payload(
                req,
                cells[1]["arm"],
                0,
                [{"stage": "chief_of_staff", "source_ids": ["E0"]}],
            )
        with self.assertRaises(ContractError):
            prepare_actual_payload(
                req,
                cells[2]["arm"],
                1,
                [{"stage": "chief_of_staff", "source_ids": ["GOLD"]}],
            )

    def test_baseline_query_and_caps_fixed(self):
        req = load_synthetic_request("synthetic-context")
        self.assertEqual(
            baseline_policy(req, "lexical")["query"], req["question"]["text"]
        )
        self.assertIsNone(baseline_policy(req, "extractive")["query"])
        self.assertEqual(baseline_policy(req, "lexical")["max_result_bytes"], 1048576)
        with self.assertRaises(ContractError):
            baseline_policy(req, "other")

    def test_schedule_six_and_fixed_document(self):
        self.assertEqual(len(_schedule()), 6)
        req = {"example": "not source authority"}
        doc = _document(req, {"prompt": "fixture"})
        self.assertEqual(doc["role"], "evaluation_only_fixture")
        self.assertEqual(doc["usage"]["input_tokens"], 64)


# Full lifecycle uses invented tokenizer assets and a fake child at the existing
# trusted process seam. Raw trace/parser/proofs are real; no OS child is started.


class HundredTokenChild(token_helpers.FakeChild):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.stdout = io.BytesIO(
            (
                "["
                + ", ".join(str(i) for i in range(100))
                + "]\nTotal number of tokens: 100\n"
            ).encode()
        )


class CompositionLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        token_helpers.TokenizationArtifactTests.setUpClass()
        cls.temp = tempfile.TemporaryDirectory(dir=token_helpers.TEMP_ROOT)
        cls.root = Path(cls.temp.name)
        real_run = tok._run_child
        with patch.object(
            tok,
            "_run_child",
            side_effect=lambda *a: real_run(*a, process_factory=HundredTokenChild),
        ):
            cls.result = composition.smoke(
                cls.root / "good",
                token_helpers.TokenizationArtifactTests.authority,
                token_helpers.TokenizationArtifactTests.roots,
            )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        token_helpers.TokenizationArtifactTests.tearDownClass()

    def test_full_replay_no_process_and_shared_accounting(self):
        with patch.object(
            tok.subprocess,
            "Popen",
            side_effect=AssertionError("Replay child forbidden"),
        ):
            result = composition.verify(
                self.root / "good", self.result["receipt_sha256"]
            )
        self.assertEqual(result["input_reserved"], 792)
        self.assertEqual(result["output_reserved"], 6144)
        self.assertEqual(result["actual_model_calls"], 0)
        self.assertEqual(result["recorded_calls"], 6)
        result_doc = parse_json(
            (self.root / "good/extractive-result.json").read_bytes()
        )
        self.assertNotEqual(
            result_doc["excerpts"][0]["grounded_sha256"],
            result_doc["excerpts"][0]["scientific_record_sha256"],
        )

    def test_existing_output_fails_without_child(self):
        with patch.object(
            tok, "_run_child", side_effect=AssertionError("No repeated child")
        ):
            with self.assertRaises(FileExistsError):
                composition.smoke(self.root / "good", {}, {})

    def test_forged_history_and_foreign_identity_rejected(self):
        events = composition.read_chain(self.root / "good/journal.jsonl")
        v = composition.AuthorityRecordedVerifier(
            self.root / "good",
            events[0]["details"]["run_id"],
            deadline=time.monotonic() + 299,
        )
        stage = encode(v.stage(5))
        stage["feedback"][0]["source_ids"] = ["E0"]
        with self.assertRaises(ContractError):
            v.payload(stage)
        stage["run_id"] = "foreign"
        with patch.object(
            v, "stage", side_effect=AssertionError("Must reject before recursion")
        ):
            with self.assertRaises(ContractError):
                v.payload(stage)

    def test_failure_retained_no_success_and_no_retry(self):
        with patch.object(
            composition,
            "prepare_tokenizer_spec",
            side_effect=KeyboardInterrupt("fixture stop"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                composition.smoke(self.root / "interrupted", {}, {})
        self.assertTrue((self.root / "interrupted/failure.json").exists())
        self.assertFalse((self.root / "interrupted/receipt.json").exists())

    def test_resealed_baseline_tampering_fails_semantics(self):
        import shutil

        out = self.root / "tamper"
        shutil.copytree(self.root / "good", out)
        raw = parse_json((out / "lexical-result.json").read_bytes())
        raw["excerpts"][0]["text"] = "fabricated"
        (out / "lexical-result.json").write_bytes(canonical(raw))
        receipt = parse_json((out / "receipt.json").read_bytes())
        receipt["artifacts"]["lexical-result.json"] = encode(
            capture_file(out / "lexical-result.json", "lexical-result.json")
        )
        (out / "receipt.json").write_bytes(canonical(receipt))
        with self.assertRaises(ContractError):
            composition.verify(out, fingerprint(receipt))


if __name__ == "__main__":
    unittest.main()
