"""Finite authored entry32/53 controls; importing this file imports no subject.

Case/variant labels remain exclusively in the trusted harness. All operational
objects come from the exact executing Source4 module and its captured helpers.
"""
import hashlib
import math
from types import MappingProxyType
from entry_independent_test_support_v4 import require, strict_equal


MISSING=object()


class DeferredBranch(Exception):
    pass


class Patch:
    def __init__(self,target,name,value):
        self.target,self.name,self.value=target,name,value
        self.previous=vars(target).get(name,MISSING)
    def __enter__(self):
        setattr(self.target,self.name,self.value)
        return self
    def __exit__(self,typ,error,tb):
        if self.previous is MISSING:delattr(self.target,self.name)
        else:setattr(self.target,self.name,self.previous)
        return False


def caught(action,*,same=None,code=None):
    error=None
    try:action()
    except BaseException as raised:error=raised
    require(error is not None,'expected actual refusal/exception')
    if same is not None:require(error is same,'same original exception identity')
    if code is not None:require(getattr(error,'code',None)==code,'exact refusal '+code)
    return error


def no_progress(w):
    s=w.state
    return (len(w.originals.calls),len(s.journal['events']),s.journal['next_sequence'],
            len(s.registry._calls),len(w.output.callbacks),len(w.loader.compiler_observations))


def axis(w,ref,name='scalar'):
    return w.gate.invoke(w.state.raw_call_view,ref).axis(name)


def record_axis(value):
    return value.to_dict()


def scripted_handled(w,ref,observation):
    """Independent callback accounting for an explicitly supplied raw return."""
    path=ref.file_ref.spec.path
    if ref.api=='CreateFileW':
        w.originals.open_attempts[path]+=1
        require(w.originals.open_attempts[path]==1,'one supplied CreateFile callback')
    elif ref.api=='CloseHandle':
        w.originals.close_attempts[path]+=1
        require(w.originals.open_attempts[path]==1 and w.originals.close_attempts[path]==1,
                'one supplied CloseHandle callback')
    observation['handled_by_injected_original']=True


def short_read_hook(count,*,missing=False):
    def hook(w,point,ref,args,carrier,observation):
        if point!='entered' or ref.api!='ReadFile':return
        scripted_handled(w,ref,observation)
        body=w.originals.by_path[ref.file_ref.spec.path]['body']
        require(type(body)is bytes and len(body)>=count,'actual captured helper prefix for short read')
        carrier.buffer_write_slice(ref,ref.buffer_ref,ref.buffer_generation,0,body[:count])
        carrier.store_scalar(ref,1);observation['scalar_hook_completed']=True
        if not missing:
            carrier.store_count(ref,count);observation['count_hook_completed']=True
            w.originals.delivered[ref.file_ref.spec.path]+=count
    return hook


def loaded(w):
    w.enter();w.bootstrap();w.load_helpers()


def require_initial_identity(w):
    require(w.state is w.attempt.state and w.state.origin.provider_ref is w.clock,
            'same canonical Core and original clock provider')
    require(w.state.origin.start==100 and w.state.origin.work_end==395 and w.state.origin.hard_end==400,
            'original clock window')
    require(w.state.registry is w.identities[3] and w.state.raw_store is w.identities[4],
            'original Registry/raw store')


def E01(ctx,variant):
    w=ctx.world();K=w.K;observed=[];original=K._KernelAlgorithms.admit_plan
    def inspect_before_plan(state,*args):
        observed.append((state,state.origin,state.nonce,state.registry,state.raw_store,state.port,state.sink,state.loader))
        require(state.origin.start==100 and state.registry is not None and state.raw_store is not None,
                'canonical objects exist before actual plan admission')
        require(not w.originals.calls and not w.loader.compiler_observations,'no original/helper work before Core')
        return original(state,*args)
    w.clock.script=[100,101]
    with Patch(K._KernelAlgorithms,'admit_plan',inspect_before_plan):
        w.enter();w.bootstrap()
    require(len(observed)==1 and observed[0][0] is w.state,'actual plan receiver is initial Core')
    require(w.events[0]==('clock',1) and w.attempt.start_cell==100,'first original clock result100')
    require_initial_identity(w)
    require(not w.loader.compiler_observations,'helpers are only captured, not executed, before loader work')
    ctx.note(first_sample=100,all_canonical_objects_before_plan=True,full_prefix_bytes=w.geometry['early_bytes'])


def E02(ctx,variant):
    w=ctx.world();K=w.K;fault=MemoryError('E02 actual Registry construction')
    def fail_registry(registry,owner):raise fault
    with Patch(K.Registry,'__init__',fail_registry):
        caught(w.enter,same=fault)
    require(w.attempt.start_cell==100 and w.attempt.error is fault and w.state is None,
            'first sample/error retained with absent incomplete Core')
    require(not w.originals.calls and not w.loader.compiler_observations and not w.output.callbacks,
            'zero work after Registry construction failure')
    ctx.note(original_exception_identity=True,start=100,core_absent=True,registry_absent=True)


