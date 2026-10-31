"""One frozen E08/Source4 source/pure suite; Root binding required.

Importing this runner imports no subject. Deferred/metadata-only assertions
never become whole-entry acceptance. All persistence happens outside ACTIVE;
it reads already retained state, never repairs or resamples a source owner.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import types

HERE=Path(__file__).resolve().parent
BINDING=HERE/'ENTRY-E08-SUITE-BINDING-v1.json'
ATTEMPT=HERE/'ENTRY-E08-SUITE-ATTEMPT-v1.json'
PROOF=HERE/'ENTRY-E08-SUITE-PROOF-v1.json'
ARTIFACTS=HERE/'ENTRY-E08-SUITE-ARTIFACTS-v1'
AXES=('scalar','count','error_value','error_definition')
AXIS_OFFSETS=(128,160,192,224)
KIND_NAMES={1:'HANDLE64',2:'BOOL32_BITS',3:'DWORD32',4:'COUNT32',5:'DEFINEDNESS'}


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read_exact(value):
    raw=Path(value['path']).resolve().read_bytes()
    if len(raw)!=value['bytes'] or hashlib.sha256(raw).hexdigest()!=value['sha256']:
        raise RuntimeError('changed frozen input: '+value['path'])
    return raw


def save_new(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode()
    with path.open('xb')as stream:stream.write(raw)
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def trusted_module(name,value):
    module=types.ModuleType(name);module.__file__=str(Path(value['path']).resolve())
    sys.modules[name]=module
    exec(compile(read_exact(value),module.__file__,'exec'),module.__dict__)
    return module


def error_data(error):
    if error is None:return None
    try:
        args=[]
        for value in error.args[:8]:
            if type(value)is str:args.append(value[:512])
            elif value is None or type(value)is bool or type(value)is int:args.append(value)
            else:args.append(dict(type=type(value).__name__[:128]))
        frames=[];tb=error.__traceback__
        while tb is not None and len(frames)<64:
            frames.append(dict(file=tb.tb_frame.f_code.co_filename,line=tb.tb_lineno,function=tb.tb_frame.f_code.co_name))
            tb=tb.tb_next
        code=getattr(error,'code',None)
        return dict(type=type(error).__module__+'.'+type(error).__qualname__,code=code if type(code)is str else None,args=args,frames=frames)
    except BaseException as formatting:
        return dict(type=type(error).__name__,formatting_failed=True,format_error_type=type(formatting).__name__)


def clock_fact(value,sentinel):
    if value is sentinel:return dict(tag='UNOBSERVED',value=None,bits_hex=None)
    if type(value)is float:
        return dict(tag='F64',value=value if math.isfinite(value)else None,bits_hex=struct.pack('<d',value).hex(),finite=math.isfinite(value))
    if type(value)is int and -(1<<63)<=value<(1<<63):
        return dict(tag='I64',value=value,bits_hex=struct.pack('<q',value).hex())
    if type(value)is bool:return dict(tag='BOOL_INVALID',value=value,bits_hex=None)
    if value is None:return dict(tag='NULL_INVALID',value=None,bits_hex=None)
    return dict(tag='UNENCODABLE_INVALID',value=None,bits_hex=None,type=type(value).__name__[:128])


class Sanitizer:
    """Data-only labels for retained opaque identities, never subject inputs."""
    def __init__(self,sentinel):self.sentinel=sentinel;self.opaque={}
    def value(self,value):
        if value is self.sentinel:return dict(tag='UNOBSERVED')
        if value is None or type(value)is bool or type(value)is int:return value
        if type(value)is str:return value
        if type(value)is float:return value if math.isfinite(value)else clock_fact(value,self.sentinel)
        if type(value)is bytes:return dict(bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
        if type(value)is dict or type(value)is types.MappingProxyType:
            return {key:self.value(v)for key,v in value.items()}
        if type(value)is list or type(value)is tuple:return [self.value(v)for v in value]
        if isinstance(value,BaseException):return error_data(value)
        key=id(value)
        if key not in self.opaque:self.opaque[key]='opaque_'+str(len(self.opaque))
        return dict(tag='OPAQUE_IDENTITY_DATA_ONLY',identity=self.opaque[key],type=type(value).__name__[:128])


def decode_axis(raw):
    bits,epoch,kind,width,padding,stage,commit,tail=struct.unpack('<QIHBBIIQ',raw)
    valid=(kind in KIND_NAMES and epoch==1 and padding==0 and tail==0 and stage in(0,1)and commit in(0,1)and(not commit or stage))
    name=KIND_NAMES.get(kind)
    valid=valid and width==(8 if name=='HANDLE64'else 1 if name=='DEFINEDNESS'else 4)
    valid=valid and bits<(1<<(8*width)) and(name!='DEFINEDNESS'or bits in(0,1))
    native='COMMITTED'if commit else'STAGED_UNCOMMITTED'if stage else'UNOBSERVED'
    known=None
    if valid and commit:
        known=bool(bits)if name=='DEFINEDNESS'else bits-(1<<32)if name=='BOOL32_BITS'and bits&(1<<31)else bits
    return dict(layout_valid=bool(valid),native_state=native if valid else'INVALID_LAYOUT',kind=name,width=width,epoch=epoch,stage_hint=stage,commit=commit,raw_payload_bits=bits,known_value=known)


def write_bytes(name,raw):
    if type(raw)is not bytes:raise TypeError('existing immutable source bytes required')
    path=ARTIFACTS/name
    with path.open('xb')as stream:stream.write(raw)
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),persistence='HARNESS_COPY_OUTSIDE_ACTIVE')


def retain_world(world,prefix):
    """Read cached/registered facts only; no source method or resnapshot."""
    K=world.K;s=world.state if world.state is not None else world.attempt.state
    clean=Sanitizer(K.UNOBSERVED)
    result=dict(actual_entry_attempts=int(world.attempt.attempted),first_clock=clock_fact(world.attempt.start_cell,K.UNOBSERVED),attempt_error=error_data(world.attempt.error),core_present=s is not None,full_geometry=world.geometry,actual_original_calls=list(world.originals.calls),original_events=clean.value(world.events),compiler_callbacks=list(world.loader.compiler_observations),output_callbacks=list(world.output.callbacks),open_attempts=dict(world.originals.open_attempts),close_attempts=dict(world.originals.close_attempts),delivered_bytes=dict(world.originals.delivered),source_identity_comparison_available=False,source_identity_stable=None,source_identity_comparison_reason='ENTRY_DID_NOT_RETURN_A_BASELINE_IDENTITY_TUPLE',artifacts=[])
    result['geometry_scope']=getattr(world,'geometry_scope','ACTUAL_HELPER_FIXTURE_PLAN')
    result['base_fixture_geometry']=getattr(world,'base_fixture_geometry',None)
    result['policy_entry_basis_pins']=getattr(world,'policy_entry_basis_pins',None)
    result['policy_only']=world.policy_only
    result['policy_entry_error']=error_data(world.policy_entry_error)
    if s is None:return result
    result['original_primary']=error_data(s._primary)
    result['secondary_errors']=[error_data(e)for e in s._secondary]
    prepared_policy=s._manifest_policy_prepared
    issued_policy=s._manifest_policy_report
    result['policy_observation']=dict(
        attempted=s._manifest_policy_attempted,
        captured_binding=clean.value(s._manifest_policy_binding_data),
        captured_envelope=clean.value(s._manifest_policy_envelope_data),
        prepared_report=None if prepared_policy is None else clean.value(prepared_policy._data),
        issued_report=None if issued_policy is None else clean.value(issued_policy._data),
        prepared_and_issued_same_object=None if prepared_policy is None or issued_policy is None else prepared_policy is issued_policy,
        execution_eligible=s._manifest_policy_eligible,
        original_error=error_data(s._manifest_policy_error),
        selected_original_binding=s._manifest_policy_binding is s._services.manifest_policy_binding)
    result['origin']=dict(start=clock_fact(s._origin._start,K.UNOBSERVED),latest=clock_fact(s._origin._clock_carrier.value,K.UNOBSERVED),now=clock_fact(s._origin._now,K.UNOBSERVED),state=s._origin._state)
    result['current_call_count']=len(s._registry._calls)
    if world.identities is not None:
        result['source_identity_comparison_available']=True
        result['source_identity_stable']=all(a is b for a,b in zip(world.identities,(s,s._origin,s._nonce,s._registry,s._raw_store,s._port,s._sink,s._loader,s._journal)))
        result['source_identity_comparison_reason']=None
    observed=world.first_snapshot;prepared=s._final
    result['wrapper_snapshot_observed']=observed is not None
    result['source_final_prepared']=prepared is not None
    snapshots=[]
    for label,snapshot in(('first_wrapper_observed',observed),('source_cached_final',prepared)):
        if snapshot is None:continue
        genuine=type(snapshot)is K.KernelSnapshot and snapshot._owner is s
        if not genuine:raise RuntimeError('foreign cached snapshot evidence')
        if snapshots and snapshot is observed and prepared is observed and label=='source_cached_final':
            result['same_snapshot_object']=True;continue
        snapshots.append((label,snapshot))
        metadata=dict(label=label,genuine_source_snapshot=True,partial_capture=snapshot._partial,copied_native_bytes=snapshot._copy_bytes,raw_call_count=len(snapshot._raw_calls),capture_error=error_data(snapshot._capture_error),data=clean.value(snapshot._data))
        copied_path=ARTIFACTS/(prefix+'.'+label+'.native-rows.bin')
        copied_meta_path=ARTIFACTS/(prefix+'.'+label+'.native-rows.jsonl')
        copied_hash=hashlib.sha256();copied_meta_hash=hashlib.sha256();copied_bytes=copied_meta_bytes=0
        with copied_path.open('xb')as copied_stream,copied_meta_path.open('xb')as copied_meta_stream:
            for index,copied in enumerate(snapshot._raw_calls):
                raw=copied._raw
                if type(raw)is not bytes or len(raw)!=256:raise RuntimeError('existing snapshot raw row size')
                copied_stream.write(raw);copied_hash.update(raw);copied_bytes+=len(raw)
                record=dict(index=index,axes={name:decode_axis(raw[offset:offset+32])for name,offset in zip(AXES,AXIS_OFFSETS)},facts=clean.value(copied._facts))
                encoded=(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
                copied_meta_stream.write(encoded);copied_meta_hash.update(encoded);copied_meta_bytes+=len(encoded)
        metadata['immutable_raw_artifacts']=[dict(path=str(copied_path.resolve()),bytes=copied_bytes,sha256=copied_hash.hexdigest(),semantics='ALREADY_COPIED_IMMUTABLE_KERNEL_SNAPSHOT_ROWS'),dict(path=str(copied_meta_path.resolve()),bytes=copied_meta_bytes,sha256=copied_meta_hash.hexdigest(),semantics='CACHED_IMMUTABLE_SNAPSHOT_FACTS_NOT_LATEST_BANK')]
        result['artifacts'].extend(metadata['immutable_raw_artifacts'])
        result['artifacts'].append(save_new(ARTIFACTS/(prefix+'.'+label+'.json'),metadata))
    for kind,record in s._generated.items():
        raw=record['raw']
        if raw is None:continue
        label=kind.replace('/','_').replace('\\','_')
        result['artifacts'].append(dict(kind=kind,source_eligible=record['eligible'],source_return_observed=record['return_observed'],source_phase=record['phase'],**write_bytes(prefix+'.generated.'+label,raw)))
    raw_path=ARTIFACTS/(prefix+'.canonical-native-rows.bin')
    meta_path=ARTIFACTS/(prefix+'.canonical-calls.jsonl')
    raw_hash=hashlib.sha256();meta_hash=hashlib.sha256();raw_bytes=meta_bytes=registered=0
    store=s._raw_store
    with raw_path.open('xb')as raw_stream,meta_path.open('xb')as meta_stream:
        for call in s._registry._calls:
            index=call.ordinal
            present=(store._bank is not None and 0<=index<len(store._refs)and store._refs[index]is call.ref)
            row=dict(ordinal=index,api=call.api,prepared=call.prepared,invoked=call.invoked,registered=present,native_record_offset=raw_bytes if present else None,wrapper_return_observed=call.wrapper_return,wrapper_state=call.wrapper_state,stopped=call.stopped,pre_clock=clock_fact(call.pre_clock,K.UNOBSERVED),post_clock=clock_fact(call.post_clock,K.UNOBSERVED),read_fold=call._read_fold_phase,hash_fold=call._hash_fold_phase,copy_fold=call._copy_fold_phase,python_delivery={name:clean.value(getattr(call,field))for name,field in(('scalar','_python_scalar'),('count','_python_count'),('error_value','_python_error_value'),('error_definition','_python_error_definition'))})
            if present:
                raw=bytes(memoryview(store._bank)[256*index:256*(index+1)])
                raw_stream.write(raw);raw_hash.update(raw);raw_bytes+=len(raw);registered+=1
                row['axes']={name:decode_axis(raw[offset:offset+32])for name,offset in zip(AXES,AXIS_OFFSETS)}
            else:row['axes']=None;row['native_absence']='RESERVATION_NOT_REGISTERED_NO_TYPED_ZERO_ROW'
            if call.query_bytes is not None:
                query=write_bytes(prefix+'.query-'+str(index)+'.bin',call.query_bytes)
                result['artifacts'].append(query);row['query']=query
            encoded=(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
            meta_stream.write(encoded);meta_hash.update(encoded);meta_bytes+=len(encoded)
    result['registered_native_rows']=registered
    result['artifacts'].extend([dict(path=str(raw_path.resolve()),bytes=raw_bytes,sha256=raw_hash.hexdigest(),semantics='LATEST_EXISTING_BANK_ROWS_NOT_A_NEW_KERNEL_SNAPSHOT'),dict(path=str(meta_path.resolve()),bytes=meta_bytes,sha256=meta_hash.hexdigest(),semantics='HARNESS_STREAM_OF_EXISTING_CANONICAL_ROWS')])
    return result


class CaseContext:
    def __init__(self,W,gate,inputs,literal_vectors,allow_large_stream):
        self.W=W;self.gate=gate;self.inputs=inputs;self.literal_vectors=literal_vectors;self.allow_large_stream=allow_large_stream
        self.worlds=[];self.notes=[];self.current_worlds=[];self.world_attempts=0;self.constructor_errors=[]
    def world(self,**kwargs):
        self.world_attempts+=1
        try:world=self.W.EntryWorld(self.gate,self.inputs,**kwargs)
        except BaseException as error:
            self.constructor_errors.append(error);raise
        self.worlds.append(world);self.current_worlds.append(world);return world
    def note(self,**data):
        if len(data)>32 or any(type(k)is not str or len(k)>80 for k in data):raise RuntimeError('bounded note keys required')
        encoded=json.dumps(data,sort_keys=True,allow_nan=False)
        if len(encoded.encode())>16384:raise RuntimeError('bounded note payload required')
        self.notes.append(json.loads(encoded))


def main():
    started=time.monotonic()
    if ATTEMPT.exists() or PROOF.exists() or ARTIFACTS.exists():
        raise RuntimeError('consumed Source4 suite attempt; no replay')
    binding=json.loads(BINDING.read_bytes())
    if binding['status']!='AUTHORIZED_SOURCE4_E08_122_SUITE_ONCE':
        raise RuntimeError('Root exact Source4 execution binding required')
    if type(binding['deadline_seconds']) is not int or binding['deadline_seconds']!=60:
        raise RuntimeError('one original cooperative60s deadline')
    if type(binding['allow_large_stream']) is not bool:
        raise RuntimeError('Root explicitly selects the procedural stream')
    read_exact(binding['execution_scope'])
    preparation=json.loads(read_exact(binding['preparation']))
    inputs=json.loads(read_exact(binding['inputs']))
    corpus=json.loads(read_exact(inputs['literal_corpus']))
    read_exact(binding['freeze']);read_exact(binding['source_pause'])
    if binding['source_map']!=inputs['source_map'] or binding['harness']!=preparation['harness']:
        raise RuntimeError('exact frozen Source4 source/harness maps required')
    if pin(__file__)!=binding['harness']['runner']:
        raise RuntimeError('actual runner pin required')
    for value in {**binding['source_map'],**binding['harness']}.values():
        read_exact(value)
    branches=inputs['suite_branches']
    expected_groups={'CORRECTIONS':5,'LITERALS':52,'INTEGRATION':15,'CAUSAL':50}
    if len(branches)!=122 or len({row['branch'] for row in branches})!=122:
        raise RuntimeError('exact122 unique dispatches required')
    if {name:sum(row['group']==name for row in branches) for name in expected_groups}!=expected_groups:
        raise RuntimeError('exact5/52/15/50 frozen group counts required')
    if len(corpus['vectors'])!=52 or len({row['id'] for row in corpus['vectors']})!=52:
        raise RuntimeError('unchanged52 literal vectors required')
    literal_by_id={row['id']:row for row in corpus['vectors']}
    save_new(ATTEMPT,dict(status='STARTED_BEFORE_SOURCE4_IMPORT',binding=pin(BINDING),
                         groups=expected_groups,declared_dispatches=122,
                         allow_large_stream=binding['allow_large_stream']))
    rows=[dict(branch=row['branch'],group=row['group'],case=row['case'],variant=row['variant'],
               coverage_class=row['coverage_class'],outcome='NOT_REACHED',action_outcome='NOT_REACHED',
               first_error=None,deferred_reason=None,cleanup_errors=[],evidence_errors=[],notes=[],
               worlds=[],source_world_constructor_errors=[]) for row in branches]
    gate=ctx=None;setup_error=None;deadline_error=None
    try:
        ARTIFACTS.mkdir()
        support=trusted_module('entry_independent_test_support_v4',binding['harness']['support'])
        W=trusted_module('entry_independent_world_v4',binding['harness']['world'])
        C=trusted_module('entry_contract_cases_source4_v1',binding['harness']['causal'])
        R=trusted_module('entry_initial_regressions_source4_v1',binding['harness']['corrections'])
        P=trusted_module('entry_e08_policy_tests_v1',binding['harness']['policy_tests'])
        if set(C.CASES)!={f'E{i:02d}' for i in range(1,33)} or set(P.INTEGRATION)!={f'I{i:02d}' for i in range(1,11)}:
            raise RuntimeError('exact frozen assertion surfaces required')
        gate=support.CallGate(started+60);sys.addaudithook(gate.audit)
        ctx=CaseContext(W,gate,inputs,corpus['vectors'],binding['allow_large_stream'])
        for number,row in enumerate(rows):
            try:
                gate.check()
            except BaseException as error:
                deadline_error=error_data(error)
                for later in rows[number:]:later['outcome']='UNKNOWN_DEADLINE'
                break
            ctx.current_worlds=[];ctx.notes=[];ctx.constructor_errors=[]
            try:
                if row['group']=='CORRECTIONS':
                    getattr(R,row['case'])(ctx.world())
                elif row['group']=='LITERALS':
                    P.run_literal(ctx,literal_by_id[row['case']])
                elif row['group']=='INTEGRATION':
                    P.INTEGRATION[row['case']](ctx,row['variant'])
                elif row['group']=='CAUSAL':
                    C.CASES[row['case']](ctx,row['variant'])
                else:
                    raise RuntimeError('unknown dispatch group')
                row['action_outcome']='PASS';row['outcome']='PASS'
            except C.DeferredBranch as error:
                row['action_outcome']='DEFERRED';row['outcome']='DEFERRED'
                row['deferred_reason']=error_data(error)
            except BaseException as error:
                row['action_outcome']='FAIL';row['outcome']='FAIL';row['first_error']=error_data(error)
            finally:
                row['notes']=list(ctx.notes)
                row['source_world_constructor_errors']=[error_data(e) for e in ctx.constructor_errors]
                for world in reversed(ctx.current_worlds):
                    try:
                        world.cleanup()
                    except BaseException as error:
                        row['cleanup_errors'].append(error_data(error));row['outcome']='FAIL'
                for wi,world in enumerate(ctx.current_worlds):
                    try:
                        row['worlds'].append(retain_world(world,'dispatch-%03d-world-%02d'%(number+1,wi+1)))
                    except BaseException as error:
                        row['evidence_errors'].append(error_data(error));row['outcome']='FAIL'
            try:
                gate.check()
            except BaseException as error:
                deadline_error=error_data(error);row['deadline_veto']=True
                if row['outcome']=='PASS':row['outcome']='UNKNOWN_DEADLINE'
                for later in rows[number+1:]:later['outcome']='UNKNOWN_DEADLINE'
                break
    except BaseException as error:
        setup_error=error_data(error)
    changed=[]
    for name,value in {**binding['source_map'],**binding['harness']}.items():
        if pin(value['path'])!=value:changed.append(name)
    late=time.monotonic()>=started+60
    audit=[] if gate is None else list(gate.audit_denials)
    counts={name:sum(row['outcome']==name for row in rows)
            for name in ('PASS','FAIL','DEFERRED','NOT_REACHED','UNKNOWN_DEADLINE')}
    group_counts={group:{name:sum(row['group']==group and row['outcome']==name for row in rows)
                         for name in counts} for group in expected_groups}
    complete=(counts['PASS']==122 and setup_error is None and deadline_error is None
              and not changed and not audit and not late)
    status='ALL_122_SOURCE4_ASSERTIONS_PASSED' if complete else 'INCOMPLETE_OR_FAILED'
    result=dict(schema_version=1,status=status,scope='SOURCE4_E08_52_15_5_50_SOURCE_PURE_ONLY',
                source_pause=binding['source_pause'],source_map=binding['source_map'],
                preparation=binding['preparation'],inputs=binding['inputs'],freeze=binding['freeze'],
                binding=pin(BINDING),rows=rows,declared_dispatches=122,declared_groups=expected_groups,
                counts=counts,group_counts=group_counts,
                actually_invoked_dispatches=sum(row['action_outcome']!='NOT_REACHED' for row in rows),
                world_construction_attempts=0 if ctx is None else ctx.world_attempts,
                worlds_constructed=0 if ctx is None else len(ctx.worlds),
                actual_entry_attempts=0 if ctx is None else sum(int(world.attempt.attempted) for world in ctx.worlds),
                setup_error=setup_error,deadline_error=deadline_error,cooperative_deadline_late=late,
                audit_denials=audit,changed_pins=changed,elapsed_seconds=time.monotonic()-started,
                call_gate=None if gate is None else dict(attempts=gate.attempts,normal_returns=gate.returns,checks=gate.checks),
                allow_large_stream=binding['allow_large_stream'],
                evidence_persistence='PER_WORLD_HARNESS_COPIES_INCLUDED; FINAL_PROOF_WRITE_OUTSIDE_REPORTED_ELAPSED_UNMEASURED',
                metadata_report_is_full_entry_success=False,
                source3_original_e08_and_historical_e16_results='UNCHANGED',
                complete_entry_gate=False,native25='NOT_EXECUTED',
                qualification=dict(source_only=True,pure_synthetic=True,native=False,physical_io=False,
                                   real_first_entry=False,whole_r09=False,full_real_roster=False,
                                   resource_fit=False,scientific=False))
    proof=save_new(PROOF,result)
    print(json.dumps(dict(status=status,proof=proof,counts=counts,group_counts=group_counts)))
    return 0 if complete else 1


if __name__=='__main__':
    raise SystemExit(main())
