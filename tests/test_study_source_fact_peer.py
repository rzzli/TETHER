"""Independent fictional controls derived from SOURCE_FACT_EVALUATION.md.

These fixtures use original temporary JSON bytes and v2 source contracts. They do
not use prior candidates, expert responses, clinical labels or network resources.
"""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import ContractError, canonical, encode, sha256_file
from asof.study.source_fact_adapters import adapt_output
from asof.study.source_fact_evaluation import aggregate_cells, score_cell
from asof.study.source_fact_sources import compile_reference, verify_reference


_FACT_KEYS = ("fact_id", "value", "unit", "source", "unknown_reason")
_MEASUREMENTS = (
    "beta", "standardError", "betaConfidenceIntervalLower",
    "betaConfidenceIntervalUpper", "oddsRatio",
)


def _cases(names, values):
    def decorate(function):
        function._peer_cases = (names, values)
        return function
    return decorate


_raises = unittest.TestCase().assertRaises


def _fixture(tmp_path, *, row=None, fields=None, primary=None, collection=None,
             two_sources=False, task_id="fictional-peer-case", source_identity=None):
    """Create every admitted value in this test, then independently hash its bytes."""
    row = {"targetId": "FICT_TARGET", "diseaseId": "FICT_INDICATION", "beta": 1.0} if row is None else row
    row = {"targetId": "FICT_TARGET", "diseaseId": "FICT_INDICATION", **row}
    if fields is None:
        fields = [("beta", "reported_measurement", "measurement", None)]
    cutoff = datetime(2024, 1, 2, tzinfo=timezone.utc)
    public = date(2020, 1, 1)
    availability = Availability(public, public, public, public, public,
                                "fictional_control", None)
    nodes, records, task_fields = [], [], []
    for index in range(2 if two_sources else 1):
        record_key = f"row-{index}"
        path = tmp_path / f"fictional-{index}.json"
        path.write_bytes(canonical(row))
        source_id = source_identity or f"source-{index}"
        nodes.append(SourceNode(source_id, "fictional", "fictional-release-1",
            path.name, sha256_file(path), "agent_evidence", availability,
            TemporalClass.CONTEMPORARY, "https://example.invalid/fictional"))
        records.append({"record_key": record_key, "source_id": source_id,
            "locator": {"format": "json", "pointer": ""},
            "identity": {"targetId": "FICT_TARGET", "diseaseId": "FICT_INDICATION"}})
        task_fields.extend({"record_key": record_key, "field": field,
            "family": family, "group": f"{record_key}-{group}",
            "unit_field": unit_field, "empty_policy": "unknown"}
            for field, family, group, unit_field in fields)
    task = {"schema_version": 1, "task_id": task_id,
        "scope": {"target_id": "FICT_TARGET", "indication_id": "FICT_INDICATION",
            "target_namespace_version": "fictional-target-v1",
            "indication_namespace_version": "fictional-indication-v1",
            "action": None, "modality": None, "tissue": None},
        "cutoff": cutoff.isoformat(), "profile": "synthetic_demo",
        "primary_families": primary or ["reported_measurement"],
        "records": records, "fields": task_fields, "joins": [],
        "collection": collection or {"status": "selected_records",
            "reason": "Fictional selected records only; no biological absence claim."}}
    snapshot = Snapshot(2, "fictional-peer-snapshot", Profile.DEMO,
        cutoff.date(), False, (), tuple(nodes), raw_root=str(tmp_path), origin_at=cutoff)
    catalog = {"fictional": {"roles": ["agent_evidence"]}}
    reference = compile_reference(task, snapshot, tmp_path, catalog,
                                  deadline=time.monotonic() + 30)
    return reference, task, snapshot, catalog


