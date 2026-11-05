"""Strict JSON/dataclass decoding and canonical artifact fingerprints."""

from __future__ import annotations

import hashlib
import json
import math
import types
import os
import tempfile
import time
from dataclasses import MISSING, fields, is_dataclass
from datetime import date, datetime, timezone
from collections.abc import Mapping
from types import MappingProxyType
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints


_WINDOWS_REPLACE_RETRY = os.name == "nt"
_REPLACE_RETRY_DELAYS = (0.05, 0.1)


class ContractError(ValueError):
    """Invalid input, provenance or scientific contract."""


def freeze(value: Any) -> Any:
    """Copy and recursively freeze containers; no caller-owned backing dictionaries."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


class Frozen:
    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(self, field.name, freeze(getattr(self, field.name)))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(payload: str | bytes) -> Any:
    def bad_constant(value: str) -> None:
        raise ContractError(f"Non-finite JSON number: {value}")

    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8-sig")
        return json.loads(payload,
                          object_pairs_hook=_pairs, parse_constant=bad_constant)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ContractError(f"Invalid JSON: {error}") from error


MAX_NORMALIZED_JSON_BYTES = 64 * 1024 * 1024
# Sealed ledger outputs repeat citation/claim envelopes around admitted records.
# Four times the packet limit provides finite output headroom; it does not expand
# evidence admission or guarantee that arbitrary multi-packet runs fit this cap.
MAX_LEDGER_JSON_BYTES = 256 * 1024 * 1024


def _read_bounded_json(path: Path, maximum: int, message: str) -> Any:
    if path.stat().st_size > maximum:
        raise ContractError(message)
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise ContractError(message)
    return parse_json(payload)


def read_json(path: Path) -> Any:
    return _read_bounded_json(path, MAX_NORMALIZED_JSON_BYTES,
        "Normalized JSON input exceeds the 64 MiB limit; select a smaller packet")


def read_ledger_json(path: Path) -> Any:
    """Read a sealed execution ledger output, never a normalized evidence input."""
    return _read_bounded_json(path, MAX_LEDGER_JSON_BYTES,
        "Ledger JSON output exceeds the 256 MiB limit")



def decode(kind: Any, value: Any, location: str = "input") -> Any:
    """Reject unknown fields and coercions (including bool-as-number)."""
    origin = get_origin(kind)
    args = get_args(kind)
    if kind is Any:
        # Arbitrary method parameters remain JSON data, never executable code.
        if isinstance(value, float) and not math.isfinite(value):
            raise ContractError(f"{location}: expected finite value")
        if isinstance(value, Mapping):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ContractError(f"{location}: expected string keys")
                decode(Any, item, f"{location}.{key}")
        if isinstance(value, list):
            for item in value:
                decode(Any, item, location)
        return value
    if origin in (Union, types.UnionType):
        branch_errors = []
        for option in args:
            try:
                return decode(option, value, location)
            except (ContractError, ValueError, TypeError) as error:
                branch_errors.append(error)
        raise ContractError(f"{location}: invalid value for {kind}") from ExceptionGroup(
            f"{location}: union branch validation errors", branch_errors)
    if kind is type(None):
        if value is not None:
            raise ContractError(f"{location}: expected null")
        return None
    if origin in (list, tuple):
        if not isinstance(value, list):
            raise ContractError(f"{location}: expected array")
        items = [decode(args[0], item, f"{location}[{i}]")
                 for i, item in enumerate(value)]
        return tuple(items) if origin is tuple else items
    if origin in (dict, Mapping):
        if not isinstance(value, dict):
            raise ContractError(f"{location}: expected object")
        return {decode(args[0], key, location): decode(args[1], item, f"{location}.{key}")
                for key, item in value.items()}
    if kind is datetime:
        if not isinstance(value, str):
            raise ContractError(f"{location}: expected timezone-aware ISO timestamp")
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ContractError(f"{location}: invalid timestamp") from error
        if result.tzinfo is None:
            raise ContractError(f"{location}: timestamp requires a timezone")
        return result.astimezone(timezone.utc)
    if kind is date:
        if not isinstance(value, str) or len(value) != 10:
            raise ContractError(f"{location}: expected YYYY-MM-DD")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ContractError(f"{location}: invalid date") from error
    if isinstance(kind, type) and issubclass(kind, Enum):
        try:
            return kind(value)
        except (ValueError, TypeError) as error:
            raise ContractError(f"{location}: invalid {kind.__name__}: {value}") from error
    if is_dataclass(kind):
        if not isinstance(value, dict):
            raise ContractError(f"{location}: expected object")
        names = {field.name for field in fields(kind)}
        extra = value.keys() - names
        if extra:
            raise ContractError(f"{location}: unknown fields {sorted(extra)}")
        hints = get_type_hints(kind)
        result = {}
        for field in fields(kind):
            if field.name not in value:
                if field.default is MISSING and field.default_factory is MISSING:
                    raise ContractError(f"{location}: missing {field.name}")
                continue
            result[field.name] = decode(hints[field.name], value[field.name],
                                        f"{location}.{field.name}")
        return kind(**result)
    if kind is float:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ContractError(f"{location}: expected finite number")
        return float(value)
    if kind in (str, int, bool):
        if type(value) is not kind:
            raise ContractError(f"{location}: expected {kind.__name__}")
        return value
    raise ContractError(f"{location}: unsupported schema type {kind}")


def encode(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: encode(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ContractError("Cannot serialize a naive timestamp")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def canonical(value: Any) -> bytes:
    return json.dumps(encode(value), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_staged(temporary: Path, path: Path) -> None:
    """Retry only native Windows access failures on the same staged bytes.

    Error 5 can be permanent; this is a bounded retry policy, not a diagnosis.
    At most three replace calls and 150 ms requested sleep are added. Individual
    filesystem calls/scheduler delays are not a hard wall-time guarantee. This
    mutable-file operation is deliberately separate from no-clobber publication.
    """
    for attempt in range(len(_REPLACE_RETRY_DELAYS) + 1):
        try:
            os.replace(temporary, path)
            return
        except OSError as error:
            if (not _WINDOWS_REPLACE_RETRY or getattr(error, "winerror", None) not in (5, 32, 33) or
                    attempt == len(_REPLACE_RETRY_DELAYS)):
                if attempt:
                    error.add_note(f"Atomic JSON replacement failed after {attempt + 1} attempts; same staged file retained until cleanup")
                raise
            time.sleep(_REPLACE_RETRY_DELAYS[attempt])


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    payload = canonical(value) if compact else (
        json.dumps(encode(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    temporary = Path(name)
    primary = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _replace_staged(temporary, path)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except BaseException as cleanup_error:
            if primary is None:
                raise
            primary.add_note(f"Staged JSON cleanup failed ({type(cleanup_error).__name__}): {cleanup_error}; path={temporary}")


def _windows_path_spelling(value: str) -> str:
    """Canonicalize only equivalent extended Win32 drive/UNC spellings.

    Path.resolve may retain an extended prefix when a missing directory appears
    concurrently. Normalize after resolution, so symlink targets still determine
    containment. Other device namespaces are not filesystem artifact roots.
    """
    if value.startswith(("\\\\.\\", "\\??\\")):
        raise ContractError("Unsupported Windows device path")
    if not value.startswith("\\\\?\\"):
        return value
    tail = value[4:]
    # Extended syntax also permits names that ordinary Win32 paths reinterpret.
    # Those are not spelling aliases and must not be silently normalized.
    components = tail.split("\\")
    for index, component in enumerate(components):
        if not component and index == len(components) - 1:
            continue
        if not component or component.endswith((".", " ")):
            raise ContractError("Non-equivalent extended Windows path")
        if ":" in component and not (index == 0 and len(component) == 2 and component[1] == ":"):
            raise ContractError("Unsupported extended Windows path component")
    if tail[:4].upper() == "UNC\\":
        components = tail[4:].split("\\")
        if len(components) < 2 or any(part in ("", ".", "..") for part in components[:2]):
            raise ContractError("Invalid extended Windows UNC path")
        return "\\\\" + tail[4:]
    if len(tail) >= 3 and tail[0].isascii() and tail[0].isalpha() and tail[1:3] == ":\\":
        return tail
    raise ContractError("Unsupported Windows device path")


def _windows_path_identity(path: Path) -> Path:
    return Path(_windows_path_spelling(str(path))) if os.name == "nt" else path


def safe_child(root: Path, relative: str) -> Path:
    """Constrain paths after resolving symlinks; reject Windows drive/ADS syntax."""
    parts = relative.replace("\\", "/").split("/")
    if not relative or relative.startswith(("/", "\\")) or ":" in relative:
        raise ContractError(f"Expected relative artifact path: {relative}")
    if any(part in ("", ".", "..") for part in parts):
        raise ContractError(f"Unsafe artifact path: {relative}")
    root = _windows_path_identity(root)
    resolved = _windows_path_identity(root.joinpath(*parts).resolve())
    if not resolved.is_relative_to(_windows_path_identity(root.resolve())):
        raise ContractError(f"Artifact escapes approved root: {relative}")
    return resolved

