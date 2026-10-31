"""One authorized Source1 entry attempt; never invokes deeper regressions.

The fixed binding must be supplied by Root. Importing this runner performs no
subject import. No runtime alias, partial-Core construction or entry retry is
permitted. A later corrected-source runner may use the frozen three checks.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE = Path(__file__).resolve().parent
BINDING = HERE / 'ENTRY-SOURCE1-SMOKE-BINDING-v1.json'
ATTEMPT = HERE / 'ENTRY-SOURCE1-SMOKE-ATTEMPT-v1.json'
PROOF = HERE / 'ENTRY-SOURCE1-SMOKE-PROOF-v1.json'


def exact_pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_exact(pin):
    path = Path(pin['path']).resolve()
    raw = path.read_bytes()
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise RuntimeError('pinned preparation changed: ' + str(path))
    return raw


def save_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('utf-8'))


def error_data(error):
    if error is None:
        return None
    frames = []
    tb = error.__traceback__
    while tb is not None:
        frames.append(dict(file=tb.tb_frame.f_code.co_filename, line=tb.tb_lineno,
                           function=tb.tb_frame.f_code.co_name))
        tb = tb.tb_next
    args = [x if type(x) in (str, int, bool, type(None)) else
            {'type': type(x).__module__ + '.' + type(x).__qualname__}
            for x in error.args]
    code = getattr(error, 'code', None)
    return dict(type=type(error).__module__ + '.' + type(error).__qualname__,
                code=code if type(code) is str else None, args=args, frames=frames)


def trusted_module(name, pin):
    module = types.ModuleType(name)
    module.__file__ = str(Path(pin['path']).resolve())
    sys.modules[name] = module
    exec(compile(read_exact(pin), module.__file__, 'exec'), module.__dict__)
    return module


def main():
    started = time.monotonic()
    if ATTEMPT.exists() or PROOF.exists():
        raise RuntimeError('first attempt already retained; no replay')
    binding = json.loads(BINDING.read_bytes().decode('utf-8'))
    if binding['status'] != 'AUTHORIZED_SOURCE1_ENTRY_SMOKE_ONLY':
        raise RuntimeError('Root entry-smoke authorization required')
    if binding['deadline_seconds'] != 60:
        raise RuntimeError('one fixed original cooperative 60-second limit')
    read_exact(binding['execution_scope'])
    preparation = json.loads(read_exact(binding['preparation']).decode('utf-8'))
    inputs = json.loads(read_exact(binding['inputs']).decode('utf-8'))
    read_exact(binding['source_pause'])
    if binding['source_map'] != inputs['source_map']:
        raise RuntimeError('exact actual source map required')
    for pin in binding['source_map'].values():
        read_exact(pin)
    if binding['harness'] != preparation['harness']:
        raise RuntimeError('exact preregistered harness map required')
    if exact_pin(__file__) != binding['harness']['runner']:
        raise RuntimeError('actual runner pin required')
    for pin in binding['harness'].values():
        read_exact(pin)
    save_new(ATTEMPT, dict(status='STARTED_BEFORE_SUBJECT_IMPORT',
                          binding=exact_pin(BINDING), preparation=binding['preparation'],
                          deeper_checks='NOT_REACHED_UNLESS_ENTRY_SUCCEEDS_AND_SEPARATELY_AUTHORIZED'))
    world = gate = support = None
    setup_error = entry_error = cleanup_error = None
    entry_completed = False
    source_import_completed = False
    try:
        support = trusted_module('entry_independent_test_support_v1', binding['harness']['support'])
        W = trusted_module('entry_independent_world_v1', binding['harness']['world'])
        T = trusted_module('entry_initial_regressions_v1', binding['harness']['regressions'])
        gate = support.CallGate(started + 60)
        sys.addaudithook(gate.audit)
        # The only subject module loaded before entry is the exact new kernel.
        # All helper bodies remain data until the kernel captured loader runs.
        world = W.EntryWorld(gate, inputs)
        source_import_completed = True
        try:
            T.test01_valid_entry(world)
            entry_completed = True
        except BaseException as error:
            entry_error = error
        # On failed construction there is no fabricated Core and no cleanup
        # call. If entry unexpectedly succeeds, retain normal emergency cleanup
        # without invoking either downstream test or captured helper lifecycle.
        if entry_completed:
            try:
                world.cleanup()
            except BaseException as error:
                cleanup_error = error
    except BaseException as error:
        setup_error = error
    audit = [] if gate is None else list(gate.audit_denials)
    changed = []
    for name, pin in {**binding['source_map'], **binding['harness']}.items():
        if exact_pin(pin['path']) != pin:
            changed.append(name)
    late = time.monotonic() >= started + 60
    exact_expected = (world is not None and entry_error is not None and
                      type(entry_error) is world.K.KernelRefusal and
                      entry_error.code == binding['expected_entry_error_code'])
    observation = None
    if world is not None:
        observation = world.observation()
        observation['original_first_error'] = error_data(observation['original_first_error'])
    result = dict(
        schema_version=1, scope='SOURCE1_SINGLE_ENTRY_SMOKE_NO_DOWNSTREAM_EXECUTION',
        status=('EXPECTED_ENTRY_SETUP_FAILURE_RETAINED' if exact_expected and
                setup_error is None and not audit and not changed and not late else
                'ENTRY_SUCCEEDED_DOWNSTREAM_NOT_EXECUTED' if entry_completed and
                setup_error is None and not audit and not changed and not late else 'INCOMPLETE_OR_UNEXPECTED'),
        source_pause=binding['source_pause'], source_map=binding['source_map'],
        preparation=binding['preparation'], inputs=binding['inputs'], binding=exact_pin(BINDING),
        source_import_completed=source_import_completed, actual_entry_attempts=(
            int(world.attempt.attempted) if world is not None else None),
        original_first_clock_observed=(world.attempt.start_cell is not world.K.UNOBSERVED
                                       if world is not None else None),
        entry_return_observed=entry_completed, entry_error=error_data(entry_error),
        setup_error=error_data(setup_error), cleanup_error=error_data(cleanup_error),
        intended_checks={
            'test01_valid_entry': 'PASS' if entry_completed else 'FAIL' if entry_error is not None else 'NOT_REACHED',
            'test02_normal_captured_helpers_finish': 'NOT_REACHED',
            'test03_staged_scalar_has_no_cleanup_authority': 'NOT_REACHED'},
        downstream_source_defects_reproduced=False, observations=observation,
        clock_events=[] if world is None else world.events,
        call_gate=None if gate is None else dict(attempts=gate.attempts, normal_returns=gate.returns,
                                                deadline_checks=gate.checks),
        audit_denials=audit, changed_pins=changed, cooperative_deadline_late=late,
        elapsed_seconds=time.monotonic()-started,
        qualification=dict(source_only=True, pure_synthetic=True, native=False,
                           physical_io=False, real_first_entry=False, whole_r09=False))
    save_new(PROOF, result)
    print(json.dumps(dict(status=result['status'], proof=exact_pin(PROOF))))
    return 0 if result['status'] == 'EXPECTED_ENTRY_SETUP_FAILURE_RETAINED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
