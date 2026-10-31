"""Three pre-fix authored assertions; importing this file imports no subject.

The initial Source1 smoke runner executes only test01. The other two checks
remain NOT_REACHED after an entry-construction failure. No runtime workaround
may manufacture a partial Core to reach them.
"""
from entry_independent_test_support_v1 import require


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
