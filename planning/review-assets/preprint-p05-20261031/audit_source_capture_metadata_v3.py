"""Supplement P05 full source audit with direct selected-source metadata replay.

Only originals, frozen neutral plans, and quarantined comparison targets are read.
Reports contain counts, hashes and check names, never native scientific values.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_p05_audit", HERE / "audit_source_registry_v3.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def full_guard(row, cutoff):
    reasons, statuses = a.dates(row, cutoff)
    fields, publication = {}, []
    for field in a.GUARDS:
        native = row.get(field)
        if field not in row:
            fields[field] = {"status": "schema_absent", "native": None, "upper_bound_utc": None}
        elif field == "releaseVersion":
            fields[field] = {"status": "native_annotation_metadata_only", "native": a.normalized(native), "upper_bound_utc": None}
        elif statuses[field] == "invalid_explicit_date":
            fields[field] = {"status": "invalid_explicit_date", "native": a.normalized(native), "upper_bound_utc": None}
        else:
            bounds = a.interval(native, field)
            low, high = bounds if bounds is not None else (None, None)
            spelling = str(native) if field == "publicationYear" and type(native) is int else native
            precision = "unknown" if low is None else "year" if re.fullmatch(r"\d{4}", spelling) else "month" if re.fullmatch(r"\d{4}-\d{2}", spelling) else "day" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", spelling) else "timestamp"
            fields[field] = {"status": statuses[field], "native": a.normalized(native), "lower_bound_utc": low.isoformat() if low else None,
                             "upper_bound_utc": high.isoformat() if high else None, "precision": precision}
            if low is not None and field in ("publicationDate", "publicationYear"):
                publication.append(bounds)
    event = {"status": "unknown", "lower_bound_utc": None, "upper_bound_utc": None}
    if publication:
        low, high = max(v[0] for v in publication), min(v[1] for v in publication)
        if low > high:
            event["status"] = "publication_date_conflict"
        else:
            event = {"status": "explicit_future" if low > cutoff else "date_precision_unverified" if high > cutoff else "within_cutoff",
                     "lower_bound_utc": low.isoformat(), "upper_bound_utc": high.isoformat(), "resolution": "intersection_of_supplied_publication_precision_intervals"}
    return {"cutoff_utc": cutoff.isoformat(), "fields": fields, "publication_event": event,
            "exclusion_reasons": reasons, "purpose": "eligibility_and_provenance_only_not_primary_facts_or_rank"}


def main():
    import pyarrow.parquet as pq
    started = time.monotonic()
    report_path = HERE / "REGISTRY-AUDIT-v3.json"
    prior = a.document(report_path)
    a.require("full_source_audit_completed_first", prior["status"] == "PASS_SOURCE_ONLY_TECHNICAL_AUDIT")
    a.terminal_gate()
    ready = a.document(HERE / "REGISTRY-READY-v3.json")
    plan = a.document(HERE / "REGISTRY-PLAN-DRAFT-v3.json")
    cutoff = datetime.fromisoformat(ready["row_guard_cutoff_utc"])
    docs = {k: a.document(v["path"]) for k, v in plan["neutral_inputs"].items()}
    originals = a.inventory(docs["frame"], docs["acquisition"])
    records = {r["relative_path"]: r for r in originals}
    cases = a.document(a.RUN / "selected-case-plan.json")["cases"]
    coverage = a.document(a.RUN / "coverage.json")
    captures = {}
    row_groups = defaultdict(set)
    header_counts, normalization_counts = Counter(), Counter()
    policy_good = True
    for case in cases:
        cid = case["case_id"]
        captures[cid] = [json.loads(line) for line in (a.RUN / "selected-originals" / (cid + ".jsonl")).read_bytes().splitlines()]
        for v in captures[cid]:
            if v["record_type"] == "case_header":
                header_counts[cid] += 1
            elif v["record_type"] == "normalization_originals":
                normalization_counts[cid] += 1
            elif v["record_type"] in ("gwas_credible_sets_original", "credible_set_original"):
                loc = v["locator"]
                row_groups[(loc["source_relative_path"], loc["row_group_0based"])].add(loc["row_in_group_0based"])
            else:
                policy_good = False
    a.require("exact_one_header_and_normalization_per_case", policy_good and all(header_counts[c["case_id"]] == normalization_counts[c["case_id"]] == 1 for c in cases))
    paths = {Path(records[path]["path"]) for path, group in row_groups}
    paths.update(Path(r["path"]) for r in originals if r["family"] in ("target", "disease", "hgnc"))
    source_values = {}
    with a.stable_files(paths, deadline=time.monotonic() + 300):
        indexes = a.load_mappings(originals)
        for (path, group), positions in row_groups.items():
            r = records[path]
            source = pq.ParquetFile(r["path"])
            b = source.read_row_group(group, columns=a.columns(r), use_threads=False)
            a.observe(b)
            for position in positions:
                source_values[(path, group, position)] = b.slice(position, 1).to_pylist()[0]
        capture_eligibility_good = native_lists_good = True
        selected_rows = 0
        for case in cases:
            cid = case["case_id"]
            natives = {f: defaultdict(dict) for f in ("gwas_credible_sets", "credible_set")}
            for v in captures[cid]:
                if v["record_type"] not in ("gwas_credible_sets_original", "credible_set_original"):
                    continue
                selected_rows += 1
                family = v["record_type"].removesuffix("_original")
                loc = v["locator"]
                native = source_values[(loc["source_relative_path"], loc["row_group_0based"], loc["row_in_group_0based"])]
                for field in ("studyId", "variantId"):
                    natives[family][field][a.wire(native.get(field))] = a.normalized(native.get(field))
                if family == "credible_set":
                    capture_eligibility_good &= v["eligibility"] == "not_used_for_selection"
                else:
                    reasons, symbol, exposure, _ = a.eligible(native, indexes, cutoff)
                    expected = {"eligible": not reasons, "exclusion_reasons": reasons, "date_guard": full_guard(native, cutoff),
                                "approved_symbol": symbol, "exposure_status": exposure}
                    capture_eligibility_good &= v["eligibility"] == expected
            for field in ("studyId", "variantId"):
                context = coverage["selected"][cid]["native_identity_context"][field]
                for family, label in (("gwas_credible_sets", "gwas_native_values"), ("credible_set", "credible_native_values")):
                    native_lists_good &= {a.wire(x) for x in context[label]} == set(natives[family][field]) and len(context[label]) == len(natives[family][field])
                native_lists_good &= context["semantic_variant_inference"] == "not_performed"
        a.require("every_selected_capture_eligibility_and_native_date_guard_replayed", capture_eligibility_good, original_rows=selected_rows)
        a.require("complete_native_identity_lists_including_missing_values", native_lists_good)
    db = sqlite3.connect("file:" + (a.RUN / "candidate-registry.sqlite").as_posix() + "?mode=ro&immutable=1", uri=True)
    known_units, unique_units = db.execute("SELECT COUNT(unit_hash),COUNT(DISTINCT unit_hash) FROM gwas_rows").fetchone()
    known_ids, unique_ids = db.execute("SELECT COUNT(evidence_id),COUNT(DISTINCT evidence_id) FROM gwas_rows WHERE evidence_id IS NOT NULL AND evidence_id!=''").fetchone()
    total = db.execute("SELECT COUNT(*) FROM gwas_rows").fetchone()[0]
    duplicates = {"missing_or_invalid_unit_identity_rows": total - known_units, "known_unit_duplicate_extra_rows": known_units - unique_units,
                  "missing_or_empty_evidence_id_rows": total - known_ids, "known_evidence_id_duplicate_extra_rows": known_ids - unique_ids}
    db.close()
    a.REPORT["duplicate_and_missing_identity_counts"] = duplicates
    a.REPORT["prior_full_audit_sha256"] = a.sha(report_path.read_bytes())
    a.REPORT["full_audit_script_sha256"] = a.sha((HERE / "audit_source_registry_v3.py").read_bytes())
    a.REPORT["supplement_script_sha256"] = a.sha(Path(__file__).read_bytes())
    a.REPORT["cost"]["wall_seconds"] = time.monotonic() - started
    a.REPORT["status"] = "PASS_SELECTED_CAPTURE_METADATA_SUPPLEMENT" if not a.REPORT["issues"] else "FAIL_SELECTED_CAPTURE_METADATA_SUPPLEMENT"
    output = HERE / "REGISTRY-AUDIT-CAPTURE-METADATA-v3.json"
    if output.exists():
        raise RuntimeError("Preserve existing supplement")
    output.write_bytes(a.wire(a.REPORT) + b"\n")
    print(json.dumps({"status": a.REPORT["status"], "checks": len(a.REPORT["checks"]), "issues": a.REPORT["issues"], "duplicates": duplicates,
                      "report_sha256": a.sha(output.read_bytes()), "cost": a.REPORT["cost"]}))
    return 0 if not a.REPORT["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
