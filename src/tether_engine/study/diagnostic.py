"""Offline diagnostic payloads and strict response checks, never source admission.

The current interface preserves its contextual propositions. The simplified
interface returns a distinct bound flat response and never invents propositions.
Neither mechanical success nor a source quote establishes scientific entailment.
"""

import json

from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json

from . import diagnostic_codec as codec
from .diagnostic_resources import REQUIRED_RESOURCES as REQUIRED_RESOURCES
from .diagnostic_resources import load_resource

MAX_PROMPT_BYTES = 14200
MAX_HTTP_BYTES = 65536
MAX_OUTPUT_TOKENS = 2048
CONTEXT_TOKENS = 16384
INTERFACES = ("current", "simplified")
# v1 remains an authenticated historical R05 reference. v2 documents the active
# Python validator below; neither version changes the generic native grammar.
ACTIVE_SIMPLIFIED_SCHEMA_RESOURCE = "simplified-response-schema-v2.json"
ACTIVE_SIMPLIFIED_SCHEMA = load_resource(ACTIVE_SIMPLIFIED_SCHEMA_RESOURCE)


def _request(request):
    request = codec.validate_request(request)
    codec.need(
        request["source_request"]["bounds"]["max_claims"] <= 3,
        "Diagnostic supports at most three claims; no silent bound change",
    )
    return request


def _prefix(request):
    guide = codec.TEMPLATES["simplified_guide"].format(
        max_claims=request["source_request"]["bounds"]["max_claims"]
    )
    return "<|im_start|>system\n" + guide + "<|im_end|>\n<|im_start|>user\n"


def _interface(interface):
    codec.need(
        isinstance(interface, str) and interface in INTERFACES,
        "Unknown diagnostic interface",
    )


def load_synthetic_request(name):
    """Load an authenticated, explicitly invented fixture; not admitted evidence."""
    codec.need(
        name in ("synthetic-orientation", "synthetic-context"),
        "Unknown synthetic diagnostic case",
    )
    return _request(load_resource(name + "-v1.json"))


