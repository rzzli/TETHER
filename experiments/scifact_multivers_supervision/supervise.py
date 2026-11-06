"""Pin and supervise one owned qualification process; never retry inference.

Hard deadlines cover the owned child, including initial imports. Parent pinning
and small-file finalization are measured cooperative local operations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
MAX_CONTROL_BYTES = 8 * 1024 * 1024


class SupervisionError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise SupervisionError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write(path, value):
    with path.open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def regular(path):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
         "Required regular non-link file: " + str(path))
    return info


def pin(path):
    path = Path(path).resolve(strict=True)
    info = regular(path)
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
    need(count == info.st_size, "Pinned file size changed")
    return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}


def read_control(path):
    need(regular(path).st_size <= MAX_CONTROL_BYTES, "Control file size limit")
    raw = path.read_bytes()
    need(len(raw) <= MAX_CONTROL_BYTES, "Control file size changed")
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "Duplicate JSON key")
            value[key] = item
        return value
    def invalid(value):
        raise SupervisionError("Invalid numeric constant: " + value)
    return raw, json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def fresh_path(value):
    path = Path(value)
    need(path.is_absolute(), "Output path must be absolute")
    need(not path.exists() and not path.is_symlink(), "Output already exists or is a link")
    resolved = path.resolve()
    need(resolved.is_relative_to(ROOT) and resolved != ROOT and not resolved.exists(), "Fresh workspace output required")
    for parent in path.parents:
        if parent.exists():
            need(not parent.is_symlink() and not getattr(parent.lstat(), "st_file_attributes", 0) & 0x400, "Output reparse ancestor")
    return resolved


def preflight(manifest_path, expected_sha256):
    raw, manifest = read_control(Path(manifest_path))
    need(hashlib.sha256(raw).hexdigest() == expected_sha256, "Manifest external hash mismatch")
    need(manifest.get("schema_version") == 1 and manifest.get("kind") == "multivers_qualification_supervision", "Manifest schema")
    schedule = manifest["schedule"]
    need(type(schedule) is list and schedule and all(type(x) is str and x for x in schedule) and len(schedule) == len(set(schedule)), "Unique nonempty case schedule required")
    limits = manifest["limits"]
    for key, maximum in (("process_seconds", 1800), ("case_seconds", 120), ("poll_seconds", .25)):
        value = limits[key]
        need(type(value) in (int, float) and 0 < value <= maximum, "Invalid deadline: " + key)
    need(limits["case_seconds"] <= limits["process_seconds"], "Case cap exceeds process cap")
    launch, child = fresh_path(manifest["launch_output"]), fresh_path(manifest["qualification_output"])
    need(launch != child and not launch.is_relative_to(child) and not child.is_relative_to(launch), "Output trees overlap")
    command = manifest["command"]
    need(type(command) is list and len(command) > 3 and all(type(x) is str and x and "\x00" not in x for x in command), "Invalid command argv")
    flag_index = 1
    flags = []
    while flag_index < len(command) and command[flag_index].startswith('-'):
        flag = command[flag_index]
        need(flag in ('-I', '-B', '-u', '-X'), 'Unsupported interpreter flag')
        flags.append(flag)
        flag_index += 2 if flag == '-X' else 1
    need('-I' in flags and '-B' in flags and flag_index < len(command), "Isolated no-bytecode script child required")
    entrypoint = Path(command[flag_index])
    need(entrypoint.is_absolute() and entrypoint.suffix == '.py', 'Explicit absolute Python script required')
    need(command.count("--output") == 1 and command.index("--output") + 1 < len(command), "Explicit child output argument required")
    need(Path(command[command.index("--output")+1]).resolve() == child, "Child output differs from manifest")
    need(Path(manifest["cwd"]).resolve() == ROOT, "Explicit workspace working directory required")
    pins = manifest["pins"]
    need(type(pins) is list and pins, "Source/authority/interpreter pins required")
    identities = set()
    for item in pins:
        need(type(item) is dict and set(item) == {"path", "bytes", "sha256"}, "Invalid pin shape")
        observed = pin(item["path"])
        need(observed == item, "Pinned file differs: " + item["path"])
        need(item["path"] not in identities, "Duplicate file pin")
        identities.add(item["path"])
        need(not Path(item["path"]).is_relative_to(launch) and not Path(item["path"]).is_relative_to(child), "Output overlaps a source")
    need(str(Path(command[0]).resolve(strict=True)) in identities, "Child interpreter is not pinned")
    need(str(entrypoint.resolve(strict=True)) in identities, "Child entrypoint is not pinned")
    need(str(Path(__file__).resolve()) in identities, "Supervisor source is not pinned")
    need(Path(command[0]).is_absolute(), "Interpreter path must be absolute")
    return raw, manifest, launch, child


class Events:
    def __init__(self, schedule, launch_monotonic, case_seconds):
        self.schedule = schedule
        self.launch_monotonic = launch_monotonic
        self.case_seconds = case_seconds
        self.offset = 0
        self.buffer = b""
        self.rows = []
        self.active = None
        self.active_started = None
        self.next_index = 0
        self.completed = []
        self.last_monotonic = launch_monotonic
        self.terminal = False

    def accept(self, row, now):
        need(not self.terminal, "Event after terminal completion")
        need(type(row) is dict and type(row.get("event")) is str, "Malformed event")
        stamp = row.get("monotonic_seconds")
        need(type(stamp) in (int, float) and self.last_monotonic <= stamp <= now + .1, "Invalid/nonmonotonic event clock")
        self.last_monotonic = stamp
        kind = row["event"]
        if kind == "case_started":
            need(self.active is None and self.next_index < len(self.schedule) and row.get("case_id") == self.schedule[self.next_index], "Out-of-order/duplicate case start")
            self.active, self.active_started = row["case_id"], stamp
            self.next_index += 1
        elif kind == "case_completed":
            need(self.active is not None and row.get("case_id") == self.active, "Unmatched case completion")
            need(stamp - self.active_started <= self.case_seconds, "Case completed after deadline")
            self.completed.append(self.active)
            self.active, self.active_started = None, None
        elif kind == "completed":
            need(self.active is None and self.completed == self.schedule and row.get("status") == "passed", "Premature or invalid terminal event")
            self.terminal = True
        else:
            need(kind in ("started", "model_load_started", "models_loaded"), "Unknown event type")
        self.rows.append(row)

    def poll(self, path, now):
        if not path.exists():
            return
        size = regular(path).st_size
        need(self.offset <= size <= MAX_CONTROL_BYTES, "Event stream truncated/oversized")
        with path.open("rb") as stream:
            stream.seek(self.offset)
            raw = stream.read(MAX_CONTROL_BYTES - self.offset + 1)
        self.offset += len(raw)
        self.buffer += raw
        need(self.offset <= MAX_CONTROL_BYTES, "Event stream byte cap")
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            need(line, "Blank event row")
            self.accept(json.loads(line.decode("utf-8")), now)


def supervise(manifest_path, expected_sha256, *, interrupt_check=lambda: False):
    initial = time.monotonic()
    raw, manifest, launch, child = preflight(manifest_path, expected_sha256)
    launch.mkdir(parents=True, exist_ok=False)
    temp = launch / "temp"
    temp.mkdir()
    write(launch / "FROZEN.json", {"status": "FROZEN", "manifest_sha256": expected_sha256, "manifest": manifest,
          "supervisor": pin(__file__), "preflight_seconds": time.monotonic()-initial,
          "deadline_scope": "Owned child includes startup/imports and case work; parent pinning/finalization is cooperative local I/O."})
    write(launch / "COMMAND.json", {"argv": manifest["command"], "cwd": str(ROOT), "automatic_retry": False,
                                   "started_utc": datetime.now(timezone.utc).isoformat()})
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    limits = manifest["limits"]
    process, tracker, status, error = None, None, "failure", None
    child_started = time.monotonic()
    try:
        with (launch/"stdout.txt").open("xb") as stdout, (launch/"stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(manifest["command"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
            tracker = Events(manifest["schedule"], child_started, limits["case_seconds"])
            while True:
                now = time.monotonic()
                tracker.poll(child/"events.jsonl", now)
                if interrupt_check():
                    raise KeyboardInterrupt("Requested controller interruption")
                need(now-child_started < limits["process_seconds"], "Process deadline exceeded")
                need(tracker.active is None or now-tracker.active_started < limits["case_seconds"], "Case deadline exceeded")
                need((launch/"stdout.txt").stat().st_size + (launch/"stderr.txt").stat().st_size <= 32*1024*1024, "Child log byte cap")
                if process.poll() is not None:
                    break
                time.sleep(limits["poll_seconds"])
            tracker.poll(child/"events.jsonl", time.monotonic())
            need(process.returncode == 0, "Child exited unsuccessfully")
            need(not tracker.buffer and tracker.terminal and tracker.completed == manifest["schedule"], "Child lacks complete terminal event accounting")
            status = "completed"
    except KeyboardInterrupt as exc:
        status, error = "interrupted", {"type": type(exc).__name__, "message": str(exc)}
    except BaseException as exc:
        message = str(exc)
        status = "timeout" if "deadline" in message.lower() else "failure"
        error = {"type": type(exc).__name__, "message": message}
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except BaseException as exc:
                status, error = "failure", {"type": type(exc).__name__, "message": "Owned child termination failed: " + str(exc)}
        if tracker is not None and not tracker.terminal:
            try:
                tracker.poll(child/"events.jsonl", time.monotonic())
            except BaseException as exc:
                if error is None:
                    status, error = "failure", {"type": type(exc).__name__, "message": str(exc)}
    observed_seconds = time.monotonic()-child_started
    completed = set(tracker.completed if tracker else [])
    active = tracker.active if tracker else None
    dispositions = [{"case_id": cid, "status": "completed" if cid in completed else status if cid == active else "unexecuted"}
                    for cid in manifest["schedule"]]
    if tracker is not None and tracker.buffer and tracker.active is None and tracker.next_index < len(manifest["schedule"]):
        dispositions[tracker.next_index]["status"] = "unknown_start"
    preservation = True
    try:
        need(hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest() == expected_sha256, "Manifest changed after execution")
        for item in manifest["pins"]:
            need(pin(item["path"]) == item, "Frozen source/authority/interpreter changed")
    except BaseException as exc:
        preservation = False
        if error is None:
            error = {"type": type(exc).__name__, "message": str(exc)}
        status = "failure"
    record = {"schema_version": 1, "status": status, "exit_code": process.returncode if process else None,
              "child_pid": process.pid if process else None, "observed_child_phase_seconds": observed_seconds,
              "manifest_sha256": expected_sha256, "cases": dispositions, "error": error, "automatic_retry": False,
              "all_frozen_pins_unchanged": preservation, "events_observed": len(tracker.rows) if tracker else 0,
              "partial_event_bytes": len(tracker.buffer) if tracker else 0,
              "disposition_semantics": "Completed/start states follow complete retained events; an incomplete next start event is unknown_start, later unstarted cases remain unexecuted.",
              "completed_at_utc": datetime.now(timezone.utc).isoformat(),
              "deadline_scope": "Owned child only; final source hashes and terminal-file writes are cooperative parent I/O."}
    write(launch/"OUTCOME.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    result = supervise(args.manifest, args.manifest_sha256)
    print(json.dumps({"status": result["status"], "exit_code": result["exit_code"], "cases": result["cases"]}))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
