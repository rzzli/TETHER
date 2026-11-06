"""Invented controls only: this suite never opens retained development data."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.scifact_diagnostics.analyze import (
    AnalysisError, ROOT, SOURCE_CLOSURE, analyze_case, analyze_dataset, run_manifest,
)


CORPUS = {d: {"doc_id": d, "title": "Invented", "abstract": [f"Invented {i}" for i in range(12)]}
          for d in (10, 20, 30)}


def gold(evidence=None, claim=1):
    return {"id": claim, "evidence": evidence if evidence is not None else {
        "10": [{"label": "SUPPORT", "sentences": [0, 1]}]}}


def pred(sentences=(0, 1), label="SUPPORT", claim=1):
    return {"id": claim, "evidence": {"10": {"label": label, "sentences": list(sentences)}}}


def record(prediction=None, claim=1, status="produced", check="accepted"):
    return {"id": claim, "producer_status": status, "check_status": check,
            "prediction": pred(claim=claim) if prediction is None and status == "produced" else prediction,
            "reason": None if status == "produced" and check == "accepted" else "Invented disposition"}


class CaseTests(unittest.TestCase):
    def case(self, reference=None, prediction=None, retrieved=(10, 20)):
        return analyze_case(reference or gold(), record(prediction), retrieved)

    def test_extra_rationale_sentences_are_allowed_when_complete_inside_cap(self):
        row = self.case(prediction=pred((0, 1, 8, 9)))
        self.assertTrue(row["raw_strict_correct"])
        self.assertEqual(row["first_failure"], "strict_correct")
        self.assertTrue(row["flags"]["rationale_extra_outside_gold_union"])
        self.assertEqual(row["gold_document_details"][0]["extra_sentences_full"], [8, 9])

    def test_cap_preserves_prediction_order_and_does_not_sort(self):
        row = self.case(prediction=pred((8, 9, 0, 1)))
        detail = row["gold_document_details"][0]
        self.assertFalse(row["raw_strict_correct"])
        self.assertTrue(detail["complete_any_full"])
        self.assertFalse(detail["complete_any_capped"])
        self.assertEqual(detail["capped_sentences"], [8, 9, 0])
        self.assertTrue(row["flags"]["correct_label_incomplete_rationale"])
        self.assertTrue(row["flags"]["complete_full_but_not_capped"])
        self.assertEqual(row["first_failure"], "rationale_incomplete")

    def test_any_complete_alternative_is_sufficient_not_union(self):
        reference = gold({"10": [{"label": "SUPPORT", "sentences": [0, 1]},
                                  {"label": "SUPPORT", "sentences": [4]}]})
        row = self.case(reference, pred((4,)))
        self.assertTrue(row["raw_strict_correct"])
        self.assertEqual(row["gold_document_details"][0]["complete_rationale_indices_capped"], [1])
        self.assertFalse(row["flags"]["rationale_incomplete"])

    def test_cap_uses_shortest_alternative_with_floor_three(self):
        reference = gold({"10": [{"label": "SUPPORT", "sentences": [0, 1, 2, 3]},
                                  {"label": "SUPPORT", "sentences": [7, 8, 9, 10, 11]}]})
        row = self.case(reference, pred((7, 8, 9, 10, 11)))
        self.assertEqual(row["gold_document_details"][0]["native_cap"], 4)
        self.assertFalse(row["raw_strict_correct"])

    def test_multiple_documents_require_all_documents_and_labels(self):
        reference = gold({"10": [{"label": "SUPPORT", "sentences": [0]}],
                          "20": [{"label": "CONTRADICT", "sentences": [2]}]})
        prediction = pred((0,))
        prediction["evidence"]["20"] = {"label": "CONTRADICT", "sentences": [2]}
        self.assertTrue(self.case(reference, prediction)["raw_strict_correct"])
        prediction["evidence"]["20"]["label"] = "SUPPORT"
        row = self.case(reference, prediction)
        self.assertEqual(row["gold_stratum"], "MIXED")
        self.assertEqual(row["first_failure"], "label_mismatch")

    def test_missing_and_extra_documents_and_label_rationale_errors_overlap(self):
        reference = gold({"10": [{"label": "SUPPORT", "sentences": [0]}],
                          "20": [{"label": "SUPPORT", "sentences": [2]}]})
        prediction = pred((), "CONTRADICT")
        prediction["evidence"]["30"] = {"label": "SUPPORT", "sentences": [1]}
        row = self.case(reference, prediction, (10, 30))
        self.assertEqual(row["retrieval"]["false_negative_documents"], ["20"])
        self.assertEqual(row["selection"]["false_positive_documents"], ["30"])
        self.assertEqual(row["selection"]["false_negative_documents"], ["20"])
        self.assertTrue(row["flags"]["label_mismatch"])
        self.assertTrue(row["flags"]["rationale_incomplete"])
        self.assertEqual(row["first_failure"], "retrieval_miss")

    def test_retrieved_gold_omission_is_separate_from_retrieval_miss(self):
        row = self.case(prediction={"id": 1, "evidence": {}})
        self.assertEqual(row["selection"]["retrieved_gold_not_selected"], ["10"])
        self.assertEqual(row["first_failure"], "selection_omission")
        self.assertFalse(row["flags"]["retrieval_miss"])

    def test_extra_selected_document_fails_even_with_correct_gold_document(self):
        prediction = pred()
        prediction["evidence"]["20"] = {"label": "SUPPORT", "sentences": []}
        row = self.case(prediction=prediction)
        self.assertFalse(row["raw_strict_correct"])
        self.assertEqual(row["first_failure"], "selection_extra")

    def test_nei_empty_is_correct_and_retrieval_recall_is_not_applicable(self):
        row = self.case(gold({}), {"id": 1, "evidence": {}})
        self.assertTrue(row["raw_strict_correct"])
        self.assertIsNone(row["retrieval"]["recall"])
        self.assertIsNone(row["retrieval"]["complete_gold_retrieved"])
        self.assertEqual(row["nei_outcome"], "produced_empty_correct")

    def test_nei_nonempty_is_false_positive_not_label_error(self):
        row = self.case(gold({}), pred())
        self.assertEqual(row["nei_outcome"], "produced_nonempty_false_positive")
        self.assertTrue(row["flags"]["selection_extra"])
        self.assertFalse(row["flags"]["label_mismatch"])

    def test_missing_prediction_is_not_substantive_empty_nei(self):
        row = analyze_case(gold({}), record(status="timeout", check="not_run"), None)
        self.assertIsNone(row["raw_strict_correct"])
        self.assertIsNone(row["selection"]["false_negative_documents"])
        self.assertEqual(row["nei_outcome"], "operational_failure")
        self.assertEqual(row["first_failure"], "operational_failure")

    def test_checker_rejection_does_not_reclassify_raw_correctness(self):
        row = analyze_case(gold(), record(pred(), check="rejected"), (10,))
        self.assertTrue(row["raw_strict_correct"])
        self.assertFalse(row["checked_strict_correct"])
        self.assertEqual(row["first_failure"], "strict_correct")

    def test_selected_document_not_retrieved_is_rejected(self):
        with self.assertRaisesRegex(AnalysisError, "retrieved"):
            self.case(retrieved=(20,))


class DatasetTests(unittest.TestCase):
    def dataset(self):
        references = [gold(), gold({}, 2)]
        records = [record(), record({"id": 2, "evidence": {}}, 2)]
        candidates = [{"cell_id": str(r["id"]), "status": "completed", "result": {
            "prediction": r["prediction"], "retrieved": [{"doc_id": 10, "rank": 1}]}}
            for r in records]
        evaluation = {"case_results": [{"id": i, "raw_strict_correct": True,
                                         "checked_strict_correct": True} for i in (1, 2)]}
        return [1, 2], CORPUS, references, records, candidates, evaluation

    def test_complete_partition_and_stratum_denominators(self):
        result = analyze_dataset(*self.dataset())
        self.assertEqual(result["summary"]["scheduled_claims"], 2)
        self.assertEqual(sum(result["summary"]["first_failure_partition"].values()), 2)
        self.assertEqual(result["summary"]["strata"]["NEI"]["scheduled_claims"], 1)
        self.assertEqual(result["summary"]["document_counts"]["gold"], 1)

    def test_schedule_omission_duplication_and_retained_mismatch_fail_closed(self):
        for index, mutation in ((3, lambda a: a.pop()), (4, lambda a: a.append(a[0])),
                                (5, lambda a: a["case_results"][0].update(raw_strict_correct=False))):
            args = list(self.dataset())
            mutation(args[index])
            with self.subTest(index=index), self.assertRaises((AnalysisError, ValueError)):
                analyze_dataset(*args)

    def test_bad_native_sentence_bounds_are_rejected(self):
        args = list(self.dataset())
        args[3][0]["prediction"]["evidence"]["10"]["sentences"] = [99]
        with self.assertRaises(ValueError):
            analyze_dataset(*args)

    def test_duplicate_retrieval_and_rank_changes_are_rejected(self):
        for mutation in (lambda rows: rows.append(rows[0]), lambda rows: rows[0].update(rank=2)):
            args = list(self.dataset())
            mutation(args[4][0]["result"]["retrieved"])
            with self.assertRaises(AnalysisError):
                analyze_dataset(*args)

    def test_overlapping_gold_alternatives_remain_unsupported(self):
        args = list(self.dataset())
        args[2][0]["evidence"]["10"].append({"label": "SUPPORT", "sentences": [1, 2]})
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            analyze_dataset(*args)


def fictional_manifest(root):
    """Write only invented data; real filesystem reads are diagnostic/native source files."""
    schedule, corpus, references, records, candidates, evaluation = DatasetTests().dataset()
    def encode(value):
        return (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    payloads = {"freeze": encode({"dev_schedule": schedule}),
                "corpus": b"".join(encode(r) for r in corpus.values()),
                "references": b"".join(encode(r) for r in references),
                "dispositions": encode(records), "candidates": encode(candidates), "evaluation": encode(evaluation)}
    inputs = {}
    for name, raw in payloads.items():
        path = root / (name + ".json")
        path.write_bytes(raw)
        inputs[name] = pin(path)
    manifest = {"schema_version": 1, "kind": "scifact_descriptive_decomposition_inputs",
                "mode": "fictional_qualification", "expected_claim_count": 2, "inputs": inputs,
                "source_pins": [pin(ROOT / p) for p in SOURCE_CLOSURE]}
    path = root / "MANIFEST.json"
    path.write_bytes(encode(manifest))
    return path, hashlib.sha256(path.read_bytes()).hexdigest(), manifest


class ManifestTests(unittest.TestCase):
    def test_valid_fictional_manifest_generates_replayable_no_clobber_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, digest, _ = fictional_manifest(root)
            output = root / "output"
            receipt = run_manifest(path, digest, output)
            self.assertEqual(receipt["status"], "PASS")
            result = json.loads((output / "DECOMPOSITION.json").read_bytes())
            self.assertEqual(result["schedule"], [1, 2])
            self.assertEqual(result["summary"]["raw_strict_correct"], 2)
            for name, pin in receipt["outputs"].items():
                raw = (output / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin["sha256"])
                self.assertNotIn(b"\r", raw)
            with self.assertRaisesRegex(AnalysisError, "exists"):
                run_manifest(path, digest, output)

    def test_tampered_input_and_missing_source_closure_fail_before_output(self):
        for kind in ("input_tamper", "missing_source"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path, digest, manifest = fictional_manifest(root)
                if kind == "input_tamper":
                    Path(manifest["inputs"]["references"]["path"]).write_bytes(b"{}\n")
                else:
                    manifest["source_pins"].pop()
                    path.write_bytes((json.dumps(manifest) + "\n").encode("utf-8"))
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(AnalysisError, "hash/size|source closure"):
                    run_manifest(path, digest, root / "output")
                self.assertFalse((root / "output").exists())

    def test_duplicate_json_keys_rejected_even_if_correctly_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, digest, manifest = fictional_manifest(root)
            raw = b'{"dev_schedule":[1,2],"dev_schedule":[1,2]}\n'
            freeze = Path(manifest["inputs"]["freeze"]["path"])
            freeze.write_bytes(raw)
            manifest["inputs"]["freeze"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            path.write_bytes((json.dumps(manifest) + "\n").encode("utf-8"))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(AnalysisError, "Duplicate JSON"):
                run_manifest(path, digest, root / "output")

    def test_actual_mode_requires_300_scheduled_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, digest, manifest = fictional_manifest(root)
            manifest["mode"] = "actual"
            path.write_bytes((json.dumps(manifest) + "\n").encode("utf-8"))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(AnalysisError, "300"):
                run_manifest(path, digest, root / "output")

    def test_manifest_hash_mismatch_and_existing_output_are_not_clobbered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_bytes(b'{}\n')
            output = root / "output"
            with self.assertRaisesRegex(AnalysisError, "hash"):
                run_manifest(manifest, "0" * 64, output)
            self.assertFalse(output.exists())
            output.mkdir()
            sentinel = output / "sentinel"
            sentinel.write_bytes(b"retain")
            with self.assertRaises((AnalysisError, FileExistsError)):
                run_manifest(manifest, hashlib.sha256(manifest.read_bytes()).hexdigest(), output)
            self.assertEqual(sentinel.read_bytes(), b"retain")


if __name__ == "__main__":
    unittest.main(verbosity=2)
