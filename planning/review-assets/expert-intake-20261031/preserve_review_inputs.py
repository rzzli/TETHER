"""Preserve owner-supplied review originals and exact text as evaluator-only data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/expert-response10312026"
EXPECTED = {
    "IL6R_Completed_Responses1.docx": "78af3e50cde860bb551337a69a59bfb9439c327bb8e06693bc799377fbd0ed19",
    "response2.txt": "cf8ddfb04e1827220983d807b79fa7ad1fcb1d16d24449a942c24a6e57e90c84",
    "response3.txt": "8597d4e6d4f68b4f568b8ad09a76722ee100e7e2a64e94e0c0d4258b820ab32b",
}
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return pin(path)


def extract_docx(raw_path):
    with zipfile.ZipFile(raw_path) as archive:
        members = archive.infolist()
        if len(members) > 128 or sum(item.file_size for item in members) > 4 * 1024 * 1024:
            raise ValueError("Document archive exceeds the inspected bound")
        names = [item.filename for item in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate document members")
        for item in members:
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or item.flag_bits & 1:
                raise ValueError("Linked/encrypted document member")
        raw = archive.read("word/document.xml")
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("External/entity document declarations")
        document = ET.fromstring(raw)
        paragraphs = []
        for ordinal, paragraph in enumerate(document.findall(".//w:p", NS)):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
            paragraphs.append({"locator": f"word/document.xml#paragraph[{ordinal}]", "text": text})
        comments = []
        if "word/comments.xml" in names:
            for comment in ET.fromstring(archive.read("word/comments.xml")):
                comments.append({"id": comment.get("{" + NS["w"] + "}id"),
                                 "text": "".join(node.text or "" for node in comment.findall(".//w:t", NS))})
        return {"format": "docx_text_projection", "paragraphs": paragraphs, "comments": comments,
                "insertions": len(document.findall(".//w:ins", NS)),
                "deletions": len(document.findall(".//w:del", NS)),
                "archive_members": len(members), "expanded_bytes": sum(item.file_size for item in members),
                "limits": "Text nodes in XML paragraph order; no formatting/render equivalence, image OCR, macro or external-link execution."}


def main():
    for name, expected in EXPECTED.items():
        actual = pin(SOURCE / name)
        if actual["sha256"] != expected:
            raise ValueError("Source changed since inspection: " + name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "data/benchmark/gold_evidence" / ("expert-intake-" + stamp)
    output.mkdir()
    originals = output / "originals"
    extracts = output / "extracts"
    originals.mkdir()
    extracts.mkdir()
    manifest = {"schema_version": 1, "received_at_utc": datetime.now(timezone.utc).isoformat(),
                "role": "evaluation_only", "classification": "unqualified_development_review_intake",
                "agent_visible": False, "human_provenance_accepted": False,
                "adjudicated_gold": False, "packet_claim": "mechanism orientation; exact binding to verify",
                "records": [], "source_inputs": [pin(SOURCE / name) for name in EXPECTED]}
    for index, name in enumerate(EXPECTED, 1):
        source = SOURCE / name
        copied = originals / name
        with copied.open("xb") as stream:
            stream.write(source.read_bytes())
        if pin(copied)["sha256"] != EXPECTED[name]:
            raise ValueError("Copied bytes differ")
        if source.suffix == ".docx":
            projection = extract_docx(copied)
        else:
            text = copied.read_bytes().decode("utf-8-sig")
            projection = {"format": "utf8_text_lines", "lines": [
                {"locator": f"line[{ordinal}]", "text": line}
                for ordinal, line in enumerate(text.splitlines(), 1)],
                "replacement_codepoints": text.count("\ufffd"),
                "limits": "Original encoding marker/line endings retained in copied original; no text correction or Unicode normalization."}
        projection["role"] = "evaluation_only"
        projection["input_parent"] = pin(copied)
        projected = write_json(extracts / f"response-{index:02d}.json", projection)
        manifest["records"].append({"submission_id": f"received-{index:02d}", "source": pin(source),
                                    "preserved_original": pin(copied), "projection": projected,
                                    "reviewer_id": None, "independence": None,
                                    "catalog_intent": ["gold_evidence", "panel_ratings"],
                                    "catalog_intent_limit": "Evaluator-only classification, not acceptance as human/adjudicated/blinded panel evidence."})
    for source in manifest["source_inputs"]:
        if pin(Path(source["path"])) != source:
            raise ValueError("Original changed during preservation")
    result = write_json(output / "intake-manifest.json", manifest)
    print(json.dumps({"output": str(output), "manifest": result, "files_preserved": len(EXPECTED),
                      "source_bytes": sum(row["bytes"] for row in manifest["source_inputs"]),
                      "human_provenance_accepted": False, "agent_visible": False}))


if __name__ == "__main__":
    main()
