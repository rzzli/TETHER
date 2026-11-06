"""One bounded caller-supervised native witness process; never resumes/retries."""
import argparse
import hashlib
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import parse, proof, publish, read_bytes
from experiments.inspect_policy.network import install_guard


def run(recipe_path, recipe_sha256, work, start_gate=None):
    work = Path(work).absolute()
    work.mkdir(parents=False, exist_ok=False)
    started, cpu = time.perf_counter(), time.process_time()
    os.environ.update(PYTHON_DOTENV_DISABLED="1", INSPECT_CACHE_DIR=str(work / "cache"),
                      TIKTOKEN_CACHE_DIR=str(work / "token-cache"))
    network = install_guard()
    raw = read_bytes(recipe_path, 4 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != recipe_sha256:
        raise ValueError("External witness recipe pin differs")
    recipe = parse(raw)
    if set(recipe) != {"rows", "output_root", "oracle_path", "oracle_proof"}:
        raise ValueError("Witness recipe fields differ")
    publish(work / "recipe.json", recipe)
    from inspect_ai import eval
    from experiments.inspect_policy.runtime import build_runtime_task
    task = build_runtime_task(recipe["rows"], recipe["output_root"], recipe["oracle_path"], recipe["oracle_proof"])
    publish(work / "READY.json", {"recipe_sha256": recipe_sha256, "scheduled": len(recipe["rows"]), "provider_calls": 0})
    if start_gate is not None:
        deadline = time.monotonic() + 30
        while not Path(start_gate).is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError("Fictional concurrency gate did not open")
            time.sleep(0.02)
    logs = eval(task, display="none", log_dir=str(work / "logs"), log_format="json",
        fail_on_error=False, retry_on_error=0, score_on_error=False, max_retries=0,
        max_samples=1, max_tasks=1, time_limit=120, log_shared=False, notification=False,
        log_samples=True, log_model_api=True)
    if len(logs) != 1 or network["blocked"]:
        raise ValueError("Native witness log/network outcome differs")
    log = logs[0]
    result = {"schema_version": 1, "status": log.status, "recipe_sha256": recipe_sha256,
        "scheduled": [row["id"] for row in recipe["rows"]], "native_log": {"path": str(log.location), **proof(log.location)},
        "samples": [{"id": sample.id, "epoch": sample.epoch, "native_error": sample.error is not None,
                     "native_scores": {key: score.value for key, score in (sample.scores or {}).items()},
                     "record": (sample.metadata or {}).get("policy_record")} for sample in (log.samples or [])],
        "native_usage": {key: value.model_dump(mode="json") for key, value in log.stats.model_usage.items()},
        "network": network, "wall_before_publication_seconds": time.perf_counter() - started,
        "cpu_before_publication_seconds": time.process_time() - cpu,
        "provider_cost_usd": 0, "scientific_inference": False, "automatic_retry": False}
    publish(work / "RESULT.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--recipe-sha256", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--start-gate", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.recipe, args.recipe_sha256, args.work, args.start_gate)
        print("Scripted witness process finished: " + result["status"])
    except BaseException as exc:
        if args.work.is_dir() and not (args.work / "FAILURE.json").exists():
            publish(args.work / "FAILURE.json", {"error_type": type(exc).__name__, "message": str(exc), "automatic_retry": False})
        raise


if __name__ == "__main__":
    main()
