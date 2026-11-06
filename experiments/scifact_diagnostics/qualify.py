"""Run invented tests and retain a fresh fictional manifest/output for review."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(Path(__file__).resolve().parent / "tests")]
from experiments.scifact_diagnostics.analyze import run_manifest
from test_decomposition import fictional_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "temp"
    temporary.mkdir()
    os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
    tempfile.tempdir = str(temporary)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "experiments/scifact_diagnostics/tests"))
    stream = io.StringIO()
    outcome = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (output / "TEST-RESULTS.txt").write_bytes(stream.getvalue().replace("\r\n", "\n").encode("utf-8"))
    fixture = output / "fictional-inputs"
    fixture.mkdir()
    manifest, digest, value = fictional_manifest(fixture)
    if outcome.wasSuccessful():
        run_manifest(manifest, digest, output / "fictional-analysis")
    files = [ROOT / "experiments/scifact_diagnostics/qualify.py",
             ROOT / "experiments/scifact_diagnostics/tests/test_decomposition.py"]
    report = {"schema_version": 1, "status": "PASS" if outcome.wasSuccessful() else "FAIL",
              "tests_run": outcome.testsRun, "failures": len(outcome.failures), "errors": len(outcome.errors),
              "scope": "Invented fixtures only; no actual development data analysis, inference, tuning or acquisition.",
              "tests_written_and_first_run_before_implementation": "See qualification-red01/TEST-FIRST.json",
              "isolated_mode": sys.flags.isolated == 1, "bytecode_writes_disabled": sys.dont_write_bytecode,
              "pycache_prefix": sys.pycache_prefix, "temp": tempfile.gettempdir(),
              "interpreter": sys.executable,
              "source_pins": value["source_pins"] + [{"path": str(p), "bytes": p.stat().st_size,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (output / "QUALIFICATION.json").write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "tests_run": report["tests_run"], "output": str(output)}))
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
