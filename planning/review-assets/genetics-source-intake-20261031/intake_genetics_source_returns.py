"""One-off evaluator-only intake of two supplied TXT reviews; no agent admission."""
from datetime import datetime, timezone
from html import unescape
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/expert-review-genetics-20261026"
EXPECTED = {
    "ds_response.txt": "2920e189e50f161b9690217123e68fea924c3b03ad1182f45286e358b3b09ce5",
    "ge_respomse.txt": "4bb0719846f1fad99d7c54b660e96f319e4df05a7fe31856a42ed5aa3665ef63",
}


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write("\n")
    return pin(path)


def span(text, start, end):
    return {"decoded_character_start": start, "decoded_character_end_exclusive": end,
            "lf_line_start": text.count("\n", 0, start) + 1,
            "column_start": start - text.rfind("\n", 0, start),
            "raw_text": text[start:end]}


def field(text, label):
    match = re.search(r"(?m)^" + re.escape(label) + r": ([^\r\n]*)", text)
    return None if match is None else {"value": match[1], "locator": span(text, match.start(1), match.end(1))}


def normalize(text, items, name):
    records = []
    if name == "ds_response.txt":
        markers = list(re.finditer(r"(?m)^Selected: (option_\d+|cannot_assess|outside_expertise) ([^\r\n]+)", text))
    else:
        markers = list(re.finditer(r"Item (\d+): (option_\d+|cannot_assess|outside_expertise) (\([^\r\n]+\))(?=\r?\n)", text))
        assert [int(match[1]) for match in markers] == list(range(1, len(items) + 1))
    assert len(markers) == len(items) == 10
    for index, (item, match) in enumerate(zip(items, markers)):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        block = text[match.end():end]
        selection = match[1] if name == "ds_response.txt" else match[2]
        options = {option["value"]: option["label"] for option in item["options"]}
        assert selection in options
        raw_label = match[2].removeprefix("\u2014 ") if name == "ds_response.txt" else match[3][1:-1]
        if name == "ds_response.txt":
            confidence = re.search(r"(?m)^Confidence: ([^\r\n]+)", block)
            passages = re.search(r"(?m)^Passages: ([^\r\n]+)", block)
            rationale = re.search(r"(?m)^Rationale: ([^\r\n]+)", block)
            assert confidence and passages and rationale
            confidence_value = confidence[1]
            passage_ids = [entry.strip() for entry in passages[1].split(",")]
            assert len(passage_ids) == len(set(passage_ids))
            assert all(re.fullmatch(r"P(?:0[1-9]|1[0-3])", value) for value in passage_ids)
            rationale_start = match.end() + rationale.start(1)
            rationale_end = match.end() + rationale.end(1)
            confidence_locator = span(text, match.end() + confidence.start(1), match.end() + confidence.end(1))
            passage_locator = span(text, match.end() + passages.start(1), match.end() + passages.end(1))
        else:
            confidence_value = None
            passage_ids = None
            confidence_locator = passage_locator = None
            rationale_start = match.end()
            while rationale_start < end and text[rationale_start].isspace():
                rationale_start += 1
            rationale_end = end
            while rationale_end > rationale_start and text[rationale_end - 1].isspace():
                rationale_end -= 1
        assert rationale_end > rationale_start
        records.append({
            "item_id": item["id"], "ordinal": index + 1, "selection": selection,
            "canonical_option_label": options[selection], "returned_option_label": raw_label,
            "returned_label_matches_canonical": raw_label == options[selection],
            "selection_locator": span(text, match.start(), match.end()),
            "confidence": confidence_value,
            "confidence_matches_form_vocabulary": None if confidence_value is None else confidence_value in ("Low", "Moderate", "High", "Cannot assess"),
            "confidence_locator": confidence_locator,
            "passage_ids_field": passage_ids, "passage_field_locator": passage_locator,
            "rationale": text[rationale_start:rationale_end],
            "rationale_locator": span(text, rationale_start, rationale_end),
            "rationale_passage_mentions": re.findall(r"\bP(?:0[1-9]|1[0-3])\b", text[rationale_start:rationale_end]),
        })
    admin = {key: field(text, label) for key, label in {
        "reviewer_id": "Reviewer ID", "expertise": "Expertise", "conflicts": "Conflicts of interest",
        "candidate_exposure": "Previously seen candidate answer", "workflow": "How reference prepared",
        "outside_material": "Outside material used", "additional_source_needs": "Additional source text needed",
        "overall_comments": "Overall comments", "elapsed_minutes": "Elapsed review time in minutes",
    }.items()}
    return {"responses": records, "returned_admin": admin}


