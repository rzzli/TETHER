"""Source-only finite adoption-seam design; no imported helper or live adapter."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parent
ADAPTERS=REVIEW/"recovery-step9-verifier-adapters-20261029"
CONTROLLER=REVIEW/"recovery-step9-verifier-recovery-20261029"
TARGET=HERE/"FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json"


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


assert not TARGET.exists()
sources=(
    (HERE/"portable_file_ports_v2.py","b7785bd67b461f41ae7beeb1ce2e3b1a8bd0f210ba875eae61aaa25732425aed"),
    (ADAPTERS/"verifier_bootstrap_interfaces_v2.py","d937599212133ee7c036ee863b8c751885ffe60f7d657ec1ed5e506bf90c74eb"),
    (CONTROLLER/"deterministic_verifier_v2.py","98ef68ee1bd0a5bb8fd2cf2c780a0dd0c294f7f24654d169280831cca5d4b725"))
for path,expected in sources: assert pin(path)["sha256"]==expected
gap=ADAPTERS/"ENGINE-CONTINUATION-INTEGRATION-GAP-v1.json"
assert pin(gap)["sha256"].startswith("69df")
tree=ast.parse(sources[0][0].read_bytes())
api_names=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="API_NAMES" for t in n.targets))
exports=[
    ("CreateFileW","HANDLE; INVALID only known failure, NULL/other malformed return remains unknown/no guessed ownership","N+F","Register usable scalar handle and closer before error-copy/clock/RawReturn."),
    ("GetFileType","DWORD","N+F","Retain raw value/error definedness; identity still requires disk-file value1."),
    ("GetFileInformationByHandleEx","signed32 BOOL +8-byte FILE_ATTRIBUTE_TAG_INFO","N+F","Retain raw flag/buffer before decode; regular/non-reparse checks do not follow a pathname."),
    ("GetFinalPathNameByHandleW","DWORD +4101UTF16-unit buffer","N+F","Retain returned length/buffer; clipping, scalar/terminator/path mismatch cannot mint identity."),
    ("GetFileSizeEx","signed32 BOOL +signed64 size","N+F","Retain raw flag/8-byte output; exact nonnegative declared size required for identity."),
    ("ReadFile","signed32 BOOL +DWORD count +buffer<=65536","sum(ceil(size/65536)+16 if size>0 else0)","Known count only after true rawBOOL+defined count<=request; failed/undefined is unknown, not zero."),
    ("CloseHandle","signed32 BOOL","N+F","Reserve same file-slot close once before invoke; adopt returned flag even if wrapper then raises."),
    ("GetFileAttributesExW","signed32 BOOL +36-byte attribute frame","1040","Metadata-only admitted directory/root; no discovered-path authority."),
    ("FindFirstFileExW","HANDLE +592-byte find frame","16","Adopt search handle with FindClose right immediately; function-specific INVALID/empty rule retained."),
    ("FindNextFileW","signed32 BOOL +592-byte find frame","178","False/error18 only natural end after a known search; no guessed scan completion."),
    ("FindClose","signed32 BOOL","16","Only search-slot once closer; never substitute CloseHandle."),
    ("CreateDirectoryW","signed32 BOOL","1","True return establishes namespace ownership immediately, never reservation readiness."),
    ("WriteFile","signed32 BOOL +DWORD count; immutable prepared chunk<=65536","E+412","Retain raw/count and known written lower bound before hash/flush/log; entered-unreturned stays unknown."),
    ("FlushFileBuffers","signed32 BOOL","E+9","Known success advances only the existing known-byte flush watermark; unknown return is not known flush failure/zero effect.")]
assert tuple(row[0] for row in exports)==api_names
record=dict(schema_version=1,status="FINITE_NEXT_GATE_DESIGN_ONLY_NO_IMPLEMENTATION_OR_RUNTIME_AUTHORITY",
    sources=[pin(path) for path,_ in sources],prior_gap=pin(gap),author=pin(Path(__file__).resolve()),
    exact_question="Can one source-issued owner retain raw file-call effects before throwable Python normalization and continue its existing bootstrap without new clock/registry/output ownership?",
    immediate_source_seam={
        "portable":"_new preallocates Slot and _call reserves a call before api(), but raw/counter/observe updates occur only AFTER api returns an already allocated RawReturn. _open_observation, hash_capture observed(), write_record observed(), and close_slot observed() are too late for an exception inside a real binding wrapper.",
        "bootstrap":"LeaseSlot.observe_owned_open/observe_read/observe_close expose a useful callback seam, but current callbacks accept normalized values; acquire/inspect/read/close and capture post-return checks cannot recover a raw handle/count lost before the wrapper returns.",
        "controller":"_Owner.hash_files consumes allocated OpenReturn/ReadReturn; close_all consumes a normalized return. _Owner constructor/run_once make fresh token/registry/time and output reservation. They cannot be called as continuation without a separately reviewed adoption entry."},
    proposed_boundary={
        "reservation":"Before dispatch, reserve one owner+Origin+nonce+slot+call ordinal record and any C out-buffer, immutable write slice, expected capacity and closer class. Bound all records/buffers by the eventual jointly admitted plan. Reservation is not proof that C was entered.",
        "first_Python_visible_return":"Immediately retain the raw scalar in the preallocated record and transfer usable handle/namespace/close status to the SAME actionable registry. Then retain count/definedness from preallocated outputs as each becomes observable. Do this before RawReturn allocation, error-string/last-error copy, post-call clock, query, log, hash or byte copy.",
        "defined_count":"Only the exact existing function-specific success+defined-count+range predicate advances known bytes. Raw zero with a defined successful count is a known zero; false/undefined/unreturned never becomes a known zero. Raw fields and definedness remain separate.",
        "return_axes":"Keep portable_call_reserved/entered, FFI_invocation_reserved, scalar_return_observed, count_observed/defined, and portable_wrapper_return_observed separately. Scalar-observed plus wrapper-exception means known raw return/effect and unknown or failed wrapper handoff, not an unreturned C call. Conversely ctypes argument/result conversion may prevent observing C entry/return: label that unknown rather than pretending a measured C census.",
        "counter_commit":"Raw-record scalar-return fact is counted once by call ordinal. Portable return acknowledgment is a different counter, not a second native return. If counter formatting/allocation fails after raw adoption, derive known returns from the retained flags without replaying the API or clearing the known effect.",
        "views":"A source-issued adopted-return view may be allocated later, but it owns no handle and grants no new close right. It references the current record identity/owner/nonce. No dict, identity_ok flag, serialized receipt or HarnessIdentityPrecondition can stand in for raw adoption.",
        "partial_Python_adoption":"A scalar can be retained while count/error/buffer conversion remains unknown. Preserve each observed fact and pending field independently; a later wrapper exception never overwrites a known handle/flag/count as unknown. No retry of an uncertain invocation.",
        "residual_FFI_gap":"Python-visible assignment is not atomic with native return or ctypes conversion. Async interruption/allocation/conversion before the first adoption can still leave an unknown side effect/handle. Preallocation narrows the window; it does not prove its absence. Any stronger C-level guarantee would require its own separately authorized design/build, not a claim from these Python/fake interfaces."},
    method_successor_map=[
        dict(existing="PortableOwner._call + _new + Slot",successor="One reserved call/slot passed INTO the binding. Replace the assumption that api() return is the first effect observation with adopted-record reconciliation; do not add another registry."),
        dict(existing="_open_observation/open_original/open_output/scan/create_namespace",successor="Install raw observed handle/search/namespace effect through the central slot before wrapper work. Preserve INVALID versus NULL and namespace_owned versus reservation_ready."),
        dict(existing="_file_identity/_IdentityWitness/_require_identity",successor="Mint real identity only after four same-handle query records pass under the current owner/Origin. Production adoption rejects test seeds/harness identity assumptions; no content I/O after a caught identity failure."),
        dict(existing="hash_capture observed()/write_record entering()+observed()",successor="Adopt defined known counts exactly once before copy/hash and reconcile a wrapper exception with the same raw record, not the pending-only fallback. Retain current raw C buffer lifetime when immutable copy/hash cannot finish."),
        dict(existing="close_slot/run finally + BootstrapOwner.close_all + controller _Owner.close_all",successor="Non-owning reporting views of one once-only close reservation. One caller consumes the exact file/search close right; other finally paths observe it, never dispatch again."),
        dict(existing="BootstrapOwner.acquire/capture/CapturedSources",successor="Adopt inspected live early slots and exact immutable captured bytes/digests/counts/pending state. A late buffer is retained as raw evidence, not silently discarded or marked hash_complete."),
        dict(existing="Handoff.claim/EngineContinuation + CapturedLoader",successor="Claim the exact existing owner/Origin/nonce/port/registry/output/events once. Keep same captured loader and current source context; no normal-import/cache fallback or second source capture."),
        dict(existing="deterministic_verifier.run_once/_Owner.__init__/hash_files/finish",successor="A distinct continuation-only entry and shared-owner views; do not invoke run_once, construct another _Owner, mint another token, reopen/hash early sources, or reserve output again."),
        dict(existing="PortableOwner.Origin versus bootstrap Origin versus controller _Owner.check",successor="Reconcile signatures/classes through a reviewed shared-origin interface retaining identical object/start/last/295s-work/300s-hard ends. Passing a numeric old start to a fresh Origin is insufficient."),
        dict(existing="reserve_namespace/write_record/output_pin + BootstrapOwner.reserve_output/event + engine sink.reserve/seal",successor="Same fixed namespace/output registry/journal sequence and physical observations; no acknowledgment echo or earlier owned boolean is a terminal source/file proof.")],
    minimal_exports=[dict(name=name,raw_shape=shape,existing_portable_cap=cap,adoption_rule=rule) for name,shape,cap,rule in exports],
    export_scope="Exactly the existing14 file-only exports/types/flags and bounded frames. No process, model, loader, network, GetLastError-export fallback, arbitrary WinDLL or discovery. ctypes-local last-error copying is later than raw adoption and retains definedness; successful stale LastError is not normalized into an OS guarantee.",
    ownership_and_late_data={
        "closers":"File handles use CloseHandle, search handles FindClose. Reserve once before invocation, including false/unknown/late returns. Known close success survives wrapper failure; no adapter destructor, portable finally, bootstrap finally or engine finally repeats it. Never guess a handle from an unobserved return.",
        "read_buffer":"The owner record retains the preallocated output-buffer reference and known returned slice/count before any copy/clock can throw. Do not reuse that storage until immutable capture is safely committed or the failed operation is retained. Known late bytes may remain unhashed/uncaptured; no positive file pin or renewed work after cutoff.",
        "write_buffer":"Retain the immutable prepared record and chunk before dispatch. A known short write advances only its count; do not retry an uncertain write or rehash/flush unknown tails into a positive pin. Returned flush/close flags are separate from output hash completeness.",
        "primary":"Keep any already latched Python primary object/phase unchanged. Later binding/copy/log/close errors are secondary. Raw API false/error facts remain independently retained even if a wrapper exception is the first Python exception; do not invent an earlier allocated PortError or silently reorder exception precedence."},
    same_owner_handoff={
        "identity":"Exact same Origin object, nonce, central registry and source-bound port. No origin reset, close-right copying, second reservation or serialized readiness token; adoption is one-use and rejects foreign/double claims.",
        "early_sources":"Match each current source claim/slot/context to the eventual full roster by lexical path/role/size/digest/capture policy. Preserve spent time, count/hash/capture state and live identity. Reuse only these current immutable bytes; hash only remaining originals later under the original deadline. This note does not inspect or qualify that full roster.",
        "loader":"Factories/checkers must execute through the same CapturedLoader/closed captured-byte dependencies. Current source self-registration/capture provenance and real pre-import first clock remain pending separate qualification, not supplied by this adoption design.",
        "events":"One event sequence/joint reservation covering early bootstrap and later engine/sink activity. Raw output/API observations stay registry-only to avoid recursive logging. Existing prototype128/2048 counters and the eventual E formula cannot be reset or added independently; exact roster/event fit is not established here.",
        "finalization":"Retain candidate write/flush/close, original cleanup, cleanup artifact, final journal flush/close, receipt, terminal seal and final SAME-Origin acknowledgment in the reviewed order. One central cleanup owner only. No failure file I/O after hard cutoff; preserve in-memory incomplete disposition instead of a new owner/retry."},
    fixture_expectations_to_freeze_before_code=[
        dict(id="pre_dispatch_cutoff",fault="Deadline before FFI invocation",expected="Logical reservation may exist; no FFI invocation, no owned handle or guessed unknown C side effect, no closer dispatch."),
        dict(id="handle_then_error_copy",fault="Usable CreateFile scalar observed; error-copy/RawReturn allocation raises",expected="Raw return1/wrapper return0; same slot retains ownership, exact original exception, one legal close before hard cutoff."),
        dict(id="INVALID_and_NULL",fault="Observed INVALID versus NULL; wrapper fails",expected="INVALID known failed no-handle; NULL remains function-specific unknown/no guessed ownership. Neither creates close rights."),
        dict(id="read_count_then_copy_failure",fault="BOOLsuccess/count3 adopted, immutable byte copy raises",expected="Known read3 retained once, hash/capture not falsely3; raw buffer retained; wrapper return0 does not reset known count or trigger another read."),
        dict(id="false_or_undefined_read",fault="BOOLfalse or undefined count with zero-initialized out storage",expected="Read count unknown; never treat storage zero as defined0. Raw fields/first Python error retained separately."),
        dict(id="write_count_then_late_clock",fault="Known write4 then hard cutoff",expected="Known write4 once, hash/flush/pin pending, no further I/O; original late stop preserved and no returned-count double accounting."),
        dict(id="close_return_then_wrapper_failure",fault="CloseHandle or FindClose BOOL observed then wrapper raises",expected="Raw close outcome survives, correct once-only closer consumed, no finally retry; wrapper error is not a second C return."),
        dict(id="query_fourth_return_then_expiry",fault="Last identity query known but post-call work clock expires",expected="Raw query data retained, no new content call or manufactured production identity token; existing owned handle cleanup only while hard time permits."),
        dict(id="unreturned_invocation",fault="Invocation/conversion raises before scalar adoption",expected="Preserve conservative invocation and unknown return/effect; no guessed zero, raw result, handle or automatic retry."),
        dict(id="search_boundary",fault="Initial INVALID/error2 declared empty versus18, later Next false18",expected="Existing exact empty/natural-end rules, bounded592B frames and one FindClose for each known search handle."),
        dict(id="namespace_partial",fault="CreateDirectory true then reservation/journal wrapper fails",expected="Namespace ownership retained, readiness false; known partial outputs/counters retained, no original content read or second reservation."),
        dict(id="foreign_or_duplicate_adoption",fault="Foreign Origin/nonce/port/slot, copied dict, repeated ordinal or wrong closer",expected="Reject before new FFI invocation; no extra returned count, close right or harness-only identity authority."),
        dict(id="same_owner_early_context",fault="Continue after spent time/early captures, then role mismatch or repeat claim",expected="Same original clock/events/context/slots; no reopened early source or fresh300s owner; mismatch/second claim rejected before remaining reads."),
        dict(id="existing_primary_and_late_cleanup",fault="Original exception then adopted close/publication error",expected="Original object/phase retained; bounded secondary facts, no post-hard I/O, no terminal positive acknowledgment.")],
    next_gate="Root/peer design review, then literal expectation freeze, then separately authorized source/pure adopted-record/controller-continuation work. Actual FFI binding construction/live exercise still separate; this note authorizes none.",
    qualifications_pending=["native-to-Python conversion/async-interruption window","actual14-export FFI behavior and same-slot adoption",
        "real first-clock entry/source authority","full static roster/closure/role/event/resource fit","real namespace/sink/archive/checker integration",
        "integrated originals/live leases and final owner/resource completion","runtime/profile/scientific qualification"],
    portable_helper_imports_or_executions=0,actual_FFI_API_calls=0,old_source_closure_operations=0,old_payload_operations=0,
    implementation_authorized=False,runtime_authorized=False,FFI_registration_proven=False,production_owner_bound=False,
    originals_authenticated=False,profile_qualified=False)
with TARGET.open("xb") as out: out.write(json.dumps(record,sort_keys=True,indent=2,ensure_ascii=False).encode("utf-8")+b"\n")
print(json.dumps(pin(TARGET)))
