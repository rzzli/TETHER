"""Genuine Source4 E08 assertions, authored before any subject execution.

The 52 frozen metadata outcomes are not full-entry-success predictions.
Integration controls use actual fresh helper contexts separately. No source
module, reference policy solver or old owner is imported on module load.
"""
from entry_independent_test_support_v4 import require, strict_equal
from entry_independent_world_v4 import clone_json
from entry_contract_cases_source4_v1 import Patch, caught, no_progress


REPORT_KEYS = {'schema_version', 'mode', 'status', 'node_count', 'edge_count',
               'basis_ids', 'external_anchor_ids', 'prior_root_ids', 'planned_ids',
               'unbuilt_ids', 'binding_sha256', 'envelope_sha256'}
POLICY_KEYS = {'attempted', 'prepared_report', 'issued_report',
               'execution_eligible', 'error_identity'}


def vector(ctx, ident):
    return next(row for row in ctx.literal_vectors if row['id'] == ident)


def policy_world(ctx, row):
    return ctx.world(policy_request=row['request'],
                     entry_basis_pins=row['entry_basis_pins'], policy_only=True)


def entry_error(w):
    try:
        w.enter()
    except BaseException as error:
        return error
    return None


def no_dispatch(w):
    require(not w.originals.calls and not w.loader.compiler_observations and
            not w.output.callbacks, 'no output/original/compiler callback before policy eligibility')


def same_core(w):
    state = w.state
    require(type(state) is w.K.KernelState and state is w.attempt.state,
            'actual entry-retained Core, never a fabricated partial object')
    require(w.events[0] == ('clock', 1) and w.attempt.start_cell == 100 and
            state.origin.start == 100 and state.origin.provider_ref is w.clock,
            'original first sample and provider retained')
    require(state.origin.work_end == 395 and state.origin.hard_end == 400,
            'original work/hard boundaries')
    require(state.registry._owner is state and state.raw_store.owner is state and
            state.port.owner is state and state.sink.owner is state,
            'same canonical registry/bank/facades')
    return state


def observation(w):
    # Explicitly captures one genuine snapshot. Subsequent cold checks use
    # this already-issued object, not a newly requested live row copy.
    snap = w.gate.invoke(w.state.snapshot)
    if w.first_snapshot is None:
        w.first_snapshot = snap
    data = w.gate.invoke(snap.to_dict)['manifest_policy']
    require(set(data) == POLICY_KEYS, 'exact five policy observation fields')
    return snap, data


def replace_binding(w, binding):
    s = w.services
    w.services = w.K.PreboundServices(s.clock, s.entry_attempt, s.raw_backend,
        s.output_backend, s.hash_factory, s.compile_exec, s.executing_module,
        s.external_root_envelope, s.trusted_modules, binding)


def run_literal(ctx, row):
    pristine = clone_json(row['request'])
    w = policy_world(ctx, row)
    error = entry_error(w)
    state = same_core(w)
    require(state._manifest_policy_attempted is True, 'one real policy attempt after Core construction')
    expected = row['expected']
    report = w.gate.invoke(lambda: state.manifest_policy_report)
    if expected['kind'] == 'REPORT':
        require(type(report) is w.K.ManifestPolicyReport and
                report is state._manifest_policy_prepared,
                'genuine returned report retained then issued as the same object')
        actual = w.gate.invoke(report.to_dict)
        require(set(actual) == REPORT_KEYS and strict_equal(actual, expected['report']),
                'unchanged literal exact twelve-field report')
        require(state._manifest_policy_error is None, 'later plan error is not a policy error')
        eligible = expected['report']['mode'] == 'EXECUTION'
        require(state._manifest_policy_eligible is eligible, 'mode-specific eligibility')
        if not eligible:
            require(error is None and w.plan is None, 'AUTHORING returns before executable plan requirements')
        elif error is not None:
            require(error is w.attempt.error and state._manifest_policy_report is report,
                    'later unrelated plan refusal retains successful metadata policy result')
    else:
        require(error is not None and getattr(error, 'code', None) == expected['code'],
                'unchanged literal exact policy refusal')
        require(state._manifest_policy_error is error and state.primary is error,
                'genuine original policy exception identity retained')
        require(report is None and state._manifest_policy_prepared is None and
                state._manifest_policy_eligible is False,
                'refused metadata has no report or eligibility')
    require(strict_equal(row['request'], pristine) and strict_equal(w.policy_request, pristine),
            'caller literal request unchanged by construction/entry')
    no_dispatch(w)
    ctx.note(literal_id=row['id'], expected_kind=expected['kind'],
             policy_code=None if state._manifest_policy_error is None else
                         getattr(state._manifest_policy_error, 'code', None),
             policy_report_issued=report is not None,
             later_entry_error_code=None if error is None else getattr(error, 'code', None),
             full_entry_success_claimed=False)