def E03(ctx,variant):
    w=ctx.world();fault=RuntimeError('E03 original provider failure')
    w.clock.script=[fault]
    caught(w.enter,same=fault)
    require(w.attempt.start_cell is w.K.UNOBSERVED and w.attempt.error is fault and w.state is None,
            'UNOBSERVED first sample with original provider exception')
    calls=w.clock.calls;w.clock.set(100)
    caught(w.enter,code='ENTRY_REPEATED')
    require(w.clock.calls==calls==1 and w.attempt.error is fault,'no restart or renewed clock')
    require(not w.originals.calls and not w.loader.compiler_observations and not w.output.callbacks,'no later helper/original work')
    ctx.note(start_unobserved=True,provider_exception_identity=True,restart_refused=True)


def E04(ctx,variant):
    w=ctx.world();K=w.K
    if variant=='public_Origin':
        caught(lambda:w.gate.invoke(K.Origin,object(),w.clock,w.attempt),code='FOREIGN_STATE')
    else:
        key='started' if variant=='extra_started' else 't0'
        error=caught(lambda:w.gate.invoke(K.entry,w.services,w.plan,executing_module=K,**{key:100}))
        require(type(error)is TypeError,'ordinary unsupported keyword is external signature TypeError')
    require(w.clock.calls==0 and not w.attempt.attempted and w.state is None,'no caller-supplied start adoption')
    require(not w.originals.calls and not w.output.callbacks,'no dispatch on signature/issuer refusal')
    ctx.note(refusal_boundary='SIGNATURE_OR_PRIVATE_ORIGIN_ISSUER',clock_calls=0)


def E05(ctx,variant):
    w=ctx.world();K=w.K;original=K.Registry.__init__;fault=MemoryError('E05 canonical append after commit')
    class AppendFailure(list):
        def append(self,value):
            list.append(self,value)
            raise fault
    def registered(registry,owner):
        original(registry,owner);object.__setattr__(registry,'_calls',AppendFailure())
    with Patch(K.Registry,'__init__',registered):
        w.enter();core=w.state
        caught(w.bootstrap,same=fault)
    require(w.state is core and core.primary is fault,'existing Core and original primary retained')
    require(len(core.registry._calls)==1,'actual canonical reserved row survives append interruption')
    call=core.registry._calls[0]
    require(call.prepared and not call.invoked and core.raw_store._refs[0] is None,
            'reserved/uninvoked row with explicitly absent native registration')
    require(not w.originals.calls,'no dispatch without registered carrier')
    snap=w.gate.invoke(core.snapshot)
    w.first_snapshot=snap
    require(snap.partial_capture and snap.raw_call_count==0,'missing row remains explicit partial capture')
    ctx.note(reserved=1,invoked=0,native_registration_absent=True,partial_snapshot=True)


def E06(ctx,variant):
    w=ctx.world();w.enter();w.bootstrap();fault=SyntaxError('E06 actual captured compiler')
    name=w.inputs['module_names']['owner_ops']
    def fail_compile(world,fullname,raw):
        if fullname==name:raise fault
    w.compile_hook=fail_compile
    caught(lambda:w.gate.invoke(w.state.load_captured,name),same=fault)
    require(name in w.state.loader.attempted and name not in w.state.loader.loaded,'compile attempt without accepted module')
    before=len(w.loader.compiler_observations)
    caught(lambda:w.gate.invoke(w.state.load_captured,name),same=fault)
    require(len(w.loader.compiler_observations)==before,'no compiler retry/fallback')
    require(w.state.primary is fault and not w.state._issued,'no eligible continuation after compiler failure')
    ctx.note(compile_original_identity=True,retry_callbacks=0,accepted_module=False)


def E07(ctx,variant):
    w=ctx.world(toy=True);loaded(w)
    extra=w.gate.invoke(w.state.load_captured,'entry_extra_entry_v1')
    require(w.gate.invoke(extra.run)==18,'additional actual captured marker dependency')
    early=w.state.early_context
    blobs={p:early.bytes_for(p) for p in w.early_paths}
    refs=tuple(w.file_refs);registry=w.state.registry
    result=w.finish();data=result.to_dict()
    require(data['pure_seam_complete'] is True,'actual extended-prefix continuation')
    current_refs=tuple(f.ref for f in w.state.registry._files)
    require(w.state.registry is registry and all(a is b for a,b in zip(refs,current_refs)),'same original refs and Registry')
    require(w.state.evidence_context.early_context is early,'same early context retained into full evidence')
    require(all(w.state.evidence_context.bytes_for(p)is blob for p,blob in blobs.items()),'same early byte objects')
    require(sum(w.originals.delivered.values())==w.geometry['known_bytes'],'full actual-plus-toy input bytes once')
    require(all(v==1 for v in w.originals.open_attempts.values()),'no early reopen')
    require(w.geometry['early_bytes']==99141 and w.geometry['captured_bytes']==99209,
            'actual99000 plus additional141 plus later68, never old209 total')
    ctx.note(actual_helper_bytes=99000,additional_toy_bytes=141,full_geometry=w.geometry,
             marker_executed=True,same_early_bytes=True)


