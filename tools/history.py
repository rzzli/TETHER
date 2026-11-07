"""Read exact archival test bytes from the immutable pre-migration checkpoint.

This is not a fallback for qualifying current scientific executions. Restored
files belong in fresh temporary directories and retain their original identity.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = "b492a8fca9bb1aa500d2939b3e2d19242a55cb96"
TAG = "tether-pre-namespace-migration-20261106"
MAX_BLOB_BYTES = 64 * 1024 * 1024
MAX_TREE_BYTES = 256 * 1024 * 1024
MAX_TREE_FILES = 4096


class HistoryError(ValueError):
    """An archived artifact cannot be recovered without changing its bytes."""


def _path(relative: str) -> str:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise HistoryError("Archive paths must be nonempty repository-relative POSIX paths")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ("", ".", "..", ".git") or ":" in part for part in relative.split("/")):
        raise HistoryError("Unsafe archive path")
    return relative


def _git(*arguments: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(ROOT), *arguments],
            stderr=subprocess.PIPE, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise HistoryError("Pinned historical checkpoint unavailable; restore " + TAG + " locally") from error


def _entries(relative: str) -> list[tuple[str, str]]:
    relative = _path(relative)
    output = _git("ls-tree", "-r", "-z", "--full-tree", CHECKPOINT, "--", relative)
    result = []
    for entry in output.split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8")
        _path(name)
        if name != relative and not name.startswith(relative + "/"):
            raise HistoryError("Archive path escaped requested subtree")
        if mode not in ("100644", "100755") or kind != "blob":
            raise HistoryError("Archive contains a nonregular file")
        if len(object_id) != 40 or any(char not in "0123456789abcdef" for char in object_id):
            raise HistoryError("Invalid immutable archive object identity")
        result.append((name, object_id))
    if not result or len(result) > MAX_TREE_FILES or len({name for name, _ in result}) != len(result):
        raise HistoryError("Missing, duplicate or oversized archive subtree")
    return result


def _blob(object_id: str) -> bytes:
    size = int(_git("cat-file", "-s", object_id))
    if not 0 <= size <= MAX_BLOB_BYTES:
        raise HistoryError("Archived blob exceeds read bound")
    raw = _git("cat-file", "blob", object_id)
    identity = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if len(raw) != size or identity != object_id:
        raise HistoryError("Archived blob identity mismatch")
    return raw


def read_checkpoint(relative: str) -> bytes:
    """Return an exact regular file; never import or execute archived content."""
    entries = _entries(relative)
    if len(entries) != 1 or entries[0][0] != relative:
        raise HistoryError("Expected one exact archived file")
    return _blob(entries[0][1])


def materialize_checkpoint(relative: str, destination: Path) -> Path:
    """Restore a regular file or subtree into an exclusively reserved new path."""
    entries = _entries(relative)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    # A caller-supplied parent must already exist and contain no link/reparse
    # components. New directory contents remain beneath this checked parent.
    for parent in (destination.parent, *destination.parent.parents):
        info = parent.lstat()
        if parent.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise HistoryError("Linked archive destination ancestor")
    is_file = len(entries) == 1 and entries[0][0] == relative
    if is_file:
        raw = _blob(entries[0][1])
        with destination.open("xb") as stream:
            stream.write(raw)
        return destination
    destination.mkdir(exist_ok=False)
    total = 0
    for name, object_id in entries:
        raw = _blob(object_id)
        total += len(raw)
        if total > MAX_TREE_BYTES:
            raise HistoryError("Archived subtree exceeds total bound")
        target = destination.joinpath(*PurePosixPath(name[len(relative) + 1:]).parts)
        if not target.is_relative_to(destination):
            raise HistoryError("Archive destination escaped")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
    return destination
