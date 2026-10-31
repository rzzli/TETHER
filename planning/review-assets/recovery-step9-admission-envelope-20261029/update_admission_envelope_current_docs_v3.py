"""Retain the major-stage assessment and reconcile current status documents."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Admission Envelope.md"
OLD = "Project Progress Reassessment 2026-10-29 - Indexed Accounting.md"
LOG = "research-log-2026-10-29-admission-envelope"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-sha256", required=True)
    args = parser.parse_args()
    raw = (HERE / "ADMISSION-ENVELOPE-SCOPED-ACCEPTANCE-v3.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.acceptance_sha256
    acceptance = json.loads(raw)
    assert acceptance["status"] == "ACCEPTED_STANDALONE_V3_METADATA_ENVELOPE_CALCULATOR_SOURCE_PURE_ONLY"
    peer = next(name for name in acceptance["inputs"] if "SOURCE-INDEPENDENT-PEER" in name)
    peer_sha = acceptance["inputs"][peer]["sha256"]
    short, peer_short = args.acceptance_sha256[:8], peer_sha[:8]
    base = "review-assets/recovery-step9-admission-envelope-20261029/"
    prior = (ROOT / "planning" / OLD).read_text(encoding="utf-8")
    table = prior.split("| Item | Current status and remaining gate |", 1)[1].split("\n\nAsOf", 1)[0]
    rows = table.splitlines()
    rows = ["| R09 | Application 0.3.11 and scoped source/pure components accepted, now including the standalone metadata-envelope calculator. Actual producer/role/storage/output representation, approved roster, entry/FFI/source/physical publication/new format/resource/native/masking/integrated/scientific gates remain unfinished. |" if row.startswith("| R09 |") else row for row in rows]
    table = "| Item | Current status and remaining gate |" + "\n".join(rows)
    assessment = f"""# Project reassessment after the metadata admission envelope

29 October 2026 UTC. The standalone metadata calculator is accepted for source/pure correctness. It computes conditional read/call/event, capture, buffer, journal, report and output requirements from explicit metadata, distinguishes missing assumptions from invalid metadata and exceeded bounds, and grants no runtime authority. The C++ toolchain works without restarting. R09 and the complete project remain unfinished.

This is a project-wide **status reconciliation** against retained evidence, with fresh verification of this component. It is not a new complete application/data audit or a replay of the consumed native experiment. The [indexed-accounting assessment](<{OLD}>) and all earlier snapshots remain preserved.

## Accepted implementation and evidence

Root [acceptance]({base}ADMISSION-ENVELOPE-SCOPED-ACCEPTANCE-v3.json), SHA `{args.acceptance_sha256}`, verifies **55 direct evidence pins** and binds the [final source peer]({base}{peer}), SHA `{peer_sha}`. The [combined freeze]({base}ADMISSION-ENVELOPE-ACTUAL-EVIDENCE-FREEZE-v3.json), `23d63277...`, binds the [final independent proof]({base}ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json), `5ba8af6c...`, and unchanged eight author controls. The [source]({base}admission_envelope_v3.py), SHA `24889920...`, is 17,145 bytes and imports only standard-library json, re and types. It does not import the application or previous source components.

The independent suite passes **nine methods**: four original interface methods covering **30 frozen metadata vectors**, four focused regressions and one additional regression within the numeric-type finding. The original vectors include one discriminating mixed-role equality case and **12 isolated one-over-limit cases**. The source executes 59 analyze calls (38 returns/21 exceptions), 488 checks (470 returns/18 original cancellation exceptions) and 113 getter calls. All 18 cancellation stops preserve original exception identity. The separate author suite passes eight methods/50 analyze calls. There are no active audit/import denials, failed comparisons or changed source/test pins in the final replay.

The API has seven exact input keys, 32 derived fields, four statuses, 12 nullable declared limits and 11 nullable positive representation coefficients. It validates bounded ordinary containers, lexical paths, IDs, roles, software/module binding and acyclic declared dependencies. Exact integer arithmetic refuses overflow. Known cap exceedance takes precedence over unrelated unknowns; absent assumptions never become zero. Reports retain canonical immutable JSON bytes and return detached containers. These are mathematical/metadata properties, not original-file verification or layout/RSS measurements.

## Corrections and retained chronology

The original 30-vector corpus/test module predates V1. Its first execution encountered 27 audited denials because CPython lazily loaded its trusted UTF-16 codec. The [runner correction]({base}ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json) preloads that codec before source loading and the active audit window. The original failure remains preserved; no active audit exception or source/oracle relaxation was added. The corrected runner then passed all 30 vectors.

