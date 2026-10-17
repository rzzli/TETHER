"""Compare pinned 2.1/2.2 packets and recheck the original review rows locally.

This is a technical fidelity comparison, not an efficacy or expert-gold assessment.
It never mutates a snapshot, run, registry or download receipt.
"""
from __future__ import annotations

import argparse
import gc
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from asof.contracts import Case
from asof.ingest import REVIEW_CONTEXT_COLUMNS
from asof.serde import ContractError, decode, fingerprint, read_json, safe_child, sha256_file, write_json
from tools.framework.run_pilot import SourceAudit


def compare_observation(before, after):
    """Reject any unplanned scientific edit while allowing the versioned projection."""
    for key, value in before.items():
        if key not in ("method", "source_metrics") and value != after.get(key):
            raise ContractError(f"Unexpected observation change: {key}")
    old_metrics, new_metrics = before["source_metrics"], after["source_metrics"]
    if any(new_metrics.get(key) != value or key not in new_metrics for key, value in old_metrics.items()):
        raise ContractError("Previously retained source context changed")
    if set(new_metrics) - set(old_metrics) - set(REVIEW_CONTEXT_COLUMNS):
        raise ContractError("Unexpected new provider field")
    method = after["method"]
    if method["code_id"] != "asof.opentargets.normalize" or method["version"] != "2.2":
        raise ContractError("Expected normalization recipe 2.2")
    if method["parameters"].get("interpretation_scope") != "resource_annotation_only":
        raise ContractError("Missing interpretation boundary")
    old_method = before["method"]
    if any(method.get(key) != value for key, value in old_method.items() if key not in ("version", "parameters")):
        raise ContractError("Previously retained method/QC declaration changed")
    old_params, new_params = old_method["parameters"], method["parameters"]
    if any(new_params.get(key) != value for key, value in old_params.items()
           if key not in ("projection", "source_row_sha256")):
        raise ContractError("Previously retained method parameter changed")
    if (set(old_params["projection"]) - set(new_params["projection"]) or
            set(new_params["projection"]) - set(old_params["projection"]) - set(REVIEW_CONTEXT_COLUMNS)):
        raise ContractError("Unexpected projection change")
    return [field for field in REVIEW_CONTEXT_COLUMNS
            if field not in old_metrics and new_metrics.get(field) not in (None, [], "")]


