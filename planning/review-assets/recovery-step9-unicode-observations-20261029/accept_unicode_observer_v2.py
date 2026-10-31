"""Accept exact observer source/pure evidence without replaying a runtime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "unicode_observations_v2.py": "47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6",
    "unicode_observation_tables_v1.py": "009e46ee19e945575472afb5105e88fe708a38b30c2f1014bbf8f6549d76786d",
    "UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json": "66a57c7b3316e6791dbdcb645ca968338aa61f19f68962964bf96126c9d6ca70",
    "UNICODE-OBSERVATIONS-IMPLEMENTATION-FREEZE-v2.json": "f8afdc057976ac871bb8d27b75771a0c3332c66a17869e48be68006ded02c1e6",
    "UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v2.json": "eb6aad83d2f6a15592a9203c1bb3892331b3403608ac9ef5df0cb401eae18a23",
    "UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-AFTER-v2.json": "280b37501d99e8fd8ec20ceb5a317baf5edaf0aabb6f98df6cd2c70774a8c80d",
    "UNICODE-OBSERVATIONS-ROOT-BOUNDARY-AFTER-v2.json": "628834ca137cedfb11dfdd9ca29e3ec2cd3c05a892706971d62912bac4d08a2e",
    "UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json": "e6ebbb0fc2c9e237edad11c3d00b85c52e697db139730b0b0401a5d7f98d9282",
    "UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json": "cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b",
    "UNICODE-OBSERVATIONS-ROOT-CORRECTION-SCOPE-v2.json": "b39b0ef2876d50775a588cdc84ea9985f99225de5000933a59f43069223c82d1",
    "UNICODE-OBSERVATIONS-ROOT-TERMINAL-PHASE-CLARIFICATION-v2.json": "45300fb64d9958d5208804b35b8f2193c99652f7e710f195977ac370da74b72e",
}
inputs, docs = {}, {}
for name, expected in EXPECTED.items():
    assert len(expected) == 64
    raw = (HERE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    inputs[name] = {"bytes": len(raw), "sha256": expected}
    if name.endswith(".json"):
        docs[name] = json.loads(raw)
proof = docs["UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v3.json"]
assert proof["status"] == "passed" and proof["tests"] == 14
assert not proof["errors"] and not proof["failures"]
peer = docs["UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v2.json"]
assert peer["status"] == "CLEAR_SOURCE_PURE_ONLY_WITH_EXTERNAL_GATES_PENDING"
after = docs["UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-AFTER-v2.json"]
assert after["status"] == "passed"
root = docs["UNICODE-OBSERVATIONS-ROOT-BOUNDARY-AFTER-v2.json"]
assert root["status"] == "TWO_PURE_BOUNDARY_REGRESSIONS_PASS_ON_V2"
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "ACCEPTED_V2_SOURCE_PURE_UNICODE_OBSERVATION_VALIDATOR_ONLY",
    "inputs": inputs,
    "scope": "Callback-bounded caller-captured Unicode JSONL/marker consistency, immutable typed observations, exact source/state/counter/geometry/selection/cleanup checks and separate complete-success, complete-negative and partial classifications.",
    "author_methods": 14, "complete_fictional_histories": 6,
    "literal_scenarios": 36, "observe_callback_identity_vectors": 33,
    "strict_callback_identity_vectors": 22, "nested_type_mutations": 22,
    "independent_terminal_data_probes": 4, "root_boundary_regressions": 2,
    "four_corrected_guards": [
        "Bounded JSON integer data errors",
        "Phase-aware failure/marker terminal work and safe cleanup, including an in-flight prefix",
        "Supplied marker presence before row parsing",
        "Final original-caller check after result freezing",
    ],
    "prior_sources_harness_failures_and_before_proofs_preserved": True,
    "scope_limits": [
        "Declared paths/descriptors and reported module consistency authenticate no original file/image, loaded DLL, process or actual clock",
        "Optional module rejection diagnostic is bounded but opaque and remains partial/external pending",
        "Cross-case piece-ID and failure current_case diagnostics receive no new semantic rule beyond the accepted contract",
        "Raw bytes, declared sources and a typed consistent result cannot replace actual owner, journal, archive, resource or native profile gates",
    ],
    "actual_old_run_replay": False, "old_original_source_closure_qualified": False,
    "runtime_pack_file_created": False, "new_SDK_native_model_calls": 0,
    "production_activation": False, "originals_authenticated": False,
    "profile_qualified": False, "runtime_authorized": False,
    "scientific_validation": "not_established",
    "original_negative_and_timeout_unchanged": True,
    "remaining": [
        "Portable file-port source/fixture corrections and independent behavioral acceptance",
        "Same-origin owner/entry/loader/registry/output/engine continuation",
        "New Unicode child/parent source and exact new journal/archive/resource policies",
        "Separate real-file/native/masking/integrated-resource/scientific gates",
    ],
}
output = HERE / "UNICODE-OBSERVATIONS-SCOPED-ACCEPTANCE-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": record["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
