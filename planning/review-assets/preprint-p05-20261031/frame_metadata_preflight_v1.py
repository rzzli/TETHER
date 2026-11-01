"""Read transport metadata and schema/footer metadata; never read source values."""

import hashlib
import json
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pyarrow
import pyarrow.parquet as parquet


CWD = Path(r"D:\Projects\drug_target_agents")
BULK = Path(r"E:\projects_data\drug_target_agents_data")
OUT = CWD / "planning/review-assets/preprint-p05-20261031/FRAME-METADATA-PREFLIGHT-v1.json"
EXPECTED_CATALOG_SHA256 = "3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109"
QUEUES = [
    CWD / "data/manifests/private/core-2026-10-10-queue.json",
    CWD / "data/manifests/private/literature-recovery-20261017-queue.json",
    CWD / "data/manifests/private/preprint-p02-credible-completion-20261101T031842Z/queue.json",
    CWD / "data/manifests/private/starter-2026-10-10-queue.json",
]
MAX_FILES = 256
MAX_BYTES = 10 * 1024**3


def digest(path):
    # This function is used only on JSON metadata and this metadata helper.
    assert Path(path).suffix in {".json", ".py"}, path
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def pin(path, role):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size, "role": role}


def normalized_parts(path):
    return unquote(path.replace("\\", "/")).strip("/").split("/")


def partition_proof(record):
    """Require exact 25.09 roots and one exact partition segment on both paths."""
    if record.get("dataset_id") != "ot_evidence" or record.get("release_id") != "25.09":
        return None
    local = normalized_parts(record.get("relative_path", ""))
    source = urlsplit(record.get("url", ""))
    remote = normalized_parts(source.path)
    if local[:3] != ["raw", "open_targets_platform", "25.09"]:
        return None
    remote_prefix = ["pub", "databases", "opentargets", "platform", "25.09", "output", "evidence"]
    if source.scheme != "https" or source.hostname != "ftp.ebi.ac.uk" or remote[:7] != remote_prefix:
        return None
    if len(remote) != 9 or local.count("evidence") != 1:
        return None
    evidence_index = local.index("evidence")
    if len(local[evidence_index:]) != 3:
        return None
    local_partition = local[evidence_index + 1].split("=", 1)
    remote_partition = remote[7].split("=", 1)
    if len(local_partition) != 2 or len(remote_partition) != 2:
        return None
    if local_partition[0] not in {"sourceId", "datasourceId"} or remote_partition[0] not in {"sourceId", "datasourceId"}:
        return None
    if local_partition[1] != remote_partition[1] or local[-1] != remote[-1]:
        return None
    return {"value": local_partition[1], "local_key": local_partition[0], "official_url_key": remote_partition[0], "filename": local[-1]}


def family(record):
    proof = partition_proof(record)
    if proof and proof["value"] == "gwas_credible_sets":
        return "gwas_credible_sets"
    if record.get("dataset_id") in {"ot_target", "ot_disease"} and record.get("release_id") == "25.09":
        return {"ot_target": "target", "ot_disease": "disease"}[record["dataset_id"]]
    if record.get("dataset_id") == "hgnc_symbols" and record.get("release_id") == "snapshot_2026-10-10":
        return "hgnc"
    return None


def footer_schema(path):
    # read_metadata reads the footer; no read_table, read_row_group, iter_batches,
    # column-statistics access, or TSV data-line iteration is permitted here.
    size = path.stat().st_size
    with path.open("rb") as handle:
        header = handle.read(4)
        handle.seek(-8, 2)
        trailer = handle.read(8)
    length = struct.unpack("<I", trailer[:4])[0]
    assert header == b"PAR1" and trailer[4:] == b"PAR1" and 0 < length < size - 12
    metadata = parquet.read_metadata(path)
    schema = metadata.schema.to_arrow_schema()
    text = str(schema)
    return {
        "format": "parquet", "PAR1_header_and_footer": True,
        "footer_length_bytes": length, "footer_metadata_readable": True,
        "row_count_metadata_only": metadata.num_rows,
        "row_group_count_metadata_only": metadata.num_row_groups,
        "schema_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "schema_top_level_fields": schema.names, "schema_text": text,
    }


