"""Bounded evaluator-only P02 source feasibility; no model or new acquisition."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW_ROOT = Path("E:/projects_data/drug_target_agents_data")
PLAN = ROOT / "planning/review-assets/recovery-step8-20261026/bounded-source-plan-v1.json"
PLAN_SHA = "bf23203020e88c591512c64b81bfedf733b641bbf6b61f7c8e10a3f89992cdc2"
CACHE = ROOT / "data/cache/recovery-step8-source-feasibility-20261026"
CHECKS_SHA = "fba3e94435448be75205969dc61793ed74771b166ae6ff888e3869eced37c37e"
PAIRS_SHA = "0ce5672e3e8ba895203c1a43d7ada86d7ed19ef482cb20b64cdf9a610c01385c"
IDENTITY_FIELDS = ("id", "targetId", "diseaseId", "datasourceId", "datatypeId", "literature", "pmcIds")
CONTEXT_FIELDS = ("publicationDate", "publicationYear", "evidenceDate")
SCIENTIFIC_FIELDS = (
    "studyId", "ancestry", "ancestryId", "cellType", "biosamplesFromSource",
    "alleleOrigins", "allelicRequirements", "biologicalModelId", "diseaseCellLines", "sex",
    "studyLocusId", "studyCases", "studyCasesWithQualifyingVariants", "studySampleSize",
    "targetInModelEnsemblId", "targetInModelMgiId", "targetModulation",
    "variantFromSourceId", "variantFunctionalConsequenceId", "variantHgvsId", "variantId", "variantRsId",
    "variantEffect", "directionOnTrait", "beta", "betaConfidenceIntervalLower", "betaConfidenceIntervalUpper",
    "oddsRatio", "oddsRatioConfidenceIntervalLower", "oddsRatioConfidenceIntervalUpper",
    "pValueExponent", "pValueMantissa", "log2FoldChangePercentileRank", "log2FoldChangeValue",
)
FAMILIES = {"identity": IDENTITY_FIELDS, "context": CONTEXT_FIELDS, "scientific": SCIENTIFIC_FIELDS}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def pin(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)}


def bound(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Pinned input differs: " + str(path))
    return json.loads(raw)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    return pin(path)


def make_slots(record, locator):
    if not isinstance(record.get("id"), str) or not record["id"]:
        raise ValueError("Source record ID required")
    slots = []
    for family, fields in FAMILIES.items():
        for field in fields:
            value = record.get(field)
            slots.append({"slot_id": record["id"] + ":" + field, "family": family,
                          "value": value, "unit": None, "source": dict(locator, field=field),
                          "transform": "exact_raw_typed_field.v1", "clinical_truth": False,
                          "unknown_reason": "field_not_in_schema" if field not in record else
                          ("null_source_value" if value is None else None)})
    return slots


def score_slots(slots, answers):
    expected = {slot["slot_id"]: slot for slot in slots}
    if len(expected) != len(slots) or not isinstance(answers, list):
        raise ValueError("Invalid expected slots or answer sequence")
    counts = {family: {"answerable": sum(s["family"] == family and s["value"] is not None for s in slots),
                       "matched": 0} for family in FAMILIES}
    errors, seen = [], set()
    for answer in answers:
        if not isinstance(answer, dict) or set(answer) != {"slot_id", "value", "unit", "source"}:
            raise ValueError("Invalid answer fields")
        identifier = answer["slot_id"]
        if not isinstance(identifier, str):
            raise ValueError("Invalid answer slot identity")
        if identifier in seen:
            errors.append({"slot_id": identifier, "reason": "duplicate_answer"})
            continue
        seen.add(identifier)
        slot = expected.get(identifier)
        if slot is None:
            errors.append({"slot_id": identifier, "reason": "unknown_slot"})
        elif slot["value"] is None:
            if (answer["value"] is not None or canonical(answer["unit"]) != canonical(slot["unit"])
                    or canonical(answer["source"]) != canonical(slot["source"])):
                errors.append({"slot_id": identifier, "reason": "unsupported_unknown_assertion"})
        elif any(canonical(answer[key]) != canonical(slot[key]) for key in ("value", "unit", "source")):
            errors.append({"slot_id": identifier, "reason": "value_unit_or_source_mismatch"})
        else:
            counts[slot["family"]]["matched"] += 1
    for value in counts.values():
        value["coverage"] = value["matched"] / value["answerable"] if value["answerable"] else None
    return {"family_scores": counts, "critical_errors": errors}


def missing_input_result(status, answers):
    return status == "insufficient_input_in_selected_collection" and answers == []


def collect(output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if pa.__version__ != "21.0.0":
        raise ValueError("P02 requires the already qualified Arrow 21.0.0 environment")
    plan = bound(PLAN, PLAN_SHA)
    checks = bound(CACHE / "file-checks.json", CHECKS_SHA)
    pairs = bound(CACHE / "candidate-pair-metadata.json", PAIRS_SHA)
    if plan["role"] != "evaluation_only" or len(plan["contexts"]) != 2:
        raise ValueError("Fixed evaluator-only selection changed")
    inventory = {item["source"]["source_id"]: item for item in checks}
    # Use the existing role policy, not a relabeled source cache.
    sys.path.insert(0, str(ROOT / "src"))
    from asof.provenance import catalog_index, check_role
    catalog_path = ROOT / "data/catalog/sources.json"
    catalog = catalog_index(json.loads(catalog_path.read_bytes()))
    now = datetime.now(timezone.utc)
    units, raw_proofs, rows, selected_bytes, compressed_columns, projected_rows = [], [], [], 0, 0, 0
    for context in plan["contexts"]:
        selected, slots = [], []
        for locator in context["selected_record_locators"]:
            entry = inventory[locator["source_id"]]
            source = entry["source"]
            check_role(source["dataset_id"], source["role"], catalog)
            original = (RAW_ROOT / source["path"]).resolve()
            receipt_path = (RAW_ROOT / source["receipt_path"]).resolve()
            if not original.is_relative_to(RAW_ROOT.resolve()) or not receipt_path.is_relative_to(RAW_ROOT.resolve()):
                raise ValueError("Original/receipt escaped approved root")
            if source["parents"] or source["role"] != "agent_evidence" or source["release_id"] != "25.09":
                raise ValueError("Ineligible original lineage")
            source_pin, receipt_pin = pin(original), pin(receipt_path)
            if source_pin["sha256"] != locator["source_sha256"] or source_pin["sha256"] != source["sha256"] or source_pin["bytes"] != entry["bytes"]:
                raise ValueError("Original hash/size mismatch")
            receipt = bound(receipt_path, source["receipt_sha256"])
            if (receipt["status"] != "completed" or receipt["sha256"] != source_pin["sha256"]
                    or receipt["bytes"] != source_pin["bytes"] or receipt["release_id"] != "25.09"
                    or receipt["dataset_id"] != source["dataset_id"]
                    or (RAW_ROOT / receipt["relative_path"]).resolve() != original):
                raise ValueError("Receipt does not bind original")
            public_by = datetime.fromisoformat(source["availability"]["known_public_by"].replace("Z", "+00:00"))
            if public_by > now or source["temporal_classification"] != "contemporary_only":
                raise ValueError("Availability incompatible with contemporary cutoff")
            parquet = pq.ParquetFile(original)
            fields = [field for group in FAMILIES.values() for field in group if field in parquet.schema_arrow.names]
            group, row = locator["row_group"], locator["row"]
            if row < 0 or row >= parquet.metadata.row_group(group).num_rows:
                raise ValueError("Invalid original row locator")
            table = parquet.read_row_group(group, columns=fields).slice(row, 1)
            record = table.to_pylist()[0]  # Arrow selection precedes Python conversion.
            for key, value in locator["record"].items():
                if canonical(record.get(key)) != canonical(value):
                    raise ValueError("Original row changed from fixed metadata")
            if record["targetId"] != context["target_id"] or record["diseaseId"] != context["indication_id"] or record["datasourceId"] != "europepmc" or record["datatypeId"] != "literature":
                raise ValueError("Source identity/scope differs")
            for key in ("publicationDate", "evidenceDate"):
                if record.get(key) and record[key][:10] > now.date().isoformat():
                    raise ValueError("Explicitly future-dated source metadata")
            row_locator = {"source_id": source["source_id"], "row_group": group, "row": row}
            new_slots = make_slots(record, row_locator)
            slots.extend(new_slots)
            selected.append({"original": source_pin, "receipt": receipt_pin, "source": source,
                             "locator": row_locator, "record": record,
                             "cluster_ids": list(record["literature"])})
            rows.append(row_locator)
            raw_proofs.append({"original": source_pin, "receipt": receipt_pin})
            selected_bytes += table.nbytes
            meta = parquet.metadata.row_group(group)
            projected_rows += meta.num_rows
            compressed_columns += sum(meta.column(i).total_compressed_size for i in range(meta.num_columns)
                                      if meta.column(i).path_in_schema.split(".")[0] in fields)
        answers = [{key: slot[key] for key in ("slot_id", "value", "unit", "source")}
                   for slot in slots if slot["value"] is not None]
        units.append({"unit_id": context["symbol"].lower() + "-" + context["indication_id"].lower(),
                      "target_id": context["target_id"], "disease_id": context["indication_id"],
                      "action": None, "modality": None, "tissue": None,
                      "exposure": "fixed_exposed_development_context_not_fresh",
                      "collection_status": "fixed_three_record_subset_not_whole_release",
                      "original_records": selected, "slots": slots,
                      "baseline": {"method": "exact_field_projection.v1", "answers": answers,
                                   "scores": score_slots(slots, answers)}})
    zero = sorted((pair for pair in pairs if pair["physical_matches"] == 0),
                  key=lambda pair: (pair["symbol"], pair["disease_id"]))[0]
    units.append({"unit_id": zero["symbol"].lower() + "-" + zero["disease_id"].lower(),
                  "target_id": zero["target_id"], "disease_id": zero["disease_id"],
                  "action": None, "modality": None, "tissue": None,
                  "exposure": "development_missing_input_unit_no_freshness_claim",
                  "collection_status": "zero_matches_in_retained_selected_metadata_scan",
                  "current_full_collection_rescanned": False, "biological_absence": "not_established",
                  "slots": [], "original_records": [],
                  "baseline": {"method": "explicit_collection_bounded_missingness.v1", "answers": [],
                               "status": "insufficient_input_in_selected_collection",
                               "missingness_check": missing_input_result("insufficient_input_in_selected_collection", []),
                               "scores": score_slots([], [])}})
    manifest = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False,
                "adjudicated_gold": False, "computed_at": now.isoformat(), "cutoff_utc": now.isoformat(),
                "selection": "Original pre-response fixed two-context selector plus first zero-match pair in symbol/disease-ID order",
                "parents": [pin(PLAN), pin(CACHE / "file-checks.json"), pin(CACHE / "candidate-pair-metadata.json"), pin(catalog_path)],
                "raw_proofs": raw_proofs, "units": units, "code": pin(Path(__file__)),
                "scientific_validation": "not_established", "downstream_role": "evaluation_only_for_all_descendants",
                "rights": "Local evaluator prototype; source-byte redistribution not authorized by this result"}
    proof = save(output / "prototype.json", manifest)
    return units, proof, {"original_file_bytes_rehashed": sum(p["original"]["bytes"] for p in raw_proofs),
                         "row_group_rows_covered_by_column_reads": projected_rows,
                         "original_rows_selected": len(rows), "selected_arrow_bytes": selected_bytes,
                         "projected_column_compressed_bytes_estimate": compressed_columns,
                         "arrow_peak_allocated_bytes": pa.default_memory_pool().max_memory(),
                         "process_peak_memory_bytes": None, "process_peak_memory_reason": "Not measured; Python/Arrow allocator peaks are separate and not process RSS"}


def main():
    report_path = HERE / "PROTOTYPE-REPORT-v1.json"
    if report_path.exists():
        raise FileExistsError("Preserve prior report; a new protocol/output version is required")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "data/benchmark/gold_evidence" / ("preprint-p02-" + stamp)
    output.mkdir()
    save(output / "attempt.json", {"started_at_utc": stamp, "role": "evaluation_only", "model_calls": 0})
    started = time.perf_counter()
    tracemalloc.start()
    try:
        units, proof, resources = collect(output)
        resources.update(elapsed_seconds=time.perf_counter() - started,
                         python_traced_peak_bytes=tracemalloc.get_traced_memory()[1])
        scores = [{"unit_id": unit["unit_id"], "records": len(unit["original_records"]),
                   "collection_status": unit["collection_status"], **unit["baseline"]["scores"]} for unit in units]
        report = {"schema_version": 1, "status": "COMPLETE_BOUNDED_FEASIBILITY_SCIENTIFIC_PRIMARY_NOT_ESTIMABLE",
                  "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
                  "manifest": proof, "unit_scores": scores, "resources": resources,
                  "source_policy": "Original receipt-bound rows only; no response payload, old AI assessment, candidate, narrative or clinical field is projected",
                  "scientific_primary": {"answerable_slots": sum(s["family_scores"]["scientific"]["answerable"] for s in scores),
                                         "coverage": None, "pass": None, "reason": "No populated typed scientific fields in fixed source subset; zero denominator never passes"},
                  "baseline_ceiling": "Identity/reporting-context projection only; not LLM or scientific-interpretation superiority",
                  "model_calls": 0, "provider_spending_usd": 0, "new_downloads": 0,
                  "next_scope": "P03 must not turn context-only projection into scientific primary performance. Use bounded eligibility/composition/missingness measurements or qualify a separately declared richer source task before model evaluation.",
                  "entire_project_complete": False}
        if report["scientific_primary"]["answerable_slots"] != 0:
            raise ValueError("Unexpected scientific values: review scope rather than silently change the protocol")
        saved = save(report_path, report)
        save(output / "terminal.json", {"status": report["status"], "report": saved})
        print(canonical({"report": saved, "manifest": proof, "scores": scores, "resources": resources}))
    except BaseException as error:
        save(output / "failure.json", {"status": "failed", "error_type": type(error).__name__,
                                      "message": str(error), "model_calls": 0,
                                      "elapsed_seconds": time.perf_counter() - started})
        raise
    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    main()
