"""Author new harness files from frozen Source2 files; AST/text only."""
import ast
from pathlib import Path

HERE=Path(__file__).resolve().parent
SUPPLEMENT='''

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
        services.executing_module, services.external_root_envelope, services.trusted_modules)
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
'''


def write_new(name,text):
    ast.parse(text,filename=str(HERE/name))
    with (HERE/name).open('xb') as stream:
        stream.write(text.encode('utf-8'))


def main():
    original=(HERE/'entry_initial_regressions_v2.py').read_bytes().decode('utf-8')
    updated=original+SUPPLEMENT
    old_methods={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body
                 if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}
    new_methods={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(updated).body
                 if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}
    assert len(old_methods)==4 and len(new_methods)==5
    assert all(new_methods[k]==v for k,v in old_methods.items())
    write_new('entry_initial_regressions_v3.py',updated)
    runner=(HERE/'run_entry_source2_regressions_v1.py').read_bytes().decode('utf-8')
    runner=runner.replace('Fresh Source2 worlds for three unchanged checks and one F2 converse.',
                          'Fresh Source2 worlds for four preserved checks and one stopped-close diagnostic.')
    runner=runner.replace('ENTRY-SOURCE2-REGRESSION-BINDING-v1.json','ENTRY-SOURCE2-DIAGNOSTIC-BINDING-v2.json')
    runner=runner.replace('ENTRY-SOURCE2-REGRESSION-ATTEMPT-v1.json','ENTRY-SOURCE2-DIAGNOSTIC-ATTEMPT-v2.json')
    runner=runner.replace('ENTRY-SOURCE2-REGRESSION-PROOF-v1.json','ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json')
    runner=runner.replace("'test04_committed_scalar_survives_cache_boundary_failure')",
                          "'test04_committed_scalar_survives_cache_boundary_failure',\n           'test05_stopped_close_normal_return_does_not_heal_cache')")
    runner=runner.replace('AUTHORIZED_SOURCE2_FOUR_REGRESSIONS_ONLY',
                          'AUTHORIZED_SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC')
    runner=runner.replace('closed four-check suite','closed five-check diagnostic suite')
    runner=runner.replace('entry_initial_regressions_v2','entry_initial_regressions_v3')
    runner=runner.replace('SOURCE2_FOUR_REAL_ENTRY_REGRESSIONS_ONLY',
                          'SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC')
    needle='original_events=list(world.events))'
    assert runner.count(needle)==1
    runner=runner.replace(needle,"original_events=list(world.events),\n                  stopped_close_probe=getattr(world, 'stopped_close_probe', None))")
    write_new('run_entry_source2_regressions_v2.py',runner)
    print('AST-only new diagnostic authored; original four test ASTs unchanged.')


if __name__=='__main__':
    main()
