"""Bounded, exposed-development P03 replay of one previously fixed raw row.

Run ``prepare`` first. A separately authorized filesystem-only operation must
archive the inspected receipt under RAW_ROOT before ``replay PRIVATE_DIR``.
This script never downloads, scans a partition, generates or scores a response.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from asof.contracts import Snapshot, SourceNode  # noqa: E402
from asof.provenance import catalog_index  # noqa: E402
from asof.serde import canonical, decode, encode, fingerprint, parse_json  # noqa: E402
from asof.study.source_fact_sources import compile_reference, validate_task, verify_reference  # noqa: E402
from asof.study.source_rows import parquet_row  # noqa: E402
from asof.study.stable_read import checked_path, hash_file, read_file, stable_files  # noqa: E402


RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")
REPORT = "planning/review-assets/preprint-p02-20261031/GWAS-SCAN-REPORT-v1.json"
MANIFEST = "data/benchmark/gold_evidence/preprint-p02-gwas-20261101T025951484714Z/gwas-availability.json"
CATALOG = "data/catalog/sources.json"
PINS = {
    REPORT: (40651, "aea3bd23443ace6305016dbfcb86a8cead068018a9ad159460f92eb1090740b3"),
    MANIFEST: (325832, "b700a763613927e808b475243c0c94c09d4f29a15204f543183496fbec434a99"),
    CATALOG: (1222375, "cac453e30dd3f21c9684ef2e84132fd3ab373949501ca349619567c8c6f345fb"),
    "src/asof/study/source_fact_sources.py": (None, "18d059744b39390a12f84d4cf1b92fee00f86438b4a7574ec2cd202c9ab76ec8"),
}
SOURCE_ID = "raw-b7a0617719960624a653c097"
ORIGINAL = "raw/open_targets_platform/25.09/output/evidence/sourceId=gwas_credible_sets/part-00009-910bad14-9254-465e-a5e6-bca5fd902d82.c000.snappy.parquet"
ORIGINAL_SHA = "44727015a4a3fd5d894bb877a6a3924c16c790366f66bed2ac5f71e84eed877e"
RECEIPT_SHA = "40e35071484945484202e30821854237f2a9008a59b04b65f9aba93ad8157f5c"
TRANSPORT_RECEIPT = f"manifests/receipt-archive/{RECEIPT_SHA}.json"
ARCHIVED_RECEIPT = f"manifests/receipt_archive/preprint-p03/{RECEIPT_SHA}.json"
LOCATOR = {"format": "parquet", "row_group": 0, "row": 14254}
RECORD_ID = "cd8e86b25a0ff5a2914b6ce405c2ddd669d4b110"
KEY = "ctla4-crohn-original-0"
SUMMARY = ROOT / "planning/review-assets/preprint-p03-20261031/ACTUAL-SOURCE-REPLAY-v1.json"
PRIVATE_PARENT = ROOT / "data/benchmark/gold_evidence"


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def create(path, payload):
    """Never replace an already retained artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def save(path, value):
    create(path, canonical(value))


def pinned(relative, deadline):
    size, expected = PINS[relative]
    path = checked_path(ROOT, relative)
    with stable_files([path], deadline=deadline):
        payload = read_file(path, deadline, size if size is not None else 1024 * 1024)
    need((size is None or len(payload) == size) and digest(payload) == expected,
         "Pinned input is unavailable or changed: " + relative)
    return payload


