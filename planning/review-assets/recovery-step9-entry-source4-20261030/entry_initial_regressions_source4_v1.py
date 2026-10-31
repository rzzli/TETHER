"""Three pre-fix authored assertions; importing this file imports no subject.

The Source1 smoke executed only test01 and retained its setup failure.
The distinct Source2 runner may execute all three unchanged checks plus one
committed-fact converse. No partial Core or runtime alias is permitted.
"""
from entry_independent_test_support_v4 import require


def test01_valid_entry(world):
    state = world.enter()
    require(state is world.attempt.state, 'entry returned the actual retained Core')
    require(world.clock.calls >= 1 and world.events[0] == ('clock', 1),
            'original clock sample precedes application work')
    require(not world.originals.calls and not world.loader.compiler_observations,
            'normal entry returns before original opens and helper execution')
    require(state.reservation_ready, 'bootstrap output reservation completed')
    return state


def test02_normal_captured_helpers_finish(world):
    test01_valid_entry(world)
    snapshot = world.finish()
    data = snapshot.to_dict()
    require(world.ops.state is world.view.core is world.state,
            'captured helpers share the original Core')
    names = world.inputs['module_names']
    require({r['module'] for r in world.loader.compiler_observations} ==
            {names['codec'], names['owner_ops'], names['file_view']},
            'all three actual helper bodies executed through captured loader')
    require(data['status'] == 'PURE_SEAM_COMPLETE_CONSISTENT',
            'normal continuation completes through actual sink facade')
    require(data['pure_seam_complete'] is True, 'normal final completion')
    for field in ('journal_closed', 'receipt_acknowledged', 'seal_acknowledged',
                  'final_clock_passed', 'pure_owner_ack'):
        require(data['terminal'][field] is True, 'actual terminal ACK ' + field)
    require(sum(world.originals.close_attempts.values()) == world.geometry['original_closes'],
            'normal once-only original cleanup')
    return snapshot


def test03_staged_scalar_has_no_cleanup_authority(world):
    test01_valid_entry(world)
    K = world.K
    original_observe = K.RawCallStore.observe
    fault = MemoryError('independent staged scalar before native commit')
    injected = []

    def interrupted(store, ref, axis, value):
        if not injected and ref.api == 'CreateFileW' and axis == 'scalar':
            injected.append(ref)
            store.stage_axis(ref, axis, value)
            raise fault
        return original_observe(store, ref, axis, value)

    K.RawCallStore.observe = interrupted
    cleanup_error = None
    try:
        observed = None
        try:
            world.bootstrap()
        except BaseException as error:
            observed = error
        require(observed is fault and len(injected) == 1,
                'original staged-publication error propagates by identity')
        ref = injected[0]
        axis = world.gate.invoke(world.state.raw_call_view, ref).axis('scalar')
        require(axis.native_state == 'STAGED_UNCOMMITTED', 'actual bank remains staged')
        require(axis.raw_payload_bits == 1000 and axis.known_value is None,
                'raw handle bits retained without committed handle authority')
        try:
            world.cleanup()
        except BaseException as error:
            cleanup_error = error
        require(sum(world.originals.close_attempts.values()) == 0,
                'staged handle grants no CloseHandle right through Python cache')
        require(world.state.primary is fault, 'cleanup retains the original first error')
        require(cleanup_error is None, 'quarantined cleanup returns retained evidence')
        snapshot = world.first_snapshot
        copied = snapshot.raw_call(ref.ordinal).axis('scalar')
        require(copied.native_state == 'STAGED_UNCOMMITTED' and
                copied.raw_payload_bits == 1000 and copied.known_value is None,
                'genuine immutable snapshot preserves the non-authoritative raw fact')
        refusal = None
        try:
            snapshot.require_role1_representable()
        except K.KernelRefusal as error:
            refusal = error
        require(refusal is not None and refusal.code == 'NATIVE_STATE_NOT_REPRESENTABLE',
                'projection may not erase staged native information')
        return snapshot
    finally:
        K.RawCallStore.observe = original_observe


