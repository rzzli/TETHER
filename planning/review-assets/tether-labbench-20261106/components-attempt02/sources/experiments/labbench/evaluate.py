"""Label-only LitQA2 scoring with explicit full-schedule operational accounting.

Correct/all, correct/answered, and answered/all follow the original native
definitions. Failed or checked-rejected tasks remain in all-scheduled accuracy
and coverage denominators. They are never relabeled as a successful unsure.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from asof.serde import ContractError, freeze
from .native_contract import evidence_ids, validate_prediction, validate_query, visible_unsure_index

PRODUCER_STATUSES = frozenset(("produced", "parse_failure", "timeout", "error", "interrupted", "unexecuted", "input_unavailable"))
CHECK_STATUSES = frozenset(("accepted", "rejected", "error", "not_run"))


def _ordered(rows, ids, name):
    if not isinstance(rows, (list, tuple)) or len(rows) != len(ids):
        raise ContractError(f"{name} must retain every scheduled case")
    if any(not isinstance(row, Mapping) for row in rows) or [row.get("id") for row in rows] != ids:
        raise ContractError(f"{name} differs from the unique ordered schedule")


def evaluate_schedule(queries, references, records, *, evidence_ids_by_query):
    if not isinstance(queries, (list, tuple)) or not queries:
        raise ContractError("Scoring requires a nonempty full task schedule")
    queries = [validate_query(row) for row in queries]
    ids = [row["id"] for row in queries]
    if len(set(ids)) != len(ids):
        raise ContractError("Duplicate task IDs in schedule")
    _ordered(references, ids, "References")
    _ordered(records, ids, "Dispositions")
    if not isinstance(evidence_ids_by_query, Mapping) or set(evidence_ids_by_query) != set(ids):
        raise ContractError("Offered evidence must be declared for every scheduled case")
    counts = Counter({key: 0 for key in ("produced", "producer_failures", "accepted", "rejected", "check_errors",
        "check_not_run", "raw_answered", "checked_answered", "raw_correct", "correct_and_admitted", "correct_but_rejected",
        "correct_not_admitted", "native_unsure", "accepted_unsure", "incorrect_and_admitted",
        "incorrect_substantive_and_admitted", "parse_failures", "produced_or_parse_failure")})
    producer_statuses, check_statuses = Counter(), Counter()
    cases = []
    for query, reference, row in zip(queries, references, records):
        if set(reference) != {"id", "answer_index", "unsure_index"}:
            raise ContractError("Reference contains unknown or missing fields")
        if any(type(reference[key]) is not int or not 0 <= reference[key] < len(query["choices"])
               for key in ("answer_index", "unsure_index")):
            raise ContractError("Reference choice index outside query")
        if reference["answer_index"] == reference["unsure_index"] or reference["unsure_index"] != visible_unsure_index(query):
            raise ContractError("Reference correct/unsure fields contradict visible task")
        if set(row) != {"id", "producer_status", "check_status", "prediction", "reason"}:
            raise ContractError("Disposition contains unknown or missing fields")
        ps, cs = row["producer_status"], row["check_status"]
        if ps not in PRODUCER_STATUSES or cs not in CHECK_STATUSES:
            raise ContractError("Unknown producer/check status")
        reason = row["reason"]
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise ContractError("Disposition reason must be null or nonempty text")
        produced = ps == "produced"
        allowed = evidence_ids(evidence_ids_by_query[query["id"]])
        if produced:
            pred = validate_prediction(row["prediction"], query, allowed)
            if cs != "accepted" and reason is None:
                raise ContractError("Non-admission requires an explicit reason")
            if cs == "accepted" and reason is not None:
                raise ContractError("Accepted disposition cannot contain a failure reason")
        else:
            pred = None
            if row["prediction"] is not None or cs != "not_run" or reason is None:
                raise ContractError("Operational failure must remain null, unchecked and explained")
        unsure = None if not produced else pred["answer_index"] == reference["unsure_index"]
        correct = bool(produced and pred["answer_index"] == reference["answer_index"])
        admitted = cs == "accepted"
        answered = produced and not unsure
        counts["produced"] += produced
        counts["producer_failures"] += not produced
        counts["accepted"] += admitted
        counts["rejected"] += cs == "rejected"
        counts["check_errors"] += cs == "error"
        counts["check_not_run"] += cs == "not_run"
        counts["raw_answered"] += answered
        counts["checked_answered"] += answered and admitted
        counts["raw_correct"] += correct
        counts["correct_and_admitted"] += correct and admitted
        counts["correct_but_rejected"] += correct and cs == "rejected"
        counts["correct_not_admitted"] += correct and not admitted
        counts["native_unsure"] += unsure is True
        counts["accepted_unsure"] += unsure is True and admitted
        counts["incorrect_and_admitted"] += admitted and not correct
        counts["incorrect_substantive_and_admitted"] += admitted and answered and not correct
        counts["parse_failures"] += ps == "parse_failure"
        counts["produced_or_parse_failure"] += ps in ("produced","parse_failure")
        producer_statuses[ps] += 1
        check_statuses[cs] += 1
        cases.append({"id": query["id"], "producer_status": ps, "check_status": cs, "prediction": pred,
                      "native_unsure": unsure, "raw_correct": correct, "correct_and_admitted": correct and admitted,
                      "raw_answered": bool(answered), "checked_answered": bool(answered and admitted), "reason": reason})
    total = len(ids)
    def metrics(correct, answered):
        return {"accuracy": correct / total, "precision": correct / answered if answered else 0., "coverage": answered / total}
    return freeze({"schema_version": 1, "scheduled_count": total,
        "raw_metrics": metrics(counts["raw_correct"], counts["raw_answered"]),
        "checked_metrics": metrics(counts["correct_and_admitted"], counts["checked_answered"]),
        "raw_precision_defined": bool(counts["raw_answered"]), "checked_precision_defined": bool(counts["checked_answered"]),
        "counts": dict(counts), "producer_status_counts": dict(producer_statuses), "check_status_counts": dict(check_statuses),
        "rates": {"correct_and_admitted_per_scheduled": counts["correct_and_admitted"] / total,
                  "admitted_per_scheduled": counts["accepted"] / total,
                  "producer_failure_per_scheduled": counts["producer_failures"] / total},
        "case_results": cases,
        "metric_conventions": {
            "native_attempted": "Successfully decoded native choice other than the visible insufficient-information option",
            "parse_failure": "Operational unanswerable projection: remains incorrect on all-scheduled accuracy but outside attempted precision/coverage",
            "upstream_difference": "An arbitrary returned non-unsure string can count as attempted upstream; this strict JSON run makes no old fallback-harness equivalence claim",
            "zero_attempt_precision": "0 by reporting convention; precision_defined=False and answered=0 identify the undefined ratio",
            "incorrect_and_admitted": "Native key mismatch, including accepted unsure; incorrect_substantive_and_admitted excludes unsure",
            "produced_or_parse_failure": "Known returned-output statuses only; partial timeout/error response bytes are counted separately by transport accounting"},
        "interpretation": "Admission checks declared provenance obligations, not semantic correctness or entailment."})


def source_annotation_metrics(schedule, gold_ids, retrieved_ids):
    """Exact normalized bibliographic-ID agreement; caller supplies normalization.

    Empty/unknown annotations are outside recall's denominator, never recall=1.
    This does not treat an unannotated retrieved paper as irrelevant or false.
    """
    if not isinstance(schedule, (list, tuple)) or not schedule or len(set(schedule)) != len(schedule):
        raise ContractError("Source diagnostic requires a unique nonempty schedule")
    if not isinstance(gold_ids, Mapping) or not isinstance(retrieved_ids, Mapping) or set(gold_ids) != set(schedule) or set(retrieved_ids) != set(schedule):
        raise ContractError("Source diagnostic must retain all scheduled cases")
    cases, total_gold, hits, annotated_cases, any_hits, complete_hits = [], 0, 0, 0, 0, 0
    for key in schedule:
        gold, retrieved = evidence_ids(gold_ids[key]), evidence_ids(retrieved_ids[key])
        hit = gold & retrieved
        total_gold += len(gold); hits += len(hit)
        annotated_cases += bool(gold); any_hits += bool(hit); complete_hits += bool(gold and gold <= retrieved)
        cases.append({"id": key, "annotated_ids": sorted(gold), "retrieved_ids": sorted(retrieved), "matched_ids": sorted(hit),
                      "annotated_source_recall": len(hit) / len(gold) if gold else None})
    return freeze({"annotated_source_count": total_gold, "matched_annotated_source_count": hits,
        "annotated_source_recall": hits / total_gold if total_gold else None,
        "questions_with_annotations": annotated_cases, "questions_without_annotations": len(schedule)-annotated_cases,
        "questions_with_any_annotated_source_hit": any_hits, "questions_with_all_annotated_sources": complete_hits,
        "semantic_support": "unevaluated", "case_results": cases})
