"""Author distinct harness copies only; no subject or copied module import."""
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'recovery-step9-entry-source-20261029'

SUPPLEMENT = '''

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
'''


def write_new(name, text):
    path = HERE / name
    with path.open('xb') as stream:
        stream.write(text.encode('utf-8'))
    ast.parse(text, filename=str(path))


def main():
    support = (OLD / 'entry_independent_test_support_v1.py').read_bytes().decode('utf-8')
    support = support.replace('preflight_entry_kernel_v1', 'preflight_entry_kernel_v2')
    write_new('entry_independent_test_support_v2.py', support)
    world = (OLD / 'entry_independent_world_v1.py').read_bytes().decode('utf-8')
    world = world.replace('entry_independent_test_support_v1', 'entry_independent_test_support_v2')
    write_new('entry_independent_world_v2.py', world)
    original = (OLD / 'entry_initial_regressions_v1.py').read_bytes().decode('utf-8')
    regression = original.replace('entry_independent_test_support_v1', 'entry_independent_test_support_v2')
    regression = regression.replace('The initial Source1 smoke runner executes only test01. The other two checks\nremain NOT_REACHED after an entry-construction failure. No runtime workaround\nmay manufacture a partial Core to reach them.',
        'The Source1 smoke executed only test01 and retained its setup failure.\nThe distinct Source2 runner may execute all three unchanged checks plus one\ncommitted-fact converse. No partial Core or runtime alias is permitted.') + SUPPLEMENT
    old_methods = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(original).body
                   if isinstance(n, ast.FunctionDef) and n.name.startswith('test')}
    new_methods = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(regression).body
                   if isinstance(n, ast.FunctionDef) and n.name.startswith('test')}
    assert all(new_methods[name] == body for name, body in old_methods.items())
    assert len(old_methods) == 3 and len(new_methods) == 4
    write_new('entry_initial_regressions_v2.py', regression)
    print('AST-only authoring complete: three original test ASTs identical; one supplemental method.')


if __name__ == '__main__':
    main()
