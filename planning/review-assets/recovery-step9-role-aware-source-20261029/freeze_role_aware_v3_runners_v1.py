"""Freeze only mechanical module/path renaming, without source operations."""
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
    # Reverse exact textual mappings must restore the previous complete file.
    new=(H/'run_role_aware_independent_v6.py').read_text(encoding='utf-8')
    old=(H/'run_role_aware_independent_v5.py').read_text(encoding='utf-8')
    back=new
    for a,b in [('role_ledger_codec_v3','role_ledger_codec_v2'),('role_owner_v3','role_owner_v2'),
                ('role_file_ports_v3','role_file_ports_v2'),('continue_role_verification_v3','continue_role_verification_v2')]:back=back.replace(a,b)
    back=back.replace('-SOURCE-BINDING-v6.json','-SOURCE-BINDING-v5.json').replace("+'-PROOF-v6.json'","+'-PROOF-v5.json'").replace("+'-ATTEMPT-v6.json'","+'-ATTEMPT-v5.json'").replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v6.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v5.json')
    assert back==old;ast.parse(new)
    new_ext=(H/'run_role_aware_extensions_v3.py').read_text(encoding='utf-8');back=new_ext
    for a,b in [('role_ledger_codec_v3','role_ledger_codec_v2'),('role_owner_v3','role_owner_v2'),
                ('role_file_ports_v3','role_file_ports_v2'),('continue_role_verification_v3','continue_role_verification_v2')]:back=back.replace(a,b)
    back=back.replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v3.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v2.json').replace("+'-PROOF-v3.json'","+'-PROOF-v2.json'").replace("+'-ATTEMPT-v3.json'","+'-ATTEMPT-v2.json'").replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v3.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v2.json')
    assert back==(H/'run_role_aware_extensions_v2.py').read_text(encoding='utf-8');ast.parse(new_ext)
    names=['role_ledger_codec_v3','role_owner_v3','role_file_ports_v3','continue_role_verification_v3']
    tail=pin(H/'ROLE-AWARE-CODEC-DISJOINT-TAIL-PROOF-v1.json')
    assert tail['sha256']=='05582b847e3ca8625692979cefd41d098123c64733004d63a1cf4bf49f524c97'
    result=js(Path(tail['path']));assert result['diagnostic_complete'] and result['all_tail_outcomes_match'] and len(result['rows'])==125
    outlines=[]
    for old_name,new_name,runner,extension in [
        ('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v5.json','ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v6.json','run_role_aware_independent_v6.py',False),
        ('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v2.json','ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v3.json','run_role_aware_extensions_v3.py',True)]:
        v=js(H/old_name);v.update(status='UNBOUND_EXPLICIT_V3_SOURCE_MAP_NOT_EXECUTION_BINDING',source_module_load_order=names,
            source_pins={n:None for n in names},source_paths={n:str(H/(n+'.py')) for n in names},source_pause=None,execution_scope=None,
            pending_root_v3_correction_scope=None,actual_runner=pin(H/runner))
        if extension:v['intended_binding_basename']='ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v3.json'
        else:v['intended_phase_bindings']={p:str(H/('ROLE-AWARE-INDEPENDENT-'+p+'-SOURCE-BINDING-v6.json')) for p in ('CODEC_FIRST','LEGACY48_FIRST')}
        v['dependencies'].update(retained_v2_disjoint_tail=tail,
            retained_v2_first_codec=pin(H/'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v5.json'),
            retained_v2_failure_localization=pin(H/'ROLE-AWARE-CODEC-V2-FAILURE-LOCALIZATION-v1.json'))
        for p in v['harness_pins'].values():assert pin(Path(p['path']))==p
        outlines.append(pub(new_name,v))
    prep=pub('ROLE-AWARE-V3-RUNNERS-PREPARATION-v1.json',dict(schema_version=1,status='MECHANICAL_V3_MAP_ONLY_FROZEN_UNEXECUTED',
        independent_runner=pin(H/'run_role_aware_independent_v6.py'),extensions_runner=pin(H/'run_role_aware_extensions_v3.py'),outlines=outlines,
        preserved_runners=[pin(H/'run_role_aware_independent_v5.py'),pin(H/'run_role_aware_extensions_v2.py')],
        author=pin(H/'prepare_role_aware_v3_source_runners_v1.py'),freeze_author=pin(Path(__file__).resolve()),
        exact_reverse_text_equality=True,
        invariant='Only the four source module spellings and new binding/attempt/proof filenames change. Tests, corpusV3, adapters/assertions, deadline facade, audit, original identity checks and abort/count accounting remain byte-identical after reversing those spellings.',
        retained_actual_tail=tail,retained_tail_calls=125,retained_tail_mismatches=0,retained_tail_unknowns=0,
        root_correction='Only header count-cap order before module-repeat; codec reservation/shape semantics and frozen oracles unchanged. All4source imports get freshv3 names.',
        activity=dict(subject_sources_read_or_hashed=0,V3_subject_imports=0,V3_subject_tests=0,prior_source_replays=0,oracle_or_harness_logic_changes=0,
                      original_payload_native_physical_operations=0),
        pending=['coherent V3 source pause','Root finite source correction scope','Native narrow mechanical runner peer','exclusive phase-specific binding and Root execution'],
        execution_order='CODEC first; actual genuine legacy48/same8 immediately after a passing codec decision, then extensions after pass. Large remains held.',
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,independent_runner=pin(H/'run_role_aware_independent_v6.py'),
        extensions_runner=pin(H/'run_role_aware_extensions_v3.py'),outlines=outlines)))


if __name__=='__main__':main()
