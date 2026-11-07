"""Versioned logical identities and caller-approved archive IO; never execute code."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from tether_engine.serde import ContractError


def _need(ok, message):
    if not ok:
        raise ContractError(message)


def _parts(value):
    _need(isinstance(value, str) and value and '\x00' not in value,
          'Invalid archive logical path')
    windows = bool(re.match(r'^[A-Za-z]:', value))
    if windows:
        _need(len(value) >= 3 and value[2] in '/\\', 'Drive-relative archive path denied')
        anchor, rest = value[:2].upper(), value[3:].replace('\\', '/')
    else:
        _need(value.startswith('/') and not value.startswith('//') and '\\' not in value,
              'Logical path must be absolute POSIX or drive-qualified Windows; UNC denied')
        anchor, rest = '/', value[1:]
    components = rest.split('/') if rest else []
    _need(all(x not in ('', '.', '..') and ':' not in x and
              not any(ord(c) < 32 for c in x) for x in components),
          'Traversal, empty component or ADS in archive path')
    if windows:
        _need(all(not x.endswith((' ', '.')) and not any(c in x for c in '<>"|?*')
                  and x.split('.')[0].upper() not in
                  {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                   *(f'LPT{i}' for i in range(1, 10))} for x in components),
              'Ambiguous Windows archive component')
    return windows, anchor, tuple(components)


def logical_key(value):
    """Host-independent, component-aware identity; never accesses the filesystem."""
    windows, anchor, parts = _parts(str(value))
    return ('windows' if windows else 'posix', anchor,
            *(x.casefold() if windows else x for x in parts))


def join(logical_directory, relative):
    """Join a strictly relative artifact name without altering original directory spelling."""
    _parts(str(logical_directory))
    _relative(relative)
    return str(logical_directory).rstrip('/\\') + '/' + relative.replace('\\', '/')


def _relative(value):
    _need(isinstance(value, str) and value and not value.startswith(('/', '\\')) and
          ':' not in value and '\x00' not in value, 'Invalid relative archive path')
    parts = value.replace('\\', '/').split('/')
    _need(all(p not in ('', '.', '..') and not p.endswith((' ', '.')) and
              not any(ord(c) < 32 or c in '<>"|?*' for c in p) for p in parts),
          'Unsafe relative archive path')
    _parts('Z:/' + '/'.join(parts))  # Reject device names on every restoration host.
    return parts


def _no_links(path):
    """Reject every existing symlink/reparse component, including approved root ancestors."""
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        _need(not stat.S_ISLNK(info.st_mode) and
              not (getattr(info, 'st_file_attributes', 0) & 0x400),
              'Archive symlink/reparse component denied: ' + str(item))


@dataclass(frozen=True)
class _File:
    logical_path: str
    root_id: str
    relative_path: str
    sha256: str
    size: int


class ArchiveResolver:
    """Per-run immutable allowlist. Unregistered identities never fall back to originals.

    bindings: [{root_id, logical_root, physical_root}]
    files: [{logical_path, root_id, relative_path, sha256, bytes}]
    A separate resolver per run permits the same original code identity at different hashes.
    """
    resolver_version = 1
    logical_key = staticmethod(logical_key)
    join = staticmethod(join)

    def __init__(self, bindings, files):
        roots, logical, declared_roots = {}, {}, {}
        for binding in bindings:
            rid = binding['root_id']
            _need(isinstance(rid, str) and re.fullmatch(r'[A-Za-z0-9_-]+', rid) and rid not in roots,
                  'Duplicate/invalid archive root ID')
            key = logical_key(binding['logical_root'])
            physical = Path(binding['physical_root'])
            _need(physical.is_absolute(), 'Physical archive root must be caller-approved absolute path')
            _no_links(physical)
            physical = physical.resolve(strict=True)
            _need(physical.is_dir(), 'Archive root is not a directory')
            for other in logical.values():
                _need(not (key[:len(other)] == other or other[:len(key)] == key),
                      'Logical root alias collision/overlap')
            for other in roots.values():
                _need(not (physical.is_relative_to(other) or other.is_relative_to(physical)),
                      'Physical root alias collision/overlap')
            roots[rid], logical[rid] = physical, key
            declared_roots[key] = binding['logical_root']
        _need(bool(roots), 'Archive roots required')
        entries, destinations = {}, {}
        for entry in files:
            rid = entry['root_id']; key = logical_key(entry['logical_path'])
            _need(rid in roots and key not in entries, 'Unknown root or duplicate logical file')
            base = logical[rid]
            _need(key[:len(base)] == base and len(key) > len(base), 'File outside its logical root')
            relative = entry['relative_path']; parts = _relative(relative)
            digest, size = entry['sha256'], entry['bytes']
            _need(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) and
                  type(size) is int and size >= 0, 'Invalid archive hash/size')
            destination = (rid, tuple(p.casefold() if os.name == 'nt' else p for p in parts))
            # Multiple logical identities may share exactly the same CAS object only at equal hash/size.
            prior = destinations.get(destination)
            _need(prior is None or (prior.sha256, prior.size) == (digest, size),
                  'Conflicting archive physical file alias')
            entries[key] = _File(entry['logical_path'], rid, relative, digest, size)
            destinations[destination] = entries[key]
        self._roots = MappingProxyType(roots)
        self._logical_roots = MappingProxyType(logical)
        self._declared_roots = MappingProxyType(declared_roots)
        self._files = MappingProxyType(entries)

    def layout_path(self, logical_path):
        """Validate a mapped location without granting read permission or requiring bytes.

        Used for root directories and excluded lineage nodes during graph construction.
        Registered files retain their explicit CAS layout; other paths mirror the logical
        suffix under its approved root. Only read_bytes/verify_file attest file contents.
        """
        key = logical_key(logical_path)
        item = self._files.get(key)
        if item is not None:
            root = self._roots[item.root_id]
            path = root.joinpath(*_relative(item.relative_path))
        else:
            matches = [(rid, base) for rid, base in self._logical_roots.items()
                       if key[:len(base)] == base]
            _need(len(matches) == 1, 'Layout identity outside approved logical roots')
            rid, base = matches[0]
            root = self._roots[rid]
            # Use original spelling, not case-folded identity components, on POSIX hosts.
            parts = _parts(str(logical_path))[2]
            suffix = parts[len(base) - 2:]
            path = root.joinpath(*suffix)
        _no_links(path)
        candidate = path.resolve(strict=False)
        _need(candidate.is_relative_to(root), 'Archive layout escapes approved root')
        return candidate

    def declared_path(self, logical_path):
        """Return exact manifest spelling for a registered file or declared root only."""
        key = logical_key(logical_path)
        item = self._files.get(key)
        if item is not None:
            return item.logical_path
        _need(key in self._declared_roots, 'No declared original archive identity')
        return self._declared_roots[key]

    @property
    def file_entries(self):
        """Immutable snapshots of file declarations for closure/inventory verification."""
        return tuple(MappingProxyType(dict(logical_path=f.logical_path, root_id=f.root_id,
                     relative_path=f.relative_path, sha256=f.sha256, bytes=f.size))
                     for f in self._files.values())

    def resolve(self, logical_path):
        key = logical_key(logical_path)
        _need(key in self._files, 'Unregistered archive identity: ' + str(logical_path))
        item = self._files[key]; root = self._roots[item.root_id]
        path = root.joinpath(*_relative(item.relative_path))
        _no_links(path)
        physical = path.resolve(strict=True)
        _need(physical.is_relative_to(root) and physical.is_file(), 'Archive file escapes root or is not regular')
        return physical

    def _checked(self, logical_path, retain, maximum_bytes=None):
        _need(maximum_bytes is None or type(maximum_bytes) is int and maximum_bytes >= 0,
              'Invalid archive read limit')
        item = self._files[logical_key(logical_path)] if logical_key(logical_path) in self._files else None
        _need(item is not None, 'Unregistered archive identity: ' + str(logical_path))
        if maximum_bytes is not None:
            _need(item.size <= maximum_bytes, 'Archive declaration exceeds read limit')
        path = self.resolve(logical_path); before = path.stat()
        if maximum_bytes is not None:
            _need(before.st_size <= maximum_bytes, 'Archive file exceeds read limit')
        digest, chunks = hashlib.sha256(), []
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            _need(stat.S_ISREG(opened.st_mode) and (before.st_dev, before.st_ino) ==
                  (opened.st_dev, opened.st_ino), 'Archive file changed before read')
            if maximum_bytes is not None:
                _need(opened.st_size <= maximum_bytes, 'Archive opened file exceeds read limit')
            total = 0
            while True:
                allowance = 1024 * 1024 if maximum_bytes is None else min(
                    1024 * 1024, maximum_bytes - total + 1)
                chunk = stream.read(allowance)
                if not chunk:
                    break
                total += len(chunk)
                if maximum_bytes is not None:
                    _need(total <= maximum_bytes, 'Archive stream exceeds read limit')
                _need(total <= item.size, 'Archive file exceeds declared size')
                digest.update(chunk)
                if retain:
                    chunks.append(chunk)
            after = os.fstat(stream.fileno())
        final_path = self.resolve(logical_path); final = final_path.stat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        _need(identity(before) == identity(opened) == identity(after) == identity(final),
              'Archive file changed during read')
        _need(total == item.size and digest.hexdigest() == item.sha256, 'Archive file hash/size mismatch')
        return b''.join(chunks) if retain else path

    def read_bytes(self, logical_path, *, maximum_bytes=None):
        """Authenticate retained bytes, optionally rejecting oversize before buffering.

        The caller supplies its artifact-specific allowance; raw-source verification
        and callers without a limit retain the existing streaming/hash behavior.
        One extra byte may be read to detect concurrent growth, but is never retained.
        """
        return self._checked(logical_path, True, maximum_bytes)

    def verify_file(self, logical_path):
        return self._checked(logical_path, False)


def from_envelope(envelope_path, expected_sha256, approved_roots, run_id):
    """Load externally anchored envelope; archive content cannot authorize physical roots.

    {schema_version:1,resolver_version:1,roots:[{root_id,logical_root}],
     runs:[{run_id,receipt_sha256,files:[...]}]}
    Extra application metadata is allowed; physical_root in roots is forbidden.
    """
    path = Path(envelope_path)
    _no_links(path.absolute())
    raw = path.read_bytes()
    _need(isinstance(expected_sha256, str) and hashlib.sha256(raw).hexdigest() == expected_sha256,
          'External archive envelope anchor mismatch')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, 'Duplicate archive JSON key')
            result[key] = value
        return result
    doc = json.loads(raw, object_pairs_hook=unique)
    _need(type(doc.get('schema_version')) is int and doc['schema_version'] == 1 and
          type(doc.get('resolver_version')) is int and doc['resolver_version'] == 1,
          'Unsupported archive envelope/resolver version')
    runs = doc['runs']; ids = [r['run_id'] for r in runs]
    _need(len(ids) == len(set(ids)) and run_id in ids, 'Unknown/duplicate archived run')
    roots = doc['roots']; root_ids = [r['root_id'] for r in roots]
    _need(set(approved_roots) == set(root_ids), 'Approved root map differs from envelope')
    bindings = []
    for root in roots:
        _need(set(root) == {'root_id', 'logical_root'}, 'Envelope cannot authorize physical locations')
        bindings.append(dict(root, physical_root=approved_roots[root['root_id']]))
    run = runs[ids.index(run_id)]
    _need(isinstance(run.get('receipt_sha256'), str) and
          re.fullmatch('[0-9a-f]{64}', run['receipt_sha256']), 'Archived receipt anchor required')
    return ArchiveResolver(bindings, run['files'])
