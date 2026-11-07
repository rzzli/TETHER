"""Approved normalized packets, time gates and a narrow retrieval capability."""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .contracts import (Case, Category, Citation, EvidencePacket, GroundedObservation,
                        Profile, Snapshot, TemporalClass, validate_observation)
from .serde import ContractError, Frozen, decode, freeze, fingerprint, parse_json, read_json, safe_child
from .provenance import InputGraph, catalog_index, check_role


@dataclass(frozen=True)
class Exclusion(Frozen):
    item_id: str
    level: str
    reason: str


class EvidenceStore:
    """Only the trusted runner reads paths; specialists receive immutable views."""

    def __init__(self, snapshot: Snapshot, records: tuple[GroundedObservation, ...],
                 exclusions: tuple[Exclusion, ...], sources: tuple[dict, ...], policy=None,
                 *, snapshot_base: Path | None = None):
        self.snapshot = snapshot
        try:
            self.snapshot_base = None if snapshot_base is None else Path(snapshot_base).resolve()
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            raise ContractError('Invalid snapshot base') from error
        self._records = freeze({record.observation.observation_id: record for record in records})
        index = {}
        for record in self._records.values():
            observation = record.observation
            index.setdefault((observation.target_id, observation.indication_id, observation.category), []).append(record)
        self._query_index = freeze(index)
        self.admitted_fingerprints = freeze({key: fingerprint(record) for key, record in self._records.items()})
        self.exclusions = exclusions
        self.source_proofs = freeze(sources)
        self.catalog_policy = freeze(policy)

    def execution_base(self) -> Path:
        """Query-only stores are supported; execution requires an explicit live base."""
        if self.snapshot_base is None:
            raise ContractError('Execution requires an explicit snapshot base')
        if getattr(self, 'archive_graph', None) is not None:
            raise ContractError('Archive verification stores are read-only; re-admit for new execution')
        try:
            base = Path(self.snapshot_base)
            if not base.is_absolute():
                raise ContractError('Execution snapshot base must be absolute')
            base = base.resolve()
            if not base.is_dir():
                raise ContractError('Execution snapshot base is not a directory')
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise ContractError('Invalid execution snapshot base') from error
        return base

    def query(self, case: Case, category: Category) -> tuple[GroundedObservation, ...]:
        # Exact normalized identifiers only; crosswalks belong in audited adapters.
        return tuple(record for record in self._query_index.get(
                         (case.hypothesis.target_id, case.hypothesis.indication_id, category), ())
                     if case.permits_program(record.observation.program_id))

    def lookup(self, observation_id: str) -> GroundedObservation:
        try:
            return self._records[observation_id]
        except KeyError as error:
            raise ContractError(f"Observation is outside approved snapshot: {observation_id}") from error


def publication_exclusion(observation, case: Case) -> str | None:
    """Publication precision never substitutes for eligible information lineage.

    A year overlapping origin is not a known exact publication date. It remains
    usable only through the caller's complete availability/lineage admission;
    no January/December date is imputed. Exact future dates/years and conflicting
    date/year metadata remain ineligible. Computation dates are a separate clock.
    """
    published, year = observation.publication_date, observation.publication_year
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise ContractError('Invalid publication year')
    if published is not None and type(published) is not date:
        raise ContractError('Invalid publication date')
    if published is not None and year is not None and published.year != year:
        return 'publication_metadata_inconsistent'
    if (published is not None and published > case.origin or
            year is not None and year > case.origin.year):
        return 'publication_after_origin'
    return None


def observation_exclusion(observation, artifact, graph: InputGraph, case: Case, artifact_inputs=None) -> str | None:
    """The same observation gate is used for admission and semantic verification."""
    validate_observation(observation)
    if observation.program_id is not None and case.program is not None and case.program.mapping_confidence == 0:
        return "unresolved_program_mapping"
    if artifact_inputs is None:
        artifact_inputs = frozenset(graph.closure(artifact.input_refs))
    if not set(graph.closure(observation.input_refs)).issubset(artifact_inputs):
        raise ContractError("Observation lineage escapes its artifact's declared inputs")
    reason = graph.exclusion(observation.input_refs, case)
    if not reason and observation.source_kind != "computed":
        reason = observation.availability.exclusion(case.cutoff)
    if not reason:
        reason = publication_exclusion(observation, case)
    return reason


def eligible_artifacts(snapshot: Snapshot, graph: InputGraph, case: Case):
    """Validate the artifact inventory, yielding each artifact and its exclusion."""
    identifiers, paths = set(), set()
    for artifact in snapshot.artifacts:
        if (not artifact.artifact_id.strip() or not artifact.release_id.strip() or
                artifact.artifact_id in identifiers or artifact.path in paths or artifact.artifact_id in graph.nodes):
            raise ContractError("Artifact IDs and paths must be unique and releases explicit")
        identifiers.add(artifact.artifact_id)
        paths.add(artifact.path)
        if not re.fullmatch("[0-9a-f]{64}", artifact.sha256):
            raise ContractError(f"Invalid SHA-256: {artifact.artifact_id}")
        if artifact.role != "agent_evidence":
            raise ContractError(f"Evaluator/reference-only artifact denied: {artifact.artifact_id}")
        safe_child(graph.root, artifact.path)
        if not artifact.access_approved:
            yield artifact, "access_denied"
            continue
        check_role(artifact.dataset_id, artifact.role, graph.catalog)
        yield artifact, graph.exclusion(artifact.input_refs, case)


