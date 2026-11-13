"""Closed deterministic transformations; submitted code is never executed.

Projection proves equality to declared source information, not source truth or
historical authenticity. Method availability is a recorded local registration
bound, not an independently authenticated public-release date. Callers also
enforce the complete graph's role, availability and receipt policy before
providing parent bytes.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import inspect
import re
import textwrap
from typing import Any

from .contracts import (
    Availability, Category, Derivation, EvidenceStatus, FEATURE_CATEGORIES, Method, Observation,
    Polarity, QuantitativeResult, ScientificContext, SourceNode, validate_observation,
)
from .serde import (
    ContractError, Frozen, MAX_NORMALIZED_JSON_BYTES, _pairs, canonical, decode,
    encode, fingerprint, freeze, parse_json,
)


POLICY = "tether.derivation.v1"
_METHOD = "tether.json_projection"
_VERSION = "1"
_AVAILABLE = datetime(2026, 11, 13, 7, 48, 48, tzinfo=timezone.utc)
_AVAILABILITY_BASIS = "local_source_registration_not_authenticated_public_release"
_SCHEMAS = ("canonical_json.v1", "observation.v2")
_MODES = ("contemporary_method_retrospective", "historical_method_simulation")
_ENVELOPE_FIELDS = frozenset(("source_kind", "computed_at", "input_refs", "derivation"))
_MAX_POINTER_BYTES = 4096
_MAX_POINTER_DEPTH = 128


def _resolve_pointer(value: Any, pointer: str) -> Any:
    """Resolve RFC 6901 tokens without JSONPath, evaluation or mutation."""
    if not isinstance(pointer, str) or len(pointer.encode("utf-8")) > _MAX_POINTER_BYTES:
        raise ContractError("Derivation JSON pointer exceeds its bounded string contract")
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ContractError("Derivation JSON pointer must be empty or start with /")
    tokens = pointer[1:].split("/")
    if len(tokens) > _MAX_POINTER_DEPTH:
        raise ContractError("Derivation JSON pointer is too deep")
    for token in tokens:
        if re.search(r"~(?:[^01]|$)", token):
            raise ContractError("Invalid derivation JSON pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, Mapping):
            if token not in value:
                raise ContractError("Derivation JSON pointer member is missing")
            value = value[token]
        elif isinstance(value, (list, tuple)):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ContractError("Derivation JSON pointer requires a canonical array index")
            # Bound conversion before int() to avoid giant-index conversion work.
            if len(token) > len(str(len(value))) or int(token) >= len(value):
                raise ContractError("Derivation JSON pointer index is out of range")
            value = value[int(token)]
        else:
            raise ContractError("Derivation JSON pointer descends into a scalar")
    return value


def _projection_v1(payload: bytes, pointer: str) -> Any:
    if len(payload) > MAX_NORMALIZED_JSON_BYTES:
        raise ContractError("Derivation JSON input exceeds the 64 MiB limit")
    try:
        parsed = decode(Any, parse_json(payload), "derivation input")
        return _resolve_pointer(parsed, pointer)
    except RecursionError as error:
        raise ContractError("Derivation JSON nesting exceeds supported depth") from error
    except (UnicodeError, ValueError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Derivation JSON cannot be decoded canonically") from error


def information_payload(observation: Observation) -> Mapping:
    """Retain every observation field except its computation/lineage envelope."""
    if not isinstance(observation, Observation):
        raise ContractError("Derivation output must be a typed observation")
    return freeze({key: value for key, value in encode(observation).items()
                   if key not in _ENVELOPE_FIELDS})


@lru_cache(maxsize=1)
def _implementation_sha256() -> str:
    # ASTs bind actual qualified behavior while ignoring comments/line endings.
    # This deliberately excludes unrelated engine files and environment paths.
    functions = (_resolve_pointer, _projection_v1, information_payload, verify_observation,
                 _validate_recipe, validate_descriptor, project, parse_json, _pairs,
                 decode, encode, canonical, fingerprint, freeze, Frozen.__post_init__,
                 Observation.__post_init__, validate_observation, registry_entry)

    def normalize(node):
        if isinstance(node, ast.AST):
            # Empty generic-parameter fields appeared in Python 3.12. Their
            # absence on 3.11 does not change these non-generic functions.
            return {"type": type(node).__name__, "fields": {
                key: normalize(value) for key, value in ast.iter_fields(node)
                if not (key == "type_params" and not value)}}
        if isinstance(node, list):
            return [normalize(value) for value in node]
        if node is Ellipsis:
            return {"constant": "ellipsis"}
        if isinstance(node, bytes):
            return {"constant_bytes": node.hex()}
        return node

    source = [normalize(ast.parse(textwrap.dedent(inspect.getsource(function)))) for function in functions]
    specification = {
        "policy": POLICY, "method": _METHOD, "version": _VERSION,
        "available_at": _AVAILABLE, "availability_basis": _AVAILABILITY_BASIS, "schemas": _SCHEMAS,
        "parameters": ("input", "pointer"), "pointer": "RFC6901", "modes": _MODES,
        "maximum_input_bytes": MAX_NORMALIZED_JSON_BYTES,
        "maximum_pointer_bytes": _MAX_POINTER_BYTES, "maximum_pointer_depth": _MAX_POINTER_DEPTH,
        "observation_fields": [(item.name, str(item.type)) for item in fields(Observation)
                               if item.name not in _ENVELOPE_FIELDS],
        "nested_contracts": {
            kind.__name__: normalize(ast.parse(textwrap.dedent(inspect.getsource(kind))))
            for kind in (Availability, ScientificContext, QuantitativeResult, Method, Derivation)},
        "enums": {kind.__name__: [member.value for member in kind]
                  for kind in (Category, EvidenceStatus, Polarity)},
        "feature_categories": FEATURE_CATEGORIES,
        "excluded_envelope_fields": sorted(_ENVELOPE_FIELDS),
        "comparison": "typed-v2-canonical-information-payload",
        "json": "UTF8-strict-duplicate-key-and-nonfinite-rejection",
    }
    return fingerprint({"implementation_ast": source, "specification": specification})


def registry_entry(method_id: str = _METHOD, method_version: str = _VERSION) -> Mapping:
    """Return the sole built-in method's immutable authoritative descriptor."""
    if (method_id, method_version) != (_METHOD, _VERSION):
        raise ContractError("Unknown or unsupported derivation method/version")
    return freeze({"method_id": _METHOD, "method_version": _VERSION,
                   "implementation_sha256": _implementation_sha256(),
                   "method_available_at": _AVAILABLE, "availability_basis": _AVAILABILITY_BASIS,
                   "output_schemas": _SCHEMAS})


