"""Reconcile current priorities with the original scientific scope; no runtime edits."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    names = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
             "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md",
             "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
             "memory/MEMORY.md", "memory/project-goals.md"]
    before = {name: pin(ROOT / name) for name in names}
    readme = ROOT / "README.md"
    original = readme.read_bytes()
    archived = ROOT / "docs/history/README-before-scientific-priority-20261031.md"
    with archived.open("xb") as stream:stream.write(original)
    operational = original.decode().split("## Run the offline demonstration\n", 1)[1]
    operational = operational.replace("Temporary v2 review probes and legacy verification", "Required review probes and legacy verification")
    intro = """# AsOf target-evaluation agents

AsOf turns dated evidence into auditable target-evaluation dossiers. It provides
strict temporal and lineage admission, immutable evidence, bounded execution,
failure/usage journals and semantic re-verification. The default backend runs
offline and makes no model-provider requests.

**Current software: 0.3.11, with v2 execution contracts.** The retained acceptance
has 1,774 tests; all 327 accepted source/resource pins matched at the latest resume.
The source includes optional study preparation, recorded comparison and bounded
model interfaces. Recorded fixtures and passing software tests are not scientific
performance measurements.

## Current status and next step

The [scientific-readiness assessment](<planning/Project Progress Reassessment 2026-10-31 - Scientific Readiness.md>) is the current plan. The next dependent step needs independent reviewer submissions, qualified fresh sources and a justified capability condition. Use the [review handoff](<planning/Scientific Review Handoff 2026-10-31.md>) for the existing clean exercises and local return folders. Human submissions remain pending.

- Ten canonical contemporary development dossiers and their retained source audit exist; see the [run registry](planning/run-registry.json).
- R07's technical diagnostic is negative: six complete responses, zero frozen-contract passes. Independent human assessment and a stronger-model control remain unavailable.
- Source5 corrects two API/axis-kind guards: 43 executable controls pass, four branches remain deferred and one static. The separate C79 fake-target component passed; the installed C++ tools work without restart.
- Further private native-bank/physical14/new84 proof work is deferred pending a demonstrated study need. It is not a prerequisite for reporting the existing extractive framework and negative feasibility result.
- Scientific H5 and clinical H1–H4 remain open. Real numerical features stay empty and probabilities null. The frozen interpretation slice has 65 missing inputs; the clinical route has 36 unqualified endpoints and 0/12 jointly source-ready cases.

The original native recognition result remains FAILED and whole verification
INCOMPLETE_TIMEOUT. Failed attempts are retained, with no automatic replay or
answer repair. Provider spending remains $0; the downloader and stopped monitor
are unchanged. Python interfaces are not an OS sandbox.

## Navigation

| Resource | Purpose |
|---|---|
| [TODO](TODO.md) | Current accepted work and incomplete scientific/optional engineering gates |
| [Recovery plan](<planning/Project Recovery and Evaluation Plan 2026-10-26.md>) | Original ordered dependencies and stop rules |
| [Progress assessments](<planning/Project Progress Reassessments.md>) | Dated evidence and limitations |
| [Framework](docs/FRAMEWORK.md) / [migration](docs/V02_MIGRATION.md) | v2 interfaces, temporal/semantic guarantees and v1 limitations |
| [Study runtime](docs/STUDY_RUNTIME.md) / [interpretation](docs/INTERPRETATION_INTERFACE.md) | Packaged research mechanics and their claim boundaries |
| [Data plan](data/DATA_PLAN.md) / [catalog](data/catalog/sources.json) | Dataset products, versions, permissions and acquisition requirements |
| [Prior README](docs/history/README-before-scientific-priority-20261031.md) | Exact pre-reassessment history, preserved at its original checkpoint |

