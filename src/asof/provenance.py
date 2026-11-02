"""Validated input DAGs: computation dates never replace information availability."""
from __future__ import annotations

import re
from pathlib import Path
from collections.abc import Mapping
from datetime import datetime

from .contracts import Case, Profile, Snapshot, SourceNode, TemporalClass
from .serde import ContractError, decode, freeze, read_json, safe_child, sha256_file


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
            elif node.parents:
                raise ContractError("Derived node requires computed_at")
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

    def verify(self, refs: tuple[str, ...], already: dict) -> tuple[dict, ...]:
        proofs = []
        for key in self.closure(refs):
            if key in already:
                proofs.append(already[key])
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
            already[key] = proof
            proofs.append(proof)
        return tuple(proofs)

