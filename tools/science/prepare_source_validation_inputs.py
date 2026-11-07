"""P05 stage-2 ORIGINAL-ONLY generation inputs. No reference/output creation.

The DRAFT command reads neutral metadata only. Actual original value reads require
an independently root-authored READY, its externally supplied exact hash, and an
exclusive new ignored output directory. Stage-1 captures are never opened.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE / "tools/science"))
import prepare_source_validation_set as stage1
from tether_engine.atomic import publish_bytes
from tether_engine.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from tether_engine.journal import RunJournal
from tether_engine.provenance import InputGraph, catalog_index, check_role
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study.source_fact_adapters import _json_value, _source
from tether_engine.study.source_fact_sources import FIELD_FAMILIES, _publication, validate_task
from tether_engine.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files

ASSETS = stage1.ASSETS
PLAN_PATH = ASSETS / "INPUT-PLAN-DRAFT-v1.json"
READY_PATH = ASSETS / "INPUT-READY-v1.json"
CASE_PLAN_PATH = WORKSPACE / "data/derived/preprint-p05-source-validation-20261101T071713Z/selected-case-plan.json"
STAGE1_SEAL_PATH = CASE_PLAN_PATH.parent / "seal.json"
RAW_ROOT = stage1.RAW_ROOT
OUTPUT_ROOT = WORKSPACE / "data/derived"
OUTPUT_PREFIX = "preprint-p05-source-inputs-"
METHOD = "p05.original_only_generation_inputs.v1"
CUTOFF = "2026-11-01T07:16:26.101448+00:00"
LIMITS = {"compressed_input_bytes": 4 * 1024**3, "files": 137,
          "output_bytes": 512 * 1024**2, "case_product_bytes": 64 * 1024**2,
          "seconds": 1200, "batch_rows": 8192, "matching_rows_per_case": 100000}
GWAS_FIELDS = ("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")
CREDIBLE_IDENTITY = ("studyLocusId", "studyId", "variantId")
MEASUREMENTS = ("beta", "standardError", "pValueMantissa", "pValueExponent")
CORE_DATE_FIELDS = ("publicationDate", "evidenceDate", "annotationDate", "publicationYear")
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


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def utc(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as error:
        raise ContractError("Exact UTC timestamp required") from error
    need("T" in value and result.tzinfo is not None and result.utcoffset().total_seconds() == 0,
         "Exact UTC timestamp required")
    return result.astimezone(timezone.utc)


def code_paths():
    return sorted(stage1.framework_paths() + [Path(stage1.__file__).resolve(), Path(__file__).resolve()])


def code_pins():
    return {p.relative_to(WORKSPACE).as_posix(): digest(p.read_bytes()) for p in code_paths()}


def metadata_paths():
    return [p for p, _ in stage1.PINS.values()] + [stage1.PLAN_PATH, stage1.READY_PATH, CASE_PLAN_PATH, STAGE1_SEAL_PATH]


def route_contract(document, *, stage1_plan_sha256):
    """Routing identities only. Counts/availability fields never supply values."""
    need(document.get("schema_version") == 1 and document.get("role") == "neutral_metadata" and
         document.get("product_kind") == "neutral_selected_case_plan" and document.get("agent_visible") is False,
         "Only the sealed neutral selected-case routing plan is permitted")
    need(document.get("plan_sha256") == stage1_plan_sha256 and document.get("row_guard_cutoff_utc") == CUTOFF,
         "Neutral routing plan protocol/cutoff changed")
    need(document.get("no_replacement") is True and document.get("numeric_availability_used") is False and
         document.get("model_performance_used") is False and document.get("selection_seed") == stage1.SEED,
         "Neutral routing selection policy changed")
    cases = document.get("cases")
    need(type(cases) is list and 1 <= len(cases) <= 12 and len(cases) == document.get("actual_selected_units"),
         "Selected case count must remain 1..12")
    result = []
    for case in cases:
        need(type(case) is dict and re.fullmatch(r"p05-\d{2}", case.get("case_id", "")), "Invalid neutral case ID")
        key = stage1.unit_key(case)
        need(key is not None and case.get("release_id") == "25.09" and
             case.get("unit_hash") == stage1.unit_hash("25.09", key), "Invalid exact routing identity hash")
        result.append({k: case[k] for k in ("case_id", "targetId", "diseaseId", "studyLocusId", "release_id", "unit_hash")})
    need(len({c["case_id"] for c in result}) == len(result) and
         len({c["unit_hash"] for c in result}) == len(result), "Duplicate neutral routing identities")
    return result


def neutral_documents(deadline):
    docs = stage1.pinned_documents(deadline)
    inventory = stage1.inventory_from_metadata(docs["frame"], docs["acquisition"])
    stage1_plan_bytes = read_file(stage1.PLAN_PATH, deadline, 1024**2)
    old_plan = parse_json(stage1_plan_bytes)
    ready = parse_json(read_file(stage1.READY_PATH, deadline, 1024**2))
    stage1.validate_freeze(old_plan, stage1_plan_bytes, ready)
    need(ready.get("row_guard_cutoff_utc") == CUTOFF and
         old_plan.get("frame_descriptor_sha256") == fingerprint(inventory), "Frozen stage-1 frame changed")
    routing_bytes = read_file(CASE_PLAN_PATH, deadline, 1024**2)
    routing = parse_json(routing_bytes)
    cases = route_contract(routing, stage1_plan_sha256=digest(stage1_plan_bytes))
    # Seal is authentication metadata only. Never open any other stage-1 artifact.
    seal_bytes = read_file(STAGE1_SEAL_PATH, deadline, 4 * 1024**2)
    seal = parse_json(seal_bytes)
    selected = [a for a in seal.get("artifacts", ()) if a.get("path") == "selected-case-plan.json"]
    need(seal.get("status") == "completed_source_only_stage1" and len(selected) == 1 and
         selected[0].get("sha256") == digest(routing_bytes) and selected[0].get("bytes") == len(routing_bytes) and
         seal.get("plan_sha256") == digest(stage1_plan_bytes) and
         seal.get("ready_sha256") == hash_file(stage1.READY_PATH, deadline)["sha256"], "Stage-1 seal does not authenticate routing")
    need(not (CASE_PLAN_PATH.parent / "failure-seal.json").exists(), "Stage-1 has a terminal failure seal")
    return docs, inventory, cases, {"stage1_plan_sha256": digest(stage1_plan_bytes),
        "stage1_ready_sha256": hash_file(stage1.READY_PATH, deadline)["sha256"],
        "stage1_case_plan_sha256": digest(routing_bytes), "stage1_case_plan_bytes": len(routing_bytes),
        "stage1_seal_sha256": digest(seal_bytes)}, routing_bytes


def make_plan():
    """Metadata-only preparation; this function never opens an original payload."""
    deadline = time.monotonic() + 120
    with stable_files(metadata_paths() + code_paths(), deadline=deadline):
        docs, inventory, cases, auth, _ = neutral_documents(deadline)
        current_code, current_environment = code_pins(), stage1.environment()
    return {"schema_version": 1, "artifact_id": "preprint-p05-input-plan-v1", "status": "DRAFT",
        "scope": "p05_source_only_stage2_inputs", "actual_build_authorized": False,
        "build_gate": "external exact READY hash plus root READY binding these DRAFT bytes and all active code/environment; no original values before this gate",
        "code_sha256": current_code, "environment": current_environment, "limits": LIMITS,
        "row_guard_cutoff_utc": CUTOFF, "authentication": auth,
        "neutral_inputs": {k: {"path": str(p), "sha256": h} for k, (p, h) in stage1.PINS.items()},
        "selected_case_plan": str(CASE_PLAN_PATH), "stage1_seal": str(STAGE1_SEAL_PATH),
        "frame_descriptor_sha256": fingerprint(inventory), "original_file_count": len(inventory),
        "original_compressed_bytes": sum(i["bytes"] for i in inventory), "actual_selected_units": len(cases),
        "original_root": str(RAW_ROOT), "approved_derived_root": str(OUTPUT_ROOT), "output_prefix": OUTPUT_PREFIX,
        "literal_fields": {"gwas": list(GWAS_FIELDS), "credible_identity": list(CREDIBLE_IDENTITY), "credible_measurement": list(MEASUREMENTS)},
        "raw_projection": {"gwas_credible_sets": list(stage1.GWAS),
            "credible_set": list(CREDIBLE_IDENTITY + MEASUREMENTS + ("chromosome", "position", "sampleSize")),
            "guard_fields_if_present": list(dict.fromkeys(stage1.GUARD_FIELDS + CORE_DATE_FIELDS)),
            "core_scope_fields_if_present": ["targetId", "target_id", "diseaseId", "indication_id"]},
        "join_policy": "one exact studyLocusId one_to_many per physical eligible GWAS anchor; all eligible physical credible matches; locus-only, no composite identity/causality",
        "field_policy": "four native measurement fields grouped per physical credible row; native studyId/variantId separate identity requests; null/empty/absent preserved; no numerical inference",
        "scope_policy": {"action": None, "modality": None, "tissue": None, "namespace_versions": "explicit unknown"},
        "unknown_context": UNKNOWN_CONTEXT,
        "date_policy": "stage1 precision guards precede packet visibility; unchanged core native-date and wire representability checked separately; blocked cases retained without coercion/replacement",
        "mapping_policy": "fresh original target/disease/HGNC exact canonical uniqueness replay; no aliases, old mapping/capture values or previously built references",
        "roles": {"packets": "agent_evidence", "neutral_case_plan": "validated routing/config outside InputGraph", "receipts": "exact-byte transport archives"},
        "denied_inputs": ["human_responses_and_descendants", "old_candidate_answers", "private_gold", "P02_joins", "stage1_SQLite_and_quarantined_capture_mapping_coverage_values", "references_and_descendants"],
        "model_calls": 0, "network_calls": 0, "new_downloads": 0, "reference_calls": 0,
        "baselines": "later phase only", "scientific_claims": "technical literal reporting only; not clinical or independent studies",
        "resource_enforcement": "cooperative checkpoints, RSS samples, logical byte counters; physical I/O unmeasured; no hard OS watchdog"}


def validate_freeze(plan, plan_bytes, ready, expected_ready_sha256, ready_bytes, *, current_code=None, current_environment=None):
    need(type(expected_ready_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_ready_sha256) and
         digest(ready_bytes) == expected_ready_sha256, "Independent exact root READY hash required")
    need(plan.get("status") == "DRAFT" and plan.get("actual_build_authorized") is False and
         ready.get("schema_version") == 1 and ready.get("status") == "READY" and
         ready.get("scope") == "p05_source_only_stage2_inputs" and ready.get("frozen_by") == "root" and
         ready.get("actual_build_authorized") is True, "Root stage-2 input READY authorization required")
    need(ready.get("plan_sha256") == digest(plan_bytes), "READY does not bind exact DRAFT bytes")
    need(ready.get("code_sha256") == plan.get("code_sha256") == (code_pins() if current_code is None else current_code),
         "Frozen active implementation changed")
    need(ready.get("environment") == plan.get("environment") == (stage1.environment() if current_environment is None else current_environment),
         "Frozen environment changed")
    need(plan.get("limits") == LIMITS and ready.get("row_guard_cutoff_utc") == plan.get("row_guard_cutoff_utc") == CUTOFF and
         ready.get("stage1_case_plan_sha256") == plan.get("authentication", {}).get("stage1_case_plan_sha256"),
         "Frozen limits/cutoff/routing authorization changed")


class Bounds:
    def __init__(self, output, *, deadline=None):
        self.output = Path(output)
        self.started = time.monotonic()
        self.deadline = deadline if deadline is not None else self.started + LIMITS["seconds"]
        self.max_batch_arrow_bytes = 0
        self.peak_sampled_rss_bytes = None
        self.logical_hashed_bytes = 0
        self.logical_original_compressed_bytes_scanned = 0

    def check(self):
        deadline_check(self.deadline)
        try:
            import psutil
            rss = psutil.Process().memory_info().rss
            self.peak_sampled_rss_bytes = max(self.peak_sampled_rss_bytes or 0, rss)
        except (ImportError, OSError):
            pass
        size = sum(p.stat().st_size for p in self.output.rglob("*") if p.is_file()) if self.output.exists() else 0
        need(size <= LIMITS["output_bytes"], "Total stage-2 output exceeds bound")
        return size

    def observe(self, batch, **_):
        self.max_batch_arrow_bytes = max(self.max_batch_arrow_bytes, batch.nbytes)
        self.check()

    def publish_bytes(self, relative, payload, *, packet=False):
        need(not packet or len(payload) <= LIMITS["case_product_bytes"], "Per-case packet exceeds 64 MiB; no truncation")
        need(self.check() + len(payload) <= LIMITS["output_bytes"], "Total stage-2 output exceeds bound")
        publish_bytes(self.output / relative, payload)

    def publish(self, relative, value, **kwargs):
        self.publish_bytes(relative, canonical(value) + b"\n", **kwargs)

    def report(self):
        return {"bounds": LIMITS, "wall_seconds": time.monotonic() - self.started,
            "enforcement": "cooperative; no hard OS watchdog", "physical_io_bytes": None, "physical_io_status": "not_measured",
            "peak_sampled_process_rss_bytes": self.peak_sampled_rss_bytes,
            "rss_basis": "psutil process RSS at cooperative checkpoints; unavailable if null",
            "max_batch_arrow_bytes": self.max_batch_arrow_bytes, "logical_bytes_hashed": self.logical_hashed_bytes,
            "logical_original_compressed_bytes_scanned": self.logical_original_compressed_bytes_scanned,
            "output_bytes_before_report_and_seal": self.check()}


def verify_originals(inventory, bounds, catalog, *, raw_root=RAW_ROOT):
    """Caller holds all original and receipt locks; all hashes precede values."""
    index = catalog_index(catalog)
    need(len(inventory) == LIMITS["files"] and sum(i["bytes"] for i in inventory) <= LIMITS["compressed_input_bytes"],
         "Original frame count/byte bound changed")
    proofs = []
    for item in inventory:
        check_role(item["dataset_id"], stage1.original_role(item), index)
    for number, item in enumerate(inventory):
        path = checked_path(raw_root, item["relative_path"])
        need(path == Path(item["path"]), "Original logical/physical path mismatch")
        actual = dict(hash_file(path, bounds.deadline))
        need(actual == {"sha256": item["sha256"], "bytes": item["bytes"]}, "Original hash/size mismatch")
        bounds.logical_hashed_bytes += actual["bytes"]
        proofs.append({**item, "source_id": f"original-{number:03d}", "verified_payload": actual})
        bounds.check()
    for item in proofs:
        receipt = item["receipt"]
        relative = Path(receipt["path"]).relative_to(raw_root).as_posix()
        path = checked_path(raw_root, relative)
        payload = read_file(path, bounds.deadline, min(receipt["bytes"], 1024**2))
        need(len(payload) == receipt["bytes"] and digest(payload) == receipt["sha256"], "Receipt hash/size mismatch")
        bounds.logical_hashed_bytes += len(payload)
        document = parse_json(payload)
        stage1.check_receipt_identity(document, item, source_id=item["source_id"])
        observed = utc(document["completed_at_utc"])
        need(observed <= utc(CUTOFF), "Original receipt is newer than frozen information cutoff")
        item["completed_at_utc"] = observed.isoformat()
        item["receipt_archive"] = "_private/receipts/" + receipt["sha256"] + ".json"
        item["receipt_relative_path"] = relative
        bounds.publish_bytes(item["receipt_archive"], payload)
    return proofs


def original_snapshot(proofs, catalog, output, *, raw_root=RAW_ROOT):
    cutoff = utc(CUTOFF)
    nodes = []
    for item in proofs:
        observed = utc(item["completed_at_utc"])
        availability = Availability(None, None, None, None, observed.date(), "public_download_receipt",
            "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown",
            observed, item["receipt"]["sha256"])
        nodes.append(SourceNode(item["source_id"], item["dataset_id"], item["release_id"], item["relative_path"],
            item["sha256"], stage1.original_role(item), availability, TemporalClass.CONTEMPORARY, item["source_url"],
            receipt_path=item["receipt_relative_path"], receipt_sha256=item["receipt"]["sha256"]))
    snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(raw_root),
        {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
    graph = InputGraph(snapshot, output, catalog_index(catalog))
    need(graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=cutoff)) is None,
         "Full original graph is not eligible at frozen cutoff")
    return snapshot


def selected_projection(item):
    required = stage1.GWAS if item["family"] == "gwas_credible_sets" else CREDIBLE_IDENTITY + MEASUREMENTS + ("chromosome", "position", "sampleSize")
    need(set(required) <= set(item["fields"]) and len(item["fields"]) == len(set(item["fields"])), "Frozen literal source schema changed")
    automatic = stage1.GUARD_FIELDS + CORE_DATE_FIELDS + ("targetId", "target_id", "diseaseId", "indication_id")
    return tuple(required) + tuple(k for k in dict.fromkeys(automatic) if k in item["fields"] and k not in required)


def matching_rows(item, cases, bounds):
    """Arrow-filter original rows; preserve row-group and row-in-group locators."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    need(pa.__version__ == "21.0.0", "Frozen Arrow 21.0.0 required")
    source = pq.ParquetFile(item["path"])
    need(source.schema_arrow.names == item["fields"] and source.metadata.num_rows == item["rows"], "Original schema/footer changed")
    projection = selected_projection(item)
    physical = 0
    for group in range(source.num_row_groups):
        offset = 0
        for batch in source.iter_batches(batch_size=LIMITS["batch_rows"], row_groups=[group], columns=list(projection), use_threads=False):
            bounds.observe(batch)
            for case in cases:
                mask = pc.equal(batch.column("studyLocusId"), case["studyLocusId"])
                if item["family"] == "gwas_credible_sets":
                    mask = pc.and_(mask, pc.and_(pc.equal(batch.column("targetId"), case["targetId"]), pc.equal(batch.column("diseaseId"), case["diseaseId"])))
                indices = pc.indices_nonzero(pc.fill_null(mask, False)).to_pylist()
                rows = batch.take(pa.array(indices, type=pa.int64())).to_pylist()
                for index, row in zip(indices, rows):
                    yield case["case_id"], {"source_id": item["source_id"], "family": item["family"],
                        "locator": {"format": "parquet", "row_group": group, "row": offset + index},
                        "physical_row_0based": physical + offset + index, "values": row}
            offset += batch.num_rows
        need(offset == source.metadata.row_group(group).num_rows, "Incomplete original row-group scan")
        physical += offset
    bounds.logical_original_compressed_bytes_scanned += item["bytes"]


