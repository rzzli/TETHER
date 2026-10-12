"""Version-two immutable contracts; v1 artifacts are verified without execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from .serde import ContractError, Frozen, fingerprint


class Profile(StrEnum):
    HISTORICAL = "historical_benchmark"
    CONTEMPORARY = "contemporary_assessment"
    DEMO = "synthetic_demo"


class TemporalClass(StrEnum):
    HISTORICAL = "verified_historical"
    RECONSTRUCTED = "reconstructed"
    CONTEMPORARY = "contemporary_only"
    UNVERIFIED = "unverified"


class Category(StrEnum):
    GENETICS = "genetics"
    PERTURBATION = "perturbation"
    EXPRESSION = "expression"
    MODALITY = "modality"
    LITERATURE = "literature"
    CLINICAL = "clinical"
    SAFETY = "safety"
    PATHWAY = "pathway"


class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    ABSENT = "absent"
    NOT_MEASURED = "not_measured"
    FAILED_QC = "failed_qc"
    ACCESS_DENIED = "access_denied"
    OUTSIDE_APPLICABILITY = "outside_applicability"


class Polarity(StrEnum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class Availability(Frozen):
    # Dates are conservative upper bounds when exact availability is uncertain.
    first_public_at: date | None
    release_public_at: date | None
    record_public_at: date | None
    annotation_public_at: date | None
    retrieved_at: date
    basis: str
    uncertainty: str | None
    known_public_by: datetime | None = None
    evidence_ref: str | None = None

    def exclusion(self, origin: date | datetime) -> str | None:
        cutoff = origin if isinstance(origin, datetime) else datetime.combine(origin, time.max, timezone.utc)
        dates = [self.first_public_at, self.release_public_at,
                 self.record_public_at, self.annotation_public_at]
        if not self.basis.strip():
            return "availability_unverified"
        if any(datetime.combine(value, time.max, timezone.utc) > cutoff for value in dates if value is not None):
            return "available_after_origin"
        if any(value > self.retrieved_at for value in dates if value is not None):
            return "availability_after_retrieval"
        if self.known_public_by is not None:
            if self.known_public_by.tzinfo is None or not self.evidence_ref:
                return "availability_proof_invalid"
            if self.known_public_by > cutoff:
                return "available_after_origin"
            if self.known_public_by.date() > self.retrieved_at:
                return "availability_after_retrieval"
        elif any(value is None for value in dates):
            return "availability_unverified"
        return None


@dataclass(frozen=True)
class Hypothesis(Frozen):
    target_id: str
    indication_id: str
    target_namespace_version: str
    indication_namespace_version: str
    intended_action: str
    modality: str
    tissue: str | None
    availability: Availability

    @property
    def key(self) -> str:
        return fingerprint({name: getattr(self, name) for name in (
            "target_id", "indication_id", "target_namespace_version", "indication_namespace_version",
            "intended_action", "modality", "tissue")})


@dataclass(frozen=True)
class Program(Frozen):
    program_id: str
    molecule_id: str
    sponsor: str
    phase_at_origin: int
    status_at_origin: str
    eligible_since: date
    mapping_confidence: float
    trial_ids: tuple[str, ...]
    availability: Availability


@dataclass(frozen=True)
class Endpoint(Frozen):
    name: str
    horizon_months: int


@dataclass(frozen=True)
class Case(Frozen):
    schema_version: int
    case_id: str
    task: str
    origin: date
    hypothesis: Hypothesis
    program: Program | None
    endpoint: Endpoint | None
    origin_at: datetime | None = None

    @property
    def cutoff(self) -> datetime:
        return self.origin_at or datetime.combine(self.origin, time.max, timezone.utc)

    def validate(self) -> None:
        if self.schema_version != 2 or self.task not in ("T1", "T6"):
            raise ContractError("New execution requires v2 inputs; see docs/V02_MIGRATION.md")
        if (self.origin_at is None or self.origin_at.tzinfo is None or
                self.origin_at.astimezone(timezone.utc).date() != self.origin):
            raise ContractError("v2 requires an exact UTC origin_at matching origin")
        values = [self.case_id, self.hypothesis.target_id, self.hypothesis.indication_id,
                  self.hypothesis.target_namespace_version,
                  self.hypothesis.indication_namespace_version,
                  self.hypothesis.intended_action, self.hypothesis.modality]
        if any(not value.strip() for value in values):
            raise ContractError("Case/hypothesis identifiers and versions must be nonempty")
        if self.hypothesis.availability.exclusion(self.cutoff):
            raise ContractError("Hypothesis mappings/annotations are not verified at origin")
        if self.program is not None and self.program.availability.exclusion(self.cutoff):
            raise ContractError("Program state/mapping was not available at origin")
        if self.task == "T1":
            if self.program is None or self.endpoint is None:
                raise ContractError("T1 requires an origin-eligible program and endpoint")
            program = self.program
            if (program.phase_at_origin not in (1, 2) or
                    self.endpoint.name != f"phase_{program.phase_at_origin}_to_{program.phase_at_origin + 1}"):
                raise ContractError("Endpoint does not match program phase at origin")
            if self.endpoint.horizon_months <= 0:
                raise ContractError("Horizon must be positive")
            if program.status_at_origin != "active" or program.eligible_since > self.origin:
                raise ContractError("Program was not active/eligible at origin")
            if not 0 < program.mapping_confidence <= 1:
                raise ContractError("Unresolved program mapping cannot be scored")
            if not all((program.program_id.strip(), program.molecule_id.strip(), program.sponsor.strip())):
                raise ContractError("Program identity must be explicit")


@dataclass(frozen=True)
class Artifact(Frozen):
    artifact_id: str
    dataset_id: str
    release_id: str
    path: str
    sha256: str
    role: str
    access_approved: bool
    temporal_classification: TemporalClass
    availability: Availability
    source_url: str
    input_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceNode(Frozen):
    source_id: str
    dataset_id: str
    release_id: str
    path: str
    sha256: str
    role: str
    availability: Availability
    temporal_classification: TemporalClass
    source_url: str
    parents: tuple[str, ...] = ()
    computed_at: datetime | None = None
    method_id: str | None = None
    method_version: str | None = None
    receipt_path: str | None = None
    receipt_sha256: str | None = None


@dataclass(frozen=True)
class Snapshot(Frozen):
    schema_version: int
    snapshot_id: str
    profile: Profile
    origin: date
    allow_reconstructed: bool
    artifacts: tuple[Artifact, ...]
    sources: tuple[SourceNode, ...] = ()
    raw_root: str | None = None
    coverage: Mapping[str, Any] = None
    origin_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.coverage is None:
            object.__setattr__(self, "coverage", {})
        super().__post_init__()


@dataclass(frozen=True)
class ScientificContext(Frozen):
    species: str | None
    ancestry: str | None
    tissue: str | None
    disease_state: str | None
    intervention: str | None
    comparator: str | None
    cohort_ids: tuple[str, ...]


@dataclass(frozen=True)
class QuantitativeResult(Frozen):
    effect: float | None
    scale: str | None
    standard_error: float | None
    ci_lower: float | None
    ci_upper: float | None
    sample_size: int | None
    adjusted_p_value: float | None


@dataclass(frozen=True)
class Method(Frozen):
    code_id: str
    version: str
    parameters: Mapping[str, Any]
    qc_status: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class Observation(Frozen):
    observation_id: str
    target_id: str
    indication_id: str
    program_id: str | None
    category: Category
    source_kind: str
    statement: str
    status: EvidenceStatus
    polarity: Polarity
    mechanism_direction: str
    study_id: str | None
    dependency_group: str | None
    context: ScientificContext
    quantitative: QuantitativeResult
    method: Method
    availability: Availability
    features: Mapping[str, float]
    feature_scope: str | None = None
    input_refs: tuple[str, ...] = ()
    computed_at: datetime | None = None
    source_locator: Mapping[str, Any] = None
    source_metrics: Mapping[str, Any] = None
    missingness: Mapping[str, str] = None
    publication_date: date | None = None
    publication_year: int | None = None

    def __post_init__(self) -> None:
        for name in ("source_locator", "source_metrics", "missingness"):
            if getattr(self, name) is None:
                object.__setattr__(self, name, {})
        super().__post_init__()


@dataclass(frozen=True)
class EvidencePacket(Frozen):
    schema_version: int
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class Citation(Frozen):
    artifact_id: str
    dataset_id: str
    release_id: str
    artifact_sha256: str
    source_url: str


@dataclass(frozen=True)
class GroundedObservation(Frozen):
    observation: Observation
    citation: Citation


@dataclass(frozen=True)
class Claim(Frozen):
    claim_id: str
    specialist: Category
    evidence: GroundedObservation
    extraction_mode: str
    admitted_fingerprint: str = ""


# Features are fixed normalized adapter outputs. This is not a trained feature set.
FEATURE_CATEGORIES = {
    "genetic_support": Category.GENETICS,
    "direction_alignment": Category.GENETICS,
    "perturbation_support": Category.PERTURBATION,
    "expression_relevance": Category.EXPRESSION,
    "modality_feasibility": Category.MODALITY,
    "literature_support": Category.LITERATURE,
    "safety_liability": Category.SAFETY,
    "pathway_support": Category.PATHWAY,
}


def validate_observation(observation: Observation) -> None:
    if not all(value.strip() for value in (observation.observation_id, observation.target_id,
                                           observation.indication_id, observation.statement)):
        raise ContractError("Observation identity and statement are required")
    if not observation.input_refs:
        raise ContractError("v2 observations require complete input lineage")
    if observation.source_kind == "computed" and (
            observation.computed_at is None or not observation.method.code_id or not observation.method.version):
        raise ContractError("Computed result requires computed_at and versioned method")
    if observation.source_kind not in ("primary", "integrated", "computed", "clinical"):
        raise ContractError("Unsupported source kind; labels/gold answers are not evidence inputs")
    if observation.mechanism_direction not in ("inhibit", "activate", "degrade", "uncertain", "not_applicable"):
        raise ContractError("Unsupported mechanism direction")
    if observation.method.qc_status not in ("passed", "failed", "not_run"):
        raise ContractError("Invalid QC status")
    result = observation.quantitative
    if result.standard_error is not None and result.standard_error <= 0:
        raise ContractError("Standard error must be positive")
    if result.sample_size is not None and result.sample_size <= 0:
        raise ContractError("Sample size must be positive")
    if result.adjusted_p_value is not None and not 0 <= result.adjusted_p_value <= 1:
        raise ContractError("Invalid adjusted p value")
    if ((result.ci_lower is None) != (result.ci_upper is None) or
            (result.ci_lower is not None and result.ci_lower > result.ci_upper)):
        raise ContractError("Incomplete or reversed confidence interval")
    if observation.features:
        if (observation.status != EvidenceStatus.OBSERVED or observation.method.qc_status != "passed"):
            raise ContractError("Unobserved or unreviewed evidence cannot create numerical features")
        if observation.source_kind == "clinical" or observation.category == Category.CLINICAL:
            raise ContractError("Clinical/known-drug evidence cannot enter prediction features")
        if not observation.feature_scope:
            raise ContractError("Numerical features require a hypothesis derivation scope")
        if not observation.method.code_id.strip() or not observation.method.version.strip():
            raise ContractError("Feature-generating method must be versioned")
        for name, value in observation.features.items():
            if name not in FEATURE_CATEGORIES or FEATURE_CATEGORIES[name] != observation.category:
                raise ContractError(f"Invalid feature/category mapping: {name}")
            minimum = -1 if name in ("direction_alignment", "perturbation_support", "literature_support") else 0
            if not minimum <= value <= 1:
                raise ContractError(f"Feature {name} outside declared range")

