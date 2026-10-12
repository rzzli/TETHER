"""Run the fixed offline development pack and independently audit original rows.

Existing output is never resumed or overwritten. Each CLI attempt has durable console
files and a run journal. This is a technical source audit, not biological adjudication.
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from asof.ingest import PILOT, peak_memory_bytes
from asof.serde import ContractError, fingerprint, read_json, read_ledger_json, safe_child, sha256_file, write_json


CONTEXT_FIELDS = (
    "biosamplesFromSource", "diseaseCellLines", "biologicalModelId",
    "biologicalModelAllelicComposition", "biologicalModelGeneticBackground",
    "targetInModel", "targetInModelEnsemblId", "targetInModelMgiId",
    "variantId", "variantRsId", "variantFromSourceId", "variantHgvsId",
    "variantAminoacidDescriptions", "variantFunctionalConsequenceId",
    "variantEffect", "directionOnTrait", "cellType", "ancestry", "ancestryId",
    "geneticBackground", "alleleOrigins", "allelicRequirements", "sex", "contrast",
    "crisprScreenLibrary", "diseaseModelAssociatedHumanPhenotypes", "diseaseModelAssociatedModelPhenotypes",
    "cohortDescription", "cohortPhenotypes", "cohortShortName", "studyLocusId", "targetModulation",
)
FORBIDDEN = {"clinicalPhase", "clinicalStatus", "trialPhase", "trialStatus",
             "studyStopReason", "studyStopReasonCategories", "trialOutcome", "outcome"}
CATEGORIES = {"genetic_association": "genetics", "somatic_mutation": "genetics",
              "rna_expression": "expression", "animal_model": "perturbation",
              "affected_pathway": "pathway", "literature": "literature"}


def raw_json(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: raw_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [raw_json(item) for item in value]
    return value


def present_context(observation):
    metrics = observation["source_metrics"]
    return {name for name in CONTEXT_FIELDS if metrics.get(name) not in (None, [], "")}


class SourceAudit:
    def __init__(self):
        self.seen, self.contexts, self.hashes = set(), set(), {}
        self.rows, self.coverage = [], []

    def source(self, node, raw_root):
        path = safe_child(Path(raw_root), node["path"])
        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cached = self.hashes.get(str(path))
        if cached is None or cached[0] != signature:
            digest = sha256_file(path)
            after = path.stat()
            if signature != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ContractError("Source audit file changed during hash verification")
            self.hashes[str(path)] = signature, digest
        if self.hashes[str(path)][1] != node["sha256"]:
            raise ContractError("Source audit raw hash mismatch")
        return path

    def parquet_row(self, node, raw_root, locator, columns):
        import pyarrow.parquet as pq
        parquet = pq.ParquetFile(self.source(node, raw_root))
        group, offset = locator["row_group"], locator["row"]
        if (type(group) is not int or type(offset) is not int or group < 0 or offset < 0 or
                group >= parquet.num_row_groups):
            raise ContractError("Invalid audit row locator")
        projection = [key for key in columns if key in parquet.schema_arrow.names]
        table = parquet.read_row_group(group, columns=projection)
        if offset >= len(table):
            raise ContractError("Audit locator outside row group")
        return raw_json(table.slice(offset, 1).to_pylist()[0])

    def mappings(self, bundle_case, case, snapshot):
        validation = read_json(bundle_case / "identifier-validation.json")
        nodes = {node["source_id"]: node for node in snapshot["sources"]}
        actual = {}
        for key in ("target", "disease"):
            recorded, locator = validation[key]
            node = nodes[locator["source_id"]]
            if node["dataset_id"] != "ot_" + key or node["release_id"] != "25.09":
                raise ContractError("Identifier audit references the wrong provider product")
            actual[key] = self.parquet_row(nodes[locator["source_id"]], snapshot["raw_root"],
                                           locator, tuple(recorded))
            if actual[key] != recorded:
                raise ContractError("Identifier audit differs from original provider row")
        recorded, locator = validation["hgnc"]
        node = nodes[locator["source_id"]]
        if (node["dataset_id"] != "hgnc_symbols" or node["release_id"] != "snapshot_2026-10-10" or
                type(locator["row"]) is not int or locator["row"] < 0):
            raise ContractError("HGNC audit reference is invalid")
        path = self.source(node, snapshot["raw_root"])
        with path.open(encoding="utf-8-sig", newline="") as stream:
            actual_hgnc = next((row for index, row in enumerate(csv.DictReader(stream, delimiter="\t"))
                                if index == locator["row"]), None)
        if actual_hgnc != recorded or recorded["status"] != "Approved":
            raise ContractError("HGNC source row differs from approved mapping")
        hypothesis = case["hypothesis"]
        if (actual["target"]["id"] != hypothesis["target_id"] or
                actual["disease"]["id"] != hypothesis["indication_id"] or
                recorded["ensembl_gene_id"] != hypothesis["target_id"] or
                actual["target"]["approvedSymbol"] != recorded["symbol"]):
            raise ContractError("Audit canonical identifiers disagree")
        if (hypothesis["target_namespace_version"] != "OpenTargets-25.09:target:" +
                nodes[validation["target"][1]["source_id"]]["sha256"] or
                hypothesis["indication_namespace_version"] != "OpenTargets-25.09:disease:" +
                nodes[validation["disease"][1]["source_id"]]["sha256"] or
                hypothesis["tissue"] is not None or
                (recorded["symbol"], hypothesis["indication_id"], hypothesis["intended_action"], hypothesis["modality"]) not in PILOT):
            raise ContractError("Audited hypothesis differs from pinned development pack")
        return actual["target"]["approvedSymbol"], actual["disease"]["name"]

    def case(self, run_dir, bundle_case):
        inputs = read_json(run_dir / "inputs.json")
        case, snapshot = inputs["case"], inputs["snapshot"]
        if any(item["case_id"] == case["case_id"] for item in self.coverage):
            raise ContractError("Development hypothesis already audited")
        nodes = {node["source_id"]: node for node in snapshot["sources"]}
        symbol, disease_name = self.mappings(bundle_case, case, snapshot)
        claims = read_ledger_json(run_dir / "ledger.json")["claims"]
        candidates = []
        for claim in claims:
            observation = claim["evidence"]["observation"]
            if observation["features"]:
                raise ContractError("Real-data pilot unexpectedly contains numerical features")
            locator = observation["source_locator"]
            identity = (locator["source_id"], locator["row_group"], locator["row"])
            if identity not in self.seen:
                candidates.append((claim, observation, identity))
        selected, case_rows = [], []
        seen, contexts = set(self.seen), set(self.contexts)
        for claim, observation, identity in sorted(candidates, key=lambda item: item[1]["observation_id"]):
            if identity not in seen and present_context(observation) - contexts:
                selected.append((claim, observation, identity))
                contexts.update(present_context(observation))
                seen.add(identity)
        # At least two physically distinct rows per development hypothesis, including
        # sparse context. Rich context rows above are additional stratified checks.
        for item in sorted(candidates, key=lambda item: (len(present_context(item[1])), item[1]["observation_id"])):
            if len(selected) >= 2:
                break
            if item[2] not in seen:
                selected.append(item)
                seen.add(item[2])
        if len(selected) < 2:
            raise ContractError("Insufficient distinct rows for the required pilot audit")
        for claim, observation, identity in selected:
            locator = observation["source_locator"]
            node = nodes[locator["source_id"]]
            if node["dataset_id"] != "ot_evidence" or node["release_id"] != "25.09":
                raise ContractError("Evidence audit references the wrong provider product")
            projection = observation["method"]["parameters"]["projection"]
            row = self.parquet_row(node, snapshot["raw_root"], locator, tuple(dict.fromkeys((*projection, *CONTEXT_FIELDS))))
            if set(projection) - row.keys() or len(projection) != len(set(projection)):
                raise ContractError("Audit projection contains missing or duplicate fields")
            projected = {key: row[key] for key in projection}
            if fingerprint(projected) != observation["method"]["parameters"]["source_row_sha256"]:
                raise ContractError("Normalized row fingerprint differs from original projection")
            if (row["id"] != locator["evidence_id"] or row["datasourceId"] != locator["datasource_id"] or
                    row["targetId"] != observation["target_id"] or row["diseaseId"] != observation["indication_id"]):
                raise ContractError("Evidence identity or target/indication mismatch")
            if observation["observation_id"] != f"ot25:{row['datasourceId']}:{row['id']}":
                raise ContractError("Normalized observation identifier differs from source")
            if row["datasourceId"] == "chembl" or row["datatypeId"] not in CATEGORIES:
                raise ContractError("Excluded or unsupported source entered a claim")
            if observation["category"] != CATEGORIES[row["datatypeId"]]:
                raise ContractError("Incorrect datatype/category mapping")
            expected_statement = (f"Open Targets 25.09 record {row['id']} from {row['datasourceId']} links {symbol} "
                f"({row['targetId']}) to {disease_name} ({row['diseaseId']}); datatype {row['datatypeId']}; "
                f"provider evidence score {row.get('score')}. This is a resource annotation.")
            if observation["statement"] != expected_statement:
                raise ContractError("Claim statement differs from original source and identifier rows")
            metrics = observation["source_metrics"]
            expected_metrics = {key: value for key, value in projected.items() if key not in (
                "id", "targetId", "diseaseId", "datasourceId", "datatypeId")}
            if metrics != expected_metrics or FORBIDDEN.intersection(metrics):
                raise ContractError("Source metrics differ or contain excluded clinical fields")
            for field in CONTEXT_FIELDS:
                if row.get(field) not in (None, [], "") and metrics.get(field) != row[field]:
                    raise ContractError(f"Reported context lost: {field}")
            if observation["context"]["tissue"] is not None:
                raise ContractError("Pilot tissue must remain unresolved without a validated mapping")
            if observation["mechanism_direction"] != "uncertain":
                raise ContractError("Provider variant direction became an intervention recommendation")
            context, missing = observation["context"], observation["missingness"]
            if any(context[key] is not None for key in ("species", "disease_state", "intervention", "comparator")):
                raise ContractError("Unresolved scientific context acquired an unsupported value")
            if (any(value is not None for value in observation["quantitative"].values()) or
                    observation["feature_scope"] is not None or observation["program_id"] is not None or
                    observation["polarity"] != "uncertain" or
                    observation["method"]["parameters"].get("scientific_validation") != "not_run"):
                raise ContractError("Unreviewed source metrics became an interpreted result")
            study, cohort = row.get("studyId"), row.get("cohortId")
            study = str(study) if study is not None else None
            cohort = str(cohort) if cohort is not None else None
            source = str(row["datasourceId"])
            expected_group = source + ":cohort:" + cohort if cohort else source + ":study:" + study if study else None
            ancestry = row.get("ancestry") if isinstance(row.get("ancestry"), str) and row.get("ancestry") else None
            if (observation["study_id"] != (source + ":" + study if study else None) or
                    observation["dependency_group"] != expected_group or
                    context["cohort_ids"] != ([source + ":" + cohort] if cohort else []) or context["ancestry"] != ancestry):
                raise ContractError("Study, cohort or ancestry differs from original source")
            expected_unknown = {"species", "effect_scale", "scientific_interpretation", "tissue"}
            expected_unknown.update(key for key, value in (("study_id", study), ("cohort", cohort), ("ancestry", ancestry)) if not value)
            if any(not missing.get(key) for key in expected_unknown) or missing.get("scientific_interpretation") != "unreviewed":
                raise ContractError("Required unknown scientific context is not reported")
            case_rows.append({"case_id": case["case_id"], "claim_id": claim["claim_id"],
                "observation_id": observation["observation_id"], "source_id": node["source_id"],
                "source_path": node["path"], "source_sha256": node["sha256"],
                "row_group": locator["row_group"], "row": locator["row"],
                "datasource_id": row["datasourceId"], "datatype_id": row["datatypeId"],
                "statement": observation["statement"], "original_score": row.get("score"),
                "preserved_context": {key: row[key] for key in CONTEXT_FIELDS if row.get(key) not in (None, [], "")},
                "unknown_fields": observation["missingness"], "publication_date": observation["publication_date"],
                "publication_year": observation["publication_year"], "technical_result": "passed",
                "scientific_adjudication": "not_run"})
        self.rows.extend(case_rows)
        self.seen, self.contexts = seen, contexts
        self.coverage.append({"case_id": case["case_id"], "audited_distinct_rows": len(selected),
                              "coverage": snapshot["coverage"]})

    def report(self):
        return {"schema_version": 1, "audit_type": "original_row_and_mapping_technical_review",
            "created_at_utc": datetime.now(timezone.utc), "distinct_original_rows": len(self.rows),
            "cases": self.coverage, "rows": self.rows, "reported_context_fields_checked": sorted(self.contexts),
            "scientific_adjudication": "not_run", "conflicting_evidence": "No conflicting duplicate IDs observed in this selected build; conflict rejection is tested with synthetic fixtures",
            "limitations": ["Not an independent biological interpretation or expert gold-standard audit",
                            "Selected source coverage is incomplete; unavailable inputs are not biological absence"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(), args.output.resolve()
    build = read_json(bundle / "build-report.json")
    if build["status"] != "built" or build["blocked_cases"] or len(build["cases"]) != len(PILOT):
        raise ContractError("Pilot requires all ten built canonical cases")
    output.mkdir(parents=True, exist_ok=False)
    logs = output / "console"
    logs.mkdir()
    started = time.monotonic()
    report = {"schema_version": 1, "status": "running", "bundle": str(bundle),
              "build_report_sha256": sha256_file(bundle / "build-report.json"),
              "pilot_helper_sha256": sha256_file(Path(__file__)),
              "catalog_sha256": sha256_file(args.catalog), "created_at_utc": datetime.now(timezone.utc),
              "cases": [], "scientific_validation": "not_run", "provider_spend_usd": 0}
    audit = SourceAudit()
    write_json(output / "pilot-report.json", report)
    try:
        for item in build["cases"]:
            case_id = item["case_id"]
            case_dir, run_dir = safe_child(bundle, case_id), safe_child(output, case_id)
            entry = {"case_id": case_id, "status": "dispatching", "run_dir": str(run_dir)}
            report["cases"].append(entry)
            write_json(output / "pilot-report.json", report)
            case_started = time.monotonic()
            with (logs / (case_id + ".stdout.json")).open("w", encoding="utf-8") as stdout, (logs / (case_id + ".stderr.log")).open("w", encoding="utf-8") as stderr:
                completed = subprocess.run([sys.executable, "-m", "asof", "run", "--case", str(case_dir / "case.json"),
                    "--snapshot", str(case_dir / "snapshot.json"), "--catalog", str(args.catalog.resolve()),
                    "--output", str(run_dir)], stdout=stdout, stderr=stderr, check=False)
            entry["exit_code"] = completed.returncode
            if completed.returncode:
                raise ContractError(f"Offline case failed: {case_id}; retained console/journal require inspection")
            answer = read_json(logs / (case_id + ".stdout.json"))
            anchor = answer["receipt_sha256"]
            from asof.artifacts import verify_run
            verification = verify_run(run_dir, anchor)
            if verification["semantic_consistency"] != "verified":
                raise ContractError("Pilot semantic verification did not pass")
            prediction = read_json(run_dir / "prediction.json")
            if prediction["probability"] is not None or prediction["status"] != "audit_only":
                raise ContractError("Pilot must withhold clinical probabilities")
            audit.case(run_dir, case_dir)
            write_json(output / "source-review.json", audit.report())
            entry.update(status="verified", receipt_sha256=anchor, verification=verification,
                         claims=answer["claims"], elapsed_seconds=time.monotonic() - case_started,
                         output_bytes=sum(path.stat().st_size for path in run_dir.iterdir() if path.is_file()))
            write_json(output / "pilot-report.json", report)
            print(f"Verified {case_id}: {answer['claims']} claims", flush=True)
            gc.collect()
        if len(audit.rows) < 20:
            raise ContractError("Pilot source-review threshold not met")
        report.update(status="completed", elapsed_seconds=time.monotonic() - started,
            peak_memory_bytes=peak_memory_bytes(), peak_memory_scope="pilot_parent_source_verification_and_audit_only",
            source_review_sha256=sha256_file(output / "source-review.json"),
            audited_distinct_rows=len(audit.rows), output_bytes=sum(path.stat().st_size for path in output.rglob("*") if path.is_file()))
        write_json(output / "pilot-report.json", report)
        lines = ["# Contemporary T6 development dossiers", "", "All probabilities are withheld. Technical source review is not independent scientific adjudication.", "",
                 "| Case | Claims | Dossier |", "| --- | ---: | --- |"]
        for entry in report["cases"]:
            lines.append(f"| {entry['case_id']} | {entry['claims']} | [Dossier]({entry['case_id']}/dossier.md) |")
        lines += ["", f"Original rows audited: {len(audit.rows)}. See source-review.json and pilot-report.json."]
        (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps({"status": "completed", "output": str(output), "cases": len(report["cases"]),
                          "audited_distinct_rows": len(audit.rows)}, indent=2))
    except BaseException as error:
        report.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                      error_class=type(error).__name__, error=str(error), elapsed_seconds=time.monotonic() - started)
        write_json(output / "pilot-report.json", report)
        raise


if __name__ == "__main__":
    main()
