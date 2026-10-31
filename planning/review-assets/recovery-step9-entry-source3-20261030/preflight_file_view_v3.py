"""Captured, non-owning original-file operations over the entry's exact core.

The kernel requires these bounded original7 primitives for bootstrap before
this module can be authenticated. Reusing them preserves its existing cells,
buffers, leases and debits. Calling the stable PortFacade here would recurse.
This source provides no native backend, physical output or model authority.
"""
import preflight_entry_kernel_v3 as K

_MINT = object()
_ROLES = frozenset(('captured_software', 'captured_metadata', 'hash_only_bulk'))


class FileView:
    __slots__ = ('_view', '_state', '_attach_ref')

    def __init__(self, mint, state_view):
        if mint is not _MINT:
            raise K.KernelRefusal('SOURCE_ISSUER_REQUIRED')
        if type(state_view) is not K.StateView:
            raise K.KernelRefusal('FOREIGN_IDENTITY')
        core = state_view._state
        if type(core) is not K.KernelState:
            raise K.KernelRefusal('FOREIGN_IDENTITY')
        if core.kernel_module is not K:
            raise K.KernelRefusal('FOREIGN_IDENTITY')
        core.validate_state_view(state_view)
        object.__setattr__(self, '_view', state_view)
        object.__setattr__(self, '_state', core)
        object.__setattr__(self, '_attach_ref', attach)

    def __setattr__(self, name, value):
        raise TypeError('immutable non-owning FileView')

    @property
    def owner(self):
        return self._state

    @property
    def core(self):
        return self._state

    def _check(self, *, cleanup=False):
        core = self._state
        if core.kernel_module is not K:
            raise K.KernelRefusal('FOREIGN_IDENTITY')
        core.validate_state_view(self._view)
        core.check(cleanup=cleanup)
        return core

    @staticmethod
    def _spec(spec):
        if type(spec) is not K.FileSpec:
            raise K.KernelRefusal('INVALID_INPUT')
        if type(spec.role) is not str or spec.role not in _ROLES:
            raise K.KernelRefusal('INVALID_INPUT')
        if type(spec.capture) is not bool or spec.capture != (spec.role != 'hash_only_bulk'):
            raise K.KernelRefusal('INVALID_INPUT')
        return spec

    def _ref(self, file_ref):
        if type(file_ref) is not K.FileRef or file_ref.owner is not self._state:
            raise K.KernelRefusal('FOREIGN_IDENTITY')
        # The kernel primitive additionally checks its exact registry entry,
        # phase, original target kind, handle right and generation. Data with
        # equal path/ordinal values never substitutes for that canonical ref.
        return file_ref

    def acquire(self, spec):
        core = self._check()
        self._spec(spec)
        return core._bootstrap_acquire(spec)

    def inspect(self, file_ref):
        core = self._check()
        return core._bootstrap_inspect(self._ref(file_ref))

    def hash_capture(self, file_ref):
        core = self._check()
        ref = self._ref(file_ref)
        self._spec(ref.spec)
        return core._bootstrap_hash_capture(ref)

    def close(self, file_ref):
        # A failed work prefix does not erase a known close right. The same
        # reliable original hard clock, canonical registry and consumed-right
        # gate still control this cleanup; false/unknown close is not retried.
        core = self._check(cleanup=True)
        return core._bootstrap_close(self._ref(file_ref))

    def __reduce_ex__(self, protocol):
        raise TypeError('FileView is not serialized authority')


def attach(state_view):
    view = FileView(_MINT, state_view)
    view.core.install_file_view(state_view, view)
    return view
