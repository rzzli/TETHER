"""Evaluator-only pilot metrics. Agents/workflows never import or read labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean

from .scorer import Prediction
from .serde import ContractError


@dataclass(frozen=True)
class Outcome:
    case_id: str
    origin: date
    endpoint: str
    horizon_months: int
    status: str
    value: int | None
    event_at: date | None
    observed_until: date
    label_available_at: date
    cluster_id: str


@dataclass(frozen=True)
class Outcomes:
    schema_version: int
    label_freeze: date
    outcomes: tuple[Outcome, ...]


def add_months(origin: date, months: int) -> date:
    import calendar
    month_number = origin.year * 12 + origin.month - 1 + months
    year, month = divmod(month_number, 12)
    return date(year, month + 1, min(origin.day, calendar.monthrange(year, month + 1)[1]))


def evaluate(predictions: tuple[Prediction, ...], labels: Outcomes,
             allow_synthetic: bool = False) -> dict:
    if labels.schema_version != 1:
        raise ContractError("Unsupported outcome schema")
    if len({row.case_id for row in predictions}) != len(predictions):
        raise ContractError("Duplicate prediction cases")
    if len({row.case_id for row in labels.outcomes}) != len(labels.outcomes):
        raise ContractError("Duplicate outcome cases")
    predicted = {row.case_id: row for row in predictions}
    if set(predicted) != {row.case_id for row in labels.outcomes}:
        raise ContractError("Predictions and labels must cover the same registered cohort")
    scored, excluded = [], []
    for outcome in labels.outcomes:
        prediction = predicted[outcome.case_id]
        if (prediction.origin != outcome.origin or prediction.endpoint != outcome.endpoint or
                prediction.horizon_months != outcome.horizon_months):
            raise ContractError("Prediction/label endpoint, horizon or origin mismatch")
        if prediction.synthetic and not allow_synthetic:
            raise ContractError("Synthetic predictions require explicit evaluation opt-in")
        if outcome.horizon_months <= 0 or not outcome.cluster_id.strip():
            raise ContractError("Outcome horizon and dependence cluster are required")
        horizon = add_months(outcome.origin, outcome.horizon_months)
        if outcome.label_available_at > labels.label_freeze or outcome.observed_until > labels.label_freeze:
            raise ContractError("Outcome information is later than the label freeze")
        if outcome.observed_until < outcome.origin or outcome.label_available_at < outcome.origin:
            raise ContractError("Outcome follow-up/availability cannot precede the origin")
        if outcome.event_at is not None and (outcome.event_at <= outcome.origin or
                                             outcome.event_at > outcome.observed_until or
                                             outcome.event_at > outcome.label_available_at):
            raise ContractError("Event date contradicts origin, observation or availability dates")
        if outcome.status not in ("resolved", "censored", "unresolved"):
            raise ContractError("Unknown outcome status")
        if outcome.status != "resolved":
            if outcome.value is not None:
                raise ContractError("Censored/unresolved outcome cannot be a negative label")
            excluded.append({"case_id": outcome.case_id, "reason": outcome.status})
            continue
        if outcome.value not in (0, 1):
            raise ContractError("Resolved outcome must be binary")
        if outcome.value == 0 and outcome.observed_until < horizon:
            raise ContractError("A negative requires complete horizon follow-up")
        if outcome.value == 0 and outcome.label_available_at < horizon:
            raise ContractError("A negative label was not available before horizon completion")
        if outcome.value == 1 and (outcome.event_at is None or
                                   not outcome.origin < outcome.event_at <= horizon or
                                   outcome.event_at > outcome.observed_until or
                                   outcome.event_at > outcome.label_available_at):
            raise ContractError("Positive progression needs an eligible, available event date")
        if outcome.value == 0 and outcome.event_at is not None and outcome.event_at <= horizon:
            raise ContractError("Negative contradicts a progression event within the horizon")
        if prediction.probability is None:
            excluded.append({"case_id": outcome.case_id, "reason": "prediction_abstained_or_failed"})
            continue
        if prediction.status != "scored" or not 0 <= prediction.probability <= 1:
            raise ContractError("Invalid scored probability")
        scored.append((outcome.value, prediction.probability, outcome.cluster_id))
    positives = [p for y, p, _ in scored if y == 1]
    negatives = [p for y, p, _ in scored if y == 0]
    # Pilot-scale implementation with exact tie handling; no independence assumption/inference.
    auc = (sum((a > b) + 0.5 * (a == b) for a in positives for b in negatives)
           / (len(positives) * len(negatives))) if positives and negatives else None
    average_precision = None
    if positives:
        thresholds = sorted({p for _, p, _ in scored}, reverse=True)
        tp, fp, old_tp, average_precision = 0, 0, 0, 0.0
        for threshold in thresholds:
            group = [y for y, p, _ in scored if p == threshold]
            tp += sum(group)
            fp += len(group) - sum(group)
            average_precision += ((tp - old_tp) / len(positives)) * tp / (tp + fp)
            old_tp = tp
    return {"schema_version": 1, "cohort_size": len(labels.outcomes), "scored_cases": len(scored),
            "coverage": len(scored) / len(labels.outcomes) if labels.outcomes else 0,
            "positive_cases": len(positives), "negative_cases": len(negatives),
            "clusters": len({cluster for _, _, cluster in scored}),
            "brier": mean((p - y) ** 2 for y, p, _ in scored) if scored else None,
            "auroc": auc, "average_precision": average_precision, "excluded": excluded,
            "inference": "descriptive_only; clustered uncertainty and preregistered tests not implemented"}

