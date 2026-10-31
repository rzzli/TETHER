"""Retain exact corrected source/pure review and existing proofs; no test replay."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v2.json'
NOTE=HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v2.md'

def pin(name):
    p=HERE/name;raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
    assert not OUT.exists() and not NOTE.exists()
    expected={
        'unicode_observations_v2.py':'47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6',
        'unicode_observation_tables_v1.py':'009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d',
        'UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json':'66a57c7b3316e6791dbdcb645ca968338aa61f19f68962964bf96126c9d6ca70',
        'UNICODE-OBSERVATIONS-IMPLEMENTATION-FREEZE-v2.json':'f8afdc057976ac871bb8d27b75771a0c3332c66a17869e48be68006ded02c1e6',
        'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.json':'5ebd57eff292ecf5c49abf7ae7d41c60598721f87c2673460cc53c59da1a96be',
        'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-AFTER-v2.json':'280b37501d99e8fd8ec20ceb5a317baf5edaf0aabb6f98df6cd2c70774a8c80d',
        'UNICODE-OBSERVATIONS-ROOT-BOUNDARY-AFTER-v2.json':'628834ca137cedfb11dfdd9ca29e3ec2cd3c05a892706971d62912bac4d08a2e',
        'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json':'f6a3c50437c2a75d38b94878aaa7083c24695b57ea2fac2c28e4f909850c32ad',
    }
    pins={name:pin(name) for name in expected}
    assert all(pins[name]['sha256']==value for name,value in expected.items())
    author=json.loads((HERE/'UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json').read_text(encoding='utf-8'))
    own=json.loads((HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-AFTER-v2.json').read_text(encoding='utf-8'))
    assert author['status']=='passed' and author['tests']==14 and not author['failures'] and not author['errors']
    assert author['source']==pins['unicode_observations_v2.py'] and author['tables']==pins['unicode_observation_tables_v1.py']
    assert own['status']=='passed' and own['probe_count']==4 and len(own['outcomes'])==4 and all(v['passed'] for v in own['outcomes'])
    assert own['audit_denials']==author['audit_denials']==[]
    pins['check_unicode_observations_peer_v2.py']=pin('check_unicode_observations_peer_v2.py')
    note='''# Corrected Unicode observer source peer

The exact source47c7 and unchanged tables009e are clear for their declared source/pure scope. All four first-source findings are resolved: large JSON integer conversion becomes a bounded data error without swallowing callbacks; marker-only snapshots obey phase-specific terminal deltas; supplied marker presence is latched before earlier row errors; and the original callback runs after result freezing. The shared terminal guard retains bounded next-prefix creation with an unknown return as partial, with no invented dependent cleanup.

The author’s 14 methods pass across six literal bases, 36 scenarios, 33 observe callback identities, 22 strict callback identities, nested/type/immutability controls and the before/after boundaries. Four separate reviewer probes pass: bounded giant integer, retained valid marker-only negative, rejected post-normal tokenize work, and retained partial prefix nonreturn. Root independently repeated its two identical marker-presence/final-freeze probes. No broad full-suite replay was performed for peer publication.

Exact AST comparison confines changes to observe and five existing Reader methods plus the new shared failure_tail helper. Profile factory, membership/ledger handling, strict typed result API, data tables and the other methods remain unchanged. The first source, its real failures, initial harness-only codec support failure, and before witnesses remain preserved.

This accepts captured source-reported instrumentation consistency only. Exact native truth, original/capture provenance, production source loader/owner binding, new Unicode-specific archive/journal policies, complete resource checks, runtime and scientific qualification remain pending. Opaque module diagnostics remain partial/external_pending. Cross-case vocabulary mapping and exact reconstruction of unknown failure diagnostics were not silently added as gates. The known pure matcher is reused without claiming a new original-source closure qualification. No CPU/GGUF/old pack/runtime file, SDK/native or actual experiment was accessed.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as f:f.write(note)
    record=dict(schema_version=1,status='CLEAR_SOURCE_PURE_ONLY_WITH_EXTERNAL_GATES_PENDING',recorded_at_utc=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_039_acceptance_audit',inputs=pins,
        record_script=pin(Path(__file__).name),note=pin(NOTE.name),prior_four_findings_resolved=True,
        author_methods=14,reviewer_probes=4,root_identical_after_probes=2,literal_bases=6,literal_scenarios=36,
        exact_AST_delta=dict(changed_top_level=own['changed_named_top_level_ASTs'],changed_reader_methods=own['changed_reader_methods'],added_reader_methods=['failure_tail'],unchanged_reader_methods=own['unchanged_reader_methods']),
        retained_prefix_unknown=True,no_remaining_material_finding_in_bounded_source_delta=True,
        author_full_suite_rerun_for_this_record=False,optional_module_diagnostics='partial_external_pending',
        new_crosscase_or_unknown_diagnostic_reconstruction_rules=False,
        original_source_closure_qualified=False,production_loader_owner_bound=False,new_Unicode_archive_journal_policies_qualified=False,
        resource_qualified=False,profile_qualified=False,originals_authenticated=False,runtime_authorized=False,scientific_validation='not_established',
        SDK_native_payload_operations=0,old_run_operations=0,pack_file_created=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(peer=pin(OUT.name),note=pin(NOTE.name),author_methods=14,own_probes=4)))

if __name__=='__main__':main()
