"""Portable first-fact adoption model v3, NOT a native FFI or production owner.

All constructor preconditions are source-issued HARNESS_ONLY assumptions.
The C/ctypes-to-first-Python-store window and live engine integration are unproved.
No files, fixture labels, expected projections, SDK or platform APIs are consumed.
"""
from dataclasses import dataclass
import hashlib
from types import MappingProxyType

UNOBSERVED=object()
_MINT=object()
INVALID=2**64-1
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle','GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')
FIXED_BUFFERS={'GetFileInformationByHandleEx':8,'GetFinalPathNameByHandleW':8202,'GetFileSizeEx':8,'GetFileAttributesExW':36,'FindFirstFileExW':592,'FindNextFileW':592}
API_KINDS={'CreateFileW':('original_file','output_file'),'GetFileType':('original_file','output_file'),'GetFileInformationByHandleEx':('original_file','output_file'),'GetFinalPathNameByHandleW':('original_file','output_file'),'GetFileSizeEx':('original_file','output_file'),'ReadFile':('original_file',),'CloseHandle':('original_file','output_file'),'GetFileAttributesExW':('namespace',),'FindFirstFileExW':('search',),'FindNextFileW':('search',),'FindClose':('search',),'CreateDirectoryW':('namespace',),'WriteFile':('output_file',),'FlushFileBuffers':('output_file',)}
CONTEXT_KINDS=('owner','origin','nonce','registry','port','output','source_context','loader','journal')
PHASES=('pre_dispatch','after_scalar_before_aux','after_scalar_before_right_transfer','error_copy','RawReturn_allocation','after_count_before_aux','buffer_copy','hash_update','post_call_clock','identity_query','handoff','close_wrapper','cleanup_publication')

def _uint(v,cap):return type(v) is int and 0<=v<=cap
def _bool(v):return type(v) is int and -2**31<=v<2**31
def _usable(v):return _uint(v,INVALID) and v not in (0,INVALID)
def _need(v,code):
    if not v:raise AdoptionError(code)

class AdoptionError(RuntimeError):
    def __init__(self,code):super().__init__(code);self.code=code

@dataclass(frozen=True,slots=True,eq=False)
class HarnessRef:
    _brand:object
    kind:str
    scope:str='HARNESS_ONLY'

class HarnessOrigin:
    __slots__=('_brand','kind','scope','start_ns','now_ns','work_end_ns','hard_end_ns')
    def __init__(self,mint,brand,start_ns,now_ns,work_end_ns,hard_end_ns):
        _need(mint is _MINT and all(_uint(n,2**63-1) for n in (start_ns,now_ns,work_end_ns,hard_end_ns)) and start_ns<=now_ns and work_end_ns==start_ns+295000000000 and hard_end_ns==start_ns+300000000000,'origin_domain')
        for k,v in dict(_brand=brand,kind='origin',scope='HARNESS_ONLY',start_ns=start_ns,now_ns=now_ns,work_end_ns=work_end_ns,hard_end_ns=hard_end_ns).items():object.__setattr__(self,k,v)
    def __setattr__(self,k,v):raise TypeError('source-issued Origin is immutable')

@dataclass(frozen=True,slots=True,eq=False)
class Context:
    owner:object
    origin:object
    nonce:object
    registry:object
    port:object
    output:object
    early_context:object
    loader:object
    journal:object

def _freeze(v):
    if type(v) is dict:return MappingProxyType({k:_freeze(x) for k,x in v.items()})
    if type(v) is list:return tuple(_freeze(x) for x in v)
    return v
def _thaw(v):
    if type(v) is MappingProxyType:return {k:_thaw(x) for k,x in v.items()}
    if type(v) is tuple:return [_thaw(x) for x in v]
    return v
@dataclass(frozen=True,slots=True)
class Snapshot:
    _data:object
    def to_dict(self):return _thaw(self._data)

class _Slot:
    __slots__=('id','kind','initial_handle','closer','identity_ref','close_state','identity_prefix')
    def __init__(self,identity,kind,handle,closer,identity_ref):
        self.id,self.kind,self.initial_handle,self.closer,self.identity_ref=identity,kind,handle,closer,identity_ref
        self.close_state='available' if _usable(handle) else 'none';self.identity_prefix=()

