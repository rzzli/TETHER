"""Fixed corpus JSON/byte framing only; imports no C/subject or SDK tools."""
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
checks = []


def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def check(name, result):
    checks.append(dict(name=name, passed=bool(result)))


def unpack(raw, offset, fmt):
    return struct.unpack_from('<' + fmt, raw, offset)[0]


def verify(row, field, phase):
    raw = bytes.fromhex(row[field])
    api = row['api']
    kind = 1 if api in (1, 9) else 3 if api in (2, 4) else 2
    assert len(raw) == 256
    assert (unpack(raw, 0, 'H'), unpack(raw, 2, 'H'), unpack(raw, 4, 'I'),
            unpack(raw, 8, 'I'), unpack(raw, 12, 'H')) == (1, 256, row['ordinal'], 7, api)
    assert unpack(raw, 32, 'Q') == 19 and unpack(raw, 68, 'I') == 0xa5a5a5a5
    assert unpack(raw, 72, 'I') == phase and unpack(raw, 76, 'I') == 0
    assert not any(raw[80:128])
    flags = ((1 if api in (6, 13) else 0) |
             (2 if api in (2, 3, 4, 5, 6, 7, 10, 11, 13, 14) else 0) |
             (32 if api in (7, 11) else 0) | (4 if phase else 0) |
             (8 if phase == 2 else 0))
    assert unpack(raw, 24, 'I') == flags
    assert unpack(raw, 20, 'I') == (16 if api in (6, 13) else 0)
    for offset, axis_kind, width in ((128, kind, 8 if kind == 1 else 4),
                                    (160, 4, 4), (192, 3, 4), (224, 5, 1)):
        assert unpack(raw, offset + 8, 'I') == 7
        assert unpack(raw, offset + 12, 'H') == axis_kind and raw[offset + 14] == width
        assert raw[offset + 15] == 0 and unpack(raw, offset + 24, 'Q') == 0
        assert not any(raw[offset + width:offset + 8])
    scalar = row['scalar_bits'] if phase else 0
    count = row['count'] if phase == 2 and api in (6, 13) else 0
    error = row['error'] if phase == 2 and row['probes_error'] else 0
    definition = int(row['probes_error']) if phase else 0
    for offset, value, committed in ((128, scalar, phase != 0),
            (160, count, phase == 2 and api in (6, 13)),
            (192, error, phase == 2 and row['probes_error']),
            (224, definition, phase != 0)):
        assert unpack(raw, offset, 'Q') == value
        assert unpack(raw, offset + 16, 'I') == int(committed)
        assert unpack(raw, offset + 20, 'I') == int(committed)
    return True


expected = json.loads((HERE / 'NATIVE-CARRIER-FAKE-EXPECTATIONS-v1.json').read_bytes())
try:
    semantic = expected['semantic_vectors']
    malformed = expected['malformed_wrapper_vectors']
    initial = expected['initializer_negative_vectors']
    partial = expected['interrupted_error_vector']
    check('exact_counts', (len(semantic), len(malformed), len(initial)) == (46, 22, 10)
          and expected['counts']['named_controls'] == 79)
    ids = [row['id'] for row in semantic + malformed + initial] + [partial['id']]
    check('79_unique_IDs', len(ids) == len(set(ids)) == 79)
    for row in semantic:
        check(row['id'] + '/initialized', verify(row, 'initialized_copy256_hex', 0))
        check(row['id'] + '/normal', verify(row, 'normal_copy256_hex', 2))
        check(row['id'] + '/error_boundary', verify(row, 'error_boundary_copy256_hex', 1)
              if row['probes_error'] else row['error_boundary_copy256_hex'] is None)
    check('partial_initialized', verify(partial, 'initialized_copy256_hex', 0))
    check('partial_escaped', verify(partial, 'escaped_copy256_hex', 1))
    check('malformed_literal_lengths', all(len(bytes.fromhex(row['cell_copy256_hex'])) == 256
          and row['expected_status'] == 'PF14_INVALID' and row['expected_fake_target_calls'] == 0
          for row in malformed))
    check('initializer_all_bytes_unchanged', all(bytes.fromhex(row['expected_cell_copy256_hex']) ==
          bytes([0xc3]) * 256 and row['expected_status'] == 'PF14_INVALID' for row in initial))
    check('zero_requests_negative_not_returned_count', [(row['api'], row['requested'], row['flags'])
          for row in initial if 'requested0_present' in row['id']] == [(6, 0, 3), (13, 0, 3)])
    fields = ('initializer_attempts', 'wrapper_attempts', 'actual_fake_target_calls',
              'error_callback_entries', 'error_callback_normal_returns', 'error_boundary_copies')
    check('79_116_47_17_16_17', tuple(expected['planned_invocations'][key] for key in fields) ==
          (79, 116, 47, 17, 16, 17))
    old = (HERE / 'preflight_file14_raw_v2.c').read_bytes()
    new = (HERE / 'preflight_file14_raw_v3.c').read_bytes()
    marker = b'static void publish('
    check('publish_finish_and14wrappers_exact', old[old.index(marker):] == new[new.index(marker):])
    check('header_exact', pin('preflight_file14_raw_v1.h')['sha256'] ==
          '7460f59849b6c8a7f800b61e3eb6d4b70f1e16ac15dabed12f0ceadb48ccbf50')
except BaseException as error:
    checks.append(dict(name='metadata_checker_exception', passed=False,
                       error_type=type(error).__name__, message=str(error)))

result = dict(schema_version=1, status='PASS' if all(row['passed'] for row in checks) else 'HOLD',
    checks=checks, counts=dict(checks=len(checks), passed=sum(row['passed'] for row in checks),
                              failed=sum(not row['passed'] for row in checks)),
    checker=pin(__file__), inputs=[pin(name) for name in
        ('NATIVE-CARRIER-FAKE-EXPECTATIONS-v1.json', 'native_carrier_fake_tests_v1.c',
         'preflight_file14_raw_v3.c', 'preflight_file14_raw_v1.h')],
    initial_tooling_note='Initial inline metadata checker failed to parse its own missing-space ternaries before any checks or subject work. This explicit saved helper corrects that display/checker syntax; no source/test artifact changed.',
    activity='Only fixed JSON/struct/hash data framing and exact source text comparison. No C preprocessing, compiler, SDK, FFI, fake-target or subject execution.')
path = HERE / 'NATIVE-CARRIER-PREBUILD-LITERAL-CHECK-v1.json'
with path.open('xb') as stream:
    stream.write((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
print(json.dumps(dict(status=result['status'], counts=result['counts'], report=pin(path.name))))