def select_eligible(cases, proofs, indexes, bounds, progress=None):
    selected = {case["case_id"]: {"gwas_credible_sets": [], "credible_set": []} for case in cases}
    excluded = {case["case_id"]: [] for case in cases}
    for item in proofs:
        family = item["family"]
        if family not in ("gwas_credible_sets", "credible_set"):
            continue
        for case_id, record in matching_rows(item, cases, bounds):
            # Eligibility decision precedes raw-row retention or packet visibility.
            decision = (stage1.eligibility(record["values"], indexes, cutoff=utc(CUTOFF)) if family == "gwas_credible_sets" else
                        {"date_guard": stage1.date_guard(record["values"], utc(CUTOFF))})
            reasons = list(decision.get("exclusion_reasons", decision["date_guard"]["exclusion_reasons"]))
            # Core replay automatically reads annotationDate as well. Apply the
            # same native precision policy independently, without altering the
            # already frozen stage-1 selector or publication interval logic.
            if "annotationDate" in record["values"]:
                try:
                    lower, upper, _ = stage1.source_date_interval(record["values"]["annotationDate"], "annotationDate")
                    status = "unknown" if lower is None else stage1.interval_status(lower, upper, utc(CUTOFF))
                    if status not in ("unknown", "within_cutoff"):
                        reasons.append("annotationDate_" + status)
                except (ContractError, ValueError, TypeError, OverflowError):
                    reasons.append("annotationDate_invalid_explicit_date")
            if reasons:
                excluded[case_id].append({"source_id": record["source_id"], "family": family, "locator": record["locator"],
                    "exclusion_reasons": list(reasons)})
            else:
                selected[case_id][family].append(record)
            need(sum(len(v) for v in selected[case_id].values()) + len(excluded[case_id]) <= LIMITS["matching_rows_per_case"],
                 "Selected physical-row safety bound exceeded; no truncation")
        if progress:
            progress("original_file_scanned", source_id=item["source_id"], family=family,
                selected_eligible_rows=sum(len(rows) for groups in selected.values() for rows in groups.values()))
        bounds.check()
    return selected, excluded


