"""Captured, non-owning late operations over the canonical entry kernel.

No Owner/Origin/Registry constructor, native access or ordinary import fallback.
Source4 algorithms are explicit lineage; late algorithm receivers are KernelState.
The accepted Source4 files remain unchanged. Initial factories are synthetic.
"""
from dataclasses import dataclass
from types import MappingProxyType
import json
import preflight_entry_kernel_v3 as K
import role_ledger_codec_v4 as codec

UNOBSERVED=K.UNOBSERVED
INVALID=K.INVALID
PROFILE_N4=K.PROFILE_N4
PROFILE_ORIGINAL7_1M=K.PROFILE_ORIGINAL7_1M
CapturedContext=K.CapturedContext
KernelSnapshot=K.KernelSnapshot
uint=K.uint
signed_bool=K.signed_bool
usable=K.usable
sha=K.sha
freeze=K.freeze
thaw=K.thaw
atom=K.atom
_Rows=K._Rows
_same_typed=K._same_typed
_utf8_prefix=K._utf8_prefix
_clock_atom=K._clock_atom
CHECKS=('archive','journal','resources','core')
GATES=('admission','hashes',*CHECKS,'consistency','leases_closed','sealed','final_clock')
KINDS=('candidate','cleanup','failure','receipt','seal')
QUALIFICATION=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,real_checkers_bound=False,verification_complete=False,profile_qualified=False,runtime_authorized=False)
ARTIFACT_CAPS=K.ARTIFACT_CAPS
ROLE_WIRE=K.ROLE_WIRE
_MINT=object()
_OPS_MINT=object()

def need(ok,code='INVALID_INPUT'):
    if not ok:raise K.KernelRefusal(code)

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
    def __post_init__(self):
        need(self._mint is _MINT and type(self.owner)is K.KernelState and type(self.raw)is bytes)

@dataclass(frozen=True,slots=True)
class LegacySnapshot:
    _data:object
    def to_dict(self):return thaw(self._data)

