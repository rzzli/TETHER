"""Retain optional bridge design metadata only; never imports or tests subjects."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.json"
CHECK = HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-CHECK-v2.json"


def pin(path):
    path = Path(path).resolve()
    b = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


assert not OUT.exists() and not CHECK.exists(), "Retained successor already exists"
basis = json.loads((HERE / "NATIVE-BANK-TICKET-BRIDGE-BASIS-v1.json").read_bytes())
pins = basis["source_and_metadata_pins"]
checks = []
for name, item in pins.items():
    actual = pin(ROOT / item["path"])
    checks.append(dict(name="unchanged_basis/" + name, passed=actual == item))
refs = {name: pin(HERE / name) for name in (
    "NATIVE-BANK-TICKET-BRIDGE-BASIS-v1.json",
    "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v1.md",
    "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v1.json",
    "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-CHECK-v1.json",
    "NATIVE-BANK-TICKET-BRIDGE-INDEPENDENT-STATIC-REVIEW-v1.json",
    "NATIVE-BANK-PYTHON-SDK-PREREQUISITES-v1.json")}
checks += [dict(name="preserved_HOLD", passed=refs["NATIVE-BANK-TICKET-BRIDGE-INDEPENDENT-STATIC-REVIEW-v1.json"]["sha256"] == "d1d6a91bf4452552d9ee003efd32c17eae7bda66e026d655ca1af76127805f96"),
           dict(name="SDK_metadata_pin", passed=refs["NATIVE-BANK-PYTHON-SDK-PREREQUISITES-v1.json"]["sha256"] == "736be5dfa055b32de84f1f58a312765af7538c73569e2cd1b5c8995efb6e8021")]
proof = ROOT / "planning/review-assets/recovery-step9-entry-source5-20261030/NATIVE25-COMPONENT-PROOF-v5.json"
p = json.loads(proof.read_bytes())
checks.append(dict(name="source5_observation_pin", passed=pin(proof)["sha256"] == "757e9a88c262f476d7744dc227a4aab752fca17e810589ced4f12e33654f5551" and p["counts"] == dict(COMPONENT_PASS=43, DEFERRED_NOT_EXECUTED=4, STATIC_DECLARATION_ONLY=1)))
cases = [
    ("B01", "First EXECUTION/admitted allocation before output and earliest original reserve", "Same Core/store owns native array from first row; no Python canonical bank or migration."),
    ("B02", "AUTHORING external policy", "No payload/argument/ticket arrays, output, target, compilation or continuation."),
    ("B03", "Foreign identity or attempted backend replacement", "Refuse before target; exact Core/Origin/nonce/Registry/store bindings remain."),
    ("B04", "First committed CreateFile success then first handle-taking reserve", "Initialize exact derived usable handle before C3 register; target_generation1/actor derived."),
    ("B05", "prepare_input equal versus mismatched handle", "Equal validates without writes; mismatch stops uninvoked row and preserves header bytes."),
    ("B06", "Unknown/unregistered/NULL0/INVALID open handle", "Refuse handle-taking reserve before append; no close right fabricated."),
    ("B07", "Wrong target generation/actor/flags", "Positive FileState._native_generation1 and row/axis epoch1; no numeric caller authority."),
    ("B08", "Close consumption and failure before/after registration", "Source flag consumed once, API7 flag32; no second close/retry; fresh unrelated cleanup uses original clock."),
    ("B09", "First query/read with source generation0", "Native buffer epoch1 with exact query0/read1 identity, capacity and exporter."),
    ("B10", "Successful generation0 retirement then stale ticket/next generation", "Next source1/native2; old ticket cannot match or be consumed twice."),
    ("B11", "Source generation4294967294 and next/overflow/bool/subclass", "Last encoding4294967295; permanently retire boundary, no wrap/coercion or new row on overflow."),
    ("B12", "Unbuffered API versus present buffer", "Absent ID UINT32_MAX/generation0/capacity0; no present buffer native epoch0."),
    ("B13", "Registry append fault before/after observable append", "Retain genuine prepared/admitted distinction; no manufactured registration or retry."),
    ("B14", "pf14_initialize refusal", "Prepared/appended unregistered stopped row; no axis authority or invocation."),
    ("B15", "Injected ref-index publication interruption", "Initialized bytes/ref entry may remain, registered byte false until final publication; no healing."),
    ("B16", "Reservation accounting-index fault after registered", "Retain registered/uninvoked/stopped row; no target or retry."),
    ("B17", "Committed handle then conversion failure", "Cold committed_fact/handle/report sees same bank and entered state, no wrapper return; one fresh legal close."),
    ("B18", "All seven API scalar/error/count shapes", "Exact HANDLE64/DWORD32/signed BOOL bits, NULL versus unknown, raw error0 versus definition, count only independent committed axis."),
    ("B19", "Same-width wrong scalar/count kind or metadata corruption", "NATIVE_STATE_NOT_REPRESENTABLE; no changed bytes/cache/rights."),
    ("B20", "Every synthetic mutator, including equal value, hooks and native call-field setters", "UNQUALIFIED_BACKEND before any native mutation; prepare_input validation exception only."),
    ("B21", "Wrong private type/coercible numeric/subclass/overflow", "Reject before consumption/target; no __index__ or equality callbacks."),
    ("B22", "NativeArguments equal clone/wrong exact identity or mutated original dict", "Invoke requires ticket.arguments identity; native POD ignores later original mapping changes."),
    ("B23", "Replay after consumed success/native refusal/target or conversion failure", "No second target, no new ticket for the same ordinal."),
    ("B24", "Preparation/path/export/allocation failure", "No native entry; first actual C error triple retained before release/diagnostics; partial acquisition inventory retained."),
    ("B25", "Consumed wrapper attempt then C3 rejects before begin", "Wrapper attempt true, native entered false, no fabricated Python return or retry."),
    ("B26", "C-only fake LastError escape after scalar publication", "Retain exact available scalar/definition/raw states; no RAW_EXIT/count/completion upgrade. Label injected, not atomicity proof."),
    ("B27", "Already-instantiated sentinel conversion error", "First fetched type/value/traceback retained; same value identity restored after cleanup."),
    ("B28", "Unnormalized exception indicator", "Retain original type/value/traceback without normalization; distinguish later Python-created instance."),
    ("B29", "Prepared view followed by cleanup/return failure", "Retain identical prepared object and original error; wrapper_return remains false until actual Python caller observes return."),
    ("B30", "Secondary cleanup error", "Separate secondary triple; original triple survives and is restored with duplicate owned refs."),
    ("B31", "Read FALSE with initialized/count0 scratch", "Raw scalar/count may be known; no defined completion, bytes or progress; quarantine."),
    ("B32", "Read TRUE count0 versus oversized/unknown count", "Count0 defined zero completion but no positive progress; malformed count refuses bytes/progress."),
    ("B33", "Completed read then hash/copy/fold failure", "Known native count/completion preserved, optional caches/folds never repaired, buffer generation quarantined."),
    ("B34", "Successful three query frames", "Immutable raw copies8/8202/8, distinct defined spans8/2*(n+1)/8, checked terminator; unused tail not claimed API-written."),
    ("B35", "Query immutable-copy failure", "Capture staged/uncommitted, no frame commit, first error/quarantine retained; getters cannot finish copy."),
    ("B36", "Zero/one successful export and each unwind point", "Acquire/release matched at most once; release states0/1/2 explicit; no release while native-active or retry unacknowledged release."),
    ("B37", "GC attempt during active/prepared/conversion and explicit retirement", "External roots/C-stack refs retain objects, no free/unrecorded close; deferred clear/quarantine retained; exact traverse coverage."),
    ("B38", "Old view then later row; snapshot copy failure", "Immutable prior bytes, native-derived entered facts, partial noneligible snapshot with actual copied progress; no old snapshot substitution/healing."),
    ("B39", "Injected diagnostic staged or unobserved-nonzero cell", "Preserve exact bits/unknown state, refuse current native wire projection; explicitly label diagnostic injection rather than actual C3 interruption."),
    ("B40", "Positive NativeInput/physical14/real image request and capacity audit", "Remain unavailable; planned struct/cell/array/export/reference limits checked without resource/native/scientific overclaim.")]
roster = [dict(id=i, placement=where, required_observation=expect) for i, where, expect in cases]
planned = [dict(path=name, sha256=None, bytes=None, status="PLANNED_OPTIONAL_DEFERRED") for name in (
    "preflight_entry_kernel_v6.py", "preflight_native_bank_v1.h", "preflight_native_bank_v1.c",
    "native_bank_fake_targets_v1.c", "build_native_bank_v1.py", "native_bank_bridge_cases_v1.py",
    "run_native_bank_bridge_v1.py", "_preflight_native_bank_fake_v1.pyd", "_preflight_native_bank_original7_v1.pyd")]
data = dict(
    schema_version=2, status="PROPOSED_OPTIONAL_ENGINEERING_DEFERRED_PENDING_STUDY_NEED",
    authority="Root strategic reassessment defers native expansion. This preserves authoring only; no implementation/import/literals/build/native action authorization.",
    priority="Controlling R07 stop-native negative disposition and proportional R09 scientific comparison precede optional native-bank/physical14 work.",
    preserved_and_prerequisite_references=refs, unchanged_source_basis=pins,
    source5_context_at_authoring_start=dict(proof=pin(proof), observed_counts=p["counts"], acceptance="UNACCEPTED_PENDING_INDEPENDENT_ACTUAL_REVIEW_AND_ROOT_AT_AUTHORING_START", scope="source component only, not native integration"),
    readable_proposal=pin(HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.md"), planned_nodes=planned,
    resolved_design_choices={
        "B1": "Canonical committed file-open handle, actor, FileState._native_generation1 and flags before C3 initialization. prepare_input is validation-only. Registered byte publishes after exact ref entry. Preserve append/init/index failure states without retry.",
        "B2": "Source generation remains0-based; present native buffer epoch=source+1, source range0..4294967294. Row/axis epoch1 and target epoch1 separate. Overflow/retired/quarantined/stale refuses before reservation.",
        "B3": "RawCallStore row_registered/header_facts/axis/copy_row/native_entered/buffer_facts are backend neutral. Native CallState.invoked/buffer facts derive from native authority; cold reports never heal caches or invent wrapper return.",
        "B4": "All synthetic store/call/hook mutation routes reject in native mode, except input validation without writes. C3 owns raw/entry/exit; private C extension owns conversion/capture metadata."},
    clarified_choices={
        "C1": "First PyErr_Fetch into preallocated original triple before formatting/normalization/release/decref; restore duplicate owned refs and retain original triple; separate cleanup triple/prepared view.",
        "C2": "One active synchronous GIL-held ticket, explicit quiescence, once-only buffer release0/1/2, strong external/C-stack roots, complete GC traversal, deferred clear until explicit retirement; no finalizer handle close.",
        "C3": "Closed NativeArguments private type with copied exact typed POD, immutable admitted path/ref identities; invoke requires identical args object bound to ticket. All conversions before consumption; consumed dispatch never retries.",
        "C4": "Native defined completion requires actual C3 RAW_EXIT and valid scalar/count/export/generation. Query immutable-copy commit separate from defined span; failure quarantines and getters cannot finish it.",
        "C5": "Planned exact Arena176/Arguments136/Ticket256 fields, C preallocated instances and three C pointer arrays/registered bytes, inline Py_buffer80, input path8194 distinct output8202; actual sizeof/GC/allocator/process overhead unqualified."},
    native_enums=dict(buffer_ids=dict(query=0, read=1, absent=4294967295), call_epoch=1, file_target_epoch=1, conversion=dict(NOT_STARTED=0, ENTERED=1, OBJECT_PREPARED=2, FAILED=3), query_capture=dict(UNOBSERVED=0, STAGED_UNCOMMITTED=1, COMMITTED_CAPTURE=2), export_release=dict(NOT_ATTEMPTED=0, RELEASE_ENTERED=1, RELEASE_ACKNOWLEDGED=2)),
    planned_layout=dict(assumptions=dict(PyObject_HEAD=16, pointer=8, u32=4, u64=8, Py_buffer=80, WCHAR=2, normal_alignment=True), expected_struct_bytes=dict(Arena=176, Arguments=136, Ticket=256), no_actual_ABI_or_memory_proof=True),
    allocation_inventory=dict(Arena_count=1, PF14Cell_count="C", call_ref_slots="C", argument_ref_slots="C", ticket_ref_slots="C", registered_bytes="C", Arguments_count="C", Ticket_count="C", inline_Py_buffer_per_ticket=1, max_simultaneous_exports=1, path_workspace_bytes=8194, fixed_struct_payload_formula="176+C*(256+24+1+136+256)+8194", fixed_struct_payload_C92=70286, excludes="GC allocator headers/pools, source objects, boxed metadata/factory temporaries, exceptions/tracebacks, CRT/native stack/process overhead; no memory fit claim"),
    source_method_roster=["entry", "PreboundServices.__init__", "KernelState.__init__", "FileState.__init__", "BufferRef.__init__", "CallState.__init__/prepare/native read properties", "RawCallStore.__init__/allocate/register/_call", "RawCallStore neutral read methods", "RawCallStore synthetic mutators", "AdoptionHooks native mutation guards", "reserve_call", "committed_fact", "defined", "_BootstrapPrimitives._call/hash_capture", "_advance_buffer_generation", "raw_call_view", "_issue_snapshot", "NativeRawBackend"],
    build_policy=dict(interpreter="exact pinned local CPython3.11.15 release/full API x64", online_docs_current="3.11.18, not local ABI authority", CRT="explicit /MD for every linked translation unit", C3="fresh compile exact source; never reuse C79 /MT object or EXE", required_future_proof="preprocessed header/sizeof/staticassertions, exact compiler/CRT/objects/PE dependencies/listing/image/source/oracle/driver; separate one-shot binding"),
    precode_requirements=roster, independent_literal_freeze=False,
    unfinished_gates=["independent review of this optional v2, if study need reopens branch", "independent exact literals and fault schedules", "separate exact source-authoring scope", "actual kernel/native objects and lifecycle implementation", "actual ABI/build/compiled review", "separate first compiled fake-bridge runtime and independent review", "separate owned-D original7 fixture and real-linked extension", "positive leases/child/path/physical14/native-wire/resources/new84 remain outside scope"],
    activity=dict(subject_imports=0, subject_runs=0, native_actions=0, builds=0, original_or_model_reads=0, current_ten_doc_edits=0, metadata_author_helper_only=True),
    qualification=dict(implemented=False, independent_design_clear=False, native_bank=False, original7=False, NativeInput=False, physical14=False, memory_fit=False, scientific=False),
    owner_blockers_identified=[])
checks += [dict(name="exact_forty_unique_case_requirements", passed=[x["id"] for x in roster] == ["B%02d" % i for i in range(1, 41)]),
           dict(name="fixed_struct_payload_arithmetic", passed=176+92*(256+24+1+136+256)+8194 == 70286),
           dict(name="all_planned_hashes_unknown", passed=all(x["sha256"] is None and x["bytes"] is None for x in planned)),
           dict(name="all_four_joins_and_five_clarifications", passed=set(data["resolved_design_choices"]) == {"B1", "B2", "B3", "B4"} and set(data["clarified_choices"]) == {"C1", "C2", "C3", "C4", "C5"})]
text = (HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.md").read_text(encoding="utf-8")
checks += [dict(name="explicit_optional_deferral_and_scoped_status", passed=all(x in text for x in (data["status"], "R07", "not an implementation", "No native expansion"))),
           dict(name="no_unfinished_author_draft_marker", passed="provisional192" not in text and "author-draft" not in text)]
assert all(x["passed"] for x in checks), [x for x in checks if not x["passed"]]
with OUT.open("xb") as f:
    f.write((json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8"))
result = dict(schema_version=2, status="PASS_AUTHOR_METADATA_CHECK_ONLY_OPTIONAL_DEFERRED", proposal=pin(OUT), readable=pin(HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.md"), helper=pin(__file__), counts=dict(checks=len(checks), failed=0, required_cases=40, planned_nodes=len(planned), source_basis_pins=len(pins)), checks=checks, qualification="Author metadata arithmetic/pins only; no independent design clearance, literal freeze, implementation, import, build or runtime")
with CHECK.open("xb") as f:
    f.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(dict(proposal=pin(OUT), readable=pin(HERE / "NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.md"), author_check=pin(CHECK), counts=result["counts"])))
