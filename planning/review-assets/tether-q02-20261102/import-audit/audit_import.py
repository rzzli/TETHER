"""Independent finite metadata audit; no raw provider/clinical payload reads."""
import collections
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
IMPORTED = ROOT / "data/derived/catalog-policy-v2-20261102T084315Z"
FRAME = ROOT / "data/derived/literature-coverage-20261017T082208Z"
EXPECTED_POLICY = "8e6709135e25924f576e33315ff2f36f1cc9745892c5018bbc9a0b382a79ed94"
EXPECTED_CATALOG = "eafd955cad30dd36bd7417de165a508b1e891f90f42e2cc4bcb573043eaa65ac"
EXPECTED_FRAME = "755f3ec861e3283ea6e04bd802fdc39d1e810cdf70556ac30718f796915f4115"
IDENTITY = ("dataset_id", "release_id", "root_alias", "relative_path", "sha256", "bytes")
CHECKS = collections.Counter()
HASHED = {}


def need(value, kind):
    if not value:
        raise AssertionError(kind)
    CHECKS[kind] += 1


def read(path):
    path = Path(path)
    need(path.suffix == ".json" and path.stat().st_size <= 16 * 1024 * 1024, "bounded_json_only")
    raw = path.read_bytes()
    HASHED[str(path)] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    return json.loads(raw.decode("utf-8-sig")), raw