def _output(reference, *, selected=None, status="answered", reason=None):
    document = reference.document
    facts = document["facts"] if selected is None else selected
    return {"schema_version": 1, "task_id": document["task_id"],
        "task_sha256": document["task_sha256"], "status": status,
        "facts": [{key: encode(fact[key]) for key in _FACT_KEYS} for fact in facts],
        "collection_status": document["collection"]["status"], "reason": reason}


def _adapt(reference, output):
    return adapt_output(canonical(output), wire_format="typed_facts_v1",
        task_id=reference.document["task_id"], task_sha256=reference.document["task_sha256"])


def _score(reference, output=None, **kwargs):
    raw = canonical(_output(reference) if output is None else output)
    return score_cell(reference, raw, cell_id=kwargs.pop("cell_id", "cell-1"), **kwargs)


def _plan(reference, *cell_ids):
    return [{"cell_id": cell_id, "task_id": reference.document["task_id"],
        "task_sha256": reference.document["task_sha256"],
        "reference_sha256": reference.fingerprint} for cell_id in cell_ids]


def test_peer_group_denominator_is_not_component_denominator(tmp_path):
    fields = [(name, "reported_measurement", "four" if i < 4 else "one", None)
              for i, name in enumerate(_MEASUREMENTS)]
    fields.append(("sampleSize", "reported_context", "context", None))
    reference, *_ = _fixture(tmp_path,
        row={**{name: float(i + 1) for i, name in enumerate(_MEASUREMENTS)}, "sampleSize": 20},
        fields=fields, primary=["reported_measurement", "reported_context"])
    selected = [f for f in reference.document["facts"] if f["field"] != "oddsRatio"]
    result = _score(reference, _output(reference, selected=selected,
        status="partial", reason="One requested group omitted."))
    measurement = result["family_scores"]["reported_measurement"]
    assert measurement["answerable_facts"] == 5
    assert measurement["matched_facts"] == 4
    assert measurement["answerable_groups"] == 2
    assert math.isclose(measurement["coverage"], 0.5)
    assert result["primary"]["answerable_groups"] == 3
    assert math.isclose(result["primary"]["coverage"], 2 / 3)
    assert result["primary"]["passes"] == {"60": True, "80": False, "100": False}
    assert not result["critical_errors"]
    assert result["completion"] is False


def test_peer_provider_and_identifiers_do_not_create_measurement_coverage(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": None, "score": 0.9, "studyLocusId": "same-id"},
        fields=[("beta", "reported_measurement", "missing", None),
                ("score", "provider_metric", "provider", None),
                ("studyLocusId", "identity_linkage", "identifier", None)])
    result = _score(reference)
    measurement = result["family_scores"]["reported_measurement"]
    assert measurement["answerable_facts"] == 0
    assert measurement["answerable_groups"] == 0
    assert measurement["coverage"] is None
    assert result["measurement_pass"] is None
    assert result["primary"]["coverage"] is None
    assert all(value is None for value in result["primary"]["passes"].values())
    assert result["completion"] is False
    assert not result["critical_errors"]


@_cases(("native", "wrong"), [
    (True, 1), (1, True), (1, 1.0), (1.0, 1), (-0.0, 0.0), (0.0, -0.0),
    ([1, 2], [2, 1]), ([1, True], [1, 1]),
])
def test_peer_native_types_signed_zero_and_list_order_are_exact(tmp_path, native, wrong):
    # Numeric measurement QC is a dated pre-generation clarification. Other
    # source-native types remain literal projections in the context family.
    is_measurement = type(native) in (int, float)
    field = "beta" if is_measurement else "ancestry"
    family = "reported_measurement" if is_measurement else "reported_context"
    reference, *_ = _fixture(tmp_path, row={field: native},
        fields=[(field, family, "typed-native-value", None)], primary=[family])
    assert _score(reference)["completion"] is True
    output = _output(reference)
    output["facts"][0]["value"] = wrong
    result = _score(reference, output)
    assert result["family_scores"][family]["matched_facts"] == 0
    assert result["critical_errors"]
    assert result["completion"] is False


