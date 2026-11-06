"""Small, independently implemented immutable captures and durable case records.

These helpers belong to the Inspect policy extension and count in its footprint.
They are not native Inspect features, source authentication, or an OS sandbox.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from types import MappingProxyType


def thaw(value):
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw(item) for item in value]
    return value


def canonical(value):
    return json.dumps(thaw(value), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def freeze(value):
    """Copy and recursively freeze the JSON domain; reject nonfinite/custom data."""
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("JSON mapping keys must be strings")
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("Only finite JSON data may be captured")


def parse(raw):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = item
        return result
    def nonfinite(_):
        raise ValueError("Nonfinite JSON value")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=nonfinite)


def safe_path(path):
    path = Path(os.path.abspath(path))
    for item in (*reversed(path.parents), path):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Linked/reparse paths are not allowed")
    return path


def read_bytes(path, maximum=64 * 1024 * 1024):
    """Bound by actual size plus one growth byte, then compare open/path identity."""
    path = safe_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
        raise ValueError("Nonregular or oversized input")
    key = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if key(before) != key(opened):
            raise ValueError("Input changed before read")
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(raw) != before.st_size or key(before) != key(after) or key(before) != key(path.stat()):
        raise ValueError("Input changed during read")
    return raw


def proof(path, maximum=64 * 1024 * 1024):
    raw = read_bytes(path, maximum)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def checked_json(path, expected, maximum=64 * 1024 * 1024):
    raw = read_bytes(path, maximum)
    if expected != {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}:
        raise ValueError("Input proof differs")
    return freeze(parse(raw))


def publish(path, value):
    raw = canonical(value) + b"\n"
    path = safe_path(path)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def reserve(path):
    path = safe_path(path)
    path.mkdir(parents=False, exist_ok=False)
    return path


class CaseRecord:
    """Exclusive no-resume record, durable before a provider can be dispatched."""

    def __init__(self, path, request):
        self.path = reserve(path)
        self.request = freeze(request)
        self.previous = "0" * 64
        self.sequence = 0
        self.closed = False
        self.request_proof = publish(self.path / "request.json", self.request)
        self.append("reserved", {"request_sha256": digest(self.request)})

    def append(self, event, details):
        if self.closed:
            raise RuntimeError("Record already finalized")
        row = {"sequence": self.sequence, "previous_sha256": self.previous,
               "at_utc": datetime.now(timezone.utc).isoformat(),
               "event": event, "details": thaw(freeze(details))}
        row["sha256"] = digest(row)
        with (self.path / "journal.jsonl").open("ab") as stream:
            stream.write(canonical(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1
        self.previous = row["sha256"]
        return freeze(row)

    def finish(self, result):
        captured = freeze(result)
        result_proof = publish(self.path / "result.json", captured)
        self.append("terminal", {"result": result_proof})
        receipt = {"schema_version": 1, "kind": "inspect_policy_case",
                   "request": self.request_proof, "result": result_proof,
                   "journal": proof(self.path / "journal.jsonl"),
                   "terminal_chain_sha256": self.previous}
        receipt_proof = publish(self.path / "receipt.json", receipt)
        self.closed = True
        return {"result": captured, "receipt": receipt_proof}


def inspect_record(path, *, receipt_sha256=None, allow_partial=False):
    """Check retained bytes/chain; an unfinished prefix is never redispatched."""
    path = safe_path(path)
    request = parse(read_bytes(path / "request.json"))
    raw = read_bytes(path / "journal.jsonl")
    chunks = raw.splitlines(keepends=True)
    if chunks and not chunks[-1].endswith(b"\n"):
        if not allow_partial:
            raise ValueError("Unterminated journal")
        chunks.pop()
    previous = "0" * 64
    events = []
    for sequence, line in enumerate(chunks):
        row = parse(line)
        if set(row) != {"sequence", "previous_sha256", "at_utc", "event", "details", "sha256"}:
            raise ValueError("Journal fields differ")
        unsigned = {key: value for key, value in row.items() if key != "sha256"}
        if row["sequence"] != sequence or row["previous_sha256"] != previous or row["sha256"] != digest(unsigned):
            raise ValueError("Journal chain differs")
        previous = row["sha256"]
        events.append(row)
    if not events or events[0]["event"] != "reserved" or events[0]["details"] != {"request_sha256": digest(request)}:
        raise ValueError("Request/journal binding differs")
    receipt_path = path / "receipt.json"
    if not receipt_path.exists():
        if not allow_partial:
            raise ValueError("No terminal receipt")
        return freeze({"status": "partial", "request": request, "events": events,
                       "automatic_redispatch": False})
    receipt_raw = read_bytes(receipt_path)
    if receipt_sha256 is not None and hashlib.sha256(receipt_raw).hexdigest() != receipt_sha256:
        raise ValueError("External receipt anchor differs")
    receipt = parse(receipt_raw)
    if set(receipt) != {"schema_version", "kind", "request", "result", "journal", "terminal_chain_sha256"} or receipt["schema_version"] != 1 or receipt["kind"] != "inspect_policy_case":
        raise ValueError("Receipt fields differ")
    for name in ("request", "result", "journal"):
        filename = name + (".jsonl" if name == "journal" else ".json")
        if proof(path / filename) != receipt[name]:
            raise ValueError("Receipt output proof differs")
    if events[-1]["event"] != "terminal" or events[-1]["details"] != {"result": receipt["result"]} or receipt["terminal_chain_sha256"] != previous:
        raise ValueError("Terminal binding differs")
    result = parse(read_bytes(path / "result.json"))
    return freeze({"status": "sealed", "request": request, "result": result,
                   "events": events, "automatic_redispatch": False})
