"""Apply a reversible naming-only paper revision and version its renderer.

No source rows, scientific outputs, reference answers or existing PDFs are read
or rewritten. Original paper bytes are retained for inverse verification.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NOTE = ("TETHER expands to Target Evidence Tracking Harness for Evaluation and Reproducibility. "
        "The project was previously named AsOf. This naming revision postdates the experiments; "
        "their identifiers, code commitments, results and costs remain unchanged.")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    baseline = json.loads((HERE / "PRE-RENAME-BASELINE.json").read_bytes())
    names = ("manuscript.md", "supplement.md", "README.md", "RELATED-WORK-SOURCE-AUDIT.md")
    before, prepared, records = {}, {}, {}
    for name in names:
        raw = (ROOT / "paper" / name).read_bytes()
        assert sha(raw) == baseline["pins"]["paper/" + name]["sha256"]
        assert b"TETHER" not in raw and b"AsOf" in raw
        changed = raw.replace(b"AsOf", b"TETHER")
        if name == "manuscript.md":
            anchor = b"\n## Abstract\n"
            assert changed.count(anchor) == 1
            changed = changed.replace(anchor, b"\n" + NOTE.encode() + b"\n" + anchor, 1)
        inverse = changed
        if name == "manuscript.md":
            inverse = inverse.replace(b"\n" + NOTE.encode() + b"\n", b"", 1)
        assert inverse.replace(b"TETHER", b"AsOf") == raw
        before[name], prepared[name] = raw, changed
        records[name] = {"before_sha256": sha(raw), "after_sha256": sha(changed),
            "brand_replacements": raw.count(b"AsOf"), "numerical_or_scientific_edits": 0}
    renderer = ROOT / "tools/science/build_preprint_manuscript.py"
    renderer_raw = renderer.read_bytes()
    assert sha(renderer_raw) == "0d6044702a8e6f97de605f7f92acf140c337f7a3f19b1bf6a2c0abb0b432238f"
    new_renderer = renderer_raw.replace(b"AsOf", b"TETHER")
    new_renderer = new_renderer.replace(b'OUTPUT = PAPER / "asof-source-reporting-preprint.pdf"',
                                        b'OUTPUT = PAPER / "tether-source-reporting-preprint.pdf"')
    new_renderer = new_renderer.replace(b'BUILD = PAPER / "PDF-BUILD.json"',
                                        b'BUILD = PAPER / "TETHER-PDF-BUILD.json"')
    inverse = new_renderer.replace(
        b'OUTPUT = PAPER / "tether-source-reporting-preprint.pdf"', b'OUTPUT = PAPER / "asof-source-reporting-preprint.pdf"').replace(
        b'BUILD = PAPER / "TETHER-PDF-BUILD.json"', b'BUILD = PAPER / "PDF-BUILD.json"').replace(b"TETHER", b"AsOf")
    assert inverse == renderer_raw
    history = ROOT / "paper/history/pre-tether-20261101"
    history.mkdir(parents=True, exist_ok=False)
    for name, raw in before.items():
        (history / name).write_bytes(raw)
    for name, raw in prepared.items():
        (ROOT / "paper" / name).write_bytes(raw)
    destination = ROOT / "tools/presentation/build_tether_manuscript.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(new_renderer)
    result = {"schema_version": 1, "method": "tether.paper_naming_delta.v1", "status": "PASS_EXACT_INVERSE_NAMING_DELTA",
        "role": "evaluation_only", "agent_visible": False, "sources": records, "new_naming_paragraph": NOTE,
        "historical_paper_directory": history.relative_to(ROOT).as_posix(), "scientific_change": False,
        "renderer": {"path": destination.relative_to(ROOT).as_posix(), "sha256": sha(new_renderer),
            "original_renderer_sha256": sha(renderer_raw), "inverse_exact": True,
            "changes": ["AsOf branding to TETHER", "new PDF output filename", "new build-manifest filename"]}}
    with (HERE / "PAPER-NAMING-DELTA.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "changed_sources": len(records), "scientific_change": False,
                      "renderer_sha256": sha(new_renderer)}))


if __name__ == "__main__":
    main()
