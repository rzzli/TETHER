"""Copy only already approved local assets to a fresh D root; no new download."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

from asof.study import tokenization,native_mode
from asof.study.stable_read import checked_path,stable_files

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
old_report=ROOT/'planning/review-assets/recovery-step9-four-arm-20261026/MODEL-MIRROR.json'
old=json.loads(old_report.read_bytes())
assert old['status']=='verified_identical_local_mirror'
source=Path(old['target'])
resource=tokenization._resource()
server=native_mode._resource()['server']
inventory_path=ROOT/'planning/review-assets/recovery-step5-20261026/inventory.json'
inventory=json.loads(inventory_path.read_bytes())
row=next(a for a in inventory['assets'] if Path(a['path']).name=='llama-server.exe')
assert row['sha256']==server['sha256'] and row['bytes']==server['bytes']
items=[dict(asset=a,source=checked_path(source,a['relative_path'])) for a in resource['assets']]
items.append(dict(asset=server,source=Path(row['path'])))
items.append(dict(asset=dict(relative_path='acquisition.json',sha256=resource['acquisition_sha256'],bytes=(source/'acquisition.json').stat().st_size),source=source/'acquisition.json'))
assert len(items)==36
total=sum(i['asset']['bytes'] for i in items)
assert shutil.disk_usage(ROOT).free>total*2+50*1024*1024
assert not (HERE/'NATIVE-MODEL-MIRROR.json').exists()
out=ROOT/'data/cache'/('approved-native-mirror-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
out.mkdir(exist_ok=False)
report=dict(schema_version=1,status='preparing',target=str(out),items=[],source_writes=False,new_downloads=0,
    prior_mirror_sha256=hashlib.sha256(old_report.read_bytes()).hexdigest(),native_server_resource_sha256=native_mode.RESOURCE_SHA256)
started=time.monotonic()
try:
    with stable_files([i['source'] for i in items],deadline=started+300):
        for item in items:
            asset=item['asset'];src=item['source'];dest=out/asset['relative_path']
            dest.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256();size=0
            with src.open('rb') as inp,dest.open('xb') as output:
                for block in iter(lambda:inp.read(8*1024*1024),b''):
                    output.write(block);digest.update(block);size+=len(block)
                output.flush();os.fsync(output.fileno())
            assert size==asset['bytes'] and digest.hexdigest()==asset['sha256'],src
            with dest.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==asset['sha256']
            report['items'].append(dict(relative_path=asset['relative_path'],source=str(src),sha256=asset['sha256'],bytes=size))
    report.update(status='verified_identical_local_native_mirror',verified_bytes=total,elapsed_seconds=time.monotonic()-started)
except BaseException as error:
    report.update(status='failed',error_class=type(error).__name__,message=str(error),elapsed_seconds=time.monotonic()-started)
    raise
finally:
    with (HERE/'NATIVE-MODEL-MIRROR.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],bytes=total,seconds=report['elapsed_seconds'],target=str(out))))
