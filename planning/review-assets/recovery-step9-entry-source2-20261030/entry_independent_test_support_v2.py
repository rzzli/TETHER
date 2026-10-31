"""Trusted independent harness support; no subject is imported on module load.

The eventual runner supplies one externally started deadline and exact source
pins. Compile/exec below is callable test machinery, not executed preparation.
"""
import builtins
import dataclasses
import encodings.utf_16_le
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
import types


class HarnessError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise HarnessError(message)


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return set(a) == set(b) and all(strict_equal(a[k], b[k]) for k in a)
    if type(a) in (list, tuple):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    if type(a) is float:
        return struct.pack('<d', a) == struct.pack('<d', b)
    return a == b


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_pin(value):
    raw = Path(value['path']).read_bytes()
    require(type(value['bytes']) is int and len(raw) == value['bytes'], 'exact new source length')
    require(hashlib.sha256(raw).hexdigest() == value['sha256'], 'exact new source hash')
    return raw


class ControlledClock:
    """Returns exactly scripted values/errors, including deliberately bad ones."""
    def __init__(self, value=100, events=None):
        self.value = value
        self.calls = 0
        self.script = []
        self.events = [] if events is None else events

    def __call__(self):
        self.calls += 1
        self.events.append(('clock', self.calls))
        value = self.script.pop(0) if self.script else self.value
        if isinstance(value, BaseException):
            raise value
        self.value = value
        return value

    def set(self, value):
        # A fixture may intentionally set a backward/nonfinite value. Only the
        # actual kernel determines validity; the fixture cannot repair it.
        self.value = value


class CallGate:
    """One real cooperative suite deadline, separate from synthetic owner time."""
    def __init__(self, deadline):
        self.deadline = deadline
        self.active = False
        self.attempts = 0
        self.returns = 0
        self.checks = 0
        self.source_filenames = set()
        self.audit_denials = []

    def check(self):
        self.checks += 1
        if time.monotonic() >= self.deadline:
            raise TimeoutError('original independent entry suite deadline')

    def invoke(self, function, *args, **kwargs):
        self.check()
        old = self.active
        self.active = True
        self.attempts += 1
        try:
            result = function(*args, **kwargs)
        finally:
            # No finally deadline check may replace the original exception.
            self.active = old
        self.returns += 1
        self.check()
        return result

    def audit(self, event, args):
        dangerous = event == 'open' or event == 'import' or event.startswith(('ctypes.', 'subprocess.', 'socket.', 'os.'))
        if not dangerous:
            return
        active = self.active
        frame = sys._getframe()
        for _ in range(512):
            if frame is None:
                break
            if frame.f_code.co_filename in self.source_filenames:
                active = True
                break
            frame = frame.f_back
        if active:
            self.audit_denials.append(event)
            raise HarnessError('unexpected source I/O or import')


class ExactLoader:
    """Actual new kernel first; helpers only through its captured compiler path."""
    STDLIB = {'dataclasses': dataclasses, 'hashlib': hashlib, 'json': json,
              'math': math, 're': re, 'struct': struct, 'types': types}

    def __init__(self, gate, source_pins, fixture_modules=None):
        self.gate = gate
        self.pins = dict(source_pins)
        # Trusted preparation reads exact NEW test inputs before subject work.
        # No source-owned resolver may access this filesystem map.
        self.raw = {name: read_pin(p) for name, p in self.pins.items()}
        for name, raw in (() if fixture_modules is None else fixture_modules.items()):
            require(name not in self.raw and type(name) is str and type(raw) is bytes,
                    'separately pinned literal module cannot replace actual helper')
            self.raw[name] = raw
        self.kernel = None
        self.compiler_observations = []
        self.captured_namespaces = []
        self.before_compile = None

    def kernel_module(self, namespace='preflight_entry_kernel_v2'):
        self.gate.check()
        source_name = 'preflight_entry_kernel_v2'
        require(source_name in self.raw, 'kernel exact source pin')
        module = types.ModuleType(namespace)
        module.__file__ = self.pins[source_name]['path']
        module.__package__ = ''
        self.gate.source_filenames.add(module.__file__)

        def imported(name, globals=None, locals=None, fromlist=(), level=0):
            require(level == 0 and name in self.STDLIB, 'kernel may import only explicit pre-entry stdlib prerequisites')
            return self.STDLIB[name]

        module.__dict__['__builtins__'] = dict(vars(builtins), __import__=imported)
        # Registration supports stdlib dataclass lookup only. Source import
        # resolution never looks up or trusts this name later.
        sys.modules[namespace] = module
        self.gate.invoke(exec, compile(self.raw[source_name], module.__file__, 'exec'), module.__dict__)
        self.kernel = module
        return module

    def compiler(self, fullname, raw, module_globals):
        self.gate.check()
        require(self.kernel is not None and fullname in self.raw and fullname != 'preflight_entry_kernel_v2', 'captured helper in exact source graph')
        require(type(raw) is bytes and raw == self.raw[fullname], 'actual authored helper bytes, not marker substitute')
        require(type(module_globals) is dict and module_globals.get('__name__') == fullname,
                'kernel supplies the actual captured module namespace')
        require('__builtins__' in module_globals, 'kernel supplies its closed resolver')
        observation = dict(module=fullname, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), entered=True, return_prepared=False)
        self.compiler_observations.append(observation)
        if self.before_compile is not None:
            self.before_compile(fullname, raw)
        filename = module_globals.get('__file__', '<captured ' + fullname + '>')
        require(type(filename) is str, 'actual captured compile filename')
        self.gate.source_filenames.add(filename)
        # Do not replace the namespace, importer or brands supplied by the
        # under-test kernel. Its resolver/loader is part of what is graded.
        self.gate.invoke(exec, compile(raw, filename, 'exec'), module_globals)
        self.captured_namespaces.append(module_globals)
        self.gate.check()
        observation['return_prepared'] = True
        return None


