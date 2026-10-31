"""Update current repository status after exact scoped root acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Indexed Accounting.md"


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-sha256", required=True)
    args = parser.parse_args()
    raw = (HERE / "INDEXED-ACCOUNTING-SCOPED-ACCEPTANCE-v3.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.acceptance_sha256
    acceptance = json.loads(raw)
    assert acceptance["status"] == "ACCEPTED_V3_INDEXED_ACCOUNTING_SOURCE_PURE_N4_ONLY"
    peer_name = next(n for n in acceptance["inputs"] if "SOURCE-INDEPENDENT-PEER" in n)
    peer_sha = acceptance["inputs"][peer_name]["sha256"]
    short, peer_short = args.acceptance_sha256[:8], peer_sha[:8]
    prefix = "review-assets/recovery-step9-indexed-accounting-20261029/"
    old_name = "Project Progress Reassessment 2026-10-29 - Shared Owner Continuation.md"
    previous = (ROOT / "planning" / old_name).read_text(encoding="utf-8")
    table = previous.split("| Item | Current status and remaining gate |", 1)[1].split("\n\nAsOf", 1)[0]
    rows = table.splitlines()
    for index, row in enumerate(rows):
        if row.startswith("| R09 |"):
            rows[index] = "| R09 | Application 0.3.11, small shared-owner V2 and indexed N4 V3 accepted in their exact scopes. Role/storage/output admission, actual entry/FFI/source/physical publication/new format/resource/native/masking/integrated/scientific gates remain unfinished. |"
    table = "| Item | Current status and remaining gate |" + "\n".join(rows)
    assessment = f"""# Project reassessment after indexed accounting

29 October 2026 UTC. The indexed-accounting successor is accepted for new-source/pure tests under the unchanged N<=4 profile. Normal handle lookup, read totals, call-reference checks and read reservation no longer traverse the global call history. R09 and the complete project remain unfinished. The C++ toolchain works without restarting.

This is a project-wide **status reconciliation** against retained evidence, with fresh verification of this component. It is not a new scan or execution of the complete application, original datasets, consumed native experiment or protected answers. The prior [shared-owner assessment](<{old_name}>) and all earlier dated findings remain preserved.

## Evidence and implementation

Root [acceptance]({prefix}INDEXED-ACCOUNTING-SCOPED-ACCEPTANCE-v3.json), SHA `{args.acceptance_sha256}`, verifies all **31** pins in the [evidence freeze]({prefix}INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json), `2be26673...`, and binds the [independent source peer]({prefix}{peer_name}), `{peer_sha}`. The [first actual independent proof]({prefix}INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json), `173bfdeb...`, passes **15 methods**: all 48 unchanged histories in one method, the same eight previous regressions, and six genuinely pre-code indexed controls. Separate unchanged author suites pass 12 plus four methods. There are no test failures, errors, audit denials or source/test hash changes. No correction or rerun of V3 was needed.

The unchanged 48 histories retain **372 strict snapshots, 518 simulated original-file dispatches and 34 actual in-memory toy module executions**. Their 209-byte fictional input cohort is unchanged. The independent suite takes approximately 0.406 seconds; this is a pure algorithm/lifecycle result, not real-file, memory, native or integrated timing qualification.

Frozen sources are [owner]({prefix}shared_owner_v3.py), `d8ee1e13...` / 42,970 bytes, [file ports]({prefix}shared_file_ports_v3.py), `8ecabef9...` / 11,057 bytes, and [controller]({prefix}continue_verification_v3.py), `16ff0a34...` / 4258 bytes. Independent AST review records 20 changed existing methods, five added private helpers and 95 unchanged methods. The four controller method bodies and the 16 author-control bodies match their accepted predecessor ASTs. Runtime application sources and dispatch defaults are unchanged.

