"""Pure declared-metadata arithmetic; never executable runtime admission.

No source discovery, I/O, streaming, owner, clock or physical output binding.
Representation coefficients are logical declarations, not measured RSS.
"""
import json
import re
from types import MappingProxyType

MAX = 2**63 - 1
COEF_MAX = 2**31 - 1
TOP = ('schema_version', 'files', 'early_ids', 'modules', 'aggregate', 'limits', 'representation')
LIMITS = ('max_files', 'max_software_file_bytes', 'max_metadata_file_bytes', 'max_bulk_file_bytes', 'max_captured_bytes', 'max_raw_payload_bytes', 'max_calls', 'max_events', 'max_packet_bytes', 'max_output_bytes', 'max_report_bytes', 'max_declared_memory_bytes')
REP = ('call_record_bytes', 'file_index_bytes', 'module_index_bytes', 'hash_state_bytes', 'transient_bytes', 'report_base_bytes', 'report_call_bytes', 'report_file_bytes', 'report_event_bytes', 'report_copies', 'packet_overhead_bytes')
DERIVED = ('chunk_bytes', 'query_frame_bytes_per_file', 'event_row_bytes', 'packet_kind_count', 'current_runtime_packet_cap', 'N', 'total_bytes', 'positive_files', 'B', 'M', 'Q', 'R', 'C', 'E', 'captured_bytes', 'hash_only_bytes', 'query_witness_bytes', 'work_buffer_bytes', 'raw_payload_bytes', 'immutable_capture_bytes', 'logical_call_bytes', 'index_bytes', 'hash_state_bytes', 'journal_bytes', 'canonical_report_bytes', 'closure_array_bound_bytes', 'digest_array_bytes', 'packet_bound_bytes', 'output_reserved_bytes', 'peak_declared_memory_bytes', 'aggregate_R_range', 'aggregate_C_range')
CONSTANTS = dict(chunk_bytes=65536, query_frame_bytes_per_file=8218, event_row_bytes=1024, packet_kind_count=5, current_runtime_packet_cap=8192)
ROLES = ('captured_software', 'captured_metadata', 'hash_only_bulk')
QUALIFICATION = dict(FFI_registration_proven=False, production_owner_bound=False, originals_authenticated=False, real_checkers_bound=False, verification_complete=False, profile_qualified=False, runtime_authorized=False)
_MINT = object()


class _Bad(Exception):
    def __init__(self, code):
        self.code = code


def _need(condition, code):
    if not condition:
        raise _Bad(code)


def _object(value, keys):
    _need(type(value) is dict, 'TYPE_DOMAIN')
    _need(len(value) == len(keys), 'SCHEMA_KEYS')
    _need(all(type(key) is str for key in value), 'TYPE_DOMAIN')
    _need(set(value) == set(keys), 'SCHEMA_KEYS')
    return value


def _integer(value, maximum=MAX, minimum=0, nullable=False):
    if value is None and nullable:
        return None
    kind = type(value)
    _need(kind is int or kind is bool or kind is float or kind is str or kind is type(None), 'TYPE_DOMAIN')
    _need(kind is int and minimum <= value <= maximum, 'INTEGER_DOMAIN')
    return value


def _string(value, maximum, code):
    _need(type(value) is str, 'TYPE_DOMAIN')
    _need(0 < len(value) <= maximum, code)
    return value


