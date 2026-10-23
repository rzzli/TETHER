# Clinical validation: design reassessment and data feasibility plan

Date: October 22, 2026. Status: **planning assessment complete; proposed studies not activated**.

## Decision

Keep strict clinical-efficacy prediction deferred. End the repeated search for the
already exposed poster/trial. The next executable step should be a **bounded,
local-data audit of registry-observable outcomes**, with its own endpoint contract.
Use that audit to decide whether a registry operations benchmark is worth building.
It cannot establish target validity or therapeutic benefit.

For the main scientific contribution, prioritize a harder, source-grounded T6
comparison after that bounded audit. T6 quality does not require a clinical-success
scorer. A genuinely prospective clinical evaluation remains a later, separately
registered study, conditional on observable outcomes and adequate sample size.

This document proposes a change in work order and a separate operational study.
It does **not** change existing H1–H6 meanings, endpoints, labels, cutoffs or cohort
membership. The inactive `source-readiness-feasibility-v0.1` next-twelve study stays
inactive. Its retrieval failures remain failures; a new registry-only study needs
its own applicable controls rather than passing unrelated sponsor-PDF controls.

**No new user-supplied files, credentials, paid data or accounts are needed for
the first proposed phase.** Existing archive readiness is supported by retained
checks; recheck source seals and local restore paths before executing queries.

## What the evidence supports

| Retained finding | Consequence for the design |
|---|---|
| Two development pilots retain 36 unresolved endpoint labels each. The later pilot has zero qualified positive or negative labels for all three endpoints. | There is no qualified clinical training/evaluation set. These purposive samples do not estimate population label yield or prove that clinical validation is impossible. |
| The later origin screen processed 128 trials, with 36 meeting the old planned-maturity rule and 12 followed up. | A bounded origin frame exists, but its design and exposure are unsuitable for an untouched clinical test. Do not silently reuse its remaining members as a fresh holdout. |
| The 2023-origin registry audit found 4,419 automatically included programs, 27 with recorded starts, and 19 event-containing dependency components. | Program totals substantially overstate independent event information. These older proxy counts cannot supply a 2025 clinical power calculation. |
| The 2025 historical mapping frame has 61,541 conditional scopes across 12,941 trials; regimen/population equivalence remains unresolved. | Trial-level registry observations are easier to define than same-program clinical transitions. Scope counts are not qualified programs. |
| January 2025, January 2026 and April 2026 AACT restorations have retained technical checks and bounded source extractions. | A local snapshot comparison is feasible to attempt without another download. Full new-cohort field coverage has not been measured. |
| Primary report lookup authenticated a conference listing, but not its exact NCT bridge, primary results, complete decision rule or analysis chronology. | More effort on this same case has no established benefit. Preserve its unresolved state and stop the lookup. |
| Sixty matched T6 development runs were executed; AsOf selected all 37 offered candidates. | Infrastructure works, but that comparison does not demonstrate difficult prioritization or independent clinical utility. |

Evidence: [origin sample](Endpoint-specific%20Origin%20Sample%202026-10-21.md),
[follow-up assessment](Endpoint-specific%20Follow-up%20Feasibility%202026-10-21.md),
[registry audit](Registry-scale%20Cohort%20and%20Label%20Audit%20v0.4.md),
[scientific prerequisites](Scientific%20Prerequisites%20Execution%202026-10-18.md),
[primary-report stop decision](Primary%20Report%20Lookup%20and%20Source%20Readiness%202026-10-22.md),
and [matched T6 comparison](Matched%20T6%20Comparison%20Execution%202026-10-20.md).
These are retained project findings, not newly repeated database measurements.

## Why the earlier clinical route stalled

The design asks public sources to establish several different facts simultaneously:
an origin-eligible program, equivalent regimen and population, an authentic
prespecified efficacy rule, the corresponding analysis and decision, event timing,
and historical public availability. Registry status, completion, participant
responses and publication dates cannot fill those gaps. The difficulty is partly
endpoint observability, not merely search performance or insufficient disk space.

The requirements also differ by question. A formal efficacy decision requires a
decision rule; a documented registry record state does not. Actual first dosing
requires arm-specific treatment evidence; a newly registered study does not. An
endpoint called first-ever program advancement requires much stronger prior-history
coverage than an endpoint called a new higher-phase registry registration.

