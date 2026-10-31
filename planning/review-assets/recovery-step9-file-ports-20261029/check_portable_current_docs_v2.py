"""Check current project docs at injected portable-source acceptance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Portable File Ports.md"
ASSESSMENT = "planning/" + NAME
DOCS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-r09-unicode-controls.md",
)
texts, pins = {}, {}
for relative in DOCS:
    raw = (ROOT / relative).read_bytes()
    texts[relative] = raw.decode("utf-8", "strict")
    pins[relative] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
text = texts[ASSESSMENT]
rows = re.findall(r"^\| (R\d\d|HR\d) \|", text, re.M)
assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
assert re.findall(r"^([1-5])\. ", text, re.M) == list("12345")
links = []
for wrapped, bare in re.findall(r"\]\((?:<([^>]+)>|([^\s)]+))\)", text):
    target = wrapped or bare
    if target.startswith(("http://", "https://", "#")):
        continue
    path = ((ROOT / ASSESSMENT).parent / unquote(target.split("#", 1)[0])).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), target
    links.append(str(path.relative_to(ROOT)))
for relative in DOCS[:7]:
    if relative != ASSESSMENT:
        assert NAME in texts[relative], relative
assert "[x] Implement/review injected portable file logic" in texts["TODO.md"]
assert "[x] Resolve first65/84" in texts["TODO.md"]
assert "[ ] Implement/review same-origin" in texts["TODO.md"]
assert "[ ] R09 Implement" in texts["TODO.md"]
assert all(f"[ ] HR{i}" in texts["TODO.md"] for i in range(1, 5))
assert "1,774 retained" in text and "327 source/resource pins" in text
assert "original 189-case profile remains failed" in text and "INCOMPLETE_TIMEOUT" in text
assert "0/12" in text and "65 missing inputs" in text
assert all("16d65f57" in texts[path] for path in DOCS[-3:])
assert "fourteen fault families" in text and "not an atomic OS-to-Python" in text
raw = (HERE / "PORTABLE-FILE-PORTS-SCOPED-ACCEPTANCE-v2.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "16d65f572019a86b466d684f5c67b330140de85362829abad7a19330ee4d318a"
acceptance = json.loads(raw)
assert acceptance["published_behavioral_cases"] == 84
assert acceptance["focused_author_methods"] == 21 and acceptance["independent_source_probes"] == 9
for flag in ("real_FFI_qualified", "actual_file_operations_qualified", "production_entry_or_engine_activated", "originals_authenticated", "profile_qualified", "runtime_authorized"):
    assert acceptance[flag] is False
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Ten current UTF8 docs, twenty recovery/human statuses, five critical next gates, local links and exact limited injected-source acceptance.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links,
    "application_tests_rerun": False, "retained_application_tests": 1774,
    "retained_application_source_pins": 327,
    "new_payload_or_native_activity": False,
}
output = HERE / "PORTABLE-CURRENT-DOCS-QA-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows),
                  "links": len(links), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