def canon(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fp(value):
    return hashlib.sha256(canon(value)).hexdigest()


def main():
    policy, policy_bytes = read(IMPORTED / "policy.json")
    report, _ = read(IMPORTED / "report.json")
    envelope, _ = read(IMPORTED / "roots.json")
    source, source_bytes = read(ROOT / "data/catalog/sources.json")
    build, build_bytes = read(FRAME / "build-report.json")
    roots = envelope["roots"]
    need(hashlib.sha256(policy_bytes).hexdigest() == EXPECTED_POLICY == report["policy_sha256"], "external_policy_hash")
    need(hashlib.sha256(source_bytes).hexdigest() == EXPECTED_CATALOG == policy["source_catalog"]["sha256"], "source_catalog_hash")
    need(hashlib.sha256(build_bytes).hexdigest() == EXPECTED_FRAME, "external_frame_hash")
    need(envelope["schema_version"] == 1 and Path(roots["metadata"]) == ROOT, "roots_envelope")
    raw_root = Path(roots["external_data"])
    need(raw_root == Path(r"E:\projects_data\drug_target_agents_data"), "explicit_external_root")
    need(len(policy["products"]) == len(source["datasets"]) == 178, "all_178_products")
    need(policy["catalog_metadata"] == {k:v for k,v in source.items() if k != "datasets"}, "catalog_metadata_preserved")
    need(policy["source_catalog"]["document_fingerprint"] == fp(source), "catalog_document_fingerprint")
    products = {r["dataset_id"]:r for r in policy["products"]}
    for row in source["datasets"]:
        need(products[row["dataset_id"]]["metadata"] == row, "original_product_exact")
    genetic = products["genetics_results"]
    need(genetic["validation_dependencies"] == ["genetics_qc_cases"] and
         genetic["input_dependencies"] == ["assay_gene_map", "gwas_study_metadata"], "genetics_classification")
    need(products["scorer_artifacts"]["input_dependencies"] == products["scorer_artifacts"]["metadata"]["dependencies"],
         "genuine_training_ancestry_retained")
    records = {r["artifact_id"]:r for r in policy["artifacts"]}
    need(len(records) == len(policy["artifacts"]) == 266, "artifact_unique_count")
    for key, record in records.items():
        need(key == "artifact-" + fp({name:record[name] for name in IDENTITY}), "derived_artifact_identity")
        need(record["scientific_validation"] == "not_established", "science_not_promoted")
    allowed = [u for u in policy["uses"] if u["status"] == "allowed"]
    blocked = [u for u in policy["uses"] if u["status"] == "blocked"]
    need(len(allowed) == 10 and len(blocked) == 7 and len({u["use_id"] for u in policy["uses"]}) == 17, "use_counts")
    uses = {u["use_id"]:u for u in allowed}
    observed_raw, observed_packets = set(), set()
    occurrences = 0
    paths = {(r["root_alias"], r["relative_path"], r["dataset_id"], r["release_id"], r["sha256"]):r for r in records.values()}
    need(len(paths) == len(records), "no_ambiguous_artifact_paths")
    for frame_case in build["cases"]:
        folder = FRAME / frame_case["case_id"]
        case, _ = read(folder / "case.json")
        snapshot, _ = read(folder / "snapshot.json")
        use = uses["canonical-ten-" + frame_case["case_id"]]
        need(Path(roots[use["snapshot_root_alias"]]) == folder, "snapshot_root_exact")
        need(case["case_id"] == frame_case["case_id"] and snapshot["snapshot_id"] == build["snapshot_id"] + ":" + case["case_id"],
             "canonical_case_identity")
        hypothesis = {k:case["hypothesis"][k] for k in ("target_id","indication_id","target_namespace_version",
                     "indication_namespace_version","intended_action","modality","tissue")}
        need(fp(hypothesis) == frame_case["hypothesis_key"], "hypothesis_matches_pinned_frame")
        need(use["case_fingerprint"] == fp(case) and use["snapshot_fingerprint"] == fp(snapshot), "case_snapshot_fingerprints")
        need(use["frame_sha256"] == EXPECTED_FRAME, "use_external_frame_anchor")
        need(use["origin_at"] == case["origin_at"] == snapshot["origin_at"] == build["origin_at_utc"], "unchanged_contemporary_origin")
        need(use["profile"] == snapshot["profile"] == "contemporary_assessment", "unchanged_profile")
        need(len(snapshot["sources"]) == frame_case["input_sources"], "source_inventory_complete")
        expected_packets = {p["path"]:p for p in frame_case["packets"]}
        need({p["path"] for p in snapshot["artifacts"]} == set(expected_packets) and len(snapshot["artifacts"]) == len(expected_packets),
             "complete_packet_set_including_shards")
        grants = {g["artifact_id"]:g["role"] for g in use["grants"]}
        node_ids, expected_grants = {}, {}
        for node in snapshot["sources"]:
            occurrences += 1
            need(node.get("computed_at") is None and node["parents"] == [], "raw_source_only")
            record = paths[(use["raw_root_alias"],node["path"],node["dataset_id"],node["release_id"],node["sha256"])]
            observed_raw.add(record["artifact_id"]); node_ids[node["source_id"]] = record["artifact_id"]
            expected_grants[record["artifact_id"]] = node["role"]
            need(record["availability"] == node["availability"] and record["temporal_classification"] == node["temporal_classification"], "source_context_preserved")
            need(record["parents"] == [] and record["kind"] == "raw", "source_kind_parents")
            receipt_ref = record["provenance"]["receipt"]
            need(receipt_ref["relative_path"] == node["receipt_path"] and receipt_ref["sha256"] == node["receipt_sha256"], "node_receipt_binding")
            # Only immutable small receipt JSON, never its referenced payload.
            receipt_path = raw_root / receipt_ref["relative_path"]
            need(receipt_path.parent == raw_root / "manifests/receipt-archive", "immutable_receipt_location")
            receipt, raw = read(receipt_path)
            need(hashlib.sha256(raw).hexdigest() == receipt_ref["sha256"], "fresh_receipt_hash")
            need(all(receipt[k] == record[k] for k in ("dataset_id","release_id","sha256","bytes")), "receipt_artifact_identity")
            need(receipt["relative_path"].replace("\\","/") == record["relative_path"] and
                 receipt["url"] == node["source_url"] == record["source_url"] == receipt_ref["url"] and
                 receipt["receipt_id"] == receipt_ref["receipt_id"] and receipt["status"] == "completed", "receipt_identity_exact")
            need("evaluation_only" not in products[node["dataset_id"]]["metadata"]["roles"] and
                 node["role"] in products[node["dataset_id"]]["metadata"]["roles"], "input_role_allowed")
        for packet in snapshot["artifacts"]:
            record = paths[(use["snapshot_root_alias"],packet["path"],packet["dataset_id"],packet["release_id"],packet["sha256"])]
            expected_grants[record["artifact_id"]] = packet["role"]; observed_packets.add(record["artifact_id"])
            need(record["kind"] == "packet" and packet["role"] == "agent_evidence" and packet["access_approved"] is True, "packet_role")
            need(record["sha256"] == expected_packets[packet["path"]]["sha256"] and
                 record["bytes"] == expected_packets[packet["path"]]["bytes"], "packet_identity_matches_frame")
            need(set(record["parents"]) == {node_ids[p] for p in packet["input_refs"]}, "exact_actual_packet_parent_edges")
        need(grants == expected_grants and len(use["grants"]) == len(expected_grants), "all_nodes_and_grants_exact")
    need(occurrences == 920 and len(observed_raw) == 248 and len(observed_packets) == 11, "distinct_lineage_vs_occurrences")
    need(build["inspection"]["selected_files"] == 2206 and build["inspection"]["selected_bytes"] == 9038960079
         and build["inspection"]["missing_inputs"] == [], "broader_inspection_scope")
    expected_dates = {"2023-01-01","2023-07-02","2024-01-01","2024-07-01","2025-01-01","2026-01-01","2026-04-01"}
    aact = [r for r in records.values() if r["dataset_id"] == "aact_snapshots"]
    need({r["release_id"] for r in aact} == expected_dates and len(aact) == 7, "seven_exact_aact_dates")
    public = ROOT / "data/manifests/public"
    origin, _ = read(public / "2026-10-16-aact-restoration.json")
    followup, _ = read(public / "2026-10-16-aact-followup.json")
    intermediate, _ = read(public / "2026-10-17-aact-intermediate-restorations.json")
    endpoint, _ = read(public / "2026-10-18-aact-endpoint-technical.json")
    ascertainment, _ = read(public / "2026-10-18-aact-ascertainment-technical.json")
    expected_aact = {"2023-01-01": (origin["input"]["sha256"], origin["input"]["bytes"], origin["input"]["path"]),
                     "2025-01-01": (followup["archive"]["sha256"], followup["archive"]["bytes"], followup["archive"]["archive"])}
    archive_locations = {}
    for item in report["metadata"]:
        if item["root_alias"] == "external_data" and item["relative_path"].endswith("/archive-inspection.json"):
            inspection, _ = read(raw_root / item["relative_path"])
            need(inspection["status"] == "archive_integrity_passed", "aact_retained_integrity_status")
            archive_locations[inspection["archive_sha256"]] = (inspection["archive_bytes"], inspection["archive"])
    for r in intermediate["snapshots"]:
        size, location = archive_locations[r["archive_sha256"]]
        need(size == r["archive_bytes"], "aact_intermediate_reports_agree")
        expected_aact[r["actual_dump_date"]] = (r["archive_sha256"], size, location)
    for date, neutral in (("2026-01-01",endpoint),("2026-04-01",ascertainment)):
        size, location = archive_locations[neutral["source_archive_sha256"]]
        need(size == neutral["source_archive_bytes"] and neutral["role"] == "evaluation_only"
             and neutral["public_availability_at"] is None, "aact_evaluator_reports_agree")
        expected_aact[date] = (neutral["source_archive_sha256"], size, location)
    for record in aact:
        use = next(u for u in blocked if any(g["artifact_id"] == record["artifact_id"] for g in u["grants"]))
        need(use["blockers"] and use["frame_sha256"] is None and use["case_fingerprint"] is None and
             use["snapshot_fingerprint"] is None, "aact_qualified_binding_absent_blocked")
        need(record["source_url"] is None and record["availability"] is None and record["temporal_classification"] == "unverified"
             and record["provenance"]["kind"] == "manual_archive" and record["provenance"]["receipt"] is None, "aact_unknowns_not_invented")
        need(not any(record["artifact_id"] in {g["artifact_id"] for g in u["grants"]} for u in allowed), "aact_not_inference_input")
        expected_sha, expected_bytes, expected_location = expected_aact[record["release_id"]]
        need(record["sha256"] == expected_sha and record["bytes"] == expected_bytes and
             raw_root / record["relative_path"] == Path(expected_location), "aact_identity_matches_independent_neutral_reports")
    metadata_roots = {"project":ROOT,"external_data":raw_root}
    for item in report["metadata"]:
        original = metadata_roots[item["root_alias"]] / item["relative_path"]
        if item["root_alias"] == "external_data":
            need(original.parent == raw_root / "manifests/receipt-archive" or original.name == "archive-inspection.json", "neutral_external_metadata_only")
        _, original_bytes = read(original)
        _, copied_bytes = read(ROOT / item["archived_copy"])
        need(copied_bytes == original_bytes and len(copied_bytes) == item["bytes"] and hashlib.sha256(copied_bytes).hexdigest() == item["sha256"], "metadata_copy_exact")
    for record in records.values():
        for proof in record["provenance"]["evidence"]:
            _, content = read(ROOT / proof["path"])
            need(hashlib.sha256(content).hexdigest() == proof["sha256"], "artifact_provenance_copy_hash")
    need(report["collection_status_promotions"] == 0 and report["scientific_validation"] == "not_established", "no_report_promotion")
    result = dict(schema_version=1, status="PASS", created_at_utc=datetime.now(timezone.utc).isoformat(),
                  imported_path=IMPORTED.relative_to(ROOT).as_posix(), policy_sha256=EXPECTED_POLICY,
                  source_catalog_sha256=EXPECTED_CATALOG, frame_sha256=EXPECTED_FRAME,
                  assertions=sum(CHECKS.values()), assertions_by_property=dict(CHECKS),
                  products=178, artifacts=266, raw_lineage_artifacts=248, packet_artifacts=11, aact_artifacts=7,
                  source_node_occurrences=920, allowed_uses=10, blocked_uses=7,
                  raw_lineage_products=dict(collections.Counter(records[key]["dataset_id"] for key in observed_raw)),
                  metadata_originals_and_copies_checked=len(report["metadata"]), metadata_distinct_files_hashed=len(HASHED),
                  broader_build_inspection_files=2206, broader_build_inspection_bytes=9038960079,
                  source_payloads_opened_or_hashed=0, normalized_packet_payloads_opened_or_hashed=0,
                  clinical_outcome_or_expert_artifacts_opened=0, network_or_database_or_model_calls=0,
                  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  importer_code_sha256=hashlib.sha256((ROOT / "tools/data/build_tether_policy.py").read_bytes()).hexdigest(),
                  limitations=["Fresh checks cover metadata and immutable receipt bytes. Raw source payload checks remain inherited, not fresh.",
                               "Normalized packet identities checked against pinned frame and snapshots; packet bytes not rehashed by this independent metadata audit.",
                               "No queue-to-receipt acquisition promotion and no scientific/clinical qualification.",
                               "Exact code-path changes after import require separate qualification; this audit certifies retained artifact metadata consistency only."])
    path = Path(__file__).with_name("ACTUAL-IMPORT-AUDIT-v3.json")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2); handle.write("\n")
    print(json.dumps({key:result[key] for key in ("status","assertions","artifacts","metadata_originals_and_copies_checked")}))


if __name__ == "__main__":
    main()
