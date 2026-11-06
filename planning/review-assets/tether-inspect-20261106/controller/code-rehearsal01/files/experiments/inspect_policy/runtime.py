"""Scripted local-provider witnesses through Inspect's actual runner lifecycle.

No remote model or scientific inference occurs. The extension, not a best-effort
hook, owns source admission, immutable claim capabilities and conservative usage.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
import math
from pathlib import Path
import time

import anyio
from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.hooks import Hooks, hooks
from inspect_ai.model import (ChatMessageUser, GenerateConfig, Model, ModelAPI,
                              ModelCall, ModelOutput, ModelUsage, modelapi)
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver

from .accounting import Accounting, BudgetDenied, usage
from .archive import checked_rows
from .evidence import EvidenceContext
from .records import (CaseRecord, canonical, checked_json, digest, freeze,
                      inspect_record, parse, publish, safe_path, thaw)


ACTIVE = ContextVar("inspect_policy_provider_authority", default=None)
CONFIG = {"temperature": 0.0, "max_retries": 0, "cache": False,
          "max_connections": 1, "adaptive_connections": False}


def _hook_identity(active, data):
    return {"control_id": active["row"]["id"], "attempt": active["ticket"]["attempt"],
            "epoch": active["epoch"], "native_sample_uuid": active["sample_uuid"],
            "run_id": data.run_id, "eval_id": data.eval_id, "task_name": data.task_name}


@hooks("inspect_policy_telemetry", "Non-authoritative scripted witness telemetry")
class WitnessHooks(Hooks):
    async def on_before_model_generate(self, data):
        active = ACTIVE.get()
        if active is None:
            return
        if active["row"]["hook_skip"]:
            return
        active["record"].append("inspect_before_model", {"model_name": data.model_name,
                                                       "identity": _hook_identity(active, data)})
        active["hook_before"] = True
        if active["row"]["hook_fault"]:
            active["telemetry_faults"].append("declared_optional_hook_exception_after_durable_before_event")
            raise RuntimeError("Declared fictional telemetry hook failure")
        if active["row"]["hook_mutate_request"]:
            data.input[0].content = data.input[0].text + " altered by fictional hook"

    async def on_model_usage(self, data):
        active = ACTIVE.get()
        if active is not None:
            active["record"].append("inspect_model_usage", {
                "usage": data.usage.model_dump(mode="json"), "retries": data.retries,
                "identity": _hook_identity(active, data)})
            active["hook_usage"] = True


@modelapi(name="inspect_policy_fixture")
class ScriptedProvider(ModelAPI):
    """Only the active reserved request may execute; no keys, sockets or retries."""

    async def count_tokens(self, input, config=None):
        # A documented fixture counting rule, not a real tokenizer benchmark.
        return sum(len(message.text) for message in input) if isinstance(input, list) else len(input)

    async def generate(self, input, tools, tool_choice, config):
        active = ACTIVE.get()
        if active is None:
            raise RuntimeError("Unreserved scripted provider call")
        active["entries"] += 1
        record, ticket = active["record"], active["ticket"]
        record.append("provider_entered", {"attempt": ticket["attempt"], "entry": active["entries"]})
        if active["entries"] != 1 or active["account"].pending is not ticket:
            raise RuntimeError("Provider call replay or missing live reservation")
        prompt = canonical(ticket["request"]).decode("utf-8")
        expected_config = GenerateConfig(**CONFIG, max_tokens=ticket["quote"]["output_tokens"]).model_dump(mode="json", exclude_none=True)
        if (len(input) != 1 or input[0].role != "user" or input[0].text != prompt or tools or
                canonical(config.model_dump(mode="json", exclude_none=True)) != canonical(expected_config)):
            raise ValueError("Native provider request/configuration differs from reserved payload")
        payload = {"messages": [{"role": item.role, "content": item.text} for item in input],
                   "tools": [], "configuration": config.model_dump(mode="json", exclude_none=True)}
        record.append("provider_dispatched", {"attempt": ticket["attempt"],
            "request_sha256": ticket["request_sha256"], "payload": payload, "payload_sha256": digest(payload)})
        active["dispatched"] += 1
        script = active["step"]["script"]
        if script["behavior"] == "error":
            raise RuntimeError("Declared fictional provider failure")
        if script["behavior"] == "interrupt":
            raise asyncio.CancelledError("Declared fictional in-flight interruption")
        if script["behavior"] == "sleep":
            await anyio.sleep(script["delay_seconds"])
        output = ModelOutput.from_content(model=self.model_name, content=script["content"])
        reported = thaw(script["usage"])
        output.usage = ModelUsage(input_tokens=reported["input_tokens"], output_tokens=reported["output_tokens"],
                                 total_tokens=reported["input_tokens"] + reported["output_tokens"], total_cost=reported["cost_usd"])
        return output, ModelCall.create(payload, {"content": script["content"], "usage": reported})


def checked_runtime_rows(rows):
    result, names = [], set()
    fields = {"id", "input", "budget", "steps", "call_seconds", "hook_fault", "hook_skip", "hook_mutate_request", "mutate_task_state", "commit_clock"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("Runtime witness fields differ")
        source = checked_rows([row["input"]])[0]
        if row["id"] != source["control_id"] or row["id"] in names:
            raise ValueError("Runtime case identity differs or repeats")
        names.add(row["id"])
        if type(row["call_seconds"]) not in (int, float) or not math.isfinite(row["call_seconds"]) or not 0 < row["call_seconds"] <= 120:
            raise ValueError("Bounded positive call time required")
        if any(type(row[name]) is not bool for name in ("hook_fault", "hook_skip", "hook_mutate_request", "mutate_task_state")):
            raise ValueError("Runtime fault switches must be explicit booleans")
        ticks = row["commit_clock"]
        if ticks is not None and (type(ticks) is not list or not ticks or any(type(x) not in (int, float) or not math.isfinite(x) for x in ticks) or ticks != sorted(ticks)):
            raise ValueError("Injected clock must be a nonempty monotonic finite sequence")
        if type(row["steps"]) is not list or not row["steps"]:
            raise ValueError("A nonempty explicit operation schedule is required")
        for step in row["steps"]:
            if set(step) != {"category", "quote", "script"} or type(step["category"]) is not str:
                raise ValueError("Step fields differ")
            usage(step["quote"])
            if step["quote"]["output_tokens"] < 1:
                raise ValueError("Positive native response token cap required")
            script = step["script"]
            if set(script) != {"behavior", "content", "usage", "delay_seconds"} or script["behavior"] not in ("success", "error", "interrupt", "sleep") or type(script["content"]) is not str:
                raise ValueError("Scripted provider fields differ")
            usage(script["usage"])
            if type(script["delay_seconds"]) not in (int, float) or not math.isfinite(script["delay_seconds"]) or not 0 <= script["delay_seconds"] <= 10:
                raise ValueError("Scripted delay outside witness bounds")
        result.append(freeze(row))
    if not result:
        raise ValueError("A nonempty runtime schedule is required")
    return tuple(result)


@solver
def runtime_solver(rows: list[dict], output_root: str) -> Solver:
    schedule = {row["id"]: row for row in checked_runtime_rows(rows)}

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        row = schedule[str(state.sample_id)]
        if state.input_text != canonical(row["input"]).decode("utf-8"):
            raise ValueError("Runtime sample input differs from captured source request")
        root = safe_path(output_root)
        source_root = safe_path(row["input"]["bundle_root"])
        if root.is_relative_to(source_root) or source_root.is_relative_to(root):
            raise ValueError("Runtime output and source trees must not overlap")
        record = CaseRecord(root / row["id"], row)
        account = Accounting(record, thaw(row["budget"]))
        context = None
        status, error, last_content = "completed", None, None
        provider_entries = provider_dispatches = 0
        telemetry_faults = []
        commits = []
        fatal = None
        try:
            context = EvidenceContext(row["input"])
            context_proof = publish(record.path / "context.json", context.report)
            record.append("source_admitted", {"context": context_proof, "context_sha256": digest(context.report)})
            # Mutable Inspect state receives a copied telemetry view. The actual
            # admission capability remains private and recursively immutable.
            state.metadata["evidence_view"] = thaw(context.records)
            if row["mutate_task_state"] and state.metadata["evidence_view"]:
                first = next(iter(state.metadata["evidence_view"].values()))
                first["observation"]["statement"] = "Fictional attempted nested state mutation"
            for index, step in enumerate(row["steps"]):
                request = {"case_id": context.case["case_id"], "category": step["category"],
                           "context_sha256": digest(context.report),
                           "offered_observation_ids": context.offered(step["category"]), "step": index}
                ticket = account.reserve(request, thaw(step["quote"]))
                active = {"record": record, "account": account, "ticket": ticket,
                          "row": row, "step": step, "entries": 0, "dispatched": 0,
                          "epoch": state.epoch, "sample_uuid": state.uuid,
                          "hook_before": False, "hook_usage": False, "telemetry_faults": []}
                state.messages = [ChatMessageUser(content=canonical(request).decode("utf-8"))]
                token = ACTIVE.set(active)
                try:
                    with anyio.fail_after(min(row["call_seconds"], max(0.000001,
                            row["budget"]["max_seconds"] - (time.monotonic() - account.started)))):
                        state = await generate(state, tool_calls="none", max_tokens=ticket["quote"]["output_tokens"], **CONFIG)
                    output = state.output
                    last_content = output.completion
                    response = output.model_dump(mode="json")
                    response_proof = publish(record.path / f"response-{index:03d}.json", response)
                    record.append("native_response", {"attempt": ticket["attempt"], "response": response_proof})
                    if not active["hook_before"] or not active["hook_usage"]:
                        raise ValueError("Required Inspect telemetry callback is missing")
                    selection = parse(last_content.encode("utf-8"))
                    if type(selection) is not dict or set(selection) != {"observation_ids"}:
                        raise ValueError("Scripted selection response fields differ")
                    selected = context.review(selection["observation_ids"], step["category"])
                    reported = output.usage
                    if reported is None or reported.total_tokens != reported.input_tokens + reported.output_tokens:
                        raise ValueError("Native reported usage is incomplete")
                    measured = usage({"input_tokens": reported.input_tokens, "output_tokens": reported.output_tokens,
                                      "cost_usd": reported.total_cost})
                    accounted = account.settle(measured=measured, outcome="completed", response_sha256=response_proof["sha256"])
                    if accounted["quote_breach"]:
                        status = "budget_exhausted"
                        break
                    if row["commit_clock"] is None:
                        clock, deadline = time.monotonic, account.started + row["budget"]["max_seconds"]
                    else:
                        ticks = iter(row["commit_clock"])
                        last = [row["commit_clock"][-1]]
                        def clock():
                            last[0] = next(ticks, last[0])
                            return last[0]
                        deadline = 1.0
                    committed = context.commit(list(selected), step["category"], record, clock=clock, deadline=deadline)
                    commits.append(committed)
                    if committed["status"] != "completed":
                        status, account.stopped = "budget_exhausted", True
                        break
                finally:
                    provider_entries += active["entries"]
                    provider_dispatches += active["dispatched"]
                    telemetry_faults.extend(active["telemetry_faults"])
                    ACTIVE.reset(token)
        except BudgetDenied as exc:
            status, error = "budget_exhausted", {"type": type(exc).__name__, "message": str(exc)}
        except BaseException as exc:
            account.stopped = True
            status = "interrupted" if not isinstance(exc, Exception) else "error"
            if isinstance(exc, TimeoutError):
                status = "timeout"
            error = {"type": type(exc).__name__, "message": str(exc)}
            fatal = exc
        finally:
            if account.pending is not None:
                account.settle(outcome=status)
            result = {"schema_version": 1, "control_id": row["id"], "status": status,
                "error": error, "accounting": account.summary(), "provider_entries": provider_entries,
                "provider_dispatches": provider_dispatches, "commits": commits,
                "context_sha256": digest(context.report) if context else None,
                "last_response_content": last_content,
                "telemetry_faults": telemetry_faults,
                "required_hook_policy": "before-and-usage events required for completed response; hooks never authorize a call",
                "commit_clock_kind": "injected_contract_clock" if row["commit_clock"] is not None else "measured_monotonic",
                "scope": "scripted_provider_and_minimal_claim_commit_not_full_therapeutic_scheduler"}
            finished = record.finish(result)
            state.metadata["policy_record"] = {"path": str(record.path), "receipt": finished["receipt"]}
        if fatal is not None:
            if status == "timeout":
                # Inspect 0.3.287 catches a bare TimeoutError at the top of a
                # sample and proceeds to scoring. Surface this extension-owned
                # deadline as an operational error, retaining its exact cause.
                raise RuntimeError("Reserved scripted provider call exceeded its deadline") from fatal
            raise fatal
        state.completed = True
        return state

    return solve


@scorer(metrics=[accuracy()])
def runtime_scorer(oracle_path: str, oracle_proof: dict):
    async def score(state: TaskState, target: Target):
        retained = state.metadata["policy_record"]
        checked = inspect_record(retained["path"], receipt_sha256=retained["receipt"]["sha256"])
        result = checked["result"]
        if checked["request"].get("id") != str(state.sample_id) or result.get("control_id") != str(state.sample_id):
            raise ValueError("Sample and retained runtime identities differ")
        if result["last_response_content"] is not None and state.output.completion != result["last_response_content"]:
            raise ValueError("Native output/retained response differs")
        oracle = checked_json(oracle_path, oracle_proof)
        expected = [item for item in oracle["cases"] if item["control_id"] == str(state.sample_id)]
        if len(expected) != 1:
            raise ValueError("Runtime oracle case missing or duplicated")
        mismatches = []
        for field, value in expected[0]["fields"].items():
            actual = result
            try:
                for part in field.split("."):
                    actual = actual[int(part)] if isinstance(actual, (tuple, list)) else actual[part]
            except (KeyError, IndexError, ValueError, TypeError):
                actual = {"missing_field": True}
            if canonical(actual) != canonical(value):
                mismatches.append(field)
        return Score(value="I" if mismatches else "C", answer=result["status"],
                     metadata={"mismatches": mismatches, "scope": "scripted_runtime_obligations"})
    return score


def build_runtime_task(rows, output_root, oracle_path, oracle_proof):
    rows = [thaw(row) for row in checked_runtime_rows(rows)]
    root = safe_path(output_root)
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("Caller must reserve an empty runtime output root")
    config = GenerateConfig(**CONFIG)
    model = Model(ScriptedProvider(model_name="scripted-local-v1", config=config), config)
    return Task(dataset=[Sample(id=row["id"], input=canonical(row["input"]).decode("utf-8"), target="") for row in rows],
                solver=runtime_solver(rows, str(root)), scorer=runtime_scorer(str(oracle_path), dict(oracle_proof)),
                model=model, config=config, fail_on_error=False, score_on_error=False, epochs=1,
                name="tether_equivalent_policy_runtime", version=1,
                metadata={"scheduled": len(rows), "provider_cost_usd": 0,
                          "scope": "scripted_local_provider_not_scientific_inference"})
