"""Frozen logistic scorer interface. Training/calibration are separate work."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from collections.abc import Mapping

from .contracts import Case, FEATURE_CATEGORIES, Profile
from .features import FEATURE_SCHEMA, FeatureVector
from .serde import ContractError, Frozen


@dataclass(frozen=True)
class ScorerArtifact(Frozen):
    schema_version: int
    model_id: str
    kind: str
    feature_schema: str
    aggregation: str
    endpoint: str
    horizon_months: int
    phases: tuple[int, ...]
    modalities: tuple[str, ...]
    intended_actions: tuple[str, ...]
    target_namespace_versions: tuple[str, ...]
    indication_namespace_versions: tuple[str, ...]
    training_origin_max: date
    training_label_available_max: date
    calibration_label_available_max: date | None
    training_manifest_sha256: str
    calibration: str
    intercept: float
    coefficients: Mapping[str, float]
    required_features: tuple[str, ...]
    missing_values: Mapping[str, float]
    minimum_coverage: float

    def validate(self) -> None:
        import re
        if (self.schema_version != 2 or self.kind not in ("synthetic_demo", "frozen_model") or
                self.feature_schema != FEATURE_SCHEMA or
                self.aggregation != "mean_of_unique_dependency_groups_v2"):
            raise ContractError("Unsupported scorer schema/type/aggregation")
        if not self.model_id.strip() or not self.coefficients:
            raise ContractError("Scorer identity and coefficients are required")
        names = set(self.coefficients)
        if (names - FEATURE_CATEGORIES.keys() or set(self.required_features) - names or
                set(self.missing_values) - names):
            raise ContractError("Unknown scorer feature or invalid missingness policy")
        if not re.fullmatch("[0-9a-f]{64}", self.training_manifest_sha256):
            raise ContractError("Training provenance hash is required")
        if not 0 <= self.minimum_coverage <= 1:
            raise ContractError("Invalid scorer coverage threshold")
        for name, value in self.missing_values.items():
            minimum = -1 if name in ("direction_alignment", "perturbation_support", "literature_support") else 0
            if not minimum <= value <= 1:
                raise ContractError("Frozen imputation is outside the declared feature range")
        if self.calibration not in ("none", "held_out_logistic"):
            raise ContractError("Unsupported calibration declaration")
        if self.calibration != "none" and self.calibration_label_available_max is None:
            raise ContractError("Calibration needs a dated label cutoff")
        values = [self.intercept, *self.coefficients.values(), *self.missing_values.values()]
        if any(not math.isfinite(value) for value in values):
            raise ContractError("Non-finite scorer parameters")


@dataclass(frozen=True)
class Contribution(Frozen):
    value: float
    coefficient: float
    log_odds: float
    imputed: bool
    observation_ids: tuple[str, ...]


@dataclass(frozen=True)
class Prediction(Frozen):
    case_id: str
    origin: date
    endpoint: str | None
    horizon_months: int | None
    status: str
    probability: float | None
    reason: str | None
    scorer_id: str | None
    synthetic: bool
    calibration: str | None
    feature_coverage: float | None
    intercept: float | None
    contributions: Mapping[str, Contribution]


def abstain(case: Case, reason: str, model: ScorerArtifact | None = None,
            coverage: float | None = None) -> Prediction:
    return Prediction(case.case_id, case.origin,
                      case.endpoint.name if case.endpoint else None,
                      case.endpoint.horizon_months if case.endpoint else None,
                      "audit_only" if case.task == "T6" else "abstained", None, reason,
                      model.model_id if model else None,
                      model is not None and model.kind == "synthetic_demo",
                      model.calibration if model else None, coverage, None, {})


def preflight_scorer(case: Case, profile: Profile, model: ScorerArtifact | None) -> str | None:
    if model is None:
        return "dossier_audit_has_no_clinical_probability" if case.task == "T6" else "no_frozen_scorer_configured"
    model.validate()
    if model.kind == "synthetic_demo" and profile != Profile.DEMO:
        raise ContractError("Synthetic weights cannot score real-data cases")
    if profile == Profile.DEMO and model.kind != "synthetic_demo":
        raise ContractError("Real scorer cannot be tested as a synthetic prediction")
    cutoffs = [model.training_origin_max, model.training_label_available_max,
               model.calibration_label_available_max]
    if any(cutoff >= case.origin for cutoff in cutoffs if cutoff is not None):
        raise ContractError("Training/calibration labels or origins reach the prediction origin")
    if case.task == "T6":
        return "dossier_audit_has_no_clinical_probability"
    hypothesis = case.hypothesis
    if (case.endpoint.name != model.endpoint or case.endpoint.horizon_months != model.horizon_months or
            case.program.phase_at_origin not in model.phases or hypothesis.modality not in model.modalities or
            hypothesis.intended_action not in model.intended_actions or
            hypothesis.target_namespace_version not in model.target_namespace_versions or
            hypothesis.indication_namespace_version not in model.indication_namespace_versions):
        return "outside_scorer_applicability"
    return None


def score(case: Case, profile: Profile, features: FeatureVector,
          model: ScorerArtifact | None) -> Prediction:
    reason = preflight_scorer(case, profile, model)
    if reason:
        return abstain(case, reason, model)
    if features.schema_version != model.feature_schema or features.aggregation != model.aggregation:
        raise ContractError("Feature contract differs from frozen scorer")
    present = sum(features.values[name].value is not None for name in model.coefficients)
    coverage = present / len(model.coefficients)
    if any(features.values[name].value is None for name in model.required_features):
        return abstain(case, "required_features_missing", model, coverage)
    if coverage < model.minimum_coverage:
        return abstain(case, "insufficient_feature_coverage", model, coverage)
    contributions = {}
    for name, coefficient in sorted(model.coefficients.items()):
        feature = features.values[name]
        imputed = feature.value is None
        if imputed and name not in model.missing_values:
            return abstain(case, "missing_feature_without_frozen_imputation", model, coverage)
        value = model.missing_values[name] if imputed else feature.value
        contributions[name] = Contribution(value, coefficient, value * coefficient,
                                            imputed, feature.observation_ids)
    logit = model.intercept + sum(item.log_odds for item in contributions.values())
    if not math.isfinite(logit):
        raise ContractError("Scorer arithmetic overflow")
    probability = 1 / (1 + math.exp(-logit)) if logit >= 0 else math.exp(logit) / (1 + math.exp(logit))
    return Prediction(case.case_id, case.origin, case.endpoint.name, case.endpoint.horizon_months,
                      "scored", probability, None, model.model_id, model.kind == "synthetic_demo",
                      model.calibration, coverage, model.intercept, contributions)

