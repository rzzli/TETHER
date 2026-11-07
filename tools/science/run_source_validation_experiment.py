"""P05-only deterministic source experiment. Default DRAFT; no model/network code.

The generation functions accept packets only and perform no file reads. Source
references are opened and replayed only by the evaluator/orchestrator branch.
Fictional JSON controls exercise real core guards plus applicable pure P05
predicates; they do not claim to pass the native Parquet input builder.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE / "tools/science"))
import prepare_source_validation_set as stage1
import prepare_source_validation_inputs as source_inputs
import build_source_validation_references as reference_builder
from tether_engine.atomic import publish_bytes
from tether_engine.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from tether_engine.journal import RunJournal, read_chain
from tether_engine.provenance import InputGraph, catalog_index
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, freeze, parse_json
from tether_engine.study.source_fact_adapters import adapt_output
from tether_engine.study.source_fact_evaluation import aggregate_cells, score_cell
from tether_engine.study.source_fact_sources import compile_reference, validate_task, verify_reference
from tether_engine.study.proofs import _relative
from tether_engine.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files
from tether_engine.wire import same_json

ASSETS = stage1.ASSETS
DESIGN_PATH = ASSETS / "EXPERIMENT-DESIGN-v1.md"
PLAN_PATH = ASSETS / "EXPERIMENT-PLAN-DRAFT-v1.json"
READY_PATH = ASSETS / "EXPERIMENT-READY-v1.json"
OUTPUT_ROOT = WORKSPACE / "data/derived"
OUTPUT_PREFIX = "preprint-p05-experiment-"
METHOD = "p05.deterministic_source_validation_experiment.v1"
CUTOFF = source_inputs.CUTOFF
CASES = tuple(f"p05-{n:02d}" for n in range(1, 13))
SCENARIOS = tuple([f"C{n:02d}" for n in range(1, 5)] + [f"F{n:02d}" for n in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
STAGES = ("G0", "G1", "G2", "G3", "G4")
EXTRA_CODE = (
    "tools/science/analyze_source_validation_experiment.py",
    "tools/science/audit_source_validation_experiment.py",
    "planning/review-assets/preprint-p05-20261031/test_analyze_source_validation_experiment.py",
    "planning/review-assets/preprint-p05-20261031/test_audit_source_validation_experiment.py",
    "planning/review-assets/preprint-p05-20261031/audit_source_registry_v3.py",
    "planning/review-assets/preprint-p05-20261031/audit_source_inputs_v1.py",
    "planning/review-assets/preprint-p05-20261031/audit_source_references_v1.py",
)
ANALYSIS_CODE = EXTRA_CODE[0]
TERMINALS = ("returned", "malformed", "failed", "timeout", "interrupted", "unexecuted")
LIMITS = dict(seconds=3600, audit_seconds=3600, output_bytes=256 * 1024**2,
              retained_raw_bytes=512 * 1024, accepted_wire_bytes=256 * 1024,
              fictional_source_bytes=4 * 1024**2, memory_bytes=2 * 1024**3,
              unique_original_bytes=4 * 1024**3, original_files=137,
              logical_completed_hash_bytes=512 * 1024**3, row_enumeration_passes=4)
PACKET_KEYS = frozenset(("schema_version", "packet_type", "case_id", "role", "agent_visible",
    "neutral_task", "task_sha256", "source_records", "fact_skeleton", "normalization_proof",
    "source_nodes", "source_proofs", "unknown_context", "instruction", "output_contract", "lineage"))


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def schedule():
    outputs, decisions = [], []
    for case_id in CASES:
        for arm in ("L", "A"):
            cell_id = f"N-{arm}-{case_id}"
            outputs.append(dict(cell_id=cell_id, case_id=case_id, arm=arm, stratum="native"))
            for policy in POLICIES if arm == "L" else ("FULL",):
                decisions.append(dict(decision_id=f"D-{cell_id}-{policy}", output_cell_id=cell_id, policy=policy))
    for scenario_id in SCENARIOS:
        cell_id = "S-" + scenario_id
        outputs.append(dict(cell_id=cell_id, case_id=scenario_id, arm="fixture", stratum="fictional_json_core"))
        for policy in POLICIES:
            decisions.append(dict(decision_id=f"D-{cell_id}-{policy}", output_cell_id=cell_id, policy=policy))
    return dict(output_cells=outputs, decision_cells=decisions)


def code_paths():
    return sorted(set(reference_builder.code_paths() + [Path(__file__).resolve(),
        ASSETS / "test_source_validation_experiment.py"]))


def code_pins():
    return {p.relative_to(WORKSPACE).as_posix(): digest(p.read_bytes()) for p in code_paths()}


def make_draft():
    """Metadata only. No packet, original, reference, audit capture or old answer."""
    raw = PLAN_PATH.read_bytes()
    plan = parse_json(raw)
    need(plan.get("status") == "DRAFT_NOT_EXECUTABLE" and plan.get("actual_execution_authorized") is False,
         "Checked-in DRAFT must remain non-executable")
    return dict(schema_version=1, status="DRAFT_NOT_EXECUTABLE", actual_execution_authorized=False,
        method=METHOD, plan_sha256=digest(raw), design_sha256=digest(DESIGN_PATH.read_bytes()),
        code_sha256=code_pins(), environment=stage1.environment(), limits=LIMITS,
        extra_code_sha256={name: digest((WORKSPACE / name).read_bytes()) if (WORKSPACE / name).exists() else None for name in EXTRA_CODE},
        schedule=schedule(), missing_ready="root exact READY, admitted audits, case/ref denominators, fixture and code seals",
        model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0)


def packet_view(packet):
    """Pure packet validation/projection. No source/reference or filesystem lookup.

    This checks supplied claims. Original ancestry is authenticated separately.
    It does not turn packet metadata into an independently source-verified fact.
    """
    need(isinstance(packet, dict) and set(packet) == PACKET_KEYS, "Unknown P05 packet shape")
    need(type(packet["schema_version"]) is int and packet["schema_version"] == 1 and
         packet["packet_type"] == source_inputs.METHOD and packet["role"] == "agent_evidence" and
         packet["agent_visible"] is True, "Original-only P05 source packet required")
    lineage = packet["lineage"]
    need(isinstance(lineage, dict) and lineage.get("method") == source_inputs.METHOD and
         lineage.get("reference_inputs") == [] and lineage.get("evaluation_inputs") == [] and
         lineage.get("generation_authority") is False and lineage.get("information_cutoff") == CUTOFF,
         "Evaluator or unsealed generation ancestry denied")
    need(all(isinstance(x, dict) and x.get("kind") in ("original", "neutral_config", "neutral_selected_case_plan")
             for x in lineage.get("input_refs", [])), "Unsupported source packet ancestor")
    need(packet["unknown_context"] == source_inputs.UNKNOWN_CONTEXT, "Unknown scientific context changed")
    task = encode(validate_task(packet["neutral_task"]))
    need(packet["task_sha256"] == fingerprint(task) and task["cutoff"] == CUTOFF and
         task["primary_families"] == ["reported_measurement"], "P05 task/cutoff/family binding differs")
    need(all(task["scope"][k] is None for k in ("action", "modality", "tissue")) and
         all(task["scope"][k] == "unknown" for k in ("target_namespace_version", "indication_namespace_version")),
         "Intervention/namespace unknowns must remain explicit")
    need(all(f["unit_field"] is None and f["empty_policy"] == "unknown" for f in task["fields"]),
         "Only frozen native null-unit literal requests are supported")
    nodes = {n["source_id"]: n for n in packet["source_nodes"]}
    need(len(nodes) == len(packet["source_nodes"]), "Duplicate packet source node")
    records = {r["record_key"]: r for r in task["records"]}
    rows = {r["record_key"]: r for r in packet["source_records"]}
    need(len(rows) == len(packet["source_records"]) and set(rows) == set(records), "Packet record inventory differs")
    for key, record in records.items():
        row = rows[key]
        need(isinstance(row.get("values"), dict) and row["source_id"] == record["source_id"] and
             row["source_id"] in nodes and same_json(row["locator"], record["locator"]), "Packet row binding differs")
        node = nodes[row["source_id"]]
        need(node["role"] in ("agent_evidence", "reference") and not node.get("parents") and
             node.get("computed_at") is None, "Packet claims a non-original selected input")
        need(all(name in row["values"] and same_json(row["values"][name], value)
                 for name, value in record["identity"].items()), "Packet native record identity differs")
    restrictions = {key: [] for key in records}
    anchors = set()
    for key, record in records.items():
        values = record["identity"]
        if values.get("targetId") == task["scope"]["target_id"] and values.get("diseaseId") == task["scope"]["indication_id"]:
            anchors.add(key)
    for join in task["joins"]:
        need(join["cardinality"] == "one_to_many" and join["inventory_status"] == "complete" and
             join["left_record"] in anchors and join["left_field"] == join["right_field"] == "studyLocusId",
             "Unsupported P05 join shape; no general join extension")
        left = rows[join["left_record"]]["values"].get("studyLocusId")
        for right in join["right_records"]:
            right_value = rows[right]["values"].get("studyLocusId")
            restrictions[right].append(left not in (None, "") and right_value not in (None, "") and same_json(left, right_value))
            need(nodes[records[right]["source_id"]]["release_id"] == nodes[records[join["left_record"]]["source_id"]]["release_id"],
                 "P05 joins require same release")
    skeleton = []
    for field in task["fields"]:
        record = records[field["record_key"]]
        node = nodes[record["source_id"]]
        binding = dict(source_id=node["source_id"], sha256=node["sha256"], release_id=node["release_id"],
                       locator=record["locator"], field=field["field"])
        identity = dict(task_sha256=fingerprint(task), scope=task["scope"], record_key=field["record_key"], source=binding)
        skeleton.append(dict(fact_id="fact:" + fingerprint(identity), record_key=field["record_key"],
                             field=field["field"], source=binding))
    need(same_json(skeleton, packet["fact_skeleton"]), "Value-free slot inventory differs")
    return task, rows, anchors, restrictions, skeleton


def literal_report(packet, *, always_abstain=False):
    """Generate from native packet rows and value-free tasks/slots only."""
    need(type(always_abstain) is bool, "Invalid abstention policy")
    task, rows, anchors, restrictions, skeleton = packet_view(packet)
    facts = []
    if not always_abstain:
        for slot in skeleton:
            key, name = slot["record_key"], slot["field"]
            row = rows[key]["values"]
            value = row.get(name)
            empty = (type(value) is str and value == "") or isinstance(value, (list, tuple, dict)) and not value
            reason = ("unavailable_join" if key not in anchors and (not restrictions[key] or not all(restrictions[key])) else
                      "failed_qc" if task["collection"]["status"] == "failed_qc" else
                      "field_not_in_schema" if name not in row else "null_source_value" if value is None else
                      "empty_source_value" if empty else None)
            facts.append(dict(fact_id=slot["fact_id"], value=None if reason else value, unit=None,
                              source=slot["source"], unknown_reason=reason))
    result = dict(schema_version=1, task_id=task["task_id"], task_sha256=fingerprint(task),
                  status="abstained" if always_abstain else "answered" if facts else "insufficient_input",
                  facts=facts, collection_status=task["collection"]["status"],
                  reason="Deliberate no-assertion baseline." if always_abstain else None if facts else
                  "No requested records in the declared bounded collection.")
    raw = canonical(result)
    need(adapt_output(raw, wire_format="typed_facts_v1", task_id=task["task_id"], task_sha256=fingerprint(task))["status"] == "scorable",
         "Literal output exceeds unchanged common wire; no truncation")
    return raw


def report_exactness(reference, raw, *, cell_id):
    """Use a genuine source-replayed reference. Exact report != 80% completion."""
    score = score_cell(reference, raw, cell_id=cell_id)
    exact = (score["terminal"] == "returned" and score["adapter_status"] == "scorable" and
             not score["critical_errors"] and score["answer_status"] == "answered" and
             score["emitted_facts"] == len(reference.document["facts"]))
    return exact, score


def fact_accounting(reference, raw):
    """Descriptive fact counters only; no new score and no values in this view."""
    task_id, task_hash = reference.document["task_id"], reference.document["task_sha256"]
    adapted = adapt_output(raw, wire_format="typed_facts_v1", task_id=task_id, task_sha256=task_hash)
    expected = {f["fact_id"]: f for f in reference.document["facts"]}
    emitted = adapted["output"]["facts"] if adapted["status"] == "scorable" else None
    multiplicity = Counter(f["fact_id"] for f in emitted) if emitted is not None else Counter()
    families = {}
    for family in ("identity_linkage", "reported_context", "reported_measurement", "provider_metric"):
        selected = [f for f in expected.values() if f["family"] == family]
        row = dict(requested=len(selected), answerable=sum(f["value"] is not None for f in selected),
            expected_unknown_by_reason=dict(Counter(f["unknown_reason"] for f in selected if f["value"] is None)),
            correct_unknown=0 if emitted is not None else None, omitted=0 if emitted is not None else None,
            matched=0 if emitted is not None else None, false_asserted_values=0 if emitted is not None else None)
        if emitted is not None:
            row["omitted"] = sum(multiplicity[f["fact_id"]] == 0 for f in selected)
            for fact in emitted:
                original = expected.get(fact["fact_id"])
                if original is None or original["family"] != family:
                    continue
                same = all(same_json(fact[k], original[k]) for k in ("value", "unit", "source", "unknown_reason"))
                if original["value"] is None and same and multiplicity[fact["fact_id"]] == 1:
                    row["correct_unknown"] += 1
                if original["value"] is not None and same and multiplicity[fact["fact_id"]] == 1:
                    row["matched"] += 1
                if fact["value"] is not None and not same:
                    row["false_asserted_values"] += 1
        row["false_asserted"] = row["false_asserted_values"]
        families[family] = row
    return dict(families=families, unknown_fact_id_emissions=sum(f["fact_id"] not in expected for f in emitted) if emitted is not None else None,
                adapter_status=adapted["status"])


def memory_reading():
    try:
        import psutil
        info = psutil.Process().memory_info()
        return info.rss, getattr(info, "peak_wset", None)
    except (ImportError, OSError):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize, counters.PeakWorkingSetSize
        return None, None


class Bounds:
    def __init__(self, output, *, seconds=LIMITS["seconds"]):
        self.output = Path(output)
        self.started = time.monotonic()
        self.cpu_started = time.process_time()
        self.deadline = self.started + seconds
        self.logical_completed_hash_bytes = 0
        self.partial_failed_hash_bytes = None
        self.original_row_passes = 0
        self.original_row_pass_attempts = 0
        self.peak_sampled_rss_bytes = 0
        self.process_lifetime_peak_bytes = None
        self.bytes_read_retained = 0

    def check(self):
        deadline_check(self.deadline)
        rss, peak = memory_reading()
        need(rss is not None, "Process memory reading unavailable; bound unqualified")
        self.peak_sampled_rss_bytes = max(self.peak_sampled_rss_bytes, rss)
        self.process_lifetime_peak_bytes = peak
        need(rss <= LIMITS["memory_bytes"] and (peak is None or peak <= LIMITS["memory_bytes"]), "Process memory checkpoint bound exceeded")
        need(self.logical_completed_hash_bytes <= LIMITS["logical_completed_hash_bytes"], "Logical complete hash-byte budget exceeded")
        need(self.original_row_pass_attempts <= LIMITS["row_enumeration_passes"], "Original row pass budget exceeded")
        size = sum(p.stat().st_size for p in self.output.rglob("*") if p.is_file())
        need(size <= LIMITS["output_bytes"], "Whole experiment output bound exceeded")
        return size

    def read(self, path, max_bytes, *, allowed):
        path = Path(path)
        need(path in set(allowed), "File not in explicit branch allowlist")
        self.check()
        raw = read_file(path, self.deadline, max_bytes)
        self.bytes_read_retained += len(raw)
        return raw

    def hash(self, path):
        self.check()
        proof = dict(hash_file(path, self.deadline))
        self.logical_completed_hash_bytes += proof["bytes"]
        self.check()
        return proof

    def publish(self, relative, raw):
        need(type(raw) is bytes and self.check() + len(raw) <= LIMITS["output_bytes"], "Publication bound exceeded")
        _relative(relative)
        path = self.output.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent != self.output:
            checked_path(self.output, path.parent.relative_to(self.output).as_posix())
        publish_bytes(path, raw)
        checked_path(self.output, relative)
        self.check()

    def report(self):
        return dict(wall_seconds=time.monotonic() - self.started, cpu_seconds=time.process_time() - self.cpu_started,
            peak_sampled_process_rss_bytes=self.peak_sampled_rss_bytes, process_lifetime_peak_bytes=self.process_lifetime_peak_bytes,
            logical_completed_hash_bytes=self.logical_completed_hash_bytes, partial_failed_hash_bytes=self.partial_failed_hash_bytes,
            original_row_enumeration_passes=self.original_row_passes, retained_bytes_read=self.bytes_read_retained,
            original_row_enumeration_pass_attempts=self.original_row_pass_attempts,
            partial_original_row_enumeration_status="unknown_in_failed_wrapper_calls" if self.original_row_pass_attempts > self.original_row_passes else "none_observed",
            physical_io_bytes=None, physical_io_status="not_measured", limits=LIMITS,
            enforcement="cooperative checkpoints; process peak may precede this run; physical/cache effects unmeasured",
            model_calls=0, provider_spending_usd=0, network_calls=0, new_downloads=0)


def retained_bundle(manifest):
    """Reconstruct query/config only from retained text; never execute archived code."""
    context = manifest["authorization"]
    query_bytes = {name: text.encode("utf-8") for name, text in context["neutral_files_json"].items()}
    metadata_bytes = {name: text.encode("utf-8") for name, text in context["metadata_files_json"].items()}
    query = {name: parse_json(raw) for name, raw in query_bytes.items()}
    docs = {name: parse_json(raw) for name, raw in metadata_bytes.items()}
    routing = query["selected-case-plan.json"]
    cases = source_inputs.route_contract(routing, stage1_plan_sha256=routing["plan_sha256"])
    plan = parse_json(context["draft_json"])
    return SimpleNamespace(docs=docs, inventory=stage1.inventory_from_metadata(docs["frame"], docs["acquisition"]),
        cases=cases, tasks={c["case_id"]: encode(validate_task(query[c["case_id"] + ".task.json"])) for c in cases},
        snapshot_document=query["source-snapshot.json"], retained=query_bytes, authentication=plan["authentication"],
        metadata_bytes=metadata_bytes, neutral_seal_bytes=context["neutral_seal_json"].encode("utf-8"))


def verify_success_seal(root, seal, *, status, manifest_fingerprint=None):
    need(not (root / "failure-seal.json").exists() and seal["status"] == status, "Failed/unqualified upstream directory")
    chain = read_chain(root / "journal.jsonl")
    need(chain[-1]["event"] == "build_completed" and chain[-1]["details"]["seal_sha256"] == fingerprint(seal) and
         len(chain) >= 2 and seal["journal_prefix_sha256"] == chain[-2]["sha256"], "Upstream terminal/seal binding differs")
    if manifest_fingerprint is not None:
        need(seal["manifest_sha256"] == manifest_fingerprint == chain[-1]["details"]["manifest_sha256"], "Reference fingerprint differs")


def checked_descriptor(descriptor, *, root=WORKSPACE):
    path = Path(descriptor["path"])
    need(path.is_absolute() and path.is_relative_to(root), "Pinned path outside explicit approved root")
    need(checked_path(root, path.relative_to(root).as_posix()) == path, "Unsafe pinned path")
    need(re.fullmatch(r"[0-9a-f]{64}", descriptor.get("sha256", "")) is not None, "External exact byte SHA required")
    return path


def read_descriptor(descriptor, bounds, *, max_bytes=64 * 1024**2):
    path = checked_descriptor(descriptor)
    raw = bounds.read(path, max_bytes, allowed=[path])
    need(digest(raw) == descriptor["sha256"], "External pinned artifact bytes differ")
    return parse_json(raw)


def validate_freeze(plan_raw, ready_raw, expected_ready_sha256):
    need(re.fullmatch(r"[0-9a-f]{64}", expected_ready_sha256 or "") is not None and digest(ready_raw) == expected_ready_sha256,
         "Externally retained exact root READY byte hash required")
    plan, ready = parse_json(plan_raw), parse_json(ready_raw)
    need(plan.get("status") == "DRAFT_NOT_EXECUTABLE" and plan.get("actual_execution_authorized") is False,
         "Underlying DRAFT must not authorize execution")
    need(ready.get("schema_version") == 1 and ready.get("status") == "READY" and ready.get("frozen_by") == "root" and
         ready.get("scope") == METHOD and ready.get("actual_execution_authorized") is True, "Separate root READY required")
    need(ready.get("plan_sha256") == digest(plan_raw) and ready.get("design_sha256") == digest(DESIGN_PATH.read_bytes()),
         "READY must pin exact plan/design bytes")
    need(ready.get("code_sha256") == code_pins() and ready.get("environment") == stage1.environment() and
         ready.get("limits") == LIMITS and ready.get("cutoff") == CUTOFF and ready.get("schedule") == schedule(),
         "Frozen code/environment/limits/cutoff/schedule differs")
    extra = ready.get("extra_code_sha256", {})
    need(set(extra) == set(EXTRA_CODE), "Exact independent analysis/audit/helper/test code pins required")
    for name in EXTRA_CODE:
        need(re.fullmatch(r"[0-9a-f]{64}", extra.get(name, "")) is not None and
             digest(checked_path(WORKSPACE, name).read_bytes()) == extra[name], "Independent analysis/audit code changed")
    need(ready.get("analysis_code_sha256") == extra[ANALYSIS_CODE], "Analyzer code pin differs")
    need(plan["constraints"]["model_calls"] == plan["constraints"]["network_calls"] == plan["constraints"]["new_downloads"] ==
         plan["constraints"]["provider_spending_usd"] == 0, "Forbidden resource authority")
    cases = ready.get("native_cases", {})
    need(list(cases) == list(CASES), "All twelve ordered native case bindings required")
    for case_id, item in cases.items():
        need(item.get("disposition") in ("compiled", "blocked") and re.fullmatch(r"[0-9a-f]{64}", item.get("task_sha256", "")),
             "Unresolved case/task qualification")
        if item["disposition"] == "compiled":
            need(re.fullmatch(r"[0-9a-f]{64}", item.get("reference_sha256", "")) is not None and
                 re.fullmatch(r"[0-9a-f]{64}", item.get("packet_sha256", "")) is not None and
                 all(type(item.get(k)) is int and item[k] >= 0 for k in ("measurement_answerable_facts", "measurement_answerable_groups", "requested_facts")),
                 "Case reference and actual denominators must be frozen")
        else:
            need(item.get("reference_sha256") is None and item.get("blocked_reason"), "Blocked case needs explicit reason and null reference")
    required = ("input_seal", "input_audit", "reference_manifest", "reference_seal", "reference_audit",
                "fixture_manifest", "exposure_dependence", "peer_review", "fictional_qualification")
    need(set(ready.get("inputs", {})) == set(required), "Exact late-input/audit/fixture allowlist required")
    for key in required:
        checked_descriptor(ready["inputs"][key])
    need(re.fullmatch(r"[0-9a-f]{64}", ready.get("reference_manifest_fingerprint", "")) is not None and
         re.fullmatch(r"[0-9a-f]{64}", ready.get("reference_ready_sha256", "")) is not None,
         "Reference byte SHA, canonical fingerprint and retained READY hash are distinct anchors")
    fictional = ready.get("fictional_references", {})
    need(set(fictional) == set(SCENARIOS), "All fourteen fictional reference/denominator bindings required before output")
    for item in fictional.values():
        need(re.fullmatch(r"[0-9a-f]{64}", item.get("task_sha256", "")) is not None, "Fictional task pin missing")
        if item.get("reference_sha256") is None:
            need(item.get("counts") is None, "Absent fictional reference cannot have invented counts")
        else:
            need(re.fullmatch(r"[0-9a-f]{64}", item["reference_sha256"]) is not None and isinstance(item.get("counts"), dict) and
                 set(item["counts"]) == {"requested_facts", "measurement_answerable_facts", "measurement_answerable_groups"} and
                 all(type(v) is int and v >= 0 for v in item["counts"].values()), "Frozen fictional denominators missing")
    return plan, ready


def fictional_oracle():
    """Hand-declared design expectations, not computed from any guard outcome."""
    first = {"F01": "G0", "F02": "G1", "F03": "G2", "F04": "G2", "F09": "G3"}
    rows = {}
    for key in SCENARIOS:
        valid = key.startswith("C")
        rows[key] = dict(truth="VALID_REPORT" if valid else "INVALID",
            first_full_failure=None if valid else first.get(key, "G4"),
            expected_by_policy={"FULL": "admitted" if valid else "rejected",
                "WITHOUT_WRAPPER": "admitted" if valid or key in ("F03", "F04") else "rejected",
                "WIRE_ONLY": "rejected" if key in ("F01", "F08", "F10") else "admitted"},
            scientific_validation="not_established", fixture_domain="generic_JSON_core_and_applicable_P05_predicates")
    return dict(schema_version=1, rows=rows, valid_scenarios=4, invalid_scenarios=10,
        authority="hand-declared design labels; peer review required before READY; no empirical results")


def fixture_packet(case, groups, nodes):
    """Author invented packet data. Does not call a reference compiler."""
    task = source_inputs.build_task(case, groups)
    slots, rawrows = [], []
    source_nodes = {n.source_id: n for n in nodes}
    for record, original in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"]):
        rawrows.append(dict(record_key=record["record_key"], **original))
    declared = {r["record_key"]: r for r in task["records"]}
    for field in task["fields"]:
        record = declared[field["record_key"]]
        node = source_nodes[record["source_id"]]
        binding = dict(source_id=node.source_id, sha256=node.sha256, release_id=node.release_id,
                       locator=record["locator"], field=field["field"])
        slots.append(dict(fact_id="fact:" + fingerprint(dict(task_sha256=fingerprint(task), scope=task["scope"],
            record_key=field["record_key"], source=binding)), record_key=field["record_key"], field=field["field"], source=binding))
    return dict(schema_version=1, packet_type=source_inputs.METHOD, case_id=case["case_id"], role="agent_evidence", agent_visible=True,
        neutral_task=task, task_sha256=fingerprint(task), source_records=rawrows, fact_skeleton=slots,
        normalization_proof={"method": "fictional author configuration; not native P05 Parquet build"},
        source_nodes=encode(nodes), source_proofs=[], unknown_context=source_inputs.UNKNOWN_CONTEXT,
        instruction="Invented literal fields only; no scientific validation.",
        output_contract=dict(wire_format="typed_facts_v1", max_facts=512, max_output_bytes=262144),
        lineage=dict(method=source_inputs.METHOD, computed_at=CUTOFF, input_refs=[dict(kind="original", source_id=n.source_id, sha256=n.sha256)
            for n in nodes], information_cutoff=CUTOFF, reference_inputs=[], evaluation_inputs=[], generation_authority=False))


def author_fictional_fixtures(root):
    """Create only fictional sources/config/oracle. No candidate output or score."""
    root = Path(root).absolute()
    need(root.is_relative_to(WORKSPACE / "data/cache"), "Fictional authoring stays under workspace data/cache")
    root.mkdir(parents=True, exist_ok=False)
    all_files, scenarios = [], {}
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for key in SCENARIOS:
        raw_root = root / key / "originals"
        raw_root.mkdir(parents=True)
        case = dict(case_id="fiction-" + key, targetId="ENSG_FICTIONAL", diseaseId="EFO_FICTIONAL",
                    studyLocusId="locus-fictional", release_id="25.09")
        gwas = dict(id="fictional-evidence", targetId=case["targetId"], diseaseId=case["diseaseId"],
            studyLocusId=case["studyLocusId"], studyId="STUDY_A", variantId="VARIANT_A", datasourceId="gwas_credible_sets",
            datatypeId="genetic_association", publicationDate="2026-01-01", evidenceDate="2026-01-01")
        credible = dict(studyLocusId=case["studyLocusId"], studyId="STUDY_A", variantId="VARIANT_A",
                        beta=1.25, standardError=0.25, pValueMantissa=2.0, pValueExponent=-6)
        if key in ("C02", "F07"):
            credible.update(beta=None, pValueMantissa="")
            del credible["standardError"]
        if key == "C04":
            credible.update({field: None for field in source_inputs.MEASUREMENTS})
        if key == "F09":
            credible["beta"] = True
        if key == "F03":
            gwas["releaseDate"] = "2026-11-02"
        credible_rows = [credible]
        if key in ("C03", "F04"):
            credible_rows.append(dict(credible, studyId="STUDY_B", variantId="VARIANT_B", standardError=-0.5))
        mapping = {"target": [dict(values=dict(id=case["targetId"], approvedSymbol="FICTIONAL_GENE"), locator={})],
            "disease": [dict(values=dict(id=case["diseaseId"], name="Fictional phenotype"), locator={})],
            "hgnc": [dict(values=dict(ensembl_gene_id=case["targetId"], symbol="FICTIONAL_GENE", hgnc_id="HGNC:FICTIONAL", status="Approved"), locator={})]}
        products = [("gwas", {"rows": [gwas]}), ("credible", {"rows": credible_rows}), ("mapping", mapping)]
        if key == "F02":
            products.append(("forbidden", {"invented": "not a real evaluator artifact"}))
        nodes, source_anchors = [], []
        catalog = dict(schema_version=1, datasets=[])
        for name, document in products:
            path = raw_root / (name + ".json")
            payload = canonical(document) + b"\n"
            publish_bytes(path, payload)
            dataset = "fiction_" + name
            role = "evaluation_only" if name == "forbidden" else "reference" if name == "mapping" else "agent_evidence"
            receipt = dict(status="completed", dataset_id=dataset, release_id="25.09", relative_path=path.name,
                sha256=digest(payload), bytes=len(payload), url="https://example.invalid/" + name,
                completed_at_utc=observed.isoformat())
            receipt_raw = canonical(receipt) + b"\n"
            receipt_path = raw_root / (name + ".receipt.json")
            publish_bytes(receipt_path, receipt_raw)
            available = Availability(None, None, None, None, observed.date(), "public_download_receipt", "fictional only",
                                     observed, digest(receipt_raw))
            nodes.append(SourceNode("fiction-" + name, dataset, "25.09", path.name, digest(payload), role,
                available, TemporalClass.CONTEMPORARY, receipt["url"], receipt_path=receipt_path.name, receipt_sha256=digest(receipt_raw)))
            source_anchors.append(dict(path=path.name, sha256=digest(payload), bytes=len(payload)))
            source_anchors.append(dict(path=receipt_path.name, sha256=digest(receipt_raw), bytes=len(receipt_raw)))
            catalog["datasets"].append(dict(dataset_id=dataset, roles=[role]))
        packet_nodes = nodes[:3]
        if key == "F02":
            original = nodes[0]
            nodes[0] = SourceNode(original.source_id, original.dataset_id, original.release_id, original.path,
                original.sha256, original.role, original.availability, original.temporal_classification, original.source_url,
                parents=("fiction-forbidden",), computed_at=observed, method_id="fiction-derived", method_version="1",
                receipt_path=original.receipt_path, receipt_sha256=original.receipt_sha256)
        snapshot = Snapshot(2, "fiction-" + key, Profile.CONTEMPORARY, source_inputs.utc(CUTOFF).date(), False, (), tuple(nodes),
                            str(raw_root), {"scope": "fictional_JSON_only"}, source_inputs.utc(CUTOFF))
        def row(value, source_id, index, family):
            return dict(source_id=source_id, family=family, locator=dict(format="json", pointer=f"/rows/{index}"),
                        physical_row_0based=index, values=value)
        groups = dict(gwas_credible_sets=[row(gwas, "fiction-gwas", 0, "gwas_credible_sets")],
            credible_set=[row(value, "fiction-credible", i, "credible_set") for i, value in enumerate(credible_rows[:1] if key == "F04" else credible_rows)])
        packet = fixture_packet(case, groups, packet_nodes)
        if key == "F01":
            # Altered observation is separately pinned; original source anchor stays stale.
            with (raw_root / "gwas.json").open("ab") as stream:
                stream.write(b" ")
        scenario = dict(schema_version=1, scenario_id=key, fixture_domain="generic_JSON_core_and_applicable_P05_predicates",
            case=case, task=packet["neutral_task"], snapshot=encode(snapshot), catalog=catalog,
            original_source_anchors=source_anchors, packet_path="packet.json", fixture_is_native_P05_build=False)
        scenario_raw, packet_raw = canonical(scenario) + b"\n", canonical(packet) + b"\n"
        publish_bytes(root / key / "scenario.json", scenario_raw)
        publish_bytes(root / key / "packet.json", packet_raw)
        scenarios[key] = dict(scenario_path=key + "/scenario.json", scenario_sha256=digest(scenario_raw),
                             packet_path=key + "/packet.json", packet_sha256=digest(packet_raw))
    oracle_raw = canonical(fictional_oracle()) + b"\n"
    publish_bytes(root / "oracle.json", oracle_raw)
    for path in sorted(root.rglob("*")):
        if path.is_file():
            raw = path.read_bytes()
            all_files.append(dict(path=path.relative_to(root).as_posix(), sha256=digest(raw), bytes=len(raw)))
    need(sum(x["bytes"] for x in all_files if "/originals/" in x["path"]) <= LIMITS["fictional_source_bytes"], "Fictional source cap exceeded")
    manifest = dict(schema_version=1, status="FROZEN_FICTIONAL_SOURCES_ONLY_NOT_STUDY_RESULTS", method=METHOD,
        fixture_domain="generic_JSON_core_and_applicable_P05_predicates", scenarios=scenarios, files=all_files,
        oracle_sha256=digest(oracle_raw), candidate_outputs_created=False, code_sha256=code_pins(),
        model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0)
    publish_bytes(root / "manifest.json", canonical(manifest) + b"\n")
    return manifest


def load_fictional(root, key, manifest, bounds):
    need(key in SCENARIOS and key in manifest["scenarios"], "Unscheduled fictional scenario")
    item = manifest["scenarios"][key]
    paths = [checked_path(root, item[name]) for name in ("scenario_path", "packet_path")]
    with stable_files(paths, deadline=bounds.deadline):
        payloads = [bounds.read(path, 1024**2, allowed=paths) for path in paths]
        for raw, key_hash in zip(payloads, ("scenario_sha256", "packet_sha256")):
            need(digest(raw) == item[key_hash], "Frozen fictional query/packet changed")
    return [parse_json(raw) for raw in payloads]


def fictional_candidate(packet, scenario_id):
    """Untrusted invented candidate attempt, never a FULL-qualified output."""
    raw = literal_report(packet)
    if scenario_id in ("F05", "F06", "F07"):
        output = parse_json(raw)
        fact = next(f for f in output["facts"] if f["source"]["field"] == "beta")
        if scenario_id == "F05":
            fact["value"] = 2.25
        elif scenario_id == "F06":
            fact["source"]["locator"] = dict(format="json", pointer="/rows/999")
        else:
            fact["unknown_reason"] = "field_not_in_schema"
        raw = canonical(output)
    elif scenario_id == "F08":
        raw = raw[:-1] + b',"status":"answered"}'
    elif scenario_id == "F10":
        raw += b" " * (262145 - len(raw))
    need(len(raw) <= LIMITS["retained_raw_bytes"], "Fictional raw retention cap exceeded")
    return raw


def guard_result(function):
    started, cpu_started = time.monotonic(), time.process_time()
    try:
        value = function()
        return dict(status="pass", error_class=None, reason=None, wall_seconds=time.monotonic()-started,
                    cpu_seconds=time.process_time()-cpu_started), value
    except ContractError as error:
        return dict(status="rejected", error_class=type(error).__name__, reason=str(error)[:400],
                    wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu_started), None


def fictional_wrapper(scenario, packet, raw_root, deadline):
    """Actual pure predicates + exhaustive JSON inventory; no Parquet-schema claim."""
    case = scenario["case"]
    mapping = parse_json(read_file(raw_root / "mapping.json", deadline, 1024**2))
    indexes = stage1.mapping_index(mapping)
    groups = dict(gwas_credible_sets=[], credible_set=[])
    for name, family in (("gwas", "gwas_credible_sets"), ("credible", "credible_set")):
        rows = parse_json(read_file(raw_root / (name + ".json"), deadline, 1024**2))["rows"]
        for index, values in enumerate(rows):
            if values.get("studyLocusId") != case["studyLocusId"]:
                continue
            if family == "gwas_credible_sets" and (values.get("targetId"), values.get("diseaseId")) != (case["targetId"], case["diseaseId"]):
                continue
            decision = (stage1.eligibility(values, indexes, cutoff=source_inputs.utc(CUTOFF)) if family == "gwas_credible_sets" else
                        dict(date_guard=stage1.date_guard(values, source_inputs.utc(CUTOFF))))
            reasons = list(decision.get("exclusion_reasons", decision["date_guard"]["exclusion_reasons"]))
            if "annotationDate" in values:
                lower, upper, _ = stage1.source_date_interval(values["annotationDate"], "annotationDate")
                need(lower is None or stage1.interval_status(lower, upper, source_inputs.utc(CUTOFF)) == "within_cutoff", "annotationDate rejected")
            if not reasons:
                groups[family].append(dict(source_id="fiction-" + name, family=family,
                    locator=dict(format="json", pointer=f"/rows/{index}"), physical_row_0based=index, values=values))
    source_inputs.normalization_proof(case, groups["gwas_credible_sets"], indexes)
    rebuilt = source_inputs.build_task(case, groups)
    need(same_json(rebuilt, scenario["task"]) and same_json(rebuilt, packet["neutral_task"]),
         "Exhaustive eligible JSON inventory/task differs; no subset-completeness claim")
    originals = groups["gwas_credible_sets"] + groups["credible_set"]
    need(len(originals) == len(packet["source_records"]) and all(same_json(original["values"], supplied["values"]) and
        same_json(original["locator"], supplied["locator"]) and original["source_id"] == supplied["source_id"]
        for original, supplied in zip(originals, packet["source_records"])), "Packet native values/bindings differ from originals")
    return {"eligible_rows": len(originals), "domain": "generic_JSON_pure_predicates_only"}


def project_decision(stages, policy, *, decision_id):
    required = ("G0",) if policy == "WIRE_ONLY" else ("G0", "G1", "G3", "G4") if policy == "WITHOUT_WRAPPER" else STAGES
    checks = [(stage, stages[stage]["schema_status"] if policy == "WIRE_ONLY" and stage == "G4" else stages[stage]["status"]) for stage in required]
    if policy == "WIRE_ONLY":
        checks.append(("G4", stages["G4"]["schema_status"]))
    rejection = next((stage for stage, status in checks if status == "rejected"), None)
    missing = next((stage for stage, status in checks if status not in ("pass", "rejected")), None)
    verdict = "rejected" if rejection else "no_decision" if missing else "admitted"
    return dict(decision_id=decision_id, policy=policy, verdict=verdict,
        first_failure_stage=rejection, terminal="unexecuted" if verdict == "no_decision" else "returned",
        required_stages=list(required) + (["G4_schema_only"] if policy == "WIRE_ONLY" else []),
        reason=stages[rejection].get("reason") if rejection else "required_stage_not_attempted" if missing else None,
        projection=True, scientific_validation="not_established")


def evaluate_fictional(scenario, packet, raw, bounds, *, approved_fixture_root):
    """Actual guard outcomes only. Oracle labels are not an input."""
    key = scenario["scenario_id"]
    need(key in SCENARIOS, "Unscheduled fictional source scope")
    raw_root = checked_path(Path(approved_fixture_root), key + "/originals")
    need(Path(scenario["snapshot"]["raw_root"]) == raw_root, "Serialized fixture cannot grant a raw root")
    snapshot = decode(Snapshot, scenario["snapshot"])
    task = scenario["task"]
    stages = {key: dict(status="unexecuted", reason="preceding_admission_not_passed", error_class=None) for key in STAGES}
    def integrity():
        paths = [checked_path(raw_root, x["path"]) for x in scenario["original_source_anchors"]]
        with stable_files(paths, deadline=bounds.deadline):
            for item, path in zip(scenario["original_source_anchors"], paths):
                need(bounds.hash(path) == {"sha256": item["sha256"], "bytes": item["bytes"]}, "Fictional original/receipt anchor differs")
        return True
    stages["G0"], _ = guard_result(integrity)
    reference = None
    if stages["G0"]["status"] == "pass":
        def provenance():
            graph = InputGraph(snapshot, raw_root, catalog_index(scenario["catalog"]))
            refs = tuple(graph.nodes)
            need(graph.exclusion(refs, SimpleNamespace(cutoff=source_inputs.utc(CUTOFF))) is None, "Fictional source graph after cutoff")
            paths = [graph.path(n) for n in snapshot.sources] + [checked_path(raw_root, n.receipt_path) for n in snapshot.sources if n.receipt_path]
            with stable_files(paths, deadline=bounds.deadline):
                proofs = graph.verify(refs, {})
            bounds.logical_completed_hash_bytes += sum(p.stat().st_size for p in paths)
            return proofs
        stages["G1"], _ = guard_result(provenance)
    if stages["G1"]["status"] == "pass":
        paths = [checked_path(raw_root, item["path"]) for item in scenario["original_source_anchors"]]
        with stable_files(paths, deadline=bounds.deadline):
            stages["G2"], _ = guard_result(lambda: fictional_wrapper(scenario, packet, raw_root, bounds.deadline))
        def base():
            compiled = compile_reference(task, snapshot, raw_root, scenario["catalog"], deadline=bounds.deadline, approved_raw_root=raw_root)
            # Unchanged replay, not deserializing a reference into a trusted type.
            verified = verify_reference(encode(compiled.document), compiled.fingerprint, task, snapshot, raw_root,
                scenario["catalog"], deadline=bounds.deadline, approved_raw_root=raw_root)
            bounds.logical_completed_hash_bytes += 4 * sum(x["bytes"] for x in scenario["original_source_anchors"])
            return verified
        stages["G3"], reference = guard_result(base)
    adapter = adapt_output(raw, wire_format="typed_facts_v1", task_id=task["task_id"], task_sha256=fingerprint(task))
    schema_status = "pass" if adapter["status"] == "scorable" else "rejected"
    score = None
    if reference is not None:
        exact, score = report_exactness(reference, raw, cell_id="S-" + scenario["scenario_id"])
        stages["G4"] = dict(status="pass" if exact else "rejected", reason=None if exact else "not_complete_exact_report",
                            error_class=None, schema_status=schema_status)
    else:
        stages["G4"] = dict(status="unexecuted", reason="no_source_verified_reference", error_class=None, schema_status=schema_status)
    decisions = [project_decision(stages, p, decision_id=f"D-S-{scenario['scenario_id']}-{p}") for p in POLICIES]
    return dict(stages=stages, decisions=decisions, score=score, adapter_status=adapter["status"],
        raw_terminal="malformed" if adapter["status"] == "malformed" else "returned",
        measurement_completion=score["completion"] if score is not None else None,
        primary_coverage=score["primary"]["coverage"] if score is not None else None,
        reference_fingerprint=reference.fingerprint if reference is not None else None,
        reference_counts=reference_counts(reference) if reference is not None else None,
        fact_accounting=fact_accounting(reference, raw) if reference is not None else None,
        scientific_validation="not_established")


def reference_counts(reference):
    facts = reference.document["facts"]
    measurements = [f for f in facts if f["family"] == "reported_measurement" and f["value"] is not None]
    return dict(requested_facts=len(facts), measurement_answerable_facts=len(measurements),
        measurement_answerable_groups=len({(f["record_key"], f["group"]) for f in measurements}))


def field_at(document, dotted):
    value = document
    for part in dotted.split("."):
        value = value[part]
    return value


def admitted_audit(descriptor, bounds, *, required_binding):
    audit = read_descriptor(descriptor, bounds)
    need(isinstance(audit.get("status"), str) and audit["status"].startswith("PASS") and
         not audit.get("issues") and not audit.get("findings"), "Required independent/qualification audit is not PASS")
    bindings = descriptor.get("expected_fields", {})
    need(bindings and required_binding in bindings.values(), "Audit descriptor must bind the relevant sealed artifact/code")
    for path, expected in bindings.items():
        need(same_json(field_at(audit, path), expected), "Audit subject/version binding differs")
    return audit


def verify_native_references(ready, bounds):
    """Evaluator branch only: anchor archived wrapper and obtain genuine objects."""
    inputs = ready["inputs"]
    input_seal = read_descriptor(inputs["input_seal"], bounds)
    input_root = checked_descriptor(inputs["input_seal"]).parent
    need(input_root.parent == OUTPUT_ROOT and input_root.name.startswith(source_inputs.OUTPUT_PREFIX), "Unapproved native packet root")
    verify_success_seal(input_root, input_seal, status="completed_source_only_stage2_inputs")
    admitted_audit(inputs["input_audit"], bounds, required_binding=inputs["input_seal"]["sha256"])
    manifest = read_descriptor(inputs["reference_manifest"], bounds)
    manifest_fp = ready["reference_manifest_fingerprint"]
    need(fingerprint(manifest) == manifest_fp, "External canonical reference manifest fingerprint differs")
    reference_root = checked_descriptor(inputs["reference_manifest"]).parent
    need(reference_root.parent == reference_builder.OUTPUT_ROOT and reference_root.name.startswith(reference_builder.OUTPUT_PREFIX) and
         checked_descriptor(inputs["reference_manifest"]).name == "references.json", "Unapproved evaluator reference root")
    need(checked_descriptor(inputs["reference_seal"]) == reference_root / "seal.json", "Reference seal from another root")
    reference_seal = read_descriptor(inputs["reference_seal"], bounds)
    verify_success_seal(reference_root, reference_seal, status="sealed_verified_source_references", manifest_fingerprint=manifest_fp)
    record = [x for x in reference_seal["artifacts"] if x["path"] == "references.json"]
    need(len(record) == 1 and record[0]["sha256"] == inputs["reference_manifest"]["sha256"], "Source seal does not bind exact manifest bytes")
    admitted_audit(inputs["reference_audit"], bounds, required_binding=manifest_fp)
    admitted_audit(inputs["peer_review"], bounds, required_binding=code_pins()[Path(__file__).relative_to(WORKSPACE).as_posix()])
    qualification = admitted_audit(inputs["fictional_qualification"], bounds, required_binding=code_pins()[Path(__file__).relative_to(WORKSPACE).as_posix()])
    need(qualification.get("qualification_only") is True and qualification.get("native_outputs_executed") == 0 and
         qualification.get("scenario_count") == 14 and qualification.get("fictional_references") == ready["fictional_references"] and
         qualification.get("fixture_manifest_sha256") == inputs["fixture_manifest"]["sha256"], "Fictional qualification/fixture reference binding differs")
    dependence = read_descriptor(inputs["exposure_dependence"], bounds)
    need(dependence.get("status") in ("FROZEN", "READY") and dependence.get("case_ids") == list(CASES) and
         dependence.get("other_exposure") == "UNKNOWN" and dependence.get("independent_studies_established") is False,
         "Exposure/dependence register unqualified or missing")
    registered = {item["case_id"]: item for item in dependence["native_cases"]}
    need(list(registered) == list(CASES), "Source-only register native inventory differs")
    bundle = retained_bundle(manifest)
    need([x["case_id"] for x in bundle.cases] == list(CASES) and set(bundle.tasks) == set(CASES), "Fixed native inventory differs")
    approved_raw_root = Path(ready["approved_raw_root"])
    need(approved_raw_root == reference_builder.RAW_ROOT, "READY cannot grant another native source root")
    replay_root = bounds.output / "_private/reference-replay"
    replay_root.mkdir(parents=True, exist_ok=False)
    checked_path(bounds.output, "_private/reference-replay")
    replay_bounds = reference_builder.Bounds(replay_root, deadline=bounds.deadline)
    bounds.original_row_pass_attempts += 1
    try:
        verified = reference_builder.verify_p05_references(manifest, manifest_fp, bundle, replay_bounds,
            approved_raw_root=approved_raw_root, expected_ready_sha256=ready["reference_ready_sha256"])
        bounds.original_row_passes += 1
    finally:
        bounds.logical_completed_hash_bytes += replay_bounds.logical_hashed_bytes + replay_bounds.logical_base_completed_hash_bytes
    bounds.check()
    packet_specs = {}
    sealed_packets = {x["path"]: x for x in input_seal["artifacts"] if x["path"].startswith("packets/")}
    for key in CASES:
        frozen = ready["native_cases"][key]
        need(fingerprint(bundle.tasks[key]) == frozen["task_sha256"], "Case task differs from frozen neutral query")
        need(registered[key]["task_sha256"] == frozen["task_sha256"], "Independent source-register task differs")
        if key in verified:
            reference = verified[key]
            need(all(registered[key][name] == frozen[name] for name in ("requested_facts", "measurement_answerable_facts",
                     "measurement_answerable_groups")), "Independent source-register denominator differs")
            need(frozen["disposition"] == "compiled" and reference.fingerprint == frozen["reference_sha256"] and
                 all(frozen[name] == value for name, value in reference_counts(reference).items()), "Case/reference/denominator differs")
            relative = "packets/" + key + ".json"
            need(relative in sealed_packets and sealed_packets[relative]["sha256"] == frozen["packet_sha256"], "Native packet pin differs")
            packet_specs[key] = dict(path=str(checked_path(input_root, relative)), sha256=frozen["packet_sha256"],
                                    task_sha256=frozen["task_sha256"], blocked_reason=None)
        else:
            need(frozen["disposition"] == "blocked" and manifest["cases"][key]["disposition"]["status"] == "blocked", "Case disposition changed")
            packet_specs[key] = dict(path=None, sha256=None, task_sha256=frozen["task_sha256"], blocked_reason=frozen["blocked_reason"])
    return verified, packet_specs, dict(reference_manifest_fingerprint=manifest_fp,
        reference_ready_sha256=ready["reference_ready_sha256"], source_replay="one full wrapper replay amortized across native policies/cells",
        independent_audit="admitted sealed prior source audit; later final output audit remains separate",
        wrapper_resources=replay_bounds.report(), scientific_validation="not_established")


def generate_native_case(case_id, spec, bounds):
    """Generation branch: allowlisted single packet only, no evaluator parameters."""
    need(case_id in CASES and set(spec) == {"path", "sha256", "task_sha256", "blocked_reason"}, "Generation spec has extra/evaluator fields")
    need(spec["blocked_reason"] is None, "Blocked case cannot generate")
    path = Path(spec["path"])
    need(path.name == case_id + ".json" and path.parent.name == "packets" and path.parent.parent.parent == OUTPUT_ROOT and
         path.parent.parent.name.startswith(source_inputs.OUTPUT_PREFIX), "Generation path outside native packet allowlist")
    checked_path(path.parent.parent, "packets/" + case_id + ".json")
    with stable_files([path], deadline=bounds.deadline):
        raw = bounds.read(path, source_inputs.LIMITS["case_product_bytes"], allowed=[path])
    need(digest(raw) == spec["sha256"], "Audited native packet byte SHA differs")
    packet = parse_json(raw)
    need(packet["case_id"] == case_id and packet["task_sha256"] == spec["task_sha256"], "Native generation case/task differs")
    return literal_report(packet), literal_report(packet, always_abstain=True)


def verify_fixture_manifest(ready, bounds):
    descriptor = ready["inputs"]["fixture_manifest"]
    path = checked_descriptor(descriptor)
    root = path.parent
    need(root.is_relative_to(WORKSPACE / "data/cache") and path.name == "manifest.json", "Only isolated fictional cache root permitted")
    manifest = read_descriptor(descriptor, bounds)
    need(manifest["status"] == "FROZEN_FICTIONAL_SOURCES_ONLY_NOT_STUDY_RESULTS" and manifest["candidate_outputs_created"] is False and
         manifest["code_sha256"] == code_pins() and tuple(manifest["scenarios"]) == SCENARIOS, "Fictional source/config freeze differs")
    paths = [checked_path(root, item["path"]) for item in manifest["files"]]
    with stable_files(paths, deadline=bounds.deadline):
        for item, actual in zip(manifest["files"], paths):
            need(bounds.hash(actual) == {"sha256": item["sha256"], "bytes": item["bytes"]}, "Frozen observed fictional bytes differ")
    oracle = parse_json(read_file(root / "oracle.json", bounds.deadline, 1024**2))
    need(digest(canonical(oracle) + b"\n") == manifest["oracle_sha256"] and oracle == fictional_oracle(), "Hand-declared fixture oracle differs")
    return root, manifest, oracle


def blank_ledgers():
    fixed = schedule()
    outputs = {x["cell_id"]: dict(x, terminal="unexecuted", received_terminal=None, raw_path=None,
        raw_sha256=None, raw_bytes=None, reason="not_dispatched", core_score=None, strict_exact_report=None,
        full_source_admitted=None, full_verified_exact=None, fact_accounting=None) for x in fixed["output_cells"]}
    decisions = {x["decision_id"]: dict(x, verdict="no_decision", terminal="unexecuted", first_failure_stage=None,
        reason="not_dispatched", scientific_validation="not_established") for x in fixed["decision_cells"]}
    return outputs, decisions


def retain_fictional_metrics(cell, result):
    admitted = all(result["stages"][key]["status"] == "pass" for key in ("G0", "G1", "G2", "G3"))
    exact = result["stages"]["G4"]["status"] == "pass" if result["score"] is not None else None
    cell.update(terminal=result["raw_terminal"], core_score=encode(result["score"]) if result["score"] is not None else None,
        strict_exact_report=exact, full_source_admitted=admitted, full_verified_exact=bool(admitted and exact),
        fact_accounting=result["fact_accounting"])


def reserve_output(output):
    output = Path(output)
    need(output.is_absolute() and output.parent == OUTPUT_ROOT and
         re.fullmatch(OUTPUT_PREFIX + r"\d{8}T\d{6}Z", output.name), "Exclusive approved new experiment output leaf required")
    checked_path(OUTPUT_ROOT.parent, OUTPUT_ROOT.name)
    import subprocess
    need(subprocess.run(["git", "check-ignore", "--quiet", "--", str(output)], cwd=WORKSPACE, capture_output=True).returncode == 0,
         "Experiment output must already be git-ignored")
    need(not output.exists(), "Existing output is inspect-only; never resume/overwrite")
    return output


def finalize_ledger(output, journal, ledger, *, expected_ready_sha256=None):
    """Independent bounded terminal writes; cleanup failures cannot qualify success.

    If storage rejects every write, durability cannot be promised. Attempt an
    emergency ledger and an independent failure seal, preserve errors, and never
    replace an existing artifact. No expired deadline/source reads are needed.
    """
    errors = []
    def failed(where, error):
        errors.append(dict(stage=where, error_class=type(error).__name__, reason=str(error)[:200]))
    try:
        raw = canonical(ledger) + b"\n"
        need(len(raw) <= 16 * 1024**2, "Terminal metadata reserve exceeded")
    except BaseException as error:
        failed("terminal_full_ledger_serialization", error)
        # Known primitive fields only. Keep the entire scheduled terminal frame
        # when an optional score/resource/guard payload is not serializable.
        fallback_outputs, fallback_decisions = blank_ledgers()
        for kind, defaults, identity in (("output_cells", fallback_outputs, "cell_id"),
                                         ("decision_cells", fallback_decisions, "decision_id")):
            for cell in ledger.get(kind, []):
                if not isinstance(cell, dict) or cell.get(identity) not in defaults:
                    continue
                target = defaults[cell[identity]]
                for key in ("terminal", "received_terminal", "raw_path", "raw_sha256", "raw_bytes", "reason", "verdict", "first_failure_stage"):
                    value = cell.get(key)
                    if value is None or type(value) in (bool, int) or type(value) is str and len(value) <= 1024:
                        target[key] = value
                if target.get("terminal") not in TERMINALS:
                    target.update(terminal="failed", reason="invalid_terminal_in_unserializable_ledger")
        minimal = dict(schema_version=1, status="FAILED_PARTIAL_NOT_QUALIFIED", planned_output_cells=38, planned_decisions=90,
            output_cells=list(fallback_outputs.values()), decision_cells=list(fallback_decisions.values()),
            failure=dict(stage="terminal_serialization", errors=errors), scientific_validation="not_established",
            optional_full_metadata="unavailable; no source/coverage claim qualified")
        raw = canonical(minimal) + b"\n"
    ledger_written = False
    try:
        publish_bytes(output / "ledger.json", raw)
        ledger_written = True
    except BaseException as error:
        failed("terminal_ledger_publication", error)
        try:
            publish_bytes(output / "emergency-ledger.json", raw)
        except BaseException as emergency:
            failed("emergency_ledger_publication", emergency)
    for kind, cells, identity in (("cell_terminal", ledger["output_cells"], "cell_id"),
                                  ("decision_terminal", ledger["decision_cells"], "decision_id")):
        for cell in cells:
            try:
                details = {identity: cell[identity], "terminal": cell["terminal"]}
                if kind == "cell_terminal":
                    details["raw_sha256"] = cell.get("raw_sha256")
                else:
                    details["verdict"] = cell["verdict"]
                journal.append(kind, **details)
            except BaseException as error:
                failed("terminal_journal_append:" + cell[identity], error)
    artifacts = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "journal.jsonl":
            try:
                artifacts.append(dict(path=path.relative_to(output).as_posix(), sha256=digest(path.read_bytes()), bytes=path.stat().st_size))
            except BaseException as error:
                failed("terminal_artifact_hash", error)
    failed_run = bool(ledger.get("failure") or errors)
    seal = dict(schema_version=1, status="FAILED_PARTIAL_NOT_QUALIFIED" if failed_run else ledger["status"],
        artifacts=artifacts, intended_ledger_sha256=digest(raw), ledger_written=ledger_written,
        journal_prefix_sha256=journal.events[-1]["sha256"] if journal.events else None,
        expected_ready_sha256=expected_ready_sha256, lifecycle_errors=list(errors),
        retry_policy="none; inspect only; no resume/overwrite", scientific_validation="not_established")
    try:
        journal.append("experiment_failed" if failed_run else "experiment_completed", seal_sha256=fingerprint(seal), ledger_sha256=digest(raw))
    except BaseException as error:
        failed("terminal_completion_append", error)
    try:
        journal.close()
    except BaseException as error:
        failed("terminal_journal_close", error)
    if errors:
        failed_run = True
        seal.update(status="FAILED_PARTIAL_NOT_QUALIFIED", lifecycle_errors=list(errors), terminal_binding_valid=False)
    name = "failure-seal.json" if failed_run else "seal.json"
    try:
        publish_bytes(output / name, canonical(seal) + b"\n")
    except BaseException as error:
        failed("terminal_seal_publication", error)
        failed_run = True
        retained_frame = parse_json(raw)
        fallback = dict(seal, status="FAILED_PARTIAL_NOT_QUALIFIED", lifecycle_errors=errors, terminal_binding_valid=False,
                        output_cells=retained_frame["output_cells"], decision_cells=retained_frame["decision_cells"])
        try:
            publish_bytes(output / ("emergency-failure-seal.json" if name == "failure-seal.json" else "failure-seal.json"), canonical(fallback) + b"\n")
        except BaseException as emergency:
            failed("emergency_failure_seal_publication", emergency)
    if failed_run and not ledger.get("failure"):
        ledger["failure"] = dict(stage="terminal_finalization", error_class="LifecycleFailure", errors=errors)
        ledger["status"] = "FAILED_PARTIAL_NOT_QUALIFIED"
    return failed_run, errors


def terminal_aggregate(planned, scores):
    try:
        return encode(aggregate_cells(planned, scores)) if planned else None, None
    except BaseException as error:
        return None, dict(stage="terminal_core_aggregation", error_class=type(error).__name__, reason=str(error)[:400])


def terminal_resources(bounds):
    try:
        return bounds.report(), None
    except BaseException as error:
        return dict(status="unknown_terminal_resource_report", model_calls=0, network_calls=0, new_downloads=0), dict(
            stage="terminal_resource_report", error_class=type(error).__name__, reason=str(error)[:400])


def qualify_fictional_fixtures(fixture_root, output, *, expected_manifest_sha256):
    """Real JSON guard/retention qualification only; never opens native sources.

    Native 24 outputs/48 decisions remain explicitly unexecuted. This is a test
    artifact, not the locked 38/90 study. A fresh output leaf is mandatory.
    """
    fixture_root, output = Path(fixture_root).absolute(), Path(output).absolute()
    need(fixture_root.is_relative_to(WORKSPACE / "data/cache") and output.is_relative_to(WORKSPACE / "data/cache"),
         "Fictional qualification stays in isolated cache")
    checked_path(output.parent.parent, output.parent.name)
    journal = RunJournal(output, kind="build")
    bounds = Bounds(output, seconds=300)
    outputs, decisions = blank_ledgers()
    guards, bindings, failure, qualification_pins = {}, {}, None, {}
    try:
        qualification_pins = code_pins()
        config = dict(inputs=dict(fixture_manifest=dict(path=str(fixture_root / "manifest.json"), sha256=expected_manifest_sha256)))
        fixture_root, manifest, oracle = verify_fixture_manifest(config, bounds)
        for key in SCENARIOS:
            cell_id = "S-" + key
            scenario, packet = load_fictional(fixture_root, key, manifest, bounds)
            journal.append("dispatch", cell_id=cell_id, domain="fictional_qualification_only", retry_policy="none")
            outputs[cell_id].update(terminal="failed", reason="fictional_qualification_before_return")
            raw = fictional_candidate(packet, key)
            relative = "raw/" + cell_id + ".json"
            bounds.publish(relative, raw)
            outputs[cell_id].update(terminal="returned", received_terminal="returned", raw_path=relative,
                raw_sha256=digest(raw), raw_bytes=len(raw), reason=None)
            result = evaluate_fictional(scenario, packet, raw, bounds, approved_fixture_root=fixture_root)
            retain_fictional_metrics(outputs[cell_id], result)
            guards[cell_id] = result["stages"]
            bindings[key] = dict(task_sha256=fingerprint(scenario["task"]), reference_sha256=result["reference_fingerprint"], counts=result["reference_counts"])
            for decision in result["decisions"]:
                decisions[decision["decision_id"]].update(decision)
                need(decision["verdict"] == oracle["rows"][key]["expected_by_policy"][decision["policy"]], "Fictional qualification differs from declared hypothesis")
                if decision["policy"] == "FULL":
                    need(decision["first_failure_stage"] == oracle["rows"][key]["first_full_failure"], "Fictional first-stage hypothesis differs")
        bounds.check()
    except BaseException as error:
        failure = dict(stage="fictional_qualification", error_class=type(error).__name__, reason=str(error)[:400])
        terminal = "interrupted" if isinstance(error, KeyboardInterrupt) else "timeout" if isinstance(error, TimeoutError) else "failed"
        for cell in outputs.values():
            if cell["terminal"] == "failed" and cell["received_terminal"] is None:
                cell.update(terminal=terminal, reason=failure["error_class"])
    resources, resource_failure = terminal_resources(bounds)
    failure = failure or resource_failure
    ledger = dict(schema_version=1, status="FAILED_FICTIONAL_QUALIFICATION" if failure else "PASS_FICTIONAL_QUALIFICATION_ONLY",
        qualification_only=True, native_outputs_executed=0, scenario_count=14, reviewed_code_sha256=qualification_pins.get(Path(__file__).relative_to(WORKSPACE).as_posix()),
        code_sha256=qualification_pins, fixture_manifest_sha256=expected_manifest_sha256, fictional_references=bindings,
        planned_output_cells=38, planned_decisions=90, output_cells=list(outputs.values()), decision_cells=list(decisions.values()),
        guards=guards, resources=resources, resource_report_error=resource_failure, failure=failure, scientific_validation="not_established")
    finalize_ledger(output, journal, ledger)
    if ledger["failure"]:
        raise ContractError("Fictional qualification failed; inspect retained failure metadata")
    return ledger


def execute(output, *, expected_ready_sha256):
    """Actual run only through an external root READY. No native run during tests."""
    output = reserve_output(output)
    journal = RunJournal(output, kind="build")  # exclusive reservation BEFORE dispatch/authorization
    bounds = Bounds(output)
    extra_locks = ExitStack()
    outputs, decisions = blank_ledgers()
    scores, planned_scores, guard_records, provenance = [], [], {}, None
    native_qualification = {key: dict(case_id=key, disposition="unverified", measurement_answerable_facts=None,
        measurement_answerable_groups=None, requested_facts=None, task_sha256=None, reference_sha256=None) for key in CASES}
    frozen_inputs, subject_bindings = None, None
    analysis_code_sha256, extra_code_sha256 = None, None
    stage, failure = "root_authorization", None
    try:
        with stable_files([PLAN_PATH, READY_PATH, DESIGN_PATH] + code_paths(), deadline=bounds.deadline):
            plan_raw = bounds.read(PLAN_PATH, 1024**2, allowed=[PLAN_PATH])
            ready_raw = bounds.read(READY_PATH, 1024**2, allowed=[READY_PATH])
            _, ready = validate_freeze(plan_raw, ready_raw, expected_ready_sha256)
            extra_locks.enter_context(stable_files([checked_path(WORKSPACE, name) for name in EXTRA_CODE], deadline=bounds.deadline))
            frozen_inputs, subject_bindings = ready["inputs"], ready["native_cases"]
            analysis_code_sha256, extra_code_sha256 = ready["analysis_code_sha256"], ready["extra_code_sha256"]
            bounds.publish("authorization.json", canonical(dict(plan_json=plan_raw.decode("utf-8"), ready_json=ready_raw.decode("utf-8"),
                expected_ready_sha256=expected_ready_sha256, method=METHOD)) + b"\n")
            stage = "native_source_inclusive_verification"
            journal.append("build_stage", stage=stage)
            references, generation_specs, provenance = verify_native_references(ready, bounds)
            for key in CASES:
                if key in references:
                    native_qualification[key].update(disposition="compiled", **reference_counts(references[key]),
                        task_sha256=references[key].document["task_sha256"], reference_sha256=references[key].fingerprint)
                else:
                    native_qualification[key].update(disposition="blocked", reason=generation_specs[key]["blocked_reason"],
                        task_sha256=ready["native_cases"][key]["task_sha256"])
            fixture_root, fixture_manifest, oracle = verify_fixture_manifest(ready, bounds)
            need(set(ready.get("fictional_references", {})) == set(SCENARIOS), "All fictional core reference/denominator bindings must be frozen")
            for case_id in CASES:
                if case_id not in references:
                    for arm in ("L", "A"):
                        outputs[f"N-{arm}-{case_id}"]["reason"] = "frozen_reference_blocked:" + generation_specs[case_id]["blocked_reason"]
                    continue
                stage = "native_packet_only_generation:" + case_id
                journal.append("dispatch", case_id=case_id, output_cells=[f"N-L-{case_id}", f"N-A-{case_id}"], retry_policy="none")
                for arm in ("L", "A"):
                    outputs[f"N-{arm}-{case_id}"].update(terminal="failed", reason="generation_interrupted_before_return")
                pair_wall, pair_cpu = time.monotonic(), time.process_time()
                literal, abstain = generate_native_case(case_id, generation_specs[case_id], bounds)
                pair_resources = dict(wall_seconds=time.monotonic()-pair_wall, cpu_seconds=time.process_time()-pair_cpu,
                    basis="shared packet read plus literal/abstain pair; count once per case, not once per arm")
                for arm, raw in (("L", literal), ("A", abstain)):
                    cell_id = f"N-{arm}-{case_id}"
                    need(len(raw) <= LIMITS["retained_raw_bytes"], "Native output retention bound exceeded")
                    relative = "raw/" + cell_id + ".json"
                    bounds.publish(relative, raw)
                    outputs[cell_id].update(terminal="returned", received_terminal="returned", raw_path=relative,
                        raw_sha256=digest(raw), raw_bytes=len(raw), reason=None)
                    reference = references[case_id]
                    score_wall, score_cpu = time.monotonic(), time.process_time()
                    exact, score = report_exactness(reference, raw, cell_id=cell_id)
                    outputs[cell_id].update(core_score=encode(score), strict_exact_report=exact, full_source_admitted=True,
                        full_verified_exact=exact, fact_accounting=fact_accounting(reference, raw), shared_case_generation_resources=pair_resources,
                        scoring_resources=dict(wall_seconds=time.monotonic()-score_wall, cpu_seconds=time.process_time()-score_cpu))
                    scores.append(score)
                    frozen = ready["native_cases"][case_id]
                    planned_scores.append(dict(cell_id=cell_id, task_id=reference.document["task_id"],
                        task_sha256=frozen["task_sha256"], reference_sha256=frozen["reference_sha256"]))
                    stages = {key: dict(status="pass", reason=None, evidence="amortized_source_wrapper_and_sealed_input_audit") for key in STAGES}
                    stages["G4"] = dict(status="pass" if exact else "rejected", schema_status="pass" if score["adapter_status"] == "scorable" else "rejected",
                        reason=None if exact else "not_complete_exact_report")
                    guard_records[cell_id] = stages
                    for policy in POLICIES if arm == "L" else ("FULL",):
                        identifier = f"D-{cell_id}-{policy}"
                        decisions[identifier].update(project_decision(stages, policy, decision_id=identifier))
                    journal.append("output_returned", cell_id=cell_id, raw_sha256=digest(raw), raw_bytes=len(raw),
                                   exact_report=exact, measurement_completion=score["completion"])
            for key in SCENARIOS:
                stage = "fictional_candidate_and_guards:" + key
                scenario, packet = load_fictional(fixture_root, key, fixture_manifest, bounds)
                cell_id = "S-" + key
                journal.append("dispatch", cell_id=cell_id, domain="fictional_JSON_core", retry_policy="none")
                outputs[cell_id].update(terminal="failed", reason="fictional_candidate_interrupted_before_return")
                raw = fictional_candidate(packet, key)
                relative = "raw/" + cell_id + ".json"
                bounds.publish(relative, raw)
                outputs[cell_id].update(terminal="returned", received_terminal="returned", raw_path=relative,
                                       raw_sha256=digest(raw), raw_bytes=len(raw), reason=None)
                result = evaluate_fictional(scenario, packet, raw, bounds, approved_fixture_root=fixture_root)
                frozen = ready["fictional_references"][key]
                need(frozen == dict(task_sha256=fingerprint(scenario["task"]), reference_sha256=result["reference_fingerprint"],
                    counts=result["reference_counts"]), "Fictional source/core-reference denominator differs from pre-run freeze")
                retain_fictional_metrics(outputs[cell_id], result)
                guard_records[cell_id] = result["stages"]
                for decision in result["decisions"]:
                    decisions[decision["decision_id"]].update(decision, expected_verdict=oracle["rows"][key]["expected_by_policy"][decision["policy"]],
                                                           fixture_truth=oracle["rows"][key]["truth"])
                if result["score"] is not None:
                    score = result["score"]
                    scores.append(score)
                    planned_scores.append(dict(cell_id=cell_id, task_id=score["task_id"], task_sha256=frozen["task_sha256"], reference_sha256=frozen["reference_sha256"]))
                journal.append("output_returned", cell_id=cell_id, raw_sha256=digest(raw), raw_bytes=len(raw), normalized_terminal=result["raw_terminal"])
            stage = "all_cell_accounting"
            need(len(outputs) == 38 and len(decisions) == 90, "Schedule accounting changed")
            bounds.check()
    except BaseException as error:
        failure = dict(stage=stage, error_class=type(error).__name__, reason=str(error)[:400])
        terminal = "interrupted" if isinstance(error, KeyboardInterrupt) else "timeout" if isinstance(error, TimeoutError) else "failed"
        for cell in outputs.values():
            if cell["terminal"] == "failed" and cell["received_terminal"] is None:
                cell.update(terminal=terminal, reason=failure["error_class"])
        try:
            journal.fail(error, stage)
        except BaseException:
            failure["journal_failure"] = True
    finally:
        try:
            extra_locks.close()
        except BaseException as cleanup:
            detail = dict(stage="frozen_extra_code_cleanup", error_class=type(cleanup).__name__, reason=str(cleanup)[:400])
            if failure:
                failure.setdefault("cleanup_errors", []).append(detail)
            else:
                failure = detail
        # Bounded terminal metadata needs no further source reads or expired deadline.
        for cell in outputs.values():
            if cell.get("terminal") not in TERMINALS:
                cell.update(terminal="failed", reason="invalid_terminal_contract")
                failure = failure or dict(stage="terminal_disposition_contract", error_class="ContractError", reason="Invalid output terminal")
        aggregate, aggregate_failure = terminal_aggregate(planned_scores, scores)
        failure = failure or aggregate_failure
        resources, resource_failure = terminal_resources(bounds)
        failure = failure or resource_failure
        included = [item["cell_id"] for item in planned_scores]
        intended = (["N-" + arm + "-" + key for key, item in (subject_bindings or {}).items() if item["disposition"] == "compiled" for arm in ("L", "A")] +
                    ["S-" + key for key, item in ready.get("fictional_references", {}).items() if item["reference_sha256"] is not None]) if frozen_inputs else []
        ledger = dict(schema_version=1, method=METHOD, status="FAILED_PARTIAL_NOT_QUALIFIED" if failure else "COMPLETED_PENDING_INDEPENDENT_AUDIT",
            planned_output_cells=38, planned_decisions=90, native_units=12, independent_studies=None,
            output_cells=list(outputs.values()), decision_cells=list(decisions.values()), guards=guard_records,
            native_qualification=native_qualification, frozen_inputs=frozen_inputs, subject_bindings=subject_bindings,
            analysis_code_sha256=analysis_code_sha256, extra_code_sha256=extra_code_sha256,
            core_aggregate=aggregate, core_aggregate_error=aggregate_failure, core_aggregate_scope=dict(label="secondary genuinely source-verified scored subset; outer38/90 ledger is primary",
                intended_cell_ids=intended, included_cell_ids=included, excluded_cell_ids=[key for key in outputs if key not in included]),
            source_verification=provenance, resources=resources, resource_report_error=resource_failure, failure=failure,
            scientific_validation="not_established", model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0)
        finalize_ledger(output, journal, ledger, expected_ready_sha256=expected_ready_sha256)
    if ledger["failure"]:
        raise ContractError("Experiment failed; all scheduled terminals retained; inspect failure seal")
    return ledger


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--draft", action="store_true")
    mode.add_argument("--author-fictional", action="store_true")
    mode.add_argument("--qualify-fictional", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ready-sha256")
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--fixture-sha256")
    args = parser.parse_args(argv)
    if args.draft:
        need(args.output is None and args.ready_sha256 is None, "DRAFT takes no run arguments")
        print(canonical(make_draft()).decode("utf-8"))
    elif args.author_fictional:
        need(args.output is not None and args.ready_sha256 is None, "Fictional authoring takes only a new cache output")
        result = author_fictional_fixtures(args.output)
        print(canonical(dict(status=result["status"], scenarios=len(result["scenarios"]), candidate_outputs_created=False,
                             manifest_sha256=digest((args.output / "manifest.json").read_bytes()))).decode("utf-8"))
    elif args.qualify_fictional:
        need(args.output is not None and args.fixtures is not None and args.fixture_sha256 is not None and args.ready_sha256 is None,
             "Qualification needs only fictional cache fixtures, exact manifest hash and fresh cache output")
        result = qualify_fictional_fixtures(args.fixtures, args.output, expected_manifest_sha256=args.fixture_sha256)
        print(canonical(dict(status=result["status"], native_outputs_executed=0, scenario_count=14)).decode("utf-8"))
    else:
        need(args.output is not None and args.ready_sha256 is not None, "Actual run requires new output and externally retained root READY hash")
        execute(args.output, expected_ready_sha256=args.ready_sha256)


if __name__ == "__main__":
    main()
