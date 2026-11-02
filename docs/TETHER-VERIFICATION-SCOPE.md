# TETHER verification capabilities

This table distinguishes the interface, version, input anchor and property being checked. A passing check establishes the stated consistency property; it does not establish biological truth, source authenticity or clinical validity. The [current corrective plan](<../planning/TETHER Corrective Execution Plan 2026-11-02.md>) and [critical review](<../planning/TETHER Full Project Critical Review 2026-11-02.md>) retain the counterexamples that motivated these distinctions.

The [execution plan](<../planning/TETHER Benchmark Execution Plan 2026-11-02.md>) is active. TETHER 0.5.1/AsOf 0.3.12 are [locally qualified](../planning/review-assets/tether-ce-fixes-20261102/COMPLETION.md) for all-supplied-raw receipt-time consistency, retained failed-call usage and bounded Windows replacement; the supporting transport verifier prevents report/input aliasing and publishes without replacement. Full2020/facade138 tests and742 aggregate checks pass on Windows. Historical rows keep their stated scopes. Preserve matching 0.5.0/0.3.11 wheels for older outer runs; same-version development candidates also require matching code hashes.

## Qualified interfaces

| Interface | Checked property | Required evidence | Remaining limit |
| --- | --- | --- | --- |
| Frozen engine v1 receipt verification | Listed output hashes and available source hashes | Original receipt and an independently retained receipt hash for replacement detection | Legacy semantic verification is unavailable; a v1 receipt does not acquire v2 guarantees. |
| Frozen engine v2 API, including `tether.artifacts` and `tether.semantics` aliases | The original engine's output, lineage, deterministic feature, scorer, accounting and trace checks | Archived inputs, receipts and proofs; current originals for source-inclusive mode | The review reproduced missing coverage-state, review-selection and dossier-text relationships. These aliases preserve compatibility rather than adding the new CLI checks. |
| Canonical `tether verify` on a v2 engine directory, from 0.4.1 | Original checks plus category-state reconstruction, reviewed-selection/commit consistency, bounded-request membership, known terminal dispositions and deterministic dossier rendering | The engine run and its input/archive proofs; original receipt anchor recommended | Serialized custom exception names do not prove Python class inheritance. The checker reconstructs declared inputs, not undeclared real-world ancestry. |
| Canonical engine verification with `--outputs-only` | Consistency against archived fingerprints and records | Complete archived run | Does not reread the current originals. `source_binding: archived_fingerprints_only` must not be described as fresh source verification. |
| Canonical verification of a TETHER outer run | Source-inclusive engine checks plus exact first-header projection, complete file inventory, outer journal/manifest, launcher source/version and receipt bindings | Matching launcher code/version and originals; independently retained outer receipt hash | A different launcher version cannot silently verify the old launcher's proof. `--outputs-only` is rejected. |
| Explicit schema-2 policy `run`/verification, from 0.5.0 | Exact artifact/use/parent admission, copied control/provenance bindings, original catalog anchor and deterministic projection rederivation against actual engine inputs | Policy, original catalog, exact use/frame, root map, case/snapshot and current raw originals/receipts | Run-only offline extractive scope; no model/scorer or synthetic-demo policy bypass. Projection alone is not authorization. Compatibility runs report the policy was not requested. |
| `inspect-run` | Readable retained attempt, terminal status and declared accounting, including unresolved calls | Existing output directory and bounded journal snapshot | Inspection neither completes an interrupted execution nor retries a call; it is not successful-run verification. |

The `semantic_consistency` field alone is not a complete description. Preserve the command, version, `source_binding`, stronger TETHER check details and external-anchor status with the result. Without an external anchor, replacing the complete self-consistent output tree cannot be detected solely by its internal hashes.

The [artifact-policy guide](TETHER-CATALOG-POLICY.md) specifies the 0.5.0 interface and its separate `artifact_policy.status` result. It requires current original raw files/receipts even though exact metadata, controls and receipt copies are archived. Strong policy grants do not qualify scientific interpretation or guarantee that all records pass publication/temporal admission. Legacy schema-1 APIs and runs keep their declared scope.

## Execution limits and trust boundary

