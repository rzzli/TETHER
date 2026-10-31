"""Record the owner's correction separately from immutable received responses."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    source = ROOT / "docs/expert-response10312026/addendum_response1.txt"
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "c9e2578acdc48cd3b9ccefe88f80444fb232a142b42fb89e1b72526a0fbf5f31"
    manifest_path = ROOT / "data/benchmark/gold_evidence/expert-intake-20261031T160538Z/intake-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    for selected in manifest["source_inputs"]:
        assert pin(Path(selected["path"])) == selected
    at = datetime.now(timezone.utc)
    destination = manifest_path.parent / "provenance-addenda" / at.strftime("%Y%m%dT%H%M%SZ")
    destination.mkdir(parents=True)
    copied = destination / source.name
    with copied.open("xb") as stream:
        stream.write(raw)
    assert copied.read_bytes() == source.read_bytes()
    note = dict(
        schema_version=2, recorded_at_utc=at.isoformat(), role="evaluation_only",
        supersedes=pin(BASE / "OWNER-PROVENANCE-NOTE-v1.json"),
        scope="Current authorship classification for received-01 only; earlier literal observations and original responses remain unchanged.",
        owner_statement="no ai was used, that was a typpo in response 1 document",
        source_manifest=pin(manifest_path), addendum_source=pin(source), preserved_addendum=pin(copied),
        addendum_version_note=dict(
            previously_observed_sha256="ec0750e28c14a2d1f0134a5f5208a27dd325526a41d2dbfc36e541d4d757faed",
            previous_expertise_choice="2B", current_expertise_choice="2C",
            limitation="Earlier addendum bytes were observed in the tool read, not archived before the owner edited the file. Only the current version is copied here."),
        current_received_01=dict(
            author_type="human_without_ai_owner_attested", ai_used=False,
            attestation_basis="Owner's explicit conversational correction; no inference from writing style or agreement.",
            original_ai_disclosure="Owner identifies it as a typo; retained as literal historical content.",
            addendum_1B="Retained verbatim; superseded for current authorship classification by the owner's explicit no-AI clarification.",
            expertise="Other biomedical or evidence-review experience; current addendum2C self-report.",
            independence_of_other_answers="Self-reported3A; not an established two-person panel or source-first process.",
            separate_first_pass_record_available=False,
            review_minutes=45, review_time_basis="estimated_self_report_not_measured",
            conflicts="None known, self-report8A.",
            candidate_related_answers_present=True,
            source_first_chronology="unresolved: addendum4D versus existing Part2/candidate-visible statement",
            outside_material_scope="unresolved: addendum7A versus original outside-material note",
            independent_blind_source_reference_qualified=False),
        other_returns="received-02 and received-03 remain individually unverified under the owner's earlier mixed-or-uncertain statement.",
        counts=dict(owner_attested_human_authored_files=1,
                    individually_unverified_files=2, qualified_independent_source_references=0),
        qualification=dict(HR2_complete=False, R07_genetics_complete=False,
                           HR3_fresh_reference=False, locked_H5=False, clinical_validation=False),
        original_reviews_changed=False, normalized_selections_changed=False,
        agent_visible=False, model_or_native_experiment=False)
    output = BASE / "OWNER-PROVENANCE-NOTE-v2.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(note, stream, indent=2, ensure_ascii=True); stream.write("\n")
    print(json.dumps({"correction": pin(output), "preserved_addendum": pin(copied),
                      "current_authorship": note["current_received_01"]["author_type"]}))


if __name__ == "__main__":
    main()
