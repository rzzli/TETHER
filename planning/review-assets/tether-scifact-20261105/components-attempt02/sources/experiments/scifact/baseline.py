"""Small train-only linear SciFact solver with explicit numeric persistence.

This is a deliberately modest benchmark baseline, not a clinical scoring model.
Only ``fit_model`` receives supervision. Prediction takes a claim-only record.
"""
from __future__ import annotations

import hashlib
import io
import math
import unicodedata
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from threadpoolctl import threadpool_limits

from asof.atomic import publish_bytes
from asof.serde import ContractError, canonical, freeze, parse_json

LABELS = ("CONTRADICT", "NEI", "SUPPORT")
SEED = 20261105
VECTORIZER_SETTINGS = dict(ngram_range=(1, 2), lowercase=True, norm="l2", sublinear_tf=True)
LEARNER_SETTINGS = dict(loss="log_loss", penalty="l2", alpha=1e-4, max_iter=2000,
                        tol=1e-4, class_weight="balanced", random_state=SEED)
ARRAY_KEYS = frozenset({"retrieval_idf", "pair_idf", "index_data", "index_indices", "index_indptr",
                        "label_coefficients", "label_intercepts", "rationale_coefficients", "rationale_intercepts"})


def need(condition, message):
    if not condition:
        raise ContractError(message)


def normalize(text):
    need(isinstance(text, str) and bool(text.strip()), "Expected nonempty source text")
    return unicodedata.normalize("NFKC", text)


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def document_text(row):
    return normalize(row["title"] + "\n" + "\n".join(row["abstract"]))


def pair_features(vectorizer, claims, documents):
    left = vectorizer.transform([normalize(x) for x in claims]).tocsr()
    right = vectorizer.transform([normalize(x) for x in documents]).tocsr()
    difference = left - right
    difference.data = np.abs(difference.data)
    return sparse.hstack((left, right, left.multiply(right), difference), format="csr")


def probabilities(features, coefficients, intercepts, classes):
    scores = np.asarray(features @ coefficients.T) + intercepts
    values = expit(scores)
    if len(classes) == 2:
        values = np.column_stack((1 - values.ravel(), values.ravel()))
    else:
        values /= values.sum(axis=1, keepdims=True)
    need(np.isfinite(values).all(), "Nonfinite model probabilities")
    return values


@dataclass
class LinearBaseline:
    corpus: dict
    doc_ids: tuple
    retrieval_vectorizer: TfidfVectorizer
    retrieval_matrix: sparse.csr_matrix
    pair_vectorizer: TfidfVectorizer
    label_coefficients: np.ndarray
    label_intercepts: np.ndarray
    rationale_coefficients: np.ndarray
    rationale_intercepts: np.ndarray
    metadata: dict

    def predict(self, query, *, k, rationale_threshold):
        need(isinstance(query, dict) and set(query) == {"id", "claim"}, "Prediction requires claim-only query")
        need(type(query["id"]) is int and query["id"] >= 0, "Invalid claim ID")
        need(type(k) is int and 0 < k <= 100, "Invalid retrieval k")
        need(type(rationale_threshold) in (float, int) and math.isfinite(rationale_threshold)
             and 0 <= rationale_threshold <= 1, "Invalid rationale threshold")
        claim = normalize(query["claim"])
        with threadpool_limits(limits=1):
            vector = self.retrieval_vectorizer.transform([claim])
            similarities = np.asarray((self.retrieval_matrix @ vector.T).toarray()).ravel()
            order = sorted(range(len(self.doc_ids)), key=lambda i: (-float(similarities[i]), self.doc_ids[i]))[:k]
            selected = [self.doc_ids[i] for i in order]
            features = pair_features(self.pair_vectorizer, [claim] * len(selected),
                                     [document_text(self.corpus[d]) for d in selected])
            scores = probabilities(features, self.label_coefficients, self.label_intercepts, LABELS)
            evidence, raw_scores, source_bindings = {}, [], []
            for position, doc_id in enumerate(selected):
                label = LABELS[int(np.argmax(scores[position]))]
                sentences = self.corpus[doc_id]["abstract"]
                sentence_scores = None
                rationale = []
                if label != "NEI":
                    sentence_scores = probabilities(
                        pair_features(self.pair_vectorizer, [claim] * len(sentences), list(sentences)),
                        self.rationale_coefficients, self.rationale_intercepts, (0, 1))[:, 1]
                    rationale = sorted((i for i, x in enumerate(sentence_scores) if x >= rationale_threshold),
                                       key=lambda i: (-float(sentence_scores[i]), i))[:5]
                raw_scores.append({"doc_id": doc_id, "label": label,
                                   "classes": list(LABELS), "probabilities": scores[position].tolist(),
                                   "rationale_probabilities": None if sentence_scores is None else sentence_scores.tolist(),
                                   "rationale_status": "not_requested_for_nei" if label == "NEI" else "computed"})
                if label != "NEI":
                    evidence[str(doc_id)] = {"label": label, "sentences": rationale}
                    source_bindings.extend({"doc_id": doc_id, "sentence_id": i,
                                            "text_sha256": hashlib.sha256(sentences[i].encode("utf-8")).hexdigest()}
                                           for i in rationale)
        return {"prediction": {"id": query["id"], "evidence": evidence},
                "retrieved": [{"doc_id": self.doc_ids[i], "rank": rank + 1,
                               "score": float(similarities[i]),
                               "document_sha256": digest(self.corpus[self.doc_ids[i]])}
                              for rank, i in enumerate(order)],
                "pair_scores": raw_scores, "source_bindings": source_bindings}


