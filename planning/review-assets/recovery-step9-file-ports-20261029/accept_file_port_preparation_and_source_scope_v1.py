"""Accept frozen fictional tests and authorize only portable source logic."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "FILE-PORTS-DESIGN-CONTRACT-v2.json": "d2c775cb9e24dce90f2dc0cc97d7976567d94a1e147e1f57be72f7a5d21efd4d",
    "FILE-PORTS-FIXTURE-SCHEMA-v3.json": "e3069b89cca7e9b04c630de994f24392054daf341c280f50778aea3d0f81657b",
    "FILE-PORTS-FIXTURES-v3.json": "9e445e2e230689aa7c36e7eba666959dcac87478caf27252154eb02e978109b7",
    "file_port_fixture_script_v2.py": "d6ec279a90b5424d30a2239a7305d04b8cbd059dbff6bbf3107c4cfb9c503e51",
    "FILE-PORTS-FIXTURE-CALLABLE-PROOF-v2.json": "6df42b04e9c21fa22c9ee398dfb72b55c0c57b691144f9717288cc193ec8d094",
    "FILE-PORTS-FIXTURE-CALLABLE-FREEZE-v2.json": "1a47880ade1119bae93c1b242238d9d2d9b012c784a9513f86120a16ceac2bd0",
    "FILE-PORTS-FIXTURE-INDEPENDENT-PEER-v3.json": "c8a46dde6753141909d560d0558c2ea6cc68881bae6689078c9af00e50ccd22c",
}
inputs, docs = {}, {}
for name, expected in EXPECTED.items():
    assert len(expected) == 64 and all(c in "0123456789abcdef" for c in expected)
    raw = (HERE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    inputs[name] = {"bytes": len(raw), "sha256": expected}
    if name.endswith(".json"):
        docs[name] = json.loads(raw)
peer = docs["FILE-PORTS-FIXTURE-INDEPENDENT-PEER-v3.json"]
assert peer["status"] == "CLEAR_FICTIONAL_FIXTURE_PREPARATION_ONLY"
assert peer["checks"]["cases"] == 84 and peer["checks"]["required_families"] == 16
assert peer["checks"]["independent_byte_and_close_disagreements"] == 0
assert peer["actual_FFI_raw_registration_qualified"] is False
proof = docs["FILE-PORTS-FIXTURE-CALLABLE-PROOF-v2.json"]
assert proof["methods"] == 10 and not proof["errors"] and not proof["failures"]
assert proof["port_implementation_under_test"] is False
result = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "FICTIONAL_PREPARATION_ACCEPTED_PORTABLE_SOURCE_IMPLEMENTATION_AUTHORIZED",
    "inputs": inputs,
    "accepted_preparation": "84 authored cases across sixteen fault families, a limited primitive composition baseline and fifteen signed-BOOL controls; ten fake interchange checks and independent literal arithmetic/schema review. These are not observed port outcomes.",
    "source_implementation_scope": "Implement coherent portable file/read/metadata/output ownership and deadline logic against injected raw returns, fake calls and clocks. Exercise the frozen scripts through this logic and compare independently authored outcomes. Keep guards, plan derivations and bounded publication logic explicit.",
    "implementation_requirements": [
        "The component under test must not read fixture files, expected results, case IDs or fault-name selectors to derive behavior",
        "Register observed ownership and known byte counts before post-call callbacks, copies, hashes or formatting; retain unknown side effects and do not invent close rights",
        "Preserve raw signed32 BOOL values and infer success by nonzero; reject malformed types/ranges",
        "Keep namespace ownership distinct from readiness, retain partial slots and avoid recursive journal accounting",
        "Respect original clock, known late immutable data and distinct once-only file/search closers; dispatch no API after the hard cutoff",
        "Primitive test seeds are fictional harness preconditions, not serialized production authority; no real owner/source/profile readiness can be minted from a dict",
        "Freeze exact source, meaningful fault-test evidence and any failures for an independent peer before acceptance",
    ],
    "FFI_gap": "The fake RawReturn already exists when portable logic sees it. Actual FFI must separately register scalar handle/rawflag/count in shared preallocated owner slots immediately after conversion and before constructing RawReturn. Portable tests do not qualify that unimplemented boundary.",
    "pure_source_implementation_authorized": True,
    "real_binding_implementation_or_construction_authorized": False,
    "top_level_ctypes_or_SDK_import_authorized": False,
    "live_file_or_native_operations_authorized": False,
    "old_original_payload_or_archive_operations_authorized": False,
    "production_engine_or_entry_activation_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "originals_authenticated": False,
    "prior_negative_timeout_sources_and_fixture_failures_preserved": True,
    "next_gate": "Independent exact portable-source and behavioral review, followed by separate real binding/entry/source/resource/integration qualification. Existing launch SDK stays disabled.",
}
output = HERE / "FILE-PORTS-PREPARATION-AND-SOURCE-SCOPE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
