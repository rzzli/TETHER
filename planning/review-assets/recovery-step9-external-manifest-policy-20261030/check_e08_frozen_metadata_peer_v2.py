"""Independent fixed-corpus framing checks; not a policy solver or subject runner."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FREEZE = HERE / 'E08-POLICY-PRECODE-FREEZE-v1.json'
OUT = HERE / 'E08-INDEPENDENT-FROZEN-METADATA-CHECK-v2.json'
CANON = dict(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, **CANON).encode('utf-8')


def pin(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def main():
    assert not OUT.exists(), 'retain first metadata-check result; no overwrite'
    frozen = json.loads(FREEZE.read_bytes())
    checked = []
    for name, expected in frozen['pins'].items():
        actual = pin(ROOT / expected['path'])
        assert actual == expected, (name, actual, expected)
        checked.append({'name': name, **actual})
    assert len(checked) == frozen['verified_pin_count'] == 24
    contract = json.loads((ROOT / frozen['pins']['contract']['path']).read_bytes())
    schema = json.loads((ROOT / frozen['pins']['schema']['path']).read_bytes())
    corpus = json.loads((ROOT / frozen['pins']['independent_corpus']['path']).read_bytes())
    draft = json.loads((ROOT / frozen['pins']['literal_draft']['path']).read_bytes())
    provenance = json.loads((ROOT / frozen['pins']['independent_provenance']['path']).read_bytes())
    scenarios = json.loads((ROOT / frozen['pins']['genuine_integration_scenarios']['path']).read_bytes())
    vectors = corpus['vectors']
    assert vectors == draft['vectors']
    assert len(vectors) == corpus['vector_count'] == provenance['vector_count'] == 52
    assert [v['ordinal'] for v in vectors] == list(range(1, 53))
    assert len({v['id'] for v in vectors}) == 52
    assert {v['expected_boundary'] for v in vectors} == {'CORE_POLICY_AFTER_ORIGINAL_START'}
    assert schema['x_contract']['sha256'] == frozen['pins']['contract']['sha256']
    assert set(contract['report']['exact_keys']) == set(schema['$defs']['report']['required'])

    # Manually assigned from the reviewed fixed literal facts, not computed by a graph engine.
    expected = [
        'EXECUTION_BASIS_VALIDATED', 'EXECUTION_BASIS_VALIDATED', 'AUTHORING_ONLY',
        'POLICY_UNBUILT', 'POLICY_UNBUILT', 'POLICY_FORBIDDEN_ANCESTRY',
        'POLICY_FORBIDDEN_ANCESTRY', 'POLICY_FORBIDDEN_ANCESTRY', 'POLICY_FORBIDDEN_ANCESTRY',
        'POLICY_CYCLE', 'POLICY_CYCLE', 'POLICY_CYCLE', 'POLICY_DEPENDENCY_ROLE',
        'POLICY_DEPENDENCY_ROLE', 'POLICY_UNKNOWN_NODE', 'POLICY_DUPLICATE_ID',
        'POLICY_PIN_CONFLICT', 'POLICY_DUPLICATE_ID', 'POLICY_BINDING_MISMATCH',
        'POLICY_BINDING_MISMATCH', 'POLICY_BINDING_MISMATCH', 'POLICY_BINDING_MISMATCH',
        'POLICY_SCHEMA', 'POLICY_DOMAIN', 'POLICY_DOMAIN', 'POLICY_DOMAIN',
        'AUTHORING_ONLY', 'POLICY_DOMAIN', 'POLICY_DOMAIN', 'EXECUTION_BASIS_VALIDATED',
        'POLICY_LIMIT', 'POLICY_DOMAIN', 'AUTHORING_ONLY', 'POLICY_LIMIT', 'POLICY_DOMAIN',
        'EXECUTION_BASIS_VALIDATED', 'POLICY_LIMIT', 'EXECUTION_BASIS_VALIDATED',
        'POLICY_LIMIT', 'EXECUTION_BASIS_VALIDATED', 'POLICY_LIMIT', 'AUTHORING_ONLY',
        'POLICY_LIMIT', 'POLICY_BASIS_MISMATCH', 'POLICY_BASIS_MISMATCH',
        'POLICY_DUPLICATE_ID', 'POLICY_PIN_CONFLICT', 'POLICY_PIN_CONFLICT',
        'POLICY_DUPLICATE_ID', 'POLICY_PIN_CONFLICT', 'POLICY_DOMAIN', 'POLICY_CYCLE',
    ]
    report_count = 0
    refusal_count = 0
    rows = []
    binding_keys = {'mode', 'current_decision_id', 'current_output_ids', 'basis_ids',
                    'external_tcb_pins', 'prior_metadata_pins'}
    for value, wanted in zip(vectors, expected, strict=True):
        req = value['request']
        b, e = req['binding'], req['envelope']
        # Constructor shell only. Invalid domains are deliberately NOT admitted here.
        assert type(b) is dict and set(b) == binding_keys
        for name in ('current_output_ids', 'basis_ids', 'external_tcb_pins', 'prior_metadata_pins'):
            assert type(b[name]) is list and len(b[name]) <= 256
            for item in b[name]:
                if name.endswith('_pins'):
                    assert type(item) is dict and set(item) == {'id', 'bytes', 'sha256'}
                    assert all(type(x) in (str, int, float, bool, type(None)) for x in item.values())
                else:
                    assert type(item) in (str, int, float, bool, type(None))
        assert type(b['mode']) in (str, int, float, bool, type(None))
        assert type(b['current_decision_id']) in (str, int, float, bool, type(None))
        try:
            size = len(canonical(req))
        except UnicodeEncodeError:
            size = None
            assert value['ordinal'] in (34, 35)
        expected_framing = {'canonical_combined_utf8_bytes': size}
        if value['ordinal'] in (34, 35):
            expected_framing['reason'] = 'INVALID_UNICODE_LITERAL; encoding is never a successful outcome'
        assert value['framing'] == expected_framing
        outcome = value['expected']
        if outcome['kind'] == 'REPORT':
            report_count += 1
            nodes = e['nodes']
            reconstructed = {
                'schema_version': 1, 'mode': b['mode'], 'status': wanted,
                'node_count': len(nodes),
                'edge_count': sum(len(n['pin_dependencies']) for n in nodes),
                'basis_ids': b['basis_ids'], 'external_anchor_ids': e['external_anchor_ids'],
                'prior_root_ids': [p['id'] for p in b['prior_metadata_pins']],
                'planned_ids': [n['id'] for n in nodes if n['state'] == 'PLANNED_SOURCE'],
                'unbuilt_ids': [n['id'] for n in nodes if n['state'] == 'UNBUILT'],
                'binding_sha256': sha(canonical(b)), 'envelope_sha256': sha(canonical(e)),
            }
            assert outcome['report'] == reconstructed, value['id']
            assert set(reconstructed) == set(schema['$defs']['report']['required'])
            observed = outcome['report']['status']
        else:
            refusal_count += 1
            assert outcome['kind'] == 'REFUSAL'
            observed = outcome['code']
        assert observed == wanted, value['id']
        rows.append({'ordinal': value['ordinal'], 'id': value['id'],
                     'reviewed_outcome': wanted, 'canonical_utf8_bytes': size})
    assert (report_count, refusal_count) == (10, 42)
    assert provenance['vector_data_ascii_json_sha256'] == sha(json.dumps(
        vectors, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('utf-8'))

    # Fixed bound geometries, no general policy traversal or admission implementation.
    get = lambda number: vectors[number - 1]
    assert get(27)['request']['envelope']['nodes'][2]['bytes'] == 2**63 - 1
    assert get(28)['request']['envelope']['nodes'][2]['bytes'] == 2**63
    assert len(get(30)['request']['binding']['basis_ids'][0]) == 128
    assert len(get(31)['request']['binding']['basis_ids'][0]) == 129
    assert len(get(33)['request']['envelope']['nodes'][-1]['reason']) == 256
    assert len(get(34)['request']['envelope']['nodes'][-1]['reason']) == 257
    assert len(get(36)['request']['binding']['current_output_ids']) == 14
    assert len(get(37)['request']['binding']['current_output_ids']) == 15
    assert len(get(38)['request']['envelope']['nodes']) == 256
    assert len(get(39)['request']['envelope']['nodes']) == 257
    for number, total in ((40, 4096), (41, 4097)):
        nodes = get(number)['request']['envelope']['nodes']
        roots = {n['id'] for n in nodes if n['role'] == 'EXTERNAL_TCB'}
        assert len(roots) == 33
        assert sum(len(n['pin_dependencies']) for n in nodes) == total
        assert all(set(n['pin_dependencies']) <= roots for n in nodes)
        assert all(len(n['pin_dependencies']) == len(set(n['pin_dependencies'])) for n in nodes)
    for number, size in ((42, 131072), (43, 131073)):
        req = get(number)['request']
        roots = {n['id'] for n in req['envelope']['nodes'] if n['role'] == 'EXTERNAL_TCB'}
        assert len(roots) == 16
        assert len(canonical(req)) == size
        assert all(set(n['pin_dependencies']) <= roots for n in req['envelope']['nodes'])
    assert get(44)['request'] == get(1)['request'] == get(45)['request']
    assert len(get(44)['entry_basis_pins']) == 1
    assert len(get(1)['entry_basis_pins']) == len(get(45)['entry_basis_pins']) == 2
    assert get(1)['entry_basis_pins'][0]['sha256'] != get(45)['entry_basis_pins'][0]['sha256']

    ss = scenarios['scenarios']
    assert [s['id'] for s in ss] == ['I%02d' % n for n in range(1, 11)]
    assert sum(len(s['branches']) for s in ss) == 15
    assert scenarios['counts'] == {'named_scenarios': 10, 'planned_expanded_branches': 15,
                                   'executed_scenarios': 0, 'subject_imports': 0}
    result = {
        'schema_version': 1, 'status': 'PASS_FIXED_METADATA_FRAMING_ONLY',
        'checker': pin(Path(__file__).resolve()), 'freeze': pin(FREEZE),
        'verified_pins': checked, 'counts': {'vectors': 52, 'reports': report_count,
            'refusals': refusal_count, 'constructor_shells': 52,
            'named_integration_scenarios': 10, 'planned_branches': 15},
        'literal_rows': rows,
        'checks': ['24 retained pin bytes/hashes', '52 draft/final object identities by value',
            '52 structural constructor shells', '52 canonical sizes or explicit Unicode absence',
            '10 exact report fields/counts/digests', '42 manually reviewed refusal labels',
            '7 independent equality/one-over bound pairs', 'independent EntryPlan mismatch context',
            '10/15 unexecuted genuine integration geometry'],
        'activity': {'subject_imports': 0, 'subject_runs': 0, 'policy_solver': False,
                     'native_or_original_targets_followed': False},
        'qualification': False,
    }
    with OUT.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=True)
        stream.write('\n')
    print(json.dumps({'result': pin(OUT), 'counts': result['counts']}, sort_keys=True))


if __name__ == '__main__':
    main()