def reporting_task(cutoff):
    groups = (
        ("identity_linkage", "source_ids", ("id", "targetId", "diseaseId", "datasourceId", "datatypeId")),
        ("identity_linkage", "publication_ids", ("literature", "pmcIds")),
        ("identity_linkage", "study_ids", ("studyId", "studyLocusId")),
        ("reported_context", "reported_dates", ("publicationDate", "evidenceDate")),
        ("reported_measurement", "beta", ("beta",)),
        ("reported_measurement", "p_value", ("pValueMantissa", "pValueExponent")),
        ("reported_measurement", "standard_error", ("standardError",)),
    )
    return dict(
        schema_version=1, task_id="p03-actual-ctla4-crohn-selected-original-v1",
        scope=dict(target_id="ENSG00000163599", indication_id="EFO_0000384",
                   target_namespace_version="unknown upstream Ensembl version; native Open Targets 25.09 targetId",
                   indication_namespace_version="unknown upstream EFO version; native Open Targets 25.09 diseaseId",
                   action=None, modality=None, tissue=None),
        cutoff=cutoff, profile="contemporary_assessment", primary_families=["reported_measurement"],
        records=[dict(record_key=KEY, source_id=SOURCE_ID, locator=dict(LOCATOR),
                      identity=dict(id=RECORD_ID, targetId="ENSG00000163599", diseaseId="EFO_0000384"))],
        fields=[dict(record_key=KEY, field=name, family=family, group=f"{KEY}:{family}:{group}",
                     unit_field=None, empty_policy="unknown")
                for family, group, names in groups for name in names],
        joins=[], collection=dict(status="selected_records", reason=(
            "Exactly one previously fixed CTLA4/Crohn physical original row. No new search or full-release inventory; "
            "the earlier broad collection is not reverified. Native provider identifiers are not independently mapped.")),
    )


