"""Clarify the existing terminal-delta correction without expanding its scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
expected = {
    "UNICODE-OBSERVATIONS-ROOT-CORRECTION-SCOPE-v2.json": "b39b0ef2876d50775a588cdc84ea9985f99225de5000933a59f43069223c82d1",
    "UNICODE-OBSERVATIONS-SOURCE-INDEPENDENT-PEER-v1.json": "5ebd57eff292ecf5c49abf7ae7d41c60598721f87c2673460cc53c59da1a96be",
}
inputs = {}
for name, digest in expected.items():
    raw = (here / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    inputs[name] = {"bytes": len(raw), "sha256": digest}
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PHASE_CLARIFICATION_WITHIN_FOUR_GUARD_CORRECTION",
    "inputs": inputs,
    "clarification": "The number84 alone does not prove all native work has completed. A declared next selected-prefix control may be in flight after all document cases. Use the validated phase to reconcile terminal deltas for both failure rows and marker-only snapshots.",
    "required": [
        "After completed work/full normal completion permit only the source-allowed safe cleanup deltas; reject new tokenize work",
        "During the next declared unfinished prefix permit only its bounded sampler/apply/accept/free work and safe known cleanup, with monotone attempted/returned counts and explicit unknown attribution",
        "Never infer a completed prefix, retokenize, permit a second unseen prefix or create a close right from an unknown return",
        "Unknown in-flight creation/release stays partial; complete-negative requires independently known clean source cleanup",
        "Retain a source-valid prefix-inflight regression alongside rejection of tokenize after full normal completion",
    ],
    "not_a_fifth_reproduced_defect": True,
    "no_new_runtime_schema_or_authority": True,
    "old_source_original_or_runtime_qualification": False,
    "profile_qualified": False, "runtime_authorized": False,
}
output = here / "UNICODE-OBSERVATIONS-ROOT-TERMINAL-PHASE-CLARIFICATION-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
