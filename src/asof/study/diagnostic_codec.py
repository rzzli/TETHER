"""Versioned pure diagnostic codec, copied from reviewed legacy codecs.

No evidence admission, execution, tools imports or scientific validation. Legacy
implementations remain untouched. Input bindings are structural, not source proofs.
"""

import json
import re
from asof.contracts import Case
from asof.serde import (
    ContractError,
    canonical,
    decode,
    encode,
    fingerprint,
    freeze,
    parse_json,
)
from .diagnostic_resources import load_resource

MAX_BYTES = 64 * 1024 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
TEMPLATES = load_resource("diagnostic-templates-v1.json")
QUESTIONS = TEMPLATES["questions"]
GUIDE = TEMPLATES["current_guide"]
PREFIX = "<|im_start|>system\n" + GUIDE + "<|im_end|>\n<|im_start|>user\n"
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n"
RECORD_ORDER = TEMPLATES["record_order"]
PROPOSITION_KEYS = {
    "subject",
    "predicate",
    "object",
    "negation",
    "modal",
    "population",
    "tissue",
    "intervention",
    "comparator",
    "outcome",
    "timing",
    "orientation",
}


def need(condition, message):
    if not condition:
        raise ContractError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def pointer(document, location):
    need(
        isinstance(location, str) and (location == "" or location.startswith("/")),
        "Expected an RFC6901 JSON pointer",
    )
    for part in location.split("/")[1:]:
        need(re.search(r"~(?![01])", part) is None, "Invalid JSON pointer escape")
        part = part.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(document, list):
                need(
                    bool(re.fullmatch(r"0|[1-9][0-9]*", part)),
                    "Noncanonical array index",
                )
                document = document[int(part)]
            else:
                need(isinstance(document, dict), "Pointer traverses a scalar")
                document = document[part]
        except (KeyError, IndexError) as exc:
            raise ContractError("Unresolvable original source pointer") from exc
    return document


