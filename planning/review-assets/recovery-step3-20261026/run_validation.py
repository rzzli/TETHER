"""Validate the unchanged final recovery implementation; no acquisition or inference."""
import hashlib
import json
import os
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / 'data/cache/recovery-step3-validation-20261026'
CACHE.mkdir(exist_ok=True)
tempfile.tempdir = str(CACHE)
os.environ['TMP'] = os.environ['TEMP'] = str(CACHE)
os.environ['UV_OFFLINE'] = '1'
os.environ['PATH'] = str(ROOT/'data/cache/powershell-7.4.6-portable') + os.pathsep + os.environ['PATH']
sys.path.insert(0, str(ROOT))


def pins():
    paths = [p for folder in ('src', 'tools', 'tests') for p in (ROOT/folder).rglob('*.py')
             if '__pycache__' not in p.parts]
    paths += [ROOT/'pyproject.toml', ROOT/'uv.lock', ROOT/'data/.gitignore',
              ROOT/'src/asof/archive/semantic_dependencies.json']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


before = pins()
sys.argv = ['tools/validate.py', '--mode', 'full', '--package', '--report',
            str(CACHE/'full-validation.json')]
try:
    runpy.run_path(str(ROOT/'tools/validate.py'), run_name='__main__')
except SystemExit as error:
    after = pins()
    result = dict(exit_code=error.code, unchanged_code=before == after,
                  source_pins=after, status='passed' if error.code == 0 and before == after else 'failed')
    (CACHE/'code-validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    raise
except BaseException as error:
    (CACHE/'failure.json').write_text(json.dumps(dict(status='failed', error_class=type(error).__name__,
        message=str(error), source_pins=pins()), indent=2)+'\n', encoding='utf-8')
    raise
