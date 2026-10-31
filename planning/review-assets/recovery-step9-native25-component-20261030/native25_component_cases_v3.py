"""Prospective assertions from frozen native25; never imports a subject.

Only the Root-bound runner supplies the genuine, freshly pinned kernel/world.
DATA and source-runtime observations do not qualify native C or physical I/O.
"""
import struct


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def refused(ctx, function, code):
    try:
        result = function()
    except BaseException as error:
        ctx.errors.append(error)
        require(getattr(error, 'code', None) == code, 'exact refusal ' + code)
        return error
    ctx.unexpected_returns.append(result)
    raise AssertionError('required refusal was absent: ' + code)


def dref(ctx, api='CreateFileW', requested=None, capacity=4):
    x = ctx.data(capacity)
    ref = ctx.call(x.reserve_fragment, api, requested=requested)
    return x, ref


def axis(ctx, x, ref, name='scalar'):
    return ctx.call(x.raw_call_view, ref).axis(name)


def scalar(ctx, x, ref, value):
    ctx.call(x.observe, ref, 'scalar', value)


def n01_data(ctx):
    x, ref = dref(ctx)
    a = axis(ctx, x, ref)
    require(a.native_state == 'UNOBSERVED' and a.raw_payload_bits == 0 and a.known_value is None, 'unobserved is not known zero')
    require(not ctx.call(x.interpret, ref)['usable_handle'], 'no data handle authority')


def n01_runtime(ctx):
    w = ctx.world()
    ref = ctx.call(w.state.reserve_call, 'CreateFileW', 'BOOTSTRAP', w.file_refs[0])
    snap = ctx.snapshot(w)
    require(not ref._state.invoked and not w.originals.calls, 'reserved is not invoked')
    require(snap.raw_call(ref.ordinal).axis('scalar').native_state == 'UNOBSERVED', 'actual reserved native axis unknown')
    require(w.state.handle(w.held_states[0]) is w.K.UNOBSERVED, 'no close right')


def interrupted(ctx, staged):
    w = ctx.world()
    ctx.call(w.load_helpers)  # actual captured code; no Ops attachment/state clone
    target = w.metadata_path
    def hook(_world, point, ref, args, carrier, observation):
        if point == 'entered' and ref.api == 'CreateFileW' and ref.file_ref.spec.path == target:
            if staged:
                carrier.stage_axis(ref, 'scalar', 101)
            else:
                w.state.raw_store.write_payload(ref, 'scalar', 101)
            observation['handled_by_injected_original'] = True
    w.raw_hook = hook
    refused(ctx, lambda: ctx.call(w.state.port.acquire, w.specs[-2]), 'RAW_RETURN_UNKNOWN')
    c = w.originals.refs[-1]._state
    snap = ctx.snapshot(w)
    a = snap.raw_call(c.ordinal).axis('scalar')
    require(a.raw_payload_bits == 101 and a.known_value is None, 'provisional bits retained without value authority')
    require(a.native_state == ('STAGED_UNCOMMITTED' if staged else 'UNOBSERVED'), 'exact native state')
    require(w.state.handle(w.held_states[-2]) is w.K.UNOBSERVED, 'no target ownership from provisional bits')
    require(w.held_states[-2]._known_read_bytes == 0, 'no target progress')
    refused(ctx, lambda: ctx.call(w.state.require_role1_representable, snap), 'NATIVE_STATE_NOT_REPRESENTABLE')
    refused(ctx, lambda: ctx.call(w.ops_module.project_legacy, snap, check=ctx.gate.check), 'NATIVE_STATE_NOT_REPRESENTABLE')


def n02_data(ctx):
    x, ref = dref(ctx)
    ctx.call(x.stage_axis, ref, 'scalar', 101)
    a = axis(ctx, x, ref)
    require(a.native_state == 'STAGED_UNCOMMITTED' and a.raw_payload_bits == 101 and a.known_value is None, 'staged authority unknown')


def n03_data(ctx):
    x, ref = dref(ctx)
    ctx.call(x.write_payload, ref, 'scalar', 101)
    a = axis(ctx, x, ref)
    require(a.native_state == 'UNOBSERVED' and a.raw_payload_bits == 101 and a.known_value is None, 'payload before stage remains inspectable unknown')


