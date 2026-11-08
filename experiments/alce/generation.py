"""Inert, source-only ALCE generation coordinator; evaluation is a separate role.

The parent admits all source projections once. Its child receives only the
three generation files, pinned code/model inputs and a frozen full schedule.
No failure is retried or removed from the denominator. Python auditing is a
trusted-code boundary, not an operating-system sandbox for native extensions.
"""
import argparse
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import ctypes
import hashlib
import math
import os
from pathlib import Path
import subprocess
import stat
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
if __package__ in (None,''):
    for directory in (ROOT/'packages/tether/src',ROOT/'src',ROOT):sys.path.insert(0,str(directory))
from tether import _process as processes
import tether
import tether_engine
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import canonical,encode,fingerprint,freeze,parse_json,ContractError
from experiments.alce import data_views as data,prompts,producer
from experiments.labbench import runtime

FAMILIES=prompts.FAMILIES
COUNTS={'asqa':948,'qampari':1000,'eli5':1000}
KIND='alce_generation_plan_v2'
need=producer.need
PACKAGES={'tether_engine':'src/tether_engine','tether':'packages/tether/src/tether'}
SOURCE_FIELDS=('code_files','source_identities','package_origins')
# Fresh isolated child only: admit package initializers before loading either
# package, then retain their normal package search paths for every dependency.
WORKER_BOOTSTRAP="""import hashlib,importlib.util,json,sys
from pathlib import Path
root=Path(sys.argv[1]);origins=json.loads(sys.argv[2])
if set(origins)!={'tether_engine','tether'}:raise ValueError('Exact package origins required')
sys.path.insert(0,str(root))
for name in ('tether_engine','tether'):
    if name in sys.modules:raise ValueError('Package already loaded before admitted bootstrap')
    proof=origins[name];path=Path(proof['path']);raw=path.read_bytes()
    if set(proof)!={'path','bytes','sha256'} or path!=path.resolve() or path.name!='__init__.py' or len(raw)!=proof['bytes'] or hashlib.sha256(raw).hexdigest()!=proof['sha256']:
        raise ValueError('Package initializer differs from admitted origin')
    spec=importlib.util.spec_from_file_location(name,str(path),submodule_search_locations=[str(path.parent)])
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
sys.argv=[str(root/'experiments/alce/generation.py'),*sys.argv[3:]]
from experiments.alce.generation import main
main()
"""


@dataclass(frozen=True)
class Limits:
    whole_seconds: float
    call_seconds: float
    output_bytes: int
    input_byte_limit: int
    context_tokens: int
    finalization_seconds: float

    def __post_init__(self):
        for value in (self.whole_seconds,self.call_seconds,self.finalization_seconds):
            need(type(value) in (int,float) and math.isfinite(value) and value>0,'Explicit finite generation clocks required')
        need(self.call_seconds<=600 and self.whole_seconds>self.call_seconds+self.finalization_seconds,
             'Qualified call bound and explicit carried finalization allowance required')
        need(type(self.output_bytes)is int and self.output_bytes>0 and type(self.input_byte_limit)is int and
             0<self.input_byte_limit<=producer.MAX_PAYLOAD_BYTES,'Explicit byte ceilings required')
        need(type(self.context_tokens)is int and self.context_tokens==16384,'Qualified context unchanged')


def _read(proof,end,maximum=32*1024**2):return parse_json(data._read(proof,maximum,end))
def _write(path,value):publish_bytes(path,canonical(value));return data._hash(path,time.monotonic()+30)
def _proof(path,end):return data._hash(path,end)


def source_context(end):
    """Logical identities plus actual immutable origins; no path-only acceptance."""
    paths={Path(__file__).resolve()}
    for name in ('src/tether_engine','packages/tether/src/tether','experiments/labbench'):
        paths.update(p for p in (ROOT/name).rglob('*.py') if not p.name.startswith('test_') and 'tests' not in p.parts)
    paths.update(ROOT/'experiments/alce'/name for name in ('__init__.py','producer.py','prompts.py','data_views.py'))
    declared={p.relative_to(ROOT).as_posix():_proof(p,end) for p in sorted(paths)}
    proofs={p['path']:p for p in declared.values()};origins={};package_roots={}
    for name,relative in PACKAGES.items():
        module=sys.modules[name];initializer=data._path(module.__file__)
        need(initializer.name=='__init__.py' and module.__spec__.origin==str(initializer)
             and list(module.__path__)==[str(initializer.parent)],'Canonical loaded package origin required')
        origins[name]=_proof(initializer,end);package_roots[name]=initializer.parent
        expected={key[len(relative)+1:]:p for key,p in declared.items() if key.startswith(relative+'/')}
        observed={p.relative_to(initializer.parent).as_posix():p for p in initializer.parent.rglob('*.py')
                  if not p.name.startswith('test_') and 'tests' not in p.relative_to(initializer.parent).parts}
        need(set(observed)==set(expected),'Installed package source membership differs')
        for key,path in observed.items():
            p=_proof(path,end)
            need(all(p[k]==expected[key][k] for k in ('bytes','sha256')),'Loaded dependency bytes differ: '+name+'/'+key)
            proofs[p['path']]=p
    for alias,module in tuple(sys.modules.items()):
        prefix=next((p for p in PACKAGES if alias==p or alias.startswith(p+'.')),None)
        if prefix is None:continue
        name=getattr(module,'__name__',None)
        need(name==alias or (prefix=='tether' and name=='tether_engine'+alias[len('tether'):]),
             'Undeclared loaded module alias')
        actual_prefix=name.split('.')[0];suffix=name.split('.')[1:]
        actual=data._path(module.__file__)
        relative=Path(*suffix)/'__init__.py' if actual.name=='__init__.py' else Path(*suffix).with_suffix('.py')
        expected=package_roots[actual_prefix]/relative
        need(actual==expected and module.__spec__.origin==str(expected) and str(actual) in proofs,
             'Loaded module origin differs from admitted package')
    need(all(p==proofs.get(p['path']) for p in producer._sources(end)),
         'Loaded producer dependencies differ from the declared source closure')
    return dict(code_files=[proofs[p] for p in sorted(proofs)],package_origins=origins,
        source_identities={key:{k:p[k] for k in ('bytes','sha256')} for key,p in declared.items()})


def source_pins(end):return source_context(end)['code_files']


