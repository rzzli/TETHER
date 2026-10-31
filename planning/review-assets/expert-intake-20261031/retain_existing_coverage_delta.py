"""Reuse the sealed mechanism coverage; append only evaluator-only development deltas."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
INTAKE = ROOT / "data/benchmark/gold_evidence/expert-intake-20261031T160538Z"
OLD = ROOT / "data/benchmark/labels/question-development-review-20261026/attempt-v1"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


class Articles(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.field, self.text = [], None, None, []

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.row = dict(kind=dict(attrs).get("class"), heading=None, paragraphs=[], fields=[])
        elif self.row is not None and tag in ("h3", "p", "dt", "dd"):
            self.field, self.text = tag, []

    def handle_data(self, text):
        if self.field is not None:
            self.text.append(text)

    def handle_endtag(self, tag):
        if self.row is not None and tag == self.field:
            text = "".join(self.text)
            if tag == "h3":
                self.row["heading"] = text
            elif tag == "p":
                self.row["paragraphs"].append(text)
            else:
                self.row["fields"].append((tag, text))
            self.field, self.text = None, []
        if tag == "article" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def main():
    checks = []

    def check(name, value):
        checks.append(dict(id=name, passed=bool(value)))
        if not value:
            raise AssertionError(name)

    packet_path = ROOT / "docs/expert-review-20261026/Expert-review.html"
    provenance_path = ROOT / "planning/review-assets/opus-response-20261026/expert-packet-provenance.json"
    historical_closeout = ROOT / "planning/review-assets/question-pilot-controller-20261025/scientific-closeout-validation.json"
    seal_path = OLD / "adjudication/final-output-pins.json"
    coverage_path = OLD / "adjudication/adjudication.json"
    candidate_path = OLD / "candidate-original-content.txt"
    current_feedback = INTAKE / "analysis/selection-comparison-v1.json"
    current_provenance = BASE / "OWNER-PROVENANCE-NOTE-v1.json"
    credibility_path = BASE / "IL6R-SOURCE-CREDIBILITY-CHECK-v1.json"
    packet_meta = json.loads(provenance_path.read_bytes())
    candidate = json.loads(candidate_path.read_bytes())
    old = json.loads(coverage_path.read_bytes())
    seal = json.loads(seal_path.read_bytes())
    closeout = json.loads(historical_closeout.read_bytes())
    check("packet_exact_original_binding", pin(packet_path)["sha256"] == packet_meta["files"]["Expert-review.html"])
    check("candidate_exact_original_binding", pin(candidate_path)["sha256"] == packet_meta["candidate_sha256"])
    check("same_sealed_candidate_json", json.loads((OLD / "candidate-wire.json").read_bytes()) == candidate)
    check("old_adjudication_seal_matches_historical_closeout", pin(seal_path) in closeout["seals"])
    for item in seal["outputs"]:
        check("sealed_output_" + Path(item["path"]).name, pin(Path(item["path"])) == item)
    for index, item in enumerate(old["input_pins"]):
        check("sealed_input_" + str(index), pin(Path(item["path"])) == item)
    check("same_offered_view_pinned", any(p["sha256"] == packet_meta["source_view_sha256"] for p in old["input_pins"]))
    check("candidate_failed_unchanged", seal["two_task_pilot_qualifies"] is False and closeout["scientific_gate_passed"] is False)
    for index, row in enumerate(old["final_leaf_decisions"]):
        value = candidate
        for part in row["pointer"].split("/")[1:]:
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        check("same_candidate_leaf_" + str(index), type(value) is type(row["value"]) and value == row["value"] and hashlib.sha256(canonical).hexdigest() == row["value_fingerprint"]["sha256"])
    parser = Articles()
    parser.feed(packet_path.read_bytes().decode("utf-8"))
    cards = [row for row in parser.rows if row["kind"] == "source"]
    claims = [row for row in parser.rows if row["kind"] == "candidate"]
    check("same_seven_cards_two_claims", len(cards) == 7 and len(claims) == len(candidate["claims"]) == 2)
    unique, by_text = [], {}
    for index, passage in enumerate(old["source_passage_audit"]):
        text = passage["text"]
        check("offered_passage_utf8_span_" + str(index), passage["local_utf8_span"] == [0, len(text.encode("utf-8"))])
        if text not in by_text:
            by_text[text] = len(unique)
            unique.append(dict(text=text, occurrence_indices=[]))
        unique[by_text[text]]["occurrence_indices"].append(index)
    aliases = []
    for index, (card, source) in enumerate(zip(cards, unique), 1):
        check("exact_card_" + str(index), card["heading"] == "P" + str(index) and card["paragraphs"] == [source["text"]])
        aliases.append(dict(card=card["heading"], text_sha256=hashlib.sha256(source["text"].encode()).hexdigest(),
                            source_occurrence_indices=source["occurrence_indices"],
                            existing_audit_pointers=["/source_passage_audit/" + str(i) for i in source["occurrence_indices"]]))
    check("all_twelve_occurrences_indexed", sum(len(a["source_occurrence_indices"]) for a in aliases) == 12)
    for index, (shown, original) in enumerate(zip(claims, candidate["claims"])):
        check("same_candidate_text_" + str(index), shown["paragraphs"][0] == original["text"])
        actual_alias = "P" + str(index + 1)
        check("same_actual_citation_" + str(index), shown["paragraphs"][1] == "Actual cited passage: " + actual_alias + ". Applicability label: " + original["applicability"] + "." and original["quote_refs"][0]["pointer"].endswith("/" + str(index) + "/text"))
        check("same_limitation_" + str(index), shown["paragraphs"][2] == "Limitation: " + original["limitations"][0])
        expected_fields = []
        for key, value in original["proposition"].items():
            expected_fields += [("dt", key.replace("_", " ")), ("dd", "Unspecified (null)" if value is None else str(value).lower() if isinstance(value, bool) else value)]
        check("same_structured_fields_" + str(index), shown["fields"] == expected_fields)
    leaf = {row["pointer"]: "/final_leaf_decisions/" + str(i) for i, row in enumerate(old["final_leaf_decisions"])}
    columns = {
        "actual_citation": [leaf[f"/claims/{i}/quote_refs/0/pointer"] for i in range(2)],
        "proposition_support_elsewhere": ["/clause_decisions/" + str(i) for i in range(7)],
        "source_reported_model_manipulation_contrast_endpoint": ["/source_passage_audit/" + str(i) for i in (3, 5, 6, 7)],
        "proposal_versus_observation": ["/source_passage_audit/1", "/source_passage_audit/2", "/source_passage_audit/3", "/source_passage_audit/5"],
        "intended_versus_observed_population": [leaf[f"/claims/{i}/proposition/population"] for i in range(2)],
        "offered_but_omitted_fields": ["/material_issues/0", "/source_passage_audit/3", "/source_passage_audit/5", "/source_passage_audit/6", "/source_passage_audit/7"],
        "unknowns_and_source_limits": ["/original_assignment/coverage", "/limits", leaf["/claims/0/proposition/timing"], leaf["/claims/1/proposition/timing"]],
    }
    for column, pointers in columns.items():
        for pointer in pointers:
            value = old
            for part in pointer.split("/")[1:]:
                value = value[int(part)] if isinstance(value, list) else value[part]
        check("existing_column_" + column, bool(pointers))
    feedback = json.loads(current_feedback.read_bytes())
    owner = json.loads(current_provenance.read_bytes())
    credibility = json.loads(credibility_path.read_bytes())
    check("current_feedback_evaluator_only", feedback["role"] == "evaluation_only")
    check("current_credibility_evaluator_only_no_human_acceptance", credibility["role"] == "evaluation_only" and credibility["human_gate_satisfied"] is False)
    check("mixed_origin_does_not_qualify_humans", owner["owner_answer"] == "Mixed or uncertain" and all(row["qualified_human_reference"] is False for row in owner["files"]))
    item_index = {row["item_id"]: index for index, row in enumerate(feedback["items"])}
    feedback_links = {}
    for dimension, ids in dict(context_preservation=["R01", "R02", "R07"], citation_support=["R05", "R06"],
                               population=["R04"], action_context_transfer=["R03"], source_credibility=["R09"]).items():
        feedback_links[dimension] = ["/items/" + str(item_index[item]) for item in ids]
    private = dict(
        schema_version=1, role="evaluation_only", created_at_utc=datetime.now(timezone.utc).isoformat(),
        status="REUSE_SEALED_COVERAGE_WITH_CURRENT_DEVELOPMENT_DELTA",
        existing_coverage=pin(coverage_path), existing_seal=pin(seal_path), exact_candidate=pin(candidate_path),
        packet=pin(packet_path), card_aliases=aliases, requested_column_index=columns,
        counts=dict(unique_cards=7, passage_occurrences=12, candidate_claims=2, original_leaves=40, original_clauses=13, reused_columns=len(columns), new_candidate_texts=0),
        current_feedback=dict(source=pin(current_feedback), dimension_pointers=feedback_links,
            status="Unqualified development feedback only; choices/majority are not truth or independent-reference evidence."),
        provenance_delta=dict(owner_note=pin(current_provenance), human_references_qualified=0,
            effect="One disclosed AI/candidate-visible return and two mixed-or-uncertain text origins do not qualify source-first human references."),
        source_credibility_delta=dict(annotation=pin(credibility_path),
            previous_scope="Old adjudication source-fidelity analysis did not independently reopen the primary studies.",
            current_scope="Separate current AI development annotation checks the seed's internal soluble-receptor wording against cited/foundational primary reports.",
            consequences=["Keep source credibility separate from literal source support and actual-citation entailment.",
                "Do not change the frozen source cards, choices, candidate citations or old adjudication.",
                "Do not impute newly checked primary-study timing or donor details into fields missing from the offered cards.",
                "Do not charge a candidate with a source statement that the candidate did not assert."]),
        next_design_implications=["Required-findings coverage must retain offered model/manipulation/contrast/readout even when complete design/timing are unknown.",
            "Use separate actual-citation entailment, proposition support, context transfer and source-credibility assessments.",
            "Keep proposed future source-only coverage requirements prospectively defined; do not turn this exposed feedback into a locked test or corrected response."],
        limits="Pointer/alias reuse index and delta only. The existing table is not rebuilt. No primary details added to offered cards; no corrected candidate, consensus score, human acceptance, new model run or held-out claim.")
    output = INTAKE / "analysis/existing-coverage-reuse-and-delta-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(private, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    check("private_delta_is_git_ignored", subprocess.run(["git", "check-ignore", "--quiet", "--", str(output)], cwd=ROOT).returncode == 0)
    public = dict(schema_version=1, status="EXACT_SEALED_COVERAGE_REUSED_CURRENT_DELTA_ONLY",
                  checked_at_utc=datetime.now(timezone.utc).isoformat(), existing_coverage=pin(coverage_path),
                  seal=pin(seal_path), packet=pin(packet_path), private_reuse_index=pin(output),
                  counts=private["counts"], checks=checks,
                  inputs=dict(method=pin(Path(__file__)), packet_provenance=pin(provenance_path), historical_closeout=pin(historical_closeout),
                              current_feedback=pin(current_feedback), owner_provenance=pin(current_provenance), source_credibility=pin(credibility_path)),
                  method_limits="Existing AI adjudication is reused at exact same candidate/source pins, not promoted to independent truth. Public output contains counts/pins/checks only; full coverage and new feedback pointers remain evaluator-only. No corrected response or duplicate coverage table.",
                  scientific_validation=False, independent_human_reference_accepted=False,
                  protected_outcome_reads=0, model_native_runs=0, schema_controller_or_test_added=False)
    report = BASE / "EXISTING-COVERAGE-REUSE-VALIDATION-v1.json"
    with report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(public, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print(json.dumps(dict(report=pin(report), private=pin(output), checks=len(checks), counts=private["counts"])))


if __name__ == "__main__":
    main()
