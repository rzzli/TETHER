"""Accept fictional trace preparation and authorize only its pure validator."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json": "edacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f",
    "UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json": "cecd6aad28b91a526541ffc1694e5fa9e7c91749f8b920453316314319bf065b",
    "UNICODE-OBSERVATIONS-TRACE-FREEZE-v2.json": "d2c9ade61f3c619bb6d66bc92ba560ea3a5d8e297fcf06350dff4df62976c145",
    "UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v1.json": "64c1b9139faa55edbdb79ec4f628dba8969a66fc29d989360af594c0fde753d9",
    "UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v2.json": "8625e590c41e39c3ff5f2192bb35b0ac8fb4f436ee3625f87ba45ea247314d8f",
    "UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.json": "a22e3d7010978f25d16a9c549134a6866336617b5d99c83721cca19bac164804",
    "UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json": "f6a3c50437c2a75d38b94878aaa7083c24695b57ea2fac2c28e4f909850c32ad",
}
inputs, docs = {}, {}
for name, expected in EXPECTED.items():
    assert len(expected) == 64 and all(c in "0123456789abcdef" for c in expected)
    raw = (HERE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    inputs[name] = {"bytes": len(raw), "sha256": expected}
    docs[name] = json.loads(raw)
peer = docs["UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v2.json"]
assert peer["status"] == "CLEAR_NARROW_LITERAL_TRACE_PREPARATION_ONLY"
assert peer["prior_gap_resolved"] is True
assert peer["mixed_EOG"]["population_unchanged"] is True
assert peer["nonpopulation_QC_unknown"]["all_case_QC_complete"] is False
assert peer["observation_validator_implemented"] is False
proof = docs["UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v2.json"]
assert proof["status"] == "passed" and proof["tests"] == 6
assert not proof["errors"] and not proof["failures"]
result = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "FICTIONAL_TRACE_PREPARATION_ACCEPTED_PURE_VALIDATOR_IMPLEMENTATION_AUTHORIZED",
    "inputs": inputs,
    "accepted_preparation": "Six complete fictional histories, thirty-six unchanged literal mutation/partial scenarios, eleven callback exception families, a fixed117-ID simulated piece table, seven original and six supplemental encoding/formula checks, and independent full-plus-narrow review. All outcomes remain authored engineering expectations.",
    "source_scope": "Implement observe and typed require_complete_success from the exact v2 design, base/framing tables, accepted codecv2 and supplied-piece analyzer. Consume bytes/profile/immutable declared bindings only; perform no path/file/runtime operations.",
    "requirements": [
        "Validate exact setup/body/state schemas, order, types, counters, before/result write lag, source references, geometry, population, selectors, original-token prefix controls, cleanup and failure identities",
        "Rebuild source geometry through the accepted analyzer and deterministic pack binding through accepted codecv2; no arbitrary schema/matcher/analyzer stub or serialized ready flag",
        "Keep complete_success_consistent, complete_negative_consistent and partial_observation distinct; expose typed immutable results and bounded immutable error-prefix metadata",
        "Preserve valid geometry for token rejection and mixed EOG; source population never follows observed membership; nonpopulation unknown still prevents whole-case QC success",
        "Required callbacks outside every data-only catch; preserve exact BaseException identity including UnicodeError-family and interruption at first/middle/final check sites",
        "Exercise all six bases, thirty-six scenarios, first/middle/final eleven-family callback probes, typed-result rejection and nested mutation controls before independent source review",
        "No expected fixture data/case-specific selector drives behavior; supplementary cases were authored before validator code",
    ],
    "external_unqualified": "Declared runtime descriptors and reported module context are not supplied or authenticated by the codec. Original/source/owner/clock/parent/archive/resource/native/scientific gates remain independent and cannot be replaced by this checker.",
    "fixture_container_note": "The12,027,723-byte source fixture container stores multiple hex-encoded histories. Each runtime JSONL history retains its existing8MiB/row/footer bounds; no runtime cap is raised.",
    "pure_validator_implementation_authorized": True,
    "runtime_or_native_operations_authorized": False,
    "pack_file_creation_authorized": False,
    "old_original_or_archive_operations_authorized": False,
    "production_entry_or_engine_activation_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "originals_authenticated": False,
    "old_failures_and_all_prior_fixture_versions_preserved": True,
    "next_gate": "Freeze exact pure source and behavioral evidence, then obtain independent review before scoped acceptance or any later parent/child/integration work.",
}
output = HERE / "UNICODE-OBSERVATIONS-PREPARATION-AND-SOURCE-SCOPE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
