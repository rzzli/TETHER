"""Accept R04 only from fresh full, unchanged-code and installed-archive reports."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / "data/cache/recovery-step4-validation-20261026"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(name):
    return json.loads((CACHE / name).read_text(encoding="utf-8"))


full = read("full-validation.json")
code = read("code-validation.json")
installed = read("guarded-installed-verification.json")
assert full["status"] == code["status"] == installed["status"] == "passed"
assert full["mode"] == "full" and full["tests"]["run"] > 1307
assert full["tests"]["failures"] == full["tests"]["errors"] == 0 and not full["tests"]["skipped"]
assert full["required_probes_exit_code"] == 0
assert full["packaging"]["dependency_free_demo"] == "passed"
assert code["unchanged_code"] and code["protected_unchanged"] and code["exit_code"] == 0
assert all(digest(ROOT / name) == expected for name, expected in code["source_pins"].items())
assert len(installed["results"]) == 7 and all(r["status"] == "passed" for r in installed["results"])
assert installed["isolated_mode"] and installed["receipt_bytes_rewritten"] is False
for key in ("original_root_access_attempts", "archived_execution_attempts",
            "repository_tools_import_attempts", "network_or_child_attempts"):
    assert installed[key] == []

profile = ROOT / "src/asof/archive/semantic_dependencies.json"
declarations = json.loads(profile.read_text(encoding="utf-8"))
assert declarations["executing_build_profile"] == "recovery-r04-20261026"
assert all(digest(profile.parent.parent / name) == expected
           for name, expected in declarations["modules"].items())
for name in ("full-validation.json", "code-validation.json", "guarded-installed-verification.json"):
    with (HERE / name).open("xb") as stream:
        stream.write((CACHE / name).read_bytes())
peer = ROOT / "data/cache/recovery-step4-final-peer-20261026/review.md"
with (HERE / "independent-peer-review.md").open("xb") as stream:
    stream.write(peer.read_bytes())

logs = [
    "data/cache/store-temporal-before-20261026.log",
    "data/cache/contracts-before-20261026.log",
    "data/cache/store-contracts-after-20261026.log",
    "data/cache/backend-hardening-20261026/before.txt",
    "data/cache/backend-hardening-20261026/after.txt",
    "data/cache/recovery-archive-design-20261026/atomic-portable-after.txt",
    "data/cache/recovery-step4-integrated-final-20261026.log",
    "data/cache/recovery-step4-full-validation-20261026.log",
    "data/cache/recovery-step4-installed-verification-20261026.log",
]
assert all((ROOT / name).is_file() for name in logs)
result = dict(
    schema_version=1, status="accepted_r04_engineering_only", step="R04", date_utc="2026-10-26",
    full_validation=full, unchanged_code=code["unchanged_code"], source_pins=code["source_pins"],
    protected_hashes=code["protected_hashes"], installed_relocated_runs=7,
    installed_elapsed_seconds=installed["elapsed_seconds"],
    installed_peak_working_set_bytes=installed["peak_working_set_bytes"],
    executing_dependency_profile=declarations["executing_build_profile"],
    executing_dependency_resource_sha256=digest(profile),
    reports={name: digest(HERE / name) for name in (
        "full-validation.json", "code-validation.json", "guarded-installed-verification.json",
        "independent-peer-review.md", "compatibility-profile-review.md")},
    logs={name: digest(ROOT / name) for name in logs},
    model_calls=0, provider_spending_usd=0, new_data_downloads=0, clinical_outcome_contents_read=False,
    downloader_or_monitor_changed=False, archived_receipts_rewritten=False,
    limitations=["Scientific validation and independent human references remain open",
        "Stronger-model capacity is unresolved", "Legacy v1 semantic verification is unavailable",
        "Historical code is hashed as data, not executed",
        "Successful native-question callback archive replay is unsupported",
        "Hosted cross-platform CI and off-machine durability remain release gates"],
    whole_project_complete=False,
)
with (HERE / "acceptance.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("status", "installed_relocated_runs", "whole_project_complete")}, indent=2))