def I01(ctx, variant):
    w = ctx.world()
    K = w.K
    original = K.KernelState.validate_external_policy
    retained = []

    def validate(state, envelope):
        require(state is w.attempt.state and type(state) is K.KernelState,
                'Core retained before policy validation')
        require(w.events[0] == ('clock', 1) and state.origin.start == 100,
                'original entry clock before policy')
        require(state.registry._owner is state and state.raw_store.owner is state,
                'registry and raw bank exist before policy')
        no_dispatch(w)
        before = (state, state.origin, state.registry, state.raw_store, state.port, state.sink)
        result = original(state, envelope)
        require(result is state.manifest_policy_report and state._manifest_policy_eligible,
                'same-Core report issued before entry work')
        no_dispatch(w)
        retained.append(before)
        return result

    # OutputSpy's callback hook receives target/phase/data; retain its native
    # signature through a generic forwarding function below.
    def check_output(*unused):
        state = w.attempt.state
        require(state is not None and state.manifest_policy_report is not None and
                state._manifest_policy_eligible, 'output is after actual policy issuance')

    w.output.hook = check_output
    with Patch(K.KernelState, 'validate_external_policy', validate):
        w.enter()
    require(len(retained) == 1, 'one policy validation in entry')
    state = same_core(w)
    require(all(a is b for a, b in zip(retained[0],
        (state, state.origin, state.registry, state.raw_store, state.port, state.sink))),
        'policy and output preserve sole Core identities')
    w.attach_helpers()
    require(w.ops.state is w.view.core is state, 'first helper work retains actual policy Core')


def I02(ctx, variant):
    row = vector(ctx, 'authoring_planned_unbuilt_descendants')
    w = policy_world(ctx, row)
    require(entry_error(w) is None, 'AUTHORING needs no executable FileSpec plan')
    state = same_core(w)
    require(state.manifest_policy_report.to_dict()['status'] == 'AUTHORING_ONLY',
            'genuine immutable authoring report')
    actions = [lambda: state.reserve_output('authoring'),
               lambda: state.bootstrap_capture(),
               lambda: state.load_captured(w.inputs['module_names']['owner_ops']),
               lambda: state.issue_continuation(),
               lambda: state.port.acquire(w.fixtures[0]),
               lambda: state.reserve_call('CreateFileW', 'ORIGINAL', None),
               lambda: state.sink.close_journal(object(), 400)]
    for action in actions:
        caught(lambda: w.gate.invoke(action), code='POLICY_NOT_VALIDATED')
    snap, data = observation(w)
    require(data['prepared_report'] == data['issued_report'] and
            data['execution_eligible'] is False, 'authoring data never opens execution gate')
    no_dispatch(w)


def I03(ctx, variant):
    w = ctx.world()
    w.enter()
    state = same_core(w)
    report = state.manifest_policy_report
    before = (state.origin, state.nonce, state.registry, state.raw_store, state.port, state.sink)
    snap = w.finish()
    require(w.ops.state is w.view.core is snap.owner_state is state and
            w.ops_module.K is w.view_module.K is w.K,
            'genuine captured helpers and final snapshot belong to executing Core')
    require(all(a is b for a, b in zip(before,
        (state.origin, state.nonce, state.registry, state.raw_store, state.port, state.sink))),
        'helper capture and handoff preserve all canonical identities')
    require(state.manifest_policy_report is report and state._manifest_policy_eligible,
            'issued policy fact remains on same Core through normal lifecycle')
    require(snap.to_dict()['pure_seam_complete'] is True, 'actual positive helper continuation')
    require(w.geometry['early_bytes'] == w.inputs['baseline_geometry']['early_bytes'],
            'all actual newly frozen helper bytes counted')


