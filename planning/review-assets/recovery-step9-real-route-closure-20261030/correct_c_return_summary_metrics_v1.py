"""Retain the five authorized documentation additions; no subject execution."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD_AUTHOR = HERE / "C-RETURN-CURRENT-DOCS-AUTHORING-v2.json"
OLD_QA = HERE / "C-RETURN-CURRENT-DOCS-QA-v1.json"
REPORT = HERE / "C-RETURN-CURRENT-DOCS-AUTHORING-v3.json"


def pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


if REPORT.exists():
    raise RuntimeError("One-shot documentation correction already retained")
author = json.loads(OLD_AUTHOR.read_bytes())
qa = json.loads(OLD_QA.read_bytes())
assert qa["status"] == "HOLD_CURRENT_DOC_CHECKS"
assert qa["counts"]["failed"] == 5
names = [item["path"] for item in author["after_document_pins"]]
before = {name: (ROOT / name).read_bytes() for name in names}
for name, item in qa["documents_final"].items():
    assert pin(ROOT / name) == item, name
edits = []
texts = {name: data.decode("utf-8") for name, data in before.items()}
for name in ("README.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
             "planning/Recovery Status and Next Gates 2026-10-26.md",
             "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"):
    old = "All 79 controls / 29,310 measured C checks pass;"
    new = ("Independent compiled-artifact review passes 129 checks and actual-run review "
           "passes 399 checks. All 79 controls / 29,310 measured C checks pass;")
    assert texts[name].count(old) == 1, name
    texts[name] = texts[name].replace(old, new, 1)
    edits.append({"path": name, "old": old, "new": new})
name = "memory/MEMORY.md"
old = "Root ad4c9f0e accepts compiled x64 layout + one C79 fake image only:"
new = ("Root ad4c9f0e accepts compiled x64 layout + one C79 fake image only "
       "(compiled peer 5796bcc6; actual peer 1b10326d):")
assert texts[name].count(old) == 1
texts[name] = texts[name].replace(old, new, 1)
edits.append({"path": name, "old": old, "new": new})
assert {item["path"] for item in edits} == {
    "README.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md", "memory/MEMORY.md"}
for name, data in before.items():
    assert (ROOT / name).read_bytes() == data, name
for name in {item["path"] for item in edits}:
    (ROOT / name).write_bytes(texts[name].encode("utf-8"))
result = {
    "schema_version": 1,
    "status": "FIVE_SUMMARY_ADDITIONS_INDEPENDENT_QA_PENDING",
    "reason": "Preserve original v1 QA HOLD. Four summaries omitted independent check counts; MEMORY omitted two independent peer references. Add only the evidence-backed omissions, without relaxing any original QA assertion.",
    "authorization": "Root resume audit follow-up authorizes these five narrow additions and a named independent QA v2 successor; no source or runtime execution.",
    "previous_authoring": pin(OLD_AUTHOR), "preserved_failed_QA": pin(OLD_QA),
    "root_acceptance": pin(HERE / "NATIVE-CARRIER-ROOT-ACCEPTANCE-v1.json"),
    "before_document_pins": [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in before.items()],
    "after_document_pins": [pin(ROOT / name) for name in names],
    "authorized_summary_edits": edits,
    "activity": {"subject_runs": 0, "subject_imports": 0, "application_tests": 0,
                 "builds": 0, "native_dispatches": 0, "original_or_model_payload_reads": 0},
    "QA_checkbox": "UNTICKED_PENDING_INDEPENDENT_PEER"
}
with REPORT.open("xb") as stream:
    stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(pin(REPORT)))
