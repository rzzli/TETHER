"""Independent installed P09 source-inclusive reconstruction audit.

Expected native values come from complete original payloads and neutral Tasks.
No producer policy, baseline, controls, prior expected-reference value or dynamic
old-tool import is used. Selected source/reference values stay in memory. This
version ports the independently authored P05 audit algorithms, not its producer.
Core contracts, provenance, canonical encoding, field taxonomy and stable reads
remain explicit shared software dependencies; scientific validation is separate.
"""
from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import ctypes
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import sys
import time
from types import SimpleNamespace

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index
from asof.serde import ContractError, decode, encode
from asof.study.source_fact_sources import FIELD_FAMILIES
from asof.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files

METHOD = "p09.independent_source_inclusive_reconstruction_audit.v1"
CUTOFF = "2026-11-01T07:16:26.101448+00:00"
CASES = tuple("p05-" + str(i).zfill(2) for i in range(1, 13))
SCENARIOS = tuple(["C" + str(i).zfill(2) for i in range(1, 5)] + ["F" + str(i).zfill(2) for i in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
FAMILIES = ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")
STAGES = ("G0", "G1", "G2", "G3", "G4")
GUARDS = ("evidenceDate", "publicationDate", "publicationYear", "releaseDate", "releaseVersion")
EXPOSED = {"CD276", "OSMR", "ERBB2", "PCSK9", "IL6R", "CFTR", "GLP1R", "SCN9A", "CTLA4"}
GWAS = ("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")
IDENTITY = ("studyLocusId", "studyId", "variantId")
MEASURE = ("beta", "standardError", "pValueMantissa", "pValueExponent")
BASE = {"gwas_credible_sets": ("id", "targetId", "diseaseId", "diseaseFromSourceMappedId", "variantId", "studyId", "studyLocusId", "datasourceId", "datatypeId"), "credible_set": IDENTITY + MEASURE + ("chromosome", "position", "sampleSize"), "target": ("id", "approvedSymbol"), "disease": ("id", "name"), "hgnc": ("hgnc_id", "symbol", "ensembl_gene_id", "status")}


def wire(value):
    return json.dumps(encode(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same(left, right):
    return wire(left) == wire(right)


def utc(value):
    if type(value) is not str or "T" not in value:
        raise ContractError("Exact timezone-aware UTC timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError("Timestamp must be explicitly UTC")
    return parsed.astimezone(timezone.utc)


def empty(value):
    return type(value) is str and value == "" or type(value) in (list, dict, tuple) and not value



def good_text(value):
    return type(value) is str and bool(value) and value == value.strip()

def key_of(row):
    key = tuple(row.get(k) for k in ("targetId", "diseaseId", "studyLocusId"))
    return key if all(good_text(v) and "|" not in v for v in key) else None

def identity_hash(release, key):
    return sha("|".join(("preprint-p05-deterministic-v1", release, *key)).encode())

def interval(value, field):
    import re
    if value is None or value == "":
        return None
    if field == "publicationYear" and type(value) is int:
        value = str(value)
    if type(value) is not str or value != value.strip():
        raise ValueError()
    if field == "publicationYear" and re.fullmatch(r"\d{4}", value) is None:
        raise ValueError()
    if re.fullmatch(r"\d{4}", value):
        y = int(value)
        return datetime(y, 1, 1, tzinfo=timezone.utc), datetime(y, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
    if re.fullmatch(r"\d{4}-\d{2}", value):
        y, m = map(int, value.split("-"))
        return datetime(y, m, 1, tzinfo=timezone.utc), datetime(y, m, calendar.monthrange(y, m)[1], 23, 59, 59, 999999, tzinfo=timezone.utc)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        d = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        return d, d.replace(hour=23, minute=59, second=59, microsecond=999999)
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError()
    return t.astimezone(timezone.utc), t.astimezone(timezone.utc)

def dates(row, cutoff):
    reasons, publication, states = [], [], {}
    for field in GUARDS:
        if field not in row:
            states[field] = "schema_absent"
            continue
        if field == "releaseVersion":
            states[field] = "native_annotation_metadata_only"
            continue
        try:
            bounds = interval(row[field], field)
            if bounds is None:
                states[field] = "unknown"
                continue
            low, high = bounds
            status = "explicit_future" if low > cutoff else "date_precision_unverified" if high > cutoff else "within_cutoff"
            states[field] = status
            if field in ("publicationDate", "publicationYear"):
                publication.append(bounds)
            elif status != "within_cutoff":
                reasons.append(field + "_" + status)
        except (ValueError, TypeError, OverflowError):
            states[field] = "invalid_explicit_date"
            reasons.append(field + "_invalid_explicit_date")
    if publication:
        low, high = max(x[0] for x in publication), min(x[1] for x in publication)
        if low > high:
            reasons.append("publication_date_conflict")
        elif low > cutoff:
            reasons.append("publication_explicit_future")
        elif high > cutoff:
            reasons.append("publication_date_precision_unverified")
    return reasons, states

def eligible(row, indexes, cutoff):
    reasons = []
    if key_of(row) is None:
        reasons.append("unit_identity_missing_or_invalid")
    for field, exact in (("datasourceId", "gwas_credible_sets"), ("datatypeId", "genetic_association")):
        if row.get(field) != exact:
            reasons.append(field + "_not_exact")
    targets = indexes["target"].get(row.get("targetId"), [])
    symbol = None
    if len(targets) != 1:
        reasons.append("target_id_missing_or_nonunique")
    else:
        symbol = targets[0]["values"].get("approvedSymbol")
        if not good_text(symbol) or len(indexes["target_symbol"].get(symbol, [])) != 1:
            reasons.append("target_symbol_missing_or_nonunique")
        hgnc = indexes["hgnc"].get(row.get("targetId"), [])
        if len(hgnc) != 1:
            reasons.append("hgnc_ensembl_missing_or_nonunique")
        else:
            h = hgnc[0]["values"]
            if h.get("symbol") != symbol or h.get("status") != "Approved" or not good_text(h.get("hgnc_id")):
                reasons.append("hgnc_exact_symbol_status_or_id_invalid")
            if len(indexes["hgnc_symbol"].get(symbol, [])) != 1 or len(indexes["hgnc_id"].get(h.get("hgnc_id"), [])) != 1:
                reasons.append("hgnc_symbol_or_id_nonunique")
        if symbol in EXPOSED:
            reasons.append("known_exposed_symbol")
    diseases = indexes["disease"].get(row.get("diseaseId"), [])
    if len(diseases) != 1 or not good_text(diseases[0]["values"].get("name")):
        reasons.append("disease_id_or_name_missing_or_nonunique")
    if row.get("diseaseFromSourceMappedId") not in (None, "", row.get("diseaseId")):
        reasons.append("disease_mapped_id_disagreement")
    date_reasons, states = dates(row, cutoff)
    reasons.extend(date_reasons)
    return sorted(reasons), symbol, "known_exposed" if symbol in EXPOSED else "UNKNOWN", states

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
    return all(name not in row or row[name] is None or same(row[name], task["scope"][scope]) for name, scope in (("targetId", "target_id"), ("target_id", "target_id"), ("diseaseId", "indication_id"), ("indication_id", "indication_id")))

def expected_joins(task, rows, nodes):
    """Literal joins and reachability authored independently of the compiler."""
    requests = {r["record_key"]: r for r in task["records"]}
    anchors = {k for k, r in requests.items() if any(r["identity"].get(n) == task["scope"]["target_id"] for n in ("targetId", "target_id")) and any(r["identity"].get(n) == task["scope"]["indication_id"] for n in ("diseaseId", "indication_id"))}
    incoming, reports = defaultdict(list), []
    for j in task["joins"]:
        left = rows[j["left_record"]]
        value = left.get(j["left_field"])
        available = j["left_field"] in left and value is not None and not empty(value)
        matches = [k for k in j["right_records"] if available and j["right_field"] in rows[k] and rows[k][j["right_field"]] is not None and not empty(rows[k][j["right_field"]]) and same(value, rows[k][j["right_field"]])]
        require(all(nodes[requests[k]["source_id"]].release_id == nodes[requests[j["left_record"]]["source_id"]].release_id for k in matches), "Locus join source releases differ")
        # The frozen P05 Tasks explicitly declare locus-only one_to_many joins.
        require(j["cardinality"] == "one_to_many" and j["left_field"] == j["right_field"] == "studyLocusId" and j["inventory_status"] == "complete", "Frozen locus-only join differs")
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
    task_hash = sha(wire(task))
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
        facts.append({"fact_id": "fact:" + sha(wire(identity)), "record_key": key, "field": name, "family": field["family"], "group": field["group"], "value": value, "unit": unit, "source": binding, "unknown_reason": reason})
    # This public type taxonomy is protocol metadata, never an expected-value oracle.
    snapshot_policy = json.loads(wire(snapshot))
    snapshot_policy["raw_root"] = None
    return {"schema_version": 1, "task_id": task["task_id"], "task_sha256": task_hash, "role": "evaluation_only", "agent_visible": False,
            "scope": task["scope"], "cutoff": task["cutoff"], "profile": task["profile"], "primary_families": task["primary_families"],
            "collection": task["collection"], "facts": facts, "joins": joins, "source_proofs": proofs,
            "method": {"code_id": "asof.study.source_fact_sources", "version": "1", "transform": "literal_field.v1", "task": task,
                       "json_read_max_bytes": 67108864, "field_family_map_sha256": sha(wire(FIELD_FAMILIES)), "scientific_validation": "not_established",
                       "linked_measurement_scope": "source_locus_only", "catalog_sha256": sha(wire({x["dataset_id"]: x for x in catalog["datasets"]})),
                       "source_snapshot_sha256": sha(wire(snapshot_policy)), "deny_policy": {"source_ids": [], "dataset_ids": [], "sha256": []}, "projection_wire_verified": True}}

class WireFailure(ValueError):
    pass

def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise WireFailure("Duplicate JSON key: " + key)
        result[key] = value
    return result

def strict_json(raw):
    def invalid_constant(value):
        raise WireFailure("Non-finite JSON number: " + value)
    try:
        return json.loads(raw.decode("utf-8-sig") if type(raw) is bytes else raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WireFailure("Invalid JSON: " + str(exc)) from exc

def text(value, limit=512, blank=False):
    if type(value) is not str or len(value) > limit or not (blank or bool(value.strip())):
        return False
    try:
        value.encode("utf-8")
        return True
    except UnicodeError:
        return False

def require(condition, message):
    if not condition:
        raise WireFailure(message)

def json_value(value):
    stack, count = [(value, 0)], 0
    while stack:
        value, depth = stack.pop()
        count += 1
        require(count <= 4096 and depth <= 16, "Fact JSON bound exceeded")
        if type(value) is str:
            require(text(value, 8192, True), "Invalid fact value string")
        elif type(value) is float:
            require(math.isfinite(value), "Fact value must be finite")
        elif value is None or type(value) in (bool, int):
            pass
        elif type(value) in (list, dict):
            require(len(value) <= 4096, "Fact container bound exceeded")
            if type(value) is dict:
                require(all(text(k, 8192, True) for k in value), "Invalid fact object key")
            stack.extend((v, depth + 1) for v in (value.values() if type(value) is dict else value))
        else:
            raise WireFailure("Fact value must contain native JSON types")

def binding_ok(source):
    if type(source) is not dict or set(source) != {"source_id", "sha256", "release_id", "locator", "field"}:
        return False
    if not all(text(source[k]) for k in ("source_id", "release_id", "field")) or re.fullmatch(r"[a-f0-9]{64}", source["sha256"] or "") is None:
        return False
    loc = source["locator"]
    if type(loc) is not dict:
        return False
    if loc.get("format") == "json":
        return set(loc) == {"format", "pointer"} and text(loc["pointer"], 8192, True) and re.fullmatch(r"(?:/(?:[^~]|~[01])*)*", loc["pointer"]) is not None
    return set(loc) == {"format", "row_group", "row"} and loc["format"] == "parquet" and all(type(loc[k]) is int and loc[k] >= 0 for k in ("row_group", "row"))

def parse_wire(raw, task):
    """Independent typed-facts parser. No adapter or scorer call."""
    try:
        require(type(raw) is bytes and len(raw) <= 262144, "Retained output exceeds 256 KiB")
        doc = strict_json(raw)
        require(type(doc) is dict and set(doc) == {"schema_version", "task_id", "task_sha256", "status", "facts", "collection_status", "reason"}, "Invalid typed-facts output shape")
        require(type(doc["schema_version"]) is int and doc["schema_version"] == 1, "Invalid typed-facts schema version")
        require(doc["task_id"] == task["task_id"] and type(doc["task_id"]) is str and doc["task_sha256"] == sha(wire(task)), "Typed-facts task binding differs")
        status, facts, reason = doc["status"], doc["facts"], doc["reason"]
        require(status in ("answered", "partial", "abstained", "insufficient_input") and type(facts) is list and len(facts) <= 512, "Invalid emitted fact array")
        require(reason is None or text(reason, 1800), "Invalid typed-facts reason")
        require(status == "answered" and bool(facts) and reason is None or status == "partial" and bool(facts) and reason is not None or status in ("abstained", "insufficient_input") and not facts and reason is not None, "Typed-facts status, facts and reason disagree")
        require(doc["collection_status"] in ("selected_records", "zero_matches_selected_collection", "incomplete", "failed_qc"), "Invalid collection disposition")
        for fact in facts:
            require(type(fact) is dict and set(fact) == {"fact_id", "value", "unit", "source", "unknown_reason"}, "Invalid emitted fact shape")
            require(text(fact["fact_id"]), "Invalid fact ID")
            require(fact["unit"] is None or text(fact["unit"]), "Invalid emitted unit")
            json_value(fact["value"])
            require(text(fact["unknown_reason"], 1800) if fact["value"] is None else fact["unknown_reason"] is None, "Emitted value and unknown reason disagree")
            require(binding_ok(fact["source"]), "Invalid complete emitted source binding")
        return {"status": "scorable", "output": doc, "error": None}
    except (WireFailure, TypeError, ValueError, RecursionError, OverflowError) as exc:
        return {"status": "malformed", "output": None, "error": "ContractError: " + str(exc)[:225]}

def fixed_schedule():
    outputs, decisions = [], []
    for case in CASES:
        for arm in ("L", "A"):
            cell = "N-" + arm + "-" + case
            outputs.append({"cell_id": cell, "case_id": case, "arm": arm, "stratum": "native"})
            decisions.extend({"decision_id": "D-" + cell + "-" + p, "output_cell_id": cell, "policy": p} for p in POLICIES if arm == "L" or p == "FULL")
    for key in SCENARIOS:
        cell = "S-" + key
        outputs.append({"cell_id": cell, "case_id": key, "arm": "fixture", "stratum": "fictional_json_core"})
        decisions.extend({"decision_id": "D-" + cell + "-" + p, "output_cell_id": cell, "policy": p} for p in POLICIES)
    return outputs, decisions

def wire_projection(task, facts, *, abstain=False):
    return {"schema_version": 1, "task_id": task["task_id"], "task_sha256": sha(wire(task)),
            "status": "abstained" if abstain else "answered" if facts else "insufficient_input",
            "facts": [] if abstain else [{k: f[k] for k in ("fact_id", "value", "unit", "source", "unknown_reason")} for f in facts],
            "collection_status": task["collection"]["status"], "reason": "Deliberate no-assertion baseline." if abstain else None if facts else "No requested records in the declared bounded collection."}

def independent_score(reference, raw, cell_id, terminal="returned"):
    facts = reference["facts"]
    task = reference["method"]["task"]
    expected = {f["fact_id"]: f for f in facts}
    adapted = parse_wire(raw, task) if terminal == "returned" else {"status": "not_attempted", "output": None, "error": "terminal_" + terminal}
    scorable = adapted["status"] == "scorable"
    output, matched, errors = adapted["output"], set(), []
    eligible = False
    if scorable:
        counts = Counter(f["fact_id"] for f in output["facts"])
        errors.extend({"fact_id": k, "reason": "duplicate_emission"} for k, n in counts.items() if n > 1)
        for fact in output["facts"]:
            old = expected.get(fact["fact_id"])
            if old is None:
                errors.append({"fact_id": fact["fact_id"], "reason": "unknown_fact_id"})
            elif not all(same(fact[k], old[k]) for k in ("value", "unit", "source", "unknown_reason")):
                errors.append({"fact_id": fact["fact_id"], "reason": "value_unit_source_or_unknown_mismatch"})
            elif old["value"] is not None and counts[fact["fact_id"]] == 1:
                matched.add(fact["fact_id"])
        collection_correct = output["collection_status"] == reference["collection"]["status"]
        if not collection_correct:
            errors.append({"fact_id": None, "reason": "collection_status_mismatch"})
        eligible = output["status"] in ("answered", "partial") and collection_correct and not errors
    groups = defaultdict(list)
    for f in facts:
        if f["value"] is not None:
            groups[(f["record_key"], f["family"], f["group"])].append(f["fact_id"])
    family_scores = {}
    for family in FAMILIES:
        selected = {key: ids for key, ids in groups.items() if key[1] == family}
        fractions = {key: Fraction(sum(i in matched for i in ids), len(ids)) for key, ids in selected.items()}
        coverage = sum(fractions.values(), Fraction()) / len(fractions) if fractions and scorable else None
        family_scores[family] = {"answerable_facts": sum(len(ids) for ids in selected.values()), "matched_facts": sum(sum(i in matched for i in ids) for ids in selected.values()) if scorable else None,
            "answerable_groups": len(selected), "group_coverage": [{"record_key": k[0], "group": k[2], "answerable_facts": len(selected[k]), "matched_facts": sum(i in matched for i in selected[k]) if scorable else None, "coverage": float(v) if scorable else None} for k, v in fractions.items()], "coverage": float(coverage) if coverage is not None else None}
    primary = {k: ids for k, ids in groups.items() if k[1] in reference["primary_families"]}
    coverage = sum((Fraction(sum(i in matched for i in ids), len(ids)) for ids in primary.values()), Fraction()) / len(primary) if primary and scorable else None
    passes = {key: bool(eligible and coverage >= value) if coverage is not None else None for key, value in (("60", Fraction(3, 5)), ("80", Fraction(4, 5)), ("100", Fraction(1)))}
    measurement = family_scores["reported_measurement"]
    measurement_groups = {k: ids for k, ids in groups.items() if k[1] == "reported_measurement"}
    measurement_fraction = sum((Fraction(sum(i in matched for i in ids), len(ids)) for ids in measurement_groups.values()), Fraction()) / len(measurement_groups) if measurement_groups and scorable else None
    result = {"schema_version": 1, "cell_id": cell_id, "task_id": reference["task_id"], "task_sha256": reference["task_sha256"], "reference_sha256": sha(wire(reference)),
        "terminal": "malformed" if adapted["status"] == "malformed" else terminal, "received_terminal": terminal, "wire_format": "typed_facts_v1", "adapter_status": adapted["status"], "raw_sha256": sha(raw) if raw is not None else None, "raw_bytes": len(raw) if raw is not None else None,
        "failure_reason": adapted["error"], "critical_errors": errors, "completion": passes["80"] is True, "correct_missing_input": None,
        "answer_status": output["status"] if scorable else None, "emitted_facts": len(output["facts"]) if scorable else None,
        "family_scores": family_scores, "primary": {"families": reference["primary_families"], "answerable_groups": len(primary), "coverage": float(coverage) if coverage is not None else None, "passes": passes},
        "measurement_pass": bool(eligible and measurement_fraction >= Fraction(4, 5)) if measurement_fraction is not None else None, "measurement_answerable_facts": measurement["answerable_facts"], "scientific_validation": "not_established", "provider_spending_incurred": False}
    if not groups:
        result["correct_missing_input"] = bool(scorable and output["status"] == "insufficient_input" and output["collection_status"] == reference["collection"]["status"] and not errors)
    exact = terminal == "returned" and scorable and not errors and output["status"] == "answered" and len(output["facts"]) == len(facts)
    accounting = {}
    for family in FAMILIES:
        selected = [f for f in facts if f["family"] == family]
        counts = Counter(f["fact_id"] for f in output["facts"]) if scorable else Counter()
        correct_unknown = false_assertions = exact_known = 0
        if scorable:
            for fact in output["facts"]:
                old = expected.get(fact["fact_id"])
                if old is None or old["family"] != family:
                    continue
                exact_fact = all(same(fact[k], old[k]) for k in ("value", "unit", "source", "unknown_reason"))
                correct_unknown += old["value"] is None and exact_fact and counts[fact["fact_id"]] == 1
                exact_known += old["value"] is not None and exact_fact and counts[fact["fact_id"]] == 1
                false_assertions += fact["value"] is not None and not exact_fact
        accounting[family] = {"requested": len(selected), "answerable": sum(f["value"] is not None for f in selected), "expected_unknown_by_reason": dict(Counter(f["unknown_reason"] for f in selected if f["value"] is None)), "correct_unknown": correct_unknown if scorable else None, "omitted": sum(counts[f["fact_id"]] == 0 for f in selected) if scorable else None, "matched": exact_known if scorable else None, "false_asserted_values": false_assertions if scorable else None, "false_asserted": false_assertions if scorable else None}
    accounting = {"families": accounting, "unknown_fact_id_emissions": sum(f["fact_id"] not in expected for f in output["facts"]) if scorable else None, "adapter_status": adapted["status"]}
    return result, exact, accounting

def policy_decision(statuses, schema_status, policy):
    required = ("G0",) if policy == "WIRE_ONLY" else ("G0", "G1", "G3", "G4") if policy == "WITHOUT_WRAPPER" else STAGES
    checks = [(stage, statuses[stage]) for stage in required] + ([("G4", schema_status)] if policy == "WIRE_ONLY" else [])
    failed = next((stage for stage, status in checks if status == "rejected"), None)
    missing = any(status not in ("pass", "rejected") for stage, status in checks)
    verdict = "rejected" if failed else "no_decision" if missing else "admitted"
    return {"verdict": verdict, "first_failure_stage": failed, "terminal": "unexecuted" if verdict == "no_decision" else "returned", "required_stages": list(required) + (["G4_schema_only"] if policy == "WIRE_ONLY" else [])}

def fixture_documents(key):
    """Hand-authored byte/truth protocol, independent of fixture producer."""
    require(key in SCENARIOS, "Unknown fixed fictional scenario")
    case = {"case_id": "fiction-" + key, "targetId": "ENSG_FICTIONAL", "diseaseId": "EFO_FICTIONAL", "studyLocusId": "locus-fictional", "release_id": "25.09"}
    gwas = {"id": "fictional-evidence", "targetId": case["targetId"], "diseaseId": case["diseaseId"], "studyLocusId": case["studyLocusId"], "studyId": "STUDY_A", "variantId": "VARIANT_A", "datasourceId": "gwas_credible_sets", "datatypeId": "genetic_association", "publicationDate": "2026-01-01", "evidenceDate": "2026-01-01"}
    credible = {"studyLocusId": case["studyLocusId"], "studyId": "STUDY_A", "variantId": "VARIANT_A", "beta": 1.25, "standardError": 0.25, "pValueMantissa": 2.0, "pValueExponent": -6}
    if key in ("C02", "F07"):
        credible["beta"], credible["pValueMantissa"] = None, ""
        del credible["standardError"]
    if key == "C04":
        credible.update({f: None for f in MEASURE})
    if key == "F03":
        gwas["releaseDate"] = "2026-11-02"
    if key == "F09":
        credible["beta"] = True
    credible_rows = [credible]
    if key in ("C03", "F04"):
        credible_rows.append({**credible, "studyId": "STUDY_B", "variantId": "VARIANT_B", "standardError": -0.5})
    mapping = {"target": [{"values": {"id": case["targetId"], "approvedSymbol": "FICTIONAL_GENE"}, "locator": {}}], "disease": [{"values": {"id": case["diseaseId"], "name": "Fictional phenotype"}, "locator": {}}], "hgnc": [{"values": {"ensembl_gene_id": case["targetId"], "symbol": "FICTIONAL_GENE", "hgnc_id": "HGNC:FICTIONAL", "status": "Approved"}, "locator": {}}]}
    docs = {"gwas": {"rows": [gwas]}, "credible": {"rows": credible_rows}, "mapping": mapping}
    if key == "F02":
        docs["forbidden"] = {"invented": "not a real evaluator artifact"}
    return case, docs

def json_indexes(mapping):
    index = {k: defaultdict(list) for k in ("target", "target_symbol", "disease", "hgnc", "hgnc_symbol", "hgnc_id")}
    for rec in mapping["target"]:
        index["target"][rec["values"].get("id")].append(rec)
        index["target_symbol"][rec["values"].get("approvedSymbol")].append(rec)
    for rec in mapping["disease"]:
        index["disease"][rec["values"].get("id")].append(rec)
    for rec in mapping["hgnc"]:
        for name, field in (("hgnc", "ensembl_gene_id"), ("hgnc_symbol", "symbol"), ("hgnc_id", "hgnc_id")):
            index[name][rec["values"].get(field)].append(rec)
    return index

def json_groups(case, documents, *, eligible_only=False, declared_subset=False):
    result = {"gwas_credible_sets": [], "credible_set": []}
    index = json_indexes(documents["mapping"])
    for name, family in (("gwas", "gwas_credible_sets"), ("credible", "credible_set")):
        values = documents[name]["rows"][:1] if declared_subset and family == "credible_set" else documents[name]["rows"]
        for i, row in enumerate(values):
            if row.get("studyLocusId") != case["studyLocusId"] or family == "gwas_credible_sets" and (row.get("targetId"), row.get("diseaseId")) != (case["targetId"], case["diseaseId"]):
                continue
            reasons = eligible(row, index, utc(CUTOFF))[0] if family == "gwas_credible_sets" else dates(row, utc(CUTOFF))[0]
            if eligible_only and reasons:
                continue
            result[family].append({"source_id": "fiction-" + name, "family": family, "locator": {"format": "json", "pointer": "/rows/" + str(i)}, "physical_row_0based": i, "values": row})
    return result

def projected_facts(task, rows, nodes, *, permit_boolean_measurement=False):
    joins, restrictions = expected_joins(task, rows, nodes)
    facts = []
    records = {rec["record_key"]: rec for rec in task["records"]}
    for field in task["fields"]:
        key, name = field["record_key"], field["field"]
        row, rec = rows[key], records[key]
        node = nodes[rec["source_id"]]
        value = row.get(name)
        reason = restrictions[key]
        if reason is None:
            reason = "field_not_in_schema" if name not in row else "null_source_value" if value is None else "empty_source_value" if empty(value) else None
        if reason is None and field["family"] == "reported_measurement" and not permit_boolean_measurement:
            require(type(value) in (int, float) and (type(value) is not float or math.isfinite(value)) and (name != "pValueExponent" or type(value) is int), "Native measurement type failure")
        source = {"source_id": node.source_id, "sha256": node.sha256, "release_id": node.release_id, "locator": rec["locator"], "field": name}
        identity = {"task_sha256": sha(wire(task)), "scope": task["scope"], "record_key": key, "source": source}
        facts.append({"fact_id": "fact:" + sha(wire(identity)), "record_key": key, "field": name, "family": field["family"], "group": field["group"], "value": None if reason else value, "unit": None, "source": source, "unknown_reason": reason})
    return facts, joins

def candidate_bytes(task, facts, key):
    doc = wire_projection(task, facts)
    if key in ("F05", "F06", "F07"):
        fact = next(f for f in doc["facts"] if f["source"]["field"] == "beta")
        if key == "F05":
            fact["value"] = 2.25
        elif key == "F06":
            fact["source"]["locator"] = {"format": "json", "pointer": "/rows/999"}
        else:
            fact["unknown_reason"] = "field_not_in_schema"
    raw = wire(doc)
    if key == "F08":
        raw = raw[:-1] + b',"status":"answered"}'
    if key == "F10":
        raw += b" " * (262145 - len(raw))
    return raw


class AuditFailure(ContractError):
    pass


class Audit:
    """Bounded, values-free evidence and costs for this audit process only."""
    def __init__(self, deadline):
        deadline_check(deadline)
        self.deadline = deadline
        self.started = time.monotonic()
        self.cpu_started = time.process_time()
        self.report = {"schema_version": 1, "method": METHOD,
            "status": "INCOMPLETE_INDEPENDENT_RECONSTRUCTION_AUDIT", "checks": [],
            "unresolved_findings": [], "source_inclusive": False, "independent_projection": True,
            "scientific_validation": "not_established", "old_private_archive_G0": "unavailable",
            "study_independence": "not_established",
            "model_calls": 0, "network_calls": 0, "new_downloads": 0,
            "producer_policy_baseline_controls_imports": 0, "expected_values_written": False,
            "shared_core_dependencies": ["contracts", "provenance", "serde", "stable_read", "FIELD_FAMILIES"],
            "resources": {"logical_bytes_hashed": 0, "logical_original_compressed_bytes_scanned": 0,
                "physical_io_bytes": None, "original_row_passes": 0, "max_batch_arrow_bytes": 0,
                "peak_sampled_process_rss_bytes": None, "process_lifetime_peak_bytes": None,
                "memory_scope": "audit process only; lifetime peak can predate function; never a producer estimate"}}

    def need(self, label, condition):
        deadline_check(self.deadline)
        self.report["checks"].append({"check": label, "pass": bool(condition)})
        if not condition:
            raise AuditFailure(label)

    def digest(self, path):
        result = dict(hash_file(path, self.deadline))
        cost = self.report["resources"]
        cost["logical_bytes_hashed"] += result["bytes"]
        self.need("audit_hash_budget", cost["logical_bytes_hashed"] <= 512 * 1024**3)
        return result

    def document(self, path, descriptor=None):
        payload = read_file(path, self.deadline, 64 * 1024**2)
        self.report["resources"]["logical_bytes_hashed"] += len(payload)
        if descriptor is not None:
            self.need("exact_document_" + sha(str(path.name).encode())[:12],
                sha(payload) == descriptor["sha256"] and len(payload) == descriptor["bytes"])
        return strict_json(payload)

    def observe(self, batch):
        deadline_check(self.deadline)
        cost = self.report["resources"]
        cost["max_batch_arrow_bytes"] = max(cost["max_batch_arrow_bytes"], batch.nbytes)
        self.sample_memory()

    def sample_memory(self):
        if sys.platform != "win32":
            return
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
                ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        try:
            kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = ctypes.c_void_p
            psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
            psapi.GetProcessMemoryInfo.restype = ctypes.c_int
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return
            cost = self.report["resources"]
            cost["peak_sampled_process_rss_bytes"] = max(cost["peak_sampled_process_rss_bytes"] or 0, counters.WorkingSetSize)
            cost["process_lifetime_peak_bytes"] = counters.PeakWorkingSetSize
            self.need("audit_process_memory_budget", counters.WorkingSetSize <= 2 * 1024**3)
        except (OSError, AttributeError):
            return


def projection_digest(reference):
    """Only the newly authenticated role catalog may differ from old refs."""
    projection = strict_json(wire(reference))
    require("catalog_sha256" in projection["method"], "Reference catalog anchor missing")
    del projection["method"]["catalog_sha256"]
    return sha(wire(projection))


def _columns(item):
    required = BASE[item["family"]]
    require(set(required) <= set(item["fields"]), "Required original columns are missing")
    extras = (("gene_group", "gene_group_id") if item["family"] == "hgnc" else ()
        if item["family"] in ("target", "disease") else
        GUARDS + ("annotationDate", "targetId", "target_id", "diseaseId", "indication_id"))
    return list(required) + [key for key in dict.fromkeys(extras) if key in item["fields"] and key not in required]


def _parquet_batches(item, path, audit):
    import pyarrow.parquet as pq
    source = pq.ParquetFile(path)
    audit.need("native_schema_" + item["source_id"], source.schema_arrow.names == item["fields"] and source.metadata.num_rows == item["rows"])
    physical = 0
    for group in range(source.num_row_groups):
        local = 0
        for batch in source.iter_batches(batch_size=8192, row_groups=[group], columns=_columns(item), use_threads=False):
            audit.observe(batch)
            yield batch, group, local, physical
            local += batch.num_rows
        audit.need("native_row_group_" + item["source_id"] + "_" + str(group), local == source.metadata.row_group(group).num_rows)
        physical += local
    audit.need("native_complete_file_" + item["source_id"], physical == item["rows"])
    audit.report["resources"]["logical_original_compressed_bytes_scanned"] += item["bytes"]


def _mapping_tables(inventory, paths, audit):
    import pyarrow as pa
    import pyarrow.csv as pcsv
    small = {family: [] for family in ("target", "disease", "hgnc")}
    counts = Counter()
    for item in inventory:
        family = item["family"]
        if family not in small:
            continue
        if family == "hgnc":
            with paths[item["source_id"]].open("rb") as stream:
                header = stream.readline(1024**2 + 1)
            audit.need("native_hgnc_header", len(header) <= 1024**2 and header.decode("utf-8-sig").rstrip("\r\n").split("\t") == item["fields"])
            names = _columns(item)
            reader = pcsv.open_csv(paths[item["source_id"]], read_options=pcsv.ReadOptions(block_size=1024**2), parse_options=pcsv.ParseOptions(delimiter="\t"),
                convert_options=pcsv.ConvertOptions(include_columns=names, column_types={name: pa.string() for name in names}, strings_can_be_null=False))
            audit.need("native_hgnc_projection", reader.schema.names == names)
            position = 0
            for batch in reader:
                audit.observe(batch)
                for number, row in enumerate(batch.to_pylist()):
                    small[family].append({"values": row, "locator": {"source_relative_path": item["relative_path"], "source_sha256": item["sha256"],
                        "data_record_0based": position + number, "locator_basis": "TSV parsed data record, header excluded; not a text line number"}})
                position += batch.num_rows
            counts[family] += position
            audit.need("native_hgnc_rows", item["rows"] is None or position == item["rows"])
            audit.report["resources"]["logical_original_compressed_bytes_scanned"] += item["bytes"]
        else:
            for batch, group, offset, physical in _parquet_batches(item, paths[item["source_id"]], audit):
                counts[family] += batch.num_rows
                for number, row in enumerate(batch.to_pylist()):
                    small[family].append({"values": row, "locator": {"source_relative_path": item["relative_path"], "source_sha256": item["sha256"],
                        "row_group_0based": group, "row_in_group_0based": offset + number, "physical_row_0based": physical + offset + number}})
    return json_indexes(small), dict(counts)


def _selected_rows(inventory, paths, cases, indexes, audit):
    import pyarrow as pa
    import pyarrow.compute as pc
    selected = {case["case_id"]: {"gwas_credible_sets": [], "credible_set": []} for case in cases}
    excluded = {case["case_id"]: [] for case in cases}
    by_locus = defaultdict(list)
    for case in cases:
        by_locus[case["studyLocusId"]].append(case)
    locus_set = pa.array(list(by_locus))
    scanned = Counter()
    cutoff = utc(CUTOFF)
    for item in inventory:
        family = item["family"]
        if family not in ("gwas_credible_sets", "credible_set"):
            continue
        for batch, group, offset, physical in _parquet_batches(item, paths[item["source_id"]], audit):
            scanned[family] += batch.num_rows
            hits = pc.indices_nonzero(pc.is_in(batch.column("studyLocusId"), value_set=locus_set)).to_pylist()
            values = batch.take(pa.array(hits, type=pa.int64())).to_pylist()
            for index, row in zip(hits, values):
                for case in by_locus[row["studyLocusId"]]:
                    if family == "gwas_credible_sets" and (row.get("targetId"), row.get("diseaseId")) != (case["targetId"], case["diseaseId"]):
                        continue
                    reasons = eligible(row, indexes, cutoff)[0] if family == "gwas_credible_sets" else dates(row, cutoff)[0]
                    if "annotationDate" in row:
                        try:
                            bounds = interval(row["annotationDate"], "annotationDate")
                            if bounds is not None and bounds[1] > cutoff:
                                reasons.append("annotationDate_" + ("explicit_future" if bounds[0] > cutoff else "date_precision_unverified"))
                        except (ValueError, TypeError, OverflowError):
                            reasons.append("annotationDate_invalid_explicit_date")
                    record = {"source_id": item["source_id"], "family": family,
                        "locator": {"format": "parquet", "row_group": group, "row": offset + index},
                        "physical_row_0based": physical + offset + index, "values": row}
                    cid = case["case_id"]
                    if reasons:
                        excluded[cid].append({"source_id": item["source_id"], "family": family, "locator": record["locator"], "exclusion_reasons": reasons})
                    else:
                        selected[cid][family].append(record)
                    audit.need("native_matching_bound_" + cid, sum(map(len, selected[cid].values())) + len(excluded[cid]) <= 100000)
    return selected, excluded, dict(scanned)


def _policy_shape(policy, audit, full_frame=True):
    audit.need("source_policy_shape", type(policy) is dict and set(policy) == {"schema_version", "method", "cutoff", "inventory", "expected_frame", "catalog", "snapshot", "cases", "tasks", "exposed_symbols", "limits"})
    audit.need("source_policy_version_cutoff", type(policy["schema_version"]) is int and policy["schema_version"] == 1 and policy["method"] == "p09.source_policy.v1" and policy["cutoff"] == CUTOFF)
    inventory, cases = policy["inventory"], policy["cases"]
    audit.need("source_policy_frame_count", type(inventory) is list and (len(inventory) == 137 if full_frame else 0 < len(inventory) <= 137))
    audit.need("source_policy_fixed_cases", [case["case_id"] for case in cases] == list(CASES) and list(policy["tasks"]) == list(CASES))
    audit.need("source_policy_exposure_exclusions", set(policy["exposed_symbols"]) == EXPOSED and len(policy["exposed_symbols"]) == len(EXPOSED))
    audit.need("source_policy_families", set(policy["expected_frame"]) == set(BASE))
    names = []
    for number, item in enumerate(inventory):
        audit.need("native_descriptor_" + str(number), set(item) == {"source_id", "family", "dataset_id", "release_id", "relative_path", "sha256", "bytes", "fields", "rows", "source_url", "role", "receipt"}
            and item["source_id"] == "original-" + str(number).zfill(3) and item["family"] in BASE and item["role"] == ("reference" if item["family"] == "hgnc" else "agent_evidence")
            and type(item["bytes"]) is int and item["bytes"] > 0 and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None
            and type(item["fields"]) is list and len(set(item["fields"])) == len(item["fields"]) and all(good_text(x) for x in item["fields"]))
        receipt = item["receipt"]
        audit.need("native_receipt_descriptor_" + str(number), set(receipt) == {"relative_path", "sha256", "bytes"} and type(receipt["bytes"]) is int and receipt["bytes"] > 0 and re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]) is not None)
        names.extend((item["relative_path"], receipt["relative_path"]))
    audit.need("native_unique_sorted_paths", len(set(x.casefold() for x in names)) == len(names) and [(x["family"], x["relative_path"]) for x in inventory] == sorted((x["family"], x["relative_path"]) for x in inventory))
    audit.need("native_compressed_byte_bound", sum(x["bytes"] for x in inventory) <= 4 * 1024**3)
    for family in BASE:
        items = [x for x in inventory if x["family"] == family]
        expected = policy["expected_frame"][family]
        audit.need("native_frame_totals_" + family, set(expected) == {"files", "bytes", "rows"} and len(items) == expected["files"] and sum(x["bytes"] for x in items) == expected["bytes"]
            and (expected["rows"] is None or sum(x["rows"] for x in items) == expected["rows"]))
    if full_frame:
        audit.need("native_full_family_inventory", {k: v["files"] for k, v in policy["expected_frame"].items()} == {"gwas_credible_sets": 100, "credible_set": 25, "target": 10, "disease": 1, "hgnc": 1})
    for case in cases:
        audit.need("native_selected_identity_" + case["case_id"], set(case) == {"case_id", "targetId", "diseaseId", "studyLocusId", "release_id", "unit_hash"} and key_of(case) is not None and case["unit_hash"] == identity_hash(case["release_id"], key_of(case)))


@contextmanager
def native_projection(policy, originals_root, audit, *, full_frame=True):
    """Fresh complete-file audit, independent physical scan and literal facts."""
    _policy_shape(policy, audit, full_frame)
    inventory, root = policy["inventory"], Path(originals_root).absolute()
    paths = {item["source_id"]: checked_path(root, item["relative_path"]) for item in inventory}
    receipts = {item["source_id"]: checked_path(root, item["receipt"]["relative_path"]) for item in inventory}
    with stable_files(tuple(paths.values()) + tuple(receipts.values()), deadline=audit.deadline):
        nodes, proofs = [], []
        for item in inventory:
            sid = item["source_id"]
            audit.need("native_original_hash_" + sid, audit.digest(paths[sid]) == {"sha256": item["sha256"], "bytes": item["bytes"]})
            payload = read_file(receipts[sid], audit.deadline, 1024**2)
            audit.report["resources"]["logical_bytes_hashed"] += len(payload)
            audit.need("native_exact_receipt_" + sid, sha(payload) == item["receipt"]["sha256"] and len(payload) == item["receipt"]["bytes"])
            receipt = strict_json(payload)
            observed = utc(receipt["completed_at_utc"])
            audit.need("native_receipt_identity_" + sid, all(type(receipt.get(k)) is type(v) and receipt[k] == v for k, v in {"status": "completed", "dataset_id": item["dataset_id"], "release_id": item["release_id"], "sha256": item["sha256"], "bytes": item["bytes"], "url": item["source_url"]}.items())
                and type(receipt.get("relative_path")) is str and receipt["relative_path"].replace("\\", "/") == item["relative_path"] and observed <= utc(CUTOFF))
            availability = Availability(None, None, None, None, observed.date(), "public_download_receipt", "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, item["receipt"]["sha256"])
            node = SourceNode(sid, item["dataset_id"], item["release_id"], item["relative_path"], item["sha256"], item["role"], availability, TemporalClass.CONTEMPORARY, item["source_url"], receipt_path=item["receipt"]["relative_path"], receipt_sha256=item["receipt"]["sha256"])
            nodes.append(node)
            proofs.append({"artifact_id": sid, "dataset_id": node.dataset_id, "release_id": node.release_id, "path": node.path, "sha256": node.sha256, "role": node.role, "parents": [], "bytes": item["bytes"], "availability": encode(availability), "temporal_classification": "contemporary_only", "path_scope": "raw", "receipt_path": node.receipt_path, "receipt_sha256": node.receipt_sha256, "receipt_bytes": item["receipt"]["bytes"]})
        cutoff = utc(CUTOFF)
        snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(root), {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
        audit.need("native_snapshot_root_only_rebase", same(encode(replace(snapshot, raw_root=None)), policy["snapshot"]))
        graph = InputGraph(snapshot, root, catalog_index(policy["catalog"]))
        audit.need("native_original_graph_roles_time", graph.exclusion(tuple(node.source_id for node in nodes), SimpleNamespace(cutoff=cutoff)) is None and all(not n.parents and n.computed_at is None for n in nodes))
        indexes, mapping_counts = _mapping_tables(inventory, paths, audit)
        selected, excluded, row_counts = _selected_rows(inventory, paths, policy["cases"], indexes, audit)
        dispositions, references = {}, {}
        node_map = {node.source_id: node for node in nodes}
        for case in policy["cases"]:
            cid, groups = case["case_id"], selected[case["case_id"]]
            audit.need("native_fixed_anchor_" + cid, bool(groups["gwas_credible_sets"]))
            task = expected_task(case, groups)
            audit.need("native_complete_physical_task_" + cid, same(task, policy["tasks"][cid]))
            audit.need("native_unique_mapping_" + cid, all(len(indexes[k][case["targetId"] if k != "disease" else case["diseaseId"]]) == 1 for k in ("target", "disease", "hgnc")))
            mapping = {"method": "fresh exact original canonical target/HGNC/disease replay", "target_id_from_raw_GWAS": case["targetId"], "indication_id_from_raw_GWAS": case["diseaseId"], "no_alias_or_variant_inference": True,
                "target_original": indexes["target"][case["targetId"]][0], "disease_original": indexes["disease"][case["diseaseId"]][0], "hgnc_original": indexes["hgnc"][case["targetId"]][0], "upstream_namespace_versions": {"target": "unknown", "indication": "unknown"}, "other_exposure": "UNKNOWN"}
            records = groups["gwas_credible_sets"] + groups["credible_set"]
            audit.need("native_selected_release_" + cid, all(node_map[record["source_id"]].release_id == case["release_id"] for record in records))
            rows = {request["record_key"]: record["values"] for request, record in zip(task["records"], records)}
            audit.need("native_strict_scope_dates_" + cid, all(strict_source_guards(row, task) for row in rows.values()))
            references[cid] = direct_reference(task, rows, node_map, proofs, policy["catalog"], encode(snapshot))
            dispositions[cid] = {"status": "ready_for_base_compile", "blocked_reason": None,
                "eligible_inventory": {family: [{"source_id": record["source_id"], "locator": record["locator"]} for record in rows] for family, rows in groups.items()},
                "excluded_inventory": excluded[cid], "neutral_task_sha256": sha(wire(task)), "normalization_sha256": sha(wire(mapping))}
        coverage = {"original_files": len(inventory), "selected_cases": len(policy["cases"]), "mapping_rows": mapping_counts,
            "cases": {cid: {"eligible": {family: len(rows) for family, rows in groups.items()}, "excluded": len(excluded[cid])} for cid, groups in selected.items()}}
        audit.report["resources"]["original_row_passes"] += 1
        audit.report["source_inclusive"] = True
        audit.report["native_physical_row_counts"] = row_counts
        audit.report["mapping_row_counts"] = mapping_counts
        audit.report["originals_verified"] = len(inventory)
        yield {"references": references, "snapshot": snapshot, "source_proofs": proofs, "coverage": coverage, "dispositions": dispositions}


def _control_source_documents(key):
    """Independently specified fictional source bytes, receipts and nodes."""
    case, documents = fixture_documents(key)
    observed = utc("2026-01-01T00:00:00+00:00")
    sources, receipts, nodes, anchors, catalog = {}, {}, [], [], {"schema_version": 1, "datasets": []}
    for name, document in documents.items():
        clean = wire(document) + b"\n"
        sources[name] = clean + (b" " if key == "F01" and name == "gwas" else b"")
        dataset = "fiction_" + name
        role = "evaluation_only" if name == "forbidden" else "reference" if name == "mapping" else "agent_evidence"
        receipt = {"status": "completed", "dataset_id": dataset, "release_id": "25.09", "relative_path": name + ".json",
            "sha256": sha(clean), "bytes": len(clean), "url": "https://example.invalid/" + name, "completed_at_utc": observed.isoformat()}
        receipts[name] = wire(receipt) + b"\n"
        availability = Availability(None, None, None, None, observed.date(), "public_download_receipt", "fictional only", observed, sha(receipts[name]))
        nodes.append(SourceNode("fiction-" + name, dataset, "25.09", name + ".json", sha(clean), role, availability,
            TemporalClass.CONTEMPORARY, receipt["url"], receipt_path=name + ".receipt.json", receipt_sha256=sha(receipts[name])))
        anchors.extend(({"path": name + ".json", "sha256": sha(clean), "bytes": len(clean)},
            {"path": name + ".receipt.json", "sha256": sha(receipts[name]), "bytes": len(receipts[name])}))
        catalog["datasets"].append({"dataset_id": dataset, "roles": [role]})
    generation = Snapshot(2, "fiction-" + key, Profile.CONTEMPORARY, utc(CUTOFF).date(), False, (), tuple(nodes[:3]), None,
        {"scope": "fictional_JSON_only"}, utc(CUTOFF))
    if key == "F02":
        nodes[0] = replace(nodes[0], parents=("fiction-forbidden",), computed_at=observed, method_id="fiction-derived", method_version="1")
    evaluation = replace(generation, sources=tuple(nodes))
    return case, documents, sources, receipts, generation, evaluation, anchors, catalog


def _control_spec_snapshot(spec, name):
    if name == "evaluation_snapshot" and name not in spec and "snapshot" in spec:
        return spec["snapshot"]
    return spec[name]


def audit_control(spec, source_root, raw, audit):
    """Actual source bytes and a distinct fixed recipe determine all guards."""
    key = spec["scenario_id"]
    case, documents, expected_sources, expected_receipts, generation, evaluation, anchors, catalog = _control_source_documents(key)
    root = Path(source_root).absolute()
    audit.need("control_case_" + key, same(spec["case"], case))
    audit.need("control_catalog_" + key, same(spec["catalog"], catalog))
    audit.need("control_source_anchors_" + key, same(spec["original_source_anchors"], anchors))
    snapshots = [("evaluation_snapshot", evaluation)]
    if "generation_snapshot" in spec:
        snapshots.append(("generation_snapshot", generation))
    for name, expected in snapshots:
        declared = _control_spec_snapshot(spec, name)
        audit.need("control_neutral_" + name + "_" + key, declared["raw_root"] is None and same(declared, encode(expected)))
    audit.need("control_root_is_configuration_only_" + key, "originals_root" not in spec or spec["originals_root"] == "fictional/" + key + "/originals")
    required = {name + suffix for name in documents for suffix in (".json", ".receipt.json")}
    audit.need("control_complete_source_inventory_" + key, {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == required)
    paths = [checked_path(root, name) for name in sorted(required)]
    observed_sources, observed_receipts = {}, {}
    with stable_files(paths, deadline=audit.deadline):
        for name in documents:
            observed_sources[name] = read_file(checked_path(root, name + ".json"), audit.deadline, 4 * 1024**2)
            observed_receipts[name] = read_file(checked_path(root, name + ".receipt.json"), audit.deadline, 1024**2)
            audit.need("control_original_bytes_" + key + "_" + name, observed_sources[name] == expected_sources[name])
            audit.need("control_receipt_bytes_" + key + "_" + name, observed_receipts[name] == expected_receipts[name])
        states = dict.fromkeys(STAGES, "unexecuted")
        anchor_map = {x["path"]: x for x in anchors}
        states["G0"] = "pass" if all(sha(observed_sources[n]) == anchor_map[n + ".json"]["sha256"]
            and len(observed_sources[n]) == anchor_map[n + ".json"]["bytes"] for n in documents) else "rejected"
        nodes = {node.source_id: node for node in evaluation.sources}
        if states["G0"] == "pass":
            roles = {x["dataset_id"]: x["roles"] for x in catalog["datasets"]}
            admissible = all(n.role in ("agent_evidence", "reference") and n.role in roles[n.dataset_id]
                and "evaluation_only" not in roles[n.dataset_id] and not n.parents and n.computed_at is None
                and n.availability.known_public_by <= utc(CUTOFF) for n in nodes.values())
            states["G1"] = "pass" if admissible else "rejected"
        groups = json_groups(case, documents, declared_subset=key == "F04")
        task = expected_task(case, groups)
        audit.need("control_independent_neutral_task_" + key, same(spec["task"], task))
        records = groups["gwas_credible_sets"] + groups["credible_set"]
        rows = {request["record_key"]: record["values"] for request, record in zip(task["records"], records)}
        facts, _ = projected_facts(task, rows, nodes, permit_boolean_measurement=True)
        expected_raw = candidate_bytes(task, facts, key)
        audit.need("control_independent_candidate_bytes_" + key, raw == expected_raw)
        reference = None
        if states["G1"] == "pass":
            eligible_groups = json_groups(case, documents, eligible_only=True)
            states["G2"] = "pass" if eligible_groups["gwas_credible_sets"] and same(expected_task(case, eligible_groups), task) else "rejected"
            try:
                require(all(strict_source_guards(row, task) for row in rows.values()), "Control automatic native scope/date differs")
                projected_facts(task, rows, nodes)
                states["G3"] = "pass"
            except (ValueError, TypeError, OverflowError, ContractError):
                states["G3"] = "rejected"
        if states["G3"] == "pass":
            proofs = [{"artifact_id": n.source_id, "dataset_id": n.dataset_id, "release_id": n.release_id, "path": n.path,
                "sha256": n.sha256, "role": n.role, "parents": list(n.parents), "bytes": len(observed_sources[n.source_id.removeprefix("fiction-")]),
                "availability": encode(n.availability), "temporal_classification": "contemporary_only", "path_scope": "raw",
                "receipt_path": n.receipt_path, "receipt_sha256": n.receipt_sha256, "receipt_bytes": len(observed_receipts[n.source_id.removeprefix("fiction-")])} for n in sorted(evaluation.sources, key=lambda node: node.source_id)]
            reference = direct_reference(task, rows, nodes, proofs, catalog, encode(evaluation))
        schema = "pass" if parse_wire(raw, task)["status"] == "scorable" else "rejected"
        score = exact = accounting = None
        if reference is not None:
            score, exact, accounting = independent_score(reference, raw, "S-" + key)
            states["G4"] = "pass" if exact else "rejected"
        return {"task": task, "reference": reference, "core_score": score, "strict_exact_report": exact, "fact_accounting": accounting,
            "states": states, "schema_status": schema, "terminal": "malformed" if schema == "rejected" else "returned",
            "full_source_admitted": all(states[x] == "pass" for x in STAGES[:-1]), "full_verified_exact": all(states[x] == "pass" for x in STAGES),
            "decisions": {p: policy_decision(states, schema, p) for p in POLICIES}}


def analysis_counts(outputs, decisions):
    """Descriptive arithmetic over audited individual cells, never denominators from success."""
    literal = [x for x in outputs if x["stratum"] == "native" and x["arm"] == "L"]
    abstain = [x for x in outputs if x["stratum"] == "native" and x["arm"] == "A"]
    controls = [x for x in outputs if x["stratum"] == "fictional_json_core"]
    mapping = {(x["output_cell_id"], x["policy"]): x for x in decisions}
    counts = {"planned_output_cells": len(outputs), "planned_decisions": len(decisions),
        "output_terminal_counts": dict(Counter(x["terminal"] for x in outputs)),
        "decision_verdict_counts": dict(Counter(x["verdict"] for x in decisions)),
        "core_scored_outputs": sum(x["core_score"] is not None for x in outputs),
        "native_literal": {"cases": len(literal), "verified_exact": sum(x["full_verified_exact"] is True for x in literal),
            **{"complete_" + k: sum(x["core_score"]["primary"]["passes"][k] is True for x in literal) for k in ("60", "80", "100")},
            "critical_errors": sum(len(x["core_score"]["critical_errors"]) for x in literal)},
        "native_abstain": {"cases": len(abstain), "completion_80": sum(x["core_score"]["completion"] is True for x in abstain),
            "emitted_facts": sum(x["core_score"]["emitted_facts"] for x in abstain),
            "critical_errors": sum(len(x["core_score"]["critical_errors"]) for x in abstain)}}
    identity = [x["fact_accounting"]["families"]["identity_linkage"] for x in literal]
    measurements = [x["fact_accounting"]["families"]["reported_measurement"] for x in literal]
    reasons = Counter()
    for x in literal:
        for row in x["fact_accounting"]["families"].values():
            reasons.update(row["expected_unknown_by_reason"])
    counts["native_availability"] = {"identity_requested": sum(x["requested"] for x in identity),
        "identity_answerable": sum(x["answerable"] for x in identity), "measurement_requested": sum(x["requested"] for x in measurements),
        "measurement_answerable": sum(x["answerable"] for x in measurements), "native_nulls": reasons["null_source_value"],
        "absent": reasons["field_not_in_schema"], "empty": reasons["empty_source_value"]}
    valid, invalid = [x for x in controls if x["case_id"].startswith("C")], [x for x in controls if x["case_id"].startswith("F")]
    counts["controls"] = {"scenarios": len(controls), "valid": len(valid), "invalid": len(invalid),
        "invalid_admissions": {p: sum(mapping[(x["cell_id"], p)]["verdict"] == "admitted" for x in invalid) for p in POLICIES},
        "valid_rejections": {p: sum(mapping[(x["cell_id"], p)]["verdict"] == "rejected" for x in valid) for p in POLICIES}}
    counts["paired_control_discordance"] = {p + "__" + q: sum(mapping[(x["cell_id"], p)]["verdict"] != mapping[(x["cell_id"], q)]["verdict"] for x in controls)
        for p, q in (("FULL", "WITHOUT_WRAPPER"), ("FULL", "WIRE_ONLY"), ("WITHOUT_WRAPPER", "WIRE_ONLY"))}
    return counts


def _descriptor_path(root, descriptor, audit):
    audit.need("descriptor_shape", type(descriptor) is dict and {"path", "sha256", "bytes"} <= set(descriptor)
        and re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]) is not None and type(descriptor["bytes"]) is int and descriptor["bytes"] >= 0)
    return checked_path(root, descriptor["path"])


def _verify_files(root, files, audit, prefix):
    audit.need(prefix + "_file_map", type(files) is dict and bool(files))
    for relative, descriptor in files.items():
        audit.need(prefix + "_anchor_shape", type(descriptor) is dict and {"sha256", "bytes"} <= set(descriptor))
        path = checked_path(root, relative)
        audit.need(prefix + "_" + sha(relative.encode())[:16], audit.digest(path) == {k: descriptor[k] for k in ("sha256", "bytes")})


def _journal_and_receipt(root, authority_hash, audit, *, comparison_sha256):
    receipt_raw = read_file(checked_path(root, "receipt.json"), audit.deadline, 64 * 1024**2)
    receipt = strict_json(receipt_raw)
    audit.need("final_receipt_schema_version", same(receipt.get("schema_version"), 1))
    audit.need("final_receipt_protocol", receipt["protocol_sha256"] == authority_hash)
    audit.need("final_receipt_success", receipt["method"] == "p09.reconstruction_receipt.v1" and receipt["operation"] == "reconstruct" and receipt["status"] == "SEALED_SUCCESS")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    audit.need("whole_final_artifact_set", actual == set(receipt["files"]) | {"receipt.json"})
    audit.need("no_failed_reconstruction_seal", not {"failure-seal.json", "failure.json"} & actual)
    _verify_files(root, receipt["files"], audit, "final_receipt")
    raw = read_file(checked_path(root, "reconstruction.json"), audit.deadline, 64 * 1024**2)
    audit.need("final_reconstruction_byte_anchor", sha(raw) == receipt["reconstruction_sha256"])
    reconstruction = strict_json(raw)
    audit.need("reconstruction_schema_version", same(reconstruction.get("schema_version"), 1))
    audit.need("completed_reconstruction_subject", reconstruction["method"] == "p09.source_inclusive_reconstruction.v1"
        and reconstruction["status"] == "COMPLETED_PENDING_AUDIT" and reconstruction["protocol_sha256"] == authority_hash)
    report_scope = {"historical_output_comparison": "all_38_exact_byte_hashes_and_all_90_decisions",
        "historical_archive_integrity": "not_provided_by_public_reconstruction", "scientific_validation": "not_established",
        "source_coverage_path": "source-coverage.json", "model_calls": 0, "network_calls": 0, "new_downloads": 0, "provider_spending_usd": 0}
    audit.need("reconstruction_declared_scope", same({k: reconstruction.get(k) for k in report_scope}, report_scope))
    seal_raw = read_file(checked_path(root, "output-seal.json"), audit.deadline, 64 * 1024**2)
    seal_hash = sha(seal_raw)
    audit.need("new_output_seal_exact_bytes", seal_hash == receipt["output_seal_sha256"] == reconstruction["output_seal_sha256"])
    seal = strict_json(seal_raw)
    audit.need("new_output_seal_schema_version", same(seal.get("schema_version"), 1))
    audit.need("new_output_seal_scope", seal["method"] == "p09.reconstructed_output_seal.v1" and seal["protocol_sha256"] == authority_hash)
    seal_scope = {"comparison_inputs_parsed": False, "model_calls": 0, "scientific_validation": "not_established"}
    audit.need("new_output_seal_declared_scope", same({k: seal.get(k) for k in seal_scope}, seal_scope))
    audit.need("complete_precomparison_artifact_set", set(seal["files"]) == actual - {"receipt.json", "output-seal.json", "journal.jsonl", "reconstruction.json"})
    _verify_files(root, seal["files"], audit, "precomparison_output")
    events = [strict_json(line) for line in read_file(checked_path(root, "journal.jsonl"), audit.deadline, 64 * 1024**2).splitlines()]
    previous = None
    for number, event in enumerate(events):
        audit.need("reconstruction_journal_chain_" + str(number), event["sequence"] == number and event["previous_sha256"] == previous
            and event["sha256"] == sha(wire({k: v for k, v in event.items() if k != "sha256"})))
        previous = event["sha256"]
    sealed = [i for i, event in enumerate(events) if event["event"] == "outputs_sealed"]
    compared = [i for i, event in enumerate(events) if event["event"] == "comparison_started"]
    audit.need("seal_before_evaluation_bridge", len(sealed) == len(compared) == 1 and 0 < sealed[0] < compared[0] < len(events) - 1
        and events[-1]["event"] == "reconstruction_completed" and events[sealed[0]]["details"]["output_seal_sha256"] == seal_hash
        and events[sealed[0] - 1]["sha256"] == seal["journal_prefix_sha256"])
    audit.need("terminal_journal_exact_report_bytes", events[-1]["details"].get("report_sha256") == sha(raw))
    audit.need("comparison_journal_exact_authorized_bytes", events[compared[0]]["details"].get("comparison_sha256") == comparison_sha256)
    audit.report["subject"] = {"reconstruction_sha256": sha(raw), "output_seal_sha256": seal_hash,
        "receipt_sha256": sha(receipt_raw), "protocol_sha256": authority_hash}
    return reconstruction, seal


def _code_pins(protocol, audit):
    import asof
    from . import __file__ as package_init
    packages = (("core_files", Path(asof.__file__).resolve().parent), ("replay_files", Path(package_init).resolve().parent))
    for key, root in packages:
        pins = protocol[key]
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.suffix in (".py", ".json")}
        audit.need("installed_" + key + "_complete_inventory", set(pins) == actual and (len(pins) == 92 if key == "core_files" else bool(pins)))
        for relative, expected in pins.items():
            value = audit.digest(checked_path(root, relative))
            audit.need("installed_" + key + "_" + sha(relative.encode())[:12], value["sha256"] == (expected if type(expected) is str else expected["sha256"]))


def _control_descriptors(document):
    scenarios = document if set(document) == set(SCENARIOS) else document["scenarios"]
    return scenarios if type(scenarios) is dict else {x["scenario_id"]: x for x in scenarios}


def _check_output(row, expected, audit):
    cid = expected["cell_id"]
    for key in ("cell_id", "case_id", "arm", "stratum", "raw_sha256", "raw_bytes", "terminal", "received_terminal",
                "core_score", "fact_accounting", "strict_exact_report", "full_source_admitted", "full_verified_exact"):
        audit.need("independent_output_" + cid + "_" + key, key in row and same(row[key], expected[key]))


def _check_guards(guards, states, schema, cid, audit):
    audit.need("all_five_guards_" + cid, set(guards) == set(STAGES))
    for stage in STAGES:
        audit.need("independent_guard_" + cid + "_" + stage, guards[stage]["status"] == states[stage])
    audit.need("independent_schema_guard_" + cid, guards["G4"]["schema_status"] == schema)


def _independent_outputs(reconstruction, root, native, control_specs, audit):
    planned_outputs, planned_decisions = fixed_schedule()
    actual_outputs, actual_decisions = reconstruction["output_cells"], reconstruction["decision_cells"]
    audit.need("all38_outputs_once_in_order", [{k: x[k] for k in ("cell_id", "case_id", "arm", "stratum")} for x in actual_outputs] == planned_outputs)
    audit.need("all90_decisions_once_in_order", [{k: x[k] for k in ("decision_id", "policy")} for x in actual_decisions] == [{k: x[k] for k in ("decision_id", "policy")} for x in planned_decisions]
        and all("output_cell_id" not in actual or actual["output_cell_id"] == plan["output_cell_id"] for actual, plan in zip(actual_decisions, planned_decisions)))
    audit.need("all38_guard_records", set(reconstruction["guards"]) == {x["cell_id"] for x in planned_outputs})
    expected_outputs, expected_decisions = [], []
    for plan, row in zip(planned_outputs, actual_outputs):
        cid = plan["cell_id"]
        audit.need("fixed_raw_path_" + cid, row["raw_path"] == "raw/" + cid + ".json")
        raw = read_file(checked_path(root, row["raw_path"]), audit.deadline, 524288)
        if plan["stratum"] == "native":
            ref = native["references"][plan["case_id"]]
            task = ref["method"]["task"]
            audit.need("source_only_native_wire_" + cid, raw == wire(wire_projection(task, ref["facts"], abstain=plan["arm"] == "A")))
            score, exact, accounting = independent_score(ref, raw, cid)
            states = {stage: "pass" for stage in STAGES}
            states["G4"] = "pass" if exact else "rejected"
            schema = "pass" if parse_wire(raw, task)["status"] == "scorable" else "rejected"
            result = {"core_score": score, "strict_exact_report": exact, "fact_accounting": accounting,
                "terminal": score["terminal"], "full_source_admitted": True, "full_verified_exact": exact}
        else:
            result = audit_control(control_specs[plan["case_id"]], checked_path(root, "fictional/" + plan["case_id"] + "/originals"), raw, audit)
            states, schema = result["states"], result["schema_status"]
        expected = {**plan, **{k: result[k] for k in ("core_score", "strict_exact_report", "fact_accounting", "terminal", "full_source_admitted", "full_verified_exact")},
            "raw_sha256": sha(raw), "raw_bytes": len(raw), "received_terminal": "returned"}
        _check_output(row, expected, audit)
        _check_guards(reconstruction["guards"][cid], states, schema, cid, audit)
        expected_outputs.append(expected)
        for decision in [x for x in planned_decisions if x["output_cell_id"] == cid]:
            expected_decisions.append({**decision, **policy_decision(states, schema, decision["policy"])})
    for actual, expected in zip(actual_decisions, expected_decisions):
        audit.need("independent_policy_" + expected["decision_id"], all((key == "output_cell_id" and key not in actual) or key in actual and same(actual[key], value) for key, value in expected.items()))
    return expected_outputs, expected_decisions


def _bridge_comparison(bridge, source_policy_hash, reconstruction, native, outputs, decisions, audit):
    audit.need("bridge_evaluator_only", bridge["method"] == "p09.p05_comparison_bridge.v1" and bridge["role"] == "evaluation_only"
        and bridge["agent_visible"] is False and bridge["source_policy_sha256"] == source_policy_hash and bridge["scientific_validation"] == "not_established")
    audit.need("bridge_same12_fixed_units", set(bridge["native"]) == set(CASES))
    for cid, ref in native["references"].items():
        historical = bridge["native"][cid]
        audit.need("native_historical_catalog_only_projection_" + cid, historical["projection_method"] == "remove_only_method_catalog_sha256.v1"
            and historical["task_sha256"] == ref["task_sha256"] and historical["reference_projection_sha256"] == projection_digest(ref))
        measurements = [f for f in ref["facts"] if f["family"] == "reported_measurement" and f["value"] is not None]
        counts = {"requested_facts": len(ref["facts"]), "measurement_answerable_facts": len(measurements), "measurement_answerable_groups": len({(f["record_key"], f["group"]) for f in measurements})}
        audit.need("native_historical_denominator_" + cid, same({k: historical["counts"].get(k) for k in counts}, counts))
        audit.need("native_historical_compiled_binding_" + cid, historical["counts"]["case_id"] == cid and historical["counts"]["disposition"] == "compiled"
            and historical["counts"]["task_sha256"] == ref["task_sha256"] and historical["counts"]["reference_sha256"] == historical["historical_reference_sha256"])
    audit.need("bridge_output_count", len(bridge["outputs"]) == len(outputs))
    audit.need("bridge_exact38_guard_records", set(bridge["guards"]) == {x["cell_id"] for x in fixed_schedule()[0]})
    for expected, historical in zip(outputs, bridge["outputs"]):
        reduced = strict_json(wire(expected))
        if reduced["core_score"] is not None:
            del reduced["core_score"]["reference_sha256"]
        audit.need("historical_output_metadata_" + expected["cell_id"], set(historical) == set(reduced) and same(historical, reduced))
        _check_guards(bridge["guards"][expected["cell_id"]], {x: reconstruction["guards"][expected["cell_id"]][x]["status"] for x in STAGES},
            reconstruction["guards"][expected["cell_id"]]["G4"]["schema_status"], "historical_" + expected["cell_id"], audit)
    audit.need("bridge_decision_count", len(bridge["decisions"]) == len(decisions))
    for expected, historical in zip(decisions, bridge["decisions"]):
        reduced = {k: v for k, v in expected.items() if k != "output_cell_id"}
        audit.need("historical_decision_" + expected["decision_id"], type(historical) is dict and set(historical) == set(reduced) and same(historical, reduced))


def audit_reconstruction(protocol, bundle_root, originals_root, reconstruction_root, deadline):
    """Audit one closed reconstruction, returning values-free PASS/failure evidence.

    protocol is {document, raw_bytes, byte_sha256}. The caller must supply its
    independently retained byte hash. No comparison values define native facts.
    This function writes nothing and never reruns production or selects cases.
    """
    audit = Audit(deadline)
    try:
        audit.need("authority_exact_shape", type(protocol) is dict and set(protocol) == {"document", "raw_bytes", "byte_sha256"})
        raw, pin = protocol["raw_bytes"], protocol["byte_sha256"]
        audit.need("external_protocol_exact_byte_hash", type(raw) is bytes and re.fullmatch(r"[0-9a-f]{64}", pin) is not None and sha(raw) == pin)
        document = strict_json(raw)
        audit.need("protocol_document_not_canonical_byte_substitution", same(document, protocol["document"]))
        audit.need("root_authorized_public_protocol", type(document.get("schema_version")) is int and document["schema_version"] == 1
            and document.get("method") == "p09.public_reconstruction_protocol.v1" and document.get("status") == "READY"
            and document.get("actual_reconstruction_authorized") is True)
        import pyarrow
        expected_environment = {"python": platform.python_version(), "pyarrow": pyarrow.__version__, "platform": sys.platform}
        audit.need("frozen_environment", all(document["environment"].get(k) == v for k, v in expected_environment.items()) and pyarrow.__version__ == "21.0.0" and sys.platform == "win32")
        bundle, root = Path(bundle_root).absolute(), Path(reconstruction_root).absolute()
        bundle_paths = [checked_path(bundle, name) for name in document["files"]]
        result_paths = [p for p in root.rglob("*") if p.is_file()]
        with stable_files(tuple(bundle_paths) + tuple(result_paths), deadline=deadline):
            _verify_files(bundle, document["files"], audit, "protocol_bundle")
            extras = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()} - set(document["files"])
            audit.need("explicit_bundle_allowlist", len(extras) <= 1 and all(read_file(checked_path(bundle, p), deadline, 64 * 1024**2) == raw for p in extras))
            _code_pins(document, audit)
            reconstruction, seal = _journal_and_receipt(root, pin, audit, comparison_sha256=document["comparison"]["sha256"])
            source_path = _descriptor_path(bundle, document["source_policy"], audit)
            controls_path = _descriptor_path(bundle, document["controls"], audit)
            source_policy = audit.document(source_path, document["source_policy"])
            controls = audit.document(controls_path, document["controls"])
            specs = _control_descriptors(controls)
            audit.need("exact14_constructed_descriptors", list(specs) == list(SCENARIOS))
            audit.need("sealed_required_output_inventory", {"raw/" + x["cell_id"] + ".json" for x in fixed_schedule()[0]} |
                {"references/" + cid + ".json" for cid in CASES} | {"source-coverage.json", "control-descriptors.json"} <= set(seal["files"]))
            runtime_controls = audit.document(checked_path(root, "control-descriptors.json"))
            audit.need("same_neutral_constructed_configuration", same(runtime_controls, controls))
            with native_projection(source_policy, originals_root, audit) as native:
                coverage = audit.document(checked_path(root, reconstruction["source_coverage_path"]))
                audit.need("source_coverage_path_fixed", reconstruction["source_coverage_path"] == "source-coverage.json")
                for key in ("source_proofs", "coverage", "dispositions"):
                    audit.need("independent_native_" + key, same(coverage[key], native[key]))
                audit.need("independent_native_scan_counter", coverage["resources"]["logical_original_compressed_bytes_scanned"] == sum(x["bytes"] for x in source_policy["inventory"]))
                audit.need("independent_native_hash_counter", coverage["resources"]["logical_bytes_hashed"] == sum(x["bytes"] + x["receipt"]["bytes"] for x in source_policy["inventory"]))
                audit.need("all12_genuine_native_references", set(reconstruction["native_references"]) == set(CASES))
                for cid, expected in native["references"].items():
                    item = reconstruction["native_references"][cid]
                    audit.need("fixed_new_reference_path_" + cid, item["path"] == "references/" + cid + ".json")
                    actual = audit.document(checked_path(root, item["path"]))
                    audit.need("independent_complete_new_reference_" + cid, same(actual, expected) and item["fingerprint"] == sha(wire(expected)) and item["projection_sha256"] == projection_digest(expected))
                    measurements = [f for f in expected["facts"] if f["family"] == "reported_measurement" and f["value"] is not None]
                    counts = {"requested_facts": len(expected["facts"]), "measurement_answerable_facts": len(measurements), "measurement_answerable_groups": len({(f["record_key"], f["group"]) for f in measurements})}
                    audit.need("independent_new_reference_counts_" + cid, item["task_sha256"] == expected["task_sha256"] and same(item["counts"], counts))
                outputs, decisions = _independent_outputs(reconstruction, root, native, specs, audit)
                measured = analysis_counts(outputs, decisions)
                audit.need("independent_all_cell_descriptive_counts", same(reconstruction["analysis_counts"], measured))
                # Evaluation-only bridge is parsed only after source/individual
                # output reconstruction and exact precomparison seal validation.
                comparison_path = _descriptor_path(bundle, document["comparison"], audit)
                bridge = audit.document(comparison_path, document["comparison"])
                _bridge_comparison(bridge, document["source_policy"]["sha256"], reconstruction, native, outputs, decisions, audit)
                audit.report["analysis_counts"] = measured
                audit.report["native_reference_projection_checks"] = len(native["references"])
            audit.report["status"] = "PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT"
    except Exception as error:
        audit.report["status"] = "FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT"
        audit.report["unresolved_findings"].append(str(error) if isinstance(error, AuditFailure) else "audit_exception_" + type(error).__name__)
    finally:
        try:
            audit.sample_memory()
        except (AuditFailure, TimeoutError):
            audit.report["status"] = "FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT"
            audit.report["unresolved_findings"].append("audit_final_resource_checkpoint")
        audit.report["resources"]["wall_seconds"] = time.monotonic() - audit.started
        audit.report["resources"]["cpu_seconds"] = time.process_time() - audit.cpu_started
        audit.report["check_count"] = len(audit.report["checks"])
    return audit.report
