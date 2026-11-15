"""Caller-controlled verification requirements, separate from producer declarations."""
import re

from .serde import ContractError


def normalize_anchor(value: str | None) -> str | None:
    """Normalize a caller's digest; canonical stored digest fields remain strict."""
    if value is None:
        return None
    if type(value) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ContractError("Receipt or manifest anchor must contain exactly 64 hexadecimal characters")
    return value.lower()