def compare(before, after, baseline_run, new_run, output):
    output.mkdir(parents=True, exist_ok=False)
    old_build, new_build = read_json(before / "build-report.json"), read_json(after / "build-report.json")
    old_pilot, new_pilot = read_json(baseline_run / "pilot-report.json"), read_json(new_run / "pilot-report.json")
    old_audit = read_json(baseline_run / "source-review.json")
    if (sha256_file(baseline_run / "source-review.json") != old_pilot["source_review_sha256"] or
            sha256_file(new_run / "source-review.json") != new_pilot["source_review_sha256"]):
        raise ContractError("Source review report hash differs from pilot")
    if new_pilot["status"] != "completed" or len(new_pilot["cases"]) != 10:
        raise ContractError("Ten completed revised runs required")
    for entry in new_pilot["cases"]:
        if (entry["status"] != "verified" or entry["verification"]["semantic_consistency"] != "verified" or
                sha256_file(safe_child(new_run, entry["case_id"]) / "receipt.json") != entry["receipt_sha256"]):
            raise ContractError("Revised run lacks retained semantic verification or receipt anchor")
    old_files = read_json(before / "inspection.json")["files"]
    new_files = read_json(after / "inspection.json")["files"]
    if {row["source"]["source_id"]: row["source"] for row in old_files} != {
            row["source"]["source_id"]: row["source"] for row in new_files}:
        raise ContractError("Raw source/receipt inventory changed")
    if old_build["inspection"]["missing_inputs"] != new_build["inspection"]["missing_inputs"]:
        raise ContractError("Frozen missing-input list changed")
    old_cases = {item["case_id"]: item for item in old_build["cases"]}
    new_cases = {item["case_id"]: item for item in new_build["cases"]}
    if set(old_cases) != set(new_cases) or len(new_cases) != 10:
        raise ContractError("Development case set changed")
    auditor, cases, reviewed, seen = SourceAudit(), [], [], set()
    for case_id, item in new_cases.items():
        old_dir, new_dir = safe_child(before, case_id), safe_child(after, case_id)
        for directory, entry in ((old_dir, old_cases[case_id]), (new_dir, item)):
            if sha256_file(directory / "evidence.json") != entry["packet_sha256"]:
                raise ContractError("Packet changed after build")
        old_case = decode(Case, read_json(old_dir / "case.json"))
        new_case = decode(Case, read_json(new_dir / "case.json"))
        if old_case.hypothesis.key != new_case.hypothesis.key:
            raise ContractError("This comparison requires unchanged development hypotheses")
        old_observations = {row["observation_id"]: row for row in read_json(old_dir / "evidence.json")["observations"]}
        new_observations = {row["observation_id"]: row for row in read_json(new_dir / "evidence.json")["observations"]}
        if set(old_observations) != set(new_observations):
            raise ContractError("Observation set changed; investigate before attributing effects to projection")
        enriched = Counter()
        for key, observation in new_observations.items():
            enriched.update(compare_observation(old_observations[key], observation))
        snapshot = read_json(new_dir / "snapshot.json")
        nodes = {node["source_id"]: node for node in snapshot["sources"]}
        for original in (row for row in old_audit["rows"] if row["case_id"] == case_id):
            observation = new_observations[original["observation_id"]]
            locator = observation["source_locator"]
            identity = (locator["source_id"], locator["row_group"], locator["row"])
            if identity != (original["source_id"], original["row_group"], original["row"]) or identity in seen:
                raise ContractError("Original review row identity changed or repeated")
            seen.add(identity)
            node = nodes[locator["source_id"]]
            if node["sha256"] != original["source_sha256"]:
                raise ContractError("Original reviewed source hash changed")
            projection = observation["method"]["parameters"]["projection"]
            raw = auditor.parquet_row(node, snapshot["raw_root"], locator, projection)
            if fingerprint(raw) != observation["method"]["parameters"]["source_row_sha256"]:
                raise ContractError("Revised row projection differs from original source")
            recovered = {field: raw[field] for field in REVIEW_CONTEXT_COLUMNS if raw.get(field) not in (None, [], "")}
            if any(observation["source_metrics"].get(field) != value for field, value in recovered.items()):
                raise ContractError("Reviewed source context still missing")
            reviewed.append({"case_id": case_id, "observation_id": observation["observation_id"],
                "source_locator": locator, "source_sha256": node["sha256"], "recovered_context": recovered,
                "technical_result": "passed", "scientific_validation": "not_run"})
        cases.append({"case_id": case_id, "observations": len(new_observations), "hypothesis_key": new_case.hypothesis.key,
                      "nonempty_fields_recovered": dict(enriched), "before_packet_bytes": old_cases[case_id]["packet_bytes"],
                      "after_packet_bytes": item["packet_bytes"], "qualification": snapshot["coverage"]["hypothesis_qualification"]})
        del old_observations, new_observations
        gc.collect()
    if len(reviewed) < 20:
        raise ContractError("Original twenty-row recheck incomplete")
    report = {"schema_version": 1, "status": "passed", "role": "evaluation_only", "created_at_utc": datetime.now(timezone.utc),
              "before": str(before), "after": str(after), "baseline_run": str(baseline_run), "new_run": str(new_run),
              "before_origin": old_build["origin_at_utc"], "after_origin": new_build["origin_at_utc"],
              "same_raw_inputs": True, "same_hypotheses": True, "same_observation_ids_and_original_fields": True,
              "cases": cases, "original_review_rows_rechecked": reviewed,
              "new_pilot_audited_rows": new_pilot["audited_distinct_rows"],
              "source_inventory_files": len(new_files), "missing_inputs": len(new_build["inspection"]["missing_inputs"]),
              "scientific_validation": "not_run", "provider_spend_usd": 0,
              "anchors": {str(path): sha256_file(path) for path in (before / "build-report.json", after / "build-report.json",
                          baseline_run / "pilot-report.json", new_run / "pilot-report.json", baseline_run / "source-review.json",
                          new_run / "source-review.json")}}
    write_json(output / "comparison.json", report)
    lines = ["# Context revision: before and after", "",
             "Ten unchanged development hypotheses were rebuilt with normalization 2.2 using the same pinned raw files and archived receipts. "
             "All previous observation IDs, statements, scientific values and source fields are preserved. "
             "The new cutoff is contemporary; this is not a historical reconstruction.", "",
             f"Original review rows rechecked: {len(reviewed)}. New pilot source-audit rows: {new_pilot['audited_distinct_rows']}. "
             "All ten runs passed source-inclusive semantic verification. Numerical predictions remain withheld.", "",
             "| Case | Records | Newly retained nonempty fields (record counts) | Packet MiB before → after |",
             "| --- | ---: | --- | ---: |"]
    for row in cases:
        fields = "; ".join(f"{key}: {value}" for key, value in row["nonempty_fields_recovered"].items()) or "None reported"
        lines.append(f"| {row['case_id']} | {row['observations']} | {fields} | "
                     f"{row['before_packet_bytes']/2**20:.2f} → {row['after_packet_bytes']/2**20:.2f} |")
    lines += ["", "Packet size reduction comes from compact JSON, not dropped records. "
              "Clinical status/outcome fields and evaluator judgments remain excluded. "
              "Provider scores remain descriptive; variant classifications are frozen source annotations, not reconciled current judgments.", "",
              "## Remaining interpretation limits", "",
              "Action/modality relevance is explicitly unassessed. Disease subtype, population, regimen and endpoint remain unspecified; "
              "HER2 biomarker, familial hypercholesterolemia subtype/LDLR function, CFTR genotype/protein production/modulator mechanism, "
              "and neuropathy subtype are explicit unresolved qualifications where applicable. No narrower case was invented. "
              "Refined hypotheses require versioned contracts and new fingerprints before execution.", "",
              "The 65 missing inputs remain missing. Article type and citation-chain interpretation are not inferred from a passage. "
              "Text-mining sections are preserved as provider-reported context. Historical ClinVar reconstruction and full current CFTR-label "
              "reconciliation remain open. This technical correction is not independent scientific validation.", ""]
    (output / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "baseline-run", "new-run", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.before.resolve(), args.after.resolve(), args.baseline_run.resolve(), args.new_run.resolve(), args.output.resolve())
    print(f"Compared {len(report['cases'])} cases; rechecked {len(report['original_review_rows_rechecked'])} original rows.")


if __name__ == "__main__":
    main()
