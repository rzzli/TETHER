"""One fresh, bounded native evaluator process; never an automatic retry route."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import math
import os
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
for directory in (ROOT/'packages/tether/src',ROOT/'src',ROOT):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))

from tether import _process as processes
from tether_engine.serde import canonical, encode, parse_json
from experiments.labbench.runtime import DeadlineWatchdog, contain_process_tree, process_sample
from experiments.scifact_multivers_transport.download import Journal, utc, write_new as _write_new
from experiments.alce.data_views import _path, _hash, _read, _tick, need
from experiments.alce.offline import OfflineNetworkGuard
from experiments.alce import native_runtime as runtime

MAX_JOB=16*1024**2


def write_new(path,value):
    # Decode immutable serializer containers before exclusive file creation.
    value=encode(value);canonical(value)
    _write_new(path,value)


class OutputBudget:
    """One aggregate ceiling for normal receipts, results and journal bytes."""
    def __init__(self,maximum):self.maximum,self.used=maximum,0
    def reserve(self,size):
        need(type(size)is int and 0<=size<=self.maximum-self.used,'Aggregate native output byte ceiling')
    def write(self,path,value):
        raw=canonical(encode(value))+b'\n';self.reserve(len(raw))
        write_new(path,value);self.used+=len(raw)
    def append(self,path,raw):
        self.reserve(len(raw))
        with path.open('ab') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self.used+=len(raw)


class NativeJournal:
    def __init__(self,path,budget):
        self.path,self.budget=path,budget;self.seq=0;self.previous='0'*64
        with path.open('xb'):pass
    def append(self,event,**details):
        row=dict(seq=self.seq,previous_sha256=self.previous,event=event,utc=utc(),details=details)
        row['sha256']=hashlib.sha256(canonical(row)).hexdigest()
        raw=canonical(row)+b'\n';need(len(raw)<=2*1024**2,'Native journal event ceiling')
        self.budget.append(self.path,raw);self.seq+=1;self.previous=row['sha256']


def journal_rows(proof,maximum,deadline):
    """Stream a complete proof-bound journal with bounded lines and file size."""
    path=_path(proof['path']);before=path.stat()
    need(type(proof['bytes'])is int and 0<proof['bytes']<=maximum and before.st_size==proof['bytes'],'Bounded native journal proof')
    from experiments.alce.data_views import _identity
    seq=0;previous='0'*64;digest=hashlib.sha256();total=0
    with path.open('rb') as stream:
        need(_identity(os.fstat(stream.fileno()))==_identity(before),'Journal changed before replay')
        while True:
            _tick(deadline);line=stream.readline(2*1024**2+1)
            if not line:break
            need(len(line)<=2*1024**2 and line.endswith(b'\n'),'Bounded complete journal line required')
            total+=len(line);need(total<=proof['bytes'],'Journal grew during replay');digest.update(line)
            row=parse_json(line)
            need(set(row)=={'seq','previous_sha256','event','utc','details','sha256'} and type(row['seq'])is int
                 and row['seq']==seq and row['previous_sha256']==previous and
                 row['sha256']==hashlib.sha256(canonical({k:v for k,v in row.items() if k!='sha256'})).hexdigest(),
                 'Native journal chain differs')
            seq+=1;previous=row['sha256'];yield row
        need(_identity(os.fstat(stream.fileno()))==_identity(before),'Journal changed during replay')
    need(total==proof['bytes'] and digest.hexdigest()==proof['sha256'] and _identity(path.stat())==_identity(before),
         'Native journal byte binding differs')


def source_pins():
    paths=[Path(__file__).resolve(),Path(runtime.__file__).resolve(),ROOT/'experiments/alce/offline.py',
        ROOT/'experiments/alce/data_views.py',ROOT/'experiments/alce/native_metrics.py',
        ROOT/'experiments/labbench/runtime.py',ROOT/'experiments/scifact_multivers_transport/download.py',
        ROOT/'src/tether_engine/serde.py',ROOT/'packages/tether/src/tether/_process.py']
    end=time.monotonic()+60
    return {p.relative_to(ROOT).as_posix():_hash(p,end) for p in paths}


def load_job(proof):
    end=time.monotonic()+60
    value=parse_json(_read(proof,MAX_JOB,end))
    need(set(value)=={'schema_version','kind','operation','purpose','acquisition_receipt','inputs','output',
         'interpreter','offline','limits','placement','native_sources','code_pins','runtime_sources'},'Exact native job schema')
    need(type(value['schema_version'])is int and value['schema_version']==1 and value['kind']=='alce_native_job_v1'
         and value['operation'] in ('true','qa','mauve') and value['purpose'] in ('qualification','evaluation'),'Native job identity')
    need(value['code_pins']==source_pins(),'Executing native worker source closure differs')
    limits=value['limits']
    keys={'seconds','process_bytes','minimum_available_host_bytes','gpu_bytes','offload_bytes','max_calls','input_bytes','output_bytes','cpu_threads'}
    need(type(limits)is dict and set(limits)==keys and all(type(v)is int and v>0 for v in limits.values()),'Explicit positive native bounds')
    need(limits['seconds']<=86400 and limits['max_calls']<=1_000_000 and limits['input_bytes']<=256*1024**2
         and limits['output_bytes']<=1024**3 and limits['cpu_threads']<=64,'Native operation ceiling')
    need(type(value['runtime_sources'])is dict and value['runtime_sources'],'Explicit installed runtime sources required')
    for p in [value['interpreter'],*value['offline'].values(),*value['runtime_sources'].values(),*value['native_sources'].values()]:
        _read(p,256*1024**2,end)
    need(set(value['offline'])=={'record','connection'},'Exact offline guard controls')
    input_path=_path(value['inputs']['path']);output=_path(value['output'])
    root=_path(value['acquisition_receipt']['path']).parent
    protected=[root,_path(proof['path']),input_path,*(Path(p['path']) for p in value['runtime_sources'].values()),
               *(Path(p['path']) for p in value['offline'].values()),*(Path(p['path']) for p in value['native_sources'].values())]
    need(output.parent.is_dir() and not output.exists() and all(output!=p and output not in p.parents and p not in output.parents for p in protected),
         'Fresh native output must not overlap inputs, assets or runtime')
    rows=parse_json(_read(value['inputs'],limits['input_bytes'],end))
    need(isinstance(rows,list) and rows and len(rows)<=limits['max_calls'],'Bounded nonempty native input schedule')
    need(all(isinstance(row,dict) and type(row.get('id'))is str and row['id'] for row in rows)
         and len({row['id'] for row in rows})==len(rows),'Unique ordered native request IDs')
    return value,rows


def host_available():
    if os.name!='nt':return None
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                  *[(name,ctypes.c_ulonglong) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]]
    value=Memory();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):return None
    return int(value.available)


def resource_sample(offload):
    memory=process_sample(os.getpid())
    total=0;count=0
    if offload.exists():
        for p in offload.rglob('*'):
            _path(p)
            if p.is_file():total+=p.stat().st_size;count+=1
            need(count<=100000,'Bounded weight-offload membership')
    return dict(process_bytes=None if memory is None else memory['working_set_bytes'],
                process_peak_bytes=None if memory is None else memory['process_peak_working_set_bytes'],
                cpu_seconds=None if memory is None else memory['cpu_seconds'],
                available_host_bytes=host_available(),offload_bytes=total,offload_files=count)


def check_resources(sample,limits):
    for name in ('process_bytes','available_host_bytes','offload_bytes'):
        need(type(sample.get(name))is int and sample[name]>=0,'Required resource observation unavailable: '+name)
    need(sample['process_bytes']<=limits['process_bytes'],'Native process memory ceiling')
    need(sample['available_host_bytes']>=limits['minimum_available_host_bytes'],'Native host-memory headroom exhausted')
    need(sample['offload_bytes']<=limits['offload_bytes'],'Native weight-offload byte ceiling')


class ResourceWatchdog:
    """Measured abort guard, not an OS allocation quota; unknown samples stop work."""
    def __init__(self,output,limits,*,sample=None,terminate=os._exit):
        self.output,self.limits=output,limits
        self.sample=sample or (lambda:resource_sample(output/'offload'))
        self.terminate=terminate;self.stop=threading.Event();self.values=[];self.error=None
        self.thread=threading.Thread(target=self.poll,daemon=True)
    def capture(self):
        value=self.sample();check_resources(value,self.limits)
        if len(self.values)<172802:self.values.append(value)
        else:raise ValueError('Resource observation count exceeded')
        return value
    def poll(self):
        while not self.stop.wait(.5):
            try:self.capture()
            except BaseException as error:
                self.error=error
                try:write_new(self.output/'RESOURCE-LIMIT.json',dict(status='failed',error_type=type(error).__name__,reason=str(error),automatic_retries=0))
                finally:self.terminate(125)
                return
    def __enter__(self):self.capture();self.thread.start();return self
    def __exit__(self,*unused):
        self.stop.set();self.thread.join(2)
        try:
            need(not self.thread.is_alive(),'Resource sampler did not stop')
            if self.error is not None:raise self.error
            self.capture()
        except BaseException as error:
            if unused and unused[1] is not None:unused[1].add_note('Resource finalization failed: '+type(error).__name__)
            else:raise


def execute(job_proof,*,module_loader=runtime.dependencies,asset_loader=runtime.ModelAssets,resource_sampler=None):
    started=time.monotonic();job,rows=load_job(job_proof)
    # The running interpreter may be a venv symlink. Only this process-reported
    # identity is resolved; supplied interpreter proofs still require regular paths.
    need(_path(Path(sys.executable).resolve(strict=True))==_path(job['interpreter']['path']),
         'Worker interpreter differs from qualified environment')
    output=_path(job['output']);output.mkdir()
    budget=OutputBudget(job['limits']['output_bytes'])
    journal=NativeJournal(output/'journal.jsonl',budget);deadline=started+job['limits']['seconds']
    guard=None;adapter=None;watch=None
    def emit(event,value):journal.append(event,**encode(value))
    try:
        budget.write(output/'REQUEST.json',dict(job=job_proof,code_pins=job['code_pins'],scope='one native worker; no automatic retry'))
        emit('native_worker_reserved',dict(operation=job['operation'],purpose=job['purpose'],ids=[r['id'] for r in rows]))
        with DeadlineWatchdog(deadline,output/'DEADLINE.json'), ResourceWatchdog(output,job['limits'],sample=resource_sampler) as watch:
            guard=OfflineNetworkGuard(job['offline']['record'],job['offline']['connection']).install()
            for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_TELEMETRY'):
                os.environ[key]='1'
            for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
                os.environ[key]=str(job['limits']['cpu_threads'])
            modules=module_loader(include_mauve=job['operation']=='mauve')
            actual=runtime.loaded_modules(modules,deadline)
            need(actual==job['runtime_sources'],'Actual imported evaluator module paths/bytes differ')
            need(modules['torch'].cuda.is_available(),'Explicit CUDA native evaluator required')
            modules['torch'].set_num_threads(job['limits']['cpu_threads'])
            available=modules['torch'].cuda.get_device_properties(0).total_memory
            need(job['limits']['gpu_bytes']<=available,'GPU allocator ceiling exceeds hardware')
            modules['torch'].cuda.set_per_process_memory_fraction(job['limits']['gpu_bytes']/available,0)
            assets=asset_loader(job['acquisition_receipt'],dict(true='true_nli',qa='qa_roberta',mauve='gpt2_large')[job['operation']],deadline=deadline)
            common=dict(deadline=deadline,emit=emit)
            if job['operation']=='true':adapter=runtime.TrueRuntime(assets,modules,max_memory=job['placement'],offload_root=output/'offload',**common)
            elif job['operation']=='qa':adapter=runtime.QARuntime(assets,modules,**common)
            else:adapter=runtime.MauveRuntime(assets,modules,**common)
            (output/'results').mkdir();results=[]
            if job['operation']=='mauve':
                result=adapter.metric(rows,job['native_sources']);calls=[dict(id='full-family',result=result)]
            else:
                calls=[]
                for row in rows:
                    _tick(deadline)
                    if job['operation']=='true':result=adapter(row['request'])
                    else:
                        answer=adapter.pipeline('question-answering',model=runtime.MODELS['qa_roberta'][0],device=0)
                        result=answer(**row['request'])
                    # Durable per-request outputs precede any subsequent dispatch.
                    data=dict(id=row['id'],result=result)
                    path=output/'results'/f'{len(results):06}.json';budget.write(path,data)
                    results.append(_hash(path,deadline))
            for data in calls:
                path=output/'results'/f'{len(results):06}.json';budget.write(path,data);results.append(_hash(path,deadline))
            snapshot=guard.snapshot()
            need(snapshot['denied_network_attempts']==0 and snapshot['dropped_event_records']==0,'Offline runtime attempted forbidden network operation')
            assets.revalidate(deadline,full=True)
            need(job['code_pins']==source_pins(),'Native source changed before completion')
            _read(job_proof,MAX_JOB,deadline);_read(job['inputs'],job['limits']['input_bytes'],deadline)
            emit('native_worker_completed',dict(result_count=len(results),elapsed_seconds=time.monotonic()-started))
        budget.write(output/'COMPLETE.json',dict(status='completed',operation=job['operation'],purpose=job['purpose'],
            job=job_proof,result_files=results,native=adapter.report(),offline=snapshot,
            resource_samples=watch.values,wall_seconds=time.monotonic()-started,automatic_retries=0,
            memory_scope='Measured host/process/offload guard and CUDA allocator cap; not an OS-wide allocation bound.',
            offload_scope='Derived disposable weight staging retained separately; never source evidence.'))
        files={p.relative_to(output).as_posix():_hash(p,deadline) for p in sorted(output.rglob('*')) if p.is_file() and not p.is_relative_to(output/'offload')}
        budget.write(output/'WORKER-RECEIPT.json',dict(kind='alce_native_worker_receipt_v1',status='completed',files=files))
        return _hash(output/'WORKER-RECEIPT.json',deadline)
    except BaseException as error:
        try:write_new(output/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,reason=str(error)[:2000],
            wall_seconds=time.monotonic()-started,automatic_retries=0,native=None if adapter is None else adapter.report(),
            offline=None if guard is None else guard.snapshot()))
        except BaseException as persistence:error.add_note('Worker failure retention failed: '+type(persistence).__name__)
        raise
    finally:
        if guard is not None:guard.close()


def verify_worker(worker,job_proof,job,rows,deadline):
    for name in ('FAILURE.json','DEADLINE.json','RESOURCE-LIMIT.json'):
        need(not (worker/name).exists(),'Worker terminal contradiction')
    rp=_hash(worker/'WORKER-RECEIPT.json',deadline)
    receipt=parse_json(_read(rp,MAX_JOB,deadline))
    count=1 if job['operation']=='mauve' else len(rows)
    expected={'REQUEST.json','journal.jsonl','COMPLETE.json',*(f'results/{i:06}.json' for i in range(count))}
    need(receipt['kind']=='alce_native_worker_receipt_v1' and receipt['status']=='completed' and set(receipt['files'])==expected,'Complete native worker membership')
    actual=set()
    for path in worker.rglob('*'):
        _path(path)
        if path.is_relative_to(worker/'offload'):continue
        if path.is_file():actual.add(path.relative_to(worker).as_posix())
        else:need(path==worker/'results','Unknown native output directory')
    need(actual==expected|{'WORKER-RECEIPT.json'},'Closed native result files')
    need(sum((worker/name).stat().st_size for name in actual)<=job['limits']['output_bytes'],'Aggregate retained native output ceiling')
    for name,p in receipt['files'].items():need(Path(p['path'])==worker/name and _hash(worker/name,deadline)==p,'Worker result changed')
    request=parse_json(_read(receipt['files']['REQUEST.json'],MAX_JOB,deadline))
    need(request['job']==job_proof and request['code_pins']==job['code_pins'],'Native request authority differs')
    complete=parse_json(_read(receipt['files']['COMPLETE.json'],job['limits']['output_bytes'],deadline))
    need(complete['job']==job_proof and complete['status']=='completed' and complete['operation']==job['operation']
         and complete['purpose']==job['purpose'] and type(complete['automatic_retries'])is int and complete['automatic_retries']==0,'Worker job identity')
    need(type(complete['wall_seconds'])in(int,float) and 0<=complete['wall_seconds']<job['limits']['seconds'],'Native worker total clock')
    need(complete['result_files']==[receipt['files'][f'results/{i:06}.json'] for i in range(count)],'Ordered native result proofs')
    samples=complete['resource_samples']
    need(isinstance(samples,list) and len(samples)>=2,'Initial and final resource observations required')
    for sample in samples:check_resources(sample,job['limits'])
    result_values=[]
    for i in range(count):
        row=parse_json(_read(receipt['files'][f'results/{i:06}.json'],job['limits']['output_bytes'],deadline))
        need(set(row)=={'id','result'} and row['id']==('full-family' if job['operation']=='mauve' else rows[i]['id']),'Full native result schedule')
        if job['operation']=='true':need(type(row['result'])is int and row['result'] in (0,1),'Typed native TRUE verdict required')
        result_values.append(row['result'])
    native=complete['native'];calls=native['calls']
    need(native['failed'] is False and native['automatic_retries']==0 and native['runtime_sources']==job['runtime_sources']
         and len(calls)==count,'Complete native runtime accounting')
    expected_requests=[rows] if job['operation']=='mauve' else [row['request'] for row in rows]
    for i,call in enumerate(calls):
        need(call['ordinal']==i and call['status']=='completed' and call['error_type'] is None
             and call['request_sha256']==hashlib.sha256(canonical(expected_requests[i])).hexdigest(),'Native request/accounting join')
        need(type(call['elapsed_seconds'])in(int,float) and math.isfinite(call['elapsed_seconds'])
             and 0<=call['elapsed_seconds']<=complete['wall_seconds'],'Native call/worker clock binding')
    need(sum(c['elapsed_seconds'] for c in calls)<=complete['wall_seconds'],'Sequential native calls exceed worker clock')
    gpu=native['gpu']
    need(gpu.get('available') is True and all(type(gpu.get(k))is int and 0<=gpu[k]<=job['limits']['gpu_bytes']
         for k in ('peak_allocated_bytes','peak_reserved_bytes')),'Known GPU peaks within native allocation ceiling required')
    need(complete['offline']['denied_network_attempts']==0 and complete['offline']['dropped_event_records']==0,'Native offline denial')
    entered=completed=observed=true_observed=0;first=last=None;finished=False
    for event in journal_rows(receipt['files']['journal.jsonl'],job['limits']['output_bytes'],deadline):
        if first is None:first=event
        need(not finished and not event['event'].endswith('failed'),'Native journal contradicts completion')
        if event['event']=='call_entered':
            need(entered==completed and entered<count and event['details']['ordinal']==entered,'Ordered native call reservation')
            need(event['details']==dict(calls[entered],status='entered',elapsed_seconds=None,error_type=None),'Reserved native request differs')
            entered+=1
        elif event['event']=='native_result_observed':
            need(entered==completed+1 and observed==completed and event['details']==dict(ordinal=completed,
                 kind=calls[completed]['kind'],result_sha256=hashlib.sha256(canonical(result_values[completed])).hexdigest()),
                 'Captured native result differs from published result')
            observed+=1
        elif event['event']=='true_generation_observed':
            details=event['details']
            need(job['operation']=='true' and entered==completed+1 and true_observed==completed
                 and details['ordinal']==completed and type(details['decoded_text'])is str
                 and type(details['entailment'])is int and details['entailment']==int(details['decoded_text']=='1')
                 and details['entailment']==result_values[completed],'Literal TRUE decoded verdict differs')
            true_observed+=1
        elif event['event']=='call_completed':
            need(entered==completed+1 and observed==entered and event['details']==calls[completed],
                 'Native journal/call reconciliation')
            completed+=1
        elif event['event']=='native_worker_completed':finished=True
        last=event
    need(first is not None and first['event']=='native_worker_reserved' and first['details']['ids']==[r['id'] for r in rows]
         and last['event']=='native_worker_completed' and last['details']['result_count']==count
         and entered==completed==observed==count and true_observed==(count if job['operation']=='true' else 0),
         'Native journal completion')
    return rp


def supervise(job_proof,output):
    start=time.monotonic();job,rows=load_job(job_proof);root=_path(output);worker=_path(job['output'])
    protected=[worker,_path(job_proof['path']),_path(job['acquisition_receipt']['path']).parent,
               _path(job['inputs']['path']),*(Path(p['path']) for p in job['runtime_sources'].values())]
    need(root.parent.is_dir() and not root.exists() and all(root!=p and root not in p.parents and p not in root.parents for p in protected),
         'Separate fresh native supervisor output required')
    containment=contain_process_tree()
    root.mkdir();seconds=job['limits']['seconds']+30;deadline=start+seconds
    command=[job['interpreter']['path'],'-I','-B',str(Path(__file__).resolve()),'--worker','--job',job_proof['path'],'--job-sha256',job_proof['sha256']]
    try:
        write_new(root/'REQUEST.json',dict(job=job_proof,command=command,worker=str(worker),automatic_retries=0))
        with DeadlineWatchdog(deadline+10,root/'DEADLINE.json'):
            limits=processes.ProcessLimits(deadline-time.monotonic(),4*1024**2)
            try:result=processes.supervise_command(command,limits=limits)
            except BaseException as error:
                result=getattr(error,'tether_engine_result',getattr(error,'result',None))
                if result is not None:_process_files(root,result,primary=error)
                raise
            _process_files(root,result)
            need(result.returncode==0,'Native worker unsuccessful')
            processes.validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
            rp=verify_worker(worker,job_proof,job,rows,deadline)
            need(job['code_pins']==source_pins(),'Supervisor source drift')
            write_new(root/'COMPLETE.json',dict(status='verified',worker_receipt=rp,job=job_proof,wall_seconds=time.monotonic()-start))
            files={p.name:_hash(p,deadline) for p in root.iterdir() if p.is_file()}
            write_new(root/'RECEIPT.json',dict(kind='alce_native_execution_receipt_v1',status='verified',files=files))
            return _hash(root/'RECEIPT.json',deadline)
    except BaseException as error:
        try:write_new(root/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,reason=str(error)[:2000],automatic_retries=0))
        except BaseException as persistence:error.add_note('Supervisor failure retention failed: '+type(persistence).__name__)
        raise


def _process_files(root,result,primary=None):
    """Retain each capture independently without replacing a child exception."""
    failures=[]
    for name,raw in (('stdout.bin',result.stdout),('stderr.bin',result.stderr)):
        try:
            with (root/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        except BaseException as error:failures.append((name,error))
    try:write_new(root/'PROCESS.json',dict(returncode=result.returncode,supervision=result.supervision))
    except BaseException as error:failures.append(('PROCESS.json',error))
    if failures:
        target=primary if primary is not None else failures[0][1]
        for name,error in failures:target.add_note('Process capture failed for '+name+': '+type(error).__name__)
        if primary is None:raise target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',type=Path,required=True);parser.add_argument('--job-sha256',required=True)
    parser.add_argument('--output',type=Path);parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();p=_hash(_path(args.job),time.monotonic()+60)
    need(p['sha256']==args.job_sha256,'Externally anchored native job required')
    if args.worker:result=execute(p)
    else:
        need(args.output is not None,'Fresh supervisor output required');result=supervise(p,args.output)
    print(canonical(dict(status='completed',receipt=result)).decode(),flush=True)


if __name__=='__main__':main()
