"""Run only the32 fictional cell/controller tests in both discovery modes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Path(__file__).resolve().parent
SUBJECTS = ("tests/test_study_source_fact_cell.py", "tests/test_study_source_fact_controller.py")


def run_mode(mode, attempt):
    command = [sys.executable] + (["-S"] if mode == "core-package" else []) + ["-m", "unittest", "discover", "-s", "tests"]
    if mode in ("package", "core-package"):
        command += ["-t", "."]
    command += ["-p", "test_study_source_fact_c*.py", "-v"]
    environment = dict(os.environ, TEMP=str(ROOT / "tmp"), TMP=str(ROOT / "tmp"), PYTHONPATH=str(ROOT / "src"))
    completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    payload = completed.stdout.encode("utf-8")
    log = ASSETS / ("SOURCE-FACT-DISCOVERY-" + mode + "-after-" + attempt + ".txt")
    with log.open("xb") as stream:
        stream.write(payload)
    count = re.search(r"^Ran (\d+) tests? in ([0-9.]+)s$", completed.stdout, re.M)
    tests = int(count[1]) if count else None
    success = completed.returncode == 0 and tests == 32 and re.search(r"^OK$", completed.stdout, re.M) is not None
    return dict(mode=mode, command=command, returncode=completed.returncode, tests=tests,
        seconds=float(count[2]) if count else None, status="PASS" if success else "FAIL", log=log.name,
        log_sha256=hashlib.sha256(payload).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="v2")
    attempt = parser.parse_args().attempt
    if re.fullmatch(r"v[1-9][0-9]*", attempt) is None:
        raise ValueError("An explicit versioned evidence attempt is required")
    expected = sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "tests").glob("test_study_source_fact_c*.py"))
    if expected != list(SUBJECTS):
        raise RuntimeError("Focused discovery pattern changed")
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = list(workers.map(lambda mode: run_mode(mode, attempt), ("package", "top-level", "core-package")))
    report = dict(schema_version=1, method="p09.fictional_test_discovery_regression.v1",
        status="PASS" if all(result["status"] == "PASS" for result in results) else "FAIL",
        subjects={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SUBJECTS},
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), results=results,
        actual_source_reads=False, retained_production_packet_reads=False, model_calls=0, network_calls=0, runtime_source_changes=False,
        core_package_mode="-S removes site packages; source imports use only the explicit src PYTHONPATH")
    path = ASSETS / ("SOURCE-FACT-DISCOVERY-after-" + attempt + ".json")
    with path.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
