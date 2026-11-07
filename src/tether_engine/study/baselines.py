"""Pure, synthetic-only source extraction; no model or scientific answer attempt.

Public execution accepts only authenticated packaged diagnostic fixture identities.
Text matching ranks literal source statements, never biological evidence strength.
"""

import hashlib
import re
import unicodedata

from tether_engine.serde import canonical, encode, fingerprint, freeze

from .diagnostic import REQUIRED_RESOURCES as REQUIRED_RESOURCES
from .diagnostic import load_synthetic_request
from .diagnostic_codec import need, validate_request

FIXTURES = ("synthetic-context", "synthetic-orientation")
TOKENIZER = "unicode-nfkc-casefold-word-set.v1"
MAX_BYTES = 1048576


def _policy(policy):
    p = encode(policy)
    need(
        isinstance(p, dict)
        and set(p)
        == {
            "schema_version",
            "method",
            "query",
            "max_excerpts",
            "max_quote_bytes",
            "max_request_bytes",
            "max_result_bytes",
        },
        "Invalid complete baseline policy",
    )
    need(
        type(p["schema_version"]) is int and p["schema_version"] == 1,
        "Invalid baseline policy version",
    )
    need(p["method"] in ("extractive", "lexical"), "Invalid baseline method")
    need(
        (p["method"] == "extractive" and p["query"] is None)
        or (p["method"] == "lexical" and isinstance(p["query"], str)),
        "Invalid explicit baseline query",
    )
    need(
        p["query"] is None or len(p["query"].encode("utf-8")) <= 8192,
        "Baseline query exceeds bound",
    )
    need(
        type(p["max_excerpts"]) is int and 0 <= p["max_excerpts"] <= 64,
        "Invalid excerpt count",
    )
    for field, ceiling in (
        ("max_quote_bytes", 8192),
        ("max_request_bytes", MAX_BYTES),
        ("max_result_bytes", MAX_BYTES),
    ):
        need(
            type(p[field]) is int and 0 < p[field] <= ceiling,
            "Invalid baseline byte bound",
        )
    return freeze(p)


def _authenticated(request):
    request = validate_request(request)
    for row in request["source_request"]["evidence"]:
        need(
            row["admitted_sha256"] == fingerprint(row["scientific_record"]),
            "Baseline source fingerprint differs",
        )
        need(
            encode(row["source_ref"]) == {"kind": "synthetic_fixture_not_admitted"},
            "Baseline source reference is not the synthetic-only contract",
        )
    need(
        any(
            canonical(request) == canonical(load_synthetic_request(name))
            for name in FIXTURES
        ),
        "Baseline public execution requires an authenticated packaged synthetic request",
    )
    return request


