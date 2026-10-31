"""Validate the current design milestone documents and then complete its TODO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Producer Storage Design.md"
ASSESSMENT = "planning/" + NAME
DOCS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-producer-storage-design.md",
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
    assert "d3fee3d6" in texts[name] and "98729d86" in texts[name], name
todo = texts["TODO.md"]
assert "- [x] Review concrete prospective producer/storage design" in todo
assert "- [ ] Freeze complete offset/enum/raw-fact/checker/legacy schema" in todo
assert "- [ ] Select/qualify the concrete producer/role/storage/serialization" in todo
assert "[ ] R09 Implement" in todo and all(f"[ ] HR{i}" in todo for i in range(1, 5))
for token in ("as design only", "213", "9,017,363,392", "137753", "141161", "142439", "13482", "7042",
              "712,415", "8,989,020,320", "40,139,776", "113,985,546", "105,596,938",
              "14,800,384", "not", "17/32", "0/12", "65 missing inputs", "INCOMPLETE_TIMEOUT",
              "1,774 passing full tests", "327 source/resource pins", "human reviews pending",
              "before throwable packing", "complete admissible operational route"):
    # Whitespace between words and numbers in retained prose is immaterial here.
    assert token.replace(" ", "") in text.replace(" ", ""), token
raw = (HERE / "ROLE-AWARE-PRODUCER-DESIGN-ACCEPTANCE-v2.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "d3fee3d6e91b272267075f2b6df93e32e8a026e1f464ba8c0e3b072c155d7d64"
decision = json.loads(raw)
assert decision["verified_design_index_pins"] == 12
assert decision["generated_artifact_kinds"] == 14 and decision["named_payload_conservative_bytes"] == 113985546
for flag in ("source_implementation_authorized", "new_profile_activated", "real_entry", "real_FFI", "physical_IO", "full_roster_admitted", "new84_runtime", "measured_resource_fit", "application_changed"):
    assert decision[flag] is False, flag
pending = next(line for line in todo.splitlines() if line.startswith("- [ ] Reassess all R01-R16/HR1-HR4 after producer storage design;"))
assert todo.count(pending) == 1
(ROOT / "TODO.md").write_text(todo.replace(pending, pending.replace("- [ ]", "- [x]", 1), 1), encoding="utf-8", newline="\n")
pins = {}
for name in DOCS:
    data = (ROOT / name).read_bytes()
    pins[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Ten current UTF8 docs,20 recovery/human statuses,five next gates,exact limited design decision,historical-versus-prospective distinction and unresolved source/runtime/science terms.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links, "application_tests_rerun": False,
    "retained_application_tests": 1774, "retained_application_source_pins": 327,
    "target_payload_or_native_operations": 0,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
output = HERE / "ROLE-AWARE-PRODUCER-CURRENT-DOCS-QA-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "rows": len(rows), "links": len(links), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