def test04_committed_scalar_survives_cache_boundary_failure(world):
    test01_valid_entry(world)
    K = world.K
    original_observe = K.RawCallStore.observe
    fault = MemoryError('independent committed scalar before cache acknowledgment')
    injected = []

    def interrupted(store, ref, axis, value):
        result = original_observe(store, ref, axis, value)
        if not injected and ref.api == 'CreateFileW' and axis == 'scalar':
            injected.append(ref)
            raise fault
        return result

    K.RawCallStore.observe = interrupted
    try:
        observed = None
        try:
            world.bootstrap()
        except BaseException as error:
            observed = error
        require(observed is fault and len(injected) == 1,
                'original error propagates after actual native commit')
        ref = injected[0]
        call = world.state.registry._calls[ref.ordinal]
        require(call.scalar is K.UNOBSERVED, 'cache assignment did not complete')
        axis = world.gate.invoke(world.state.raw_call_view, ref).axis('scalar')
        require(axis.native_state == 'COMMITTED' and axis.raw_payload_bits == 1000 and
                type(axis.known_value) is int and axis.known_value == 1000,
                'committed native raw fact remains independently known')
        require(world.state.committed_fact(call, 'scalar') == 1000,
                'inspection uses committed bank authority')
        before_calls = len(world.originals.calls)
        before = world.gate.invoke(world.state.snapshot)
        copied = before.raw_call(ref.ordinal).axis('scalar')
        require(copied.native_state == 'COMMITTED' and copied.known_value == 1000,
                'cold snapshot preserves committed known lower bound')
        require(before.raw_call(ref.ordinal).facts['scalar'] == dict(tag='HANDLE', value=1000),
                'copied Python fact projection derives authority from committed bank')
        require(before.to_dict()['files'][ref.file_ref.id]['handle_fact'] == dict(tag='HANDLE', value=1000),
                'cold file projection retains committed handle without healing cache')
        require(call.scalar is K.UNOBSERVED and len(world.originals.calls) == before_calls,
                'cold report neither heals the cache nor retries binding')
        world.cleanup()
        require(sum(world.originals.close_attempts.values()) == 1,
                'committed bank handle grants exactly one cleanup close')
        require(world.state.primary is fault, 'cleanup preserves original first failure')
        require(call.scalar is K.UNOBSERVED, 'cleanup does not heal interrupted cache')
        final = world.first_snapshot
        copied = final.raw_call(ref.ordinal).axis('scalar')
        require(copied.native_state == 'COMMITTED' and copied.known_value == 1000,
                'terminal immutable snapshot retains committed native authority')
        calls_after_cleanup = len(world.originals.calls)
        again = world.gate.invoke(world.state.snapshot)
        require(again is final and len(world.originals.calls) == calls_after_cleanup and
                sum(world.originals.close_attempts.values()) == 1 and call.scalar is K.UNOBSERVED,
                'cached terminal getter does not retry, double-close or heal')
        return final
    finally:
        K.RawCallStore.observe = original_observe


def test05_stopped_close_normal_return_does_not_heal_cache(world):
    K = world.K
    services = world.services
    original_callback = services.raw_backend.callback
    original_observe = K.RawCallStore.observe
    fault = MemoryError('independent stopped close after native commit')
    injected = []
    caught = []

    def interrupted(store, ref, axis, value):
        result = original_observe(store, ref, axis, value)
        if not injected and ref.api == 'CloseHandle' and axis == 'scalar':
            injected.append(ref)
            raise fault
        return result

    def catches_original(ticket, args):
        try:
            return original_callback(ticket, args)
        except BaseException as error:
            if error is fault and ticket.call_ref.api == 'CloseHandle':
                caught.append(ticket.call_ref)
                return None
            raise

    # A different prebound synthetic callback is supplied BEFORE actual entry.
    # Every other service object/clock/attempt/backend and input remains exact.
    # There is no alias, Core replacement or constructor workaround.
    world.services = K.PreboundServices(
        services.clock, services.entry_attempt, K.SyntheticRawBackend(catches_original),
        services.output_backend, services.hash_factory, services.compile_exec,
        services.executing_module, services.external_root_envelope, services.trusted_modules,
        services.manifest_policy_binding)
    test01_valid_entry(world)
    world.attach_helpers()
    chosen_ref = world.file_refs[0]
    K.RawCallStore.observe = interrupted
    try:
        observed = None
        try:
            world.gate.invoke(world.view.close, chosen_ref)
        except BaseException as error:
            observed = error
        require(observed is fault and world.state.primary is fault,
                'normal callback return preserves the original stopped-close error')
        require(len(injected) == len(caught) == 1 and caught[0] is injected[0],
                'actual synthetic callback caught only the injected original fault')
        ref = injected[0]
        call = world.state.registry._calls[ref.ordinal]
        axis = world.gate.invoke(world.state.raw_call_view, ref).axis('scalar')
        world.stopped_close_probe = dict(
            ordinal=ref.ordinal, api=ref.api, native_state=axis.native_state,
            raw_payload_bits=axis.raw_payload_bits, known_value=axis.known_value,
            cache_scalar_unobserved=call.scalar is K.UNOBSERVED,
            cache_scalar=None if call.scalar is K.UNOBSERVED else call.scalar,
            call_stopped=call.stopped, wrapper_return_observed=call.wrapper_return,
            wrapper_state=call.wrapper_state, wrapper_result_is_none=call.wrapper_result is None,
            original_error_is_primary=world.state.primary is fault,
            original_error_rethrown=observed is fault,
            callback_caught_original=len(caught),
            chosen_path_close_attempts=world.originals.close_attempts[chosen_ref.spec.path])
        require(call.wrapper_return is True and call.wrapper_state == 'returned' and call.stopped is True,
                'known wrapper return remains separate from stopped raw-cache work')
        require(axis.native_state == 'COMMITTED' and axis.raw_payload_bits == 1 and axis.known_value == 1,
                'known committed close BOOL1 survives normal-return failure')
        require(world.originals.close_attempts[chosen_ref.spec.path] == 1,
                'one actual close callback attempt is retained')
        require(call.scalar is K.UNOBSERVED,
                'stopped CloseHandle normal-return path must not heal its interrupted scalar cache')
        world.cleanup()
        require(call.scalar is K.UNOBSERVED and world.state.primary is fault,
                'later cleanup retains the same original error without cache healing')
        require(world.originals.close_attempts[chosen_ref.spec.path] == 1,
                'cleanup never repeats the already-consumed close right')
        final = world.first_snapshot
        copied = final.raw_call(ref.ordinal).axis('scalar')
        require(copied.native_state == 'COMMITTED' and copied.known_value == 1,
                'terminal snapshot preserves actual committed close evidence')
        return final
    finally:
        K.RawCallStore.observe = original_observe
