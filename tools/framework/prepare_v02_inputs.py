"""Select pinned inputs from existing transport receipts; never control the downloader."""
import copy
from pathlib import Path

from asof.ingest import InputFile, InputManifest
from asof.serde import read_json, safe_child, write_json


def main():
    project = Path(__file__).resolve().parents[2]
    catalog_path = project / "data/catalog/sources.json"
    catalog = read_json(catalog_path)
    if not any(row["dataset_id"] == "asof_normalized_packets" for row in catalog["datasets"]):
        template = copy.deepcopy(next(row for row in catalog["datasets"] if row["dataset_id"] == "evidence_ledgers"))
        template.update(dataset_id="asof_normalized_packets", provider_id="project",
            name="AsOf v2 contemporary normalized evidence packets", roles=["agent_evidence"],
            supported_tasks=["T6"], supported_hypotheses=[], supported_ablations=[],
            purpose="Receipt-verified contemporary target/disease/evidence packets with complete raw-input lineage",
            required_fields=["schema_version", "origin_at", "hypothesis_key", "input_refs", "source_locator",
                             "source_metrics", "missingness", "availability", "computed_at"],
            field_contract_note="Runtime v2 contracts; provider scores are descriptive. No real prediction features or clinical probabilities.",
            collection_scope="Ten development hypotheses; selected Open Targets 25.09/HGNC inputs. Source completeness is explicit.",
            formats=["JSON (version 2)", "Markdown dossiers"],
            release_policy="Immutable build-time UTC cutoff and checksum-backed input manifests; never historical backfill",
            candidate_releases=["Build-time UTC snapshots"],
            dependencies=["ot_target", "ot_disease", "ot_evidence", "hgnc_symbols"],
            collection_status="planned", parse_status="not_run", validation_status="not_run",
            blockers=["Build, integrity/semantic verification and retained source-field audit must complete"])
        template["temporal"].update(classification="contemporary_only", annotation_version="Open Targets 25.09 / HGNC snapshot_2026-10-10",
            eligibility_note="Verified public-download observations bound current availability; no historical eligibility claim",
            unknowns=["Earliest publisher availability and scientific interpretation remain unverified"])
        template["verification"].update(level="not_checked", checked_at=None, evidence=[],
            next_acquisition_check="Run v2 build, verify every dossier and audit twenty statements against source rows")
        for key in template["profile_policy"]:
            template["profile_policy"][key] = ("contemporary_development_only" if key == "contemporary_assessment" else
                                               "excluded_from_this_milestone")
        catalog["datasets"].append(template)
        catalog["last_updated"] = "2026-10-10"
        catalog["scope"] = "Full requirements catalog with transport and v2 contemporary normalization; scientific/model validation remains separate."
        write_json(catalog_path, catalog)
    raw_root = Path("E:/projects_data/drug_target_agents_data")
    rows = []
    for name in ("core-2026-10-10-queue.json", "starter-2026-10-10-queue.json"):
        queue = read_json(project / "data/manifests/private" / name)
        rows.extend(row for row in queue["files"] if row["dataset_id"] in (
            "ot_target", "ot_disease", "ot_evidence", "hgnc_symbols"))
    files, missing, expected = [], [], {}
    for row in rows:
        if "sourceId=chembl" in row["relative_path"].replace("\\", "/").split("/"):
            continue
        expected[row["dataset_id"]] = expected.get(row["dataset_id"], 0) + 1
        receipt_relative = "manifests/receipts/" + row["receipt_id"] + ".json"
        receipt_path = safe_child(raw_root, receipt_relative)
        if not receipt_path.is_file() or not safe_child(raw_root, row["relative_path"]).is_file():
            missing.append(row["relative_path"])
            continue
        receipt = read_json(receipt_path)
        if receipt.get("status") != "completed":
            missing.append(row["relative_path"])
            continue
        files.append(InputFile(row["dataset_id"], row["release_id"], row["relative_path"], receipt_relative))
    destination = project / "data/manifests/private/v02-inputs.json"
    write_json(destination, InputManifest(2, str(raw_root), tuple(files), expected, tuple(missing)))
    print(f"Prepared explicit input manifest: {destination}")
    print("No transport queues, worker or monitoring configuration changed.")


if __name__ == "__main__":
    main()