def validate_legacy_claims(request, response):
    need(
        isinstance(response, dict)
        and set(response)
        == {
            "schema_version",
            "kind",
            "request_sha256",
            "hypothesis_key",
            "claims",
            "abstention_reason",
            "features",
            "clinical_probability",
        },
        "Invalid response fields",
    )
    need(
        type(response["schema_version"]) is int
        and response["schema_version"] == 1
        and response["kind"] == "generated_interpretation",
        "Wrong interpretation contract",
    )
    need(
        response["request_sha256"] == fingerprint(request)
        and response["hypothesis_key"] == request["hypothesis_key"],
        "Response request/hypothesis differs",
    )
    need(
        response["features"] == {} and response["clinical_probability"] is None,
        "Interpretation cannot supply scorer features or clinical probability",
    )
    need(
        len(canonical(response)) <= MAX_RESPONSE_BYTES,
        "Interpretation response exceeds bound",
    )
    claims = response["claims"]
    need(
        isinstance(claims, list) and len(claims) <= request["bounds"]["max_claims"],
        "Claim bound exceeded",
    )
    need(
        response["abstention_reason"] is None
        or nonempty(response["abstention_reason"]),
        "Invalid abstention",
    )
    need(
        bool(claims) or nonempty(response["abstention_reason"]),
        "Empty output needs explicit abstention",
    )
    evidence = {r["observation_id"]: r for r in request["evidence"]}
    ids = set()
    for claim in claims:
        need(
            isinstance(claim, dict)
            and set(claim)
            == {
                "claim_id",
                "kind",
                "text",
                "proposition",
                "premise_ids",
                "quotes",
                "limitations",
                "applicability",
            },
            "Invalid interpretation claim fields",
        )
        need(
            nonempty(claim["claim_id"]) and claim["claim_id"] not in ids,
            "Duplicate/empty claim ID",
        )
        ids.add(claim["claim_id"])
        need(
            claim["kind"]
            in {"source_report", "scientific_inference", "caution", "abstention"},
            "Invalid claim kind",
        )
        need(
            nonempty(claim["text"])
            and len(claim["text"].encode("utf-8"))
            <= request["bounds"]["max_text_bytes"],
            "Claim text bound exceeded",
        )
        prop = claim["proposition"]
        need(
            isinstance(prop, dict) and set(prop) == PROPOSITION_KEYS,
            "Incomplete contextual proposition",
        )
        need(
            all(nonempty(prop[k]) for k in ("subject", "predicate", "object"))
            and type(prop["negation"]) is bool
            and prop["modal"] in {"asserted", "possible", "conditional", "proposal"},
            "Invalid proposition core",
        )
        need(
            all(
                prop[k] is None or nonempty(prop[k])
                for k in (
                    "population",
                    "tissue",
                    "intervention",
                    "comparator",
                    "outcome",
                    "timing",
                )
            ),
            "Invalid proposition context",
        )
        need(
            prop["orientation"] is None
            or isinstance(prop["orientation"], dict)
            and set(prop["orientation"]) == {"exposure", "outcome"}
            and all(nonempty(v) for v in prop["orientation"].values()),
            "Invalid numerical orientation",
        )
        need(
            claim["applicability"]
            in {"claimed", "uncertain", "context_mismatch", "not_assessed"},
            "Invalid applicability",
        )
        limits = claim["limitations"]
        need(
            isinstance(limits, list)
            and all(nonempty(v) for v in limits)
            and (bool(limits) or claim["kind"] == "source_report"),
            "Inference/caution/abstention needs limitations",
        )
        premises = claim["premise_ids"]
        need(
            isinstance(premises, list)
            and all(nonempty(v) for v in premises)
            and len(set(premises)) == len(premises)
            and not set(premises) - evidence.keys(),
            "Foreign/duplicate premises",
        )
        quotes = claim["quotes"]
        need(
            isinstance(quotes, list)
            and len(quotes) <= request["bounds"]["max_quotes_per_claim"],
            "Invalid quote bound",
        )
        quoted = set()
        for quote in quotes:
            need(
                isinstance(quote, dict)
                and set(quote) == {"observation_id", "pointer", "span", "text"},
                "Invalid quote",
            )
            identity = quote["observation_id"]
            need(identity in premises, "Quote outside declared premises")
            row = evidence[identity]
            value = pointer(encode(row["scientific_record"]), quote["pointer"])
            need(
                isinstance(value, str), "Quote pointer must locate original string data"
            )
            span = quote["span"]
            raw = value.encode("utf-8")
            need(
                isinstance(span, dict)
                and set(span) == {"start", "end"}
                and type(span["start"]) is int
                and type(span["end"]) is int
                and 0 <= span["start"] < span["end"] <= len(raw),
                "Invalid UTF-8 quote span",
            )
            try:
                literal = raw[span["start"] : span["end"]].decode("utf-8")
            except UnicodeError as error:
                raise ContractError("Quote splits UTF-8 character") from error
            need(literal == quote["text"], "Quote differs from admitted source string")
            quoted.add(identity)
        need(quoted == set(premises), "Every premise needs an exact quote")
        need(
            bool(premises) or claim["kind"] == "abstention",
            "Uncited scientific interpretation",
        )
        if claim["kind"] == "source_report":
            need(
                len(quotes) == 1 and claim["text"] == quotes[0]["text"],
                "Source report must remain verbatim",
            )
    return response


def question_template(family):
    need(
        isinstance(family, str) and family in QUESTIONS,
        "Unknown question family/version",
    )
    return freeze(QUESTIONS[family])


def _scope(source):
    need(
        isinstance(source, dict)
        and nonempty(source.get("snapshot_id"))
        and isinstance(source.get("evidence"), list),
        "Missing source snapshot/evidence",
    )
    need(
        all(
            isinstance(row, dict)
            and nonempty(row.get("observation_id"))
            and isinstance(row.get("scientific_record"), dict)
            for row in source["evidence"]
        ),
        "Incomplete source scope record",
    )
    return dict(
        snapshot_id=source["snapshot_id"],
        observations=[
            dict(
                observation_id=row["observation_id"],
                scientific_record_sha256=fingerprint(row["scientific_record"]),
            )
            for row in source["evidence"]
        ],
    )


