"""Retain the project-wide reassessment at portable-source acceptance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME = "Project Progress Reassessment 2026-10-29 - Portable File Ports.md"
NEW = "planning/" + NAME
PREVIOUS = "Project Progress Reassessment 2026-10-29 - Unicode Observation Validator.md"


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative, text):
    (ROOT / relative).write_text(text, encoding="utf-8", newline="\n")


previous = read("planning/" + PREVIOUS)
start = previous.index("| Item | Current status")
end = previous.index("\n\nAsOf0.3.11", start)
table = previous[start:end]
lines = table.splitlines()
lines = ["| R09 | Application0.3.11 and scoped pure components, codec, captured graph, Unicode observer and injected portable file logic accepted. Real FFI/entry/shared-owner/engine/source/new-parent/resource/profile/native, masking, integrated resources and usefulness remain unfinished. |" if line.startswith("| R09 |") else line for line in lines]
table = "\n".join(lines)
intro = """# Project reassessment after portable file handling

29 October 2026 UTC. Portable file handling is accepted for injected source/pure tests. This completes another engineering component; R09 and the complete project remain unfinished. Actual Windows file binding, first-entry timing and the shared bootstrap/engine owner remain unqualified. The installed C++ tools work without restarting.

Root [acceptance](review-assets/recovery-step9-file-ports-20261029/PORTABLE-FILE-PORTS-SCOPED-ACCEPTANCE-v2.json), SHA `16d65f572019a86b466d684f5c67b330140de85362829abad7a19330ee4d318a`, binds source `b7785bd6...`, the published 84-case fixture set `e1fd8d21...`, all21focused methods and nine independent probes ([peer](review-assets/recovery-step9-file-ports-20261029/PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.json), `56b57f3c...`). The published [behavioral proof](review-assets/recovery-step9-file-ports-20261029/PORTABLE-FILE-PORTS-BEHAVIORAL-PROOF-v2.json), `246baec6...`, records84/84matches,199simulated API attempts/193returns and zero script mismatches. These calls are fictional; no Windows file API is qualified by these counts.

Three source boundaries are now corrected. Content reads/writes require the same owner/nonce/slot/handle/path/spec identity witness from successful identity checks; changing identity_ok alone cannot grant it. Entered unreturned writes retain unknown counts and the original interruption. Read accounting distinguishes an admitted/entered call from a deadline preventing dispatch and retains unknown counts for malformed returned values. Independent controls verify zero reads at the295work cutoff, zero writes at300, correct closure rights, and retained known late bytes. Primitive seeded identities require a separate test capability and remain explicitly fictional.

The first 65/84 behavioral result, source-v1 and the intermediate pre-read candidate remain preserved. The independently reviewed [fixture publication decision](review-assets/recovery-step9-file-ports-20261029/PORTABLE-FILE-PORTS-ROOT-FIXTURE-PUBLICATION-v4.json), `c35f9802...`, applies the exact proposal to13scripts/18cases with66unchanged: required fresh clocks and no-op logging checkpoints, a coherent namespace/reservation prefix, immutable primary errors and explicit diagnostic choices. API raw outcomes, injected faults and advancing times are retained. Old fixtures, earlier limited preparation reviews, before probes and root/reviewer metadata-helper mistakes remain visible. Corrections did not remove source work guards to obtain a pass.

The [Unicode observer](review-assets/recovery-step9-unicode-observations-20261029/UNICODE-OBSERVATIONS-SCOPED-ACCEPTANCE-v2.json), `743ece01...`, separately retains14author methods, six complete histories/36scenarios,33observe+22strict callback controls,22nested/type mutations, four independent probes and two root regressions. Captured graph, codec, byte oracle, supplied-piece analyzer, bootstrap/journal and Job-byte acceptances keep their scopes. Neither portable file logic nor a consistent captured trace supplies actual source, process, owner, clock, resource or native truth.

The critical remaining boundary is concrete. The fake RawReturn object already exists before portable code sees it. A real binding must adopt the C-returned scalar handle/flag/count in shared preallocated slots before constructing that object or doing error-copy, clock, formatting or hash work. If a wrapper then fails, the outer port must preserve that known inner ownership and distinguish native return from portable return without double-counting. This is application ordering after FFI conversion, not an atomic OS-to-Python guarantee. The real binding and adoption seam are not implemented or qualified.

