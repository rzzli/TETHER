"""Independent Q03 selection/metadata/locator check; no producer imports or backend.

Reads all 100 evidence files' four ID columns for the first-eligible proof, plus
seven selected row-group projections. Does not repeat full source payload hashes.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ROOT = HERE.parents[3]
STORE = Path(r"E:\projects_data\drug_target_agents_data")
OUT = HERE / "INDEPENDENT-FEASIBILITY-CHECK.json"
CHECKS = []


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(name, condition):
    CHECKS.append({"property": name, "pass": bool(condition)})
    if not condition:
        raise AssertionError(name)


def good(x):
    return x is not None and x != ""


def main():
    started = time.perf_counter()
    inv = load(DATA / "SOURCE-INVENTORY.json")
    policy = load(DATA / "SOURCE-SELECTION-POLICY.json")
    report = load(DATA / "SOURCE-FEASIBILITY.json")
    manifest = load(DATA / "SOURCE-FILE-MANIFEST.json")
    excerpts = load(DATA / "SOURCE-EXCERPT-MANIFEST.json")
    labels_manifest = load(DATA / "LABEL-SOURCE-MANIFEST.json")
    attempts = load(DATA / "SOURCE-AUDIT-ATTEMPTS.json")
    binding = load(DATA / "SOURCE-INPUT-BINDING.json")
    check("task digest", digest(policy["task_spec_path"]) == policy["task_spec_sha256"])
    check("inventory digest", digest(DATA / "SOURCE-INVENTORY.json") == policy["universe_inventory_sha256"])
    check("selection policy digest", digest(DATA / "SOURCE-SELECTION-POLICY.json") == binding["selection_policy_sha256"])
    check("binding consistent", binding == report["binding"])
    check("original semantics unchanged", binding["task_spec_sha256"] == policy["task_spec_sha256"])

    # Check actual footer totals and neutral receipt bytes; raw hashes are inherited.
    states = {}
    for entry in inv["state_metadata"]:
        check("pinned receipt state " + entry["batch_id"], digest(entry["path"]) == entry["sha256"])
        state = load(entry["path"])
        for r in state["results"]:
            states[r["receipt_id"]] = r
    catalog = load(inv["catalog_path"])
    check("original catalog digest", digest(inv["catalog_path"]) == inv["catalog_sha256"])
    queue = load(ROOT / "data/manifests/private/core-2026-10-10-queue.json")
    expected_ev = {r["relative_path"].replace("\\", "/") for r in queue["files"] if "/evidence/sourceId=gwas_credible_sets/" in r["relative_path"].replace("\\", "/")}
    expected_cs = {p.replace("\\", "/") for d in catalog["datasets"] if d["dataset_id"] == "ot_credible_set" for p in d["acquisition_snapshot"]["relative_paths"]}
    files = {r["relative_path"]: r for family in ["gwas_credible_sets_evidence", "credible_set", "target", "disease"] for r in inv["inventory"][family]["files"]}
    footer_totals = {}
    footer_groups = {}
    for family in ["gwas_credible_sets_evidence", "credible_set", "target", "disease"]:
        total = groups = 0
        for f in inv["inventory"][family]["files"]:
            path = Path(f["path"])
            check("approved root " + f["relative_path"], path.resolve() == (STORE / f["relative_path"]).resolve() and path.resolve().is_relative_to(STORE / "raw/open_targets_platform/25.09"))
            check("source stat " + f["relative_path"], path.stat().st_size == f["bytes"])
            metadata = pq.ParquetFile(path).metadata
            rows = [metadata.row_group(g).num_rows for g in range(metadata.num_row_groups)]
            check("footer " + f["relative_path"], rows == f["row_group_rows"] and metadata.num_rows == f["row_count"] and metadata.num_row_groups == f["row_group_count"])
            receipt = states[f["receipt"]["receipt_id"]]
            check("receipt identity " + f["relative_path"], receipt["relative_path"].replace("\\", "/") == f["relative_path"] and receipt["status"] == "completed" and receipt["release_id"] == "25.09")
            check("receipt values " + f["relative_path"], all(receipt[k] == f["receipt"][k] for k in ["receipt_id", "dataset_id", "release_id", "bytes", "sha256", "url"]))
            total += metadata.num_rows
            groups += metadata.num_row_groups
        footer_totals[family], footer_groups[family] = total, groups
    ev_files = inv["inventory"]["gwas_credible_sets_evidence"]["files"]
    cs_files = inv["inventory"]["credible_set"]["files"]
    check("exact evidence queue paths", {f["relative_path"] for f in ev_files} == expected_ev)
    check("exact credible-set catalog paths", {f["relative_path"] for f in cs_files} == expected_cs)
    check("manifest inventory", len(manifest["files"]) == 125 and {f["relative_path"] for f in manifest["files"]} == expected_ev | expected_cs)
    for f in manifest["files"]:
        original = files[f["relative_path"]]
        receipt = original["receipt"]
        check("manifest receipt binding " + f["relative_path"], f["bytes"] == original["bytes"] and all(f[k] == receipt[k] for k in ["sha256", "receipt_id", "release_id"]) and f["publisher_url"] == receipt["url"])
    for f in labels_manifest["files"]:
        check("label source receipt " + f["relative_path"], f["receipt"] == files[f["relative_path"]]["receipt"] and f["sha256"] == f["receipt"]["sha256"] and f["bytes"] == f["receipt"]["bytes"])
    check("hash volume", sum(f["bytes"] for f in manifest["files"]) == report["resource_use"]["source_payload_bytes_hashed"])
    sc = report["scan_counts"]
    check("separate evidence passes", sc["selection_evidence_rows"] == sc["slice_evidence_rows"] == footer_totals["gwas_credible_sets_evidence"])
    check("credible-set pass", sc["credible_set_key_rows"] == footer_totals["credible_set"])
    check("label scan counts", sc["target_label_rows"] == footer_totals["target"] and sc["disease_label_rows"] == footer_totals["disease"])
    check("logical bytes add", sum(report["resource_use"]["arrow_logical_bytes_by_phase"].values()) == report["resource_use"]["arrow_logical_bytes_total"])
    check("failed then successful attempts", [a["exit_code"] for a in attempts["attempts"]] == [1, 0] and attempts["attempts"][1]["scan_counts"] == sc and attempts["attempts"][1]["resource_use"] == report["resource_use"])

    # Independent selection proof: retain all earlier-prefix locus sets, no cap-two
    # algorithm, and do not inspect measurement values in this pass.
    chosen = (binding["diseaseId"], binding["targetA"], binding["targetB"])
    check("distinct ordered targets", chosen[1] < chosen[2])
    selection_started = time.perf_counter()
    prefix = defaultdict(lambda: defaultdict(set))
    prefix_row_keys = Counter()
    scanned = retained = arrow_bytes = 0
    for f in ev_files:
        for batch in pq.ParquetFile(f["path"]).iter_batches(batch_size=8192, columns=["datasourceId", "diseaseId", "targetId", "studyLocusId"], use_threads=False):
            scanned += batch.num_rows
            arrow_bytes += batch.nbytes
            check("selection partition " + str(scanned), pc.all(pc.fill_null(pc.equal(batch.column(0), "gwas_credible_sets"), False)).as_py())
            mask = pc.fill_null(pc.less_equal(batch.column(1), chosen[0]), False)
            selected = batch.filter(mask).to_pylist()
            retained += len(selected)
            for r in selected:
                if good(r["diseaseId"]) and good(r["targetId"]):
                    prefix_row_keys[r["diseaseId"], r["targetId"], r["studyLocusId"]] += 1
                    loc = prefix[r["diseaseId"]][r["targetId"]]
                    if good(r["studyLocusId"]):
                        loc.add(r["studyLocusId"])
    earlier = []
    eligible_earlier = []
    prefix_pairs = eligible_prefix_pairs = 0
    first = None
    for d in sorted(prefix):
        for a, b in itertools.combinations(sorted(prefix[d]), 2):
            key = (d, a, b)
            n = len(prefix[d][a] | prefix[d][b])
            prefix_pairs += 1
            eligible_prefix_pairs += n >= 2
            if key < chosen:
                earlier.append({"diseaseId": d, "targetA": a, "targetB": b, "union_distinct_loci": n})
                if n >= 2:
                    eligible_earlier.append(key)
            if n >= 2 and first is None:
                first = key
    check("independently selected first eligible pair", first == chosen)
    check("no earlier eligible pair", not eligible_earlier)
    check("selection complete scan", scanned == footer_totals["gwas_credible_sets_evidence"])
    selection = {"rows_scanned": scanned, "arrow_logical_bytes": arrow_bytes, "prefix_rows_converted_to_python": retained, "prefix_diseases": len(prefix), "prefix_target_groups": sum(len(v) for v in prefix.values()), "prefix_distinct_pairs": prefix_pairs, "prefix_eligible_pairs": eligible_prefix_pairs, "earlier_pairs_checked": len(earlier), "earlier_eligible_pairs": len(eligible_earlier), "earlier_pairs": earlier, "chosen_tuple": list(chosen), "elapsed_seconds": time.perf_counter() - selection_started, "rule_check": "all full locus sets retained for earlier disease prefix; distinct ordered pair combination; exact >=2 union rule"}

    # Verify only retained source rows, using the physical locators in original files.
    grouped = defaultdict(list)
    sources = {}
    for item in excerpts["excerpts"]:
        check("excerpt bytes " + item["path"], digest(item["path"]) == item["sha256"])
        rows = load(item["path"])
        check("excerpt locators " + item["path"], len(rows) == item["row_count"] and [r["_locator"] for r in rows] == item["locators"])
        sources[Path(item["path"]).name] = rows
        for row in rows:
            loc = row["_locator"]
            projected = {k: v for k, v in row.items() if not k.startswith("_")}
            grouped[loc["relative_path"], loc["row_group"]].append((loc["row_in_group"], projected))
    decoded = logical_bytes = reconstructed = 0
    detail_counts = Counter()
    for (relative, rg), selections in grouped.items():
        path = STORE / relative
        columns = sorted(set().union(*(r.keys() for _, r in selections)))
        table = pq.ParquetFile(path).read_row_group(rg, columns=columns, use_threads=False)
        decoded += len(table)
        logical_bytes += table.nbytes
        kind = "evidence" if "/evidence/" in relative else "credible_set" if "/credible_set/" in relative else "labels"
        detail_counts[kind] += len(table)
        for index, expected in selections:
            actual = table.slice(index, 1).to_pylist()[0]
            check("original physical locator " + relative + ":" + str(rg) + ":" + str(index), actual == expected)
            reconstructed += 1
    check("selected detail row counts", detail_counts["evidence"] == sc["evidence_detail_rows_decoded"] and detail_counts["credible_set"] == sc["credible_set_detail_rows_decoded"])
    evidence = sources["source-slice-evidence.json"]
    credible = sources["source-slice-credible-set.json"]
    labels = sources["source-slice-labels.json"]
    chosen_row_keys = {k: v for k, v in prefix_row_keys.items() if k[0] == chosen[0] and k[1] in chosen[1:]}
    check("retained slice has every original matching row", Counter((r["diseaseId"], r["targetId"], r["studyLocusId"]) for r in evidence) == chosen_row_keys)
    for name, rows, expected in [("evidence", evidence, report["evidence_missing_counts"]), ("credible-set", credible, report["credible_set_missing_counts"])]:
        check(name + " missingness", {k: sum(not good(r.get(k)) for r in rows) for k in expected} == expected)
    loci = {r["studyLocusId"] for r in evidence}
    by_locus = defaultdict(list)
    for r in credible:
        by_locus[r["studyLocusId"]].append(r)
    check("selected counts", len(evidence) == 4 and len(credible) == 4 and len(loci) == 4 and len(labels) == 3 and sum(r["targetId"] == chosen[1] for r in evidence) == 1 and sum(r["targetId"] == chosen[2] for r in evidence) == 3)
    check("every locus resolved once", set(by_locus) == loci and all(len(v) == 1 for v in by_locus.values()))
    check("evidence identifiers present", len({r["id"] for r in evidence}) == 4 and all(good(r["id"]) and good(r["studyLocusId"]) for r in evidence))
    check("all comparison unknowns", all(r["studyId"] is None and r["variantId"] is None for r in evidence) and report["identity_comparison_counts"] == {"studyId": {"not_assessable": 4}, "variantId": {"not_assessable": 4}})
    check("source object labels not independent groups", len({r["studyId"] for r in credible}) == 3 and len({r["variantId"] for r in credible}) == 3)
    check("GWAS source type", all(r["studyType"] == "gwas" for r in credible))
    check("all PICS", all(r["finemappingMethod"] == "PICS" for r in credible))
    studies_by_target = {t: {by_locus[r["studyLocusId"]][0]["studyId"] for r in evidence if r["targetId"] == t} for t in chosen[1:]}
    check("reported study reuse across target groups", len(studies_by_target[chosen[1]] & studies_by_target[chosen[2]]) == 1)
    check("quality counters zero", all(v == 0 for v in report["quality_counts"].values()))
    counts = {"evidence_rows": len(evidence), "credible_set_rows": len(credible), "label_rows": len(labels), "distinct_objects": len(loci), "reported_study_ids": len({r["studyId"] for r in credible}), "reported_variant_ids": len({r["variantId"] for r in credible}), "unknown_study_comparisons": 4, "unknown_variant_comparisons": 4, "source_quality_control_sets": sorted({tuple(r["qualityControls"]) for r in credible}), "source_confidence_labels": sorted({r["confidence"] for r in credible}), "identifier_labels": [{k: v for k, v in r.items() if not k.startswith("_")} for r in labels]}
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": "pass", "scope": "independent source-only feasibility selection, receipt metadata, footers and 8 original source +3 label rows; not candidate evaluation", "checks": CHECKS, "footer_totals": footer_totals, "footer_row_groups": footer_groups, "selection": selection, "locator_reads": {"physical_row_groups": len(grouped), "row_group_rows_decoded": decoded, "arrow_logical_bytes": logical_bytes, "retained_records_reconstructed": reconstructed, "detail_rows_by_kind": dict(detail_counts)}, "selected_source_counts": counts, "elapsed_seconds": time.perf_counter() - started, "limitations": ["No repeated whole-payload source hash scan; inherited raw SHA verification from pinned source-agent manifests and exact acquisition receipt bytes", "No fresh memory or physical-I/O measurement", "No claim of first-attempt immutability: failed telemetry attempt and successful rerun explicitly recorded", "No original study/cohort/participant or LD/variant-array reads; no causal or independence validation", "Selected missingness is not a global estimate; all file footers and projected IDs do not assess all scientific fields"], "input_pins": {str(p.relative_to(ROOT)): digest(p) for p in sorted(DATA.glob('*.json'))}, "checker_sha256": digest(__file__)}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "check_count": len(CHECKS), "selection": selection, "locator_reads": result["locator_reads"], "selected_source_counts": counts, "report": str(OUT)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        failure = HERE / ("INDEPENDENT-FEASIBILITY-FAILURE-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        failure.write_text(json.dumps({"error_type": type(exc).__name__, "message": str(exc), "checks": CHECKS}, indent=2) + "\n", encoding="utf-8")
        raise