def validate_request(request):
    """Structure/binding check, NOT evidence admission or temporal verification."""
    request = encode(request)
    need(
        isinstance(request, dict)
        and set(request)
        == {
            "schema_version",
            "role",
            "question",
            "question_key",
            "hypothesis_key",
            "source_scope",
            "source_request",
        },
        "Invalid question request fields",
    )
    need(
        type(request["schema_version"]) is int
        and request["schema_version"] == 2
        and request["role"] == "agent_evidence",
        "Wrong question request version/role",
    )
    question = request["question"]
    need(
        isinstance(question, dict) and isinstance(question.get("question_id"), str),
        "Missing question identity",
    )
    expected = question_template(question["question_id"])
    need(
        fingerprint(question) == fingerprint(expected)
        and request["question_key"] == fingerprint(expected),
        "Question differs from reviewed template",
    )
    source = request["source_request"]
    need(
        isinstance(source, dict)
        and set(source)
        == {
            "schema_version",
            "role",
            "case",
            "hypothesis_key",
            "snapshot_id",
            "evidence",
            "coverage",
            "bounds",
            "instructions",
        },
        "Invalid retained source request",
    )
    need(
        type(source["schema_version"]) is int
        and source["schema_version"] == 1
        and source["role"] == "agent_evidence"
        and nonempty(source["snapshot_id"])
        and nonempty(source["instructions"]),
        "Invalid retained source context",
    )
    case = decode(Case, source["case"])
    case.validate()
    need(
        case.task == "T6"
        and request["hypothesis_key"]
        == source["hypothesis_key"]
        == case.hypothesis.key,
        "Question hypothesis/task differs",
    )
    rows = source["evidence"]
    need(
        isinstance(rows, list) and len(rows) <= 1024, "Invalid question evidence bound"
    )
    identities = set()
    for row in rows:
        need(
            isinstance(row, dict)
            and set(row)
            == {
                "observation_id",
                "admitted_sha256",
                "source_ref",
                "statement",
                "scientific_record",
            }
            and nonempty(row["observation_id"])
            and row["observation_id"] not in identities,
            "Invalid/duplicate question source",
        )
        identities.add(row["observation_id"])
        science = row["scientific_record"]
        need(
            isinstance(science, dict)
            and science.get("observation_id") == row["observation_id"]
            and science.get("statement") == row["statement"]
            and isinstance(row["statement"], str)
            and science.get("features") == {}
            and science.get("category") != "clinical",
            "Invalid visible scientific record",
        )
    coverage = source["coverage"]
    need(
        isinstance(coverage, dict)
        and type(coverage.get("observations_visible")) is int
        and coverage["observations_visible"] == len(rows)
        and coverage.get("absence_claim") is False,
        "Coverage differs from selected sources",
    )
    missing = coverage.get("missing_input_count")
    need(
        "missing_input_count" in coverage
        and (missing is None or type(missing) is int and missing >= 0),
        "Invalid missing-input declaration",
    )
    need(
        coverage.get("missing_count_basis")
        == ("snapshot_declaration" if missing is not None else "not_measured"),
        "Missing-input basis differs",
    )
    if "observations_available" in coverage:
        need(
            type(coverage["observations_available"]) is int
            and coverage["observations_available"] >= len(rows),
            "Available source count differs",
        )
    bounds = source["bounds"]
    need(
        isinstance(bounds, dict)
        and set(bounds) == {"max_claims", "max_text_bytes", "max_quotes_per_claim"}
        and type(bounds["max_claims"]) is int
        and 1 <= bounds["max_claims"] <= 64
        and type(bounds["max_text_bytes"]) is int
        and bounds["max_text_bytes"] == 8192
        and type(bounds["max_quotes_per_claim"]) is int
        and bounds["max_quotes_per_claim"] == 8,
        "Question bounds differ from source contract",
    )
    need(
        fingerprint(request["source_scope"]) == fingerprint(_scope(source)),
        "Selected source scope differs",
    )
    need(len(canonical(request)) <= MAX_BYTES, "Question request exceeds 64 MiB")
    return freeze(request)