def _list(value, nullable=False):
    if value is None and nullable:
        return None
    _need(type(value) is list, 'TYPE_DOMAIN')
    _need(len(value) <= 256, 'INTEGER_DOMAIN')
    return value


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if type(value) is MappingProxyType:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _capture(metadata):
    """Bounded exact-container copy, with no injected callback in this phase."""
    obj = _object(metadata, TOP)
    _integer(obj['schema_version'], 1, 1)
    files = _list(obj['files'], nullable=True)
    copied_files = None
    if files is not None:
        copied_files = []
        for item in files:
            item = _object(item, ('id', 'path', 'role', 'size', 'sha256'))
            copied_files.append(dict(id=_integer(item['id'], len(files) - 1), path=_string(item['path'], 4096, 'PATH_IDENTITY'), role=_string(item['role'], 64, 'ROLE'), size=_integer(item['size']), sha256=_string(item['sha256'], 64, 'DIGEST_FORMAT')))
    early = _list(obj['early_ids'], nullable=True)
    copied_early = None if early is None else [_integer(value, 255) for value in early]
    modules = _list(obj['modules'], nullable=True)
    copied_modules = None
    if modules is not None:
        copied_modules = []
        for item in modules:
            item = _object(item, ('name', 'file_id', 'dependencies', 'package'))
            deps = _list(item['dependencies'])
            _need(type(item['package']) is bool, 'TYPE_DOMAIN')
            copied_modules.append(dict(name=_string(item['name'], 128, 'MODULE_GRAPH'), file_id=_integer(item['file_id'], 255), dependencies=[_string(dep, 128, 'MODULE_GRAPH') for dep in deps], package=item['package']))
    aggregate = _object(obj['aggregate'], ('files', 'bytes'))
    aggregate = dict(files=_integer(aggregate['files'], 256, nullable=True), bytes=_integer(aggregate['bytes'], nullable=True))
    limits = _object(obj['limits'], LIMITS)
    copied_limits = {key: _integer(limits[key], 256 if key == 'max_files' else MAX, nullable=True) for key in LIMITS}
    representation = _object(obj['representation'], REP)
    copied_rep = {key: _integer(representation[key], 8 if key == 'report_copies' else COEF_MAX, 1, nullable=True) for key in REP}
    return _freeze(dict(schema_version=1, files=copied_files, early_ids=copied_early, modules=copied_modules, aggregate=aggregate, limits=copied_limits, representation=copied_rep))


def _path_key(path):
    _need(len(path) >= 4 and path[0] in 'CcDd' and path[1] == ':' and path[2] in '/\\', 'PATH_IDENTITY')
    try:
        units = len(path.encode('utf-16-le', 'strict')) // 2
    except UnicodeError:
        raise _Bad('PATH_IDENTITY')
    _need(units <= 4096, 'PATH_IDENTITY')
    normalized = path.replace('/', '\\')
    devices = {'con', 'prn', 'aux', 'nul', *('com' + str(i) for i in range(1, 10)), *('lpt' + str(i) for i in range(1, 10))}
    for part in normalized[3:].split('\\'):
        _need(part not in ('', '.', '..') and not part.endswith((' ', '.')), 'PATH_IDENTITY')
        _need(not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*~' for c in part), 'PATH_IDENTITY')
        stem = part.split('.', 1)[0].translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))
        _need(stem not in devices, 'PATH_IDENTITY')
    return normalized.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def _add(*values):
    if any(value is None for value in values):
        return None
    total = 0
    for value in values:
        _need(value <= MAX - total, 'ARITHMETIC_OVERFLOW')
        total += value
    return total


def _mul(a, b):
    if a is None or b is None:
        return None
    _need(a == 0 or b <= MAX // a, 'ARITHMETIC_OVERFLOW')
    return a * b


def _ceil_read(size):
    return size // 65536 + (1 if size % 65536 else 0)


def _encoded(value, newline=False):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + ('\n' if newline else '')).encode('utf-8')


def _empty_derived():
    result = {key: None for key in DERIVED}
    result.update(CONSTANTS)
    return result


