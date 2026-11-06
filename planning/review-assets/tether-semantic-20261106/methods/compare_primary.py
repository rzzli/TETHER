"""Compare fresh primary diagnostic output to separately computed observations.

This script imports no primary analyzer or reconstruction implementation.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def proof(path):
    content = Path(path).read_bytes()
    return {"path": str(Path(path).resolve()), "sha256": sha256(content).hexdigest(), "bytes": len(content)}


def compare(primary, independent):
    assert primary["analysis_manifest_sha256"] == independent["inputs"]["freeze"]["sha256"]
    assert primary["schedule"] == [x["id"] for x in independent["cases"]]
    assert len(primary["schedule"]) == len(set(primary["schedule"])) == 300
    field_map = {"retrieval_miss": "retrieval_missing", "selection_omission": "selected_missing",
                 "retrieved_gold_not_selected": "retrieved_selection_omission", "selection_extra": "selected_extra",
                 "label_mismatch": "wrong_label_common", "rationale_incomplete": "rationale_capped_incomplete_common",
                 "incomplete_even_full": "rationale_full_incomplete_common", "complete_full_but_not_capped": "rationale_cap_displacement_common",
                 "rationale_extra_outside_gold_union": "rationale_outside_union_full_common"}
    category_map = {"operational_nonproduction": "operational_failure", "retrieval_missing": "retrieval_miss",
                    "retrieved_selection_omission": "selection_omission", "selected_extra": "selection_extra",
                    "wrong_label": "label_mismatch", "rationale_incomplete": "rationale_incomplete",
                    "correct_evidence": "strict_correct", "correct_nei": "strict_correct", "nei_false_positive": "selection_extra"}
    docs_verified = 0
    for p, q in zip(primary["cases"], independent["cases"]):
        assert p["id"] == q["id"]
        for name in ("raw_strict_correct", "checked_strict_correct"):
            assert p[name] is q[name], (p["id"], name)
        assert p["prediction_produced"] == q["produced"]
        assert p["gold_documents"] == q["gold_doc_ids"]
        assert p["selection"]["documents"] == q["selected_doc_ids"]
        assert p["selection"]["false_positive_documents"] == q["selected_extra_ids"]
        assert p["selection"]["false_negative_documents"] == q["selected_missing_ids"]
        if q["gold_doc_ids"]:
            assert p["retrieval"]["false_negative_documents"] == q["retrieval_missing_ids"]
            assert p["selection"]["retrieved_gold_not_selected"] == q["retrieved_selection_omission_ids"]
        else:
            assert p["retrieval"]["recall"] is None and p["retrieval"]["complete_gold_retrieved"] is None
        assert p["first_failure"] == category_map[q["first_failure"]]
        for left, right in field_map.items():
            assert p["flags"][left] == q["flags"][right], (p["id"], left)
        assert p["flags"]["operational_failure"] == (not q["produced"])
        assert p["flags"]["not_admitted"] == (q["produced"] and not q["accepted"])
        pdocs = {x["doc_id"]: x for x in p["gold_document_details"] if x["selected"]}
        assert set(pdocs) == {x["doc_id"] for x in q["documents"]}
        for d in q["documents"]:
            other = pdocs[d["doc_id"]]
            for left, right in (("native_cap", "native_cap"), ("label_correct", "label_correct"),
                                ("complete_any_full", "complete_full"), ("complete_any_capped", "complete_capped"),
                                ("extra_sentences_full", "outside_union_full"), ("extra_sentences_capped", "outside_union_capped"),
                                ("missing_sentences_by_rationale_full", "missing_by_alternative_full"),
                                ("missing_sentences_by_rationale_capped", "missing_by_alternative_capped")):
                assert other[left] == d[right], (p["id"], d["doc_id"], left)
            docs_verified += 1
        assert p["flags"]["correct_label_incomplete_rationale"] == any(d["label_correct"] and not d["complete_capped"] for d in q["documents"])
    s, c = primary["summary"], independent["counts"]
    for left, right in (("scheduled_claims", "scheduled"), ("produced_claims", "produced"),
                        ("evidence_bearing_claims", "nonempty_gold_claims"), ("raw_strict_correct", "raw_strict_correct"),
                        ("checked_strict_correct", "checked_strict_correct"), ("complete_gold_retrieved_claims", "nonempty_gold_complete_retrieval_claims")):
        assert s[left] == c[right], left
    partition = Counter(category_map[x["first_failure"]] for x in independent["cases"])
    assert all(s["first_failure_partition"][key] == partition[key] for key in s["first_failure_partition"])
    assert sum(s["first_failure_partition"].values()) == 300
    all_docs = [d for x in independent["cases"] for d in x["documents"]]
    def total(key):
        return sum(len(x[key] or []) for x in independent["cases"])
    doc_counts = {
        "gold": c["gold_document_pairs"], "retrieved_gold": c["gold_document_pairs_retrieved"],
        "unretrieved_gold": total("retrieval_missing_ids"), "selected": independent["raw_native"]["abstract"]["predicted"],
        "selected_gold": len(all_docs), "selection_false_positive": total("selected_extra_ids"),
        "selection_false_negative": total("selected_missing_ids"), "retrieved_gold_not_selected": total("retrieved_selection_omission_ids"),
        "selected_gold_label_correct": sum(d["label_correct"] for d in all_docs),
        "selected_gold_label_wrong": sum(not d["label_correct"] for d in all_docs),
        "selected_gold_rationale_complete_capped": sum(d["complete_capped"] for d in all_docs),
        "selected_gold_rationale_incomplete_capped": sum(not d["complete_capped"] for d in all_docs),
        "selected_gold_correct_label_incomplete_rationale": sum(d["label_correct"] and not d["complete_capped"] for d in all_docs),
        "selected_gold_rationale_complete_full_but_not_capped": sum(d["cap_displacement"] for d in all_docs),
        "selected_gold_rationale_incomplete_even_full": sum(not d["complete_full"] for d in all_docs),
        "extra_sentences_on_selected_gold_full": sum(len(d["outside_union_full"]) for d in all_docs),
        "extra_sentences_on_selected_gold_capped": sum(len(d["outside_union_capped"]) for d in all_docs),
    }
    for key, value in doc_counts.items():
        assert s["document_counts"][key] == value, key
    for left, right in field_map.items():
        assert s["overlapping_flag_counts"][left] == independent["overlapping_claim_flags"][right]
    for stratum, summary in s["strata"].items():
        subset = [x for x in independent["cases"] if ("MIXED" if "+" in x["reference_stratum"] else x["reference_stratum"]) == stratum]
        assert summary["scheduled_claims"] == len(subset)
        assert summary["raw_strict_correct"] == sum(x["raw_strict_correct"] is True for x in subset)
        assert summary["checked_strict_correct"] == sum(x["checked_strict_correct"] for x in subset)
        expected = Counter(category_map[x["first_failure"]] for x in subset)
        assert all(summary["first_failure_partition"][k] == expected[k] for k in summary["first_failure_partition"])
    return {"status": "PASS", "claims_checked": len(primary["cases"]), "selected_gold_documents_checked": docs_verified,
            "first_failure_partition": s["first_failure_partition"], "overlapping_flag_counts": s["overlapping_flag_counts"],
            "document_counts_checked": doc_counts, "independent_native_counts": {k: independent[k] for k in ("raw_native", "checked_native")},
            "scope": "Independent descriptive reconstruction; no analyzer import, new model, tuning or causal repair claim."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--primary", type=Path, required=True)
    p.add_argument("--independent", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    before = {"primary": proof(args.primary), "independent": proof(args.independent), "comparator": proof(__file__)}
    result = compare(read(args.primary), read(args.independent))
    assert before == {"primary": proof(args.primary), "independent": proof(args.independent), "comparator": proof(__file__)}
    result["inputs"] = before
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "claims_checked": result["claims_checked"], "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
