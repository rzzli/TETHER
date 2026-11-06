"""Fictional witness that a fresh cache prefix avoids existing usable caches."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import marshal
import os
import struct
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def main():
    root = ROOT / 'data/cache/labbench-cache-policy-attempt01'
    root.mkdir(parents=True, exist_ok=False)
    source = root / 'cache_probe.py'
    source.write_bytes(b"value = 'good'\n")
    cached = Path(importlib.util.cache_from_source(str(source)))
    cached.parent.mkdir()
    # Only a harmless marker differs, while the standard timestamp/size header
    # is valid for the source. No non-fixture bytecode is loaded by this probe.
    wrong_code = compile("value = 'evil'\n", str(source), 'exec')
    header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0,
        int(source.stat().st_mtime) & 0xffffffff, source.stat().st_size)
    cached.write_bytes(header + marshal.dumps(wrong_code))
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.pop('PYTHONPYCACHEPREFIX', None)
    body = 'import cache_probe; print(cache_probe.value)'
    baseline = subprocess.run([sys.executable, '-B', '-c', body], env=env,
                              capture_output=True, timeout=20, check=True)
    assert baseline.stdout.strip() == b'evil', baseline.stdout
    prefix = root / 'empty-prefix'
    prefix.mkdir()
    env['PYTHONPYCACHEPREFIX'] = str(prefix)
    command = [sys.executable, '-B', '-X', 'pycache_prefix=' + str(prefix), '-c',
        'import sys,cache_probe; print(cache_probe.value); print(sys.dont_write_bytecode); print(sys.pycache_prefix)']
    guarded = subprocess.run(command, env=env, capture_output=True, timeout=20, check=True)
    lines = guarded.stdout.decode().splitlines()
    assert lines == ['good', 'True', str(prefix)], lines
    assert not any(prefix.rglob('*'))
    result = {'schema_version': 1, 'status': 'PASS',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.executable, 'python_version': sys.version,
        'baseline_B_only_marker': 'evil', 'fresh_prefix_B_marker': 'good',
        'fresh_prefix_remained_empty': True,
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Ordinary source-backed imports on this interpreter; no claim about explicitly executed sourceless bytecode, stdlib/OS attestation or hostile same-user code.',
        'remaining': 'Actual BG04 launch must use and retain this environment/flag policy.'}
    with (BASE / 'IMPORT-CACHE-POLICY-01.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print('PASS: -B alone can read a usable adjacent cache; fresh empty prefix imports current source.')


if __name__ == '__main__':
    main()