class OutputSpy:
    """Synthetic actual callbacks only; source records caller receipt separately."""
    def __init__(self, clock, events=None):
        self.clock = clock
        self.events = [] if events is None else events
        self.callbacks = []
        self.journal = []
        self.packets = {}
        self.hook = None
        self.namespace_scalar = 1

    def _before(self, target, *values):
        self.events.append(('output', target))
        row = dict(target=target, return_prepared=False)
        self.callbacks.append(row)
        if self.hook is not None:
            self.hook(target, *values)
        return row

    def reserve(self, key, carrier, ack, hard_end):
        row = self._before('reserve', key, carrier)
        carrier.store_namespace_return(self.namespace_scalar)
        # An injected post-namespace failure is a real raised callback, not an
        # invented returned False or a source-consumed ready argument.
        if self.hook is not None:
            self.hook('namespace_stored', key, carrier)
        row['return_prepared'] = True
        return ack

    def append(self, raw, ack, hard_end):
        row = self._before('append', raw)
        require(type(raw) is bytes, 'actual journal immutable bytes')
        self.journal.append(raw)
        row['return_prepared'] = True
        return ack

    def publish(self, kind, raw, ack, hard_end):
        row = self._before('publish_' + kind, raw)
        require(type(raw) is bytes and len(raw) <= 8192, 'actual bounded publication bytes')
        require(kind not in self.packets, 'once-only publication')
        self.packets[kind] = raw
        row['return_prepared'] = True
        return ack

    def close_journal(self, ack, hard_end):
        row = self._before('close_journal')
        row['return_prepared'] = True
        return ack


