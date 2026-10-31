"""Check current repository docs at scoped observer completion."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Unicode Observation Validator.md"
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
assert "[x] Implement/review Unicode observer-v2" in texts["TODO.md"]
assert "[x] Correct/review observer's four guards" in texts["TODO.md"]
assert "[ ] Implement/review portable file" in texts["TODO.md"]
assert "[ ] R09 Implement" in texts["TODO.md"]
assert all(f"[ ] HR{i}" in texts["TODO.md"] for i in range(1, 5))
assert "1,774 retained" in text and "327 source/resource pins" in text
assert "original 189-case profile remains failed" in text and "INCOMPLETE_TIMEOUT" in text
assert "0/12" in text and "65 missing inputs" in text
assert all("743ece01" in texts[path] for path in DOCS[-3:])
assert "old journal/archive policies" in text
raw = (HERE / "UNICODE-OBSERVATIONS-SCOPED-ACCEPTANCE-v2.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "743ece01c441aa01456e072f4a7a6613501c09469bd410ee182e41f0324d6d1f"
acceptance = json.loads(raw)
assert acceptance["author_methods"] == 14 and acceptance["independent_terminal_data_probes"] == 4
assert acceptance["root_boundary_regressions"] == 2
assert acceptance["profile_qualified"] is False and acceptance["runtime_authorized"] is False
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Ten current UTF8 docs, all twenty recovery/human rows, five critical next gates, local assessment references and exact limited acceptance.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links,
    "application_tests_rerun": False, "retained_application_tests": 1774,
    "retained_application_source_pins": 327,
    "new_payload_or_native_activity": False,
}
output = HERE / "UNICODE-OBSERVER-CURRENT-DOCS-QA-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "status_rows": len(rows),
                  "links": len(links), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
