"""Independent AST/hash/fixture framing only; never imports a subject or test."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSETS = HERE.parent
OUT = HERE / 'ENTRY-E08-SUITE-INDEPENDENT-STATIC-CHECK-v1.json'


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not OUT.exists(), 'retain first checker result'
    checked = {}
    def verify(value):
        actual = pin(value['path'])
        assert all(actual[k] == value[k] for k in ('bytes', 'sha256')), value['path']
        checked[actual['path']] = actual
        return actual
    def read(name):
        return json.loads((HERE / name).read_bytes())
    def pins_in(value):
        if type(value) is dict:
            if {'path', 'bytes', 'sha256'} <= set(value) and type(value['bytes']) is int:
                verify(value)
            else:
                for child in value.values(): pins_in(child)
        elif type(value) is list:
            for child in value: pins_in(child)
    def tree(path, normalize=False):
        text = Path(path).read_text(encoding='utf-8')
        if normalize:
            for stem in ('entry_kernel', 'owner_ops', 'file_view'):
                text = text.replace('preflight_' + stem + '_v3', 'preflight_' + stem + '_v4')
        return ast.parse(text)
    def defs(node, prefix=''):
        result = {}
        for child in ast.iter_child_nodes(node):
            key = prefix
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                key = prefix + child.name
                if not isinstance(child, ast.ClassDef): result[key] = ast.dump(child, include_attributes=False)
                key += '.'
            result.update(defs(child, key))
        return result

    frozen = read('ENTRY-E08-SUITE-FREEZE-v1.json')
    pins_in(frozen)
    prep = read('ENTRY-E08-SUITE-PREPARATION-v1.json')
    inputs = read('ENTRY-E08-SUITE-INPUTS-v1.json')
    pause = read('ENTRY-SOURCE-PAUSE-v4.json')
    delta = read('ENTRY-SOURCE-DELTA-v4.json')
    pins_in(prep); pins_in(pause); pins_in(delta)
    old_input_pin = inputs['source3_base_inputs']; verify(old_input_pin)
    old_inputs = json.loads(Path(old_input_pin['path']).read_bytes())
    verify(inputs['literal_corpus']); verify(inputs['integration_scenarios'])
    corpus = json.loads(Path(inputs['literal_corpus']['path']).read_bytes())
    scenarios = json.loads(Path(inputs['integration_scenarios']['path']).read_bytes())
    assert frozen['source_map'] == prep['source_map'] == inputs['source_map']
    assert frozen['harness'] == prep['harness']
    assert set(frozen['source_map']) == {'preflight_entry_kernel_v4', 'preflight_owner_ops_v4', 'preflight_file_view_v4', 'role_ledger_codec_v4'}
    for kind in ('kernel', 'owner_ops', 'file_view'):
        assert frozen['source_map']['preflight_' + ('entry_kernel' if kind == 'kernel' else kind) + '_v4']['sha256'] == pause['sources'][kind]['sha256']

    old = tree(ROOT / delta['base_sources']['kernel']['path'], True)
    new = tree(ROOT / delta['new_sources']['kernel']['path'])
    old_defs, new_defs = defs(old), defs(new)
    changed = [k for k in old_defs if old_defs[k] != new_defs.get(k)]
    added = [k for k in new_defs if k not in old_defs]
    assert set(changed) == set(delta['kernel_ast']['changed_existing_functions'])
    assert set(added) == set(delta['kernel_ast']['added_functions'])
    assert (len(changed), len(old_defs) - len(changed), len(added)) == (21, 200, 28)
    fragment = tree(ROOT / pause['root_graph_fragment']['path']).body[0]
    assert new_defs['_manifest_policy_graph'] == ast.dump(fragment, include_attributes=False)
    for name in ('APIS', 'FRAMES', 'PROFILE_N4', 'PROFILE_ORIGINAL7_1M', 'ROLES', 'ROLE_WIRE', 'ARTIFACT_CAPS', 'STAGES', 'GATES', 'EVENTS', 'KINDS', 'QUALIFICATION'):
        def assignment(t):
            return next(ast.dump(n, include_attributes=False) for n in t.body
                if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in n.targets))
        assert assignment(old) == assignment(new), name
    for kind in ('owner_ops', 'file_view'):
        a = (ROOT / delta['base_sources'][kind]['path']).read_text(encoding='utf-8')
        b = (ROOT / delta['new_sources'][kind]['path']).read_text(encoding='utf-8')
        assert a.replace('preflight_entry_kernel_v3', 'preflight_entry_kernel_v4') == b

    causal_old = ASSETS / 'recovery-step9-entry-contract-tests-20261030/entry_contract_cases_v2.py'
    causal_new = Path(frozen['harness']['causal']['path'])
    assert defs(tree(causal_old)) == defs(tree(causal_new))
    support_old = ASSETS / 'recovery-step9-entry-source3-20261030/entry_independent_test_support_v3.py'
    support_new = Path(frozen['harness']['support']['path'])
    assert support_old.read_text(encoding='utf-8').replace('preflight_entry_kernel_v3', 'preflight_entry_kernel_v4') == support_new.read_text(encoding='utf-8')
    correction_old = tree(ASSETS / 'recovery-step9-entry-source3-20261030/entry_initial_regressions_v4.py')
    correction_new = tree(frozen['harness']['corrections']['path'])
    a, b = defs(correction_old), defs(correction_new)
    assert [k for k in a if a[k] != b.get(k)] == ['test05_stopped_close_normal_return_does_not_heal_cache']
    class RemoveAppendedBinding(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'PreboundServices':
                assert len(node.args) == 10 and ast.dump(node.args[-1], include_attributes=False) == "Attribute(value=Name(id='services', ctx=Load()), attr='manifest_policy_binding', ctx=Load())"
                node.args.pop()
            return node
    assert defs(correction_old) == defs(RemoveAppendedBinding().visit(correction_new))

    branches = inputs['suite_branches']
    counts = {g: sum(v['group'] == g for v in branches) for g in ('CORRECTIONS', 'LITERALS', 'INTEGRATION', 'CAUSAL')}
    assert counts == frozen['declared_groups'] == {'CORRECTIONS': 5, 'LITERALS': 52, 'INTEGRATION': 15, 'CAUSAL': 50}
    assert len(branches) == len({v['branch'] for v in branches}) == 122
    assert [v['case'] for v in branches if v['group'] == 'LITERALS'] == [v['id'] for v in corpus['vectors']]
    assert [(v['case'], v['variant']) for v in branches if v['group'] == 'INTEGRATION'] == [(s['id'], b) for s in scenarios['scenarios'] for b in s['branches']]
    retained = [v for v in old_inputs['branches'] if v['case'] != 'E08' and not (v['case'] == 'E16' and v['variant'] in ('Source4_constructor', 'Source4_start_injected'))]
    assert inputs['branches'] == retained and len(retained) == 50
    assert [(v['case'], v['variant']) for v in branches if v['group'] == 'CAUSAL'] == [(v['case'], v['variant']) for v in retained]

    helpers = inputs['helpers']; early = [v['bytes'] for v in helpers]
    assert sum(early) == prep['actual_helper_prefix_bytes'] == 99000
    for helper in helpers:
        assert helper['sha256'] == inputs['source_map'][helper['module']]['sha256']
        assert helper['bytes'] == inputs['source_map'][helper['module']]['bytes']
    assert inputs['kernel_pre_entry_tcb_bytes'] == prep['kernel_pre_entry_tcb_bytes'] == 145042
    for value in [inputs['metadata'], *inputs['toy_modules']]:
        raw = bytes.fromhex(value['hex'])
        assert len(raw) == value['bytes'] and hashlib.sha256(raw).hexdigest() == value['sha256']
    def geometry(sizes, captured, early_sizes, m):
        n = len(sizes); q = sum(divmod(s, 1048576)[0] + bool(divmod(s, 1048576)[1]) for s in sizes)
        r = q + 16 * sum(s > 0 for s in sizes)
        return dict(N=n, B=len(early_sizes), M=m, Q=q, R=r, C=6*n+r,
            E=6*n+2*len(early_sizes)+2*m+192,
            bootstrap_calls=5*len(early_sizes)+sum(divmod(s,1048576)[0]+bool(divmod(s,1048576)[1]) for s in early_sizes),
            work_calls=5*n+q, terminal_calls=6*n+q, known_bytes=sum(sizes),
            captured_bytes=sum(s for s,c in zip(sizes,captured) if c), early_bytes=sum(early_sizes), original_closes=n)
    meta = inputs['metadata']['bytes']; bulk = inputs['bulk']['bytes']
    normal = geometry(early+[meta,bulk], [True]*4+[False], early, 3)
    toy = geometry(early+[58,83,meta,bulk], [True]*6+[False], early+[58,83], 5)
    large = geometry(early+[meta,3991999872], [True]*4+[False], early, 3)
    assert normal == inputs['baseline_geometry'] == prep['normal_geometry']
    assert toy == inputs['toy_geometry'] == prep['toy_geometry']
    assert large == inputs['large_geometry'] == prep['large_geometry']
    result = dict(schema_version=1, status='PASS_STATIC_METADATA_AND_AST_ONLY', checker=pin(__file__),
        freeze=pin(HERE/'ENTRY-E08-SUITE-FREEZE-v1.json'), verified_file_count=len(checked), verified_pins=list(checked.values()),
        kernel_ast=dict(changed=changed, unchanged=200, added=added), groups=counts,
        causal_function_asts_equal=True, corrections_only_typed_binding_argument_added=True,
        source_helpers_import_only=True, frozen_graph_exact=True, caps_unchanged=True,
        normal_geometry=normal, toy_geometry=toy, large_geometry=large,
        inherited_metadata_note='inputs.kernel_tcb and baseline_input are retained Source3 baseline context, not the current active module map; active Source4 TCB is source_map plus kernel_pre_entry_tcb_bytes145042.',
        subject_imports=0, subject_runs=0, native_or_original_targets_followed=False, qualification=False)
    with OUT.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(proof=pin(OUT), verified_files=len(checked), groups=counts)))


if __name__ == '__main__':
    main()