def _check_sources(value,end):
    current=source_context(end)
    need(all(value[k]==current[k] for k in SOURCE_FIELDS),'Current code/source origins differ')


def _command(value,job_proof):
    return [value['interpreter']['path'],'-I','-B','-c',WORKER_BOOTSTRAP,str(ROOT),
        canonical(value['package_origins']).decode(),'--worker','--job',job_proof['path'],'--job-sha256',job_proof['sha256']]


def _same(proofs,end):
    for proof in proofs:data._read(proof,2*1024**2,end)


def _fresh(output,protected):
    root=data._path(output)
    need(root.parent.is_dir() and not root.exists(),'Fresh output under an existing parent required')
    for item in protected:
        path=data._path(item)
        need(root!=path and root not in path.parents and path not in root.parents,'Output overlaps protected input')
    return root


def _metadata(preparation,end):
    need(isinstance(preparation,Mapping) and set(preparation)=={'root','receipt_sha256'},'Exact preparation descriptor required')
    root=data._path(preparation['root']);rp=_proof(root/'RECEIPT.json',end)
    need(rp['sha256']==preparation['receipt_sha256'],'Preparation receipt anchor differs')
    receipt=_read(rp,end)
    need(receipt['kind']=='alce_data_preparation_receipt_v1' and receipt['status']=='prepared','Prepared projection required')
    for name in ('GENERATION.json','SCHEDULE.json','COMPLETE.json'):
        need(receipt['files'][name]['path']==str(root/name),'Preparation metadata location differs')
    generation=_read(receipt['files']['GENERATION.json'],end)
    need(generation['kind']=='alce_generation_files_v1' and generation['condition']=='original_retrieved_order_first_five'
         and set(generation['files'])==set(FAMILIES),'All supplied-passage families required')
    schedule=_read(receipt['files']['SCHEDULE.json'],end)
    need(set(schedule)==set(FAMILIES),'Full schedule families required')
    files={};ids={}
    for family in FAMILIES:
        gp=receipt['files'][f'generation/{family}.json']
        need(generation['files'][family]==gp and gp['path']==str(root/f'generation/{family}.json'),'Exact actor file required')
        files[family]=gp;ids[family]=[row['id'] for row in schedule[family]]
        need(ids[family] and len(set(ids[family]))==len(ids[family]),'Unique nonempty ordered family schedule required')
    return dict(receipt=rp,files=files,ids=ids,counts={f:len(ids[f]) for f in FAMILIES})


def prepare_plan(preparation,output,*,configurations,model_receipt,port,alias,limits,purpose,gate_receipts):
    """Freeze metadata only. Full source admission happens in the supervised parent."""
    need(isinstance(limits,Limits),'Explicit prospectively frozen limits required')
    end=time.monotonic()+120;meta=_metadata(preparation,end)
    need(purpose in ('production','invented_qualification'),'Declared schedule purpose required')
    need(meta['counts']==COUNTS if purpose=='production' else all(1<=n<=8 for n in meta['counts'].values()),'Complete declared population required')
    need(set(configurations)==set(FAMILIES),'Configuration for every family required')
    for family,config in configurations.items():
        prompts._configuration(config,family)
        need(config['max_new_tokens']==300 and config['temperature']==0 and config['top_p']==1 and config['seed']==20261107,
             'Qualified generation settings unchanged')
    need(set(gate_receipts)=={'free_text','true_baseline','qa','mauve','lexical'},'All required baseline qualification anchors required')
    for proof in (*gate_receipts.values(),model_receipt):data._read(proof,32*1024**2,end)
    spec,bindings,model=producer.shared.make_server_spec(model_receipt['path'],model_receipt['sha256'],port=port,
        alias=alias,context_tokens=limits.context_tokens)
    protected=[preparation['root'],str(Path(model_receipt['path']).parent),*(p['path'] for p in gate_receipts.values())]
    sources=source_context(end)
    root=_fresh(output,protected);root.mkdir()
    value=dict(schema_version=2,kind=KIND,purpose=purpose,preparation=encode(preparation),
        preparation_receipt=meta['receipt'],generation_files=meta['files'],ordered_ids=meta['ids'],expected_counts=meta['counts'],
        configurations=encode(configurations),model_receipt=encode(model_receipt),model_provenance=encode(model),
        port=port,alias=alias,limits=asdict(limits),gate_receipts=encode(gate_receipts),
        **sources,interpreter=_proof(Path(sys.executable).resolve(),end),automatic_retries=0,provider_cost_usd=0)
    return _write(root/'PLAN.json',value)


def load_plan(proof,end):
    plan=_read(proof,end)
    need(set(plan)=={'schema_version','kind','purpose','preparation','preparation_receipt','generation_files','ordered_ids','expected_counts',
        'configurations','model_receipt','model_provenance','port','alias','limits','gate_receipts','code_files','source_identities','package_origins','interpreter',
        'automatic_retries','provider_cost_usd'} and plan['schema_version']==2 and plan['kind']==KIND,'Exact v2 generation plan required')
    limits=Limits(**plan['limits']);need(plan['automatic_retries']==plan['provider_cost_usd']==0,'No retry/provider contract')
    need(plan['purpose'] in ('production','invented_qualification'),'Schedule purpose required')
    need(set(plan['ordered_ids'])==set(plan['generation_files'])==set(plan['expected_counts'])==set(plan['configurations'])==set(FAMILIES),
         'Full family schedule required')
    for family in FAMILIES:
        ids=plan['ordered_ids'][family]
        need(isinstance(ids,list) and ids and len(set(ids))==len(ids) and all(type(i)is str and i for i in ids),'Ordered case IDs required')
        need(type(plan['expected_counts'][family])is int and len(ids)==plan['expected_counts'][family],'Case denominator differs')
        config=prompts._configuration(plan['configurations'][family],family)
        need(config['max_new_tokens']==300 and config['temperature']==0 and config['top_p']==1 and config['seed']==20261107,'Generation method differs')
    need(plan['expected_counts']==COUNTS if plan['purpose']=='production' else all(1<=n<=8 for n in plan['expected_counts'].values()),'Full declared population required')
    _check_sources(plan,end)
    need(_proof(Path(sys.executable).resolve(),end)==plan['interpreter'],'Current interpreter differs')
    spec,bindings,model=producer.shared.make_server_spec(plan['model_receipt']['path'],plan['model_receipt']['sha256'],
        port=plan['port'],alias=plan['alias'],context_tokens=limits.context_tokens)
    need(canonical(model)==canonical(plan['model_provenance']),'Model identity differs')
    return plan,limits,spec,bindings


