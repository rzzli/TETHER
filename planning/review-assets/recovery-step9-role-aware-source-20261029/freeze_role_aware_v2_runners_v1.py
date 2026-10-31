"""Freeze new-source runners and accurate failure accounting, never test them."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
P=H.parent/'recovery-step9-role-aware-producer-20261029'


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def js(p):return json.loads(p.read_bytes())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)
def funcs(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}


def main():
    pause=pin(H/'ROLE-AWARE-PRODUCER-SOURCE-PAUSE-v2.json')
    assert pause['sha256']=='ddc92af0f11b94652ad90a34fbbcd4b428c8a01566dcf09e8ec750ead89fed6f'
    names=['role_ledger_codec_v2','role_owner_v2','role_file_ports_v2','continue_role_verification_v2']
    data=js(Path(pause['path']));assert data['own_module_order']==names and set(data['sources'])==set(names)
    source_pins={}
    for n in names:
        p=dict(data['sources'][n]);p['path']=str(Path(p['path']).resolve())
        assert Path(p['path'])==H/(n+'.py')
        source_pins[n]=p # Metadata only: do not open/read/import subject files.
    a=funcs(H/'run_role_aware_independent_v4.py');b=funcs(H/'run_role_aware_independent_v5.py')
    assert set(b)-set(a)=={'partial_codec_counts'} and [n for n in a if a[n]!=b[n]]==['main']
    c=funcs(H/'run_role_aware_extensions_v1.py');d=funcs(H/'run_role_aware_extensions_v2.py')
    assert set(c)==set(d) and [n for n in c if c[n]!=d[n]]==['main']
    assert pin(P/'role_ledger_independent_tests_v2.py')['sha256']=='a3051f08375fd412d49a9a69ce180b65de69214500c787f9562a23cc3859beea'
    peer=pin(H/'ROLE-AWARE-PRODUCER-CORRECTION-INDEPENDENT-REVIEW-v2.json')
    assert peer['sha256']=='2e3c90ab67d643d7fa96962e7f5a75982f9ac4ab08936732b32047e9685a26c7'
    def revised(old_name,runner_name,phase_version):
        v=js(H/old_name);v.update(status='EXPLICIT_V2_SOURCE_OUTLINE_NOT_EXECUTION_BINDING',source_module_load_order=names,
            source_pins=source_pins,source_paths={n:p['path'] for n,p in source_pins.items()},source_pause=pause,
            execution_scope=None,actual_runner=pin(H/runner_name),pending_current_root_correction_acceptance=None)
        dep=v['dependencies']
        if 'literal_peer' in dep:dep['preserved_literal_v2_peer']=dep.pop('literal_peer')
        if 'literal_acceptance' in dep:dep['preserved_literal_v2_acceptance']=dep.pop('literal_acceptance')
        dep.update(literal_corpus=pin(P/'ROLE-AWARE-FORMAT-LITERAL-CORPUS-v3.json'),
            literal_freeze=pin(P/'ROLE-AWARE-FORMAT-LITERAL-FREEZE-v3.json'),
            literal_contract=pin(P/'ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v3.json'),
            normative_oracle_choice=pin(P/'ROLE-AWARE-RESERVATION-ORACLE-CORRECTION-v3.json'),
            combined_source_oracle_peer=peer,
            first_v1_codec_failure=pin(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v4.json'))
        if phase_version==5:
            v['intended_phase_bindings']={p:str(H/('ROLE-AWARE-INDEPENDENT-'+p+'-SOURCE-BINDING-v5.json')) for p in ('CODEC_FIRST','LEGACY48_FIRST')}
        else:v['intended_binding_basename']='ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v2.json'
        return v
    outline=pub('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v5.json',revised('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v4.json','run_role_aware_independent_v5.py',5))
    extension_outline=pub('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v2.json',revised('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v1.json','run_role_aware_extensions_v2.py',2))
    for old_outline in ('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v4.json','ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v1.json'):
        for p in js(H/old_outline)['harness_pins'].values():assert pin(Path(p['path']))==p
    first=js(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v4.json')
    assert first['codec_forwarding']['facade_attempts']==83 and first['codec_forwarding']['actual_source_check_sites']==1288
    preparation=pub('ROLE-AWARE-V2-RUNNERS-PREPARATION-v1.json',dict(schema_version=1,status='EXPLICIT_V2_MAP_AND_ABORT_ACCOUNTING_FROZEN_UNEXECUTED',
        independent_runner=pin(H/'run_role_aware_independent_v5.py'),extension_runner=pin(H/'run_role_aware_extensions_v2.py'),
        independent_outline=outline,extension_outline=extension_outline,source_pause=pause,source_pins_metadata=source_pins,combined_peer=peer,
        author=pin(H/'prepare_role_aware_v2_source_runners_v1.py'),freeze_author=pin(Path(__file__).resolve()),
        preserved=[pin(H/n) for n in ('run_role_aware_independent_v4.py','run_role_aware_extensions_v1.py',
            'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v4.json','ROLE-AWARE-PRODUCER-EXTENSION-TEST-PREPARATION-v1.json',
            'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v4.json')],
        static_delta=dict(independent_added_helper='partial_codec_counts',only_changed_existing_functions=['main'],
            facade_source_loader_audit_and_identity_helpers_AST_equal=True,all_harness_tests_adapters_and_assertions_pins_equal=True,
            maps='Only four v2 source names are admitted. HARNESS-ONLY old role keys point to the corresponding actual v2 modules; no old module import/cache fallback.'),
        failure_accounting=dict(setup_import='Distinct status before conformance starts.',
            started_codec_abort='Distinct CODEC_CONFORMANCE_ABORTED status; retain live facade counters, never relabel as setup-only.',
            partial_test_counts='Observe only exact builtin counters in the exact pinned T.run traceback frame. Otherwise None with reason. Declared unique cases/methods do not prove executed coverage.',
            missing_method_results='None plus UNKNOWN reason when T.run does not return, never zero complete outcomes.',
            extensions='Distinct started/returned stage and aborted status; retained observations are not normalized into complete accounting.',
            preserved_known_first_v1_forwarding=first['codec_forwarding'],preserved_first_v1_completed_method_outcomes=None,
            preserved_first_v1_completed_method_reason='Aborted unittest exception formatting; unknown remainder. Owner negative finding remains static-only, no executed BEFORE claim.'),
        activity=dict(subject_sources_read_or_hashed=0,V2_subject_imports=0,V2_subject_tests=0,V1_subject_replays=0,oracle_changes_in_runner_preparation=0,
                      original_payload_native_physical_operations=0),
        pending=['Native narrow runner mapping/accounting peer','Root acceptance of combined correction','exclusive phase-specific execution bindings and Root go'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=preparation,independent_outline=outline,extension_outline=extension_outline,
        independent_runner=pin(H/'run_role_aware_independent_v5.py'),extension_runner=pin(H/'run_role_aware_extensions_v2.py'))))


if __name__=='__main__':main()
