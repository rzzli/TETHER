"""Freeze Source4 metadata/harness inputs; never import or execute a subject."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ASSETS=HERE.parent
POLICY=ASSETS/'recovery-step9-external-manifest-policy-20261030'
OLD=ASSETS/'recovery-step9-entry-contract-tests-20261030'
SOURCE4_PAUSE_SHA='c38df4b3133133805e7a13c30e2d65d21748e4c1ce1a320929c0871f05dfab67'
INPUTS=HERE/'ENTRY-E08-SUITE-INPUTS-v1.json'
PREPARATION=HERE/'ENTRY-E08-SUITE-PREPARATION-v1.json'
OUTLINE=HERE/'ENTRY-E08-SUITE-BINDING-OUTLINE-v1.json'
FREEZE=HERE/'ENTRY-E08-SUITE-FREEZE-v1.json'
FAILURE=HERE/'ENTRY-E08-SUITE-PREPARATION-FAILURE-v1.json'


def pin(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT):raise RuntimeError('review asset outside repository')
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact(path,digest):
    value=pin(path)
    if value['sha256']!=digest:raise RuntimeError('changed prerequisite: '+str(path))
    return value,json.loads(Path(path).read_bytes())


def save_new(path,value):
    with path.open('xb')as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode())
    return pin(path)


def geometry(sizes,captured,early,module_count):
    n=len(sizes);q=sum((size+1048575)//1048576 for size in sizes);positive=sum(size>0 for size in sizes)
    return dict(N=n,B=len(early),M=module_count,Q=q,R=q+16*positive,C=6*n+q+16*positive,
                E=6*n+2*len(early)+2*module_count+192,
                bootstrap_calls=5*len(early)+sum((size+1048575)//1048576 for size in early),
                work_calls=5*n+q,terminal_calls=6*n+q,known_bytes=sum(sizes),
                captured_bytes=sum(size for size,yes in zip(sizes,captured)if yes),
                early_bytes=sum(early),original_closes=n)


def main():
    if any(path.exists()for path in(INPUTS,PREPARATION,OUTLINE,FREEZE,FAILURE)):
        raise RuntimeError('preparation already retained; no overwrite')
    if SOURCE4_PAUSE_SHA is None:
        raise RuntimeError('authoring draft only: coherent Source4 pause not yet bound')
    try:
        scope,scope_data=exact(POLICY/'E08-ENTRY-SUCCESSOR-AUTHORING-SCOPE-v1.json',
                              '29f35d62699766b5a6eaf7aa00441af2410cff542a26a36c20b718dda3a47113')
        precode,precode_data=exact(POLICY/'E08-PRECODE-ROOT-ACCEPTANCE-v1.json',
                                  'a055dfb37924481a103b47c54a21423dff4ec70bbbf6a4f71919be3eec9f393a')
        precode_freeze,precode_frozen=exact(POLICY/'E08-POLICY-PRECODE-FREEZE-v1.json',
                                          '096efd94efe29ab2c9e5b65b3d9ccd3e12eabf375a94e0f4ddcdfb4c557f3fa0')
        for value in precode_frozen['pins'].values():
            actual=pin(value['path'])
            if actual['bytes']!=value['bytes']or actual['sha256']!=value['sha256']:
                raise RuntimeError('changed precode input: '+value['path'])
        corpus_pin,corpus=exact(POLICY/'E08-INDEPENDENT-LITERAL-CORPUS-v1.json',
                               'ea2fc0966d45f95e97e995e9477c89fe3d2c6d9f647c7ed7dfaf1710b8c25b4c')
        scenarios_pin,scenarios=exact(POLICY/'E08-GENUINE-INTEGRATION-PRECODE-SCENARIOS-v1.json',
                                     '95f6b3be183593d9ae154fce3ee15065a29143ae091bbbf59b9dc3dd3a6618ff')
        base_pin,base=exact(OLD/'ENTRY-CONTRACT-SUITE-INPUTS-v2.json',
                           '722636e395b69c9a19e64dee7c1e38843fcffebce090b40c84841ccc8df4840e')
        source_pause,pause=exact(HERE/'ENTRY-SOURCE-PAUSE-v4.json',SOURCE4_PAUSE_SHA)
        source_map={}
        names={kind:'preflight_'+stem+'_v4'for kind,stem in
               (('kernel','entry_kernel'),('owner_ops','owner_ops'),('file_view','file_view'))}
        names['codec']='role_ledger_codec_v4'
        for kind in ('kernel','owner_ops','file_view'):
            expected=pause['sources'][kind];actual=pin(expected['path'])
            if actual['bytes']!=expected['bytes']or actual['sha256']!=expected['sha256']:
                raise RuntimeError('paused Source4 file changed')
            source_map[names[kind]]=actual
        codec=pin(ASSETS/'recovery-step9-role-aware-source-20261029'/'role_ledger_codec_v4.py')
        if codec['sha256']!='c0b3c5a689e72803487c9c3504513bc2bc0e4a4466b91128393fdbc4436f5b5e':
            raise RuntimeError('exact pure codec4 changed')
        source_map[names['codec']]=codec
        harness={name:pin(HERE/filename)for name,filename in dict(
            runner='run_entry_policy_suite_v1.py',support='entry_independent_test_support_v4.py',
            world='entry_independent_world_v4.py',policy_tests='entry_e08_policy_tests_v1.py',
            corrections='entry_initial_regressions_source4_v1.py',causal='entry_contract_cases_source4_v1.py').items()}
        for value in {**source_map,**harness}.values():ast.parse(Path(value['path']).read_bytes())
        helpers=[]
        for old in base['helpers']:
            row=dict(old)
            module=old['module'].replace('preflight_owner_ops_v3','preflight_owner_ops_v4').replace('preflight_file_view_v3','preflight_file_view_v4')
            value=source_map[module]
            row.update(module=module,bytes=value['bytes'],sha256=value['sha256'],
                       fictional_path='D:\\EntrySynthetic4\\helpers\\'+module+'.py',
                       declared_dependencies=[name.replace('preflight_entry_kernel_v3','preflight_entry_kernel_v4')for name in old['declared_dependencies']])
            helpers.append(row)
        sizes=[row['bytes']for row in helpers]+[base['metadata']['bytes'],base['bulk']['bytes']]
        flags=[True,True,True,True,False];early=sizes[:3]
        normal=geometry(sizes,flags,early,3)
        toy=geometry(early+[58,83]+sizes[-2:],[True]*6+[False],early+[58,83],5)
        large=geometry(early+[base['metadata']['bytes'],3991999872],flags,early,3)
        if normal['early_bytes']!=sum(early)or normal['N']!=5 or large['C']>16384:
            raise RuntimeError('invalid actual helper geometry')
        corrections=('test01_valid_entry','test02_normal_captured_helpers_finish',
                     'test03_staged_scalar_has_no_cleanup_authority',
                     'test04_committed_scalar_survives_cache_boundary_failure',
                     'test05_stopped_close_normal_return_does_not_heal_cache')
        branches=[]
        for method in corrections:
            branches.append(dict(group='CORRECTIONS',case=method,variant=None,branch='CORRECTIONS/'+method,coverage_class='GENUINE_SOURCE_CORRECTION_REGRESSION'))
        for row in corpus['vectors']:
            branches.append(dict(group='LITERALS',case=row['id'],variant=None,branch='LITERALS/'+row['id'],coverage_class='GENUINE_CORE_POLICY_OUTCOME_NOT_FULL_ENTRY_SUCCESS'))
        for scenario in scenarios['scenarios']:
            for variant in scenario['branches']:
                branches.append(dict(group='INTEGRATION',case=scenario['id'],variant=variant,branch='INTEGRATION/'+scenario['id']+'/'+variant,coverage_class='GENUINE_E08_ENTRY_INTEGRATION'))
        prior_branches=[]
        for row in base['branches']:
            if row['case']=='E08'or row['case']=='E16'and row['variant']in('Source4_constructor','Source4_start_injected'):
                continue
            prior_branches.append(dict(row))
            branches.append(dict(group='CAUSAL',case=row['case'],variant=row['variant'],branch='CAUSAL/'+row['branch'],coverage_class=row['coverage_class']))
        counts={group:sum(row['group']==group for row in branches)for group in('CORRECTIONS','LITERALS','INTEGRATION','CAUSAL')}
        if counts!={'CORRECTIONS':5,'LITERALS':52,'INTEGRATION':15,'CAUSAL':50}or len({row['branch']for row in branches})!=122:
            raise RuntimeError('exact122 dispatch inventory')
        imports={}
        for name,value in source_map.items():
            found=[]
            for node in ast.walk(ast.parse(Path(value['path']).read_bytes())):
                if isinstance(node,ast.Import):found.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.ImportFrom):found.append(node.module)
            imports[name]=sorted(set(found))
        forbidden={'role_owner_v4','role_file_ports_v4','continue_role_verification_v4','preflight_entry_kernel_v3'}
        if any(forbidden&set(value)for value in imports.values()):raise RuntimeError('forbidden old owner/kernel import')
        metadata=dict(base['metadata']);metadata['fictional_path']='D:\\EntrySynthetic4\\fixture-metadata.json'
        bulk=dict(base['bulk']);bulk['fictional_path']='D:\\EntrySynthetic4\\periodic-bulk.bin'
        static=dict(base['static_metadata'])
        static.pop('authored_source3_pins',None)
        static.update(actual_source_imports_exclude_old_owner=True,source_import_AST=imports,
                      authored_source4_pins={key:value for key,value in source_map.items()if key!='role_ledger_codec_v4'})
        inputs=dict(base)
        inputs.update(schema_version=1,scope='SOURCE4_E08_122_FROZEN_INPUTS_NO_RUNTIME_AUTHORITY',
                      source_map=source_map,source_pause=source_pause,module_names=names,helpers=helpers,
                      metadata=metadata,bulk=bulk,baseline_geometry=normal,toy_geometry=toy,large_geometry=large,
                      static_metadata=static,branches=prior_branches,suite_branches=branches,literal_corpus=corpus_pin,
                      integration_scenarios=scenarios_pin,source3_base_inputs=base_pin,
                      kernel_pre_entry_tcb_bytes=source_map[names['kernel']]['bytes'],
                      selected_current_outputs='SOURCE4_SYNTHETIC_POLICY_CONTEXT_ONLY_NOT_PHYSICAL_ADMISSION')
        ip=save_new(INPUTS,inputs)
        preparation=dict(schema_version=1,status='FROZEN_SOURCE4_E08_122_PREPARATION_NO_SUBJECT_RUN',
                         authoring_scope=scope,precode_acceptance=precode,precode_freeze=precode_freeze,
                         source_pause=source_pause,source_map=source_map,harness=harness,preparer=pin(__file__),inputs=ip,
                         groups=counts,declared_dispatches=122,literal_corpus=corpus_pin,integration_scenarios=scenarios_pin,
                         actual_helper_prefix_bytes=normal['early_bytes'],kernel_pre_entry_tcb_bytes=source_map[names['kernel']]['bytes'],
                         normal_geometry=normal,toy_geometry=toy,large_geometry=large,
                         metadata_only_checks=['all fixed precode pins','actual paused source and helper bytes','52 immutable literal outcomes and15 scenario branches','5 correction names and50 unchanged causal branches','independent actual helper/normal/toy/large geometry','new-source AST import exclusion'],
                         execution_design='One prospective122-dispatch real60s cooperative timer; no automatic retry/cap lift. Per-world evidence included; finalproofwrite/startup excluded or unmeasured. Root explicitly selects procedural E32 stream.',
                         subject_imports=0,subject_runs=0,full_entry_gate=False,native25='NOT_EXECUTED',qualification=False)
        pp=save_new(PREPARATION,preparation)
        outline=dict(schema_version=1,status='ROOT_BINDING_REQUIRED_NOT_EXECUTABLE',required_execution_status='AUTHORIZED_SOURCE4_E08_122_SUITE_ONCE',
                     deadline_seconds=60,allow_large_stream=None,execution_scope=None,preparation=pp,inputs=ip,
                     source_pause=source_pause,source_map=source_map,harness=harness,
                     freeze=dict(path=str(FREEZE),bytes=None,sha256=None,reason='Root fills acyclic final freeze pin'),
                     consumed_paths=[str(HERE/name)for name in('ENTRY-E08-SUITE-ATTEMPT-v1.json','ENTRY-E08-SUITE-PROOF-v1.json','ENTRY-E08-SUITE-ARTIFACTS-v1')])
        op=save_new(OUTLINE,outline)
        frozen=dict(schema_version=1,status='FROZEN_SOURCE4_E08_122_BEFORE_SUBJECT_EXECUTION',
                    authoring_scope=scope,precode_acceptance=precode,precode_freeze=precode_freeze,source_pause=source_pause,
                    source_map=source_map,harness=harness,inputs=ip,preparation=pp,outline=op,preparer=pin(__file__),
                    declared_groups=counts,declared_dispatches=122,subject_imports=0,subject_runs=0,qualification=False)
        fp=save_new(FREEZE,frozen)
        print(json.dumps(dict(inputs=ip,preparation=pp,freeze=fp)))
    except BaseException as error:
        if not FAILURE.exists():
            save_new(FAILURE,dict(status='METADATA_PREPARATION_FAILED_NO_SUBJECT_IMPORT',type=type(error).__name__,
                                 args=[value if type(value)is str else type(value).__name__ for value in error.args],subject_imports=0,subject_runs=0))
        raise


if __name__=='__main__':
    main()
