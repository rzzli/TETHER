"""Independent original-source audit of one CLOSED P05 reference run.

No reference/answer/compiler/baseline/model function is called. Expected literal
facts are computed here from fresh originals and the sealed neutral Tasks.
Producer wrappers, selectors, mapping helpers and task builders are not imported.
The independent INPUT audit's own scan/date/mapping implementations are reused.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from types import SimpleNamespace

ASSETS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_p05_input_audit", ASSETS / "audit_source_inputs_v1.py")
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
a, ROOT, RAW, TASKS = s.a, s.ROOT, s.RAW, s.TASKS
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index
from asof.serde import encode

PLAN_SHA = "f8dbfd218f99fb2d694b78b606cb7d183fd267639159e0895c1bafb93741617b"
BUILDER_SHA = "c6850eb84953a7102f68bbfbb11550602267046f0eef3533636b65d8731aa9c6"
METHOD = "p05.independent_original_source_references.v1"
REPORT = {"schema_version": 1, "scope": "independent_algorithmic_original_source_reference_audit", "checks": {}, "issues": [], "cost": {},
          "model_calls": 0, "network_calls": 0, "new_downloads": 0, "reference_builder_calls": 0, "core_compiler_calls": 0,
          "baseline_calls": 0, "raw_scientific_values_or_expected_answers_written": False,
          "retained_prior_attempts": [{"report": "REFERENCE-AUDIT-v1-attempt1.json", "sha256": "8362d3e26a692a97a3a4d79d09d1cbfb53e52e324b88dbf4630f27b80384015f", "checker": "audit_source_references_v1_attempt1.py", "checker_sha256": "dee19d6f880e135b48d50f5526fbbf7382f7581e9be86035df86ee155ef6a334", "status": "INCOMPLETE_OR_FAILED_REFERENCE_AUDIT", "error_class": "NameError", "cause": "missing platform module import in checker", "original_source_values_read": 0, "tool_process_wall_seconds": 1.0755454}],
          "evidence_separation": {"producer": "independent author and isolated original rereads; shared selection/mapping/task/base compiler algorithms", "audit": "separate original reads and independently implemented selector/date/mapping/Task and literal fact/join projection; no producer helper/compiler oracle"}}
s.REPORT = a.REPORT = REPORT


def utc(value):
    if type(value) is not str or "T" not in value:
        raise ValueError("Exact UTC metadata timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("Timezone-aware UTC metadata timestamp required")
    return result.astimezone(timezone.utc)


def empty(value):
    return type(value) is str and value == "" or type(value) in (list, dict, tuple) and not value


def strict_source_guards(row, task):
    """Independently check the core's literal native date/scope boundary."""
    cutoff = utc(task["cutoff"])
    for field in ("publicationDate", "evidenceDate", "annotationDate"):
        value = row.get(field)
        if value is None or value == "":
            continue
        if type(value) is not str:
            return False
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            observed = datetime.fromisoformat(value).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
        else:
            observed = utc(value)
        if observed > cutoff:
            return False
    year = row.get("publicationYear")
    if year is not None and (type(year) is not int or not 1 <= year <= cutoff.year):
        return False
    return all(name not in row or row[name] is None or s.same(row[name], task["scope"][scope]) for name, scope in (("targetId", "target_id"), ("target_id", "target_id"), ("diseaseId", "indication_id"), ("indication_id", "indication_id")))


