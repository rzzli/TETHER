"""Accept recorded engineering with explicit real-source and science limitations."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / "data/cache/recovery-step9-comparison-validation-20261026"


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
assert full["tests"] == dict(run=1536, failures=0, errors=0, skipped=[])
assert full["required_probes_exit_code"] == 0 and code["protected_unchanged"]
for name, expected in code["source_pins"].items():
    assert sha(ROOT / name) == expected, name
for name, expected in code["protected_hashes"].items():
    # Hash only. Never parse protected outcome JSON.
    assert sha(ROOT / name) == expected, name
installed_path = ROOT / "data/cache/r09c-installed-20261026/guarded-installed-verification.json"
installed = json.loads(installed_path.read_bytes())
assert installed["status"] == "passed" and len(installed["results"]) == 7
assert all(item["status"] == "passed" for item in installed["results"])
for key in ("original_root_access_attempts", "archived_execution_attempts", "repository_tools_import_attempts", "network_or_child_attempts"):
    assert installed[key] == [], key
comparison = installed["installed_comparison_smoke"]
assert comparison["recorded_adapter_cells"] == 12 and comparison["pure_baseline_results"] == 4
assert comparison["actual_model_calls"] == 0 and comparison["scientific_validation"] == "not_attempted"
for name, status in (("frozen-r07-verification-after.json", "passed_frozen_installed_verifier_without_live_source"),
                     ("frozen-baseline-verification-after.json", "passed_synthetic_bundle_relocation"),
                     ("relocation-verification.json", "passed_recorded_comparison_relocation")):
    data = json.loads((HERE / name).read_bytes())
    assert data["status"] == status and not any(data["guards"].values())

wheel = ROOT / "data/cache/recovery-step9-comparison-wheel-20261026/dist/asof_target_agents-0.3.3-py3-none-any.whl"
with ZipFile(wheel) as archive:
    members = {name for name in archive.namelist() if name.startswith("asof/") and name.endswith((".py", ".json"))}
    source_members = {path.relative_to(ROOT / "src").as_posix() for path in (ROOT / "src/asof").rglob("*")
                      if path.is_file() and path.suffix in (".py", ".json") and "__pycache__" not in path.parts}
    assert members == source_members
    for name in members:
        assert archive.read(name) == (ROOT / "src" / name).read_bytes(), name
preserved = ROOT / "data/reference/recovery-r09-comparison-verifier-033-20261026"
preserved.mkdir(parents=True, exist_ok=False)
for path in (wheel, ROOT / "src/asof/archive/semantic_dependencies.json", ROOT / "src/asof/__init__.py"):
    (preserved / path.name).write_bytes(path.read_bytes())

reports = [retain(CACHE / "full-validation.json", "full-validation.json"),
           retain(CACHE / "code-validation.json", "code-validation.json"),
           retain(installed_path, "installed-verification.json")]
reports += [HERE / name for name in (
    "PLAN-v2.json", "PREPARATION-CHECK-v2.json", "PEER-DESIGN-REVIEW-v1.json",
    "IMPLEMENTATION-PEER-REVIEW-v1.json", "frozen-r07-verification-after.json",
    "frozen-baseline-verification-after.json", "relocation-verification.json",
    "REAL-INPUT-FEASIBILITY.json", "lossless-projection-v1/RESULT.json",
    "tokenizer-measurement-v1/MEASUREMENT-PLAN-v2.json", "tokenizer-measurement-v1/RESULT.json",
    "tokenizer-measurement-v1/ASSET-CHECK.json", "tokenizer-measurement-v1/SOURCE-PIN-CHECK.json")]
result = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
              status="accepted_recorded_fixed_evidence_engineering_only", version="0.3.3",
              full_tests=full["tests"], scoped_tests=17, source_pins_rechecked=len(code["source_pins"]),
              protected_hashes_only=2, installed_legacy_families=7,
              recorded_adapter_cells=12, pure_baseline_results=4,
              actual_generation_calls=0, provider_spending_usd=0,
              fixture_tokens="declared_fixture_usage_not_observed_model_usage",
              comparison_receipt_sha256=comparison["receipt_sha256"],
              comparison_relocation="verified_original_bundle_and_live_source_unavailable",
              prior_R07_and_baseline_replay="verified_by_matching_reviewed_frozen_installations",
              real_source_admission=False, entire_R09_complete=False, scientific_validation="not_established",
              actual_input_feasibility=dict(unchanged_IL6R_byte_reservation=85173,
                  lossless_trial_byte_reservation=81945, pinned_CLI_tokens=28049,
                  pinned_CLI_reservation_with_margin=28241, unchanged_input_ceiling=32000,
                  exact_prior_native_token_count_controls=6,
                  conclusion="Byte policy fails; measured tokenizer counts fit. Current runtime policy and source allowlist unchanged."),
              remaining=["Trusted token-aware preflight specification and implementation",
                         "Source-inclusive real-data admission and separate end-to-end retrieval",
                         "Qualified fresh case/reference/interpretation protocols and actual human submissions",
                         "Native/model and scientific quality remain untested by recorded fixtures"],
              wheel=pin(wheel), preserved_wheel=pin(preserved / wheel.name), evidence=[pin(path) for path in reports])
output = HERE / "acceptance.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "full_tests": 1536, "source_pins": len(code["source_pins"]), "acceptance_sha256": sha(output)}))
