"""Freeze deterministic source-grounded T6 reference packets before arm outputs.

This is a technical source audit and reference-preparation product. It contains no
arm predictions, therapeutic gold answers, interpreted genetic features or scores.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from pathlib import Path
import time

from tether_engine.contracts import Case, Observation, Profile, Snapshot, validate_observation
from tether_engine.ingest import EVIDENCE_COLUMNS, NORMALIZATION_VERSION, _load_case_pack, _publication, peak_memory_bytes
from tether_engine.journal import RunJournal
from tether_engine.provenance import InputGraph, catalog_index
from tether_engine.serde import ContractError, decode, fingerprint, read_json, safe_child, sha256_file, write_json
from tools.framework.run_pilot import CATEGORIES, CONTEXT_FIELDS, FORBIDDEN, SourceAudit


SEED = "science2-20261018"
CASE_PACK_SHA256 = "3d9e5763e5b9a48bd333dc67697becf1badf00d83ed166fc5a018c40dac62f90"
IDENTITY_FIELDS = {"id", "targetId", "diseaseId", "datasourceId", "datatypeId"}


def _physical_key(observation):
    locator = observation.get("source_locator", {})
    keys = ("source_id", "row_group", "row")
    if any(key not in locator for key in keys):
        raise ContractError("Evidence requires an explicit physical source locator")
    if (not isinstance(locator["source_id"], str) or not locator["source_id"] or
            any(type(locator[key]) is not int or locator[key] < 0 for key in keys[1:])):
        raise ContractError("Evidence source locator requires a source ID and nonnegative integer offsets")
    return tuple(locator[key] for key in keys)


def select_observations(observations, case_id, *, maximum=5, seed=SEED):
    """Greedy category/provider/study spread with identity-hash ties, never score rank."""
    if type(maximum) is not int or not 1 <= maximum <= 5:
        raise ContractError("Reference selection limit must be an integer from one to five")
    if not isinstance(seed, str) or not seed:
        raise ContractError("Reference selection seed must be explicit")
    ids, physical, candidates = set(), set(), []
    for row in observations:
        identity = row.get("observation_id")
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ContractError("Duplicate or missing reference observation ID")
        locator = _physical_key(row)
        if locator in physical:
            raise ContractError("Duplicate physical evidence row in a case")
        ids.add(identity)
        physical.add(locator)
        provider = row.get("source_locator", {}).get("datasource_id")
        if not isinstance(provider, str) or not provider:
            raise ContractError("Reference evidence provider must be explicit")
        rank = fingerprint({"seed": seed, "case_id": case_id, "observation_id": identity,
                            "physical_locator": locator})
        candidates.append((row, provider, row.get("study_id"), rank))
    chosen, categories, providers, studies = [], set(), set(), set()
    while candidates and len(chosen) < maximum:
        index = min(range(len(candidates)), key=lambda i: (
            -(candidates[i][0]["category"] not in categories),
            -(candidates[i][1] not in providers),
            -(candidates[i][2] is not None and candidates[i][2] not in studies), candidates[i][3]))
        row, provider, study, _ = candidates.pop(index)
        chosen.append(row)
        categories.add(row["category"])
        providers.add(provider)
        if study is not None:
            studies.add(study)
    return chosen


def _source(audit, graph, node, proofs):
    key = node["source_id"]
    if not node["source_url"].startswith(("https://ftp.ebi.ac.uk/", "https://storage.googleapis.com/public-download-files/hgnc/")):
        raise ContractError("Reference source URL is outside the approved public-source origins")
    path = audit.source(node, graph.snapshot.raw_root)
    if key not in proofs:
        receipt_path = node.get("receipt_path")
        if not receipt_path or not node.get("receipt_sha256"):
            raise ContractError("Reference audit requires archived public-download receipt proofs")
        receipt_file = safe_child(Path(graph.snapshot.raw_root), receipt_path)
        if sha256_file(receipt_file) != node["receipt_sha256"]:
            raise ContractError("Reference source receipt checksum mismatch")
        receipt = read_json(receipt_file)
        if (receipt.get("status") != "completed" or receipt.get("sha256") != node["sha256"] or
                receipt.get("dataset_id") != node["dataset_id"] or
                receipt.get("release_id") != node["release_id"] or
                receipt.get("bytes") != path.stat().st_size or
                safe_child(Path(graph.snapshot.raw_root), receipt.get("relative_path", "")) != path or
                receipt.get("url") != node["source_url"]):
            raise ContractError("Reference source receipt identity mismatch")
        if node["availability"]["basis"] == "public_download_receipt":
            observed = decode(datetime, receipt.get("completed_at_utc"))
            available = decode(datetime, node["availability"]["known_public_by"])
            if available < observed or node["availability"]["evidence_ref"] != node["receipt_sha256"]:
                raise ContractError("Reference source public-availability proof mismatch")
        proofs[key] = {"source_id": key, "path": node["path"], "sha256": node["sha256"],
            "raw_root": graph.snapshot.raw_root,
            "source_url": node["source_url"], "dataset_id": node["dataset_id"], "release_id": node["release_id"],
            "receipt_path": receipt_path, "receipt_sha256": node["receipt_sha256"]}
    return path


def _mappings(audit, folder, case, snapshot, definition, graph, proofs):
    recorded = read_json(folder / "identifier-validation.json")
    nodes = {node["source_id"]: node for node in snapshot["sources"]}
    values, refs = {}, []
    for kind in ("target", "disease"):
        expected, locator = recorded[kind]
        source = nodes.get(locator.get("source_id"))
        if source is None or source["dataset_id"] != "ot_" + kind or source["release_id"] != "25.09":
            raise ContractError("Reference mapping uses an incorrect source product")
        _source(audit, graph, source, proofs)
        actual = audit.parquet_row(source, snapshot["raw_root"], locator, tuple(expected))
        if actual != expected:
            raise ContractError("Reference mapping differs from its original source row")
        values[kind] = actual
        refs.append(source["source_id"])
        if case["hypothesis"][kind + "_namespace_version" if kind == "target" else "indication_namespace_version"] != (
                "OpenTargets-25.09:" + kind + ":" + source["sha256"]):
            raise ContractError("Reference hypothesis namespace version differs from mapping source")
    expected, locator = recorded["hgnc"]
    source = nodes.get(locator.get("source_id"))
    if (source is None or source["dataset_id"] != "hgnc_symbols" or
            source["release_id"] != "snapshot_2026-10-10" or type(locator.get("row")) is not int or locator["row"] < 0):
        raise ContractError("Reference HGNC mapping locator or version is invalid")
    path = _source(audit, graph, source, proofs)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        actual = next((row for number, row in enumerate(csv.DictReader(stream, delimiter="\t"))
                       if number == locator["row"]), None)
    if (actual != expected or actual["status"] != "Approved" or actual["symbol"] != definition.symbol or
            actual["ensembl_gene_id"] != case["hypothesis"]["target_id"] or
            values["target"]["id"] != actual["ensembl_gene_id"] or
            values["target"]["approvedSymbol"] != definition.symbol or
            values["disease"]["id"] != definition.disease_id or recorded["symbol"] != definition.symbol or
            definition.target_id is not None and definition.target_id != actual["ensembl_gene_id"] or
            definition.hgnc_id is not None and definition.hgnc_id != actual["hgnc_id"]):
        raise ContractError("Reference canonical HGNC/Ensembl/disease identities disagree")
    refs.append(source["source_id"])
    if graph.exclusion(tuple(refs), decode(Case, case)):
        raise ContractError("Reference mapping has ineligible information lineage")
    return nodes, tuple(sorted(refs)), values["disease"]["name"]


def audit_observation(audit, observation, *, case, nodes, graph, mapping_refs, symbol,
                      disease_name, proofs):
    """Check one whole normalized observation against the physically located raw row."""
    locator = observation["source_locator"]
    _physical_key(observation)
    node = nodes.get(locator["source_id"])
    if node is None or node["dataset_id"] != "ot_evidence" or node["release_id"] != "25.09":
        raise ContractError("Reference evidence uses an incorrect raw source product")
    _source(audit, graph, node, proofs)
    if (observation["method"]["code_id"] != "tether.opentargets.normalize" or
            observation["method"]["version"] != NORMALIZATION_VERSION or
            observation["method"]["qc_status"] != "passed" or observation["computed_at"] is not None or
            observation["availability"] != node["availability"]):
        raise ContractError("Reference normalization method or availability differs from the admitted source")
    projection = observation["method"]["parameters"].get("projection")
    if (not isinstance(projection, list) or not projection or
            any(not isinstance(field, str) for field in projection) or len(set(projection)) != len(projection) or
            FORBIDDEN.intersection(projection)):
        raise ContractError("Reference raw projection is missing, duplicated or contains clinical fields")
    import pyarrow.parquet as pq
    original_columns = pq.ParquetFile(audit.source(node, graph.snapshot.raw_root)).schema_arrow.names
    if projection != [field for field in EVIDENCE_COLUMNS if field in original_columns]:
        raise ContractError("Reference projection differs from the complete explicit normalization recipe")
    row = audit.parquet_row(node, graph.snapshot.raw_root, locator,
                            tuple(dict.fromkeys((*projection, *CONTEXT_FIELDS))))
    if set(projection) - row.keys():
        raise ContractError("Reference raw row lacks a projected field")
    projected = {key: row[key] for key in projection}
    digest = fingerprint(projected)
    if digest != observation["method"]["parameters"].get("source_row_sha256"):
        raise ContractError("Reference source-row projection fingerprint mismatch")
    hypothesis = case.hypothesis
    if (row.get("id") != locator.get("evidence_id") or row.get("datasourceId") != locator.get("datasource_id") or
            row.get("targetId") != hypothesis.target_id or row.get("diseaseId") != hypothesis.indication_id or
            observation["target_id"] != hypothesis.target_id or observation["indication_id"] != hypothesis.indication_id or
            observation["observation_id"] != f"ot25:{row['datasourceId']}:{row['id']}"):
        raise ContractError("Reference evidence identity or case scope differs from original row")
    if row["datasourceId"] == "chembl" or row["datatypeId"] not in CATEGORIES:
        raise ContractError("Excluded or unsupported evidence entered reference selection")
    if observation["category"] != CATEGORIES[row["datatypeId"]]:
        raise ContractError("Reference evidence datatype/category mismatch")
    expected_statement = (f"Open Targets 25.09 record {row['id']} from {row['datasourceId']} links {symbol} "
        f"({row['targetId']}) to {disease_name} ({row['diseaseId']}); datatype {row['datatypeId']}; "
        f"provider evidence score {row.get('score')}. This is a resource annotation.")
    if observation["statement"] != expected_statement:
        raise ContractError("Reference statement differs from original source annotation")
    expected_metrics = {key: value for key, value in projected.items() if key not in IDENTITY_FIELDS}
    if observation["source_metrics"] != expected_metrics or FORBIDDEN.intersection(observation["source_metrics"]):
        raise ContractError("Reference scientific metrics differ from original row or contain clinical fields")
    for field in CONTEXT_FIELDS:
        if row.get(field) not in (None, [], "") and observation["source_metrics"].get(field) != row[field]:
            raise ContractError("Reference normalization dropped reported source context: " + field)
    context = observation["context"]
    if any(context[field] is not None for field in ("species", "tissue", "disease_state", "intervention", "comparator")):
        raise ContractError("Reference source context acquired inferred biological values")
    if (observation["features"] or observation["feature_scope"] is not None or observation["program_id"] is not None or
            any(value is not None for value in observation["quantitative"].values()) or
            observation["mechanism_direction"] != "uncertain" or observation["polarity"] != "uncertain" or
            observation["status"] != "observed" or observation["method"]["parameters"].get("scientific_validation") != "not_run"):
        raise ContractError("Reference source annotation became an interpreted numerical or causal result")
    study, cohort = row.get("studyId"), row.get("cohortId")
    study = str(study) if study is not None else None
    cohort = str(cohort) if cohort is not None else None
    source = str(row["datasourceId"])
    ancestry = row.get("ancestry") if isinstance(row.get("ancestry"), str) and row.get("ancestry") else None
    dependency = source + ":cohort:" + cohort if cohort else source + ":study:" + study if study else None
    if (observation["study_id"] != (source + ":" + study if study else None) or
            observation["dependency_group"] != dependency or context["ancestry"] != ancestry or
            context["cohort_ids"] != ([source + ":" + cohort] if cohort else [])):
        raise ContractError("Reference study, cohort or ancestry differs from the source")
    published, year, date_unknown, reason = _publication(row, case.cutoff)
    if reason or observation["publication_date"] != (published.isoformat() if published else None) or observation["publication_year"] != year:
        raise ContractError("Reference publication metadata is ineligible or inconsistent")
    expected_missing = {"species": "not_verified_from_source_model_context", "effect_scale": "unverified_source_scale",
        "scientific_interpretation": "unreviewed", "tissue": "not_canonically_resolved_from_source_context"}
    for field, raw_name in (("study_id", "studyId"), ("cohort", "cohortId")):
        if not row.get(raw_name):
            expected_missing[field] = "not_supplied_by_source"
    if ancestry is None:
        expected_missing["ancestry"] = "not_supplied_by_source" if not row.get("ancestry") else "unresolved_provider_value"
    expected_missing.update(date_unknown)
    if observation["missingness"] != expected_missing:
        raise ContractError("Reference missingness differs from source-supported unknowns")
    expected_refs = tuple(sorted(set(mapping_refs) | {node["source_id"]}))
    if tuple(observation["input_refs"]) != expected_refs or graph.exclusion(expected_refs, case):
        raise ContractError("Reference input lineage is unscoped or ineligible")
    return {"case_id": case.case_id, "observation_id": observation["observation_id"],
        "physical_locator": locator, "source": proofs[node["source_id"]],
        "projection": projection, "projected_original_row": projected, "source_row_sha256": digest,
        "preserved_context": {field: row[field] for field in CONTEXT_FIELDS if row.get(field) not in (None, [], "")},
        "missingness": observation["missingness"], "technical_result": "passed",
        "scientific_adjudication": "not_run", "therapeutic_relevance": "not_assessed"}


def build_reference_packets(bundle: Path, output: Path, *, case_pack: Path, catalog_path: Path,
                            case_pack_sha256=CASE_PACK_SHA256, maximum=5, seed=SEED,
                            build_report_sha256=None):
    """New output only; any failed attempt retains a durable journal and failure."""
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    case_pack, catalog_path = Path(case_pack).resolve(), Path(catalog_path).resolve()
    journal = RunJournal(output, kind="build")
    started = time.monotonic()
    stage, results, audits, proofs = "configuration", [], [], {}
    try:
        journal.append("reference_request", bundle=str(bundle), case_pack=str(case_pack),
            case_pack_sha256=case_pack_sha256, catalog_path=str(catalog_path), maximum=maximum, seed=seed,
            build_report_sha256=build_report_sha256)
        if case_pack_sha256 != CASE_PACK_SHA256:
            raise ContractError("This reference protocol requires the frozen science2 case-pack SHA-256")
        if type(maximum) is not int or not 1 <= maximum <= 5 or seed != SEED:
            raise ContractError("Reference protocol requires the fixed seed and a selection limit from one to five")
        stage = "build_validation"
        definitions, pack_bytes, digest = _load_case_pack(case_pack, case_pack_sha256)
        build_path = bundle / "build-report.json"
        build_hash, build = sha256_file(build_path), read_json(build_path)
        if build_report_sha256 is not None and build_hash != build_report_sha256:
            raise ContractError("Reference build report differs from its externally supplied SHA-256 anchor")
        if (build.get("status") != "built" or build.get("blocked_cases") or
                build.get("case_pack", {}).get("sha256") != digest or
                sha256_file(bundle / "case-pack.json") != digest or
                build.get("normalization_recipe", {}).get("case_pack") != build.get("case_pack")):
            raise ContractError("Reference preparation requires the completed frozen custom case build")
        if sha256_file(catalog_path) != build["inspection"]["catalog_sha256"]:
            raise ContractError("Reference audit catalog differs from build admission policy")
        policy = catalog_index(read_json(catalog_path))
        expected = {definition.case_id: definition for definition in definitions}
        summaries = build["cases"]
        if len(summaries) != len(expected) or {row["case_id"] for row in summaries} != set(expected):
            raise ContractError("Reference build case set differs from the frozen pack")
        (output / "case-pack.json").write_bytes(pack_bytes)
        audit = SourceAudit()
        input_hashes = {build_path: build_hash, bundle / "case-pack.json": digest, case_pack: digest,
                        catalog_path: build["inspection"]["catalog_sha256"]}
        for summary in summaries:
            stage = "case_validation"
            case_id = summary["case_id"]
            folder = safe_child(bundle, case_id)
            raw_case, raw_snapshot = read_json(folder / "case.json"), read_json(folder / "snapshot.json")
            for name in ("case.json", "snapshot.json", "identifier-validation.json"):
                input_hashes[folder / name] = sha256_file(folder / name)
            case, snapshot = decode(Case, raw_case), decode(Snapshot, raw_snapshot)
            case.validate()
            definition = expected[case_id]
            hypothesis = case.hypothesis
            if (case.task != "T6" or case.program is not None or case.endpoint is not None or
                    snapshot.profile != Profile.CONTEMPORARY or case.case_id != case_id or
                    snapshot.origin_at != case.origin_at or
                    (hypothesis.indication_id, hypothesis.intended_action, hypothesis.modality, hypothesis.tissue) !=
                    (definition.disease_id, definition.intended_action, definition.modality, definition.tissue) or
                    summary["hypothesis_key"] != hypothesis.key or
                    raw_snapshot["coverage"].get("case_pack") != build["case_pack"]):
                raise ContractError("Reference case hypothesis or profile differs from its frozen scope")
            graph = InputGraph(snapshot, folder, policy)
            nodes, mapping_refs, disease_name = _mappings(audit, folder, raw_case, raw_snapshot,
                                                         definition, graph, proofs)
            stage = "artifact_validation"
            if len(summary["packets"]) != len(snapshot.artifacts):
                raise ContractError("Reference artifact count differs from build packet inventory")
            observations, packet_proofs, counts = [], [], Counter()
            for record, artifact in zip(summary["packets"], snapshot.artifacts):
                path = safe_child(folder, artifact.path)
                if (artifact.path != record["path"] or artifact.sha256 != record["sha256"] or
                        sha256_file(path) != artifact.sha256 or path.stat().st_size != record["bytes"] or
                        artifact.role != "agent_evidence" or artifact.dataset_id != "tether_normalized_packets" or
                        not artifact.access_approved or artifact.availability.exclusion(case.cutoff) or
                        graph.exclusion(artifact.input_refs, case)):
                    raise ContractError("Reference artifact integrity, role or lineage mismatch")
                packet = read_json(path)
                if packet.get("schema_version") != 2 or len(packet.get("observations", [])) != record["observations"]:
                    raise ContractError("Reference evidence packet count or contract mismatch")
                for observation in packet["observations"]:
                    normalized = decode(Observation, observation)
                    validate_observation(normalized)
                    if (normalized.target_id != hypothesis.target_id or normalized.indication_id != hypothesis.indication_id or
                            normalized.features or normalized.feature_scope is not None or normalized.program_id is not None or
                            not set(mapping_refs).issubset(normalized.input_refs) or
                            not set(normalized.input_refs).issubset(artifact.input_refs) or
                            graph.exclusion(normalized.input_refs, case)):
                        raise ContractError("Reference packet contains unscoped or interpreted evidence")
                    counts[normalized.category.value] += 1
                    observations.append(observation)
                packet_proofs.append({"path": artifact.path, "sha256": artifact.sha256,
                                      "bytes": record["bytes"], "observations": record["observations"]})
                input_hashes[path] = artifact.sha256
            if len(observations) != summary["observations"] or len(observations) != raw_snapshot["coverage"]["matching_observations"]:
                raise ContractError("Reference selected-subset coverage count mismatch")
            selected = select_observations(observations, case_id, maximum=maximum, seed=seed)
            stage = "original_row_audit"
            selected_audits = [audit_observation(audit, observation, case=case, nodes=nodes, graph=graph,
                mapping_refs=mapping_refs, symbol=definition.symbol, disease_name=disease_name, proofs=proofs)
                for observation in selected]
            destination = safe_child(output, case_id)
            destination.mkdir()
            write_json(destination / "source-packet.json", {"schema_version": 2, "observations": selected})
            write_json(destination / "raw-row-audit.json", selected_audits)
            reference = {"schema_version": 1, "role": "evaluation_only", "case": raw_case,
                "source_coverage": raw_snapshot["coverage"], "selected_observations": len(selected),
                "available_observations": len(observations), "available_categories": dict(counts),
                "selected_categories": dict(Counter(row["category"] for row in selected)),
                "zero_evidence": not observations, "absence_claim": False,
                "selection": {"seed": seed, "maximum": maximum,
                    "policy": "greedy_new_category_provider_known_study_then_identity_hash", "provider_score_ranking": False},
                "original_packets": packet_proofs, "case_sha256": sha256_file(folder / "case.json"),
                "snapshot_sha256": sha256_file(folder / "snapshot.json"),
                "source_packet_sha256": sha256_file(destination / "source-packet.json"),
                "raw_row_audit_sha256": sha256_file(destination / "raw-row-audit.json"),
                "scientific_reference_answers": "not_created", "scientific_validation": "not_established"}
            write_json(destination / "reference-context.json", reference)
            results.append({"case_id": case_id, "selected_observations": len(selected),
                "zero_evidence": not observations, "reference_context_sha256": sha256_file(destination / "reference-context.json")})
            audits.extend(selected_audits)
            journal.append("reference_case_completed", **results[-1], elapsed_seconds=time.monotonic() - started)
        stage = "source_recheck"
        for path, expected_hash in input_hashes.items():
            if sha256_file(path) != expected_hash:
                raise ContractError("Reference input changed during preparation: " + str(path))
        for proof in proofs.values():
            audit.source(proof, proof["raw_root"])
            if sha256_file(safe_child(Path(proof["raw_root"]), proof["receipt_path"])) != proof["receipt_sha256"]:
                raise ContractError("Reference archived receipt changed during preparation")
        stage = "report_finalization"
        report = {"schema_version": 1, "role": "evaluation_only", "status": "completed",
            "created_at_utc": datetime.now(timezone.utc), "bundle": str(bundle), "build_report_sha256": build_hash,
            "case_pack_sha256": digest, "catalog_sha256": build["inspection"]["catalog_sha256"],
            "code_sha256": sha256_file(Path(__file__)), "seed": seed, "maximum_per_case": maximum,
            "cases": results, "audited_rows": len(audits),
            "distinct_physical_rows": len({tuple(row["physical_locator"][key] for key in ("source_id", "row_group", "row")) for row in audits}),
            "source_proofs": sorted(proofs.values(), key=lambda row: row["source_id"]),
            "elapsed_seconds": time.monotonic() - started, "peak_memory_bytes": peak_memory_bytes(),
            "provider_spend_usd": 0, "scientific_validation": "not_established", "absence_claim": False,
            "limitations": ["Only selected original rows were independently audited; all packet byte hashes and case scopes were checked",
                "Selection is deterministic development sampling, not a representative biological validation set",
                "Source annotations and unknowns are preserved; no therapeutic reference answers or predictions are produced"]}
        write_json(output / "reference-report.json", report)
        journal.append("reference_completed", report_sha256=sha256_file(output / "reference-report.json"), cases=len(results), audited_rows=len(audits))
        return report
    except BaseException as error:
        try:
            journal.fail(error, stage)
        except OSError:
            pass
        try:
            write_json(output / "reference-failure.json", {"schema_version": 1, "status": "interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                "stage": stage, "error_class": type(error).__name__, "message": str(error),
                "completed_cases": results, "recovery": "inspect only; do not resume or overwrite this output"})
        except OSError:
            pass
        raise
    finally:
        journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--case-pack", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--case-pack-sha256", default=CASE_PACK_SHA256)
    parser.add_argument("--max-per-case", type=int, default=5)
    parser.add_argument("--build-report-sha256")
    args = parser.parse_args(argv)
    report = build_reference_packets(args.bundle, args.output, case_pack=args.case_pack, catalog_path=args.catalog,
        case_pack_sha256=args.case_pack_sha256, maximum=args.max_per_case,
        build_report_sha256=args.build_report_sha256)
    print({"status": report["status"], "cases": len(report["cases"]), "audited_rows": report["audited_rows"]})


if __name__ == "__main__":
    main()