def I04(ctx, variant):
    w = ctx.world()
    if variant == 'caller_container_alias':
        original_binding = clone_json(w.policy_request['binding'])
        # Genuine constructor already detached these caller-owned lists.
        w.policy_request['binding']['basis_ids'].append('caller.mutation')
        w.policy_request['binding']['external_tcb_pins'][0]['bytes'] += 1
        require(strict_equal(w.policy_binding.to_dict(), original_binding),
                'binding constructor detaches nested caller containers')
        w.enter()
        report = w.state.manifest_policy_report
        expected = report.to_dict()
        w.policy_request['envelope']['nodes'].clear()
        data = report.to_dict();data['basis_ids'].clear();data['status'] = 'FORGED'
        require(strict_equal(report.to_dict(), expected), 'captured envelope and report copies do not alias callers')
    elif variant == 'ordinary_rebinding':
        w.enter();state = w.state;report = state.manifest_policy_report
        for target, name, replacement in ((w.services, 'manifest_policy_binding', {}),
                (state, 'manifest_policy_binding', {}), (state, 'manifest_policy_report', {}),
                (w.policy_binding, '_values', ()), (report, '_data', {})):
            caught(lambda t=target, n=name, r=replacement: setattr(t, n, r))
        require(state.manifest_policy_binding is w.policy_binding and
                state.manifest_policy_report is report, 'ordinary aliases cannot replace genuine policy identity')
    elif variant == 'foreign_equal_source_binding':
        foreign = ctx.world()
        require(foreign.K is not w.K and foreign.policy_binding.to_dict() == w.policy_binding.to_dict(),
                'equal metadata under a genuinely separate executing namespace')
        replace_binding(w, foreign.policy_binding)
        w.skip_cleanup = True
        error = entry_error(w)
        require(getattr(error, 'code', None) == 'FOREIGN_POLICY_BINDING', 'foreign namespace binding refuses')
        same_core(w);no_dispatch(w)
    else:
        raise AssertionError('unrecognized frozen I04 branch')


def I05(ctx, variant):
    w = ctx.world();w.enter()
    state = w.state;report = state.manifest_policy_report
    snap, expected = observation(w)  # Captured once before the cold baseline.
    clocks = w.clock.calls;before = no_progress(w)
    for _ in range(3):
        require(w.gate.invoke(lambda: state.manifest_policy_report) is report, 'cache-only report getter')
        require(w.gate.invoke(report.to_dict)['status'] == 'EXECUTION_BASIS_VALIDATED', 'cold immutable report')
        require(strict_equal(w.gate.invoke(snap.to_dict)['manifest_policy'], expected), 'cached snapshot, no new row copy')
    caught(lambda: w.gate.invoke(state.validate_external_policy, w.services.external_root_envelope),
           code='POLICY_ALREADY_CHECKED')
    require(w.clock.calls == clocks and no_progress(w) == before and
            state.manifest_policy_report is report, 'no retry/resample after one validation')
    failed = policy_world(ctx, vector(ctx, 'forbidden_decision_direct'))
    first = entry_error(failed);s = same_core(failed)
    clocks = failed.clock.calls
    caught(lambda: failed.gate.invoke(s.validate_external_policy, failed.services.external_root_envelope),
           code='POLICY_ALREADY_CHECKED')
    require(failed.clock.calls == clocks and s._manifest_policy_error is first and
            s.manifest_policy_report is None, 'failed validation is not retried or healed')


