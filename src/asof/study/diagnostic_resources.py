"""Authenticated source-only diagnostic resources; no evaluator answers."""

from importlib.resources import files
import hashlib
from asof.serde import ContractError, freeze, parse_json

RESOURCE_HASHES = freeze(
    {
        "diagnostic-templates-v1.json": "050742fd8621378130fdce0d596df40f0e12a9a86602b9c8e3c95f8ba26f36d7",
        "simplified-response-schema-v1.json": "b91d4f97fae1bcb42007bbad58c30f3b909dec8a4dd56cf7937a0b9b1bb19051",
        "simplified-response-schema-v2.json": "00885ab1f3f67da533192351db3516602a61c8beb72e16e23b298f53d17f4c1c",
        "synthetic-context-v1.json": "22099c48404069444ce482f0f81c37c36814b7fe77cc6f8ca54326761e458221",
        "synthetic-orientation-v1.json": "2a951ee8bc329aec95bf7de9e2cb189b41c2355ae7165d55d9762f75ae811219",
    }
)
REQUIRED_RESOURCES = tuple("resources/" + name for name in RESOURCE_HASHES)


def load_resource(name):
    if not isinstance(name, str) or name not in RESOURCE_HASHES:
        raise ContractError("Unknown diagnostic resource")
    raw = files("asof.study").joinpath("resources").joinpath(name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != RESOURCE_HASHES[name]:
        raise ContractError("Diagnostic resource hash mismatch")
    return freeze(parse_json(raw))
