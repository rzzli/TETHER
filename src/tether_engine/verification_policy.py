"""Caller-controlled verification requirements, separate from producer declarations."""

import re

from .serde import ContractError


def normalize_anchor(value: str | None) -> str | None:
    """Normalize a caller's digest; canonical stored digest fields remain strict."""
    if value is None:
        return None
    if type(value) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ContractError(
            "Receipt or manifest anchor must contain exactly 64 hexadecimal characters"
        )
    return value.lower()


def require_semantic_policy(policy: str, allow_legacy: bool) -> None:
    """Only an explicit caller opt-in can lower legacy verification assurance."""
    if type(allow_legacy) is not bool:
        raise ContractError("allow_legacy must be a boolean")
    if policy != "current" and not allow_legacy:
        raise ContractError(
            "Semantic verification requires a current policy; "
            "use allow_legacy=True (--allow-legacy) for explicit legacy byte-only verification"
        )
