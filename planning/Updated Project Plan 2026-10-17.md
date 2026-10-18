---
title: Updated Project Plan — October 17, 2026
date: 2026-10-17
status: registry-v04-technically-audited-scientific-gates-open
tags: [asof, roadmap, clinical-evaluation, feasibility]
---

# AsOf: current project plan

## Decision

Execution update: local preservation, private Git hosting and baseline off-machine
recovery/hosted CI are complete. The frozen v0.4 registry extraction and technical
label audit now cover 232,722 observations, 4,419 included programs and 37 distinct
recorded registry-start events across 27 programs. All programs/event links passed
original-row checks; 185 sampled programs have technical annotations and 33 have
AI-assisted narrative notes. No clinical training labels or scientific accuracy
estimates were produced. See [[Registry-scale Cohort and Label Audit v0.4]] and its
evidence index for canonical hashes, final registry backup/CI and limitations.

Next: separately freeze clinical-scope/condition-equivalence sensitivities, qualify
prior advancement and regimen/population roles, then simulate dependency-aware power.
Do not infer feasibility from raw program totals or resume the superseded per-case
sequence. The 2023 mappings remain contemporary oracle evaluator information.

**Registry-scale development sizing and its first technical audit are complete; scientific label validity and empirical design power are the next gates.** Further qualification of the same 15 non-excluded development representatives is an audit subtask, not the prerequisite for measuring whether T1 is feasible.

This revision reconciles [[Claude Review and Plan_claude10172026]] with the code, retained review assets and [[project-goals]]. It supersedes this file's earlier per-case-first sequence. The Claude review, original proposals, dated completion notes and sealed v0.3 artifacts remain historical evidence. The planning reconciliation was followed by the local preservation and v0.4 protocol freeze recorded above; no benchmark labels, paid calls or external publication are authorized by that freeze.

The working research objective remains H1–H6 from [[Beyond the Virtual Biotech Tooling Gaps and Project Plan]]. Technical reproducibility is established for the selected offline pipeline. Clinical discrimination, therapeutic interpretation and comparative dossier quality remain untested.

## Starting point and corrections

- The review's retained full validation reports **173 tests, zero failures/errors/skips, ten required probes, PowerShell syntax and installed-wheel checks passing**. This reconciliation read those results; it did not rerun that suite. The earlier 149-test claim remains a dated long-session result.
- Ten contemporary T6 outputs verify their source-copy path. They are large extractive evidence dossiers, not evidence of successful specialist reasoning or H5 improvement. The selected release contains 2,206 files, 31,554 case records and 11 bounded packets; features remain empty and probabilities null. Canonical selection remains `planning/run-registry.json`.
- Five AACT snapshots are restored: 2023-01-01, 2023-07-02, 2024-01-01, 2024-07-01 and 2025-01-01. The separate January 2026 archive is archive-checked only. No re-import is needed for the development sizing window.
- The v0.3 milestone accounts for all **24** exposed representatives, but `evaluate()` runs on only **two authored fact records, P01 and P24**. The other 22 have routing/disposition records, not completed transition searches. The 15 non-excluded representatives are not a sized program universe.
- Zero qualified events under strict v0.3 is a reason not to train on that set. It is not a conclusion that T1 itself is infeasible.
- The review's crude linkage scenarios give 659 higher-phase pair matches among 46,819 pairs, or 485 among 15,631 under a five-year recency restriction. These are neither adjudicated program counts nor statistical bounds: lagging linkage, comparator contamination, phase collapsing and cross-program matching can bias them in different directions. Recency is not origin-active status. The 343 twelve-month matches are similarly preliminary.
- I checked the local dependency metadata: Open Targets 25.09 `drug_molecule` has 18,119 rows and `drug_mechanism_of_action` 6,332 rows. The raw fields include molecule `id`/synonyms/parent IDs and mechanism `chemblIds`/`targets`, rather than the catalog's normalized field names. The evaluator adapter and source-inclusive checks are now implemented for the frozen v0.4 sizing route. Clinical-phase, linked-disease and approval fields in those tables must not enter origin predictors.

## Revised work sequence

### WP0 — Preserve the runnable state and correct status drift

Prepare logical local commits of runtime/tests, evaluator tools, catalog/anchors and documentation; inspect the intended contents and run the required validation before committing. Preserve all pre-existing work. Keep credentials, bulk originals and third-party page bodies out of the repository. Public-manifest names do not imply externally published or independently timestamped anchors.

At the start of this work package the remote, committed release and off-machine recovery test were missing. The later user-authorized execution completed private Git hosting, baseline hosted CI and off-machine restoration; see the milestone evidence index. Creating a private remote, transmitting data or choosing an off-machine destination requires the actual owner/destination and the user's instruction; none is assumed by this planning request. A local checkpoint and further local sizing design can proceed without waiting for a hosted account. Hosted CI is complete only after a real run is retained.

