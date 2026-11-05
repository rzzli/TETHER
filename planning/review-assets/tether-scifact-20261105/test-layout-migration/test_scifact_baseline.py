"""Fictional baseline tests: actual learning, safe persistence and retrieval isolation."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from asof.serde import ContractError
from experiments.scifact import baseline
from experiments.scifact.baseline import fit_model, load_model, save_model


def fictional():
    corpus = {
        2: {"doc_id": 2, "title": "Example alpha", "abstract": ["The active signal was observed.", "A neutral methods sentence.", "A neutral limitation sentence."]},
        10: {"doc_id": 10, "title": "Example beta", "abstract": ["The active signal was observed.", "A neutral methods sentence.", "A neutral limitation sentence."]},
    }
    queries, pairs = [], []
    for i, label in enumerate(("SUPPORT", "CONTRADICT", "NEI")):
        for j in range(12):
            cid = i * 12 + j + 1
            queries.append({"id": cid, "claim": f"{label.lower()}cue signal relationship querytoken"})
            pairs.append({"claim_id": cid, "doc_id": 2 if j % 2 else 10, "label": label,
                          "rationale_sentences": [] if label == "NEI" else [0]})
    return corpus, queries, pairs


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus, cls.queries, cls.pairs = fictional()
        cls.model = fit_model(cls.corpus, cls.queries, cls.pairs)

    def test_learns_three_way_document_labels(self):
        for q in self.queries:
            expected = self.pairs[q["id"] - 1]["label"]
            result = self.model.predict(q, k=2, rationale_threshold=0.25)
            self.assertEqual({x["label"] for x in result["pair_scores"]}, {expected})
            self.assertEqual(bool(result["prediction"]["evidence"]), expected != "NEI")

    def test_retrieval_vocabulary_never_uses_claims(self):
        self.assertNotIn("querytoken", self.model.retrieval_vectorizer.vocabulary_)
        self.assertIn("querytoken", self.model.pair_vectorizer.vocabulary_)

    def test_zero_similarity_has_numeric_id_tie_order(self):
        result = self.model.predict({"id": 100, "claim": "zzzzunseen"}, k=2, rationale_threshold=0.5)
        self.assertEqual([x["doc_id"] for x in result["retrieved"]], [2, 10])

    def test_native_nei_is_successful_empty_dictionary(self):
        result = self.model.predict(self.queries[-1], k=2, rationale_threshold=0.5)
        self.assertEqual(result["prediction"], {"id": 36, "evidence": {}})
        self.assertEqual(len(result["pair_scores"]), 2)

    def test_serialized_numeric_inference_agrees_with_fit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "model"
            save_model(self.model, path)
            loaded = load_model(path)
            for q in (self.queries[0], self.queries[12], self.queries[24]):
                a = self.model.predict(q, k=2, rationale_threshold=0.5)
                b = loaded.predict(q, k=2, rationale_threshold=0.5)
                self.assertEqual(a["prediction"], b["prediction"])
                np.testing.assert_allclose([x["probabilities"] for x in a["pair_scores"]],
                                           [x["probabilities"] for x in b["pair_scores"]], atol=1e-12)
            self.assertEqual(set(p.name for p in path.iterdir()), {"model.json", "arrays.npz"})

    def test_array_tamper_rejected_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "model"
            save_model(self.model, path)
            before = (path / "model.json").read_bytes()
            with self.assertRaises(FileExistsError):
                save_model(self.model, path)
            self.assertEqual(before, (path / "model.json").read_bytes())
            with (path / "arrays.npz").open("ab") as f:
                f.write(b"corruption")
            with self.assertRaises(ContractError):
                load_model(path)

    def test_numeric_load_uses_hash_verified_capture_despite_disk_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "model"
            save_model(self.model, path)
            target = path / "arrays.npz"
            checked_bytes = target.read_bytes()
            original_load = np.load
            with original_load(io.BytesIO(checked_bytes), allow_pickle=False) as archive:
                replacement = {name: archive[name].copy() for name in archive.files}
            replacement["label_coefficients"][0, 0] += 10
            buffer = io.BytesIO()
            np.savez_compressed(buffer, **replacement)
            def replace_before_load(file, *args, **kwargs):
                target.write_bytes(buffer.getvalue())
                return original_load(file, *args, **kwargs)
            with patch.object(baseline.np, "load", side_effect=replace_before_load):
                loaded = load_model(path)
            np.testing.assert_array_equal(loaded.label_coefficients, self.model.label_coefficients)
            self.assertNotEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                                hashlib.sha256(checked_bytes).hexdigest())

    def test_numeric_schema_and_csr_structure_are_validated_before_construction(self):
        def replace_payload(path, mutate):
            with np.load(io.BytesIO((path / "arrays.npz").read_bytes()), allow_pickle=False) as archive:
                arrays = {name: archive[name].copy() for name in archive.files}
            mutate(arrays)
            np.savez_compressed(path / "arrays.npz", **arrays)
            raw = (path / "arrays.npz").read_bytes()
            metadata = json.loads((path / "model.json").read_text())
            metadata.update(arrays_sha256=hashlib.sha256(raw).hexdigest(), arrays_bytes=len(raw))
            (path / "model.json").write_text(json.dumps(metadata), encoding="utf-8")
        mutations = {
            "unexpected_array_key": lambda a: a.update(unexpected=a.pop("index_data")),
            "fractional_column_indices": lambda a: a.update(index_indices=a["index_indices"].astype(float) + .5),
            "truncated_data": lambda a: a["index_indptr"].__setitem__(-1, int(a["index_indptr"][-1]) - 1),
            "column_out_of_range": lambda a: a["index_indices"].__setitem__(0, len(a["retrieval_idf"])),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "model"
                save_model(self.model, path)
                replace_payload(path, mutate)
                with self.assertRaises(ContractError):
                    load_model(path)

    def test_supervision_must_reference_exact_fit_claims_and_corpus(self):
        for field, value in [("claim_id", 10000), ("doc_id", 999), ("label", "UNKNOWN")]:
            altered = [dict(x) for x in self.pairs]
            altered[0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                fit_model(self.corpus, self.queries, altered)

    def test_duplicate_pairs_and_claims_rejected(self):
        with self.assertRaises(ContractError):
            fit_model(self.corpus, self.queries, self.pairs + [self.pairs[0]])
        with self.assertRaises(ContractError):
            fit_model(self.corpus, self.queries + [self.queries[0]], self.pairs)

    def test_missing_class_cannot_silently_become_binary_model(self):
        with self.assertRaises(ContractError):
            fit_model(self.corpus, self.queries, [p for p in self.pairs if p["label"] != "NEI"])

    def test_invalid_prediction_configuration_rejected(self):
        for k, threshold in [(0, 0.5), (True, 0.5), (2, -0.1), (2, float("nan"))]:
            with self.subTest(k=k, threshold=threshold), self.assertRaises(ContractError):
                self.model.predict(self.queries[0], k=k, rationale_threshold=threshold)


if __name__ == "__main__":
    unittest.main()
