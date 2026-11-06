"""Hash-bound restricted loading of the released Lightning checkpoint.

No Lightning import, dynamic pickle-class resolution, or unrestricted fallback.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import math
import os

from .contracts import ContractError, need


def primitive_metadata(value, *, depth=0, budget=None):
    if budget is None:
        budget = [8192]
    budget[0] -= 1
    need(depth <= 12 and budget[0] >= 0, 'Hyperparameter metadata exceeds structural bounds')
    if type(value) is argparse.Namespace:
        value = vars(value)
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        need(math.isfinite(value), 'Non-finite hyperparameter')
        return value
    if type(value) is str:
        need(len(value) <= 32768, 'Hyperparameter string too long')
        return value
    if type(value) in (list, tuple):
        return [primitive_metadata(x, depth=depth+1, budget=budget) for x in value]
    if type(value) is dict:
        need(all(type(k) is str and len(k) <= 1024 for k in value), 'Invalid hyperparameter key')
        return {k: primitive_metadata(v, depth=depth+1, budget=budget) for k, v in value.items()}
    raise ContractError('Unsupported hyperparameter value: ' + type(value).__name__)


def load_checkpoint_state(path, *, expected_sha256, expected_bytes, maximum_bytes=5_500_000_000):
    import torch
    need(type(expected_bytes) is int and 0 < expected_bytes <= maximum_bytes, 'Invalid checkpoint byte bound')
    need(isinstance(expected_sha256, str) and len(expected_sha256) == 64 and
         all(c in '0123456789abcdef' for c in expected_sha256), 'Expected checkpoint SHA256 required')
    with open(path, 'rb') as stream:
        need(os.fstat(stream.fileno()).st_size == expected_bytes, 'Checkpoint length mismatch')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        need(digest == expected_sha256, 'Checkpoint SHA256 mismatch')
        stream.seek(0)
        try:
            unsafe = torch.serialization.get_unsafe_globals_in_checkpoint(stream)
        except Exception as exc:
            raise ContractError('Checkpoint static global inspection failed') from exc
        need(set(unsafe) <= {'argparse.Namespace'}, 'Unsupported checkpoint global: ' + ', '.join(unsafe))
        stream.seek(0)
        try:
            with torch.serialization.safe_globals([argparse.Namespace] if unsafe else []):
                checkpoint = torch.load(stream, map_location='cpu', weights_only=True)
        except Exception as exc:
            raise ContractError('Restricted checkpoint load failed; no unrestricted fallback') from exc
        # Same opened handle, rechecked before the returned tensors can be used.
        stream.seek(0)
        need(hashlib.file_digest(stream, 'sha256').hexdigest() == expected_sha256,
             'Checkpoint changed during restricted load')
    need(type(checkpoint) is dict and isinstance(checkpoint.get('state_dict'), dict), 'Checkpoint lacks state_dict')
    state = dict(checkpoint['state_dict'])
    need(0 < len(state) <= 2000 and all(type(k) is str for k in state), 'Invalid checkpoint state dictionary')
    hyper = primitive_metadata(checkpoint.get('hyper_parameters', {}))
    hparams = hyper.get('hparams', hyper)
    need(type(hparams) is dict, 'Invalid model hyperparameters')
    metadata = dict(sha256=digest, bytes=expected_bytes, unsafe_globals=sorted(unsafe),
                    restricted_weights_only=True, hparams=hparams, state_tensor_count=len(state),
                    optimizer_state_discarded='optimizer_states' in checkpoint)
    del checkpoint
    gc.collect()
    return state, metadata
