"""One separately authorized, generated 216-file SOURCE/PURE lifecycle.

CODE PREPARATION ONLY. No work occurs merely by importing this harness.
No historical payload is read. The pinned reference supplies size VALUES and
invented-prefix hashes. All injected paths are fictional. Evidence persistence
below is trusted harness output AFTER the subject stack has unwound; it is not
the producer's unqualified physical publication implementation.
"""
import argparse
import builtins
import dataclasses
import encodings.utf_16_le
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
import traceback
import types

HERE=Path(__file__).resolve().parent
MODULES=('role_ledger_codec_v4','role_owner_v4','role_file_ports_v4','continue_role_verification_v4')
PAUSE_SHA='a746e552d5fb6a2eef7c80d5a593a9f4a5a606456d4fae63acfb8905cb14e929'
REFERENCE_SHA='1a3e47ec28b1f96c4ac0d5c9c9eb7c2f13288cf5a6df4e3c4f6853d07a56aa03'
ADAPTER_SHA='b0f8cbf326f05c9b868b26fbac2eaee5bdd9ae78fdcc15d1da848d2822abff4f'
CHUNK=1048576
N=216
Q=8799
R=12255
C=13551
E=1496
WORK_CALLS=9879
ALL_CALLS=10095
TOTAL=9017363601
QUERY_BYTES=1775088
SEED=bytes(range(256))
API=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
OUTKEY='fictional_role_aware_large_v1'
# 64 bytes per independent observation, allocated to admitted C, not bulk size.
# ordinal,file,API,requested,count,scalar,entry,prepared,generation,flags,handle.
# Flags1/2/4/8 = entered/scalar hook completed/count hook completed/return PREPARED.
# Canonical raw assignment is separate: a hook can first-store then raise.
# Actual portable return is independently observed in canonical c.wrapper_return.
SPY_ROW=struct.Struct('<IHHQQQddIIQ')
QUAL={k:False for k in ('real_entry','real_FFI','physical_IO','full_real_roster','new84_runtime','resource_fit','scientific')}


class HarnessError(RuntimeError):pass


def require(ok,message):
    if not ok:raise HarnessError(message)


