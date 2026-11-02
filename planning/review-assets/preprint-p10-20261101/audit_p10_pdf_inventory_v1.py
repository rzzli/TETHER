"""Independent Markdown inventory and PDF-miner checks; no renderer helpers."""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
PINS = {
    "paper/manuscript.md": "79a49c7bbaba7ad65786cc5e1bbfd872ae941396990b2d17315f685e4ca3b507",
    "paper/supplement.md": "d1a63bec471b13d44e888c4f40857d67d2cd13e504c2acef856659c3f5fabb85",
    "paper/asof-source-reporting-preprint-v2.pdf": "c9778533984d2a04451c0f535b54704397977a13de1832dc4dfe9364d25d766d",
    "paper/PDF-BUILD-v2.json": "2d056ffff02dc8977790408d6f1ead452a929c837c86291d2634ceaf2cb8b2d7",
    "paper/asof-source-reporting-preprint.pdf": "4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588",
    "paper/PDF-BUILD.json": "f920afd5ea4259ca8f8f4da4255dc43a0d317978cffabf7434dc8ac4ba77dcb5",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def key(value):
    return "".join(unicodedata.normalize("NFKC", value).split())


def typography(value):
    replacements = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": " - ", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "\u00a0": " "}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def plain(value):
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\[[^\]]+\]", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", value)
    return re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", value)


def cells(line):
    require(line.strip().startswith("|") and line.strip().endswith("|"), "Unsupported table borders")
    body = line.strip()[1:-1]
    result, current, index = [], [], 0
    while index < len(body):
        if body[index:index + 2] == "\\|":
            current.append("|"); index += 2
        elif body[index] == "|":
            result.append("".join(current).strip()); current = []; index += 1
        else:
            current.append(body[index]); index += 1
    result.append("".join(current).strip())
    return result


def inventory():
    units, figure_number = [], 0
    for name in ("manuscript.md", "supplement.md"):
        lines = typography((ROOT / "paper" / name).read_text(encoding="utf-8-sig")).splitlines()
        groups, active, fence = [], [], False
        for number, line in enumerate(lines, 1):
            if line.startswith("```"):
                fence = not fence
            if line.strip() or fence:
                active.append((number, line))
            elif active:
                groups.append(active); active = []
        if active: groups.append(active)
        require(not fence, "Unclosed raw source fence")
        for group in groups:
            start = group[0][0]
            content = [line for _, line in group]
            def emit(text, kind, header=False):
                require(bool(key(text)), "Empty visible source unit")
                units.append(dict(id=len(units), source=name, line=start, kind=kind, table_header=header, text=text))
            if all(re.fullmatch(r"\[[^\]]+\]:\s+https?://\S+\s*", line) for line in content):
                continue
            if len(content) == 1 and re.fullmatch(r"[-*_]{3,}", content[0].strip()):
                continue
            if content[0].startswith("```"):
                require(content[-1].startswith("```"), "Unclosed source code block")
                emit("\n".join(content[1:-1]), "code")
            elif len(content) == 1 and (heading := re.match(r"^#{1,6}\s+(.+)$", content[0])):
                emit(plain(heading[1]), "heading")
            elif len(content) == 1 and (image := re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)\s*", content[0])):
                figure_number += 1
                caption = image[1] if re.match(r"Figure\s+\d", image[1]) else f"Figure {figure_number}. " + image[1]
                emit(plain(caption), "figure")
            elif len(content) >= 2 and content[0].strip().startswith("|") and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells(content[1])):
                for row_number, row in enumerate([content[0], *content[2:]]):
                    for cell in cells(row): emit(plain(cell), "table", row_number == 0)
            elif all(re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)", line) for line in content):
                for line in content: emit("- " + plain(re.sub(r"^\s*(?:[-*+]\s+|\d+\.\s+)", "", line)), "bullet")
            else:
                require(not any(re.match(r"^(?:#{1,6}\s|!\[|```)", line) for line in content), "Unsupported mixed source block")
                emit(plain(" ".join(line.strip() for line in content)), "paragraph")
    return units