class _LateAlgorithms:
    def match_full_roster(self,request,authority):
        self._active();self.check();self._live_early();self.require(type(request.output_key)is str and request.output_key==self.output_key and type(request.files) is tuple and request.files==self._specs and authority.files==self._specs and authority.owner is self,'EARLY_DESCRIPTOR_MISMATCH');self.proof('admission')

    def hash_remaining(self):
        self._active();self._live_early()
        for f in self.registry._files:
            if not f.early:self.port.acquire(f.spec);self.port.inspect(f.ref);self.port.hash_capture(f.ref)
        self.require(all(f.hash_complete and (not f.spec.capture or f.capture_complete)for f in self.registry._files),'READ_PROGRESS_INCOMPLETE')
        self._evidence_context=self.make_context(self._specs,{f.spec.path:f.blob for f in self.registry._files if f.spec.capture},{f.spec.path:f.actual_sha for f in self.registry._files},early_context=self.early_context);self.proof('hashes');return self.evidence_context

    def _packet(self,kind):
        self.require_role1_representable()
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
        scalar=self.committed_fact(c,'scalar')
        if not c.invoked or not signed_bool(scalar):return False,None
        return True,scalar!=0

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
        scalar=self.committed_fact(c,'scalar');count=self.committed_fact(c,'count');error=self.committed_fact(c,'error_value');error_definition=self.committed_fact(c,'error_definition')
        # Native committed HANDLE64 zero is NULL; copied raw axes retain its integer bits.
        if scalar_tag=='HANDLE' and type(scalar)is int and scalar==0:scalar=None
        so=scalar is not UNOBSERVED;co=count is not UNOBSERVED;eo=error is not UNOBSERVED
        scalar_valid=so and((scalar is None or uint(scalar,INVALID))if scalar_tag=='HANDLE'else uint(scalar,0xffffffff)if scalar_tag=='DWORD'else signed_bool(scalar))
        defined=self.defined(c);frame={'GetFileInformationByHandleEx':8,'GetFinalPathNameByHandleW':8202,'GetFileSizeEx':8}.get(c.api,0)
        hash_return=c.hash_return is not UNOBSERVED;copy_return=c.copy_return is not UNOBSERVED
        account=c._read_fold_phase=='applying'or c._hash_fold_phase=='applying'or c._copy_fold_phase=='applying'
        cf.update(INVOKED=c.invoked,SCALAR_OBSERVED=so,SCALAR_NULL=so and scalar is None,COUNT_OBSERVED=co,COUNT_DEFINED=defined,ERROR_OBSERVED=eo,ERROR_DEFINED=error_definition is True,ERROR_DEFINITION_OBSERVED=error_definition is not UNOBSERVED,SCALAR_AUX_ACK=c.scalar_aux_ack,COUNT_AUX_ACK=c.count_aux_ack,RIGHT_TRANSFER_ACK=c.right_transfer_ack,WRAPPER_RETURNED=c.wrapper_return,STOPPED=c.stopped,QUERY_CAPTURE_OBSERVED=c.query_bytes is not None,QUERY_DEFINED=c.query_bytes is not None and scalar_valid and scalar not in(None,0,INVALID),BUFFER_DATA_OBSERVED=c.buffer_state in('raw_retained','defined'),ACCOUNTING_FAULT=account,CLOSE_RIGHT_CONSUMED=c.api=='CloseHandle'and f.close_reserved,IDENTITY_VERIFIED_AT_DISPATCH=c.api=='ReadFile'and f.identity_witness is not None,SCALAR_DOMAIN_VALID=scalar_valid,COUNT_DOMAIN_VALID=co and uint(count,0xffffffff),ERROR_DOMAIN_VALID=eo and uint(error,0xffffffff),PRE_CLOCK_ATTEMPTED=c.pre_clock_attempted,POST_CLOCK_ATTEMPTED=c.post_clock_attempted,PRE_CLOCK_RETURN_OBSERVED=c.pre_clock is not UNOBSERVED,POST_CLOCK_RETURN_OBSERVED=c.post_clock is not UNOBSERVED,HASH_ATTEMPTED=c.hash_attempted,HASH_RETURN_OBSERVED=hash_return,COPY_ATTEMPTED=c.copy_attempted,COPY_RETURN_OBSERVED=copy_return,CAPTURE_REQUESTED=f.spec.capture,MALFORMED_RAW=so and not scalar_valid,INPUT_HANDLE_PRESENT=c.input_handle is not UNOBSERVED,REQUESTED_PRESENT=c.api=='ReadFile',BUFFER_PRESENT=c.buffer is not None,QUERY_SPAN_PRESENT=bool(frame))
        fold='COMMITTED'if c._read_fold_phase=='committed'else'FAILED_BEFORE_COMMIT'if c._read_fold_phase=='applying'else'PENDING'
        if account:cf['STOPPED']=True
        qoff=8218*f.id+{'GetFileInformationByHandleEx':0,'GetFinalPathNameByHandleW':8,'GetFileSizeEx':8210}.get(c.api,0)if frame else 0
        error_id=0 if c.stopped and self.primary is not None and self._diagnostics else None
        r=dict(ordinal=index,file_id=f.id,api=c.api,record_version=1,flags=cf,requested=c.requested if c.requested is not None else 0,buffer_id=None if c.buffer is None else 0 if c.api=='ReadFile'else 1,phase='original_close'if c.api=='CloseHandle'else'binding_invoke',generation=c.generation or 0,buffer_written=c.buffer_written,scalar_atom=atom(scalar,scalar_tag),count_atom=atom(count,'COUNT32'),error_atom=atom(error,'DWORD'),error_definition_atom=atom(UNOBSERVED,'DEFINEDNESS')if error_definition is UNOBSERVED else dict(tag='DEFINEDNESS',value=error_definition),hashed_contribution=count if hash_return and defined else 0,captured_contribution=count if copy_return and defined else 0,known_count_contribution=count if defined else 0,query_offset=qoff,query_length=frame,input_handle_atom=atom(c.input_handle,'HANDLE'),pre_dispatch_clock=_clock_atom(c.pre_clock),post_binding_clock=_clock_atom(c.post_clock),error_id=error_id,path_id=f.id,fold_state=fold,buffer_state=c.buffer_state.upper())
        return tuple(r[k]for k in codec.CALL_KEYS)

    def _wire_source(self,phase):
        self.require_role1_representable()
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
            b=name.encode('ascii');names.append(b)
            self.require(all(n in module_ids or n in self._trusted_modules for n in rule.dependencies),'SOURCE_IMPORT_REFUSED')
            deps=tuple(module_ids[n]for n in rule.dependencies if n in module_ids)
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
        if type(kind)is not str or kind not in self._generated:raise K.KernelRefusal('UNISSUED_ARTIFACT')
        rec=self._generated[kind]
        if not rec['eligible']:raise K.KernelRefusal('UNISSUED_ARTIFACT')
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

    def _snapshot(self,finalized=False):
        projection=self._canonical_projection(include_calls=self.profile is PROFILE_N4);cs=projection['calls']
        plan=None if self._plan is None else dict(self._plan,calls_used=len(self.registry._calls),events_used=len(self.journal['events']),capture_used=self._capture_used,raw_storage_used=self._raw_used,raw_storage_peak=self._raw_peak,read_buffer_capacity=self._read_buffer.capacity if self._read_buffer else 0,read_generation=self._read_buffer._generation if self._read_buffer else 0,output_reserved_bytes=self._outputs['total_reserved_bytes'])
        return self._issue_snapshot(dict(schema_version=2,scope='entry_kernel_producer_seam',status=self._status,phase=self._phase,refusal_code=self._refusal,finalized=finalized,pure_seam_complete=self._terminal['pure_owner_ack'],origin=dict(start=self.origin.start,now=self.origin.now,work_end=self.origin.work_end,hard_end=self.origin.hard_end,clock_state=self.origin._state),plan=plan,files=projection['files'],calls=cs,api_counters=projection['api_counters'],byte_totals=projection['byte_totals'],early_context=self._context_report(self.early_context),evidence_context=self._context_report(self.evidence_context),loader=dict(bound=self._compiler is not None,attempted=list(self.loader.attempted),returned=list(self.loader.returned),cache_hits=list(self.loader.cache_hits),records=list(self.loader.records),declared_dependencies={name:list(rule.dependencies)for name,rule in self.loader.rules.items()},trusted_dependency_names=sorted(self._trusted_modules)),journal=dict(self.journal),outputs=dict(self._outputs),stages=list(self._stages),gates=list(self._gates),errors=dict(primary=self._diag(self.primary),secondary=[self._diag(e) for e in self._secondary]),terminal=dict(self._terminal),qualification=dict(QUALIFICATION),generated={k:dict(state=v['state'],eligible=v['eligible'],bytes=len(v['raw'])if v['raw']is not None else None,sha256=v['sha256'])for k,v in self._generated.items()},assembly_live=self._assembly_live,assembly_peak=self._assembly_peak),finalized=finalized)

