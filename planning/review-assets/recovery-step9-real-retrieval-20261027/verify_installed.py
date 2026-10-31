"""Explicit installed source-inclusive replay with live code and dispatch denied."""
from importlib import metadata
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
qualified=json.loads((HERE/'QUALIFICATION.json').read_bytes())
authority=json.loads((HERE/'SOURCE-AUTHORITY-v1.json').read_bytes())
out=Path(qualified['output'])
roots=dict(project=ROOT,raw=Path(r'E:\projects_data\drug_target_agents_data'))
allowed={os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
         for p in authority['files'].values()}
assert sys.flags.isolated and metadata.version('asof-target-agents')=='0.3.6'
assert metadata.version('pyarrow')=='21.0.0'
guards=dict(live_code=[],unapproved_source=[],imports=[],dispatch=[])


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
        if under(path,ROOT/'src') or under(path,ROOT/'.venv'):
            guards['live_code'].append(path)
            raise RuntimeError('Live source/development environment unavailable')
        if event=='open' and (under(path,ROOT) or path.startswith('e:')):
            if path not in allowed and not any(under(path,p) for p in (ENV,out,HERE,REPORT.parent)):
                guards['unapproved_source'].append(path)
                raise RuntimeError('Only explicitly pinned source inputs may be opened')
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo'):
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
from asof.study.retrieval_preparation import verify_retrieval_preparation

started=time.monotonic()
results=[]
for row in qualified['results']:
    result=encode(verify_retrieval_preparation(out/row['strategy'],row['result']['receipt_sha256'],
        qualified['retrieval_authority_sha256'],roots=roots,deadline=started+299))
    assert result==row['replay']
    results.append(dict(strategy=row['strategy'],result=result))
assert not any(guards.values())
report=dict(schema_version=1,status='installed_source_inclusive_real_retrieval_verified',isolated=True,
    installed_environment=str(ENV),version='0.3.6',pyarrow_version='21.0.0',guards=guards,results=results,
    elapsed_seconds=time.monotonic()-started,model_calls=0,tokenizer_calls=0,network_calls=0,
    archived_code_executed=False,scientific_validation='not_attempted')
with REPORT.open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],elapsed_seconds=report['elapsed_seconds'],guards=guards)))