def normalization_proof(case, gwas, indexes):
    need(bool(gwas), "No eligible physical GWAS anchor remains; retain blocked case")
    for record in gwas:
        need(stage1.unit_key(record["values"]) == stage1.unit_key(case) and
             stage1.eligibility(record["values"], indexes, cutoff=utc(CUTOFF))["eligible"], "Original anchor normalization failed")
    target = indexes["target"][case["targetId"]]
    disease = indexes["disease"][case["diseaseId"]]
    hgnc = indexes["hgnc"][case["targetId"]]
    need(len(target) == len(disease) == len(hgnc) == 1, "Original canonical mapping is not unique")
    return {"method": "fresh exact original canonical target/HGNC/disease replay", "target_id_from_raw_GWAS": case["targetId"],
        "indication_id_from_raw_GWAS": case["diseaseId"], "no_alias_or_variant_inference": True,
        "target_original": target[0], "disease_original": disease[0], "hgnc_original": hgnc[0],
        "upstream_namespace_versions": {"target": "unknown", "indication": "unknown"}, "other_exposure": "UNKNOWN"}


def native_representability(record, case=None):
    """Pure preflight using unchanged core/adapter guards; no expected facts."""
    row = record["values"]
    _publication(row, utc(CUTOFF))
    if case is not None:
        for name, expected in (("targetId", "targetId"), ("target_id", "targetId"), ("diseaseId", "diseaseId"), ("indication_id", "diseaseId")):
            need(name not in row or row[name] is None or row[name] == case[expected], "Native automatic core scope field disagrees")
    for name, value in row.items():
        _json_value(value)
        if name in MEASUREMENTS and value is not None and value != "" and value != [] and value != {}:
            need(type(value) in (int, float) and (type(value) is not float or math.isfinite(value)), "Native measurement requires finite int/float excluding Boolean")
            need(name != "pValueExponent" or type(value) is int, "Native pValueExponent requires int")


