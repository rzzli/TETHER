"""Fresh, no-retry public acquisition, using only Python's standard library.

The CLI's parent supervises a separate worker for total and stalled-progress
deadlines. Tests may inject streams into acquire(); that direct API has only its
cooperative deadline and must not be used instead of the CLI for real downloads.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request


CHUNK_BYTES = 1024 * 1024
PROGRESS_BYTES = 256 * 1024 * 1024
TOTAL_SECONDS = 7200.0
NETWORK_SECONDS = 30.0
MAX_TOTAL_BYTES = 9_000_000_000
ALLOWED_HOSTS = (
    "download-r2.pytorch.org", "download.pytorch.org", "files.pythonhosted.org",
    "scifact.s3.us-west-2.amazonaws.com", "huggingface.co",
)
RECEIPT_FIELDS = ("logical_id", "source_url", "final_url", "started_utc", "completed_utc", "bytes", "sha256",
                  "http_etag", "http_version_id", "http_repo_commit", "status")
STOP_CONDITIONS = ("unexpected_length", "hash_mismatch", "version_or_revision_mismatch",
                   "aggregate_cap_exceeded", "redirect_outside_source_host_allowlist")
KIND_DIRECTORY = {"wheel": "wheel", "checkpoint": "checkpoint", "tokenizer_config": "tokenizer"}


class AcquisitionError(ValueError):
    """Acquisition integrity, contract or deadline failure."""


def need(condition, message):
    if not condition:
        raise AcquisitionError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise AcquisitionError("Invalid JSON numeric constant: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def bounded_read(path, maximum=2 * 1024 * 1024):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400),
         "Required regular non-link file is missing")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum, "Control file exceeds size bound")
    return raw


def safe_url(url, allowed_hosts=ALLOWED_HOSTS):
    need(isinstance(url, str) and 0 < len(url) <= 4096 and all(ord(c) >= 33 for c in url), "Invalid URL")
    parts = urllib.parse.urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:
        raise AcquisitionError("Invalid URL port") from exc
    need(parts.scheme == "https" and parts.hostname in allowed_hosts and parts.netloc == parts.hostname
         and port is None and not parts.username and not parts.password and not parts.fragment, "Unapproved HTTPS source URL")
    decoded = urllib.parse.unquote(parts.path)
    need(decoded.startswith("/") and "\\" not in decoded and "%" not in decoded and ":" not in decoded
         and all(x not in (".", "..") for x in decoded.split("/")), "Unsafe URL path")
    return parts


def _logical_id(value):
    need(isinstance(value, str) and len(value) <= 200 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*", value), "Unsafe logical ID")
    need(not value.endswith((".", " ")) and value.split(".", 1)[0].upper() not in
         {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)), *("LPT" + str(i) for i in range(1, 10))},
         "Windows-reserved logical ID")


def _hex(value, count):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(count) + "}", value) is not None


def validate_manifest(value):
    expected = {"schema", "status", "assets", "total_payload_bytes", "maximum_total_payload_bytes",
                "preserve_existing_downloader", "unique_attempt_directory_required", "receipt_fields",
                "stop_conditions", "allowed_source_hosts"}
    need(isinstance(value, dict) and set(value) == expected, "Manifest fields differ")
    need(value["schema"] == "bounded-sc02-acquisition-v1" and value["status"] == "planned_only_no_payloads_downloaded", "Manifest status/schema differs")
    need(value["preserve_existing_downloader"] is True and value["unique_attempt_directory_required"] is True, "Preservation/no-clobber policy required")
    for field, allowed in (("allowed_source_hosts", ALLOWED_HOSTS), ("receipt_fields", RECEIPT_FIELDS), ("stop_conditions", STOP_CONDITIONS)):
        need(isinstance(value[field], list) and len(value[field]) == len(allowed) and set(value[field]) == set(allowed), "Manifest policy differs: " + field)
    need(type(value["maximum_total_payload_bytes"]) is int and 0 < value["maximum_total_payload_bytes"] <= MAX_TOTAL_BYTES,
         "Invalid aggregate byte cap")
    need(isinstance(value["assets"], list) and 0 < len(value["assets"]) <= 64, "Invalid asset count")
    seen, total = set(), 0
    common = {"kind", "logical_id", "url", "expected_bytes", "expected_sha256"}
    for row in value["assets"]:
        need(isinstance(row, dict) and row.get("kind") in KIND_DIRECTORY, "Unknown asset kind")
        kind, logical = row["kind"], row.get("logical_id")
        fields = common | ({"expected_version_id", "expected_etag", "local_sha256_required_before_deserialization"} if kind == "checkpoint" else
                           {"expected_revision", "expected_git_blob_sha1", "local_sha256_required_before_use"} if kind == "tokenizer_config" else set())
        need(set(row) == fields, "Asset fields differ")
        _logical_id(logical)
        key = (KIND_DIRECTORY[kind] + "/" + logical).casefold()
        need(key not in seen, "Duplicate case-insensitive output identity")
        seen.add(key)
        need(type(row["expected_bytes"]) is int and 0 < row["expected_bytes"] <= value["maximum_total_payload_bytes"], "Invalid expected size")
        total += row["expected_bytes"]
        need(row["expected_sha256"] is None or _hex(row["expected_sha256"], 64), "Invalid SHA-256 pin")
        parts = safe_url(row["url"])
        path = urllib.parse.unquote(parts.path)
        if kind == "wheel":
            need(_hex(row["expected_sha256"], 64) and logical.endswith(".whl") and
                 parts.hostname in {"files.pythonhosted.org", "download-r2.pytorch.org", "download.pytorch.org"}
                 and path.rsplit("/", 1)[-1] == logical and not parts.query
                 and path.startswith("/packages/" if parts.hostname == "files.pythonhosted.org" else "/whl/cu128/"), "Wheel URL/hash does not match logical identity")
        elif kind == "checkpoint":
            version = row["expected_version_id"]
            need(isinstance(version, str) and re.fullmatch(r"[A-Za-z0-9._~\-]{1,200}", version), "Invalid S3 version pin")
            need(logical == "fever_sci.ckpt" and parts.hostname == "scifact.s3.us-west-2.amazonaws.com"
                 and path == "/longchecker/latest/checkpoints/fever_sci.ckpt"
                 and urllib.parse.parse_qsl(parts.query, keep_blank_values=True) == [("versionId", version)], "Checkpoint version URL mismatch")
            need(isinstance(row["expected_etag"], str) and re.fullmatch(r"[0-9a-f]{32}(?:-[1-9][0-9]*)?", row["expected_etag"])
                 and row["local_sha256_required_before_deserialization"] is True, "Checkpoint ETag/hash requirement missing")
        else:
            need(_hex(row["expected_revision"], 40) and _hex(row["expected_git_blob_sha1"], 40), "Invalid HF immutable revision/blob pin")
            need(logical in {"config.json", "vocab.json", "merges.txt", "tokenizer.json"} and parts.hostname == "huggingface.co"
                 and path == "/allenai/longformer-large-4096/resolve/" + row["expected_revision"] + "/" + logical
                 and not parts.query and row["local_sha256_required_before_use"] is True, "HF URL lacks expected immutable revision")
    need(type(value["total_payload_bytes"]) is int and total == value["total_payload_bytes"] <= value["maximum_total_payload_bytes"], "Manifest aggregate size mismatch/cap exceeded")
    return value


class Journal:
    def __init__(self, path, *, existing=False):
        self.path = Path(path)
        rows = verify_journal(path) if existing else []
        self.seq = len(rows)
        self.previous = rows[-1]["sha256"] if rows else "0" * 64
        if not existing:
            with self.path.open("xb"):
                pass

    def append(self, event, **details):
        row = {"seq": self.seq, "previous_sha256": self.previous, "event": event, "utc": utc(), "details": details}
        row["sha256"] = sha(canonical(row))
        with self.path.open("ab") as stream:
            stream.write(canonical(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.seq += 1
        self.previous = row["sha256"]
        return row


def verify_journal(path):
    raw = bounded_read(path, 4 * 1024 * 1024)
    need(not raw or raw.endswith(b"\n"), "Truncated journal retained")
    rows, previous = [], "0" * 64
    for line in raw.splitlines():
        row = strict_json(line)
        need(set(row) == {"seq", "previous_sha256", "event", "utc", "details", "sha256"}, "Invalid journal shape")
        calculated = sha(canonical({k: v for k, v in row.items() if k != "sha256"}))
        need(type(row["seq"]) is int and row["seq"] == len(rows) and row["previous_sha256"] == previous
             and row["sha256"] == calculated, "Journal chain mismatch")
        rows.append(row)
        previous = row["sha256"]
    return rows


def open_response(url, timeout, allowed_hosts, on_redirect):
    class BoundedRedirect(urllib.request.HTTPRedirectHandler):
        count = 0
        def redirect_request(self, request, fp, code, message, headers, target):
            target = urllib.parse.urljoin(request.full_url, target)
            safe_url(target, allowed_hosts)
            self.count += 1
            need(self.count <= 5, "Redirect count bound exceeded")
            on_redirect(request.full_url, target, code)
            return super().redirect_request(request, fp, code, message, headers, target)
    # No inherited proxy routing or authentication handlers; public source GET only.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), BoundedRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "TETHER-SC02-public-acquisition/1.0", "Accept-Encoding": "identity"})
    return opener.open(request, timeout=timeout)


def _headers(response):
    names = ("Content-Length", "Content-Encoding", "ETag", "x-amz-version-id", "X-Repo-Commit")
    result = {}
    for name in names:
        if hasattr(response.headers, "get_all"):
            entries = response.headers.get_all(name, [])
        else:
            entries = [value for key, value in response.headers.items() if key.lower() == name.lower()]
        need(len(entries) <= 1, "Ambiguous duplicate response header: " + name)
        result[name.lower()] = entries[0].strip() if entries else None
    return result


def _etag(value):
    if value is None:
        return None
    need(not value.startswith("W/"), "Weak HTTP ETag is not an identity pin")
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def _publish_partial(partial, final):
    # Windows rename is no-replace. POSIX link+unlink is likewise no-clobber.
    if os.name == "nt":
        os.rename(partial, final)
    else:
        os.link(partial, final)
        os.unlink(partial)


def _preflight(manifest_path, manifest_sha256, source_sha256, output, reservation_sha256=None):
    raw = bounded_read(manifest_path)
    need(_hex(manifest_sha256, 64) and sha(raw) == manifest_sha256, "Manifest hash mismatch")
    source = bounded_read(__file__)
    need(_hex(source_sha256, 64) and sha(source) == source_sha256, "Transport source hash mismatch")
    value = validate_manifest(strict_json(raw))
    output = Path(output).absolute()
    if reservation_sha256 is None:
        need(not output.exists() and not output.is_symlink(), "Output exists; a fresh no-clobber attempt is required")
    else:
        need(output.is_dir() and not output.is_symlink() and _hex(reservation_sha256, 64), "Missing supervisor reservation")
        need({p.name for p in output.iterdir()} == {"SUPERVISOR-STARTED.json"}, "Reserved attempt already started or contains unexpected files")
        reserved = bounded_read(output / "SUPERVISOR-STARTED.json")
        need(sha(reserved) == reservation_sha256, "Supervisor reservation hash differs")
        binding = strict_json(reserved)
        need(binding["manifest_sha256"] == manifest_sha256 and binding["source_sha256"] == source_sha256,
             "Supervisor reservation pins differ")
    need(output.resolve() != Path(manifest_path).resolve() and output.resolve() not in Path(manifest_path).resolve().parents,
         "Output overlaps manifest")
    # Reject symlink/junction ancestors; an absolute explicit attempt stays in its declared tree.
    for parent in output.parents:
        if parent.exists():
            need(not parent.is_symlink() and not (getattr(parent.lstat(), "st_file_attributes", 0) & 0x400), "Output has a link/reparse ancestor")
    return raw, value, output


def acquire(manifest_path, manifest_sha256, source_sha256, output, *, open_response=open_response,
            clock=time.monotonic, emit=lambda message: None, receipt_filename="RECEIPT.json", reservation_sha256=None):
    start = clock()
    deadline = start + TOTAL_SECONDS
    raw, manifest, output = _preflight(manifest_path, manifest_sha256, source_sha256, output, reservation_sha256)
    need(receipt_filename in {"RECEIPT.json", "WORKER-RECEIPT.json"}, "Unsupported receipt filename")
    if reservation_sha256 is None:
        output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "journal.jsonl")
    begun = {"schema_version": 1, "status": "started", "started_utc": utc(), "manifest_sha256": manifest_sha256,
             "source_sha256": source_sha256, "total_seconds": TOTAL_SECONDS, "network_seconds": NETWORK_SECONDS,
             "stream_bytes": CHUNK_BYTES, "automatic_retries": 0}
    write_new(output / "STARTED.json", begun)
    with (output / "INPUT-MANIFEST.json").open("xb") as stream:
        stream.write(raw)
    journal.append("acquisition_started", **begun)
    emit({"type": "progress", "event": "acquisition_started", "assets": len(manifest["assets"]), "bytes": manifest["total_payload_bytes"]})
    files, total, started_ids = [], 0, []
    try:
        for row in manifest["assets"]:
            need(clock() < deadline, "Acquisition total deadline exceeded")
            directory = output / KIND_DIRECTORY[row["kind"]]
            directory.mkdir(exist_ok=True)
            final = directory / row["logical_id"]
            partial = directory / (row["logical_id"] + ".partial")
            relative = final.relative_to(output).as_posix()
            note = {"schema_version": 1, "kind": row["kind"], "logical_id": row["logical_id"], "path": str(final),
                    "relative_path": relative, "receipt_path": str(final) + ".receipt.json",
                    "source_url": row["url"], "final_url": None, "started_utc": utc(), "completed_utc": None,
                    "expected_bytes": row["expected_bytes"], "expected_sha256": row["expected_sha256"],
                    "bytes": 0, "sha256": None, "http_etag": None, "http_version_id": None, "http_repo_commit": None,
                    "status": "started", "manifest_sha256": manifest_sha256, "source_sha256": source_sha256,
                    "redirects": [], "attempts": 1}
            write_new(str(final) + ".started.json", note)
            started_ids.append(relative)
            journal.append("asset_started", logical_id=row["logical_id"], relative_path=relative, expected_bytes=row["expected_bytes"])
            emit({"type": "heartbeat", "event": "asset_started", "logical_id": row["logical_id"]})
            response, count = None, 0
            hasher = hashlib.sha256()
            git_hasher = hashlib.sha1(b"blob " + str(row["expected_bytes"]).encode("ascii") + b"\0")
            next_progress = PROGRESS_BYTES
            try:
                with partial.open("xb") as stream:
                    def redirected(source, target, status):
                        need(clock() < deadline, "Deadline exceeded during redirect")
                        safe_url(target)
                        note["redirects"].append({"source_url": source, "target_url": target, "http_status": status})
                        journal.append("redirect", logical_id=row["logical_id"], target_url=target, http_status=status)
                        emit({"type": "heartbeat", "event": "redirect"})
                    remaining = deadline - clock()
                    need(remaining > 0, "Acquisition deadline before request")
                    response = open_response(row["url"], min(NETWORK_SECONDS, remaining), ALLOWED_HOSTS, redirected)
                    need(response.status == 200, "Unexpected HTTP status; no partial/range response accepted")
                    note["final_url"] = response.geturl()
                    safe_url(note["final_url"])
                    headers = _headers(response)
                    note.update(http_etag=_etag(headers["etag"]), http_version_id=headers["x-amz-version-id"], http_repo_commit=headers["x-repo-commit"])
                    need(headers["content-encoding"] in (None, "identity"), "Unexpected content encoding")
                    length = headers["content-length"]
                    need(isinstance(length, str) and re.fullmatch(r"[0-9]+", length) and int(length) == row["expected_bytes"], "Unexpected Content-Length")
                    if row["kind"] == "checkpoint":
                        need(note["http_version_id"] == row["expected_version_id"] and note["http_etag"] == row["expected_etag"], "Checkpoint version or ETag mismatch")
                    if row["kind"] == "tokenizer_config":
                        need(note["http_repo_commit"] == row["expected_revision"] and note["http_etag"] == row["expected_git_blob_sha1"], "HF repo commit or ETag mismatch")
                    journal.append("asset_headers_verified", logical_id=row["logical_id"], final_url=note["final_url"],
                                   http_etag=note["http_etag"], http_version_id=note["http_version_id"], http_repo_commit=note["http_repo_commit"])
                    while True:
                        need(clock() < deadline, "Acquisition total deadline exceeded")
                        chunk = response.read1(CHUNK_BYTES)
                        need(isinstance(chunk, bytes) and len(chunk) <= CHUNK_BYTES, "Invalid/beyond-bound stream chunk")
                        need(clock() < deadline, "Acquisition total deadline exceeded after read")
                        if not chunk:
                            break
                        need(count + len(chunk) <= row["expected_bytes"] and total + len(chunk) <= manifest["maximum_total_payload_bytes"], "Stream size or aggregate cap exceeded")
                        stream.write(chunk)
                        count += len(chunk)
                        total += len(chunk)
                        hasher.update(chunk)
                        git_hasher.update(chunk)
                        emit({"type": "heartbeat", "event": "stream_progress", "logical_id": row["logical_id"], "bytes": count})
                        if count >= next_progress:
                            journal.append("asset_progress", logical_id=row["logical_id"], bytes=count, total_bytes=total)
                            emit({"type": "progress", "event": "asset_progress", "logical_id": row["logical_id"], "bytes": count})
                            next_progress += PROGRESS_BYTES
                    stream.flush()
                    os.fsync(stream.fileno())
                need(count == row["expected_bytes"], "Unexpected final stream length")
                local_sha = hasher.hexdigest()
                need(row["expected_sha256"] is None or local_sha == row["expected_sha256"], "Upstream SHA-256 hash mismatch")
                if row["kind"] == "tokenizer_config":
                    need(git_hasher.hexdigest() == row["expected_git_blob_sha1"], "HF git blob hash mismatch")
                    note["git_blob_sha1"] = git_hasher.hexdigest()
                _publish_partial(partial, final)
                note.update(status="completed", bytes=count, sha256=local_sha, completed_utc=utc())
                write_new(str(final) + ".receipt.json", note)
                files.append(note)
                journal.append("asset_completed", logical_id=row["logical_id"], relative_path=relative, bytes=count, sha256=local_sha)
                emit({"type": "progress", "event": "asset_completed", "logical_id": row["logical_id"], "bytes": count})
            except BaseException as exc:
                note.update(status="failed", bytes=count, sha256=hasher.hexdigest(), failed_utc=utc(),
                            error_type=type(exc).__name__, error=str(exc)[:1000], partial_path=str(partial))
                # A success receipt or injected collision is never overwritten.
                if not Path(str(final) + ".receipt.json").exists():
                    write_new(str(final) + ".receipt.json", note)
                journal.append("asset_failed", logical_id=row["logical_id"], bytes=count, error_type=type(exc).__name__, error=str(exc)[:1000])
                raise
            finally:
                if response is not None:
                    response.close()
        need(total == manifest["total_payload_bytes"], "Completed aggregate differs from manifest")
        need(clock() < deadline, "Acquisition total deadline exceeded before sealing")
        need(sha(bounded_read(manifest_path)) == manifest_sha256 and sha(bounded_read(__file__)) == source_sha256,
             "Manifest/source hash changed during acquisition")
        journal.append("acquisition_completed", files=len(files), total_payload_bytes=total)
        receipt = {"schema_version": 1, "status": "PASS", "manifest_sha256": manifest_sha256, "source_sha256": source_sha256,
                   "started_utc": begun["started_utc"], "completed_utc": utc(), "root": str(output),
                   "files": files, "total_payload_bytes": total, "automatic_retries": 0,
                   "checkpoint_deserialized": False, "dependencies_installed": False,
                   "journal_tail_sha256": journal.previous,
                   "transport_seconds": clock() - start, "hard_watchdog_applied_by_cli_parent": receipt_filename == "WORKER-RECEIPT.json",
                   "deadline_scope": "CLI worker hard supervised; parent small-file finalization is cooperative local I/O"}
        write_new(output / receipt_filename, receipt)
        return receipt
    except BaseException as exc:
        journal.append("acquisition_failed", completed_assets=len(files), retained_stream_bytes=total, error_type=type(exc).__name__, error=str(exc)[:1000])
        write_new(output / "FAILED.json", {"schema_version": 1, "status": "FAIL", "failed_utc": utc(),
                  "manifest_sha256": manifest_sha256, "source_sha256": source_sha256, "completed_assets": len(files),
                  "retained_stream_bytes": total, "journal_tail_sha256": journal.previous,
                  "unexecuted_relative_paths": [KIND_DIRECTORY[a["kind"]] + "/" + a["logical_id"] for a in manifest["assets"]
                                                if KIND_DIRECTORY[a["kind"]] + "/" + a["logical_id"] not in started_ids],
                  "error_type": type(exc).__name__, "error": str(exc)[:1000], "automatic_retries": 0})
        raise


def supervise_process(command, *, total_seconds=TOTAL_SECONDS, stall_seconds=NETWORK_SECONDS, progress=lambda message: None):
    """Run one child, bound total elapsed and intervals without worker heartbeats."""
    start, last = time.monotonic(), time.monotonic()
    messages = queue.Queue()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               creationflags=flags, bufsize=0)
    def reader():
        try:
            while True:
                raw = process.stdout.readline(8193)
                if not raw:
                    break
                messages.put(raw)
        finally:
            messages.put(None)
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    count = 0
    try:
        while True:
            now = time.monotonic()
            need(now - start < total_seconds, "Supervisor total deadline exceeded")
            need(now - last < stall_seconds, "Supervisor stalled-progress timeout")
            try:
                raw = messages.get(timeout=min(0.05, max(0.001, total_seconds - (now - start))))
            except queue.Empty:
                if process.poll() is not None and not thread.is_alive():
                    break
                continue
            if raw is None:
                break
            need(len(raw) <= 8192 and raw.endswith(b"\n"), "Invalid/overlong worker control message")
            message = strict_json(raw)
            need(isinstance(message, dict) and message.get("type") in {"heartbeat", "progress", "terminal"}, "Unexpected worker control message")
            count += 1
            last = time.monotonic()
            if message["type"] != "heartbeat":
                progress(message)
        remaining = min(2.0, total_seconds - (time.monotonic() - start))
        need(remaining > 0, "Supervisor total deadline exceeded")
        exit_code = process.wait(timeout=remaining)
        return {"exit_code": exit_code, "elapsed_seconds": time.monotonic() - start, "control_messages": count,
                "total_seconds": total_seconds, "stalled_progress_seconds": stall_seconds, "child_pid": process.pid}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        thread.join(timeout=1)


def _emit(message):
    print(json.dumps(message, separators=(",", ":")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reservation-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        try:
            need(args.reservation_sha256 is not None, "Worker requires a parent reservation")
            acquire(args.manifest, args.manifest_sha256, args.source_sha256, args.output, emit=_emit,
                    receipt_filename="WORKER-RECEIPT.json", reservation_sha256=args.reservation_sha256)
            _emit({"type": "terminal", "status": "PASS"})
            return 0
        except BaseException as exc:
            _emit({"type": "terminal", "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:1000]})
            return 1
    _, _, output = _preflight(args.manifest, args.manifest_sha256, args.source_sha256, args.output)
    # Reserve once in the supervisor, before a worker exists, so a competing
    # launcher cannot write failure metadata into another attempt's directory.
    output.mkdir(parents=True, exist_ok=False)
    reserved = {"schema_version": 1, "status": "started", "started_utc": utc(), "nonce": secrets.token_hex(16),
                "manifest_sha256": args.manifest_sha256, "source_sha256": args.source_sha256, "parent_pid": os.getpid()}
    write_new(output / "SUPERVISOR-STARTED.json", reserved)
    reservation_sha256 = sha(bounded_read(output / "SUPERVISOR-STARTED.json"))
    _emit({"type": "progress", "event": "supervisor_started", "output": str(output)})
    # Preserve caller's explicitly qualified fresh prefix, while disallowing writes.
    command = [sys.executable, "-I", "-B"]
    if sys.pycache_prefix:
        command += ["-X", "pycache_prefix=" + str(sys.pycache_prefix)]
    command += [str(Path(__file__).resolve()), "--worker", "--manifest", str(args.manifest.resolve()),
                "--manifest-sha256", args.manifest_sha256, "--source-sha256", args.source_sha256,
                "--output", str(output), "--reservation-sha256", reservation_sha256]
    try:
        supervision = supervise_process(command, progress=_emit)
        need(supervision["exit_code"] == 0, "Acquisition worker exited unsuccessfully")
        worker = strict_json(bounded_read(output / "WORKER-RECEIPT.json"))
        need(worker["status"] == "PASS" and worker["manifest_sha256"] == args.manifest_sha256
             and worker["source_sha256"] == args.source_sha256, "Worker receipt pins differ")
        journal = Journal(output / "journal.jsonl", existing=True)
        need(verify_journal(journal.path)[-1]["event"] == "acquisition_completed", "Worker completion journal missing")
        journal.append("supervisor_completed", **supervision)
        worker.update(supervision=supervision, journal_tail_sha256=journal.previous,
                      hard_watchdog_applied_by_cli_parent=True, reservation_sha256=reservation_sha256)
        write_new(output / "RECEIPT.json", worker)
        _emit({"type": "terminal", "status": "PASS", "files": len(worker["files"]), "total_payload_bytes": worker["total_payload_bytes"], "receipt": str(output / "RECEIPT.json")})
        return 0
    except BaseException as exc:
        # The worker is already stopped by supervise_process's finally block.
        output.mkdir(parents=True, exist_ok=True)
        failure = {"schema_version": 1, "status": "FAIL", "failed_utc": utc(), "manifest_sha256": args.manifest_sha256,
                   "source_sha256": args.source_sha256, "error_type": type(exc).__name__, "error": str(exc)[:1000], "automatic_retries": 0}
        try:
            path = output / "journal.jsonl"
            journal = Journal(path, existing=path.exists())
            journal.append("supervisor_failed", **failure)
            failure["journal_tail_sha256"] = journal.previous
        except BaseException as journal_error:
            failure["journal_error"] = type(journal_error).__name__ + ": " + str(journal_error)[:1000]
        write_new(output / "SUPERVISOR-FAILED.json", failure)
        _emit({"type": "terminal", **failure})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
