"""Additional v0.4.1 execution/prose checks over already verified v2 engine runs.

This is a deterministic consistency check, not source authenticity, therapeutic
validation or an operating-system boundary. The frozen engine stays unchanged.
"""
from types import SimpleNamespace
from tether_engine.artifacts import dossier
from tether_engine.chrono import Exclusion
from tether_engine.agents import Usage
from tether_engine.contracts import Case, Claim, Snapshot
from tether_engine.features import FeatureVector
from tether_engine.scorer import Prediction
from tether_engine.serde import ContractError, canonical, decode
from tether_engine.workflow import Budget, PlanStep, RunResult

HANDLED_ERRORS = {"BackendFailure", "ContractError", "TimeoutError", "ConnectionError",
                  "ValueError", "RuntimeError", "RecursionError"}
FATAL_ERRORS = {"OSError", "PermissionError", "FileNotFoundError", "KeyError", "TypeError",
                "AttributeError", "AssertionError", "MemoryError", "Exception"}


def need(condition, message):
    if not condition:
        raise ContractError("TETHER execution semantics: " + message)


def check_states(run, trace, configuration):
    states = {s["category"]: (s["initial_status"] if s["initial_status"] != "ready" else "not_run")
              for s in run["plan"]}
    initial = {s["category"]: s["initial_status"] for s in run["plan"]}
    active = None
    exhausted = False
    failures = []
    failed_categories = set()
    retrievals = {}
    attempted = set()
    completed_order = []
    attempts = {}
    plan_seen = finalized = False
    terminal_failure = False
    preamble = set()
    need(type(configuration["review_enabled"]) is bool, "invalid review configuration")

    def finish_attempt(next_category=None):
        if active is None:
            return
        need(active["accounted"] is not None and (active["reviewed"] or active["terminal"]),
             "accounted attempt lacks a review or terminal disposition")
        if active["reviewed"] and active["selected"] is None and configuration["review_enabled"]:
            need(next_category == active["category"]
                 or attempts[active["category"]] == run["budget"]["max_retries"] + 1,
                 "rejected review abandoned configured retries without a terminal reason")
        if active["selected"] is not None:
            selected, committed = active["selected"], active["committed"]
            need(committed == selected[:len(committed)], "claims differ from reviewed selection order")
            need(active["partial"] or committed == selected, "reviewed selection was not fully committed")

    def category(details):
        name = details["category"]
        need(name in states and initial[name] == "ready", "event for inactive specialist")
        need(name not in failed_categories, "event after terminal backend failure")
        return name

    for event in trace:
        kind, details = event["event"], event["details"]
        need(not finalized, "event follows finalization")
        need(not terminal_failure or kind == "finalize", "execution follows a terminal failure")
        if kind in ("run_reserved", "inputs_archived"):
            need(not plan_seen and kind not in preamble, "invalid workflow preamble order")
            preamble.add(kind)
            continue
        if kind == "plan":
            need(not plan_seen, "duplicate execution plan")
            plan_seen = True
            continue
        need(plan_seen, "execution precedes plan")
        if kind in ("bounded_retrieval", "backend_quote_failed", "budget_denied", "dispatch"):
            name = category(details)
            need(not exhausted and states[name] not in ("completed", "no_records_within_retrieval_budget"),
                 "preparation follows a terminal category or budget state")
        if kind == "bounded_retrieval":
            name = category(details)
            need(type(details["attempt"]) is int and details["attempt"] == attempts.get(name, 0) + 1,
                 "retrieval attempt sequence differs")
            finish_attempt(name)
            active = None
            ids = details["selected_ids"]
            need(type(ids) is list and all(type(x) is str for x in ids) and len(set(ids)) == len(ids),
                 "invalid retrieval ID inventory")
            retrievals[name] = {k: v for k, v in details.items() if k not in ("category", "attempt")}
            if not ids:
                states[name] = "no_records_within_retrieval_budget"
        elif kind in ("backend_quote_failed", "budget_denied"):
            name = category(details)
            finish_attempt(name)
            active = None
            states[name] = "failed" if kind == "backend_quote_failed" else "budget_exhausted"
            if kind == "backend_quote_failed":
                failed_categories.add(name)
            exhausted |= kind == "budget_denied"
        elif kind == "dispatch":
            name = category(details)
            finish_attempt(name)
            need(type(details["attempt"]) is int and details["attempt"] == attempts.get(name, 0) + 1,
                 "dispatch attempt sequence differs")
            attempts[name] = details["attempt"]
            need(not exhausted and states[name] not in ("completed", "no_records_within_retrieval_budget"),
                 "dispatch after terminal specialist/budget state")
            if name not in attempted:
                completed_order.append(name)
                attempted.add(name)
            need(completed_order[-1] == name, "specialist execution returned to a prior category")
            states[name] = "failed"
            active = dict(category=name, attempt_id=details["attempt_id"], accounted=None,
                          selected=None, reviewed=False, committed=[], partial=False, terminal=False)
        elif kind == "attempt_accounted":
            need(active is not None and details["attempt_id"] == active["attempt_id"]
                 and active["accounted"] is None, "accounting outside active attempt")
            active["accounted"] = details["usage"]
        elif kind in ("backend_failed", "backend_usage_contract_violated"):
            name = category(details)
            need(active is not None and active["category"] == name and active["accounted"] is not None
                 and not active["reviewed"], "failure outside accounted pre-review attempt")
            states[name] = "failed"
            active["terminal"] = True
            if kind == "backend_failed":
                failures.append(details["error_class"])
                failed_categories.add(name)
                terminal_failure = details["error_class"] in FATAL_ERRORS | {"KeyboardInterrupt"}
            else:
                exhausted = True
        elif kind == "wall_time_budget_exceeded":
            name = category(details)
            need(active is not None and active["category"] == name and active["accounted"] is not None,
                 "wall-time event outside accounted attempt")
            exhausted = True
            active["terminal"] = True
            if details.get("stage") == "claim_commit":
                need(active["selected"] is not None, "commit deadline without accepted review")
                active["partial"] = True
                states[name] = "budget_exhausted"
            else:
                need(not active["reviewed"], "pre-review deadline follows review")
                states[name] = "failed"
        elif kind == "review":
            name = category(details)
            need(active is not None and active["category"] == name and active["accounted"] is not None
                 and not active["reviewed"] and not exhausted, "review outside accounted attempt")
            need(canonical(details["usage"]) == canonical(active["accounted"]), "review/accounted usage mismatch")
            ids, problems = details["selected"], details["problems"]
            need(type(ids) is list and all(type(x) is str for x in ids)
                 and type(problems) is list and all(type(x) is str for x in problems), "invalid review payload")
            active["reviewed"] = True
            if problems and not configuration["review_enabled"]:
                failed_categories.add(name)
            if not problems:
                need(len(ids) == len(set(ids)), "accepted selection contains duplicate IDs")
                if name in retrievals:
                    need(set(ids).issubset(retrievals[name]["selected_ids"]),
                         "accepted selection is outside the bounded request")
                active["selected"] = ids
                states[name] = "completed"
        elif kind == "claim_committed":
            need(active is not None and active["selected"] is not None and not active["partial"]
                 and not exhausted and active["category"] not in failed_categories,
                 "claim without an accepted active review")
            claim = details["claim"]
            need(claim["specialist"] == active["category"], "claim belongs to another specialist")
            active["committed"].append(claim["evidence"]["observation"]["observation_id"])
            need(active["committed"] == active["selected"][:len(active["committed"])],
                 "claim was not selected by its review")
        elif kind == "finalize":
            finish_attempt()
            finalized = True
        else:
            raise ContractError("TETHER execution semantics: unsupported workflow event " + kind)
    ready_order = [s["category"] for s in run["plan"] if s["initial_status"] == "ready"]
    need(completed_order == [c for c in ready_order if c in attempted], "specialist dispatch order differs from plan")
    for name in states:
        if states[name] == "not_run" and exhausted:
            states[name] = "not_run_budget_exhausted"
        need(run["coverage"][name]["status"] == states[name], "coverage status differs from trace: " + name)
        if name in retrievals:
            need(canonical(run["coverage"][name].get("retrieval")) == canonical(retrievals[name]),
                 "coverage retrieval differs from trace")
        else:
            need("retrieval" not in run["coverage"][name], "coverage invents an unrecorded retrieval")
    status = run["status"]
    need(status in ("completed", "partial", "budget_exhausted", "failed", "interrupted"), "unknown terminal status")
    # The engine records names, not Python exception inheritance. Constrain known
    # standard names; unknown custom subclasses cannot be classified from this
    # trace alone and remain a declared trust limitation.
    handled, fatal = HANDLED_ERRORS, FATAL_ERRORS
    if "KeyboardInterrupt" in failures:
        need(status == "interrupted", "interrupt trace/terminal status mismatch")
    elif any(name in fatal for name in failures):
        need(status == "failed", "fatal exception trace/terminal status mismatch")
    if status == "interrupted":
        need(any(name not in handled | fatal for name in failures), "interrupted status lacks a possible interruption")
    if status == "failed":
        need(any(name not in handled | {"KeyboardInterrupt"} for name in failures), "failed status lacks a possible fatal exception")
    if exhausted:
        need(status == "budget_exhausted", "exhaustion trace/terminal status mismatch")
    else:
        need(status != "budget_exhausted", "budget exhaustion lacks a trace event")
    if status == "completed":
        need(all(s in ("completed", "disabled", "no_observed_evidence", "no_records_within_retrieval_budget")
                 for s in states.values()), "completed run has incomplete specialists")
    elif status == "partial":
        need("failed" in states.values() and "not_run" not in states.values(), "partial run lacks failed completed traversal")
    elif status in ("failed", "interrupted"):
        need(failures and "failed" in states.values(), "failed/interrupted run lacks a backend failure")
    return states


