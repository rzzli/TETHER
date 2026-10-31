"""Accept injected portable behavior; no platform or runtime qualification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "portable_file_ports_v2.py": "b7785bd67b461f41ae7beeb1ce2e3b1a8bd0f210ba875eae61aaa25732425aed",
    "PORTABLE-FILE-PORTS-COMPONENT-FREEZE-v2.json": "d7fb7763921e53c508c8ae26f9aea15b727357e4aee1cfb0d9cc0015a6e4b44c",
    "PORTABLE-FILE-PORTS-SOURCE-FREEZE-v2.json": "cfb8c8ea21214732ad085804b1e64444ebdcb9795ccf08241696738c15771e55",
    "PORTABLE-FILE-PORTS-CORE-PURE-PROOF-v2.json": "bcc8a865c043135b7b9b734f75d17604f2486cf4b6cd11af091df3d8303ec0c1",
    "PORTABLE-FILE-PORTS-BEHAVIORAL-PROOF-v2.json": "246baec6c054e4c4063f1f1da9a89efa6d0e2c422bae547405915bc2ffdb96c2",
    "FILE-PORTS-FIXTURES-v4.json": "e1fd8d2161972fd5b64870d5ba9ad84fd5ed3d240973e5e111839556d7baf2a3",
    "PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.json": "56b57f3ce0f08770b8bbf16698adc64d6560e19d14e04239a976d0d09694132d",
    "PORTABLE-FILE-PORTS-INDEPENDENT-AFTER-v2.json": "7bad3fba79cb86c49d4e088aecf3ce498f2e95fb1ec45f4f1d9adc4bafea36bd",
    "PORTABLE-FILE-PORTS-ROOT-FIXTURE-PUBLICATION-v4.json": "c35f98026775de8e4faa9b5230b3ee8adf8e24707efe13e455b6553b26f0fb6f",
    "PORTABLE-FILE-PORTS-CORRECTION-INDEPENDENT-REVIEW-v2.json": "d280210e7cc639a2898b8be0f669d52a6929bc43d4864e054c6525d4db575254",
}
inputs, docs = {}, {}
for name, expected in EXPECTED.items():
    assert len(expected) == 64
    raw = (HERE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    inputs[name] = {"bytes": len(raw), "sha256": expected}
    if name.endswith(".json"):
        docs[name] = json.loads(raw)
core = docs["PORTABLE-FILE-PORTS-CORE-PURE-PROOF-v2.json"]
assert core["status"] == "PASS" and core["tests"] == 21
assert not core["errors"] and not core["failures"]
behavior = docs["PORTABLE-FILE-PORTS-BEHAVIORAL-PROOF-v2.json"]
assert behavior["status"] == "PASS" and behavior["cases"] == behavior["matched"] == 84
peer = docs["PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.json"]
assert peer["status"] == "CLEAR_PORTABLE_INJECTED_SOURCE_PURE_ONLY"
assert docs["PORTABLE-FILE-PORTS-INDEPENDENT-AFTER-v2.json"]["status"] == "passed"
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "ACCEPTED_V2_INJECTED_PORTABLE_SOURCE_PURE_ONLY",
    "inputs": inputs,
    "scope": "Portable ownership, identity-before-content, known/unknown read/write accounting, once-only cleanup, metadata, deadline and bounded output/control logic against injected fake calls/returns and clocks.",
    "published_behavioral_cases": 84, "focused_author_methods": 21,
    "independent_source_probes": 9, "fake_API_attempts": 199,
    "fake_API_returns": 193, "script_mismatches": 0,
    "corrected_source_boundaries": [
        "Owner/nonce/slot/handle/path/spec identity witness before content read/write, regardless of a writable identity_ok flag",
        "Entered unreturned writes retain unknown counts and original interruption",
        "Read admission and raw-return validation distinguish no-dispatch, known bytes and undefined/malformed counts",
    ],
    "fixture_correction": "Exact separately reviewed proposal applied to13 scripts/18 cases;66 unchanged. Required clocks/hooks remain, coherent namespace prefix retained, primary stays first, admission failures and raw API outcomes are not weakened.",
    "preserved": "V1/first65-of84, intermediate pre-read source, all before probes, root metadata-helper failures, proposal/interchange proofs, prior literal versions and independent reviews remain unchanged.",
    "explicit_limits": [
        "Harness seed identity assumptions are fictional and require a separate ordinary source capability; no serialized production identity is granted",
        "Fake RawReturn already exists before portable logic sees it; actual raw FFI adoption before object allocation/error transport is unimplemented",
        "No live Windows file API, real first-entry clock, shared bootstrap/engine owner, actual source/capture/roster fit or integrated verifier is qualified",
        "Old known-v7 policies and pure Job/Unicode primitives do not qualify a new Unicode parent/runtime",
    ],
    "real_FFI_qualified": False, "actual_file_operations_qualified": False,
    "production_entry_or_engine_activated": False,
    "originals_authenticated": False, "profile_qualified": False,
    "runtime_authorized": False, "new_SDK_native_model_calls": 0,
    "old_original_or_payload_operations": 0,
    "scientific_validation": "not_established",
    "original_negative_and_timeout_unchanged": True,
    "next": "Specify/review shared-owner raw-FFI/first-entry/continuation interfaces and closed fault expectations, then qualify their separately versioned source and real mechanics before native or application activation.",
}
output = HERE / "PORTABLE-FILE-PORTS-SCOPED-ACCEPTANCE-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": record["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
