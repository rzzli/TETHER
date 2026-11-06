"""Invoke the frozen post-seal evaluator once and retain outer elapsed time.

No inference or retrieval is performed. This wrapper is outside the frozen
experiment modules and changes no scoring or source policy.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.labbench.score_run import score_run
from asof.serde import encode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-sha", required=True)
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    # Reserve an external controller record before any evaluator work. A new
    # attempt needs a different filename/output; this wrapper does not resume.
    record = Path(args.record)
    with record.open("x", encoding="utf-8") as stream:
        started, cpu = time.monotonic(), time.process_time()
        result = {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "generation_sealed_sha256": args.generation_sha,
            "new_model_calls": 0,
            "new_retrieval_calls": 0,
        }
        try:
            report = score_run(
                ROOT / "data/benchmark/labbench/generation-20261106T011303Z-attempt01",
                args.generation_sha,
                ROOT / "data/benchmark/labbench/preparation-20261106-attempt02",
                "7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b",
                ROOT / "data/benchmark/labbench/evaluation-20261106T011303Z-attempt01",
                deadline_seconds=3600,
            )
            result.update(status=report["status"], scheduled_count=report["scheduled_count"],
                          raw_metrics=encode(report["raw_metrics"]),
                          checked_metrics=encode(report["checked_metrics"]))
        except BaseException as error:
            result.update(status="failed", error_class=type(error).__name__, message=str(error))
            raise
        finally:
            result.update(elapsed_seconds=time.monotonic()-started,
                          controller_cpu_seconds=time.process_time()-cpu,
                          closed_at_utc=datetime.now(timezone.utc).isoformat())
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
        print(json.dumps(result))


if __name__ == "__main__":
    main()
