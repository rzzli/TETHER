"""Canonical SOURCE/PURE entry kernel, with an explicitly synthetic raw bank.

TCB algorithms are copied by name from accepted Source4 and adapted here;
this module never imports or constructs its Owner, Origin or Registry.
Pre-entry trusted runtime/hash/compiler services are explicit. No C/FFI,
filesystem discovery, physical I/O, model or native consumption is enabled.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re
import struct
from types import MappingProxyType, MethodType, ModuleType

UNOBSERVED=object()
_MINT=object()
INVALID=(1<<64)-1
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
ALL_APIS=APIS+('GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')
ACTORS=('BOOTSTRAP','ORIGINAL','OUTPUT','READBACK','ANCESTOR_METADATA','SEARCH','NAMESPACE','TERMINAL_TAIL')
CHECKS=('archive','journal','resources','core')
GATES=('admission','hashes',*CHECKS,'consistency','leases_closed','sealed','final_clock')
KINDS=('candidate','cleanup','failure','receipt','seal')
EVENTS=('output_reserved','source_open_reserved','source_open_returned','source_identity_reserved','source_identity_returned','source_hash_reserved','source_hash_returned','handoff_reserved','handoff_claimed','source_compile_reserved','source_compile_returned','file_open_reserved','file_open_returned','file_hash_reserved','file_hash_returned','stage_reserved','stage_returned','finalization_reserved','publication_reserved','publication_returned','original_close_reserved','original_close_returned_or_unknown','journal_close_reserved')
STAGES=('authority_factory','checker_factory','admit_reconcile','hash_remaining',*CHECKS,'consistency')
QUALIFICATION=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,real_checkers_bound=False,verification_complete=False,profile_qualified=False,runtime_authorized=False)
class KernelRefusal(RuntimeError):
    def __init__(self,code):
        if type(code)is not str:raise TypeError('exact code required')
        super().__init__(code);self.code=code

def _numeric(value):
    return (type(value)is int and -(1<<63)<=value<(1<<63)) or (type(value)is float and math.isfinite(value))

class EntryAttempt:
    """Pre-entry retainer, not an owner or a start-time authority."""
    __slots__=('start_cell','attempted','error','state')
    def __init__(self):
        self.start_cell=UNOBSERVED;self.attempted=False;self.error=None;self.state=None
    def capture_start(self,provider):
        if self.attempted:raise KernelRefusal('ENTRY_REPEATED')
        self.attempted=True
        try:self.start_cell=provider()
        except BaseException as error:self.error=error;raise

class Origin:
    __slots__=('_clock','_start','_now','_nonce','_state','_clock_carrier','_work_end','_hard_end')
    def __init__(self,mint,provider,attempt):
        need(mint is _MINT and type(attempt)is EntryAttempt and attempt.attempted,'FOREIGN_STATE')
        started=attempt.start_cell
        need(_numeric(started),'CLOCK_INVALID')
        work=started+295;hard=started+300
        need(_numeric(work) and _numeric(hard) and type(work)is type(started) and type(hard)is type(started) and started<work<hard,'CLOCK_INVALID')
        for k,v in dict(_clock=provider,_start=started,_now=started,_nonce=object(),_state='ok',_clock_carrier=_ClockCarrier(),_work_end=work,_hard_end=hard).items():object.__setattr__(self,k,v)
        self._clock_carrier.value=started
    def __setattr__(self,key,value):raise TypeError('immutable canonical Origin')
    provider_ref=property(lambda self:self._clock)
    unit=property(lambda self:'seconds')
    domain=property(lambda self:'PREBOUND_MONOTONIC')
    start=property(lambda self:self._start)
    raw_latest=property(lambda self:self._clock_carrier.value)
    now=property(lambda self:self._now)
    work_end=property(lambda self:self._work_end)
    hard_end=property(lambda self:self._hard_end)
    def accept(self,value,cleanup=False):
        if self._state=='invalid':raise KernelRefusal('CLOCK_INVALID')
        if not _numeric(value) or value<self._now:
            object.__setattr__(self,'_state','invalid');raise KernelRefusal('CLOCK_INVALID')
        object.__setattr__(self,'_now',value)
        if value>=self.hard_end:
            object.__setattr__(self,'_state','hard_expired');raise KernelRefusal('HARD_DEADLINE')
        if not cleanup and value>=self.work_end:
            object.__setattr__(self,'_state','work_expired');raise KernelRefusal('WORK_DEADLINE')
        return value
    def check(self,cleanup=False):
        if self._state=='invalid':raise KernelRefusal('CLOCK_INVALID')
        carrier=self._clock_carrier;carrier.value=UNOBSERVED
        try:carrier.value=self._clock()
        except BaseException:
            object.__setattr__(self,'_state','invalid');raise
        return self.accept(carrier.value,cleanup)

class _ClockCarrier:
    __slots__=('value',)
    def __init__(self):self.value=UNOBSERVED

@dataclass(frozen=True,slots=True)
class EntryPlan:
    files:tuple
    early_paths:tuple
    module_rules:tuple
    output_key:str
    owner_ops_name:str='preflight_owner_ops_v2'
    file_view_name:str='preflight_file_view_v2'
    codec_name:str='role_ledger_codec_v4'
    profile:object=None

@dataclass(frozen=True,slots=True)
class PreboundServices:
    clock:object
    entry_attempt:object
    raw_backend:object
    output_backend:object
    hash_factory:object
    compile_exec:object
    executing_module:object
    external_root_envelope:object
    trusted_modules:object

@dataclass(frozen=True,slots=True)
class SyntheticRawBackend:
    callback:object
    def invoke_reserved(self,ticket,args):
        need(type(ticket)is InvocationTicket and ticket.owner._injected_current is ticket._call,'FOREIGN_RAW_REF')
        ticket._call.invoked=True
        ticket.owner.raw_store.mark_entered(ticket.call_ref)
        return self.callback(ticket,args)

class SyntheticOutputBackend:
    """Explicit fictional callbacks, never physical namespace authority."""
    __slots__=('reserve_callback','append_callback','close_callback','publish_callback')
    def __init__(self,reserve,append,close,publish):
        for name,value in (('reserve_callback',reserve),('append_callback',append),('close_callback',close),('publish_callback',publish)):
            need(callable(value));object.__setattr__(self,name,value)
    def __setattr__(self,key,value):raise TypeError('immutable backend')

class BootstrapOutputCarrier:
    __slots__=('_owner','_accepting','_namespace_scalar')
    def __init__(self,mint,owner):
        need(mint is _MINT);object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_accepting',True);object.__setattr__(self,'_namespace_scalar',UNOBSERVED)
    def __setattr__(self,key,value):raise TypeError('immutable carrier binding')
    namespace_scalar=property(lambda self:self._namespace_scalar)
    def store_namespace_return(self,value):
        if not self._accepting:raise KernelRefusal('FOREIGN_STATE')
        if self.namespace_scalar is UNOBSERVED:object.__setattr__(self,'_namespace_scalar',value)
        else:raise KernelRefusal('OUTPUT_ALREADY_RESERVED')
        need(signed_bool(value),'UNENCODABLE_RAW')
    def _stop(self):object.__setattr__(self,'_accepting',False)

@dataclass(frozen=True,slots=True)
class BootstrapOutputRef:
    owner:object
    carrier:object

class SinkFacade:
    __slots__=('_owner','_backend')
    def __init__(self,owner,backend):object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_backend',backend)
    def __setattr__(self,key,value):raise TypeError('stable sink facade')
    owner=property(lambda self:self._owner)
    def append(self,raw,ack,hard_end):return self._backend.append_callback(raw,ack,hard_end)
    def close_journal(self,ack,hard_end):return self._backend.close_callback(ack,hard_end)
    def publish(self,kind,raw,ack,hard_end):return self._backend.publish_callback(kind,raw,ack,hard_end)

class PortFacade:
    __slots__=('_owner','_delegate')
    def __init__(self,owner):object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_delegate',None)
    def __setattr__(self,key,value):raise TypeError('stable port facade')
    owner=property(lambda self:self._owner)
    def acquire(self,spec):return self._owner._bootstrap_acquire(spec) if self._delegate is None else self._delegate.acquire(spec)
    def inspect(self,ref):return self._owner._bootstrap_inspect(ref) if self._delegate is None else self._delegate.inspect(ref)
    def hash_capture(self,ref):return self._owner._bootstrap_hash_capture(ref) if self._delegate is None else self._delegate.hash_capture(ref)
    def close(self,ref):return self._owner._bootstrap_close(ref) if self._delegate is None else self._delegate.close(ref)

@dataclass(frozen=True,slots=True)
class InvocationTicket:
    _mint:object
    owner:object
    _call:object
    carrier:object
    def __post_init__(self):need(self._mint is _MINT)
    call_ref=property(lambda self:self._call.ref)

_AXES=('scalar','count','error_value','error_definition')
_AXIS_OFFSET=dict(zip(_AXES,(128,160,192,224)))
_KIND_IDS={'HANDLE64':1,'BOOL32_BITS':2,'DWORD32':3,'COUNT32':4,'DEFINEDNESS':5}

def _scalar_kind(api):
    return 'HANDLE64' if api in ('CreateFileW','FindFirstFileExW') else 'DWORD32' if api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32_BITS'

def _axis_bits(kind,value):
    if kind=='DEFINEDNESS':need(type(value)is bool,'UNENCODABLE_RAW');return int(value)
    if kind=='HANDLE64':
        need(value is None or uint(value,INVALID),'UNENCODABLE_RAW');return 0 if value is None else value
    if kind=='BOOL32_BITS':need(signed_bool(value),'UNENCODABLE_RAW');return value&0xffffffff
    need(uint(value,0xffffffff),'UNENCODABLE_RAW');return value

def _known_axis(kind,bits):
    if kind=='DEFINEDNESS':return bool(bits)
    if kind=='BOOL32_BITS':return bits-(1<<32) if bits&(1<<31) else bits
    return bits

class RawCallStore:
    """One preallocated synthetic byte bank; no native/ABI atomicity claim.

    Python first values remain in CallState before any throwable packing.
    Synthetic stage/commit words are independent observable source-model facts.
    Native release/acquire and before-conversion capture remain unimplemented.
    """
    __slots__=('_owner','_bank','_capacity','_refs','_partial')
    def __init__(self,owner):self._owner=owner;self._bank=None;self._capacity=0;self._refs=[];self._partial=False
    owner=property(lambda self:self._owner)
    capacity=property(lambda self:self._capacity)
    def allocate(self,capacity):
        need(self._bank is None and uint(capacity,16384) and capacity>0,'JOINT_CAP_EXCEEDED')
        self._bank=bytearray(256*capacity);self._refs=[None]*capacity;self._capacity=capacity
    def register(self,call,actor):
        need(call.owner is self.owner and uint(call.ordinal,self.capacity-1) and self._refs[call.ordinal]is None,'FOREIGN_STATE')
        base=256*call.ordinal
        # All row/axis metadata is initialized before the original may enter.
        struct.pack_into('<HHIIHBBIII',self._bank,base,1,256,call.ordinal,1,ALL_APIS.index(call.api)+1,ACTORS.index(actor),1 if call.file is not None else 0,call.file.id if call.file is not None else 0xffffffff,call.requested or 0,0)
        struct.pack_into('<Q',self._bank,base+32,0)
        struct.pack_into('<III',self._bank,base+48,0xffffffff if call.buffer is None else int(call.api=='ReadFile'),call.generation or 0,call.buffer.capacity if call.buffer is not None else 0)
        struct.pack_into('<II',self._bank,base+64,0xa5a5a5a5,0xa5a5a5a5)
        for axis in _AXES:
            kind=_scalar_kind(call.api) if axis=='scalar' else 'COUNT32' if axis=='count' else 'DWORD32' if axis=='error_value' else 'DEFINEDNESS'
            width=8 if kind=='HANDLE64' else 1 if kind=='DEFINEDNESS' else 4
            struct.pack_into('<IHB',self._bank,base+_AXIS_OFFSET[axis]+8,1,_KIND_IDS[kind],width)
        self._refs[call.ordinal]=call.ref
    def _call(self,ref):
        need(type(ref)is RawCallRef and ref._state.owner is self.owner,'FOREIGN_RAW_REF')
        c=ref._state;need(uint(c.ordinal,len(self._refs)-1) and self._refs[c.ordinal]is ref,'FOREIGN_RAW_REF')
        schema,size,ordinal,generation,api_id=struct.unpack_from('<HHIIH',self._bank,256*c.ordinal)
        need(schema==1 and size==256 and ordinal==c.ordinal and generation==1 and api_id==ALL_APIS.index(c.api)+1,'NATIVE_STATE_NOT_REPRESENTABLE')
        base=256*c.ordinal
        need(struct.unpack_from('<I',self._bank,base+28)[0]==0 and not any(memoryview(self._bank)[base+80:base+128]),'NATIVE_STATE_NOT_REPRESENTABLE')
        return c
    def stage_axis(self,ref,axis,value):
        c=self._call(ref);need(type(axis)is str and axis in _AXES,'INVALID_INPUT')
        self._writable(c)
        base=256*c.ordinal+_AXIS_OFFSET[axis]
        need(struct.unpack_from('<II',self._bank,base+16)==(0,0),'NATIVE_CELL_CONFLICT')
        kind=_scalar_kind(c.api) if axis=='scalar' else 'COUNT32' if axis=='count' else 'DWORD32' if axis=='error_value' else 'DEFINEDNESS'
        bits=_axis_bits(kind,value)
        # Native-width staging is only modeled here. A partial Python packing
        # failure cannot upgrade an absent commit to a known native fact.
        struct.pack_into('<Q',self._bank,base,bits)
        if axis=='count':struct.pack_into('<I',self._bank,256*c.ordinal+64,bits)
        struct.pack_into('<I',self._bank,base+16,1)
    def write_payload(self,ref,axis,value):
        c=self._call(ref);need(type(axis)is str and axis in _AXES,'INVALID_INPUT')
        self._writable(c)
        base=256*c.ordinal+_AXIS_OFFSET[axis]
        need(struct.unpack_from('<II',self._bank,base+16)==(0,0),'NATIVE_CELL_CONFLICT')
        kind=_scalar_kind(c.api) if axis=='scalar' else 'COUNT32' if axis=='count' else 'DWORD32' if axis=='error_value' else 'DEFINEDNESS'
        struct.pack_into('<Q',self._bank,base,_axis_bits(kind,value))
    def commit_axis(self,ref,axis):
        c=self._call(ref);need(type(axis)is str and axis in _AXES,'INVALID_INPUT')
        base=256*c.ordinal+_AXIS_OFFSET[axis]
        stage,commit=struct.unpack_from('<II',self._bank,base+16)
        need(stage==1 and commit in (0,1),'INVALID_INPUT')
        if not commit:self._writable(c);struct.pack_into('<I',self._bank,base+20,1)
    def _writable(self,c):
        if type(self.owner)is KernelState:
            need(self.owner._injected_current is c and c.invoked,'FOREIGN_RAW_REF')
        else:need(type(self.owner)is SyntheticExercise,'UNQUALIFIED_BACKEND')
    def observe(self,ref,axis,value):
        current=self.axis(ref,axis)
        if current['native_state']=='COMMITTED':
            need(_axis_bits(current['kind'],value)==current['raw_payload_bits'],'NATIVE_CELL_CONFLICT');return
        need(current['native_state']=='UNOBSERVED','NATIVE_CELL_CONFLICT')
        self.stage_axis(ref,axis,value);self.commit_axis(ref,axis)
    def axis(self,ref,name):
        c=self._call(ref);need(type(name)is str and name in _AXES,'INVALID_INPUT')
        return _decode_axis(bytes(memoryview(self._bank)[256*c.ordinal+_AXIS_OFFSET[name]:256*c.ordinal+_AXIS_OFFSET[name]+32]))
    def copy_row(self,ref):
        c=self._call(ref);return bytes(memoryview(self._bank)[256*c.ordinal:256*(c.ordinal+1)])
    def mark_entered(self,ref):
        c=self._call(ref);struct.pack_into('<I',self._bank,256*c.ordinal+72,1)
    def prepare_input(self,ref,handle):
        c=self._call(ref);need(uint(handle,INVALID),'UNENCODABLE_RAW')
        struct.pack_into('<Q',self._bank,256*c.ordinal+40,handle)
    def mark_exit(self,ref):
        c=self._call(ref);struct.pack_into('<I',self._bank,256*c.ordinal+72,2)
    def require_representable(self):
        for ref in self._refs:
            if ref is None:continue
            for name in _AXES:
                axis=self.axis(ref,name)
                if axis['native_state']=='STAGED_UNCOMMITTED' or axis['native_state']=='UNOBSERVED' and axis['raw_payload_bits']!=0:raise KernelRefusal('NATIVE_STATE_NOT_REPRESENTABLE')

def _decode_axis(raw):
    need(type(raw)is bytes and len(raw)==32,'NATIVE_STATE_NOT_REPRESENTABLE')
    bits,epoch,kind_id,width,reserved,stage,commit,padding=struct.unpack('<QI HBBIIQ',raw)
    need(reserved==0 and padding==0 and epoch==1 and kind_id in _KIND_IDS.values() and stage in (0,1) and commit in (0,1) and(not commit or stage),'NATIVE_STATE_NOT_REPRESENTABLE')
    kind=next(k for k,v in _KIND_IDS.items() if v==kind_id)
    need(width==(8 if kind=='HANDLE64' else 1 if kind=='DEFINEDNESS' else 4),'NATIVE_STATE_NOT_REPRESENTABLE')
    need(bits<(1<<(8*width)) and(kind!='DEFINEDNESS' or bits in (0,1)),'NATIVE_STATE_NOT_REPRESENTABLE')
    native='COMMITTED' if commit else 'STAGED_UNCOMMITTED' if stage else 'UNOBSERVED'
    return dict(native_state=native,kind=kind,width=width,epoch=epoch,stage_hint=stage,commit=commit,raw_payload_bits=bits,known_value=_known_axis(kind,bits) if commit else None)

@dataclass(frozen=True,slots=True)
class AxisSnapshot:
    native_state:str
    kind:str
    width:int
    epoch:int
    stage_hint:int
    commit:int
    raw_payload_bits:int
    known_value:object
    def to_dict(self):return {name:getattr(self,name) for name in self.__slots__}

class RawCallSnapshot:
    __slots__=('_raw','_facts','_axes')
    def __init__(self,mint,raw,facts):
        need(mint is _MINT and type(raw)is bytes and len(raw)==256)
        object.__setattr__(self,'_raw',raw);object.__setattr__(self,'_facts',freeze(facts))
        object.__setattr__(self,'_axes',tuple(AxisSnapshot(**_decode_axis(raw[_AXIS_OFFSET[name]:_AXIS_OFFSET[name]+32])) for name in _AXES))
    def __setattr__(self,key,value):raise TypeError('immutable raw snapshot')
    raw_row=property(lambda self:self._raw)
    row_available=property(lambda self:True)
    facts=property(lambda self:thaw(self._facts))
    def axis(self,name):
        need(type(name)is str and name in _AXES)
        return self._axes[_AXES.index(name)]

class KernelSnapshot:
    __slots__=('_owner','_data','_profile','_raw_calls','_partial','_copy_bytes','_capture_error')
    def __init__(self,mint,owner,data,rows,partial=False,capture_error=None):
        need(mint is _MINT)
        for k,v in dict(_owner=owner,_data=freeze(data),_profile=owner.profile,_raw_calls=tuple(rows),_partial=partial,_copy_bytes=256*len(rows),_capture_error=capture_error).items():object.__setattr__(self,k,v)
    def __setattr__(self,key,value):raise TypeError('immutable kernel snapshot')
    owner=property(lambda self:self._owner)
    owner_state=property(lambda self:self._owner)
    state=property(lambda self:self._owner)
    partial_capture=property(lambda self:self._partial)
    eligible=property(lambda self:not self._partial)
    capture_error=property(lambda self:self._capture_error)
    copied_native_bytes=property(lambda self:self._copy_bytes)
    raw_call_count=property(lambda self:len(self._raw_calls))
    def to_dict(self):return thaw(self._data)
    def raw_call(self,ordinal):
        need(uint(ordinal,len(self._raw_calls)-1));return self._raw_calls[ordinal]
    def require_role1_representable(self):
        if self._partial:raise KernelRefusal('NATIVE_STATE_NOT_REPRESENTABLE')
        for row in self._raw_calls:
            for name in _AXES:
                axis=row.axis(name)
                if axis.native_state=='STAGED_UNCOMMITTED' or axis.native_state=='UNOBSERVED' and axis.raw_payload_bits!=0:raise KernelRefusal('NATIVE_STATE_NOT_REPRESENTABLE')
        return None

class RawCallView:
    """Quiescent synthetic-bank observation, never a fresh owner/lease."""
    __slots__=('_owner','_ref','_snapshot')
    def __init__(self,mint,owner,ref,snapshot):
        need(mint is _MINT)
        object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_ref',ref);object.__setattr__(self,'_snapshot',snapshot)
    def __setattr__(self,key,value):raise TypeError('immutable raw view')
    owner=property(lambda self:self._owner)
    call_ref=property(lambda self:self._ref)
    raw_row=property(lambda self:self._snapshot.raw_row)
    facts=property(lambda self:self._snapshot.facts)
    def axis(self,name):return self._snapshot.axis(name)

class _SearchState:
    __slots__=('first','handle','close_reserved')
    def __init__(self,first,handle):self.first=first;self.handle=handle;self.close_reserved=False

class SyntheticSearchRef:
    __slots__=('_owner','_state')
    def __init__(self,mint,owner,state):need(mint is _MINT);object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_state',state)
    def __setattr__(self,key,value):raise TypeError('immutable unqualified search reference')
    owner=property(lambda self:self._owner)
    closed=property(lambda self:self._state.close_reserved)
    scope=property(lambda self:'UNQUALIFIED_RAW_EXERCISE')

class SyntheticExercise:
    """Standalone bounded raw DATA exercise, not a KernelState or backend.

    It uses the real RawCallStore/CallState implementation. Search references
    are source-issued within this unqualified data domain; they cannot be used
    as runtime FileRefs, native leases or output authority. No API is invoked.
    """
    __slots__=('raw_store','_calls','_targets','_searches')
    def __init__(self,capacity=64):
        need(uint(capacity,16384) and capacity>0,'JOINT_CAP_EXCEEDED')
        self.raw_store=RawCallStore(self);self.raw_store.allocate(capacity)
        self._calls=[];self._targets={};self._searches=[]
    scope=property(lambda self:'UNQUALIFIED_RAW_EXERCISE')
    def reserve_fragment(self,api,actor='ORIGINAL',target_ref=None,requested=None):
        need(type(api)is str and api in ALL_APIS and type(actor)is str and actor in ACTORS,'ACTOR_PROFILE_UNQUALIFIED')
        need(requested is None or uint(requested,0xffffffff),'INVALID_INPUT')
        need(api in ('ReadFile','WriteFile') or requested is None,'INVALID_INPUT')
        if target_ref is not None:
            need(type(target_ref)is SyntheticSearchRef and target_ref.owner is self and any(target_ref is x for x in self._searches),'FOREIGN_RAW_REF')
            need(api in ('FindNextFileW','FindClose'),'WRONG_CLOSER')
            need(not target_ref.closed,'LEASE_NOT_LIVE')
        if api in ('FindNextFileW','FindClose'):need(target_ref is not None,'LEASE_NOT_LIVE')
        need(len(self._calls)<self.raw_store.capacity,'JOINT_CAP_EXCEEDED')
        c=CallState(self,len(self._calls),api,None,requested,None)
        self.raw_store.register(c,actor);self._calls.append(c);self._targets[c.ordinal]=target_ref
        if api=='FindClose':target_ref._state.close_reserved=True
        return c.ref
    def _call(self,ref):
        c=self.raw_store._call(ref);need(self._calls[c.ordinal]is c,'FOREIGN_RAW_REF');return c
    def write_payload(self,ref,axis,value):self._call(ref);return self.raw_store.write_payload(ref,axis,value)
    def stage_axis(self,ref,axis,value):self._call(ref);return self.raw_store.stage_axis(ref,axis,value)
    def commit_axis(self,ref,axis):self._call(ref);return self.raw_store.commit_axis(ref,axis)
    def observe(self,ref,axis,value):self._call(ref);return self.raw_store.observe(ref,axis,value)
    def raw_call_view(self,ref):
        c=self._call(ref);snap=RawCallSnapshot(_MINT,self.raw_store.copy_row(ref),dict(ordinal=c.ordinal,api=c.api,scope=self.scope))
        return RawCallView(_MINT,self,ref,snap)
    def snapshot(self):return tuple(self.raw_call_view(c.ref)._snapshot for c in self._calls)
    def establish_search(self,first_ref):
        c=self._call(first_ref);a=self.raw_store.axis(first_ref,'scalar')
        need(c.api=='FindFirstFileExW' and a['native_state']=='COMMITTED' and usable(a['known_value']),'LEASE_NOT_LIVE')
        need(not any(x._state.first is first_ref for x in self._searches),'NATIVE_CELL_CONFLICT')
        ref=SyntheticSearchRef(_MINT,self,_SearchState(first_ref,a['known_value']));self._searches.append(ref);return ref
    def interpret(self,ref):
        c=self._call(ref);axes={name:self.raw_store.axis(ref,name) for name in _AXES}
        scalar=axes['scalar']['known_value'];known=axes['scalar']['native_state']=='COMMITTED'
        count=axes['count']['known_value'];count_known=axes['count']['native_state']=='COMMITTED'
        definition=axes['error_definition']['known_value'];error=axes['error_value']['known_value']
        count_applicable=c.api in ('ReadFile','WriteFile')
        if axes['count']['native_state']!='UNOBSERVED':need(count_applicable,'COUNT_NOT_APPLICABLE')
        if definition is True:
            probe=known and(scalar==INVALID if c.api in ('CreateFileW','FindFirstFileExW') else scalar==0)
            need(probe,'ERROR_DEFINITION_CONTRADICTION')
        defined=count_applicable and known and signed_bool(scalar) and scalar!=0 and count_known and c.requested is not None and count<=c.requested
        if count_applicable and known and scalar!=0 and count_known and not defined:raise KernelRefusal('COUNT_RANGE')
        target=self._targets[c.ordinal]
        search_right=c.api=='FindFirstFileExW' and known and usable(scalar)
        natural_end=c.api=='FindNextFileW' and target is not None and known and scalar==0 and definition is True and axes['error_value']['native_state']=='COMMITTED' and error==18
        return freeze(dict(scope=self.scope,scalar_known=known,scalar=scalar,usable_handle=known and c.api in ('CreateFileW','FindFirstFileExW') and usable(scalar),count_defined=bool(defined),known_count=count if defined else None,progress=count if defined else 0,error_definition=definition,error_value=error,error_value_observed=axes['error_value']['native_state']=='COMMITTED',search_right=bool(search_right),natural_end=bool(natural_end),right_consumed=bool(target is not None and target.closed),frame_defined=known and scalar not in (0,INVALID),native_dispatches=0))


def uint(v,cap):return type(v) is int and 0<=v<=cap

def finite(v):return type(v) is int or type(v) is float and math.isfinite(v)

def usable(v):return uint(v,INVALID) and v not in (0,INVALID)

def signed_bool(v):return type(v) is int and -2**31<=v<2**31

def sha(v):return hashlib.sha256(v).hexdigest()

def need(ok,code='INVALID_INPUT'):
    if not ok:raise KernelRefusal(code)

def path_key(path):
    need(type(path) is str and len(path)>=4 and path[0] in 'CcDd' and path[1]==':' and path[2] in '/\\')
    try:need(len(path.encode('utf-16-le','strict'))//2<=4096)
    except UnicodeError as error:raise KernelRefusal('INVALID_INPUT') from error
    out=path.replace('/','\\')
    for p in out[3:].split('\\'):
        need(p not in ('','.','..') and not p.endswith((' ','.')) and not any(ord(c)<32 or ord(c)==127 or c in '<>:"|?*~' for c in p))
        need(p.split('.',1)[0].lower() not in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]})
    return out.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))

def freeze(v):
    if type(v) is dict or type(v) is MappingProxyType:return MappingProxyType({k:freeze(x) for k,x in v.items()})
    if type(v) is list or type(v) is tuple:return tuple(freeze(x) for x in v)
    if v is None or type(v)is bool or type(v)is int or type(v)is float or type(v)is str or type(v)is bytes or type(v)is object:return v
    raise KernelRefusal('UNENCODABLE_RAW')

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

class CaptureNotRequested(KernelRefusal):
    def __init__(self):super().__init__('CAPTURE_NOT_REQUESTED')

class _DiagnosticGuard:
    __slots__=('owner','cleanup','outer','remaining')
    def __init__(self,owner,cleanup):self.owner=owner;self.cleanup=cleanup;self.outer=False;self.remaining=0
    def __enter__(self):
        o=self.owner
        o._active()
        if not self.cleanup and o.primary is not None:raise o.primary
        if o._diagnostic_guard is None:
            if o._diag_committed+o._diag_borrowed+2>o._diag_capacity:raise KernelRefusal('DIAGNOSTIC_CAPACITY')
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

class FileRef:
    __slots__=('_owner','_state')
    def __init__(self,mint,owner,state):need(mint is _MINT);object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_state',state)
    def __setattr__(self,k,v):raise TypeError('read-only file reference')
    @property
    def id(self):return self._state.id
    @property
    def spec(self):return self._state.spec
    @property
    def owner(self):return self._owner

class BufferRef:
    __slots__=('_owner','_data','_generation','_written')
    def __init__(self,owner,capacity):
        object.__setattr__(self,'_owner',owner);object.__setattr__(self,'_data',bytearray(capacity));object.__setattr__(self,'_generation',0);object.__setattr__(self,'_written',0)
    def __setattr__(self,k,v):raise TypeError('read-only buffer reference')
    @property
    def capacity(self):return len(self._data)

class FileState:
    def __init__(self,owner,i,spec,early):
        self.id=i;self.spec=spec;self.early=early;self.ref=FileRef(_MINT,owner,self)
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
    __slots__=('owner','ordinal','api','file','requested','buffer','generation','invoked','scalar','count','error','error_definition','_python_scalar','_python_count','_python_error_value','_python_error_definition','scalar_aux_ack','count_aux_ack','right_transfer_ack','wrapper_return','wrapper_state','wrapper_result','wrapper_error','stopped','buffer_state','buffer_written','query_bytes','_reservation_fold','_read_fold_phase','_read_contribution','ref','pre_clock','post_clock','pre_clock_attempted','post_clock_attempted','hash_attempted','hash_return','copy_attempted','copy_return','input_handle','prepared','hash_count','copy_count','_hash_fold_phase','_copy_fold_phase')
    def __init__(self,owner,i,api=None,file=None,requested=None,buffer=None):
        self.owner=owner;self.ordinal=i;self.api=api;self.file=file;self.requested=requested;self.buffer=buffer;self.generation=buffer._generation if buffer else None
        self.invoked=False;self.scalar=UNOBSERVED;self.count=UNOBSERVED;self.error=UNOBSERVED;self.error_definition=UNOBSERVED
        self._python_scalar=self._python_count=self._python_error_value=self._python_error_definition=UNOBSERVED
        self.scalar_aux_ack=self.count_aux_ack=self.right_transfer_ack=False
        self.wrapper_return=False;self.wrapper_state='not_returned';self.wrapper_result=UNOBSERVED;self.wrapper_error=None;self.stopped=False;self.buffer_state='reserved' if buffer else 'not_applicable';self.buffer_written=0;self.query_bytes=None
        self._reservation_fold='unapplied';self._read_fold_phase='pending';self._read_contribution=None
        self.ref=RawCallRef(_MINT,self)
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

class RawCallRef:
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
        need(type(path)is str,'INVALID_INPUT')
        if path not in self.blobs:
            if any(s.path==path and not s.capture for s in self.specs):raise CaptureNotRequested()
            raise KernelRefusal('INVALID_INPUT')
        return self.blobs[path]
    def check_work(self):return self.owner.check()
    origin=property(lambda self:self.owner.origin)
    registry=property(lambda self:self.owner.registry)
    raw_store=property(lambda self:self.owner.raw_store)
    def __reduce_ex__(self,p):raise TypeError('not serialized authority')

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

def _utf8_prefix(text,cap):
    raw=text.encode('utf-8','replace')
    if len(raw)<=cap:return raw,False
    return raw[:cap].decode('utf-8','ignore').encode(),True


PROFILE_N4=ProducerProfile('ORIGINAL7_N4',65536,4,2,2,4096,16384,92,224,131072)
PROFILE_ORIGINAL7_1M=ProducerProfile('ORIGINAL7_PROSPECTIVE',1048576,256,128,128,8388608,33554432,16384,2240,127809034)
ROLES=('captured_software','captured_metadata','hash_only_bulk')
ROLE_WIRE=dict(zip(ROLES,('CAPTURED_SOFTWARE','CAPTURED_METADATA','HASH_ONLY_BULK')))
ARTIFACT_CAPS={'candidate-ledger.bin':14800384,'terminal-ledger.bin':14800384,'journal.jsonl':2293760,'producer-report.json':8192,**{k+'.json':8192 for k in KINDS},'child/result.partial.jsonl':7995392,'child/attempt.json':4096,'child/failure.json':65536,'stdout.bin':65536,'stderr.bin':65536}


class _KernelAlgorithms:

    def _active(self):
        if self.finalized:raise KernelRefusal('FINALIZED_MISUSE')

    def record_error(self,error,phase,code=None):
        self._active()
        if error is self._primary or any(e is error for e in self._secondary):return
        if self._primary is None:
            self._primary=error;self._refusal=code or (error.code if isinstance(error,KernelRefusal) else 'INVALID_INPUT');self._status='REFUSED' if isinstance(error,KernelRefusal) else 'INCOMPLETE'
        else:self._secondary.append(error)
        self._commit_diagnostic_slot();token=object();entry=[error,token,None];self._diagnostics.append(entry)
        try:diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message=str(error)[:256],args_repr=[repr(a)[:256] for a in error.args[:8]],format_failed=False)
        except BaseException as formatting:
            diag=dict(identity=token,phase=phase,class_name=type(error).__name__[:128],message='<diagnostic unavailable>',args_repr=[],format_failed=True)
            self._secondary.append(formatting);self._commit_diagnostic_slot();self._diagnostics.append([formatting,object(),None]);e=self._diagnostics[-1];e[2]=freeze(dict(identity=e[1],phase='diagnostic_format',class_name='<formatter-failure>',message='<diagnostic unavailable>',args_repr=[],format_failed=True))
        entry[2]=freeze(diag)

    def _commit_diagnostic_slot(self):
        if self._diag_committed>=self._diag_capacity:raise KernelRefusal('DIAGNOSTIC_CAPACITY')
        g=self._diagnostic_guard
        if g is not None and g.remaining:
            g.remaining-=1;self._diag_borrowed-=1
        self._diag_committed+=1

    def operation_guard(self,cleanup=False):return _DiagnosticGuard(self,cleanup)

    def exception_for_token(self,token):
        for e,t,_ in self._diagnostics:
            if t is token:return e
        raise KernelRefusal('FOREIGN_IDENTITY')

    def _diag(self,error):
        if error is None:return None
        return next(d for e,_,d in self._diagnostics if e is error)

    def require(self,ok,code='INVALID_INPUT',phase=None):
        self._active()
        if not ok:
            e=KernelRefusal(code);self.record_error(e,phase or self._diagnostic_phase());raise e

    def check(self,cleanup=False):
        self._active()
        if not cleanup:
            self._require_accounting_work()
            if self.primary is not None:raise self.primary
        try:return self.origin.check(cleanup)
        except BaseException as error:self.record_error(error,'final_clock' if cleanup else self._diagnostic_phase());raise

    def charge_raw(self,n):
        self.require(uint(n,self.profile.raw_cap) and self._raw_used+n+self._assembly_live<=self.profile.raw_cap,'JOINT_CAP_EXCEEDED');self.check();self._raw_used+=n;self._raw_peak=max(self._raw_peak,self._raw_used)

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
        for r in module_rules:self.require(type(r.fullname) is str and len(r.fullname)<=512 and re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',r.fullname,re.ASCII)is not None and r.path in early_paths and type(r.dependencies) is tuple and len(set(r.dependencies))==len(r.dependencies) and all(type(n)is str and (n in rules or n in self._trusted_modules) for n in r.dependencies) and type(r.package) is bool)
        visited=set()
        def visit(n,trail):
            self.require(n not in trail,'SOURCE_IMPORT_REFUSED')
            if n in visited:return
            for d in rules[n].dependencies:
                if d in rules:visit(d,trail+(n,))
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
        raise KernelRefusal('INVALID_INPUT')

    def file_state(self,ref):
        self.require(type(ref) is FileRef and ref._owner is self,'FOREIGN_IDENTITY')
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
        contribution=self.committed_fact(call,'count') if self.defined(call) else None
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
            scalar=self.committed_fact(c,'scalar');count=self.committed_fact(c,'count');error=self.committed_fact(c,'error_value');error_definition=self.committed_fact(c,'error_definition')
            g=groups[c.file.id];counter=counters[c.api];counter['reserved']+=1;counter['invocations']+=int(c.invoked);counter['scalar_returns']+=int(scalar is not UNOBSERVED);counter['count_values']+=int(count is not UNOBSERVED);counter['wrapper_returns']+=int(c.wrapper_return)
            defined=self.defined(c)
            if c.api=='CreateFileW':
                if g['open'] is None:g['open']=c
                g['open_invocations']+=int(c.invoked)
            elif c.api=='CloseHandle':
                if g['close'] is None:g['close']=c
                g['close_invocations']+=int(c.invoked)
            elif c.api=='ReadFile':
                g['read_generation']=c.generation if c.generation is not None else 0
                g['read_reservations']+=1;g['read_invocations']+=int(c.invoked);g['read_scalar_returns']+=int(scalar is not UNOBSERVED)
                if defined:g['known']+=count
                if c.invoked and not defined:g['unknown']=True
                if c.hash_return is not UNOBSERVED and defined:g['hashed']+=count
                if c.copy_return is not UNOBSERVED and defined:g['copied']+=count
                g['hash_unknown']|=c.hash_attempted and c.hash_return is UNOBSERVED
                g['copy_unknown']|=c.copy_attempted and c.copy_return is UNOBSERVED
                if compare_cache:self.require((c._read_fold_phase=='committed' and c._read_contribution==count) if defined else (c._read_fold_phase=='pending' and c._read_contribution is None),'INVALID_INPUT','consistency')
            tag='HANDLE' if c.api=='CreateFileW' else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32'
            scalar_atom=dict(tag='NULL',value=None) if tag=='HANDLE' and type(scalar)is int and scalar==0 else atom(scalar,tag)
            if include_calls:calls.append(dict(ordinal=c.ordinal,api=c.api,file_id=c.file.id,reserved=True,invocation_reserved=c.invoked,raw_scalar=scalar_atom,raw_count=atom(count,'COUNT32'),raw_error=atom(error,'DWORD'),error_defined=error_definition is True,scalar_aux_ack=c.scalar_aux_ack,count_aux_ack=c.count_aux_ack,right_transfer_ack=c.right_transfer_ack,wrapper_return_observed=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,count_defined=defined,buffer_state=c.buffer_state,buffer_generation=c.generation,raw_buffer_bytes=len(c.query_bytes) if c.query_bytes is not None else None,raw_buffer_sha256=sha(c.query_bytes) if c.query_bytes is not None else None))
        files=[];totals=dict(known_read_bytes=0,hashed_bytes=0,captured_bytes=0,read_count_unknown=False,early_reopens_after_claim=0,early_rehashes_after_claim=0,early_known_read_bytes=0,early_hashed_bytes=0,early_captured_bytes=0,remaining_known_read_bytes=0,remaining_hashed_bytes=0,remaining_captured_bytes=0)
        for f,g in zip(fs,groups):
            if compare_cache:self.require(f._open_call is g['open'] and f._close_call is g['close'] and f._read_reservations==g['read_reservations'] and f._known_read_bytes==g['known'],'INVALID_INPUT','consistency')
            oc,cc=g['open'],g['close'];handle=self.committed_fact(oc,'scalar') if oc is not None and oc.invoked else UNOBSERVED
            open_state='unopened' if oc is None else 'reserved' if not oc.invoked else 'entered_return_unknown' if handle is UNOBSERVED else 'owned' if usable(handle) else 'known_failure_no_handle' if uint(handle,INVALID)and handle==INVALID else 'ownership_unknown'
            close_scalar=self.committed_fact(cc,'scalar') if cc is not None else UNOBSERVED
            observed=cc is not None and cc.invoked and signed_bool(close_scalar);success=close_scalar!=0 if observed else None
            close_state='returned_success' if observed and success else 'returned_failure' if observed else 'entered_return_unknown' if cc is not None and cc.invoked else 'not_dispatched_deadline' if f.close_state=='not_dispatched_deadline' else 'reserved' if f.close_reserved else 'not_attempted'
            capture_state='NOT_REQUESTED'if not f.spec.capture else'COMPLETE'if f.capture_complete else'FAILED'if f.hash_attempted and self.primary is not None else'PENDING'
            files.append(dict(id=f.id,spec=dict(path=f.spec.path,role=f.spec.role,size=f.spec.size,sha256=f.spec.sha256,capture=f.spec.capture),early=f.early,open_state=open_state,handle_fact=dict(tag='NULL',value=None) if handle is not UNOBSERVED and type(handle)is int and handle==0 else atom(handle,'HANDLE'),identity_state=f.identity_state,identity_queries=list(f.identity_queries),open_invocations=g['open_invocations'],read_invocations=g['read_invocations'],read_scalar_returns=g['read_scalar_returns'],known_read_bytes=g['known'],hashed_bytes=g['hashed'],captured_bytes=g['copied'],read_count_unknown=g['unknown'],hash_complete=f.hash_complete,capture_complete=f.capture_complete,actual_sha256=f.actual_sha,close_reserved=f.close_reserved,close_invocations=g['close_invocations'],close_return_observed=observed,close_success=success,close_state=close_state,capture_state=capture_state,hash_unknown=g['hash_unknown'],copy_unknown=g['copy_unknown'],read_generation=g['read_generation']))
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

    def _live_early(self):
        self.require(self.early_context is not None and self.early_context.owner is self and self.early_context.nonce is self.nonce,'EARLY_SOURCE_NOT_LIVE_COMPLETE')
        self.require(all(f.hash_complete and f.capture_complete and not f.close_reserved and usable(self.handle(f)) for f in self.registry._files if f.early),'EARLY_SOURCE_NOT_LIVE_COMPLETE')

    def handle(self,file):
        c=file._open_call
        if c is None:return UNOBSERVED
        self.require(c.owner is self and c.file is file and uint(c.ordinal,len(self.registry._calls)-1) and self.registry._calls[c.ordinal] is c,'FOREIGN_IDENTITY')
        return self.committed_fact(c,'scalar') if c.invoked else UNOBSERVED

    def read_known(self,file):
        self._require_accounting_work();self.require(uint(file.id,len(self.registry._files)-1) and self.registry._files[file.id] is file,'FOREIGN_IDENTITY');return file._known_read_bytes

    def defined(self,c):
        scalar=self.committed_fact(c,'scalar');count=self.committed_fact(c,'count')
        return c.api=='ReadFile' and c.invoked and signed_bool(scalar) and scalar!=0 and uint(count,2**32-1) and c.requested is not None and count<=c.requested

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

FRAMES = {'GetFileInformationByHandleEx': 8,
          'GetFinalPathNameByHandleW': 8202, 'GetFileSizeEx': 8}

class AdoptionHooks:
    """A single prebound invocation; never an owner reconstructed from data."""
    __slots__ = ('owner', '_bound', '_accepting')

    def __init__(self, owner, call=None):
        if type(owner) is not KernelState:
            raise KernelRefusal('FOREIGN_IDENTITY')
        owner._active()
        if call is not None:
            # Validate the carrier BEFORE the original is invoked. A caller
            # cannot construct a bound shim around another owner's live slot.
            if (type(call) is not CallState or call.owner is not owner
                or not uint(call.ordinal, len(owner.registry._calls) - 1)
                or owner.registry._calls[call.ordinal] is not call
                or call.invoked or call.stopped):
                raise KernelRefusal('FOREIGN_IDENTITY')
        object.__setattr__(self, 'owner', owner)
        object.__setattr__(self, '_bound', call)
        object.__setattr__(self, '_accepting', call is not None)

    def __setattr__(self, name, value):
        raise TypeError('read-only invocation carrier')

    def _stop(self):
        object.__setattr__(self, '_accepting', False)

    def _carrier(self, ref):
        # Identity/lifetime tests invoke no supplied equality, type conversion,
        # callback or clock. The actual slot is fixed before binding dispatch.
        c = self._bound
        if c is None:
            # Legacy inspection/idempotence surface, not a first-return port.
            o = self.owner
            o._active()
            o._require_accounting_work()
            o.require(type(ref) is RawCallRef and ref._state.owner is o, 'FOREIGN_IDENTITY')
            c = ref._state
            o.require(uint(c.ordinal, len(o.registry._calls) - 1)
                and o.registry._calls[c.ordinal] is c, 'FOREIGN_IDENTITY')
            o.require(c.invoked and not c.stopped and o.primary is None, 'INVALID_INPUT')
            return c
        if not self._accepting or ref is not c.ref:
            raise KernelRefusal('FOREIGN_IDENTITY')
        return c

    def _state(self, ref):
        c = self._carrier(ref)
        o = self.owner
        o._active()
        o.require(c.owner is o and c.invoked, 'FOREIGN_IDENTITY')
        return c

    def _publish_axis(self,c,axis,value):
        try:self.owner.raw_store.observe(c.ref,axis,value)
        except BaseException as error:
            self.owner._accounting_failed(c,error,'native_axis_publish');raise

    def _cache_axis(self,c,axis):
        try:self.owner._cache_committed_fact(c,axis)
        except BaseException as error:
            self.owner._accounting_failed(c,error,'native_cache_fold');raise

    def stage_axis(self,ref,axis,value):
        c=self._carrier(ref)
        if self._bound is None:raise KernelRefusal('FOREIGN_STATE')
        self.owner.raw_store.stage_axis(c.ref,axis,value)

    def commit_axis(self,ref,axis):
        c=self._carrier(ref)
        if self._bound is None:raise KernelRefusal('FOREIGN_STATE')
        self.owner.raw_store.commit_axis(c.ref,axis)

    def store_scalar(self, ref, value):
        c = self._carrier(ref)
        if c._python_scalar is UNOBSERVED:
            if self._bound is None:
                raise KernelRefusal('INVALID_INPUT')
            c._python_scalar = value
        else:
            self.owner.require(c._python_scalar is value or type(c._python_scalar) is type(value)
                and type(value) is int and c._python_scalar == value, 'INVALID_INPUT')
        self._publish_axis(c,'scalar',value)
        self._cache_axis(c,'scalar')
        o = self.owner
        try:
            self._state(ref)
            valid = ((value is None or uint(value, INVALID)) if c.api == 'CreateFileW'
                else uint(value, 2**32 - 1) if c.api in ('GetFileType', 'GetFinalPathNameByHandleW')
                else signed_bool(value))
            if value is None and c.api != 'CreateFileW':
                # Observed NULL is losslessly retainable malformed data. It is
                # different from an arbitrary object/out-of-width raw value.
                raise KernelRefusal('RAW_RETURN_UNKNOWN')
            o.require(valid, 'UNENCODABLE_RAW')
            if c.api == 'ReadFile':
                o._fold_read_fact(c)
            if c.api == 'CreateFileW':
                c.file.open_state = ('owned' if usable(value) else
                    'known_failure_no_handle' if value == INVALID else 'ownership_unknown')
            elif c.api == 'CloseHandle':
                c.file.close_state = 'returned_success' if value != 0 else 'returned_failure'
        except BaseException as error:
            o._accounting_failed(c, error, 'after_scalar_before_aux')
            raise

    def store_count(self, ref, value):
        c = self._carrier(ref)
        if c._python_count is UNOBSERVED:
            if self._bound is None:
                raise KernelRefusal('INVALID_INPUT')
            c._python_count = value
        else:
            self.owner.require(c._python_count is value or type(c._python_count) is int
                and type(value) is int and c._python_count == value, 'INVALID_INPUT')
        self._publish_axis(c,'count',value)
        self._cache_axis(c,'count')
        o = self.owner
        try:
            self._state(ref)
            o.require(c.api == 'ReadFile' and uint(value, 2**32 - 1), 'UNENCODABLE_RAW')
            o._fold_read_fact(c)
        except BaseException as error:
            o._accounting_failed(c, error, 'after_count_before_aux')
            raise

    def store_error_definition(self, ref, defined):
        c = self._carrier(ref)
        if c._python_error_definition is UNOBSERVED:
            if self._bound is None:
                raise KernelRefusal('INVALID_INPUT')
            c._python_error_definition = defined
        else:
            self.owner.require(c._python_error_definition is defined, 'INVALID_INPUT')
        self._publish_axis(c,'error_definition',defined)
        self._cache_axis(c,'error_definition')
        self._state(ref)
        self.owner.require(type(defined) is bool, 'UNENCODABLE_RAW')
        if defined:
            scalar=self.owner.committed_fact(c,'scalar')
            failed = ((type(scalar) is int and scalar == INVALID)
                if c.api == 'CreateFileW' else
                (type(scalar) is int and scalar == 0))
            self.owner.require(failed, 'INVALID_INPUT')

    def store_error_value(self, ref, value):
        c = self._carrier(ref)
        if c._python_error_value is UNOBSERVED:
            if self._bound is None:
                raise KernelRefusal('INVALID_INPUT')
            c._python_error_value = value
        else:
            self.owner.require(c._python_error_value is value or type(c._python_error_value) is int
                and type(value) is int and c._python_error_value == value, 'INVALID_INPUT')
        self._publish_axis(c,'error_value',value)
        self._cache_axis(c,'error_value')
        self._state(ref)
        self.owner.require(uint(value, 2**32 - 1), 'UNENCODABLE_RAW')

    def store_error(self, ref, value, defined):
        # Retain distinct Python delivery before either throwable native
        # publication. Delivery alone never grants a native fact or right.
        c = self._carrier(ref)
        if self._bound is None and (c._python_error_value is UNOBSERVED or c._python_error_definition is UNOBSERVED):
            raise KernelRefusal('INVALID_INPUT')
        if c._python_error_value is UNOBSERVED:c._python_error_value=value
        if c._python_error_definition is UNOBSERVED:c._python_error_definition=defined
        self.store_error_value(ref, value)
        self.store_error_definition(ref, defined)

    def _buffer(self, ref, buffer_ref, generation):
        c = self._state(ref)
        o = self.owner
        o.require(self._bound is not None, 'INVALID_INPUT')
        o.require(c.buffer is not None and buffer_ref is c.buffer
            and type(generation) is int and generation >= 0
            and generation == c.generation == buffer_ref._generation, 'FOREIGN_IDENTITY')
        o.require(c.scalar is UNOBSERVED, 'INVALID_INPUT')
        limit = FRAMES[c.api] if c.api in FRAMES else c.requested
        o.require(c.api in FRAMES or c.api == 'ReadFile', 'INVALID_INPUT')
        return c, limit

    def buffer_write_slice(self, ref, buffer_ref, generation, offset, data):
        """Trusted binding appends exact bytes; it receives no mutable view."""
        c, limit = self._buffer(ref, buffer_ref, generation)
        o = self.owner
        o.require(type(offset) is int and offset == c.buffer_written
            and type(data) is bytes and offset + len(data) <= limit, 'INVALID_INPUT')
        end = offset + len(data)
        memoryview(buffer_ref._data)[offset:end] = data
        # This is an observed completed copy, not an inferred native count.
        c.buffer_written = end
        object.__setattr__(buffer_ref, '_written', end)
        c.buffer_state = 'raw_retained'

    def buffer_copy_within(self, ref, buffer_ref, generation, source_offset, length):
        """Append a retained buffer region without exposing/caching its body."""
        c, limit = self._buffer(ref, buffer_ref, generation)
        o = self.owner
        o.require(type(source_offset) is int and type(length) is int
            and 0 <= source_offset and 0 < length
            and source_offset + length <= c.buffer_written
            and c.buffer_written + length <= limit, 'INVALID_INPUT')
        start = c.buffer_written
        end = start + length
        view = memoryview(buffer_ref._data)
        view[start:end] = view[source_offset:source_offset + length]
        c.buffer_written = end
        object.__setattr__(buffer_ref, '_written', end)
        c.buffer_state = 'raw_retained'

    def buffer_write(self, ref, buffer_ref, generation, data):
        c, limit = self._buffer(ref, buffer_ref, generation)
        self.owner.require(c.buffer_written == 0 and type(data) is bytes, 'INVALID_INPUT')
        if c.api in FRAMES:
            self.owner.require(len(data) == limit, 'INVALID_INPUT')
        self.buffer_write_slice(ref, buffer_ref, generation, 0, data)

    def aux(self, ref, field):
        c = self._state(ref)
        self.owner.require(self._bound is not None, 'INVALID_INPUT')
        self.owner.require(field in ('scalar_aux_ack', 'count_aux_ack', 'right_transfer_ack'), 'INVALID_INPUT')
        setattr(c, field, True)

    def raise_exception(self, ref, error, phase):
        c = self._state(ref)
        o = self.owner
        o.require(self._bound is not None, 'INVALID_INPUT')
        o.require(isinstance(error, BaseException) and type(phase) is str, 'INVALID_INPUT')
        c.stopped = True
        if not c.wrapper_return:
            c.wrapper_state = 'raised'
        o.record_error(error, phase)

@dataclass(frozen=True, eq=False)
class _BootstrapPrimitives:
    owner: object
    injected_binding: object

    def __post_init__(self):
        if type(self.owner) is not KernelState or not callable(getattr(self.injected_binding, 'invoke_reserved', None)):
            raise KernelRefusal('INVALID_INPUT')

    def _file(self, ref):
        return self.owner.file_state(ref)

    def _call(self, api, file, args, requested=None):
        o = self.owner
        o._active()
        cleanup = api == 'CloseHandle'
        o.require(o._bootstrap is self and api in APIS and o._plan is not None, 'FOREIGN_IDENTITY')
        o.require(o.primary is None or cleanup, 'INVALID_INPUT')
        if api == 'ReadFile':
            limit = (file.spec.size // o.profile.chunk
                + int(file.spec.size % o.profile.chunk != 0) + 16) if file.spec.size else 0
            # A quota refusal precedes creating another reserved row. The
            # owner's index independently checks and charges the accepted row.
            o.require(uint(file._read_reservations, limit - 1), 'JOINT_CAP_EXCEEDED')
        buffer = o._read_buffer if api == 'ReadFile' else o._query_buffer if api in FRAMES else None
        c = o._reserve_original(api, file, requested, buffer)
        # The input carrier is an actual argument delivered to this invocation.
        if 'handle' in args:
            c.input_handle = args['handle']
            o.raw_store.prepare_input(c.ref,c.input_handle)
        hooks = AdoptionHooks(o, c)
        try:
            with o.operation_guard(cleanup=cleanup):
                invoke = self.injected_binding.invoke_reserved
                call_ref = c.ref
                ticket=InvocationTicket(_MINT,o,c,hooks)
                if buffer is not None:
                    object.__setattr__(buffer, '_written', 0)
                if api in ('GetFileType', 'GetFileInformationByHandleEx', 'GetFinalPathNameByHandleW', 'GetFileSizeEx'):
                    file.identity_queries.append(c.ordinal)
                o.call_clock(c, 'pre', cleanup)
                if api == 'CreateFileW':
                    file.open_state = 'entered_return_unknown'
                if cleanup:
                    file.close_state = 'entered_return_unknown'
                o._injected_current=c
                c.wrapper_result=invoke(ticket,args)
                c.wrapper_return = True
                c.wrapper_state = 'returned'
                o.raw_store.mark_exit(c.ref)
                o._reconcile_native(c)
                hooks._stop()
                if c.stopped or o.primary is not None and not cleanup:
                    raise o.primary or KernelRefusal('RAW_RETURN_UNKNOWN')
                o.call_clock(c, 'post', cleanup)
                o.require(c.scalar is not UNOBSERVED, 'RAW_RETURN_UNKNOWN')
                valid=(c.scalar is None or uint(c.scalar,INVALID)) if api=='CreateFileW' else uint(c.scalar,0xffffffff) if api in ('GetFileType','GetFinalPathNameByHandleW') else signed_bool(c.scalar)
                o.require(valid,'UNENCODABLE_RAW')
                if api in FRAMES:
                    o.require(c.buffer_written == FRAMES[api], 'IDENTITY_INCOMPLETE')
                    o.charge_raw(FRAMES[api])
                    c.query_bytes = bytes(memoryview(buffer._data)[:FRAMES[api]])
                    c.buffer_state = 'defined'
                    object.__setattr__(buffer, '_generation', buffer._generation + 1)
                return c
        except BaseException as error:
            c.wrapper_error=error
            c.stopped = True
            if not c.wrapper_return:
                c.wrapper_state = 'raised'
            o.record_error(error, 'original_close' if cleanup else 'binding_invoke')
            raise
        finally:
            hooks._stop()
            o._injected_current=None

    def acquire(self, spec):
        o = self.owner
        o._active()
        o.check()
        o.require(o._owned and o._bootstrap is self and type(spec) is FileSpec, 'FOREIGN_IDENTITY')
        file = o.registry._file_by_exact_path.get(spec.path)
        o.require(file is not None and file.spec == spec, 'FOREIGN_IDENTITY')
        o.require(file.open_state == 'unopened', 'INVALID_INPUT')
        prefix = 'source' if file.early else 'file'
        o.emit(prefix + '_open_reserved', {'file_id': file.id})
        c = self._call('CreateFileW', file, dict(path=spec.path, desired_access=2147483648,
            share_mode=1, security=None, creation=3, flags=2097280, template=None))
        o.require(usable(c.scalar), 'RAW_RETURN_UNKNOWN')
        o.emit(prefix + '_open_returned', {'file_id': file.id})
        return file.ref

    def inspect(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.check()
        o.require(o._bootstrap is self and usable(o.handle(file)) and not file.close_reserved
            and file.identity_state == 'not_attempted', 'IDENTITY_INCOMPLETE')
        file.identity_state = 'in_progress'
        handle = o.handle(file)
        if file.early:
            o.emit('source_identity_reserved', {'file_id': file.id})
        try:
            values = []
            calls = [('GetFileType', dict(handle=handle)),
                ('GetFileInformationByHandleEx', dict(handle=handle, info_class=9, buffer_bytes=8)),
                ('GetFinalPathNameByHandleW', dict(handle=handle, capacity=4101, flags=0)),
                ('GetFileSizeEx', dict(handle=handle))]
            for api, args in calls:
                values.append(self._call(api, file, args))
                o.check()
            typ, attrs, path, size = values
            o.require(type(typ.scalar) is int and typ.scalar == 1, 'IDENTITY_INCOMPLETE')
            o.require(attrs.scalar != 0 and attrs.query_bytes is not None, 'IDENTITY_INCOMPLETE')
            attributes, tag = struct.unpack('<II', attrs.query_bytes)
            o.require(not attributes & (16 | 1024), 'IDENTITY_INCOMPLETE')
            n = path.scalar
            o.require(uint(n, 4100) and n > 0 and path.query_bytes[2*n:2*n+2] == b'\0\0', 'IDENTITY_INCOMPLETE')
            text = path.query_bytes[:2*n].decode('utf-16-le', 'strict')
            if text.startswith('\\\\?\\'):
                text = text[4:]
            o.require(path_key(text) == path_key(file.spec.path), 'IDENTITY_INCOMPLETE')
            o.require(size.scalar != 0 and struct.unpack('<q', size.query_bytes)[0] == file.spec.size, 'IDENTITY_INCOMPLETE')
            o.check()
            file.identity_witness = (o, o.nonce, file.ref, handle, tuple(values))
            file.identity_state = 'verified'
            if file.early:
                o.emit('source_identity_returned', {'file_id': file.id})
        except BaseException as error:
            file.identity_state = 'unknown' if file.identity_state != 'refused' else 'refused'
            o.record_error(error, 'identity_query')
            raise

    def hash_capture(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.check()
        witness = file.identity_witness
        o.require(witness is not None and witness[0] is o and witness[1] is o.nonce
            and witness[2] is ref and witness[3] == o.handle(file)
            and not file.close_reserved and not file.hash_attempted, 'IDENTITY_INCOMPLETE')
        file.hash_attempted = True
        file.hasher = o._services.hash_factory()
        prefix = 'source' if file.early else 'file'
        o.emit(prefix + '_hash_reserved', {'file_id': file.id})
        c = None
        try:
            if file.spec.capture:
                o.begin_capture(file)
            while o.read_known(file) < file.spec.size:
                o.check()
                n = min(o.profile.chunk, file.spec.size - o.read_known(file))
                c = self._call('ReadFile', file, dict(handle=o.handle(file), requested=n, overlapped=None), n)
                o.require(o.defined(c), 'READ_COUNT_UNKNOWN')
                o.require(c.count > 0 and c.buffer_written >= c.count, 'READ_PROGRESS_INCOMPLETE')
                with o.operation_guard():
                    o.check()
                    o.hook('hash_update', c.ref)
                    o.check()
                    update = file.hasher.update
                    hash_view = memoryview(c.buffer._data)[:c.count]
                    c.hash_attempted = True
                    c.hash_return = update(hash_view)
                    del hash_view, update
                    try:
                        c._hash_fold_phase = 'applying'
                        file.hashed += c.count
                        c._hash_fold_phase = 'applied'
                    except BaseException as error:
                        o._accounting_failed(c, error, 'hash_return_fold')
                        raise
                    o.check()
                if file.spec.capture:
                    with o.operation_guard():
                        o.hook('copy_bytes', c.ref)
                        o.check()
                        offset = file.captured
                        copy_into = memoryview(file.assembly).__setitem__
                        copy_span = slice(offset, offset + c.count)
                        copy_view = memoryview(c.buffer._data)[:c.count]
                        c.copy_attempted = True
                        c.copy_return = copy_into(copy_span, copy_view)
                        del copy_into, copy_span, copy_view
                        try:
                            c._copy_fold_phase = 'applying'
                            file.captured += c.count
                            c._copy_fold_phase = 'applied'
                        except BaseException as error:
                            o._accounting_failed(c, error, 'copy_return_fold')
                            raise
                        o.check()
                object.__setattr__(c.buffer, '_generation', c.buffer._generation + 1)
            with o.operation_guard():
                digest = file.hasher.hexdigest
                file.actual_sha = digest()
                del digest
                o.check()
            o.require(file.actual_sha == file.spec.sha256, 'INVALID_INPUT')
            file.hash_complete = True
            if file.spec.capture:
                blob = bytes(file.assembly)
                o.finish_capture(file, blob)
            else:
                blob = None
            o.emit(prefix + '_hash_returned', {'file_id': file.id})
            return blob
        except BaseException as error:
            if c is not None:
                c.stopped = True
            if file.spec.capture and not file.capture_complete:
                file.capture_state = 'FAILED'
            o.record_error(error, 'hash_update')
            raise

    def close(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.require(o._bootstrap is self, 'FOREIGN_IDENTITY')
        o.require(not file.close_reserved, 'INVALID_INPUT')
        if not usable(o.handle(file)):
            return
        try:
            o.check(cleanup=True)
        except BaseException:
            file.close_state = 'not_dispatched_deadline'
            raise
        file.close_reserved = True
        file.close_state = 'reserved'
        try:
            o.emit('original_close_reserved', {'file_id': file.id}, cleanup=True)
        except BaseException:
            pass
        try:
            c = self._call('CloseHandle', file, dict(handle=o.handle(file)))
            o.require(c.scalar != 0, 'INVALID_INPUT')
        finally:
            try:
                o.emit('original_close_returned_or_unknown', {'file_id': file.id}, cleanup=True)
            except BaseException:
                pass


class KernelState(_KernelAlgorithms):
    def __init__(self,mint,services,origin,executing_module):
        need(mint is _MINT and type(origin) is Origin);self._origin=origin;self._nonce=origin._nonce;self._registry=Registry(self);self._profile=None
        self._port=PortFacade(self);self._sink=SinkFacade(self,services.output_backend);self._loader=CapturedLoader(self);self._early_context=self._evidence_context=None;self._journal=dict(reservation=0,next_sequence=0,closed=False,close_return_observed=False,close_acknowledged=False,tip=None,events=[])
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
        self._services=services;self._kernel_module=executing_module
        self._raw_store=RawCallStore(self);self._bootstrap=_BootstrapPrimitives(self,services.raw_backend)
        self._trusted_modules=dict(services.trusted_modules)
        self._trusted_modules['preflight_entry_kernel_v2']=executing_module
        self._late_table={};self._owner_ops=None;self._state_view=None;self._file_view=None
        self._late_integrity=None
        self._entry_plan=None;self._namespace_carrier=None;self._reservation_ready=False
        self._namespace_owned=False;self._entry_trace=['CORE_CREATED'];self._snapshot_serial=0
        self._module_integrity={};self._continuation=None
        self._kernel_identity=(_ORIGINAL_KERNEL_STATE,_ORIGINAL_ORIGIN,_ORIGINAL_REGISTRY,_ORIGINAL_RAW_STORE)
        self._kernel_exports=_ORIGINAL_EXPORTS
        self._external_root_envelope=freeze(services.external_root_envelope)
        self._codec=None;self._output_key=None;self._compiler=services.compile_exec
        self._phase='CORE_CREATED'

    kernel_module=property(lambda self:self._kernel_module)
    profile=property(lambda self:self._profile)
    origin=property(lambda self:self._origin)
    nonce=property(lambda self:self._nonce)
    registry=property(lambda self:self._registry)
    raw_store=property(lambda self:self._raw_store)
    port=property(lambda self:self._port)
    sink=property(lambda self:self._sink)
    loader=property(lambda self:self._loader)
    early_context=property(lambda self:self._early_context)
    evidence_context=property(lambda self:self._evidence_context)
    journal=property(lambda self:self._journal)
    output_key=property(lambda self:self._output_key)
    namespace_owned=property(lambda self:self._namespace_carrier is not None and signed_bool(self._namespace_carrier.namespace_scalar) and self._namespace_carrier.namespace_scalar!=0)
    reservation_ready=property(lambda self:self._reservation_ready)
    primary=property(lambda self:self._primary)
    secondary=property(lambda self:tuple(self._secondary))
    finalized=property(lambda self:self._final is not None)
    entry_trace=property(lambda self:tuple(self._entry_trace))

    def __getattr__(self,name):
        table=self.__dict__.get('_late_table',{})
        if type(name)is str and name in table:
            self._namespace_intact();return MethodType(table[name],self)
        raise AttributeError(name)

    def _diagnostic_phase(self):
        return self._error_phase or {'CREATED':'entry','CORE_CREATED':'entry','PLAN':'admit_plan','PLAN_ADMITTED':'admit_plan','RESERVATION':'reserve_output','EARLY_CAPTURE':'capture_early','BOOTSTRAP_CAPTURE':'capture_early','HELPERS_CAPTURED':'capture_early','HELPERS_LOADED':'load_source','HANDOFF':'handoff','CONTINUATION_ISSUED':'handoff','OPS_ATTACHED':'handoff','LOADING':'load_source','CONTINUATION':'continue_once','CONTINUING':'continue_once','CHECKERS':'core','FINALIZING':'finalize','FINALIZED':'finalize'}.get(self._phase,'entry')

    def call_clock(self,call,which,cleanup=False):
        self.require(which in ('pre','post'),'INVALID_INPUT')
        if self.origin._state=='invalid':raise KernelRefusal('CLOCK_INVALID')
        try:
            if which=='pre':
                call.pre_clock_attempted=True
                call.pre_clock=self.origin._clock()
                value=call.pre_clock
            else:
                call.post_clock_attempted=True
                call.post_clock=self.origin._clock()
                value=call.post_clock
        except BaseException as error:
            object.__setattr__(self.origin,'_state','invalid')
            self.record_error(error,'final_clock' if cleanup else self._diagnostic_phase());raise
        self.origin._clock_carrier.value=value
        try:return self.origin.accept(value,cleanup)
        except BaseException as error:
            self.record_error(error,'final_clock' if cleanup else self._diagnostic_phase());raise

    def _namespace_intact(self):
        module=self.kernel_module
        need(type(module)is ModuleType and module.__dict__ is globals(),'KERNEL_NAMESPACE_MISMATCH')
        need(module.__dict__.get('KernelState')is self._kernel_identity[0] and module.__dict__.get('Origin')is self._kernel_identity[1] and module.__dict__.get('Registry')is self._kernel_identity[2] and module.__dict__.get('RawCallStore')is self._kernel_identity[3],'KERNEL_NAMESPACE_MISMATCH')
        need(all(module.__dict__.get(name)is value for name,value in self._kernel_exports.items()),'KERNEL_NAMESPACE_MISMATCH')
        for name,(original,attach,cls) in self._module_integrity.items():
            need(self.loader.loaded.get(name)is original,'CAPTURED_MODULE_REBOUND')
            if attach is not None:need(original.__dict__.get('attach')is attach,'CAPTURED_MODULE_REBOUND')
            if cls is not None:need(original.__dict__.get(cls.__name__)is cls,'CAPTURED_MODULE_REBOUND')
        if self._late_integrity is not None:
            module,original_table,pairs=self._late_integrity
            need(module.__dict__.get('_LATE_TABLE')is original_table and tuple(original_table)==tuple(name for name,_ in pairs),'CAPTURED_MODULE_REBOUND')
            need(all(original_table.get(name)is fn for name,fn in pairs),'CAPTURED_MODULE_REBOUND')

    def reserve_bootstrap_output(self,key):
        self._active();self._phase='RESERVATION'
        self.require(self._plan is not None and self._namespace_carrier is None,'OUTPUT_ALREADY_RESERVED')
        self.require(type(key)is str and 0<len(key)<=128 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-' for c in key))
        self._output_key=key
        carrier=BootstrapOutputCarrier(_MINT,self);self._namespace_carrier=carrier
        rec=self._outputs['reservation'];ack=object()
        with self.operation_guard():
            self.check();rec['attempted']=True
            try:
                value=self._services.output_backend.reserve_callback(key,carrier,ack,self.origin.hard_end)
                rec['return_observed']=True;rec['acknowledged']=value is ack
                self._namespace_owned=signed_bool(carrier.namespace_scalar) and carrier.namespace_scalar!=0
                self.check()
                self.require(self.namespace_owned and rec['acknowledged'],'OUTPUT_NOT_OWNED')
                self._owned=True;self._reservation_ready=True
                self.emit('output_reserved',{})
                return BootstrapOutputRef(self,carrier)
            except BaseException as error:
                self._namespace_owned=signed_bool(carrier.namespace_scalar) and carrier.namespace_scalar!=0
                self.record_error(error,'reserve_output');raise
            finally:carrier._stop()

    def reserve_output(self,key):return self.reserve_bootstrap_output(key)

    def _reserve_original(self,api,file,requested=None,buffer=None):
        actor='BOOTSTRAP' if file.early else 'ORIGINAL'
        return self.reserve_call(api,actor,file.ref,requested,buffer)._state

    def committed_fact(self,call,axis):
        """Read canonical committed native authority; never repair a cache.

        This works for cold reporting/cleanup after an error or finalization.
        No clock, error latch, reconciliation, folding or allocation of owner
        state occurs. A reserved but not registered row has no observed axis.
        HANDLE64 bits0 is known native NULL represented by integer0, distinct
        from UNOBSERVED and from separately retained Python delivery None.
        """
        need(type(call)is CallState and call.owner is self and uint(call.ordinal,len(self.registry._calls)-1) and self.registry._calls[call.ordinal]is call,'FOREIGN_RAW_REF')
        need(type(axis)is str and axis in _AXES,'INVALID_INPUT')
        store=self.raw_store
        if store._bank is None or call.ordinal>=store.capacity or store._refs[call.ordinal]is not call.ref:return UNOBSERVED
        observation=store.axis(call.ref,axis)
        return observation['known_value'] if observation['native_state']=='COMMITTED' else UNOBSERVED

    def _cache_committed_fact(self,call,axis):
        # Only live dispatch derives these optional caches. Failed work never
        # retries them during reporting or cleanup of a different call.
        if call.api!='CloseHandle':self._require_accounting_work()
        value=self.committed_fact(call,axis)
        if value is UNOBSERVED:return
        field={'scalar':'scalar','count':'count','error_value':'error','error_definition':'error_definition'}[axis]
        previous=getattr(call,field)
        if previous is UNOBSERVED:setattr(call,field,value)
        else:need(_same_typed(previous,value),'NATIVE_CELL_CONFLICT')

    def reserve_call(self,api,actor,target_ref,requested=None,buffer_ref=None):
        self._active()
        self.require(type(api)is str and api in APIS and type(actor)is str and actor in ('BOOTSTRAP','ORIGINAL'),'ACTOR_PROFILE_UNQUALIFIED')
        self.require(self.reservation_ready and self.namespace_owned and self._plan is not None,'OUTPUT_NOT_OWNED')
        cleanup=api=='CloseHandle'
        if not cleanup:self._require_accounting_work();self.require(self.primary is None,'INVALID_INPUT')
        f=self.file_state(target_ref)
        self.require((actor=='BOOTSTRAP')==f.early,'FOREIGN_STATE')
        expected=self._read_buffer if api=='ReadFile' else self._query_buffer if api in FRAMES else None
        self.require(buffer_ref is expected and(requested is None if api!='ReadFile' else uint(requested,self.profile.chunk) and requested>0),'INVALID_INPUT')
        self.require(len(self.registry._calls)<self._plan['C'],'JOINT_CAP_EXCEEDED')
        c=self.registry._slots[len(self.registry._calls)]
        try:
            c.prepare(api,f,requested,buffer_ref)
            self.registry._calls.append(c)
            self.raw_store.register(c,actor)
            self._index_reserved_call(c)
        except BaseException as error:
            if c.prepared and len(self.registry._calls)==c.ordinal:
                try:list.append(self.registry._calls,c)
                except BaseException:pass
            self._accounting_failed(c,error,'pre_dispatch');raise
        return c.ref

    def _reconcile_native(self,c,fold=True):
        """Healthy live-dispatch cache derivation, never a report/getter path."""
        if c.api!='CloseHandle':self._require_accounting_work()
        for axis in _AXES:
            if self.committed_fact(c,axis)is not UNOBSERVED:self._cache_committed_fact(c,axis)
        if fold and c.api=='ReadFile':self._fold_read_fact(c)

    def _bootstrap_acquire(self,spec):
        with self.operation_guard():
            self.require(self.reservation_ready,'OUTPUT_NOT_OWNED');return self._bootstrap.acquire(spec)
    def _bootstrap_inspect(self,ref):
        with self.operation_guard():return self._bootstrap.inspect(ref)
    def _bootstrap_hash_capture(self,ref):
        with self.operation_guard():return self._bootstrap.hash_capture(ref)
    def _bootstrap_close(self,ref):
        with self.operation_guard(cleanup=True):return self._bootstrap.close(ref)

    def bootstrap_capture(self):
        with self.operation_guard():return self._bootstrap_capture_all()

    def _bootstrap_capture_all(self):
        self._active();self._phase='BOOTSTRAP_CAPTURE'
        self.require(self.reservation_ready and self.early_context is None,'OUTPUT_NOT_OWNED')
        for path in self._early_paths:
            ref=self._bootstrap_acquire(self.registry._file_by_exact_path[path].spec)
            self._bootstrap_inspect(ref);self._bootstrap_hash_capture(ref)
        files=tuple(f for f in self.registry._files if f.early)
        self._early_context=self.make_context(tuple(f.spec for f in files),{f.spec.path:f.blob for f in files},{f.spec.path:f.actual_sha for f in files})
        self._phase='HELPERS_CAPTURED';self._entry_trace.append('HELPERS_CAPTURED');return self.early_context

    def capture_early(self):return self.bootstrap_capture()

    def make_context(self,specs,blobs,digests,early_context=None):
        self.require(type(specs)is tuple and type(blobs)is dict and type(digests)is dict,'FOREIGN_STATE')
        for s in specs:
            self.require(type(s)is FileSpec and self.registry._file_by_exact_path.get(s.path)is not None and self.registry._file_by_exact_path[s.path].spec is s,'FOREIGN_STATE')
            f=self.registry._file_by_exact_path[s.path]
            self.require(f.hash_complete and digests.get(s.path)==f.actual_sha and(not s.capture or f.capture_complete and blobs.get(s.path)is f.blob),'EARLY_SOURCE_NOT_LIVE_COMPLETE')
        self.require(set(blobs)=={s.path for s in specs if s.capture} and set(digests)=={s.path for s in specs},'FOREIGN_STATE')
        if early_context is not None:self.require(early_context is self.early_context,'FOREIGN_STATE')
        return CapturedContext(self,self.nonce,specs,blobs,digests,early_context,_issuer=_MINT)

    def load_captured(self,fullname):
        self._active();self._phase='LOADING';return self.loader.load(fullname)
    def load_source(self,fullname):return self.load_captured(fullname)

    def issue_continuation(self):
        self._active();self._namespace_intact();self.check();self._live_early()
        self.require(not self._issued and self.primary is None and self.reservation_ready,'HANDOFF_REPEATED')
        p=self._entry_plan
        for name,classname in ((p.owner_ops_name,'OwnerOps'),(p.file_view_name,'FileView')):
            module=self.loader.loaded.get(name)
            self.require(type(module)is ModuleType and name in self._module_integrity,'SOURCE_LOADER_UNBOUND')
            self.require(callable(module.__dict__.get('attach')) and type(module.__dict__.get(classname))is type,'CAPTURED_MODULE_REBOUND')
        self._namespace_intact();self._issued=True;self._phase='CONTINUATION_ISSUED'
        self.emit('handoff_reserved',{});self._continuation=KernelContinuation(_MINT,self)
        return self._continuation

    def validate_state_view(self,view):
        self._active();self._namespace_intact()
        need(type(view)is StateView and view is self._state_view and view._state is self and self._claimed,'FOREIGN_STATE')

    def install_owner_ops(self,view,ops,table):
        self.validate_state_view(view);self.require(self._owner_ops is None and type(table)is MappingProxyType,'HANDOFF_REPEATED')
        module,attach,cls=self._module_integrity[self._entry_plan.owner_ops_name]
        self.require(type(ops)is cls and ops._state is self and ops._view is view and ops._attach_ref is attach,'FOREIGN_STATE')
        self.require(self._late_integrity is not None and table is self._late_integrity[1] and table is module.__dict__.get('_LATE_TABLE') and all(type(name)is str and type(fn)is type(entry) and fn.__globals__ is module.__dict__ for name,fn in table.items()),'FOREIGN_STATE')
        self._late_table=dict(table);self._owner_ops=ops;self._phase='OPS_ATTACHED';self._entry_trace.append('OPS_ATTACHED')

    def install_file_view(self,view,file_view):
        self.validate_state_view(view);self.require(self._owner_ops is not None and self._file_view is None,'HANDOFF_REPEATED')
        module,attach,cls=self._module_integrity[self._entry_plan.file_view_name]
        self.require(type(file_view)is cls and file_view._state is self and file_view._view is view and file_view._attach_ref is attach,'FOREIGN_STATE')
        object.__setattr__(self.port,'_delegate',file_view);self._file_view=file_view

    def require_role1_representable(self,snapshot=None):
        if snapshot is not None:
            if type(snapshot)is not KernelSnapshot or snapshot.owner is not self:raise KernelRefusal('NATIVE_STATE_NOT_REPRESENTABLE')
            return snapshot.require_role1_representable()
        return self.raw_store.require_representable()

    def raw_call_view(self,ref):
        c=self.raw_store._call(ref)
        facts=dict(ordinal=c.ordinal,api=c.api,invoked=c.invoked,wrapper_return_observed=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,pre_clock=_clock_fact(c.pre_clock),post_clock=_clock_fact(c.post_clock),pre_clock_attempted=c.pre_clock_attempted,post_clock_attempted=c.post_clock_attempted,read_fold=c._read_fold_phase,hash_fold=c._hash_fold_phase,copy_fold=c._copy_fold_phase,python_delivery=self._python_delivery_facts(c))
        return RawCallView(_MINT,self,ref,RawCallSnapshot(_MINT,self.raw_store.copy_row(ref),facts))

    def _python_delivery_facts(self,c):
        tag='HANDLE' if c.api=='CreateFileW' else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32'
        definition=c._python_error_definition
        return dict(scalar=atom(c._python_scalar,tag),count=atom(c._python_count,'COUNT32'),error_value=atom(c._python_error_value,'DWORD'),error_definition=dict(tag='BOOL',value=definition) if type(definition)is bool else atom(definition,'DEFINEDNESS'),authority='PYTHON_DELIVERY_ONLY_NOT_NATIVE_COMMIT')

    def _issue_snapshot(self,data,finalized=False):
        rows=[];partial=False;capture_error=None
        for c in self.registry._calls:
            try:
                self.check(cleanup=True)
                scalar=self.committed_fact(c,'scalar');count=self.committed_fact(c,'count');error=self.committed_fact(c,'error_value');definition=self.committed_fact(c,'error_definition')
                scalar_atom=dict(tag='NULL',value=None) if c.api=='CreateFileW' and type(scalar)is int and scalar==0 else atom(scalar,'HANDLE' if c.api=='CreateFileW' else 'DWORD' if c.api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32')
                facts=dict(ordinal=c.ordinal,api=c.api,invoked=c.invoked,scalar=scalar_atom,count=atom(count,'COUNT32'),error=atom(error,'DWORD'),error_definition=atom(definition,'DEFINEDNESS') if definition is UNOBSERVED else dict(tag='BOOL',value=definition),wrapper_return=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,pre_clock=_clock_fact(c.pre_clock),post_clock=_clock_fact(c.post_clock),pre_clock_attempted=c.pre_clock_attempted,post_clock_attempted=c.post_clock_attempted,read_fold=c._read_fold_phase,hash_fold=c._hash_fold_phase,copy_fold=c._copy_fold_phase,hash_return_observed=c.hash_return is not UNOBSERVED,copy_return_observed=c.copy_return is not UNOBSERVED,python_delivery=self._python_delivery_facts(c))
                rows.append(RawCallSnapshot(_MINT,self.raw_store.copy_row(c.ref),facts))
            except BaseException as error:
                partial=True;capture_error=error
                if not self.finalized:
                    try:self.record_error(error,'snapshot')
                    except BaseException:pass
                break
        if partial:
            data=thaw(freeze(data))
            data['native_snapshot_partial']=True
            data['native_snapshot_eligible']=False
            data['pure_seam_complete']=False
            data['status']=self._status if self.primary is not None else 'INCOMPLETE'
            if type(data.get('terminal'))is dict:
                data['terminal']['pure_owner_ack']=False;data['terminal']['result_issued']=False
            if type(data.get('errors'))is dict:
                data['errors']=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self.secondary])
        self._snapshot_serial+=1
        snapshot=KernelSnapshot(_MINT,self,data,rows,partial,capture_error)
        if not partial:
            try:self.check(cleanup=True)
            except BaseException as error:
                # The completed raw copies remain available, but the already
                # assembled positive object is never issued after a late stop.
                capture_error=error;data=thaw(snapshot._data)
                data['native_snapshot_partial']=True;data['native_snapshot_eligible']=False
                data['pure_seam_complete']=False;data['status']=self._status
                if type(data.get('terminal'))is dict:
                    data['terminal']['pure_owner_ack']=False;data['terminal']['result_issued']=False
                if type(data.get('errors'))is dict:data['errors']=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self.secondary])
                self._terminal['pure_owner_ack']=False;self._terminal['result_issued']=False
                return KernelSnapshot(_MINT,self,data,rows,True,capture_error)
        if partial:
            self._terminal['pure_owner_ack']=False;self._terminal['result_issued']=False
        return snapshot

    def snapshot(self):
        if self._final is not None:return self._final
        if '_snapshot' in self._late_table:return self._snapshot()
        p=self._canonical_projection(include_calls=self.profile is PROFILE_N4)
        data=dict(schema_version=1,scope='entry_kernel_source_pure',phase=self._phase,status=self._status,origin=dict(start=self.origin.start,now=self.origin.now,work_end=self.origin.work_end,hard_end=self.origin.hard_end),plan=None if self._plan is None else dict(self._plan),files=p['files'],calls=p['calls'],api_counters=p['api_counters'],byte_totals=p['byte_totals'],namespace_owned=self.namespace_owned,reservation_ready=self.reservation_ready,entry_trace=list(self._entry_trace),errors=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self.secondary]),qualification=dict(QUALIFICATION))
        return self._issue_snapshot(data)

    def finalize_incomplete(self):
        self._active()
        if '_finish' in self._late_table:return self._finish(False)
        self._phase='FINALIZING'
        for f in reversed(self.registry._files):
            if not f.close_reserved and usable(self.handle(f)):
                try:self._bootstrap_close(f.ref)
                except BaseException as error:
                    try:self.record_error(error,'original_close')
                    except BaseException:pass
        self._status='INCOMPLETE' if self.primary is None else self._status
        snap=self.snapshot();self._final=snap;self._phase='FINALIZED';return snap

    def request_native_input(self,file_ref,launch=None):
        # No NativeInputLease issuer exists in this pure slice. Even an owned,
        # hash-complete handle is not qualified child/image/launch authority.
        return request_native_inputs(self,(file_ref,),None,launch)


class StateView:
    __slots__=('_state','_capsule')
    def __init__(self,mint,state,capsule):
        need(mint is _MINT);object.__setattr__(self,'_state',state);object.__setattr__(self,'_capsule',capsule)
    def __setattr__(self,key,value):raise TypeError('immutable non-owning state view')
    state=property(lambda self:self._state)
    owner=property(lambda self:self._state)
    origin=property(lambda self:self._state.origin)
    nonce=property(lambda self:self._state.nonce)
    registry=property(lambda self:self._state.registry)
    raw_store=property(lambda self:self._state.raw_store)

class KernelContinuation:
    __slots__=('_state','_origin','_nonce','_registry','_raw_store','_early','_claimed')
    def __init__(self,mint,state):
        need(mint is _MINT)
        for key,value in dict(_state=state,_origin=state.origin,_nonce=state.nonce,_registry=state.registry,_raw_store=state.raw_store,_early=state.early_context,_claimed=False).items():object.__setattr__(self,key,value)
    def __setattr__(self,key,value):raise TypeError('immutable source-issued continuation')
    owner=property(lambda self:self._state)
    def claim_operations(self,attach_callable):
        state=self._state;state._active();state._namespace_intact()
        need(not self._claimed and not state._claimed and state._continuation is self,'HANDOFF_REPEATED')
        need(state.origin is self._origin and state.nonce is self._nonce and state.registry is self._registry and state.raw_store is self._raw_store and state.early_context is self._early,'FOREIGN_STATE')
        module,original,cls=state._module_integrity[state._entry_plan.owner_ops_name]
        need(attach_callable is original and module.__dict__.get('attach')is original,'FOREIGN_STATE')
        state.check();state._live_early()
        state.require(state.reservation_ready and state.primary is None,'OUTPUT_NOT_OWNED')
        view=StateView(_MINT,state,self)
        object.__setattr__(self,'_claimed',True);state._claimed=True;state._state_view=view
        state._claim_call_count=len(state.registry._calls);state.emit('handoff_claimed',{})
        return view

class CapturedLoader:
    """Actual captured code only; no sys.modules or filesystem resolution."""
    def __init__(self,owner):
        self.owner=owner;self.rules={};self.loaded={};self.active=set();self.attempted=[];self.returned=[];self.cache_hits=[];self.records=[]
    def _import(self,caller,name,globals=None,locals=None,fromlist=(),level=0):
        state=self.owner;state.check();state._live_early();state._namespace_intact()
        state.require(caller in self.active and type(name)is str and type(level)is int and level==0,'SOURCE_IMPORT_REFUSED')
        state.require(name in self.rules[caller].dependencies,'SOURCE_IMPORT_REFUSED')
        if name in state._trusted_modules:
            module=state._trusted_modules[name]
            state.require(type(module)is ModuleType,'SOURCE_IMPORT_REFUSED')
            if name=='preflight_entry_kernel_v2':state.require(module is state.kernel_module,'KERNEL_NAMESPACE_MISMATCH')
            return module
        return self.load(name)
    def load(self,name):
        state=self.owner
        with state.operation_guard():
            state._active();state.check();state._live_early();state._namespace_intact()
            state.require(type(name)is str and name in self.rules,'SOURCE_IMPORT_REFUSED')
            if name in self.loaded:self.cache_hits.append(name);return self.loaded[name]
            state.require(name not in self.active and name not in self.attempted,'SOURCE_IMPORT_REFUSED')
            self.attempted.append(name)
            rec=dict(module=name,state='reserved',return_observed=False,accepted=False);self.records.append(rec)
            state.emit('source_compile_reserved',{'module':name});state.check()
            self.active.add(name);rec['state']='entered_return_unknown'
            module=ModuleType(name);namespace=module.__dict__
            namespace['__package__']=name if self.rules[name].package else name.rpartition('.')[0]
            builtins_source=__builtins__ if type(__builtins__)is dict else __builtins__.__dict__
            safe={k:v for k,v in builtins_source.items() if k not in ('open','input','exec','eval','compile','__import__','breakpoint','exit','quit')}
            safe['__import__']=lambda name,globals=None,locals=None,fromlist=(),level=0:self._import(module.__name__,name,globals,locals,fromlist,level)
            namespace['__builtins__']=safe
            try:
                rec['compiler_return']=state._services.compile_exec(name,state.early_context.bytes_for(self.rules[name].path),namespace)
                rec.update(state='return_observed',return_observed=True);self.returned.append(name)
                state.check();state._live_early();state._namespace_intact()
                state.require(rec['compiler_return']is None,'SOURCE_IMPORT_REFUSED')
                state.require(namespace.get('__name__')==name and namespace.get('__builtins__')is safe,'SOURCE_IMPORT_REFUSED')
                rec['accepted']=True;self.loaded[name]=module
                classname='OwnerOps' if name==state._entry_plan.owner_ops_name else 'FileView' if name==state._entry_plan.file_view_name else None
                attach=namespace.get('attach') if classname else None;cls=namespace.get(classname) if classname else None
                state._module_integrity[name]=(module,attach,cls)
                if name==state._entry_plan.owner_ops_name:
                    table=namespace.get('_LATE_TABLE')
                    expected=('match_full_roster','hash_remaining','_packet','_publish','_make_report','_close','finalize','_finish','_context_report','_wire_call','_wire_source','_consume_ledger','freeze_generated','generated_bytes','generated_artifact','_install_generated','check_generated','_snapshot')
                    state.require(type(table)is MappingProxyType and tuple(table)==expected and all(type(fn)is type(entry) and fn.__globals__ is namespace for fn in table.values()),'CAPTURED_MODULE_REBOUND')
                    state._late_integrity=(module,table,tuple(table.items()))
                if name==state._entry_plan.codec_name:state._codec=module
                state.emit('source_compile_returned',{'module':name})
                state._phase='HELPERS_LOADED';return module
            except BaseException as error:
                state.record_error(error,'load_source');raise
            finally:self.active.remove(name)

def _clock_atom(value):
    if value is UNOBSERVED:return dict(tag='UNOBSERVED',value=None)
    return dict(tag='I64' if type(value)is int and -(1<<63)<=value<(1<<63) else 'F64' if type(value)is float and math.isfinite(value) else 'INVALID',value=value if _numeric(value) else None)

def _clock_fact(value):
    if value is UNOBSERVED:return dict(tag='UNOBSERVED',bits=None,value=None,valid=False)
    if type(value)is float:return dict(tag='F64',bits=struct.unpack('<Q',struct.pack('<d',value))[0],value=value if math.isfinite(value) else None,valid=math.isfinite(value))
    if type(value)is int and -(1<<63)<=value<(1<<63):return dict(tag='I64',bits=value&INVALID,value=value,valid=True)
    if type(value)is bool:return dict(tag='BOOL_INVALID',bits=int(value),value=value,valid=False)
    if value is None:return dict(tag='NULL_INVALID',bits=None,value=None,valid=False)
    return dict(tag='UNENCODABLE_INVALID',bits=None,value=None,valid=False)

def entry(bootstrap_services,entry_plan,*,executing_module):
    """First application operation is the prebound original clock call.

    Fresh exact services/attempt/provider are pre-entry TCB requirements.
    Their class checks follow the first sample on the valid entry path;
    the retainer itself refuses a repeated attempt before overwriting it.
    """
    attempt=bootstrap_services.entry_attempt
    attempt.capture_start(bootstrap_services.clock)
    state=None
    try:
        need(type(bootstrap_services)is PreboundServices and type(attempt)is EntryAttempt,'FOREIGN_STATE')
        need(type(executing_module)is ModuleType and executing_module is bootstrap_services.executing_module and executing_module.__dict__ is globals(),'KERNEL_NAMESPACE_MISMATCH')
        need(type(bootstrap_services.raw_backend)is SyntheticRawBackend and callable(bootstrap_services.raw_backend.callback) and type(bootstrap_services.output_backend)is SyntheticOutputBackend,'UNQUALIFIED_BACKEND')
        need(callable(bootstrap_services.hash_factory) and callable(bootstrap_services.compile_exec),'INVALID_INPUT')
        need(type(bootstrap_services.trusted_modules)is dict and all(type(k)is str and k in ('dataclasses','hashlib','json','math','re','struct','types') and type(v)is ModuleType for k,v in bootstrap_services.trusted_modules.items()),'SOURCE_IMPORT_REFUSED')
        need(type(bootstrap_services.external_root_envelope)is dict,'INVALID_INPUT')
        need(all(globals().get(name)is value for name,value in _ORIGINAL_EXPORTS.items()),'KERNEL_NAMESPACE_MISMATCH')
        origin=Origin(_MINT,bootstrap_services.clock,attempt)
        # Core/Registry/RawCallStore/facades precede all plan/helper work.
        state=KernelState(_MINT,bootstrap_services,origin,executing_module)
        attempt.state=state
        need(type(entry_plan)is EntryPlan,'INVALID_INPUT');state._entry_plan=entry_plan
        profile=entry_plan.profile if entry_plan.profile is not None else PROFILE_ORIGINAL7_1M
        state.require(profile is PROFILE_N4 or profile is PROFILE_ORIGINAL7_1M,'INVALID_INPUT')
        state._profile=profile
        state.require(all(type(n)is str for n in (entry_plan.owner_ops_name,entry_plan.file_view_name,entry_plan.codec_name)),'INVALID_INPUT')
        state.require(len({entry_plan.owner_ops_name,entry_plan.file_view_name,entry_plan.codec_name})==3,'SOURCE_IMPORT_REFUSED')
        state._namespace_intact()
        state.admit_plan(entry_plan.files,entry_plan.early_paths,entry_plan.module_rules)
        state.raw_store.allocate(state._plan['C'])
        state.require(all(n in state.loader.rules for n in (entry_plan.owner_ops_name,entry_plan.file_view_name,entry_plan.codec_name)),'SOURCE_IMPORT_REFUSED')
        state.require('preflight_entry_kernel_v2' not in state.loader.rules and not any(r.fullname in state._trusted_modules for r in entry_plan.module_rules),'STATIC_PIN_CYCLE')
        state._phase='PLAN_ADMITTED';state._entry_trace.append('PLAN_ADMITTED')
        state.reserve_bootstrap_output(entry_plan.output_key)
        return state
    except BaseException as error:
        if attempt.error is None:attempt.error=error
        if state is not None:
            try:state.record_error(error,'entry')
            except BaseException:pass
        raise

# Stored original class objects detect ordinary namespace rebinding after entry.
_ORIGINAL_KERNEL_STATE=KernelState
_ORIGINAL_ORIGIN=Origin
_ORIGINAL_REGISTRY=Registry
_ORIGINAL_RAW_STORE=RawCallStore

def request_native_inputs(state,file_refs,consumer_binding=None,launch_binding=None):
    """Negative-only boundary: no issuer for a qualified native capability.

    Ordinary foreign-object and consumed-file branches are meaningful guards;
    they do not qualify an actual child/image/path-lifetime mechanism.
    """
    need(type(state)is _ORIGINAL_KERNEL_STATE,'FOREIGN_NATIVE_BINDING')
    state._active()
    if launch_binding is not None:raise KernelRefusal('FOREIGN_LAUNCH_BINDING')
    if consumer_binding is not None:raise KernelRefusal('FOREIGN_NATIVE_BINDING')
    need(type(file_refs)is tuple and len(file_refs)>0,'LEASE_NOT_LIVE_OR_PATH_UNKNOWN')
    for ref in file_refs:
        f=state.file_state(ref)
        if f.close_reserved or not usable(state.handle(f)) or f.identity_state!='verified' or not f.hash_complete:
            raise KernelRefusal('LEASE_NOT_LIVE_OR_PATH_UNKNOWN')
    raise KernelRefusal('NATIVE_ROUTE_UNAVAILABLE')

_ORIGINAL_EXPORTS=MappingProxyType({name:globals()[name] for name in ('entry','Origin','KernelState','Registry','RawCallStore','RawCallRef','RawCallView','FileSpec','FileRef','CapturedContext','EntryAttempt','PreboundServices','StateView','KernelContinuation','KernelSnapshot','KernelRefusal')})