class VirtualOriginals:
    """Actual injected returns over authored helper bytes and a periodic bulk.

    No local path is opened here. Fixture bodies were frozen by trusted setup.
    The actual source carrier owns buffer writes and canonical raw stores.
    """
    APIS = ('CreateFileW', 'GetFileType', 'GetFileInformationByHandleEx',
            'GetFinalPathNameByHandleW', 'GetFileSizeEx', 'ReadFile', 'CloseHandle')
    SEED = bytes(range(256))

    def __init__(self, gate, clock, fixtures, events=None):
        self.gate = gate
        self.clock = clock
        self.fixtures = tuple(fixtures)
        self.by_path = {x['path']: x for x in self.fixtures}
        require(len(self.by_path) == len(self.fixtures), 'unique fictional original paths')
        self.events = [] if events is None else events
        self.calls = []
        self.refs = []
        self.delivered = {x['path']: 0 for x in self.fixtures}
        self.open_attempts = {x['path']: 0 for x in self.fixtures}
        self.close_attempts = {x['path']: 0 for x in self.fixtures}
        self.handles = {x['path']: 1000+i for i, x in enumerate(self.fixtures)}
        self.hook = None

    def _point(self, point, ref, args, carrier, observation):
        self.gate.check()
        if self.hook is not None:
            self.hook(point, ref, args, carrier, observation)

    def invoke_reserved(self, ticket, args):
        self.gate.check()
        ref = ticket.call_ref
        carrier = ticket.carrier
        api = ref.api
        path = ref.file_ref.spec.path
        require(api in self.APIS and path in self.by_path, 'original7 admitted fixture only')
        d = self.by_path[path]
        i = self.fixtures.index(d)
        handle = self.handles[path]
        self.events.append(('original', api, path))
        observation = dict(api=api, path=path, ordinal=ref.ordinal,
                           scalar_hook_completed=False, count_hook_completed=False,
                           normal_return_prepared=False)
        self.calls.append(observation)
        self.refs.append(ref)
        expected = {
            'CreateFileW': dict(path=path, desired_access=2147483648, share_mode=1,
                               security=None, creation=3, flags=2097280, template=None),
            'GetFileType': dict(handle=handle),
            'GetFileInformationByHandleEx': dict(handle=handle, info_class=9, buffer_bytes=8),
            'GetFinalPathNameByHandleW': dict(handle=handle, capacity=4101, flags=0),
            'GetFileSizeEx': dict(handle=handle),
            'ReadFile': dict(handle=handle, requested=min(d['chunk'], d['size']-self.delivered[path]), overlapped=None),
            'CloseHandle': dict(handle=handle),
        }[api]
        require(strict_equal(args, expected), 'independent actual argument dictionary')
        self._point('entered', ref, args, carrier, observation)
        if observation.get('handled_by_injected_original') is True:
            # Only the trusted fixture callback can select its own supplied
            # return. No such selector reaches a source guard or factory.
            self._point('before_return', ref, args, carrier, observation)
            observation['normal_return_prepared'] = True
            return None
        scalar = 1
        if api == 'CreateFileW':
            self.open_attempts[path] += 1
            require(self.open_attempts[path] == 1, 'no original reopen')
            scalar = handle
        elif api == 'CloseHandle':
            self.close_attempts[path] += 1
            require(self.open_attempts[path] == 1 and self.close_attempts[path] == 1, 'known original once-close attempt')
        elif api == 'GetFileInformationByHandleEx':
            carrier.buffer_write_slice(ref, ref.buffer_ref, ref.buffer_generation, 0, struct.pack('<II', 128, 0))
        elif api == 'GetFinalPathNameByHandleW':
            path_raw = ('\\\\?\\' + path).encode('utf-16-le')
            frame = path_raw + bytes(8202-len(path_raw))
            carrier.buffer_write_slice(ref, ref.buffer_ref, ref.buffer_generation, 0, frame)
            scalar = len(path_raw)//2
        elif api == 'GetFileSizeEx':
            carrier.buffer_write_slice(ref, ref.buffer_ref, ref.buffer_generation, 0, struct.pack('<q', d['size']))
        elif api == 'ReadFile':
            count = expected['requested']
            require(count > 0 and count == ref.requested, 'exact independent remaining request')
            if d['body'] is not None:
                offset = self.delivered[path]
                carrier.buffer_write_slice(ref, ref.buffer_ref, ref.buffer_generation, 0, d['body'][offset:offset+count])
            else:
                require(self.delivered[path] % 256 == 0, 'periodic prefix chunk phase')
                first = min(256, count)
                carrier.buffer_write_slice(ref, ref.buffer_ref, ref.buffer_generation, 0, self.SEED[:first])
                written = first
                while written < count:
                    self.gate.check()
                    n = min(written, count-written)
                    carrier.buffer_copy_within(ref, ref.buffer_ref, ref.buffer_generation, 0, n)
                    written += n
        self._point('before_scalar', ref, args, carrier, observation)
        carrier.store_scalar(ref, scalar)
        observation['scalar_hook_completed'] = True
        self._point('after_scalar', ref, args, carrier, observation)
        if api == 'ReadFile':
            carrier.store_count(ref, expected['requested'])
            observation['count_hook_completed'] = True
            self.delivered[path] += expected['requested']
            self._point('after_count', ref, args, carrier, observation)
        self._point('before_return', ref, args, carrier, observation)
        observation['normal_return_prepared'] = True
        return None


def independent_geometry(fixtures, early_paths, module_count):
    """Frozen input arithmetic only; never an under-test output oracle."""
    n = len(fixtures)
    q = sum(x['size']//x['chunk'] + int(x['size'] % x['chunk'] != 0) for x in fixtures)
    positive = sum(x['size'] > 0 for x in fixtures)
    early = [x for x in fixtures if x['path'] in early_paths]
    bootstrap_reads = sum(x['size']//x['chunk'] + int(x['size'] % x['chunk'] != 0) for x in early)
    return dict(N=n, B=len(early_paths), M=module_count, Q=q, R=q+16*positive,
                C=6*n+q+16*positive, E=6*n+2*len(early_paths)+2*module_count+192,
                bootstrap_calls=5*len(early)+bootstrap_reads,
                work_calls=5*n+q, terminal_calls=6*n+q,
                known_bytes=sum(x['size'] for x in fixtures),
                captured_bytes=sum(x['size'] for x in fixtures if x['capture']),
                early_bytes=sum(x['size'] for x in early),
                original_closes=n)
