"""Metadata-only preparation. Never imports a subject, world or assertion file."""
import ast
import copy
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SOURCE = ROOT / 'planning/review-assets/recovery-step9-entry-source4-20261030'


def pin(path):
    path = path.resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def exact(path, sha256):
    result = pin(path)
    assert result['sha256'] == sha256, result
    return result


def write(name, data):
    path = BASE / name
    assert not path.exists(), 'preserve first metadata output'
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True)+'\n', encoding='utf-8', newline='\n')
    return pin(path)


def geometry(value):
    sizes = [(r['bytes'], True) for r in value['helpers']]
    sizes += [(value['metadata']['bytes'], True), (value['bulk']['bytes'], False)]
    chunk = value['chunk']
    n = len(sizes);b = m = len(value['helpers'])
    q = sum(size//chunk + int(size % chunk != 0) for size, _ in sizes)
    positive = sum(size > 0 for size, _ in sizes)
    early = sum(r['bytes'] for r in value['helpers'])
    early_reads = sum(r['bytes']//chunk + int(r['bytes'] % chunk != 0) for r in value['helpers'])
    return dict(N=n, B=b, M=m, Q=q, R=q+16*positive, C=6*n+q+16*positive,
                E=6*n+2*b+2*m+192, bootstrap_calls=5*b+early_reads,
                work_calls=5*n+q, terminal_calls=6*n+q,
                known_bytes=sum(size for size, _ in sizes),
                captured_bytes=sum(size for size, captured in sizes if captured),
                early_bytes=early, original_closes=n)


def main():
    scope = pin(ROOT / 'planning/review-assets/recovery-step9-real-route-closure-20261030/NATIVE25-COMPONENT-HARNESS-AUTHORING-SCOPE-v1.json')
    source_pause = exact(SOURCE / 'ENTRY-SOURCE-PAUSE-v4.json', 'c38df4b3133133805e7a13c30e2d65d21748e4c1ce1a320929c0871f05dfab67')
    old_inputs = exact(SOURCE / 'ENTRY-E08-SUITE-INPUTS-v2.json', '23708be2b0e78dac2ae34dba6178086f6a053efd380a6c5ce5ec8a2b7a4c26d1')
    prior = json.loads(Path(old_inputs['path']).read_bytes())
    keys = ('source_map','module_names','helpers','metadata','bulk','chunk','baseline_geometry','output_key')
    normal = {key: copy.deepcopy(prior[key]) for key in keys}
    normal['output_key'] = 'native25_component_fixture'
    assert normal['bulk']['bytes'] == 2097169
    assert geometry(normal) == normal['baseline_geometry']
    empty = copy.deepcopy(normal)
    empty_digest = hashlib.sha256(b'').hexdigest()
    empty['metadata'].update(bytes=0, hex='', sha256=empty_digest)
    empty['bulk'].update(bytes=0, sha256=empty_digest, recipe='zero-length same periodic-prefix recipe')
    empty['baseline_geometry'] = geometry(empty)
    for values in (normal, empty):
        body = bytes.fromhex(values['metadata']['hex'])
        assert len(body) == values['metadata']['bytes'] and hashlib.sha256(body).hexdigest() == values['metadata']['sha256']
    source_pins = {}
    for name, item in normal['source_map'].items():
        actual = exact(Path(item['path']), item['sha256']);assert actual['bytes'] == item['bytes']
        source_pins[name] = actual
    matrix = exact(BASE / 'NATIVE25-COMPONENT-BRANCH-MATRIX-v2.json', 'e52a6c66d8839b2e40115ff6b10f439432d29ba103614760e33f6862cd585049')
    data = json.loads(Path(matrix['path']).read_bytes())
    executable = {x['id'] for row in data['cases'] for x in row['branches'] if x['classification'] in ('DATA','SOURCE_RUNTIME')}
    cases = pin(BASE / 'native25_component_cases_v1.py')
    tree = ast.parse(Path(cases['path']).read_text(encoding='utf-8'))
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in n.targets))
    assert {k.value for k in table.keys} == executable and len(executable) == 43
    pins = dict(authoring_scope=scope, source_pause=source_pause, prior_fixture_inputs=old_inputs,
                matrix=matrix, cases=cases, runner=pin(BASE/'run_native25_component_v1.py'),
                preparer=pin(Path(__file__)), support=pin(SOURCE/'entry_independent_test_support_v4.py'),
                world=pin(SOURCE/'entry_independent_world_v4.py'))
    for name, item in source_pins.items():pins['subject_'+name] = item
    for key in ('cases','runner','preparer','support','world'):
        ast.parse(Path(pins[key]['path']).read_text(encoding='utf-8'))
    inputs = write('NATIVE25-COMPONENT-INPUTS-v1.json', dict(
        schema_version=1, world_inputs=normal, empty_world_inputs=empty,
        source_pause=source_pause, baseline_fixture=old_inputs,
        prepared_data_only=True, no_large_stream=True,
        subject_imports=0, subject_runs=0,
        note='Only helper source text and same small fictional metadata/periodic recipe. No target path was followed; no4GB digest/body or prior122 suite execution is included.'))
    pins['inputs'] = inputs
    prep = write('NATIVE25-COMPONENT-PREPARATION-v1.json', dict(
        schema_version=1, status='METADATA_AND_AST_ONLY_READY_FOR_INDEPENDENT_STATIC_PEER',
        pins=pins, counts=data['counts'], executable_branch_count=43,
        normal_geometry=normal['baseline_geometry'], empty_geometry=empty['baseline_geometry'],
        fixture_variants='N23 byte-domain assertions contrast real captured empty bytes with hash-only empty absence; same already-declared recipes, independent empty SHA.',
        proposed_limits=dict(cooperative_seconds=60, genuine_worlds_max=20, synthetic_data_instances_max=32, synthetic_capacity_max=20, bulk_bytes=2097169),
        expected_diagnostic='Two API/axis-kind mismatches must typed-refuse NATIVE_STATE_NOT_REPRESENTABLE; firstactualFAIL remains failure if current source accepts. No xfail/oracle weakening.',
        activity=dict(subject_imports=0, subject_runs=0, native_or_original_operations=0), qualification=False))
    pins['preparation'] = prep
    freeze = write('NATIVE25-COMPONENT-FREEZE-v1.json', dict(
        schema_version=1, status='FROZEN_BEFORE_FIRST_SUBJECT_IMPORT_OR_NATIVE25_COMPONENT_RUN',
        pins=pins, scope='UnchangedSource4 only; RootC14 source/build/driver is not a subject.',
        counts=data['counts'], executable_branch_count=43, no_subject_changes=True,
        independent_peer_required=True, separate_Root_execution_binding_required=True,
        activity=dict(subject_imports=0, subject_runs=0, C_or_native_or_model_operations=0),
        qualification=dict(native25_complete=False, native_C=False, physical=False, real_resources=False, RSS=False)))
    outline = write('NATIVE25-COMPONENT-BINDING-OUTLINE-v1.json', dict(
        schema_version=1, status='OUTLINE_ONLY_NOT_AUTHORIZED_TO_RUN',
        future_binding_filename='NATIVE25-COMPONENT-BINDING-v1.json',
        required_binding=dict(status='ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT', run_authorized=True,
                              deadline_seconds=60, freeze=freeze,
                              execution_scope={'path':'ROOT_TO_SUPPLY','bytes':None,'sha256':None}),
        required_execution_scope_status='ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION',
        invocation='python -I -B run_native25_component_v1.py only after actual binding and finite independent peer',
        outputs=['NATIVE25-COMPONENT-ATTEMPT-v1.json','NATIVE25-COMPONENT-ARTIFACTS-v1','NATIVE25-COMPONENT-PROOF-v1.json'],
        one_shot=True, known_diagnostic_failure_is_not_setup_failure=True, qualification=False))
    print(json.dumps(dict(inputs=inputs, preparation=prep, freeze=freeze, outline=outline)))


if __name__ == '__main__':
    main()
