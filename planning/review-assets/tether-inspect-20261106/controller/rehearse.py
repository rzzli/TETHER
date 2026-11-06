"""Fresh all-three-arm rehearsal on two invented policy cases, never EP cases."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"experiments/inspect_policy/tests"))
from fixtures import source
from experiments.inspect_policy import controller
from experiments.inspect_policy.records import proof, publish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output).absolute()
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        corpus = root/"corpus"
        (corpus/"bundles").mkdir(parents=True)
        source(corpus/"bundles/FICTIONAL-POSITIVE", "FICTIONAL-POSITIVE")
        source(corpus/"bundles/FICTIONAL-INVALID", "FICTIONAL-INVALID",
               mutate=lambda d: d["case"].update(task="invalid-task"))
        cases = [{"control_id": key, "descriptor": "bundles/"+key+"/descriptor.json"}
                 for key in ("FICTIONAL-POSITIVE", "FICTIONAL-INVALID")]
        oracle = {"cases": [{"control_id": cases[0]["control_id"], "decision": "accept", "observables": {}},
                            {"control_id": cases[1]["control_id"], "decision": "reject", "observables": {}}]}
        oracle_pin = publish(corpus/"oracle.json", oracle)
        files = {p.relative_to(corpus/"bundles").as_posix(): proof(p)
                 for p in (corpus/"bundles").rglob("*") if p.is_file()}
        directories = [p.relative_to(corpus/"bundles").as_posix()
                       for p in (corpus/"bundles").rglob("*") if p.is_dir()]
        publish(corpus/"FROZEN.json", {"cases": cases, "bundles": files,
                "bundle_directories": directories, "oracle_pin": oracle_pin, "sources": {}})
        receipt = ROOT/"planning/review-assets/tether-inspect-20261106/environment/attempt02/ENVIRONMENT-QUALIFICATION.json"
        controller.freeze_run(corpus, receipt, proof(receipt)["sha256"], root/"preparation",
                              additional_source_paths=[Path(__file__)], mode="fictional")
        freeze_path = root/"preparation/FROZEN.json"
        run_started = time.perf_counter()
        result = controller.run_stage(freeze_path, proof(freeze_path)["sha256"], root/"run")
        through_seal_seconds = time.perf_counter()-run_started
        seal = proof(root/"run/SEALED.json")
        verified = controller.verify_stage(root/"run", seal["sha256"])
        assert result["status"] == verified["status"] == "completed", "Fictional comparison did not complete"
        assert result["retained_cells"] == 18 and all(b["score"]["full_conformance"] == 2 for b in result["batches"])
        publish(root/"QUALIFICATION.json", {"status": "pass", "fictional_cases": 2, "arms": 3, "repetitions": 3,
            "scheduled_cells": 18, "actual_EP_cases_executed": 0, "stage_seal": seal,
            "through_stage_seal_seconds": through_seal_seconds, "total_rehearsal_seconds": time.perf_counter()-started,
            "native_inspect_batches": 3, "real_model_calls": 0, "provider_cost_usd": 0})
        print(json.dumps({"status": "pass", "fictional_cells": 18, "seal_sha256": seal["sha256"]}))
    except BaseException as exc:
        publish(root/"FAILED.json", {"error_class": type(exc).__name__, "message": str(exc), "automatic_retry": False})
        raise


if __name__ == "__main__":
    main()
