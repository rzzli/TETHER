"""Update repository status at a scoped source-only completion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "Project Progress Reassessment 2026-10-29 - Captured Archive Checker.md"
NEW = f"planning/{NAME}"
OLD = "Project Progress Reassessment 2026-10-29 - In Memory Unicode Codec.md"


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative, text):
    (ROOT / relative).write_text(text, encoding="utf-8", newline="\n")


assessment = """# Project reassessment after the captured archive checker

29 October 2026 UTC. The corrected archive checker is accepted for source and pure tests. R09 and the complete project remain unfinished. No new native experiment, old payload pass or actual archive replay occurred. The installed C++ tools already worked without restarting.

Root [acceptance](review-assets/recovery-step9-archive-bytes-20261029/CAPTURED-ARCHIVE-CHECKER-SCOPED-ACCEPTANCE-v3.json), SHA `686dcf476b13e117badbae2d5bff4276859219bb3cbc704be5a31af513edcd8e`, binds source `90ba49a9...`, thirteen authored test methods, all 32 frozen synthetic projections and seven independent peer methods ([peer](review-assets/recovery-step9-archive-bytes-20261029/CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v3.json), `d562bcfd...`). The checker consumes caller-captured bytes and declared metadata. It checks bounded schemas, locators, source-map relationships, hashes and the acyclic publication graph while retaining negative and incomplete dispositions. It authenticates no original file, directory universe, owner, complete journal or resource/profile semantics.

The two v2 defects are reproduced in fully rebound synthetic captures: a legitimate already-closed lease has null close_success, and a 1001-digit invalid periodic interval raised OverflowError during floating conversion. V3 admits only the documented unattempted/closed null shape and checks integers without coercing them to float. Invalid periodic intervals produce data rejection. The peer confirms 57 other top-level ASTs are unchanged, including the entry and analysis paths. Earlier callback-identity and exact-one-LF fixes remain intact; callback OverflowError is still propagated as the original object. All prior sources, failed probes and peer HOLDs remain preserved ([correction evidence](review-assets/recovery-step9-archive-bytes-20261029/CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json)). Passing the captured graph is not a cleanup qualification or successful real-run verification.

The corrected [in-memory codec](review-assets/recovery-step9-unicode-codec-20261029/UNICODE-PACK-CODEC-SCOPED-ACCEPTANCE-v2.json), `3455f282...`, retains eleven author/eleven independent methods, three focused regression methods and 720 callback identity probes. Its 37,766-byte complete encoding existed only in test memory. The accepted oracle, supplied-piece analyzer, bootstrap interfaces, captured journal and Job-byte primitive keep their existing source-only scopes. None supplies actual source, runtime or scientific authority.

The file-port design has independently cleared its metadata-only drive-root correction. Root [fixture-scope decision](review-assets/recovery-step9-file-ports-20261029/FILE-PORTS-ROOT-FIXTURE-SCOPE-v1.json), `0253bda8...`, now permits concrete simulated API/clock/ownership vectors for all sixteen design fault families and a coherent success baseline. No port implementation or live API qualification exists. Unicode observation design v1 separately needs three clarifications before complete trace fixtures: elapsed-time samples, terminal failure ordering and external runtime context versus codec-bound metadata ([design review](review-assets/recovery-step9-unicode-observations-20261029/UNICODE-OBSERVATIONS-INDEPENDENT-DESIGN-REVIEW-v1.json), `384385f3...`). Corrected design work is underway; no trace validator is accepted.

The original 189-case profile remains failed; the original independent whole-check remains INCOMPLETE_TIMEOUT. Later source checks do not repair either. No old CPU/GGUF/pack access, SDK/compiler/native invocation, new download or provider spending belongs to this checkpoint. Full-vocabulary masking, integrated resources and scientific usefulness remain unqualified.

## Complete recovery status

