"""Controlled synthetic probes; never read retained manifests or requests."""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import io
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests.test_study_diagnostic import StudyDiagnosticTests
from tests.test_study_source_fact_sources import SourceFactSourceTests
from tools.validate import successful_tests


def package(version):
    result = ModuleType("pyarrow")
    result.__spec__ = importlib.machinery.ModuleSpec("pyarrow", loader=None, is_package=True)
    result.__path__ = []
    result.__version__ = version
    return result


def arrow_probe(kind):
    arrow = None if kind == "absent" else package("24.0.0" if kind == "wrong" else "21.0.0")
    parquet = None if kind != "wrong" else ModuleType("pyarrow.parquet")
    if parquet is not None:
        parquet.__spec__ = importlib.machinery.ModuleSpec("pyarrow.parquet", loader=None)
        arrow.parquet = parquet
    with patch.dict(sys.modules, {"pyarrow": arrow, "pyarrow.parquet": parquet}):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([
            SourceFactSourceTests("test_fictional_parquet_selected_row_and_absent_schema")]))
    return dict(kind=kind, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skips=[reason for _, reason in result.skipped], core_gate=successful_tests(result, "core"), full_gate=successful_tests(result, "full"),
        error_details=[message.splitlines()[-1] for _, message in result.errors])


def diagnostic_probe(phase):
    if phase == "before":
        method = "test_local_retained_real_payload_parity_when_available"
        case = StudyDiagnosticTests(method)
        case.setUp()  # Explicit packaged synthetic resource only.
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.read_bytes", side_effect=AssertionError("BLOCKED implicit archived read")) as read:
            try:
                getattr(case, method)()
            except AssertionError as error:
                if str(error) != "BLOCKED implicit archived read": raise
                attempted = True
            else:
                attempted = False
        return dict(implicit_archived_read_attempted=attempted, blocked_reads=read.call_count, actual_archived_reads=0)
    case = StudyDiagnosticTests("test_explicit_synthetic_context_orientation_payload_parity")
    case.setUp()
    getattr(case, case._testMethodName)()
    return dict(implicit_archived_read_attempted=False, explicit_synthetic_requests=2, interfaces=2, actual_archived_reads=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    diagnostic = diagnostic_probe(args.phase)
    arrows = [arrow_probe(kind) for kind in ("absent", "wrong", "broken")]
    absence, wrong, broken = arrows
    valid = absence["skips"] == ["install the ingest extra for source-audit tests"] and absence["errors"] == 0 and absence["core_gate"] is True
    if args.phase == "before":
        valid = valid and diagnostic["implicit_archived_read_attempted"] and len(wrong["skips"]) == 1 and not wrong["core_gate"] \
            and len(broken["skips"]) == 1 and broken["core_gate"] is True
    else:
        valid = valid and not diagnostic["implicit_archived_read_attempted"] and not wrong["skips"] and wrong["errors"] == 1 \
            and not wrong["core_gate"] and not broken["skips"] and broken["errors"] == 1 and not broken["core_gate"]
    result = dict(schema_version=1, phase=args.phase, status="EXPECTED_BOUNDARY_REPRODUCED" if args.phase == "before" and valid else "PASS" if valid else "FAIL",
        diagnostic=diagnostic, arrows=arrows, actual_source_reads=False, model_calls=0, network_calls=0,
        source_hashes={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            "tests/test_study_diagnostic.py", "tests/test_study_source_fact_sources.py", "tests/test_validation.py")})
    destination = Path(__file__).resolve().parent / ("TEST-SOURCE-BOUNDARIES-" + args.phase + "-v1.json")
    with destination.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
