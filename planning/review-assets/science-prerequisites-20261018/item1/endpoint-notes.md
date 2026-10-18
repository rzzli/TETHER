# Proposed scientific endpoint and reference contract

Review date: 2026-10-18. Scope: Item 1 design only; no endpoint joins, new cohort extraction, original protocol edits or labels assigned.

## Scientific question and unit

Preserve the original H1/H2 clinical-success questions in `planning/Beyond the Virtual Biotech Tooling Gaps and Project Plan.md`. Registry advancement is a separately named operational endpoint. It cannot satisfy H1 by relabeling a later study start as success. Original H3–H6 meanings remain unchanged. One row is a versioned **experimental product/regimen × indication/population × origin phase** program. Target IDs annotate the program; a multi-target drug does not establish target-specific efficacy. Freeze target/action/modality hypotheses and aggregation rules separately before target-level analysis.

The proposed clinical window remains (2025-01-01, 2026-01-01], with origin eligibility at the analytic origin, not at endpoint. This proposal does not activate that window. ClinicalTrials.gov study-start dates refer to recruitment estimates or actual first participant enrollment; actual enrollment is not necessarily experimental-arm dosing. Completion and termination are conduct statuses, not efficacy classifications. [Official registration definitions](https://clinicaltrials.gov/policy/protocol-definitions?trk=article-ssr-frontend-pulse_little-text-block)

## Separate endpoint IDs

1. **registry_next_phase_enrollment_v1:** first distinct, eligible next numerical phase trial with the same qualified experimental product/regimen and disease/population scope; ACTUAL start interval wholly within the occurrence window. This predicts a registry-observable development milestone. Mixed/seamless phases, altered drug combinations, extensions, regional bridging and prior higher-phase activity require explicit adjudication; they never automatically become incident events.
2. **experimental_arm_first_dosing_v1:** separately documented first dosing of the experimental regimen in a qualifying next-phase arm. A study-level enrollment date cannot substitute. Use exact dates or bounded event intervals, retaining uncertainty.
3. **clinical_efficacy_success_v1:** a prespecified clinical efficacy objective of a qualified program/arm is met under the protocol/statistical-analysis decision rule, appropriate population, analysis set and multiplicity control. Capture magnitude, uncertainty and safety assessment separately. A press release saying “positive,” nominal secondary-endpoint significance, phase-one safety/PK completion or trial initiation is insufficient. A positive efficacy result is not automatically clinical benefit, acceptable benefit–risk, or regulatory approval. Define any benefit–risk composite or regulatory endpoint in a separate amendment rather than adding it after results are seen.

The third definition is a proposed operationalization of the original broad clinical-success wording. It requires a versioned amendment and prespecified phase/endpoint eligibility before labels are used. Phase-one programs lacking an eligible efficacy objective are inapplicable to this endpoint, not efficacy failures. ICH E9(R1) supports explicitly defining the population, treatment, variable and handling of intercurrent events; applying it to this program-level prediction benchmark is a design adaptation, not a claim that the benchmark is a randomized trial. [Final ICH E9(R1)](https://www.ema.europa.eu/en/documents/scientific-guideline/ich-e9-r1-addendum-estimands-and-sensitivity-analysis-clinical-trials-guideline-statistical-principles-clinical-trials-step-5_en.pdf)

## Label states and decision rules

| State | Required evidence and interpretation |
|---|---|
| positive | Qualified endpoint event, qualifying incident interval, program/arm scope match and retained primary evidence. A result event and its first public disclosure are separate dates. |
| negative | For efficacy: reviewed final eligible analysis explicitly fails its prespecified efficacy decision rule. This is failure of that objective, not proof of no drug effect. For registry enrollment only: a completed prespecified registry ascertainment search finds no qualifying record through the mature ascertainment cutoff. Label it `no_qualifying_record`, not biological failure. |
| censored | The chosen event-observation process is qualified only through a documented date before the occurrence endpoint. Retain reason and evidence; never assign the administrative endpoint as each program's last-known status without support. Survival analysis requires justified censoring assumptions and sensitivity analysis. |
| unresolved | Missing/inaccessible evidence, ambiguous linkage, conflicting dates/results, inadequate follow-up or date interval straddling a boundary. No default binary value or scorer-training admission. |
| ineligible | Wrong origin phase/activity/role, prior qualifying advancement at origin, scope mismatch, no eligible efficacy objective or another prespecified exclusion. Retain excluded rows and reason. |
| competing_event | Confirmed program discontinuation/death of sponsor/administrative withdrawal or other event that prevents the target milestone, when defined as a competing event in the frozen estimand. Record biological and nonbiological reasons separately; do not auto-convert to an efficacy negative or assume noninformative censoring. |

For positive and negative labels, `binary_value` is endpoint-specific. For all other states it is null. Missing documents are unresolved; no posted results is not a negative. Withdrawn means no enrollment in that trial, not failure of efficacy. Program discontinuation for toxicity is important safety evidence but is not failure of the prespecified efficacy objective unless an explicitly frozen composite says so. A program may have multiple events and separate efficacy/safety/advancement states; later discontinuation does not erase a correctly observed earlier advancement.

## Time and public availability

Keep occurrence interval, result data-cutoff/analysis date, primary completion date, first public disclosure, registry version-posting interval, snapshot date, dump creation time, source retrieval time and adjudication time distinct. Partial dates stay intervals; unknown timezones stay unknown. A first-post date identifies the initial study record, not when a later changed field first appeared; last-update dates alone do not establish a field's initial public availability. [Official API field mapping](https://clinicaltrials.gov/data-about-studies/csv-download)

Use occurrence window `(origin, endpoint]` and a separate ascertainment cutoff. The suggested 90-calendar-day reporting allowance is a planning assumption to freeze before endpoint inspection, not an empirically established completeness guarantee. For a 2026-01-01 endpoint it reaches **2026-04-01**. An event occurring after the endpoint never becomes eligible because it was disclosed during the allowance. A post-origin report may adjudicate the actual event but cannot enter predictors. Report event-dated and public-observable results separately when events are disclosed after endpoint. If only January 2026 data are available, do not assert that the reporting allowance was observed; use an explicitly limited ascertainment analysis or retain a file gap.

## Program linkage and adjudication

Qualify product identity (molecule/salt/formulation where consequential), regimen partners and doses, experimental versus comparator/background/rescue roles, route, disease/subtype, biomarker, stage/severity, prior therapy/line, age and geography. Record each dimension as matched, mismatch, unknown or not applicable with evidence. Cell/ontology aliases and study-wide text are discovery aids, not program equivalence. Same disease parent or same drug name alone is insufficient. Master protocols need arm/substudy activation and enrollment evidence; shared control enrollment cannot establish experimental-arm initiation.

Adjudication retains independent draft assessments, cited source passages/locators, exclusions, conflicts, rationale, uncertainty and final resolution. Source quality prefers full primary results and protocol/SAP; registry results and regulator documents can qualify, while sponsor disclosures are explicitly attributed and may provide timing leads. Multiple websites repeating one sponsor release are one evidence source. A protocol/SAP unavailable for a decisive efficacy interpretation leaves that interpretation unresolved rather than guessed.

Agents can carry out evidence searches and separately drafted specialist/critic/resolver reviews as authorized. Record their model, prompts, exposure and shared sources. Distinct agent names or a unanimous vote do **not** establish external independence or biological truth. Distinguish `operationally_qualified_ai_assisted` (source/procedure rules passed), `independently_adjudicated_reference` (genuinely independent qualified review), and `externally_validated_science` (independent empirical validation suited to the claim). The first allows transparent development analyses; it cannot silently satisfy original H5 blinded expert preference or locked clinical truth requirements.

## Findings in current implementation

- `registry_cohort.py` preserves ambiguous transitions, ACTUAL dates, posting checks and no-recorded status; this supports candidate generation, not qualified negatives.
- `registry_scope.py` explicitly marks eligibility, regimen/population equivalence and clinical training labels unresolved. Its OT25.09 mapping is evaluator-only for the 2023 cohort; it cannot qualify 2025 historical predictors.
- `program_outcomes.py` deliberately forbids development clinical labels/censoring and hard-codes the old 2023–2025 window in `validate_bundle`. Introduce a new versioned endpoint validator for this proposal; do not relax old validators or rewrite sealed bundles. Its incident check requires a within-window report, which is stricter than the proposed separate occurrence/ascertainment policy and must not be silently reused.
- Retained power assessment counted 4,419 programs but only 19 positive proxy components in the base grouping, six with target/sponsor grouping; no independently qualified labels exist. These numbers must not be promoted to the new window or to clinical-success counts.
- `evaluation-v0.3.json` already separates endpoint tiers and null labels, but original model `collection_status` and runtime gate values are frozen stale checkpoints. Current readiness must reference later runtime proofs, not overwrite that archived protocol.

## Item 1 acceptance

Every future reference row must name its endpoint/estimand, program and source scope, occurrence versus availability dates, label-state rationale, qualification level and admitted use. No actual outcomes are assigned by this document. The accompanying `endpoint-fields.json` defines proposed required field paths and conditional rules; it is a design contract, not a runtime-admitted dataset or JSON Schema.
