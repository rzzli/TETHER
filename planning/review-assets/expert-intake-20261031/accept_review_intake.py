"""Accept preservation/comparison mechanics without accepting reviewer provenance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return pin(path)


def main():
    expected = {
        "INTAKE-INTEGRITY-AND-ROLE-REVIEW-v1.json": "45202f1128ef98abc604c0a300c745a5201afd95ccfd99de5f4bce8a2242d276",
        "RETURNED-REVIEW-COMPARISON-v1.json": "104ce17bea29eb0fed1e6af83bcc891597e70579702be28a9a070c135ad178dd",
        "RETURNED-REVIEW-LOCATOR-CHECK-v1.json": "89a50a56d5d0b3493a5f425124f2b646ec42331ce36b1aefd40fa007723ebc52",
        "IL6R-SOURCE-CREDIBILITY-CHECK-v1.json": "91fc6165c76657141594b54a03763ae0b662333e4de529418a15594f322f66fc",
    }
    for name, digest in expected.items():
        if pin(BASE / name)["sha256"] != digest:
            raise ValueError("Selected report changed: " + name)
    integrity = json.loads((BASE / "INTAKE-INTEGRITY-AND-ROLE-REVIEW-v1.json").read_bytes())
    comparison = json.loads((BASE / "RETURNED-REVIEW-COMPARISON-v1.json").read_bytes())
    assert integrity["status"] == "PASS_EXACT_INTAKE_INTEGRITY_AND_EVALUATOR_ROLE_ONLY"
    assert len(integrity["checks"]) == 95 and all(row["passed"] for row in integrity["checks"])
    assert integrity["counts"]["existing_test_methods"] == 6
    assert all(integrity["counts"][key] == 0 for key in ("test_failures", "test_errors", "test_skips"))
    manifest_pin = integrity["manifest"]
    assert pin(Path(manifest_pin["path"])) == manifest_pin
    manifest = json.loads(Path(manifest_pin["path"]).read_bytes())
    for record in manifest["records"]:
        for key in ("source", "preserved_original", "projection"):
            assert pin(Path(record[key]["path"])) == record[key]
    for selected in comparison["private_outputs"]:
        assert pin(Path(selected["path"])) == selected
    counts = comparison["counts"]
    assert counts["files"] == 3 and counts["explicit_selections"] == 54
    assert counts["missing_selections"] == counts["invalid_selections"] == 0
    assert counts["items_with_same_selection_in_all_files"] == 17
    assert counts["items_with_differing_selections"] == 1
    assert counts["independent_human_source_references_qualified"] == 0
    note = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "evaluation_only",
        "owner_answer": "Mixed or uncertain",
        "question_scope": "Origin of response2.txt and response3.txt: separate human reviewers, AI systems, or uncertain; expertise/source-first sequence if human.",
        "interpretation": "This does not establish either text file's individual author type, expertise, independence or source-first chronology. No further attribution is inferred.",
        "source_manifest": manifest_pin,
        "files": [
            {"submission_id": "received-01", "author_type": "explicit_ai_disclosure", "candidate_exposure": "explicitly_visible", "qualified_human_reference": False},
            {"submission_id": "received-02", "author_type": "unverified", "candidate_exposure": None, "qualified_human_reference": False},
            {"submission_id": "received-03", "author_type": "unverified", "candidate_exposure": None, "qualified_human_reference": False},
        ],
        "limits": "Owner provenance statement recorded separately; original responses, notes, selections and prior intake reports unchanged."
    }
    note_pin = write(BASE / "OWNER-PROVENANCE-NOTE-v1.json", note)
    acceptance = {
        "schema_version": 1,
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_INTAKE_AND_DESCRIPTIVE_COMPARISON_ONLY",
        "evidence": {name: pin(BASE / name) for name in expected},
        "owner_provenance": note_pin,
        "original_files": 3, "original_bytes": 22693,
        "mechanism_selections": 54, "same_selection_items": 17,
        "different_selection_items": 1, "independent_integrity_checks": 95,
        "existing_synthetic_regressions_passed": 6,
        "role_denials": 12, "role_positive_controls": 1,
        "catalog_changed": False, "runtime_source_changed": False,
        "accepted_human_reference_count": 0,
        "distinct_reviewer_count": None,
        "qualification": {"human_provenance": False, "source_first_independence": False,
                          "adjudicated_gold": False, "R07_genetics": False, "HR2": False,
                          "fresh_HR3": False, "locked_H5": False, "clinical_validation": False,
                          "project_complete": False},
        "scientific_followup": "Focused primary-literature check supports a source-credibility concern, not a formal erratum, repaired source, human adjudication or patient effect.",
        "provider_spend_usd": 0, "model_or_native_runs": 0,
        "next": "Use the unqualified feedback for prospective question/source-quality design; obtain traceable source-only human submissions before scientific gate acceptance. Do not replace fixed passages or repeat old model cells."
    }
    result = write(BASE / "EXPERT-INTAKE-ROOT-ACCEPTANCE-v1.json", acceptance)
    print(json.dumps({"acceptance": result, "owner_provenance": note_pin,
                      "originals_unchanged": True, "qualified_human_references": 0}))


if __name__ == "__main__":
    main()