def E08(ctx,variant):
    w=ctx.world();K=w.K;rules=list(w.module_rules)
    r=rules[0];rules[0]=K.ModuleRule(r.fullname,r.path,(r.fullname,),r.package)
    p=w.plan;w.plan=K.EntryPlan(p.files,p.early_paths,tuple(rules),p.output_key,p.owner_ops_name,p.file_view_name,p.codec_name,p.profile)
    caught(w.enter,code='SOURCE_IMPORT_REFUSED')
    require(not w.originals.calls and not w.loader.compiler_observations,'real captured-DAG cycle refused before helper/file work')
    ctx.note(exercised='ACTUAL_CAPTURED_IMPORT_DAG_SELF_CYCLE',decision_output_manifest_policy='UNIMPLEMENTED_SEPARATE_POLICY')
    raise DeferredBranch('Kernel DAG cycle refusal exercised; recursive decision/output manifest-pin policy is outside this implemented API and remains deferred.')


def E09(ctx,variant):
    w=ctx.world();loaded(w);identity=w.identities;w.clock.set(140);w.attach_helpers()
    require_initial_identity(w)
    require(w.state.origin.now==140 and w.state.origin.now-w.state.origin.start==40,'spent original40 seconds retained')
    current=(w.state,w.state.origin,w.state.nonce,w.state.registry,w.state.raw_store,
             w.state.port,w.state.sink,w.state.loader,w.state.journal)
    require(all(a is b for a,b in zip(identity,current)),'canonical identities preserved')
    require(sum(r['target']=='reserve' for r in w.output.callbacks)==1,'no second namespace reservation')
    ctx.note(elapsed_original=40,same_facades=True,namespace_reservations=1)


def E10(ctx,variant):
    a=ctx.world();loaded(a);a.attach_helpers()
    b=ctx.world(kernel=a.K);loaded(b);b.attach_helpers()
    require(a.state.origin.start==b.state.origin.start==100 and a.state is not b.state and a.state.nonce is not b.state.nonce,
            'distinct genuine equal-valued states')
    before=no_progress(a)
    caught(lambda:a.gate.invoke(a.view.inspect,b.file_refs[0]))
    require(no_progress(a)==before,'foreign actual ref rejected without progress')
    ctx.note(genuine_states=2,same_class=True,equal_starts=True,foreign_ref_refused=True)


def E11(ctx,variant):
    a=ctx.world();a.enter();a.bootstrap()
    b=ctx.world();loaded(b)
    require(a.K is not b.K and a.K.__name__==b.K.__name__ and a.K.KernelState is not b.K.KernelState,
            'actual equal-source/equal-name independent kernel namespace')
    a.load_helpers();require(a.ops_module.K is a.K and a.view_module.K is a.K,'resolver retained actual executing kernel despite same-name replacement')
    capsule=a.gate.invoke(a.state.issue_continuation);before=no_progress(a)
    caught(lambda:b.gate.invoke(b.ops_module.attach,capsule))
    require(no_progress(a)==before and not a.state._claimed,'foreign namespace cannot claim A')
    ctx.note(equal_source_distinct_namespaces=True,resolver_actual_object=True,foreign_namespace_claim_refused=True)


def E12(ctx,variant):
    w=ctx.world();loaded(w);called=[]
    def replacement(*args,**kwargs):
        called.append(True);raise AssertionError('replacement must never be called')
    target,name=(w.K,'Origin') if variant=='Origin_rebound' else (w.ops_module,'attach')
    before=no_progress(w)
    with Patch(target,name,replacement):caught(lambda:w.gate.invoke(w.state.issue_continuation))
    require(no_progress(w)==before and not called and not w.state._issued,
            'stored original factory/namespace identity refuses replacement')
    ctx.note(replacement_followed=False,events_or_dispatch_advanced=False)


def E13(ctx,variant):
    w=ctx.world();w.attach_helpers();before=no_progress(w)
    caught(lambda:w.gate.invoke(w.ops_module.attach,w.capsule),code='HANDOFF_REPEATED')
    require(no_progress(w)==before,'repeat claim adds no events/counters/I/O')
    ctx.note(second_claim_refused=True,same_view=True)


