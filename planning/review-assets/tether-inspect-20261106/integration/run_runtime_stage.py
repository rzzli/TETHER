"""Externally pinned, exactly-once supervisor for three fictional witness groups.

The qualified process guard bounds each owned child and captured stdout/stderr.
It does not contain arbitrary descendants or preempt parent proof/finalization
work. Such work is timed separately and checked between bounded operations.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import (CaseRecord, parse, proof,
    publish, read_bytes, safe_path, inspect_record, thaw)

DEFAULT_LIMITS = {"stage_seconds": 900.0, "ordinary_seconds": 240.0,
                  "process_group_seconds": 180.0, "process_output_bytes": 8 * 1024**2}
PROCESS_HELPER = Path(__file__).with_name("run_process_witness.py")
NATIVE_WORKER = ROOT / "experiments/inspect_policy/witness_worker.py"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    raw = read_bytes(path, max(2 * 1024**2, expected["bytes"]))
    need({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)} == expected,
         "Frozen proof differs: " + str(path))
    return raw


def validate_limits(limits):
    need(set(limits) == set(DEFAULT_LIMITS), "Exact runtime stage limits required")
    for key, value in limits.items():
        need(type(value) in (int, float) and math.isfinite(value) and
             0 < value <= DEFAULT_LIMITS[key], "Invalid bounded limit: " + key)
    need(type(limits["process_output_bytes"]) is int, "Integral output cap required")


def audit(config, preparation):
    started = time.perf_counter()
    pins = dict(config["code_pins"])
    pins[config["python"]["path"]] = {key: config["python"][key] for key in ("sha256", "bytes")}
    prep = config["preparation"]
    pins[prep["path"]] = {key: prep[key] for key in ("sha256", "bytes")}
    base = safe_path(prep["path"]).parent
    for relative, expected in preparation["input_inventory"].items():
        path = safe_path(base / relative)
        need(path.is_relative_to(base), "Prepared input escapes its root")
        pins[str(path)] = expected
    for path, expected in pins.items():
        pinned(path, expected)
    return {"files": len(pins), "logical_bytes": sum(p["bytes"] for p in pins.values()),
            "wall_seconds": time.perf_counter() - started}


def _write_raw(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return proof(path)


@contextmanager
def clean_environment(root):
    previous = os.environ.copy()
    try:
        allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH",
                   "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}
        minimal = {name: value for name, value in previous.items() if name.upper() in allowed}
        temporary = Path(root) / "tmp"
        temporary.mkdir(exist_ok=False)
        minimal.update(TEMP=str(temporary), TMP=str(temporary), PYTHON_DOTENV_DISABLED="1")
        os.environ.clear()
        os.environ.update(minimal)
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def commands(config, preparation, output):
    base = safe_path(config["preparation"]["path"]).parent
    ordinary = parse(read_bytes(preparation["ordinary"]["rows"]["path"]))
    need(len(ordinary) == preparation.get("scheduled_ordinary_rows", len(ordinary)),
         "Prepared ordinary denominator differs")
    processes = parse(read_bytes(preparation["process_rows"]["path"]))
    recipe = preparation["ordinary_recipe"]
    raw_recipe = parse(pinned(recipe["path"], {key: recipe[key] for key in ("sha256", "bytes")}))
    need(raw_recipe["output_root"] == str(base / "ordinary-cases"), "Ordinary output path differs")
    need(raw_recipe["rows"] == ordinary, "Ordinary recipe schedule differs")
    scheduled = [
        {"id": "ordinary16", "case_ids": [row["id"] for row in ordinary],
         "result": base / "ordinary-worker/RESULT.json", "seconds": config["limits"]["ordinary_seconds"],
         "args": [str(NATIVE_WORKER), "--recipe", recipe["path"], "--recipe-sha256", recipe["sha256"],
                  "--work", str(base / "ordinary-worker")]},
        {"id": "IX06", "case_ids": [row["id"] for row in processes["IX06"]],
         "result": base / "IX06-interruption/RESULT.json", "seconds": config["limits"]["process_group_seconds"]},
        {"id": "IX08", "case_ids": [processes["IX08"]["id"]],
         "result": base / "IX08-concurrency/RESULT.json", "seconds": config["limits"]["process_group_seconds"]}]
    for item in scheduled:
        if "args" not in item:
            item["args"] = [str(PROCESS_HELPER), "--preparation", config["preparation"]["path"],
                "--preparation-sha256", config["preparation"]["sha256"], "--which", item["id"]]
        prefix = output / (item["id"] + "-import-cache")
        item["prefix"] = prefix
        item["argv"] = [config["python"]["path"], "-I", "-B", "-X", "pycache_prefix=" + str(prefix)] + item.pop("args")
    return base, scheduled


def recover_case_dispositions(base, schedule):
    result = []
    for item in schedule:
        folder = base / {"ordinary16": "ordinary-cases", "IX06": "IX06-interruption/cases", "IX08": "IX08-concurrency/cases"}[item["id"]]
        for ident in item["case_ids"]:
            row = {"group": item["id"], "id": ident, "status": "unexecuted", "receipt": None}
            if (folder / ident / "request.json").exists():
                try:
                    record = inspect_record(folder / ident, allow_partial=True)
                    row["status"] = record["result"]["status"] if record["status"] == "sealed" else "interrupted_unresolved"
                    if record["status"] == "sealed":
                        row["receipt"] = proof(folder / ident / "receipt.json")
                except BaseException as exc:
                    row.update(status="record_invalid", error=type(exc).__name__ + ": " + str(exc))
            result.append(row)
    return result


def run_stage(freeze_path, freeze_sha256, output, *, execute=None):
    """Only tests replace execute; CLI always uses qualified supervise_command."""
    output = safe_path(output)
    raw = read_bytes(freeze_path, 4 * 1024**2)
    need(hashlib.sha256(raw).hexdigest() == freeze_sha256, "External runtime freeze anchor differs")
    config = parse(raw)
    need(set(config) == {"schema_version", "preparation", "python", "code_pins", "limits"} and
         config["schema_version"] == 1, "Runtime freeze schema differs")
    validate_limits(config["limits"])
    need(safe_path(config["python"]["path"]) == safe_path(sys.executable), "Parent interpreter differs")
    required = [Path(__file__), PROCESS_HELPER, NATIVE_WORKER,
                ROOT / "experiments/inspect_policy/records.py"]
    need(all(str(safe_path(path)) in config["code_pins"] for path in required), "Required orchestration sources are unpinned")
    prep_ref = config["preparation"]
    preparation = parse(pinned(prep_ref["path"], {key: prep_ref[key] for key in ("sha256", "bytes")}))
    base, schedule = commands(config, preparation, output)
    # Reject unsafe placement before writing any output, including a copied freeze.
    protected = [base / "inputs", base / "process-inputs", safe_path(freeze_path)]
    protected += [safe_path(path) for path in config["code_pins"]]
    for path in protected:
        need(not output.is_relative_to(path) and not path.is_relative_to(output), "Stage output overlaps frozen inputs")
    stage = CaseRecord(output, {"operation": "native_runtime_witness_stage", "freeze_sha256": freeze_sha256,
        "scheduled": [{"id": row["id"], "case_ids": row["case_ids"]} for row in schedule], "automatic_retry": False})
    started, cpu = time.perf_counter(), time.process_time()
    deadline = time.monotonic() + config["limits"]["stage_seconds"]
    outcomes = [{"id": row["id"], "case_ids": row["case_ids"], "status": "unexecuted"} for row in schedule]
    error = None
    preflight = postflight = None
    try:
        _write_raw(output / "freeze.json", raw)
        preflight = audit(config, preparation)
        for name in ("ordinary-cases", "ordinary-worker", "IX06-interruption", "IX08-concurrency"):
            need(not (base / name).exists(), "Prior native output forbids redispatch: " + name)
        from tether._process import ProcessLimits, supervise_command, validate_success_report
        # The supervisor is part of the pinned environment; verify its module here.
        import tether._process as process_module
        need(str(safe_path(process_module.__file__)) in config["code_pins"], "Qualified process supervisor is unpinned")
        runner = supervise_command if execute is None else execute
        for index, item in enumerate(schedule):
            remaining = deadline - time.monotonic()
            need(remaining > 0, "Runtime stage budget exhausted before next attempt")
            item["prefix"].mkdir(exist_ok=False)
            if item["id"] == "ordinary16":
                (base / "ordinary-cases").mkdir(exist_ok=False)
            limits = ProcessLimits(timeout_seconds=min(item["seconds"], remaining),
                                   max_output_bytes=config["limits"]["process_output_bytes"])
            attempt = CaseRecord(output / item["id"], {"argv": item["argv"], "limits": limits.payload(),
                "case_ids": item["case_ids"], "automatic_retry": False})
            outcomes[index] = {"id": item["id"], "case_ids": item["case_ids"],
                               "status": "attempt_reserved", "dispatch_attempted": False}
            stage.append("attempt_started", {"id": item["id"], "request": attempt.request_proof})
            execution = None
            failure = None
            child_started = time.perf_counter()
            try:
                outcomes[index]["dispatch_attempted"] = True
                with clean_environment(attempt.path):
                    execution = runner(item["argv"], limits=limits)
                validate_success_report(execution.supervision, limits, len(execution.stdout), len(execution.stderr))
                need(execution.returncode == 0, "Witness child returned nonzero: " + str(execution.returncode))
                report = parse(read_bytes(item["result"], 4 * 1024**2))
                expected_status = "success" if item["id"] == "ordinary16" else "PASS"
                need(report["status"] == expected_status, "Witness child terminal status differs")
            except BaseException as exc:
                failure = {"type": type(exc).__name__, "message": str(exc)}
                execution = getattr(exc, "tether_engine_result", getattr(exc, "result", execution))
            captured = {}
            if execution is not None:
                captured = {"stdout": _write_raw(attempt.path / "stdout.bin", execution.stdout),
                            "stderr": _write_raw(attempt.path / "stderr.bin", execution.stderr)}
            outcome = {"id": item["id"], "case_ids": item["case_ids"],
                "status": "completed" if failure is None else "failed", "error": failure,
                "returncode": execution.returncode if execution else None,
                "supervision": execution.supervision if execution else None,
                "captures": captured, "wall_seconds": time.perf_counter() - child_started,
                "result": {"path": str(item["result"]), **proof(item["result"])} if item["result"].exists() else None}
            terminal = attempt.finish(outcome)
            outcome["attempt_receipt"] = terminal["receipt"]
            outcomes[index] = outcome
            stage.append("attempt_finished", outcome)
            if failure is not None:
                error = failure
                break
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        for outcome in outcomes:
            if outcome["status"] == "attempt_reserved":
                outcome.update(status="failed_unresolved", error=error)
    try:
        postflight = audit(config, preparation)
    except BaseException as exc:
        postflight = {"status": "failed", "error": type(exc).__name__ + ": " + str(exc)}
        error = error or {"type": type(exc).__name__, "message": str(exc)}
    witness_outputs = {}
    for directory in ("ordinary-cases", "ordinary-worker", "IX06-interruption", "IX08-concurrency"):
        if (base / directory).is_dir():
            for path in sorted((base / directory).rglob("*")):
                if path.is_file():
                    witness_outputs[str(path.relative_to(base)).replace("\\", "/")] = proof(path)
    result = {"schema_version": 1, "status": "completed" if error is None else "failed", "error": error,
        "schedule": outcomes, "case_dispositions": recover_case_dispositions(base, schedule),
        "scheduled_operation_groups": len(schedule),
        "scheduled_logical_cases": sum(len(item["case_ids"]) for item in schedule),
        "witness_output_root": str(base), "witness_outputs": witness_outputs,
        "preflight": preflight, "postflight": postflight,
        "parent_wall_before_final_seal_seconds": time.perf_counter() - started,
        "parent_cpu_before_final_seal_seconds": time.process_time() - cpu,
        "provider_cost_usd": 0, "automatic_retry": False,
        "scope": "Scripted controls; owned-child bounds, not arbitrary descendant containment; parent proof and sealing overhead is not hard-preempted."}
    terminal = stage.finish(result)
    inventory = {str(path.relative_to(output)).replace("\\", "/"): proof(path)
                 for path in sorted(output.rglob("*")) if path.is_file()}
    publish(output / "SEALED.json", {"schema_version": 1, "status": result["status"],
        "freeze_sha256": freeze_sha256, "stage_receipt": terminal["receipt"], "files": inventory,
        "wall_through_inventory_seconds": time.perf_counter() - started})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_stage(args.freeze, args.freeze_sha256, args.output)
    print({"status": result["status"], "schedule": [{"id": row["id"], "status": row["status"]} for row in result["schedule"]]})
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
