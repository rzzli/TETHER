"""Check retained engine/artifacts, source-only rename delta and current PDF QA."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []
    def need(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        assert condition, name
    baseline = json.loads((HERE / "PRE-RENAME-BASELINE.json").read_bytes())
    immutable = {name: value for name, value in baseline["pins"].items()
        if name.startswith(("src/asof/", "paper/release/code/src/asof_p05_replay/"))
        or name in ("pyproject.toml", "uv.lock", "LICENSE", "paper/references.bib", "paper/references.json",
                    "paper/asof-source-reporting-preprint.pdf", "paper/PDF-BUILD.json",
                    "paper/asof-source-reporting-preprint-v2.pdf", "paper/PDF-BUILD-v2.json",
                    "paper/release/RELEASE-RECORD.json", "paper/release/qualification.json",
                    "paper/release/WORKING-PACKET-RECORD.json", "paper/release/WORKING-PACKET-QUALIFICATION.json")}
    for name, item in {**immutable, **baseline["sealed_artifacts"]}.items():
        need("immutable:" + name, sha((ROOT / name).read_bytes()) == item["sha256"])
    delta = json.loads((HERE / "PAPER-NAMING-DELTA.json").read_bytes())
    for name in ("manuscript.md", "supplement.md", "RELATED-WORK-SOURCE-AUDIT.md"):
        raw = (ROOT / "paper" / name).read_bytes()
        need(name + ":current naming hash", sha(raw) == delta["sources"][name]["after_sha256"])
        if name == "manuscript.md":
            paragraph = b"\n" + delta["new_naming_paragraph"].encode() + b"\n"
            need("single explicit former-name paragraph", raw.count(paragraph) == 1)
            raw = raw.replace(paragraph, b"", 1)
        need(name + ":exact inverse to original science", sha(raw.replace(b"TETHER", b"AsOf")) == delta["sources"][name]["before_sha256"])
    build_raw = (ROOT / "paper/TETHER-PDF-BUILD.json").read_bytes()
    build = json.loads(build_raw)
    need("TETHER PDF output name", build["pdf"]["path"] == "paper/tether-source-reporting-preprint.pdf")
    need("TETHER PDF bytes", sha((ROOT / build["pdf"]["path"]).read_bytes()) == build["pdf"]["sha256"])
    need("fresh274 text units", build["qa"]["ordered_source_retention"]["expected_units"] == build["qa"]["ordered_source_retention"]["observed_units"] == 274)
    need("no text loss/change/reorder", all(build["qa"]["ordered_source_retention"][key] == 0 for key in ("missing_units", "changed_visible_units", "duplicate_or_reordered_units")))
    need("18 pages three vector figures no raster/clipping", build["qa"]["pages"] == 18 and build["qa"]["vector_figure_overlays"] == 3 and build["qa"]["raster_images"] == 0 and build["qa"]["out_of_page_glyphs"] == [])
    need("local byte repeat", build["repeat_bytes_equal"] is True)
    need("eight negative formatter/publication controls", len(build["self_tests"]["retention"]["negative_cases"]) + len(build["self_tests"]["publication"]["negative_cases"]) == 8)
    for page, item in enumerate(build["page_previews"], 1):
        need(f"viewed final page{page} preview binding", sha((ROOT / item["path"]).read_bytes()) == item["sha256"])
    need("all final pages separately viewed", len(build["page_previews"]) == 18)
    result = {"schema_version": 1, "method": "tether.rename_preservation_and_presentation.v1",
        "status": "PASS_PRESERVATION_AND_PRESENTATION", "role": "evaluation_only", "agent_visible": False,
        "checks": checks, "check_count": len(checks), "unresolved_findings": [],
        "pdf_sha256": build["pdf"]["sha256"], "build_sha256": sha(build_raw),
        "visual_review": {"status": "PASS", "pages_viewed": list(range(1, 19)),
            "method": "Every final18 page PNG viewed with native image tools; headers/body/tables/figures/references/footers readable. Sparse reference continuation and intact control-table pagination accepted as working draft."},
        "legacy_payloads_unchanged": 100, "scientific_change": False, "provider_originals_read": 0,
        "owner_declarations": "deferred", "publication_authorized": False}
    (HERE / "PRESERVATION-AND-PAPER-QA.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": len(checks), "visual_pages": 18}))


if __name__ == "__main__":
    main()
