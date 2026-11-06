"""Independent stdlib-only postflight membership/content check; no execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT/"data/cache/tether-inspect-runtime-witnesses-20261106-attempt01"
HERE = Path(__file__).parent
FREEZE_SHA = "532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5"
INPUT_CHECK_SHA = "b68352f5f40c7ce10296372f646a956fbfab7a61f6ef4a6af92dbac3086446f8"
SEAL_SHA = "92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f"


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("Nonregular or linked file: "+str(path))
    return info


def file_proof(path):
    path = Path(path)
    before = regular(path)
    hashed = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("File identity changed during open")
        while chunk := stream.read(1024*1024):
            hashed.update(chunk)
            size += len(chunk)
        after_open = os.fstat(stream.fileno())
    after = regular(path)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if signature(before) != signature(after_open) or signature(before) != signature(after) or size != before.st_size:
        raise ValueError("File changed during capture: "+str(path))
    return {"sha256": hashed.hexdigest(), "bytes": size}


def load(path, expected=None):
    raw = Path(path).read_bytes()
    pin = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    if expected is not None:
        assert pin == expected if isinstance(expected, dict) else pin["sha256"] == expected
    return json.loads(raw), pin


def inventory(root):
    root = Path(root)
    names = set()
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            info = (Path(parent)/name).lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Linked directory in inventoried tree")
        for name in files:
            path = Path(parent)/name
            regular(path)
            names.add(path.relative_to(root).as_posix())
    return names


def check_pins(pins):
    for name, expected in pins.items():
        assert file_proof(name) == expected, name
    return {"files": len(pins), "logical_bytes": sum(p["bytes"] for p in pins.values())}


def main():
    started = time.perf_counter()
    output = HERE/"POSTFLIGHT-EXACT-INVENTORY-01.json"
    assert not output.exists()
    result = {"schema_version": 1, "status": "failed", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Independent stdlib-only content and exact file-membership postcheck; no case execution or policy recomputation"}
    try:
        frozen, freeze_pin = load(BASE/"freeze/FROZEN.json", FREEZE_SHA)
        input_check, input_check_pin = load(BASE/"freeze/INPUT-INVENTORY-AT-PREPARATION.json", INPUT_CHECK_SHA)
        pins = frozen["code_pins"]
        preparation, prep_pin = load(frozen["preparation"]["path"], {k: frozen["preparation"][k] for k in ("sha256", "bytes")})
        assert prep_pin["sha256"] == input_check["preparation_sha256"]
        env_inventory_name = next(p for p in pins if p.replace("\\", "/").endswith("/ENVIRONMENT-INVENTORY.json"))
        env_inventory, inventory_pin = load(env_inventory_name, pins[env_inventory_name])
        env_root = Path(frozen["python"]["path"]).parent.parent
        expected_environment = {p["path"].replace("\\", "/") for p in env_inventory["files"]}
        assert len(expected_environment) == 9014
        assert inventory(env_root) == expected_environment
        expected_inputs = {p for p in preparation["input_inventory"] if p.startswith(("inputs/", "process-inputs/"))}
        input_membership = lambda: {name+"/"+relative for name in ("inputs", "process-inputs") for relative in inventory(BASE/name)}
        assert len(expected_inputs) == input_check["actual_files"] == input_check["expected_files"] == 175
        assert input_membership() == expected_inputs
        all_pins = dict(pins)
        all_pins[frozen["python"]["path"]] = {k: frozen["python"][k] for k in ("sha256", "bytes")}
        all_pins[frozen["preparation"]["path"]] = prep_pin
        for relative, expected in preparation["input_inventory"].items():
            all_pins[str(BASE/relative)] = expected
        counts = check_pins(all_pins)
        assert inventory(env_root) == expected_environment
        assert input_membership() == expected_inputs
        environment_pins = {str(env_root/p["path"]): {k: p[k] for k in ("sha256", "bytes")} for p in env_inventory["files"]}
        assert all(all_pins.get(name) == pin for name, pin in environment_pins.items())
        product_python = [p for p in environment_pins if p.endswith(".py") and any(
            "/site-packages/"+package+"/" in p.replace("\\", "/") for package in ("asof", "tether"))]
        assert len(product_python) == 85
        source_index, source_index_pin = load(BASE/"freeze/source-archive/INDEX.json",
            pins[str(BASE/"freeze/source-archive/INDEX.json")])
        for original, archived in source_index["files"].items():
            expected = {k: archived[k] for k in ("sha256", "bytes")}
            assert all_pins[original] == expected
            assert all_pins[str(BASE/"freeze/source-archive"/archived["path"])] == expected
        anchor, anchor_pin = load(HERE/"ROOT-RUNTIME-ANCHOR-01.json")
        assert anchor["sha256"] == SEAL_SHA
        seal, seal_pin = load(BASE/"runtime-stage/SEALED.json", SEAL_SHA)
        assert seal["freeze_sha256"] == FREEZE_SHA
        actual_outputs = inventory(BASE/"runtime-stage")-{"SEALED.json"}
        assert actual_outputs == set(seal["files"])
        stage_proofs = check_pins({str(BASE/"runtime-stage"/name): p for name, p in seal["files"].items()})
        stage, stage_pin = load(BASE/"runtime-stage/result.json", seal["files"]["result.json"])
        assert stage["status"] == seal["status"] == "completed"
        assert stage["scheduled_logical_cases"] == 19 and stage["scheduled_operation_groups"] == 3
        assert all(row["status"] == "completed" and row["returncode"] == 0 for row in stage["schedule"])
        witness_actual = {name+"/"+relative for name in ("ordinary-cases", "ordinary-worker", "IX06-interruption", "IX08-concurrency")
                          for relative in inventory(BASE/name)}
        assert witness_actual == set(stage["witness_outputs"])
        witness_proofs = check_pins({str(BASE/name): pin for name, pin in stage["witness_outputs"].items()})
        outer, outer_pin = load(HERE/"RUNTIME-OUTER-TIMING-01.json")
        assert outer["exit_code"] == 0 and outer["wall_seconds"] == 77.2505843
        ordinary_ref = stage["schedule"][0]["result"]
        ordinary, _ = load(ordinary_ref["path"], {k: ordinary_ref[k] for k in ("sha256", "bytes")})
        audit_seconds = stage["preflight"]["wall_seconds"]+stage["postflight"]["wall_seconds"]
        group_seconds = sum(row["wall_seconds"] for row in stage["schedule"])
        timing = {"outer_wall_through_return_seconds": outer["wall_seconds"],
            "outer_scope": outer["scope"], "known_file_audit_wall_seconds": audit_seconds,
            "operation_group_wall_seconds": {row["id"]: row["wall_seconds"] for row in stage["schedule"]},
            "owned_child_supervised_wall_seconds": {row["id"]: row["supervision"]["total_elapsed_seconds"] for row in stage["schedule"]},
            "parent_wall_before_final_seal_seconds": stage["parent_wall_before_final_seal_seconds"],
            "stage_wall_through_output_inventory_seconds": seal["wall_through_inventory_seconds"],
            "other_parent_wall_before_seal_seconds": stage["parent_wall_before_final_seal_seconds"]-audit_seconds-group_seconds,
            "finalization_to_inventory_seconds": seal["wall_through_inventory_seconds"]-stage["parent_wall_before_final_seal_seconds"],
            "outer_minus_inner_inventory_seconds": outer["wall_seconds"]-seal["wall_through_inventory_seconds"],
            "parent_cpu_before_final_seal_seconds": stage["parent_cpu_before_final_seal_seconds"],
            "ordinary_worker_cpu_before_publication_seconds": ordinary["cpu_before_publication_seconds"],
            "ordinary_worker_wall_before_publication_seconds": ordinary["wall_before_publication_seconds"],
            "total_process_tree_cpu_seconds": None, "peak_memory_bytes": None,
            "unknown_reason": "No complete process-tree CPU or runtime peak-memory measurement was retained. Timers have different boundaries; group subprocess intervals overlap their contained work.",
            "ordinary_native_usage": ordinary["native_usage"],
            "usage_scope": "Scripted local provider telemetry; not measured language-model tokenization or actual remote-provider billing.",
            "provider_cost_usd": 0}
        result.update(status="pass", freeze=freeze_pin, input_preparation_check=input_check_pin,
            environment_inventory=inventory_pin, known_original_content=counts,
            exact_environment_files=9014, exact_product_python_sources=85,
            exact_prepared_tree_files=175, separate_pinned_recipe_files=1,
            membership_scope="Exact file membership before and after this audit; empty-directory identities and transient changes are not independently attested.",
            original_and_archived_sources=len(source_index["files"]), source_archive_index=source_index_pin,
            root_postexecution_anchor=anchor_pin, anchor_scope=anchor["scope"],
            runtime_seal=seal_pin, stage_outputs=stage_proofs, witness_outputs=witness_proofs,
            timing_source=outer_pin, timing_and_resources=timing,
            runtime_semantic_conformance="Separate independent reconstruction; this audit establishes preservation and resource-record consistency only.",
            helper=file_proof(__file__), audit_wall_seconds=time.perf_counter()-started,
            original_artifacts_modified=False, cases_dispatched=0)
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, message=str(exc), audit_wall_seconds=time.perf_counter()-started)
        raise
    finally:
        with output.open("xb") as stream:
            stream.write(json.dumps(result,sort_keys=True,separators=(",", ":"),allow_nan=False).encode())
    print("PASS: exact environment, prepared-input, source and output inventories")


if __name__ == "__main__":
    main()