def build_task(case, groups):
    records, fields, keys = [], [], {"gwas_credible_sets": [], "credible_set": []}
    for family in ("gwas_credible_sets", "credible_set"):
        for number, original in enumerate(groups[family]):
            key = ("gwas" if family == "gwas_credible_sets" else "credible") + f"-{number:04d}"
            keys[family].append(key)
            row = original["values"]
            required = ("targetId", "diseaseId", "studyLocusId") if family == "gwas_credible_sets" else ("studyLocusId",)
            identity = {k: row[k] for k in required}
            identity.update({k: row[k] for k in ("id", "studyId", "variantId") if k in row and row[k] is not None and row[k] != ""})
            records.append({"record_key": key, "source_id": original["source_id"], "locator": original["locator"], "identity": identity})
            names = GWAS_FIELDS if family == "gwas_credible_sets" else CREDIBLE_IDENTITY + MEASUREMENTS
            for name in names:
                family_name = FIELD_FAMILIES[name]
                fields.append({"record_key": key, "field": name, "family": family_name,
                    "group": ("measurement:" if name in MEASUREMENTS else "identity:") + key,
                    "unit_field": None, "empty_policy": "unknown"})
    task = {"schema_version": 1, "task_id": "p05-" + case["case_id"] + "-native-locus-v1",
        "scope": {"target_id": case["targetId"], "indication_id": case["diseaseId"],
            "target_namespace_version": "unknown", "indication_namespace_version": "unknown", "action": None, "modality": None, "tissue": None},
        "cutoff": CUTOFF, "profile": "contemporary_assessment", "primary_families": ["reported_measurement"],
        "records": records, "fields": fields,
        "joins": [{"join_id": "locus:" + key, "left_record": key, "left_field": "studyLocusId",
            "right_records": keys["credible_set"], "right_field": "studyLocusId", "cardinality": "one_to_many", "inventory_status": "complete"}
            for key in keys["gwas_credible_sets"]],
        "collection": {"status": "selected_records", "reason": "All eligible selected physical rows in the pinned original frame only; source-locus reporting, no biological absence claim."}}
    return encode(validate_task(task))


