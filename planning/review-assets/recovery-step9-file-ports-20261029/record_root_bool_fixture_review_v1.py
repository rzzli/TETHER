"""Retain a pre-fixture type-domain review, using only new schema bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "FILE-PORTS-FIXTURE-SCHEMA-v1.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "c8f2bb80662c8c1a13cf5b8ff7f96f19c406b7835c7f16c2d96aabff8e401b2b"
schema = json.loads(raw)
assert "BOOL returns are raw0/1 ints" in schema["step_union"]["raw_semantics"]
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PRE_FIXTURE_TYPE_DOMAIN_CLARIFICATION_REQUIRED",
    "input": {"file": "FILE-PORTS-FIXTURE-SCHEMA-v1.json", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
    "finding": "The schema limits BOOL return fixtures to raw0/1. The accepted design already declares signed32 BOOL; the relevant APIs define success by nonzero. A future implementation tested only against0/1 could reject valid noncanonical nonzero returns or erase their raw value.",
    "evidence": [
        {"url": "https://learn.microsoft.com/en-us/windows/win32/winprog/windows-data-types", "basis": "BOOL is declared as int in WinDef.h; source read through official documentation only."},
        {"url": "https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile", "basis": "ReadFile return semantics define success as nonzero and failure/pending as zero; this design only opens synchronous files."},
    ],
    "required_correction": "Preserve schema-v1, make a separately frozen narrow schema-v2 signed32 raw-BOOL domain and add literal +2/-1 success and invalid-type/range controls before fixture freeze. Preserve raw values and distinguish strict Python bool from exact FFI integer representations. No API or design scope expansion.",
    "port_implementation_exists": False, "fixture_suite_frozen": False,
    "Win32_API_calls": 0, "old_original_payload_operations": 0,
    "runtime_authorized": False, "profile_qualified": False,
    "review_scope": "Fixture fidelity only; not a reproduced platform/production defect or actual qualification.",
}
output = here / "FILE-PORTS-ROOT-BOOL-DOMAIN-REVIEW-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
