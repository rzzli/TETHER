"""Bounded stable reads on Windows; file sharing is not a hostile-user sandbox.

Callers hold stable_files across hashing and interpretation of original paths.
Directory handles deny rename, not creation of all possible child files. System
DLLs, filesystem/OS integrity and privileged actors remain trust dependencies.
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import math
import os
from pathlib import Path
import stat
import time

from asof.serde import ContractError, freeze
from .proofs import _identity, _no_links, _relative


def deadline_check(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ContractError("An absolute monotonic deadline is required")
    if time.monotonic() >= deadline:
        raise TimeoutError("Preparation deadline expired")


def checked_path(root, relative):
    """Resolve an explicit logical descendant, rejecting aliases before access."""
    _relative(relative)
    root = Path(root)
    if not root.is_absolute() or root.drive.startswith("\\\\"):
        raise ContractError("An absolute local approved root is required")
    if len(root.parts) > 1:
        _relative("/".join(root.parts[1:]))
    _no_links(root)
    path = root.joinpath(*relative.split("/"))
    _no_links(path)
    if not path.is_relative_to(root):
        raise ContractError("Input escapes approved root")
    return path


def hash_file(path, deadline):
    deadline_check(deadline)
    path = Path(path).absolute()
    _no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ContractError("Stable input is not a regular file")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(before):
            raise ContractError("Stable input changed before hashing")
        while True:
            deadline_check(deadline)
            block = stream.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > before.st_size:
                raise ContractError("Stable input grew while hashing")
            digest.update(block)
        after = os.fstat(stream.fileno())
    deadline_check(deadline)
    _no_links(path)
    if (
        _identity(before) != _identity(after)
        or _identity(after) != _identity(path.stat())
        or size != before.st_size
    ):
        raise ContractError("Stable input changed while hashing")
    return freeze({"sha256": digest.hexdigest(), "bytes": size})


def read_file(path, deadline, max_bytes):
    if type(max_bytes) is not int or max_bytes < 0:
        raise ContractError("Invalid stable read bound")
    deadline_check(deadline)
    path = Path(path).absolute()
    _no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
        raise ContractError("Stable input exceeds its read bound")
    chunks, size = [], 0
    with path.open("rb") as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(before):
            raise ContractError("Stable input changed before read")
        while True:
            deadline_check(deadline)
            block = stream.read(min(1024 * 1024, max_bytes + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > max_bytes:
                raise ContractError("Stable read exceeds bound")
        after = os.fstat(stream.fileno())
    deadline_check(deadline)
    _no_links(path)
    if (
        _identity(before) != _identity(after)
        or _identity(after) != _identity(path.stat())
        or size != before.st_size
    ):
        raise ContractError("Stable input changed while reading")
    return b"".join(chunks)


@contextmanager
def stable_files(paths, *, deadline):
    """Hold read/share-read file handles and no-delete directory handles.

    Fail closed on non-Windows. Tests may inject this trusted Python boundary;
    serialized manifests cannot select another locking implementation.
    """
    deadline_check(deadline)
    if os.name != "nt":
        raise ContractError("Stable original-path reads require Windows sharing locks")
    files = tuple(sorted({Path(path).absolute() for path in paths}))
    if not files:
        raise ContractError("Stable-read inventory cannot be empty")
    for path in files:
        _no_links(path)
        if not path.is_file():
            raise ContractError("Stable input must be a regular file")
    directories = sorted(
        {parent for path in files for parent in path.parents},
        key=lambda p: (len(p.parts), str(p)),
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handles, primary = [], None
    try:
        for directory, path in [(True, p) for p in directories] + [
            (False, p) for p in files
        ]:
            deadline_check(deadline)
            _no_links(path)
            handle = kernel.CreateFileW(
                str(path),
                0x80000000,
                3 if directory else 1,
                None,
                3,
                0x02000000 if directory else 0x80,
                None,
            )
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            _no_links(path)
        deadline_check(deadline)
        yield
        deadline_check(deadline)
    except BaseException as error:
        primary = error
        raise
    finally:
        cleanup = None
        while handles:
            if not kernel.CloseHandle(handles.pop()):
                error = ctypes.WinError(ctypes.get_last_error())
                if cleanup is None:
                    cleanup = error
        if cleanup is not None:
            if primary is None:
                raise cleanup
            primary.add_note("Stable-read cleanup failed: " + type(cleanup).__name__)
