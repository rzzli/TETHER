"""Retain the exact F1-only design delta review; never follow metadata targets."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(r"D:/Projects/drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-role-aware-producer-20261029"
EXPECTED = {
    "ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v1.json": "cce5dbedd166ff58e2182deb2ada8afcf5a165a6c0413e9245f4490d987e7512",
    "ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v2.json": "0460eb2df71b393670b2cc386155e4ee960ceff2d1e873730eaa37f97cebf462",
    "ROLE-AWARE-PRODUCER-F1-DESIGN-ADDENDUM-v2.json": "b1405e2d9f349a109a70647936c1d7a861923b26e8390dc7b56886e2427abedc",
    "ROLE-AWARE-PRODUCER-INDEPENDENT-DESIGN-REVIEW-v1.json": "f06480b0efee0a74a0897e891bd07ce1acd9ad612b81dec1beebc2096cdf3972",
    "RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json": "3a7e00e9cc812f7fcf0676c70704c65ab35565cac4b6a652fe06fad42c890c75",
    "PROSPECTIVE-NEW84-KNOWN-RESOURCE-SUBSET-v1.json": "458a289c807dc2db6082a1f74b7f3dbda131ad660d2541de8372630b516d72f9",
}
data = {}
pins = []
for name, expected in EXPECTED.items():
    raw = (PHASE / name).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == expected, name
    data[name] = json.loads(raw)
    pins.append({"path": str((PHASE / name).relative_to(ROOT)).replace("\\", "/"), "bytes": len(raw), "sha256": sha})

old = data["ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v1.json"]
new = data["ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v2.json"]
add = data["ROLE-AWARE-PRODUCER-F1-DESIGN-ADDENDUM-v2.json"]
top_changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
assert top_changed == {"status", "root_selected_F1_scope", "serialization", "correction_basis", "representation", "preserved_proposal", "F1_unchanged_dimensions", "schema_version"}
rep_changed = {key for key in set(old["representation"]) | set(new["representation"]) if old["representation"].get(key) != new["representation"].get(key)}
assert rep_changed == {"capture", "paths", "terms_at_profile_max", "freeze_failure", "freeze_lifetime", "generated_bytes", "journal_packet_report_lifetime", "transient_rule"}
serial_changed = {key for key in set(old["serialization"]) | set(new["serialization"]) if old["serialization"].get(key) != new["serialization"].get(key)}
assert serial_changed == {"artifacts", "bounded_emission", "ledger", "out_bytes", "readback", "store"}
unchanged = sorted(set(old) - top_changed)
for key in unchanged:
    assert old[key] == new[key]
terms = new["representation"]["terms_at_profile_max"]
artifacts = new["serialization"]["artifacts"]
assert len(artifacts) == len({item["kind"] for item in artifacts}) == 14
assert artifacts == add["artifact_caps"]
assert sum(item["maximum_bytes"] for item in artifacts) == terms["generated_store_bytes"] == terms["output_reservation_bytes"] == 40139776
assert sum(terms["ledger_sections"].values()) == terms["one_ledger_bytes"] == 14800384
assert terms["ledger_sections"] == old["representation"]["terms_at_profile_max"]["ledger_sections"]
assert sum(terms["named_retained_payload_terms"].values()) == terms["named_retained_payload_sum"] == 113985546
assert terms["named_retained_payload_sum"] - terms["named_retained_payload_terms"]["one_capture_assembly"] == terms["phase_sums"]["healthy_generated_phase_after_original_assembly_release"] == 105596938
assert old["representation"]["terms_at_profile_max"]["named_retained_payload_sum"] - 2342912 + 40139776 + 14800384 + 1048576 + 131072 == 113985546
assert set(terms["named_retained_payload_terms"]) == {"canonical_evidence_tables", "generated_immutable_store", "hash_or_slice_transient", "immutable_capture", "one_capture_assembly", "one_generated_artifact_assembly", "path_comparison_workspace", "query_work_buffer", "read_buffer", "serializer_work"}
assert add["generated_store_bytes"] == 40139776 and add["named_payload_conservative_bytes"] == 113985546
assert add["structured_child_bytes"] == 8065024 and add["independent_capture_stream_bytes"] == 131072
assert sum(item["maximum_bytes"] for item in artifacts if item["kind"].startswith("child/")) == 8065024
assert sum(item["maximum_bytes"] for item in artifacts if item["kind"] in ("stdout.bin", "stderr.bin")) == 131072
assert old["current_n4"] == new["current_n4"]
assert old["operational_profile_proposal"] == new["operational_profile_proposal"]
assert old["role_policy"] == new["role_policy"]
assert old["transitions"] == new["transitions"]
assert old["versioning"] == new["versioning"]

record = {
    "schema_version": 2,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": "/root/native_039_acceptance_audit",
    "status": "CLEAR_DESIGN_F1_LIFETIME_CLOSURE_ONLY",
    "material_blockers": [],
    "proposal": pins[1],
    "pins": pins,
    "scope": "Exact F1 phase-lifetime/byte-consumption correction only. This metadata review closes the single f064 HOLD family and does not authorize implementation, physical output, full-roster admission or runtime.",
    "prior_finding_disposition": {
        "id": "F1_PHASE_LIFETIME_AND_BYTE_CONSUMPTION",
        "status": "resolved_at_design_level",
        "reason": "The generated artifact universe and immutable-byte store are separate from original captured inputs. Canonical tables, candidate and terminal snapshots, one generated assembly, hash/slice transient and path workspace have explicit distinct lifetimes and bounds. Byte-consuming checkers receive complete actual immutable bytes, not iterators, digests, ACKs or reported counts. Failed/unissued/late/quarantined states cannot mint positive evidence."
    },
    "independent_metadata_checks": {
        "top_level_delta_keys": sorted(top_changed),
        "representation_delta_keys": sorted(rep_changed),
        "serialization_delta_keys": sorted(serial_changed),
        "unchanged_top_level_sections": unchanged,
        "closed_artifact_count": 14,
        "artifact_caps": artifacts,
        "generated_store_bytes": 40139776,
        "one_ledger_bytes": 14800384,
        "original_capture_total_bytes": 33554432,
        "original_capture_file_and_assembly_max_bytes": 8388608,
        "one_generated_artifact_assembly_max_bytes": 14800384,
        "hash_or_slice_transient_max_bytes": 1048576,
        "path_workspace_bytes": 131072,
        "named_payload_terms": terms["named_retained_payload_terms"],
        "conservative_named_payload_bytes": 113985546,
        "healthy_generated_phase_named_payload_bytes": 105596938,
        "removed_duplicate_journal_packet_report_bytes": 2342912,
        "structured_child_bytes": 8065024,
        "separate_stdout_stderr_bytes": 131072,
        "no_changes_to_historical_vector_or_subset": True,
        "no_changes_to_N4_roles_chunk_caps_limits_legacy_oracle_or_operational_missing_route": True
    },
    "reviewed_lifetime_and_evidence_rules": [
        "The same canonical owner/origin/nonce/registry issues a non-owning GeneratedArtifactContext holding actual immutable bytes. It is separate from original InputContext.blobs and cannot promote hash-only originals.",
        "Live canonical facts remain allocated. Candidate freezes pre-close facts and terminal freezes final-close facts in distinct byte objects that cannot alias mutable tables, an assembly or each other. Later closes cannot change candidate bytes.",
        "Each closed artifact has at most one attempt/issued object. Missing, partial and unissued artifacts remain explicit; only eligible fully frozen bytes reach positive consumers.",
        "Freeze validation occurs under the original owner clock. Known late returns remain observed but ineligible. Failure latches the original exception, never retries favorably, and keeps canonical facts and close rights.",
        "A failed/unissued assembly is released before another build when safely known; unknown release retains/quarantines that single assembly and stops another build.",
        "One original-path UTF8 pool is counted. Final-path evidence remains in complete retained UTF16 query frames; one reserved path workspace handles comparisons without another per-file decoded pool.",
        "Store-owned journal, packet and report bytes are not duplicated in the named payload sum. Structured child artifacts and stdout/stderr are separate bounded entries.",
        "Original capture limits are unchanged. Generated ledgers do not bypass those limits as oversized originals; they have a distinct closed store and consumer source-binding requirement."
    ],
    "prerequisites_unchanged": [
        "Exact raw-cell provenance, enum/bit/offset/length/numeric/clock representations and independent literal framing remain to be frozen before implementation.",
        "Complete selected new84 roster, module graph, byte-consumer graph and versioned legacy projection remain required; the historical213 vector and16-resource subset are not new admission.",
        "The prospective1MiB formula/representation remains distinct from the accepted64KiB calculator and unchanged indexed N4 source.",
        "Physical same-handle writer/flush/close/readback, their call reservations and real first-entry/FFI bindings remain explicitly missing.",
        "The distinct84 child/header/pack/build/parent/protocol and new exact archive/journal/resource/semantic composition remain missing; old189 source policies cannot substitute.",
        "The113,985,546 sum covers named encoded payload only. Python/interpreter/exception/module/native memory, measured RSS and timing remain outside this proof;256MiB and all clock gates remain external qualifications."
    ],
    "activities": {"metadata_only": True, "reviewed_component_imports": 0, "subject_probes_or_tests": 0, "embedded_target_stat_open_hash": 0, "old_run_replay": 0, "Win32_FFI_SDK_native_compiler_calls": 0, "accepted_artifact_edits": 0},
    "qualification": {"design_F1_closed": True, "implementation": False, "full_roster_admitted": False, "physical_IO": False, "real_entry": False, "real_FFI": False, "resource_fit": False, "new84_runtime": False, "scientific_validation": False},
    "retainer": {"path": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
}
out_json = PHASE / "ROLE-AWARE-PRODUCER-INDEPENDENT-DESIGN-REVIEW-v2.json"
out_md = PHASE / "ROLE-AWARE-PRODUCER-INDEPENDENT-DESIGN-REVIEW-v2.md"
prose = """# Role-aware producer — exact F1 design closure

