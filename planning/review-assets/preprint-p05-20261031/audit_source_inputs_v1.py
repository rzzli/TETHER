"""Audit the closed P05 STAGE2 inputs against fresh original sources.

No producer/reference/baseline/model execution. Expected source rows, Task
definitions and value-free source bindings are rebuilt independently. No raw
scientific values, answers or human annotations are written to the report.
"""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
from types import SimpleNamespace

ASSETS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p05_audit_primitives", ASSETS / "audit_source_registry_v3.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
ROOT, RAW = a.ROOT, a.RAW
RUN = ROOT / "data/derived/preprint-p05-source-inputs-20261101T074942Z"
TASKS = ROOT / "data/derived/preprint-p05-neutral-tasks-20261101T075541Z"
READY_SHA = "3dbac487bd7fdaf7e7d9470ad9e522d34b5595911387f9dad0971b80f38a291d"
PLAN_SHA = "4d1cfd81f9755a8f63bc737c3aab71b7756c100982724c482c44a7c03b37814c"
BUILDER_SHA = "ec91e0bb288f3bf6747e34d05c61fafdae075be2983fa9bcf0a5c19b881afad3"
COMMIT = "98346a9a6732cad2fc66db838f6cdf3c634ee054"
NEUTRAL_SEAL_SHA = "5bf827df9921a01712d9739d7d04f59e8b0aa3554a9ebc9eaf87d6e240aadace"
CUTOFF = "2026-11-01T07:16:26.101448+00:00"
GWAS = ("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")
IDENTITY = ("studyLocusId", "studyId", "variantId")
MEASURE = ("beta", "standardError", "pValueMantissa", "pValueExponent")
REPORT = {"schema_version": 1, "scope": "independent_original_source_stage2_input_and_neutral_task_audit",
          "run": RUN.relative_to(ROOT).as_posix(), "neutral_tasks": TASKS.relative_to(ROOT).as_posix(),
          "checks": {}, "issues": [], "cost": {}, "model_calls": 0, "network_calls": 0, "new_downloads": 0,
          "reference_builder_calls": 0, "baseline_calls": 0, "raw_scientific_values_in_report": False,
          "scientific_claims": "literal original-source input registration only; no biological validity, intervention, causal, clinical or independent-study claim"}
a.REPORT = REPORT
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index
from asof.serde import encode
from asof.study.source_fact_adapters import _json_value, _source
from asof.study.source_fact_sources import _publication, validate_task


def same(left, right):
    return a.wire(left) == a.wire(right)


def terminal():
    events = [json.loads(line) for line in (RUN / "journal.jsonl").read_bytes().splitlines()]
    prior = None
    for i, e in enumerate(events):
        a.require("journal_" + str(i), e["sequence"] == i and e["previous_sha256"] == prior and a.sha(a.wire({k: v for k, v in e.items() if k != "sha256"})) == e["sha256"])
        prior = e["sha256"]
    a.require("producer_closed_and_terminal", not a.process_live(events[0]["details"]["owner_pid"]) and events[-1]["event"] == "build_completed" and not (RUN / "failure-seal.json").exists())
    seal = a.document(RUN / "seal.json")
    a.require("seal_terminal_binding", events[-1]["details"]["seal_sha256"] == a.sha(a.wire(seal)) and events[-2]["sha256"] == seal["journal_prefix_sha256"])
    a.require("seal_stage_scope", seal["status"] == "completed_source_only_stage2_inputs" and seal["ready_sha256"] == READY_SHA and seal["plan_sha256"] == PLAN_SHA and seal["packet_count"] == seal["selected_case_count"] == 12 and seal["blocked_case_count"] == 0 and all(seal[k] == "not_created" for k in ("references", "outputs", "baselines")) and seal["model_calls"] == seal["network_calls"] == seal["source_mutations"] == 0)
    order = {e["details"]["stage"]: i for i, e in enumerate(events) if e["event"] == "build_stage"}
    admitted = [i for i, e in enumerate(events) if e["event"] == "all_originals_admitted_before_values"]
    a.require("admission_before_values_and_visibility", len(admitted) == 1 and order["verify_all_originals_before_values"] < admitted[0] < order["fresh_original_normalization_and_inventory"] < order["assemble_generation_inputs"] and all(i > order["assemble_generation_inputs"] for i, e in enumerate(events) if e["event"] == "case_packet_prepared"))
    REPORT["terminal"] = {"seal_sha256": a.sha((RUN / "seal.json").read_bytes()), "journal_sha256": a.sha((RUN / "journal.jsonl").read_bytes()), "events": len(events), "producer_process_closed": True}
    return seal, events


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


