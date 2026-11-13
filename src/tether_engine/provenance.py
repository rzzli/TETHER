"""Validated input DAGs: computation dates never replace information availability."""
from __future__ import annotations

import re
import hashlib
from pathlib import Path
from collections.abc import Mapping
from datetime import datetime

from .contracts import Case, Profile, Snapshot, SourceNode, TemporalClass
from .derivations import project, validate_descriptor
from .serde import (ContractError, MAX_NORMALIZED_JSON_BYTES, canonical, decode, freeze,
                    parse_json, read_json, safe_child, sha256_file)


MAX_DERIVATION_CACHE_BYTES = 256 * 1024 * 1024


def catalog_index(document: Mapping) -> Mapping:
    if document.get("schema_version") != 1:
        raise ContractError("Unsupported catalog version")
    records = document.get("datasets", ())
    if len({item["dataset_id"] for item in records}) != len(records):
        raise ContractError("Duplicate catalog dataset IDs")
    return freeze({item["dataset_id"]: item for item in records})


def check_role(dataset_id: str, role: str, catalog: Mapping | None) -> None:
    if role not in ("agent_evidence", "reference"):
        raise ContractError(f"Evaluator/unsupported input role denied: {dataset_id}")
    if catalog is not None:
        product = catalog.get(dataset_id)
        if product is None:
            raise ContractError(f"Unregistered dataset: {dataset_id}")
        roles = product.get("roles", ())
        if "evaluation_only" in roles or role not in roles:
            raise ContractError(f"Catalog denies agent access: {dataset_id}")


def check_receipt_availability(node: SourceNode, receipt: Mapping) -> None:
    """Reconcile a declared download-based bound with its exact receipt.

    Callers must separately verify receipt identity and bytes. A later download
    proves no earlier availability; other documented availability bases retain
    their own eligibility rules rather than inheriting the download timestamp.
    Shared by used-ancestry verification and the all-input policy boundary.
    """
    if node.availability.basis != "public_download_receipt":
        return
    observed_at = decode(datetime, receipt.get("completed_at_utc"))
    if (node.availability.known_public_by is None or node.availability.known_public_by < observed_at or
            node.availability.evidence_ref != node.receipt_sha256 or node.source_url != receipt.get("url")):
        raise ContractError("Contemporary availability bound does not match public-download receipt")


