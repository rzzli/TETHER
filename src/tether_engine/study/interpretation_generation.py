"""Pure v3 GBNF preparation; neither native qualification nor dispatch authority.

The v2 renderer/validator remain unchanged. New wire fingerprints are explicit;
complete semantic validation is reused without rewriting authored responses.
"""

from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from . import interpretation_interface as legacy
from .diagnostic_codec import need, pointer
from .fixed_evidence import load_plan
from .interpretation_grammar import build_grammar

INTERFACE = "source-quote-interpretation-v3-gbnf"
GENERATION_GUIDE = (
    "Generation format: compact JSON, with object keys in this exact order: "
    "abstention_reason, answer_status, claims, unresolved; each claim uses kind, "
    "limitations, quote_refs, text. Encode every less-than character with a JSON "
    "Unicode escape. Preserve decoded text exactly, including whitespace and "
    "combining marks. No normalization, shortening or reordering of references. "
    "The GBNF defines a generation serialization domain; complete semantic and "
    "source validation remain required after generation. "
)


def _prepare(request, arm, index, feedback):
    # Preserve all existing source/history/stage and complete-v2 byte preflights.
    prior = legacy.prepare_payload(request, arm, index, feedback)
    data = encode(prior["semantic_data"])
    original = data["original_request"]
    texts = {
        row["quote_id"]: pointer(original, row["request_pointer"])
        for row in data["quote_catalog"]
    }
    grammar = build_grammar(texts, claim_limit=prior["claim_limit"])
    grammar_fingerprint = fingerprint(grammar)
    acceptance_schema = prior["payload"]["json_schema"]
    acceptance_fingerprint = fingerprint(acceptance_schema)
    data["interface"] = INTERFACE
    data["generation_contract"] = dict(
        generator=grammar["generator"],
        grammar_sha256=grammar["grammar_sha256"],
        generation_contract_sha256=grammar_fingerprint,
        serialization_domain=grammar["serialization_domain"],
        acceptance_schema_sha256=acceptance_fingerprint,
        post_validation_only=grammar["post_validation_only"],
        native_conformance="unverified",
    )
    guide = (
        legacy.GUIDE
        + GENERATION_GUIDE
        + f"Active maximum claims: {prior['claim_limit']}. "
        + load_plan()["role_guides"][data["stage"]]
    )
    prompt = (
        "<|im_start|>system\n"
        + guide
        + legacy.MARKER
        + canonical(data).decode("utf-8").replace("<|", "<\\u007c")
        + legacy.SUFFIX
    )
    payload = encode(prior["payload"])
    del payload["json_schema"]
    payload.update(prompt=prompt, grammar=grammar["grammar"])
    need(
        len(prompt.encode("utf-8")) <= 32768 and len(canonical(payload)) <= 65536,
        "Complete v3 interpretation payload exceeds byte caps; no clipping",
    )
    prepared = freeze(
        dict(
            schema_version=3,
            interface=INTERFACE,
            semantic_data=data,
            payload=payload,
            request_sha256=prior["request_sha256"],
            payload_sha256=fingerprint(payload),
            quote_catalog_sha256=prior["quote_catalog_sha256"],
            claim_limit=prior["claim_limit"],
            generation_grammar=grammar,
            generation_contract_sha256=grammar_fingerprint,
            acceptance_schema=acceptance_schema,
            acceptance_schema_sha256=acceptance_fingerprint,
            native_conformance="unverified",
            execution_authorized=False,
        )
    )
    return prepared, prior


def prepare_payload(request, arm, index, feedback):
    """Prepare complete original inputs and new grammar; authorize no execution."""
    try:
        return _prepare(request, arm, index, feedback)[0]
    except (TypeError, KeyError, ValueError, IndexError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Malformed v3 interpretation preparation") from error


def _reconstruct(payload):
    payload = encode(payload)
    need(
        isinstance(payload, dict) and isinstance(payload.get("prompt"), str),
        "Missing v3 interpretation prompt",
    )
    need(len(canonical(payload)) <= 65536, "V3 interpretation HTTP payload exceeds cap")
    prompt = payload["prompt"]
    need(
        prompt.startswith("<|im_start|>system\n")
        and legacy.MARKER in prompt
        and prompt.endswith(legacy.SUFFIX),
        "Invalid v3 interpretation framing",
    )
    body = prompt.split(legacy.MARKER, 1)[1][: -len(legacy.SUFFIX)]
    need("<|" not in body, "Unescaped runtime control delimiter")
    data = parse_json(body)
    need(
        isinstance(data, dict) and data.get("interface") == INTERFACE,
        "Wrong v3 interpretation interface",
    )
    expected, prior = _prepare(
        data["original_request"],
        data["arm"],
        data["stage_index"],
        data["prior_source_id_feedback"],
    )
    need(
        canonical(expected["payload"]) == canonical(payload),
        "V3 interpretation payload differs from frozen renderer",
    )
    return expected, prior


def request_from_payload(payload):
    """Recompute exact new grammar/options and preserve complete request identity."""
    try:
        prepared, _ = _reconstruct(payload)
        return prepared["semantic_data"]["original_request"]
    except (TypeError, KeyError, ValueError, IndexError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Malformed v3 interpretation payload") from error


def validate_output(request, payload, document):
    """Apply complete unchanged semantic validation with new payload binding."""
    try:
        prepared, prior = _reconstruct(payload)
        need(
            fingerprint(request) == prepared["request_sha256"],
            "V3 interpretation response request differs",
        )
        result = encode(legacy.validate_output(request, prior["payload"], document))
        # Only the artifact envelope changes. The response and exact quotes are
        # the unchanged trusted validator's output, never a repaired answer.
        result.update(
            schema_version=3,
            kind="source_quote_interpretation_v3",
            interface=INTERFACE,
            payload_sha256=prepared["payload_sha256"],
            generation_contract_sha256=prepared["generation_contract_sha256"],
            acceptance_schema_sha256=prepared["acceptance_schema_sha256"],
            native_conformance="unverified",
        )
        return freeze(result)
    except (TypeError, KeyError, ValueError, IndexError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Malformed v3 interpretation response") from error
