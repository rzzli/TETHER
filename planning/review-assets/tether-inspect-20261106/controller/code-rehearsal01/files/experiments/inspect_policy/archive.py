"""Shared stdlib archive wrapper and scoring projections for all comparison arms.

The full immutable equal_policy independent implementation is reused and counted.
Inspect supplies scheduling/scoring/logging, not the project's biomedical policy.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
import sys
import time

from .records import (CaseRecord, canonical, checked_json, digest, freeze,
                      inspect_record, parse, proof, safe_path, thaw)

# Reused v2 modules retain their original top-level equal_policy imports.
EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))


def checked_rows(rows):
    result = []
    ids = set()
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"control_id", "bundle_root", "descriptor"}:
            raise ValueError("Task-only archive row fields differ")
        ident = row["control_id"]
        if type(ident) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident) or ident in ids:
            raise ValueError("Unique safe case ID required")
        ids.add(ident)
        pin = row["descriptor"]
        if not isinstance(pin, Mapping) or set(pin) != {"path", "sha256", "bytes"}:
            raise ValueError("Descriptor proof fields differ")
        if type(pin["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]):
            raise ValueError("Descriptor digest invalid")
        if type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= 16 * 1024 * 1024:
            raise ValueError("Descriptor size invalid")
        name = pin["path"]
        if type(name) is not str or ":" in name or name.startswith(("/", "\\")) or any(part in ("", ".", "..") for part in name.replace("\\", "/").split("/")):
            raise ValueError("Descriptor path must be contained and relative")
        root = safe_path(row["bundle_root"])
        path = safe_path(root / name)
        if not path.is_relative_to(root) or not root.is_dir():
            raise ValueError("Bundle boundary invalid")
        result.append(freeze(row))
    if not result:
        raise ValueError("A nonempty schedule is required")
    return tuple(result)


def execute_archive_case(row, output_root, *, validator=None):
    """Identical durable wrapper for Inspect and the parent's direct arms.

    Per-case total timings include source capture and terminal receipt writing.
    Operation timing covers only the selected validator call. These are neither
    physical I/O volumes nor fresh-process import timings.
    """
    wall, cpu = time.perf_counter(), time.process_time()
    row = checked_rows([row])[0]
    output_root = safe_path(output_root)
    bundle_root = safe_path(row["bundle_root"])
    if output_root.is_relative_to(bundle_root) or bundle_root.is_relative_to(output_root):
        raise ValueError("Output and frozen input trees must not overlap")
    if validator is None:
        from equal_policy_v2.independent import validate_bundle
        validator = validate_bundle
    implementation = validator.__module__ + "." + validator.__qualname__
    record = CaseRecord(output_root / row["control_id"], row)
    (record.path / "scratch").mkdir()
    observed = None
    error = None
    operation_wall = operation_cpu = None
    status = "error"
    try:
        declared = row["descriptor"]
        descriptor = checked_json(Path(row["bundle_root"]) / declared["path"],
                                  {key: declared[key] for key in ("sha256", "bytes")}, 16 * 1024 * 1024)
        if descriptor.get("control_id") != row["control_id"]:
            raise ValueError("Descriptor/case identity differs")
        record.append("validation_started", {"descriptor_sha256": declared["sha256"],
                                               "implementation": implementation})
        started_wall, started_cpu = time.perf_counter(), time.process_time()
        try:
            observed = validator(Path(row["bundle_root"]), thaw(descriptor),
                                 scratch_dir=record.path / "scratch")
        finally:
            operation_wall = time.perf_counter() - started_wall
            operation_cpu = time.process_time() - started_cpu
        required = {"schema_version", "control_id", "decision", "stage",
                    "violated_obligations", "checked_scope", "observables"}
        if (type(observed) is not dict or not required <= observed.keys() or
                observed["control_id"] != row["control_id"] or
                observed["decision"] not in ("accept", "reject", "inspect_only", "unsupported", "error")):
            raise ValueError("Native policy result contract differs")
        observed = thaw(freeze(observed))
        status = "error" if observed["decision"] == "error" else "completed"
    except BaseException as exc:
        status = "interrupted" if not isinstance(exc, Exception) else "error"
        error = {"type": type(exc).__name__, "message": str(exc)}
    result = {"schema_version": 1, "control_id": row["control_id"], "status": status,
              "decision": observed, "error": error, "implementation": implementation,
              "source_descriptor_proof": thaw(row["descriptor"]),
              "resources": {"operation_wall_seconds": operation_wall,
                            "operation_cpu_seconds": operation_cpu}}
    receipt = record.finish(result)["receipt"]
    return {"result": freeze(result), "receipt": receipt, "output": str(record.path),
            "case_wall_seconds": time.perf_counter() - wall,
            "case_cpu_seconds": time.process_time() - cpu}


def replay_archive_case(path, receipt_sha256):
    """Read-only, source-inclusive replay, never re-executing a producer/model."""
    record = inspect_record(path, receipt_sha256=receipt_sha256)
    original = record["result"]
    if original["status"] != "completed":
        raise ValueError("Failed/unfinished case is not a successful replay")
    row = checked_rows([record["request"]])[0]
    descriptor = checked_json(Path(row["bundle_root"]) / row["descriptor"]["path"],
                              {key: row["descriptor"][key] for key in ("sha256", "bytes")})
    from equal_policy_v2.independent import validate_bundle
    if original["implementation"] != validate_bundle.__module__ + "." + validate_bundle.__qualname__:
        raise ValueError("Replay endpoint is scoped to the independent policy implementation")
    # Policy preparation may write normalized selected files. Re-verification
    # uses a separate caller-owned temporary scratch directory for that case.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="replay-", dir=Path(path).parent) as temporary:
        observed = validate_bundle(Path(row["bundle_root"]), thaw(descriptor), scratch_dir=Path(temporary))
    if canonical(observed) != canonical(original["decision"]):
        raise ValueError("Source-inclusive policy replay differs")
    return freeze({"status": "verified", "source_inclusive": True,
                   "model_calls": 0, "decision_sha256": digest(observed),
                   "scientific_validation": "not_established"})


_MISSING = {"missing_observable": True}


def observable(observed, name):
    """Declared BG02 projections; missing is distinct from explicit null."""
    if name in ("admitted_observation_ids", "eligible_observation_ids", "selected_observation_ids", "scorer_preflight"):
        return observed.get(name, _MISSING)
    if name in ("prediction_status", "prediction_reason"):
        return observed.get("prediction", {}).get(name.removeprefix("prediction_"), _MISSING)
    if name == "probability_is_null":
        prediction = observed.get("prediction", {})
        return prediction["probability"] is None if "probability" in prediction else _MISSING
    if name in ("feature_values", "feature_status", "dependency_groups"):
        values = observed.get("features", {}).get("values")
        if not isinstance(values, Mapping):
            return _MISSING
        field = {"feature_values": "value", "feature_status": "status", "dependency_groups": "dependency_groups"}[name]
        return {key: row.get(field, _MISSING) for key, row in values.items()}
    if name == "exclusion_reasons":
        return [row["reason"] for row in observed["exclusions"]] if "exclusions" in observed else _MISSING
    if name == "dispatches":
        return observed.get("calls", _MISSING)
    if name == "accounting_basis":
        if "accounting" not in observed:
            return _MISSING
        bases = sorted({row["basis"] for row in observed["accounting"]})
        return bases[0] if len(bases) == 1 else bases
    if name == "later_dispatches":
        return len(observed["dispatches"]) - 1 if observed.get("dispatches") else _MISSING
    recovery = observed.get("recovery", {})
    if name == "unresolved_attempts":
        return recovery.get("unresolved_attempts", _MISSING)
    if name == "recovery_may_dispatch":
        action = recovery.get("recovery_action", "")
        return False if action.startswith("inspect only;") and "never automatically repeat" in action else _MISSING
    raise ValueError("Unimplemented oracle observable: " + name)


def compare_result(observed, expected):
    if observed["decision"] in ("error", "unsupported"):
        return {"has_verdict": False, "decision_match": False, "observable_match": False,
                "full_match": False, "mismatches": [], "reason": observed["decision"]}
    mismatches = []
    for name, value in expected["observables"].items():
        actual = observable(observed["observables"], name)
        if isinstance(value, Mapping) and isinstance(actual, Mapping):
            actual = {key: actual.get(key, _MISSING) for key in value}
        if canonical(actual) != canonical(value):
            mismatches.append(name)
    same = observed["decision"] == expected["decision"]
    return {"has_verdict": True, "decision_match": same, "observable_match": not mismatches,
            "full_match": same and not mismatches, "mismatches": mismatches, "reason": None}

