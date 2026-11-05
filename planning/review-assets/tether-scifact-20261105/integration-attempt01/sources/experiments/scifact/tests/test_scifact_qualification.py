"""Narrow declared protocol controls using fictional data and unchanged runtime."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning

from experiments.scifact.baseline import fit_model, SEED
from experiments.scifact.tether_adapter import NativeSession, verify_session
from test_scifact_baseline import fictional
from test_scifact_policy import resources


class DeclaredQualificationTests(unittest.TestCase):
    def test_equivalent_normalized_output_alias_cannot_replace_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "original"
            with NativeSession(output, ["cell"], {}) as session:
                session.begin("cell", {"fictional": True})
                session.finish("cell", {"value": "keep"}, resources())
                receipt = session.finalize()
            before = {path.relative_to(output).as_posix(): path.read_bytes()
                      for path in output.rglob("*") if path.is_file()}
            (root / "alias-parent").mkdir()
            alias = root / "alias-parent" / ".." / "original"
            self.assertNotEqual(str(alias), str(output))
            self.assertEqual(alias.resolve(), output.resolve())
            with self.assertRaises(FileExistsError):
                NativeSession(alias, ["replacement"], {"replacement": True})
            after = {path.relative_to(output).as_posix(): path.read_bytes()
                     for path in output.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(verify_session(output, expected_receipt_sha256=receipt["sha256"])["terminal_cells"], 1)

    def test_two_same_seed_fictional_fits_have_identical_numeric_state_and_predictions(self):
        corpus, queries, pairs = fictional()
        first = fit_model(corpus, queries, pairs)
        second = fit_model(corpus, queries, pairs)
        self.assertEqual(SEED, 20261105)
        self.assertEqual(first.metadata["seed"], SEED)
        self.assertEqual(first.metadata, second.metadata)
        self.assertEqual(first.doc_ids, second.doc_ids)
        for name in ("retrieval_vectorizer", "pair_vectorizer"):
            left, right = getattr(first, name), getattr(second, name)
            self.assertEqual(left.vocabulary_, right.vocabulary_)
            np.testing.assert_array_equal(left.idf_, right.idf_)
        for name in ("label_coefficients", "label_intercepts", "rationale_coefficients", "rationale_intercepts"):
            np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
        self.assertEqual(first.retrieval_matrix.shape, second.retrieval_matrix.shape)
        for name in ("data", "indices", "indptr"):
            np.testing.assert_array_equal(getattr(first.retrieval_matrix, name), getattr(second.retrieval_matrix, name))
        for query in (queries[0], queries[12], queries[24], {"id": 1000, "claim": "A previously unseen fictional claim"}):
            with self.subTest(claim_id=query["id"]):
                self.assertEqual(first.predict(query, k=2, rationale_threshold=.5),
                                 second.predict(query, k=2, rationale_threshold=.5))

    def test_injected_sklearn_convergence_warning_aborts_before_second_learner(self):
        corpus, queries, pairs = fictional()
        def nonconverged(*args, **kwargs):
            warnings.warn("fictional nonconvergence", ConvergenceWarning)
            raise AssertionError("The convergence warning was silently ignored")
        with patch("experiments.scifact.baseline.SGDClassifier.fit", side_effect=nonconverged) as fitting:
            with self.assertRaisesRegex(ConvergenceWarning, "fictional nonconvergence"):
                fit_model(corpus, queries, pairs)
        self.assertEqual(fitting.call_count, 1)


if __name__ == "__main__":
    unittest.main()
