"""Pinned official SciFact scoring and complete operational denominators.

No reference labels are loaded implicitly. Callers pass authorized evaluation
objects explicitly after candidate production. This is not an entailment judge.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path, PurePosixPath
import stat
import types
import zipfile

from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical, freeze, parse_json
from .native_contract import (
    _fields, _prediction_shape, _reference_shapes, need,
    validate_prediction, validate_references, validate_schedule,
)

EVALUATOR_COMMIT = '66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb'
EVALUATOR_SHA256 = '2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f'
ARCHIVE_SHA256 = '16a743524ed0bbb83e56d862b7f04475c5fbdd22d21046aecad7583a1bc0b009'
RECEIPT_SHA256 = '2801f35f5af442c3beba3d56135fe471e5f0c098321f30e3f852fbde307652fe'
ARCHIVE_NAME = 'scifact-evaluator-source.zip'
METRIC_FAMILIES = ('abstract_label_only', 'abstract_rationalized',
                   'sentence_selection', 'sentence_label')
PRODUCER_STATUSES = frozenset({'produced', 'parse_failure', 'timeout', 'error',
                               'unexecuted', 'input_unavailable'})
CHECK_STATUSES = frozenset({'accepted', 'rejected', 'error', 'not_run'})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _regular_bytes(path, maximum):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), 'Expected an unaliased regular source file')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum, 'Source exceeds bounded read limit')
    return raw


def _safe_members(archive):
    """Validate member names/types/sizes before any extraction."""
    members, seen, total = [], set(), 0
    for item in archive.infolist():
        # ZipInfo normalizes Windows backslashes and truncates NULs when read.
        # Validate the original central-directory name before accepting that view.
        raw = item.orig_filename
        parts = PurePosixPath(raw).parts
        need(raw == item.filename and raw and '\\' not in raw and ':' not in raw and not raw.startswith('/')
             and all(part not in ('', '.', '..') for part in raw.rstrip('/').split('/')),
             'Unsafe evaluator archive path')
        key = raw.rstrip('/').casefold()
        need(len(parts) >= 1 and key not in seen, 'Duplicate evaluator archive member')
        seen.add(key)
        mode = item.external_attr >> 16
        need(not stat.S_ISLNK(mode), 'Evaluator archive links are forbidden')
        kind = stat.S_IFMT(mode)
        need(kind in (0, stat.S_IFREG, stat.S_IFDIR), 'Unsupported evaluator archive member type')
        need(not item.flag_bits & 1, 'Encrypted evaluator archive member')
        total += item.file_size
        need(item.file_size <= 1024 * 1024 and total <= 8 * 1024 * 1024
             and len(members) < 100, 'Evaluator archive exceeds bounded extraction limits')
        members.append(item)
    return members


def materialize_official_evaluator(acquisition_root, output):
    """Extract the exact acquired upstream source to a new directory.

    The archive and original transport receipt are hard-pinned. Original upstream
    fixture files are preserved as source assets but never used as our controls.
    """
    acquisition_root, output = Path(acquisition_root), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    publish_bytes(output / 'STARTED.json', canonical({'started_at_utc': _now(),
                  'operation': 'materialize_pinned_official_scorer'}) + b'\n')
    try:
        receipt_raw = _regular_bytes(acquisition_root / (ARCHIVE_NAME + '.receipt.json'), 65536)
        need(_digest(receipt_raw) == RECEIPT_SHA256, 'Official scorer receipt hash mismatch')
        receipt = parse_json(receipt_raw)
        raw = _regular_bytes(acquisition_root / ARCHIVE_NAME, 8 * 1024 * 1024)
        need(_digest(raw) == ARCHIVE_SHA256 == receipt.get('sha256'),
             'Official scorer archive hash mismatch')
        need(receipt.get('status') == 'downloaded_not_parsed'
             and receipt.get('bytes') == len(raw)
             and receipt.get('url') == f'https://codeload.github.com/allenai/scifact-evaluator/zip/{EVALUATOR_COMMIT}',
             'Official scorer receipt identity/status mismatch')
        rows = []
        prefix = f'scifact-evaluator-{EVALUATOR_COMMIT}/'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = _safe_members(archive)
            # Validate all roots before publishing any archive member.
            need(all(item.filename.startswith(prefix) for item in members),
                 'Unexpected evaluator archive root')
            for item in members:
                relative = item.filename[len(prefix):]
                if item.is_dir():
                    continue
                need(relative and relative not in ('STARTED.json', 'FAILED.json', 'MATERIALIZED.json'),
                     'Reserved evaluator output path')
                payload = archive.read(item)
                need(len(payload) == item.file_size, 'Incomplete evaluator archive member')
                publish_bytes(output / relative, payload)
                rows.append({'path': relative, 'bytes': len(payload), 'sha256': _digest(payload)})
        evaluator = output / 'evaluator/eval.py'
        need(_digest(_regular_bytes(evaluator, 1024 * 1024)) == EVALUATOR_SHA256,
             'Official scorer source hash mismatch')
        publish_bytes(output / 'MATERIALIZED.json', canonical({
            'schema_version': 1, 'completed_at_utc': _now(), 'commit': EVALUATOR_COMMIT,
            'archive_sha256': ARCHIVE_SHA256, 'receipt_sha256': RECEIPT_SHA256,
            'license': 'Apache-2.0', 'files': rows,
            'upstream_fixtures_used_for_qualification': False,
        }) + b'\n')
        return evaluator
    except BaseException as error:
        publish_bytes(output / 'FAILED.json', canonical({'failed_at_utc': _now(),
                      'error_type': type(error).__name__, 'error': str(error)}) + b'\n')
        raise


def _official_module(evaluator_path):
    raw = _regular_bytes(evaluator_path, 1024 * 1024)
    need(_digest(raw) == EVALUATOR_SHA256, 'Official scorer source hash mismatch')
    module = types.ModuleType('tether_pinned_scifact_evaluator_' + EVALUATOR_COMMIT)
    module.__file__ = str(Path(evaluator_path).resolve())
    # Execute the already-read exact hash-pinned upstream bytes. Do not reopen a
    # mutable path through an import loader, or import symbols from archived JSON.
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def official_metrics(golds, predictions, *, evaluator_path):
    """Return all 12 official metrics from exact upstream code.

    This function checks native shape and exact ID order. Corpus sentence bounds
    require validate_prediction / evaluate_schedule with an explicit corpus.
    """
    need(isinstance(golds, Sequence) and bool(golds), 'References must be nonempty')
    schedule = validate_schedule([entry.get('id') if isinstance(entry, Mapping) else None for entry in golds])
    references = _reference_shapes(golds, schedule)
    need(isinstance(predictions, Sequence) and len(predictions) == len(schedule),
         'Prediction count does not match schedule')
    checked = [_prediction_shape(pred, expected_claim_id=claim_id)
               for claim_id, pred in zip(schedule, predictions)]
    module = _official_module(evaluator_path)
    unified = [module.unify_label(row) for row in references]
    actual = module.Evaluator(verbose=True).evaluate(unified, checked)
    expected = {f'{family}_{name}' for family in METRIC_FAMILIES
                for name in ('precision', 'recall', 'f1')}
    need(set(actual) == expected, 'Pinned scorer returned unexpected metric fields')
    need(all(type(value) in (int, float) and 0 <= value <= 1 for value in actual.values()),
         'Pinned scorer returned invalid metric values')
    return freeze(actual)


def strict_correct(gold, prediction):
    """Supplemental exact-document/label correctness with native rationale cap.

    Call on validated native objects. A successful empty-evidence prediction is
    correct only for empty gold; callers must exclude operational placeholders.
    """
    if gold['id'] != prediction['id'] or set(gold['evidence']) != set(prediction['evidence']):
        return False
    for doc_id, rationales in gold['evidence'].items():
        pred = prediction['evidence'][doc_id]
        if pred['label'] != rationales[0]['label']:
            return False
        cap = max(3, min(len(item['sentences']) for item in rationales))
        predicted = set(pred['sentences'][:cap])
        if not any(set(item['sentences']) <= predicted for item in rationales):
            return False
    return True


def _dispositions(schedule, corpus, records):
    need(isinstance(records, Sequence) and len(records) == len(schedule),
         'Disposition count does not match schedule')
    checked = []
    for claim_id, record in zip(schedule, records):
        _fields(record, ('id', 'producer_status', 'check_status', 'prediction'), ('reason',))
        need(type(record['id']) is int and record['id'] == claim_id,
             'Disposition ordering/identity does not match schedule')
        produced, check = record['producer_status'], record['check_status']
        need(isinstance(produced, str) and produced in PRODUCER_STATUSES, 'Unknown producer disposition')
        need(isinstance(check, str) and check in CHECK_STATUSES, 'Unknown check disposition')
        reason = record.get('reason')
        need(reason is None or isinstance(reason, str) and bool(reason.strip()), 'Invalid disposition reason')
        if produced == 'produced':
            pred = validate_prediction(record['prediction'], corpus, expected_claim_id=claim_id)
            if check in ('rejected', 'error'):
                need(reason is not None, 'Rejected/failed check requires a retained reason')
        else:
            need(record['prediction'] is None and check == 'not_run',
                 'Failed/unexecuted producer cannot have a prediction or check result')
            need(produced == 'unexecuted' or reason is not None,
                 'Failed producer requires a retained reason')
            pred = None
        checked.append({'id': claim_id, 'producer_status': produced,
                        'check_status': check, 'prediction': pred, 'reason': reason})
    return freeze(checked)


def evaluate_schedule(schedule, corpus, golds, records, *, evaluator_path):
    """Score both paired arms, retaining every scheduled operational outcome."""
    schedule = validate_schedule(schedule)
    references = validate_references(golds, corpus, schedule)
    records = _dispositions(schedule, corpus, records)
    raw_predictions, checked_predictions, cases = [], [], []
    counts = Counter({name: 0 for name in ('produced', 'accepted', 'correct_raw',
        'correct_and_admitted', 'correct_but_policy_rejected', 'correct_but_not_admitted',
        'successful_native_nei', 'correct_native_nei', 'raw_failure_placeholders',
        'checked_failure_or_rejection_placeholders')})
    producer_counts, check_counts = Counter(), Counter()
    for gold, record in zip(references, records):
        producer_counts[record['producer_status']] += 1
        check_counts[record['check_status']] += 1
        produced = record['producer_status'] == 'produced'
        accepted = produced and record['check_status'] == 'accepted'
        empty = {'id': record['id'], 'evidence': {}}
        raw = record['prediction'] if produced else empty
        checked = raw if accepted else empty
        raw_predictions.append(raw)
        checked_predictions.append(checked)
        correct = strict_correct(gold, raw) if produced else None
        useful = bool(accepted and correct)
        native_nei = bool(produced and not raw['evidence'])
        counts['produced'] += produced
        counts['accepted'] += accepted
        counts['correct_raw'] += bool(correct)
        counts['correct_and_admitted'] += useful
        counts['correct_but_policy_rejected'] += bool(correct and record['check_status'] == 'rejected')
        counts['correct_but_not_admitted'] += bool(correct and not accepted)
        counts['successful_native_nei'] += native_nei
        counts['correct_native_nei'] += bool(native_nei and correct)
        counts['raw_failure_placeholders'] += not produced
        counts['checked_failure_or_rejection_placeholders'] += not accepted
        cases.append({'id': record['id'], 'producer_status': record['producer_status'],
                      'check_status': record['check_status'], 'reason': record['reason'],
                      'prediction_produced': produced, 'native_nei_prediction': native_nei,
                      'raw_strict_correct': correct, 'checked_strict_correct': useful,
                      'raw_is_placeholder': not produced, 'checked_is_placeholder': not accepted})
    count = len(schedule)
    return freeze({'schema_version': 1, 'scheduled_count': count,
        'projection_policy': 'failure_as_empty_for_native_metrics_only',
        'strict_case_rule': 'exact_evidence_documents_and_labels_with_complete_native_capped_rationale',
        'official_evaluator': {'commit': EVALUATOR_COMMIT, 'sha256': EVALUATOR_SHA256},
        'raw_metrics': official_metrics(references, raw_predictions, evaluator_path=evaluator_path),
        'checked_metrics': official_metrics(references, checked_predictions, evaluator_path=evaluator_path),
        'counts': dict(counts), 'producer_status_counts': dict(producer_counts),
        'check_status_counts': dict(check_counts), 'case_results': cases,
        'rates': {'produced_per_scheduled': counts['produced'] / count,
                  'accepted_per_scheduled': counts['accepted'] / count,
                  'correct_raw_per_scheduled': counts['correct_raw'] / count,
                  'correct_and_admitted_per_scheduled': counts['correct_and_admitted'] / count}})
