"""Owned direct-child native runtime witnesses.

Owned finite-child interruption and actual simultaneous output reservation.
This uses the native Inspect witness worker, not a direct stand-in provider.
It makes no claim about terminating arbitrary descendant process trees.
"""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import time

from .records import inspect_record, parse, proof, publish, read_bytes, thaw


WORKER = Path(__file__).with_name("witness_worker.py")


def _launch(recipe, parent, name, gate=None):
    parent = Path(parent)
    work = parent / name
    prefix = parent / (name + "-import-cache")
    prefix.mkdir()
    pin = publish(parent / (name + "-recipe.json"), recipe)
    command = [sys.executable, "-I", "-B", "-X", "pycache_prefix=" + str(prefix),
               str(WORKER), "--recipe", str(parent / (name + "-recipe.json")),
               "--recipe-sha256", pin["sha256"], "--work", str(work)]
    if gate is not None:
        command.extend(["--start-gate", str(gate)])
    output = (parent / (name + ".stdout")).open("xb")
    error = (parent / (name + ".stderr")).open("xb")
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith(("INSPECT_", "PYTHONPATH", "PYTHONHOME", "PYTHONPYCACHEPREFIX")):
            environment.pop(key)
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    try:
        process = subprocess.Popen(command, stdout=output, stderr=error,
            env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    finally:
        output.close()
        error.close()
    return process, work, {"argv": command, "recipe": pin, "pid": process.pid,
                           "scope": "owned_direct_child_no_descendant_tree_claim"}


def _cleanup(process):
    if process.poll() is None:
        process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def _wait(predicate, processes, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("Owned child exited before declared witness point")
        time.sleep(0.025)
    raise TimeoutError("Bounded witness wait expired")


def interruption(output, rows, oracle_path, oracle_proof):
    """Stop after actual provider entry; a second scheduled case stays unstarted."""
    output = Path(output).absolute()
    output.mkdir(parents=False, exist_ok=False)
    if len(rows) != 2 or rows[0]["steps"][0]["script"]["behavior"] != "sleep":
        raise ValueError("Interruption needs slow first and unstarted second case")
    cases = output / "cases"
    cases.mkdir()
    recipe = {"rows": rows, "output_root": str(cases), "oracle_path": str(oracle_path), "oracle_proof": oracle_proof}
    process, work, launch = _launch(recipe, output, "worker")
    started = time.perf_counter()
    captured = None
    try:
        def dispatched():
            nonlocal captured
            path = cases / rows[0]["id"]
            if not (path / "journal.jsonl").exists():
                return False
            try:
                captured = inspect_record(path, allow_partial=True)
            except (OSError, ValueError):
                return False
            return any(event["event"] == "provider_dispatched" for event in captured["events"])
        _wait(dispatched, [process])
        # Termination targets only the exact Popen child owned by this invocation.
        process.terminate()
        returncode = process.wait(timeout=5)
        partial = inspect_record(cases / rows[0]["id"], allow_partial=True)
        events = partial["events"]
        reservations = [event for event in events if event["event"] == "attempt_reserved"]
        accounted = [event for event in events if event["event"] == "attempt_accounted"]
        dispatches = [event for event in events if event["event"] == "provider_dispatched"]
        if len(reservations) != 1 or accounted or len(dispatches) != 1 or partial["status"] != "partial":
            raise ValueError("Actual interrupted prefix differs")
        if (cases / rows[1]["id"]).exists() or (work / "RESULT.json").exists():
            raise ValueError("Interrupted schedule incorrectly finalized or continued")
        journal_pin = proof(cases / rows[0]["id"] / "journal.jsonl")
        # Repeated inspection is read-only and never authorizes dispatch.
        replay = inspect_record(cases / rows[0]["id"], allow_partial=True)
        if replay["automatic_redispatch"] or proof(cases / rows[0]["id"] / "journal.jsonl") != journal_pin:
            raise ValueError("Inspection mutated or resumed the prefix")
        result = {"status": "PASS", "witness": "IX06", "launch": launch,
            "returncode": returncode, "process_reaped": process.poll() is not None,
            "provider_dispatches": 1, "automatic_retry": False,
            "dispositions": [{"id": rows[0]["id"], "status": "interrupted", "unresolved_calls": 1},
                             {"id": rows[1]["id"], "status": "unexecuted", "unresolved_calls": 0}],
            "outstanding_quote": thaw(reservations[0]["details"]["quote"]),
            "measured_usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
            "journal": journal_pin, "wall_seconds": time.perf_counter() - started,
            "scope": "owned child after durable reservation; no power-loss or descendant-tree proof"}
        publish(output / "RESULT.json", result)
        return result
    except BaseException as exc:
        publish(output / "FAILURE.json", {"type": type(exc).__name__, "message": str(exc), "automatic_retry": False})
        raise
    finally:
        _cleanup(process)


def concurrent_reservation(output, row, oracle_path, oracle_proof):
    """Two real native workers wait at one gate; only one may dispatch."""
    output = Path(output).absolute()
    output.mkdir(parents=False, exist_ok=False)
    cases = output / "cases"
    cases.mkdir()
    gate = output / "START"
    recipe = {"rows": [row], "output_root": str(cases), "oracle_path": str(oracle_path), "oracle_proof": oracle_proof}
    children = []
    started = time.perf_counter()
    try:
        for name in ("first", "second"):
            children.append(_launch(recipe, output, name, gate))
        _wait(lambda: all((work / "READY.json").is_file() for _, work, _ in children), [child[0] for child in children])
        gate.write_bytes(b"release both owned native workers\n")
        returncodes = [process.wait(timeout=45) for process, _, _ in children]
        if returncodes != [0, 0]:
            raise ValueError("Concurrent workers did not retain both native logs")
        reports = [parse(read_bytes(work / "RESULT.json")) for _, work, _ in children]
        sample_errors = [report["samples"][0]["native_error"] for report in reports]
        if sorted(sample_errors) != [False, True]:
            raise ValueError("Race did not produce exactly one owner and one native failure")
        checked = inspect_record(cases / row["id"])
        dispatches = [event for event in checked["events"] if event["event"] == "provider_dispatched"]
        if len(dispatches) != 1 or checked["result"]["provider_dispatches"] != 1:
            raise ValueError("Race permitted duplicate provider dispatch")
        winner = reports[sample_errors.index(False)]
        if winner["samples"][0]["record"]["receipt"] != proof(cases / row["id"] / "receipt.json"):
            raise ValueError("Winning receipt differs")
        result = {"status": "PASS", "witness": "IX08", "launches": [launch for _, _, launch in children],
            "returncodes": returncodes, "processes_reaped": all(process.poll() is not None for process, _, _ in children),
            "native_sample_errors": sample_errors, "owners": 1, "provider_dispatches": 1,
            "receipt": proof(cases / row["id"] / "receipt.json"), "automatic_retry": False,
            "wall_seconds": time.perf_counter() - started,
            "scope": "Two direct native workers released from one barrier; no universal filesystem-race theorem"}
        publish(output / "RESULT.json", result)
        return result
    except BaseException as exc:
        publish(output / "FAILURE.json", {"type": type(exc).__name__, "message": str(exc), "automatic_retry": False})
        raise
    finally:
        for process, _, _ in children:
            _cleanup(process)
