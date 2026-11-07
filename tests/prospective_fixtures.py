"""Restore pinned protocol inputs for synthetic current-code tests only.

Protocol and parent bytes are read from the immutable checkpoint, never from
mutable planning documents. Public metadata uses the small tracked schema copies.
Every parent must still match its original declared SHA-256. No archived Python
is imported and no historical receipt is rewritten or re-sealed.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from tools.history import read_checkpoint
from tools.science import prospective_frame as frame


@lru_cache(maxsize=32)
def archived_bytes(relative):
    return read_checkpoint(relative)


def archived_json(relative):
    # Return fresh mutable fixture data; callers cannot alter cached originals.
    return json.loads(archived_bytes(relative))


def restore_protocol_inputs(root):
    """Write exact original input bytes into a new synthetic fixture root."""
    root = Path(root).resolve()
    protocol_bytes = archived_bytes(frame.PROTOCOL)
    protocol = json.loads(protocol_bytes)
    restored = {frame.PROTOCOL: protocol_bytes}
    for parent in protocol['parents']:
        relative = parent['path']
        source = ('tests/fixtures/prospective-frame-metadata/' + Path(relative).name
                  if relative.startswith(frame.METADATA) else relative)
        raw = archived_bytes(source)
        if hashlib.sha256(raw).hexdigest() != parent['sha256']:
            raise AssertionError('Archived prospective parent bytes differ: ' + relative)
        restored[relative] = raw
    for relative, raw in restored.items():
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise AssertionError('Prospective fixture path escaped temporary root')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
    return restored
