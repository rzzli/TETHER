# Project execution checklist

Run tasks in order. Mark complete only after the task's validation passes. Stop and
record a blocker if a task cannot be completed after reasonable attempts. Existing
development artifacts are evidence, not independent scientific validation.

- [x] **Task 1 — Build registry-scale cohorts and audit transition labels.** Verify
  the sealed v0.4 milestone, freeze the condition/scope sensitivity rules, and finish
  the prior-risk and regimen/population audit. Validate source lineage and regressions.
- [x] **Task 2 — Measure sample size, statistical power and clinical feasibility.**
  Use measured dependencies and explicit label-error/effect-size assumptions; retain
  simulations and a proceed/revise decision without claiming observed model accuracy.
- [x] **Task 3 — Finalize model chronology, evaluation windows and preregistration.**
  Verify model versions/cutoffs and matching historical origin/endpoint data; complete
  a defensible frozen evaluation protocol before treating a set as locked.
- [ ] **Task 4 — Build bounded retrieval and the model-backed specialist.** Preserve
  the default budget and $0 provider-spending boundary; validate offline/replay behavior.
- [ ] **Task 5 — If feasible, validate genetics features and train/calibrate scoring.**
  Scientific derivations, leakage-safe cohorts and calibration data must qualify first.
- [ ] **Task 6 — Compare Virtual Biotech, simple baselines and ablations.** Verify
  compatible data/model chronology and comparable budgets and retain evaluation outputs.
- [ ] **Task 7 — Run independent T6 quality and locked clinical evaluations.**
  Independent review and an actually locked, temporally eligible cohort are required.
- [ ] **Task 8 — Conditionally extend T2â€“T5 and H6.** Proceed only after their
  prespecified feasibility and data gates pass; document any unmet condition explicitly.

## Current execution

Task 1 passed source/scope validation and the full 194-test suite. Its evidence is
in `planning/Ordered Execution Progress 2026-10-17.md` and
`planning/review-assets/ordered-execution-20261017/`.
Task 2 passed corrected small-sample null validation, all 120 scenario checks and
201 full-suite tests. Its clinical feasibility decision is revise before training;
these are conditional simulations, not clinical performance or validated labels.
Task 3 passed 208 full-suite tests and proof/hash validation. A local development
protocol and gated 2025-2026 clinical design are frozen; no public registration or
locked clinical set is claimed. Task 4 is active: bounded retrieval and local inference.

## Validation and blockers

Tasks 1-3 are complete within their documented scope after successful validation. No blocker has yet been declared
for this ordered execution. Original proposals and sealed outputs remain
unchanged; no paid model calls or public preregistration submission is assumed.
