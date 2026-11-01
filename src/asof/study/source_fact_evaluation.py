"""Grouped literal-report scoring, separate from clinical/scientific validity.

Only source-verified references and actual emitted bytes enter this scorer.
ScoredCell is a copied immutable in-process result, not a serialized receipt or
an OS security boundary. Persisted results must be replayed, never promoted back
to a verified result merely by trusting their own hashes.
"""

from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
import hashlib
import re

from asof.serde import ContractError, fingerprint, freeze
from asof.wire import same_json
from .source_fact_adapters import adapt_output, WIRE_FORMATS


FAMILIES = ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")
TERMINALS = ("returned", "malformed", "failed", "timeout", "interrupted", "unexecuted")
_TOKEN = object()


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _identifier(value):
    return type(value) is str and bool(value.strip()) and len(value) <= 512


def _hash(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


class ScoredCell(Mapping):
    """Immutable result obtainable only through scoring in the trusted process."""

    __slots__ = ("_document",)

    def __init__(self, document, *, _token=None):
        _need(_token is _TOKEN, "Scored cells require raw-output replay")
        object.__setattr__(self, "_document", freeze(document))

    def __setattr__(self, name, value):
        raise TypeError("Scored cells are immutable")

    def __getitem__(self, key):
        return self._document[key]

    def __iter__(self):
        return iter(self._document)

    def __len__(self):
        return len(self._document)


def _families(facts, matched, *, scorable):
    """Use exact fractions for thresholds; export floating display coverage."""
    scores, groups = {}, {}
    for fact in facts:
        if fact["value"] is not None:
            key = (fact["record_key"], fact["family"], fact["group"])
            groups.setdefault(key, []).append(fact["fact_id"])
    for family in FAMILIES:
        selected = {key: ids for key, ids in groups.items() if key[1] == family}
        fractions = {key: Fraction(sum(i in matched for i in ids), len(ids))
                     for key, ids in selected.items()}
        coverage = (sum(fractions.values(), Fraction()) / len(fractions)
                    if fractions and scorable else None)
        scores[family] = dict(
            answerable_facts=sum(len(ids) for ids in selected.values()),
            matched_facts=sum(sum(i in matched for i in ids) for ids in selected.values()) if scorable else None,
            answerable_groups=len(selected),
            group_coverage=[dict(record_key=key[0], group=key[2],
                                 answerable_facts=len(selected[key]),
                                 matched_facts=sum(i in matched for i in selected[key]) if scorable else None,
                                 coverage=float(value) if scorable else None)
                            for key, value in fractions.items()],
            coverage=float(coverage) if coverage is not None else None,
        )
    return scores, groups


def score_cell(reference, raw_output, *, cell_id, terminal="returned", wire_format="typed_facts_v1"):
    """Score actual retained output; non-return terminal events cannot be rescued.

    Source verification occurs when the reference is compiled/replayed. This
    function makes no filesystem or model calls and does not parse partial bytes
    after failure/timeout/interruption. All return fields are deeply immutable.
    """
    from .source_fact_sources import VerifiedReference

    _need(isinstance(reference, VerifiedReference), "A source-verified reference object is required")
    document = reference.document
    _need(reference.fingerprint == fingerprint(document), "Reference changed after source verification")
    _need(_identifier(cell_id), "Invalid cell ID")
    _need(type(terminal) is str and terminal in TERMINALS, "Unknown terminal disposition")
    _need(type(wire_format) is str and wire_format in WIRE_FORMATS, "Unknown adapter wire format")
    _need(raw_output is None or type(raw_output) is bytes, "Retained output must be bytes or absent")
    _need(terminal != "returned" or raw_output is not None, "Returned output bytes are required")
    facts = document["facts"]
    expected = {fact["fact_id"]: fact for fact in facts}
    _need(len(expected) == len(facts), "Duplicate reference fact identity")
    _need(all(fact["family"] in FAMILIES for fact in facts), "Unsupported reference fact family")
    primary_families = tuple(document["primary_families"])
    _need(bool(primary_families) and len(primary_families) == len(set(primary_families))
          and set(primary_families) <= set(FAMILIES), "Invalid reference primary families")
    result = dict(schema_version=1, cell_id=cell_id, task_id=document["task_id"],
                  task_sha256=document["task_sha256"], reference_sha256=reference.fingerprint,
                  terminal=terminal, received_terminal=terminal, wire_format=wire_format,
                  adapter_status="not_attempted", raw_sha256=hashlib.sha256(raw_output).hexdigest()
                  if raw_output is not None else None,
                  raw_bytes=len(raw_output) if raw_output is not None else None,
                  failure_reason=None, critical_errors=[], completion=False,
                  correct_missing_input=None)
    adapted, output, scorable, eligible = None, None, False, False
    if terminal == "returned":
        adapted = adapt_output(raw_output, wire_format=wire_format,
                               task_id=document["task_id"], task_sha256=document["task_sha256"])
        result["adapter_status"] = adapted["status"]
        result["failure_reason"] = adapted["error"]
        if adapted["status"] == "malformed":
            result["terminal"] = "malformed"
        elif adapted["status"] == "unscorable_legacy":
            result["failure_reason"] = "legacy_prose_has_no_emitted_typed_facts"
        else:
            output, scorable = adapted["output"], True
    else:
        result["failure_reason"] = "terminal_" + terminal

    matched = set()
    if scorable:
        errors = result["critical_errors"]
        counts = Counter(fact["fact_id"] for fact in output["facts"])
        for identifier, count in counts.items():
            if count > 1:
                errors.append(dict(fact_id=identifier, reason="duplicate_emission"))
        for fact in output["facts"]:
            identifier = fact["fact_id"]
            original = expected.get(identifier)
            if original is None:
                errors.append(dict(fact_id=identifier, reason="unknown_fact_id"))
                continue
            if not all(same_json(fact[key], original[key])
                       for key in ("value", "unit", "source", "unknown_reason")):
                errors.append(dict(fact_id=identifier, reason="value_unit_source_or_unknown_mismatch"))
            elif original["value"] is not None and counts[identifier] == 1:
                matched.add(identifier)
        collection_correct = output["collection_status"] == document["collection"]["status"]
        if not collection_correct:
            errors.append(dict(fact_id=None, reason="collection_status_mismatch"))
        eligible = output["status"] in ("answered", "partial") and collection_correct and not errors
        # Abstention/insufficient states have no facts by the adapter contract.
        result["answer_status"] = output["status"]
        result["emitted_facts"] = len(output["facts"])
    else:
        result.update(answer_status=None, emitted_facts=None)

    family_scores, groups = _families(facts, matched, scorable=scorable)
    primary_groups = {key: ids for key, ids in groups.items() if key[1] in primary_families}
    primary_coverage = (sum((Fraction(sum(i in matched for i in ids), len(ids))
                             for ids in primary_groups.values()), Fraction()) / len(primary_groups)
                        if primary_groups and scorable else None)
    thresholds = {"60": Fraction(3, 5), "80": Fraction(4, 5), "100": Fraction(1)}
    passes = {label: bool(eligible and primary_coverage >= threshold)
              if primary_coverage is not None else None for label, threshold in thresholds.items()}
    measurement = family_scores["reported_measurement"]
    measurement_groups = {key: ids for key, ids in groups.items() if key[1] == "reported_measurement"}
    measurement_coverage = (sum((Fraction(sum(i in matched for i in ids), len(ids))
                                 for ids in measurement_groups.values()), Fraction()) / len(measurement_groups)
                            if measurement_groups and scorable else None)
    measurement_pass = (bool(eligible and measurement_coverage >= Fraction(4, 5))
                        if measurement_coverage is not None else None)
    result.update(family_scores=family_scores,
                  primary=dict(families=primary_families, answerable_groups=len(primary_groups),
                               coverage=float(primary_coverage) if primary_coverage is not None else None,
                               passes=passes),
                  measurement_pass=measurement_pass, completion=passes["80"] is True,
                  measurement_answerable_facts=measurement["answerable_facts"],
                  scientific_validation="not_established", provider_spending_incurred=False)
    if not groups:
        result["correct_missing_input"] = bool(
            scorable and output["status"] == "insufficient_input"
            and output["collection_status"] == document["collection"]["status"]
            and not result["critical_errors"])
    return ScoredCell(result, _token=_TOKEN)


def aggregate_cells(planned_cells, results):
    """Reconcile the complete planned schedule against source/output-bound cells.

    There is no listwise deletion of failed, unexecuted or insufficient cells.
    The schedule is independent of outputs; one task cannot switch references.
    Persisted dictionaries must be replayed through score_cell before aggregation.
    """
    _need(isinstance(planned_cells, (list, tuple)) and bool(planned_cells), "Nonempty planned cells required")
    _need(isinstance(results, (list, tuple)), "Results must be an explicit sequence")
    plan, task_bindings = {}, {}
    keys = {"cell_id", "task_id", "task_sha256", "reference_sha256"}
    for cell in planned_cells:
        _need(isinstance(cell, Mapping) and set(cell) == keys, "Invalid planned cell shape")
        _need(_identifier(cell["cell_id"]) and _identifier(cell["task_id"])
              and _hash(cell["task_sha256"]) and _hash(cell["reference_sha256"]), "Invalid planned cell binding")
        _need(cell["cell_id"] not in plan, "Duplicate scheduled cell")
        binding = (cell["task_sha256"], cell["reference_sha256"])
        _need(cell["task_id"] not in task_bindings or task_bindings[cell["task_id"]] == binding,
              "A task cannot switch its source/reference denominator")
        task_bindings[cell["task_id"]] = binding
        plan[cell["cell_id"]] = dict(cell)
    accepted = {}
    for result in results:
        _need(isinstance(result, ScoredCell), "Aggregate requires replayed scored cells")
        identifier = result["cell_id"]
        _need(identifier in plan, "Unscheduled result cell")
        _need(identifier not in accepted, "Duplicate terminal result cell")
        _need(all(result[key] == value for key, value in plan[identifier].items()), "Scheduled task/reference binding mismatch")
        accepted[identifier] = result
    _need(set(accepted) == set(plan), "Missing terminal result; record an explicit unexecuted cell")
    ordered = [accepted[identifier] for identifier in plan]
    terminals = dict.fromkeys(TERMINALS, 0)
    for result in ordered:
        terminals[result["terminal"]] += 1
    completed = sum(result["completion"] for result in ordered)
    scorable = sum(result["adapter_status"] == "scorable" for result in ordered)
    missing = sum(result["correct_missing_input"] is True for result in ordered)
    return freeze(dict(schema_version=1, planned_cells=len(plan), task_count=len(task_bindings),
                       terminal_counts=terminals, scorable_cells=scorable,
                       completion_count=completed, completion_rate=completed / len(plan),
                       correct_missing_input_count=missing,
                       correct_missing_input_denominator=sum(result["correct_missing_input"] is not None for result in ordered),
                       case_results=ordered, result_sha256=tuple(fingerprint(result) for result in ordered),
                       scientific_validation="not_established"))