Independent review retained [three source findings]({base}ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json). Four genuinely pre-fix methods [reproduced their failures]({base}ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json): a 4096-key built-in dictionary yielded every key before size refusal; an int subclass received the wrong error code; and aggregate mismatch or total overflow preempted a declared cycle. V2 changed only `_object`, `_integer` and `_steps`. The original 30 vectors, four new controls and author eight then passed.

The type correction introduced equality-based membership over type objects. One separately frozen [F2 probe]({base}ADMISSION-ENVELOPE-F2-METACLASS-BEFORE-v1.json) confirmed five producer metaclass equality calls despite a TYPE_DOMAIN result. V3 changes only `_integer` relative to V2, using identity alternatives. Its first replay passes all nine methods. The oversized dictionary now causes **zero key yields/resumptions**, ordinary numeric subclasses invoke no hooks, both cycle cases return MODULE_GRAPH, and the metaclass probe records **zero equality hooks**. Other helpers/constants/API remain unchanged; all eight author assertion bodies remain unchanged. No original expectation was edited to fit a source result.

V1/V2/V3 sources, first codec failure, corrected original pass, first author7/8, four before failures, V2 eight-method pass, F2 before failure, all frozen tests and corrective scopes remain retained. The final independent suite takes about 0.047 seconds. That pure-test duration does not establish real-file, process-memory, model or integrated feasibility.

## Feasibility implications and limits

The passing mixed-role fixture declares four files totaling 65,746 bytes, with 209 captured bytes and one hypothetical hash-only input. It produces Q5/R69/C93/E224, raw payload106819, journal229376, report12244, packet728, output245260 and peak595116 bytes **under fictitious declared coefficients**. Its R69/C93 exceeds the unchanged runtime R68/C92. The existing runtime also lacks the proposed hash-only role path. The packet bound uses declared overhead; it is not a qualified production packet format. No operational admission follows.

The retained old aggregate is 213 files / 9,017,363,392 bytes. With unknown per-file roles/sizes and unknown positive-file count, only informational ranges can be derived: R=137611-141215 and C=138889-142493 at 64 KiB. This is broader than the earlier all-positive conditional range; neither is a measured dispatch count. **Aggregate-only remains INDETERMINATE**, even with these ranges. The exact future approved roster and actual representation coefficients remain missing. No original was opened or hashed to produce this assessment.

Earlier storage warnings remain: query frames alone would retain 1,750,434 bytes against a131072-byte raw pool; the old213-entry closure list needs at least14588 bytes before other fields, over8192. The three owner/port/controller sources total58285 bytes, exceed file4096/capture16384/M2 limits, and are not self-hosted by the toy cohort. Indexing removes repeated work scans; this calculator resolves arithmetic, not producer representation, capture/stream implementation, full-source eligibility or physical storage. Paths retain the bounded C/D lexical policy; E: support requires a separate policy decision. Metadata SHA syntax is not actual hash verification.

All seven real qualification flags remain false. Runtime application/defaults/caps are unchanged. No actual Win32/FFI/SDK/C++/CPU/GGUF/model/tokenizer, original-source closure pass, old-run replay, physical publication, data download or paid query occurred in this component phase.

## Complete recovery status

{table}

AsOf 0.3.11/default v2 retains **1,774 passing full tests**, **327 source/resource pins** and ten matching preserved-version qualifications. The application suite was not rerun for this isolated component. Optional Arrow retains its prior baseline. Data/science still has **65 missing inputs**, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and **0/12** jointly source-ready clinical cases. Numerical prediction features remain empty, probabilities null and human reviews pending. Provider spending is $0. The download worker and stopped periodic monitor are untouched.

The consumed189-case native profile remains failed; its independent whole-verification remains **INCOMPLETE_TIMEOUT**. Those results are neither repaired nor repeated. Engineering peer review by agents does not complete independent human scientific review.

## Critical next major step

The immediate barrier is a real producer/storage/serialization contract and an explicit approved input vector. Arbitrary declared coefficients cannot unlock the operational profile. Close this gate before moving to physical activation.

