"""Retained fictional scorer qualification; no production reference files."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from asof.atomic import publish_bytes
from asof.serde import canonical, encode
from experiments.scifact.evaluate import (
    EVALUATOR_SHA256, evaluate_schedule, materialize_official_evaluator,
    official_metrics,
)


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    publish_bytes(path, canonical(value) + b'\n')


def main():
    root = Path(__file__).resolve().parents[4]
    output = root / sys.argv[1]
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    write(output / 'STARTED.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                                  'scope': 'seven authored fictional claims; no benchmark scores'})
    try:
        reference_root = root / 'data/reference/scifact-evaluator-66feffc5'
        if reference_root.exists():
            evaluator = reference_root / 'evaluator/eval.py'
            assert pin(evaluator)['sha256'] == EVALUATOR_SHA256
        else:
            evaluator = materialize_official_evaluator(
                root / 'data/raw/scifact_public/20261105-attempt01', reference_root)
        paths = [root / 'experiments/scifact/native_contract.py', root / 'experiments/scifact/evaluate.py',
                 root / 'tests/test_scifact_scoring.py', Path(__file__), evaluator,
                 root / 'src/asof/serde.py', root / 'src/asof/atomic.py']
        before = [pin(path) for path in paths]
        for path in paths:
            publish_bytes(output / 'source_snapshots' / path.relative_to(root), path.read_bytes())
        corpus = {10: {'doc_id': 10, 'title': 'Invented A',
                       'abstract': [f'Invented sentence {i}.' for i in range(7)]},
                  20: {'doc_id': 20, 'title': 'Invented B', 'abstract': ['Invented text.']}}
        # Hand-declared cases and counts, deliberately distinct from released fixtures.
        labels = [
            {'id': 1, 'evidence': {'10': [{'label': 'SUPPORT', 'sentences': [0, 1]}]}},
            {'id': 2, 'evidence': {'10': [{'label': 'CONTRADICT', 'sentences': [0]}]}},
            {'id': 3, 'evidence': {}},
            {'id': 4, 'evidence': {'10': [{'label': 'SUPPORT', 'sentences': [0, 1, 2, 3]}]}},
            {'id': 5, 'evidence': {'10': [{'label': 'SUPPORT', 'sentences': [0, 1]},
                                      {'label': 'SUPPORT', 'sentences': [2]}]}},
            {'id': 6, 'evidence': {'10': [{'label': 'SUPPORT', 'sentences': [3, 4]}]}},
            {'id': 7, 'evidence': {}},
        ]
        predictions = [
            {'id': 1, 'evidence': {'10': {'label': 'SUPPORT', 'sentences': [0]}}},
            {'id': 2, 'evidence': {'10': {'label': 'SUPPORT', 'sentences': [0]}}},
            {'id': 3, 'evidence': {}},
            {'id': 4, 'evidence': {'10': {'label': 'SUPPORT', 'sentences': [0, 1, 2, 3, 4]}}},
            {'id': 5, 'evidence': {'10': {'label': 'SUPPORT', 'sentences': [2]}}},
            {'id': 6, 'evidence': {'10': {'label': 'SUPPORT', 'sentences': [0, 1, 2, 3, 4]}}},
            {'id': 7, 'evidence': {'20': {'label': 'SUPPORT', 'sentences': [0]}}},
        ]
        hand_counts = {'abstract_gold': 5, 'abstract_predicted': 6,
                       'abstract_correct_label': 4, 'abstract_correct_rationalized': 2,
                       'sentence_gold': 12, 'sentence_predicted': 14,
                       'sentence_correct_selection': 8, 'sentence_correct_label': 7,
                       'strict_correct_claims': [3, 4, 5]}
        expected = {
            'abstract_label_only_precision': 2/3, 'abstract_label_only_recall': 4/5,
            'abstract_label_only_f1': 8/11,
            'abstract_rationalized_precision': 1/3, 'abstract_rationalized_recall': 2/5,
            'abstract_rationalized_f1': 4/11,
            'sentence_selection_precision': 4/7, 'sentence_selection_recall': 2/3,
            'sentence_selection_f1': 8/13,
            'sentence_label_precision': .5, 'sentence_label_recall': 7/12,
            'sentence_label_f1': 7/13,
        }
        for filename, rows in [('fictional-labels.jsonl', labels), ('fictional-predictions.jsonl', predictions)]:
            publish_bytes(output / filename, b''.join(canonical(row) + b'\n' for row in rows))
        write(output / 'HAND-EXPECTED.json', {'counts': hand_counts, 'metrics': expected})
        command = [sys.executable, '-I', '-B', '-X', 'utf8', str(evaluator),
                   '--labels_file', str(output / 'fictional-labels.jsonl'),
                   '--preds_file', str(output / 'fictional-predictions.jsonl'),
                   '--metrics_output_file', str(output / 'official-cli-metrics.json'), '--verbose']
        write(output / 'COMMAND.json', {'argv': command, 'cwd': str(output), 'timeout_seconds': 30})
        completed = subprocess.run(command, cwd=output, capture_output=True, timeout=30)
        publish_bytes(output / 'official.stdout', completed.stdout)
        publish_bytes(output / 'official.stderr', completed.stderr)
        if completed.returncode:
            raise RuntimeError(f'Official scorer CLI failed: {completed.returncode}')
        actual = json.loads((output / 'official-cli-metrics.json').read_text(encoding='utf-8'))
        api = official_metrics(labels, predictions, evaluator_path=evaluator)
        for result in (actual, api):
            assert set(result) == set(expected)
            for key, value in expected.items():
                assert abs(result[key] - value) < 1e-12, (key, result[key], value)
        records = [{'id': pred['id'], 'producer_status': 'produced', 'check_status': 'accepted',
                    'prediction': pred} for pred in predictions]
        good = evaluate_schedule(list(range(1, 8)), corpus, labels, records, evaluator_path=evaluator)
        assert good['counts']['correct_and_admitted'] == 3
        records[2] = {'id': 3, 'producer_status': 'timeout', 'check_status': 'not_run',
                      'prediction': None, 'reason': 'Invented timeout on empty-gold claim'}
        failed = evaluate_schedule(list(range(1, 8)), corpus, labels, records, evaluator_path=evaluator)
        assert failed['counts']['correct_and_admitted'] == 2
        assert failed['raw_metrics'] == good['raw_metrics']
        assert failed['case_results'][2]['raw_strict_correct'] is None
        write(output / 'SUCCESSFUL-NEI-PANEL.json', good)
        write(output / 'FAILED-NEI-PANEL.json', failed)
        assert before == [pin(path) for path in paths], 'Qualification source changed during execution'
        write(output / 'VALIDATION.json', {
            'status': 'PASS', 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds': time.monotonic() - started, 'source_pins': before,
            'source_bracket_unchanged': True,
            'output_pins': [pin(p) for p in sorted(output.iterdir()) if p.is_file()],
            'official_cli_exit_code': completed.returncode, 'native_metric_fields_checked': 12,
            'hand_counted_claims': 7, 'operational_placeholder_contrast_pass': True,
            'production_references_read': False, 'scientific_benchmark_result': False,
        })
        print(json.dumps({'status': 'PASS', 'output': str(output),
                          'evaluator_path': str(evaluator), 'metrics_checked': 12}))
    except BaseException as error:
        write(output / 'FAILED.json', {'error_type': type(error).__name__, 'error': str(error),
                                     'failed_at_utc': datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == '__main__':
    main()
