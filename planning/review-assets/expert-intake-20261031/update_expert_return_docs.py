"""Update current navigation/status after the validated mixed-provenance intake."""
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
    common = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
              "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md",
              "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
              "memory/MEMORY.md", "memory/project-goals.md", "planning/Scientific Review Handoff 2026-10-31.md"]
    before = {name: pin(ROOT / name) for name in common}
    values = {name: (ROOT / name).read_bytes().decode("utf-8") for name in common}
    current = ("Current checkpoint, 31 October UTC: {link}. All three supplied mechanism returns are "
               "preserved and normalized (54 selections; 95 integrity and 549 conversion checks; six "
               "selected isolation regressions pass). One explicitly AI-prepared file and two individually "
               "unverified files remain after the owner's 'Mixed or uncertain' reply. Zero independent "
               "human source references are qualified; no genetics/source-feasibility forms were returned. "
               "This is completed development intake, not missing files or scientific acceptance.")
    next_step = ("Next: qualify author/source-first provenance where it can be established, using the clean "
                 "provenance addendum; otherwise obtain traceable references for the relevant source-only "
                 "exercise. Reuse the existing sealed Candidate A audit and keep source credibility separate "
                 "from quotation fidelity. Preserve original responses/cards; do not vote away disagreement, "
                 "request the same files again or repair prior answers. Fresh-source/capability/H5/clinical "
                 "gates remain open. Optional native expansion stays deferred; unchanged v2, $0, original "
                 "FAILED/INCOMPLETE_TIMEOUT and downloader/stopped-monitor boundaries remain.")
    for name in common[1:6]:
        target = ("planning/" if name == "TODO.md" else "") + "Project Progress Reassessment 2026-10-31 - Expert Returns.md"
        raw, count = re.subn(r"^Current priority, 31 October UTC: [^\r\n]+", lambda _: current.format(link="[Expert returns](<" + target + ">)"), values[name], count=1, flags=re.M)
        assert count == 1, name
        raw, count = re.subn(r"^Next: use the existing clean reviewer[^\r\n]+", lambda _: next_step, raw, count=1, flags=re.M)
        assert count == 1, name
        if name == "TODO.md":
            raw += ("\n- [x] Preserve and normalize the three owner-supplied mechanism returns as unqualified evaluator-only development feedback: 95 integrity checks, 549 independent conversion checks and six existing isolation regressions pass. Originals/answers remain ignored.\n"
                    "- [x] Reuse the exact sealed Candidate A audit instead of rebuilding it (102 checks), and retain the separate primary-literature source-credibility concern without editing cards or ratings.\n"
                    "- [x] Prepare a clean blank provenance addendum; record the owner's mixed/uncertain provenance separately, with no human-reference acceptance.\n"
                    "- [ ] Reassess the full project after expert-return intake and validate current docs/memory; assessment: planning/Project Progress Reassessment 2026-10-31 - Expert Returns.md.\n")
        if name == "planning/Project Progress Reassessments.md":
            raw += ("\n| Three mechanism returns processed; provenance unqualified | [31 October UTC expert-return assessment](<Project Progress Reassessment 2026-10-31 - Expert Returns.md>) | All three files preserved; 54 selections, 95 integrity/549 conversion checks and six selected regressions pass. One AI-disclosed/two individually unverified; no human/reference/scientific gate passed. Sealed coverage reused, source-credibility concern separate. |\n")
        values[name] = raw
    old = "The [scientific-readiness assessment](<planning/Project Progress Reassessment 2026-10-31 - Scientific Readiness.md>) is the current plan. The next dependent step needs independent reviewer submissions, qualified fresh sources and a justified capability condition. Use the [review handoff](<planning/Scientific Review Handoff 2026-10-31.md>) for the existing clean exercises and local return folders. Human submissions remain pending."
    assert values["README.md"].count(old) == 1
    new = ("The [expert-return assessment](<planning/Project Progress Reassessment 2026-10-31 - Expert Returns.md>) is the current checkpoint. All three supplied files have been processed as mechanism-development feedback. One explicitly discloses AI preparation; the two text origins remain individually unverified after the owner's 'Mixed or uncertain' reply. No independent human-reference gate is passed. Use the [review handoff](<planning/Scientific Review Handoff 2026-10-31.md>) and clean [provenance addendum](docs/expert-review-admin-20261031/Review-provenance-addendum.md) for the next qualification step; do not resend the same files.")
    values["README.md"] = values["README.md"].replace(old, new, 1)
    memory = values["memory/MEMORY.md"]
    entry = ("- [[research-log-2026-10-31-expert-returns]] - Current checkpoint: three mechanism files preserved/normalized, 54 selections; 95 integrity/549 conversion checks and six selected regressions pass. One AI-disclosed/two individually unverified after owner 'Mixed or uncertain'; zero qualified human references. Existing sealed coverage reused/102 checks; source-credibility concern checked separately against primary literature. No new model, repaired answer or scientific gate acceptance.\n\n")
    assert memory.startswith("# Research memory index\n\n")
    memory = memory.replace("# Research memory index\n\n", "# Research memory index\n\n" + entry, 1)
    memory, count = re.subn(r"^- \[\[project-goals\]\] - [^\r\n]+", "- [[project-goals]] - Current AsOf 0.3.11/default v2. Three mixed/unverified-provenance mechanism returns are processed development material; independent source-only references, fresh-source and capability readiness remain open. No R07 genetics/HR3/H5 gate is passed. Optional native expansion deferred; existing failures, $0 and no new model run preserved.", memory, count=1, flags=re.M)
    assert count == 1
    values["memory/MEMORY.md"] = memory
    goals = values["memory/project-goals.md"]
    old_current = "Current priority: [[Project Progress Reassessment 2026-10-31 - Scientific Readiness]]."
    assert goals.count(old_current) == 1
    intro = ("Current checkpoint: [[Project Progress Reassessment 2026-10-31 - Expert Returns]].\n"
             "The three supplied files are received and processed, not missing: 54 mechanism selections,\n"
             "95 integrity/549 conversion checks and six isolation regressions pass. The owner reports\n"
             "TXT origins as mixed/uncertain; one DOCX explicitly says AI-prepared/candidate-visible.\n"
             "No individual human provenance/source-first independence is qualified, and no genetics\n"
             "or source-feasibility exercise was returned. Existing sealed Candidate A coverage is\n"
             "reused (102 checks); primary-literature source credibility is a separate AI annotation.\n"
             "Next use the clean provenance addendum where authors can clarify; otherwise obtain\n"
             "traceable relevant source-only references. Do not infer authorship from agreement or\n"
             "retrofit blind/fresh status. H5/clinical/capability/source gates remain open, optional\n"
             "native work deferred, default v2 and $0 unchanged. See [[research-log-2026-10-31-expert-returns]].\n\n"
             "### Prior scientific-readiness checkpoint (retained history)\n\n"
             "Prior priority: [[Project Progress Reassessment 2026-10-31 - Scientific Readiness]].")
    values["memory/project-goals.md"] = goals.replace(old_current, intro, 1)
    handoff = values["planning/Scientific Review Handoff 2026-10-31.md"]
    marker = "## What to send and collect"
    assert handoff.count(marker) == 1
    receipt = ("## Current returns\n\n"
               "The three files supplied under `docs/expert-response10312026/` are already preserved and processed. They all address the mechanism orientation. The Word file discloses AI preparation/candidate exposure; the owner described the text origins as mixed or uncertain. Individual authorship and source-first independence remain unverified. Do not request those same files again or count them as completed genetics/source-feasibility reviews.\n\n"
               "If actual authors can clarify, use the clean [provenance addendum](../docs/expert-review-admin-20261031/Review-provenance-addendum.md). Unknown is allowed; this cannot retrospectively create blind/fresh/human status. Keep completed addenda evaluator-only alongside the preserved intake. See the [current assessment](<Project Progress Reassessment 2026-10-31 - Expert Returns.md>) for qualification limits.\n\n")
    handoff = handoff.replace(marker, receipt + marker, 1)
    handoff = handoff.replace("An empty local inbox is prepared at:", "A local return inbox is available at the path below. Current responses are already preserved in the separate ignored `expert-intake-20261031T160538Z` directory; no duplicate copy is needed:", 1)
    values["planning/Scientific Review Handoff 2026-10-31.md"] = handoff
    # Preflight all edits before changing any current document.
    for name, selected in before.items():
        assert pin(ROOT / name) == selected
    for name, raw in values.items():
        (ROOT / name).write_bytes(raw.encode("utf-8"))
    all_names = common + ["planning/Project Progress Reassessment 2026-10-31 - Expert Returns.md",
                          "memory/research-log-2026-10-31-expert-returns.md",
                          "docs/expert-review-admin-20261031/Review-provenance-addendum.md"]
    report = dict(schema_version=1, status="CURRENT_RETURN_DOCS_AUTHORED_PENDING_QA",
                  documents_before=before, documents_final={name: pin(ROOT / name) for name in all_names},
                  human_reference_qualified=False, original_response_changed=False,
                  source_runtime_changed=False, catalog_changed=False, provider_spend_usd=0,
                  limits="Current navigation/status and new receipt checklist only; old dated assessments, frozen packets/answers, scientific gates and native contracts remain unchanged.")
    output = BASE / "EXPERT-RETURNS-DOCS-AUTHORING-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True); stream.write("\n")
    print(json.dumps({"authoring": pin(output), "documents": len(all_names), "source_runtime_changed": False}))


if __name__ == "__main__":
    main()
