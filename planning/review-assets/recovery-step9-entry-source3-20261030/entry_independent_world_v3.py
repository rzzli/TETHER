"""Actual new-entry fixture world, callable only after Root test authorization.

Authored-source pins and complete prefix expectations are supplied by the
independent pre-run input freeze. No old owner, prefix stripping or body-sized
bulk allocation is used. No subject module is imported here.
"""
import hashlib
import types
from entry_independent_test_support_v3 import (ControlledClock, ExactLoader,
    OutputSpy, VirtualOriginals, independent_geometry, require)


class EntryWorld:
    def __init__(self, gate, inputs, kernel=None, *, clock=None, toy=False,
                 bulk_size=None, output_hook=None, raw_hook=None):
        self.gate = gate
        self.inputs = inputs
        fixture_modules = {x['module']: bytes.fromhex(x['hex'])
                           for x in inputs.get('toy_modules', ())} if toy else {}
        self.loader = ExactLoader(gate, inputs['source_map'], fixture_modules)
        if kernel is None:
            kernel = self.loader.kernel_module()
        else:
            self.loader.kernel = kernel  # Direct actual object, not a name lookup.
        self.K = kernel
        self.events = [] if clock is None else clock.events
        self.clock = ControlledClock(events=self.events) if clock is None else clock
        self.output = OutputSpy(self.clock, self.events)
        self.output.hook = output_hook
        self.raw_hook = raw_hook
        self.compile_hook = None
        self.compiler_blob_refs = []
        self.state = None
        self.early = None
        self.ops_module = self.view_module = self.ops = self.view = None
        self.capsule = self.first_snapshot = None
        self.identities = None
        self.cleanup_errors = []
        self.fixtures = []
        self.module_rules = []
        for row in inputs['helpers']:
            raw = self.loader.raw[row['module']]
            require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'frozen actual helper bytes')
            self.fixtures.append(dict(path=row['fictional_path'], role='captured_software',
                                      size=len(raw), sha256=row['sha256'], capture=True,
                                      body=raw, chunk=inputs['chunk'], module=row['module']))
            self.module_rules.append(kernel.ModuleRule(row['module'], row['fictional_path'], tuple(row['declared_dependencies']), False))
        if toy:
            for row in inputs['toy_modules']:
                raw = bytes.fromhex(row['hex'])
                self.fixtures.append(dict(path=row['fictional_path'], role='captured_software',
                                          size=len(raw), sha256=row['sha256'], capture=True,
                                          body=raw, chunk=inputs['chunk'], module=row['module']))
                self.module_rules.append(kernel.ModuleRule(row['module'], row['fictional_path'], tuple(row['declared_dependencies']), False))
        self.early_paths = tuple(x['path'] for x in self.fixtures)
        metadata = inputs['metadata']
        meta_body = bytes.fromhex(metadata['hex'])
        self.metadata_path = metadata['fictional_path']
        self.fixtures.append(dict(path=self.metadata_path, role='captured_metadata',
                                  size=len(meta_body), sha256=metadata['sha256'], capture=True,
                                  body=meta_body, chunk=inputs['chunk']))
        bulk = inputs['bulk']
        size = bulk['bytes'] if bulk_size is None else bulk_size
        digest = bulk['sha256'] if bulk_size is None else inputs['staged_4GB_digest']
        self.bulk_path = bulk['fictional_path']
        self.fixtures.append(dict(path=self.bulk_path, role='hash_only_bulk',
                                  size=size, sha256=digest, capture=False,
                                  body=None, chunk=inputs['chunk']))
        self.geometry = independent_geometry(self.fixtures, self.early_paths, len(self.module_rules))
        if not toy and bulk_size is None:
            require(self.geometry == inputs['baseline_geometry'], 'literal independently frozen complete prefix')
        self.specs = tuple(kernel.FileSpec(x['path'], x['role'], x['size'], x['sha256'], x['capture'], i)
                           for i, x in enumerate(self.fixtures))
        self.originals = VirtualOriginals(gate, self.clock, self.fixtures, self.events)
        self.originals.hook = self._original_hook
        self.loader.before_compile = self._compile_hook
        self.attempt = kernel.EntryAttempt()
        self.services = kernel.PreboundServices(
            self.clock, self.attempt, kernel.SyntheticRawBackend(self.originals.invoke_reserved),
            kernel.SyntheticOutputBackend(self.output.reserve, self.output.append,
                                          self.output.close_journal, self.output.publish),
            hashlib.sha256, self.loader.compiler, kernel,
            dict(scope='ROOT_AUTHORIZED_SYNTHETIC_ENTRY_SOURCE_TEST_ONLY'),
            dict(self.loader.STDLIB))
        names = inputs['module_names']
        self.plan = kernel.EntryPlan(self.specs, self.early_paths, tuple(self.module_rules),
                                     inputs['output_key'], names['owner_ops'], names['file_view'],
                                     names['codec'], kernel.PROFILE_ORIGINAL7_1M)

    def _original_hook(self, point, ref, args, carrier, observation):
        if self.raw_hook is not None:
            self.raw_hook(self, point, ref, args, carrier, observation)

    def _compile_hook(self, fullname, raw):
        require(self.state is not None and self.state.early_context is not None,
                'actual kernel capture precedes helper compiler')
        row = next(x for x in self.fixtures if x.get('module') == fullname)
        blob = self.state.early_context.bytes_for(row['path'])
        require(raw is blob and raw == row['body'], 'same source-issued immutable helper byte object')
        self.compiler_blob_refs.append((fullname, raw))
        if self.compile_hook is not None:
            self.compile_hook(self, fullname, raw)

    def enter(self):
        try:
            self.state = self.gate.invoke(self.K.entry, self.services, self.plan,
                                          executing_module=self.K)
        except BaseException:
            self.state = self.attempt.state
            raise
        require(self.state is self.attempt.state and type(self.state) is self.K.KernelState,
                'actual canonical entry result')
        self.identities = (self.state, self.state.origin, self.state.nonce,
                           self.state.registry, self.state.raw_store, self.state.port,
                           self.state.sink, self.state.loader, self.state.journal)
        require(self.events and self.events[0] == ('clock', 1), 'clock is first application event')
        require(not self.originals.calls, 'entry output prefix before original opens')
        self.file_refs = tuple(self.gate.invoke(self.state.file_ref, x.path) for x in self.specs)
        self.held_states = tuple(self.gate.invoke(self.state.file_state, x) for x in self.file_refs)
        return self.state

    def bootstrap(self):
        if self.state is None:
            self.enter()
        self.early = self.gate.invoke(self.state.bootstrap_capture)
        require(self.early is self.state.early_context and self.early.owner is self.state,
                'actual early captured context')
        require(len(self.originals.calls) == self.geometry['bootstrap_calls'],
                'all actual helper-prefix calls counted independently')
        for row in self.fixtures:
            if row['path'] in self.early_paths:
                require(self.early.bytes_for(row['path']) == row['body'], 'full authored helper body captured')
        return self.early

    def load_helpers(self):
        if self.early is None:
            self.bootstrap()
        names = self.inputs['module_names']
        self.ops_module = self.gate.invoke(self.state.load_captured, names['owner_ops'])
        self.view_module = self.gate.invoke(self.state.load_captured, names['file_view'])
        require(self.ops_module.K is self.K and self.view_module.K is self.K,
                'actual captured helpers import the executing kernel object')
        return self.ops_module, self.view_module

    def attach_helpers(self):
        if self.ops_module is None:
            self.load_helpers()
        self.capsule = self.gate.invoke(self.state.issue_continuation)
        self.ops = self.gate.invoke(self.ops_module.attach, self.capsule)
        self.view = self.gate.invoke(self.view_module.attach, self.ops.view)
        require(self.ops.state is self.view.core is self.state and self.ops.raw_store is self.state.raw_store,
                'actual non-owning helper objects use the same core and bank')
        require(all(a is b for a, b in zip(self.identities,
                    (self.state, self.state.origin, self.state.nonce,
                     self.state.registry, self.state.raw_store, self.state.port,
                     self.state.sink, self.state.loader, self.state.journal))),
                'attach preserves canonical prefix identities')
        return self.ops, self.view

    def finish(self, *, checker_hook=None):
        if self.ops is None:
            self.attach_helpers()
        O = self.ops_module
        ids = tuple((stage, 'synthetic_entry_' + stage)
                    for stage in ('archive', 'journal', 'resources', 'core'))

        def handler(stage):
            def observe(context):
                require(context is self.state.evidence_context and context.owner is self.state,
                        'genuine current context for explicitly synthetic checker')
                if checker_hook is not None:
                    checker_hook(self, stage, context)
                return O.TestObservation(context, stage, 'consistent',
                                         (self.metadata_path,),
                                         'SYNTHETIC_ENTRY_CONTROL_NOT_REAL_CHECKER_AUTHORITY')
            return observe

        factories = O.test_factories(
            self.state, lambda: O.TestAuthority(self.state, self.specs, ids),
            lambda: O.TestCheckerPorts(self.state, ids, tuple(handler(stage) for stage, _ in ids)))
        request = O.Request(self.inputs['output_key'], self.specs)
        self.first_snapshot = self.gate.invoke(O.continue_once, self.ops.view, request, *factories)
        require(type(self.first_snapshot) is self.K.KernelSnapshot and self.first_snapshot.owner_state is self.state,
                'actual new kernel snapshot, not old owner or decoded brand')
        return self.first_snapshot

    def cleanup(self):
        if self.state is None:
            self.state = self.attempt.state
        if self.state is not None and not self.state.finalized:
            try:
                snapshot = self.gate.invoke(self.state.finalize_incomplete)
                if self.first_snapshot is None:
                    self.first_snapshot = snapshot
            except BaseException as error:
                self.cleanup_errors.append(error)
                raise

    def observation(self):
        return dict(original_dispatches=len(self.originals.calls),
                    actual_read_dispatches=sum(x['api'] == 'ReadFile' for x in self.originals.calls),
                    scripted_close_attempts=sum(self.originals.close_attempts.values()),
                    helper_completed_delivery_bytes=sum(self.originals.delivered.values()),
                    helper_compiler_callbacks=len(self.loader.compiler_observations),
                    namespace_callback_attempts=sum(x['target'] == 'reserve' for x in self.output.callbacks),
                    original_clock_calls=self.clock.calls, prepared_output_callbacks=len(self.output.callbacks),
                    original_first_error=self.state.primary if self.state is not None else self.attempt.error)
