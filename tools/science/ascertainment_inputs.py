"""Bounded evaluator-only AACT ZIP qualification; no restore or clinical queries."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import zipfile
import zlib

from asof.journal import RunJournal
from asof.serde import ContractError, sha256_file

DEFAULT_LIMITS = {"archive_bytes": 4 * 1024**3, "expanded_bytes": 8 * 1024**3,
    "member_bytes": 6 * 1024**3, "members": 32, "expansion_ratio": 200,
    "toc_bytes": 64 * 1024**2, "toc_timeout_seconds": 120}
BLOCK = 8 * 1024**2


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write("\n")
        stream.flush(); os.fsync(stream.fileno())


def identity(path):
    value = Path(path).stat()
    return {"bytes": value.st_size, "mtime_ns": value.st_mtime_ns,
            "device": value.st_dev, "inode": value.st_ino}


def safe_members(infos, limits):
    if not infos or len(infos) > limits["members"]:
        raise ContractError("ZIP member count exceeds configured bound")
    names = [item.filename for item in infos]
    if len(set(name.casefold() for name in names)) != len(names):
        raise ContractError("Duplicate or case-colliding ZIP member")
    if names.count("postgres.dmp") != 1:
        raise ContractError("Exactly one postgres.dmp required")
    expanded = 0
    for item in infos:
        mode = item.external_attr >> 16
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+", item.filename) or item.filename in (".", "..")
                or item.is_dir() or stat.S_ISLNK(mode)
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
            raise ContractError("Unsafe ZIP member; only flat regular named files permitted")
        if item.flag_bits & 1 or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ContractError("Encrypted or unsupported ZIP member")
        if item.file_size < 0 or item.file_size > limits["member_bytes"]:
            raise ContractError("ZIP member exceeds expansion bound")
        if item.file_size > max(1, item.compress_size) * limits["expansion_ratio"]:
            raise ContractError("ZIP member expansion ratio exceeds bound")
        expanded += item.file_size
    if expanded > limits["expanded_bytes"]:
        raise ContractError("ZIP total expansion exceeds configured bound")
    return expanded


def actual_date(toc, requested_date):
    date.fromisoformat(requested_date)
    matches = re.findall(r"^; Archive created at (\d{4}-\d{2}-\d{2}) ([0-9:]+)\s*$", toc, re.M)
    if len(matches) != 1:
        raise ContractError("Exactly one dump creation date required in pg_restore TOC")
    actual, clock = matches[0]
    datetime.fromisoformat(actual + "T" + clock)
    if actual != requested_date:
        raise ContractError("Actual dump date differs from requested date: " + actual)
    return actual


def run_toc(executable, dump, timeout, maximum):
    """Run only pg_restore --list; retain bounded output and terminate on overflow."""
    process = subprocess.Popen([str(executable), "--list", str(dump)], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(process.stdout.read, maximum + 1)
    try:
        payload = future.result(timeout=timeout)
        if len(payload) > maximum:
            raise ContractError("TOC output exceeds configured bound")
        returncode = process.wait(timeout=max(1, timeout))
        return {"returncode": returncode, "output": payload}
    except BaseException:
        process.kill(); process.wait()
        raise
    finally:
        process.stdout.close(); pool.shutdown(wait=True)


def qualify(archive, output, pg_restore, *, requested_date="2026-04-01",
            expected_archive_bytes=None, expected_archive_sha256=None, limits=None, runner=None):
    """Reserve output once, preserve all originals, retain partials/failures on error."""
    archive, output, executable = Path(archive).resolve(), Path(output).resolve(), Path(pg_restore).resolve()
    journal = RunJournal(output, kind="build")
    stage, started = "input_identity", time.monotonic()
    active_limits = dict(DEFAULT_LIMITS)
    try:
        if limits:
            if set(limits) - set(active_limits):
                raise ContractError("Unknown qualification bound")
            active_limits.update(limits)
        if any(type(value) is not int or value <= 0 for value in active_limits.values()):
            raise ContractError("Qualification bounds must be positive integers")
        date.fromisoformat(requested_date)
        initial = identity(archive)
        if not archive.is_file() or archive.is_symlink() or initial["bytes"] > active_limits["archive_bytes"]:
            raise ContractError("Archive outside file/size bounds")
        if expected_archive_bytes is not None and initial["bytes"] != expected_archive_bytes:
            raise ContractError("Supplied archive byte count differs")
        code = Path(__file__).read_bytes()
        with (output / "executed-code.py").open("xb") as stream:
            stream.write(code)
        code_proof = {"path": str(output / "executed-code.py"),
            "sha256": hashlib.sha256(code).hexdigest(), "bytes": len(code)}
        executable_hash = sha256_file(executable)
        executable_proof = {"path": str(executable), "sha256": executable_hash, "bytes": executable.stat().st_size}
        save(output / "plan.json", {"archive": str(archive), "requested_date": requested_date,
            "expected_archive_bytes": expected_archive_bytes, "expected_archive_sha256": expected_archive_sha256,
            "limits": active_limits, "pg_restore": executable_proof, "role": "evaluation_only",
            "database_restore_allowed": False, "clinical_queries_allowed": False})
        stage = "archive_sha256"
        journal.append("build_stage", stage=stage)
        digest = sha256_file(archive)
        if expected_archive_sha256 is not None and digest != expected_archive_sha256:
            raise ContractError("Supplied archive hash differs")
        if identity(archive) != initial:
            raise ContractError("Archive changed during initial hashing")
        print(json.dumps({"stage": "archive_hashed", "sha256": digest, "bytes": initial["bytes"]}), flush=True)
        stage = "bounded_zip_member_integrity"
        journal.append("build_stage", stage=stage, archive_sha256=digest)
        extracted = output / "extracted"; extracted.mkdir()
        members = []
        with zipfile.ZipFile(archive) as source_zip:
            infos = source_zip.infolist(); expanded = safe_members(infos, active_limits)
            if shutil.disk_usage(output).free < expanded + 128 * 1024**2:
                raise ContractError("Insufficient free space for bounded extraction")
            for info in infos:
                target = extracted / info.filename
                hasher, count, crc = hashlib.sha256(), 0, 0
                with source_zip.open(info) as source, target.open("xb") as destination:
                    while block := source.read(BLOCK):
                        count += len(block)
                        if count > info.file_size or count > active_limits["member_bytes"]:
                            raise ContractError("Actual member expansion exceeds declared bound")
                        destination.write(block); hasher.update(block); crc = zlib.crc32(block, crc)
                    destination.flush(); os.fsync(destination.fileno())
                if count != info.file_size or crc != info.CRC:
                    raise ContractError("ZIP member size or CRC mismatch")
                members.append({"name": info.filename, "path": str(target), "sha256": hasher.hexdigest(),
                    "bytes": count, "crc32": crc, "crc_check": "passed_full_read",
                    "zip_timestamp": list(info.date_time)})
                journal.append("build_progress", member=info.filename, bytes=count, sha256=hasher.hexdigest())
        stage = "dump_toc"
        journal.append("build_stage", stage=stage)
        result = (runner or run_toc)(executable, extracted / "postgres.dmp",
                                     active_limits["toc_timeout_seconds"], active_limits["toc_bytes"])
        toc_bytes = result["output"]
        if not isinstance(toc_bytes, bytes) or len(toc_bytes) > active_limits["toc_bytes"]:
            raise ContractError("TOC output outside byte bound")
        with (output / "dump-toc.txt").open("xb") as stream:
            stream.write(toc_bytes)
        if result["returncode"] != 0:
            raise ContractError("pg_restore --list failed; retained TOC output")
        actual = actual_date(toc_bytes.decode("utf-8"), requested_date)
        toc_proof = {"path": str(output / "dump-toc.txt"), "sha256": hashlib.sha256(toc_bytes).hexdigest(),
            "bytes": len(toc_bytes), "command": [str(executable), "--list", str(extracted / "postgres.dmp")],
            "returncode": 0}
        print(json.dumps({"stage": "toc_date_checked", "actual_dump_date": actual, "archive_sha256": digest}), flush=True)
        stage = "final_identity_and_hash_closure"
        journal.append("build_stage", stage=stage)
        if identity(archive) != initial or sha256_file(archive) != digest or identity(archive) != initial:
            raise ContractError("Archive changed during qualification")
        for proof in members + [code_proof, executable_proof, toc_proof]:
            if sha256_file(Path(proof["path"])) != proof["sha256"] or Path(proof["path"]).stat().st_size != proof["bytes"]:
                raise ContractError("Qualified ancestor changed during qualification")
        report = {"schema_version": 1, "status": "archive_qualification_passed", "role": "evaluation_only",
            "requested_date": requested_date, "actual_dump_date": actual,
            "archive": {"path": str(archive), "sha256": digest, "bytes": initial["bytes"]},
            "archive_identity_before": initial, "archive_identity_after": identity(archive),
            "members": members, "toc": toc_proof, "executed_code": code_proof, "pg_restore": executable_proof,
            "proofs": members + [toc_proof, code_proof, executable_proof],
            "date_basis": "dump_creation_date_timezone_unknown_not_exact_public_availability",
            "dump_creation_timezone": None, "exact_first_public_availability": None,
            "source_publication_date": None, "retrieved_at": None,
            "qualified_at_utc": datetime.now(timezone.utc).isoformat(),
            "database_restored": False, "clinical_rows_queried": 0, "provider_spend_usd": 0,
            "limits": active_limits, "expanded_bytes": expanded,
            "elapsed_seconds": time.monotonic() - started,
            "limitations": ["Technical archive qualification does not establish exact dataset public availability or registry completeness.",
                "Ancillary files are retained for integrity only and are not qualified scientific evidence."]}
        save(output / "qualification.json", report)
        journal.append("build_completed", report_sha256=sha256_file(output / "qualification.json"))
        return report
    except BaseException as error:
        journal.fail(error, stage)
        save(output / "failure.json", {"status": "failed", "stage": stage, "error_class": type(error).__name__,
            "error": str(error), "recovery": "Inspect preserved output; retry only in a fresh output directory"})
        raise
    finally:
        journal.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--pg-restore", required=True); parser.add_argument("--requested-date", default="2026-04-01")
    parser.add_argument("--expected-bytes", type=int); parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = qualify(args.archive, args.output, args.pg_restore, requested_date=args.requested_date,
        expected_archive_bytes=args.expected_bytes, expected_archive_sha256=args.expected_sha256)
    print(json.dumps({"status": result["status"], "actual_dump_date": result["actual_dump_date"],
                      "archive_sha256": result["archive"]["sha256"]}), flush=True)


if __name__ == "__main__":
    main()
