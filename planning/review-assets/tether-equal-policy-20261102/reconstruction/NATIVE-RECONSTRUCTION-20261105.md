# BG02 independent native reconstruction

The independent evaluator reconstructed all **1,296 scheduled cells** and agreed with the primary analysis on every decision, observable-mismatch key set, grouping and total. This establishes retained-evidence consistency for this run; it does not settle the separate quality review of the authored oracle or prove every policy clause. No case, expected answer or frozen execution source was changed after execution. The full output is [INDEPENDENT-RECONSTRUCTION.json](D:/Projects/drug_target_agents/data/benchmark/tether-equal-policy-20261102-attempt03/INDEPENDENT-RECONSTRUCTION.json); the tracked [compact numerical summary](D:/Projects/drug_target_agents/planning/review-assets/tether-equal-policy-20261102/reconstruction/NATIVE-RECONSTRUCTION-SUMMARY-20261105.json) preserves denominators, all 27 obligation groups, exposure strata, operation groups, measurements and code footprint.

The evaluator is a separate standard-library implementation and imports no runner, product validator, corpus producer or oracle-construction helpers. Its [27-test qualification](D:/Projects/drug_target_agents/planning/review-assets/tether-equal-policy-20261102/reconstruction/qualification-20261105-attempt02.json) includes the retained failing-first footprint regression. Native reconstruction exited 0 in 18.946 seconds; that analysis time is separate from benchmark execution. [Invocation and pins](D:/Projects/drug_target_agents/planning/review-assets/tether-equal-policy-20261102/reconstruction/native-reconstruction-20261105-attempt01.json).

## Integrity and denominators

The checked freeze SHA-256 is `26b30fef132fc6ce6acd6f1844a41521da47fb091d53e513d4b14588db476736`. Reconstruction checked the exact cell grid/order, every terminal and stream pin, raw worker-to-terminal projections, isolated interpreter/module identities, invocation arguments, oracle/descriptors, source files, installed packages and qualification/wheel references. The corpus inventory is **1,938 files, 339 directories and 4,387,486 logical bytes**. The source inventory has 46 pinned files. Installed Python inventories contain 66 AsOf and 18 TETHER files. These are local consistency checks, not signed external execution attestation or a complete OS/stdlib inventory.

There are **108 fictional cases × four arms × three repetitions**, with 324 cells per arm. The unique-case oracle contains 43 accepts, 64 rejects and one inspect-only decision. All decision/observable scores were identical across repetitions. Consequently, the following unique-case counts summarize repeated outcomes; the repetitions are not new independent cases. Thirteen cases are labeled exposed regressions and 95 newly constructed synthetic cases. Both groups were authored with knowledge of the project and policy. Family denominators overlap.

| Implementation | Correct decisions / 108 | Fully conformant / 108 | False admission / 64 rejects | False rejection / 43 accepts | Error cases |
|---|---:|---:|---:|---:|---:|
| TETHER | 108 | 107 | 0 | 0 | 0 |
| Independent validator | 108 | 107 | 0 | 0 | 0 |
| Hash/schema diagnostic | 56 | 12 | 51 | 0 | 1 |
| Reject-all | 64 | 63 | 0 | 43 | 0 |

All 1,296 launcher dispositions were `returned`; this does **not** mean every validator returned a successful policy verdict. Hash/schema returned `error` on **EP057 in repetitions 1, 2 and 3**, rather than a correct rejection. No unsupported verdicts occurred. Reject-all never supplies useful accepted-case completion and rejects the inspect-only case. Weaker controls do not implement the complete observable contract, so their full-conformance totals must be interpreted with that declared scope.

**EP077 remains a full-conformance mismatch for both full-policy implementations in all three repetitions:** `EP077-r1-tether`, `EP077-r2-tether`, `EP077-r3-tether`, and the corresponding three `independent` cells. The authored decision is reject, and both reject. The oracle also requires `unresolved_attempts = ["genetics:1"]` and `recovery_may_dispatch = false`; both observables are missing from the retained reject results. Thus each full arm is **324/324 decision-correct but 321/324 fully conformant** under the frozen scoring. Nothing was removed or repaired to turn these into perfect scores. Whether the rejected-journal oracle should demand these recovery fields is a separate adjudication question, not a reconstruction correction.

## Resource measurements

Timing below includes Python import **plus** the operation. This avoids crediting the reference adapter for lazy product imports while charging eager imports to the independent implementation. Launcher wall time additionally includes process startup/supervision. Every cell has the reported timing/memory/input measurements. Measurements are descriptive for this Windows, fresh-process, tracemalloc-instrumented execution, with three correlated repetitions per authored case; there is no cold-cache or cross-machine speed claim.

