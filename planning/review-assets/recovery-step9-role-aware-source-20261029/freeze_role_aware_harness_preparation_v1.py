"""Pin runnable harness preparation without reading/importing subject sources."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
P=H.parent/'recovery-step9-role-aware-producer-20261029'
S=H.parent/'recovery-step9-shared-owner-20261029'
I=H.parent/'recovery-step9-indexed-accounting-20261029'


def pin(p):
    raw=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def pub(name,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    with (H/name).open('xb') as f:f.write(raw)
    return pin(H/name)


def func(path,name):
    matches=[n for n in ast.walk(ast.parse(path.read_bytes())) if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(matches)==1,name
    return ast.dump(matches[0],include_attributes=False)


def main():
    names=('role_ledger_codec_v1','role_owner_v1','role_file_ports_v1','continue_role_verification_v1')
    harness={
        'legacy_adapter':pin(H/'role_aware_legacy_fixture_adapter_v1.py'),
        'same8_adapter':pin(H/'role_aware_same8_adapter_v1.py'),
        'codec_tests':pin(P/'role_ledger_independent_tests_v2.py'),
        'snapshot_validator':pin(S/'shared_owner_snapshot_validator_v1.py')}
    assert harness['codec_tests']['sha256']=='a3051f08375fd412d49a9a69ce180b65de69214500c787f9562a23cc3859beea'
    assert harness['snapshot_validator']['sha256']=='afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc'
    dependencies={
        'literal_corpus':pin(P/'ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json'),
        'literal_freeze':pin(P/'ROLE-AWARE-FORMAT-LITERAL-FREEZE-v2.json'),
        'literal_peer':pin(P/'ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v2.json'),
        'literal_acceptance':pin(P/'ROLE-AWARE-FORMAT-LITERAL-ACCEPTANCE-v2.json'),
        'format_schema':pin(P/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'),
        'fixtures':pin(S/'SHARED-OWNER-INTEGRATION-FIXTURES-v3.json'),
        'fixture_schema':pin(S/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json'),
        'legacy_observation_schema':pin(S/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'),
        'synthetic_cohort':pin(S/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'),
        'permitted_static_source_index':pin(I/'INDEXED-ACCOUNTING-INDEPENDENT-SOURCE-BINDING-v3.json')}
    fixtures=json.loads((S/'SHARED-OWNER-INTEGRATION-FIXTURES-v3.json').read_bytes())
    assert len(fixtures['cases'])==48
    for n in ('prepare_role_aware_legacy_adapter_v1.py','role_aware_legacy_fixture_adapter_v1.py',
              'prepare_role_aware_same8_adapter_v1.py','role_aware_same8_adapter_v1.py','run_role_aware_independent_v1.py'):
        ast.parse((H/n).read_bytes())
    # All 48 checks/relations remain the exact external JSON, not rewritten by
    # the adapter. Comparison and original identity/ref monitors are unchanged.
    unchanged=[]
    for n in ('compare','project','check_identity','normalize','check_token','run','_call'):
        if n=='_call':continue # Only packet transport schema/version is changed.
        assert func(S/'shared_owner_fixture_driver_v2.py',n)==func(H/'role_aware_legacy_fixture_adapter_v1.py',n),n
        unchanged.append(n)
    # Eight causal assertion bodies are untouched; only their shared capture
    # helper passes the genuine snapshot through the actual typed projector.
    old=ast.parse((S/'shared_owner_five_regressions_v2.py').read_bytes())
    new=ast.parse((H/'role_aware_same8_adapter_v1.py').read_bytes())
    old_tests={n.name:ast.dump(n,include_attributes=False) for n in ast.walk(old) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    new_tests={n.name:ast.dump(n,include_attributes=False) for n in ast.walk(new) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    assert old_tests==new_tests and len(old_tests)==8
    outline=pub('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v1.json',dict(schema_version=1,status='UNBOUND_PREPARATION_NOT_EXECUTION_BINDING',
        intended_binding_basename='ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v1.json',phase_choices=['CODEC_FIRST','LEGACY48_FIRST'],
        source_module_load_order=list(names),source_pins={n:None for n in names},
        source_paths={n:str(H/(n+'.py')) for n in names},source_scope=pin(P/'ROLE-AWARE-PRODUCER-SOURCE-SCOPE-v1.json'),
        execution_scope=None,source_pause=None,deadline_seconds=60,harness_pins=harness,dependencies=dependencies,
        actual_runner=pin(H/'run_role_aware_independent_v1.py'),
        bound_fields_only_after_root_go=['phase','exact all4source pins from coherent source pause','source_pause','execution_scope'],
        no_activation='The actual runner reads only the separately named final binding, never this outline. No subject import/run is authorized by this metadata.'))
    report=pub('ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v1.json',dict(schema_version=1,status='RUNNABLE_UNEXECUTED_HARNESS_PREPARED',
        outline=outline,harness_pins=harness,dependencies=dependencies,
        preparation_pins=[pin(H/n) for n in ['prepare_role_aware_legacy_adapter_v1.py','prepare_role_aware_same8_adapter_v1.py',
                                           'run_role_aware_independent_v1.py',Path(__file__).name]],
        static_checks=dict(harness_sources_parse=True,unchanged_legacy_driver_functions=unchanged,
                           unchanged_same8_assertion_methods=8,frozen_48_json_unchanged=48),
        adapters=dict(roles='Only software->captured_software and owner_metadata/artifact->captured_metadata; exact original role retained as legacy_role input fact.',
                      packet_transport='Exact b71 schema2,scope,status,11 keys and allfalse qualifiers. Original50ee 7-key journal/once-kind/ACK/8192/cutoff guards retained.',
                      snapshot='Actual type ProducerSnapshot from new owner -> actual same-source project_legacy -> actual immutable LegacySnapshot.to_dict -> strict unchanged50ee validator -> expected comparison.',
                      identities='Original Owner/Origin/Continuation/nonce/registry/loader/journal/early bytes/refs and original exception-token is assertions unchanged.',
                      cancellation='One real60s suite deadline includes bootstrap. Immutable negative projection may observe late synthetic clock without resampling/reset; original owner100/395/400 monitors remain strict.',
                      audit='ACTIVE source definitions/calls plus current exact subject filename stack frames cover ordinary source getters/error properties; no original/native/fs/network/import fallback.'),
        source_bytes_read_or_hashed=0,subject_imports=0,subject_runs=0,actual_toy_helper_execution=0,
        legacy_expected_rewrites=0,large_fixture_preparation=0,original_or_payload_operations=0,native_physical_operations=0,
        pending=['coherent4source pause pins','Native exact source/runner/adapter peer','root execution authorization and final binding','preserve exact first actual proof for each explicitly chosen phase'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=report,outline=outline,harness_pins=harness)))


if __name__=='__main__':main()
