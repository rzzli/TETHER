"""Retain a fresh, source-pinned fictional BG04 component test checkpoint.

No native question is loaded, source fetched or model started by this driver.
Tests must use fictional inputs; final source and model rehearsals are separate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
REQUIRED = ('data_views.py', 'retrieval.py', 'native_contract.py',
            'evaluate.py', 'tether_adapter.py', 'model.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 999:
        raise ValueError('Attempt must be 1..999')
    output = BASE / f'components-attempt{args.attempt:02d}'
    output.mkdir(exist_ok=False)
    write(output / 'BEGIN.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                                'python': sys.executable, 'scope': 'fictional tests only'})
    start = time.monotonic()
    try:
        experiment = ROOT / 'experiments/labbench'
        for name in REQUIRED:
            if not (experiment / name).is_file():
                raise ValueError('Missing required component: ' + name)
        files = sorted(experiment.glob('*.py')) + sorted((experiment / 'tests').glob('test*.py'))
        if len(files) <= len(REQUIRED):
            raise ValueError('No fictional test modules')
        files.append(Path(__file__))
        pins = {str(path.relative_to(ROOT)): digest(path) for path in files}
        for path in files:
            target = output / 'sources' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(path.read_bytes())
            if digest(target) != pins[str(path.relative_to(ROOT))]:
                raise ValueError('Source changed during capture')
        temporary = output / 'temp'
        temporary.mkdir()
        cache_prefix = output / 'empty-import-cache'
        cache_prefix.mkdir()
        env = os.environ.copy()
        env.update(TEMP=str(temporary), TMP=str(temporary), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPYCACHEPREFIX=str(cache_prefix),
                   PYTHONPATH=os.pathsep.join(map(str, [ROOT / 'src', ROOT / 'packages/tether/src', ROOT])))
        command = [sys.executable, '-B', '-X', 'pycache_prefix=' + str(cache_prefix),
                   '-m', 'unittest', 'discover', '-s',
                   str(experiment / 'tests'), '-p', 'test*.py', '-v']
        with (output / 'tests.log').open('xb') as log:
            completed = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, timeout=300, check=False)
        after = {str(path.relative_to(ROOT)): digest(path) for path in files}
        raw = (output / 'tests.log').read_bytes()
        match = re.search(rb'Ran (\d+) tests? in ', raw)
        count = int(match.group(1)) if match else 0
        successful = (completed.returncode == 0 and count > 0 and pins == after
                      and not any(cache_prefix.rglob('*'))
                      and re.search(rb'\nOK\s*$', raw) is not None)
        result = {'schema_version': 1, 'status': 'PASS' if successful else 'FAIL',
                  'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                  'command': command, 'returncode': completed.returncode,
                  'tests': count, 'sources_unchanged': pins == after,
                  'source_pins': pins, 'source_pins_after': after,
                  'import_cache_policy': 'Fresh empty prefix with bytecode writes disabled; ordinary source imports do not read pre-existing adjacent caches.',
                  'import_cache_remained_empty': not any(cache_prefix.rglob('*')),
                  'tests_log_sha256': hashlib.sha256(raw).hexdigest(),
                  'elapsed_seconds': time.monotonic() - start,
                  'scope': 'Fictional component tests only; no native benchmark or runtime scientific qualification.'}
        write(output / 'VALIDATION.json', result)
        print(json.dumps({key: result[key] for key in ('status', 'tests', 'sources_unchanged')}))
        if not successful:
            raise RuntimeError('Component qualification failed; retained original attempt')
    except BaseException as error:
        write(output / 'FAILED.json', {'error_type': type(error).__name__,
                                      'elapsed_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