Canonical call records remain append-only. Per-file open/close references and read reservations use canonical ordinal/file indices. Defined read counts fold once into private totals; defined zero remains distinct from an unobserved count. Raw scalar/count cells are stored before auxiliary folding. An interruption in canonical append, indexing or folding latches the original error and blocks further work before clock, dispatch or state advancement. Reporting rebuilds a view from canonical facts; it cannot heal the fault, renew authority or resume work. Known owned handles retain cleanup rights.

Four instrumented normal-work windows have **zero global iteration, membership traversal or copied slices**. Handle and call-reference lookup each use one direct canonical index; the tested read admission uses six direct indices, eight length checks and one append. Eighteen explicitly separated reporting windows visit exactly r records once. Five healthy-clock quarantine checks refuse work with zero dispatch/output callbacks and unchanged facts/progress. Static peer review also checks for uninstrumented base-list/dictionary traversal, hidden rebuilds or alternate owners. These facts support the scoped complexity claim; they do not establish full-roster fit.

## Chronology and limitations

The [six-control pre-code freeze](review-assets/recovery-step9-production-preflight-20261029/INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json), `52da9451...`, predates all V3 source. Its accepted-V2 [before proof](review-assets/recovery-step9-production-preflight-20261029/INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json), `24da94c6...`, has four expected scan-cost failures, two functional passes and no errors. The first control version, its two-point harness HOLD and the corrected second version remain preserved. The V3 [source pause]({prefix}INDEXED-ACCOUNTING-SOURCE-PAUSE-v3.json), `8c010397...`, precedes any V3 import/test. The independent runner's later zero-test counters refer to its own execution boundary, not a claim that author tests had never run. The older eight-regression module remains retrospective to V2, as documented previously; it predates V3.

All current caps remain: N<=4, file<=4096 bytes, immutable capture<=16,384 bytes, R<=68, C<=92, E<=224 and buffer generation<=68. Public DATA, the 48-history oracle and snapshot types are unchanged. The algorithm uses a canonical in-memory call ledger and serializes complete views. It has not solved large-ledger retention, bounded report/output storage, physical journaling, source self-hosting or process memory.

All seven real qualification flags remain false. There was no actual Win32/ctypes/SDK/C++/CPU/GGUF/model/tokenizer activity, original-source closure pass, old-run replay, paid query or download in this component phase. Seven original-file operations and output acknowledgments are injected. The helper bodies really compile/execute only in memory through the closed toy resolver. This does not qualify fourteen real exports, physical durability, real checker provenance, first entry or a native protocol. Ordinary object immutability is not a hostile-Python security boundary.

## Complete recovery status

{table}

AsOf 0.3.11/default v2 retains **1,774 retained passing full tests**, **327 source/resource pins** and ten matching preserved-version qualifications. The full application suite was not rerun for this private-component change. Optional Arrow retains its prior baseline. Data/science still has **65 missing inputs**, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and **0/12** jointly source-ready clinical cases. Numerical prediction features remain empty, probabilities null and human reviews pending. Provider spending is $0. The download worker and stopped periodic monitor remain untouched.

The consumed 189-case native profile remains failed; its independent whole-verification remains **INCOMPLETE_TIMEOUT**. Neither result was repaired or repeated. Agents can prepare references, tests and engineering reviews; they cannot create independent human submissions or biological validation.

## Critical next step and dependency order

The [production preflight](review-assets/recovery-step9-production-preflight-20261029/PRODUCTION-ROSTER-SCALING-PREFLIGHT-v1.md), `3038edd7...`, and [independent feasibility check](review-assets/recovery-step9-production-preflight-20261029/SHARED-OWNER-FULL-ROSTER-FEASIBILITY-INDEPENDENT-v1.json), `97024275...`, remain material. Indexing removes the diagnosed repeated global-work scans; the earlier analytic lower bound of 9,466,123,215 quota-scan visits describes the superseded V2 algorithm, not V3. It does not remove the remaining input, storage and output barriers.

