"""Freeze finite entry32/53 harness DATA; never import/execute a subject.

Only exact retained new source/metadata is read. Tiny invented helper bytes
are parsed/hashed as data. The procedural4GB reference is reused by pin; no
large body, hashing, original path or model operation is performed here.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ASSETS=HERE.parent
SOURCE=ASSETS/'recovery-step9-entry-source3-20261030'
PREFLIGHT=ASSETS/'recovery-step9-production-preflight-20261029'
REFERENCE=ASSETS/'recovery-step9-role-aware-source-20261029'/'ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json'
INPUTS=HERE/'ENTRY-CONTRACT-SUITE-INPUTS-v1.json'
PREPARATION=HERE/'ENTRY-CONTRACT-SUITE-PREPARATION-v1.json'
OUTLINE=HERE/'ENTRY-CONTRACT-SUITE-BINDING-OUTLINE-v1.json'
FREEZE=HERE/'ENTRY-CONTRACT-SUITE-FREEZE-v1.json'
FAILURE=HERE/'ENTRY-CONTRACT-SUITE-PREPARATION-FAILURE-v1.json'


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact(path,sha):
    p=pin(path)
    if p['sha256']!=sha:raise RuntimeError('retained prerequisite mismatch: '+str(path))
    return p,json.loads(Path(path).read_bytes())


def save_new(path,value):
    with path.open('xb')as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode())
    return pin(path)


def geometry(fixtures,early,module_count):
    n=len(fixtures);q=sum((size+1048575)//1048576 for size,capture in fixtures)
    p=sum(size>0 for size,capture in fixtures)
    return dict(N=n,B=len(early),M=module_count,Q=q,R=q+16*p,C=6*n+q+16*p,E=6*n+2*len(early)+2*module_count+192,bootstrap_calls=5*len(early)+sum((size+1048575)//1048576 for size in early),work_calls=5*n+q,terminal_calls=6*n+q,known_bytes=sum(size for size,capture in fixtures),captured_bytes=sum(size for size,capture in fixtures if capture),early_bytes=sum(early),original_closes=n)


def tiny_module(module,path,body,size,dependencies):
    if len(body)>size-2:raise RuntimeError('tiny source declared size')
    raw=body+b'#'+b' '*(size-len(body)-2)+b'\n'
    tree=ast.parse(raw.decode())
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            if node.level:raise RuntimeError('closed tiny source imports only')
            imports.append(node.module)
    if sorted(set(imports))!=sorted(dependencies):raise RuntimeError('exact tiny source dependencies')
    return dict(module=module,fictional_path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),hex=raw.hex(),declared_dependencies=list(dependencies))


def main():
    if any(p.exists()for p in(INPUTS,PREPARATION,OUTLINE,FREEZE,FAILURE)):
        raise RuntimeError('preparation already retained; no overwrite')
    try:
        scope,scope_data=exact(SOURCE/'ENTRY-CONTRACT-SUITE-AUTHORING-SCOPE-v1.json','df44dee067272444230061107b8a6d8774f52c0f1b5b4da7576714e480c6fd66')
        case_contract,contract=exact(PREFLIGHT/'ENTRY-KERNEL-OWNEROPS-PRECODE-CASES-v1.json','cdfeaa338f387c18039818e7d414c9c13252ee916f872ff42e400da48012a95b')
        accepted,acceptance=exact(SOURCE/'ENTRY-SOURCE3-FIVE-REGRESSION-ROOT-ACCEPTANCE-v1.json','0d9c42a2f8c3575f4706ce43d189e56a680ed26eb9ef60737e9453d7b2bd4fb4')
        source_scope,source_authority=exact(ASSETS/'recovery-step9-entry-source2-20261030'/'ENTRY-SOURCE3-CORRECTION-AUTHORING-SCOPE-v1.json','92efd17643ecaf7ed0d303225fe9616d5fa921cce48c365a904a0b9d49381b0b')
        manifest,staged=exact(PREFLIGHT/'STAGED-NEW84-SELECTION-MANIFEST-v1.json','2aad403db06d5388bf9a8e8fb674bf2a26f8ad90a437f2db51e1e19f17ff80a9')
        reference,ref=exact(REFERENCE,'1a3e47ec28b1f96c4ac0d5c9c9eb7c2f13288cf5a6df4e3c4f6853d07a56aa03')
        baseline_pin,baseline=exact(SOURCE/'ENTRY-SOURCE3-ACTUAL-HELPER-INPUTS-v1.json','a528efaa504524de6dc2223526e4d7b4d5218689570a5cfdad108b8039bd4bf1')
        if scope_data['status']!='ROOT_AUTHORIZED_ENTRY32_53_HARNESS_AUTHORING_ONLY':raise RuntimeError('authoring scope only')
        if acceptance['qualification']['complete_entry_gate']is not False or staged['admission']is not False:raise RuntimeError('no runtime admission inheritance')
        source_map=baseline['source_map']
        for expected in source_map.values():
            if pin(expected['path'])!=expected:raise RuntimeError('changed exact Source3 input')
        pause=baseline['source_pause']
        if pin(pause['path'])!=pause:raise RuntimeError('Source3 pause unchanged')
        if pause['sha256']!=scope_data['source_pause_sha256']or pause['sha256']!=acceptance['source_pause']['sha256']or pause['bytes']!=acceptance['source_pause']['bytes']or Path(pause['path']).resolve()!=Path(acceptance['source_pause']['path']).resolve():raise RuntimeError('accepted parent Source3 pause anchor')
        source4=ASSETS/'recovery-step9-role-aware-source-20261029'
        historical,historical_data=exact(source4/'ROLE-AWARE-PRODUCER-SMALL-GATE-ACCEPTANCE-v4.json','096f5781b0c5d92208fcbd6a0da21528939f668be62ccd573c433ae7517b7445')
        legacy=pin(source4/'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v8.json')
        extensions=pin(source4/'ROLE-AWARE-EXTENSIONS-EXTENSIONS_FIRST-PROOF-v5.json')
        if legacy['bytes']!=9690627 or legacy['sha256']!='f53e3db06b69337d2a8ce4b34fe851dab1338806bfe9aba0bba7b89261f22c6f':raise RuntimeError('retained historical legacy48/SAME8 bytes')
        if extensions['bytes']!=66266 or extensions['sha256']!='cd0caf2efce5e8899c6275d1f82df7c0a63b4f7713e4e5235f48e2ee0bf125ae':raise RuntimeError('retained historical indexed6 extension bytes')
        groups=historical_data['separate_test_groups']
        if groups['genuine_legacy']['main_histories_matched']!=48 or groups['genuine_legacy']['focused_methods']!=8 or groups['genuine_extensions']['old_indexed_methods']!=6:raise RuntimeError('historical accepted groups')
        if historical_data['genuine_legacy_pass_sha256']!=legacy['sha256']or historical_data['genuine_extensions_pass_sha256']!=extensions['sha256']:raise RuntimeError('historical proof parent links')
        historical_retained=True
        harness={name:pin(path)for name,path in dict(runner=HERE/'run_entry_contract_suite_v1.py',cases=HERE/'entry_contract_cases_v1.py',support=SOURCE/'entry_independent_test_support_v3.py',world=SOURCE/'entry_independent_world_v3.py').items()}
        for value in harness.values():ast.parse(Path(value['path']).read_text(encoding='utf-8'))
        cases_tree=ast.parse(Path(harness['cases']['path']).read_text(encoding='utf-8'))
        declared={n.name for n in cases_tree.body if isinstance(n,ast.FunctionDef)and n.name.startswith('E')}
        if declared!={f'E{i:02d}'for i in range(1,33)}:raise RuntimeError('exact32 test functions')
        branches=[]
        for row in contract['cases']:
            case=row['id']
            for variant in contract['branch_expansion'].get(case,[None]):
                coverage='GENUINE_SOURCE_RUNTIME'
                if case=='E08':coverage='PARTIAL_RUNTIME_DEFERRED_MANIFEST_POLICY'
                elif case=='E16'and variant!='foreign_attach':coverage='PARTIAL_RUNTIME_DEFERRED_HISTORICAL_REFERENCE'
                elif case=='E29':coverage='STATIC_METADATA_ONLY'
                elif case=='E30':coverage='GENUINE_RUNTIME_PLUS_STATIC_LINEAGE'
                elif case=='E32':coverage='CONDITIONAL_GENUINE_PROCEDURAL_LARGE_STREAM'
                branches.append(dict(case=case,variant=variant,branch=case if variant is None else case+'/'+variant,coverage_class=coverage))
        if len(branches)!=53 or len({r['branch']for r in branches})!=53:raise RuntimeError('exact53 ordered branch expansion')
        toy=[tiny_module('entry_extra_leaf_v1',r'D:\EntryContractSynthetic\entry_extra_leaf_v1.py',b'def marker():\n    return 17\n',58,()),tiny_module('entry_extra_entry_v1',r'D:\EntryContractSynthetic\entry_extra_entry_v1.py',b'from entry_extra_leaf_v1 import marker\n\ndef run():\n    return marker()+1\n',83,('entry_extra_leaf_v1',))]
        helpers=[r['bytes']for r in baseline['helpers']]
        fixtures=[(n,True)for n in helpers]+[(baseline['metadata']['bytes'],True),(baseline['bulk']['bytes'],False)]
        if geometry(fixtures,helpers,3)!=baseline['baseline_geometry']:raise RuntimeError('independent complete prefix geometry')
        toy_geometry=geometry([(n,True)for n in helpers+[58,83]]+fixtures[-2:],helpers+[58,83],5)
        expected_toy=dict(N=7,B=5,M=5,Q=9,R=121,C=163,E=254,bootstrap_calls=30,work_calls=44,terminal_calls=51,known_bytes=2196378,captured_bytes=99209,early_bytes=99141,original_closes=7)
        if toy_geometry!=expected_toy:raise RuntimeError('exact actual-plus-toy geometry')
        large_size=3991999872;large_digest=ref['checkpoint_sha256'][str(large_size)]
        if large_digest!='5321e7c0efc028f133e7a6690e5c5bdf0344dded80904eb416fddb7ed0c2b1fb':raise RuntimeError('pinned procedural reference checkpoint')
        large=geometry([(n,True)for n in helpers]+[(baseline['metadata']['bytes'],True),(large_size,False)],helpers,3)
        expected_large=dict(N=5,B=3,M=3,Q=3812,R=3892,C=3922,E=234,bootstrap_calls=18,work_calls=3837,terminal_calls=3842,known_bytes=3992098940,captured_bytes=99068,early_bytes=99000,original_closes=5)
        if large!=expected_large:raise RuntimeError('exact independently derived large geometry')
        old_modules={'role_owner_v4','role_file_ports_v4','continue_role_verification_v4','shared_owner_v3'}
        imports={}
        for name,value in source_map.items():
            tree=ast.parse(Path(value['path']).read_text(encoding='utf-8'));found=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):found.update(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom):found.add(node.module)
            imports[name]=sorted(found)
        if any(old_modules&set(v)for v in imports.values()):raise RuntimeError('old owner import exclusion')
        planned=[dict(resource_id=r['resource_id'],state=r['state'],sha256=None,reason=r['null_reason'])for r in staged['resources']if r.get('state')in('PLANNED_SOURCE','UNBUILT','UNRESOLVED')and r.get('resource_id')not in('PLANNED_ENTRY_KERNEL','PLANNED_OWNER_OPS','PLANNED_FILE_VIEW')and r.get('actual_sha256')is None and r.get('null_reason')]
        if not planned:raise RuntimeError('explicit planned/unbuilt metadata')
        retained_baselines=[accepted,pin(ASSETS/'recovery-step9-entry-source-20261029'/'ENTRY-SOURCE1-SMOKE-PROOF-v1.json'),pin(ASSETS/'recovery-step9-entry-source2-20261030'/'ENTRY-SOURCE2-DIAGNOSTIC-PROOF-v2.json')]
        enriched=dict(baseline)
        enriched.update(schema_version=1,scope='ENTRY32_53_FROZEN_TEST_INPUTS_NO_PRODUCER_AUTHORITY',baseline_input=baseline_pin,branches=branches,toy_modules=toy,toy_geometry=toy_geometry,toy_expected_result=18,staged_4GB_digest=large_digest,large_geometry=large,joint_physical_call_warning=19079,large_reference=reference,static_metadata=dict(planned_unbuilt_nodes=planned,source_authoring_authorized=source_authority['status']=='ROOT_AUTHORIZED_MINIMAL_SOURCE3_AUTHORING_ONLY',runtime_admission_authorized=False,actual_source_imports_exclude_old_owner=True,historical_baselines_retained=historical_retained,historical_baseline_pins=[historical,legacy,extensions],historical_baseline_scope='Accepted Source4 legacy48/SAME8/indexed6 metadata and proof hashes retained; no proof body parse, source import or replay.',source_import_AST=imports,provenance=[manifest,source_scope,accepted,*retained_baselines[1:],historical,legacy,extensions],authored_source3_pins={name:value for name,value in source_map.items()if name!='role_ledger_codec_v4'},retained_plan_scope='Original staged declarations retained as metadata; authored Source3 files are pinned separately, not called unbuilt.',semantics='HARNESS_METADATA_ONLY_NOT_PRODUCER_OR_NATIVE_AUTHORITY'),large_stream_execution_authorized=False)
        ip=save_new(INPUTS,enriched)
        data_checks=['exact retained prerequisites/source/harness pins with accepted baseline anchor','32 actual case functions and53 frozen ordered branches','unchanged Source3 full99000B helper prefix geometry','two actual AST-only toy blobs58/83 with closed dependency','pinned procedural4GB reference and independent numeric geometry','staged/unbuilt null reasons plus explicit source AST exclusion','accepted historical legacy48/SAME8/indexed6 parent and unchanged proof byte hashes']
        preparation=dict(schema_version=1,status='FROZEN_ENTRY32_53_PREPARATION_NO_SUBJECT_RUN',authoring_scope=scope,source_pause=pause,source_map=source_map,harness=harness,preparer=pin(__file__),inputs=ip,case_contract=case_contract,accepted_five_regressions=accepted,large_reference=reference,declared_named_controls=32,declared_branches=53,data_only_checks=dict(passed=7,checks=data_checks),execution_design='One prospective original60s cooperative timer incl setup, runtime and per-world evidence copies. Final proof write is outside reported elapsed/unmeasured. Root explicitly selects the large-stream boolean; no execution authority follows from preparation.',retention='First action/source error, cleanup/evidence errors, first wrapper snapshot and cached source final remain separate; actual immutable snapshot256B rows and latest registered bank rows persist separately. Missing registration/partial captures explicit, no body hex.',subject_imports=0,subject_runs=0,full_entry_gate=False,native25='NOT_EXECUTED',qualification=False)
        pp=save_new(PREPARATION,preparation)
        outline=dict(schema_version=1,status='ROOT_BINDING_REQUIRED_NOT_EXECUTABLE',required_execution_status='AUTHORIZED_SOURCE3_ENTRY32_53_SUITE_ONCE',deadline_seconds=60,allow_large_stream=None,allow_large_stream_reason='Root must explicitly choose bool; preparation alone never enables4GB streaming',execution_scope=None,preparation=pp,inputs=ip,source_pause=pause,source_map=source_map,harness=harness,freeze=dict(path=str(FREEZE.resolve()),bytes=None,sha256=None,reason='Root binding fills final freeze pin after acyclic preparation'),consumed_paths=[str((HERE/n).resolve())for n in('ENTRY-CONTRACT-SUITE-ATTEMPT-v1.json','ENTRY-CONTRACT-SUITE-PROOF-v1.json','ENTRY-CONTRACT-SUITE-ARTIFACTS-v1')],deferred_policy='E08 and the two E16 historical references remain DEFERRED after limited real checks; E29 static separately; no full entry acceptance from expected defer.')
        op=save_new(OUTLINE,outline)
        frozen=dict(schema_version=1,status='FROZEN_ENTRY32_53_PREPARATION_BEFORE_SUBJECT_EXECUTION',authoring_scope=scope,source_pause=pause,source_map=source_map,harness=harness,preparer=pin(__file__),inputs=ip,preparation=pp,outline=op,case_contract=case_contract,large_reference=reference,named_controls=32,ordered_branches=53,subject_imports=0,subject_runs=0,qualification=False)
        fp=save_new(FREEZE,frozen)
        print(json.dumps(dict(inputs=ip,preparation=pp,freeze=fp)))
    except BaseException as error:
        if not FAILURE.exists():save_new(FAILURE,dict(status='METADATA_PREPARATION_FAILED_NO_SUBJECT_IMPORT',type=type(error).__name__,args=[x if type(x)is str else type(x).__name__ for x in error.args],subject_imports=0,subject_runs=0))
        raise


if __name__=='__main__':main()
