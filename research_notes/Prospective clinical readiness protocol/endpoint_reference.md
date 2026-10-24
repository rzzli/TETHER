# Endpoint and reference qualification for prospective clinical readiness

## 1. What exact endpoint can independent agent extraction qualify?

### Takeaway
The defensible near-term reference is **source-linked reported disposition of a prespecified efficacy decision**, for a specified trial, regimen, population and analysis. Blinded agents can author this documentary reference without a mandatory human-expert gate; agreement alone cannot establish treatment benefit, correctness of the underlying trial or target causality. This is a proposed research operationalization, not an FDA qualification or regulatory endorsement.

### Cited Findings
- ICH E9(R1), sections A.3.1–A.3.3, specifies treatment/comparator, population, patient variable, handling of intercurrent events and population summary; treatment discontinuation differs from study withdrawal/missing data. [Official ICH E9(R1)](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- FDA distinguishes all-required co-primary endpoints from a family in which success on any endpoint suffices; the latter needs multiplicity control. Composite and multi-component endpoints are distinct designs. [FDA guidance, III.A–C](https://www.fda.gov/media/162416/download)
- The retained project origin protocol already separates decision polarity, decision occurrence and disclosure, and prohibits absence-of-report failure labels. Its exposed historical membership must not be reused for this prospective design. [Local endpoint protocol](../../planning/protocols/endpoint-origin-feasibility-v0.1.json)
- The original proposal mixes phase advancement T1 with clinical-success H1 language and separately proposes expert preference H5. These remain different claims. [Original proposal](../../planning/Beyond%20the%20Virtual%20Biotech%20Tooling%20Gaps%20and%20Project%20Plan.md)

### Inferences
All items below are **proposed protocol decisions**, grounded in the distinction between estimand and observed report, not claims that a regulator mandates this exact benchmark.

**Contract.** Use `reported_prespecified_efficacy_decision_v1`. Unit: trial identifier × experimental product/regimen × indication/population × origin phase × named primary efficacy objective and designated analysis. Retain target/action/modality/tissue separately; a combination product does not confer success on each target. For the nested clinical estimand, extract the five attributes above, measurement time, estimator, analysis set, null/alternative, directional effect, superiority/non-inferiority margin if relevant, missing-data strategy, multiplicity graph and stopping boundaries. If a source does not name a modern estimand, faithful extraction of explicit equivalent attributes is acceptable; agents must not invent an attribute.

The benchmark estimand is a forecast of a **reported, qualified trial decision**, rather than an estimate of the trial's causal treatment effect. Freeze both a decision-occurrence outcome and its polarity. Do not call a binary score on decision-complete cases the probability of benefit for every origin member.

| State | Proposed definition |
|---|---|
| success | Authentic designated efficacy rule met for the frozen scope, supported by original reported analysis/decision, with rule-compliant multiplicity/interim treatment and decision interval wholly in `(origin,horizon]`. |
| failure | Same qualified definitive rule explicitly not met at its designated terminal analysis in-window. Non-significance is failure of this rule, not proof of no treatment effect. Definitive prespecified futility may qualify only if the frozen endpoint explicitly includes that decision and terminal status is supported. |
| unknown | Missing/unavailable rule or result; unclear scope, timing or authenticity; unresolved contradictions; pending final analysis; inaccessible originals; unsupported prespecification; insufficient evidence of origin risk. Preserve null numeric efficacy label and a reason code. |
| not at risk | Definitive decision for this same objective already occurred by origin, or an origin-defined inapplicable scope (e.g. safety-only/no efficacy objective). Distinguish these reasons. Record in screening denominator; do not create post-origin exclusions. Prior higher phase elsewhere is insufficient. |
| competing event | A documented event prevents the designated decision (e.g. definitive abandonment before analysis for safety or commercial reasons), without qualifying efficacy failure. Record event type/time separately. Trial termination alone does not prove prevention: analysis can still occur. |
| no decision by horizon | Positive documentary evidence that the designated decision had not occurred through horizon, with scope and timing qualified. Occurrence diagnostic zero only; efficacy polarity remains undefined. No-record is unknown. |
| out of window | A qualified decision lies wholly after horizon (or before/equal origin); retain its timing diagnostic, do not silently count as in-window polarity. |

Represent dimensions separately: `origin_risk`, `decision_occurrence`, `decision_polarity`, `competing_event`, `source_qualification`, `temporal_qualification`; avoid a single enum hiding a known polarity with uncertain timing. Patient-level intercurrent events belong to the trial estimand. Program-level competing events belong to the forecast endpoint; these are not interchangeable.

For co-primary objectives, extract the authentic AND/OR/threshold rule; never choose the favorable endpoint. Freeze a named family or aggregate the authentic whole objective. Stage-1 continuation, an interim boundary not crossed, nominal secondary significance, or later subgroup success cannot replace the designated terminal rule. Early success can count when the prespecified design makes that interim decision definitive. Preserve individual analyses and one dependent trial-level decision, avoiding event inflation.

### Gaps
- No studies/outcomes were opened or adjudicated. Therefore no actual prevalence, label yield, power or qualified event count is established here.
- No primary methodological source located in this scope certifies agent agreement as a validated clinical gold standard. Agent extraction is an authorized benchmark design choice whose limitations must be measured.

## 2. What proves authentic prespecification and decision timing?

### Takeaway
Treat document date, authentic rule adoption, analysis/unblinding, clinical observation and public availability as separate evidence fields. A later-public SAP can document genuine prespecification, but cannot automatically prove that its rule existed at prediction origin or become an origin predictor.

### Cited Findings
- ICH E9 5.1 permits a detailed SAP after protocol finalization, recommends finalization before breaking the blind, and formal records of both dates; principal-feature changes require protocol amendment. Sections 4.5 and 5.6 address planned interim decisions and multiplicity. [Official ICH E9](https://database.ich.org/sites/default/files/E9_Guideline.pdf)
- ClinicalTrials.gov's March 2019 protocol definitions identify primary completion as final primary-outcome data collection, including terminated studies, and actual study start as first enrollment. Neither definition identifies analysis or efficacy decision. [Official-government retained definitions, pp. 5–6](https://www.reginfo.gov/public/do/DownloadDocument?objectID=97967501)
- NLM describes separate submission/posting/QC dates and submission cycles before public posting. This is an archived 2017 description, useful for separating concepts rather than asserting current posting policy. [NLM technical bulletin](https://www.nlm.nih.gov/pubs/techbull/nd17/nd17_clinicaltrials_enhanced.html)
- Existing project rules already require exact source version availability by ascertainment and preserve access failures separately from absent decisions. [Local source-readiness protocol](../../planning/protocols/source-readiness-feasibility-v0.1.json)

### Inferences
**Authenticity proof proposal.** Preserve original issuer/host, trial-to-sponsor-protocol bridge, title, version, signed/approved dates if present, amendment table, exact section/page and retained bytes/hash in any later authorized acquisition. Record `rule_existed_by_origin`, `rule_prespecified_before_relevant_unblinding_or_analysis`, and `exact_version_public_by_ascertainment` independently. A cover date, current registry link, filesystem timestamp or hash proves neither historical existence nor historical public access. An original issuer's dated amendment history or explicit report of SAP finalization/unblinding may support an interval; classify the evidentiary basis and conflicts.

For the future-origin study, require the **material success rule** to be available and fixed before prediction freeze. A detailed later SAP can clarify previously fixed methods if consistent; material post-origin changes (population, endpoint, threshold, multiplicity or designated analysis) cannot silently redefine the forecast. Freeze handling now: retain original-rule assessment if reported, otherwise classify the original endpoint as unknown/changed and report an amended-rule secondary diagnostic. This is deliberately stronger than claiming all clinically legitimate pre-unblinding amendments must have existed at origin. Alternatively, a future protocol may explicitly forecast the eventual authentic amended rule, but that is a different estimand requiring a prespecified amendment algorithm and disclosure of its moving target.

**Timing proposal.** Store intervals for clinical observations, data cutoff, database lock, unblinding, designated analysis execution, formal decision and each public disclosure/version. Name the event whose time defines occurrence; recommend the formal designated efficacy decision, not an interchangeable mixture of analysis and press release. When decision time is unavailable but formal analysis time is known, retain the distinction; only use it as a proxy if the protocol explicitly freezes that proxy and its claim.

Evidence that a completed decision was disclosed on day D gives an upper bound at D, not an exact decision date. A relevant data cutoff may provide a lower bound for an analysis using those data, but only with an explicit source link; planned completion is no such proof. Use interval intersection only for statements known to refer to the same event. Contradictory nonoverlapping bounds remain held. In-window requires the whole supported interval inside `(origin,horizon]`; month-only dates crossing a boundary or unknown time zones remain uncertain. Choose occurrence and ascertainment horizons separately before activation; no evidence found here justifies a universal reporting allowance. Later-public information stays in a labeled late-ascertainment sensitivity record, not the primary label by silent window extension.

### Gaps
- Current ClinicalTrials.gov protocol/results/glossary policy URLs returned only an 11-line UI shell through web extraction, despite indexed snippets. Results-document upload date semantics could not be verified in the current rendered official source. An OMB-report mirror was discovered but was not relied on as current policy. [Current results definitions, access limited](https://clinicaltrials.gov/policy/results-definitions#DocumentUpload); [current protocol definitions, access limited](https://clinicaltrials.gov/policy/protocol-definitions); [current glossary, access limited](https://clinicaltrials.gov/study-basics/glossary).
- Do not infer a missing version, authenticity date, decision date or time zone from these methodological sources; later study-specific qualification must establish it.

## 3. What agent reference protocol and next action are admissible?

### Takeaway
Proceed with a versioned **non-dispatch reference contract and empty extraction/reconciliation schema** now. Later, two independently sealed extraction agents plus a separate reconciliation agent can qualify documentary facts without human experts, conditional on source evidence and strict unknown rules.

### Cited Findings
- The prospective planning document permits agent implementation while distinguishing source review from independent therapeutic truth; it authorizes protocol preparation without cohort activation. [Remaining gates/design](../../planning/Remaining%20Scientific%20Gates%20and%20Prospective%20Design%202026-10-23.md)
- ICH distinguishes precise treatment-effect questions from estimates and their assumptions, and calls for sensitivity analysis aligned to the estimand. This supports keeping source disposition and substantive efficacy inference distinct. [ICH E9(R1), A.1–A.3](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)

### Inferences
**Concrete proposed protocol:**

1. Freeze the endpoint dictionary, mandatory fields, material-amendment policy, source hierarchy, contradiction rules and bounded discovery routes before any new membership or follow-up. Keep the old failed discovery calibration and old cohorts inactive.
2. Prepare source-only packets under later separate activation. Neither extractors nor reconciler sees predictions, scores, comparator identity or dossiers. Reference agents may see the trial result because extracting that result is their task; predictor agents must not. Freeze model/version/prompts and disclose prior/source/model exposure.
3. Run two isolated agents with identical allowed evidence and schema; each emits exact supported facts, locators, evidence strength, intervals, unsupported fields, contradictions and final proposed state. Seal both outputs before mutual visibility. Agent independence means procedural isolation from predictions and each other's current judgments, not independent training histories or biological evidence.
4. Reconciler checks every mandatory field against cited originals, not majority vote; cannot invent a rule, upgrade weak date evidence or resolve conflict merely by preference. A second source repeating the same sponsor statement is not independent corroboration. Deterministic checks enforce scope joins, date logic and executable Boolean success rules where sufficient reported numbers permit them; no reconstruction from rounded p-values at a boundary.
5. Material inconsistency triggers a bounded predefined source clarification route only if later acquisition is authorized; unresolved cases remain unknown. Preserve both extractions, reconciliation rationale and original receipts. No human review prerequisite is added. Missing records remain a scientific limitation regardless of reviewer type.
6. Report initial exact field agreement and disagreements, after-reconciliation yield, and unknown/held counts over every frame member. Agreement measures reproducibility, not accuracy. Blind synthetic specification fixtures can test deterministic handling of AND/OR rules, interim continuation, conflicts and intervals; they cannot establish clinical validity or discovery sensitivity in a representative cohort.
7. Pass documentary-reference qualification for an individual event only when scope, authentic rule, prespecification, designated analysis/polarity, origin risk, timing and applicable availability all have inspectable evidence and no unresolved material contradiction. Population readiness additionally requires the separately frozen source-frame/coverage and sample-size rules; no arbitrary numeric rate is derived by this note.

**Qualified claims:** source-supported decision extraction; reproducible reference construction; forecasting reported prespecified decision on the declared source-defined population, if later prospective validation and missingness/dependency analyses support it.

Preserve the original H1 clinical-efficacy objective and every retained historical endpoint contract unchanged. The documentary endpoint is a separately named operationalization for a new prospective study, not retrospective replacement of advancement, dosing or efficacy labels. **Ready for feasibility** means the schema and bounded source-only origin audit can be proposed; **ready for prediction activation** additionally means that audit passed its prospectively frozen criteria, future origin and membership are sealed, material rules and predictors qualify, independent event/precision requirements are satisfied, reference isolation is secured, and the complete analysis/prediction recipe is frozen. Completion of this note implies only the former protocol-design deliverable, with no acquisition or prediction allowance activated.

**Claims requiring stronger independent evidence:** true clinical benefit or comparative effectiveness beyond what the trial supports; mechanistic target causality; efficacy of each component of a multi-target/combo product; population-generalizable performance under selective reporting; expert preference under original H5; original T6 therapeutic claim-error accuracy. Stronger evidence may be regulatory scientific assessment, adequate controlled trial evidence, independent replication, or independently qualified question-specific reference—not necessarily human participation. Original expert-preference H5 cannot be reported as fulfilled by agent preference without explicit hypothesis amendment. A prospective clinical decision forecast can still be a scientifically useful clinical-outcome benchmark; it should not be dismissed as merely engineering because agents authored its evidence records.

### Gaps
- This note does not activate extraction, monitoring, study search, model invocation, download, fitting or scoring. Safe immediate deliverable: the contract/schema plus a source-access repair specification for methodological documentation, followed by a separately bounded origin-only readiness design. No study outcomes/documents were fetched; search results incidentally surfaced unrelated study PDFs, which were not opened or used.
- Official methodological texts do not supply a numeric reference-error tolerance or reporting allowance for this benchmark. Those remain explicit design choices tied to its intended inference, not facts to invent.