def E14(ctx,variant):
    w=ctx.world();loaded(w);ref=w.file_refs[0]
    w.gate.invoke(w.state.port.close,ref);before=no_progress(w)
    caught(lambda:w.gate.invoke(w.state.issue_continuation),code='EARLY_SOURCE_NOT_LIVE_COMPLETE')
    require(no_progress(w)==before and not w.state._issued,'known closed early lease cannot issue')
    require(w.originals.close_attempts[ref.spec.path]==1,'known close remains once-only')
    ctx.note(known_closed_early_ref=True,issue_refused=True)


def E15(ctx,variant):
    w=ctx.world();fault=MemoryError('E15 incomplete early evidence')
    def hook(world,point,ref,args,carrier,obs):
        hit=(variant=='open_unknown' and ref.api=='CreateFileW' and point=='before_scalar' or
             variant=='capture_incomplete' and ref.api=='ReadFile' and point=='after_count' or
             variant=='close_unknown' and ref.api=='CloseHandle' and point=='before_scalar')
        if hit:raise fault
    w.raw_hook=hook;w.enter()
    if variant=='close_unknown':
        w.bootstrap();w.load_helpers();caught(lambda:w.gate.invoke(w.state.port.close,w.file_refs[0]),same=fault)
    else:caught(w.bootstrap,same=fault)
    before=no_progress(w);caught(lambda:w.gate.invoke(w.state.issue_continuation))
    require(no_progress(w)==before and not w.state._issued,'unknown/incomplete early data never becomes continuation authority')
    ctx.note(unknown_or_incomplete_preserved=True,issue_refused=True,variant=variant)


def E16(ctx,variant):
    if variant=='foreign_attach':
        a=ctx.world();loaded(a);capsule=a.gate.invoke(a.state.issue_continuation)
        b=ctx.world(kernel=a.K);loaded(b);before=no_progress(a)
        caught(lambda:b.gate.invoke(b.ops_module.attach,capsule))
        require(no_progress(a)==before and not a.state._claimed,'different genuine captured factory refuses before claim')
        ctx.note(exercised='ACTUAL_FOREIGN_CAPTURED_ATTACH',genuine_states=2)
        return
    w=ctx.world();loaded(w);before=len(w.originals.calls)
    require(not hasattr(w.K,'SharedOwner') and not hasattr(w.K,'start_injected'),'old public constructors absent from actual new kernel API')
    caught(lambda:w.gate.invoke(w.state.load_captured,'shared_owner_v4'),code='SOURCE_IMPORT_REFUSED')
    require(len(w.originals.calls)==before,'excluded old source not read or dispatched')
    ctx.note(exercised='CLOSED_LOADER_AND_NEW_API_EXCLUSION',historical_factory_executed=False)
    raise DeferredBranch('Historical Source4 constructor/start_injected is excluded and not imported/constructed. Closed new-loader/API refusal is exercised; the literal historical factory invocation is not.')


def E17(ctx,variant):
    w=ctx.world();fault=KeyboardInterrupt('E17 after committed native handle77')
    first=w.fixtures[0]['path'];w.originals.handles[first]=77
    def hook(world,point,ref,args,carrier,obs):
        if point=='after_scalar' and ref.api=='CreateFileW':raise fault
    w.raw_hook=hook;w.enter();caught(w.bootstrap,same=fault)
    ref=w.originals.refs[0];a=axis(w,ref)
    require(a.native_state=='COMMITTED' and a.known_value==77,'committed handle77 independent of wrapper return')
    require(not w.state.registry._calls[ref.ordinal].wrapper_return and w.state.primary is fault,'original interrupt and absent wrapper return')
    w.cleanup();require(w.originals.close_attempts[first]==1,'known77 gets one genuine cleanup opportunity')
    require(w.state.primary is fault,'cleanup retains the original interrupt')
    ctx.note(native_handle=77,wrapper_return_observed=False,original_interrupt_identity=True,once_close=True)


def E18(ctx,variant):
    w=ctx.world();fault=MemoryError('E18 staged native handle77')
    first=w.fixtures[0]['path'];w.originals.handles[first]=77
    def hook(world,point,ref,args,carrier,obs):
        if point=='entered' and ref.api=='CreateFileW':
            carrier.stage_axis(ref,'scalar',77);raise fault
    w.raw_hook=hook;w.enter();caught(w.bootstrap,same=fault)
    ref=w.originals.refs[0];a=axis(w,ref)
    require(a.native_state=='STAGED_UNCOMMITTED' and a.raw_payload_bits==77 and a.known_value is None,
            'staged77 retained without handle authority')
    w.cleanup();require(sum(w.originals.close_attempts.values())==0,'no close right from staged bits')
    ctx.note(native=record_axis(a),atomic_native_claim=False,close_attempts=0)


