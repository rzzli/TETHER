"""Executable genuine-producer controls, prepared without subject execution.

Only the supplied fresh modules construct owners/refs/contexts/artifacts.
Expected bytes come from the frozen209B cohort and the periodic00..ff recipe.
"""
import copy
import hashlib
import struct
import time
import unittest

SEED=bytes(range(256))
SMALL_BULK_BYTES=2097169
SMALL_BULK_SHA256='6f8b1421035dcde6d517143914932e7996c17ae9a6c30042b1142b1b8b5f0557'


def reference_digest(size):
    """Independent small-fixture reference; never retains a whole bulk body."""
    h=hashlib.sha256();block=SEED*256;remaining=size
    while remaining:
        n=min(len(block),remaining);h.update(memoryview(block)[:n]);remaining-=n
    return h.hexdigest()


def make_tests(D,modules,fixture,public,cohort,validator,observations):
    S=modules['shared_owner_v1'];P=modules['shared_file_ports_v1'];C=modules['continue_verification_v1'];L=modules['role_ledger_codec_v1']
    def guard():
        if D.TEST_DEADLINE is None or time.monotonic()>=D.TEST_DEADLINE:raise TimeoutError('original extension suite deadline')
    def base_world(script=None,*,profile=None,reserve=True,capture=False,claim=False):
        w=D.Runtime(modules,fixture,public,cohort,script or dict(binding_overrides=[],callback_rules=[]))
        kw={} if profile is None else dict(profile=profile)
        D.invoke(S.start_injected,w.clock,w.setup,**kw)
        D.invoke(w.owner.admit_plan,w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules)
        if reserve:D.invoke(w.owner.reserve_output,fixture['common']['output_key'])
        if capture:D.invoke(w.owner.capture_early)
        token=continuation=None
        if claim:token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)
        return w,token,continuation
    def close(w):
        if not w.owner.finalized:D.invoke(w.owner.finalize,'incomplete')
        if w.violations:raise D.HarnessError('extension monitor violations:'+repr(w.violations))
    def legacy(w):
        issued=D.invoke(w.owner.snapshot)
        out=D.invoke(D.projected_snapshot(w,issued).to_dict)
        def identity(token):
            error=w.owner.exception_for_token(token)
            return error is w.owner.primary or any(error is x for x in w.owner.secondary)
        D.invoke(validator.validate_snapshot,out,diagnostic_identity_check=identity)
        return out
    def note(name,w,**extra):
        observations.append(dict(name=name,actual_original_dispatches=len(w.binding.records),
            actual_sink_callbacks=len(w.sink.records),violations=list(w.violations),
            original_primary_class=None if w.owner.primary is None else type(w.owner.primary).__name__,
            real_qualification=False,**extra))

    class VirtualBinding:
        """Original7 fake with real source-owned buffers; metadata logs only."""
        def __init__(self,w,chunk):
            self.w=w;self.chunk=chunk;self.records=[];self.actual_refs=[];self.delivered=[0]*len(w.blobs)
            self.close_counts={};self.known_handles=set();self.read_completions=0;self.read_buffer=None
        def invoke(self,ref,args,hooks):
            w=self.w;i=ref.file_ref.id;api=ref.api
            record=dict(api=api,file_id=i,arguments=copy.deepcopy(args),wrapper_returned=False)
            self.records.append(record);self.actual_refs.append(ref)
            if type(i) is not int or not 0<=i<len(w.blobs):w.violate('foreign virtual file ordinal')
            if ref.file_ref is not w.owner.file_ref(w.blobs[i]['path']):w.violate('noncanonical virtual file ref')
            if api not in D.API:w.violate('inactive virtual API')
            if w.clock.value>=400:w.violate('virtual binding after original hard cutoff')
            if w.owner.primary is not None and api!='CloseHandle':w.violate('virtual new work after primary')
            b=w.blobs[i];handle=100+i
            expected={
                'CreateFileW':dict(path=b['path'],desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None),
                'GetFileType':dict(handle=handle),
                'GetFileInformationByHandleEx':dict(handle=handle,info_class=9,buffer_bytes=8),
                'GetFinalPathNameByHandleW':dict(handle=handle,capacity=4101,flags=0),
                'GetFileSizeEx':dict(handle=handle),
                'ReadFile':dict(handle=handle,requested=min(self.chunk,b['bytes']-self.delivered[i]),overlapped=None),
                'CloseHandle':dict(handle=handle)}[api]
            if not D.same(args,expected):w.violate('virtual argument mismatch against independent metadata')
            if api=='CreateFileW':
                self.known_handles.add(handle);hooks.store_scalar(ref,handle)
            elif api=='GetFileType':hooks.store_scalar(ref,1)
            elif api in ('GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx'):
                if api=='GetFileInformationByHandleEx':data=struct.pack('<II',0x80,0);scalar=1
                elif api=='GetFileSizeEx':data=struct.pack('<q',b['bytes']);scalar=1
                else:
                    text=('\\\\?\\'+b['path']).encode('utf-16-le');scalar=len(text)//2
                    data=text+b'\0\0'+bytes(8202-len(text)-2)
                hooks.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,data);hooks.store_scalar(ref,scalar)
            elif api=='ReadFile':
                n=expected['requested']
                if n<=0:w.violate('virtual extra read after all declared bytes')
                if ref.requested!=n:w.violate('virtual CallRef request differs from independent remaining')
                if self.read_buffer is None:self.read_buffer=ref.buffer_ref
                elif ref.buffer_ref is not self.read_buffer:w.violate('virtual read buffer identity replaced')
                if ref.buffer_generation!=self.read_completions:w.violate('virtual read generation differs from own completed-read count')
                if b['role']=='hash_only_bulk':
                    first=SEED[:min(256,n)]
                    hooks.buffer_write_slice(ref,ref.buffer_ref,ref.buffer_generation,0,first)
                    written=len(first)
                    while written<n:
                        k=min(written,n-written)
                        hooks.buffer_copy_within(ref,ref.buffer_ref,ref.buffer_generation,0,k);written+=k
                else:
                    body=bytes.fromhex(b['utf8_hex']);part=body[self.delivered[i]:self.delivered[i]+n]
                    hooks.buffer_write_slice(ref,ref.buffer_ref,ref.buffer_generation,0,part)
                hooks.store_scalar(ref,1);hooks.store_count(ref,n)
                self.delivered[i]+=n;self.read_completions+=1
            else:
                if handle not in self.known_handles:w.violate('virtual guessed closer')
                self.close_counts[i]=self.close_counts.get(i,0)+1
                if self.close_counts[i]!=1:w.violate('virtual duplicate close')
                hooks.store_scalar(ref,1)
            record['wrapper_returned']=True
            return None

    class VirtualWorld(D.Runtime):
        def __init__(self,blobs,profile,*,inspect_artifacts=False):
            super().__init__(modules,fixture,public,dict(blobs=blobs),dict(binding_overrides=[],callback_rules=[]))
            self.profile=profile;self.inspect_artifacts=inspect_artifacts;self.artifacts={};self.consumption=[]
        def setup(self,owner):
            self.owner=owner
            self.specs=tuple(S.FileSpec(b['path'],b['role'] if b['role']=='hash_only_bulk' else D.subject_role(b['role']),
                b['bytes'],b['sha256'],b['capture'],legacy_role=b['role'] if self.profile==S.PROFILE_N4 and b['role'] in ('software','owner_metadata','artifact') else None) for b in self.blobs)
            self.rules=(S.ModuleRule('cohort_leaf',self.blobs[0]['path'],(),False),S.ModuleRule('cohort_entry',self.blobs[1]['path'],('cohort_leaf',),False))
            self.binding=VirtualBinding(self,1048576 if self.profile==S.PROFILE_ORIGINAL7_1M else 65536)
            self.view=P.FilePortView(owner,self.binding);self.sink=D.SinkSpy(self)
            owner.bind_ports(self.view,self.sink);owner.bind_test_hooks(S.TestHooks(owner,self.hook));owner.bind_test_compiler(self.compiler,stdlib=())
            return owner
        def callback_actions(self,target,call_ref=None):
            if self.inspect_artifacts and target in ('publish_candidate','publish_cleanup'):
                kind='candidate-ledger.bin' if target=='publish_candidate' else 'terminal-ledger.bin'
                artifact=self.owner.generated_artifact(kind);raw=self.owner.generated_bytes(kind)
                if artifact.raw is not raw:self.violate('generated getter copied/replaced actual issued bytes')
                if any(getattr(artifact,k) is not getattr(self.owner,k) for k in ('origin','nonce','registry')) or artifact.owner is not self.owner:self.violate('generated artifact issuer identity lost')
                expected_calls=5*len(self.blobs)+sum((b['bytes']+self.binding.chunk-1)//self.binding.chunk for b in self.blobs if b['bytes'])
                if target=='publish_cleanup':expected_calls+=len(self.blobs)
                pools=dict(queries=b''.join(self.query_frame(b) for b in self.blobs),paths=b''.join(b['path'].encode() for b in self.blobs),module_names=b'cohort_leafcohort_entry')
                fixed_expected=dict(files=len(self.blobs),calls=expected_calls,modules=2,diagnostics=0,module_edges=1)
                counts={};pool_bytes={};passes=[];entered=[0];exhausted=[0];original=L.iter_checked_records
                def observed(actual_raw,*,check):
                    if actual_raw is not raw:self.violate('consumer parsed different bytes')
                    entered[0]+=1;this_pass={}
                    for row_kind,index,value in original(actual_raw,check=check):
                        counts[row_kind]=counts.get(row_kind,0)+1
                        this_pass[row_kind]=this_pass.get(row_kind,0)+1
                        if row_kind in pools:
                            if type(value) is not memoryview or value.nbytes!=len(pools[row_kind]) or hashlib.sha256(value).digest()!=hashlib.sha256(pools[row_kind]).digest():self.violate('consumer pool bytes incomplete/different')
                            pool_bytes[row_kind]=value.nbytes
                        yield row_kind,index,value
                    exhausted[0]+=1;passes.append(this_pass)
                L.iter_checked_records=observed
                try:seen=D.invoke(self.owner.check_generated,artifact)
                finally:L.iter_checked_records=original
                if seen is not artifact or entered[0]<1 or exhausted[0]!=entered[0]:self.violate('actual full consumer pass was not exhausted')
                for one in passes:
                    if one.get('header')!=1:self.violate('consumer missing actual header')
                    for k,n in fixed_expected.items():
                        if one.get(k,0)!=n:self.violate('consumer fixed table/edge rows incomplete')
                    if any(one.get(k)!=1 for k in pools):self.violate('consumer omitted/repeated a pool within one pass')
                if pool_bytes!={k:len(v) for k,v in pools.items()}:self.violate('consumer did not visit all pool bytes')
                self.artifacts[kind]=artifact;self.consumption.append(dict(kind=kind,phase=artifact.phase,raw_bytes=len(raw),sha256=artifact.sha256,counts=counts,pool_bytes=pool_bytes,complete_passes=entered[0],exhausted=True))
            return super().callback_actions(target,call_ref)
        @staticmethod
        def query_frame(b):
            fp=('\\\\?\\'+b['path']).encode('utf-16-le')+b'\0\0'
            return struct.pack('<II',0x80,0)+fp+bytes(8202-len(fp))+struct.pack('<q',b['bytes'])

    def virtual_blobs(*,bulk_size,empty_metadata=False):
        if bulk_size not in (0,SMALL_BULK_BYTES):raise ValueError('closed small-fixture sizes only')
        expected=hashlib.sha256(b'').hexdigest() if bulk_size==0 else SMALL_BULK_SHA256
        assert reference_digest(bulk_size)==expected
        blobs=copy.deepcopy(cohort['blobs'])
        if empty_metadata:
            blobs[2].update(bytes=0,utf8_hex='',sha256=hashlib.sha256(b'').hexdigest())
        blobs.append(dict(id='virtual_bulk',path='D:\\RoleAwareSmall\\bulk.bin',role='hash_only_bulk',bytes=bulk_size,
            sha256=expected,capture=False,utf8_hex=''))
        return blobs
    def virtual_world(blobs,profile,*,artifacts=False,run=True):
        w=VirtualWorld(blobs,profile,inspect_artifacts=artifacts)
        D.invoke(S.start_injected,w.clock,w.setup,profile=profile)
        D.invoke(w.owner.admit_plan,w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules)
        if run:
            D.invoke(w.owner.reserve_output,fixture['common']['output_key']);D.invoke(w.owner.capture_early)
            token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)
            loaded=D.invoke(w.owner.load_source,'cohort_entry');D.invoke(w.owner.check)
            if D.invoke(loaded.run)!=('cohort-entry-v1','cohort-leaf-v1'):w.violate('actual small marker functions differ')
            D.invoke(w.owner.check)
            D.invoke(C.continue_once,continuation,C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))
        return w

    class ProducerExtensions(unittest.TestCase):
        def test01_captured_empty_bulk_empty_and_typed_no_bytes(self):
            guard();w=virtual_world(virtual_blobs(bulk_size=0,empty_metadata=True),S.PROFILE_N4,run=False)
            held_ref=D.invoke(w.owner.file_ref,w.blobs[3]['path']);held_state=D.invoke(w.owner.file_state,held_ref)
            D.invoke(w.owner.reserve_output,fixture['common']['output_key']);D.invoke(w.owner.capture_early)
            token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)
            loaded=D.invoke(w.owner.load_source,'cohort_entry');D.invoke(w.owner.check)
            self.assertEqual(D.invoke(loaded.run),('cohort-entry-v1','cohort-leaf-v1'));D.invoke(w.owner.check)
            D.invoke(C.continue_once,continuation,C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))
            try:
                context=w.owner.evidence_context
                self.assertIsNotNone(context);self.assertEqual(len(context.specs),4);self.assertEqual(len(context.digests),4)
                self.assertEqual(context.bytes_for(w.blobs[2]['path']),b'')
                self.assertNotIn(w.blobs[3]['path'],context.blobs)
                with self.assertRaises(S.CaptureNotRequested):context.bytes_for(w.blobs[3]['path'])
                raw=D.invoke(w.owner.snapshot).to_dict();captured=raw['files'][2];bulk=raw['files'][3]
                self.assertEqual((captured['capture_state'],captured['capture_complete'],captured['captured_bytes']),('COMPLETE',True,0))
                self.assertEqual((bulk['capture_state'],bulk['capture_complete'],bulk['captured_bytes'],bulk['hash_complete']),('NOT_REQUESTED',False,0,True))
                self.assertIs(held_ref._state,held_state);self.assertIs(w.owner.file_ref(w.blobs[3]['path']),held_ref)
                state=held_state
                self.assertIsNone(state.assembly);self.assertIsNone(state.blob)
                with self.assertRaises(S.SharedOwnerError) as misuse:D.invoke(w.owner.file_state,held_ref)
                self.assertEqual(misuse.exception.code,'FINALIZED_MISUSE')
                self.assertEqual(w.binding.delivered,[58,83,0,0]);self.assertEqual(sum(x['api']=='ReadFile' for x in w.binding.records),2)
                self.assertEqual(len(w.binding.records),26);self.assertEqual(w.binding.close_counts,{0:1,1:1,2:1,3:1})
                note('capture_zero_vs_not_requested',w,captured=141,bulk=0,read_calls=2)
            finally:close(w)

        def test02_first_NULL_and_unencodable_raw_object_survive(self):
            class Opaque:
                def __deepcopy__(self,memo):return self
            for value in (None,Opaque()):
                guard();actions=[dict(hook='store_scalar',value=value)]
                if value is None:actions.append(dict(hook='raise_exception',exception='err0',phase='after_scalar_before_aux'))
                override=dict(api='CreateFileW',file_id=0,occurrence=1,actions=actions,**{'return':'throw_original' if value is None else 'normal_None'})
                w,_,_=base_world(dict(binding_overrides=[override],callback_rules=[]))
                try:
                    with self.assertRaises(BaseException):D.invoke(w.owner.capture_early)
                    state=w.binding.actual_refs[0]._state
                    self.assertIs(state.scalar,value);self.assertFalse(any(r['api']=='CloseHandle' and r['file_id']==0 for r in w.binding.records))
                    if value is None:self.assertIs(w.owner.primary,w.errors['err0'])
                    else:
                        self.assertIsNotNone(w.owner.primary)
                        issued=D.invoke(w.owner.snapshot);self.assertIs(type(issued),S.ProducerSnapshot)
                        try:D.projected_snapshot(w,issued)
                        except (S.SharedOwnerError,L.FormatError) as error:self.assertEqual(error.code,'LEGACY_NOT_REPRESENTABLE')
                        else:self.fail('unencodable original raw object fabricated a legacy value')
                    note('first_null' if value is None else 'first_unencodable_object',w,raw_object_identity_retained=True,guessed_close=False)
                finally:close(w)

        def test03_independent_error_definition_and_value_first_slots(self):
            for mode in ('definition_first','value_first'):
                guard();actions=[dict(hook='store_scalar',value=0),dict(hook='store_count',value=0),dict(hook='store_error',value=0,defined=True)]
                rule=dict(api='ReadFile',file_id=0,occurrence=1,actions=actions,**{'return':'normal_None'})
                w,_,_=base_world(dict(binding_overrides=[rule],callback_rules=[]));error=MemoryError('independent error transport stop')
                original_invoke=w.binding.invoke
                class Delivery:
                    def __init__(self,actual):self.actual=actual
                    def __getattr__(self,key):return getattr(self.actual,key)
                    def store_error(self,ref,value,defined):
                        if mode=='definition_first':self.actual.store_error_definition(ref,defined)
                        else:self.actual.store_error_value(ref,value)
                        raise error
                def invoke(ref,args,hooks):return original_invoke(ref,args,Delivery(hooks))
                w.binding.invoke=invoke
                try:
                    with self.assertRaises(BaseException) as caught:D.invoke(w.owner.capture_early)
                    self.assertIs(caught.exception,error);self.assertIs(w.owner.primary,error)
                    call=next(r for r in w.binding.actual_refs if r.api=='ReadFile')._state
                    self.assertEqual((call.scalar,call.count),(0,0))
                    self.assertIs(call.error_definition,True if mode=='definition_first' else S.UNOBSERVED)
                    self.assertIs(call.error,S.UNOBSERVED) if mode=='definition_first' else self.assertEqual(call.error,0)
                    self.assertIs(call.error_defined,mode=='definition_first')
                    note(mode,w,raw_count_zero_undefined=True,definition_observed=mode=='definition_first',error_value_observed=mode=='value_first')
                finally:close(w)

        def test04_actual_packing_failure_preserves_canonical_facts(self):
            guard();w,_,continuation=base_world(capture=True,claim=True)
            loaded=D.invoke(w.owner.load_source,'cohort_entry');D.invoke(w.owner.check)
            self.assertEqual(D.invoke(loaded.run),('cohort-entry-v1','cohort-leaf-v1'));D.invoke(w.owner.check)
            error=MemoryError('actual call-row packing failure');original=L.pack_row_tuple_into;hits=[]
            def failed(dst,offset,kind,fields):
                if kind=='calls':hits.append(offset);raise error
                return original(dst,offset,kind,fields)
            L.pack_row_tuple_into=failed
            try:
                try:D.invoke(C.continue_once,continuation,C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))
                except BaseException as caught:self.assertIs(caught,error)
            finally:L.pack_row_tuple_into=original
            try:
                self.assertTrue(hits);self.assertIs(w.owner.primary,error)
                issued=D.invoke(w.owner.snapshot);self.assertIs(type(issued),S.ProducerSnapshot);self.assertIs(issued.owner,w.owner)
                raw=D.invoke(issued.to_dict);self.assertFalse(raw['pure_seam_complete'])
                self.assertEqual(raw['schema_version'],2);self.assertEqual(raw['errors']['primary']['phase'],'freeze')
                self.assertIs(w.owner.exception_for_token(raw['errors']['primary']['identity']),error)
                with self.assertRaises(L.FormatError) as refused:D.projected_snapshot(w,issued)
                self.assertEqual(refused.exception.code,'LEGACY_NOT_REPRESENTABLE')
                self.assertIs(w.owner.primary,error);self.assertTrue(D.same(raw,D.invoke(issued.to_dict)))
                self.assertEqual((raw['byte_totals']['known_read_bytes'],raw['byte_totals']['hashed_bytes'],raw['byte_totals']['captured_bytes']),(209,209,209))
                self.assertTrue(all(f['close_invocations']==1 for f in raw['files']))
                self.assertEqual(w.sink.kind_counts['receipt'],0);self.assertEqual(w.sink.kind_counts['seal'],0)
                with self.assertRaises(S.SharedOwnerError):D.invoke(w.owner.generated_bytes,'candidate-ledger.bin')
                self.assertIs(w.owner.primary,error)
                note('packing_failed_after_first_raw_facts',w,known=209,hashed=209,captured=209,packing_attempts=len(hits),retry_or_eligible_bytes=False)
            finally:close(w)

        def test05_actual_diagnostic_borrow_release_and_formatter_identity(self):
            guard();w,_,_=base_world(reserve=False)
            try:
                self.assertEqual((w.owner._diag_capacity,w.owner._diag_committed,w.owner._diag_borrowed),(506,0,0))
                for i in range(16384):
                    if i%256==0:guard()
                    with w.owner.operation_guard():
                        self.assertEqual(w.owner._diag_borrowed,2)
                        with w.owner.operation_guard():self.assertEqual(w.owner._diag_borrowed,2)
                    self.assertEqual((w.owner._diag_borrowed,w.owner._diag_committed),(0,0))
                error=RuntimeError('first actual diagnostic failure')
                with self.assertRaises(BaseException) as caught:
                    with w.owner.operation_guard():raise error
                self.assertIs(caught.exception,error);self.assertIs(w.owner.primary,error)
                self.assertEqual((w.owner._diag_committed,w.owner._diag_borrowed),(1,0))
                raw=legacy(w);token=raw['errors']['primary']['identity'];self.assertIs(w.owner.exception_for_token(token),error)
                note('diagnostic_reusable_guards',w,outer_successful_guard_operations=16384,nested_successful_entries=16384,capacity=506,committed_after_failure=1,borrowed=0)
                self.assertEqual((len(w.binding.records),len(w.sink.records)),(0,0))
            finally:close(w)
            w,_,_=base_world(reserve=False);formatter=MemoryError('original formatter object')
            class BadText(RuntimeError):
                def __str__(self):raise formatter
            error=BadText('source primary before formatter')
            try:
                with self.assertRaises(BaseException) as caught:
                    with w.owner.operation_guard():raise error
                self.assertIs(caught.exception,error);self.assertIs(w.owner.primary,error)
                self.assertTrue(any(x is formatter for x in w.owner.secondary))
                self.assertEqual((w.owner._diag_committed,w.owner._diag_borrowed),(2,0))
                issued=D.invoke(w.owner.snapshot);projected=D.projected_snapshot(w,issued);before=projected.to_dict();error.args=('changed after issuance',)
                self.assertTrue(D.same(before,projected.to_dict()));self.assertIs(w.owner.primary,error)
                note('formatter_original_identity',w,committed=2,borrowed=0,primary_is_original=True,secondary_formatter_is_original=True)
            finally:close(w)

        def test06_genuine_immutable_artifacts_full_consumer_and_foreign_refusal(self):
            guard();w=virtual_world(copy.deepcopy(cohort['blobs']),S.PROFILE_N4,artifacts=True)
            try:
                self.assertEqual(set(w.artifacts),{'candidate-ledger.bin','terminal-ledger.bin'})
                a=w.artifacts['candidate-ledger.bin'];b=w.artifacts['terminal-ledger.bin']
                self.assertIsNot(a,b);self.assertIsNot(a.raw,b.raw)
                self.assertEqual(hashlib.sha256(a.raw).hexdigest(),a.sha256);self.assertEqual(hashlib.sha256(b.raw).hexdigest(),b.sha256)
                self.assertNotEqual(a.raw,b.raw)
                self.assertIs(w.owner.generated_bytes(a.kind),a.raw);self.assertIs(w.owner.generated_artifact(a.kind),a)
                for key in ('raw','owner','origin','nonce','registry','kind','phase','sha256'):
                    with self.assertRaises((AttributeError,TypeError)):setattr(a,key,getattr(a,key))
                with self.assertRaises(S.SharedOwnerError):D.invoke(w.owner.check_generated,a)
                note('actual_generated_bytes_and_full_consumer',w,consumption=w.consumption,postfinal_consumer_refused=True)
                other,_,_=base_world(reserve=False)
                try:
                    before=legacy(other)
                    with self.assertRaises(S.SharedOwnerError):D.invoke(other.owner.check_generated,a)
                    after=legacy(other)
                    self.assertEqual(after['gates'],before['gates']);self.assertFalse(after['pure_seam_complete'])
                    self.assertEqual((len(other.binding.records),len(other.sink.records)),(0,0))
                    note('foreign_genuine_artifact_refused',other,wrong_owner=True,no_gate_or_dispatch=True)
                finally:close(other)
            finally:close(w)

        def test07_small_real_multichunk_hash_only_stream_and_209_capture(self):
            guard();prepared=time.monotonic();blobs=virtual_blobs(bulk_size=2*1048576+17)
            preparation_seconds=time.monotonic()-prepared
            w=virtual_world(blobs,S.PROFILE_ORIGINAL7_1M,artifacts=True,run=False)
            held_ref=D.invoke(w.owner.file_ref,w.blobs[3]['path']);held_state=D.invoke(w.owner.file_state,held_ref)
            D.invoke(w.owner.reserve_output,fixture['common']['output_key']);D.invoke(w.owner.capture_early)
            token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)
            loaded=D.invoke(w.owner.load_source,'cohort_entry');D.invoke(w.owner.check)
            self.assertEqual(D.invoke(loaded.run),('cohort-entry-v1','cohort-leaf-v1'));D.invoke(w.owner.check)
            D.invoke(C.continue_once,continuation,C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))
            try:
                self.assertEqual(w.binding.delivered,[58,83,68,2097169])
                self.assertEqual((len(w.binding.records),w.binding.read_completions),(30,6))
                self.assertEqual(w.binding.close_counts,{0:1,1:1,2:1,3:1})
                raw=D.invoke(w.owner.snapshot).to_dict()
                self.assertEqual((raw['byte_totals']['known_read_bytes'],raw['byte_totals']['hashed_bytes'],raw['byte_totals']['captured_bytes']),(2097378,2097378,209))
                self.assertTrue(raw['pure_seam_complete'])
                ctx=w.owner.evidence_context
                self.assertEqual(len(ctx.specs),4);self.assertEqual(len(ctx.digests),4);self.assertEqual(len(ctx.blobs),3)
                self.assertIs(ctx.owner,w.owner);self.assertIs(ctx.nonce,w.owner.nonce);self.assertIs(ctx.early_context,w.owner.early_context)
                for b in blobs[:3]:self.assertEqual(ctx.bytes_for(b['path']),bytes.fromhex(b['utf8_hex']))
                for b in blobs[:2]:self.assertIs(ctx.bytes_for(b['path']),w.owner.early_context.bytes_for(b['path']))
                self.assertIs(held_ref._state,held_state);self.assertIs(w.owner.file_ref(blobs[3]['path']),held_ref)
                bulk=held_state
                self.assertIsNone(bulk.assembly);self.assertIsNone(bulk.blob);self.assertEqual(bulk.capture_state,'NOT_REQUESTED')
                with self.assertRaises(S.SharedOwnerError) as misuse:D.invoke(w.owner.file_state,held_ref)
                self.assertEqual(misuse.exception.code,'FINALIZED_MISUSE')
                with self.assertRaises(S.CaptureNotRequested):ctx.bytes_for(blobs[3]['path'])
                self.assertEqual(raw['files'][3]['actual_sha256'],blobs[3]['sha256'])
                self.assertTrue(all(x is False for x in raw['qualification'].values()))
                note('small_actual_1MiB_periodic_stream',w,reference_preparation_seconds=preparation_seconds,
                    virtual_bytes=2097378,captured=209,bulk=2097169,original_calls=30,reads=6,closures=4,
                    recipe='periodic00..ff reset perfile;256B seed thenactualbuffer doubling; no wholebulk body',consumption=w.consumption)
            finally:close(w)
    return ProducerExtensions
