"""Review the closed DATA design; no component or toy-helper execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


path = PHASE / "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json"
schema_pin = pin(path)
assert schema_pin["sha256"] == "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6"
schema = json.loads(path.read_text(encoding="utf-8"))
draft = json.loads((PHASE / "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-DRAFT-v1.json").read_text(encoding="utf-8"))
for name in ("proposal", "preserved_v1", "finite_precheck"):
    assert schema[name] == pin(Path(schema[name]["path"]))
assert schema["preserved_v1"]["sha256"] == "1de34a270ee1e05c268553c40977c73032be7f53fe356fea2730ad407b7526af"
assert schema["finite_precheck"]["sha256"] == "4c9b82ed1b5ed363331b737c2cf06d16c0ea32552d45679d1c0d195a4663a784"
assert schema["proposal"]["sha256"] == "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd"
root_scope = pin(PHASE / "SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json")
assert root_scope["sha256"].startswith("ba6328")
assert schema["baseline"] == draft["baseline"]
assert schema["baseline_event_order"] == draft["baseline_event_order"]
assert schema["required_gate_order"] == draft["required_gate_order"]
assert schema["qualification_exact"] == draft["qualification_exact"]
assert set(schema["qualification_exact"].values()) == {False}
packet_keys = ["schema_version", "kind", "scope", "status", "elapsed", "totals", "gates",
               "original_closures", "file_digests", "links", "qualification"]
row_keys = ["sequence", "event", "stage", "kind", "file_id", "module", "elapsed"]
assert schema["compact_publication_packet"]["exact_keys"] == packet_keys and len(set(packet_keys)) == 11
assert schema["serialized_journal_row"]["exact_keys"] == row_keys and len(set(row_keys)) == 7
assert not {"state", "return_observed", "acknowledged"} & set(row_keys)
assert set(row_keys) < set(schema["event"]["exact_keys"])
assert len(schema["packet_totals"]["exact_keys"]) == 8
assert "result_returned" not in schema["terminal"]["exact_keys"] and "result_issued" in schema["terminal"]["exact_keys"]
assert len(schema["diagnostic_phase_enum"]) == len(set(schema["diagnostic_phase_enum"]))
assert set(schema["test_seams"]) == set(draft["test_seams"])
assert schema["read_only_ref_surface"]["BufferRef"] == ["capacity"]
assert schema["read_only_ref_surface"]["FileRecordRef"] == ["id", "spec"]
assert schema["read_only_ref_surface"]["CallRef"] == ["ordinal", "api", "file_ref", "requested", "buffer_ref", "buffer_generation"]
weights = [1, 6, 6, 1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 4, 1, 2, 2, 2, 2, 2, 1, 2, 6, 2, 1]
assert len(weights) == len(schema["baseline_event_order"]) and sum(weights) == 53
assert schema["baseline"]["plan"] == {"N": 3, "B": 2, "M": 2, "R": 51, "C": 69, "E": 218}
assert schema["source_implementation_authorized"] is False
groups = [
    {"id": "result_issuance_and_finalization", "result": "resolved",
     "detail": "result_issued denotes the owner's committed frozen result, not measured caller receipt. Public bootstrap finalize accepts only incomplete; normal consistent/negative completion derives from controller-owned gates. Cached finalized state rejects later misuse without clock/error/counter/I/O mutation. Existing emit permits the in-flight postseal veto before final acknowledgment."},
    {"id": "raw_close_and_wrapper", "result": "resolved",
     "detail": "File close observation is explicitly derived from the raw signed32 CloseHandle scalar, independently of wrapper return. Nonzero scalar followed by wrapper failure stays known closed/once-consumed; unobserved remains null/unknown. Monotonic wrapper and raw-count facts remain separate."},
    {"id": "immutable_journal_and_callbacks", "result": "resolved",
     "detail": "Serialized rows have seven immutable keys and no own state/return/ACK. Registry observations may update after append without changing bytes. Callback defaults distinguish unprepared0/null, prepared-undispatched payload and returned/foreign/unknown ACK. Journal close consumes the no-more-append right before dispatch even when ACK is unknown; tip requires all known row ACKs and close ACK."},
    {"id": "diagnostic_phases_and_refs", "result": "resolved",
     "detail": "Finite diagnostic phases, exact read-only FileRecordRef/CallRef/BufferRef surfaces and canonical identity comparisons are declared. Immutable diagnostic token/text is separate from original exception getters. No copied fields, token or ready bool grants authority."},
    {"id": "strict_domains_and_compact_packets", "result": "resolved",
     "detail": "Integer counters/IDs/lengths reject bool/coercion and oversized conversions; flags are exact bool, times finite nonbool original-clock samples. Compact publication packets have exactly11keys/8totals keys, no raw ledger/paths/selfhash, and only earlier acknowledged links. Five kinds stay once-attempted/<=8192; no new public publication method is introduced."},
]
record = {
    "schema_version": 2, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_CLOSED_DATA_FOR_LITERAL_PREPARATION_ONLY",
    "reviewer": "/root/native_039_acceptance_audit", "author": "/root/os_accounting_peer",
    "scope": "Exact finite same-field public DATA closure review and root A/B/C callability choices. This is preparation metadata, not implemented behavior or final48 literal-history acceptance.",
    "schema": schema_pin, "preserved_draft": schema["preserved_v1"],
    "prior_precheck": schema["finite_precheck"], "proposal": schema["proposal"],
    "root_preparation_scope": root_scope,
    "roster_precheck": pin(PHASE / "SHARED-OWNER-HISTORY-ROSTER-INDEPENDENT-PRECHECK-v1.json"),
    "cohort_peer": pin(PHASE / "SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json"),
    "review_groups": groups, "material_blockers": [],
    "authored_baseline_unchanged": {"planned_injected_dispatches": 21, "planned_bytes": 209,
        "capacity_R": 51, "capacity_C": 69, "capacity_E": 218, "planned_journal_rows": 53,
        "no_actual_measurement_or_fit_claim": True},
    "closed_surfaces": {"compact_packet_keys": 11, "serialized_journal_row_keys": 7,
        "registry_event_keys": len(schema["event"]["exact_keys"]),
        "diagnostic_phase_count": len(schema["diagnostic_phase_enum"]),
        "reference_surfaces": ["FileRecordRef", "CallRef", "BufferRef"]},
    "required_coverage_limit": "The existing publication_attempt_or_size_cap history is explicitly structural/future SinkSpy coverage of produced <=8192B/once-kind packets. Isolated8193B or repeated-kind refusal is NOT exercised through a new publication API. No history/case count expansion or stronger coverage claim follows.",
    "composition_limit": "The seven-key serialized fictional journal has sequence and immutable-byte/ACK-prefix tip semantics only; it has no per-row prev/hash. This review does not establish a persisted hash chain, old/native runtime journal format or actual storage durability.",
    "next_gate": "Author and freeze final exact DATA-bound48 literal schedules/snapshots and their preparation checks, then independent whole-literal peer before any separately authorized three-source implementation.",
    "reviewed_components_or_toy_helpers_imported_or_executed": 0,
    "embedded_path_labels_opened": False, "actual_target_API_calls": 0,
    "old_original_payload_or_source_closure_operations": 0,
    "source_implementation_authorized_by_peer": False,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
    "retention_source": pin(Path(__file__).resolve()),
}
out = PHASE / "SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
md = """# Shared-owner public DATA v2: independent preparation peer

