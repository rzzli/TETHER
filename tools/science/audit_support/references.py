"""Selected source-audit helpers; see PROVENANCE.md for scope and origin."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
import re
from . import inputs as s
from . import registry as a
REPORT = a.REPORT


PLAN_SHA = "f8dbfd218f99fb2d694b78b606cb7d183fd267639159e0895c1bafb93741617b"


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
    from tether_engine.study.source_fact_sources import FIELD_FAMILIES
    snapshot_policy = json.loads(a.wire(snapshot))
    snapshot_policy["raw_root"] = None
    return {"schema_version": 1, "task_id": task["task_id"], "task_sha256": task_hash, "role": "evaluation_only", "agent_visible": False,
            "scope": task["scope"], "cutoff": task["cutoff"], "profile": task["profile"], "primary_families": task["primary_families"],
            "collection": task["collection"], "facts": facts, "joins": joins, "source_proofs": proofs,
            "method": {"code_id": "tether_engine.study.source_fact_sources", "version": "1", "transform": "literal_field.v1", "task": task,
                       "json_read_max_bytes": 67108864, "field_family_map_sha256": a.sha(a.wire(FIELD_FAMILIES)), "scientific_validation": "not_established",
                       "linked_measurement_scope": "source_locus_only", "catalog_sha256": a.sha(a.wire({x["dataset_id"]: x for x in catalog["datasets"]})),
                       "source_snapshot_sha256": a.sha(a.wire(snapshot_policy)), "deny_policy": {"source_ids": [], "dataset_ids": [], "sha256": []}, "projection_wire_verified": True}}
