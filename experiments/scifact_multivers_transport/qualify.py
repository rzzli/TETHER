"""Retain invented transport tests and a read-only manifest/lock correspondence."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent / "tests")]
from experiments.scifact_multivers_transport import download
from test_download import AcquisitionTests, asset


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "temp"
    temporary.mkdir()
    os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
    tempfile.tempdir = str(temporary)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "experiments/scifact_multivers_transport/tests"))
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (output / "TEST-RESULTS.txt").write_bytes(log.getvalue().replace("\r\n", "\n").encode("utf-8"))
    review_root = ROOT / "planning/review-assets/tether-semantic-20261106/solver-feasibility"
    manifest_path = review_root / "acquisition-manifest.json"
    lock_path = review_root / "dependency-lock.json"
    requirements_path = review_root / "requirements.lock.txt"
    manifest = download.validate_manifest(download.strict_json(manifest_path.read_bytes()))
    lock = download.strict_json(lock_path.read_bytes())
    packages = {p["filename"]: p for p in lock["packages"]}
    wheels = {a["logical_id"]: a for a in manifest["assets"] if a["kind"] == "wheel"}
    download.need(set(packages) == set(wheels), "Wheel/dependency-lock identity mismatch")
    for name, row in wheels.items():
        p = packages[name]
        download.need(row["url"] == p["url"] and row["expected_bytes"] == p["bytes"] and row["expected_sha256"] == p["sha256"], "Wheel/dependency-lock pin mismatch")
    requirement_rows = [line for line in requirements_path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    expected = {p["name"].replace("_", "-").lower() + "==" + p["version"] + " --hash=sha256:" + p["sha256"] for p in packages.values()}
    actual = {line.split("==", 1)[0].replace("_", "-").lower() + "==" + line.split("==", 1)[1] for line in requirement_rows}
    download.need(actual == expected and len(requirement_rows) == len(expected), "Requirements/dependency-lock mismatch")
    fixture = output / "fictional-retained"
    fixture.mkdir()
    if result.wasSuccessful():
        AcquisitionTests().run_fake(fixture, [asset(), asset("checkpoint"), asset("tokenizer_config")])
    paths = [Path(download.__file__), Path(__file__), ROOT / "experiments/scifact_multivers_transport/tests/test_download.py",
             manifest_path, lock_path, requirements_path]
    report = {"schema_version": 1, "status": "PASS" if result.wasSuccessful() else "FAIL", "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "actual_network_requests": 0,
              "qualification_scope": "Invented streams; tiny local watchdog child processes; read-only actual manifest/lock validation. No payload download, install or model load.",
              "actual_manifest_assets": len(manifest["assets"]), "actual_manifest_payload_bytes": manifest["total_payload_bytes"],
              "actual_manifest_wheels": len(wheels), "manifest_lock_requirements_agree": True,
              "isolated_mode": sys.flags.isolated == 1, "bytecode_writes_disabled": sys.dont_write_bytecode,
              "pycache_prefix": sys.pycache_prefix, "temp": tempfile.gettempdir(), "interpreter": sys.executable,
              "pins": [pin(p) for p in paths]}
    download.write_new(output / "QUALIFICATION.json", report)
    print(json.dumps({"status": report["status"], "tests_run": result.testsRun, "assets": report["actual_manifest_assets"], "network_requests": 0}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
