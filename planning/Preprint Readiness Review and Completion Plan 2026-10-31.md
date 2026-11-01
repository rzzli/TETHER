# Preprint readiness review and completion plan

31 October 2026, America/Los_Angeles. Reviewed checkpoint: `10c7ba6`. **The project has a substantial tested engineering base and exploratory experiments, but it is not yet a complete preprint package.** The missing critical work is a paper-specific objective evaluator, an informative multicase evaluation, reproducible analysis and the manuscript/release package. Another exposed-case questionnaire or native infrastructure expansion will not supply those results.

This is the current paper-completion roadmap. It refines execution order in the [AI only evaluation plan](AI%20Only%20Evaluation%20Plan%202026-10-31.md), retaining its [no-external-expert decision](decisions/2026-10-31-no-external-expert-input.md), source isolation, cost and claim boundaries. No new human response, panel, expert approval or follow-up is required. Original H1–H6 and conditional branches remain preserved; completing this bounded paper does not complete the entire original programme.

## 1. Recommended paper and contribution

**Working subject:** auditable, time-scoped evidence workflows and automated source-reporting evaluation for therapeutic target dossiers. A possible working title is *AsOf: Auditable Evidence Workflows and Source-Reporting Evaluation for Therapeutic Target Assessment*.

The paper should ask whether explicit source eligibility, hypothesis scope, missingness handling and verification improve measurable source reporting under fixed evidence and resource budgets. Its empirical contribution must be a reproducible evaluation and an informative controlled result, which may be negative. The exact contribution and novelty remain hypotheses to test against the nearest literature; neither a high unit-test count nor additional provenance fields establishes a research advance.

| Proposed contribution | Existing basis | Evidence still needed |
|---|---|---|
| A reusable workflow with temporal/lineage gates, immutable evidence, evaluator isolation, durable attempt accounting and replay | Implemented framework and retained engineering acceptance | Exact-release reproducibility and focused controls demonstrating the claimed behavior, including valid-input false rejections |
| A target/scenario-scoped, source-grounded reporting evaluation with typed facts and explicit insufficient-evidence outcomes | H5-A specification and existing source/comparison utilities | Executable evaluator, lawful case/source subset, independent deterministic derivation checks, frozen protocols and reusable benchmark artifacts |
| Controlled evidence on reporting quality, completion and resource tradeoffs | Exploratory source-selection experiments and negative interpretation diagnostic | A new prospectively frozen multicase comparison with simple same-source baselines, ablations, all-cell accounting and uncertainty |

**Claim limits:** no validated clinical-success prediction, causal genetics, biological ground truth, therapeutic usefulness or expert equivalence is demonstrated. AI semantic judgments are secondary model-conditioned measurements. Original expert-preference H5 stays untested. H1–H4, T2–T5 and H6 are separate future studies, not prerequisites for this preprint. If only the retained engineering and exposed negative studies can be supported, the honest deliverable is a narrower technical/feasibility report; it should not be presented as a completed benchmark-performance paper.

## 2. Current status supported by retained artifacts

This review inspected current code/configuration and result metadata, not protected clinical outcomes, bespoke expert-response payloads, candidate answers or mask keys. No tests or model runs were repeated. Results below retain their original experimental scope.