def _admit(plan,end):
    verified=data.verify_preparation(**plan['preparation'])
    data._tick(end)
    need(verified['counts']==plan['expected_counts'] and canonical(verified['generation_files'])==canonical(plan['generation_files'])
         and canonical(verified['receipt'])==canonical(plan['preparation_receipt']),'Source projection differs from frozen plan')
    metadata=_metadata(plan['preparation'],end)
    need(metadata['ids']==plan['ordered_ids'],'Frozen ordered source schedule differs')
    return verified


def _release(proof,plan_proof,plan,end,*,output):
    value=_read(proof,end)
    need(set(value)=={'kind','status','plan','qualification_receipts','native_baselines_qualified','post_candidate_evaluator_gate_required',
        'automatic_retries','provider_cost_usd','output'} and value['kind']=='alce_generation_release_v1' and value['status']=='approved'
        and value['plan']==plan_proof and value['qualification_receipts']==plan['gate_receipts']
        and data._path(value['output'])==data._path(output)
        and value['native_baselines_qualified'] is True and value['post_candidate_evaluator_gate_required'] is True
        and value['automatic_retries']==value['provider_cost_usd']==0,'Prospective staged generation release required')
    need(set(plan['gate_receipts'])=={'free_text','true_baseline','qa','mauve','lexical'},'Required baseline gate missing')
    for gate in plan['gate_receipts'].values():data._read(gate,32*1024**2,end)
    return value


class ActorAudit:
    """Exact data/code grants and loopback only; all denials remain terminal."""
    def __init__(self,inputs,output,port,command):
        self.inputs={str(data._path(x)).casefold() for x in inputs};self.output=data._path(output)
        self.runtime_roots=tuple(Path(x).resolve() for x in (sys.prefix,sys.base_prefix))
        self.port=port;self.command=list(command);self.active=False;self.busy=threading.local();self.denied=0
        self.stream=(self.output/'io-audit.jsonl').open('xb',buffering=0)
    def hook(self,event,args):
        if not self.active or getattr(self.busy,'value',False):return
        self.busy.value=True
        try:
            allowed=True;record=None
            if event=='open':
                name,mode,flags=args
                if type(name)is int:allowed=name>=0;record=dict(event=event,path=None,descriptor=name,allowed=allowed,basis='descriptor')
                elif type(name)is str and name==os.devnull:
                    allowed=not bool(flags&(os.O_CREAT|os.O_TRUNC|os.O_APPEND));record=dict(event=event,path=name,flags=flags,allowed=allowed,basis='literal_null_device')
                else:
                    path=Path(os.fsdecode(name)).resolve();write=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
                    output=path.is_relative_to(self.output)
                    granted=str(path).casefold() in self.inputs
                    runtime_read=any(path.is_relative_to(r) for r in self.runtime_roots)
                    allowed=output or (not write and (granted or runtime_read))
                    record=dict(event=event,path=str(path),write=write,allowed=allowed,basis='output' if output else 'exact_input' if granted else 'runtime' if runtime_read else 'denied')
            elif event.startswith('socket.'):
                if event in ('socket.__new__','socket.gethostname'):return
                allowed=(event=='socket.getaddrinfo' and args[:2]==('127.0.0.1',self.port)) or (
                    event in ('socket.bind','socket.connect') and type(args[1])is tuple and args[1]==('127.0.0.1',self.port))
                endpoint=list(args[:2]) if event=='socket.getaddrinfo' else list(args[1]) if event in ('socket.bind','socket.connect') and type(args[1])is tuple else None
                record=dict(event=event,endpoint=endpoint,allowed=allowed,basis='declared_loopback' if allowed else 'denied')
            elif event=='subprocess.Popen':
                executable,command=args[:2]
                allowed=(command==self.command or (os.name=='nt' and command==subprocess.list2cmdline(self.command))) and (
                    executable is None or Path(executable).resolve()==Path(self.command[0]).resolve())
                record=dict(event=event,command=encode(command),executable=os.fsdecode(executable) if executable is not None else None,
                            allowed=allowed,basis='owned_server' if allowed else 'denied')
            if record is not None:
                self.stream.write(canonical(record)+b'\n')
                if not allowed:self.denied+=1;os.fsync(self.stream.fileno());raise PermissionError('Generation actor denied undeclared access')
        finally:self.busy.value=False
    def activate(self):self.active=True;sys.addaudithook(self.hook)
    def close(self):self.active=False;self.stream.flush();os.fsync(self.stream.fileno());self.stream.close()


def _inventory(root,end,omit=()):
    result={}
    for path in sorted(root.rglob('*')):
        data._path(path)
        name=path.relative_to(root).as_posix()
        if path.is_file() and name not in omit:result[name]=_proof(path,end)
    return result


def _size(root,maximum):
    total=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    need(total<=maximum,'Frozen generation output-byte ceiling exceeded')
    return total


def _live_entry(path):
    try:info=path.lstat()
    except FileNotFoundError:
        if path.name.startswith('.publishing-'):return 0
        raise
    need(not getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400),
         'Linked live output rejected')
    if stat.S_ISREG(info.st_mode):return info.st_size
    need(stat.S_ISDIR(info.st_mode),'Special live output rejected')
    return None


def _live_tree_bytes(root):
    total=0
    for path in root.rglob('*'):
        size=_live_entry(path)
        if size is not None:total+=size
    return total


