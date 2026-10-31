"""Accept seam design preparation and authorize only closed fictional faults."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
expected = {
    "FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json": "055db993a35f173d19a01c52c3b88515d97d3752d7dd409e1273b55f63c15cd6",
    "FILE-PORTS-ADOPTION-SEAM-FREEZE-v1.json": "f2d57dee6454c04dc2d3416e411b9c2a6bc69aab79db0ad131ec5be7fe769046",
    "FILE-PORTS-ADOPTION-SEAM-INDEPENDENT-PEER-v1.json": "7de66b427cb72c9ea6a631ce40dc328b087469f47307b866eb115060dc99eb85",
    "PORTABLE-FILE-PORTS-SCOPED-ACCEPTANCE-v2.json": "16d65f572019a86b466d684f5c67b330140de85362829abad7a19330ee4d318a",
}
inputs = {}
for name, digest in expected.items():
    assert len(digest) == 64
    raw = (here / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    json.loads(raw)
    inputs[name] = {"bytes": len(raw), "sha256": digest}
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "DESIGN_PREPARATION_ACCEPTED_LITERAL_ADOPTION_FIXTURES_AUTHORIZED",
    "inputs": inputs,
    "scope": "Freeze a bounded raw-adoption record/interface schema and literal inputs/expected states for the fourteen reviewed fault families and coherent success path before any successor implementation.",
    "requirements": [
        "Preallocated scalar/count fields distinguish UNOBSERVED from observed0 and observedNULL. Do not require a later auxiliary flag or multi-field update to preserve the first stored fact; disclose the remaining conversion/async window",
        "Separate invocation reservation, scalar/count observation and portable-wrapper return; no guessed measured C-entry census from a Python exception",
        "Known raw handle/count/close outcomes survive wrapper/error-copy/copy/clock failures under the same owner and once-only closer",
        "Counter folding and duplicate handling are idempotent by call ordinal; include interruption between first fact storage and later bookkeeping as a variant of the reviewed fault families",
        "Raw buffers and prepared immutable write slices retain their lifetimes when copy/hash cannot complete; no reuse or positive pin after unknown/late work",
        "Use typed same-owner/Origin/nonce/registry/output/source-context/loader/journal handoff, reject foreign/repeated claims and avoid run_once or renewed output reservation",
        "Bound records/buffers/events before dispatch; exact real roster, memory and time fit remain unproved",
        "Expected states are independently authored fictional facts, not results derived from the future implementation; source/role/production authority remains false",
    ],
    "fixture_directory": "planning/review-assets/recovery-step9-raw-adoption-20261029",
    "successor_source_implementation_authorized": False,
    "ctypes_or_actual_binding_construction_authorized": False,
    "real_file_or_native_operations_authorized": False,
    "old_source_closure_or_payload_operations_authorized": False,
    "production_entry_or_engine_activation_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "originals_authenticated": False,
    "next_gate": "Independent exact schema/literal-fault review, then a separate root decision for a portable source successor. Harmless actual binding/first-entry/source qualification remains later.",
}
output = here / "FILE-PORTS-ADOPTION-ROOT-FIXTURE-SCOPE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
