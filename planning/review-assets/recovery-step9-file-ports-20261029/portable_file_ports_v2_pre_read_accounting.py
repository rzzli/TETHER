"""Portable injected file primitives v2; no ctypes, SDK, filesystem or activation.

RawReturn is a captured Python observation, NOT an actual FFI ownership bridge.
The first real entry, platform adapter and complete verifier remain pending.
"""
from dataclasses import dataclass
import hashlib
import math
import re
import struct
from types import MappingProxyType

INVALID=2**64-1
CHUNK=65536
MINT=object()
HEX=re.compile(r'[0-9a-f]{64}\Z')
API_NAMES=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle','GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')
_new_hasher=hashlib.sha256


class PortError(RuntimeError):
    def __init__(self,code,kind='incomplete_known_failure'):
        super().__init__(code);self.code=code;self.kind=kind


def need(value,code,kind='incomplete_known_failure'):
    if not value:raise PortError(code,kind)


def uint(value,cap=2**32-1):return type(value) is int and 0<=value<=cap
def raw_BOOL(value):
    need(type(value) is int and -2**31<=value<2**31,'raw_BOOL_domain','control_rejected')
    return value!=0


def path_key(path,*,drive_root=False):
    need(type(path) is str,'path_type','admission_rejected')
    try:units=len(path.encode('utf-16-le','strict'))//2
    except UnicodeError as error:raise PortError('path_scalar','admission_rejected') from error
    need(3<=units<=4096,'UTF16_cap','admission_rejected')
    if drive_root:
        need(path in ('C:\\','D:\\'),'unapproved_root_spelling','admission_rejected');return path[0].lower()+':\\'
    need(len(path)>=4 and path[0] in 'CDcd' and path[1]==':' and path[2] in '\\/','path_root','admission_rejected')
    converted=path.replace('/','\\')
    for part in converted[3:].split('\\'):
        need(part not in ('','.','..') and not part.endswith(('.',' ')) and not any(ord(c)<32 or ord(c)==127 or c in '<>:"|?*~' for c in part),'path_component','admission_rejected')
        need(part.split('.',1)[0].lower() not in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]},'path_device','admission_rejected')
    return converted.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))


@dataclass(frozen=True,slots=True)
class RawReturn:
    value:object
    last_error:int
    error_defined:bool
    raw_count:object
    raw_count_defined:bool
    buffer:bytes
    buffer_defined:bool


@dataclass(frozen=True,slots=True)
class FileSpec:
    path:str
    size:int
    sha256:str
    capture:bool=True


@dataclass(frozen=True,slots=True)
class EntrySpec:
    name:str
    kind:str


class Origin:
    """One injected origin. This class is not a real pre-import bootstrap."""
    __slots__=('_clock','_start','_last','_work_end','_end','_nonce','_clock_failed')
    def __init__(self,mint,clock,start):
        need(mint is MINT,'source_origin_required')
        for key,value in dict(_clock=clock,_start=start,_last=start,_work_end=start+295,_end=start+300,_nonce=object(),_clock_failed=False).items():object.__setattr__(self,key,value)
    def __setattr__(self,name,value):raise TypeError('Origin is not assignable')
    @property
    def start(self):return self._start
    @property
    def last(self):return self._last
    @property
    def work_end(self):return self._work_end
    @property
    def end(self):return self._end
    @property
    def nonce(self):return self._nonce
    def check(self,*,hard=False):
        limit=self.end if hard else self.work_end
        need(self.last<limit,'hard_deadline' if hard else 'work_deadline','incomplete_deadline')
        try:
            now=self._clock()
            need(type(now) in (int,float) and not isinstance(now,bool) and math.isfinite(now) and now>=self.last,'invalid_clock','incomplete_unknown')
        except BaseException:object.__setattr__(self,'_clock_failed',True);raise
        object.__setattr__(self,'_last',now)
        need(now<limit,'hard_deadline' if hard else 'work_deadline','incomplete_deadline')
        return now


def begin_injected(clock,build):
    """Synthetic entry only; first call precedes this injected setup, not imports."""
    start=clock();need(type(start) in (int,float) and not isinstance(start,bool) and math.isfinite(start),'finite_first_clock')
    return build(Origin(MINT,clock,start))