def fit_model(corpus, fit_queries, fit_pairs):
    """Fit exactly two learners; callers enforce supervision purpose/partition."""
    need(bool(corpus) and all(type(k) is int for k in corpus), "Native integer corpus IDs required")
    docs = {}
    for doc_id, row in corpus.items():
        need(set(row) == {"doc_id", "title", "abstract"} and row["doc_id"] == doc_id,
             "Corpus must be the approved three-field view")
        need(isinstance(row["title"], str) and isinstance(row["abstract"], (tuple, list))
             and len(row["abstract"]) > 0, "Invalid corpus text")
        for sentence in row["abstract"]:
            normalize(sentence)
        docs[doc_id] = {"doc_id": doc_id, "title": row["title"], "abstract": list(row["abstract"])}
    queries = {}
    for row in fit_queries:
        need(set(row) == {"id", "claim"} and type(row["id"]) is int and row["id"] not in queries,
             "Duplicate or invalid fit query")
        queries[row["id"]] = normalize(row["claim"])
    need(bool(queries) and bool(fit_pairs), "Missing fit data")
    seen, labels, paired_claims, paired_documents = set(), [], [], []
    sentence_claims, sentence_texts, sentence_labels = [], [], []
    for pair in fit_pairs:
        cid, did, label = pair["claim_id"], pair["doc_id"], pair["label"]
        need((cid, did) not in seen and cid in queries and did in docs and label in LABELS,
             "Invalid, duplicate, or non-fit supervision pair")
        seen.add((cid, did))
        rationale = pair["rationale_sentences"]
        need(isinstance(rationale, (tuple, list)) and len(set(rationale)) == len(rationale)
             and all(type(x) is int and 0 <= x < len(docs[did]["abstract"]) for x in rationale),
             "Invalid rationale supervision")
        need((label == "NEI" and not rationale) or (label != "NEI" and bool(rationale)),
             "Label and rationale supervision disagree")
        labels.append(label)
        paired_claims.append(queries[cid])
        paired_documents.append(document_text(docs[did]))
        if label != "NEI":
            sentence_claims.extend([queries[cid]] * len(docs[did]["abstract"]))
            sentence_texts.extend(docs[did]["abstract"])
            sentence_labels.extend(int(i in rationale) for i in range(len(docs[did]["abstract"])))
    need(set(labels) == set(LABELS), "Fit requires all three document labels")
    need(set(sentence_labels) == {0, 1}, "Fit requires both sentence-selector classes")
    doc_ids = tuple(sorted(docs))
    with warnings.catch_warnings(), threadpool_limits(limits=1):
        warnings.simplefilter("error", ConvergenceWarning)
        retrieval = TfidfVectorizer(**VECTORIZER_SETTINGS, max_features=100000)
        index = retrieval.fit_transform([document_text(docs[d]) for d in doc_ids]).tocsr()
        paired = TfidfVectorizer(**VECTORIZER_SETTINGS, max_features=50000)
        # Each fit claim and fit-pair document contributes once to the vocabulary/IDF.
        fit_doc_ids = sorted({did for _, did in seen})
        paired.fit([queries[c] for c in sorted(queries)] + [document_text(docs[d]) for d in fit_doc_ids])
        label_model = SGDClassifier(**LEARNER_SETTINGS).fit(
            pair_features(paired, paired_claims, paired_documents), np.asarray(labels))
        rationale_model = SGDClassifier(**LEARNER_SETTINGS).fit(
            pair_features(paired, sentence_claims, sentence_texts), np.asarray(sentence_labels))
    need(tuple(label_model.classes_) == LABELS and tuple(rationale_model.classes_) == (0, 1),
         "Unexpected learned class ordering")
    metadata = {"schema_version": 1, "method_id": "scifact_sparse_linear_v1", "seed": SEED,
                "fit_claim_ids": sorted(queries), "fit_document_ids": fit_doc_ids,
                "fit_pairs": len(labels), "sentence_fit_rows": len(sentence_labels),
                "class_counts": {label: labels.count(label) for label in LABELS},
                "label_iterations": int(label_model.n_iter_),
                "rationale_iterations": int(rationale_model.n_iter_),
                "retrieval_features": len(retrieval.vocabulary_), "pair_features": len(paired.vocabulary_),
                "fit_semantics": "annotation_relative_cited_pairs",
                "index_semantics": "whole_unlabeled_public_corpus_idf",
                "normalization": "NFKC_then_lowercase_vectorizer",
                "learner_settings": LEARNER_SETTINGS, "vectorizer_settings": VECTORIZER_SETTINGS}
    return LinearBaseline(freeze(docs), doc_ids, retrieval, index, paired,
                          label_model.coef_.copy(), label_model.intercept_.copy(),
                          rationale_model.coef_.copy(), rationale_model.intercept_.copy(), freeze(metadata))