| Area | Verified current evidence | What this does not prove |
|---|---|---|
| Framework | Package 0.3.11/default v2; retained 1,774 tests, no failures/errors/skips; 327 accepted code/resource pins have matched recent checks. [Acceptance](review-assets/recovery-step9-generation-contract-20261028/acceptance.json) | A fresh test on a final paper-release commit, scientific accuracy or novelty |
| Real development dossiers | Ten integrity-verified canonical dossiers; 31,554 source observations reported across overlapping case worlds. [Pilot report](../runs/literature-coverage-20261017T082208Z/pilot-report.json) | Ten held-out independent cases, 31,554 independent findings or validated interpretation |
| Retained source audit | Twenty distinct original rows, two per dossier, with mapping/row checks. [Audit](../runs/literature-coverage-20261017T082208Z/source-review.json) | Scientific adjudication or complete audit of every reported observation |
| Real source-selection comparison | Ten cases × six arms = 60 cells and 114 model calls. AsOf completed 10/10; the adapted Virtual Biotech arm completed 3/10 and exhausted its budget on 7/10. [Execution report](../runs/science7-v02-20261021T005551Z/execution-report.json) | Full dossier interpretation, fresh locked inference or superiority over the released Virtual Biotech system |
| Real top-one selection study | Eight tasks across five exposed cases; 32 arm results, 48 calls. AsOf and the adaptation each matched AI references on 6/8; lexical 5/8; provider score 3/7 evaluable, one inapplicable. Three reference ties and two none-sufficient tasks. [Acceptance](review-assets/t6-topone-20261023/final-acceptance.json) | Independent truth, a statistically established advantage, appropriate abstention or generative dossier quality |
| Real interpretation diagnostic | Six complete HTTP responses and zero frozen-contract passes, no retries. [Closeout](review-assets/recovery-step7-20261026/technical-closeout.json) | Six independent biomedical cases, estimated scientific accuracy or identification of model-capacity effects |
| Recorded comparison / v3 preparation | Four-arm recorded mechanics and pure generation preparation are accepted in their stated scope; neither is a successful new generated-answer experiment. [Recorded acceptance](review-assets/recovery-step9-four-arm-20261026/acceptance.json) | Model inference, repaired R07 outputs or native v3 qualification |
| H5-A objective measurement | Specification exists; code for selection/copy/Q1 overlap and source-ID agreement exists | Implemented typed-fact coverage, critical-distortion score, the 80% rule or the missing-input primary evaluation |
| Fresh source frame | R08 metadata/exposure scans exist, but zero fresh cases are qualified; fixed BTK/CTLA4 contexts are exposed. [Source feasibility](review-assets/recovery-step8-20261026/source-feasibility.md) | A ready locked evaluation cohort or permission to equate source nonmatches with fresh cases |
| Clinical branch | 36 unqualified endpoint labels; 17/32 states observable in the primary registry view; 0/12 jointly source-ready packages | Clinical efficacy labels, trained/calibrated scoring or a prediction result. These counts concern different scopes |
| Paper and release | Apache-2.0 code license, packaging, validation commands, portable fictional fixtures and historical hosted CI exist | A manuscript, bibliography, paper figures/tables, unified release inventory or exact-current-SHA hosted qualification |

No tracked manuscript draft or manuscript `.bib`/`.tex`, citation metadata or paper-specific data-card/release inventory was found in the repository-scoped scan. This is not a claim about files elsewhere on the machine. Empty real numerical prediction features/null probabilities correctly withhold unsupported prediction; they do not validate a clinical model.

Retain failed attempts as well as successes, including the earlier 28-cell/58-call matched execution ending in `ContractError`. Distinguish actual selection calls, raw interpretation calls, recorded responses, synthetic fixtures and preparation-only artifacts in every result table. The current paper must not say that all comparisons were recorded, or that source-ID selection is full interpretive generation.

## 3. Necessary change to the current priority

**Replace the immediate ten-item genetics-form task with the minimum shared typed-fact evaluator needed by the paper.** Keep A02's source/hash/scope/provenance/unknown/seal and response-lineage protections, but implement them around objective fact slots, common arm adapters and missing-input scoring. The ten genetics items contain semantic judgments such as attribution and sufficiency; validating their options does not measure H5-A's primary endpoint.

A03's retrospective audit of one exposed R07 pair can become an optional appendix closeout. It supplies neither fresh multicase evidence nor a primary typed-fact score and must not delay the main study. Existing source/question definitions may be used for exposed development if their pre-response provenance is clean. No old candidate is repaired or rerun, and no old case is relabeled unseen.

The immediate next stage is a **small source-to-fact-to-score prototype on 2–4 development cases**, including answerable and insufficient-input conditions. First demonstrate that useful nontrivial objective slots can be derived from actual eligible inputs; then implement only the evaluator needed to score them. Do not build another general framework before learning whether the proposed endpoint is measurable.

## 4. Ordered path to a complete preprint

