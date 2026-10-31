"""Retain a finite metadata-only independent design review; no target access."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(r"D:/Projects/drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-role-aware-producer-20261029"
EXPECTED = {
    "planning/review-assets/recovery-step9-role-aware-producer-20261029/ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v1.json": "cce5dbedd166ff58e2182deb2ada8afcf5a165a6c0413e9245f4490d987e7512",
    "planning/review-assets/recovery-step9-role-aware-producer-20261029/RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json": "3a7e00e9cc812f7fcf0676c70704c65ab35565cac4b6a652fe06fad42c890c75",
    "planning/review-assets/recovery-step9-role-aware-producer-20261029/PROSPECTIVE-NEW84-KNOWN-RESOURCE-SUBSET-v1.json": "458a289c807dc2db6082a1f74b7f3dbda131ad660d2541de8372630b516d72f9",
    "planning/review-assets/recovery-step9-role-aware-producer-20261029/ROLE-AWARE-PRODUCER-DESIGN-EVIDENCE-INDEX-v1.json": "d41df29f2e0c702a02b9b6b0ff5fb5cad783f322bfa85d888e5e5b08018802c7",
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-FRESH-INPUT-PASS-v1.json": "04eff7fb2274a13130c8bc6ee639d57cb3362d7761f2ae96c1e084d97b06fb49",
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json": "e42cfda8a76c0784883c5d3dd1f695fd6e10c4d60b9c85685bfc2aba2a89922c",
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-EXECUTION-CONTRACT-v1.json": "30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861",
    "planning/review-assets/recovery-step9-unicode-wire-20261029/UNICODE-WIRE-DESIGN-CONTRACT-v2.json": "ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc",
    "planning/review-assets/recovery-step9-unicode-wire-20261029/UNICODE-WIRE-FRAMING-CONTRACT-v1.json": "4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24",
}
data = {}
pins = []
for name, expected in EXPECTED.items():
    raw = (ROOT / name).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == expected, name
    pins.append({"path": name, "bytes": len(raw), "sha256": digest})
    data[Path(name).name] = json.loads(raw)

proposal = data["ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v1.json"]
historical = data["RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json"]
original_metadata = data["RECOGNITION-FRESH-INPUT-PASS-v1.json"]
subset = data["PROSPECTIVE-NEW84-KNOWN-RESOURCE-SUBSET-v1.json"]
assert len(historical["files"]) == len(original_metadata["records"]) == 213
for ordinal, (left, right) in enumerate(zip(historical["files"], original_metadata["records"])):
    assert left["ordinal"] == ordinal
    assert (left["path"], left["bytes"], left["sha256"], left["historical_role"]) == (
        right["path"], right["expected_bytes"], right["expected_sha256"], right["role"])
sizes = [row["bytes"] for row in historical["files"]]
assert sum(sizes) == 9017363392 and all(size > 0 for size in sizes)
chunks = []
for q in (65536, 1048576, 4194304):
    Q = sum(size // q + bool(size % q) for size in sizes)
    R = Q + 16 * len(sizes)
    C = R + 6 * len(sizes)
    chunks.append({"chunk_bytes": q, "Q": Q, "R": R, "C": C})
assert [(r["Q"], r["R"], r["C"]) for r in chunks] == [
    (137753, 141161, 142439), (8796, 12204, 13482), (2356, 5764, 7042)]
assert len(subset["resources"]) == 16
assert sum(row["bytes"] for row in subset["resources"] if row["role"] != "hash_only_bulk") == 712415
assert sum(row["bytes"] for row in subset["resources"] if row["role"] == "hash_only_bulk") == 8989020320
assert subset["full_roster"] is None and subset["module_graph"] is None and subset["physical_pack_exists"] is False

rep = proposal["representation"]
terms = rep["terms_at_profile_max"]
assert sum(item["bytes"] for item in rep["call_layout"]) == rep["call_record_bytes"] == 256
assert sum(terms["ledger_sections"].values()) == terms["one_ledger_bytes"] == 14800384
assert sum(terms["named_retained_payload_terms"].values()) == terms["named_retained_payload_sum"] == 60208650
assert 2 * (terms["N"] + terms["E"] + 32) == terms["D"] == 5056
assert 6 * terms["N"] + 2 * terms["B"] + 2 * terms["M"] + 192 == terms["E"] == 2240
assert 2 * terms["one_ledger_bytes"] + terms["journal_bytes"] + 5 * 8192 + 8192 + 8065024 + 2 * 65536 == terms["output_reservation_bytes"] == 40139776
assert terms["one_ledger_bytes"] > proposal["operational_profile_proposal"]["captured_file_max"]

findings = [{
    "id": "F1_PHASE_LIFETIME_AND_BYTE_CONSUMPTION",
    "severity": "required_precode_design_closure",
    "location": ["representation.capture", "representation.terms_at_profile_max", "serialization.ledger", "serialization.bounded_emission", "serialization.report", "operational_route.complete evidence"],
    "observation": "The output reservation includes separate candidate and terminal ledgers, while the named retained payload sum includes one canonical evidence table. The design does not yet close the exact lifetime/provenance of frozen candidate bytes, final terminal bytes and checker access while canonical facts change, or the maximum active hash/slice transient.",
    "concrete_boundary": {"one_ledger_bytes": 14800384, "captured_file_max": 8388608, "captured_total_max": 33554432, "two_ledgers_plus_child_structured_reservation": 37665792},
    "why_material": "Each maximum ledger exceeds the proposed captured-file cap. Two ledgers plus the child reservation exceed the proposed captured-total cap. Full artifact capture therefore cannot be presumed. Conversely, a manifest or iterator over mutable records is not immutable captured byte evidence. The 60,208,650 figure is a named retained encoded-payload sum, not a complete phase peak or checker-storage proof.",
    "bounded_resolution": "Retain v1 and close the phase lifetime table in a separate addendum: live canonical records versus immutable candidate/terminal outputs; exact in-memory versus streamed artifact retention; bounded transient/snapshot/section-reader storage; consumer evidence and provenance/refusal rules; path-pool ownership if final paths are reconstructed only from retained query frames. Keep physical writer/readback and their call reservations explicitly pending. Do not silently lift capture caps or substitute a digest/ready flag for bytes.",
    "scope_limit": "No RSS, timing, physical I/O or full-roster claim is requested. This is one representation/lifetime closure within the existing proposal, not a new runtime framework or feature family."
}]

record = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": "/root/native_039_acceptance_audit",
    "status": "HOLD_DESIGN_FOR_PHASE_LIFETIME_CLOSURE_ONLY",
    "proposal": pins[0],
    "pins": pins,
    "material_blockers": findings,
    "review_scope": "One finite design/metadata batch. No subject implementation, reviewed-module import or execution, target access or actual runtime qualification.",
    "checks": {
        "historical_vector_all_213_rows_equal_retained_metadata": True,
        "historical_positive_files": 213,
        "historical_bytes": 9017363392,
        "exact_conditional_chunk_arithmetic": chunks,
        "known_subset_resources": 16,
        "known_subset_captured_logical_bytes": 712415,
        "known_subset_hash_only_bytes": 8989020320,
        "logical_pack_bytes_not_physical_file": 37766,
        "call_record_sum_bytes": 256,
        "one_ledger_bytes": 14800384,
        "named_retained_encoded_payload_sum": 60208650,
        "output_reservation_bytes": 40139776,
        "role_state_context_raw_first_and_once_close_design": "No additional scoped blocker found: explicit not_requested versus captured zero-length, captured-only byte consumers/modules, all-file digest/query/call/close coverage, raw observedness before fallible work, canonical owned-close rights, late facts independent of acceptance.",
        "legacy_versioning": "Accepted indexed V3/DATA50ee/48 expectations remain immutable. Any projection is explicit harness-only and refuses hash-only cases.",
        "operational_route": "The proposal advances the actual 84-document route by identifying retained CPU/model resources, new84 metadata and logical pack, and explicitly missing first-entry/wrappers/producer/encoder/child/header/build/parent/protocol/new-format checker graph. Tiny N4 invariants cannot qualify those missing components."
    },
    "existing_next_gate_prerequisites_not_new_findings": [
        "Freeze exhaustive enum/bit/offset/length/overflow tables and independent literal framing before encoding implementation.",
        "Freeze new packet/report/ledger schema and exact conditional artifact/DAG rules; old v7 archive/journal policy cannot qualify the new84 protocol.",
        "Recompute a complete selected new84 roster and module graph; historical192 software and oldpack/16outputs are not inherited.",
        "Version the 1MiB formulas; the accepted 64KiB calculator remains unchanged and cannot certify new dimensions.",
        "Bind physical writer/flush/closure/readback operations and reservations separately before activation.",
        "Keep 300/295/5 owner and 117/120 child limits, 256MiB external gate and all runtime/native/science holds."
    ],
    "explicit_limits": [
        "Only named planning JSON metadata was read; embedded target paths were never followed.",
        "Historical fresh-pass labels and old acceptance claims are quoted historical metadata, not new freshness/source qualification.",
        "No arbitrary calculator coefficient is accepted as implemented representation or physical RSS proof.",
        "No 1MiB cap activation, 213-file admission, 3-pass whole-shard timing fit or actual84 runtime is established.",
        "Original failed189 profile remains consumed and failed; the prior external whole gate remains INCOMPLETE_TIMEOUT.",
        "No extra role/schema/case family is proposed beyond the single lifetime closure."
    ],
    "activities": {"metadata_only_retention": True, "subject_imports": 0, "subject_tests_or_probes": 0, "embedded_target_stat_open_hash": 0, "old_run_replay": 0, "Win32_FFI_SDK_native_compiler_calls": 0, "accepted_source_or_fixture_edits": 0},
    "qualification": {"source_implementation": False, "full_roster_admitted": False, "new84_runtime": False, "physical_IO": False, "real_entry": False, "real_FFI": False, "resource_fit": False, "scientific_validation": False},
    "retainer": {"path": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
}
json_path = PHASE / "ROLE-AWARE-PRODUCER-INDEPENDENT-DESIGN-REVIEW-v1.json"
md_path = PHASE / "ROLE-AWARE-PRODUCER-INDEPENDENT-DESIGN-REVIEW-v1.md"
text = """# Role-aware producer design — finite independent review

