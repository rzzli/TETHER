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
from .derivations import validate_descriptor, verify_observation


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

    def validate_execution(self, case: Case) -> InputGraph:
        """Re-admit the live inputs before an actor can see this store.

        This also checks explicitly constructed stores, whose recorded admission
        fingerprints alone cannot prove that the records came from their packet.
        The fresh graph is reused for ledger checks within this execution pass.
        """
        base = self.execution_base()
        fresh = admit_snapshot(self.snapshot, case, base, self.catalog_policy)
        if (fingerprint(self._records) != fingerprint(fresh._records) or
                fingerprint(self.admitted_fingerprints) != fingerprint(fresh.admitted_fingerprints)):
            raise ContractError("Execution store differs from freshly admitted source records")
        if (set(self._query_index) != set(fresh._query_index) or
                any(fingerprint(self._query_index[key]) != fingerprint(records)
                    for key, records in fresh._query_index.items())):
            raise ContractError("Execution query cache differs from freshly admitted source records")
        if fingerprint(self.exclusions) != fingerprint(fresh.exclusions):
            raise ContractError("Execution store exclusions differ from source admission")

        def inventory(proofs):
            result = {item["artifact_id"]: item for item in proofs}
            if len(result) != len(proofs):
                raise ContractError("Execution store contains duplicate source proofs")
            return result

        if fingerprint(inventory(self.source_proofs)) != fingerprint(inventory(fresh.source_proofs)):
            raise ContractError("Execution store source proofs differ from live inputs")
        self._execution_graph = fresh._execution_graph
        self._execution_case_fingerprint = fingerprint(case)
        return self._execution_graph

    def validate_record(self, case: Case, record: GroundedObservation) -> None:
        """Check a ledger candidate against the current source-validation pass."""
        graph = getattr(self, "_execution_graph", None)
        if (graph is None or graph.snapshot is not self.snapshot or
                getattr(self, "_execution_case_fingerprint", None) != fingerprint(case)):
            graph = self.validate_execution(case)
        observation, citation = record.observation, record.citation
        if fingerprint(record) != self.admitted_fingerprints.get(observation.observation_id):
            raise ContractError("Record no longer matches its admitted source fingerprint")
        artifact = next((item for item in self.snapshot.artifacts
                         if item.artifact_id == citation.artifact_id), None)
        if (artifact is None or citation.artifact_sha256 != artifact.sha256 or
                citation.dataset_id != artifact.dataset_id or citation.release_id != artifact.release_id or
                citation.source_url != artifact.source_url):
            raise ContractError("Record citation differs from the admitted artifact")
        reason = observation_exclusion(observation, artifact, graph, case)
        if reason:
            raise ContractError(f"Record contains ineligible information: {reason}")


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


def observation_exclusion(observation, artifact, graph: InputGraph, case: Case, artifact_inputs=None,
                          *, verify_derivations: bool = True) -> str | None:
    """The same observation gate is used for admission and semantic verification."""
    validate_observation(observation)
    if observation.source_kind != "computed" and observation.derivation is not None:
        raise ContractError("An observation derivation requires computed source kind")
    if observation.program_id is not None and case.program is not None and case.program.mapping_confidence == 0:
        return "unresolved_program_mapping"
    if artifact_inputs is None:
        artifact_inputs = frozenset(graph.closure(artifact.input_refs))
    if not set(graph.closure(observation.input_refs)).issubset(artifact_inputs):
        raise ContractError("Observation lineage escapes its artifact's declared inputs")
    reason = graph.exclusion(observation.input_refs, case)
    if not reason and observation.source_kind == "computed":
        if observation.derivation is None:
            raise ContractError("Computed observation requires a registered derivation")
        validate_descriptor(observation.derivation, observation.input_refs, graph.nodes, case.cutoff)
        if observation.derivation.output_schema != "observation.v2":
            raise ContractError("Computed observation requires the observation output schema")
    if not reason:
        # A registered projection retains its source information availability;
        # computed_at alone is a later execution clock and is never gated here.
        reason = observation.availability.exclusion(case.cutoff)
    if not reason:
        reason = publication_exclusion(observation, case)
    if not reason and verify_derivations:
        if observation.source_kind == "computed":
            verify_observation(observation, observation.derivation,
                               graph.payloads(observation.input_refs, case),
                               eligible_refs=graph.closure(observation.input_refs))
        elif any(graph.nodes[key].computed_at is not None
                 for key in graph.closure(observation.input_refs)):
            # Integrated/primary observations cannot conceal an unverified
            # computed ancestor behind an ordinary observation source kind.
            graph.verify(observation.input_refs, {}, case=case)
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
            graph.verify(observation.input_refs, input_proofs, case=case)
        graph.verify(artifact.input_refs, input_proofs, case=case)
    result = EvidenceStore(snapshot, tuple(records), tuple(exclusions),
                           tuple(proofs) + tuple(input_proofs.values()), policy, snapshot_base=root)
    result._execution_graph = graph
    result._execution_case_fingerprint = fingerprint(case)
    return result

