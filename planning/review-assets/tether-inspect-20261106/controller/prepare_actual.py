"""Freeze the authorized BG05 inputs only; never launch a comparison worker."""
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy import controller
from experiments.inspect_policy.records import checked_json, proof, publish, thaw

EVIDENCE = ROOT/"planning/review-assets/tether-inspect-20261106"
BASE = ROOT/"data/benchmark/tether-inspect-20261106-attempt01"
RUNTIME = ROOT/"data/cache/tether-inspect-runtime-witnesses-20261106-attempt01"
ENVIRONMENT_SHA = "d759f9fb05bcb985167add81a273e09294cfa325870c2de072e309fcdb9053b6"


def main():
    started = time.perf_counter()
    BASE.mkdir(parents=True, exist_ok=False)
    try:
        environment = EVIDENCE/"environment/attempt02/ENVIRONMENT-QUALIFICATION.json"
        runtime = checked_json(RUNTIME/"PREPARATION.json", proof(RUNTIME/"PREPARATION.json"))
        assert runtime["status"] == "prepared_not_executed" and runtime["input_files"] == 176
        runtime_inputs = []
        for relative, expected in runtime["input_inventory"].items():
            path = RUNTIME/relative
            assert proof(path) == thaw(expected), str(path)
            runtime_inputs.append(path)
        extras = [
            ROOT/"planning/TETHER Inspect Comparison Protocol 2026-11-06.md",
            ROOT/"planning/review-assets/tether-equal-policy-20261102/POLICY-SPEC.md",
            ROOT/"planning/review-assets/tether-equal-policy-20261102/policy-spec.json",
            environment, RUNTIME/"PREPARATION.json", RUNTIME/"ordinary-recipe.json", Path(__file__),
        ] + runtime_inputs
        extras += [EVIDENCE/relative for relative in (
            "policy/PORT-DESIGN.md", "policy/OBLIGATION-MATRIX.json", "policy/OBLIGATION-MATRIX.md",
            "policy/MATRIX-VALIDATION.json", "policy/INSPECT-SOURCE-REVIEW.json", "policy/IMPLEMENTATION-REVIEW.md",
            "controller/QUALIFICATION.md", "controller/INVENTORY-QUALIFICATION-01.json",
            "controller/qualify_current_inventory.py", "controller/rehearse.py",
            "controller/code-rehearsal01/ARCHIVE.json", "controller/code-rehearsal01/ARCHIVE-INITIAL-FAILURE.json",
            "controller-tests05-red.log", "controller-tests06-green.log", "controller-tests07-inventory-red.log",
            "controller-tests08-inventory-green.log", "integration/INTERFACE-AND-QUALIFICATION.md",
            "integration/archive-projection-red01.log", "integration/archive-projection-green01.log",
            "integration/boundary-tests01.log", "integration/evidence-tests01.log",
            "integration/native-tests04.log", "integration/native-timeout-green01.log",
            "integration/runtime-process-tests01.log", "integration/prepare_runtime_inputs.py",
            "stage/INHERITED-INPUT-CHECK-01.json", "stage/PREPARATION-VALIDATION-01.json",
            "stage/preflight.py", "stage/implementation_inventory.py",
            "reconstruction/reconstruct.py", "reconstruction/test_reconstruct.py",
            "reconstruction/FICTIONAL-STAGE-01.json", "reconstruction/FICTIONAL-STAGE-02.json",
            "reconstruction/TESTS-GREEN-09.log",
        )]
        for attempt in ("01", "02"):
            rehearsal = ROOT/("data/cache/tether-inspect-controller-rehearsal-attempt"+attempt)
            extras += [rehearsal/"QUALIFICATION.json", rehearsal/"run/SEALED.json", rehearsal/"preparation/FROZEN.json"]
        extras = sorted(set(path.absolute() for path in extras))
        extra_proofs = {str(path): proof(path) for path in extras}
        request = {"operation": "prepare_only", "actual_cases_dispatched": 0,
            "runtime_input_files": len(runtime_inputs), "additional_sources": extra_proofs,
            "excluded_pending_helpers": ["integration/run_runtime_stage.py", "reconstruction/runtime_reconstruct.py"],
            "provider_cost_usd": 0, "limits": controller.DEFAULT_LIMITS}
        publish(BASE/"PREPARATION-REQUEST.json", request)
        config = controller.freeze_run(
            ROOT/"data/benchmark/tether-equal-policy-v2-patched-20261105-attempt01",
            environment, ENVIRONMENT_SHA, BASE/"freeze", additional_source_paths=extras)
        frozen = proof(BASE/"freeze/FROZEN.json")
        audit = controller.global_source_audit(config)
        assert len(config["rows"]) == 109 and config["expected_cells"] == 981
        assert len(config["schedule"]) == 9
        assert thaw(config["limits"]) == controller.DEFAULT_LIMITS
        command = [config["python"]["path"], "-I", "-B", str(ROOT/"experiments/inspect_policy/controller.py"),
                   "run", "--freeze", str(BASE/"freeze/FROZEN.json"), "--sha", frozen["sha256"],
                   "--output", str(BASE/"run")]
        powershell = "& "+" ".join("'"+part.replace("'", "''")+"'" for part in command)
        ready = {"schema_version": 1, "status": "prepared_and_verified_not_dispatched",
            "freeze": {"path": str(BASE/"freeze/FROZEN.json"), **frozen},
            "preparation_receipt": proof(BASE/"freeze/receipt.json"),
            "scheduled_cases": 109, "scheduled_cells": 981, "batches": 9,
            "actual_cases_dispatched": 0, "provider_calls": 0, "provider_cost_usd": 0,
            "full_input_pins": len(config["input_pins"]), "batch_input_pins": len(config["batch_input_pins"]),
            "archived_sources": len(config["source_archive"]), "runtime_input_files": len(runtime_inputs),
            "final_preparation_audit": audit, "limits": thaw(config["limits"]),
            "command": command, "powershell_command": powershell,
            "run_output_exists": (BASE/"run").exists(),
            "source_hold": "Original paths and archived source copies held through execution and reconstruction",
            "preparation_wall_seconds": time.perf_counter()-started}
        publish(BASE/"READY.json", ready)
        print("PREPARED ONLY: "+frozen["sha256"])
    except BaseException as exc:
        publish(BASE/"PREPARATION-FAILED.json", {"error_class": type(exc).__name__, "message": str(exc),
            "automatic_retry": False, "actual_cases_dispatched": 0})
        raise


if __name__ == "__main__":
    main()