The 0.4.2 launcher retains the 64 MiB individual metadata and 256 MiB dossier read/product limits. It adds a default **3,600-second absolute child deadline** and **16 MiB combined stdout/stderr cap**. Set `--process-timeout-seconds` and `--process-output-bytes` after a delegated subcommand; the latter allows 1 through 67,108,864 bytes. The deadline includes pipe EOF, with a separate five-second cleanup wait budget. Retained output is bounded in bytes; this is not a bound on whole-process peak memory or source-artifact size. These conservative defaults are an execution policy, not evidence that a particular source build will fit.

`demo` and `run` seal the effective limits and supervision report, including observed/retained bytes, timing, EOF, reaping and cleanup errors. Their raw accepted argument hash remains separate from the effective-limit record. Failed outer attempts retain capped stream files, a failure record and available engine accounting. `inspect-run` never redispatches. Failed delegated commands without an outer directory emit supervision diagnostics to stderr; they do not implicitly create an output tree or partial-byte artifact. Existing engine output paths remain available when the command created them.

The supervisor owns one child. It cannot preempt a blocked operating-system process creation, kill a descendant process tree or bound outer source verification/publication after the child returns. In-process `verify` rejects the child-limit flags; outer `inspect-run` rejects explicit flags too. Operating-system signal, wait and pipe-close calls remain trusted host operations. The qualified checks are local Windows checks; the POSIX implementation is not thereby qualified. The old 0.4.1 launcher still has its original unbounded main `communicate()` and does not inherit this change.

Windows qualification uses the CLI polling loop with one reader per pipe. Microsoft documents an immediate return for `PeekNamedPipe` in a single-threaded application, with a blocking caveat for synchronous handles in multithreaded applications. Arbitrary embedded multithreaded use is outside the qualified deadline guarantee. Python also documents that initial process creation may not be interruptible. [Microsoft pipe API](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe), [Python subprocess limits](https://docs.python.org/3.11/library/subprocess.html#subprocess.Popen.communicate).

Workflow token/cost/time budgets, individual filesystem read limits and a child-process envelope are different limits. An elapsed-time bound does not estimate scientific feasibility or guarantee that a large source build will fit. Neither the facade nor the frozen engine is an operating-system sandbox. Host compromise, malicious native code, forced termination, filesystem unavailability and unreported remote billing are outside these consistency guarantees.

The locally qualified 0.5.1/0.3.12 build adds bounded retry to mutable JSON file
replacement on Windows: native access/sharing/lock errors permit three attempts
on the same staged bytes, with 50/100 ms requested waits. Permanent failures and
interruptions still propagate; cleanup errors cannot replace the primary error.
This neither retries model calls nor changes the no-clobber publisher. It does
not guarantee write availability, wall-clock completion, or version ordering
under contention. The [retained peer probes](../planning/review-assets/tether-ce-fixes-20261102/integration/windows-replace-peer/REVIEW.md)
include explicit failed writes and last-completing-writer-wins behavior. The
full Windows gate passes; earlier same-version candidate wheels have different
code hashes and must be treated separately.

## Verifying historical artifacts

Keep the original outer receipt hash outside the artifact tree. Select the exact archived TETHER wheel and the pinned `asof-target-agents==0.3.11` wheel in a separate environment; install those local files without dependency resolution or network access. Run that environment's `python -I -m tether verify --run-dir <archive> --receipt-sha256 <original-hash>`. Match the launcher source fingerprint as well as the displayed version: two source revisions with the same version number are not interchangeable proofs.

The original 0.4.0 launcher and artifact record remain in [the TETHER release record](../paper/release/tether/RELEASE-RECORD.json). The separately qualified 0.4.1 wheel is recorded in [its installed qualification](../planning/review-assets/full-project-review-20261102/platform/WHEEL-QUALIFICATION-FINAL-v3.json). Its local wheel SHA-256 is `b392440919fddb8cab17b1741ee716bfa95d4cc1172878725b2603b115b322d5`. These are local Windows qualifications. Hosted jobs, Linux execution and exact-byte provider reacquisition are not implied.

No receipt, source-linked quotation, passing regression or deterministic replay establishes therapeutic efficacy, valid causal inference, independent expert agreement or general model superiority. Numerical real-data prediction features remain empty and probabilities null until their derivations are qualified.
