"""Non-owning seven-operation injected original-file view; NO real FFI."""
from dataclasses import dataclass
import hashlib
import struct
from shared_owner_v3 import (SharedOwner,SharedOwnerError,FileSpec,FileRecordRef,CallRef,CallState,UNOBSERVED,INVALID,APIS,uint,signed_bool,usable,path_key,sha)

FRAMES={'GetFileInformationByHandleEx':8,'GetFinalPathNameByHandleW':8202,'GetFileSizeEx':8}

class AdoptionHooks:
    def __init__(self,owner):self.owner=owner
    def _state(self,ref):
        o=self.owner;o._active();o.require(type(ref) is CallRef and ref._state.owner is o,'FOREIGN_IDENTITY');c=ref._state;o.require(uint(c.ordinal,len(o.registry._calls)-1) and o.registry._calls[c.ordinal] is c,'FOREIGN_IDENTITY');o.require(c.invoked and not c.stopped,'INVALID_INPUT');return c
    def store_scalar(self,ref,value):
        c=self._state(ref);o=self.owner
        valid=value is None or uint(value,INVALID) if c.api=='CreateFileW' else uint(value,2**32-1) if c.api in ('GetFileType','GetFinalPathNameByHandleW') else signed_bool(value)
        o.require(valid and (c.scalar is UNOBSERVED or type(c.scalar) is type(value) and c.scalar==value),'INVALID_INPUT')
        try:
            if c.scalar is UNOBSERVED:c.scalar=value
            if c.api=='ReadFile':o._fold_read_fact(c)
            if c.api=='CreateFileW':c.file.open_state='owned' if usable(value) else 'known_failure_no_handle' if value==INVALID else 'ownership_unknown'
            elif c.api=='CloseHandle':c.file.close_state='returned_success' if value!=0 else 'returned_failure'
        except BaseException as error:o._accounting_failed(c,error,'after_scalar_before_aux');raise
    def store_count(self,ref,value):
        c=self._state(ref);self.owner.require(c.api=='ReadFile' and uint(value,2**32-1) and (c.count is UNOBSERVED or c.count==value),'INVALID_INPUT')
        try:
            if c.count is UNOBSERVED:c.count=value
            self.owner._fold_read_fact(c)
        except BaseException as error:self.owner._accounting_failed(c,error,'after_count_before_aux');raise
    def store_error(self,ref,value,defined):
        c=self._state(ref);o=self.owner;o.require(c.scalar is not UNOBSERVED and uint(value,2**32-1) and type(defined) is bool,'INVALID_INPUT')
        failed=c.scalar in (0,INVALID,None) if c.api=='CreateFileW' else c.scalar==0
        o.require(not defined or failed,'INVALID_INPUT');o.require(c.error is UNOBSERVED or c.error==value and c.error_defined is defined,'INVALID_INPUT');c.error=value;c.error_defined=defined
    def buffer_write(self,ref,buffer_ref,generation,data):
        c=self._state(ref);o=self.owner;o.require(c.buffer is not None and buffer_ref is c.buffer and uint(generation,68) and generation==c.generation==buffer_ref._generation and type(data) is bytes,'FOREIGN_IDENTITY')
        o.require(c.scalar is UNOBSERVED and len(data)<=buffer_ref.capacity,'INVALID_INPUT')
        if c.api in FRAMES:o.require(len(data)==FRAMES[c.api],'INVALID_INPUT')
        else:o.require(c.api=='ReadFile' and len(data)<=c.requested,'INVALID_INPUT')
        buffer_ref._data[:len(data)]=data;object.__setattr__(buffer_ref,'_written',len(data));c.buffer_written=len(data);c.buffer_state='raw_retained'
    def aux(self,ref,field):
        c=self._state(ref);self.owner.require(field in ('scalar_aux_ack','count_aux_ack','right_transfer_ack'),'INVALID_INPUT');setattr(c,field,True)
    def raise_exception(self,ref,error,phase):
        c=self._state(ref);o=self.owner;o.require(isinstance(error,BaseException) and type(phase) is str,'INVALID_INPUT');c.stopped=True
        if not c.wrapper_return:c.wrapper_state='raised'
        o.record_error(error,phase)

