"""Retain finite proposal review and arithmetic; never import reviewed helpers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


path = PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v1.json"
proposal_pin = pin(path)
assert proposal_pin["sha256"] == "ed72dbb98842f3daa61e4bc89e5619335bed6e3226546016acd87ffd6146f953"
proposal = json.loads(path.read_text(encoding="utf-8"))
assert len(proposal["proposed_files"]) == 3 and len(proposal["pure_fixture_matrix"]) == 14
verified = []
for item in proposal["accepted_source_pins"] + [proposal["author"], proposal["interface_note"], proposal["raw_core_acceptance"], proposal["synthetic_input_cohort"]]:
    actual_path = Path(item["path"])
    assert actual_path.resolve().is_relative_to(PHASE.parent.resolve())
    assert pin(actual_path) == item
    verified.append(item)
md_pin = pin(PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v1.md")
assert md_pin["sha256"] == "edd1387f650666d46a19717407252c048d22f2e1efcf016e45aa0e3fdb9e5d57"
cohort_peer = pin(PHASE / "SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json")
assert cohort_peer["sha256"] == "40adfa21e53f2d67dba648ed069f4d577c48afb5df10f86df8e0bc4ee4fee481"
first = proposal["joint_caps"]["first_batch"]
assert first == {"B_max": 2, "M_max": 2, "N_max": 4, "S": 0, "captured_bytes_max": 16384,
                 "file_bytes_max": 4096, "original_slots_max": 4}
R = 4 * (1 + 16)
C, E = 6 * 4 + R, 6 * 4 + 2 * 2 + 2 * 2 + 64 + 128
assert (R, C, E) == (68, 92, 224)
baseline_R, baseline_C, baseline_E = 3 * 17, 6 * 3 + 3 * 17, 6 * 3 + 2 * 2 + 2 * 2 + 64 + 128
assert (baseline_R, baseline_C, baseline_E) == (51, 69, 218)
output_reservation = 224 * 1024 + 8 * 8192
assert output_reservation == 294912 and output_reservation <= 524288
assert 68 * 4096 > 131072 and 68 * 65536 > 131072
issues = [
    {"id": "active_modeled_domain", "severity": "required_before_fixture_or_code",
     "basis": "FilePortView activates only seven original-file APIs and the fictional sink returns acknowledgments, while late_count/budget cases mention WriteFile/short writes and terminal order claims write/flush/close observations.",
     "required_closure": "Declare exactly which first-batch effects are modeled. Prefer keep the seven-API original subset and label sink acknowledgments as abstract fictional publication outcomes, with no raw write-count/flush/physical-close evidence. Restrict the first fixtures accordingly; actual WriteFile/physical sink remains a later explicit gate. Do not infer namespace ownership or physical completion from an acknowledgment outside its declared synthetic contract."},
    {"id": "raw_buffer_budget", "severity": "required_before_fixture_or_code",
     "basis": "R can reach68 and the proposal retains failed/unknown/pending generations under an aggregate131072-byte raw-buffer ceiling, but does not bound allocation/reuse across those generations and identity frames.",
     "required_closure": "Specify finite preallocated frame capacities/counts, serial allocation/reuse eligibility, release/retention rules, and a stop rule preventing fresh work after a retained failed/unknown generation. Joint admission must account for all retained identity/read frames and separately bounded immutable captures. Enforce the aggregate before allocating; merely bounding generation count byR does not prove fit."},
    {"id": "closed_output_kinds", "severity": "required_before_fixture_or_code",
     "basis": "publish(kind,...) says closed eight nonjournal kinds, but those kind names and exact publication/once rules are absent.",
     "required_closure": "Enumerate the eight fixed names, per-kind once/byte limits, reservation/journal membership and failure/late/afterseal behavior. Define candidate/cleanup/journal-tip/receipt/seal dependencies and source-issued acknowledgment binding. Terminal artifacts after journal close must remain registry-only and may never reopen that journal."},
    {"id": "joint_admission_before_early_open", "severity": "required_before_fixture_or_code",
     "basis": "The proposal requires joint admission before original opens, but its early entry takes only early specs; the full request/authority is introduced later in match_full_roster/continue_once.",
     "required_closure": "Provide the immutable provisional full descriptor/early/module plan and joint ceilings before the first early open, with lexical role/alias/size/capture and derived-budget rejection then. Later authority may corroborate or reject that exact admitted request; it must not silently expand/reset it. Keep delayed semantic authority separate from early bounded resource admission."},
    {"id": "factory_and_loader_binding", "severity": "required_before_fixture_or_code",
     "basis": "The frozen209-byte cohort exposes only marker()/run(), while continuation accepts authority_factory/checker_factory and describes source binding.",
     "required_closure": "Choose explicit trusted fixture-only branded injected authority/checker handlers for this first cohort, with real factory/source/checker binding pending, while testing the captured marker-chain loader separately. Specify their owner/Origin/context identity and lifecycle/signatures. Do not mutate the cohort/add factory source or let arbitrary callbacks/ready dictionaries assert source binding. Clarify synthetic mode success versus refused real-checker mode."},
]
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "HOLD_FOR_FIVE_FINITE_PROPOSAL_CLOSURES",
    "canonical_owner_choice": "COHERENT_DESIGN_CHOICE_ONE_OWNER_FROM_BEGINNING",
    "reviewer": "/root/native_039_acceptance_audit", "author": "/root/os_accounting_peer",
    "scope": "Independent design-only interface/arithmetic/causal review of the exact proposed three-source integration. No new integration implementation, fixture schedule, reviewed-helper import or runtime execution.",
    "proposal": proposal_pin, "proposal_md": md_pin, "cohort_peer": cohort_peer,
    "verified_NEW_basis_pins": verified,
    "coherent_choices": [
        "One new bootstrap-successor owner/Origin/nonce/registry starts the future synthetic cohort; no legacy object upgrade or numeric restart.",
        "Ports and controller are non-owning views; old run_once, owner constructors, independent finally/cleanup and repeated output reservation are excluded.",
        "EarlySourceContext and loader retain exact immutable early bytes and current live slot provenance; EvidenceContext unions remaining captures without early reopen/rehash.",
        "Raw first facts, field watermarks, immutable diagnostics, once-only close and original primary/known late facts are copied as algorithms requiring new actual-method regressions.",
        "One original295/300 clock and one event ledger; terminal candidate/cleanup/tip/receipt/seal/final acknowledgment order and no posthard sink calls remain explicit.",
        "Pure-seam consistent/negative outcomes keep all real-source/checker/FFI/runtime/profile flags false; the old timed-out experiment is neither repaired nor replayed.",
    ],
    "arithmetic": {"ceilings": {"N": 4, "B": 2, "M": 2, "S": 0, "R": R, "original_call_records_C": C, "event_rows_E": E},
                   "cohort_baseline": {"N": 3, "B": 2, "M": 2, "R": baseline_R, "C": baseline_C, "E": baseline_E},
                   "row_and_eight_output_reservation_bytes": output_reservation,
                   "modeled_output_cap_bytes": 524288,
                   "buffer_fit_established": False,
                   "retaining_68_4096B_frames_alone": 68 * 4096,
                   "retaining_68_65536B_frames_alone": 68 * 65536,
                   "arithmetic_is_not_actual_roster_resource_fit": True},
    "material_blockers": issues, "finite_batch_complete": True,
    "next_gate": "Retain this exact proposal; separately version only these finite design closures for peer/root review. Concrete synthetic schedules then precede separately authorized source implementation. No broader framework or real binding expansion is requested.",
    "reviewed_helpers_imported_or_executed": 0, "embedded_cohort_paths_opened": False,
    "actual_target_API_calls": 0, "old_payload_pack_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "originals_authenticated": False, "real_checkers_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
    "retention_source": pin(Path(__file__).resolve()),
}
out = PHASE / "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v1.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": record["status"], "record": pin(out)}, sort_keys=True))
