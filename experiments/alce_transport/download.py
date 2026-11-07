"""Pinned large-file acquisition; no retry, overwrite, range resume or model use.

The Windows CLI owns a supervised worker. The injected-stream acquire() API has
cooperative deadlines and is for qualification, not unsupervised acquisition.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "packages/tether/src", ROOT / "src", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from experiments.scifact_multivers_transport import download as primitives
from experiments.labbench.runtime import DeadlineWatchdog, contain_process_tree
from tether import _process as processes

AcquisitionError = primitives.AcquisitionError
need, canonical, strict_json = primitives.need, primitives.canonical, primitives.strict_json
write_new, Journal, utc = primitives.write_new, primitives.Journal, primitives.utc
CHUNK_BYTES = 1024 * 1024
MAX_CONTROL_BYTES = 4 * CHUNK_BYTES
PROGRESS_BYTES = 256 * CHUNK_BYTES
KIND = "alce_acquisition_manifest_v1"
RESERVED = {"CON", "PRN", "AUX", "NUL", *("COM" + str(i) for i in range(1, 10)), *("LPT" + str(i) for i in range(1, 10))}


def hex_value(value, size=64):
    return type(value) is str and re.fullmatch("[0-9a-f]{%d}" % size, value) is not None


def relative(value):
    need(type(value) is str and 0 < len(value) <= 240 and not value.startswith("/") and "\\" not in value, "Safe POSIX path required")
    need(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*", p) and p not in (".", "..") and not p.endswith((".", " "))
             and p.split(".", 1)[0].upper() not in RESERVED for p in value.split("/")), "Unsafe/reserved relative path")
    return value


def local_path(value):
    path = Path(value)
    need(path.is_absolute() and not str(path).startswith(("\\\\", "//")) and ".." not in path.parts and path == path.resolve(),
         "Canonical absolute local path required")
    for part in path.parts[1:]:
        need(not part.endswith((".", " ")) and ":" not in part and part.split(".", 1)[0].upper() not in RESERVED, "Unsafe physical path")
    for parent in (path, *path.parents):
        if parent.exists() or parent.is_symlink():
            need(not parent.is_symlink() and not getattr(parent.lstat(), "st_file_attributes", 0) & 0x400, "Linked/reparse paths rejected")
    return path


def identity(info): return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def capture(path, maximum=MAX_CONTROL_BYTES):
    path = local_path(path); before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Bounded regular control file required")
    with path.open("rb") as stream:
        need(identity(os.fstat(stream.fileno())) == identity(before), "Control changed before read")
        raw = stream.read(before.st_size + 1); after = os.fstat(stream.fileno())
    local_path(path)
    need(len(raw) == before.st_size and identity(before) == identity(after) == identity(path.stat()), "Control changed during read")
    return raw, dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def proof_shape(value):
    need(type(value) is dict and set(value) == {"path", "bytes", "sha256"} and type(value["bytes"]) is int
         and 0 < value["bytes"] <= MAX_CONTROL_BYTES and hex_value(value["sha256"]), "Exact metadata proof required")
    local_path(value["path"])


def bound(proof):
    proof_shape(proof); raw, actual = capture(proof["path"])
    need(actual == proof, "Metadata proof changed")
    return raw


def source_pins():
    """Logical byte pins for transport and reused infrastructure, not scientific ancestry."""
    files = [Path(__file__).resolve(), ROOT / "experiments/alce_transport/__init__.py",
             Path(primitives.__file__).resolve(), ROOT / "experiments/labbench/runtime.py"]
    for folder in (ROOT / "src/tether_engine", ROOT / "packages/tether/src/tether"):
        files.extend(folder.rglob("*.py"))
    result = {}
    for path in sorted(set(files)):
        raw, proof = capture(path)
        result[path.relative_to(ROOT).as_posix()] = dict(bytes=proof["bytes"], sha256=proof["sha256"])
    for name, module in tuple(sys.modules.items()):
        prefix = next((p for p in ("tether_engine", "tether") if name == p or name.startswith(p + ".")), None)
        if prefix is None or not getattr(module, "__file__", "").endswith(".py"): continue
        rest = name.split(".")[1:]
        base = "src/tether_engine" if prefix == "tether_engine" else "packages/tether/src/tether"
        suffix = "/".join(rest) if rest else ""
        logical = base + ("/" + suffix if suffix else "") + ("/__init__.py" if Path(module.__file__).name == "__init__.py" else ".py")
        # Facade aliases intentionally point at the corresponding engine module.
        actual = Path(module.__file__).resolve()
        if prefix == "tether" and "tether_engine" in actual.parts: continue
        need(logical in result, "Undeclared loaded transport dependency")
        _, p = capture(actual)
        need(result[logical] == dict(bytes=p["bytes"], sha256=p["sha256"]), "Loaded dependency differs from declared source")
    return result


def source_fingerprint(): return hashlib.sha256(canonical(source_pins())).hexdigest()


def safe_url(value, hosts):
    need(type(value) is str and 0 < len(value) <= 16384 and all(33 <= ord(c) <= 126 for c in value), "Bounded ASCII URL required")
    parts = urllib.parse.urlsplit(value)
    try: port = parts.port
    except ValueError as error: raise AcquisitionError("Invalid URL port") from error
    need(parts.scheme == "https" and parts.hostname in hosts and parts.netloc == parts.hostname and port is None
         and not parts.username and not parts.password and not parts.fragment, "Unapproved HTTPS source")
    decoded = urllib.parse.unquote(parts.path)
    need(decoded.startswith("/") and "\\" not in decoded and "%" not in decoded and ":" not in decoded
         and all(p not in (".", "..") for p in decoded.split("/")), "Unsafe URL path")
    return parts


def public_url(value):
    parts = urllib.parse.urlsplit(value)
    return dict(url=urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
                query_sha256=hashlib.sha256(parts.query.encode()).hexdigest() if parts.query else None)


def validate_manifest(value):
    need(type(value) is dict and set(value) == {"schema_version", "kind", "approved_root", "limits", "allowed_hosts", "assets"}, "Manifest fields differ")
    need(type(value["schema_version"]) is int and value["schema_version"] == 1 and value["kind"] == KIND, "Manifest version differs")
    local_path(value["approved_root"]); limits = value["limits"]
    need(type(limits) is dict and set(limits) == {"max_total_bytes", "total_seconds", "network_seconds", "stall_seconds", "max_redirects"}, "Limit fields differ")
    for key, low, high in (("max_total_bytes", 1, 256 * 1024**3), ("total_seconds", 1, 86400),
                           ("network_seconds", 1, 300), ("stall_seconds", 1, 1800), ("max_redirects", 0, 10)):
        need(type(limits[key]) is int and low <= limits[key] <= high, "Invalid limit: " + key)
    need(limits["network_seconds"] <= limits["stall_seconds"] <= limits["total_seconds"], "Network/stall/total limits disagree")
    hosts = value["allowed_hosts"]
    need(type(hosts) is list and 0 < len(hosts) <= 16 and len(hosts) == len(set(hosts))
         and all(type(h) is str and re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}", h)
                 and not h.endswith((".local", ".localhost", ".internal")) for h in hosts), "Exact public hostname allowlist required")
    need(type(value["assets"]) is list and 0 < len(value["assets"]) <= 512, "Bounded nonempty asset list required")
    ids, paths, total = set(), [], 0
    for row in value["assets"]:
        need(type(row) is dict and set(row) == {"id", "product_id", "revision", "url", "destination", "expected_bytes", "digest", "metadata_proof", "rights_reference"}, "Asset fields differ")
        for key in ("id", "product_id"): need("/" not in relative(row[key]), "Single-component ID required")
        need(row["id"].casefold() not in ids, "Duplicate asset ID"); ids.add(row["id"].casefold())
        dest = relative(row["destination"]).casefold()
        need(all(dest != p and not dest.startswith(p + "/") and not p.startswith(dest + "/") for p in paths), "Overlapping destinations")
        paths.append(dest)
        need(type(row["expected_bytes"]) is int and 0 < row["expected_bytes"] <= limits["max_total_bytes"], "Exact positive asset size required")
        total += row["expected_bytes"]; digest = row["digest"]
        need(type(digest) is dict and set(digest) == {"algorithm", "kind", "value"} and
             (((digest["algorithm"], digest["kind"]) == ("sha256", "content") and hex_value(digest["value"])) or
              ((digest["algorithm"], digest["kind"]) == ("sha1", "git_blob") and hex_value(digest["value"], 40))), "Pinned content/Git-blob digest required")
        rev = row["revision"]; parts = safe_url(row["url"], hosts)
        need(type(rev) is dict and set(rev) == {"kind", "value"} and rev["kind"] in ("git_commit", "version"), "Explicit revision required")
        if rev["kind"] == "git_commit":
            need(hex_value(rev["value"], 40) and rev["value"] in parts.path.split("/"), "URL lacks immutable commit")
        else: need(type(rev["value"]) is str and re.fullmatch(r"[A-Za-z0-9_.+\-]{1,200}", rev["value"]), "Invalid explicit version")
        proof_shape(row["metadata_proof"])
        need(type(row["rights_reference"]) is str and 0 < len(row["rights_reference"]) <= 4096, "Rights reference required")
    need(total <= limits["max_total_bytes"], "Aggregate byte cap exceeded")
    return value


def controls(manifest_path, manifest_sha256, code_sha256, output, *, reserved=False):
    need(hex_value(manifest_sha256) and hex_value(code_sha256), "External manifest/code SHA256 required")
    raw, mp = capture(manifest_path); need(mp["sha256"] == manifest_sha256, "Manifest hash differs")
    manifest = validate_manifest(strict_json(raw)); out = local_path(output); approved = local_path(manifest["approved_root"])
    need(approved.is_dir() and out.parent == approved and (out.is_dir() if reserved else not out.exists()), "Fresh approved-root child required")
    relative(out.name)
    for p in [Path(manifest_path), *(Path(a["metadata_proof"]["path"]) for a in manifest["assets"])]:
        need(not p.is_relative_to(out), "Output overlaps control")
    for row in manifest["assets"]: bound(row["metadata_proof"])
    pins = source_pins(); need(hashlib.sha256(canonical(pins)).hexdigest() == code_sha256, "Executing code closure differs")
    return raw, mp, manifest, pins, out


def reservation(out, manifest_sha256, code_sha256, expected):
    raw, proof = capture(out / "RESERVATION.json"); token = strict_json(raw)
    need(hex_value(expected) and proof["sha256"] == expected and
         set(p.name for p in out.iterdir()) == {"RESERVATION.json", "COMMAND.json"}, "Reservation changed/already used")
    need(type(token) is dict and set(token) == {"manifest_sha256", "code_sha256", "nonce", "parent_pid", "utc"}
         and token["manifest_sha256"] == manifest_sha256 and token["code_sha256"] == code_sha256
         and hex_value(token["nonce"], 32) and type(token["parent_pid"]) is int and token["parent_pid"] > 0, "Invalid parent reservation")
    return token


def response_headers(response):
    result = {}
    for key in ("Content-Length", "Content-Encoding", "Content-Range", "ETag", "X-Repo-Commit"):
        values = response.headers.get_all(key, []) if hasattr(response.headers, "get_all") else [v for k, v in response.headers.items() if k.lower() == key.lower()]
        need(len(values) <= 1 and all(type(v) is str for v in values), "Ambiguous response header")
        result[key.lower()] = values[0].strip() if values else None
    return result


def open_response(url, timeout, hosts, on_redirect, max_redirects):
    class Redirect(urllib.request.HTTPRedirectHandler):
        count = 0
        def redirect_request(self, request, fp, code, message, headers, target):
            target = urllib.parse.urljoin(request.full_url, target); safe_url(target, hosts)
            self.count += 1; need(self.count <= max_redirects, "Redirect bound exceeded")
            on_redirect(request.full_url, target, code)
            return super().redirect_request(request, fp, code, message, headers, target)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), Redirect())
    request = urllib.request.Request(url, headers={"User-Agent": "TETHER-ALCE-acquisition/1", "Accept-Encoding": "identity"})
    return opener.open(request, timeout=timeout)


def acquire(manifest_path, manifest_sha256, code_sha256, output, *, opener=open_response, clock=time.monotonic,
            progress=lambda: None, reservation_sha256=None):
    """One attempt; injected streams and clocks are qualification seams."""
    start = clock()
    raw, mp, manifest, pins, out = controls(manifest_path, manifest_sha256, code_sha256, output, reserved=reservation_sha256 is not None)
    if reservation_sha256 is None: out.mkdir(exist_ok=False)
    else:
        reservation(out, manifest_sha256, code_sha256, reservation_sha256)
    deadline = start + manifest["limits"]["total_seconds"]; journal = Journal(out / "journal.jsonl")
    files, total_received, completed = [], 0, set()
    try:
        write_new(out / "REQUEST.json", dict(manifest=mp, code_sha256=code_sha256, code_pins=pins, started_utc=utc(),
            automatic_retries=0, range_resume=False, hard_parent_supervision=reservation_sha256 is not None))
        with (out / "INPUT-MANIFEST.json").open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        for name in ("payloads", "partials", "receipts"): (out / name).mkdir()
        journal.append("acquisition_started", manifest=mp, expected_assets=len(manifest["assets"]))
        for row in manifest["assets"]:
            need(clock() < deadline, "Acquisition deadline exceeded")
            final = local_path(out / "payloads" / row["destination"]); final.parent.mkdir(parents=True, exist_ok=True)
            partial = local_path(out / "partials" / (row["id"] + ".part")); receipt = out / "receipts" / (row["id"] + ".json")
            note = dict(id=row["id"], destination=row["destination"], expected_bytes=row["expected_bytes"], digest=row["digest"],
                source_url=public_url(row["url"]), revision=row["revision"], metadata_proof=row["metadata_proof"],
                rights_reference=row["rights_reference"], started_utc=utc(), attempts=1, redirects=[])
            write_new(out / "receipts" / (row["id"] + ".started.json"), note)
            journal.append("asset_reserved", id=row["id"], expected_bytes=row["expected_bytes"])
            count, received, response = 0, 0, None
            sha = hashlib.sha256(); blob = hashlib.sha1(b"blob " + str(row["expected_bytes"]).encode() + b"\0")
            next_progress = PROGRESS_BYTES
            try:
                with partial.open("xb") as stream:
                    opened = os.fstat(stream.fileno())
                    def redirect(source, target, status):
                        need(clock() < deadline, "Deadline during redirect"); safe_url(target, manifest["allowed_hosts"])
                        need(len(note["redirects"]) < manifest["limits"]["max_redirects"], "Redirect bound exceeded")
                        note["redirects"].append(dict(source=public_url(source), target=public_url(target), status=status))
                        journal.append("redirect", id=row["id"], target=public_url(target), status=status); progress()
                    progress(); remaining = deadline - clock(); need(remaining > 0, "Deadline before request")
                    response = opener(row["url"], min(manifest["limits"]["network_seconds"], remaining), manifest["allowed_hosts"], redirect, manifest["limits"]["max_redirects"])
                    need(response.status == 200, "Only complete HTTP200 bodies accepted; no range resume")
                    safe_url(response.geturl(), manifest["allowed_hosts"]); headers = response_headers(response)
                    need(headers["content-encoding"] in (None, "identity") and headers["content-range"] is None, "Encoded/range body rejected")
                    length = headers["content-length"]
                    need(length is None or re.fullmatch(r"[0-9]+", length) and int(length) == row["expected_bytes"], "Content length differs")
                    if headers["x-repo-commit"] is not None and row["revision"]["kind"] == "git_commit":
                        need(headers["x-repo-commit"] == row["revision"]["value"], "Returned revision differs")
                    note.update(final_url=public_url(response.geturl()), observed_headers=headers)
                    journal.append("headers_verified", id=row["id"], content_length=length); progress()
                    while True:
                        need(clock() < deadline, "Total deadline exceeded")
                        maximum = min(CHUNK_BYTES, row["expected_bytes"] - count + 1); chunk = response.read1(maximum)
                        need(type(chunk) is bytes and len(chunk) <= maximum, "Invalid bounded stream chunk")
                        received += len(chunk); total_received += len(chunk)
                        need(clock() < deadline, "Deadline after read")
                        if not chunk: break
                        need(count + len(chunk) <= row["expected_bytes"] and total_received <= manifest["limits"]["max_total_bytes"], "Payload overflow")
                        need(stream.write(chunk) == len(chunk), "Partial write")
                        count += len(chunk); sha.update(chunk); blob.update(chunk); progress()
                        if count >= next_progress:
                            journal.append("asset_progress", id=row["id"], stored_bytes=count, received_bytes=received); next_progress += PROGRESS_BYTES
                    stream.flush(); os.fsync(stream.fileno()); after = os.fstat(stream.fileno())
                need(count == row["expected_bytes"], "Truncated payload")
                need((opened.st_dev, opened.st_ino) == (after.st_dev, after.st_ino) and after.st_size == count and identity(after) == identity(local_path(partial).stat()), "Written payload changed")
                need((sha.hexdigest() if row["digest"]["kind"] == "content" else blob.hexdigest()) == row["digest"]["value"], "Payload digest mismatch")
                need(clock() < deadline, "Deadline before publish"); local_path(final); primitives._publish_partial(partial, final)
                note.update(status="completed", bytes=count, received_body_bytes=received, sha256=sha.hexdigest(), git_blob_sha1=blob.hexdigest(), path=str(final), completed_utc=utc())
                write_new(receipt, note); files.append(note); completed.add(row["id"])
                journal.append("asset_completed", id=row["id"], bytes=count, sha256=note["sha256"]); progress()
            except BaseException as error:
                note.update(status="failed", bytes=count, received_body_bytes=received, retained_partial_bytes=partial.stat().st_size if partial.exists() else None,
                    partial_path=str(partial), published_path=str(final) if final.exists() else None, error_type=type(error).__name__, error=str(error)[:1000], automatic_retries=0)
                try:
                    if not receipt.exists(): write_new(receipt, note)
                except BaseException: pass
                raise
            finally:
                if response is not None: response.close()
        need(clock() < deadline and capture(manifest_path)[1] == mp and source_pins() == pins, "Deadline/control/source changed before seal")
        for row in manifest["assets"]: bound(row["metadata_proof"])
        journal.append("acquisition_completed", assets=len(files), received_body_bytes=total_received)
        value = dict(kind="alce_acquisition_worker_receipt_v1", status="completed", manifest=mp, code_sha256=code_sha256, files=files,
            received_body_bytes=total_received, payload_bytes=sum(x["bytes"] for x in files), elapsed_seconds=clock()-start,
            journal_tail_sha256=journal.previous, automatic_retries=0, range_resume=False, hard_parent_supervision=reservation_sha256 is not None,
            model_loaded=False, dependencies_installed=False)
        write_new(out / "WORKER-RECEIPT.json", value)
        return value
    except BaseException as error:
        failure = dict(status="failed", error_type=type(error).__name__, error=str(error)[:1000], automatic_retries=0, utc=utc(),
            completed_assets=sorted(completed), received_body_bytes=total_received,
            uncompleted_assets=[x["id"] for x in manifest["assets"] if x["id"] not in completed])
        try: journal.append("acquisition_failed", **failure)
        except BaseException as secondary: failure["journal_error"] = type(secondary).__name__
        try: write_new(out / "FAILED.json", failure)
        except BaseException: pass
        raise


def verify_payload(path, row, deadline, clock=time.monotonic):
    path = local_path(path); before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size == row["expected_bytes"], "Payload size changed")
    sha = hashlib.sha256(); blob = hashlib.sha1(b"blob " + str(before.st_size).encode() + b"\0"); count = 0
    with path.open("rb") as stream:
        need(identity(before) == identity(os.fstat(stream.fileno())), "Payload changed before read")
        while True:
            need(clock() < deadline, "Deadline during payload verification"); block = stream.read(CHUNK_BYTES)
            if not block: break
            count += len(block); need(count <= row["expected_bytes"], "Payload grew"); sha.update(block); blob.update(block)
        after = os.fstat(stream.fileno())
    local_path(path)
    need(identity(before) == identity(after) == identity(path.stat()) and count == before.st_size, "Payload changed during read")
    need((sha.hexdigest() if row["digest"]["kind"] == "content" else blob.hexdigest()) == row["digest"]["value"], "Published digest differs")
    return sha.hexdigest()


def verify_completed(out, manifest, mp, code_sha256, deadline):
    raw, wp = capture(out / "WORKER-RECEIPT.json"); worker = strict_json(raw)
    need(worker["status"] == "completed" and worker["manifest"] == mp and worker["code_sha256"] == code_sha256
         and len(worker["files"]) == len(manifest["assets"]) and not (out / "FAILED.json").exists() and not (out / "STALLED.json").exists(), "Worker completion differs")
    copied, copied_proof = capture(out / "INPUT-MANIFEST.json")
    need((copied_proof["bytes"], copied_proof["sha256"]) == (mp["bytes"], mp["sha256"]) and strict_json(copied) == manifest, "Retained manifest differs")
    request = strict_json(capture(out / "REQUEST.json")[0])
    need(set(request) == {"manifest", "code_sha256", "code_pins", "started_utc", "automatic_retries", "range_resume", "hard_parent_supervision"}
         and request["manifest"] == mp and request["code_sha256"] == code_sha256 and request["code_pins"] == source_pins()
         and hashlib.sha256(canonical(request["code_pins"])).hexdigest() == code_sha256
         and type(request["automatic_retries"]) is int and request["automatic_retries"] == 0 and request["range_resume"] is False
         and request["hard_parent_supervision"] is worker["hard_parent_supervision"], "Retained request differs")
    events = primitives.verify_journal(out / "journal.jsonl")
    need(events[-1]["event"] == "acquisition_completed" and events[-1]["sha256"] == worker["journal_tail_sha256"], "Completion journal differs")
    need(events[0]["event"] == "acquisition_started" and events[0]["details"]["manifest"] == mp and
         not any(e["event"].endswith("failed") for e in events), "Journal contradicts completion")
    reserved = [e["details"] for e in events if e["event"] == "asset_reserved"]
    completed = [e["details"] for e in events if e["event"] == "asset_completed"]
    need(reserved == [dict(id=a["id"], expected_bytes=a["expected_bytes"]) for a in manifest["assets"]] and
         completed == [dict(id=a["id"], bytes=a["bytes"], sha256=a["sha256"]) for a in worker["files"]], "Journal asset claims differ")
    need(events[-1]["details"] == dict(assets=len(worker["files"]), received_body_bytes=worker["received_body_bytes"]), "Journal totals differ")
    for row, observed in zip(manifest["assets"], worker["files"]):
        need(observed["id"] == row["id"] and observed["destination"] == row["destination"] and type(observed["bytes"]) is int
             and observed["bytes"] == row["expected_bytes"] and observed["status"] == "completed" and observed["attempts"] == 1, "Ordered membership differs")
        for key in ("expected_bytes", "digest", "revision", "metadata_proof", "rights_reference"):
            need(observed[key] == row[key], "Asset source binding differs")
        started = strict_json(capture(out / "receipts" / (row["id"] + ".started.json"))[0])
        start_keys = {"id", "destination", "expected_bytes", "digest", "source_url", "revision", "metadata_proof", "rights_reference", "started_utc", "attempts", "redirects"}
        need(set(started) == start_keys and started["redirects"] == [] and
             all(started[k] == observed[k] for k in start_keys - {"redirects"}) and observed["source_url"] == public_url(row["url"]), "Started asset binding differs")
        need(strict_json(capture(out / "receipts" / (row["id"] + ".json"))[0]) == observed, "Asset receipt differs")
        path = local_path(out / "payloads" / row["destination"])
        need(observed["path"] == str(path) and verify_payload(path, row, deadline) == observed["sha256"], "Local payload hash differs")
    expected = {a["destination"] for a in manifest["assets"]}
    expected_dirs = {parent.as_posix() for name in expected for parent in Path(name).parents if parent.as_posix() != "."}
    payload_files, payload_dirs = set(), set()
    for path in (out / "payloads").rglob("*"):
        local_path(path)
        (payload_dirs if path.is_dir() else payload_files).add(path.relative_to(out / "payloads").as_posix())
    need(payload_files == expected and payload_dirs == expected_dirs and not any((out / "partials").iterdir()), "Unexpected payload/partial entries")
    expected_receipts = {a["id"] + suffix for a in manifest["assets"] for suffix in (".json", ".started.json")}
    need({p.name for p in (out / "receipts").iterdir()} == expected_receipts, "Unexpected asset receipt entries")
    for path in (out / "receipts").iterdir(): local_path(path); need(path.is_file(), "Receipt must be regular")
    top = {"REQUEST.json", "INPUT-MANIFEST.json", "journal.jsonl", "WORKER-RECEIPT.json", "payloads", "partials", "receipts"}
    need(type(worker["hard_parent_supervision"]) is bool, "Typed supervision scope required")
    if worker["hard_parent_supervision"]: top |= {"RESERVATION.json", "COMMAND.json", "PROCESS.json", "stdout.bin", "stderr.bin"}
    need({p.name for p in out.iterdir()} == top, "Unexpected attempt entries")
    need(worker["payload_bytes"] == worker["received_body_bytes"] == sum(a["expected_bytes"] for a in manifest["assets"]), "Byte totals differ")
    return worker, wp


def process_record(out, value):
    for name, raw in (("stdout.bin", value.stdout), ("stderr.bin", value.stderr)):
        with (out / name).open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    write_new(out / "PROCESS.json", dict(returncode=value.returncode, supervision=value.supervision))


def supervise(manifest_path, manifest_sha256, code_sha256, output):
    started = time.monotonic()
    raw, mp, manifest, pins, out = controls(manifest_path, manifest_sha256, code_sha256, output)
    containment = contain_process_tree()  # Hold until all owned-child cleanup has completed.
    out.mkdir(exist_ok=False); deadline = started + manifest["limits"]["total_seconds"]
    try:
        write_new(out / "RESERVATION.json", dict(manifest_sha256=manifest_sha256, code_sha256=code_sha256, nonce=secrets.token_hex(16), parent_pid=os.getpid(), utc=utc()))
        rp = capture(out / "RESERVATION.json")[1]
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", "--manifest", str(local_path(manifest_path)),
            "--manifest-sha256", manifest_sha256, "--code-sha256", code_sha256, "--output", str(out), "--reservation-sha256", rp["sha256"]]
        write_new(out / "COMMAND.json", dict(argv=command, automatic_retries=0))
        with DeadlineWatchdog(deadline + 10, out / "DEADLINE.json"):
            remaining = deadline-time.monotonic(); need(remaining > 0, "Preflight exhausted whole budget")
            limits = processes.ProcessLimits(remaining, 4 * CHUNK_BYTES)
            try: result = processes.supervise_command(command, limits=limits)
            except BaseException as error:
                observed = getattr(error, "tether_engine_result", getattr(error, "result", None))
                if observed is not None: process_record(out, observed)
                raise
            process_record(out, result); need(result.returncode == 0, "Acquisition worker failed")
            processes.validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
            worker, wp = verify_completed(out, manifest, mp, code_sha256, deadline)
            need(worker["hard_parent_supervision"] is True, "Unsupervised worker cannot finalize acquisition")
            need(time.monotonic() < deadline and source_pins() == pins and capture(manifest_path)[1] == mp, "Final deadline/source check failed")
            for row in manifest["assets"]: bound(row["metadata_proof"])
            write_new(out / "RECEIPT.json", dict(kind="alce_acquisition_receipt_v1", status="verified", worker_receipt=wp,
                manifest=mp, code_sha256=code_sha256, payload_bytes=worker["payload_bytes"], asset_count=len(worker["files"]),
                elapsed_seconds=time.monotonic()-started, process=capture(out / "PROCESS.json")[1], automatic_retries=0,
                range_resume=False, payload_hashes_rechecked=True, model_loaded=False, dependencies_installed=False))
            return capture(out / "RECEIPT.json")[1]
    except BaseException as error:
        try: write_new(out / "SUPERVISOR-FAILED.json", dict(status="failed", error_type=type(error).__name__, error=str(error)[:1000],
            elapsed_seconds=time.monotonic()-started, automatic_retries=0, utc=utc()))
        except BaseException: pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path); parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--code-sha256", required=True); parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reservation-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        need(args.reservation_sha256 is not None, "Worker requires parent reservation")
        _, _, manifest, _, out = controls(args.manifest, args.manifest_sha256, args.code_sha256, args.output, reserved=True)
        reservation(out, args.manifest_sha256, args.code_sha256, args.reservation_sha256)
        # Windows virtualenv launchers introduce an interpreter child. Ownership
        # is established by the reserving supervisor and held process tree,
        # not by assuming that the worker's immediate parent is that supervisor.
        with DeadlineWatchdog(time.monotonic()+manifest["limits"]["stall_seconds"], out / "STALLED.json") as watchdog:
            def progress(): watchdog.deadline = time.monotonic()+manifest["limits"]["stall_seconds"]
            acquire(args.manifest, args.manifest_sha256, args.code_sha256, out, progress=progress, reservation_sha256=args.reservation_sha256)
        print('{"status":"completed"}', flush=True)
    else:
        receipt = supervise(args.manifest, args.manifest_sha256, args.code_sha256, args.output)
        print(canonical(dict(status="verified", receipt=receipt)).decode(), flush=True)


if __name__ == "__main__": main()