| Stage | Concrete work and deliverables | Completion evidence |
|---|---|---|
| **P01 — Freeze paper scope and evidence map** | This review, contribution/claim matrix, current primary-source positioning and prioritized TODO; archive the preceding checklist | Every proposed abstract/result claim mapped to an artifact or explicitly pending experiment; no external-expert dependency |
| **P02 — Prove evaluation-data feasibility** | Define one bounded reporting task; inspect existing eligible raw subsets; select 2–4 development units including missing-input conditions; enumerate fact families, units/unknowns, locators, transformations, study/family clusters and exposure. Run a cheap deterministic field-projection/extractive baseline and create the later candidate/exclusion register | Replayable fact derivations, complete denominators and explicit baseline-ceiling check before P03 coding. Distinguish identifiers from reported measurements/context; if the task is trivial copying, narrow the claim or revise development scope before locking. No default twenty-case promise or candidate-performance selection |
| **P03 — Implement the minimal paper evaluator** | Versioned typed-fact representation, common scoring adapters, failure/missing-input scoring, source/temporal/role checks, response-ancestor exclusion and reproducible analysis primitives; reuse existing accepted helpers | Relevant regression/negative tests pass; independent implementation checks replay source-derived expected values. Adapters do not add omitted facts, repair outputs or require only baselines to use a generator-specific wire format. AI semantic choice correctness remains outside the mechanical primary |
| **P04 — Qualify a bounded development comparison** | Freeze and run the small development protocol with deterministic baselines, plain evidence-grounded LLM and AsOf where actual generation is qualified; include a Virtual Biotech-inspired prompt adaptation only under a declared comparable access path | All scheduled cells/failures accounted; measured resource fit and faithful scoring. If generation fails, retain the negative result; decide between a narrower feasible experiment and a technical/feasibility paper without restarting old cells/native expansion |
| **P05 — Freeze the evaluation set and analysis** | Lock fresh source/question units where possible, source/reference versions, target-family/source-study groups, primary contrast, effect/precision objective, conservative sensitivity assumptions, budgets, masks/order swaps, control/ablation schedules, exclusions and analysis | A reconstructable protocol with actual eligible counts. Development items and used tuning controls excluded from locked evaluation. If fresh coverage/precision is inadequate, state exploratory scope and its selection limits before results |
| **P06 — Execute the frozen experiments** | Run every declared clean-input, ablation and controlled fault condition once; retain originals, terminal accounting, semantic/source verification and separate AI secondary audits | No response-driven retries/repairs or favorable substitutions. Every planned unit appears in the analysis with a terminal disposition. Old R07/native failures remain unchanged |
| **P07 — Regenerate analyses, tables and figures** | Case-level paired summaries, source-study/family-aware uncertainty where supported, failures/abstention/missingness, coverage sensitivities, critical errors, false rejections, evaluator controls, per-judge secondary results and resources | One documented analysis command regenerates every main figure/table from frozen permitted inputs; row/count checks trace back to original outputs. No pseudoreplication from claims, judges, repeated passages or related hypotheses |
| **P08 — Complete the manuscript** | Editable manuscript source, rendered PDF, bibliography, related-work matrix, methods, all results including negatives, discussion/limitations, supplements, availability and AI-use/contribution/funding/conflict statements | All numerical claims and figure/table/citation references resolve; no placeholders or unsupported clinical/novelty/superiority statements. Intro/methods drafting can proceed alongside P02–P07; final results await computed evidence |
| **P09 — Qualify the research release** | Public artifact allowlist, data/source cards and rights decisions, frozen protocol/prompts/adapters/evaluator/analysis, exact release manifest, model/runtime/environment records, lawful acquisition instructions, wheel/source archives, clean-install study replay and applicable release checks | Every packaged non-code asset has a redistribution disposition; no human-response derivatives/credentials/private paths included; advertised study/baseline commands run outside the checkout and original drive roots. Exact release code SHA passes applicable validation/CI |
| **P10 — Final preprint readiness check** | Reconcile the final manuscript with release results, regenerated figures, references, disclosures and limitations; prepare the submission-ready local package | Complete PDF/source/supplements plus reproducible artifact index, no unresolved paper-critical placeholders, failures included and claims bounded. Actual upload/publication and final author details remain owner-controlled, not an external scientific-review dependency |