The original 189-case profile remains failed; its original independent whole-check remains INCOMPLETE_TIMEOUT. No old CPU/GGUF/pack pass, actual old-run replay, original source-closure qualification, compiler/SDK/native invocation, data download or provider spending occurred. The old launch SDK remains disabled. The accepted old known-v7 --recognize journal/archive policies cannot qualify the future Unicode parent by changing a caller binding.

## Complete recovery status

"""
baseline = """

AsOf0.3.11/default v2 remains unchanged: 1,774 retained passing full tests,327source/resource pins and ten matching preserved-version qualifications. This private-component checkpoint did not rerun the full application suite. Optional Arrow remains755unchanged files plus five separately source-equivalent caches. Data/science remains65missing inputs, nine exposed IL6R observations,36unqualified endpoint labels,17/32observable primary registry states and0/12jointly source-ready clinical cases. Numerical prediction features remain empty and probabilities null. Human reviews are pending; provider spending is$0. The download worker and stopped periodic monitor are untouched.

## Critical next step and order

1. Freeze and independently review the actual raw-FFI/shared-owner interface before code. Map the accepted portable methods to preallocated raw-return slots and define native-entered/native-returned/portable-returned observations separately. Fault expectations must cover an acquisition followed by error-copy/object/copy/clock failure, valid inner ownership surviving an outer exception, known counts before further work, unknown handles without guessed closure, distinct once-only closers and pending late buffers. Keep ordinary test capabilities separate from production authority. The interface must identify how the same Origin, nonce, registry, namespace, output and journal survive handoff; a second session with the same numeric start is insufficient.
2. Implement a separately versioned inactive binding/bootstrap/continuation source against those closed faults. The [six-gap review](review-assets/recovery-step9-verifier-adapters-20261029/ENGINE-CONTINUATION-INTEGRATION-GAP-v1.md), JSON69dfb4a4, requires one time/identity owner, one live registry and reserved output, exact adoption of early captured bytes once, one closed source loader/journal, the acyclic finalization sequence and actual raw-return registration. Calling run_once after handoff creates another owner and reservation. Require the first real entry before helper imports/source checks, exact early/full roster admission and actual event/capture/report sizing. No arbitrary import, cached own module, serialized ready marker, repeated early hash or duplicated closer may complete this gate. Source tests remain distinct from real platform qualification.
3. Qualify harmless real-file mechanics under a separate concrete decision, using new owned local fixtures. Check14typed exports, declared Win64 layouts/flags and same-handle disk/nonreparse/path/size identity, real synchronous reads/writes, partial returns, reserved output, final acknowledgment and cleanup. Include binding/source-loader/import work under the original clock and disclose interpreter/platform prerequisites. Do not infer actual roster, path-policy or300-second fit from algebra or simulated counters. Original model/source inputs and a native child remain outside this harmless stage until separately admitted.
4. Implement/review the new Unicode child/parent and exact new journal/archive/resource policies, then separately qualify the source/header/build closure and distinct once-only native protocol. Preserve all84cases, whole-source population, deterministic first/de-duplicated controls, full ledgers, row caps, failure/partial states and cleanup. Full-vocabulary masking and integrated resources remain separate. The295.922/300-second no-inference result still leaves only4.078seconds;16passes/133.933GiB is a logical source estimate, not a physical or timing measurement. Preserve the consumed profile and expired verification without repetition or favorable case replacement.
5. Make a minimal application integration only after its exact gates pass, with relevant regressions and installed/archive/relocation checks. Complete R08 andHR1–HR3 beforeR10; size/freeze H5 and its analysis before lockedR12. Clinical ascertainment, regional genetics/compatible LD, calibration, competitors andT2–T5/H6 keep their individual prerequisites. Agent review cannot create independent human responses or biological validation.

