"""Pure retained-byte adapters for the separate source-reporting study.

No source, reference value, quote expansion, coercion, omission insertion or
deduplication is available here. Structural acceptance is not source verification.
Bounds are 256 KiB, 512 facts, 512-character identifiers/binding strings/units,
1,800-character reasons, and JSON values with 8,192-character strings, depth 16,
at most 4,096 nodes and at most 4,096 entries per container. A value root has
depth zero and counts as one node. Legacy bounds retain the v2 three-claim,
two-reference, four-list-item, 1,800-character text and 512-character reason caps.
"""

import hashlib
import math
import re

from tether_engine.serde import ContractError, freeze, parse_json


WIRE_FORMATS = ("typed_facts_v1", "interpretation_v2")
STATUSES = ("answered", "partial", "abstained", "insufficient_input")
COLLECTION_STATUSES = (
    "selected_records", "zero_matches_selected_collection", "incomplete", "failed_qc"
)
MAX_RAW_BYTES = 256 * 1024
MAX_FACTS = 512
MAX_IDENTIFIER_CHARACTERS = 512
MAX_REASON_CHARACTERS = 1800
MAX_VALUE_STRING_CHARACTERS = 8192
MAX_VALUE_DEPTH = 16
MAX_VALUE_NODES = 4096
MAX_CONTAINER_ENTRIES = 4096
MAX_LEGACY_CLAIMS = 3
MAX_LEGACY_TEXT_CHARACTERS = 1800
MAX_LEGACY_REASON_CHARACTERS = 512
MAX_LEGACY_LIST_ITEMS = 4
MAX_LEGACY_QUOTE_REFS = 2
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_POINTER = re.compile(r"(?:/(?:[^~]|~[01])*)*\Z")
_QUOTE_ID = re.compile(r"Q(?:0|[1-9][0-9]*)\Z")


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _string(value, maximum, *, nonblank=True):
    valid = (
        type(value) is str
        and len(value) <= maximum
        and (not nonblank or bool(value.strip()))
    )
    if valid:
        try:
            value.encode("utf-8")
        except UnicodeError:
            valid = False
    return valid


def _hash(value):
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _shape(value, keys, message):
    _need(type(value) is dict and set(value) == set(keys), message)


def _json_value(value):
    """Bound native JSON without changing its scalar types, strings or order."""
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        _need(nodes <= MAX_VALUE_NODES, "Fact value exceeds JSON node bound")
        _need(depth <= MAX_VALUE_DEPTH, "Fact value exceeds JSON depth bound")
        kind = type(item)
        if kind is str:
            _need(_string(item, MAX_VALUE_STRING_CHARACTERS, nonblank=False),
                  "Invalid fact value string")
        elif kind is float:
            _need(math.isfinite(item), "Fact value must be finite")
        elif item is None or kind in (bool, int):
            continue
        elif kind in (dict, list):
            _need(len(item) <= MAX_CONTAINER_ENTRIES,
                  "Fact value exceeds JSON container bound")
            if kind is dict:
                _need(all(_string(key, MAX_VALUE_STRING_CHARACTERS, nonblank=False)
                          for key in item), "Invalid fact value object key")
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1) for child in children)
        else:
            raise ContractError("Fact value must contain native JSON types")


def _locator(locator):
    _need(type(locator) is dict, "Invalid physical source locator")
    if locator.get("format") == "json":
        _shape(locator, ("format", "pointer"), "Invalid JSON source locator shape")
        location = locator["pointer"]
        _need(_string(location, MAX_VALUE_STRING_CHARACTERS, nonblank=False)
              and _POINTER.fullmatch(location) is not None,
              "Invalid RFC6901 source pointer")
    elif locator.get("format") == "parquet":
        _shape(locator, ("format", "row_group", "row"),
               "Invalid Parquet source locator shape")
        _need(all(type(locator[key]) is int and locator[key] >= 0
                  for key in ("row_group", "row")),
              "Parquet source indices must be nonnegative integers")
    else:
        raise ContractError("Unknown physical source locator format")


def _source(source):
    _shape(source, ("source_id", "sha256", "release_id", "locator", "field"),
           "Invalid complete emitted source binding")
    _need(all(_string(source[key], MAX_IDENTIFIER_CHARACTERS)
              for key in ("source_id", "release_id", "field")),
          "Invalid emitted source binding string")
    _need(_hash(source["sha256"]), "Invalid emitted source SHA-256")
    _locator(source["locator"])