def test_peer_native_units_are_bound_to_original_unit_field(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": 2.0, "originalUnit": "fictional mg"},
        fields=[("beta", "reported_measurement", "measurement", "originalUnit")])
    assert reference.document["facts"][0]["unit"] == "fictional mg"
    output = _output(reference)
    output["facts"][0]["unit"] = "fictional g"
    result = _score(reference, output)
    assert result["critical_errors"]
    assert result["family_scores"]["reported_measurement"]["matched_facts"] == 0


@_cases(("key", "wrong"), [
    ("source_id", "another-source"), ("sha256", "0" * 64),
    ("release_id", "another-release"), ("field", "standardError"),
    ("locator", {"format": "json", "pointer": "/another-record"}),
])
def test_peer_correct_value_with_wrong_physical_binding_is_critical(tmp_path, key, wrong):
    reference, *_ = _fixture(tmp_path)
    output = _output(reference)
    output["facts"][0]["source"][key] = wrong
    result = _score(reference, output)
    assert result["critical_errors"]
    assert result["completion"] is False
    assert result["family_scores"]["reported_measurement"]["matched_facts"] == 0


def test_peer_provider_id_collision_cannot_alias_fact_ids_across_files(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": 2.0, "studyLocusId": "provider-collision"},
        fields=[("beta", "reported_measurement", "measurement", None),
                ("studyLocusId", "identity_linkage", "identity", None)], two_sources=True)
    facts = reference.document["facts"]
    assert len(facts) == len({fact["fact_id"] for fact in facts}) == 4
    assert len({f["source"]["source_id"] for f in facts}) == 2
    assert _score(reference)["completion"] is True
    output = _output(reference)
    left, right = [f for f in output["facts"] if f["value"] == 2.0]
    right["source"] = dict(left["source"])
    assert _score(reference, output)["critical_errors"]


def test_peer_null_empty_and_schema_absence_are_distinct_unknowns(tmp_path):
    fields = [(name, "reported_measurement", name, None) for name in _MEASUREMENTS[:3]]
    reference, *_ = _fixture(tmp_path, row={"beta": None, "standardError": ""}, fields=fields)
    facts = reference.document["facts"]
    assert all(f["value"] is None and f["unknown_reason"] for f in facts)
    assert len({f["unknown_reason"] for f in facts}) == 3
    result = _score(reference)
    assert not result["critical_errors"]
    assert result["primary"]["coverage"] is None
    assert result["completion"] is False
    output = _output(reference)
    output["facts"][0]["unknown_reason"] = output["facts"][1]["unknown_reason"]
    assert _score(reference, output)["critical_errors"]