def I06(ctx, variant):
    w = ctx.world();w.skip_cleanup = True
    fault = MemoryError('independent policy report allocation before return')
    def allocation(self, mint, values):
        raise fault
    with Patch(w.K.ManifestPolicyReport, '__init__', allocation):
        error = entry_error(w)
    state = same_core(w)
    require(error is fault and state.primary is fault and state._manifest_policy_error is fault,
            'original report-construction error identity')
    require(state._manifest_policy_prepared is None and state.manifest_policy_report is None and
            not state._manifest_policy_eligible, 'no report return means no prepared or issued object')
    snap, data = observation(w)
    token = snap.to_dict()['errors']['primary']['identity']
    require(w.gate.invoke(state.exception_for_token, token) is fault and data['error_identity'] is token,
            'actual diagnostic token resolves the original allocation exception')
    caught(lambda: w.gate.invoke(state.reserve_output, 'unreturned_report'), code='POLICY_NOT_VALIDATED')
    no_dispatch(w)


def I07(ctx, variant):
    w = ctx.world();w.skip_cleanup = True
    originals = []
    fault = MemoryError('independent policy prepared issuance interruption')
    if variant == 'prepared_then_final_work_clock':
        original = w.K.ManifestPolicyReport.__init__
        def delayed(self, mint, values):
            original(self, mint, values)
            originals.append(self)
            w.clock.set(395)
        with Patch(w.K.ManifestPolicyReport, '__init__', delayed):
            error = entry_error(w)
        require(getattr(error, 'code', None) == 'WORK_DEADLINE', 'original final work-clock veto')
    elif variant == 'prepared_then_issuance_bookkeeping_failure':
        original = w.K.KernelState.check
        def interrupted(state, cleanup=False):
            if state._manifest_policy_prepared is not None and state._manifest_policy_report is None and not originals:
                originals.append(state._manifest_policy_prepared)
                raise fault
            return original(state, cleanup=cleanup)
        with Patch(w.K.KernelState, 'check', interrupted):
            error = entry_error(w)
        require(error is fault, 'original post-return issuance interruption identity')
    else:
        raise AssertionError('unrecognized frozen I07 branch')
    state = same_core(w)
    require(len(originals) == 1 and state._manifest_policy_prepared is originals[0] and
            type(originals[0]) is w.K.ManifestPolicyReport,
            'actual constructor-returned object retained before eligibility step')
    require(state.manifest_policy_report is None and not state._manifest_policy_eligible and
            state.primary is error and state._manifest_policy_error is error,
            'prepared success data cannot create issued eligibility after a fault')
    snap, data = observation(w)
    require(data['prepared_report'] == originals[0].to_dict() and
            data['issued_report'] is None and data['execution_eligible'] is False,
            'genuine immutable snapshot retains prepared versus unissued values')
    token = snap.to_dict()['errors']['primary']['identity']
    require(state.exception_for_token(token) is error, 'same original diagnostic identity after unwind')
    clocks = w.clock.calls
    caught(lambda: w.gate.invoke(state.reserve_output, 'prepared_not_issued'), code='POLICY_NOT_VALIDATED')
    for _ in range(3):
        require(snap.to_dict()['manifest_policy'] == data and state.manifest_policy_report is None,
                'cold reads preserve unissued prepared data')
    caught(lambda: w.gate.invoke(state.validate_external_policy, w.services.external_root_envelope),
           code='POLICY_ALREADY_CHECKED')
    require(w.clock.calls == clocks and state._manifest_policy_prepared is originals[0],
            'no clock retry, report retry or eligibility healing')
    no_dispatch(w)


