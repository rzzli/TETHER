"""Qualify existing import caches without deleting or executing their code.

Python -B suppresses cache writes, not reads. Supplement RECORD source checks
with a bounded inventory and source-compilation equality for current caches.
This is a trusted local-runtime check, not attestation of transient host changes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import marshal
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    roots = [Path(sys.prefix) / 'Lib/site-packages', ROOT / 'experiments/scifact']
    records = []
    for root in roots:
        for path in sorted(root.rglob('*.pyc')):
            raw = path.read_bytes()
            assert 16 <= len(raw) <= 16 * 1024**2 and raw[:4] == importlib.util.MAGIC_NUMBER
            source = Path(importlib.util.source_from_cache(str(path)))
            assert source.is_file() and not source.is_symlink()
            source_raw = source.read_bytes()
            code = marshal.loads(raw[16:])
            assert isinstance(code, types.CodeType)
            optimization = 2 if '.opt-2.' in path.name else 1 if '.opt-1.' in path.name else 0
            expected = compile(source_raw, code.co_filename, 'exec', dont_inherit=True, optimize=optimization)
            flags = int.from_bytes(raw[4:8], 'little')
            assert not flags & ~3, 'Unsupported cache header flags'
            if flags & 1:
                valid_header = not (flags & 2) or raw[8:16] == importlib.util.source_hash(source_raw)
                header_basis = 'unchecked_hash' if not flags & 2 else 'checked_source_hash'
            else:
                stat = source.stat()
                valid_header = (int.from_bytes(raw[8:12], 'little') == int(stat.st_mtime) & 0xffffffff and
                                int.from_bytes(raw[12:16], 'little') == len(source_raw) & 0xffffffff)
                header_basis = 'source_mtime_and_size'
            usable = valid_header and optimization == sys.flags.optimize
            matches = code == expected
            assert not usable or matches, f'Usable import-cache code differs from current source: {path}'
            records.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
                            'source_path': str(source.resolve()), 'source_sha256': hashlib.sha256(source_raw).hexdigest(),
                            'optimization': optimization, 'code_matches_compiled_source': matches,
                            'usable_by_default_interpreter': usable, 'header_validation': header_basis,
                            'status': 'matches_source' if matches else 'stale_cache_ignored_by_interpreter'})
    report = {'schema_version': 1, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS', 'python': sys.version, 'roots': [str(root) for root in roots],
              'cache_files': records, 'scope': 'installed_scientific_and_TETHER_packages_plus_native_task_code',
              'limits': 'Does not attest stdlib/OS files or transient changes; no caches deleted or executed.'}
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'cache_files': len(records), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
