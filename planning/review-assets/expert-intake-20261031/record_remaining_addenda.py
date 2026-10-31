"""Preserve addenda 2/3 and the owner's confirmation of three distinct reviewers."""
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
    prior_path = BASE / "OWNER-PROVENANCE-NOTE-v2.json"
    prior = json.loads(prior_path.read_bytes())
    intake = ROOT / "data/benchmark/gold_evidence/expert-intake-20261031T160538Z"
    manifest = json.loads((intake / "intake-manifest.json").read_bytes())
    for selected in manifest["source_inputs"]:
        assert pin(Path(selected["path"])) == selected
    sources = [ROOT / "docs/expert-response10312026" / f"addendum_response{i}.txt" for i in (2, 3)]
    expected = "6f45b77b227ab680b394a355daa3f3bf882e25132c3d3e8bb40d789151030c53"
    assert all(pin(path)["sha256"] == expected for path in sources)
    at = datetime.now(timezone.utc)
    folder = intake / "provenance-addenda" / at.strftime("%Y%m%dT%H%M%SZ")
    folder.mkdir()
    records = []
    for number, source in zip((2, 3), sources):
        copied = folder / source.name
        with copied.open("xb") as stream:
            stream.write(source.read_bytes())
        assert copied.read_bytes() == source.read_bytes()
        records.append(dict(
            submission_id=f"received-0{number}", reviewer_alias=f"R{number}",
            source=pin(source), preserved_addendum=pin(copied),
            author_type="human_with_ai_assistance_self_reported", ai_assistance=True,
            expertise="Statistical genetics/epidemiology, self-report2B",
            independent_of_other_answers="Yes, self-report3A",
            source_before_candidate="Yes, self-report4A; procedural disclosure, not externally certified blinding",
            separate_first_pass_record_available=False,
            review_minutes=45, review_time_basis="estimated_self_report_not_measured",
            additional_inputs=["outside_sources", "AI_tools"], tool_name_reported="Claude Code",
            assistant_context_or_model_version=None, assistance_cost=None,
            assistance_unknowns_reason="Not supplied; no AI context, model identity, usage or cost is inferred.",
            conflicts="None known, self-report8A"))
    note = dict(
        schema_version=3, recorded_at_utc=at.isoformat(), role="evaluation_only",
        supersedes=pin(prior_path), source_manifest=pin(intake / "intake-manifest.json"),
        current_received_01=prior["current_received_01"],
        received_01_reviewer_alias="R1", current_received_02_and_03=records,
        owner_distinctness_statement="Yes, three different people",
        distinctness_basis="Owner confirmation; pseudonyms R1/R2/R3 map to the three submissions. Names or identity proof were not requested.",
        same_addendum_bytes_note="Both addenda have the same bytes/hash; they are retained as two submitted records. Neither duplication nor distinct people is inferred from hash equality; distinctness follows owner confirmation.",
        counts=dict(distinct_reviewers_owner_attested=3, unassisted_owner_attested=1,
                    ai_assisted_human_self_reported=2, human_reported_orientation_returns=3,
                    source_first_order_self_reports=2, measured_review_times=0,
                    estimated_minutes_by_reviewer={"R1":45,"R2":45,"R3":45},
                    estimated_reviewer_minutes_sum=135),
        development_disposition="Authorship/disclosure intake complete for the three orientation returns at their declared assistance levels. Accept useful development feedback; missing separate exports alone does not reject it.",
        limits="One exposed mechanism case; no general reliability, unassisted-human panel, externally certified blind reference, fresh-case qualification or measured workload claim. Estimates and assistant costs stay separate from measured execution costs.",
        qualification=dict(orientation_disclosure_intake_complete=True,
                           HR2_timed_workload_complete=False, R07_genetics_complete=False,
                           fresh_HR3=False, locked_H5=False, clinical_validation=False),
        original_reviews_changed=False, normalized_selections_changed=False, agent_visible=False,
        next="Assign R2/R3 the existing clean genetics-source packet first; release its separate candidate follow-up only after each source reference is returned. No mechanism review is relabeled as genetics review.")
    output = BASE / "OWNER-PROVENANCE-NOTE-v3.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(note, stream, indent=2, ensure_ascii=True); stream.write("\n")
    print(json.dumps({"note":pin(output), "preserved_addenda":len(records),
                      "distinct_reviewers":3, "disclosure_intake_complete":True}))


if __name__ == "__main__":
    main()