def I08(ctx, variant):
    w = policy_world(ctx, vector(ctx, 'authoring_planned_unbuilt_descendants'))
    require(entry_error(w) is None, 'genuine authoring Core')
    state = same_core(w);report = state.manifest_policy_report
    data = report.to_dict()
    require(set(data) == REPORT_KEYS, 'only twelve declared data keys')
    data['mode'] = 'EXECUTION';data['status'] = 'EXECUTION_BASIS_VALIDATED'
    data['ready'] = True
    caught(lambda: w.gate.invoke(state.reserve_output, 'forged_report'), code='POLICY_NOT_VALIDATED')
    caught(lambda: w.gate.invoke(w.K.request_native_inputs, data, ()), code='FOREIGN_NATIVE_BINDING')
    full = ctx.world();full.attach_helpers()
    before = no_progress(full)
    caught(lambda: full.gate.invoke(full.ops_module.attach, data))
    caught(lambda: full.gate.invoke(full.ops_module.project_legacy, data, check=full.gate.check))
    require(no_progress(full) == before, 'ordinary report dictionaries cannot become contexts or continuations')
    foreign = ctx.world();replace_binding(foreign, data);foreign.skip_cleanup = True
    error = entry_error(foreign)
    require(getattr(error, 'code', None) == 'FOREIGN_POLICY_BINDING', 'status dictionary is not an actual binding')
    require(state.manifest_policy_report is report and not state._manifest_policy_eligible,
            'data mutation cannot grant execution authority')
    no_dispatch(w);no_dispatch(foreign)


def I09(ctx, variant):
    fault = MemoryError('independent later work error after known usable handle')
    injected = []
    def hook(w, point, ref, args, carrier, observation):
        if not injected and point == 'after_scalar' and ref.api == 'CreateFileW':
            injected.append(ref)
            raise fault
    w = ctx.world(raw_hook=hook);w.enter();state = w.state
    report = state.manifest_policy_report
    caught(lambda: w.gate.invoke(state.port.acquire, w.specs[0]), same=fault)
    require(len(injected) == 1 and state.handle(w.held_states[0]) == 1000,
            'later fault retains committed usable native right')
    call = state.registry._calls[injected[0].ordinal]
    old_cache = call.scalar
    require(call.stopped and state.primary is fault, 'same failed call remains stopped with original error')
    if variant == 'fresh_cleanup_after_later_work_error':
        w.clock.set(396)
        w.gate.invoke(state.port.close, w.file_refs[0])
        require(w.originals.close_attempts[w.specs[0].path] == 1,
                'valid policy permits fresh once-only known-right cleanup below hard end')
    elif variant == 'cleanup_blocked_at_original_hard_end':
        w.clock.set(400)
        caught(lambda: w.gate.invoke(state.port.close, w.file_refs[0]), code='HARD_DEADLINE')
        require(w.originals.close_attempts[w.specs[0].path] == 0,
                'original hard end blocks close, no renewed policy timer')
    else:
        raise AssertionError('unrecognized frozen I09 branch')
    require(call.scalar is old_cache and state.primary is fault and
            state.manifest_policy_report is report and state._manifest_policy_eligible,
            'fresh cleanup never heals old work or revokes an already issued policy fact')


def I10(ctx, variant):
    if variant == 'constructor_structural_refusal':
        w = ctx.world()
        value = clone_json(w.policy_request['binding'])
        value['basis_ids'] = tuple(value['basis_ids'])  # Ordinary wrong exact container.
        caught(lambda: w.gate.invoke(w.K.ManifestPolicyBinding, value['mode'],
            value['current_decision_id'], value['current_output_ids'], value['basis_ids'],
            value['external_tcb_pins'], value['prior_metadata_pins']), code='POLICY_SCHEMA')
        require(w.clock.calls == 0 and not w.attempt.attempted and w.attempt.state is None,
                'genuine constructor structural refusal precedes entry and any original sample')
        no_dispatch(w)
    elif variant == 'valid_shell_bad_semantics_reaches_core':
        row = vector(ctx, 'unknown_mode_domain')
        w = policy_world(ctx, row)
        require(type(w.policy_binding) is w.K.ManifestPolicyBinding and w.clock.calls == 0,
                'bad semantic value passes only genuine bounded constructor shell')
        error = entry_error(w);same_core(w)
        require(getattr(error, 'code', None) == 'POLICY_DOMAIN' and
                w.state._manifest_policy_error is error, 'semantic/domain refusal occurs after original Core')
        no_dispatch(w)
    else:
        raise AssertionError('unrecognized frozen I10 branch')


INTEGRATION = {name: globals()[name] for name in
               ('I01', 'I02', 'I03', 'I04', 'I05', 'I06', 'I07', 'I08', 'I09', 'I10')}