class OutputWatchdog:
    """Charge closed cells once; sample only the active cell and live writers.

    This is a sampled application budget, not an OS disk quota. The final closed
    inventory rechecks all sealed cells; trusted code never reopens them to write.
    """
    def __init__(self,root,maximum):
        self.root,self.maximum=root,maximum;self.stop=threading.Event()
        self.lock=threading.Lock();self.sealed={};self.sealed_bytes=0;self.active=None
        self.thread=threading.Thread(target=self.poll,daemon=True)
    def begin(self,cell):
        with self.lock:
            need(self.active is None and cell not in self.sealed,'Only one fresh active output cell permitted')
            self.active=cell
        self.check()
    def seal(self,cell):
        measured=_live_tree_bytes(cell)
        with self.lock:
            need(self.active==cell and cell not in self.sealed,'Output cell already charged or not active')
            self.sealed[cell]=measured;self.sealed_bytes+=measured;self.active=None
        self.check()
    def check(self):
        with self.lock:
            total=self.sealed_bytes;active=self.active
            for path in self.root.iterdir():
                size=_live_entry(path)
                if size is not None:total+=size
                elif path.name=='server':total+=_live_tree_bytes(path)
                else:need(path.name=='attempts','Unregistered generation writer directory')
            if active is not None and active.exists():total+=_live_tree_bytes(active)
        need(total<=self.maximum,'Frozen generation output-byte ceiling exceeded')
        return total
    def poll(self):
        while not self.stop.wait(.25):
            try:self.check()
            except BaseException as error:
                try:_write(self.root/'OUTPUT-LIMIT.json',dict(status='output_limit_or_monitor_failure',output_bytes=self.maximum,
                    error_type=type(error).__name__,error_message=str(error)[:1000]))
                finally:os._exit(125)
    def __enter__(self):self.check();self.thread.start();return self
    def __exit__(self,*unused):self.stop.set();self.thread.join(2);need(not self.thread.is_alive(),'Output monitor did not stop')


def _host_memory():
    if os.name!='nt':return None
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
            ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended')]
    value=Memory();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):return None
    return dict(total_bytes=int(value.total_phys),available_bytes=int(value.avail_phys))


def resource_summary(rows):
    def observed(role,key):return [r[role][key] for r in rows if r[role] is not None and r[role].get(key) is not None]
    together=[r['worker']['working_set_bytes']+r['server']['working_set_bytes'] for r in rows
        if r['worker'] and r['server'] and r['worker'].get('working_set_bytes') is not None and r['server'].get('working_set_bytes') is not None]
    cpu={role:observed(role,'cpu_seconds') for role in ('worker','server')}
    peaks={role:observed(role,'process_peak_working_set_bytes') for role in ('worker','server')}
    available=[r['host']['available_bytes'] for r in rows if r['host'] is not None]
    return dict(samples=len(rows),sampled_worker_plus_server_peak_bytes=max(together) if together else None,
        process_lifetime_peak_working_set_bytes={role:max(v) if v else None for role,v in peaks.items()},
        observed_cpu_delta_seconds={role:max(v)-min(v) if len(v)>1 else None for role,v in cpu.items()},
        server_observed_lifetime_cpu_seconds=max(cpu['server']) if cpu['server'] else None,
        host_available_min_bytes=min(available) if available else None,gpu_peak_bytes=None,whole_process_tree_peak_bytes=None,
        scope='Sampling begins before owned-server entry and includes asset verification/startup through server closure. CPU deltas span observed samples only; process-lifetime high-water marks have a distinct scope. GPU and arbitrary descendants are unmeasured.')


class Resources:
    def __init__(self,owner):
        self.owner=owner;self.rows=[];self.stop=threading.Event();self.thread=threading.Thread(target=self.poll,daemon=True)
    def capture(self):
        row=dict(monotonic=time.monotonic(),worker=None,server=None,host=None,errors=[])
        for role,pid in (('worker',os.getpid()),('server',self.owner.terminal_record.get('pid'))):
            if pid is not None:
                try:row[role]=runtime.process_sample(pid)
                except Exception as error:row['errors'].append(role+':'+type(error).__name__)
        try:row['host']=_host_memory()
        except Exception as error:row['errors'].append('host:'+type(error).__name__)
        self.rows.append(row)
    def poll(self):
        while not self.stop.wait(1):self.capture()
    def __enter__(self):self.capture();self.thread.start();return self
    def __exit__(self,error_type,error,tb):
        self.stop.set();self.thread.join(2);self.capture()
        if self.thread.is_alive():
            if error is None:raise ContractError('Resource monitor did not close')
            error.add_note('Resource monitor did not close')


