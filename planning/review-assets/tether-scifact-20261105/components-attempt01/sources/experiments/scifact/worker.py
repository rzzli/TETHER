"""Owned train/predict subprocess. No preparation manifest or held-out answers."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from asof.atomic import publish_bytes
from asof.serde import canonical, parse_json
from experiments.scifact.baseline import fit_model, load_model, save_model, LEARNER_SETTINGS, VECTORIZER_SETTINGS, SEED
from experiments.scifact.runtime import IOAudit, Watchdog, load_input, measured
from experiments.scifact.tether_adapter import NativeSession


def write(path, value):
    publish_bytes(path, canonical(value) + b"\n")


def rows(raw):
    return [parse_json(line) for line in raw.splitlines() if line.strip()]


def run(recipe_path, output):
    recipe = parse_json(Path(recipe_path).read_bytes())
    required = {"schema_version", "mode", "inputs", "configuration", "schedule", "limits"}
    if set(recipe) != required or recipe["schema_version"] != 1 or recipe["mode"] not in {"fit", "predict"}:
        raise ValueError("Invalid native worker recipe")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "recipe.json", recipe)
    inputs = recipe["inputs"]
    names = {"corpus", "queries_fit", "fit_pairs"} if recipe["mode"] == "fit" else {"model_json", "model_arrays", "queries"}
    if set(inputs) != names:
        raise ValueError("Worker input names differ from purpose")
    if recipe["mode"] == "fit":
        actual_configuration = {"method_id": "scifact_sparse_linear_v1", "seed": SEED,
                                "learner_settings": LEARNER_SETTINGS, "vectorizer_settings": VECTORIZER_SETTINGS}
        if canonical(recipe["configuration"]) != canonical(actual_configuration):
            raise ValueError("Declared fitting configuration differs from implemented method")
    elif set(recipe["configuration"]) != {"k", "rationale_threshold"}:
        raise ValueError("Unsupported prediction configuration")
    roots = [sys.base_prefix, sys.prefix, Path(__file__).resolve().parent]
    if os.name == "nt":
        roots.append(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    audit = IOAudit([p["path"] for p in inputs.values()], output, roots)
    audit.activate()
    phase_seconds = recipe["limits"]["phase_seconds"]
    setup_id = "fit" if recipe["mode"] == "fit" else "setup"
    schedule = [setup_id] + ([] if recipe["mode"] == "fit" else [str(x) for x in recipe["schedule"]])
    with Watchdog(output, memory_limit=recipe["limits"]["memory_bytes"],
                  sample_seconds=0.5, call_seconds=phase_seconds) as watchdog:
        with NativeSession(output / "session", schedule, recipe["configuration"],
                           max_wall_seconds=phase_seconds) as session:
            current = setup_id
            start, cpu = time.perf_counter(), time.process_time()
            try:
                session.begin(current, {"mode": recipe["mode"], "inputs": inputs})
                watchdog.active_started = start
                raw = {key: load_input(proof) for key, proof in inputs.items()}
                input_bytes = sum(map(len, raw.values()))
                if recipe["mode"] == "fit":
                    corpus = {row["doc_id"]: row for row in rows(raw["corpus"])}
                    queries, pairs = rows(raw["queries_fit"]), rows(raw["fit_pairs"])
                    model = fit_model(corpus, queries, pairs)
                    save_model(model, output / "model")
                    files = [{"path": p.name, "bytes": p.stat().st_size,
                              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                             for p in sorted((output / "model").iterdir())]
                    result = {"kind": "fitted_native_model", "files": files, "metadata": model.metadata}
                    resources = measured(start, cpu, input_bytes=input_bytes,
                                         output_bytes=sum(x["bytes"] for x in files), examples=len(pairs))
                    session.finish(current, result, resources)
                else:
                    model_path = Path(inputs["model_json"]["path"])
                    if model_path.name != "model.json" or Path(inputs["model_arrays"]["path"]) != model_path.parent / "arrays.npz":
                        raise ValueError("Unexpected native model file layout")
                    model = load_model(model_path.parent)
                    queries = rows(raw["queries"])
                    if [row["id"] for row in queries] != recipe["schedule"]:
                        raise ValueError("Query schedule differs from frozen recipe")
                    session.finish(current, {"kind": "native_model_loaded", "queries": len(queries)},
                                   measured(start, cpu, input_bytes=input_bytes, output_bytes=0, examples=0))
                    watchdog.active_started = None
                    watchdog.call_seconds = recipe["limits"]["query_seconds"]
                    for query in queries:
                        current = str(query["id"])
                        start, cpu = time.perf_counter(), time.process_time()
                        session.begin(current, {"query": query, "configuration": recipe["configuration"]})
                        watchdog.active_started = start
                        result = model.predict(query, k=recipe["configuration"]["k"],
                                               rationale_threshold=recipe["configuration"]["rationale_threshold"])
                        payload = canonical(result)
                        session.finish(current, result, measured(start, cpu, input_bytes=len(canonical(query)),
                                       output_bytes=len(payload), examples=1))
                        watchdog.active_started = None
                watchdog.active_started = None
                receipt = session.finalize()
                audit.flush()
                write(output / "COMPLETE.json", {"status": "completed", "session_receipt_sha256": receipt["sha256"],
                                                "memory_sampling_seconds": watchdog.sample_seconds,
                                                "peak_sampled_working_set_bytes": watchdog.peak_sample,
                                                "memory_samples": watchdog.samples,
                                                "io_audit_scope": "managed_python_opens_trusted_worker_not_os_sandbox"})
            except BaseException as error:
                watchdog.active_started = None
                if session.active is not None:
                    try:
                        session.fail(current, error, measured(start, cpu, input_bytes=None, output_bytes=None, examples=None))
                    except BaseException:
                        pass  # Primary exception and durable native journal remain authoritative.
                write(output / "FAILED.json", {"status": "failed", "error_type": type(error).__name__,
                                               "message": str(error), "active_cell": current,
                                               "recovery": "inspect; no automatic repeat"})
                audit.flush()
                raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.recipe, args.output)