class _Buffer:
    __slots__=('ref','capacity','generation','data')
    def __init__(self,ref,capacity,data,generation):self.ref,self.capacity,self.generation,self.data=ref,capacity,generation,bytes(data)

class Call:
    """Preallocated carrier; facts are changed only through its source owner."""
    __slots__=('owner','ordinal','api','slot','requested','buffer','buffer_generation','prepared','declared_empty','invocation_reserved','raw_scalar','raw_count','raw_error','error_defined','scalar_aux_ack','count_aux_ack','right_transfer_ack','wrapper_state','stopped','copied','hashed','copied_bytes','digest','folded_scalar','folded_count','folded_bytes','reconciled')
    def __init__(self,owner,ordinal,api,slot,requested,buffer,prepared,declared_empty):
        values=dict(owner=owner,ordinal=ordinal,api=api,slot=slot,requested=requested,buffer=buffer,buffer_generation=buffer.generation if buffer else None,prepared=prepared,declared_empty=declared_empty,invocation_reserved=False,raw_scalar=UNOBSERVED,raw_count=UNOBSERVED,raw_error=UNOBSERVED,error_defined=False,scalar_aux_ack=False,count_aux_ack=False,right_transfer_ack=False,wrapper_state='not_returned',stopped=False,copied=False,hashed=False,copied_bytes=None,digest=None,folded_scalar=False,folded_count=False,folded_bytes=0,reconciled=False)
        for k,v in values.items():object.__setattr__(self,k,v)
    def __setattr__(self,k,v):raise TypeError('call fields are source-owned')
    def _set(self,k,v):object.__setattr__(self,k,v)

def _exception_text(error):
    """Bounded immutable text; called only AFTER original identity is latched."""
    return dict(class_name=type(error).__name__[:128],message=str(error)[:256],args_repr=[repr(v)[:256] for v in error.args[:8]],format_failed=False)


def _diagnostic_fallback(error):
    # No str/repr/args access and no recursive diagnostic attempt.
    return dict(class_name=type(error).__name__[:128],message='<diagnostic unavailable>',args_repr=[],format_failed=True)


class HarnessFactory:
    """Fictional typed-precondition factory, never real owner/identity authority."""
    def __init__(self):self._brand=object()
    def ref(self,kind):
        _need(kind in CONTEXT_KINDS+('file_identity','buffer','exception'),'ref_kind')
        if kind=='origin':return self.origin(0,0,295000000000,300000000000)
        return HarnessRef(self._brand,kind)
    def origin(self,start_ns,now_ns,work_end_ns,hard_end_ns):return HarnessOrigin(_MINT,self._brand,start_ns,now_ns,work_end_ns,hard_end_ns)
    def owner(self,context,*,namespace_owned=False,reservation_ready=False,primary=None):return Owner(_MINT,self._brand,context,namespace_owned,reservation_ready,primary)

