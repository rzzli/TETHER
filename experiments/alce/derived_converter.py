"""One-shot lossless FP32 repacking; conversion is explicit and never runs inference.

Original files are read once under the existing Windows stable-read boundary into
an owned, hash-verified spool. Independent layout/bit audits precede spool deletion.
The derived cache remains a separately identified artifact, not an acquisition.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import gc
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from tether_engine.serde import canonical, encode, parse_json
from tether_engine.study.stable_read import stable_files
from experiments.labbench.runtime import DeadlineWatchdog
from experiments.scifact_multivers_transport.download import Journal, utc, write_new
from .data_views import _hash, _identity, _path, _read, _tick, need
from . import derived_checkpoint as contract

ROOT=Path(__file__).resolve().parents[2]
GIB=1024**3
PROCESS_LIMITS=dict(seconds=9600,process_bytes=4*GIB,minimum_available_host_bytes=4*GIB,cpu_threads=1)


def source_pins(deadline):
    modules=[sys.modules[__name__],contract]
    for name in ('tether_engine.serde','tether_engine.study.stable_read','tether_engine.study.proofs',
                 'experiments.labbench.runtime','experiments.scifact_multivers_transport.download',
                 'experiments.alce.data_views','experiments.alce.native_runtime','tether._process'):
        modules.append(importlib.import_module(name))
    return {('converter' if m is modules[0] else 'contract' if m is contract else m.__name__):
            _hash(Path(m.__file__).resolve(),deadline) for m in modules}


def _put(path,value):
    write_new(path,encode(value))


def _checked_plan(proof,deadline):
    value=parse_json(_read(proof,16*1024**2,deadline))
    expected=contract.prepare_plan(value['acquisition_receipt'],value['metadata_inventory'],
        value['metadata_supervision'],storage_cap=value['limits']['storage_bytes'],deadline=deadline)
    need(canonical(encode(expected))==canonical(value),'Independent packing plan differs')
    return value


def check_import_origin(name,proof,deadline):
    """Bind a top-level dependency's actual origin before its first import."""
    loaded=sys.modules.get(name)
    origin=(getattr(loaded,'__file__',None) if loaded is not None
            else getattr(importlib.util.find_spec(name),'origin',None))
    need(isinstance(origin,str) and _path(origin)==_path(proof['path']),'Pinned dependency import origin differs')
    need(_hash(_path(origin),deadline)==proof,'Pinned dependency import bytes differ')


def spool_original(proof,scratch,*,deadline,maximum):
    """Exclusive copy while original handles deny mutation; one original at a time."""
    source=_path(proof['path']);scratch=_path(scratch)
    need(scratch.is_dir() and not list(scratch.iterdir()),'Empty owned spool directory required')
    need(type(proof['bytes'])is int and 0<proof['bytes']<=maximum,'Original exceeds spool bound')
    target=scratch/source.name
    with stable_files([source],deadline=deadline):
        before=source.stat();need(before.st_size==proof['bytes'],'Original size differs')
        digest=hashlib.sha256();size=0
        with source.open('rb') as src,target.open('xb') as dst:
            need(_identity(os.fstat(src.fileno()))==_identity(before),'Original changed before copy')
            while True:
                _tick(deadline);block=src.read(1024**2)
                if not block:break
                size+=len(block);need(size<=proof['bytes'],'Original grew during copy')
                digest.update(block);dst.write(block)
            dst.flush();os.fsync(dst.fileno())
            need(_identity(os.fstat(src.fileno()))==_identity(before),'Original changed during copy')
        need(_identity(source.stat())==_identity(before),'Original identity changed after copy')
        need(size==proof['bytes'] and digest.hexdigest()==proof['sha256'],'Original-to-spool SHA256 differs')
    result=dict(path=str(target),bytes=size,sha256=digest.hexdigest())
    need(target.stat().st_size==size,'Spool size differs')
    return result


def _storage(torch,stream,group,deadline):
    """Copy raw bytes, then reinterpret; no floating point arithmetic is applied."""
    size=group['bytes'];need(type(size)is int and 0<size<=512*1024**2 and size%4==0,'Bounded FP32 storage required')
    buffer=bytearray(size);view=memoryview(buffer);stream.seek(group['offset']);read=0
    while read<size:
        _tick(deadline);count=stream.readinto(view[read:min(size,read+1024**2)])
        need(type(count)is int and count>0,'Original spool storage is incomplete');read+=count
    # Clone uint8, so even nonfinite FP32 bit patterns are copied without conversion.
    copied=torch.frombuffer(buffer,dtype=torch.uint8).clone()
    del view,buffer
    return copied.view(torch.float32)