def expected_joins(task, rows, nodes):
    """Literal joins and reachability authored independently of the compiler."""
    requests = {r["record_key"]: r for r in task["records"]}
    anchors = {k for k, r in requests.items() if any(r["identity"].get(n) == task["scope"]["target_id"] for n in ("targetId", "target_id")) and any(r["identity"].get(n) == task["scope"]["indication_id"] for n in ("diseaseId", "indication_id"))}
    incoming, reports = defaultdict(list), []
    for j in task["joins"]:
        left = rows[j["left_record"]]
        value = left.get(j["left_field"])
        available = j["left_field"] in left and value is not None and not empty(value)
        matches = [k for k in j["right_records"] if available and j["right_field"] in rows[k] and rows[k][j["right_field"]] is not None and not empty(rows[k][j["right_field"]]) and s.same(value, rows[k][j["right_field"]])]
        # The frozen P05 Tasks explicitly declare locus-only one_to_many joins.
        a.require("frozen_locus_only_join_" + a.sha(a.wire([task["task_id"], j["join_id"]]))[:16], j["cardinality"] == "one_to_many" and j["left_field"] == j["right_field"] == "studyLocusId" and j["inventory_status"] == "complete")
        status = "unavailable_key" if not available else "zero_matches_selected_collection" if not matches else "matched"
        sources = []
        for k in matches:
            n, request = nodes[requests[k]["source_id"]], requests[k]
            sources.append({"source_id": n.source_id, "sha256": n.sha256, "release_id": n.release_id, "locator": request["locator"], "field": j["right_field"]})
        report = {k: j[k] for k in ("join_id", "left_record", "right_records", "cardinality", "inventory_status")}
        reports.append({**report, "status": status, "matched_records": matches, "matched_sources": sources})
        for right in j["right_records"]:
            incoming[right].append((j["left_record"], None if status == "matched" and right in matches else "unavailable_join"))
    def reach(key, active):
        if key in anchors:
            return None
        if key in active or not incoming[key]:
            return "unavailable_join"
        return "unavailable_join" if any(reason or reach(left, active | {key}) for left, reason in incoming[key]) else None
    return reports, {key: reach(key, set()) for key in requests}


def direct_reference(task, original_rows, nodes, proofs, catalog, snapshot):
    """Expected document only in memory; never save expected facts or answers."""
    requests = {r["record_key"]: r for r in task["records"]}
    joins, restrictions = expected_joins(task, original_rows, nodes)
    task_hash = a.sha(a.wire(task))
    facts = []
    for field in task["fields"]:
        key, name = field["record_key"], field["field"]
        row, record = original_rows[key], requests[key]
        source_node = nodes[record["source_id"]]
        value = row.get(name)
        unit = row.get(field["unit_field"]) if field["unit_field"] is not None else None
        reason = "failed_qc" if task["collection"]["status"] == "failed_qc" else restrictions[key]
        if reason is None:
            if name not in row:
                reason = "field_not_in_schema"
            elif value is None:
                reason = "null_source_value"
            elif empty(value) and field["empty_policy"] == "unknown":
                reason = "empty_source_value"
        if reason is None and field["family"] == "reported_measurement":
            if type(value) not in (int, float) or type(value) is float and not math.isfinite(value) or name == "pValueExponent" and type(value) is not int:
                raise ValueError("Original native numeric representation failed")
        if reason is not None:
            value = None
        binding = {"source_id": source_node.source_id, "sha256": source_node.sha256, "release_id": source_node.release_id, "locator": record["locator"], "field": name}
        identity = {"task_sha256": task_hash, "scope": task["scope"], "record_key": key, "source": binding}
        facts.append({"fact_id": "fact:" + a.sha(a.wire(identity)), "record_key": key, "field": name, "family": field["family"], "group": field["group"], "value": value, "unit": unit, "source": binding, "unknown_reason": reason})
    # This public type taxonomy is protocol metadata, never an expected-value oracle.
    from asof.study.source_fact_sources import FIELD_FAMILIES
    snapshot_policy = json.loads(a.wire(snapshot))
    snapshot_policy["raw_root"] = None
    return {"schema_version": 1, "task_id": task["task_id"], "task_sha256": task_hash, "role": "evaluation_only", "agent_visible": False,
            "scope": task["scope"], "cutoff": task["cutoff"], "profile": task["profile"], "primary_families": task["primary_families"],
            "collection": task["collection"], "facts": facts, "joins": joins, "source_proofs": proofs,
            "method": {"code_id": "asof.study.source_fact_sources", "version": "1", "transform": "literal_field.v1", "task": task,
                       "json_read_max_bytes": 67108864, "field_family_map_sha256": a.sha(a.wire(FIELD_FAMILIES)), "scientific_validation": "not_established",
                       "linked_measurement_scope": "source_locus_only", "catalog_sha256": a.sha(a.wire({x["dataset_id"]: x for x in catalog["datasets"]})),
                       "source_snapshot_sha256": a.sha(a.wire(snapshot_policy)), "deny_policy": {"source_ids": [], "dataset_ids": [], "sha256": []}, "projection_wire_verified": True}}


