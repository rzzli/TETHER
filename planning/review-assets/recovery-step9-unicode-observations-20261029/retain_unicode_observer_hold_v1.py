"""Retain completed finite source review; no observer/test replay."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.json'
NOTE=HERE/'UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.md'

def pin(name):
    p=HERE/name;raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
    assert not OUT.exists() and not NOTE.exists()
    expected={
        'unicode_observations_v1.py':'58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0',
        'unicode_observation_tables_v1.py':'009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d',
        'UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v2.json':'dba9ce192bb126532290b5b033c9b6cbb686c1d5d3bd267205830704941170f5',
        'UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json':'e6ebbb0fc2c9e237edad11c3d00b85c52e697db139730b0b0401a5d7f98d9282',
        'UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json':'cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b',
        'UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json':'f6a3c50437c2a75d38b94878aaa7083c24695b57ea2fac2c28e4f909850c32ad',
    }
    inputs={name:pin(name) for name in expected}
    assert all(inputs[name]['sha256']==value for name,value in expected.items())
    proof=json.loads((HERE/'UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v2.json').read_text(encoding='utf-8'))
    assert proof['tests']==10 and len(proof['failures'])==len(proof['errors'])==1
    assert proof['source']==inputs['unicode_observations_v1.py'] and proof['tables']==inputs['unicode_observation_tables_v1.py']
    for row in proof['dependency_pins']:
        # These are authored source-binding claims already consumed in the pure
        # proof, not a new original-source qualification pass by this reviewer.
        assert set(row)=={'path','bytes','sha256'}
    note='''# Unicode observer first-source peer HOLD

The finite source pass is complete against preserved source58d6 and tables009e. Four guards require a separately versioned correction: bounded JSON integer-conversion errors, marker-only post-collection call deltas, supplied-marker presence before row parsing, and a callback after result freezing. The first two were identified by this reviewer and reproduced in the author's full pure proof; root independently retained the latter two. No source or test was replayed to publish this record.

The full proof otherwise covers six literal bases, 36 scenarios, 33 observe callback identities, 22 strict callback identities and 22 nested mutations. Source inspection checked closed row/body sets, source references, exact setup vectors, case/prefix deltas, geometry delegation, progress commit placement and negative/partial classification. This is not blanket acceptance: the four reproduced boundaries remain held. The earlier stdlib-codec support harness failure is separately preserved and is not an additional observer defect.

The terminal-delta correction must preserve the design distinction between completed-phase cleanup and an unfinished prefix attempt; bounded unknown prefix work is partial evidence, while new tokenize work after full normal completion is a source-order contradiction. No separately reproduced fifth defect is claimed here. Cross-case token-piece mapping and exact reconstruction of unrecorded failure diagnostic indices are not newly imposed gates. Optional opaque module diagnostics remain explicitly pending/partial, not complete-positive.

No runtime, original-source closure, CPU/GGUF/old pack, SDK/native or actual experiment qualification is established. Retained matcher5031 is reused only as a known pure lexical dependency. All source/owner/resource/profile authority remains external and false in this component.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as f:f.write(note)
    findings=[
        dict(id='integer_conversion_data_error',origin='independent source review; reproduced by author',source='parse lines169-173',observed='5000-digit bounded JSON integer raises uncaught ValueError instead of bounded ObservationError',required='Handle data-only integer conversion errors around decode/loads; preserve already bounded ObservationError and original callback identities; no outer blanket catch.'),
        dict(id='marker_only_terminal_delta',origin='independent source review; reproduced by author',source='marker_record and finish',observed='Marker-only after full normal rows can add returned tokenize work and adjusted totals/last fields yet classify complete_negative_consistent',required='Apply phase-appropriate progress/call-delta constraints to marker snapshots; completed normal history admits no new work. Preserve partial prefix/unknown distinctions.'),
        dict(id='marker_presence_before_parse',origin='root independent pure probe',source='observe/marker_record',observed='Provided marker plus malformed early row yields error-prefix terminal_negative_seen false',required='Latch marker presence before any row parse without pretending its bytes/schema are validated.'),
        dict(id='callback_after_result_issue',origin='root independent pure probe',source='finish/_issue',observed='Caller deadline crossed during result deep-freeze still returns complete_success_consistent without a post-issue callback',required='Invoke the original callback after the immutable result is issued/frozen and before returning; propagate exact exception identity.'),
    ]
    value=dict(schema_version=1,status='HOLD_FOUR_REPRODUCED_SOURCE_PURE_BOUNDARIES',recorded_at_utc=datetime.now(timezone.utc).isoformat(),reviewer='/root/native_039_acceptance_audit',inputs=inputs,
        record_script=pin(Path(__file__).name),note=pin(NOTE.name),findings=findings,batch_complete=True,
        scope='Read-only finite source and retained pure evidence review; no author test or observer execution by reviewer for this record.',
        shared_evidence=dict(author_methods=10,author_real_failures=2,literal_bases=6,literal_scenarios=36,observe_callback_identity_controls=33,strict_callback_identity_controls=22,nested_mutations=22,root_additional_probes=2),
        root_harness_failure_is_not_observer_defect=True,implementation_acceptance=False,
        new_crosscase_or_diagnostic_reconstruction_rules_imposed=False,
        SDK_native_payload_operations=0,old_run_operations=0,original_source_qualification=False,profile_qualified=False,runtime_authorized=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(peer=pin(OUT.name),note=pin(NOTE.name),findings=4)))

if __name__=='__main__':main()
