"""Read bounded historical source bytes without importing or executing them.

An externally anchored manifest binds logical execution paths to local archived
files. Payloads must stay beneath the manifest directory. No working-tree
fallback, relocation of execution records, or permission to execute is implied.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType


MAX_MANIFEST_BYTES = 4 * 1024 ** 2
MAX_FILES = 2048
MAX_FILE_BYTES = 8 * 1024 ** 2
MAX_TOTAL_BYTES = 64 * 1024 ** 2
_HASH = re.compile(r"[0-9a-f]{64}\Z")


class SourceArchiveError(ValueError):
    """The archive does not establish the requested historical source binding."""


def _need(condition, message):
    if not condition:
        raise SourceArchiveError(message)


def _hash(value):
    _need(isinstance(value, str) and _HASH.fullmatch(value), "Invalid SHA-256")
    return value


def _logical(value):
    _need(isinstance(value, str) and value and "\\" not in value and ":" not in value,
          "Invalid logical source path")
    _need(all(part not in ("", ".", "..") for part in value.split("/")) and
          not PurePosixPath(value).is_absolute() and "\x00" not in value,
          "Unsafe logical source path")
    return value


def _absolute(value):
    _need(isinstance(value, str) and value and "\x00" not in value,
          "Invalid absolute archive path")
    # Reject aliases before pathlib normalizes away dot components. A local
    # archive cannot use UNC/device paths or alternate data streams on Windows.
    _need(not value.startswith(("\\\\", "//")), "Network/device archive path")
    _need(all(part not in (".", "..") for part in re.split(r"[/\\]", value)),
          "Traversal in archive path")
    path = Path(value)
    _need(path.is_absolute(), "Archive path must be absolute")
    # Keep archive names portable and unambiguous on Windows even when a
    # manifest is first checked on another platform. Win32 strips trailing dots
    # and spaces and interprets device basenames independently of extensions.
    for component in path.parts[1:]:
        _need(component.rstrip(' .') == component and
              not any(ord(char) < 32 or char in '<>:"|?*' for char in component),
              "Ambiguous archive path component")
        stem = component.split('.')[0].upper()
        _need(stem not in {'CON', 'PRN', 'AUX', 'NUL'} and
              re.fullmatch(r'(COM|LPT)[1-9\u00b9\u00b2\u00b3]', stem) is None,
              "Reserved archive path component")
    if os.name == "nt":
        _need(not any(":" in part for part in path.parts[1:]), "Alternate stream archive path")
    return path


def _regular(path):
    # Inspect every ancestor without resolve(): resolve would hide a linked
    # parent and permit content outside the declared archive directory.
    for parent in reversed(path.parents):
        info = parent.lstat()
        _need(not stat.S_ISLNK(info.st_mode) and
              not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT and
              stat.S_ISDIR(info.st_mode), "Linked or non-directory archive parent")
    info = path.lstat()
    _need(not stat.S_ISLNK(info.st_mode) and
          not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT and
          stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
          "Linked or nonregular archive file")
    return info


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path, limit):
    before = _regular(path)
    _need(before.st_size <= limit, "Archive file exceeds byte limit")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        _need(_identity(before) == _identity(opened), "Archive file changed before read")
        data = stream.read(limit + 1)
        closed = os.fstat(stream.fileno())
    after = _regular(path)
    _need(_identity(before) == _identity(closed) == _identity(after) and
          len(data) == before.st_size <= limit, "Archive file changed during read")
    return data


def _object(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "Duplicate manifest key")
        value[key] = item
    return value


@dataclass(frozen=True, slots=True)
class SourceArchive:
    """Immutable bindings; each read/proof rechecks the current archived bytes."""

    original_repository_root: str
    _manifest_proof: object
    _files: object

    @property
    def manifest_proof(self):
        return dict(self._manifest_proof)

    @property
    def logical_names(self):
        return tuple(self._files)

    def _checked(self, logical_name):
        _logical(logical_name)
        _need(logical_name in self._files, "Source is not bound by this archive")
        expected = self._files[logical_name]
        payload = _read(Path(expected["path"]), MAX_FILE_BYTES)
        _need(len(payload) == expected["bytes"] and
              hashlib.sha256(payload).hexdigest() == expected["sha256"],
              "Archived source differs from its immutable binding")
        return payload, dict(expected)

    def read(self, logical_name):
        return self._checked(logical_name)[0]

    def proof(self, logical_name):
        """Return the physical archive proof, never a fictional original path."""
        return self._checked(logical_name)[1]


def load_archive(path, sha, code_pins, original_repository_root):
    """Verify an exact source archive and its complete caller-supplied pin set."""
    location = _absolute(os.fspath(path))
    _hash(sha)
    declared_root = os.fspath(original_repository_root)
    _absolute(declared_root)
    _need(isinstance(code_pins, dict) and 0 < len(code_pins) <= MAX_FILES,
          "Invalid source pin count")
    # Copy caller data before validating or performing file I/O.
    pins = dict(code_pins)
    for name, fingerprint in pins.items():
        _logical(name)
        _hash(fingerprint)
    raw = _read(location, MAX_MANIFEST_BYTES)
    _need(hashlib.sha256(raw).hexdigest() == sha, "External source archive anchor mismatch")
    try:
        manifest = json.loads(raw, object_pairs_hook=_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SourceArchiveError("Invalid source archive JSON") from error
    _need(isinstance(manifest, dict) and set(manifest) ==
          {"schema_version", "kind", "original_repository_root", "files"},
          "Unexpected source archive schema")
    _need(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1 and
          manifest["kind"] == "sc04_executed_source_archive_v1", "Unsupported source archive schema")
    _absolute(manifest["original_repository_root"])
    _need(manifest["original_repository_root"] == declared_root, "Original repository root differs")
    files = manifest["files"]
    _need(isinstance(files, dict) and set(files) == set(pins), "Archive source membership differs")
    archive_root = location.parent
    bound = {}
    total = 0
    physical_paths = set()
    for name, item in files.items():
        _logical(name)
        _need(isinstance(item, dict) and set(item) == {"path", "bytes", "sha256"},
              "Unexpected source proof schema")
        _hash(item["sha256"])
        _need(item["sha256"] == pins[name], "Archive source hash differs from executed pin")
        _need(type(item["bytes"]) is int and 0 <= item["bytes"] <= MAX_FILE_BYTES,
              "Invalid source byte count")
        total += item["bytes"]
        _need(total <= MAX_TOTAL_BYTES, "Archive exceeds total byte limit")
        physical = _absolute(item["path"])
        _need(physical.is_relative_to(archive_root) and physical != location,
              "Source outside the archive payload root")
        identity = os.path.normcase(str(physical))
        _need(identity not in physical_paths, "Physical source file used by multiple logical paths")
        physical_paths.add(identity)
        payload = _read(physical, MAX_FILE_BYTES)
        _need(len(payload) == item["bytes"] and hashlib.sha256(payload).hexdigest() == item["sha256"],
              "Archived source bytes differ")
        bound[name] = MappingProxyType(dict(item, path=str(physical)))
    return SourceArchive(declared_root,
                         MappingProxyType(dict(path=str(location), bytes=len(raw), sha256=sha)),
                         MappingProxyType(bound))
