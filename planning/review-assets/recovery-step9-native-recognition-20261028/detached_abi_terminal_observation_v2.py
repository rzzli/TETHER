"""Bounded pre-cleanup observations; no construction, dispatch or cleanup authority."""

import math
import time


MAX_CAPTURE_POLLS = 64
CAPTURE_DRAIN_SECONDS = 0.25


def observe_terminal(owner, report, captures, streams, *, sdk, event, work_deadline,
                     drain_seconds=CAPTURE_DRAIN_SECONDS, now=time.monotonic,
                     sleep=time.sleep):
    """Observe known owned handles, retaining each error without replacing primary.

    The caller must always run its existing owned cleanup afterward. This helper
    never creates, opens, terminates or closes a process/Job/handle. A capture
    drain is at most250ms/64 polls inside the unchanged child work deadline.
    """
    if type(work_deadline) not in (int, float) or not math.isfinite(work_deadline):
        raise ValueError("Finite terminal work deadline required")
    if not (0 < drain_seconds <= CAPTURE_DRAIN_SECONDS):
        raise ValueError("Terminal capture drain must remain within250ms")
    state = dict(started_at=now(), work_deadline=work_deadline,
                 drain_seconds=drain_seconds, maximum_capture_polls=MAX_CAPTURE_POLLS,
                 capture_polls_reserved=0, interrupted=False, complete=False,
                 physical_pipe_EOF_does_not_establish_child_exit=True,
                 observations={}, errors=[])
    report["terminal_observation"] = state
    report["terminal_observation_errors"] = state["errors"]
    creation = dict(getattr(owner, "creation", {})) if owner is not None else {}
    process = getattr(getattr(owner, "pi", None), "hProcess", None)
    pid = getattr(getattr(owner, "pi", None), "dwProcessId", 0)
    known_exit = bool(process and creation.get("return_observed") is True
                      and creation.get("returned_success") is True
                      and report.get("call_return_observed") is True
                      and type(report.get("returncode")) is int)
    state.update(creation=creation, owned_process_handle_known=bool(process),
                 exit_observed=known_exit,
                 scope="after_observed_owned_exit_before_cleanup" if known_exit else
                       "pre_cleanup_creation_or_exit_unconfirmed")

    def error(label, exc):
        row = dict(phase=label, error_class=type(exc).__name__, error=str(exc)[:512])
        state["errors"].append(row)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            state["interrupted"] = True
        return row

    def check(deadline):
        if state["interrupted"]:
            raise RuntimeError("Terminal observation stopped after interruption")
        if now() >= deadline:
            raise TimeoutError("Terminal observation work cutoff reached; cleanup remains required")

    def invoke(row, label, callback, deadline, summarize=lambda value: value):
        row.update(status="not_attempted", attempt_reserved=False,
                   call_attempted=False, return_observed=False)
        try:
            check(deadline)
            row.update(status="attempt_reserved", attempt_reserved=True, started_at=now())
            event("detached_ABI_terminal_call_reserved", observation=label)
            check(deadline)
            row["call_attempted"] = True
            value = callback()
            row.update(return_observed=True, status="returned", returned_at=now(), value=summarize(value))
            check(deadline)
            return True, value
        except BaseException as exc:
            row.update(status="failed", error=error(label, exc))
            return False, None

    # Each stream has an independent outcome. An earlier cap/error cannot hide
    # the other pipe's available bytes or its EOF status.
    drain_end = min(work_deadline, now() + drain_seconds)
    drains = {name: dict(status="not_attempted", eof=bool(captures[name].get("eof")),
                        polls_reserved=0, calls=[]) for name in ("stdout", "stderr")}
    state["observations"]["capture_drain"] = drains
    pending = []
    for name, row in drains.items():
        if row["eof"]:
            row["status"] = "already_observed_EOF"
        elif captures[name].get("truncated"):
            row.update(status="not_attempted_cap_already_exceeded", reason="Unknown further bytes")
        elif owner is None or not owner.handles.get(name + "_read") or name not in streams:
            row.update(status="not_attempted", reason="Owned pipe or sink unavailable")
        else:
            pending.append(name)
    while pending and state["capture_polls_reserved"] < MAX_CAPTURE_POLLS:
        if state["interrupted"] or now() >= drain_end:
            break
        for name in tuple(pending):
            if state["capture_polls_reserved"] >= MAX_CAPTURE_POLLS:
                break
            row = drains[name]
            row["polls_reserved"] += 1
            state["capture_polls_reserved"] += 1
            call = dict(poll=state["capture_polls_reserved"])
            row["calls"].append(call)
            ok, available = invoke(call, "capture_available_" + name,
                                   lambda name=name: owner.api.available(owner.handles[name + "_read"]), drain_end)
            if not ok:
                row["status"] = "failed"
                pending.remove(name)
                continue
            if available is None:
                captures[name]["eof"] = row["eof"] = True
                row["status"] = "observed_pipe_EOF" if known_exit else "observed_pipe_EOF_unconfirmed_child_state"
                pending.remove(name)
            elif type(available) is not int or available < 0:
                row.update(status="failed", error=error("capture_available_" + name,
                           RuntimeError("Invalid available-byte result")))
                pending.remove(name)
            elif available:
                read_call = {}
                call["read"] = read_call
                ok, block = invoke(read_call, "capture_read_" + name,
                                   lambda name=name, available=available:
                                   owner.api.read(owner.handles[name + "_read"], min(4096, available)),
                                   drain_end, summarize=lambda value: dict(bytes=len(value)))
                if ok:
                    try:
                        if not block:
                            raise RuntimeError("Pipe advertised bytes but returned none")
                        sdk.consume_capture(captures[name], block, streams[name], cap=65536)
                    except BaseException as exc:
                        ok = False
                        read_call["consume_error"] = error("capture_consume_" + name, exc)
                if not ok:
                    row["status"] = "failed"
                    pending.remove(name)
        if pending and not state["interrupted"] and now() < drain_end:
            try:
                sleep(min(0.005, max(0, drain_end - now())))
            except BaseException as exc:
                error("capture_drain_wait", exc)
                break
    for name in pending:
        drains[name].update(status="incomplete", reason="Finite drain cutoff or poll cap")

    snapshot = dict(status="not_attempted", raw_publication="not_attempted",
                    predicate="not_evaluated", scope=state["scope"])
    state["observations"]["job_snapshot"] = snapshot
    job = getattr(owner, "job", None)
    if not job:
        snapshot["reason"] = "No known owned private Job handle"
    else:
        try:
            check(work_deadline)
            if owner.snapshot_count >= sdk.LIMITS["maximum_job_snapshots"]:
                raise RuntimeError("Job snapshot budget exhausted before terminal query")
            # Conservative reservation before dispatch, including unknown returns.
            owner.snapshot_count += 1
            snapshot["ordinal"] = owner.snapshot_count
            ok, raw = invoke(snapshot, "terminal_job_snapshot",
                             lambda: owner.api.job_snapshot(job), work_deadline)
            if ok:
                snapshot["raw"] = raw
                try:
                    event("abi_job_snapshot_observed", stage="after_wait" if known_exit else
                          "pre_cleanup_creation_or_exit_unconfirmed",
                          ordinal=snapshot["ordinal"], snapshot=raw)
                    snapshot["raw_publication"] = "returned"
                except BaseException as exc:
                    snapshot.update(raw_publication="failed", publication_error=error("terminal_job_raw_publication", exc))
                if snapshot["raw_publication"] == "returned" and known_exit:
                    try:
                        check(work_deadline)
                        problem = sdk.job_snapshot_problem(raw, "finished", int(pid))
                        snapshot.update(predicate="passed" if problem is None else "failed", problem=problem)
                        if problem is not None:
                            error("terminal_job_predicate", RuntimeError(str(problem)))
                    except BaseException as exc:
                        snapshot.update(predicate="failed", predicate_error=error("terminal_job_predicate", exc))
                elif not known_exit:
                    snapshot["predicate"] = "not_applicable_unconfirmed_exit"
        except BaseException as exc:
            snapshot.update(status="failed", error=error("terminal_job_admission", exc))

    limits = dict(status="not_attempted")
    state["observations"]["memory_limits_and_peaks"] = limits
    if job:
        invoke(limits, "terminal_memory_limits_and_peaks", lambda: owner.api.verify_limits(job), work_deadline)
    else:
        limits["reason"] = "No known owned private Job handle"
    state["ended_at"] = now()
    state["complete"] = bool(known_exit and all(captures[name].get("eof") is True
                                               and not captures[name].get("truncated") for name in drains)
                             and snapshot.get("raw_publication") == "returned"
                             and snapshot.get("predicate") == "passed"
                             and limits.get("status") == "returned" and not state["errors"])
    return state
