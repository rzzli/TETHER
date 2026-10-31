"""Check three current source decisions; never follows original/path descriptors."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
CASES = (
    ("recovery-step9-archive-bytes-20261029", "CAPTURED-ARCHIVE-CHECKER-SCOPED-ACCEPTANCE-v3.json"),
    ("recovery-step9-file-ports-20261029", "FILE-PORTS-ROOT-FIXTURE-SCOPE-v1.json"),
    ("recovery-step9-unicode-observations-20261029", "UNICODE-OBSERVATIONS-ROOT-TRACE-FIXTURE-SCOPE-v2.json"),
)
results, count = [], 0
for directory, basename in CASES:
    location = ASSETS / directory
    raw = (location / basename).read_bytes()
    decision = json.loads(raw)
    assert decision["runtime_authorized"] is False
    assert decision["profile_qualified"] is False
    assert decision["originals_authenticated"] is False
    verified = []
    for name, pin in decision["inputs"].items():
        # A closed local input map, not a descriptor/path walker or source closure.
        assert re.fullmatch(r"[A-Za-z0-9_.-]+", name) and name.endswith((".json", ".py"))
        assert set(pin) == {"bytes", "sha256"}
        assert type(pin["bytes"]) is int and 0 <= pin["bytes"] <= 2 * 1024 * 1024
        assert type(pin["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
        source = (location / name).read_bytes()
        assert len(source) == pin["bytes"]
        assert hashlib.sha256(source).hexdigest() == pin["sha256"]
        verified.append(name)
        count += 1
    results.append({"decision": f"{directory}/{basename}", "sha256": hashlib.sha256(raw).hexdigest(), "verified_input_names": verified})
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Exact current root decision interfaces and their direct local new-source input pins only. Not an original archive, runtime or transitive source qualification.",
    "decisions": results, "direct_local_input_pins": count,
    "original_path_descriptors_followed": False,
    "runtime_or_native_operations": 0, "profile_qualified": False,
}
output = HERE / "ROOT-NEW-SOURCE-APPROVAL-INTERFACE-QA-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "decisions": len(results), "local_input_pins": count,
                  "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
