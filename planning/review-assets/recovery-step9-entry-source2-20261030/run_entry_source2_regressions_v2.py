"""Fresh Source2 worlds for four preserved checks and one stopped-close diagnostic.

Execution requires Root's exact fixed binding. No subject is imported at module
load, no Source1 fallback exists, and every first outcome is retained.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE = Path(__file__).resolve().parent
BINDING = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-BINDING-v2.json'
ATTEMPT = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-ATTEMPT-v2.json'
PROOF = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json'
METHODS = ('test01_valid_entry', 'test02_normal_captured_helpers_finish',
           'test03_staged_scalar_has_no_cleanup_authority',
           'test04_committed_scalar_survives_cache_boundary_failure',
           'test05_stopped_close_normal_return_does_not_heal_cache')
AXIS_FIELDS = ('native_state', 'kind', 'width', 'epoch', 'stage_hint', 'commit',
               'raw_payload_bits', 'known_value')


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
        stream.write((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True,
                                 allow_nan=False) + '\n').encode('utf-8'))


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


def retain_world(world, gate):
    """Observe genuine immutable rows; no source call, retry or owner repair."""
    if world is None:
        return None
    observation = world.observation()
    observation['original_first_error'] = error_data(observation['original_first_error'])
    snapshot = world.first_snapshot
    native_rows = []
    if snapshot is not None:
        for ordinal in range(snapshot.raw_call_count):
            row = snapshot.raw_call(ordinal)
            axes = {}
            for name in ('scalar', 'count', 'error_value', 'error_definition'):
                axis = row.axis(name)
                axes[name] = {key: getattr(axis, key) for key in AXIS_FIELDS}
            native_rows.append(dict(ordinal=ordinal, raw_row256_hex=row.raw_row.hex(),
                                    axes=axes, facts=row.facts))
    close_rows = [dict(path=path, attempts=count)
                  for path, count in world.originals.close_attempts.items()]
    result = dict(observations=observation, first_clock_observed=(
                      world.attempt.start_cell is not world.K.UNOBSERVED),
                  actual_entry_attempts=int(world.attempt.attempted),
                  source_identities_same=(world.identities is not None and
                      all(a is b for a, b in zip(world.identities,
                        (world.state, world.state.origin, world.state.nonce,
                         world.state.registry, world.state.raw_store, world.state.port,
                         world.state.sink, world.state.loader, world.state.journal)))),
                  compiler_callbacks=list(world.loader.compiler_observations),
                  close_dispatch_attempts=close_rows, native_rows=native_rows,
                  snapshot_present=snapshot is not None,
                  snapshot_genuine=(snapshot is not None and type(snapshot) is world.K.KernelSnapshot and
                                    snapshot.owner_state is world.state),
                  partial_snapshot=None if snapshot is None else snapshot.partial_capture,
                  captured_native_bytes=None if snapshot is None else snapshot.copied_native_bytes,
                  original_events=list(world.events),
                  stopped_close_probe=getattr(world, 'stopped_close_probe', None))
    gate.check()
    return result


def main():
    started = time.monotonic()
    if ATTEMPT.exists() or PROOF.exists():
        raise RuntimeError('first attempt already retained; no replay')
    binding = json.loads(BINDING.read_bytes().decode('utf-8'))
    if binding['status'] != 'AUTHORIZED_SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC':
        raise RuntimeError('Root exact Source2 regression authorization required')
    if binding['deadline_seconds'] != 60 or tuple(binding['methods']) != METHODS:
        raise RuntimeError('closed five-check diagnostic suite under one original 60-second deadline')
    read_exact(binding['execution_scope'])
    preparation = json.loads(read_exact(binding['preparation']).decode('utf-8'))
    inputs = json.loads(read_exact(binding['inputs']).decode('utf-8'))
    read_exact(binding['source_pause'])
    if binding['source_map'] != inputs['source_map'] or binding['harness'] != preparation['harness']:
        raise RuntimeError('exact Source2 source/harness maps required')
    if exact_pin(__file__) != binding['harness']['runner']:
        raise RuntimeError('actual runner pin required')
    for pin in {**binding['source_map'], **binding['harness']}.values():
        read_exact(pin)
    save_new(ATTEMPT, dict(status='STARTED_BEFORE_SOURCE2_IMPORT',
                          binding=exact_pin(BINDING), methods=list(METHODS),
                          source1_replayed=False))
    setup_error = None
    gate = None
    rows = [dict(method=name, outcome='NOT_REACHED', error=None, cleanup_error=None,
                 evidence_error=None, evidence=None, source_import_completed=None)
            for name in METHODS]
    worlds = []
    try:
        support = trusted_module('entry_independent_test_support_v2', binding['harness']['support'])
        W = trusted_module('entry_independent_world_v2', binding['harness']['world'])
        T = trusted_module('entry_initial_regressions_v3', binding['harness']['regressions'])
        gate = support.CallGate(started + 60)
        sys.addaudithook(gate.audit)
        for row in rows:
            gate.check()
            world = None
            primary = None
            try:
                world = W.EntryWorld(gate, inputs)
                worlds.append(world)
                row['source_import_completed'] = True
                getattr(T, row['method'])(world)
                row['outcome'] = 'PASS'
            except BaseException as error:
                primary = error
                row['error'] = error_data(error)
                row['outcome'] = 'FAIL'
            finally:
                if world is not None:
                    try:
                        world.cleanup()
                    except BaseException as error:
                        row['cleanup_error'] = error_data(error)
                        if primary is None:
                            row['outcome'] = 'FAIL'
                    try:
                        row['evidence'] = retain_world(world, gate)
                    except BaseException as error:
                        row['evidence_error'] = error_data(error)
                        row['outcome'] = 'FAIL'
            # Do not repeat ordinary entry setup if the corrected constructor
            # still fails in the first intended check. No fabricated state.
            if row['method'] == METHODS[0] and row['outcome'] != 'PASS':
                break
        gate.check()
    except BaseException as error:
        setup_error = error_data(error)
    changed = []
    for name, pin in {**binding['source_map'], **binding['harness']}.items():
        if exact_pin(pin['path']) != pin:
            changed.append(name)
    late = time.monotonic() >= started + 60
    audit = [] if gate is None else list(gate.audit_denials)
    passed = sum(row['outcome'] == 'PASS' for row in rows)
    result = dict(schema_version=1, scope='SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC',
                  status='PASS' if passed == len(METHODS) and setup_error is None and not changed and
                         not late and not audit else 'INCOMPLETE_OR_FAILED',
                  source_pause=binding['source_pause'], source_map=binding['source_map'],
                  inputs=binding['inputs'], preparation=binding['preparation'], binding=exact_pin(BINDING),
                  methods=rows, declared_methods=len(METHODS), passed_methods=passed,
                  executed_methods=sum(row['outcome'] != 'NOT_REACHED' for row in rows),
                  actual_worlds_constructed=len(worlds),
                  actual_entry_attempts=sum(int(w.attempt.attempted) for w in worlds),
                  setup_error=setup_error, audit_denials=audit, changed_pins=changed,
                  cooperative_deadline_late=late, elapsed_seconds=time.monotonic()-started,
                  call_gate=None if gate is None else dict(attempts=gate.attempts,
                        normal_returns=gate.returns,deadline_checks=gate.checks),
                  full_32_named_53_branches='NOT_EXECUTED',native25='NOT_EXECUTED',
                  qualification=dict(source_only=True,pure_synthetic=True,native=False,
                      physical_io=False,real_first_entry=False,whole_r09=False))
    save_new(PROOF, result)
    print(json.dumps(dict(status=result['status'], proof=exact_pin(PROOF))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
