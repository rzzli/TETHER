# TETHER full project critical review

Review date: 2 November 2026 UTC. Baseline: `21f64e7`. This review supersedes earlier **next-action instructions**, not their experiment records. The companion [corrective execution plan](<TETHER Corrective Execution Plan 2026-11-02.md>) is the current roadmap.

**Verdict:** TETHER has a substantial auditable engineering implementation and a reproducible, narrow source-reporting result. It is not yet a scientifically validated target-assessment agent, clinical predictor or broadly qualified benchmark. The retained paper quantities recompute correctly, but new adversarial probes demonstrate that the earlier semantic-verification guarantee was incomplete. Those findings justify a versioned correction and a paper errata note before further release qualification. More audit counts alone will not resolve the scientific limitations.

## Scope and confidence

The baseline inventory covers 7,474 tracked files. All 205 active runtime/tool Python files, totaling 55,544 lines, were inventoried and AST parsed. Deep reviews covered the execution and verification boundaries, source ingestion, catalog and data utilities, clinical/genetics feasibility, study compiler/scoring/analysis, releases and current planning. The test tree contains 154 Python files/31,499 lines; planning contains 6,744 files and 219,799 Python lines, much of it historical audit code. These counts describe the baseline, not independent evidence observations.

Three parallel code/data/results reviews support this pass. The data review statted 1,222 catalog-named paths and examined selected neutral receipts, inventories and schemas. It did not rehash every raw dataset or inspect every historical script line. The results review rechecked retained result bindings and arithmetic, rather than rerunning the experiment. Protected outcomes and historical human returns were excluded. This is a project-wide risk-based review with an explicit coverage inventory, not an assertion that every possible defect has been ruled out.

Evidence: [inventory](review-assets/full-project-review-20261102/BASELINE-INVENTORY.json), [platform review](review-assets/full-project-review-20261102/platform/PLATFORM-REVIEW.md), [data review](review-assets/full-project-review-20261102/data/DATA-REVIEW.md), [results review](review-assets/full-project-review-20261102/results/RESULTS-REVIEW.md), and [validation record](review-assets/full-project-review-20261102/VALIDATION.json). Findings below distinguish reproducible bugs, unsupported generalizations and future research requirements.

## Critical findings and dispositions

| ID / priority | Finding and practical consequence | Disposition |
| --- | --- | --- |
| F01 / P1 | Legacy v2 verification accepts completed runs whose coverage says `failed`, `biologically_absent` or an invented status. This can be produced and verified under the producer's original newly generated receipt, so it is not merely a wholesale-tampering scenario. | New TETHER 0.4.1 CLI semantic boundary reconstructs expected state. The frozen legacy engine/direct API retains its weaker historical guarantee. |
| F02 / P1 | Review events can select no records while the ledger commits records, yet legacy verification accepts the trace. A newly anchored dossier can also contain extra assertions without failing the legacy semantic check. | New CLI boundary checks review-to-commit consistency and deterministic dossier reconstruction. Old receipts still detect byte changes against their original anchor; they did not prove these missing relationships. |
| F03 / P2 | `Test-DownloadBatch.ps1` accepted matching bytes/URL/path with wrong receipt, dataset and release identities. A transport check could therefore label the wrong product complete. | Corrected exact identity comparisons; synthetic negative and valid fixtures retained. Downloader and existing receipts remain untouched. |
| F04 / P2 | `tools/validate.py` could perform expensive work before discovering an existing report path, and prerequisite/structural exceptions produced no requested failure report. | Added early collision rejection and stage/error reporting for exceptions and interruption. Hard termination and competing publication remain explicit limits. |
| F05 / P2 | Genetics orientation returned a usable orientation for identical REF/ALT alleles. Such a row does not represent the intended biallelic SNP. | Current QC helper rejects it; focused regressions pass. Previous technical QC outputs are not retrospectively upgraded. |
| F06 / P1 data design | `genetics_results` is agent evidence but declares evaluator-only `genetics_qc_cases` as an unconditional dependency. Validation fixtures and scientific input ancestry are conflated. | Require a versioned catalog migration separating validation dependencies from lineage. Preserve the existing catalog fingerprint until that migration is tested. Do not weaken evaluator exclusion to satisfy the dependency. |
| F07 / P1 data design | One AACT product spans origin and later evaluator snapshots; product-level roles cannot fully describe artifact-specific use. Queued/planned statuses also lag some local files and technical regional subsets. | Add release/artifact-level manifests and receipt reconciliation before any status promotion. File existence is insufficient. |
| F08 / P1 scientific scope | Twelve identity-ranked units are not twelve independent studies; original study/cohort/variant identity and broader exposure are unresolved. | Keep descriptive scope. Study metadata and a verified composite join precede causal interpretation or inferential comparisons. |
| F09 / P2 study design | Each native measurement group has only 2–4 answerable components. For every native unit, `ceil(0.8*n) = n`; the 80% and 100% criteria are identical. | Correct planning and paper interpretation: those two sensitivities are not separate robustness evidence. Preserve the original prespecified results. |
| F10 / P1 interpretation | The deterministic assembler copies typed source fields and reaches the ceiling. Designed invalid controls test explicitly implemented guards. | Retain the engineering result, but do not infer reasoning advantage, realistic error prevalence, unseen-fault generalization or multi-agent benefit. A separately designed nontrivial task is required for those claims. |
| F11 / P2 resources | Source verification consumes about 97.05% of production time; logical hashing is about 49.00 times the 2.866 GB source frame. | Profile and optimize a new version using stable, scoped reuse of verified inputs. Keep physical I/O distinct from logical bytes and never reuse a cache across changed sources. |
| F12 / P1 model attribution | Negative generator results do not isolate model capacity, workflow quality and output-format/token constraints. The audit stage was never reached in P04. | Preserve the negative observation. Any future generator branch needs exact output-token feasibility and a new matched protocol; do not reopen closed attempts by retries. |
| F13 / P2 operational bounds | TETHER child `communicate()` lacks a whole-process deadline/output cap; some HTTP/Tabix paths provide inactivity or byte bounds rather than absolute end-to-end bounds. | Treat current limits as conditional. Add supervised wall-time/output bounds before advertising robust unattended or hostile-input execution. |
| F14 / P2 maintainability | Historical audit code and status narratives exceed active runtime/tool code substantially. Multiple check counts and stale “next” instructions obscure current authority. | One current plan and a small coverage/claim register; preserve historical evidence without repeatedly expanding the verification stack. |