def n04_data(ctx):
    x, ref = dref(ctx)
    scalar(ctx, x, ref, None)
    a = axis(ctx, x, ref)
    require(a.native_state == 'COMMITTED' and a.known_value == 0 and a.raw_payload_bits == 0 and a.kind == 'HANDLE64', 'native NULL is committed zero')
    require(not ctx.call(x.interpret, ref)['usable_handle'], 'native NULL unusable')


def n04_runtime(ctx):
    w = ctx.world()
    def hook(_world, point, ref, args, carrier, observation):
        if point == 'entered' and ref.api == 'CreateFileW':
            carrier.store_scalar(ref, None)
            observation['handled_by_injected_original'] = True
    w.raw_hook = hook
    refused(ctx, lambda: ctx.call(w.state.port.acquire, w.specs[-2]), 'RAW_RETURN_UNKNOWN')
    snap = ctx.snapshot(w)
    require(snap.raw_call(0).axis('scalar').known_value == 0, 'native zero retained')
    require(not w.held_states[-2].close_reserved, 'no NULL close right')
    require(sum(r['api'] == 'CloseHandle' for r in w.originals.calls) == 0, 'no NULL close call')


def bool_data(ctx, value, bits, success):
    x, ref = dref(ctx, 'ReadFile', 16)
    scalar(ctx, x, ref, value)
    ctx.call(x.observe, ref, 'count', 0)
    a = axis(ctx, x, ref)
    info = ctx.call(x.interpret, ref)
    require(a.known_value == value and a.raw_payload_bits == bits, 'BOOL bits/value preserved')
    require(info['count_defined'] is success and info['progress'] == 0, 'noncanonical BOOL success without normalization')


def read_case(ctx, false=False):
    w = ctx.world()
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    ctx.call(w.state.port.inspect, ref)
    def hook(_world, point, call, args, carrier, observation):
        if point == 'entered' and call.api == 'ReadFile':
            # Real canonical raw-store calls model independent native axes;
            # no first Python-cache value or fixture completion is fabricated.
            store = w.state.raw_store
            store.observe(call, 'scalar', 0 if false else 1)
            store.observe(call, 'count', 0)
            if false:
                store.observe(call, 'error_value', 0)
                store.observe(call, 'error_definition', True)
            observation['handled_by_injected_original'] = True
    w.raw_hook = hook
    refused(ctx, lambda: ctx.call(w.state.port.hash_capture, ref), 'READ_COUNT_UNKNOWN' if false else 'READ_PROGRESS_INCOMPLETE')
    snap = ctx.snapshot(w)
    call = w.originals.refs[-1]
    row = snap.raw_call(call.ordinal)
    require(row.axis('count').native_state == 'COMMITTED' and row.axis('count').known_value == 0, 'known count zero')
    require(w.state.defined(call._state) is (not false), 'definedness distinct from raw count')
    f = w.held_states[-2]
    require(f._known_read_bytes == 0 and f.hashed == 0 and f.captured == 0 and not f.hash_complete, 'no zero-progress success')
    require(sum(r['api'] == 'ReadFile' for r in w.originals.calls) == 1, 'no zero-read retry')
    if false:
        require(row.axis('error_value').known_value == 0 and row.axis('error_definition').known_value is True, 'defined error DWORD0 is observed')


def n08(ctx):
    x, ref = dref(ctx, 'ReadFile', 16)
    ctx.call(x.observe, ref, 'error_value', 0)
    require(axis(ctx, x, ref, 'error_value').known_value == 0, 'error word zero observed')
    require(axis(ctx, x, ref, 'error_definition').native_state == 'UNOBSERVED', 'definition independently unknown')
    require(ctx.call(x.interpret, ref)['error_definition'] is None, 'no defined error classification')


def n09(ctx):
    x, ref = dref(ctx, 'ReadFile', 16)
    scalar(ctx, x, ref, 0)  # explicit documented failure-branch setup
    ctx.call(x.observe, ref, 'error_definition', True)
    require(axis(ctx, x, ref, 'error_definition').known_value is True, 'definition observed first')
    require(axis(ctx, x, ref, 'error_value').native_state == 'UNOBSERVED', 'error transport still unknown')
    require(not ctx.call(x.interpret, ref)['error_value_observed'], 'no guessed error word')


