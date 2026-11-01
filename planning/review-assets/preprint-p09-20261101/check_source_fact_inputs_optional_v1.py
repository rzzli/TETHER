"""Check the optional Parquet boundary with absent, pinned and wrong Arrow."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Path(__file__).resolve().parent
PARQUET_TESTS = (
    "test_metadata_role_lineage_and_caps_fail_before_scan",
    "test_wrong_provider_type_and_frozen_scope_cutoff_fail_closed",
    "test_inventory_declaration_mismatch_and_unapproved_expanded_cap_precede_values",
    "test_unapproved_arbitrary_deadline_precedes_original_access",
    "test_progress_journal_and_callback_write_failure_stop_source_work",
    "test_fictional_preparation_source_only_and_slot_closure",
    "test_source_tamper_precedes_any_original_value_scan",
    "test_receipt_tamper_and_deadline",
)
REASON = "install the ingest extra for adapter tests"
PROBE = r'''
import importlib.util,json,sys,unittest
mode=sys.argv[1]
found=importlib.util.find_spec("pyarrow") is not None
version=None
if found:
    import pyarrow
    version=pyarrow.__version__
    if mode=="wrong-version": pyarrow.__version__="0.0.0"
suite=unittest.defaultTestLoader.loadTestsFromName("tests.test_study_source_fact_inputs")
result=unittest.TextTestRunner(verbosity=2).run(suite)
summary=dict(mode=mode,pyarrow_spec_found=found,installed_version=version,tests=result.testsRun,
    failures=len(result.failures),errors=len(result.errors),skipped=[dict(test=test.id(),reason=reason) for test,reason in result.skipped],
    error_details=[dict(test=test.id(),error=message.splitlines()[-1]) for test,message in result.errors])
print("P09_OPTIONAL_SUMMARY="+json.dumps(summary,sort_keys=True))
'''


def run(mode, executable, attempt):
    command = [str(executable), "-c", PROBE, mode]
    environment = dict(os.environ, TEMP=str(ROOT / "tmp"), TMP=str(ROOT / "tmp"), PYTHONPATH="")
    completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    log = ASSETS / ("SOURCE-FACT-INPUTS-OPTIONAL-" + mode + "-after-" + attempt + ".txt")
    payload = completed.stdout.encode()
    with log.open("xb") as stream:
        stream.write(payload)
    matched = re.search(r"^P09_OPTIONAL_SUMMARY=(.*)$", completed.stdout, re.M)
    summary = json.loads(matched[1]) if matched else {}
    expected_ids = {"tests.test_study_source_fact_inputs.InputTests." + name for name in PARQUET_TESTS}
    success = completed.returncode == 0 and summary.get("tests") == 12 and summary.get("failures") == 0
    if mode == "core-absent":
        success = success and summary.get("pyarrow_spec_found") is False and summary.get("errors") == 0 \
            and {item["test"] for item in summary.get("skipped", [])} == expected_ids \
            and all(item["reason"] == REASON for item in summary.get("skipped", []))
    elif mode == "arrow21":
        success = success and summary.get("installed_version") == "21.0.0" and summary.get("errors") == 0 and not summary.get("skipped")
    else:
        success = success and summary.get("installed_version") == "21.0.0" and summary.get("errors") == 8 and not summary.get("skipped") \
            and {item["test"] for item in summary.get("error_details", [])} == expected_ids \
            and all("Parquet fixture requires pinned pyarrow 21.0.0" in item["error"] for item in summary.get("error_details", []))
    return dict(summary, status="PASS" if success else "FAIL", interpreter=str(executable), log=log.name,
        log_sha256=hashlib.sha256(payload).hexdigest(), returncode=completed.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-python", type=Path, required=True)
    parser.add_argument("--full-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--attempt", default="v1")
    args = parser.parse_args()
    if re.fullmatch(r"v[1-9][0-9]*", args.attempt) is None:
        raise ValueError("Versioned evidence attempt required")
    jobs = (("core-absent", args.core_python), ("arrow21", args.full_python), ("wrong-version", args.full_python))
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = list(workers.map(lambda job: run(*job, args.attempt), jobs))
    report = dict(schema_version=1, method="p09.source_fact_inputs_optional_boundary.v1",
        status="PASS" if all(result["status"] == "PASS" for result in results) else "FAIL", results=results,
        test_sha256=hashlib.sha256((ROOT / "tests/test_study_source_fact_inputs.py").read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        optional_reason=REASON, parquet_methods=list(PARQUET_TESTS), pure_methods=4,
        package_installs=0, actual_source_reads=False, model_calls=0, network_calls=0, runtime_source_changes=False)
    path = ASSETS / ("SOURCE-FACT-INPUTS-OPTIONAL-after-" + args.attempt + ".json")
    with path.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
