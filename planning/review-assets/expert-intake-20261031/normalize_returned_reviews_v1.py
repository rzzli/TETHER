"""Project supplied reviews into private, source-located comparison records.

This reads no clinical outcome/gold file and performs no model execution. Choice
agreement is descriptive only; file counts never establish reviewer independence.
"""
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
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
CONFIDENCE = {"Low", "Moderate", "High"}
ITEM = re.compile(r"^[SR]0[1-9]$")
LINE_ITEM = re.compile(r"^([SR]0[1-9])[.:]\s+([A-E])\.\s*(.*)$")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read_pin(selected):
    path = Path(selected["path"])
    actual = pin(path)
    if any(actual[key] != selected[key] for key in ("path", "bytes", "sha256")):
        raise ValueError("Changed selected input: " + str(path))
    return path.read_bytes()


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return pin(path)


def text(element):
    return "".join(node.text or "" for node in element.findall(".//w:t", NS))


def form_packet():
    path = ROOT / "docs/expert-review-20261026/Expert-review.html"
    raw = path.read_text(encoding="utf-8")
    start = raw.index("const PACKET=") + len("const PACKET=")
    packet, _ = json.JSONDecoder().raw_decode(raw[start:])
    if packet["packet_id"] != "asof-il6r-development-review-20261026-v1":
        raise ValueError("Unexpected mechanism form")
    questions = packet["source_questions"] + packet["rating_questions"]
    expected = [f"{stage}{number:02d}" for stage in ("S", "R") for number in range(1, 10)]
    if [question["id"] for question in questions] != expected:
        raise ValueError("Unexpected question universe")
    return packet, {question["id"]: question for question in questions}, pin(path)


def record_answer(item_id, choice, confidence_raw, note_records, selection_locator,
                  returned_choice_text, questions):
    if item_id not in questions or choice not in "ABCDE":
        raise ValueError("Invalid explicit item/choice")
    index = ord(choice) - ord("A")
    if index >= len(questions[item_id]["options"]):
        raise ValueError("Choice outside the pinned question")
    return {"item_id": item_id, "stage": "source_only_requested" if item_id[0] == "S" else "candidate_assessment",
            "choice": choice, "selection_locator": selection_locator,
            "returned_choice_text": returned_choice_text,
            "option_text_from_bound_form": questions[item_id]["options"][index],
            "confidence_raw": confidence_raw,
            "confidence_form_value": confidence_raw if confidence_raw in CONFIDENCE else None,
            "confidence_mapping": "exact" if confidence_raw in CONFIDENCE else "missing" if confidence_raw is None else "not_an_exact_form_value_no_coercion",
            "note_records": note_records}


def docx_record(record, projection, questions):
    path = Path(record["preserved_original"]["path"])
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    paragraphs = document.findall(".//w:p", NS)
    indices = {id(paragraph): index for index, paragraph in enumerate(paragraphs)}
    if len(paragraphs) != len(projection["paragraphs"]):
        raise ValueError("DOCX projection paragraph count differs")
    for ordinal, paragraph in enumerate(paragraphs):
        if text(paragraph) != projection["paragraphs"][ordinal]["text"]:
            raise ValueError("DOCX projection text differs")
    answers = {}
    metadata_rows = []
    for table_ordinal, table in enumerate(document.findall(".//w:tbl", NS)):
        for row_ordinal, row in enumerate(table.findall("./w:tr", NS)):
            cells = row.findall("./w:tc", NS)
            values = [text(cell) for cell in cells]
            if len(cells) == 2:
                metadata_rows.append({"label": values[0], "raw_value": values[1],
                    "locator": f"word/document.xml#table[{table_ordinal}]/row[{row_ordinal}]"})
            if len(cells) != 4 or not ITEM.fullmatch(values[0]):
                continue
            item_id, choice, confidence_raw, _ = values
            if item_id in answers:
                raise ValueError("Duplicate DOCX answer")
            notes = [{"locator": f"word/document.xml#paragraph[{indices[id(p)]}]", "text": text(p)}
                     for p in cells[3].findall(".//w:p", NS)]
            choice_paragraph = cells[1].find("./w:p", NS)
            answers[item_id] = record_answer(item_id, choice, confidence_raw, notes,
                f"word/document.xml#paragraph[{indices[id(choice_paragraph)]}]", choice, questions)
    all_paragraphs = projection["paragraphs"]
    notes = [all_paragraphs[index] for index in (4, 5, 6, 7)]
    revisions = []
    for item_id, answer in answers.items():
        for entry in answer["note_records"]:
            match = re.search(r"Revised from ([A-E]) to ([A-E]) on re-check\.", entry["text"])
            if match:
                revisions.append({"item_id": item_id, "previous_choice": match[1],
                                  "current_choice": match[2], "record": entry})
    return {"answers": answers, "administrative_raw": metadata_rows, "completion_notes": notes,
            "free_text_sections": [{"heading": all_paragraphs[index], "contents": [all_paragraphs[index + 1]]}
                                   for index in (62, 118, 120)],
            "explicit_revisions": revisions,
            "provenance": {"origin_type": "ai_prepared_explicit", "human_provenance_accepted": False,
                "reviewer_identity": None, "expertise": None, "conflicts": None, "elapsed_minutes": None,
                "candidate_available_during_source_stage": True,
                "source_first_preservation": None, "independent_source_only_reference_accepted": False,
                "outside_material_disclosure": all_paragraphs[121],
                "administrative_missingness": "All six reviewer-detail cells are blank; no source-first export or reviewer identity/experience/time evidence."}}