def _steps(snapshot):
    """Each yielded checkpoint is checked outside all metadata-error catches."""
    files, early, modules = snapshot['files'], snapshot['early_ids'], snapshot['modules']
    aggregate, limits, rep = snapshot['aggregate'], snapshot['limits'], snapshot['representation']
    derived = _empty_derived()
    unknown = {group + '.' + key for group in ('limits', 'representation') for key, value in snapshot[group].items() if value is None}
    if files is None:
        unknown.add('files')
        for key in ('files', 'bytes'):
            if aggregate[key] is None:
                unknown.add('aggregate.' + key)
    if early is None:
        unknown.add('early_ids')
    if modules is None:
        unknown.add('modules')
    software_ids = set()
    if files is not None:
        ids = [item['id'] for item in files]
        _need(len(set(ids)) == len(ids) and set(ids) == set(range(len(files))), 'FILE_IDS')
        paths = set()
        for item in files:
            key = _path_key(item['path'])
            _need(key not in paths, 'DUPLICATE_PATH')
            paths.add(key)
            _need(item['role'] in ROLES, 'ROLE')
            _need(len(item['sha256']) == 64 and all(c in '0123456789abcdef' for c in item['sha256']), 'DIGEST_FORMAT')
            if item['role'] == 'captured_software':
                software_ids.add(item['id'])
            yield
        derived['N'] = len(files)
    if modules is not None:
        by_name = {}
        for item in modules:
            _need(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*', item['name']) is not None and item['name'] not in by_name, 'MODULE_GRAPH')
            _need(len(set(item['dependencies'])) == len(item['dependencies']), 'MODULE_GRAPH')
            by_name[item['name']] = item
        for item in modules:
            _need(all(dep in by_name for dep in item['dependencies']), 'MODULE_GRAPH')
            parts = item['name'].split('.')
            for length in range(1, len(parts)):
                parent = '.'.join(parts[:length])
                _need(parent in by_name and by_name[parent]['package'], 'MODULE_GRAPH')
            yield
        active, done = set(), set()
        def visit(name):
            _need(name not in active, 'MODULE_GRAPH')
            if name in done:
                return
            active.add(name)
            for dep in by_name[name]['dependencies']:
                visit(dep)
            active.remove(name)
            done.add(name)
        for name in by_name:
            visit(name)
        if files is not None:
            bindings = [item['file_id'] for item in modules]
            _need(len(set(bindings)) == len(bindings) and set(bindings) == software_ids, 'MODULE_BINDING')
            derived['M'] = len(modules)
    if early is not None:
        _need(len(set(early)) == len(early), 'MODULE_BINDING')
        if files is not None:
            _need(set(early) == software_ids, 'MODULE_BINDING')
            derived['B'] = len(early)
    if files is not None:
        _need(aggregate['files'] is None or aggregate['files'] == len(files), 'AGGREGATE_MISMATCH')
        if aggregate['bytes'] is not None:
            compared = 0
            for item in files:
                _need(item['size'] <= aggregate['bytes'] - compared, 'AGGREGATE_MISMATCH')
                compared += item['size']
            _need(compared == aggregate['bytes'], 'AGGREGATE_MISMATCH')
        derived['total_bytes'] = _add(*(item['size'] for item in files))
        derived['positive_files'] = sum(1 for item in files if item['size'] > 0)
    if files is None:
        n, size = aggregate['files'], aggregate['bytes']
        _need(n != 0 or size in (None, 0), 'AGGREGATE_MISMATCH')
        if n is not None and size is not None:
            if size == 0:
                lo = hi = 0
            else:
                _need(n > 0, 'AGGREGATE_MISMATCH')
                pmax = min(n, size)
                lo = _add(_ceil_read(size), 16)
                hi = _add((size - pmax) // 65536, _mul(17, pmax))
            derived['aggregate_R_range'] = [lo, hi]
            derived['aggregate_C_range'] = [_add(lo, _mul(6, n)), _add(hi, _mul(6, n))]
    else:
        derived['Q'] = _add(*(_ceil_read(item['size']) for item in files))
        derived['R'] = _add(derived['Q'], _mul(16, derived['positive_files']))
        derived['C'] = _add(_mul(6, derived['N']), derived['R'])
        derived['E'] = _add(_mul(6, derived['N']), _mul(2, derived['B']), _mul(2, derived['M']), 192)
        derived['captured_bytes'] = _add(*(item['size'] for item in files if item['role'] != 'hash_only_bulk'))
        derived['hash_only_bytes'] = _add(*(item['size'] for item in files if item['role'] == 'hash_only_bulk'))
    yield
    n, c, e = derived['N'], derived['C'], derived['E']
    capture = derived['captured_bytes']
    derived['work_buffer_bytes'] = 73738
    derived['query_witness_bytes'] = _mul(8218, n)
    derived['raw_payload_bytes'] = _add(73738, derived['query_witness_bytes'], capture)
    derived['immutable_capture_bytes'] = capture
    derived['logical_call_bytes'] = _mul(c, rep['call_record_bytes'])
    derived['index_bytes'] = _add(_mul(n, rep['file_index_bytes']), _mul(derived['M'], rep['module_index_bytes']))
    derived['hash_state_bytes'] = _mul(n, rep['hash_state_bytes'])
    derived['journal_bytes'] = _mul(1024, e)
    derived['canonical_report_bytes'] = _add(rep['report_base_bytes'], _mul(c, rep['report_call_bytes']), _mul(n, rep['report_file_bytes']), _mul(e, rep['report_event_bytes']))
    yield
    if files is not None:
        # Mathematical upper sizing rows, not an observed event-history union.
        closures = [dict(file_id=i, invoked=False, return_observed=False, success=False) for i in range(len(files))]
        digests = [dict(file_id=i, size=item['size'], sha256=item['sha256']) for i, item in enumerate(files)]
        derived['closure_array_bound_bytes'] = len(_encoded(closures))
        derived['digest_array_bytes'] = len(_encoded(digests))
    derived['packet_bound_bytes'] = _add(rep['packet_overhead_bytes'], derived['closure_array_bound_bytes'], derived['digest_array_bytes'])
    derived['output_reserved_bytes'] = _add(derived['journal_bytes'], _mul(5, derived['packet_bound_bytes']), derived['canonical_report_bytes'])
    derived['peak_declared_memory_bytes'] = _add(derived['raw_payload_bytes'], capture, rep['transient_bytes'], derived['logical_call_bytes'], derived['index_bytes'], derived['hash_state_bytes'], _mul(2, derived['journal_bytes']), _mul(5, derived['packet_bound_bytes']), _mul(rep['report_copies'], derived['canonical_report_bytes']))
    yield
    violations = []
    def compare(key, value, ordinal=None):
        limit = limits[key]
        if value is not None and limit is not None and value > limit:
            violations.append(dict(code=key.upper(), file_id=ordinal, required=value, limit=limit))
    compare('max_files', n)
    if files is not None:
        role_limit = dict(captured_software='max_software_file_bytes', captured_metadata='max_metadata_file_bytes', hash_only_bulk='max_bulk_file_bytes')
        for ordinal, item in enumerate(files):
            compare(role_limit[item['role']], item['size'], ordinal)
    for limit, key in (('max_captured_bytes', 'captured_bytes'), ('max_raw_payload_bytes', 'raw_payload_bytes'), ('max_calls', 'C'), ('max_events', 'E'), ('max_packet_bytes', 'packet_bound_bytes'), ('max_output_bytes', 'output_reserved_bytes'), ('max_report_bytes', 'canonical_report_bytes'), ('max_declared_memory_bytes', 'peak_declared_memory_bytes')):
        compare(limit, derived[key])
    violations.sort(key=lambda item: (item['code'], -1 if item['file_id'] is None else item['file_id']))
    yield
    status = 'EXCEEDS_DECLARED_BOUNDS' if violations else 'INDETERMINATE' if unknown else 'WITHIN_DECLARED_BOUNDS_ONLY'
    return dict(schema_version=1, status=status, derived=derived, unknowns=sorted(unknown), violations=violations, qualification=dict(QUALIFICATION))


class EnvelopeReport:
    __slots__ = ('_data', '_encoded')
    def __init__(self, mint, data, encoded):
        if mint is not _MINT:
            raise TypeError('factory-issued metadata report')
        object.__setattr__(self, '_data', data)
        object.__setattr__(self, '_encoded', encoded)
    def __setattr__(self, key, value):
        raise TypeError('immutable metadata report')
    def to_dict(self):
        return _thaw(self._data)
    def to_json_bytes(self):
        return self._encoded


def _finish(payload, check):
    encoded = _encoded(payload, newline=True)
    report = EnvelopeReport(_MINT, _freeze(payload), encoded)
    check()  # Final cancellation point; getters never re-enter the callback.
    return report


def _invalid(code, check):
    return _finish(dict(schema_version=1, status='REFUSED_INVALID_METADATA', derived=_empty_derived(), unknowns=[], violations=[dict(code=code, file_id=None, required=None, limit=None)], qualification=dict(QUALIFICATION)), check)


def analyze_admission(metadata, *, check):
    """Return conditional declared bounds, never a live-ready/verified token."""
    if not callable(check):
        raise TypeError('check must be callable')
    check()
    try:
        snapshot = _capture(metadata)
    except _Bad as error:
        return _invalid(error.code, check)
    check()  # The second callback sees an already detached immutable snapshot.
    steps = _steps(snapshot)
    while True:
        try:
            next(steps)
        except _Bad as error:
            return _invalid(error.code, check)
        except StopIteration as done:
            payload = done.value
            break
        check()  # Deliberately outside every metadata-error catch above.
    return _finish(payload, check)
