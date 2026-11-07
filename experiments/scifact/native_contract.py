"""Strict native SciFact shapes; validation never implies semantic truth.

Prediction sentence order is significant to the official abstract scorer and is
preserved. Empty evidence is a task prediction, not an operational disposition.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import re

from tether_engine.serde import ContractError, freeze, parse_json

MAX_PREDICTION_BYTES = 1024 * 1024
LABELS = frozenset({'SUPPORT', 'CONTRADICT'})


def need(condition, message):
    if not condition:
        raise ContractError(message)


def _sequence(value):
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _native_id(value, title):
    need(type(value) is int and value >= 0, f'{title} must be a nonnegative integer')
    return value


def _document_id(value):
    need(isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]*', value) is not None,
         'Document ID must be a canonical nonnegative integer string')
    return int(value)


def _fields(value, required, optional=()):
    need(isinstance(value, Mapping), 'Native object must be a mapping')
    keys = set(value)
    need(set(required) <= keys and keys <= set(required) | set(optional),
         'Native object has missing or unknown fields')


def _document(corpus, doc_id):
    native = _document_id(doc_id)
    need(isinstance(corpus, Mapping), 'Corpus must be a document-ID mapping')
    keys = [key for key in (native, doc_id) if key in corpus]
    need(len(keys) <= 1, 'Ambiguous integer/string corpus document alias')
    need(len(keys) == 1, 'Predicted or reference document is absent from corpus')
    record = corpus[keys[0]]
    need(isinstance(record, Mapping) and _sequence(record.get('abstract')),
         'Corpus document must retain ordered abstract sentences')
    need(all(isinstance(text, str) for text in record['abstract']),
         'Corpus abstract sentence must be text')
    return record


def _sentences(value, corpus=None, doc_id=None, *, nonempty=False):
    need(_sequence(value), 'Sentence IDs must be a sequence')
    result = tuple(value)
    need(all(type(item) is int and item >= 0 for item in result),
         'Sentence IDs must be nonnegative integers')
    need(len(set(result)) == len(result), 'Duplicate sentence IDs')
    need(not nonempty or bool(result), 'Gold rationale cannot be empty')
    if corpus is not None:
        count = len(_document(corpus, doc_id)['abstract'])
        need(all(item < count for item in result), 'Sentence ID outside original abstract')
    return result


def validate_schedule(schedule):
    """Return immutable scheduled IDs, preserving the declared order."""
    need(_sequence(schedule) and bool(schedule), 'Schedule must be nonempty')
    result = tuple(_native_id(item, 'Scheduled claim ID') for item in schedule)
    need(len(set(result)) == len(result), 'Duplicate scheduled claim IDs')
    return result


def _prediction_shape(value, *, expected_claim_id=None, corpus=None):
    _fields(value, ('id', 'evidence'))
    claim_id = _native_id(value['id'], 'Claim ID')
    if expected_claim_id is not None:
        _native_id(expected_claim_id, 'Expected claim ID')
        need(claim_id == expected_claim_id, 'Prediction claim identity mismatch')
    need(isinstance(value['evidence'], Mapping), 'Evidence must be a mapping')
    evidence = {}
    for doc_id, row in value['evidence'].items():
        _document_id(doc_id)
        _fields(row, ('label', 'sentences'))
        need(isinstance(row['label'], str) and row['label'] in LABELS,
             'Native document label must be SUPPORT or CONTRADICT')
        if corpus is not None:
            _document(corpus, doc_id)
        evidence[doc_id] = {'label': row['label'],
                            'sentences': _sentences(row['sentences'], corpus, doc_id)}
    return freeze({'id': claim_id, 'evidence': evidence})


def validate_prediction(value, corpus, *, expected_claim_id=None):
    """Copy/freeze a native prediction, checking source IDs and sentence bounds.

    This validates schema and locators only; no reference label is consulted.
    Corpus identity, authorization and source bytes are the policy adapter's job.
    """
    need(isinstance(corpus, Mapping), 'Corpus must be a document-ID mapping')
    return _prediction_shape(value, expected_claim_id=expected_claim_id, corpus=corpus)


def parse_prediction(payload, corpus, *, expected_claim_id=None):
    need(isinstance(payload, bytes) and len(payload) <= MAX_PREDICTION_BYTES,
         'Native prediction must be bytes within the 1 MiB limit')
    return validate_prediction(parse_json(payload), corpus,
                               expected_claim_id=expected_claim_id)


def _reference_shapes(references, schedule, corpus=None):
    schedule = validate_schedule(schedule)
    need(_sequence(references) and len(references) == len(schedule),
         'Reference count does not match schedule')
    result = []
    for expected_id, row in zip(schedule, references):
        _fields(row, ('id', 'evidence'), ('claim', 'cited_doc_ids'))
        need(_native_id(row['id'], 'Reference claim ID') == expected_id,
             'Reference ordering/identity does not match schedule')
        if 'claim' in row:
            need(isinstance(row['claim'], str), 'Reference claim must be text')
        if 'cited_doc_ids' in row:
            need(_sequence(row['cited_doc_ids']), 'Reference citation IDs must be a sequence')
            ids = tuple(_native_id(item, 'Cited document ID') for item in row['cited_doc_ids'])
            if corpus is not None:
                for doc_id in ids:
                    _document(corpus, str(doc_id))
        need(isinstance(row['evidence'], Mapping), 'Reference evidence must be a mapping')
        evidence = {}
        for doc_id, rationales in row['evidence'].items():
            _document_id(doc_id)
            need(_sequence(rationales) and bool(rationales), 'Gold document must have rationales')
            checked, labels, seen = [], set(), set()
            for rationale in rationales:
                _fields(rationale, ('label', 'sentences'))
                label = rationale['label']
                need(isinstance(label, str) and label in LABELS, 'Invalid gold evidence label')
                sentences = _sentences(rationale['sentences'], corpus, doc_id, nonempty=True)
                need(not seen.intersection(sentences),
                     'Overlapping gold rationale sets unsupported by the pinned official scorer')
                seen.update(sentences)
                labels.add(label)
                checked.append({'label': label, 'sentences': sentences})
            need(len(labels) == 1, 'Conflicting gold document labels')
            evidence[doc_id] = checked
        checked_row = {'id': expected_id, 'evidence': evidence}
        # Preserve optional original metadata. Citation repetitions are legal
        # metadata and have no effect on native metric denominators.
        for field in ('claim', 'cited_doc_ids'):
            if field in row:
                checked_row[field] = row[field]
        result.append(checked_row)
    return freeze(result)


def validate_references(references, corpus, schedule):
    """Evaluator-only validation of native references and exact schedule order."""
    need(isinstance(corpus, Mapping), 'Corpus must be a document-ID mapping')
    return _reference_shapes(references, schedule, corpus)
