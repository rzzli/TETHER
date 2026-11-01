"""Finite, additive, evaluator-only GWAS field-availability scan for P02.

Run --freeze first, then --run. Neither mode downloads data, calls a model,
changes original sources, or creates an agent-visible evidence manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sys
import time
import tracemalloc

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INSPECTION = ROOT / "data/derived/literature-coverage-20261017T082208Z/inspection.json"
INSPECTION_SHA = "f523b156957107afa0bfcd2fc111d70ef269950e367006ff70349effc56f1226"
PLAN_PATH = HERE / "GWAS-SCAN-PLAN-v1.json"
REPORT_PATH = HERE / "GWAS-SCAN-REPORT-v1.json"
CATALOG_PATH = ROOT / "data/catalog/sources.json"
PROTOTYPE_PATH = HERE / "prototype.py"
RAW_ROOT = Path("E:/projects_data/drug_target_agents_data")
PARTITION = "raw/open_targets_platform/25.09/output/evidence/sourceId=gwas_credible_sets/"
MEASUREMENTS = (
    "beta", "betaConfidenceIntervalLower", "betaConfidenceIntervalUpper",
    "oddsRatio", "oddsRatioConfidenceIntervalLower", "oddsRatioConfidenceIntervalUpper",
    "pValueExponent", "pValueMantissa", "log2FoldChangePercentileRank", "log2FoldChangeValue",
)
QUALITATIVE = ("variantEffect", "directionOnTrait", "targetModulation")
STUDY_CONTEXT = (
    "ancestry", "ancestryId", "cellType", "biosamplesFromSource", "alleleOrigins",
    "allelicRequirements", "diseaseCellLines", "sex", "studyCases",
    "studyCasesWithQualifyingVariants", "studySampleSize",
)
LINKAGE = (
    "studyId", "biologicalModelId", "studyLocusId", "targetInModelEnsemblId",
    "targetInModelMgiId", "variantFromSourceId", "variantFunctionalConsequenceId",
    "variantHgvsId", "variantId", "variantRsId",
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": path.stat().st_size, "sha256": digest(path)}


def read_pinned(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Pinned metadata changed: " + str(path))
    return json.loads(raw)


def save_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    return pin(path)


def load_prototype():
    spec = importlib.util.spec_from_file_location("p02_gwas_projection_helpers", PROTOTYPE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot import bounded P02 helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output_path(plan):
    output = ROOT / plan["private_output"]
    if not output.resolve().is_relative_to((ROOT / "data/benchmark/gold_evidence").resolve()):
        raise ValueError("Private output escaped its authorized root")
    return output


def freeze():
    if PLAN_PATH.exists() or REPORT_PATH.exists():
        raise FileExistsError("Preserve existing v1 plan/report; no automatic rerun or replacement")
    helpers = load_prototype()
    inspection = read_pinned(INSPECTION, INSPECTION_SHA)
    selected = sorted(
        (entry for entry in inspection["files"]
         if entry["source"]["dataset_id"] == "ot_evidence"
         and entry["source"]["path"].startswith(PARTITION)),
        key=lambda entry: (entry["source"]["source_id"], entry["source"]["path"]),
    )
    if (len(selected) != 100 or sum(entry["bytes"] for entry in selected) != 180049263
            or sum(entry["rows"] for entry in selected) != 1753850):
        raise ValueError("Bounded GWAS source-frame counts changed")
    if len({entry["source"]["source_id"] for entry in selected}) != 100:
        raise ValueError("Duplicate source IDs in bounded source frame")
    for entry in selected:
        source = entry["source"]
        if (source["release_id"] != "25.09" or source["role"] != "agent_evidence"
                or source["parents"] or source["computed_at"] is not None):
            raise ValueError("Unexpected original source role, release, or lineage")
    old_plan = read_pinned(helpers.PLAN, helpers.PLAN_SHA)
    pairs = read_pinned(helpers.CACHE / "candidate-pair-metadata.json", helpers.PAIRS_SHA)
    contexts = [{"unit_id": context["symbol"].lower() + "-" + context["indication_id"].lower(),
                 "symbol": context["symbol"], "target_id": context["target_id"],
                 "disease_id": context["indication_id"], "prior_scope": "fixed_literature_development"}
                for context in old_plan["contexts"]]
    zero = sorted((pair for pair in pairs if pair["physical_matches"] == 0),
                  key=lambda pair: (pair["symbol"], pair["disease_id"]))[0]
    if (zero["symbol"], zero["target_id"], zero["disease_id"]) != (
            "FCGRT", "ENSG00000104870", "EFO_0000384"):
        raise ValueError("Prior first zero-match pair changed")
    contexts.append({"unit_id": zero["symbol"].lower() + "-" + zero["disease_id"].lower(),
                     "symbol": zero["symbol"], "target_id": zero["target_id"],
                     "disease_id": zero["disease_id"],
                     "prior_scope": "zero_matches_in_retained_literature_collection_only"})
    if len(contexts) != 3 or {context["symbol"] for context in contexts} != {"BTK", "CTLA4", "FCGRT"}:
        raise ValueError("Only the three existing development units are authorized")
    fields = list(helpers.IDENTITY_FIELDS + helpers.CONTEXT_FIELDS + helpers.SCIENTIFIC_FIELDS)
    if (len(fields) != 44 or len(helpers.SCIENTIFIC_FIELDS) != 34
            or set(MEASUREMENTS + QUALITATIVE + STUDY_CONTEXT + LINKAGE) != set(helpers.SCIENTIFIC_FIELDS)):
        raise ValueError("Typed-field contract changed")
    forbidden = {"textMiningSentences", "score", "resourceScore", "confidence"}
    if forbidden.intersection(fields) or any(field.startswith("clinical") for field in fields):
        raise ValueError("Forbidden narrative, clinical, or provider-score column")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    private = ROOT / "data/benchmark/gold_evidence" / ("preprint-p02-gwas-" + stamp)
    private.mkdir(exist_ok=False)
    save_new(private / "attempt.json", {"started_at_utc": utcnow(), "role": "evaluation_only",
                                       "stage": "metadata_only_plan_reservation", "raw_reads": 0,
                                       "model_calls": 0, "new_downloads": 0})
    plan = {
        "schema_version": 1, "protocol": "preprint_p02_additive_gwas_availability.v1",
        "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
        "created_at_utc": utcnow(), "raw_originals_read_before_freeze": False,
        "purpose": "Additive development field feasibility, preserving the literature-only v1 result",
        "inspection": pin(INSPECTION), "catalog_current": pin(CATALOG_PATH),
        "catalog_historical_sha256_reported_by_inspection": inspection["catalog_sha256"],
        "catalog_policy": "Preserve historical catalog hash; enforce pinned current catalog roles, without claiming byte equality",
        "code": pin(Path(__file__)), "projection_helpers": pin(PROTOTYPE_PATH),
        "prior_selection_parents": [pin(helpers.PLAN), pin(helpers.CACHE / "candidate-pair-metadata.json")],
        "private_output": str(private.relative_to(ROOT)).replace("\\", "/"),
        "raw_root_read_only": str(RAW_ROOT), "partition": PARTITION,
        "files": selected, "scheduled_files": 100, "scheduled_original_bytes": 180049263,
        "scheduled_physical_rows": 1753850, "contexts": contexts,
        "fields": {"identity": list(helpers.IDENTITY_FIELDS), "context": list(helpers.CONTEXT_FIELDS),
                   "scientific_legacy_family": list(helpers.SCIENTIFIC_FIELDS)},
        "scientific_subgroups": {"reported_measurements": list(MEASUREMENTS),
                                  "reported_qualitative_annotations": list(QUALITATIVE),
                                  "study_sample_context": list(STUDY_CONTEXT),
                                  "study_model_variant_identifiers": list(LINKAGE)},
        "matching": "Exact targetId AND diseaseId; no ontology expansion, entity inference, or source replacement",
        "selection": {"cap_unique_record_ids_per_unit": 3,
                      "order": ["record.id", "source.source_id", "row_group", "original_row"],
                      "duplicates": "Count all physical matches; choose earliest locator for each selected unique ID; do not assume independent studies",
                      "invalid_record_id": "Stop rather than select by values or repair IDs",
                      "availability_or_performance_selection": False},
        "all_matching_rows": "Aggregate field schema/null/nonnull/empty/nonfinite counts only; retain values for at most the first three unique record IDs per unit",
        "eligibility": "Rehash every original and receipt; require original parent-free agent_evidence role, catalog permission, exact release/path/schema and contemporary availability",
        "insufficient_input": "Only completed 100-file exact-pair scan can establish zero matches in this partition; never biological absence",
        "baseline": "Exact copies of nonnull eligible typed fields with unchanged values, units=None and original locators; a constructive ceiling, not an LLM comparison",
        "primary_measurement": "Report 10 measurement-component fields separately from study/linkage IDs; components and repeated mappings are not independent findings",
        "numeric_policy": "No transforms, inferred units, effect interpretation, or narrative extraction; nonfinite or nonnumeric populated measurement fields are reported and stop selected-value projection",
        "descendant_role": "evaluation_only_for_all_descendants",
        "resource_policy": "Measure elapsed/CPU, Python/Arrow allocation peaks and logical rows/bytes; process RSS and physical storage I/O remain unmeasured",
        "failure_policy": "Persist failure and partial collection accounting; stop without retries, substitutions, or a zero-match claim",
        "prohibited": ["human_response", "AI_reference_or_candidate", "protected_outcome", "narrative_projection",
                       "clinical_fields", "provider_source_scores", "network", "downloads", "raw_root_writes",
                       "agent_manifest", "P03_framework"],
    }
    proof = save_new(PLAN_PATH, plan)
    marker = save_new(private / "PLAN-FROZEN.json", {"frozen_at_utc": utcnow(), "plan": proof,
                                                    "raw_originals_read": 0,
                                                    "role": "evaluation_only"})
    print(canonical({"status": "PLAN_FROZEN_BEFORE_RAW_READS", "plan": proof, "marker": marker,
                     "private_output": plan["private_output"]}))


def safe_raw_child(relative):
    # Reject traversal and every Windows reparse point, including junctions.
    pure = PurePosixPath(relative.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or ":" in relative:
        raise ValueError("Unsafe original/receipt path")
    base = RAW_ROOT.absolute()
    candidate = base.joinpath(*pure.parts)
    if not candidate.resolve().is_relative_to(base.resolve()):
        raise ValueError("Original/receipt escaped the read-only raw root")
    for component in (candidate,) + tuple(candidate.parents):
        metadata = component.lstat()
        if component.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("Symlink/reparse original path denied: " + str(component))
    if not candidate.is_file():
        raise ValueError("Original/receipt is not a regular file")
    return candidate


def empty_counts():
    return {"rows": 0, "schema_absent": 0, "null": 0, "nonnull": 0,
            "empty_nonnull": 0, "nonfinite_numeric": 0, "nonnumeric_measurement": 0}


def add_counts(target, values):
    for key, value in values.items():
        target[key] += value


def field_counts(table, field, pa, pc):
    count = table.num_rows
    result = empty_counts()
    result["rows"] = count
    if field not in table.column_names:
        result["schema_absent"] = count
        return result
    array = table[field]
    result["null"] = array.null_count
    result["nonnull"] = count - array.null_count
    datatype = array.type
    lengths = None
    if pa.types.is_string(datatype) or pa.types.is_large_string(datatype):
        lengths = pc.utf8_length(array)
    elif pa.types.is_list(datatype) or pa.types.is_large_list(datatype) or pa.types.is_fixed_size_list(datatype):
        lengths = pc.list_value_length(array)
    if lengths is not None:
        result["empty_nonnull"] = pc.sum(pc.cast(pc.fill_null(pc.equal(lengths, 0), False), pa.int64())).as_py() or 0
    if field in MEASUREMENTS:
        if pa.types.is_floating(datatype) or pa.types.is_integer(datatype) or pa.types.is_decimal(datatype):
            finite = pc.is_finite(pc.cast(array, pa.float64()))
            result["nonfinite_numeric"] = pc.sum(pc.cast(pc.fill_null(pc.invert(finite), False), pa.int64())).as_py() or 0
        elif not pa.types.is_null(datatype):
            result["nonnumeric_measurement"] = result["nonnull"]
    return result


def score_subset(helpers, slots, fields):
    subset = [slot for slot in slots if slot["source"]["field"] in fields]
    answers = [{key: slot[key] for key in ("slot_id", "value", "unit", "source")}
               for slot in subset if slot["value"] is not None]
    scored = helpers.score_slots(subset, answers)
    answerable = sum(value["answerable"] for value in scored["family_scores"].values())
    matched = sum(value["matched"] for value in scored["family_scores"].values())
    return {"answerable_components": answerable, "matched_components": matched,
            "coverage": matched / answerable if answerable else None,
            "pass_80pct_zero_critical": (matched / answerable >= .8 and not scored["critical_errors"]) if answerable else None,
            "critical_errors": scored["critical_errors"]}


def run():
    if REPORT_PATH.exists():
        raise FileExistsError("Preserve existing report; no automatic rerun")
    plan = json.loads(PLAN_PATH.read_bytes())
    output = output_path(plan)
    frozen = json.loads((output / "PLAN-FROZEN.json").read_bytes())
    if pin(PLAN_PATH) != frozen["plan"]:
        raise ValueError("Plan differs from pre-read freeze marker")
    for expected in (plan["code"], plan["projection_helpers"], plan["inspection"], plan["catalog_current"]):
        if pin(ROOT / expected["path"]) != expected:
            raise ValueError("Frozen code or metadata changed before raw reads")
    started, cpu_started = time.perf_counter(), time.process_time()
    tracemalloc.start()
    save_new(output / "RUN-STARTED.json", {"started_at_utc": utcnow(), "role": "evaluation_only",
                                           "frozen_plan": frozen["plan"]})
    resources = {"original_file_bytes_rehashed": 0, "receipt_bytes_rehashed": 0,
                 "physical_parquet_rows_scanned": 0, "key_projection_row_group_rows": 0,
                 "field_projection_row_group_rows": 0, "all_matched_projected_arrow_bytes": 0,
                 "selected_arrow_bytes": 0, "unique_projected_compressed_column_bytes_estimate": 0,
                 "actual_storage_io_bytes": None, "process_peak_rss_bytes": None,
                 "process_peak_rss_reason": "Not measured; Python and Arrow allocation peaks are separate from process RSS"}
    completed, proofs, units = [], [], []
    stage = "environment"
    try:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        if pa.__version__ != "21.0.0":
            raise ValueError("Use the existing pyarrow 21.0.0 environment")
        helpers = load_prototype()
        sys.path.insert(0, str(ROOT / "src"))
        from asof.provenance import catalog_index, check_role
        from asof.serde import fingerprint
        catalog = catalog_index(json.loads(CATALOG_PATH.read_bytes()))
        inspection = read_pinned(INSPECTION, INSPECTION_SHA)
        expected_entries = {entry["source"]["source_id"]: entry for entry in inspection["files"]}
        fields = sum((plan["fields"][key] for key in ("identity", "context", "scientific_legacy_family")), [])
        states = {context["unit_id"]: {"context": context, "matched_rows": 0, "ids": Counter(),
                                      "selected": {}, "counts": {field: empty_counts() for field in fields}}
                  for context in plan["contexts"]}
        with (output / "file-events.jsonl").open("x", encoding="utf-8", newline="\n") as events:
            for entry in plan["files"]:
                source = entry["source"]
                stage = "verify:" + source["source_id"]
                if canonical(entry) != canonical(expected_entries[source["source_id"]]):
                    raise ValueError("Frozen source differs from pinned inspection")
                check_role(source["dataset_id"], source["role"], catalog)
                if (source["dataset_id"] != "ot_evidence" or source["release_id"] != "25.09"
                        or source["role"] != "agent_evidence" or source["parents"]
                        or source["computed_at"] is not None or not source["path"].startswith(PARTITION)):
                    raise ValueError("Ineligible original source lineage/scope")
                public_by = datetime.fromisoformat(source["availability"]["known_public_by"].replace("Z", "+00:00"))
                if (public_by > datetime.fromisoformat(plan["created_at_utc"])
                        or source["temporal_classification"] != "contemporary_only"
                        or source["availability"]["evidence_ref"] != source["receipt_sha256"]):
                    raise ValueError("Original availability incompatible with frozen contemporary scope")
                original = safe_raw_child(source["path"])
                receipt_path = safe_raw_child(source["receipt_path"])
                before = original.stat()
                original_pin = pin(original)
                receipt_bytes = receipt_path.read_bytes()
                receipt_pin = {"path": str(receipt_path), "bytes": len(receipt_bytes),
                               "sha256": hashlib.sha256(receipt_bytes).hexdigest()}
                resources["original_file_bytes_rehashed"] += original_pin["bytes"]
                resources["receipt_bytes_rehashed"] += receipt_pin["bytes"]
                if original_pin["sha256"] != source["sha256"] or original_pin["bytes"] != entry["bytes"]:
                    raise ValueError("Original source hash/size differs")
                receipt = json.loads(receipt_bytes)
                if (receipt_pin["sha256"] != source["receipt_sha256"] or receipt["status"] != "completed"
                        or receipt["sha256"] != source["sha256"] or receipt["bytes"] != entry["bytes"]
                        or receipt["release_id"] != "25.09" or receipt["dataset_id"] != "ot_evidence"
                        or safe_raw_child(receipt["relative_path"]) != original):
                    raise ValueError("Receipt does not bind the original")
                parquet = pq.ParquetFile(original)
                names = parquet.schema_arrow.names
                if (names != entry["columns"] or fingerprint(tuple(names)) != entry["schema_sha256"]
                        or parquet.metadata.num_rows != entry["rows"]):
                    raise ValueError("Original schema/row count differs from frozen inspection")
                resources["physical_parquet_rows_scanned"] += parquet.metadata.num_rows
                present = [field for field in fields if field in names]
                file_matches = {key: 0 for key in states}
                for group in range(parquet.num_row_groups):
                    stage = "scan:" + source["source_id"] + ":" + str(group)
                    metadata = parquet.metadata.row_group(group)
                    keys = parquet.read_row_group(group, columns=["id", "targetId", "diseaseId"])
                    resources["key_projection_row_group_rows"] += keys.num_rows
                    read_fields = {"id", "targetId", "diseaseId"}
                    match_indices = {}
                    for key, state in states.items():
                        context = state["context"]
                        mask = pc.and_(pc.equal(keys["targetId"], context["target_id"]),
                                       pc.equal(keys["diseaseId"], context["disease_id"]))
                        indices = pc.indices_nonzero(pc.fill_null(mask, False))
                        if len(indices):
                            match_indices[key] = indices
                    if match_indices:
                        projected = parquet.read_row_group(group, columns=present)
                        read_fields.update(present)
                        resources["field_projection_row_group_rows"] += projected.num_rows
                        for key, indices in match_indices.items():
                            state = states[key]
                            matched = projected.take(indices)  # Exact Arrow row selection before any Python values.
                            state["matched_rows"] += matched.num_rows
                            file_matches[key] += matched.num_rows
                            resources["all_matched_projected_arrow_bytes"] += matched.nbytes
                            if pc.any(pc.not_equal(matched["datasourceId"], "gwas_credible_sets")).as_py():
                                raise ValueError("Matched record contradicts fixed source partition")
                            for field in fields:
                                add_counts(state["counts"][field], field_counts(matched, field, pa, pc))
                            identities = matched["id"].to_pylist()
                            original_rows = indices.to_pylist()
                            for offset, (identifier, row) in enumerate(zip(identities, original_rows)):
                                if not isinstance(identifier, str) or not identifier:
                                    raise ValueError("Unsortable original record ID; no repair/substitution")
                                state["ids"][identifier] += 1
                                selected = state["selected"]
                                if identifier in selected or (len(selected) == 3 and identifier > max(selected)):
                                    continue
                                one_row = matched.slice(offset, 1)
                                record = one_row.to_pylist()[0]
                                canonical(record)  # Reject non-JSON/nonfinite selected values rather than repair.
                                locator = {"source_id": source["source_id"], "row_group": group, "row": row}
                                selected[identifier] = {"record": record, "locator": locator,
                                                        "logical_arrow_bytes": one_row.nbytes}
                                if len(selected) > 3:
                                    del selected[max(selected)]
                    resources["unique_projected_compressed_column_bytes_estimate"] += sum(
                        metadata.column(index).total_compressed_size for index in range(metadata.num_columns)
                        if metadata.column(index).path_in_schema.split(".")[0] in read_fields)
                after = original.stat()
                if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                    raise ValueError("Original changed during bounded read")
                proofs.append({"source": source, "original": original_pin, "receipt": receipt_pin,
                               "columns_fingerprint": entry["schema_sha256"],
                               "observed_arrow_schema_sha256": hashlib.sha256(parquet.schema_arrow.serialize().to_pybytes()).hexdigest(),
                               "rows": parquet.metadata.num_rows, "matches": file_matches})
                completed.append(source["source_id"])
                events.write(canonical({"source_id": source["source_id"], "status": "verified_and_scanned",
                                        "matches": file_matches, "finished_at_utc": utcnow()}) + "\n")
                events.flush()
        if (len(completed) != 100 or resources["original_file_bytes_rehashed"] != 180049263
                or resources["physical_parquet_rows_scanned"] != 1753850):
            raise ValueError("Incomplete declared collection; zero-match conclusions withheld")
        stage = "derive_selected_projection"
        for context in plan["contexts"]:
            state = states[context["unit_id"]]
            selected = [state["selected"][identifier] for identifier in sorted(state["selected"])]
            slots = [slot for selected_row in selected
                     for slot in helpers.make_slots(selected_row["record"], selected_row["locator"])]
            answers = [{key: slot[key] for key in ("slot_id", "value", "unit", "source")}
                       for slot in slots if slot["value"] is not None]
            measurements = score_subset(helpers, slots, MEASUREMENTS)
            if any(state["counts"][field]["nonfinite_numeric"] or state["counts"][field]["nonnumeric_measurement"]
                   for field in MEASUREMENTS):
                raise ValueError("Invalid populated measurement type/value; retain diagnostics and stop")
            for field, counts in state["counts"].items():
                if counts["schema_absent"] + counts["null"] + counts["nonnull"] != state["matched_rows"]:
                    raise ValueError("Field-count denominator mismatch: " + field)
            resources["selected_arrow_bytes"] += sum(row["logical_arrow_bytes"] for row in selected)
            missing = state["matched_rows"] == 0
            unit = {**context, "role": "evaluation_only", "action": None, "modality": None, "tissue": None,
                    "collection_status": "complete_100_file_exact_pair_partition_scan",
                    "matched_physical_rows": state["matched_rows"], "distinct_record_ids": len(state["ids"]),
                    "duplicate_record_id_occurrences": sum(value - 1 for value in state["ids"].values()),
                    "selected_record_ids": [row["record"]["id"] for row in selected],
                    "selected_records": selected, "all_matched_field_counts": state["counts"],
                    "selected_slots": slots,
                    "baseline": {"method": "exact_raw_field_projection.v1", "answers": answers,
                                 "scores": helpers.score_slots(slots, answers),
                                 "measurement_component_scores": measurements,
                                 "subgroup_scores": {name: score_subset(helpers, slots, fields)
                                                     for name, fields in plan["scientific_subgroups"].items()},
                                 "status": "insufficient_input_in_selected_collection" if missing else "completed_projection",
                                 "missingness_check": helpers.missing_input_result("insufficient_input_in_selected_collection", answers) if missing else None},
                    "biological_absence": "not_established", "independent_study_count": None,
                    "exposure": "existing_development_unit_additive_source_family_no_freshness_claim"}
            units.append(unit)
        resources.update(elapsed_seconds=time.perf_counter() - started,
                         process_cpu_seconds=time.process_time() - cpu_started,
                         python_traced_peak_bytes=tracemalloc.get_traced_memory()[1],
                         arrow_allocator_peak_bytes=pa.default_memory_pool().max_memory(),
                         selected_original_rows=sum(len(unit["selected_records"]) for unit in units),
                         measurement_scope="Run start through collection/projection, before output serialization and sealing")
        manifest = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False,
                    "adjudicated_gold": False, "computed_at_utc": utcnow(),
                    "parents": [frozen["plan"], plan["inspection"], plan["catalog_current"],
                                plan["projection_helpers"], plan["code"]],
                    "descendant_role": "evaluation_only_for_all_descendants", "source_proofs": proofs,
                    "units": units, "resources": resources,
                    "scientific_validation": "Not established; native source reporting only",
                    "redistribution": "Private local derivation; this scan grants no source redistribution rights"}
        manifest_pin = save_new(output / "gwas-availability.json", manifest)
        report_units = []
        for unit in units:
            report_units.append({key: unit[key] for key in (
                "unit_id", "symbol", "target_id", "disease_id", "prior_scope", "collection_status",
                "matched_physical_rows", "distinct_record_ids", "duplicate_record_id_occurrences", "selected_record_ids")}
                | {"selected_records": len(unit["selected_records"]),
                   "all_matched_field_counts": unit["all_matched_field_counts"],
                   "family_scores": unit["baseline"]["scores"]["family_scores"],
                   "critical_errors": unit["baseline"]["scores"]["critical_errors"],
                   "measurement_component_scores": unit["baseline"]["measurement_component_scores"],
                   "subgroup_scores": unit["baseline"]["subgroup_scores"],
                   "status": unit["baseline"]["status"], "missingness_check": unit["baseline"]["missingness_check"]})
        substantive = sum(unit["baseline"]["measurement_component_scores"]["answerable_components"] for unit in units)
        matched_components = sum(unit["baseline"]["measurement_component_scores"]["matched_components"] for unit in units)
        component_errors = [error for unit in units
                            for error in unit["baseline"]["measurement_component_scores"]["critical_errors"]]
        report = {"schema_version": 1, "status": "COMPLETE_ADDITIVE_GWAS_FIELD_FEASIBILITY",
                  "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
                  "frozen_plan": frozen["plan"], "manifest": manifest_pin,
                  "collection": {"scheduled_files": 100, "completed_files": len(completed),
                                 "scope": "Only this fixed GWAS partition and the same three exact development pairs"},
                  "units": report_units, "resources": resources,
                  "reported_measurement_components": substantive,
                  "measurement_primary": {"coverage": matched_components / substantive if substantive else None,
                                          "pass": (matched_components / substantive >= .8 and not component_errors) if substantive else None,
                                          "interpretation": "Constructive exact-copy ceiling; not model performance or independent clinical/biological validation" if substantive else "Not estimable: zero answerable reported measurement components"},
                  "baseline_ceiling": "All eligible populated fields are copied exactly; no incremental LLM benefit is tested",
                  "unit_denominator": "Three existing development units; rows, fields, IDs, and components do not add biomedical cases or independent studies",
                  "v1_preserved": "Earlier six-literature-record null finding and literature-bounded FCGRT zero remain unchanged",
                  "catalog": {"historical_inspection_sha256": plan["catalog_historical_sha256_reported_by_inspection"],
                              "current_enforced": plan["catalog_current"], "byte_equality_claimed": False},
                  "scientific_validation": "not_established", "model_calls": 0, "new_downloads": 0,
                  "provider_spending_usd": 0, "entire_project_complete": False}
        report_pin = save_new(REPORT_PATH, report)
        save_new(output / "terminal.json", {"status": report["status"], "report": report_pin,
                                             "manifest": manifest_pin, "finished_at_utc": utcnow()})
        print(canonical({"report": report_pin, "manifest": manifest_pin, "frozen_plan": frozen["plan"],
                         "units": [{key: unit[key] for key in ("unit_id", "matched_physical_rows", "selected_record_ids",
                                                              "measurement_component_scores")} for unit in report_units],
                         "resources": resources}))
    except BaseException as error:
        resources.update(elapsed_seconds=time.perf_counter() - started,
                         process_cpu_seconds=time.process_time() - cpu_started,
                         python_traced_peak_bytes=tracemalloc.get_traced_memory()[1])
        failure = {"schema_version": 1, "status": "FAILED_STOPPED_NO_RETRY", "role": "evaluation_only",
                   "stage": stage, "error_type": type(error).__name__, "message": str(error),
                   "frozen_plan": frozen["plan"], "completed_source_ids": completed,
                   "scheduled_files": 100, "completed_files": len(completed), "resources": resources,
                   "partial_source_proofs": proofs, "zero_match_claim_authorized": False,
                   "partial_field_counts": {key: {"matched_rows": value["matched_rows"], "counts": value["counts"]}
                                            for key, value in locals().get("states", {}).items()},
                   "model_calls": 0, "new_downloads": 0, "failed_at_utc": utcnow()}
        save_new(output / "failure.json", failure)
        if not REPORT_PATH.exists():
            save_new(REPORT_PATH, failure)
        raise
    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--freeze", action="store_true")
    operation.add_argument("--run", action="store_true")
    arguments = parser.parse_args()
    freeze() if arguments.freeze else run()