def n10(ctx):
    w = ctx.world()
    original = MemoryError('native25-original-conversion-model')
    w.originals.handles[w.metadata_path] = 101
    def hook(_world, point, ref, args, carrier, observation):
        if point == 'after_scalar' and ref.api == 'CreateFileW':
            raise original
    w.raw_hook = hook
    try:
        ctx.call(w.state.port.acquire, w.specs[-2])
    except BaseException as error:
        require(error is original and w.state.primary is original, 'same original wrapper MemoryError')
        ctx.errors.append(error)
    else:
        raise AssertionError('wrapper fault absent')
    snap = ctx.snapshot(w)
    call = w.originals.refs[-1]
    require(snap.raw_call(call.ordinal).axis('scalar').known_value == 101 and not call._state.wrapper_return, 'committed handle survives wrapper fault')
    w.raw_hook = None
    ctx.call(w.state.port.close, w.file_refs[-2])
    require(sum(r['api'] == 'CloseHandle' for r in w.originals.calls) == 1, 'one actual cleanup callback')
    refused(ctx, lambda: ctx.call(w.state.port.close, w.file_refs[-2]), 'INVALID_INPUT')
    require(w.state.primary is original, 'cleanup preserved original error')


def close_case(ctx, false=False):
    w = ctx.world()
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    original = KeyboardInterrupt('native25-original-close-interrupt')
    def hook(_world, point, call, args, carrier, observation):
        if call.api != 'CloseHandle':
            return
        if false and point == 'entered':
            carrier.store_scalar(call, 0)
            carrier.store_error_value(call, 5)
            carrier.store_error_definition(call, True)
            observation['handled_by_injected_original'] = True
        elif not false and point == 'before_scalar':
            carrier.store_scalar(call, 2)
            raise original
    w.raw_hook = hook
    if false:
        refused(ctx, lambda: ctx.call(w.state.port.close, ref), 'INVALID_INPUT')
    else:
        try:
            ctx.call(w.state.port.close, ref)
        except BaseException as error:
            require(error is original and w.state.primary is original, 'same close KeyboardInterrupt')
            ctx.errors.append(error)
        else:
            raise AssertionError('close interrupt absent')
    snap = ctx.snapshot(w)
    call = w.originals.refs[-1]
    require(snap.raw_call(call.ordinal).axis('scalar').known_value == (0 if false else 2), 'original close BOOL retained')
    f = snap.to_dict()['files'][-2]
    require(f['close_reserved'] and f['close_success'] is (not false), 'right consumed and exact known close result')
    refused(ctx, lambda: ctx.call(w.state.port.close, ref), 'INVALID_INPUT')
    require(sum(r['api'] == 'CloseHandle' for r in w.originals.calls) == 1, 'no second actual close callback')


def n13(ctx):
    x, ref = dref(ctx, 'ReadFile', 1048576)
    scalar(ctx, x, ref, -1)
    ctx.call(x.observe, ref, 'count', 0xffffffff)
    refused(ctx, lambda: ctx.call(x.interpret, ref), 'COUNT_RANGE')
    require(axis(ctx, x, ref, 'count').known_value == 0xffffffff, 'raw out-of-range word retained')


def n14_foreign(ctx):
    a = ctx.world()
    other = ctx.world()
    refs = []
    for w in (a, other):
        for _ in range(5):
            r = ctx.call(w.state.reserve_call, 'GetFileType', 'BOOTSTRAP', w.file_refs[0])
        refs.append(r)
    require(refs[0].ordinal == refs[1].ordinal == 4 and a.state is not other.state and a.state.nonce is not other.state.nonce, 'genuine equal ordinal distinct owners')
    refused(ctx, lambda: ctx.call(a.state.raw_store.axis, refs[1], 'scalar'), 'FOREIGN_RAW_REF')
    require(not a.originals.calls and not other.originals.calls, 'foreign ref adds no original callback')


def n14_expired(ctx):
    w = ctx.world()
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    call = w.originals.refs[-1]
    before = w.state.raw_store.copy_row(call)
    refused(ctx, lambda: ctx.call(w.state.raw_store.stage_axis, call, 'error_value', 0), 'FOREIGN_RAW_REF')
    require(w.state.raw_store.copy_row(call) == before and len(w.originals.calls) == 1, 'expired write refused without erasing cold fact')


def n15_same(ctx):
    x, ref = dref(ctx, 'ReadFile', 16)
    scalar(ctx, x, ref, 1)
    ctx.call(x.observe, ref, 'count', 3)
    old = ctx.call(x.raw_call_view, ref)
    ctx.call(x.observe, ref, 'count', 3)
    ctx.call(x.commit_axis, ref, 'count')
    require(ctx.call(x.raw_call_view, ref).raw_row == old.raw_row, 'identical replay unchanged')


