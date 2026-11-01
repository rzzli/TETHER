"""Exact external protocol authority and installed-code checks, version one."""
from __future__ import annotations

import hashlib
from importlib import metadata
from pathlib import Path
import platform
import re
import sys

import asof
import asof_p05_replay
from asof.serde import ContractError, encode, parse_json
from asof.study.stable_read import checked_path, read_file, stable_files


def need(value, message):
    if not value:
        raise ContractError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_descriptor(root, descriptor, deadline, *, maximum=64 * 1024**2):
    need(isinstance(descriptor, dict) and all(k in descriptor for k in ("path", "sha256", "bytes")),
         "Explicit file descriptor required")
    need(type(descriptor["bytes"]) is int and 0 <= descriptor["bytes"] <= maximum and
         re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"] or "") is not None, "Invalid file descriptor")
    path = checked_path(Path(root).absolute(), descriptor["path"])
    raw = read_file(path, deadline, maximum)
    need(len(raw) == descriptor["bytes"] and sha(raw) == descriptor["sha256"],
         "Pinned descriptor bytes differ: " + descriptor["path"])
    return raw


def code_inventory(package_root):
    package_root = Path(package_root).resolve()
    return {p.relative_to(package_root).as_posix(): sha(p.read_bytes())
            for p in sorted(package_root.rglob("*")) if p.is_file() and p.suffix in (".py", ".json")}


def load_authority(protocol_path, expected_sha256, bundle_root, deadline, *, require_installed=True):
    need(re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is not None,
         "Independently retained protocol byte SHA-256 required")
    path = Path(protocol_path).absolute()
    with stable_files((path,), deadline=deadline):
        raw = read_file(path, deadline, 8 * 1024**2)
    need(sha(raw) == expected_sha256, "External protocol byte anchor differs")
    document = parse_json(raw)
    need(type(document.get("schema_version")) is int and document["schema_version"] == 1 and document.get("method") == "p09.public_reconstruction_protocol.v1"
         and document.get("status") == "READY" and document.get("actual_reconstruction_authorized") is True,
         "A frozen authorized READY P09 protocol is required")
    root = Path(bundle_root).absolute()
    need(path == checked_path(root, "protocol.json"), "Protocol must be the explicitly approved bundle member")
    for key in ("source_policy", "comparison", "controls"):
        descriptor = document[key]
        need(document["files"].get(descriptor["path"]) == descriptor, "Protocol descriptor inventory differs")
    for logical, descriptor in document["files"].items():
        need(descriptor["path"] == logical, "Bundle logical path differs")
        read_descriptor(root, descriptor, deadline)
    environment = document["environment"]
    import pyarrow
    need(environment == dict(python=platform.python_version(), pyarrow=pyarrow.__version__, platform=sys.platform),
         "P09 Python/Arrow/platform differs from frozen reconstruction authority")
    need(sys.platform == "win32" and pyarrow.__version__ == "21.0.0", "Actual source replay requires Windows/Arrow21")
    for package, expected, distribution, version in (
        (asof, document["core_files"], "asof-target-agents", "0.3.11"),
        (asof_p05_replay, document["replay_files"], "asof-p05-replay", "0.1.0"),
    ):
        package_root = Path(package.__file__).resolve().parent
        if require_installed:
            need(package_root.is_relative_to(Path(sys.prefix).resolve()), "Reconstruction imports must come from installed environments")
            need(metadata.version(distribution) == version, "Installed distribution version differs")
        need(code_inventory(package_root) == expected, "Complete installed source/resource proof differs: " + distribution)
    return dict(document=encode(document), raw_bytes=raw, byte_sha256=expected_sha256)