| Item | Current status and remaining gate |
|---|---|
| R01 | Accepted scope, governance and exposure boundaries. |
| R02 | Accepted tested checkpoint and restoration inventory. |
| R03 | Accepted scoped archive compatibility/relocation; complete raw/model/host restoration separate. |
| R04 | Accepted reproduced core correctness fixes. |
| R05 | Accepted bounded diagnostic preparation; stronger-model sufficiency unresolved. |
| R06 | Accepted reusable infrastructure slice. |
| R07 | Technical diagnostic closed negative; independent human assessment pending. |
| R08 | Partial source/exposure preparation; no scientifically qualified fresh case. |
| R09 | Application 0.3.11 and scoped pure components, in-memory codec and captured graph checker accepted. Actual platform/entry/engine, source/owner/archive/resource/profile binding, native coverage, masking, integrated resources and usefulness remain unfinished. |
| R10 | Independent human development pilot pending source, engineering and human prerequisites. |
| R11 | H5 estimand, power, amended protocol/preregistration and analysis freeze pending. |
| R12 | Locked H5 execution/report pending qualified mechanics, protocol and final panel. |
| R13 | Alternative clinical outcome source conditional and unqualified. |
| R14 | Regional genetics/compatible LD, causal features, predictors and scoring/calibration conditional and unqualified. |
| R15 | Original clinical comparisons and ablations conditional and pending. |
| R16 | Individually gated T2–T5/H6 extensions and reproducible release pending. |
| HR1 | Human recruitment, domain matching, conflicts and exposure records pending. |
| HR2 | Two independent orientation submissions and measured workload pending. |
| HR3 | Fresh source-only references, reviewer coverage and masked ratings pending. |
| HR4 | Sized final panel and independent adjudication pending. |

AsOf 0.3.11/default v2 is unchanged: 1,774 retained passing full tests, 327 source/resource pins and ten matching preserved-version qualifications. This private component checkpoint did not rerun the full application suite. Optional Arrow remains 755 unchanged files plus five separately source-equivalent caches. Data/science remains 65 missing inputs, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and 0/12 jointly source-ready clinical cases. Numerical prediction features stay empty and probabilities null. Independent human reviews are still pending. Provider spending is $0; the download worker and stopped periodic monitor are untouched.

## Critical next step and order

1. Freeze independently reviewable simulated file-port inputs and exact expected calls/results before implementation. Cover all sixteen required families, a full success sequence, UTF16-unit path limits, unknown/null returns, identity failure after acquisition, short/undefined reads and writes, correct once-only closers, namespace ownership before readiness and final-clock failure. Reject a fixture set that supplies only prose promises or recreates expected outputs from the implementation being tested.
2. Implement the minimal file/source/output logic against those closed fake APIs, preserving original-clock ownership and the existing disabled launch SDK. Verify known counts before hashing or callbacks, retain late immutable write evidence without a positive pin, keep partial namespaces and slots, and permit no API dispatch after the hard cutoff. Separate source acceptance from later harmless real-file qualification. Any unregistered acquisition, guessed close, uncertain retry, recursive journal accounting or positive publication after unknown cleanup must fail this gate.
3. Close the Unicode observation design, then freeze complete fictional positive, negative and partial traces before the validator. Enforce all fifteen setup rows, 84 before/result pairs, exact coverage/selection, de-duplicated original-token prefix controls and cleanup/footer order. Recompute geometry and accounting; distinguish collection completeness from native truth and profile qualification. Runtime descriptors are externally declared, not supplied by the codec profile. After source validation, separately implement and review the new child/parent; no old success constants or favorable boundary substitution.
4. Integrate the real first-clock entry, closed captured-source loader, fresh leases, complete role roster, acyclic archive/resource graph, output sink and production engine. Count every bootstrap and remaining source once, retain unknown returns and original deadlines, and admit exact calls/events/capture/report bounds before dispatch. Pure components do not establish that the actual roster or complete verification fits 300 seconds. Preserve the 295.922/300-second no-inference warning and stop on budget or authority failure rather than dropping checks.
5. Separately qualify file mechanics, a distinct once-only native Unicode protocol, full-vocabulary masking and integrated case resources, then versioned application/installed/archive/relocation behavior. Complete R08 and HR1–HR3 before R10; size/freeze H5 before locked R12. Clinical ascertainment, genetics/LD, calibration, competitors and T2–T5/H6 remain individually gated. Agent review cannot substitute for pending independent human submissions.

