"""Descriptive evaluator-only metrics; this pure API does not verify producers.

The common binary risk set is selected by origin, horizon, reporting allowance
and a shared freeze, never by which outcomes happened to resolve first. Labels
and predictions remain missing rather than becoming negative outcomes.
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from .scorer import Prediction
from .serde import ContractError, Frozen, encode, fingerprint


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


@dataclass(frozen=True)
class EvaluationPolicy(Frozen):
    schema_version: int
    endpoint: str
    horizon_months: int
    reporting_lag_days: int

    def validate(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ContractError("Unsupported evaluation policy schema")
        _identifier(self.endpoint, "Evaluation endpoint")
        _horizon(self.horizon_months)
        if (type(self.reporting_lag_days) is not int or
                not 0 <= self.reporting_lag_days < date.max.toordinal()):
            raise ContractError("Reporting lag must be a nonnegative, bounded integer number of days")


def _identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{field} must be a nonempty string without surrounding whitespace")


def _date(value: date, field: str) -> None:
    # datetime subclasses date, but accepting one changes calendar comparisons.
    if type(value) is not date:
        raise ContractError(f"{field} must be a calendar date")


def _horizon(value: int) -> None:
    if type(value) is not int or not 0 < value <= 9999 * 12 - 1:
        raise ContractError("Outcome horizon must be a positive, bounded integer number of months")


def add_months(origin: date, months: int) -> date:
    _date(origin, "Origin")
    _horizon(months)
    month_number = origin.year * 12 + origin.month - 1 + months
    year, month = divmod(month_number, 12)
    if not 1 <= year <= 9999:
        raise ContractError("Outcome horizon exceeds the supported calendar")
    return date(year, month + 1, min(origin.day, calendar.monthrange(year, month + 1)[1]))


def _validate_pair(prediction: Prediction, outcome: Outcome, freeze: date,
                   policy: EvaluationPolicy, allow_synthetic: bool) -> tuple[date, date]:
    """Validate every row before deciding whether it enters the mature risk set."""
    _date(outcome.origin, "Outcome origin")
    _date(prediction.origin, "Prediction origin")
    _date(outcome.observed_until, "Outcome observation date")
    _date(outcome.label_available_at, "Outcome availability date")
    _identifier(outcome.cluster_id, "Outcome dependence cluster")
    _identifier(prediction.endpoint, "Prediction endpoint")
    _horizon(prediction.horizon_months)
    if (prediction.origin != outcome.origin or prediction.endpoint != outcome.endpoint or
            prediction.horizon_months != outcome.horizon_months or
            outcome.endpoint != policy.endpoint or outcome.horizon_months != policy.horizon_months):
        raise ContractError("Prediction/label/policy endpoint, horizon or origin mismatch")
    if type(prediction.synthetic) is not bool:
        raise ContractError("Prediction synthetic flag must be boolean")
    if prediction.synthetic and not allow_synthetic:
        raise ContractError("Synthetic predictions require explicit evaluation opt-in")
    if prediction.status not in ("scored", "abstained", "failed", "audit_only"):
        raise ContractError("Unknown prediction status")
    if prediction.reason is not None and not isinstance(prediction.reason, str):
        raise ContractError("Prediction reason must be text or null")
    if prediction.status == "scored":
        probability = prediction.probability
        if (type(probability) not in (int, float) or not 0 <= probability <= 1 or
                not math.isfinite(probability)):
            raise ContractError("Invalid scored probability")
    elif prediction.probability is not None:
        raise ContractError("An unscored prediction cannot carry a probability")
    horizon = add_months(outcome.origin, policy.horizon_months)
    try:
        matures_at = horizon + timedelta(days=policy.reporting_lag_days)
    except (ValueError, OverflowError) as error:
        raise ContractError("Horizon plus reporting lag exceeds the supported calendar") from error
    if outcome.label_available_at > freeze or outcome.observed_until > freeze:
        raise ContractError("Outcome information is later than the label freeze")
    if outcome.observed_until < outcome.origin or outcome.label_available_at < outcome.origin:
        raise ContractError("Outcome follow-up/availability cannot precede the origin")
    if outcome.event_at is not None:
        _date(outcome.event_at, "Outcome event date")
        if (outcome.event_at <= outcome.origin or outcome.event_at > outcome.observed_until or
                outcome.event_at > outcome.label_available_at):
            raise ContractError("Event date contradicts origin, observation or availability dates")
    if outcome.status not in ("resolved", "censored", "unresolved"):
        raise ContractError("Unknown outcome status")
    if outcome.status != "resolved":
        if outcome.value is not None:
            raise ContractError("Censored/unresolved outcome cannot be a negative label")
    else:
        if type(outcome.value) is not int or outcome.value not in (0, 1):
            raise ContractError("Resolved outcome must be an integer binary label")
        if outcome.value == 0 and outcome.observed_until < horizon:
            raise ContractError("A negative requires complete horizon follow-up")
        if outcome.value == 0 and outcome.label_available_at < horizon:
            raise ContractError("A negative label was not available before horizon completion")
        if outcome.value == 1 and (outcome.event_at is None or outcome.event_at > horizon):
            raise ContractError("Positive progression needs an eligible, available event date")
        if outcome.value == 0 and outcome.event_at is not None and outcome.event_at <= horizon:
            raise ContractError("Negative contradicts a progression event within the horizon")
    return horizon, matures_at


def _metrics(scored: list[tuple[int, float, str]]) -> dict:
    """One sorted threshold pass preserves exact tie groups in O(n log n)."""
    positives = sum(y for y, _, _ in scored)
    negatives = len(scored) - positives
    groups = []
    for probability, group in groupby(sorted(scored, key=lambda row: row[1]), lambda row: row[1]):
        size, positive_count = 0, 0
        for y, _, _ in group:
            size += 1
            positive_count += y
        groups.append((probability, positive_count, size - positive_count))
    lower_negatives, concordance = 0, 0.0
    for _, positive_count, negative_count in groups:
        concordance += positive_count * (lower_negatives + 0.5 * negative_count)
        lower_negatives += negative_count
    auc = concordance / (positives * negatives) if positives and negatives else None
    ap_terms, tp, fp = [], 0, 0
    if positives:
        for _, positive_count, negative_count in reversed(groups):
            tp += positive_count
            fp += negative_count
            ap_terms.append((positive_count / positives) * tp / (tp + fp))
    return {
        "cases": len(scored), "positive_cases": positives, "negative_cases": negatives,
        "clusters": len({cluster for _, _, cluster in scored}),
        "brier": math.fsum((p - y) ** 2 for y, p, _ in scored) / len(scored) if scored else None,
        "auroc": auc, "average_precision": math.fsum(ap_terms) if positives else None,
    }


def evaluate(predictions: tuple[Prediction, ...], labels: Outcomes,
             allow_synthetic: bool = False, *, policy: EvaluationPolicy | None = None) -> dict:
    """Report fixed-horizon descriptive metrics without asserting source provenance.

    Production callers must supply their registered policy and verify prediction
    producers separately. The omitted-policy path only preserves the raw API for
    a single endpoint/horizon, with its zero-day reporting assumption disclosed.
    Primary metrics require every mature member to have a label and prediction.
    Available-case metrics are separately named, and completion bounds retain all
    mature members without imputing either labels or probabilities.
    """
    if (not isinstance(labels, Outcomes) or type(labels.schema_version) is not int or
            labels.schema_version != 1):
        raise ContractError("Unsupported outcome schema")
    _date(labels.label_freeze, "Label freeze")
    if type(allow_synthetic) is not bool:
        raise ContractError("Synthetic evaluation opt-in must be boolean")
    if not isinstance(predictions, (tuple, list)) or not isinstance(labels.outcomes, (tuple, list)):
        raise ContractError("Predictions and outcomes must be explicit sequences")
    for prediction in predictions:
        if not isinstance(prediction, Prediction):
            raise ContractError("Invalid prediction record")
        _identifier(prediction.case_id, "Prediction case ID")
    for outcome in labels.outcomes:
        if not isinstance(outcome, Outcome):
            raise ContractError("Invalid outcome record")
        _identifier(outcome.case_id, "Outcome case ID")
        _identifier(outcome.endpoint, "Outcome endpoint")
        _horizon(outcome.horizon_months)
    if len({row.case_id for row in predictions}) != len(predictions):
        raise ContractError("Duplicate prediction cases")
    if len({row.case_id for row in labels.outcomes}) != len(labels.outcomes):
        raise ContractError("Duplicate outcome cases")
    predicted = {row.case_id: row for row in predictions}
    if set(predicted) != {row.case_id for row in labels.outcomes}:
        raise ContractError("Predictions and labels must cover the same registered cohort")
    if policy is None:
        endpoints = {(row.endpoint, row.horizon_months) for row in labels.outcomes}
        if len(endpoints) != 1:
            raise ContractError("Raw evaluation needs one endpoint/horizon, or an explicit policy for an empty cohort")
        endpoint, horizon_months = endpoints.pop()
        policy = EvaluationPolicy(1, endpoint, horizon_months, 0)
        policy_source = "inferred_legacy_zero_lag"
    else:
        policy_source = "explicit"
    if not isinstance(policy, EvaluationPolicy):
        raise ContractError("Invalid evaluation policy")
    policy.validate()

    populations = {name + "_case_ids": [] for name in (
        "registered", "mature", "immature", "resolved", "scored", "prediction_available",
        "registered_prediction_available", "censored", "unresolved", "missing_predictions")}
    case_states, excluded, scored, identity_rows = [], [], [], []
    lower_losses, upper_losses = [], []
    fixed_losses = missing_labels_only = missing_predictions = mature_positive = mature_negative = 0
    for outcome in sorted(labels.outcomes, key=lambda row: row.case_id):
        prediction = predicted[outcome.case_id]
        horizon, matures_at = _validate_pair(prediction, outcome, labels.label_freeze, policy, allow_synthetic)
        mature = matures_at <= labels.label_freeze
        label_known = outcome.status == "resolved"
        probability_available = prediction.status == "scored"
        populations["registered_case_ids"].append(outcome.case_id)
        if probability_available:
            populations["registered_prediction_available_case_ids"].append(outcome.case_id)
        identity_rows.append({"case_id": outcome.case_id, "origin": outcome.origin,
                              "endpoint": outcome.endpoint, "horizon_months": outcome.horizon_months,
                              "cluster_id": outcome.cluster_id})
        reasons = []
        if not mature:
            populations["immature_case_ids"].append(outcome.case_id)
            reasons.append("calendar_immature")
        else:
            populations["mature_case_ids"].append(outcome.case_id)
            if label_known:
                populations["resolved_case_ids"].append(outcome.case_id)
                mature_positive += outcome.value == 1
                mature_negative += outcome.value == 0
            else:
                populations[outcome.status + "_case_ids"].append(outcome.case_id)
            if probability_available:
                populations["prediction_available_case_ids"].append(outcome.case_id)
                p = prediction.probability
                if label_known:
                    scored.append((outcome.value, p, outcome.cluster_id))
                    populations["scored_case_ids"].append(outcome.case_id)
                    loss = (p - outcome.value) ** 2
                    lower_losses.append(loss)
                    upper_losses.append(loss)
                    fixed_losses += 1
                else:
                    losses = (p ** 2, (1 - p) ** 2)
                    lower_losses.append(min(losses))
                    upper_losses.append(max(losses))
                    missing_labels_only += 1
            else:
                populations["missing_predictions_case_ids"].append(outcome.case_id)
                lower_losses.append(0.0)
                upper_losses.append(1.0)
                missing_predictions += 1
        # Preserve both kinds of missingness, including on immature rows, rather
        # than recording only the first reason in a filtering sequence.
        if not label_known:
            reasons.append(outcome.status)
        if not probability_available:
            reasons.append("prediction_abstained_or_failed")
        excluded.extend({"case_id": outcome.case_id, "reason": reason} for reason in reasons)
        case_states.append({
            "case_id": outcome.case_id, "origin": outcome.origin.isoformat(),
            "horizon_at": horizon.isoformat(), "matures_at": matures_at.isoformat(),
            "calendar_mature": mature, "label_state": outcome.status,
            "prediction_state": "available" if probability_available else "missing",
            "prediction_status": prediction.status,
            "prediction_reason": prediction.reason,
            "scored": mature and label_known and probability_available,
            "exclusion_reasons": reasons,
        })

    denominators = {name.removesuffix("_case_ids"): len(ids) for name, ids in populations.items()}
    denominators.update(mature_positive=mature_positive, mature_negative=mature_negative)
    mature_count, registered_count = denominators["mature"], denominators["registered"]
    if not mature_count:
        metric_status = "no_mature_cases"
    elif denominators["resolved"] != mature_count:
        metric_status = "incomplete_labels"
    elif denominators["prediction_available"] != mature_count:
        metric_status = "incomplete_predictions"
    else:
        metric_status = "complete"
    conditional = _metrics(scored)
    primary = {name: conditional[name] if metric_status == "complete" else None
               for name in ("brier", "auroc", "average_precision")}
    return {
        "schema_version": 2, "estimator": "fixed_horizon_binary", "metric_status": metric_status,
        "prediction_provenance": "not_checked_by_metrics_function",
        "policy": encode(policy), "policy_source": policy_source,
        "label_freeze": labels.label_freeze.isoformat(),
        "population_fingerprint": fingerprint({"policy": policy, "label_freeze": labels.label_freeze,
                                                "registered": identity_rows}),
        "population_fingerprint_scope": "calendar_and_dependence_population; full_hypotheses_and_producers_not_verified",
        "denominators": denominators, "populations": populations, "case_states": case_states,
        "coverage_by_population": {
            "mature_of_registered": mature_count / registered_count if registered_count else 0,
            "resolved_of_mature": denominators["resolved"] / mature_count if mature_count else 0,
            "prediction_available_of_mature": denominators["prediction_available"] / mature_count if mature_count else 0,
            "scored_of_resolved": len(scored) / denominators["resolved"] if denominators["resolved"] else 0,
        },
        "conditional_metrics": {"population": "mature_resolved_with_predictions",
                                "interpretation": "available_case_descriptive_only; not the common_universe_estimate",
                                **conditional},
        "brier_completion_bounds": {
            "population": "common_mature_universe", "cases": mature_count,
            "lower": math.fsum(lower_losses) / mature_count if mature_count else None,
            "upper": math.fsum(upper_losses) / mature_count if mature_count else None,
            "fixed_loss_cases": fixed_losses, "missing_label_only_cases": missing_labels_only,
            "missing_prediction_cases": missing_predictions,
            "method": "bounded_completion; no_label_or_probability_imputation; not_a_confidence_interval",
        },
        # Legacy count/coverage aliases refer to the explicitly listed scored
        # subset. Primary metric aliases now require a complete mature universe.
        "cohort_size": registered_count, "scored_cases": len(scored),
        "coverage": len(scored) / registered_count if registered_count else 0,
        "positive_cases": conditional["positive_cases"], "negative_cases": conditional["negative_cases"],
        "clusters": conditional["clusters"], **primary, "excluded": excluded,
        "inference": "descriptive_only; clustered uncertainty and preregistered tests not implemented",
    }