def prepare():
    started = time.perf_counter()
    cpu = time.process_time()
    # This exact cutoff precedes every original-source and transport-receipt read.
    cutoff = datetime.now(timezone.utc)
    deadline = time.monotonic() + 180
    report_bytes = pinned(REPORT, deadline)
    manifest_bytes = pinned(MANIFEST, deadline)
    catalog_bytes = pinned(CATALOG, deadline)
    pinned("src/asof/study/source_fact_sources.py", deadline)
    report = parse_json(report_bytes)
    manifest = parse_json(manifest_bytes)
    catalog = parse_json(catalog_bytes)
    need(report["manifest"]["path"].replace("\\", "/") == MANIFEST and
         report["manifest"]["sha256"] == PINS[MANIFEST][1], "Report/manifest pin differs")
    units = [unit for unit in manifest["units"] if unit["unit_id"] == "ctla4-efo_0000384"]
    need(len(units) == 1, "Exactly one fixed CTLA4 unit is required")
    unit = units[0]
    need(unit["target_id"] == "ENSG00000163599" and unit["disease_id"] == "EFO_0000384" and
         unit["selected_record_ids"] == [RECORD_ID] and len(unit["selected_records"]) == 1 and
         all(unit[name] is None for name in ("action", "modality", "tissue")), "Fixed reporting scope differs")
    # Deliberately do not access selected_records[*].record, selected_slots or baseline.
    locator = unit["selected_records"][0]["locator"]
    need(locator == dict(source_id=SOURCE_ID, row_group=0, row=14254), "Fixed physical locator differs")
    matches = [proof for proof in manifest["source_proofs"] if proof["source"]["source_id"] == SOURCE_ID]
    need(len(matches) == 1, "Fixed original source metadata is unavailable")
    proof = matches[0]
    source = proof["source"]
    need(source["path"] == ORIGINAL and source["sha256"] == ORIGINAL_SHA and
         source["receipt_path"] == TRANSPORT_RECEIPT and source["receipt_sha256"] == RECEIPT_SHA,
         "Pinned original or receipt identity differs")
    need(source["parents"] == [], "Additional source ancestors are unavailable within this fixed scope")
    need(source["computed_at"] is None and source["role"] == "agent_evidence" and
         source["dataset_id"] == "ot_evidence" and source["release_id"] == "25.09",
         "Source metadata is not the fixed raw original")
    index = catalog_index(catalog)
    need("agent_evidence" in index[source["dataset_id"]]["roles"] and
         "evaluation_only" not in index[source["dataset_id"]]["roles"], "Current catalog denies the original")
    original = checked_path(RAW_ROOT, ORIGINAL)
    receipt = checked_path(RAW_ROOT, TRANSPORT_RECEIPT)
    need(Path(proof["original"]["path"]) == original and Path(proof["receipt"]["path"]) == receipt,
         "Manifest absolute paths do not match the sole approved E originals")
    task = encode(validate_task(reporting_task(cutoff.isoformat())))
    with stable_files([original, receipt], deadline=deadline):
        original_hash = encode(hash_file(original, deadline))
        receipt_bytes = read_file(receipt, deadline, 841)
        need(original_hash == {"sha256": ORIGINAL_SHA, "bytes": 1816029} and
             len(receipt_bytes) == 841 and digest(receipt_bytes) == RECEIPT_SHA,
             "Original source/receipt byte proof differs")
        transport = parse_json(receipt_bytes)
        need(transport["status"] == "completed" and transport["sha256"] == ORIGINAL_SHA and
             transport["dataset_id"] == source["dataset_id"] and transport["release_id"] == source["release_id"] and
             Path(transport["relative_path"]) == Path(ORIGINAL) and transport["bytes"] == original_hash["bytes"] and
             transport["url"] == source["source_url"], "Inspected receipt identity differs")
        import pyarrow as pa
        import pyarrow.parquet as pq
        need(pa.__version__ == "21.0.0", "Arrow 21.0.0 is required")
        available = pq.ParquetFile(original).schema_arrow.names
        requested = {field["field"] for field in task["fields"]}
        selected = parquet_row(original, LOCATOR, tuple(name for name in available if name in requested),
                               deadline_check=lambda: need(time.monotonic() < deadline, "Preparation deadline expired"))
        need(all(selected.get(name) == expected for name, expected in task["records"][0]["identity"].items()),
             "Original physical row identity differs")
    stamp = cutoff.strftime("%Y%m%dT%H%M%S%fZ")
    private = PRIVATE_PARENT / ("preprint-p03-actual-" + stamp)
    private.mkdir(exist_ok=False)
    archived_source = dict(source, receipt_path=ARCHIVED_RECEIPT)
    node = decode(SourceNode, archived_source)
    snapshot = Snapshot(schema_version=2, snapshot_id="p03-actual-one-original-" + stamp,
                        profile=task["profile"], origin=cutoff.date(), allow_reconstructed=False,
                        artifacts=(), sources=(node,), raw_root=str(RAW_ROOT), origin_at=cutoff)
    save(private / "task.json", task)
    create(private / "task.sha256", (fingerprint(task) + "\n").encode("ascii"))
    save(private / "snapshot.json", encode(snapshot))
    create(private / "snapshot.sha256", (fingerprint(snapshot) + "\n").encode("ascii"))
    create(private / "catalog.json", catalog_bytes)
    create(private / "receipts" / (RECEIPT_SHA + ".json"), receipt_bytes)
    save(private / "independent-selected-original-projection.json", selected)
    save(private / "original-source-metadata.json", source)
    preparation = dict(
        schema_version=1, role="evaluation_only", agent_visible=False, exposure="exposed_development",
        cutoff=cutoff.isoformat(), cutoff_captured_before_original_read=True,
        pins={path: dict(bytes=size, sha256=sha) for path, (size, sha) in PINS.items()},
        original=proof["original"], transport_receipt=proof["receipt"],
        archive_receipt=dict(path=str(RAW_ROOT / ARCHIVED_RECEIPT), sha256=RECEIPT_SHA, bytes=841),
        script_sha256=digest(Path(__file__).read_bytes()),
        original_parent_refs_retained=source["parents"],
        namespace_version_policy="Upstream namespace versions unknown; provider-native IDs and export release only; no mapping claims",
        source_only_expected_facts=True,
        author_exposure="Prior manifest selected-record projection was inadvertently displayed during metadata inspection; no candidate/expert outputs read. No projected values are used by this script.",
        preparation_wall_seconds=time.perf_counter() - started, preparation_cpu_seconds=time.process_time() - cpu,
    )
    save(private / "preparation.json", preparation)
    print(json.dumps(dict(status="prepared_awaiting_authorized_receipt_archive", private_dir=str(private),
                          receipt_copy_source=str(private / "receipts" / (RECEIPT_SHA + ".json")),
                          receipt_copy_target=str(RAW_ROOT / ARCHIVED_RECEIPT), receipt_sha256=RECEIPT_SHA)))


def retained(private, name, expected=None):
    payload = (private / name).read_bytes()
    if expected is not None:
        need(digest(payload) == expected, "Retained file hash differs: " + name)
    return parse_json(payload)