The next major task is the shared-owner raw-return and continuation boundary. Portable source acceptance removes a prerequisite; it does not complete real execution or the project.
"""
assert not (ROOT / NEW).exists()
write(NEW, intro + table + baseline)

paths = ("README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
    "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md",
    "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md")
for relative in paths:
    text = read(relative)
    if relative == "README.md":
        old = "Portable file handling is still under correction; real platform/entry/source/\nresource/profile integration and actual Unicode coverage remain unfinished."
        new = "Injected portable file handling now passes84published cases,21focused methods\nand nine independent probes (acceptance16d65f57). Actual raw FFI, first-entry/shared-\nowner/engine/source/resource/profile integration and native coverage remain unfinished."
        assert old in text; text = text.replace(old, new, 1)
    if relative == "TODO.md":
        start = text.index("Current checkpoint:"); end = text.index("\nOracle107", start)
        text = text[:start] + f"Current checkpoint: [portable file handling](<planning/{NAME}>), acceptance16d65f57:84published cases,21focused methods and9independent probes pass. Unicode observer743ece01 and earlier pure components retain scoped acceptance. Actual rawFFI/first-entry/shared-owner/engine/source/new-parent/resource/profile/native and scientific gates remain unfinished." + text[end:]
        replacements = {
            "- [ ] Implement/review portable file ownership, metadata, read/write, deadline and publication logic against the frozen84 cases; production origin/source/FFI adoption and actual file qualification stay separate.": "- [x] Implement/review injected portable file logic b7785bd6, acceptance16d65f57:84published cases/21focused methods/9independent probes pass. Actual rawFFI, production origin/source adoption and real file qualification remain separate.",
            "- [ ] Resolve the first portable behavioral batch644fa49d (65/84 match): correct the unreturned-write unknown-count bug and independently review explicit fixture clock/hook/namespace omissions, primary retention and diagnostic expectations. Preserve every prior fixture/source/proof; no weaker checks to obtain a pass.": "- [x] Resolve first65/84 batch with identity-before-content, unreturned-write and read-admission/malformed-count source guards, exact13script/18case corrections and immutable primary. Publishedproof246baec6/corebcc8a865/peer56b57f3c pass; all before sources/fixtures/proofs preserved without weaker clocks/hooks.",
        }
        for old, new in replacements.items():
            assert old in text; text = text.replace(old, new, 1)
    if relative.endswith("Project Recovery and Evaluation Plan 2026-10-26.md"):
        start = text.index("Current checkpoint:"); end = text.index("\n\nAsOf", start)
        text = text[:start] + f"Current checkpoint: [injected portable file handling](<{NAME}>) is accepted after84published cases,21focused methods and9independent probes, acceptance16d65f57. All source/fixture failures remain preserved. Unicode observer743ece01 and earlier pure components retain scope. Next: actual raw-return/shared-owner/entry/continuation interfaces and closed faults; real FFI, new-parent policies, native/resources and science remain unfinished. AsOf0.3.11/defaultv2 and the [ordered plan](<R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md>) are unchanged." + text[end:]
    if relative.endswith("Recovery Status and Next Gates 2026-10-26.md"):
        start = text.index("Current checkpoint:"); end = text.index("\n\nThe native-build", start)
        text = text[:start] + f"Current checkpoint: [portable file handling](<{NAME}>) is accepted for injected source/pure behavior:84published cases,21focused methods and9independent probes, acceptance16d65f57. The next raw-FFI/shared-owner/first-entry/continuation gate remains unimplemented. Actual source/resource/new-parent/native and human/scientific qualification are pending; the original profile and INCOMPLETE_TIMEOUT stay unchanged. The following dated narratives are historical." + text[end:]
    if relative.endswith("R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"):
        start = text.index("**Execution update,"); end = text.index("\n\n## Ordered", start)
        text = text[:start] + f"**Execution update,29October UTC:** source/pure portable file handling now passes84published cases/21focused methods/9independent probes, acceptance16d65f57. Unicode observer743ece01 and previous components retain their scopes. All first failures and separate corrections are preserved. Next: exact raw-FFI/shared-owner/entry/continuation interfaces and closed fault expectations. Actual FFI/source/new-parent/resource/native and scientific qualification remain unfinished. No runtime pack file or new native experiment. The [current reassessment](<{NAME}>) covers all20recovery/human statuses and five critical next gates." + text[end:]
    if relative.endswith("Project Progress Reassessments.md"):
        text += f"\n| R09 injected portable file logic accepted | [29 October UTC portable-source snapshot](<{NAME}>) |84published cases/21focused methods/9independent probes pass after three accounting/identity guards and exact fixture repairs. Actual rawFFI/shared-owner/entry/engine/new-parent/resource/native and human/scientific gates remain open.|\n"
    else:
        text = text.replace(PREVIOUS, NAME)
    write(relative, text)

relative = "memory/project-goals.md"
text = read(relative); start = text.index("Current source-only checkpoint:"); end = text.index("Acceptance `3e80ae97", start)
text = text[:start] + f"""Current source-only checkpoint: [portable file handling](../planning/{NAME.replace(' ', '%20')}).
Acceptance16d65f57 binds b7785bd6,84published cases,21focused methods and9peer
probes56b57f3c. Identity-before-content, unknown writes and read admission/count
guards pass; exact13script/18case corrections preserve66cases and all raw faults.
First65/84, intermediate source, before probes and every old fixture remain.
No realFFI/first-entry/shared-owner/engine/source/resource/profile/native gate is
qualified. A returned fake object cannot prove raw C-return adoption before
object construction; known inner ownership/bytes must survive wrapper failure.
The concrete next-gate design and closed faults are in preparation.
Unicode observer743ece01 retains14author methods,6histories/36scenarios,55callback
identity controls,22nested/type mutations,4independent probes and2rootregressions.
Earlier graph686dcf47, codec3455f282 and other pure components retain scope. Oldv7
--recognize journal/archive policies require new exact Unicode counterparts.
Same-owner review69df identifies six adoption gaps; no run_once/time/registry
reset is allowed. Original negative/timeout,65missinginputs/36unqualifiedlabels,
0/12source-ready clinical cases, emptyfeatures/nullprobabilities and human holds
remain. Provider$0 and untouched downloader/stopped monitor are unchanged.
""" + text[end:]
write(relative, text)

relative = "memory/MEMORY.md"
text = read(relative); start = text.index("- [[research-log-2026-10-29-r09-unicode-controls]]"); end = text.index("\n", start)
text = text[:start] + "- [[research-log-2026-10-29-r09-unicode-controls]] — Portable16d65f57 accepted injected source/pure:84published cases/21focused methods/9peer probes; three source guards/exact fixture repairs preserve prior failures. Observer743ece01 and earlier components retain scope. RawFFI/shared-owner/entry/engine/new-parent/resource/native and human/scientific gates remain open; old profile/timeout unchanged." + text[end:]
write(relative, text)

relative = "memory/research-log-2026-10-29-r09-unicode-controls.md"
text = read(relative) + f"""

