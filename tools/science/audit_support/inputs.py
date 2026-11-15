"""Selected source-audit helpers; see PROVENANCE.md for scope and origin."""
from __future__ import annotations
from collections import Counter, defaultdict
from . import registry as a
ROOT, RAW = a.ROOT, a.RAW
TASKS = ROOT / "data/derived/preprint-p05-neutral-tasks-20261101T075541Z"
REPORT = a.REPORT


NEUTRAL_SEAL_SHA = "5bf827df9921a01712d9739d7d04f59e8b0aa3554a9ebc9eaf87d6e240aadace"


CUTOFF = "2026-11-01T07:16:26.101448+00:00"


GWAS = ("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")


IDENTITY = ("studyLocusId", "studyId", "variantId")


MEASURE = ("beta", "standardError", "pValueMantissa", "pValueExponent")


def same(left, right):
    return a.wire(left) == a.wire(right)


def projected(r):
    required = a.BASE["gwas_credible_sets"] if r["family"] == "gwas_credible_sets" else IDENTITY + MEASURE + ("chromosome", "position", "sampleSize")
    automatic = a.GUARDS + ("publicationDate", "evidenceDate", "annotationDate", "publicationYear", "targetId", "target_id", "diseaseId", "indication_id")
    return list(required) + [k for k in dict.fromkeys(automatic) if k in r["fields"] and k not in required]


def source_selected(records, cases, indexes, cutoff):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    selected = {c["case_id"]: {"gwas_credible_sets": [], "credible_set": []} for c in cases}
    excluded = {c["case_id"]: [] for c in cases}
    by_locus = defaultdict(list)
    for c in cases:
        by_locus[c["studyLocusId"]].append(c)
    locus_set = pa.array(list(by_locus))
    scanned, states = Counter(), Counter()
    for r in records:
        if r["family"] not in ("gwas_credible_sets", "credible_set"):
            continue
        f = r["family"]
        p = pq.ParquetFile(r["path"])
        a.require("schema_footer_" + r["source_id"], p.schema_arrow.names == r["fields"] and p.metadata.num_rows == r["rows"])
        physical = 0
        for group in range(p.num_row_groups):
            local = 0
            for batch in p.iter_batches(batch_size=8192, row_groups=[group], columns=projected(r), use_threads=False):
                a.observe(batch)
                scanned[f + "_rows"] += batch.num_rows
                mask = pc.is_in(batch.column("studyLocusId"), value_set=locus_set)
                indices = pc.indices_nonzero(pc.fill_null(mask, False)).to_pylist()
                for i, v in zip(indices, batch.take(pa.array(indices, type=pa.int64())).to_pylist()):
                    for c in by_locus[v["studyLocusId"]]:
                        if f == "gwas_credible_sets" and (v.get("targetId"), v.get("diseaseId")) != (c["targetId"], c["diseaseId"]):
                            continue
                        if f == "gwas_credible_sets":
                            reasons, _, _, date_states = a.eligible(v, indexes, cutoff)
                        else:
                            reasons, date_states = a.dates(v, cutoff)
                        states.update(f + ":" + k + ":" + s for k, s in date_states.items())
                        if "annotationDate" in v:
                            try:
                                bounds = a.interval(v["annotationDate"], "annotationDate")
                                status = "unknown" if bounds is None else "explicit_future" if bounds[0] > cutoff else "date_precision_unverified" if bounds[1] > cutoff else "within_cutoff"
                                if status not in ("unknown", "within_cutoff"):
                                    reasons.append("annotationDate_" + status)
                            except (ValueError, TypeError, OverflowError):
                                status = "invalid_explicit_date"
                                reasons.append("annotationDate_invalid_explicit_date")
                            states[f + ":annotationDate:" + status] += 1
                        loc = {"format": "parquet", "row_group": group, "row": local + i}
                        if reasons:
                            excluded[c["case_id"]].append({"source_id": r["source_id"], "family": f, "locator": loc, "exclusion_reasons": reasons})
                        else:
                            selected[c["case_id"]][f].append({"source_id": r["source_id"], "family": f, "locator": loc, "physical_row_0based": physical + local + i, "values": v})
                local += batch.num_rows
            a.require("physical_group_" + r["source_id"] + "_" + str(group), local == p.metadata.row_group(group).num_rows)
            physical += local
        scanned[f + "_files"] += 1
    REPORT["original_inventory_scan"] = dict(scanned)
    REPORT["selected_native_date_status_counts"] = dict(states)
    a.require("complete_selected_original_inventory_scan", scanned == Counter({"gwas_credible_sets_rows": 1753850, "gwas_credible_sets_files": 100, "credible_set_rows": 2862043, "credible_set_files": 25}))
    return selected, excluded


def expected_task(case, groups):
    records, fields, keys = [], [], {"gwas_credible_sets": [], "credible_set": []}
    for family in ("gwas_credible_sets", "credible_set"):
        for i, row in enumerate(groups[family]):
            key = ("gwas" if family == "gwas_credible_sets" else "credible") + "-" + str(i).zfill(4)
            keys[family].append(key)
            v = row["values"]
            identity = {k: v[k] for k in (("targetId", "diseaseId", "studyLocusId") if family == "gwas_credible_sets" else ("studyLocusId",))}
            identity.update({k: v[k] for k in ("id", "studyId", "variantId") if k in v and v[k] is not None and v[k] != ""})
            records.append({"record_key": key, "source_id": row["source_id"], "locator": row["locator"], "identity": identity})
            for name in GWAS if family == "gwas_credible_sets" else IDENTITY + MEASURE:
                measurement = name in MEASURE
                fields.append({"record_key": key, "field": name, "family": "reported_measurement" if measurement else "identity_linkage", "group": ("measurement:" if measurement else "identity:") + key, "unit_field": None, "empty_policy": "unknown"})
    return {"schema_version": 1, "task_id": "p05-" + case["case_id"] + "-native-locus-v1", "scope": {"target_id": case["targetId"], "indication_id": case["diseaseId"], "target_namespace_version": "unknown", "indication_namespace_version": "unknown", "action": None, "modality": None, "tissue": None}, "cutoff": CUTOFF, "profile": "contemporary_assessment", "primary_families": ["reported_measurement"], "records": records, "fields": fields, "joins": [{"join_id": "locus:" + key, "left_record": key, "left_field": "studyLocusId", "right_records": keys["credible_set"], "right_field": "studyLocusId", "cardinality": "one_to_many", "inventory_status": "complete"} for key in keys["gwas_credible_sets"]], "collection": {"status": "selected_records", "reason": "All eligible selected physical rows in the pinned original frame only; source-locus reporting, no biological absence claim."}}
