"""Bounded local file reads for portable bundles, with held file identities."""
from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import Path
import stat
import unicodedata

from .serde import ContractError


def logical_parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not 0 < len(value) <= 512 or "\\" in value:
        raise ContractError("Expected a bounded relative bundle path")
    parts = tuple(value.split("/"))
    devices = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    devices.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "0123456789¹²³")
    for part in parts:
        if (not part or part.endswith((" ", ".")) or len(part) > 120 or
                part.split(".")[0].rstrip().upper() in devices or
                unicodedata.normalize("NFC", part) != part or
                any(ord(ch) < 32 or ord(ch) == 127 or ch in ':<>"|?*' or
                    unicodedata.category(ch) == "Cs" for ch in part)):
            raise ContractError("Unsafe or noncanonical relative bundle path")
    return parts


def _physical_path(value):
    try:
        path = Path(value).absolute()
    except (TypeError, ValueError, OSError) as error:
        raise ContractError("Expected an explicit local bundle path") from error
    if path.anchor.startswith(("\\\\", "//")) or ".." in path.parts:
        raise ContractError("Bundle paths require local paths without parent traversal")
    if len(path.parts) > 1:
        logical_parts("/".join(path.parts[1:]))
    return path


def _directory_ancestors(path, *, allow_missing):
    """Point-in-time preflight, not exclusive ownership of a hostile filesystem."""
    for member in (*reversed(path.parents), path):
        try:
            info = member.lstat()
        except FileNotFoundError:
            if allow_missing:
                return
            raise ContractError("Bundle source root is missing") from None
        except OSError as error:
            raise ContractError("Cannot inspect bundle directory ancestors") from error
        if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400 or
                not stat.S_ISDIR(info.st_mode)):
            raise ContractError("Bundle directory ancestors must be unlinked directories")


def checked_root(root: Path) -> Path:
    """Require an existing canonical local directory before trusting its scope."""
    path = _physical_path(root)
    _directory_ancestors(path, allow_missing=False)
    return path


def checked_output(output: Path, forbidden_roots=()) -> Path:
    """Reject unsafe output before any creation; caller still reserves exclusively.

    These path checks are point-in-time. They do not claim to prevent hostile
    concurrent directory replacement during later writes; bundle readers use
    held, no-follow file identities independently.
    """
    path = _physical_path(output)
    roots = tuple(checked_root(root) for root in forbidden_roots)
    if any(path.is_relative_to(root) for root in roots):
        raise ContractError("Bundle output must be outside original and run roots")
    _directory_ancestors(path.parent, allow_missing=True)
    try:
        path.lstat()
    except FileNotFoundError:
        return path
    except OSError as error:
        raise ContractError("Cannot inspect bundle output") from error
    raise ContractError("Bundle output must be a fresh directory")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _bounded(stream, before, maximum):
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
        raise ContractError("Bundle member must be a bounded, single-link regular file")
    if _identity(before) != _identity(os.fstat(stream.fileno())):
        raise ContractError("Bundle member changed before open")
    payload = stream.read(maximum + 1)
    if len(payload) != before.st_size or _identity(before) != _identity(os.fstat(stream.fileno())):
        raise ContractError("Bundle member changed during read")
    return payload


def _windows_member_allowed(attributes, directory, links, size, maximum):
    return (not attributes & 0x400 and bool(attributes & 0x10) == directory and
            (directory or (links == 1 and size <= maximum)))


def _read_posix(path, maximum):
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise ContractError("Bundle verification requires no-follow local file handles")
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent = os.open(path.anchor, flags)
        stack.callback(os.close, parent)
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=parent)
            stack.callback(os.close, child)
            parent = child
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ContractError("Bundle member must be a bounded, single-link regular file")
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            payload = _bounded(stream, before, maximum)
        if _identity(before) != _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)):
            raise ContractError("Bundle member was replaced during read")
        return payload


def _read_windows(path, maximum):
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL

    class FileInfo(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                    ("accessed", wintypes.FILETIME), ("modified", wintypes.FILETIME),
                    ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                    ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                    ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

    inspect = kernel.GetFileInformationByHandle
    inspect.argtypes = (wintypes.HANDLE, ctypes.POINTER(FileInfo))
    inspect.restype = wintypes.BOOL

    def open_checked(member, directory):
        # Open the reparse point itself, and deny deletion while traversing.
        # Files also deny writers while their held descriptor is consumed.
        flags = 0x00200000 | (0x02000000 if directory else 0)
        handle = create(str(member), 0x80000000, 3 if directory else 1, None, 3, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        info = FileInfo()
        if not inspect(handle, ctypes.byref(info)):
            error = ctypes.WinError(ctypes.get_last_error())
            close(handle)
            raise error
        if not _windows_member_allowed(info.attributes, directory, info.links,
                                       info.size_high << 32 | info.size_low, maximum):
            close(handle)
            raise ContractError("Bundle member is linked, nonregular or exceeds its read bound")
        return handle

    with ExitStack() as stack:
        for parent in reversed(path.parents):
            stack.callback(close, open_checked(parent, True))
        handle = open_checked(path, False)
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except OSError:
            close(handle)
            raise
        with os.fdopen(descriptor, "rb") as stream:
            return _bounded(stream, os.fstat(stream.fileno()), maximum)


def read_local(path: Path, maximum: int) -> bytes:
    """Read a local regular file through no-follow handles; never resolve links."""
    path = Path(path).absolute()
    if path.anchor.startswith(("\\\\", "//")) or ".." in path.parts or not path.name:
        raise ContractError("Bundle members require explicit local paths")
    try:
        return _read_windows(path, maximum) if os.name == "nt" else _read_posix(path, maximum)
    except OSError as error:
        raise ContractError(f"Cannot read bundle member {path.name!r}: {error.strerror or error}") from error