def wire_size_upper_bound(task, rawrows, slots):
    """Prove space for literal reporting without constructing an answer object.

    Count both a native value and a 64-character unknown-reason allowance per
    request. This deliberately overbounds either alternative; it does not derive
    reference unknowns, joins, expected values, or an answer projection. A case
    whose fit cannot be proved is retained as blocked rather than truncated.
    """
    rows = {row["record_key"]: row["values"] for row in rawrows}
    envelope = len(b'{"schema_version":1,"task_id":,"task_sha256":,"status":,"facts":[],"collection_status":,"reason":null}')
    size = envelope + len(canonical(task["task_id"])) + len(canonical(fingerprint(task)))
    size += len(canonical("insufficient_input")) + len(canonical("zero_matches_selected_collection"))
    overhead = len(b'{"fact_id":,"value":,"unit":null,"source":,"unknown_reason":}')
    for slot in slots:
        raw = rows[slot["record_key"]]
        value_bytes = len(canonical(raw[slot["field"]])) if slot["field"] in raw else 4
        size += overhead + len(canonical(slot["fact_id"])) + max(4, value_bytes) + len(canonical(slot["source"])) + 66
    return size + max(0, len(slots) - 1)


def make_packet(case, groups, mapping, snapshot, proofs, plan_sha256, *, computed_at, routing_sha256):
    for originals in groups.values():
        for record in originals:
            native_representability(record, case)
    task = build_task(case, groups)
    task_hash = fingerprint(task)
    nodes = {node.source_id: node for node in snapshot.sources}
    slots, rawrows = [], []
    originals = groups["gwas_credible_sets"] + groups["credible_set"]
    for request, original in zip(task["records"], originals):
        rawrows.append({"record_key": request["record_key"], **original})
    for request in task["fields"]:
        record = next(r for r in task["records"] if r["record_key"] == request["record_key"])
        node = nodes[record["source_id"]]
        source = {"source_id": node.source_id, "sha256": node.sha256, "release_id": node.release_id,
            "locator": record["locator"], "field": request["field"]}
        _source(source)
        identity = {"task_sha256": task_hash, "scope": task["scope"], "record_key": record["record_key"], "source": source}
        slots.append({"fact_id": "fact:" + fingerprint(identity), "record_key": record["record_key"], "field": request["field"], "source": source})
    wire_bound = wire_size_upper_bound(task, rawrows, slots)
    need(wire_bound <= 262144, "Common-wire serialized-size upper bound exceeds 256 KiB; exact fit unproven, case blocked without truncation")
    parents = [{"kind": "original", "source_id": n.source_id, "sha256": n.sha256} for n in snapshot.sources]
    packet = {"schema_version": 1, "packet_type": METHOD, "case_id": case["case_id"], "role": "agent_evidence", "agent_visible": True,
        "neutral_task": task, "task_sha256": task_hash, "source_records": rawrows, "fact_skeleton": slots,
        "normalization_proof": mapping, "source_nodes": encode(snapshot.sources), "source_proofs": proofs,
        "unknown_context": UNKNOWN_CONTEXT,
        "instruction": "Report requested literal native original fields using typed_facts_v1 and exact physical source bindings. Preserve absent/null/empty distinctions. Locus joins assert no composite identity or causality. Do not derive p-values, standard errors, scales, alleles, gene/action effects or clinical claims.",
        "output_contract": {"wire_format": "typed_facts_v1", "max_facts": 512, "max_output_bytes": 262144,
            "literal_wire_size_upper_bound_bytes": wire_bound, "wire_size_basis": "native field byte lengths plus bounded structural allowance; no expected facts constructed",
            "top_level_keys": ["schema_version", "task_id", "task_sha256", "status", "facts", "collection_status", "reason"],
            "fact_keys": ["fact_id", "value", "unit", "source", "unknown_reason"]},
        "lineage": {"method": METHOD, "computed_at": computed_at, "input_refs": parents + [
            {"kind": "neutral_config", "sha256": plan_sha256}, {"kind": "neutral_selected_case_plan", "sha256": routing_sha256}],
            "information_cutoff": CUTOFF, "reference_inputs": [], "evaluation_inputs": [], "generation_authority": False}}
    need(len(canonical(packet)) + 1 <= LIMITS["case_product_bytes"], "Complete packet exceeds 64 MiB; no truncation")
    return packet


