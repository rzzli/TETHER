"""Mechanical adapter2/fresh-path runners on SAME source3; no execution."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def js(p):return json.loads(p.read_bytes())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)


def main():
    adapter=pin(H/'role_aware_legacy_fixture_adapter_v2.py')
    assert adapter['sha256']=='b0f8cbf326f05c9b868b26fbac2eaee5bdd9ae78fdcc15d1da848d2822abff4f'
    choice=pin(H/'ROLE-AWARE-PACKET-ALIAS-HARNESS-CORRECTION-v2.json')
    assert choice['sha256']=='02bac72d6f9d45c49ddb88cd3b4d97ece4fd24eba6a6f0d72ab39f239f2a3afa'
    old=(H/'run_role_aware_independent_v6.py').read_bytes()
    assert hashlib.sha256(old).hexdigest()=='1c2a9e5a9dbe372e25d6537f6714276b1f2100169e61284fda1e6b152f636018'
    text=old.decode().replace('role_aware_independent_legacy_adapter_v1','role_aware_independent_legacy_adapter_v2')
    text=text.replace('-SOURCE-BINDING-v6.json','-SOURCE-BINDING-v7.json').replace("+'-PROOF-v6.json'","+'-PROOF-v7.json'").replace("+'-ATTEMPT-v6.json'","+'-ATTEMPT-v7.json'").replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v6.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v7.json')
    ast.parse(text)
    with (H/'run_role_aware_independent_v7.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    back=text.replace('role_aware_independent_legacy_adapter_v2','role_aware_independent_legacy_adapter_v1')
    back=back.replace('-SOURCE-BINDING-v7.json','-SOURCE-BINDING-v6.json').replace("+'-PROOF-v7.json'","+'-PROOF-v6.json'").replace("+'-ATTEMPT-v7.json'","+'-ATTEMPT-v6.json'").replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v7.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v6.json')
    assert back.encode()==old
    old_ext=(H/'run_role_aware_extensions_v3.py').read_bytes()
    assert hashlib.sha256(old_ext).hexdigest()=='29b1511874f8b83aec68b872051ce8fa289c723939ca9032609f897a86f71073'
    text=old_ext.decode().replace('role_aware_independent_legacy_adapter_v1','role_aware_independent_legacy_adapter_v2')
    text=text.replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v3.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v4.json').replace("+'-PROOF-v3.json'","+'-PROOF-v4.json'").replace("+'-ATTEMPT-v3.json'","+'-ATTEMPT-v4.json'").replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v3.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v4.json')
    ast.parse(text)
    with (H/'run_role_aware_extensions_v4.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    back=text.replace('role_aware_independent_legacy_adapter_v2','role_aware_independent_legacy_adapter_v1')
    back=back.replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v4.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v3.json').replace("+'-PROOF-v4.json'","+'-PROOF-v3.json'").replace("+'-ATTEMPT-v4.json'","+'-ATTEMPT-v3.json'").replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v4.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v3.json')
    assert back.encode()==old_ext
    previous=js(H/'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-SOURCE-BINDING-v6.json')
    names=['role_ledger_codec_v3','role_owner_v3','role_file_ports_v3','continue_role_verification_v3']
    assert previous['source_module_load_order']==names and set(previous['source_pins'])==set(names)
    codec_pass=pin(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v6.json')
    codec=js(Path(codec_pass['path']));assert codec['status']=='PASS' and codec['methods']==4 and codec['codec_forwarding']['facade_attempts']==387
    legacy_failure=pin(H/'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v6.json')
    assert legacy_failure['sha256']=='dc02853ad550319d50c8361aa073aa0d4ba4ee8577d3b2bc99dc6bf318565a84'
    outlines=[]
    for old_name,new_name,runner,extension in [
        ('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v6.json','ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v7.json','run_role_aware_independent_v7.py',False),
        ('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v3.json','ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v4.json','run_role_aware_extensions_v4.py',True)]:
        v=js(H/old_name);v.update(status='SAME_SOURCE3_ADAPTER2_OUTLINE_NOT_EXECUTION_BINDING',
            source_module_load_order=names,source_pins=previous['source_pins'],source_paths={n:p['path'] for n,p in previous['source_pins'].items()},
            source_pause=previous['source_pause'],execution_scope=None,actual_runner=pin(H/runner),
            next_execution='Corrected harness LEGACY48_FIRST only after Root scope/peer; existing codec pass remains valid and no codec repeat is authorized.')
        v['harness_pins']['legacy_adapter']=adapter
        for p in v['harness_pins'].values():assert pin(Path(p['path']))==p
        if extension:v['intended_binding_basename']='ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v4.json'
        else:v['intended_phase_bindings']={p:str(H/('ROLE-AWARE-INDEPENDENT-'+p+'-SOURCE-BINDING-v7.json')) for p in ('CODEC_FIRST','LEGACY48_FIRST')}
        v['dependencies'].update(packet_alias_root_choice=choice,packet_alias_adapter_delta=pin(H/'ROLE-AWARE-PACKET-ALIAS-ADAPTER-DELTA-v2.json'),
            retained_source3_codec_pass=codec_pass,retained_first_legacy_failure=legacy_failure,
            independent_packet_guard_localization=pin(H/'ROLE-AWARE-LEGACY-PACKET-GUARD-INDEPENDENT-REVIEW-v1.json'),
            native_packet_guard_localization=pin(H/'ROLE-AWARE-LEGACY-FIRST-INDEPENDENT-LOCALIZATION-v3.json'))
        outlines.append(pub(new_name,v))
    prep=pub('ROLE-AWARE-ADAPTER2-RUNNERS-PREPARATION-v1.json',dict(schema_version=1,status='SAME_SOURCE3_ADAPTER2_MECHANICAL_RUNNERS_FROZEN_UNEXECUTED',
        independent_runner=pin(H/'run_role_aware_independent_v7.py'),extension_runner=pin(H/'run_role_aware_extensions_v4.py'),outlines=outlines,
        adapter=adapter,root_choice=choice,adapter_delta=pin(H/'ROLE-AWARE-PACKET-ALIAS-ADAPTER-DELTA-v2.json'),author=pin(Path(__file__).resolve()),
        reverse_text_equality=True,source_map_unchanged=previous['source_pins'],source_pause=previous['source_pause'],
        preserved_codec_pass=codec_pass,preserved_legacy_failure=legacy_failure,
        preserved_runners=[pin(H/'run_role_aware_independent_v6.py'),pin(H/'run_role_aware_extensions_v3.py')],
        invariant='Only the adapter module-load identity/pin and fresh binding/attempt/proof paths change. Source3 names/code, frozen tests/corpus/48 expectations, same8/indexed6/extension assertions, original clocks/deadline/audit/identity and abort accounting are unchanged.',
        next='Native finite alias/map peer, Root exclusive corrected Legacy binding/scope, then one actual Legacy run. No codec repeat; extensions and large remain held.',
        activity=dict(subject_sources_read_or_hashed=0,subject_imports=0,subject_runs=0,codec_repeats=0,legacy_replays=0,
                      oracle_changes=0,original_payload_native_physical_operations=0),
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,independent_runner=pin(H/'run_role_aware_independent_v7.py'),
        extension_runner=pin(H/'run_role_aware_extensions_v4.py'),outlines=outlines)))


if __name__=='__main__':main()