P1 means material to the advertised guarantee or scientific interpretation; it does not imply that a reported numerical result was falsified. Reproduced bug probes and fixed-version tests are separate evidence from historical acceptance tests.

## Platform assessment

**Contracts, immutability and lineage.** The distinction between information availability and computation time is well designed. Typed evidence, hypothesis scope and evaluator ancestry are useful controls. Their guarantee depends on truthful metadata and complete supplied ancestry; hashes cannot establish publisher authenticity or reveal an omitted real-world source that was never declared. The new semantic findings show why a receipt and a general `verified` status are insufficient descriptions of coverage. Verification responses should enumerate exactly which relationships were reconstructed.

**Execution and backend behavior.** Journals, reservations, conservative versus measured usage and retained failures are strengths. Generic Python backends cannot be forcibly bounded by cooperative timeout checks. The local HTTP paths and outer child process also need absolute elapsed-time supervision before a long unattended workflow is qualified. Test delayed output, endless small chunks, blocked reads and cleanup failure with fictional local processes. Do not turn a timeout into success because some earlier claims were committed.

**TETHER facade and legacy compatibility.** A separate namespace preserves legacy type/token identity and avoids rewriting archived science. It also creates two verification surfaces. The stricter 0.4.1 CLI must be explicitly distinguished from direct `asof`/aliased legacy APIs. Serialized exception names do not prove custom-class inheritance, so that aspect of exceptional control flow remains unqualified. An old TETHER run needs its matching launcher wheel because the receipt binds launcher bytes. The 0.4.0 review ZIP remains a historical qualified artifact; new working-tree source does not retroactively belong to its qualification.

**Ingestion and supporting utilities.** Explicit projections and excluded clinical fields are preferable to importing every provider column. The production path retains row locators, contexts and selected-subset coverage, but these do not make uncollected inputs biologically absent. Receipt identity must agree with bytes, product, release and path. The fixed standalone verifier now checks that relationship. The old downloader's mutable receipt behavior remains a separate known risk; retain content-addressed receipt copies, and design a successor before resuming sensitive pinned acquisitions.