def n15_conflict(ctx):
    x, ref = dref(ctx)
    scalar(ctx, x, ref, 101)
    refused(ctx, lambda: ctx.call(x.observe, ref, 'scalar', 102), 'NATIVE_CELL_CONFLICT')
    require(axis(ctx, x, ref).known_value == 101, 'first committed value retained')


def n15_runtime(ctx):
    w = ctx.world()
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    ctx.call(w.state.port.inspect, ref)
    def hook(_world, point, call, args, carrier, observation):
        if point == 'after_count' and call.api == 'ReadFile':
            before = w.held_states[-2]._known_read_bytes
            carrier.store_count(call, call.requested)
            require(w.held_states[-2]._known_read_bytes == before, 'no duplicate fold')
    w.raw_hook = hook
    ctx.call(w.state.port.hash_capture, ref)
    old = ctx.snapshot(w)
    old_bytes = tuple(row.raw_row for row in old._raw_calls)
    ctx.call(w.state.port.close, ref)
    calls = len(w.originals.calls)
    clock_calls = w.clock.calls
    for _ in range(3):
        for i in range(old.raw_call_count):
            old.raw_call(i).axis('count')
    require(tuple(row.raw_row for row in old._raw_calls) == old_bytes and w.clock.calls == clock_calls and len(w.originals.calls) == calls, 'cold immutable snapshots do not refresh or retry')


def clock_case(ctx, kind):
    w = ctx.world(zero_clock=True)
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    require(w.state.origin.start == 0 and w.state.origin.work_end == 295 and w.state.origin.hard_end == 300, 'original cutoffs')
    if kind == 'hard':
        w.clock.set(300)
        refused(ctx, lambda: ctx.call(w.state.port.close, ref), 'HARD_DEADLINE')
        require(sum(r['api'] == 'CloseHandle' for r in w.originals.calls) == 0, 'hard stop forbids close callback')
        w.native25_hard_stop = True
        ctx.notes.append('Known fictional right retained; cleanup/terminal blocked by original hard deadline, not reported closed.')
        return
    w.clock.set(295)
    refused(ctx, lambda: ctx.call(w.state.port.inspect, ref), 'WORK_DEADLINE')
    require(len(w.originals.calls) == 1, 'no new work at cutoff')
    if kind == 'cleanup':
        w.clock.set(299)
        ctx.call(w.state.port.close, ref)
        require(sum(r['api'] == 'CloseHandle' for r in w.originals.calls) == 1, 'known cleanup allowed at299')


def n17(ctx):
    w = ctx.world()
    ref = ctx.call(w.state.port.acquire, w.specs[-2])
    require(bytes(memoryview(w.state._query_buffer._data)[:8]) == bytes(8), 'real query buffer initially zero')
    def hook(_world, point, call, args, carrier, observation):
        if point == 'entered' and call.api == 'GetFileInformationByHandleEx':
            carrier.store_scalar(call, 0)
            observation['handled_by_injected_original'] = True
    w.raw_hook = hook
    refused(ctx, lambda: ctx.call(w.state.port.inspect, ref), 'IDENTITY_INCOMPLETE')
    c = w.originals.refs[-1]._state
    require(w.state.committed_fact(c, 'scalar') == 0 and c.query_bytes is None and w.held_states[-2].identity_state != 'verified', 'known scalar0 cannot promote zero initialized frame')
    ctx.snapshot(w)


def search(ctx):
    x, first = dref(ctx, 'FindFirstFileExW')
    scalar(ctx, x, first, 101)
    return x, ctx.call(x.establish_search, first)


def n18(ctx):
    x, ref = dref(ctx, 'FindFirstFileExW')
    scalar(ctx, x, ref, (1 << 64)-1)
    ctx.call(x.observe, ref, 'error_value', 2)
    ctx.call(x.observe, ref, 'error_definition', True)
    info = ctx.call(x.interpret, ref)
    require(not info['search_right'] and not info['natural_end'] and not info['frame_defined'], 'initial find failure is not established natural end')
    refused(ctx, lambda: ctx.call(x.establish_search, ref), 'LEASE_NOT_LIVE')


