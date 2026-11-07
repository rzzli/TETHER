"""Bounded P05 source-only registration and selected-original capture.

Drafting reads only pinned neutral metadata. Execution requires a separate root
READY freeze, and never creates agent packets, references, or model outputs.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import platform
import re
import sqlite3
import sys
import time
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "src"))
from tether_engine.atomic import publish_bytes
from tether_engine.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from tether_engine.journal import RunJournal
from tether_engine.ingest import peak_memory_bytes
from tether_engine.provenance import InputGraph, catalog_index, check_role
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files

ASSETS = WORKSPACE / "planning/review-assets/preprint-p05-20261031"
PLAN_PATH = ASSETS / "REGISTRY-PLAN-DRAFT-v3.json"
READY_PATH = ASSETS / "REGISTRY-READY-v3.json"
RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")
OUTPUT_ROOT = WORKSPACE / "data/derived"
OUTPUT_PREFIX = "preprint-p05-source-validation-"
FRAME_PATH = ASSETS / "FRAME-METADATA-PREFLIGHT-v1.json"
ACQUISITION_PATH = ASSETS / "ACQUISITION-METADATA-v1.json"
CATALOG_PATH = WORKSPACE / "data/catalog/sources.json"
PINS = {
    "frame": (FRAME_PATH, "c9af0da5ff7a07b95372383d73c493faef0ba4081a34768d88393a881ff26551"),
    "acquisition": (ACQUISITION_PATH, "428ab3be53abffb24f8d2e95e457f603012b8e66a3ee02575e696f996b00a405"),
    "catalog": (CATALOG_PATH, "3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109"),
}
FRAMEWORK = ("provenance.py", "contracts.py", "chrono.py", "serde.py", "journal.py",
             "atomic.py", "study/stable_read.py", "study/proofs.py", "study/source_fact_sources.py",
             "__init__.py", "study/__init__.py")
SEED = "preprint-p05-deterministic-v1"
EXPOSED = frozenset(("CD276", "OSMR", "ERBB2", "PCSK9", "IL6R", "CFTR", "GLP1R", "SCN9A", "CTLA4"))
EXPECTED = {
    "gwas_credible_sets": {"files": 100, "bytes": 180049263, "rows": 1753850},
    "credible_set": {"files": 25, "bytes": 2588111695, "rows": 2862043},
    "target": {"files": 10, "bytes": 75568567, "rows": 78726},
    "disease": {"files": 1, "bytes": 5545555, "rows": 39530},
    "hgnc": {"files": 1, "bytes": 16973159, "rows": None},
}
GWAS = ("id", "targetId", "diseaseId", "diseaseFromSourceMappedId", "variantId", "studyId",
        "studyLocusId", "datasourceId", "datatypeId")
CREDIBLE = ("studyLocusId", "studyId", "variantId", "chromosome", "position", "beta",
            "standardError", "pValueMantissa", "pValueExponent", "sampleSize", "zScore")
PROJECTIONS = {"gwas_credible_sets": GWAS, "credible_set": CREDIBLE,
               "target": ("id", "approvedSymbol"), "disease": ("id", "name"),
               "hgnc": ("hgnc_id", "symbol", "ensembl_gene_id", "status")}
OPTIONAL = {"gwas_credible_sets": ("literature",), "hgnc": ("gene_group", "gene_group_id")}
GUARD_FIELDS = ("evidenceDate", "publicationDate", "publicationYear", "releaseDate", "releaseVersion")
LIMITS = {"compressed_input_bytes": 4 * 1024**3, "files": 256,
          "registry_bytes": 2 * 1024**3, "output_bytes": 3 * 1024**3,
          "case_product_bytes": 64 * 1024**2, "seconds": 1200, "batch_rows": 8192}


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def text(value):
    return type(value) is str and bool(value) and value == value.strip()


def source_value(value):
    """Preserve native invalid numeric context in strict JSON, never fabricate a number."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"type": "invalid_native_number", "native_type": "float",
                "kind": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"}
    if isinstance(value, dict):
        return {k: source_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [source_value(v) for v in value]
    return value


def unit_key(row):
    values = tuple(row.get(k) for k in ("targetId", "diseaseId", "studyLocusId"))
    return values if all(text(x) and "|" not in x for x in values) else None


def unit_hash(release, key):
    need(text(release) and "|" not in release and len(key) == 3 and
         all(text(v) and "|" not in v for v in key), "Invalid exact unit identity")
    return digest_bytes("|".join((SEED, release, *key)).encode("utf-8"))


def environment():
    import pyarrow
    need(Path(sys.executable).resolve() == (WORKSPACE / ".venv/Scripts/python.exe").resolve(),
         "The absolute workspace .venv interpreter is required")
    need(pyarrow.__version__ == "21.0.0" and sys.platform == "win32", "Frozen Windows/PyArrow 21.0.0 environment required")
    return {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(),
            "pyarrow": pyarrow.__version__, "platform": sys.platform}


def code_pins():
    files = [Path(__file__).resolve()] + framework_paths()
    return {str(p.relative_to(WORKSPACE)).replace("\\", "/"): digest_bytes(p.read_bytes()) for p in files}


def framework_paths():
    return sorted((WORKSPACE / "src/tether_engine").rglob("*.py"))


def pinned_documents(deadline):
    documents = {}
    for name, (path, expected_hash) in PINS.items():
        payload = read_file(path, deadline, 64 * 1024**2)
        need(digest_bytes(payload) == expected_hash, "Pinned neutral document changed: " + name)
        documents[name] = parse_json(payload)
    return documents


def inventory_from_metadata(frame, acquisition):
    """Extract only declared file descriptors; no source file is opened here."""
    result = []
    for family, rows in ((None, frame["files"]), ("credible_set", acquisition["files"])):
        for row in rows:
            family_name = family or row["family"]
            metadata = row.get("metadata", row.get("format", {}))
            fields = metadata.get("schema_top_level_fields", metadata.get("schema_header_fields", ()))
            record = {"family": family_name, "dataset_id": row["dataset_id"],
                      "release_id": row["release_id"], "path": row["payload_path"],
                      "relative_path": row["relative_path"], "source_url": row["source_url"],
                      "bytes": row["measured_bytes"],
                      "sha256": row.get("sha256", row.get("receipt_recorded_payload_sha256")),
                      "receipt": row["receipt"], "fields": list(fields),
                      "rows": metadata.get("row_count_metadata_only")}
            if family_name == "gwas_credible_sets":
                proof = row.get("partition_proof", {})
                need(proof.get("value") == "gwas_credible_sets" and
                     proof.get("local_key") in ("sourceId", "datasourceId") and
                     proof.get("official_url_key") in ("sourceId", "datasourceId"),
                     "GWAS exact partition proof absent")
                record["partition"] = proof
            result.append(record)
    result.sort(key=lambda x: (x["family"], x["relative_path"]))
    need(len({x["path"].casefold() for x in result}) == len(result), "Duplicate physical input paths")
    need(len({x["receipt"]["path"].casefold() for x in result}) == len(result), "Duplicate receipt paths")
    for family_name, expected in EXPECTED.items():
        rows = [r for r in result if r["family"] == family_name]
        need(len(rows) == expected["files"] and sum(r["bytes"] for r in rows) == expected["bytes"],
             "Exact neutral frame changed: " + family_name)
        if expected["rows"] is not None:
            need(sum(r["rows"] for r in rows) == expected["rows"], "Footer row frame changed: " + family_name)
        for row in rows:
            projection(row, optional=True)
    need(len(result) <= LIMITS["files"] and sum(x["bytes"] for x in result) <= LIMITS["compressed_input_bytes"],
         "Compressed input frame exceeds bound")
    return result


def projection(record, *, optional=False):
    fields = record["fields"]
    required = PROJECTIONS[record["family"]]
    need(len(fields) == len(set(fields)), "Duplicate schema fields")
    need(set(required) <= set(fields), "Required source fields absent: " + record["family"])
    guards = GUARD_FIELDS if record["family"] == "gwas_credible_sets" else ()
    return tuple(required) + tuple(k for k in guards if k in fields) + tuple(
        k for k in OPTIONAL.get(record["family"], ()) if optional and k in fields)


def make_plan():
    deadline = time.monotonic() + 120
    with stable_files([p for p, _ in PINS.values()], deadline=deadline):
        docs = pinned_documents(deadline)
    inventory = inventory_from_metadata(docs["frame"], docs["acquisition"])
    return {"schema_version": 1, "artifact_id": "preprint-p05-registry-plan-v3", "status": "DRAFT",
            "purpose": "deterministic technical source validation; stage 1 source-only originals, never gold",
            "neutral_inputs": {name: {"path": str(path), "sha256": sha} for name, (path, sha) in PINS.items()},
            "code_sha256": code_pins(), "environment": environment(),
            "frame": EXPECTED, "frame_descriptor_sha256": fingerprint(inventory),
            "file_count": len(inventory), "compressed_input_bytes": sum(x["bytes"] for x in inventory),
            "release": "25.09", "selection_seed": SEED, "selected_units": 12,
            "selection_count_policy": "12 is an upper bound; accept actual count 1..12; zero fails with registry retained",
            "unit": ["targetId", "diseaseId", "studyLocusId"],
            "selection": "lowest SHA256(seed|release|targetId|diseaseId|studyLocusId), lexical ties; unique eligible units",
            "duplicate_policy": "retain every physical GWAS row and every selected credible-set match; never first-row resolve",
            "missing_policy": "retain selected cases with missing/conflicting joins or measurements; never replace",
            "exposed_symbols_excluded": sorted(EXPOSED), "other_exposure": "UNKNOWN",
            "freshness_independence_claim": "not_made", "canonical_mapping": "exact target id and approvedSymbol, unique exact Approved HGNC mapping; exact disease id; no aliases",
            "gwas_partition_value": "gwas_credible_sets", "gwas_datasourceId": "gwas_credible_sets",
            "gwas_datatypeId": "genetic_association",
            "eligibility_only_guard_fields": list(GUARD_FIELDS),
            "row_guard_cutoff_utc": docs["frame"]["created_at_utc"],
            "ready_cutoff_policy": "root READY pins explicit UTC cutoff >= this neutral-frame default and <= execution admission; all source and row guards use READY cutoff",
            "row_date_guard": "explicit native precision intervals only; intersect publicationDate/publicationYear for same event, exclude disjoint publication intervals, explicit future, straddling precision-unverified and malformed dates; independent evidenceDate/releaseDate guards; missing dates unknown; releaseVersion native metadata only",
            "projections": {k: list(v) for k, v in PROJECTIONS.items()},
            "optional_projections": {k: list(v) for k, v in OPTIONAL.items()},
            "limits": LIMITS, "resource_enforcement": "cooperative checks and SQLite page cap; no hard OS watchdog",
            "output_root": str(OUTPUT_ROOT), "output_name": OUTPUT_PREFIX + "<UTC>",
            "receipt_archive": "private exact-byte content-addressed receipts",
            "source_access": "read-only originals; hash all payloads and receipts under stable locks before values",
            "scope": {"model_branch": "closed_after_conformance_failure", "model_calls": 0, "network_calls": 0,
                      "new_downloads": 0, "clinical_fields": [], "probability_features": [], "provider_weights": [],
                      "agent_packets": "not_created", "references": "not_created"},
            "output_roles": {"registry_and_case_plan": "neutral_metadata; original and neutral-plan parents only",
                             "selected_original_captures": "UNQUALIFIED/AUDIT_ONLY; evaluation_only; agent_visible=false",
                             "captured_values_as_downstream_parents": "forbidden for both agent packets and references"},
            "unknown_context": ["study_table_absent_not_substituted", "ancestry", "units_and_scales", "study_identity_if_missing",
                                "availableAt", "publicationDate", "historical_eligibility", "causal_direction", "MR_validity"],
            "reference_phase": "later agent-packet and reference builders must freshly reread originals plus neutral case plan and recheck row dates; no audit capture values or evaluator-only ancestors"}


def validate_freeze(plan, plan_bytes, ready, *, current_code=None, current_environment=None):
    need(plan.get("status") == "DRAFT", "Only the immutable neutral DRAFT can be frozen")
    need(ready.get("schema_version") == 1 and ready.get("status") == "READY" and
         ready.get("scope") == "p05_source_only_stage1" and ready.get("frozen_by") == "root",
         "Root source-only READY freeze required")
    need(ready.get("plan_sha256") == digest_bytes(plan_bytes), "READY does not bind these exact plan bytes")
    need(ready.get("code_sha256") == plan.get("code_sha256"), "READY code pins differ from plan")
    need(plan.get("code_sha256") == (current_code if current_code is not None else code_pins()), "Frozen implementation changed")
    need(ready.get("environment") == plan.get("environment") ==
         (current_environment if current_environment is not None else environment()), "Frozen environment changed")
    need(plan.get("limits") == LIMITS and plan.get("frame") == EXPECTED and
         plan.get("selection_seed") == SEED and plan.get("selected_units") == 12,
         "Frozen protocol constants changed")
    freeze_cutoff(plan, ready)


def freeze_cutoff(plan, ready):
    value = ready.get("row_guard_cutoff_utc")
    need(type(value) is str, "READY must pin an explicit UTC source/row eligibility cutoff")
    try:
        cutoff = datetime.fromisoformat(value.replace("Z", "+00:00"))
        minimum = datetime.fromisoformat(plan["row_guard_cutoff_utc"].replace("Z", "+00:00"))
    except (KeyError, ValueError) as error:
        raise ContractError("Invalid frozen UTC eligibility cutoff") from error
    need(cutoff.tzinfo is not None and cutoff.utcoffset().total_seconds() == 0 and
         minimum.tzinfo is not None and minimum <= cutoff <= datetime.now(timezone.utc),
         "READY cutoff must be UTC, no earlier than neutral frame, no later than execution admission")
    return cutoff


def load_guard(deadline):
    plan_bytes = read_file(PLAN_PATH, deadline, 1024**2)
    plan = parse_json(plan_bytes)
    ready_bytes = read_file(READY_PATH, deadline, 1024**2)
    ready = parse_json(ready_bytes)
    validate_freeze(plan, plan_bytes, ready)
    docs = pinned_documents(deadline)
    inventory = inventory_from_metadata(docs["frame"], docs["acquisition"])
    need(fingerprint(inventory) == plan["frame_descriptor_sha256"], "Frozen descriptor frame changed")
    need(plan == make_plan(), "DRAFT differs from the current exact neutral protocol")
    return {**plan, "row_guard_cutoff_utc": freeze_cutoff(plan, ready).isoformat()}, inventory, docs["catalog"]


class Bounds:
    def __init__(self, output, *, deadline=None, limits=None):
        self.output = Path(output)
        self.limits = dict(limits or LIMITS)
        self.started = time.monotonic()
        self.deadline = deadline if deadline is not None else self.started + self.limits["seconds"]
        self.max_batch_arrow_bytes = 0
        self.selected_arrow_bytes = 0
        self.peak_process_rss_bytes = None
        self.rss_measurement = "unavailable"

    def observe(self, batch, *, selected=False):
        self.max_batch_arrow_bytes = max(self.max_batch_arrow_bytes, batch.nbytes)
        if selected:
            self.selected_arrow_bytes += batch.nbytes
        self.check()

    def check(self):
        deadline_check(self.deadline)
        try:
            import psutil
            value = psutil.Process().memory_info().rss
            self.peak_process_rss_bytes = max(self.peak_process_rss_bytes or 0, value)
            self.rss_measurement = "psutil process RSS sampled at cooperative checkpoints"
        except (ImportError, OSError):
            pass
        size = sum(p.stat().st_size for p in self.output.rglob("*") if p.is_file()) if self.output.exists() else 0
        need(size <= self.limits["output_bytes"], "Total output bound exceeded")
        registry = self.output / "candidate-registry.sqlite"
        need(not registry.exists() or registry.stat().st_size <= self.limits["registry_bytes"], "Registry bound exceeded")
        return size

    def publish(self, relative, value):
        payload = canonical(value) + b"\n"
        need(self.check() + len(payload) <= self.limits["output_bytes"], "Total output bound exceeded")
        publish_bytes(self.output / relative, payload)

    def report(self):
        try:
            peak = peak_memory_bytes()
            peak_status = "measured" if type(peak) is int and peak > 0 else "os_query_unavailable"
            if peak_status != "measured":
                peak = None
        except (OSError, AttributeError, ValueError) as error:
            peak, peak_status = None, "os_query_failed:" + type(error).__name__
        return {"wall_seconds": time.monotonic() - self.started, "bounds": self.limits,
                "enforcement": "cooperative; not a hard OS watchdog", "physical_io_bytes": None,
                "physical_io_status": "not_measured", "peak_sampled_process_rss_bytes": self.peak_process_rss_bytes,
                "rss_measurement": self.rss_measurement, "max_batch_arrow_bytes": self.max_batch_arrow_bytes,
                "process_peak_working_set_bytes": peak, "process_peak_working_set_status": peak_status,
                "process_peak_working_set_basis": "tether_engine.ingest.peak_memory_bytes; Win32 PeakWorkingSetSize; overall Python process lifetime, not a stage-only increment",
                "selected_arrow_bytes_cumulative": self.selected_arrow_bytes,
                "output_bytes_before_report_and_seal": self.check()}


def check_receipt_identity(document, record, *, source_id=None):
    """Pure exact receipt check; normalize only relative-path separators.

    The expected relative path is the trusted canonical descriptor spelling.
    No path resolution, alias collapse, case folding, or byte rewriting occurs.
    """
    need(isinstance(record, Mapping), "Receipt check requires a neutral source descriptor")
    if source_id is None:
        source_id = str(record.get("dataset_id", "unknown")) + ":" + str(record.get("sha256", "unknown"))[:16]
    need(type(source_id) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", source_id),
         "Receipt check requires a neutral source_id")
    expected = {"status": "completed", "dataset_id": record.get("dataset_id"),
                "release_id": record.get("release_id"), "sha256": record.get("sha256"),
                "bytes": record.get("bytes"), "url": record.get("source_url")}
    mismatched = []
    normalized = None
    raw_relative = None
    if not isinstance(document, Mapping):
        mismatched.append("receipt_document")
    else:
        for field, value in expected.items():
            observed = document.get(field)
            required_type = int if field == "bytes" else str
            if type(observed) is not required_type or observed != value:
                mismatched.append(field)
        raw_relative = document.get("relative_path")
        if type(raw_relative) is str:
            normalized = raw_relative.replace("\\", "/")
        if normalized != record.get("relative_path") or type(raw_relative) is not str:
            mismatched.append("relative_path")
    need(not mismatched, "Receipt identity mismatch: source_id=" + source_id + "; fields=" + ",".join(sorted(mismatched)))
    return {"source_id": source_id, "relative_path_separator_normalized": raw_relative != normalized}


def verify_originals(inventory, output, bounds):
    """Caller holds all original and receipt locks through the final parse and seal."""
    proofs = []
    # All 137 opaque payload hashes precede any receipt interpretation or source value parse.
    for record in inventory:
        path = checked_path(RAW_ROOT, record["relative_path"])
        need(path == Path(record["path"]), "Payload path differs from exact neutral relative path")
        measured = hash_file(path, bounds.deadline)
        need(dict(measured) == {"sha256": record["sha256"], "bytes": record["bytes"]}, "Original payload checksum/size mismatch")
        proofs.append({**record, "verified_payload": dict(measured)})
        bounds.check()
    for index, record in enumerate(proofs):
        receipt = record["receipt"]
        relative = Path(receipt["path"]).relative_to(RAW_ROOT).as_posix()
        path = checked_path(RAW_ROOT, relative)
        payload = read_file(path, bounds.deadline, min(1024**2, receipt["bytes"]))
        need(len(payload) == receipt["bytes"] and digest_bytes(payload) == receipt["sha256"], "Original receipt checksum/size mismatch")
        document = parse_json(payload)
        check_receipt_identity(document, record, source_id=f"original-{index:03d}")
        timestamp = datetime.fromisoformat(document["completed_at_utc"].replace("Z", "+00:00"))
        need(timestamp.tzinfo is not None, "Receipt timestamp lacks timezone")
        record["completed_at_utc"] = timestamp.astimezone(timezone.utc).isoformat()
        archive = "_private/receipts/" + receipt["sha256"] + ".json"
        need(bounds.check() + len(payload) <= bounds.limits["output_bytes"], "Receipt archive exceeds total output bound")
        publish_bytes(output / archive, payload)
        record["receipt_archive"] = archive
    return proofs


def parquet_batches(record, bounds, *, optional=False):
    """Project in Arrow before Python; locators refer to physical rows, starting at zero."""
    import pyarrow.parquet as pq
    columns = projection(record, optional=optional)
    source = pq.ParquetFile(record["path"])
    need(source.schema_arrow.names == record["fields"], "Source schema differs from pinned metadata")
    need(source.metadata.num_rows == record["rows"], "Source footer row count differs from frozen frame")
    physical_base = 0
    for group in range(source.num_row_groups):
        in_group = 0
        for batch in source.iter_batches(batch_size=LIMITS["batch_rows"], row_groups=[group], columns=list(columns), use_threads=False):
            bounds.observe(batch)
            yield batch, {"row_group": group, "row_in_group_start": in_group, "physical_row_start": physical_base + in_group}
            in_group += batch.num_rows
        need(in_group == source.metadata.row_group(group).num_rows, "Incomplete physical row-group traversal")
        physical_base += in_group


def locator(record, offset, index):
    return {"source_relative_path": record["relative_path"], "source_sha256": record["sha256"],
            "row_group_0based": offset["row_group"],
            "row_in_group_0based": offset["row_in_group_start"] + index,
            "physical_row_0based": offset["physical_row_start"] + index}


def load_small(inventory, bounds):
    import pyarrow as pa
    import pyarrow.csv as csv
    result = {family: [] for family in ("target", "disease", "hgnc")}
    schemas = []
    for record in inventory:
        family = record["family"]
        if family not in result:
            continue
        optional = OPTIONAL.get(family, ())
        schemas.append({"source_relative_path": record["relative_path"], "family": family,
                        "optional_fields": {k: "present" if k in record["fields"] else "schema_absent" for k in optional}})
        if family == "hgnc":
            columns = projection(record, optional=True)
            stream = csv.open_csv(record["path"], read_options=csv.ReadOptions(block_size=1024**2),
                                  parse_options=csv.ParseOptions(delimiter="\t"),
                                  convert_options=csv.ConvertOptions(include_columns=list(columns),
                                      column_types={k: pa.string() for k in columns}, strings_can_be_null=False))
            need(stream.schema.names == list(columns), "HGNC projection changed")
            position = 0
            for batch in stream:
                # Arrow CSV block batches are sliced to the protocol's maximum row batch.
                for start in range(0, batch.num_rows, LIMITS["batch_rows"]):
                    piece = batch.slice(start, LIMITS["batch_rows"])
                    bounds.observe(piece)
                    for index, row in enumerate(piece.to_pylist()):
                        result[family].append({"values": row, "locator": {"source_relative_path": record["relative_path"],
                            "source_sha256": record["sha256"], "data_record_0based": position + start + index,
                            "locator_basis": "TSV parsed data record, header excluded; not a text line number"}})
                position += batch.num_rows
        else:
            for batch, offset in parquet_batches(record, bounds):
                result[family].extend({"values": row, "locator": locator(record, offset, index)}
                                      for index, row in enumerate(batch.to_pylist()))
    return result, schemas


def mapping_index(small):
    indexes = {k: defaultdict(list) for k in ("target", "target_symbol", "disease", "hgnc", "hgnc_symbol", "hgnc_id")}
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


def source_date_interval(value, field):
    """Preserve the supplied source precision; never infer a first public time."""
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
        year, month = (int(x) for x in value.split("-"))
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


def source_date_bound(value, field):
    _, upper, precision = source_date_interval(value, field)
    return upper, precision


def interval_status(lower, upper, cutoff):
    return "explicit_future" if lower > cutoff else "date_precision_unverified" if upper > cutoff else "within_cutoff"


def date_guard(row, cutoff):
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
    publication = [intervals[k] for k in ("publicationDate", "publicationYear") if k in intervals]
    event = {"status": "unknown", "lower_bound_utc": None, "upper_bound_utc": None}
    if publication:
        lower, upper = max(x[0] for x in publication), min(x[1] for x in publication)
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


def eligibility(row, indexes, *, cutoff=None):
    reasons = []
    key = unit_key(row)
    if key is None:
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
    return {"eligible": not reasons, "exclusion_reasons": sorted(reasons), "date_guard": guard, "approved_symbol": symbol,
            "exposure_status": "known_exposed" if symbol in EXPOSED else "UNKNOWN"}


def open_registry(path, cap):
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA synchronous=FULL")
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        connection.execute("PRAGMA max_page_count=" + str(cap // page_size))
        connection.execute("""CREATE TABLE source_files (
            source_id INTEGER PRIMARY KEY, source_path TEXT NOT NULL UNIQUE, source_sha256 TEXT NOT NULL,
            release_id TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE gwas_rows (
        physical_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES source_files(source_id),
        row_group INTEGER NOT NULL, row_in_group INTEGER NOT NULL, physical_row INTEGER NOT NULL,
        evidence_id TEXT, target_id TEXT, disease_id TEXT, study_locus_id TEXT,
        eligible INTEGER NOT NULL, exclusion_reasons TEXT NOT NULL, unit_hash TEXT,
        approved_symbol TEXT, exposure_status TEXT NOT NULL, identity_json TEXT NOT NULL,
        UNIQUE(source_id, physical_row))""")
        connection.execute("CREATE INDEX eligible_units ON gwas_rows(eligible,unit_hash,target_id,disease_id,study_locus_id)")
        connection.execute("CREATE VIEW physical_rows AS SELECT gwas_rows.*, source_files.source_path, source_files.source_sha256, source_files.release_id FROM gwas_rows JOIN source_files USING(source_id)")
        connection.execute("CREATE TABLE registry_metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL)")
    except BaseException:
        connection.close()
        raise
    return connection


def register_batch(connection, record, rows, offset, indexes, *, cutoff=None):
    counts = Counter()
    connection.execute("INSERT OR IGNORE INTO source_files(source_path,source_sha256,release_id) VALUES (?,?,?)",
                       (record["relative_path"], record["sha256"], record["release_id"]))
    source_id, source_hash, release_id = connection.execute("SELECT source_id,source_sha256,release_id FROM source_files WHERE source_path=?",
                                                           (record["relative_path"],)).fetchone()
    need(source_hash == record["sha256"] and release_id == record["release_id"], "Physical source identity changed within registry")
    for index, row in enumerate(rows):
        decision = eligibility(row, indexes, cutoff=cutoff)
        key = unit_key(row)
        loc = locator(record, offset, index)
        connection.execute("INSERT INTO gwas_rows VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            source_id, loc["row_group_0based"], loc["row_in_group_0based"],
            loc["physical_row_0based"], row.get("id"), row.get("targetId"), row.get("diseaseId"), row.get("studyLocusId"),
            int(decision["eligible"]), canonical(decision["exclusion_reasons"]).decode(),
            unit_hash(record["release_id"], key) if key else None, decision["approved_symbol"], decision["exposure_status"],
            canonical(source_value(row)).decode()))
        counts["physical_rows"] += 1
        counts["eligible_physical_rows" if decision["eligible"] else "excluded_physical_rows"] += 1
        counts.update({"exclusion:" + reason: 1 for reason in decision["exclusion_reasons"]})
    connection.commit()
    return counts


def choose_units(connection, count=12):
    need(type(count) is int and 1 <= count <= 12, "Selected unit cap must be an integer within 1..12")
    rows = connection.execute("""SELECT unit_hash,target_id,disease_id,study_locus_id,release_id,COUNT(*)
        FROM physical_rows WHERE eligible=1
        GROUP BY unit_hash,target_id,disease_id,study_locus_id,release_id
        ORDER BY unit_hash,target_id,disease_id,study_locus_id,release_id LIMIT ?""", (count,)).fetchall()
    need(bool(rows), "Zero eligible unique units; retain registry and fail without replacement")
    return [{"case_id": f"p05-{index + 1:02d}", "unit_hash": row[0], "targetId": row[1], "diseaseId": row[2],
             "studyLocusId": row[3], "release_id": row[4], "eligible_physical_rows": row[5], "exposure_status": "UNKNOWN",
             "availableAt": None, "publicationDate": None, "historical_eligibility": "not_verified"}
            for index, row in enumerate(rows)]


def filtered_rows(batch, cases, *, family):
    """Return only selected Arrow rows and their original batch indices."""
    import pyarrow as pa
    import pyarrow.compute as pc
    mask = pa.array([False] * batch.num_rows)
    keys = ("studyLocusId",) if family == "credible_set" else ("targetId", "diseaseId", "studyLocusId")
    unique = sorted({tuple(case[k] for k in keys) for case in cases})
    for values in unique:
        current = pa.array([True] * batch.num_rows)
        for key, value in zip(keys, values):
            current = pc.and_(current, pc.fill_null(pc.equal(batch.column(batch.schema.get_field_index(key)), value), False))
        mask = pc.or_(mask, current)
    indices = pc.indices_nonzero(mask)
    return batch.filter(mask), indices.to_pylist()


class CaseProducts:
    def __init__(self, output, bounds, cases):
        self.bounds, self.output, self.streams, self.sizes = bounds, output, {}, Counter()
        try:
            for case in cases:
                path = output / "selected-originals" / (case["case_id"] + ".jsonl")
                path.parent.mkdir(parents=True, exist_ok=True)
                self.streams[case["case_id"]] = path.open("xb")
                self.append(case["case_id"], {"record_type": "case_header", "case": case,
                    "product_kind": "unqualified_source_audit_capture_not_gold", "unknown_context": {
                        "study_table": "absent_not_substituted", "ancestry": "unknown", "units_and_scales": "unknown",
                        "availableAt": None, "publicationDate": None, "causal_direction": "not_inferred",
                        "sample_size": "preserve_source_or_unknown", "effect_allele": "unknown",
                        "genome_build": "unknown", "native_numeric_interpretation": "study_and_variant_observations_only",
                        "gene_or_action_effect": "not_inferred", "probability_features": [], "clinical_fields": []}})
        except BaseException:
            self.close()
            raise

    def append(self, case_id, record):
        # Every record remains quarantined when handled outside its enclosing JSONL file.
        record = {**record, "qualification": "UNQUALIFIED/AUDIT_ONLY", "role": "evaluation_only",
                  "agent_visible": False, "downstream_parent_use": "forbidden_for_agent_packets_and_references"}
        payload = canonical(source_value(record)) + b"\n"
        need(self.sizes[case_id] + len(payload) <= self.bounds.limits["case_product_bytes"], "Selected case product bound exceeded")
        need(self.bounds.check() + len(payload) <= self.bounds.limits["output_bytes"], "Total output bound exceeded")
        self.streams[case_id].write(payload)
        self.streams[case_id].flush()
        self.sizes[case_id] += len(payload)

    def close(self):
        for stream in self.streams.values():
            if not stream.closed:
                stream.flush()
                os.fsync(stream.fileno())
                stream.close()


def capture_selected(inventory, cases, indexes, bounds, products, *, cutoff=None):
    counters = Counter()
    signatures = defaultdict(lambda: defaultdict(set))
    identities = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    by_unit = {tuple(case[k] for k in ("targetId", "diseaseId", "studyLocusId")): case for case in cases}
    by_locus = defaultdict(list)
    for case in cases:
        by_locus[case["studyLocusId"]].append(case)
    for record in inventory:
        family = record["family"]
        if family not in ("gwas_credible_sets", "credible_set"):
            continue
        for batch, offset in parquet_batches(record, bounds, optional=True):
            selected, indices = filtered_rows(batch, cases, family=family)
            bounds.observe(selected, selected=True)
            counters[family + "_scanned_rows"] += batch.num_rows
            for row, index in zip(selected.to_pylist(), indices):
                matches = by_locus.get(row["studyLocusId"], ()) if family == "credible_set" else [by_unit[unit_key(row)]]
                for case in matches:
                    case_id = case["case_id"]
                    value = source_value(row)
                    products.append(case_id, {"record_type": family + "_original", "values": value,
                        "locator": locator(record, offset, index),
                        "eligibility": eligibility(row, indexes, cutoff=cutoff) if family == "gwas_credible_sets" else "not_used_for_selection"})
                    counters[case_id + ":" + family + "_matches"] += 1
                    signatures[case_id][family].add(fingerprint(value))
                    for field in ("studyId", "variantId"):
                        native = value.get(field)
                        identities[case_id][field][family][canonical(native)] = native
    coverage = {case["case_id"]: {family: {
        "physical_matches": counters[case["case_id"] + ":" + family + "_matches"],
        "distinct_projected_rows": len(signatures[case["case_id"]][family]),
        "status": "missing_retained_no_replacement" if not signatures[case["case_id"]][family] else
                  "multiple_distinct_rows_retained_unresolved" if len(signatures[case["case_id"]][family]) > 1 else
                  "one_distinct_projection_all_physical_matches_retained"}
        for family in ("gwas_credible_sets", "credible_set")} for case in cases}
    for case in cases:
        context = {}
        for field in ("studyId", "variantId"):
            groups = identities[case["case_id"]][field]
            evidence_values = groups["gwas_credible_sets"]
            credible_values = groups["credible_set"]
            known_evidence = {k for k, v in evidence_values.items() if text(v)}
            known_credible = {k for k, v in credible_values.items() if text(v)}
            context[field] = {"gwas_native_values": list(evidence_values.values()), "credible_native_values": list(credible_values.values()),
                "status": "unknown_missing_native_identity" if not known_evidence or not known_credible else
                          "exact_native_identity_agreement" if len(known_evidence) == len(known_credible) == 1 and known_evidence == known_credible else
                          "native_identity_disagreement_or_multiplicity_retained_unresolved",
                "semantic_variant_inference": "not_performed"}
        coverage[case["case_id"]]["native_identity_context"] = context
    return counters, coverage


def original_role(record):
    return "reference" if record["family"] == "hgnc" else "agent_evidence"


def admit_originals(proofs, output, catalog, computed_at):
    nodes = []
    for index, record in enumerate(proofs):
        observed = datetime.fromisoformat(record["completed_at_utc"])
        availability = Availability(None, None, None, None, observed.date(), "public_download_receipt",
            "contemporary download bound only; availableAt/publicationDate unknown; historical eligibility not verified",
            observed, record["receipt"]["sha256"])
        nodes.append(SourceNode(f"original-{index:03d}", record["dataset_id"], record["release_id"],
            record["relative_path"], record["sha256"], original_role(record), availability, TemporalClass.CONTEMPORARY,
            record["source_url"], receipt_path=Path(record["receipt"]["path"]).relative_to(RAW_ROOT).as_posix(),
            receipt_sha256=record["receipt"]["sha256"]))
    snapshot = Snapshot(2, "p05-source-only-originals-v1", Profile.CONTEMPORARY, computed_at.date(), False,
                        (), tuple(nodes), str(RAW_ROOT), {}, computed_at)
    graph = InputGraph(snapshot, output, catalog_index(catalog))
    # This is a technical availability cutoff, not a fabricated clinical Case.
    need(graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=computed_at)) is None,
         "Original source chronology is not admissible at build time")
    return nodes