def bind_question(source_request, family):
    """Bind an existing source request; this function does not admit evidence."""
    source = encode(source_request)
    question = question_template(family)
    need(
        isinstance(source, dict) and isinstance(source.get("evidence"), list),
        "Missing source evidence",
    )
    request = dict(
        schema_version=2,
        role="agent_evidence",
        question=encode(question),
        question_key=fingerprint(question),
        hypothesis_key=source.get("hypothesis_key"),
        source_scope=_scope(source),
        source_request=source,
    )
    return validate_request(request)


def scientific_view(request):
    """Reorder original fields without selecting, interpreting or losing data."""
    original = encode(validate_request(request))
    source = original.pop("source_request")
    records = []
    for row in source.pop("evidence"):
        science = row.pop("scientific_record")
        present = "source_metrics" in science
        metrics = science.pop("source_metrics", None)
        is_object = isinstance(metrics, dict)
        passages_present = is_object and "textMiningSentences" in metrics
        passages = metrics.pop("textMiningSentences") if passages_present else None
        records.append(
            dict(
                reported_passages=passages,
                scientific_context=science,
                provider_metadata=metrics,
                annotation=row,
                source_metrics_present=present,
                source_metrics_is_object=is_object,
                passages_present=passages_present,
            )
        )
    view = dict(
        format="question-scientific-first-v1",
        request_sha256=fingerprint(request),
        request_context=original,
        source_request_context=source,
        records=records,
    )
    need(
        fingerprint(expand_view(view)) == fingerprint(request),
        "Scientific view lost original fields",
    )
    need(
        len(canonical(view)) <= MAX_BYTES,
        "Scientific view exceeds 64 MiB; no truncation",
    )
    return freeze(view)


def expand_view(view):
    """Reconstruct exact original request; local hashes do not prove admission."""
    view = encode(view)
    need(
        isinstance(view, dict)
        and set(view)
        == {
            "format",
            "request_sha256",
            "request_context",
            "source_request_context",
            "records",
        }
        and view["format"] == "question-scientific-first-v1",
        "Invalid scientific view",
    )
    context, source = view["request_context"], view["source_request_context"]
    need(
        isinstance(context, dict)
        and "source_request" not in context
        and isinstance(source, dict)
        and "evidence" not in source
        and isinstance(view["records"], list),
        "Scientific view context collision",
    )
    rows = []
    keys = {
        "reported_passages",
        "scientific_context",
        "provider_metadata",
        "annotation",
        "source_metrics_present",
        "source_metrics_is_object",
        "passages_present",
    }
    for item in view["records"]:
        need(
            isinstance(item, dict)
            and set(item) == keys
            and all(
                type(item[k]) is bool
                for k in (
                    "source_metrics_present",
                    "source_metrics_is_object",
                    "passages_present",
                )
            ),
            "Invalid scientific view record/flags",
        )
        science, row, metrics = (
            item["scientific_context"],
            item["annotation"],
            item["provider_metadata"],
        )
        need(
            isinstance(science, dict)
            and "source_metrics" not in science
            and isinstance(row, dict)
            and "scientific_record" not in row,
            "Scientific view field collision",
        )
        if not item["source_metrics_present"]:
            need(
                not item["source_metrics_is_object"]
                and not item["passages_present"]
                and metrics is None
                and item["reported_passages"] is None,
                "Absent source metrics gained fields",
            )
        else:
            need(
                item["source_metrics_is_object"] is isinstance(metrics, dict),
                "Metric object flag differs",
            )
            if item["source_metrics_is_object"]:
                need("textMiningSentences" not in metrics, "Passage field duplicated")
                if item["passages_present"]:
                    metrics["textMiningSentences"] = item["reported_passages"]
                else:
                    need(
                        item["reported_passages"] is None,
                        "Absent passages gained a value",
                    )
            else:
                need(
                    not item["passages_present"] and item["reported_passages"] is None,
                    "Opaque metrics cannot supply fabricated passages",
                )
            science["source_metrics"] = metrics
        row["scientific_record"] = science
        rows.append(row)
    source["evidence"] = rows
    context["source_request"] = source
    result = validate_request(context)
    need(
        fingerprint(result) == view["request_sha256"],
        "Scientific view request fingerprint differs",
    )
    return result