def audit(args):
    import pyarrow
    started = time.monotonic()
    run = Path(args.run).resolve()
    a.require("explicit_approved_new_reference_run", run.parent == ROOT / "data/benchmark/gold_evidence" and re.fullmatch(r"preprint-p05-references-\d{8}T\d{6}Z", run.name) is not None and a.checked_path(ROOT, run.relative_to(ROOT).as_posix()) == run)
    REPORT["run"] = run.relative_to(ROOT).as_posix()
    REPORT["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    events = [json.loads(line) for line in (run / "journal.jsonl").read_bytes().splitlines()]
    previous = None
    for i, e in enumerate(events):
        a.require("journal_event_" + str(i), e["sequence"] == i and e["previous_sha256"] == previous and a.sha(a.wire({k: v for k, v in e.items() if k != "sha256"})) == e["sha256"])
        previous = e["sha256"]
    a.require("producer_closed_terminal_no_failure", not a.process_live(events[0]["details"]["owner_pid"]) and events[-1]["event"] == "build_completed" and not (run / "failure-seal.json").exists())
    seal_bytes = (run / "seal.json").read_bytes()
    seal = json.loads(seal_bytes)
    a.require("independent_exact_seal_pin", a.sha(seal_bytes) == args.seal_sha256)
    a.require("terminal_journal_seal_binding", events[-1]["details"]["seal_sha256"] == a.sha(a.wire(seal)) and events[-2]["sha256"] == seal["journal_prefix_sha256"])
    a.require("reference_seal_role_scope", seal["status"] == "sealed_verified_source_references" and seal["role"] == "evaluation_only" and seal["agent_visible"] is False and seal["adjudicated_gold"] is False and seal["model_calls"] == seal["provider_cost_usd"] == 0)
    deadline = time.monotonic() + 1200
    artifacts = seal["artifacts"]
    a.require("whole_sealed_artifact_set", {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file()} == {x["path"] for x in artifacts} | {"seal.json", "journal.jsonl"})
    for i, item in enumerate(artifacts):
        path = a.checked_path(run, item["path"])
        a.require("artifact_hash_" + str(i), dict(a.hash_file(path, deadline)) == {"sha256": item["sha256"], "bytes": item["bytes"]})
    manifest_bytes = (run / "references.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    a.require("independent_manifest_fingerprint", a.sha(a.wire(manifest)) == args.manifest_sha256 == seal["manifest_sha256"] == events[-1]["details"]["manifest_sha256"])
    context = manifest["authorization"]
    plan_bytes, ready_bytes = context["draft_json"].encode(), context["ready_json"].encode()
    plan, ready = json.loads(plan_bytes), json.loads(ready_bytes)
    a.require("retained_frozen_plan_ready_and_scope", a.sha(plan_bytes) == PLAN_SHA and a.sha(ready_bytes) == args.ready_sha256 and ready["plan_sha256"] == PLAN_SHA and ready["status"] == "READY" and ready["frozen_by"] == "root" and ready["scope"] == plan["scope"] == "p05_independent_source_references" and ready["actual_build_authorized"] is True)
    a.require("exact_current_code_and_environment", len(plan["code_sha256"]) == 69 and ready["code_sha256"] == plan["code_sha256"] and all(a.sha((ROOT / p).read_bytes()) == h for p, h in plan["code_sha256"].items()) and plan["code_sha256"]["tools/science/build_source_validation_references.py"] == BUILDER_SHA and ready["environment"] == plan["environment"] == {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(), "pyarrow": pyarrow.__version__, "platform": sys.platform})
    git_files = dict(plan["code_sha256"])
    git_files.update({"planning/review-assets/preprint-p05-20261031/REFERENCE-PLAN-DRAFT-v1.json": PLAN_SHA, "planning/review-assets/preprint-p05-20261031/REFERENCE-READY-v1.json": args.ready_sha256})
    a.require("pre_run_git_frozen_bytes", all((lambda result: result.returncode == 0 and a.sha(result.stdout) == h)(subprocess.run(["git", "show", args.pre_run_commit + ":" + path], cwd=ROOT, capture_output=True)) for path, h in git_files.items()), files=len(git_files))
    auth = plan["authentication"]
    a.require("manifest_authentication_and_information_time", s.same(auth, ready["authentication"]) and s.same(auth, manifest["authentication"]) and manifest["ready_sha256"] == args.ready_sha256 and plan["row_guard_cutoff_utc"] == ready["row_guard_cutoff_utc"] == manifest["information_cutoff"] == s.CUTOFF and utc(s.CUTOFF) <= utc(manifest["computed_at"]) <= datetime.now(timezone.utc))
    neutral_seal_bytes = context["neutral_seal_json"].encode()
    a.require("neutral_seal_exact_archived_and_current", a.sha(neutral_seal_bytes) == auth["neutral_seal_sha256"] == s.NEUTRAL_SEAL_SHA and neutral_seal_bytes == (TASKS / "SEAL.json").read_bytes())
    a.require("exact_retained_authorization_shape", set(context) == {"draft_json", "ready_json", "neutral_seal_json", "neutral_files_json", "metadata_files_json", "version_policy"})
    docs = {}
    metadata_paths = {"frame": ASSETS / "FRAME-METADATA-PREFLIGHT-v1.json", "acquisition": ASSETS / "ACQUISITION-METADATA-v1.json", "catalog": ROOT / "data/catalog/sources.json"}
    for name, path in metadata_paths.items():
        payload = context["metadata_files_json"][name].encode()
        a.require("retained_neutral_metadata_" + name, payload == path.read_bytes() and a.sha(payload) == auth["metadata_sha256"][name])
        docs[name] = json.loads(payload)
    expected_query_names = {"p05-" + str(i).zfill(2) + ".task.json" for i in range(1, 13)} | {"source-snapshot.json", "selected-case-plan.json"}
    a.require("exact_retained_neutral_query_inventory", set(context["neutral_files_json"]) == set(auth["neutral_files_sha256"]) == expected_query_names and set(context["metadata_files_json"]) == set(metadata_paths))
    neutral = {}
    for name in expected_query_names:
        payload = context["neutral_files_json"][name].encode()
        a.require("retained_query_" + name, payload == (TASKS / name).read_bytes() and a.sha(payload) == auth["neutral_files_sha256"][name])
        neutral[name] = json.loads(payload)
    cases = neutral["selected-case-plan.json"]["cases"]
    a.require("all_twelve_unchanged_routing_cases", [c["case_id"] for c in cases] == ["p05-" + str(i).zfill(2) for i in range(1, 13)] and manifest["actual_selected_units"] == plan["actual_selected_units"] == len(cases) == 12 and set(manifest["cases"]) == {c["case_id"] for c in cases})
    originals = a.inventory(docs["frame"], docs["acquisition"])
    a.require("exact_original_frame_descriptor", len(originals) == 137 and a.sha(a.wire(originals)) == auth["frame_descriptor_sha256"])
    for i, r in enumerate(originals):
        r["source_id"] = "original-" + str(i).zfill(3)
    expected_inputs = [{"source_id": r["source_id"], **{k: r[k] for k in ("relative_path", "sha256", "receipt")}} for r in originals]
    a.require("manifest_full_original_only_inputs", s.same(manifest["original_inputs"], expected_inputs))
    recipes = manifest["recipe"]
    allowed_recipes = {p.relative_to(ROOT).as_posix() for p in metadata_paths.values()} | {p.relative_to(ROOT).as_posix() for p in [TASKS / "SEAL.json", *[TASKS / n for n in expected_query_names], ASSETS / "REFERENCE-PLAN-DRAFT-v1.json", ASSETS / "REFERENCE-READY-v1.json"]} | set(plan["code_sha256"])
    a.require("recipe_exact_whitelisted_inventory_before_reads", len(recipes) == len(allowed_recipes) == 89 and {r["logical_path"] for r in recipes} == allowed_recipes and len({r["archive_path"] for r in recipes}) == len(recipes))
    for i, r in enumerate(recipes):
        payload = a.checked_path(run, r["archive_path"]).read_bytes()
        a.require("recipe_exact_archive_" + str(i), r["archive_path"].startswith("_private/recipe/") and payload == (ROOT / r["logical_path"]).read_bytes() and a.sha(payload) == r["sha256"] and len(payload) == r["bytes"])
    source_paths = [a.checked_path(RAW, r["relative_path"]) for r in originals] + [Path(r["receipt"]["path"]) for r in originals]
    with a.stable_files(source_paths, deadline=deadline):
        hashing_started = time.monotonic()
        nodes, proofs, hashes = [], [], []
        receipt_checks = True
        for r in originals:
            a.require("approved_original_path_" + r["source_id"], a.checked_path(RAW, r["relative_path"]) == Path(r["path"]))
            measured = dict(a.hash_file(r["path"], deadline))
            a.require("original_hash_" + r["source_id"], measured == {"sha256": r["sha256"], "bytes": r["bytes"]})
            hashes.append({"source_id": r["source_id"], "family": r["family"], **measured})
            receipt_bytes = Path(r["receipt"]["path"]).read_bytes()
            receipt = json.loads(receipt_bytes)
            observed = utc(receipt["completed_at_utc"])
            receipt_rel = Path(r["receipt"]["path"]).relative_to(RAW).as_posix()
            receipt_checks &= observed <= utc(s.CUTOFF) and a.sha(receipt_bytes) == r["receipt"]["sha256"] and len(receipt_bytes) == r["receipt"]["bytes"] and receipt_bytes == (run / "_private/receipts" / (r["receipt"]["sha256"] + ".json")).read_bytes()
            receipt_checks &= receipt["status"] == "completed" and receipt["dataset_id"] == r["dataset_id"] and receipt["release_id"] == r["release_id"] and receipt["sha256"] == r["sha256"] and type(receipt["bytes"]) is int and receipt["bytes"] == r["bytes"] and receipt["url"] == r["source_url"] and receipt["relative_path"].replace("\\", "/") == r["relative_path"]
            avail = Availability(None, None, None, None, observed.date(), "public_download_receipt", "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, r["receipt"]["sha256"])
            role = "reference" if r["family"] == "hgnc" else "agent_evidence"
            n = SourceNode(r["source_id"], r["dataset_id"], r["release_id"], r["relative_path"], r["sha256"], role, avail, TemporalClass.CONTEMPORARY, r["source_url"], receipt_path=receipt_rel, receipt_sha256=r["receipt"]["sha256"])
            nodes.append(n)
            proofs.append({"artifact_id": n.source_id, "dataset_id": n.dataset_id, "release_id": n.release_id, "path": n.path, "sha256": n.sha256, "role": n.role, "parents": [], "receipt_path": receipt_rel, "receipt_sha256": r["receipt"]["sha256"], "bytes": r["bytes"], "availability": encode(avail), "temporal_classification": "contemporary_only", "path_scope": "raw", "receipt_bytes": r["receipt"]["bytes"]})
        a.require("all_exact_receipts_and_UTC_chronology", receipt_checks, receipts=137)
        cutoff = utc(s.CUTOFF)
        snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(RAW), {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
        graph = InputGraph(snapshot, run, catalog_index(docs["catalog"]))
        a.require("fresh_original_snapshot_roles_ancestry_and_time", s.same(encode(snapshot), neutral["source-snapshot.json"]) and graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=cutoff)) is None and all(not n.parents and n.computed_at is None for n in nodes))
        REPORT["original_hashes"] = hashes
        REPORT["cost"]["original_hash_seconds"] = time.monotonic() - hashing_started
        projection_started = time.monotonic()
        indexes = a.load_mappings(originals)
        selected, excluded = s.source_selected(originals, cases, indexes, cutoff)
        total_facts, unknown_reasons, value_types, groups_count = Counter(), Counter(), Counter(), Counter()
        selected_locators = set()
        node_map = {n.source_id: n for n in nodes}
        case_counts = {}
        for case in cases:
            cid = case["case_id"]
            task = neutral[cid + ".task.json"]
            groups = selected[cid]
            a.require("independent_task_reconstruction_" + cid, s.same(task, s.expected_task(case, groups)))
            rows = {record["record_key"]: row["values"] for record, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])}
            a.require("independent_native_publication_annotation_scope_guard_" + cid, all(strict_source_guards(row, task) for row in rows.values()) and task["scope"]["target_namespace_version"] == task["scope"]["indication_namespace_version"] == "unknown" and all(task["scope"][key] is None for key in ("action", "modality", "tissue")))
            for source_row in groups["gwas_credible_sets"] + groups["credible_set"]:
                selected_locators.add(a.wire({"source_id": source_row["source_id"], "locator": source_row["locator"]}))
            expected = direct_reference(task, rows, node_map, proofs, docs["catalog"], encode(snapshot))
            wire = {"schema_version": 1, "task_id": task["task_id"], "task_sha256": expected["task_sha256"], "status": "answered" if expected["facts"] else "insufficient_input", "facts": [{key: f[key] for key in ("fact_id", "value", "unit", "source", "unknown_reason")} for f in expected["facts"]], "collection_status": task["collection"]["status"], "reason": None if expected["facts"] else "No selected facts; collection-bounded missing input."}
            a.require("independent_common_wire_bounds_" + cid, len(a.wire(wire)) <= 262144 and len(wire["facts"]) <= 512 and all(len(f["fact_id"]) <= 512 and all(len(f["source"][key]) <= 512 for key in ("source_id", "release_id", "field")) and (f["unknown_reason"] is None or type(f["unknown_reason"]) is str and 0 < len(f["unknown_reason"]) <= 1800) and (type(f["value"]) is not str or len(f["value"]) <= 8192) for f in wire["facts"]))
            actual = manifest["cases"][cid]
            a.require("complete_reference_from_independent_original_projection_" + cid, s.same(actual["reference"], expected), facts=len(expected["facts"]))
            mapping = {"method": "fresh exact original canonical target/HGNC/disease replay", "target_id_from_raw_GWAS": case["targetId"], "indication_id_from_raw_GWAS": case["diseaseId"], "no_alias_or_variant_inference": True, "target_original": indexes["target"][case["targetId"]][0], "disease_original": indexes["disease"][case["diseaseId"]][0], "hgnc_original": indexes["hgnc"][case["targetId"]][0], "upstream_namespace_versions": {"target": "unknown", "indication": "unknown"}, "other_exposure": "UNKNOWN"}
            inventory = {family: [{"source_id": row["source_id"], "locator": row["locator"]} for row in items] for family, items in groups.items()}
            replay = {"case_id": cid, "eligible_inventory": inventory, "excluded_inventory": excluded[cid], "neutral_task_sha256": a.sha(a.wire(task)), "row_guard_cutoff_utc": s.CUTOFF, "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False, "normalization_sha256": a.sha(a.wire(mapping)), "status": "ready_for_base_compile", "blocked_reason": None}
            replay["replay_sha256"] = a.sha(a.wire(replay))
            replay.update(status="compiled", reference_sha256=a.sha(a.wire(expected)))
            a.require("original_guard_inventory_mapping_disposition_" + cid, s.same(actual["disposition"], replay))
            family_groups = set()
            for fact in expected["facts"]:
                total_facts[fact["family"]] += 1
                unknown_reasons[fact["unknown_reason"] or "known"] += 1
                value_types[fact["field"] + ":" + type(fact["value"]).__name__] += 1
                family_groups.add((fact["family"], fact["group"]))
                a.require("native_unit_and_source_binding_" + cid + "_" + a.sha(fact["fact_id"].encode())[:12], fact["unit"] is None and set(fact["source"]) == {"source_id", "sha256", "release_id", "locator", "field"} and (fact["unknown_reason"] is None) == (fact["value"] is not None))
            groups_count.update(family for family, group in family_groups)
            case_counts[cid] = {"facts": len(expected["facts"]), "known": sum(f["unknown_reason"] is None for f in expected["facts"]), "unknown": sum(f["unknown_reason"] is not None for f in expected["facts"]), "GWAS_rows": len(groups["gwas_credible_sets"]), "credible_rows": len(groups["credible_set"]), "excluded_rows": len(excluded[cid]), "locus_joins": len(expected["joins"])}
        a.require("all_180_bindings_and_24_distinct_original_rows", sum(total_facts.values()) == 180 and len(selected_locators) == 24, facts=sum(total_facts.values()), distinct_original_rows=len(selected_locators))
        REPORT["case_counts"] = case_counts
        REPORT["fact_family_counts"] = dict(total_facts)
        REPORT["fact_unknown_reason_counts"] = dict(unknown_reasons)
        REPORT["native_field_type_counts"] = dict(value_types)
        REPORT["group_counts"] = dict(groups_count)
        REPORT["dependence"] = {"technical_source_units": 12, "independent_studies": "not_established", "measurement_grouping": "four native fields per physical credible row; locus-only linkage; study/variant fields separate"}
        REPORT["cost"]["independent_original_projection_seconds"] = time.monotonic() - projection_started
    a.require("manifest_exact_role_context_scientific_limits", set(manifest) == {"schema_version", "method", "role", "agent_visible", "adjudicated_gold", "computed_at", "information_cutoff", "authentication", "ready_sha256", "recipe", "recipe_policy", "authorization", "original_inputs", "unknown_context", "actual_selected_units", "scientific_validation", "cases"} and manifest["method"] == METHOD and manifest["role"] == "evaluation_only" and manifest["agent_visible"] is False and manifest["adjudicated_gold"] is False and s.same(manifest["unknown_context"], plan["unknown_context"]) and manifest["scientific_validation"] == "not_established; technical source units only" and manifest["recipe_policy"] == "descriptive_archive_inventory_only; archive files are authenticated by the output seal, not standalone source replay")
    build_report = a.document(run / "build-report.json")
    resource = build_report["resources"]
    a.require("build_report_dispositions", build_report["status"] == "verified" and build_report["role"] == "evaluation_only" and build_report["agent_visible"] is False and build_report["adjudicated_gold"] is False and build_report["manifest_sha256"] == args.manifest_sha256 and build_report["verified_cases"] == [c["case_id"] for c in cases] and build_report["blocked_cases"] == [])
    logical_one_pass = sum(r["bytes"] + r["receipt"]["bytes"] for r in originals)
    a.require("resource_logical_vs_physical_accounting", resource["logical_bytes_hashed_by_wrapper"] == 2 * logical_one_pass and resource["logical_original_compressed_bytes_scanned"] == 2 * sum(r["bytes"] for r in originals) and resource["fresh_original_compressed_bytes"] == sum(r["bytes"] for r in originals) and resource["logical_base_completed_hash_bytes"] == 6 * 12 * logical_one_pass and resource["base_failed_calls_with_unmeasured_partial_hash_bytes"] == 0 and resource["physical_io_bytes"] is None and resource["model_calls"] == resource["provider_cost_usd"] == 0)
    REPORT["producer_resource_report"] = resource
    REPORT["pins"] = {"ready_sha256": args.ready_sha256, "plan_sha256": PLAN_SHA, "builder_sha256": BUILDER_SHA, "pre_run_commit": args.pre_run_commit, "manifest_sha256": args.manifest_sha256, "seal_sha256": args.seal_sha256, "journal_sha256": a.sha((run / "journal.jsonl").read_bytes()), "independent_input_audit_script_sha256": a.sha((ASSETS / "audit_source_inputs_v1.py").read_bytes()), "independent_registry_audit_primitives_sha256": a.sha((ASSETS / "audit_source_registry_v3.py").read_bytes())}
    REPORT["cost"]["total_wall_seconds"] = time.monotonic() - started
    REPORT["cost"]["physical_io_bytes"] = None
    REPORT["byte_semantic_scientific_separation"] = {"bytes": "all source/receipt/output/archive hashes verified", "semantics": "all facts, unknown reasons, source bindings, joins and grouping compared to independent original projection", "scientific_validation": "not_established"}
    REPORT["limitations"] = ["No compiler/wrapper replay was used as the expected-fact oracle; producer replay is separate evidence.", "This is an audit of 12 fixed technical source units, not clinical validation or a count of independent studies.", "Native beta and p-value components remain study/variant observations; unknown units/scales/alleles/ancestry/build/action are preserved.", "Cooperative original-file locks and pins do not establish hostile-OS isolation or absence of unlogged activity.", "Logical hashing/scan bytes and audit process peak are distinct from physical disk traffic, which is unmeasured."]
    REPORT["status"] = "PASS_INDEPENDENT_ORIGINAL_SOURCE_REFERENCE_AUDIT" if not REPORT["issues"] else "FAIL_INDEPENDENT_ORIGINAL_SOURCE_REFERENCE_AUDIT"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True)
    p.add_argument("--ready-sha256", required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--seal-sha256", required=True)
    p.add_argument("--pre-run-commit", required=True)
    p.add_argument("--producer-closed", required=True, action="store_true")
    args = p.parse_args()
    if any(re.fullmatch(r"[0-9a-f]{64}", getattr(args, k)) is None for k in ("ready_sha256", "manifest_sha256", "seal_sha256")) or re.fullmatch(r"[0-9a-f]{40}", args.pre_run_commit) is None:
        raise ValueError("Independent exact pins are required")
    try:
        audit(args)
    except BaseException as exc:
        REPORT["status"] = "INCOMPLETE_OR_FAILED_REFERENCE_AUDIT"
        REPORT["error_class"] = type(exc).__name__
        if isinstance(exc, AssertionError):
            REPORT["failed_check"] = str(exc)
    REPORT["audit_script_sha256"] = a.sha(Path(__file__).read_bytes())
    output = ASSETS / "REFERENCE-AUDIT-v1.json"
    if output.exists():
        raise RuntimeError("Preserve existing reference audit history")
    output.write_bytes(a.wire(REPORT) + b"\n")
    print(json.dumps({"status": REPORT["status"], "checks": len(REPORT["checks"]), "issues": REPORT["issues"], "error_class": REPORT.get("error_class"), "report_sha256": a.sha(output.read_bytes()), "cost": REPORT["cost"]}))
    return 0 if REPORT["status"] == "PASS_INDEPENDENT_ORIGINAL_SOURCE_REFERENCE_AUDIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