def lineage_for(proofs, nodes, plan_hash, ready_hash, computed_at, *, cases=()):
    neutral = [{"source_id": "neutral-" + name, "path": str(p), "sha256": h}
               for name, (p, h) in PINS.items()]
    neutral += [{"source_id": "neutral-plan", "path": str(PLAN_PATH), "sha256": plan_hash},
                {"source_id": "neutral-ready", "path": str(READY_PATH), "sha256": ready_hash}]
    original_parents = [n.source_id for n in nodes] + ["neutral-plan"]
    bindings = [n["source_id"] for n in neutral if n["source_id"] != "neutral-plan"]
    per_artifact = [{"artifact_id": name, "path": path, "role": "neutral_metadata", "agent_visible": False,
                     "parents": original_parents, "protocol_and_catalog_bindings": bindings,
                     "downstream_use": "neutral_routing_only; reread and revalidate eligible originals"}
                    for name, path in (("neutral-registry", "candidate-registry.sqlite"),
                                       ("neutral-case-plan", "selected-case-plan.json"))]
    per_artifact += [{"artifact_id": "audit-selected-original-" + case["case_id"],
                      "path": "selected-originals/" + case["case_id"] + ".jsonl",
                      "role": "evaluation_only", "qualification": "UNQUALIFIED/AUDIT_ONLY", "agent_visible": False,
                      "parents": original_parents, "protocol_and_catalog_bindings": bindings,
                      "downstream_parent_use": "forbidden_for_agent_packets_and_references"} for case in cases]
    per_artifact += [{"artifact_id": "audit-normalized-mapping", "path": "normalized-mapping-provenance.json",
                      "role": "evaluation_only", "qualification": "UNQUALIFIED/AUDIT_ONLY", "agent_visible": False,
                      "parents": original_parents, "protocol_and_catalog_bindings": bindings,
                      "downstream_parent_use": "forbidden_for_agent_packets_and_references"}]
    per_artifact += [{"artifact_id": "audit-" + name, "path": path, "role": "evaluation_only",
                      "agent_visible": False, "parents": original_parents, "protocol_and_catalog_bindings": bindings,
                      "product_kind": "technical_audit_metadata_not_source_fact_input"}
                     for name, path in (("coverage", "coverage.json"), ("resources", "resource-report.json"),
                                        ("lineage", "lineage.json"), ("journal", "journal.jsonl"))]
    per_artifact += [{"artifact_id": "transport-receipt-" + str(i), "path": proof["receipt_archive"],
                      "role": "neutral_metadata", "agent_visible": False, "parents": [f"original-{i:03d}"],
                      "product_kind": "exact_transport_receipt_bytes_not_source_fact_input"}
                     for i, proof in enumerate(proofs)]
    return {"schema_version": 1, "role": "source_only_lineage_not_reference", "source_nodes": encode(nodes),
            "source_node_contract": "tether_engine SourceNode; graph/catalog/chronology admitted before values; stable hash proofs retained",
            "neutral_metadata_nodes": neutral,
            "plan_sha256": plan_hash, "code_sha256": code_pins(),
            "verified_originals": [{"source_id": f"original-{i:03d}", "path": p["path"],
                "relative_path": p["relative_path"], "sha256": p["verified_payload"]["sha256"],
                "bytes": p["verified_payload"]["bytes"], "receipt_path": p["receipt"]["path"],
                "receipt_sha256": p["receipt"]["sha256"], "receipt_bytes": p["receipt"]["bytes"],
                "hash_and_parse_stable_lock_scope": "all originals and receipts held across verification and interpretation"}
                for i, p in enumerate(proofs)],
            "receipt_archives": [{"source_id": f"original-{i:03d}", "path": p["receipt_archive"],
                "sha256": p["receipt"]["sha256"], "exact_original_bytes": True} for i, p in enumerate(proofs)],
            "derived_products": {"role": "mixed_per_artifact_roles; no_agent_packets_created",
                                 "parents": [n.source_id for n in nodes] + [n["source_id"] for n in neutral],
                                 "method_id": "p05-source-only-builder", "method_version": "1", "computed_at": computed_at.isoformat()},
            "artifact_lineage": per_artifact,
            "downstream_phase_policy": "agent packets AND references must freshly reread originals plus neutral case plan and recheck row dates; no audit capture value parents",
            "evaluator_only_ancestors": [], "historical_eligibility": "not_verified"}