_LATE_TABLE=MappingProxyType({name:getattr(_LateAlgorithms,name) for name in (
    'match_full_roster','hash_remaining','_packet','_publish','_make_report','_close',
    'finalize','_finish','_context_report','_wire_call','_wire_source','_consume_ledger',
    'freeze_generated','generated_bytes','generated_artifact','_install_generated',
    'check_generated','_snapshot')})

class OwnerOps:
    __slots__=('_view','_state','_attach_ref')
    def __init__(self,mint,view):
        need(mint is _OPS_MINT and type(view)is K.StateView,'FOREIGN_STATE')
        need(type(view.state)is K.KernelState and view.state.kernel_module is K,'FOREIGN_STATE')
        view.state.validate_state_view(view)
        object.__setattr__(self,'_view',view);object.__setattr__(self,'_state',view.state);object.__setattr__(self,'_attach_ref',attach)
    def __setattr__(self,name,value):raise TypeError('non-owning operations are read-only')
    @property
    def view(self):return self._view
    @property
    def state(self):return self._state
    @property
    def core(self):return self._state
    @property
    def owner(self):return self._state
    @property
    def kernel_module(self):return self._state.kernel_module
    @property
    def origin(self):return self._state.origin
    @property
    def nonce(self):return self._state.nonce
    @property
    def registry(self):return self._state.registry
    @property
    def raw_store(self):return self._state.raw_store
    @property
    def port(self):return self._state.port
    @property
    def sink(self):return self._state.sink
    @property
    def journal(self):return self._state.journal
    @property
    def loader(self):return self._state.loader
    @property
    def early_context(self):return self._state.early_context
    @property
    def evidence_context(self):return self._state.evidence_context
    @property
    def profile(self):return self._state.profile
    @property
    def primary(self):return self._state.primary
    @property
    def secondary(self):return self._state.secondary
    @property
    def finalized(self):return self._state.finalized
    def snapshot(self):return self._state.snapshot()
    def __getattr__(self,name):
        # A literal API set is independent of mutable module globals. The Core
        # resolves its retained function identities and validates namespace
        # integrity; it does not renew time or invalidate cached observations.
        if name in ('match_full_roster','hash_remaining','_packet','_publish',
            '_make_report','_close','finalize','_finish','_context_report',
            '_wire_call','_wire_source','_consume_ledger','freeze_generated',
            'generated_bytes','generated_artifact','_install_generated',
            'check_generated','_snapshot','check','file_ref','file_state',
            'exception_for_token','operation_guard','load_source'):
            return getattr(self._state,name)
        raise AttributeError(name)
    def continue_once(self,request,authority_factory,checker_factory):
        return continue_once(self._view,request,authority_factory,checker_factory)
    def __reduce_ex__(self,protocol):raise TypeError('OwnerOps is not serialized authority')