def _typed(document, task_id, task_sha256):
    _shape(document, ("schema_version", "task_id", "task_sha256", "status", "facts",
                      "collection_status", "reason"), "Invalid typed-facts output shape")
    _need(type(document["schema_version"]) is int and document["schema_version"] == 1,
          "Invalid typed-facts schema version")
    _need(type(document["task_id"]) is str and document["task_id"] == task_id
          and type(document["task_sha256"]) is str
          and document["task_sha256"] == task_sha256,
          "Typed-facts task binding differs")
    status, facts, reason = document["status"], document["facts"], document["reason"]
    _need(type(status) is str and status in STATUSES, "Invalid typed-facts status")
    _need(type(facts) is list and len(facts) <= MAX_FACTS, "Invalid emitted fact array")
    _need(reason is None or _string(reason, MAX_REASON_CHARACTERS),
          "Invalid typed-facts reason")
    _need((status == "answered" and bool(facts) and reason is None)
          or (status == "partial" and bool(facts) and reason is not None)
          or (status in ("abstained", "insufficient_input")
              and not facts and reason is not None),
          "Typed-facts status, facts and reason disagree")
    _need(type(document["collection_status"]) is str
          and document["collection_status"] in COLLECTION_STATUSES,
          "Invalid collection disposition")
    for fact in facts:
        _shape(fact, ("fact_id", "value", "unit", "source", "unknown_reason"),
               "Invalid emitted fact shape")
        _need(_string(fact["fact_id"], MAX_IDENTIFIER_CHARACTERS), "Invalid fact ID")
        _need(fact["unit"] is None or _string(fact["unit"], MAX_IDENTIFIER_CHARACTERS),
              "Invalid emitted unit")
        _json_value(fact["value"])
        _need((_string(fact["unknown_reason"], MAX_REASON_CHARACTERS)
               if fact["value"] is None else fact["unknown_reason"] is None),
              "Emitted value and unknown reason disagree")
        _source(fact["source"])
    return document


def _legacy_strings(value, maximum_items):
    _need(type(value) is list and len(value) <= maximum_items
          and all(_string(item, MAX_LEGACY_TEXT_CHARACTERS) for item in value),
          "Invalid legacy text list")


def _legacy(document):
    """Check original v2 wire shape only; no quote catalog or expected values."""
    _shape(document, ("answer_status", "claims", "unresolved", "abstention_reason"),
           "Invalid legacy interpretation shape")
    status, claims, reason = (document["answer_status"], document["claims"],
                              document["abstention_reason"])
    _need(type(status) is str and status in ("answered", "partial", "abstained"),
          "Invalid legacy answer state")
    _need(type(claims) is list and len(claims) <= MAX_LEGACY_CLAIMS,
          "Invalid legacy claim array")
    _need(reason is None or _string(reason, MAX_LEGACY_REASON_CHARACTERS),
          "Invalid legacy abstention reason")
    _need((status == "answered" and bool(claims) and reason is None)
          or (status == "partial" and bool(claims) and reason is not None)
          or (status == "abstained" and not claims and reason is not None),
          "Legacy state, claims and reason disagree")
    _legacy_strings(document["unresolved"], MAX_LEGACY_LIST_ITEMS)
    seen = set()
    for claim in claims:
        _shape(claim, ("kind", "text", "quote_refs", "limitations"),
               "Invalid legacy claim shape")
        kind = claim["kind"]
        _need(type(kind) is str and kind in ("source_report", "scientific_inference", "caution"),
              "Invalid legacy claim kind")
        _need(_string(claim["text"], MAX_LEGACY_TEXT_CHARACTERS)
              and claim["text"] not in seen, "Invalid or duplicate legacy claim text")
        seen.add(claim["text"])
        _legacy_strings(claim["limitations"], MAX_LEGACY_LIST_ITEMS)
        _need(kind == "source_report" or bool(claim["limitations"]),
              "Legacy inference requires limitations")
        refs = claim["quote_refs"]
        _need(type(refs) is list and 1 <= len(refs) <= MAX_LEGACY_QUOTE_REFS
              and all(_string(ref, MAX_IDENTIFIER_CHARACTERS)
                      and _QUOTE_ID.fullmatch(ref) is not None and int(ref[1:]) < 256
                      for ref in refs)
              and len(set(refs)) == len(refs), "Invalid legacy quote references")
        _need(kind != "source_report" or len(refs) == 1,
              "Legacy source report requires one quote reference")


def adapt_output(raw: bytes, *, wire_format: str, task_id: str, task_sha256: str):
    """Return an immutable terminal adaptation, preserving only emitted facts.

    Invalid trusted caller configuration (including non-byte input) raises
    ContractError. Every invalid byte payload instead returns ``malformed`` with
    its exact retained-byte digest. Valid legacy prose is ``unscorable_legacy``.
    Caller-owned storage must retain original bytes; this adapter never writes.
    """
    _need(type(raw) is bytes, "Adapter requires retained bytes")
    _need(type(wire_format) is str and wire_format in WIRE_FORMATS,
          "Unknown trusted adapter wire format")
    _need(_string(task_id, MAX_IDENTIFIER_CHARACTERS), "Invalid trusted task ID")
    _need(_hash(task_sha256), "Invalid trusted task SHA-256")
    result = dict(status="malformed", output=None,
                  raw_sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw),
                  error=None, wire_format=wire_format)
    try:
        _need(len(raw) <= MAX_RAW_BYTES, "Retained output exceeds 256 KiB")
        document = parse_json(raw)
        if wire_format == "typed_facts_v1":
            result.update(status="scorable", output=_typed(document, task_id, task_sha256))
        else:
            _legacy(document)
            result["status"] = "unscorable_legacy"
    except (ContractError, TypeError, ValueError, RecursionError, OverflowError) as error:
        message = str(error).encode("utf-8", "backslashreplace").decode("utf-8")[:240]
        result.update(status="malformed", output=None,
                      error=f"{type(error).__name__}: {message}")
    return freeze(result)
