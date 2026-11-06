"""Fresh-process, matched three-arm archive execution; no automatic recovery calls.

Product supervision is imported only by the trusted parent. Independent workers
do not import asof/tether. Native Inspect scoring follows each sealed case; the
parent's all-scheduled comparison follows the sealed worker or retained prefix.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.abc
import ipaddress
import math
import os
from pathlib import Path
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if not __package__:
    __package__ = "experiments.inspect_policy"
from experiments.inspect_policy.records import (CaseRecord, canonical, checked_json, digest, freeze,
    inspect_record, parse, proof, publish, read_bytes, safe_path, thaw)

ARMS = ("bare_independent", "bare_tether", "inspect")
DEFAULT_LIMITS = dict(stage_seconds=14400, batch_seconds=1200, case_seconds=120,
    process_output_bytes=8*1024**2, worker_output_bytes=256*1024**2, stage_output_bytes=2*1024**3)
FROZEN_SHA = "3ec7625fa601a517d8e2dd302228f9f465f35e877f79cd1a587a3a63b394a4fc"
ORACLE_SHA = "99706490490bc485614ba2690ff39e91cc0862366c1af811592c338f3aafa5b7"


def need(value, message):
    if not value:
        raise ValueError(message)


def file_reference(path):
    return {"path": str(safe_path(path)), **proof(path)}


def verify_pins(pins):
    started = time.perf_counter()
    for name, expected in pins.items():
        need(proof(name) == expected, "Frozen input changed: "+name)
    return {"files": len(pins), "logical_bytes": sum(p["bytes"] for p in pins.values()),
            "wall_seconds": time.perf_counter()-started}


def batch_schedule(repetitions=3):
    need(type(repetitions) is int and repetitions == 3, "Exactly three matched repetitions required")
    return [{"repetition": repetition+1, "position": position+1, "arm": arm}
            for repetition in range(repetitions)
            for position, arm in enumerate(ARMS[repetition:]+ARMS[:repetition])]


def validate_limits(limits):
    need(set(limits) == set(DEFAULT_LIMITS), "Limit fields differ")
    for name, value in limits.items():
        need(type(value) in (int, float) and math.isfinite(value) and 0 < value <= DEFAULT_LIMITS[name], "Invalid finite limit: "+name)
        if name.endswith("_bytes"):
            need(type(value) is int, "Byte limits must be integers")
    return dict(limits)


def output_boundary(output, protected):
    output = safe_path(output)
    if output.exists():
        raise FileExistsError(str(output))
    for root in protected:
        root = safe_path(root)
        need(not output.is_relative_to(root) and not root.is_relative_to(output), "Output overlaps protected input root")
    return output


def verify_corpus_inventory(root, frozen):
    root = safe_path(root)
    bundles = root/"bundles"
    actual_files = {p.relative_to(bundles).as_posix() for p in bundles.rglob("*") if p.is_file()}
    actual_dirs = {p.relative_to(bundles).as_posix() for p in bundles.rglob("*") if p.is_dir()}
    need(actual_files == set(frozen["bundles"]) and actual_dirs == set(frozen["bundle_directories"]),
         "Frozen bundle inventory differs")
    return {"files": len(actual_files), "directories": len(actual_dirs)}


def corpus_pins(root, frozen):
    root = safe_path(root)
    bundles = root/"bundles"
    verify_corpus_inventory(root, frozen)
    pins = {str(bundles/name): thaw(pin) for name, pin in frozen["bundles"].items()}
    pins[str(root/"oracle.json")] = thaw(frozen["oracle_pin"])
    if "trusted_runtime_pin" in frozen:
        pins[str(root/"trusted-runtime.json")] = thaw(frozen["trusted_runtime_pin"])
    for path, pin in frozen.get("sources", {}).items():
        pins[str(ROOT/path)] = thaw(pin)
    for path, pin in frozen.get("runtime_proofs", {}).items():
        pins[path] = thaw(pin)
    for family in frozen.get("installed_runtime", {}).values():
        for relative, pin in family["files"].items():
            pins[str(Path(family["root"])/relative)] = thaw(pin)
    if "python" in frozen:
        pins[frozen["python"]["path"]] = {key: frozen["python"][key] for key in ("sha256", "bytes")}
    return pins


def source_pins(additional=()):
    paths = list(Path(__file__).parent.rglob("*.py"))
    paths += list((ROOT/"experiments/equal_policy").glob("*.py"))
    paths += list((ROOT/"experiments/equal_policy_v2").glob("*.py"))
    paths += [Path(p) for p in additional]
    return {str(p.absolute()): proof(p) for p in sorted(set(paths))}


def archive_sources(output, pins):
    """Retain executed source bytes independently of mutable original paths."""
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archived = {}
    for name, pin in pins.items():
        raw = read_bytes(name)
        need(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
             "Source changed during archive: "+name)
        relative = "files/"+pin["sha256"]+"-"+Path(name).name
        target = output/relative
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            need(read_bytes(target) == raw, "Source archive collision")
        else:
            with target.open("xb") as stream:
                stream.write(raw)
        archived[name] = {"path": relative, **thaw(pin)}
    publish(output/"INDEX.json", {"schema_version": 1, "files": archived})
    return archived


def global_source_audit(config):
    audit = verify_pins(config["input_pins"])
    if "corpus" in config:
        corpus_root = safe_path(config["corpus_root"])
        corpus = checked_json(corpus_root/"FROZEN.json", config["corpus"])
        audit["bundle_inventory"] = verify_corpus_inventory(corpus_root, corpus)
    expected = config.get("environment_files")
    if expected is not None:
        root = safe_path(config["environment_root"])
        current = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        need(current == set(expected), "Complete environment file inventory changed")
        audit["environment_inventory_files"] = len(current)
    return audit


def freeze_run(corpus_root, environment_receipt_path, environment_receipt_sha256, output,
               *, additional_source_paths=(), mode="benchmark", limits=None):
    env_path = safe_path(environment_receipt_path)
    env_proof = proof(env_path)
    need(env_proof["sha256"] == environment_receipt_sha256, "Environment receipt anchor differs")
    environment = checked_json(env_path, env_proof)
    output = output_boundary(output, [corpus_root, Path(environment["python"]).parent.parent.parent])
    output.parent.mkdir(parents=True, exist_ok=True)
    record = CaseRecord(output, {"operation": "freeze_archive_comparison", "mode": mode})
    try:
        need(mode in ("benchmark", "fictional"), "Unknown population mode")
        limits = validate_limits(DEFAULT_LIMITS if limits is None else limits)
        corpus_root = safe_path(corpus_root)
        frozen_proof = proof(corpus_root/"FROZEN.json")
        frozen = checked_json(corpus_root/"FROZEN.json", frozen_proof)
        if mode == "benchmark":
            need(frozen_proof["sha256"] == FROZEN_SHA and frozen["oracle_pin"]["sha256"] == ORACLE_SHA
                 and len(frozen["cases"]) == 109, "Wrong original corpus or oracle")
        pins = corpus_pins(corpus_root, frozen)
        pins[str(corpus_root/"FROZEN.json")] = frozen_proof
        batch_pins = dict(pins)
        need(environment["status"] == "pass" and environment["inspect_ai_version"] == "0.3.287", "Unqualified Inspect environment")
        inventory_ref = [p for p in environment["proofs"] if p["path"].endswith("/ENVIRONMENT-INVENTORY.json")]
        need(len(inventory_ref) == 1, "Missing environment payload inventory")
        inventory_ref = inventory_ref[0]
        inventory_path = ROOT/inventory_ref["path"]
        inventory = checked_json(inventory_path, {key: inventory_ref[key] for key in ("sha256", "bytes")})
        env_root = Path(environment["python"]).parent.parent
        for item in inventory["files"]:
            pins[str(env_root/item["path"])] = {key: item[key] for key in ("sha256", "bytes")}
            relative = item["path"].replace("\\", "/")
            if relative.endswith(".py") and relative.startswith(("Lib/site-packages/asof/", "Lib/site-packages/tether/")):
                batch_pins[str(env_root/item["path"])] = pins[str(env_root/item["path"])]
        pins[str(env_path)] = env_proof
        pins[str(inventory_path)] = proof(inventory_path)
        batch_pins[str(env_path)] = pins[str(env_path)]
        batch_pins[str(inventory_path)] = pins[str(inventory_path)]
        for item in environment["proofs"]:
            pins[str(ROOT/item["path"])] = {key: item[key] for key in ("sha256", "bytes")}
            batch_pins[str(ROOT/item["path"])] = pins[str(ROOT/item["path"])]
        code = source_pins(additional_source_paths)
        for path, pin in code.items():
            need(path not in pins or pins[path] == pin, "Original code/source closure changed")
            pins[path] = pin
            batch_pins[path] = pin
        audit = verify_pins(pins)
        archived = archive_sources(output/"source-archive", code)
        for item in archived.values():
            archived_path = str(output/"source-archive"/item["path"])
            pins[archived_path] = {key: item[key] for key in ("sha256", "bytes")}
            batch_pins[archived_path] = pins[archived_path]
        archive_index = str(output/"source-archive/INDEX.json")
        pins[archive_index] = proof(archive_index)
        batch_pins[archive_index] = pins[archive_index]
        rows = []
        for item in frozen["cases"]:
            ident = item["control_id"]
            descriptor = corpus_root/str(item["descriptor"]).replace("\\", "/")
            need(descriptor == corpus_root/"bundles"/ident/"descriptor.json", "Noncanonical descriptor path")
            rows.append({"control_id": ident, "bundle_root": str(descriptor.parent),
                         "descriptor": {"path": "descriptor.json", **proof(descriptor)}})
        from .archive import checked_rows
        checked_rows(rows)
        config = dict(schema_version=1, mode=mode, corpus_root=str(corpus_root), corpus=frozen_proof,
            environment=file_reference(env_path), python=file_reference(environment["python"]),
            oracle=file_reference(corpus_root/"oracle.json"), rows=rows, schedule=batch_schedule(), limits=limits,
            input_pins=pins, batch_input_pins=batch_pins,
            environment_root=str(env_root), environment_files=[p["path"].replace("\\", "/") for p in inventory["files"]],
            source_archive=archived, code_pins={p: pin for p, pin in code.items() if p.endswith(".py")},
            audit_scope="Complete content and environment inventory before and after stage; corpus, original runtime, code, source archive and qualification receipts before and after each batch. Third-party content is bracketed, not continuously attested.",
            source_preflight=audit, expected_cells=len(rows)*9, provider_cost_usd=0,
            process_scope="One owned child per arm/repetition; not process-tree containment")
        freeze_proof = publish(output/"FROZEN.json", config)
        record.finish({"status": "completed", "freeze": freeze_proof, "scheduled_cells": len(rows)*9})
        return freeze(config)
    except BaseException as exc:
        record.finish({"status": "failed", "error": type(exc).__name__+": "+str(exc)})
        raise


def worker_recipe(config, arm, output):
    need(arm in ARMS, "Unknown comparator arm")
    recipe = dict(schema_version=1, mode=config["mode"], arm=arm, rows=thaw(config["rows"]),
        output=str(output), limits=thaw(config["limits"]), code_pins=thaw(config["code_pins"]))
    if arm == "inspect":
        recipe["oracle"] = thaw(config["oracle"])
    return recipe


class ImportBoundary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("asof", "tether"):
            raise ImportError("Independent worker cannot import product validation")
        return None


def network_guard():
    events = []
    socket_source = str(Path(socket.__file__).resolve())
    def audit(event, args):
        if event not in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
            return
        frame, allowed = sys._getframe(1), False
        while frame:
            if frame.f_code.co_name == "_fallback_socketpair" and str(Path(frame.f_code.co_filename).resolve()) == socket_source:
                allowed = event == "socket.connect" and ipaddress.ip_address(args[1][0]).is_loopback
                break
            frame = frame.f_back
        events.append({"event": event, "allowed_stdlib_loopback": allowed})
        if not allowed:
            raise PermissionError("External network disabled for archive comparison")
    sys.addaudithook(audit)
    return events


def tree_bytes(root):
    total = 0
    for directory, _, names in os.walk(root):
        for name in names:
            try:
                total += (Path(directory)/name).stat().st_size
            except FileNotFoundError:
                pass
    return total


@contextmanager
def case_deadline(root, ident, seconds):
    deadline = time.perf_counter()+seconds
    stop = threading.Event()
    def terminate():
        try:
            publish(Path(root)/"WATCHDOG.json", {"control_id": ident, "reason": "per_case_deadline", "seconds": seconds})
        finally:
            os._exit(124)
    def poll():
        while not stop.wait(0.025):
            if time.perf_counter() >= deadline:
                terminate()
    thread = threading.Thread(target=poll, daemon=True)
    thread.start()
    try:
        yield
        if time.perf_counter() >= deadline:
            terminate()
    finally:
        stop.set()
        thread.join(1)


def execute_worker(recipe_path, expected_sha):
    started, cpu = time.perf_counter(), time.process_time()
    recipe_pin = proof(recipe_path)
    need(recipe_pin["sha256"] == expected_sha, "Worker recipe anchor differs")
    recipe = checked_json(recipe_path, recipe_pin)
    validate_limits(recipe["limits"])
    need(sys.flags.isolated == 1 and sys.dont_write_bytecode and sys.pycache_prefix, "Fresh isolated imports required")
    cache = safe_path(sys.pycache_prefix)
    cache.mkdir(parents=True, exist_ok=True)
    need(not any(cache.iterdir()), "Import cache is not empty")
    arm = recipe["arm"]
    need(arm in ARMS and ("oracle" in recipe) == (arm == "inspect"), "Oracle/arm boundary differs")
    record = CaseRecord(recipe["output"], recipe)
    root = record.path
    cases = root/"cases"
    cases.mkdir()
    if arm != "bare_tether":
        sys.meta_path.insert(0, ImportBoundary())
    network = network_guard()
    result = None
    try:
        preflight = verify_pins(recipe["code_pins"])
        from .archive import execute_archive_case, checked_rows
        rows = checked_rows(recipe["rows"])
        validator = None
        if arm == "bare_tether":
            sys.path.insert(0, str(ROOT/"experiments"))
            from equal_policy_v2.reference import validate_bundle
            validator = validate_bundle
        returns = []
        def execute(row, output_root):
            need(tree_bytes(root) <= recipe["limits"]["worker_output_bytes"], "Worker artifact byte cap")
            record.append("case_started", {"control_id": row["control_id"]})
            with case_deadline(root, row["control_id"], recipe["limits"]["case_seconds"]):
                returned = execute_archive_case(row, output_root, validator=validator)
            returns.append({"control_id": row["control_id"], "receipt": thaw(returned["receipt"]),
                            "case_wall_seconds": returned["case_wall_seconds"], "case_cpu_seconds": returned["case_cpu_seconds"]})
            record.append("case_returned", returns[-1])
            if returned["result"]["status"] == "interrupted":
                raise KeyboardInterrupt("Interrupted archive validation; no later dispatch")
            return returned
        execution_start = time.perf_counter()
        native = None
        if arm == "inspect":
            from inspect_ai import eval
            from .task import build_archive_task
            oracle = recipe["oracle"]
            task = build_archive_task(rows, cases, oracle["path"],
                {key: oracle[key] for key in ("sha256", "bytes")}, execute=execute)
            logs = eval(task, model=None, display="none", log_dir=str(root/"native-logs"), log_format="json",
                max_samples=1, max_tasks=1, retry_on_error=0, max_retries=0, fail_on_error=False,
                score_on_error=False, log_shared=False, notification=False, epochs=1,
                cache=False, time_limit=recipe["limits"]["case_seconds"], log_samples=True)
            need(len(logs) == 1, "Native Inspect log count differs")
            log = logs[0]
            native = {"status": log.status, "location": str(log.location), "results": thaw(log.results.model_dump(mode="json")) if log.results else None,
                "samples": [{"id": str(s.id), "error": s.error.model_dump(mode="json") if s.error else None,
                    "scores": {k: v.model_dump(mode="json") for k, v in (s.scores or {}).items()}} for s in (log.samples or [])]}
        else:
            for row in rows:
                execute(row, cases)
        execution_wall = time.perf_counter()-execution_start
        postflight = verify_pins(recipe["code_pins"])
        imported_product = sorted(k for k in sys.modules if k.split(".")[0] in ("asof", "tether"))
        need(arm == "bare_tether" or not imported_product, "Independent worker imported product")
        need(tree_bytes(root) <= recipe["limits"]["worker_output_bytes"], "Worker artifact byte cap")
        import psutil
        memory = psutil.Process().memory_info()
        result = {"status": "completed", "arm": arm, "returns": returns, "native": native,
            "worker_preexecution_wall_seconds": execution_start-started, "arm_execution_interval_seconds": execution_wall,
            "timing_scope": "Full supervised batch is the paired cost; Inspect's lazy framework import is inside arm_execution_interval, bare validator import is in preexecution. Operation-only values are diagnostic, not standalone framework overhead.",
            "worker_cpu_seconds": time.process_time()-cpu, "worker_peak_memory_bytes": getattr(memory, "peak_wset", None),
            "preflight": preflight, "postflight": postflight, "network_events": network,
            "imported_product_modules": imported_product, "provider_cost_usd": 0}
        record.finish(result)
    except BaseException as exc:
        record.finish({"status": "failed", "arm": arm, "error": type(exc).__name__+": "+str(exc),
                       "network_events": network, "worker_cpu_seconds": time.process_time()-cpu})
        raise


def recover_rows(worker, rows):
    worker = Path(worker)
    watchdog = parse(read_bytes(worker/"WATCHDOG.json")) if (worker/"WATCHDOG.json").exists() else None
    result = []
    for row in rows:
        ident = row["control_id"]
        path = worker/"cases"/ident
        item = {"control_id": ident, "status": "unstarted", "decision": None, "receipt": None, "error": None}
        try:
            if (path/"receipt.json").exists():
                pin = proof(path/"receipt.json")
                retained = inspect_record(path, receipt_sha256=pin["sha256"])
                need(canonical(retained["request"]) == canonical(row), "Case request differs from frozen row")
                item.update(status=retained["result"]["status"], decision=thaw(retained["result"]["decision"]),
                            error=thaw(retained["result"]["error"]), receipt=pin)
            elif path.exists():
                item.update(status="unfinished", error="No sealed case receipt")
        except Exception as exc:
            item.update(status="artifact_error", decision=None, error=type(exc).__name__+": "+str(exc))
        if watchdog and watchdog["control_id"] == ident:
            item.update(status="timeout", decision=None, error="Per-case wall bound exceeded")
        result.append(item)
    return result


def score_rows(records, oracle):
    from .archive import compare_result
    expected = {row["control_id"]: row for row in oracle["cases"]}
    need(len(expected) == len(records) and set(expected) == {r["control_id"] for r in records}, "Scoring schedule differs")
    count = Counter(scheduled=len(records), completed=0, full_conformance=0, decision_match=0,
                    correct_rejection=0, false_admission=0, false_rejection=0, unscored=0)
    details = []
    for item in records:
        key = item["control_id"]
        gold = expected[key]
        verdict = item["status"] == "completed" and item["decision"] is not None
        match = compare_result(item["decision"], gold) if verdict else {"has_verdict": False, "decision_match": False, "full_match": False}
        decision = item["decision"]["decision"] if verdict else None
        count.update(completed=item["status"] == "completed", full_conformance=match["full_match"],
            decision_match=match["decision_match"], correct_rejection=decision == gold["decision"] == "reject",
            false_admission=gold["decision"] == "reject" and decision == "accept",
            false_rejection=gold["decision"] == "accept" and decision == "reject", unscored=not match["has_verdict"])
        details.append({"control_id": key, "status": item["status"], "expected_decision": gold["decision"],
                        "actual_decision": decision, **match})
    return {**dict(count), "full_conformance_per_scheduled": count["full_conformance"]/len(records),
            "status_counts": dict(Counter(r["status"] for r in records)), "cases": details}


def clean_environment(root):
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}}
    (root/"tmp").mkdir()
    env.update(TEMP=str(root/"tmp"), TMP=str(root/"tmp"), PYTHON_DOTENV_DISABLED="1",
               INSPECT_CACHE_DIR=str(root/"inspect-cache"), TIKTOKEN_CACHE_DIR=str(root/"token-cache"))
    return env


@contextmanager
def process_environment(environment):
    """The serial trusted controller alone changes its child launch context."""
    old, cwd = dict(os.environ), Path.cwd()
    try:
        os.environ.clear()
        os.environ.update(environment)
        os.chdir(ROOT)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)
        os.chdir(cwd)


def run_stage(freeze_path, expected_freeze_sha256, output):
    output = safe_path(output)
    if output.exists():
        raise FileExistsError(str(output))
    pin = proof(freeze_path)
    need(pin["sha256"] == expected_freeze_sha256, "Run freeze anchor differs")
    config = checked_json(freeze_path, pin)
    validate_limits(config["limits"])
    output_boundary(output, [Path(freeze_path).parent, config["corpus_root"], Path(config["python"]["path"]).parent.parent.parent])
    output.parent.mkdir(parents=True, exist_ok=True)
    record = CaseRecord(output, {"freeze_path": str(freeze_path), "expected_freeze_sha256": expected_freeze_sha256})
    start = time.perf_counter()
    batches = []
    fatal = None
    integrity = {"status": "pending", "global_preflight": None, "global_postflight": None,
                 "scope": config.get("audit_scope", "Legacy complete input checks at each batch")}
    try:
        need(config["schedule"] == freeze(batch_schedule()), "Batch rotation differs")
        publish(output/"freeze.json", config)
        from tether._process import ProcessLimits, supervise_command, validate_success_report
        deadline = time.perf_counter()+config["limits"]["stage_seconds"]
        integrity["global_preflight"] = global_source_audit(config)
        record.append("global_source_preflight", integrity["global_preflight"])
        for ordinal, batch in enumerate(config["schedule"]):
            folder = output/("batch-"+str(ordinal+1).zfill(2)+"-"+batch["arm"])
            folder.mkdir()
            before = verify_pins(config.get("batch_input_pins", config["input_pins"]))
            remaining = deadline-time.perf_counter()
            need(remaining > 0, "Stage budget exhausted before dispatch")
            limits = ProcessLimits(timeout_seconds=min(remaining, config["limits"]["batch_seconds"]),
                                   max_output_bytes=config["limits"]["process_output_bytes"])
            recipe = worker_recipe(config, batch["arm"], folder/"worker")
            recipe_proof = publish(folder/"recipe.json", recipe)
            command = [config["python"]["path"], "-I", "-B", "-X", "pycache_prefix="+str(folder/"empty-import-cache"),
                       str(Path(__file__)), "worker", "--recipe", str(folder/"recipe.json"), "--sha", recipe_proof["sha256"]]
            record.append("worker_dispatch", {"ordinal": ordinal, **thaw(batch), "recipe": recipe_proof,
                                               "command": command, "limits": limits.payload()})
            execution = None
            error = None
            try:
                with process_environment(clean_environment(folder)):
                    execution = supervise_command(command, limits=limits)
            except BaseException as exc:
                execution = getattr(exc, "tether_engine_result", getattr(exc, "result", None))
                error = type(exc).__name__+": "+str(exc)
            if execution is not None:
                (folder/"stdout.bin").write_bytes(execution.stdout)
                (folder/"stderr.bin").write_bytes(execution.stderr)
                report = {"returncode": execution.returncode, "supervision": execution.supervision, "error": error}
                if error is None:
                    try:
                        need(execution.returncode == 0, "Nonzero worker exit")
                        validate_success_report(execution.supervision, limits, len(execution.stdout), len(execution.stderr))
                    except Exception as exc:
                        error = type(exc).__name__+": "+str(exc)
                        report["error"] = error
            else:
                report = {"error": error, "returncode": None, "supervision": None}
            publish(folder/"supervision.json", report)
            record.append("worker_returned", {"ordinal": ordinal, "report": report})
            after = verify_pins(config.get("batch_input_pins", config["input_pins"]))
            rows = recover_rows(folder/"worker", config["rows"])
            if any(row["status"] in ("artifact_error", "unfinished", "unstarted", "timeout") for row in rows):
                error = error or "A scheduled case lacks a valid completed execution record"
            terminal = None
            if (folder/"worker/receipt.json").exists():
                terminal = inspect_record(folder/"worker", receipt_sha256=proof(folder/"worker/receipt.json")["sha256"])
            if not terminal or terminal["result"]["status"] != "completed":
                error = error or "Worker has no completed terminal receipt"
            # The original bytes are already frozen. Oracle opens only now for parent scoring.
            oracle = checked_json(config["oracle"]["path"], {k: config["oracle"][k] for k in ("sha256", "bytes")})
            scored = score_rows(rows, oracle)
            result = {"ordinal": ordinal, **thaw(batch), "status": "completed" if error is None else "failed",
                "error": error, "source_preflight": before, "source_postflight": after, "rows": rows,
                "score": scored, "worker_result": thaw(terminal["result"]) if terminal else None,
                "supervision": report}
            publish(folder/"RESULT.json", result)
            batches.append(result)
            need(tree_bytes(output) <= config["limits"]["stage_output_bytes"], "Stage output byte cap")
            if error:
                fatal = error
                break
    except BaseException as exc:
        fatal = type(exc).__name__+": "+str(exc)
    if config is not None:
        for ordinal in range(len(batches), len(config["schedule"])):
            batch = config["schedule"][ordinal]
            folder = output/("batch-"+str(ordinal+1).zfill(2)+"-"+batch["arm"])
            retained_rows = recover_rows(folder/"worker", config["rows"])
            dispatched = (folder/"supervision.json").exists() or (folder/"worker").exists()
            batches.append({"ordinal": ordinal, **thaw(batch), "status": "failed" if dispatched else "unstarted", "error": fatal,
                            "rows": retained_rows, "score": None,
                            "recovery": "Retained outcomes after controller failure; no call repeated; scoring unavailable"})
    try:
        integrity["global_postflight"] = global_source_audit(config)
        integrity["status"] = "passed" if integrity["global_preflight"] is not None else "failed"
        record.append("global_source_postflight", integrity["global_postflight"])
    except BaseException as exc:
        integrity["status"] = "failed"
        integrity["error"] = type(exc).__name__+": "+str(exc)
        fatal = fatal or integrity["error"]
        record.append("global_source_postflight_failed", {"error": integrity["error"]})
    if time.perf_counter()-start > config["limits"]["stage_seconds"]:
        fatal = fatal or "Stage wall budget exceeded, including final source audit"
    finalization = time.perf_counter()
    result = {"status": "completed" if fatal is None and config is not None and len(batches) == 9 else "partial",
        "failure": fatal, "source_integrity": integrity, "scheduled_cells": config["expected_cells"] if config else None,
        "retained_cells": sum(len(b["rows"]) for b in batches), "batches": batches,
        "wall_seconds_before_finalization": finalization-start, "automatic_retry": False, "provider_cost_usd": 0}
    record.finish(result)
    inventory = {p.relative_to(output).as_posix(): proof(p, maximum=512*1024**2)
                 for p in output.rglob("*") if p.is_file()}
    seal = {"schema_version": 1, "kind": "inspect_policy_comparison", "status": result["status"], "outputs": inventory,
            "finalization_seconds_before_seal_write": time.perf_counter()-finalization,
            "total_wall_seconds_before_seal_write": time.perf_counter()-start,
            "seal_write_included": False, "source_freeze_sha256": expected_freeze_sha256}
    publish(output/"SEALED.json", seal)
    return freeze(result)


def verify_stage(root, expected_seal_sha256):
    root = safe_path(root)
    seal_proof = proof(root/"SEALED.json")
    need(seal_proof["sha256"] == expected_seal_sha256, "External stage seal differs")
    seal = checked_json(root/"SEALED.json", seal_proof)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root/"SEALED.json"}
    need(actual == set(seal["outputs"]), "Stage output inventory differs")
    verify_pins({str(root/name): pin for name, pin in seal["outputs"].items()})
    retained = inspect_record(root, receipt_sha256=proof(root/"receipt.json")["sha256"])
    result = retained["result"]
    need(result["status"] == seal["status"] and result["retained_cells"] == sum(len(b["rows"]) for b in result["batches"]),
         "Stage denominator/status differs")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("--recipe", required=True)
    worker.add_argument("--sha", required=True)
    run = sub.add_parser("run")
    run.add_argument("--freeze", required=True)
    run.add_argument("--sha", required=True)
    run.add_argument("--output", required=True)
    prepare = sub.add_parser("freeze")
    prepare.add_argument("--corpus", required=True)
    prepare.add_argument("--environment-receipt", required=True)
    prepare.add_argument("--environment-sha", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--source", action="append", default=[])
    prepare.add_argument("--fictional", action="store_true")
    args = parser.parse_args()
    if args.command == "worker":
        execute_worker(args.recipe, args.sha)
    elif args.command == "run":
        outer_started = time.perf_counter()
        result = run_stage(args.freeze, args.sha, args.output)
        print(canonical({"status": result["status"], "retained_cells": result["retained_cells"],
                         "outer_wall_seconds_through_stage_seal": time.perf_counter()-outer_started}).decode())
        if result["status"] != "completed":
            raise SystemExit(1)
    else:
        result = freeze_run(args.corpus, args.environment_receipt, args.environment_sha, args.output,
                            additional_source_paths=args.source, mode="fictional" if args.fictional else "benchmark")
        print(canonical({"scheduled_cells": result["expected_cells"],
                         "freeze_sha256": proof(Path(args.output)/"FROZEN.json")["sha256"]}).decode())


if __name__ == "__main__":
    main()