def attach(capsule):
    need(type(capsule)is K.KernelContinuation,'FOREIGN_STATE')
    view=capsule.claim_operations(attach)
    view.state.validate_state_view(view)
    ops=OwnerOps(_OPS_MINT,view)
    view.state.install_owner_ops(view,ops,_LATE_TABLE)
    return ops

@dataclass(frozen=True,slots=True)
class Request:
    output_key:str
    files:tuple
@dataclass(frozen=True,slots=True)
class TestAuthority:
    owner:object
    files:tuple
    checker_ids:tuple
@dataclass(frozen=True,slots=True)
class TestCheckerPorts:
    owner:object
    ids:tuple
    handlers:tuple
@dataclass(frozen=True,slots=True)
class TestObservation:
    context:object
    stage:str
    verdict:str
    evidence_paths:tuple
    detail:str=''
@dataclass(frozen=True,slots=True)
class TestAuthorityFactory:
    owner:object
    callback:object
    scope:str='SYNTHETIC_ONLY'
    def __call__(self):return self.callback()
@dataclass(frozen=True,slots=True)
class TestCheckerFactory:
    owner:object
    callback:object
    scope:str='SYNTHETIC_ONLY'
    def __call__(self):return self.callback()

def test_factories(state,authority_callback,checker_callback):
    need(type(state)is K.KernelState and callable(authority_callback) and callable(checker_callback))
    return TestAuthorityFactory(state,authority_callback),TestCheckerFactory(state,checker_callback)

