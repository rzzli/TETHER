"""Verify documentation at a source-only checkpoint; never loads the core."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Raw Adoption Core.md"
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
assert "[x] Implement/review the portable adoption/reconciliation" in texts["TODO.md"]
assert "[ ] Implement/review one canonical shared-owner continuation" in texts["TODO.md"]
assert "[ ] Implement/review same-origin" in texts["TODO.md"]
assert "[ ] R09 Implement" in texts["TODO.md"]
assert all(f"[ ] HR{i}" in texts["TODO.md"] for i in range(1, 5))
assert all("5afb82f0" in texts[path] for path in DOCS[-3:])
assert "1,774 retained" in text and "327 source/resource pins" in text
assert "original 189-case profile remains failed" in text and "INCOMPLETE_TIMEOUT" in text
assert "0/12" in text and "65 missing inputs" in text
assert "native-to-Python return window remains" in text
assert "19 independent driver methods" in text and "21 owner-control methods" in text
assert "nine checkpoints and 320 issued snapshots" in text
raw = (HERE / "RAW-ADOPTION-CORE-SCOPED-ACCEPTANCE-v3.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "5afb82f048dd05e65be5223ead9410c40e4670c429c3b5b762ee49d8c7db87a7"
acceptance = json.loads(raw)
assert acceptance["status"] == "ACCEPTED_V3_PORTABLE_RAW_ADOPTION_SOURCE_PURE_ONLY"
assert acceptance["histories"] == 32 and acceptance["checkpoints"] == 9 and acceptance["snapshots"] == 320
assert acceptance["owner_controls_methods"] == 21 and acceptance["independent_driver_methods"] == 19
assert acceptance["verified_frozen_input_pins"] == 28
for flag in ("runtime_authorized", "FFI_registration_proven", "production_owner_bound", "originals_authenticated", "profile_qualified", "application_changed"):
    assert acceptance[flag] is False, flag
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "scope": "Ten current UTF8 docs, twenty recovery/human statuses, five critical next gates, local links and exact portable source-only acceptance. This is no new whole-code/data/old-run qualification.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links,
    "application_tests_rerun": False, "retained_application_tests": 1774,
    "retained_application_source_pins": 327,
    "new_payload_or_native_activity": False,
}
destination = HERE / "RAW-ADOPTION-CURRENT-DOCS-QA-v3.json"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows), "links": len(links), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
