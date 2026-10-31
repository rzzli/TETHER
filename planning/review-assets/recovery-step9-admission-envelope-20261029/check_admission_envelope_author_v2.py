"""Eight bounded author methods; synthetic metadata, no runtime qualification."""
import builtins
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import types

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'admission_envelope_v2.py'
SOURCE_SHA = 'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191'
data = SOURCE.read_bytes()
assert hashlib.sha256(data).hexdigest() == SOURCE_SHA
fixtures = json.loads((HERE / 'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json').read_text(encoding='utf-8'))
BASE = next(v for v in fixtures['vectors'] if v['id'] == 'mixed_role_all_bounds_equal')
''.encode('utf-16-le')  # Authorized trusted codec bootstrap, before ACTIVE.
ACTIVE = [False]
DENIALS = []
CALLS = [0]


def audit(event, args):
    if ACTIVE[0] and (event == 'open' or event.startswith(('subprocess.', 'socket.', 'ctypes.'))):
        DENIALS.append(event)
        raise AssertionError('subject operation denied: ' + event)


sys.addaudithook(audit)
trusted = {'json': json, 're': re, 'types': types}


def closed_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in trusted:
        raise ImportError(name)
    return trusted[name]


S = types.ModuleType('admission_envelope_v2')
S.__builtins__ = dict(vars(builtins), __import__=closed_import)
code = compile(data, '<author-captured-admission-v2>', 'exec')
ACTIVE[0] = True
try:
    exec(code, S.__dict__)
finally:
    ACTIVE[0] = False


def invoke(fn, *args, **kwargs):
    ACTIVE[0] = True
    try:
        return fn(*args, **kwargs)
    finally:
        ACTIVE[0] = False


def analyze(metadata, check=lambda: None):
    CALLS[0] += 1
    return invoke(S.analyze_admission, metadata, check=check)


def report(metadata, check=lambda: None):
    return invoke(analyze(metadata, check).to_dict)


def invalid(metadata, expected):
    value = report(metadata)
    assert value['status'] == 'REFUSED_INVALID_METADATA'
    assert value['violations'][0]['code'] == expected, (value['violations'][0]['code'], expected)


def t01_baseline_and_scope():
    value = report(copy.deepcopy(BASE['metadata']))
    assert value == BASE['expected']
    d = value['derived']
    assert (d['N'], d['Q'], d['R'], d['C'], d['E']) == (4, 5, 69, 93, 224)
    assert d['captured_bytes'] == 209 and d['raw_payload_bytes'] == 106819
    assert all(flag is False for flag in value['qualification'].values())


def t02_all_numeric_boolean_and_zero_coefficients():
    checked = 0
    for group in ('limits', 'representation'):
        for key in BASE['metadata'][group]:
            metadata = copy.deepcopy(BASE['metadata']);metadata[group][key] = True
            invalid(metadata, 'INTEGER_DOMAIN');checked += 1
    for key in BASE['metadata']['representation']:
        metadata = copy.deepcopy(BASE['metadata']);metadata['representation'][key] = 0
        invalid(metadata, 'INTEGER_DOMAIN');checked += 1
    assert checked == 34


def t03_path_scalar_units_and_aliases():
    metadata = copy.deepcopy(BASE['metadata'])
    metadata['files'][0]['path'] = 'D:\\scalar\\\u03b1\U0001f600\\a.py'
    assert report(metadata)['status'] == 'WITHIN_DECLARED_BOUNDS_ONLY'
    metadata['files'][0]['path'] = 'D:\\' + '\U0001f600' * 2047 + '\\a.py'
    invalid(metadata, 'PATH_IDENTITY')
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'][0]['path'] = 'E:\\future-policy\\a.py'
    invalid(metadata, 'PATH_IDENTITY')
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'][1]['path'] = metadata['files'][0]['path'].lower().replace('\\', '/')
    invalid(metadata, 'DUPLICATE_PATH')