P02–P04 form the **next execution tranche**. Completing only a new plan or another reference schema does not complete that tranche. A negative result is reportable, but a positive model-performance claim needs actual generated outputs and the declared evaluation. No larger model, paid API, new bulk acquisition or full Virtual Biotech reproduction is assumed in this path.

## 5. Experimental design that would support the paper

### Primary task and fair comparators

Use the H5-A mechanical endpoint from the AI-only plan: case-level verified completion with zero mechanically established critical distortion and at least 80% of prospectively enumerated answerable typed-fact slots. Report full coverage distributions and frozen 60/80/100% sensitivities. Only typed fields or finite reproducible source syntax qualify; AI-only assignment of a fact's meaning is not objective truth. A mechanically valid answer can still contain scientifically unsupported prose, which belongs in the separate semantic audit.

Use the same frozen answerable-case denominator for every arm. Zero-slot cases have no coverage fraction and are a separate insufficient-evidence stratum; `0/0` does not pass. Report all-case completion and missing-input behavior as well. Identify fact families and provenance so an identifier-heavy benchmark is not described as broad therapeutic judgment.

Choose the primary contrast **before generation**, preferably AsOf against a plain same-model evidence-grounded workflow. This tests workflow contribution more directly than a comparison confounded by different models/tools. Include extractive and lexical/source-ranking baselines as floors and a Virtual Biotech-inspired prompt adaptation as a separately scoped comparator. Model-specific native-contract validity is not the common outcome score. If a required arm cannot run within the declared access/budget, predeclare the resulting narrower question; do not silently substitute recorded prose.

Fixed-evidence evaluation comes first. Retrieval policy is a separate frozen factor, not a simultaneous undocumented change. If only one approved generator is available, make claims conditional on it; platform research-agent availability is not a reproducible stronger-model control. Do not infer that failure uniquely reflects capacity rather than task/interface design.

Check the extractive baseline during development. If simple field projection already reaches the primary endpoint's ceiling, report that finding. Either study the actual verification/completion/resource tradeoff or revise the development task toward nontrivial source-scoping or multi-record composition with reproducible expected answers before locking evaluation. Do not create favorable locked cases or move the endpoint after seeing arm results. More identifiers or longer prompts do not by themselves create a stronger scientific benchmark.

Freshness means absence of prior project development exposure under the declared policy; it does not prove that public articles or facts were absent from model training. Record known model/training-cutoff information and keep unknowns explicit. This contemporary source-reporting study does not establish a historically uncontaminated clinical forecast.

### Controls and ablations

Predeclare at least these questions, and keep the number of ablations bounded by the actual hypothesis and compute budget:

- **Eligibility/lineage contribution:** inject clearly labeled synthetic later-information or evaluator-parent ancestors, including mappings. Compare full enforcement with a controlled ablation; measure detection, valid-input false rejection, terminal outcome and reporting impact.
- **Hypothesis-scope contribution:** exercise typed target/indication/action/modality/tissue mismatches without inventing biological direction. Distinguish scope checks from causal mechanism inference.
- **Verification contribution:** test altered numeric values/signs/intervals/units, wrong citations, source substitution and immutable/trace inconsistencies against frozen expected controls. Source quotation matching is measured separately from semantic entailment.
- **Missingness contribution:** compare explicit unknown/partial/abstain handling with a declared ablation and include an always-abstain baseline. Incomplete collection cannot produce biological absence.
- **Interpretation contribution:** compare plain grounded generation with AsOf and any declared critic/checker ablation. Test whether extra orchestration changes coverage/errors/completion under the same budget, rather than assuming more agents help.

Injected conditions are artificial challenge data, not observed biological errors or new real-world truths. Freeze held-out challenge controls separately from evaluator-development controls. Do not count existing unit tests as independent biomedical test cases. Fault-injection and clean-source reporting answer different questions and need distinct denominators. Keep every arm on the same eligible clean inputs in the reporting experiment; altered access in a fault ablation must be explicit rather than a hidden comparator disadvantage.

### AI audits and contamination controls

