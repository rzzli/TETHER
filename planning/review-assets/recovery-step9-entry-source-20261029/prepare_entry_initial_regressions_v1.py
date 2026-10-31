"""Metadata/AST-only input freeze. Does not import any harness or subject."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(name, value):
    path = HERE / name
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(path)


def dependencies(path):
    tree = ast.parse(Path(path).read_bytes().decode('utf-8'), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module is not None
            names.add(node.module)
    return sorted(names)


def main():
    pause_path = HERE / 'ENTRY-SOURCE-PAUSE-v1.json'
    pause_pin = pin(pause_path)
    assert pause_pin['sha256'] == '5594746b7d9687a7a386f4188564726f8ab000f1ec4ba38e557b7696373687fb'
    pause = json.loads(pause_path.read_bytes().decode('utf-8'))
    module_names = dict(kernel='preflight_entry_kernel_v1', owner_ops='preflight_owner_ops_v1',
                        file_view='preflight_file_view_v1', codec='role_ledger_codec_v4')
    sources = {}
    for role, row in pause['source_module_map'].items():
        actual = pin(ROOT / row['path'])
        assert actual['sha256'] == row['sha256'] and actual['bytes'] == row['bytes']
        assert row['module'] == module_names[role]
        sources[row['module']] = actual
    row = pause['captured_dependency']
    actual = pin(ROOT / row['path'])
    assert actual['sha256'] == row['sha256'] and actual['bytes'] == row['bytes']
    sources[module_names['codec']] = actual
    helpers = []
    for role in ('codec', 'owner_ops', 'file_view'):
        name = module_names[role]
        p = sources[name]
        helpers.append(dict(module=name, fictional_path='D:\\EntrySynthetic\\helpers\\' + name + '.py',
                            bytes=p['bytes'], sha256=p['sha256'],
                            declared_dependencies=dependencies(p['path']),
                            source_pin=p))
    body = b'{"scope":"entry-harness","native":false}'
    body = body + b' ' * (67 - len(body)) + b'\n'
    assert len(body) == 68 and json.loads(body)['native'] is False
    bulk_size = 2097169
    block = bytes(range(256)) * 256
    digest = hashlib.sha256()
    blocks, remainder = divmod(bulk_size, len(block))
    for _ in range(blocks):
        digest.update(block)
    digest.update(block[:remainder])
    total_helpers = sum(x['bytes'] for x in helpers)
    assert total_helpers == 98641
    chunk = 1048576
    sizes = [x['bytes'] for x in helpers] + [len(body), bulk_size]
    n, b, m = len(sizes), len(helpers), len(helpers)
    q = sum(s // chunk + int(s % chunk != 0) for s in sizes)
    qb = sum(s // chunk + int(s % chunk != 0) for s in sizes[:b])
    geometry = dict(N=n, B=b, M=m, Q=q, R=q+16*sum(s > 0 for s in sizes),
                    C=6*n+q+16*sum(s > 0 for s in sizes), E=6*n+2*b+2*m+192,
                    bootstrap_calls=5*b+qb, work_calls=5*n+q, terminal_calls=6*n+q,
                    known_bytes=sum(sizes), captured_bytes=sum(sizes[:-1]),
                    early_bytes=total_helpers, original_closes=n)
    assert geometry == dict(N=5,B=3,M=3,Q=7,R=87,C=117,E=234,
                           bootstrap_calls=18,work_calls=32,terminal_calls=37,
                           known_bytes=2195878,captured_bytes=98709,early_bytes=98641,original_closes=5)
    inputs = dict(schema_version=1, scope='INVENTED_ACTUAL_HELPER_ENTRY_TEST_INPUTS_ONLY',
                  source_pause=pause_pin, source_map=sources, module_names=module_names,
                  kernel_tcb=dict(pin=sources[module_names['kernel']], captured_as_helper=False),
                  helpers=helpers, chunk=chunk,
                  metadata=dict(fictional_path='D:\\EntrySynthetic\\fixture-metadata.json',
                                hex=body.hex(), bytes=len(body), sha256=hashlib.sha256(body).hexdigest()),
                  bulk=dict(fictional_path='D:\\EntrySynthetic\\periodic-bulk.bin',bytes=bulk_size,
                            sha256=digest.hexdigest(), recipe='byte_at_offset=i_mod_256; no full body allocated'),
                  output_key='ENTRY_SYNTHETIC_INITIAL_REGRESSIONS_V1', baseline_geometry=geometry,
                  original_target_paths_followed=False, subject_imports=0, subject_runs=0,
                  qualification=dict(native=False, physical=False, new84=False, real_first_entry=False))
    input_pin = save('ENTRY-ACTUAL-HELPER-INPUTS-v1.json', inputs)
    harness_paths = dict(support='entry_independent_test_support_v1.py',
                         world='entry_independent_world_v1.py',
                         regressions='entry_initial_regressions_v1.py',
                         runner='run_entry_source1_smoke_v1.py')
    harness = {name: pin(HERE / path) for name, path in harness_paths.items()}
    methods = []
    for name, p in harness.items():
        tree = ast.parse(Path(p['path']).read_bytes().decode('utf-8'), filename=p['path'])
        if name == 'regressions':
            methods = [node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test')]
    assert methods == ['test01_valid_entry', 'test02_normal_captured_helpers_finish',
                       'test03_staged_scalar_has_no_cleanup_authority']
    preparation = dict(schema_version=1, status='FROZEN_THREE_REGRESSIONS_BEFORE_SOURCE_CORRECTION_AND_EXECUTION',
                       source_pause=pause_pin, inputs=input_pin, source_map=sources, harness=harness,
                       authoring_scope=pin(ROOT / 'planning/review-assets/recovery-step9-production-preflight-20261029/ENTRY-SOURCE-AUTHORING-SCOPE-v1.json'),
                       intended_regressions=methods,
                       source1_execution=dict(allowed_only_after_root_binding=True,
                                              selected_check=methods[0], maximum_entry_attempts=1,
                                              stop_on_constructor_failure=True,
                                              deeper_checks_on_setup_failure='NOT_REACHED',
                                              runtime_alias_or_partial_core_workaround=False),
                       prefix=dict(actual_helper_bytes=total_helpers, helpers=len(helpers),
                                   old_209B_or_21call_prefix_used=False, full_geometry=geometry,
                                   kernel_pre_entry_tcb_bytes=sources[module_names['kernel']]['bytes']),
                       static_authoring_checks=dict(ast_files=len(harness),ast='PASS',
                                                    helper_dependencies='EXACT_AST_NAMES',
                                                    subject_imports=0,subject_tests=0),
                       limitations=['One cooperative 60-second deadline, no hard callback-free hang guarantee.',
                                    'All raw/output/factory backends are synthetic; no native or physical authority.',
                                    'The full32/53 and native25 controls are not executed by this smoke runner.'])
    preparation_pin = save('ENTRY-INITIAL-REGRESSION-PREPARATION-v1.json', preparation)
    outline = dict(status='UNBOUND_NO_EXECUTION_AUTHORITY', deadline_seconds=60,
                   expected_entry_error_code='INVALID_INPUT', execution_scope=None,
                   source_pause=pause_pin, preparation=preparation_pin, inputs=input_pin,
                   source_map=sources,harness=harness,
                   selected_execution='test01_valid_entry only; stop without downstream tests')
    outline_pin = save('ENTRY-SOURCE1-SMOKE-BINDING-OUTLINE-v1.json', outline)
    freeze_pin = save('ENTRY-INITIAL-REGRESSION-FREEZE-v1.json',
                      dict(schema_version=1,status='FROZEN_BEFORE_SOURCE1_ENTRY_SMOKE_OR_SOURCE2',
                           source_pause=pause_pin, inputs=input_pin, preparation=preparation_pin,
                           outline=outline_pin,harness=harness,preparer=pin(__file__),
                           subject_imports=0,subject_runs=0,source2_exists=False))
    print(json.dumps(dict(freeze=freeze_pin, preparation=preparation_pin, inputs=input_pin,
                          harness=harness, geometry=geometry)))


if __name__ == '__main__':
    main()