def _freeze(v):
    if type(v) is dict:return MappingProxyType({k:_freeze(x) for k,x in v.items()})
    if type(v) is list:return tuple(_freeze(x) for x in v)
    return v


def _thaw(v):
    if type(v) is MappingProxyType:return {k:_thaw(x) for k,x in v.items()}
    if type(v) is tuple:return [_thaw(x) for x in v]
    return v


@dataclass(frozen=True,slots=True)
class Observation:
    _data:object
    def to_dict(self):return _thaw(self._data)


@dataclass(frozen=True,slots=True)
class _IdentityWitness:
    owner:object
    nonce:object
    slot:object
    handle:int
    path:object
    spec:object
    size:int
    observations:tuple


@dataclass(frozen=True,slots=True)
class HarnessIdentityPrecondition:
    """Source-issued fictional seed assumption, NEVER four observed queries."""
    owner:object
    nonce:object
    slot:object
    handle:int
    path:object
    spec:object


class Slot:
    def __init__(self,identity,kind,path=None,spec=None):
        self.id,self.kind,self.path,self.spec=identity,kind,path,spec
        self.handle=None;self.open_state='reserved';self.closer=None
        self.close_state='not_attempted';self.close_attempts=0
        self.raw_open=None;self.raw_reads=[];self.identity=[];self.read_attempts=0
        self.identity_ok=False
        self.known_bytes=self.hashed_bytes=self.captured_bytes=0
        self.write_offset=0;self.pending_read=False;self.hash_pending=False
        self.capture=bytearray();self.hash=None
        self.output_hash=None;self.output_hashed=0;self.output_flushed=0;self.record_count=0;self.reserved_bytes=0;self.records=[]
    def projection(self):
        return dict(id=self.id,kind=self.kind,handle=self.handle,open_state=self.open_state,
                    close_state=self.close_state,closer=self.closer,close_attempts=self.close_attempts)