## Run the offline demonstration
"""
    with readme.open("w", encoding="utf-8", newline="") as stream:stream.write(intro + operational)
    current = ("Current priority, 31 October UTC: {link}. Retain Source5's accepted 43 executable "
               "PASS / four DEFERRED / one STATIC and C79 fake-component evidence. Defer further "
               "native-bank/physical14/new84 implementation pending a demonstrated scientific consumer. "
               "R07 human assessment, fresh source/reference readiness and a justified capability "
               "condition are the next scientific gates; no new model run or old-experiment replay.")
    next_step = ("Next: use the existing clean reviewer exercises and scientific review handoff to obtain "
                 "actual independent submissions, qualify source/question/exposure readiness, then choose "
                 "a bounded capability/design decision. Reuse packaged comparison/provenance/accounting "
                 "instead of adding another controller stack. H5 and H1–H6 remain unfinished; native "
                 "deferral does not pass its contracts. AsOf 0.3.11/default v2, retained 1,774 tests and "
                 "327 pins, $0, original FAILED/INCOMPLETE_TIMEOUT, empty features/null probabilities "
                 "and downloader/stopped-monitor boundaries remain unchanged.")
    for name in names[1:6]:
        path = ROOT / name
        raw = path.read_bytes().decode()
        target = ("planning/" if name == "TODO.md" else "") + "Project Progress Reassessment 2026-10-31 - Scientific Readiness.md"
        raw, count = re.subn(r"^Current checkpoint, 31 October UTC: [^\n]+", lambda _: current.format(link="[Scientific readiness](<" + target + ">)"), raw, count=1, flags=re.M)
        assert count == 1, name
        raw, count = re.subn(r"^Next: close the four native-bank[^\n]+", lambda _: next_step, raw, count=1, flags=re.M)
        assert count == 1, name
        if name == "TODO.md":
            raw = raw.replace("- [ ] Implement and validate the complete entry/operations/file-view route.", "- [ ] Optional native branch — deferred pending demonstrated study need: implement and validate the complete entry/operations/file-view route.", 1)
            raw = raw.replace("- [ ] Qualify native25 component coverage with runtime/data/static/deferred distinctions;", "- [ ] Optional native branch — deferred pending demonstrated study need: qualify native25 component coverage with runtime/data/static/deferred distinctions;", 1)
            raw += ("\n- [ ] Reassess next-step alignment with Opus/R01/R07 and retain the accepted Source5 milestone; defer optional native-proof expansion without weakening its contracts.\n"
                    "- [ ] Prepare the scientific review handoff and empty evaluator-only return inbox; no human responses are implied.\n"
                    "- [ ] Receive actual independent source-only reviews and qualify source/question/capability readiness before a new scientific pilot.\n")
        if name == "planning/Project Progress Reassessments.md":
            raw += ("\n| Scientific priorities restored after Source5 | [31 October UTC readiness assessment](<Project Progress Reassessment 2026-10-31 - Scientific Readiness.md>) | Preserve accepted components; defer optional native-proof expansion. Independent submissions/source sufficiency/capability remain the scientific gate. No new model run or scientific completion. |\n")
        with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    path = ROOT / "memory/MEMORY.md"
    raw = path.read_bytes().decode()
    entry = ("- [[Project Progress Reassessment 2026-10-31 - Scientific Readiness]] - Current priority: actual independent reviewer submissions and source/question/capability readiness. Optional native-bank/physical14/new84 branch deferred pending demonstrated study need; Source5 43 PASS/four DEFERRED/one STATIC and C79 scopes preserved. No scientific completion or new model run. Review handoff and empty evaluator-only inbox prepared.\n\n")
    raw = raw.replace("# Research memory index\n\n", "# Research memory index\n\n" + entry, 1)
    raw, count = re.subn(r"^- \[\[project-goals\]\] - [^\n]+", "- [[project-goals]] - Current AsOf 0.3.11/default v2; scientific gates are independent human references, fresh source readiness and a justified capability condition. R01–R06 accepted, R07 technical negative/human pending; H5 and clinical/genetics/scorer/comparisons/T2–T5/H6 unfinished. Optional native-proof expansion deferred, existing failures preserved; no new spending or model run.", raw, count=1, flags=re.M)
    assert count == 1
    with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    path = ROOT / "memory/project-goals.md"
    raw = path.read_bytes().decode()
    marker = "## Current recovery execution\r\n\r\n"
    assert marker in raw
    text = ("Current priority: [[Project Progress Reassessment 2026-10-31 - Scientific Readiness]].\n"
            "Return to the original smallest interpretable T6 comparison and its scientific prerequisites.\n"
            "R07 human assessment, fresh source/question/exposure readiness and an approved capability\n"
            "condition remain open. Use planning/Scientific Review Handoff 2026-10-31.md; source-only\n"
            "human submissions must precede candidate exposure. Agents cannot replace those submissions.\n"
            "Optional native-bank/physical14/new84 implementation is deferred pending a demonstrated\n"
            "study consumer/defect and finite plan; its strict contracts and unqualified states remain.\n"
            "Source5 43 executable PASS/four DEFERRED/one STATIC and C79 are retained component results.\n"
            "No new model/old-cell replay, download, spending, default change or monitor restart.\n"
            "Scientific H5/H1–H6 and HR1–HR4 remain open; next dependent work is externally gated.\n\n"
            "### Prior component-guard checkpoint (retained history)\n\n")
    raw = raw.replace(marker, marker + text, 1)
    old = "Current checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]]."
    raw = raw.replace(old, "Prior checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]].", 1)
    with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    inbox = ROOT / "data/benchmark/gold_evidence/human-review-inbox-20261031"
    for child in ("mechanism", "genetics-source", "genetics-followup", "source-feasibility"):
        folder = inbox / child
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / ".gitkeep").open("xb") as stream:pass
    docs = names + ["planning/Project Progress Reassessment 2026-10-31 - Scientific Readiness.md",
                    "planning/Scientific Review Handoff 2026-10-31.md"]
    report = dict(schema_version=1, status="PRIORITY_DOCUMENTATION_AUTHORED_PENDING_FINAL_QA",
                  documents_before=before, documents_final={name: pin(ROOT / name) for name in docs},
                  archived_readme=pin(archived), original_readme_preserved=archived.read_bytes() == original,
                  inbox_contains_human_submissions=False, source_or_runtime_changes=False,
                  project_complete=False, provider_spend_usd=0,
                  scope="Prospective scientific priority/handoff; no old acceptance, native contract or failure amended. README history preserved byte for byte; operative usage retained.")
    with (BASE / "SCIENTIFIC-PRIORITY-DOCS-AUTHORING-v1.json").open("x", encoding="utf-8", newline="\n") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    print(json.dumps({"documents": len(docs), "readme_bytes_before": len(original),
                      "readme_bytes_after": len(readme.read_bytes()), "inbox_placeholders": 4,
                      "source_or_runtime_changes": False}))


if __name__ == "__main__":main()