def n19_end(ctx):
    x, target = search(ctx)
    ref = ctx.call(x.reserve_fragment, 'FindNextFileW', 'SEARCH', target)
    scalar(ctx, x, ref, 0)
    ctx.call(x.observe, ref, 'error_value', 18)
    ctx.call(x.observe, ref, 'error_definition', True)
    info = ctx.call(x.interpret, ref)
    require(info['natural_end'] and not info['frame_defined'], 'established search end DATA')


def n19_close(ctx):
    x, target = search(ctx)
    ref = ctx.call(x.reserve_fragment, 'FindClose', 'SEARCH', target)
    require(target.closed, 'reservation consumes DATA search right')
    scalar(ctx, x, ref, 1)
    before = len(x._calls)
    refused(ctx, lambda: ctx.call(x.reserve_fragment, 'FindClose', 'SEARCH', target), 'LEASE_NOT_LIVE')
    require(len(x._calls) == before, 'no second data close reservation')


def n20(ctx):
    x, target = search(ctx)
    before = len(x._calls)
    refused(ctx, lambda: ctx.call(x.reserve_fragment, 'CloseHandle', 'ORIGINAL', target), 'WRONG_CLOSER')
    require(not target.closed and len(x._calls) == before, 'wrong closer cannot consume target')


def n21_atoms(ctx):
    apis = ('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle','GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')
    require(ctx.K.ALL_APIS == apis, 'frozen14 table')
    x = ctx.data(20)
    target = None
    for name in apis:
        ref = ctx.call(x.reserve_fragment, name, 'SEARCH' if name.startswith('Find') else 'ORIGINAL', target if name in ('FindNextFileW','FindClose') else None, 16 if name in ('ReadFile','WriteFile') else None)
        expected = 'HANDLE64' if name in ('CreateFileW','FindFirstFileExW') else 'DWORD32' if name in ('GetFileType','GetFinalPathNameByHandleW') else 'BOOL32_BITS'
        require(axis(ctx, x, ref).kind == expected, 'exact API scalar kind')
        if name == 'FindFirstFileExW':
            scalar(ctx, x, ref, 101)
            target = ctx.call(x.establish_search, ref)


def n21_runtime(ctx):
    w = ctx.world()
    refused(ctx, lambda: ctx.call(w.state.reserve_call, 'WriteFile', 'ORIGINAL', w.file_refs[-2], 16), 'ACTOR_PROFILE_UNQUALIFIED')
    require(not w.originals.calls and not w.state.registry._calls, 'no physical/output activation')


def n22(ctx):
    w, ref = ctx.bulk_world()
    refused(ctx, lambda: ctx.call(w.state.request_native_input, ref), 'NATIVE_ROUTE_UNAVAILABLE')
    f = w.held_states[-1]
    require(f.hash_complete and f.assembly is None and f.blob is None and f.capture_state == 'NOT_REQUESTED', 'hash-only never promoted')


def n23_bytes(ctx):
    w, ref = ctx.bulk_world()
    f = w.held_states[-1]
    context = ctx.call(w.state.make_context, (ref.spec,), {}, {ref.spec.path: f.actual_sha})
    require(context.owner is w.state, 'actual source-issued subset context')
    refused(ctx, lambda: ctx.call(context.bytes_for, ref.spec.path), 'CAPTURE_NOT_REQUESTED')
    require(f.assembly is None and f.blob is None and not f.capture_complete, 'absent bulk blob distinct from empty capture')
    # Same already-declared recipe at zero length, independently pinned input.
    empty = ctx.world(empty=True)
    for index in (-2, -1):
        r = ctx.call(empty.state.port.acquire, empty.specs[index])
        ctx.call(empty.state.port.inspect, r)
        ctx.call(empty.state.port.hash_capture, r)
    captured, bulk = empty.held_states[-2:]
    require(captured.capture_complete and captured.blob == b'' and bulk.blob is None and not bulk.capture_complete, 'genuine captured empty versus hash-only empty')
    ec = ctx.call(empty.state.make_context, (captured.spec, bulk.spec), {captured.spec.path: captured.blob}, {captured.spec.path: captured.actual_sha, bulk.spec.path: bulk.actual_sha})
    require(ctx.call(ec.bytes_for, captured.spec.path) is captured.blob, 'same actual empty bytes object')
    refused(ctx, lambda: ctx.call(ec.bytes_for, bulk.spec.path), 'CAPTURE_NOT_REQUESTED')
    require(not any(r['api'] == 'ReadFile' for r in empty.originals.calls), 'zero-length facts require no invented read')


