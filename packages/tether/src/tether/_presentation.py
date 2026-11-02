"""A separately sealed TETHER presentation around unchanged engine artifacts.

This local wrapper is trusted code, not an OS sandbox. Its receipt needs an
independently retained hash to detect replacement of an entire output tree.
"""
from __future__ import annotations

import hashlib
from importlib import metadata
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

import asof
from asof.artifacts import verify_run
from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import (ContractError, MAX_LEDGER_JSON_BYTES, MAX_NORMALIZED_JSON_BYTES,
                        canonical, encode, fingerprint, parse_json)
from asof.study.proofs import capture_file
from asof.study.stable_read import read_file

from . import __version__
from ._process import (EngineResult, EngineInterrupted, ProcessLimits, supervise_command,
                       validate_success_report, CLEANUP_SECONDS)

MANIFEST = "tether-manifest.json"
RECEIPT = "tether-receipt.json"
FAILURE = "tether-failure.json"
JOURNAL = "attempt/journal.jsonl"
METHOD = "tether.engine_presentation.v1"
MAX_METADATA_BYTES = MAX_NORMALIZED_JSON_BYTES
MAX_DOSSIER_BYTES = MAX_LEDGER_JSON_BYTES
READ_SECONDS = 300


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _no_links(path):
    path = Path(path).absolute()
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "TETHER path contains a symlink/reparse point")
    return path


def _relative(value):
    need(type(value) is str and value and "\\" not in value and ":" not in value
         and all(p not in ("", ".", "..") for p in value.split("/")), "Unsafe TETHER artifact path")
    return value


def _read(path, *, max_bytes=MAX_METADATA_BYTES):
    # The frozen core helper rejects oversized/nonregular inputs before open,
    # bounds every chunk and compares path/descriptor identities around the read.
    return read_file(Path(path), time.monotonic() + READ_SECONDS, max_bytes)


def _json(path):
    value = parse_json(_read(path))
    need(type(value) is dict, "TETHER metadata must be an object")
    return value


def _save(path, payload):
    maximum = MAX_DOSSIER_BYTES if Path(path).name == "dossier.md" else MAX_METADATA_BYTES
    need(type(payload) is bytes and len(payload) <= maximum, "TETHER product exceeds its byte bound")
    publish_bytes(Path(path), payload)
    need(_read(path, max_bytes=maximum) == payload, "TETHER publication readback differs")


def _journal_events(payload, *, allow_incomplete_tail=False):
    """Decode one already bounded/stable journal snapshot, without reopening it."""
    events, previous = [], None
    lines = payload.splitlines()
    for index, line in enumerate(lines):
        if allow_incomplete_tail and index == len(lines) - 1 and not payload.endswith(b"\n"):
            break
        event = parse_json(line)
        need(type(event) is dict and "sha256" in event, "Invalid TETHER journal event")
        expected = event.pop("sha256")
        need(event.get("sequence") == len(events) and event.get("previous_sha256") == previous
             and fingerprint(event) == expected, "TETHER journal hash-chain failure")
        event["sha256"] = expected
        events.append(event)
        previous = expected
    need(events, "Empty TETHER execution trace")
    return events


def _inspect_engine(output):
    """Preserve legacy run accounting from a single bounded journal snapshot."""
    events = _journal_events(_read(output / "journal.jsonl"), allow_incomplete_tail=True)
    attempts = {}
    measured = dict(input_tokens=0, output_tokens=0, cost_usd=0)
    estimated = dict(input_tokens=0, output_tokens=0, cost_usd=0)
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
    return dict(schema_version=2, last_event=events[-1]["event"], durable_events=len(events),
                unresolved_attempts=tuple(attempts), measured_usage=measured,
                estimated_upper_usage=estimated, receipt_present=(output / "receipt.json").is_file(),
                recovery_action="inspect only; never automatically repeat unresolved calls")


def _descriptor(root, relative):
    relative = _relative(relative)
    proof = capture_file(root / relative, relative)
    return dict(path=relative, sha256=proof["sha256"], bytes=proof["bytes"])


