"""Validate the schema milestone's status documents before closing its TODO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Producer Format Schema.md"
ASSESSMENT = "planning/" + NAME
DOCS = (
    "README.md", "TODO.md", ASSESSMENT,
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
    "memory/MEMORY.md", "memory/project-goals.md",
    "memory/research-log-2026-10-29-producer-format-schema.md",
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
    assert "14bc12d3" in texts[name] and "7828e215" in texts[name], name
todo = texts["TODO.md"]
assert "- [x] Freeze and independently review the exact offset" in todo
assert "- [ ] Freeze independent literal corpus/test source" in todo
assert "[ ] R09 Implement" in todo and all(f"[ ] HR{i}" in todo for i in range(1, 5))
for token in ("127,809,034", "13,823,488", "12,325,232,640", "19079", "5,232,640",
              "16384", "forty semantic base histories", "same-owner ProducerSnapshot",
              "Derived encoder and assembly", "API IDs8-14", "first-fact", "INCOMPLETE_TIMEOUT",
              "1,774 passing full tests", "327 source/resource pins", "65 missing inputs", "0/12",
              "probabilities null", "human reviews pending", "The project remains unfinished"):
    assert token.replace(" ", "") in text.replace(" ", ""), token
raw = (HERE / "ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "14bc12d3b193cb1d92ea7bc6ec852efa4728eac8b8beeda95e0ea2fd895d3b1f"
decision = json.loads(raw)
assert decision["verified_index_pins"] == 12 and decision["literal_preparation_authorized"] is True
for flag in ("source_implementation_authorized", "producer_integration_qualified", "full_roster_admitted", "new84_runtime", "measured_resource_fit", "scientific_validation", "application_changed"):
    assert decision[flag] is False, flag
pending = next(line for line in todo.splitlines() if line.startswith("- [ ] Reassess all R01-R16/HR1-HR4 after producer format schema;"))
assert todo.count(pending) == 1
(ROOT / "TODO.md").write_text(todo.replace(pending, pending.replace("- [ ]", "- [x]", 1), 1), encoding="utf-8", newline="\n")
pins = {}
for name in DOCS:
    data = (ROOT / name).read_bytes()
    pins[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
report = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "scope": "Ten UTF8 current docs,20 statuses,five next gates,exact limited schema acceptance and codec/producer/physical/inference-resource boundaries.",
    "documents": pins, "status_rows": rows, "ordered_next_gates": 5,
    "assessment_local_links": links, "application_tests_rerun": False,
    "retained_application_tests": 1774, "retained_application_source_pins": 327,
    "original_target_or_native_operations": 0,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
output = HERE / "ROLE-AWARE-FORMAT-CURRENT-DOCS-QA-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "passed", "documents": len(DOCS), "rows": len(rows), "links": len(links), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
