"""Check the current documentation checkpoint; no subject tests or originals."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Shared Owner Continuation.md"
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
todo = texts["TODO.md"]
assert "[x] Implement/review one canonical shared-owner continuation" in todo
assert "[ ] R09 Implement" in todo and "[ ] Implement/review same-origin" in todo
assert all(f"[ ] HR{i}" in todo for i in range(1, 5))
assert all("7e0d9484" in texts[path] for path in DOCS[-3:])
for expected in ("1,774 retained", "327 source/resource pins", "65 missing inputs", "0/12", "INCOMPLETE_TIMEOUT",
                 "137,595", "142,493", "1,750,434", "9,466,123,215", "14,588", "51,809",
                 "not preregistered", "107 methods remain unchanged", "518 simulated", "372 snapshots"):
    assert expected in text, expected
raw = (HERE / "SHARED-OWNER-SCOPED-ACCEPTANCE-v2.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "7e0d94849d5ba9da358167a9d103b44fa6ae25acc8e5bed646d2839162220344"
acceptance = json.loads(raw)
assert acceptance["verified_evidence_freeze_pins"] == 27
assert acceptance["validation"]["histories"] == 48 and acceptance["validation"]["focused_regression_methods"] == 8
assert acceptance["validation"]["author_controls"] == 12 and acceptance["validation"]["supplemental_controls"] == 4
for flag in ("runtime_authorized", "FFI_registration_proven", "production_owner_bound", "originals_authenticated", "profile_qualified", "real_checkers_bound", "verification_complete", "application_changed"):
    assert acceptance[flag] is False, flag
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "scope": "Ten current UTF8 docs, twenty recovery/human statuses, five next gates, exact limited source/pure acceptance, retained chronology and analytic production barriers. No new whole-code/data/runtime qualification.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links,
    "application_tests_rerun": False, "retained_application_tests": 1774,
    "retained_application_source_pins": 327,
    "new_payload_or_native_activity": False,
}
destination = HERE / "SHARED-OWNER-CURRENT-DOCS-QA-v2.json"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows), "links": len(links), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
