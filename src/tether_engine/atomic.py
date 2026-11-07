"""Atomic no-clobber publication of complete bytes on supported local filesystems.

Windows uses same-directory os.rename: Windows rename fails if the destination
exists, including under competing writers, and does not require hard links.
POSIX uses link publication, where destination creation is atomic/no-clobber.
There is intentionally no POSIX rename or exists-plus-replace fallback. A
filesystem that cannot provide the selected primitive fails closed. This is
atomic visibility, not a promise of directory-entry durability after power loss.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from threading import Lock


_directory_initialization_lock = Lock()


def ensure_directory(path: Path) -> None:
    """Serialize in-process directory initialization; propagate filesystem failures.

    This does not coordinate directory creation by other processes. Publication
    itself remains protected across processes by the OS rename/link primitive.
    """
    with _directory_initialization_lock:
        Path(path).mkdir(parents=True, exist_ok=True)


def publish_bytes(path: Path, payload: bytes, *, prefix='.publishing-') -> None:
    """Publish exactly payload once; preserve existing destinations and clean staging."""
    if not isinstance(payload, bytes):
        raise TypeError('Atomic publication requires immutable bytes')
    path = Path(path)
    ensure_directory(path.parent)
    descriptor, name = tempfile.mkstemp(prefix=prefix, dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'nt':
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