def main():
    assert Path.cwd() == CWD and not OUT.exists()
    catalog_path = CWD / "data/catalog/sources.json"
    assert digest(catalog_path) == EXPECTED_CATALOG_SHA256
    catalog = read_json(catalog_path)
    provider_by_dataset = {x["dataset_id"]: x["provider_id"] for x in catalog["datasets"]}
    core_path = BULK / "manifests/core-25-09-chembl35-2026-10-10-state.json"
    core = read_json(core_path)
    core_by_receipt = {x["receipt_id"]: x for x in core["results"]}
    inventory_path = CWD / "data/manifests/public/2026-10-10-download-size-inventory.json"
    inventory = next(x for x in read_json(inventory_path)["inventories"] if x["release_id"] == "25.09")
    official_by_url = {x["url"]: x for x in inventory["files"]}
    parents = [pin(catalog_path, "current_catalog"), pin(core_path, "readonly_core_state"), pin(inventory_path, "official_inventory_capture")]
    registered = {}
    for queue_path in QUEUES:
        queue = read_json(queue_path)
        parents.append(pin(queue_path, "neutral_registered_source_queue"))
        for record in queue["files"]:
            rid = record["receipt_id"]
            if rid in registered:
                assert registered[rid]["record"] == record
            registered[rid] = {"record": record, "queue_path": str(queue_path), "batch_id": queue["batch_id"]}

    # Enumerate every locally present receipt whose ID is registered in any of
    # the four neutral queues. Filter by metadata, never by a scientific row.
    local_receipt_paths = {p.stem: p for p in (BULK / "manifests/receipts").glob("*.json")}
    ot_registered = {rid for rid, entry in registered.items() if provider_by_dataset.get(entry["record"]["dataset_id"]) == "opentargets"}
    candidate_records = []
    ambiguous = []
    for rid, entry in registered.items():
        queued = entry["record"]
        if provider_by_dataset.get(queued["dataset_id"]) != "opentargets" and queued["dataset_id"] != "hgnc_symbols":
            continue
        if rid not in local_receipt_paths:
            continue
        receipt_path = local_receipt_paths[rid]
        receipt = read_json(receipt_path)
        for key in ["receipt_id", "dataset_id", "release_id", "relative_path", "url"]:
            assert receipt[key] == queued[key], (rid, key)
        # Detect malformed or unprovable partition labels rather than silently
        # excluding a potentially relevant registered source path.
        if "gwas_credible_sets" in receipt.get("relative_path", "") + receipt.get("url", "") and not partition_proof(receipt):
            ambiguous.append({"receipt_id": rid, "relative_path": receipt.get("relative_path"), "url": receipt.get("url")})
        group = family(receipt)
        if group:
            candidate_records.append((group, receipt, receipt_path, entry))

    bounds = {}
    for group in ["gwas_credible_sets", "target", "disease", "hgnc"]:
        rows = [x for x in candidate_records if x[0] == group]
        sizes = [int(x[1]["bytes"]) for x in rows]
        bounds[group] = {"receipt_known_files": len(rows), "receipt_recorded_total_bytes": sum(sizes), "exceeds_256_files_or_10_GiB": len(rows) > MAX_FILES or sum(sizes) > MAX_BYTES}
    oversized = [key for key, value in bounds.items() if value["exceeds_256_files_or_10_GiB"]]
    assert not oversized, {"bounds_only_required": oversized, "bounds": bounds}
    assert not ambiguous, ambiguous

    files = []
    for group, receipt, receipt_path, entry in candidate_records:
        path = BULK / receipt["relative_path"].replace("\\", "/")
        row = {
            "family": group, "dataset_id": receipt["dataset_id"],
            "provider_id": provider_by_dataset[receipt["dataset_id"]],
            "release_id": receipt["release_id"], "receipt_id": receipt["receipt_id"],
            "receipt": pin(receipt_path, "original_transport_receipt"),
            "registered_queue_path": entry["queue_path"], "source_batch_id": entry["batch_id"],
            "payload_path": str(path), "relative_path": receipt["relative_path"].replace("\\", "/"),
            "source_url": receipt["url"], "receipt_status": receipt["status"],
            "receipt_recorded_bytes": int(receipt["bytes"]),
            "receipt_recorded_payload_sha256": receipt["sha256"],
            "payload_hash_verified_this_preflight": False,
            "payload_hash_scope": "Recorded transport-receipt hash only; no new payload hashing in this preflight.",
            "publisher_hash_verified": receipt.get("publisher_hash_verified", False),
            "publisher_hash_status": "unknown_not_supplied",
            "local_file_exists": path.is_file(),
            "parse_status": "not_run", "scientific_validation": "not_run",
        }
        assert row["receipt_status"] == "completed"
        if path.is_file():
            row["measured_bytes"] = path.stat().st_size
            row["size_matches_receipt"] = path.stat().st_size == receipt["bytes"]
            assert row["size_matches_receipt"]
            if group != "hgnc":
                row["metadata"] = footer_schema(path)
            else:
                with path.open("rb") as handle:
                    header = handle.readline(1024 * 1024)
                assert header.endswith(b"\n")
                fields = header.decode("utf-8-sig").rstrip("\r\n").split("\t")
                assert fields[0] == "hgnc_id"
                row["metadata"] = {"format": "tsv", "header_only": True, "schema_header_fields": fields, "schema_header_sha256": hashlib.sha256(header).hexdigest(), "data_lines_read": 0}
        if group != "hgnc":
            assert receipt["url"] in official_by_url
            row["official_inventory_entry"] = official_by_url[receipt["url"]]
            assert receipt["receipt_id"] in core_by_receipt
            for key in ["relative_path", "url", "bytes", "sha256", "status"]:
                assert core_by_receipt[receipt["receipt_id"]][key] == receipt[key]
            row["readonly_core_state_record_matches_receipt"] = True
        if group == "gwas_credible_sets":
            row["partition_proof"] = partition_proof(receipt)
        files.append(row)
    files.sort(key=lambda x: (x["family"], x["relative_path"]))

    families = {}
    for group, b in bounds.items():
        rows = [x for x in files if x["family"] == group]
        eligible = [x["record"] for x in registered.values() if family(x["record"]) == group]
        missing_receipts = [x for x in eligible if x["receipt_id"] not in local_receipt_paths]
        official = []
        if group != "hgnc":
            for item in inventory["files"]:
                if not item["relative_path"].endswith(".parquet"):
                    continue
                parts = normalized_parts(item["relative_path"])
                is_match = (group in {"target", "disease"} and parts[0] == group)
                is_match = is_match or (group == "gwas_credible_sets" and len(parts) == 3 and parts[0] == "evidence" and parts[1] in {"sourceId=gwas_credible_sets", "datasourceId=gwas_credible_sets"})
                if is_match:
                    official.append(item)
        local_urls = {x["source_url"] for x in rows}
        official_urls = {x["url"] for x in official}
        families[group] = {
            **b, "registered_queue_files": len(eligible),
            "measured_local_files": sum(x["local_file_exists"] for x in rows),
            "measured_local_bytes": sum(x.get("measured_bytes", 0) for x in rows),
            "missing_receipts": missing_receipts,
            "missing_local_payload_paths": [x["payload_path"] for x in rows if not x["local_file_exists"]],
            "captured_official_inventory_payload_files": len(official) if group != "hgnc" else None,
            "captured_official_inventory_complete_coverage": local_urls == official_urls if group != "hgnc" else None,
            "missing_official_source_urls": sorted(official_urls - local_urls),
            "local_source_urls_absent_from_official_capture": sorted(local_urls - official_urls) if group != "hgnc" else [],
            "unique_schema_sha256": sorted({x["metadata"]["schema_sha256"] for x in rows if "metadata" in x and "schema_sha256" in x["metadata"]}),
            "metadata_row_count_only": sum(x.get("metadata", {}).get("row_count_metadata_only", 0) for x in rows) if group != "hgnc" else None,
            "parse_status": "not_run", "scientific_validation": "not_run",
        }
        assert not missing_receipts
        if group != "hgnc":
            assert local_urls == official_urls

    credible_path = CWD / "planning/review-assets/preprint-p05-20261031/ACQUISITION-METADATA-v1.json"
    credible = read_json(credible_path)
    parents.append(pin(credible_path, "previous_independent_neutral_credible_set_acquisition_metadata"))
    assert credible["summary"]["measured_original_payload_count"] == 25
    study = next(x for x in catalog["datasets"] if x["dataset_id"] == "ot_study")
    study_paths = [{"path": str(BULK / x.replace("\\", "/")), "exists": (BULK / x.replace("\\", "/")).exists()} for x in study["acquisition_snapshot"]["relative_paths"]]
    result = {
        "schema_version": 1, "artifact_id": "preprint-p05-frame-metadata-preflight-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "metadata_preflight_complete_awaiting_root_source_only_frame_freeze",
        "scope": "Exact receipt-known local originals and neutral acquisition/footer/schema metadata only. No biological row values, source-value scans, case selection, candidates, answers, human responses, clinical/evaluation ancestors, models or downloads.",
        "roles": ["agent_evidence", "reference"],
        "execution": {"cwd": str(CWD), "interpreter": sys.executable, "pyarrow_version": pyarrow.__version__, "helper": pin(Path(__file__), "pure_metadata_helper"), "new_payload_hashes": 0, "source_data_rows_read": 0, "network_calls": 0, "model_calls": 0, "download_or_worker_restarts": 0},
        "parents": parents,
        "registration_coverage": {"neutral_queue_count": len(QUEUES), "registered_open_targets_receipt_ids": len(ot_registered), "registered_open_targets_local_receipts_enumerated": len(ot_registered & set(local_receipt_paths)), "registered_open_targets_receipts_absent": len(ot_registered - set(local_receipt_paths)), "local_registry_json_filenames_enumerated": len(local_receipt_paths), "selection_rule": "Inspect every locally present receipt registered by the neutral core, recovery, completion and starter queues; select only exact dataset/release metadata and provable gwas_credible_sets partitions. No first-N or basename-only filtering.", "unregistered_local_receipt_ids_not_read": sorted(set(local_receipt_paths) - set(registered))},
        "partition_filter": {"accepted_keys": ["sourceId", "datasourceId"], "exact_value": "gwas_credible_sets", "required_release": "25.09", "local_layout_counts": dict(Counter(x["partition_proof"]["local_key"] for x in files if x["family"] == "gwas_credible_sets")), "official_url_layout_counts": dict(Counter(x["partition_proof"]["official_url_key"] for x in files if x["family"] == "gwas_credible_sets")), "ambiguous_or_unprovable_registered_partition_records": ambiguous, "scope_of_absence": "No claim of global absence for a layout not present in the captured official inventory or registered local receipts."},
        "bounds_policy": {"maximum_candidate_family_files_before_value_scan_freeze": MAX_FILES, "maximum_candidate_family_bytes_before_value_scan_freeze": MAX_BYTES, "oversized_families": oversized, "payload_values_still_require_root_freeze": True},
        "families": families, "files": files,
        "credible_set_reused_neutral_metadata": {"parent_path": str(credible_path), "parent_sha256": digest(credible_path), "summary": credible["summary"], "new_payload_reads_or_hashes_this_preflight": 0},
        "ot_study_location_check_only": {"paths": study_paths, "contents_read": False, "availability": "missing_at_catalog_path_retained_unknown" if not any(x["exists"] for x in study_paths) else "location_exists_contents_unchecked"},
        "limitations": ["Transport receipt SHA-256 pins are recorded, not newly verified against payload bytes in this preflight.", "Publisher checksums remain unknown where not supplied by original receipts.", "Captured directory coverage is file coverage, not proof of biological completeness or semantic validity.", "Parquet footer/schema metadata and the HGNC header are inspected; full product parsing and scientific validation remain not_run.", "All selected Open Targets files are exactly 25.09; HGNC is exactly snapshot_2026-10-10. No older/newer release or substitute was selected.", "25.09 acquisition establishes contemporary availability only; historical eligibility and source/annotation dates remain unverified.", "Root must freeze explicit source-only scan rules and file pins before any value reads or deterministic case selection."],
        "source_mutations": 0,
    }
    for item in parents:
        assert digest(item["path"]) == item["sha256"], item["path"]
    assert digest(catalog_path) == EXPECTED_CATALOG_SHA256
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert read_json(OUT)["execution"]["source_data_rows_read"] == 0
    print(json.dumps({"artifact": str(OUT), "sha256": digest(OUT), "family_bounds": bounds, "registration_coverage": result["registration_coverage"], "partition_filter": result["partition_filter"], "official_coverage": {k: v["captured_official_inventory_complete_coverage"] for k, v in families.items()}}, indent=2))


if __name__ == "__main__":
    main()