def E19(ctx,variant):
    w=ctx.world(raw_hook=short_read_hook(0,missing=variant=='count_UNOBSERVED'));w.enter()
    caught(w.bootstrap)
    ref=next(r for r in w.originals.refs if r.api=='ReadFile');a=axis(w,ref,'count')
    call=w.state.registry._calls[ref.ordinal];defined=w.state.defined(call)
    require(defined is (variant=='count0'),'defined zero differs from absent count')
    if variant=='count0':require(a.native_state=='COMMITTED' and a.known_value==0,'observed defined0')
    else:require(a.native_state=='UNOBSERVED' and a.known_value is None,'unobserved count stays unknown')
    before=len(w.originals.calls);first=w.gate.invoke(w.state.snapshot);w.first_snapshot=first
    one=first.to_dict();two=w.gate.invoke(w.state.snapshot).to_dict()
    require(one['byte_totals']['known_read_bytes']==two['byte_totals']['known_read_bytes']==0,'no invented progress/double fold')
    require(one['byte_totals']['read_count_unknown'] is (variant=='count_UNOBSERVED'),'known0 versus unknown population accounting')
    require(len(w.originals.calls)==before and not w.held_states[0].hash_complete,'no retry/full-file completion')
    ctx.note(count=record_axis(a),defined=defined,full_file_complete=False)


def E20(ctx,variant):
    w=ctx.world();K=w.K
    def hook(world,point,ref,args,carrier,obs):
        if point!='entered' or ref.api!='CreateFileW':return
        scripted_handled(world,ref,obs)
        scalar=world.originals.handles[ref.file_ref.spec.path] if variant=='definition_before_code' else K.INVALID
        carrier.store_scalar(ref,scalar);obs['scalar_hook_completed']=True
        if variant=='definition_before_code':carrier.store_error_definition(ref,True)
        elif variant=='code_before_definition':carrier.store_error_value(ref,0)
        else:carrier.store_error_value(ref,0);carrier.store_error_definition(ref,False)
    w.raw_hook=hook;w.enter();caught(w.bootstrap)
    ref=w.originals.refs[0];code=axis(w,ref,'error_value');definition=axis(w,ref,'error_definition')
    require((code.native_state=='COMMITTED') is (variant!='definition_before_code'),'raw code observedness independent')
    require((definition.native_state=='COMMITTED') is (variant!='code_before_definition'),'definition observedness independent')
    if variant=='definition_before_code':
        require(definition.known_value is True and code.known_value is None,'definitionTrue before absent code')
        require(w.state.primary is not None,'success plus defined failure error refused after raw retention')
    elif variant=='code_before_definition':require(code.known_value==0 and definition.known_value is None,'raw DWORD0 before missing definition')
    else:require(code.known_value==0 and definition.known_value is False,'observed definitionFalse with code0')
    ctx.note(raw_code=record_axis(code),definition=record_axis(definition),no_zero_or_definedness_invention=True)


def E21(ctx,variant):
    w=ctx.world(raw_hook=short_read_hook(58));K=w.K;original=K.KernelState._fold_read_fact
    fault=MemoryError('E21 count fold '+variant);hit=[]
    def fold(state,call):
        if not hit and call.api=='ReadFile' and state.committed_fact(call,'count')==58:
            hit.append(call)
            if variant=='after_commit':original(state,call)
            raise fault
        return original(state,call)
    with Patch(K.KernelState,'_fold_read_fact',fold):
        w.enter();caught(w.bootstrap,same=fault)
    require(len(hit)==1 and w.state.primary is fault,'one original count fold interruption')
    call=hit[0];require(axis(w,call.ref,'count').known_value==58,'canonical raw58 survives')
    cached=w.held_states[0]._known_read_bytes
    require(cached==(58 if variant=='after_commit' else 0),'honest pre/post cache commit boundary')
    before=len(w.originals.calls)
    first=w.gate.invoke(w.state.snapshot);w.first_snapshot=first
    one=first.to_dict();two=w.gate.invoke(w.state.snapshot).to_dict()
    require(one['byte_totals']['known_read_bytes']==two['byte_totals']['known_read_bytes']==58,'cold report derives58 once')
    require(w.held_states[0]._known_read_bytes==cached,'cold report never heals interrupted fold')
    caught(lambda:w.gate.invoke(w.state.check))
    require(w.clock.value==100 and len(w.originals.calls)==before,'otherwise-valid work refuses quarantine without I/O')
    require(not w.held_states[0].hash_complete and not w.held_states[0].capture_complete,'no hash/copy completion')
    w.cleanup()
    require(w.state.primary is fault and w.held_states[0]._known_read_bytes==cached,
            'cleanup preserves the same primary without healing the failed read cache')
    require(sum(r.api=='ReadFile' for r in w.originals.refs)==1,'cleanup never retries the failed read')
    ctx.note(raw_count=58,cache_known_bytes=cached,cold_known_bytes=58,no_healing=True,no_double_fold=True)