def validate_response(request, response):
    """Check v2 state/identity and exact legacy claims, never scientific entailment."""
    request = encode(validate_request(request))
    response = encode(response)
    need(
        isinstance(response, dict)
        and set(response)
        == {
            "schema_version",
            "kind",
            "request_sha256",
            "hypothesis_key",
            "question_key",
            "answer_status",
            "claims",
            "abstention_reason",
            "features",
            "clinical_probability",
        },
        "Invalid question response fields",
    )
    need(
        type(response["schema_version"]) is int
        and response["schema_version"] == 2
        and response["kind"] == "question_interpretation",
        "Wrong question response version/kind",
    )
    need(
        response["request_sha256"] == fingerprint(request)
        and response["hypothesis_key"] == request["hypothesis_key"]
        and response["question_key"] == request["question_key"],
        "Question response identity differs",
    )
    need(
        response["features"] == {} and response["clinical_probability"] is None,
        "Question response cannot supply predictive features/probability",
    )
    need(
        len(canonical(response)) <= MAX_RESPONSE_BYTES,
        "Question response exceeds bound",
    )
    claims, reason, state = (
        response["claims"],
        response["abstention_reason"],
        response["answer_status"],
    )
    need(
        isinstance(claims, list)
        and isinstance(state, str)
        and state in {"answered", "partial", "abstained"},
        "Invalid question answer state",
    )
    need(
        reason is None or nonempty(reason) and len(reason.encode("utf-8")) <= 8192,
        "Invalid abstention reason",
    )
    need(
        (state == "answered" and bool(claims) and reason is None)
        or (state == "partial" and bool(claims) and nonempty(reason))
        or (state == "abstained" and not claims and nonempty(reason)),
        "Claims contradict answer state",
    )
    need(
        all(
            isinstance(c, dict)
            and isinstance(c.get("kind"), str)
            and c["kind"] in {"source_report", "scientific_inference", "caution"}
            for c in claims
        ),
        "Abstention is not an endorsed claim kind",
    )
    source = request["source_request"]
    legacy = dict(
        schema_version=1,
        kind="generated_interpretation",
        request_sha256=fingerprint(source),
        hypothesis_key=request["hypothesis_key"],
        claims=claims,
        abstention_reason=reason,
        features={},
        clinical_probability=None,
    )
    try:
        validate_legacy_claims(
            source, legacy
        )  # Transient; never archived as a v1 response.
    except (TypeError, KeyError) as error:
        raise ContractError("Malformed question claim fields") from error
    return freeze(response)


def _ordered_data(value):
    # Canonicalize arbitrary nested object order, not arrays or JSON scalar types.
    return parse_json(canonical(value))


def wire_for(request):
    view = encode(scientific_view(request))
    context = view["request_context"]
    question = context.pop("question")
    wire = dict(
        question=_ordered_data(question),
        records=[
            {k: _ordered_data(row[k]) for k in RECORD_ORDER} for row in view["records"]
        ],
        request_context=_ordered_data(context),
        source_request_context=_ordered_data(view["source_request_context"]),
        format=view["format"],
        request_sha256=view["request_sha256"],
    )
    need(
        fingerprint(expand_wire(wire)) == fingerprint(request),
        "Rendered wire lost source information",
    )
    return freeze(wire)


def expand_wire(wire):
    wire = encode(wire)
    need(
        isinstance(wire, dict)
        and set(wire)
        == {
            "question",
            "records",
            "request_context",
            "source_request_context",
            "format",
            "request_sha256",
        }
        and isinstance(wire["request_context"], dict)
        and "question" not in wire["request_context"],
        "Invalid rendered wire or question collision",
    )
    context = wire["request_context"]
    context["question"] = wire["question"]
    return expand_view(
        dict(
            format=wire["format"],
            request_sha256=wire["request_sha256"],
            request_context=context,
            source_request_context=wire["source_request_context"],
            records=wire["records"],
        )
    )


