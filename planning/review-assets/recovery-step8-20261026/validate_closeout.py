"""Check retained preparation proofs and current docs, without dispatch or labels."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(name):
    path = Path(name)
    return path if path.is_absolute() else ROOT / path


def check(proof):
    path = resolve(proof["path"])
    assert sha(path) == proof["sha256"], f"Hash mismatch: {path}"
    if "bytes" in proof:
        assert path.stat().st_size == proof["bytes"], f"Size mismatch: {path}"


def pin(path):
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha(path), "bytes": path.stat().st_size}


code = load(ROOT / "planning/review-assets/recovery-step7-20261026/code-validation.json")
for name, expected in code["source_pins"].items():
    check({"path": name, "sha256": expected})
for name, expected in code["protected_hashes"].items():
    # Deliberately hash only. Never load or parse protected outcome payloads.
    check({"path": name, "sha256": expected})
technical_path = ROOT / "planning/review-assets/recovery-step7-20261026/technical-closeout.json"
technical = load(technical_path)
for proof in [technical["plan"], technical["terminal_seal"], *technical["evidence"]]:
    check(proof)
v4_path = HERE / "EXPOSURE-DRAFT-v4.json"
assert sha(v4_path) == "7fa00b8859b8c196b429981d3e0a32ab45c068e79d08eb38053c1e3eb743905d"
v4 = load(v4_path)
for proof in v4["inputs"]:
    check(proof)
assert len(v4["inputs"]) == 571
artifact_checks = 0
manifests = ["source-feasibility-pins.json", "date-followup-pins.json",
             "bounded-source-qualification-pins.json"]
for name in manifests:
    data = load(HERE / name)
    for path, proof in data.get("artifacts", data.get("files", {})).items():
        check({"path": path, **proof})
        artifact_checks += 1
crosswalk_path = HERE / "article-identity-crosswalk-v1/manifest.json"
crosswalk = load(crosswalk_path)
for proof in crosswalk["artifact_proofs"]:
    check(proof)
    artifact_checks += 1
assert crosswalk["matched_article_ids"] == ["31019502"]
assert crosswalk["source_descriptor_count"] == 57 and crosswalk["source_packet_count"] == 58
plan_path = HERE / "bounded-source-plan-v1.json"
assert sha(plan_path) == "bf23203020e88c591512c64b81bfedf733b641bbf6b61f7c8e10a3f89992cdc2"
assert (HERE / "bounded-source-plan-v1.sha256").read_text().strip() == sha(plan_path)

bundle_checks = []
for directory, acceptance in (
    ("expert-review-genetics-20261026", ROOT / "planning/review-assets/recovery-step7-20261026/addendum-review/final-interface-acceptance.json"),
    ("expert-review-source-feasibility-20261026", HERE / "form-review/final-interface-acceptance.json"),
):
    folder = ROOT / "docs" / directory
    data = load(acceptance)
    for name, expected in data["files"].items():
        check({"path": str(folder / name), "sha256": expected})
    bundle = folder / "Expert-source-review-share.zip"
    assert sha(bundle) == data["share_bundle_sha256"]
    with ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {"Expert-source-review.html", "README.md", "Recruitment.md"}
        assert archive.testzip() is None
        for name in archive.namelist():
            assert archive.read(name) == (folder / name).read_bytes()
    bundle_checks.append(pin(bundle))

documents = [ROOT / name for name in (
    "README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md", "docs/STUDY_RUNTIME.md",
    "docs/Expert Review Coordinator Guide 2026-10-26.md", "memory/project-goals.md",
    "memory/MEMORY.md", "memory/research-log-2026-10-26-recovery-execution.md")]
links = 0
for path in documents:
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\((?:<([^>]+)>|([^\)]+))\)", text):
        target = match.group(1) or match.group(2)
        if re.match(r"^(?:https?|mailto|codex):", target) or target.startswith("#"):
            continue
        target = unquote(target.split("#", 1)[0])
        if not target:
            continue
        assert (path.parent / target).exists(), f"Broken link in {path}: {target}"
        links += 1

# Repository-only review helper, deliberately outside the installed runtime.
sys.path.insert(0, str(ROOT))
from tools.validate import structural_checks

structural = structural_checks()
evidence = [technical_path, v4_path, HERE / "exposure-v4-validation.json", plan_path,
            HERE / "bounded-source-qualification-pins.json", crosswalk_path,
            HERE / "metadata-followup-v1.json", HERE / "form-review/final-interface-acceptance.json",
            HERE / "form-review/independent-source-form-audit.json"]
report = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "bounded_preparation_verified_scientific_qualification_pending",
    "runtime_code_changed_after_full_validation": False,
    "full_test_result_retained_not_rerun": technical["full_tests"],
    "source_pins_rechecked": len(code["source_pins"]),
    "protected_files_hash_only": len(code["protected_hashes"]),
    "r07_closeout_proofs_rechecked": len(technical["evidence"]) + 2,
    "v4_input_pins_rechecked": len(v4["inputs"]),
    "preparation_artifact_pins_rechecked": artifact_checks,
    "current_document_local_links_checked": links,
    "structural_checks": structural,
    "clean_bundles_verified": bundle_checks,
    "r07_technical_disposition": "negative_stop_native_expansion",
    "r07_human_scientific_assessment": "pending",
    "r08_fixed_source_contexts": 2,
    "shared_article_id": "31019502",
    "shared_article_does_not_prove_identical_passage_or_prior_model_consumption": True,
    "fresh_cases_qualified": 0,
    "new_model_calls_in_R08": 0,
    "source_replacements": 0,
    "provider_spending_usd": 0,
    "aggregate_R08_complete": False,
    "remaining_gates": [
        "Actual independent domain-matched human judgments and workload observations",
        "Qualified source sufficiency and fresh case/exposure policy before case/split freeze",
        "Complete payload preflight after question/hypothesis scope is qualified",
        "Separately versioned interpretation design before any later model experiment"
    ],
    "evidence": [pin(path) for path in evidence],
    "current_document_pins": [pin(path) for path in documents],
}
destination = HERE / "preparation-closeout.json"
assert not destination.exists(), "Preserve earlier closeout instead of overwriting it"
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "source_pins": len(code["source_pins"]),
                  "v4_pins": len(v4["inputs"]), "artifact_pins": artifact_checks,
                  "local_links": links, "closeout_sha256": sha(destination)}))