def test_peer_invented_value_for_expected_null_is_critical(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": None})
    output = _output(reference)
    output["facts"][0].update(value=0.0, unknown_reason=None)
    result = _score(reference, output)
    assert result["critical_errors"]
    assert result["primary"]["coverage"] is None


def test_peer_correct_unknown_group_has_no_denominator_or_error(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": 1.0, "standardError": None},
        fields=[("beta", "reported_measurement", "answerable", None),
                ("standardError", "reported_measurement", "unknown-only", None)])
    result = _score(reference)
    measurement = result["family_scores"]["reported_measurement"]
    assert measurement["answerable_facts"] == 1
    assert measurement["answerable_groups"] == 1
    assert measurement["coverage"] == 1.0
    assert not result["critical_errors"]
    assert result["completion"] is True


def test_peer_abstention_has_no_coverage_credit(tmp_path):
    reference, *_ = _fixture(tmp_path)
    output = _output(reference, selected=[], status="abstained",
        reason="Fictional generator explicitly abstains.")
    result = _score(reference, output)
    assert result["primary"]["coverage"] == 0.0
    assert result["completion"] is False
    assert not result["critical_errors"]


@_cases("conflicting", [False, True])
def test_peer_duplicate_emissions_are_preserved_and_critical(tmp_path, conflicting):
    reference, *_ = _fixture(tmp_path)
    output = _output(reference)
    duplicate = encode(output["facts"][0])
    if conflicting:
        duplicate["value"] = -123.0
    output["facts"].append(duplicate)
    adapted = _adapt(reference, output)
    assert adapted["status"] == "scorable"
    assert len(adapted["output"]["facts"]) == 2
    assert adapted["output"]["facts"][1]["value"] == duplicate["value"]
    result = _score(reference, output)
    assert result["critical_errors"]
    assert result["completion"] is False


def test_peer_unknown_fact_id_is_critical(tmp_path):
    reference, *_ = _fixture(tmp_path)
    output = _output(reference)
    output["facts"][0]["fact_id"] = "unknown-slot"
    result = _score(reference, output)
    assert result["critical_errors"]
    assert result["family_scores"]["reported_measurement"]["matched_facts"] == 0


@_cases(("count", "coverage", "completion"), [(3, 0.6, False), (4, 0.8, True), (5, 1.0, True)])
def test_peer_declared_thresholds_use_reference_groups(tmp_path, count, coverage, completion):
    reference, *_ = _fixture(tmp_path, row={name: i + 1.0 for i, name in enumerate(_MEASUREMENTS)},
        fields=[(name, "reported_measurement", name, None) for name in _MEASUREMENTS])
    output = _output(reference, selected=reference.document["facts"][:count],
        status="partial", reason="Fictional retained subset.")
    result = _score(reference, output)
    assert math.isclose(result["primary"]["coverage"], coverage)
    assert result["completion"] is completion
    assert result["primary"]["passes"]["60"] is True
    assert result["primary"]["passes"]["80"] is (count >= 4)
    assert result["primary"]["passes"]["100"] is (count == 5)


def test_peer_correct_bounded_insufficient_input_has_no_coverage_pass(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": None}, collection={
        "status": "incomplete", "reason": "Fictional collection is missing its measurement row."})
    output = _output(reference, selected=[], status="insufficient_input",
        reason="Only the frozen incomplete collection is available.")
    result = _score(reference, output)
    assert result["correct_missing_input"] is True
    assert result["primary"]["coverage"] is None
    assert result["measurement_pass"] is None
    assert result["completion"] is False
    output["collection_status"] = "selected_records"
    assert _score(reference, output)["correct_missing_input"] is False


