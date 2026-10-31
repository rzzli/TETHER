"""Static preparation freeze only; no reviewed subject source operations."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pub(name,value):
    b=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    with (H/name).open('xb') as f:f.write(b)
    return pin(H/name)
def functions(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}

def main():
    assert pin(H/'run_role_aware_independent_v2.py')['sha256']=='0cad8bf8ed080a17842945086d9b3ff9c8ea93352ad6e62655417cfe1d87d79e'
    a=functions(H/'run_role_aware_independent_v2.py');b=functions(H/'run_role_aware_independent_v3.py')
    assert set(a)==set(b) and [k for k in a if a[k]!=b[k]]==['main']
    outline=json.loads((H/'ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v2.json').read_bytes())
    outline.update(status='UNBOUND_V3_PREPARATION_NOT_EXECUTION_BINDING',
        intended_binding_basename='ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v3.json',
        actual_runner=pin(H/'run_role_aware_independent_v3.py'))
    op=pub('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v3.json',outline)
    for p in outline['harness_pins'].values():assert pin(Path(p['path']))==p
    prep=pub('ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v3.json',dict(schema_version=1,status='COMMON_POST_SUITE_VETO_FROZEN_BEFORE_SUBJECT_EXECUTION',
        runner=pin(H/'run_role_aware_independent_v3.py'),outline=op,
        preserved_preparations=[pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v1.json'),pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v2.json')],
        preserved_runners=[pin(H/'run_role_aware_independent_v1.py'),pin(H/'run_role_aware_independent_v2.py')],
        author=pin(H/'prepare_role_aware_runner_v3.py'),freeze_author=pin(Path(__file__).resolve()),
        unchanged_harness_pins=outline['harness_pins'],dependencies=outline['dependencies'],
        static_delta=dict(only_changed_existing_function='main',deadline_facade_AST_equal=True,
            helpers_audit_identity_monitors_adapters_tests_and_expectations_unchanged=True,
            normal_completion='After either suite and before constructing a PASS record, compare real time with the original started+60 deadline. If late, overall result is FIRST_FAILURES_RETAINED while measured method results/counters remain intact.',
            exceptions='No finally deadline check; original escaping callback/source exception remains the original primary error. Common veto runs only on normal suite return.'),
        clocks='One real cooperative60s suite window includes bootstrap. BothCODEC_FIRST andLEGACY48_FIRST have the common post-suite veto. Original owner100/395/400 guards are unchanged. No owned outer watchdog/hard callback-free hang bound.',
        activity=dict(subject_source_reads=0,subject_imports=0,subject_runs=0,producer_runs=0,fixture_expectation_changes=0,original_payload_native_physical_operations=0),
        pending=['Native exact delta peer','coherent4source pause and root go','final execution binding and immutable first result'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=prep,outline=op,runner=pin(H/'run_role_aware_independent_v3.py'))))

if __name__=='__main__':main()
