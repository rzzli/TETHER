"""Combine retained static/browser evidence; never manufacture human responses."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


page = ROOT / "docs/expert-review-genetics-followup-20261026/Candidate-followup.html"
readme = page.parent / "README.md"
assert sha(page) == "82bace1c4b87097fd5b25df77b6b83074b8c7c12c66ea66090ee22dca7d16ad6"
browser = ROOT / "data/cache/r07-followup-form-browser-20261026/browser-report.json"
checks = json.loads(browser.read_bytes())
assert checks["status"] == "passed"
assert not checks["external_requests"] and not checks["page_errors"]
assert {item["name"] for item in checks["views"]} == {"desktop", "mobile"}
fidelity = json.loads((HERE / "fidelity-check.json").read_bytes())
assert fidelity["status"] == "passed" and fidelity["defaults"] == 0
assert fidelity["html_sha256"] == sha(page)
source_bundle = ROOT / "docs/expert-review-genetics-20261026/Expert-source-review-share.zip"
assert sha(source_bundle) == "f94194f676fbd09b05e40005f29916025f619c730e6d6eb11f21bfb8edc02fc7"
copy = HERE / "browser-check.json"
assert not copy.exists() or copy.read_bytes() == browser.read_bytes()
copy.write_bytes(browser.read_bytes())
result = {
    "schema_version": 1,
    "status": "passed_interface_qa_coordinator_held",
    "candidate_texts_verbatim": 2,
    "original_json_blocks_verbatim": 2,
    "source_passages_verbatim": 13,
    "dimensions_per_candidate": 7,
    "blank_defaults": True,
    "desktop_mobile_export_roundtrip": "passed",
    "desktop_candidate_and_mobile_save_views_visually_inspected": True,
    "external_requests": 0,
    "qa_exports_are_human_submissions": False,
    "human_reviews_received": 0,
    "source_reference_gate": "retain_independent_source_reference_before_candidate_release",
    "masking": "deterministic_neutral_A_B_not_randomized",
    "scientific_validation": "not_established",
    "candidate_content_or_source_modified": False,
    "source_only_share_bundle_unchanged": True,
    "files": {"Candidate-followup.html": sha(page), "README.md": sha(readme),
              "browser-check.json": sha(copy), "fidelity-check.json": sha(HERE / "fidelity-check.json")},
}
destination = HERE / "final-interface-acceptance.json"
assert not destination.exists(), "Preserve earlier acceptance evidence"
destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "sha256": sha(destination)}))
