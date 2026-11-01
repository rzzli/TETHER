"""Evaluator-only P05 exposure/dependence/denominator metadata, fresh originals.

No generation packets, reference values, answers, human returns, old gold,
clinical outcomes, producer selectors, models or network services are read.
Native identifier strings are retained literally; equality is never study identity.
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

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "planning/review-assets/preprint-p05-20261031"
spec = importlib.util.spec_from_file_location("independent_p05_input_audit", ASSETS / "audit_source_inputs_v1.py")
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
a, RAW, TASKS = s.a, s.RAW, s.TASKS
from asof.atomic import publish_bytes
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.journal import RunJournal
from asof.provenance import InputGraph, catalog_index
from asof.serde import encode
from types import SimpleNamespace

PARENT = ROOT / "data/benchmark/cohorts"
PREFIX = "preprint-p05-register-"
METHOD = "p05.fresh_original_exposure_dependence_denominators.v1"
FIELDS = ("studyId", "variantId", "studyLocusId", "targetId", "diseaseId")
STATUSES = ("answerable", "null", "absent", "empty", "invalid")
PINS = {"frame": (ASSETS / "FRAME-METADATA-PREFLIGHT-v1.json", "c9af0da5ff7a07b95372383d73c493faef0ba4081a34768d88393a881ff26551"),
        "acquisition": (ASSETS / "ACQUISITION-METADATA-v1.json", "428ab3be53abffb24f8d2e95e457f603012b8e66a3ee02575e696f996b00a405"),
        "catalog": (ROOT / "data/catalog/sources.json", "3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109")}
REPORT = {"schema_version": 1, "scope": "fresh_original_evaluator_metadata_register", "checks": {}, "issues": [], "cost": {}}
s.REPORT = a.REPORT = REPORT


def utc(value):
    if type(value) is not str or "T" not in value:
        raise ValueError("Exact UTC timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Timezone-aware UTC required")
    return parsed.astimezone(timezone.utc)


def classify(row, field, family):
    if field not in row:
        return "absent"
    value = row[field]
    if value is None:
        return "null"
    if type(value) is str and value == "" or type(value) in (list, dict, tuple) and not value:
        return "empty"
    if family == "reported_measurement" and (type(value) not in (int, float) or type(value) is float and not math.isfinite(value) or field == "pValueExponent" and type(value) is not int):
        return "invalid"
    return "answerable"


def native_identity(row):
    result = {}
    reasons = {"answerable": None, "absent": "field_not_in_schema", "null": "null_source_value", "empty": "empty_source_value", "invalid": "native_type_invalid"}
    for field in FIELDS:
        status = classify(row, field, "identity_linkage")
        result[field] = {"present": field in row, "value": row.get(field), "status": status, "unknown_reason": reasons[status]}
    return result


def denominator(task, rows):
    families = {family: {"requested": 0, **dict.fromkeys(STATUSES, 0), "groups": 0} for family in ("identity_linkage", "reported_measurement")}
    components, groups = [], defaultdict(list)
    for f in task["fields"]:
        status = classify(rows[f["record_key"]], f["field"], f["family"])
        families[f["family"]]["requested"] += 1
        families[f["family"]][status] += 1
        item = {"record_key": f["record_key"], "field": f["field"], "family": f["family"], "group": f["group"], "status": status}
        components.append(item)
        groups[(f["family"], f["group"], f["record_key"])].append(item)
    measurements = []
    for (family, group, record_key), items in groups.items():
        families[family]["groups"] += 1
        if family == "reported_measurement":
            measurements.append({"group": group, "record_key": record_key, "requested_components": len(items),
                                 **{status + "_components": sum(i["status"] == status for i in items) for status in STATUSES}})
    return {"definition": "Literal Task-field availability at the original physical record; no output accuracy or biological validity label.",
            "families": families, "field_statuses": components, "measurement_groups": measurements}


def equality_groups(cases):
    values = defaultdict(list)
    for case in cases:
        for record in case["native_records"]:
            for field, native in record["native_identity"].items():
                if native["status"] == "answerable" and type(native["value"]) is str:
                    values[(field, native["value"])].append({"case_id": case["case_id"], "record_key": record["record_key"],
                        "table_family": record["table_family"], "source_id": record["source"]["source_id"], "locator": record["source"]["locator"]})
    result = []
    for (field, native), members in sorted(values.items()):
        if len(members) < 2:
            continue
        result.append({"relationship_id": "equal-string:" + a.sha(a.wire([field, native])), "field": field, "native_string": native,
                       "members": members, "relationship": "exact native string equality within the same named field only",
                       "study_or_cohort_identity": "not_established", "independence_implication": "not_established"})
    return result


def aggregate(cases, overlaps):
    families = {family: {"requested": 0, **dict.fromkeys(STATUSES, 0), "groups": 0} for family in ("identity_linkage", "reported_measurement")}
    histogram = Counter()
    for case in cases:
        for family, counts in case["denominators"]["families"].items():
            for key, value in counts.items():
                families[family][key] += value
        histogram.update(str(g["answerable_components"]) for g in case["denominators"]["measurement_groups"])
    return {"technical_source_units": len(cases), "physical_source_records": sum(len(c["native_records"]) for c in cases),
            "exposure_status_counts": dict(Counter(c["exposure"]["status"] for c in cases)), "families": families,
            "measurement_group_answerable_component_histogram": dict(sorted(histogram.items())),
            "equal_string_group_counts_by_field": dict(Counter(g["field"] for g in overlaps)),
            "cross_case_equal_string_groups": sum(len({m["case_id"] for m in g["members"]}) > 1 for g in overlaps),
            "independent_studies": "not_established", "study_ready": False}


def native_case_summary(case):
    families = case["denominators"]["families"]
    groups = case["denominators"]["measurement_groups"]
    return {"case_id": case["case_id"], "task_sha256": case["task_sha256"],
            "requested_facts": sum(counts["requested"] for counts in families.values()),
            "measurement_answerable_facts": families["reported_measurement"]["answerable"],
            "measurement_answerable_groups": sum(g["answerable_components"] > 0 for g in groups),
            "measurement_fully_answerable_groups": sum(g["answerable_components"] == g["requested_components"] for g in groups),
            "technical_measurement_groups": len(groups), "family_counts": families}


def build(output):
    import pyarrow
    import pyarrow.parquet as pq
    started = time.monotonic()
    deadline = started + 1200
    public_path = ASSETS / "REGISTER-MANIFEST-v1.json"
    a.require("public_manifest_fresh", not public_path.exists())
    a.require("fresh_approved_ignored_output", output.is_absolute() and output.parent == PARENT and re.fullmatch(PREFIX + r"\d{8}T\d{6}Z", output.name) is not None and not output.exists() and a.checked_path(ROOT, PARENT.relative_to(ROOT).as_posix()) == PARENT and subprocess.run(["git", "check-ignore", "--quiet", "--", str(output)], cwd=ROOT).returncode == 0)
    journal = RunJournal(output, kind="build")
    stage = "freeze_configuration"
    def publish(name, value=None, *, payload=None):
        data = payload if payload is not None else a.wire(value) + b"\n"
        if time.monotonic() >= deadline:
            raise TimeoutError("Register deadline exceeded")
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) + len(data) > 128 * 1024**2:
            raise ValueError("Register output bound exceeded")
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        a.checked_path(ROOT, target.parent.relative_to(ROOT).as_posix())
        publish_bytes(target, data)
    try:
        names = ["p05-" + str(i).zfill(2) + ".task.json" for i in range(1, 13)] + ["source-snapshot.json", "selected-case-plan.json"]
        neutral_paths = [TASKS / "SEAL.json"] + [TASKS / n for n in names]
        code_paths = sorted((ROOT / "src/asof").rglob("*.py")) + [ASSETS / "audit_source_registry_v3.py", ASSETS / "audit_source_inputs_v1.py", Path(__file__).resolve()]
        guard_paths = [p for p, h in PINS.values()] + neutral_paths + code_paths
        with a.stable_files(guard_paths, deadline=deadline):
            docs = {}
            for k, (path, pin) in PINS.items():
                a.require("neutral_metadata_pin_" + k, a.sha(path.read_bytes()) == pin)
                docs[k] = a.document(path)
            neutral_seal = a.document(TASKS / "SEAL.json")
            a.require("neutral_seal_pin", a.sha((TASKS / "SEAL.json").read_bytes()) == s.NEUTRAL_SEAL_SHA and neutral_seal["source_row_values_copied"] is False and neutral_seal["measurement_expected_values"] is False)
            a.require("neutral_exact_inventory", len(neutral_seal["items"]) == 14 and {x["path"] for x in neutral_seal["items"]} == set(names))
            for item in neutral_seal["items"]:
                payload = (TASKS / item["path"]).read_bytes()
                a.require("neutral_query_pin_" + item["path"], a.sha(payload) == item["sha256"] and len(payload) == item["bytes"])
            neutral = {name: a.document(TASKS / name) for name in names}
            routing = neutral["selected-case-plan.json"]
            cases = routing["cases"]
            a.require("fixed_routing_order_and_policy", [c["case_id"] for c in cases] == ["p05-" + str(i).zfill(2) for i in range(1, 13)] and routing["no_replacement"] is True and routing["numeric_availability_used"] is False and all(c["unit_hash"] == a.identity_hash(c["release_id"], (c["targetId"], c["diseaseId"], c["studyLocusId"])) for c in cases))
            originals = a.inventory(docs["frame"], docs["acquisition"])
            frame_hash = a.sha(a.wire(originals))
            a.require("original_frame_exact", len(originals) == 137 and frame_hash == "18fe8042718ca9c10a98a79e2bc23d3e46904b69d60a0c9cdc1dc32afaca5f8c")
            for i, r in enumerate(originals):
                r["source_id"] = "original-" + str(i).zfill(3)
            config = {"schema_version": 1, "method": METHOD, "authorization": "explicit root source-only register task", "role": "evaluation_only", "agent_visible": False,
                      "cutoff": s.CUTOFF, "raw_root": str(RAW), "neutral_task_seal_sha256": s.NEUTRAL_SEAL_SHA,
                      "routing_sha256": a.sha((TASKS / "selected-case-plan.json").read_bytes()), "frame_descriptor_sha256": frame_hash,
                      "original_files": len(originals), "native_identity_fields": list(FIELDS), "known_development_symbols_excluded": sorted(a.EXPOSED),
                      "other_case_exposure": "UNKNOWN", "selection_changes": False, "outputs_or_labels": "not_created",
                      "denominator_policy": "original Task-field answerable/null/absent/empty/invalid counts and physical-record groups; no expected numeric values retained",
                      "dependence_policy": "same-field exact native string equality only; no study/cohort/article/family resolution or independence inference",
                      "environment": {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(), "pyarrow": pyarrow.__version__, "platform": sys.platform},
                      "code_sha256": {p.relative_to(ROOT).as_posix(): a.sha(p.read_bytes()) for p in code_paths},
                      "limits": {"seconds": 1200, "output_bytes": 134217728, "original_files": 137, "fresh_compressed_original_bytes": 4294967296},
                      "model_calls": 0, "network_calls": 0, "new_downloads": 0, "generation_packets_or_reference_values_read": False}
            publish("configuration.json", config)
            recipe = []
            for i, path in enumerate(guard_paths):
                payload = path.read_bytes()
                rel = "_private/recipe/" + str(i).zfill(3) + "-" + path.name
                publish(rel, payload=payload)
                recipe.append({"logical_path": path.relative_to(ROOT).as_posix(), "archive_path": rel, "sha256": a.sha(payload), "bytes": len(payload)})
            stage = "all_original_hashes_and_receipts_before_values"
            journal.append("build_stage", stage=stage)
            paths = [a.checked_path(RAW, r["relative_path"]) for r in originals] + [Path(r["receipt"]["path"]) for r in originals]
            with a.stable_files(paths, deadline=deadline):
                hash_started = time.monotonic()
                for r in originals:
                    a.require("original_approved_path_" + r["source_id"], a.checked_path(RAW, r["relative_path"]) == Path(r["path"]))
                    a.require("original_hash_" + r["source_id"], dict(a.hash_file(r["path"], deadline)) == {"sha256": r["sha256"], "bytes": r["bytes"]})
                nodes, proofs = [], []
                for r in originals:
                    payload = Path(r["receipt"]["path"]).read_bytes()
                    receipt = json.loads(payload)
                    observed = utc(receipt["completed_at_utc"])
                    rel = Path(r["receipt"]["path"]).relative_to(RAW).as_posix()
                    archive = "_private/receipts/" + r["receipt"]["sha256"] + ".json"
                    a.require("receipt_identity_time_" + r["source_id"], a.sha(payload) == r["receipt"]["sha256"] and len(payload) == r["receipt"]["bytes"] and observed <= utc(s.CUTOFF) and receipt["status"] == "completed" and receipt["dataset_id"] == r["dataset_id"] and receipt["release_id"] == r["release_id"] and receipt["sha256"] == r["sha256"] and type(receipt["bytes"]) is int and receipt["bytes"] == r["bytes"] and receipt["url"] == r["source_url"] and receipt["relative_path"].replace("\\", "/") == r["relative_path"])
                    publish(archive, payload=payload)
                    availability = Availability(None, None, None, None, observed.date(), "public_download_receipt", "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, r["receipt"]["sha256"])
                    role = "reference" if r["family"] == "hgnc" else "agent_evidence"
                    n = SourceNode(r["source_id"], r["dataset_id"], r["release_id"], r["relative_path"], r["sha256"], role, availability, TemporalClass.CONTEMPORARY, r["source_url"], receipt_path=rel, receipt_sha256=r["receipt"]["sha256"])
                    nodes.append(n)
                    proofs.append({"source_id": r["source_id"], "family": r["family"], "relative_path": r["relative_path"], "sha256": r["sha256"], "bytes": r["bytes"], "release_id": r["release_id"], "receipt_path": rel, "receipt_sha256": r["receipt"]["sha256"], "receipt_bytes": r["receipt"]["bytes"], "receipt_archive": archive})
                cutoff = utc(s.CUTOFF)
                snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(RAW), {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
                graph = InputGraph(snapshot, output, catalog_index(docs["catalog"]))
                a.require("full_original_role_graph_chronology", s.same(encode(snapshot), neutral["source-snapshot.json"]) and graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=cutoff)) is None)
                REPORT["cost"]["original_hash_and_receipt_seconds"] = time.monotonic() - hash_started
                journal.append("all_originals_admitted_before_values", files=len(originals), original_bytes=sum(r["bytes"] for r in originals))
                stage = "fresh_original_register_projection"
                journal.append("build_stage", stage=stage)
                indexes = a.load_mappings(originals)
                selected, excluded = s.source_selected(originals, cases, indexes, cutoff)
                register_cases = []
                source_by_id = {r["source_id"]: r for r in originals}
                for case in cases:
                    cid = case["case_id"]
                    task = neutral[cid + ".task.json"]
                    groups = selected[cid]
                    a.require("unchanged_original_task_" + cid, s.same(task, s.expected_task(case, groups)))
                    rows = {request["record_key"]: r["values"] for request, r in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])}
                    symbol = indexes["target"][case["targetId"]][0]["values"]["approvedSymbol"]
                    a.require("development_exclusion_and_canonical_mapping_" + cid, symbol not in a.EXPOSED and all(len(indexes[k][case["targetId"] if k != "disease" else case["diseaseId"]]) == 1 for k in ("target", "hgnc", "disease")))
                    records = []
                    for request, original in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"]):
                        src = source_by_id[original["source_id"]]
                        records.append({"record_key": request["record_key"], "table_family": original["family"], "role": "evaluation_only", "agent_visible": False,
                            "source": {"source_id": src["source_id"], "release_id": src["release_id"], "sha256": src["sha256"], "relative_path": src["relative_path"], "locator": original["locator"], "physical_row_0based": original["physical_row_0based"]},
                            "native_identity": native_identity(original["values"])})
                    register_cases.append({"case_id": cid, "role": "evaluation_only", "agent_visible": False, "task_sha256": a.sha(a.wire(task)), "routing_unit_hash": case["unit_hash"],
                        "native_records": records, "exposure": {"status": "UNKNOWN", "canonical_original_symbol": symbol, "known_development_symbol_match": False, "reason": "Nine known development symbols are excluded; other prior exposure is unknown, with no freshness or unexposed claim."},
                        "unresolved_identity": {name: {"value": None, "unknown_reason": "not_established_from_literal_source_identifiers"} for name in ("independent_study", "cohort", "article", "evidence_family")},
                        "native_study_variant_policy": "Identifiers remain separate by original table; equal strings alone do not resolve study, variant, cohort or family identity.",
                        "denominators": denominator(task, rows), "excluded_locators": excluded[cid]})
                overlaps = equality_groups(register_cases)
                summary = aggregate(register_cases, overlaps)
                register = {"schema_version": 1, "status": "FROZEN", "method": METHOD, "role": "evaluation_only", "agent_visible": False, "computed_at": datetime.now(timezone.utc).isoformat(), "information_cutoff": s.CUTOFF,
                    "case_ids": [c["case_id"] for c in register_cases], "other_exposure": "UNKNOWN", "independent_studies_established": False,
                    "native_cases": [native_case_summary(c) for c in register_cases],
                    "measurement_answerable_group_definition": "at least one requested native measurement component is answerable; fully answerable groups counted separately",
                    "parents": [{"kind": "original", "source_id": n.source_id, "sha256": n.sha256} for n in nodes] + [{"kind": "neutral_config", "sha256": a.sha(a.wire(config))}, {"kind": "neutral_routing", "sha256": config["routing_sha256"]}, {"kind": "neutral_task_seal", "sha256": s.NEUTRAL_SEAL_SHA}],
                    "cases": register_cases, "literal_equal_string_groups": overlaps, "summary": summary,
                    "generation_use": "forbidden; source-generation packets were already sealed and may not consume evaluator metadata", "scientific_validation": "not_established", "study_ready": False}
                publish("register.json", register)
                publish("source-snapshot.json", encode(snapshot))
                publish("original-inventory-proofs.json", proofs)
                publish("lineage.json", {"role": "evaluation_only", "agent_visible": False, "parents": register["parents"], "recipe": recipe, "evaluation_or_generation_value_ancestors": [], "original_nodes": encode(nodes)})
                stage = "reread_all_retained_original_records_and_equality"
                journal.append("build_stage", stage=stage)
                saved = a.document(output / "register.json")
                validation_cases = []
                rows_verified = 0
                for case in saved["cases"]:
                    task = neutral[case["case_id"] + ".task.json"]
                    reread_rows = {}
                    for record in case["native_records"]:
                        src = source_by_id[record["source"]["source_id"]]
                        loc = record["source"]["locator"]
                        p = pq.ParquetFile(src["path"])
                        table = p.read_row_group(loc["row_group"], columns=s.projected(src), use_threads=False)
                        a.observe(table)
                        row = table.slice(loc["row"], 1).to_pylist()[0]
                        expected_physical = sum(p.metadata.row_group(g).num_rows for g in range(loc["row_group"])) + loc["row"]
                        a.require("reread_native_record_" + case["case_id"] + "_" + record["record_key"], s.same(record["native_identity"], native_identity(row)) and record["source"]["sha256"] == src["sha256"] and record["source"]["release_id"] == src["release_id"] and record["source"]["relative_path"] == src["relative_path"] and record["source"]["physical_row_0based"] == expected_physical and record["role"] == "evaluation_only" and record["agent_visible"] is False)
                        reread_rows[record["record_key"]] = row
                        rows_verified += 1
                    a.require("reread_denominators_" + case["case_id"], s.same(case["denominators"], denominator(task, reread_rows)))
                    validation_cases.append(case)
                fresh_overlaps = equality_groups(validation_cases)
                a.require("complete_literal_equality_and_summary_reread", s.same(saved["literal_equal_string_groups"], fresh_overlaps) and s.same(saved["summary"], aggregate(validation_cases, fresh_overlaps)) and rows_verified == summary["physical_source_records"] == 24)
                a.require("runner_denominator_interface_exact", s.same(saved["native_cases"], [native_case_summary(c) for c in validation_cases]) and saved["status"] == "FROZEN" and saved["case_ids"] == [c["case_id"] for c in cases] and saved["other_exposure"] == "UNKNOWN" and saved["independent_studies_established"] is False)
                a.require("frozen_per_case_family_denominators", all(all(sum(counts[k] for k in STATUSES) == counts["requested"] for counts in c["denominators"]["families"].values()) for c in saved["cases"]) and len(saved["cases"]) == 12 and saved["study_ready"] is False)
                REPORT["source_reread_validation"] = {"physical_records": rows_verified, "all_literal_identities": True, "all_original_denominators": True, "complete_equal_string_groups": True}
                publish("validation.json", {"role": "evaluation_only", "agent_visible": False, **REPORT})
        resources = {"wall_seconds": time.monotonic() - started, **REPORT["cost"], "logical_original_and_receipt_bytes_hashed": sum(r["bytes"] + r["receipt"]["bytes"] for r in originals),
                     "logical_original_compressed_bytes_scanned": sum(r["bytes"] for r in originals), "selected_original_records_reread": rows_verified, "physical_io_bytes": None, "physical_io_status": "not_measured",
                     "model_calls": 0, "network_calls": 0, "new_downloads": 0, "enforcement": "cooperative checkpoints; no hard OS watchdog"}
        publish("resource-report.json", resources)
        artifacts = [{"path": p.relative_to(output).as_posix(), **dict(a.hash_file(p, deadline))} for p in sorted(output.rglob("*")) if p.is_file() and p.name != "journal.jsonl"]
        seal = {"schema_version": 1, "status": "sealed_source_metadata_register", "role": "evaluation_only", "agent_visible": False, "study_ready": False,
                "register_sha256": a.sha((output / "register.json").read_bytes()), "artifacts": artifacts, "original_parent_count": 137, "technical_source_units": 12,
                "source_mutations": 0, "model_calls": 0, "network_calls": 0, "journal_prefix_sha256": journal.events[-1]["sha256"], "validity_requires": "terminal build_completed binding seal; no failure-seal.json"}
        journal.append("build_completed", seal_sha256=a.sha(a.wire(seal)), register_sha256=seal["register_sha256"], study_ready=False)
        journal.close()
        publish("seal.json", seal)
        public = {"schema_version": 1, "status": "FROZEN", "artifact_kind": "SEALED_EVALUATOR_ONLY_METADATA_REGISTER", "role": "evaluation_only", "agent_visible": False, "study_ready": False,
                  "output": output.relative_to(ROOT).as_posix(), "seal_sha256": a.sha((output / "seal.json").read_bytes()), "register_sha256": seal["register_sha256"], "configuration_sha256": a.sha((output / "configuration.json").read_bytes()),
                  "register_path": (output / "register.json").relative_to(ROOT).as_posix(), "case_ids": register["case_ids"], "other_exposure": "UNKNOWN", "independent_studies_established": False,
                  "native_cases": register["native_cases"], "measurement_answerable_group_definition": register["measurement_answerable_group_definition"],
                  "builder_sha256": a.sha(Path(__file__).read_bytes()), "neutral_task_seal_sha256": s.NEUTRAL_SEAL_SHA, "original_parent_count": 137, "summary": summary,
                  "per_case_family_counts": {c["case_id"]: c["denominators"]["families"] for c in register_cases}, "validation": REPORT["source_reread_validation"], "checks": len(REPORT["checks"]), "issues": REPORT["issues"],
                  "resources": resources, "source_rule": "fresh originals plus neutral task/routing/config only; no packet/reference values", "model_calls": 0, "network_calls": 0, "new_downloads": 0}
        publish_bytes(public_path, a.wire(public) + b"\n")
        return public
    except BaseException as error:
        try:
            journal.fail(error, stage)
        except BaseException:
            pass
        try:
            journal.close()
        except BaseException:
            pass
        failure = {"schema_version": 1, "status": "failed_partial_register_not_usable", "stage": stage, "error_class": type(error).__name__, "role": "evaluation_only", "agent_visible": False, "study_ready": False, "model_calls": 0, "network_calls": 0}
        publish_bytes(output / "failure-seal.json", a.wire(failure) + b"\n")
        if not public_path.exists():
            publish_bytes(public_path, a.wire({**failure, "output": output.relative_to(ROOT).as_posix()}) + b"\n")
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    output = args.output or PARENT / (PREFIX + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    result = build(output.absolute())
    print(json.dumps({"status": result["status"], "output": result["output"], "seal_sha256": result["seal_sha256"], "register_sha256": result["register_sha256"], "summary": result["summary"], "checks": result["checks"], "resources": result["resources"]}))


if __name__ == "__main__":
    main()
