"""Finite detached tests of the new harness retention functions only.

No Source4 import, owner construction, real file port or producer dispatch.
"""
import ast
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace as NS

H = Path(__file__).resolve().parent
source = H / 'run_role_aware_large_injected_v3.py'
raw = source.read_bytes()
expected = sys.argv[1]
assert len(expected) == 64 and hashlib.sha256(raw).hexdigest() == expected
names = {'HarnessError', 'require', 'canonical', 'raw_atom', 'persist_canonical_raw'}
tree = ast.parse(raw, str(source))
nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
assert {n.name for n in nodes} == names
scope = dict(hashlib=hashlib, json=json, struct=struct, C=13551, QUERY_BYTES=1775088)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), scope)
sentinel = object()
atom = scope['raw_atom']
assert atom(sentinel, sentinel) == {'tag': 'UNOBSERVED', 'value': None}
assert atom(None, sentinel) == {'tag': 'NULL', 'value': None}
assert atom(0, sentinel) == {'tag': 'INT', 'value': 0}
assert atom(False, sentinel) == {'tag': 'BOOL', 'value': False}
for value in (-(1 << 63), (1 << 64) - 1):
    assert atom(value, sentinel) == {'tag': 'INT', 'value': value}
for value in (-(1 << 63) - 1, 1 << 64):
    assert atom(value, sentinel)['tag'] == 'OBSERVED_UNENCODABLE'
assert atom(-0.0, sentinel) == {'tag': 'FLOAT64_BITS', 'bits': '0000000000000080'}
nan_bits = '010000000000f87f'
assert atom(struct.unpack('<d', bytes.fromhex(nan_bits))[0], sentinel)['bits'] == nan_bits
assert atom(b'\x00\xff', sentinel) == {'tag': 'BYTES', 'hex': '00ff'}

class Unformattable:
    def __repr__(self):
        raise AssertionError('retention must not format the original object')
    __str__ = __repr__

opaque = Unformattable()
assert atom(opaque, sentinel)['local_object_id'] == id(opaque)
owner = NS(registry=NS(_calls=[]))
def cell(i):
    return NS(owner=owner, ordinal=i, file=None, api=None, prepared=False,
        invoked=False, scalar=sentinel, count=sentinel, error=sentinel,
        error_definition=sentinel, input_handle=sentinel,
        wrapper_return=False, wrapper_state='not_returned', stopped=False,
        scalar_aux_ack=False, count_aux_ack=False, right_transfer_ack=False,
        _reservation_fold='unapplied', _read_fold_phase='pending', _read_contribution=None,
        hash_attempted=False, hash_return=sentinel, hash_count=0, _hash_fold_phase='pending',
        copy_attempted=False, copy_return=sentinel, copy_count=0, _copy_fold_phase='pending',
        pre_clock_attempted=False, pre_clock=sentinel, post_clock_attempted=False,
        post_clock=sentinel, buffer=None, generation=None, buffer_state='not_applicable',
        buffer_written=0, query_bytes=None)

reserved, stopped, unencodable = [cell(i) for i in range(3)]
stopped.file = NS(id=7, close_reserved=False)
stopped.api = 'ReadFile'; stopped.prepared = stopped.invoked = stopped.stopped = True
stopped.scalar = None; stopped.count = stopped.error = 0; stopped.error_definition = False
stopped.pre_clock_attempted = True; stopped.pre_clock = -0.0
query = b'\x80\x00\x00\x00\x00\x00\x00\x00'
stopped.query_bytes = query
unencodable.scalar = opaque; unencodable.hash_return = None
owner.registry._calls = [reserved, stopped, unencodable]
world = NS(owner=owner, S=NS(UNOBSERVED=sentinel))
outdir = H / 'raw-sidecar-harness-only-check-v3'
outdir.mkdir()
retained = []; progress = {}
scope['persist_canonical_raw'](world, outdir, retained, progress)
rows = [json.loads(line) for line in (outdir / 'independent-canonical-raw-facts.jsonl').read_bytes().splitlines()]
assert [r['ordinal'] for r in rows] == [0, 1, 2]
assert rows[0]['invoked'] is False and rows[0]['prepared'] is False
assert rows[0]['scalar']['tag'] == 'UNOBSERVED'
assert rows[1]['scalar']['tag'] == 'NULL' and rows[1]['count'] == {'tag': 'INT', 'value': 0}
assert rows[1]['error'] == {'tag': 'INT', 'value': 0}
assert rows[1]['error_definition'] == {'tag': 'BOOL', 'value': False}
assert rows[1]['wrapper_return_observed'] is False and rows[1]['stopped'] is True
assert rows[1]['auxiliary'] == dict(scalar_ack=False, count_ack=False, right_transfer_ack=False)
assert rows[1]['clocks']['pre_raw']['bits'] == '0000000000000080'
assert rows[2]['scalar']['tag'] == 'OBSERVED_UNENCODABLE'
assert rows[2]['hash']['raw_return']['tag'] == 'NULL'
assert (outdir / 'independent-canonical-query-frames.bin').read_bytes() == query
assert progress['rows_expected'] == progress['rows_written'] == 3
assert progress['query_bytes'] == 8 and progress['unencodable_atoms'] == 1
assert progress['state'] == 'OBSERVED_UNENCODABLE_RAW_RETAINED_AS_EXPLICIT_UNKNOWN'
for p in retained:
    data = Path(p['path']).read_bytes()
    assert len(data) == p['bytes'] and hashlib.sha256(data).hexdigest() == p['sha256']
report = dict(schema_version=1, status='PASS_HARNESS_RAW_SIDECAR_ONLY',
    harness_sha256=expected, extracted_functions=sorted(names),
    detached_records_checked=3, raw_atom_controls=12, artifacts=retained,
    scope='Exact harness functions on three detached mock records. Reserved/uninvoked, raw NULL/zero/false, absent helper ACK, binary clocks, query bytes and explicit unencodable values remain distinct. No formatting of opaque objects.',
    subject_imports=0, owner_constructions=0, producer_dispatches=0,
    large_runs=0, native_calls=0, qualification=False)
path = H / 'ROLE-AWARE-LARGE-HARNESS-RAW-SIDECAR-CHECK-v3.json'
with path.open('x', encoding='utf-8', newline='\n') as out:
    json.dump(report, out, sort_keys=True, indent=2); out.write('\n')
print(json.dumps(dict(status=report['status'], sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