class PortableOwner:
    """Central portable ownership, not a production authority or verifier gate."""
    def __init__(self,origin,api,hook,*,files,output,allowed_entries=(),admitted_directories=(),event_budget=175):
        need(type(origin) is Origin and callable(api) and callable(hook),'injected_ports_required')
        need(type(files) is tuple and len(files)<=256,'finite_file_roster')
        self.origin,self.api,self.hook=origin,api,hook;self.output=output;path_key(output)
        self.specs={}
        for spec in files:
            need(type(spec) is FileSpec and uint(spec.size,2**63-1) and type(spec.capture) is bool and type(spec.sha256) is str and HEX.fullmatch(spec.sha256),'file_descriptor')
            key=path_key(spec.path);need(key not in self.specs,'file_role_collision');self.specs[key]=spec
        need(sum(spec.size for spec in files if spec.capture)<=67108864,'capture_aggregate')
        need(type(allowed_entries) is tuple and len(allowed_entries)<=64,'finite_entry_roster')
        self.entry_types={}
        for entry in allowed_entries:
            need(type(entry) is EntrySpec and entry.kind in ('file','directory') and '\\' not in entry.name and '/' not in entry.name,'entry_spec')
            key=path_key('D:\\'+entry.name);need(key not in self.entry_types,'entry_alias');self.entry_types[key]=entry.kind
        need(type(admitted_directories) is tuple and len(admitted_directories)<=1024,'directory_index')
        self.directories={}
        for path in admitted_directories:
            key=path_key(path,drive_root=len(path)==3);need(key not in self.directories,'directory_alias');self.directories[key]=path
        need(uint(event_budget,2048),'event_budget')
        n=len(files);f=9
        self.caps=dict(CreateFileW=n+f,GetFileType=n+f,GetFileInformationByHandleEx=n+f,GetFinalPathNameByHandleW=n+f,GetFileSizeEx=n+f,ReadFile=sum((s.size+65535)//65536+16 if s.size else 0 for s in files),CloseHandle=n+f,GetFileAttributesExW=1040,FindFirstFileExW=16,FindNextFileW=178,FindClose=16,CreateDirectoryW=1,WriteFile=event_budget+412,FlushFileBuffers=event_budget+9)
        self.attempts={n:0 for n in API_NAMES};self.returns={n:0 for n in API_NAMES};self.calls=[];self.slots=[]
        self.namespace_owned=self.reservation_ready=False;self.primary=None;self.secondary=[];self._primary_object=None
        self.disposition='primitive_complete';self.known_read_bytes=self.hashed_bytes=self.captured_bytes=0
        self.known_write_bytes=self.write_hash_bytes=self.flushed_known_bytes=0
        self.read_count_unknown=self.write_count_unknown=False;self._finished=False;self._test_seeded=False;self._composition=False;self._phase=None;self._handoff_claimed=False
        self.event_budget=event_budget;self.reserved_output_bytes=0
        self._identities={};self._harness_identities={};self._seed_slots=set()

    def seed_for_tests(self,*,namespace_owned,reservation_ready,slots,known_read_bytes=0,hashed_bytes=0,captured_bytes=0):
        """Explicit test-only preconditions; no production handoff or ready token."""
        need(not self.slots and not self.calls,'test_seed_before_operations')
        need(type(namespace_owned) is bool and type(reservation_ready) is bool,'test_seed_bool')
        self._test_seeded=True;self.namespace_owned=namespace_owned;self.reservation_ready=reservation_ready
        self.known_read_bytes=known_read_bytes;self.hashed_bytes=hashed_bytes;self.captured_bytes=captured_bytes
        for identity,kind,handle,spec in slots:
            need(kind in ('original_file','output_file','file_search') and uint(handle,INVALID) and handle not in (0,INVALID),'test_seed_known_handle')
            if kind=='original_file':need(type(spec) is FileSpec and self.specs.get(path_key(spec.path)) is spec,'test_seed_current_spec')
            slot=Slot(identity,kind,spec.path if spec else None,spec);slot.handle=handle;slot.open_state='observed_owned';slot.closer='FindClose' if kind=='file_search' else 'CloseHandle';self.slots.append(slot);self._seed_slots.add(slot)

    def assume_seed_identity_for_tests(self,identity):
        """HARNESS ONLY: acknowledge pre-existing fictional file identity.

        Only pristine seeded slots qualify. This token is not serialized and
        cannot authorize a slot opened by this owner or a caught failed query.
        No test assumption is a real observed identity or production authority.
        """
        slot=self._slot(identity)
        need(self._test_seeded and not self.calls and slot in self._seed_slots and slot.kind in ('original_file','output_file') and not slot.identity and slot.close_attempts==0,'harness_seed_identity_only')
        need(identity not in self._harness_identities,'harness_identity_once')
        token=HarnessIdentityPrecondition(self,self.origin.nonce,slot,slot.handle,slot.path,slot.spec)
        self._harness_identities[identity]=token
        return token

    def _require_identity(self,slot):
        need(slot in self.slots,'current_identity_slot')
        token=self._identities.get(slot.id)
        assumed=self._harness_identities.get(slot.id)
        witness=token if type(token) is _IdentityWitness else assumed if type(assumed) is HarnessIdentityPrecondition and slot in self._seed_slots and not slot.identity else None
        need(witness is not None and witness.owner is self and witness.nonce is self.origin.nonce and witness.slot is slot and witness.handle==slot.handle and witness.path==slot.path and witness.spec is slot.spec,'four_query_identity_required')
        if type(witness) is _IdentityWitness:
            need(len(witness.observations)==4 and tuple(slot.identity)==witness.observations and witness.size==(slot.spec.size if slot.spec is not None else 0),'four_query_identity_required')

    def diagnostic_projection(self):
        result={'namespace_owned':self.namespace_owned,'reservation_ready':self.reservation_ready,'known_read_bytes':self.known_read_bytes,'hashed_bytes':self.hashed_bytes,'captured_bytes':self.captured_bytes,'known_write_bytes':self.known_write_bytes,'write_hash_bytes':self.write_hash_bytes}
        for s in self.slots:
            for key,value in s.projection().items():result['slots.'+s.id+'.'+key]=value
        return result

    def _latch(self,error,code=None,kind=None):
        code=code or (error.code if type(error) is PortError else self._phase or type(error).__name__)
        kind=kind or (error.kind if type(error) is PortError else 'incomplete_unknown')
        if self.primary is None:self.primary=code;self._primary_object=error;self.disposition=kind
        else:self.secondary.append(code)

    def _call(self,name,args,observe=None,*,hard=False,entered=None):
        self.origin.check(hard=hard)
        need(self.attempts[name]<self.caps[name],'API_cap_'+name)
        record=dict(name=name,return_observed=False,raw=None);self.calls.append(record);self.attempts[name]+=1
        if entered is not None:entered()
        returned=self.api(name,args)
        # Exact captured Python result is retained before any clock/query/copy.
        record['raw']=returned;record['return_observed']=True;self.returns[name]+=1
        need(type(returned) is RawReturn,'malformed_API_observation','incomplete_unknown')
        if observe is not None:observe(returned)
        self.origin.check(hard=hard)
        return returned

    def _slot(self,identity):
        found=[s for s in self.slots if s.id==identity];need(len(found)==1,'current_slot_required');return found[0]

    def _new(self,identity,kind,path=None,spec=None):
        need(not any(s.id==identity for s in self.slots),'slot_reuse');need(len(self.slots)<281,'slot_cap')
        slot=Slot(identity,kind,path,spec);self.slots.append(slot);return slot

    def _open_observation(self,slot,raw):
        slot.raw_open=raw;value=raw.value
        if uint(value,INVALID) and value not in (0,INVALID):slot.handle=value;slot.open_state='observed_owned';slot.closer='FindClose' if slot.kind=='file_search' else 'CloseHandle'
        elif type(value) is int and value==INVALID:slot.open_state='known_failure_no_handle'
        else:slot.open_state='malformed_or_return_unknown'

    def _file_identity(self,slot,size):
        self._identities.pop(slot.id,None);self._harness_identities.pop(slot.id,None);slot.identity_ok=False
        h=slot.handle;hard=slot.kind=='output_file'
        raw=self._call('GetFileType',dict(handle=h),hard=hard);slot.identity.append(raw);need(type(raw.value) is int and raw.value==1,'identity')
        raw=self._call('GetFileInformationByHandleEx',dict(handle=h,info_class=9,buffer_bytes=8),hard=hard);slot.identity.append(raw)
        need(raw_BOOL(raw.value) and raw.buffer_defined and type(raw.buffer) is bytes and len(raw.buffer)==8,'identity')
        attrs,tag=struct.unpack('<II',raw.buffer);need(not(attrs&(16|1024)),'identity')
        raw=self._call('GetFinalPathNameByHandleW',dict(handle=h,capacity=4101,flags=0),hard=hard);slot.identity.append(raw)
        need(uint(raw.value) and 0<raw.value<4101 and raw.buffer_defined and type(raw.buffer) is bytes and len(raw.buffer)==8202,'identity')
        n=raw.value;need(raw.buffer[2*n:2*n+2]==b'\0\0','identity')
        try:final=raw.buffer[:2*n].decode('utf-16-le','strict')
        except UnicodeError as error:raise PortError('identity') from error
        if final.startswith('\\\\?\\'):final=final[4:]
        need(path_key(final)==path_key(slot.path),'identity')
        raw=self._call('GetFileSizeEx',dict(handle=h),hard=hard);slot.identity.append(raw)
        need(raw_BOOL(raw.value) and raw.buffer_defined and len(raw.buffer)==8 and struct.unpack('<q',raw.buffer)[0]==size,'identity')
        self._identities[slot.id]=_IdentityWitness(self,self.origin.nonce,slot,slot.handle,slot.path,slot.spec,size,tuple(slot.identity))
        slot.identity_ok=True

    def open_original(self,spec,identity='o0'):
        need(self.namespace_owned and self.reservation_ready,'reservation_not_ready')
        need(type(spec) is FileSpec and self.specs.get(path_key(spec.path)) is spec,'exact_original_roster')
        slot=self._new(identity,'original_file',spec.path,spec)
        self._phase='open_unreturned'
        try:
            raw=self._call('CreateFileW',dict(path=spec.path,desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None),lambda raw:self._open_observation(slot,raw),entered=lambda:setattr(slot,'open_state','entered_return_unknown'))
        except BaseException as error:
            if slot.raw_open is None and slot.open_state!='reserved':slot.open_state='malformed_or_return_unknown'
            if type(error) is PortError and error.kind=='incomplete_deadline':raise PortError('work_deadline','incomplete_deadline') from error
            raise
        need(slot.handle is not None,'open_INVALID' if raw.value==INVALID else 'open_NULL','incomplete_known_failure' if raw.value==INVALID else 'incomplete_unknown')
        self._phase='log';self.hook('log_append');self._phase='identity'
        self._file_identity(slot,spec.size)
        return slot

    def hash_capture(self,identity):
        slot=self._slot(identity);need(slot.kind=='original_file' and slot.spec is not None and slot.close_attempts==0,'live_original_required')
        self._require_identity(slot)
        spec=slot.spec;need(slot.hash is None,'no_hash_retry');slot.hash=_new_hasher()
        while slot.known_bytes<spec.size:
            need(slot.read_attempts<((spec.size+65535)//65536+16),'read_cap')
            requested=min(CHUNK,spec.size-slot.known_bytes);slot.read_attempts+=1;slot.pending_read=True
            def observed(raw):
                slot.raw_reads.append(raw);slot.pending_read=False
                defined=raw_BOOL(raw.value) and raw.raw_count_defined is True and uint(raw.raw_count) and raw.raw_count<=requested
                if defined:slot.known_bytes+=raw.raw_count;self.known_read_bytes+=raw.raw_count
                else:self.read_count_unknown=True
            self._phase='unreturned_read'
            try:raw=self._call('ReadFile',dict(handle=slot.handle,requested=requested,overlapped=None),observed)
            except BaseException as error:
                if slot.pending_read:self.read_count_unknown=True
                if type(error) is PortError and error.kind=='incomplete_deadline':raise PortError('late','incomplete_deadline') from error
                raise
            need(raw_BOOL(raw.value) and raw.raw_count_defined and uint(raw.raw_count) and 0<raw.raw_count<=requested,'failed_count' if not raw_BOOL(raw.value) else 'zero_read','incomplete_unknown' if not raw_BOOL(raw.value) else 'incomplete_known_failure')
            need(raw.buffer_defined and type(raw.buffer) is bytes and len(raw.buffer)>=raw.raw_count,'read_buffer','incomplete_unknown')
            self.origin.check();self._phase='hash';self.hook('hash_update');slot.hash_pending=True;slot.hash.update(raw.buffer[:raw.raw_count]);slot.hash_pending=False
            slot.hashed_bytes+=raw.raw_count;self.hashed_bytes+=raw.raw_count;self.origin.check()
            if spec.capture:
                self._phase='copy';self.hook('copy_bytes');slot.capture.extend(raw.buffer[:raw.raw_count]);slot.captured_bytes+=raw.raw_count;self.captured_bytes+=raw.raw_count;self.origin.check()
        need(slot.hash.hexdigest()==spec.sha256,'hash_mismatch')

    def close_slot(self,identity,requested_closer=None):
        slot=self._slot(identity)
        need(requested_closer is None or requested_closer==slot.closer,'wrong_closer','control_rejected')
        if slot.handle is None or slot.close_attempts:return
        def observed(raw):slot.close_state='returned_success' if raw_BOOL(raw.value) else 'returned_failure'
        def entering():slot.close_attempts=1;slot.close_state='entered_return_unknown'
        self._phase='close_unknown'
        try:raw=self._call(slot.closer,dict(handle=slot.handle),observed,hard=True,entered=entering)
        except BaseException as error:
            if slot.close_attempts==0 and type(error) is PortError and error.kind=='incomplete_deadline':slot.close_state='not_dispatched_deadline'
            raise
        need(raw_BOOL(raw.value),'close_failed')

    def _attributes(self,path):
        need(path_key(path,drive_root=len(path)==3) in self.directories,'undeclared_directory')
        self._phase='root_attributes_unreturned'
        try:raw=self._call('GetFileAttributesExW',dict(path=path,info_level=0,buffer_bytes=36))
        except PortError as error:
            if error.kind=='incomplete_deadline':raise PortError('root_attributes_late','incomplete_deadline') from error
            raise
        need(raw_BOOL(raw.value) and raw.buffer_defined and type(raw.buffer) is bytes and len(raw.buffer)==36,'root_attributes_false','incomplete_unknown')
        attrs,=struct.unpack_from('<I',raw.buffer);need(attrs&16 and not attrs&1024,'directory_or_reparse')

    def inspect_ancestors(self,paths):
        need(type(paths) is tuple and len(paths)<=1024,'ancestor_cap');seen=set()
        for path in paths:
            key=path_key(path,drive_root=len(path)==3)
            if key in seen:continue
            seen.add(key);self._attributes(path)

    def scan(self,path,declared_empty=False):
        path_key(path);self._attributes(path)
        index=sum(s.kind=='file_search' for s in self.slots);slot=self._new('s'+str(index),'file_search',path)
        raw=self._call('FindFirstFileExW',dict(pattern=path+'\\*',info_level=1,search_op=0,search_filter=None,flags=0),lambda raw:self._open_observation(slot,raw),entered=lambda:setattr(slot,'open_state','entered_return_unknown'))
        if slot.handle is None:
            need(raw.value==INVALID and declared_empty is True and raw.error_defined and raw.last_error==2,'initial18_is_not_natural_end')
            return ()
        records=[];dots=0;attempts=0
        while True:
            need(raw.buffer_defined and type(raw.buffer) is bytes and len(raw.buffer)==592,'scan_buffer','incomplete_unknown')
            attrs,=struct.unpack_from('<I',raw.buffer);units=struct.unpack_from('<260H',raw.buffer,44)
            need(0 in units,'scan_unterminated')
            stop=units.index(0)
            try:name=raw.buffer[44:44+2*stop].decode('utf-16-le','strict')
            except UnicodeError as error:raise PortError('scan_unterminated') from error
            if name in ('.','..'):dots+=1;need(dots<=2,'scan_dot_cap')
            else:
                records.append((name,attrs));need(len(records)<=64,'scan_overflow')
                need(not attrs&1024,'scan_reparse');entry_key=path_key('D:\\'+name);need(entry_key in self.entry_types,'scan_extra')
                need(bool(attrs&16)==(self.entry_types[entry_key]=='directory'),'scan_type')
                path_key(path+'\\'+name)
            attempts+=1;need(attempts<=68,'scan_attempt_cap')
            raw=self._call('FindNextFileW',dict(handle=slot.handle,buffer_bytes=592))
            if not raw_BOOL(raw.value):
                need(raw.error_defined and raw.last_error==18,'scan_next_failed','incomplete_unknown');break
        return tuple(records)

    def create_namespace(self,path):
        need(path==self.output,'exact_output_namespace');path_key(path)
        def observed(raw):
            if raw_BOOL(raw.value):self.namespace_owned=True
        raw=self._call('CreateDirectoryW',dict(path=path,security=None),observed,hard=True)
        need(raw_BOOL(raw.value),'namespace_creation_failed')

    def open_output(self,name,identity,handle_size=0):
        need(self.namespace_owned,'unowned_output');need(name in ('reservation.json','journal.jsonl','verification-candidate.json','original-lease-cleanup.json','receipt.json','terminal-seal.json','failure.json','late-failure.json','after-seal-failure.json'),'fixed_output_name')
        path=self.output+'\\'+name;need(not any(s.kind=='output_file' and path_key(s.path)==path_key(path) for s in self.slots),'duplicate_output_path')
        slot=self._new(identity,'output_file',path)
        raw=self._call('CreateFileW',dict(path=path,desired_access=1073741952,share_mode=0,security=None,creation=1,flags=128,template=None),lambda raw:self._open_observation(slot,raw),hard=True,entered=lambda:setattr(slot,'open_state','entered_return_unknown'))
        need(slot.handle is not None,'journal_reservation_failed')
        self._file_identity(slot,handle_size)
        return slot

    def write_record(self,identity,data):
        slot=self._slot(identity);need(slot.kind=='output_file' and slot.handle is not None and slot.close_attempts==0,'owned_output_slot')
        self._require_identity(slot)
        need(type(data) is bytes,'immutable_output_record')
        name=slot.path.rsplit('\\',1)[-1] if slot.path else None
        journal=name=='journal.jsonl'
        small=name in ('reservation.json','failure.json','late-failure.json','after-seal-failure.json')
        cap=8388608 if journal else 8192 if small else 2097152
        need(len(data)<=(65536 if journal else cap) and slot.reserved_bytes+len(data)<=cap,'output_record_cap')
        need(slot.record_count<(self.event_budget if journal else 1),'output_record_retry')
        need(self.reserved_output_bytes+len(data)<=16809984,'output_aggregate_cap')
        slot.record_count+=1;slot.reserved_bytes+=len(data);self.reserved_output_bytes+=len(data);slot.records.append(data)
        if slot.output_hash is None:slot.output_hash=_new_hasher()
        offset=0
        while offset<len(data):
            chunk=data[offset:offset+CHUNK]
            pending=[False]
            def entering():pending[0]=True
            def observed(raw):
                try:defined=raw_BOOL(raw.value) and raw.raw_count_defined is True and uint(raw.raw_count) and raw.raw_count<=len(chunk)
                except BaseException:
                    self.write_count_unknown=True;pending[0]=False;raise
                if defined:self.known_write_bytes+=raw.raw_count;slot.write_offset+=raw.raw_count
                else:self.write_count_unknown=True
                pending[0]=False
            self._phase='unreturned'
            try:raw=self._call('WriteFile',dict(handle=slot.handle,data_hex=chunk.hex(),overlapped=None),observed,hard=True,entered=entering)
            except BaseException:
                if pending[0]:self.write_count_unknown=True
                raise
            need(raw_BOOL(raw.value),'false','incomplete_unknown')
            need(raw.raw_count_defined and uint(raw.raw_count) and 0<raw.raw_count<=len(chunk),'zero')
            self.origin.check(hard=True);self._phase='hash';self.hook('hash_update');slot.hash_pending=True
            slot.output_hash.update(chunk[:raw.raw_count]);slot.hash_pending=False;slot.output_hashed+=raw.raw_count
            self.write_hash_bytes+=raw.raw_count;offset+=raw.raw_count;self.origin.check(hard=True)
        def flushed(raw):
            if raw_BOOL(raw.value):
                self.flushed_known_bytes+=slot.write_offset-slot.output_flushed;slot.output_flushed=slot.write_offset
        self._phase='flush_unknown';raw=self._call('FlushFileBuffers',dict(handle=slot.handle),flushed,hard=True)
        need(raw_BOOL(raw.value),'flush_false')

    def output_pin(self,identity):
        slot=self._slot(identity);self.origin.check(hard=True)
        need(slot.kind=='output_file' and slot.identity_ok and slot.path is not None and slot.close_state=='returned_success' and slot.output_hash is not None and not slot.hash_pending and slot.output_hashed==slot.output_flushed==slot.write_offset==slot.reserved_bytes,'output_pin_incomplete')
        result=dict(path=slot.path,bytes=slot.write_offset,sha256=slot.output_hash.hexdigest());self.origin.check(hard=True)
        return _freeze(result)

    def reserve_namespace(self,path,reservation,first_record):
        parent=path.rsplit('\\',1)[0];self._attributes(parent);self.create_namespace(path);self._attributes(path)
        self.open_output('reservation.json','r0');self.write_record('r0',reservation);self.close_slot('r0')
        self.open_output('journal.jsonl','j0');self.write_record('j0',first_record)
        self.reservation_ready=True;self._composition=True

    def finalize_output(self,identity,data):
        self.write_record(identity,data);self.close_slot(identity);self.origin.check(hard=True)

    def admit_plan(self,q):
        need(type(q) is dict,'plan_shape','admission_rejected')
        for key in ('N','B','M','U','S','E','F','sumRi','sumWj','capture_bytes','report_bytes'):need(uint(q.get(key),2**63-1),'plan_'+key,'admission_rejected')
        need(q['N']<=256,'plan_N','admission_rejected');need(q['B']<=16 and q['B']<=q['N'] and q['M']<=16,'plan_B','admission_rejected');need(q['U']<=1024,'plan_U','admission_rejected')
        need(type(q['Dk']) is list and len(q['Dk'])==2 and all(uint(x,8) for x in q['Dk']) and sum(q['Dk'])==q['S']<=16,'plan_S','admission_rejected')
        E=6*q['N']+2*q['B']+2*q['M']+4*q['S']+161;need(q['E']==E and E<=2048,'plan_E','admission_rejected')
        need(q['capture_bytes']<=67108864,'plan_capture','admission_rejected');need(q['report_bytes']<=2097152,'plan_report','admission_rejected')
        need(type(q['file_byte_sizes']) is list and len(q['file_byte_sizes'])==q['N'] and all(uint(n,2**63-1) for n in q['file_byte_sizes']),'plan_files','admission_rejected')
        Ri=sum((n+65535)//65536+16 if n else 0 for n in q['file_byte_sizes']);need(q['sumRi']==Ri,'plan_read','admission_rejected')
        need(q['F']==9 and q['sumWj']==E+412,'plan_write','admission_rejected')

    def validate_path_syntax(self,path,use):
        """Only the bounded role grammar. Does not mint original-file authority."""
        if len(path)==3 and path[1:]==':\\':
            need(use=='ancestor','root_wrong_role','admission_rejected');return path_key(path,drive_root=True)
        if use=='ancestor' and len(path)<=3:raise PortError('unapproved_root_spelling','admission_rejected')
        need(use in ('ancestor','original','output_file','namespace','scan_root'),'path_role','admission_rejected')
        return path_key(path)

    def validate_handoff(self,*,origin,port,nonce,serialized_ready=None,cached_own_module=False):
        need(port is self.api,'foreign_port','control_rejected');need(nonce is self.origin.nonce and origin is self.origin,'foreign_nonce','control_rejected')
        need(serialized_ready is None,'serialized_ready','control_rejected');need(not self._handoff_claimed,'double_handoff','control_rejected');need(cached_own_module is False,'cached_own_module','control_rejected')
        self._handoff_claimed=True

    def validate_seal_graph(self,nodes,edges,operations):
        need(type(nodes) is tuple and len(nodes)==5 and type(edges) is tuple and len(edges)<=16,'DAG_shape','control_rejected')
        keys=set();names=set()
        for node in nodes:
            need(type(node) is dict and set(node)=={'id','path','bytes','sha256'} and type(node['id']) is str and node['id'] not in names,'DAG_node','control_rejected')
            names.add(node['id']);key=path_key(node['path']);need(key not in keys,'DAG_same_path','control_rejected');keys.add(key)
            need(uint(node['bytes'],2097152) and type(node['sha256']) is str and HEX.fullmatch(node['sha256']),'DAG_pin','control_rejected')
        graph={name:[] for name in names}
        for source,target in edges:
            need(source in graph and target in graph and source!=target,'DAG_self_hash','control_rejected');graph[source].append(target)
        def visit(node,trail):
            need(node not in trail,'DAG_cycle','control_rejected')
            for dep in graph[node]:visit(dep,trail+(node,))
        for name in graph:visit(name,())
        need(type(operations) is tuple and len(operations)<=16 and all(type(op) is dict and op.get('state')=='returned_success' for op in operations),'DAG_unknown_veto','control_rejected')

    def run(self,action):
        need(not self._finished,'owner_consumed')
        try:action(self)
        except BaseException as error:self._latch(error)
        finally:
            for slot in reversed(self.slots):
                if slot.handle is None or slot.close_attempts:continue
                try:self.close_slot(slot.id)
                except BaseException as error:
                    if slot.close_state=='not_dispatched_deadline' and self.primary is not None:continue
                    self._latch(error,'close_unknown' if slot.close_state=='entered_return_unknown' else 'close_failed')
            self._finished=True
        return self.observe()

    def observe(self):
        return Observation(_freeze(dict(disposition=self.disposition if self.primary else 'primitive_composition_complete' if self._composition else 'primitive_complete',
            namespace_owned=self.namespace_owned,reservation_ready=self.reservation_ready,known_read_bytes=self.known_read_bytes,hashed_bytes=self.hashed_bytes,captured_bytes=self.captured_bytes,
            read_count_unknown=self.read_count_unknown,known_write_bytes=self.known_write_bytes,write_hash_bytes=self.write_hash_bytes,flushed_known_bytes=self.flushed_known_bytes,write_count_unknown=self.write_count_unknown,
            slots=[s.projection() for s in self.slots],primary=self.primary,secondary=list(self.secondary),terminal_ack=False,journal_recursive_events=0,api_attempts=dict(self.attempts),api_returns=dict(self.returns),
            profile_qualified=False,runtime_authorized=False,originals_authenticated=False,test_seeded=self._test_seeded,harness_identity_assumptions=len(self._harness_identities),FFI_registration_proven=False,production_owner_bound=False)))
