"""Q03 source-only inventory. Reads selected metadata and Parquet footers, never rows."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow
import pyarrow.parquet as pq

WORK = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
STORE = Path(r"E:\projects_data\drug_target_agents_data")
RAW = STORE / "raw/open_targets_platform/25.09"
SELECTED = {"ot_evidence", "ot_credible_set", "ot_study", "ot_target", "ot_disease", "hgnc_symbols", "ot_l2g_prediction", "ot_colocalisation_coloc"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    catalog_path = WORK / "data/catalog/sources.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    datasets = {d["dataset_id"]: d for d in catalog["datasets"] if d["dataset_id"] in SELECTED}
    state_paths = [STORE / "manifests" / (name + "-state.json") for name in [
        "core-25-09-chembl35-2026-10-10", "literature-recovery-20261017",
        "preprint-p02-credible-completion-20261101T031842Z", "starter-2026-10-10"]]
    states = []
    receipts = {}
    for path in state_paths:
        state = json.loads(path.read_text(encoding="utf-8"))
        selected = [r for r in state.get("results", []) if r.get("dataset_id") in SELECTED]
        states.append({"path": str(path), "sha256": digest(path), "batch_id": state.get("batch_id"), "selected_receipt_counts": dict(Counter(r["dataset_id"] for r in selected))})
        for receipt in selected:
            rel = str(receipt.get("relative_path", "")).replace("\\", "/")
            receipts[rel] = receipt
    folders = {
        "gwas_credible_sets_evidence": [RAW / "output/evidence/sourceId=gwas_credible_sets"],
        "credible_set": [RAW / "output/credible_set", RAW / "preprint-p02-credible-completion-20261101T031842Z/credible_set"],
        "target": [RAW / "output/target"],
        "disease": [RAW / "output/disease"],
        "l2g_prediction": [RAW / "output/l2g_prediction"],
        "colocalisation_coloc": [RAW / "output/colocalisation_coloc"],
    }
    inventory = {}
    schemas = {}
    for table, paths in folders.items():
        files = sorted(p for folder in paths for p in folder.glob("*.parquet"))
        records = []
        signatures = Counter()
        for path in files:
            parquet = pq.ParquetFile(path)
            schema_text = str(parquet.schema_arrow.remove_metadata())
            signature = hashlib.sha256(schema_text.encode()).hexdigest()
            signatures[signature] += 1
            schemas.setdefault(table, {})[signature] = {"schema": schema_text, "field_names": parquet.schema_arrow.names, "example_path": str(path)}
            rel = path.relative_to(STORE).as_posix()
            receipt = receipts.get(rel)
            records.append({"path": str(path), "relative_path": rel, "bytes": path.stat().st_size, "schema_sha256": signature,
                            "row_count": parquet.metadata.num_rows, "row_group_count": parquet.metadata.num_row_groups,
                            "row_group_rows": [parquet.metadata.row_group(i).num_rows for i in range(parquet.metadata.num_row_groups)],
                            "receipt": {k: receipt.get(k) for k in ["receipt_id", "dataset_id", "release_id", "status", "bytes", "sha256", "publisher_hash_verified", "checksum_origin", "url"]} if receipt else None,
                            "receipt_size_match": path.stat().st_size == receipt.get("bytes") if receipt else None})
        inventory[table] = {"directories": [str(p) for p in paths], "file_count": len(files), "partial_file_count": sum(len(list(p.glob("*.partial"))) for p in paths), "schema_counts": dict(signatures), "files": records}
    queue_path = WORK / "data/manifests/private/core-2026-10-10-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    study_queue = [f for f in queue["files"] if f.get("dataset_id") == "ot_study"]
    study = {"queue_path": str(queue_path), "queue_sha256": digest(queue_path), "queue_records": study_queue,
             "named_paths_exist": {r["relative_path"]: (STORE / r["relative_path"]).exists() for r in study_queue},
             "directory_exists": (RAW / "output/study").exists(),
             "completed_receipts": [r for r in receipts.values() if r.get("dataset_id") == "ot_study"]}
    neutral_catalog = {}
    for key, dataset in datasets.items():
        snap = dataset.get("acquisition_snapshot") or {}
        neutral_catalog[key] = {"provider_id": dataset.get("provider_id"), "collection_status": dataset.get("collection_status"),
                               "snapshot": {k: snap.get(k) for k in ["expected_files", "completed_files", "status", "release_ids", "batch_id", "source_batch_ids", "snapshot_date"]}}
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "phase": "schemas_and_file_metadata_only", "row_values_read": 0,
              "pyarrow_version": pyarrow.__version__, "catalog_path": str(catalog_path), "catalog_sha256": digest(catalog_path),
              "selected_catalog": neutral_catalog, "state_metadata": states, "study_availability": study, "inventory": inventory}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "SOURCE-SCHEMAS.json").write_text(json.dumps(schemas, indent=2) + "\n", encoding="utf-8")
    (OUT / "SOURCE-INVENTORY.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": result["phase"], "tables": {k: {"files": v["file_count"], "partial_files": v["partial_file_count"], "schema_variants": len(v["schema_counts"])} for k, v in inventory.items()}, "study_directory_exists": study["directory_exists"], "study_named_path_exists": list(study["named_paths_exist"].values())}, indent=2))


if __name__ == "__main__":
    main()
