"""Retain a source-only root decision; never imports or constructs file ports."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "FILE-PORTS-DESIGN-CONTRACT-v2.json": "d2c775cb9e24dce90f2dc0cc97d7976567d94a1e147e1f57be72f7a5d21efd4d",
    "FILE-PORTS-INDEPENDENT-DESIGN-REVIEW-v2.json": "d6c03181a6cd51222b9a7fcf4f96ef0e9f8a7e19d8f06c8c2377a397fe4d4582",
}
inputs = {}
for name, expected in EXPECTED.items():
    raw = (ROOT / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected, (name, actual)
    json.loads(raw)
    inputs[name] = {"bytes": len(raw), "sha256": actual}
contract = json.loads((ROOT / "FILE-PORTS-DESIGN-CONTRACT-v2.json").read_bytes())
semantic = contract["semantic_contract"]
assert len(semantic["required_fake_vectors"]) == 16
assert semantic["execution_authorized"] is False
assert semantic["implementation_authorized"] is False
result = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "DESIGN_PREPARATION_ACCEPTED_SYNTHETIC_FIXTURE_AUTHORING_ONLY",
    "inputs": inputs,
    "root_decision": "Proceed with finite fictional API/clock/ownership fixtures covering the sixteen required fault families plus a coherent success baseline. Freeze independently checkable inputs, expected results and call order before any port implementation.",
    "accepted_scope": [
        "Metadata-only drive roots with unchanged leaf and source-role rules",
        "Fourteen bounded file exports and declared ownership/deadline/output semantics as design",
        "Closed synthetic fixture schema and vectors under the existing project workspace",
    ],
    "required_fixture_properties": [
        "Explicit scripted fake returns, undefined buffers and expected call order",
        "Known ownership and byte counts distinguished from unknown or failed returns",
        "Namespace ownership separate from reservation readiness",
        "Once-only correct closer; no failed/unknown close retry",
        "Original clock preserved; no API after hard cutoff",
        "Late immutable write evidence retained without completed hash or positive pin",
        "Acyclic sealing and failure vetoes; no positive result from serialized readiness",
        "Every design fault family mapped to concrete fixture IDs",
    ],
    "required_next_gate": "Independent fixture review before a separate root decision authorizes a source-only implementation. Live platform qualification, real entry/engine integration and full resource/source qualification remain later gates.",
    "port_implementation_authorized": False,
    "ctypes_or_SDK_construction_authorized": False,
    "live_file_operations_authorized": False,
    "runtime_authorized": False,
    "originals_authenticated": False,
    "profile_qualified": False,
    "old_negative_and_timeout_unchanged": True,
    "actual_API_calls": 0,
    "old_original_payload_operations": 0,
}
output = ROOT / "FILE-PORTS-ROOT-FIXTURE-SCOPE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
raw = output.read_bytes()
print(json.dumps({"status": result["status"], "file": output.name,
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}))