No bespoke expert response or response-derived artifact enters reference building, evaluation, generation, tuning or source/case/arm selection. Preserve existing returns as archive-only. Source/reference builders receive fresh no-fork contexts with an explicit source allowlist; they do not inherit this answer-aware chat/memory. New evaluator artifacts remain evaluator-only through every descendant. Procedural separation does not certify independent model errors or an OS sandbox.

AI source proposals/reconciliation, where used, are sealed before new candidate generation. Keep per-judge support/omission/transfer ratings, uncertainty and fixed order swaps separate from typed facts. Unresolved disagreement remains unresolved. The old candidates predate any new source reference and remain retrospective. ARES-style human-label calibration or expert-alignment claims are unavailable under this protocol.

## 6. Results and manuscript package

| Main item | What it should show |
|---|---|
| Table 1: scope and related work | Precise task, eligible evidence, verification and reference regimes; identify what is implemented or claimed in each primary source |
| Table 2: data/case flow | Candidate universe, rights/access, dates/versions, exposed development, exclusions, sufficient/insufficient strata, locked units and independent clusters |
| Table 3: primary results | Every arm's planned/terminal cells, completion, case-level coverage, critical errors, abstention/missingness and paired uncertainty |
| Table 4: controls and ablations | Detection and false-rejection rates, scope/lineage/missingness effects and failures, with artificial versus real-source units distinguished |
| Table 5: resource use | Actual calls/tokens/time/peak memory and overhead; unknown or unmetered platform costs visible; no total-cost claim from $0 provider spend |
| Separate secondary table | Individual AI semantic audits/order sensitivity/disagreements; no human preference or biomedical-truth interpretation |
| Figure 1 | Source → eligibility/lineage → typed facts → original output → score, with generation/evaluation separation |
| Figure 2 | Source/case/exposure/cluster/exclusion flow |
| Figure 3 | Paired coverage/completion distributions and intervals, with failed cells retained |
| Figure 4 | Controlled fault/ablation and resource tradeoffs; avoid presenting fault tests as clinical performance |

Suggested manuscript sections: introduction and bounded contributions; related work; source/temporal/scope model; workflow and failure/accounting design; evaluator and data construction; protocols/comparators; main results; ablations/resources; negative and stopped routes; limitations; reproducibility/availability and disclosures. Supplements hold schemas, fact derivations, source cards, lawful retrieval instructions, detailed exclusion/attempt registries, AI procedures and preserved diagnostic failures. The old one-case genetics exercise is optional supplementary history, not the paper's centerpiece.

## 7. Release and reproducibility gaps

The current package is Apache-2.0, Python >=3.11, default dependency-free with optional `pyarrow==21.0.0`. That does not license third-party source text/data. For every asset actually included, record source/version, original URL/citation/hash, dates and precision, rights/access depth, transformations, role, exposure and redistribution decision. Withhold source bytes when rights are unverified; release identifiers/locators/hashes and lawful acquisition instructions instead. Do not redistribute the entire acquired inventory as a paper supplement.

Create one release manifest tying each reported result to the exact code SHA, protocol/evaluator/analysis version, environment/model/runtime, input hashes and output seals. The 327 accepted internal pins are useful but not a complete research-release inventory. Keep wheel/source/release archives on an explicit public allowlist; gitignore alone is insufficient. All expert-response histories and response-aware derivatives stay private/archive-only and outside the new scientific inputs.

Fresh-wheel checks currently cover installed offline demo/verification. The paper needs an installed study/baseline/comparison smoke and at least the advertised lawful public fixture/replay, including relocation to a fresh root outside D:/E: assumptions and a correctly rejected invalid control. Preserve matching-version requirements for old runs rather than claiming universal replay.

Run appropriate final code/package tests once the release code is stable, and qualify the intended release SHA. Historical CI passed an older commit; current HEAD is not thereby hosted-qualified. The [workflow](../.github/workflows/validate.yml) has a 20-minute job limit while retained local full validation took about 42.4 minutes. This is a **runtime risk**, not proof of hosted failure: measure the release matrix and adjust the declared job budget only if warranted. Include fresh exact-SHA hosted Windows/Linux core/full evidence when that is part of the advertised release; do not infer it from a green historical job or a documentation-only check. Any push/publication or missing account permission is handled only when a concrete release candidate exists.

