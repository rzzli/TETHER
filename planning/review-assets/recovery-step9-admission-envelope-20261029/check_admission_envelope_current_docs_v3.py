"""Validate this milestone's current documents before completing its TODO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Admission Envelope.md"
ASSESSMENT = "planning/" + NAME
DOCS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-admission-envelope.md",
)
texts = {name: (ROOT / name).read_bytes().decode("utf-8", "strict") for name in DOCS}
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
for name in DOCS[:7]:
    if name != ASSESSMENT:
        assert NAME in texts[name], name
for name in DOCS[-3:]:
    assert "64d26ee8" in texts[name] and "8029e92a" in texts[name], name
todo = texts["TODO.md"]
assert "- [x] Implement/review the standalone role-aware metadata calculator" in todo
assert "- [ ] Select/qualify the concrete producer/role/storage/serialization" in todo
assert "[ ] R09 Implement" in todo and all(f"[ ] HR{i}" in todo for i in range(1, 5))
for token in ("status reconciliation", "55 direct evidence pins", "nine methods", "30 frozen metadata vectors",
              "12 isolated one-over-limit", "59 analyze calls", "488 checks", "113 getter calls",
              "18 cancellation stops", "zero key yields/resumptions", "zero equality hooks",
              "1,774 passing full tests", "327 source/resource pins", "65 missing inputs", "0/12",
              "INCOMPLETE_TIMEOUT", "137611-141215", "138889-142493", "R69/C93", "R68/C92",
              "595116", "fictitious declared coefficients", "Aggregate-only remains INDETERMINATE",
              "All seven real qualification flags remain false", "human reviews pending"):
    assert token in text, token
raw = (HERE / "ADMISSION-ENVELOPE-SCOPED-ACCEPTANCE-v3.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "64d26ee8be94dc6234fa5eed1aad21f38cfed6a0e984cb04a1397a8a7b673159"
acceptance = json.loads(raw)
assert acceptance["verified_evidence_freeze_pins"] == 55
assert acceptance["validation"]["independent_methods"] == 9 and acceptance["validation"]["author_methods"] == 8
assert all(value is False for value in acceptance["qualification"].values())
assert acceptance["application_changed"] is False and acceptance["application_tests_rerun"] is False
assert acceptance["actual_target_API_calls"] == acceptance["original_payload_operations"] == 0
pending = next(line for line in todo.splitlines() if line.startswith("- [ ] Reassess all R01-R16/HR1-HR4 after the admission envelope;"))
assert todo.count(pending) == 1
(ROOT / "TODO.md").write_text(todo.replace(pending, pending.replace("- [ ]", "- [x]", 1), 1), encoding="utf-8", newline="\n")
pins = {}
for name in DOCS:
    data = (ROOT / name).read_bytes()
    pins[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Ten current UTF8 docs,20 recovery/human status rows,five ordered next gates,exact source/pure acceptance,retained failures and unresolved actual producer/runtime/science boundaries.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links, "application_tests_rerun": False,
    "retained_application_tests": 1774, "retained_application_source_pins": 327,
    "new_original_or_native_activity": False,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
destination = HERE / "ADMISSION-ENVELOPE-CURRENT-DOCS-QA-v3.json"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows), "links": len(links), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
