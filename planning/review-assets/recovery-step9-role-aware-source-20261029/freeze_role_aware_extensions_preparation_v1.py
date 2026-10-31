"""Freeze executable test preparation; never import/run subject or tests."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
OLD=H.parent/'recovery-step9-production-preflight-20261029'/'indexed_accounting_controls_v2.py'


def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)
def assertions(path):
    tree=ast.parse(path.read_bytes());out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Assert):out.append(ast.dump(n,include_attributes=False))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id in ('self','test') and n.func.attr.startswith(('assert','fail')):
            out.append(ast.dump(n,include_attributes=False))
    return out


def main():
    assert pin(OLD)['sha256']=='d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b'
    assert assertions(OLD)==assertions(H/'role_aware_indexed6_adapter_v1.py')
    own={}
    for name in ('role_aware_indexed6_adapter_v1.py','role_aware_producer_extension_tests_v1.py','run_role_aware_extensions_v1.py'):
        tree=ast.parse((H/name).read_bytes())
        own[name]=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test')]
    assert len(own['role_aware_indexed6_adapter_v1.py'])==6
    assert len(own['role_aware_producer_extension_tests_v1.py'])==7
    assert not own['run_role_aware_extensions_v1.py']
    def definitions(p):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    a=definitions(H/'run_role_aware_independent_v3.py');b=definitions(H/'run_role_aware_extensions_v1.py')
    assert set(a)==set(b) and [n for n in a if a[n]!=b[n]]==['main']
    # Independent reference over the exact small periodic bytes; no body or
    # source/model/old payload is read. This second small reference pass checks
    # the literal first prepared by a separate8192*256+17 seed recipe command.
    h=hashlib.sha256();seed=bytes(range(256));block=seed*256;remaining=2097169
    while remaining:
        n=min(remaining,len(block));h.update(memoryview(block)[:n]);remaining-=n
    assert h.hexdigest()=='6f8b1421035dcde6d517143914932e7996c17ae9a6c30042b1142b1b8b5f0557'
    recipe=pub('ROLE-AWARE-SMALL-VIRTUAL-STREAM-RECIPE-v1.json',dict(schema_version=1,status='SMALL_SYNTHETIC_PREIMPLEMENTATION_REFERENCE',
        bulk_bytes=2097169,bulk_sha256=h.hexdigest(),recipe='periodic bytes00..ff, reset offset0 perfile;8192 complete256B periods plus first17 bytes',
        actual_delivery='256B seed then real source buffer_write_slice/copy_within doubling; no wholebulk body or1MiB delivery bytes',
        captured_bytes=209,total_known_and_hashed_bytes=2097378,chunk=1048576,files=4,modules=2,early_files=2,
        Q=6,R=70,C=94,E=224,expected_actual_reads=6,expected_actual_original7_calls=30,candidate_calls=26,terminal_calls=30,owned_closures=4,
        query_bytes=32872,capture_bytes=209,large216_file_preparation=False,
        reference_computations_before_source=2,bytes_per_reference_computation=2097169,subject_imports=0,subject_runs=0))
    old_outline=json.loads((H/'ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v3.json').read_bytes())
    old_outline.update(status='UNBOUND_EXTENSIONS_PREPARATION_NOT_EXECUTION_BINDING',
        intended_binding_basename='ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v1.json',phase_choices=['EXTENSIONS_FIRST'],
        actual_runner=pin(H/'run_role_aware_extensions_v1.py'))
    old_outline['harness_pins'].update(indexed6_adapter=pin(H/'role_aware_indexed6_adapter_v1.py'),extension_tests=pin(H/'role_aware_producer_extension_tests_v1.py'))
    old_outline['dependencies'].update(indexed_precode_test_source=pin(OLD),small_stream_recipe=recipe,
        preserved_runner3_peer=pin(H/'ROLE-AWARE-RUNNER-INDEPENDENT-STATIC-REVIEW-v3.json'))
    outline=pub('ROLE-AWARE-EXTENSIONS-BINDING-OUTLINE-v1.json',old_outline)
    prep=pub('ROLE-AWARE-PRODUCER-EXTENSION-TEST-PREPARATION-v1.json',dict(schema_version=1,status='ACTUAL_MODULE_TESTS_FROZEN_UNEXECUTED',
        outline=outline,small_stream_recipe=recipe,
        pins=[pin(H/n) for n in ('role_aware_indexed6_adapter_v1.py','role_aware_producer_extension_tests_v1.py',
            'run_role_aware_extensions_v1.py','prepare_role_aware_indexed6_adapter_v1.py','prepare_role_aware_extensions_runner_v1.py',Path(__file__).name)],
        preserved_runner3=pin(H/'run_role_aware_independent_v3.py'),preserved_independent_preparation=pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v3.json'),
        permitted_static_source=pin(OLD),unchanged_precode_assertions=len(assertions(OLD)),
        method_names=own,planned_method_count=13,planned_indexed_methods=6,planned_extension_methods=7,
        finite_variants=dict(indexed_owner_worlds=13,extension_owner_worlds=11,raw_null_and_malformed_variants=2,error_axis_order_variants=2,
            diagnostic_outer_successful_operations=16384,diagnostic_nested_successful_entries=16384,
            diagnostic_successful_context_entries=32768,diagnostic_failed_contexts=2,
            diagnostic_stress_N=3,diagnostic_stress_E=218,diagnostic_stress_capacity=506,
            small_stream_reference_bytes=2097169,small_stream_actual_original_calls=30,small_stream_actual_reads=6,
            no_large_fixture_preparation=True),
        actual_counts_now=dict(subject_module_imports=0,subject_test_methods_run=0,actual_producer_owner_worlds=0,actual_virtual_original_dispatches=0),
        observations_not_preclaimed='Actual per-method/source/iterator/dispatch/check counts and first failures will be retained only after coherent4pause+root go. Planned counts do not claim executed coverage.',
        source_scope='Exact same four fresh modules. Generic harness roles only; no old owner construction/import, decoder brand, sourcecase selection, ready flags or ownercontext override.',
        controls=[
            'SAME6 real canonical CountingList hot accesses, raw-before-cache/quarantine/append-committed failures, healthy idempotent fold and unknown-versus-defined0; assertions unchanged.',
            'Captured empty bytes differ from hash-only NOT_REQUESTED; actual state/blobs/getter typed refusal, no bulk assembly.',
            'Actual canonical malformed object/NULL/COUNT0/error-definition slots survive later stop; independent error-definition/value delivery orders.',
            'Actual codec call-row packing interruption preserves source raw facts, original error and once-only cleanup; no eligible candidate/retry.',
            'Actual diagnostic guard borrow/release across16384 outer success operations/nested sharing, then original failure and formatter identity.',
            'Actual candidate/terminal issued objects and cached bytes; live consumer delegates real iterator and exhausts every fixed row/edge/pool byte; foreign genuine artifact refuses without advancing gates.',
            'Actual small1MiB-profile periodic stream with real hashlib,209 captured bytes, no bulk body retention, exact raw/counter/closure and same-context assertions.'
        ],
        timing='Separate cooperative60s extension suite from original test-runner started time; original source owners100/395/400 never reset. No hard callback-free hang bound or resource-fit guarantee.',
        activity=dict(subject_sources_read_or_hashed=0,subject_imports=0,subject_runs=0,large_fixture_preparation=0,original_payload_native_physical_operations=0),
        pending=['exact helper/source interface peer after coherent4pause','root execution scope+final binding','first actual result; preserve all failures and use named corrections only'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,outline=outline,small_recipe=recipe,
        indexed6=pin(H/'role_aware_indexed6_adapter_v1.py'),tests=pin(H/'role_aware_producer_extension_tests_v1.py'),runner=pin(H/'run_role_aware_extensions_v1.py'))))


if __name__=='__main__':main()
