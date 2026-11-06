"""Strict LitQA2 task/answer codec; evidence is an added declared interface.

Native correctness is a multiple-choice answer. This module deliberately does
not make source-backed admission or semantic-support decisions.
"""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from asof.serde import ContractError, freeze, parse_json

UNSURE_TEXT = "Insufficient information to answer the question"
MAX_RESPONSE_BYTES = 65536
MAX_EVIDENCE_IDS = 64


def _fields(value, keys, name):
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise ContractError(f"{name} requires exactly {sorted(keys)}")


def validate_query(value):
    _fields(value, ("id", "question", "choices"), "query")
    try:
        if not isinstance(value["id"], str) or str(UUID(value["id"])) != value["id"]:
            raise ValueError("noncanonical UUID")
    except (ValueError, TypeError, AttributeError) as error:
        raise ContractError("Query id must be a canonical UUID") from error
    if not isinstance(value["question"], str) or not value["question"].strip():
        raise ContractError("Query question must be nonempty text")
    choices = value["choices"]
    if not isinstance(choices, (list, tuple)) or not 2 <= len(choices) <= 26:
        raise ContractError("Query choices must contain 2 through 26 labeled options")
    texts = []
    for index, choice in enumerate(choices):
        prefix = f"({chr(65 + index)}) "
        if not isinstance(choice, str) or not choice.startswith(prefix) or not choice[len(prefix):].strip():
            raise ContractError("Query choices require exact sequential native letter prefixes")
        texts.append(choice[len(prefix):])
    if len(set(texts)) != len(texts) or texts.count(UNSURE_TEXT) != 1:
        raise ContractError("Query choices require unique text and one visible unsure option")
    return freeze(value)


def visible_unsure_index(query):
    query = validate_query(query)
    return next(i for i, choice in enumerate(query["choices"]) if choice[4:] == UNSURE_TEXT)


def evidence_ids(value):
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ContractError("Offered evidence IDs must be a finite collection")
    if any(not isinstance(key, str) or not key.strip() for key in value) or len(set(value)) != len(value):
        raise ContractError("Evidence IDs must be unique nonempty strings")
    return frozenset(value)


def validate_prediction(value, query, allowed_evidence_ids):
    query = validate_query(query)
    allowed = evidence_ids(allowed_evidence_ids)
    _fields(value, ("answer_index", "evidence_ids"), "prediction")
    index = value["answer_index"]
    if type(index) is not int or not 0 <= index < len(query["choices"]):
        raise ContractError("Prediction answer_index is outside the visible choices")
    selected = value["evidence_ids"]
    if not isinstance(selected, (list, tuple)) or len(selected) > MAX_EVIDENCE_IDS:
        raise ContractError("Prediction evidence_ids must be a bounded array")
    if not evidence_ids(selected).issubset(allowed):
        raise ContractError("Prediction cites evidence not offered to the producer")
    return freeze(value)


def parse_prediction(raw, query, allowed_evidence_ids):
    if not isinstance(raw, (bytes, str)):
        raise ContractError("Prediction response must be UTF-8 JSON bytes or text")
    try:
        size = len(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
    except UnicodeError as error:
        raise ContractError("Prediction response is not valid UTF-8") from error
    if size > MAX_RESPONSE_BYTES:
        raise ContractError("Prediction response exceeds 64 KiB")
    return validate_prediction(parse_json(raw), query, allowed_evidence_ids)