def prepare_payload(request, interface="current"):
    """Render the exact R05 v2 payload and enforce full framing/body reservations."""
    _interface(interface)
    request = _request(request)
    if interface == "current":
        prompt = codec.render_prompt(
            request,
            max_prompt_bytes=MAX_PROMPT_BYTES,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        schema = codec.output_schema(request)
    else:
        body = json.dumps(
            encode(codec.wire_for(request)),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).replace("<|", "<\\u007c")
        prompt = _prefix(request) + body + codec.SUFFIX
        schema = {"type": "object"}
    size = len(prompt.encode("utf-8"))
    codec.need(
        size <= MAX_PROMPT_BYTES and size + 32 + MAX_OUTPUT_TOKENS <= CONTEXT_TOKENS,
        "Complete diagnostic prompt exceeds reservation; no truncation",
    )
    payload = dict(
        prompt=prompt,
        n_predict=MAX_OUTPUT_TOKENS,
        temperature=0.0,
        seed=42,
        cache_prompt=False,
        json_schema=encode(schema),
        stop=["<|im_end|>"],
        stream=False,
    )
    codec.need(
        len(canonical(payload)) <= MAX_HTTP_BYTES, "Complete HTTP payload exceeds cap"
    )
    return freeze(payload)


def request_from_payload(payload, interface="current"):
    """Decode and authenticate the full payload, including guide and native options."""
    _interface(interface)
    payload = encode(payload)
    codec.need(
        isinstance(payload, dict) and isinstance(payload.get("prompt"), str),
        "Missing diagnostic prompt",
    )
    codec.need(
        len(canonical(payload)) <= MAX_HTTP_BYTES, "Complete HTTP payload exceeds cap"
    )
    prompt = payload["prompt"]
    if interface == "current":
        request = codec.request_from_prompt(prompt)
    else:
        marker = "<|im_end|>\n<|im_start|>user\n"
        codec.need(
            prompt.startswith("<|im_start|>system\n")
            and marker in prompt
            and prompt.endswith(codec.SUFFIX),
            "Invalid simplified framing",
        )
        body = prompt.split(marker, 1)[1][: -len(codec.SUFFIX)]
        codec.need("<|" not in body, "Unescaped runtime control delimiter in data")
        request = codec.expand_wire(parse_json(body))
    request = _request(request)
    codec.need(
        canonical(payload) == canonical(prepare_payload(request, interface)),
        "Diagnostic payload differs from frozen renderer/options",
    )
    return request


def _text(value, maximum, message):
    codec.need(codec.nonempty(value) and len(value) <= maximum, message)


def _strings(values, maximum_count, message):
    codec.need(isinstance(values, list) and len(values) <= maximum_count, message)
    for value in values:
        _text(value, 1800, message)


def _flat(request, document):
    codec.need(
        isinstance(document, dict)
        and set(document)
        == {"answer_status", "claims", "unresolved", "abstention_reason"},
        "Invalid simplified fields",
    )
    claims = document["claims"]
    codec.need(
        isinstance(claims, list)
        and len(claims) <= request["source_request"]["bounds"]["max_claims"],
        "Simplified claim cap exceeded",
    )
    state, reason = document["answer_status"], document["abstention_reason"]
    codec.need(
        isinstance(state, str) and state in {"answered", "partial", "abstained"},
        "Invalid simplified answer state",
    )
    codec.need(
        reason is None or codec.nonempty(reason) and len(reason) <= 512,
        "Invalid simplified abstention reason",
    )
    codec.need(
        (state == "answered" and bool(claims) and reason is None)
        or (state == "partial" and bool(claims) and codec.nonempty(reason))
        or (state == "abstained" and not claims and codec.nonempty(reason)),
        "Simplified claims contradict answer state",
    )
    _strings(document["unresolved"], 4, "Invalid unresolved scope")
    choices = codec.quote_choices(request)
    seen = set()
    for claim in claims:
        codec.need(
            isinstance(claim, dict)
            and set(claim)
            == {"kind", "text", "source_ids", "quote_pointers", "limitations"},
            "Invalid simplified claim fields",
        )
        kind = claim["kind"]
        codec.need(
            isinstance(kind, str)
            and kind in {"source_report", "scientific_inference", "caution"},
            "Invalid simplified claim kind",
        )
        _text(claim["text"], 1800, "Invalid simplified text")
        codec.need(claim["text"] not in seen, "Duplicate simplified claim")
        seen.add(claim["text"])
        _strings(claim["limitations"], 4, "Invalid simplified limitations")
        codec.need(
            bool(claim["limitations"]) or kind == "source_report",
            "Inference/caution needs limitations",
        )
        sources, pointers = claim["source_ids"], claim["quote_pointers"]
        codec.need(
            isinstance(sources, list)
            and isinstance(pointers, list)
            and 1 <= len(sources) == len(pointers) <= 2,
            "Invalid paired quote bounds",
        )
        pairs = set()
        for source, pointer in zip(sources, pointers):
            codec.need(
                isinstance(source, str)
                and isinstance(pointer, str)
                and len(pointer) <= 512
                and source in choices
                and pointer in choices[source],
                "Foreign source alias/pointer",
            )
            codec.need((source, pointer) not in pairs, "Duplicate quote reference")
            pairs.add((source, pointer))
        if kind == "source_report":
            codec.need(
                len(sources) == 1 and claim["text"] == choices[sources[0]][pointers[0]],
                "Source report must remain verbatim",
            )
    return freeze(
        dict(
            schema_version=1,
            kind="diagnostic_flat_response",
            request_sha256=fingerprint(request),
            hypothesis_key=request["hypothesis_key"],
            question_key=request["question_key"],
            response=document,
            features={},
            clinical_probability=None,
        )
    )


def validate_output(request, interface, document):
    """Validate native JSON without repairs; return a distinct bound frozen response."""
    _interface(interface)
    try:
        request = _request(request)
        if isinstance(document, (str, bytes)):
            codec.need(
                len(document.encode() if isinstance(document, str) else document)
                <= codec.MAX_RESPONSE_BYTES,
                "Diagnostic response exceeds cap",
            )
            document = parse_json(document)
        document = encode(document)
        codec.need(
            len(canonical(document)) <= codec.MAX_RESPONSE_BYTES,
            "Diagnostic response exceeds cap",
        )
        return (
            codec.materialize(request, document)
            if interface == "current"
            else _flat(request, document)
        )
    except (TypeError, KeyError, ValueError, IndexError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Malformed diagnostic request/response") from error
