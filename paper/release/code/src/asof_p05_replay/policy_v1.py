"""P09 explicit-root replay of the frozen P05 original-source policy.

This is a separately versioned re-expression, not a replacement for frozen P05
authorization or private-archive verification.  No comparison/answer input is
accepted.  The caller supplies independently authenticated neutral policy bytes.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import time
from types import SimpleNamespace

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index, check_role
from asof.serde import ContractError, canonical, decode, encode, fingerprint, freeze, parse_json
from asof.study.proofs import _relative
from asof.study.source_fact_adapters import _json_value
from asof.study.source_fact_sources import FIELD_FAMILIES, _publication, validate_task
from asof.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files

CUTOFF = "2026-11-01T07:16:26.101448+00:00"
METHOD = "p09.source_policy.v1"
SEED = "preprint-p05-deterministic-v1"
EXPOSED = frozenset(("CD276", "OSMR", "ERBB2", "PCSK9", "IL6R", "CFTR", "GLP1R", "SCN9A", "CTLA4"))
LIMITS = {"compressed_input_bytes": 4 * 1024**3, "files": 137,
          "output_bytes": 512 * 1024**2, "case_product_bytes": 64 * 1024**2,
          "seconds": 1200, "batch_rows": 8192, "matching_rows_per_case": 100000}
GWAS = ("id", "targetId", "diseaseId", "diseaseFromSourceMappedId", "variantId", "studyId",
        "studyLocusId", "datasourceId", "datatypeId")
GWAS_FIELDS = ("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")
CREDIBLE_IDENTITY = ("studyLocusId", "studyId", "variantId")
MEASUREMENTS = ("beta", "standardError", "pValueMantissa", "pValueExponent")
GUARD_FIELDS = ("evidenceDate", "publicationDate", "publicationYear", "releaseDate", "releaseVersion")
CORE_DATE_FIELDS = ("publicationDate", "evidenceDate", "annotationDate", "publicationYear")
SMALL = {"target": ("id", "approvedSymbol"), "disease": ("id", "name"),
         "hgnc": ("hgnc_id", "symbol", "ensembl_gene_id", "status")}
OPTIONAL = {"hgnc": ("gene_group", "gene_group_id")}
UNKNOWN_CONTEXT = {
    "units_and_scales": "unknown: no native unit/scale field is supplied by the frozen projection; null is not a dimensionless or log-odds claim",
    "effect_and_reference_alleles": "unknown: no supplied native allele context; variantId spelling is not interpreted",
    "ancestry": "unknown: study table is absent; ancestry is not transferred from GWAS to credible statistics",
    "genome_build": "unknown: not literally supplied; not inferred from variantId",
    "target_namespace_version": "unknown: Ensembl release/version is not supplied by the original target/HGNC identifiers",
    "indication_namespace_version": "unknown: upstream ontology version is not supplied by the original disease identifiers",
    "study_identity_if_missing": "unknown: locus equality does not establish study or variant identity",
    "scientific_scope": "native study/variant statistics at a source locus only; no gene/action, intervention, causal, clinical or independent-study claim",
    "historical_eligibility": "not_verified; receipt-bound contemporary assessment only",
}


def need(condition, message):
    if not condition:
        raise ContractError(message)


def utc(value):
    need(type(value) is str, "An explicit UTC timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("Invalid explicit UTC timestamp") from error
    need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "Timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def text(value):
    return type(value) is str and bool(value) and value == value.strip()


def source_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"type": "invalid_native_number", "native_type": "float",
                "kind": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"}
    if isinstance(value, Mapping):
        return {key: source_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [source_value(item) for item in value]
    return value


def unit_key(row):
    values = tuple(row.get(key) for key in ("targetId", "diseaseId", "studyLocusId"))
    return values if all(text(value) and "|" not in value for value in values) else None


def unit_hash(release, key):
    import hashlib
    need(text(release) and "|" not in release and len(key) == 3 and
         all(text(value) and "|" not in value for value in key), "Invalid exact unit identity")
    return hashlib.sha256("|".join((SEED, release, *key)).encode()).hexdigest()


def source_date_interval(value, field):
    if value is None or value == "":
        return None, None, "unknown"
    if field == "publicationYear" and type(value) is int:
        value = str(value)
    need(type(value) is str and value == value.strip(), "Invalid explicit date type/spelling")
    need(field != "publicationYear" or re.fullmatch(r"\d{4}", value), "Invalid explicit publication year")
    if re.fullmatch(r"\d{4}", value):
        return (datetime(int(value), 1, 1, tzinfo=timezone.utc),
                datetime(int(value), 12, 31, 23, 59, 59, 999999, timezone.utc), "year")
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = (int(part) for part in value.split("-"))
        return (datetime(year, month, 1, tzinfo=timezone.utc),
                datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 999999, timezone.utc), "month")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.fromisoformat(value)
        return (day.replace(tzinfo=timezone.utc),
                day.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc), "day")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(parsed.tzinfo is not None, "Explicit datetime must supply timezone")
    instant = parsed.astimezone(timezone.utc)
    return instant, instant, "timestamp"


def interval_status(lower, upper, cutoff):
    return "explicit_future" if lower > cutoff else "date_precision_unverified" if upper > cutoff else "within_cutoff"


def date_guard(row, cutoff=None):
    cutoff = cutoff or datetime.now(timezone.utc)
    need(cutoff.tzinfo is not None, "Date guard cutoff must supply timezone")
    fields, reasons, intervals = {}, [], {}
    for field in GUARD_FIELDS:
        if field not in row:
            fields[field] = {"status": "schema_absent", "native": None, "upper_bound_utc": None}
            continue
        native = row[field]
        if field == "releaseVersion":
            fields[field] = {"status": "native_annotation_metadata_only", "native": source_value(native), "upper_bound_utc": None}
            continue
        try:
            lower, upper, precision = source_date_interval(native, field)
            status = "unknown" if lower is None else interval_status(lower, upper, cutoff)
            fields[field] = {"status": status, "native": source_value(native),
                             "lower_bound_utc": lower.isoformat() if lower else None,
                             "upper_bound_utc": upper.isoformat() if upper else None, "precision": precision}
            if lower is not None:
                intervals[field] = (lower, upper)
                if field not in ("publicationDate", "publicationYear") and status != "within_cutoff":
                    reasons.append(field + "_" + status)
        except (ContractError, ValueError, TypeError, OverflowError):
            fields[field] = {"status": "invalid_explicit_date", "native": source_value(native), "upper_bound_utc": None}
            reasons.append(field + "_invalid_explicit_date")
    publication = [intervals[key] for key in ("publicationDate", "publicationYear") if key in intervals]
    event = {"status": "unknown", "lower_bound_utc": None, "upper_bound_utc": None}
    if publication:
        lower, upper = max(item[0] for item in publication), min(item[1] for item in publication)
        if lower > upper:
            event["status"] = "publication_date_conflict"
            reasons.append("publication_date_conflict")
        else:
            status = interval_status(lower, upper, cutoff)
            event = {"status": status, "lower_bound_utc": lower.isoformat(), "upper_bound_utc": upper.isoformat(),
                     "resolution": "intersection_of_supplied_publication_precision_intervals"}
            if status != "within_cutoff":
                reasons.append("publication_" + status)
    return {"cutoff_utc": cutoff.isoformat(), "fields": fields, "publication_event": event, "exclusion_reasons": reasons,
            "purpose": "eligibility_and_provenance_only_not_primary_facts_or_rank"}


def mapping_index(small):
    indexes = {key: defaultdict(list) for key in ("target", "target_symbol", "disease", "hgnc", "hgnc_symbol", "hgnc_id")}
    for record in small["target"]:
        indexes["target"][record["values"].get("id")].append(record)
        indexes["target_symbol"][record["values"].get("approvedSymbol")].append(record)
    for record in small["disease"]:
        indexes["disease"][record["values"].get("id")].append(record)
    for record in small["hgnc"]:
        row = record["values"]
        indexes["hgnc"][row.get("ensembl_gene_id")].append(record)
        indexes["hgnc_symbol"][row.get("symbol")].append(record)
        indexes["hgnc_id"][row.get("hgnc_id")].append(record)
    return indexes


def eligibility(row, indexes, *, cutoff=None):
    reasons = []
    if unit_key(row) is None:
        reasons.append("unit_identity_missing_or_invalid")
    if row.get("datasourceId") != "gwas_credible_sets":
        reasons.append("datasourceId_not_exact")
    if row.get("datatypeId") != "genetic_association":
        reasons.append("datatypeId_not_exact")
    targets = indexes["target"].get(row.get("targetId"), ())
    symbol = None
    if len(targets) != 1:
        reasons.append("target_id_missing_or_nonunique")
    else:
        symbol = targets[0]["values"].get("approvedSymbol")
        if not text(symbol) or len(indexes["target_symbol"].get(symbol, ())) != 1:
            reasons.append("target_symbol_missing_or_nonunique")
        matches = indexes["hgnc"].get(row.get("targetId"), ())
        if len(matches) != 1:
            reasons.append("hgnc_ensembl_missing_or_nonunique")
        else:
            hgnc = matches[0]["values"]
            if hgnc.get("symbol") != symbol or hgnc.get("status") != "Approved" or not text(hgnc.get("hgnc_id")):
                reasons.append("hgnc_exact_symbol_status_or_id_invalid")
            if len(indexes["hgnc_symbol"].get(symbol, ())) != 1 or len(indexes["hgnc_id"].get(hgnc.get("hgnc_id"), ())) != 1:
                reasons.append("hgnc_symbol_or_id_nonunique")
        if symbol in EXPOSED:
            reasons.append("known_exposed_symbol")
    diseases = indexes["disease"].get(row.get("diseaseId"), ())
    if len(diseases) != 1 or not text(diseases[0]["values"].get("name")):
        reasons.append("disease_id_or_name_missing_or_nonunique")
    mapped = row.get("diseaseFromSourceMappedId")
    if mapped not in (None, "") and mapped != row.get("diseaseId"):
        reasons.append("disease_mapped_id_disagreement")
    guard = date_guard(row, cutoff)
    reasons.extend(guard["exclusion_reasons"])
    return {"eligible": not reasons, "exclusion_reasons": sorted(reasons), "date_guard": guard,
            "approved_symbol": symbol, "exposure_status": "known_exposed" if symbol in EXPOSED else "UNKNOWN"}


def normalization_proof(case, gwas, indexes, *, cutoff=None):
    cutoff = utc(CUTOFF) if cutoff is None else cutoff
    need(bool(gwas), "No eligible physical GWAS anchor remains; retain blocked case")
    for record in gwas:
        need(unit_key(record["values"]) == unit_key(case) and
             eligibility(record["values"], indexes, cutoff=cutoff)["eligible"], "Original anchor normalization failed")
    target, disease, hgnc = (indexes["target"][case["targetId"]], indexes["disease"][case["diseaseId"]], indexes["hgnc"][case["targetId"]])
    need(len(target) == len(disease) == len(hgnc) == 1, "Original canonical mapping is not unique")
    return {"method": "fresh exact original canonical target/HGNC/disease replay", "target_id_from_raw_GWAS": case["targetId"],
            "indication_id_from_raw_GWAS": case["diseaseId"], "no_alias_or_variant_inference": True,
            "target_original": target[0], "disease_original": disease[0], "hgnc_original": hgnc[0],
            "upstream_namespace_versions": {"target": "unknown", "indication": "unknown"}, "other_exposure": "UNKNOWN"}


def native_representability(record, case=None, *, cutoff=None):
    row = record["values"]
    _publication(row, utc(CUTOFF) if cutoff is None else cutoff)
    if case is not None:
        for name, expected in (("targetId", "targetId"), ("target_id", "targetId"), ("diseaseId", "diseaseId"), ("indication_id", "diseaseId")):
            need(name not in row or row[name] is None or row[name] == case[expected], "Native automatic scope field disagrees")
    for name, value in row.items():
        _json_value(value)
        if name in MEASUREMENTS and value is not None and value != "" and value != [] and value != {}:
            need(type(value) in (int, float) and (type(value) is not float or math.isfinite(value)), "Native measurement requires finite int/float excluding Boolean")
            need(name != "pValueExponent" or type(value) is int, "Native pValueExponent requires int")


def build_task(case, groups, *, cutoff=CUTOFF):
    records, fields, keys = [], [], {"gwas_credible_sets": [], "credible_set": []}
    for family in ("gwas_credible_sets", "credible_set"):
        for number, original in enumerate(groups[family]):
            key = ("gwas" if family == "gwas_credible_sets" else "credible") + f"-{number:04d}"
            keys[family].append(key)
            row = original["values"]
            required = ("targetId", "diseaseId", "studyLocusId") if family == "gwas_credible_sets" else ("studyLocusId",)
            identity = {name: row[name] for name in required}
            identity.update({name: row[name] for name in ("id", "studyId", "variantId") if name in row and row[name] is not None and row[name] != ""})
            records.append({"record_key": key, "source_id": original["source_id"], "locator": original["locator"], "identity": identity})
            names = GWAS_FIELDS if family == "gwas_credible_sets" else CREDIBLE_IDENTITY + MEASUREMENTS
            for name in names:
                fields.append({"record_key": key, "field": name, "family": FIELD_FAMILIES[name],
                    "group": ("measurement:" if name in MEASUREMENTS else "identity:") + key,
                    "unit_field": None, "empty_policy": "unknown"})
    task = {"schema_version": 1, "task_id": "p05-" + case["case_id"] + "-native-locus-v1",
        "scope": {"target_id": case["targetId"], "indication_id": case["diseaseId"],
            "target_namespace_version": "unknown", "indication_namespace_version": "unknown", "action": None, "modality": None, "tissue": None},
        "cutoff": cutoff, "profile": "contemporary_assessment", "primary_families": ["reported_measurement"],
        "records": records, "fields": fields,
        "joins": [{"join_id": "locus:" + key, "left_record": key, "left_field": "studyLocusId",
            "right_records": keys["credible_set"], "right_field": "studyLocusId", "cardinality": "one_to_many", "inventory_status": "complete"}
            for key in keys["gwas_credible_sets"]],
        "collection": {"status": "selected_records", "reason": "All eligible selected physical rows in the pinned original frame only; source-locus reporting, no biological absence claim."}}
    return encode(validate_task(task))


def validate_policy(policy):
    policy = encode(policy)
    need(type(policy) is dict and set(policy) == {"schema_version", "method", "cutoff", "inventory", "expected_frame", "catalog", "snapshot", "cases", "tasks", "exposed_symbols", "limits"}, "Unknown source policy fields")
    need(type(policy["schema_version"]) is int and policy["schema_version"] == 1 and policy["method"] == METHOD and policy["cutoff"] == CUTOFF, "Unsupported source policy version/cutoff")
    limits = policy["limits"]
    need(type(limits) is dict and set(limits) == set(LIMITS) and all(type(limits[k]) is int and 0 < limits[k] <= v for k, v in LIMITS.items()), "Unsupported source-policy limits")
    need(type(policy["exposed_symbols"]) is list and len(policy["exposed_symbols"]) == len(EXPOSED) and set(policy["exposed_symbols"]) == EXPOSED, "Frozen exposure exclusions changed")
    inventory = policy["inventory"]
    need(type(inventory) is list and 0 < len(inventory) <= limits["files"] and sum(item["bytes"] for item in inventory) <= limits["compressed_input_bytes"], "Complete source frame exceeds bounds")
    families = {*SMALL, "gwas_credible_sets", "credible_set"}
    expected_frame = policy["expected_frame"]
    need(type(expected_frame) is dict and set(expected_frame) == families, "All five original source families required")
    paths, receipts = [], []
    for number, item in enumerate(inventory):
        need(type(item) is dict and set(item) == {"source_id", "family", "dataset_id", "release_id", "relative_path", "sha256", "bytes", "fields", "rows", "source_url", "role", "receipt"}, "Unknown original descriptor fields")
        need(item["source_id"] == f"original-{number:03d}" and item["family"] in families and item["role"] == ("reference" if item["family"] == "hgnc" else "agent_evidence"), "Original ordering/family/role changed")
        for key in ("dataset_id", "release_id", "source_url"):
            need(text(item[key]), "Original identity missing")
        for proof in (item, item["receipt"]):
            need(type(proof) is dict and re.fullmatch(r"[0-9a-f]{64}", proof.get("sha256", "")) and type(proof.get("bytes")) is int and proof["bytes"] > 0, "Exact original/receipt bytes and SHA required")
            _relative(proof["relative_path"])
        need(set(item["receipt"]) == {"relative_path", "sha256", "bytes"}, "Unknown receipt descriptor fields")
        need(type(item["fields"]) is list and all(text(field) for field in item["fields"]) and len(set(item["fields"])) == len(item["fields"]), "Invalid complete schema fields")
        need(item["rows"] is None or type(item["rows"]) is int and item["rows"] >= 0, "Invalid original footer count")
        need(item["family"] == "hgnc" or type(item["rows"]) is int, "Parquet footer count required")
        paths.append(item["relative_path"]); receipts.append(item["receipt"]["relative_path"])
    need(list(zip((i["family"] for i in inventory), paths)) == sorted(zip((i["family"] for i in inventory), paths)), "Original inventory ordering changed")
    need(len(set(p.casefold() for p in paths + receipts)) == len(paths) + len(receipts), "Duplicate original/receipt paths")
    for family in families:
        rows = [item for item in inventory if item["family"] == family]
        expected = expected_frame[family]
        need(type(expected) is dict and set(expected) == {"files", "bytes", "rows"} and rows and
             type(expected["files"]) is int and type(expected["bytes"]) is int and
             expected["files"] == len(rows) and expected["bytes"] == sum(item["bytes"] for item in rows), "Exact family frame changed")
        need(expected["rows"] is None or type(expected["rows"]) is int and expected["rows"] >= 0, "Invalid expected row count")
        if all(item["rows"] is not None for item in rows):
            need(expected["rows"] == sum(item["rows"] for item in rows), "Exact family footer count changed")
    cases = policy["cases"]
    need(type(cases) is list and 1 <= len(cases) <= 12 and type(policy["tasks"]) is dict, "Fixed selected cases required")
    for case in cases:
        need(type(case) is dict and set(case) == {"case_id", "targetId", "diseaseId", "studyLocusId", "release_id", "unit_hash"} and re.fullmatch(r"p05-\d{2}", case["case_id"]), "Invalid neutral case fields")
        key = unit_key(case)
        need(key is not None and case["release_id"] == "25.09" and case["unit_hash"] == unit_hash("25.09", key), "Neutral unit identity/rank hash differs")
    need(len({case["case_id"] for case in cases}) == len(cases) == len({case["unit_hash"] for case in cases}) and set(policy["tasks"]) == {case["case_id"] for case in cases}, "Duplicate/missing case/task inventory")
    for case in cases:
        task = validate_task(policy["tasks"][case["case_id"]])
        need(task["cutoff"] == CUTOFF and task["scope"]["target_id"] == case["targetId"] and task["scope"]["indication_id"] == case["diseaseId"], "Neutral task routing differs")
    snapshot = decode(Snapshot, policy["snapshot"])
    need(snapshot.raw_root is None and not snapshot.artifacts and len(snapshot.sources) == len(inventory), "Only root-neutral full original snapshot permitted")
    return policy, snapshot


def _projection(item, *, small=False):
    family = item["family"]
    required = SMALL[family] if small else GWAS if family == "gwas_credible_sets" else CREDIBLE_IDENTITY + MEASUREMENTS + ("chromosome", "position", "sampleSize")
    need(set(required) <= set(item["fields"]), "Frozen literal source schema lacks required columns: " + family)
    extra = OPTIONAL.get(family, ()) if small else GUARD_FIELDS + CORE_DATE_FIELDS + ("targetId", "target_id", "diseaseId", "indication_id")
    return tuple(required) + tuple(key for key in dict.fromkeys(extra) if key in item["fields"] and key not in required)


def _fresh_snapshot(inventory, receipts, raw_root):
    nodes = []
    for item, receipt in zip(inventory, receipts):
        observed = utc(receipt["completed_at_utc"])
        availability = Availability(None, None, None, None, observed.date(), "public_download_receipt",
            "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, item["receipt"]["sha256"])
        nodes.append(SourceNode(item["source_id"], item["dataset_id"], item["release_id"], item["relative_path"], item["sha256"], item["role"],
            availability, TemporalClass.CONTEMPORARY, item["source_url"], receipt_path=item["receipt"]["relative_path"], receipt_sha256=item["receipt"]["sha256"]))
    cutoff = utc(CUTOFF)
    return Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(raw_root),
                    {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)


def _receipt_identity(receipt, item):
    need(type(receipt) is dict, "Receipt is not a JSON object")
    for name, expected in {"status": "completed", "dataset_id": item["dataset_id"], "release_id": item["release_id"],
                           "sha256": item["sha256"], "bytes": item["bytes"], "url": item["source_url"]}.items():
        need(type(receipt.get(name)) is (int if name == "bytes" else str) and receipt[name] == expected, "Receipt identity differs: " + name)
    relative = receipt.get("relative_path")
    need(type(relative) is str and relative.replace("\\", "/") == item["relative_path"], "Receipt relative path differs")
    need(utc(receipt.get("completed_at_utc")) <= utc(CUTOFF), "Receipt is later than the information cutoff")


@contextmanager
def policy_session(policy, originals_root, deadline, progress=None):
    """Hold actual Windows sharing locks through caller generation/core replay.

    ``progress(event, **metadata)`` is trusted caller instrumentation, never a
    function selected by serialized configuration. Original values stay local.
    """
    import hashlib
    import pyarrow as pa
    import pyarrow.csv as csv
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    need(pa.__version__ == "21.0.0", "Native replay requires PyArrow 21.0.0")
    deadline_check(deadline)
    started = time.monotonic()
    policy, declared = validate_policy(policy)
    limits, inventory = policy["limits"], policy["inventory"]
    deadline = min(deadline, started + limits["seconds"])
    root = Path(originals_root)
    need(root.is_absolute(), "Explicit absolute original root required")
    paths = {item["source_id"]: checked_path(root, item["relative_path"]) for item in inventory}
    receipt_paths = {item["source_id"]: checked_path(root, item["receipt"]["relative_path"]) for item in inventory}
    runtime_declared = replace(declared, raw_root=str(root))
    index = catalog_index(policy["catalog"])
    graph = InputGraph(runtime_declared, root, index)
    need(graph.exclusion(tuple(graph.nodes), SimpleNamespace(cutoff=utc(CUTOFF))) is None, "Full original graph is not eligible")
    for item, node in zip(inventory, declared.sources):
        check_role(item["dataset_id"], item["role"], index)
        need(not node.parents and node.computed_at is None and node.method_id is None and node.method_version is None and
             (node.source_id, node.dataset_id, node.release_id, node.path, node.sha256, node.role, node.source_url, node.receipt_path, node.receipt_sha256) ==
             (item["source_id"], item["dataset_id"], item["release_id"], item["relative_path"], item["sha256"], item["role"], item["source_url"], item["receipt"]["relative_path"], item["receipt"]["sha256"]), "Source snapshot/descriptor identity differs")
    resources = {"logical_bytes_hashed": 0, "logical_original_compressed_bytes_scanned": 0, "max_batch_arrow_bytes": 0,
                 "physical_io_bytes": None, "enforcement": "cooperative Windows sharing locks and checkpoints; not an OS sandbox"}
    def checkpoint(event="checkpoint", **metadata):
        deadline_check(deadline)
        if progress is not None:
            progress(event, **metadata)
        deadline_check(deadline)
    def observe(batch):
        resources["max_batch_arrow_bytes"] = max(resources["max_batch_arrow_bytes"], batch.nbytes)
        checkpoint("arrow_batch", rows=batch.num_rows, arrow_bytes=batch.nbytes)
    def batches(item, columns):
        source = pq.ParquetFile(paths[item["source_id"]])
        readers.callback(source.close)
        try:
            need(source.schema_arrow.names == item["fields"] and source.metadata.num_rows == item["rows"], "Original schema/footer differs")
            physical = 0
            for group in range(source.num_row_groups):
                offset = 0
                for batch in source.iter_batches(batch_size=limits["batch_rows"], row_groups=[group], columns=list(columns), use_threads=False):
                    observe(batch)
                    yield batch, group, offset, physical
                    offset += batch.num_rows
                need(offset == source.metadata.row_group(group).num_rows, "Incomplete physical row-group scan")
                physical += offset
            need(physical == item["rows"], "Incomplete physical file scan")
            resources["logical_original_compressed_bytes_scanned"] += item["bytes"]
        finally:
            source.close()
    with stable_files(tuple(paths.values()) + tuple(receipt_paths.values()), deadline=deadline), ExitStack() as readers:
        for item in inventory:
            proof = dict(hash_file(paths[item["source_id"]], deadline))
            need(proof == {"sha256": item["sha256"], "bytes": item["bytes"]}, "Complete original checksum/size differs")
            resources["logical_bytes_hashed"] += proof["bytes"]
            checkpoint("original_payload_verified", source_id=item["source_id"], bytes=proof["bytes"])
        receipts = []
        for item in inventory:
            payload = read_file(receipt_paths[item["source_id"]], deadline, 1024**2)
            need(len(payload) == item["receipt"]["bytes"] and hashlib.sha256(payload).hexdigest() == item["receipt"]["sha256"], "Exact original receipt bytes differ")
            resources["logical_bytes_hashed"] += len(payload)
            receipt = parse_json(payload); _receipt_identity(receipt, item); receipts.append(receipt)
            checkpoint("original_receipt_verified", source_id=item["source_id"], bytes=len(payload))
        snapshot = _fresh_snapshot(inventory, receipts, root)
        need(canonical(encode(replace(snapshot, raw_root=None))) == canonical(policy["snapshot"]), "Receipt-derived neutral snapshot differs")
        fresh_graph = InputGraph(snapshot, root, index)
        need(fresh_graph.exclusion(tuple(fresh_graph.nodes), SimpleNamespace(cutoff=utc(CUTOFF))) is None, "Fresh original graph is not eligible")
        proofs = []
        for item, node in zip(inventory, snapshot.sources):
            proofs.append({"artifact_id": node.source_id, "dataset_id": node.dataset_id, "release_id": node.release_id,
                "path": node.path, "sha256": node.sha256, "role": node.role, "parents": [], "bytes": item["bytes"],
                "availability": encode(node.availability), "temporal_classification": node.temporal_classification.value,
                "path_scope": "raw", "receipt_path": node.receipt_path, "receipt_sha256": node.receipt_sha256,
                "receipt_bytes": item["receipt"]["bytes"]})
        checkpoint("all_originals_admitted", original_files=len(inventory))
        small = {family: [] for family in SMALL}
        for item in inventory:
            family = item["family"]
            if family not in small:
                continue
            columns = _projection(item, small=True)
            if family == "hgnc":
                with paths[item["source_id"]].open("rb") as stream:
                    header = stream.readline(1024**2 + 1)
                need(len(header) <= 1024**2 and header.decode("utf-8-sig").rstrip("\r\n").split("\t") == item["fields"], "Original HGNC header differs")
                csv_input = readers.enter_context(paths[item["source_id"]].open("rb"))
                source = csv.open_csv(csv_input, read_options=csv.ReadOptions(block_size=1024**2),
                    parse_options=csv.ParseOptions(delimiter="\t"), convert_options=csv.ConvertOptions(include_columns=list(columns),
                        column_types={key: pa.string() for key in columns}, strings_can_be_null=False))
                readers.callback(source.close)
                need(source.schema.names == list(columns), "Original HGNC projection differs")
                position = 0
                for batch in source:
                    for start in range(0, batch.num_rows, limits["batch_rows"]):
                        piece = batch.slice(start, limits["batch_rows"]); observe(piece)
                        for offset, row in enumerate(piece.to_pylist()):
                            small[family].append({"values": row, "locator": {"source_relative_path": item["relative_path"], "source_sha256": item["sha256"],
                                "data_record_0based": position + start + offset, "locator_basis": "TSV parsed data record, header excluded; not a text line number"}})
                    position += batch.num_rows
                if item["rows"] is not None:
                    need(position == item["rows"], "Original HGNC row count differs")
                source.close()
                csv_input.close()
                resources["logical_original_compressed_bytes_scanned"] += item["bytes"]
            else:
                for batch, group, offset, physical in batches(item, columns):
                    small[family].extend({"values": row, "locator": {"source_relative_path": item["relative_path"], "source_sha256": item["sha256"],
                        "row_group_0based": group, "row_in_group_0based": offset + index, "physical_row_0based": physical + offset + index}}
                        for index, row in enumerate(batch.to_pylist()))
        indexes = mapping_index(small)
        selected = {case["case_id"]: {"gwas_credible_sets": [], "credible_set": []} for case in policy["cases"]}
        excluded = {case["case_id"]: [] for case in policy["cases"]}
        for item in inventory:
            family = item["family"]
            if family not in ("gwas_credible_sets", "credible_set"):
                continue
            for batch, group, offset, physical in batches(item, _projection(item)):
                for case in policy["cases"]:
                    mask = pc.equal(batch.column("studyLocusId"), case["studyLocusId"])
                    if family == "gwas_credible_sets":
                        mask = pc.and_(mask, pc.and_(pc.equal(batch.column("targetId"), case["targetId"]), pc.equal(batch.column("diseaseId"), case["diseaseId"])))
                    indices = pc.indices_nonzero(pc.fill_null(mask, False)).to_pylist()
                    rows = batch.take(pa.array(indices, type=pa.int64())).to_pylist()
                    for index_in_batch, row in zip(indices, rows):
                        record = {"source_id": item["source_id"], "family": family,
                            "locator": {"format": "parquet", "row_group": group, "row": offset + index_in_batch},
                            "physical_row_0based": physical + offset + index_in_batch, "values": row}
                        decision = eligibility(row, indexes, cutoff=utc(CUTOFF)) if family == "gwas_credible_sets" else {"date_guard": date_guard(row, utc(CUTOFF))}
                        reasons = list(decision.get("exclusion_reasons", decision["date_guard"]["exclusion_reasons"]))
                        if "annotationDate" in row:
                            try:
                                lower, upper, _ = source_date_interval(row["annotationDate"], "annotationDate")
                                status = "unknown" if lower is None else interval_status(lower, upper, utc(CUTOFF))
                                if status not in ("unknown", "within_cutoff"):
                                    reasons.append("annotationDate_" + status)
                            except (ContractError, ValueError, TypeError, OverflowError):
                                reasons.append("annotationDate_invalid_explicit_date")
                        cid = case["case_id"]
                        if reasons:
                            excluded[cid].append({"source_id": record["source_id"], "family": family, "locator": record["locator"], "exclusion_reasons": reasons})
                        else:
                            selected[cid][family].append(record)
                        need(sum(len(records) for records in selected[cid].values()) + len(excluded[cid]) <= limits["matching_rows_per_case"], "Selected physical-row safety bound exceeded; no truncation")
            checkpoint("original_file_scanned", source_id=item["source_id"], family=family)
        dispositions = {}
        for case in policy["cases"]:
            cid, groups = case["case_id"], selected[case["case_id"]]
            detail = {"status": "blocked", "blocked_reason": None, "eligible_inventory": {family: [{"source_id": record["source_id"], "locator": record["locator"]} for record in records] for family, records in groups.items()},
                      "excluded_inventory": excluded[cid], "neutral_task_sha256": fingerprint(policy["tasks"][cid]), "normalization_sha256": None}
            try:
                mapping = normalization_proof(case, groups["gwas_credible_sets"], indexes)
                detail["normalization_sha256"] = fingerprint(mapping)
                derived = build_task(case, groups)
                need(canonical(derived) == canonical(policy["tasks"][cid]), "Fresh eligible task/inventory differs from fixed neutral task")
                for records in groups.values():
                    for record in records:
                        native_representability(record, case)
                need(len(canonical(groups)) <= limits["case_product_bytes"], "Complete case source projection exceeds bound; no truncation")
                detail.update(status="ready_for_base_compile", blocked_reason=None)
            except (ContractError, KeyError) as error:
                detail["blocked_reason"] = str(error)
            dispositions[cid] = detail
        coverage = {"original_files": len(inventory), "selected_cases": len(policy["cases"]),
            "mapping_rows": {family: len(records) for family, records in small.items()},
            "cases": {cid: {"eligible": {family: len(records) for family, records in groups.items()}, "excluded": len(excluded[cid])} for cid, groups in selected.items()}}
        resources["wall_seconds_before_caller_replay"] = time.monotonic() - started
        checkpoint("source_policy_complete", cases=len(policy["cases"]))
        yield {"snapshot": snapshot, "catalog": freeze(policy["catalog"]), "tasks": freeze(policy["tasks"]),
               "cases": freeze(policy["cases"]), "groups": freeze(selected), "source_proofs": freeze(proofs),
               "coverage": freeze(coverage), "resources": resources, "dispositions": freeze(dispositions)}
        checkpoint("source_policy_caller_completed")
