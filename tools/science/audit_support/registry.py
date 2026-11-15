"""Selected source-audit helpers; see PROVENANCE.md for scope and origin."""
from __future__ import annotations
import calendar
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from tether_engine.ingest import peak_memory_bytes
from tether_engine.study.stable_read import checked_path, hash_file, stable_files
ROOT = Path(__file__).resolve().parents[3]
RAW = Path(r"E:\projects_data\drug_target_agents_data")
REPORT = {"checks": {}, "issues": [], "cost": {}}


GUARDS = ("evidenceDate", "publicationDate", "publicationYear", "releaseDate", "releaseVersion")


BASE = {
    "gwas_credible_sets": ("id", "targetId", "diseaseId", "diseaseFromSourceMappedId", "variantId", "studyId", "studyLocusId", "datasourceId", "datatypeId"),
    "credible_set": ("studyLocusId", "studyId", "variantId", "chromosome", "position", "beta", "standardError", "pValueMantissa", "pValueExponent", "sampleSize", "zScore"),
    "target": ("id", "approvedSymbol"), "disease": ("id", "name"),
    "hgnc": ("hgnc_id", "symbol", "ensembl_gene_id", "status"),
}


EXPOSED = {"CD276", "OSMR", "ERBB2", "PCSK9", "IL6R", "CFTR", "GLP1R", "SCN9A", "CTLA4"}


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