def _failure(root,journal,error,stage):
    value=dict(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',stage=stage,error_type=type(error).__name__,automatic_retries=0)
    for action in (lambda:_write(root/'FAILURE.json',value),lambda:journal.append('generation_failed',**value)):
        try:action()
        except BaseException as secondary:error.add_note('Failure retention: '+type(secondary).__name__)


def _schedule(job):
    return [dict(family=f,ordinal=i,id=identifier,owner='resident',execution_id=f'alce-{f}-{i:04d}',
        disposition='unexecuted',descriptor=None,evidence=None,output=None) for f in FAMILIES for i,identifier in enumerate(job['ordered_ids'][f])]


def _job_schema(job):
    need(isinstance(job,Mapping) and set(job)=={'kind','generation_files','ordered_ids','expected_counts','configurations',
         'model_receipt','model_provenance','port','alias','limits','code_files','source_identities','package_origins',
         'interpreter','output','deadline_monotonic','plan_sha256'} and job['kind']=='alce_generation_actor_job_v2',
         'Exact v2 actor job required')


def worker(job_proof):
    started=time.monotonic();job=_read(job_proof,started+60);_job_schema(job)
    limits=Limits(**job['limits']);end=job['deadline_monotonic']
    need(type(end) in (int,float) and math.isfinite(end)
         and 0<end-started<=limits.whole_seconds,'Bounded actor job required')
    need(set(job['generation_files'])==set(job['ordered_ids'])==set(job['expected_counts'])==set(job['configurations'])==set(FAMILIES),
         'Actor requires all three source families')
    _check_sources(job,end)
    need(_proof(Path(sys.executable).resolve(),end)==job['interpreter'],'Actor interpreter differs')
    root=_fresh(job['output'],[job_proof['path'],*(p['path'] for p in job['generation_files'].values()),job['model_receipt']['path']])
    journal=RunJournal(root,kind='build');guard=None;owner=None;samples=None;stage='admission';rows=_schedule(job);known=dict(input_tokens=0,output_tokens=0,cost_usd=0.0)
    handle=None
    try:
        handle=runtime.contain_process_tree()
        with runtime.DeadlineWatchdog(end,root/'DEADLINE.json'),OutputWatchdog(root,limits.output_bytes) as budget:
            # Model metadata is source-only; evaluator/archive paths are absent.
            spec,bindings,model=producer.shared.make_server_spec(job['model_receipt']['path'],job['model_receipt']['sha256'],
                port=job['port'],alias=job['alias'],context_tokens=limits.context_tokens)
            need(canonical(model)==canonical(job['model_provenance']),'Actor model differs')
            grants=[job_proof['path'],job['model_receipt']['path'],*(p['path'] for p in job['generation_files'].values()),
                *(p['path'] for p in job['code_files']),*(str(p) for p in bindings.values())]
            guard=ActorAudit(grants,root,job['port'],encode(spec)['argv']);guard.activate()
            families={f:data.load_generation(job['generation_files'][f]) for f in FAMILIES}
            for family in FAMILIES:
                need([r['id'] for r in families[family]]==job['ordered_ids'][family] and len(families[family])==job['expected_counts'][family],
                     'Actor full source schedule differs')
                # All full prompts are byte-preflighted before any server/call.
                for case in families[family]:prompts.build_request(case,family=family,input_byte_limit=limits.input_byte_limit,configuration=job['configurations'][family])
            _write(root/'MODEL.json',dict(spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()},model=encode(model),alias=job['alias']))
            (root/'server').mkdir();(root/'attempts').mkdir();stage='startup'
            owner=producer.shared.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end)
            startup=time.monotonic()
            with Resources(owner) as samples,owner:
                load_seconds=time.monotonic()-startup
                for position,row in enumerate(rows):
                    stage=f"{row['family']}:{row['ordinal']}";data._tick(end);budget.check()
                    case=families[row['family']][row['ordinal']]
                    request=prompts.build_request(case,family=row['family'],input_byte_limit=limits.input_byte_limit,configuration=job['configurations'][row['family']])
                    call,payload=producer.make_call(request,model,limits=producer.Limits(limits.context_tokens,limits.call_seconds))
                    cell=root/'attempts'/f'{position:04d}'
                    budget.begin(cell)
                    journal.append('case_reserved',family=row['family'],ordinal=row['ordinal'],id=row['id'],execution_id=row['execution_id'],call_sha256=fingerprint(call))
                    row['disposition']='failed';row['evidence']=dict(root=str(cell),status='reserved_or_uncertain')
                    result=producer.execute_once(owner,call,payload,output=cell,deadline=end,alias=job['alias'],execution_id=row['execution_id'])
                    checked=producer.verify_attempt(cell,result['receipt_sha256'],call=call,payload=payload,owner_pid=owner.terminal_record['pid'],
                        alias=job['alias'],server_spec=spec,bindings=bindings,deadline=end)
                    row.update(disposition='completed',descriptor=dict(root=str(cell),receipt_sha256=result['receipt_sha256']),evidence=None)
                    for key in known:known[key]+=checked['result']['verified']['usage'][key]
                    journal.append('case_completed',family=row['family'],ordinal=row['ordinal'],id=row['id'],receipt_sha256=result['receipt_sha256'])
                    budget.seal(cell)
            terminal=encode(owner.terminal_record);_write(root/'SERVER-TERMINAL.json',terminal)
            need(terminal['server_stopped'] is True and terminal['secondary_failures']==[] and 'error_class' not in terminal,'Clean resident server closure required')
            need(guard.denied==0,'Denied actor access blocks success')
            for asset in (spec.executable,*spec.required_inputs):
                observed=_proof(bindings[asset['logical_id']],end)
                need(observed['bytes']==asset['bytes'] and observed['sha256']==asset['sha256'],'Model/runtime bytes changed')
            for value in (*job['generation_files'].values(),job['model_receipt']):data._read(value,256*1024**2,end)
            _check_sources(job,end)
            report=dict(kind='alce_generation_actor_report_v1',status='completed',expected_counts=job['expected_counts'],attempts=rows,
                owners={'resident':dict(owner_pid=terminal['pid'],alias=job['alias'],server_spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()})},
                generation=dict(configurations=job['configurations'],input_byte_limit=limits.input_byte_limit,model_provenance=encode(model),
                    limits=dict(context_tokens=limits.context_tokens,call_seconds=limits.call_seconds)),
                known_measured_usage=known,automatic_retries=0,source_http_calls=0,io_denials=guard.denied,
                first_load_including_asset_verification_seconds=load_seconds,wall_seconds=time.monotonic()-started,
                resources=resource_summary(samples.rows),output_accounting=dict(closed_cells=len(budget.sealed),
                    sampled_live_writers=True,operating_system_quota=False,final_closed_inventory_rechecked=True),
                reference_access=False,scientific_correctness_evaluated=False)
            _write(root/'RESOURCE-SAMPLES.json',samples.rows)
            _write(root/'REPORT.json',report);journal.append('generation_completed',report_sha256=fingerprint(report));guard.close();guard=None;journal.close()
            _size(root,limits.output_bytes)
            receipt=_write(root/'RECEIPT.json',dict(kind='alce_generation_actor_receipt_v1',status='completed',job=job_proof,
                files=_inventory(root,end),seal_elapsed_seconds=time.monotonic()-started))
            budget.check();data._tick(end);return receipt
    except BaseException as error:
        try:
            for row in rows:
                if row['disposition']=='failed' and row['evidence']:
                    cell=Path(row['evidence']['root']);row['evidence']['files']=_inventory(cell,time.monotonic()+30) if cell.exists() else {}
            _write(root/'PARTIAL.json',dict(status='failed',attempts=rows,known_measured_usage=known,
                uncertain_usage_not_in_known_totals=True,automatic_retries=0,expected_counts=job['expected_counts']))
            if owner is not None:_write(root/'SERVER-FAILURE-TERMINAL.json',encode(owner.terminal_record))
            if samples is not None:_write(root/'FAILED-RESOURCE-SAMPLES.json',samples.rows)
        except BaseException as secondary:error.add_note('Partial accounting retention: '+type(secondary).__name__)
        _failure(root,journal,error,stage);raise
    finally:
        primary=sys.exception()
        for action in ([guard.close] if guard is not None else [])+[journal.close]:
            try:action()
            except BaseException as secondary:
                if primary is None:raise
                primary.add_note('Cleanup: '+type(secondary).__name__)
        _=handle


