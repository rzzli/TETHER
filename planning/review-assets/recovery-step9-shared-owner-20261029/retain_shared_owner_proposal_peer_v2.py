"""Exact finite five-clause design review; no reviewed helper imports/execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    return json.loads((PHASE / name).read_text(encoding="utf-8"))


proposal_path = PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json"
proposal_pin = pin(proposal_path)
assert proposal_pin["sha256"] == "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd"
md_pin = pin(PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.md")
assert md_pin["sha256"] == "8a6d3b4179dde1f607e0f85d5e831e9d3c7b91304ee348598d094a27def48dc7"
old, proposal = load("SHARED-OWNER-CONTINUATION-PROPOSAL-v1.json"), load(proposal_path.name)
assert pin(PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v1.json")["sha256"] == "ed72dbb98842f3daa61e4bc89e5619335bed6e3226546016acd87ffd6146f953"
assert pin(PHASE / "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v1.json")["sha256"] == "68ed430031b8f6c6aeccca23dda480b42c43e51950cde8b684f963f4c14fcece"
verified = []
for item in proposal["accepted_source_pins"] + [proposal["author"], proposal["interface_note"], proposal["raw_core_acceptance"], proposal["synthetic_input_cohort"], proposal["preserved_v1"], proposal["v1_peer_hold"]]:
    actual_path = Path(item["path"])
    assert actual_path.resolve().is_relative_to(PHASE.parent.resolve())
    assert pin(actual_path) == item
    verified.append(item)
for name in ("accepted_source_pins", "context_rule", "copied_algorithm_obligation", "decision",
             "incompatible_interfaces", "later_bindings", "required_gates", "qualification",
             "synthetic_input_cohort", "typed_refusals", "unchanged"):
    assert old[name] == proposal[name], name
assert old["joint_caps"]["first_batch"] == proposal["joint_caps"]["first_batch"]
assert old["joint_caps"]["source_global_ceilings_retained"] == proposal["joint_caps"]["source_global_ceilings_retained"]
assert old["joint_caps"]["derived"][:3] == proposal["joint_caps"]["derived"][:3]
assert set(old["proposed_files"]) == set(proposal["proposed_files"]) == {"shared_owner_v1.py", "shared_file_ports_v1.py", "continue_verification_v1.py"}
assert [x["id"] for x in old["pure_fixture_matrix"]] == [x["id"] for x in proposal["pure_fixture_matrix"]]
assert len(proposal["pure_fixture_matrix"]) == 14
active = ["CreateFileW", "GetFileType", "GetFileInformationByHandleEx", "GetFinalPathNameByHandleW", "GetFileSizeEx", "ReadFile", "CloseHandle"]
inactive = ["GetFileAttributesExW", "FindFirstFileExW", "FindNextFileW", "FindClose", "CreateDirectoryW", "WriteFile", "FlushFileBuffers"]
assert proposal["active_original_API_subset"] == active and proposal["inactive_exports"] == inactive
assert not set(active) & set(inactive) and len(set(active + inactive)) == 14
kinds = {"candidate": "verification-candidate.json", "cleanup": "original-lease-cleanup.json",
         "failure": "failure.json", "receipt": "receipt.json", "seal": "terminal-seal.json"}
assert proposal["publication_protocol"]["kinds"] == kinds
assert proposal["pre_open_admission"]["signature"] == "SharedOwner.admit_plan(full_specs, early_paths, module_rules)"
assert proposal["test_factory_binding"]["signature"] == "continue_once(continuation, request, test_authority_factory, test_checker_factory)"
assert set(proposal["qualification"].values()) == {False}
R, C, E = 4 * 17, 6 * 4 + 4 * 17, 6 * 4 + 2 * 2 + 2 * 2 + 64 + 128
retained_frames = 4 * (8 + 8202 + 8)
raw_payload = 65536 + 8202 + retained_frames + 16384
assert (R, C, E, retained_frames, raw_payload) == (68, 92, 224, 32872, 122994)
assert raw_payload <= 131072
five_kind_output = E * 1024 + 5 * 8192
eight_record_upper = E * 1024 + 8 * 8192
assert five_kind_output == 270336 and eight_record_upper == 294912 and eight_record_upper <= 524288
groups = [
    {"id": "active_modeled_domain", "verdict": "resolved",
     "detail": "Seven active original-file APIs and seven inactive exports are exact disjoint sets. Byte-count cases are ReadFile only. Hook call/owner/generation/first-fact/error/phase authority is explicit; injected normal return transfers no handle/count. Fictional sink acknowledgments prove no physical WriteFile/flush/file-close/durability facts."},
    {"id": "raw_buffer_budget", "verdict": "resolved",
     "detail": "One read work buffer, one query work buffer, bounded retained identity frames and mutable capture assemblies share a preallocation ledger. Exact worst declared payload122994B fits131072B; immutable final captures have a separate16KiB cap. No68-frame allocation. Generations advance only after fold/hash/capture commit; pending/failed/unknown slices retain storage and forbid future read/reuse."},
    {"id": "closed_output_kinds", "verdict": "resolved",
     "detail": "Five named kinds are closed, at most one attempt each including failure/unknown, <=8192B. Eight is upper/slack rather than three invented extra kinds. Candidate/cleanup/optional failure precede journal closure; receipt/seal are registry-only after close. Afterseal errors stay in memory; no retry, overwrite, reopened journal or posthard callback."},
    {"id": "joint_admission_before_early_open", "verdict": "resolved",
     "detail": "admit_plan(full_specs,early_paths,module_rules) validates and reserves the full provisional descriptor and joint resource plan before output reservation or any original open. The later fixture authority must match that exact tuple/IDs and current early live records without growth/reset/reopen. Resource admission is distinct from completed authority/hash gates."},
    {"id": "factory_and_loader_binding", "verdict": "resolved",
     "detail": "The marker-chain loader uses unchanged209B bytes and current early live sources. Authority/checker factories are explicitly fixture-only trusted branded injections bound to this owner/nonce/EvidenceContext/stage. They are not loaded from the marker chain and establish no real source/checker qualification. Missing/foreign brands refuse."},
]
record = {
    "schema_version": 2, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_SOURCE_DESIGN_FOR_LITERAL_FIXTURE_PREPARATION_ONLY",
    "reviewer": "/root/native_039_acceptance_audit", "author": "/root/os_accounting_peer",
    "scope": "Exact finite five-clause successor review against original ed72, peer HOLD68ed and the root's minimal design choices. No integration implementation or helper execution.",
    "proposal": proposal_pin, "proposal_md": md_pin,
    "prior_proposal": proposal["preserved_v1"], "prior_hold": proposal["v1_peer_hold"],
    "cohort": proposal["synthetic_input_cohort"],
    "cohort_peer": pin(PHASE / "SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json"),
    "verified_NEW_basis_pins": verified, "review_groups": groups,
    "material_blockers": [],
    "preserved_scope": {"canonical_owner_from_beginning": True, "source_files": 3, "causal_groups": 14,
                        "cohort_bytes": 209, "accepted_source_pins_and_pending_real_gates_unchanged": True,
                        "N": 4, "B": 2, "M": 2, "S": 0, "R": R, "C": C, "E": E,
                        "work_seconds": 295, "hard_seconds": 300},
    "arithmetic": {"retained_query_frames_bytes": retained_frames,
                   "raw_payload_cap_derivation_bytes": raw_payload, "raw_storage_ceiling_bytes": 131072,
                   "separate_immutable_capture_ceiling_bytes": 16384,
                   "five_active_kind_plus_rows_reservation_bytes": five_kind_output,
                   "eight_record_upper_plus_rows_bytes": eight_record_upper,
                   "modeled_output_ceiling_bytes": 524288,
                   "not_measured_process_memory_or_actual_roster_fit": True},
    "scope_precedence": "The explicit v2 test_factory_binding and qualification fields govern the first cohort. Inherited 'source-bound' wording under continuation exclusions describes a pending real binding and does not qualify the branded injected test factories/checkers.",
    "next_gate": "Freeze concrete synthetic fake-binding/publication schedules over the unchanged209B cohort, then obtain separate root authorization before implementing the three proposed source files. No real binding or broader framework is authorized by this review.",
    "reviewed_modules_imported_or_executed": 0, "embedded_path_labels_opened": False,
    "actual_target_API_calls": 0, "old_payload_pack_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "originals_authenticated": False, "real_checkers_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
    "retention_source": pin(Path(__file__).resolve()),
}
out = PHASE / "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v2.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
md = """# Shared-owner proposal v2: independent design peer

