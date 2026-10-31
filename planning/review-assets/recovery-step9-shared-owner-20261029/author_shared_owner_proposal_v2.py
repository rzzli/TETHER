"""Retain the five agreed design clarifications; no component implementation."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    old=HERE/'SHARED-OWNER-CONTINUATION-PROPOSAL-v1.json';target=HERE/'SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json';md=HERE/'SHARED-OWNER-CONTINUATION-PROPOSAL-v2.md'
    assert not target.exists() and not md.exists()
    assert pin(old)['sha256']=='ed72dbb98842f3daa61e4bc89e5619335bed6e3226546016acd87ffd6146f953'
    hold=HERE/'SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v1.json';assert pin(hold)['sha256']=='68ed430031b8f6c6aeccca23dda480b42c43e51950cde8b684f963f4c14fcece'
    d=copy.deepcopy(json.loads(old.read_text(encoding='utf-8')));d['schema_version']=2;d['recorded_at_utc']=datetime.now(timezone.utc).isoformat();d['preserved_v1']=pin(old);d['v1_peer_hold']=pin(hold)
    d['status']='CLOSED_FIVE_CLAUSE_SOURCE_DESIGN_SUCCESSOR_NOT_IMPLEMENTATION_AUTHORIZATION'
    files=d['proposed_files'];files['shared_owner_v1.py']['apis'].insert(3,'SharedOwner.admit_plan(full_specs, early_paths, module_rules) [before reserve_output and first original open]')
    files['shared_owner_v1.py']['apis'].remove('SharedOwner.admit_early(specs)')
    files['continue_verification_v1.py']['apis'][0]='continue_once(continuation, request, test_authority_factory, test_checker_factory)'
    d['active_original_API_subset']=['CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle']
    d['inactive_exports']=['GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers']
    d['active_scope_rule']='Only seven injected original-file operations are active. Byte-count regressions are ReadFile only. No WriteFile/short-write/physical-output flush/close assertion belongs to this batch. The sink models Python attempt/ack/unknown observations, NOT file I/O. Full fourteen-export and physical sink binding remain later.'
    d['pre_open_admission']={
      'signature':'SharedOwner.admit_plan(full_specs, early_paths, module_rules)',
      'order':'Original Origin exists first; validate/admit ALL provisional descriptors and joint worst-case bounds before reserve_output and before any original open. An admission failure has no output write right. Then reserve output once, capture the declared early subset and exercise its closed loader.',
      'typed_input':'full_specs is an exact tuple of canonical immutable FileSpec objects. early_paths is a unique ordered tuple referring to software/captureTrue entries. module_rules is the closed two-module graph referencing only early entries. The provisional tuple is expected metadata, not a completed authority/hash gate.',
      'one_reservation':'Allocate/reserve one owner-local joint plan and its slot/call/buffer/event/output capacities here. There is no later 128/175/2048 reset or second pool. All early work and failures debit it.',
      'later_authority':'The later fixture-only authority callback must return the exact pre-admitted descriptor tuple/checker IDs bound to this owner. Reconcile against the saved plan and current early live records; do not grow limits, replace descriptors, reopen early paths or reset counters. Only then can the pure admission stage complete.'}
    d['buffer_protocol']={
      'read_work_buffer':'Exactly ONE owner-retained read work buffer, capacity<=65536. Its allocation is admitted and timed before any dispatch. Every read record borrows the same object and its current bounded generation; never allocate R independent frames.',
      'successful_reuse':'After a defined returned slice is folded once, hash-updated and copied into the owner append-only file capture assembly, it may advance generation for the next read. The record retains count/generation/file-offset evidence; completed bytes are retained by the capture assembly or immutable final blob. No unfinished slice is silently dropped.',
      'stop':'The FIRST pending, failed, undefined, unknown or copy/hash-stopped read stops all future read dispatch/reuse. Keep its actual current buffer/reference/generation and observed raw facts. Cleanup CloseHandle needs no replacement read buffer.',
      'query_work':'One owner-retained query work buffer<=8202B, with exact8/8202/8-byte views for the three buffer-returning identity queries. Store immutable query frames before reuse; failed/unknown conversion retains the current buffer and blocks identity/content progress.',
      'enforceable_raw_ceiling':'Before each allocation reserve bytes in the SAME raw-storage ledger. Worst first-cohort payload storage: read65536 + querywork8202 + retained queryframes4*(8+8202+8)=32872 + mutable capture assemblies16384 =122994B <=131072. Captured final immutable blobs have their separate16384B cap. Reject an allocation before it exceeds either pool; do not allocate Rframes. These are payload-storage caps, not measured Python process memory.',
      'generation_bound':'Strict increasing generations bounded by admitted total R<=68, with before-mutation owner/record/generation checks. This is an explicit new cohort bound, not an assertion that old literal generation0..3 qualified a larger trace.'}
    kinds={'candidate':'verification-candidate.json','cleanup':'original-lease-cleanup.json','failure':'failure.json','receipt':'receipt.json','seal':'terminal-seal.json'}
    d['sink_signature']=['reserve(output_key, ack, hard_end) -> observed ack','append(immutable_event_bytes, ack, hard_end) -> observed ack','publish(kind, immutable_bytes, ack, hard_end) -> observed ack [exact five kinds below]','close_journal(ack, hard_end) -> observed ack; owner derives its fictional tip from retained acknowledged row bytes']
    d['publication_protocol']={
      'kinds':kinds,'bounds':'Each kind at most one ATTEMPT, including failed/unknown, <=8192B. Journal rows<=1024B inclLF, total modeled output<=524288B. The previous eight nonjournal-record allowance is ceiling/slack, NOT eight active kinds.',
      'semantics':'Sink callbacks are fictional publication attempt/ack/unknown evidence only; a returned token never claims physical WriteFile bytes, FlushFileBuffers, file close, filesystem durability or source freshness. No storage-complete real gate is minted.',
      'ordering':'candidate, cleanup and optional failure before journal close may have pre-reserved journal events. Receipt/seal callbacks run after journal close and update registry only. Final owner acknowledgment is in-memory. Any postseal error remains in-memory; no afterseal output kind or further write.',
      'veto':'Never publish a successful seal while a primary, unknown/failed original closure or required-stage gap exists. No append after close_journal, no retry/overwrite of a consumed kind, no callback after original hard cutoff. An owned failed path may publish the optional failure once only if time and original budget remain.'}
    d['terminal_order']=[
      'While early and remaining source leases are live and the last required test checker has returned, publish the immutable candidate through the fictional sink. Preserve its observed callback return before clock checks.',
      'Close ALL originals once through the canonical original-file raw ledger; include early helpers. No view/destructor/finally repeats a consumed close right.',
      'Publish cleanup and optional failure (owned/time/budget permitting). Emit all final preclose journal events and call close_journal once. These are callback acknowledgments, not physical flush/close facts.',
      'If no primary, no unknown/failed original closure and every required pure stage completed, publish receipt then seal with registry-only observations. Otherwise do not claim seal success.',
      'Perform the final SAME-Origin clock check and in-memory pure-seam acknowledgment. Late seal returns remain known callbacks but cannot complete. Postseal errors stay in-memory. No sink call after hard300.']
    d['test_factory_binding']={
      'signature':'continue_once(continuation, request, test_authority_factory, test_checker_factory)',
      'origin':'Explicit fixture-only branded trusted injected callbacks supplied by the independent harness, bound to the canonical owner/nonce. Their objects are not imported from the209B cohort and are never described as freshly source-qualified authority/checkers.',
      'marker_loader':'The unchanged58B leaf +83B entry marker chain tests captured-byte loading, exact dependency resolution and live early leases under this SAME owner only. It contains no factories/checkers and is not modified to add them.',
      'observations':'Test observations require this exact EvidenceContext/stage/owner and captured synthetic evidence references. Missing or foreign brands refuse. They can prove pure seam control flow only; real factory/checker binding remains unimplemented/unqualified, with all real/profile flags false.'}
    d['injected_binding_hook_contract']={
      'invoke':'InjectedBinding.invoke(call_ref, arguments, adoption_hooks) -> None. FilePortView alone reserves/enters the canonical call and accounts for the wrapper return before its post-clock check. The return value transfers NO handle/count/close right; a normal None return with no scalar store remains raw-return unknown.',
      'call_ref':'A source-issued non-owning reference to the exact owner/nonce/registry/ordinal/slot/buffer generation. No dict, ordinal alone, copied carrier, Harness identity assumption or returned RawReturn can replace it.',
      'hooks':{
        'store_scalar(call_ref, value)':'CreateFileW: observedNone or strictuint64 incl0/INVALID; GetFileType/GetFinalPathNameByHandleW: strictuint32; other four active APIs: strictsigned32 BOOL. Pythonbool is rejected. UNOBSERVED is initialization-only and distinct from observedNone/0.',
        'store_count(call_ref, value)':'ReadFile only, strictuint32 observed cell. Known defined bytes require stored nonzero signedBOOL pluscount<=reservedrequest. False/undefined/unobserved is NOT known0; defined0 is a raw knownzero but cannot satisfy a remaining-file read.',
        'store_error(call_ref, value, defined)':'Strictuint32 ctypes-local error observation and strictbool defined, only after scalar storage. Definedtrue only on the function failure/unknown branch. It cannot erase prior scalar/count. No GetLastError export or real error-copy is introduced.',
        'buffer_write(call_ref, buffer_ref, generation, data)':'Source-bound current buffer/generation, immutablebytes, capacity checked BEFORE mutation. Read data<=reserved capacity; query frames exactly8/8202/8 as applicable. Raw buffer bytes alone are not defined read/query results; FilePortView applies scalar/count/length/terminator/path/size predicates under the same clock.',
        'aux(call_ref, field)':'Only scalar_aux_ack/count_aux_ack/right_transfer_ack diagnostic booleans. Raw first facts, never these flags, drive effect reconciliation.',
        'raise_exception(call_ref, exception, phase)':'Actual original BaseException plus closed source position. Records a wrapper observation, preserves first primary and known return facts, then the binding may rethrow that SAME object. Outer FilePortView catch records only an unrecorded exact error, using binding_invoke when no finer source phase was observed.'},
      'phases':['binding_invoke','pre_dispatch','after_scalar_before_aux','after_scalar_before_right_transfer','error_copy','RawReturn_allocation','after_count_before_aux','buffer_copy','hash_update','post_call_clock','identity_query','handoff','close_wrapper','cleanup_publication'],
      'query_result':'No identity-ready/query_result shortcut exists. The same four actual query records and exact scalar/buffer data are validated by FilePortView; only that owner may issue its current-handle witness. The seven-API fake binding does not mint production identity.',
      'internal_only':'reserve/invoke/wrapper_return/reconcile and once-closer consumption belong to FilePortView/central owner, not an injected binding return. Reconciliation folds by ordinal+field once after success or exception. Stopped calls reject new facts/work; known wrapper returns stay known; legal once cleanup is separate.',
      'unknown_window':'These hooks model deliberate application-level first assignments AFTER Python sees a return. They neither run a real FFI nor close conversion/allocation/async interruption before first storage.'}
    d['joint_caps']['derived']=[s.replace('source/sink fixture row','source/sink fixture row') for s in d['joint_caps']['derived']]
    d['joint_caps']['derived'][3]='Fixed64 covers the pre-reserved normal source-loading/authority/checker/stage/output/cleanup events; failure128 is in the SAME E. Before ANY early open, reserve the complete joint plan; later matching authority only debits/reconciles it. No fresh pool or cap growth.'
    d['joint_caps']['derived'][4]='R<=68 does NOT allocate68 frames: enforce the single read/query-work and retained-frame ledger in buffer_protocol; first pending/failed/unknown stops future reads. Read generation increases only after fold/hash/capture commit.'
    d['joint_caps']['derived'][5]='Journal rows<=1024B inclLF, five named publish kinds<=8192B each, total modeled output<=524288B. Eight nonjournal records is conservative slack, not additional active kinds. Callback acknowledgments are not physical I/O metrics.'
    for c in d['pure_fixture_matrix']:
      if c['id']=='late_count':c['input']='Known ReadFile count followed by cutoff or copy/hash exception.';c['required']='Known read bytes preserved before clock; hash/capture pending; no future read/reuse or fabricated zero; no double fold. WriteFile is inactive.'
      elif c['id']=='reservation_or_append_fault':c['required']='Unowned output gets no further sink callbacks; owned failed append retains attempt/primary, no recursive journal. Attempt/ack/unknown only, no physical byte/flush/close assertion.'
      elif c['id']=='close_and_terminal_faults':c['required']='One original-file CloseHandle reservation, no retry; no seal success for primary/unknown original closure; no journal callback after close and no publication after seal/hard cutoff. Sink facts remain fictional acknowledgments.'
      elif c['id']=='budget_and_output_caps':c['input']='N5/B3/M3, forged C/E, exhausted short-read/publication budget.'
      elif c['id']=='checker_binding':c['required']='Only explicitly harness-branded injected test callbacks accepted; they are not loaded from the markerchain. Negative is pure-seam negative only after all remaining required stages/closure; every real factory/checker/profile flag stays false.'
    d['next_coding_batch']='After root/peer accepts v2: freeze exact synthetic fake-binding/publication schedules over the unchanged209B input cohort, then implement only shared_owner_v1.py/shared_file_ports_v1.py/continue_verification_v1.py plus independent drivers/tests. Use the active seven-original-API hook contract, one pre-open admitted plan, single read buffer and five-kind fictional sink. No actual FFI, remaining seven exports, real first-entry, physical sink/metadata/search, production checker or old archive/source qualification.'
    d['v2_change_scope']='Exactly the five root/peer closure clauses plus their closed active-hook/signature details; one-owner/three-source choice,14causal groups,209B cohort, N/B/M/R/C/E ceilings and all pending real gates remain. v1/68ed HOLD are preserved.'
    d['author']=pin(Path(__file__))
    with target.open('x',encoding='utf-8') as out:json.dump(d,out,sort_keys=True,indent=2);out.write('\n')
    md.write_text('''The v2 proposal keeps one canonical bootstrap-successor owner and two non-owning views. It closes the five ed72 review points without adding a production binding.

`admit_plan(full_specs, early_paths, module_rules)` now runs before output reservation or the first original open. It validates the complete provisional cohort and reserves the one joint slot/call/buffer/event/output plan. Later harness authority must match the exact saved descriptors and checker IDs; it cannot reset or grow the plan. Baseline N3/B2/M2 has R51/C69/E218; ceilings remain N4/B2/M2, R68/C92/E224.

Only seven original-file APIs are active. The fake binding uses central-owner store_scalar/count/error, buffer_write, aux and exception hooks; exact value domains and names are in the JSON. The returned Python None/typed view grants no ownership. Query results must come from the four retained query records, not a ready flag. WriteFile and the other six inactive exports remain pending.

There is exactly one retained read buffer at most65536B, not R independent buffers. A generation can advance only after its known slice is folded, hash-updated and captured. The first pending/failed/unknown slice stops future reads and retains the current storage. Query work/retained frames and mutable capture assemblies debit the same131072B pool; final immutable captures have their separate16KiB cap. The explicit worst payload-storage sum is122994B, not a process-memory measurement.

The fictional sink has five once-attempt publish kinds: candidate, cleanup, failure, receipt and seal, each at most8192B. Its callbacks provide attempt/ack/unknown evidence only: no physical WriteFile/flush/close/durability claim. Candidate/cleanup/optional preclose failure may have journal reservations; receipt/seal are registry-only after journal closure. Postseal errors are in-memory only. No successful seal is claimed with a primary or unknown original closure, and no callback runs after hard300.

The unchanged209B marker chain tests captured-byte loading only. Authority and checker callbacks are explicitly harness-branded trusted injections, not loaded/source-qualified factories from those helpers. They can establish pure seam control flow; real factory/checker and all runtime/profile qualification remain unbound.

No component code, ctypes, SDK, native/file API, payload, model, old closure or prior timed-out experiment was executed or repaired. The original v1 proposal and its HOLD remain preserved. Root/peer review of this exact successor precedes any coding batch.
''',encoding='utf-8')
    print(json.dumps(dict(proposal=pin(target),readable=pin(md))))
if __name__=='__main__':main()