def _retain(root,result,primary):
    first=None
    for name,value in [('stdout.bin',result.stdout),('stderr.bin',result.stderr),
        ('PROCESS.json',canonical(dict(returncode=result.returncode,supervision=result.supervision)))]:
        try:publish_bytes(root/name,value)
        except BaseException as secondary:
            if primary is not None:primary.add_note('Process retention: '+type(secondary).__name__)
            elif first is None:first=secondary
    if first is not None:raise first


def launch(plan_proof,release_proof,output):
    started=time.monotonic();initial=_read(plan_proof,started+60);limits=Limits(**initial['limits']);end=started+limits.whole_seconds
    need(data._path(_read(release_proof,started+60)['output'])==data._path(output),'Release is bound to another output')
    root=_fresh(output,[plan_proof['path'],release_proof['path'],initial['preparation']['root'],str(Path(initial['model_receipt']['path']).parent),
        *(p['path'] for p in initial['gate_receipts'].values())])
    journal=RunJournal(root,kind='build');handle=None;stage='preflight'
    try:
        handle=runtime.contain_process_tree()
        with runtime.DeadlineWatchdog(end,root/'DEADLINE.json'):
            _write(root/'REQUEST.json',dict(plan=plan_proof,release=release_proof,output=str(root),whole_seconds=limits.whole_seconds,automatic_retries=0))
            plan,limits,spec,bindings=load_plan(plan_proof,end);_release(release_proof,plan_proof,plan,end,output=root)
            admitted=_admit(plan,end)
            _write(root/'ADMISSION.json',dict(status='source_projection_verified',receipt=encode(admitted['receipt']),counts=encode(admitted['counts']),
                generation_files=encode(admitted['generation_files']),worker_reference_grants=False))
            job={key:plan[key] for key in ('generation_files','ordered_ids','expected_counts','configurations','model_receipt','model_provenance',
                'port','alias','limits','code_files','source_identities','package_origins','interpreter')}
            job.update(kind='alce_generation_actor_job_v2',output=str(root/'worker'),deadline_monotonic=end-limits.finalization_seconds,plan_sha256=plan_proof['sha256'])
            jp=_write(root/'JOB.json',job)
            command=_command(plan,jp)
            _write(root/'COMMAND.json',command)
            child_limits=processes.ProcessLimits(end-limits.finalization_seconds-time.monotonic(),4*1024**2);_write(root/'LIMITS.json',child_limits.payload())
            stage='actor';result=None;primary=None
            try:result=processes.supervise_command(command,limits=child_limits)
            except BaseException as error:primary=error;result=getattr(error,'tether_engine_result',None);raise
            finally:
                if result is not None:_retain(root,result,primary)
            need(result.returncode==0,'Generation actor failed; retained attempt must not be retried')
            processes.validate_success_report(result.supervision,child_limits,len(result.stdout),len(result.stderr))
            stage='verification';worker_receipt=_proof(root/'worker/RECEIPT.json',end)
            report=verify_worker(root/'worker',worker_receipt,job,end)
            wr=_read(worker_receipt,end)
            need(report['wall_seconds']<=wr['seal_elapsed_seconds']<=result.supervision['execution_elapsed_seconds'],'Actor clock mismatch')
            _check_sources(plan,end);_release(release_proof,plan_proof,plan,end,output=root);data._read(plan_proof,32*1024**2,end)
            summary=dict(report,preparation=plan['preparation'],plan=plan_proof,worker_receipt=worker_receipt,
                status='completed',outer_wall_seconds=time.monotonic()-started,post_candidate_evaluator_gate_required=True,
                reference_access_scope='actor only; coordinator source projection validation reads complete originals',
                coordinator_source_originals_read=True)
            _write(root/'REPORT.json',summary);journal.append('generation_supervision_completed',report_sha256=fingerprint(summary));journal.close()
            receipt=_write(root/'RECEIPT.json',dict(kind='alce_generation_supervision_receipt_v1',status='completed',files=_inventory(root,end)))
            _size(root,limits.output_bytes);data._tick(end);return freeze(dict(root=str(root),receipt_sha256=receipt['sha256']))
    except BaseException as error:_failure(root,journal,error,stage);raise
    finally:
        primary=sys.exception()
        try:journal.close()
        except BaseException as secondary:
            if primary is None:raise
            primary.add_note('Journal close: '+type(secondary).__name__)
        _=handle


