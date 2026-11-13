# Verification scope

TETHER reports byte integrity, semantic consistency, source binding and scientific
validation separately. A verified execution is not a validated scientific conclusion.
The current interface is `tether-target-agents` 0.7.0 over
`tether-target-engine` 0.5.0.

**Current scope (12 November 2026):** new execution requires the registered
computed-evidence policy described in [the architecture](FRAMEWORK.md#registered-computation).
Source-inclusive replay rederives supported complete outputs; unknown computations
are rejected. This does not validate arbitrary scientific methods. The descriptive
clinical evaluator can still retain early positives while
excluding immature follow-up and accepts predictions without run receipts. These
paths must not support historical clinical-performance claims until corrected.
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

## Source and receipt anchors

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

## Version compatibility

Current `tether` module aliases share the new engine's classes and modules; direct
aliases do not acquire the wrapper's additional checks or artifact authorization.
Current version-two execution seals policy `tether.derivation.v1` consistently in
configuration, run and receipt. Known engine 0.4.0 version-two receipts and generic
version-one receipts retain read-only byte checks with semantic/derivation checking
explicitly unavailable. Declared source bytes may be verified, but this does not
replay the completeness of their inventory. Exact older semantic replay requires
the original software checkpoint. New-policy relocated semantic replay is not
yet implemented; it is rejected explicitly rather than inferred from old pins.
See [upgrade guidance](../packages/tether/MIGRATION.md) and
[historical compatibility](ARCHIVE.md).

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
