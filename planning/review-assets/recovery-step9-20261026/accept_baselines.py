"""Accept the finite baseline engineering slice, not the whole R09 milestone."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / "data/cache/recovery-step9-validation-20261026"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return dict(path=str(path.relative_to(ROOT)).replace("\\", "/"), sha256=sha(path), bytes=path.stat().st_size)


def retain(path, name):
    output = HERE / name
    assert not output.exists() or output.read_bytes() == path.read_bytes()
    output.write_bytes(path.read_bytes())
    return output


full = json.loads((CACHE / "full-validation.json").read_bytes())
code = json.loads((CACHE / "code-validation.json").read_bytes())
assert full["status"] == code["status"] == "passed" and code["unchanged_code"]
assert full["tests"] == dict(run=1519, failures=0, errors=0, skipped=[])
assert full["required_probes_exit_code"] == 0 and code["protected_unchanged"]
for name, expected in code["source_pins"].items():
    assert sha(ROOT / name) == expected, name
for name, expected in code["protected_hashes"].items():
    # Protected outcomes are hashed only, never loaded as JSON.
    assert sha(ROOT / name) == expected, name
installed_path = ROOT / "data/cache/recovery-step9-installed-20261026-v2/guarded-installed-verification.json"
installed = json.loads(installed_path.read_bytes())
assert installed["status"] == "passed" and len(installed["results"]) == 7
assert all(item["status"] == "passed" for item in installed["results"])
for key in ("original_root_access_attempts", "archived_execution_attempts", "repository_tools_import_attempts", "network_or_child_attempts"):
    assert installed[key] == [], key
assert installed["installed_baseline_smoke"]["synthetic_cells"] == 4
assert installed["installed_baseline_smoke"]["model_calls"] == 0
frozen_path = HERE / "frozen-r07-verification-after.json"
frozen = json.loads(frozen_path.read_bytes())
assert frozen["status"] == "passed_frozen_installed_verifier_without_live_source"
assert not any(frozen["guards"].values())
relocation_path = HERE / "baseline-relocation-verification.json"
assert json.loads(relocation_path.read_bytes())["status"] == "passed_synthetic_bundle_relocation"

wheel = ROOT / "data/cache/recovery-step9-wheel-20261026/dist/asof_target_agents-0.3.2-py3-none-any.whl"
with ZipFile(wheel) as archive:
    names = {name for name in archive.namelist() if name.startswith("asof/") and name.endswith((".py", ".json"))}
    source_names = {path.relative_to(ROOT / "src").as_posix() for path in (ROOT / "src/asof").rglob("*")
                    if path.is_file() and path.suffix in (".py", ".json") and "__pycache__" not in path.parts}
    assert names == source_names
    for name in names:
        assert archive.read(name) == (ROOT / "src" / name).read_bytes(), name

preserved = ROOT / "data/reference/recovery-r09-verifier-032-20261026"
preserved.mkdir(parents=True, exist_ok=False)
for path in (wheel, ROOT / "src/asof/archive/semantic_dependencies.json", ROOT / "src/asof/__init__.py"):
    (preserved / path.name).write_bytes(path.read_bytes())
reports = [retain(CACHE / "full-validation.json", "full-validation.json"),
           retain(CACHE / "code-validation.json", "code-validation.json"),
           retain(installed_path, "installed-verification.json"),
           frozen_path, relocation_path, HERE / "independent-peer-review.json", HERE / "ENGINEERING-SCOPE.md",
           HERE / "frozen-verifier-preservation.json", HERE / "compatibility-profile-review.md"]
result = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
              status="accepted_r09_deterministic_engineering_slice_only", version="0.3.2",
              full_tests=full["tests"], source_pins_rechecked=len(code["source_pins"]), protected_hashes_only=2,
              scoped_tests=34, installed_legacy_families=7, installed_synthetic_baseline_results=4,
              baseline_receipt_sha256=installed["installed_baseline_smoke"]["receipt_sha256"],
              baseline_relocation="verified_original_bundle_and_live_source_unavailable",
              r07_verification="verified_by_explicit_reviewed_frozen_0.3.1_installation",
              native_R07_relocation="not_claimed", new_native_calls=0, provider_spending_usd=0,
              real_case_admission=False, scientific_validation="not_established", entire_R09_complete=False,
              remaining=["Generated interpretation and honestly adapted comparator contract",
                         "Qualified real-source admission and complete paired budget preflight",
                         "Separate end-to-end retrieval comparison", "Fresh sources/cases and independent human references"],
              wheel=pin(wheel), preserved_wheel=pin(preserved / wheel.name),
              evidence=[pin(path) for path in reports])
output = HERE / "acceptance.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "full_tests": 1519, "source_pins": len(code["source_pins"]), "acceptance_sha256": sha(output)}))
