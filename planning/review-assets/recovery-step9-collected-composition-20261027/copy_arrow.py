"""Reuse and hash an existing approved Arrow21 install; no download or default-env edit."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=ROOT/'data/cache/recovery-step9-token-aware-wheel-20261026/environment-v2/Lib/site-packages'
target=ROOT/'data/cache/recovery-step9-collected-wheel-20261027/ingestion-environment/Lib/site-packages'
records=[]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


for name in ('pyarrow','pyarrow.libs','pyarrow-21.0.0.dist-info'):
    assert (source/name).is_dir() and not (target/name).exists()
    shutil.copytree(source/name,target/name)
    for path in sorted((source/name).rglob('*')):
        if path.is_file():
            relative=path.relative_to(source)
            expected=sha(path)
            assert sha(target/relative)==expected
            records.append(dict(relative_path=relative.as_posix(),sha256=expected,bytes=path.stat().st_size))
with (HERE/'ARROW-INSTALL.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(schema_version=1,status='copied_and_byte_verified_existing_arrow21',source=str(source),
        target=str(target),files=records,file_count=len(records),bytes=sum(r['bytes'] for r in records),
        new_downloads=0,default_installed_environment_modified=False),stream,indent=2)
print(json.dumps(dict(status='verified_existing_arrow_copy',files=len(records),bytes=sum(r['bytes'] for r in records))))
