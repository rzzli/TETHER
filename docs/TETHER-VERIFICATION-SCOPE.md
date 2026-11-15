# Verification scope

TETHER reports byte integrity, semantic consistency, source binding and scientific
validation separately. A verified execution is not a validated scientific conclusion.
The current interface is `tether-target-agents` 0.7.0 over
`tether-target-engine` 0.5.0.

**Current scope (13 November 2026):** new execution requires the registered
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
| Canonical CLI verification | Coverage states, reviewed selections, request membership, terminal dispositions and dossier rendering agree | A stronger guarantee for callers that use only a lower-level API |
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
| Silent reduction in verification strength | Receipt policy and returned semantic/derivation fields | Legacy byte-only results currently return integrity success. A producer version string is not an authentication mechanism; explicit minimum-level enforcement is pending. |
| Later or evaluator-only information | `chrono.admit_snapshot`, lineage validation and catalog role checks | Declared dates and complete lineage must be truthful. Artifact-envelope clocks remain inconsistent with source-node gating; current checks do not prove earliest public availability. |
| Hostile source text or model output | Typed selection parsing, source membership, ledger fingerprint and request binding | These controls constrain accepted records, not arbitrary model reasoning. Generated-text entailment and semantic prompt-injection robustness are not qualified. |
| Exhausted budget, timeout or interruption | Workflow budget, attempt journal, wrapper supervision | Durable attempts reveal uncertain work; they cannot prove unreported billing or guarantee a terminal event after hard kill/storage failure. Post-seal error handling still needs repair. |
| Malicious filesystem replacement | Bounded wrapper reads and file identity/path checks | The verifier trusts the operating system and approved original sources. Native read limits/source-root handling and supported-platform behavior need further qualification. |
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
| Engine `study/` | Migration candidate; some primitives are live CLI dependencies | Extract and test dependency closure before moving drivers out of the wheel. |
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
version-one receipts retain read-only byte checks with semantic/derivation checking
explicitly unavailable. Declared source bytes may be verified, but this does not
replay the completeness of their inventory. Exact older semantic replay requires
the original software checkpoint. Native current-policy runs retain their source
path bindings. The versioned bundle format provides a separate relocation path
for supported offline runs with its own manifest and verification tiers.
[Upgrade guidance](../packages/tether/MIGRATION.md) · [Historical compatibility](ARCHIVE.md) · [Portable verification](PORTABLE-BUNDLE.md)

## Process and filesystem limits

Engine-backed CLI commands default to a 3,600-second child-process deadline and
16 MiB combined stdout/stderr limit. The engine workflow's 300-second budget is a
separate bound. The supervisor retains capped output, exit/reaping information and
cleanup errors. An uncertain call is never automatically repeated.

The supervisor owns one child. It does not contain arbitrary descendant processes,
preempt operating-system process creation or bound later outer verification.
Windows-specific handle and path controls require Windows tests; portable checks
do not imply identical platform guarantees.

Metadata and journal reads are capped at 64 MiB; dossiers at 256 MiB. Bounded file
reads reject links, reparse points and nonregular files and check file identity.
These controls do not guarantee exclusive ownership of external files or survive
all host compromise, forced termination, filesystem failure or unreported billing.

Preserve command/version, `source_binding`, receipt-anchor status and the relevant
verification fields when reporting a result. A single `semantic_consistency` flag
is not a complete description of the checks performed.