Back up the small evaluator/derived artifacts and source manifests to an authorized independent destination and test restoration. Preserve rights restrictions on page bodies. Repair catalog metadata through the existing single writer, without changing download-worker state or transport receipts:

- AACT acquisition already records five archives, while verification/blocker prose still says no restoration. Reconcile those fields with retained technical restore evidence; do not promote clinical validation.
- ChEMBL is partial/idle, and colocalisation is still described as downloading. Verify current files/processes before replacing those stale claims with a documented idle/stalled observation. Extend the controlled status vocabulary only if necessary; retain measured incomplete-file facts.
- Avoid full-file serialization churn for a few semantic edits. Publisher hashes, provider pipeline exceptions and scientific-validation status remain separate.

Exit: a recoverable local code/evidence checkpoint, consistent metadata, and an explicit record of any remote/backup/CI dependency still pending. No invented rights-holder notice or automatic public release.

### WP1 — Measure label feasibility at registry scale

**The v0.4 development-sizing protocol is now frozen before enumeration.** The v0.3 protocol and results remain unchanged. Development-sizing endpoint hierarchy:

| Tier | Meaning | Use |
| --- | --- | --- |
| A | Registry-recorded ACTUAL start of an eligible experimental next-phase program, same resolved drug/regimen and specified condition/population family | Primary feasibility-sizing endpoint; enrollment/development progression, not dosing or efficacy |
| B | v0.3 experimental-regimen first dosing with its stricter scope, time and source requirements | Higher-specificity audit tier; not automatically scientific gold |
| C | Any-arm initiation, efficacy, safety and administrative decisions as separate descriptive domains | Context and disagreement analysis, never a combined success label |

The benchmark's final endpoint is not approved or implemented by this document. Compare Tier A observability and error with the strict tier and an adjudicated reference before promoting labels. Freeze origin eligibility, next-phase edges, same-program rules, dose/population narrowing, prior advancement, outcome window and reporting cutoff. Distinguish program-level and target–indication estimands; prespecify any-program versus representative-program rollups and popularity sensitivity. New products, ADC payloads, active partners or unrepresented genotypes require explicit treatment.

Enumerate Phase 1/2 interventional programs active at the 2023 origin using the original snapshot, then seek transitions in the four later restored snapshots. An EXPERIMENTAL arm flag alone is insufficient: drugs linked to that arm can still be background, rescue or supportive agents. Resolve the role of the matched drug within the regimen. Preserve ambiguous mappings and mixed-phase stages instead of collapsing them or counting comparator targets.

Use the collected OT molecule/mechanism products on the evaluator side for alias/target mapping only. For 2023 this is explicitly contemporary/oracle mapping for sizing, quarantined from historical predictors and locked-test claims. Target assignments derived from later knowledge must remain qualified in the labels too. Full ChEMBL acquisition is not a prerequisite until the mapping audit demonstrates a missing dependency.

Report candidate and resolved counts, exclusions, missingness, phase edges, actual versus estimated starts, public-posting lag and snapshot observation intervals. Count drug/program/target/sponsor/evidence dependency components. A later snapshot containing an older actual date does not establish that the field was publicly available at the original endpoint. Specify both occurrence horizon and ascertainment/reporting cutoff.

Audit a stratified development sample: approximately 120 candidate transitions and 120 at-risk programs without a recorded transition, adjusted to actual counts. Use the 24 exposed cases as protocol examples. Obtain independent review where needed for scientific claims. Tier B is incomplete and cannot be treated as a perfect reference: estimate Tier A precision and agreement first; recall requires a systematic independent event search in sampled non-transitions with sampling weights and unresolved-case handling. Kappa alone does not establish label validity.

Then simulate power across measured prevalence, plausible score correlations/effect sizes, cluster dependence and label error. A target of 80% power for a 0.05 AUROC improvement is a planning scenario to freeze before model results, not a guarantee or a threshold inherited from the old independent-case calculation. Report PR metrics/calibration as appropriate. If enriching positives, record inclusion probabilities and population-weighted analyses; do not interpret an enriched sample's prevalence as the population rate.

Exit: one sizing/decision milestone with counts, audit uncertainty, cluster-aware sample/cost scenarios and explicit proceed/revise/fallback criteria. If mapping or audit precision is inadequate, report that before training. Scientific viability is assessed from these measurements, not the 24-case zero-label result.

### WP2 — Model, origin and outcome chronology