def save_model(model, output):
    """Exclusive numeric/vocabulary artifact; no executable Python pickle."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", retrieval_idf=model.retrieval_vectorizer.idf_,
                        pair_idf=model.pair_vectorizer.idf_, index_data=model.retrieval_matrix.data,
                        index_indices=model.retrieval_matrix.indices, index_indptr=model.retrieval_matrix.indptr,
                        label_coefficients=model.label_coefficients, label_intercepts=model.label_intercepts,
                        rationale_coefficients=model.rationale_coefficients, rationale_intercepts=model.rationale_intercepts)
    arrays = (output / "arrays.npz").read_bytes()
    metadata = {"schema_version": 1, "corpus": [model.corpus[x] for x in model.doc_ids],
                "retrieval_vocabulary": {k: int(v) for k, v in model.retrieval_vectorizer.vocabulary_.items()},
                "pair_vocabulary": {k: int(v) for k, v in model.pair_vectorizer.vocabulary_.items()}, "metadata": model.metadata,
                "arrays_sha256": hashlib.sha256(arrays).hexdigest(), "arrays_bytes": len(arrays)}
    publish_bytes(output / "model.json", canonical(metadata) + b"\n")


def _vectorizer(vocabulary, idf, cap):
    need(isinstance(vocabulary, dict) and 0 < len(vocabulary) <= cap and
         all(isinstance(key, str) and bool(key) and type(value) is int for key, value in vocabulary.items()) and
         set(vocabulary.values()) == set(range(len(vocabulary))) and idf.ndim == 1 and len(idf) == len(vocabulary),
         "Invalid model vocabulary")
    need(np.isfinite(idf).all() and (idf >= 1).all(), "Invalid IDF values")
    result = TfidfVectorizer(**VECTORIZER_SETTINGS, max_features=cap, vocabulary=vocabulary)
    result.idf_ = idf.copy()
    return result


def load_model(directory):
    """Load trusted pinned numeric files; caller also checks outer model provenance."""
    directory = Path(directory)
    captures = {}
    for name, cap in (("model.json", 64 * 1024 * 1024), ("arrays.npz", 256 * 1024 * 1024)):
        p = directory / name
        need(p.is_file() and not p.is_symlink() and p.stat().st_size <= cap, "Invalid or oversized model file")
        with p.open("rb") as stream:
            captures[name] = stream.read(cap + 1)
        need(len(captures[name]) <= cap, "Model file grew beyond bounded read limit")
    return load_model_bytes(captures["model.json"], captures["arrays.npz"])


def load_model_bytes(model_raw, arrays_raw):
    """Decode the very buffers whose outer recipe hashes were validated."""
    need(isinstance(model_raw, bytes) and len(model_raw) <= 64 * 1024 * 1024
         and isinstance(arrays_raw, bytes) and len(arrays_raw) <= 256 * 1024 * 1024,
         "Invalid captured model payload")
    metadata = parse_json(model_raw)
    need(isinstance(metadata, dict) and metadata.get("schema_version") == 1 and len(arrays_raw) == metadata.get("arrays_bytes")
         and hashlib.sha256(arrays_raw).hexdigest() == metadata.get("arrays_sha256"), "Model array binding mismatch")
    # Both ZIP inspection and numeric decoding consume the exact captured bytes
    # whose digest was checked, rather than reopening a replaceable path.
    with zipfile.ZipFile(io.BytesIO(arrays_raw)) as archive:
        items = archive.infolist()
        need(len(items) == len(ARRAY_KEYS) and {i.filename for i in items} == {key + ".npy" for key in ARRAY_KEYS}
             and sum(i.file_size for i in items) <= 512 * 1024 * 1024,
             "Oversized or unexpected numeric payload")
    try:
        with np.load(io.BytesIO(arrays_raw), allow_pickle=False) as archive:
            arrays = {k: archive[k].copy() for k in archive.files}
    except (ValueError, TypeError) as error:
        raise ContractError("Non-numeric model payload") from error
    for a in arrays.values():
        need(a.dtype.kind in "iuf" and np.isfinite(a).all(), "Invalid numeric model array")
    corpus = {row["doc_id"]: row for row in metadata["corpus"]}
    need(bool(corpus) and len(corpus) == len(metadata["corpus"]) and all(type(k) is int for k in corpus), "Duplicate or empty model corpus ID set")
    doc_ids = tuple(sorted(corpus))
    retrieval = _vectorizer(metadata["retrieval_vocabulary"], arrays["retrieval_idf"], 100000)
    paired = _vectorizer(metadata["pair_vocabulary"], arrays["pair_idf"], 50000)
    values, indices, indptr = arrays["index_data"], arrays["index_indices"], arrays["index_indptr"]
    need(values.ndim == indices.ndim == indptr.ndim == 1
         and indices.dtype.kind in "iu" and indptr.dtype.kind in "iu",
         "Invalid sparse matrix array types")
    need(len(indices) == len(values) and len(indptr) == len(doc_ids) + 1
         and indptr[0] == 0 and indptr[-1] == len(values)
         and np.all(indptr[1:] >= indptr[:-1])
         and np.all(indices >= 0) and np.all(indices < len(retrieval.vocabulary_)),
         "Invalid sparse matrix index structure")
    index = sparse.csr_matrix((values, indices, indptr),
                              shape=(len(doc_ids), len(retrieval.vocabulary_)))
    width = 4 * len(paired.vocabulary_)
    need(arrays["label_coefficients"].shape == (3, width) and arrays["label_intercepts"].shape == (3,)
         and arrays["rationale_coefficients"].shape == (1, width) and arrays["rationale_intercepts"].shape == (1,),
         "Invalid trained coefficient shape")
    return LinearBaseline(freeze(corpus), doc_ids, retrieval, index, paired,
                          arrays["label_coefficients"], arrays["label_intercepts"],
                          arrays["rationale_coefficients"], arrays["rationale_intercepts"], freeze(metadata["metadata"]))
