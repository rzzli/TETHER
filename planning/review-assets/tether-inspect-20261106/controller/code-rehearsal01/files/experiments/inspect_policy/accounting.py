"""Fail-closed extension reservations, separate from Inspect's telemetry hooks."""
from __future__ import annotations

import math
import time

from .records import digest, freeze, thaw


class BudgetDenied(RuntimeError):
    pass


def usage(value):
    if not isinstance(value, dict) or set(value) != {"input_tokens", "output_tokens", "cost_usd"}:
        raise ValueError("Exact usage fields required")
    if any(type(value[name]) is not int or value[name] < 0 for name in ("input_tokens", "output_tokens")):
        raise ValueError("Token counts must be nonnegative integers")
    if type(value["cost_usd"]) not in (int, float) or not math.isfinite(value["cost_usd"]) or value["cost_usd"] < 0:
        raise ValueError("Cost must be finite and nonnegative")
    return dict(value)


def zero():
    return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


def add(left, right):
    return {key: left[key] + right[key] for key in left}


class Accounting:
    """One sample's operation authority, created before any scripted generation.

    The local provider's reported token counts are controlled fixture values;
    they are not measured language-model inference or tokenization performance.
    Unknown output is conservatively charged the prior quote, never zeroed.
    """

    def __init__(self, record, budget, *, clock=time.monotonic):
        self.record = record
        self.budget = freeze(budget)
        if set(budget) != {"max_calls", "max_input_tokens", "max_output_tokens", "max_cost_usd", "max_seconds"}:
            raise ValueError("Budget fields differ")
        for name in ("max_calls", "max_input_tokens", "max_output_tokens"):
            if type(budget[name]) is not int or budget[name] < 0:
                raise ValueError("Budget count invalid")
        for name in ("max_cost_usd", "max_seconds"):
            if type(budget[name]) not in (int, float) or not math.isfinite(budget[name]) or budget[name] < 0:
                raise ValueError("Budget scalar invalid")
        if budget["max_seconds"] <= 0:
            raise ValueError("Positive time limit required")
        self.clock = clock
        self.started = clock()
        self.calls = 0
        self.pending = None
        self.measured = zero()
        self.estimated = zero()
        self.stopped = False
        self.record.append("budget", {"limits": budget})

    @property
    def total(self):
        return add(self.measured, self.estimated)

    def reserve(self, request, quote):
        quote = usage(quote)
        if self.pending is not None:
            raise RuntimeError("A prior potentially dispatched call is unresolved")
        would_use = add(self.total, quote)
        denied = (self.stopped or self.calls >= self.budget["max_calls"] or
                  self.clock() - self.started >= self.budget["max_seconds"] or
                  any(would_use[key] > self.budget["max_" + key] for key in would_use))
        if denied:
            self.stopped = True
            self.record.append("reservation_denied", {"request_sha256": digest(request), "quote": quote})
            raise BudgetDenied("Sample budget does not permit a new call")
        pending = freeze({"attempt": self.calls, "request": request,
                          "request_sha256": digest(request), "quote": quote})
        # A write failure exits before a provider can observe this reservation.
        self.record.append("attempt_reserved", pending)
        self.pending = pending
        self.calls += 1
        return pending

    def settle(self, *, measured=None, outcome, response_sha256=None):
        if self.pending is None:
            raise RuntimeError("No reserved attempt to settle")
        actual = usage(measured) if measured is not None else thaw(self.pending["quote"])
        quote = self.pending["quote"]
        breach = measured is not None and any(actual[key] > quote[key] for key in actual)
        kind = "measured" if measured is not None else "estimated"
        details = {"attempt": self.pending["attempt"], "request_sha256": self.pending["request_sha256"],
                   "kind": kind, "usage": actual, "outcome": outcome,
                   "quote_breach": breach, "response_sha256": response_sha256}
        self.record.append("attempt_accounted", details)
        if measured is not None:
            self.measured = add(self.measured, actual)
        else:
            self.estimated = add(self.estimated, actual)
        self.pending = None
        if breach or outcome != "completed":
            self.stopped = True
        return freeze(details)

    def summary(self):
        outstanding = thaw(self.pending["quote"]) if self.pending else zero()
        return freeze({"calls": self.calls, "measured_usage": self.measured,
                       "estimated_usage": self.estimated, "usage": self.total,
                       "outstanding_reservation": outstanding,
                       "conservative_upper_usage": add(self.total, outstanding),
                       "unresolved_calls": int(self.pending is not None), "stopped": self.stopped,
                       "wall_seconds": self.clock() - self.started,
                       "usage_basis": "reported_scripted_provider_counts_not_language_model_inference"})