def _validate_recipe(recipe: Derivation) -> None:
    if not isinstance(recipe, Derivation) or type(recipe.schema_version) is not int or recipe.schema_version != 1:
        raise ContractError("Unsupported derivation descriptor schema")
    registered = registry_entry(recipe.method_id, recipe.method_version)
    if recipe.implementation_sha256 != registered["implementation_sha256"]:
        raise ContractError("Derivation implementation fingerprint does not match registry")
    if (not isinstance(recipe.method_available_at, datetime) or recipe.method_available_at.tzinfo is None or
            recipe.method_available_at != registered["method_available_at"]):
        raise ContractError("Derivation method availability does not match registry")
    if recipe.mode not in _MODES or recipe.output_schema not in _SCHEMAS:
        raise ContractError("Unsupported derivation mode or output schema")
    if not isinstance(recipe.parameters, Mapping) or set(recipe.parameters) != {"input", "pointer"}:
        raise ContractError("Projection parameters must contain only input and pointer")
    if (not isinstance(recipe.parameters["input"], str) or
            not isinstance(recipe.parameters["pointer"], str)):
        raise ContractError("Projection input and pointer must be strings")
    if recipe.parameters_sha256 != fingerprint(recipe.parameters):
        raise ContractError("Derivation parameter fingerprint mismatch")
    if not isinstance(recipe.inputs, Mapping) or not recipe.inputs or not isinstance(recipe.assets, Mapping):
        raise ContractError("Derivation requires exact input and asset mappings")
    if set(recipe.inputs) & set(recipe.assets):
        raise ContractError("Derivation inputs and assets must be disjoint")
    for source_id, digest in (*recipe.inputs.items(), *recipe.assets.items()):
        if (not isinstance(source_id, str) or not source_id.strip() or not isinstance(digest, str) or
                re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ContractError("Derivation input identity and SHA-256 are required")
    if recipe.parameters["input"] not in recipe.inputs:
        raise ContractError("Projection source is not a declared information input")


def validate_descriptor(recipe: Derivation, expected_refs: tuple[str, ...],
                        graph_nodes: Mapping[str, SourceNode], cutoff: datetime) -> None:
    """Bind direct dependencies and method mode; caller qualifies all ancestors."""
    _validate_recipe(recipe)
    refs = tuple(expected_refs)
    if len(set(refs)) != len(refs) or set(refs) != set(recipe.inputs) | set(recipe.assets):
        raise ContractError("Derivation inputs/assets differ from declared lineage")
    for source_id, digest in (*recipe.inputs.items(), *recipe.assets.items()):
        node = graph_nodes.get(source_id)
        if node is None or node.source_id != source_id or node.sha256 != digest:
            raise ContractError("Derivation source/hash does not match lineage graph")
    if not isinstance(cutoff, datetime) or cutoff.tzinfo is None:
        raise ContractError("Derivation eligibility requires an aware cutoff")
    if recipe.mode == "historical_method_simulation" and recipe.method_available_at > cutoff:
        raise ContractError("Derivation method was not available by the historical cutoff")


def project(recipe: Derivation, payloads: Mapping[str, bytes]) -> Any:
    """Rehash every declared dependency and return a frozen selected JSON value."""
    _validate_recipe(recipe)
    for source_id, expected in (*recipe.inputs.items(), *recipe.assets.items()):
        payload = payloads.get(source_id)
        if not isinstance(payload, bytes) or hashlib.sha256(payload).hexdigest() != expected:
            raise ContractError(f"Derivation input bytes missing or changed: {source_id}")
    selected = _projection_v1(payloads[recipe.parameters["input"]], recipe.parameters["pointer"])
    try:
        return freeze(selected)
    except RecursionError as error:
        raise ContractError("Derivation result nesting exceeds supported depth") from error


def verify_observation(observation: Observation, recipe: Derivation,
                       payloads: Mapping[str, bytes], *, eligible_refs=None) -> None:
    """Preserve the source's policy restrictions before comparing its information.

    The optional references are an already qualified ancestor closure supplied
    by the graph verifier, not a list whose eligibility this function asserts.
    Nested computed observation recipes are unsupported; derived source nodes
    are independently verified by the graph before projection.
    """
    if recipe.output_schema != "observation.v2":
        raise ContractError("Observation derivation requires observation.v2 output schema")
    if observation.derivation != recipe:
        raise ContractError("Observation derivation descriptor mismatch")
    expected = decode(Observation, encode(project(recipe, payloads)), "derived observation")
    validate_observation(expected)
    if (expected.source_kind == "computed" or expected.derivation is not None or
            expected.computed_at is not None):
        raise ContractError("Projection cannot qualify an embedded computed observation")
    allowed = set(recipe.inputs) | set(recipe.assets) if eligible_refs is None else set(eligible_refs)
    if not set(expected.input_refs).issubset(allowed):
        raise ContractError("Projected observation lineage escapes the qualified source closure")
    if canonical(information_payload(observation)) != canonical(information_payload(expected)):
        raise ContractError("Computed observation differs from registered derivation output")