def render_prompt(request, *, max_prompt_bytes=14200, max_output_tokens=2048):
    need(
        type(max_prompt_bytes) is int
        and max_prompt_bytes > 0
        and type(max_output_tokens) is int
        and 1 <= max_output_tokens <= 2048
        and max_prompt_bytes + max_output_tokens + 32 <= 16384,
        "Invalid prompt/context bounds",
    )
    # Escape control delimiters only inside serialized data. Never replace newline
    # strings globally: that corrupts valid JSON text such as source "system\n".
    body = json.dumps(
        encode(wire_for(request)),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    body = body.replace("<|", "<\\u007c")
    prompt = PREFIX + body + SUFFIX
    need(
        len(prompt.encode("utf-8")) <= max_prompt_bytes,
        "Complete prompt exceeds cap; no truncation",
    )
    need(
        fingerprint(request_from_prompt(prompt)) == fingerprint(request),
        "Final prompt body differs from request",
    )
    return prompt


def request_from_prompt(prompt):
    need(
        isinstance(prompt, str)
        and prompt.startswith(PREFIX)
        and prompt.endswith(SUFFIX)
        and len(prompt.encode("utf-8")) <= MAX_BYTES,
        "Wrong or oversized prompt framing/guide",
    )
    body = prompt[len(PREFIX) : -len(SUFFIX)]
    need("<|" not in body, "Unescaped runtime control delimiter in data")
    return expand_wire(parse_json(body))


def quote_choices(request):
    request = encode(validate_request(request))
    result = {}
    for index, row in enumerate(request["source_request"]["evidence"]):
        science = row["scientific_record"]
        choices = {"/statement": row["statement"]} if nonempty(row["statement"]) else {}
        metrics = science.get("source_metrics")
        sentences = (
            metrics.get("textMiningSentences") if isinstance(metrics, dict) else None
        )
        if isinstance(sentences, list):
            for i, item in enumerate(sentences):
                if isinstance(item, dict) and nonempty(item.get("text")):
                    choices[f"/source_metrics/textMiningSentences/{i}/text"] = item[
                        "text"
                    ]
        result[f"E{index}"] = choices
    return freeze(result)


def output_schema(request):
    request = encode(validate_request(request))
    text = {"type": "string", "maxLength": 1800}
    optional = {"anyOf": [{"type": "string", "maxLength": 512}, {"type": "null"}]}
    prop = {
        k: optional
        for k in (
            "population",
            "tissue",
            "intervention",
            "comparator",
            "outcome",
            "timing",
        )
    }
    prop.update(
        {
            k: {"type": "string", "minLength": 1, "maxLength": 512}
            for k in ("subject", "predicate", "object")
        }
    )
    prop.update(
        negation={"type": "boolean"},
        modal={
            "type": "string",
            "enum": ["asserted", "possible", "conditional", "proposal"],
        },
        orientation={
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {"exposure": text, "outcome": text},
                    "required": ["exposure", "outcome"],
                    "additionalProperties": False,
                },
            ]
        },
    )
    choices = quote_choices(request)
    sources = list(choices) or ["NO_SOURCE"]
    paths = sorted({p for values in choices.values() for p in values}) or ["/statement"]
    quote = {
        "type": "object",
        "properties": {
            "source": {"type": "string", "enum": sources},
            "pointer": {"type": "string", "enum": paths},
        },
        "required": ["source", "pointer"],
        "additionalProperties": False,
    }
    fields = dict(
        claim_id={"type": "string", "minLength": 1, "maxLength": 64},
        kind={
            "type": "string",
            "enum": ["source_report", "scientific_inference", "caution"],
        },
        text=text,
        proposition={
            "type": "object",
            "properties": prop,
            "required": list(prop),
            "additionalProperties": False,
        },
        quote_refs={"type": "array", "items": quote, "maxItems": 2},
        limitations={"type": "array", "items": text, "maxItems": 4},
        applicability={
            "type": "string",
            "enum": ["claimed", "uncertain", "context_mismatch", "not_assessed"],
        },
    )
    fields = dict(
        answer_status={"type": "string", "enum": ["answered", "partial", "abstained"]},
        claims={
            "type": "array",
            "maxItems": min(4, request["source_request"]["bounds"]["max_claims"]),
            "items": {
                "type": "object",
                "properties": fields,
                "required": list(fields),
                "additionalProperties": False,
            },
        },
        abstention_reason=optional,
    )
    return freeze(
        dict(
            type="object",
            properties=fields,
            required=list(fields),
            additionalProperties=False,
        )
    )


