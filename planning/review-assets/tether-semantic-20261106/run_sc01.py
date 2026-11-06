"""One bounded, no-retry launch of the frozen descriptive analysis."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "planning/review-assets/tether-semantic-20261106"
MANIFEST = ASSETS / "decomposition/actual-freeze-attempt01/INPUT-MANIFEST.json"
DIGEST = "f465f1579dd6f71d82d261c0a1230acfc258935c557025f0f0197fe670659203"


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != DIGEST:
        raise ValueError("Frozen manifest mismatch")
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    execution = ASSETS / "decomposition/actual-execution-attempt01"
    execution.mkdir(exist_ok=False)
    temp = execution / "temp"
    temp.mkdir()
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp))
    command = [frozen["execution"]["interpreter"]["path"], "-I", "-B", "-X",
               f"pycache_prefix={execution / 'fresh-pycache'}",
               str(ROOT / "experiments/scifact_diagnostics/analyze.py"), "--manifest", str(MANIFEST),
               "--manifest-sha256", DIGEST, "--output", frozen["execution"]["analysis_output"]]
    write(execution / "COMMAND.json", {"argv": command, "cwd": str(ROOT), "timeout_seconds": 120,
          "manifest_sha256": DIGEST, "started_at_utc": datetime.now(timezone.utc).isoformat(),
          "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "scope": "One diagnostic analysis; no model dispatch or retry."})
    started = time.perf_counter()
    report = {"status": "FAIL", "provider_spend_usd": 0}
    with (execution / "stdout.txt").open("xb") as stdout, (execution / "stderr.txt").open("xb") as stderr:
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=120)
            report.update(returncode=result.returncode, status="PASS" if result.returncode == 0 else "FAIL")
        except BaseException as exc:
            report.update(error_type=type(exc).__name__, error=str(exc))
        finally:
            report.update(elapsed_seconds=time.perf_counter() - started,
                          completed_at_utc=datetime.now(timezone.utc).isoformat())
            write(execution / "RUN.json", report)
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