def validate_output_location(output):
    output = Path(output)
    need(output.is_absolute() and output.parent == OUTPUT_ROOT and
         re.fullmatch(OUTPUT_PREFIX + r"\d{8}T\d{6}Z", output.name), "Exclusive approved data/derived stage-2 output location required")
    need(checked_path(WORKSPACE, output.parent.relative_to(WORKSPACE).as_posix()) == output.parent and
         output.parent.is_dir(), "Unsafe output parent")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", str(output)], cwd=WORKSPACE, capture_output=True, check=False)
    need(ignored.returncode == 0, "Stage-2 output must be ignored before reservation")
    try:
        output.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ContractError("Output leaf already exists; inspect only, no resume/overwrite")
    return output


def failure_seal(output, stage, error):
    # Fresh deadline only for bounded terminal metadata; no more original reads.
    deadline = time.monotonic() + 30
    artifacts = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in ("seal.json", "failure-seal.json", "journal.jsonl"):
            continue
        item = {"path": path.relative_to(output).as_posix()}
        try:
            item.update(dict(hash_file(path, deadline)), hash_status="verified")
        except BaseException as hash_error:
            item.update(sha256=None, bytes=None, hash_status="unavailable:" + type(hash_error).__name__)
        artifacts.append(item)
    publish_bytes(output / "failure-seal.json", canonical({"schema_version": 1, "status": "failed_stage2_partial_not_usable",
        "stage": stage, "error_class": type(error).__name__, "retained_artifacts": artifacts,
        "reuse_policy": "inspect only; new READY/build in a fresh directory required", "model_calls": 0, "reference_calls": 0}) + b"\n")


