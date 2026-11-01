"""Isolated P02 completed-release literal join; all products are evaluation_only.

No network, acquisition, model calls, or writes to the external original-data root.
Run self-test, freeze, then scan. A frozen plan is never overwritten.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


ROOT = Path(r"D:\Projects\drug_target_agents")
ASSETS = ROOT / "planning/review-assets/preprint-p02-20261031"
DATA = Path(r"E:\projects_data\drug_target_agents_data")
QUEUE = ROOT / "data/manifests/private/preprint-p02-credible-completion-20261101T031842Z/queue.json"
QUEUE_SHA = "2c976d24830472e40271db98363bf5cb6d9c54a47e83974a26fa3422c988b5a2"
CORE = DATA / "manifests/core-25-09-chembl35-2026-10-10-state.json"
CORE_SHA = "f7f238e92db035232f8273a18ec2182d99ad6571d570bff50b3899dbc56c15ea"
PLAN = ASSETS / "COMPLETED-JOIN-PLAN-v2.json"
REPORT = ASSETS / "COMPLETED-JOIN-REPORT-v2.json"
VERIFY = ASSETS / "CREDIBLE-COMPLETION-VERIFY-v1.json"
CATALOG = ROOT / "data/catalog/sources.json"
INVENTORY = ROOT / "data/manifests/public/2026-10-10-download-size-inventory.json"
GWAS_PLAN = ASSETS / "GWAS-SCAN-PLAN-v1.json"
GWAS_REPORT = ASSETS / "GWAS-SCAN-REPORT-v1.json"
OLD_PLAN = ASSETS / "CREDIBLE-JOIN-PLAN-v1.json"
OLD_REPORT = ASSETS / "CREDIBLE-JOIN-REPORT-v1.json"
FIELDS = ["studyLocusId", "studyId", "variantId", "chromosome", "position",
          "beta", "zScore", "pValueMantissa", "pValueExponent", "standardError", "sampleSize"]
NUMERIC = ["beta", "zScore", "pValueMantissa", "pValueExponent", "standardError", "sampleSize"]
ROLE = {"role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False}


def utc():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def check_pin(expected):
    actual = pin(expected["path"])
    assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], f"Pin changed: {expected['path']}"
    return actual


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def archive_bytes(directory, data, extension="json"):
    path = directory / f"{digest(data)}.{extension}"
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    return pin(path)


def same_identity(receipt, source):
    for field in ["receipt_id", "dataset_id", "release_id", "url"]:
        assert receipt[field] == source[field], f"Receipt identity mismatch: {field}"
    assert receipt["relative_path"].replace("\\", "/") == source["relative_path"].replace("\\", "/")
    assert receipt["status"] == "completed"


def footer_proof(path):
    with Path(path).open("rb") as stream:
        assert stream.read(4) == b"PAR1"
        stream.seek(-8, 2)
        tail = stream.read(8)
        assert tail[4:] == b"PAR1"
        length = struct.unpack("<I", tail[:4])[0]
        assert 0 < length <= Path(path).stat().st_size - 12
        stream.seek(-8 - length, 2)
        footer = stream.read(length)
        assert len(footer) == length
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    assert "studyLocusId" in schema.names
    assert pa.types.is_string(schema.field("studyLocusId").type) or pa.types.is_large_string(schema.field("studyLocusId").type)
    return {"footer_bytes": length, "footer_sha256": digest(footer),
            "rows": parquet.metadata.num_rows,
            "row_groups": [parquet.metadata.row_group(i).num_rows for i in range(parquet.num_row_groups)],
            "arrow_schema": str(schema),
            "arrow_schema_serialized_sha256": digest(schema.serialize().to_pybytes()),
            "projected_fields": [name for name in FIELDS if name in schema.names],
            "schema_absent_fields": [name for name in FIELDS if name not in schema.names]}


def select_exact(batch, key):
    """Arrow equality and filtering precede Python conversion; null keys never match."""
    column = batch.column(batch.schema.get_field_index("studyLocusId"))
    mask = pc.fill_null(pc.equal(column, pa.scalar(key, type=column.type)), False)
    indices = pc.indices_nonzero(mask).to_pylist()
    return indices, batch.filter(mask)


def classify(rows):
    if not rows:
        return {"status": "zero_exact_matches_in_complete_release", "matches": 0,
                "duplicate_physical_occurrences": 0, "conflicting_fields": [], "chosen_row": None}
    conflicts = [field for field in FIELDS if len({json.dumps(row.get(field), sort_keys=True, allow_nan=False) for row in rows}) > 1]
    return {"status": "one_exact_match" if len(rows) == 1 else ("many_exact_matches_with_conflicts" if conflicts else "many_identical_exact_matches"),
            "matches": len(rows), "duplicate_physical_occurrences": max(0, len(rows) - 1),
            "conflicting_fields": conflicts, "chosen_row": None}


def self_test():
    """Fictional literal data exercise zero/one/many/conflict shapes and nulls."""
    def exercise(keys, labels, sought="fictional-key"):
        batch = pa.record_batch({"studyLocusId": keys, "studyId": labels})
        indices, chosen = select_exact(batch, sought)
        return indices, chosen.to_pylist()
    assert exercise(["other", None], ["a", "b"])[0] == []
    indices, rows = exercise([None, "fictional-key", "other"], ["a", "b", "c"])
    assert indices == [1] and classify(rows)["status"] == "one_exact_match"
    indices, rows = exercise(["fictional-key", "fictional-key"], ["a", "a"])
    assert indices == [0, 1] and classify(rows)["status"] == "many_identical_exact_matches"
    indices, rows = exercise(["fictional-key", "fictional-key"], ["a", "b"])
    assert classify(rows)["conflicting_fields"] == ["studyId"] and classify(rows)["chosen_row"] is None
    assert exercise(["Fictional-key", "fictional-key "], ["a", "b"])[0] == []
    # Offsets remain physical within each row group, including later batches.
    offset = 0
    physical = []
    for batch in pa.table({"studyLocusId": ["other", "fictional-key", "fictional-key", None]}).to_batches(max_chunksize=2):
        indices, _ = select_exact(batch, "fictional-key")
        physical.extend(offset + i for i in indices)
        offset += batch.num_rows
    assert physical == [1, 2]
    return {**ROLE, "fixture": "fictional_literal_strings_only_no_biological_data", "shapes_passed": ["zero", "one", "many_identical", "many_conflicting", "null", "case_and_whitespace_exact", "physical_batch_offsets"]}


def freeze():
    assert not PLAN.exists() and not REPORT.exists(), "Never overwrite an earlier plan/report"
    started = time.perf_counter()
    queue_pin = pin(QUEUE)
    assert queue_pin["sha256"] == QUEUE_SHA
    queue = read_json(QUEUE)
    verify_bytes = VERIFY.read_bytes()
    verify = json.loads(verify_bytes.decode("utf-8-sig"))
    assert verify["complete"] and verify["expected_files"] == verify["verified_files"] == 23 and verify["failed_files"] == 0
    assert verify["verified_bytes"] == 2430231014
    old = read_json(OLD_PLAN)
    old_report = read_json(OLD_REPORT)
    assert pin(OLD_PLAN)["sha256"] == old_report["frozen_plan"]["sha256"]
    gwas_report = read_json(GWAS_REPORT)
    assert pin(GWAS_PLAN)["sha256"] == gwas_report["frozen_plan"]["sha256"]
    gwas_manifest = ROOT / gwas_report["manifest"]["path"]
    check_pin({**gwas_report["manifest"], "path": str(gwas_manifest)})
    gwas = read_json(gwas_manifest)
    unit = next(unit for unit in gwas["units"] if unit["unit_id"] == old["case"]["unit_id"])
    slots = [slot for slot in unit["selected_slots"] if slot["source"]["field"] == "studyLocusId"]
    assert len(slots) == 1
    slot = slots[0]
    assert slot["value"] == old["case"]["studyLocusId"]
    assert {k: slot["source"][k] for k in ["source_id", "row_group", "row"]} == old["case"]["previous_locator"]
    gwas_source = next(proof for proof in gwas["source_proofs"] if proof["source"]["source_id"] == slot["source"]["source_id"])
    catalogue = read_json(CATALOG)
    dataset = next(d for d in catalogue["datasets"] if d["dataset_id"] == "ot_credible_set")
    assert "25.09" in [r["release_id"] for r in dataset["candidate_releases"]]
    inventory = read_json(INVENTORY)
    release = next(i for i in inventory["inventories"] if i["release_id"] == "25.09")
    official = [f for f in release["files"] if f["relative_path"].startswith("credible_set/") and f["relative_path"].endswith(".parquet")]
    assert len(official) == 25
    official_by_name = {Path(f["relative_path"]).name: f for f in official}
    assert len(official_by_name) == 25
    sources = [{"source": f["state_result"], "expected_original": f["original"], "expected_receipt": f["receipt"], "origin": "old_two_file_plan"} for f in old["files"]]
    sources.extend({"source": f, "origin": "approved_isolated_23_file_batch"} for f in queue["files"])
    assert len(sources) == 25
    assert {Path(x["source"]["relative_path"]).name for x in sources} == set(official_by_name)
    private = ROOT / "data/benchmark/gold_evidence" / ("preprint-p02-completed-credible-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    ignored = subprocess.run(["git", "check-ignore", "-q", str(private / "receipt-archive/placeholder.json")], cwd=ROOT, check=False)
    assert ignored.returncode == 0, "Raw matches must remain ignored"
    private.mkdir(parents=True, exist_ok=False)
    archive = private / "receipt-archive"
    archive.mkdir()
    emitted_verifier_pin = archive_bytes(archive, verify_bytes)
    # Preserve the exact unmodified verifier output before adding role metadata.
    verify.update(ROLE)
    verify["unmodified_tool_output_archive"] = emitted_verifier_pin
    VERIFY.write_text(json.dumps(verify, indent=2) + "\n", encoding="utf-8")
    core_pin = pin(CORE)
    preservation = {"core_state": {"observed": core_pin, "prior_sha256": CORE_SHA, "unchanged": core_pin["sha256"] == CORE_SHA}, "old_two_files": []}
    files = []
    for item in sorted(sources, key=lambda x: Path(x["source"]["relative_path"]).name):
        source = item["source"]
        basename = Path(source["relative_path"].replace("\\", "/")).name
        listing = official_by_name[basename]
        assert source["dataset_id"] == "ot_credible_set" and source["release_id"] == "25.09" and source["url"] == listing["url"]
        original = DATA / source["relative_path"]
        original_pin = pin(original)
        receipt_path = DATA / "manifests/receipts" / (source["receipt_id"] + ".json")
        raw = receipt_path.read_bytes()
        receipt = json.loads(raw.decode("utf-8-sig"))
        same_identity(receipt, source)
        assert original_pin["bytes"] == receipt["bytes"] and original_pin["sha256"] == receipt["sha256"]
        if "expected_bytes" in source:
            assert original_pin["bytes"] == source["expected_bytes"]
        receipt_pin = {"path": str(receipt_path), "bytes": len(raw), "sha256": digest(raw)}
        archived = archive_bytes(archive, raw)
        record = {"basename": basename, "origin": item["origin"], "source": source,
                  "official_inventory_entry": listing, "original": original_pin,
                  "receipt_original": receipt_pin, "receipt_archive": archived,
                  "receipt_observation_utc": receipt["completed_at_utc"], "publisher_hash_verified": receipt.get("publisher_hash_verified", False),
                  **footer_proof(original)}
        if "expected_original" in item:
            preserved = {"basename": basename, "original_unchanged": original_pin == item["expected_original"],
                         "receipt_unchanged": receipt_pin == item["expected_receipt"],
                         "expected_original": item["expected_original"], "expected_receipt": item["expected_receipt"]}
            preservation["old_two_files"].append(preserved)
        files.append(record)
    parents = [pin(p) for p in [QUEUE, VERIFY, INVENTORY, CATALOG, GWAS_PLAN, GWAS_REPORT, gwas_manifest, OLD_PLAN, OLD_REPORT, Path(__file__).resolve()]]
    cutoff = utc()
    observed_times = [datetime.fromisoformat(f["receipt_observation_utc"]) for f in files]
    assert datetime.fromisoformat(cutoff) > max(observed_times)
    plan = {"schema_version": 2, **ROLE, "protocol": "preprint_p02_completed_credible_literal_join.v2",
            "created_at_utc": cutoff, "cutoff_utc": cutoff, "raw_source_values_scanned_before_freeze": 0,
            "parents": parents, "private_output": str(private), "files": files,
            "case": old["case"], "original_gwas_source": {k: gwas_source[k] for k in ["source", "original", "receipt"]},
            "key_evidence": {"manifest": pin(gwas_manifest), "source_locator": slot["source"], "slot_id": slot["slot_id"]},
            "fields": FIELDS, "numeric_fields": NUMERIC, "batch_size": 65536,
            "collection": {"release_id": "25.09", "official_parquet_files": 25, "old_files": 2, "newly_completed_files": 23, "verified_files": len(files), "original_bytes": sum(f["original"]["bytes"] for f in files), "physical_rows": sum(f["rows"] for f in files), "scope": "Complete pinned 25-file credible_set Parquet release inventory; _SUCCESS is not a payload"},
            "matching": "Exact studyLocusId equality in Arrow batches before Python conversion; retain every matching physical row and original file/row-group/row locator; no first-choice selection",
            "duplicate_policy": "Keep all matches; report multiplicity and per-field disagreements without resolving them",
            "native_value_policy": "Retain reported native values with source types, nulls and component names; no transformations, gene/drug direction, MR, prediction features or clinical claims",
            "unknowns": {"units": None, "units_reason": "Not established by bounded native credible_set fields", "ancestry": None, "ancestry_reason": "Not requested or inferred from another dataset", "upstream_study": None, "upstream_study_reason": "Native studyId may be retained but original upstream study identity/metadata were not verified"},
            "temporal_policy": "New UTC cutoff after all download observations; contemporary evaluation-only descendant; no backfill into earlier runs or earlier cutoffs",
            "preservation_before_scan": preservation, "receipt_policy": "Exact inspected bytes copied into a private content-addressed archive; transport originals and state remain read-only",
            "resource_policy": "Record verification and scan time separately, logical bytes/rows/selected packet bytes; actual physical I/O unknown; Windows process peak RSS measured when available",
            "verification_elapsed_seconds": time.perf_counter() - started, "self_test": self_test(),
            "new_downloads": 0, "model_calls": 0}
    write_new(PLAN, plan)
    print(json.dumps({**ROLE, "phase": "frozen_before_source_value_scan", "plan": pin(PLAN), "files": len(files), "physical_rows": plan["collection"]["physical_rows"], "preservation": preservation["core_state"]["unchanged"]}))


def peak_rss():
    """Windows PeakWorkingSetSize, process-wide high-water mark, not scan delta."""
    if sys.platform != "win32":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    success = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(ctypes.windll.kernel32.GetCurrentProcess()), ctypes.byref(counters), counters.cb)
    return counters.PeakWorkingSetSize if success else None


def scan():
    assert PLAN.exists() and not REPORT.exists(), "Require frozen plan and no existing report"
    plan_pin = pin(PLAN)
    plan = read_json(PLAN)
    private = Path(plan["private_output"])
    assert plan["role"] == "evaluation_only" and plan["agent_visible"] is False
    for parent in plan["parents"]:
        check_pin(parent)
    verification_started = time.perf_counter()
    pre = plan["preservation_before_scan"]
    assert pre["core_state"]["unchanged"] and all(x["original_unchanged"] and x["receipt_unchanged"] for x in pre["old_two_files"]), "Preservation difference recorded; do not scan or roll back"
    for file in plan["files"]:
        check_pin(file["original"])
        check_pin(file["receipt_original"])
        check_pin(file["receipt_archive"])
        assert footer_proof(file["original"]["path"]) == {k: file[k] for k in ["footer_bytes", "footer_sha256", "rows", "row_groups", "arrow_schema", "arrow_schema_serialized_sha256", "projected_fields", "schema_absent_fields"]}
    verification_elapsed = time.perf_counter() - verification_started
    tracemalloc.start()
    started = time.perf_counter()
    cpu = time.process_time()
    matches = []
    key_rows = key_arrow_bytes = projected_rows = projected_arrow_bytes = selected_arrow_bytes = 0
    compressed_key_bytes = compressed_projected_bytes = 0
    files_scanned = []
    for file in plan["files"]:
        parquet = pq.ParquetFile(file["original"]["path"])
        file_matches = []
        file_row_base = 0
        for group in range(parquet.num_row_groups):
            metadata = parquet.metadata.row_group(group)
            for index in range(metadata.num_columns):
                column = metadata.column(index)
                if column.path_in_schema == "studyLocusId":
                    compressed_key_bytes += column.total_compressed_size
            offset = 0
            selected_offsets = []
            # First pass scans only the literal join key, with no Python source rows.
            for batch in parquet.iter_batches(batch_size=plan["batch_size"], row_groups=[group], columns=["studyLocusId"], use_threads=False):
                indices, selected = select_exact(batch, plan["case"]["studyLocusId"])
                selected_offsets.extend(offset + i for i in indices)
                key_rows += batch.num_rows
                key_arrow_bytes += batch.nbytes
                offset += batch.num_rows
            assert offset == metadata.num_rows
            if selected_offsets:
                # Project native fields only in row groups already containing exact matches.
                for index in range(metadata.num_columns):
                    column = metadata.column(index)
                    if column.path_in_schema in file["projected_fields"]:
                        compressed_projected_bytes += column.total_compressed_size
                projected_offset = 0
                recovered = []
                for batch in parquet.iter_batches(batch_size=plan["batch_size"], row_groups=[group], columns=file["projected_fields"], use_threads=False):
                    indices, selected = select_exact(batch, plan["case"]["studyLocusId"])
                    projected_rows += batch.num_rows
                    projected_arrow_bytes += batch.nbytes
                    selected_arrow_bytes += selected.nbytes
                    # Only Arrow-selected exact matches cross into Python dictionaries.
                    for local_index, values in zip(indices, selected.to_pylist()):
                        row = projected_offset + local_index
                        recovered.append(row)
                        absent = file["schema_absent_fields"]
                        values = {name: values.get(name) for name in FIELDS}
                        match = {**ROLE, "source": {"original": file["original"], "receipt_archive": file["receipt_archive"], "url": file["source"]["url"], "release_id": "25.09"},
                                 "locator": {"row_group": group, "row": row, "file_row": file_row_base + row, "index_basis": "zero_based_physical_original"},
                                 "native_values": values, "schema_absent_fields": absent,
                                 "source_arrow_types": {field: str(parquet.schema_arrow.field(field).type) if field in parquet.schema_arrow.names else None for field in FIELDS},
                                 "unknowns": plan["unknowns"], "interpretation": "Native linked locus fields; no gene/drug effect inference"}
                        matches.append(match)
                        file_matches.append(match["locator"])
                    projected_offset += batch.num_rows
                assert recovered == selected_offsets and projected_offset == metadata.num_rows
            file_row_base += metadata.num_rows
        files_scanned.append({"basename": file["basename"], "original_sha256": file["original"]["sha256"], "receipt_archive_sha256": file["receipt_archive"]["sha256"], "rows": file["rows"], "exact_matches": len(file_matches)})
    scan_elapsed = time.perf_counter() - started
    cpu_elapsed = time.process_time() - cpu
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert key_rows == plan["collection"]["physical_rows"]
    classification = classify([m["native_values"] for m in matches])
    availability = {field: {"rows": len(matches), "schema_absent": sum(field in m["schema_absent_fields"] for m in matches), "null": sum(field not in m["schema_absent_fields"] and m["native_values"][field] is None for m in matches), "nonnull": sum(m["native_values"][field] is not None for m in matches)} for field in FIELDS}
    preservation_after = {"core_state": {"pin": pin(CORE), "unchanged": pin(CORE) == pre["core_state"]["observed"]}, "files": []}
    for file in plan["files"]:
        preservation_after["files"].append({"basename": file["basename"], "original_unchanged": pin(file["original"]["path"]) == file["original"], "receipt_unchanged": pin(file["receipt_original"]["path"]) == file["receipt_original"], "archive_verified": pin(file["receipt_archive"]["path"]) == file["receipt_archive"]})
    packet_path = private / "credible-completed-join.json"
    packet = {"schema_version": 2, **ROLE, "computed_at_utc": utc(), "cutoff_utc": plan["cutoff_utc"], "frozen_plan": plan_pin, "all_exact_matches": matches, "classification": classification, "descendant_role": "evaluation_only", "scientific_validation": "not_established", "biological_absence": "not_established"}
    write_new(packet_path, packet)
    packet_pin = pin(packet_path)
    resources = {"original_bytes_hashed_during_freeze": plan["collection"]["original_bytes"], "original_bytes_rehashed_before_scan": plan["collection"]["original_bytes"], "original_bytes_rehashed_after_scan": plan["collection"]["original_bytes"], "original_bytes_rehashed_total": plan["collection"]["original_bytes"] * 3, "receipt_bytes_archived": sum(f["receipt_archive"]["bytes"] for f in plan["files"]), "key_column_rows_scanned": key_rows, "key_arrow_logical_bytes": key_arrow_bytes, "projected_matching_row_group_rows": projected_rows, "projected_arrow_logical_bytes": projected_arrow_bytes, "selected_rows": len(matches), "selected_arrow_bytes": selected_arrow_bytes, "packet_bytes": packet_pin["bytes"], "compressed_key_column_bytes_metadata_estimate": compressed_key_bytes, "compressed_matching_group_projected_bytes_metadata_estimate": compressed_projected_bytes, "freeze_verification_elapsed_seconds": plan["verification_elapsed_seconds"], "pre_scan_verification_elapsed_seconds": verification_elapsed, "scan_elapsed_seconds": scan_elapsed, "scan_process_cpu_seconds": cpu_elapsed, "python_traced_peak_bytes": traced_peak, "arrow_allocator_process_peak_bytes": pa.default_memory_pool().max_memory(), "process_peak_rss_bytes": peak_rss(), "process_peak_rss_basis": "Windows GetProcessMemoryInfo PeakWorkingSetSize; process-wide high-water mark including verification, not scan delta", "actual_storage_io_bytes": None, "actual_storage_io_reason": "Physical storage reads/cache effects not instrumented; hashes, Arrow buffers and Parquet compressed-size estimates are logical counters"}
    report = {"schema_version": 2, **ROLE, "status": "COMPLETE_25_FILE_CREDIBLE_SET_EXACT_JOIN", "frozen_plan": plan_pin, "manifest": packet_pin, "collection": plan["collection"], "cutoff_utc": plan["cutoff_utc"], "computed_at_utc": packet["computed_at_utc"], "classification": classification, "matched_field_availability": availability, "files": files_scanned, "preservation_before_scan": pre, "preservation_after_scan": preservation_after, "resources": resources, "self_test": plan["self_test"], "native_value_policy": plan["native_value_policy"], "unknowns": plan["unknowns"], "temporal_policy": plan["temporal_policy"], "receipt_policy": plan["receipt_policy"], "publisher_hash_verified": all(f["publisher_hash_verified"] for f in plan["files"]), "scientific_validation": "not_established", "biological_absence": "not_established", "new_downloads": 0, "model_calls": 0, "provider_spending_usd": 0, "earlier_artifacts_modified": False}
    write_new(REPORT, report)
    print(json.dumps({**ROLE, "report": pin(REPORT), "files": len(files_scanned), "rows_scanned": key_rows, "exact_matches": len(matches), "classification": classification["status"], "packet_bytes": packet_pin["bytes"], "preserved": preservation_after["core_state"]["unchanged"] and all(x["original_unchanged"] and x["receipt_unchanged"] and x["archive_verified"] for x in preservation_after["files"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["self-test", "freeze", "scan"])
    args = parser.parse_args()
    if args.phase == "self-test":
        print(json.dumps(self_test()))
    elif args.phase == "freeze":
        freeze()
    else:
        scan()
