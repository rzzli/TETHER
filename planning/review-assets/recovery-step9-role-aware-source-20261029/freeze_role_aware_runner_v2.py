"""Freeze the one static runner deadline correction; no source execution."""
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
def functions(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}


def main():
    assert pin(H/'run_role_aware_independent_v1.py')['sha256']=='088759d53cba839a72499ac4c5be724eaea33b53fab59bd95376115f78ef4ac6'
    assert pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v1.json')['sha256']=='5280b159a71a556c40c45ab7983332aac7c33d9393f517898dd86f2ea124f40b'
    old=functions(H/'run_role_aware_independent_v1.py');new=functions(H/'run_role_aware_independent_v2.py')
    assert set(new)-set(old)=={'DeadlineCodecFacade'}
    assert [n for n in old if old[n]!=new[n]]==['main']
    prior=json.loads((H/'ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v1.json').read_bytes())
    prior.update(status='UNBOUND_V2_PREPARATION_NOT_EXECUTION_BINDING',
        intended_binding_basename='ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v2.json',
        actual_runner=pin(H/'run_role_aware_independent_v2.py'),
        cooperative_deadline='One original started+60 actual suite deadline; facade surrounds actual codec calls and their original callbacks. Post-call/post-suite late veto. No hard wall-time claim for callback-free hangs.')
    outline=pub('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v2.json',prior)
    for p in prior['harness_pins'].values():assert pin(Path(p['path']))==p
    report=pub('ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v2.json',dict(schema_version=1,
        status='RUNNER_ONLY_DEADLINE_CORRECTION_FROZEN_BEFORE_SUBJECT_EXECUTION',outline=outline,
        preserved_preparation=pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v1.json'),
        preserved_runner=pin(H/'run_role_aware_independent_v1.py'),runner=pin(H/'run_role_aware_independent_v2.py'),
        preparer=pin(H/'prepare_role_aware_runner_v2.py'),freeze_author=pin(Path(__file__).resolve()),
        unchanged_harness_pins=prior['harness_pins'],dependencies=prior['dependencies'],
        static_delta=dict(new_class='DeadlineCodecFacade',changed_existing_functions=['main'],
            all_other_top_level_function_class_ASTs_equal=True,original_fixed_source_map_unchanged=True,
            legacy48_expected_relations_unchanged=True,identity_and_audit_guards_unchanged=True,
            source_bytes_read_or_imported=0,source_runs=0),
        corrected_issue='V1 CODEC_FIRST passed the raw module to frozen tests, whose own check callbacks did not consult the real suite deadline. No subject was run under that gap; V1 evidence remains preserved.',
        facade_laws=[
            'Expose actual source FormatError type and return actual source DecodedLedger without wrapping/branding it.',
            'Forward the exact value and exact supplied check semantics. The wrapper checks the single original deadline before and after the actual supplied callback; no extra actual source callback site is introduced.',
            'If original check raises, rethrow the exact same object. A nonthrowing lateness observation replaces no callback exception; no finally-timecheck can mask it.',
            'Return the exact callback value including False. Do not convert it into eligibility.',
            'Record facade attempts/preforward refusals separately from actual encode/decode forwarding attempts, source checks, original callbacks and known returns/exceptions.',
            'Known source return after deadline is retained in forwarding counters and vetoed; a post-suite late result cannot become PASS.',
            'All original synthetic100/395/400 owner and dispatch clocks persist. One external suite deadline is test cancellation only, never renewed owner eligibility.'
        ],
        hard_wall_time_guard=False,callback_free_hang_bound='UNKNOWN_NO_OWNED_OUTER_WATCHDOG',
        authority='Root authorized one named runner-only correction after Native finite static batch; deadline was the only material runner/adapter issue. No frozen test, corpus, legacy expectation, source API or schema was changed.',
        pending=['Native exact runner-v2 peer','coherent4source pause pins','root execution authorization/final binding','first actual source proof for each explicitly selected phase'],
        activity=dict(subject_imports=0,subject_runs=0,producer_runs=0,fixture_expectation_changes=0,
                      original_payload_native_physical_operations=0),
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=report,outline=outline,runner=pin(H/'run_role_aware_independent_v2.py'))))


if __name__=='__main__':main()
