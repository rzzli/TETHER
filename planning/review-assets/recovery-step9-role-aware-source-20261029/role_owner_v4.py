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
import struct
import re
import role_ledger_codec_v4 as codec

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
    def __init__(self,code):
        if type(code)is not str:raise TypeError('error code must be an exact string')
        super().__init__(code);self.code=code

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
    if type(v) is dict or type(v) is MappingProxyType:return MappingProxyType({k:freeze(x) for k,x in v.items()})
    if type(v) is list or type(v) is tuple:return tuple(freeze(x) for x in v)
    if v is None or type(v)is bool or type(v)is int or type(v)is float or type(v)is str or type(v)is bytes or type(v)is object:return v
    raise SharedOwnerError('UNENCODABLE_RAW')
def thaw(v):
    if type(v) is MappingProxyType:return {k:thaw(x) for k,x in v.items()}
    if type(v) is tuple:return [thaw(x) for x in v]
    return v
def atom(v,tag):
    if v is UNOBSERVED:return dict(tag='UNOBSERVED',value=None)
    if v is None:return dict(tag='NULL',value=None)
    valid=signed_bool(v)if tag in('BOOL','BOOL32')else uint(v,INVALID if tag=='HANDLE'else 0xffffffff)
    if not valid:return dict(tag='UNENCODABLE_RAW',value=None)
    return dict(tag=tag,value=v)
def callback_record():return dict(attempted=False,return_observed=False,acknowledged=False,prepared_bytes=0,prepared_sha256=None,semantics='fictional_callback_not_physical_IO')

@dataclass(frozen=True,slots=True)
class FileSpec:
    path:str
    role:str
    size:int
    sha256:str
    capture:bool
    descriptor_id:object=None
    legacy_role:object=None
@dataclass(frozen=True,slots=True)
class ModuleRule:
    fullname:str
    path:str
    dependencies:tuple
    package:bool=False
@dataclass(frozen=True,slots=True)
class LegacySnapshot:
    _data:object
    def to_dict(self):return thaw(self._data)

class ProducerSnapshot:
    __slots__=('_owner','_data','_profile')
    def __init__(self,mint,owner,data):
        need(mint is _MINT);object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_data',freeze(data));object.__setattr__(self,'_profile',owner.profile)
    def __setattr__(self,k,v):raise TypeError('immutable source snapshot')
    @property
    def owner(self):return self._owner
    def to_dict(self):return thaw(self._data)

@dataclass(frozen=True,slots=True)
class ProducerProfile:
    name:str
    chunk:int
    Nmax:int
    Bmax:int
    Mmax:int
    captured_file:int
    captured_total:int
    Cmax:int
    Emax:int
    raw_cap:int

PROFILE_N4=ProducerProfile('ORIGINAL7_N4',65536,4,2,2,4096,16384,92,224,131072)
PROFILE_ORIGINAL7_1M=ProducerProfile('ORIGINAL7_PROSPECTIVE',1048576,256,128,128,8388608,33554432,16384,2240,127809034)
ROLES=('captured_software','captured_metadata','hash_only_bulk')
ROLE_WIRE=dict(zip(ROLES,('CAPTURED_SOFTWARE','CAPTURED_METADATA','HASH_ONLY_BULK')))
ARTIFACT_CAPS={'candidate-ledger.bin':14800384,'terminal-ledger.bin':14800384,'journal.jsonl':2293760,'producer-report.json':8192,**{k+'.json':8192 for k in KINDS},'child/result.partial.jsonl':7995392,'child/attempt.json':4096,'child/failure.json':65536,'stdout.bin':65536,'stderr.bin':65536}

@dataclass(frozen=True,slots=True)
class GeneratedArtifactBytes:
    _mint:object
    owner:object
    origin:object
    nonce:object
    registry:object
    kind:str
    phase:str
    raw:bytes
    sha256:str
    def __post_init__(self):need(self._mint is _MINT and type(self.raw) is bytes)

class CaptureNotRequested(SharedOwnerError):
    def __init__(self):super().__init__('CAPTURE_NOT_REQUESTED')

class _DiagnosticGuard:
    __slots__=('owner','cleanup','outer','remaining')
    def __init__(self,owner,cleanup):self.owner=owner;self.cleanup=cleanup;self.outer=False;self.remaining=0
    def __enter__(self):
        o=self.owner
        o._active()
        if not self.cleanup and o.primary is not None:raise o.primary
        if o._diagnostic_guard is None:
            if o._diag_committed+o._diag_borrowed+2>o._diag_capacity:raise SharedOwnerError('DIAGNOSTIC_CAPACITY')
            self.outer=True;self.remaining=2;o._diag_borrowed+=2;o._diagnostic_guard=self
        return o._diagnostic_guard
    def __exit__(self,kind,error,tb):
        try:
            if error is not None:
                try:self.owner.record_error(error,self.owner._diagnostic_phase())
                except BaseException:raise error
        finally:
            if self.outer:
                o=self.owner;o._diag_borrowed-=self.remaining;self.remaining=0;o._diagnostic_guard=None
        return False

class _ClockCarrier:
    __slots__=('value',)
    def __init__(self):self.value=UNOBSERVED

class Origin:
    __slots__=('_clock','_start','_now','_nonce','_state','_clock_carrier')
    def __init__(self,mint,clock,started,carrier=None):
        need(mint is _MINT and callable(clock) and finite(started))
        for k,v in dict(_clock=clock,_start=started,_now=started,_nonce=object(),_state='ok').items():object.__setattr__(self,k,v)
        object.__setattr__(self,'_clock_carrier',carrier if carrier is not None else _ClockCarrier())
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
            carrier=self._clock_carrier;carrier.value=UNOBSERVED;carrier.value=self._clock();n=carrier.value
            need(finite(n) and n>=self._now,'CLOCK_INVALID')
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
        self.hashed=0;self.captured=0;self.hash_attempted=False;self.hash_complete=False;self.capture_complete=False;self.actual_sha=None;self.blob=None;self.assembly=None;self.hasher=None
        self.capture_state='PENDING' if spec.capture else 'NOT_REQUESTED';self.hash_unknown=False;self.copy_unknown=False
        self.descriptor_id=i if spec.descriptor_id is None else spec.descriptor_id
        self.close_reserved=False;self.close_state='not_attempted'
        self._open_call=self._close_call=None;self._read_reservations=0;self._known_read_bytes=0
class Registry:
    __slots__=('_owner','_files','_calls','_file_by_exact_path','_slots')
    def __init__(self,owner):object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_files',[]);object.__setattr__(self,'_calls',[]);object.__setattr__(self,'_file_by_exact_path',{});object.__setattr__(self,'_slots',[])
    def __setattr__(self,k,v):raise TypeError('canonical registry is source-owned')
class CallState:
    __slots__=('owner','ordinal','api','file','requested','buffer','generation','invoked','scalar','count','error','error_definition','scalar_aux_ack','count_aux_ack','right_transfer_ack','wrapper_return','wrapper_state','stopped','buffer_state','buffer_written','query_bytes','_reservation_fold','_read_fold_phase','_read_contribution','ref','pre_clock','post_clock','pre_clock_attempted','post_clock_attempted','hash_attempted','hash_return','copy_attempted','copy_return','input_handle','prepared','hash_count','copy_count','_hash_fold_phase','_copy_fold_phase')
    def __init__(self,owner,i,api=None,file=None,requested=None,buffer=None):
        self.owner=owner;self.ordinal=i;self.api=api;self.file=file;self.requested=requested;self.buffer=buffer;self.generation=buffer._generation if buffer else None
        self.invoked=False;self.scalar=UNOBSERVED;self.count=UNOBSERVED;self.error=UNOBSERVED;self.error_definition=UNOBSERVED
        self.scalar_aux_ack=self.count_aux_ack=self.right_transfer_ack=False
        self.wrapper_return=False;self.wrapper_state='not_returned';self.stopped=False;self.buffer_state='reserved' if buffer else 'not_applicable';self.buffer_written=0;self.query_bytes=None
        self._reservation_fold='unapplied';self._read_fold_phase='pending';self._read_contribution=None
        self.ref=CallRef(_MINT,self)
        self.pre_clock=self.post_clock=UNOBSERVED;self.pre_clock_attempted=self.post_clock_attempted=False
        self.hash_attempted=self.copy_attempted=False;self.hash_return=self.copy_return=UNOBSERVED;self.input_handle=UNOBSERVED
        self.prepared=api is not None;self.hash_count=self.copy_count=0
        self._hash_fold_phase=self._copy_fold_phase='pending'
    @property
    def error_defined(self):return self.error_definition is True
    @error_defined.setter
    def error_defined(self,value):self.error_definition=value
    def prepare(self,api,file,requested,buffer):
        need(not self.prepared);self.api=api;self.file=file;self.requested=requested;self.buffer=buffer;self.generation=buffer._generation if buffer else None;self.buffer_state='reserved' if buffer else 'not_applicable';self.prepared=True
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
    _issuer:object=None
    def __post_init__(self):
        need(self._issuer is _MINT)
        object.__setattr__(self,'blobs',MappingProxyType(dict(self.blobs)));object.__setattr__(self,'digests',MappingProxyType(dict(self.digests)))
    def bytes_for(self,path):
        if path not in self.blobs:
            if any(s.path==path and not s.capture for s in self.specs):raise CaptureNotRequested()
            raise SharedOwnerError('INVALID_INPUT')
        return self.blobs[path]
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
    __slots__=('_owner',)
    def __init__(self,mint,owner):need(mint is _MINT and owner._claimed);object.__setattr__(self,'_owner',owner)
    def __setattr__(self,key,value):raise TypeError('read-only continuation owner')
    @property
    def owner(self):return self._owner