The exact five-clause successor is clear for literal fixture preparation only. No material blocker remains in this finite batch. The canonical owner, three proposed files, 14 causal groups, unchanged 209-byte cohort and all pending real qualification gates are preserved.

The active domain is seven original-file APIs with ReadFile counts; the other seven exports remain inactive. The fictional sink records attempt/ack/unknown callbacks and claims no physical output bytes, flush, close or durability. Five named publication kinds each have one attempt and an 8192-byte bound; eight records remains conservative slack. Receipt/seal observations stay outside the closed journal and postseal errors remain in memory.

Full provisional descriptor and joint budget admission now precedes output reservation and early opens. Later authority corroborates that exact plan without growth or counter reset. One read buffer and bounded query/retained/capture storage have an explicit reserve-before-allocation/reuse protocol: the declared raw payload upper bound is 122994 bytes within 131072, with immutable captures separately capped at 16KiB. This is arithmetic, not measured process or production resource fit.

The unchanged marker helpers test only their closed captured-byte loader. Authority/checker callbacks are explicitly fixture-only branded injections, separate from those helpers. The explicit v2 factory contract governs this cohort; inherited source-bound wording does not establish real factory/checker qualification.

Next are concrete synthetic schedules and separately authorized source implementation. No reviewed helper was imported or executed, no embedded path label was opened, and no actual API, old payload or source-closure operation occurred. Real FFI first-store capture, first-entry provenance, production continuation and runtime/profile qualification remain pending.

- [Exact peer record](SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v2.json)
- [Reviewed proposal](SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json)
- [Preserved prior HOLD](SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v1.json)
- [Cohort preparation peer](SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json)
"""
md_path = PHASE / "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v2.md"
with md_path.open("x", encoding="utf-8", newline="\n") as stream: stream.write(md)
print(json.dumps({"status": record["status"], "json": pin(out), "md": pin(md_path)}, sort_keys=True))
