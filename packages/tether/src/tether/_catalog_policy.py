"""Pure, additive artifact policy over the frozen schema-one catalog.

This module never opens originals, writes receipts, executes a model, or changes
the compatibility engine. Callers must stable-read/copy inputs and bind the
returned projection at execution and verification. A projection alone is not an
artifact authorization boundary.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import PurePosixPath, PureWindowsPath
import re

from asof.contracts import Availability
from asof.serde import ContractError, canonical, decode, fingerprint

MAX_POLICY_BYTES = 16 * 1024 * 1024
ROLES = {"agent_evidence", "reference", "evaluation_only", "comparison_only"}
PROFILES = {"contemporary_assessment", "historical_benchmark", "synthetic_demo"}
TEMPORAL = {"verified_historical", "reconstructed", "contemporary_only", "unverified"}
USE_KINDS = {"contemporary_evidence", "normalization_reference", "origin_context",
             "endpoint_evaluation", "ascertainment_evaluation"}
IDENTITY_FIELDS = ("dataset_id", "release_id", "root_alias", "relative_path", "sha256", "bytes")
POLICY_FIELDS = {"schema_version", "policy_id", "created_at_utc", "source_catalog",
                 "catalog_metadata", "products", "artifacts", "uses"}
PRODUCT_FIELDS = {"dataset_id", "metadata", "input_dependencies", "validation_dependencies",
                  "conditional_input_groups", "dependency_review_status", "agent_use_policy"}
ARTIFACT_FIELDS = {"artifact_id", *IDENTITY_FIELDS, "kind", "parents", "availability",
                   "temporal_classification", "source_url", "provenance", "scope", "scientific_validation"}
USE_FIELDS = {"use_id", "kind", "status", "profile", "origin_at", "frame_sha256",
              "case_fingerprint", "snapshot_fingerprint", "raw_root_alias", "snapshot_root_alias",
              "grants", "blockers"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
ALIAS = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}\Z")


def _need(value, message):
    if not value:
        raise ContractError("TETHER catalog policy: " + message)


def _text(value, name):
    _need(type(value) is str and value.strip() == value and bool(value) and
          not any(ord(char) < 32 for char in value), "invalid " + name)
    return value


def _keys(value, expected, name):
    _need(type(value) is dict and set(value) == expected, "invalid " + name + " fields")


def _sha(value, name="SHA-256"):
    _need(type(value) is str and SHA.fullmatch(value) is not None, "invalid " + name)
    return value


def relative_path(value):
    """A platform-independent exact identity, not case-folded filesystem lookup."""
    _text(value, "relative path")
    _need("\\" not in value and ":" not in value and not value.startswith("/") and
          all(part not in ("", ".", "..") and part.rstrip(" .") == part
              for part in value.split("/")), "unsafe relative path")
    _need(not any(c in value for c in '<>"|?*'), "unsafe relative path characters")
    reserved = {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)),
                *("LPT" + str(i) for i in range(1, 10))}
    _need(all(part.split(".", 1)[0].upper() not in reserved for part in value.split("/")),
          "reserved device path")
    return value


def _alias(value):
    _need(type(value) is str and ALIAS.fullmatch(value) is not None, "invalid root alias")
    return value


def _utc(value):
    _text(value, "UTC timestamp")
    _need("T" in value, "exact UTC timestamp required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("TETHER catalog policy: invalid timestamp") from error
    _need(result.tzinfo is not None and result.utcoffset().total_seconds() == 0,
          "timestamp must be UTC")
    return result


def _unique_strings(value, name):
    _need(type(value) is list and all(type(v) is str and v.strip() and v.strip() == v for v in value),
          "invalid " + name)
    _need(len(value) == len(set(value)), "duplicate " + name)
    return value


def strict_json(payload):
    _need(type(payload) is bytes and len(payload) <= MAX_POLICY_BYTES, "JSON byte limit/type")
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ContractError("TETHER catalog policy: nonfinite JSON constant")
    try:
        value = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ContractError("TETHER catalog policy: invalid JSON") from error
    _need(type(value) is dict, "JSON object required")
    _json_values(value)
    return value


def _json_values(value):
    if isinstance(value, dict):
        _need(type(value) is dict and all(type(k) is str for k in value), "plain JSON object required")
        for child in value.values():
            _json_values(child)
    elif isinstance(value, list):
        _need(type(value) is list, "plain JSON array required")
        for child in value:
            _json_values(child)
    else:
        _need(type(value) in (str, int, float, bool, type(None)) and
              not (type(value) is float and not math.isfinite(value)), "non-JSON/nonfinite value")


def _acyclic(graph, name):
    active, done = set(), set()
    def visit(key):
        _need(key in graph, "unknown " + name + " reference")
        _need(key not in active, name + " cycle")
        if key in done:
            return
        active.add(key)
        for parent in graph[key]:
            visit(parent)
        active.remove(key)
        done.add(key)
    for key in graph:
        visit(key)


def _legacy_document(policy):
    return {**copy.deepcopy(policy["catalog_metadata"]),
            "datasets": [copy.deepcopy(row["metadata"]) for row in policy["products"]]}


def migrate_catalog(source_bytes, *, source_path, policy_id, created_at_utc):
    """Copy exact schema-one metadata; classify two reviewed genetics edges only."""
    source = strict_json(source_bytes)
    _need(type(source.get("schema_version")) is int and source["schema_version"] == 1,
          "migration requires schema-one source")
    _need(type(source.get("datasets")) is list and type(source.get("providers")) is list,
          "migration requires full catalog")
    rows = []
    for raw in source["datasets"]:
        metadata = copy.deepcopy(raw)
        dependencies = list(raw.get("dependencies", []))
        validation = []
        groups = copy.deepcopy(raw.get("conditional_input_groups", []))
        review = "legacy_carried_forward"
        if raw["dataset_id"] == "genetics_results":
            if "genetics_qc_cases" in dependencies:
                dependencies.remove("genetics_qc_cases")
                validation.append("genetics_qc_cases")
            if "igsr_ld_reference" in dependencies:
                _need(any("igsr_ld_reference" in group.get("dataset_ids", []) for group in groups),
                      "method-conditioned LD group missing")
                dependencies.remove("igsr_ld_reference")
            review = "reviewed_dependency_classification"
        rows.append(dict(dataset_id=raw["dataset_id"], metadata=metadata,
                         input_dependencies=dependencies, validation_dependencies=validation,
                         conditional_input_groups=groups, dependency_review_status=review,
                         agent_use_policy=("denied_evaluator_product" if "evaluation_only" in raw["roles"]
                                           else "requires_artifact_grant")))
    result = dict(schema_version=2, policy_id=policy_id, created_at_utc=created_at_utc,
                  source_catalog=dict(path=source_path, sha256=hashlib.sha256(source_bytes).hexdigest(),
                                      document_fingerprint=fingerprint(source)),
                  catalog_metadata={key: copy.deepcopy(value) for key, value in source.items() if key != "datasets"},
                  products=rows, artifacts=[], uses=[])
    validate_policy(result)
    return result


def artifact_id(record):
    return "artifact-" + fingerprint({key: record[key] for key in IDENTITY_FIELDS})


def validate_source_catalog(policy, source_bytes):
    """Check the actual schema-one anchor, not just an editable fingerprint claim."""
    validated = validate_policy(policy)
    source = strict_json(source_bytes)
    _need(hashlib.sha256(source_bytes).hexdigest() == validated["source_catalog"]["sha256"],
          "source catalog byte anchor differs")
    _need(fingerprint(source) == validated["source_catalog"]["document_fingerprint"] and
          source == _legacy_document(validated), "source catalog metadata anchor differs")
    return copy.deepcopy(source)


def artifact_record(**fields):
    """Construct identity only; validate_policy checks the complete record later."""
    result = copy.deepcopy(fields)
    result["artifact_id"] = artifact_id(result)
    return result


def _proof(value):
    _keys(value, {"path", "sha256"}, "metadata proof")
    relative_path(value["path"])
    _sha(value["sha256"])


def validate_policy(policy):
    """Validate descriptions without granting access or changing any status."""
    _json_values(policy)
    _keys(policy, POLICY_FIELDS, "policy")
    _need(type(policy["schema_version"]) is int and policy["schema_version"] == 2, "unsupported policy schema")
    _text(policy["policy_id"], "policy ID")
    _utc(policy["created_at_utc"])
    source = policy["source_catalog"]
    _keys(source, {"path", "sha256", "document_fingerprint"}, "source catalog")
    relative_path(source["path"]); _sha(source["sha256"]); _sha(source["document_fingerprint"])
    _need(type(policy["catalog_metadata"]) is dict and type(policy["catalog_metadata"].get("schema_version")) is int
          and policy["catalog_metadata"]["schema_version"] == 1
          and "datasets" not in policy["catalog_metadata"], "invalid retained catalog metadata")
    for field in ("products", "artifacts", "uses"):
        _need(type(policy[field]) is list, field + " array required")
    providers = policy["catalog_metadata"].get("providers")
    _need(type(providers) is list and providers, "provider inventory required")
    provider_ids = [p.get("provider_id") for p in providers if type(p) is dict]
    _need(len(provider_ids) == len(providers) and all(type(p) is str and p for p in provider_ids)
          and len(set(provider_ids)) == len(provider_ids), "invalid provider identities")
    products = {}
    for row in policy["products"]:
        _keys(row, PRODUCT_FIELDS, "product")
        key = _text(row["dataset_id"], "dataset ID")
        _need(key not in products, "duplicate dataset ID")
        metadata = row["metadata"]
        _need(type(metadata) is dict and metadata.get("dataset_id") == key and
              metadata.get("provider_id") in provider_ids, "product/source identity differs")
        roles = _unique_strings(metadata.get("roles"), "product roles")
        _need(bool(roles) and set(roles) <= ROLES, "invalid product roles")
        expected = "denied_evaluator_product" if "evaluation_only" in roles else "requires_artifact_grant"
        _need(row["agent_use_policy"] == expected, "legacy evaluator deny changed")
        _need(row["dependency_review_status"] in {"legacy_carried_forward", "reviewed_dependency_classification",
                                                 "reviewed_for_selected_frame"}, "unknown dependency review state")
        for name in ("input_dependencies", "validation_dependencies"):
            _unique_strings(row[name], name)
        _need(not set(row["input_dependencies"]) & set(row["validation_dependencies"]), "dependency classification overlaps")
        _need(type(row["conditional_input_groups"]) is list, "conditional groups must be an array")
        products[key] = row
    _need(bool(products), "empty product inventory")
    _need(fingerprint(_legacy_document(policy)) == source["document_fingerprint"],
          "retained catalog metadata/status changed")
    graph = {}
    for key, row in products.items():
        for name in ("input_dependencies", "validation_dependencies"):
            _need(set(row[name]) <= set(products), "unknown dependency")
        for group in row["conditional_input_groups"]:
            _keys(group, {"requirement", "dataset_ids"}, "conditional group")
            _text(group["requirement"], "conditional requirement")
            _need(bool(_unique_strings(group["dataset_ids"], "conditional IDs")) and
                  set(group["dataset_ids"]) <= set(products), "unknown conditional dependency")
        _need(set(row["metadata"].get("required_component_dataset_ids", [])) <= set(products),
              "unknown component requirement")
        graph[key] = row["input_dependencies"]
    _acyclic(graph, "input dependency")
    if "genetics_results" in products:
        genetics = products["genetics_results"]
        _need("genetics_qc_cases" not in genetics["input_dependencies"] and
              ("genetics_qc_cases" not in products or "genetics_qc_cases" in genetics["validation_dependencies"]),
              "genetics QC must remain a validation dependency")
        _need("igsr_ld_reference" not in genetics["input_dependencies"], "LD must be method-conditional")
    artifacts = {}
    for record in policy["artifacts"]:
        _keys(record, ARTIFACT_FIELDS, "artifact")
        key = record["artifact_id"]
        _need(key == artifact_id(record) and key not in artifacts, "duplicate/conflicting artifact identity")
        _need(record["dataset_id"] in products, "unknown artifact product")
        _text(record["release_id"], "release ID"); _alias(record["root_alias"])
        relative_path(record["relative_path"]); _sha(record["sha256"])
        _need(type(record["bytes"]) is int and record["bytes"] >= 0, "invalid artifact byte count")
        _need(record["kind"] in {"raw", "derived", "packet"}, "invalid artifact kind")
        _unique_strings(record["parents"], "artifact parents")
        _need((record["kind"] == "raw") == (not record["parents"]), "raw/derived parents disagree")
        _need(record["temporal_classification"] in TEMPORAL, "unknown temporal classification")
        if record["availability"] is not None:
            decode(Availability, record["availability"])
        _need(record["source_url"] is None or type(record["source_url"]) is str, "invalid source URL type")
        _text(record["scope"], "artifact scope")
        _need(record["scientific_validation"] == "not_established", "Q02 cannot promote scientific validation")
        proof = record["provenance"]
        _keys(proof, {"kind", "evidence", "receipt"}, "provenance")
        _need(proof["kind"] in {"download_receipt", "generated", "manual_archive"}, "unknown provenance kind")
        _need(record["source_url"] is not None or proof["kind"] == "manual_archive",
              "only blocked manual archives may have an unknown source URL")
        _need(type(proof["evidence"]) is list and proof["evidence"], "retained provenance evidence required")
        for ref in proof["evidence"]:
            _proof(ref)
        receipt = proof["receipt"]
        if proof["kind"] == "download_receipt":
            _need(record["kind"] == "raw", "download receipt cannot prove generated artifact")
            _keys(receipt, {"root_alias", "relative_path", "sha256", "receipt_id", "url"}, "receipt reference")
            _alias(receipt["root_alias"]); relative_path(receipt["relative_path"]); _sha(receipt["sha256"])
            _text(receipt["receipt_id"], "receipt ID"); _text(receipt["url"], "receipt URL")
            _need(receipt["url"] == record["source_url"], "receipt/source URL differs")
        else:
            _need(receipt is None, "nontransport provenance cannot invent a receipt")
            _need((proof["kind"] == "manual_archive") == (record["kind"] == "raw"), "provenance/kind mismatch")
        artifacts[key] = record
    _acyclic({key: value["parents"] for key, value in artifacts.items()}, "artifact ancestry")
    uses = set()
    for use in policy["uses"]:
        _keys(use, USE_FIELDS, "use")
        _text(use["use_id"], "use ID")
        _need(use["use_id"] not in uses, "duplicate use ID"); uses.add(use["use_id"])
        _need(use["kind"] in USE_KINDS and use["status"] in {"allowed", "blocked"}, "unknown use disposition")
        _need(use["profile"] in PROFILES, "unknown use profile")
        _utc(use["origin_at"]); _alias(use["raw_root_alias"]); _alias(use["snapshot_root_alias"])
        _need(use["raw_root_alias"] != use["snapshot_root_alias"], "raw/snapshot roots require distinct aliases")
        _unique_strings(use["blockers"], "use blockers")
        _need((use["status"] == "blocked") == bool(use["blockers"]), "use disposition/blockers disagree")
        for field in ("frame_sha256", "case_fingerprint", "snapshot_fingerprint"):
            if use[field] is not None:
                _sha(use[field], field)
            else:
                _need(use["status"] == "blocked", "allowed use requires exact bindings")
        _need(type(use["grants"]) is list, "use grants array required")
        seen = set()
        for grant in use["grants"]:
            _keys(grant, {"artifact_id", "role"}, "artifact grant")
            key = grant["artifact_id"]
            _need(key in artifacts and key not in seen and grant["role"] in ROLES, "unknown/duplicate artifact grant")
            seen.add(key)
            if use["status"] == "allowed":
                product = products[artifacts[key]["dataset_id"]]
                _need(grant["role"] in {"agent_evidence", "reference"} and
                      grant["role"] in product["metadata"]["roles"] and
                      product["agent_use_policy"] != "denied_evaluator_product", "evaluator/unsupported grant")
                _need(product["dependency_review_status"] == "reviewed_for_selected_frame",
                      "selected product requirements not reviewed for frame")
                _need(artifacts[key]["provenance"]["kind"] != "manual_archive", "manual archives remain unqualified for inference")
        if use["status"] == "allowed":
            _need(bool(seen) and use["kind"] not in {"endpoint_evaluation", "ascertainment_evaluation"},
                  "evaluation or empty use cannot authorize inference")
            _need(all(set(artifacts[key]["parents"]) <= seen for key in seen), "grant omits actual ancestors")
    return copy.deepcopy(policy)


def _absolute_root(value):
    _text(value, "absolute root")
    is_windows = bool(re.match(r"^[A-Za-z]:[\\/]", value))
    path = PureWindowsPath(value) if is_windows else PurePosixPath(value)
    _need(path.is_absolute() and ".." not in path.parts, "absolute nontraversing root required")
    return path


def authorize_snapshot(policy, snapshot, *, case, use_id, root_aliases):
    """Bind all supplied metadata to one declared use; no filesystem operations.

    The caller MUST compare binding.frame_sha256 with its independently selected
    frame, verify physical roots and bytes, copy controls and verify this binding
    again during finalization/replay. Legacy temporal parsing remains mandatory.
    """
    policy = validate_policy(policy)
    _json_values(snapshot); _json_values(case)
    _need(type(snapshot) is dict and type(case) is dict and
          type(snapshot.get("schema_version")) is int and snapshot["schema_version"] == 2 and
          type(case.get("schema_version")) is int and case["schema_version"] == 2, "v2 case/snapshot required")
    matches = [use for use in policy["uses"] if use["use_id"] == use_id]
    _need(len(matches) == 1 and matches[0]["status"] == "allowed", "use is missing or blocked")
    use = matches[0]
    _need(fingerprint(case) == use["case_fingerprint"] and fingerprint(snapshot) == use["snapshot_fingerprint"],
          "case/snapshot fingerprint differs")
    _need(snapshot.get("profile") == use["profile"] and snapshot.get("origin_at") == use["origin_at"] and
          case.get("origin_at") == use["origin_at"] and snapshot.get("origin") == case.get("origin") ==
          _utc(use["origin_at"]).date().isoformat(), "use profile/origin differs")
    _need(type(root_aliases) is dict, "explicit root aliases required")
    roots = {}
    for alias, value in root_aliases.items():
        _alias(alias); roots[alias] = _absolute_root(value)
    _need(len({str(p).replace("\\", "/").casefold() for p in roots.values()}) == len(roots), "root alias collision")
    _need(use["raw_root_alias"] in roots and use["snapshot_root_alias"] in roots, "selected root alias missing")
    _need(str(_absolute_root(snapshot.get("raw_root"))) == str(roots[use["raw_root_alias"]]), "raw root differs")
    products = {row["dataset_id"]: row for row in policy["products"]}
    records = {row["artifact_id"]: row for row in policy["artifacts"]}
    grants = {row["artifact_id"]: row["role"] for row in use["grants"]}
    identities = {(r["dataset_id"], r["release_id"], r["root_alias"], r["relative_path"], r["sha256"]): r
                  for r in records.values()}
    _need(len(identities) == len(records), "ambiguous artifact identity/size")
    supplied, by_id = [], {}
    for category, field, identifier in (("source", "sources", "source_id"), ("packet", "artifacts", "artifact_id")):
        values = snapshot.get(field)
        _need(type(values) is list, "snapshot inventory must be arrays")
        for node in values:
            _need(type(node) is dict, "invalid inventory node")
            key = _text(node.get(identifier), "snapshot node ID")
            _need(key not in by_id, "duplicate supplied node ID")
            is_raw = category == "source" and node.get("computed_at") is None
            alias = use["raw_root_alias"] if is_raw else use["snapshot_root_alias"]
            relative = relative_path(node.get("path"))
            identity = (node.get("dataset_id"), node.get("release_id"), alias, relative, node.get("sha256"))
            record = identities.get(identity)
            _need(record is not None, "undeclared source/artifact identity")
            global_id = record["artifact_id"]
            role = node.get("role")
            _need(global_id in grants and grants[global_id] == role, "source/artifact role differs from selected grant")
            _need(role in {"agent_evidence", "reference"}, "evaluator/unsupported actual input")
            _need(products[node["dataset_id"]]["agent_use_policy"] != "denied_evaluator_product", "evaluator product input")
            _need(node["dataset_id"] != "scorer_artifacts", "training lineage policy not implemented")
            expected_kind = "raw" if is_raw else "derived" if category == "source" else "packet"
            _need(record["kind"] == expected_kind, "artifact kind differs")
            if category == "packet":
                _need(role == "agent_evidence" and node.get("access_approved") is True, "packet access not approved")
            _need(node.get("availability") == record["availability"] and
                  node.get("temporal_classification") == record["temporal_classification"] and
                  node.get("source_url") == record["source_url"], "availability/source context differs")
            if is_raw:
                _need(record["availability"] is not None, "raw availability missing")
                availability = decode(Availability, record["availability"])
                _need(availability.exclusion(_utc(use["origin_at"])) is None, "raw information unavailable at origin")
                classification = record["temporal_classification"]
                if use["profile"] == "historical_benchmark":
                    _need(classification == "verified_historical" or
                          (classification == "reconstructed" and snapshot.get("allow_reconstructed") is True),
                          "historical information not qualified")
                else:
                    _need(classification != "unverified", "temporal classification unverified")
                receipt = record["provenance"]["receipt"]
                _need(receipt is not None and receipt["root_alias"] == use["raw_root_alias"] and
                      node.get("receipt_path") == receipt["relative_path"] and
                      node.get("receipt_sha256") == receipt["sha256"], "raw receipt binding differs")
            parents = node.get("parents", []) if category == "source" else node.get("input_refs", [])
            _unique_strings(parents, "supplied parent IDs")
            entry = dict(source_id=key, artifact_id=global_id, category=category, role=role,
                         dataset_id=record["dataset_id"], release_id=record["release_id"], root_alias=alias,
                         relative_path=relative, physical_path=str(roots[alias].joinpath(*relative.split("/"))),
                         sha256=record["sha256"], bytes=record["bytes"], parents=list(parents),
                         receipt=copy.deepcopy(record["provenance"]["receipt"]))
            supplied.append(entry); by_id[key] = entry
    _need(supplied and len({row["artifact_id"] for row in supplied}) == len(supplied), "empty/aliased supplied inventory")
    _need({row["artifact_id"] for row in supplied} == set(grants), "selected grant/inventory mismatch")
    for entry in supplied:
        _need(set(entry["parents"]) <= set(by_id), "missing actual parent")
        _need(all(by_id[parent]["category"] == "source" for parent in entry["parents"]), "packet cannot be an input node")
        actual = {by_id[parent]["artifact_id"] for parent in entry["parents"]}
        _need(actual == set(records[entry["artifact_id"]]["parents"]), "actual parent edges differ")
        entry["parent_artifact_ids"] = sorted(actual)
    _acyclic({row["source_id"]: row["parents"] for row in supplied}, "actual input")
    projection = _legacy_document(policy)
    permitted = {}
    for entry in supplied:
        permitted.setdefault(entry["dataset_id"], set()).add(entry["role"])
    for product in projection["datasets"]:
        product["roles"] = sorted(permitted.get(product["dataset_id"], {"evaluation_only"}))
    binding = dict(schema_version=1, method="tether.catalog_policy_binding.v1", policy_id=policy["policy_id"],
                   policy_fingerprint=fingerprint(policy), source_catalog=copy.deepcopy(policy["source_catalog"]),
                   use_id=use_id, frame_sha256=use["frame_sha256"], profile=use["profile"], origin_at=use["origin_at"],
                   case_fingerprint=fingerprint(case), snapshot_fingerprint=fingerprint(snapshot),
                   root_aliases=copy.deepcopy(root_aliases), projection_fingerprint=fingerprint(projection),
                   inventory=supplied, scientific_validation="not_established")
    return dict(projection=projection, binding=binding)


def reconcile_receipt(queue_record, receipt, *, observed_size, observed_sha256):
    """Check exact transport identity; never promote catalog/scientific status."""
    _need(type(queue_record) is dict and type(receipt) is dict, "receipt/queue must be objects")
    for field in ("receipt_id", "dataset_id", "release_id", "url"):
        _text(queue_record.get(field), "queue " + field)
        _need(receipt.get(field) == queue_record[field], "receipt " + field + " differs")
    # Earlier Windows transport receipts retained backslashes. Separators are
    # equivalent path syntax; case, URL characters and IDs are still exact.
    # Validate both spellings before comparing; never resolve '..' away.
    queue_path = _text(queue_record.get("relative_path"), "queue relative_path")
    receipt_path = _text(receipt.get("relative_path"), "receipt relative_path")
    _need(relative_path(queue_path.replace("\\", "/")) == relative_path(receipt_path.replace("\\", "/")),
          "receipt relative_path differs")
    _need(receipt.get("status") == "completed", "receipt not completed")
    _need(type(observed_size) is int and observed_size >= 0 and type(receipt.get("bytes")) is int and
          receipt["bytes"] == observed_size, "receipt size differs")
    _sha(observed_sha256); _sha(receipt.get("sha256"))
    _need(receipt["sha256"] == observed_sha256, "receipt payload hash differs")
    _utc(receipt.get("completed_at_utc"))
    expected = queue_record.get("expected_sha256")
    if expected is not None:
        _sha(expected); _need(expected == observed_sha256, "expected source hash differs")
    return dict(status="transport_identity_consistent", dataset_id=queue_record["dataset_id"],
                release_id=queue_record["release_id"], receipt_id=queue_record["receipt_id"],
                sha256=observed_sha256, bytes=observed_size, scientific_validation="not_established",
                scope="Caller-supplied observed size/hash checked against exact queue and receipt; no file was opened")
