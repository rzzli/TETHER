"""Produce old-engine fictional policy seals, then verify with the corrected code.

Run create using the retained 0.5.0/0.3.11 environment. Run verify using the new
version. This exercises policy bindings only, not engine execution or scientific
validation. Every source and receipt is generated fiction for this check.
"""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

import asof.provenance as provenance
from tether import _catalog_binding as binding, _catalog_policy, _presentation, _cli

ROOT = Path(__file__).resolve().parents[4]


def write_new(path, document):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)
        stream.write("\n")


def versions():
    return dict(tether=importlib.metadata.version("tether-target-agents"),
                engine=importlib.metadata.version("asof-target-agents"),
                binding_path=binding.__file__, provenance_path=provenance.__file__,
                binding_sha256=hashlib.sha256(Path(binding.__file__).read_bytes()).hexdigest(),
                provenance_sha256=hashlib.sha256(Path(provenance.__file__).read_bytes()).hexdigest())


mode, base, destination = sys.argv[1], Path(sys.argv[2]).absolute(), Path(sys.argv[3]).absolute()
destination.mkdir(parents=True, exist_ok=False)
if mode == "create":
    assert versions()["tether"] == "0.5.0" and versions()["engine"] == "0.3.11"
    # Preloaded package modules above stay bound to the old installed wheels;
    # only the neutral fictional fixture construction comes from the checkout.
    path = ROOT / "packages/tether/tests/test_ce03_receipt_time.py"
    spec = importlib.util.spec_from_file_location("ce03_archive_helpers", path)
    helpers = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helpers
    original_search_path = list(sys.path)
    try:
        spec.loader.exec_module(helpers)
    finally:
        # Test helper discovery inserts checkout paths; don't let those shadow
        # the installed distribution metadata recorded for the old producer.
        sys.path[:] = original_search_path
    assert versions()["tether"] == "0.5.0" and versions()["engine"] == "0.3.11"
    base.mkdir(parents=True, exist_ok=False)
    cases = []
    for name, kwargs, expected in (
            ("unused-valid", {}, "accepted"),
            ("unused-contradictory", dict(completed="2024-01-01T00:00:00+00:00"), "rejected"),
            ("used-alternative-basis", dict(used=True, completed="2024-01-01T00:00:00+00:00", known=None,
                basis="Fictional separately retained release dates", evidence_ref="fictional-release-proof"), "accepted")):
        folder = base / name
        folder.mkdir()
        fixture = helpers.make_fixture(folder)
        helpers.add_raw(fixture, **kwargs)
        output = folder / "outer"
        output.mkdir()
        descriptor = binding.prepare_policy_run(output, fixture["request"])
        verified = binding.verify_policy_run(output, descriptor, check_engine=False)
        cases.append(dict(name=name, output=str(output), descriptor=descriptor, old_result=verified,
                          expected_corrected_result=expected))
    record = dict(scope="Fictional old policy seals; no engine dispatch", versions=versions(), cases=cases)
    write_new(base / "archives.json", record)
    write_new(destination / "results.json", record)
elif mode == "verify":
    prior = json.loads((base / "archives.json").read_bytes())
    results = []
    for case in prior["cases"]:
        try:
            proof = binding.verify_policy_run(Path(case["output"]), case["descriptor"], check_engine=False)
            result = dict(actual="accepted", verification=proof)
        except Exception as error:
            result = dict(actual="rejected", exception=type(error).__name__, message=str(error))
        result.update(name=case["name"], expected=case["expected_corrected_result"])
        result["passed"] = result["actual"] == result["expected"]
        if result["expected"] == "rejected":
            result["passed"] = result["passed"] and "availability bound" in result.get("message", "")
        results.append(result)
    record = dict(scope=prior["scope"], producer_versions=prior["versions"], verifier_versions=versions(),
                  results=results, passed=all(row["passed"] for row in results),
                  archives_sha256=hashlib.sha256((base / "archives.json").read_bytes()).hexdigest())
    write_new(destination / "results.json", record)
    if not record["passed"]:
        print(json.dumps(record, indent=2))
        raise SystemExit(1)
else:
    raise ValueError("Expected create or verify")
print(json.dumps(record, indent=2))
