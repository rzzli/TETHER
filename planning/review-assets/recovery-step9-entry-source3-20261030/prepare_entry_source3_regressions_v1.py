"""Exact Source3 namespace adaptation/input freeze; metadata and AST only."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-entry-source2-20261030'


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact(p):
    assert pin(p['path'])==p
    return Path(p['path']).read_bytes()


def save(name,value):
    path=HERE/name
    with path.open('xb') as f:f.write((json.dumps(value,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    return pin(path)


def write_new(name,text):
    ast.parse(text,filename=str(HERE/name))
    with (HERE/name).open('xb') as f:f.write(text.encode('utf-8'))
    return pin(HERE/name)


def functions(text):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body
            if isinstance(n,ast.FunctionDef)}


def dependencies(path):
    names=set()
    for n in ast.walk(ast.parse(Path(path).read_bytes().decode('utf-8'))):
        if isinstance(n,ast.Import):names.update(x.name for x in n.names)
        if isinstance(n,ast.ImportFrom):
            assert n.level==0 and n.module is not None
            names.add(n.module)
    return sorted(names)


def main():
    prior_freeze=pin(OLD/'ENTRY-SOURCE2-DIAGNOSTIC-FREEZE-v2.json')
    assert prior_freeze['sha256']=='09607fb5a47cd6813933fb5a315564a8172d135f4a3176c5d64772c0121040e3'
    old=json.loads(exact(prior_freeze).decode('utf-8'))
    prior=json.loads(exact(old['preparation']).decode('utf-8'))
    old_inputs=json.loads(exact(old['inputs']).decode('utf-8'))
    for p in old['harness'].values():exact(p)
    pause_path=HERE/'ENTRY-SOURCE-PAUSE-v3.json'
    pause_pin=pin(pause_path)
    assert pause_pin['sha256']=='225e8baf3aea76240e934eb1f80ad85478ba404a1e38a0a26cba5d65bd11973a'
    pause=json.loads(exact(pause_pin).decode('utf-8'))
    names=dict(kernel='preflight_entry_kernel_v3',owner_ops='preflight_owner_ops_v3',
               file_view='preflight_file_view_v3',codec='role_ledger_codec_v4')
    sources={}
    for role,p in pause['source_module_map'].items():
        actual=pin(ROOT/p['path'])
        assert actual['bytes']==p['bytes'] and actual['sha256']==p['sha256'] and p['module']==names[role]
        sources[names[role]]=actual
    p=pause['captured_dependency'];actual=pin(ROOT/p['path'])
    assert actual['bytes']==55497 and actual['sha256']==p['sha256']=='c0b3c5a689e72803487c9c3504513bc2bc0e4a4466b91128393fdbc4436f5b5e'
    sources[names['codec']]=actual
    helpers=[]
    for role in ('codec','owner_ops','file_view'):
        name=names[role];p=sources[name]
        helpers.append(dict(module=name,fictional_path='D:\\EntrySynthetic3\\helpers\\'+name+'.py',
                            bytes=p['bytes'],sha256=p['sha256'],source_pin=p,
                            declared_dependencies=dependencies(p['path'])))
    metadata=dict(old_inputs['metadata']);metadata['fictional_path']='D:\\EntrySynthetic3\\fixture-metadata.json'
    bulk=dict(old_inputs['bulk']);bulk['fictional_path']='D:\\EntrySynthetic3\\periodic-bulk.bin'
    body=bytes.fromhex(metadata['hex'])
    assert len(body)==metadata['bytes']==68 and hashlib.sha256(body).hexdigest()==metadata['sha256']
    assert json.loads(body)['native'] is False
    chunk=old_inputs['chunk'];assert chunk==1048576 and bulk['bytes']==2097169
    block=bytes(range(256))*256;h=hashlib.sha256();q,r=divmod(bulk['bytes'],len(block))
    for _ in range(q):h.update(block)
    h.update(block[:r]);assert h.hexdigest()==bulk['sha256']
    sizes=[x['bytes'] for x in helpers]+[metadata['bytes'],bulk['bytes']]
    n=b=m=None
    n=len(sizes);b=len(helpers);m=b
    q=sum(s//chunk+int(s%chunk!=0) for s in sizes)
    qb=sum(s//chunk+int(s%chunk!=0) for s in sizes[:b])
    geometry=dict(N=n,B=b,M=m,Q=q,R=q+16*sum(s>0 for s in sizes),C=6*n+q+16*sum(s>0 for s in sizes),
                  E=6*n+2*b+2*m+192,bootstrap_calls=5*b+qb,work_calls=5*n+q,terminal_calls=6*n+q,
                  known_bytes=sum(sizes),captured_bytes=sum(sizes[:-1]),early_bytes=sum(sizes[:b]),original_closes=n)
    assert geometry==old_inputs['baseline_geometry']
    inputs=dict(schema_version=3,scope='INVENTED_ACTUAL_SOURCE3_HELPER_ENTRY_TEST_INPUTS_ONLY',
                source_pause=pause_pin,source_map=sources,module_names=names,
                kernel_tcb=dict(pin=sources[names['kernel']],captured_as_helper=False),
                helpers=helpers,chunk=chunk,metadata=metadata,bulk=bulk,
                output_key='ENTRY_SYNTHETIC_SOURCE3_REGRESSIONS',baseline_geometry=geometry,
                prior_fixture_metadata_pin=old['inputs'],source1_replay=False,source2_replay=False,
                old_source_runtime_fallback=False,subject_imports=0,subject_runs=0,
                qualification=dict(native=False,physical=False,new84=False,real_first_entry=False))
    input_pin=save('ENTRY-SOURCE3-ACTUAL-HELPER-INPUTS-v1.json',inputs)
    support=exact(old['harness']['support']).decode('utf-8').replace('preflight_entry_kernel_v2','preflight_entry_kernel_v3')
    world=exact(old['harness']['world']).decode('utf-8').replace('entry_independent_test_support_v2','entry_independent_test_support_v3')
    regression=exact(old['harness']['regressions']).decode('utf-8').replace('entry_independent_test_support_v2','entry_independent_test_support_v3')
    assert functions(regression)==functions(exact(old['harness']['regressions']).decode('utf-8'))
    runner=exact(old['harness']['runner']).decode('utf-8')
    runner=runner.replace('Fresh Source2 worlds','Fresh Source3 worlds')
    runner=runner.replace('ENTRY-SOURCE2-DIAGNOSTIC-BINDING-v2.json','ENTRY-SOURCE3-REGRESSION-BINDING-v1.json')
    runner=runner.replace('ENTRY-SOURCE2-DIAGNOSTIC-ATTEMPT-v2.json','ENTRY-SOURCE3-REGRESSION-ATTEMPT-v1.json')
    runner=runner.replace('ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json','ENTRY-SOURCE3-REGRESSION-PROOF-v1.json')
    runner=runner.replace('AUTHORIZED_SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC','AUTHORIZED_SOURCE3_FIVE_REGRESSIONS_ONLY')
    runner=runner.replace('SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC','SOURCE3_FIVE_REGRESSIONS_ONLY')
    runner=runner.replace('source2','source3').replace('Source2','Source3').replace('SOURCE2','SOURCE3')
    runner=runner.replace('entry_independent_test_support_v2','entry_independent_test_support_v3')
    runner=runner.replace('entry_independent_world_v2','entry_independent_world_v3')
    runner=runner.replace('entry_initial_regressions_v3','entry_initial_regressions_v4')
    runner=runner.replace('source1_replayed=False)', 'source1_replayed=False,source2_replayed=False)')
    harness=dict(support=write_new('entry_independent_test_support_v3.py',support),
                 world=write_new('entry_independent_world_v3.py',world),
                 regressions=write_new('entry_initial_regressions_v4.py',regression),
                 runner=write_new('run_entry_source3_regressions_v1.py',runner))
    old_fn=functions(exact(old['harness']['runner']).decode('utf-8'));new_fn=functions(runner)
    assert old_fn.keys()==new_fn.keys()
    runner_changed=sorted(k for k in old_fn if old_fn[k]!=new_fn[k])
    assert runner_changed==['main']
    actualreview=pin(OLD/'ENTRY-SOURCE2-DIAGNOSTIC-INDEPENDENT-ACTUAL-REVIEW-v2.json')
    assert actualreview['sha256']=='973114a9d54861e9e7ba4441c4085d5d97362c5fd2a87276add2ce7b1a1e4c2e'
    scope=pin(OLD/'ENTRY-SOURCE3-CORRECTION-AUTHORING-SCOPE-v1.json')
    preparation=dict(schema_version=1,status='FROZEN_SOURCE3_UNCHANGED_FIVE_CHECKS_BEFORE_EXECUTION',
                     source_pause=pause_pin,source_map=sources,inputs=input_pin,harness=harness,
                     authoring_scope=scope,prior_five_check_freeze=prior_freeze,
                     actual_source2_review=actualreview,actual_source2_proof=pin(OLD/'ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json'),
                     methods=list(functions(regression)),all_five_method_ASTs_unchanged=True,
                     source_delta=pin(HERE/'ENTRY-SOURCE-CORRECTION-DELTA-v3.json'),
                     harness_deltas=dict(support='Exact kernel_v2->kernel_v3 source/default spelling only.',
                                         world='Exact trusted support_v2->support_v3 import only.',
                                         regressions='Exact trusted support_v2->support_v3 import only; five assertion ASTs unchanged.',
                                         runner_changed_functions=runner_changed,
                                         runner='Exact source3 phase paths/module spelling/map/auth caption only; no assertion/deadline/audit/failure-retention change.'),
                     actual_helper_bytes=geometry['early_bytes'],geometry=geometry,
                     kernel_pre_entry_tcb_bytes=sources[names['kernel']]['bytes'],
                     subject_imports=0,subject_tests=0,full_32_53='NOT_EXECUTED',native25='NOT_EXECUTED',
                     limitations=['Five-regression Source3 behavioral acceptance remains pending Root execution.',
                                  'Prior Source2 4PASS/1FAIL is preserved; no older source replay.',
                                  'Cooperative60s suite only, not a callback-free hard timeout.',
                                  'No native/physical/real-entry/full-roster/new84/resource/scientific qualification.'])
    prep=save('ENTRY-SOURCE3-REGRESSION-PREPARATION-v1.json',preparation)
    outline=save('ENTRY-SOURCE3-REGRESSION-BINDING-OUTLINE-v1.json',
                 dict(status='UNBOUND_NO_EXECUTION_AUTHORITY',deadline_seconds=60,methods=preparation['methods'],
                      execution_scope=None,source_pause=pause_pin,preparation=prep,inputs=input_pin,
                      source_map=sources,harness=harness))
    freeze=save('ENTRY-SOURCE3-REGRESSION-FREEZE-v1.json',
                dict(schema_version=1,status='FROZEN_BEFORE_FIRST_SOURCE3_IMPORT_OR_TEST',
                     source_pause=pause_pin,inputs=input_pin,preparation=prep,outline=outline,harness=harness,
                     author=pin(__file__),prior_five_check_freeze=prior_freeze,subject_imports=0,subject_runs=0))
    print(json.dumps(dict(freeze=freeze,preparation=prep,inputs=input_pin,harness=harness,geometry=geometry)))


if __name__=='__main__':
    main()
