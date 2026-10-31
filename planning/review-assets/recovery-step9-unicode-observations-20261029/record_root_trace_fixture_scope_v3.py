"""Record approval for fictional observation fixtures, without validator code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json": "edacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f",
    "UNICODE-OBSERVATIONS-DESIGN-FREEZE-v2.json": "75093a117a4b196111bf1a5a6b2b555840413c2f0d12a483fee643b799f046f4",
    "UNICODE-OBSERVATIONS-INDEPENDENT-DESIGN-REVIEW-v2.json": "b815af2189b4bb03b521bd1539082507783f62c99369c19e3eb8c4a607c20950",
}
inputs = {}
for name, expected in EXPECTED.items():
    assert len(expected) == 64 and all(c in '0123456789abcdef' for c in expected)
    raw = (HERE / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected, (name, actual)
    json.loads(raw)
    inputs[name] = {"bytes": len(raw), "sha256": actual}
result = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "DESIGN_V2_ACCEPTED_FOR_FICTIONAL_COMPLETE_TRACE_FIXTURES_ONLY",
    "inputs": inputs,
    "root_scope": "Author and independently review literal synthetic positive, complete-negative and partial/fault JSONL histories from the exact 84-case profile before any observation validator implementation.",
    "required": [
        "All fifteen setup occurrences, 84 exact source before/result pairs, coverage/selection, deduplicated original-token prefixes, cleanup/batch/normal schedule",
        "At least one complete fictional positive trace with all required geometry classes; synthetic one-byte pieces alone cannot establish mixed coverage",
        "Explicit fictional PID/runtime/model descriptors, token IDs/pieces, native outcomes, counters and times; no actual observation claim",
        "Source-fixed coverage population, independently recomputed geometry and original-token prefix identity",
        "Negative, unavailable, conflict and partial/failure histories with exact independently authored expected projections and bounded fault locations",
        "Strict elapsed samples and terminal-failure grammar from v2; no success from marker presence, unknown cleanup or missing rows",
        "Freeze literal trace bytes, source references, all caps and expectations before source-validator implementation",
    ],
    "native_or_model_operations_authorized": False,
    "pack_file_creation_authorized": False,
    "validator_implementation_authorized": False,
    "old_original_or_archive_operations_authorized": False,
    "runtime_authorized": False, "profile_qualified": False,
    "originals_authenticated": False,
    "old_negative_and_timeout_unchanged": True,
    "next_gate": "Independent finite trace-fixture review followed by a separate root decision for a pure callback-bounded observation validator. Source/parent/resource/clock/provenance qualification remains external.",
}
output = HERE / "UNICODE-OBSERVATIONS-ROOT-TRACE-FIXTURE-SCOPE-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, sort_keys=True, ensure_ascii=False, indent=2)
    handle.write("\n")
raw = output.read_bytes()
print(json.dumps({"status": result["status"], "bytes": len(raw),
                  "sha256": hashlib.sha256(raw).hexdigest()}))