def continue_once(claimed_view,request,test_authority_factory,test_checker_factory):
    need(type(claimed_view)is K.StateView,'FOREIGN_STATE')
    state=claimed_view.state
    need(type(state)is K.KernelState and state.kernel_module is K,'FOREIGN_STATE')
    state.validate_state_view(claimed_view)
    state._active();state.require(state._claimed and not state._engine_entered,'CONTINUATION_REPEATED')
    state._engine_entered=True;state._phase='CONTINUATION'
    try:
        state.check();state._live_early();state.require(type(request)is Request,'INVALID_INPUT')
        state.require(type(test_authority_factory)is TestAuthorityFactory and type(test_checker_factory)is TestCheckerFactory and test_authority_factory.owner is state and test_checker_factory.owner is state and test_authority_factory.scope=='SYNTHETIC_ONLY' and test_checker_factory.scope=='SYNTHETIC_ONLY','FOREIGN_STATE')
        def valid_authority(value):state.require(type(value)is TestAuthority and value.owner is state,'FOREIGN_STATE')
        authority=state.stage('authority_factory',test_authority_factory,valid_authority)
        def valid_checkers(value):
            state.require(type(value)is TestCheckerPorts and value.owner is state and type(value.ids)is tuple and value.ids==authority.checker_ids and type(value.handlers)is tuple and len(value.handlers)==4 and all(callable(h)for h in value.handlers),'CHECKER_BINDING_REFUSED')
            order=tuple(x[0]if type(x)is tuple and len(x)==2 else x for x in value.ids)
            state.require(order==CHECKS,'CHECKER_BINDING_REFUSED')
        checkers=state.stage('checker_factory',test_checker_factory,valid_checkers)
        state.stage('admit_reconcile',lambda:state.match_full_roster(request,authority))
        state.stage('hash_remaining',state.hash_remaining)
        for stage,handler in zip(CHECKS,checkers.handlers):
            state._phase='CHECKERS'
            def validate(observation,stage=stage):
                state.require(type(observation)is TestObservation and observation.context is state.evidence_context and type(observation.context)is K.CapturedContext and observation.context.owner is state and observation.stage==stage,'CHECKER_CONTEXT_REFUSED')
                state.require(observation.verdict in('consistent','negative') and(observation.verdict!='negative'or stage=='core')and type(observation.detail)is str and len(observation.detail)<=4096,'CHECKER_BINDING_REFUSED')
                state.require(type(observation.evidence_paths)is tuple and 0<len(observation.evidence_paths)<=state.profile.Nmax and len(set(observation.evidence_paths))==len(observation.evidence_paths)and all(p in state.evidence_context.blobs for p in observation.evidence_paths),'CHECKER_CONTEXT_REFUSED')
                state._negative=state._negative or observation.verdict=='negative';state.proof(stage)
            state.stage(stage,lambda handler=handler:handler(state.evidence_context),validate)
        state.stage('consistency',lambda:state.proof('consistency'))
    except BaseException as error:state.record_error(error,'continue_once')
    return state._finish(state.primary is None and tuple(state._gates)==GATES[:7])

def project_legacy(snapshot,*,check):
    need(callable(check));check()
    need(type(snapshot)is K.KernelSnapshot,'LEGACY_NOT_REPRESENTABLE')
    snapshot.require_role1_representable()
    if snapshot._profile is not PROFILE_N4:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    state=snapshot.owner_state;data=snapshot.to_dict()
    if set(data['loader'])!={'bound','attempted','returned','cache_hits','records'}:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    if data['calls']is None or any(not f['spec']['capture']for f in data['files']):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for diagnostic in(data['errors']['primary'],*data['errors']['secondary']):
        if diagnostic is not None and diagnostic['phase']not in LEGACY_PHASES:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    # No fallback role guess, prefix stripping or new-phase normalization.
    for f in data['files']:
        spec=state._specs[f['id']]
        if spec.legacy_role not in('software','owner_metadata','artifact'):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    data.pop('schema_version');data.pop('generated');data.pop('assembly_live');data.pop('assembly_peak');data['scope']='pure_shared_owner_seam'
    for f in data['files']:
        for key in('capture_state','hash_unknown','copy_unknown','read_generation'):f.pop(key,None)
        f['spec']['role']=state._specs[f['id']].legacy_role
        if f['handle_fact']['tag']=='UNENCODABLE_RAW':raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for c in data['calls']:
        if any(c[k]['tag']=='UNENCODABLE_RAW'for k in('raw_scalar','raw_count','raw_error')):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    result=LegacySnapshot(freeze(data));check();return result

LEGACY_PHASES=('binding_invoke','pre_dispatch','after_scalar_before_aux','after_scalar_before_right_transfer','error_copy','RawReturn_allocation','after_count_before_aux','buffer_copy','hash_update','post_call_clock','identity_query','handoff','close_wrapper','cleanup_publication','entry','bind_ports','bind_test_hooks','bind_test_compiler','admit_plan','reserve_output','capture_early','issue_continuation','claim_continuation','load_source','continue_once','finalize','journal_append','journal_close','publish_candidate','publish_cleanup','publish_failure','publish_receipt','publish_seal','original_close','diagnostic_format','final_clock','authority_factory','checker_factory','admit_reconcile','hash_remaining','archive','journal','resources','core','consistency','copy_bytes','before_final_ack')