Only an old retained aggregate is available: 213 files / 9,017,363,392 bytes. The actual future approved role/size vector remains unknown. At 65,536-byte reads the aggregate requires at least 137,595 successful reads. Conditional on all 213 files being positive-sized, reservation bounds remain R=141,003-141,215 and C=142,281-142,493 under the unchanged strategy. These are analytic capacities, not observed dispatches or timings. Query frames alone would retain 1,750,434 bytes against a 131,072-byte raw pool. A 213-entry compact closure list needs at least 14,588 bytes before other fields, over the 8192-byte packet cap. The three current V3 sources total 58,285 bytes and each exceeds 4096 bytes; they exceed the tiny profile's capture budget and M<=2 module limit. No cap-only migration is justified.

1. **Implement the finite metadata admission envelope first.** Freeze exact descriptor roles and validation rules, read/call/event reservations, immutable-software capture versus hash-only streaming, query/call retention and bounded output representation. Consume explicit approved metadata; do not discover or open real originals. Require sizes and roles for a proposed roster; an aggregate cannot stand in for them. Expose missing inputs and units, refuse booleans masquerading as integers, duplicate/unsafe identities, inconsistent lineage and arithmetic/cap overflow. Calculate declared payload/storage bounds separately from measured Python RSS, transfer traffic and time. Retain synthetic pre-code controls and independent review. Keep the executable N4 profile unchanged. Acceptance of the calculator is an admission-design result, not full-roster or runtime authority. If the representation cannot fit a justified envelope, retain the refusal and amend the design before activation.
2. **Close actual first entry and typed binding.** Specify the trusted interpreter/runtime/entry kernel and startup exclusions. Sample the prebound monotonic clock before helper validation/import work; a whole-process startup bound requires an external qualified watchdog. The kernel must own the same Origin/class/nonce/registry and rights later operations use. Numeric time copies, module-cache fallback or class monkeypatches cannot establish that identity. Review inactive fourteen-export declarations and raw-first conversion/adoption before a separately scoped harmless owned-fixture qualification. Source/pure tests cannot establish real ABI layouts, metadata ancestry or the native-to-Python timing window.
3. **Bind actual source, checker, physical output and new format policies.** Use freshly captured software through a closed dependency map. Separate static manifest/entry trust to avoid self-reference cycles. Preserve once-only rights and cleanup, unknown write/read outcomes, bounded prepared/known bytes, flush/close acknowledgments, persisted hash-chain, receipt and final same-Origin seal. Qualify new Unicode parent/journal/archive/resource composition independently; old known-v7 policy and current fictional ACK-prefix digest cannot supply it. A late ACK never repairs an ineligible result.
4. **Qualify the distinct native and integrated resource gates.** Only a concrete source/header/build/parent/protocol decision may authorize the distinct fixed 84-document Unicode experiment. Preserve required coverage and negative outcomes; do not repeat the consumed 189-case experiment. Full-vocabulary masking and integrated startup/source/retrieval/generation/accounting/cleanup measurements remain separate. The earlier 295.922/300-second no-inference simulation leaves 4.078 seconds and establishes no integrated fit. Failed resource admission needs a retained negative disposition or explicit study amendment, not a hidden waiver.
5. **Integrate minimally, then resume science in dependency order.** Change the application only after relevant source/platform/resource gates, regression and installed/archive/relocation checks. Finish R08 and HR1-HR3 before R10. Size/freeze H5 before locked R12. Clinical ascertainment, regional genetics/compatible LD, training/calibration, competitors, T2-T5 and H6 retain their individual feasibility gates. Keep numerical clinical predictions withheld until their scientific prerequisites pass.