def E22(ctx,variant):
    w=ctx.world();K=w.K;first=w.fixtures[0]['path']
    if variant.startswith('BOOL'):
        w.enter();w.bootstrap();value=0 if variant=='BOOL0' else -1
        def hook(world,point,ref,args,carrier,obs):
            if point=='entered' and ref.api=='CloseHandle' and ref.file_ref.spec.path==first:
                scripted_handled(world,ref,obs);carrier.store_scalar(ref,value);obs['scalar_hook_completed']=True
        w.raw_hook=hook
        if value==0:caught(lambda:w.gate.invoke(w.state.port.close,w.file_refs[0]),code='INVALID_INPUT')
        else:w.gate.invoke(w.state.port.close,w.file_refs[0])
        ref=next(r for r in w.originals.refs if r.api=='CloseHandle');a=axis(w,ref)
        require(a.known_value==value and a.native_state=='COMMITTED','signed BOOL32 remains exact')
        count=len(w.originals.calls);caught(lambda:w.gate.invoke(w.state.port.close,w.file_refs[0]))
        require(len(w.originals.calls)==count and w.originals.close_attempts[first]==1,'known false/true closer consumed once')
        ctx.note(native=record_axis(a),known_success=value!=0,close_consumed_once=True)
        return
    value={'handle_NULL':None,'handle0':0,'handle_INVALID':K.INVALID,'handle77':77}.get(variant,K.UNOBSERVED)
    fault=KeyboardInterrupt('E22 scalar unobserved')
    if value==77:w.originals.handles[first]=77
    def hook(world,point,ref,args,carrier,obs):
        if point=='entered' and ref.api=='CreateFileW' and ref.file_ref.spec.path==first:
            if value is K.UNOBSERVED:raise fault
            scripted_handled(world,ref,obs);carrier.store_scalar(ref,value);obs['scalar_hook_completed']=True
    w.raw_hook=hook;w.enter()
    if value==77:w.bootstrap()
    else:caught(w.bootstrap,same=fault if value is K.UNOBSERVED else None)
    ref=w.originals.refs[0];a=axis(w,ref)
    snap=w.gate.invoke(w.state.snapshot)
    w.first_snapshot=snap
    delivery=snap.raw_call(ref.ordinal).facts['python_delivery']['scalar']
    if value is K.UNOBSERVED:require(a.native_state=='UNOBSERVED' and delivery['tag']=='UNOBSERVED','unknown is not zero')
    elif value is None:require(a.known_value==0 and delivery==dict(tag='NULL',value=None),'Python None retained separately from native HANDLE0')
    elif value==0:require(a.known_value==0 and delivery==dict(tag='HANDLE',value=0),'Python int0 retained separately from None')
    else:require(a.known_value==value,'exact nonzero/invalid handle')
    w.cleanup();require(w.originals.close_attempts[first]==int(value==77),'only committed usable77 grants chosen close right')
    ctx.note(native=record_axis(a),python_delivery=delivery,chosen_close_attempts=w.originals.close_attempts[first])


def E23(ctx,variant):
    w=ctx.world();w.enter();w.bootstrap();before=len(w.originals.calls);w.clock.set(395)
    caught(lambda:w.gate.invoke(w.state.port.acquire,w.specs[3]),code='WORK_DEADLINE')
    require(len(w.originals.calls)==before,'work boundary refuses before dispatch')
    w.clock.set(396);w.gate.invoke(w.state.port.close,w.file_refs[0])
    require(w.originals.close_attempts[w.specs[0].path]==1,'known cleanup allowed under original hard limit')
    require_initial_identity(w)
    ctx.note(work_refused_at=395,cleanup_known_at=396,original_hard_end=400)


def E24(ctx,variant):
    w=ctx.world();w.enter();w.bootstrap();before=len(w.originals.calls);callbacks=len(w.output.callbacks);w.clock.set(400)
    caught(lambda:w.gate.invoke(w.state.port.close,w.file_refs[0]),code='HARD_DEADLINE')
    caught(lambda:w.gate.invoke(w.state.emit,'publication_reserved',{'kind':'failure'},cleanup=True),code='HARD_DEADLINE')
    require(len(w.originals.calls)==before and len(w.output.callbacks)==callbacks,'hard cutoff blocks closers/publication')
    require(sum(w.originals.close_attempts.values())==0,'known rights not fabricated closed')
    ctx.note(hard_cutoff=400,post_cutoff_dispatches=0,known_rights_unclosed=True)


