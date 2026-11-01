# Project progress reassessment after removing external expert inputs

31 October 2026, America/Los_Angeles. **The owner has retired external expert responses and review participation as project inputs and dependencies.** The prior human-response blocker no longer applies. Planning has moved to the [AI only evaluation plan](AI%20Only%20Evaluation%20Plan%202026-10-31.md) and its [scope decision](decisions/2026-10-31-no-external-expert-input.md). This is a change in the evaluation protocol and claim, not successful completion of the previous human study.

## Completed in this revision

- Replaced recruitment, source-return, GE confirmation, candidate-follow-up, human-time and panel/adjudication dependencies with automated source checks, disclosed AI references and explicit uncertainty.
- Restated the active dossier hypothesis as H5-A source-reporting fidelity/coverage. Original H5 expert preference remains historically defined and untested; original clinical and H6 hypotheses remain conditional.
- Set an archive-only policy for bespoke responses and all response-derived artifacts. New references, generation, evaluation, tuning and source/case/arm selection exclude them. The immediate implementation task must enforce this through manifests and tests; a planning decision alone is not a technical isolation proof.
- Preserved the previous TODO exactly at [the pre-amendment archive](../docs/history/TODO-before-ai-only-replan-20261031.md); its SHA-256 is `09bfff2bcbbf7b9b8fcdb6710ce2eca3cecfe1784379522e724b5756e4ed359d`. Previous plan/status/decision versions remain recoverable from Git checkpoint `0b61b85`.
- Reconciled current navigation, data policy, TODO and memory with the new plan. Marked prior human handoffs as superseded. No new form or response is requested.

This revision does not implement or execute the new evaluator. Existing 0.3.11/default-v2 application acceptances and the retained 1,774-test result remain unchanged. Full application tests are not rerun for documentation changes. Review of existing code confirms AI-source reference support but a new small adapter is required for the ten genetics items; existing Q1 and top-one utilities do not implement that schema.

## Complete recovery status

| Item | Current disposition |
|---|---|
| R01 | Accepted scope/governance, prospectively amended to no external expert inputs |
| R02 | Accepted checkpoint/restoration inventory; timestamped local commits continue |
| R03 | Accepted scoped archive/relocation compatibility; preserve all legacy verifier semantics |
| R04 | Accepted reproduced framework corrections |
| R05 | Diagnostic preparation accepted; stronger-model condition unqualified, not silently supplied by agent fanout |
| R06 | Accepted reusable infrastructure slice |
| R07 | Technical NEGATIVE, six complete responses/zero contract passes; human gate retired; separately scoped retrospective AI assessment pending A03 |
| R08 | Source/exposure preparation retained; fresh-case/source-slot feasibility pending A04, without expert approval requirement |
| R09 | Recorded/preparation mechanics retained; minimal evaluator and scientific consumer pending A02/A05/A06; optional native expansion deferred |
| R10 | Human pilot retired; new AI-only development pilot pending A06 |
| R11 | Amended H5-A sizing, analysis and freeze pending A07 |
| R12 | Locked automated comparison pending A08; original expert-preference H5 untested |
| R13 | Conditional clinical source/label/negative/censoring feasibility; ambiguous endpoints excluded/deferred rather than sent for expert approval |
| R14 | Conditional genetics/LD/assay/ancestry/overlap and scorer validation; no numerical feature or probability promotion |
| R15 | Original clinical comparisons/ablations conditional on actual qualified information, chronology and power |
| R16 | Individual T2–T5/H6/release requirements retained, with source-reproducible references and no expert-response prerequisite |
| HR1 | Recruitment retired from active scope, not completed |
| HR2 | Human orientation/workload endpoint retired; existing returns archived |
| HR3 | Human source-reference/candidate-rating requirement retired |
| HR4 | Human final panel/adjudicator requirement retired |

Ten canonical contemporary development dossiers and source audits remain retained. The interpretation slice's 65 missing inputs, clinical route's 36 unqualified endpoint labels, 17/32 observable states and 0/12 joint-ready cases refer to different denominators and remain unresolved by this amendment. Numerical prediction features remain empty and clinical probabilities null.

The original native recognition FAILED and whole-verification INCOMPLETE_TIMEOUT remain unchanged. Source5/C79 retain scoped component acceptance, not full native qualification. No old call is repeated and no old response is repaired. Existing expert-response originals and provenance records remain byte-preserved; their former role as potential evaluation inputs is now retired by policy.

## Critical next major step

**A02: implement and test the smallest evaluator-side source-reference contract for the existing ten-item genetics question.** It binds source cards, request, question/hypothesis, original passages, item/option IDs, reviewer/execution provenance, uncertainty and seals. It must retain partial and unresolved answers and prevent direct or derived response leakage. Historical `human_scientific_review=pending` strings and verifiers are not edited to make this work.

Then A03 can use two fresh source-only AI contexts and a third reconciler, followed by a separately masked retrospective audit of unchanged R07 candidate views. These agents must not inherit this conversation/memory or human-response-aware analysis. Old candidates predate the new reference, so the analysis is exposed and retrospective regardless of source-only annotator order. This gives a bounded content/feasibility account without another model-generation attempt or human request.

The later A04–A08 path needs eligible new source/question units, objective fact slots, tested evaluator controls and a genuinely feasible model route. Keep deterministic metrics primary and AI semantic ratings secondary; shared-model agents do not establish independent truth. If only simple baselines or a negative model-feasibility result can be supported, report that result honestly rather than restarting the optional native stack. A03 is development closeout, not proof of the original expert-usefulness claim.

## Remaining risks and operational needs

- **Correlated AI errors:** isolate contexts and audit against sources/controls; report per-judge outcomes and unresolved disagreement. Different agent names are not independent evidence.
- **Reference contamination:** enforce source-only allowlists and evaluator lineage before future runs; preserve unknown exposure and exclude affected locked cases. A rewrite of the rubric does not make old cases unseen.
- **Metric gaming:** require nontrivial fact coverage, retain insufficient-evidence strata and count failed cells. Exact quotes alone do not prove entailment or useful interpretation.
- **Missing science inputs:** inspect dataset-level coverage and dates. Source omission is not biological absence; missing LD, outcome ascertainment or individual-level H6 data cannot be synthesized by reviewers or agents.
- **Model/resource limits:** the approved stronger condition is still unqualified and prior simulation is not actual inference fit. New runs need their own bounded protocol; platform annotators are not automatically experimental generator arms.
- **Costs:** retain $0 additional provider spending; disclose unknown platform-agent usage/cost and evaluation overhead. Do not claim measured human-time or total-cost savings.

No new dataset/model download, paid API, protected clinical-outcome read, runtime change, download-worker change or stopped-monitor restart is part of this planning revision. Future owner involvement is limited to a named file, access, permission or resource issue when actually encountered; no further external expert input is planned.
