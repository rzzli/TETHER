"""Bind final Q03 metadata corrections without original-source reads or execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[3]
DATA = BASE / "data"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


prior_path = HERE / "INDEPENDENT-FEASIBILITY-CHECK.json"
prior = load(prior_path)
old_pins = {k.replace("\\", "/"): v for k, v in prior["input_pins"].items()}
checks = []


def check(name, value):
    checks.append({"property": name, "pass": bool(value)})
    if not value:
        raise AssertionError(name)


changed = []
for path in sorted(DATA.glob("*.json")):
    rel = path.relative_to(ROOT).as_posix()
    if rel in old_pins and sha(path) != old_pins[rel]:
        changed.append(path.name)
check("only two prior JSON metadata files changed", changed == ["SOURCE-AUDIT-ATTEMPTS.json", "SOURCE-EXCERPT-MANIFEST.json"])
old_attempt_path = DATA / "revisions/attempt-record-before-clarification.json"
check("earlier attempt record retained exactly", sha(old_attempt_path) == old_pins[(DATA / "SOURCE-AUDIT-ATTEMPTS.json").relative_to(ROOT).as_posix()])
attempt = load(DATA / "SOURCE-AUDIT-ATTEMPTS.json")
old_attempt = load(old_attempt_path)
check("recorded selection policy unchanged", attempt["selection_policy_sha256"] == old_attempt["selection_policy_sha256"])
for earlier, current in zip(old_attempt["attempts"], attempt["attempts"]):
    check("earlier attempt fields preserved " + str(earlier["attempt"]), all(current[k] == v for k, v in earlier.items()))
check("both contemporaneous executed code pins absent", all(a["executed_script_sha256"] is None for a in attempt["attempts"]))
check("first attempt bytes and hashes absent", attempt["first_attempt_retention"]["projection_bytes_retained"] is False and attempt["first_attempt_retention"]["projection_sha256_retained"] is False)
revision = attempt["executed_revision_pins"]
check("honest post-run source pin", sha(revision["retained_post_run_revision_path"]) == revision["retained_post_run_revision_sha256"] == old_attempt["current_audit_script_sha256"])
current_code = attempt["current_reusable_code"]
check("current unmeasured utility pinned", sha(current_code["main_path"]) == current_code["main_sha256"] and sha(current_code["helper_path"]) == current_code["helper_sha256"])
excerpt = load(DATA / "SOURCE-EXCERPT-MANIFEST.json")
retention = excerpt.pop("retention_provenance")
reconstructed = (json.dumps(excerpt, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8")
check("old excerpt metadata reproduced without retention addition", hashlib.sha256(reconstructed).hexdigest() == old_pins[(DATA / "SOURCE-EXCERPT-MANIFEST.json").relative_to(ROOT).as_posix()])
check("retained excerpts identified as attempt2", retention["retained_attempt"] == 2 and retention["first_attempt_outputs_were_overwritten"] is True)
for ex in excerpt["excerpts"]:
    path = Path(ex["path"])
    check("cached projection hash still matches " + path.name, path.resolve().is_relative_to(ROOT / "data/cache/tether-q03") and sha(path) == ex["sha256"])
collision = load(DATA / "SOURCE-NO-CLOBBER-VERIFICATION.json")
check("recorded fixture scope", collision["passed"] is True and len(collision["checks"]) == 4 and collision["raw_source_files_read"] == 0 and collision["original_sentinel_sha256"] == collision["final_sentinel_sha256"])
check("prior source check preserved", len(prior["checks"]) == 1160 and all(c["pass"] for c in prior["checks"]))
pins = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(DATA.glob("*.json"))}
for p in [DATA / "SOURCE-FEASIBILITY.md", Path(current_code["main_path"]), Path(current_code["helper_path"]), Path(revision["retained_post_run_revision_path"]), old_attempt_path, prior_path, HERE / "INDEPENDENT-FEASIBILITY-REVIEW.md", Path(__file__)]:
    pins[p.relative_to(ROOT).as_posix()] = sha(p)
result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": "pass", "scope": "metadata-only delta; no raw originals read, no source/audit/model execution", "changed_previous_metadata": changed, "checks": checks, "original_source_files_read": 0, "cached_projection_files_hashed_only": 3, "previous_source_check_sha256": sha(prior_path), "limits": ["1,160 earlier assertions remain evidence of prior independent source pass, not newly executed here", "No full-source qualification or measured-code reconstruction for current no-clobber utility", "Source-agent collision fixture report is bound and scope-checked, not independently rerun"], "current_pins": pins}
(HERE / "FINAL-METADATA-DELTA.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "pass", "metadata_checks": len(checks), "current_pins": len(pins), "raw_source_reads": 0, "review_sha256": sha(HERE / "INDEPENDENT-FEASIBILITY-REVIEW.md"), "delta_sha256": sha(HERE / "FINAL-METADATA-DELTA.json")}, indent=2))
