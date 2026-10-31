"""Bind the finite four-guard source correction, without rerunning probes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
expected = {
    "unicode_observations_v1.py": "58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0",
    "UNICODE-OBSERVATIONS-IMPLEMENTATION-PURE-PROOF-v2.json": "dba9ce192bb126532290b5b033c9b6cbb686c1d5d3bd267205830704941170f5",
    "UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json": "e6ebbb0fc2c9e237edad11c3d00b85c52e697db139730b0b0401a5d7f98d9282",
}
inputs = {}
for name, digest in expected.items():
    assert len(digest) == 64
    raw = (here / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    inputs[name] = {"bytes": len(raw), "sha256": digest}
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "FOUR_GUARD_SOURCE_V2_CORRECTION_AUTHORIZED_NOT_ACCEPTED",
    "inputs": inputs,
    "required_corrections": [
        "Convert bounded genuine JSON integer-conversion failures into ObservationError with immutable prefix metadata; never catch/relabel caller callbacks",
        "Apply the after84 known-cleanup-only delta rule to marker-only terminal snapshots as well as completed failure rows",
        "Latch supplied failure-marker presence before profile or row data parsing can produce prefix diagnostics",
        "Check the original caller after final result issue/freezing and before return; preserve exact callback exception identity",
    ],
    "required_validation": "Preserve v1 and all initial/harness/full/before proofs. Add regression-first before/after tests for the same four cases, rerun the meaningful full fixture/callback/type/immutability suite, freeze separately named v2 and obtain exact independent re-review.",
    "not_new_normative_rules": [
        "Cross-case tokenID to piece mapping was fixture-fidelity preparation; no new production validation rule in this correction",
        "Bounded failure current_case diagnostics are not newly reconstructed; optional opaque module diagnostics remain explicitly partial/external pending",
    ],
    "retained_pure_dependency": "Reuse of recognition_module_policy_v1.py5031f2e3 as a single isolated pure lexical matcher is permitted. This is not a renewed original-run source closure, file/image authentication or runtime qualification. No old payload paths or extra dependencies are followed.",
    "SDK_native_payload_or_old_run_operations_authorized": False,
    "profile_qualified": False, "runtime_authorized": False,
    "source_implementation_correction_authorized": True,
    "source_acceptance": False,
}
output = here / "UNICODE-OBSERVATIONS-ROOT-CORRECTION-SCOPE-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
