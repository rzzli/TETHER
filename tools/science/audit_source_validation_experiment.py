"""Independent P05 experiment audit; actual execution requires external pins.

Expected values come from originals and frozen query definitions. This module
does not import the experiment producer, its assembler, selector, compiler or
scorer. Earlier independently authored audit projection code is reused.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "planning/review-assets/preprint-p05-20261031"
spec = importlib.util.spec_from_file_location("independent_p05_reference_audit", ASSETS / "audit_source_references_v1.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
s, a = r.s, r.a
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index
from asof.serde import decode, encode

METHOD = "p05.independent_source_inclusive_experiment_audit.v1"
CASES = tuple("p05-" + str(i).zfill(2) for i in range(1, 13))
SCENARIOS = tuple(["C" + str(i).zfill(2) for i in range(1, 5)] + ["F" + str(i).zfill(2) for i in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
FAMILIES = ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")
STAGES = ("G0", "G1", "G2", "G3", "G4")
TERMINALS = ("returned", "malformed", "failed", "timeout", "interrupted", "unexecuted")
REPORT = {"schema_version": 1, "method": METHOD, "checks": {}, "issues": [], "unresolved_findings": [], "cost": {},
          "source_inclusive": False, "independent_projection": True, "scientific_validation": "not_established",
          "model_calls": 0, "network_calls": 0, "new_downloads": 0, "producer_compiler_or_scorer_calls": 0,
          "raw_scientific_values_written": False}
r.REPORT = s.REPORT = a.REPORT = REPORT


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
        require(doc["task_id"] == task["task_id"] and type(doc["task_id"]) is str and doc["task_sha256"] == a.sha(a.wire(task)), "Typed-facts task binding differs")
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
    return {"schema_version": 1, "task_id": task["task_id"], "task_sha256": a.sha(a.wire(task)),
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
            elif not all(s.same(fact[k], old[k]) for k in ("value", "unit", "source", "unknown_reason")):
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
    result = {"schema_version": 1, "cell_id": cell_id, "task_id": reference["task_id"], "task_sha256": reference["task_sha256"], "reference_sha256": a.sha(a.wire(reference)),
        "terminal": "malformed" if adapted["status"] == "malformed" else terminal, "received_terminal": terminal, "wire_format": "typed_facts_v1", "adapter_status": adapted["status"], "raw_sha256": a.sha(raw) if raw is not None else None, "raw_bytes": len(raw) if raw is not None else None,
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
                exact_fact = all(s.same(fact[k], old[k]) for k in ("value", "unit", "source", "unknown_reason"))
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
        credible.update({f: None for f in s.MEASURE})
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


def json_groups(case, documents, *, eligible=False, declared_subset=False):
    result = {"gwas_credible_sets": [], "credible_set": []}
    index = json_indexes(documents["mapping"])
    for name, family in (("gwas", "gwas_credible_sets"), ("credible", "credible_set")):
        values = documents[name]["rows"][:1] if declared_subset and family == "credible_set" else documents[name]["rows"]
        for i, row in enumerate(values):
            if row.get("studyLocusId") != case["studyLocusId"] or family == "gwas_credible_sets" and (row.get("targetId"), row.get("diseaseId")) != (case["targetId"], case["diseaseId"]):
                continue
            reasons = a.eligible(row, index, r.utc(s.CUTOFF))[0] if family == "gwas_credible_sets" else a.dates(row, r.utc(s.CUTOFF))[0]
            if eligible and reasons:
                continue
            result[family].append({"source_id": "fiction-" + name, "family": family, "locator": {"format": "json", "pointer": "/rows/" + str(i)}, "physical_row_0based": i, "values": row})
    return result


def projected_facts(task, rows, nodes, *, permit_boolean_measurement=False):
    joins, restrictions = r.expected_joins(task, rows, nodes)
    facts = []
    records = {rec["record_key"]: rec for rec in task["records"]}
    for field in task["fields"]:
        key, name = field["record_key"], field["field"]
        row, rec = rows[key], records[key]
        node = nodes[rec["source_id"]]
        value = row.get(name)
        reason = restrictions[key]
        if reason is None:
            reason = "field_not_in_schema" if name not in row else "null_source_value" if value is None else "empty_source_value" if r.empty(value) else None
        if reason is None and field["family"] == "reported_measurement" and not permit_boolean_measurement:
            require(type(value) in (int, float) and (type(value) is not float or math.isfinite(value)) and (name != "pValueExponent" or type(value) is int), "Native measurement type failure")
        source = {"source_id": node.source_id, "sha256": node.sha256, "release_id": node.release_id, "locator": rec["locator"], "field": name}
        identity = {"task_sha256": a.sha(a.wire(task)), "scope": task["scope"], "record_key": key, "source": source}
        facts.append({"fact_id": "fact:" + a.sha(a.wire(identity)), "record_key": key, "field": name, "family": field["family"], "group": field["group"], "value": None if reason else value, "unit": None, "source": source, "unknown_reason": reason})
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
    raw = a.wire(doc)
    if key == "F08":
        raw = raw[:-1] + b',"status":"answered"}'
    if key == "F10":
        raw += b" " * (262145 - len(raw))
    return raw


class Budget:
    def __init__(self, production=None):
        self.started, self.cpu_started = time.monotonic(), time.process_time()
        self.deadline = self.started + 3600
        self.logical_hash_bytes = 0
        self.production = production or {}
        self.rss_peak = self.process_peak = 0
        self.original_row_passes = 0

    def sample(self):
        import ctypes
        from ctypes import wintypes
        class Info(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in ("peak", "rss", "a", "b", "c", "d", "e", "f")]
        info = Info()
        info.cb = ctypes.sizeof(info)
        kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info), wintypes.DWORD]
        require(psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb), "Audit memory bound unqualified: no reading")
        self.rss_peak, self.process_peak = max(self.rss_peak, info.rss), max(self.process_peak, info.peak)
        require(time.monotonic() < self.deadline, "Independent audit deadline exceeded")
        require(max(self.rss_peak, self.process_peak) <= 2 * 1024**3, "Audit memory bound exceeded")
        require(self.logical_hash_bytes + self.production.get("logical_completed_hash_bytes", 0) <= 512 * 1024**3, "Combined completed logical hash budget exceeded")

    def hash(self, path):
        self.sample()
        measured = dict(a.hash_file(path, self.deadline))
        self.logical_hash_bytes += measured["bytes"]
        self.sample()
        return measured

    def report(self):
        return {"wall_seconds": time.monotonic() - self.started, "cpu_seconds": time.process_time() - self.cpu_started,
                "peak_sampled_process_rss_bytes": self.rss_peak, "process_lifetime_peak_bytes": self.process_peak,
                "logical_completed_hash_bytes": self.logical_hash_bytes, "combined_declared_completed_hash_bytes": self.logical_hash_bytes + self.production.get("logical_completed_hash_bytes", 0),
                "original_row_enumeration_passes": self.original_row_passes, "physical_io_bytes": None, "physical_io_status": "not_measured", "memory_basis": "Win32 GetProcessMemoryInfo fallback", "enforcement": "cooperative checkpoints; no hard OS watchdog"}


def proof_documents(nodes, source_bytes, receipt_bytes):
    return [{"artifact_id": n.source_id, "dataset_id": n.dataset_id, "release_id": n.release_id, "path": n.path,
             "sha256": n.sha256, "role": n.role, "parents": list(n.parents), "receipt_path": n.receipt_path,
             "receipt_sha256": n.receipt_sha256, "bytes": len(source_bytes[n.source_id]), "availability": encode(n.availability),
             "temporal_classification": n.temporal_classification.value, "path_scope": "derived" if n.computed_at is not None else "raw",
             "receipt_bytes": len(receipt_bytes[n.source_id])} for n in sorted(nodes, key=lambda n: n.source_id)]


def fixture_evidence(scenario, packet, source_bytes, receipts, raw, *, fixture_root=None):
    """Derive actual fixture validity from bytes; never read an oracle verdict."""
    key = scenario["scenario_id"]
    case, blueprint = fixture_documents(key)
    documents = {name: strict_json(payload) for name, payload in source_bytes.items()}
    require(s.same(case, scenario["case"]), "Fixture case differs from frozen invented protocol")
    require(set(documents) == set(blueprint), "Fixture original file inventory differs")
    for name, expected in blueprint.items():
        require(s.same(documents[name], expected), "Fixture original literal content differs from byte/truth protocol")
        expected_bytes = a.wire(expected) + b"\n" + (b" " if key == "F01" and name == "gwas" else b"")
        require(source_bytes[name] == expected_bytes, "Fixture observed bytes differ from fixed recipe")
    anchors = {x["path"]: x for x in scenario["original_source_anchors"]}
    for name, expected in blueprint.items():
        clean = a.wire(expected) + b"\n"
        require(anchors[name + ".json"] == {"path": name + ".json", "sha256": a.sha(clean), "bytes": len(clean)}, "Fixture clean source anchor was changed")
        receipt = strict_json(receipts[name])
        require(receipt["status"] == "completed" and receipt["relative_path"] == name + ".json" and receipt["sha256"] == a.sha(clean) and receipt["bytes"] == len(clean), "Fixture receipt/source anchor differs")
        require(anchors[name + ".receipt.json"] == {"path": name + ".receipt.json", "sha256": a.sha(receipts[name]), "bytes": len(receipts[name])}, "Fixture receipt anchor differs")
    require(len(anchors) == 2 * len(blueprint), "Duplicate or extra fixture anchors")
    statuses = dict.fromkeys(STAGES, "unexecuted")
    statuses["G0"] = "pass" if all(a.sha(source_bytes[name]) == anchors[name + ".json"]["sha256"] and len(source_bytes[name]) == anchors[name + ".json"]["bytes"] for name in documents) else "rejected"
    nodes = [decode(SourceNode, value) for value in scenario["snapshot"]["sources"]]
    node_map = {n.source_id: n for n in nodes}
    require(len(nodes) == len(node_map), "Duplicate fixture source nodes")
    if fixture_root is not None:
        require(Path(scenario["snapshot"]["raw_root"]) == Path(fixture_root) / key / "originals", "Fixture serialized root exceeds fixed authority")
    if statuses["G0"] == "pass":
        role_ok = set(node_map) == {"fiction-" + name for name in documents}
        catalog = {d["dataset_id"]: d for d in scenario["catalog"]["datasets"]}
        for n in nodes:
            name = n.source_id.removeprefix("fiction-")
            receipt = strict_json(receipts[name])
            product = catalog.get(n.dataset_id, {})
            role_ok &= n.role in ("agent_evidence", "reference") and n.role in product.get("roles", []) and "evaluation_only" not in product.get("roles", [])
            role_ok &= n.path == name + ".json" and n.sha256 == a.sha(source_bytes[name]) and n.receipt_path == name + ".receipt.json" and n.receipt_sha256 == a.sha(receipts[name])
            role_ok &= n.source_url == receipt["url"] and n.dataset_id == receipt["dataset_id"] and n.release_id == receipt["release_id"]
            role_ok &= n.availability.known_public_by == r.utc(receipt["completed_at_utc"]) and n.availability.evidence_ref == n.receipt_sha256 and n.availability.known_public_by <= r.utc(s.CUTOFF)
            role_ok &= not n.parents and n.computed_at is None  # Every legitimate fixture dependency is an original.
        statuses["G1"] = "pass" if role_ok else "rejected"
    declared_groups = json_groups(case, documents, declared_subset=key == "F04")
    declared_task = s.expected_task(case, declared_groups)
    require(s.same(scenario["task"], declared_task) and s.same(packet["neutral_task"], declared_task), "Fixture declared query differs from fixed attempted recipe")
    rawrows = groups_records = declared_groups["gwas_credible_sets"] + declared_groups["credible_set"]
    require(s.same(packet["source_records"], [{"record_key": request["record_key"], **row} for request, row in zip(declared_task["records"], rawrows)]), "Fixture attempted packet rows differ from originals")
    rows = {request["record_key"]: row["values"] for request, row in zip(declared_task["records"], groups_records)}
    candidate_facts, _ = projected_facts(declared_task, rows, node_map, permit_boolean_measurement=True)
    expected_raw = candidate_bytes(declared_task, candidate_facts, key)
    require(raw == expected_raw, "Retained fictional candidate bytes differ from independently authored recipe")
    if statuses["G1"] == "pass":
        eligible = json_groups(case, documents, eligible=True)
        derived = s.expected_task(case, eligible)
        wrapper_ok = bool(eligible["gwas_credible_sets"]) and s.same(derived, declared_task)
        statuses["G2"] = "pass" if wrapper_ok else "rejected"
        try:
            require(all(r.strict_source_guards(row, declared_task) for row in rows.values()), "Strict native source scope/date failure")
            projected_facts(declared_task, rows, node_map)
            statuses["G3"] = "pass"
        except (WireFailure, ValueError, TypeError, OverflowError):
            statuses["G3"] = "rejected"
    reference = None
    if statuses["G3"] == "pass":
        by_id_bytes = {"fiction-" + k: v for k, v in source_bytes.items()}
        by_id_receipts = {"fiction-" + k: v for k, v in receipts.items()}
        proofs = proof_documents(nodes, by_id_bytes, by_id_receipts)
        reference = r.direct_reference(declared_task, rows, node_map, proofs, scenario["catalog"], scenario["snapshot"])
    schema = parse_wire(raw, declared_task)["status"]
    score = exact = accounting = None
    if reference is not None:
        score, exact, accounting = independent_score(reference, raw, "S-" + key)
        statuses["G4"] = "pass" if exact else "rejected"
    schema_status = "pass" if schema == "scorable" else "rejected"
    # Truth is reconstructed from source eligibility plus emitted exactness, not copied from C/F labels.
    truth = "VALID_REPORT" if all(statuses[k] == "pass" for k in STAGES) else "INVALID"
    require((truth == "VALID_REPORT") == key.startswith("C"), "Invented fixture no longer represents its predeclared valid/fault construction")
    return {"task": declared_task, "reference": reference, "score": score, "strict_exact_report": exact, "fact_accounting": accounting,
            "statuses": statuses, "schema_status": schema_status, "truth": truth, "raw_terminal": "malformed" if schema == "malformed" else "returned",
            "full_source_admitted": all(statuses[k] == "pass" for k in STAGES[:-1]),
            "full_verified_exact": all(statuses[k] == "pass" for k in STAGES), "decisions": {p: policy_decision(statuses, schema_status, p) for p in POLICIES}}


def check(name, condition, **details):
    a.check(name, condition, **details)


def need(name, condition, **details):
    a.require(name, condition, **details)


def read_document(path, budget, expected_sha=None, maximum=64 * 1024**2):
    path = Path(path)
    need("bounded_file_" + a.sha(str(path).encode())[:12], path.is_file() and path.stat().st_size <= maximum)
    measured = budget.hash(path)
    if expected_sha is not None:
        need("pinned_file_" + a.sha(str(path).encode())[:12], measured["sha256"] == expected_sha)
    return strict_json(path.read_bytes())


def descriptor(value, budget):
    require(type(value) is dict and type(value.get("path")) is str and re.fullmatch(r"[0-9a-f]{64}", value.get("sha256", "")) is not None, "Pinned descriptor required")
    path = Path(value["path"])
    path = path if path.is_absolute() else ROOT / path
    need("descriptor_inside_workspace_" + a.sha(str(path).encode())[:12], path.is_relative_to(ROOT) and a.checked_path(ROOT, path.relative_to(ROOT).as_posix()) == path)
    return path, read_document(path, budget, value["sha256"])


def verify_seal(directory, seal, budget, *, terminal="build_completed", expected_ledger=None):
    need("no_upstream_failure_" + a.sha(str(directory).encode())[:12], not (directory / "failure-seal.json").exists())
    chain = [strict_json(line) for line in (directory / "journal.jsonl").read_bytes().splitlines()]
    previous = None
    for i, event in enumerate(chain):
        need("chain_" + a.sha(str(directory).encode())[:8] + "_" + str(i), event["sequence"] == i and event["previous_sha256"] == previous and event["sha256"] == a.sha(a.wire({k: v for k, v in event.items() if k != "sha256"})))
        previous = event["sha256"]
    need("terminal_seal_" + a.sha(str(directory).encode())[:12], chain[-1]["event"] == terminal and chain[-1]["details"]["seal_sha256"] == a.sha(a.wire(seal)) and chain[-2]["sha256"] == seal["journal_prefix_sha256"])
    artifacts = seal["artifacts"]
    need("whole_artifact_set_" + a.sha(str(directory).encode())[:12], {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()} == {x["path"] for x in artifacts} | {"seal.json", "journal.jsonl"})
    for i, item in enumerate(artifacts):
        path = a.checked_path(directory, item["path"])
        need("artifact_" + a.sha(str(directory).encode())[:8] + "_" + str(i), budget.hash(path) == {"sha256": item["sha256"], "bytes": item["bytes"]})
    if expected_ledger is not None:
        need("outer_terminal_ledger_byte_binding", seal["intended_ledger_sha256"] == chain[-1]["details"]["ledger_sha256"] == expected_ledger and seal["ledger_written"] is True and seal["lifecycle_errors"] == [])
    return chain


def native_projection(ready, manifest, budget):
    """One fresh original hash/row pass; no producer/compiler/scorer oracle."""
    context = manifest["authorization"]
    auth = strict_json(context["draft_json"])["authentication"]
    need("native_reference_authentication", a.sha(context["ready_json"].encode()) == ready["reference_ready_sha256"] and a.sha(context["draft_json"].encode()) == r.PLAN_SHA)
    docs = {name: strict_json(payload) for name, payload in context["metadata_files_json"].items()}
    for name, payload in context["metadata_files_json"].items():
        need("retained_native_metadata_" + name, a.sha(payload.encode()) == auth["metadata_sha256"][name])
    query = {}
    for name, payload in context["neutral_files_json"].items():
        need("retained_native_query_" + name, a.sha(payload.encode()) == auth["neutral_files_sha256"][name] and payload.encode() == (s.TASKS / name).read_bytes())
        query[name] = strict_json(payload)
    need("native_neutral_seal", a.sha(context["neutral_seal_json"].encode()) == s.NEUTRAL_SEAL_SHA)
    cases = query["selected-case-plan.json"]["cases"]
    need("unchanged_ordered_native_cases", [c["case_id"] for c in cases] == list(CASES))
    originals = a.inventory(docs["frame"], docs["acquisition"])
    need("native_original_frame", len(originals) == 137 and a.sha(a.wire(originals)) == auth["frame_descriptor_sha256"] and Path(ready["approved_raw_root"]) == s.RAW)
    for i, original in enumerate(originals):
        original["source_id"] = "original-" + str(i).zfill(3)
    paths = [a.checked_path(s.RAW, original["relative_path"]) for original in originals] + [Path(original["receipt"]["path"]) for original in originals]
    references, selected_all = {}, {}
    with a.stable_files(paths, deadline=budget.deadline):
        for original in originals:
            need("fresh_native_hash_" + original["source_id"], budget.hash(original["path"]) == {"sha256": original["sha256"], "bytes": original["bytes"]})
        nodes, proofs = [], []
        for original in originals:
            receipt_hash = budget.hash(original["receipt"]["path"])
            payload = Path(original["receipt"]["path"]).read_bytes()
            receipt = strict_json(payload)
            observed = r.utc(receipt["completed_at_utc"])
            need("fresh_native_receipt_" + original["source_id"], receipt_hash == {"sha256": original["receipt"]["sha256"], "bytes": original["receipt"]["bytes"]} and observed <= r.utc(s.CUTOFF) and receipt["status"] == "completed" and receipt["dataset_id"] == original["dataset_id"] and receipt["release_id"] == original["release_id"] and receipt["sha256"] == original["sha256"] and receipt["bytes"] == original["bytes"] and receipt["relative_path"].replace("\\", "/") == original["relative_path"] and receipt["url"] == original["source_url"])
            avail = Availability(None, None, None, None, observed.date(), "public_download_receipt", "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, original["receipt"]["sha256"])
            role = "reference" if original["family"] == "hgnc" else "agent_evidence"
            receipt_rel = Path(original["receipt"]["path"]).relative_to(s.RAW).as_posix()
            node = SourceNode(original["source_id"], original["dataset_id"], original["release_id"], original["relative_path"], original["sha256"], role, avail, TemporalClass.CONTEMPORARY, original["source_url"], receipt_path=receipt_rel, receipt_sha256=original["receipt"]["sha256"])
            nodes.append(node)
            proofs.append({"artifact_id": node.source_id, "dataset_id": node.dataset_id, "release_id": node.release_id, "path": node.path, "sha256": node.sha256, "role": role, "parents": [], "receipt_path": receipt_rel, "receipt_sha256": original["receipt"]["sha256"], "bytes": original["bytes"], "availability": encode(avail), "temporal_classification": "contemporary_only", "path_scope": "raw", "receipt_bytes": original["receipt"]["bytes"]})
        cutoff = r.utc(s.CUTOFF)
        snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), str(s.RAW), {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
        graph = InputGraph(snapshot, ROOT, catalog_index(docs["catalog"]))
        need("fresh_native_provenance_snapshot", s.same(encode(snapshot), query["source-snapshot.json"]) and graph.exclusion(tuple(n.source_id for n in nodes), SimpleNamespace(cutoff=cutoff)) is None)
        old_observe = a.observe
        def observe(batch):
            old_observe(batch)
            budget.sample()
        a.observe = observe
        try:
            indexes = a.load_mappings(originals)
            selected_all, excluded = s.source_selected(originals, cases, indexes, cutoff)
            budget.original_row_passes += 1
        finally:
            a.observe = old_observe
        node_map = {node.source_id: node for node in nodes}
        for case in cases:
            cid, groups = case["case_id"], selected_all[case["case_id"]]
            task = query[cid + ".task.json"]
            need("fresh_native_task_" + cid, s.same(task, s.expected_task(case, groups)))
            rows = {record["record_key"]: row["values"] for record, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])}
            need("fresh_native_date_scope_" + cid, all(r.strict_source_guards(row, task) for row in rows.values()))
            reference = r.direct_reference(task, rows, node_map, proofs, docs["catalog"], encode(snapshot))
            check("fresh_native_reference_comparison_" + cid, s.same(manifest["cases"][cid]["reference"], reference))
            frozen = ready["native_cases"][cid]
            measurements = [fact for fact in reference["facts"] if fact["family"] == "reported_measurement" and fact["value"] is not None]
            counts = {"requested_facts": len(reference["facts"]), "measurement_answerable_facts": len(measurements), "measurement_answerable_groups": len({(f["record_key"], f["group"]) for f in measurements})}
            check("fresh_native_frozen_binding_" + cid, frozen["disposition"] == "compiled" and frozen["task_sha256"] == a.sha(a.wire(task)) and frozen["reference_sha256"] == a.sha(a.wire(reference)) and all(frozen[k] == v for k, v in counts.items()))
            references[cid] = reference
    REPORT["source_inclusive"] = True
    REPORT["original_source_proofs"] = [{"source_id": o["source_id"], "sha256": o["sha256"], "receipt_sha256": o["receipt"]["sha256"], "bytes": o["bytes"]} for o in originals]
    return references, query, selected_all, nodes


def qualification_index(ledger):
    qualification = ledger.get("native_qualification")
    require(type(qualification) is dict and list(qualification) == list(CASES),
            "Exactly twelve ordered native qualification mappings required")
    require(all(type(row) is dict and row.get("case_id") == key
                for key, row in qualification.items()), "Qualification key/row identity differs")
    return dict(qualification)


def audit_actual(args):
    """Actual audit only after the user's separately pinned terminal run exists."""
    ledger_path = Path(args.ledger).absolute()
    run = ledger_path.parent
    need("explicit_experiment_subject_path", ledger_path.name == "ledger.json" and run.parent == ROOT / "data/derived" and re.fullmatch(r"preprint-p05-experiment-\d{8}T\d{6}Z", run.name) is not None and a.checked_path(ROOT, run.relative_to(ROOT).as_posix()) == run)
    ledger_bytes = ledger_path.read_bytes()
    need("external_exact_ledger_bytes", a.sha(ledger_bytes) == args.ledger_sha256)
    ledger = strict_json(ledger_bytes)
    REPORT["subject"] = {"ledger_path": str(ledger_path), "ledger_sha256": args.ledger_sha256}
    chain0 = [strict_json(line) for line in (run / "journal.jsonl").read_bytes().splitlines()]
    need("producer_process_closed_before_source_audit", not a.process_live(chain0[0]["details"]["owner_pid"]))
    budget = Budget(ledger.get("resources"))
    seal = read_document(run / "seal.json", budget, args.seal_sha256)
    chain = verify_seal(run, seal, budget, terminal="experiment_completed", expected_ledger=args.ledger_sha256)
    need("qualified_terminal_no_cleanup_failures", ledger["status"] == "COMPLETED_PENDING_INDEPENDENT_AUDIT" and ledger["failure"] is None and seal["status"] == ledger["status"] and seal["expected_ready_sha256"] == args.ready_sha256)
    authorization = read_document(run / "authorization.json", budget)
    ready_bytes, plan_bytes = authorization["ready_json"].encode(), authorization["plan_json"].encode()
    ready, plan = strict_json(ready_bytes), strict_json(plan_bytes)
    need("external_READY_and_archived_plan", a.sha(ready_bytes) == args.ready_sha256 == authorization["expected_ready_sha256"] and ready["status"] == "READY" and ready["frozen_by"] == "root" and ready["actual_execution_authorized"] is True and ready["scope"] == "p05.deterministic_source_validation_experiment.v1" and a.sha(plan_bytes) == ready["plan_sha256"] and plan["status"] == "DRAFT_NOT_EXECUTABLE" and plan["actual_execution_authorized"] is False)
    need("frozen_design_bytes", budget.hash(ASSETS / "EXPERIMENT-DESIGN-v1.md")["sha256"] == ready["design_sha256"])
    need("frozen_environment", ready["environment"] == {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(), "pyarrow": __import__("pyarrow").__version__, "platform": sys.platform})
    for path, pin in ready["code_sha256"].items():
        need("runner_code_" + a.sha(path.encode())[:12], budget.hash(a.checked_path(ROOT, path))["sha256"] == pin)
    audit_dependencies = [Path(__file__).resolve(), ASSETS / "audit_source_registry_v3.py", ASSETS / "audit_source_inputs_v1.py", ASSETS / "audit_source_references_v1.py"]
    extra = ready["extra_code_sha256"]
    for path in audit_dependencies:
        logical = path.relative_to(ROOT).as_posix()
        need("frozen_independent_auditor_" + path.name, logical in extra and budget.hash(path)["sha256"] == extra[logical])
    for path, pin in extra.items():
        need("all_extra_code_" + a.sha(path.encode())[:12], budget.hash(a.checked_path(ROOT, path))["sha256"] == pin)
    schedule_outputs, schedule_decisions = fixed_schedule()
    need("frozen_schedule", ready["schedule"] == {"output_cells": schedule_outputs, "decision_cells": schedule_decisions})
    outputs, decisions = ledger["output_cells"], ledger["decision_cells"]
    need("all38_output_cells_once_in_order", len(outputs) == 38 and [{k: c[k] for k in ("cell_id", "case_id", "arm", "stratum")} for c in outputs] == schedule_outputs)
    need("all90_decision_cells_once_in_order", len(decisions) == 90 and [{k: c[k] for k in ("decision_id", "output_cell_id", "policy")} for c in decisions] == schedule_decisions)
    need("fixed_unit_and_science_accounting", ledger["planned_output_cells"] == 38 and ledger["planned_decisions"] == 90 and ledger["native_units"] == 12 and ledger["independent_studies"] is None and ledger["scientific_validation"] == "not_established" and all(ledger[k] == 0 for k in ("model_calls", "network_calls", "new_downloads", "provider_spending_usd")))
    need("frozen_input_and_subject_descriptors", s.same(ledger["frozen_inputs"], ready["inputs"]) and s.same(ledger["subject_bindings"], ready["native_cases"]))
    inputs = {}
    paths = {}
    expected_inputs = {"input_seal", "input_audit", "reference_manifest", "reference_seal", "reference_audit", "fixture_manifest", "exposure_dependence", "peer_review", "fictional_qualification"}
    need("exact_upstream_allowlist", set(ready["inputs"]) == expected_inputs)
    for name, value in ready["inputs"].items():
        paths[name], inputs[name] = descriptor(value, budget)
        if name.endswith("audit") or name in ("peer_review", "fictional_qualification"):
            check("upstream_PASS_" + name, type(inputs[name].get("status")) is str and inputs[name]["status"].startswith("PASS") and not inputs[name].get("issues") and not inputs[name].get("findings"))
            for dotted, expected in value.get("expected_fields", {}).items():
                observed = inputs[name]
                for part in dotted.split("."):
                    observed = observed[part]
                check("upstream_binding_" + name + "_" + dotted, s.same(observed, expected))
    input_root, reference_root = paths["input_seal"].parent, paths["reference_manifest"].parent
    need("explicit_current_upstream_roots", input_root.parent == ROOT / "data/derived" and input_root.name.startswith("preprint-p05-source-inputs-") and reference_root.parent == ROOT / "data/benchmark/gold_evidence" and reference_root.name.startswith("preprint-p05-references-") and paths["reference_manifest"].name == "references.json" and paths["reference_seal"] == reference_root / "seal.json")
    verify_seal(input_root, inputs["input_seal"], budget)
    verify_seal(reference_root, inputs["reference_seal"], budget)
    manifest = inputs["reference_manifest"]
    need("reference_external_canonical_anchor", a.sha(a.wire(manifest)) == ready["reference_manifest_fingerprint"] == inputs["reference_seal"]["manifest_sha256"])
    references, query, selected, nodes = native_projection(ready, manifest, budget)
    node_map = {n.source_id: n for n in nodes}
    dependence = inputs["exposure_dependence"]
    check("register_status_exposure_independence", dependence["status"] in ("FROZEN", "READY") and dependence["role"] == "evaluation_only" and dependence["agent_visible"] is False and dependence["case_ids"] == list(CASES) and dependence["other_exposure"] == "UNKNOWN" and dependence["independent_studies_established"] is False)
    registered = {c["case_id"]: c for c in dependence["native_cases"]}
    for cid in CASES:
        ref = references[cid]
        measurements = [f for f in ref["facts"] if f["family"] == "reported_measurement" and f["value"] is not None]
        counts = {"requested_facts": len(ref["facts"]), "measurement_answerable_facts": len(measurements), "measurement_answerable_groups": len({(f["record_key"], f["group"]) for f in measurements})}
        check("independent_register_denominator_" + cid, all(registered[cid][k] == value for k, value in counts.items()) and registered[cid]["task_sha256"] == ref["task_sha256"])
        packet_path = input_root / "packets" / (cid + ".json")
        packet = read_document(packet_path, budget, ready["native_cases"][cid]["packet_sha256"])
        task = query[cid + ".task.json"]
        groups = selected[cid]
        rawrows = [{"record_key": request["record_key"], **row} for request, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])]
        skeleton = [{k: f[k] for k in ("fact_id", "record_key", "field", "source")} for f in ref["facts"]]
        check("native_original_to_packet_" + cid, s.same(packet["neutral_task"], task) and s.same(packet["source_records"], rawrows) and s.same(packet["fact_skeleton"], skeleton) and s.same(packet["source_nodes"], encode(nodes)) and packet["lineage"]["reference_inputs"] == packet["lineage"]["evaluation_inputs"] == [] and packet["role"] == "agent_evidence" and packet["agent_visible"] is True)
    qualification = qualification_index(ledger)
    need("all12_qualification_rows", list(qualification) == list(CASES))
    for cid, row in qualification.items():
        check("source_qualified_denominator_" + cid, row["disposition"] == "compiled" and all(row[k] == ready["native_cases"][cid][k] for k in ("task_sha256", "reference_sha256", "measurement_answerable_facts", "measurement_answerable_groups", "requested_facts")))
    fixture_root = paths["fixture_manifest"].parent
    fixture_manifest = inputs["fixture_manifest"]
    need("fictional_root_and_inventory", fixture_root.is_relative_to(ROOT / "data/cache") and paths["fixture_manifest"].name == "manifest.json" and fixture_manifest["status"] == "FROZEN_FICTIONAL_SOURCES_ONLY_NOT_STUDY_RESULTS" and fixture_manifest["candidate_outputs_created"] is False and list(fixture_manifest["scenarios"]) == list(SCENARIOS) and fixture_manifest["code_sha256"] == ready["code_sha256"])
    for i, item in enumerate(fixture_manifest["files"]):
        need("frozen_fixture_byte_" + str(i), budget.hash(a.checked_path(fixture_root, item["path"])) == {"sha256": item["sha256"], "bytes": item["bytes"]})
    oracle = read_document(fixture_root / "oracle.json", budget, fixture_manifest["oracle_sha256"])
    output_map = {o["cell_id"]: o for o in outputs}
    actual_scores, expected_scores, fixture_truth, expected_stages = [], [], {}, {}
    audit_cell_rows = {}
    for out in outputs:
        cid = out["cell_id"]
        check("valid_terminal_" + cid, out["terminal"] in TERMINALS)
        if out.get("raw_path") is None:
            check("nonreturn_not_rescued_" + cid, out["terminal"] in ("failed", "timeout", "interrupted", "unexecuted") and out.get("core_score") is None and out.get("strict_exact_report") is None and not out.get("full_verified_exact"))
            audit_cell_rows[cid] = {"terminal": out["terminal"], "exact": None, "completion": None, "source_admitted": False}
            continue
        raw_path = a.checked_path(run, out["raw_path"])
        need("exact_raw_retention_path_" + cid, out["raw_path"] == "raw/" + cid + ".json" and raw_path.stat().st_size <= 524288)
        measured = budget.hash(raw_path)
        check("raw_byte_binding_" + cid, measured == {"sha256": out["raw_sha256"], "bytes": out["raw_bytes"]})
        raw = raw_path.read_bytes()
        if out["stratum"] == "native":
            ref = references[out["case_id"]]
            task = ref["method"]["task"]
            check("independent_native_literal_bytes_" + cid, raw == a.wire(wire_projection(task, ref["facts"], abstain=out["arm"] == "A")))
            score, exact, accounting = independent_score(ref, raw, cid, out["received_terminal"])
            statuses = {key: "pass" for key in STAGES}
            statuses["G4"] = "pass" if exact else "rejected"
            schema = "pass" if score["adapter_status"] == "scorable" else "rejected"
            source_admitted = True
        else:
            key = out["case_id"]
            entry = fixture_manifest["scenarios"][key]
            scenario = read_document(a.checked_path(fixture_root, entry["scenario_path"]), budget, entry["scenario_sha256"])
            packet = read_document(a.checked_path(fixture_root, entry["packet_path"]), budget, entry["packet_sha256"])
            source_bytes, receipts = {}, {}
            _, blueprint = fixture_documents(key)
            for name in blueprint:
                source_bytes[name] = a.checked_path(fixture_root, key + "/originals/" + name + ".json").read_bytes()
                receipts[name] = a.checked_path(fixture_root, key + "/originals/" + name + ".receipt.json").read_bytes()
            evidence = fixture_evidence(scenario, packet, source_bytes, receipts, raw, fixture_root=fixture_root)
            score, exact, accounting = evidence["score"], evidence["strict_exact_report"], evidence["fact_accounting"]
            statuses, schema, source_admitted = evidence["statuses"], evidence["schema_status"], evidence["full_source_admitted"]
            ref = evidence["reference"]
            fixture_truth[key] = evidence["truth"]
            frozen = ready["fictional_references"][key]
            count = None if ref is None else {"requested_facts": len(ref["facts"]), "measurement_answerable_facts": sum(f["family"] == "reported_measurement" and f["value"] is not None for f in ref["facts"]), "measurement_answerable_groups": len({(f["record_key"], f["group"]) for f in ref["facts"] if f["family"] == "reported_measurement" and f["value"] is not None})}
            check("independent_fixture_reference_anchor_" + key, frozen == {"task_sha256": a.sha(a.wire(evidence["task"])), "reference_sha256": a.sha(a.wire(ref)) if ref is not None else None, "counts": count})
            check("independently_checked_fixture_oracle_truth_" + key, oracle["rows"][key]["truth"] == evidence["truth"])
            for policy in POLICIES:
                check("independent_fixture_oracle_policy_" + key + "_" + policy, oracle["rows"][key]["expected_by_policy"][policy] == evidence["decisions"][policy]["verdict"])
        expected_stages[cid] = (statuses, schema)
        check("independent_complete_score_" + cid, s.same(out.get("core_score"), score))
        check("independent_fact_accounting_" + cid, s.same(out.get("fact_accounting"), accounting))
        check("exactness_source_admission_separated_" + cid, out["strict_exact_report"] is exact and out["full_source_admitted"] is source_admitted and out["full_verified_exact"] is bool(source_admitted and exact is True))
        actual_guards = ledger["guards"][cid]
        check("independent_guard_statuses_" + cid, all(actual_guards[key]["status"] == statuses[key] for key in STAGES) and actual_guards["G4"]["schema_status"] == schema)
        if score is not None:
            expected_scores.append(score)
            actual_scores.append(out["core_score"])
        check("received_and_normalized_terminal_" + cid, out["received_terminal"] == "returned" and out["terminal"] == ("malformed" if schema == "rejected" else "returned"))
        audit_cell_rows[cid] = {"terminal": out["terminal"], "exact": exact, "completion": score["completion"] if score is not None else None, "source_admitted": source_admitted}
    false_counts = {p: {"valid_planned": 4, "invalid_planned": 10, "valid_attempted": 0, "invalid_attempted": 0, "false_accept": 0, "false_reject": 0, "unknown_valid": 0, "unknown_invalid": 0} for p in POLICIES}
    policy_rows = defaultdict(dict)
    for decision in decisions:
        cid, policy = decision["output_cell_id"], decision["policy"]
        if cid not in expected_stages:
            check("unexecuted_decision_" + decision["decision_id"], decision["verdict"] == "no_decision" and decision["terminal"] == "unexecuted")
            continue
        expected = policy_decision(*expected_stages[cid], policy)
        check("independent_policy_" + decision["decision_id"], all(s.same(decision[k], v) for k, v in expected.items()) and decision["projection"] is True and decision["scientific_validation"] == "not_established")
        policy_rows[cid][policy] = expected["verdict"]
        if cid.startswith("S-"):
            truth = fixture_truth[cid[2:]]
            row = false_counts[policy]
            valid = truth == "VALID_REPORT"
            if expected["verdict"] == "no_decision":
                row["unknown_valid" if valid else "unknown_invalid"] += 1
            else:
                row["valid_attempted" if valid else "invalid_attempted"] += 1
                row["false_accept"] += not valid and expected["verdict"] == "admitted"
                row["false_reject"] += valid and expected["verdict"] == "rejected"
            check("retained_fixture_truth_and_expectation_" + decision["decision_id"], decision["fixture_truth"] == truth and decision["expected_verdict"] == expected["verdict"])
    aggregate = ledger["core_aggregate"]
    check("complete_genuine_score_subset", s.same(aggregate["case_results"], expected_scores))
    terminals = dict.fromkeys(TERMINALS, 0)
    for score in expected_scores:
        terminals[score["terminal"]] += 1
    check("independent_core_aggregate_contributions", aggregate["planned_cells"] == len(expected_scores) and aggregate["task_count"] == len({score["task_id"] for score in expected_scores}) and aggregate["terminal_counts"] == terminals and aggregate["scorable_cells"] == sum(score["adapter_status"] == "scorable" for score in expected_scores) and aggregate["completion_count"] == sum(score["completion"] for score in expected_scores) and aggregate["completion_rate"] == sum(score["completion"] for score in expected_scores) / len(expected_scores) and aggregate["result_sha256"] == [a.sha(a.wire(score)) for score in expected_scores])
    check("independent_core_aggregate_unknown_and_science_fields", aggregate["correct_missing_input_count"] == sum(score["correct_missing_input"] is True for score in expected_scores) and aggregate["correct_missing_input_denominator"] == sum(score["correct_missing_input"] is not None for score in expected_scores) and aggregate["scientific_validation"] == "not_established")
    terminal_outputs = [e for e in chain if e["event"] == "cell_terminal"]
    terminal_decisions = [e for e in chain if e["event"] == "decision_terminal"]
    check("all38_terminal_journal_bindings", [e["details"] for e in terminal_outputs] == [{"cell_id": o["cell_id"], "terminal": o["terminal"], "raw_sha256": o["raw_sha256"]} for o in outputs])
    check("all90_terminal_journal_bindings", [e["details"] for e in terminal_decisions] == [{"decision_id": d["decision_id"], "terminal": d["terminal"], "verdict": d["verdict"]} for d in decisions])
    pairs_summary = {}
    for left, right in (("FULL", "WITHOUT_WRAPPER"), ("FULL", "WIRE_ONLY"), ("WITHOUT_WRAPPER", "WIRE_ONLY")):
        pairs_summary[left + "__" + right] = dict(Counter(row[left] + "__" + row[right] for row in policy_rows.values() if left in row and right in row))
    production = ledger["resources"]
    check("production_resources_qualified", 0 < production["peak_sampled_process_rss_bytes"] <= 2 * 1024**3 and production["process_lifetime_peak_bytes"] is not None and production["process_lifetime_peak_bytes"] <= 2 * 1024**3 and production["wall_seconds"] <= 3600 and production["physical_io_bytes"] is None and production["original_row_enumeration_passes"] + budget.original_row_passes <= 4)
    budget.sample()
    REPORT["cost"] = budget.report()
    REPORT["producer_resources"] = production
    REPORT["output_cells_checked"] = len(outputs)
    REPORT["decision_cells_checked"] = len(decisions)
    REPORT["independent_cell_summary"] = audit_cell_rows
    REPORT["fictional_false_accept_reject_unknown"] = false_counts
    REPORT["paired_policy_verdicts"] = pairs_summary
    REPORT["anchors"] = {"ready_sha256": args.ready_sha256, "seal_sha256": args.seal_sha256, "reference_manifest_fingerprint": ready["reference_manifest_fingerprint"], "fixture_manifest_sha256": ready["inputs"]["fixture_manifest"]["sha256"], "register_sha256": ready["inputs"]["exposure_dependence"]["sha256"]}
    REPORT["byte_semantic_scientific_separation"] = {"byte_integrity": "checked", "source_semantics": "independently projected from originals and fixed fictional byte/truth protocol", "scientific_validation": "not_established", "independent_studies": "not_established"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--ready-sha256", required=True)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--authorized-actual-audit", action="store_true", required=True)
    args = parser.parse_args()
    for name in ("ledger_sha256", "ready_sha256", "seal_sha256"):
        require(re.fullmatch(r"[0-9a-f]{64}", getattr(args, name)) is not None, "External exact pins required")
    require(not args.audit_output.exists(), "Existing audit reports must be preserved")
    try:
        audit_actual(args)
    except BaseException as exc:
        REPORT["issues"].append("audit_exception:" + type(exc).__name__)
        REPORT["error_class"] = type(exc).__name__
        if isinstance(exc, AssertionError):
            REPORT["failed_check"] = str(exc)
    REPORT["unresolved_findings"] = list(REPORT["issues"])
    REPORT["status"] = "PASS_INDEPENDENT_EXPERIMENT_AUDIT" if not REPORT["unresolved_findings"] and REPORT["source_inclusive"] else "FAIL_INDEPENDENT_EXPERIMENT_AUDIT"
    REPORT["auditor_sha256"] = a.sha(Path(__file__).read_bytes())
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_bytes(a.wire(REPORT) + b"\n")
    print(json.dumps({"status": REPORT["status"], "checks": len(REPORT["checks"]), "unresolved_findings": REPORT["unresolved_findings"], "audit_sha256": a.sha(args.audit_output.read_bytes()), "subject": REPORT.get("subject"), "cost": REPORT["cost"]}))
    return 0 if REPORT["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
