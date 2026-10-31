"""Record a bounded pre-implementation trace correction and coverage addition."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
name = "UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.json"
raw = (here / name).read_bytes()
assert hashlib.sha256(raw).hexdigest() == "a22e3d7010978f25d16a9c549134a6866336617b5d99c83721cca19bac164804"
json.loads(raw)
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "BOUNDED_TRACE_SUCCESSOR_AUTHORIZED_BEFORE_VALIDATOR",
    "peer_input": {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
    "confirmed_peer_gap": "The known all-EOG-false disagreement does not exercise the mixed-EOG union with null membership and retained valid geometry.",
    "correction": "Preserve every v1 artifact and author one coherent mixed-EOG negative history with exact existing union/reason, known cleanup, counters, null membership/matches and unchanged geometry/population.",
    "supplemental_coverage_not_new_peer_defects": [
        "Coherent ordinary-token rejection with full retained piece ledger/geometry, exact first-rejection spans and independently authored API/state deltas",
        "Nonpopulation QC-unknown with known population availability/selectors but incomplete all_case_QC and strict abstention",
    ],
    "reason_for_supplements": "These are existing closed design branches. Complete trace tests should exercise their distinct geometry, population and accounting behavior before the new validator is implemented. Identify an existing literal scenario if already covered; do not duplicate it.",
    "limits": "No new source cases, populations, runtime schemas, enum values, native behavior claim, observed-outcome selection or field-cap increase. Fixture containers are source assets, distinct from each capped runtime JSONL history.",
    "validator_implementation_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "old_original_or_native_operations_authorized": False,
    "required_next": "Freeze exact successor bytes/expected projections before code and obtain one narrow independent delta review.",
}
output = here / "UNICODE-OBSERVATIONS-ROOT-SUPPLEMENTAL-TRACE-SCOPE-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
