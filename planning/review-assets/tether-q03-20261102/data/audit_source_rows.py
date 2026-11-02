"""Bounded source-only Q03 feasibility, exact local slice, no LLM/backend calls.

Selection policy is fixed in SOURCE-SELECTION-POLICY.json before this script runs.
Every decoded row traversal is counted. Source files and metadata are read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import ctypes
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from audit_outputs import reserve_run_directories, save_new_json

HERE = Path(__file__).resolve().parent
WORK = Path(__file__).resolve().parents[4]
CACHE = WORK / "data/cache/tether-q03"
EVIDENCE_KEYS = ["id", "datasourceId", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId"]
EVIDENCE_DETAILS = ["variantRsId", "ancestry", "ancestryId", "cohortDescription", "cohortId", "cohortShortName", "studyCases", "studySampleSize", "beta", "betaConfidenceIntervalLower", "betaConfidenceIntervalUpper", "oddsRatio", "oddsRatioConfidenceIntervalLower", "oddsRatioConfidenceIntervalUpper", "pValueMantissa", "pValueExponent", "statisticalMethod"]
CS_FIELDS = ["studyLocusId", "studyId", "variantId", "studyType", "chromosome", "position", "region", "beta", "zScore", "pValueMantissa", "pValueExponent", "effectAlleleFrequencyFromSource", "standardError", "subStudyDescription", "qualityControls", "finemappingMethod", "credibleSetIndex", "credibleSetlog10BF", "purityMeanR2", "purityMinR2", "locusStart", "locusEnd", "sampleSize", "confidence", "isTransQtl"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def valid(value):
    return value is not None and value != ""


def save(path: Path, value) -> None:
    save_new_json(path, value)


def peak_working_set_bytes() -> int:
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = ctypes.c_void_p
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    get_memory.restype = ctypes.c_int
    if not get_memory(get_process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.PeakWorkingSetSize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Fresh output ID; an existing ID is never reused")
    args = parser.parse_args()
    output, cache = reserve_run_directories(args.run_id, HERE / "runs", CACHE / "runs")
    started = time.perf_counter()
    save(output / "RUN-START.json", {"run_id": args.run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(), "executed_script_sha256": sha256(Path(__file__)), "output_helper_sha256": sha256(HERE / "audit_outputs.py"), "report_directory": str(output), "cache_directory": str(cache)})
    policy_path = HERE / "SOURCE-SELECTION-POLICY.json"
    policy = json.loads(policy_path.read_text())
    spec_path = Path(policy["task_spec_path"])
    if sha256(spec_path) != policy["task_spec_sha256"]:
        raise RuntimeError("Frozen task specification changed")
    if sha256(HERE / "SOURCE-INVENTORY.json") != policy["universe_inventory_sha256"]:
        raise RuntimeError("Predeclared source universe changed")
    inv = json.loads((HERE / "SOURCE-INVENTORY.json").read_text())
    evidence_files = inv["inventory"]["gwas_credible_sets_evidence"]["files"]
    cs_files = inv["inventory"]["credible_set"]["files"]
    if sum(f["row_count"] for f in evidence_files) > policy["max_evidence_rows"]:
        raise RuntimeError("Evidence scan bound exceeded")
    if sum(f["row_count"] for f in cs_files) > policy["max_credible_set_rows"]:
        raise RuntimeError("Credible-set scan bound exceeded")

    # Provenance reconciliation: expected queue -> actual full files -> local receipts.
    queue = json.loads((WORK / "data/manifests/private/core-2026-10-10-queue.json").read_text())
    expected_evidence = {r["relative_path"].replace("\\", "/") for r in queue["files"] if "/evidence/sourceId=gwas_credible_sets/" in r["relative_path"].replace("\\", "/")}
    admitted_evidence = {r["relative_path"] for r in evidence_files}
    if admitted_evidence != expected_evidence:
        raise RuntimeError("Admitted evidence does not exactly match named queue partition")
    catalog = json.loads((WORK / "data/catalog/sources.json").read_text(encoding="utf-8"))
    expected_cs = {p.replace("\\", "/") for d in catalog["datasets"] if d["dataset_id"] == "ot_credible_set" for p in d["acquisition_snapshot"]["relative_paths"]}
    if {r["relative_path"] for r in cs_files} != expected_cs:
        raise RuntimeError("Admitted credible-set files differ from the selected25.09 catalog paths")
    verified = []
    for record in evidence_files + cs_files:
        receipt = record["receipt"]
        if not receipt or receipt["release_id"] != "25.09" or not record["receipt_size_match"]:
            raise RuntimeError("Missing/wrong-release/size-mismatched receipt")
        digest = sha256(Path(record["path"]))
        if digest != receipt["sha256"]:
            raise RuntimeError("Local source digest mismatch")
        verified.append({"relative_path": record["relative_path"], "bytes": record["bytes"], "sha256": digest, "receipt_id": receipt["receipt_id"], "release_id": receipt["release_id"], "publisher_url": receipt["url"]})
    save(output / "SOURCE-FILE-MANIFEST.json", {"release": "25.09", "evidence_coverage": "all 100 locally acquired shards, exact equality with the named acquisition queue partition", "credible_set_coverage": "25 locally acquired shards, catalog paths and matching local receipts", "hash_kind": "independently recomputed SHA-256 versus local acquisition receipts; not publisher authenticity", "files": verified})
    hashing_seconds = time.perf_counter() - started

    scan_counts = Counter()
    logical_bytes = Counter()
    group_locators = defaultdict(list)
    explicit = policy.get("prebound_ids")
    if explicit:
        disease, target_a, target_b = explicit["diseaseId"], explicit["targetA"], explicit["targetB"]
    else:
        # Keep at most two loci per key: this is sufficient for fixed >=2-union eligibility.
        candidates = defaultdict(set)
        for rec in evidence_files:
            pf = pq.ParquetFile(rec["path"])
            for batch in pf.iter_batches(batch_size=8192, columns=["datasourceId", "targetId", "diseaseId", "studyLocusId"], use_threads=False):
                scan_counts["selection_evidence_rows"] += batch.num_rows
                logical_bytes["selection_evidence"] += batch.nbytes
                for row in batch.to_pylist():
                    if row["datasourceId"] != "gwas_credible_sets":
                        raise RuntimeError("Source partition contains a different datasourceId")
                    d, t, locus = row["diseaseId"], row["targetId"], row["studyLocusId"]
                    if valid(d) and valid(t):
                        seen = candidates[(d, t)]
                        if valid(locus) and len(seen) < 2:
                            seen.add(locus)
        by_disease = defaultdict(list)
        for d, t in candidates:
            by_disease[d].append(t)
        choice = None
        for d in sorted(by_disease):
            for a, b in combinations(sorted(by_disease[d]), 2):
                if len(candidates[d, a] | candidates[d, b]) >= 2:
                    choice = d, a, b
                    break
            if choice:
                break
        if choice is None:
            save(output / "SOURCE-FEASIBILITY.json", {"feasible": False, "reason": "No eligible fixed-semantics pair in admitted exhaustive evidence universe", "scan_counts": dict(scan_counts)})
            return
        disease, target_a, target_b = choice
    if target_a == target_b:
        raise RuntimeError("Target pair must be distinct")
    binding = {"diseaseId": disease, "targetA": target_a, "targetB": target_b, "selection_policy_sha256": sha256(policy_path), "task_spec_sha256": policy["task_spec_sha256"], "selection_rule": policy["selection_rule"], "selected_at_utc": datetime.now(timezone.utc).isoformat()}
    save(output / "SOURCE-INPUT-BINDING.json", binding)

    # Exact admitted slice; positions refer to physical row order within Parquet row groups.
    evidence_rows = []
    for rec in evidence_files:
        pf = pq.ParquetFile(rec["path"])
        for rg in range(pf.num_row_groups):
            offset = 0
            for batch in pf.iter_batches(batch_size=8192, row_groups=[rg], columns=EVIDENCE_KEYS, use_threads=False):
                scan_counts["slice_evidence_rows"] += batch.num_rows
                logical_bytes["slice_evidence"] += batch.nbytes
                for i, row in enumerate(batch.to_pylist()):
                    if row["datasourceId"] != "gwas_credible_sets":
                        raise RuntimeError("Source partition contains a different datasourceId")
                    if row["diseaseId"] == disease and row["targetId"] in [target_a, target_b]:
                        row["_locator"] = {"relative_path": rec["relative_path"], "row_group": rg, "row_in_group": offset + i}
                        evidence_rows.append(row)
                        group_locators[rec["path"], rg].append(row)
                offset += batch.num_rows
    for (path, rg), rows in group_locators.items():
        table = pq.ParquetFile(path).read_row_group(rg, columns=EVIDENCE_DETAILS, use_threads=False)
        scan_counts["evidence_detail_rows_decoded"] += table.num_rows
        logical_bytes["evidence_details"] += table.nbytes
        indices = [r["_locator"]["row_in_group"] for r in rows]
        details = table.take(pa.array(indices)).to_pylist()
        for row, more in zip(rows, details):
            row.update(more)
    loci = {r["studyLocusId"] for r in evidence_rows if valid(r["studyLocusId"])}
    if not all(any(r["targetId"] == t for r in evidence_rows) for t in [target_a, target_b]) or len(loci) < 2:
        raise RuntimeError("Bound input does not satisfy pre-frozen eligibility")

    cs_rows = []
    cs_locators = defaultdict(list)
    for rec in cs_files:
        pf = pq.ParquetFile(rec["path"])
        for rg in range(pf.num_row_groups):
            offset = 0
            for batch in pf.iter_batches(batch_size=8192, row_groups=[rg], columns=["studyLocusId"], use_threads=False):
                scan_counts["credible_set_key_rows"] += batch.num_rows
                logical_bytes["credible_set_keys"] += batch.nbytes
                for i, key in enumerate(batch.column(0).to_pylist()):
                    if key in loci:
                        row = {"_locator": {"relative_path": rec["relative_path"], "row_group": rg, "row_in_group": offset + i}}
                        cs_rows.append(row)
                        cs_locators[rec["path"], rg].append(row)
                offset += batch.num_rows
    for (path, rg), rows in cs_locators.items():
        table = pq.ParquetFile(path).read_row_group(rg, columns=CS_FIELDS, use_threads=False)
        scan_counts["credible_set_detail_rows_decoded"] += table.num_rows
        logical_bytes["credible_set_details"] += table.nbytes
        indices = [r["_locator"]["row_in_group"] for r in rows]
        details = table.take(pa.array(indices)).to_pylist()
        for row, more in zip(rows, details):
            row.update(more)

    labels = []
    for table, fields, identifiers in [("target", ["id", "approvedSymbol"], {target_a, target_b}), ("disease", ["id", "name"], {disease})]:
        for rec in inv["inventory"][table]["files"]:
            pf = pq.ParquetFile(rec["path"])
            for rg in range(pf.num_row_groups):
                offset = 0
                for batch in pf.iter_batches(batch_size=8192, row_groups=[rg], columns=fields, use_threads=False):
                    scan_counts[table + "_label_rows"] += batch.num_rows
                    logical_bytes[table + "_labels"] += batch.nbytes
                    for i, row in enumerate(batch.to_pylist()):
                        if row["id"] in identifiers:
                            row["_source_table"] = table
                            row["_locator"] = {"relative_path": rec["relative_path"], "row_group": rg, "row_in_group": offset + i}
                            labels.append(row)
                    offset += batch.num_rows

    save(cache / "source-slice-evidence.json", evidence_rows)
    save(cache / "source-slice-credible-set.json", cs_rows)
    save(cache / "source-slice-labels.json", labels)
    # Feasibility counts only; this is a scientific source audit, not an agent study.
    matched = Counter(r["studyLocusId"] for r in cs_rows)
    cs_by_key = defaultdict(list)
    evidence_by_id = defaultdict(list)
    for row in cs_rows:
        cs_by_key[row["studyLocusId"]].append(row)
    for row in evidence_rows:
        if valid(row["id"]):
            evidence_by_id[row["id"]].append(row)
    cs_projection = lambda row: tuple(row.get(k) for k in ["studyLocusId", "studyId", "variantId", "studyType"])
    evidence_projection = lambda row: tuple(row.get(k) for k in EVIDENCE_KEYS)
    ambiguous_keys = {k for k, rows in cs_by_key.items() if len({cs_projection(r) for r in rows}) > 1}
    duplicate_ids = {k for k, rows in evidence_by_id.items() if len(rows) > 1}
    conflicting_ids = {k for k in duplicate_ids if len({evidence_projection(r) for r in evidence_by_id[k]}) > 1}
    comparisons = {field: Counter() for field in ["studyId", "variantId"]}
    for row in evidence_rows:
        key = row["studyLocusId"]
        links = cs_by_key.get(key, [])
        for field in comparisons:
            if not links or key in ambiguous_keys or not valid(row.get(field)) or not valid(links[0].get(field)):
                comparisons[field]["not_assessable"] += 1
            else:
                comparisons[field]["equal" if row[field] == links[0][field] else "different"] += 1
    result = {"feasible": True, "task_nature": "source-composition reporting and identity verification; no independent-genetic-support inference", "binding": binding, "source_universe": {"evidence_shards": len(evidence_files), "credible_set_shards": len(cs_files)}, "scan_counts": dict(scan_counts), "selected_counts": {"evidence_rows": len(evidence_rows), "target_a_rows": sum(r["targetId"] == target_a for r in evidence_rows), "target_b_rows": sum(r["targetId"] == target_b for r in evidence_rows), "distinct_nonnull_referenced_loci": len(loci), "credible_set_rows": len(cs_rows), "unmatched_loci": sum(matched[x] == 0 for x in loci), "multiply_matched_loci": sum(matched[x] > 1 for x in loci), "labels": len(labels)}, "evidence_missing_counts": {f: sum(not valid(r.get(f)) for r in evidence_rows) for f in EVIDENCE_KEYS + EVIDENCE_DETAILS}, "credible_set_missing_counts": {f: sum(not valid(r.get(f)) for r in cs_rows) for f in CS_FIELDS}, "source_slice_files": [str(cache / name) for name in ["source-slice-evidence.json", "source-slice-credible-set.json", "source-slice-labels.json"]], "limitations": ["No study table payload at named queued25.09 path and no completed receipt", "No explicit genome-build/reference-allele/alternate-allele fields in inspected schemas", "Exact study/variant equality does not establish allele harmonization", "Provider study labels and credible-set IDs do not establish participant/cohort independence", "Live documentation does not certify historical release invariants", "Selected source projections are not an inference-engine/backend experiment"]}
    result["quality_counts"] = {"duplicate_evidence_ids": len(duplicate_ids), "conflicting_evidence_ids": len(conflicting_ids), "conflicting_credible_set_keys": len(ambiguous_keys), "missing_evidence_ids": sum(not valid(r["id"]) for r in evidence_rows), "missing_study_locus_keys": sum(not valid(r["studyLocusId"]) for r in evidence_rows), "cs_missing_or_not_gwas_study_type": sum(r["studyType"] != "gwas" for r in cs_rows)}
    result["identity_comparison_counts"] = {f: dict(c) for f, c in comparisons.items()}
    result["resource_use"] = {"elapsed_seconds": time.perf_counter() - started, "hashing_seconds": hashing_seconds, "source_payload_bytes_hashed": sum(r["bytes"] for r in verified), "arrow_logical_bytes_by_phase": dict(logical_bytes), "arrow_logical_bytes_total": sum(logical_bytes.values()), "peak_process_working_set_bytes": peak_working_set_bytes(), "batch_rows": 8192, "logical_byte_definition": "Sum Arrow decoded column nbytes; repeated scan phases counted again, excludes Python object overhead; peak process working set is Windows process high-water mark"}
    save(output / "SOURCE-FEASIBILITY.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
