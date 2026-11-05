"""Bounded fictional baseline math and verified-byte read review."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import numpy as np
from experiments.scifact import baseline


def main():
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / 'tests'))
    from test_scifact_baseline import fictional
    output = root / sys.argv[1]
    output.mkdir(parents=True, exist_ok=False)
    source = Path(baseline.__file__).read_bytes()
    (output / 'baseline-reviewed.py').write_bytes(source)
    corpus, queries, pairs = fictional()
    models = []
    constructor = baseline.SGDClassifier
    def capture(**settings):
        estimator = constructor(**settings)
        models.append(estimator)
        return estimator
    with patch.object(baseline, 'SGDClassifier', side_effect=capture):
        model = baseline.fit_model(corpus, queries, pairs)
    feature_rows = baseline.pair_features(
        model.pair_vectorizer,
        [queries[0]['claim'], queries[12]['claim'], queries[24]['claim'], 'Previously unseen active signal'],
        [baseline.document_text(corpus[2])] * 4)
    direct = models[0].predict_proba(feature_rows)
    stored = baseline.probabilities(feature_rows, model.label_coefficients, model.label_intercepts, baseline.LABELS)
    np.testing.assert_allclose(direct, stored, rtol=0, atol=1e-14)
    sentence_rows = baseline.pair_features(model.pair_vectorizer,
        [queries[0]['claim']] * 3, corpus[2]['abstract'])
    direct_sentence = models[1].predict_proba(sentence_rows)
    stored_sentence = baseline.probabilities(sentence_rows, model.rationale_coefficients,
                                            model.rationale_intercepts, (0, 1))
    np.testing.assert_allclose(direct_sentence, stored_sentence, rtol=0, atol=1e-14)
    temporary_root = root / 'data/cache/scifact-scoring-test-temp'
    assert temporary_root.resolve().is_relative_to(root)
    with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
        path = Path(temporary) / 'model'
        baseline.save_model(model, path)
        target = path / 'arrays.npz'
        checked = target.read_bytes()
        original_load = np.load
        with original_load(io.BytesIO(checked), allow_pickle=False) as archive:
            altered = {name: archive[name].copy() for name in archive.files}
        altered['label_coefficients'][0, 0] += 10
        buffer = io.BytesIO()
        np.savez_compressed(buffer, **altered)
        replacement = buffer.getvalue()
        def replace_before_load(file, *args, **kwargs):
            target.write_bytes(replacement)
            return original_load(file, *args, **kwargs)
        with patch.object(baseline.np, 'load', side_effect=replace_before_load):
            loaded = baseline.load_model(path)
        checked_model_preserved = np.array_equal(loaded.label_coefficients, model.label_coefficients)
    after = Path(baseline.__file__).read_bytes()
    record = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fictional supervised baseline only; no production data/model fitting',
        'reviewed_source_sha256': hashlib.sha256(source).hexdigest(),
        'source_unchanged_during_review': source == after,
        'document_probability_parity': {'rows': 4, 'values': 12, 'atol': 1e-14, 'passed': True},
        'sentence_probability_parity': {'rows': 3, 'values': 6, 'atol': 1e-14, 'passed': True},
        'checked_array_bytes_preserved_on_path_replacement': checked_model_preserved,
        'finding': 'captured_bytes_preserved' if checked_model_preserved else 'loader_accepts_arrays_different_from_verified_bytes',
        'provider_spend_usd': 0,
    }
    (output / 'REVIEW.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