class Owner:
    def __init__(self,mint,brand,context,namespace_owned,reservation_ready,primary):
        _need(mint is _MINT and type(context) is Context,'typed_context')
        self._brand=brand;self._validate_context(context)
        _need(type(namespace_owned) is bool and type(reservation_ready) is bool and (not reservation_ready or namespace_owned),'namespace_state')
        _need(primary is None or isinstance(primary,BaseException),'primary_type')
        self.context=context;self.origin=context.origin;self._slots={};self._buffers={};self._calls={};self._early=None;self._claims=0
        self._namespace_initial=namespace_owned;self.reservation_ready=reservation_ready
        self._primary=primary;self._primary_code='existing_primary' if primary is not None else None;self._disposition='incomplete_unknown' if primary is not None else 'primitive_complete'
        self._secondary=[];self._secondary_codes=[]
        self._sealed_setup=False;self._exception_entries=[]
        if primary is not None:self._retain_diagnostic(primary)
    @property
    def primary(self):return self._primary
    @property
    def secondary(self):return tuple(self._secondary)
    def _ref(self,ref,kind):return type(ref) in (HarnessRef,HarnessOrigin) and ref._brand is self._brand and ref.kind==kind
    def _validate_context(self,context):
        _need(type(context) is Context,'typed_context')
        for name,kind in zip(Context.__dataclass_fields__,CONTEXT_KINDS):
            value=getattr(context,name)
            _need((name=='early_context' and value is None) or self._ref(value,kind),'foreign_reference')
    def _latch(self,error,code,disposition='incomplete_unknown'):
        if self._primary is None:self._primary=error;self._primary_code=code;self._disposition=disposition
        else:self._secondary.append(error);self._secondary_codes.append(code)
        self._retain_diagnostic(error)
    def _retain_diagnostic(self,error):
        for entry in self._exception_entries:
            if entry[0] is error:return
        entry=[error,object(),None];self._exception_entries.append(entry)
        try:text=_exception_text(error)
        except BaseException as formatting_error:
            entry[2]=_freeze(dict(identity=entry[1],**_diagnostic_fallback(error)))
            # Preserve the actual formatting failure but never format it again.
            self._secondary.append(formatting_error);self._secondary_codes.append('diagnostic_format')
            if not any(e[0] is formatting_error for e in self._exception_entries):
                token=object();self._exception_entries.append([formatting_error,token,_freeze(dict(identity=token,**_diagnostic_fallback(formatting_error)))])
        else:entry[2]=_freeze(dict(identity=entry[1],**text))
    def _diagnostic(self,error):
        if error is None:return None
        for entry in self._exception_entries:
            if entry[0] is error:return entry[2]
        raise AdoptionError('missing_diagnostic')
    def exception_for_token(self,token):
        """Non-owning diagnostic identity lookup; no serialized ref is authority."""
        for error,identity,_ in self._exception_entries:
            if identity is token:return error
        raise AdoptionError('foreign_reference')
    def _reject(self,code,disposition='control_rejected'):
        error=AdoptionError(code);self._latch(error,code,disposition);raise error
    def _require(self,v,code,disposition='control_rejected'):
        if not v:self._reject(code,disposition)
    def _setup(self):self._require(not self._sealed_setup and not self._calls and self._claims==0,'setup_only')
    def declare_slot(self,identity,kind,*,handle=UNOBSERVED,closer=None,identity_ref=None):
        self._setup();self._require(type(identity) is str and 0<len(identity)<=32 and identity not in self._slots and len(self._slots)<4,'slot_domain')
        self._require(kind in ('original_file','output_file','search','namespace'),'slot_domain')
        expected=None if kind=='namespace' else 'FindClose' if kind=='search' else 'CloseHandle'
        self._require(closer==expected and (handle is UNOBSERVED or handle is None or _uint(handle,INVALID)),'slot_domain')
        self._require(identity_ref is None or self._ref(identity_ref,'file_identity') and kind in ('original_file','output_file') and _usable(handle),'harness_identity_domain')
        slot=_Slot(identity,kind,handle,closer,identity_ref);self._slots[identity]=slot;return slot
    def declare_buffer(self,ref,capacity,data,generation=0):
        self._setup();self._require(self._ref(ref,'buffer') and ref not in self._buffers and len(self._buffers)<4,'buffer_domain')
        self._require(_uint(capacity,65536) and type(data) is bytes and len(data)<=capacity and _uint(generation,3),'buffer_domain')
        self._require(sum(x.capacity for x in self._buffers.values())+capacity<=131072,'buffer_aggregate')
        self._buffers[ref]=_Buffer(ref,capacity,data,generation)
    def declare_identity_prefix(self,slot_id,query_names):
        self._setup();self._require(slot_id in self._slots and query_names==('GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW'),'identity_prefix')
        self._slots[slot_id].identity_prefix=query_names
    def install_early(self,context_ref,slot_ids,blob,digest,known_read_bytes,hashed_bytes,captured_bytes,event_sequence):
        self._setup();self._require(self._early is None and context_ref is self.context.early_context and self._ref(context_ref,'source_context'),'foreign_reference')
        self._require(type(slot_ids) is tuple and len(slot_ids)<=4 and len(set(slot_ids))==len(slot_ids) and all(i in self._slots and self._slots[i].identity_ref is not None for i in slot_ids),'early_slots')
        self._require(type(blob) is bytes and len(blob)<=65536 and type(digest) is str and digest==hashlib.sha256(blob).hexdigest(),'early_blob')
        self._require(all(_uint(n,65536) for n in (known_read_bytes,hashed_bytes,captured_bytes)) and captured_bytes==len(blob) and captured_bytes<=hashed_bytes<=known_read_bytes and _uint(event_sequence,2048),'early_counts')
        self._early=(context_ref,slot_ids,blob,digest,known_read_bytes,hashed_bytes,captured_bytes,event_sequence)
    def _call(self,call):
        self._require(type(call) is Call and call.owner is self and self._calls.get(call.ordinal) is call,'foreign_reference');return call
    def record(self,ordinal):self._require(ordinal in self._calls,'unknown_ordinal');return self._calls[ordinal]
    def _check(self,hard=False):self._require(self.origin.now_ns<(self.origin.hard_end_ns if hard else self.origin.work_end_ns),'deadline','incomplete_deadline')
    def _hard_api(self,api):return api in ('CloseHandle','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')
    def reserve(self,ordinal,api,slot_id,requested=None,buffer_ref=None,prepared=b'',declared_empty=False):
        self._sealed_setup=True
        self._require(_uint(ordinal,63) and ordinal not in self._calls,'duplicate_ordinal')
        self._require(api in APIS and slot_id in self._slots and len(self._calls)<8,'call_domain')
        slot=self._slots[slot_id]
        self._require(type(prepared) is bytes and type(declared_empty) is bool and (not declared_empty or api=='FindFirstFileExW'),'call_domain')
        if api in ('CloseHandle','FindClose'):self._require(api==slot.closer,'wrong_closer')
        self._require(slot.kind in API_KINDS[api],'API_slot_domain')
        if api in ('ReadFile','WriteFile'):
            self._require(_uint(requested,65536) and requested>0,'request_domain')
            self._require(slot.identity_ref is not None and slot.kind==('original_file' if api=='ReadFile' else 'output_file'),'identity_incomplete')
        else:self._require(requested is None,'request_domain')
        buf=self._buffers.get(buffer_ref) if buffer_ref is not None else None
        if api=='ReadFile':self._require(buf is not None and buf.capacity>=requested and not prepared,'read_buffer_domain')
        elif api=='WriteFile':self._require(buffer_ref is None and len(prepared)==requested,'write_buffer_domain')
        elif api in FIXED_BUFFERS:self._require(buf is not None and buf.capacity==FIXED_BUFFERS[api] and not prepared,'fixed_buffer_domain')
        else:self._require(buffer_ref is None and not prepared,'unused_buffer_domain')
        if buf is not None:self._require(self._buffer_reusable_for_reservation(buf),'buffer_reuse')
        self._require(self.primary is None or api in ('CloseHandle','FindClose'),'work_stopped')
        call=Call(self,ordinal,api,slot,requested,buf,prepared,declared_empty);self._calls[ordinal]=call;return call
    def invoke(self,call):
        call=self._call(call);self._require(not call.invocation_reserved,'duplicate_invocation')
        self._check(self._hard_api(call.api));self._require(self.primary is None or call.api in ('CloseHandle','FindClose'),'work_stopped')
        if call.api in ('CloseHandle','FindClose'):
            state=self._slot_state(call.slot);self._require(state['close_right']=='available' and _usable(state['handle']),'wrong_closer')
        elif call.api in ('CreateFileW','FindFirstFileExW'):
            self._require(not _usable(call.slot.initial_handle) and not any(c is not call and c.slot is call.slot and c.api in ('CreateFileW','FindFirstFileExW') and c.invocation_reserved for c in self._calls.values()),'slot_reuse')
        elif call.api=='CreateDirectoryW':
            self._require(not self._namespace_initial and not any(c is not call and c.api=='CreateDirectoryW' and c.invocation_reserved for c in self._calls.values()),'namespace_reuse')
        elif call.api!='GetFileAttributesExW':
            state=self._slot_state(call.slot);self._require(state['close_right']=='available' and _usable(state['handle']),'owned_slot_required')
        call._set('invocation_reserved',True)
    def _fact_ready(self,call):
        call=self._call(call);self._require(call.invocation_reserved and not call.stopped,'fact_order');return call
    def _store(self,call,field,value):
        prior=getattr(call,field)
        self._require(prior is UNOBSERVED or type(prior) is type(value) and prior==value,'conflicting_fact')
        if prior is UNOBSERVED:call._set(field,value) # first fact BEFORE all auxiliary/fold work
        self._fold(call)
    def store_scalar(self,call,value):
        call=self._fact_ready(call)
        if call.api in ('CreateFileW','FindFirstFileExW'):valid=value is None or _uint(value,INVALID)
        elif call.api in ('GetFileType','GetFinalPathNameByHandleW'):valid=_uint(value,2**32-1)
        else:valid=_bool(value)
        self._require(valid,'scalar_domain');self._store(call,'raw_scalar',value)
    def store_count(self,call,value):
        call=self._fact_ready(call);self._require(call.api in ('ReadFile','WriteFile') and _uint(value,2**32-1),'count_domain');self._store(call,'raw_count',value)
    def store_error(self,call,value,defined):
        call=self._fact_ready(call);self._require(call.raw_scalar is not UNOBSERVED and _uint(value,2**32-1) and type(defined) is bool,'error_domain')
        failed=call.raw_scalar is None or call.raw_scalar in (0,INVALID) if call.api in ('CreateFileW','FindFirstFileExW') else call.raw_scalar==0
        self._require(not defined or failed,'error_domain')
        self._require(call.raw_error is UNOBSERVED or call.raw_error==value and call.error_defined is defined,'conflicting_fact')
        if call.raw_error is UNOBSERVED:call._set('raw_error',value);call._set('error_defined',defined)
    def aux(self,call,field):
        call=self._fact_ready(call);self._require(field in ('scalar_aux_ack','count_aux_ack','right_transfer_ack'),'aux_domain');call._set(field,True)
    def wrapper_return(self,call):
        call=self._call(call);self._require(call.invocation_reserved and not call.stopped and call.wrapper_state=='not_returned','wrapper_order');call._set('wrapper_state','returned')
    def raise_exception(self,call,error,phase):
        self._require(isinstance(error,BaseException) and phase in PHASES,'exception_domain')
        if call is not None:
            call=self._call(call)
            if call.wrapper_state!='returned':call._set('wrapper_state','raised')
            call._set('stopped',True)
        identity_clock_stop=phase=='identity_query' and isinstance(error,TimeoutError) and call is not None and call.api in ('GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx') and self.origin.now_ns>=self.origin.work_end_ns
        if phase in ('pre_dispatch','post_call_clock') or identity_clock_stop:code='deadline';kind='incomplete_deadline'
        elif call is not None and call.invocation_reserved and call.raw_scalar is UNOBSERVED:code='return_unknown';kind='incomplete_unknown'
        else:code='wrapper_exception';kind='incomplete_unknown'
        self._latch(error,code,kind)
    def _defined(self,call):return call.api in ('ReadFile','WriteFile') and _bool(call.raw_scalar) and call.raw_scalar!=0 and _uint(call.raw_count,2**32-1) and call.raw_count<=call.requested
    def _fold(self,call):
        if call.raw_scalar is not UNOBSERVED:call._set('folded_scalar',True)
        if call.raw_count is not UNOBSERVED:call._set('folded_count',True)
        if self._defined(call):call._set('folded_bytes',call.raw_count)
    def _raw_failure(self,call):
        value=call.raw_scalar
        if value is UNOBSERVED:return ('return_unknown','incomplete_unknown') if call.invocation_reserved else None
        if call.api in ('CreateFileW','FindFirstFileExW'):
            if _usable(value):return None
            if value is None or value==0:return ('open_unknown','incomplete_unknown')
            if call.api=='FindFirstFileExW':
                if call.raw_error==2 and call.error_defined and call.declared_empty:return None
                if call.raw_error==18 and call.error_defined:return ('initial_search18','incomplete_known_failure')
            return ('raw_failure','incomplete_known_failure')
        if call.api in ('ReadFile','WriteFile'):
            if self._defined(call):return None
            if call.raw_count is UNOBSERVED and call.wrapper_state=='not_returned':return None
            return ('count_unknown','incomplete_unknown')
        if call.api=='FindNextFileW' and value==0 and call.raw_error==18 and call.error_defined:return None
        if value==0:return ('raw_failure','incomplete_known_failure')
        return None
    def reconcile(self,call,owner_ref):
        call=self._call(call);self._require(owner_ref is self.context.owner,'foreign_reference')
        self._fold(call);call._set('reconciled',True)
        if self.primary is None:
            failure=self._raw_failure(call)
            if failure:self._latch(AdoptionError(failure[0]),*failure)
        return Snapshot(_freeze(dict(ordinal=call.ordinal,owner=self.context.owner,nonce=self.context.nonce,nonowning=True)))
    def _buffer_pending(self,call):return not call.invocation_reserved or call.stopped or not (call.wrapper_state=='returned' and self._defined(call) and call.copied and call.hashed)
    def _buffer_reusable_for_reservation(self,buf):return not any(c.buffer is buf and c.buffer_generation==buf.generation and self._buffer_pending(c) for c in self._calls.values())
    def _slice(self,call):
        self._require(self._defined(call),'count_unknown','incomplete_unknown')
        if call.api=='WriteFile':return call.prepared[:call.raw_count]
        self._require(call.buffer is not None and call.buffer.generation==call.buffer_generation and len(call.buffer.data)>=call.raw_count,'buffer_slice')
        return call.buffer.data[:call.raw_count]
    def _component(self,call,kind,before):
        call=self._call(call);self._check();self._require(self.primary is None and not call.stopped,'work_stopped')
        self._require(kind in ('copy','hash') and (before is None or callable(before)),'component_domain')
        if getattr(call,'copied' if kind=='copy' else 'hashed'):return
        try:
            if before is not None:before()
            data=self._slice(call)
            if kind=='copy':call._set('copied_bytes',bytes(bytearray(data)));call._set('copied',True)
            else:call._set('digest',hashlib.sha256(data).hexdigest());call._set('hashed',True)
            self._check()
        except BaseException as error:
            call._set('stopped',True)
            if error is not self.primary and not any(previous is error for previous in self._secondary):self._latch(error,'wrapper_exception')
            raise
    def copy(self,call,*,before=None):return self._component(call,'copy',before)
    def hash(self,call,*,before=None):return self._component(call,'hash',before)
    def buffer_write(self,ref,generation,data):
        self._require(ref in self._buffers,'buffer_domain');buf=self._buffers[ref]
        self._require(_uint(generation,3) and generation==buf.generation and type(data) is bytes and len(data)<=buf.capacity,'buffer_domain')
        active=[c for c in self._calls.values() if c.buffer is buf and c.buffer_generation==generation and c.invocation_reserved]
        self._require(len(active)==1 and active[0].raw_scalar is UNOBSERVED and not active[0].stopped,'buffer_reuse')
        buf.data=data
    def reuse_buffer(self,ref,new_generation,data):
        self._require(ref in self._buffers,'buffer_reuse');buf=self._buffers[ref]
        self._require(_uint(new_generation,3) and new_generation==buf.generation+1 and type(data) is bytes and len(data)<=buf.capacity and self._buffer_reusable_for_reservation(buf),'buffer_reuse')
        self._check();self._require(self.primary is None,'buffer_reuse');buf.generation=new_generation;buf.data=data
    def advance(self,now_ns):
        self._sealed_setup=True
        self._require(_uint(now_ns,2**63-1) and now_ns>=self.origin.now_ns,'clock_domain')
        object.__setattr__(self.origin,'now_ns',now_ns) # sample only; a later stop keeps its injected exception
    def handoff(self,context):
        self._sealed_setup=True
        try:self._validate_context(context)
        except AdoptionError:self._reject('foreign_reference')
        self._require(all(getattr(context,k) is getattr(self.context,k) for k in Context.__dataclass_fields__) and self._early is not None,'foreign_reference')
        self._require(self._claims==0,'handoff_repeated');self._check();self._require(self.primary is None,'work_stopped')
        self._require(all(self._slot_state(self._slots[identity])['liveness']=='owned_live' and self._slot_state(self._slots[identity])['close_right']=='available' for identity in self._early[1]),'early_context_not_live')
        self._require(self._early[7]<2048,'handoff_event_cap');self._claims=1
        return Snapshot(_freeze(dict(context=self.context,nonowning=True,same_owner=True)))
    def _slot_state(self,slot):
        handle=slot.initial_handle;close=[];unknown=False
        for call in self._calls.values():
            if call.slot is not slot or not call.invocation_reserved:continue
            if call.api in ('CreateFileW','FindFirstFileExW'):
                if call.raw_scalar is UNOBSERVED:unknown=True
                else:handle=call.raw_scalar;unknown=handle is None or handle==0
            if call.api in ('CloseHandle','FindClose'):close.append(call)
        self._require(len(close)<=1,'multiple_close_invariant')
        success=None if not close or close[0].raw_scalar is UNOBSERVED else close[0].raw_scalar!=0
        if close:liveness='close_return_unknown' if success is None else 'closed_known' if success else 'close_failed_known'
        elif _usable(handle):liveness='owned_live'
        else:liveness='ownership_unknown' if unknown else 'no_handle'
        right='consumed' if close else 'available' if _usable(handle) else 'none'
        return dict(handle=handle,liveness=liveness,close_right=right,close_success=success,close_invocations=len(close))
    def _atom(self,value,tag):return dict(tag='UNOBSERVED' if value is UNOBSERVED else 'NULL' if value is None else tag,value=None if value is UNOBSERVED else value)
    def _count_state(self,call):
        if call.api not in ('ReadFile','WriteFile'):return 'not_applicable'
        if not call.invocation_reserved:return 'not_invoked'
        if self._defined(call):return 'known_defined'
        if call.raw_count is not UNOBSERVED:return 'known_undefined'
        return 'pending' if call.wrapper_state=='not_returned' and not call.stopped else 'return_unknown'
    def snapshot(self):
        calls=tuple(self._calls.values());base=self._early
        reads=(base[4] if base else 0)+sum(c.raw_count for c in calls if c.api=='ReadFile' and self._defined(c))
        writes=sum(c.raw_count for c in calls if c.api=='WriteFile' and self._defined(c))
        records=[]
        for c in calls:
            tag='HANDLE' if c.api in ('CreateFileW','FindFirstFileExW') else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32'
            records.append(dict(ordinal=c.ordinal,api=c.api,invocation_reserved=c.invocation_reserved,raw_scalar=self._atom(c.raw_scalar,tag),raw_count=self._atom(c.raw_count,'COUNT32'),raw_error=self._atom(c.raw_error,'DWORD'),error_defined=c.error_defined,scalar_aux_ack=c.scalar_aux_ack,count_aux_ack=c.count_aux_ack,right_transfer_ack=c.right_transfer_ack,count_defined=self._defined(c),count_state=self._count_state(c),wrapper_state=c.wrapper_state))
        slots=[]
        for s in self._slots.values():
            state=self._slot_state(s);slots.append(dict(id=s.id,handle_fact=self._atom(state['handle'],'HANDLE'),liveness=state['liveness'],close_right=state['close_right'],closer=s.closer,close_invocations=state['close_invocations'],close_success=state['close_success']))
        raw_unknown=lambda api:any(c.api==api and c.invocation_reserved and self._count_state(c) in ('known_undefined','return_unknown') for c in calls)
        return Snapshot(_freeze(dict(disposition=self._disposition,primary_exception=self._diagnostic(self.primary),primary_code=self._primary_code,secondary_exceptions=[self._diagnostic(e) for e in self._secondary],secondary_codes=list(self._secondary_codes),
            counters=dict(logical_call_reservations=len(calls),FFI_invocations_reserved=sum(c.invocation_reserved for c in calls),known_scalar_returns=sum(c.raw_scalar is not UNOBSERVED for c in calls),known_count_values=sum(c.raw_count is not UNOBSERVED for c in calls),portable_wrapper_returns=sum(c.wrapper_state=='returned' for c in calls),unique_reconciled_ordinals=sum(c.reconciled for c in calls)),
            records=records,slots=slots,buffers=[dict(id=b.ref,generation=b.generation,hex=b.data.hex(),retained=True,reusable=self._buffer_reusable_for_reservation(b)) for b in self._buffers.values()],
            namespace_owned=self._namespace_initial or any(c.api=='CreateDirectoryW' and _bool(c.raw_scalar) and c.raw_scalar!=0 for c in calls),reservation_ready=self.reservation_ready,
            known_read_bytes=reads,read_count_unknown=raw_unknown('ReadFile'),known_write_bytes=writes,write_count_unknown=raw_unknown('WriteFile'),hashed_bytes=(base[5] if base else 0)+sum(c.raw_count for c in calls if c.hashed),captured_bytes=(base[6] if base else 0)+sum(c.raw_count for c in calls if c.copied),
            handoff=dict(claims=self._claims,same_objects=self._claims>0,origin_start_ns=self.origin.start_ns,origin_now_ns=self.origin.now_ns,next_event_sequence=(base[7] if base else 0)+self._claims,new_origins=0,new_output_reservations=0,early_source_reopens=0),
            qualification=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,profile_qualified=False,runtime_authorized=False))))
