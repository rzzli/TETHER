"""Finalize exact portable-source peer from frozen metadata and prior probes."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.json'
NOTE=HERE/'PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.md'

def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def pin(name):
    p=HERE/name;raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))

def main():
    assert not OUT.exists() and not NOTE.exists()
    expected={
        'portable_file_ports_v2.py':'b7785bd67b461f41ae7beeb1ce2e3b1a8bd0f210ba875eae61aaa25732425aed',
        'PORTABLE-FILE-PORTS-COMPONENT-FREEZE-v2.json':'d7fb7763921e53c508c8ae26f9aea15b727357e4aee1cfb0d9cc0015a6e4b44c',
        'PORTABLE-FILE-PORTS-SOURCE-FREEZE-v2.json':'cfb8c8ea21214732ad085804b1e64444ebdcb9795ccf08241696738c15771e55',
        'PORTABLE-FILE-PORTS-CORE-PURE-PROOF-v2.json':'bcc8a865c043135b7b9b734f75d17604f2486cf4b6cd11af091df3d8303ec0c1',
        'PORTABLE-FILE-PORTS-BEHAVIORAL-PROOF-v2.json':'246baec6c054e4c4063f1f1da9a89efa6d0e2c422bae547405915bc2ffdb96c2',
        'FILE-PORTS-FIXTURES-v4.json':'e1fd8d2161972fd5b64870d5ba9ad84fd5ed3d240973e5e111839556d7baf2a3',
        'PORTABLE-FILE-PORTS-INDEPENDENT-AFTER-v2.json':'7bad3fba79cb86c49d4e088aecf3ce498f2e95fb1ec45f4f1d9adc4bafea36bd',
        'PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json':'c30fbddf1019dee9a457705ec2553d0662b6555ae5a753a6bab7aeecd51dfc22',
        'PORTABLE-FILE-PORTS-SOURCE-CHOICE-REVIEW-v1.json':'9f00a14375d87734f985d217ac3fb5add5c4e93a720604ffaebb2519fd4d6eae',
    }
    pins={name:pin(name) for name in expected}
    assert all(pins[name]['sha256']==value for name,value in expected.items())
    component=read('PORTABLE-FILE-PORTS-COMPONENT-FREEZE-v2.json')
    indexed={}
    for key in ('authority','behavioral_checker','behavioral_proof','data','data_freeze','fixture_author','focused_checker','focused_proof','interface','schema','source','source_freeze'):
        claimed=component[key];path=Path(claimed['path']);assert path.parent==HERE
        actual=pin(path.name);assert actual==claimed;indexed[key]=actual
    before=read('FILE-PORTS-FIXTURES-v3.json');proposal=read('PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json');after=read('FILE-PORTS-FIXTURES-v4.json')
    proposed=copy.deepcopy(before['cases']);by={c['id']:c for c in proposed}
    for patch in proposal['patches']:
        c=by[patch['id']]
        if patch['new_script'] is not None:c['script']=patch['new_script']
        for key,change in patch['expected_field_changes'].items():
            assert canon(c['expected'][key])==canon(change['before']);c['expected'][key]=change['proposed']
    assert canon(proposed)==canon(after['cases'])
    assert len(proposal['patches'])==18 and sum(p['script_changed'] for p in proposal['patches'])==13
    assert sum(canon(a)==canon(b) for a,b in zip(before['cases'],after['cases']))==66
    core=read('PORTABLE-FILE-PORTS-CORE-PURE-PROOF-v2.json');behavior=read('PORTABLE-FILE-PORTS-BEHAVIORAL-PROOF-v2.json');own=read('PORTABLE-FILE-PORTS-INDEPENDENT-AFTER-v2.json')
    assert core['status']=='PASS' and core['tests']==21 and not core['failures'] and not core['errors']
    assert behavior['status']=='PASS' and behavior['cases']==behavior['matched']==84
    assert behavior['source']==core['source']==pins['portable_file_ports_v2.py']
    assert all(r['expected_projection_matches'] is True and r['script_exhausted'] is True and not r['differences'] and not r['adapter_errors'] and r['exception'] is None for r in behavior['rows'])
    attempts=sum(sum(r['source_observation']['api_attempts'].values()) for r in behavior['rows'])
    returns=sum(sum(r['source_observation']['api_returns'].values()) for r in behavior['rows'])
    assert (attempts,returns)==(199,193)
    assert all(all(r['source_observation'][flag] is False for flag in ('terminal_ack','FFI_registration_proven','production_owner_bound','profile_qualified','originals_authenticated','runtime_authorized')) for r in behavior['rows'])
    assert own['status']=='passed' and own['probes']==9 and not own['errors'] and not own['audit_denials']
    old_tree=ast.parse((HERE/'portable_file_ports_v1.py').read_text(encoding='utf-8'));new_tree=ast.parse((HERE/'portable_file_ports_v2.py').read_text(encoding='utf-8'))
    old_owner=next(n for n in old_tree.body if isinstance(n,ast.ClassDef) and n.name=='PortableOwner');new_owner=next(n for n in new_tree.body if isinstance(n,ast.ClassDef) and n.name=='PortableOwner')
    methods=lambda c:{n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
    left,right=methods(old_owner),methods(new_owner);changed=[name for name in left if left[name]!=right[name]]
    assert changed==['__init__','seed_for_tests','_file_identity','hash_capture','write_record','observe']
    assert set(right)-set(left)=={'assume_seed_identity_for_tests','_require_identity'}
    for name in ('Origin','RawReturn','FileSpec','EntrySpec','Slot'):
        a=next(n for n in old_tree.body if isinstance(n,ast.ClassDef) and n.name==name)
        b=next(n for n in new_tree.body if isinstance(n,ast.ClassDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    assert all(pin(name)==value for name,value in pins.items())
    note='''# Portable file primitives: independent source peer

The exact portable source b778 is clear for injected source/pure scope. Content I/O now requires a same-owner, nonce/slot/handle/path/spec-bound four-query witness. A separate pristine-seed capability is explicitly harness-only, cannot be minted for a caught query failure, and is never reported as production identity. Read/write entry accounting distinguishes predispatch stops from entered unknown returns and preserves known late byte counts.

The published v4 cases equal the exact root-authorized proposal applied to preserved v3: 18 changed, 66 unchanged, 13 repaired scripts. No deadline/hash/copy guard was removed. The full namespace failure retains its actual reservation prefix and 20 known written/hashed/flushed bytes; first WriteFile failure stays primary and later close failure stays secondary. All84 published behavioral projections pass with199 fake attempts/193 returns. The author's21 focused methods and nine independent reviewer boundary probes pass. Before failures and the earlier limited passes remain preserved.

The source delta changes six existing owner methods, adds two identity methods/classes, and leaves Origin, call/close mechanics, other owner methods and primitive types unchanged. Independent probes reject caught failed identity and raw booleans as authority, reject foreign seed capabilities, retain a valid fictional seed, preserve the original write exception, and distinguish no-dispatch versus malformed/nonreturned counts. No broad suite was replayed for this retention.

This accepts portable behavior over injected Python RawReturn observations only. It does not qualify actual FFI scalar registration before wrapper construction, a Win32 binding, live file/namespace behavior, a real first-entry clock, complete source loader/owner integration, exact real roster/resource fit, new Unicode archive/journal policies or a full verifier. Every terminal/provenance/profile/runtime flag remains false. No actual Win32/SDK/compiler, model/CPU/GGUF/old-pack or old-run operation occurred.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as f:f.write(note)
    record=dict(schema_version=1,status='CLEAR_PORTABLE_INJECTED_SOURCE_PURE_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_039_acceptance_audit',inputs=pins,component_index_verified=indexed,
        record_script=pin(Path(__file__).name),note=pin(NOTE.name),published_cases=84,focused_author_methods=21,independent_probes=9,
        fictional_API_attempts=199,fictional_API_returns=193,script_mismatches=0,
        exact_proposal_application=dict(changed_cases=18,unchanged_cases=66,repaired_scripts=13),
        source_AST_delta=dict(changed_owner_methods=changed,added_owner_methods=['assume_seed_identity_for_tests','_require_identity'],unchanged_owner_methods=[n for n in left if n not in changed],unchanged_Origin_and_primitive_types=True),
        identity_content_and_known_unknown_findings_resolved=True,no_remaining_material_finding_in_bounded_source_delta=True,
        author_suites_replayed_for_this_record=False,actual_Win32_FFI_qualified=False,FFI_raw_registration_qualified=False,
        production_owner_bound=False,real_first_entry_clock_qualified=False,complete_verifier_qualified=False,
        source_original_qualification=False,resource_qualified=False,profile_qualified=False,originals_authenticated=False,runtime_authorized=False,
        actual_API_calls=0,old_original_payload_operations=0)
    with OUT.open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(peer=pin(OUT.name),note=pin(NOTE.name),published84=True,focused21=True,own9=True)))

if __name__=='__main__':main()