The final package needs manuscript source/PDF, bibliography, figure/table source and outputs, protocol, result/exclusion/attempt manifests, runnable analysis commands, data/model/source cards and availability/AI-use/contribution/funding/conflict statements. Author names/affiliations and actual submission are owner-controlled metadata/actions; they are not a request for external expert judgments. No publishing is authorized or performed by this review.

## 8. Updated primary-source positioning

This is a focused check from the existing Virtual Biotech/evaluation seeds, not an exhaustive novelty survey. The proposed distinction below remains an inference to substantiate with a benchmark and experiment.

| Primary source | Implication for this paper |
|---|---|
| [Zhang et al., The Virtual Biotech, Science 2026](https://pubmed.ncbi.nlm.nih.gov/42752167/) and [pinned implementation](https://raw.githubusercontent.com/harrisongzhang/TheVirtualBiotech/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/README.md) | Use the canonical publication and exact baseline revision. The pinned implementation supports scripted headless execution and separates artifact integrity/evidence coverage. Retire blanket claims that it lacks batch use or checks only hashes. A prompt adaptation inside AsOf is not full system reproduction |
| [Sokolova et al., Alvessa, 2025 preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC12773016/) | Evidence-grounded target assessment and statement-level verification/corruption controls already exist. Generic verification or numeric/identifier mutations alone are insufficient novelty |
| [Le et al., TxBench-PP, 2026](https://arxiv.org/html/2606.19245v1) | Structured drug-discovery answers and deterministic grading already exist. Explain the different task, inputs, reference derivation and scientific limits |
| [Qu et al., BiomniBench, 2026 v2](https://www.biorxiv.org/content/10.64898/2026.05.12.724604v2.full) | Process/rubric evaluation extends beyond final answers. Its expert-associated judge validation cannot be inherited by an AI-only AsOf study |
| [Gao et al., ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/) | Correctness and citation quality are distinct established measurements; do not claim their separation as new |
| [Windisch et al., Show Your Work, 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13252682/) | Mechanical quotation validation plus separate support assessment is already studied in biomedical text processing; the distinction alone is not a novel contribution |
| [Saad-Falcon et al., ARES, NAACL 2024](https://aclanthology.org/2024.naacl-long.20/) and [Zheng et al., LLM-as-a-Judge, 2023](https://arxiv.org/abs/2306.05685) | AI judging needs explicit error/bias treatment. No uncalibrated AI-only confidence interval is represented as a human-corrected estimate or external scientific validity |
| [Patel et al., Retrieve to Explain](https://arxiv.org/html/2402.04068v4) | Evidence-based target ranking and historical outcome evaluation are different estimands from source-reporting H5-A; retain them as context/future clinical comparison rather than implying reproduction |

The proposed contribution is the **combination of a reusable target/scenario-scoped evaluation artifact, explicit source/version/cutoff and evaluator-lineage controls, and measured effects on reporting, rejection, missingness and resource tradeoffs**. Whether it is sufficiently novel or useful remains to be established. A complete preprint is an auditable research argument with reproducible evidence, not a promise of journal acceptance.

## 9. Completion boundary and deferrals

Preprint readiness requires: bounded claim and related work; a complete appropriately scoped empirical report; executable primary measurement or an honestly narrower technical-note scope; all attempts/negative results and uncertainty; a finished manuscript and reproducible lawful artifact package; appropriate exact-release validation; and no unsupported scientific claims. Positive superiority is not mandatory. Missing scientific outcomes cannot be replaced by software-test counts, AI agreement or policy prose.

Defer the clinical prediction/scorer/MR programme, T2–T5, H6 reconstruction, full original Virtual Biotech reproduction, new model acquisition, production deployment and optional native-bank expansion from this paper unless a stated paper claim actually needs and qualifies them. Retain all existing FAILED/INCOMPLETE_TIMEOUT results and no-retry rules. Existing $0 provider spending, no unapproved data/model acquisition, empty real numerical features/null clinical probabilities and untouched downloader/stopped monitor boundaries remain.

**Next concrete task: P02**, the 2–4-case source-to-fact feasibility prototype and a frozen objective scoring specification. P03 evaluator implementation follows that evidence; old A03 genetics review is optional and no external expert response is needed.
