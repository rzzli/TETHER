"""Full offline four-arm validation with source pins and hash-only outcome checks."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / 'data/cache/recovery-step9-four-arm-validation-20261026'
CACHE.mkdir(exist_ok=True)
tempfile.tempdir = str(CACHE)
os.environ['TMP'] = os.environ['TEMP'] = str(CACHE)
os.environ['UV_OFFLINE'] = '1'
os.environ['UV_CACHE_DIR'] = str(ROOT/'data/cache/uv-preparation')
os.environ['UV_NO_BUILD_ISOLATION'] = '1'
os.environ['PATH'] = str(ROOT/'data/cache/powershell-7.4.6-portable')+os.pathsep+os.environ['PATH']
sys.path.insert(0,str(ROOT))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pins():
    paths=[p for folder in ('src','tools','tests') for p in (ROOT/folder).rglob('*.py')
           if '__pycache__' not in p.parts]
    paths+=list((ROOT/'src').rglob('*.json'))
    paths+=[ROOT/'pyproject.toml',ROOT/'uv.lock',ROOT/'data/.gitignore']
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(paths))}


protected={
    'data/benchmark/cohorts/science4-outcomes-20261019T024500Z/adjudication/normalized-outcomes.json':
        '9392df7cec11704f3f0abaddc12e4196349ace1aba55b4da0af0f14d41bb26f2',
    'data/benchmark/labels/endpoint-followup-feasibility-20261021/adjudication-v1/normalized-outcomes.json':
        'c3195a27565debe2c0b891f8aecffbae8a63988dfe2fd62b9e5aed37f0353398',
}
assert {n:digest(ROOT/n) for n in protected} == protected
before=pins()
(CACHE/'before-source-pins.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
sys.argv=['tools/validate.py','--mode','full','--package','--report',str(CACHE/'full-validation.json')]
code=0
try:
    runpy.run_path(str(ROOT/'tools/validate.py'),run_name='__main__')
except SystemExit as error:
    code=error.code
except BaseException as error:
    code=1
    (CACHE/'failure.json').write_text(json.dumps(dict(status='failed',error_class=type(error).__name__,
        message=str(error)),indent=2)+'\n',encoding='utf-8')
    raise
finally:
    after=pins()
    protected_after={n:digest(ROOT/n) for n in protected}
    result=dict(exit_code=code,unchanged_code=before==after,source_pins=after,
        protected_hashes=protected_after,protected_unchanged=protected_after==protected,
        status='passed' if code==0 and before==after and protected_after==protected else 'failed')
    (CACHE/'code-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
raise SystemExit(code if result['status']=='passed' else 1)
