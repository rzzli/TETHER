"""One canonical SOURCE/PURE owner. No filesystem, SDK, ctypes or live entry.

All ports/factories are explicit synthetic test ports. Callback ACKs are NOT
physical I/O. First native-return conversion/storage and production binding
remain unproved; complete pure results never qualify a real profile.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType

UNOBSERVED=object()
_MINT=object()
INVALID=2**64-1
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
CHECKS=('archive','journal','resources','core')
GATES=('admission','hashes',*CHECKS,'consistency','leases_closed','sealed','final_clock')
KINDS=('candidate','cleanup','failure','receipt','seal')
EVENTS=('output_reserved','source_open_reserved','source_open_returned','source_identity_reserved','source_identity_returned','source_hash_reserved','source_hash_returned','handoff_reserved','handoff_claimed','source_compile_reserved','source_compile_returned','file_open_reserved','file_open_returned','file_hash_reserved','file_hash_returned','stage_reserved','stage_returned','finalization_reserved','publication_reserved','publication_returned','original_close_reserved','original_close_returned_or_unknown','journal_close_reserved')
STAGES=('authority_factory','checker_factory','admit_reconcile','hash_remaining',*CHECKS,'consistency')
QUALIFICATION=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,real_checkers_bound=False,verification_complete=False,profile_qualified=False,runtime_authorized=False)

class SharedOwnerError(RuntimeError):
    def __init__(self,code):super().__init__(code);self.code=code

def uint(v,cap):return type(v) is int and 0<=v<=cap
def finite(v):return type(v) is int or type(v) is float and math.isfinite(v)
def usable(v):return uint(v,INVALID) and v not in (0,INVALID)
def signed_bool(v):return type(v) is int and -2**31<=v<2**31
def sha(v):return hashlib.sha256(v).hexdigest()
def need(ok,code='INVALID_INPUT'):
    if not ok:raise SharedOwnerError(code)
def path_key(path):
    need(type(path) is str and len(path)>=4 and path[0] in 'CcDd' and path[1]==':' and path[2] in '/\\')
    try:need(len(path.encode('utf-16-le','strict'))//2<=4096)
    except UnicodeError as error:raise SharedOwnerError('INVALID_INPUT') from error
    out=path.replace('/','\\')
    for p in out[3:].split('\\'):
        need(p not in ('','.','..') and not p.endswith((' ','.')) and not any(ord(c)<32 or ord(c)==127 or c in '<>:"|?*~' for c in p))
        need(p.split('.',1)[0].lower() not in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]})
    return out.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))
def freeze(v):
    if type(v) is dict:return MappingProxyType({k:freeze(x) for k,x in v.items()})
    if type(v) is list:return tuple(freeze(x) for x in v)
    return v
def thaw(v):
    if type(v) is MappingProxyType:return {k:thaw(x) for k,x in v.items()}
    if type(v) is tuple:return [thaw(x) for x in v]
    return v
def atom(v,tag):return dict(tag='UNOBSERVED' if v is UNOBSERVED else 'NULL' if v is None else tag,value=None if v is UNOBSERVED else v)
def callback_record():return dict(attempted=False,return_observed=False,acknowledged=False,prepared_bytes=0,prepared_sha256=None,semantics='fictional_callback_not_physical_IO')

@dataclass(frozen=True,slots=True)
class FileSpec:
    path:str
    role:str
    size:int
    sha256:str
    capture:bool
@dataclass(frozen=True,slots=True)
class ModuleRule:
    fullname:str
    path:str
    dependencies:tuple
    package:bool=False
@dataclass(frozen=True,slots=True)
class Snapshot:
    _data:object
    def to_dict(self):return thaw(self._data)

class Origin:
    __slots__=('_clock','_start','_now','_nonce','_state')
    def __init__(self,mint,clock,started):
        need(mint is _MINT and callable(clock) and finite(started))
        for k,v in dict(_clock=clock,_start=started,_now=started,_nonce=object(),_state='ok').items():object.__setattr__(self,k,v)
    def __setattr__(self,k,v):raise TypeError('immutable Origin')
    @property
    def start(self):return self._start
    @property
    def now(self):return self._now
    @property
    def work_end(self):return self._start+295
    @property
    def hard_end(self):return self._start+300
    def check(self,cleanup=False):
        if self._state=='invalid':raise SharedOwnerError('CLOCK_INVALID')
        try:
            n=self._clock();need(finite(n) and n>=self._now,'CLOCK_INVALID')
        except BaseException:
            object.__setattr__(self,'_state','invalid');raise
        object.__setattr__(self,'_now',n)
        if n>=self.hard_end:object.__setattr__(self,'_state','hard_expired');raise SharedOwnerError('HARD_DEADLINE')
        if not cleanup and n>=self.work_end:object.__setattr__(self,'_state','work_expired');raise SharedOwnerError('WORK_DEADLINE')
        return n
    def __reduce_ex__(self,p):raise TypeError('not serialized authority')

class FileRecordRef:
    __slots__=('_owner','_state')
    def __init__(self,mint,owner,state):need(mint is _MINT);object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_state',state)
    def __setattr__(self,k,v):raise TypeError('read-only file reference')
    @property
    def id(self):return self._state.id
    @property
    def spec(self):return self._state.spec
class BufferRef:
    __slots__=('_owner','_data','_generation','_written')
    def __init__(self,owner,capacity):
        object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_data',bytearray(capacity));object.__setattr__(self,'_generation',0);object.__setattr__(self,'_written',0)
    def __setattr__(self,k,v):raise TypeError('read-only buffer reference')
    @property
    def capacity(self):return len(self._data)
class FileState:
    def __init__(self,owner,i,spec,early):
        self.id=i;self.spec=spec;self.early=early;self.ref=FileRecordRef(_MINT,owner,self)
        self.open_state='unopened';self.identity_state='not_attempted';self.identity_queries=[];self.identity_witness=None
        self.hashed=0;self.captured=0;self.hash_attempted=False;self.hash_complete=False;self.capture_complete=False;self.actual_sha=None;self.blob=None;self.assembly=bytearray(spec.size);self.hasher=None
        self.close_reserved=False;self.close_state='not_attempted'
class Registry:
    __slots__=('_owner','_files','_calls')
    def __init__(self,owner):object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_files',[]);object.__setattr__(self,'_calls',[])
    def __setattr__(self,k,v):raise TypeError('canonical registry is source-owned')
class CallState:
    def __init__(self,owner,i,api,file,requested,buffer):
        self.owner=owner;self.ordinal=i;self.api=api;self.file=file;self.requested=requested;self.buffer=buffer;self.generation=buffer._generation if buffer else None
        self.invoked=False;self.scalar=UNOBSERVED;self.count=UNOBSERVED;self.error=UNOBSERVED;self.error_defined=False
        self.scalar_aux_ack=self.count_aux_ack=self.right_transfer_ack=False
        self.wrapper_return=False;self.wrapper_state='not_returned';self.stopped=False;self.buffer_state='reserved' if buffer else 'not_applicable';self.buffer_written=0;self.query_bytes=None
        self.ref=CallRef(_MINT,self)
class CallRef:
    __slots__=('_state',)
    def __init__(self,mint,state):need(mint is _MINT);object.__setattr__(self,'_state',state)
    def __setattr__(self,k,v):raise TypeError('read-only call reference')
    @property
    def ordinal(self):return self._state.ordinal
    @property
    def api(self):return self._state.api
    @property
    def file_ref(self):return self._state.file.ref
    @property
    def requested(self):return self._state.requested
    @property
    def buffer_ref(self):return self._state.buffer
    @property
    def buffer_generation(self):return self._state.generation

@dataclass(frozen=True,slots=True)
class CapturedContext:
    owner:object
    nonce:object
    specs:tuple
    blobs:object
    digests:object
    early_context:object=None
    def __post_init__(self):
        object.__setattr__(self,'blobs',MappingProxyType(dict(self.blobs)));object.__setattr__(self,'digests',MappingProxyType(dict(self.digests)))
    def bytes_for(self,path):return self.blobs[path]
    def check_work(self):return self.owner.check()
    def __reduce_ex__(self,p):raise TypeError('not serialized authority')

class TestHooks:
    def __init__(self,owner,callback):need(type(owner) is SharedOwner and callable(callback));self.owner=owner;self.callback=callback
class HandoffToken:
    def __init__(self,mint,owner):need(mint is _MINT);self._owner=owner;self._claimed=False
    def claim(self):
        o=self._owner;o._active();o.require(not self._claimed and not o._claimed,'HANDOFF_REPEATED');self._claimed=True
        o.check();o._live_early();o._claimed=True;o._claim_call_count=len(o.registry._calls);o.emit('handoff_claimed',{});return Continuation(_MINT,o)
class Continuation:
    def __init__(self,mint,owner):need(mint is _MINT and owner._claimed);self.owner=owner

class CapturedLoader:
    def __init__(self,owner):self.owner=owner;self.rules={};self.loaded={};self.active=set();self.attempted=[];self.returned=[];self.cache_hits=[];self.records=[]
    def resolve(self,caller,name,level=0):
        o=self.owner;o.check();o.require(caller in self.active and type(name) is str and type(level) is int and level==0,'SOURCE_IMPORT_REFUSED')
        o.require(name in self.rules[caller].dependencies,'SOURCE_IMPORT_REFUSED');return self.load(name)
    def load(self,name):
        o=self.owner;o._active();o.check();o._live_early();o.require(o._claimed and o._compiler is not None and name in self.rules,'SOURCE_LOADER_UNBOUND')
        if name in self.loaded:self.cache_hits.append(name);return self.loaded[name]
        o.require(name not in self.active and name not in self.attempted,'SOURCE_IMPORT_REFUSED');self.attempted.append(name)
        rec=dict(module=name,state='reserved',return_observed=False,accepted=False);self.records.append(rec)
        o.emit('source_compile_reserved',{'module':name});o.check();self.active.add(name);rec['state']='entered_return_unknown'
        try:
            value=o._compiler(name,o.early_context.blobs[self.rules[name].path],lambda n,level=0:self.resolve(name,n,level))
            rec.update(state='return_observed',return_observed=True);o.check();o._live_early();rec['accepted']=True;self.loaded[name]=value;self.returned.append(name);o.emit('source_compile_returned',{'module':name});return value
        except BaseException as error:o.record_error(error,'load_source');raise
        finally:self.active.remove(name)

class SharedOwner:
    def __init__(self,mint,origin):
        need(mint is _MINT and type(origin) is Origin);self.origin=origin;self.nonce=origin._nonce;self.registry=Registry(self)
        self.port=self.sink=None;self.loader=CapturedLoader(self);self.early_context=self.evidence_context=None;self.journal=dict(reservation=0,next_sequence=0,closed=False,close_return_observed=False,close_acknowledged=False,tip=None,events=[])
        self._plan=None;self._specs=();self._early_paths=();self._primary=None;self._secondary=[];self._diagnostics=[];self._refusal=None;self._status='ACTIVE';self._phase='CREATED'
        self._compiler=None;self._hooks=None;self._issued=False;self._claimed=False;self._engine_entered=False;self._finishing=False;self._final=None;self._owned=False;self._negative=False
        self._outputs=dict(reservation=callback_record(),publications={k:callback_record() for k in KINDS},journal_close=callback_record(),total_reserved_bytes=0)
        self._terminal=dict(started=False,candidate_acknowledged=False,original_closures_complete=False,cleanup_acknowledged=False,journal_closed=False,receipt_acknowledged=False,seal_acknowledged=False,final_clock_passed=False,pure_owner_ack=False,result_issued=False)
        self._stages=[];self._gates=[];self._row_bytes=[];self._pins={};self._raw_used=0;self._raw_peak=0;self._capture_used=0;self._read_buffer=self._query_buffer=None
        self._error_phase=None;self._claim_call_count=None
    @property
    def primary(self):return self._primary
    @property
    def secondary(self):return tuple(self._secondary)
    @property
    def finalized(self):return self._final is not None
    def _active(self):
        if self.finalized:raise SharedOwnerError('FINALIZED_MISUSE')
    def record_error(self,error,phase,code=None):
        self._active()
        if error is self._primary or any(e is error for e in self._secondary):return
        if self._primary is None:
            self._primary=error;self._refusal=code or (error.code if isinstance(error,SharedOwnerError) else 'INVALID_INPUT');self._status='REFUSED' if isinstance(error,SharedOwnerError) else 'INCOMPLETE'
        else:self._secondary.append(error)
        token=object();entry=[error,token,None];self._diagnostics.append(entry)
        try:diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message=str(error)[:256],args_repr=[repr(a)[:256] for a in error.args[:8]],format_failed=False)
        except BaseException as formatting:
            diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message='<diagnostic unavailable>',args_repr=[],format_failed=True)
            self._secondary.append(formatting);self._diagnostics.append([formatting,object(),None]);e=self._diagnostics[-1];e[2]=freeze(dict(identity=e[1],phase='diagnostic_format',class_name=type(formatting).__name__[:128],message='<diagnostic unavailable>',args_repr=[],format_failed=True))
        entry[2]=freeze(diag)
    def exception_for_token(self,token):
        for e,t,_ in self._diagnostics:
            if t is token:return e
        raise SharedOwnerError('FOREIGN_IDENTITY')
    def _diag(self,error):
        if error is None:return None
        return next(d for e,_,d in self._diagnostics if e is error)
    def require(self,ok,code='INVALID_INPUT',phase=None):
        self._active()
        if not ok:
            e=SharedOwnerError(code);self.record_error(e,phase or self._diagnostic_phase());raise e
    def _diagnostic_phase(self):
        return self._error_phase or {'CREATED':'entry','PLAN':'admit_plan','RESERVATION':'reserve_output','EARLY_CAPTURE':'capture_early','HANDOFF':'handoff','LOADING':'load_source','CONTINUATION':'continue_once','CHECKERS':'core','FINALIZING':'finalize','FINALIZED':'finalize'}[self._phase]
    def check(self,cleanup=False):
        self._active()
        try:return self.origin.check(cleanup)
        except BaseException as error:self.record_error(error,'final_clock' if cleanup else self._diagnostic_phase());raise
    def charge_raw(self,n):
        self.require(uint(n,131072) and self._raw_used+n<=131072,'JOINT_CAP_EXCEEDED');self.check();self._raw_used+=n;self._raw_peak=max(self._raw_peak,self._raw_used)
    def bind_ports(self,file_view,sink):
        self._active();self.require(self.port is None and self.sink is None and getattr(file_view,'owner',None) is self,'PORT_ALREADY_BOUND');self.port=file_view;self.sink=sink
    def bind_test_hooks(self,hooks):
        self._active();self.require(self._plan is None and self._hooks is None and type(hooks) is TestHooks and hooks.owner is self);self._hooks=hooks
    def bind_test_compiler(self,compiler,stdlib=()):
        self._active();self.require(self._plan is None and self._compiler is None and callable(compiler) and stdlib==());self._compiler=compiler
    def hook(self,point,call=None):
        self.require(point in ('hash_update','copy_bytes','before_final_ack'))
        if self._hooks is not None:
            try:self._hooks.callback(point,self,call)
            except BaseException as error:self.record_error(error,point);raise
    def admit_plan(self,full_specs,early_paths,module_rules):
        self._active();self._phase='PLAN';self.check();self.require(self._plan is None and type(full_specs) is tuple and 0<len(full_specs)<=4 and type(early_paths) is tuple and 0<len(early_paths)<=2 and type(module_rules) is tuple and 0<len(module_rules)<=2)
        keys=set();paths=set()
        for s in full_specs:
            self.require(type(s) is FileSpec and s.role in ('software','owner_metadata','artifact') and s.capture is True and uint(s.size,4096) and type(s.sha256) is str and len(s.sha256)==64 and all(c in '0123456789abcdef' for c in s.sha256))
            try:k=path_key(s.path)
            except BaseException as error:self.record_error(error,'admit_plan');raise
            self.require(k not in keys);keys.add(k);paths.add(s.path)
        self.require(len(set(early_paths))==len(early_paths) and all(p in paths for p in early_paths))
        self.require(all(s.role=='software' and s.capture and s.path.endswith('.py') for s in full_specs if s.path in early_paths))
        rules={r.fullname:r for r in module_rules if type(r) is ModuleRule};self.require(len(rules)==len(module_rules))
        for r in module_rules:self.require(r.path in early_paths and type(r.dependencies) is tuple and len(set(r.dependencies))==len(r.dependencies) and all(n in rules for n in r.dependencies) and type(r.package) is bool)
        def visit(n,trail):
            self.require(n not in trail,'SOURCE_IMPORT_REFUSED')
            for d in rules[n].dependencies:visit(d,trail+(n,))
        for n in rules:visit(n,())
        N,B,M=len(full_specs),len(early_paths),len(module_rules);R=sum((s.size+65535)//65536+16 if s.size else 0 for s in full_specs);C=6*N+R;E=6*N+2*B+2*M+192
        self.require(R<=68 and C<=92 and E<=224 and sum(s.size for s in full_specs)<=16384,'JOINT_CAP_EXCEEDED')
        self._specs=full_specs;self._early_paths=early_paths;self._plan=dict(N=N,B=B,M=M,R=R,C=C,E=E);self.journal['reservation']=E;self.loader.rules=rules
        for i,s in enumerate(full_specs):self.charge_raw(s.size);self.registry._files.append(FileState(self,i,s,s.path in early_paths))
        self.charge_raw(65536);self._read_buffer=BufferRef(self,65536);self.charge_raw(8202);self._query_buffer=BufferRef(self,8202)
    def file_ref(self,path):
        self._active() if self._plan is None else None
        for f in self.registry._files:
            if f.spec.path==path:return f.ref
        raise SharedOwnerError('INVALID_INPUT')
    def file_state(self,ref):
        self.require(type(ref) is FileRecordRef and ref._owner is self and ref._state in self.registry._files,'FOREIGN_IDENTITY');return ref._state
    def _callback(self,rec,action,payload=None,cleanup=False):
        self._active();self.require(not rec['attempted'],'PUBLICATION_REFUSED')
        if payload is not None:
            self.require(type(payload) is bytes and self._outputs['total_reserved_bytes']+len(payload)<=524288,'JOINT_CAP_EXCEEDED');rec.update(prepared_bytes=len(payload),prepared_sha256=sha(payload));self._outputs['total_reserved_bytes']+=len(payload)
        self.check(cleanup);ack=object();rec['attempted']=True
        try:
            value=action(ack);rec['return_observed']=True;rec['acknowledged']=value is ack;self.check(cleanup);self.require(rec['acknowledged'],'PUBLICATION_REFUSED');return value
        except BaseException as error:self.record_error(error,'journal_append' if payload is not None else 'reserve_output');raise
    def reserve_output(self,output_key):
        self._active();self._phase='RESERVATION';self.require(self._plan is not None and self.sink is not None and self.port is not None,'PLAN_NOT_ADMITTED');self.require(type(output_key) is str and 0<len(output_key)<=128 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-' for c in output_key));self.require(not self._outputs['reservation']['attempted'],'OUTPUT_ALREADY_RESERVED')
        rec=self._outputs['reservation'];self.check();ack=object();rec['attempted']=True
        try:
            value=self.sink.reserve(output_key,ack,self.origin.hard_end);rec['return_observed']=True;rec['acknowledged']=value is ack;self._owned=rec['acknowledged'];self.check();self.require(self._owned,'OUTPUT_NOT_OWNED');self.emit('output_reserved',{})
        except BaseException as error:self.record_error(error,'reserve_output');raise
    def emit(self,event,details,cleanup=False):
        self._active();self.require(type(cleanup) is bool and self._owned,'OUTPUT_NOT_OWNED');self.require(not self._outputs['publications']['seal']['acknowledged'],'POST_SEAL_DISPATCH');self.require(not self.journal['closed'],'JOURNAL_CLOSED');self.require(event in EVENTS and type(details) is dict and set(details)<=set(('stage','kind','file_id','module')))
        self.require(details.get('stage') is None or type(details['stage']) is str and details['stage'] in STAGES)
        self.require(details.get('kind') is None or type(details['kind']) is str and details['kind'] in KINDS[:3])
        self.require(details.get('file_id') is None or uint(details['file_id'],len(self.registry._files)-1))
        self.require(details.get('module') is None or type(details['module']) is str and details['module'] in self.loader.rules)
        self.check(cleanup);self.require(len(self.journal['events'])<self._plan['E'],'JOINT_CAP_EXCEEDED')
        row=dict(sequence=len(self.journal['events']),event=event,stage=details.get('stage'),kind=details.get('kind'),file_id=details.get('file_id'),module=details.get('module'),elapsed=self.origin.now-self.origin.start)
        raw=(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8');self.require(len(raw)<=1024,'JOINT_CAP_EXCEEDED')
        obs=dict(row,state='reserved',return_observed=False,acknowledged=False);self.journal['events'].append(obs);self.journal['next_sequence']=len(self.journal['events']);self._row_bytes.append(None)
        self.require(self._outputs['total_reserved_bytes']+len(raw)<=524288,'JOINT_CAP_EXCEEDED');self._outputs['total_reserved_bytes']+=len(raw)
        ack=object();obs['state']='entered_return_unknown'
        try:
            v=self.sink.append(raw,ack,self.origin.hard_end);obs.update(state='return_observed',return_observed=True,acknowledged=v is ack)
            if v is ack:self._row_bytes[-1]=raw
            self.check(cleanup);self.require(v is ack,'PUBLICATION_REFUSED')
        except BaseException as error:self.record_error(error,'journal_append');raise
    def capture_early(self):
        self._active();self._phase='EARLY_CAPTURE';self.require(self._owned and self._plan is not None and self.early_context is None,'OUTPUT_NOT_OWNED')
        for p in self._early_paths:
            ref=self.port.acquire(next(s for s in self._specs if s.path==p));self.port.inspect(ref);self.port.hash_capture(ref)
        fs=tuple(f for f in self.registry._files if f.early);self.early_context=CapturedContext(self,self.nonce,tuple(f.spec for f in fs),{f.spec.path:f.blob for f in fs},{f.spec.path:f.actual_sha for f in fs});return self.early_context
    def _live_early(self):
        self.require(self.early_context is not None and self.early_context.owner is self and self.early_context.nonce is self.nonce,'EARLY_SOURCE_NOT_LIVE_COMPLETE')
        self.require(all(f.hash_complete and f.capture_complete and not f.close_reserved and usable(self.handle(f)) for f in self.registry._files if f.early),'EARLY_SOURCE_NOT_LIVE_COMPLETE')
    def issue_continuation(self):
        self._active();self._phase='HANDOFF';self.check();self.require(not self._issued and self.primary is None,'HANDOFF_REPEATED');self._live_early();self._issued=True;self.emit('handoff_reserved',{});return HandoffToken(_MINT,self)
    def load_source(self,fullname):self._active();self._phase='LOADING';return self.loader.load(fullname)
    def handle(self,file):
        opens=[c for c in self.registry._calls if c.file is file and c.api=='CreateFileW' and c.invoked]
        return opens[0].scalar if opens else UNOBSERVED
    def read_known(self,file):return sum(c.count for c in self.registry._calls if c.file is file and c.api=='ReadFile' and self.defined(c))
    def defined(self,c):return c.api=='ReadFile' and signed_bool(c.scalar) and c.scalar!=0 and uint(c.count,2**32-1) and c.count<=c.requested
    def match_full_roster(self,request,authority):
        self._active();self.check();self._live_early();self.require(type(request.files) is tuple and request.files==self._specs and authority.files==self._specs and authority.owner is self,'EARLY_DESCRIPTOR_MISMATCH');self.proof('admission')
    def hash_remaining(self):
        self._active();self._live_early()
        for f in self.registry._files:
            if not f.early:self.port.acquire(f.spec);self.port.inspect(f.ref);self.port.hash_capture(f.ref)
        self.require(all(f.hash_complete and f.capture_complete for f in self.registry._files),'READ_PROGRESS_INCOMPLETE')
        self.evidence_context=CapturedContext(self,self.nonce,self._specs,{f.spec.path:f.blob for f in self.registry._files},{f.spec.path:f.actual_sha for f in self.registry._files},self.early_context);self.proof('hashes');return self.evidence_context
    def proof(self,name):
        self.require(len(self._gates)<len(GATES) and name==GATES[len(self._gates)],'CHECKER_BINDING_REFUSED');self.check(cleanup=name in GATES[7:]);self._gates.append(name)
    def stage(self,name,action,validator=None):
        self._error_phase=name
        self._active();self.check();row=dict(name=name,state='reserved',return_observed=False,accepted=False,verdict=None);self._stages.append(row);self.emit('stage_reserved',{'stage':name});row['state']='entered_return_unknown'
        try:
            value=action();row.update(state='return_observed',return_observed=True)
            if hasattr(value,'verdict') and type(value.verdict) is str:row['verdict']=value.verdict
            self.check()
            if validator is not None:validator(value)
            row.update(state='accepted',accepted=True);self.emit('stage_returned',{'stage':name});return value
        except BaseException as error:self.record_error(error,name);raise
        finally:self._error_phase=None
    def _packet(self,kind):
        files=self.registry._files
        links={k:self._pins.get(k) for k in ('candidate','cleanup','journal','receipt')}
        if kind in links:links[kind]=None
        value=dict(schema_version=1,kind=kind,scope='pure_shared_owner_seam',status=self._status,elapsed=self.origin.now-self.origin.start,totals=dict(N=self._plan['N'],B=self._plan['B'],M=self._plan['M'],raw_calls=len(self.registry._calls),journal_events=len(self.journal['events']),known_read_bytes=sum(self.read_known(f) for f in files),hashed_bytes=sum(f.hashed for f in files),captured_bytes=sum(f.captured for f in files)),gates=list(self._gates),original_closures=[dict(file_id=f.id,invoked=any(c.file is f and c.api=='CloseHandle' and c.invoked for c in self.registry._calls),return_observed=self._close(f)[0],success=self._close(f)[1]) for f in files],file_digests=[dict(file_id=f.id,size=f.spec.size,sha256=f.actual_sha) for f in files if f.hash_complete],links=links,qualification=dict(QUALIFICATION))
        raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8');self.require(len(raw)<=8192,'JOINT_CAP_EXCEEDED');return raw
    def _publish(self,kind):
        self.require(kind in KINDS and not self._outputs['publications']['seal']['acknowledged'],'POST_SEAL_DISPATCH')
        if not self.journal['closed']:self.emit('publication_reserved',{'kind':kind},cleanup=True)
        raw=self._packet(kind);rec=self._outputs['publications'][kind];self._callback(rec,lambda ack:self.sink.publish(kind,raw,ack,self.origin.hard_end),raw,True);self._pins[kind]=dict(bytes=len(raw),sha256=sha(raw))
        if not self.journal['closed']:self.emit('publication_returned',{'kind':kind},cleanup=True)
    def _close(self,file):
        cs=[c for c in self.registry._calls if c.file is file and c.api=='CloseHandle' and c.invoked]
        if not cs or cs[0].scalar is UNOBSERVED:return False,None
        return True,cs[0].scalar!=0
    def finalize(self,outcome='incomplete'):
        self._active();self.require(outcome=='incomplete');return self._finish(False)
    def _finish(self,normal):
        self._active();self.require(not self._finishing,'PUBLICATION_REFUSED');self._finishing=True;self._phase='FINALIZING';self._terminal['started']=True
        normal=normal and self.primary is None and tuple(self._gates)==GATES[:7]
        def try_action(fn):
            try:fn();return True
            except BaseException as error:self.record_error(error,'finalize');return False
        if self._owned:
            try_action(lambda:self.emit('finalization_reserved',{},cleanup=True))
            if normal: self._terminal['candidate_acknowledged']=try_action(lambda:self._publish('candidate'))
        for f in reversed(self.registry._files):
            if usable(self.handle(f)) and not f.close_reserved:try_action(lambda f=f:self.port.close(f.ref))
        self._terminal['original_closures_complete']=all(not usable(self.handle(f)) or self._close(f)==(True,True) for f in self.registry._files)
        normal=normal and self.primary is None and self._terminal['original_closures_complete']
        if normal:try_action(lambda:self.proof('leases_closed'))
        if self._owned:
            self._terminal['cleanup_acknowledged']=try_action(lambda:self._publish('cleanup'))
            if self.primary is not None and not self._outputs['publications']['failure']['attempted']:try_action(lambda:self._publish('failure'))
            def journal_close():
                self.emit('journal_close_reserved',{},cleanup=True);self.journal['closed']=True
                rec=self._outputs['journal_close'];self._callback(rec,lambda ack:self.sink.close_journal(ack,self.origin.hard_end),cleanup=True)
                self.journal['close_return_observed']=rec['return_observed'];self.journal['close_acknowledged']=rec['acknowledged']
                if all(b is not None for b in self._row_bytes):
                    raw=b''.join(self._row_bytes);self.journal['tip']=dict(bytes=len(raw),sha256=sha(raw));self._pins['journal']=self.journal['tip']
            try_action(journal_close)
            self.journal['close_return_observed']=self._outputs['journal_close']['return_observed'];self.journal['close_acknowledged']=self._outputs['journal_close']['acknowledged'];self._terminal['journal_closed']=self.journal['close_acknowledged']
            if normal and self.primary is None and self._terminal['journal_closed']:
                self._terminal['receipt_acknowledged']=try_action(lambda:self._publish('receipt'))
                if self.primary is None:self._terminal['seal_acknowledged']=try_action(lambda:self._publish('seal'))
                if self.primary is None:
                    try:
                        self.proof('sealed');self.hook('before_final_ack');self.require(self.primary is None,'PUBLICATION_REFUSED');self.proof('final_clock');self._terminal['final_clock_passed']=True;self._terminal['pure_owner_ack']=True
                    except BaseException as error:self.record_error(error,'final_clock')
        self._status=('PURE_SEAM_COMPLETE_NEGATIVE' if self._negative else 'PURE_SEAM_COMPLETE_CONSISTENT') if self._terminal['pure_owner_ack'] else 'REFUSED' if self._status=='REFUSED' else 'INCOMPLETE'
        self._phase='FINALIZED';self._terminal['result_issued']=True;self._final=self._snapshot(True);return self._final
    def _context_report(self,ctx):
        if ctx is None:return None
        return dict(file_ids=[f.id for f in self.registry._files if f.spec in ctx.specs],captured_bytes=sum(len(b) for b in ctx.blobs.values()),digests=dict(ctx.digests),complete=True)
    def snapshot(self):return self._final if self._final is not None else self._snapshot(False)
    def _snapshot(self,finalized):
        fs=self.registry._files;cs=self.registry._calls;calls=[]
        for c in cs:
            tag='HANDLE' if c.api=='CreateFileW' else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32'
            calls.append(dict(ordinal=c.ordinal,api=c.api,file_id=c.file.id,reserved=True,invocation_reserved=c.invoked,raw_scalar=atom(c.scalar,tag),raw_count=atom(c.count,'COUNT32'),raw_error=atom(c.error,'DWORD'),error_defined=c.error_defined,scalar_aux_ack=c.scalar_aux_ack,count_aux_ack=c.count_aux_ack,right_transfer_ack=c.right_transfer_ack,wrapper_return_observed=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,count_defined=self.defined(c),buffer_state=c.buffer_state,buffer_generation=c.generation,raw_buffer_bytes=len(c.query_bytes) if c.query_bytes is not None else None,raw_buffer_sha256=sha(c.query_bytes) if c.query_bytes is not None else None))
        files=[]
        for f in fs:
            fc=[c for c in cs if c.file is f];read=[c for c in fc if c.api=='ReadFile'];observed,success=self._close(f)
            files.append(dict(id=f.id,spec=dict(path=f.spec.path,role=f.spec.role,size=f.spec.size,sha256=f.spec.sha256,capture=f.spec.capture),early=f.early,open_state=f.open_state,handle_fact=atom(self.handle(f),'HANDLE'),identity_state=f.identity_state,identity_queries=list(f.identity_queries),open_invocations=sum(c.invoked for c in fc if c.api=='CreateFileW'),read_invocations=sum(c.invoked for c in read),read_scalar_returns=sum(c.scalar is not UNOBSERVED for c in read),known_read_bytes=self.read_known(f),hashed_bytes=f.hashed,captured_bytes=f.captured,read_count_unknown=any(c.invoked and not self.defined(c) for c in read),hash_complete=f.hash_complete,capture_complete=f.capture_complete,actual_sha256=f.actual_sha,close_reserved=f.close_reserved,close_invocations=sum(c.invoked for c in fc if c.api=='CloseHandle'),close_return_observed=observed,close_success=success,close_state=f.close_state))
        counters={a:dict(reserved=sum(c.api==a for c in cs),invocations=sum(c.api==a and c.invoked for c in cs),scalar_returns=sum(c.api==a and c.scalar is not UNOBSERVED for c in cs),count_values=sum(c.api==a and c.count is not UNOBSERVED for c in cs),wrapper_returns=sum(c.api==a and c.wrapper_return for c in cs)) for a in APIS}
        totals=dict(known_read_bytes=sum(self.read_known(f) for f in fs),hashed_bytes=sum(f.hashed for f in fs),captured_bytes=sum(f.captured for f in fs),read_count_unknown=any(f['read_count_unknown'] for f in files),early_reopens_after_claim=0,early_rehashes_after_claim=0)
        for label,subset in [('early',[f for f in fs if f.early]),('remaining',[f for f in fs if not f.early])]:
            totals[label+'_known_read_bytes']=sum(self.read_known(f) for f in subset);totals[label+'_hashed_bytes']=sum(f.hashed for f in subset);totals[label+'_captured_bytes']=sum(f.captured for f in subset)
        plan=None if self._plan is None else dict(self._plan,calls_used=len(cs),events_used=len(self.journal['events']),capture_used=self._capture_used,raw_storage_used=self._raw_used,raw_storage_peak=self._raw_peak,read_buffer_capacity=self._read_buffer.capacity if self._read_buffer else 0,read_generation=self._read_buffer._generation if self._read_buffer else 0,output_reserved_bytes=self._outputs['total_reserved_bytes'])
        return Snapshot(freeze(dict(scope='pure_shared_owner_seam',status=self._status,phase=self._phase,refusal_code=self._refusal,finalized=finalized,pure_seam_complete=self._terminal['pure_owner_ack'],origin=dict(start=self.origin.start,now=self.origin.now,work_end=self.origin.work_end,hard_end=self.origin.hard_end,clock_state=self.origin._state),plan=plan,files=files,calls=calls,api_counters=counters,byte_totals=totals,early_context=self._context_report(self.early_context),evidence_context=self._context_report(self.evidence_context),loader=dict(bound=self._compiler is not None,attempted=list(self.loader.attempted),returned=list(self.loader.returned),cache_hits=list(self.loader.cache_hits),records=list(self.loader.records)),journal=dict(self.journal),outputs=dict(self._outputs),stages=list(self._stages),gates=list(self._gates),errors=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self._secondary]),terminal=dict(self._terminal),qualification=dict(QUALIFICATION))))

def start_injected(clock,setup):
    started=clock();need(finite(started));owner=SharedOwner(_MINT,Origin(_MINT,clock,started));return setup(owner)
