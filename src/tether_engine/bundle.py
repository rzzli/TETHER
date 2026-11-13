"""Relocatable, content-addressed export of one offline evidence run."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace

from typing import Any

from .agents import ExtractiveBackend, Usage
from .artifacts import ADMISSION_POLICY, DOSSIER_FORMAT, RUN_FILES, dossier_for_format
from .atomic import publish_bytes
from .bundle_files import checked_output, checked_root, logical_parts, read_local
from .chrono import admit_snapshot, required_source_proofs
from .contracts import Case, Category, Claim, EvidencePacket, EvidenceStatus, Profile, Snapshot
from .derivations import registry_entry
from .features import FeatureVector
from .journal import read_chain
from .provenance import check_receipt_availability
from .scorer import Prediction, ScorerArtifact
from .semantics import check_execution, check_semantics
from .serde import ContractError, canonical, decode, fingerprint, parse_json
from .workflow import Budget, PlanStep, RunResult


FORMAT = "tether.portable_bundle.v1"
MANIFEST_LIMIT = 1024 * 1024
OBJECT_LIMIT = 64 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
OBJECT_COUNT = 256
RUN_OBJECTS = frozenset(RUN_FILES) - {"journal.jsonl"}
PREFIXES = ("packets/", "lineage/", "originals/")


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _ordered_json(value):
    # The logical fingerprint is canonical, while dossier display order can
    # depend on the producer's insertion order in nested mappings.
    return (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _object(payload):
    try:
        value = decode(Any, parse_json(payload), "bundle JSON")
    except (RecursionError, UnicodeError, ValueError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("Malformed or excessively nested bundle JSON") from error
    _need(type(value) is dict, "Expected a bundle JSON object")
    return value


def _exact(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys.split()), f"Invalid {label} fields")


def _cas(digest):
    return Path("objects", "sha256", digest)


def _manifest(payload):
    value = _object(payload)
    _exact(value, "format admission_policy source_tier producer objects", "bundle manifest")
    _need(value["format"] == FORMAT, "Unsupported bundle format")
    _need(type(value["admission_policy"]) is str and 0 < len(value["admission_policy"]) <= 128,
          "Invalid bundle admission policy")
    _need(value["source_tier"] in ("included", "receipts_only"), "Invalid bundle source tier")
    producer = value["producer"]
    _exact(producer, "software_version receipt_sha256 input_fingerprint code environment", "producer metadata")
    _need(type(producer["software_version"]) is str and _digest(producer["receipt_sha256"])
          and _digest(producer["input_fingerprint"]), "Invalid producer version or digest")
    _exact(producer["environment"], "python platform runtime_dependencies", "producer environment")
    code = producer["code"]
    _need(type(code) is dict and 0 < len(code) <= 512, "Invalid producer code inventory")
    for name, digest in code.items():
        logical_parts(name)
        _need(name.endswith(".py") and _digest(digest), "Invalid producer code proof")
    inventory = value["objects"]
    _need(type(inventory) is dict and RUN_OBJECTS <= inventory.keys() and len(inventory) <= OBJECT_COUNT,
          "Incomplete or oversized bundle object inventory")
    _need(len({name.casefold() for name in inventory}) == len(inventory), "Aliased bundle object names")
    sizes = {}
    for name, item in inventory.items():
        logical_parts(name)
        _need(name in RUN_OBJECTS or name.startswith(PREFIXES), "Unexpected logical bundle object")
        _exact(item, "sha256 bytes", "bundle object")
        digest, count = item["sha256"], item["bytes"]
        _need(_digest(digest) and type(count) is int and 0 <= count <= OBJECT_LIMIT,
              "Invalid bundle object size or digest")
        _need(sizes.setdefault(digest, count) == count, "Conflicting sizes for the same bundle digest")
    # Bound logical expansion as well as the deduplicated physical inventory.
    _need(sum(item["bytes"] for item in inventory.values()) <= TOTAL_LIMIT, "Bundle exceeds 256 MiB total")
    return value


def _inputs(payload):
    value = _object(payload)
    _exact(value, "case snapshot scorer catalog_policy configuration", "portable inputs")
    case = decode(Case, value["case"], "portable case")
    case.validate()
    snapshot = decode(Snapshot, value["snapshot"], "portable snapshot")
    _need(snapshot.schema_version == 2 and snapshot.raw_root is None and not snapshot.allow_reconstructed
          and snapshot.profile in (Profile.DEMO, Profile.CONTEMPORARY), "Unsupported portable snapshot profile/root")
    _need(snapshot.profile == Profile.DEMO or (case.task == "T6" and case.program is None
          and case.endpoint is None and value["scorer"] is None), "Real bundles require unscored T6 without a program")
    _need(type(value["configuration"]) is dict and
          value["configuration"].get("backend_id") == ExtractiveBackend.backend_id and
          value["configuration"].get("backend_provenance") is None, "Bundle requires the offline extractive workflow")
    policy = value["catalog_policy"]
    if snapshot.profile != Profile.DEMO:
        _need(type(policy) is dict and type(policy.get("datasets")) is list and
              all(type(row) is dict and type(row.get("dataset_id")) is str and
                  type(row.get("roles")) is list and all(type(role) is str for role in row["roles"])
                  for row in policy["datasets"]), "Invalid portable catalog policy")
    for item in snapshot.artifacts:
        logical_parts(item.path)
    for item in snapshot.sources:
        logical_parts(item.path)
        if item.receipt_path is not None:
            logical_parts(item.receipt_path)
    _need(len(snapshot.sources) + len(snapshot.artifacts) <= OBJECT_COUNT,
          "Too many portable artifact or lineage declarations")
    return value, case, snapshot


def _slot_paths(snapshot, proofs, snapshot_root, original_root, source_tier):
    # Computed nodes live with packets; raw demo inputs can share that directory
    # in native runs, but use the originals namespace in the portable export.
    nodes = {node.source_id: node for node in snapshot.sources}
    artifacts = {artifact.artifact_id: artifact for artifact in snapshot.artifacts}
    result = {}

    def add(key, path, digest):
        logical_parts(key)
        _need(_digest(digest) and result.get(key, (path, digest)) == (path, digest),
              "Conflicting logical source proof")
        result[key] = (path, digest)

    for proof in proofs:
        key = proof["artifact_id"]
        node = nodes.get(key)
        # Use declared lexical paths, so native resolution cannot hide links
        # before the no-follow reader receives the original components.
        if node is None or node.computed_at is not None:
            path = (artifacts[key] if node is None else node).path
            add("packets/" + path, snapshot_root.joinpath(*logical_parts(path)), proof["sha256"])
        elif source_tier == "included":
            add("originals/" + node.path, original_root.joinpath(*logical_parts(node.path)), proof["sha256"])
        if "receipt_path" in proof:
            add("lineage/" + node.receipt_path, original_root.joinpath(*logical_parts(node.receipt_path)),
                proof["receipt_sha256"])
    return result


def _coverage(run, store, case):
    _need(fingerprint(run["exclusions"]) == fingerprint(store.exclusions), "Portable exclusions differ from sources")
    for category in Category:
        records = store.query(case, category)
        observed = sum(item.observation.status == EvidenceStatus.OBSERVED for item in records)
        nonobserved = [{"observation_id": item.observation.observation_id,
                        "status": item.observation.status.value, "reason": item.observation.statement}
                       for item in records if item.observation.status != EvidenceStatus.OBSERVED]
        row = run["coverage"][category.value]
        _need(row["available_observations"] == observed and
              fingerprint(row["nonobserved"]) == fingerprint(nonobserved) and
              fingerprint(row["source_coverage"]) == fingerprint(store.snapshot.coverage),
              "Portable coverage differs from sources")


def _receipt_relative(value):
    _need(type(value) is str, "Portable download witness requires a relative path")
    return "/".join(logical_parts(value.replace("\\", "/")))


def _methods_supported(recipes):
    for recipe in recipes:
        if recipe is not None:
            try:
                registry_entry(recipe.method_id, recipe.method_version)
            except ContractError:
                return False
    return True


def _replay(payloads, manifest, expected_admitted=None):
    if manifest["admission_policy"] != ADMISSION_POLICY:
        return "unavailable_unknown_policy", "unavailable_unknown_policy"
    inputs, case, snapshot = _inputs(payloads["inputs.json"])
    config, policy = inputs["configuration"], inputs["catalog_policy"]
    run = _object(payloads["run.json"])
    _need(run.get("input_fingerprint") == fingerprint(inputs) and run.get("admission_policy") == ADMISSION_POLICY,
          "Portable run input/policy mismatch")
    _need(run.get("software_version") == manifest["producer"]["software_version"], "Portable producer version mismatch")
    _need(run.get("dossier_format") == DOSSIER_FORMAT, "Portable runs require the safe dossier format")
    packet_names = {"packets/" + artifact.path for artifact in snapshot.artifacts}
    packets = [decode(EvidencePacket, _object(payload), name) for name, payload in payloads.items()
               if name in packet_names]
    _need(all(packet.schema_version == 2 for packet in packets), "Unsupported portable packet version")
    observations = [item for packet in packets for item in packet.observations]
    _need(all(item.source_kind != "clinical" and item.category != Category.CLINICAL
              for item in observations) or snapshot.profile == Profile.DEMO,
          "Clinical evidence is outside the real portable workflow")
    recipes = [item.derivation for item in (*snapshot.sources, *observations)]
    if not _methods_supported(recipes):
        return "unavailable_unknown_method", "unavailable_unknown_method"
    with tempfile.TemporaryDirectory(prefix="tether-bundle-") as folder:
        base = Path(folder).resolve()
        snapshots, originals = base / "normalized", base / "originals"
        snapshots.mkdir()
        originals.mkdir()
        snapshot = replace(snapshot, raw_root=str(originals))
        proofs = required_source_proofs(snapshot, case, snapshots, policy)
        slots = _slot_paths(snapshot, proofs, snapshots, originals, manifest["source_tier"])
        _need(set(payloads) == RUN_OBJECTS | slots.keys(), "Portable source inventory differs from eligible closure")
        checked_source_ids = {item["artifact_id"] for item in proofs if "receipt_path" in item}
        for node in snapshot.sources:
            if node.source_id not in checked_source_ids:
                continue
            witness = _object(payloads["lineage/" + node.receipt_path])
            _need(witness.get("status") == "completed" and witness.get("sha256") == node.sha256 and
                  witness.get("dataset_id") == node.dataset_id and witness.get("release_id") == node.release_id and
                  _receipt_relative(witness.get("relative_path")) == node.path and
                  type(witness.get("bytes")) is int and
                  witness["bytes"] >= 0, "Portable download witness identity differs from its source")
            check_receipt_availability(node, witness)
        for key, (path, digest) in slots.items():
            _need(manifest["objects"][key]["sha256"] == digest, "Portable lineage digest mismatch")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(payloads[key])
        if manifest["source_tier"] == "receipts_only":
            return "unavailable_raw_originals_omitted", "unavailable_raw_originals_omitted"
        trace_path = base / "trace.jsonl"
        trace_path.write_bytes(payloads["trace.jsonl"])
        trace = read_chain(trace_path)
        ledger = _object(payloads["ledger.json"])
        _exact(ledger, "schema_version claims", "portable ledger")
        _need(type(ledger["schema_version"]) is int and ledger["schema_version"] == 2, "Invalid portable ledger version")
        claims = decode(tuple[Claim, ...], ledger["claims"])
        features = decode(FeatureVector, _object(payloads["features.json"]))
        prediction = decode(Prediction, _object(payloads["prediction.json"]))
        scorer = decode(ScorerArtifact, inputs["scorer"]) if inputs["scorer"] is not None else None
        store = admit_snapshot(snapshot, case, snapshots, policy)
        if expected_admitted is not None:
            _need(fingerprint(expected_admitted) == fingerprint(store.admitted_fingerprints),
                  "Native admitted fingerprints differ from portable sources")
        _coverage(run, store, case)
        check_execution(run, case, snapshot, config, claims, trace)
        check_semantics(case, snapshot, claims, features, prediction, run["coverage"], config,
                        run["status"], scorer, store.admitted_fingerprints, policy, snapshots, trace)
        result = RunResult(case, run["snapshot_id"], run["profile"], run["backend_id"], run["status"],
                           decode(Budget, run["budget"]), run["calls"], decode(Usage, run["usage"]),
                           decode(tuple[PlanStep, ...], run["plan"]), run["coverage"], claims, features,
                           prediction, trace, decode(Usage, run["measured_usage"]),
                           decode(Usage, run["estimated_usage"]), config)
        prose = dossier_for_format(result, SimpleNamespace(snapshot=snapshot, exclusions=store.exclusions),
                                  run["dossier_format"]).encode("utf-8")
        _need(payloads["dossier.md"] in (prose, prose.replace(b"\n", b"\r\n")), "Portable dossier rendering mismatch")
    derivations = "verified_registered_methods" if any(recipes) else "not_applicable_no_registered_derivation"
    return "verified", derivations


def _read_bundle(root, expected, *, objects, replay=True):
    payload = read_local(root / "bundle.json", MANIFEST_LIMIT)
    digest = _sha(payload)
    _need(expected is None or (_digest(expected) and expected == digest), "Bundle manifest anchor mismatch")
    manifest = _manifest(payload)
    result = dict(format=FORMAT, manifest_sha256=digest, source_tier=manifest["source_tier"],
                  objects=len(manifest["objects"]), producer_receipt_sha256=manifest["producer"]["receipt_sha256"],
                  logical_bytes=sum(item["bytes"] for item in manifest["objects"].values()),
                  external_anchor="matched" if expected is not None else "not_supplied",
                  external_authenticity="not_established", scientific_validation="not_established")
    if not objects:
        return result | {"status": "manifest_inspected", "byte_integrity": "not_checked"}
    contents, payloads = {}, {}
    for name, item in manifest["objects"].items():
        key, size = item["sha256"], item["bytes"]
        if key not in contents:
            blob = read_local(root / _cas(key), size)
            _need(len(blob) == size and _sha(blob) == key, f"Bundle object integrity failure: {name}")
            contents[key] = blob
        payloads[name] = contents[key]
    try:
        source, derivations = (_replay(payloads, manifest) if replay else ("not_checked_bytes_only",) * 2)
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError, UnicodeError) as error:
        raise ContractError("Malformed portable run, source or policy data") from error
    return result | dict(status="integrity_verified", byte_integrity="verified", physical_objects=len(contents),
                         source_inclusive_consistency=source, supported_derivation_replay=derivations,
                         exact_producer_replay="not_performed_portable_export")


def inspect_bundle(root: Path, expected_manifest_sha256: str | None = None) -> dict:
    return _read_bundle(Path(root), expected_manifest_sha256, objects=False)


def verify_bundle(root: Path, expected_manifest_sha256: str | None = None, *, replay=True) -> dict:
    return _read_bundle(Path(root), expected_manifest_sha256, objects=True, replay=replay)


def export_bundle(run_dir: Path, output: Path, *, source_roots=(), receipt_sha256=None,
                  include_originals=True) -> dict:
    """Preflight a sealed native run and copy only its explicitly permitted closure."""
    run_dir = checked_root(run_dir)
    output = checked_output(output, (run_dir,))
    receipt_payload = read_local(run_dir / "receipt.json", MANIFEST_LIMIT)
    receipt_digest = _sha(receipt_payload)
    _need(receipt_sha256 is None or (_digest(receipt_sha256) and receipt_sha256 == receipt_digest),
          "Original run receipt anchor mismatch")
    receipt = _object(receipt_payload)
    _need(type(receipt.get("schema_version")) is int and receipt["schema_version"] == 2 and
          receipt.get("admission_policy") == ADMISSION_POLICY, "Export requires a current-policy native v2 run")
    outputs = receipt.get("outputs")
    _need(type(outputs) is dict and set(outputs) == set(RUN_FILES) and all(_digest(v) for v in outputs.values()),
          "Invalid native run output inventory")
    payloads = {}
    for name, digest in outputs.items():
        payload = read_local(run_dir / name, OBJECT_LIMIT)
        _need(_sha(payload) == digest, f"Native run output integrity failure: {name}")
        payloads[name] = payload
        _need(sum(map(len, payloads.values())) <= TOTAL_LIMIT, "Native run exceeds portable byte limit")
    _need(payloads.pop("journal.jsonl") == payloads["trace.jsonl"], "Native journal differs from finalized trace")
    original = _object(payloads["inputs.json"])
    _exact(original, "case snapshot scorer catalog_policy configuration snapshot_base environment", "native inputs")
    _need(receipt.get("input_fingerprint") == fingerprint(original), "Native input fingerprint mismatch")
    _need(type(original["snapshot_base"]) is str and type(original["snapshot"]) is dict,
          "Invalid native snapshot location")
    base = Path(original["snapshot_base"])
    raw_base = original["snapshot"].get("raw_root")
    _need(raw_base is None or type(raw_base) is str, "Invalid native original location")
    raw = Path(raw_base) if raw_base else base
    allowed = tuple(checked_root(root) for root in source_roots)
    for root in (base, raw):
        _need(root.is_absolute() and any(root.is_relative_to(parent) for parent in allowed),
              "Explicit --source-root authorization is required for both original roots")
    base, raw = checked_root(base), checked_root(raw)
    checked_output(output, (run_dir, base, raw, *allowed))
    portable = {key: value for key, value in original.items() if key not in ("environment", "snapshot_base")}
    portable["snapshot"] = portable["snapshot"] | {"raw_root": None}
    payloads["inputs.json"] = _ordered_json(portable)
    _, case, snapshot = _inputs(payloads["inputs.json"])
    snapshot = replace(snapshot, raw_root=str(raw))
    proofs = required_source_proofs(snapshot, case, base, portable["catalog_policy"])
    source_proofs = receipt.get("sources")
    _need(type(source_proofs) is list and all(type(p) is dict and type(p.get("artifact_id")) is str for p in source_proofs),
          "Invalid native source proof inventory")
    indexed = {item["artifact_id"]: item for item in source_proofs}
    _need(len(indexed) == len(source_proofs) and
          fingerprint(indexed) == fingerprint({item["artifact_id"]: item for item in proofs}),
          "Native source proofs differ from eligible closure")
    source_tier = "included" if include_originals else "receipts_only"
    for name, (path, digest) in _slot_paths(snapshot, proofs, base, raw, source_tier).items():
        _need(any(path.is_relative_to(root) for root in allowed), "Native proof escapes the authorized roots")
        remaining = TOTAL_LIMIT - sum(map(len, payloads.values()))
        payload = read_local(path, min(OBJECT_LIMIT, remaining))
        _need(_sha(payload) == digest, f"Native source proof mismatch: {name}")
        payloads[name] = payload
    run = _object(payloads["run.json"])
    _need(run.get("input_fingerprint") == receipt["input_fingerprint"], "Native run input fingerprint mismatch")
    run["input_fingerprint"] = fingerprint(portable)
    payloads["run.json"] = _ordered_json(run)
    environment = original["environment"]
    _need(type(environment) is dict and all(key in environment for key in ("python", "platform", "runtime_dependencies")),
          "Invalid native producer environment")
    manifest = dict(format=FORMAT, admission_policy=receipt["admission_policy"], source_tier=source_tier,
                    producer=dict(software_version=receipt.get("software_version"), receipt_sha256=receipt_digest,
                                  input_fingerprint=receipt["input_fingerprint"], code=receipt.get("code"),
                                  environment={key: environment[key] for key in ("python", "platform", "runtime_dependencies")}),
                    objects={name: {"sha256": _sha(payload), "bytes": len(payload)} for name, payload in payloads.items()})
    body = canonical(manifest)
    _need(len(body) <= MANIFEST_LIMIT, "Portable bundle manifest exceeds its byte bound")
    _manifest(body)
    admitted = receipt.get("admitted_fingerprints")
    _need(type(admitted) is dict and all(_digest(value) for value in admitted.values()),
          "Invalid native admission fingerprints")
    source, _ = _replay(payloads, manifest, admitted)
    _need(source == ("verified" if include_originals else "unavailable_raw_originals_omitted"),
          "Native run is outside the supported portable replay scope")
    # Reserve only after successful preflight. The manifest is the commit marker.
    checked_output(output, (run_dir, base, raw, *allowed))
    output.mkdir(parents=True, exist_ok=False)
    (output / "objects" / "sha256").mkdir(parents=True)
    emitted = set()
    for name, payload in payloads.items():
        digest = manifest["objects"][name]["sha256"]
        if digest not in emitted:
            with (output / _cas(digest)).open("xb") as stream:
                stream.write(payload)
            emitted.add(digest)
    publish_bytes(output / "bundle.json", body)
    return {"output": str(output), **verify_bundle(output, _sha(body)), "status": "bundle_exported"}


def automatic_output() -> Path:
    return Path("tether-bundle-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
