"""Static installed-package and data proofs; never execute archived code."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from importlib import metadata
import math
import os
from pathlib import Path
import platform
import re
import stat
import time

from tether_engine.serde import ContractError, fingerprint, freeze


_WINDOWS_IDENTITY = os.name == 'nt'


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _relative(value):
    _need(
        isinstance(value, str) and value and "\\" not in value,
        "Invalid logical identity",
    )
    parts = value.split("/")
    _need(
        all(
            p not in ("", ".", "..")
            and not p.endswith((" ", "."))
            and not any(ord(c) < 32 or c in ':<>"|?*' for c in p)
            and p.split(".")[0].upper()
            not in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10)),
            }
            for p in parts
        ),
        "Unsafe logical identity",
    )
    return value


def _no_links(path):
    for member in (*reversed(path.parents), path):
        info = member.lstat()
        _need(
            not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Proof path has a symlink/reparse component",
        )


def _identity(info):
    # On Windows Python 3.12+, use the explicit creation clock. Some builds
    # expose creation time through path.stat().ctime but change time through
    # fstat().ctime; those are different quantities even for an unchanged file.
    # https://docs.python.org/3.14/library/os.html#os.stat_result
    clock = getattr(info, 'st_birthtime_ns', info.st_ctime_ns) if _WINDOWS_IDENTITY else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, clock


def _handle_identity(info):
    # Still compare the descriptor's change clock with itself before/after I/O.
    return _identity(info) + (info.st_ctime_ns,)


def capture_file(path: Path, logical_id: str, *, deadline=None,
                 monotonic=time.monotonic, max_bytes=None) -> Mapping:
    """Hash bounded chunks with optional absolute deadline and pre-open size cap.

    Deadlines are checked around I/O, not a guarantee of OS syscall preemption.
    """
    _need(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline),
          "Invalid proof read deadline")
    _need(callable(monotonic), "Invalid proof clock")
    _need(max_bytes is None or type(max_bytes) is int and max_bytes >= 0,
          "Invalid proof size bound")
    def check_time():
        if deadline is not None and monotonic() >= deadline:
            raise TimeoutError("Proof read deadline exceeded")
    check_time()
    _relative(logical_id)
    path = Path(path).absolute()
    _no_links(path)
    before = path.stat()
    _need(stat.S_ISREG(before.st_mode), "Proof input must be a regular file")
    _need(max_bytes is None or before.st_size <= max_bytes, "Proof input exceeds size bound")
    check_time()
    digest, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        _need(_identity(before) == _identity(opened), "Proof file changed before read")
        while True:
            check_time()
            chunk = stream.read(1024 * 1024)
            check_time()
            if not chunk:
                break
            total += len(chunk)
            _need(total <= before.st_size, "Proof file grew during read")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    _no_links(path)
    _need(
        _identity(before) == _identity(after) == _identity(path.stat())
        and _handle_identity(opened) == _handle_identity(after)
        and total == before.st_size,
        "Proof file changed during read",
    )
    check_time()
    return freeze(dict(logical_id=logical_id, sha256=digest.hexdigest(), bytes=total))


def verify_file(path: Path, proof: Mapping, *, deadline=None, monotonic=time.monotonic) -> None:
    """Verify against an independently retained expected proof, not a sibling digest."""
    _need(
        isinstance(proof, Mapping) and set(proof) == {"logical_id", "sha256", "bytes"},
        "Invalid file proof",
    )
    _relative(proof["logical_id"])
    _need(
        type(proof["bytes"]) is int
        and proof["bytes"] >= 0
        and isinstance(proof["sha256"], str)
        and re.fullmatch("[0-9a-f]{64}", proof["sha256"]),
        "Invalid file proof size/hash",
    )
    _need(capture_file(path, proof["logical_id"], deadline=deadline,
                       monotonic=monotonic, max_bytes=proof["bytes"]) == proof,
          "File proof mismatch")


def _package_root():
    # This module belongs to the executing trusted installed package. No manifest
    # string is imported or treated as executable code.
    return Path(__file__).absolute().parent


def _required(resources, required_resources):
    _need(
        isinstance(resources, Mapping) and isinstance(required_resources, tuple),
        "Explicit resource mapping and required tuple are required",
    )
    _need(
        all(isinstance(name, str) for name in required_resources)
        and len(set(required_resources)) == len(required_resources)
        and set(resources) == set(required_resources),
        "Required resource inventory differs",
    )
    for name in required_resources:
        _relative(name)
    paths = [_relative(resources[name]) for name in required_resources]
    _need(
        len({p.casefold() for p in paths}) == len(paths)
        and all(not p.endswith(".py") for p in paths),
        "Duplicate/code resource identity",
    )


def _code_inventory(root):
    _no_links(root)
    _need((root / "__init__.py").is_file(), "Unsupported non-filesystem package")
    files = []
    for directory, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name != "__pycache__")
        for name in directories:
            _no_links(Path(directory) / name)
        for name in sorted(names):
            if name.endswith(".py"):
                member = Path(directory) / name
                files.append((member.relative_to(root).as_posix(), member))
    files.sort()
    _need(
        len({name.casefold() for name, _ in files}) == len(files),
        "Package path alias collision",
    )
    return files


def capture_package_proof(
    resources: Mapping[str, str], required_resources: tuple[str, ...]
) -> Mapping:
    """Inventory all executing-package Python plus the consumer's required resources.

    The consumer supplies its versioned complete resource-name set. The returned
    proof is immutable but must itself be anchored in a retained run receipt.
    """
    _required(resources, required_resources)
    root = _package_root()
    inventory = _code_inventory(root)
    code = tuple(capture_file(path, "tether_engine/" + relative) for relative, path in inventory)
    resource_proofs = {
        name: dict(
            relative_path=relative,
            proof=capture_file(root / relative, "tether_engine/" + relative),
        )
        for name, relative in sorted(resources.items())
    }
    _need(
        [name for name, _ in inventory] == [name for name, _ in _code_inventory(root)],
        "Package inventory changed during capture",
    )
    # An earlier member can change while later files are being hashed. Recheck
    # complete byte proofs, not merely the set of filenames, before returning.
    for (_, path), proof in zip(inventory, code):
        verify_file(path, proof)
    for record in resource_proofs.values():
        verify_file(root / record["relative_path"], record["proof"])
    try:
        version = metadata.version("tether-target-engine")
    except metadata.PackageNotFoundError:
        version = None
    return freeze(
        dict(
            schema_version=1,
            kind="installed_tether_engine_package",
            inventory_policy="all_python_and_required_resources_v1",
            package_version=version,
            python=dict(
                implementation=platform.python_implementation(),
                version=platform.python_version(),
            ),
            runtime_dependencies={},
            required_resources=tuple(sorted(required_resources)),
            code=code,
            resources=resource_proofs,
        )
    )


def verify_package_proof(
    proof: Mapping, *, required_resources: tuple[str, ...]
) -> None:
    """Compare to current trusted package; no original path or archived import is used."""
    _need(
        isinstance(proof, Mapping) and isinstance(proof.get("resources"), Mapping),
        "Invalid package proof",
    )
    resources = {}
    for name, record in proof["resources"].items():
        _need(
            isinstance(record, Mapping) and set(record) == {"relative_path", "proof"},
            "Invalid resource proof",
        )
        resources[name] = record["relative_path"]
    current = capture_package_proof(resources, required_resources)
    _need(fingerprint(current) == fingerprint(proof), "Package proof mismatch")
