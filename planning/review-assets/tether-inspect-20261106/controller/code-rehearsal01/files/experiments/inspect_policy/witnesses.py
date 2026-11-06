"""Prospective persistent fictional runtime inputs and a separately stored oracle.

Construction uses schema templates, never a validator or scored outcome. These
are declared fault-injection controls, not unseen examples or scientific cases.
"""
from copy import deepcopy
from pathlib import Path

from .archive import EXPERIMENTS
from .records import proof, publish
from equal_policy.cases import source_documents, seal_sources, file_bytes


def make_source(root, ident, mutate=None):
    root = Path(root)
    root.mkdir()
    folder = root / "input"
    folder.mkdir()
    documents = source_documents()
    documents["case"]["case_id"] = "FICTIONAL:INSPECT:" + ident
    second = deepcopy(documents["evidence"]["observations"][0])
    second["observation_id"] = "obs-2"
    second["statement"] = "A second invented observation for bounded claim commits."
    second["source_locator"] = {"row": 1}
    documents["evidence"]["observations"].append(second)
    if mutate is not None:
        mutate(documents)
    seal_sources(documents)
    for name, value in documents.items():
        (folder / (name + ".json")).write_bytes(file_bytes(value))
    descriptor = {"schema_version": 1, "control_id": ident, "operation": "prepare_run",
        "variant": "core_v2_catalog1", "paths": {name: "input/" + name + ".json" for name in ("case", "snapshot", "catalog", "scorer")},
        "options": {"review_enabled": True, "budget": {"max_retries": 0}}, "anchors": {}}
    publish(root / "descriptor.json", descriptor)
    return {"control_id": ident, "bundle_root": str(root),
            "descriptor": {"path": "descriptor.json", **proof(root / "descriptor.json")}}


def make_row(source, **changes):
    result = {"id": source["control_id"], "input": source,
        "budget": {"max_calls": 2, "max_input_tokens": 200, "max_output_tokens": 200,
                   "max_cost_usd": 0.0, "max_seconds": 30.0},
        "steps": [{"category": "genetics", "quote": {"input_tokens": 20, "output_tokens": 40, "cost_usd": 0.0},
                   "script": {"behavior": "success", "content": '{"observation_ids":["obs-1","obs-2"]}',
                              "usage": {"input_tokens": 10, "output_tokens": 8, "cost_usd": 0.0}, "delay_seconds": 0.0}}],
        "call_seconds": 3.0, "hook_fault": False, "hook_skip": False, "hook_mutate_request": False,
        "mutate_task_state": False, "commit_clock": None}
    result.update(changes)
    return result


def prepare_witnesses(output):
    """Create only inputs; caller freezes all bytes before any native execution."""
    output = Path(output).absolute()
    output.mkdir(parents=False, exist_ok=False)
    (output / "sources").mkdir()
    rows, expectations = [], []
    def add(ident, status="completed", calls=1, *, mutate=None, changes=None, fields=None):
        row = make_row(make_source(output / "sources" / ident, ident, mutate))
        if changes:
            changes(row)
        expected = {"status": status, "accounting.calls": calls, "provider_dispatches": calls}
        expected.update(fields or {})
        rows.append(row)
        expectations.append({"control_id": ident, "fields": expected})
        return row

    add("IX01-positive", fields={"accounting.measured_usage.input_tokens": 10, "accounting.estimated_usage.input_tokens": 0})
    add("IX02-zero-budget", "budget_exhausted", 0, changes=lambda row: row["budget"].update(max_calls=0))
    def future_program(docs):
        docs["case"]["task"] = "T6"
        docs["case"]["program"]["availability"]["record_public_at"] = "2025-01-01"
    add("IX02-future-program", "error", 0, mutate=future_program)
    add("IX02-future-scorer", "error", 0, mutate=lambda docs: docs["scorer"].update(training_label_available_max="2025-01-01"))
    add("IX03-request-mutation", "error", 1, changes=lambda row: row.update(hook_mutate_request=True), fields={"provider_dispatches": 0, "provider_entries": 1})
    add("IX04-nested-state", changes=lambda row: row.update(mutate_task_state=True))
    add("IX05-provider-error", "error", changes=lambda row: row["steps"][0]["script"].update(behavior="error"), fields={"accounting.estimated_usage.input_tokens": 20})
    def timeout(row):
        row["call_seconds"] = 0.05
        row["steps"][0]["script"].update(behavior="sleep", delay_seconds=1.0)
    add("IX05-timeout", "timeout", changes=timeout, fields={"accounting.estimated_usage.output_tokens": 40})
    def malformed(row):
        row["steps"][0]["script"]["content"] = "not a JSON selection"
        row["steps"][0]["script"]["usage"]["input_tokens"] = 21
        row["steps"].append(deepcopy(row["steps"][0]))
    add("IX05-malformed", "error", changes=malformed, fields={"accounting.measured_usage.input_tokens": 0, "accounting.estimated_usage.input_tokens": 20})
    def overquote(row):
        row["steps"][0]["script"]["usage"]["input_tokens"] = 21
        row["steps"].append(deepcopy(row["steps"][0]))
    add("IX05-overquote", "budget_exhausted", changes=overquote, fields={"accounting.measured_usage.input_tokens": 21, "accounting.estimated_usage.input_tokens": 0})
    add("IX07-optional-hook-error", changes=lambda row: row.update(hook_fault=True), fields={"telemetry_faults.0": "declared_optional_hook_exception_after_durable_before_event"})
    add("IX07-required-hook-omitted", "error", changes=lambda row: row.update(hook_skip=True))
    def expires(row):
        row["commit_clock"] = [0.0, 1.0]
        row["steps"].append(deepcopy(row["steps"][0]))
    add("IX10-commit-prefix", "budget_exhausted", changes=expires, fields={"commits.0.prediction.reason": "run_incomplete", "commits.0.prediction.probability": None})
    add("IX10-duplicate-selection", "error", changes=lambda row: row["steps"][0]["script"].update(content='{"observation_ids":["obs-1","obs-1"]}'))
    add("IX10-unoffered-selection", "error", changes=lambda row: row["steps"][0]["script"].update(content='{"observation_ids":["unoffered"]}'))
    add("IX10-wrong-category", "error", changes=lambda row: row["steps"][0].update(category="expression"))
    row_proof = publish(output / "rows.json", rows)
    oracle_proof = publish(output / "oracle.json", {"schema_version": 1, "cases": expectations,
        "scope": "prospectively_declared_fictional_fault_controls_not_scientific_results"})
    return {"schema_version": 1, "rows": {"path": str(output / "rows.json"), **row_proof},
            "oracle": {"path": str(output / "oracle.json"), **oracle_proof}, "scheduled": len(rows),
            "separate_process_witnesses": ["IX06-owned-child-interruption", "IX08-concurrent-reservation", "IX09-process-supervision"],
            "scope": "inputs_only_not_executed", "positive_review_retry": "archive_only"}