def failure_seal(output, stage, error, deadline):
    """Retain terminal failure evidence; partial originals are never marked usable."""
    artifacts = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in ("failure-seal.json", "journal.jsonl"):
            continue
        record = {"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
                  "sha256": None, "hash_status": "deadline_expired_not_hashed"}
        if time.monotonic() < deadline:
            try:
                record.update(dict(hash_file(path, deadline)))
                record["hash_status"] = "measured"
            except (OSError, ContractError, TimeoutError):
                record["hash_status"] = "unavailable_at_failure"
        artifacts.append(record)
    document = {"schema_version": 1, "status": "failed_stage1_partial_not_usable", "stage": stage,
                "error_class": type(error).__name__, "retained_artifacts": artifacts,
                "partial_products_usable": False, "replacement_action": "start a new output directory"}
    publish_bytes(output / "failure-seal.json", canonical(document) + b"\n")


def execute(output):
    output = Path(output).absolute()
    need(output.parent == OUTPUT_ROOT and re.fullmatch(OUTPUT_PREFIX + r"\d{8}T\d{6}Z", output.name),
         "Output must be a fresh ignored data/derived/preprint-p05-source-validation-<UTC> directory")
    # The approved parent must already exist and have no links/reparse components.
    # The prospective leaf is deliberately absent until RunJournal reserves it.
    need(checked_path(WORKSPACE, output.parent.relative_to(WORKSPACE).as_posix()) == output.parent and
         output.parent.is_dir(), "Unsafe output parent")
    try:
        output.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ContractError("Output leaf already exists; a fresh reservation is required")
    deadline = time.monotonic() + LIMITS["seconds"]
    guard_paths = [PLAN_PATH, READY_PATH, Path(__file__).resolve()] + [p for p, _ in PINS.values()]
    guard_paths += framework_paths()
    # READY validation precedes directory creation; the exclusive RunJournal mkdir is the reservation.
    journal, connection, products = None, None, None
    stage = "guard"
    stack = ExitStack()
    try:
        stack.enter_context(stable_files(guard_paths, deadline=deadline))
        plan, inventory, catalog = load_guard(deadline)
        plan_hash = digest_bytes(read_file(PLAN_PATH, deadline, 1024**2))
        ready_hash = digest_bytes(read_file(READY_PATH, deadline, 1024**2))
        row_cutoff = datetime.fromisoformat(plan["row_guard_cutoff_utc"])
        journal = RunJournal(output, kind="build")
        stage = "output_reservation_validation"
        need(checked_path(WORKSPACE, output.relative_to(WORKSPACE).as_posix()) == output and output.is_dir(),
             "Unsafe reserved output path")
        bounds = Bounds(output, deadline=deadline)
        stage = "source_integrity"
        paths = [Path(x["path"]) for x in inventory] + [Path(x["receipt"]["path"]) for x in inventory]
        stack.enter_context(stable_files(paths, deadline=deadline))
        journal.append("build_stage", stage=stage)
        proofs = verify_originals(inventory, output, bounds)
        journal.append("all_originals_verified_before_values", files=len(proofs), receipts=len(proofs),
                       payload_bytes=sum(x["bytes"] for x in proofs))
        nodes = admit_originals(proofs, output, catalog, row_cutoff)
        journal.append("original_lineage_admitted_before_values", source_nodes=len(nodes),
                       neutral_plan_sha256=plan_hash, catalog_sha256=PINS["catalog"][1])
        stage = "canonical_normalization"
        journal.append("build_stage", stage=stage)
        small, schemas = load_small(inventory, bounds)
        indexes = mapping_index(small)
        stage = "physical_candidate_registration"
        journal.append("build_stage", stage=stage)
        connection = open_registry(output / "candidate-registry.sqlite", LIMITS["registry_bytes"])
        connection.execute("INSERT INTO registry_metadata VALUES (?,?)", ("neutral_protocol", canonical({
            "plan_sha256": plan_hash, "row_guard_cutoff_utc": row_cutoff.isoformat(),
            "role": "neutral_metadata", "agent_visible": False,
            "guard_fields": list(GUARD_FIELDS), "date_guard_replay": "native guard values in identity_json; exclusions retained per physical row",
            "source_path_and_hash": "normalized source_files table joined by physical_rows view"}).decode()))
        counters = Counter()
        for record in inventory:
            if record["family"] != "gwas_credible_sets":
                continue
            for batch, offset in parquet_batches(record, bounds):
                counters.update(register_batch(connection, record, batch.to_pylist(), offset, indexes, cutoff=row_cutoff))
                bounds.check()
        need(counters["physical_rows"] == EXPECTED["gwas_credible_sets"]["rows"], "Full GWAS registry coverage mismatch")
        stage = "deterministic_selection"
        journal.append("build_stage", stage=stage)
        cases = choose_units(connection, plan["selected_units"])
        bounds.publish("selected-case-plan.json", {"schema_version": 1, "role": "neutral_metadata",
            "product_kind": "neutral_selected_case_plan", "agent_visible": False,
            "selected_unit_cap": plan["selected_units"], "actual_selected_units": len(cases),
            "row_guard_cutoff_utc": row_cutoff.isoformat(), "plan_sha256": plan_hash,
            "downstream_phase_policy": "reread eligible originals and recheck row dates; audit captures forbidden as value parents",
            "selection_seed": SEED, "numeric_availability_used": False, "model_performance_used": False,
            "no_replacement": True, "cases": cases})
        connection.close()
        connection = None
        stage = "selected_original_capture"
        journal.append("build_stage", stage=stage)
        products = CaseProducts(output, bounds, cases)
        selected_mapping = []
        for case in cases:
            mapping = {"case_id": case["case_id"],
                "target_originals": indexes["target"].get(case["targetId"], []),
                "disease_originals": indexes["disease"].get(case["diseaseId"], []),
                "hgnc_originals": indexes["hgnc"].get(case["targetId"], []), "aliases_used": False}
            selected_mapping.append(mapping)
            products.append(case["case_id"], {"record_type": "normalization_originals", **mapping})
        captured, coverage = capture_selected(inventory, cases, indexes, bounds, products, cutoff=row_cutoff)
        counters.update(captured)
        products.close()
        products = None
        bounds.publish("normalized-mapping-provenance.json", {"selected_cases": selected_mapping,
            "role": "evaluation_only", "qualification": "UNQUALIFIED/AUDIT_ONLY", "agent_visible": False,
            "downstream_parent_use": "forbidden_for_agent_packets_and_references",
            "optional_schema_presence": schemas, "other_exposure": "UNKNOWN", "fresh_or_independent_claim": False})
        stage = "lineage_and_coverage"
        journal.append("build_stage", stage=stage)
        bounds.publish("coverage.json", {"frame": EXPECTED, "counters": dict(counters), "selected": coverage,
            "role": "evaluation_only", "agent_visible": False,
            "selected_unit_cap": plan["selected_units"], "actual_selected_units": len(cases),
            "all_25_credible_files_scanned": len([r for r in inventory if r["family"] == "credible_set"]) == EXPECTED["credible_set"]["files"],
            "credible_files_scanned": len([r for r in inventory if r["family"] == "credible_set"]), "all_selected_conflicts_retained": True,
            "source_schema_projection": [{"path": r["relative_path"], "projected_columns": list(projection(r, optional=True)),
                 "eligibility_only_fields": {k: "present" if k in r["fields"] else "schema_absent" for k in GUARD_FIELDS}
                 if r["family"] == "gwas_credible_sets" else {}} for r in inventory],
            "study_table": "absent_not_substituted", "availableAt": None, "publicationDate": None,
            "clinical_fields": [], "probability_features": [], "references": "not_created"})
        bounds.publish("lineage.json", lineage_for(proofs, nodes, plan_hash, ready_hash, datetime.now(timezone.utc), cases=cases))
        bounds.publish("resource-report.json", bounds.report())
        stage = "seal"
        journal.append("build_stage", stage=stage)
        artifacts = [{"path": p.relative_to(output).as_posix(), **dict(hash_file(p, deadline))}
                     for p in sorted(output.rglob("*")) if p.is_file() and p.name != "journal.jsonl"]
        seal = {"schema_version": 1, "status": "completed_source_only_stage1", "plan_sha256": plan_hash,
                "ready_sha256": ready_hash, "artifacts": artifacts,
                "journal_prefix_sha256": journal.events[-1]["sha256"], "agent_packets": "not_created",
                "references": "not_created", "models": "not_run", "source_mutations": 0,
                "selected_unit_cap": plan["selected_units"], "actual_selected_units": len(cases),
                "selected_original_captures": "UNQUALIFIED/AUDIT_ONLY; evaluation_only; agent_visible=false",
                "validity_requires": "terminal build_completed binding this seal, no failure-seal.json"}
        # All locks, database/product streams and journal cleanup succeed before success publication.
        stage = "terminal_cleanup"
        stack.close()
        bounds.check()
        deadline_check(deadline)
        journal.append("build_completed", seal_sha256=fingerprint(seal), stage1_only=True)
        journal.close()
        stage = "success_seal_publication"
        bounds.publish("seal.json", seal)
        return seal
    except BaseException as error:
        for resource in (connection, products):
            if resource is not None:
                try:
                    resource.close()
                except BaseException as cleanup:
                    error.add_note("Resource close failed: " + type(cleanup).__name__)
        try:
            stack.close()
        except BaseException as cleanup:
            error.add_note("Stable-lock close failed: " + type(cleanup).__name__)
        if journal is not None:
            try:
                journal.fail(error, stage)
            except BaseException as cleanup:
                error.add_note("Failure journal append failed: " + type(cleanup).__name__)
            try:
                journal.close()
            except BaseException as cleanup:
                error.add_note("Failure journal close failed: " + type(cleanup).__name__)
            try:
                failure_seal(output, stage, error, deadline)
            except BaseException as cleanup:
                error.add_note("Terminal failure-seal publication failed: " + type(cleanup).__name__)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--draft", action="store_true", help="publish neutral DRAFT only, no source values")
    actions.add_argument("--execute", action="store_true", help="requires exact root READY and fresh ignored output")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.draft:
        need(args.output is None, "DRAFT output path is fixed")
        plan = make_plan()
        publish_bytes(PLAN_PATH, canonical(plan) + b"\n")
        print(canonical({"status": "DRAFT", "path": str(PLAN_PATH), "sha256": digest_bytes(PLAN_PATH.read_bytes()),
                         "source_values_read": 0, "files": plan["file_count"]}).decode())
    else:
        need(args.output is not None, "--execute requires --output")
        seal = execute(args.output)
        print(canonical({"status": seal["status"], "output": str(args.output)}).decode())


if __name__ == "__main__":
    main()
