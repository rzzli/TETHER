"""Frozen two-file local credible-set join; evaluator-only, no acquisition."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import tracemalloc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = Path("E:/projects_data/drug_target_agents_data")
PLAN = HERE / "CREDIBLE-JOIN-PLAN-v1.json"
REPORT = HERE / "CREDIBLE-JOIN-REPORT-v1.json"
STATE = RAW / "manifests/core-25-09-chembl35-2026-10-10-state.json"
STATE_SHA = "f7f238e92db035232f8273a18ec2182d99ad6571d570bff50b3899dbc56c15ea"
GWAS = ROOT / "data/benchmark/gold_evidence/preprint-p02-gwas-20261101T025951484714Z/gwas-availability.json"
GWAS_SHA = "b700a763613927e808b475243c0c94c09d4f29a15204f543183496fbec434a99"
HELPER_SHA = "c59ee418be8f303e02cf6b6332a2f7b31cde3307f0b3970679b106e4e1f4d050"
FIELDS = "studyLocusId studyId variantId chromosome position beta zScore pValueMantissa pValueExponent standardError sampleSize".split()
NUMERIC = "beta zScore pValueMantissa pValueExponent standardError sampleSize".split()
RECEIPTS = {
    "ot25-f01fc0d46d1d4872d84ab6e5": "563935e9a220b025d64db9dcbbc894a2b1a655e9637b4cc11b30617379b15d36",
    "ot25-99b6086482ae7ebeb936f2fe": "e24ca9ae8d87acd80d8d775de2961f63dafaf3f8a332cc9d77f34932c0a5129b",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def helpers():
    path = HERE / "prototype.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError("Pinned pure hash/save helpers changed")
    spec = importlib.util.spec_from_file_location("p02_credible_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_path(relative):
    candidate = RAW / relative
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(RAW.resolve()):
        raise ValueError("Original path escaped the read-only raw root")
    for part in (candidate,) + tuple(candidate.parents):
        if getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse point in original path")
    return candidate.resolve()


def verify(h, expected):
    path = Path(expected["path"])
    if h.pin(path) != expected:
        raise ValueError("Pinned input changed: " + str(path))
    return path


def availability(records):
    return {field: {"rows": len(records), "schema_absent": sum(field not in r for r in records),
                    "null": sum(field in r and r[field] is None for r in records),
                    "nonnull": sum(field in r and r[field] is not None for r in records)} for field in FIELDS}


def freeze(h):
    import pyarrow.parquet as pq
    if PLAN.exists() or REPORT.exists():
        raise FileExistsError("Preserve existing plan/report; no automatic rerun")
    state = h.bound(STATE, STATE_SHA)
    gwas = h.bound(GWAS, GWAS_SHA)
    ctla = next(u for u in gwas["units"] if u["unit_id"] == "ctla4-efo_0000384")
    if gwas["role"] != "evaluation_only" or len(ctla["selected_records"]) != 1:
        raise ValueError("Expected exactly one evaluator-only CTLA4 linkage record")
    previous = ctla["selected_records"][0]
    locus = previous["record"]["studyLocusId"]
    if not isinstance(locus, str) or not locus:
        raise ValueError("Missing exact linkage key; no replacement")
    catalog_path = ROOT / "data/catalog/sources.json"
    catalog = json.loads(catalog_path.read_bytes())
    dataset = next(d for d in catalog["datasets"] if d["dataset_id"] == "ot_credible_set")
    entries = sorted((r for r in state["results"] if r["dataset_id"] == "ot_credible_set" and r["status"] == "completed"), key=lambda r: r["relative_path"])
    if {r["receipt_id"] for r in entries} != set(RECEIPTS) or "agent_evidence" not in dataset["roles"]:
        raise ValueError("Two-file selection or catalog permission changed")
    output = ROOT / "data/benchmark/gold_evidence" / ("preprint-p02-credible-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir()
    h.save(output / "attempt.json", {"role": "evaluation_only", "stage": "metadata_only_freeze", "created_at_utc": now(), "raw_rows_read": 0})
    files = []
    for entry in entries:
        original = raw_path(entry["relative_path"])
        receipt = raw_path("manifests/receipts/" + entry["receipt_id"] + ".json")
        receipt_pin = h.pin(receipt)
        if receipt_pin["sha256"] != RECEIPTS[entry["receipt_id"]] or original.stat().st_size != entry["bytes"]:
            raise ValueError("Transport metadata changed before freeze")
        parquet = pq.ParquetFile(original)  # Footer/schema only; no row values.
        files.append({"state_result": entry, "original": {"path": str(original), "bytes": entry["bytes"], "sha256": entry["sha256"]},
                      "receipt": receipt_pin, "rows": parquet.metadata.num_rows,
                      "row_groups": [parquet.metadata.row_group(g).num_rows for g in range(parquet.num_row_groups)],
                      "schema_sha256": hashlib.sha256(parquet.schema_arrow.serialize().to_pybytes()).hexdigest(),
                      "projected_fields": [f for f in FIELDS if f in parquet.schema_arrow.names]})
    if len(files) != 2 or sum(f["original"]["bytes"] for f in files) != 157880681:
        raise ValueError("Bounded local inventory changed")
    plan = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False, "created_at_utc": now(), "raw_rows_read_before_freeze": 0,
            "parents": [h.pin(STATE), h.pin(catalog_path), h.pin(GWAS), h.pin(HERE / "prototype.py"), h.pin(Path(__file__))],
            "private_output": str(output), "files": files, "fields": FIELDS, "numeric_availability_fields": NUMERIC,
            "case": {"unit_id": ctla["unit_id"], "target_id": ctla["target_id"], "disease_id": ctla["disease_id"], "studyLocusId": locus, "previous_locator": previous["locator"]},
            "matching": "Exact studyLocusId only; retain every matching physical row with original locators; no target or effect inference",
            "parser_control": {"file": files[0]["original"]["path"], "row_group": 0, "row": 0, "role": "real_parser_control_only_not_a_target_case", "selection": "First file by original relative path, original row zero, frozen before values"},
            "collection": {"local_completed_files": 2, "catalog_snapshot_expected_files": dataset["acquisition_snapshot"]["expected_files"], "scope": "Partial local 2-of-25 inventory; no global locus or biological absence claim"},
            "receipt_policy": "Copy exact current transport receipt bytes into private hash archive before parsing; preserve raw receipts and state",
            "numeric_policy": "Exact native values, units unknown; no transformations, inferred direction, MR, feature/scorer or clinical interpretation",
            "descendant_role": "evaluation_only_for_all_descendants", "new_downloads": 0, "model_calls": 0}
    proof = h.save(PLAN, plan)
    h.save(output / "PLAN-FROZEN.json", {"role": "evaluation_only", "frozen_at_utc": now(), "plan": proof, "raw_rows_read": 0})
    return {"plan": proof, "files": 2, "row_values_read": 0, "private_output": str(output)}


def run(h):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    if REPORT.exists() or pa.__version__ != "21.0.0":
        raise ValueError("Preserve existing report and use the qualified Arrow environment")
    plan = json.loads(PLAN.read_bytes()); output = Path(plan["private_output"])
    frozen = json.loads((output / "PLAN-FROZEN.json").read_bytes())
    if h.pin(PLAN) != frozen["plan"] or plan["fields"] != FIELDS:
        raise ValueError("Frozen plan changed")
    for parent in plan["parents"]:
        verify(h, parent)
    if (output / "RUN-STARTED.json").exists():
        raise FileExistsError("No retry of an existing attempt")
    h.save(output / "RUN-STARTED.json", {"role": "evaluation_only", "started_at_utc": now(), "plan": frozen["plan"]})
    started, cpu = time.perf_counter(), time.process_time()
    tracemalloc.start(); matches, proofs, control = [], [], None
    counters = {"original_bytes_rehashed": 0, "receipt_bytes_archived": 0, "projected_row_group_rows": 0, "selected_join_arrow_bytes": 0, "projected_compressed_column_bytes_estimate": 0}
    try:
        archive = output / "receipt-archive"; archive.mkdir()
        for info in plan["files"]:
            receipt_path = raw_path(info["receipt"]["path"]); receipt_bytes = receipt_path.read_bytes()
            if hashlib.sha256(receipt_bytes).hexdigest() != info["receipt"]["sha256"]:
                raise ValueError("Current transport receipt changed")
            archived = archive / (info["receipt"]["sha256"] + ".json")
            with archived.open("xb") as stream:
                stream.write(receipt_bytes)
            if archived.read_bytes() != receipt_bytes:
                raise ValueError("Receipt archive differs")
            receipt = json.loads(archived.read_bytes())  # Parse the retained copy only.
            if receipt != info["state_result"] or receipt["publisher_hash_verified"] is not False or receipt["release_id"] != "25.09":
                raise ValueError("Receipt and frozen current state differ")
            original = raw_path(info["original"]["path"]); before = original.stat(); verify(h, info["original"])
            counters["original_bytes_rehashed"] += before.st_size; counters["receipt_bytes_archived"] += len(receipt_bytes)
            parquet = pq.ParquetFile(original)
            if hashlib.sha256(parquet.schema_arrow.serialize().to_pybytes()).hexdigest() != info["schema_sha256"] or parquet.metadata.num_rows != info["rows"]:
                raise ValueError("Original footer/schema changed")
            found = 0
            for group in range(parquet.num_row_groups):
                table = parquet.read_row_group(group, columns=info["projected_fields"])
                if "studyLocusId" not in table.column_names:
                    raise ValueError("Join key absent from schema")
                indices = pc.indices_nonzero(pc.fill_null(pc.equal(table["studyLocusId"], plan["case"]["studyLocusId"]), False))
                selected = table.take(indices)  # Filter in Arrow before Python conversion.
                counters["projected_row_group_rows"] += table.num_rows; counters["selected_join_arrow_bytes"] += selected.nbytes
                metadata = parquet.metadata.row_group(group)
                counters["projected_compressed_column_bytes_estimate"] += sum(metadata.column(i).total_compressed_size for i in range(metadata.num_columns) if metadata.column(i).path_in_schema.split(".")[0] in info["projected_fields"])
                for row_index, record in zip(indices.to_pylist(), selected.to_pylist()):
                    matches.append({"record": record, "locator": {"original_sha256": info["original"]["sha256"], "row_group": group, "row": row_index}}); found += 1
                if str(original) == plan["parser_control"]["file"] and group == 0:
                    control = {"record": table.slice(0, 1).to_pylist()[0], "locator": {"original_sha256": info["original"]["sha256"], "row_group": 0, "row": 0}, "role": "real_parser_control_only_not_a_target_case"}
            after = original.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise ValueError("Original changed during read")
            verify(h, info["receipt"])
            proofs.append({"original": info["original"], "current_transport_receipt": info["receipt"], "archived_receipt": h.pin(archived), "publisher_hash_verified": False, "matched_rows": found})
        for parent in plan["parents"]:
            verify(h, parent)
        if control is None or sum(p["matched_rows"] for p in proofs) != len(matches):
            raise ValueError("Missing parser control or incomplete join accounting")
        resources = {**counters, "elapsed_seconds": time.perf_counter() - started, "process_cpu_seconds": time.process_time() - cpu,
                     "python_traced_peak_bytes": tracemalloc.get_traced_memory()[1], "arrow_allocator_peak_bytes": pa.default_memory_pool().max_memory(),
                     "process_peak_rss_bytes": None, "actual_storage_io_bytes": None}
        manifest = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False, "computed_at_utc": now(), "parents": [frozen["plan"]] + plan["parents"],
                    "source_proofs": proofs, "case": plan["case"], "all_matching_rows": matches, "parser_control": control, "resources": resources,
                    "raw_value_units": "unknown; no transformation or inference", "descendant_role": "evaluation_only_for_all_descendants", "scientific_validation": "not_established"}
        manifest_pin = h.save(output / "credible-join.json", manifest)
        control_fields = [f for f in NUMERIC if control["record"].get(f) is not None]
        report = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False, "status": "COMPLETE_BOUNDED_CREDIBLE_SET_JOIN",
                  "frozen_plan": frozen["plan"], "manifest": manifest_pin, "collection": plan["collection"], "join_rows": len(matches),
                  "join_status": "linked_locus_rows_available" if matches else "missing_join_input_in_partial_local_collection",
                  "matched_field_availability": availability([m["record"] for m in matches]),
                  "parser_control": {"role": control["role"], "selection": plan["parser_control"]["selection"], "rows": 1, "numeric_nonnull_fields": control_fields, "availability": availability([control["record"]])},
                  "interpretation": "Joined values describe a linked locus, not a gene/drug effect. Parser control is separate and adds no target case.",
                  "biological_absence": "not_established", "resources": resources, "publisher_hash_verified": False, "scientific_validation": "not_established",
                  "process_RSS_and_physical_IO": "Unmeasured; allocator peaks and logical counters are separate", "new_downloads": 0, "model_calls": 0, "provider_spending_usd": 0}
        report_pin = h.save(REPORT, report)
        h.save(output / "terminal.json", {"role": "evaluation_only", "status": report["status"], "report": report_pin, "manifest": manifest_pin, "finished_at_utc": now()})
        return {"report": report_pin, "manifest": manifest_pin, "join_rows": len(matches), "control_numeric_nonnull_fields": control_fields, "resources": resources}
    except BaseException as error:
        failure = {"role": "evaluation_only", "status": "FAILED_STOPPED_NO_RETRY", "plan": frozen["plan"], "error_type": type(error).__name__, "message": str(error), "completed_files": len(proofs), "resources": counters, "zero_match_claim_authorized": False, "model_calls": 0}
        h.save(output / "failure.json", failure)
        if not REPORT.exists():
            h.save(REPORT, failure)
        raise
    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--run", action="store_true"); args = parser.parse_args()
    if args.freeze == args.run:
        parser.error("Choose exactly one of --freeze or --run")
    print(json.dumps((freeze if args.freeze else run)(helpers()), sort_keys=True, allow_nan=False))
