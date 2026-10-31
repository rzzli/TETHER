"""Authorize the independently reviewed exact fixture successor, not a runtime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
expected = {
    "PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json": "c30fbddf1019dee9a457705ec2553d0662b6555ae5a753a6bab7aeecd51dfc22",
    "PORTABLE-FILE-PORTS-CORRECTION-INDEPENDENT-REVIEW-v2.json": "d280210e7cc639a2898b8be0f669d52a6929bc43d4864e054c6525d4db575254",
    "PORTABLE-FILE-PORTS-SOURCE-CHOICE-REVIEW-v1.json": "9f00a14375d87734f985d217ac3fb5add5c4e93a720604ffaebb2519fd4d6eae",
    "portable_file_ports_v2.py": "b7785bd67b461f41ae7beeb1ce2e3b1a8bd0f210ba875eae61aaa25732425aed",
    "PORTABLE-FILE-PORTS-SOURCE-FREEZE-v2.json": "cfb8c8ea21214732ad085804b1e64444ebdcb9795ccf08241696738c15771e55",
}
inputs = {}
for name, digest in expected.items():
    assert len(digest) == 64
    raw = (here / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    if name.endswith(".json"):
        json.loads(raw)
    inputs[name] = {"bytes": len(raw), "sha256": digest}
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "EXACT_REVIEWED_FIXTURE_SUCCESSOR_PUBLICATION_AUTHORIZED",
    "inputs": inputs,
    "scope": "Publish a separately named literal fixture successor applying the exact c30 proposal: thirteen repaired scripts, eighteen changed cases and sixty-six unchanged cases. Preserve the original case set, raw API outcomes, fault injections and explicit advancing times.",
    "allowed_changes": [
        "Insert required same-origin clock/no-op log checkpoints without removing real work guards",
        "Complete the coherent namespace/reservation prefix with known bytes and retained partial slots",
        "Preserve first write failure as primary and close failure as secondary",
        "Use reviewed known-vs-unknown and root-spelling diagnostics without changing admission rejection or byte observations",
        "Keep primitive seed identity assumptions explicit and harness-only under the separately guarded test capability; never mint production identity from a serialized flag",
    ],
    "required_after_publication": "Hash/freeze the exact literal data and interface, run all84 cases through b778 portable behavior (zero script mismatches) and retain the focused21-method proof. Obtain final independent source/fixture verification before any acceptance.",
    "source_guards": "Identity before content, entered unreturned write counts, and entered/defined read counts across pre-dispatch deadline/malformed return boundaries are required. Existing source/before/proposal evidence stays unchanged.",
    "source_acceptance": False,
    "fixture_publication_authorized": True,
    "real_FFI_or_live_file_operations_authorized": False,
    "production_entry_or_engine_activation_authorized": False,
    "old_original_or_payload_operations_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "originals_authenticated": False,
    "no_changes_to_default_application_or_disabled_SDK": True,
}
output = here / "PORTABLE-FILE-PORTS-ROOT-FIXTURE-PUBLICATION-v4.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
