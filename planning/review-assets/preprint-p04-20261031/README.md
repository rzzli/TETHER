# P04 preparation evidence

P04 is not complete. No actual model generation has occurred at this checkpoint.

The [READY protocol](EXECUTION-PROTOCOL-READY-v1.json) freezes twelve cells across
two exposed real contexts and one controlled missing-input condition. It binds
69 code files, exact environment/model/runtime, separate source and evaluator
seals, common outputs, per-arm budgets and all-cell failure accounting.

- [Source inputs](GENERATION-INPUTS-v1.json) were sealed independently before
  [evaluator references](REFERENCES-v1.json).
- [Independent source fidelity audit](INPUT-REFERENCE-AUDIT-v1.json) checks selected
  original rows, hashes/receipts, both seals and role/scope/missingness boundaries.
- [Targeted tests](TARGETED-TESTS-v1.txt) pass 217 methods, not the full suite.
- [Installed smoke](INSTALLED-SMOKE-v1.json) uses mock clients only; no inference.
- [Input plan v1](DEVELOPMENT-INPUT-PLAN-v1.json), [v2](DEVELOPMENT-INPUT-PLAN-v2.json),
  [v3](DEVELOPMENT-INPUT-PLAN-v3.json), [v4](DEVELOPMENT-INPUT-PLAN-v4.json),
  [metadata failure](PREPARATION-FAILURE-v1.json) and
  [hashing timeout](PREPARATION-TIMEOUT-v1.json) preserve the complete chronology.
- [Rendering preflight](RENDERING-PREFLIGHT-v1.json) measured source-only prompt
  and literal-projection size/format before model calls. It is not a scored study
  cell or an expected-answer input to generation.

The separate [progress assessment](../../Project%20Progress%20Reassessment%202026-10-31%20-%20Reporting%20Pilot%20Preparation.md)
records limitations and next steps. All original-value packets/references/model
outputs stay ignored; public metadata is not an independently validated biological
benchmark. No external expert input or clinical probability is involved.
