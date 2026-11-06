"""Decompose retained SciFact errors without changing its native correctness rule.

The CLI reads only explicitly pinned local artifacts and writes a new directory.
No model is loaded, no configuration is selected, and no sources are acquired.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
SOURCE_CLOSURE = (
    "experiments/scifact_diagnostics/__init__.py",
    "experiments/scifact_diagnostics/analyze.py",
    "experiments/scifact/__init__.py",
    "experiments/scifact/evaluate.py",
    "experiments/scifact/native_contract.py",
    "src/asof/__init__.py",
    "src/asof/atomic.py",
    "src/asof/serde.py",
)
INPUT_KEYS = {"freeze", "references", "corpus", "dispositions", "candidates", "evaluation"}
FIRST_FAILURE_ORDER = (
    "operational_failure", "retrieval_miss", "selection_omission",
    "selection_extra", "label_mismatch", "rationale_incomplete", "strict_correct",
)
SCOPE = (
    "Descriptive post hoc analysis of frozen public-development predictions. "
    "The ordered partition is a reporting convention, not a causal attribution, "
    "ablation, retuning, new model run, or biological/clinical conclusion. "
    "False positives and negatives are relative to benchmark annotations; "
    "unannotated documents are not established biological negatives. "
    "This analysis does not replace the retained official metrics."
)


class AnalysisError(ValueError):
    """A required artifact, correspondence, or methodological invariant failed."""


def need(condition, message):
    if not condition:
        raise AnalysisError(message)


def _native():
    # CLI verifies this entire local source closure before these imports.
    # Explicit local roots allow a qualified interpreter launched with -I -B.
    for value in (str(ROOT / "src"), str(ROOT)):
        if value not in sys.path:
            sys.path.insert(0, value)
    from experiments.scifact.evaluate import _dispositions, strict_correct
    from experiments.scifact.native_contract import validate_references, validate_schedule
    return strict_correct, _dispositions, validate_references, validate_schedule


def ids(values):
    return sorted(values, key=int)


def analyze_case(gold, record, retrieved_ids):
    """Analyze one validated native case; never project an operational failure to NEI."""
    strict_correct, _, _, _ = _native()
    produced = record["producer_status"] == "produced"
    prediction = record["prediction"] if produced else None
    gold_docs = set(gold["evidence"])
    retrieved = None if retrieved_ids is None else {str(i) for i in retrieved_ids}
    selected = set(prediction["evidence"]) if produced else None
    need(not produced or retrieved is not None, "Produced prediction lacks retained retrieval")
    need(not produced or selected <= retrieved, "Selected document was not retrieved")
    need(record["id"] == gold["id"], "Case identity mismatch")
    labels = {r[0]["label"] for r in gold["evidence"].values()}
    stratum = "NEI" if not labels else next(iter(labels)) if len(labels) == 1 else "MIXED"
    retrieval_fn = gold_docs - retrieved if retrieved is not None else None
    selected_fn = gold_docs - selected if produced else None
    selected_fp = selected - gold_docs if produced else None
    common = gold_docs & selected if produced else set()
    details = []
    for doc_id in ids(gold_docs):
        rationales = gold["evidence"][doc_id]
        sets = [set(r["sentences"]) for r in rationales]
        union = set().union(*sets)
        cap = max(3, min(map(len, sets)))
        chosen = prediction["evidence"].get(doc_id) if produced else None
        full = list(chosen["sentences"]) if chosen is not None else None
        capped = full[:cap] if full is not None else None
        full_set, capped_set = (set(full), set(capped)) if chosen is not None else (None, None)
        complete_full = [i for i, s in enumerate(sets) if s <= full_set] if chosen is not None else None
        complete_capped = [i for i, s in enumerate(sets) if s <= capped_set] if chosen is not None else None
        details.append({
            "doc_id": doc_id, "retrieved": doc_id in retrieved if retrieved is not None else None,
            "selected": doc_id in selected if produced else None,
            "gold_label": rationales[0]["label"], "predicted_label": chosen["label"] if chosen is not None else None,
            "label_correct": chosen["label"] == rationales[0]["label"] if chosen is not None else None,
            "gold_rationale_sets": [list(r["sentences"]) for r in rationales],
            "native_cap": cap, "predicted_sentences": full, "capped_sentences": capped,
            "complete_any_full": bool(complete_full) if chosen is not None else None,
            "complete_any_capped": bool(complete_capped) if chosen is not None else None,
            "complete_rationale_indices_full": complete_full,
            "complete_rationale_indices_capped": complete_capped,
            "missing_sentences_by_rationale_full": [sorted(s - full_set) for s in sets] if chosen is not None else None,
            "missing_sentences_by_rationale_capped": [sorted(s - capped_set) for s in sets] if chosen is not None else None,
            "extra_sentences_full": sorted(full_set - union) if chosen is not None else None,
            "extra_sentences_capped": sorted(capped_set - union) if chosen is not None else None,
        })
    observed = [d for d in details if d["selected"]]
    flags = {
        "operational_failure": not produced,
        "retrieval_miss": bool(gold_docs and retrieval_fn),
        "selection_omission": bool(selected_fn),
        "retrieved_gold_not_selected": bool(produced and (gold_docs & retrieved) - selected),
        "selection_extra": bool(selected_fp),
        "label_mismatch": any(d["label_correct"] is False for d in observed),
        "rationale_incomplete": any(d["complete_any_capped"] is False for d in observed),
        "correct_label_incomplete_rationale": any(d["label_correct"] and not d["complete_any_capped"] for d in observed),
        "incomplete_even_full": any(not d["complete_any_full"] for d in observed),
        "complete_full_but_not_capped": any(d["complete_any_full"] and not d["complete_any_capped"] for d in observed),
        "rationale_extra_outside_gold_union": any(d["extra_sentences_full"] for d in observed),
        "not_admitted": produced and record["check_status"] != "accepted",
    }
    raw_correct = strict_correct(gold, prediction) if produced else None
    first = next((name for name in FIRST_FAILURE_ORDER[:-1] if flags[name]), "strict_correct")
    need((first == "strict_correct") == bool(raw_correct), "Partition differs from native strict correctness")
    return {
        "id": gold["id"], "gold_stratum": stratum, "gold_has_evidence": bool(gold_docs),
        "producer_status": record["producer_status"], "check_status": record["check_status"],
        "prediction_produced": produced, "raw_strict_correct": raw_correct,
        "checked_strict_correct": bool(raw_correct and record["check_status"] == "accepted"),
        "native_empty_prediction": not selected if produced else None,
        "nei_outcome": ("operational_failure" if not produced else "produced_empty_correct" if not selected
                        else "produced_nonempty_false_positive") if not gold_docs else None,
        "gold_documents": ids(gold_docs),
        "retrieval": {"available": retrieved is not None, "documents": list(map(str, retrieved_ids)) if retrieved is not None else None,
                      "true_positive_documents": ids(gold_docs & retrieved) if retrieved is not None else None,
                      "false_negative_documents": ids(retrieval_fn) if retrieval_fn is not None else None,
                      "non_gold_documents": ids(retrieved - gold_docs) if retrieved is not None else None,
                      "recall": len(gold_docs & retrieved) / len(gold_docs) if gold_docs and retrieved is not None else None,
                      "complete_gold_retrieved": not retrieval_fn if gold_docs and retrieved is not None else None},
        "selection": {"documents": ids(selected) if produced else None,
                      "true_positive_documents": ids(common) if produced else None,
                      "false_negative_documents": ids(selected_fn) if produced else None,
                      "false_positive_documents": ids(selected_fp) if produced else None,
                      "retrieved_gold_not_selected": ids((gold_docs & retrieved) - selected) if produced else None,
                      "exact_document_set": selected == gold_docs if produced else None},
        "labels_correct_on_all_selected_gold_documents": all(d["label_correct"] for d in observed) if observed else None,
        "all_gold_documents_selected_with_correct_labels": bool(produced and gold_docs <= selected and
                                                                all(d["label_correct"] for d in observed)) if gold_docs else None,
        "gold_document_details": details,
        "extra_selected_document_details": [{"doc_id": d, "predicted_label": prediction["evidence"][d]["label"],
                                               "predicted_sentences": list(prediction["evidence"][d]["sentences"])}
                                              for d in ids(selected_fp)] if produced else [],
        "flags": flags, "first_failure": first,
    }


def _summarize(cases):
    partition = {name: 0 for name in FIRST_FAILURE_ORDER}
    overlap = Counter()
    docs = Counter({key: 0 for key in (
        "gold", "retrieved_gold", "unretrieved_gold", "retrieved_non_gold", "selected", "selected_gold",
        "selection_false_positive", "selection_false_negative", "retrieved_gold_not_selected",
        "selected_gold_label_correct", "selected_gold_label_wrong", "selected_gold_rationale_complete_capped",
        "selected_gold_rationale_incomplete_capped", "selected_gold_correct_label_incomplete_rationale",
        "selected_gold_rationale_complete_full_but_not_capped", "selected_gold_rationale_incomplete_even_full",
        "extra_sentences_on_selected_gold_full", "extra_sentences_on_selected_gold_capped")})
    for row in cases:
        partition[row["first_failure"]] += 1
        overlap.update({name: int(value) for name, value in row["flags"].items()})
        docs["gold"] += len(row["gold_documents"])
        for metric, field in (("retrieved_gold", "true_positive_documents"), ("unretrieved_gold", "false_negative_documents"),
                              ("retrieved_non_gold", "non_gold_documents")):
            docs[metric] += len(row["retrieval"][field] or [])
        for metric, field in (("selected", "documents"), ("selected_gold", "true_positive_documents"),
                              ("selection_false_positive", "false_positive_documents"),
                              ("selection_false_negative", "false_negative_documents"),
                              ("retrieved_gold_not_selected", "retrieved_gold_not_selected")):
            docs[metric] += len(row["selection"][field] or [])
        for d in row["gold_document_details"]:
            if not d["selected"]:
                continue
            docs["selected_gold_label_correct"] += d["label_correct"]
            docs["selected_gold_label_wrong"] += not d["label_correct"]
            docs["selected_gold_rationale_complete_capped"] += d["complete_any_capped"]
            docs["selected_gold_rationale_incomplete_capped"] += not d["complete_any_capped"]
            docs["selected_gold_correct_label_incomplete_rationale"] += d["label_correct"] and not d["complete_any_capped"]
            docs["selected_gold_rationale_complete_full_but_not_capped"] += d["complete_any_full"] and not d["complete_any_capped"]
            docs["selected_gold_rationale_incomplete_even_full"] += not d["complete_any_full"]
            docs["extra_sentences_on_selected_gold_full"] += len(d["extra_sentences_full"])
            docs["extra_sentences_on_selected_gold_capped"] += len(d["extra_sentences_capped"])
    return {"scheduled_claims": len(cases), "produced_claims": sum(r["prediction_produced"] for r in cases),
            "evidence_bearing_claims": sum(r["gold_has_evidence"] for r in cases),
            "retrieval_observed_claims": sum(r["retrieval"]["available"] for r in cases),
            "complete_gold_retrieved_claims": sum(r["retrieval"]["complete_gold_retrieved"] is True for r in cases),
            "raw_strict_correct": sum(r["raw_strict_correct"] is True for r in cases),
            "checked_strict_correct": sum(r["checked_strict_correct"] for r in cases),
            "native_empty_predictions": sum(r["native_empty_prediction"] is True for r in cases),
            "first_failure_partition": partition, "overlapping_flag_counts": dict(overlap),
            "document_counts": dict(docs),
            "nei_outcomes": dict(Counter(r["nei_outcome"] for r in cases if r["gold_stratum"] == "NEI"))}


def analyze_dataset(schedule, corpus, references, records, candidates, evaluation):
    """Validate every schedule member and compare native results to the retained scorer."""
    _, dispositions, validate_references, validate_schedule = _native()
    schedule = validate_schedule(schedule)
    references = validate_references(references, corpus, schedule)
    records = dispositions(schedule, corpus, records)
    need(isinstance(candidates, list) and len(candidates) == len(schedule), "Candidate schedule count mismatch")
    retained = evaluation.get("case_results")
    need(isinstance(retained, list) and [r.get("id") for r in retained] == list(schedule), "Retained evaluation schedule mismatch")
    cases = []
    for claim_id, gold, record, candidate, previous in zip(schedule, references, records, candidates, retained):
        need(candidate.get("cell_id") == str(claim_id), "Candidate identity/order mismatch")
        retrieved_ids = None
        if record["producer_status"] == "produced":
            result = candidate.get("result")
            need(candidate.get("status") == "completed" and isinstance(result, dict), "Produced candidate is not completed")
            # Canonical JSON comparison handles frozen tuple/list representations.
            need(_plain(result.get("prediction")) == _plain(record["prediction"]), "Candidate/disposition prediction mismatch")
            rows = result.get("retrieved")
            need(isinstance(rows, list), "Missing retained retrieval")
            retrieved_ids = [r.get("doc_id") for r in rows]
            need(all(type(i) is int and i >= 0 and (i in corpus or str(i) in corpus) for i in retrieved_ids), "Invalid retrieved document")
            need(len(set(retrieved_ids)) == len(retrieved_ids), "Duplicate retrieved document")
            need([r.get("rank") for r in rows] == list(range(1, len(rows) + 1)), "Retrieved rank/order mismatch")
        row = analyze_case(gold, record, retrieved_ids)
        need(row["raw_strict_correct"] is previous.get("raw_strict_correct") and
             row["checked_strict_correct"] is previous.get("checked_strict_correct"), "Retained native strict result mismatch")
        cases.append(row)
    summary = _summarize(cases)
    summary["strata"] = {name: _summarize([c for c in cases if c["gold_stratum"] == name])
                         for name in ("SUPPORT", "CONTRADICT", "NEI", "MIXED")}
    need(sum(summary["first_failure_partition"].values()) == len(schedule), "Partition incomplete")
    return {"schema_version": 1, "kind": "scifact_descriptive_error_decomposition", "scope": SCOPE,
            "strict_criterion": "Unchanged experiments.scifact.evaluate.strict_correct; operational placeholders excluded",
            "first_failure_order": list(FIRST_FAILURE_ORDER),
            "partition_semantics": "First observed failed requirement in a fixed descriptive order; errors overlap and this is not causal.",
            "retrieval_non_gold_semantics": "Retrieved documents without gold evidence annotations; benchmark-relative retrieval false positives, not biological negatives.",
            "rationale_extra_semantics": "Extra means outside the union of annotated rationale sentences; extras alone do not fail native strict correctness.",
            "inapplicable_semantics": "NEI retrieval recall/completeness and absent operational predictions use null; missing gold documents have unobserved labels/rationales.",
            "schedule": list(schedule), "summary": summary, "cases": cases}


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON object key")
            result[key] = value
        return result
    def invalid(value):
        raise AnalysisError(f"Invalid JSON numeric constant: {value}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def _bytes(path, limit=32 * 1024 * 1024):
    path = Path(path)
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and
         not (getattr(info, "st_file_attributes", 0) & 0x400), "Input must be a regular non-link file")
    need(info.st_size <= limit, "Input exceeds size bound")
    raw = path.read_bytes()
    need(len(raw) == info.st_size, "Input size changed while reading")
    return raw


def _pin(pin):
    need(isinstance(pin, dict) and set(pin) == {"path", "sha256", "bytes"}, "Invalid explicit file pin")
    need(isinstance(pin["path"], str) and Path(pin["path"]).is_absolute(), "Pinned path must be absolute")
    need(isinstance(pin["sha256"], str) and re.fullmatch("[0-9a-f]{64}", pin["sha256"]), "Invalid SHA-256 pin")
    need(type(pin["bytes"]) is int and pin["bytes"] >= 0, "Invalid byte count")
    raw = _bytes(pin["path"])
    need(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], "Pinned input hash/size mismatch: " + pin["path"])
    return raw


def _encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _markdown(result):
    s = result["summary"]
    lines = ["# SciFact descriptive error decomposition", "", SCOPE, "",
             f"All {s['scheduled_claims']} scheduled claims are retained. Native strict correctness: "
             f"{s['raw_strict_correct']}/{s['scheduled_claims']}; evidence-bearing claims: {s['evidence_bearing_claims']}.", "",
             "## Mutually exclusive first-failure partition", "", "This fixed order assigns each claim once. It does not estimate causal contributions.", "",
             "| First observed failure | Claims |", "|---|---:|"]
    lines.extend(f"| {name} | {count} |" for name, count in s["first_failure_partition"].items())
    lines += ["", "## Overlapping observations", "", "The following counts overlap; do not add them as an error total.", "",
              "| Flag | Claims |", "|---|---:|"]
    lines.extend(f"| {name} | {count} |" for name, count in s["overlapping_flag_counts"].items())
    lines += ["", "## Document and rationale counts", "", "| Observation | Count |", "|---|---:|"]
    lines.extend(f"| {name} | {count} |" for name, count in s["document_counts"].items())
    lines += ["", "## Strata", "", "| Stratum | Scheduled | Produced | Strict correct |", "|---|---:|---:|---:|"]
    lines.extend(f"| {name} | {r['scheduled_claims']} | {r['produced_claims']} | {r['raw_strict_correct']} |"
                 for name, r in s["strata"].items())
    lines += ["", "NEI outcomes: " + json.dumps(s["nei_outcomes"], sort_keys=True) + ".", "",
              "Native rationale correctness requires any one complete annotated rationale within the original ordered prediction prefix "
              "of length max(3, shortest annotated rationale length), with an exact evidence-document set and correct document labels. "
              "Extra rationale sentences alone are permitted; extras can coexist with strict correctness. "
              "Full-list completeness with cap incompleteness identifies ordering/cap displacement descriptively. "
              "NEI retrieval recall is not applicable. Labels and rationales are assessed only for selected annotated documents.", "",
              "Retrieval non-gold documents and selected false positives are annotation-relative. These counts do not establish biological falsehoods. "
              "All per-claim document IDs, ordered sentences, rationale-set differences, flags and statuses are retained in DECOMPOSITION.json. "
              "Official metrics remain in the sealed baseline evaluation; none are replaced or recomputed here.", ""]
    return "\n".join(lines).encode("utf-8")


def run_manifest(manifest_path, manifest_sha256, output):
    """Verify explicit input/source pins; publish to one fresh directory only."""
    raw = _bytes(manifest_path)
    need(hashlib.sha256(raw).hexdigest() == manifest_sha256, "Analysis manifest hash mismatch")
    manifest = _json(raw)
    output = Path(output).resolve()
    need(not output.exists(), "Output already exists; no clobber permitted")
    need(manifest.get("schema_version") == 1 and manifest.get("kind") == "scifact_descriptive_decomposition_inputs", "Unsupported analysis manifest")
    need(manifest.get("mode") in {"actual", "fictional_qualification"}, "Missing declared analysis mode")
    need(set(manifest.get("inputs", {})) == INPUT_KEYS, "Explicit input set mismatch")
    need(type(manifest.get("expected_claim_count")) is int and manifest["expected_claim_count"] > 0, "Invalid expected claim count")
    need(manifest["mode"] != "actual" or manifest["expected_claim_count"] == 300, "Actual analysis must retain all 300 claims")
    source_pins = manifest.get("source_pins")
    need(isinstance(source_pins, list), "Missing source closure pins")
    source_paths = [str(Path(p["path"]).resolve()) for p in source_pins]
    need(len(set(source_paths)) == len(source_paths), "Duplicate source pin")
    need({str((ROOT / p).resolve()) for p in SOURCE_CLOSURE} <= set(source_paths), "Incomplete source closure")
    pins = list(manifest["inputs"].values()) + source_pins + manifest.get("authority_pins", [])
    need(manifest["mode"] != "actual" or (manifest.get("baseline_identity") and manifest.get("authority_pins")), "Actual analysis requires baseline authorities")
    for pin in pins:
        path = Path(pin["path"]).resolve()
        need(output != path and output not in path.parents, "Output overlaps a pinned input")
    for pin in source_pins + manifest.get("authority_pins", []):
        _pin(pin)
    inputs = {name: _pin(pin) for name, pin in manifest["inputs"].items()}
    schedule = _json(inputs["freeze"])["dev_schedule"]
    need(len(schedule) == manifest["expected_claim_count"], "Manifest schedule count mismatch")
    references = [_json(line) for line in inputs["references"].splitlines() if line.strip()]
    corpus_rows = [_json(line) for line in inputs["corpus"].splitlines() if line.strip()]
    need(all(isinstance(r, dict) and type(r.get("doc_id")) is int and r["doc_id"] >= 0 for r in corpus_rows), "Invalid corpus document ID")
    corpus = {r["doc_id"]: r for r in corpus_rows}
    need(len(corpus) == len(corpus_rows), "Duplicate corpus document ID")
    result = analyze_dataset(schedule, corpus, references, _json(inputs["dispositions"]),
                             _json(inputs["candidates"]), _json(inputs["evaluation"]))
    # Recheck every byte pin after analysis, before output creation.
    for pin in pins:
        _pin(pin)
    need(hashlib.sha256(_bytes(manifest_path)).hexdigest() == manifest_sha256, "Analysis manifest changed during execution")
    result["analysis_manifest_sha256"] = manifest_sha256
    result["mode"] = manifest["mode"]
    result["baseline_identity"] = manifest.get("baseline_identity")
    output.mkdir(parents=True, exist_ok=False)
    files = {"INPUT-MANIFEST.json": raw, "DECOMPOSITION.json": _encode(result), "REPORT.md": _markdown(result)}
    for name, payload in files.items():
        with (output / name).open("xb") as stream:
            stream.write(payload)
    receipt = {"schema_version": 1, "status": "PASS", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
               "mode": manifest["mode"], "analysis_manifest_sha256": manifest_sha256,
               "all_input_and_source_pins_rechecked": True, "retained_native_case_results_matched": True,
               "scheduled_claims": len(schedule), "source_closure": source_pins,
               "outputs": {name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                           for name, payload in files.items()}}
    with (output / "RECEIPT.json").open("xb") as stream:
        stream.write(_encode(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_manifest(args.manifest, args.manifest_sha256, args.output)
    print(json.dumps({"status": receipt["status"], "scheduled_claims": receipt["scheduled_claims"], "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
