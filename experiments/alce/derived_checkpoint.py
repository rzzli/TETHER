"""Explicit lossless FP32 checkpoint lineage; never an acquisition substitute.

The converter and this independent reader use different tensor implementations.
This reader interprets a restricted stock-PyTorch pickle vocabulary as metadata
only, and compares stored bytes without importing Torch or executing model code.
Future native admission trusts an externally anchored successful derivation audit
and strongly rehashes the derived files. It does not reread original weight bytes.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import importlib
import io
import math
import os
from pathlib import Path
import pickle
import pickletools
import re
import struct
import sys
import zipfile

from tether_engine.serde import canonical, encode, freeze, parse_json
from tether_engine.study.stable_read import stable_files
from tether import _process
from . import native_runtime as runtime
from .data_views import _acquisition_process, _hash, _identity, _logical, _path, _proof, _read, _tick, need

MIB=1024**2
GIB=1024**3
PLAN_KIND='alce_true_derived_plan_v1'
RECEIPT_KIND='alce_true_derived_checkpoint_receipt_v1'
AUDIT_KIND='alce_true_original_shard_audit_v1'
LIMITS=dict(storage_bytes=512*MIB,file_bytes=513*MIB,cache_bytes=64*GIB,
            spool_bytes=12*GIB,minimum_free_disk_bytes=128*GIB)
FAILURES=('FAILURE.json','FAILED.json','DEADLINE.json','RESOURCE-LIMIT.json','SUPERVISOR-FAILED.json')
TENSOR_FIELDS=('dtype','shape','stride','storage_offset','layout','requires_grad')


def _json(proof,deadline,maximum=16*MIB):
    _proof(proof)
    return parse_json(_read(proof,maximum,deadline))


def _package(proof,deadline):
    value=_json(proof,deadline);root=_path(proof['path']).parent
    need(isinstance(value,dict) and isinstance(value.get('files'),dict),'Closed receipt file map required')
    need(not any((root/n).exists() for n in FAILURES),'Failed derivation authority')
    for name,item in value['files'].items():
        _logical(name);need(_proof(item)==root/name,'Receipt member location differs')
        _read(item,64*MIB,deadline)
    return value


def _sources(acquisition,deadline):
    """Admit source identities and small metadata; never hash original weights."""
    receipt=_json(acquisition,deadline);root=_path(acquisition['path']).parent
    need(receipt.get('kind')=='alce_acquisition_receipt_v1' and receipt.get('status')=='verified'
         and type(receipt.get('automatic_retries')) is int and receipt['automatic_retries']==0
         and receipt.get('range_resume') is False and receipt.get('payload_hashes_rechecked') is True,
         'Original completed acquisition required')
    need(not any((root/n).exists() for n in (*FAILURES,'STALLED.json')),'Original acquisition failed')
    manifest=_json(receipt['manifest'],deadline);worker=_json(receipt['worker_receipt'],deadline)
    need(manifest.get('kind')=='alce_acquisition_manifest_v1'
         and worker.get('kind')=='alce_acquisition_worker_receipt_v1'
         and worker.get('status')=='completed' and worker.get('hard_parent_supervision') is True
         and worker.get('manifest')==receipt['manifest'],'Original acquisition lineage differs')
    process=_acquisition_process(receipt['process'],root,manifest['limits']['total_seconds'],deadline)
    rows=manifest['assets'];observed=worker['files']
    need([r['id'] for r in rows]==[r['id'] for r in observed]
         and len({r['id'] for r in rows})==len(rows),'Complete ordered acquisition membership')
    files={};metadata={}
    source_root=root/'payloads/models/true_nli'
    for row,actual in zip(rows,observed):
        need(actual['status']=='completed' and type(actual['attempts']) is int and actual['attempts']==1
             and all(actual[k]==row[k] for k in ('destination','expected_bytes','digest','revision','metadata_proof','rights_reference')),
             'Original acquired member differs')
        if row['product_id']!='true_nli':continue
        name=Path(row['destination']).name
        need(row['destination']=='models/true_nli/'+name and name in runtime.FILES['true_nli']
             and row['revision']==dict(kind='git_commit',value=runtime.MODELS['true_nli'][1]),'Original TRUE revision/member differs')
        path=_path(source_root/name);proof=dict(path=str(path),bytes=row['expected_bytes'],sha256=actual['sha256'])
        _proof(proof)
        need(actual['path']==str(path) and actual['bytes']==proof['bytes'] and path.is_file()
             and path.stat().st_size==proof['bytes'] and name not in files,'Original source location/size differs')
        files[name]=proof
        if row['digest']['kind']=='content':
            need(row['digest']==dict(kind='content',algorithm='sha256',value=proof['sha256']),'Original content digest differs')
        if not name.endswith('.bin'):
            raw=_read(proof,16*MIB,deadline)
            if row['digest']['kind']=='git_blob':
                need(row['digest']==dict(kind='git_blob',algorithm='sha1',value=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()),'Original metadata Git digest differs')
            else:need(row['digest']['kind']=='content','Original digest type differs')
            if name!='pytorch_model.bin.index.json':metadata[name]=proof
    need(set(files)==runtime.FILES['true_nli'] and {p.name for p in source_root.iterdir()}==set(files),
         'Closed original TRUE checkpoint required')
    controls=dict(acquisition=acquisition,manifest=receipt['manifest'],worker=receipt['worker_receipt'],process=process)
    return files,metadata,controls


def _metadata_authority(supervision,inventory,acquisition,deadline):
    outer=_package(supervision,deadline)
    need(outer.get('kind')=='supervised_true_fp32_metadata_receipt_v1'
         and outer.get('status')=='metadata_inventory_complete' and outer.get('inference') is False
         and set(outer['files'])=={'COMMAND.json','PROCESS.json','stdout.bin','stderr.bin'},'Metadata supervision identity')
    command=_json(outer['files']['COMMAND.json'],deadline);process=_json(outer['files']['PROCESS.json'],deadline)
    need(type(process.get('returncode')) is int and process['returncode']==0,'Metadata process failed')
    limits=_process.ProcessLimits(**command['limits'])
    need(0<limits.timeout_seconds<=930 and limits.max_output_bytes==4*MIB,'Metadata process bounds differ')
    stdout=_read(outer['files']['stdout.bin'],4*MIB,deadline);stderr=_read(outer['files']['stderr.bin'],4*MIB,deadline)
    _process.validate_success_report(process['supervision'],limits,len(stdout),len(stderr))
    need(parse_json(stdout)==dict(receipt=outer['child']),'Metadata child receipt differs')
    child=_package(outer['child'],deadline)
    need(child.get('kind')=='true_fp32_metadata_probe_receipt_v1'
         and set(child['files'])=={'REQUEST.json','RESULT.json','INVENTORY.json','RESOURCES.json'}
         and child['files']['INVENTORY.json']==inventory,'Metadata inventory binding differs')
    request=_json(child['files']['REQUEST.json'],deadline);result=_json(child['files']['RESULT.json'],deadline)
    pins=_json(request['pins'],deadline)
    need(pins['acquisition']==acquisition and request['helper']==pins['helper']
         and request['inference'] is False and request['model_instantiation'] is False
         and request['numeric_storage_access_authorized'] is False,'Metadata role/parent differs')
    need(result['status']=='metadata_inventory_complete' and result['inventory']==inventory
         and result['denied_numeric_reads']==[] and result['model_instantiated'] is False
         and result['inference'] is False and result['weights_rehashed'] is False,'Metadata completion differs')
    _read(request['helper'],16*MIB,deadline);_read(command['helper'],16*MIB,deadline)
    expected=[pins['interpreter']['path'],'-I','-B','-X','utf8',request['helper']['path'],'--execute',
              '--pins',request['pins']['path'],'--pins-sha256',request['pins']['sha256'],
              '--output',str(Path(outer['child']['path']).parent)]
    need(command['argv']==expected and result['elapsed_seconds']<=process['supervision']['execution_elapsed_seconds'],
         'Exact metadata command/clock binding differs')
    return result


def _layout(row):
    need(isinstance(row,Mapping) and all(k in row for k in TENSOR_FIELDS),'Complete tensor layout required')
    shape=list(row['shape']);stride=list(row['stride'])
    need(len(shape)==len(stride) and len(shape)<=16 and all(type(x)is int and x>0 for x in shape)
         and all(type(x)is int and x>=0 for x in stride),'Bounded dense tensor shape/stride required')
    expected=[];size=1
    for n in reversed(shape):expected.insert(0,size);size*=n
    need(row['dtype']=='torch.float32' and row['layout']=='torch.strided' and row['storage_offset']==0
         and type(row['storage_offset'])is int and type(row['requires_grad'])is bool
         and stride==expected and size*4<=LIMITS['storage_bytes'],'Only exact contiguous FP32 zero-offset views supported')
    return dict(dtype='torch.float32',shape=shape,stride=stride,storage_offset=0,
                layout='torch.strided',requires_grad=row['requires_grad'])


def prepare_plan(acquisition_proof,inventory_proof,metadata_supervision_proof,*,storage_cap=512*MIB,deadline):
    need(type(storage_cap)is int and storage_cap==LIMITS['storage_bytes'],'Fixed prospective storage packing cap')
    files,metadata,controls=_sources(acquisition_proof,deadline)
    observation=_metadata_authority(metadata_supervision_proof,inventory_proof,acquisition_proof,deadline)
    inventory=_json(inventory_proof,deadline);index_proof=files['pytorch_model.bin.index.json'];index=_json(index_proof,deadline)
    need(inventory['original_index']==index_proof and inventory['original_config']==files['config.json'],
         'Metadata original index/config differs')
    weight_map=index['weight_map'];names=sorted(n for n in files if n.endswith('.bin'))
    need(set(weight_map.values())==set(names) and [r['file'] for r in inventory['shards']]==names,
         'Original shard schedule differs')
    tensors=inventory['tensors'];keys=[r['key'] for r in tensors]
    need(len(keys)==len(set(keys))==len(weight_map) and set(keys)==set(weight_map)
         and observation['key_count']==len(keys) and observation['shard_count']==len(names),'Complete unique tensor membership')
    need(type(index['metadata'].get('total_size'))is int and index['metadata']['total_size']==sum(r['tensor_bytes'] for r in tensors),
         'Original total tensor bytes differ')
    shards=[];global_keys=[];all_outputs=[];aliases={}
    for source in inventory['shards']:
        name=source['file'];rows=[r for r in tensors if r['shard']==name];groups=[];by_offset={}
        need(source['state_dict_metadata'] is None,'Current checkpoint requires semantic null state metadata')
        for ordinal,row in enumerate(rows):
            _layout(row);extent=row['zip_storage']
            need(weight_map[row['key']]==name and row['checkpoint_offset']==extent['offset']
                 and type(extent['offset'])is int and extent['offset']>=0 and type(extent['bytes'])is int
                 and 0<extent['bytes']<=storage_cap and extent['bytes']==math.prod(row['shape'])*4
                 and row['tensor_bytes']==extent['bytes'] and row['view_start_bytes']==0
                 and row['view_span_bytes']==extent['bytes'] and row['contiguous'] is True,
                 'Exact original full-storage layout required')
            offset=extent['offset']
            if offset not in by_offset:
                group=dict(id=len(groups),offset=offset,bytes=extent['bytes'],tensor_ordinals=[])
                groups.append(group);by_offset[offset]=group
            group=by_offset[offset]
            need(group is groups[-1] and group['bytes']==extent['bytes'],'Nonadjacent storage aliases cannot be repacked')
            group['tensor_ordinals'].append(ordinal)
            aliases.setdefault(name+'@'+str(offset),[]).append(row['key'])
        need({(g['offset'],g['bytes']) for g in groups}=={(s['offset'],s['bytes']) for s in source['storage_members']},
             'Unaccounted original storage')
        outputs=[];pending=[];used=0
        for group in groups:
            if pending and used+group['bytes']>storage_cap:
                outputs.append(dict(name=None,group_ids=pending,storage_bytes=used));pending=[];used=0
            pending.append(group['id']);used+=group['bytes']
        if pending:outputs.append(dict(name=None,group_ids=pending,storage_bytes=used))
        need(rows and outputs and files[name]['bytes']<=LIMITS['spool_bytes'],'Bounded nonempty original spool')
        shards.append(dict(name=name,proof=files[name],state_dict_metadata=None,tensors=rows,groups=groups,outputs=outputs))
        global_keys.extend(r['key'] for r in rows);all_outputs.extend(outputs)
    need(global_keys==keys and aliases==inventory['same_storage_aliases'],'Original order/alias inventory differs')
    derived_map={};count=len(all_outputs)
    for ordinal,output in enumerate(all_outputs,1):output['name']=f'pytorch_model-{ordinal:05}-of-{count:05}.bin'
    for shard in shards:
        for output in shard['outputs']:
            for gid in output['group_ids']:
                for i in shard['groups'][gid]['tensor_ordinals']:derived_map[shard['tensors'][i]['key']]=output['name']
    need(sum(g['bytes'] for s in shards for g in s['groups'])<LIMITS['cache_bytes'],'Derived cache byte ceiling')
    return freeze(dict(schema_version=1,kind=PLAN_KIND,product='true_nli',logical_model=runtime.MODELS['true_nli'][0],
        revision=runtime.MODELS['true_nli'][1],acquisition_receipt=acquisition_proof,metadata_inventory=inventory_proof,
        metadata_supervision=metadata_supervision_proof,source_root=str(Path(index_proof['path']).parent),
        source_controls=controls,original_files=files,metadata_files=metadata,original_index=index_proof,
        index_metadata=index['metadata'],derived_index=dict(metadata=index['metadata'],weight_map=derived_map),
        ordered_keys=keys,original_shards=shards,limits=LIMITS))


@dataclass(frozen=True)
class _Storage:
    key:str
    elements:int

@dataclass(frozen=True)
class _Tensor:
    storage:_Storage
    offset:int
    shape:tuple
    stride:tuple
    requires_grad:bool

def _float_storage():
    raise ValueError('Storage class is metadata only')

def _rebuild(storage,offset,shape,stride,requires_grad,backward_hooks,metadata=None):
    need(type(storage)is _Storage and type(offset)is int and type(shape)is tuple and type(stride)is tuple
         and type(requires_grad)is bool and type(backward_hooks)is OrderedDict and not backward_hooks
         and metadata is None,'Unsupported stock tensor pickle schema')
    return _Tensor(storage,offset,shape,stride,requires_grad)

class _MetadataUnpickler(pickle.Unpickler):
    def __init__(self,stream):
        need(type(stream)is io.BytesIO and stream.tell()==0,'Bounded metadata buffer required')
        raw=stream.getvalue();need(len(raw)<=16*MIB,'Bounded checkpoint pickle required')
        # Cached EXT globals bypass find_class in CPython. Stock protocol2
        # tensor checkpoints do not require any registered extension opcode.
        for opcode,_,_ in pickletools.genops(raw):
            need(opcode.name not in {'EXT1','EXT2','EXT4'},'Checkpoint pickle extension opcode forbidden')
        super().__init__(stream)

    def find_class(self,module,name):
        allowed={('collections','OrderedDict'):OrderedDict,('torch','FloatStorage'):_float_storage,
                 ('torch._utils','_rebuild_tensor_v2'):_rebuild}
        need((module,name) in allowed,'Unsupported checkpoint pickle global')
        return allowed[(module,name)]
    def persistent_load(self,value):
        need(type(value)is tuple and len(value)==5 and value[0]=='storage' and value[1] is _float_storage
             and type(value[2])is str and re.fullmatch('[0-9]+',value[2]) and value[3]=='cpu'
             and type(value[4])is int and 0<value[4]<=LIMITS['storage_bytes']//4,'Unsupported FP32 storage metadata')
        return _Storage(value[2],value[4])


def checkpoint_metadata(path,*,deadline,maximum=513*MIB):
    """Restricted metadata decode; never execute Torch or extract archive paths."""
    path=_path(path);before=path.stat();need(0<before.st_size<=maximum,'Bounded checkpoint file required')
    with zipfile.ZipFile(path,'r') as archive:
        infos=archive.infolist();need(0<len(infos)<=4096 and len({r.filename for r in infos})==len(infos),'Unique bounded ZIP members')
        roots={r.filename.split('/')[0] for r in infos};need(len(roots)==1,'Single stock ZIP prefix required')
        prefix=next(iter(roots));_logical(prefix)
        members={};regions=[]
        with path.open('rb') as stream:
            for info in infos:
                _tick(deadline);_logical(info.filename)
                name=info.filename[len(prefix)+1:]
                need(info.filename.startswith(prefix+'/') and info.compress_type==zipfile.ZIP_STORED
                     and not info.flag_bits&1 and info.compress_size==info.file_size,'Stored unencrypted checkpoint ZIP required')
                need(name in {'data.pkl','byteorder','version','.data/serialization_id','.format_version','.storage_alignment'}
                     or re.fullmatch(r'data/[0-9]+',name),'Unknown checkpoint ZIP member')
                stream.seek(info.header_offset);header=stream.read(30)
                need(len(header)==30 and header[:4]==b'PK\x03\x04','Stock local ZIP header required')
                fields=struct.unpack('<4s5H3I2H',header)
                flags,method,crc,compressed,uncompressed=fields[2],fields[3],fields[6],fields[7],fields[8]
                n,e=fields[-2:];local_name=stream.read(n);extra=stream.read(e)
                need(len(local_name)==n and len(extra)==e and flags==info.flag_bits and method==info.compress_type,
                     'Local ZIP flags/method differ from central directory')
                need(local_name.decode('utf-8' if flags&0x800 else 'cp437')==info.orig_filename,
                     'Local ZIP filename differs from central directory')
                # Stock torch.save uses data descriptors with zero local sizes;
                # ZIP64 may instead encode sentinel sizes plus a size extra field.
                sizes=[uncompressed,compressed];expected_sizes=[info.file_size,info.compress_size]
                cursor=0;zip64=None
                while cursor<len(extra):
                    need(cursor+4<=len(extra),'Truncated local ZIP extra field')
                    tag,length=struct.unpack_from('<HH',extra,cursor);cursor+=4
                    need(cursor+length<=len(extra),'Truncated local ZIP extra payload')
                    if tag==1:
                        need(zip64 is None,'Duplicate local ZIP64 metadata');zip64=extra[cursor:cursor+length]
                    cursor+=length
                cursor=0
                for i,size in enumerate(sizes):
                    if size==0xffffffff:
                        need(zip64 is not None and cursor+8<=len(zip64),'Missing local ZIP64 size')
                        sizes[i]=struct.unpack_from('<Q',zip64,cursor)[0];cursor+=8
                descriptor=bool(flags&8)
                need(crc in ((0,info.CRC) if descriptor else (info.CRC,))
                     and all(size in ((0,expected) if descriptor else (expected,)) for size,expected in zip(sizes,expected_sizes)),
                     'Local ZIP CRC/sizes differ from central directory')
                offset=info.header_offset+30+n+e
                need(offset+info.file_size<=archive.start_dir,'Storage overlaps ZIP directory')
                members[name]=dict(offset=offset,bytes=info.file_size)
                end=offset+info.file_size
                if descriptor:
                    stream.seek(end);suffix=stream.read(24)
                    values=[struct.pack('<IQQ',info.CRC,info.compress_size,info.file_size)]
                    if max(info.compress_size,info.file_size)<=0xffffffff:
                        values.append(struct.pack('<III',info.CRC,info.compress_size,info.file_size))
                    forms=[b'PK\x07\x08'+v for v in values]+values
                    lengths=[len(v) for v in forms if suffix.startswith(v)]
                    need(lengths,'ZIP data descriptor differs from central directory');end+=max(lengths)
                need(end<=archive.start_dir,'Local ZIP record overlaps central directory')
                regions.append((info.header_offset,end))
        extents=sorted(members.values(),key=lambda x:x['offset'])
        need(all(a['offset']+a['bytes']<=b['offset'] for a,b in zip(extents,extents[1:])),'Overlapping checkpoint ZIP payloads')
        regions.sort();need(all(a[1]<=b[0] for a,b in zip(regions,regions[1:])),'Overlapping local ZIP records')
        need({'data.pkl','version'}<=set(members) and members['data.pkl']['bytes']<=16*MIB,'Bounded pickle metadata required')
        if 'byteorder' in members:need(archive.read(prefix+'/byteorder')==b'little','Only original little-endian FP32 supported')
        else:need(sys.byteorder=='little','Legacy checkpoint byte order differs')
        raw=archive.read(prefix+'/data.pkl');reader=io.BytesIO(raw);state=_MetadataUnpickler(reader).load()
        need(reader.tell()==len(raw) and type(state) in (dict,OrderedDict) and len(state)<=4096,'Exact bounded state dictionary required')
        need(getattr(state,'_metadata',None) is None and set(getattr(state,'__dict__',{}))<={'_metadata'},'Unexpected state metadata')
        tensors=[];storages={}
        for key,value in state.items():
            need(type(key)is str and key and type(value)is _Tensor and set(value.__dict__)=={'storage','offset','shape','stride','requires_grad'},'Plain tensor members required')
            storage=value.storage;name='data/'+storage.key;need(name in members,'Missing tensor storage')
            extent=members[name];need(extent['bytes']==storage.elements*4,'Storage extent/type length differs')
            row=dict(key=key,dtype='torch.float32',shape=list(value.shape),stride=list(value.stride),storage_offset=value.offset,
                     layout='torch.strided',requires_grad=value.requires_grad,storage_key=storage.key,
                     offset=extent['offset'],bytes=extent['bytes'])
            _layout(row);need(math.prod(value.shape)==storage.elements,'Unexpected storage padding/view')
            tensors.append(row);storages[storage.key]=extent
        need({'data/'+k for k in storages}=={k for k in members if re.fullmatch(r'data/[0-9]+',k)},'Unreferenced checkpoint storage')
    need(_identity(path.stat())==_identity(before),'Checkpoint changed during metadata decode')
    return dict(tensors=tensors,storages=storages,metadata=None)


def _span_hash(path,offset,size,deadline):
    digest=hashlib.sha256();remaining=size
    with Path(path).open('rb') as stream:
        stream.seek(offset)
        while remaining:
            _tick(deadline);block=stream.read(min(MIB,remaining));need(block,'Short checkpoint storage read')
            digest.update(block);remaining-=len(block)
    return digest.hexdigest()


def _hash_and_spans(path,spans,deadline):
    """One bounded sequential pass binds both file bytes and audited raw extents."""
    path=_path(path);before=path.stat()
    need(0<before.st_size<=LIMITS['file_bytes'] and before.st_nlink==1,'Bounded single derived checkpoint required')
    need(type(spans)is list and 0<len(spans)<=4096,'Bounded audited storage list required')
    intervals=[]
    for ordinal,span in enumerate(spans):
        start,size=span['derived_offset'],span['bytes']
        need(type(start)is int and start>=0 and type(size)is int and 0<size<=LIMITS['storage_bytes']
             and start+size<=before.st_size,'Bounded audited storage extent required')
        intervals.append((start,start+size,ordinal))
    intervals.sort();need(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),'Audited storage extents overlap')
    digests=[hashlib.sha256() for _ in spans];whole=hashlib.sha256();position=0;first=0
    with path.open('rb') as stream:
        need(_identity(os.fstat(stream.fileno()))==_identity(before),'Derived file changed before hashing')
        while True:
            _tick(deadline);block=stream.read(MIB)
            if not block:break
            end=position+len(block);need(end<=before.st_size,'Derived file grew while hashing');whole.update(block)
            while first<len(intervals) and intervals[first][1]<=position:first+=1
            i=first
            while i<len(intervals) and intervals[i][0]<end:
                start,stop,ordinal=intervals[i]
                digests[ordinal].update(block[max(start,position)-position:min(stop,end)-position]);i+=1
            position=end
        need(_identity(os.fstat(stream.fileno()))==_identity(before),'Derived file changed while hashing')
    need(position==before.st_size and _identity(path.stat())==_identity(before),'Derived hashing identity differs')
    return dict(path=str(path),bytes=position,sha256=whole.hexdigest()),[h.hexdigest() for h in digests]


def _joined_layout(observed,expected):
    need([r['key'] for r in observed]==[r['key'] for r in expected],'Exact tensor assignment order differs')
    for actual,source in zip(observed,expected):need(_layout(actual)==_layout(source),'Tensor layout/type differs')
    aliases={};expected_aliases={}
    for r in observed:aliases.setdefault(r['storage_key'],[]).append(r['key'])
    for r in expected:expected_aliases.setdefault(r['checkpoint_offset'],[]).append(r['key'])
    need(list(aliases.values())==list(expected_aliases.values()),'Tensor storage alias graph differs')


def verify_spooled_original(plan,original_name,spool_path,cache_paths,*,deadline):
    """Compare independent pickle/layout and raw bytes under existing shared locks.

    The spool is a temporary byte-identical representation, not a permanent
    lineage ancestor. Its full hash must equal the original acquisition proof.
    """
    need(plan['kind']==PLAN_KIND,'Derived plan identity')
    shard=next((s for s in plan['original_shards'] if s['name']==original_name),None)
    need(shard is not None and set(cache_paths)=={o['name'] for o in shard['outputs']},'Exact original cache partition required')
    spool=_path(spool_path);paths={name:_path(p) for name,p in cache_paths.items()}
    need(spool!=_path(shard['proof']['path']) and spool.stat().st_size<=plan['limits']['spool_bytes'],
         'Separate bounded source spool required')
    with stable_files([spool,*paths.values()],deadline=deadline):
        sp=_hash(spool,deadline);need(all(sp[k]==shard['proof'][k] for k in ('bytes','sha256')),'Spool differs from original acquired bytes')
        source=checkpoint_metadata(spool,deadline=deadline,maximum=plan['limits']['spool_bytes'])
        _joined_layout(source['tensors'],shard['tensors'])
        for actual,expected in zip(source['tensors'],shard['tensors']):
            need(actual['offset']==expected['checkpoint_offset'] and actual['bytes']==expected['zip_storage']['bytes'],
                 'Source ZIP extent differs from inventory')
        outputs=[]
        for output in shard['outputs']:
            path=paths[output['name']];need(path.name==output['name'],'Cache filename differs')
            need(path.stat().st_size<=plan['limits']['file_bytes'],'Derived physical file ceiling')
            metadata=checkpoint_metadata(path,deadline=deadline,maximum=plan['limits']['file_bytes'])
            groups=[shard['groups'][i] for i in output['group_ids']]
            expected=[shard['tensors'][i] for g in groups for i in g['tensor_ordinals']]
            _joined_layout(metadata['tensors'],expected);storages=[]
            for group in groups:
                key=shard['tensors'][group['tensor_ordinals'][0]]['key']
                actual=next(r for r in metadata['tensors'] if r['key']==key)
                source_hash=_span_hash(spool,group['offset'],group['bytes'],deadline)
                need(source_hash==_span_hash(path,actual['offset'],actual['bytes'],deadline),'Derived FP32 raw bits differ')
                storages.append(dict(group_id=group['id'],source_offset=group['offset'],derived_offset=actual['offset'],bytes=group['bytes'],sha256=source_hash))
            outputs.append(dict(name=output['name'],proof=_hash(path,deadline),storages=storages,tensors=metadata['tensors']))
        need(_hash(spool,deadline)==sp,'Spool changed during independent audit')
    return freeze(dict(kind=AUDIT_KIND,original_name=original_name,original_proof=shard['proof'],spool_proof=sp,
                       outputs=outputs,key_order=[r['key'] for r in shard['tensors']],metadata=source['metadata']))


def _same(left,right):
    return canonical(encode(left))==canonical(encode(right))


def _closed(root,files):
    expected=set(files)|{'RECEIPT.json'};directories={'checkpoint','audits','scratch'};seen=set()
    for p in root.rglob('*'):
        p=_path(p);name=p.relative_to(root).as_posix()
        if p.is_dir():need(name in directories,'Unknown derived cache directory')
        else:seen.add(name)
    need(seen==expected and all((root/n).is_dir() for n in directories),'Closed derived cache membership differs')


def _journal(proof,expected,deadline):
    raw=_read(proof,4*MIB,deadline);need(raw.endswith(b'\n'),'Complete conversion journal required')
    rows=[];previous='0'*64
    for line in raw.splitlines():
        row=parse_json(line)
        need(set(row)=={'seq','previous_sha256','event','utc','details','sha256'}
             and type(row['seq'])is int and row['seq']==len(rows) and row['previous_sha256']==previous
             and row['sha256']==hashlib.sha256(canonical({k:v for k,v in row.items() if k!='sha256'})).hexdigest(),
             'Conversion journal chain differs')
        rows.append((row['event'],row['details']));previous=row['sha256']
    need(_same(rows,expected),'Exact conversion lifecycle differs')


def _control_closure(plan,receipt_proof,controls,request,installation,deadline):
    """Retain already verified controls for cheap in-call drift checks."""
    source=plan['source_controls']
    values=[receipt_proof,*controls.values(),request['plan'],request['runtime'],installation['interpreter'],
            *installation['sources'].values(),*installation['records'].values(),*installation['torch_sources'].values(),
            installation['psutil_source'],*plan['metadata_files'].values(),plan['original_index'],
            source['acquisition'],source['manifest'],source['worker'],source['process']['proof'],
            *source['process']['streams'].values(),plan['metadata_inventory'],plan['metadata_supervision']]
    outer=_json(plan['metadata_supervision'],deadline);values.extend([outer['child'],*outer['files'].values()])
    child=_json(outer['child'],deadline);values.extend(child['files'].values())
    metadata_request=_json(child['files']['REQUEST.json'],deadline)
    command=_json(outer['files']['COMMAND.json'],deadline)
    values.extend([metadata_request['pins'],metadata_request['helper'],command['helper']])
    unique={}
    for p in values:
        name=str(_proof(p));need(name not in unique or unique[name]==p,'Conflicting lineage control proofs')
        unique[name]=p
    return unique


def _cache_state(plan_proof,receipt_proof,deadline,*,full):
    plan=_json(plan_proof,deadline)
    expected=prepare_plan(plan['acquisition_receipt'],plan['metadata_inventory'],plan['metadata_supervision'],
                          storage_cap=plan['limits']['storage_bytes'],deadline=deadline)
    need(_same(plan,expected),'Derived plan differs from independently reconstructed source metadata')
    receipt=_json(receipt_proof,deadline);root=_path(receipt_proof['path']).parent;cache=root/'checkpoint'
    need(set(receipt)=={'kind','status','plan','cache_root','files','original_audits','resources','source_proofs'}
         and receipt['kind']==RECEIPT_KIND and receipt['status']=='verified_lossless_fp32'
         and receipt['plan']==plan_proof and receipt['cache_root']==str(cache),'Exact derived authority required')
    need(Path(plan_proof['path'])==root/'PLAN.json' and not any((root/n).exists() for n in FAILURES),
         'Successful local derived plan required')
    output_names=[o['name'] for s in plan['original_shards'] for o in s['outputs']]
    checkpoint_names=set(output_names)|set(plan['metadata_files'])|{'pytorch_model.bin.index.json'}
    required={'REQUEST.json','PLAN.json','journal.jsonl','RESOURCES.json','COMPLETE.json',
              *(f'audits/{i:05}.json' for i in range(len(plan['original_shards']))),
              *('checkpoint/'+n for n in checkpoint_names)}
    need(set(receipt['files'])==required and receipt['files']['PLAN.json']==plan_proof
         and receipt['resources']==receipt['files']['RESOURCES.json'],'Exact derivation file membership')
    _closed(root,receipt['files']);files={};controls={};identities={};spanhashes={};audited_outputs={}
    for ap in receipt['original_audits']:
        for out in _json(ap,deadline)['outputs']:
            need(out['name'] in output_names and out['name'] not in audited_outputs,'Unique audited derived file required')
            audited_outputs[out['name']]=out
    need(set(audited_outputs)==set(output_names),'Complete audited derived file schedule')
    for name,p in receipt['files'].items():
        path=_proof(p);need(path==root/name,'Derived member location differs')
        if name.startswith('checkpoint/'):
            identities[path.name]=_identity(path.stat())
            need(path.stat().st_size==p['bytes'],'Derived member size differs')
            if full:
                if path.name in audited_outputs:
                    observed,spanhashes[path.name]=_hash_and_spans(path,audited_outputs[path.name]['storages'],deadline)
                else:observed=_hash(path,deadline)
                need(observed==p,'Derived member content differs')
            files[path.name]=p
        else:_read(p,16*MIB,deadline);controls[name]=p
    need(sum(p['bytes'] for p in files.values())<=plan['limits']['cache_bytes'],'Derived cache byte ceiling')
    for name,source in plan['metadata_files'].items():
        need(all(files[name][k]==source[k] for k in ('bytes','sha256')),'Copied original model metadata differs')
        _read(files[name],16*MIB,deadline)
    need(_json(files['pytorch_model.bin.index.json'],deadline)==plan['derived_index'],'Derived key-to-file index differs')
    request=_json(controls['REQUEST.json'],deadline);complete=_json(controls['COMPLETE.json'],deadline)
    need(set(request)=={'kind','at_utc','plan','local_plan','runtime','output','process_limits','automatic_retries','inference'}
         and request['kind']=='alce_true_fp32_conversion_request_v1' and request['local_plan']==plan_proof
         and request['output']==str(root) and type(request['automatic_retries'])is int and request['automatic_retries']==0
         and request['inference'] is False and _json(request['plan'],deadline)==plan,'Derived request lineage differs')
    process_limits=dict(seconds=9600,process_bytes=4*GIB,minimum_available_host_bytes=4*GIB,cpu_threads=1)
    need(request['process_limits']==process_limits,'Declared conversion bounds differ')
    installation=_json(request['runtime'],deadline)
    need(set(installation)=={'interpreter','sources','records','torch_sources','psutil_source'}
         and installation['sources']==receipt['source_proofs'] and installation['records']
         and set(installation['torch_sources'])=={'torch','torch.serialization','torch._utils'},'Conversion runtime closure differs')
    source_proofs=receipt['source_proofs']
    expected_sources=dict(contract=_hash(Path(__file__).resolve(),deadline),converter=_hash(Path(__file__).with_name('derived_converter.py'),deadline))
    for module_name in ('tether_engine.serde','tether_engine.study.stable_read','tether_engine.study.proofs',
                        'experiments.labbench.runtime','experiments.scifact_multivers_transport.download',
                        'experiments.alce.data_views','experiments.alce.native_runtime','tether._process'):
        expected_sources[module_name]=_hash(Path(importlib.import_module(module_name).__file__).resolve(),deadline)
    need(source_proofs==expected_sources,'Independent validator/converter source identity differs')
    for p in [installation['interpreter'],*source_proofs.values(),*installation['records'].values(),
              *installation['torch_sources'].values(),installation['psutil_source']]:_read(p,16*MIB,deadline)
    need(set(complete)=={'kind','status','plan','original_audits','originals','shards','inference','automatic_retries'}
         and complete['kind']=='alce_true_fp32_conversion_terminal_v1' and complete['status']=='verified_lossless_fp32'
         and complete['plan']==plan_proof and complete['original_audits']==receipt['original_audits']
         and type(complete['originals'])is int and complete['originals']==len(plan['original_shards'])
         and type(complete['shards'])is int and complete['shards']==len(output_names)
         and complete['inference'] is False and type(complete['automatic_retries'])is int
         and complete['automatic_retries']==0,'Derived terminal binding differs')
    resources=_json(receipt['resources'],deadline)
    need(resources['process_limits']==process_limits and resources['storage_limits']==plan['limits']
         and type(resources['wall_seconds']) in (int,float) and math.isfinite(resources['wall_seconds'])
         and 0<=resources['wall_seconds']<process_limits['seconds']
         and type(resources['samples'])is list and len(resources['samples'])>=2,'Conversion resource accounting differs')
    for s in resources['samples']:
        for key in ('rss_bytes','available_host_bytes','cache_bytes','spool_bytes'):
            need(type(s.get(key))is int and s[key]>=0,'Missing conversion resource observation')
        need(s['rss_bytes']<=process_limits['process_bytes'] and s['available_host_bytes']>=process_limits['minimum_available_host_bytes']
             and s['cache_bytes']<=plan['limits']['cache_bytes'] and s['spool_bytes']<=plan['limits']['spool_bytes'],
             'Conversion resource bound exceeded')
    need(len(receipt['original_audits'])==len(plan['original_shards']),'Complete original audit authority')
    events=[('conversion_reserved',dict(plan=plan_proof,output=str(root)))];audit_rows=[]
    for ordinal,(shard,ap) in enumerate(zip(plan['original_shards'],receipt['original_audits'])):
        need(ap==controls[f'audits/{ordinal:05}.json'],'Exact original audit order')
        audit=_json(ap,deadline)
        need(set(audit)=={'kind','original_name','original_proof','spool_proof','outputs','key_order','metadata'}
             and audit['kind']==AUDIT_KIND and audit['original_name']==shard['name']
             and audit['original_proof']==shard['proof'] and audit['metadata'] is None
             and audit['key_order']==[t['key'] for t in shard['tensors']],'Original raw-bit audit lineage differs')
        sp=audit['spool_proof']
        # The successful owned spool was removed; validate its recorded identity without opening it.
        need(set(sp)=={'path','bytes','sha256'} and sp['path']==str(root/'scratch'/shard['name'])
             and all(sp[k]==shard['proof'][k] for k in ('bytes','sha256')),'Transient spool identity differs')
        need(len(audit['outputs'])==len(shard['outputs']),'Complete audited original partition')
        events.extend([('original_copy_entered',dict(ordinal=ordinal,source=shard['proof'])),
                       ('original_copy_verified',dict(ordinal=ordinal,spool=sp))])
        for packed,out in zip(shard['outputs'],audit['outputs']):
            need(set(out)=={'name','proof','storages','tensors'} and out['name']==packed['name']
                 and out['proof']==files[packed['name']] and out['proof']['bytes']<=plan['limits']['file_bytes'],
                 'Audited derived file identity differs')
            metadata=checkpoint_metadata(out['proof']['path'],deadline=deadline,maximum=plan['limits']['file_bytes'])
            need(metadata['tensors']==out['tensors'],'Derived current tensor metadata differs from independent audit')
            groups=[shard['groups'][i] for i in packed['group_ids']]
            tensors=[shard['tensors'][i] for g in groups for i in g['tensor_ordinals']]
            _joined_layout(metadata['tensors'],tensors)
            need(len(out['storages'])==len(groups),'Complete raw-bit storage comparison authority')
            for g,storage in zip(groups,out['storages']):
                tensor=next(t for t in metadata['tensors'] if t['key']==shard['tensors'][g['tensor_ordinals'][0]]['key'])
                need(set(storage)=={'group_id','source_offset','derived_offset','bytes','sha256'}
                     and storage['group_id']==g['id'] and storage['source_offset']==g['offset']
                     and storage['bytes']==g['bytes']==tensor['bytes'] and storage['derived_offset']==tensor['offset']
                     and type(storage['sha256'])is str and re.fullmatch('[0-9a-f]{64}',storage['sha256']),
                     'Exact raw-bit comparison extent/hash required')
            if full:
                need(spanhashes[packed['name']]==[s['sha256'] for s in out['storages']],
                     'Audited storage hashes differ from current derived FP32 bits')
            events.append(('packed_file_written',dict(ordinal=ordinal,file=out['proof'])))
        events.extend([('original_independently_audited',dict(ordinal=ordinal,audit=ap)),
                       ('owned_spool_removed',dict(ordinal=ordinal,path=sp['path']))]);audit_rows.append(ap)
    events.append(('conversion_completed',dict(complete=controls['COMPLETE.json'])))
    _journal(controls['journal.jsonl'],events,deadline)
    provenance=dict(product='true_nli',logical_model=plan['logical_model'],revision=plan['revision'],local_checkpoint=str(cache),
        files=files,acquisition=plan['source_controls'],derived_checkpoint=dict(receipt=receipt_proof,plan=plan_proof,
            original_files=plan['original_files'],metadata_inventory=plan['metadata_inventory'],metadata_supervision=plan['metadata_supervision'],
            original_audits=audit_rows,source_proofs=source_proofs,
            original_numeric_bytes_verification='SHA256-qualified owned spool and independent decoded-layout/raw-FP32-bit audit during cache creation; not freshly reread at native admission',
            current_derived_payload_verification='Strong SHA256 of every derived file at admission and final full revalidation'))
    _closed(root,receipt['files'])
    for name,p in files.items():need(_identity(_path(p['path']).stat())==identities[name],'Derived file changed during validation')
    for p in [receipt_proof,*controls.values()]:_read(p,16*MIB,deadline)
    control_proofs=_control_closure(plan,receipt_proof,controls,request,installation,deadline)
    control_identities={name:_identity(_path(name).stat()) for name in control_proofs}
    return freeze(dict(root=str(root),receipt=receipt_proof,plan=plan,files=files,provenance=provenance,file_identities=identities,
                       control_proofs=control_proofs,control_identities=control_identities))


def verify_cache(plan_proof,receipt_proof,*,deadline):
    """Rehash current cache against externally anchored successful audit authority.

    Does not reread original weight payloads or rerun the historical comparison.
    The receipt SHA must be supplied independently by the operator's release.
    """
    receipt=_json(receipt_proof,deadline)
    with stable_files([_proof(receipt_proof),*(_proof(p) for p in receipt['files'].values())],deadline=deadline):
        return _cache_state(plan_proof,receipt_proof,deadline,full=True)


def verify_asset_provenance(acquisition_receipt,derived_checkpoint,observed,*,deadline):
    """Bounded replay join for explicit derived jobs; no payload hash repetition.

    This binds the reported model to the external receipt and verifies current
    small metadata. Strong cache hashing is performed by DerivedModelAssets at
    execution admission/finalization, not claimed by this receipt replay helper.
    """
    receipt=_json(derived_checkpoint,deadline)
    value=_cache_state(receipt['plan'],derived_checkpoint,deadline,full=False)
    need(_same(value['plan']['acquisition_receipt'],acquisition_receipt),'Original acquisition parent differs')
    need(_same(observed,value['provenance']),'Explicit derived model provenance differs')
    return value['provenance']


def derived_admission(acquisition_receipt,derived_checkpoint,*,deadline):
    """Validate explicit cache authority and protected paths before reservation.

    Metadata-only admission does not replace the constructor's strong hashes.
    """
    receipt=_json(derived_checkpoint,deadline)
    value=_cache_state(receipt['plan'],derived_checkpoint,deadline,full=False)
    plan=value['plan'];need(_same(plan['acquisition_receipt'],acquisition_receipt),'Original acquisition parent differs')
    roots=[value['root'],plan['source_root'],str(Path(plan['metadata_inventory']['path']).parent),
           str(Path(plan['metadata_supervision']['path']).parent)]
    return freeze(dict(plan=receipt['plan'],receipt=derived_checkpoint,protected_roots=roots))


class DerivedModelAssets:
    """Same runtime facade, separately declared lossless cache lineage."""
    def __init__(self,acquisition_receipt,product,*,derived_checkpoint,deadline):
        need(product=='true_nli','Derived checkpoint is restricted to TRUE')
        receipt=_json(derived_checkpoint,deadline)
        state=verify_cache(receipt['plan'],derived_checkpoint,deadline=deadline)
        need(_same(state['plan']['acquisition_receipt'],acquisition_receipt),'Original acquisition parent differs')
        self.root=_path(state['provenance']['local_checkpoint']);self.product=product;self.files=state['files']
        self._state=state;self._fingerprint=hashlib.sha256(canonical(encode(state))).hexdigest()
        self._identities=state['file_identities']

    def provenance(self):return self._state['provenance']

    def revalidate(self,deadline,*,full=False):
        need(hashlib.sha256(canonical(encode(self._state))).hexdigest()==self._fingerprint
             and self.product=='true_nli' and str(self.root)==self._state['provenance']['local_checkpoint']
             and self.files==self._state['files'],'Derived asset facade state changed')
        for name,p in self.files.items():
            need(_identity(_path(p['path']).stat())==self._identities[name],'Derived model identity changed')
        if full:
            observed=verify_cache(self._state['provenance']['derived_checkpoint']['plan'],self._state['receipt'],deadline=deadline)
            need(observed==self._state,'Derived asset authority changed')
        else:
            # Call-time identity checks are drift detection, not another content
            # verification. Complete authority and strong hashes are checked at
            # admission and finalization; replay reconstructs them independently.
            root=_path(self._state['root']);plan=self._state['plan'];source=_path(plan['source_root'])
            receipt=_json(self._state['receipt'],deadline);_closed(root,receipt['files'])
            need(not any((root/n).exists() for n in FAILURES),'Late derived failure marker')
            acq=_path(plan['acquisition_receipt']['path']).parent
            need(not any((acq/n).exists() for n in (*FAILURES,'STALLED.json')),'Late acquisition failure marker')
            _json(plan['acquisition_receipt'],deadline)
            need({p.name for p in source.iterdir()}==set(plan['original_files']),'Original source membership changed')
            for p in plan['original_files'].values():
                need(_path(p['path']).stat().st_size==p['bytes'],'Original retained source size changed')
            for name,identity in self._state['control_identities'].items():
                _tick(deadline);need(_identity(_path(name).stat())==identity,'Derived lineage control identity changed')