def verify_worker(root,receipt_proof,job,end):
    _job_schema(job)
    root=data._path(root)
    need(not any((root/n).exists() for n in ('FAILURE.json','DEADLINE.json','OUTPUT-LIMIT.json','PARTIAL.json','FINALIZATION-FAILED.json')),'Actor failure dominates success')
    receipt=_read(receipt_proof,end)
    need(receipt['kind']=='alce_generation_actor_receipt_v1' and receipt['status']=='completed' and receipt['files']==_inventory(root,end,omit=('RECEIPT.json',)),
         'Closed actor receipt required')
    need(sum(p['bytes'] for p in receipt['files'].values())+receipt_proof['bytes']<=job['limits']['output_bytes'],
         'Closed actor output exceeds frozen aggregate byte ceiling')
    need({p.name for p in root.iterdir() if p.is_dir()}=={'server','attempts'} and
         {p.name for p in root.iterdir() if p.is_file()}=={'MODEL.json','SERVER-TERMINAL.json','REPORT.json','RESOURCE-SAMPLES.json',
            'io-audit.jsonl','journal.jsonl','RECEIPT.json'} and
         {p.name for p in (root/'server').iterdir()}=={'server-command.json','server.stdout.bin','server.stderr.bin'},
         'Exact actor/server output membership required')
    report=_read(receipt['files']['REPORT.json'],end)
    need(set(report)=={'kind','status','expected_counts','attempts','owners','generation','known_measured_usage','automatic_retries','source_http_calls',
        'io_denials','first_load_including_asset_verification_seconds','wall_seconds','resources','output_accounting','reference_access','scientific_correctness_evaluated'} and
        report['kind']=='alce_generation_actor_report_v1' and report['status']=='completed' and report['expected_counts']==job['expected_counts']
        and report['reference_access'] is False and report['scientific_correctness_evaluated'] is False,'Full family result required')
    expected=_schedule(job);need(len(report['attempts'])==len(expected),'Every scheduled case required')
    terminal=_read(receipt['files']['SERVER-TERMINAL.json'],end)
    need(terminal['server_stopped'] is True and terminal['secondary_failures']==[] and 'error_class' not in terminal,'Server failed closure')
    spec,bindings,model=producer.shared.make_server_spec(job['model_receipt']['path'],job['model_receipt']['sha256'],port=job['port'],alias=job['alias'],context_tokens=job['limits']['context_tokens'])
    owner=dict(owner_pid=terminal['pid'],alias=job['alias'],server_spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()})
    need(canonical(report['owners'])==canonical({'resident':owner}),'Resident owner differs')
    need(_read(receipt['files']['MODEL.json'],end)==dict(spec=encode(spec),bindings=owner['bindings'],model=encode(model),alias=job['alias'])
         and _read(receipt['files']['server/server-command.json'],end)==encode(spec),'Actual server declaration/command differs')
    need(report['generation']==dict(configurations=job['configurations'],input_byte_limit=job['limits']['input_byte_limit'],
        model_provenance=encode(model),limits=dict(context_tokens=job['limits']['context_tokens'],call_seconds=job['limits']['call_seconds'])),
        'Generation method summary differs')
    need(all(type(report[k])in(int,float) and math.isfinite(report[k]) and report[k]>=0
        for k in ('wall_seconds','first_load_including_asset_verification_seconds')) and
        report['first_load_including_asset_verification_seconds']<=report['wall_seconds']<job['limits']['whole_seconds'],
        'Finite actor clocks required')
    events=read_chain(root/'journal.jsonl');life=[e for e in events if e['event'] in ('case_reserved','case_completed')]
    need(len(life)==2*len(expected),'Exact one-attempt lifecycle required')
    started=[e for e in events if e['event']=='server_started'];ready=[e for e in events if e['event']=='server_ready'];stopped=[e for e in events if e['event']=='server_terminal']
    need(len(started)==len(ready)==len(stopped)==1 and started[0]['details']==ready[0]['details']=={'pid':terminal['pid']}
         and canonical(stopped[0]['details'])==canonical(terminal) and
         started[0]['sequence']<ready[0]['sequence']<life[0]['sequence']<life[-1]['sequence']<stopped[0]['sequence'],
         'Owned resident server lifecycle differs')
    families={f:data.load_generation(job['generation_files'][f]) for f in FAMILIES};totals=dict(input_tokens=0,output_tokens=0,cost_usd=0.0)
    for index,(record,wanted) in enumerate(zip(report['attempts'],expected)):
        need(set(record)==set(wanted) and all(record[k]==wanted[k] for k in ('family','ordinal','id','owner','execution_id')) and record['disposition']=='completed'
             and record['evidence'] is None and record['output'] is None,'Ordered successful actor disposition differs')
        cell=root/'attempts'/f'{index:04d}';descriptor=record['descriptor']
        need(descriptor['root']==str(cell),'Physical case output differs')
        request=prompts.build_request(families[record['family']][record['ordinal']],family=record['family'],
            input_byte_limit=job['limits']['input_byte_limit'],configuration=job['configurations'][record['family']])
        call,payload=producer.make_call(request,model,limits=producer.Limits(job['limits']['context_tokens'],job['limits']['call_seconds']))
        verified=producer.verify_attempt(cell,descriptor['receipt_sha256'],call=call,payload=payload,owner_pid=owner['owner_pid'],
            alias=owner['alias'],server_spec=spec,bindings=bindings,deadline=end)
        need(verified['result']['execution_id']==record['execution_id'],'Physical execution identity differs')
        need(life[index*2]['event']=='case_reserved' and life[index*2]['details']==dict(family=record['family'],ordinal=record['ordinal'],id=record['id'],
            execution_id=record['execution_id'],call_sha256=fingerprint(call)) and life[index*2+1]['event']=='case_completed'
            and life[index*2+1]['details']==dict(family=record['family'],ordinal=record['ordinal'],id=record['id'],receipt_sha256=descriptor['receipt_sha256']),
            'Ordered case journals differ')
        for key in totals:totals[key]+=verified['result']['verified']['usage'][key]
    need({x.name for x in (root/'attempts').iterdir()}=={f'{i:04d}' for i in range(len(expected))},'Extra unscheduled attempt')
    need(totals==report['known_measured_usage'] and report['io_denials']==report['automatic_retries']==report['source_http_calls']==0,'Usage/access accounting differs')
    samples=_read(receipt['files']['RESOURCE-SAMPLES.json'],end)
    need(report['resources']==resource_summary(samples) and report['output_accounting']==dict(closed_cells=len(expected),
        sampled_live_writers=True,operating_system_quota=False,final_closed_inventory_rechecked=True),'Resource/output accounting differs')
    grants={str(data._path(p['path'])).casefold() for p in (*job['generation_files'].values(),*job['code_files'],job['model_receipt'])}
    grants.update(str(data._path(v)).casefold() for v in bindings.values())
    grants.add(str(data._path(receipt['job']['path'])).casefold())
    runtime_roots=tuple(Path(x).resolve() for x in (sys.prefix,sys.base_prefix))
    spawns=0
    for line in data._read(receipt['files']['io-audit.jsonl'],job['limits']['output_bytes'],end).splitlines():
        event=parse_json(line);need(event['allowed'] is True,'Actor audit contains denied access')
        if event['event']=='open':
            if event.get('path') is None:
                need(set(event)=={'event','path','descriptor','allowed','basis'} and event['basis']=='descriptor'
                     and type(event['descriptor'])is int and event['descriptor']>=0,'Descriptor audit identity differs')
            elif event['path']==os.devnull:
                need(set(event)=={'event','path','flags','allowed','basis'} and event['basis']=='literal_null_device'
                     and type(event['flags'])is int and not event['flags']&(os.O_CREAT|os.O_TRUNC|os.O_APPEND),'Null device audit differs')
            else:
                need(set(event)=={'event','path','write','allowed','basis'} and type(event['write'])is bool,'File audit schema differs')
                path=Path(event['path']);out=path.is_relative_to(root);runtime_read=any(path.is_relative_to(x) for x in runtime_roots)
                granted=str(path).casefold() in grants
                need(event['basis']==('output' if out else 'exact_input' if granted else 'runtime' if runtime_read else 'denied') and
                     (out or (not event['write'] and (granted or runtime_read))),'Recorded actor open exceeded source-only grants')
        elif event['event'] in ('socket.getaddrinfo','socket.bind','socket.connect'):
            need(set(event)=={'event','endpoint','allowed','basis'} and event['basis']=='declared_loopback'
                 and event['endpoint']==['127.0.0.1',job['port']],'Recorded network endpoint differs')
        elif event['event']=='subprocess.Popen':
            expected_command=encode(spec)['argv'];command=event.get('command');executable=event.get('executable')
            need(set(event)=={'event','command','executable','allowed','basis'} and event['basis']=='owned_server' and
                 (command==expected_command or (os.name=='nt' and command==subprocess.list2cmdline(expected_command))) and
                 (executable is None or Path(executable).resolve()==Path(expected_command[0]).resolve()),'Recorded subprocess command differs')
            spawns+=1
        else:raise ContractError('Unknown actor audit event')
    need(spawns==1,'Exactly one resident server process must be declared')
    need(events[-1]['event']=='generation_completed' and events[-1]['details']==dict(report_sha256=fingerprint(report)),'Actor terminal journal differs')
    for proof in job['generation_files'].values():data._read(proof,256*1024**2,end)
    _check_sources(job,end)
    need(receipt['files']==_inventory(root,end,omit=('RECEIPT.json',)),'Late actor mutation')
    return report


