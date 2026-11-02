"""Root presentation/retention checks; no provider or protected records opened."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []
    def check(name, ok):
        checks.append({"check": name, "passed": bool(ok)})
        assert ok, name
    delta_path = HERE / "SOURCE-DELTA-v2.json"
    delta = json.loads(delta_path.read_bytes())
    check("four status/release paragraphs only", delta["edited_paragraphs"] == 4)
    for name, item in delta["sources"].items():
        raw = (ROOT / "paper" / name).read_bytes()
        check(name + " final source hash", sha(raw) == item["after_sha256"])
        for edit in reversed(item["edits"]):
            check(name + " unique inverse delta", raw.count(edit["new"].encode()) == 1)
            raw = raw.replace(edit["new"].encode(), edit["old"].encode(), 1)
        check(name + " all other bytes unchanged", sha(raw) == item["before_sha256"])
    old_files = {
        "paper/asof-source-reporting-preprint.pdf": "4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588",
        "paper/PDF-BUILD.json": "f920afd5ea4259ca8f8f4da4255dc43a0d317978cffabf7434dc8ac4ba77dcb5",
        "paper/results/ARTIFACTS.json": "84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428",
        "tools/science/build_preprint_manuscript.py": "0d6044702a8e6f97de605f7f92acf140c337f7a3f19b1bf6a2c0abb0b432238f",
    }
    for name, expected in old_files.items():
        check(name + " historical bytes retained", sha((ROOT / name).read_bytes()) == expected)
    check("inner frozen protocol unchanged", sha((ROOT / "data/cache/p09-runtime-bundle-20261101T213500Z/protocol.json").read_bytes()) == "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529")
    build_path = ROOT / "paper/PDF-BUILD-v2.json"
    build = json.loads(build_path.read_bytes())
    check("final PDF hash", build["pdf"]["sha256"] == "c9778533984d2a04451c0f535b54704397977a13de1832dc4dfe9364d25d766d" == sha((ROOT / build["pdf"]["path"]).read_bytes()))
    check("18 pages and three vector figures", build["qa"]["pages"] == 18 and build["qa"]["vector_figure_overlays"] == 3)
    check("no raster or out-of-page glyphs", build["qa"]["raster_images"] == 0 and build["qa"]["out_of_page_glyphs"] == [])
    ordered = build["qa"]["ordered_source_retention"]
    check("273 freshly observed ordered units", ordered["expected_units"] == ordered["observed_units"] == 273)
    check("no changed/missing/duplicate/reordered units", all(ordered[key] == 0 for key in ("changed_visible_units", "duplicate_or_reordered_units", "missing_units")))
    check("local render byte repeat", build["repeat_bytes_equal"] is True)
    check("eight negative presentation controls", len(build["self_tests"]["retention"]["negative_cases"]) == 6 and len(build["self_tests"]["publication"]["negative_cases"]) == 2)
    check("versioned output override recorded", build["presentation_revision"]["effective_overrides"]["OUTPUT"] == "paper/asof-source-reporting-preprint-v2.pdf")
    check("source delta binding", build["presentation_revision"]["source_delta_sha256"] == sha(delta_path.read_bytes()))
    old = json.loads((ROOT / "data/derived/preprint-p10-20261101/candidate1/PDF-BUILD-v2.json").read_bytes())
    visual = []
    for page, (current, prior) in enumerate(zip(build["page_previews"], old["page_previews"]), 1):
        check(f"page{page} current preview hash", sha((ROOT / current["path"]).read_bytes()) == current["sha256"])
        same = current["sha256"] == prior["sha256"]
        check(f"page{page} visual continuity", same if page != 12 else not same)
        visual.append({"page": page, "sha256": current["sha256"], "visual_review": "PASS",
            "basis": "byte-identical to separately viewed candidate1 page" if same else "final changed page12 separately viewed"})
    check("all18 previews inventoried", len(visual) == len(build["page_previews"]) == 18)
    readme = ROOT / "paper/README.md"
    targets = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme.read_text(encoding="utf-8")):
        if target.startswith(("https://", "http://", "#")):
            continue
        path = (readme.parent / target.split("#")[0]).resolve()
        check("paper README link " + target, path.exists())
        targets.append(target)
    result = {"schema_version": 1, "method": "p10.root_working_revision_qa.v2",
        "status": "PASS_ROOT_PRESENTATION_AND_RETENTION_CHECKS", "role": "evaluation_only", "agent_visible": False,
        "check_count": len(checks), "checks": checks, "unresolved_findings": [],
        "visual_pages": visual, "visual_scope": "All18candidate1 pages viewed with native image tool;17final previews byte-identical; final changed page12 viewed separately. Sparse reference continuation and intact-control-table pagination accepted for working draft.",
        "build_manifest_sha256": sha(build_path.read_bytes()), "source_delta_sha256": sha(delta_path.read_bytes()),
        "paper_readme_sha256": sha(readme.read_bytes()), "resolved_readme_links": targets,
        "old_scientific_review_carry_forward": "Exact inverse-delta continuity for unedited bytes; four new status/release paragraphs need separate independent content review.",
        "owner_declarations": "deferred", "publication_authorized": False,
        "source_originals_or_protected_records_read": 0, "scientific_validation": "not_established"}
    (HERE / "WORKING-REVISION-ROOT-QA-v2.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": len(checks), "visually_covered_pages": 18}))


if __name__ == "__main__":
    main()
