"""Fictional pre-execution probes only; no real model fit, inference or references."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from asof.serde import canonical
from tether._process import EngineResult
from experiments.scifact.run import Stage, DEFAULT_LIMITS, file_proof, write
from experiments.scifact.tether_adapter import NativeSession


def resources():
    return dict(wall_seconds=.001, cpu_seconds=.001, peak_memory_bytes=None,
                memory_method="fictional_unavailable", input_bytes=1, output_bytes=1,
                examples=1, model_input_tokens=None, model_output_tokens=None,
                tokenizer_identity=None, provider_usage=None,
                token_usage_reason="not_applicable_non_llm", provider_cost_usd=0)


def main():
    before = file_proof(ROOT / "experiments/scifact/run.py")
    results = {"scope": "fictional controller boundary probes; no actual fit or evaluation", "source_before": before}
    with tempfile.TemporaryDirectory(dir=ROOT / "data/cache/scifact-policy-test-temp") as directory:
        root = Path(directory)
        stage = Stage(root / "unused", "0" * 64, root / "clock-stage", sys.executable,
                      root / "unused-evaluator", root / "unused-environment",
                      limits=DEFAULT_LIMITS | {"stage_seconds": 10})
        stage.runtime = {"fixture": "stable"}
        stage.started = 0
        clock = [0]
        def capture(_):
            clock[0] = 20
            return stage.runtime
        try:
            with patch("experiments.scifact.run.time.perf_counter", side_effect=lambda: clock[0]), \
                 patch("experiments.scifact.run.capture_runtime", side_effect=capture):
                try:
                    returned = stage.boundary()
                    results["expired_during_source_bracket"] = {"rejected": False, "returned_remaining": returned, "elapsed": clock[0]}
                except Exception as error:
                    results["expired_during_source_bracket"] = {"rejected": True, "error": type(error).__name__, "message": str(error)}
        finally:
            stage.journal.close()

        stage = Stage(root / "unused", "0" * 64, root / "request-stage", sys.executable,
                      root / "unused-evaluator", root / "unused-environment")
        source = root / "query-input"
        source.write_bytes(b"fictional-query-only")
        submitted = stage.recipe("predict", {"queries": file_proof(source)}, {"k": 5, "rationale_threshold": .25}, [1])
        def launch(command, *, limits):
            output = Path(command[command.index("--output") + 1])
            output.mkdir(parents=True)
            with NativeSession(output / "session", ["setup", "1"], {"k": 20, "rationale_threshold": .75}) as session:
                session.begin("setup", {"mode": "different", "inputs": {}})
                session.finish("setup", {"kind": "fictional"}, resources())
                session.begin("1", {"query": {"id": 999, "claim": "Contradictory declared query"}, "configuration": {"k": 20, "rationale_threshold": .75}})
                session.finish("1", {"prediction": {"id": 1, "evidence": {}}}, resources())
                receipt = session.finalize()
            write(output / "COMPLETE.json", {"status": "completed", "session_receipt_sha256": receipt["sha256"]})
            (output / "io-audit.jsonl").write_bytes(canonical({"path": str(source), "allowed": True}) + b"\n")
            report = {"schema_version": 1, "method": "tether.process_envelope.v1", "limits": limits.payload(),
                      "termination_reason": "exited", "execution_elapsed_seconds": .01, "total_elapsed_seconds": .02,
                      "retained_stdout_bytes": 0, "retained_stderr_bytes": 0, "observed_stdout_bytes": 0, "observed_stderr_bytes": 0,
                      "observed_counts_are_lower_bounds": False, "pipe_eof": {"stdout": True, "stderr": True},
                      "process_started": True, "process_reaped": True, "cleanup_errors": []}
            return EngineResult(0, b"", b"", report)
        stage.launcher = launch
        try:
            try:
                _, records = stage.dispatch("fictional", submitted)
                results["contradictory_worker_recipe"] = {"rejected": False, "retained_cell": records["1"]}
            except Exception as error:
                results["contradictory_worker_recipe"] = {"rejected": True, "error": type(error).__name__, "message": str(error)}
        finally:
            stage.journal.close()
    results["source_after"] = file_proof(ROOT / "experiments/scifact/run.py")
    results["source_stable"] = results["source_before"] == results["source_after"]
    print(canonical(results).decode())


if __name__ == "__main__":
    main()
