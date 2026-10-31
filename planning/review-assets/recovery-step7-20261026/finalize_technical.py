"""Retain R07 technical evidence; never dispatch or interpret a scientific gate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha(path), "bytes": path.stat().st_size}


def retain(source, destination):
    data = source.read_bytes()
    if destination.exists():
        assert destination.read_bytes() == data, f"Refuse overwrite: {destination}"
    else:
        destination.write_bytes(data)
    return pin(destination)


cache = ROOT / "data/cache/recovery-step7-validation-20261026"
full = json.loads((cache / "full-validation.json").read_bytes())
code = json.loads((cache / "code-validation.json").read_bytes())
installed = json.loads((cache / "guarded-installed-verification.json").read_bytes())
assert full["status"] == code["status"] == installed["status"] == "passed"
assert full["tests"] == {"run": 1485, "failures": 0, "errors": 0, "skipped": []}
assert full["required_probes_exit_code"] == 0
assert len(installed["results"]) == 7
assert all(item["status"] == "passed" for item in installed["results"])
for name, expected in code["source_pins"].items():
    assert sha(ROOT / name) == expected, f"Changed frozen source: {name}"
for name, expected in code["protected_hashes"].items():
    # Hash only: never parse or expose protected outcome values.
    assert sha(ROOT / name) == expected, f"Changed protected file: {name}"
pre = json.loads((HERE / "pre-dispatch-acceptance.json").read_bytes())
assert sha(cache / "full-validation.json") == pre["full_report_sha256"]
assert sha(cache / "code-validation.json") == pre["code_report_sha256"]
assert sha(cache / "guarded-installed-verification.json") == pre["installed_guard_report_sha256"]
run = ROOT / "runs/r07-native-diagnostic-20261026T165505Z"
assert sha(run / "terminal-seal.json") == "863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41"
mechanical = json.loads((HERE / "post-run-mechanical-audit.json").read_bytes())
assert mechanical["complete_http_responses"] == 6
assert mechanical["output_contracts_accepted"] == 0

reports = [retain(cache / old, HERE / new) for old, new in (
    ("full-validation.json", "full-validation.json"),
    ("code-validation.json", "code-validation.json"),
    ("guarded-installed-verification.json", "installed-verification.json"))]
reports.append(retain(ROOT / "data/cache/r07-native-terminal-verification-20261026.log",
                      HERE / "terminal-verification.json"))
for relative in ("pre-dispatch-audit.json", "post-run-mechanical-audit.json",
                 "DISPOSITION.md", "completion-audit.md", "ai-triage/interface-review.md",
                 "ai-triage/interface-findings.json", "ai-triage/source-review.md",
                 "addendum-review/final-interface-acceptance.json"):
    reports.append(pin(HERE / relative))
result = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "technical_experiment_closed_negative_scientific_assessment_pending",
    "runtime_version": "0.3.1",
    "full_tests": full["tests"],
    "frozen_source_pins_rechecked": len(code["source_pins"]),
    "protected_files_hash_checked_only": len(code["protected_hashes"]),
    "installed_legacy_families": 7,
    "recorded_success_failure_smoke": "passed",
    "plan": pin(run / "run-plan.json"),
    "terminal_seal": pin(run / "terminal-seal.json"),
    "planned_cells": 6,
    "complete_http_responses": 6,
    "output_contracts_accepted": 0,
    "measured_input_tokens": 14420,
    "measured_output_tokens": 2108,
    "retries": 0,
    "provider_spending_usd": 0,
    "human_scientific_assessment": "pending",
    "independent_scientific_validation": "not_established",
    "aggregate_r07_complete": False,
    "native_expansion": "stopped",
    "r08_independent_preparation": "permitted_under_own_dependencies",
    "evidence": reports,
}
destination = HERE / "technical-closeout.json"
assert not destination.exists(), "Retain prior closeout; do not overwrite it"
destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "evidence_files": len(reports),
                  "source_pins": len(code["source_pins"]), "closeout": pin(destination)}))
