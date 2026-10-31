"""Mirror only existing approved tokenizer assets; originals remain untouched."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

from asof.serde import encode
from asof.study.stable_read import checked_path,deadline_check,hash_file,stable_files
from asof.study.tokenization import _resource

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
resource=_resource()
old=json.loads((HERE/'QUALIFICATION-PROTOCOL-v1.json').read_bytes())
failure=json.loads((HERE/'QUALIFICATION-FAILURE-v1.json').read_bytes())
assert failure['status']=='failed' and failure['error_class']=='TimeoutError'
assert failure['tokenizer_children']==2 and failure['generation_calls']==0
source=Path(old['model_root'])
items=[*resource['assets'],dict(relative_path='acquisition.json',sha256=resource['acquisition_sha256'],bytes=None)]
source_paths={i['relative_path']:checked_path(source,i['relative_path']) for i in items}
expected_bytes=sum(i['bytes'] for i in items if i['bytes'] is not None)
assert len(items)==35 and expected_bytes < 10*1024**3
assert shutil.disk_usage(ROOT).free>expected_bytes*2
suffix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
target=ROOT/'data/cache'/('approved-tokenizer-mirror-'+suffix)
target.mkdir(exist_ok=False)
started=time.monotonic()
deadline=started+1800
report=dict(schema_version=1,role='local_infrastructure_mirror_not_new_acquisition',status='copying',
    source=str(source),target=str(target),items=[],source_writes=False,new_downloads=0,
    generation_calls=0,tokenizer_children=0,network_calls=0,provider_cost_usd=0,
    maximum_seconds=1800,maximum_asset_bytes=10*1024**3)


def save():
    (HERE/'MODEL-MIRROR.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def guard(event,args):
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo'):
        raise RuntimeError('Copy cannot dispatch or use network')
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith('e:'):
            allowed={os.path.normcase(str(p)) for p in source_paths.values()}
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            mode=args[1] if len(args)>1 else None
            assert path in allowed and not flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
            assert not isinstance(mode,str) or not any(c in mode for c in 'wax+')
        assert '\\data\\benchmark\\' not in path


sys.addaudithook(guard)
try:
    save()
    with stable_files(list(source_paths.values()),deadline=deadline):
        for item in items:
            deadline_check(deadline)
            name=item['relative_path']
            destination=target.joinpath(*name.split('/'))
            destination.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256()
            size=0
            before=time.monotonic()
            with source_paths[name].open('rb') as original,destination.open('xb') as copied:
                while True:
                    deadline_check(deadline)
                    chunk=original.read(1024*1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    size+=len(chunk)
                    assert size<10*1024**3
                    copied.write(chunk)
            assert digest.hexdigest()==item['sha256']
            assert item['bytes'] is None or size==item['bytes']
            proof=hash_file(destination,deadline)
            assert proof['sha256']==item['sha256'] and proof['bytes']==size
            report['items'].append(dict(relative_path=name,sha256=proof['sha256'],bytes=size,
                copy_and_destination_verification_seconds=time.monotonic()-before))
            save()
    report.update(status='verified_identical_local_mirror',elapsed_seconds=time.monotonic()-started,
        verified_bytes=sum(i['bytes'] for i in report['items']),asset_count=34,metadata_count=1)
    save()
    print(json.dumps({k:report[k] for k in ('status','target','verified_bytes','elapsed_seconds')}))
except BaseException as error:
    report.update(status='failed',error_class=type(error).__name__,message=str(error),elapsed_seconds=time.monotonic()-started)
    save()
    raise
