"""One Root-bound native25 SOURCE/DATA diagnostic; authoring is not execution."""
import builtins
import codecs
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types

BASE = Path(__file__).resolve().parent
ATTEMPT = BASE / 'NATIVE25-COMPONENT-ATTEMPT-v1.json'
PROOF = BASE / 'NATIVE25-COMPONENT-PROOF-v1.json'
ARTIFACTS = BASE / 'NATIVE25-COMPONENT-ARTIFACTS-v1'
FREEZE = BASE / 'NATIVE25-COMPONENT-FREEZE-v1.json'
BINDING = BASE / 'NATIVE25-COMPONENT-BINDING-v1.json'


def require(ok, text):
    if not ok:
        raise AssertionError(text)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(pin):
    raw = Path(pin['path']).read_bytes()
    require(len(raw) == pin['bytes'] and digest(raw) == pin['sha256'], 'exact frozen file')
    return raw


def describe(error):
    if error is None:
        return None
    try:
        message = str(error)[:256]
    except BaseException:
        message = '<format unavailable>'
    return dict(class_name=type(error).__name__, code=getattr(error, 'code', None),
                message=message, harness_identity=id(error))


def clean(value, kernel=None, depth=0):
    if kernel is not None and value is kernel.UNOBSERVED:
        return dict(tag='UNOBSERVED')
    if value is None or type(value) is str or type(value) is bool or type(value) is int:
        return value
    if type(value) is float:
        return value if math.isfinite(value) else dict(tag='NONFINITE_FLOAT', repr=str(value))
    if type(value) is bytes:
        return dict(bytes=len(value), sha256=digest(value))
    if isinstance(value, BaseException):
        return describe(value)
    if depth > 24:
        return dict(tag='DEPTH_NOT_SERIALIZED')
    if type(value) is dict or type(value) is types.MappingProxyType:
        return {str(k): clean(v, kernel, depth+1) for k, v in value.items()}
    if type(value) is tuple or type(value) is list:
        return [clean(v, kernel, depth+1) for v in value]
    return dict(tag='OPAQUE_SOURCE_OBJECT', class_name=type(value).__name__, harness_identity=id(value))


def write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def load_harness(pin, name):
    raw = read_pin(pin)
    module = types.ModuleType(name)
    module.__file__ = pin['path']
    sys.modules[name] = module
    exec(compile(raw, pin['path'], 'exec'), module.__dict__)
    return module