def write_pack(torch,spool,original,packed,target,*,deadline,file_limit):
    groups={g['id']:g for g in original['groups']};state=OrderedDict();storages=[]
    need(not target.exists(),'A packed output cannot be retried or overwritten')
    try:
        with spool.open('rb') as stream:
            for group_id in packed['group_ids']:
                group=groups[group_id];storage=_storage(torch,stream,group,deadline);storages.append(storage)
                for ordinal in group['tensor_ordinals']:
                    row=original['tensors'][ordinal]
                    need(row['dtype']=='torch.float32' and row['contiguous'] is True and row['storage_offset']==0,
                         'Qualified contiguous offset-zero FP32 layout required')
                    tensor=storage.as_strided(tuple(row['shape']),tuple(row['stride']),row['storage_offset'])
                    tensor.requires_grad_(row['requires_grad'])
                    need(row['key'] not in state,'Duplicate packed key');state[row['key']]=tensor
        if original['state_dict_metadata'] is not None:state._metadata=original['state_dict_metadata']
        _tick(deadline)
        with target.open('xb') as destination:
            torch.save(state,destination,pickle_protocol=2,_use_new_zipfile_serialization=True)
            destination.flush();os.fsync(destination.fileno())
        need(target.stat().st_size<=file_limit,'Packed file exceeds serialized byte limit')
        return _hash(target,deadline)
    finally:
        state.clear();storages.clear()
        # Scope-local tensors are released when this function returns, before next pack.


def _tree_bytes(root):
    total=0;count=0
    for path in root.rglob('*'):
        path=_path(path)
        if path.is_file():total+=path.stat().st_size;count+=1
        need(count<=4096,'Bounded derived output membership')
    return total


class ResourceGuard:
    def __init__(self,root,limits,sample=None):
        self.root,self.limits,self.sample=root,limits,sample;self.stop=threading.Event();self.values=[];self.error=None
        self.thread=threading.Thread(target=self.poll,daemon=True);self.lock=threading.RLock()
    def capture(self):
        with self.lock:return self._capture()
    def _capture(self):
        if self.sample is None:
            import psutil
            p=psutil.Process();m=p.memory_info()
            value=dict(rss_bytes=m.rss,peak_rss_bytes=getattr(m,'peak_wset',None),
                private_bytes=getattr(m,'private',None),available_host_bytes=psutil.virtual_memory().available,
                cache_bytes=_tree_bytes(self.root/'checkpoint'),spool_bytes=_tree_bytes(self.root/'scratch'))
        else:value=self.sample()
        value=dict(value,at_utc=utc());self.values.append(value)
        need(len(self.values)<=20000,'Converter observation count exceeded')
        for name in ('rss_bytes','available_host_bytes','cache_bytes','spool_bytes'):
            need(type(value.get(name))is int and value[name]>=0,'Exact resource counter required: '+name)
        need(value['rss_bytes']<=PROCESS_LIMITS['process_bytes'],'Converter process memory ceiling')
        need(value['available_host_bytes']>=PROCESS_LIMITS['minimum_available_host_bytes'],'Converter host memory floor')
        need(value['cache_bytes']<=self.limits['cache_bytes'],'Derived cache byte ceiling')
        need(value['spool_bytes']<=self.limits['spool_bytes'],'Owned raw spool byte ceiling')
        return value
    def poll(self):
        while not self.stop.wait(.5):
            try:self.capture()
            except BaseException as error:
                self.error=error
                try:_put(self.root/'RESOURCE-LIMIT.json',dict(reason=str(error),sample=self.values[-1] if self.values else None))
                finally:os._exit(125)
    def __enter__(self):self.capture();self.thread.start();return self
    def __exit__(self,*errors):
        self.stop.set();self.thread.join(2)
        try:
            need(not self.thread.is_alive(),'Converter resource thread did not stop')
            if self.error is not None:raise self.error
            self.capture()
        except BaseException as error:
            if errors and errors[1] is not None:errors[1].add_note('Resource finalization failed: '+type(error).__name__)
            else:raise