def check_engine_semantics(root, load_json, read_bytes, journal_events, ledger_limit):
    run, inputs = load_json(root / "run.json"), load_json(root / "inputs.json")
    trace = journal_events(read_bytes(root / "trace.jsonl"))
    check_states(run, trace, inputs["configuration"])
    from tether_engine.serde import parse_json
    ledger = parse_json(read_bytes(root / "ledger.json", max_bytes=ledger_limit))
    fields = {k: run[k] for k in ("snapshot_id", "profile", "backend_id", "status", "budget", "calls",
              "usage", "plan", "coverage", "measured_usage", "estimated_usage")}
    fields.update(case=inputs["case"], claims=ledger["claims"], features=load_json(root / "features.json"),
                  prediction=load_json(root / "prediction.json"), trace=trace, configuration=inputs["configuration"])
    # RunResult contains deliberately unparameterized immutable Mapping fields;
    # its original wire decoder does not support decoding the complete class.
    # Decode typed members explicitly; coverage/configuration/trace were checked
    # by the engine and the state replay above, then Frozen copies their data.
    for key, kind in (("case", Case), ("claims", tuple[Claim, ...]), ("features", FeatureVector),
                      ("prediction", Prediction), ("budget", Budget), ("plan", tuple[PlanStep, ...]),
                      ("usage", Usage), ("measured_usage", Usage), ("estimated_usage", Usage)):
        fields[key] = decode(kind, fields[key])
    result = RunResult(**fields)
    store = SimpleNamespace(snapshot=decode(Snapshot, inputs["snapshot"]),
                            exclusions=decode(tuple[Exclusion, ...], run["exclusions"]))
    expected = dossier(result, store).encode("utf-8")
    actual = read_bytes(root / "dossier.md", max_bytes=ledger_limit)
    need(actual in (expected, expected.replace(b"\n", b"\r\n")), "dossier prose differs from deterministic rendering")
    return {"method": "tether.execution_semantics.v1", "coverage_state_machine": "verified",
            "review_to_claims": "verified", "dossier_reconstruction": "verified"}
