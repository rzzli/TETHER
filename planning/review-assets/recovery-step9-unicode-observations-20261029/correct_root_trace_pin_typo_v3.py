"""Preserve the failed approval helper and correct its transcribed SHA only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
old = here / "record_root_trace_fixture_scope_v2.py"
raw = old.read_bytes()
misspelled = b'"dacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f"'
correct = b'"edacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f"'
assert raw.count(misspelled) == 1
assert not (here / "UNICODE-OBSERVATIONS-ROOT-TRACE-FIXTURE-SCOPE-v2.json").exists()
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "ROOT_APPROVAL_HELPER_STOPPED_BEFORE_PUBLICATION",
    "failure": "Root transcribed 63 hex characters, omitting the first e of the contract SHA. Exact hash assertion stopped the helper with exit1; no approval record was published.",
    "failed_helper": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
    "expected_typo": misspelled.decode()[1:-1], "actual_contract_sha256": correct.decode()[1:-1],
    "design_source_or_fixture_changed": False, "runtime_operations": 0,
    "correction": "Separately named helper corrects only the literal pin and adds a 64-hex length assertion. The failed helper is retained unchanged.",
}
with (here / "UNICODE-OBSERVATIONS-ROOT-PIN-FAILURE-v2.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
new = raw.replace(misspelled, correct).replace(
    b"for name, expected in EXPECTED.items():\n",
    b"for name, expected in EXPECTED.items():\n    assert len(expected) == 64 and all(c in '0123456789abcdef' for c in expected)\n",
)
with (here / "record_root_trace_fixture_scope_v3.py").open("xb") as stream:
    stream.write(new)
print("Retained root pin failure; created separately named corrected metadata helper.")
