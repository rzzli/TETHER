"""Verify current status documents, then mark the documentation task complete."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Indexed Accounting.md"
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
texts = {name: (ROOT / name).read_bytes().decode("utf-8", "strict") for name in DOCS}
text = texts[ASSESSMENT]
rows = re.findall(r"^\| (R\d\d|HR\d) \|", text, re.M)
assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
assert re.findall(r"^([1-5])\. ", text, re.M) == list("12345")
links = []
for wrapped, bare in re.findall(r"\]\((?:<([^>]+)>|([^\s)]+))\)", text):
    target = wrapped or bare
    if target.startswith(("https://", "http://", "#")):
        continue
    path = ((ROOT / ASSESSMENT).parent / unquote(target.split("#", 1)[0])).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), target
    links.append(str(path.relative_to(ROOT)))
for name in DOCS[:7]:
    if name != ASSESSMENT:
        assert NAME in texts[name], name
for name in DOCS[-3:]:
    assert "e318006d" in texts[name] and "e238e2a6" in texts[name], name
todo = texts["TODO.md"]
assert "- [x] Implement and independently verify the indexed-only V3 successor:" in todo
assert "- [ ] Implement/review the finite role-aware metadata admission envelope" in todo
assert "[ ] R09 Implement" in todo and all(f"[ ] HR{i}" in todo for i in range(1, 5))
for token in ("status reconciliation", "31", "15 methods", "372 strict snapshots",
              "518 simulated", "34 actual", "zero global", "Eighteen", "Five healthy-clock",
              "1,774 retained", "327 source/resource pins", "65 missing inputs", "0/12",
              "INCOMPLETE_TIMEOUT", "137,595", "142,493", "1,750,434", "14,588", "58,285",
              "not V3", "All seven real qualification flags remain false", "human reviews pending"):
    assert token in text, token
raw = (HERE / "INDEXED-ACCOUNTING-SCOPED-ACCEPTANCE-v3.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "e318006d805259336a9430f382edd38a255d597b944847ce8912dc58fac8822c"
acceptance = json.loads(raw)
assert acceptance["verified_evidence_freeze_pins"] == 31
assert acceptance["validation"]["independent_methods"] == 15
assert acceptance["validation"]["precode_indexed_methods"] == 6
assert all(v is False for v in acceptance["qualification"].values())
assert acceptance["application_changed"] is False and acceptance["application_tests_rerun"] is False
assert acceptance["actual_target_API_calls"] == acceptance["original_payload_or_sourceclosure_operations"] == 0
# All validations pass before completing the checklist item and sealing its final hash.
pending = next(line for line in todo.splitlines() if line.startswith("- [ ] Reassess all R01-R16/HR1-HR4 after indexed accounting;"))
assert todo.count(pending) == 1
todo = todo.replace(pending, pending.replace("- [ ]", "- [x]", 1), 1)
(ROOT / "TODO.md").write_text(todo, encoding="utf-8", newline="\n")
pins = {}
for name in DOCS:
    data = (ROOT / name).read_bytes()
    pins[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Current UTF8 documents, twenty recovery/human status rows, five ordered next gates, exact scoped acceptance, chronology and unresolved production/science boundaries.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links, "application_tests_rerun": False,
    "retained_application_tests": 1774, "retained_application_source_pins": 327,
    "new_payload_or_native_activity": False,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
destination = HERE / "INDEXED-ACCOUNTING-CURRENT-DOCS-QA-v3.json"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows), "links": len(links), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