The next deliverable is the independently reviewed role-aware admission calculator and contract, with synthetic tests and explicit unknown/refusal outputs. This assessment itself authorizes no cap increase, real-input trial, software installation or native execution.
"""
    destination = ROOT / "planning" / NAME
    assert not destination.exists()
    staged = {destination: assessment}
    common = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md", "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md", "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"]
    for relative in common:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        base = "planning/" if relative in ("README.md", "TODO.md") else ""
        current = f"Current checkpoint: [indexed accounting](<{base}{NAME}>) is accepted for SOURCE/PURE scope under unchanged N<=4 caps (root `{short}`, peer `{peer_short}`). First V3 run passes all 48 unchanged histories, eight previous regressions and six pre-code indexed controls, plus separate 12+4 author methods. Four normal-work windows have no global call-history scans; 18 reports make one canonical pass. Raw-first facts, fault quarantine and cleanup rights remain intact. This is the same 209-byte fictional cohort; actual production/entry/FFI/source/physical output/native/resources and scientific/human gates remain open."
        text, count = re.subn(r"^Current checkpoint: .*?$", lambda _: current, text, count=1, flags=re.M)
        assert count == 1, relative
        next_step = f"Next is a role-aware metadata admission envelope and streaming/storage/output contract, using [production preflight]({base}review-assets/recovery-step9-production-preflight-20261029/PRODUCTION-ROSTER-SCALING-PREFLIGHT-v1.md) (`3038edd7`) and independent review `97024275`. Full-roster fit requires an explicit role/size vector and bounded retention/serialization; no cap lift or physical activation follows from indexing. AsOf 0.3.11/default v2, 1,774 retained full tests, 327 pins and ten preserved-version qualifications are unchanged; the application suite was not rerun for this component."
        text, count = re.subn(r"^Next is \[source/metadata production preflight\].*?$", lambda _: next_step, text, count=1, flags=re.M)
        assert count == 1, relative
        if relative == "README.md":
            text = replace_once(text, f"See the [current full-project reassessment](<planning/{old_name}>),", f"See the [current full-project reassessment](<planning/{NAME}>),")
        if relative == "TODO.md":
            old = next(line for line in text.splitlines() if line.startswith("- [ ] Implement and independently verify the indexed-only V3 successor:"))
            new = f"- [x] Implement and independently verify the indexed-only V3 successor: root `{short}`, peer `{peer_short}`, final freeze `2be26673`. First run passes frozen six controls plus unchanged 48 histories/eight regressions and separate 16 author controls; zero hot global scans, 18 one-pass reports, five quarantine checks. All runtime caps and broader qualifications stay unchanged."
            text = replace_once(text, old, new)
            text = replace_once(text, new, new + f"\n- [ ] Reassess all R01-R16/HR1-HR4 after indexed accounting; retain {NAME}, exact acceptance evidence and current-document QA.\n- [ ] Implement/review the finite role-aware metadata admission envelope and streaming/storage/output contract with pre-code synthetic controls; no real-input discovery, runtime cap lift or physical activation.")
        if relative == "planning/Project Progress Reassessments.md":
            text += f"\n| R09 indexed N4 accounting accepted | [29 October UTC indexed-accounting snapshot](<{NAME}>) | Root {short}/peer {peer_short}; first-run 48 histories+8 regressions+6 pre-code controls and separate 12+4 methods pass. No hot global scans; report/quarantine facts retained. Role-aware storage/output admission is next; actual entry/FFI/source/native/science/human gates remain open. |\n"
        staged[path] = text
    path = ROOT / "memory/MEMORY.md"
    text = path.read_text(encoding="utf-8")
    memory_line = f"- [[research-log-2026-10-29-r09-unicode-controls]] - Indexed accounting root{short}/peer{peer_short} accepted N4 SOURCE/PURE: first-run48+8+6 and separate12+4 methods pass; zero hot global scans,18 one-pass reports,5 quarantine checks. Freeze2be26673 and all before/HOLD chronology retained. Next role-aware admission/storage/output envelope; real entry/FFI/source/native/resource/science/human gates open, old failure/timeout unchanged."
    text, count = re.subn(r"^- \[\[research-log-2026-10-29-r09-unicode-controls\]\].*$", lambda _: memory_line, text, count=1, flags=re.M)
    assert count == 1
    staged[path] = text
    path = ROOT / "memory/project-goals.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("Current source-only checkpoint:")
    end = text.index("Raw-adoption5afb82f0", start)
    text = text[:start] + f"""Current source-only checkpoint: [indexed accounting](../planning/{NAME.replace(' ', '%20')}).