def materialize(request, wire):
    """Copy exact original quote values; never repair the model's assertions."""
    request = encode(validate_request(request))
    wire = encode(wire)
    need(
        isinstance(wire, dict)
        and set(wire) == {"answer_status", "claims", "abstention_reason"}
        and isinstance(wire["claims"], list),
        "Invalid native question wire",
    )
    need(
        len(wire["claims"])
        <= min(4, request["source_request"]["bounds"]["max_claims"]),
        "Native claim cap exceeded",
    )
    reason = wire["abstention_reason"]
    need(
        reason is None or isinstance(reason, str) and len(reason) <= 512,
        "Native abstention text exceeds bound",
    )
    choices = quote_choices(request)
    claims = []
    for item in wire["claims"]:
        need(
            isinstance(item, dict)
            and set(item)
            == {
                "claim_id",
                "kind",
                "text",
                "proposition",
                "quote_refs",
                "limitations",
                "applicability",
            },
            "Invalid native claim fields",
        )
        need(
            isinstance(item["kind"], str)
            and item["kind"] in {"source_report", "scientific_inference", "caution"},
            "Invalid native claim kind",
        )
        need(
            nonempty(item["claim_id"])
            and len(item["claim_id"]) <= 64
            and nonempty(item["text"])
            and len(item["text"]) <= 1800,
            "Native claim text exceeds bound",
        )
        limits = item["limitations"]
        need(
            isinstance(limits, list)
            and len(limits) <= 4
            and all(nonempty(v) and len(v) <= 1800 for v in limits)
            and (bool(limits) or item["kind"] == "source_report"),
            "Invalid native limitations",
        )
        prop = item["proposition"]
        need(isinstance(prop, dict), "Invalid native proposition")
        for key in (
            "subject",
            "predicate",
            "object",
            "population",
            "tissue",
            "intervention",
            "comparator",
            "outcome",
            "timing",
        ):
            value = prop.get(key)
            need(
                value is None or isinstance(value, str) and len(value) <= 512,
                "Native proposition text exceeds bound",
            )
        if isinstance(prop.get("orientation"), dict):
            need(
                all(
                    isinstance(v, str) and len(v) <= 1800
                    for v in prop["orientation"].values()
                ),
                "Native orientation text exceeds bound",
            )
        refs = item["quote_refs"]
        need(isinstance(refs, list) and len(refs) <= 2, "Native quote cap exceeded")
        quotes, premises = [], []
        for ref in refs:
            need(
                isinstance(ref, dict)
                and set(ref) == {"source", "pointer"}
                and isinstance(ref["source"], str)
                and isinstance(ref["pointer"], str)
                and ref["source"] in choices
                and ref["pointer"] in choices[ref["source"]],
                "Foreign native source alias/pointer",
            )
            row = request["source_request"]["evidence"][int(ref["source"][1:])]
            identity = row["observation_id"]
            literal = choices[ref["source"]][ref["pointer"]]
            if identity not in premises:
                premises.append(identity)
            quotes.append(
                dict(
                    observation_id=identity,
                    pointer=ref["pointer"],
                    text=literal,
                    span=dict(start=0, end=len(literal.encode("utf-8"))),
                )
            )
        claim = {k: v for k, v in item.items() if k != "quote_refs"}
        claim.update(premise_ids=premises, quotes=quotes)
        claims.append(claim)
    return validate_response(
        request,
        dict(
            schema_version=2,
            kind="question_interpretation",
            request_sha256=fingerprint(request),
            hypothesis_key=request["hypothesis_key"],
            question_key=request["question_key"],
            answer_status=wire["answer_status"],
            claims=claims,
            abstention_reason=reason,
            features={},
            clinical_probability=None,
        ),
    )