class InputGraph:
    def __init__(self, snapshot: Snapshot, root: Path, catalog: Mapping | None):
        self.snapshot, self.root, self.catalog = snapshot, root.resolve(), catalog
        self.nodes = freeze({item.source_id: item for item in snapshot.sources})
        # These caches live only for this validation pass. Finalization and
        # verification construct a new graph and reopen the original bytes.
        self._verified_proofs = {}
        self._payloads = {}
        self._payload_cache_bytes = 0
        self._verified_computations = set()
        if not self.nodes or len(self.nodes) != len(snapshot.sources):
            raise ContractError("v2 requires unique input-lineage nodes")
        visited, active = set(), set()

        def visit(key):
            if key not in self.nodes:
                raise ContractError(f"Missing input-lineage reference: {key}")
            if key in active:
                raise ContractError("Input-lineage cycle")
            if key in visited:
                return
            active.add(key)
            node = self.nodes[key]
            check_role(node.dataset_id, node.role, catalog)
            if not node.source_id.strip() or not node.release_id or not re.fullmatch("[0-9a-f]{64}", node.sha256):
                raise ContractError("Input source release and exact hash required")
            if node.computed_at is not None:
                if not node.parents or not node.method_id or not node.method_version or node.computed_at.tzinfo is None:
                    raise ContractError("Computed lineage requires parents and versioned method")
                if node.derivation is None:
                    raise ContractError("Computed lineage requires a registered derivation")
            elif node.parents:
                raise ContractError("Derived node requires computed_at")
            elif node.derivation is not None:
                raise ContractError("A derivation requires a computed lineage node")
            self.path(node)  # Validate paths without opening rejected future bytes.
            for parent in node.parents:
                visit(parent)
            active.remove(key)
            visited.add(key)
        for key in self.nodes:
            visit(key)

    def path(self, node: SourceNode) -> Path:
        base = self.root if node.computed_at is not None else Path(self.snapshot.raw_root or self.root)
        return safe_child(base, node.path)

    def closure(self, refs: tuple[str, ...]) -> tuple[str, ...]:
        if not refs:
            raise ContractError("Missing input lineage")
        found = set()
        def visit(key):
            if key not in self.nodes:
                raise ContractError(f"Missing input-lineage reference: {key}")
            if key in found:
                return
            found.add(key)
            for parent in self.nodes[key].parents:
                visit(parent)
        for ref in refs:
            visit(ref)
        return tuple(sorted(found))

    def exclusion(self, refs: tuple[str, ...], case: Case) -> str | None:
        for key in self.closure(refs):
            node = self.nodes[key]
            if node.computed_at is not None:
                validate_descriptor(node.derivation, node.parents, self.nodes, case.cutoff)
                if (node.method_id != node.derivation.method_id or
                        node.method_version != node.derivation.method_version):
                    raise ContractError("Computed source method identity differs from its derivation")
                if node.derivation.output_schema != "canonical_json.v1":
                    raise ContractError("Computed lineage requires the canonical JSON output schema")
                continue  # Its parents carry the information eligibility.
            reason = node.availability.exclusion(case.cutoff)
            if reason:
                return reason
            if self.snapshot.profile == Profile.HISTORICAL:
                if node.temporal_classification == TemporalClass.RECONSTRUCTED:
                    if not self.snapshot.allow_reconstructed:
                        return "reconstructed_history_not_approved"
                elif node.temporal_classification != TemporalClass.HISTORICAL:
                    return "not_verified_historical"
            elif node.temporal_classification == TemporalClass.UNVERIFIED:
                return "temporal_classification_unverified"
        return None

    def _payload(self, key: str) -> bytes:
        """Read bounded derivation inputs once, hashing the exact bytes consumed.

        Ordinary raw evidence (including large Parquet originals) continues to
        use streaming checksum verification and is never loaded into this cache.
        """
        if key in self._payloads:
            return self._payloads[key]
        node = self.nodes[key]
        path = self.path(node)
        if not path.is_file() or path.stat().st_size > MAX_NORMALIZED_JSON_BYTES:
            raise ContractError("Derivation input is missing or exceeds the 64 MiB limit")
        if self._payload_cache_bytes + path.stat().st_size > MAX_DERIVATION_CACHE_BYTES:
            raise ContractError("Aggregate derivation input cache exceeds the 256 MiB limit")
        with path.open("rb") as stream:
            payload = stream.read(MAX_NORMALIZED_JSON_BYTES + 1)
        if (len(payload) > MAX_NORMALIZED_JSON_BYTES or
                hashlib.sha256(payload).hexdigest() != node.sha256):
            raise ContractError(f"Derivation input checksum/size mismatch: {key}")
        if self._payload_cache_bytes + len(payload) > MAX_DERIVATION_CACHE_BYTES:
            raise ContractError("Aggregate derivation input cache exceeds the 256 MiB limit")
        self._payloads[key] = payload
        self._payload_cache_bytes += len(payload)
        return payload

    def payloads(self, refs: tuple[str, ...], case: Case) -> Mapping[str, bytes]:
        """Return only exact declared inputs after eligible ancestry verification."""
        reason = self.exclusion(refs, case)
        if reason:
            raise ContractError(f"Derivation contains ineligible input information: {reason}")
        self.verify(refs, {}, case=case)
        return freeze({key: self._payload(key) for key in refs})

    def _verify_computation(self, node: SourceNode, case: Case) -> None:
        if node.source_id in self._verified_computations:
            return
        # Parent computations are verified recursively before their bytes can be
        # supplied to another registered transform. The constructor rejects DAG
        # cycles, so this recursion cannot return to the current node.
        expected = project(node.derivation, self.payloads(node.parents, case))
        actual = parse_json(self._payload(node.source_id))
        if canonical(actual) != canonical(expected):
            raise ContractError(f"Computed source differs from its registered derivation: {node.source_id}")
        self._verified_computations.add(node.source_id)

    def verify(self, refs: tuple[str, ...], already: dict, *, case: Case | None = None) -> tuple[dict, ...]:
        closure = self.closure(refs)
        if any(self.nodes[key].computed_at is not None for key in closure):
            if case is None:
                raise ContractError("Computed lineage verification requires an eligibility case")
            reason = self.exclusion(refs, case)
            if reason:
                raise ContractError(f"Computed lineage contains ineligible information: {reason}")
        proofs = []
        for key in closure:
            if key in self._verified_proofs:
                already[key] = self._verified_proofs[key]
                proofs.append(self._verified_proofs[key])
                continue
            node = self.nodes[key]
            path = self.path(node)
            if not path.is_file() or sha256_file(path) != node.sha256:
                raise ContractError(f"Input source checksum mismatch: {key}")
            proof = {"artifact_id": key, "dataset_id": node.dataset_id,
                     "release_id": node.release_id, "path": str(path), "sha256": node.sha256,
                     "role": node.role, "parents": node.parents}
            if node.receipt_path:
                receipt_path = safe_child(Path(self.snapshot.raw_root or self.root), node.receipt_path)
                if not node.receipt_sha256 or sha256_file(receipt_path) != node.receipt_sha256:
                    raise ContractError("Input receipt checksum mismatch")
                receipt = read_json(receipt_path)
                if (receipt.get("status") != "completed" or receipt.get("sha256") != node.sha256 or
                        receipt.get("dataset_id") != node.dataset_id or receipt.get("release_id") != node.release_id or
                        safe_child(Path(self.snapshot.raw_root or self.root), receipt.get("relative_path", "")) != path or
                        receipt.get("bytes") != path.stat().st_size):
                    raise ContractError("Input receipt identity/status mismatch")
                check_receipt_availability(node, receipt)
                proof["receipt_path"], proof["receipt_sha256"] = str(receipt_path), node.receipt_sha256
            elif self.snapshot.profile != Profile.DEMO and node.computed_at is None:
                raise ContractError("Real raw inputs require archived public-download receipts")
            if node.computed_at is not None:
                self._verify_computation(node, case)
            already[key] = proof
            self._verified_proofs[key] = proof
            proofs.append(proof)
        return tuple(proofs)