These steps advance the existing plan. They do not authorize a repeat of the consumed native attempt or timed-out original verification, extra data acquisition, paid execution or scientific claims.
"""
assert not (ROOT / NEW).exists()
write(NEW, assessment)

# Keep current entry points concise; dated narratives and prior snapshots stay intact.
for relative in (
    "README.md", "TODO.md",
    "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md",
    "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
):
    text = read(relative)
    if relative == "README.md":
        old = "callback identity probes. Real platform/entry/resource/archive/profile integration\nand actual Unicode coverage remain unfinished."
        new = "callback identity probes. The corrected captured-graph checker now passes thirteen\nauthor methods, all 32 fixtures and seven independent methods (acceptance686dcf47).\nReal platform/entry/source/resource/profile integration and actual Unicode coverage\nremain unfinished."
        assert old in text
        text = text.replace(old, new, 1)
    if relative == "TODO.md":
        start = text.index("Current checkpoint:")
        end = text.index("\nOracle107", start)
        text = text[:start] + f"Current checkpoint: [captured archive checker](<planning/{NAME}>), acceptance686dcf47: thirteen author/seven independent methods and all32 frozen projections pass after nullable-close and integer-overflow corrections. Only source/pure graph consistency is accepted; actual platform/entry/engine/source/resource/profile and native qualification remain unfinished." + text[end:]
        old = "- [ ] Correct archivechecker's source-valid null close_success and huge interval integer handling; preserveHOLD1a48b0e0 and independently review narrowv3 before acceptance."
        new = "- [x] Correct/review archive checker v3 source90ba49a9:13author/7independent methods and all32 frozen projections pass; acceptance686dcf47. Preserve v2 HOLD1a48b0e0, fully rebound before/after evidence and callback/LF fixes. Captured graph only; no actual archive/source/owner/resource/profile qualification."
        assert old in text
        text = text.replace(old, new, 1)
    if relative.endswith("Project Recovery and Evaluation Plan 2026-10-26.md"):
        start = text.index("Current checkpoint:")
        end = text.index("\n\nAsOf", start)
        text = text[:start] + f"Current checkpoint: [the captured archive checker](<{NAME}>) is accepted for source and pure tests: thirteen author/seven independent methods and all32 frozen projections pass. Source-shaped null-close and huge-integer handling are corrected with preserved before/after evidence. File-port fake vectors and complete Unicode observation design/fixtures are next; actual platform/entry/engine/source/resource/profile and native qualification remain unfinished. Original failures stay unchanged. AsOf0.3.11/default v2 and the [ordered plan](<R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md>) remain in force." + text[end:]
    if relative.endswith("Recovery Status and Next Gates 2026-10-26.md"):
        start = text.index("Current checkpoint:")
        end = text.index("\n\nThe native-build", start)
        text = text[:start] + f"Current checkpoint: [the corrected captured archive checker](<{NAME}>) passes thirteen author/seven independent methods and all32 frozen projections; root acceptance686dcf47 covers captured metadata graph consistency only. File-port simulated vectors and corrected complete-observation design precede source implementation. Actual platform, entry, engine, source, resource and native qualification remain unfinished. The original profile remains failed and its whole-check INCOMPLETE_TIMEOUT. The following dated narratives are historical." + text[end:]
    if relative.endswith("R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"):
        start = text.index("**Execution update,")
        end = text.index("\n\n## Ordered", start)
        text = text[:start] + f"**Execution update, 29 October UTC:** the pure oracle, controller, source fixtures, analyzer, corrected bootstrap, journal, Job-byte primitive and in-memory codec retain scoped acceptance. The corrected captured archive checker now passes13author/seven peer methods/all32 projections, acceptance686dcf47. Source-valid null-close and huge-integer defects are fixed without broader cleanup qualification. Next: closed file-port fake vectors and complete Unicode observation design/trace fixtures. Actual platform/entry/engine/source/resource/profile and new native qualification remain unfinished. No complete runtime pack was persisted. The [current reassessment](<{NAME}>) records all recovery and human gates." + text[end:]
    if relative.endswith("Project Progress Reassessments.md"):
        # Do not rewrite the historic codec row; append a new dated checkpoint.
        text += f"\n| R09 corrected captured archive checker accepted in source/pure scope | [29 October UTC graph-checker snapshot](<{NAME}>) | Thirteen author/seven peer methods and all32 frozen projections pass; source-shaped nullable-close and huge-integer defects resolved with prior evidence preserved. Actual platform/entry/source/owner/resource/profile/native and human/scientific gates remain open. |\n"
    else:
        text = text.replace(OLD, NAME)
    write(relative, text)

relative = "memory/project-goals.md"
text = read(relative)
start = text.index("Current source-only checkpoint:")
end = text.index("Acceptance `3e80ae97", start)
text = text[:start] + f"""Current source-only checkpoint: [captured archive checker](../planning/{NAME.replace(' ', '%20')}).
Acceptance `686dcf47...` binds corrected source `90ba49a9...`, thirteen author
methods, all32 frozen projections and seven independent methods. Legitimate
already-closed null results and huge interval integers now follow their intended
source/data rules; peer `d562bcfd...` confirms57 other ASTs unchanged. V2 HOLD,
two fully rebound before/after cases and earlier callback/LF fixes are preserved.
This is captured graph consistency, without original/source/directory/owner or
resource/profile qualification. File-port design preparation is accepted; root
`0253bda8...` permits concrete fake vectors, no port implementation or live API.
Observation design-v1 review `384385f3...` requests elapsed/failure/runtime-context
clarifications before complete trace fixtures. Actual entry/engine/platform and
native qualification remain unfinished. Codec acceptance `3455f282...` retains
eleven author/eleven independent methods and720 callback identity probes; its
37766-byte pack existed only in memory. Original negative/timeout are unchanged.
""" + text[end:]
write(relative, text)

relative = "memory/MEMORY.md"
text = read(relative)
start = text.index("- [[research-log-2026-10-29-r09-unicode-controls]]")
end = text.index("\n", start)
text = text[:start] + "- [[research-log-2026-10-29-r09-unicode-controls]] — Source/pure codec and corrected captured graph checker accepted: archive13author/7peer methods/all32 projections; null-close/huge-integer defects resolved with prior failures preserved. File-port fake vectors and corrected observation design precede implementation. Actual platform/entry/engine/source/resource/profile/native and science/human gates remain open; no restart or retry." + text[end:]
write(relative, text)

relative = "memory/research-log-2026-10-29-r09-unicode-controls.md"
text = read(relative)
text += """

