"""Retain a fresh fictional qualification with before/after source identities."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(raw): return hashlib.sha256(raw).hexdigest()


def main(output):
    root = Path(__file__).resolve().parent
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = output / "sources"; sources.mkdir()
    names = ["reconstruct.py", "test_reconstruct.py", "qualify.py"]
    before = {}
    for name in names:
        raw = (root / name).read_bytes(); (sources / name).write_bytes(raw)
        before[name] = {"sha256": digest(raw), "bytes": len(raw)}
    environment = dict(os.environ)
    temp = root.parents[3] / "data/cache/scifact-scoring-test-temp"
    temp.mkdir(parents=True, exist_ok=True)
    environment.update(TEMP=str(temp), TMP=str(temp))
    command = [sys.executable, "-B", str(root / "test_reconstruct.py")]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment, timeout=120)
    (output / "tests.log").write_bytes(result.stdout)
    after = {name: {"sha256": digest((root / name).read_bytes()), "bytes": (root / name).stat().st_size} for name in names}
    record = {"schema_version": 1, "status": "PASS" if result.returncode == 0 and before == after else "FAIL",
              "scope": "fictional_helper_qualification_only_no_actual_SciFact_predictions_or_reference_records",
              "command": command, "returncode": result.returncode, "sources_before": before, "sources_after": after,
              "test_log_sha256": digest(result.stdout), "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    (output / "QUALIFICATION.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "output": str(output), "returncode": result.returncode}))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); raise SystemExit(main(args.output))