**Testing and reproducibility.** Fresh targeted regressions plus counterexamples are more informative here than another aggregate assertion count. The earlier 1,973-test result is valid for its stated revision, not a current whole-project certificate. The new defects passed earlier suites because the relationships were not asserted. Windows installed replay is established for the old package; current hosted jobs, native Linux replay and fresh exact-byte reacquisition are still distinct unqualified scopes. Deployment or public release should name the exact tested revision and environment.

## Data assessment by layer and family

There are three different frames which must remain distinct:

1. **Catalog plan:** 178 products/83 providers; 22 collected, 19 queued, 3 partial and 134 planned. Parsing is recorded as `not_run` for 177 products and `parsed` for one; all 178 catalog validation statuses are `not_run`. These coarse fields do not erase retained subset-specific technical checks.
2. **Canonical development dossier build:** the October 17 literature build reports 2,206 files, 9,038,960,079 bytes, 2,194 evidence files and no missing inputs within its declared manifest. Its 31,554 case observations overlap across hypotheses. The **65 missing inputs refer to the older frozen interpretation slice**, not this canonical build or the whole catalog.
3. **Paper study:** 137 pinned originals, 2,866,248,239 bytes, twelve selected native units, 24 original rows and 180 requested fact slots. This is a selected reporting frame, not full Open Targets coverage or a genetics-ready population.

The bounded path check found 1,145 present and 77 missing catalog-named files; missing paths belong to queued/partial products. Some queued entries already have all their listed files, but their receipts still need reconciliation before promotion. No collection, parsing or scientific status was automatically promoted during this review. D: and E: each have about 1.5 TiB free at inspection; that supports the existing pilot and says little about unbounded single-cell or complete-QTL acquisition.

| Data family | Critical feedback and next acceptance gate |
| --- | --- |
| Identifiers and coordinates | HGNC acquisition date is not a certified annotation-release date. Validate namespace/build versions and preserve exact mapping ancestors; no modern mappings silently fill a historical gap. |
| Open Targets and baseline compatibility | The reporting subset is usable, but the Virtual Biotech input layout is much broader. Complete compatible tables and an explicit access projection are prerequisites for any full-system reproduction. |
| AACT, trials and clinical labels | Restoration is engineering success. Trial status/phase transitions do not establish efficacy. Origin eligibility, reporting lag, censoring, intervention/target mapping and source-supported endpoints remain prerequisites. Keep 36 unqualified endpoints, 17/32 observable states and 0/12 jointly ready cases distinct. |
| QTL/GWAS/LD | Regional technical subsets are useful feasibility evidence, not complete validated genetics features. Require study/variant/build/allele identity, ancestry, sample sizes, overlap, assay identity, units and uncertainty. LD requirements depend on method: SuSiE/correlated instruments need compatible LD, basic ABF colocalization does not. Significant-only hits cannot replace dense regional colocalization inputs. See the method-specific requirements in Q03 of the corrective plan. |
| Burden/direction/genetic safety | Association or variant consequence does not identify therapeutic intervention direction. Explicit nulls and independent direction rules precede any scoring feature. |
| Perturbation | Controls, replicates, dose/time, cell/model identity and assay comparability are required. Local collection is not a qualification of disease-context transfer. |
| Expression/proteomics/spatial | Cell type is not automatically tissue; expression is not target accessibility or causal dependence. Use selected studies with explicit contexts before bulk acquisitions. |
| Pathways/disease context | Account for upstream overlap with Open Targets. Multiple presentations of the same upstream study are not independent support. |
| Structure/modality | Structure and pocket features need validation for the proposed mechanism and modality. Restricted PROTAC-derived material remains excluded from a default public route. |
| Literature | Publication date, version, full-text reuse rights and evidence availability are different fields. Citation correctness cannot establish entailment or clinical truth. |
| Safety/competition | Preserve terminology restrictions and spontaneous-report biases. Counts are not incidence or causal risk; patent coverage is not freedom-to-operate analysis. |
| External benchmarks | Each benchmark needs lawful access, task-compatible projection and exposure accounting. Merely cataloging R2E/TRQA/GenomeArena/TargetBench/BiomniBench/TxBench does not execute them. |
| Project-generated references | Source-derived reporting references can support mechanical scores. Historical expert responses and their descendants remain excluded. AI agreement does not add independent biological truth. |

## Results and scientific interpretation

The independent results pass rechecks 104 bindings/arithmetic relationships. The main reported quantities agree: twelve exact literal outputs; 40/48 populated measurement slots; 108/132 populated identity slots; all 38 outputs and 90 decisions; invalid-control admissions 0/10, 2/10 and 7/10 for the three guard policies; no rejection among the four constructed technically valid controls. There is no demonstrated arithmetic error in these headline results.

