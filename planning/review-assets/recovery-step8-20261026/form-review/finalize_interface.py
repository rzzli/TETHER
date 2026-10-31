"""Publish only blank reviewer files after retained offline interface checks."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SHARE = ROOT / "docs/expert-review-source-feasibility-20261026"
MEMBERS = {"Expert-source-review.html", "README.md", "Recruitment.md"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


browser_path = ROOT / "data/cache/r08-source-form-browser-20261026/browser-report.json"
browser = json.loads(browser_path.read_bytes())
static = json.loads((HERE / "static-checks.json").read_bytes())
assert browser["status"] == "passed" and not browser["external_requests"]
assert not browser["page_errors"] and not browser["fixture_is_human_submission"]
assert len(browser["views"]) == 2
assert static["exact_passage_equality"] and static["radio_groups"] == 14
assert static["html_sha256"] == sha(SHARE / "Expert-source-review.html")
assert {path.name for path in SHARE.iterdir()} == MEMBERS
bundle = SHARE / "Expert-source-review-share.zip"
with ZipFile(bundle, "x", compression=ZIP_DEFLATED) as archive:
    for name in sorted(MEMBERS):
        archive.write(SHARE / name, name)
with ZipFile(bundle) as archive:
    assert set(archive.namelist()) == MEMBERS and archive.testzip() is None
    for name in MEMBERS:
        assert archive.read(name) == (SHARE / name).read_bytes()
browser_copy = HERE / "browser-check.json"
assert not browser_copy.exists()
browser_copy.write_bytes(browser_path.read_bytes())
report = {
    "schema_version": 1,
    "status": "passed_blank_source_only_interface_scientific_review_pending",
    "reviewer_question_groups": 14,
    "source_occurrences": 8,
    "unique_source_texts": 7,
    "distinct_article_ids": 6,
    "blank_defaults": True,
    "offline_desktop_mobile_export_and_expanded_locators": "passed",
    "desktop_sources_mobile_save_and_locator_screenshots_visually_inspected": True,
    "source_texts_unchanged": True,
    "fixture_exports_are_human_submissions": False,
    "human_reviews_received": 0,
    "fresh_cases_qualified": 0,
    "candidates_or_AI_verdicts_in_bundle": False,
    "source_or_case_replacement": False,
    "interface_correction": "Restrict export field discovery to the review form; exclude the page viewport metadata.",
    "qa_harness_correction": "Use actual option labels, not assumed machine codes; preserve initial failed QA report.",
    "original_pre_QA_html_sha256": "6d1a4328ebe892beb8c30161e0b3f8d585e0e01ab6ad41113bf92f88537f8613",
    "scientific_validation": "not_established",
    "files": {name: sha(SHARE / name) for name in sorted(MEMBERS)},
    "share_bundle_sha256": sha(bundle),
    "browser_check_sha256": sha(browser_copy),
}
destination = HERE / "final-interface-acceptance.json"
assert not destination.exists()
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "bundle_sha256": sha(bundle),
                  "acceptance_sha256": sha(destination)}))