def audit():
    import pyarrow
    started = time.monotonic()
    REPORT["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    seal, events = terminal()
    deadline = time.monotonic() + 1200
    plan = a.document(ASSETS / "INPUT-PLAN-DRAFT-v1.json")
    ready = a.document(ASSETS / "INPUT-READY-v1.json")
    a.require("frozen_ready_and_plan", a.sha((ASSETS / "INPUT-PLAN-DRAFT-v1.json").read_bytes()) == PLAN_SHA and a.sha((ASSETS / "INPUT-READY-v1.json").read_bytes()) == READY_SHA and ready["plan_sha256"] == PLAN_SHA and ready["actual_build_authorized"] is True)
    a.require("environment", ready["environment"] == plan["environment"] == {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(), "pyarrow": pyarrow.__version__, "platform": sys.platform})
    a.require("all_current_code_pins", len(plan["code_sha256"]) == 68 and plan["code_sha256"] == ready["code_sha256"] and all(a.sha((ROOT / p).read_bytes()) == h for p, h in plan["code_sha256"].items()) and plan["code_sha256"]["tools/science/prepare_source_validation_inputs.py"] == BUILDER_SHA)
    archived = dict(plan["code_sha256"])
    archived.update({"planning/review-assets/preprint-p05-20261031/INPUT-PLAN-DRAFT-v1.json": PLAN_SHA, "planning/review-assets/preprint-p05-20261031/INPUT-READY-v1.json": READY_SHA})
    a.require("pre_run_commit_exact_code_and_authorization", all((lambda result: result.returncode == 0 and a.sha(result.stdout) == h)(subprocess.run(["git", "show", COMMIT + ":" + p], cwd=ROOT, capture_output=True)) for p, h in archived.items()), archived_files=len(archived))
    builder_ast = ast.parse((ROOT / "tools/science/prepare_source_validation_inputs.py").read_bytes())
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else "" for n in ast.walk(builder_ast) if isinstance(n, ast.Call)}
    a.require("producer_no_reference_or_answer_builder_calls", not called.intersection({"compile_reference", "verify_reference", "literal_report", "reporting_view", "adapt_output", "score_output", "run_model", "choose_units", "capture_selected", "open_registry"}))
    expected_paths = {x["path"] for x in seal["artifacts"]} | {"seal.json", "journal.jsonl"}
    a.require("exact_sealed_artifact_set", {p.relative_to(RUN).as_posix() for p in RUN.rglob("*") if p.is_file()} == expected_paths)
    for i, artifact in enumerate(seal["artifacts"]):
        a.require("sealed_artifact_" + str(i), dict(a.hash_file(RUN / artifact["path"], deadline)) == {"sha256": artifact["sha256"], "bytes": artifact["bytes"]})
    docs = {}
    for k, v in plan["neutral_inputs"].items():
        a.require("neutral_pin_" + k, a.sha(Path(v["path"]).read_bytes()) == v["sha256"])
        docs[k] = a.document(v["path"])
    originals = a.inventory(docs["frame"], docs["acquisition"])
    a.require("exact_original_frame", len(originals) == 137 and a.sha(a.wire(originals)) == plan["frame_descriptor_sha256"])
    for i, r in enumerate(originals):
        r["source_id"] = "original-" + str(i).zfill(3)
    lineage = a.document(RUN / "lineage.json")
    snapshot = a.document(RUN / "source-snapshot.json")
    proofs = a.document(RUN / "original-inventory-proofs.json")
    coverage = a.document(RUN / "coverage.json")
    exclusion = a.document(RUN / "excluded-locators.json")
    resource = a.document(RUN / "resource-report.json")
    routing_bytes = Path(plan["selected_case_plan"]).read_bytes()
    routing = json.loads(routing_bytes)
    cases = routing["cases"]
    a.require("unchanged_sealed_routing_caseplan", (RUN / "selected-case-plan.json").read_bytes() == routing_bytes and a.sha(routing_bytes) == plan["authentication"]["stage1_case_plan_sha256"] and len(cases) == 12 and routing["no_replacement"] is True and routing["numeric_availability_used"] is False)
    auth = plan["authentication"]
    a.require("stage1_authentication_exact_frozen_bytes", a.sha((ASSETS / "REGISTRY-PLAN-DRAFT-v3.json").read_bytes()) == auth["stage1_plan_sha256"] and a.sha((ASSETS / "REGISTRY-READY-v3.json").read_bytes()) == auth["stage1_ready_sha256"] and a.sha(Path(plan["stage1_seal"]).read_bytes()) == auth["stage1_seal_sha256"] and len(routing_bytes) == auth["stage1_case_plan_bytes"])
    recipes = lineage["recipe_archive"]
    neutral_recipe_paths = [Path(v["path"]) for v in plan["neutral_inputs"].values()] + [ASSETS / "REGISTRY-PLAN-DRAFT-v3.json", ASSETS / "REGISTRY-READY-v3.json", Path(plan["selected_case_plan"]), Path(plan["stage1_seal"]), ASSETS / "INPUT-PLAN-DRAFT-v1.json", ASSETS / "INPUT-READY-v1.json"]
    expected_recipe_paths = {p.relative_to(ROOT).as_posix() for p in neutral_recipe_paths} | set(plan["code_sha256"])
    a.require("recipe_exact_permitted_input_path_set_before_reads", len(recipes) == len(expected_recipe_paths) == 77 and {r["logical_path"] for r in recipes} == expected_recipe_paths)
    recipe_good = len({r["archive_path"] for r in recipes}) == 77
    for r in recipes:
        a.require("recipe_archive_approved_location_" + a.sha(r["archive_path"].encode())[:16], r["archive_path"].startswith("_private/recipe/") and a.checked_path(RUN, r["archive_path"]).is_file())
        original = (ROOT / r["logical_path"]).read_bytes()
        recipe_good &= (RUN / r["archive_path"]).read_bytes() == original and len(original) == r["bytes"] and a.sha(original) == r["sha256"]
    a.require("exact_recipes_code_plans_and_environment", recipe_good and set(plan["code_sha256"]) <= {r["logical_path"] for r in recipes})
    cutoff = datetime.fromisoformat(CUTOFF)
    a.require("unchanged_old_information_cutoff_new_computation", plan["row_guard_cutoff_utc"] == ready["row_guard_cutoff_utc"] == snapshot["origin_at"] == lineage["information_cutoff"] == CUTOFF and cutoff < datetime.fromisoformat(lineage["computed_at"]) <= datetime.now(timezone.utc))
    paths = [a.checked_path(RAW, r["relative_path"]) for r in originals] + [Path(r["receipt"]["path"]) for r in originals]
    with a.stable_files(paths, deadline=deadline):
        hash_started = time.monotonic()
        nodes, expected_proofs, hashes = [], [], []
        receipts_good = True
        for r in originals:
            a.require("original_path_" + r["source_id"], a.checked_path(RAW, r["relative_path"]) == Path(r["path"]))
            measured = dict(a.hash_file(r["path"], deadline))
            a.require("original_hash_" + r["source_id"], measured == {"sha256": r["sha256"], "bytes": r["bytes"]})
            hashes.append({"source_id": r["source_id"], "family": r["family"], **measured})
            payload = Path(r["receipt"]["path"]).read_bytes()
            receipt = json.loads(payload)
            rel = Path(r["receipt"]["path"]).relative_to(RAW).as_posix()
            archive = "_private/receipts/" + r["receipt"]["sha256"] + ".json"
            receipts_good &= a.sha(payload) == r["receipt"]["sha256"] and len(payload) == r["receipt"]["bytes"] and (RUN / archive).read_bytes() == payload
            receipts_good &= receipt["status"] == "completed" and receipt["dataset_id"] == r["dataset_id"] and receipt["release_id"] == r["release_id"] and receipt["relative_path"].replace("\\", "/") == r["relative_path"] and receipt["url"] == r["source_url"] and type(receipt["bytes"]) is int and receipt["bytes"] == r["bytes"] and receipt["sha256"] == r["sha256"]
            observed = datetime.fromisoformat(receipt["completed_at_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
            receipts_good &= observed <= cutoff
            avail = Availability(None, None, None, None, observed.date(), "public_download_receipt", "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, r["receipt"]["sha256"])
            role = "reference" if r["family"] == "hgnc" else "agent_evidence"
            node = SourceNode(r["source_id"], r["dataset_id"], r["release_id"], r["relative_path"], r["sha256"], role, avail, TemporalClass.CONTEMPORARY, r["source_url"], receipt_path=rel, receipt_sha256=r["receipt"]["sha256"])
            nodes.append(node)
            expected_proofs.append({"source_id": r["source_id"], "dataset_id": r["dataset_id"], "release_id": r["release_id"], "path": r["relative_path"], "sha256": r["sha256"], "bytes": r["bytes"], "role": role, "receipt_path": rel, "receipt_sha256": r["receipt"]["sha256"], "receipt_bytes": r["receipt"]["bytes"], "receipt_archive": archive, "availability": encode(avail)})
        a.require("all_exact_receipts_and_contemporary_chronology", receipts_good, receipts=137)
        expected_snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(RAW), {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
        graph = InputGraph(expected_snapshot, RUN, catalog_index(docs["catalog"]))
        a.require("fresh_original_snapshot_proofs_graph_roles_and_chronology", same(snapshot, encode(expected_snapshot)) and same(proofs, expected_proofs) and graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=cutoff)) is None and same(lineage["original_nodes"], encode(nodes)) and same(lineage["original_proofs"], expected_proofs))
        REPORT["original_hashes"] = hashes
        REPORT["cost"]["all_original_hash_seconds"] = time.monotonic() - hash_started
        scan_started = time.monotonic()
        indexes = a.load_mappings(originals)
        selected, excluded = source_selected(originals, cases, indexes, cutoff)
        a.require("excluded_locators_values_free_and_source_replayed", same(exclusion, {"role": "neutral_metadata", "agent_visible": False, "cases": excluded, "excluded_values": "not_retained"}))
        products = []
        native_types, missingness = Counter(), Counter()
        case_counts = {}
        all_parents = [{"kind": "original", "source_id": n.source_id, "sha256": n.sha256} for n in nodes]
        for c in cases:
            cid, groups = c["case_id"], selected[c["case_id"]]
            packet = a.document(RUN / "packets" / (cid + ".json"))
            packet_keys = {"schema_version", "packet_type", "case_id", "role", "agent_visible", "neutral_task", "task_sha256", "source_records", "fact_skeleton", "normalization_proof", "source_nodes", "source_proofs", "unknown_context", "instruction", "output_contract", "lineage"}
            a.require("packet_exact_generation_input_shape_" + cid, set(packet) == packet_keys and type(packet["schema_version"]) is int and packet["schema_version"] == 1 and packet["packet_type"] == "p05.original_only_generation_inputs.v1" and packet["case_id"] == cid)
            a.require("literal_only_packet_instruction_" + cid, packet["instruction"] == "Report requested literal native original fields using typed_facts_v1 and exact physical source bindings. Preserve absent/null/empty distinctions. Locus joins assert no composite identity or causality. Do not derive p-values, standard errors, scales, alleles, gene/action effects or clinical claims.")
            task = expected_task(c, groups)
            a.require("task_from_fresh_originals_" + cid, same(packet["neutral_task"], task) and same(encode(validate_task(task)), task) and packet["task_sha256"] == a.sha(a.wire(task)))
            rawrows = [{"record_key": rec["record_key"], **row} for rec, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])]
            a.require("every_eligible_physical_raw_row_" + cid, same(packet["source_records"], rawrows))
            for row in rawrows:
                v = row["values"]
                _publication(v, cutoff)
                for k, value in v.items():
                    _json_value(value)
                    if k in MEASURE:
                        native_types[k + ":" + type(value).__name__] += 1
                        missingness[k + ":" + ("null" if value is None else "empty" if value in ("", [], {}) else "present")] += 1
                        a.require("native_scalar_" + cid + "_" + row["record_key"] + "_" + k, value in (None, "", [], {}) or type(value) in (int, float) and (type(value) is not float or math.isfinite(value)) and (k != "pValueExponent" or type(value) is int))
                a.require("native_scope_guard_" + cid + "_" + row["record_key"], all(k not in v or v[k] is None or same(v[k], expected) for k, expected in (("targetId", c["targetId"]), ("target_id", c["targetId"]), ("diseaseId", c["diseaseId"]), ("indication_id", c["diseaseId"]))))
            mapping = {"method": "fresh exact original canonical target/HGNC/disease replay", "target_id_from_raw_GWAS": c["targetId"], "indication_id_from_raw_GWAS": c["diseaseId"], "no_alias_or_variant_inference": True, "target_original": indexes["target"][c["targetId"]][0], "disease_original": indexes["disease"][c["diseaseId"]][0], "hgnc_original": indexes["hgnc"][c["targetId"]][0], "upstream_namespace_versions": {"target": "unknown", "indication": "unknown"}, "other_exposure": "UNKNOWN"}
            a.require("fresh_unique_canonical_mapping_" + cid, all(len(indexes[k][c["targetId"] if k != "disease" else c["diseaseId"]]) == 1 for k in ("target", "disease", "hgnc")) and same(packet["normalization_proof"], mapping))
            skeleton = []
            node_by_id = {n.source_id: n for n in nodes}
            for f in task["fields"]:
                record = next(r for r in task["records"] if r["record_key"] == f["record_key"])
                n = node_by_id[record["source_id"]]
                source = {"source_id": n.source_id, "sha256": n.sha256, "release_id": n.release_id, "locator": record["locator"], "field": f["field"]}
                _source(source)
                identity = {"task_sha256": packet["task_sha256"], "scope": task["scope"], "record_key": f["record_key"], "source": source}
                skeleton.append({"fact_id": "fact:" + a.sha(a.wire(identity)), "record_key": f["record_key"], "field": f["field"], "source": source})
            a.require("value_free_fact_skeleton_bindings_" + cid, same(packet["fact_skeleton"], skeleton) and all(set(s) == {"fact_id", "record_key", "field", "source"} for s in packet["fact_skeleton"]))
            lin = packet["lineage"]
            a.require("full_original_only_packet_parents_" + cid, packet["role"] == "agent_evidence" and packet["agent_visible"] is True and same(packet["source_nodes"], encode(nodes)) and same(packet["source_proofs"], expected_proofs) and set(lin) == {"method", "computed_at", "input_refs", "information_cutoff", "reference_inputs", "evaluation_inputs", "generation_authority"} and lin["method"] == "p05.original_only_generation_inputs.v1" and lin["information_cutoff"] == CUTOFF and lin["computed_at"] == lineage["computed_at"] and lin["reference_inputs"] == lin["evaluation_inputs"] == [] and lin["generation_authority"] is False and same(lin["input_refs"], all_parents + [{"kind": "neutral_config", "sha256": PLAN_SHA}, {"kind": "neutral_selected_case_plan", "sha256": a.sha(routing_bytes)}]))
            output = packet["output_contract"]
            raw_by_key = {r["record_key"]: r["values"] for r in rawrows}
            wire_bound = len(b'{"schema_version":1,"task_id":,"task_sha256":,"status":,"facts":[],"collection_status":,"reason":null}') + len(a.wire(task["task_id"])) + len(a.wire(packet["task_sha256"])) + len(a.wire("insufficient_input")) + len(a.wire("zero_matches_selected_collection"))
            overhead = len(b'{"fact_id":,"value":,"unit":null,"source":,"unknown_reason":}')
            for s in skeleton:
                value_size = len(a.wire(raw_by_key[s["record_key"]][s["field"]])) if s["field"] in raw_by_key[s["record_key"]] else 4
                wire_bound += overhead + len(a.wire(s["fact_id"])) + max(4, value_size) + len(a.wire(s["source"])) + 66
            wire_bound += max(0, len(skeleton) - 1)
            a.require("task_wire_bounds_and_explicit_unknowns_" + cid, set(output) == {"wire_format", "max_facts", "max_output_bytes", "literal_wire_size_upper_bound_bytes", "wire_size_basis", "top_level_keys", "fact_keys"} and wire_bound == output["literal_wire_size_upper_bound_bytes"] <= output["max_output_bytes"] == 262144 and output["max_facts"] == 512 and output["wire_format"] == "typed_facts_v1" and output["top_level_keys"] == ["schema_version", "task_id", "task_sha256", "status", "facts", "collection_status", "reason"] and output["fact_keys"] == ["fact_id", "value", "unit", "source", "unknown_reason"] and len(task["records"]) <= 64 and len(task["fields"]) <= 512 and len(task["joins"]) <= 32 and len(a.wire(task)) <= 1048576 and len(a.wire(packet)) + 1 <= 67108864 and same(packet["unknown_context"], plan["unknown_context"]))
            cov = coverage["cases"][cid]
            expected_base = {"eligible_physical_gwas_rows": len(groups["gwas_credible_sets"]), "eligible_physical_credible_rows": len(groups["credible_set"]), "excluded_physical_rows": len(excluded[cid]), "excluded_reasons": dict(Counter(reason for r in excluded[cid] for reason in r["exclusion_reasons"])), "excluded_values_disclosed": False, "replacement": False, "complete_original_inventory_scanned": True, "status": "packet_created", "task_sha256": packet["task_sha256"], "measurement_groups": len(groups["credible_set"]), "measurement_coverage": None, "pass": None, "zero_credible_policy": "not_scored_in_input_phase" if groups["credible_set"] else "no invented slots; measurement denominator/pass null"}
            a.require("coverage_is_literal_inventory_only_" + cid, same(cov, expected_base))
            products.append({"path": "packets/" + cid + ".json", "role": "agent_evidence", "agent_visible": True, "parents": [n.source_id for n in nodes], "neutral_config_sha256": PLAN_SHA, "neutral_selected_case_plan_sha256": a.sha(routing_bytes)})
            case_counts[cid] = {"gwas": len(groups["gwas_credible_sets"]), "credible": len(groups["credible_set"]), "excluded": len(excluded[cid]), "task_records": len(task["records"]), "field_requests": len(task["fields"]), "measurement_groups": len(groups["credible_set"])}
        a.require("global_original_only_lineage_and_denied_ancestors", set(lineage) == {"schema_version", "method", "computed_at", "information_cutoff", "original_nodes", "original_proofs", "neutral_configuration", "neutral_metadata_is_graph_input", "recipe_archive", "products", "forbidden_value_parents", "references", "model_calls"} and lineage["method"] == "p05.original_only_generation_inputs.v1" and same(lineage["neutral_configuration"], {"plan_sha256": PLAN_SHA, "ready_sha256": READY_SHA, **auth}) and same(lineage["products"], products) and lineage["neutral_metadata_is_graph_input"] is False and same(lineage["forbidden_value_parents"], plan["denied_inputs"]) and lineage["references"] == "not_created" and lineage["model_calls"] == 0)
        REPORT["selected_case_counts"] = case_counts
        REPORT["native_measurement_type_counts"] = dict(native_types)
        REPORT["native_measurement_missingness_counts"] = dict(missingness)
        REPORT["cost"]["fresh_original_selected_inventory_replay_seconds"] = time.monotonic() - scan_started
    neutral = a.document(TASKS / "SEAL.json")
    a.require("neutral_seal_exact_pin_and_input_authentication", a.sha((TASKS / "SEAL.json").read_bytes()) == NEUTRAL_SEAL_SHA and neutral["source_generation_seal_sha256"] == a.sha((RUN / "seal.json").read_bytes()) and neutral["agent_visible"] is False and neutral["source_row_values_copied"] is False and neutral["measurement_expected_values"] is False and neutral["reference_construction"] is False and neutral["model_calls"] == 0)
    a.require("neutral_exact_one_task_per_routing_case_and_two_copies", Counter(i["case_id"] for i in neutral["items"] if "case_id" in i) == Counter(c["case_id"] for c in cases) and Counter(i["path"] for i in neutral["items"] if "case_id" not in i) == Counter(("source-snapshot.json", "selected-case-plan.json")) and all(i["path"] == i["case_id"] + ".task.json" and i["origin_packet_path"] == "packets/" + i["case_id"] + ".json" for i in neutral["items"] if "case_id" in i))
    neutral_paths = {"SEAL.json"}
    for i, item in enumerate(neutral["items"]):
        payload = (TASKS / item["path"]).read_bytes()
        neutral_paths.add(item["path"])
        a.require("neutral_artifact_hash_" + str(i), len(payload) == item["bytes"] and a.sha(payload) == item["sha256"])
        if "case_id" in item:
            packet_path = RUN / item["origin_packet_path"]
            packet = a.document(packet_path)
            a.require("exact_task_only_projection_" + item["case_id"], payload == a.wire(packet["neutral_task"]) and a.sha(payload) == item["task_sha256"] and a.sha(packet_path.read_bytes()) == item["origin_packet_sha256"] and not set(json.loads(payload)).intersection({"source_records", "fact_skeleton", "normalization_proof", "unknown_context", "source_proofs", "source_nodes"}))
        else:
            a.require("unchanged_snapshot_or_routing_copy_" + str(i), item["path"] in ("source-snapshot.json", "selected-case-plan.json") and payload == (RUN / item["path"]).read_bytes())
    a.require("exact_neutral_task_artifact_set", neutral_paths == {p.relative_to(TASKS).as_posix() for p in TASKS.rglob("*") if p.is_file()} and len(neutral["items"]) == 14)
    a.require("producer_logical_resource_counters", resource["logical_bytes_hashed"] == sum(r["bytes"] + r["receipt"]["bytes"] for r in originals) and resource["logical_original_compressed_bytes_scanned"] == sum(r["bytes"] for r in originals if r["family"] in ("gwas_credible_sets", "credible_set")) and resource["physical_io_bytes"] is None)
    REPORT["producer_resource_report"] = resource
    REPORT["pins"] = {"ready_sha256": READY_SHA, "plan_sha256": PLAN_SHA, "builder_sha256": BUILDER_SHA, "pre_run_commit": COMMIT, "neutral_task_seal_sha256": NEUTRAL_SEAL_SHA, "audit_primitives_sha256": a.sha((ASSETS / "audit_source_registry_v3.py").read_bytes())}
    REPORT["cost"]["total_wall_seconds"] = time.monotonic() - started
    REPORT["cost"]["physical_io_bytes"] = None
    REPORT["limitations"] = ["Technical literal-input/source-binding validation only; no scientific or biological validation or independent-study claim.", "The unchanged STAGE1 selection was authenticated and retained; no repeat full-universe eligibility/selection audit was needed.", "Original payload hashes and source locks were fresh; the audit projected all source-frame loci and parsed only selected rows, plus canonical mapping tables.", "No reference compilation, expected-value output, baseline, scoring or model execution occurred.", "Journal/frozen code establish the declared execution path; they do not prove OS isolation or absence of undisclosed external activity.", "Producer sampled RSS is unavailable; audit Win32 process peak is separately measured. Physical disk traffic is unmeasured."]
    REPORT["status"] = "PASS_ORIGINAL_SOURCE_INPUTS_AND_NEUTRAL_TASKS" if not REPORT["issues"] else "FAIL_ORIGINAL_SOURCE_INPUTS_AND_NEUTRAL_TASKS"


def main():
    try:
        audit()
    except BaseException as exc:
        REPORT["status"] = "INCOMPLETE_OR_FAILED_INPUT_AUDIT"
        REPORT["error_class"] = type(exc).__name__
        if isinstance(exc, AssertionError):
            REPORT["failed_check"] = str(exc)
    REPORT["audit_script_sha256"] = a.sha(Path(__file__).read_bytes())
    output = ASSETS / "INPUT-AUDIT-v1.json"
    if output.exists():
        raise RuntimeError("Preserve existing audit history")
    output.write_bytes(a.wire(REPORT) + b"\n")
    print(json.dumps({"status": REPORT["status"], "checks": len(REPORT["checks"]), "issues": REPORT["issues"], "error_class": REPORT.get("error_class"), "report_sha256": a.sha(output.read_bytes()), "cost": REPORT["cost"]}))
    return 0 if REPORT["status"] == "PASS_ORIGINAL_SOURCE_INPUTS_AND_NEUTRAL_TASKS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