However, the 180 slots are not 180 independent observations. Beta, standard error and the two p-value representation fields are related components; the latter are one value encoded twice. Identity fields dominate slot counts. Equal-weight family/group summaries are defensible as a declared software contract, but do not measure clinical informativeness. The small group sizes make the native 80/100 sensitivities redundant. All unavailable native measurement slots are present-column nulls; absent-column acceptance is tested in constructed/generic paths, not established on the native Parquet study.

The control findings show that implemented restrictions reject their designed violations. They do not estimate natural error prevalence. The perfect literal baseline is expected, and gives no evidence that agents improve source reporting. Removing guards also changes the acceptance definition; this is a policy ablation rather than a same-model biomedical superiority comparison. A useful next experiment would test unseen, independently specified errors and scientifically meaningful multi-record scoping using the same inputs and budget across arms.

Production took 203.828 seconds, including 197.812 seconds of source verification (97.05%). About 140.452 GB of logical hashing on a 2.866 GB frame is approximately 49 full-frame equivalents, not a measured physical disk-transfer figure. Performance improvement should target repeated source checks while retaining source-stability guarantees. Do not claim that agent orchestration accounts for the total time, or that $0 provider spending means zero project cost.

P04's five actual model dispatches comprise three plain calls and two proposal calls; no audit-stage dispatch occurred. Four malformed responses and one output-limit failure establish failure of that configured interface/task combination. The two-/eight-fact fictional follow-up remains mixed/negative development evidence. Neither experiment isolates general model capability. A future branch needs an exactly tokenized feasible reference serialization under the same output cap before any new call is considered; bytes are not a token-capacity proof.

## Feedback on every paper stage

| Stage | Current evidence | Critical feedback and correction |
| --- | --- | --- |
| P01 scope | Bounded technical paper explicitly selected | Make this current authority; stop directing readers to P02 as if it were unstarted. |
| P02/P02a feasibility | Prototype plus complete selected credible-set join | A populated measurement is not a scientifically usable feature. Join and context deficiencies remain. |
| P03 evaluator | Typed source reporting and deterministic scoring implemented | Add semantic-boundary regressions; distinguish source correctness from interpretation. |
| P04/P04b generator | Retained negative development branch | Correct attribution: no model-capacity or complete critic/workflow efficacy conclusion. |
| P05/P05a–d freeze | Twelve units and declared controls fixed before execution | “Prospectively fixed” does not mean fresh, independently sampled or independent studies. |
| P06 execution | Complete 38-output/90-decision schedule | Preserve failures and original code. New verifier defects need scope analysis, not silent repair of old outputs. |
| P07 analysis | Quantities reproduce | Explain threshold degeneracy and component dependence; profile verification overhead. |
| P08 manuscript | Working draft with bounded claims | Author facts are pending, and technical claim corrections also need reconciliation before submission. Add errata now; prepare a newly qualified final manuscript later. |
| P09 artifact | Old Windows source replay and local package qualified | Current fixes require their own tests/wheel/installed qualification. Do not inherit old broad test counts or label hosted/Linux checks complete. |
| P10 release | Local review packet available | Author acceptance and final reconciled technical qualification remain open. A ZIP is not submission readiness. |

## Original recovery programme and hypotheses

