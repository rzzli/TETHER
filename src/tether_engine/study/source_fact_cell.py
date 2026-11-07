"""Bounded source-only reporting arm cells; no launcher, references or scoring.

Every cell reserves a fresh directory. Retention callbacks write exact transport
bytes exclusively and append fsynced accounting to the caller's existing journal.
Only actual dispatched calls are charged, using measured usage when available or
the conservative reservation when unknown. The retry policy is always none.
"""

from collections.abc import Mapping
import hashlib
import math
import os
from pathlib import Path
import re
import time

from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, freeze
from tether_engine.workflow import Budget
from .source_fact_adapters import adapt_output
from .source_fact_reporting import literal_report, render_reporting_prompt, reporting_view
from .source_fact_transport import TransportResult, prepare_completion


ARMS = ("exact_literal_assembler", "always_abstain", "plain_same_model_typed_report",
        "tether_declared_two_stage_typed_report")
_ZERO = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)


class _BudgetExhausted(ContractError):
    pass


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _write_exclusive(path, raw):
    """Retain bytes without replacement, including fsync before journal admission."""
    _need(type(raw) is bytes, "Retention requires exact bytes")
    with Path(path).open("xb", buffering=0) as stream:
        remaining = memoryview(raw)
        while remaining:
            count = stream.write(remaining)
            if not count:
                raise OSError("Reporting byte retention failed")
            remaining = remaining[count:]
        os.fsync(stream.fileno())
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _usage(value):
    _need(isinstance(value, Mapping) and set(value) == set(_ZERO)
          and all(type(value[key]) is int and value[key] >= 0
                  for key in ("input_tokens", "output_tokens"))
          and type(value["cost_usd"]) in (int, float)
          and math.isfinite(value["cost_usd"]) and value["cost_usd"] == 0,
          "Invalid reporting usage accounting")
    return dict(value)


def _add(total, usage):
    for key in _ZERO:
        total[key] += usage[key]


def _message(error):
    text = str(error).encode("utf-8", "backslashreplace").decode("utf-8")[:240]
    return type(error).__name__ + ": " + text