| Measurement across each arm's 324 cells | TETHER | Independent | Hash/schema | Reject-all |
|---|---:|---:|---:|---:|
| Median import + operation wall seconds | 0.398180 | 0.121888 | 0.143604 | 0.055112 |
| Sum import + operation wall seconds | 151.445877 | 72.414438 | 46.460688 | 17.957212 |
| Median launcher wall seconds | 0.542239 | 0.271879 | 0.293464 | 0.192245 |
| Median import + operation CPU seconds | 0.375000 | 0.125000 | 0.140625 | 0.046875 |
| Maximum OS process-lifetime peak bytes | 306,601,984 | 297,009,152 | 290,480,128 | 25,083,904 |
| Maximum Python operation allocation peak bytes | 276,325,653 | 272,848,608 | 269,264,473 | 750,821 |
| Retained scratch bytes, summed after execution | 444,738 | 427,020 | 0 | 0 |

The median of 108 paired case ratios—each dividing TETHER's three-repeat median import-plus-operation time by the independent median for the same case—is **3.3478**, ranging from **1.0571 to 6.5488**. This is not the ratio of pooled medians, a significance test, or evidence about typical real-world workload frequency. Operation composition matters:

| Operation / profile | Unique cases | TETHER median seconds | Independent median seconds |
|---|---:|---:|---:|
| Inspect / catalog1 | 2 | 0.286819 | 0.052975 |
| Prepare / catalog1 | 52 | 0.369520 | 0.095730 |
| Prepare / artifact policy v2 | 12 | 0.458374 | 0.143479 |
| Verify / catalog1 | 38 | 0.631447 | 0.468395 |
| Verify / artifact policy v2 | 4 | 0.782226 | 0.731862 |

Each arm saw the same reported logical input inventory on every case. Summed once across the 108 cases, that volume equals the independently hashed corpus size, 4,387,486 bytes; summed over one arm's three repetitions it is 13,162,458 bytes. It includes preparation/control files, not only bytes actually read by a validator. Both full arms retained 231 scratch files in total. Scratch totals describe the files still present after execution, not cumulative writes, copied bytes over time, transient files or peak disk demand. Actual read traffic, physical I/O and page-cache behavior were not instrumented. OS peaks include imports; Python allocation measurements omit non-Python allocations. Arithmetic sums of per-process memory peaks are not meaningful concurrent-memory requirements and are not used here.

## Implementation footprint and limits

| Pinned code scope | Python files | Bytes | Physical lines |
|---|---:|---:|---:|
| Independent validator, including `independent_runtime.py` | 6 | 156,573 | 2,470 |
| Reference adapter | 1 | 23,024 | 404 |
| Entire installed AsOf package | 66 | 973,426 | 21,863 |
| Entire installed TETHER package | 18 | 115,713 | 2,150 |
| Comparison infrastructure | 2 | 36,200 | 613 |
| Frozen experiment tests | 7 | 73,735 | 1,225 |
| Separate runtime-only witnesses | 1 | 10,977 | 195 |

These counts explicitly compare different scopes. The entire installed packages include archive, study, ingestion and execution capabilities that the six file-validator modules do not reproduce. Package size is **not** a lower bound for an equivalent validator, an estimate of engineering effort, or proof that one architecture is inherently simpler. The reference adapter, shared comparison infrastructure, diagnostic controls, corpus construction, policy/evidence documents and tests are itemized separately in the numerical summary. This independent evaluator and its tests are separately pinned and not charged to either implementation. Python standard-library and operating-system implementation bytes are excluded.

The paired endpoint is validation of prepared files and retained archives. Runtime-only properties such as immutable objects, dispatch durability and exclusive publication require their separately retained witnesses. Correct rejection can arise from a different violated condition than the intended mutation, so oracle specificity and causal coverage remain separate reviews. Mechanical agreement here does not certify all clauses, independently establish scientific validity, or complete later native benchmark stages. On this finite corpus, both full implementations have identical scored decisions and identical EP077 observable deficiencies; the independent validator has lower measured timing, while the broader packages have additional responsibilities. The retained result supports that bounded comparison and should not be generalized beyond it.

The raw reconstruction SHA-256 is `6a16a1103791dab5d0255398414695c8c6bebc1e7fc673e4e7bda14920d96166`; primary analysis SHA-256 is `68af206e14b41f7b19a26360dae97e5c6781356af23c0b8c5dd746014bf01462`. Original corpus, oracle, terminal records and primary analysis remain unchanged.
