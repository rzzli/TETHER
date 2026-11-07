# TETHER verification capabilities

The current interface is `tether-target-agents` **0.6.0**, backed by
`tether-target-engine` **0.4.0** (`tether_engine`). Public `tether` module aliases
share that new engine's identities. See the [namespace migration
boundary](../packages/tether/MIGRATION.md) and [quick start](../README.md#quick-start).
A passing consistency check does not establish biological truth, source
authenticity or clinical validity. The [dated corrective plan](<../planning/TETHER Corrective Execution Plan 2026-11-02.md>)
and [critical review](<../planning/TETHER Full Project Critical Review 2026-11-02.md>)
retain the counterexamples that motivated these distinctions.

The semantic experiment is **paused**. This page describes interface contracts
and explicitly dated historical qualifications; it does not claim a new-release
qualification result. Earlier proof identities, release metadata, exact commands
and original package names remain in the [historical checkpoint](ARCHIVE.md).

The November 2, 2026 [completion record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-ce-fixes-20261102/COMPLETION.md)
qualified facade 0.5.1 and engine 0.3.12 for all-supplied-raw receipt-time
consistency, retained failed-call usage and bounded Windows replacement. It
reported **2,020 full-suite tests, 138 facade tests and 742 aggregate checks** on
Windows. These are historical counts, not measurements of 0.6.0/0.4.0. The
[associated execution plan](<../planning/TETHER Benchmark Execution Plan 2026-11-02.md>)
remains a dated plan, not authorization to resume the paused experiment. Older
0.5.0/0.3.11 artifacts and same-version development candidates require their
matching original wheels and code hashes.

## Interface contracts and version boundaries

| Interface | Checked property | Required evidence | Remaining limit |
| --- | --- | --- | --- |
| Current engine v1 receipt verification | Listed output hashes and available source hashes | Original receipt and an independently retained receipt hash for replacement detection | Legacy semantic verification is unavailable; a v1 receipt does not acquire v2 guarantees. |
| Current engine v2 API, including `tether.artifacts` and `tether.semantics` aliases | Engine output, lineage, deterministic feature, scorer, accounting, trace and consumed-replay checks | Matching new-engine inputs, receipts and code proofs; current originals for source-inclusive mode | Direct aliases share the new engine API, not historical code identity. Canonical CLI coverage-state, review-selection and dossier-text checks remain additional checks. |
| Current canonical `tether verify` on a v2 engine directory | Engine checks plus category-state reconstruction, reviewed-selection/commit consistency, bounded-request membership, known terminal dispositions and deterministic dossier rendering | Matching engine run and input/archive proofs; original receipt anchor recommended | Serialized custom exception names do not prove Python class inheritance. The checker reconstructs declared inputs, not undeclared real-world ancestry. Historical runs require their original code. |
| Canonical engine verification with `--outputs-only` | Consistency against archived fingerprints and records | Complete archived run | Does not reread the current originals. `source_binding: archived_fingerprints_only` must not be described as fresh source verification. |
| Current canonical verification of a TETHER outer run | Source-inclusive engine checks plus exact dossier byte copy (`identity_dossier_v2`), complete file inventory, outer journal/manifest, launcher source/version and receipt bindings | Matching launcher code/version and originals; independently retained outer receipt hash | A different launcher version cannot silently verify an earlier launcher proof. `--outputs-only` is rejected. Earlier header projections belong to their archived releases. |
| Current explicit schema-2 policy `run`/verification | Exact artifact/use/parent admission, copied control/provenance bindings, original catalog anchor and deterministic projection rederivation against actual engine inputs | Newly verified artifact grants, policy, exact use/frame, root map, case/snapshot and current raw originals/receipts | The current policy is inventory-only: zero artifacts and zero uses. Run-only offline extractive scope; no model/scorer or synthetic-demo policy bypass. Projection alone is not authorization. |
| `inspect-run` | Readable retained attempt, terminal status and declared accounting, including unresolved calls | Existing output directory and bounded journal snapshot | Inspection neither completes an interrupted execution nor retries a call; it is not successful-run verification. |

The `semantic_consistency` field alone is not a complete description. Preserve the command, version, `source_binding`, stronger TETHER check details and external-anchor status with the result. Without an external anchor, replacing the complete self-consistent output tree cannot be detected solely by its internal hashes.

### Historical replay qualification: November 5, 2026; 0.5.2 / 0.3.13

The first independent-policy comparison exposed a v2 gap in the earlier release: a
retained replay response could name the wrong request fingerprint while its other
archive relationships remained consistent. The correction implemented in that version checks
consumed replay entries against source-reconstructed requests, response order,
selected IDs, usage and review feedback, before publication and during live v2
verification. That correction also applied to its direct engine aliases. The
historical archive verifier and original installed releases keep their stated
policies; they do not acquire this guarantee.

The corrected replay contract is retained in the new source; its historical tests
do not qualify the namespace migration. Successful recorded-run verification
includes `replay_binding`. With current
originals, its `request_binding` is `source_reconstructed`; with `--outputs-only`
it is only `archived_dispatch_fingerprints`. The latter cannot establish that a
retained dispatch describes unavailable original evidence. Verification neither
opens the original replay-file path nor invokes its backend. The original raw-file
hash remains an opaque declaration because canonical JSON cannot reconstruct its
original whitespace. Unused response entries do not become consumed evidence.

At that checkpoint, focused replay, archive, facade and isolated installed checks
passed, including the retained counterexample and a valid replay after removal
of its original input file. The historical full Windows gate passed 2,100 tests
with zero failures/errors/skips, required probes and offline packaging; the
checked source hashes were unchanged during that gate. The
[local completion record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-replay-correction-20261105/CANDIDATE-RELEASE-COMPLETION.md)
keeps test scopes and installed/full-gate wheel identities distinct. Corrected
comparison scoring and independent reconstruction passed the declared finite
[BG02 gate](<../planning/TETHER Equal Policy Comparison Results 2026-11-05.md>):
both the then-current TETHER and the independent implementation conformed on 109 authored
cases. This does not establish scientific answering performance or universal
policy equivalence; no public release is implied. Matching older wheels remain
necessary for old outer-artifact code proofs.

The [artifact-policy guide](TETHER-CATALOG-POLICY.md) describes the current interface, its inventory-only policy and separate `artifact_policy.status` result. The artifact-policy path was introduced in facade 0.5.0; original grants are not inherited by the new namespace. It requires current original raw files/receipts even though exact metadata, controls and receipt copies are archived. Strong policy grants do not qualify scientific interpretation or guarantee that all records pass publication/temporal admission. Legacy schema-1 APIs and runs keep their declared scope.

## Execution limits and trust boundary

The current launcher retains the controls introduced in facade 0.4.2: 64 MiB individual metadata and 256 MiB dossier read/product limits, with a default **3,600-second absolute child deadline** and **16 MiB combined stdout/stderr cap**. Set `--process-timeout-seconds` and `--process-output-bytes` after a delegated subcommand; the latter allows 1 through 67,108,864 bytes. The deadline includes pipe EOF, with a separate five-second cleanup wait budget. Retained output is bounded in bytes; this is not a bound on whole-process peak memory or source-artifact size. These conservative defaults are an execution policy, not evidence that a particular source build will fit.

`demo` and `run` seal the effective limits and supervision report, including observed/retained bytes, timing, EOF, reaping and cleanup errors. Their raw accepted argument hash remains separate from the effective-limit record. Failed outer attempts retain capped stream files, a failure record and available engine accounting. `inspect-run` never redispatches. Failed delegated commands without an outer directory emit supervision diagnostics to stderr; they do not implicitly create an output tree or partial-byte artifact. Existing engine output paths remain available when the command created them.

The supervisor owns one child. It cannot preempt a blocked operating-system process creation, kill a descendant process tree or bound outer source verification/publication after the child returns. In-process `verify` rejects the child-limit flags; outer `inspect-run` rejects explicit flags too. Operating-system signal, wait and pipe-close calls remain trusted host operations. The historical qualified checks were local Windows checks; neither POSIX behavior nor the new release inherits qualification from those checks. The old 0.4.1 launcher still has its original unbounded main `communicate()` and does not inherit this change.

The historical Windows qualification exercised the CLI polling loop with one reader per pipe. Microsoft documents an immediate return for `PeekNamedPipe` in a single-threaded application, with a blocking caveat for synchronous handles in multithreaded applications. Arbitrary embedded multithreaded use remains outside that historical qualification. Python also documents that initial process creation may not be interruptible. [Microsoft pipe API](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe), [Python subprocess limits](https://docs.python.org/3.11/library/subprocess.html#subprocess.Popen.communicate).

Workflow token/cost/time budgets, individual filesystem read limits and a child-process envelope are different limits. An elapsed-time bound does not estimate scientific feasibility or guarantee that a large source build will fit. Neither the facade nor the engine is an operating-system sandbox. Host compromise, malicious native code, forced termination, filesystem unavailability and unreported remote billing are outside these consistency guarantees.

The historically qualified 0.5.1/0.3.12 build added bounded retry to mutable JSON file
replacement on Windows: native access/sharing/lock errors permit three attempts
on the same staged bytes, with 50/100 ms requested waits. Permanent failures and
interruptions still propagate; cleanup errors cannot replace the primary error.
This neither retries model calls nor changes the no-clobber publisher. It does
not guarantee write availability, wall-clock completion, or version ordering
under contention. The [retained peer probes](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-ce-fixes-20261102/integration/windows-replace-peer/REVIEW.md)
include explicit failed writes and last-completing-writer-wins behavior. The
historical full Windows gate passed; earlier same-version candidate wheels have different
code hashes and must be treated separately.

## Verifying historical artifacts

Keep the original outer receipt hash outside the artifact tree. Use the
[archived checkout](ARCHIVE.md) to identify the exact original facade and engine
wheel names, versions and hashes for that run; the new distribution name is not
an alias for those older wheels. Install the original local files in a separate
environment without dependency resolution or network access, then follow the
original verification command retained there. Do not use the new 0.6.0/0.4.0
packages to reinterpret old v2 execution proofs. Match source fingerprints as
well as displayed versions: two revisions with the same version number are not
interchangeable proofs.

The original 0.4.0 launcher and artifact record remain in [the TETHER release record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/paper/release/tether/RELEASE-RECORD.json). The separately qualified 0.4.1 wheel is recorded in [its installed qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/full-project-review-20261102/platform/WHEEL-QUALIFICATION-FINAL-v3.json). Its local wheel SHA-256 is `b392440919fddb8cab17b1741ee716bfa95d4cc1172878725b2603b115b322d5`. These are local Windows qualifications. Hosted jobs, Linux execution and exact-byte provider reacquisition are not implied.

No receipt, source-linked quotation, passing regression or deterministic replay establishes therapeutic efficacy, valid causal inference, independent expert agreement or general model superiority. Numerical real-data prediction features remain empty and probabilities null until their derivations are qualified.
