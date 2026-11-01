"""Independent source-only P05 audit. No model/network calls and no raw-value report.

Expected identities, eligibility, mappings and captures are recomputed from the
exact original frame. The producer's audit captures are comparison targets only.
Run only after the producer has exited and the terminal seal/journal is present.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sqlite3
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Path(__file__).resolve().parent
RUN = ROOT / "data/derived/preprint-p05-source-validation-20261101T071713Z"
RAW = Path(r"E:\projects_data\drug_target_agents_data")
sys.path.insert(0, str(ROOT / "src"))
from asof.contracts import Profile, Snapshot, SourceNode
from asof.ingest import peak_memory_bytes
from asof.provenance import InputGraph, catalog_index
from asof.serde import decode
from asof.study.stable_read import checked_path, hash_file, stable_files

READY_SHA = "936f5c1f69c745a0b0fbb787cc22ece00da8fc6a4ec451b034816ca94b5c2225"
PLAN_SHA = "bf4558d695b1de255575e62a2877aa944f060d51b02e12d4cdbdae10955e483b"
BUILDER_SHA = "6b698be8da73b3272017e43afe4b7dc373b48e334b38df0ca596e3473783fd75"
GUARDS = ("evidenceDate", "publicationDate", "publicationYear", "releaseDate", "releaseVersion")
BASE = {
    "gwas_credible_sets": ("id", "targetId", "diseaseId", "diseaseFromSourceMappedId", "variantId", "studyId", "studyLocusId", "datasourceId", "datatypeId"),
    "credible_set": ("studyLocusId", "studyId", "variantId", "chromosome", "position", "beta", "standardError", "pValueMantissa", "pValueExponent", "sampleSize", "zScore"),
    "target": ("id", "approvedSymbol"), "disease": ("id", "name"),
    "hgnc": ("hgnc_id", "symbol", "ensembl_gene_id", "status"),
}
EXPOSED = {"CD276", "OSMR", "ERBB2", "PCSK9", "IL6R", "CFTR", "GLP1R", "SCN9A", "CTLA4"}
REPORT = {"schema_version": 1, "scope": "independent_actual_p05_source_only_stage1",
          "run": RUN.relative_to(ROOT).as_posix(), "checks": {}, "issues": [], "cost": {},
          "model_calls": 0, "network_calls": 0, "new_downloads": 0,
          "raw_scientific_values_in_report": False, "generation_or_gold_use": "forbidden",
          "scientific_claims": "technical source registration only; native study/variant observations; no intervention, causality, n-independence or clinical-validation claim"}


def normalized(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"type": "invalid_native_number", "native_type": "float", "kind": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"}
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return value


def wire(value):
    return json.dumps(normalized(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def document(path):
    return json.loads(Path(path).read_bytes())


def check(label, condition, **details):
    REPORT["checks"][label] = {"pass": bool(condition), **details}
    if not condition:
        REPORT["issues"].append(label)


def require(label, condition, **details):
    check(label, condition, **details)
    if not condition:
        raise AssertionError(label)


def good_text(value):
    return type(value) is str and bool(value) and value == value.strip()


def key_of(row):
    key = tuple(row.get(k) for k in ("targetId", "diseaseId", "studyLocusId"))
    return key if all(good_text(v) and "|" not in v for v in key) else None


def identity_hash(release, key):
    return sha("|".join(("preprint-p05-deterministic-v1", release, *key)).encode())


def interval(value, field):
    import re
    if value is None or value == "":
        return None
    if field == "publicationYear" and type(value) is int:
        value = str(value)
    if type(value) is not str or value != value.strip():
        raise ValueError()
    if field == "publicationYear" and re.fullmatch(r"\d{4}", value) is None:
        raise ValueError()
    if re.fullmatch(r"\d{4}", value):
        y = int(value)
        return datetime(y, 1, 1, tzinfo=timezone.utc), datetime(y, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
    if re.fullmatch(r"\d{4}-\d{2}", value):
        y, m = map(int, value.split("-"))
        return datetime(y, m, 1, tzinfo=timezone.utc), datetime(y, m, calendar.monthrange(y, m)[1], 23, 59, 59, 999999, tzinfo=timezone.utc)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        d = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        return d, d.replace(hour=23, minute=59, second=59, microsecond=999999)
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError()
    return t.astimezone(timezone.utc), t.astimezone(timezone.utc)


def dates(row, cutoff):
    reasons, publication, states = [], [], {}
    for field in GUARDS:
        if field not in row:
            states[field] = "schema_absent"
            continue
        if field == "releaseVersion":
            states[field] = "native_annotation_metadata_only"
            continue
        try:
            bounds = interval(row[field], field)
            if bounds is None:
                states[field] = "unknown"
                continue
            low, high = bounds
            status = "explicit_future" if low > cutoff else "date_precision_unverified" if high > cutoff else "within_cutoff"
            states[field] = status
            if field in ("publicationDate", "publicationYear"):
                publication.append(bounds)
            elif status != "within_cutoff":
                reasons.append(field + "_" + status)
        except (ValueError, TypeError, OverflowError):
            states[field] = "invalid_explicit_date"
            reasons.append(field + "_invalid_explicit_date")
    if publication:
        low, high = max(x[0] for x in publication), min(x[1] for x in publication)
        if low > high:
            reasons.append("publication_date_conflict")
        elif low > cutoff:
            reasons.append("publication_explicit_future")
        elif high > cutoff:
            reasons.append("publication_date_precision_unverified")
    return reasons, states


def eligible(row, indexes, cutoff):
    reasons = []
    if key_of(row) is None:
        reasons.append("unit_identity_missing_or_invalid")
    for field, exact in (("datasourceId", "gwas_credible_sets"), ("datatypeId", "genetic_association")):
        if row.get(field) != exact:
            reasons.append(field + "_not_exact")
    targets = indexes["target"].get(row.get("targetId"), [])
    symbol = None
    if len(targets) != 1:
        reasons.append("target_id_missing_or_nonunique")
    else:
        symbol = targets[0]["values"].get("approvedSymbol")
        if not good_text(symbol) or len(indexes["target_symbol"].get(symbol, [])) != 1:
            reasons.append("target_symbol_missing_or_nonunique")
        hgnc = indexes["hgnc"].get(row.get("targetId"), [])
        if len(hgnc) != 1:
            reasons.append("hgnc_ensembl_missing_or_nonunique")
        else:
            h = hgnc[0]["values"]
            if h.get("symbol") != symbol or h.get("status") != "Approved" or not good_text(h.get("hgnc_id")):
                reasons.append("hgnc_exact_symbol_status_or_id_invalid")
            if len(indexes["hgnc_symbol"].get(symbol, [])) != 1 or len(indexes["hgnc_id"].get(h.get("hgnc_id"), [])) != 1:
                reasons.append("hgnc_symbol_or_id_nonunique")
        if symbol in EXPOSED:
            reasons.append("known_exposed_symbol")
    diseases = indexes["disease"].get(row.get("diseaseId"), [])
    if len(diseases) != 1 or not good_text(diseases[0]["values"].get("name")):
        reasons.append("disease_id_or_name_missing_or_nonunique")
    if row.get("diseaseFromSourceMappedId") not in (None, "", row.get("diseaseId")):
        reasons.append("disease_mapped_id_disagreement")
    date_reasons, states = dates(row, cutoff)
    reasons.extend(date_reasons)
    return sorted(reasons), symbol, "known_exposed" if symbol in EXPOSED else "UNKNOWN", states


def inventory(frame, acquisition):
    records = []
    for family, rows in ((None, frame["files"]), ("credible_set", acquisition["files"])):
        for r in rows:
            m = r.get("metadata", r.get("format", {}))
            item = {"family": family or r["family"], "dataset_id": r["dataset_id"], "release_id": r["release_id"],
                    "path": r["payload_path"], "relative_path": r["relative_path"], "source_url": r["source_url"],
                    "bytes": r["measured_bytes"], "sha256": r.get("sha256", r.get("receipt_recorded_payload_sha256")),
                    "receipt": r["receipt"], "fields": m.get("schema_top_level_fields", m.get("schema_header_fields", [])),
                    "rows": m.get("row_count_metadata_only")}
            if item["family"] == "gwas_credible_sets":
                item["partition"] = r["partition_proof"]
            records.append(item)
    return sorted(records, key=lambda r: (r["family"], r["relative_path"]))


def columns(r, optional=True):
    result = list(BASE[r["family"]])
    if r["family"] == "gwas_credible_sets":
        result += [f for f in GUARDS if f in r["fields"]]
        if optional and "literature" in r["fields"]:
            result.append("literature")
    if r["family"] == "hgnc" and optional:
        result += [f for f in ("gene_group", "gene_group_id") if f in r["fields"]]
    return result


def observe(batch):
    c = REPORT["cost"]
    c["max_arrow_batch_bytes"] = max(c.get("max_arrow_batch_bytes", 0), batch.nbytes)
    c["audit_process_peak_working_set_bytes"] = max(c.get("audit_process_peak_working_set_bytes", 0), peak_memory_bytes())


def process_live(pid):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:
            return False
        raise OSError("Cannot verify producer closure")
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise OSError("Cannot inspect producer state")
        return code.value == 259
    finally:
        kernel.CloseHandle(handle)


def rows(r):
    import pyarrow.parquet as pq
    p = pq.ParquetFile(r["path"])
    require("schema_" + sha(r["relative_path"].encode())[:16], p.schema_arrow.names == r["fields"] and p.metadata.num_rows == r["rows"])
    physical = 0
    for group in range(p.num_row_groups):
        local = 0
        for b in p.iter_batches(batch_size=8192, row_groups=[group], columns=columns(r), use_threads=False):
            observe(b)
            values = b.to_pylist()
            locs = [{"source_relative_path": r["relative_path"], "source_sha256": r["sha256"], "row_group_0based": group,
                     "row_in_group_0based": local + i, "physical_row_0based": physical + local + i} for i in range(b.num_rows)]
            yield b, values, locs
            local += b.num_rows
        require("row_group_coverage_" + sha(r["relative_path"].encode())[:16] + "_" + str(group), local == p.metadata.row_group(group).num_rows)
        physical += local


def load_mappings(records):
    import pyarrow as pa
    import pyarrow.csv as pcsv
    small = {f: [] for f in ("target", "disease", "hgnc")}
    for r in records:
        f = r["family"]
        if f not in small:
            continue
        if f == "hgnc":
            cols = columns(r)
            stream = pcsv.open_csv(r["path"], read_options=pcsv.ReadOptions(block_size=1024**2), parse_options=pcsv.ParseOptions(delimiter="\t"),
                                   convert_options=pcsv.ConvertOptions(include_columns=cols, column_types={c: pa.string() for c in cols}, strings_can_be_null=False))
            position = 0
            for b in stream:
                observe(b)
                for i, v in enumerate(b.to_pylist()):
                    small[f].append({"values": normalized(v), "locator": {"source_relative_path": r["relative_path"], "source_sha256": r["sha256"],
                        "data_record_0based": position + i, "locator_basis": "TSV parsed data record, header excluded; not a text line number"}})
                position += b.num_rows
        else:
            for b, values, locs in rows(r):
                small[f].extend({"values": normalized(v), "locator": loc} for v, loc in zip(values, locs))
    index = {f: defaultdict(list) for f in ("target", "target_symbol", "disease", "hgnc", "hgnc_symbol", "hgnc_id")}
    for r in small["target"]:
        index["target"][r["values"].get("id")].append(r)
        index["target_symbol"][r["values"].get("approvedSymbol")].append(r)
    for r in small["disease"]:
        index["disease"][r["values"].get("id")].append(r)
    for r in small["hgnc"]:
        for name, field in (("hgnc", "ensembl_gene_id"), ("hgnc_symbol", "symbol"), ("hgnc_id", "hgnc_id")):
            index[name][r["values"].get(field)].append(r)
    REPORT["mapping_source_row_counts"] = {f: len(v) for f, v in small.items()}
    return index


def terminal_gate():
    events = [json.loads(line) for line in (RUN / "journal.jsonl").read_bytes().splitlines()]
    previous = None
    for i, event in enumerate(events):
        without = {k: v for k, v in event.items() if k != "sha256"}
        require("journal_event_" + str(i), event["sequence"] == i and event["previous_sha256"] == previous and sha(wire(without)) == event["sha256"])
        previous = event["sha256"]
    require("producer_process_closed", not process_live(events[0]["details"]["owner_pid"]))
    require("terminal_success_and_no_failure", events[-1]["event"] == "build_completed" and (RUN / "seal.json").is_file() and not (RUN / "failure-seal.json").exists())
    seal = document(RUN / "seal.json")
    require("terminal_seal_binding", events[-1]["details"]["seal_sha256"] == sha(wire(seal)) and events[-2]["sha256"] == seal["journal_prefix_sha256"])
    require("seal_protocol_binding", seal["status"] == "completed_source_only_stage1" and seal["ready_sha256"] == READY_SHA and seal["plan_sha256"] == PLAN_SHA)
    REPORT["terminal"] = {"journal_sha256": sha((RUN / "journal.jsonl").read_bytes()), "seal_file_sha256": sha((RUN / "seal.json").read_bytes()),
                          "seal_object_sha256": sha(wire(seal)), "journal_events": len(events), "owner_pid_closed": True}
    return seal, events


def audit():
    import pyarrow
    started = time.monotonic()
    REPORT["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    seal, events = terminal_gate()  # No originals are touched before this gate.
    deadline = time.monotonic() + 1800
    ready = document(ASSETS / "REGISTRY-READY-v3.json")
    plan = document(ASSETS / "REGISTRY-PLAN-DRAFT-v3.json")
    require("frozen_ready_plan_bytes", sha((ASSETS / "REGISTRY-READY-v3.json").read_bytes()) == READY_SHA and sha((ASSETS / "REGISTRY-PLAN-DRAFT-v3.json").read_bytes()) == PLAN_SHA)
    require("current_environment", ready["environment"] == {"interpreter": str(Path(sys.executable).resolve()), "platform": sys.platform, "pyarrow": pyarrow.__version__, "python": platform.python_version()})
    code_good = all(sha((ROOT / p).read_bytes()) == h for p, h in ready["code_sha256"].items())
    require("all_frozen_code_pins", code_good and ready["code_sha256"]["tools/science/prepare_source_validation_set.py"] == BUILDER_SHA, files=len(ready["code_sha256"]))
    docs = {}
    for name, d in plan["neutral_inputs"].items():
        require("neutral_input_pin_" + name, sha(Path(d["path"]).read_bytes()) == d["sha256"])
        docs[name] = document(d["path"])
    records = inventory(docs["frame"], docs["acquisition"])
    require("independent_descriptor_frame", len(records) == 137 and sha(wire(records)) == plan["frame_descriptor_sha256"])
    REPORT["pins"] = {"ready_sha256": READY_SHA, "plan_sha256": PLAN_SHA, "builder_sha256": BUILDER_SHA,
                       "frame_descriptor_sha256": sha(wire(records)), "neutral_inputs": {k: v["sha256"] for k, v in plan["neutral_inputs"].items()}}
    seal_started = time.monotonic()
    expected_paths = {a["path"] for a in seal["artifacts"]} | {"seal.json", "journal.jsonl"}
    actual_paths = {p.relative_to(RUN).as_posix() for p in RUN.rglob("*") if p.is_file()}
    require("sealed_artifact_set_exact", expected_paths == actual_paths, artifacts=len(seal["artifacts"]))
    for a in seal["artifacts"]:
        require("artifact_hash_" + sha(a["path"].encode())[:16], dict(hash_file(RUN / a["path"], deadline)) == {"sha256": a["sha256"], "bytes": a["bytes"]})
    REPORT["cost"]["seal_artifact_hash_seconds"] = time.monotonic() - seal_started
    cp = document(RUN / "selected-case-plan.json")
    coverage = document(RUN / "coverage.json")
    lineage = document(RUN / "lineage.json")
    mapping = document(RUN / "normalized-mapping-provenance.json")
    resource = document(RUN / "resource-report.json")
    cases = cp["cases"]
    cutoff = datetime.fromisoformat(ready["row_guard_cutoff_utc"])
    require("neutral_case_plan_policy", cp["role"] == "neutral_metadata" and cp["agent_visible"] is False and cp["numeric_availability_used"] is False and cp["model_performance_used"] is False and cp["no_replacement"] is True and 1 <= len(cases) <= 12 and cp["row_guard_cutoff_utc"] == ready["row_guard_cutoff_utc"] and cp["plan_sha256"] == PLAN_SHA and cp["selection_seed"] == "preprint-p05-deterministic-v1" and cp["selected_unit_cap"] == 12 and cp["actual_selected_units"] == len(cases))
    original_ids = {"original-" + str(i).zfill(3) for i in range(137)}
    parent_set = original_ids | {"neutral-plan"}
    products_good = True
    for a in lineage["artifact_lineage"]:
        if a["artifact_id"].startswith("transport-receipt-"):
            continue
        products_good &= a["agent_visible"] is False and set(a["parents"]) == parent_set
        products_good &= a["role"] == ("neutral_metadata" if a["artifact_id"] in ("neutral-registry", "neutral-case-plan") else "evaluation_only")
    require("per_artifact_roles_and_original_neutral_parents", products_good and lineage["evaluator_only_ancestors"] == [])
    require("audit_mapping_quarantine", mapping["role"] == "evaluation_only" and mapping["agent_visible"] is False and mapping["qualification"] == "UNQUALIFIED/AUDIT_ONLY" and mapping["downstream_parent_use"] == "forbidden_for_agent_packets_and_references")
    expected_event_order = ["all_originals_verified_before_values", "original_lineage_admitted_before_values"]
    event_names = [e["event"] for e in events]
    stage_events = {e["details"]["stage"]: e["sequence"] for e in events if e["event"] == "build_stage"}
    require("journal_integrity_and_admission_precede_values", all(event_names.count(n) == 1 for n in expected_event_order) and event_names.index(expected_event_order[0]) < event_names.index(expected_event_order[1]) < stage_events["canonical_normalization"] < stage_events["physical_candidate_registration"] < stage_events["deterministic_selection"] < stage_events["selected_original_capture"])
    proof_by_id = {p["source_id"]: p for p in lineage["verified_originals"]}
    node_by_id = {n["source_id"]: n for n in lineage["source_nodes"]}
    require("exact_source_node_and_proof_inventory", set(proof_by_id) == original_ids == set(node_by_id))
    all_paths = [checked_path(RAW, r["relative_path"]) for r in records] + [Path(r["receipt"]["path"]) for r in records]
    with stable_files(all_paths, deadline=deadline):
        hashing_started = time.monotonic()
        source_hashes = []
        receipts_good = proofs_good = roles_good = chronology_good = True
        for i, r in enumerate(records):
            sid = "original-" + str(i).zfill(3)
            require("original_exact_approved_path_" + str(i), checked_path(RAW, r["relative_path"]) == Path(r["path"]))
            measured = dict(hash_file(r["path"], deadline))
            require("original_hash_" + str(i), measured == {"sha256": r["sha256"], "bytes": r["bytes"]})
            source_hashes.append({"source_id": sid, "family": r["family"], **measured})
            receipt_bytes = Path(r["receipt"]["path"]).read_bytes()
            receipt = json.loads(receipt_bytes)
            archive = RUN / "_private/receipts" / (r["receipt"]["sha256"] + ".json")
            receipts_good &= len(receipt_bytes) == r["receipt"]["bytes"] and sha(receipt_bytes) == r["receipt"]["sha256"] and archive.read_bytes() == receipt_bytes
            receipts_good &= receipt["status"] == "completed" and receipt["dataset_id"] == r["dataset_id"] and receipt["release_id"] == r["release_id"] and receipt["sha256"] == r["sha256"] and type(receipt["bytes"]) is int and receipt["bytes"] == r["bytes"] and receipt["url"] == r["source_url"] and receipt["relative_path"].replace("\\", "/") == r["relative_path"]
            p, n = proof_by_id[sid], node_by_id[sid]
            proofs_good &= p["sha256"] == r["sha256"] and p["bytes"] == r["bytes"] and p["path"] == r["path"] and p["relative_path"] == r["relative_path"] and p["receipt_path"] == r["receipt"]["path"] and p["receipt_sha256"] == r["receipt"]["sha256"] and p["receipt_bytes"] == r["receipt"]["bytes"]
            roles_good &= n["role"] == ("reference" if r["family"] == "hgnc" else "agent_evidence") and n["dataset_id"] == r["dataset_id"] and n["release_id"] == r["release_id"] and n["sha256"] == r["sha256"] and n["path"] == r["relative_path"] and n["source_url"] == r["source_url"] and n["receipt_sha256"] == r["receipt"]["sha256"] and n["receipt_path"] == Path(r["receipt"]["path"]).relative_to(RAW).as_posix() and not n["parents"] and n["computed_at"] is None
            completed = datetime.fromisoformat(receipt["completed_at_utc"].replace("Z", "+00:00"))
            chronology_good &= completed.tzinfo is not None and completed <= cutoff and all(n["availability"][k] is None for k in ("first_public_at", "release_public_at", "record_public_at", "annotation_public_at")) and datetime.fromisoformat(n["availability"]["known_public_by"]) == completed and n["availability"]["evidence_ref"] == r["receipt"]["sha256"] and n["availability"]["retrieved_at"] == completed.astimezone(timezone.utc).date().isoformat() and n["availability"]["basis"] == "public_download_receipt" and n["temporal_classification"] == "contemporary_only"
        require("all_exact_raw_receipts_archived_and_identity_checked", receipts_good, receipts=137)
        require("all_original_proofs_and_node_roles", proofs_good and roles_good, sources=137)
        require("receipt_chronology_and_unknown_public_times", chronology_good)
        REPORT["source_hashes"] = source_hashes
        REPORT["cost"]["original_hash_seconds"] = time.monotonic() - hashing_started
        nodes = tuple(decode(SourceNode, n) for n in lineage["source_nodes"])
        snapshot = Snapshot(2, "p05-independent-audit-originals", Profile.CONTEMPORARY, cutoff.date(), False, (), nodes, str(RAW), {}, cutoff)
        graph = InputGraph(snapshot, RUN, catalog_index(docs["catalog"]))
        require("independent_graph_catalog_role_chronology_admission", graph.exclusion(tuple(sorted(original_ids)), SimpleNamespace(cutoff=cutoff)) is None)
        replay_started = time.monotonic()
        indexes = load_mappings(records)
        mapping_good = True
        distinct_mapping_rows = set()
        expected_mapping = []
        for c in cases:
            m = {"case_id": c["case_id"], "target_originals": indexes["target"].get(c["targetId"], []), "disease_originals": indexes["disease"].get(c["diseaseId"], []), "hgnc_originals": indexes["hgnc"].get(c["targetId"], []), "aliases_used": False}
            expected_mapping.append(m)
            for group in ("target_originals", "disease_originals", "hgnc_originals"):
                distinct_mapping_rows.update(wire(v["locator"]) for v in m[group])
        require("source_replayed_exact_canonical_mapping", expected_mapping == mapping["selected_cases"], distinct_original_mapping_rows=len(distinct_mapping_rows))
        db = sqlite3.connect("file:" + (RUN / "candidate-registry.sqlite").as_posix() + "?mode=ro&immutable=1", uri=True)
        db.row_factory = sqlite3.Row
        require("registry_integrity", db.execute("PRAGMA quick_check").fetchone()[0] == "ok")
        metadata = {r[0]: json.loads(r[1]) for r in db.execute("SELECT key,value_json FROM registry_metadata")}
        require("registry_metadata_frozen_protocol_and_role", set(metadata) == {"neutral_protocol"} and metadata["neutral_protocol"]["plan_sha256"] == PLAN_SHA and metadata["neutral_protocol"]["row_guard_cutoff_utc"] == ready["row_guard_cutoff_utc"] and metadata["neutral_protocol"]["role"] == "neutral_metadata" and metadata["neutral_protocol"]["agent_visible"] is False and metadata["neutral_protocol"]["guard_fields"] == list(GUARDS))
        expected_source_rows = {(r["relative_path"], r["sha256"], r["release_id"]) for r in records if r["family"] == "gwas_credible_sets"}
        actual_source_rows = {tuple(r) for r in db.execute("SELECT source_path,source_sha256,release_id FROM source_files")}
        require("registry_exact_source_hash_and_release_bindings", actual_source_rows == expected_source_rows)
        summary = {"physical_rows": db.execute("SELECT COUNT(*) FROM gwas_rows").fetchone()[0], "eligible_physical_rows": db.execute("SELECT COUNT(*) FROM gwas_rows WHERE eligible=1").fetchone()[0],
                   "physical_sources": db.execute("SELECT COUNT(*) FROM source_files").fetchone()[0],
                   "unique_physical_locators": db.execute("SELECT COUNT(*) FROM (SELECT source_id,physical_row FROM gwas_rows GROUP BY source_id,physical_row)").fetchone()[0],
                   "unique_units": db.execute("SELECT COUNT(*) FROM (SELECT unit_hash,target_id,disease_id,study_locus_id FROM gwas_rows WHERE unit_hash IS NOT NULL GROUP BY unit_hash,target_id,disease_id,study_locus_id)").fetchone()[0],
                   "eligible_unique_units": db.execute("SELECT COUNT(*) FROM (SELECT unit_hash,target_id,disease_id,study_locus_id FROM gwas_rows WHERE eligible=1 GROUP BY unit_hash,target_id,disease_id,study_locus_id)").fetchone()[0],
                   "distinct_evidence_ids": db.execute("SELECT COUNT(DISTINCT evidence_id) FROM gwas_rows").fetchone()[0]}
        summary["duplicate_unit_extra_physical_rows"] = summary["physical_rows"] - summary["unique_units"]
        summary["duplicate_evidence_id_extra_rows"] = summary["physical_rows"] - summary["distinct_evidence_ids"]
        REPORT["registry_summary"] = summary
        require("full_physical_registry_footer_frame_and_locator_uniqueness", summary["physical_rows"] == summary["unique_physical_locators"] == 1753850 and summary["physical_sources"] == 100)
        observed_captures = defaultdict(Counter)
        observed_normalizations = {}
        quarantine_good = True
        for c in cases:
            for line in (RUN / "selected-originals" / (c["case_id"] + ".jsonl")).read_bytes().splitlines():
                v = json.loads(line)
                quarantine_good &= v.get("role") == "evaluation_only" and v.get("qualification") == "UNQUALIFIED/AUDIT_ONLY" and v.get("agent_visible") is False and v.get("downstream_parent_use") == "forbidden_for_agent_packets_and_references"
                if v["record_type"] in ("gwas_credible_sets_original", "credible_set_original"):
                    observed_captures[(c["case_id"], v["record_type"])][wire({"values": v["values"], "locator": v["locator"]})] += 1
                elif v["record_type"] == "normalization_originals":
                    observed_normalizations[c["case_id"]] = {k: v[k] for k in ("case_id", "target_originals", "disease_originals", "hgnc_originals", "aliases_used")}
                elif v["record_type"] == "case_header":
                    context = v["unknown_context"]
                    quarantine_good &= v["case"] == c and context["native_numeric_interpretation"] == "study_and_variant_observations_only" and context["gene_or_action_effect"] == "not_inferred" and context["causal_direction"] == "not_inferred" and context["clinical_fields"] == [] and context["probability_features"] == []
                else:
                    quarantine_good = False
        require("every_capture_record_quarantined", quarantine_good)
        require("capture_normalizations_replayed_from_originals", all(observed_normalizations[m["case_id"]] == m for m in expected_mapping))
        by_key = {tuple(c[k] for k in ("targetId", "diseaseId", "studyLocusId")): c for c in cases}
        by_locus = defaultdict(list)
        for c in cases:
            by_locus[c["studyLocusId"]].append(c)
        expected_captures = defaultdict(Counter)
        counts, date_states = Counter(), Counter()
        eligible_keys = Counter()
        eligible_unit_hashes = set()
        mismatches = 0
        distinct_replayed_rows = set(distinct_mapping_rows)
        selected_original_bytes = 0
        for r in records:
            family = r["family"]
            if family not in ("gwas_credible_sets", "credible_set"):
                continue
            if family == "gwas_credible_sets":
                cursor = db.execute("SELECT g.* FROM gwas_rows g JOIN source_files s USING(source_id) WHERE s.source_path=? ORDER BY physical_row", (r["relative_path"],))
            for b, vals, locs in rows(r):
                selected_indices = []
                actual_db = cursor.fetchmany(len(vals)) if family == "gwas_credible_sets" else []
                if family == "gwas_credible_sets" and len(actual_db) != len(vals):
                    mismatches += 1
                counts[family + "_scanned_rows"] += len(vals)
                for i, (v, loc) in enumerate(zip(vals, locs)):
                    if family == "gwas_credible_sets":
                        projected = {k: v[k] for k in columns(r, optional=False)}
                        reasons, symbol, exposure, statuses = eligible(projected, indexes, cutoff)
                        counts["physical_rows"] += 1
                        counts["eligible_physical_rows" if not reasons else "excluded_physical_rows"] += 1
                        counts.update("exclusion:" + reason for reason in reasons)
                        date_states.update(field + ":" + status for field, status in statuses.items())
                        key = key_of(projected)
                        uh = identity_hash(r["release_id"], key) if key else None
                        if not reasons:
                            eligible_unit_hashes.add(uh)
                            rank = (uh, *key, r["release_id"])
                            if rank in eligible_keys or len(eligible_keys) < 12:
                                eligible_keys[rank] += 1
                            elif rank < max(eligible_keys):
                                del eligible_keys[max(eligible_keys)]
                                eligible_keys[rank] = 1
                        a = actual_db[i] if i < len(actual_db) else None
                        expected = (loc["row_group_0based"], loc["row_in_group_0based"], loc["physical_row_0based"], projected.get("id"), projected.get("targetId"), projected.get("diseaseId"), projected.get("studyLocusId"), int(not reasons), wire(reasons).decode(), uh, symbol, exposure, wire(projected).decode())
                        actual = tuple(a[k] for k in ("row_group", "row_in_group", "physical_row", "evidence_id", "target_id", "disease_id", "study_locus_id", "eligible", "exclusion_reasons", "unit_hash", "approved_symbol", "exposure_status", "identity_json")) if a else None
                        mismatches += actual != expected
                        matches = [by_key[key]] if key in by_key else []
                    else:
                        matches = by_locus.get(v.get("studyLocusId"), [])
                    if matches:
                        selected_indices.append(i)
                        distinct_replayed_rows.add(wire(loc))
                    for c in matches:
                        expected_captures[(c["case_id"], family + "_original")][wire({"values": v, "locator": loc})] += 1
                if selected_indices:
                    import pyarrow as pa
                    selected_set = set(selected_indices)
                    selected_original_bytes += b.filter(pa.array([i in selected_set for i in range(b.num_rows)])).nbytes
            if family == "gwas_credible_sets":
                mismatches += cursor.fetchone() is not None
        require("full_original_gwas_registry_identity_eligibility_and_hash_replay", mismatches == 0, replayed_rows=counts["physical_rows"], mismatches=mismatches)
        ranked = sorted(eligible_keys)[:12]
        expected_cases = [{"case_id": "p05-" + str(i + 1).zfill(2), "unit_hash": t[0], "targetId": t[1], "diseaseId": t[2], "studyLocusId": t[3], "release_id": t[4], "eligible_physical_rows": eligible_keys[t], "exposure_status": "UNKNOWN", "availableAt": None, "publicationDate": None, "historical_eligibility": "not_verified"} for i, t in enumerate(ranked)]
        require("independent_full_universe_first_identity_hash_selection", expected_cases == cases and len(eligible_unit_hashes) == summary["eligible_unique_units"], selected=len(cases), eligible_unique_units=len(eligible_unit_hashes))
        all_capture_keys = set(expected_captures) | set(observed_captures)
        require("every_selected_original_match_and_conflict_retained", all(expected_captures[k] == observed_captures[k] for k in all_capture_keys), distinct_replayed_original_rows=len(distinct_replayed_rows), selected_captured_physical_matches=sum(sum(v.values()) for v in expected_captures.values()))
        selected_coverage_good = True
        for c in cases:
            for family in ("gwas_credible_sets", "credible_set"):
                bucket = expected_captures[(c["case_id"], family + "_original")]
                total = sum(bucket.values())
                distinct = len({wire(json.loads(payload)["values"]) for payload in bucket})
                status = "missing_retained_no_replacement" if distinct == 0 else "multiple_distinct_rows_retained_unresolved" if distinct > 1 else "one_distinct_projection_all_physical_matches_retained"
                selected_coverage_good &= coverage["selected"][c["case_id"]][family] == {"physical_matches": total, "distinct_projected_rows": distinct, "status": status}
                selected_coverage_good &= coverage["counters"].get(c["case_id"] + ":" + family + "_matches", 0) == total
            for field in ("studyId", "variantId"):
                native = {}
                for family in ("gwas_credible_sets", "credible_set"):
                    native[family] = {wire(json.loads(p)["values"].get(field)) for p in expected_captures[(c["case_id"], family + "_original")] if good_text(json.loads(p)["values"].get(field))}
                expected_status = "unknown_missing_native_identity" if not native["gwas_credible_sets"] or not native["credible_set"] else "exact_native_identity_agreement" if len(native["gwas_credible_sets"]) == len(native["credible_set"]) == 1 and native["gwas_credible_sets"] == native["credible_set"] else "native_identity_disagreement_or_multiplicity_retained_unresolved"
                selected_coverage_good &= coverage["selected"][c["case_id"]]["native_identity_context"][field]["status"] == expected_status
        require("source_replayed_selected_coverage_and_native_conflicts", selected_coverage_good)
        require("all_credible_files_and_rows_independently_scanned", counts["credible_set_scanned_rows"] == 2862043 and len([r for r in records if r["family"] == "credible_set"]) == 25)
        require("coverage_counters_from_independent_sources", all(coverage["counters"].get(k) == v for k, v in counts.items()))
        require("selected_arrow_bytes_replayed", selected_original_bytes == resource["selected_arrow_bytes_cumulative"], bytes=selected_original_bytes)
        REPORT["source_replay_counts"] = dict(counts)
        REPORT["date_guard_status_counts"] = dict(date_states)
        REPORT["selected_coverage_counts"] = {c["case_id"]: {f: sum(expected_captures[(c["case_id"], f + "_original")].values()) for f in ("gwas_credible_sets", "credible_set")} for c in cases}
        REPORT["selected_missingness"] = {f: sum(v is None for bucket, items in expected_captures.items() for payload, multiplicity in items.items() if bucket[1] == "credible_set_original" for k, v in json.loads(payload)["values"].items() if k == f for _ in range(multiplicity)) for f in ("beta", "standardError", "sampleSize", "studyId", "variantId")}
        REPORT["producer_resource_report"] = resource
        REPORT["cost"]["full_original_replay_seconds"] = time.monotonic() - replay_started
        db.close()
    REPORT["cost"]["total_wall_seconds"] = time.monotonic() - started
    REPORT["cost"]["physical_io_bytes"] = None
    REPORT["cost"]["physical_io_status"] = "not_measured; original compressed frame and hash bytes known, OS cache/physical traffic unmeasured"
    REPORT["limitations"] = ["Contemporary downloaded-source chronology only; historical availability and publication times unknown.",
        "Original producer behavior is evidenced by frozen code, artifacts and journal; audit cannot establish OS-level isolation or absence of unlogged activity.",
        "Code and plan are externally frozen and commit-addressed; producer output contains their pins rather than archived source-code/plan copies.",
        "Full original GWAS row identities/eligibility/hashes and all credible-set selected matches were replayed; unselected credible scientific values were projected transiently but not scientifically validated.",
        "Audit/producer process peak working sets are separate process-lifetime measurements; physical disk traffic unmeasured."]
    REPORT["status"] = "PASS_SOURCE_ONLY_TECHNICAL_AUDIT" if not REPORT["issues"] else "FAIL_SOURCE_ONLY_TECHNICAL_AUDIT"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-closed", action="store_true", required=True)
    args = parser.parse_args()
    try:
        audit()
    except BaseException as exc:
        REPORT["status"] = "INCOMPLETE_OR_FAILED_AUDIT"
        REPORT["error_class"] = type(exc).__name__
        # Exception messages from source tools can include values/paths. Keep this report sanitized.
        if isinstance(exc, AssertionError):
            REPORT["failed_check"] = str(exc)
    REPORT["audit_script_sha256"] = sha(Path(__file__).read_bytes())
    output = ASSETS / "REGISTRY-AUDIT-v3.json"
    if output.exists():
        raise RuntimeError("Audit report already exists; preserve history")
    output.write_bytes(wire(REPORT) + b"\n")
    print(json.dumps({"status": REPORT["status"], "checks": len(REPORT["checks"]), "issues": REPORT["issues"], "error_class": REPORT.get("error_class"), "report_sha256": sha(output.read_bytes()), "cost": REPORT["cost"]}))
    return 0 if REPORT["status"] == "PASS_SOURCE_ONLY_TECHNICAL_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