1. **Select a concrete representation and its evidence.** Specify descriptor roles, captured software/metadata versus hash-only bytes, full canonical call retention, per-file/query witnesses, journal rows, report construction/copies and all five packet kinds. Bind an exact future roster and role/size vector from eligible provenance under a separately bounded metadata scope. Give each coefficient a layout/serialization basis and state residual interpreter/process overhead. Unknowns remain unresolved. A source aggregate, shallow object-size sample or passing synthetic calculation is insufficient. Acceptance requires a justified admissible representation and explicit refusal for unsupported inputs; otherwise retain the refusal and propose a study amendment.
2. **Implement and test the smallest producer change.** Version any new role/capture/report semantics and preserve previous sealed versions and their fixtures. First prove tiny hash-only/captured-role behavior, complete raw facts, context access restrictions, unknown outcomes, bounded report/output construction and interruption cleanup. Retain original clocks, identities, once-only rights and billing rules. No silent row dropping, invented capture completion or cap-only scaling. Operational limits remain unchanged until their own evidence supports a concrete amendment.
3. **Close actual entry, binding and publication.** Qualify the trusted entry/kernel and same Origin/class/nonce/registry across the real source closure. Specify startup exclusions and external watchdog. Review the fourteen typed exports and raw-first conversions, then separately qualify owned harmless fixtures, physical source/checker binding, sink/flush/close behavior, persisted hash-chain and new journal/archive/resource formats. Old known-v7 policy, fictional ACKs and this calculator cannot supply those proofs.
4. **Qualify native and integrated resources separately.** An exact source/header/build/parent/protocol decision is required for the distinct fixed84-document Unicode experiment. Preserve coverage and negative outcomes; do not repeat the consumed189-case profile. Full-vocabulary masking and integrated startup/source/retrieval/generation/accounting/cleanup measurements remain distinct. The retained295.922/300-second no-inference simulation leaves4.078 seconds and establishes no integrated fit. A failed gate requires a retained negative decision or explicit study amendment.
5. **Integrate minimally and resume science in order.** Require relevant regressions and installed/archive/relocation checks before a versioned application change. Finish R08 and HR1-HR3 before R10. Size/freeze H5 and analysis before locked R12. Clinical ascertainment, regional genetics/LD, training/calibration, comparisons and T2-T5/H6 remain individually conditional. Independent human submissions and scientific validation remain necessary for their gates.

This assessment authorizes no new runtime cap, original-input experiment, compiler/native execution or application activation. The next deliverable is the finite concrete producer/representation design and its pre-code controls.
"""
    destination = ROOT / "planning" / NAME
    assert not destination.exists()
    staged = {destination: assessment}
    documents = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md", "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md", "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"]
    for relative in documents:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        prefix = "planning/" if relative in ("README.md", "TODO.md") else ""
        current = f"Current checkpoint: [standalone admission envelope](<{prefix}{NAME}>) is accepted for SOURCE/PURE correctness (root `{short}`, peer `{peer_short}`). All30 pre-code vectors,12 isolated limit boundaries,five focused regressions and eight author controls pass; nine independent methods preserve18 original cancellation stops and immutable reports. Three validation findings plus one regression within the type fix are resolved; every before version/result remains preserved. Declared arithmetic grants no runtime authority; actual producer/storage/entry/FFI/source/native/resources and scientific/human gates remain open."
        text, count = re.subn(r"^Current checkpoint: .*?$", lambda _: current, text, count=1, flags=re.M)
        assert count == 1, relative
        next_step = "Next is the concrete role-aware producer/storage/serialization contract and approved roster, with coefficients justified by actual representations. The declaration-only calculator and indexed prototype do not establish full-roster fit. Keep runtime caps/defaults unchanged; source/physical/native activation requires its separate gates. AsOf0.3.11/defaultv2 retains1,774 full tests/327 pins/ten preserved-version qualifications; this component did not rerun the application suite."
        text, count = re.subn(r"^Next is a role-aware metadata admission envelope.*?$", lambda _: next_step, text, count=1, flags=re.M)
        assert count == 1, relative
        if relative == "README.md":
            text = text.replace(f"See the [current full-project reassessment](<planning/{OLD}>),", f"See the [current full-project reassessment](<planning/{NAME}>),", 1)
        if relative == "TODO.md":
            old = next(line for line in text.splitlines() if line.startswith("- [ ] Implement/review the finite role-aware metadata admission envelope"))
            done = f"- [x] Implement/review the standalone role-aware metadata calculator and declared storage/output arithmetic: root `{short}`, peer `{peer_short}`, freeze `23d63277`. Nine independent methods (original30 plus five focused), eight author controls and18 original check stops pass. Three findings and the F2 correction regression are fixed with pre-fix evidence retained; no runtime/cap/role activation."
            text = text.replace(old, done + f"\n- [ ] Reassess all R01-R16/HR1-HR4 after the admission envelope; retain {NAME} and current-document QA.\n- [ ] Select/qualify the concrete producer/role/storage/serialization representation and exact future roster; freeze finite pre-code controls before any operational profile or physical activation.", 1)
        if relative == "planning/Project Progress Reassessments.md":
            text += f"\n| R09 standalone metadata envelope accepted | [29 October UTC admission-envelope snapshot](<{NAME}>) | Root{short}/peer{peer_short};30 vectors/12 isolated bounds,five focused regressions,nine independent methods/eight author controls pass. All before evidence retained. Concrete producer/storage representation remains next; no full-roster/runtime/native/scientific authority. |\n"
        staged[path] = text
    log_text = f"""---