Retain 2023→2025 as exposed development data for retrospective/non-LLM sizing. A candidate later window is origin 2025-10-01 and endpoint 2026-10-01, with OT 25.09 and a separately defined reporting-lag allowance. It is not yet a leakage-controlled locked test.

The provider's current documentation confirms Sonnet 4.5 retirement on **2026-11-30** and June 2026 training cutoffs for the four current-lineup models. These are model/platform-specific constraints, not reasons to rush an underpowered comparison. Check the exact candidate legacy model's training cutoff, version behavior and availability when selecting it; some individual legacy documentation was inaccessible in this check. All contributing models, including Virtual Biotech's fixed chief-of-staff/reviewer, must pass the chronology policy. See [model lifecycle](https://platform.claude.com/docs/en/about-claude/model-deprecations) and [current lineup](https://platform.claude.com/docs/en/models/overview), checked October 17.

A reported training cutoff is a necessary screening input, not proof of no outcome contamination. Record model/version, post-training qualifications, prompts, evidence versions, masked outcomes, canaries, tool/egress controls and benchmark exposure. If chronology cannot be established, make a retrospective evidence-constrained claim. Changing Virtual Biotech's models is an adapted comparison, not unchanged reproduction.

**Data chronology corrections to the Claude proposal:**

- October 2025 origin requires origin-dated AACT state or verifiable version history; January 2025 plus later registry dates cannot silently reconstruct eligibility/status.
- A January 2026 archive cannot be the endpoint of a 12-month October 2025 window. It supports only shorter interim follow-up. Obtain endpoint coverage at/after October 2026 plus the specified reporting lag, or explicitly choose another design before outcomes are inspected.
- A file's Last-Modified header can reflect file construction/preservation and does not by itself prove first public availability. Combine release documentation, archived listings and product-level evidence; retain qualifications.
- Horizon maturity by calendar date is not complete public outcome ascertainment. Prior related-program exposure and registry/report lag must be checked before calling a set locked or unseen.

Prepare the chronology memo alongside sizing. November 13 remains a decision checkpoint from the review, not a committed execution deadline. Draft preregistration before inspecting the candidate later-window labels. Publishing it and selecting a paid run require the corresponding user decision.

### WP3 — Bounded evidence selection and T6 evaluation

Before adding more cases or a live model, implement a deterministic bounded selection baseline under the existing quote/select contract. A provider-score top-k may be one ranking baseline; keep source scores descriptive and incomparable across providers unless normalized under a validated policy. Also use fixed per-source/category quotas or round-robin selection so one prolific source cannot dominate by scale alone.

Record candidate universe, selected/omitted records, redundant studies, source/context diversity, bytes/tokens and coverage. Preserve finite packet/ledger limits. Benchmark the selected extractive baseline against any specialist under identical inputs, case sets and budgets. The current one-claim-per-observation output tests copying and can grow to the ledger limit; it cannot establish improved reasoning.

Define a claim rubric for fidelity, therapeutic relevance, action/modality/context fit, completeness and unsupported synthesis. Freeze fresh cases before reference review, audit a random sample independently for published claims, and report cost/latency. Implementing a provider adapter or running it is later work with an explicit model/data-use/spend decision; default remains $0 and uncertain billed calls are never automatically retried.

### WP4 — Deferred branches and reporting discipline

Hold additional genetics/MR, DICE/OneK1K replication, scorer training, full competitor execution, H4/H6 and T2–T5 until the corresponding evaluation gate is real. Keep the IL6R bundle as a qualified technical pilot. H1–H3 need a sized, temporally defensible cohort; H5 needs comparative scientific-quality evidence. None is established by passing checksums or null-probability dossiers.

Use one dated session notebook entry and milestone-level sealing. Record executable code by commit/hash once the working state is committed rather than copying repository files into every small bundle. Preserve existing seals. Create HTML review pages when a reviewer needs them, not as the default deliverable for every step.

## Decisions and immediate next action

The user can authorize a capped model run, remote publication, off-machine destination or preregistration submission when those concrete choices are ready. Those decisions do not block drafting the sizing protocol, auditing local schemas or preparing local preservation. Independent human availability affects adjudication and publication claims, not exploratory counts. Confirm exact account-mediated AACT versions only after the chronology memo identifies what is missing; do not request another broad download list now.

**Next execution unit: Task 2 in `TODO.md`, sample size/power and clinical feasibility.**
Registry extraction, private recovery/hosting/CI, and the fixed-cohort v0.5 scope audit
are complete. Task 1 passed 194 full-suite tests and original-row checks. Do not
repeat the extraction or treat the 37 recorded starts as independent validated
clinical labels. Task ordering and stop-on-blocker rules now follow the user's TODO.
