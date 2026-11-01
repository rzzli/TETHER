"""P05 independent ORIGINALS -> evaluator-only references, default-deny.

Only --draft is authorized by the checked-in DRAFT. Source reads require a
separate root READY and its externally supplied byte hash. Neutral task files
are routing configuration; generation packets/captures are never opened.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE / "tools/science"))
import prepare_source_validation_set as stage1
import prepare_source_validation_inputs as source_inputs
from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.provenance import InputGraph, catalog_index, check_role
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.source_fact_sources import compile_reference, validate_task, verify_reference
from asof.study.proofs import _relative
from asof.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files

ASSETS = stage1.ASSETS
PLAN_PATH = ASSETS / "REFERENCE-PLAN-DRAFT-v1.json"
READY_PATH = ASSETS / "REFERENCE-READY-v1.json"
NEUTRAL_ROOT = WORKSPACE / "data/derived/preprint-p05-neutral-tasks-20261101T075541Z"
NEUTRAL_SEAL_SHA256 = "5bf827df9921a01712d9739d7d04f59e8b0aa3554a9ebc9eaf87d6e240aadace"
RAW_ROOT = stage1.RAW_ROOT
OUTPUT_ROOT = WORKSPACE / "data/benchmark/gold_evidence"
OUTPUT_PREFIX = "preprint-p05-references-"
CUTOFF = source_inputs.CUTOFF
METHOD = "p05.independent_original_source_references.v1"
RECIPE_POLICY = "descriptive_archive_inventory_only; archive files are authenticated by the output seal, not standalone source replay"
SCIENTIFIC_VALIDATION = "not_established; technical source units only"
LIMITS = {"fresh_compressed_input_bytes": 4 * 1024**3, "original_files": 137,
          "output_bytes": 512 * 1024**2, "seconds": 2400,
          "records_per_task": 64, "fields_per_task": 512, "joins_per_task": 32}
DENIED_INPUTS = ["generation_packets_and_source_rows", "stage1_captures_mapping_coverage_SQLite_values",
    "old_candidate_answers", "private_gold", "human_returns_and_descendants", "clinical_outcomes", "P02_joins"]


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def code_paths():
    return sorted(stage1.framework_paths() + [Path(stage1.__file__).resolve(),
        Path(source_inputs.__file__).resolve(), Path(__file__).resolve()])


def code_pins():
    return {p.relative_to(WORKSPACE).as_posix(): digest(p.read_bytes()) for p in code_paths()}


def metadata_paths():
    return [p for p, _ in stage1.PINS.values()] + [NEUTRAL_ROOT / "SEAL.json"] + [
        NEUTRAL_ROOT / f"p05-{i:02d}.task.json" for i in range(1, 13)] + [
        NEUTRAL_ROOT / "source-snapshot.json", NEUTRAL_ROOT / "selected-case-plan.json"]


def neutral_documents(deadline):
    """Read only fixed neutral routing metadata, never its origin packet paths."""
    docs = stage1.pinned_documents(deadline)
    metadata_bytes = {}
    for name, (path, expected_hash) in stage1.PINS.items():
        data = read_file(path, deadline, 64 * 1024**2)
        need(digest(data) == expected_hash, "Pinned neutral metadata bytes changed")
        metadata_bytes[name] = data
    inventory = stage1.inventory_from_metadata(docs["frame"], docs["acquisition"])
    need(len(inventory) == LIMITS["original_files"], "Pinned original frame must contain 137 files")
    payload = read_file(NEUTRAL_ROOT / "SEAL.json", deadline, 1024**2)
    need(digest(payload) == NEUTRAL_SEAL_SHA256, "Independent neutral task seal changed")
    seal = parse_json(payload)
    need(seal.get("status") == "SEALED_NEUTRAL_TASK_DEFINITIONS_ONLY" and
         seal.get("artifact_role") == "neutral_routing_configuration_not_raw_graph_evidence" and
         seal.get("source_row_values_copied") is False and seal.get("measurement_expected_values") is False,
         "Neutral seal does not establish query-only configuration")
    expected = {f"p05-{i:02d}.task.json" for i in range(1, 13)} | {"source-snapshot.json", "selected-case-plan.json"}
    items = seal.get("items", [])
    need(len(items) == len(expected) and {i.get("path") for i in items} == expected, "Neutral file inventory changed")
    retained = {}
    for item in items:
        path = checked_path(NEUTRAL_ROOT, item["path"])
        data = read_file(path, deadline, 1024**2)
        need(len(data) == item["bytes"] and digest(data) == item["sha256"], "Neutral query bytes changed")
        retained[item["path"]] = data
    routing = parse_json(retained["selected-case-plan.json"])
    cases = source_inputs.route_contract(routing, stage1_plan_sha256=routing["plan_sha256"])
    need(len(cases) == 12 and [c["case_id"] for c in cases] == [f"p05-{i:02d}" for i in range(1, 13)],
         "All twelve fixed technical source units must be retained")
    tasks = {c["case_id"]: encode(validate_task(parse_json(retained[c["case_id"] + ".task.json"]))) for c in cases}
    for case in cases:
        task = tasks[case["case_id"]]
        need(task["cutoff"] == CUTOFF and task["scope"]["target_id"] == case["targetId"] and
             task["scope"]["indication_id"] == case["diseaseId"], "Neutral task routing/cutoff changed")
    auth = {"neutral_seal_sha256": NEUTRAL_SEAL_SHA256, "frame_descriptor_sha256": fingerprint(inventory),
            "metadata_sha256": {name: expected for name, (_, expected) in stage1.PINS.items()},
            "neutral_files_sha256": {name: digest(data) for name, data in retained.items()}}
    return SimpleNamespace(docs=docs, inventory=inventory, cases=cases, tasks=tasks,
        snapshot_document=parse_json(retained["source-snapshot.json"]), retained=retained, authentication=auth,
        metadata_bytes=metadata_bytes, neutral_seal_bytes=payload)


def make_plan():
    bundle = neutral_documents(time.monotonic() + 60)
    return {"schema_version": 1, "status": "DRAFT", "actual_build_authorized": False,
        "scope": "p05_independent_source_references", "method": METHOD, "row_guard_cutoff_utc": CUTOFF,
        "code_sha256": code_pins(), "environment": stage1.environment(), "limits": LIMITS,
        "authentication": bundle.authentication, "actual_selected_units": len(bundle.cases),
        "raw_root": str(RAW_ROOT), "output_root": str(OUTPUT_ROOT),
        "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
        "expected_values": "fresh ORIGINALS plus unchanged neutral Task/Snapshot only",
        "independence": "independent author and separate original rereads/provenance isolation; selection/mapping/task helpers and base compiler are shared, not algorithmically independent",
        "reference_policy": "unchanged compile_reference and verify_reference; wrapper replays normalization, full inventory and precision date guards",
        "join_policy": "all eligible physical credible rows; exact locus-only one_to_many; native study/variant identities remain separate",
        "blocked_policy": "retain every selected case with explicit date/API/limit/finite-QC disposition; no truncation/replacement",
        "unknown_context": source_inputs.UNKNOWN_CONTEXT, "denied_inputs": DENIED_INPUTS,
        "neutral_metadata": "query/config outside InputGraph, never role-laundered as raw evidence",
        "resources": "2400s cooperative deadline; process RSS/process peak and logical bytes measured; physical I/O unknown",
        "replay_version_policy": "This implementation verifies its exact code/environment only; older runs require their matching reviewed implementation. No universal replay or scientific validation claim.",
        "model_calls": 0, "provider_cost_usd": 0, "network_calls": 0,
        "scientific_claim": "12 T6 technical source units; clinical validation and independent studies not established"}


def validate_freeze(plan, plan_bytes, ready, ready_bytes, expected_ready_sha256, *, approved_raw_root=None):
    need(type(expected_ready_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_ready_sha256) and
         digest(ready_bytes) == expected_ready_sha256, "Independent root READY exact byte hash required")
    need(plan.get("status") == "DRAFT" and plan.get("actual_build_authorized") is False and
         ready.get("schema_version") == 1 and ready.get("status") == "READY" and ready.get("frozen_by") == "root" and
         ready.get("scope") == "p05_independent_source_references" and ready.get("actual_build_authorized") is True,
         "Independent root reference READY authorization required")
    need(ready.get("plan_sha256") == digest(plan_bytes), "READY does not bind exact reference DRAFT bytes")
    need(ready.get("code_sha256") == plan.get("code_sha256") == code_pins(), "Frozen active code changed")
    need(ready.get("environment") == plan.get("environment") == stage1.environment(), "Frozen environment changed")
    need(ready.get("authentication") == plan.get("authentication") and plan.get("limits") == LIMITS and
         ready.get("row_guard_cutoff_utc") == plan.get("row_guard_cutoff_utc") == CUTOFF,
         "Frozen original/neutral lineage, limits or cutoff changed")
    need(plan.get("raw_root") == str(RAW_ROOT if approved_raw_root is None else approved_raw_root) and
         plan.get("output_root") == str(OUTPUT_ROOT), "Trusted runtime roots changed")


def retained_context(plan_bytes, ready_bytes, bundle):
    return {"draft_json": plan_bytes.decode("utf-8"), "ready_json": ready_bytes.decode("utf-8"),
        "neutral_seal_json": bundle.neutral_seal_bytes.decode("utf-8"),
        "neutral_files_json": {name:data.decode("utf-8") for name,data in bundle.retained.items()},
        "metadata_files_json": {name:data.decode("utf-8") for name,data in bundle.metadata_bytes.items()},
        "version_policy": "exact matching reviewed code/environment only; scientific validation not established"}


def validate_context(manifest, expected_manifest_sha256, bundle, *, approved_raw_root, expected_ready_sha256):
    """Validate immutable retained context BEFORE any original value is read.

    No live READY/catalog path is consulted. Supplied runtime configuration must
    exactly match the archived bytes bound by the independent root READY hash.
    Older runs need a matching reviewed implementation; archived code is never
    dynamically executed by this verifier.
    """
    need(type(expected_manifest_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256) and
         fingerprint(manifest) == expected_manifest_sha256, "Independent wrapper manifest hash differs")
    context = manifest.get("authorization", {})
    need(type(context.get("draft_json")) is str and type(context.get("ready_json")) is str,
         "Retained exact DRAFT/READY byte context required for standalone wrapper verification")
    plan_bytes, ready_bytes = context["draft_json"].encode("utf-8"), context["ready_json"].encode("utf-8")
    need(len(plan_bytes) <= 1024**2 and len(ready_bytes) <= 1024**2, "Retained authorization exceeds bounds")
    plan, ready = parse_json(plan_bytes), parse_json(ready_bytes)
    validate_freeze(plan, plan_bytes, ready, ready_bytes, expected_ready_sha256, approved_raw_root=approved_raw_root)
    need(manifest.get("ready_sha256") == expected_ready_sha256, "Declared independent READY hash differs")
    auth = plan["authentication"]
    need(auth == manifest.get("authentication") == bundle.authentication and
         fingerprint(bundle.inventory) == auth.get("frame_descriptor_sha256"), "Retained context/source frame differs")
    case_ids = {case["case_id"] for case in bundle.cases}
    need(type(manifest.get("cases")) is dict and set(manifest["cases"]) == case_ids and
         type(manifest.get("actual_selected_units")) is int and
         manifest["actual_selected_units"] == len(case_ids) == plan.get("actual_selected_units"),
         "Declared selected-unit count/full case set differs")
    need(manifest.get("unknown_context") == source_inputs.UNKNOWN_CONTEXT and
         manifest.get("scientific_validation") == SCIENTIFIC_VALIDATION, "Declared scientific scope/unknown context differs")
    computed_at = source_inputs.utc(manifest.get("computed_at"))
    need(source_inputs.utc(CUTOFF) <= computed_at <= datetime.now(timezone.utc),
         "Declared build time must lie between information cutoff and replay time")
    need(manifest.get("recipe_policy") == RECIPE_POLICY and type(manifest.get("recipe")) is list,
         "Archive inventory policy differs; standalone replay does not authenticate archive files")
    for entry in manifest["recipe"]:
        need(type(entry) is dict and set(entry) == {"logical_path","archive_path","sha256","bytes"}, "Invalid descriptive archive entry")
        _relative(entry["logical_path"])
        _relative(entry["archive_path"])
        need(type(entry["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}",entry["sha256"]) and
             type(entry["bytes"]) is int and entry["bytes"] >= 0,"Invalid descriptive archive identity")
    declared_inputs = [{"source_id":f"original-{i:03d}",**{k:item[k] for k in ("relative_path","sha256","receipt")}}
                       for i,item in enumerate(bundle.inventory)]
    need(manifest.get("original_inputs") == declared_inputs, "Declared original provenance differs from frozen frame")
    need(type(context.get("neutral_seal_json")) is str, "Archived neutral seal required")
    seal_bytes = context["neutral_seal_json"].encode("utf-8")
    need(len(seal_bytes) <= 1024**2 and digest(seal_bytes) == auth.get("neutral_seal_sha256"), "Archived neutral seal hash differs")
    seal = parse_json(seal_bytes)
    need(seal.get("status") == "SEALED_NEUTRAL_TASK_DEFINITIONS_ONLY" and seal.get("source_row_values_copied") is False and
         seal.get("measurement_expected_values") is False, "Archived seal is not neutral query configuration")
    seal_items = seal.get("items",[])
    need(len(seal_items) == len(auth.get("neutral_files_sha256",{})) and
         {item.get("path"):item.get("sha256") for item in seal_items} == auth.get("neutral_files_sha256"),
         "Archived seal does not bind the exact query file inventory")
    archived = {}
    for context_key, hash_key in (("neutral_files_json","neutral_files_sha256"),("metadata_files_json","metadata_sha256")):
        documents = context.get(context_key)
        pins = auth.get(hash_key)
        need(type(documents) is dict and type(pins) is dict and set(documents) == set(pins), "Archived context inventory differs")
        archived[context_key] = {}
        for name, value in documents.items():
            need(type(value) is str, "Archived context requires exact UTF-8 document bytes")
            data = value.encode("utf-8")
            need(len(data) <= 64 * 1024**2 and digest(data) == pins[name], "Archived context document hash differs")
            archived[context_key][name] = parse_json(data)
    query = archived["neutral_files_json"]
    need(set(query) == {c["case_id"] + ".task.json" for c in bundle.cases} | {"source-snapshot.json","selected-case-plan.json"},
         "Archived task/snapshot/routing file inventory differs")
    for case in bundle.cases:
        need(encode(validate_task(query[case["case_id"] + ".task.json"])) == bundle.tasks[case["case_id"]], "Archived exact task differs")
    need(query["source-snapshot.json"] == bundle.snapshot_document, "Archived exact snapshot differs")
    routing = query["selected-case-plan.json"]
    need(source_inputs.route_contract(routing,stage1_plan_sha256=routing["plan_sha256"]) == bundle.cases,
         "Archived neutral selected-case plan differs")
    need(archived["metadata_files_json"] == bundle.docs and "catalog" in bundle.docs, "Archived catalog/frame configuration differs")
    need(manifest.get("method") == METHOD and manifest.get("information_cutoff") == CUTOFF and
         manifest.get("role") == "evaluation_only" and manifest.get("agent_visible") is False and
         manifest.get("adjudicated_gold") is False, "Wrapper lineage/role/cutoff differs")
    return plan, ready


class Bounds(source_inputs.Bounds):
    def __init__(self, output, *, deadline=None):
        super().__init__(output, deadline=deadline if deadline is not None else time.monotonic() + LIMITS["seconds"])
        self.logical_original_bytes_admitted = 0
        self.logical_base_completed_hash_bytes = 0
        self.base_failed_calls_with_unmeasured_partial_hash_bytes = 0

    def check(self):
        deadline_check(self.deadline)
        try:
            import psutil
            info = psutil.Process().memory_info()
            self.peak_sampled_rss_bytes = max(self.peak_sampled_rss_bytes or 0, info.rss)
            self.process_peak_working_set_bytes = getattr(info, "peak_wset", None)
        except (ImportError, OSError):
            pass
        size = sum(p.stat().st_size for p in self.output.rglob("*") if p.is_file()) if self.output.exists() else 0
        need(size <= LIMITS["output_bytes"], "Reference output exceeds 512 MiB bound")
        return size

    def publish_bytes(self, relative, payload, **_):
        need(self.check() + len(payload) <= LIMITS["output_bytes"], "Reference output exceeds 512 MiB bound")
        _relative(relative)
        target = self.output.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent != self.output:
            checked_path(self.output, target.parent.relative_to(self.output).as_posix())
        publish_bytes(target, payload)
        checked_path(self.output, relative)

    def report(self, *, terminal=False):
        size = (sum(p.stat().st_size for p in self.output.rglob("*") if p.is_file()) if terminal else self.check())
        return {"bounds": LIMITS, "wall_seconds": time.monotonic() - self.started,
            "peak_sampled_process_rss_bytes": self.peak_sampled_rss_bytes,
            "process_peak_working_set_bytes": getattr(self, "process_peak_working_set_bytes", None),
            "logical_bytes_hashed_by_wrapper": self.logical_hashed_bytes,
            "logical_original_compressed_bytes_scanned": self.logical_original_compressed_bytes_scanned,
            "scan_accounting": "completed HGNC/target/disease and GWAS/credible projection passes; failed partial passes unmeasured",
            "fresh_original_compressed_bytes": self.logical_original_bytes_admitted,
            "logical_base_completed_hash_bytes": self.logical_base_completed_hash_bytes,
            "base_hash_accounting": "two completed hash passes per retained source_proof: InputGraph.verify and stable source/receipt hash",
            "base_failed_calls_with_unmeasured_partial_hash_bytes": self.base_failed_calls_with_unmeasured_partial_hash_bytes,
            "physical_io_bytes": None, "physical_io_status": "not_measured",
            "output_bytes_before_report_and_seal": size, "enforcement": "cooperative; no hard OS watchdog",
            "model_calls": 0, "provider_cost_usd": 0}


def verify_originals(inventory, bounds, catalog, *, raw_root, archive_receipts):
    """All payload/receipt hashes and graph roles precede original value reads."""
    need(0 < len(inventory) <= LIMITS["original_files"] and
         sum(i["bytes"] for i in inventory) <= LIMITS["fresh_compressed_input_bytes"], "Fresh source frame exceeds bounds")
    index = catalog_index(catalog)
    for item in inventory:
        check_role(item["dataset_id"], stage1.original_role(item), index)
    proofs = []
    for number, item in enumerate(inventory):
        need(item.get("role", stage1.original_role(item)) == stage1.original_role(item) and
             not item.get("parents") and item.get("computed_at") is None, "Only admitted original source/reference roots permitted")
        path = checked_path(raw_root, item["relative_path"])
        need(path == Path(item["path"]), "Original logical/physical path mismatch")
        actual = dict(hash_file(path, bounds.deadline))
        need(actual == {"sha256": item["sha256"], "bytes": item["bytes"]}, "Original hash/size mismatch")
        bounds.logical_hashed_bytes += actual["bytes"]
        proofs.append({**item, "source_id": f"original-{number:03d}", "verified_payload": actual})
        bounds.check()
    bounds.logical_original_bytes_admitted = sum(i["bytes"] for i in inventory)
    for item in proofs:
        receipt = item["receipt"]
        relative = Path(receipt["path"]).relative_to(raw_root).as_posix()
        payload = read_file(checked_path(raw_root, relative), bounds.deadline, 1024**2)
        need(len(payload) == receipt["bytes"] and digest(payload) == receipt["sha256"], "Receipt hash/size mismatch")
        bounds.logical_hashed_bytes += len(payload)
        document = parse_json(payload)
        stage1.check_receipt_identity(document, item, source_id=item["source_id"])
        observed = source_inputs.utc(document["completed_at_utc"])
        need(observed <= source_inputs.utc(CUTOFF), "Original receipt is newer than information cutoff")
        item.update(completed_at_utc=observed.isoformat(), receipt_relative_path=relative)
        if archive_receipts:
            bounds.publish_bytes("_private/receipts/" + receipt["sha256"] + ".json", payload)
    return proofs


def replay_sources(bundle, bounds, *, raw_root, archive_receipts=False, expected_original_inputs=None):
    """Caller holds real stable locks over every original and receipt."""
    proofs = verify_originals(bundle.inventory, bounds, bundle.docs["catalog"], raw_root=raw_root,
                              archive_receipts=archive_receipts)
    if expected_original_inputs is not None:
        need(expected_original_inputs == [{k:p[k] for k in ("source_id","relative_path","sha256","receipt")} for p in proofs],
             "Declared original provenance differs from fresh admitted proofs before row parsing")
    snapshot = source_inputs.original_snapshot(proofs, bundle.docs["catalog"], bounds.output, raw_root=raw_root)
    need(encode(snapshot) == bundle.snapshot_document, "Unchanged neutral Source Snapshot differs from independent original admission")
    small, schemas = stage1.load_small(proofs, bounds)
    bounds.logical_original_compressed_bytes_scanned += sum(p["bytes"] for p in proofs if p["family"] in ("target","disease","hgnc"))
    indexes = stage1.mapping_index(small)
    selected, excluded = source_inputs.select_eligible(bundle.cases, proofs, indexes, bounds)
    replay = {}
    for case in bundle.cases:
        key = case["case_id"]
        groups = selected[key]
        inventory = {family: [{k: r[k] for k in ("source_id", "locator")} for r in rows] for family, rows in groups.items()}
        detail = {"case_id": key, "eligible_inventory": inventory, "excluded_inventory": excluded[key],
            "neutral_task_sha256": fingerprint(bundle.tasks[key]), "row_guard_cutoff_utc": CUTOFF,
            "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False}
        try:
            mapping = source_inputs.normalization_proof(case, groups["gwas_credible_sets"], indexes)
            detail["normalization_sha256"] = fingerprint(mapping)
            derived_task = source_inputs.build_task(case, groups)
            need(canonical(derived_task) == canonical(bundle.tasks[key]), "Independent eligible task/inventory differs from unchanged neutral task")
            for rows in groups.values():
                for record in rows:
                    source_inputs.native_representability(record, case)
            detail.update(status="ready_for_base_compile", blocked_reason=None)
        except ContractError as error:
            detail.update(status="blocked", blocked_reason=str(error))
        detail["replay_sha256"] = fingerprint(detail)
        replay[key] = detail
    return snapshot, replay, proofs


def account_base_hashes(bounds, reference):
    if bounds is not None:
        bounds.logical_base_completed_hash_bytes += 2 * sum(p["bytes"] + p.get("receipt_bytes",0)
                                                          for p in reference.document["source_proofs"])


def compile_p05_references(bundle, snapshot, replay, root, catalog, *, deadline, approved_raw_root, accounting=None):
    results = {}
    for case in bundle.cases:
        key = case["case_id"]
        detail = dict(replay[key])
        reference = None
        if detail["status"] == "ready_for_base_compile":
            try:
                reference = compile_reference(bundle.tasks[key], snapshot, root, catalog, deadline=deadline,
                                              approved_raw_root=approved_raw_root)
                account_base_hashes(accounting,reference)
                detail.update(status="compiled", reference_sha256=reference.fingerprint)
            except ContractError as error:
                if accounting is not None:
                    accounting.base_failed_calls_with_unmeasured_partial_hash_bytes += 1
                detail.update(status="blocked", blocked_reason=str(error))
            except BaseException:
                if accounting is not None:
                    accounting.base_failed_calls_with_unmeasured_partial_hash_bytes += 1
                raise
        results[key] = {"disposition": detail, "reference": reference}
    return results


def verify_p05_references(manifest, expected_manifest_sha256, bundle, bounds, *, approved_raw_root, expected_ready_sha256):
    """Replay all NEW guards and task inventories before unchanged base verify.

    The caller supplies an independently retained wrapper hash. No generation
    output or answer file is opened. The manifest embeds evaluator references.
    """
    with stable_files(code_paths(),deadline=bounds.deadline):
        validate_context(manifest,expected_manifest_sha256,bundle,approved_raw_root=approved_raw_root,
                         expected_ready_sha256=expected_ready_sha256)
        return _verify_original_references(manifest,bundle,bounds,approved_raw_root=approved_raw_root)


def _verify_original_references(manifest,bundle,bounds,*,approved_raw_root):
    paths = [Path(i["path"]) for i in bundle.inventory] + [Path(i["receipt"]["path"]) for i in bundle.inventory]
    with stable_files(paths, deadline=bounds.deadline):
        snapshot, replay, proofs = replay_sources(bundle, bounds, raw_root=approved_raw_root,
                                                  expected_original_inputs=manifest["original_inputs"])
        rebuilt = compile_p05_references(bundle, snapshot, replay, bounds.output, bundle.docs["catalog"],
                                        deadline=bounds.deadline, approved_raw_root=approved_raw_root,accounting=bounds)
        need(set(manifest["cases"]) == set(rebuilt), "All fixed selected cases must remain present")
        verified = {}
        for key, value in rebuilt.items():
            saved = manifest["cases"][key]
            need(saved["disposition"] == value["disposition"], "Original guard/inventory/normalization replay differs")
            if value["reference"] is None:
                need(saved["reference"] is None, "Blocked case must not have a reference")
                continue
            try:
                verified[key] = verify_reference(saved["reference"], saved["disposition"]["reference_sha256"],
                    bundle.tasks[key], snapshot, bounds.output, bundle.docs["catalog"], deadline=bounds.deadline,
                    approved_raw_root=approved_raw_root)
            except BaseException:
                bounds.base_failed_calls_with_unmeasured_partial_hash_bytes += 1
                raise
            account_base_hashes(bounds,verified[key])
        return verified


def validate_output_location(output):
    output = Path(output)
    need(output.is_absolute() and output.parent == OUTPUT_ROOT and
         re.fullmatch(OUTPUT_PREFIX + r"\d{8}T\d{6}Z", output.name), "Exclusive approved gold_evidence output path required")
    need(checked_path(WORKSPACE, output.parent.relative_to(WORKSPACE).as_posix()) == output.parent and
         output.parent.is_dir(), "Unsafe production output parent")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", str(output)], cwd=WORKSPACE, capture_output=True, check=False)
    need(ignored.returncode == 0, "Reference output must already be git-ignored")
    try:
        output.lstat()
    except FileNotFoundError:
        return output
    raise ContractError("Output leaf already exists; inspect only, no resume/overwrite")


def failure_seal(output, stage, error, *, resources=None):
    deadline = time.monotonic() + 30
    items = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name in ("seal.json", "failure-seal.json", "journal.jsonl"):
            continue
        item = {"path": path.relative_to(output).as_posix()}
        try:
            item.update(dict(hash_file(path, deadline)), hash_status="verified")
        except BaseException as failure:
            item.update(sha256=None, bytes=None, hash_status="unavailable:" + type(failure).__name__)
        items.append(item)
    publish_bytes(output / "failure-seal.json", canonical({"schema_version": 1, "status": "failed_partial_not_usable",
        "stage": stage, "error_class": type(error).__name__, "retained_artifacts": items,
        "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
        "resources": resources, "model_calls": 0, "provider_cost_usd": 0}) + b"\n")


def execute(output, *, expected_ready_sha256):
    output = validate_output_location(output)
    journal, bounds, stack = RunJournal(output, kind="build"), Bounds(output), ExitStack()
    stage = "root_authorization"
    try:
        need(checked_path(WORKSPACE,output.relative_to(WORKSPACE).as_posix()) == output and output.is_dir(),
             "Unsafe exclusively reserved reference output path")
        journal.append("build_stage", stage=stage)
        stack.enter_context(stable_files(metadata_paths() + [PLAN_PATH, READY_PATH] + code_paths(), deadline=bounds.deadline))
        plan_bytes, ready_bytes = read_file(PLAN_PATH, bounds.deadline, 1024**2), read_file(READY_PATH, bounds.deadline, 1024**2)
        plan, ready = parse_json(plan_bytes), parse_json(ready_bytes)
        validate_freeze(plan, plan_bytes, ready, ready_bytes, expected_ready_sha256)
        need(plan == make_plan(), "DRAFT differs from exact current neutral protocol")
        bundle = neutral_documents(bounds.deadline)
        need(bundle.authentication == plan["authentication"], "Neutral authentication changed")
        recipe = []
        for number, path in enumerate(metadata_paths() + [PLAN_PATH, READY_PATH] + code_paths()):
            payload = read_file(path, bounds.deadline, 64 * 1024**2)
            logical = path.relative_to(WORKSPACE).as_posix()
            if logical in plan["code_sha256"]:
                need(digest(payload) == plan["code_sha256"][logical], "Code archive differs from frozen code")
            relative = f"_private/recipe/{number:03d}-" + path.name
            bounds.publish_bytes(relative, payload)
            recipe.append({"logical_path": logical, "archive_path": relative, "sha256": digest(payload), "bytes": len(payload)})
        stage = "independent_original_replay_and_compile"
        journal.append("build_stage", stage=stage)
        paths = [Path(i["path"]) for i in bundle.inventory] + [Path(i["receipt"]["path"]) for i in bundle.inventory]
        stack.enter_context(stable_files(paths, deadline=bounds.deadline))
        snapshot, replay, proofs = replay_sources(bundle, bounds, raw_root=RAW_ROOT, archive_receipts=True)
        results = compile_p05_references(bundle, snapshot, replay, output, bundle.docs["catalog"], deadline=bounds.deadline,
                                        approved_raw_root=RAW_ROOT,accounting=bounds)
        manifest = {"schema_version": 1, "method": METHOD, "role": "evaluation_only", "agent_visible": False,
            "adjudicated_gold": False, "computed_at": datetime.now(timezone.utc).isoformat(), "information_cutoff": CUTOFF,
            "authentication": bundle.authentication, "ready_sha256": expected_ready_sha256, "recipe": recipe,
            "recipe_policy":RECIPE_POLICY,
            "authorization": retained_context(plan_bytes,ready_bytes,bundle),
            "original_inputs": [{k: p[k] for k in ("source_id", "relative_path", "sha256", "receipt")} for p in proofs],
            "unknown_context": source_inputs.UNKNOWN_CONTEXT, "actual_selected_units": len(bundle.cases),
            "scientific_validation": SCIENTIFIC_VALIDATION,
            "cases": {key: {"disposition": value["disposition"], "reference": encode(value["reference"].document) if value["reference"] else None}
                      for key, value in results.items()}}
        wrapper_sha256 = fingerprint(manifest)
        bounds.publish("references.json", manifest)
        stage = "independent_wrapper_and_base_verify"
        journal.append("build_stage", stage=stage)
        verified = verify_p05_references(manifest, wrapper_sha256, bundle, bounds, approved_raw_root=RAW_ROOT,
                                        expected_ready_sha256=expected_ready_sha256)
        # Close locks before success. Cleanup errors therefore become terminal failures.
        stack.close()
        bounds.publish("build-report.json", {"status": "verified", "role": "evaluation_only", "agent_visible": False,
            "adjudicated_gold": False, "manifest_sha256": wrapper_sha256, "verified_cases": sorted(verified),
            "blocked_cases": sorted(set(results) - set(verified)), "resources": bounds.report()})
        artifacts = []
        for path in sorted(output.rglob("*")):
            if path.is_file() and path.name != "journal.jsonl":
                artifacts.append({"path": path.relative_to(output).as_posix(), **dict(hash_file(path, bounds.deadline))})
        seal = {"schema_version": 1, "status": "sealed_verified_source_references",
            "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
            "manifest_sha256": wrapper_sha256, "artifacts": artifacts, "model_calls": 0, "provider_cost_usd": 0,
            "journal_prefix_sha256":journal.events[-1]["sha256"],
            "validity_requires":"terminal build_completed binding this seal; no failure-seal.json"}
        stage = "terminal_cleanup"
        bounds.check()
        journal.append("build_completed", manifest_sha256=wrapper_sha256,seal_sha256=fingerprint(seal),
                       verified_cases=len(verified), selected_units=len(results))
        journal.close()
        bounds.publish("seal.json",seal)
        return manifest
    except BaseException as error:
        try:
            stack.close()
        except BaseException as cleanup:
            error.add_note("Lock cleanup failed: " + type(cleanup).__name__)
        try:
            journal.fail(error, stage)
        except BaseException as cleanup:
            error.add_note("Failure journal append failed: " + type(cleanup).__name__)
        try:
            journal.close()
        except BaseException as cleanup:
            error.add_note("Failure journal close failed: " + type(cleanup).__name__)
        try:
            failure_seal(output,stage,error,resources=bounds.report(terminal=True))
        except BaseException as cleanup:
            error.add_note("Terminal failure-seal publication failed: " + type(cleanup).__name__)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--draft", action="store_true")
    commands.add_argument("--build", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ready-sha256")
    args = parser.parse_args(argv)
    if args.draft:
        need(args.output is None and args.ready_sha256 is None, "DRAFT accepts no build parameters")
        publish_bytes(PLAN_PATH, canonical(make_plan()) + b"\n")
        print(str(PLAN_PATH))
        return 0
    need(args.output is not None and args.ready_sha256 is not None, "--build requires --output and independent --ready-sha256")
    execute(args.output, expected_ready_sha256=args.ready_sha256)
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
