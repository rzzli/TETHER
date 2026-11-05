"""Pure-stdlib schema2 fictional input construction; no validation or oracle use."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .cases import canonical, file_bytes, fingerprint, source_documents

IDENTITY_FIELDS = ("dataset_id", "release_id", "root_alias", "relative_path", "sha256", "bytes")
POLICY_RECIPES = frozenset({
    "none", "used_receipt_late", "unused_receipt_late", "unused_receipt_url", "unused_receipt_ref",
    "receipt_utc_alias", "alternative_basis_later_download", "missing_grant", "ungranted_source",
    "wrong_frame", "evaluator_product", "unsupported_scorer", "copied_control_reseal",
    "projection_reseal", "dossier_reseal", "valid_outer",
})
OUTER_RECIPES = frozenset({"copied_control_reseal", "projection_reseal", "dossier_reseal", "valid_outer"})


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(file_bytes(value))


def _read(root, descriptor, key):
    return json.loads((root / descriptor["paths"][key]).read_bytes())


def _policy_catalog(catalog, payload):
    products = []
    for row in catalog["datasets"]:
        products.append(dict(dataset_id=row["dataset_id"], metadata=copy.deepcopy(row),
            input_dependencies=copy.deepcopy(row.get("dependencies", [])), validation_dependencies=[],
            conditional_input_groups=copy.deepcopy(row.get("conditional_input_groups", [])),
            dependency_review_status="reviewed_for_selected_frame",
            agent_use_policy="denied_evaluator_product" if "evaluation_only" in row["roles"] else "requires_artifact_grant"))
    return dict(schema_version=2, policy_id="fictional-equal-policy-v1", created_at_utc="2026-11-02T00:00:00Z",
        source_catalog=dict(path="catalog.json", sha256=hashlib.sha256(payload).hexdigest(), document_fingerprint=fingerprint(catalog)),
        catalog_metadata={key: copy.deepcopy(value) for key, value in catalog.items() if key != "datasets"},
        products=products, artifacts=[], uses=[])


def prepare_policy_sources(root, spec, descriptor):
    """Return (updated descriptor, outer mutation or None); never run a validator.

    Input recipes intentionally keep structural hashes consistent so a temporal,
    role or grant defect is not accidentally reduced to an unrelated stale hash.
    The root-owned materializer subsequently produces native outer run bytes for
    the four outer recipes. Existing source files are retained and never moved.
    """
    root = Path(root).resolve()
    if spec["variant"] != "artifact_policy_v2":
        raise ValueError("Schema2 materializer requires artifact_policy_v2")
    recipe = spec["preparation"]["recipe"]["policy_recipe"]
    if recipe not in POLICY_RECIPES:
        raise ValueError("Unknown policy construction recipe: " + recipe)
    descriptor = copy.deepcopy(descriptor)
    case, snapshot, catalog = (_read(root, descriptor, key) for key in ("case", "snapshot", "catalog"))
    source_directory = (root / descriptor["paths"]["snapshot"]).parent
    raw_root, snapshot_root, metadata_root = (root / name for name in ("raw", "snapshot", "metadata"))
    # Exclusive directory creation prevents accidental reuse of a preparation.
    for directory in (raw_root, snapshot_root, metadata_root):
        directory.mkdir(exist_ok=False)
    snapshot["raw_root"] = str(raw_root)
    source_nodes = snapshot["sources"]
    used = source_nodes[0]
    receipts = {}
    raw_payloads = {}
    for node in source_nodes:
        if node["computed_at"] is not None:
            _write(snapshot_root / node["path"], (source_directory / node["path"]).read_bytes())
            continue
        payload = (source_directory / node["path"]).read_bytes()
        receipt = json.loads((source_directory / node["receipt_path"]).read_bytes())
        raw_payloads[node["source_id"]] = payload
        receipts[node["source_id"]] = receipt
        node["availability"].update(basis="public_download_receipt",
            known_public_by="2021-01-01T00:00:00+00:00", evidence_ref=None)
    add_unused = recipe in {"unused_receipt_late", "unused_receipt_url", "unused_receipt_ref", "ungranted_source"}
    if add_unused:
        unused = copy.deepcopy(used)
        unused.update(source_id="unused-source", path="unused.json", source_url="https://example.invalid/unused-source",
                      receipt_path="unused-receipt.json")
        source_nodes.append(unused)
        payload = file_bytes(dict(fictional=True, unused=True))
        raw_payloads[unused["source_id"]] = payload
        receipts[unused["source_id"]] = dict(receipt_id="fictional-unused-receipt", dataset_id=unused["dataset_id"],
            release_id=unused["release_id"], relative_path=unused["path"], sha256=hashlib.sha256(payload).hexdigest(),
            bytes=len(payload), url=unused["source_url"], status="completed", completed_at_utc="2021-01-01T00:00:00+00:00")
    if recipe == "evaluator_product":
        used["dataset_id"] = "fixture_answers"
        receipts[used["source_id"]]["dataset_id"] = "fixture_answers"
    if recipe == "used_receipt_late":
        receipts[used["source_id"]]["completed_at_utc"] = "2022-01-01T00:00:00+00:00"
    if recipe == "unused_receipt_late":
        receipts["unused-source"]["completed_at_utc"] = "2022-01-01T00:00:00+00:00"
    if recipe == "unused_receipt_url":
        receipts["unused-source"]["url"] = "https://example.invalid/different-transport-source"
    if recipe == "receipt_utc_alias":
        receipts[used["source_id"]]["completed_at_utc"] = "2021-01-01T00:00:00Z"
    if recipe == "alternative_basis_later_download":
        used["availability"].update(basis="fictional_release_documentation", known_public_by=None, evidence_ref=None)
        receipts[used["source_id"]]["completed_at_utc"] = "2025-01-01T00:00:00+00:00"
    for node in source_nodes:
        if node["computed_at"] is not None:
            continue
        receipt = receipts[node["source_id"]]
        payload = raw_payloads[node["source_id"]]
        node["sha256"] = hashlib.sha256(payload).hexdigest()
        receipt.update(sha256=node["sha256"], bytes=len(payload), relative_path=node["path"])
        node["receipt_sha256"] = hashlib.sha256(file_bytes(receipt)).hexdigest()
        if node["availability"]["basis"] == "public_download_receipt":
            node["availability"]["evidence_ref"] = node["receipt_sha256"]
        if recipe == "unused_receipt_ref" and node["source_id"] == "unused-source":
            node["availability"]["evidence_ref"] = "0" * 64
        _write(raw_root / node["path"], payload)
        _write(raw_root / node["receipt_path"], receipt)
    for artifact in snapshot["artifacts"]:
        _write(snapshot_root / artifact["path"], (source_directory / artifact["path"]).read_bytes())

    catalog_bytes = file_bytes(catalog)
    _write(metadata_root / "catalog.json", catalog_bytes)
    proof_bytes = file_bytes(dict(fictional=True, purpose="Equal-policy software conformance inputs",
                                 scientific_validation="not_established"))
    _write(metadata_root / "provenance.json", proof_bytes)
    document = _policy_catalog(catalog, catalog_bytes)
    by_node = {}
    for node, kind, alias in [(node, "raw" if node["computed_at"] is None else "derived",
                             "raw" if node["computed_at"] is None else "snapshot") for node in source_nodes] + [
                             (node, "packet", "snapshot") for node in snapshot["artifacts"]]:
        native_id = node.get("source_id", node.get("artifact_id"))
        base = raw_root if kind == "raw" else snapshot_root
        receipt_ref = None
        if kind == "raw":
            receipt_ref = dict(root_alias="raw", relative_path=node["receipt_path"], sha256=node["receipt_sha256"],
                receipt_id=receipts[native_id]["receipt_id"], url=node["source_url"])
        parent_ids = node.get("parents", node.get("input_refs", []))
        record = dict(dataset_id=node["dataset_id"], release_id=node["release_id"], root_alias=alias,
            relative_path=node["path"], sha256=node["sha256"], bytes=(base / node["path"]).stat().st_size,
            kind=kind, parents=[by_node[parent]["artifact_id"] for parent in parent_ids],
            availability=copy.deepcopy(node["availability"]), temporal_classification=node["temporal_classification"],
            source_url=node["source_url"], provenance=dict(kind="download_receipt" if kind == "raw" else "generated",
                evidence=[dict(path="provenance.json", sha256=hashlib.sha256(proof_bytes).hexdigest())], receipt=receipt_ref),
            scope="Fictional equal-policy conformance fixture", scientific_validation="not_established")
        record["artifact_id"] = "artifact-" + fingerprint({key: record[key] for key in IDENTITY_FIELDS})
        by_node[native_id] = record
        document["artifacts"].append(record)
    frame = fingerprint(dict(frame="fictional-equal-policy-v1", control_id=spec["control_id"]))
    grants = [dict(artifact_id=by_node[node.get("source_id", node.get("artifact_id"))]["artifact_id"], role=node["role"])
              for node in [*source_nodes, *snapshot["artifacts"]]]
    if recipe == "missing_grant":
        grants = [grant for grant in grants if grant["artifact_id"] != by_node[used["source_id"]]["artifact_id"]]
    if recipe == "ungranted_source":
        grants = [grant for grant in grants if grant["artifact_id"] != by_node["unused-source"]["artifact_id"]]
    document["uses"] = [dict(use_id="fictional-use", kind="contemporary_evidence", status="allowed",
        profile=snapshot["profile"], origin_at=case["origin_at"], frame_sha256=frame,
        case_fingerprint=fingerprint(case), snapshot_fingerprint=fingerprint(snapshot),
        raw_root_alias="raw", snapshot_root_alias="snapshot", grants=grants, blockers=[])]
    roots = dict(schema_version=1, roots=dict(raw=str(raw_root), snapshot=str(snapshot_root), metadata=str(metadata_root)))
    _write(metadata_root / "policy.json", document)
    _write(metadata_root / "roots.json", roots)
    _write(metadata_root / "case.json", case)
    _write(snapshot_root / "snapshot.json", snapshot)
    descriptor["paths"].update(case="metadata/case.json", snapshot="snapshot/snapshot.json", catalog="metadata/catalog.json",
                               catalog_policy="metadata/policy.json", policy_roots="metadata/roots.json")
    descriptor["options"]["policy_use"] = "fictional-use"
    descriptor["anchors"]["frame_sha256"] = "0" * 64 if recipe == "wrong_frame" else frame
    if recipe == "unsupported_scorer":
        scorer = source_documents("core_t1")["scorer"]
        scorer["kind"] = "frozen_model"
        _write(metadata_root / "unsupported-scorer.json", scorer)
        descriptor["paths"]["scorer"] = "metadata/unsupported-scorer.json"
    return descriptor, (recipe if recipe in OUTER_RECIPES else None)