def E25(ctx,variant):
    w=ctx.world();K=w.K;fault=RuntimeError('E25 original clock provider')
    if variant in ('int64_deadline_overflow','F64_no_strict_deadline_increase'):
        value=(1<<63)-1 if variant=='int64_deadline_overflow' else 1e308
        w.clock.set(value);caught(w.enter,code='CLOCK_INVALID')
        require(type(w.attempt.start_cell)is type(value) and w.attempt.start_cell==value and w.state is None,
                'raw invalid-deadline start retained without fabricated Origin')
        ctx.note(invalid_deadline_start_type=type(value).__name__,deadline_refused=True)
        return
    w.enter();before=len(w.originals.calls)
    if variant=='provider_exception':w.clock.script=[fault]
    else:w.clock.set(99 if variant=='backward' else float('nan'))
    error=caught(lambda:w.gate.invoke(w.state.port.acquire,w.specs[3]),same=fault if variant=='provider_exception' else None)
    require(w.state.origin._state=='invalid','clock invalidity is retained')
    calls=w.clock.calls;w.clock.set(100)
    caught(lambda:w.gate.invoke(w.state.port.acquire,w.specs[3]))
    require(w.clock.calls==calls and len(w.originals.calls)==before,'favorable sample cannot heal clock')
    require(w.state.primary is error,'same first invalid-clock/provider error retained')
    ctx.note(clock_invalid_irreversible=True,original_provider_exception=variant=='provider_exception',post_invalid_dispatches=0)


def E26(ctx,variant):
    w=ctx.world(raw_hook=short_read_hook(58));K=w.K;original=K.KernelState.call_clock;target=[]
    def clocks(state,call,which,cleanup=False):
        if call.api=='ReadFile':
            if which=='pre':w.clock.set(394);target.append(call)
            else:w.clock.set(400)
        return original(state,call,which,cleanup)
    with Patch(K.KernelState,'call_clock',clocks):
        w.enter();caught(w.bootstrap,code='HARD_DEADLINE')
    call=target[0];require(call.pre_clock==394 and call.post_clock==400,'exact late postclock facts')
    require(call.wrapper_return and call.wrapper_state=='returned' and axis(w,call.ref,'count').known_value==58,
            'known58 and wrapper return precede late veto')
    before=len(w.originals.calls);caught(lambda:w.gate.invoke(w.state.port.close,w.file_refs[0]),code='HARD_DEADLINE')
    require(len(w.originals.calls)==before and sum(w.originals.close_attempts.values())==0,'no close/work after hard cutoff')
    ctx.note(known_raw_count=58,wrapper_return_observed=True,pre_clock=394,post_clock=400,eligible=False)


def E27(ctx,variant):
    w=ctx.world();fault=MemoryError('E27 namespace observed but reserve callback fails')
    def hook(point,*args):
        if point=='namespace_stored':raise fault
    w.output.hook=hook;caught(w.enter,same=fault)
    require(w.state is not None and w.state.namespace_owned and not w.state.reservation_ready,
            'partial namespace fact separate from readiness')
    identities=(w.state.port,w.state.sink,w.state.registry,w.state.raw_store)
    for name in ('port','sink','registry','raw_store'):
        caught(lambda name=name:setattr(w.state,name,object()))
    require(all(a is b for a,b in zip(identities,(w.state.port,w.state.sink,w.state.registry,w.state.raw_store))),
            'ordinary replacement cannot change canonical facades/registry')
    before=len(w.originals.calls);caught(w.bootstrap);caught(lambda:w.gate.invoke(w.state.issue_continuation))
    require(len(w.originals.calls)==before==0 and not w.state._issued,'no open or claim without output prefix')
    require(sum(r['target']=='reserve' for r in w.output.callbacks)==1,'no second reservation')
    ctx.note(namespace_owned=True,reservation_ready=False,original_opens=0,stable_original_objects=True)


def E28(ctx,variant):
    w=ctx.world();fault=RuntimeError('E28 immutable original diagnostic')
    def hook(world,point,ref,args,carrier,obs):
        if point=='after_scalar' and ref.api=='CreateFileW':raise fault
    w.raw_hook=hook;w.enter();caught(w.bootstrap,same=fault)
    snap=w.gate.invoke(w.state.snapshot);w.first_snapshot=snap
    before=snap.to_dict();token=before['errors']['primary']['identity']
    require(w.state.exception_for_token(token)is fault,'genuine source token resolves original by is')
    original_diag=dict(before['errors']['primary']);returned=snap.to_dict()
    returned['errors']['primary']['message']='external mutation';returned['files'].clear();fault.args=('later mutation',)
    require(snap.to_dict()['errors']['primary']==original_diag and len(snap.to_dict()['files'])==len(w.specs),
            'issued snapshot detached from caller data and later args')
    clocks=w.clock.calls;snap.to_dict();snap.raw_call(0).axis('scalar');w.state.exception_for_token(token)
    require(w.clock.calls==clocks,'cached getters/token resolution sample no clock')
    w.cleanup();before_calls=len(w.originals.calls);final=w.state._final.to_dict()
    caught(lambda:w.gate.invoke(w.state.port.acquire,w.specs[3]),code='FINALIZED_MISUSE')
    require(len(w.originals.calls)==before_calls and w.state._final.to_dict()==final,'postfinal misuse preserves frozen result')
    require(snap.to_dict()['errors']['primary']==original_diag,'later lifecycle never mutates earlier snapshot')
    ctx.note(token_original_identity=True,detached_snapshot=True,cache_only_getters=True,postfinal_nonmutating=True)


