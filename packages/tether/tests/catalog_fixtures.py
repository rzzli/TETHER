"""Invented policy contracts and receipts; no TestCase or external sources."""
import copy
import hashlib
import json
from pathlib import Path

from tether_engine.serde import canonical, fingerprint
from tether_engine.derivations import registry_entry
from tether import _catalog_policy as policy, _catalog_binding as binding

ROOT = Path(__file__).resolve().parents[3]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical(value) + b"\n")


def make_fixture(root):
    """Complete synthetic engine contracts plus exact policy grants and receipts."""
    root = Path(root).absolute()
    normalized, raw_root = root / "normalized", root / "raw"
    normalized.mkdir(); raw_root.mkdir()
    base = ROOT / "src/tether_engine/demo/v2"
    case = json.loads((base / "case.json").read_text())
    snapshot = json.loads((base / "snapshot.json").read_text())
    snapshot["profile"] = "contemporary_assessment"
    snapshot["sources"] = snapshot["sources"][:1]
    snapshot["artifacts"] = snapshot["artifacts"][:1]
    snapshot["raw_root"] = str(raw_root)
    raw = (base / "raw-inputs.json").read_bytes()
    node = snapshot["sources"][0]
    node["path"] = "originals/raw-inputs.json"
    write(raw_root / node["path"], raw)
    receipt = dict(receipt_id="fictional-original", dataset_id=node["dataset_id"], release_id=node["release_id"],
                   relative_path=node["path"].replace("/", "\\"), sha256=node["sha256"], bytes=len(raw), url=node["source_url"],
                   status="completed", completed_at_utc="2022-01-01T00:00:00+00:00")
    receipt_bytes = canonical(receipt) + b"\n"
    node.update(receipt_path="receipt-archive/original.json", receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest())
    write(raw_root / node["receipt_path"], receipt_bytes)
    # A registered identity projection keeps the derived-reference fixture
    # complete without introducing unverified normalization behavior.
    mapping_bytes = canonical(json.loads(raw)) + b"\n"
    registered = registry_entry()
    parameters = dict(input=node["source_id"], pointer="")
    derivation = dict(schema_version=1, method_id=registered["method_id"],
        method_version=registered["method_version"], implementation_sha256=registered["implementation_sha256"],
        parameters_sha256=fingerprint(parameters), parameters=parameters, inputs={node["source_id"]: node["sha256"]},
        assets={}, output_schema="canonical_json.v1", method_available_at=registered["method_available_at"],
        mode="contemporary_method_retrospective")
    mapping = dict(source_id="fictional-mapping", dataset_id="synthetic_reference", release_id="fixture-v1",
        path="references/mapping.json", sha256=hashlib.sha256(mapping_bytes).hexdigest(), role="reference",
        availability=copy.deepcopy(node["availability"]), temporal_classification=node["temporal_classification"],
        source_url="https://example.invalid/mapping", parents=[node["source_id"]],
        computed_at="2030-01-01T00:00:00+00:00", method_id=registered["method_id"],
        method_version=registered["method_version"], derivation=derivation)
    snapshot["sources"].append(mapping)
    write(normalized / mapping["path"], mapping_bytes)
    artifact = snapshot["artifacts"][0]
    artifact.update(path="packets/evidence.json", input_refs=[mapping["source_id"]])
    write(normalized / artifact["path"], (base / "evidence.json").read_bytes())
    source_bytes = canonical(dict(schema_version=1, providers=[dict(provider_id="fictional")], datasets=[
        dict(dataset_id=key, provider_id="fictional", roles=roles, dependencies=[], collection_status="planned",
             parse_status="not_run", validation_status="not_run")
        for key, roles in (("synthetic_fixture", ["agent_evidence"]), ("synthetic_reference", ["reference"]),
                           ("fictional_answers", ["evaluation_only", "reference"]))]))
    document = policy.migrate_catalog(source_bytes, source_path="data/catalog/sources.json",
                                      policy_id="fictional-policy", created_at_utc="2026-11-02T00:00:00Z")
    for product in document["products"][:2]:
        product["dependency_review_status"] = "reviewed_for_selected_frame"
    records, by_node = [], {}
    proof_bytes = b'{"kind":"fictional provenance"}\n'
    write(root / "reports/fictional.json", proof_bytes)
    for entry, kind, alias in ((node, "raw", "raw"), (mapping, "derived", "snapshot"), (artifact, "packet", "snapshot")):
        path = (raw_root if kind == "raw" else normalized) / entry["path"]
        parents = entry.get("parents", entry.get("input_refs", []))
        provenance = dict(kind="download_receipt" if kind == "raw" else "generated",
            evidence=[dict(path="reports/fictional.json", sha256=hashlib.sha256(proof_bytes).hexdigest())],
            receipt=(dict(root_alias="raw", relative_path=node["receipt_path"], sha256=node["receipt_sha256"],
                          receipt_id=receipt["receipt_id"], url=node["source_url"]) if kind == "raw" else None))
        record = policy.artifact_record(dataset_id=entry["dataset_id"], release_id=entry["release_id"],
            root_alias=alias, relative_path=entry["path"], sha256=entry["sha256"], bytes=path.stat().st_size,
            kind=kind, parents=[by_node[p]["artifact_id"] for p in parents], availability=entry["availability"],
            temporal_classification=entry["temporal_classification"], source_url=entry["source_url"],
            provenance=provenance, scope="Fictional integration fixture", scientific_validation="not_established")
        by_node[entry.get("source_id", entry.get("artifact_id"))] = record
        records.append(record)
    document["artifacts"] = records
    document["uses"] = [dict(use_id="fictional-use", kind="contemporary_evidence", status="allowed",
        profile=snapshot["profile"], origin_at=case["origin_at"], frame_sha256="f" * 64,
        case_fingerprint=fingerprint(case), snapshot_fingerprint=fingerprint(snapshot),
        raw_root_alias="raw", snapshot_root_alias="snapshot",
        grants=[dict(artifact_id=r["artifact_id"], role="reference" if r["kind"] == "derived" else "agent_evidence")
                for r in records], blockers=[])]
    roots = dict(schema_version=1, roots=dict(raw=str(raw_root), snapshot=str(normalized), metadata=str(root)))
    paths = dict(policy=root / "policy.json", roots=root / "roots.json", case=root / "case.json",
                 snapshot=normalized / "snapshot.json", source_catalog=root / "data/catalog/sources.json")
    for key, value in (("policy", document), ("roots", roots), ("case", case), ("snapshot", snapshot), ("source_catalog", source_bytes)):
        write(paths[key], value)
    request = binding.PolicyRequest(paths["policy"], paths["roots"], paths["case"], paths["snapshot"],
                                    paths["source_catalog"], "fictional-use", "f" * 64)
    return dict(request=request, policy=document, roots=roots, case=case, snapshot=snapshot, paths=paths,
                raw_root=raw_root, normalized=normalized)


def argv(fixture, output):
    p = fixture["paths"]
    return ["run", "--output", str(output), "--case", str(p["case"]), "--snapshot", str(p["snapshot"]),
            "--catalog", str(p["source_catalog"]), "--catalog-policy", str(p["policy"]),
            "--policy-roots", str(p["roots"]), "--policy-use", "fictional-use", "--policy-frame-sha256", "f" * 64,
            '--source-root', str(p['case'].parent)]
