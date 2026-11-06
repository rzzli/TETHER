"""Receipt-bound offline loading and bounded process observations."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import threading

from .contracts import capture_asset_bytes, need
from .data import ASSET_NAMES, build_tokenizer


def offline_environment():
    for key in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY', 'HF_HUB_DISABLE_XET'):
        os.environ[key] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def receipt_assets(acquisition_root, receipt_sha256):
    root = Path(acquisition_root).resolve()
    raw = (root/'RECEIPT.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest() == receipt_sha256, 'Acquisition receipt SHA256 mismatch')
    receipt = json.loads(raw)
    need(receipt.get('status') == 'PASS', 'Acquisition receipt is not complete')
    files = {}
    for row in receipt['files']:
        need(row.get('status') == 'completed', 'Acquisition contains an incomplete asset')
        key = (row['kind'], row['logical_id'])
        need(key not in files, 'Duplicate acquisition receipt asset')
        path = (root/row['relative_path']).resolve()
        need(path.is_relative_to(root) and path == Path(row['path']).resolve(), 'Acquisition path differs or escapes root')
        files[key] = dict(row, verified_path=path)
    selected = {}
    for name in ASSET_NAMES:
        row = files.get(('tokenizer_config', name)) or files.get(('tokenizer', name))
        need(row is not None, 'Missing tokenizer asset: ' + name)
        need(row['verified_path'] == root/'tokenizer'/name, 'Unexpected tokenizer asset path')
        need(row.get('http_repo_commit') == 'b190dd42e462d2dee634d1162c839710079f97ab',
             'Tokenizer revision differs')
        selected[name] = {'bytes': row['bytes'], 'sha256': row['sha256']}
    checkpoint = files.get(('checkpoint', 'fever_sci.ckpt'))
    need(checkpoint is not None and checkpoint['verified_path'] == root/'checkpoint/fever_sci.ckpt',
         'Missing or unexpected fever_sci checkpoint')
    need(checkpoint['bytes'] == 5253768950, 'Wrong official fever_sci object size')
    need(checkpoint.get('http_version_id') == 'GYe58tFsyvvn1n7rib5H4wrsiq32ZY5Y', 'Wrong fever_sci version')
    return capture_asset_bytes(root/'tokenizer', selected), checkpoint, receipt


def load_components(acquisition_root, receipt_sha256):
    offline_environment()
    from transformers import LongformerConfig
    from .checkpoint import load_checkpoint_state
    from .model import MultiVerS, load_state_strict
    captured, checkpoint, receipt = receipt_assets(acquisition_root, receipt_sha256)
    tokenizer = build_tokenizer(captured)
    config_data = json.loads(captured['config.json'])
    for name, expected in {'hidden_size': 1024, 'num_hidden_layers': 24, 'num_attention_heads': 16,
                           'intermediate_size': 4096, 'max_position_embeddings': 4098, 'vocab_size': 50265}.items():
        need(config_data.get(name) == expected, 'Unexpected released Longformer config: ' + name)
    need(config_data['attention_window'] == [512]*24, 'Unexpected attention windows')
    config_data['vocab_size'] = len(tokenizer)
    config = LongformerConfig(**config_data)
    config._attn_implementation = 'eager'
    state, metadata = load_checkpoint_state(checkpoint['verified_path'], expected_sha256=checkpoint['sha256'],
                                            expected_bytes=checkpoint['bytes'])
    hparams = metadata['hparams']
    need(hparams.get('num_labels', 3) == 3, 'Checkpoint does not use three labels')
    model = MultiVerS(config, label_threshold=hparams.get('label_threshold'),
                     rationale_threshold=hparams.get('rationale_threshold', 0.5))
    load_state_strict(model, state)
    model.eval().requires_grad_(False)
    metadata.update(parameter_count=sum(p.numel() for p in model.parameters()),
                    vocabulary_size=len(tokenizer), force_rationale=False,
                    receipt_sha256=receipt_sha256)
    return model, tokenizer, state, metadata, captured


def configure_device(device):
    import torch
    torch.set_num_threads(4)
    if device.startswith('cuda'):
        need(torch.cuda.is_available(), 'CUDA is unavailable')
        properties = torch.cuda.get_device_properties(device)
        fraction = min(0.9, 14 * 1024**3 / properties.total_memory)
        torch.cuda.set_per_process_memory_fraction(fraction, device=device)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        return dict(device=device, name=properties.name, total_memory=properties.total_memory,
                    allocator_fraction=fraction, tf32=False)
    need(device == 'cpu', 'Only an explicit CPU or CUDA device is permitted')
    return dict(device='cpu')


def process_memory():
    if os.name != 'nt':
        return {'working_set_bytes': None, 'peak_working_set_bytes': None}
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('PageFaultCount', w.DWORD)] + [(key, ctypes.c_size_t) for key in
            ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    fn = psapi.GetProcessMemoryInfo
    fn.argtypes = [w.HANDLE, ctypes.POINTER(Counters), w.DWORD]
    fn.restype = w.BOOL
    value = Counters(); value.cb = ctypes.sizeof(value)
    need(bool(fn(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb)), 'Process memory query failed')
    return dict(working_set_bytes=int(value.WorkingSetSize), peak_working_set_bytes=int(value.PeakWorkingSetSize))


@contextmanager
def hard_deadline(seconds):
    # Qualification uses no worker subprocesses. A controller should additionally
    # enforce an external process deadline, including interpreter startup.
    need(type(seconds) in (int, float) and 0 < seconds <= 1800, 'Invalid deadline')
    timer = threading.Timer(seconds, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
