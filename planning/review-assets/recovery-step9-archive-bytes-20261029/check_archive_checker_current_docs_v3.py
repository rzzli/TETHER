"""Validate this source-only checkpoint's documentation and references."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NAME = "Project Progress Reassessment 2026-10-29 - Captured Archive Checker.md"
ASSESSMENT = "planning/" + NAME
DOCUMENTS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-r09-unicode-controls.md",
)
texts, pins = {}, {}
for relative in DOCUMENTS:
    raw = (ROOT / relative).read_bytes()
    texts[relative] = raw.decode("utf-8", "strict")
    pins[relative] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
assessment = texts[ASSESSMENT]
rows = re.findall(r"^\| (R\d\d|HR\d) \|", assessment, re.M)
assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
assert re.findall(r"^([1-5])\. ", assessment, re.M) == list("12345")
links = []
for wrapped, bare in re.findall(r"\]\((?:<([^>]+)>|([^\s)]+))\)", assessment):
    target = wrapped or bare
    if target.startswith(("https://", "http://", "#")):
        continue
    path = ((ROOT / ASSESSMENT).parent / unquote(target.split("#", 1)[0])).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), target
    links.append(str(path.relative_to(ROOT)))
for relative in DOCUMENTS[:7]:
    if relative != ASSESSMENT:
        assert NAME in texts[relative], relative
assert "[x] Correct/review archive checker v3" in texts["TODO.md"]
assert "[ ] R09 Implement" in texts["TODO.md"]
assert all(f"[ ] HR{i}" in texts["TODO.md"] for i in range(1, 5))
assert "1,774 retained" in assessment and "327 source/resource pins" in assessment
assert "original 189-case profile remains failed" in assessment
assert "INCOMPLETE_TIMEOUT" in assessment and "0/12" in assessment
assert "686dcf47" in texts["memory/project-goals.md"]
assert "686dcf47" in texts["memory/research-log-2026-10-29-r09-unicode-controls.md"]
assert "archive13author/7peer" in texts["memory/MEMORY.md"]
acceptance_raw = (HERE / "CAPTURED-ARCHIVE-CHECKER-SCOPED-ACCEPTANCE-v3.json").read_bytes()
assert hashlib.sha256(acceptance_raw).hexdigest() == "686dcf476b13e117badbae2d5bff4276859219bb3cbc704be5a31af513edcd8e"
acceptance = json.loads(acceptance_raw)
assert acceptance["author_methods"] == 13 and acceptance["independent_methods"] == 7
assert acceptance["frozen_projection_cases"] == 32
for flag in ("runtime_authorized", "profile_qualified", "source_qualified", "resource_qualified", "actual_directory_complete", "originals_authenticated"):
    assert acceptance[flag] is False
result = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Current UTF8 repository docs, twenty recovery/human rows, five ordered next gates, local assessment links and exact source-only acceptance scope.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links, "application_tests_rerun": False,
    "retained_application_tests": 1774, "retained_application_source_pins": 327,
    "old_actual_archive_replayed": False, "new_payload_or_native_activity": False,
}
output = HERE / "ARCHIVE-CHECKER-CURRENT-DOCS-QA-v3.json"
with output.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, sort_keys=True, ensure_ascii=False, indent=2)
    handle.write("\n")
raw = output.read_bytes()
print(json.dumps({"status": "passed", "documents": len(pins),
                  "status_rows": len(rows), "links": len(links),
                  "sha256": hashlib.sha256(raw).hexdigest()}))
