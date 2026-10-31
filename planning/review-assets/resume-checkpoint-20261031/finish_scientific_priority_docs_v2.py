"""Complete only the remaining edits after V1's newline-sensitive header refusal."""
from pathlib import Path
import hashlib
import json
import subprocess

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
    before = {}
    for name in names:
        raw = subprocess.check_output(["git", "show", "ceab32f:" + name], cwd=ROOT)
        before[name] = dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    archived = ROOT / "docs/history/README-before-scientific-priority-20261031.md"
    assert pin(archived)["sha256"] == before["README.md"]["sha256"]
    path = ROOT / "memory/project-goals.md"
    raw = path.read_bytes().decode()
    candidates = [marker for marker in ("## Current recovery execution\r\n\r\n", "## Current recovery execution\n\n") if marker in raw]
    assert len(candidates) == 1
    marker = candidates[0]
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
    assert "Current priority: [[Project Progress Reassessment 2026-10-31 - Scientific Readiness]]." not in raw
    raw = raw.replace(marker, marker + text, 1)
    old = "Current checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]]."
    assert raw.count(old) == 1
    raw = raw.replace(old, "Prior checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]].", 1)
    with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    inbox = ROOT / "data/benchmark/gold_evidence/human-review-inbox-20261031"
    for child in ("mechanism", "genetics-source", "genetics-followup", "source-feasibility"):
        folder = inbox / child
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / ".gitkeep").open("xb") as stream:pass
    docs = names + ["planning/Project Progress Reassessment 2026-10-31 - Scientific Readiness.md",
                    "planning/Scientific Review Handoff 2026-10-31.md"]
    report = dict(schema_version=2, status="PRIORITY_DOCUMENTATION_AUTHORED_PENDING_FINAL_QA",
                  baseline_commit="ceab32f", documents_before=before,
                  documents_final={name: pin(ROOT / name) for name in docs},
                  archived_readme=pin(archived), original_readme_preserved=True,
                  first_attempt=dict(helper=pin(BASE / "update_scientific_priority_docs_v1.py"),
                    failure="Expected CRLF current-section marker; actual inserted header is LF in mixed-newline memory. Stopped after7 current-doc edits, before memory-goals/inbox/report. No source or subject operation.",
                    correction="Named V2 accepts exactly one observed LF/CRLF marker, preserves remaining bytes, completes memory/inbox/report only. V1 not replayed; first edited docs not rewritten."),
                  inbox_contains_human_submissions=False, source_or_runtime_changes=False,
                  project_complete=False, provider_spend_usd=0,
                  scope="Prospective scientific priority/handoff; no old acceptance, native contract or failure amended. README history preserved byte for byte; operative usage retained.")
    output = BASE / "SCIENTIFIC-PRIORITY-DOCS-AUTHORING-v2.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    print(json.dumps({"report": pin(output), "documents": len(docs), "inbox_placeholders": 4,
                      "source_or_runtime_changes": False}))


if __name__ == "__main__":main()
