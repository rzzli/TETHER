"""Retain a bounded design review; no adapter/source helper is executed."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
REPORT=HERE/'VERIFIER-ADAPTER-INDEPENDENT-DESIGN-REVIEW-v1.json'
NOTE=HERE/'VERIFIER-ADAPTER-INDEPENDENT-DESIGN-REVIEW-v1.md'
EXPECTED={
    'VERIFIER-ADAPTER-DESIGN-CONTRACT-v1.json':'0327e9088f1dc1dce09f8806c5d0cf642c4700c7893385fc44e6cf58390993ef',
    'VERIFIER-CHECKER-SOURCE-MAP-v1.json':'a1968a61e56e5fb16ba323bee158c308e207a5f3496cd23f7d97d8d08704f152',
    'VERIFIER-ADAPTER-DESIGN-v1.md':'272a6b24546d2c4b1d1876bf3c8942657fbc479dfc37752b7fba6c9771f48ca3',
}
def pin(path):
    path=Path(path);assert path.parent==HERE
    raw=path.read_bytes();raw.decode('utf-8','strict')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def main():
    assert not REPORT.exists() and not NOTE.exists()
    artifacts={}
    for name,expected in EXPECTED.items():
        row=pin(HERE/name);assert row['sha256']==expected;artifacts[name]=row
    for name in ('VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.json','VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.md','ROOT-DESIGN-REVIEW-v1.md'):
        artifacts[name]=pin(HERE/name)
    contract=load('VERIFIER-ADAPTER-DESIGN-CONTRACT-v1.json');clarification=load('VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.json')
    assert clarification['base_contract_sha256_from_frozen_record']==EXPECTED['VERIFIER-ADAPTER-DESIGN-CONTRACT-v1.json']
    assert clarification['six_stream_APIs_are_not_complete_platform_adapter'] is True
    assert contract['authorization_now']['implementation'] is False and contract['authorization_now']['live_file_adapter_or_SDK_construction'] is False
    assert contract['clock_and_bootstrap']['total_seconds']==300 and contract['clock_and_bootstrap']['no_reset'] is True
    assert contract['captured_context']['deeply_immutable'] is True and contract['captured_context']['fresh_originals_required'] is True
    proposed=[r['API'] for r in clarification['proposed_metadata_APIs']]
    assert proposed==['GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose']
    value=dict(schema_version=1,status='DESIGN_ARCHITECTURE_CLEAR_FOR_PURE_INTERFACES_PLATFORM_AND_LOADER_GATES_PENDING',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),review_type='Independent AI engineering design critique; not implementation/SDK/live evidence or scientist review',
        artifacts=artifacts,
        disposition='No fundamental architecture blocker for a separately authorized pure injected origin/handoff/ownership/metadata interface prototype. This review itself authorizes no implementation. Real platform binding and live verification remain held.',
        central_design_checks=['One bootstrap origin precedes helper source reads/imports/preflight; engine continues the same owner without a new start or numeric archive/CLI origin.',
            'Early hash-bound captured source bytes, live original leases, output reservation/journal and operation records transfer once in the same owner. Serialized ready flags and cross-run receipts are not authority.',
            'Explicit application-level owned handle/read return registration precedes deliberate identity/copy/hash/clock work; undefined/unreturned effects remain unknown; closes are once-only.',
            'Immutable captured bytes from the fresh original handle feed every checker; no copied-payload substitute, hidden path reopen or second model hash pass.',
            'Candidate/cleanup/journal/receipt/seal DAG remains acyclic and nonfinal until known output closes plus the returned original-clock acknowledgment. Late/unknown returns veto completion.'],
        resolved_design_clarifications=[dict(id='stream_API_scope',finding='Six original read-stream APIs do not implement ancestry checks, bounded directory scans or output creation/writes.',
            resolution='Clarification explicitly holds separate platform metadata and output stages. Proposed attributes/search APIs and distinct FindClose ownership, error/end-of-directory distinction and finite bounds are disclosed, not claimed implemented.'),
            dict(id='native_to_Python_gap',finding='Immediate application registration cannot make ctypes/native conversion atomic or allocation-free.',
            resolution='Clarification states earliest deliberate assignments after Python-visible return. Unobserved return remains unknown; no universal no-leak/cleanup or process-death guarantee.')],
        required_before_real_platform_binding=[dict(id='complete_API_and_ownership_census',requirement='Freeze typed stream/metadata/output API closure, flags/layouts/sentinels and correct per-handle closer. Include namespace-exclusive CreateDirectory/CreateFile(CREATE_NEW), Write/Flush/Close; do not hide Path/os/scandir/rglob fallbacks.'),
            dict(id='metadata_and_write_call_bounds',requirement='Derive exact finite admitted ancestor/directory lists and actual call/event/handle reservations. Freeze read/write/short-operation headroom with explicit exhaustion. Failed/unreturned calls never retry; false/unknown metadata cannot establish safe ancestry or natural end.'),
            dict(id='closed_source_loader',requirement='Freeze exact own-helper fullname/dependency map and approved stdlib policy, including relative resolution. Own modules load only from captured hash-matching bytes; reject unknown or cached-own-module fallback, importlib path discovery, linecache/inspect/traceback source rereads.'),
            dict(id='same_owner_handoff_proofs',requirement='Test one-time trusted origin/handoff, early ownership survival on imports/failures/late return, no numeric reset and no fresh-source rehash exemption. A real bootstrap starts its timer before component import; the accepted injected engine alone does not provide it.'),
            dict(id='real_checker_implementations',requirement='Implement and independently test actual-format captured-byte archive/universe/receipt/seal, canonical journal/order, raw resource/EOF/exit/cleanup and new-profile decoder/strict+negative observer. Synthetic gates do not supply these implementations.'),
            dict(id='new_profile_binding',requirement='Use separately frozen84case Unicode profile and future exact wire/pack/ledger semantics; no old189case/six-prefix constants or success shortcut. Profile freeze is not a runtime roster, decoder or execution protocol.')],
        bounds_assessment='Proposed metadata and read/write limits are finite design policies. Exact future role graph, joint event budget, typed SDK checks and real300s fit remain unproven; overflow holds before dispatch, not silent omission or cap expansion.',
        documentation_scope='The source author supplied official Microsoft API references in its clarification. This reviewer read the local design, not an independent SDK/API execution or documentation revalidation; exact live semantics/constants/layouts remain a future gate.',
        old_evidence_status='Original negative recognition and incomplete external verifier remain unchanged; no old gate is completed or repaired by design.',
        activity=dict(design_metadata_only=True,reviewed_helpers_or_tests_executed=0,old_original_or_source_rehashes=0,CPU_GGUF_pack_operations=0,SDK_target_compiler_calls=0,source_edits=0),
        implementation_authorized=False,live_adapter_qualified=False,execution_authorized=False,scientific_validation='not_established',recorder=pin(Path(__file__)))
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    text='''# Verifier adapter design: independent review

The architecture is suitable for a separately authorized **pure injected interface** stage. The [machine review](VERIFIER-ADAPTER-INDEPENDENT-DESIGN-REVIEW-v1.json) pins the original design and its [platform clarification](VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.md). This is a design critique, not source implementation, SDK qualification or live verification authority.

The same-owner origin/handoff is the right boundary: the entry starts its clock before helper reads/imports; the engine adopts that origin, output ownership, journal, early live leases and fresh captured bytes. No numeric restart, serialized ready flag, copied-original substitute or cross-run receipt is sufficient. Immutable captured bytes then feed every real checker. Application-level return registration, once-only cleanup and the nonfinal seal/final-clock rule preserve the earlier corrections.

The six read-stream APIs do not provide ancestry checking, finite run-root enumeration or a real output sink. The clarification now holds those as separate pending stages. It proposes attributes/search APIs with bounded rosters, an explicit end-of-directory/error distinction and search handles closed with `FindClose`. It also discloses that ctypes conversion precedes Python assignments: an unobserved native return remains unknown, and no atomicity or universal cleanup guarantee follows.

Before real platform binding, freeze the complete API/flags/layout/sentinel/closer census, including exclusive directory/file creation and write/flush/close. Derive the exact ancestor/scan/output call and event bounds; exhausted headroom is incomplete, not an excuse to omit records or increase limits. Do not supply these operations through hidden `Path`, `os.walk`, `scandir`, `rglob` or launch-SDK routes.

The finite source loader also needs an exact own-module/dependency map, relative-name rules and approved stdlib policy. Own helpers must load only from captured hash-matching bytes, with no ordinary fallback even to cached own `sys.modules` entries. Path discovery and traceback/linecache/inspect source reopening are outside the intended boundary. A real first-clock bootstrap and these loader guarantees remain implementation work.

Actual archive/universe/receipt/seal, journal/order, raw-resource/EOF/exit/cleanup and versioned profile checkers are still missing. The frozen Unicode corpus does not implement its new decoder, wire or runtime roster. Preserve the old failed189-case profile and its incomplete external verifier. Neither synthetic gates nor this design demonstrate actual300-second feasibility, full-mask/model quality or scientific validity.

No reviewed helper/test, original/source input, CPU/GGUF/pack, SDK, compiler or target operation ran during this review. The source-only design record grants no implementation or live permission; root decides the next bounded stage separately.
'''
    for target in re.findall(r'\]\(([^)]+)\)',text):assert (HERE/target).is_file()
    with NOTE.open('x',encoding='utf-8',newline='\n') as out:out.write(text)
    print(json.dumps(dict(status=value['status'],report=pin(REPORT),note=pin(NOTE))))
if __name__=='__main__':main()
