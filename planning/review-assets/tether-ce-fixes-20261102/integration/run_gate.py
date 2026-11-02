"""Run the complete gate with source pins, fresh logs and ordinary fail-fast reports.

A successful run still executes every discovered test. Failed runs stop at their
first test failure, letting the driver publish its terminal report and bracket.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(path, value):
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def source_inventory():
    paths = set()
    for directory in (ROOT / "src/asof", ROOT / "packages/tether/src/tether", ROOT / "tests",
                      ROOT / "packages/tether/tests", ROOT / "tools"):
        paths.update(p for p in directory.rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix in {".py", ".ps1", ".json"})
    paths.update(ROOT / name for name in ("pyproject.toml", "uv.lock", "packages/tether/pyproject.toml",
                 "packages/tether/uv.lock", "paper/release/build-constraints.txt", "data/catalog/sources.json",
                 "data/catalog/policy-v2.json"))
    paths.add(Path(__file__).resolve())
    return {path.relative_to(ROOT).as_posix(): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stem", type=Path, required=True)
    args = parser.parse_args()
    stem = args.stem.resolve()
    if not stem.is_relative_to(ROOT / "planning/review-assets"):
        parser.error("Use a fresh stem under planning/review-assets")
    names = {key: Path(str(stem) + suffix) for key, suffix in {
        "log": ".log", "report": ".json", "before": ".source-before.json",
        "started": ".started.json", "bracket": ".source-bracket.json"}.items()}
    if any(path.exists() or path.is_symlink() for path in names.values()):
        parser.error("All gate destinations must be fresh")
    stem.parent.mkdir(parents=True, exist_ok=True)
    before = source_inventory()
    publish(names["before"], {"schema_version": 1, "sources": before})
    environment = dict(os.environ)
    temporary = ROOT / "data/cache" / (stem.name + "-temp")
    temporary.mkdir(exist_ok=False)
    environment.update(TMP=str(temporary), TEMP=str(temporary), PYTHONDONTWRITEBYTECODE="1")
    argv = [sys.executable, "-B", str(ROOT / "tools/validate.py"), "--mode", "full", "--package",
            "--failfast", "--report", str(names["report"])]
    record = {"schema_version": 1, "status": "started", "argv": argv, "cwd": str(ROOT),
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "before_path": str(names["before"]), "before_sha256": digest(names["before"])}
    process = None
    try:
        with names["log"].open("xb") as stream:
            process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT)
            record["pid"] = process.pid
            publish(names["started"], record)
            try:
                record["exit_code"] = process.wait(timeout=5400)
            except subprocess.TimeoutExpired:
                process.kill()
                record["exit_code"] = process.wait()
                raise RuntimeError("Full gate exceeded its 90-minute bound; owned process terminated")
        after = source_inventory()
        changed = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
        gate = json.loads(names["report"].read_bytes()) if names["report"].exists() else None
        record.update(after_sources=after, changed_sources=changed, log_path=str(names["log"]),
                      log_sha256=digest(names["log"]), report_path=str(names["report"]),
                      report_sha256=digest(names["report"]) if gate is not None else None)
        record["status"] = "PASS" if record["exit_code"] == 0 and not changed and gate and gate.get("status") == "passed" else "FAILED"
    except BaseException as error:
        record.update(status="FAILED", error={"type": type(error).__name__, "message": str(error),
                                               "traceback": traceback.format_exc()})
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            record["owned_process_cleanup"] = {"pid": process.pid, "exit_code": process.returncode,
                                               "descendant_tree_guarantee": False}
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    publish(names["bracket"], record)
    print(json.dumps({"status": record["status"], "record": str(names["bracket"]),
                      "exit_code": record.get("exit_code"), "error": record.get("error")}, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