def E29(ctx,variant):
    meta=ctx.inputs['static_metadata'];nodes=meta['planned_unbuilt_nodes']
    require(nodes and all(n['sha256'] is None and n['reason'] for n in nodes),'unbuilt outputs retain null and reason')
    require(meta['source_authoring_authorized'] is True and meta['runtime_admission_authorized'] is False,
            'source authoring does not require future built hashes or admit runtime')
    ctx.note(evidence_kind='STATIC_METADATA',planned_unbuilt_count=len(nodes),runtime_admission=False)


def E30(ctx,variant):
    meta=ctx.inputs['static_metadata']
    require(meta['actual_source_imports_exclude_old_owner'] and meta['historical_baselines_retained'],
            'explicit new-source import graph and preserved historical baseline pins')
    w=ctx.world();snap=w.finish();require(snap.to_dict()['pure_seam_complete'] is True,'actual genuine new-entry continuation')
    require(w.geometry['early_bytes']==99000 and len(w.loader.compiler_observations)==3,'full actual authored-helper prefix')
    require(type(w.state)is w.K.KernelState and w.state.origin.start==100,'actual executing-kernel Core class/Origin')
    ctx.note(evidence_kind='ACTUAL_SOURCE_AND_STATIC_LINEAGE',actual_helper_bytes=99000,
             old_owner_imported=False,prefix_stripped=False,canonical_registry=True)


def E31(ctx,variant):
    w=ctx.world();w.finish();codec=w.state.loader.loaded[w.inputs['module_names']['codec']]
    require(codec is w.ops_module.codec,'exact captured pure codec selected')
    artifact=w.state._generated['candidate-ledger.bin']['raw']
    decoded=w.gate.invoke(codec.decode_ledger,artifact,check=w.gate.check)
    require(type(decoded)is codec.DecodedLedger,'actual structural decode')
    caught(lambda:w.gate.invoke(w.ops_module.attach,decoded),code='FOREIGN_STATE')
    caught(lambda:w.gate.invoke(w.ops_module.project_legacy,decoded,check=w.gate.check),code='LEGACY_NOT_REPRESENTABLE')
    require(not hasattr(w.K,'NativeInputLease'),'no decoded native lease constructor exists')
    ctx.note(actual_codec_decode=True,decoded_structural_only=True,genuine_owner_retained=True)


def E32(ctx,variant):
    if not ctx.allow_large_stream:
        raise DeferredBranch('Prospective procedural4GB stream excluded by this execution binding; no early-context or descriptor-only substitute.')
    w=ctx.world(bulk_size=3991999872);checked=[]
    def consumer(world,stage,context):
        if checked:return
        require(context is world.state.evidence_context and any(s.path==world.bulk_path for s in context.specs),
                'actual completed evidence context contains bulk descriptor')
        error=caught(lambda:context.bytes_for(world.bulk_path),code='CAPTURE_NOT_REQUESTED')
        require(type(error)is world.K.CaptureNotRequested,'isolated hash-only byte-consumption refusal')
        caught(lambda:world.K.request_native_inputs(world.state,(world.file_refs[-1],)),code='NATIVE_ROUTE_UNAVAILABLE')
        file=world.held_states[-1]
        require(file.hash_complete and file.assembly is None and file.blob is None and not file.capture_complete,
                'actual streamed bulk hash without4GB capture assembly/blob')
        require(file.actual_sha==world.inputs['staged_4GB_digest'],'independent procedural4GB digest')
        checked.append(True)
    snap=w.finish(checker_hook=consumer)
    require(checked==[True] and snap.to_dict()['pure_seam_complete'] is True,'actual source path completed prospective stream')
    require(w.originals.delivered[w.bulk_path]==3991999872,'full procedural4GB delivery actually completed')
    require(w.geometry==ctx.inputs['large_geometry'],'exact independently derived large original7 reservations')
    require(w.state.profile.Cmax==16384 and ctx.inputs['joint_physical_call_warning']==19079,
            'original7 ceiling distinct from unresolved joint physical budget')
    ctx.note(evidence_kind='ACTUAL_PROCEDURAL_STREAM_IF_AUTHORIZED',streamed_bulk_bytes=3991999872,
             full_geometry=w.geometry,hash_only_capture_refused=True,native_route='NATIVE_ROUTE_UNAVAILABLE',
             qualified_native_lease='DEFERRED_PREREQUISITE',physical_joint_admission=False,
             full_real_roster=False,whole_R09=False)


CASES={f'E{i:02d}':globals()[f'E{i:02d}'] for i in range(1,33)}