def required_source_proofs(snapshot: Snapshot, case: Case, root: Path, policy=None) -> tuple[dict, ...]:
    """Rebuild the complete eligible proof inventory without reading source bytes."""
    graph = InputGraph(snapshot, root, catalog_index(policy) if policy else None)
    proofs, parents = [], set()
    for artifact, reason in eligible_artifacts(snapshot, graph, case):
        if reason:
            continue
        proofs.append({"artifact_id": artifact.artifact_id, "dataset_id": artifact.dataset_id,
                       "release_id": artifact.release_id, "path": str(safe_child(root, artifact.path)),
                       "sha256": artifact.sha256})
        parents.update(graph.closure(artifact.input_refs))
    for key in sorted(parents):
        node = graph.nodes[key]
        proof = {"artifact_id": key, "dataset_id": node.dataset_id, "release_id": node.release_id,
                 "path": str(graph.path(node)), "sha256": node.sha256, "role": node.role,
                 "parents": node.parents}
        if node.receipt_path:
            if not node.receipt_sha256:
                raise ContractError("Input receipt checksum missing")
            proof.update(receipt_path=str(safe_child(Path(snapshot.raw_root or root), node.receipt_path)),
                         receipt_sha256=node.receipt_sha256)
        elif snapshot.profile != Profile.DEMO and node.computed_at is None:
            raise ContractError("Real raw inputs require archived public-download receipts")
        proofs.append(proof)
    return tuple(proofs)


def load_snapshot(path: Path, case: Case, catalog_path: Path | None = None) -> EvidenceStore:
    snapshot = decode(Snapshot, read_json(path), "snapshot")
    policy = read_json(catalog_path) if snapshot.profile != Profile.DEMO and catalog_path else None
    return admit_snapshot(snapshot, case, path.parent, policy)


def admit_snapshot(snapshot: Snapshot, case: Case, root: Path, policy=None) -> EvidenceStore:
    """Admit sealed inputs using either the live or archived effective catalog."""
    case.validate()
    if snapshot.schema_version != 2 or not snapshot.snapshot_id.strip():
        raise ContractError("New execution requires a v2 snapshot; see docs/V02_MIGRATION.md")
    if snapshot.origin != case.origin or snapshot.origin_at != case.origin_at:
        raise ContractError("Snapshot origin must equal case origin")
    catalog = None
    if snapshot.profile != Profile.DEMO:
        if policy is None:
            raise ContractError("Real-data snapshots require the project dataset catalog")
        catalog = catalog_index(policy)
    graph = InputGraph(snapshot, root, catalog)
    observations_seen = set()
    records, exclusions, proofs = [], [], []
    input_proofs = {}
    root = root.resolve()
    for artifact, reason in eligible_artifacts(snapshot, graph, case):
        source_path = safe_child(root, artifact.path)
        if reason:
            # Never open rejected artifact bytes or expose its content to a backend.
            exclusions.append(Exclusion(artifact.artifact_id, "artifact", reason))
            continue
        if not source_path.is_file():
            raise ContractError(f"Approved artifact missing: {artifact.artifact_id}")
        if source_path.stat().st_size > 64 * 1024 * 1024:
            raise ContractError("Evidence packet exceeds the 64 MiB normalized-input limit")
        # Hash the exact bytes subsequently decoded, preventing a hash/read race.
        payload = source_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != artifact.sha256:
            raise ContractError(f"Artifact checksum mismatch: {artifact.artifact_id}")
        packet = decode(EvidencePacket, parse_json(payload), artifact.artifact_id)
        if packet.schema_version != 2:
            raise ContractError("Unsupported evidence-packet version")
        proofs.append({"artifact_id": artifact.artifact_id,
                       "dataset_id": artifact.dataset_id, "release_id": artifact.release_id,
                       "path": str(source_path), "sha256": artifact.sha256})
        citation = Citation(artifact.artifact_id, artifact.dataset_id, artifact.release_id,
                            artifact.sha256, artifact.source_url)
        artifact_inputs = frozenset(graph.closure(artifact.input_refs))
        for observation in packet.observations:
            if observation.observation_id in observations_seen:
                raise ContractError(f"Duplicate observation ID: {observation.observation_id}")
            observations_seen.add(observation.observation_id)
            reason = observation_exclusion(observation, artifact, graph, case, artifact_inputs)
            if reason:
                exclusions.append(Exclusion(observation.observation_id, "observation", reason))
                continue
            records.append(GroundedObservation(observation, citation))
            graph.verify(observation.input_refs, input_proofs)
        graph.verify(artifact.input_refs, input_proofs)
    result = EvidenceStore(snapshot, tuple(records), tuple(exclusions),
                           tuple(proofs) + tuple(input_proofs.values()), policy, snapshot_base=root)
    return result