def text_record(projection, questions, detailed):
    lines = projection["lines"]
    answers = {}
    starts = [(index, LINE_ITEM.fullmatch(entry["text"])) for index, entry in enumerate(lines)]
    starts = [(index, match) for index, match in starts if match]
    for position, (index, match) in enumerate(starts):
        item_id, choice, rest = match.groups()
        if item_id in answers:
            raise ValueError("Duplicate text answer")
        next_index = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        block = lines[index + 1:next_index]
        boundary = next((offset for offset, row in enumerate(block)
                         if row["text"].startswith(("Source-only summary", "PART 2", "Part 2", "Important correction"))), len(block))
        block = block[:boundary]
        confidence_raw = None
        for entry in block:
            if entry["text"].startswith("Confidence: "):
                # Preserve the returner's wording; never turn 'Moderate to high' into a form enum.
                confidence_raw = entry["text"][len("Confidence: "):].split(".", 1)[0]
        note_rows = [entry for entry in block if entry["text"]]
        answers[item_id] = record_answer(item_id, choice, confidence_raw, note_rows,
                                        lines[index]["locator"], rest, questions)
    administrative = []
    if detailed:
        administrative = [row for row in lines[:next(index for index, match in starts)] if row["text"]]
    section_headers = ("Source-only summary of important contexts and limits", "Important correction or uncertainty not captured above")
    sections = []
    for index, row in enumerate(lines):
        if row["text"] in section_headers:
            end = next((j for j in range(index + 1, len(lines)) if lines[j]["text"].startswith(("PART 2", "Part 2"))), len(lines))
            sections.append({"heading": row, "contents": lines[index + 1:end]})
    return {"answers": answers, "administrative_raw": administrative,
            "completion_notes": [], "free_text_sections": sections, "explicit_revisions": [],
            "provenance": {"origin_type": "unverified_pending_owner_confirmation", "human_provenance_accepted": False,
                "reviewer_identity": None, "expertise": None, "conflicts": None, "elapsed_minutes": None,
                "candidate_available_during_source_stage": None,
                "source_first_preservation": None, "independent_source_only_reference_accepted": False,
                "administrative_missingness": "Identity/independence/source-first sequence unverified. Response2 has administrative self-report but no measured minutes; Response3 supplies no administrative fields." if detailed else "No administrative fields, confidence, source-first timing or outside-material disclosure supplied.",
                "self_report_limit": "Part headings and claims of no prior exposure are not proof of independent source-only collection; personal metadata retained verbatim in private administrative_raw."}}


