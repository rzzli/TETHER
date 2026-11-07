"""Exclusive run reservation and fsynced hash-chained execution records."""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .serde import ContractError, canonical, fingerprint, freeze, parse_json


class RunJournal:
    def __init__(self, output: Path, *, kind: str = "run"):
        if kind not in ("run", "build"):
            raise ContractError("Unknown journal kind")
        self.kind = kind
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.path = self.output / "journal.jsonl"
        self._events = []
        self._durable_size = 0
        self._stream = self.path.open("xb", buffering=0)
        self.append(kind + "_reserved", run_id=str(uuid.uuid4()), owner_pid=os.getpid(),
                    created_at_utc=datetime.now(timezone.utc).isoformat())

    @property
    def events(self):
        return tuple(self._events)

    def append(self, event: str, **details):
        record = {"sequence": len(self._events), "event": event, "details": details,
                  "previous_sha256": self._events[-1]["sha256"] if self._events else None}
        record["sha256"] = fingerprint(record)
        self._stream.seek(self._durable_size)
        self._stream.truncate(self._durable_size)
        payload = memoryview(canonical(record) + b"\n")
        while payload:
            written = self._stream.write(payload)
            if not written:
                raise OSError("Journal write failed")
            payload = payload[written:]
        os.fsync(self._stream.fileno())
        self._durable_size = self._stream.tell()
        record = freeze(record)
        self._events.append(record)
        return record

    def fail(self, error: BaseException, stage: str):
        details = {"stage": stage, "error_class": type(error).__name__}
        if self.kind == "build":
            details["message"] = str(error)
        self.append(self.kind + ("_interrupted" if isinstance(error, KeyboardInterrupt) else "_failed"),
                    **details)

    def close(self):
        self._stream.close()


def read_chain(path: Path, allow_incomplete_tail=False):
    events, previous = [], None
    payload = path.read_bytes()
    lines = payload.splitlines()
    for index, line in enumerate(lines):
        if allow_incomplete_tail and index == len(lines) - 1 and not payload.endswith(b"\n"):
            break
        event = parse_json(line)
        digest = event.pop("sha256")
        if (event.get("sequence") != len(events) or event.get("previous_sha256") != previous or
                fingerprint(event) != digest):
            raise ContractError("Trace hash-chain failure")
        event["sha256"] = digest
        events.append(freeze(event))
        previous = digest
    if not events:
        raise ContractError("Empty execution trace")
    return tuple(events)


def inspect_run(output: Path) -> dict:
    events = read_chain(output / "journal.jsonl", allow_incomplete_tail=True)
    if events[0]["event"] == "build_reserved":
        stage, progress, failure = None, {}, None
        for event in events:
            if event["event"] == "build_stage":
                stage = event["details"]["stage"]
            elif event["event"] == "build_progress":
                progress = event["details"]
            elif event["event"] in ("build_failed", "build_interrupted"):
                failure = event["details"]
        return {"schema_version": 2, "kind": "build", "last_event": events[-1]["event"],
                "durable_events": len(events), "stage": stage, "progress": progress,
                "failure": failure, "build_report_present": (output / "build-report.json").is_file(),
                "recovery_action": "inspect only; start any replacement build in a new output directory"}
    attempts, measured, estimated = {}, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0}, {
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}
    for event in events:
        details = event["details"]
        if event["event"] == "dispatch":
            attempts[details["attempt_id"]] = details
        if event["event"] == "attempt_accounted":
            attempts.pop(details["attempt_id"], None)
            totals = measured if details["basis"] == "adapter_reported" else estimated
            for key in totals:
                totals[key] += details["usage"][key]
    for attempt in attempts.values():
        for key in estimated:
            estimated[key] += attempt["reserved"][key]
    return {"schema_version": 2, "last_event": events[-1]["event"], "durable_events": len(events),
            "unresolved_attempts": tuple(attempts), "measured_usage": measured,
            "estimated_upper_usage": estimated, "receipt_present": (output / "receipt.json").is_file(),
            "recovery_action": "inspect only; never automatically repeat unresolved calls"}

