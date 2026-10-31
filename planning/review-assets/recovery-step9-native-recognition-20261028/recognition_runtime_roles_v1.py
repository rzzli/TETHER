"""Exact recognition file roles and deadline-aware leased hashing; no API construction.

Functions receive trusted caller context and typed SDK declarations. Importing this
module performs no file inspection. Only the future separately authorized runtime
caller may open payloads; source-only preparation uses validate_record exclusively.
"""
import hashlib
import math
from pathlib import Path

SMALL_CAP=128*1024**2

def require(value,message):
    if not value:raise RuntimeError(message)

def strict_pin(item):
    require(type(item) is dict and set(item)=={'path','bytes','sha256'},'Exact three-field file descriptor required')
    require(type(item['path']) is str and item['path'] and '\0' not in item['path'],'Malformed descriptor path')
    require(type(item['bytes']) is int and item['bytes']>=0,'Malformed descriptor byte count')
    require(type(item['sha256']) is str and len(item['sha256'])==64 and all(c in '0123456789abcdef' for c in item['sha256']),
            'Malformed descriptor SHA256')
    return item

def validate_record(item,*,software_records,CPU,shards,pack):
    """Pure admission before any stat/open; only exactly three model exceptions."""
    strict_pin(item);require(type(shards) is list and len(shards)==3,'Exactly three ordered model descriptors required')
    expected={}
    for row in software_records:
        strict_pin(row);require(row['bytes']<=SMALL_CAP,'Software cannot use model size exception')
        require(not row['path'].lower().endswith(('.gguf','.pyd')),'Protected/model suffix cannot enter software role')
        require(row['path'] not in expected,'Duplicate software descriptor');expected[row['path']]=(row,SMALL_CAP,'software')
    for role,rows in [('CPU',[CPU]),('pack',[pack]),('model',shards)]:
        for row in rows:
            strict_pin(row);require(row['path'] not in expected,'Software/payload/model role collision')
            cap=row['bytes'] if role=='model' else (20*1024**2 if role=='pack' else SMALL_CAP)
            require(row['bytes']<=cap and (role!='model' or 0<row['bytes']<2**63),'Invalid role-specific size')
            require(row['path'].lower().endswith('.gguf')==(role=='model'),'Model suffix belongs to exact model role only')
            expected[row['path']]=(row,cap,role)
    require(item['path'] in expected and item==expected[item['path']][0],'File outside exact reviewed recognition role')
    row,cap,role=expected[item['path']]
    return dict(role=role,cap=cap,expected_bytes=row['bytes'])

def runtime_path(item,*,role,deadline,check):
    """Inspect only an already admitted original path, within the owner clock."""
    require(type(deadline) in (float,int) and not isinstance(deadline,bool) and math.isfinite(deadline),'Finite runtime deadline required')
    check(deadline);path=Path(item['path'])
    require(path.is_absolute() and str(path)==item['path'] and path.drive.casefold()!='e:','Original canonical path required')
    require('\\data\\benchmark\\' not in str(path).casefold(),'Protected payload forbidden')
    if path.suffix.casefold()=='.gguf':require(role['role']=='model','GGUF only in exact model role')
    for part in (path,*path.parents):
        check(deadline)
        try:status=part.lstat()
        except FileNotFoundError:continue
        require(not getattr(status,'st_file_attributes',0)&0x400,'Reparse ancestry forbidden')
    check(deadline)
    return path

def hash_lease(api,sdk,handle,item,deadline,*,role,records,event):
    """Hash a live original-path read lease. Returned bytes survive late deadlines.

    One bounded record per file, never per chunk. Missing end event means unknown
    tail after its durable reservation, not zero bytes or a successful hash.
    """
    check=sdk.finite_deadline;C=sdk.C
    stage=dict(path=item['path'],role=role['role'],cap=role['cap'],expected_bytes=item['bytes'],
        status='reserved',size_return_observed=False,read_attempts=0,read_returns=0,known_returned_bytes=0,
        hash_updated_bytes=0,pending_read=False,expected_sha256=item['sha256'],hash_complete=False)
    records.append(stage)
    event('recognition_file_hash_reserved',path=item['path'],role=role['role'],expected_bytes=item['bytes'],
          pending_tail='unknown_until_successful_file_hash_return')
    try:
        check(deadline);size=sdk.LARGE_INTEGER()
        ok=api.k.GetFileSizeEx(handle,C.byref(size));stage.update(size_return_observed=True,size_call_ok=bool(ok),
            returned_size=int(size.value) if ok else None)
        check(deadline);api.win(ok,'Read leased size')
        require(size.value==item['bytes'] and 0<=size.value<=role['cap'],'Exact role size changed')
        digest=hashlib.sha256();total=0
        while total<size.value:
            check(deadline);count=min(65536,size.value-total)
            memory,got=C.create_string_buffer(count),sdk.DWORD()
            stage.update(read_attempts=stage['read_attempts']+1,pending_read=True,last_reserved_bytes=count,last_read_return_observed=False)
            ok=api.k.ReadFile(handle,memory,count,C.byref(got),None)
            stage.update(read_returns=stage['read_returns']+1,pending_read=False,last_read_return_observed=True,
                         last_read_ok=bool(ok),last_raw_returned_count=int(got.value),last_count_defined=bool(ok))
            if ok and 0<got.value<=count:
                # Retain/account known data BEFORE any throwing post-return check.
                digest.update(memory.raw[:got.value]);total+=got.value
                stage['known_returned_bytes']+=got.value;stage['hash_updated_bytes']=total
            check(deadline);api.win(ok,'Hash leased original file')
            require(0<got.value<=count,'Leased read incomplete')
        stage['computed_sha256']=digest.hexdigest()
        require(stage['computed_sha256']==item['sha256'],'Leased bytes changed')
        stage.update(status='verified',hash_complete=True)
        event('recognition_file_hash_returned',path=item['path'],role=role['role'],bytes=total,sha256=stage['computed_sha256'])
        check(deadline)
    except BaseException as error:
        stage.update(status='failed',error_class=type(error).__name__,error=str(error)[:512])
        raise