def main():
    form = SOURCE / "Expert-source-review.html"
    text = form.read_bytes().decode("utf-8")
    meta = json.loads(re.search(r"const META=(.*?);\s*\n", text)[1])
    items = json.loads(re.search(r"const ITEMS=(.*?);\s*\n", text)[1])
    original_meta = json.loads((ROOT / "planning/review-assets/recovery-step7-20261026/addendum-review/form-metadata.json").read_bytes())
    assert meta == original_meta["metadata"] and items == original_meta["items"]
    cards_path = ROOT / "data/cache/r07-source-revalidation-20261026-v2/source-cards.json"
    request_path = cards_path.parent / "prepared-request.json"
    assert pin(cards_path)["sha256"] == meta["source_cards_sha256"]
    assert pin(request_path)["sha256"] == meta["request_file_sha256"]
    cards = json.loads(cards_path.read_bytes())
    passages = re.findall(r'<article class="passage" id="(P\d+)">.*?<blockquote>(.*?)</blockquote>', text, re.S)
    assert [row[0] for row in passages] == [f"P{i:02}" for i in range(1, 14)]
    assert [unescape(row[1]) for row in passages] == [row["text"] for row in cards["cards"][0]["reported_passages"]]
    for name, digest in EXPECTED.items():
        assert pin(SOURCE / "responses" / name)["sha256"] == digest
    now = datetime.now(timezone.utc)
    out = ROOT / "data/benchmark/gold_evidence" / ("genetics-source-intake-" + now.strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir()
    (out / "originals").mkdir()
    (out / "normalized").mkdir()
    records = []
    for index, name in enumerate(EXPECTED, 1):
        source = SOURCE / "responses" / name
        original = source.read_bytes()
        target = out / "originals" / name
        with target.open("xb") as stream:
            stream.write(original)
        assert target.read_bytes() == original
        raw_text = original.decode("utf-8-sig")
        assert "\ufffd" not in raw_text
        ref = f"GSR-20261031-{index:02}"
        result = normalize(raw_text, items, name)
        result.update({"schema_version": 1, "source_reference_id": ref,
                       "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
                       "instrument": meta, "form": pin(form), "original": pin(target),
                       "binding_basis": "Coordinator matched all ten numbered selections to pinned instrument; supplied TXT has no embedded export fingerprints.",
                       "native_form_export": False, "original_exported_at_utc": None,
                       "canonical_reviewer_id": None, "prior_round_alias": None,
                       "reviewer_id_missing_reason": "Blank or absent in return; no mapping to orientation aliases supplied.",
                       "locator_convention": "Offsets count Unicode characters in UTF-8-sig-decoded original including CRLF; LF-delimited 1-based lines/columns.",
                       "raw_text": raw_text})
        normalized = save(out / "normalized" / (ref + ".json"), result)
        records.append({"source_reference_id": ref, "source": pin(source), "preserved_original": pin(target),
                        "normalized": normalized, "items_answered": len(result["responses"]),
                        "role": "evaluation_only", "agent_visible": False})
    owner = save(out / "owner-round-provenance-v1.json", {
        "schema_version": 1, "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
        "recorded_at_utc": now.isoformat(), "statement_source": "Owner answer in this chat; receipt time is not reviewer completion time.",
        "owner_statement_verbatim": "one is an non - computational phd level background in bio for ds, the othe is mixed with bioinformatics, genetics , also phd level, they may use ai to assist them in finalizing but unknow degree",
        "interpretation": {"ds_response.txt": "Owner-described PhD-level biology background, non-computational.",
                           "ge_respomse.txt": "Owner-described PhD-level mixed bioinformatics/genetics background.",
                           "authorship": "Owner describes two reviewers; possible AI assistance during finalization, degree unknown.",
                           "ai_use_confirmed_per_file": None, "ai_context_and_model": None,
                           "mapping_to_R1_R2_R3": None, "independence_of_GE": None,
                           "DS_elapsed_minutes_self_reported": 25, "DS_measured_vs_estimated": None,
                           "GE_elapsed_minutes": None},
        "supersession": "Possible assistance qualifies the DS return's outside-material none statement; neither original is rewritten. Prior-round attestations are not copied into this round."})
    manifest = save(out / "intake-manifest.json", {
        "schema_version": 1, "received_at_utc": now.isoformat(), "role": "evaluation_only",
        "agent_visible": False, "adjudicated_gold": False, "form_id": meta["form_id"],
        "classification": "unadjudicated_source_review_development_intake", "records": records,
        "parents": [pin(form), pin(cards_path), pin(request_path)], "owner_round_provenance": owner,
        "independent_human_reference_qualification": "Not certified by file receipt or normalization.",
        "catalog_intent": ["gold_evidence", "panel_ratings"],
        "downstream_rule": "Every generated descendant remains evaluation_only; no source graph, agent manifest or model input is authorized."})
    normalized_records = [json.loads((ROOT / row["normalized"]["path"]).read_bytes()) for row in records]
    differences = [a["item_id"] for a, b in zip(normalized_records[0]["responses"], normalized_records[1]["responses"]) if a["selection"] != b["selection"]]
    accepted = json.loads((ROOT / "planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json").read_bytes())
    source_checks = [{"path": name, "sha256": pin(ROOT / name)["sha256"], "matches": pin(ROOT / name)["sha256"] == digest}
                     for name, digest in accepted["source_pins"].items()]
    assert len(source_checks) == 327 and all(row["matches"] for row in source_checks)
    receipt = save(HERE / "INTAKE-RECEIPT-v1.json", {
        "schema_version": 1, "status": "PASS_PRESERVATION_AND_COORDINATOR_BINDING_ONLY",
        "at_utc": now.isoformat(), "intake_manifest": manifest, "records": records,
        "owner_round_provenance": owner, "normalizer": pin(Path(__file__)),
        "form": pin(form), "form_id": meta["form_id"], "source_cards": pin(cards_path), "request": pin(request_path),
        "counts": {"originals": 2, "original_bytes": sum(row["source"]["bytes"] for row in records),
                   "items_per_return": 10, "valid_selections": 20, "same_selections": 10 - len(differences),
                   "different_selection_item_ids": differences, "confidence_missing": 10,
                   "confidence_nonstandard_preserved": 2, "source_passages": 13},
        "scope": "Mechanical receipt and descriptive comparison, not answer key, rater reliability, adjudication or scientific acceptance.",
        "application_checks": source_checks, "full_tests_rerun": False, "retained_application_tests": 1774,
        "runtime_changed": False, "catalog_changed": False, "agent_visible": False, "adjudicated_gold": False,
        "independent_reference_certified": False, "R07_complete": False,
        "model_calls": 0, "provider_spending_usd": 0,
        "next_step": "Separate candidate follow-up linked to retained reference IDs, preserving round-specific unknown exposure/assistance; no candidate content was read in this intake."})
    print(json.dumps({"receipt": receipt, "manifest": manifest, "records": records, "application_pins_match": len(source_checks)}))


if __name__ == "__main__":
    main()