Root acceptance `{short}...` and peer `{peer_short}...` bind V3 owner d8ee1e13,
ports 8ecabef9, controller16ff0a34, source pause8c010397 and final freeze2be26673.
First actual V3 run passes15 independent methods (48 unchanged histories, same8
regressions, six genuinely pre-code indexed controls) plus separate12+4 author
methods. Strict snapshots372/fake calls518/actual in-memory toy executions34.
No source correction or rerun; zero failures/errors/audit denials. Four healthy
work windows have zero global traversal;18 reporting windows visit r calls once.
Raw-first defined counts (including zero), original faults, canonical ownership
and cleanup rights survive index/fold interruptions. Five healthy-clock work
checks refuse without dispatch/state advance. Full runtime limits remain N4,
file4096/capture16384/R68/C92/E224/generation68. This is a209B fictional cohort,
not a full-roster/platform qualification or measured process memory/time fit.

The six controls and V2 before24da94c6 predate V3. First harness HOLD and all
earlier failures remain; older consolidated8 regression chronology remains
retrospective to V2. Root source authority7683 and scoped acceptance do not
authorize physical/native activity. All seven real qualification flags are false.
Source/metadata preflights3038edd7/97024275 still leave the actual role/size vector
unknown. Query-frame storage1750434B, closure serialization>=14588B and current
software capture58285B exceed the tiny profile. Indexing resolves repeated work
scans, not these retention/output barriers. Next is a finite role-aware metadata
admission-envelope calculator and streaming/storage/output contract with frozen
synthetic controls. Runtime caps and application0.3.11/defaultv2 remain unchanged.
Actual first entry/kernel,14typed exports, real source/checkers/physical journal,
new Unicode/native/masking/integrated resources and science/human gates stay open.
The consumed failed profile/INCOMPLETE_TIMEOUT are not repaired or repeated.

""" + text[end:]
    staged[path] = text
    path = ROOT / "memory/research-log-2026-10-29-r09-unicode-controls.md"
    text = path.read_text(encoding="utf-8")
    text += f"""\n## Indexed-accounting source acceptance - 29 October UTC

Root `{args.acceptance_sha256}` and independent peer `{peer_sha}` accept the exact
N4 source/pure successor, frozen2be26673. Root verifies31 pins. First coherent
source pause8c010397 precedes all V3 imports/tests; the first run passes15 methods
(unchanged48/same8/precode6), separate12+4 controls,372 snapshots,518 fake calls
and34 actual captured-toy executions. No rerun/correction. Four hot windows have
zero global scans;18 reports visit r records once;5 quarantine checks preserve
raw facts/original errors and refuse otherwise valid work before dispatch.

Source d8ee1e13/8ecabef9/16ff0a34 changes20 existing methods/adds5/retains95;
controller4 and author16 assertion ASTs are unchanged. New six controls genuinely
predate V3; old consolidated8 tests are retrospective to V2. All old failures,
first harness HOLD and before proofs remain. This does not establish actual
first entry, physical/platform/source closure, full roster, native/resources or
science. Application/defaults/provider$0/download worker/monitor unchanged.

The [full-project status reconciliation](../planning/{NAME.replace(' ', '%20')})
covers all20 recovery/human rows and five next gates. The immediate next finite
deliverable is an explicit role-aware metadata admission envelope and bounded
stream/capture/query/call/output contract. The runtime N4 profile stays fixed.
Unknown actual roster and remaining data/human prerequisites remain explicit.
"""
    staged[path] = text
    for path, text in staged.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"updated_documents": len(staged), "assessment": str(destination), "acceptance": short, "peer": peer_short}))


if __name__ == "__main__":
    main()
