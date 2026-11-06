"""Prepare the separate native runtime-witness freeze; never execute a witness."""
import importlib.util
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.controller import archive_sources, source_pins
from experiments.inspect_policy.records import checked_json, canonical, proof, publish, thaw

EVIDENCE = ROOT/"planning/review-assets/tether-inspect-20261106"
BASE = ROOT/"data/cache/tether-inspect-runtime-witnesses-20261106-attempt01"
PREPARATION_SHA = "b17fdfba429a913cb5a12bd1d1c5e0388031066ed45d7e93fca6c931fa55077c"
RUNNER_SHA = "097d32ce611151768c4377b68693c7d132c1b2e77f83200a581dbe3f6eb1e7cc"
ENVIRONMENT_SHA = "d759f9fb05bcb985167add81a273e09294cfa325870c2de072e309fcdb9053b6"


def main():
    started = time.perf_counter()
    output = BASE/"freeze"
    output.mkdir(exist_ok=False)
    try:
        preparation_path = BASE/"PREPARATION.json"
        preparation_pin = proof(preparation_path)
        assert preparation_pin["sha256"] == PREPARATION_SHA
        preparation = checked_json(preparation_path, preparation_pin)
        assert preparation["status"] == "prepared_not_executed" and preparation["input_files"] == 176
        runner_path = EVIDENCE/"integration/run_runtime_stage.py"
        assert proof(runner_path)["sha256"] == RUNNER_SHA
        qualification_path = EVIDENCE/"integration/RUNTIME-STAGE-QUALIFICATION-02.json"
        qualification = checked_json(qualification_path, proof(qualification_path))
        assert qualification["status"] == "PASS" and qualification["tests"] == 7
        for relative, expected in qualification["proofs"].items():
            assert proof(qualification_path.parent/relative) == thaw(expected)
        environment_path = EVIDENCE/"environment/attempt02/ENVIRONMENT-QUALIFICATION.json"
        assert proof(environment_path)["sha256"] == ENVIRONMENT_SHA
        environment = checked_json(environment_path, proof(environment_path))
        assert environment["status"] == "pass" and environment["inspect_ai_version"] == "0.3.287"
        inventory_reference = next(p for p in environment["proofs"] if p["path"].endswith("/ENVIRONMENT-INVENTORY.json"))
        inventory_path = ROOT/inventory_reference["path"]
        inventory = checked_json(inventory_path, {k: inventory_reference[k] for k in ("sha256", "bytes")})
        environment_root = Path(environment["python"]).parent.parent
        paths = {p.relative_to(environment_root).as_posix() for p in environment_root.rglob("*") if p.is_file()}
        expected_paths = {p["path"].replace("\\", "/") for p in inventory["files"]}
        assert len(paths) == 9014 and paths == expected_paths
        pins = {str(environment_root/p["path"]): {k: p[k] for k in ("sha256", "bytes")} for p in inventory["files"]}
        product_sources = {name: pin for name, pin in pins.items()
            if name.endswith(".py") and any("/site-packages/"+package+"/" in name.replace("\\", "/")
                                            for package in ("asof", "tether"))}
        assert len(product_sources) == 85
        for item in environment["proofs"]:
            pins[str(ROOT/item["path"])] = {k: item[k] for k in ("sha256", "bytes")}
        for relative, expected in preparation["input_inventory"].items():
            pins[str(BASE/relative)] = thaw(expected)
        extras = [environment_path, inventory_path, preparation_path, BASE/"ordinary-recipe.json", Path(__file__),
            ROOT/"planning/TETHER Inspect Comparison Protocol 2026-11-06.md",
            ROOT/"planning/review-assets/tether-equal-policy-20261102/POLICY-SPEC.md",
            ROOT/"planning/review-assets/tether-equal-policy-20261102/policy-spec.json"]
        extras += [EVIDENCE/relative for relative in (
            "policy/PORT-DESIGN.md", "policy/OBLIGATION-MATRIX.json", "policy/OBLIGATION-MATRIX.md",
            "policy/MATRIX-VALIDATION.json", "integration/RUNTIME-STAGE-QUALIFICATION-02.json",
            "integration/run_runtime_stage.py", "integration/run_process_witness.py",
            "integration/prepare_runtime_inputs.py", "integration/test_run_runtime_stage.py",
            "integration/runtime-stage-mock-tests03.log", "integration/runtime-process-tests01.log",
            "integration/native-tests04.log", "integration/boundary-tests01.log", "integration/evidence-tests01.log",
            "integration/INTERFACE-AND-QUALIFICATION.md", "controller/QUALIFICATION.md",
            "controller/INVENTORY-QUALIFICATION-01.json", "controller-tests08-inventory-green.log")]
        sources = source_pins(extras)
        sources.update(product_sources)
        pins.update(sources)
        archived = archive_sources(output/"source-archive", sources)
        for item in archived.values():
            pins[str(output/"source-archive"/item["path"])] = {k: item[k] for k in ("sha256", "bytes")}
        pins[str(output/"source-archive/INDEX.json")] = proof(output/"source-archive/INDEX.json")
        specification = importlib.util.spec_from_file_location("qualified_runtime_stage", runner_path)
        runner = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(runner)
        config = {"schema_version": 1,
            "preparation": {"path": str(preparation_path), **preparation_pin},
            "python": {"path": environment["python"], **proof(environment["python"])},
            "code_pins": pins, "limits": runner.DEFAULT_LIMITS}
        assert len(canonical(config)) <= 4*1024**2, "Runtime freeze exceeds qualified parser cap"
        runner.validate_limits(config["limits"])
        audit = runner.audit(config, preparation)
        _, schedule = runner.commands(config, preparation, BASE/"runtime-stage")
        assert len(schedule) == 3 and sum(len(item["case_ids"]) for item in schedule) == 19
        for name in ("ordinary-cases", "ordinary-worker", "IX06-interruption", "IX08-concurrency", "runtime-stage"):
            assert not (BASE/name).exists(), "Prior output exists: "+name
        frozen = publish(output/"FROZEN.json", config)
        command = [environment["python"], "-I", "-B", "-X", "pycache_prefix="+str(BASE/"runtime-parent-import-cache"),
                   str(runner_path), "--freeze", str(output/"FROZEN.json"), "--freeze-sha256", frozen["sha256"],
                   "--output", str(BASE/"runtime-stage")]
        powershell = "& "+" ".join("'"+part.replace("'", "''")+"'" for part in command)
        publish(output/"READY.json", {"schema_version": 1, "status": "prepared_and_verified_not_dispatched",
            "freeze": {"path": str(output/"FROZEN.json"), **frozen}, "command": command, "powershell_command": powershell,
            "audit": audit, "environment_files": len(paths), "exact_product_source_files": len(product_sources),
            "archived_source_and_evidence_files": len(sources), "prepared_input_files": 176,
            "scheduled_operation_groups": 3, "scheduled_logical_cases": 19, "actual_cases_dispatched": 0,
            "provider_calls": 0, "provider_cost_usd": 0, "limits": config["limits"],
            "preparation_wall_seconds": time.perf_counter()-started,
            "inventory_scope": "Exact environment membership verified at preparation; runner rehashes every frozen file before and after execution. Root final acceptance re-enumerates membership separately.",
            "analysis_freeze": "Independent runtime reconstruction remains outside this execution closure."})
        print("RUNTIME PREPARED ONLY: "+frozen["sha256"])
    except BaseException as exc:
        publish(output/"PREPARATION-FAILED.json", {"error_class": type(exc).__name__, "message": str(exc),
            "automatic_retry": False, "actual_cases_dispatched": 0})
        raise


if __name__ == "__main__":
    main()