def verify_generation(descriptor):
    """Source-inclusive offline reconstruction before a separate evaluator gate."""
    root=data._path(descriptor['root']);end=time.monotonic()+3600;rp=_proof(root/'RECEIPT.json',end)
    need(rp['sha256']==descriptor['receipt_sha256'],'External generation receipt required')
    receipt=_read(rp,end)
    need(receipt['kind']=='alce_generation_supervision_receipt_v1' and receipt['status']=='completed'
         and receipt['files']==_inventory(root,end,omit=('RECEIPT.json',)),'Closed complete generation package required')
    need({p.name for p in root.iterdir() if p.is_dir()}=={'worker'} and
        {p.name for p in root.iterdir() if p.is_file()}=={'REQUEST.json','ADMISSION.json','JOB.json','COMMAND.json','LIMITS.json',
        'PROCESS.json','stdout.bin','stderr.bin','REPORT.json','journal.jsonl','RECEIPT.json'},'Exact coordinator output membership required')
    need(not any((root/n).exists() for n in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json')),'Parent failure dominates success')
    request=_read(receipt['files']['REQUEST.json'],end);plan,limits,_,_=load_plan(request['plan'],end)
    _release(request['release'],request['plan'],plan,end,output=root);admitted=_admit(plan,end)
    need(sum(p['bytes'] for p in receipt['files'].values())+rp['bytes']<=limits.output_bytes,'Closed coordinator output exceeds frozen aggregate byte ceiling')
    need(_read(receipt['files']['ADMISSION.json'],end)==dict(status='source_projection_verified',receipt=encode(admitted['receipt']),
        counts=encode(admitted['counts']),generation_files=encode(admitted['generation_files']),worker_reference_grants=False),
        'Retained source admission differs from reconstruction')
    jp=receipt['files']['JOB.json'];job=_read(jp,end);wrp=receipt['files']['worker/RECEIPT.json']
    need(job['plan_sha256']==request['plan']['sha256'] and job['output']==str(root/'worker'),'Actor job ancestry differs')
    for key in ('generation_files','ordered_ids','expected_counts','configurations','model_receipt','model_provenance','port','alias','limits','code_files','source_identities','package_origins','interpreter'):
        need(job[key]==plan[key],'Actor field differs from frozen plan: '+key)
    wr=_read(wrp,end);need(wr['job']==jp,'Actor external job proof differs')
    report=verify_worker(root/'worker',wrp,job,end)
    process=_read(receipt['files']['PROCESS.json'],end);process_limits=processes.ProcessLimits(**_read(receipt['files']['LIMITS.json'],end))
    need(process_limits.timeout_seconds<=limits.whole_seconds-limits.finalization_seconds and process_limits.max_output_bytes==4*1024**2,
         'Actor must preserve the declared parent finalization allowance')
    need(_read(receipt['files']['COMMAND.json'],end)==_command(plan,jp),'Pinned actor command differs')
    need(_read(receipt['files']['stdout.bin'],end)=={'receipt':wrp},'Actor terminal stdout receipt differs')
    need(process['returncode']==0,'Actor process failed')
    processes.validate_success_report(process['supervision'],process_limits,receipt['files']['stdout.bin']['bytes'],receipt['files']['stderr.bin']['bytes'])
    summary=_read(receipt['files']['REPORT.json'],end)
    need(canonical({k:summary[k] for k in report})==canonical(report) and summary['preparation']==plan['preparation']
        and summary['plan']==request['plan'] and summary['worker_receipt']==wrp and summary['post_candidate_evaluator_gate_required'] is True,
        'Coordinator report differs from actor/source')
    need(summary['reference_access_scope']=='actor only; coordinator source projection validation reads complete originals'
         and summary['coordinator_source_originals_read'] is True,'Reference-access role scope differs')
    need(report['wall_seconds']<=wr['seal_elapsed_seconds']<=process['supervision']['execution_elapsed_seconds']<=summary['outer_wall_seconds']<limits.whole_seconds,'Carried generation clocks differ')
    events=read_chain(root/'journal.jsonl');need(events[-1]['event']=='generation_supervision_completed' and
        events[-1]['details']==dict(report_sha256=fingerprint(summary)),'Parent journal differs')
    need(receipt['files']==_inventory(root,end,omit=('RECEIPT.json',)) and _proof(root/'RECEIPT.json',end)==rp,'Late generation package mutation')
    return freeze(dict(root=str(root),receipt_sha256=rp['sha256'],report=summary,
        source_projection_verified=True,wire_usage_verified=True,actor_reference_access=False,
        coordinator_source_originals_read=True,scientific_correctness_evaluated=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',action='store_true')
    parser.add_argument('--job');parser.add_argument('--job-sha256');args=parser.parse_args()
    if not args.worker:print('INERT: generation requires an externally pinned plan and separate staged release.');return
    need(args.job and args.job_sha256,'Exact internal actor arguments required')
    path=data._path(args.job);value=worker(dict(path=str(path),bytes=path.stat().st_size,sha256=args.job_sha256))
    print(canonical(dict(receipt=value)).decode())


if __name__=='__main__':main()
