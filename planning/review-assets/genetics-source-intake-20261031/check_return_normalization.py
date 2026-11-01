"""Independent, stdlib-only actual-return preservation QA.

Reads only the receipt-declared intake, the source-only instrument and its source
parents, catalog role metadata, ignore policy, and receipt-pinned application files.
Does not import the coordinator normalizer or any application code. The sole
runtime write is the adjacent sanitized QA receipt; no answer text is emitted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RECEIPT = HERE / "INTAKE-RECEIPT-v1.json"
OUTPUT = HERE / "NORMALIZATION-QA-v1.json"
EXPECTED_IDS = [
    "orientation", "attribution", "design", "instruments", "estimates",
    "scale", "replication", "context", "transfer", "sufficiency",
]
VOCABULARY = {"Low", "Moderate", "High", "Cannot assess"}
ADMIN_PREFIXES = {
    "reviewer_id": "Reviewer ID", "expertise": "Expertise",
    "conflicts": "Conflicts of interest",
    "candidate_exposure": "Previously seen candidate answer",
    "workflow": "How reference prepared", "outside_material": "Outside material used",
    "additional_source_needs": "Additional source text needed",
    "overall_comments": "Overall comments",
    "elapsed_minutes": "Elapsed review time in minutes",
}
ANCHORS = {
    "docs/expert-review-genetics-20261026/Expert-source-review.html":
        "16063a14e76df1fcd98c1d9a55b8f2e1641d179fcd688e103ec38f4227692c67",
    "docs/expert-review-genetics-20261026/responses/ds_response.txt":
        "2920e189e50f161b9690217123e68fea924c3b03ad1182f45286e358b3b09ce5",
    "docs/expert-review-genetics-20261026/responses/ge_respomse.txt":
        "4bb0719846f1fad99d7c54b660e96f319e4df05a7fe31856a42ed5aa3665ef63",
    "data/cache/r07-source-revalidation-20261026-v2/source-cards.json":
        "cd5889023713fe5a8b6bc0b1de5f06c38706b3f2d750d22902bf534d215fa2fa",
    "data/cache/r07-source-revalidation-20261026-v2/prepared-request.json":
        "14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a",
}
CHECKS: list[dict] = []
COUNTS: dict[str, int] = {}
PINS: list[dict] = []


def check(name: str, passed: bool, count: int = 1) -> None:
    CHECKS.append({"check": name, "passed": bool(passed), "count": count})


def raw(path: str | Path) -> bytes:
    target = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("outside_workspace")
    return target.read_bytes()


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def object_at(path: str | Path):
    return json.loads(raw(path))


def pin(path: str | Path) -> dict:
    target = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    value = raw(target)
    return {"path": target.relative_to(ROOT).as_posix(), "bytes": len(value), "sha256": digest(value)}


def verify_declared(name: str, declared: dict) -> bytes:
    value = raw(declared["path"])
    check(name, len(value) == declared["bytes"] and digest(value) == declared["sha256"])
    PINS.append(pin(declared["path"]))
    return value


def locator(text: str, start: int, end: int) -> dict:
    return {
        "decoded_character_start": start,
        "decoded_character_end_exclusive": end,
        "lf_line_start": text.count("\n", 0, start) + 1,
        "column_start": start - text.rfind("\n", 0, start),
        "raw_text": text[start:end],
    }


def field_matches(text: str, prefix: str) -> list:
    return list(re.finditer(r"^" + re.escape(prefix) + r": (?P<value>[^\r\n]*)", text, re.M))


def mentions(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\bP\d{2}\b", text)))


def expected_response(text: str, item: dict, ordinal: int, choice: str,
                      label: str, selection_span: tuple[int, int], rationale_span: tuple[int, int],
                      confidence_match=None, passage_match=None) -> dict:
    canonical = {option["value"]: option["label"] for option in item["options"]}
    confidence = confidence_match.group("value") if confidence_match else None
    passage_text = passage_match.group("value") if passage_match else None
    rationale = text[slice(*rationale_span)]
    return {
        "item_id": item["id"], "ordinal": ordinal, "selection": choice,
        "canonical_option_label": canonical[choice], "returned_option_label": label,
        "returned_label_matches_canonical": label == canonical[choice],
        "selection_locator": locator(text, *selection_span),
        "confidence": confidence,
        "confidence_matches_form_vocabulary": confidence in VOCABULARY if confidence is not None else None,
        "confidence_locator": locator(text, *confidence_match.span("value")) if confidence_match else None,
        "passage_ids_field": re.findall(r"\bP\d{2}\b", passage_text) if passage_text is not None else None,
        "passage_field_locator": locator(text, *passage_match.span("value")) if passage_match else None,
        "rationale": rationale, "rationale_locator": locator(text, *rationale_span),
        "rationale_passage_mentions": mentions(rationale),
    }


def parse_ds(text: str, items: list[dict]) -> tuple[list[dict], dict]:
    choices = list(re.finditer(r"^Selected: (option_\d+) — ([^\r\n]+)", text, re.M))
    confidence = field_matches(text, "Confidence")
    passages = field_matches(text, "Passages")
    rationale = field_matches(text, "Rationale")
    check("record_01_parse_cardinality", all(len(x) == 10 for x in (choices, confidence, passages, rationale)), 40)
    if not all(len(x) == 10 for x in (choices, confidence, passages, rationale)):
        raise ValueError("record_01_parse_cardinality")
    responses = []
    for i, (choice, conf, passage, why, item) in enumerate(zip(choices, confidence, passages, rationale, items), 1):
        lines = [text.count("\n", 0, x.start()) + 1 for x in (choice, conf, passage, why)]
        check("record_01_block_field_alignment", lines == list(range(lines[0], lines[0] + 4)), 4)
        responses.append(expected_response(text, item, i, choice[1], choice[2], choice.span(),
                                           why.span("value"), conf, passage))
    admin = {}
    for key, prefix in ADMIN_PREFIXES.items():
        found = field_matches(text, prefix)
        check("record_01_admin_field_cardinality", len(found) == 1)
        if len(found) != 1:
            raise ValueError("record_01_admin_field_cardinality")
        match = found[0]
        admin[key] = {"value": match.group("value"), "locator": locator(text, *match.span("value"))}
    return responses, admin


def parse_ge(text: str, items: list[dict]) -> tuple[list[dict], dict]:
    # Locate only the prefix; a balanced scan preserves parentheses inside labels.
    headings = list(re.finditer(r"\bItem (\d+): (option_\d+) \(", text))
    check("record_02_parse_cardinality", len(headings) == 10 and [int(x[1]) for x in headings] == list(range(1, 11)), 10)
    if len(headings) != 10:
        raise ValueError("record_02_parse_cardinality")
    responses = []
    for i, (heading, item) in enumerate(zip(headings, items)):
        opening = heading.end() - 1
        depth, closing = 0, None
        for position in range(opening, len(text)):
            if text[position] == "(":
                depth += 1
            elif text[position] == ")":
                depth -= 1
                if depth == 0:
                    closing = position
                    break
        if closing is None:
            raise ValueError("record_02_unbalanced_label")
        start = closing + 1
        stop = headings[i + 1].start() if i < 9 else len(text)
        while start < stop and text[start].isspace():
            start += 1
        while stop > start and text[stop - 1].isspace():
            stop -= 1
        responses.append(expected_response(text, item, i + 1, heading[2], text[opening + 1:closing],
                                           (heading.start(), closing + 1), (start, stop)))
    check("record_02_midline_heading_preservation", sum(x["selection_locator"]["column_start"] > 1 for x in responses) == 9, 9)
    check("record_02_nested_label_parentheses_preservation", "(" in responses[0]["returned_option_label"] and responses[0]["returned_option_label"].endswith(")"))
    check("record_02_optional_admin_fields_absent", all(not field_matches(text, prefix) for prefix in ADMIN_PREFIXES.values()), 9)
    check("record_02_optional_confidence_passage_fields_absent", not field_matches(text, "Confidence") and not field_matches(text, "Passages"), 20)
    return responses, {key: None for key in ADMIN_PREFIXES}


class InstrumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fieldsets, self.passages, self.pres, self.selects = [], [], [], []
        self.current_fieldset = self.current_passage = self.current_choice = None
        self.current_select = self.current_option = None
        self.in_legend = self.in_span = self.in_blockquote = self.in_heading = self.in_pointer = False
        self.current_pre = None
        self.checked = self.selected = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "fieldset":
            self.current_fieldset = {"legend": "", "choices": []}
        elif tag == "legend":
            self.in_legend = True
        elif tag == "input" and attrs.get("type") == "radio":
            self.checked += int("checked" in attrs)
            self.current_choice = {"id": attrs["name"], "value": attrs["value"], "label": ""}
            self.current_fieldset["choices"].append(self.current_choice)
        elif tag == "span" and self.current_choice is not None:
            self.in_span = True
        elif tag == "article" and re.fullmatch(r"P\d{2}", attrs.get("id", "")):
            self.current_passage = {"id": attrs["id"], "heading": "", "text": "", "pointer": ""}
        elif tag == "h3" and self.current_passage is not None:
            self.in_heading = True
        elif tag == "blockquote" and self.current_passage is not None:
            self.in_blockquote = True
        elif tag == "p" and attrs.get("class") == "pointer" and self.current_passage is not None:
            self.in_pointer = True
        elif tag == "pre":
            self.current_pre = ""
        elif tag == "select":
            self.current_select = {"id": attrs["id"], "options": []}
        elif tag == "option" and self.current_select is not None:
            self.selected += int("selected" in attrs)
            self.current_option = {"value": attrs.get("value"), "text": ""}

    def handle_data(self, value):
        if self.in_legend:
            self.current_fieldset["legend"] += value
        if self.in_span:
            self.current_choice["label"] += value
        if self.in_heading:
            self.current_passage["heading"] += value
        if self.in_blockquote:
            self.current_passage["text"] += value
        if self.in_pointer:
            self.current_passage["pointer"] += value
        if self.current_pre is not None:
            self.current_pre += value
        if self.current_option is not None:
            self.current_option["text"] += value

    def handle_endtag(self, tag):
        if tag == "legend":
            self.in_legend = False
        elif tag == "span":
            self.in_span = False
            self.current_choice = None
        elif tag == "fieldset" and self.current_fieldset is not None:
            self.fieldsets.append(self.current_fieldset)
            self.current_fieldset = None
        elif tag == "h3":
            self.in_heading = False
        elif tag == "blockquote":
            self.in_blockquote = False
        elif tag == "p":
            self.in_pointer = False
        elif tag == "article" and self.current_passage is not None:
            self.passages.append(self.current_passage)
            self.current_passage = None
        elif tag == "pre" and self.current_pre is not None:
            self.pres.append(self.current_pre)
            self.current_pre = None
        elif tag == "option" and self.current_option is not None:
            self.current_select["options"].append(self.current_option)
            self.current_option = None
        elif tag == "select" and self.current_select is not None:
            self.selects.append(self.current_select)
            self.current_select = None


def validate_instrument(receipt: dict) -> tuple[dict, list[dict], set[str]]:
    html = verify_declared("instrument_file_pin", receipt["form"]).decode("utf-8-sig")
    cards_bytes = verify_declared("source_cards_file_pin", receipt["source_cards"])
    request_bytes = verify_declared("source_request_file_pin", receipt["request"])
    cards, request = json.loads(cards_bytes), json.loads(request_bytes)
    meta = json.loads(re.search(r"const META=(.*?);\s*const ITEMS=", html, re.S)[1])
    items = json.loads(re.search(r"const ITEMS=(.*?);\s*function field", html, re.S)[1])
    check("instrument_item_ids_and_cardinality", [x["id"] for x in items] == EXPECTED_IDS, 10)
    check("instrument_option_ids_and_cardinality", all([x["value"] for x in item["options"]] ==
          ["option_1", "option_2", "option_3", "option_4", "option_5", "cannot_assess", "outside_expertise"] for item in items), 70)
    check("instrument_meta_source_pins", meta["source_cards_sha256"] == digest(cards_bytes) and
          meta["request_file_sha256"] == meta["request_sha256"] == digest(request_bytes), 3)
    check("instrument_question_case_binding", meta["question"] == cards["question"] == request["question"] and
          meta["case_id"] == cards["case"]["case_id"] and cards["case"] == request["source_request"]["case"] and
          all(meta[key] == request[key] for key in ("question_key", "hypothesis_key")) and
          meta["form_id"] == receipt["form_id"] and meta["role"] == "evaluation_only")
    expected_sources = [{"alias": x["source_alias"], "observation_id": x["observation_id"], "admitted_sha256": x["admitted_sha256"]} for x in cards["cards"]]
    check("instrument_source_identity_binding", meta["source_ids"] == expected_sources)
    check("source_cards_request_binding", cards["request_sha256"] == digest(request_bytes))
    parser = InstrumentParser()
    parser.feed(html)
    form_sets = [x for x in parser.fieldsets if re.match(r"^\d+\. ", x["legend"])]
    expected_sets = [{"legend": f"{i}. {item['question']}", "choices":
                     [{"id": item["id"], **option} for option in item["options"]]} for i, item in enumerate(items, 1)]
    check("instrument_rendered_choices_equal_items", form_sets == expected_sets, 70)
    expected_selects = [{"id": item["id"] + "-confidence", "options":
                        [{"value": "", "text": "Choose if useful"}] +
                        [{"value": None, "text": value} for value in ("Low", "Moderate", "High", "Cannot assess")]} for item in items]
    check("instrument_confidence_vocabulary", parser.selects == expected_selects, 10)
    check("instrument_no_preselected_choices", parser.checked == 0 and parser.selected == 0)
    check("instrument_embedded_record_equals_source_cards", len(parser.pres) == 2 and json.loads(parser.pres[1]) == cards)
    check("instrument_structured_context_equals_source", json.loads(parser.pres[0]) == cards["cards"][0]["scientific_context"])
    check("source_record_and_passage_cardinality", len(cards["cards"]) == 1 and len(cards["cards"][0]["reported_passages"]) == 13 and len(parser.passages) == 13, 13)
    source = cards["cards"][0]
    expected_passages = [{"id": f"P{i + 1:02d}", "heading": f"P{i + 1:02d} · {p['section']}",
                          "text": p["text"], "pointer": f"{source['source_alias']} /source_metrics/textMiningSentences/{i}/text"}
                         for i, p in enumerate(source["reported_passages"])]
    check("rendered_passages_exact_source_order_and_text", parser.passages == expected_passages, 13)
    check("source_passages_equal_retained_scientific_record", source["reported_passages"] == source["scientific_record"]["source_metrics"]["textMiningSentences"], 13)
    check("source_passage_text_hashes_equal", [digest(x["text"].encode()) for x in parser.passages] ==
          [digest(x["text"].encode()) for x in source["reported_passages"]], 13)
    COUNTS.update(instrument_items=len(items), instrument_rendered_options=sum(len(x["options"]) for x in items), source_passages=len(parser.passages))
    return meta, items, {x["id"] for x in parser.passages}


def main() -> None:
    receipt = object_at(RECEIPT)
    PINS.extend([pin(RECEIPT), pin(Path(__file__))])
    check("independently_retained_input_anchors", all(digest(raw(path)) == expected for path, expected in ANCHORS.items()), len(ANCHORS))
    check("receipt_qualification_limits", receipt["agent_visible"] is False and receipt["adjudicated_gold"] is False and
          receipt["independent_reference_certified"] is False and receipt["R07_complete"] is False and
          receipt["model_calls"] == 0 and receipt["provider_spending_usd"] == 0)
    manifest = json.loads(verify_declared("private_manifest_pin", receipt["intake_manifest"]))
    owner = json.loads(verify_declared("owner_provenance_pin", receipt["owner_round_provenance"]))
    verify_declared("coordinator_normalizer_pin_only_not_executed", receipt["normalizer"])
    check("manifest_receipt_records_equal", manifest["records"] == receipt["records"] and manifest["owner_round_provenance"] == receipt["owner_round_provenance"], 2)
    check("manifest_source_parents_equal", manifest["parents"] == [receipt[x] for x in ("form", "source_cards", "request")], 3)
    check("manifest_evaluation_only_boundary", manifest["role"] == "evaluation_only" and manifest["agent_visible"] is False and manifest["adjudicated_gold"] is False and
          manifest["catalog_intent"] == ["gold_evidence", "panel_ratings"])
    check("owner_provenance_separate_evaluation_record", owner["role"] == "evaluation_only" and owner["agent_visible"] is False and owner["adjudicated_gold"] is False and
          isinstance(owner["owner_statement_verbatim"], str) and bool(owner["owner_statement_verbatim"]))
    interpretation = owner["interpretation"]
    unknown_keys = ["ai_use_confirmed_per_file", "ai_context_and_model", "mapping_to_R1_R2_R3", "independence_of_GE", "DS_measured_vs_estimated", "GE_elapsed_minutes"]
    check("owner_round_unknowns_preserved", all(interpretation[key] is None for key in unknown_keys), 6)
    check("owner_background_qualifications_retained", all(token in interpretation["ds_response.txt"] for token in ("PhD", "biology", "non-computational")) and
          all(token in interpretation["ge_respomse.txt"] for token in ("PhD", "bioinformatics", "genetics")) and
          all(token in interpretation["authorship"] for token in ("possible AI assistance", "degree unknown")))
    meta, items, valid_passages = validate_instrument(receipt)
    private_paths = [receipt["intake_manifest"]["path"], receipt["owner_round_provenance"]["path"]]
    all_expected, normalized_records = [], []
    expected_ref_ids = ["GSR-20261031-01", "GSR-20261031-02"]
    check("intake_record_ids_and_cardinality", [x["source_reference_id"] for x in receipt["records"]] == expected_ref_ids, 2)
    for index, record in enumerate(receipt["records"], 1):
        prefix = f"record_{index:02d}"
        source = verify_declared(prefix + "_source_file_pin", record["source"])
        original = verify_declared(prefix + "_preserved_original_pin", record["preserved_original"])
        normalized = json.loads(verify_declared(prefix + "_normalized_file_pin", record["normalized"]))
        normalized_records.append(normalized)
        private_paths.extend(record[key]["path"] for key in ("source", "preserved_original", "normalized"))
        check(prefix + "_byte_identical_original", source == original)
        text = original.decode("utf-8-sig")
        check(prefix + "_full_raw_text_preserved", normalized["raw_text"] == text and text.encode("utf-8") == original)
        check(prefix + "_crlf_and_unterminated_last_line_preserved", b"\r\r\n" not in original and original.count(b"\n") == original.count(b"\r\n") and not original.endswith(b"\n"))
        expected, admin = (parse_ds if index == 1 else parse_ge)(text, items)
        all_expected.append(expected)
        check(prefix + "_all_response_values_and_exact_schema", normalized["responses"] == expected, 10)
        check(prefix + "_all_admin_values_and_locators", normalized["returned_admin"] == admin, 9)
        check(prefix + "_instrument_meta_binding", normalized["instrument"] == meta)
        check(prefix + "_form_and_original_metadata", normalized["form"] == receipt["form"] and normalized["original"] == record["preserved_original"])
        check(prefix + "_return_identity_not_inferred", all(normalized[x] is None for x in ("canonical_reviewer_id", "prior_round_alias", "original_exported_at_utc")) and normalized["native_form_export"] is False, 4)
        check(prefix + "_evaluator_only_unadjudicated", normalized["role"] == record["role"] == "evaluation_only" and normalized["agent_visible"] is record["agent_visible"] is False and normalized["adjudicated_gold"] is False)
        check(prefix + "_reference_id_binding", normalized["source_reference_id"] == record["source_reference_id"] and normalized["schema_version"] == 1)
        check(prefix + "_coordinator_binding_labeled", "Coordinator" in normalized["binding_basis"] and "no embedded export fingerprints" in normalized["binding_basis"])
        check(prefix + "_locator_convention", normalized["locator_convention"] == "Offsets count Unicode characters in UTF-8-sig-decoded original including CRLF; LF-delimited 1-based lines/columns.")
        check(prefix + "_passage_ids_valid_and_order_preserved", all(set(x["passage_ids_field"] or []) <= valid_passages and set(x["rationale_passage_mentions"]) <= valid_passages for x in expected), 10)
        for key in ("selection_locator", "confidence_locator", "passage_field_locator", "rationale_locator"):
            values = [x[key] for x in normalized["responses"] if x[key] is not None]
            check(prefix + "_" + key + "_independent_slice_recheck", all(value == locator(text, value["decoded_character_start"], value["decoded_character_end_exclusive"]) for value in values), len(values))
        check(prefix + "_admin_locator_slice_recheck", all(value is None or value["locator"] == locator(text, value["locator"]["decoded_character_start"], value["locator"]["decoded_character_end_exclusive"]) for value in normalized["returned_admin"].values()), 9)
    check("owner_elapsed_matches_returned_self_report", str(interpretation["DS_elapsed_minutes_self_reported"]) == normalized_records[0]["returned_admin"]["elapsed_minutes"]["value"])
    check("explicit_blank_reviewer_id_preserved_without_alias", bool(normalized_records[0]["returned_admin"]["reviewer_id"]["value"]) and normalized_records[0]["canonical_reviewer_id"] is None)
    expected_counts = {
        "originals": 2, "original_bytes": sum(x["source"]["bytes"] for x in receipt["records"]),
        "items_per_return": len(items), "valid_selections": sum(len(x) for x in all_expected),
        "same_selections": sum(a["selection"] == b["selection"] for a, b in zip(*all_expected)),
        "different_selection_item_ids": [a["item_id"] for a, b in zip(*all_expected) if a["selection"] != b["selection"]],
        "confidence_missing": sum(x["confidence"] is None for group in all_expected for x in group),
        "confidence_nonstandard_preserved": sum(x["confidence_matches_form_vocabulary"] is False for group in all_expected for x in group),
        "source_passages": len(valid_passages),
    }
    check("receipt_aggregate_counts_recomputed", receipt["counts"] == expected_counts)
    COUNTS.update({k: v for k, v in expected_counts.items() if isinstance(v, int)})
    COUNTS.update(different_selections=len(expected_counts["different_selection_item_ids"]),
                  returned_label_exact=sum(x["returned_label_matches_canonical"] for group in all_expected for x in group),
                  returned_label_variants=sum(not x["returned_label_matches_canonical"] for group in all_expected for x in group),
                  rationales_checked=sum(bool(x["rationale"]) for group in all_expected for x in group),
                  passage_fields_missing=sum(x["passage_ids_field"] is None for group in all_expected for x in group),
                  admin_fields_checked=18, private_artifacts_checked=len(private_paths))
    # Binary NUL framing avoids Windows text-mode CRLF translation creating
    # queries for paths with a literal trailing carriage return.
    ignore = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"], cwd=ROOT,
                            input=("\0".join(private_paths) + "\0").encode("utf-8"),
                            capture_output=True, check=False)
    ignored_paths = {value.decode("utf-8") for value in ignore.stdout.split(b"\0") if value}
    check("private_artifacts_git_ignored", ignore.returncode == 0 and ignored_paths == set(private_paths), len(private_paths))
    tracked = subprocess.run(["git", "ls-files", "--cached", "--", *private_paths], cwd=ROOT, text=True, capture_output=True, check=False)
    check("private_artifacts_not_git_tracked", tracked.returncode == 0 and not tracked.stdout.strip(), len(private_paths))
    ignore_policy = raw("data/.gitignore").decode("utf-8-sig")
    check("evaluation_directory_ignore_policy", "/benchmark/**" in ignore_policy and "!/benchmark/**/.gitkeep" in ignore_policy)
    catalog_path = "data/catalog/sources.json"
    catalog = object_at(catalog_path)
    PINS.extend([pin(catalog_path), pin("data/.gitignore")])
    roles = [x for x in catalog["datasets"] if x["dataset_id"] in {"gold_evidence", "panel_ratings"}]
    check("catalog_evaluation_roles_and_agent_exclusion", len(roles) == 2 and all(x["roles"] == ["evaluation_only"] and x["profile_policy"]["contemporary_assessment"] == "excluded_from_agent_inputs" and x["profile_policy"]["historical_benchmark"] == "evaluator_only" for x in roles), 2)
    applications = receipt["application_checks"]
    check("application_pin_cardinality", len(applications) == 327 and len({x["path"] for x in applications}) == 327, 327)
    matches = [digest(raw(entry["path"])) == entry["sha256"] for entry in applications]
    check("all_application_pins_unchanged", all(matches), len(matches))
    COUNTS.update(application_pins_checked=len(matches), application_pins_matched=sum(matches), catalog_evaluation_roles_checked=len(roles))
    PINS.append({"path": "receipt_application_pin_set", "sha256": digest(json.dumps([{"path": x["path"], "sha256": x["sha256"]} for x in applications], sort_keys=True, separators=(",", ":")).encode())})


if __name__ == "__main__":
    error_type = None
    try:
        main()
    except Exception as error:
        error_type = type(error).__name__
        check("validation_completed_without_infrastructure_error", False)
    passed = error_type is None and all(x["passed"] for x in CHECKS)
    result = {
        "schema_version": 1,
        "status": "PASS_INDEPENDENT_MECHANICAL_NORMALIZATION_QA" if passed else "FAIL_INDEPENDENT_MECHANICAL_NORMALIZATION_QA",
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Independent actual-data preservation, instrument binding and normalization QA; no scientific adjudication or independent-human-reference certification.",
        "role": "evaluation_only", "agent_visible": False, "adjudicated_gold": False,
        "independent_reference_certified": False, "full_tests_rerun": False,
        "model_calls": 0, "provider_spending_usd": 0,
        "interpreter": Path(sys.executable).relative_to(ROOT).as_posix(),
        "checks": CHECKS, "counts": COUNTS,
        "pins": list({entry["path"]: entry for entry in PINS}.values()),
        "failure_check_names": sorted({x["check"] for x in CHECKS if not x["passed"]}),
        "infrastructure_error_type": error_type,
        "sanitization": "Check names, aggregate counts and input pins only; no reviewer selections, rationales, labels, confidence strings or owner statement text.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "checks": len(CHECKS), "failed_checks": len(result["failure_check_names"]), "infrastructure_error_type": error_type}))
    sys.exit(0 if passed else 1)