NLM distinguishes initial submission, submission meeting QC and public posting
as separate milestones. Keep all three distinct, and do not interpret QC as
scientific validation. The accessible [NLM explanation of record dates](https://www.nlm.nih.gov/pubs/techbull/nd17/nd17_clinicaltrials_enhanced.html)
documents that distinction; its 2017 workflow description is not a guarantee of
every current display behavior. The proposed primary diagnostic below deliberately
measures retained snapshot content, not earliest-ever public disclosure.

## Compare the available routes

| Route | Question and defensible claim | Data feasibility | Recommendation |
|---|---|---|---|
| A. Strict historical efficacy decision | Did the specified primary efficacy decision occur within the frozen window, and did its authentic rule succeed? | Current pilots lack qualifying outcomes, rules and chronology; a scalable negative-ascertainment route is unproven. | Defer prediction, training and additional same-case searches. Reopen only with materially new qualifying evidence under a separate protocol. |
| B0. Registry results-content state | Did structured outcome-results content appear between two specified AACT snapshots for an origin trial? | Existing local archives, direct NCT linkage and result-table extraction offer the shortest testable route. Completeness and field semantics still need validation. | Recommended next feasibility audit. Reporting/data-availability claim only. |
| B1. New higher-phase registration | Was a new, publicly registered higher-phase study observed in the specified registry window and linked to the origin regimen/population? | Registry dates/phase exist; clinical program linkage and denominator coverage remain difficult. | Optional second diagnostic only after B0 and an origin-only linkage audit. Never call it efficacy success, first dosing or first-ever advancement. |
| C. Source-rich retrospective efficacy examples | Can a system faithfully extract and qualify an explicitly reported trial conclusion? | Public reports/protocols may support selected examples; selection on accessible outcomes is unavoidable if used to enrich this set. | Useful evaluator-only methods fixtures, not prevalence, incidence, calibrated prediction or a replacement locked clinical test. Do not start another open-ended collection. |
| D. Prospective clinical evaluation | Do frozen predictions anticipate future, explicitly defined outcomes? | Cleaner prediction chronology; future follow-up, independent reference quality and observable decisions still required. | Later route. Feasibility first; no promise that a longer window solves missing rules or negative ascertainment. |
| E. Harder T6 quality comparison | Does bounded reasoning improve evidence selection and contextual accuracy under identical evidence and budgets? | Existing packets, original-row proofs, local model and comparison infrastructure are available. New task/reference design is needed. | Main near-term scientific priority after the bounded B0 decision. Independent of clinical scorer readiness. |

## Proposed B0 contract: results-content appearance

**Unit:** one NCT record. The question concerns the named registry snapshots, not
all results anywhere, patient efficacy, the sponsor's first analysis, or all trials
for a drug. Target/indication hypotheses are separate units and must not inherit
this label as target success.

**Source pair:** January 1, 2025 origin and January 1, 2026 endpoint AACT snapshots.
Use April 1, 2026 only as a separately reported later-snapshot sensitivity view.
These are source identities, not verified midnight-public availability timestamps.
Retain the old clinical occurrence/ascertainment cutoffs unchanged. No April row
backfills a January observation.

**Operational state, proposed for freezing:** `present` requires at least one
retained outcome-measurement row linked to a result outcome and result group for
the same NCT; `absent_in_snapshot` requires successful complete queries of those
tables with zero outcome-measurement rows; `unknown` covers missing NCT, missing
tables/columns, failed or truncated queries, broken joins and conflicting record
evidence. A record-level inconsistency overrides an otherwise present row. Partial
but internally consistent results count as present if they meet the specified structure;
this is not a complete-results or primary-efficacy assertion. Results posting
flags/dates are consistency checks, not substitutes for result content. For example,
a posted-results flag with zero queried measurement rows is a review hold, not an
automatic absence. The executable protocol must bind exact table/column names to
each archived schema before follow-up access.

**Origin risk set:** only records with verified `absent_in_snapshot` at origin.
Origin-present records are prevalent results and excluded from incident appearance;
origin-unknown records remain in the screening/missingness report. No requirement
for planned 2025 completion, an efficacy primary objective or an eventual result.
Removing the previous maturity criterion is an explicit new-study design choice,
not an amendment to the earlier pilot.

**Outcome:** `1` for absent→present; `0` for absent→absent with complete observed
source coverage; `null` for an unknown endpoint. A zero means exactly no qualifying
content in this defined endpoint snapshot. It does not establish that results were
never posted and removed between snapshots, that no analysis occurred, or that a
treatment failed. Preserve later appearance, disappearance, corrections and
conflicts as separate diagnostics. Sparse snapshots cannot establish exact first
appearance or time-to-event.

**Selection:** a new exposed development audit, at most 32 records. Use the already
sealed 128-member origin screen in its existing deterministic order, exclude the
two previously followed-up twelve-member packs, validate origin source identity,
and apply the B0 origin risk rule before opening any new follow-up. Retain the
disposition of every screened member; stop at the cap without follow-up-based
replacement. If fewer than 32 qualify, report the smaller denominator. Neither the
number remaining nor the number meeting B0 is established by this planning pass.
Prior origin exposure and repository/model exposure remain disclosed. This is not
the inactive next-twelve protocol, a random population sample, or a locked holdout.

**Access separation:** origin-result state inspection is allowed only after the
new request/schema projection is frozen. Follow-up remains evaluator-only. A fresh
membership seal must precede January/April 2026 queries. No scientific hold is
deleted from old records; B0 uses a new artifact namespace and endpoint identifier.

## Data needs and acquisition decisions

| Input → eligible source | Product → validation | Supported work / remaining gap |
|---|---|---|
| Existing 2025 origin archive, restore/source receipts and 128-member seal | Origin-only NCT roster, version fields and result-content state → hashes, schema, complete-query coverage, exact row proofs and reproducible selection | B0 sampling. Receipt/path revalidation required; no new archive initially. |
| Existing January/April 2026 archives, separately queried | NCT-linked result outcomes/groups/measurements, record metadata, explicit missingness → repeated read-only extraction, row/FK checks, source identity and boundary checks | B0 observation pair and later sensitivity. Counts for the new roster are not yet known. |
| Existing 2025 origin design metadata | Phase, sponsor, study type, planned dates, arm/intervention context → allowlisted fields and original-row audit | Describe B0 selection/missingness; potential operational baseline inputs later. Follow-up status is forbidden as a predictor. |
| OT 24.09 historical mapping products and original clinical scopes | Product/regimen/population/phase candidate links → ambiguity, comparator/background roles and historical ancestry checks | B1 only. Resource aliases are candidates, not proof of program equivalence. Full historical predictive evidence is not qualified merely because four mapping products passed. |
| Complete, specified registry candidate universe at origin/follow-up | New NCT registration candidates and search-coverage denominator → full-frame completeness, exact posting-date precision/type, deduplication and manual source audit | B1 only. Known old mapped programs do not provide exhaustive recall. Requires a new frozen query, not just the 32 selected rows. |
| Authentic protocol/SAP, exact arm/population report, rule and analysis/date bridge | Qualified efficacy decision record → source authenticity, scope, rule, timing and appropriate negative ascertainment | Strict efficacy route; presently missing at sufficient scale. More AACT snapshots alone do not provide these facts. |
| Existing T6 originals/packets and local model | Hard-selection cases and source-bounded reference sets → exact source proofs, versioned hypothetical scope and blinded arm evaluation | Main framework quality work. Cases/reference choices must be frozen before arm output. |
| Complete regional QTL/GWAS/LD and overlap/assay context | Validated predictive features → full genetics qualification and scientific review | Later genetics route. Existing regional technical QC does not qualify causal or predictive features; unnecessary for B0/T6. |

AACT describes daily registry ingestion into connected tables and offers historical
snapshots through account-mediated access ([official AACT overview](https://aact.ctti-clinicaltrials.org/landing)).
That architecture supports the proposed comparison, but does not certify our
particular restores or complete historical publication coverage. Existing technical
proofs are the local evidence. No stable historical-version API is assumed.

## Ordered work packages and acceptance gates

| Step | Work and concrete deliverable | Pass, stop and next action |
|---|---|---|
| 1. Freeze B0 design and validate guards | New versioned protocol, schema-only inspection, source seals, exact SQL/allowlist, sample cap, membership procedure and exposure register. Freeze the numerical observability threshold and rationale before follow-up. Add adversarial fixtures before execution. | Must distinguish zero rows from failed/missing data; reject orphan results, wrong NCT, truncation, future predictor fields and snapshot substitution. Stop on any unresolved extractor/integrity defect. Old source-readiness protocol stays inactive. |
| 2. Establish origin membership | Read-only origin projection, deterministic eligible roster up to 32, every exclusion/unknown retained, immutable membership seal. | No follow-up access before seal; no record replacement after seeing outcomes. If no members qualify, stop with a documented feasibility result. |
| 3. Extract and audit B0 observations | Two independently executed repeated reads per snapshot; state transitions, January/April differences, source-linked audit, runtime/memory/storage report. Audit all selected NCT state assignments, every positive/conflict, and original rows supporting each state. | All admitted states need complete query coverage and valid identity/joins. Extractor/integrity defects stop the affected batch until repaired; faithfully observed source inconsistencies remain record-level unknown and permit a completed feasibility report. A valid audit may find zero appearances; that does not justify changing the endpoint or sample. |
| 4. Decide whether to scale | Counts of screened, origin-qualified, observed, missing, appeared and unchanged records; sponsor/drug/target dependency summaries; measured audit burden. | No predictive expansion if either class is absent, provenance remains broken, or the prefrozen observability threshold fails. Proposed operational threshold: at least 90% of sealed members have source-qualified January endpoint states. This is a workload/coverage decision rule, not scientific validation or a population estimate. Passing supports only a separately designed larger feasibility sample, not model fitting or clinical activation. |
| 5. Harder T6 comparison | New task pack with genuinely competing evidence, relevance/contradiction/uncertainty references, frozen budgets and sealed outputs from AsOf, simple baselines and adapted Virtual Biotech. | Require a selection cap smaller than the number of plausible candidates and no answer leakage. Report omissions, unsupported claims, context errors, abstention, latency and cost separately. No score reuse from the easy 37/37 exercise. |
| 6. Conditional operational/clinical design | If B0 is useful, specify a larger representative operational sample. Consider B1 only with a program-linkage/coverage audit. For clinical claims, prepare a separately prospective, measurable endpoint and independent evaluation plan. | No clinical fitting, calibrated probability or superiority test until labels, predictors, chronology, sample size and reference quality independently qualify. A reporting benchmark cannot satisfy H1 clinical efficacy. |

Steps 1–4 form **one bounded feasibility cycle**. Plan for approximately 3–5
engineering/review days including a two-day implementation allowance; these are
estimates, not measured commitments. Cap membership at 32 and new clinical web
searches/downloads at zero. A failed scientific feasibility result ends the cycle:
no repeated enlargements or trial-specific rescue searches. Fixing a technical bug
requires a retained failure and versioned rerun, with exposure disclosed.

The existing extraction utilities bind particular cohorts and request shapes.
Reuse their verified components through a new tested request/entry point; do not
remove the old twelve-member guards or pass arbitrary SQL to bypass them.

Step 5 is approximately another 3–5 days if existing packets/model remain usable;
its case count and review workload require a task-specific freeze. Steps 6 and
prospective follow-up have no reliable completion estimate yet. Stages are scoped
so that completing documentation or a technical audit cannot mark broader Tasks
6–8 complete.

## Statistical and evaluation design

For the first audit, report explicit counts and reasons, not a population confidence
interval or a classifier score. The proposed ordered development sample is
purposive and exposed. Do not extrapolate its event rate to the registry or treat
32 NCTs as 32 independent drug-development events.

If a larger operational benchmark is justified, freeze a probability sample or a
clearly defined census, missingness analysis, stratification and dependency units
before follow-up extraction. Preserve all-member and evaluable denominators.
Use sponsor/product/target sensitivity clusters where supported; exact string
keys can miss dependence. If unknown outcomes remain, report worst-case bounds
for the event proportion: `positive/N` to `(positive + unknown)/N`, alongside
the observed fraction. These count bounds apply to a census or equal-weight
sample; unequal-probability samples require the frozen design weights for both
positive and unknown mass. Sampling uncertainty is separate. These are
identification bounds, not confidence intervals.

Choose a meaningful effect/precision goal and rerun sample-size simulations under
the new endpoint, event balance, missingness and dependence assumptions. The old
paired-AUROC scenarios (difference 0.05, target power 80%) are historical planning
assumptions, not a universal requirement for a descriptive audit and not evidence
of sufficient power. Freeze the primary metric and multiplicity before outputs;
use paired comparisons and component-respecting uncertainty where justified.
Operational metadata baselines should precede biological models: they reveal
whether a reporting task mostly reflects maturity/sponsor behavior.

No clinical probabilities are created by this plan. Any future operational score
must have its own endpoint name, training/calibration qualification and output
namespace. Performance on reporting or registration never validates efficacy
probabilities. An uncalibrated ranking also needs a frozen definition and leakage
checks before predictive evaluation.

For T6, use source-bounded references and separately labeled external-literature
questions. Two independently sealed AI reviews and a third adjudication can
support the authorized development workflow; they share model-family/search biases
and are not independent clinical truth. Reference authors must not see arm outputs
before sealing. A separate-source expert/panel assessment remains necessary for
claims specifically requiring independent expert validation; it is not a blocker
to the bounded engineering/source audit requested here.

## Chronology, exposure and prospective route

The pinned September 2024 Qwen2.5 model offers a pre-January-2025 weight chronology
route, with its exact training cutoff still unverified. Contemporary research
agents may assist exposed design and evaluator audits, but their later knowledge
must not generate historical predictor evidence, labels-as-features, answers or
model-assisted case selection for a claimed untouched test. Prompt/rule choices
informed by this project must be disclosed as retrospective development.

Historical predictors need all mappings/annotation ancestors eligible at origin;
2026 HGNC and OT 25.09 cannot repair a 2025 predictor gap. The old calendar windows
remain unchanged. No corpus or membership here qualifies as an untouched holdout.

A future prospective study should freeze: the actual new origin date; eligibility
and hypothesis/program identity; every contributing model/prompt/retrieval asset;
predictions and abstentions; endpoint-specific occurrence versus disclosure rules;
horizon and later ascertainment; missingness and competing events; reference review;
and stopping/statistical rules. A 12-month horizon plus a separately specified
reporting allowance is only a design candidate, not an activated date commitment.
Freeze and, if desired, publicly register before future outcomes. Local Git history
does not establish public registration or eliminate retrospective design exposure.

## Resources, user dependencies and risks

Free space measured during this planning pass: **D: 1,754,972,614,656 bytes
(about 1.60 TiB); E: 1,685,079,273,472 bytes (about 1.53 TiB)**. These figures are
time-specific. Existing bounded registry extractions were small relative to this
capacity; no new full restore is planned for B0. Reserve a provisional 5 GiB for
selected extracts, indices, logs and a second evidence copy, enforce measured
growth limits and stop before exceeding the reservation. This is a workspace
allowance, not a measured output estimate or proof that all planned datasets fit.
Provider spending remains $0; local compute/review time is not economically free.

| Risk/dependency | Planned handling |
|---|---|
| Restore path or receipt no longer verifies | Stop affected extraction and identify exact missing/corrupt artifact. Ask the user for a file only if a verified local recovery is unavailable. |
| Sparse snapshots, deleted/corrected rows, reporting lag | Limit B0 to observed source states; January/April disagreement stays separate. No inferred continuous history or clinical negative. |
| Selective availability and exposed selection | Retain screen denominator, missingness and exposure. A later representative study requires a new frozen sampling design. |
| Schema drift / partial-result flags | Pin each archive schema and actual field mapping; preserve contradictions instead of forcing binary results. |
| Weak connection to drug-target science | Treat B0 as a finite data-feasibility diagnostic. Prioritize harder T6 quality rather than marketing reporting prediction as target validation. |
| B1 program mislinkage and incomplete search recall | Require source-defined candidate coverage, arm/regimen/population review and separate linkage precision/unknown counts before use. |
| Insufficient independent events or qualified training history | Keep fitting/calibration deferred; no automatic extrapolation or late cutoff expansion. |
| New documents, prospective follow-up or independent panel needed later | Name the exact artifact/access/review requirement at that gate. No speculative AACT download request now. |

The original downloader, stopped monitor, raw archives and old adjudications remain
untouched. T2–T5 and H6 remain conditional later work, not dependencies for this audit.

## Planning review and completion status

This reassessment read the retained design, source, chronology, cohort, comparison
and acceptance reports and relevant extractor interfaces. It checked current drive
space and archive-folder presence. It did not rehash multi-GB archives, start a
database, query new trial outcomes, run models or acquire trial documents.

A separate agent performed a read-only methods critique, supporting endpoint-specific
gates, source-defined negatives, finite feasibility work and continued T6 evaluation.
That critique is a planning review, not independent outcome adjudication. Public
documentation checks were restricted to registry/AACT methods: NLM and AACT pages
were readable; the current ClinicalTrials.gov glossary/definition/CSV pages exposed
only application shells, and the attempted AACT limitations URL was inaccessible.
No unseen definitions were treated as verified. The proposed B0 contract is our
explicit design choice, not an official clinical endpoint.

Validation for this documentation change checks local links, retained evidence and
label hashes, changed-file scope and diff formatting. The inherited framework
checkpoint is 658 tests/four hosted jobs; no fresh full-suite result is claimed.
The broader scientific project remains incomplete.

**Immediate next deliverable:** a versioned B0 protocol, exact schema/source manifest
and tested extraction guards, followed by origin-only membership sealing. This plan
alone does not dispatch those operations.