def _inventory(root):
    _no_links(root)
    files, directories = set(), set()
    for directory, children, names in os.walk(root, followlinks=False):
        for name in children:
            member = Path(directory) / name
            _no_links(member)
            directories.add(member.relative_to(root).as_posix())
        for name in names:
            member = Path(directory) / name
            _no_links(member)
            need(member.is_file(), "Non-file TETHER artifact")
            files.add(_relative(member.relative_to(root).as_posix()))
    return files, directories


def _package_root():
    return Path(__file__).resolve().parent


def code_proof():
    root = _package_root()
    files = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    need(files and (root / "__init__.py") in files, "TETHER package code is missing")
    proof = {p.relative_to(root).as_posix(): _descriptor(root, p.relative_to(root).as_posix()) for p in files}
    need(len({p.casefold() for p in proof}) == len(proof), "TETHER code path alias")
    need(proof == {p.relative_to(root).as_posix(): _descriptor(root, p.relative_to(root).as_posix()) for p in files},
         "TETHER code changed during capture")
    need(set(proof) == {p.relative_to(root).as_posix() for p in root.rglob("*.py") if "__pycache__" not in p.parts},
         "TETHER code inventory changed")
    versions = {}
    for name in ("tether-target-agents", "asof-target-agents"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    need(asof.__version__ == "0.3.11" and __version__ == "0.4.2", "Unsupported TETHER/core version")
    need(versions["asof-target-agents"] in (None, "0.3.11")
         and versions["tether-target-agents"] in (None, "0.4.2"), "Installed distribution version differs")
    return dict(schema_version=1, method="tether.launcher_code.v1", facade_version=__version__,
                core_version=asof.__version__, installed_distributions=versions, code=proof)


def project_dossier(payload):
    prefix = b"# AsOf dossier:"
    need(type(payload) is bytes and payload.startswith(prefix), "Unexpected engine dossier header")
    return b"# TETHER dossier:" + payload[len(prefix):]


class EngineFailure(ContractError):
    def __init__(self, returncode):
        super().__init__(f"engine exited {returncode}; inspect this attempt, never automatically redispatch")
        self.exit_code = 130 if returncode == 130 else 3 if returncode == 3 else 2


def invoke_engine(argv, *, limits=ProcessLimits()):
    return supervise_command([sys.executable, "-I", "-m", "asof", *argv], limits=limits)


def preflight_run_journals(output, *, verify=False):
    """Apply the new wrapper's read bound before a legacy command can reread."""
    output = Path(output)
    for name in (("journal.jsonl", "trace.jsonl") if verify else ("journal.jsonl",)):
        path = output / name
        if path.exists():
            _read(path)


def _core_check(root, receipt_hash):
    result = verify_engine(root / "engine", receipt_hash, True)
    need(result.get("code_matches_current") is True and result.get("semantic_consistency") == "verified"
         and result.get("source_binding") == "current_originals", "Engine source/code verification is incomplete")
    need(_json(root / "engine/run.json").get("status") == "completed", "Engine run did not complete")
    return result


def verify_engine(output, receipt_hash=None, verify_sources=True):
    """TETHER-qualified v2 verification; v1 retains its declared legacy scope."""
    output = Path(output)
    preflight_run_journals(output, verify=True)
    result = verify_run(output, receipt_hash, verify_sources)
    if _json(output / "receipt.json")["schema_version"] == 2:
        from ._semantics import check_engine_semantics
        result["tether_semantics"] = check_engine_semantics(
            output, _json, _read, _journal_events, MAX_DOSSIER_BYTES)
    return result


def _engine_args(argv, output):
    result, index = [], 0
    while index < len(argv):
        token = argv[index]
        if token in ("--output", "--process-timeout-seconds", "--process-output-bytes"):
            index += 2
        elif token.startswith(("--output=", "--process-timeout-seconds=", "--process-output-bytes=")):
            index += 1
        else:
            result.append(token)
            index += 1
    return result + ["--output", str(output)]


def _retain_streams(root, result):
    for name, payload in (("engine-stdout.txt", result.stdout), ("engine-stderr.txt", result.stderr)):
        _save(root / name, payload)


def create_outer(output, argv, *, engine=None, limits=ProcessLimits()):
    """Reserve a fresh leaf, run once, close journal, then publish the final receipt."""
    limits.validate()
    output = Path(output).absolute()
    _no_links(output.parent)
    # Exclusive ownership precedes every write, including failure records.
    output.mkdir(exist_ok=False)
    journal, stage, result = None, "reservation", None
    try:
        journal = RunJournal(output / "attempt")
        proof = code_proof()
        journal.append("tether_prepared", command=argv[0], launcher_proof_sha256=digest(canonical(proof)),
                       process_limits=limits.payload())
        stage = "engine_dispatch"
        journal.append("engine_dispatch", argv_sha256=digest(canonical(argv)), output="engine",
                       process_limits=limits.payload())
        result = (invoke_engine(_engine_args(argv, output / "engine"), limits=limits) if engine is None
                  else engine(_engine_args(argv, output / "engine")))
        _retain_streams(output, result)
        journal.append("engine_returned", returncode=result.returncode, supervision=result.supervision)
        if result.returncode == 130:
            raise EngineInterrupted(result)
        if result.returncode != 0:
            raise EngineFailure(result.returncode)
        stage = "source_verification"
        engine_receipt = digest(_read(output / "engine/receipt.json"))
        _core_check(output, engine_receipt)
        validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        stage = "presentation"
        _save(output / "dossier.md", project_dossier(_read(output / "engine/dossier.md", max_bytes=MAX_DOSSIER_BYTES)))
        need(canonical(code_proof()) == canonical(proof), "TETHER launcher code changed during execution")
        file_names, _ = _inventory(output)
        artifacts = {name: _descriptor(output, name) for name in sorted(file_names - {JOURNAL})}
        manifest = dict(schema_version=1, method=METHOD, brand="TETHER", status="completed",
                        role="evaluation_only", agent_visible=False, scientific_validation="not_established",
                        command=argv[0], invocation_sha256=digest(canonical(argv)),
                        process_limits=limits.payload(), supervision=result.supervision,
                        engine=dict(path="engine", receipt_sha256=engine_receipt),
                        projection=dict(source="engine/dossier.md", target="dossier.md", transform="exact_first_header_v1"),
                        launcher=proof, artifacts=artifacts)
        _save(output / MANIFEST, canonical(manifest) + b"\n")
        stage = "finalization"
        manifest_hash = digest(_read(output / MANIFEST))
        journal.append("tether_completed", manifest_sha256=manifest_hash, engine_receipt_sha256=engine_receipt)
        journal.close()
        receipt = dict(schema_version=1, method=METHOD, brand="TETHER", status="completed",
                       role="evaluation_only", agent_visible=False, scientific_validation="not_established",
                       manifest_sha256=manifest_hash, journal_sha256=digest(_read(output / JOURNAL)),
                       engine_receipt_sha256=engine_receipt)
        _save(output / RECEIPT, canonical(receipt) + b"\n")
        return dict(brand="TETHER", status="completed", output=str(output),
                    receipt_sha256=digest(_read(output / RECEIPT)), engine_receipt_sha256=engine_receipt,
                    scientific_validation="not_established")
    except BaseException as error:
        # A failed publication/readback must not leave a success receipt as the
        # apparent terminal product. Preserve its bytes under a failed name.
        if (output / RECEIPT).exists():
            try:
                os.rename(output / RECEIPT, output / "tether-receipt.failed.json")
            except OSError:
                pass
        captured = getattr(error, "tether_engine_result", error.result if isinstance(error, EngineInterrupted) else None)
        failures = list(getattr(error, "tether_cleanup_errors", ()))
        if captured is not None:
            result = captured
            try:
                for name, payload in (("engine-stdout.txt", result.stdout), ("engine-stderr.txt", result.stderr)):
                    if not (output / name).exists():
                        _save(output / name, payload)
            except BaseException as problem:
                failures.append(dict(operation="retain_engine_streams", error_class=type(problem).__name__))
        partial_streams = []
        for index, (label, stdout, stderr) in enumerate(getattr(error, "tether_partial_captures", ())):
            for stream, payload in (("stdout", stdout), ("stderr", stderr)):
                if payload:
                    relative = f"engine-partial-{index:02d}-{stream}.txt"
                    try:
                        _save(output / relative, payload)
                        partial_streams.append(dict(label=label, **_descriptor(output, relative)))
                    except BaseException as problem:
                        failures.append(dict(operation="retain_partial_stream", error_class=type(problem).__name__))
        if journal:
            try:
                journal.fail(error, stage)
            except BaseException as problem:
                failures.append(dict(operation="journal_failure_append", error_class=type(problem).__name__))
            try:
                journal.close()
            except BaseException as problem:
                failures.append(dict(operation="journal_close", error_class=type(problem).__name__))
        failure = dict(schema_version=1, method=METHOD, brand="TETHER", role="evaluation_only", agent_visible=False,
                       status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed", stage=stage,
                       error_class=type(error).__name__, engine_returncode=result.returncode if result else None,
                       process_limits=limits.payload(), supervision=result.supervision if result else None,
                       cleanup_errors=failures, partial_streams=partial_streams,
                       engine_process_reaped=getattr(error, "tether_process_reaped", None),
                       scientific_validation="not_established",
                       recovery_action="inspect only; never automatically repeat this attempt")
        try:
            _save(output / FAILURE, canonical(failure) + b"\n")
        except BaseException as problem:
            # Any valid success receipt is still rejected if this attempt did not
            # return success; a journal failure/terminal mismatch also rejects it.
            error.add_note("TETHER failure metadata could not be published: " + type(problem).__name__)
            raise error from problem
        raise


def _envelope(doc, keys):
    need(type(doc) is dict and set(doc) == set(keys), "TETHER envelope fields differ")
    need(type(doc["schema_version"]) is int and doc["schema_version"] == 1 and doc["method"] == METHOD
         and doc["brand"] == "TETHER" and doc["status"] == "completed" and doc["role"] == "evaluation_only"
         and doc["agent_visible"] is False and doc["scientific_validation"] == "not_established", "Invalid TETHER envelope")


def verify_outer(output, expected_receipt_sha256=None):
    output = _no_links(Path(output).absolute())
    need(not (output / FAILURE).exists(), "TETHER attempt has a retained failure")
    raw = _read(output / RECEIPT)
    if expected_receipt_sha256 is not None:
        need(type(expected_receipt_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_receipt_sha256)
             and digest(raw) == expected_receipt_sha256, "TETHER external receipt hash differs")
    receipt = parse_json(raw)
    common = {"schema_version", "method", "brand", "status", "role", "agent_visible", "scientific_validation"}
    _envelope(receipt, common | {"manifest_sha256", "journal_sha256", "engine_receipt_sha256"})
    manifest_raw = _read(output / MANIFEST)
    need(digest(manifest_raw) == receipt["manifest_sha256"], "TETHER manifest hash differs")
    manifest = parse_json(manifest_raw)
    _envelope(manifest, common | {"command", "invocation_sha256", "engine", "projection", "launcher", "artifacts",
                                  "process_limits", "supervision"})
    need(type(manifest["process_limits"]) is dict and set(manifest["process_limits"]) ==
         {"timeout_seconds", "max_output_bytes"}, "TETHER process limits differ")
    limits = ProcessLimits(**manifest["process_limits"])
    limits.validate()
    need(manifest["command"] in ("demo", "run") and manifest["engine"] == dict(path="engine", receipt_sha256=receipt["engine_receipt_sha256"]),
         "TETHER engine binding differs")
    need(canonical(manifest["launcher"]) == canonical(code_proof()), "TETHER current launcher code/version differs")
    need(type(manifest["invocation_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", manifest["invocation_sha256"]),
         "TETHER invocation binding differs")
    need(manifest["projection"] == dict(source="engine/dossier.md", target="dossier.md", transform="exact_first_header_v1"),
         "TETHER projection declaration differs")
    need(type(manifest["artifacts"]) is dict, "TETHER artifact inventory is invalid")
    expected_files = set(manifest["artifacts"]) | {MANIFEST, RECEIPT, JOURNAL}
    actual_files, actual_directories = _inventory(output)
    need(actual_files == expected_files, "TETHER whole artifact inventory differs")
    expected_directories = {p.as_posix() for name in expected_files for p in Path(name).parents if p.as_posix() != "."}
    need(actual_directories == expected_directories, "TETHER directory inventory differs")
    for name, descriptor in manifest["artifacts"].items():
        need(canonical(descriptor) == canonical(_descriptor(output, name)), "TETHER artifact hash/bytes/path differs: " + name)
    journal_raw = _read(output / JOURNAL)
    need(digest(journal_raw) == receipt["journal_sha256"], "TETHER journal hash differs")
    events = _journal_events(journal_raw)
    need([e["event"] for e in events] == ["run_reserved", "tether_prepared", "engine_dispatch", "engine_returned", "tether_completed"]
         and all(type(e["sequence"]) is int for e in events)
         and events[-1]["details"] == dict(manifest_sha256=receipt["manifest_sha256"], engine_receipt_sha256=receipt["engine_receipt_sha256"]),
         "TETHER journal terminal binding differs")
    need(canonical(events[1]["details"]) == canonical(dict(command=manifest["command"],
            launcher_proof_sha256=digest(canonical(manifest["launcher"])), process_limits=limits.payload()))
         and canonical(events[2]["details"]) == canonical(dict(argv_sha256=manifest["invocation_sha256"],
            output="engine", process_limits=limits.payload()))
         and canonical(events[3]["details"]) == canonical(dict(returncode=0,
            supervision=manifest["supervision"])), "TETHER journal dispatch/proof binding differs")
    validate_success_report(manifest["supervision"], limits,
                            len(_read(output / "engine-stdout.txt")), len(_read(output / "engine-stderr.txt")))
    need(not any(e["event"] in ("run_failed", "run_interrupted") for e in events), "TETHER failure journal cannot qualify")
    need(_read(output / "dossier.md", max_bytes=MAX_DOSSIER_BYTES)
         == project_dossier(_read(output / "engine/dossier.md", max_bytes=MAX_DOSSIER_BYTES)), "TETHER dossier projection differs")
    engine_result = _core_check(output, receipt["engine_receipt_sha256"])
    return dict(brand="TETHER", status="integrity_verified", receipt_sha256=digest(raw),
                external_anchor_checked=expected_receipt_sha256 is not None, launcher_code_verified=True,
                presentation_projection="exact_first_header_v1", engine=engine_result,
                scientific_validation="not_established")


def inspect_outer(output):
    output = _no_links(Path(output).absolute())
    journal_error = None
    try:
        events = _journal_events(_read(output / JOURNAL), allow_incomplete_tail=True) if (output / JOURNAL).is_file() else ()
    except (OSError, ContractError) as error:
        events, journal_error = (), type(error).__name__
    result = dict(brand="TETHER", kind="outer_attempt", durable_events=len(events),
                  last_event=events[-1]["event"] if events else None,
                  journal_inspection_error=journal_error,
                  receipt_present=(output / RECEIPT).is_file(), failure=_json(output / FAILURE) if (output / FAILURE).is_file() else None,
                  recovery_action="inspect only; never automatically repeat this attempt")
    if (output / "engine/journal.jsonl").is_file():
        try:
            result["engine"] = _inspect_engine(output / "engine")
        except Exception as error:
            result["engine"] = dict(inspection_error=type(error).__name__)
    return encode(result)