The single phase-lifetime finding is resolved at the design level. The accepted N4 source, roles, caps, clocks, legacy oracle, historical vector and prospective missing-component route are unchanged. This verdict permits no implementation or activation by itself.

The separate generated immutable-byte store has fourteen explicit artifact caps totaling 40,139,776 bytes. Candidate and terminal ledgers are distinct immutable snapshots, separate from live canonical first-fact tables; byte-consuming checkers must receive and consume their actual complete bytes. An iterator, digest, ACK or ready flag cannot replace that evidence. Missing, failed, late and unissued states remain negative or incomplete. Original captured inputs retain their 32 MiB total and 8 MiB per-file limits.

The revised named payload sum is 113,985,546 bytes, including the live table, generated store, one 14,800,384-byte generated assembly, one 1 MiB hash/slice transient and a 128 KiB path workspace. The healthy generated phase after known original-assembly release totals 105,596,938 bytes; the higher bound remains reserved. Journal, packet and report bytes already in the store are not counted twice. All artifact sums and the exact delta were independently recomputed from metadata.

These are encoded storage terms, not measured heap/RSS or a time-fit proof. Exact field framing, source implementation, complete new84 roster and consumer graph, physical writer/readback reservations, real first-entry/FFI and the new child/parent/protocol remain separate gates. The original consumed189 failure and external timeout are not repaired. This reviewer performed metadata comparisons and arithmetic only, with no reviewed-component execution or target operations.
"""
with out_json.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
with out_md.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(prose)
for path in (out_json, out_md):
    raw = path.read_bytes()
    print(path.name, len(raw), hashlib.sha256(raw).hexdigest())