class Context:
    def __init__(self, gate, support, world_module, inputs):
        self.gate = gate
        self.S = support
        self.W = world_module
        self.inputs = inputs
        self.loader = support.ExactLoader(gate, inputs['world_inputs']['source_map'])
        self.K = self.loader.kernel_module()
        self.worlds = []
        self.data_objects = []
        self.bulk = None
        self.snapshots = []
        self.world_ids = {}
        self.data_ids = {}
        self.cleanup_done = set()
        self.artifacts = []
        self.current_worlds = []
        self.current_data = []
        self.errors = []
        self.notes = []
        self.unexpected_returns = []

    def start(self):
        self.current_worlds = []
        self.current_data = []
        self.errors = []
        self.notes = []
        self.unexpected_returns = []

    def call(self, function, *args, **kwargs):
        return self.gate.invoke(function, *args, **kwargs)

    def touch(self, world):
        if not any(world is old for old in self.current_worlds):
            self.current_worlds.append(world)

    def world(self, zero_clock=False, empty=False):
        values = self.inputs['empty_world_inputs'] if empty else self.inputs['world_inputs']
        clock = self.S.ControlledClock(0) if zero_clock else None
        world = self.W.EntryWorld(self.gate, values, kernel=self.K, clock=clock)
        self.worlds.append(world)
        self.world_ids[id(world)] = len(self.worlds)
        self.touch(world)
        world.enter()
        return world

    def data(self, capacity=4):
        value = self.call(self.K.SyntheticExercise, capacity)
        self.data_objects.append(value)
        self.data_ids[id(value)] = len(self.data_objects)
        self.current_data.append(value)
        return value

    def snapshot(self, world):
        # Retain the original returned snapshot before the outer call-gate's
        # cooperative post-return veto; no data is substituted for its brand.
        def observe():
            snapshot = world.state.snapshot()
            self.snapshots.append((world, snapshot))
            return snapshot
        return self.call(observe)

    def bulk_world(self):
        if self.bulk is None:
            world = self.world()
            world.native25_defer_cleanup = True
            ref = self.call(world.state.port.acquire, world.specs[-1])
            self.call(world.state.port.inspect, ref)
            self.call(world.state.port.hash_capture, ref)
            require(world.held_states[-1].identity_state == 'verified' and self.K.usable(world.state.handle(world.held_states[-1])), 'live source identity/handle before unavailable-route guard')
            self.bulk = world, ref
        self.touch(self.bulk[0])
        return self.bulk

    def cleanup_world(self, world):
        if id(world) in self.cleanup_done:
            return None
        self.cleanup_done.add(id(world))
        if getattr(world, 'native25_hard_stop', False):
            return None  # explicit retained fake right, no post-deadline retry
        try:
            world.cleanup()
        except BaseException as error:
            return describe(error)
        return None

    def branch_cleanup(self, branch_id):
        problems = []
        if branch_id == 'N24.1' and self.bulk is not None:
            self.bulk[0].native25_defer_cleanup = False
        for world in self.current_worlds:
            if getattr(world, 'native25_defer_cleanup', False):
                continue
            error = self.cleanup_world(world)
            if error is not None:
                problems.append(error)
        return problems

    def persist_bank(self, label, owner, calls):
        raw_name = ARTIFACTS / (label+'.raw256.bin')
        meta_name = ARTIFACTS / (label+'.rows.jsonl')
        raw_hash = hashlib.sha256()
        meta_hash = hashlib.sha256()
        raw_n = meta_n = 0
        missing = []
        with raw_name.open('xb') as raw_file, meta_name.open('xb') as meta_file:
            for call in calls:
                ordinal = call.ordinal
                registered = ordinal < len(owner.raw_store._refs) and owner.raw_store._refs[ordinal] is call.ref
                if registered:
                    # A deliberately malformed bank may refuse its own public
                    # decoder. Retain existing bytes, not a fabricated row.
                    raw = bytes(memoryview(owner.raw_store._bank)[256*ordinal:256*(ordinal+1)])
                    raw_file.write(raw);raw_hash.update(raw);raw_n += len(raw)
                else:
                    missing.append(ordinal)
                query = None
                if type(call.query_bytes) is bytes:
                    query_path = ARTIFACTS / (label+'.query-%05d.bin'%ordinal)
                    with query_path.open('xb') as stream:stream.write(call.query_bytes)
                    query = dict(path=str(query_path), bytes=len(call.query_bytes), sha256=digest(call.query_bytes), semantics='EXISTING_IMMUTABLE_SOURCE_QUERY_CAPTURE_NOT_AN_INITIALIZED_BUFFER')
                    self.artifacts.append(query)
                item = dict(ordinal=ordinal, api=call.api, registered=registered,
                            invoked=call.invoked, stopped=call.stopped,
                            wrapper_return=call.wrapper_return, wrapper_state=call.wrapper_state,
                            scalar=clean(call.scalar, self.K), count=clean(call.count, self.K),
                            error=clean(call.error, self.K), error_definition=clean(call.error_definition, self.K),
                            pre_clock=clean(call.pre_clock, self.K), post_clock=clean(call.post_clock, self.K),
                            read_fold=call._read_fold_phase, hash_fold=call._hash_fold_phase,
                            copy_fold=call._copy_fold_phase, query_capture=query,
                            buffer_written=call.buffer_written, buffer_generation=call.generation)
                raw = (json.dumps(item, ensure_ascii=True, sort_keys=True, allow_nan=False)+'\n').encode('utf-8')
                meta_file.write(raw);meta_hash.update(raw);meta_n += len(raw)
        result = [dict(path=str(raw_name), bytes=raw_n, sha256=raw_hash.hexdigest(), semantics='EXISTING_SOURCE_MODEL_BANK_BYTES_NOT_NATIVE_C_EVIDENCE'),
                  dict(path=str(meta_name), bytes=meta_n, sha256=meta_hash.hexdigest(), semantics='SOURCE_CACHE_WRAPPER_FACTS_SEPARATE_FROM_CANONICAL_RAW')]
        self.artifacts.extend(result)
        return dict(raw_rows=raw_n//256, missing_registered_ordinals=missing, files=result)

    def persist(self):
        result = dict(worlds=[], data=[], snapshots=[], artifacts=self.artifacts)
        for world in self.worlds:
            number = self.world_ids[id(world)]
            state = world.state if world.state is not None else world.attempt.state
            row = dict(id=number, core_present=state is not None,
                       entry_attempted=world.attempt.attempted, start=clean(world.attempt.start_cell, self.K),
                       first_entry_error=describe(world.attempt.error),
                       original_calls=clean(world.originals.calls, self.K),
                       fixture_completed_delivery=world.originals.delivered,
                       fixture_close_counter=world.originals.close_attempts,
                       output_callbacks=clean(world.output.callbacks, self.K),
                       compiler_callbacks=clean(world.loader.compiler_observations, self.K),
                       cleanup_skipped=bool(world.skip_cleanup),
                       cleanup_blocked_hard_deadline=bool(getattr(world, 'native25_hard_stop', False)))
            if state is not None:
                row.update(primary=describe(state.primary), secondary=[describe(x) for x in state.secondary],
                           origin=dict(start=clean(state.origin.start, self.K), now=clean(state.origin.now, self.K), latest=clean(state.origin.raw_latest, self.K)),
                           final_snapshot_issued=state._final is not None,
                           bank=self.persist_bank('world-%03d'%number, state, state.registry._calls))
                if state._final is not None and not any(s is state._final for _, s in self.snapshots):
                    self.snapshots.append((world, state._final))
            result['worlds'].append(row)
        for value in self.data_objects:
            number = self.data_ids[id(value)]
            result['data'].append(dict(id=number, scope=value.scope,
                                       bank=self.persist_bank('data-%03d'%number, value, value._calls)))
        seen = set()
        for world, snapshot in self.snapshots:
            if id(snapshot) in seen:
                continue
            seen.add(id(snapshot))
            number = len(result['snapshots'])+1
            raw_path = ARTIFACTS / ('snapshot-%03d.raw256.bin'%number)
            raw_hash = hashlib.sha256();size = 0
            with raw_path.open('xb') as stream:
                for row in snapshot._raw_calls:
                    raw = row.raw_row;stream.write(raw);raw_hash.update(raw);size += len(raw)
            rp = dict(path=str(raw_path), bytes=size, sha256=raw_hash.hexdigest(), semantics='ALREADY_COPIED_IMMUTABLE_GENUINE_KERNEL_SNAPSHOT')
            meta = dict(world=self.world_ids[id(world)], partial=snapshot.partial_capture,
                        copied_bytes=snapshot.copied_native_bytes, raw_rows=snapshot.raw_call_count,
                        capture_error=describe(snapshot.capture_error), data=clean(snapshot.to_dict(), self.K))
            mp = write_json(ARTIFACTS / ('snapshot-%03d.json'%number), meta)
            self.artifacts.extend((rp, mp));result['snapshots'].append(dict(raw=rp, metadata=mp))
        # Source-generated objects are retained by original reference, with no
        # re-freeze/rehash/consumer work in the producer after its unwinding.
        for world in self.worlds:
            state = world.state if world.state is not None else world.attempt.state
            if state is None:
                continue
            for kind, record in state._generated.items():
                raw = record.get('raw')
                if type(raw) is bytes:
                    path = ARTIFACTS / ('world-%03d.generated.%s'%(self.world_ids[id(world)], kind))
                    with path.open('xb') as stream:stream.write(raw)
                    self.artifacts.append(dict(path=str(path), bytes=len(raw), sha256=digest(raw),
                                               semantics='HARNESS_COPY_OF_ACTUAL_SOURCE_GENERATED_OBJECT', eligible=record.get('eligible')))
        return result


def main():
    started = time.monotonic()
    require(not ATTEMPT.exists() and not PROOF.exists() and not ARTIFACTS.exists(), 'exclusive one-shot output paths')
    binding = json.loads(BINDING.read_bytes())
    require(binding['status'] == 'ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT' and binding['run_authorized'] is True, 'separate Root execution binding')
    seconds = binding['deadline_seconds']
    require(type(seconds) is int and 0 < seconds <= 60, 'bounded original suite timer')
    scope = json.loads(read_pin(binding['execution_scope']))
    require(scope['status'] == 'ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION', 'separate execution scope')
    freeze = json.loads(read_pin(binding['freeze']))
    require(Path(binding['freeze']['path']).resolve() == FREEZE.resolve(), 'exact freeze path')
    for p in freeze['pins'].values():read_pin(p)
    require(read_pin(freeze['pins']['runner']) == Path(__file__).read_bytes(), 'actual runner bytes')
    attempt = write_json(ATTEMPT, dict(status='ATTEMPT_CONSUMED_BEFORE_FIRST_SUBJECT_IMPORT', binding=binding, deadline_seconds=seconds))
    rows = [];ctx = gate = None;setup_error = None;evidence_error = None;late = False
    try:
        ARTIFACTS.mkdir()
        codecs.lookup('utf-16-le')  # named trusted pre-entry codec prerequisite
        support = load_harness(freeze['pins']['support'], 'entry_independent_test_support_v4')
        world = load_harness(freeze['pins']['world'], 'entry_independent_world_v4')
        cases = load_harness(freeze['pins']['cases'], 'native25_component_cases_v1')
        inputs = json.loads(read_pin(freeze['pins']['inputs']))
        matrix = json.loads(read_pin(freeze['pins']['matrix']))
        gate = support.CallGate(started+seconds)
        sys.addaudithook(gate.audit)
        ctx = Context(gate, support, world, inputs)
        branches = [branch for case in matrix['cases'] for branch in case['branches']]
        require(set(cases.CASES) == {x['id'] for x in branches if x['classification'] in ('DATA','SOURCE_RUNTIME')}, 'exact frozen executable branch set')
        deadline = False
        for branch in branches:
            row = dict(id=branch['id'], classification=branch['classification'], outcome=None,
                       first_error=None, cleanup_errors=[], expected_errors=[], notes=[], worlds=[], data=[])
            rows.append(row)
            if branch['classification'] not in ('DATA','SOURCE_RUNTIME'):
                row['outcome'] = 'DEFERRED_NOT_EXECUTED' if branch['classification'] == 'DEFERRED' else 'STATIC_DECLARATION_ONLY'
                continue
            if deadline:
                row['outcome'] = 'UNKNOWN_DEADLINE';continue
            ctx.start()
            try:
                gate.check();cases.CASES[branch['id']](ctx);gate.check()
                row['outcome'] = 'COMPONENT_PASS'
            except TimeoutError as error:
                row['first_error'] = describe(error);row['outcome'] = 'UNKNOWN_DEADLINE';deadline = True
            except BaseException as error:
                row['first_error'] = describe(error);row['outcome'] = 'FAIL'
            finally:
                row['cleanup_errors'] = ctx.branch_cleanup(branch['id'])
                row['expected_errors'] = [describe(e) for e in ctx.errors]
                row['notes'] = list(ctx.notes)
                row['unexpected_source_returns'] = clean(ctx.unexpected_returns, ctx.K)
                row['worlds'] = [ctx.world_ids[id(w)] for w in ctx.current_worlds]
                row['data'] = [ctx.data_ids[id(x)] for x in ctx.current_data]
                if row['cleanup_errors'] and row['outcome'] == 'COMPONENT_PASS':row['outcome'] = 'FAIL'
        for world in ctx.worlds:
            if getattr(world, 'native25_defer_cleanup', False):
                world.native25_defer_cleanup = False
                error = ctx.cleanup_world(world)
                if error is not None:rows.append(dict(id='FINAL_CLEANUP', outcome='FAIL', first_error=error))
    except BaseException as error:
        setup_error = describe(error)
    evidence = None
    if ctx is not None:
        try:evidence = ctx.persist()
        except BaseException as error:evidence_error = describe(error)
    counts = {}
    for row in rows:counts[row['outcome']] = counts.get(row['outcome'], 0)+1
    changed = []
    for key, p in freeze['pins'].items():
        try:read_pin(p)
        except BaseException as error:changed.append(dict(key=key, error=describe(error)))
    elapsed = time.monotonic()-started
    late = elapsed >= seconds
    status = 'COMPONENT_FAILURES_WITH_EXPLICIT_DEFERRED' if setup_error or evidence_error or changed or late or counts.get('FAIL') or counts.get('UNKNOWN_DEADLINE') else 'COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED'
    proof = dict(schema_version=1, status=status,
                 attempt=attempt, binding=binding, freeze=binding['freeze'], counts=counts, rows=rows,
                 setup_error=setup_error, evidence_error=evidence_error, evidence=evidence,
                 elapsed_seconds=elapsed, cooperative_deadline_late=late, changed_pins=changed,
                 call_gate=None if gate is None else dict(attempts=gate.attempts, returns=gate.returns, checks=gate.checks),
                 audit_denials=[] if gate is None else gate.audit_denials,
                 native25_complete=False, qualification=dict(source_component_only=True, native_C=False, native_input_lease=False, physical_IO=False, model=False, RSS=False),
                 timing_scope='Per-world evidence copies included; final proof serialization/write/hash/print and process startup/exit outside or unmeasured.')
    pp = write_json(PROOF, proof)
    print(json.dumps(dict(proof=pp, counts=counts, setup_error=setup_error, evidence_error=evidence_error, late=late)))
    return 0 if not setup_error and not evidence_error and not changed and not late and not counts.get('FAIL') and not counts.get('UNKNOWN_DEADLINE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