def replay(private_arg):
    private = Path(private_arg).absolute()
    need(private.parent == PRIVATE_PARENT and private.name.startswith("preprint-p03-actual-"),
         "Replay directory is outside the one new private output namespace")
    need(not SUMMARY.exists(), "Sanitized replay report already exists; do not overwrite")
    started = time.perf_counter()
    cpu = time.process_time()
    deadline = time.monotonic() + 180
    for relative in PINS:
        pinned(relative, deadline)
    preparation = retained(private, "preparation.json")
    task_sha = (private / "task.sha256").read_text("ascii").strip()
    snapshot_sha = (private / "snapshot.sha256").read_text("ascii").strip()
    task = retained(private, "task.json", task_sha)
    snapshot_document = retained(private, "snapshot.json", snapshot_sha)
    snapshot = decode(Snapshot, snapshot_document)
    catalog = retained(private, "catalog.json", PINS[CATALOG][1])
    archived = checked_path(RAW_ROOT, ARCHIVED_RECEIPT)
    local_receipt = private / "receipts" / (RECEIPT_SHA + ".json")
    original_receipt = checked_path(RAW_ROOT, TRANSPORT_RECEIPT)
    with stable_files([archived, local_receipt, original_receipt], deadline=deadline):
        archived_bytes = read_file(archived, deadline, 841)
        need(archived_bytes == read_file(local_receipt, deadline, 841) == read_file(original_receipt, deadline, 841) and
             digest(archived_bytes) == RECEIPT_SHA, "Archived receipt bytes differ from preserved transport receipt")
    compile_started, compile_cpu = time.perf_counter(), time.process_time()
    reference = compile_reference(task, snapshot, ROOT, catalog, deadline=deadline, approved_raw_root=RAW_ROOT)
    compile_wall = time.perf_counter() - compile_started
    compile_cpu_seconds = time.process_time() - compile_cpu
    save(private / "reference.json", reference.document)
    # Retain the independent anchor before loading the document for either replay.
    reference_sha = reference.fingerprint
    create(private / "reference.sha256", (reference_sha + "\n").encode("ascii"))
    direct = retained(private, "independent-selected-original-projection.json")
    for fact in reference.document["facts"]:
        name = fact["field"]
        reason = ("field_not_in_schema" if name not in direct else "null_source_value" if direct[name] is None else
                  "empty_source_value" if direct[name] == "" or direct[name] == [] or direct[name] == {} else None)
        need(fact["unknown_reason"] == reason and
             canonical(fact["value"]) == canonical(None if reason else direct[name]),
             "Compiled fact differs from independently retained original projection")
    replay_times = []
    for ordinal in (1, 2):
        replay_started, replay_cpu = time.perf_counter(), time.process_time()
        anchored_sha = (private / "reference.sha256").read_text("ascii").strip()
        loaded = retained(private, "reference.json", anchored_sha)
        task_loaded = retained(private, "task.json", task_sha)
        snapshot_loaded = decode(Snapshot, retained(private, "snapshot.json", snapshot_sha))
        catalog_loaded = retained(private, "catalog.json", PINS[CATALOG][1])
        verified = verify_reference(loaded, anchored_sha, task_loaded, snapshot_loaded, ROOT, catalog_loaded,
                                    deadline=time.monotonic() + 180, approved_raw_root=RAW_ROOT)
        need(verified.fingerprint == reference_sha, "Source-inclusive replay differs")
        replay_times.append(dict(ordinal=ordinal, verified=True, wall_seconds=time.perf_counter() - replay_started,
                                 cpu_seconds=time.process_time() - replay_cpu))
    facts = reference.document["facts"]
    counters = {}
    for family in ("identity_linkage", "reported_context", "reported_measurement", "provider_metric"):
        family_facts = [fact for fact in facts if fact["family"] == family]
        counters[family] = dict(requested_components=len(family_facts),
                               answerable_components=sum(fact["unknown_reason"] is None for fact in family_facts),
                               requested_groups=len({fact["group"] for fact in family_facts}),
                               answerable_groups=len({fact["group"] for fact in family_facts if fact["unknown_reason"] is None}),
                               unknown_reasons=dict(Counter(fact["unknown_reason"] for fact in family_facts if fact["unknown_reason"])))
    summary = dict(
        schema_version=1, status="COMPLETE_ONE_SELECTED_ORIGINAL_SOURCE_REFERENCE_REPLAY",
        role="evaluation_only", agent_visible=False, adjudicated_gold=False, exposure="exposed_development",
        fresh_case=False, scientific_validation="not_established", biological_absence_claimed=False,
        broad_collection_reverified=False,
        scope=dict(selected_original_files=1, selected_physical_records=1, joins=0,
                   requested_fields=[field["field"] for field in task["fields"]],
                   primary_families=task["primary_families"], intervention_context_null=True,
                   namespace_version_policy=preparation["namespace_version_policy"]),
        cutoff=task["cutoff"], cutoff_captured_before_original_read=True,
        pins=dict(inputs=preparation["pins"], script_sha256=digest(Path(__file__).read_bytes()),
                  private_dir=str(private.relative_to(ROOT)).replace("\\", "/"),
                  task_sha256=task_sha, snapshot_sha256=snapshot_sha, reference_sha256=reference_sha,
                  catalog_file_sha256=PINS[CATALOG][1], original_file_sha256=ORIGINAL_SHA,
                  original_file_bytes=1816029, receipt_sha256=RECEIPT_SHA, receipt_bytes=841),
        source_binding_checks=dict(explicit_approved_raw_root=True, exact_manifest_original_path=True,
                                   exact_manifest_transport_receipt_path=True, physical_locator_pinned=True,
                                   identity_rechecked_from_original=True, current_catalog_role_enforced=True,
                                   source_parents_retained=True, unknown_availability_dates_preserved=True,
                                   receipt_archive_bound_in_snapshot=True, receipt_archive_content_addressed=True,
                                   d_private_receipt_copy_equal=True, original_transport_receipt_equal=True,
                                   independently_read_original_projection_equal=True,
                                   independently_retained_reference_hash=True, source_inclusive_replays=2,
                                   projection_wire_verified=reference.document["method"]["projection_wire_verified"]),
        counts=counters,
        measurement_endpoint=dict(answerable_components=counters["reported_measurement"]["answerable_components"],
                                  answerable_groups=counters["reported_measurement"]["answerable_groups"],
                                  coverage=None, pass_80pct_zero_critical=None,
                                  status="not_scored_no_generation; zero_denominator_if_no_answerable_groups"),
        resources=dict(preparation_wall_seconds=preparation["preparation_wall_seconds"],
                       preparation_cpu_seconds=preparation["preparation_cpu_seconds"],
                       compile_wall_seconds=compile_wall, compile_cpu_seconds=compile_cpu_seconds,
                       replay_runs=replay_times, execution_wall_seconds=time.perf_counter() - started,
                       execution_cpu_seconds=time.process_time() - cpu, process_rss_bytes=None,
                       process_rss_status="unmeasured", model_calls=0, generated_candidates=0,
                       scored_cells=0, new_downloads=0, provider_spending_usd=0),
        limitations=[preparation["author_exposure"],
                     "One preselected original row only; earlier 100-file collection was not reverified.",
                     "Engineering reference replay establishes no scientific validity, clinical truth, causal effect or model superiority.",
                     "Missing selected-source measurements are collection-bounded unknowns; identifiers cannot rescue measurement coverage.",
                     "No response, external baseline wire or score was constructed; only the compiler's internal common-wire closure check ran.",
                     "Upstream Ensembl/EFO namespace versions, record/annotation first-public dates and independent mapping validity remain unknown."],
    )
    save(private / "run-summary.json", summary)
    create(SUMMARY, (json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    print(json.dumps(dict(status=summary["status"], sanitized_report=str(SUMMARY),
                          measurement_answerable_components=counters["reported_measurement"]["answerable_components"],
                          source_inclusive_replays=2)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    complete = commands.add_parser("replay")
    complete.add_argument("private_dir")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        replay(args.private_dir)


if __name__ == "__main__":
    main()