def same(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if type(a) in (tuple,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if type(a) is float:return struct.pack('<d',a)==struct.pack('<d',b)
    return a==b


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()


def checked(pin):
    require(type(pin) is dict and set(pin)=={'path','bytes','sha256'},'exact pin shape')
    raw=Path(pin['path']).read_bytes()
    require(type(pin['bytes']) is int and len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'input pin changed')
    return raw


def pin(path):
    raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class EntryClock:
    """Adopt ONE actual entry sample; subsequent calls are current monotonic."""
    def __init__(self,entry):self.entry=entry;self.calls=0
    def __call__(self):
        self.calls+=1
        return self.entry if self.calls==1 else time.monotonic()


def expected_sequence(descriptors):
    """Independent causal order, not read from canonical source CallState."""
    generation=0
    for d in descriptors:
        i=d['file_id'];handle=1000+i
        for api in API[:5]:yield i,api,0,0,handle
        remaining=d['size']
        while remaining:
            n=min(CHUNK,remaining)
            yield i,'ReadFile',n,generation,handle
            remaining-=n;generation+=1
    for d in reversed(descriptors):yield d['file_id'],'CloseHandle',0,0,1000+d['file_id']


def query_frame(d,api):
    if api=='GetFileInformationByHandleEx':return struct.pack('<II',0x80,0)
    if api=='GetFileSizeEx':return struct.pack('<q',d['size'])
    require(api=='GetFinalPathNameByHandleW','query API')
    raw=('\\\\?\\'+d['path']).encode('utf-16-le')+b'\0\0'
    require(len(raw)<=8202,'invented path frame cap')
    return raw+bytes(8202-len(raw))


class VirtualBinding:
    def __init__(self,world):
        self.w=world;self.log=bytearray(C*SPY_ROW.size);self.refs=[None]*C;self.count=0
        self.delivered=[0]*N;self.close_counts=[0]*N;self.opens=[False]*N
        self.reads=0;self.read_buffer=None;self.query_buffer=None;self.expected=iter(expected_sequence(world.descriptors))
        self.overflow_attempts=0;self.open_ordinals=[None]*N
    def row(self,i):return SPY_ROW.unpack_from(self.log,i*SPY_ROW.size)
    def invoke(self,ref,args,hooks):
        w=self.w;entry=time.monotonic();j=self.count;self.count+=1
        if j>=C:
            self.overflow_attempts+=1;w.fail('spy capacity exceeded by actual dispatch')
        self.refs[j]=ref
        i=ref.file_ref.id;api=ref.api;aid=API.index(api)+1 if api in API else 0
        # Record attempted dispatch BEFORE any guard, including forbidden work.
        ordinal=ref.ordinal
        raw_ordinal=ordinal if type(ordinal)is int and 0<=ordinal<(1<<32) else (1<<32)-1
        SPY_ROW.pack_into(self.log,j*64,raw_ordinal,i if type(i)is int and 0<=i<65536 else 65535,aid,0,0,0,entry,0.,0,1,0)
        if api=='CloseHandle':
            # A real failed prefix still owns its actually observed handles.
            # Legal cleanup must not be suppressed by the positive work oracle.
            owned=[k for k in range(N-1,-1,-1) if self.opens[k] and not self.close_counts[k]]
            require(owned and self.w.owner._finishing,'closer outside actual finalization')
            require(self.w.owner.primary is not None or all(self.delivered[k]==d['size'] for k,d in enumerate(w.descriptors)),'early close outside known failed prefix')
            ei,ea,requested,generation,handle=owned[0],api,0,0,1000+owned[0]
        else:ei,ea,requested,generation,handle=next(self.expected)
        require(type(i)is int and i==ei and api==ea,'independent complete dispatch order')
        require(type(ordinal)is int and j<=ordinal<C and (ordinal==j or api=='CloseHandle' and w.owner.primary is not None),'canonical ordinal including failed uninvoked reservations')
        w.deadline(cleanup=api=='CloseHandle',where='binding entry')
        require(w.owner.primary is None or api=='CloseHandle','fresh dispatch after failed prefix')
        require(ref.file_ref is w.file_refs[i] and w.owner.origin is w.original_origin,'canonical file/origin changed')
        d=w.descriptors[i]
        expected={
            'CreateFileW':dict(path=d['path'],desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None),
            'GetFileType':dict(handle=handle),
            'GetFileInformationByHandleEx':dict(handle=handle,info_class=9,buffer_bytes=8),
            'GetFinalPathNameByHandleW':dict(handle=handle,capacity=4101,flags=0),
            'GetFileSizeEx':dict(handle=handle),
            'ReadFile':dict(handle=handle,requested=min(CHUNK,d['size']-self.delivered[i]),overlapped=None),
            'CloseHandle':dict(handle=handle)}[api]
        require(same(args,expected),'full original arguments differ from independent recipe')
        require(api!='ReadFile' or requested==expected['requested']==ref.requested,'independent remaining-byte request')
        scalar=count=0;flags=1
        SPY_ROW.pack_into(self.log,j*64,ordinal,i,aid,requested,0,0,entry,0.,generation,flags,handle)
        if api=='CreateFileW':
            require(not self.opens[i],'duplicate open');self.opens[i]=True;self.open_ordinals[i]=j;scalar=handle
        elif api=='CloseHandle':
            require(self.opens[i] and self.close_counts[i]==0,'guessed or repeated closer');self.close_counts[i]+=1;scalar=1
        elif api=='ReadFile':
            require(self.reads==generation==ref.buffer_generation,'shared read generation')
            if self.read_buffer is None:self.read_buffer=ref.buffer_ref
            require(ref.buffer_ref is self.read_buffer and ref.buffer_ref.capacity==CHUNK,'read buffer replaced')
            if d['capture']:
                raw=w.tiny[i];offset=self.delivered[i]
                hooks.buffer_write_slice(ref,ref.buffer_ref,generation,0,raw[offset:offset+requested])
            else:
                require(self.delivered[i]%256==0,'periodic chunk phase')
                n=min(256,requested);hooks.buffer_write_slice(ref,ref.buffer_ref,generation,0,SEED[:n]);written=n
                while written<requested:
                    w.deadline(where='periodic buffer fill')
                    n=min(written,requested-written);hooks.buffer_copy_within(ref,ref.buffer_ref,generation,0,n);written+=n
            scalar=1;count=requested
        elif api in API[2:5]:
            if self.query_buffer is None:self.query_buffer=ref.buffer_ref
            require(ref.buffer_ref is self.query_buffer and ref.buffer_ref.capacity==8202,'query buffer replaced')
            frame=query_frame(d,api)
            hooks.buffer_write_slice(ref,ref.buffer_ref,ref.buffer_generation,0,frame)
            scalar=len(('\\\\?\\'+d['path']).encode('utf-16-le'))//2 if api=='GetFinalPathNameByHandleW' else 1
        else:scalar=1
        hooks.store_scalar(ref,scalar);flags|=2
        SPY_ROW.pack_into(self.log,j*64,ordinal,i,aid,requested,count,scalar,entry,0.,generation,flags,handle)
        if api=='ReadFile':
            hooks.store_count(ref,count);flags|=4;self.delivered[i]+=count;self.reads+=1
        w.deadline(cleanup=api=='CloseHandle',where='binding return')
        end=time.monotonic();flags|=8
        SPY_ROW.pack_into(self.log,j*64,ordinal,i,aid,requested,count,scalar,entry,end,generation,flags,handle)
        return None


class Sink:
    """Fictional callbacks: exact bytes retained by reference, no file output."""
    def __init__(self,w):
        self.w=w;self.owned=False;self.consumed=False;self.sealed=False;self.reserve_calls=0
        self.counts={k:0 for k in ('candidate','cleanup','failure','receipt','seal')}
        self.callbacks=[];self.journal=[];self.packets={};self.artifacts={};self.consumption=[]
    def enter(self,target,hard):
        now=time.monotonic();self.callbacks.append(dict(target=target,entry=now,return_prepared=False,ack_supplied=False))
        require(type(hard)is float and hard==self.w.entry+300,'sink original hard clock')
        self.w.deadline(cleanup=True,where='sink '+target)
        require(not self.sealed,'dispatch after seal');return self.callbacks[-1]
    def finish(self,row,ack):
        self.w.deadline(cleanup=True,where='sink callback return')
        row['return_prepared']=True;row['ack_supplied']=True;row['prepared_at']=time.monotonic()
        return ack
    def reserve(self,key,ack,hard):
        row=self.enter('reserve',hard);self.reserve_calls+=1
        require(key==OUTKEY and self.reserve_calls==1,'output reservation identity/once')
        self.owned=True;return self.finish(row,ack)
    def append(self,raw,ack,hard):
        row=self.enter('append',hard)
        row['sequence']=len(self.journal)
        require(self.owned and not self.consumed and type(raw)is bytes and len(raw)<=1024,'journal state/type/bound')
        value=json.loads(raw)
        require(set(value)=={'sequence','event','stage','kind','file_id','module','elapsed'} and canonical(value)==raw,'journal exact canonical shape')
        require(type(value['sequence'])is int and value['sequence']==len(self.journal)<E,'journal contiguous reservation')
        require(type(value['elapsed'])is float and 0<=value['elapsed']<300,'journal elapsed')
        self.journal.append(raw) # Alias the producer's actual row bytes, no hex.
        return self.finish(row,ack)
    def publish(self,kind,raw,ack,hard):
        row=self.enter('publish_'+kind,hard)
        require(self.owned and kind in self.counts and self.counts[kind]==0,'publication ownership/kind/once')
        self.counts[kind]+=1
        require(type(raw)is bytes and len(raw)<=8192,'packet byte cap')
        value=json.loads(raw)
        require(set(value)=={'schema_version','kind','scope','status','elapsed','totals','gates','ledger_refs','links','diagnostic_counts','qualification'} and canonical(value)==raw,'packet exact canonical bytes')
        require(type(value['schema_version'])is int and value['schema_version']==2 and value['kind']==kind and value['scope']=='role_aware_producer_format_v1','packet source format')
        require(value['status'] in ('OBSERVED_COMPLETE','OBSERVED_NEGATIVE','INCOMPLETE'),'packet status')
        require(set(value['qualification'])=={'originals','real_entry','real_FFI','physical_IO','new84_runtime','resource_fit','scientific'} and all(v is False for v in value['qualification'].values()),'packet false qualification')
        self.packets[kind]=raw
        if kind in ('candidate','cleanup'):
            name='candidate-ledger.bin' if kind=='candidate' else 'terminal-ledger.bin'
            artifact=self.w.owner.generated_artifact(name)
            # Save first issued exact evidence BEFORE a checker could fail.
            self.artifacts[name]=artifact
            require(artifact.raw is self.w.owner.generated_bytes(name),'cached generated bytes identity')
            require(artifact.owner is self.w.owner and artifact.origin is self.w.original_origin and artifact.nonce is self.w.nonce and artifact.registry is self.w.registry,'genuine artifact issuer identities')
            self.consumption.append(self.w.consume(artifact))
            require(self.w.owner.check_generated(artifact) is artifact,'actual live checker identity')
        if kind in ('receipt','seal'):require(self.consumed,'receipt/seal before consumed journal close')
        if kind=='seal':self.sealed=True
        return self.finish(row,ack)
    def close_journal(self,ack,hard):
        row=self.enter('close_journal',hard);require(self.owned and not self.consumed,'journal close once')
        self.consumed=True;return self.finish(row,ack)


FILE_FIELDS=('ordinal','role','capture_state','target_class','open_state','identity_state','close_state','flags','descriptor_id','path_offset','path_bytes','path_utf16_units','expected_size','expected_sha256','actual_sha256','open_ordinal','close_ordinal','known_read_bytes','hashed_bytes','captured_bytes','query_offset','query_length','first_diagnostic','read_reservations','read_invocations','captured_blob_length','early_ordinal','path_id','read_generation','module_ordinal')
CALL_FIELDS=('ordinal','file_id','api','record_version','flags','requested','buffer_id','phase','generation','buffer_written','scalar_atom','count_atom','error_atom','error_definition_atom','hashed_contribution','captured_contribution','known_count_contribution','query_offset','query_length','input_handle_atom','pre_dispatch_clock','post_binding_clock','error_id','path_id','fold_state','buffer_state')
MODULE_FIELDS=('ordinal','file_ordinal','flags','dependency_count','name_offset','name_length','edge_offset','first_diagnostic','attempt_order','return_order','cache_hit_count')
FILE_FLAGS=('EXPECTED_DIGEST_PRESENT','ACTUAL_DIGEST_PRESENT','CAPTURE_REQUESTED','HASH_ATTEMPTED','HASH_COMPLETE','CAPTURE_COMPLETE','READ_UNKNOWN','HASH_UNKNOWN','COPY_UNKNOWN','CLOSE_RESERVED','EARLY','CLOSE_SUCCESS_KNOWN','CLOSE_SUCCESS_TRUE','ASSEMBLY_RETAINED','BLOB_ISSUED','EXPECTED_SIZE_PRESENT')
CALL_FLAGS=('INVOKED','SCALAR_OBSERVED','SCALAR_NULL','COUNT_OBSERVED','COUNT_DEFINED','ERROR_OBSERVED','ERROR_DEFINED','ERROR_DEFINITION_OBSERVED','SCALAR_AUX_ACK','COUNT_AUX_ACK','RIGHT_TRANSFER_ACK','WRAPPER_RETURNED','STOPPED','QUERY_CAPTURE_OBSERVED','QUERY_DEFINED','BUFFER_DATA_OBSERVED','ACCOUNTING_FAULT','CLOSE_RIGHT_CONSUMED','IDENTITY_VERIFIED_AT_DISPATCH','SCALAR_DOMAIN_VALID','COUNT_DOMAIN_VALID','ERROR_DOMAIN_VALID','PRE_CLOCK_ATTEMPTED','POST_CLOCK_ATTEMPTED','PRE_CLOCK_RETURN_OBSERVED','POST_CLOCK_RETURN_OBSERVED','HASH_ATTEMPTED','HASH_RETURN_OBSERVED','COPY_ATTEMPTED','COPY_RETURN_OBSERVED','CAPTURE_REQUESTED','MALFORMED_RAW','INPUT_HANDLE_PRESENT','REQUESTED_PRESENT','BUFFER_PRESENT','QUERY_SPAN_PRESENT')


def flags(names,true):return {name:name in true for name in names}
def atom(tag,value):return dict(tag=tag,value=value)


class World:
    def __init__(self,D,modules,reference,entry):
        self.D=D;self.L,self.S,self.P,self.C=(modules[n] for n in MODULES)
        self.entry=entry;self.clock=EntryClock(entry);self.descriptors=reference['descriptors']
        self.tiny={d['file_id']:bytes.fromhex(d['utf8_hex']) for d in self.descriptors[:3]}
        self.owner=None;self.binding=None;self.sink=None;self.view=None;self.violations=[];self.file_refs=[];self.states=[];self.token=self.continuation=None;self.checker_calls=[]
        self.consumer_partial=[];self.compile_records=[];self.identities=None
        self.open_ordinals=[];self.read_bases=[];at=reads=0
        for d in self.descriptors:
            self.open_ordinals.append(at);self.read_bases.append(reads)
            q=d['size']//CHUNK+int(d['size']%CHUNK!=0);reads+=q;at+=5+q
        require((at,reads)==(WORK_CALLS,Q),'independent call geometry')
    def fail(self,message):
        self.violations.append(dict(message=message,elapsed=time.monotonic()-self.entry))
        raise HarnessError(message)
    def deadline(self,cleanup=False,where='work'):
        if time.monotonic()>=self.entry+(300 if cleanup else 295):self.fail('original deadline at '+where)
    def setup(self,owner):
        self.owner=owner;self.original_origin=owner.origin;self.nonce=owner.nonce;self.registry=owner.registry;self.loader=owner.loader;self.journal=owner.journal
        require((owner.origin.start,owner.origin.work_end,owner.origin.hard_end)==(self.entry,self.entry+295,self.entry+300),'first actual entry sample not adopted exactly')
        self.specs=tuple(self.S.FileSpec(d['path'],d['role'],d['size'],d['sha256'],d['capture'],descriptor_id=d['file_id']) for d in self.descriptors)
        self.rules=(self.S.ModuleRule('cohort_leaf',self.descriptors[0]['path'],(),False),self.S.ModuleRule('cohort_entry',self.descriptors[1]['path'],('cohort_leaf',),False))
        self.binding=VirtualBinding(self);self.sink=Sink(self);self.view=self.P.FilePortView(owner,self.binding)
        owner.bind_ports(self.view,self.sink);owner.bind_test_compiler(self.compiler,stdlib=())
        self.identities=(owner,self.original_origin,self.nonce,self.registry,self.view,self.sink,self.loader,self.journal)
        return owner
    def compiler(self,name,raw,resolver):
        self.deadline(where='captured compiler')
        i={'cohort_leaf':0,'cohort_entry':1}[name]
        require(raw is self.owner.early_context.bytes_for(self.descriptors[i]['path']) and raw==self.tiny[i],'real captured compiler bytes')
        record=dict(name=name,size=len(raw),actual_compile_entered=True,return_prepared=False)
        self.compile_records.append(record)
        module=types.ModuleType(name)
        def closed_import(fullname,globals=None,locals=None,fromlist=(),level=0):
            require(name=='cohort_entry' and fullname=='cohort_leaf' and level==0,'toy closed dependency only')
            return resolver(fullname,level)
        module.__dict__['__builtins__']=dict(vars(builtins),__import__=closed_import)
        exec(compile(raw,'<invented captured '+name+'>','exec'),module.__dict__)
        self.deadline(where='captured compiler return');record['return_prepared']=True;return module
    def handler(self,stage):
        def observe(context):
            self.deadline(where='synthetic checker '+stage)
            require(context is self.owner.evidence_context and context.owner is self.owner and context.nonce is self.nonce,'actual checker context identity')
            self.checker_calls.append(stage)
            return self.C.TestObservation(context,stage,'consistent',(self.descriptors[2]['path'],),'SYNTHETIC_ONLY engineering control; no real checker')
        return observe
    def run(self):
        D=self.D;D.invoke(self.S.start_injected,self.clock,self.setup,profile=self.S.PROFILE_ORIGINAL7_1M)
        self.deadline(where='post bootstrap');D.invoke(self.owner.admit_plan,self.specs,tuple(d['path'] for d in self.descriptors[:2]),self.rules)
        for d in self.descriptors:
            ref=D.invoke(self.owner.file_ref,d['path']);self.file_refs.append(ref);self.states.append(D.invoke(self.owner.file_state,ref))
        D.invoke(self.owner.reserve_output,OUTKEY);D.invoke(self.owner.capture_early)
        self.early=self.owner.early_context
        self.token=D.invoke(self.owner.issue_continuation);self.continuation=D.invoke(self.token.claim)
        require(self.continuation.owner is self.owner,'same owner continuation')
        loaded=D.invoke(self.owner.load_source,'cohort_entry');D.invoke(self.owner.check)
        require(D.invoke(loaded.run)==('cohort-entry-v1','cohort-leaf-v1'),'actual 141B helper functions')
        D.invoke(self.owner.check)
        ids=tuple((stage,'toy_'+stage) for stage in ('archive','journal','resources','core'))
        factories=self.C.test_factories(self.owner,lambda:self.C.TestAuthority(self.owner,self.specs,ids),lambda:self.C.TestCheckerPorts(self.owner,ids,tuple(self.handler(stage) for stage,_ in ids)))
        return D.invoke(self.C.continue_once,self.continuation,self.C.Request(OUTKEY,self.specs),*factories)
    def consume(self,artifact):
        """Visit ALL real rows/pools and compare independent expected values."""
        terminal=artifact.phase=='TERMINAL';expected_calls=ALL_CALLS if terminal else WORK_CALLS
        counts={k:0 for k in ('header','files','calls','modules','module_edges','diagnostics','queries','paths','module_names')}
        state=dict(kind=artifact.kind,counts=counts,pool_bytes={},complete=False,elapsed_start=time.monotonic()-self.entry)
        self.consumer_partial.append(state)
        require(type(artifact.raw)is bytes and 4096<=len(artifact.raw)<=14800384,'bounded complete ledger bytes')
        require(hashlib.sha256(artifact.raw).hexdigest()==artifact.sha256,'actual immutable ledger digest')
        expected=iter(expected_sequence(self.descriptors));pathoff=0
        for kind,index,value in self.L.iter_checked_records(artifact.raw,check=lambda:self.deadline(cleanup=True,where='independent full consumer')):
            self.deadline(cleanup=True,where='consumer row');counts[kind]+=1
            if kind=='header':
                self.check_header(value,terminal,expected_calls,artifact.raw)
            elif kind=='files':
                d=self.descriptors[index];size=d['size'];q=size//CHUNK+int(size%CHUNK!=0)
                true={'EXPECTED_DIGEST_PRESENT','ACTUAL_DIGEST_PRESENT','HASH_ATTEMPTED','HASH_COMPLETE','EXPECTED_SIZE_PRESENT'}
                if d['capture']:true|={'CAPTURE_REQUESTED','CAPTURE_COMPLETE','BLOB_ISSUED'}
                if index<2:true.add('EARLY')
                if terminal:true|={'CLOSE_RESERVED','CLOSE_SUCCESS_KNOWN','CLOSE_SUCCESS_TRUE'}
                expected_row=dict(ordinal=index,role=d['role'].upper(),capture_state='COMPLETE' if d['capture'] else 'NOT_REQUESTED',target_class='ORIGINAL',open_state='OWNED',identity_state='VERIFIED',close_state='RETURNED_SUCCESS' if terminal else 'NOT_ATTEMPTED',flags=flags(FILE_FLAGS,true),descriptor_id=index,path_offset=pathoff,path_bytes=len(d['path'].encode()),path_utf16_units=len(d['path'].encode('utf-16-le'))//2,expected_size=size,expected_sha256=bytes.fromhex(d['sha256']),actual_sha256=bytes.fromhex(d['sha256']),open_ordinal=self.open_ordinals[index],close_ordinal=WORK_CALLS+N-1-index if terminal else None,known_read_bytes=size,hashed_bytes=size,captured_bytes=size if d['capture'] else 0,query_offset=8218*index,query_length=8218,first_diagnostic=None,read_reservations=q,read_invocations=q,captured_blob_length=size if d['capture'] else 0,early_ordinal=index if index<2 else None,path_id=index,read_generation=self.read_bases[index]+q-1,module_ordinal=index if index<2 else None)
                require(same(value,tuple(expected_row[k] for k in FILE_FIELDS)),'independent complete file row '+str(index));pathoff+=expected_row['path_bytes']
            elif kind=='calls':
                ei,ea,requested,generation,handle=next(expected)
                self.check_call(index,value,ei,ea,requested,generation,handle)
            elif kind=='queries':
                require(type(value)is memoryview and len(value)==QUERY_BYTES,'full querypool shape')
                offset=0
                for d in self.descriptors:
                    for api in API[2:5]:
                        raw=query_frame(d,api);require(value[offset:offset+len(raw)]==raw,'independent raw query frame')
                        ci=self.open_ordinals[d['file_id']]+API.index(api)
                        c=self.binding.refs[ci]._state
                        require(type(c.query_bytes)is bytes and value[offset:offset+len(raw)]==c.query_bytes,'packed versus actual source query frame')
                        offset+=len(raw)
                require(offset==len(value),'all querypool bytes visited');state['pool_bytes'][kind]=offset
            elif kind=='paths':
                require(type(value)is memoryview,'actual pathpool view');offset=0
                for d in self.descriptors:
                    raw=d['path'].encode();require(value[offset:offset+len(raw)]==raw,'original fictional path bytes');offset+=len(raw)
                require(offset==len(value),'all pathpool bytes visited');state['pool_bytes'][kind]=offset
            elif kind=='module_names':
                require(type(value)is memoryview and value==b'cohort_leafcohort_entry','full module name bytes');state['pool_bytes'][kind]=len(value)
            elif kind=='module_edges':require(index==0 and type(value)is int and value==0,'closed edge entry->leaf')
            elif kind=='modules':
                name=('cohort_leaf','cohort_entry')[index]
                row=dict(ordinal=index,file_ordinal=index,flags=dict(PACKAGE=False,RETURN_OBSERVED=True,ACCEPTED=True,CACHED=True),dependency_count=index,name_offset=0 if index==0 else 11,name_length=len(name),edge_offset=0,first_diagnostic=None,attempt_order=1-index,return_order=index,cache_hit_count=0)
                require(same(value,tuple(row[k] for k in MODULE_FIELDS)),'actual compiled module tuple')
            elif kind=='diagnostics':raise HarnessError('positive fixture unexpectedly has committed diagnostic')
        require(counts==dict(header=1,files=N,calls=expected_calls,modules=2,module_edges=1,diagnostics=0,queries=1,paths=1,module_names=1),'all tables/pools exhausted exactly')
        state.update(complete=True,raw_bytes=len(artifact.raw),sha256=artifact.sha256,elapsed_end=time.monotonic()-self.entry)
        return state
    def check_header(self,h,terminal,expected_calls,raw):
        require(h['magic']==b'RAPLEDG1' and h['format_version']==1 and h['value_schema_version']==2,'actual header versions')
        expected=dict(profile=2,phase=2 if terminal else 1,status=1,header_bytes=4096,section_count=8,file_count=N,call_count=expected_calls,module_count=2,module_count_repeat=2,edge_count=1,diagnostic_count=0,total_bytes=len(raw),captured_input_bytes=209,known_read_bytes=TOTAL,hashed_bytes=TOTAL,copied_bytes=209,reserved_R=R,reserved_C=C,reserved_E=E,early_count=2,read_chunk=CHUNK,origin_data_id=1,ledger_sequence=2 if terminal else 1,qualification_bits=0,path_policy=1)
        for k,v in expected.items():require(type(h[k]) is type(v) and h[k]==v,'header independent '+k)
        # Raw F64 clock bit encodings must retain the SAME actual start.
        require(h['start_clock_bits']==struct.unpack('<Q',struct.pack('<d',self.entry))[0],'header first clock raw bits')
        require(h['clock_tags']==42,'three observed F64 clock tags')
        for name in ('latest_clock_bits','freeze_clock_bits'):
            observed=struct.unpack('<d',struct.pack('<Q',h[name]))[0]
            require(self.entry<=observed<self.entry+300,'header clock belongs to original owner window')
        previous=hashlib.sha256(self.sink.artifacts['candidate-ledger.bin'].raw).digest() if terminal else bytes(32)
        require(h['previous_ledger_sha256']==previous,'terminal binds actual immutable candidate bytes')
        expected_flags=64 if terminal else 0 # Frozen b71 header bit6.
        require(h['flags']==expected_flags,'healthy exact header flags')
    def check_call(self,j,value,i,api,requested,generation,handle):
        require(j<self.binding.count,'wire invented unobserved dispatch')
        observed=self.binding.row(j);ref=self.binding.refs[j];c=ref._state;d=self.descriptors[i]
        require(observed[:4]==(j,i,API.index(api)+1,requested) and observed[9]&15==(15 if api=='ReadFile' else 11),'spy first facts and prepared normal return')
        require(ref is c.ref and c.owner is self.owner and c.file.ref is self.file_refs[i] and c.wrapper_return and c.wrapper_state=='returned' and not c.stopped,'live canonical call/source return axes')
        scalar=handle if api=='CreateFileW' else len(('\\\\?\\'+d['path']).encode('utf-16-le'))//2 if api=='GetFinalPathNameByHandleW' else 1
        require(type(c.scalar)is int and c.scalar==scalar==observed[5],'source first scalar versus independent binding')
        read=api=='ReadFile';query=api in API[2:5];buffer=read or query
        require(c.count==requested and observed[4]==requested if read else c.count is self.S.UNOBSERVED,'raw count observation exact')
        require(c.error is self.S.UNOBSERVED and c.error_definition is self.S.UNOBSERVED,'no fabricated raw error/definition')
        require(type(c.pre_clock)is float and type(c.post_clock)is float and self.entry<=c.pre_clock<=observed[6]<=observed[7]<=c.post_clock<self.entry+(300 if api=='CloseHandle' else 295),'actual pre/post clock ordering')
        true={'INVOKED','SCALAR_OBSERVED','WRAPPER_RETURNED','SCALAR_DOMAIN_VALID','PRE_CLOCK_ATTEMPTED','POST_CLOCK_ATTEMPTED','PRE_CLOCK_RETURN_OBSERVED','POST_CLOCK_RETURN_OBSERVED'}
        if api!='CreateFileW':true.add('INPUT_HANDLE_PRESENT')
        if d['capture']:true.add('CAPTURE_REQUESTED')
        if buffer:true|={'BUFFER_PRESENT','BUFFER_DATA_OBSERVED'}
        if query:true|={'QUERY_CAPTURE_OBSERVED','QUERY_DEFINED','QUERY_SPAN_PRESENT'}
        if read:true|={'COUNT_OBSERVED','COUNT_DEFINED','COUNT_DOMAIN_VALID','IDENTITY_VERIFIED_AT_DISPATCH','REQUESTED_PRESENT','HASH_ATTEMPTED','HASH_RETURN_OBSERVED'}
        if read and d['capture']:true|={'COPY_ATTEMPTED','COPY_RETURN_OBSERVED'}
        if api=='CloseHandle':true.add('CLOSE_RIGHT_CONSUMED')
        qlen=8 if api in ('GetFileInformationByHandleEx','GetFileSizeEx') else 8202 if api=='GetFinalPathNameByHandleW' else 0
        qoff=8218*i+{'GetFileInformationByHandleEx':0,'GetFinalPathNameByHandleW':8,'GetFileSizeEx':8210}.get(api,0) if query else 0
        qgen=3*i+API[2:5].index(api) if query else generation if read else 0
        row=dict(ordinal=j,file_id=i,api=api,record_version=1,flags=flags(CALL_FLAGS,true),requested=requested,buffer_id=0 if read else 1 if query else None,phase='original_close' if api=='CloseHandle' else 'binding_invoke',generation=qgen,buffer_written=requested if read else qlen,scalar_atom=atom('HANDLE' if api=='CreateFileW' else 'DWORD' if api in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL',scalar),count_atom=atom('COUNT32',requested) if read else atom('UNOBSERVED',None),error_atom=atom('UNOBSERVED',None),error_definition_atom=atom('UNOBSERVED',None),hashed_contribution=requested if read else 0,captured_contribution=requested if read and d['capture'] else 0,known_count_contribution=requested if read else 0,query_offset=qoff,query_length=qlen,input_handle_atom=atom('UNOBSERVED',None) if api=='CreateFileW' else atom('HANDLE',handle),pre_dispatch_clock=atom('F64',c.pre_clock),post_binding_clock=atom('F64',c.post_clock),error_id=None,path_id=i,fold_state='COMMITTED' if read else 'PENDING',buffer_state='RAW_RETAINED' if read else 'DEFINED' if query else 'NOT_APPLICABLE')
        require(same(value,tuple(row[k] for k in CALL_FIELDS)),'independent packed call row '+str(j))
    def verify_final(self,issued):
        require(type(issued)is self.S.ProducerSnapshot and issued.owner is self.owner,'genuine first terminal snapshot')
        # No full to_dict(): full raw call/query/journal evidence lives in the
        # actual source ledgers and retained source-issued bytes.
        data=issued._data
        require(data['status']=='PURE_SEAM_COMPLETE_CONSISTENT' and data['pure_seam_complete'] is True and data['calls'] is None,'actual terminal source verdict')
        require(all(v is False for v in data['qualification'].values()),'no authority promotion')
        require((data['byte_totals']['known_read_bytes'],data['byte_totals']['hashed_bytes'],data['byte_totals']['captured_bytes'])==(TOTAL,TOTAL,209),'actual canonical byte totals')
        require(data['byte_totals']['read_count_unknown'] is False,'known counts not unknown')
        require(self.binding.count==ALL_CALLS and self.binding.reads==Q and self.binding.overflow_attempts==0,'actual dispatch/read counts')
        require(self.binding.delivered==[d['size'] for d in self.descriptors] and self.binding.close_counts==[1]*N,'all delivered bytes and once-only closes')
        require(all(value is True for value in data['terminal'].values()),'all actual terminal ACK facts')
        require(self.owner.primary is None and not self.owner.secondary and self.owner._diag_committed==0 and self.owner._diag_borrowed==0,'no hidden diagnostics')
        require(self.owner.origin is self.original_origin and self.owner.nonce is self.nonce and self.owner.registry is self.registry and self.owner.port is self.view and self.owner.sink is self.sink and self.owner.loader is self.loader and self.owner.journal is self.journal and self.continuation.owner is self.owner,'same original owner continuation identities')
        ctx=self.owner.evidence_context
        require(ctx.owner is self.owner and ctx.nonce is self.nonce and ctx.early_context is self.early and len(ctx.specs)==N and len(ctx.digests)==N and len(ctx.blobs)==3,'full digest/capture context membership')
        for i,(d,state) in enumerate(zip(self.descriptors,self.states)):
            require(state is self.file_refs[i]._state and self.owner.file_ref(d['path']) is self.file_refs[i],'canonical retained file state identity')
            require(state.hash_complete and state.actual_sha==d['sha256'] and state.assembly is None,'actual hash/no retained assembly')
            if d['capture']:
                require(ctx.bytes_for(d['path']) is state.blob and state.blob==self.tiny[i],'exact captured blob bytes/identity')
                if i<2:require(ctx.bytes_for(d['path']) is self.early.bytes_for(d['path']),'same early captured byte object')
            else:
                require(state.blob is None and state.capture_state=='NOT_REQUESTED' and not state.capture_complete and state.captured==0,'hash-only no fabricated capture')
                try:ctx.bytes_for(d['path'])
                except self.S.CaptureNotRequested:pass
                else:raise HarnessError('bulk bytes were accessible')
        require(self.checker_calls==['archive','journal','resources','core'],'explicitly synthetic checker sequence')
        require(set(self.sink.artifacts)=={'candidate-ledger.bin','terminal-ledger.bin'} and all(x['complete'] for x in self.sink.consumption),'two complete actual byte consumers')
        require(self.sink.artifacts['candidate-ledger.bin'].raw is not self.sink.artifacts['terminal-ledger.bin'].raw,'candidate/terminal distinct immutable snapshots')
        require(self.sink.counts==dict(candidate=1,cleanup=1,failure=0,receipt=1,seal=1),'actual positive publication attempts')
        return dict(status=data['status'],pure_seam_complete=True,origin=dict(data['origin']),plan=dict(data['plan']),byte_totals=dict(data['byte_totals']),terminal=dict(data['terminal']),api_counters={k:dict(v) for k,v in data['api_counters'].items()},generated={k:dict(v) for k,v in data['generated'].items()},assembly_peak=data['assembly_peak'],all_qualifications_false=True)


def validate_reference(reference):
    require(reference['status']=='REFERENCE_COMPLETE' and reference['final_deadline_veto'] is False,'complete independent reference only')
    require((reference['N'],reference['Q'],reference['R'],reference['C'],reference['E'],reference['reference_bytes_hashed'],reference['unique_checkpoint_count'])==(N,Q,R,C,E,3991999872,198),'exact independent reference geometry')
    ds=reference['descriptors'];require(type(ds)is list and len(ds)==N,'exact216 descriptors')
    for i,d in enumerate(ds):
        require(type(d['file_id'])is int and d['file_id']==i and type(d['size'])is int and d['size']>0,'explicit positive descriptor')
        filename=('cohort_leaf.py','cohort_entry.py','metadata.json')[i] if i<3 else 'bulk\\file_'+str(i-3).zfill(3)+'.bin'
        require(d['path']=='D:\\FictionalRoleAwareLarge\\'+filename,'only new fictional paths')
        require(d['role']==('captured_software' if i<2 else 'captured_metadata' if i==2 else 'hash_only_bulk') and d['capture'] is (i<3),'closed explicit consumer roles')
        require(type(d['sha256'])is str and re.fullmatch('[0-9a-f]{64}',d['sha256']) is not None,'literal reference digest')
    require(sum(d['size'] for d in ds)==TOTAL and sum(d['size'] for d in ds[:3])==209,'size-only plus209 geometry')


def exception_metadata(error):
    if error is None:return None
    try:message=str(error)[:2048]
    except BaseException:message='<formatter failed; original object retained by owner>'
    return dict(class_name=type(error).__name__,message=message)


def terminal_observation(w,issued):
    """Retain actual negative/partial terminal before any positive assertion."""
    if w is None or w.owner is None:return dict(issued=False,reason='owner not constructed')
    if issued is None:return dict(issued=False,reason='source has not issued a terminal snapshot',primary=exception_metadata(w.owner.primary))
    require(type(issued)is w.S.ProducerSnapshot and issued.owner is w.owner,'actual source terminal brand')
    data=issued._data
    def diag(value):
        if value is None:return None
        error=w.owner.exception_for_token(value['identity'])
        return dict(class_name=value['class_name'],phase=value['phase'],message=value['message'],format_failed=value['format_failed'],resolved_original_identity=(error is w.owner.primary or any(error is e for e in w.owner.secondary)))
    return dict(issued=True,status=data['status'],phase=data['phase'],finalized=data['finalized'],pure_seam_complete=data['pure_seam_complete'],refusal_code=data['refusal_code'],origin=dict(data['origin']),plan=None if data['plan'] is None else dict(data['plan']),byte_totals=dict(data['byte_totals']),api_counters={k:dict(v) for k,v in data['api_counters'].items()},terminal=dict(data['terminal']),errors=dict(primary=diag(data['errors']['primary']),secondary=[diag(d) for d in data['errors']['secondary']]),qualification=dict(data['qualification']))


def raw_atom(value,sentinel):
    """Raw observation, never a later auxiliary flag or hook-completion bit.

    The ordinary fixture domains are retained exactly. Out-of-domain large or
    arbitrary objects are explicitly observed/unencodable, never defaulted to0.
    The id is a local diagnostic only and never serialized owner authority.
    """
    if value is sentinel:return dict(tag='UNOBSERVED',value=None)
    if value is None:return dict(tag='NULL',value=None)
    t=type(value)
    if t is bool:return dict(tag='BOOL',value=value)
    if t is int and -(1<<63)<=value<(1<<64):return dict(tag='INT',value=value)
    if t is float:return dict(tag='FLOAT64_BITS',bits=struct.pack('<d',value).hex())
    if t is str and len(value)<=256:return dict(tag='TEXT',value=value)
    if t is bytes and len(value)<=256:return dict(tag='BYTES',hex=value.hex())
    # Do not invoke repr(), str(), conversions or a producer method here.
    return dict(tag='OBSERVED_UNENCODABLE',type_name=type.__getattribute__(t,'__name__')[:128],local_object_id=id(value))


def persist_canonical_raw(w,evidence,retained,progress):
    """Cold one-row-at-a-time evidence from ALL existing reserved records.

    No owner methods, refreeze, new clock, whole-call list or bulk buffer copy.
    Immutable query captures are streamed separately, never copied as a pool.
    """
    if w.owner is None:
        progress.update(state='NO_OWNER',rows_expected=None,rows_written=0);return
    records=w.owner.registry._calls
    require(type(records)is list and len(records)<=C,'bounded existing canonical record list')
    raw_path=evidence/'independent-canonical-raw-facts.jsonl'
    query_path=evidence/'independent-canonical-query-frames.bin'
    progress.update(state='WRITING',rows_expected=len(records),rows_written=0,bytes=0,query_bytes=0,unencodable_atoms=0)
    raw_hash=hashlib.sha256();query_hash=hashlib.sha256()
    with raw_path.open('xb') as raw_out,query_path.open('xb') as query_out:
        for index,c in enumerate(records):
            require(c.owner is w.owner and type(c.ordinal)is int and c.ordinal==index,'canonical raw row identity/order')
            a=lambda value:raw_atom(value,w.S.UNOBSERVED)
            q=c.query_bytes
            if q is None:query=dict(capture_observed=False,offset=None,bytes=None,sha256=None)
            else:
                require(type(q)is bytes and len(q)<=8202 and progress['query_bytes']+len(q)<=QUERY_BYTES,'bounded retained immutable query frame')
                query=dict(capture_observed=True,offset=progress['query_bytes'],bytes=len(q),sha256=hashlib.sha256(q).hexdigest())
                query_out.write(q);query_hash.update(q);progress['query_bytes']+=len(q)
            row=dict(schema_version=1,ordinal=index,file_id=None if c.file is None else c.file.id,api=c.api,prepared=c.prepared,invoked=c.invoked,
                scalar=a(c.scalar),count=a(c.count),error=a(c.error),error_definition=a(c.error_definition),input_handle=a(c.input_handle),
                wrapper_return_observed=c.wrapper_return,wrapper_state=c.wrapper_state,stopped=c.stopped,
                close_right_consumed=c.api=='CloseHandle' and c.file is not None and c.file.close_reserved,
                auxiliary=dict(scalar_ack=c.scalar_aux_ack,count_ack=c.count_aux_ack,right_transfer_ack=c.right_transfer_ack),
                reservation_fold=c._reservation_fold,read_fold=dict(phase=c._read_fold_phase,contribution=c._read_contribution),
                hash=dict(attempted=c.hash_attempted,raw_return=a(c.hash_return),stored_count_field=c.hash_count,fold_phase=c._hash_fold_phase),
                copy=dict(attempted=c.copy_attempted,raw_return=a(c.copy_return),stored_count_field=c.copy_count,fold_phase=c._copy_fold_phase),
                clocks=dict(pre_attempted=c.pre_clock_attempted,pre_raw=a(c.pre_clock),post_attempted=c.post_clock_attempted,post_raw=a(c.post_clock)),
                buffer=dict(present=c.buffer is not None,generation=c.generation,state=c.buffer_state,written=c.buffer_written),query=query)
            atoms=(row['scalar'],row['count'],row['error'],row['error_definition'],row['input_handle'],row['hash']['raw_return'],row['copy']['raw_return'],row['clocks']['pre_raw'],row['clocks']['post_raw'])
            progress['unencodable_atoms']+=sum(x['tag']=='OBSERVED_UNENCODABLE' for x in atoms)
            encoded=canonical(row);require(len(encoded)<=4096 and progress['bytes']+len(encoded)<=C*4096,'canonical raw sidecar bound')
            raw_out.write(encoded);raw_hash.update(encoded);progress['bytes']+=len(encoded);progress['rows_written']+=1
    progress['state']='COMPLETE_EXISTING_FACTS' if progress['unencodable_atoms']==0 else 'OBSERVED_UNENCODABLE_RAW_RETAINED_AS_EXPLICIT_UNKNOWN'
    retained.extend((dict(path=str(raw_path.resolve()),bytes=progress['bytes'],sha256=raw_hash.hexdigest()),dict(path=str(query_path.resolve()),bytes=progress['query_bytes'],sha256=query_hash.hexdigest())))


def main():
    entry=time.monotonic() # FIRST helper-entry action; includes ALL bootstrap.
    parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()
    binding_path=HERE/'ROLE-AWARE-LARGE-INJECTED-BINDING-v3.json'
    attempt=HERE/'ROLE-AWARE-LARGE-INJECTED-ATTEMPT-v3.json';proof=HERE/'ROLE-AWARE-LARGE-INJECTED-PROOF-v3.json'
    evidence=HERE/'large-injected-evidence-v3'
    w=D=issued=None;bindings=None;source_started=False;failure=None;verified=None;first_terminal=None;result=None;retained=[];publication_error=None;subject_end=None
    source_pins={};harness_pins={};root_scope=None;raw_progress=dict(state='NOT_STARTED',rows_expected=None,rows_written=0)
    try:
        require(re.fullmatch('[0-9a-f]{64}',args.binding_sha256) is not None,'explicit binding digest')
        raw=binding_path.read_bytes();require(hashlib.sha256(raw).hexdigest()==args.binding_sha256,'binding changed');bindings=json.loads(raw)
        require(bindings['mode']=='GENUINE_LARGE216_INJECTED_FIRST_V3','exact single execution mode')
        root_scope=json.loads(checked(bindings['execution_scope']))
        require(not attempt.exists() and not proof.exists() and not evidence.exists(),'first result/evidence retained; no replay')
        with attempt.open('xb') as out:out.write(canonical(dict(binding_sha256=args.binding_sha256,original_entry_monotonic=entry,root_scope=bindings['execution_scope'],subject_imported=False)))
        require(bindings['reference']['sha256']==REFERENCE_SHA and Path(bindings['reference']['path']).resolve()==HERE/'ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json','fixed independent reference pin')
        reference=json.loads(checked(bindings['reference']));validate_reference(reference)
        require(bindings['source_pause']['sha256']==PAUSE_SHA and Path(bindings['source_pause']['path']).resolve()==HERE/'ROLE-AWARE-PRODUCER-SOURCE-PAUSE-v4.json','accepted source4 only')
        pause=json.loads(checked(bindings['source_pause']));source_pins=bindings['source_map']
        require(set(source_pins)==set(MODULES) and source_pins==pause['sources'],'exact coherent paused source map')
        require(tuple(pause['own_module_order'])==MODULES,'paused dependency order')
        source_pins={name:source_pins[name] for name in MODULES}
        for name,p in source_pins.items():require(Path(p['path']).resolve()==HERE/(name+'.py'),'fixed new source path');checked(p)
        require(bindings['adapter']['sha256']==ADAPTER_SHA and Path(bindings['adapter']['path']).resolve()==HERE/'role_aware_legacy_fixture_adapter_v2.py','fixed audit/closed loader')
        # Dependency evidence is loaded BEFORE ACTIVE; no source/cached fallback.
        for p in bindings['required_evidence'].values():checked(p)
        helper_pin=pin(Path(__file__).resolve());harness_pins=dict(helper=helper_pin,adapter=bindings['adapter'])
        declared_helper=bindings['helper']
        require(set(declared_helper)=={'path','bytes','sha256'} and Path(declared_helper['path']).resolve()==Path(helper_pin['path']).resolve() and declared_helper['bytes']==helper_pin['bytes'] and declared_helper['sha256']==helper_pin['sha256'],'exact reviewed helper')
        'harmless'.encode('utf-16-le')
        trusted=types.ModuleType('_large216_trusted_audit_v1');trusted.__file__=bindings['adapter']['path'];trusted.__package__=''
        exec(compile(checked(bindings['adapter']),trusted.__file__,'exec'),trusted.__dict__);D=trusted
        source_started=True;modules=D.load_exact_modules(source_pins)
        w=World(D,modules,reference,entry)
        try:
            issued=w.run()
        except BaseException:
            # Preserve first failure; finally may only attempt bounded cleanup.
            raise
        finally:
            if w.owner is not None and not w.owner.finalized:
                original_error=sys.exc_info()[1]
                try:
                    cleanup_result=D.invoke(w.owner.finalize,'incomplete')
                    if issued is None:issued=cleanup_result
                except BaseException as cleanup:
                    if original_error is None:raise
                    w.violations.append(dict(message='cleanup raised '+type(cleanup).__name__,elapsed=time.monotonic()-entry))
        subject_end=time.monotonic()
        first_terminal=terminal_observation(w,issued)
        w.deadline(cleanup=True,where='post-source terminal verification')
        verified=w.verify_final(issued)
        w.deadline(cleanup=True,where='final independent verification veto')
        require(not D.AUDIT_DENIALS and not w.violations,'audit/independent monitor violations')
        result='PASS_SOURCE_PURE_LARGE_GENERATED_ONLY'
    except BaseException as error:
        subject_end=time.monotonic() if subject_end is None else subject_end
        failure=dict(error_class=type(error).__name__,message=exception_metadata(error)['message'],traceback=traceback.format_exc())
        result='INCOMPLETE_OR_FAIL_FIRST_RESULT_RETAINED'
        if w is not None and w.owner is not None and issued is None and w.owner.finalized:
            issued=D.invoke(w.owner.snapshot) # Existing immutable cached object.
        try:first_terminal=terminal_observation(w,issued)
        except BaseException as observation_error:first_terminal=dict(issued=issued is not None,observation_error=exception_metadata(observation_error))
    # Persist complete/partial evidence only after every subject frame unwound.
    # No owner retry, new clock, re-freeze or evidence repair is permitted here.
    publication_started=time.monotonic()
    try:
        if w is not None:
            evidence.mkdir()
            def persist(name,raw,cap):
                require(type(raw)is bytes or type(raw)is memoryview,'bounded evidence raw type')
                require(len(raw)<=cap,'evidence byte cap')
                path=evidence/name
                with path.open('xb') as out:out.write(raw)
                retained.append(dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            # Complete genuine ledgers remain byte-for-byte; no digest-only proof.
            # Also retain any source-known unissued/partial bytes on failure.
            for name,rec in w.owner._generated.items() if w.owner is not None else ():
                raw=rec['raw']
                if raw is not None:persist(name.replace('/','__'),raw,w.S.ARTIFACT_CAPS[name])
            persist_canonical_raw(w,evidence,retained,raw_progress)
            if raw_progress.get('unencodable_atoms',0):result='INCOMPLETE_OR_FAIL_FIRST_RESULT_RETAINED'
            if w.binding is not None:
                persist('independent-original-dispatches.bin',memoryview(w.binding.log)[:min(w.binding.count,C)*64],C*64)
                persist('independent-close-facts.json',canonical(dict(opened=w.binding.opens,close_counts=w.binding.close_counts,delivered=w.binding.delivered)),65536)
            # Journal row refs were aliases, never hex copies. Persist stream.
            journal=evidence/'independent-callback-journal.jsonl';h=hashlib.sha256();length=0
            with journal.open('xb') as out:
                for row in (() if w.sink is None else w.sink.journal):out.write(row);h.update(row);length+=len(row)
            retained.append(dict(path=str(journal.resolve()),bytes=length,sha256=h.hexdigest()))
            # The producer observes actual callback return after our callback
            # leaves. Do not confuse our prepared ACK with its known return.
            for callback in (() if w.sink is None else w.sink.callbacks):
                target=callback['target']
                if target=='append':
                    index=callback.get('sequence')
                    source=w.owner.journal['events'][index] if type(index)is int and index<len(w.owner.journal['events']) else None
                elif target=='reserve':source=w.owner._outputs['reservation']
                elif target=='close_journal':source=w.owner._outputs['journal_close']
                else:source=w.owner._outputs['publications'].get(target.removeprefix('publish_'))
                callback['source_return_observed']=None if source is None else source['return_observed']
                callback['source_acknowledged']=None if source is None else source['acknowledged']
            persist('independent-sink-callback-metadata.json',canonical([] if w.sink is None else w.sink.callbacks),1048576)
            persist('independent-ledger-consumption.json',canonical(w.consumer_partial),65536)
    except BaseException as error:
        publication_error=dict(error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc());result='INCOMPLETE_OR_FAIL_FIRST_RESULT_RETAINED'
    stable={}
    try:
        for name,p in (*source_pins.items(),*harness_pins.items()):
            observed=pin(Path(p['path']))
            stable[name]=(Path(observed['path']).resolve()==Path(p['path']).resolve() and observed['bytes']==p['bytes'] and observed['sha256']==p['sha256'])
        if stable and not all(stable.values()):result='INCOMPLETE_OR_FAIL_FIRST_RESULT_RETAINED'
    except BaseException as error:
        result='INCOMPLETE_OR_FAIL_FIRST_RESULT_RETAINED';stable['check_error']=type(error).__name__
    record=dict(schema_version=1,status=result,original_entry_monotonic=entry,work_end=entry+295,hard_end=entry+300,
        source_stack_unwound_elapsed=None if subject_end is None else subject_end-entry,evidence_publication_elapsed=time.monotonic()-publication_started,
        binding_sha256=args.binding_sha256,source_pins=source_pins,harness_pins=harness_pins,source_and_harness_unchanged=stable,
        observed_source_imports_started=source_started,source_modules_registered=[name for name in MODULES if name in sys.modules] if source_started else [],first_exception=failure,evidence_publication_error=publication_error,
        first_actual_terminal=first_terminal,positive_verification=verified,consumer_passes=[] if w is None else w.consumer_partial,evidence=retained,canonical_raw_sidecar=raw_progress,
        actual_original_dispatches=None if w is None or w.binding is None else w.binding.count,
        actual_read_dispatch_attempts=None if w is None or w.binding is None else sum(w.binding.row(i)[2]==6 for i in range(min(w.binding.count,C))),
        helper_completed_read_deliveries=None if w is None or w.binding is None else w.binding.reads,
        actual_close_attempts=None if w is None or w.binding is None else sum(w.binding.close_counts),helper_completed_delivery_bytes=None if w is None or w.binding is None else sum(w.binding.delivered),
        canonical_known_successful_close_returns=None if w is None or w.owner is None else sum(c.api=='CloseHandle' and c.invoked and type(c.scalar)is int and -(1<<31)<=c.scalar<(1<<31) and c.scalar!=0 for c in w.owner.registry._calls),
        original_clock_calls=None if w is None else w.clock.calls,monitor_violations=[] if w is None else w.violations,
        audit_denials=[] if D is None else D.AUDIT_DENIALS,
        accounting='Reference preparation elapsed is separate. Producer original300s includes bootstrap. Evidence persistence is measured separately after source return, never a physical producer ACK.',
        memory='Harness: C*64 compact dispatch bytes + C reference slots +216 descriptors/states + aliased journal rows/artifact bytes + per-row dictionaries and <=8202B query comparison. No bulk body, fullpool copy or hex. Object overhead, peak RSS and OS resources UNKNOWN.',
        qualification=QUAL,limits='Cooperative original checks; no hard callback-free hang bound. Synthetic periodic payloads and toy checker factories do not qualify real entry/FFI/physical IO/full84/resource/scientific behavior.')
    with proof.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    print(json.dumps(dict(proof=pin(proof),status=result,actual_original_dispatches=record['actual_original_dispatches'],retained_artifacts=len(retained))))
    return 0 if result=='PASS_SOURCE_PURE_LARGE_GENERATED_ONLY' else 1


if __name__=='__main__':raise SystemExit(main())