name: {LOG}
description: Accepted standalone metadata envelope, reproduced validation corrections and remaining producer gate
metadata:
  type: project
---

# Admission-envelope source checkpoint

Root `{args.acceptance_sha256}` and peer `{peer_sha}` accept source24889920
only for standalone SOURCE/PURE metadata arithmetic. Freeze23d63277 binds55 pins.
Nine independent methods pass: unchanged30/e670, four5644 and one F2 d158.
Eight unchanged author methods pass. Counts59 analyzes/488 checks/113 getters,
18 original cancellation stops; zero audit/import denials or changed inputs.

Before evidence remains: lazy-codec failure003b/correction9719; V1 author7/8;
four pre-fix failures8a02; V2 pass a294; metaclass hook failurec4c8.
V2 fixes bounded dictionary size refusal, subclass code and graph precedence;
V3 changes only the type guard to identity checks. Zero key yields and zero
producer hooks now pass. All expectation modules predate their relevant fixes.

Seven exact inputs/32 derived fields/four nonauthorizing statuses/12 limits/11
logical coefficients; nulls are explicit unknowns. The baseline R69/C93 exceeds
current R68/C92 and hash-only runtime support remains absent. Aggregate-only213
files/9017363392B remains indeterminate; R137611-141215/C138889-142493 are
informational ranges, not measured calls. No layout/RSS/full-roster fit follows.

The [full-project assessment](../planning/{NAME.replace(' ', '%20')}) covers all20
recovery/human rows and five next gates. Immediate next work is the concrete
producer/role/storage/serialization contract and exact approved roster, with
finite pre-code controls. Application0.3.11/defaultv2,1774 retained tests/327pins,
65 missing inputs,36 unqualified labels,17/32 registry states,0/12 source-ready
clinical cases, empty features/null probabilities and pending humans remain.
Old FAILED/INCOMPLETE_TIMEOUT are not repaired or repeated. Provider$0; downloader
and stopped monitor untouched. No new original/native/model/physical activity.
"""
    log_path = ROOT / "memory" / (LOG + ".md")
    assert not log_path.exists()
    staged[log_path] = log_text
    path = ROOT / "memory/MEMORY.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("# Research memory index\n", f"# Research memory index\n\n- [[{LOG}]] - Root{short}/peer{peer_short}: standalone metadata calculator accepted;30 original vectors/five focused regressions,9 independent methods/8 author controls,55 evidence pins. Prior failures preserved. Concrete producer/storage/serialization and actual entry/native/science/human gates stay open.\n", 1)
    staged[path] = text
    path = ROOT / "memory/project-goals.md"
    text = path.read_text(encoding="utf-8")
    start, end = text.index("Current source-only checkpoint:"), text.index("Raw-adoption5afb82f0")
    text = text[:start] + f"""Current source-only checkpoint: [admission envelope](../planning/{NAME.replace(' ', '%20')}).
Root{short}/peer{peer_short} accepts standalone source24889920; freeze23d63277
binds55 pins. Nine independent methods (30 original vectors,five focused) and
eight author controls pass. All18 cancellation exceptions preserve identity;
reports are deeply immutable/detached. Three source findings and one regression
within F2 are fixed. Original sources,before proofs and codec setup failure
remain preserved. See [[{LOG}]] for exact chronology and counts.

This is declared metadata arithmetic only: no actual producer representation,
source authenticity, hash-only streaming implementation, measured RSS/time or
runtime admission. The synthetic R69/C93 exceeds existing R68/C92. Actual role/
size vector and layout coefficients remain missing. Aggregate-only213 files/
9017363392B yields informational R137611-141215/C138889-142493, stays indeterminate.
Next is a concrete role-aware producer/storage/output contract and exact roster
with finite pre-code controls; cap/physical activation requires separate gates.
Application0.3.11/defaultv2 and all real flags stay unchanged. Old189-case FAILED
and INCOMPLETE_TIMEOUT remain;65 missing inputs/36 unqualified labels/17of32
registry states/0of12 clinical cases and pending human review remain unresolved.

""" + text[end:]
    staged[path] = text
    for path, text in staged.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"documents_updated": len(staged), "assessment": str(destination), "root": short, "peer": peer_short}))


if __name__ == "__main__":
    main()