@dataclass(frozen=True,eq=False)
class FilePortView:
    owner:object
    injected_binding:object
    def __post_init__(self):
        if type(self.owner) is not SharedOwner or not callable(getattr(self.injected_binding,'invoke',None)):raise SharedOwnerError('INVALID_INPUT')
    def _file(self,ref):return self.owner.file_state(ref)
    def _call(self,api,file,args,requested=None):
        o=self.owner;o._active();cleanup=api=='CloseHandle';o.check(cleanup)
        o.require(o.port is self and api in APIS and o._plan is not None,'FOREIGN_IDENTITY');o.require(o.primary is None or cleanup,'INVALID_INPUT')
        o.require(len(o.registry._calls)<o._plan['C'],'JOINT_CAP_EXCEEDED')
        if api=='ReadFile':
            o.require(file._read_reservations<((file.spec.size+65535)//65536+16 if file.spec.size else 0),'JOINT_CAP_EXCEEDED')
        buf=o._read_buffer if api=='ReadFile' else o._query_buffer if api in FRAMES else None
        c=CallState(o,len(o.registry._calls),api,file,requested,buf)
        try:
            o.registry._calls.append(c);o._index_reserved_call(c)
        except BaseException as error:o._accounting_failed(c,error,'pre_dispatch');raise
        c.invoked=True
        if api in ('GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx'):file.identity_queries.append(c.ordinal)
        if api=='CreateFileW':file.open_state='entered_return_unknown'
        if cleanup:file.close_state='entered_return_unknown'
        hooks=AdoptionHooks(o)
        try:
            self.injected_binding.invoke(c.ref,args,hooks)
            c.wrapper_return=True;c.wrapper_state='returned'
            o.check(cleanup);o.require(c.scalar is not UNOBSERVED,'RAW_RETURN_UNKNOWN')
            if c.stopped or o.primary is not None and not cleanup:raise o.primary or SharedOwnerError('RAW_RETURN_UNKNOWN')
            if api in FRAMES:
                o.require(c.buffer_written==FRAMES[api],'IDENTITY_INCOMPLETE');o.charge_raw(FRAMES[api]);c.query_bytes=bytes(bytearray(buf._data[:FRAMES[api]]));c.buffer_state='defined';object.__setattr__(buf,'_generation',buf._generation+1)
            return c
        except BaseException as error:
            c.stopped=True
            if not c.wrapper_return:c.wrapper_state='raised'
            o.record_error(error,'original_close' if cleanup else 'binding_invoke');raise
    def acquire(self,spec):
        o=self.owner;o._active();o.check();o.require(o._owned and o.port is self and type(spec) is FileSpec and any(s is spec or s==spec for s in o._specs),'FOREIGN_IDENTITY')
        file=o.registry._file_by_exact_path[spec.path];o.require(file.open_state=='unopened','INVALID_INPUT')
        prefix='source' if file.early else 'file';o.emit(prefix+'_open_reserved',{'file_id':file.id})
        c=self._call('CreateFileW',file,dict(path=spec.path,desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None))
        o.require(usable(c.scalar),'RAW_RETURN_UNKNOWN');o.emit(prefix+'_open_returned',{'file_id':file.id});return file.ref
    def inspect(self,ref):
        o=self.owner;o._active();file=self._file(ref);o.check();o.require(o.port is self and usable(o.handle(file)) and not file.close_reserved and file.identity_state=='not_attempted','IDENTITY_INCOMPLETE')
        file.identity_state='in_progress';handle=o.handle(file)
        if file.early:o.emit('source_identity_reserved',{'file_id':file.id})
        try:
            values=[]
            for api,args in [('GetFileType',dict(handle=handle)),('GetFileInformationByHandleEx',dict(handle=handle,info_class=9,buffer_bytes=8)),('GetFinalPathNameByHandleW',dict(handle=handle,capacity=4101,flags=0)),('GetFileSizeEx',dict(handle=handle))]:
                c=self._call(api,file,args);values.append(c);o.check()
            typ,attrs,path,size=values;o.require(type(typ.scalar) is int and typ.scalar==1,'IDENTITY_INCOMPLETE')
            o.require(attrs.scalar!=0 and attrs.query_bytes is not None,'IDENTITY_INCOMPLETE');a,tag=struct.unpack('<II',attrs.query_bytes);o.require(not a&(16|1024),'IDENTITY_INCOMPLETE')
            n=path.scalar;o.require(uint(n,4100) and n>0 and path.query_bytes[2*n:2*n+2]==b'\0\0','IDENTITY_INCOMPLETE')
            text=path.query_bytes[:2*n].decode('utf-16-le','strict')
            if text.startswith('\\\\?\\'):text=text[4:]
            o.require(path_key(text)==path_key(file.spec.path),'IDENTITY_INCOMPLETE');o.require(size.scalar!=0 and struct.unpack('<q',size.query_bytes)[0]==file.spec.size,'IDENTITY_INCOMPLETE')
            o.check();file.identity_witness=(o,o.nonce,file.ref,handle,tuple(values));file.identity_state='verified'
            if file.early:o.emit('source_identity_returned',{'file_id':file.id})
        except BaseException as error:file.identity_state='unknown' if file.identity_state!='refused' else 'refused';o.record_error(error,'identity_query');raise
    def hash_capture(self,ref):
        o=self.owner;o._active();file=self._file(ref);o.check();w=file.identity_witness
        o.require(w is not None and w[0] is o and w[1] is o.nonce and w[2] is ref and w[3]==o.handle(file) and not file.close_reserved and not file.hash_attempted,'IDENTITY_INCOMPLETE');file.hash_attempted=True;file.hasher=hashlib.sha256()
        prefix='source' if file.early else 'file';o.emit(prefix+'_hash_reserved',{'file_id':file.id})
        try:
            while o.read_known(file)<file.spec.size:
                o.check();n=min(65536,file.spec.size-o.read_known(file));c=self._call('ReadFile',file,dict(handle=o.handle(file),requested=n,overlapped=None),n)
                o.require(o.defined(c),'READ_COUNT_UNKNOWN');o.require(c.count>0 and c.buffer_written>=c.count,'READ_PROGRESS_INCOMPLETE')
                o.check();o.hook('hash_update',c.ref);file.hasher.update(c.buffer._data[:c.count]);file.hashed+=c.count;o.check()
                o.hook('copy_bytes',c.ref);offset=file.captured;file.assembly[offset:offset+c.count]=c.buffer._data[:c.count];file.captured+=c.count;o.check();object.__setattr__(c.buffer,'_generation',c.buffer._generation+1)
            digest=file.hasher.hexdigest();file.actual_sha=digest;o.check();o.require(digest==file.spec.sha256,'INVALID_INPUT');o.require(o._capture_used+file.spec.size<=16384,'JOINT_CAP_EXCEEDED')
            blob=bytes(file.assembly);o._capture_used+=len(blob);file.blob=blob;file.hash_complete=True;file.capture_complete=True;o.emit(prefix+'_hash_returned',{'file_id':file.id});return blob
        except BaseException as error:
            if 'c' in locals():c.stopped=True
            o.record_error(error,'hash_update');raise
    def close(self,ref):
        o=self.owner;o._active();file=self._file(ref);o.require(o.port is self,'FOREIGN_IDENTITY');o.require(not file.close_reserved,'INVALID_INPUT')
        if not usable(o.handle(file)):return
        try:o.check(cleanup=True)
        except BaseException:file.close_state='not_dispatched_deadline';raise
        file.close_reserved=True;file.close_state='reserved'
        try:o.emit('original_close_reserved',{'file_id':file.id},cleanup=True)
        except BaseException:pass
        try:
            c=self._call('CloseHandle',file,dict(handle=o.handle(file)));o.require(c.scalar!=0,'INVALID_INPUT')
        finally:
            try:o.emit('original_close_returned_or_unknown',{'file_id':file.id},cleanup=True)
            except BaseException:pass