def convert(plan_proof,output,runtime_proof,*,torch_loader=None,resource_sample=None):
    """Explicit fresh conversion; caller separately supervises and freezes this process."""
    started=time.monotonic();deadline=started+PROCESS_LIMITS['seconds']
    plan=_checked_plan(plan_proof,deadline)
    runtime=parse_json(_read(runtime_proof,16*1024**2,deadline))
    need(set(runtime)=={'interpreter','sources','records','torch_sources','psutil_source'},'Exact converter runtime pins required')
    need(set(runtime['torch_sources'])=={'torch','torch.serialization','torch._utils'} and runtime['records'],
         'Exact installed Torch execution sources and RECORD pins required')
    need(_hash(Path(sys.executable).resolve(),deadline)==runtime['interpreter'],'Qualified converter interpreter differs')
    for p in [*runtime['sources'].values(),*runtime['records'].values(),*runtime['torch_sources'].values(),runtime['psutil_source']]:
        _read(p,16*1024**2,deadline)
    need(runtime['sources']==source_pins(deadline),'Actual converter/validator/source origins differ')
    check_import_origin('torch',runtime['torch_sources']['torch'],deadline)
    check_import_origin('psutil',runtime['psutil_source'],deadline)
    root=_path(output);approved=ROOT/'data/cache'
    protected=[_path(p['path']).parent for p in (plan_proof,runtime_proof,plan['acquisition_receipt'],
               plan['metadata_inventory'],plan['metadata_supervision'])]+[_path(plan['source_root'])]
    need(root.is_relative_to(approved) and root.parent.is_dir() and not root.exists()
         and all(root!=p and root not in p.parents and p not in root.parents for p in protected),'Fresh protected project output required')
    need(shutil.disk_usage(root.parent).free>=plan['limits']['minimum_free_disk_bytes'],'Insufficient declared conversion disk capacity')
    root.mkdir();checkpoint=root/'checkpoint';scratch=root/'scratch';audits=root/'audits'
    for directory in (checkpoint,scratch,audits):directory.mkdir()
    journal=Journal(root/'journal.jsonl');audit_proofs=[];guard=None;watch=None
    try:
        watch=DeadlineWatchdog(deadline,root/'DEADLINE.json');watch.__enter__()
        _put(root/'PLAN.json',plan);local_plan=_hash(root/'PLAN.json',deadline)
        _put(root/'REQUEST.json',dict(kind='alce_true_fp32_conversion_request_v1',at_utc=utc(),plan=plan_proof,
            local_plan=local_plan,runtime=runtime_proof,output=str(root),process_limits=PROCESS_LIMITS,
            automatic_retries=0,inference=False))
        journal.append('conversion_reserved',plan=local_plan,output=str(root))
        with ResourceGuard(root,plan['limits'],resource_sample) as guard:
            os.environ.update(CUDA_VISIBLE_DEVICES='-1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                HF_ENABLE_PARALLEL_LOADING='false',HF_PARALLEL_LOADING_WORKERS='1',
                OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
            os.environ.update(TEMP=str(scratch),TMP=str(scratch),TMPDIR=str(scratch))
            torch=importlib.import_module('torch') if torch_loader is None else torch_loader()
            need(torch.__version__=='2.7.1+cu128','Pinned stock Torch version required')
            need(not torch.cuda.is_initialized(),'Converter must not initialize CUDA');torch.set_num_threads(1)
            for module_name,p in runtime['torch_sources'].items():
                module=importlib.import_module(module_name)
                need(_hash(Path(module.__file__),deadline)==p,'Actual Torch source path/bytes differ')
            import psutil
            need(_hash(Path(psutil.__file__),deadline)==runtime['psutil_source'],'Actual resource observer source differs')
            for ordinal,original in enumerate(plan['original_shards']):
                _tick(deadline);guard.capture()
                journal.append('original_copy_entered',ordinal=ordinal,source=original['proof'])
                spool_proof=spool_original(original['proof'],scratch,deadline=deadline,maximum=plan['limits']['spool_bytes'])
                spool=_path(spool_proof['path']);spool_identity=_identity(spool.stat())
                journal.append('original_copy_verified',ordinal=ordinal,spool=spool_proof)
                with stable_files([spool],deadline=deadline):
                    paths={}
                    for packed in original['outputs']:
                        paths[packed['name']]=checkpoint/packed['name']
                        p=write_pack(torch,spool,original,packed,paths[packed['name']],deadline=deadline,file_limit=plan['limits']['file_bytes'])
                        journal.append('packed_file_written',ordinal=ordinal,file=p)
                        gc.collect();guard.capture()
                    audit=contract.verify_spooled_original(plan,original['name'],spool,paths,deadline=deadline)
                    audit_path=audits/f'{ordinal:05}.json';_put(audit_path,audit)
                    audit_proof=_hash(audit_path,deadline);audit_proofs.append(audit_proof)
                    journal.append('original_independently_audited',ordinal=ordinal,audit=audit_proof)
                # Only the exact successful owned spool may be removed; never recurse.
                with guard.lock:
                    need(spool.parent==scratch and _identity(_path(spool).stat())==spool_identity,'Owned spool identity changed before cleanup')
                    spool.unlink();journal.append('owned_spool_removed',ordinal=ordinal,path=str(spool))
            for name,p in plan['metadata_files'].items():
                source=_path(p['path']);target=checkpoint/name
                with stable_files([source],deadline=deadline):
                    raw=_read(p,16*1024**2,deadline)
                    with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                need(_hash(target,deadline)==dict(p,path=str(target)),'Copied model metadata bytes differ')
            _put(checkpoint/'pytorch_model.bin.index.json',plan['derived_index'])
            need(not list(scratch.iterdir()),'Successful spool must be empty')
            need(not torch.cuda.is_initialized(),'CUDA unexpectedly initialized')
            for p in [*runtime['sources'].values(),*runtime['records'].values(),*runtime['torch_sources'].values(),runtime['psutil_source']]:
                _read(p,16*1024**2,deadline)
            need(runtime['sources']==source_pins(deadline),'Final executing source origins differ')
            # The resource ceilings cover the final bulk payload hash too.
            checkpoint_files={p.relative_to(root).as_posix():_hash(p,deadline)
                              for p in sorted(checkpoint.iterdir())}
            guard.capture()
        _put(root/'RESOURCES.json',dict(process_limits=PROCESS_LIMITS,storage_limits=plan['limits'],samples=guard.values,
            wall_seconds=time.monotonic()-started,
            scope='Owned process through final bulk cache hashing, before bounded metadata seal; external owner records whole child time. No inference or GPU initialization.'))
        _put(root/'COMPLETE.json',dict(kind='alce_true_fp32_conversion_terminal_v1',status='verified_lossless_fp32',
            plan=local_plan,original_audits=audit_proofs,originals=len(plan['original_shards']),
            shards=sum(len(x['outputs']) for x in plan['original_shards']),inference=False,automatic_retries=0))
        journal.append('conversion_completed',complete=_hash(root/'COMPLETE.json',deadline))
        files=dict(checkpoint_files)
        files.update({p.relative_to(root).as_posix():_hash(p,deadline) for p in sorted(root.rglob('*'))
                      if p.is_file() and p.parent!=checkpoint})
        receipt=dict(kind='alce_true_derived_checkpoint_receipt_v1',status='verified_lossless_fp32',
            plan=local_plan,cache_root=str(checkpoint),files=files,original_audits=audit_proofs,
            resources=files['RESOURCES.json'],source_proofs=runtime['sources'])
        _put(root/'RECEIPT.json',receipt)
        return _hash(root/'RECEIPT.json',deadline)
    except BaseException as error:
        try:_put(root/'FAILURE.json',dict(type=type(error).__name__,reason=str(error)[:2000],
            completed_original_audits=audit_proofs,inference=False,automatic_retries=0,partials_preserved=True))
        except BaseException as capture_error:error.add_note('Conversion failure retention failed: '+type(capture_error).__name__)
        raise
    finally:
        if watch is not None:watch.__exit__(None,None,None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--plan',type=Path)
    parser.add_argument('--plan-sha256');parser.add_argument('--runtime-pins',type=Path)
    parser.add_argument('--runtime-pins-sha256');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    need(args.execute and all((args.plan,args.plan_sha256,args.runtime_pins,args.runtime_pins_sha256,args.output)),'Explicit conversion and externally pinned inputs required')
    end=time.monotonic()+60;plan=_hash(args.plan,end);runtime=_hash(args.runtime_pins,end)
    need(plan['sha256']==args.plan_sha256 and runtime['sha256']==args.runtime_pins_sha256,'External converter input anchor differs')
    print(canonical(dict(receipt=convert(plan,args.output,runtime))).decode(),flush=True)


if __name__=='__main__':main()
