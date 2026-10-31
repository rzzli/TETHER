"""Freeze the selected three-test/source-map correction using static data."""
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
def methods(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(p.read_bytes())) if isinstance(n,ast.FunctionDef) and n.name.startswith('test')}


def main():
    choice=pin(H/'ROLE-AWARE-REPRESENTABILITY-AND-OBSERVATION-CORRECTION-v4.json')
    assert choice['sha256']=='73d80d6fa424b5135d8519f7952b86797ea69465407781fe5ba80507b02a28e9'
    before=pin(H/'role_aware_producer_extension_tests_v1.py');assert before['sha256']=='a87ff334f2a4b6e03314a85d5960be1d3f6a6b709ba3095a100d14c5084d018f'
    after=pin(H/'role_aware_producer_extension_tests_v2.py');a=methods(Path(before['path']));b=methods(Path(after['path']))
    expected=['test01_captured_empty_bulk_empty_and_typed_no_bytes','test04_actual_packing_failure_preserves_canonical_facts','test07_small_real_multichunk_hash_only_stream_and_209_capture']
    assert set(a)==set(b) and len(a)==7 and [n for n in a if a[n]!=b[n]]==expected
    def strip_tests(p):
        tree=ast.parse(p.read_bytes())
        for n in ast.walk(tree):
            if isinstance(n,ast.FunctionDef) and n.name.startswith('test'):n.body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    assert strip_tests(Path(before['path']))==strip_tests(Path(after['path']))
    ast.parse((H/'run_role_aware_independent_v8.py').read_bytes());ast.parse((H/'run_role_aware_extensions_v5.py').read_bytes())
    pause=pin(H/'ROLE-AWARE-PRODUCER-SOURCE-PAUSE-v4.json')
    assert pause['sha256']=='a746e552d5fb6a2eef7c80d5a593a9f4a5a606456d4fae63acfb8905cb14e929'
    metadata=js(Path(pause['path']));names=['role_ledger_codec_v4','role_owner_v4','role_file_ports_v4','continue_role_verification_v4']
    assert metadata['own_module_order']==names and set(metadata['sources'])==set(names)
    src={n:dict(p,path=str(Path(p['path']).resolve())) for n,p in metadata['sources'].items()}
    assert src['role_ledger_codec_v4']['sha256']==js(H/'ROLE-AWARE-PRODUCER-SOURCE-PAUSE-v3.json')['sources']['role_ledger_codec_v3']['sha256']
    actual=pin(H/'ROLE-AWARE-EXTENSIONS-EXTENSIONS_FIRST-PROOF-v4.json');assert actual['sha256']=='ca8b142d6e9a96dcc7ea0518b3571e87617fda66953e3ae09830c2c276791e98'
    original=js(Path(actual['path']));assert original['methods']==13 and len(original['errors'])==3 and not original['failures']
    outlines=[]
    for old_name,new_name,runner,ext in [
        ('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v7.json','ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v8.json','run_role_aware_independent_v8.py',False),
        ('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v4.json','ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v5.json','run_role_aware_extensions_v5.py',True)]:
        v=js(H/old_name);v.update(status='CLOSED_SOURCE4_TEST2_OUTLINE_NOT_EXECUTION_BINDING',source_module_load_order=names,
            source_pins=src,source_paths={n:p['path'] for n,p in src.items()},source_pause=pause,execution_scope=None,actual_runner=pin(H/runner),
            next_execution='Root carries byte-identical codec3 pass; actual source4 Legacy is required, then corrected extensions after pass. No codec repeat or large preparation authorized.')
        if ext:
            v['intended_binding_basename']='ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v5.json';v['harness_pins']['extension_tests']=after
        else:v['intended_phase_bindings']={p:str(H/('ROLE-AWARE-INDEPENDENT-'+p+'-SOURCE-BINDING-v8.json')) for p in ('CODEC_FIRST','LEGACY48_FIRST')}
        for p in v['harness_pins'].values():assert pin(Path(p['path']))==p
        v['dependencies'].update(representability_root_choice=choice,retained_first_extensions=actual,
            native_extension_localization=pin(H/'ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v3.json'))
        outlines.append(pub(new_name,v))
    prep=pub('ROLE-AWARE-SOURCE4-TEST2-PREPARATION-v1.json',dict(schema_version=1,status='FINITE_THREE_TEST_CORRECTION_FROZEN_UNEXECUTED',
        root_choice=choice,source_pause=pause,source_pins_metadata=src,old_test=before,new_test=after,changed_test_methods=expected,
        unchanged_other_new_test_method_ASTs=4,all_supporting_helper_class_and_function_ASTs_unchanged=True,
        existing48_same8_indexed6_tests_validators_expectations_unchanged=True,
        independent_runner=pin(H/'run_role_aware_independent_v8.py'),extension_runner=pin(H/'run_role_aware_extensions_v5.py'),outlines=outlines,
        authors=[pin(H/'prepare_role_aware_extension_tests_v2.py'),pin(H/'prepare_role_aware_v4_source_runners_v1.py'),pin(Path(__file__).resolve())],
        preserved_actual_extensions=actual,preserved_legacy_pass=pin(H/'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v7.json'),
        carried_codec_body_identity='Codec4 SHA equals exact codec3 SHA; Root explicitly carries the prior pure codec pass, not a new execution claim.',
        harness_corrections=dict(tests01_and07='Capture actual FileRecordRef/FileState while owner ACTIVE before normal lifecycle; inspect held same canonical state read-only after finalization and explicitly expect FINALIZED_MISUSE on a new file_state request.',
            test04='Inspect genuine Source2 ProducerSnapshot and original MemoryError/diagnostic token identity, preserve freeze phase, require typed LEGACY_NOT_REPRESENTABLE, retain raw209/hash209/capture209, once-close/noeligible checks.'),
        normative_source_requirement='New-phase freeze is valid Source2 metadata but outside pinned47 legacy phase values. Projector must refuse before LegacySnapshot issuance; no phase renaming, dropping, validator widening, clock reset or finalized access relaxation.',
        prior_actual_limits='Old10 passing methods remain actual covered evidence. In errored01/07 only their executed prefixes are known; trailing held-state/storage assertions and notes were not executed. The prior13-method run is not relabeled pass.',
        planned_methods=13,planned_variant_counts_unchanged=True,actual_corrected_subject_imports=0,actual_corrected_test_runs=0,
        activity=dict(subject_sources_read_or_hashed=0,subject_imports=0,subject_runs=0,old_suite_replays=0,codec_repeats=0,large_preparation=0,
            original_payload_native_physical_operations=0),
        pending=['Native combined finite source4/three-method peer','Root fresh Legacy binding/scope and actual first run','Root extension binding/scope after Legacy pass'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,test=after,independent_runner=pin(H/'run_role_aware_independent_v8.py'),
        extension_runner=pin(H/'run_role_aware_extensions_v5.py'),outlines=outlines)))


if __name__=='__main__':main()
