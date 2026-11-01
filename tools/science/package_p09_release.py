"""Package an externally pinned P09 READY bundle using its exact file allowlist.

No recursive source copy, acquisition or experiment execution occurs. ZIP_STORED
and fixed UTC DOS timestamps avoid compression/version and source-mtime drift.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MAX_MEMBER = 64 * 1024**2
MAX_TOTAL = 256 * 1024**2
QUALIFICATION = {
    "schema_version": 1, "method": "p09.public_release_qualification.v1",
    "status": "PASS_LOCAL_WINDOWS_RESEARCH_ARTIFACT", "role": "evaluation_only",
    "agent_visible": False, "scientific_validation": "not_established",
    "study_independence": "not_established", "publication_authorized": False,
    "owner_declarations": "deferred",
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _json(raw):
    def invalid(_):
        raise ValueError("Nonfinite JSON number")
    def number(text):
        value = float(text)
        need(math.isfinite(value), "Nonfinite JSON number")
        return value
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=number)


def _wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() + b"\n"


def _relative(name):
    need(type(name) is str and name and not name.startswith("/") and "\\" not in name and ":" not in name
         and not any(ord(char) < 32 or ord(char) == 127 for char in name), "Unsafe logical member name")
    for part in name.split("/"):
        need(part not in ("", ".", "..") and part == part.strip() and not part.endswith("."), "Unsafe logical member segment")
        need(part.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]},
             "Reserved logical member segment")
    need(len(name.encode()) <= 65535, "ZIP member name too long")


def _read(path, maximum=MAX_MEMBER):
    path = Path(path)
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and not path.is_symlink() and before.st_size <= maximum, "Input must be a bounded regular file")
    with path.open("rb") as stream:
        initial = os.fstat(stream.fileno())
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    need(len(raw) <= maximum and identity(before) == identity(initial) == identity(after) == identity(path.lstat())
         and len(raw) == before.st_size, "Input changed or exceeded its bound")
    return raw


def _source_path(root, relative):
    _relative(relative)
    path = root
    for part in relative.split("/"):
        path = path / part
        observed = path.lstat()
        need(not path.is_symlink() and not getattr(observed, "st_file_attributes", 0) & 0x400, "Linked bundle member is not allowed")
    need(path.resolve().is_relative_to(root), "Bundle member escapes root")
    return path


def _public(value):
    if type(value) is dict:
        for key, item in value.items():
            need(not re.fullmatch(r"(?i)(?:password|authorization|access_token|refresh_token|secret|client_secret|api[-_]key|private_key|aws_access_key_id|aws_secret_access_key|credentials?)", key), "Credential field in public metadata")
            _public(item)
    elif type(value) is list:
        for item in value:
            _public(item)
    elif type(value) is str:
        need(not value.startswith("/") and not re.search(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|/Users/|/home/|(?<![A-Za-z0-9_.:/])/(?:tmp|private|var|mnt|media|etc)/|(?<!\\)\\\\[^\\/\s]+[\\/]", value), "Private machine path in public metadata")
        need(not re.search(r"(?i)(?:[?&](?:token|signature|key|x-amz-credential|x-amz-signature)=|bearer\s+[A-Za-z0-9]|authorization\s*:\s*basic\s+\S|\b(?:[A-Za-z0-9_]*(?:api_key|access_token|secret_access_key)|password|client_secret|private_key|secret)\s*[:=]\s*\S|-----BEGIN [A-Z ]*PRIVATE KEY-----)", value),
             "Credential-like value in public metadata")


def _timestamp(value):
    need(type(value) is str and "T" in value, "Frozen protocol UTC timestamp is required")
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(instant.tzinfo is not None and instant.utcoffset().total_seconds() == 0 and 1980 <= instant.year <= 2107,
         "Frozen timestamp must be UTC and representable in ZIP")
    return (instant.year, instant.month, instant.day, instant.hour, instant.minute, instant.second // 2 * 2)


def _absent(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise FileExistsError("Fresh ZIP/staging path required: " + str(path))


def _output_paths(output):
    output = Path(output).absolute()
    need(output.suffix.lower() == ".zip", "Output must be a ZIP file")
    parent = output.parent.resolve(strict=True)
    need(any(parent.is_relative_to((ROOT / "data" / name).resolve()) for name in ("cache", "derived")),
         "Release ZIP stays in ignored workspace cache/derived output")
    output = parent / output.name
    partial = output.with_name(output.name + ".partial")
    _absent(output)
    _absent(partial)
    return output, partial


def _write_member(archive, name, raw, timestamp):
    member = zipfile.ZipInfo(name, timestamp)
    member.create_system = 3
    member.create_version = member.extract_version = 20
    member.external_attr = (stat.S_IFREG | 0o644) << 16
    member.compress_type = zipfile.ZIP_STORED
    archive.writestr(member, raw)


def _verify_zip(path, entries, timestamp):
    archive_raw = _read(path, MAX_TOTAL + 16 * 1024**2)
    # Fixed stored members, without extras/comments/ZIP64, have an exact size.
    # This also excludes unlisted bytes before or after the ZIP structures.
    need(len(archive_raw) == 22 + sum(76 + 2 * len(name.encode()) + len(raw) for name, raw in entries.items()), "ZIP physical byte closure differs")
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        need(names == sorted(entries) and len(names) == len(set(names)) == len({name.casefold() for name in names}), "ZIP member closure/order differs")
        need(not archive.comment, "Unexpected ZIP comment")
        for member in members:
            need(member.date_time == timestamp and member.create_system == 3 and member.create_version == member.extract_version == 20
                 and member.external_attr == (stat.S_IFREG | 0o644) << 16 and not member.extra and not member.comment
                 and member.compress_type == zipfile.ZIP_STORED and member.file_size == member.compress_size == len(entries[member.filename]),
                 "ZIP metadata differs")
            raw = archive.read(member)
            need(raw == entries[member.filename], "ZIP readback differs")
        need(archive.testzip() is None, "ZIP CRC validation failed")
    return archive_raw


def _publish(partial, output):
    if os.name == "nt":
        # Windows rename fails if the destination exists; it never replaces it.
        os.rename(partial, output)
        return None
    os.link(partial, output)
    try:
        partial.unlink()
    except OSError:
        return str(partial)
    return None


def package(bundle_root, protocol_sha256, readme, qualification, output):
    """Build, read back, and exclusively publish one fixed-content release ZIP."""
    output, partial = _output_paths(output)
    need(type(protocol_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", protocol_sha256), "External protocol byte SHA256 required")
    root = Path(bundle_root).absolute()
    need(root == root.resolve(strict=True) and root.is_dir(), "Explicit unaliased bundle root required")
    need(not output.is_relative_to(root) and not partial.is_relative_to(root), "ZIP/staging must stay outside the frozen bundle")
    protocol_raw = _read(_source_path(root, "protocol.json"), 8 * 1024**2)
    need(sha(protocol_raw) == protocol_sha256, "External protocol byte hash differs")
    protocol = _json(protocol_raw)
    need(type(protocol) is dict and type(protocol.get("schema_version")) is int and protocol["schema_version"] == 1
         and protocol.get("method") == "p09.public_reconstruction_protocol.v1" and protocol.get("status") == "READY"
         and protocol.get("actual_reconstruction_authorized") is True, "Authorized frozen READY protocol required")
    timestamp = _timestamp(protocol.get("frozen_at_utc"))
    files = protocol.get("files")
    need(type(files) is dict and bool(files), "Explicit protocol file allowlist required")
    names = list(files)
    for name in names:
        _relative(name)
        need(name != "protocol.json", "Protocol cannot list itself")
        proof = files[name]
        need(type(proof) is dict and set(proof) == {"path", "sha256", "bytes", "role"} and proof["path"] == name
             and type(proof["bytes"]) is int and 0 <= proof["bytes"] <= MAX_MEMBER
             and type(proof["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", proof["sha256"])
             and type(proof["role"]) is str and bool(proof["role"]), "Protocol file descriptor differs")
    need(len(names) == len({name.casefold() for name in names}), "Aliased protocol file names")
    need(sum(files[name]["bytes"] for name in names) <= MAX_TOTAL, "Protocol payload total exceeds package bound")
    readme_raw, qualification_raw = _read(readme, 4 * 1024**2), _read(qualification, 4 * 1024**2)
    readme_text, qualified = readme_raw.decode("utf-8"), _json(qualification_raw)
    need(bool(readme_text.strip()) and "\x00" not in readme_text, "Public README must be nonempty UTF8 text")
    _public(readme_text)
    need(type(qualified) is dict and all(key in qualified and type(qualified[key]) is type(value) and qualified[key] == value for key, value in QUALIFICATION.items())
         and qualified.get("protocol_sha256") == protocol_sha256, "Public qualification contract or protocol binding differs")
    _public(qualified)
    entries = {"artifact/protocol.json": protocol_raw, "README.md": readme_raw, "qualification.json": qualification_raw}
    records = {"artifact/protocol.json": {"sha256": protocol_sha256, "bytes": len(protocol_raw), "role": "root_protocol_authority"},
        "README.md": {"sha256": sha(readme_raw), "bytes": len(readme_raw), "role": "public_release_instructions"},
        "qualification.json": {"sha256": sha(qualification_raw), "bytes": len(qualification_raw), "role": "evaluation_only"}}
    for name in sorted(files):
        raw = _read(_source_path(root, name))
        need(sha(raw) == files[name]["sha256"] and len(raw) == files[name]["bytes"], "Frozen bundle member differs: " + name)
        logical = "artifact/" + name
        entries[logical] = raw
        records[logical] = {key: files[name][key] for key in ("sha256", "bytes", "role")}
    manifest = {"schema_version": 1, "method": "p09.release_package_manifest.v1", "role": "evaluation_only", "agent_visible": False,
        "protocol_sha256": protocol_sha256, "public_qualification_sha256": sha(qualification_raw), "qualification_status": qualified["status"],
        "scientific_validation": "not_established", "publication_authorized": False, "frozen_at_utc": protocol["frozen_at_utc"],
        "zip_timestamp_policy": "UTC DOS floor to two-second precision; microseconds discarded", "compression": "ZIP_STORED",
        "files": records}
    entries["RELEASE-MANIFEST.json"] = _wire(manifest)
    try:
        with partial.open("xb") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
                for name in sorted(entries):
                    _write_member(archive, name, entries[name], timestamp)
            stream.flush()
            os.fsync(stream.fileno())
        archive_raw = _verify_zip(partial, entries, timestamp)
        # Windows rename and POSIX hard-link creation both fail on an existing
        # destination. No replace operation is used, even under a reservation race.
        retained_staging = _publish(partial, output)
        return {"status": "PACKAGED_AND_READBACK_VERIFIED", "archive_sha256": sha(archive_raw), "archive_bytes": len(archive_raw),
            "members": len(entries), "protocol_sha256": protocol_sha256, "manifest_sha256": sha(entries["RELEASE-MANIFEST.json"]),
            "output": str(output), "retained_staging_path": retained_staging}
    except BaseException as error:
        if partial.exists():
            error.add_note("Partial ZIP retained for inspection: " + str(partial))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(package(args.bundle_root, args.protocol_sha256, args.readme, args.qualification, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
