"""Independent naming continuity, raw Markdown/PDF inventory and local repeat.

Reads current and retained paper/metadata only. Provider originals, outcomes,
human returns, model inputs and scientific experiment code are not executed.
The old independent raw-text lexer is reused unchanged, not the producer lexer.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PDF = "paper/tether-source-reporting-preprint.pdf"
BUILD = "paper/TETHER-PDF-BUILD.json"
LEXER = "planning/review-assets/preprint-p10-20261101/audit_p10_pdf_inventory_v1.py"
RENDERER = "tools/presentation/build_tether_manuscript.py"
PINS = {
    "paper/manuscript.md": "99ee5893568d4734a393669a88e06920c882d65aa064e7f20a9ad689488e096f",
    "paper/supplement.md": "1f5c2073c7736d7a1b300c375bf84fb574d31df89ff57fa35b45feb60f80daa6",
    PDF: "c5cd6d70d5d4c85a64baf82b59b98618b9714d52840217fe77790c5ce9d4b0b1",
    BUILD: "f0dec66f5f77c9e3f4291afd0629ebd73bfb5a4d9f628983a4727ca67546ac20",
    LEXER: "6664e96c42e1306142711a63861e219092b98f9325fe31f768f1d757a46bbbe6",
    RENDERER: "07330d35414b61d78e4039c03d1ab31e5530f9949e5180d51af9f6f29ed1569b",
    "paper/asof-source-reporting-preprint.pdf": "4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588",
    "paper/asof-source-reporting-preprint-v2.pdf": "c9778533984d2a04451c0f535b54704397977a13de1832dc4dfe9364d25d766d",
    "paper/references.bib": "8804ee43da0da28b71773eb9a55ad0e7b78fb7d881e8b8423562473a2b87d05f",
    "paper/references.json": "d7cf590dd04f094c83931182517ec5d755e5309e87891e9b1c05c1fd70b5bed2",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    import pdfplumber
    from pypdf import PdfReader
    from PIL import Image

    checks = []
    def need(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise AssertionError(name)

    before = {name: sha((ROOT / name).read_bytes()) for name in PINS}
    need("explicit current and retained subject pins", before == PINS)
    lexer = load_module("tether_independent_raw_lexer", LEXER)
    delta_path = HERE / "PAPER-NAMING-DELTA.json"
    delta = json.loads(delta_path.read_bytes())
    history = ROOT / delta["historical_paper_directory"]
    inverse = {}
    for name in ("manuscript.md", "supplement.md", "RELATED-WORK-SOURCE-AUDIT.md"):
        raw = (ROOT / "paper" / name).read_bytes()
        original = (history / name).read_bytes()
        need(name + " retained pre-rename hash", sha(original) == delta["sources"][name]["before_sha256"])
        need(name + " current naming-delta hash", sha(raw) == delta["sources"][name]["after_sha256"])
        if name == "manuscript.md":
            note = b"\n" + delta["new_naming_paragraph"].encode() + b"\n"
            need("single explicit post-result former-name note", raw.count(note) == 1)
            raw = raw.replace(note, b"", 1)
        restored = raw.replace(b"TETHER", b"AsOf")
        need(name + " exact inverse byte continuity", restored == original)
        inverse[name] = {"before_sha256": sha(original), "current_sha256": sha((ROOT / "paper" / name).read_bytes()), "exact_inverse": True}
    renderer_raw = (ROOT / RENDERER).read_bytes()
    restored_renderer = renderer_raw.replace(
        b'OUTPUT = PAPER / "tether-source-reporting-preprint.pdf"', b'OUTPUT = PAPER / "asof-source-reporting-preprint.pdf"').replace(
        b'BUILD = PAPER / "TETHER-PDF-BUILD.json"', b'BUILD = PAPER / "PDF-BUILD.json"').replace(b"TETHER", b"AsOf")
    need("renderer branding/filenames-only inverse", sha(restored_renderer) == "0d6044702a8e6f97de605f7f92acf140c337f7a3f19b1bf6a2c0abb0b432238f")
    build = json.loads((ROOT / BUILD).read_bytes())
    units = lexer.inventory()
    need("274 independently inventoried source units", len(units) == len(build["visible_source_units"]) == 274)
    for unit, declared in zip(units, build["visible_source_units"]):
        need("source unit" + str(unit["id"]) + " metadata", all(unit[k] == declared[k] for k in ("id", "source", "line", "kind", "table_header")))
        need("source unit" + str(unit["id"]) + " exact visible content", sha(unit["text"].encode()) == declared["visible_text_sha256"] and len(unit["text"]) == declared["visible_characters"])
    raw = (ROOT / PDF).read_bytes()
    events, outside, overlap, headers, footers = [], [], [], [], []
    raster = 0
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        need("18 final pages", len(pdf.pages) == 18)
        for page_number, page in enumerate(pdf.pages, 1):
            need(f"page{page_number} geometry", (page.width, page.height) == (612, 792))
            raster += len(page.images)
            header = "".join(c["text"] for c in page.chars if c["top"] < 45)
            footer = "".join(c["text"] for c in page.chars if c["top"] > 750)
            need(f"page{page_number} branded header", header == "TETHER - Working research draft")
            need(f"page{page_number} page-number footer", footer == str(page_number))
            headers.append(header); footers.append(footer)
            for char in page.chars:
                if char["text"].strip() and (char["x0"] < 4 or char["x1"] > 608 or char["top"] < 4 or char["bottom"] > 788):
                    outside.append({"page": page_number, "text": char["text"]})
                ident = char.get("mcid")
                if ident is None:
                    continue
                if type(ident) is not int or not 0 <= ident < len(units):
                    raise AssertionError("PDF source MCID is outside the declared integer inventory")
                if not events or (events[-1]["id"], events[-1]["page"]) != (ident, page_number):
                    events.append({"id": ident, "page": page_number, "text": ""})
                events[-1]["text"] += char["text"]
                if not char["text"].strip():
                    continue
                for figure in build["figure_placements"]:
                    if figure["page"] != page_number:
                        continue
                    dx = min(char["x1"], figure["x"] + figure["width"]) - max(char["x0"], figure["x"])
                    dy = min(char["y1"], figure["y"] + figure["height"]) - max(char["y0"], figure["y"])
                    if dx > .5 and dy > .5:
                        overlap.append({"page": page_number, "unit": ident})
    need("all PDF source MCIDs declared", all(type(event["id"]) is int and 0 <= event["id"] < len(units) for event in events))
    observed, fragments, repeats = [], {}, 0
    for event in events:
        if not lexer.key(event["text"]):
            continue
        ident = event["id"]
        if ident in fragments and units[ident]["table_header"]:
            need("repeated header exact", lexer.key(event["text"]) == lexer.key(units[ident]["text"]))
            repeats += 1
            continue
        if not observed or observed[-1] != ident:
            need("no non-header duplicate/reordered unit", ident not in observed)
            observed.append(ident)
        fragments.setdefault(ident, []).append(event["text"])
    need("all 274 PDF units in source order", observed == list(range(274)))
    for unit in units:
        need("PDF source unit" + str(unit["id"]) + " retained", lexer.key("".join(fragments[unit["id"]])) == lexer.key(unit["text"]))
    need("no raster/clipping/body-figure overlap", raster == 0 and not outside and not overlap)
    need("three original vector overlays", len(build["figure_placements"]) == 3)
    for figure in build["figure_placements"]:
        name = Path(figure["path"]).relative_to(ROOT).as_posix()
        proof = next(x for x in build["figures"].values() if x["path"] == name)
        need(name + " exact consumed figure bytes", sha((ROOT / name).read_bytes()) == proof["sha256"])
    previews = []
    for preview in build["page_previews"]:
        path = ROOT / preview["path"]
        need("preview " + path.name, sha(path.read_bytes()) == preview["sha256"])
        with Image.open(path) as im:
            size = im.size
        previews.append({**preview, "dimensions": size})
    need("18 final preview bindings", len(previews) == 18)
    reader = PdfReader(io.BytesIO(raw))
    metadata = dict(reader.metadata)
    need("metadata current title", metadata.get("/Title", "").startswith("TETHER:"))
    need("metadata current creator", metadata.get("/Creator") == "TETHER deterministic Markdown renderer")
    need("author metadata remains empty", metadata.get("/Author") == "")
    need("working draft remains explicit", "pending" in metadata.get("/Subject", ""))
    links = sum(len(page.get("/Annots", [])) for page in reader.pages)
    need("29 PDF link annotations", links == 29)
    local_links = []
    for name in ("manuscript.md", "supplement.md", "README.md", "RELATED-WORK-SOURCE-AUDIT.md"):
        path = ROOT / "paper" / name
        for match in re.finditer(r"!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)", path.read_text(encoding="utf-8")):
            target = match[1].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme in ("https", "http") or target.startswith("#"):
                continue
            need(name + " local link " + target, (path.parent / unquote(parsed.path)).resolve().exists())
            local_links.append({"source": "paper/" + name, "target": target})
    renderer = load_module("tether_paper_review_renderer", RENDERER)
    source_bytes, blocks, definitions, references, figures = renderer.inputs()
    fonts = {name: path.read_bytes() for name, path in renderer.FONTS.items()}
    repeated, expected, overlays, _ = renderer.render_once(blocks, definitions, references, figures, fonts)
    need("fresh-process in-memory PDF byte repeat", repeated == raw)
    controls = {"retention": renderer.retention_regressions(), "publication": renderer.publication_regressions()}
    need("six retention and two publication negatives", len(controls["retention"]["negative_cases"]) == 6 and len(controls["publication"]["negative_cases"]) == 2 and controls["retention"]["status"] == controls["publication"]["status"] == "PASS")
    root_qa = json.loads((HERE / "PRESERVATION-AND-PAPER-QA.json").read_bytes())
    need("root all-page visual evidence bound to this PDF", root_qa["status"] == "PASS_PRESERVATION_AND_PRESENTATION" and root_qa["pdf_sha256"] == PINS[PDF] and root_qa["visual_review"]["status"] == "PASS" and root_qa["visual_review"]["pages_viewed"] == list(range(1, 19)))
    need("all read-only subject pins remain unchanged", {name: sha((ROOT / name).read_bytes()) for name in PINS} == before)
    need("current working-paper disclaimer retained", b"not ready for submission or publication" in (ROOT / "paper/manuscript.md").read_bytes())
    report = {"schema_version": 1, "method": "tether.independent_paper_naming_review.v1",
        "status": "PASS_PAPER_NAMING_CONTINUITY_AND_PDF", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "evaluation_only", "agent_visible": False, "unresolved_findings": [],
        "check_count": len(checks), "checks": checks, "subjects": before,
        "current_readme": {"path": "paper/README.md", "sha256": sha((ROOT / "paper/README.md").read_bytes()), "status": "separately rewritten current guide; intermediate README hash in initial naming delta is historical"},
        "inverse_scientific_sources": inverse,
        "pdf": {"sha256": PINS[PDF], "pages": 18, "independent_visible_units": 274,
            "unit_kinds": dict(Counter(x["kind"] for x in units)), "table_header_repeat_draws": repeats,
            "vector_figures": 3, "raster_images": raster, "out_of_page_glyphs": outside,
            "body_figure_intersections": overlap, "links": links, "headers": headers, "footers": footers,
            "metadata": metadata, "fresh_process_memory_repeat_bytes_equal": True, "controls": controls},
        "visual_review": {"root_all_pages": list(range(1, 19)), "root_qa_sha256": sha((HERE / "PRESERVATION-AND-PAPER-QA.json").read_bytes()),
            "peer_pages": [], "peer_scope": "Machine checks plus separately recorded direct peer preview checks."},
        "previews": previews, "resolved_local_links": local_links,
        "scientific_change": False, "scientific_validation": "not_established", "owner_declarations": "deferred",
        "publication_authorized": False, "provider_or_protected_or_human_originals_read": 0,
        "study_or_model_execution": False, "network_calls": 0, "script_sha256": sha(Path(__file__).read_bytes())}
    with (HERE / "PAPER-RENAME-PEER-REVIEW.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "checks": len(checks), "units": 274, "pages": 18, "local_links": len(local_links)}))


if __name__ == "__main__":
    main()
