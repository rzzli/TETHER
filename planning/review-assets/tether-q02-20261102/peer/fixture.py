"""Independent fictional schema-2 inputs; generated trees belong in ignored cache."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether import _catalog_policy as policy
from asof.serde import canonical, fingerprint


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(name="fixture", *, with_mapping=False, legacy_separator=False):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = ROOT / "data/cache/tether-q02-peer" / (name + "-" + stamp)
    root.mkdir(parents=True)
    raw, normalized = root / "raw", root / "normalized"
    raw.mkdir(); normalized.mkdir()
    source = ROOT / "src/asof/demo/v2"
    case = json.loads((source / "case.json").read_text())
    case.update(task="T6", program=None, endpoint=None)
    snapshot = json.loads((source / "snapshot.json").read_text())
    snapshot["profile"] = "contemporary_assessment"
    snapshot["artifacts"] = snapshot["artifacts"][:1]
    snapshot["sources"] = snapshot["sources"][:1]
    snapshot["raw_root"] = str(raw)
    snapshot["artifacts"][0]["path"] = "packets/evidence.json"
    (normalized / "packets").mkdir()
    (normalized / "packets/evidence.json").write_bytes((source / "evidence.json").read_bytes())
    source_node = snapshot["sources"][0]
    source_node["path"]="originals/raw-inputs.json"
    (raw / "originals").mkdir()
    (raw / source_node["path"]).write_bytes((source / "raw-inputs.json").read_bytes())
    receipt = dict(receipt_id="fictional-receipt", dataset_id=source_node["dataset_id"],
        release_id=source_node["release_id"], relative_path=source_node["path"], url=source_node["source_url"],
        status="completed", sha256=source_node["sha256"], bytes=(raw/source_node["path"]).stat().st_size,
        completed_at_utc="2019-01-01T00:00:00+00:00")
    if legacy_separator:
        receipt["relative_path"]=receipt["relative_path"].replace("/","\\")
    receipt_hash = save(raw / "receipts/source.json", receipt)
    source_node.update(receipt_path="receipts/source.json", receipt_sha256=receipt_hash)
    products = []
    for key, roles in [
        ("synthetic_fixture", ["agent_evidence", "reference"]),
        ("genetics_results", ["agent_evidence"]),
        ("genetics_qc_cases", ["evaluation_only", "reference"]),
        ("igsr_ld_reference", ["reference"]),
        ("study_ld_matrices", ["reference"]),
        ("vbt_linkage", ["evaluation_only", "reference"]),
        ("program_linkage", ["agent_evidence"]),
        ("scorer_artifacts", ["agent_evidence"]),
        ("dated_outcomes", ["evaluation_only"]),
        ("split_definitions", ["evaluation_only"]),
        ("aact_snapshots", ["agent_evidence", "reference"]),
    ]:
        products.append(dict(dataset_id=key, provider_id="fictional", roles=roles, dependencies=[],
            collection_status="planned", parsing_status="not_run", validation_status="not_run"))
    next(p for p in products if p["dataset_id"]=="genetics_results").update(
        dependencies=["genetics_qc_cases", "igsr_ld_reference"],
        conditional_input_groups=[dict(requirement="LD-dependent methods only", dataset_ids=["igsr_ld_reference", "study_ld_matrices"])])
    next(p for p in products if p["dataset_id"]=="scorer_artifacts")["dependencies"]=["dated_outcomes", "split_definitions"]
    legacy=dict(schema_version=1, providers=[dict(provider_id="fictional")], datasets=products)
    save(root / "catalog.json", legacy)
    doc=policy.migrate_catalog((root/"catalog.json").read_bytes(), source_path="catalog.json",
        policy_id="fictional-independent-policy", created_at_utc="2026-11-02T00:00:00+00:00")
    next(p for p in doc["products"] if p["dataset_id"]=="synthetic_fixture")["dependency_review_status"]="reviewed_for_selected_frame"
    check_hash=save(root/"evidence/check.json", dict(fictional=True, scope="No biological assertions"))
    proof=[dict(path="evidence/check.json", sha256=check_hash)]
    raw_record=policy.artifact_record(dataset_id=source_node["dataset_id"],release_id=source_node["release_id"],
        root_alias="raw",relative_path=source_node["path"],sha256=source_node["sha256"],bytes=receipt["bytes"],
        kind="raw",parents=[], availability=deepcopy(source_node["availability"]),
        temporal_classification=source_node["temporal_classification"], source_url=source_node["source_url"],
        provenance=dict(kind="download_receipt",evidence=proof,receipt=dict(root_alias="raw",relative_path=source_node["receipt_path"],
            sha256=receipt_hash,receipt_id=receipt["receipt_id"],url=receipt["url"])),
        scope="Fictional bytes only",scientific_validation="not_established")
    records=[raw_record]
    if with_mapping:
        mapping_path=normalized/"mappings/nested/mapping.json"
        mapping_hash=save(mapping_path,dict(fictional=True, mapping="identity"))
        mapping_node={k:deepcopy(v) for k,v in source_node.items() if k not in ("receipt_path","receipt_sha256")}
        mapping_node.update(source_id="derived-mapping", path="mappings/nested/mapping.json",sha256=mapping_hash,
            parents=[source_node["source_id"]],computed_at="2026-11-02T00:00:00+00:00", method_id="fictional",method_version="1")
        snapshot["sources"].append(mapping_node)
        mapping_record=policy.artifact_record(dataset_id=mapping_node["dataset_id"],release_id=mapping_node["release_id"],
            root_alias="normalized",relative_path=mapping_node["path"],sha256=mapping_hash,bytes=mapping_path.stat().st_size,
            kind="derived",parents=[raw_record["artifact_id"]], availability=deepcopy(mapping_node["availability"]),
            temporal_classification=mapping_node["temporal_classification"],source_url=mapping_node["source_url"],
            provenance=dict(kind="generated",evidence=proof,receipt=None),scope="Fictional mapping",scientific_validation="not_established")
        records.append(mapping_record)
        snapshot["artifacts"][0]["input_refs"]=["derived-mapping"]
    packet=snapshot["artifacts"][0]
    packet_record=policy.artifact_record(dataset_id=packet["dataset_id"],release_id=packet["release_id"],
        root_alias="normalized",relative_path=packet["path"],sha256=packet["sha256"],bytes=(normalized/packet["path"]).stat().st_size,
        kind="packet",parents=[records[-1]["artifact_id"]], availability=deepcopy(packet["availability"]),
        temporal_classification=packet["temporal_classification"],source_url=packet["source_url"],
        provenance=dict(kind="generated",evidence=proof,receipt=None),scope="Fictional packet",scientific_validation="not_established")
    records.append(packet_record)
    frame=hashlib.sha256(b"fictional independent source-only frame").hexdigest()
    doc["artifacts"]=records
    doc["uses"]=[dict(use_id="fictional-use",kind="contemporary_evidence",status="allowed",profile=snapshot["profile"],
        origin_at=snapshot["origin_at"],frame_sha256=frame,case_fingerprint=fingerprint(case),snapshot_fingerprint=fingerprint(snapshot),
        raw_root_alias="raw",snapshot_root_alias="normalized",grants=[dict(artifact_id=r["artifact_id"],role="agent_evidence") for r in records],blockers=[])]
    roots=dict(raw=str(raw),normalized=str(normalized),metadata=str(root))
    save(root/"case.json",case);save(normalized/"snapshot.json",snapshot)
    save(root/"roots.json",dict(schema_version=1,roots=roots));save(root/"policy.json",doc)
    return dict(root=root,case=case,snapshot=snapshot,policy=doc,roots=roots,frame=frame,legacy=legacy)


if __name__ == "__main__":
    value=build(with_mapping=True)
    result=policy.authorize_snapshot(value["policy"],value["snapshot"],case=value["case"],use_id="fictional-use",root_aliases=value["roots"])
    print(json.dumps(dict(fixture=str(value["root"]),supplied=len(result["binding"]["inventory"]))))