| Recovery area | Disposition and critical prerequisite |
| --- | --- |
| R01 scope | Technical reporting scope implemented; original therapeutic ambitions remain research questions. |
| R02 checkpoint | Retain exact revisions and artifacts; new fixes must have new fingerprints. |
| R03 archive compatibility | Old installed/reconstructed scopes retained. Verify old TETHER runs with their matched launcher; do not relabel new source as old proof coverage. |
| R04 correctness | Reopened by reproduced verification holes; new boundary fixes require targeted acceptance. |
| R05 diagnostic design | Improve output-token feasibility and matched conditions before any future generator experiment. |
| R06 infrastructure | Useful components exist; prioritize comprehensible interfaces over another controller stack. |
| R07 diagnostic capability | Negative six-response/zero-contract result retained; it is not repaired by later software tests. |
| R08 fresh feasibility | No qualified fresh independent set; grouping/exposure and eligible sources precede inference. |
| R09 interpretation arms | Recorded/failed arms do not establish generated scientific interpretation. Closed native/model attempts remain closed. |
| R10 timed development | Reuse retained measurements; future performance experiments need a new bounded protocol. |
| R11 power/design | Descriptive twelve-unit study has no independent-study power claim. Future sample size is based on clusters and intended effect/precision, not slots. |
| R12 execution/reporting | Original technical experiment completed; scientific/generalization limits and new verification errata remain. |
| R13 clinical feasibility | Registry observability, trial outcomes and efficacy are distinct; reliable endpoints are the gate. |
| R14 genetics/scorer | Technical regional QC is not validated MR, colocalization or calibrated prediction. Real features/probabilities stay empty/null. |
| R15 comparison | Full Virtual Biotech and locked clinical evaluation unexecuted. Earlier prompt adaptation is a different comparator. |
| R16 extensions/release | T2–T5, H6 and production remain conditional; local release success does not complete them. |
| HR1–HR4 | Retired by owner; no external expert-response prerequisite is reintroduced. |

H1–H4 and the original expert-preference H5 remain untested in their intended scientific sense. H5-A currently supports literal source-reporting mechanics. H6 needs reconstructable historical inputs and a separate exposure-aware design. T1 prediction has no qualified training/calibration/locked outcomes; T6 has development dossiers and bounded reporting, not validated decision support. T2–T5 remain conditional extensions.

## What counts as a proof in future planning

Every acceptance claim should identify **subject and version → tested property → inputs/anchor → checker → result → limitation**. A checksum establishes equality to an anchor, not truth. A receipt establishes declared execution bindings, not provider authenticity. A source replay establishes specified mechanical relationships, not every report sentence. A regression test establishes the exercised behavior, not statistical generalization. Several AI reviewers/checkers may share code, prompts and assumptions; call their reviews separately implemented where true, without claiming independent scientific observations.

Corrective planning therefore separates: **implemented**, **locally tested**, **archived-version qualified**, **scientifically supported**, **deferred** and **externally blocked**. Old dated assertions stay historical. New counterexamples constrain current claims even when the old acceptance run passed. Numerical check counts are supplementary evidence, never the main argument for correctness or publication value.

## Fresh validation and remaining work

The corrected 0.4.1 interface passes 73 tests in the core-only environment; the
independent follow-up passes 24 semantic tests and rejects all four retained
adversarial probes. The installed wheel passes a fresh offline demo and externally
anchored stronger verification. Separate fresh suites pass 115 critical legacy,
61 clinical/genetics/historical, six receipt-verifier (twelve fixture executions)
and thirteen validator tests. These scopes overlap and are not added together
as independent evidence. The source/result pass recomputes 104 relationships.

The new wheel is `tether_target_agents-0.4.1-py3-none-any.whl`, SHA-256
`b392440919fddb8cab17b1741ee716bfa95d4cc1172878725b2603b115b322d5`.
All fifteen current runtime source members match its installed qualification.
The original engine, catalog, paper/results, downloader, monitor and archived
0.4.0 packet remain byte-preserved. Initial failed tests, sandbox denials and
checker-context corrections remain recorded, not converted into successful runs.

The review and reproduced fixes are complete within these scopes. Absolute
execution/output bounds, artifact-level catalog migration, scientific qualification
and a reconciled release remain Q01–Q06 work. Author facts remain deferred.
No fresh 1,973-test whole-project gate, hosted execution, provider acquisition,
model experiment or scientific validation is claimed.

## Targeted external recheck

The pinned Virtual Biotech README describes broader therapeutic workflows, scripted/audited operation and 38 Open Targets datasets. This supports treating the project's prompt adaptation as a different experimental object, with a separately declared data/tool budget. It does not establish a reproduced competitor result. [Pinned Virtual Biotech README](https://raw.githubusercontent.com/harrisongzhang/TheVirtualBiotech/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/README.md).

Current Open Targets documentation distinguishes source-specific evidence and clinical-stage/outcome-related scoring. This reinforces the need for explicit clinical-field exclusion and source-specific interpretation. Current documentation was not used to certify the historical 25.09 schema. [Open Targets evidence documentation](https://platform-docs.opentargets.org/evidence).

The attempted Alvessa PMC full-text recheck returned a browser challenge. No new full-text/novelty verification is claimed from that request; retained prior bibliographic checks remain scoped to their original evidence. This targeted recheck is not an exhaustive peer survey.
