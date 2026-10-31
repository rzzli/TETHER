"""Build the frozen wheel offline; default and Arrow21 replay environments separate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/'data/cache/recovery-step9-duration-wheel-20261028'
CACHE=ROOT/'data/cache/recovery-step9-duration-validation-20261028'
code=json.loads((CACHE/'code-validation.json').read_bytes())
full=json.loads((CACHE/'full-validation.json').read_bytes())
assert code['status']==full['status']=='passed' and full['tests']==dict(run=1737,failures=0,errors=0,skipped=[])


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


assert len(code['source_pins'])==324 and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
BASE.mkdir(exist_ok=False)
build_temp=ROOT/'data/cache/preparation-build-temp'
build_temp.mkdir(exist_ok=True)
env=dict(os.environ,TEMP=str(build_temp),TMP=str(build_temp),UV_OFFLINE='1')
uv=shutil.which('uv')
assert uv
commands=[]


def call(args):
    with (BASE/f'command-{len(commands):02d}.log').open('x',encoding='utf-8') as stream:
        result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT,env=env)
    commands.append(dict(argv=args,exit_code=result.returncode))
    assert result.returncode==0,commands[-1]


python=str(ROOT/'.venv/Scripts/python.exe')
cache=str(ROOT/'data/cache/uv-preparation')
call([uv,'build','--offline','--no-build-isolation','--python',python,'--cache-dir',cache,'--wheel','--out-dir',str(BASE/'dist')])
wheel=BASE/'dist/asof_target_agents-0.3.10-py3-none-any.whl'
with ZipFile(wheel) as archive:
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
        if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    assert members==expected and all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
for name in ('environment','ingestion-environment'):
    target=BASE/name
    call([uv,'venv','--offline','--cache-dir',cache,'--python',python,str(target)])
    call([uv,'pip','install','--offline','--no-deps','--cache-dir',cache,'--python',str(target/'Scripts/python.exe'),str(wheel)])
arrow_source=ROOT/'data/cache/recovery-step9-token-aware-wheel-20261026/environment-v2/Lib/site-packages'
arrow_target=BASE/'ingestion-environment/Lib/site-packages'
copied=[]
for name in ('pyarrow','pyarrow.libs','pyarrow-21.0.0.dist-info'):
    source=arrow_source/name
    assert source.is_dir() and not (arrow_target/name).exists()
    for path in source.rglob('*'):
        assert not path.is_symlink()
        destination=arrow_target/path.relative_to(arrow_source)
        if path.is_dir():destination.mkdir(parents=True,exist_ok=True)
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            with path.open('rb') as src,destination.open('xb') as dst:shutil.copyfileobj(src,dst)
            digest=sha(path);assert sha(destination)==digest
            copied.append(dict(relative_path=path.relative_to(arrow_source).as_posix(),sha256=digest,bytes=path.stat().st_size))
call([str(BASE/'environment/Scripts/python.exe'),'-I','-c',
    "from importlib.metadata import version, PackageNotFoundError; assert version('asof-target-agents')=='0.3.10'; "
    "import importlib.util; assert importlib.util.find_spec('pyarrow') is None"])
call([str(BASE/'ingestion-environment/Scripts/python.exe'),'-I','-c',
    "from importlib.metadata import version; assert version('asof-target-agents')=='0.3.10'; assert version('pyarrow')=='21.0.0'; import pyarrow"])
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
report=dict(schema_version=1,status='offline_wheel_and_two_installed_environments_verified',version='0.3.10',
    wheel=str(wheel),wheel_sha256=sha(wheel),wheel_runtime_resources_checked=len(expected),
    default_python=str(BASE/'environment/Scripts/python.exe'),
    ingestion_python=str(BASE/'ingestion-environment/Scripts/python.exe'),
    default_runtime_dependencies=[],optional_pyarrow_version='21.0.0',new_downloads=0,
    copied_existing_arrow_files=copied,copied_arrow_bytes=sum(p['bytes'] for p in copied),commands=commands,
    source_pins_unchanged=len(code['source_pins']))
with (HERE/'WHEEL-ENVIRONMENTS.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ('status','wheel_sha256','wheel_runtime_resources_checked','source_pins_unchanged')}))
