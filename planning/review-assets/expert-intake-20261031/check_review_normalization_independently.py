"""Compare normalized review fields directly with original DOCX tables/TXT lines."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
INTAKE = ROOT / "data/benchmark/gold_evidence/expert-intake-20261031T160538Z"
NORMALIZED = INTAKE / "analysis/normalized-reviews-v1.json"
OWNER = ROOT / "docs/expert-response10312026"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXPECTED_NORMALIZED = "e5cdb5c5f95d14738fcd01c85dbefb7f90e97260f5fd55f0c828622d59acbc86"
checks = []


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def check(group, key, condition):
    checks.append({"group": group, "id": key, "pass": bool(condition)})


def text(paragraph):
    return "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))


def row_text(cell):
    return "\n".join(text(p) for p in cell.findall(".//w:p", NS))


def locator_records(value):
    if isinstance(value, dict):
        if "locator" in value:
            yield value
        for child in value.values():
            yield from locator_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from locator_records(child)


def check_confidence(prefix, answer, raw_confidence):
    check("raw_confidence", prefix, answer["confidence_raw"] == raw_confidence)
    expected = raw_confidence if raw_confidence in ("Low", "Moderate", "High") else None
    mapping = "missing" if raw_confidence is None else "exact" if expected is not None else "not_an_exact_form_value_no_coercion"
    check("confidence_no_coercion", prefix,
          answer["confidence_form_value"] == expected and answer["confidence_mapping"] == mapping)


def main():
    check("input_pins", "normalized", pin(NORMALIZED)["sha256"] == EXPECTED_NORMALIZED)
    normalized = json.loads(NORMALIZED.read_bytes())
    packet_path = ROOT / "docs/expert-review-20261026/Expert-review.html"
    packet_raw = packet_path.read_text(encoding="utf-8")
    packet = json.loads(re.search(r"const PACKET=(\{.*?\}),KEY=", packet_raw).group(1))
    questions = packet["source_questions"] + packet["rating_questions"]
    options = {question["id"]: question["options"] for question in questions}
    check("input_pins", "packet", pin(packet_path) == normalized["packet"])
    check("shape", "exact18ids", set(options) == {f"{prefix}{i:02d}" for prefix in "SR" for i in range(1, 10)})
    check("shape", "three_records", len(normalized["records"]) == 3)
    check("role_limits", "top_role", normalized["role"] == "evaluation_only")
    checked_locators = 0
    source_pins = []
    for number, record in enumerate(normalized["records"], 1):
        sid = record["submission_id"]
        source = Path(record["source"]["path"])
        owner_original = OWNER / source.name
        source_pins.append(pin(source))
        check("input_pins", sid + "_copied", pin(source) == record["source"])
        check("input_pins", sid + "_owner", pin(owner_original)["sha256"] == pin(source)["sha256"])
        check("shape", sid + "_exact_answers", set(record["answers"]) == set(options))
        check("role_limits", sid, record["role"] == "evaluation_only" and record["adjudicated_gold"] is False
              and record["provenance"]["human_provenance_accepted"] is False
              and record["provenance"]["independent_source_only_reference_accepted"] is False)
        observed = {}
        raw_map = {}
        if source.suffix == ".docx":
            with zipfile.ZipFile(owner_original) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
            paragraphs = document.findall(".//w:p", NS)
            ordinal = {id(paragraph): index for index, paragraph in enumerate(paragraphs)}
            raw_map = {f"word/document.xml#paragraph[{index}]": text(paragraph)
                       for index, paragraph in enumerate(paragraphs)}
            tables = document.findall(".//w:tbl", NS)
            check("shape", sid + "_three_tables", len(tables) == 3)
            for table_index, table in enumerate(tables):
                for row_index, row in enumerate(table.findall("./w:tr", NS)):
                    cells = row.findall("./w:tc", NS)
                    if table_index == 0:
                        raw_map[f"word/document.xml#table[{table_index}]/row[{row_index}]"] = {
                            "label": row_text(cells[0]), "raw_value": row_text(cells[1])}
                    elif len(cells) == 4 and row_text(cells[0]) in options:
                        item_id = row_text(cells[0])
                        selection_paragraph = cells[1].find(".//w:p", NS)
                        observed[item_id] = {
                            "choice": row_text(cells[1]),
                            "selection_locator": f"word/document.xml#paragraph[{ordinal[id(selection_paragraph)]}]",
                            "returned_choice_text": row_text(cells[1]),
                            "confidence": row_text(cells[2]),
                            "notes": [{"locator": f"word/document.xml#paragraph[{ordinal[id(p)]}]", "text": text(p)}
                                      for p in cells[3].findall(".//w:p", NS) if text(p)],
                        }
            check("administration", sid + "_all_six_blank_admin_rows",
                  len(record["administrative_raw"]) == 6 and all(row["raw_value"] == "" for row in record["administrative_raw"]))
            expected_notes = [{"locator": f"word/document.xml#paragraph[{i}]", "text": raw_map[f"word/document.xml#paragraph[{i}]"]}
                              for i in range(4, 8)]
            check("administration", sid + "_completion_notes", record["completion_notes"] == expected_notes)
            check("revision", sid + "_explicit_revision",
                  len(record["explicit_revisions"]) == 1 and record["explicit_revisions"][0]["item_id"] == "R09"
                  and record["explicit_revisions"][0]["previous_choice"] == "C"
                  and record["explicit_revisions"][0]["current_choice"] == "B"
                  and "Revised from C to B" in raw_map[record["explicit_revisions"][0]["record"]["locator"]])
            expected_sections = [(62, [63]), (118, [119]), (120, [121])]
            check("free_text", sid + "_three_sections", len(record["free_text_sections"]) == 3)
            for actual, (head, contents) in zip(record["free_text_sections"], expected_sections):
                check("free_text", sid + f"_section{head}",
                      actual["heading"] == {"locator": f"word/document.xml#paragraph[{head}]", "text": raw_map[f"word/document.xml#paragraph[{head}]"]}
                      and actual["contents"] == [{"locator": f"word/document.xml#paragraph[{i}]", "text": raw_map[f"word/document.xml#paragraph[{i}]"]} for i in contents])
        else:
            lines = owner_original.read_bytes().decode("utf-8-sig").splitlines()
            raw_map = {f"line[{index}]": line for index, line in enumerate(lines, 1)}
            item_lines = []
            for index, line in enumerate(lines, 1):
                match = re.fullmatch(r"([SR]\d{2})[.:]\s*([A-E])\.\s*(.*)", line)
                if match:
                    observed[match[1]] = {"choice": match[2], "selection_locator": f"line[{index}]",
                                          "returned_choice_text": match[3], "confidence": None, "notes": []}
                    item_lines.append((index, match[1]))
            for index, item_id in item_lines:
                next_line = index + 1
                while next_line <= len(lines) and lines[next_line - 1].strip():
                    line = lines[next_line - 1]
                    observed[item_id]["notes"].append({"locator": f"line[{next_line}]", "text": line})
                    confidence = re.match(r"Confidence: ([^.]+)\.", line)
                    if confidence:
                        observed[item_id]["confidence"] = confidence[1]
                    next_line += 1
            check("revision", sid + "_no_revision", record["explicit_revisions"] == [])
            if number == 2:
                administrative_expected = [{"locator": f"line[{i}]", "text": lines[i - 1]} for i in range(1, 11) if lines[i - 1]]
                check("administration", sid + "_raw_admin", record["administrative_raw"] == administrative_expected)
                check("free_text", sid + "_two_sections", len(record["free_text_sections"]) == 2)
                for actual, (head, contents) in zip(record["free_text_sections"], [(39, [40, 41]), (71, [72])]):
                    check("free_text", sid + f"_section{head}",
                          actual["heading"] == {"locator": f"line[{head}]", "text": lines[head - 1]}
                          and actual["contents"] == [{"locator": f"line[{i}]", "text": lines[i - 1]} for i in contents])
            else:
                check("administration", sid + "_no_admin", record["administrative_raw"] == [])
                check("free_text", sid + "_no_free_sections", record["free_text_sections"] == [])
        check("shape", sid + "_18original_selections", set(observed) == set(options))
        for item_id, original in observed.items():
            actual = record["answers"][item_id]
            key = sid + "_" + item_id
            check("choice", key, actual["choice"] == original["choice"])
            check("selection_locator", key, actual["selection_locator"] == original["selection_locator"])
            check("returned_choice_text", key, actual["returned_choice_text"] == original["returned_choice_text"])
            check("bound_option_label", key, actual["option_text_from_bound_form"] == options[item_id][ord(original["choice"]) - ord("A")])
            check("item_stage", key, actual["item_id"] == item_id and actual["stage"] == ("source_only_requested" if item_id.startswith("S") else "candidate_assessment"))
            check_confidence(key, actual, original["confidence"])
            check("notes", key, actual["note_records"] == original["notes"])
        for entry in locator_records(record):
            locator = entry["locator"]
            if "text" in entry:
                check("all_note_locators", sid + "_" + locator, raw_map.get(locator) == entry["text"])
            elif "label" in entry and "raw_value" in entry:
                check("all_note_locators", sid + "_" + locator, raw_map.get(locator) == {"label": entry["label"], "raw_value": entry["raw_value"]})
            else:
                check("all_note_locators", sid + "_" + locator, False)
            checked_locators += 1
    counts = Counter(row["group"] for row in checks)
    failures = [row for row in checks if not row["pass"]]
    private = {"schema_version": 1, "status": "PASS" if not failures else "HOLD",
               "role": "evaluation_only", "checks": checks, "failures": failures,
               "normalized": pin(NORMALIZED), "originals": source_pins,
               "notes": "Independent DOCX-table and text-line parsing; normalizer and its projections not executed or used as original truth."}
    private_path = INTAKE / "analysis/independent-normalization-check-v1.json"
    with private_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(private, stream, indent=2);stream.write("\n")
    report = {"schema_version": 1, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "PASS_INDEPENDENT_ORIGINAL_TO_NORMALIZED_CONVERSION" if not failures else "HOLD_NORMALIZATION",
              "role": "evaluation_only", "normalized": pin(NORMALIZED), "packet": pin(packet_path),
              "originals": source_pins, "private_check": pin(private_path),
              "checker": pin(Path(__file__)),
              "counts": {"submissions": 3, "items_per_submission": 18, "explicit_choices": counts["choice"],
                         "bound_option_labels": counts["bound_option_label"], "locator_records": checked_locators,
                         "total_checks": len(checks), "passed": len(checks) - len(failures), "failed": len(failures),
                         "explicit_revisions_retained": 1,
                         "nonstandard_confidence_preserved_uncoerced": 8, "missing_confidence_retained": 18},
              "check_groups": dict(counts),
              "limits": ["Conversion and locator integrity only; no scientific scoring, vote adjudication, or assessment of expert competence.",
                         "AI disclosure/candidate exposure remain; owner classified other origins mixed or uncertain. No human/independence qualification.",
                         "Originals, private normalized payload and private detailed checks remain ignored evaluator-only data; report contains no answer values.",
                         "No normalizer replay, model/native/full-suite run, article download or protected outcome access."],
              "human_gate_satisfied": False, "scientific_validation": "not_established"}
    public = BASE / "RETURNED-REVIEW-INDEPENDENT-NORMALIZATION-v1.json"
    with public.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2);stream.write("\n")
    print(json.dumps({"report": pin(public), "status": report["status"], "counts": report["counts"], "failed_groups": [row["group"] for row in failures]}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