def main():
    import pdfplumber
    from pypdf import PdfReader
    from PIL import Image
    before = {name: sha((ROOT / name).read_bytes()) for name in PINS}
    require(before == PINS, "Source/PDF subject pin differs")
    units = inventory()
    build = json.loads((ROOT / "paper/PDF-BUILD-v2.json").read_bytes())
    declared = build["visible_source_units"]
    require(len(units) == len(declared), "Independent unit count differs")
    for unit, producer in zip(units, declared):
        require(all(unit[k] == producer[k] for k in ("id", "source", "line", "kind", "table_header")), "Independent source metadata differs")
        require(sha(unit["text"].encode()) == producer["visible_text_sha256"] and len(unit["text"]) == producer["visible_characters"], "Independent source unit bytes differ")
    raw = (ROOT / "paper/asof-source-reporting-preprint-v2.pdf").read_bytes()
    events, intersections, outside = [], [], []
    raster, total_chars, tagged_chars = 0, 0, 0
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        pages = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, 1):
            require((page.width, page.height) == (612, 792), "PDF page geometry differs")
            raster += len(page.images)
            for char in page.chars:
                total_chars += 1
                if char["text"].strip() and (char["x0"] < 4 or char["x1"] > 608 or char["top"] < 4 or char["bottom"] > 788):
                    outside.append(dict(page=page_number, text=char["text"], bbox=[char["x0"], char["top"], char["x1"], char["bottom"]]))
                ident = char.get("mcid")
                if ident is None: continue
                tagged_chars += 1
                require(type(ident) is int and 0 <= ident < len(units), "Unexpected source MCID")
                if not events or (events[-1]["id"], events[-1]["page"]) != (ident, page_number):
                    events.append(dict(id=ident, page=page_number, text=""))
                events[-1]["text"] += char["text"]
                if not char["text"].strip(): continue
                for figure in build["figure_placements"]:
                    if figure["page"] != page_number: continue
                    dx = min(char["x1"], figure["x"] + figure["width"]) - max(char["x0"], figure["x"])
                    dy = min(char["y1"], figure["y"] + figure["height"]) - max(char["y0"], figure["y"])
                    if dx > 0.5 and dy > 0.5:
                        intersections.append(dict(page=page_number, unit=ident, character=char["text"]))
    observed, fragments, repeats = [], {}, 0
    for event in events:
        if not key(event["text"]): continue
        ident = event["id"]
        if ident in fragments and units[ident]["table_header"]:
            require(key(event["text"]) == key(units[ident]["text"]), "Changed repeated header")
            repeats += 1
            continue
        if not observed or observed[-1] != ident:
            require(ident not in observed, "Reordered or duplicated visible source unit")
            observed.append(ident)
        fragments.setdefault(ident, []).append(event["text"])
    require(observed == list(range(len(units))), "Missing/reordered PDF source units")
    for unit in units:
        require(key("".join(fragments[unit["id"]])) == key(unit["text"]), "Independent PDF/source text differs")
    require(not outside and not intersections and raster == 0, "PDF geometry/raster defect")
    require(pages == 18 and len(build["figure_placements"]) == 3, "Page/vector count differs")
    figures = []
    for figure in build["figure_placements"]:
        require(54 - 1 <= figure["x"] and 52 - 1 <= figure["y"] and figure["x"] + figure["width"] <= 559 and figure["y"] + figure["height"] <= 739, "Vector outside content frame")
        name = Path(figure["path"]).relative_to(ROOT).as_posix()
        proof = next(value for value in build["figures"].values() if value["path"] == name)
        require(sha((ROOT / name).read_bytes()) == proof["sha256"], "Consumed figure byte hash differs")
        figures.append(dict(path=name, sha256=proof["sha256"], page=figure["page"]))
    previews = []
    for preview in build["page_previews"]:
        path = ROOT / preview["path"]
        require(sha(path.read_bytes()) == preview["sha256"], "Final preview hash differs")
        with Image.open(path) as image: dimensions = image.size
        previews.append(dict(path=preview["path"], sha256=preview["sha256"], dimensions=dimensions))
    reader = PdfReader(io.BytesIO(raw))
    links = sum(len(page.get("/Annots", [])) for page in reader.pages)
    require(len(previews) == pages and links == 29, "Preview/link inventory differs")
    after = {name: sha((ROOT / name).read_bytes()) for name in PINS}
    require(before == after, "Read-only subject changed during audit")
    report = dict(schema_version=1, method="p10.independent_raw_markdown_pdfminer_inventory.v1", status="PASS", subject=before,
        implementation="Own blank-block/pipe lexer plus pdfplumber/pdfminer MCIDs; no renderer parser, visible-text helper or retention checker used",
        units=len(units), unit_kinds=dict(Counter(unit["kind"] for unit in units)), table_header_repeat_draws=repeats,
        pages=pages, total_characters=total_chars, tagged_characters=tagged_chars, raster_images=raster,
        body_vector_intersections=intersections, out_of_page_glyphs=outside, links=links, figures=figures,
        independent_units=[{k: v for k, v in unit.items() if k != "text"} | dict(visible_text_sha256=sha(unit["text"].encode()), normalized_sha256=sha(key(unit["text"]).encode()), characters=len(unit["text"])) for unit in units],
        preview_hashes=previews, old_P08_pdf_and_build_preserved=True, provider_source_values_read=False,
        science_reperformed=False, script_sha256=sha(Path(__file__).read_bytes()))
    output = Path(__file__).resolve().parent / "PDF-INDEPENDENT-INVENTORY-v1.json"
    with output.open("xb") as stream: stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({k: v for k, v in report.items() if k not in ("independent_units", "preview_hashes")}, sort_keys=True))


if __name__ == "__main__":
    main()
