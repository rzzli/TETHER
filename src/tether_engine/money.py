"""Exact decimal-USD decisions; numeric wire totals round only for display."""

from fractions import Fraction
import math

from .serde import ContractError


def usd(value: int | float) -> Fraction:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ContractError("USD amount must be finite, numeric and nonnegative")
    return Fraction(str(value))


def total_usd(*values: int | float) -> float:
    try:
        return float(sum((usd(value) for value in values), Fraction(0)))
    except OverflowError as error:
        raise ContractError("USD total exceeds numeric representation") from error
