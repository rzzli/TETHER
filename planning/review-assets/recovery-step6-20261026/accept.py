"""Accept R06 engineering only from retained fresh validation, never human proxies."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

import asof

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / "data/cache/recovery-step6-validation-20261026"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


full = read(CACHE / "full-validation.json")
code = read(CACHE / "code-validation.json")
installed = read(CACHE / "guarded-installed-verification.json")
coverage_path = ROOT / "data/cache/recovery-step6-coverage-20261026/coverage.json"
coverage = read(coverage_path)
assert asof.__version__ == importlib.metadata.version("asof-target-agents") == "0.3.0"
assert full["status"] == code["status"] == installed["status"] == coverage["status"] == "passed"
assert full["mode"] == "full" and full["tests"]["run"] >= 1435
assert full["tests"]["errors"] == full["tests"]["failures"] == 0 and not full["tests"]["skipped"]
assert full["required_probes_exit_code"] == 0 and full["packaging"]["dependency_free_demo"] == "passed"
assert "0.3.0" in full["packaging"]["wheel"]
assert code["unchanged_code"] and code["protected_unchanged"] and code["exit_code"] == 0
assert all(digest(ROOT / path) == expected for path, expected in code["source_pins"].items())
assert len(installed["results"]) == 7 and all(r["status"] == "passed" for r in installed["results"])
assert installed["isolated_mode"] and installed["installed_study_smoke"]["status"] == "recorded_smoke_passed"
assert installed["installed_study_smoke"]["native_model_calls"] == 0
for name in ("original_root_access_attempts", "archived_execution_attempts",
             "repository_tools_import_attempts", "network_or_child_attempts"):
    assert installed[name] == []
assert coverage["tests"] == 78 and coverage["skipped"] == coverage["errors"] == coverage["failures"] == 0
assert coverage["unchanged_study_sources"]
logs = ["data/cache/recovery-step6-full-validation-20261026.log",
        "data/cache/recovery-step6-installed-verification-20261026.log",
        "data/cache/recovery-step6-coverage-20261026.log",
        "data/cache/recovery-step6-format-20261026.log", "data/cache/recovery-step6-lint-20261026.log",
        "data/cache/recovery-step6-editable-environment-20261026.log",
        "data/cache/recovery-step6-editable-tests-20261026.log"]
assert all((ROOT / name).is_file() for name in logs)
raw = (ROOT / logs[-1]).read_bytes()
text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
assert "Ran 78 tests" in text and text.rstrip().endswith("OK")
prior = read(ROOT / "planning/review-assets/recovery-step4-20261026/code-validation.json")["source_pins"]
deltas = [path for path, expected in prior.items() if code["source_pins"].get(path) != expected]
assert set(deltas) == {"pyproject.toml", "uv.lock", "src/asof/__init__.py", "src/asof/archive/semantic_dependencies.json"}, deltas
for name in ("full-validation.json", "code-validation.json", "guarded-installed-verification.json"):
    with (HERE / name).open("xb") as stream:
        stream.write((CACHE / name).read_bytes())
with (HERE / "coverage.json").open("xb") as stream:
    stream.write(coverage_path.read_bytes())
covered = sum(row["covered_lines"] for row in coverage["files"])
total = sum(row["executable_lines"] for row in coverage["files"])
report = dict(schema_version=1, status="accepted_r06_engineering_only", date_utc="2026-10-26",
    version="0.3.0", full_validation=full, unchanged_code=code["unchanged_code"],
    source_pins=code["source_pins"], protected_hashes=code["protected_hashes"],
    changes_to_prior_r04_pins=deltas, installed_relocated_runs=7,
    installed_recorded_smoke="passed_success_and_failure", native_model_calls=0,
    provider_spending_usd=0, new_downloads=0, clinical_outcome_contents_read=False,
    downloader_or_monitor_changed=False, archived_receipts_rewritten=False,
    study_tests=78, line_coverage=dict(covered=covered, executable=total,
        percent=round(100 * covered / total, 2), method=coverage["coverage_method"]),
    reports={name: digest(HERE / name) for name in ("full-validation.json", "code-validation.json",
        "guarded-installed-verification.json", "coverage.json", "compatibility-profile-review.md")},
    logs={name: digest(ROOT / name) for name in logs},
    editable_environment=dict(module_version=asof.__version__, distribution_version=importlib.metadata.version("asof-target-agents"),
        offline_refresh=True, post_refresh_study_tests=78, failures=0, errors=0, skipped=0),
    next_gate="R07 held: owner confirmed human reviews pending; genetics/MR reference also needs relevant expertise",
    limitations=["No native diagnostic execution or ownership/GPU fit qualification",
        "No stronger model available; capacity unresolved", "No independent human scientific validation",
        "New study-format relocation not in legacy archive support matrix",
        "Hosted CI and off-machine durability remain release gates"], whole_project_complete=False)
with (HERE / "acceptance.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ("status", "version", "study_tests", "next_gate", "whole_project_complete")}, indent=2))
