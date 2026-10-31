"""Check the retained first reference result without rerunning its SHA stream."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
P = H.parent / 'recovery-step9-role-aware-producer-20261029'
def read(name, expected):
    path = H / name
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    return json.loads(raw)

d = read('ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json', '1a3e47ec28b1f96c4ac0d5c9c9eb7c2f13288cf5a6df4e3c4f6853d07a56aa03')
assert d['status'] == 'REFERENCE_COMPLETE' and d['final_deadline_veto'] is False
assert d['actual_reference_owner_or_subject_calls'] == 0
assert d['reference_bytes_hashed'] == 3991999872
assert d['unique_checkpoint_count'] == d['reference_hash_copy_calls'] == 198
assert 0 < d['reference_elapsed_seconds'] < 300
sizes = [r['bytes'] for r in json.loads((P / 'RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json').read_bytes())['files']]
assert d['size_values'] == sizes and len(sizes) == 213 and sum(sizes) == 9017363392
assert set(d['checkpoint_sha256']) == {str(n) for n in sizes}
assert tuple(d[k] for k in ('N','B','M','Q','R','C','E')) == (216,2,2,8799,12255,13551,1496)
descs = d['descriptors']
assert len(descs) == 216 and len({x['path'] for x in descs}) == 216
for i, x in enumerate(descs):
    assert type(x['file_id']) is int and x['file_id'] == i
    assert x['path'].startswith('D:\\FictionalRoleAwareLarge\\')
    assert type(x['size']) is int and x['size'] > 0
    assert len(x['sha256']) == 64 and len(bytes.fromhex(x['sha256'])) == 32
    if i < 3:
        assert x['capture'] is True
        assert x['role'] == ('captured_software' if i < 2 else 'captured_metadata')
        raw = bytes.fromhex(x['utf8_hex'])
        assert len(raw) == x['size'] and hashlib.sha256(raw).hexdigest() == x['sha256']
    else:
        assert x['capture'] is False and x['role'] == 'hash_only_bulk'
        assert 'utf8_hex' not in x and x['periodic_size_index'] == i - 3
        assert x['size'] == sizes[i - 3] and x['sha256'] == d['checkpoint_sha256'][str(x['size'])]
assert sum(x['size'] for x in descs) == 9017363601
assert sum(x['size'] for x in descs if x['capture']) == 209
assert sum((x['size'] + 1048575) // 1048576 for x in descs) == 8799
assert all(v is False for v in d['qualification'].values())
for role, p in d['input_pins'].items():
    raw = Path(p['path']).read_bytes()
    assert len(raw) == p['bytes'] and hashlib.sha256(raw).hexdigest() == p['sha256'], role
report = dict(schema_version=1, status='REFERENCE_METADATA_CHECKS_PASS_ONLY',
    reference_sha256='1a3e47ec28b1f96c4ac0d5c9c9eb7c2f13288cf5a6df4e3c4f6853d07a56aa03',
    reference_bytes_hashed=3991999872, prefix_checkpoints=198, descriptors_checked=216,
    total_future_producer_bytes=9017363601, captured_bytes=209,
    reference_elapsed_seconds=d['reference_elapsed_seconds'],
    checks='Exact first result/pins, geometry, all invented descriptors and digest bindings. Tiny209B hashes rechecked; no prefix SHA stream or producer rerun.',
    prefix_reference_or_subject_reexecuted=False, producer_execution_authorized=False,
    real_entry_FFI_physical_native_resource_scientific_qualified=False)
outpath = H / 'ROLE-AWARE-LARGE-REFERENCE-ROOT-CHECK-v1.json'
with outpath.open('x', encoding='utf-8', newline='\n') as out:
    json.dump(report, out, sort_keys=True, indent=2); out.write('\n')
print(json.dumps(dict(status=report['status'], sha256=hashlib.sha256(outpath.read_bytes()).hexdigest())))