def main():
    manifest_path = INTAKE / "intake-manifest.json"
    if pin(manifest_path)["sha256"] != "64fb6fd73b2b5bd112709efc80617c0da9af60a47eb40f7fdbeae9103cd518f4":
        raise ValueError("Changed intake manifest")
    manifest = json.loads(manifest_path.read_bytes())
    packet, questions, packet_pin = form_packet()
    normalized = []
    for index, selected in enumerate(manifest["records"]):
        read_pin(selected["source"])
        read_pin(selected["preserved_original"])
        projection = json.loads(read_pin(selected["projection"]))
        value = docx_record(selected, projection, questions) if index == 0 else text_record(projection, questions, index == 1)
        if set(value["answers"]) != set(questions):
            raise ValueError("Incomplete or foreign item universe")
        value.update(submission_id=selected["submission_id"], role="evaluation_only",
                     source=selected["preserved_original"], source_projection=selected["projection"],
                     inferred_form_binding={"packet_id": packet["packet_id"], "packet": packet_pin,
                         "limit": "All18 IDs and explicit selections map to the clean mechanism form. These non-export returns supply no original packet hash, version acknowledgment or source-first timestamp."},
                     scientific_validation="not_established", adjudicated_gold=False)
        normalized.append(value)
    comparison = []
    for item_id, question in questions.items():
        selections = {row["submission_id"]: row["answers"][item_id]["choice"] for row in normalized}
        comparison.append({"item_id": item_id, "question_stem": question["stem"], "selections": selections,
                           "distinct_selections": len(set(selections.values())),
                           "interpretation": "Descriptive selection comparison only; no consensus truth or reviewer independence implied."})
    pairwise = []
    for left in range(3):
        for right in range(left + 1, 3):
            same = sum(normalized[left]["answers"][key]["choice"] == normalized[right]["answers"][key]["choice"] for key in questions)
            pairwise.append({"left": normalized[left]["submission_id"], "right": normalized[right]["submission_id"],
                             "same_selections": same, "compared_items": len(questions),
                             "not_an_independent_reviewer_agreement_statistic": True})
    confidence = Counter(answer["confidence_mapping"] for row in normalized for answer in row["answers"].values())
    destination = INTAKE / "analysis"
    destination.mkdir()
    normalized_pin = write_json(destination / "normalized-reviews-v1.json", {
        "schema_version": 1, "role": "evaluation_only", "packet": packet_pin,
        "input_manifest": pin(manifest_path), "records": normalized,
        "limits": "No adjudication, human attestation, source-first certification, reference gold or clinical/model performance."})
    comparison_pin = write_json(destination / "selection-comparison-v1.json", {
        "schema_version": 1, "role": "evaluation_only", "input": normalized_pin,
        "items": comparison, "pairwise_descriptive": pairwise,
        "confidence_completeness": dict(confidence),
        "single_choice_disagreement_limit": "The credibility options are different assessment stances, not necessarily contrary biological findings. No majority adjudication performed."})
    summary = {
        "schema_version": 1, "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "MECHANISM_SELECTIONS_NORMALIZED_PROVENANCE_UNQUALIFIED",
        "method": pin(Path(__file__).resolve()), "input_manifest": pin(manifest_path), "packet": packet_pin,
        "private_outputs": [normalized_pin, comparison_pin],
        "counts": {"files": 3, "mechanism_forms": 3, "expected_items_per_form": 18,
                   "explicit_selections": 54, "missing_selections": 0, "invalid_selections": 0,
                   "items_with_same_selection_in_all_files": sum(row["distinct_selections"] == 1 for row in comparison),
                   "items_with_differing_selections": sum(row["distinct_selections"] > 1 for row in comparison),
                   "explicit_choice_revisions_retained": sum(len(row["explicit_revisions"]) for row in normalized),
                   "ai_disclosed_files": 1, "origin_unverified_files": 2,
                   "independent_human_source_references_qualified": 0,
                   "actual_source_first_stage_exports": 0,
                   "measured_review_times": 0,
                   "genetics_forms": 0, "source_feasibility_forms": 0},
        "confidence_completeness": dict(confidence),
        "provenance": "One file explicitly discloses AI preparation and candidate visibility. Two text returns do not establish origin/independence/source-first sequence; owner clarification is pending. File agreement does not resolve those unknowns.",
        "content_findings_scope": "Returned judgments concern context preservation, applicability scope, citation support, structured population/endpoint fields, and source-level credibility. The differing credibility selection and explicit revision remain private and unresolved; no automatic consensus or exam score.",
        "gates": {"received_material": True, "mechanism_selection_extraction": True,
                  "HR2_independent_orientation_and_workload_complete": False,
                  "R07_genetics_human_assessment_complete": False, "HR3_fresh_reference_complete": False,
                  "locked_H5_complete": False, "clinical_labels_changed": False},
        "activity": {"original_modifications": 0, "model_or_native_runs": 0, "protected_outcome_reads": 0,
                     "agent_manifest_admissions": 0, "human_provenance_inference": False},
        "next": ["Resolve returner provenance and source-first chronology without treating agreement as evidence of independence.",
                 "Retain the complete original notes/revision; investigate source-level concern separately against primary literature without editing returned answers.",
                 "Keep mechanism orientation separate from missing genetics/source-feasibility exercises and fresh H5 qualification."]}
    summary_path = BASE / "RETURNED-REVIEW-COMPARISON-v1.json"
    write_json(summary_path, summary)
    markdown = """# Returned review comparison

Three owner-supplied files map to the same exposed mechanism orientation form.
All 54 requested item selections are explicit and valid for the supplied choices.
Seventeen of eighteen items have the same selection across all three files; one
credibility item differs. One explicitly disclosed selection revision is retained.
These counts describe files, not independent reviewers, consensus truth or expert
competence. No total exam score or chance-adjusted agreement is calculated.

One return explicitly says it was AI-prepared and that the candidate was visible
alongside the source task. The other two returns lack verified origin, identity,
independence and source-first sequence. No actual first-stage export or measured
review time is present. Owner provenance clarification is pending. Two complete
files include confidence, but eight values do not exactly match the form enums;
the third supplies none. Raw confidence is preserved, with no coercion.

The complete selections, explanations, metadata, free text, explicit revision and
original paragraph/line locations are stored only in the ignored evaluator intake
analysis directory. This tracked summary contains no answer matrix or personal
reviewer fields. Originals were not modified or admitted to agent inputs.

The scientifically useful issues are context preservation, citation-specific
support, intended versus observed populations, and source credibility. The single
choice difference is not automatically a disagreement about a biological fact;
its explanations must be considered without majority voting. Primary-literature
verification may inform a separate source annotation, never repair the original
response or the frozen evidence.

Receipt and extraction do not complete HR2's independent orientation/workload,
R07's separate genetics assessment, fresh HR3 references or locked H5. No genetics
or source-feasibility exercise was returned in these three files. No new model,
native run, protected outcome read, clinical label or human reference was created.
"""
    with (BASE / "RETURNED-REVIEW-COMPARISON-v1.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(markdown)
    print(json.dumps({"summary": pin(summary_path), "counts": summary["counts"],
                      "confidence": dict(confidence), "private_outputs": [normalized_pin, comparison_pin]}))


if __name__ == "__main__":
    main()
