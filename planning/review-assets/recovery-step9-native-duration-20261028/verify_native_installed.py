"""Pure installed replay of simulated wrappers with explicit original source/model roots.

Optional relocation denies the original run. This does not restore the raw/model inputs.
No fixture callbacks, executable archive code, child process or HTTP request is used.
"""
from importlib import metadata
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ENV=Path(sys.prefix).resolve()
REPORT=Path(sys.argv[1]).resolve()
RESTORED=Path(sys.argv[2]).absolute() if len(sys.argv)==3 else None
assert sys.flags.isolated and metadata.version('asof-target-agents')=='0.3.10'
assert metadata.version('pyarrow')=='21.0.0' and not REPORT.exists()


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


qualified=json.loads((HERE/'SIMULATION-QUALIFICATION.json').read_bytes())
protocol=json.loads((HERE/'SIMULATION-PROTOCOL.json').read_bytes())
assert qualified['status']=='qualified_real_inputs_simulated_native_case'
assert sha(HERE/'SIMULATION-PROTOCOL.json')==qualified['protocol_sha256']
authority_path=ROOT/protocol['source_authority']['path']
assert sha(authority_path)==protocol['source_authority']['sha256']
authority=json.loads(authority_path.read_bytes())
original=Path(qualified['output'])
roots=dict(project=ROOT,raw=Path(protocol['raw_root']))
model=Path(protocol['model_root'])
allowed={os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/')))) for p in authority['files'].values()}
mirror=json.loads((HERE/'NATIVE-MODEL-MIRROR.json').read_bytes())
assert sha(HERE/'NATIVE-MODEL-MIRROR.json')==protocol['model_mirror_sha256']
model_allowed={os.path.normcase(str(model/p['relative_path'])) for p in mirror['items']}
assert len(allowed)==27 and len(model_allowed)==36
out=original
if RESTORED is not None:
    RESTORED.mkdir(parents=True,exist_ok=False)
    for path in original.rglob('*'):
        assert not path.is_symlink()
        destination=RESTORED/path.relative_to(original)
        if path.is_dir():destination.mkdir(parents=True,exist_ok=True)
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            contents=path.read_bytes()
            with destination.open('xb') as stream:stream.write(contents)
            assert sha(destination)==hashlib.sha256(contents).hexdigest()
    out=RESTORED
assert sha(out/'receipt.json')==qualified['result']['receipt_sha256']
guards=dict(live_code=[],unapproved_source=[],imports=[],dispatch=[],original_bundle=[],unapproved_model=[])


def normalized(path):return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path,root):
    try:return os.path.commonpath([path,normalized(root)])==normalized(root)
    except ValueError:return False


def audit(event,args):
    if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=normalized(args[0])
        if RESTORED is not None and under(path,original):
            guards['original_bundle'].append(path);raise RuntimeError('Original run bundle unavailable')
        if under(path,ROOT/'src') or under(path,ROOT/'.venv'):
            guards['live_code'].append(path);raise RuntimeError('Live source/development environment unavailable')
        if '\\data\\benchmark\\' in path:
            guards['unapproved_source'].append(path);raise RuntimeError('Outcome payloads unavailable')
        if event=='open' and under(path,model) and path not in model_allowed:
            guards['unapproved_model'].append(path);raise RuntimeError('Only explicitly approved model input files')
        if event=='open' and (under(path,ROOT) or path.startswith('e:')):
            mode=args[1] if len(args)>1 else None
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)) or (isinstance(mode,str) and any(c in mode for c in 'wax+'))
            if (path in allowed or path in model_allowed) and writing:
                guards['unapproved_source'].append(path);raise RuntimeError('Original inputs read-only')
            if path not in allowed|model_allowed and not any(under(path,p) for p in (ENV,out,HERE,REPORT.parent)):
                guards['unapproved_source'].append(path);raise RuntimeError('Only approved files and installed environment')
    if event=='exec' and args and not args[0].co_filename.startswith('<') and under(normalized(args[0].co_filename),out):
        guards['imports'].append(args[0].co_filename);raise RuntimeError('Archived code cannot execute')
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        guards['dispatch'].append(event);raise RuntimeError('Read-only replay cannot dispatch')


class NoRepository(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('tools','planning'):
            guards['imports'].append(fullname);raise ImportError('Repository runtime modules unavailable')


sys.meta_path.insert(0,NoRepository())
sys.addaudithook(audit)
from asof.serde import encode
from asof.study.authority_four_arm import verify
import asof.study.authority_four_arm as installed

assert Path(installed.__file__).resolve().is_relative_to(ENV)
started=time.monotonic()
result=encode(verify(out,qualified['result']['receipt_sha256'],source_roots=roots,native_roots={'model':model},deadline=started+299))
assert result==qualified['result'] and not any(guards.values())
assert result['actual_model_calls']==result['native_processes']==0 and result['simulated_native_calls']==6
report=dict(schema_version=1,status='installed_native_simulation_relocation_verified' if RESTORED else 'installed_native_simulation_replay_verified',
    result=result,isolated=True,installed_environment=str(ENV),version='0.3.10',pyarrow_version='21.0.0',
    guards=guards,elapsed_seconds=time.monotonic()-started,model_calls=0,tokenizer_calls=0,network_calls=0,
    explicit_original_input_roots={k:str(v) for k,v in roots.items()},explicit_model_root=str(model),
    original_source_input_count=len(allowed),approved_model_inputs=len(model_allowed),
    original_bundle_reads_denied=str(original) if RESTORED else None,restored=str(RESTORED) if RESTORED else None,
    run_bundle_relocation_only=RESTORED is not None,raw_inputs_restored=False,model_inputs_restored=False,
    archived_code_executed=False,scientific_validation='not_attempted',fixture_callbacks_imported=False)
with REPORT.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],elapsed_seconds=report['elapsed_seconds'],guards=guards)))
