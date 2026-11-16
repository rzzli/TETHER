"""Caller-owned source capabilities. Serialized metadata cannot grant a root.

Root ancestors selected by the caller may be links; descendants are opened
through held no-follow handles. This is not a sandbox against host compromise.
"""
from dataclasses import dataclass
import hashlib
import os
import math
from pathlib import Path, PureWindowsPath
import stat
import time
from types import MappingProxyType

from .bundle_files import logical_parts, read_local
from .serde import ContractError, _windows_path_identity


def local_path(value):
    """Validate spelling before resolve/stat/open, including on other OSes."""
    try:
        text = os.fspath(value)
        if not isinstance(text, str) or not text or '\x00' in text:
            raise ValueError('empty or non-text path')
        windows = PureWindowsPath(text)
        if text.startswith(('\\\\', '//')) or (windows.drive and not windows.root):
            raise ValueError('network, device or drive-relative path')
        path = Path(text)
        if not path.is_absolute():
            raise ValueError('absolute local path required')
        if len(path.parts) > 1:
            logical_parts('/'.join(path.parts[1:]))
        return path
    except (TypeError, ValueError) as error:
        raise ContractError('Source root/path requires an absolute local path without traversal') from error


def source_child(base, relative):
    """Join metadata lexically; never follow an untrusted path while inventorying."""
    if not isinstance(relative, str):
        raise ContractError('Expected relative source path')
    parts = logical_parts(relative.replace('\\', '/'))
    return local_path(base).joinpath(*parts)


def selected_root(value):
    """Resolve caller-selected ancestor links, rejecting network targets first."""
    value = os.fspath(value)
    # Relative roots are a caller convenience, not accepted in source metadata.
    if PureWindowsPath(value).drive and not PureWindowsPath(value).root:
        raise ContractError('Source root cannot be drive-relative')
    original = local_path(Path(value).absolute())
    path = original
    for _ in range(40):
        for member in (*reversed(path.parents), path):
            info = member.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                target = os.readlink(member)
                # Windows returns a device prefix for ordinary local junctions.
                if target.startswith('\\\\?\\') and len(target) > 6 and target[5:7] == ':\\':
                    target = target[4:]
                if not Path(target).is_absolute():
                    target = os.path.normpath(str(member.parent / target))
                target = local_path(target)  # reject UNC before its first stat
                path = target / path.relative_to(member)
                break
            if not stat.S_ISDIR(info.st_mode):
                raise ContractError(f'Source root is not a directory: {member}')
        else:
            # Only caller-selected, already inspected roots are resolved here.
            # In particular, Windows 8.3 names are aliases without reparse bits.
            # Serialized source descendants remain lexical until authorization.
            return original, local_path(_windows_path_identity(path.resolve(strict=True)))
    raise ContractError('Source root contains too many ancestor links')


def identity(info):
    clock = getattr(info, 'st_birthtime_ns', info.st_ctime_ns) if os.name == 'nt' else info.st_ctime_ns
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, clock, info.st_nlink)


@dataclass(frozen=True)
class SourceAccess:
    roots: tuple

    @classmethod
    def for_run(cls, output, roots=()):
        # Only this executing distribution grants its fixed demo location.
        builtin = Path(__file__).parent / 'demo' / 'v2'
        return cls(tuple(selected_root(root) for root in (output, builtin, *roots)))

    def authorize(self, value):
        path = local_path(value)
        for alias, physical in sorted(self.roots, key=lambda pair: len(pair[0].parts), reverse=True):
            if path.is_relative_to(alias):
                return physical / path.relative_to(alias)
            if path.is_relative_to(physical):
                return path
        raise ContractError(f'Explicit source-root authorization required for: {path}')

    def prepare(self, paths, *, deadline=None, allow_writers=False):
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ContractError('Invalid source preflight deadline')
        # Resolve the complete grant inventory before inspecting any source file.
        authorized = {local_path(path): self.authorize(path) for path in paths}
        identities = {}
        for logical, path in authorized.items():
            for member in (*reversed(path.parents), path):
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError('Source preflight deadline expired')
                try:
                    info = member.lstat()
                except OSError as error:
                    raise ContractError(f'Source input unavailable during preflight: {member}') from error
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ContractError(f'Linked source descendant denied: {member}')
                if member != path and not stat.S_ISDIR(info.st_mode):
                    raise ContractError('Source ancestor is not a directory')
            if not stat.S_ISREG(info.st_mode):
                raise ContractError('Source input must be a regular file')
            identities[logical] = identity(info)
        return SourceFiles(self, MappingProxyType(authorized), MappingProxyType(identities), deadline, allow_writers)


@dataclass(frozen=True)
class SourceFiles:
    access: SourceAccess
    paths: object
    identities: object
    deadline: float | None = None
    allow_writers: bool = False

    def consume(self, path, maximum, *, retain, deadline=None):
        deadline = self.deadline if deadline is None else deadline
        if type(maximum) is not int or maximum < 0:
            raise ContractError('Invalid source read bound')
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ContractError('Invalid source read deadline')

        def check_time():
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError('Source read deadline expired')

        check_time()
        path = local_path(path)
        if path not in self.paths:
            raise ContractError('Source read is outside the preflighted inventory')
        physical, expected = self.paths[path], self.identities[path]

        def reader(stream, before):
            if identity(before) != expected:
                raise ContractError('Source file changed after authorization preflight')
            digest, size, chunks = hashlib.sha256(), 0, []
            while True:
                check_time()
                block = stream.read(min(1024 * 1024, maximum + 1 - size))
                if not block:
                    break
                size += len(block)
                if size > maximum or size > before.st_size:
                    raise ContractError('Source input exceeds its read bound')
                digest.update(block)
                if retain:
                    chunks.append(block)
            after = os.fstat(stream.fileno())
            check_time()
            if size != before.st_size or identity(after) != expected or after.st_ctime_ns != before.st_ctime_ns:
                raise ContractError('Source file changed during read')
            return b''.join(chunks) if retain else (digest.hexdigest(), size)

        # Hash-bound source files may have installer hardlinks (uv's default).
        # Links do not grant extra paths; bundle member rules remain stricter.
        return read_local(physical, maximum, reader=reader, allow_hardlinks=True, allow_writers=self.allow_writers)

    def read(self, path, maximum, *, deadline=None):
        return self.consume(path, maximum, retain=True, deadline=deadline)

    def digest_size(self, path, *, deadline=None):
        path = local_path(path)
        if path not in self.identities:
            raise ContractError('Source read is outside the preflighted inventory')
        return self.consume(path, self.identities[path][2], retain=False, deadline=deadline)