class CapturedLoader:
    def __init__(self,owner):self.owner=owner;self.rules={};self.loaded={};self.active=set();self.attempted=[];self.returned=[];self.cache_hits=[];self.records=[]
    def resolve(self,caller,name,level=0):
        o=self.owner;o.check();o.require(caller in self.active and type(name) is str and type(level) is int and level==0,'SOURCE_IMPORT_REFUSED')
        o.require(name in self.rules[caller].dependencies,'SOURCE_IMPORT_REFUSED');return self.load(name)
    def load(self,name):
        with self.owner.operation_guard():
            o=self.owner;o._active();o.check();o._live_early();o.require(o._claimed and o._compiler is not None and name in self.rules,'SOURCE_LOADER_UNBOUND')
            if name in self.loaded:self.cache_hits.append(name);return self.loaded[name]
            o.require(name not in self.active and name not in self.attempted,'SOURCE_IMPORT_REFUSED');self.attempted.append(name)
            rec=dict(module=name,state='reserved',return_observed=False,accepted=False);self.records.append(rec)
            o.emit('source_compile_reserved',{'module':name});o.check();self.active.add(name);rec['state']='entered_return_unknown'
            try:
                value=o._compiler(name,o.early_context.blobs[self.rules[name].path],lambda n,level=0:self.resolve(name,n,level))
                rec.update(state='return_observed',return_observed=True);self.returned.append(name);o.check();o._live_early();rec['accepted']=True;self.loaded[name]=value;o.emit('source_compile_returned',{'module':name});return value
            except BaseException as error:o.record_error(error,'load_source');raise
            finally:self.active.remove(name)

class _Rows:
    __slots__=('count','get')
    def __init__(self,count,get):self.count=count;self.get=get
    def __len__(self):return self.count
    def __iter__(self):
        for i in range(self.count):yield self.get(i)