def run_reporting_cell(packet, arm, *, cell_id, output: Path, journal: RunJournal,
                       client_factory, budget: Budget = Budget(), monotonic=time.monotonic):
    """Run one declared arm under its own complete per-cell budget.

    ``client_factory(stage, retain_callback)`` supplies a fresh one-use client.
    Expected transport/structural failures return explicit terminals; unexpected
    errors and interruptions propagate after best-effort final journal retention.
    Stage summaries contain only JSON-safe metadata and relative file/hash pins.
    """
    _need(type(arm) is str and arm in ARMS, "Unknown reporting arm")
    _need(type(cell_id) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", cell_id),
          "Invalid flat reporting cell ID")
    _need(isinstance(journal, RunJournal) and callable(client_factory) and callable(monotonic),
          "Trusted journal, client factory and clock are required")
    _need(isinstance(budget, Budget), "Invalid reporting budget")
    budget.validate()
    defaults = Budget()
    _need(all(getattr(budget, key) <= getattr(defaults, key) for key in (
        "max_calls", "max_input_tokens", "max_output_tokens", "max_cost_usd", "max_seconds")),
        "Reporting budget exceeds the frozen per-cell caps")
    output = Path(output).absolute()
    _need(output.parent.resolve() == journal.output and output.name == cell_id,
          "Cell output must be a fresh direct child of the run journal")
    started = monotonic()
    _need(type(started) in (int, float) and math.isfinite(started), "Invalid reporting clock")
    output.mkdir(exist_ok=False)
    measured, estimated, stages = dict(_ZERO), dict(_ZERO), []
    dispatches = 0
    raw_final, terminal, reason, primary = None, "unexecuted", None, None
    last_elapsed = 0.0

    def elapsed():
        nonlocal last_elapsed
        now = monotonic()
        _need(type(now) in (int, float) and math.isfinite(now)
              and now - started >= last_elapsed, "Invalid or reversing reporting clock")
        last_elapsed = now - started
        return last_elapsed

    def retain_file(record, key, path, raw):
        proof = _write_exclusive(path, raw)
        record["files"][key] = dict(path=path.relative_to(output).as_posix(), **proof)

    def model_stage(stage, prompt):
        nonlocal dispatches
        prepared = canonical(prepare_completion(prompt, 2048, 0))
        quote = dict(input_tokens=len(prompt.encode("utf-8")) + 32,
                     output_tokens=2048, cost_usd=0.0)
        used = {key: measured[key] + estimated[key] for key in _ZERO}
        remaining = budget.max_seconds - elapsed()
        affordable = (dispatches < budget.max_calls
            and used["input_tokens"] + quote["input_tokens"] <= budget.max_input_tokens
            and used["output_tokens"] + quote["output_tokens"] <= budget.max_output_tokens
            and used["cost_usd"] + quote["cost_usd"] <= budget.max_cost_usd
            and remaining > 0)
        if not affordable:
            return None
        folder = output / stage
        folder.mkdir(exist_ok=False)
        record = dict(stage=stage, attempt_id=f"{cell_id}:{stage}", files={},
                      reserved=quote, dispatched=False, terminal="reserved", reason=None,
                      measured_usage=None, estimated_usage=dict(_ZERO), accounting_basis=None)
        stages.append(record)
        journal.append("stage_reserved", cell_id=cell_id, stage=stage,
                       attempt_id=record["attempt_id"], retry_policy="none")
        holder = dict(attempt=False, result=None, accounted=False)

        def retain(event):
            nonlocal dispatches
            _need(isinstance(event, Mapping), "Malformed trusted transport event")
            if event.get("event") == "attempt":
                _need(not holder["attempt"] and holder["result"] is None,
                      "Duplicate reporting dispatch attempt")
                _need(event.get("dispatched") is False and event.get("raw_request") == prepared
                      and event.get("request_sha256") == hashlib.sha256(prepared).hexdigest()
                      and canonical(event.get("estimated_usage")) == canonical(quote),
                      "Reporting dispatch differs from its frozen prompt/reservation")
                retain_file(record, "raw_request", folder / "raw-request.bin", prepared)
                if elapsed() >= budget.max_seconds:
                    raise _BudgetExhausted("Per-cell deadline expired during request retention")
                journal.append("dispatch", cell_id=cell_id, stage=stage,
                    attempt_id=record["attempt_id"], reserved=quote,
                    request_sha256=event["request_sha256"],
                    request_file=record["files"]["raw_request"], retry_policy="none")
                holder["attempt"] = True
                if elapsed() >= budget.max_seconds:
                    raise _BudgetExhausted("Per-cell deadline expired before HTTP dispatch")
                return
            _need(event.get("event") == "terminal" and holder["result"] is None
                  and isinstance(event.get("result"), TransportResult),
                  "Duplicate or malformed reporting transport terminal")
            result = event["result"]
            holder["result"] = result
            _need(type(result.dispatched) is bool, "Invalid actual dispatch disposition")
            record.update(dispatched=result.dispatched, terminal=result.status, reason=result.error,
                          envelope_complete=result.envelope_complete)
            if result.dispatched:
                dispatches += 1
                if result.measured_usage is not None:
                    charge, basis = _usage(result.measured_usage), "adapter_reported"
                    record["measured_usage"] = charge
                    _add(measured, charge)
                else:
                    charge, basis = quote, "quoted_upper_bound_not_measured"
                    record["estimated_usage"] = quote
                    _add(estimated, charge)
            else:
                charge, basis = dict(_ZERO), "not_dispatched"
            record["accounting_basis"] = basis
            failure = None
            try:
                _need(not result.dispatched or holder["attempt"], "Dispatch lacks durable attempted request")
                _need(result.raw_request == prepared
                      and result.request_sha256 == hashlib.sha256(prepared).hexdigest()
                      and canonical(result.estimated_usage) == canonical(quote),
                      "Transport terminal request/reservation differs")
                _need(result.status in ("returned", "failed", "timeout", "interrupted"),
                      "Unknown reporting transport terminal")
                if "raw_request" not in record["files"]:
                    retain_file(record, "raw_request", folder / "raw-request.bin", result.raw_request)
                if result.response_sha256 is not None:
                    _need(type(result.raw_envelope) is bytes
                          and hashlib.sha256(result.raw_envelope).hexdigest() == result.response_sha256,
                          "Retained response digest differs")
                    retain_file(record, "raw_envelope", folder / "raw-envelope.bin", result.raw_envelope)
                if result.content is not None:
                    _need(type(result.content) is bytes
                          and hashlib.sha256(result.content).hexdigest() == result.content_sha256,
                          "Retained content digest differs")
                    retain_file(record, "content", folder / "content.bin", result.content)
            except BaseException as error:
                failure = error
            finally:
                try:
                    _need(not holder["accounted"], "Reporting attempt was already accounted")
                    holder["accounted"] = True
                    journal.append("attempt_accounted", cell_id=cell_id, stage=stage,
                        attempt_id=record["attempt_id"], dispatched=result.dispatched,
                        basis=basis, usage=charge, transport_terminal=result.status,
                        files=record["files"], retention_complete=failure is None)
                except BaseException as secondary:
                    if failure is None:
                        failure = secondary
                    else:
                        failure.add_note("Secondary attempt-accounting failure: " + type(secondary).__name__)
            if failure is not None:
                raise failure

        client = client_factory(stage, retain)
        timeout = min(300, budget.max_seconds - elapsed())
        if timeout <= 0:
            record.update(terminal="unexecuted", reason="Per-cell deadline expired during client preparation")
            journal.append("stage_blocked", cell_id=cell_id, stage=stage,
                           terminal="unexecuted", dispatched=False, reason=record["reason"])
            return None
        result = client.execute(prompt, maximum=2048, seed=0, timeout_seconds=timeout)
        _need(holder["result"] is result and holder["accounted"],
              "Transport return differs from its retained terminal")
        if result.measured_usage is not None and result.dispatched:
            _need(result.measured_usage["input_tokens"] <= quote["input_tokens"]
                  and result.measured_usage["output_tokens"] <= quote["output_tokens"]
                  or result.status != "returned", "Returned transport exceeded its reservation")
        return result

    try:
        journal.append("cell_reserved", cell_id=cell_id, arm=arm,
                       budget=budget, retry_policy="none")
        view = reporting_view(packet)
        elapsed()
        deterministic = arm in ARMS[:2]
        missing_preflight = arm == ARMS[3] and not view["task"]["records"]
        if deterministic or missing_preflight:
            raw_final = literal_report(packet, always_abstain=arm == "always_abstain")
            _write_exclusive(output / "final-response.bin", raw_final)
            terminal = "returned"
        else:
            stage_names = ("plain",) if arm == ARMS[2] else ("proposal", "audit")
            prior = None
            for stage in stage_names:
                prompt = render_reporting_prompt(packet, stage=stage, prior_output=prior,
                                                 max_prompt_bytes=14304)
                result = model_stage(stage, prompt)
                if result is None:
                    terminal = "failed" if dispatches else "unexecuted"
                    reason = "Per-cell call, token or wall-time reservation exhausted before dispatch"
                    break
                if result.status != "returned":
                    terminal, reason = result.status, result.error
                    break
                if elapsed() >= budget.max_seconds:
                    terminal, reason = "timeout", "Per-cell wall-time cap exceeded"
                    break
                _need(result.content is not None and result.envelope_complete,
                      "Returned transport has no complete retained content")
                adapted = adapt_output(result.content, wire_format="typed_facts_v1",
                    task_id=view["task"]["task_id"], task_sha256=view["task_sha256"])
                journal.append("report_structure_checked", cell_id=cell_id, stage=stage,
                    status=adapted["status"], semantic_reference_grading=False)
                if adapted["status"] != "scorable":
                    terminal, reason = "malformed", adapted["error"]
                    if stage != "proposal":
                        raw_final = result.content
                        _write_exclusive(output / "final-response.bin", raw_final)
                    break
                if stage == "proposal":
                    prior = result.content
                else:
                    raw_final = result.content
                    _write_exclusive(output / "final-response.bin", raw_final)
                    terminal = "returned"
        if elapsed() >= budget.max_seconds and terminal == "returned":
            terminal, reason = "timeout", "Per-cell wall-time cap exceeded"
    except BaseException as error:
        if isinstance(error, _BudgetExhausted):
            terminal = "failed" if dispatches else "unexecuted"
            reason = _message(error)
        else:
            terminal = "interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed"
            reason, primary = _message(error), error
    finally:
        for record in stages:
            if record["terminal"] == "reserved":
                record.update(terminal=terminal, reason=reason)
        try:
            elapsed()
        except BaseException as secondary:
            if primary is None:
                terminal = "interrupted" if isinstance(secondary, (KeyboardInterrupt, SystemExit)) else "failed"
                reason, primary = _message(secondary), secondary
            else:
                primary.add_note("Secondary cell clock failure: " + type(secondary).__name__)
        if last_elapsed >= budget.max_seconds and terminal == "returned":
            terminal, reason = "timeout", "Per-cell wall-time cap exceeded at terminal retention"
        result = freeze(dict(raw_final=raw_final, terminal=terminal, reason=reason,
            stage_records=stages, measured_usage=measured, estimated_usage=estimated,
            dispatches=dispatches, elapsed_seconds=last_elapsed))
        try:
            journal.append("cell_terminal", cell_id=cell_id, arm=arm, terminal=terminal,
                reason=reason, stage_records=stages, measured_usage=measured,
                estimated_usage=estimated, dispatches=dispatches,
                elapsed_seconds=last_elapsed, retry_policy="none",
                final_sha256=None if raw_final is None else hashlib.sha256(raw_final).hexdigest())
        except BaseException as secondary:
            if primary is None:
                primary = secondary
            else:
                primary.add_note("Secondary cell-terminal retention failure: " + type(secondary).__name__)
    if primary is not None:
        # The controller can retain known accounting even if the final journal
        # append failed. Byte payloads stay in this immutable in-memory result;
        # callers must store them separately from JSON metadata. Refusal by a
        # trusted exception object must never replace the primary failure.
        result = freeze(dict(result,
            terminal="interrupted" if isinstance(primary, (KeyboardInterrupt, SystemExit)) else "failed",
            reason=_message(primary)))
        try:
            primary.reporting_cell_result = result
        except BaseException:
            pass
        raise primary
    return result