def n23_foreign(ctx):
    w, ref = ctx.bulk_world()
    refused(ctx, lambda: ctx.call(w.state.request_native_input, ref, object()), 'FOREIGN_LAUNCH_BINDING')
    ctx.notes.append('Ordinary foreign-object guard only; no qualified ChildLaunchBinding exists.')


def n24(ctx):
    w, ref = ctx.bulk_world()
    ctx.call(w.state.port.close, ref)
    require(not w.state.finalized and w.held_states[-1].close_reserved, 'actual active consumed file right')
    before = len(w.originals.calls)
    refused(ctx, lambda: ctx.call(w.state.request_native_input, ref), 'LEASE_NOT_LIVE_OR_PATH_UNKNOWN')
    require(len(w.originals.calls) == before, 'dead file refusal does not reopen')


def n25_exhaust(ctx):
    x, ref = dref(ctx, capacity=1)
    before = ctx.call(x.raw_call_view, ref).raw_row
    refused(ctx, lambda: ctx.call(x.reserve_fragment, 'GetFileType'), 'JOINT_CAP_EXCEEDED')
    require(x.raw_store.capacity == 1 and ctx.call(x.raw_call_view, ref).raw_row == before, 'bank never grows')


def n25_cap(ctx):
    refused(ctx, lambda: ctx.data(19079), 'JOINT_CAP_EXCEEDED')


def n25_layout(ctx):
    # Minimal trusted bank faults; actual objects originate in the source.
    for offset, form, value in ((0,'<H',2),(2,'<H',255),(8,'<I',2),(28,'<I',1),(143,'<B',1),(142,'<B',8)):
        x, ref = dref(ctx, 'ReadFile', 16)
        struct.pack_into(form, x.raw_store._bank, offset, value)
        refused(ctx, lambda: ctx.call(x.raw_call_view, ref), 'NATIVE_STATE_NOT_REPRESENTABLE')


def n25_kind(ctx, count=False):
    x, ref = dref(ctx, 'ReadFile', 16)
    scalar(ctx, x, ref, 1)
    ctx.call(x.observe, ref, 'count', 1)
    offset = (160 if count else 128) + 12
    struct.pack_into('<H', x.raw_store._bank, offset, 3)  # valid DWORD32, same width4
    # Frozen normative API/axis-kind relation: do not weaken after first run.
    refused(ctx, lambda: ctx.call(x.raw_call_view, ref), 'NATIVE_STATE_NOT_REPRESENTABLE')


CASES = {
    'N01.1':n01_data, 'N01.2':n01_runtime,
    'N02.1':n02_data, 'N02.2':lambda c:interrupted(c,True),
    'N03.1':n03_data, 'N03.2':lambda c:interrupted(c,False),
    'N04.1':n04_data, 'N04.2':n04_runtime,
    'N05.1':lambda c:bool_data(c,2,2,True), 'N05.2':lambda c:bool_data(c,-1,0xffffffff,True), 'N05.3':lambda c:bool_data(c,0,0,False),
    'N06.1':lambda c:read_case(c,False), 'N07.1':lambda c:read_case(c,True),
    'N08.1':n08, 'N09.1':n09, 'N10.1':n10,
    'N11.1':lambda c:close_case(c,False), 'N12.1':lambda c:close_case(c,True), 'N13.1':n13,
    'N14.1':n14_foreign, 'N14.2':n14_expired,
    'N15.1':n15_same, 'N15.2':n15_conflict, 'N15.3':n15_runtime,
    'N16.1':lambda c:clock_case(c,'work'), 'N16.2':lambda c:clock_case(c,'cleanup'), 'N16.3':lambda c:clock_case(c,'hard'),
    'N17.1':n17, 'N18.1':n18, 'N19.1':n19_end, 'N19.2':n19_close, 'N20.1':n20,
    'N21.1':n21_atoms, 'N21.2':n21_runtime, 'N22.1':n22,
    'N23.1':n23_bytes, 'N23.2':n23_foreign, 'N24.1':n24,
    'N25.1':n25_exhaust, 'N25.2':n25_cap, 'N25.3':n25_layout,
    'N25.5.scalar_kind_mismatch':lambda c:n25_kind(c,False),
    'N25.5.count_kind_mismatch':lambda c:n25_kind(c,True),
}
