"""Retain independent source/evidence review; never import or run reviewed code."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
REPORT=HERE/'VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v1.json'
NOTE=HERE/'VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v1.md'
PINS={
    'deterministic_verifier_v1.py':'b15142efac14d8beafc19f9c71b5d594737063303f5096f627e08e7f04adac4b',
    'check_deterministic_verifier_v1.py':'156649717f7b870613d6cd81bbd48a0a196cbf1a9b4735d6118a2583c217d9ac',
    'deterministic_verifier_initial_draft.py':'24f2729783ee90d2842238c381324c6d5c1b4fd9d88c69321bee064d2ba56e75',
    'VERIFIER-INITIAL-DRAFT-REGRESSION-REPLAY-v1.json':'127ae96e0a29439719ec4766922757855f742330a6af1401a117ebd340d180e9',
    'VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v1.json':'4ac3271c3b488fae45ed266585164aed700e1486f344d6eb2bc1f6f719e2ce65',
    'VERIFIER-RECOVERY-DESIGN-CONTRACT-v2.json':'7bff14386239d908ca33fd1a11214e95d90010b312aed3d23ac07b9fd69e3c6f',
    'VERIFIER-RECOVERY-SOURCE-ADDENDUM-v1.md':'0e5b2dd05e9f3789a66d1b042abdd21c9d44625f68fbd20f6307a1ad36b74377',
    'retain_verifier_pure_proofs_v1.py':'d91bd8d997030100f98b9201ccfe7ff6d8a8dcebb37f26e5c392a9187718e70e',
}
def pin(path):
    path=Path(path);assert path.parent==HERE,'Review only new-phase local files'
    raw=path.read_bytes();raw.decode('utf-8','strict')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def parsed(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def main():
    assert not REPORT.exists() and not NOTE.exists()
    records={}
    for name,expected in PINS.items():
        record=pin(HERE/name);assert record['sha256']==expected;records[name]=record
    proof=parsed('VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v1.json')
    assert proof['result']['passed'] is True and proof['result']['methods']==19 and proof['result']['failures']==proof['result']['errors']==0
    assert proof['old_original_or_payload_reads']==proof['SDK_or_native_or_compiler_calls']==0 and proof['real_filesystem_adapter'] is False
    for key in ('source','checker','retention_writer','approved_contract','source_addendum','initial_replay'):
        row=proof[key];assert row==pin(Path(row['path']))
    initial=parsed('VERIFIER-INITIAL-DRAFT-REGRESSION-REPLAY-v1.json')
    assert initial['result']['methods']==6 and initial['result']['failures']==5 and initial['result']['errors']==1
    assert 'not a historically before-fix test run' in initial['chronology']
    assert initial['source']==records['deterministic_verifier_initial_draft.py']
    source=(HERE/'deterministic_verifier_v1.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    checker_tree=ast.parse((HERE/'check_deterministic_verifier_v1.py').read_text(encoding='utf-8'))
    methods=[n.name for c in checker_tree.body if isinstance(c,ast.ClassDef) and c.name=='Checks'
        for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    assert len(methods)==19
    assert set(n.names[0].name if isinstance(n,ast.Import) else n.module for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)))=={'dataclasses','hashlib','json','math','types'}
    findings=[
        dict(id='context_immutability',original='Slots alone allowed replacing captured state attributes.',
            correction='Frozen slotted context, tuple/frozen specs, copied mapping proxies and byte values.',source_line=119,
            tests=['test_context_immutable_nonserializable_foreign','test_checker_mutation_and_omitted_gate_cannot_complete']),
        dict(id='undefined_read_and_failed_cleanup',original='Returned undefined reads and known failed closes could be mislabeled as evidence contradictions.',
            correction='Undefined counts latch unknown; returned false close sets cleanup-failed; late or uncertain close never retries.',source_line=319,
            tests=['test_read_late_failed_and_unreturned','test_close_false_unknown_late_no_retry']),
        dict(id='returned_stage_and_primary_clock',original='Late checker return was not retained, and later timing failure could replace a primary action error.',
            correction='Record bounded returned-observation facts first; latch primary before failure-time observation; preserve separate timing errors.',source_line=238,
            tests=['test_late_checker_return_and_clock_primary']),
        dict(id='pure_preflight_before_reservation',original='Malformed output shape could reach the output factory and reserve call.',
            correction='Pure typed Request/output key validation under the first owner clock precedes the factory.',source_line=465,
            tests=['test_shape_before_output_and_failed_reservations']),
        dict(id='reservation_ownership',original='Failed/foreign/unknown output reservation could still lead to seal/failure writes.',
            correction='Retain observed ownership acknowledgment and block all terminal writes without it.',source_line=413,
            tests=['test_shape_before_output_and_failed_reservations','test_same_output_cannot_repeat']),
        dict(id='durable_finalization_and_seal',original='Finalization/seal attempt reservations were only local state.',
            correction='Bounded prior journal events reserve finalization and seal; post-append hardclock checks gate later dispatch.',source_line=419,
            tests=['test_complete_order_and_negative','test_seal_failure_foreign_and_postseal_timeout']),
        dict(id='late_digest_and_final_clock',original='A late hexdigest could mark a hash complete before a fresh deadline check.',
            correction='Post-digest work check precedes hash-complete claim; report construction and seal return precede the final original-clock proof.',source_line=339,
            tests=['test_hash_fault_and_late_digest','test_seal_failure_foreign_and_postseal_timeout']),
    ]
    for item in findings:assert set(item['tests'])<=set(methods)
    result=dict(schema_version=1,status='CLEAR_SOURCE_PURE_ORCHESTRATION_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        review_type='Independent AI engineering source/evidence review; not scientist review or live verifier qualification',
        independence='Reviewer did not author this orchestration component/checker; supplied source findings and reviewed corrections. Prior native-parent authorship is unrelated and confers no new authority.',
        artifacts=records,findings_resolved=findings,remaining_material_source_blockers=[],
        evidence=dict(author_methods_passed=19,author_failures=0,author_errors=0,reviewer_reruns=0,
            initial_replay_methods=6,initial_replay_failures=5,initial_replay_errors=1,
            initial_replay_chronology=initial['chronology'],
            caveat='The one replay error is the initial draft missing checker_operations field; it is not counted as an assertion pass. Source inspection independently established the lost-return observability gap.',
            timing='Retained measured elapsed0.0 is timer-resolution output, not zero cost. Test-runner text reports0.012s; no actual300s resource fit is established.'),
        checked_boundaries=['300s original engine clock;295s work and5s reserve; no stage resets',
            'Clock precedes all injected factories; pure shape checks precede output construction/reservation',
            'Exact source-bound trusted factory claims, typed owner-local context and ordered gate proofs; no serialized ready flags',
            'Single fresh streamed fake-original pass, bounded capture, live leases held through checkers; no cross-owner cache',
            'Returned known handle/byte counts and late observations recorded before deadline/hash/log work',
            '256file/2048event joint admission;6*256+64+128=1728; no per-chunk durable event explosion',
            'Once-only known-handle cleanup, no new close dispatch after hardexpiry, primary/later errors retained',
            'Durable stage/finalization/seal reservations; candidate nonfinal; seal acknowledgment plus all required final proofs mandatory',
            'Source-negative fake archives still execute every integrity/resource/core/consistency/closure gate; never real_profile_qualified'],
        scope_limits=['No first-clock live bootstrap, CLI, real filesystem adapter or approved real checker ports are implemented or qualified.',
            'Future bootstrap must start before component/source imports and admission; this review covers only the injected engine clock, not an already implemented end-to-end program.',
            'Trusted port correctness/source identities and actual receipt/journal/raw-resource/core semantics remain separately reviewed integration work. Synthetic JSON booleans are not real archive validation.',
            'No old payload, model, CPU, pack, old source/input identity pass, runtime/native/compiler call or old-gate reclassification occurred.',
            'No real300s feasibility, DLL/vocabulary/EOG/full-mask/model/scientific validity claim follows.'],
        activity=dict(reviewed_source_or_tests_executed=0,old_input_or_payload_rehashes=0,SDK_target_compiler_calls=0,source_or_test_edits=0),
        execution_authorized=False,real_profile_qualified=False,scientific_validation='not_established',recorder=pin(Path(__file__)))
    with REPORT.open('x',encoding='utf-8') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
    text='''# Deterministic verifier recovery: independent source/pure review

**Clear within the declared orchestration-only scope.** No material source blocker remains in `deterministic_verifier_v1.py` (`b15142ef…04adac4b`). The [machine review](VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v1.json) binds the exact source, checker, design and retained proof bytes. This is an AI engineering review, not a scientist review or live verifier acceptance.

The review covered the whole component and all 19 synthetic test methods. The author-retained suite passes with no failures or errors; this reviewer did not rerun or import it. Six selected checks reproduce the preserved initial draft's defects as five failures and one missing-field error. That replay explicitly occurred after the corrected draft's first 17-method pass. It is not presented as a historically before-fix run. The measured zero elapsed field reflects clock resolution; the retained runner text reports 0.012 seconds and establishes no real resource fit.

The corrected boundaries are captured-state immutability; undefined read and failed-close classification; late checker-return bookkeeping and preservation of the primary error across timing failure; pure output-shape checks before reservation; no terminal writes without observed exclusive ownership; durable finalization/seal reservations; and rejection of late digest or final-clock outcomes. Focused tests cover these changes, required-gate omission, foreign context/ready flags, duplicate output, late open/read/close/seal, journal failures, and the joint file/event bound.

The engine uses one 300-second clock, with work ending at 295 and five seconds reserved for finalization. Its factories are called under that clock. All required owner-issued gates and known close returns, a seal acknowledgment and the final same-clock proof precede a complete synthetic result. A source-negative result still requires the remaining integrity/resource/closure checks and is never a profile pass. The 256-file limit reserves at most 1,728 events under the 2,048-event cap. Leases stay live while captured bytes are checked; no serialized ready marker or prior-run context becomes authority.

The important next boundary remains unimplemented: a real entry program must start its clock before reading/importing this component and its handlers. A separately reviewed fixed authority, original-file adapter and real archive/journal/resource/core checkers must preserve the graph and fresh identities. This review neither supplies nor qualifies those pieces, and does not show that their complete work fits 300 seconds.

No old original/source inputs or model/CPU/pack payloads were read or rehashed; no reviewed helper/test, SDK, target, compiler or native call ran during this review. The failed recognition experiment and incomplete external verifier remain unchanged. No DLL/vocabulary/EOG/full-mask, model, scientific or numerical prediction claim is made.
'''
    for target in re.findall(r'\]\(([^)]+)\)',text):assert (HERE/target).is_file()
    with NOTE.open('x',encoding='utf-8',newline='\n') as out:out.write(text)
    print(json.dumps(dict(status=result['status'],report=pin(REPORT),note=pin(NOTE),author_methods=19,reviewer_reruns=0)))
if __name__=='__main__':main()