def t04_detached_inputs_reports_and_cached_bytes():
    metadata = copy.deepcopy(BASE['metadata']);checks = [0]
    def mutate():
        checks[0] += 1
        if checks[0] == 2:
            metadata['limits'].clear();metadata['files'][0]['size'] = 0
    result = analyze(metadata, mutate);before = invoke(result.to_dict)
    assert before == BASE['expected']
    raw = invoke(result.to_json_bytes);count = checks[0]
    before['derived']['N'] = 999;before['qualification']['runtime_authorized'] = True
    assert invoke(result.to_dict) == BASE['expected']
    assert invoke(result.to_json_bytes) is raw and checks[0] == count
    assert raw == (json.dumps(BASE['expected'], sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def t05_private_domain_error_callback_identity():
    count = [0]
    def counter():count[0] += 1
    analyze(copy.deepcopy(BASE['metadata']), counter)
    for position in sorted({1, (count[0] + 1) // 2, count[0]}):
        original = S._Bad('ROLE');seen = [0]
        def cancel():
            seen[0] += 1
            if seen[0] == position:raise original
        try:
            analyze(copy.deepcopy(BASE['metadata']), cancel)
        except BaseException as actual:
            assert actual is original
        else:
            raise AssertionError('same-class callback exception swallowed')
        assert seen[0] == position


def t06_near_maximum_unknown_and_real_overflow():
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'][3]['size'] = 2**63 - 1 - 209
    metadata['aggregate']['bytes'] = 2**63 - 1;metadata['representation']['call_record_bytes'] = None
    value = report(metadata)
    assert value['status'] == 'EXCEEDS_DECLARED_BOUNDS'
    assert value['derived']['total_bytes'] == 2**63 - 1
    assert 'representation.call_record_bytes' in value['unknowns']
    metadata['representation']['call_record_bytes'] = 2**31 - 1
    invalid(metadata, 'ARITHMETIC_OVERFLOW')


def t07_exact_container_and_integer_subclasses():
    class BadDict(dict):
        def __iter__(self):raise AssertionError('custom traversal')
    invalid(BadDict(BASE['metadata']), 'TYPE_DOMAIN')
    class BadList(list):
        def __iter__(self):raise AssertionError('custom traversal')
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'] = BadList(metadata['files'])
    invalid(metadata, 'TYPE_DOMAIN')
    class IntSubclass(int):pass
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'][0]['size'] = IntSubclass(58)
    invalid(metadata, 'TYPE_DOMAIN')


def t08_aggregate_information_without_vector_admission():
    metadata = copy.deepcopy(BASE['metadata']);metadata['files'] = None;metadata['early_ids'] = None;metadata['modules'] = None
    metadata['aggregate'] = dict(files=213, bytes=9017363392)
    value = report(metadata);d = value['derived']
    assert value['status'] == 'INDETERMINATE'
    assert d['aggregate_R_range'] == [137611, 141215]
    assert d['aggregate_C_range'] == [138889, 142493]
    assert d['N'] is None and d['C'] is None and d['work_buffer_bytes'] == 73738
    assert not value['violations']


def main():
    started = time.monotonic();results = []
    for name, fn in tuple(globals().items()):
        if name.startswith('t') and name[1:3].isdigit():
            first = CALLS[0]
            try:
                fn();results.append(dict(method=name, passed=True, analyze_invocations=CALLS[0] - first))
            except BaseException as error:
                results.append(dict(method=name, passed=False, analyze_invocations=CALLS[0] - first, error_class=type(error).__name__, error=str(error)[:500]))
    proof = dict(schema_version=1, status='PASS' if all(r['passed'] for r in results) else 'FIRST_FAILURES_RETAINED', source=dict(path=str(SOURCE), bytes=len(data), sha256=SOURCE_SHA), checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), methods=len(results), results=results, analyze_invocations=CALLS[0], audit_denials=DENIALS, elapsed_seconds=time.monotonic() - started, codec_bootstrap='Trusted UTF-16-LE warmed before ACTIVE; source import list unchanged.', scope='Eight pure metadata author methods, not runtime/profile/streaming qualification.', actual_target_API_calls=0, original_payload_reads=0)
    out = HERE / 'ADMISSION-ENVELOPE-AUTHOR-PROOF-v2.json'
    with out.open('x', encoding='utf-8', newline='\n') as f:f.write(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps(proof, indent=2));print('PROOF_SHA256', hashlib.sha256(out.read_bytes()).hexdigest())
    return int(proof['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
