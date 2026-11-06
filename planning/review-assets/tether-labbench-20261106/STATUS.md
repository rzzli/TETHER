# BG04 checkpoint

6 November 2026 UTC. **In progress; no benchmark candidate generated or scored.**
BG01–BG03 are complete in their declared scopes (SciFact completion commit `5dae314`).

The original public199 LitQA2 family was selected before candidate performance.
Pinned original acquisition is complete: 17 files / 719,061 bytes, with the original
GitHub JSONL containing 199 unique IDs. The source/format projection still needs
qualification. A nonbenchmark Europe PMC query and full-text rights probe succeeded;
this does not establish coverage of benchmark questions.

| Gate | Status |
|---|---|
| Family choice and source/method review | All199 LitQA2 selected; three feasibility notes retained |
| Pinned originals and endpoint probe | Acquired; receipt `620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd` |
| Projection/reference isolation and retrieval | Implementation and fictional tests in progress |
| Native contract, scorer and TETHER policy adapter | Implementation and fictional tests in progress |
| New MCQ transport using existing local weights/runtime | Implementation and fictional tests in progress; no model startup |
| Integrated fictional qualification and final executable freeze | Pending |
| Actual question-only retrieval, exactly-once generation, paired scoring | Not started |
| Independent reconstruction/report/closure | Pending |

Current design: [protocol](<../../TETHER LitQA2 Evaluation Protocol 2026-11-06.md>).
Code owners are scoped to separate modules under `experiments/labbench/`; maintained
core and completed SciFact code/results remain unchanged. An unavailable source
stays in the all199 denominator. Source alignment is distinct from entailment.

Existing local weights are present (three shards, 8,988,110,496 bytes); fresh hashes,
runtime qualification and fictional inference are still required. No external
human input, paid provider or new model acquisition is planned. Historical model
cells, download worker and stopped monitor remain untouched.

Next: complete and integrate fictional tests, measure local runtime feasibility,
freeze exact budgets/code/configuration, then acquire sources and execute. Do not
launch benchmark retrieval or candidates from this draft alone.