The closed successor resolves the finite precheck notes and root's A/B/C choices. No material blocker remains for literal preparation. The planned baseline remains 21 injected dispatches, 209 bytes, capacities R51/C69/E218 and 53 journal rows; these are authored expectations, not measurements.

Result issuance is separate from caller receipt. Public bootstrap finalization accepts only incomplete, while normal completion derives internally from controller gates. Raw CloseHandle facts remain independent of wrapper return. Seven-key immutable journal payloads contain no own ACK/state; later callback facts stay in registry observations. Journal close consumes the no-more-append right before dispatch even if acknowledgment is unknown.

Finite diagnostic phases, exact read-only refs, strict numeric/time domains and callback prepared/attempt/return relations are explicit. Publication packets have eleven closed keys and refer only to prior acknowledged artifacts. No public publication method or extra history is added. The existing size-cap case checks produced packet shape/size/once behavior through the future SinkSpy; it does not exercise an isolated 8193-byte refusal.

The fictional journal tip covers acknowledged immutable bytes. It is not a persisted per-row hash chain or a qualified native/runtime format. No reviewed component or toy helper was executed, no embedded label was opened, and no actual API or old-original operation occurred. Final literal peer and any source implementation remain separately gated.

- [Exact DATA peer](SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json)
- [Closed schema](SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json)
- [Preserved precheck](SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PRECHECK-v1.json)
"""
md_path = PHASE / "SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.md"
with md_path.open("x", encoding="utf-8", newline="\n") as stream: stream.write(md)
print(json.dumps({"status": record["status"], "json": pin(out), "md": pin(md_path)}, sort_keys=True))