def execute(output, *, expected_ready_sha256):
    output = validate_output_location(output)
    journal = RunJournal(output, kind="build")
    bounds = Bounds(output)
    stack = ExitStack()
    stage = "root_authorization"
    try:
        need(checked_path(WORKSPACE, output.relative_to(WORKSPACE).as_posix()) == output and output.is_dir(),
             "Unsafe exclusively reserved output path")
        journal.append("build_stage", stage=stage)
        stack.enter_context(stable_files(metadata_paths() + [PLAN_PATH, READY_PATH] + code_paths(), deadline=bounds.deadline))
        plan_bytes = read_file(PLAN_PATH, bounds.deadline, 1024**2)
        ready_bytes = read_file(READY_PATH, bounds.deadline, 1024**2)
        plan, ready = parse_json(plan_bytes), parse_json(ready_bytes)
        validate_freeze(plan, plan_bytes, ready, expected_ready_sha256, ready_bytes)
        need(plan == make_plan(), "DRAFT differs from current exact neutral protocol")
        docs, inventory, cases, auth, routing_bytes = neutral_documents(bounds.deadline)
        need(auth == plan["authentication"], "Original neutral authentication changed")
        bounds.publish_bytes("selected-case-plan.json", routing_bytes)
        recipe_paths = metadata_paths() + [PLAN_PATH, READY_PATH] + code_paths()
        recipe = []
        for number, path in enumerate(recipe_paths):
            payload = read_file(path, bounds.deadline, 64 * 1024**2)
            logical = path.relative_to(WORKSPACE).as_posix()
            if logical in plan["code_sha256"]:
                need(digest(payload) == plan["code_sha256"][logical], "Archived code differs from frozen implementation")
            relative = "_private/recipe/" + f"{number:02d}-" + path.name
            bounds.publish_bytes(relative, payload)
            recipe.append({"logical_path": logical, "archive_path": relative, "sha256": digest(payload), "bytes": len(payload)})
        stage = "verify_all_originals_before_values"
        journal.append("build_stage", stage=stage)
        paths = [Path(i["path"]) for i in inventory] + [Path(i["receipt"]["path"]) for i in inventory]
        stack.enter_context(stable_files(paths, deadline=bounds.deadline))
        proofs = verify_originals(inventory, bounds, docs["catalog"], raw_root=RAW_ROOT)
        snapshot = original_snapshot(proofs, docs["catalog"], output, raw_root=RAW_ROOT)
        journal.append("all_originals_admitted_before_values", files=len(proofs), original_bytes=sum(p["bytes"] for p in proofs))
        stage = "fresh_original_normalization_and_inventory"
        journal.append("build_stage", stage=stage)
        small, _ = stage1.load_small(proofs, bounds)
        indexes = stage1.mapping_index(small)
        selected, excluded = select_eligible(cases, proofs, indexes, bounds, journal.append)
        stage = "assemble_generation_inputs"
        journal.append("build_stage", stage=stage)
        coverage, packet_paths = {}, []
        computed_at = datetime.now(timezone.utc).isoformat()
        # Only literal-original proof metadata enters packets; never an expected-value projection.
        retained_proofs = [{"source_id": p["source_id"], "dataset_id": p["dataset_id"], "release_id": p["release_id"],
            "path": p["relative_path"], "sha256": p["sha256"], "bytes": p["bytes"], "role": stage1.original_role(p),
            "receipt_path": p["receipt_relative_path"], "receipt_sha256": p["receipt"]["sha256"], "receipt_bytes": p["receipt"]["bytes"],
            "receipt_archive": p["receipt_archive"], "availability": encode(snapshot.sources[number].availability)} for number, p in enumerate(proofs)]
        for case in cases:
            case_id, groups = case["case_id"], selected[case["case_id"]]
            base = {"eligible_physical_gwas_rows": len(groups["gwas_credible_sets"]), "eligible_physical_credible_rows": len(groups["credible_set"]),
                "excluded_physical_rows": len(excluded[case_id]), "excluded_reasons": dict(Counter(r for row in excluded[case_id] for r in row["exclusion_reasons"])),
                "excluded_values_disclosed": False, "replacement": False, "complete_original_inventory_scanned": True}
            try:
                mapping = normalization_proof(case, groups["gwas_credible_sets"], indexes)
                packet = make_packet(case, groups, mapping, snapshot, retained_proofs, digest(plan_bytes), computed_at=computed_at,
                    routing_sha256=auth["stage1_case_plan_sha256"])
            except ContractError as error:
                coverage[case_id] = {**base, "status": "blocked_retained_no_replacement", "failure_class": "API_or_native_representability_or_normalization",
                    "reason": str(error), "measurement_coverage": None, "pass": None}
                journal.append("case_retained_blocked", case_id=case_id, error_class=type(error).__name__)
                continue
            relative = "packets/" + case_id + ".json"
            bounds.publish(relative, packet, packet=True)
            packet_paths.append(relative)
            coverage[case_id] = {**base, "status": "packet_created", "task_sha256": packet["task_sha256"],
                "measurement_groups": len(groups["credible_set"]), "measurement_coverage": None, "pass": None,
                "zero_credible_policy": "no invented slots; measurement denominator/pass null" if not groups["credible_set"] else "not_scored_in_input_phase"}
            journal.append("case_packet_prepared", case_id=case_id, records=len(packet["neutral_task"]["records"]), fields=len(packet["neutral_task"]["fields"]))
        bounds.publish("source-snapshot.json", encode(snapshot))
        bounds.publish("original-inventory-proofs.json", retained_proofs)
        bounds.publish("excluded-locators.json", {"role": "neutral_metadata", "agent_visible": False, "cases": excluded, "excluded_values": "not_retained"})
        bounds.publish("coverage.json", {"schema_version": 1, "role": "neutral_metadata", "agent_visible": False,
            "actual_selected_units": len(cases), "cases": coverage, "selection_scope": "sealed 1..12 original routing units; no replacements", "reference_calls": 0, "model_calls": 0})
        bounds.publish("lineage.json", {"schema_version": 1, "method": METHOD, "computed_at": computed_at,
            "information_cutoff": CUTOFF, "original_nodes": encode(snapshot.sources), "original_proofs": retained_proofs,
            "neutral_configuration": {"plan_sha256": digest(plan_bytes), "ready_sha256": digest(ready_bytes), **auth},
            "neutral_metadata_is_graph_input": False, "recipe_archive": recipe,
            "products": [{"path": p, "role": "agent_evidence", "agent_visible": True,
                "parents": [n.source_id for n in snapshot.sources], "neutral_config_sha256": digest(plan_bytes),
                "neutral_selected_case_plan_sha256": auth["stage1_case_plan_sha256"]} for p in packet_paths],
            "forbidden_value_parents": plan["denied_inputs"], "references": "not_created", "model_calls": 0})
        bounds.publish("resource-report.json", bounds.report())
        stage = "seal"
        journal.append("build_stage", stage=stage)
        artifacts = [{"path": p.relative_to(output).as_posix(), **dict(hash_file(p, bounds.deadline))}
                     for p in sorted(output.rglob("*")) if p.is_file() and p.name != "journal.jsonl"]
        seal = {"schema_version": 1, "status": "completed_source_only_stage2_inputs", "plan_sha256": digest(plan_bytes),
            "ready_sha256": digest(ready_bytes), "artifacts": artifacts, "packet_count": len(packet_paths), "selected_case_count": len(cases),
            "blocked_case_count": len(cases) - len(packet_paths), "journal_prefix_sha256": journal.events[-1]["sha256"],
            "references": "not_created", "outputs": "not_created", "baselines": "not_created", "model_calls": 0, "network_calls": 0,
            "source_mutations": 0, "validity_requires": "terminal build_completed binding this seal; no failure-seal.json"}
        stage = "terminal_cleanup"
        stack.close()
        bounds.check()
        journal.append("build_completed", seal_sha256=fingerprint(seal), stage2_inputs_only=True)
        journal.close()
        bounds.publish("seal.json", seal)
        return seal
    except BaseException as error:
        try:
            stack.close()
        except BaseException as cleanup:
            error.add_note("Input lock cleanup failed: " + type(cleanup).__name__)
        try:
            journal.fail(error, stage)
        except BaseException as cleanup:
            error.add_note("Failure journal append failed: " + type(cleanup).__name__)
        try:
            journal.close()
        except BaseException as cleanup:
            error.add_note("Failure journal close failed: " + type(cleanup).__name__)
        try:
            failure_seal(output, stage, error)
        except BaseException as cleanup:
            error.add_note("Terminal failure-seal publication failed: " + type(cleanup).__name__)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--draft", action="store_true")
    mode.add_argument("--build", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ready-sha256")
    args = parser.parse_args(argv)
    if args.draft:
        need(args.output is None and args.ready_sha256 is None, "DRAFT does not accept build arguments")
        plan = make_plan()
        publish_bytes(PLAN_PATH, canonical(plan) + b"\n")
        print(canonical({"status": "DRAFT", "plan": str(PLAN_PATH), "sha256": digest(PLAN_PATH.read_bytes()), "original_values_read": 0}).decode())
    else:
        need(args.output is not None and args.ready_sha256 is not None, "Build requires output and independent exact READY hash")
        seal = execute(args.output, expected_ready_sha256=args.ready_sha256)
        print(canonical({"status": seal["status"], "output": str(args.output), "packet_count": seal["packet_count"]}).decode())


if __name__ == "__main__":
    main()
