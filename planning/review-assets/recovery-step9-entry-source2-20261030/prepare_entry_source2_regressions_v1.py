"""Freeze exact coherent Source2 inputs/harness; AST and metadata only."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'recovery-step9-entry-source-20261029'


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(name, value):
    path = HERE / name
    with path.open('xb') as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8'))
    return pin(path)


def ast_methods(path):
    return {n.name: ast.dump(n,include_attributes=False)
            for n in ast.parse(Path(path).read_bytes().decode('utf-8'),filename=str(path)).body
            if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}


def dependencies(path):
    result=set()
    for node in ast.walk(ast.parse(Path(path).read_bytes().decode('utf-8'),filename=str(path))):
        if isinstance(node,ast.Import):
            result.update(x.name for x in node.names)
        elif isinstance(node,ast.ImportFrom):
            assert node.level == 0 and node.module is not None
            result.add(node.module)
    return sorted(result)


def main():
    pause_path=HERE/'ENTRY-SOURCE-PAUSE-v2.json'
    pause=json.loads(pause_path.read_bytes().decode('utf-8'))
    pause_pin=pin(pause_path)
    module_names=dict(kernel='preflight_entry_kernel_v2',owner_ops='preflight_owner_ops_v2',
                      file_view='preflight_file_view_v2',codec='role_ledger_codec_v4')
    sources={}
    for role,row in pause['source_module_map'].items():
        actual=pin(ROOT/row['path'])
        assert actual['bytes']==row['bytes'] and actual['sha256']==row['sha256']
        assert row['module']==module_names[role]
        sources[row['module']]=actual
    row=pause['captured_dependency']
    actual=pin(ROOT/row['path'])
    assert actual['bytes']==55497 and actual['sha256']=='c0b3c5a689e72803487c9c3504513bc2bc0e4a4466b91128393fdbc4436f5b5e'
    assert actual['bytes']==row['bytes'] and actual['sha256']==row['sha256']
    sources[module_names['codec']]=actual
    helpers=[]
    for role in ('codec','owner_ops','file_view'):
        name=module_names[role]
        p=sources[name]
        helpers.append(dict(module=name,fictional_path='D:\\EntrySynthetic2\\helpers\\'+name+'.py',
                            bytes=p['bytes'],sha256=p['sha256'],source_pin=p,
                            declared_dependencies=dependencies(p['path'])))
    old_input_pin=pin(OLD/'ENTRY-ACTUAL-HELPER-INPUTS-v1.json')
    assert old_input_pin['sha256']=='10d0d0dd66ab858e3e893f8c8ca096f5d5cf8cdd5fe21f75c1bc10dc0301c605'
    old_inputs=json.loads((OLD/'ENTRY-ACTUAL-HELPER-INPUTS-v1.json').read_bytes().decode('utf-8'))
    metadata=dict(old_inputs['metadata'])
    metadata['fictional_path']='D:\\EntrySynthetic2\\fixture-metadata.json'
    bulk=dict(old_inputs['bulk'])
    bulk['fictional_path']='D:\\EntrySynthetic2\\periodic-bulk.bin'
    chunk=old_inputs['chunk']
    meta_body=bytes.fromhex(metadata['hex'])
    assert len(meta_body)==metadata['bytes']==68
    assert hashlib.sha256(meta_body).hexdigest()==metadata['sha256']
    assert json.loads(meta_body)['native'] is False
    assert bulk['bytes']==2097169 and chunk==1048576
    block=bytes(range(256))*256
    bulk_hash=hashlib.sha256()
    blocks,remainder=divmod(bulk['bytes'],len(block))
    for _ in range(blocks):
        bulk_hash.update(block)
    bulk_hash.update(block[:remainder])
    assert bulk_hash.hexdigest()==bulk['sha256']
    sizes=[x['bytes'] for x in helpers]+[metadata['bytes'],bulk['bytes']]
    n,b,m=len(sizes),len(helpers),len(helpers)
    q=sum(s//chunk+int(s%chunk!=0) for s in sizes)
    qb=sum(s//chunk+int(s%chunk!=0) for s in sizes[:b])
    geometry=dict(N=n,B=b,M=m,Q=q,R=q+16*sum(s>0 for s in sizes),
                  C=6*n+q+16*sum(s>0 for s in sizes),E=6*n+2*b+2*m+192,
                  bootstrap_calls=5*b+qb,work_calls=5*n+q,terminal_calls=6*n+q,
                  known_bytes=sum(sizes),captured_bytes=sum(sizes[:-1]),
                  early_bytes=sum(sizes[:b]),original_closes=n)
    assert helpers[1]['bytes']==39889 and helpers[1]['sha256']=='e438b8862b84309777c6c97eae79f0d1967c943525fc18b27b28f2c5e0e16a33'
    assert helpers[2]['bytes']==3614 and helpers[2]['sha256']=='9b782a58d450543989fa79be0325ac24038b4b8a1338cf52069a53e8067c4f0e'
    assert geometry==dict(N=5,B=3,M=3,Q=7,R=87,C=117,E=234,bootstrap_calls=18,
                         work_calls=32,terminal_calls=37,known_bytes=2196237,
                         captured_bytes=99068,early_bytes=99000,original_closes=5)
    inputs=dict(schema_version=2,scope='INVENTED_ACTUAL_SOURCE2_HELPER_ENTRY_TEST_INPUTS_ONLY',
                source_pause=pause_pin,source_map=sources,module_names=module_names,
                kernel_tcb=dict(pin=sources[module_names['kernel']],captured_as_helper=False),
                helpers=helpers,chunk=chunk,metadata=metadata,bulk=bulk,
                output_key='ENTRY_SYNTHETIC_SOURCE2_REGRESSIONS',baseline_geometry=geometry,
                prior_fixture_metadata_pin=old_input_pin,
                old_source_runtime_fallback=False,source1_replay=False,
                original_target_paths_followed=False,subject_imports=0,subject_runs=0,
                qualification=dict(native=False,physical=False,new84=False,real_first_entry=False))
    input_pin=save('ENTRY-SOURCE2-ACTUAL-HELPER-INPUTS-v1.json',inputs)
    harness={name:pin(HERE/path) for name,path in
             dict(support='entry_independent_test_support_v2.py',world='entry_independent_world_v2.py',
                  regressions='entry_initial_regressions_v2.py',runner='run_entry_source2_regressions_v1.py').items()}
    old_methods=ast_methods(OLD/'entry_initial_regressions_v1.py')
    new_methods=ast_methods(HERE/'entry_initial_regressions_v2.py')
    assert len(old_methods)==3 and len(new_methods)==4
    assert all(new_methods[name]==body for name,body in old_methods.items())
    for p in harness.values():
        ast.parse(Path(p['path']).read_bytes().decode('utf-8'),filename=p['path'])
    old_support=(OLD/'entry_independent_test_support_v1.py').read_bytes().decode('utf-8')
    new_support=(HERE/'entry_independent_test_support_v2.py').read_bytes().decode('utf-8')
    assert new_support.replace('preflight_entry_kernel_v2','preflight_entry_kernel_v1')==old_support
    old_world=(OLD/'entry_independent_world_v1.py').read_bytes().decode('utf-8')
    new_world=(HERE/'entry_independent_world_v2.py').read_bytes().decode('utf-8')
    assert new_world.replace('entry_independent_test_support_v2','entry_independent_test_support_v1')==old_world
    scope=pin(OLD/'ENTRY-SOURCE2-CORRECTION-AUTHORING-SCOPE-v1.json')
    assert scope['sha256']=='911cb56cb89fb7cd5cec6acb30baf3319473522acfa77ac53bafc5bb8c97b38f'
    preparation=dict(schema_version=1,status='FROZEN_SOURCE2_FOUR_REGRESSIONS_BEFORE_EXECUTION',
                     source_pause=pause_pin,inputs=input_pin,source_map=sources,harness=harness,
                     authoring_scope=scope,
                     original_three_regression_freeze=pin(OLD/'ENTRY-INITIAL-REGRESSION-FREEZE-v1.json'),
                     actual_source1_entry_failure=pin(OLD/'ENTRY-SOURCE1-SMOKE-PROOF-v1.json'),
                     methods=list(new_methods),first_three_method_asts_equal=True,
                     supplemental='Commit actual native scalar, then throw before carrier cache acknowledgment; preserve known bank value without report/cache healing, once cleanup.',
                     support_delta='Only exact kernel source/module spelling v1->v2.',
                     world_delta='Only trusted support module spelling v1->v2.',
                     chronology='Original three methods authored/frozen before Source2. Supplemental converse authored after Source2 correction authorization and during source drafting, before coherent source pause/test execution; not claimed pre-fix authored.',
                     prefix=dict(actual_helpers=3,actual_helper_bytes=geometry['early_bytes'],
                                 full_geometry=geometry,kernel_pre_entry_tcb_bytes=sources[module_names['kernel']]['bytes']),
                     source1_replayed=False,subject_imports=0,subject_tests=0,
                     full_32_53='NOT_EXECUTED',native25='NOT_EXECUTED',
                     limitations=['All raw/output/factory backends synthetic; native/physical/real-first-entry authority absent.',
                                  'The shared 60-second deadline is cooperative, not a callback-free hang guarantee.',
                                  'Initial entry smoke is retained as an actual source failure; downstream Source1 sink/cache remain NOT_REACHED.'])
    prep_pin=save('ENTRY-SOURCE2-REGRESSION-PREPARATION-v1.json',preparation)
    outline=dict(status='UNBOUND_NO_EXECUTION_AUTHORITY',deadline_seconds=60,methods=list(new_methods),
                 execution_scope=None,source_pause=pause_pin,preparation=prep_pin,inputs=input_pin,
                 source_map=sources,harness=harness)
    outline_pin=save('ENTRY-SOURCE2-REGRESSION-BINDING-OUTLINE-v1.json',outline)
    freeze=save('ENTRY-SOURCE2-REGRESSION-FREEZE-v1.json',
                dict(schema_version=1,status='FROZEN_BEFORE_FIRST_SOURCE2_IMPORT_OR_TEST',
                     source_pause=pause_pin,inputs=input_pin,preparation=prep_pin,outline=outline_pin,
                     harness=harness,preparer=pin(__file__),adaptation_author=pin(HERE/'adapt_entry_regression_harness_v2.py'),
                     subject_imports=0,subject_runs=0))
    print(json.dumps(dict(freeze=freeze,preparation=prep_pin,inputs=input_pin,harness=harness,
                          geometry=geometry)))


if __name__=='__main__':
    main()
