# Project reassessment after Q01

2 November 2026 UTC. Baseline: `43d0384`. **Q01 is complete for the locally qualified Windows CLI scope. Q02 is next; Q03–Q06 and the broader scientific programme remain incomplete.** This checkpoint adds software guarantees, not a new scientific result. The [corrective plan](<TETHER Corrective Execution Plan 2026-11-02.md>) remains the ordered roadmap.

## What changed and what was verified

TETHER 0.4.2 replaces unbounded child `communicate()` with one-reader pipe polling, an absolute child deadline and an aggregate stdout/stderr cap. Defaults are 3,600 seconds and 16 MiB, independently configurable from the unchanged 300-second workflow budget. Limits, raw invocation binding, measured bytes/timing, EOF and cleanup/reaping disposition are recorded. Timeout, overflow and interruption preserve the original failure and available accounting without a second dispatch. Completed outer receipts reject inconsistent process declarations even after internal hashes are recomputed.

The [capability table](../docs/TETHER-VERIFICATION-SCOPE.md) separates legacy APIs, canonical v2 checks, archived-only/source-inclusive verification, outer receipts and inspection. It also states the remaining boundaries: OS process creation and host calls are trusted, descendants are not contained, outer verification/publication is in process, and arbitrary embedded multithreaded or POSIX execution is unqualified. Failed delegated commands report diagnostics to stderr without inventing a durable outer directory; `run`/`demo` retain capped stream files and failure records.

Validation:

- All **86 package tests pass**, including the earlier semantic regressions and 13 new process/CLI methods. Tests exercise blocking, trickling, flooding, exact/over-limit output, inherited pipe handles, interruption, cleanup failure, invalid limits and preserved workflow budgets.
- Independent probes exercise process failures and accounting plus a genuine outer CLI run, rehashed contradictory process records, rejected abbreviated flags and in-process flag rejection. Their exact runs and source pins are retained under [peer evidence](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q01-20261102/peer).
- The final isolated **0.4.2 wheel** qualifies successful demo/anchored verification, wrong-anchor rejection, actual CLI timeout and overflow, bounded retained output, one dispatch, reaping and failure inspection. No optional Arrow or provider/model access is required. [Installed qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q01-20261102/platform/WHEEL-QUALIFICATION-FINAL.json).
- The matching archived 0.4.1 launcher still verifies its original demo and external receipt anchor. Five exact historical artifact/catalog/wheel hashes and seven tracked frozen scopes remain unchanged. [Compatibility](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q01-20261102/ARCHIVED-041-COMPATIBILITY.json), [preservation](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q01-20261102/PRESERVATION.json).

The final wheel is `data/cache/tether-042-qualified-build-v2/wheels/tether_target_agents-0.4.2-py3-none-any.whl`, 32,642 bytes, SHA-256 `090c49f8613101d31dd5a7859033ffcf830223ab99b3ffaa9b2f53abfda0dc06`. All 16 runtime source files match the wheel. The earlier intermediate wheel remains retained. The new version does not replace the old 0.4.0/P09 packets or claim their historical whole-suite qualification. The consolidated [Q01 proof record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q01-20261102/VALIDATION.json) gives exact evidence and limits.

## Full-project disposition

| Workstream | Status after this checkpoint | Next acceptance condition |
| --- | --- | --- |
| Q01 verification and child execution | Complete in the stated Windows CLI scope | A new environment or revised implementation needs its own qualification. |
| Q02 catalog policy | Design ready; implementation pending | Explicit input/validation dependencies and artifact/use roles, checked projections, immutable bindings and synthetic rejection tests. |
| Q03 scientific data readiness | Not qualified | One meaningful source-composition task with valid identities, necessary context, missingness and independent grouping. |
| Q04 fresh evaluation | Not frozen | A discriminating endpoint and feasible serialization/budget; avoid the current literal ceiling and equivalent 80/100 thresholds. |
| Q05 new study | Not run | Execute only a new justified, frozen schedule once; retain every failure. |
| Q06 paper/release reconciliation | Pending | Incorporate technical errata under a new version; owner author facts and acceptance remain explicitly deferred. |
| Original T1–T6/H1–H6 programme | Partial or deferred as documented in the critical review | No new clinical, causal, prediction or agent-superiority claim follows from Q01. |
| External experts / HR1–HR4 | Retired | No external response, recruitment or adjudication gate is reintroduced. |

The ten development dossiers, source-review reports and deterministic paper study retain their original scopes. Numerical prediction features remain empty and clinical probabilities null. The selected paper frame still does not establish study independence or causal genetics. The unqualified clinical quantities (36 endpoints, 17/32 observable registry states, 0/12 jointly ready cases) and older 65-missing interpretation slice remain separate. No new downloads, models, restoration, provider spending or stopped-monitor activity occurred.

## Critical decision for Q02

The [Q02 design](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q02-20261102/PROPOSAL.md) identifies a feasible offline next step. Preserve the current schema-1 catalog and frozen engine; add a versioned TETHER policy and explicit run-specific compatibility projection. Index all 178 products while admitting only named, pinned artifacts for a declared use. Other artifacts remain denied, and old runs retain their old policy. A projection alone cannot enforce artifact roles: canonical admission and verification must bind the policy, original case/snapshot/manifest, actual lineage nodes and projection.

Three corrections matter before implementation:

1. `genetics_qc_cases` is a validation dependency of `genetics_results`. LD is method-conditional; removing an unconditional LD edge must not imply that MR or colocalization is scientifically qualified.
2. AACT origin and later endpoint/follow-up use are distinct. A product label or file date is insufficient permission to expose an evaluator snapshot. Planned scorer training inputs really are labels; preserve that lineage and keep inference blocked until a separate chronology policy exists.
3. The legacy Python acquisition reconciler omits receipt ID and URL checks. A new canonical reconciliation path must check them, source hashes, release/path/size and immutable receipt identity. Do not promote collection from file presence, a technical restoration report or inherited metadata checks.

Implement pure schema/migration and rejection fixtures first; then stable input copying, projection, execution/verification binding; finally import the explicitly selected neutral metadata frame. Existing receipt evidence can support inherited observations but cannot be described as a fresh payload hash check. Keep the original transport worker and receipt bytes untouched. There is no external blocker to this engineering work, so no new file, account or expert request is warranted now.