def _tokens(text):
    return set(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def _select(rows, policy):
    """Pure invented-string test seam; not public admission or result publication."""
    ranked = []
    query = _tokens(policy["query"]) if policy["method"] == "lexical" else set()
    for row in rows:
        text = row["scientific_record"]["statement"]
        score = len(query & _tokens(text)) if policy["method"] == "lexical" else None
        ranked.append((row, text, score))
    ranked.sort(
        key=lambda item: (-(item[2] or 0), item[0]["observation_id"], "/statement")
    )
    quotes, trace = [], []
    for rank, (row, text, score) in enumerate(ranked, 1):
        raw = text.encode("utf-8")
        if not text:
            disposition = "empty"
        elif len(raw) > policy["max_quote_bytes"]:
            disposition = "too_large"
        elif policy["method"] == "lexical" and score == 0:
            disposition = "zero_overlap"
        elif len(quotes) >= policy["max_excerpts"]:
            disposition = "count_bound"
        else:
            disposition = "selected"
        trace.append(
            dict(
                observation_id=row["observation_id"],
                pointer="/statement",
                rank=rank,
                retrieval_score=score,
                utf8_bytes=len(raw),
                disposition=disposition,
            )
        )
        if disposition == "selected":
            quotes.append(
                dict(
                    observation_id=row["observation_id"],
                    source_record_sha256=row["admitted_sha256"],
                    source_ref=encode(row["source_ref"]),
                    pointer="/statement",
                    character_span=[0, len(text)],
                    utf8_span=[0, len(raw)],
                    text=text,
                    text_sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
    return quotes, trace


def run_baseline(request, policy):
    """Return immutable exact quotes from authenticated invented fixtures only."""
    p = _policy(policy)
    need(
        len(canonical(request)) <= p["max_request_bytes"],
        "Baseline request exceeds byte cap",
    )
    req = _authenticated(request)
    source = req["source_request"]
    need(
        p["max_excerpts"] <= source["bounds"]["max_claims"],
        "Baseline excerpt count exceeds request bound",
    )
    need(
        p["max_quote_bytes"] <= source["bounds"]["max_text_bytes"],
        "Baseline quote bytes exceed request bound",
    )
    quotes, trace = _select(source["evidence"], p)
    state = (
        "empty"
        if not quotes
        else "complete"
        if len(quotes) == len(trace)
        else "partial"
    )
    result = dict(
        schema_version=1,
        kind="exact_source_baseline",
        role="evaluation_only",
        scope="synthetic_fixture_only_not_admitted_real_evidence",
        request_sha256=fingerprint(req),
        question_key=req["question_key"],
        hypothesis_key=req["hypothesis_key"],
        source_scope_sha256=fingerprint(req["source_scope"]),
        policy=encode(p),
        policy_sha256=fingerprint(p),
        tokenizer=TOKENIZER,
        excerpts=quotes,
        selection_trace=trace,
        extraction_state=state,
        extraction_incomplete=len(quotes) != len(trace),
        offered_statement_count=len(trace),
        selected_statement_count=len(quotes),
        coverage=encode(source["coverage"]),
        scientific_answer_status="not_attempted",
        generated_interpretations=[],
        features={},
        clinical_probability=None,
        model_calls=0,
        measured_model_usage=dict(input_tokens=0, output_tokens=0, cost_usd=0.0),
        compute_accounting="Pure local computation; CPU time and energy not measured",
    )
    need(
        len(canonical(result)) <= p["max_result_bytes"],
        "Complete baseline result exceeds byte cap; no truncation",
    )
    return freeze(result)


def verify_baseline(request, policy, result):
    """Recompute trusted policy and source bindings; never invoke a model."""
    need(
        canonical(result) == canonical(run_baseline(request, policy)),
        "Baseline result differs from deterministic source-inclusive recomputation",
    )
    return True


def reviewer_view(result, neutral_label):
    """Authenticate before making a neutral projection; no masking key is emitted."""
    need(
        isinstance(neutral_label, str)
        and re.fullmatch(r"Candidate [A-Z]", neutral_label),
        "Expected neutral Candidate label",
    )
    doc = encode(result)
    need(
        isinstance(doc, dict)
        and isinstance(doc.get("request_sha256"), str)
        and isinstance(doc.get("policy"), dict),
        "Missing baseline bindings",
    )
    matches = [
        load_synthetic_request(name)
        for name in FIXTURES
        if fingerprint(load_synthetic_request(name)) == doc["request_sha256"]
    ]
    need(len(matches) == 1, "Unknown synthetic baseline request")
    verify_baseline(matches[0], doc["policy"], doc)
    return freeze(
        dict(
            schema_version=1,
            kind="literal_source_excerpt_view",
            role="evaluation_only",
            label=neutral_label,
            excerpts=doc["excerpts"],
            coverage=doc["coverage"],
            offered_statement_count=doc["offered_statement_count"],
            selected_statement_count=doc["selected_statement_count"],
            extraction_incomplete=doc["extraction_incomplete"],
            scientific_answer_status="not_attempted",
            generated_interpretations=[],
            features={},
            clinical_probability=None,
        )
    )