def _same_typed(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return len(a)==len(b)and set(a)==set(b)and all(_same_typed(a[k],b[k])for k in a)
    if type(a) is tuple or type(a) is list:return len(a)==len(b)and all(_same_typed(x,y)for x,y in zip(a,b))
    if type(a) is float:return struct.pack('<d',a)==struct.pack('<d',b)
    return type(a)in(str,int,bool,bytes,type(None))and a==b

def _clock_atom(value):
    if value is UNOBSERVED:return dict(tag='UNOBSERVED',value=None)
    tag='I64'if type(value)is int else'F64'if type(value)is float else'INVALID'
    result=dict(tag=tag,value=value);codec.clock_bits(result);return result

def _utf8_prefix(text,cap):
    raw=text.encode('utf-8','replace')
    if len(raw)<=cap:return raw,False
    return raw[:cap].decode('utf-8','ignore').encode(),True

class SharedOwner:
    def __init__(self,mint,origin,profile=PROFILE_N4):
        need(mint is _MINT and type(origin) is Origin and (profile is PROFILE_N4 or profile is PROFILE_ORIGINAL7_1M));self._origin=origin;self._nonce=origin._nonce;self._registry=Registry(self);self._profile=profile
        self._port=self._sink=None;self._loader=CapturedLoader(self);self._early_context=self._evidence_context=None;self.journal=dict(reservation=0,next_sequence=0,closed=False,close_return_observed=False,close_acknowledged=False,tip=None,events=[])
        self._plan=None;self._specs=();self._early_paths=();self._primary=None;self._secondary=[];self._diagnostics=[];self._refusal=None;self._status='ACTIVE';self._phase='CREATED'
        self._compiler=None;self._hooks=None;self._issued=False;self._claimed=False;self._engine_entered=False;self._finishing=False;self._final=None;self._owned=False;self._negative=False
        self._outputs=dict(reservation=callback_record(),publications={k:callback_record() for k in KINDS},journal_close=callback_record(),total_reserved_bytes=0)
        self._terminal=dict(started=False,candidate_acknowledged=False,original_closures_complete=False,cleanup_acknowledged=False,journal_closed=False,receipt_acknowledged=False,seal_acknowledged=False,final_clock_passed=False,pure_owner_ack=False,result_issued=False)
        self._stages=[];self._gates=[];self._row_bytes=[];self._pins={};self._raw_used=0;self._raw_peak=0;self._capture_used=0;self._read_buffer=self._query_buffer=None
        self._error_phase=None;self._claim_call_count=None;self._accounting_fault=None
        self._diag_capacity=64;self._diag_committed=0;self._diag_borrowed=0;self._diagnostic_guard=None
        self._generated={k:dict(state='RESERVED',attempted=False,return_observed=False,eligible=False,raw=None,sha256=None,phase=None,artifact=None)for k in ARTIFACT_CAPS};self._generated_used=0;self._generated_assembly=None;self._building=False;self._injected_current=None
        self._capture_assembly_owner=None
        self._assembly_live=0;self._assembly_peak=0
        self._artifact_sources={}
    profile=property(lambda self:self._profile)
    nonce=property(lambda self:self._nonce)
    registry=property(lambda self:self._registry)
    port=property(lambda self:self._port)
    sink=property(lambda self:self._sink)
    loader=property(lambda self:self._loader)
    early_context=property(lambda self:self._early_context)
    evidence_context=property(lambda self:self._evidence_context)
    @property
    def origin(self):return self._origin
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
        self._commit_diagnostic_slot();token=object();entry=[error,token,None];self._diagnostics.append(entry)
        try:diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message=str(error)[:256],args_repr=[repr(a)[:256] for a in error.args[:8]],format_failed=False)
        except BaseException as formatting:
            diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message='<diagnostic unavailable>',args_repr=[],format_failed=True)
            self._secondary.append(formatting);self._commit_diagnostic_slot();self._diagnostics.append([formatting,object(),None]);e=self._diagnostics[-1];e[2]=freeze(dict(identity=e[1],phase='diagnostic_format',class_name='<formatter-failure>',message='<diagnostic unavailable>',args_repr=[],format_failed=True))
        entry[2]=freeze(diag)
    def _commit_diagnostic_slot(self):
        if self._diag_committed>=self._diag_capacity:raise SharedOwnerError('DIAGNOSTIC_CAPACITY')
        g=self._diagnostic_guard
        if g is not None and g.remaining:
            g.remaining-=1;self._diag_borrowed-=1
        self._diag_committed+=1
    def operation_guard(self,cleanup=False):return _DiagnosticGuard(self,cleanup)
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
        if not cleanup:
            self._require_accounting_work()
            if self.primary is not None:raise self.primary
        try:return self.origin.check(cleanup)
        except BaseException as error:self.record_error(error,'final_clock' if cleanup else self._diagnostic_phase());raise
    def charge_raw(self,n):
        self.require(uint(n,self.profile.raw_cap) and self._raw_used+n+self._assembly_live<=self.profile.raw_cap,'JOINT_CAP_EXCEEDED');self.check();self._raw_used+=n;self._raw_peak=max(self._raw_peak,self._raw_used)
    def bind_ports(self,file_view,sink):
        self._active();self.require(self.port is None and self.sink is None and getattr(file_view,'owner',None) is self,'PORT_ALREADY_BOUND');self._port=file_view;self._sink=sink
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
        self._active();self._phase='PLAN';self.check();p=self.profile;self.require(self._plan is None and type(full_specs) is tuple and 0<len(full_specs)<=p.Nmax and type(early_paths) is tuple and len(early_paths)<=p.Bmax and type(module_rules) is tuple and len(module_rules)<=p.Mmax)
        keys=set();paths=set()
        for s in full_specs:
            self.require(type(s) is FileSpec and type(s.role) is str and s.role in ROLES and type(s.capture) is bool and s.capture==(s.role!='hash_only_bulk') and uint(s.size,(1<<63)-1) and(not s.capture or s.size<=p.captured_file)and type(s.sha256) is str and len(s.sha256)==64 and all(c in '0123456789abcdef' for c in s.sha256))
            self.require(s.legacy_role is None or p is PROFILE_N4 and type(s.legacy_role) is str and s.legacy_role in('software','owner_metadata','artifact')and (s.legacy_role=='software')==(s.role=='captured_software')and s.capture)
            try:k=path_key(s.path)
            except BaseException as error:self.record_error(error,'admit_plan');raise
            self.require(k not in keys);keys.add(k);paths.add(s.path)
        self.require(len(set(early_paths))==len(early_paths) and all(p in paths for p in early_paths))
        self.require(all(s.role=='captured_software' and s.capture and s.path.endswith('.py') for s in full_specs if s.path in early_paths))
        ids=tuple(s.descriptor_id for s in full_specs)
        self.require(all(x is None for x in ids)or all(uint(x,len(full_specs)-1)for x in ids)and sorted(ids)==list(range(len(full_specs))))
        self.require(all(type(r)is ModuleRule and type(r.fullname)is str and type(r.dependencies)is tuple and all(type(n)is str for n in r.dependencies)for r in module_rules))
        rules={r.fullname:r for r in module_rules};self.require(len(rules)==len(module_rules))
        for r in module_rules:self.require(type(r.fullname) is str and len(r.fullname)<=512 and re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',r.fullname,re.ASCII)is not None and r.path in early_paths and type(r.dependencies) is tuple and len(set(r.dependencies))==len(r.dependencies) and all(type(n)is str and n in rules for n in r.dependencies) and type(r.package) is bool)
        visited=set()
        def visit(n,trail):
            self.require(n not in trail,'SOURCE_IMPORT_REFUSED')
            if n in visited:return
            for d in rules[n].dependencies:visit(d,trail+(n,))
            visited.add(n)
        for n in rules:visit(n,())
        N,B,M=len(full_specs),len(early_paths),len(module_rules);R=sum(s.size//p.chunk+int(s.size%p.chunk!=0)+16 if s.size else 0 for s in full_specs);C=6*N+R;E=6*N+2*B+2*M+192
        self.require(C<=p.Cmax and E<=p.Emax and sum(s.size for s in full_specs if s.capture)<=p.captured_total,'JOINT_CAP_EXCEEDED')
        self._specs=full_specs;self._early_paths=early_paths;self._plan=dict(N=N,B=B,M=M,R=R,C=C,E=E);self.journal['reservation']=E;self.loader.rules=rules
        self._diag_capacity=2*(N+E+32)
        try:
            for i,s in enumerate(full_specs):
                if s.capture:self.charge_raw(s.size)
                f=FileState(self,i,s,s.path in early_paths);self.registry._files.append(f);self.registry._file_by_exact_path[s.path]=f
            self.registry._slots.extend(CallState(self,i)for i in range(C))
        except BaseException as error:self._accounting_failed(None,error,'admit_plan');raise
        self.charge_raw(p.chunk);self._read_buffer=BufferRef(self,p.chunk);self.charge_raw(8202);self._query_buffer=BufferRef(self,8202)
    def begin_capture(self,file):
        self.require(file.spec.capture and(self._capture_assembly_owner is None or self._capture_assembly_owner is file),'CAPTURE_ASSEMBLY_BUSY');self.check()
        if file.assembly is None:
            self.require(self._raw_used+file.spec.size<=self.profile.raw_cap,'JOINT_CAP_EXCEEDED')
            file.assembly=bytearray(file.spec.size);self._capture_assembly_owner=file;self._assembly_live=file.spec.size;self._assembly_peak=max(self._assembly_peak,self._assembly_live)
        return file.assembly
    def finish_capture(self,file,blob):
        self.require(file.spec.capture and self._capture_assembly_owner is file and type(blob)is bytes and len(blob)==file.spec.size,'INVALID_INPUT')
        self.require(self._capture_used+len(blob)<=self.profile.captured_total,'JOINT_CAP_EXCEEDED')
        file.blob=blob;self._capture_used+=len(blob);file.capture_complete=True;file.capture_state='COMPLETE'
        file.assembly=None;self._capture_assembly_owner=None;self._assembly_live=0
        return blob
    def reserve_call(self,api,file,requested,buffer):
        self.require(self._plan is not None and len(self.registry._calls)<self._plan['C'],'JOINT_CAP_EXCEEDED')
        call=self.registry._slots[len(self.registry._calls)];call.prepare(api,file,requested,buffer)
        try:self.registry._calls.append(call);self._index_reserved_call(call)
        except BaseException as error:
            # Negative bookkeeping only: retain an already prepared, unentered
            # canonical slot if an append wrapper failed before publishing it.
            if len(self.registry._calls)==call.ordinal:
                try:list.append(self.registry._calls,call)
                except BaseException:pass
            self._accounting_failed(call,error,'pre_dispatch');raise
        return call
    def call_clock(self,call,which,cleanup=False):
        self.require(which in('pre','post'),'INVALID_INPUT')
        try:
            if which=='pre':
                call.pre_clock_attempted=True;call.pre_clock=self.origin._clock();value=call.pre_clock
            else:
                call.post_clock_attempted=True;call.post_clock=self.origin._clock();value=call.post_clock
            valid=finite(value)and(type(value)is not int or -(1<<63)<=value<(1<<63))
            self.require(valid and value>=self.origin.now,'CLOCK_INVALID');object.__setattr__(self.origin,'_now',value)
            if value>=self.origin.hard_end:object.__setattr__(self.origin,'_state','hard_expired');self.require(False,'HARD_DEADLINE')
            if not cleanup and value>=self.origin.work_end:object.__setattr__(self.origin,'_state','work_expired');self.require(False,'WORK_DEADLINE')
            return value
        except BaseException as error:
            self.record_error(error,'final_clock'if cleanup else self._diagnostic_phase());raise
    def file_ref(self,path):
        self._active() if self._plan is None else None
        f=self.registry._file_by_exact_path.get(path) if type(path) is str else None
        if f is not None:return f.ref
        raise SharedOwnerError('INVALID_INPUT')
    def file_state(self,ref):
        self.require(type(ref) is FileRecordRef and ref._owner is self,'FOREIGN_IDENTITY')
        f=ref._state;self.require(uint(f.id,len(self.registry._files)-1) and self.registry._files[f.id] is f,'FOREIGN_IDENTITY');return f
    def _require_accounting_work(self):
        self._active()
        if self._accounting_fault is not None:raise self.primary if self.primary is not None else self._accounting_fault
    def _accounting_failed(self,call,error,phase):
        if self._accounting_fault is None:self._accounting_fault=error
        if type(call) is CallState and call.owner is self:call.stopped=True
        try:self.record_error(error,phase)
        except BaseException:raise error
    def _index_reserved_call(self,call):
        if call.api!='CloseHandle':self._require_accounting_work()
        self.require(call.owner is self and uint(call.ordinal,len(self.registry._calls)-1) and self.registry._calls[call.ordinal] is call,'FOREIGN_IDENTITY')
        if call._reservation_fold=='committed':return
        self.require(call._reservation_fold=='unapplied','INVALID_INPUT');call._reservation_fold='applying';f=call.file
        if call.api=='CreateFileW':
            self.require(f._open_call is None,'INVALID_INPUT');f._open_call=call
        elif call.api=='CloseHandle':
            self.require(f._close_call is None,'INVALID_INPUT');f._close_call=call
        elif call.api=='ReadFile':
            limit=f.spec.size//self.profile.chunk+int(f.spec.size%self.profile.chunk!=0)+16 if f.spec.size else 0
            self.require(uint(f._read_reservations,limit-1),'JOINT_CAP_EXCEEDED');f._read_reservations+=1
        call._reservation_fold='committed'
    def _fold_read_fact(self,call):
        self._require_accounting_work();self.require(call.owner is self and call.api=='ReadFile' and uint(call.ordinal,len(self.registry._calls)-1) and self.registry._calls[call.ordinal] is call,'FOREIGN_IDENTITY')
        contribution=call.count if self.defined(call) else None
        if call._read_fold_phase=='committed':
            self.require(contribution is not None and contribution==call._read_contribution,'INVALID_INPUT');return
        self.require(call._read_fold_phase=='pending' and call._read_contribution is None,'INVALID_INPUT')
        if contribution is None:return
        f=call.file;total=f._known_read_bytes+contribution;self.require(uint(total,f.spec.size),'INVALID_INPUT')
        call._read_fold_phase='applying';call._read_contribution=contribution;f._known_read_bytes=total;call._read_fold_phase='committed'
    def _canonical_projection(self,compare_cache=False,include_calls=True):
        # A declared reporting/consistency pass, never a hot-work cache repair.
        if compare_cache:self.check();self.require(self.primary is None,'INVALID_INPUT','consistency')
        fs=self.registry._files;groups=[dict(open=None,close=None,open_invocations=0,close_invocations=0,read_reservations=0,read_invocations=0,read_scalar_returns=0,known=0,unknown=False,hashed=0,copied=0,hash_unknown=False,copy_unknown=False,read_generation=0) for f in fs]
        counters={api:dict(reserved=0,invocations=0,scalar_returns=0,count_values=0,wrapper_returns=0) for api in APIS};calls=[]
        for ordinal,c in enumerate(self.registry._calls):
            if compare_cache:self.require(c.owner is self and c.ordinal==ordinal and uint(c.file.id,len(fs)-1) and fs[c.file.id] is c.file and c._reservation_fold=='committed','INVALID_INPUT','consistency')
            g=groups[c.file.id];counter=counters[c.api];counter['reserved']+=1;counter['invocations']+=int(c.invoked);counter['scalar_returns']+=int(c.scalar is not UNOBSERVED);counter['count_values']+=int(c.count is not UNOBSERVED);counter['wrapper_returns']+=int(c.wrapper_return)
            defined=self.defined(c)
            if c.api=='CreateFileW':
                if g['open'] is None:g['open']=c
                g['open_invocations']+=int(c.invoked)
            elif c.api=='CloseHandle':
                if g['close'] is None:g['close']=c
                g['close_invocations']+=int(c.invoked)
            elif c.api=='ReadFile':
                g['read_generation']=c.generation if c.generation is not None else 0
                g['read_reservations']+=1;g['read_invocations']+=int(c.invoked);g['read_scalar_returns']+=int(c.scalar is not UNOBSERVED)
                if defined:g['known']+=c.count
                if c.invoked and not defined:g['unknown']=True
                if c.hash_return is not UNOBSERVED and defined:g['hashed']+=c.count
                if c.copy_return is not UNOBSERVED and defined:g['copied']+=c.count
                g['hash_unknown']|=c.hash_attempted and c.hash_return is UNOBSERVED
                g['copy_unknown']|=c.copy_attempted and c.copy_return is UNOBSERVED
                if compare_cache:self.require((c._read_fold_phase=='committed' and c._read_contribution==c.count) if defined else (c._read_fold_phase=='pending' and c._read_contribution is None),'INVALID_INPUT','consistency')
            tag='HANDLE' if c.api=='CreateFileW' else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32'
            if include_calls:calls.append(dict(ordinal=c.ordinal,api=c.api,file_id=c.file.id,reserved=True,invocation_reserved=c.invoked,raw_scalar=atom(c.scalar,tag),raw_count=atom(c.count,'COUNT32'),raw_error=atom(c.error,'DWORD'),error_defined=c.error_defined,scalar_aux_ack=c.scalar_aux_ack,count_aux_ack=c.count_aux_ack,right_transfer_ack=c.right_transfer_ack,wrapper_return_observed=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,count_defined=defined,buffer_state=c.buffer_state,buffer_generation=c.generation,raw_buffer_bytes=len(c.query_bytes) if c.query_bytes is not None else None,raw_buffer_sha256=sha(c.query_bytes) if c.query_bytes is not None else None))
        files=[];totals=dict(known_read_bytes=0,hashed_bytes=0,captured_bytes=0,read_count_unknown=False,early_reopens_after_claim=0,early_rehashes_after_claim=0,early_known_read_bytes=0,early_hashed_bytes=0,early_captured_bytes=0,remaining_known_read_bytes=0,remaining_hashed_bytes=0,remaining_captured_bytes=0)
        for f,g in zip(fs,groups):
            if compare_cache:self.require(f._open_call is g['open'] and f._close_call is g['close'] and f._read_reservations==g['read_reservations'] and f._known_read_bytes==g['known'],'INVALID_INPUT','consistency')
            oc,cc=g['open'],g['close'];handle=oc.scalar if oc is not None and oc.invoked else UNOBSERVED
            open_state='unopened' if oc is None else 'reserved' if not oc.invoked else 'entered_return_unknown' if handle is UNOBSERVED else 'owned' if usable(handle) else 'known_failure_no_handle' if uint(handle,INVALID)and handle==INVALID else 'ownership_unknown'
            observed=cc is not None and cc.invoked and signed_bool(cc.scalar);success=cc.scalar!=0 if observed else None
            close_state='returned_success' if observed and success else 'returned_failure' if observed else 'entered_return_unknown' if cc is not None and cc.invoked else 'not_dispatched_deadline' if f.close_state=='not_dispatched_deadline' else 'reserved' if f.close_reserved else 'not_attempted'
            capture_state='NOT_REQUESTED'if not f.spec.capture else'COMPLETE'if f.capture_complete else'FAILED'if f.hash_attempted and self.primary is not None else'PENDING'
            files.append(dict(id=f.id,spec=dict(path=f.spec.path,role=f.spec.role,size=f.spec.size,sha256=f.spec.sha256,capture=f.spec.capture),early=f.early,open_state=open_state,handle_fact=atom(handle,'HANDLE'),identity_state=f.identity_state,identity_queries=list(f.identity_queries),open_invocations=g['open_invocations'],read_invocations=g['read_invocations'],read_scalar_returns=g['read_scalar_returns'],known_read_bytes=g['known'],hashed_bytes=g['hashed'],captured_bytes=g['copied'],read_count_unknown=g['unknown'],hash_complete=f.hash_complete,capture_complete=f.capture_complete,actual_sha256=f.actual_sha,close_reserved=f.close_reserved,close_invocations=g['close_invocations'],close_return_observed=observed,close_success=success,close_state=close_state,capture_state=capture_state,hash_unknown=g['hash_unknown'],copy_unknown=g['copy_unknown'],read_generation=g['read_generation']))
            label='early' if f.early else 'remaining'
            for key,value in [('known_read_bytes',g['known']),('hashed_bytes',g['hashed']),('captured_bytes',g['copied'])]:totals[key]+=value;totals[label+'_'+key]+=value
            totals['read_count_unknown']=totals['read_count_unknown'] or g['unknown']
        if compare_cache:self.check()
        return dict(calls=calls if include_calls else None,files=files,api_counters=counters,byte_totals=totals)
    def _callback(self,rec,action,payload=None,cleanup=False):
        with self.operation_guard(cleanup=cleanup):
            self._active();self.require(not rec['attempted'],'PUBLICATION_REFUSED')
            if payload is not None:
                self.require(type(payload) is bytes and self._outputs['total_reserved_bytes']+len(payload)<=(524288 if self.profile is PROFILE_N4 else 40139776),'JOINT_CAP_EXCEEDED');rec.update(prepared_bytes=len(payload),prepared_sha256=sha(payload));self._outputs['total_reserved_bytes']+=len(payload)
            self.check(cleanup);ack=object();rec['attempted']=True
            try:
                value=action(ack);rec['return_observed']=True;rec['acknowledged']=value is ack;self.check(cleanup);self.require(rec['acknowledged'],'PUBLICATION_REFUSED');return value
            except BaseException as error:self.record_error(error,'journal_append' if payload is not None else 'reserve_output');raise
    def reserve_output(self,output_key):
        with self.operation_guard():
            self._active();self._phase='RESERVATION';self.require(self._plan is not None and self.sink is not None and self.port is not None,'PLAN_NOT_ADMITTED');self.require(type(output_key) is str and 0<len(output_key)<=128 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-' for c in output_key));self.require(not self._outputs['reservation']['attempted'],'OUTPUT_ALREADY_RESERVED')
            rec=self._outputs['reservation'];self.check();ack=object();rec['attempted']=True
            try:
                value=self.sink.reserve(output_key,ack,self.origin.hard_end);rec['return_observed']=True;rec['acknowledged']=value is ack;self._owned=rec['acknowledged'];self.check();self.require(self._owned,'OUTPUT_NOT_OWNED');self.emit('output_reserved',{})
            except BaseException as error:self.record_error(error,'reserve_output');raise
    def emit(self,event,details,cleanup=False):
        with self.operation_guard(cleanup=cleanup):
            self._active();self.require(type(cleanup) is bool and self._owned,'OUTPUT_NOT_OWNED');self.require(not self._outputs['publications']['seal']['acknowledged'],'POST_SEAL_DISPATCH');self.require(not self.journal['closed'],'JOURNAL_CLOSED');self.require(event in EVENTS and type(details) is dict and set(details)<=set(('stage','kind','file_id','module')))
            self.require(details.get('stage') is None or type(details['stage']) is str and details['stage'] in STAGES)
            self.require(details.get('kind') is None or type(details['kind']) is str and details['kind'] in KINDS[:3])
            self.require(details.get('file_id') is None or uint(details['file_id'],len(self.registry._files)-1))
            self.require(details.get('module') is None or type(details['module']) is str and details['module'] in self.loader.rules)
            self.check(cleanup);self.require(len(self.journal['events'])<self._plan['E'],'JOINT_CAP_EXCEEDED')
            row=dict(sequence=len(self.journal['events']),event=event,stage=details.get('stage'),kind=details.get('kind'),file_id=details.get('file_id'),module=details.get('module'),elapsed=self.origin.now-self.origin.start)
            raw=(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8');self.require(len(raw)<=1024,'JOINT_CAP_EXCEEDED')
            obs=dict(row,state='reserved',return_observed=False,acknowledged=False);self.journal['events'].append(obs);self.journal['next_sequence']=len(self.journal['events']);self._row_bytes.append(None)
            self.require(self._outputs['total_reserved_bytes']+len(raw)<=(524288 if self.profile is PROFILE_N4 else 40139776),'JOINT_CAP_EXCEEDED');self._outputs['total_reserved_bytes']+=len(raw)
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
        fs=tuple(f for f in self.registry._files if f.early);self._early_context=CapturedContext(self,self.nonce,tuple(f.spec for f in fs),{f.spec.path:f.blob for f in fs},{f.spec.path:f.actual_sha for f in fs},_issuer=_MINT);return self.early_context
    def _live_early(self):
        self.require(self.early_context is not None and self.early_context.owner is self and self.early_context.nonce is self.nonce,'EARLY_SOURCE_NOT_LIVE_COMPLETE')
        self.require(all(f.hash_complete and f.capture_complete and not f.close_reserved and usable(self.handle(f)) for f in self.registry._files if f.early),'EARLY_SOURCE_NOT_LIVE_COMPLETE')
    def issue_continuation(self):
        self._active();self._phase='HANDOFF';self.check();self.require(not self._issued and self.primary is None,'HANDOFF_REPEATED');self._live_early();self._issued=True;self.emit('handoff_reserved',{});return HandoffToken(_MINT,self)
    def load_source(self,fullname):self._active();self._phase='LOADING';return self.loader.load(fullname)
    def handle(self,file):
        c=file._open_call
        if c is None:return UNOBSERVED
        self.require(c.owner is self and c.file is file and uint(c.ordinal,len(self.registry._calls)-1) and self.registry._calls[c.ordinal] is c,'FOREIGN_IDENTITY')
        return c.scalar if c.invoked else UNOBSERVED
    def read_known(self,file):
        self._require_accounting_work();self.require(uint(file.id,len(self.registry._files)-1) and self.registry._files[file.id] is file,'FOREIGN_IDENTITY');return file._known_read_bytes
    def defined(self,c):return c.api=='ReadFile' and signed_bool(c.scalar) and c.scalar!=0 and uint(c.count,2**32-1) and c.count<=c.requested
    def match_full_roster(self,request,authority):
        self._active();self.check();self._live_early();self.require(type(request.files) is tuple and request.files==self._specs and authority.files==self._specs and authority.owner is self,'EARLY_DESCRIPTOR_MISMATCH');self.proof('admission')
    def hash_remaining(self):
        self._active();self._live_early()
        for f in self.registry._files:
            if not f.early:self.port.acquire(f.spec);self.port.inspect(f.ref);self.port.hash_capture(f.ref)
        self.require(all(f.hash_complete and (not f.spec.capture or f.capture_complete)for f in self.registry._files),'READ_PROGRESS_INCOMPLETE')
        self._evidence_context=CapturedContext(self,self.nonce,self._specs,{f.spec.path:f.blob for f in self.registry._files if f.spec.capture},{f.spec.path:f.actual_sha for f in self.registry._files},self.early_context,_issuer=_MINT);self.proof('hashes');return self.evidence_context
    def proof(self,name):
        self.require(len(self._gates)<len(GATES) and name==GATES[len(self._gates)],'CHECKER_BINDING_REFUSED');self.check(cleanup=name in GATES[7:])
        if name=='consistency':
            try:self._canonical_projection(compare_cache=True,include_calls=False)
            except BaseException as error:self._accounting_failed(None,error,'consistency');raise
        self._gates.append(name)
    def stage(self,name,action,validator=None):
        with self.operation_guard():
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
        projection=self._canonical_projection(include_calls=False);tot=projection['byte_totals']
        def ref(name):
            r=self._generated[name]
            return dict(kind=name,phase=r['phase'],bytes=len(r['raw']),sha256=r['sha256'])if r['eligible']else None
        links={k:ref(n)for k,n in(('journal','journal.jsonl'),('producer_report','producer-report.json'),('cleanup','cleanup.json'),('receipt','receipt.json'))}
        if kind in links:links[kind]=None
        totals=dict(known_read_bytes=tot['known_read_bytes'],hashed_bytes=tot['hashed_bytes'],copied_bytes=tot['captured_bytes'],captured_input_bytes=self._capture_used,generated_bytes=self._generated_used,read_unknown=tot['read_count_unknown'],hash_unknown=any(f['hash_unknown']for f in projection['files']),copy_unknown=any(f['copy_unknown']for f in projection['files']))
        value=dict(schema_version=2,kind=kind,scope='role_aware_producer_format_v1',status='INCOMPLETE'if self.primary is not None else'OBSERVED_NEGATIVE'if self._negative else'OBSERVED_COMPLETE',elapsed=_clock_atom(self.origin.now-self.origin.start),totals=totals,gates=list(self._gates),ledger_refs=dict(candidate=ref('candidate-ledger.bin'),terminal=ref('terminal-ledger.bin')),links=links,diagnostic_counts=dict(committed=len(self._diagnostics),primary=int(self.primary is not None),secondary=len(self._secondary),formatter=sum(d[2]['phase']=='diagnostic_format'for d in self._diagnostics if d[2]is not None)),qualification={k:False for k in('originals','real_entry','real_FFI','physical_IO','new84_runtime','resource_fit','scientific')})
        raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8');self.require(len(raw)<=8192,'JOINT_CAP_EXCEEDED');return raw
    def _publish(self,kind):
        self.require(kind in KINDS and not self._outputs['publications']['seal']['acknowledged'],'POST_SEAL_DISPATCH')
        self.require(self._generated_assembly is None,'UNISSUED_ARTIFACT')
        if not self.journal['closed']:self.emit('publication_reserved',{'kind':kind},cleanup=True)
        raw=self._packet(kind);self._install_generated(kind+'.json',raw,'TERMINAL'if kind!='candidate'else'CANDIDATE');rec=self._outputs['publications'][kind];self._callback(rec,lambda ack:self.sink.publish(kind,raw,ack,self.origin.hard_end),raw,True);self._pins[kind]=dict(bytes=len(raw),sha256=sha(raw))
        if not self.journal['closed']:self.emit('publication_returned',{'kind':kind},cleanup=True)
    def _make_report(self):
        with self.operation_guard(cleanup=True):
            self.require(self._generated_assembly is None,'UNISSUED_ARTIFACT')
            packet=json.loads(self._packet('cleanup'))
            artifacts=[dict(kind=k,state=v['state'],attempted=v['attempted'],return_observed=v['return_observed'],eligible=v['eligible'],bytes=len(v['raw'])if v['raw']is not None else None,sha256=v['sha256'],phase=v['phase'])for k,v in self._generated.items()]
            value=dict(schema_version=2,format_id='ROLE_AWARE_LEDGER_1',profile=self.profile.name,phase='TERMINAL',status=packet['status'],counts=dict(N=self._plan['N'],used_C=len(self.registry._calls),M=self._plan['M'],used_E=len(self.journal['events'])),totals=packet['totals'],ledger_refs=packet['ledger_refs'],artifacts=artifacts,diagnostic_counts=packet['diagnostic_counts'],qualification=packet['qualification'])
            raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode();self.require(len(raw)<=8192,'JOINT_CAP_EXCEEDED');return self._install_generated('producer-report.json',raw,'TERMINAL')
    def _close(self,file):
        c=file._close_call
        if c is None:return False,None
        self.require(c.owner is self and c.file is file and uint(c.ordinal,len(self.registry._calls)-1) and self.registry._calls[c.ordinal] is c,'FOREIGN_IDENTITY')
        if not c.invoked or not signed_bool(c.scalar):return False,None
        return True,c.scalar!=0
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
            if normal:
                try_action(lambda:self.freeze_generated('candidate-ledger.bin'))
                try_action(lambda:self._publish('candidate'));self._terminal['candidate_acknowledged']=self._outputs['publications']['candidate']['acknowledged']
        for f in reversed(self.registry._files):
            if usable(self.handle(f)) and not f.close_reserved:try_action(lambda f=f:self.port.close(f.ref))
        self._terminal['original_closures_complete']=all(not usable(self.handle(f)) or self._close(f)==(True,True) for f in self.registry._files)
        normal=normal and self.primary is None and self._terminal['original_closures_complete']
        if normal:try_action(lambda:self.proof('leases_closed'))
        if self._owned:
            if self._plan is not None and self.registry._files:try_action(lambda:self.freeze_generated('terminal-ledger.bin'))
            try_action(lambda:self._publish('cleanup'));self._terminal['cleanup_acknowledged']=self._outputs['publications']['cleanup']['acknowledged']
            if self.primary is not None and not self._outputs['publications']['failure']['attempted']:try_action(lambda:self._publish('failure'))
            try_action(self._make_report)
            def journal_close():
                self.emit('journal_close_reserved',{},cleanup=True);self.journal['closed']=True
                rec=self._outputs['journal_close'];self._callback(rec,lambda ack:self.sink.close_journal(ack,self.origin.hard_end),cleanup=True)
                self.journal['close_return_observed']=rec['return_observed'];self.journal['close_acknowledged']=rec['acknowledged']
                if all(b is not None for b in self._row_bytes):
                    raw=b''.join(self._row_bytes);self.journal['tip']=dict(bytes=len(raw),sha256=sha(raw));self._pins['journal']=self.journal['tip'];self._install_generated('journal.jsonl',raw,'TERMINAL');self._row_bytes=[None]*len(self._row_bytes)
            try_action(journal_close)
            self.journal['close_return_observed']=self._outputs['journal_close']['return_observed'];self.journal['close_acknowledged']=self._outputs['journal_close']['acknowledged'];self._terminal['journal_closed']=self.journal['close_acknowledged']
            if normal and self.primary is None and self._terminal['journal_closed']:
                try_action(lambda:self._publish('receipt'));self._terminal['receipt_acknowledged']=self._outputs['publications']['receipt']['acknowledged']
                if self.primary is None:
                    try_action(lambda:self._publish('seal'));self._terminal['seal_acknowledged']=self._outputs['publications']['seal']['acknowledged']
                if self.primary is None:
                    try:
                        self.proof('sealed');self.hook('before_final_ack');self.require(self.primary is None,'PUBLICATION_REFUSED');self.proof('final_clock');self._terminal['final_clock_passed']=True;self._terminal['pure_owner_ack']=True
                    except BaseException as error:self.record_error(error,'final_clock')
        self._status=('PURE_SEAM_COMPLETE_NEGATIVE' if self._negative else 'PURE_SEAM_COMPLETE_CONSISTENT') if self._terminal['pure_owner_ack'] else 'REFUSED' if self._status=='REFUSED' else 'INCOMPLETE'
        self._phase='FINALIZED';self._terminal['result_issued']=True;self._final=self._snapshot(True);return self._final
    def _context_report(self,ctx):
        if ctx is None:return None
        return dict(file_ids=[f.id for f in self.registry._files if f.spec.path in ctx.blobs],captured_bytes=sum(len(b) for b in ctx.blobs.values()),digests=dict(ctx.digests),complete=True)
    def _wire_call(self,index):
        c=self.registry._calls[index];f=c.file;cf={k:False for k in codec.ENUMS['call_flags_bits']}
        scalar_tag='HANDLE'if c.api=='CreateFileW'else'DWORD'if c.api in('GetFileType','GetFinalPathNameByHandleW')else'BOOL'
        so=c.scalar is not UNOBSERVED;co=c.count is not UNOBSERVED;eo=c.error is not UNOBSERVED
        scalar_valid=so and((c.scalar is None or uint(c.scalar,INVALID))if scalar_tag=='HANDLE'else uint(c.scalar,0xffffffff)if scalar_tag=='DWORD'else signed_bool(c.scalar))
        defined=self.defined(c);frame={'GetFileInformationByHandleEx':8,'GetFinalPathNameByHandleW':8202,'GetFileSizeEx':8}.get(c.api,0)
        hash_return=c.hash_return is not UNOBSERVED;copy_return=c.copy_return is not UNOBSERVED
        account=c._read_fold_phase=='applying'or c._hash_fold_phase=='applying'or c._copy_fold_phase=='applying'
        cf.update(INVOKED=c.invoked,SCALAR_OBSERVED=so,SCALAR_NULL=so and c.scalar is None,COUNT_OBSERVED=co,COUNT_DEFINED=defined,ERROR_OBSERVED=eo,ERROR_DEFINED=c.error_definition is True,ERROR_DEFINITION_OBSERVED=c.error_definition is not UNOBSERVED,SCALAR_AUX_ACK=c.scalar_aux_ack,COUNT_AUX_ACK=c.count_aux_ack,RIGHT_TRANSFER_ACK=c.right_transfer_ack,WRAPPER_RETURNED=c.wrapper_return,STOPPED=c.stopped,QUERY_CAPTURE_OBSERVED=c.query_bytes is not None,QUERY_DEFINED=c.query_bytes is not None and scalar_valid and c.scalar not in(None,0,INVALID),BUFFER_DATA_OBSERVED=c.buffer_state in('raw_retained','defined'),ACCOUNTING_FAULT=account,CLOSE_RIGHT_CONSUMED=c.api=='CloseHandle'and f.close_reserved,IDENTITY_VERIFIED_AT_DISPATCH=c.api=='ReadFile'and f.identity_witness is not None,SCALAR_DOMAIN_VALID=scalar_valid,COUNT_DOMAIN_VALID=co and uint(c.count,0xffffffff),ERROR_DOMAIN_VALID=eo and uint(c.error,0xffffffff),PRE_CLOCK_ATTEMPTED=c.pre_clock_attempted,POST_CLOCK_ATTEMPTED=c.post_clock_attempted,PRE_CLOCK_RETURN_OBSERVED=c.pre_clock is not UNOBSERVED,POST_CLOCK_RETURN_OBSERVED=c.post_clock is not UNOBSERVED,HASH_ATTEMPTED=c.hash_attempted,HASH_RETURN_OBSERVED=hash_return,COPY_ATTEMPTED=c.copy_attempted,COPY_RETURN_OBSERVED=copy_return,CAPTURE_REQUESTED=f.spec.capture,MALFORMED_RAW=so and not scalar_valid,INPUT_HANDLE_PRESENT=c.input_handle is not UNOBSERVED,REQUESTED_PRESENT=c.api=='ReadFile',BUFFER_PRESENT=c.buffer is not None,QUERY_SPAN_PRESENT=bool(frame))
        fold='COMMITTED'if c._read_fold_phase=='committed'else'FAILED_BEFORE_COMMIT'if c._read_fold_phase=='applying'else'PENDING'
        if account:cf['STOPPED']=True
        qoff=8218*f.id+{'GetFileInformationByHandleEx':0,'GetFinalPathNameByHandleW':8,'GetFileSizeEx':8210}.get(c.api,0)if frame else 0
        error_id=0 if c.stopped and self.primary is not None and self._diagnostics else None
        r=dict(ordinal=index,file_id=f.id,api=c.api,record_version=1,flags=cf,requested=c.requested if c.requested is not None else 0,buffer_id=None if c.buffer is None else 0 if c.api=='ReadFile'else 1,phase='original_close'if c.api=='CloseHandle'else'binding_invoke',generation=c.generation or 0,buffer_written=c.buffer_written,scalar_atom=atom(c.scalar,scalar_tag),count_atom=atom(c.count,'COUNT32'),error_atom=atom(c.error,'DWORD'),error_definition_atom=atom(UNOBSERVED,'DEFINEDNESS')if c.error_definition is UNOBSERVED else dict(tag='DEFINEDNESS',value=c.error_definition),hashed_contribution=c.count if hash_return and defined else 0,captured_contribution=c.count if copy_return and defined else 0,known_count_contribution=c.count if defined else 0,query_offset=qoff,query_length=frame,input_handle_atom=atom(c.input_handle,'HANDLE'),pre_dispatch_clock=_clock_atom(c.pre_clock),post_binding_clock=_clock_atom(c.post_clock),error_id=error_id,path_id=f.id,fold_state=fold,buffer_state=c.buffer_state.upper())
        return tuple(r[k]for k in codec.CALL_KEYS)
    def _wire_source(self,phase):
        projection=self._canonical_projection(include_calls=False);files=[];paths=[];pathoff=0;module_ids={name:i for i,name in enumerate(self.loader.rules)};module_paths={rule.path:i for i,rule in enumerate(self.loader.rules.values())}
        for f,view in zip(self.registry._files,projection['files']):
            path=f.spec.path.encode('utf-8');paths.append(path);ff={k:False for k in codec.ENUMS['file_flags_bits']}
            ff.update(EXPECTED_DIGEST_PRESENT=True,ACTUAL_DIGEST_PRESENT=f.actual_sha is not None,CAPTURE_REQUESTED=f.spec.capture,HASH_ATTEMPTED=f.hash_attempted,HASH_COMPLETE=f.hash_complete,CAPTURE_COMPLETE=f.capture_complete,READ_UNKNOWN=view['read_count_unknown'],HASH_UNKNOWN=view['hash_unknown'],COPY_UNKNOWN=view['copy_unknown'],CLOSE_RESERVED=f.close_reserved,EARLY=f.early,CLOSE_SUCCESS_KNOWN=view['close_return_observed'],CLOSE_SUCCESS_TRUE=view['close_success']is True,ASSEMBLY_RETAINED=f.assembly is not None,BLOB_ISSUED=f.blob is not None,EXPECTED_SIZE_PRESENT=True)
            r=dict(ordinal=f.id,role=ROLE_WIRE[f.spec.role],capture_state=view['capture_state'].upper(),target_class='ORIGINAL',open_state=view['open_state'].upper(),identity_state=f.identity_state.upper(),close_state=view['close_state'].upper(),flags=ff,descriptor_id=f.descriptor_id,path_offset=pathoff,path_bytes=len(path),path_utf16_units=len(f.spec.path.encode('utf-16-le'))//2,expected_size=f.spec.size,expected_sha256=bytes.fromhex(f.spec.sha256),actual_sha256=bytes.fromhex(f.actual_sha)if f.actual_sha is not None else None,open_ordinal=f._open_call.ordinal if f._open_call is not None else None,close_ordinal=f._close_call.ordinal if f._close_call is not None else None,known_read_bytes=view['known_read_bytes'],hashed_bytes=view['hashed_bytes'],captured_bytes=view['captured_bytes'],query_offset=8218*f.id,query_length=8218,first_diagnostic=None,read_reservations=f._read_reservations,read_invocations=view['read_invocations'],captured_blob_length=len(f.blob)if f.blob is not None else 0,early_ordinal=self._early_paths.index(f.spec.path)if f.early else None,path_id=f.id,read_generation=view['read_generation'],module_ordinal=module_paths.get(f.spec.path))
            files.append(tuple(r[k]for k in codec.FILE_KEYS));pathoff+=len(path)
        def query_chunks():
            for f in self.registry._files:
                found={self.registry._calls[i].api:self.registry._calls[i].query_bytes for i in f.identity_queries}
                for api,n in(('GetFileInformationByHandleEx',8),('GetFinalPathNameByHandleW',8202),('GetFileSizeEx',8)):yield found.get(api)or bytes(n)
        modules=[];names=[];edges=[];nameoff=0
        for i,(name,rule)in enumerate(self.loader.rules.items()):
            b=name.encode('ascii');names.append(b);deps=tuple(module_ids[n]for n in rule.dependencies)
            r=dict(ordinal=i,file_ordinal=self.registry._file_by_exact_path[rule.path].id,flags=dict(PACKAGE=rule.package,RETURN_OBSERVED=name in self.loader.returned,ACCEPTED=name in self.loader.loaded,CACHED=name in self.loader.loaded),dependency_count=len(deps),name_offset=nameoff,name_length=len(b),edge_offset=len(edges),first_diagnostic=None,attempt_order=self.loader.attempted.index(name)if name in self.loader.attempted else None,return_order=self.loader.returned.index(name)if name in self.loader.returned else None,cache_hit_count=self.loader.cache_hits.count(name))
            modules.append(tuple(r[k]for k in codec.MODULE_KEYS));edges.extend(deps);nameoff+=len(b)
        diagnostics=[]
        for i,(error,token,meta)in enumerate(self._diagnostics):
            meta=thaw(meta);cls,ct=_utf8_prefix(meta['class_name'],96);msg,mt=_utf8_prefix(meta['message'],512);args=list(meta['args_repr']);at=False
            while True:
                argraw=json.dumps(args,separators=(',',':'),ensure_ascii=True).encode()
                if len(argraw)<=256:break
                at=True
                if args and len(args[-1])>8:args[-1]=args[-1][:len(args[-1])//2]
                elif args:args.pop()
                else:break
            label=meta['phase'];label='canonical_reconcile'if label in('hash_return_fold','copy_return_fold')else label
            self.require(label in codec.ENUMS['phase_code'],'INVALID_INPUT')
            r=dict(ordinal=i,state='FORMAT_FALLBACK'if meta['format_failed']else'COMMITTED',flags=dict(CLASS_TRUNCATED=ct,MESSAGE_TRUNCATED=mt,ARGS_TRUNCATED=at,FORMAT_FAILED=meta['format_failed']),phase=label,opaque_identity_id=i+1,call_ordinal=None,secondary_of=0 if i else None,class_bytes=len(cls),message_bytes=len(msg),args_bytes=len(argraw),clock_atom=_clock_atom(self.origin.now),severity='PRIMARY'if i==0 else'FORMATTER_FAILURE'if label=='diagnostic_format'else'SECONDARY',class_utf8=cls,message_utf8=msg,args_utf8=argraw)
            diagnostics.append(tuple(r[k]for k in codec.DIAG_KEYS))
        header_flags={k:False for k in codec.ENUMS['header_flags_bits']};header_flags.update(READ_UNKNOWN=any(f['read_count_unknown']for f in projection['files']),HASH_UNKNOWN=any(f['hash_unknown']for f in projection['files']),COPY_UNKNOWN=any(f['copy_unknown']for f in projection['files']),ACCOUNTING_FAULT=self._accounting_fault is not None,PRIMARY_PRESENT=self.primary is not None,CLOCK_INVALID=self.origin._state=='invalid',PREVIOUS_LEDGER_PRESENT=phase=='TERMINAL'and self._generated['candidate-ledger.bin']['eligible'])
        def header():
            self.check(cleanup=phase=='TERMINAL')
            prior=self._generated['candidate-ledger.bin']
            return dict(profile=self.profile.name,phase=phase,status='INCOMPLETE'if self.primary is not None else'OBSERVED_NEGATIVE'if self._negative else'OBSERVED_COMPLETE',origin_data_id=1,ledger_sequence=1 if phase=='CANDIDATE'else 2,start_clock=_clock_atom(self.origin.start),latest_clock=_clock_atom(self.origin.now),freeze_clock=_clock_atom(self.origin.now),previous_ledger_sha256=bytes.fromhex(prior['sha256'])if header_flags['PREVIOUS_LEDGER_PRESENT']else None,reserved_R=self._plan['R'],reserved_C=self._plan['C'],reserved_E=self._plan['E'],early_count=self._plan['B'],read_chunk=self.profile.chunk,flags=header_flags)
        return dict(header=header,files=tuple(files),calls=_Rows(len(self.registry._calls),self._wire_call),queries=codec.ByteChunks(8218*len(files),query_chunks),paths=codec.ByteChunks(pathoff,lambda:iter(paths)),modules=tuple(modules),module_names=codec.ByteChunks(nameoff,lambda:iter(names)),module_edges=tuple(edges),diagnostics=tuple(diagnostics))
    def _consume_ledger(self,raw,source):
        expected={k:source[k]for k in codec.SECTIONS};seen={k:0 for k in codec.SECTIONS}
        for kind,index,value in codec.iter_checked_records(raw,check=lambda:self.check(cleanup=True)):
            if kind=='header':
                for field,actual_source in source['header_wire']:self.require(field in value and _same_typed(value[field],actual_source),'WIRE_SOURCE_MISMATCH')
                continue
            items=expected[kind]
            if kind in('files','calls','modules','diagnostics'):
                row=items.get(index)if type(items)is _Rows else items[index];self.require(_same_typed(value,row),'WIRE_SOURCE_MISMATCH');seen[kind]+=1
            elif kind=='module_edges':self.require(value==items[index],'WIRE_SOURCE_MISMATCH');seen[kind]+=1
            else:
                at=0
                for chunk in items.factory():self.require(value[at:at+len(chunk)]==chunk,'WIRE_SOURCE_MISMATCH');at+=len(chunk)
                self.require(at==len(value),'WIRE_SOURCE_MISMATCH');seen[kind]=at
        for kind,items in expected.items():self.require(seen[kind]==len(items),'WIRE_SOURCE_MISMATCH')
    def freeze_generated(self,kind):
        with self.operation_guard(cleanup=kind=='terminal-ledger.bin'):
            self._active();self.require(kind in('candidate-ledger.bin','terminal-ledger.bin')and self._plan is not None and self._generated_assembly is None,'UNISSUED_ARTIFACT')
            rec=self._generated[kind];self.require(not rec['attempted'],'PUBLICATION_REFUSED');rec['attempted']=True;rec['state']='BUILDING';phase='CANDIDATE'if kind.startswith('candidate')else'TERMINAL';rec['phase']=phase;self._generated_assembly=object()
            try:
                source=self._wire_source(phase)
                def capture_header(fields):source['header_wire']=fields
                rec['raw']=codec.build_ledger(source['header'],*(source[k]for k in codec.SECTIONS),check=lambda:self.check(cleanup=phase=='TERMINAL'),capture_header=capture_header)
                raw=rec['raw'];rec['return_observed']=True;self._generated_used+=len(raw)
                self.require(len(raw)<=ARTIFACT_CAPS[kind]and self._generated_used<=40139776,'JOINT_CAP_EXCEEDED');self.check(cleanup=phase=='TERMINAL');self._consume_ledger(raw,source);self.check(cleanup=phase=='TERMINAL')
                artifact=GeneratedArtifactBytes(_MINT,self,self.origin,self.nonce,self.registry,kind,phase,raw,sha(raw))
                rec.update(sha256=artifact.sha256,eligible=True,state='ISSUED',artifact=artifact)
                # Retain only immutable phase provenance, never live row readers.
                # Every field was compared against canonical slots before issuance.
                self._artifact_sources[kind]=(source['header_wire'],raw);self._generated_assembly=None
                return artifact
            except BaseException as error:rec['state']='UNISSUED_PARTIAL';self.record_error(error,'freeze');raise
    def generated_bytes(self,kind):
        if type(kind)is not str or kind not in self._generated:raise SharedOwnerError('UNISSUED_ARTIFACT')
        rec=self._generated[kind]
        if not rec['eligible']:raise SharedOwnerError('UNISSUED_ARTIFACT')
        return rec['raw']
    def generated_artifact(self,kind):
        self.generated_bytes(kind)
        return self._generated[kind]['artifact']
    def _install_generated(self,kind,raw,phase):
        self.require(self._generated_assembly is None and kind in self._generated and type(raw)is bytes,'UNISSUED_ARTIFACT')
        rec=self._generated[kind];self.require(not rec['attempted']and len(raw)<=ARTIFACT_CAPS[kind]and self._generated_used+len(raw)<=40139776,'JOINT_CAP_EXCEEDED')
        rec['raw']=raw;rec.update(attempted=True,state='BUILDING',phase=phase,return_observed=True);self._generated_used+=len(raw)
        try:
            self.check(cleanup=True)
            artifact=GeneratedArtifactBytes(_MINT,self,self.origin,self.nonce,self.registry,kind,phase,raw,sha(raw));rec.update(sha256=artifact.sha256,eligible=True,state='ISSUED',artifact=artifact);return artifact
        except BaseException as error:
            rec['state']='UNISSUED_PARTIAL';self.record_error(error,'freeze');raise
    def check_generated(self,artifact):
        self.require(type(artifact)is GeneratedArtifactBytes and artifact._mint is _MINT and artifact.owner is self and artifact.origin is self.origin and artifact.nonce is self.nonce and artifact.registry is self.registry,'FOREIGN_IDENTITY')
        rec=self._generated[artifact.kind];self.require(rec['eligible']and artifact.raw is rec['raw']and artifact.sha256==sha(artifact.raw),'UNISSUED_ARTIFACT')
        if artifact.kind in self._artifact_sources:
            header_fields,phase_bytes=self._artifact_sources[artifact.kind];self.require(artifact.raw is phase_bytes,'FOREIGN_IDENTITY')
            seen_header=False
            for kind,index,value in codec.iter_checked_records(artifact.raw,check=lambda:self.check(cleanup=True)):
                if kind=='header':
                    for field,source_fact in header_fields:self.require(field in value and _same_typed(value[field],source_fact),'WIRE_SOURCE_MISMATCH')
                    seen_header=True
            self.require(seen_header,'WIRE_SOURCE_MISMATCH')
        self.check(cleanup=True);return artifact
    def snapshot(self):return self._final if self._final is not None else self._snapshot(False)
    def _snapshot(self,finalized):
        projection=self._canonical_projection(include_calls=self.profile is PROFILE_N4);cs=projection['calls']
        plan=None if self._plan is None else dict(self._plan,calls_used=len(self.registry._calls),events_used=len(self.journal['events']),capture_used=self._capture_used,raw_storage_used=self._raw_used,raw_storage_peak=self._raw_peak,read_buffer_capacity=self._read_buffer.capacity if self._read_buffer else 0,read_generation=self._read_buffer._generation if self._read_buffer else 0,output_reserved_bytes=self._outputs['total_reserved_bytes'])
        return ProducerSnapshot(_MINT,self,dict(schema_version=2,scope='role_aware_producer_seam',status=self._status,phase=self._phase,refusal_code=self._refusal,finalized=finalized,pure_seam_complete=self._terminal['pure_owner_ack'],origin=dict(start=self.origin.start,now=self.origin.now,work_end=self.origin.work_end,hard_end=self.origin.hard_end,clock_state=self.origin._state),plan=plan,files=projection['files'],calls=cs,api_counters=projection['api_counters'],byte_totals=projection['byte_totals'],early_context=self._context_report(self.early_context),evidence_context=self._context_report(self.evidence_context),loader=dict(bound=self._compiler is not None,attempted=list(self.loader.attempted),returned=list(self.loader.returned),cache_hits=list(self.loader.cache_hits),records=list(self.loader.records)),journal=dict(self.journal),outputs=dict(self._outputs),stages=list(self._stages),gates=list(self._gates),errors=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self._secondary]),terminal=dict(self._terminal),qualification=dict(QUALIFICATION),generated={k:dict(state=v['state'],eligible=v['eligible'],bytes=len(v['raw'])if v['raw']is not None else None,sha256=v['sha256'])for k,v in self._generated.items()},assembly_live=self._assembly_live,assembly_peak=self._assembly_peak))

def start_injected(clock,setup,*,profile=PROFILE_N4):
    carrier=_ClockCarrier();carrier.value=clock();started=carrier.value;need(finite(started));codec.clock_bits(_clock_atom(started));owner=SharedOwner(_MINT,Origin(_MINT,clock,started,carrier),profile);return setup(owner)

PROFILE_1M=PROFILE_ORIGINAL7_1M

def project_legacy(snapshot,*,check):
    need(callable(check));check()
    if type(snapshot)is not ProducerSnapshot or snapshot._profile is not PROFILE_N4:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    owner=snapshot.owner;data=snapshot.to_dict()
    if data['calls']is None or any(not f['spec']['capture']for f in data['files']):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for diagnostic in (data['errors']['primary'],*data['errors']['secondary']):
        if diagnostic is not None and diagnostic['phase'] not in ('binding_invoke', 'pre_dispatch', 'after_scalar_before_aux', 'after_scalar_before_right_transfer', 'error_copy', 'RawReturn_allocation', 'after_count_before_aux', 'buffer_copy', 'hash_update', 'post_call_clock', 'identity_query', 'handoff', 'close_wrapper', 'cleanup_publication', 'entry', 'bind_ports', 'bind_test_hooks', 'bind_test_compiler', 'admit_plan', 'reserve_output', 'capture_early', 'issue_continuation', 'claim_continuation', 'load_source', 'continue_once', 'finalize', 'journal_append', 'journal_close', 'publish_candidate', 'publish_cleanup', 'publish_failure', 'publish_receipt', 'publish_seal', 'original_close', 'diagnostic_format', 'final_clock', 'authority_factory', 'checker_factory', 'admit_reconcile', 'hash_remaining', 'archive', 'journal', 'resources', 'core', 'consistency', 'copy_bytes', 'before_final_ack'):
            raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    data.pop('schema_version');data.pop('generated');data.pop('assembly_live');data.pop('assembly_peak');data['scope']='pure_shared_owner_seam'
    for f in data['files']:
        for key in('capture_state','hash_unknown','copy_unknown','read_generation'):f.pop(key,None)
        spec=owner._specs[f['id']];f['spec']['role']=spec.legacy_role or('software'if spec.role=='captured_software'else'owner_metadata')
        if f['handle_fact']['tag']=='UNENCODABLE_RAW':raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for c in data['calls']:
        if any(c[k]['tag']=='UNENCODABLE_RAW'for k in('raw_scalar','raw_count','raw_error')):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    result=LegacySnapshot(freeze(data));check();return result
