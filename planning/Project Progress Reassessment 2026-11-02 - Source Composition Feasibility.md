# Project progress reassessment: source composition feasibility

2 November 2026 UTC. Q03 is complete as a **reporting-only feasibility decision**. It does not qualify a genetics predictor, independent replication endpoint or new model benchmark. The accepted narrow technical-paper branch is now active: reconcile the manuscript and release under Q06 while leaving Q04/Q05 unactivated. This is an explicit scope decision, not completion of those experiments by omission.

## What was asked and checked

A fresh design agent defined a two-target, one-exact-disease source-composition question before seeing biological values or previous answers. It partitions exact Open Targets 25.09 `studyLocusId` references into shared and target-specific groups, then tests evidence/credible-set `studyId` and `variantId` identity where both sides exist. The [frozen specification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/task-spec/SOURCE-ONLY-TASK.md) and [design addendum](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/task-spec/DESIGN-ADDENDUM-01.md) distinguish missing comparisons, source coverage, identifier reuse and scientific independence.

Before source rows were examined, the selection rule bound the complete 100-file GWAS evidence universe and selected its lexicographically first eligible exact disease/distinct ordered target pair. No score, effect, label or desired overlap pattern was used. This is exploratory source feasibility, not a prospective benchmark or formal preregistration. These sources and the selected slice are now exposed.

The [source audit](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/data/SOURCE-FEASIBILITY.md) freshly reconciled 125 evidence/credible-set originals with their local acquisition receipts: **2,768,160,958 bytes**. Two original label files added 13,397,731 bytes. All 1,753,850 evidence rows and 2,862,043 credible-set keys were scanned for the required selection/linkage. An independently implemented check reconstructed the first eligible selection, the entire four-row slice, four linked rows and three labels; **1,160 assertions pass**. These are software/data checks, not independent scientific observations.

## Findings and consequences

| Finding | Consequence / correction |
| --- | --- |
| REV3L and RNASET2, exact disease `EFO_0000094`, form the algorithmically selected example. | Labels were resolved only after selection. This is not a recommendation to compare these targets therapeutically. |
| Four evidence rows link to four unique credible-set objects without missing or ambiguous locus keys. | Exact object-level composition is feasible. No effect, causal-gene or clinical claim follows from a successful join. |
| Evidence-side study and variant IDs are missing in all four rows. | All four study comparisons and all four variant comparisons are **not assessable**, never agreements. Missingness applies to this selected slice, not the whole release. |
| The four linked objects contain three study IDs and three lead-variant IDs; one study ID crosses target groups. | Count identifier reuse explicitly. Distinct records or strings do not establish independent studies, participants, signals or replication. |
| Linked rows are PICS/top-hit objects with study-QC, no-in-sample-LD and curated-top-hit flags; effect/uncertainty/sample-size fields are missing. | Preserve the provider flags. Do not infer effect agreement, harmonization, MR, colocalization, quantitative synthesis or target superiority. |
| The release-matched study file is absent; build/allele and cohort/overlap metadata remain unqualified. | A study table would improve traceability but would not by itself establish independence or supply valid regional causal inputs. No automatic download was started. |
| Sixteen L2G files have completed receipts despite stale catalog collection metadata; colocalization has four partial files and zero completed ones in the inspected scope. | Record the drift without promoting product readiness. Neither enters this task. The original 178-product catalog remains unchanged. |
| A deterministic set-and-join baseline completely specifies every required output. | No model advantage or need for another model experiment has been established. Do not manufacture difficulty by adding dependent fields or redundant thresholds. |

The task is richer than a single-row copy but still a fully deterministic reporting operation. A useful future scientific task needs an estimand that requires qualified scientific information and a comparison capable of distinguishing approaches. More source files or an agent label would not supply that automatically. The [independent route review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/review/ROUTE-REVIEW.md) supports the narrow technical-paper route.

## Resource and audit limitations

The successful source-audit pass took **16.14 seconds**, with 524,574,720 bytes peak Windows process working set, 570,220,997 decoded Arrow logical bytes and 2.17 seconds of source hashing. These are successful-pass measurements, not all-attempt costs or physical storage I/O. Repeated phases count again in logical bytes. A separate independent source replay has its own scope.

The first attempt failed at terminal Windows memory telemetry after extraction. The second attempt corrected the pointer binding but overwrote the first attempt's fixed-path projections, manifest and input binding. **First-attempt bytes, hashes and original binding timestamp are unavailable; byte identity across attempts cannot be proved.** Neither measured script revision has a contemporaneous byte-level pin. The retained post-run code is labeled as such, not retroactively represented as the executed revision. These limitations prevent presenting this exploratory audit as a fully sealed new study.

The reusable utility now requires fresh run IDs, reserves separate directories, refuses replacement and writes startup code hashes. Four focused collision/unsafe-ID checks pass with unchanged sentinel bytes and zero raw-source reads. The current utility was not rerun over the full sources just to obtain cleaner history. See [attempts](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/data/SOURCE-AUDIT-ATTEMPTS.json), [no-clobber checks](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/data/SOURCE-NO-CLOBBER-VERIFICATION.json) and [independent review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-q03-20261102/review/INDEPENDENT-FEASIBILITY-REVIEW.md).

## Complete programme status and next action

| Work | Disposition |
| --- | --- |
| C01–C05 full review/corrections | Complete in the retained review scope; old results and source originals preserved. |
| Q01 child execution / Q02 artifact policy | Complete for qualified Windows CLI/offline paths. Current TETHER is 0.5.0; old run verification requires matching archived launchers. |
| Q03 source task feasibility | Complete: reporting-only branch accepted, scientific extensions unqualified. |
| Q04 new discriminating evaluation / Q05 new execution | **Not activated; not completed.** No new candidate/reference pack, model run or statistical result is justified by this slice. |
| Q06 manuscript/release reconciliation | Next authorized work: separately versioned technical working draft and review packet, preserving old artifacts. |
| Author facts/declarations/acceptance | Owner-deferred. No new request, inferred facts or submission-ready claim. |
| T1 clinical prediction, MR, training/calibration, full Virtual Biotech, T2–T5, H6 | Conditional and unfinished; substantive data/chronology/validation needs remain. Numerical features stay empty and probabilities null. |

Q06 must incorporate the verified semantic limits, mathematically redundant native 80/100 thresholds, source-verification overhead, negative model-dispatch details and dependence/exposure limitations. Describe the later 0.5.0 fixes separately from the frozen study; their current tests do not retroactively strengthen old experiments. The small Q03 audit may appear only as exploratory feasibility with the retention limits above, never a new qualified benchmark. Reuse the existing formatter and positive release allowlist, qualify the new PDF/package, and retain the original experiment and archived packages byte-for-byte.

No external expert input, protected clinical outcomes, model/backend execution, new download, paid service, database restore, worker change or monitor restart occurred in Q03.