def test_peer_adapter_does_not_open_sources_or_backfill_omissions(tmp_path):
    reference, *_ = _fixture(tmp_path, row={"beta": 1.0, "standardError": 0.2},
        fields=[("beta", "reported_measurement", "m", None),
                ("standardError", "reported_measurement", "m", None)])
    output = _output(reference, selected=reference.document["facts"][:1],
        status="partial", reason="Only one literal value was emitted.")
    raw = canonical(output)
    def deny_open(*args, **kwargs):
        raise AssertionError("The adapter must parse retained bytes without source reads")
    with patch.object(Path, "open", deny_open):
        adapted = adapt_output(raw, wire_format="typed_facts_v1",
            task_id=reference.document["task_id"], task_sha256=reference.document["task_sha256"])
    assert len(adapted["output"]["facts"]) == 1
    assert adapted["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert adapted["raw_bytes"] == len(raw)
    output["facts"][0]["value"] = 999.0
    assert adapted["output"]["facts"][0]["value"] != 999.0
    with _raises(TypeError):
        adapted["output"]["facts"][0]["source"]["field"] = "changed"


@_cases("raw", [
    b'{"schema_version":1,"schema_version":1}', b'{"value":NaN}',
    b'{"value":Infinity}', b'[]', b'null', b'{"facts":', b'\xff',
])
def test_peer_malformed_emitted_bytes_cannot_be_rescued(tmp_path, raw):
    reference, *_ = _fixture(tmp_path)
    result = score_cell(reference, raw, cell_id="cell-1")
    assert result["terminal"] == "malformed"
    assert result["adapter_status"] == "malformed"
    assert result["primary"]["coverage"] is None
    assert result["completion"] is False
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()


@_cases("replacement", [b'"value":1.0,"value":2.0', b'"value":NaN', b'"value":Infinity'])
def test_peer_duplicate_key_and_nonfinite_inside_otherwise_valid_output_are_malformed(tmp_path, replacement):
    reference, *_ = _fixture(tmp_path)
    raw = canonical(_output(reference)).replace(b'"value":1.0', replacement)
    result = score_cell(reference, raw, cell_id="invalid-native-output")
    assert result["adapter_status"] == "malformed"
    assert result["primary"]["coverage"] is None
    assert result["completion"] is False


def test_peer_legacy_quotes_are_unscorable_typed_measurements(tmp_path):
    reference, *_ = _fixture(tmp_path)
    raw = canonical({"answer_status": "answered", "claims": [{
        "kind": "source_report", "text": "Fictional beta 1.0",
        "quote_refs": ["Q0"], "limitations": []}], "unresolved": [],
        "abstention_reason": None})
    result = score_cell(reference, raw, cell_id="legacy", wire_format="interpretation_v2")
    assert result["adapter_status"] == "unscorable_legacy"
    assert result["primary"]["coverage"] is None
    assert result["completion"] is False


@_cases("terminal", ["failed", "timeout", "interrupted", "unexecuted", "malformed"])
def test_peer_nonreturn_terminals_never_rescue_partial_or_complete_bytes(tmp_path, terminal):
    reference, *_ = _fixture(tmp_path)
    raw = canonical(_output(reference))
    result = score_cell(reference, raw, cell_id="failed-cell", terminal=terminal)
    assert result["terminal"] == terminal
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["primary"]["coverage"] is None
    assert result["completion"] is False


def test_peer_aggregate_retains_unexecuted_cell_in_denominator(tmp_path):
    reference, *_ = _fixture(tmp_path)
    completed = _score(reference, cell_id="done")
    unexecuted = score_cell(reference, None, cell_id="never-ran", terminal="unexecuted")
    summary = aggregate_cells(_plan(reference, "done", "never-ran"), [completed, unexecuted])
    assert summary["planned_cells"] == 2
    assert summary["terminal_counts"]["unexecuted"] == 1
    assert summary["completion_count"] == 1
    assert summary["completion_rate"] == 0.5


@_cases("fault", ["missing", "duplicate", "unscheduled", "task", "task_hash", "reference_hash"])
def test_peer_aggregate_rejects_missing_duplicate_and_substituted_cells(tmp_path, fault):
    reference, *_ = _fixture(tmp_path)
    plans = _plan(reference, "a", "b")
    a, b = _score(reference, cell_id="a"), _score(reference, cell_id="b")
    results = [a, b]
    if fault == "missing":
        results = [a]
    elif fault == "duplicate":
        results = [a, a]
    elif fault == "unscheduled":
        results = [a, _score(reference, cell_id="c")]
    else:
        key = {"task": "task_id", "task_hash": "task_sha256", "reference_hash": "reference_sha256"}[fault]
        plans[1][key] = "substitution" if key == "task_id" else "0" * 64
    with _raises(ContractError):
        aggregate_cells(plans, results)


def test_peer_score_requires_verified_reference_and_retained_bytes(tmp_path):
    reference, *_ = _fixture(tmp_path)
    raw = canonical(_output(reference))
    with _raises(ContractError):
        score_cell(encode(reference.document), raw, cell_id="forged-reference")
    with _raises(ContractError):
        score_cell(reference, _adapt(reference, _output(reference)), cell_id="forged-raw-binding")
    with _raises(TypeError):
        reference.document["facts"][0]["value"] = 999.0


def test_peer_aggregate_cannot_accept_manually_rescored_cell(tmp_path):
    reference, *_ = _fixture(tmp_path)
    result = encode(score_cell(reference, None, cell_id="never-ran", terminal="unexecuted"))
    result["completion"] = True
    result["primary"]["coverage"] = 1.0
    with _raises(ContractError):
        aggregate_cells(_plan(reference, "never-ran"), [result])


def test_peer_compile_rejects_corrupted_original_source(tmp_path):
    reference, task, snapshot, catalog = _fixture(tmp_path)
    (tmp_path / "fictional-0.json").write_bytes(canonical({
        "targetId": "FICT_TARGET", "diseaseId": "FICT_INDICATION", "beta": 999.0}))
    with _raises(ContractError):
        compile_reference(task, snapshot, tmp_path, catalog, deadline=time.monotonic() + 30)
    assert reference.document["scope"]["action"] is None
    assert reference.document["scope"]["modality"] is None
    assert reference.document["scope"]["tissue"] is None


def test_peer_reference_replay_rejects_answer_and_original_byte_tampering(tmp_path):
    reference, task, snapshot, catalog = _fixture(tmp_path)
    document = encode(reference.document)
    document["facts"][0]["value"] = 999.0
    with _raises(ContractError):
        verify_reference(document, reference.fingerprint, task, snapshot, tmp_path,
                         catalog, deadline=time.monotonic() + 30)
    # Even a caller-computed hash of a changed expected value is insufficient:
    # source replay must recover the original value from the independently pinned file.
    with _raises(ContractError):
        verify_reference(document, hashlib.sha256(canonical(document)).hexdigest(),
            task, snapshot, tmp_path, catalog, deadline=time.monotonic() + 30)
    (tmp_path / "fictional-0.json").write_bytes(canonical({
        "targetId": "FICT_TARGET", "diseaseId": "FICT_INDICATION", "beta": 999.0}))
    with _raises(ContractError):
        verify_reference(encode(reference.document), reference.fingerprint,
            task, snapshot, tmp_path, catalog, deadline=time.monotonic() + 30)


@_cases("fault", ["unit-513", "task-id-513", "source-id-513", "context-string-8193"])
def test_peer_every_compiled_reference_has_an_emittable_exact_projection(tmp_path, fault):
    # A compiler-accepted case must admit the declared exact projection ceiling.
    # These values cannot be represented by the frozen common output bounds.
    options = {
        "unit-513": {"row": {"beta": 1.0, "originalUnit": "u" * 513},
            "fields": [("beta", "reported_measurement", "m", "originalUnit")]},
        "task-id-513": {"task_id": "t" * 513},
        "source-id-513": {"source_identity": "s" * 513},
        "context-string-8193": {"row": {"ancestry": "a" * 8193},
            "fields": [("ancestry", "reported_context", "context", None)],
            "primary": ["reported_context"]},
    }
    with _raises(ContractError):
        _fixture(tmp_path, **options[fault])


class SourceFactPeerTests(unittest.TestCase):
    """Use unittest so the default installed package needs no testing extra."""


def _install_cases():
    workspace = Path(__file__).resolve().parents[1]
    temp_root = (workspace / "data" / "cache" / "preprint-p03-peer-tmp").resolve()
    assert temp_root.is_relative_to(workspace)
    temp_root.mkdir(parents=True, exist_ok=True)
    for name, function in tuple(globals().items()):
        if not name.startswith("test_peer_") or not callable(function):
            continue
        names, values = getattr(function, "_peer_cases", ((), [()]))
        names = (names,) if isinstance(names, str) else names
        for index, value in enumerate(values):
            parameters = dict(zip(names, (value,) if len(names) == 1 else value))
            def run(self, original=function, arguments=parameters):
                with tempfile.TemporaryDirectory(dir=temp_root) as directory:
                    original(Path(directory), **arguments)
            run.__name__ = name + (f"_{index:02d}" if names else "")
            setattr(SourceFactPeerTests, run.__name__, run)


_install_cases()


if __name__ == "__main__":
    unittest.main()
