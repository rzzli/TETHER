"""Independent SciFact diagnostic reconstruction; imports no experiment analyzer.

Fictional tests run before the actual diagnostic freeze. Actual mode requires a
retained freeze path and only writes a newly created review directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import types


OFFICIAL_SHA256 = "2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def proof(path):
    p = Path(path)
    content = p.read_bytes()
    return {"path": str(p.resolve()), "sha256": sha256(content).hexdigest(), "size_bytes": len(content)}


def counts_and_metrics(golds, predictions):
    """Compute native integer counts directly, without an experiment helper."""
    ac, sc = Counter(), Counter()
    assert [x["id"] for x in golds] == [x["id"] for x in predictions]
    for gold, pred in zip(golds, predictions):
        ac["gold"] += len(gold["evidence"])
        for rationales in gold["evidence"].values():
            sets = [set(r["sentences"]) for r in rationales]
            assert sum(map(len, sets)) == len(set().union(*sets))
            sc["gold"] += sum(map(len, sets))
        for doc, predicted in pred["evidence"].items():
            ac["predicted"] += 1
            sc["predicted"] += len(predicted["sentences"])
            if doc not in gold["evidence"]:
                continue
            rationales = gold["evidence"][doc]
            sets = [set(r["sentences"]) for r in rationales]
            cap = max(3, min(map(len, sets)))
            full = set(predicted["sentences"])
            prefix = set(predicted["sentences"][:cap])
            label_match = predicted["label"] == rationales[0]["label"]
            complete_sentences = set().union(*(r for r in sets if r <= full))
            sc["selection_correct"] += len(complete_sentences)
            if label_match:
                ac["label_correct"] += 1
                ac["rationalized_correct"] += any(r <= prefix for r in sets)
                sc["label_correct"] += len(complete_sentences)
    metric = {}
    for family, counts, key in (("abstract_label_only", ac, "label_correct"),
                                ("abstract_rationalized", ac, "rationalized_correct"),
                                ("sentence_selection", sc, "selection_correct"),
                                ("sentence_label", sc, "label_correct")):
        correct, predicted, gold = counts[key], counts["predicted"], counts["gold"]
        precision = correct / predicted if predicted else 0.0
        recall = correct / gold if gold else 0.0
        metric.update({family + "_precision": precision, family + "_recall": recall,
                       family + "_f1": 2 * correct / (predicted + gold) if predicted + gold else 0.0})
    return {"abstract": dict(ac), "sentence": dict(sc), "metrics": metric}


def one_case(gold, disposition, candidate):
    produced = disposition["producer_status"] == "produced"
    prediction = disposition["prediction"] if produced else {"id": gold["id"], "evidence": {}}
    accepted = produced and disposition["check_status"] == "accepted"
    gs, ps = set(gold["evidence"]), set(prediction["evidence"])
    if produced:
        assert candidate is not None
        assert candidate["result"]["prediction"] == prediction
        retrieval = [str(x["doc_id"]) for x in candidate["result"]["retrieved"]]
        assert len(retrieval) == len(set(retrieval))
        rs = set(retrieval)
        assert ps <= rs
    else:
        rs = set()
    docs = []
    for doc in sorted(gs & ps, key=int):
        annotations = gold["evidence"][doc]
        rationale_sets = [set(x["sentences"]) for x in annotations]
        predicted = prediction["evidence"][doc]
        cap = max(3, min(map(len, rationale_sets)))
        full, capped = set(predicted["sentences"]), set(predicted["sentences"][:cap])
        complete_full, complete_cap = any(x <= full for x in rationale_sets), any(x <= capped for x in rationale_sets)
        union = set().union(*rationale_sets)
        docs.append({"doc_id": doc, "label_correct": predicted["label"] == annotations[0]["label"],
                     "native_cap": cap, "complete_full": complete_full, "complete_capped": complete_cap,
                     "cap_displacement": complete_full and not complete_cap,
                     "outside_union_full": sorted(full - union), "outside_union_capped": sorted(capped - union),
                     "missing_by_alternative_full": [sorted(x - full) for x in rationale_sets],
                     "missing_by_alternative_capped": [sorted(x - capped) for x in rationale_sets]})
    strict = (gs == ps and all(x["label_correct"] and x["complete_capped"] for x in docs)) if produced else None
    flags = {"retrieval_missing": bool(produced and gs - rs),
             "retrieved_selection_omission": bool(produced and (gs & rs) - ps),
             "selected_missing": bool(produced and gs - ps), "selected_extra": bool(produced and ps - gs),
             "wrong_label_common": any(not x["label_correct"] for x in docs),
             "rationale_full_incomplete_common": any(not x["complete_full"] for x in docs),
             "rationale_capped_incomplete_common": any(not x["complete_capped"] for x in docs),
             "rationale_cap_displacement_common": any(x["cap_displacement"] for x in docs),
             "rationale_outside_union_full_common": any(x["outside_union_full"] for x in docs),
             "rationale_outside_union_capped_common": any(x["outside_union_capped"] for x in docs)}
    if not produced:
        first = "operational_nonproduction"
    elif not gs:
        first = "correct_nei" if not ps else "nei_false_positive"
    elif flags["retrieval_missing"]:
        first = "retrieval_missing"
    elif flags["retrieved_selection_omission"]:
        first = "retrieved_selection_omission"
    elif flags["selected_extra"]:
        first = "selected_extra"
    elif flags["wrong_label_common"]:
        first = "wrong_label"
    elif flags["rationale_capped_incomplete_common"]:
        first = "rationale_incomplete"
    else:
        assert strict
        first = "correct_evidence"
    return {"id": gold["id"], "gold_doc_ids": sorted(gs, key=int),
            "selected_doc_ids": sorted(ps, key=int) if produced else None,
            "retrieval_missing_ids": sorted(gs - rs, key=int) if produced and gs else None,
            "retrieved_selection_omission_ids": sorted((gs & rs) - ps, key=int) if produced and gs else None,
            "selected_missing_ids": sorted(gs - ps, key=int) if produced else None,
            "selected_extra_ids": sorted(ps - gs, key=int) if produced else None,
            "raw_strict_correct": strict, "checked_strict_correct": bool(strict and accepted),
            "produced": produced, "accepted": accepted, "flags": flags, "documents": docs,
            "first_failure": first, "reference_stratum": "NEI" if not gs else "+".join(sorted({r[0]["label"] for r in gold["evidence"].values()}))}


def reconstruct(golds, dispositions, candidates, schedule):
    assert len(schedule) == len(set(schedule))
    assert [x["id"] for x in golds] == [x["id"] for x in dispositions] == schedule
    by_id = {int(x["cell_id"]): x for x in candidates}
    assert len(by_id) == len(candidates)
    assert set(by_id) <= set(schedule)
    cases = [one_case(g, d, by_id.get(g["id"])) for g, d in zip(golds, dispositions)]
    produced_ids = {d["id"] for d in dispositions if d["producer_status"] == "produced"}
    assert produced_ids <= set(by_id)
    raw = [d["prediction"] if d["producer_status"] == "produced" else {"id": d["id"], "evidence": {}} for d in dispositions]
    checked = [p if d["producer_status"] == "produced" and d["check_status"] == "accepted" else {"id": d["id"], "evidence": {}} for p, d in zip(raw, dispositions)]
    flags = Counter({k: 0 for k in cases[0]["flags"]})
    flags.update(k for x in cases for k, v in x["flags"].items() if v)
    first = Counter(x["first_failure"] for x in cases)
    counts = {"scheduled": len(schedule), "produced": sum(x["produced"] for x in cases),
              "accepted": sum(x["accepted"] for x in cases), "raw_strict_correct": sum(x["raw_strict_correct"] is True for x in cases),
              "checked_strict_correct": sum(x["checked_strict_correct"] for x in cases),
              "nonempty_gold_claims": sum(bool(x["gold_doc_ids"]) for x in cases),
              "gold_document_pairs": sum(len(x["gold_doc_ids"]) for x in cases),
              "gold_document_pairs_retrieved": sum(len(x["gold_doc_ids"]) - len(x["retrieval_missing_ids"]) for x in cases if x["retrieval_missing_ids"] is not None),
              "nonempty_gold_complete_retrieval_claims": sum(x["retrieval_missing_ids"] == [] for x in cases)}
    return {"counts": counts, "first_failure_counts": dict(first), "overlapping_claim_flags": dict(flags),
            "raw_native": counts_and_metrics(golds, raw), "checked_native": counts_and_metrics(golds, checked), "cases": cases}


def fixture_check(evaluator):
    source = Path(evaluator).read_bytes()
    assert sha256(source).hexdigest() == OFFICIAL_SHA256
    module = types.ModuleType("independent_pinned_native_scorer")
    exec(compile(source, str(evaluator), "exec"), module.__dict__)
    reports = []
    def check(name, rationale, predicted, expected_strict, first, *, label="SUPPORT", extra=False, gold_empty=False, failed=False, retrieved=None):
        gold = {"id": 1, "evidence": {} if gold_empty else {"10": [{"label": "SUPPORT", "sentences": x} for x in rationale]}}
        evidence = {} if predicted is None else {"10": {"label": label, "sentences": predicted}}
        if extra:
            evidence["20"] = {"label": "SUPPORT", "sentences": [0]}
        pred = {"id": 1, "evidence": evidence}
        d = {"id": 1, "producer_status": "error" if failed else "produced", "check_status": "not_run" if failed else "accepted", "prediction": None if failed else pred}
        c = None if failed else {"cell_id": "1", "result": {"prediction": pred, "retrieved": [{"doc_id": x} for x in (retrieved if retrieved is not None else [10, 20])]}}
        row = one_case(gold, d, c)
        assert row["raw_strict_correct"] is expected_strict, name
        assert row["first_failure"] == first, (name, row["first_failure"])
        projected = pred if not failed else {"id": 1, "evidence": {}}
        manual = counts_and_metrics([gold], [projected])["metrics"]
        upstream = module.Evaluator(verbose=True).evaluate([module.unify_label(gold)], [projected])
        assert set(manual) == set(upstream)
        assert all(abs(manual[k] - upstream[k]) < 1e-12 for k in manual), name
        reports.append({"name": name, "strict": row["raw_strict_correct"], "first_failure": first, "native_metric_agreement": True, "flags": row["flags"]})
        return row
    check("perfect", [[0]], [0], True, "correct_evidence")
    check("wrong_label", [[0]], [0], False, "wrong_label", label="CONTRADICT")
    check("partial_multisentence", [[0, 1]], [0], False, "rationale_incomplete")
    check("alternative_complete", [[0, 1], [2]], [2], True, "correct_evidence")
    row = check("cap_displacement", [[3, 4]], [0, 1, 2, 3, 4], False, "rationale_incomplete")
    assert row["flags"]["rationale_cap_displacement_common"] and not row["flags"]["rationale_full_incomplete_common"]
    check("long_rationale_expands_cap", [[0, 1, 2, 3]], [0, 1, 2, 3, 4], True, "correct_evidence")
    check("extra_sentences_can_pass_strict", [[0]], [1, 0, 2, 3], True, "correct_evidence")
    check("extra_document", [[0]], [0], False, "selected_extra", extra=True)
    check("selected_omission_after_retrieval", [[0]], None, False, "retrieved_selection_omission")
    check("unretrieved_document", [[0]], None, False, "retrieval_missing", retrieved=[20])
    row = check("retrieval_and_extra_overlap", [[0]], None, False, "retrieval_missing", extra=True, retrieved=[20])
    assert row["flags"]["selected_extra"]
    check("successful_nei", [], None, True, "correct_nei", gold_empty=True)
    check("nei_false_positive", [], [0], False, "nei_false_positive", gold_empty=True)
    check("failed_nei_is_not_correct", [], None, None, "operational_nonproduction", gold_empty=True, failed=True)
    return {"status": "PASS", "fictional_cases": len(reports), "official_scorer_sha256": OFFICIAL_SHA256, "cases": reports}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--references", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixtures = fixture_check(args.evaluator)
    write(args.output / "FICTIONAL.json", fixtures)
    if args.baseline is not None:
        assert args.freeze is not None and args.freeze.is_file()
        assert args.references is not None
        frozen = read(args.freeze)
        assert frozen["kind"] == "scifact_descriptive_decomposition_inputs"
        assert frozen["mode"] == "actual" and frozen["expected_claim_count"] == 300
        inputs = {"freeze": proof(args.freeze), "references": proof(args.references),
                  "dispositions": proof(args.baseline / "dispositions.json"),
                  "candidates": proof(args.baseline / "check-inputs/candidates.json"),
                  "evaluation": proof(args.baseline / "evaluation.json"),
                  "recipe": proof(args.baseline / "jobs/dev/recipe.json"),
                  "baseline_receipt": proof(args.baseline / "RECEIPT.json"),
                  "checker": proof(__file__), "evaluator": proof(args.evaluator)}
        for name in ("references", "dispositions", "candidates", "evaluation"):
            pin, consumed = frozen["inputs"][name], inputs[name]
            assert str(Path(pin["path"]).resolve()) == consumed["path"]
            assert pin["sha256"] == consumed["sha256"] and pin["bytes"] == consumed["size_bytes"]
        old_freeze_pin = frozen["inputs"]["freeze"]
        old_freeze_proof = proof(old_freeze_pin["path"])
        assert old_freeze_pin["sha256"] == old_freeze_proof["sha256"]
        assert old_freeze_pin["bytes"] == old_freeze_proof["size_bytes"]
        assert read(old_freeze_pin["path"])["dev_schedule"] == read(args.baseline / "jobs/dev/recipe.json")["schedule"]
        refs = [json.loads(line) for line in args.references.read_text(encoding="utf-8").splitlines() if line]
        result = reconstruct(refs, read(args.baseline / "dispositions.json"), read(args.baseline / "check-inputs/candidates.json"), read(args.baseline / "jobs/dev/recipe.json")["schedule"])
        old = read(args.baseline / "evaluation.json")
        assert result["counts"]["scheduled"] == 300
        assert result["counts"]["raw_strict_correct"] == old["counts"]["correct_raw"]
        for arm in ("raw", "checked"):
            assert all(abs(v - old[arm + "_metrics"][k]) < 1e-12 for k, v in result[arm + "_native"]["metrics"].items())
        assert [x["raw_strict_correct"] for x in result["cases"]] == [x["raw_strict_correct"] for x in old["case_results"]]
        assert [x["checked_strict_correct"] for x in result["cases"]] == [x["checked_strict_correct"] for x in old["case_results"]]
        for record in inputs.values():
            assert proof(record["path"]) == record
        result["inputs"] = inputs
        result["status"] = "PASS"
        write(args.output / "INDEPENDENT-RECONSTRUCTION.json", result)
    write(args.output / "REVIEW-RECEIPT.json", {"status": "PASS", "outputs": [proof(x) for x in sorted(args.output.iterdir()) if x.is_file()]})
    print(json.dumps({"status": "PASS", "output": str(args.output.resolve()), "fictional_cases": fixtures["fictional_cases"], "actual_reconstructed": args.baseline is not None}))


if __name__ == "__main__":
    main()