## Injected portable file handling accepted

Acceptance16d65f57 binds sourceb7785bd6, componentd7fb7763, core21bcc8a865,
published84/84proof246baec6 and independent9probes7bad3fba/peer56b57f3c. Literal
v4e1fd8d21 applies exact13scripts/18changed/66unchanged after rootc35f9802 and
independent d280/9f00 reviews. Three source guards cover identity before content,
unknown entered writes and read dispatch/defined-count semantics. First65/84,
pre-read snapshot87f6, before159ec/5e053, primaryc651 and all old fixtures/proofs
remain.199/193are fake API attempts/returns, not observed Windows calls.

Ordinary owner-bound identity witnesses and a separate harness-only seed cap
pass. Actual FFI raw-return adoption before object construction, one real start/
owner/registry/output/loader/journal, exact roster and new Unicode policies remain
pending. The next design maps accepted concrete APIs to those gaps; no real
binding or runtime is active. Observer743ece01 and other pure acceptances retain
scope. Full reassessment: [{NAME}](../planning/{NAME.replace(' ', '%20')}).
AsOf0.3.11/defaultv2/retained1774tests/327pins, data/science/human holds, original
negative/timeout, provider$0 and untouched downloader/stopped monitor remain.
"""
write(relative, text)
print("Retained portable full-project reassessment; updated ten current repository documents.")
