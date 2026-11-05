"""Bounded trusted native checks; consumes frozen candidates without re-inference.

Source reconstruction is a trusted audit, so it may inspect restricted archive
members. This process is separate from the producer and cannot change its inputs.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import math
from pathlib import Path
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from asof.atomic import publish_bytes
from asof.serde import ContractError, canonical, fingerprint, parse_json, safe_child
from experiments.scifact.native_contract import validate_schedule
from experiments.scifact.runtime import Watchdog, load_input, measured
from experiments.scifact.tether_adapter import (NativeSession, build_context, make_request,
                                               validate_resources, verify_candidate, verify_session)


def need(condition, message):
    if not condition:
        raise ContractError(message)


def write(path, value):
    publish_bytes(Path(path), canonical(value) + b"\n")


def verify_producer(recipe, context, records):
    """Join original producer dispatch events to the exact captured candidate records."""
    anchor = recipe["producer_session"]
    need(isinstance(anchor, Mapping) and set(anchor) == {"path", "receipt_sha256"}, "Invalid producer session anchor")
    root = Path(anchor["path"])
    verified = verify_session(root, expected_receipt_sha256=anchor["receipt_sha256"])
    receipt_path = root / "receipt.json"
    receipt = parse_json(load_input({"path": str(receipt_path), "sha256": anchor["receipt_sha256"], "bytes": receipt_path.stat().st_size}))
    journal_path = root / "journal.jsonl"
    journal = load_input({"path": str(journal_path), "sha256": receipt["outputs"]["journal.jsonl"], "bytes": journal_path.stat().st_size})
    events = [parse_json(line) for line in journal.splitlines()]
    headers = [event["details"] for event in events if event["event"] == "native_configured"]
    expected_schedule = ["setup", *map(str, recipe["schedule"])]
    need(len(headers) == 1 and list(headers[0]["schedule"]) == expected_schedule and
         fingerprint(headers[0]["configuration"]) == fingerprint(recipe["configuration"]),
         "Producer session configuration/schedule differs from frozen checking frame")
    dispatched = {event["details"]["cell_id"]: event["details"]["request"]
                  for event in events if event["event"] == "native_dispatch"}
    terminals = {event["details"]["cell_id"]: event["details"] for event in events if event["event"] == "native_terminal"}
    need(set(dispatched) == set(terminals) == set(expected_schedule), "Producer trace is incomplete")
    inputs = {}
    for logical, name in (("model_json", "model.json"), ("model_arrays", "arrays.npz")):
        matches = [item for item in context.model["files"] if item["path"] == name]
        need(len(matches) == 1, "Native producer model asset inventory differs")
        inputs[logical] = {"path": str(safe_child(context.model_root, name)),
                           "sha256": matches[0]["sha256"], "bytes": matches[0]["bytes"]}
    query = context.manifest["products"]["queries_dev"]
    inputs["queries"] = {"path": str(safe_child(context.preparation_root, query["path"])),
                         "sha256": query["sha256"], "bytes": query["bytes"]}
    need(fingerprint(dispatched["setup"]) == fingerprint({"mode": "predict", "inputs": inputs}),
         "Producer setup model/query inputs differ from frozen checking frame")
    for claim_id, record in zip(recipe["schedule"], records):
        key = str(claim_id)
        expected = {"query": context.queries[claim_id], "configuration": recipe["configuration"]}
        need(fingerprint(dispatched[key]) == fingerprint(expected), "Producer query/configuration differs from frozen checking frame")
        terminal = terminals[key]
        need(terminal["status"] == "completed" and terminal["record_fingerprint"] == fingerprint(record) and
             terminal["record_sha256"] == hashlib.sha256(canonical(record) + b"\n").hexdigest(),
             "Captured candidate differs from original producer terminal record")
    return verified


def run(recipe_path, output):
    recipe = parse_json(Path(recipe_path).read_bytes())
    keys = {"schema_version", "preparation_root", "preparation_manifest_sha256", "model_root",
            "model_manifest_sha256", "cutoff", "workspace_root", "container_admission", "policy_sha256",
            "configuration", "schedule", "candidates", "producer_session", "limits"}
    need(isinstance(recipe, Mapping) and set(recipe) == keys and recipe["schema_version"] == 1,
         "Invalid native checker recipe")
    schedule = list(validate_schedule(recipe["schedule"]))
    limits = recipe["limits"]
    need(set(limits) == {"phase_seconds", "query_seconds", "memory_bytes"} and
         all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in limits.values()) and
         type(limits["memory_bytes"]) is int, "Invalid native checker limits")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "recipe.json", recipe)
    phase_started, phase_cpu = time.perf_counter(), time.process_time()
    dispositions = []
    current = None

    def remaining():
        value = limits["phase_seconds"] - (time.perf_counter() - phase_started)
        need(value > 0, "Native checking phase time budget exhausted")
        return value

    with Watchdog(output, memory_limit=limits["memory_bytes"], sample_seconds=.5,
                  call_seconds=limits["phase_seconds"]) as watchdog:
        watchdog.active_started = phase_started
        try:
            raw = load_input(recipe["candidates"])
            records = parse_json(raw)
            need(isinstance(records, list), "Checker candidates must be a terminal-record array")
            need(all(isinstance(row, Mapping) and row.get("status") == "completed" for row in records),
                 "Checker requires completed producer records")
            need([row.get("cell_id") for row in records] == [str(key) for key in schedule],
                 "Checker candidate identities/order differ from full schedule")
            for row in records:
                validate_resources(row["resources"])
                need(isinstance(row.get("result"), Mapping) and
                     {"prediction", "retrieved", "source_bindings"} <= set(row["result"]),
                     "Missing producer candidate fields")
            context = build_context(recipe["preparation_root"], recipe["preparation_manifest_sha256"],
                                    recipe["model_root"], recipe["model_manifest_sha256"], recipe["cutoff"],
                                    workspace_root=recipe["workspace_root"],
                                    container_admission=recipe["container_admission"])
            need(context.policy_sha256 == recipe["policy_sha256"], "Checker policy binding differs")
            need(fingerprint(context.model["configuration"]) == fingerprint(recipe["configuration"]),
                 "Checker configuration differs from frozen model")
            need(list(context.queries) == schedule, "Checker schedule differs from admitted query view")
            producer_verification = verify_producer(recipe, context, records)
            setup_resources = measured(phase_started, phase_cpu, input_bytes=len(raw), output_bytes=0, examples=0)
            with NativeSession(output / "session", [str(key) for key in schedule], recipe["configuration"],
                               max_wall_seconds=remaining()) as session:
                try:
                    for claim_id, produced in zip(schedule, records):
                        current = str(claim_id)
                        started, cpu = time.perf_counter(), time.process_time()
                        watchdog.call_seconds = min(limits["query_seconds"], remaining())
                        watchdog.active_started = started
                        request = make_request(context, claim_id, recipe["configuration"])
                        session.begin(current, request)
                        value = produced["result"]
                        envelope = {"request_sha256": fingerprint(request), "prediction_sha256": fingerprint(value["prediction"]),
                                    "retrieved": value["retrieved"], "source_bindings": value["source_bindings"],
                                    "producer_code_sha256": context.model["producer_code"]["sha256"],
                                    "resources": produced["resources"]}
                        try:
                            result = verify_candidate(context, request, value["prediction"], envelope)
                            status, reason = "accepted", None
                        except ContractError as error:
                            status, reason = "rejected", str(error)
                            result = {"kind": "rejected_candidate", "request": request, "prediction": value["prediction"],
                                      "envelope": envelope, "error_type": "ContractError", "message": reason}
                        need(time.perf_counter() - started <= limits["query_seconds"], "Native check cell deadline exceeded")
                        record = session.finish(current, result, measured(started, cpu, input_bytes=len(canonical(value)),
                                                output_bytes=len(canonical(result)), examples=1), status=status)
                        need(record["status"] == status, "Native check session budget exhausted")
                        dispositions.append({"id": claim_id, "producer_status": "produced", "check_status": status,
                                             "prediction": value["prediction"], "reason": reason})
                        current = None
                    watchdog.call_seconds = remaining()
                    watchdog.active_started = time.perf_counter()
                    receipt = session.finalize()
                except BaseException as error:
                    if session.active is not None:
                        try:
                            session.fail(current, error, measured(started, cpu, input_bytes=None, output_bytes=None, examples=None))
                        except BaseException:
                            pass  # Keep the primary failure and durable attempt; never repeat it.
                    raise
            verify_started, verify_cpu = time.perf_counter(), time.process_time()
            watchdog.call_seconds = remaining()
            watchdog.active_started = verify_started
            verification = verify_session(output / "session", expected_receipt_sha256=receipt["sha256"], context=context)
            verification_resources = measured(verify_started, verify_cpu, input_bytes=None, output_bytes=None, examples=len(schedule))
            remaining()
            write(output / "dispositions.json", dispositions)
            write(output / "verification.json", verification)
            write(output / "producer-verification.json", producer_verification)
            write(output / "COMPLETE.json", {"status": "completed", "session_receipt_sha256": receipt["sha256"],
                  "candidate_input_sha256": recipe["candidates"]["sha256"], "policy_sha256": context.policy_sha256,
                  "setup_resources": setup_resources, "verification_resources": verification_resources,
                  "memory_sampling_seconds": watchdog.sample_seconds, "peak_sampled_working_set_bytes": watchdog.peak_sample,
                  "memory_samples": watchdog.samples, "memory_observations": watchdog.memory_observations,
                  "memory_sampling_status": "observed" if watchdog.memory_observations else "no_observations",
                  "scope": "trusted_source_audit_and_native_checks_not_scientific_truth"})
            watchdog.active_started = None
        except BaseException as error:
            watchdog.active_started = None
            write(output / "PARTIAL-DISPOSITIONS.json", dispositions)
            write(output / "FAILED.json", {"status": "failed", "error_type": type(error).__name__, "message": str(error),
                  "active_cell": current, "schedule": schedule, "recovery": "inspect only; no automatic repeat"})
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.recipe, args.output)