The exact proposal is held for one phase-lifetime closure before serialization source. No additional role, context, raw-first, query, once-close or operational-route blocker was found in this finite pass.

The 213 retained historical rows match the earlier metadata exactly. At 1 MiB their conditional Q/R/C counts are 8,796 / 12,204 / 13,482. The new16-resource subset declares 712,415 captured logical bytes and 8,989,020,320 hash-only bytes; its 37,766-byte pack is logical only. Neither vector is a complete admitted new84 roster.

The call record sums to 256 bytes. The proposed maximum ledger is 14,800,384 bytes, named retained encoded payload totals 60,208,650 bytes, and output reservation totals 40,139,776 bytes. Those sums reconcile. The lifetime of the live canonical table, immutable pre-close candidate, terminal ledger, checker section access and slice/hash transient needs an explicit phase table. Each ledger exceeds the proposed 8 MiB captured-file cap; two ledgers plus child artifacts exceed the 32 MiB capture-total cap. Full capture cannot be assumed, and an iterator or manifest cannot silently replace immutable byte evidence.

The route correctly names missing first-entry/wrapper, producer/encoding, new84 child/header/build/parent/protocol and source-closed checker composition work. Exact formats, writer reservations, complete selected roster and 1 MiB formulas remain prerequisites. N4 invariants are only the first gate. No cap activation, physical storage, RSS/time fit, source closure, native observation or scientific qualification follows. The consumed189 failure and external INCOMPLETE_TIMEOUT remain unchanged.

This reviewer read named planning JSON metadata only and did not follow embedded paths, import or execute reviewed components, replay tests, or alter accepted artifacts. The JSON record contains exact pins and the bounded closure.
"""
with json_path.open("x", encoding="utf-8", newline="\n") as out:
    json.dump(record, out, indent=2, sort_keys=True)
    out.write("\n")
with md_path.open("x", encoding="utf-8", newline="\n") as out:
    out.write(text)
for path in (json_path, md_path):
    raw = path.read_bytes()
    print(path.name, len(raw), hashlib.sha256(raw).hexdigest())
