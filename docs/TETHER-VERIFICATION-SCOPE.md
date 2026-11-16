# Verification scope

TETHER reports byte integrity, semantic consistency, source binding and scientific
validation separately. A verified execution is not a validated scientific conclusion.
The current interface is `tether-target-agents` 0.8.0.dev1 over
`tether-target-engine` 0.6.0.dev1.

**Current scope (15 November 2026):** new execution requires the registered
computed-evidence policy described in [the architecture](FRAMEWORK.md#registered-computation).
Source-inclusive replay rederives supported complete outputs; unknown computations
are rejected. This does not validate arbitrary scientific methods. Fixed-horizon
evaluation uses outcome-independent calendar maturity and full-cohort accounting.
Production evaluation binds run receipts or an explicit external producer
declaration; unverified diagnostics have a separate raw interface. These repairs
do not qualify the clinical endpoint, historical data, model chronology or scorer.
See [results and current scope](RESULTS.md).

| Check | What it establishes | What it cannot establish |
|---|---|---|
| Receipt and inventory | Listed files match their recorded hashes | Authenticity of an untrusted receipt or replacement of the entire tree without an external anchor |
| Source-inclusive verification | Current originals, receipts, declared lineage and accepted claims agree | Publisher authenticity or undeclared real-world ancestry |
| Semantic replay | Declared requests, selections, registered derivations, deterministic features, scorer contributions, accounting and traces agree | Correct biological interpretation, trusted historical metadata or predictive usefulness |
| Shared engine/CLI/bundle verification | Coverage states, reviewed selections, request membership, terminal dispositions and dossier rendering agree | Scientific validity or independent implementation of those shared checks |
| Outer-run verification | Exact engine dossier copy, complete inventory, launcher identity, journal and receipts agree | Compatibility with a different launcher or engine version |
| Artifact-policy verification | Exact registered artifacts, parents, use, frame and controls agree | Scientific validity or automatic eligibility of every row in an allowed artifact |
| `inspect-run` | Retained attempts, terminal state and declared accounting can be read | Completion of an interrupted run or permission to retry it |
| Bound evaluation | Cohort, policy, labels, exact prediction bytes and stated producer checks agree; incomplete mature populations withhold primary metrics | Independent producer authentication, pre-label registration, valid clinical labels or a causal missingness/censoring model |

## Threat model and supported boundary

Scope baseline: 15 November 2026. The following is the contract for interpreting
results, including known gaps awaiting correction. It does not upgrade old runs.

| Threat or error | Checker and evidence | Assumption and remaining limit |
|---|---|---|
| Accidental file changes or post-run editing | Receipt inventories and hash-chained journals in `artifacts.verify_run`; outer inventories in `tether._presentation.verify_outer` | Hashes must be compared with a separately retained trusted root to detect replacement of the entire tree. |
| Internally contradictory run state | `semantics.check_execution`, shared `execution_states.check_states`, `check_semantics` and `dossier_verification.check_dossier` | Native verification, portable replay and bound evaluation share review/coverage and dossier reconstruction. Consistent rendering does not prove the source statements true. |
| Silent reduction in verification strength | Receipt policy and explicit weaker-assurance opt-in | Default verification requires current semantics; legacy byte-only and outputs-only results identify their narrower scope. A producer version string is not authentication. |
| Later or evaluator-only information | Shared artifact/source information gates, UTC/calendar bounds, publication precision, lineage and catalog roles | Declared dates and complete lineage must be truthful. Checks do not prove earliest public availability; unresolved publication timing stays distinct from known future information. |
| Hostile source text or model output | Typed selection parsing, source membership, ledger fingerprint and request binding | These controls constrain accepted records, not arbitrary model reasoning. Generated-text entailment and semantic prompt-injection robustness are not qualified. |
| Exhausted budget, timeout or interruption | Workflow budget, attempt journal, wrapper supervision and immutable engine receipt boundary | Durable attempts reveal uncertain work; they cannot prove unreported billing or guarantee a terminal event after hard kill/storage failure. Supporting study-driver terminal paths still need qualification. |
| Receipt-controlled source paths and filesystem replacement | Caller-selected source roots, complete required-source preflight, no-follow handles, file identity and hash checks | Receipts cannot grant roots. Caller-selected local ancestor links are resolved; descendant links are rejected. The verifier trusts the OS and does not hold a transaction over all sources across all evaluated runs. Full platform support still requires its declared matrix. |
| Invalid scientific inference | Source replay plus separately scoped benchmark/outcome evaluation | Integrity, signatures, timestamps and checker agreement do not establish causal biology, clinical success or model usefulness. |

Execution completeness, byte integrity, semantic consistency, source binding,
external author/key authenticity, externally witnessed time and scientific
validity are separate properties. Verified bytes of a failed attempt do not make
the execution successful. A nested engine receipt bound by an outer receipt is
not a second independently trusted anchor. Signing and external timestamping are
not current runtime guarantees.

The maintained interface is the installed CLI and engine evidence/execution APIs,
plus the portable bundle workflow and descriptive `temporal_audit` reproduction.
Their known gaps above constrain support. Python 3.11 is the established reference
runtime; the advertised broader range still needs additional matrix qualification.
Windows-specific file controls do not establish identical POSIX guarantees.

| Component | Preservation/support designation | Change rule |
|---|---|---|
| Engine top-level modules, demos, schemas; public `tether` package | Maintained, with the disclosed verification gaps | Test contract changes across engine, wrapper, bundle and evaluation. |
| Engine `study/` | Migration candidate; shared proof/read primitives have moved to the maintained core with old import aliases preserved | Historical drivers are excluded from slim wheels; retain their matching original environments. Only proof/read import aliases remain installed. |
| Engine `archive/` | Historical compatibility with live entry points | Preserve original-runtime checks; decide API migration before removal. |
| `experiments/temporal_audit/` | Maintained descriptive reproduction | Preserve the source-to-table contract and public replay. |
| Other experiment modules | Historical research; potential shared-code migration candidates | No current-engine or turnkey-reproduction promise; preserve exact protocols/results and extract consumers before archival. |
| Validation/history/portable utilities | Maintained infrastructure | Keep current and original-runtime gates separately accounted for. |
| Remaining acquisition, science and feasibility utilities | Migration candidates requiring per-tool qualification | Inventory imports and tests before retaining in the supported surface. Original download worker remains unchanged. |
| Tests and fixtures | Maintained checks or explicitly original-runtime checks | No private data publication to make a ZIP test pass; verify fixture rights and exact bytes. |

Preserve the reviewed commit and original artifacts before any subtraction.
An implementation fingerprint identifies what ran; a compatibility policy decides
what a later verifier can check. Neither cosmetic refactoring nor a version-label
change authorizes rewriting frozen receipts. Broad code deletion, new datasets,
provider spending and external release are not consequences of this threat model.

## Independently retained anchors

Save the printed receipt hash independently and provide it to `tether verify`
with `--receipt-sha256`. Without an independent anchor, an internally consistent
replacement of the entire output tree can evade hash checks against that same tree.

Caller anchors accept exactly 64 hexadecimal characters in either case; empty,
malformed and non-string values fail. `anchor_scope` distinguishes a caller's
receipt/manifest digest from an inner `parent_receipt` binding. The latter reports
`receipt_anchor_checked: true` and `external_anchor_checked: false`: the inner hash
was checked, but its trust comes from the parent. A bundle export's
`export_self_check` is similarly not an independently supplied manifest anchor;
`producer_receipt_anchor_checked` separately reports its optional input anchor.

The direct engine's `--outputs-only` mode uses archived fingerprints instead of
rereading current originals. Its result must not be described as fresh source
verification. Computed content reports `derivation_verification: not_checked_outputs_only`
and does not receive a full semantic-verification claim. The public wrapper rejects
that mode for outer runs.

Replay verification checks consumed responses against source-reconstructed
requests, response order, selected IDs, usage and feedback. Unused entries do not
become consumed evidence. A raw replay-file digest does not reconstruct that file's
original whitespace or prove that undeclared inputs were absent.

Evaluation's source checks occur within each source-inclusive run verification.
Final rereads cover captured evaluation inputs and run artifacts; they do not
lock or atomically verify all external sources across the cohort. External
baseline references are declarations, not automatically verified files.
See [evaluation contracts and missingness](FRAMEWORK.md#fixed-horizon-evaluation).

## Version compatibility

Current `tether` module aliases share the new engine's classes and modules; direct
aliases do not acquire the wrapper's additional checks or artifact authorization.
Current version-two execution seals policy `tether.derivation.v1` consistently in
configuration, run and receipt. Known engine 0.4.0 version-two receipts and generic
version-one receipts require `--allow-legacy` (Python `allow_legacy=True`) for
read-only byte checks with semantic/derivation checking
explicitly unavailable. Declared source bytes may be verified, but this does not
replay the completeness of their inventory. Exact older semantic replay requires
the original software checkpoint. Native current-policy runs retain their source
path bindings. The versioned bundle format provides a separate relocation path
for supported offline runs with its own manifest and verification tiers.
Default verification rejects a receipt-selected downgrade. Explicit legacy results
use `status: byte_integrity_verified` and `assurance: byte_integrity`; current
source-inclusive results report `assurance: source_inclusive_semantics`.
An explicit native `--outputs-only` request reports `assurance: output_consistency`.
The public CLI applies its current-code check to bare native directories as well
as outer presentations. Portable replay instead checks supported format semantics,
not equality to the current producer code.
[Upgrade guidance](../packages/tether/MIGRATION.md) · [Historical compatibility](ARCHIVE.md) · [Portable verification](PORTABLE-BUNDLE.md)

## Process and filesystem limits

Engine-backed CLI commands default to a 3,600-second child-process deadline and
16 MiB combined stdout/stderr limit. The engine workflow's 300-second budget is a
separate bound. The supervisor retains capped output, exit/reaping information and
cleanup errors. An uncertain call is never automatically repeated.

On Windows, native CLI, tokenizer and owned-server launches use one shared core
Job Object primitive. The initial process is suspended until assigned to a
non-breakaway, kill-on-close job; shutdown covers its inherited descendants,
including after abrupt owner exit. Assignment/resume failures retain the owned
process identity and do not trigger another launch. A normal root exit does not
leave its descendants running. Trusted injected process factories and non-Windows
execution retain single-child scope. The unchanged receipt fields do not assert
that older runs had process-tree containment; retain the implementation identity.

This is lifecycle containment for cooperating local execution, not a hostile-code
sandbox. It cannot preempt OS process creation, cover processes created through
external brokers, or bound later outer verification. Microsoft documents ordinary
child-job inheritance and its exceptions in [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
Native Windows tests exercise real finite Python descendants, abrupt parent exit,
startup faults and unrelated-process survival; no model is used. Other platform
support requires its own qualification. Cleanup failures remain execution errors;
lost storage or a killed owner cannot be guaranteed a final journal event.

Study input readers use the Windows creation clock for path/descriptor identity
and independently compare the descriptor change clock before and after reading.
This avoids comparing different clock meanings on Python 3.14 while retaining
replacement and in-read change checks. The focused reader suite passed on Windows
Python 3.11 and 3.14; the installed public wrapper passed 146 tests on each. These
results do not qualify other operating systems or arbitrary filesystem races.

Owned-server startup has one absolute deadline covering pinned executable/weight
verification, spawn and readiness, limited further by any parent deadline. Proof
verification rejects oversized files before opening and checks the deadline around
each bounded read. It cannot preempt a blocked filesystem syscall. Cleanup has its
separately bounded wait policy; timeout never authorizes an automatic second launch.

The typed-report HTTP client uses a direct loopback connection and an absolute
socket watchdog across headers and body. It ignores proxy settings and never
follows redirects. One deadline also includes ownership/attempt preparation;
expiry there prevents dispatch. Slow-header/body fixture tests passed on Windows
Python 3.11 and 3.14. Injected openers and callbacks remain trusted integrations:
elapsed-time checks reject late returns but cannot preempt arbitrary callback code.
No real model endpoint was used in these checks.

Tokenizer preparation and replay use the earlier of the caller's absolute deadline
and their existing 300-second local cap. A larger parent budget is capped locally,
not rejected; a shorter budget is never extended. Child execution retains its
separate 30-second cap within that deadline. This does not change source/retrieval
preparation's separate contracts or qualify native model token counts scientifically.

Study-cell, source/retrieval preparation, tokenizer and recorded-comparison drivers
keep their journals open through seal staging. A staging/hash/sync failure can
therefore append a terminal failure; a successfully published receipt prevents
further journal or failure-marker mutation. The final deadline gate runs after
staging is synced, immediately before the atomic publication call. This cannot
preempt that OS call or certify the wall time of later presentation/cleanup.
An exception after publication leaves the seal available for explicit verification;
it does not authorize withdrawal, rewriting or automatic redispatch.
Source/retrieval and tokenizer preparation also retain the primary execution
exception when journal closing fails, recording the secondary error as a note.
A close failure without an earlier execution failure still propagates.
Parent comparisons and native transport/launch retention use their own execution
failure state. They do not attach a new cleanup error to an unrelated exception
being handled by their caller. Source-lease cleanup cannot skip parent journal
closure, and native preparation tries both failure-retention paths even when one
fails. Secondary errors remain attached to the original failure; successful
execution followed by failed cleanup is reported as an error with any existing
seal preserved.

Wrapper metadata and journal reads are capped at 64 MiB; dossiers at 256 MiB. Bounded file
reads reject links, reparse points and nonregular files and check file identity.
These controls do not guarantee exclusive ownership of external files or survive
all host compromise, forced termination, filesystem failure or unreported billing.

Native run verification now caps receipt/metadata/journal/trace outputs at 64 MiB
and ledger/dossier outputs at 256 MiB. Hashing also stops at the applicable output
limit if a file grows; trace parsing checks the hash of the bytes it consumes.
Journal appends cannot exceed 64 MiB or rewrite the last durable prefix when the
cap is reached. A full journal may have no room for a failure event: a missing
receipt and the retained last event must be treated as incomplete execution.
These byte limits do not establish filesystem containment or a hard peak-memory
bound for decoded Python objects. Original source-file hashing has its separate
source policy and is not restricted to the normalized-output size cap.

The explicitly invoked legacy native diagnostic reports `execution_status`,
`all_scheduled_cells_terminal` and `successful_cells` separately from verification
of its terminal record. Its execute command returns 3 for failed/incomplete
execution and 130 for interruption. Verification of a valid failure record can
still return success as a verification operation; its execution status remains
failed. The original frozen report's human-review field is historical metadata,
not a new expert-recruitment prerequisite or scientific acceptance.
Its outer terminal-seal writer keeps the execution journal open until publication;
storage failures append a failure event, while post-publication errors preserve
the seal and journal. The native diagnostic fixture suite verifies this separately
from the ordinary study-driver receipt boundary.

Preserve command/version, `source_binding`, receipt-anchor status and the relevant
verification fields when reporting a result. A single `semantic_consistency` flag
is not a complete description of the checks performed.
