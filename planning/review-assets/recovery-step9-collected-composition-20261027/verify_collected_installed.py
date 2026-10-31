"""Installed replay or run-bundle relocation with explicitly supplied raw roots.

The original 27 source inputs remain available. This is not a full raw restoration.
Run with the isolated installed Arrow21 environment; never imports archived code.
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
assert sys.flags.isolated and metadata.version('asof-target-agents')=='0.3.7'
assert metadata.version('pyarrow')=='21.0.0' and not REPORT.exists()
qualified=json.loads((HERE/'QUALIFICATION.json').read_bytes())
protocol=json.loads((HERE/'QUALIFICATION-PROTOCOL.json').read_bytes())
assert qualified['status']=='qualified_collected_source_recorded_four_arm'
assert hashlib.sha256((HERE/'QUALIFICATION-PROTOCOL.json').read_bytes()).hexdigest()==qualified['protocol_sha256']
authority_path=ROOT/protocol['source_authority']['path']
assert hashlib.sha256(authority_path.read_bytes()).hexdigest()==protocol['source_authority']['sha256']
authority=json.loads(authority_path.read_bytes())
original=Path(qualified['output'])
roots=dict(project=ROOT,raw=Path(protocol['raw_root']))
allowed={os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
         for p in authority['files'].values()}
out=original
if RESTORED is not None:
    RESTORED.mkdir(parents=True,exist_ok=False)
    for path in original.rglob('*'):
        assert not path.is_symlink()
        destination=RESTORED/path.relative_to(original)
        if path.is_dir():
            destination.mkdir(parents=True,exist_ok=True)
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            contents=path.read_bytes()
            destination.write_bytes(contents)
            assert hashlib.sha256(destination.read_bytes()).digest()==hashlib.sha256(contents).digest()
    out=RESTORED
assert hashlib.sha256((out/'receipt.json').read_bytes()).hexdigest()==qualified['result']['receipt_sha256']
guards=dict(live_code=[],unapproved_source=[],imports=[],dispatch=[],original_bundle=[])


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path,root):
    try:
        return os.path.commonpath([path,normalized(root)])==normalized(root)
    except ValueError:
        return False


def audit(event,args):
    if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=normalized(args[0])
        if RESTORED is not None and under(path,original):
            guards['original_bundle'].append(path)
            raise RuntimeError('Original run bundle unavailable')
        if under(path,ROOT/'src') or under(path,ROOT/'.venv'):
            guards['live_code'].append(path)
            raise RuntimeError('Live source/development environment unavailable')
        if '\\data\\benchmark\\' in path:
            guards['unapproved_source'].append(path)
            raise RuntimeError('Evaluation/outcome payloads unavailable')
        if event=='open' and (under(path,ROOT) or path.startswith('e:')):
            if path not in allowed and not any(under(path,p) for p in (ENV,out,HERE,REPORT.parent)):
                guards['unapproved_source'].append(path)
                raise RuntimeError('Only explicitly pinned source inputs may be opened')
    if event=='exec' and args and not args[0].co_filename.startswith('<') and under(normalized(args[0].co_filename),out):
        guards['imports'].append(args[0].co_filename)
        raise RuntimeError('Archived code cannot execute')
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        guards['dispatch'].append(event)
        raise RuntimeError('Read-only replay cannot dispatch')


class NoRepository(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('tools','planning'):
            guards['imports'].append(fullname)
            raise ImportError('Repository runtime modules unavailable')


sys.meta_path.insert(0,NoRepository())
sys.addaudithook(audit)
from asof.serde import encode
from asof.study.authority_four_arm import verify
import asof.study.authority_four_arm as installed

assert Path(installed.__file__).resolve().is_relative_to(ENV)
started=time.monotonic()
result=encode(verify(out,qualified['result']['receipt_sha256'],source_roots=roots,deadline=started+299))
assert result==qualified['result'] and not any(guards.values())
report=dict(schema_version=1,status='installed_collected_source_relocation_verified' if RESTORED else 'installed_collected_source_replay_verified',
    result=result,isolated=True,installed_environment=str(ENV),version='0.3.7',pyarrow_version='21.0.0',
    guards=guards,elapsed_seconds=time.monotonic()-started,model_calls=0,tokenizer_calls=0,network_calls=0,
    explicit_original_input_roots={k:str(v) for k,v in roots.items()},original_source_input_count=len(allowed),
    original_bundle_reads_denied=str(original) if RESTORED else None,restored=str(RESTORED) if RESTORED else None,
    run_bundle_relocation_only=RESTORED is not None,raw_inputs_restored=False,
    archived_code_executed=False,scientific_validation='not_attempted')
with REPORT.open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],elapsed_seconds=report['elapsed_seconds'],guards=guards)))