## Captured archive checker correction accepted

Root acceptance `686dcf47...` binds source `90ba49a9...`, author proof
`cfde0f81...` (13 methods/all32 frozen synthetic projections), freeze
`43041bff...` and independent peer `d562bcfd...` (seven methods, after proof
`6f730def...`). Both v2 findings reproduce with fully rebound synthetic maps:
source-valid already-closed close_success:null and giant periodic interval
OverflowError. V3 corrects only those source/data boundaries; callback identity,
strict LF and57 other ASTs are unchanged. V1/v2 and every HOLD/witness remain.
Acceptance covers captured metadata graph consistency only; actual directory,
original/source authentication, owner, complete journal and resource/profile
qualification remain false. No old actual archive or payload replay occurred.

Root `0253bda8...` accepts file-port design preparation and permits concrete fake
API/clock/ownership vectors for sixteen required families and a success baseline.
No port implementation or live file/API operation. Observation design peer
`384385f3...` requires elapsed sample, failure ordering and external runtime
context clarification before complete trace fixtures. Source work continues.
The full20-row project reassessment is retained at
[captured archive checker checkpoint](../planning/Project%20Progress%20Reassessment%202026-10-29%20-%20Captured%20Archive%20Checker.md).
AsOf0.3.11/default v2, original negative/timeout, scientific/human holds, provider
$0 and untouched downloader/stopped monitor remain unchanged.
"""
write(relative, text)
print("Updated current repository documentation and retained a new full-project reassessment.")
