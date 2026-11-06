# TETHER LitQA2 evaluation protocol

Status: implementation and qualification in progress. Family and intended cohort selected before candidate performance on 6 November 2026 UTC; no benchmark candidate has been generated or scored. Final executable configuration and code hashes will be frozen before benchmark retrieval and model dispatch. This is BG04 of the [active execution plan](<TETHER Benchmark Execution Plan 2026-11-02.md>).

## Purpose and selected population

Evaluate the original public **199-item LitQA2 family**, using question-only public literature retrieval, a local answer-producing model and native multiple-choice scoring. Produce each candidate once and compare its raw result with the same bytes under the declared TETHER native-task checks. This tests task utility, preservation/rejection of useful answers, operational reliability and cost. It does not establish clinical efficacy or faithful reasoning merely from matching an answer key.

LitQA2 was selected for its literature-evidence fit and a uniform Europe PMC open-access retrieval route. DbQA is not categorically inaccessible: exact MSigDB 2023.2 files have a public distribution route. Full-family DbQA source/version qualification is heterogeneous and remains a separate option. Selection does not depend on candidate scores or gold-passage availability.

The public set is development/exposed material. A dataset split named `train` does not authorize training on these answers. No model training or threshold tuning uses this set. The historical 2024 LAB-Bench model experiments were tool-free; this is a tool-assisted native public-question evaluation with an explicitly bounded source universe. It is not an exact reproduction of those model conditions or a private leaderboard test.

## Pinned originals and rights

- Hugging Face `futurehouse/lab-bench` revision `5c77cec648430f30611808808861eb86f81d5eaa`; original LitQA2 Parquet SHA-256 `3e578fdaaa4728a77e884954dbf85ae0e3899791631a3be0838313b3e2334114`.
- Original LAB-Bench code/data repository commit `998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`.
- Acquisition: `data/raw/labbench_public/20261106-attempt01`; receipt SHA-256 `620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd`.
- Dataset terms: CC-BY-SA-4.0. Code and retrieved article terms are reviewed separately. No claim that dataset licensing grants redistribution rights for every cited paper.
- Raw originals and evaluator answers stay ignored. Track sanitized receipts, code pins and reports. Use new output directories and preserve every failed attempt.

The original Parquet and repository JSONL must be reconciled for IDs and native content before projection. Any unexplained difference is a preparation blocker, not permission to choose whichever version performs better. No automatic substitution with LABBench2.

## Reference isolation and native contract

Trusted preparation projects only `id`, `question` and labelled `choices` into the answering view. Shuffle all substantive options and the visible insufficient-information option using a fixed deterministic preparation rule. Correct-answer identity, original `ideal`/`distractors` field names, original-order mapping, key passages, per-question source URLs and other reference hints stay evaluator-only. Do not expose a seed/permutation map in the prompt that reconstructs the original answer position.

The answerer receives the projected task and eligible retrieved passage views, not the full preparation manifest or raw dataset. Retrieval accepts the question string alone. Source URLs obtained through that search are legitimate inputs; reference-only links are not search seeds. A corpus made from annotated gold papers would be a privileged derivative and is excluded from this main evaluation.

Candidate output is a strict object selecting an offered `answer_index` and offered `evidence_ids`. The insufficient-information choice is a valid native answer; it is not a timeout or missing output. The exact output grammar, task cardinalities, passage bounds and malformed-response handling are qualified with fictional cases. An integer selecting an option must not be confused with a Boolean. Unknown fields and out-of-range/duplicate evidence identifiers fail validation.

Substantive answers require a nonempty source selection for admission under this study's declared source-backed-answer policy. An empty-source answer can still be scored raw, but it cannot become a provenance-qualified scientific claim. Insufficient-information outputs may select no evidence. Neither decision establishes entailment.

## Bounded source acquisition

Before any benchmark request, freeze the exact deterministic question-to-query algorithm. Initial implementation limits: at most two query variants, ten metadata hits per query, and three distinct eligible full-text articles per question. Retain rank order and every attempted request, including HTTP failures, empty results, unsupported licenses, oversized bodies and parsing failures. Missing inputs remain on the all-199 denominator.

Use the Europe PMC official metadata and full-text routes. A successful nonbenchmark endpoint probe proves availability of that endpoint only. Accept full-text bodies with explicitly qualified CC-BY or CC0 permissions; unresolved or other licenses are unavailable under this study policy. Pin original response bytes, URLs, UTC retrieval timestamps, headers needed for provenance, article identities and license evidence. Strip credentials if any unexpected URL contains them; do not store tokens.

Use bounded HTTP timeouts and response sizes; no redirects to unapproved origins, no account login and no paid access. Validate XML safely and retain extraction/version/locator metadata. Select passages deterministically from parsed full text using only the question. Preserve truncation and missing-section coverage. Never label no result or inaccessible full text as absence of scientific evidence.

Every passage links to its exact source body and extraction method. A search response, parsed article and selected passage are separate lineage products. Contemporary download availability is not historical publication availability. Record publication dates separately and reject explicitly future-dated articles relative to the acquisition cutoff.

## Fixed local answer producer

Use the already acquired Qwen2.5-14B-Instruct Q4_K_M weights at revision `b466e1f8c07172155743e8e1307507d8a4f91fbd`, subject to fresh verification of all three shard hashes and runtime files. Their existence does not qualify model execution. This new MCQ experiment does not retry or relabel any closed historical T6/model cell.

The new adapter uses a launcher-owned loopback-only server, no external provider and no historical launcher that writes old pointers. Proposed bounds to qualify before final freeze: temperature 0, seed 20261106, 16,384-token context, at most 256 generated tokens and one generation attempt per question. Exact tokenization reserves output headroom. Overlong input is an explicit failure rather than silent source truncation. Tokenizer calls and model load/startup costs are measured separately from generation.

Before actual questions, use fictional content to verify exact JSON grammar behavior, token accounting, accepted finish reasons, timeout and output limits, server ownership and cleanup. Retain raw requests/responses, measured versus estimated usage, process/runtime pins and failures. Do not repair malformed answers with a second model or guess which option the model intended. No generation is automatically repeated after an uncertain call.

Final per-call, startup, stage-time, source-byte and memory bounds depend on this fictional qualification and must be frozen before actual execution. These values may change during implementation; any later change after seeing real candidates requires an explicit amendment and a new attempt with preserved history.

## Paired policy comparison and accounting

Archive the schedule and reserve output before dispatch. Retain hash-chained execution events with requested/reserved/measured usage and terminal disposition. Apply raw reporting and the native TETHER checks to identical candidate and source bytes; no arm receives different retrieval, models, retries or answer hints.

The native adapter reuses TETHER's eligibility, lineage, stable source capture and request-binding primitives where applicable. Its declared policy covers this task, not automatic equivalence to the entire BG02 or therapeutic schema-2 contract. Tests must exercise evaluator-only ancestry, later information, incorrect source hashes, substituted requests, ambiguous/duplicate identifiers, immutable captured evidence and failure accounting.

Keep all 199 tasks in the final schedule, including any not dispatched after a fatal stage failure. Report input unavailable, no-source, native unsure, malformed output, timeout, interruption, policy rejection and unattempted separately. A partial run remains partial. An all-abstaining or no-generation run cannot by itself satisfy the active stage's requirement for actual task-capable answering.

## Native scoring and source diagnostics

Open references only after candidate production is sealed. Independently reconstruct the correct-answer and insufficient-information indices from the pinned originals and frozen shuffle, then compare with the preparation reference map. Qualify scoring against original task semantics using fictional controls.

Report:

- Accuracy: correct/all scheduled; answer precision: correct/attempted; coverage: attempted/all scheduled. Explain original scorer conventions separately from operational failures, including undefined zero-attempt precision.
- Correct-and-admitted/all scheduled; correct-but-rejected; incorrect-but-admitted; valid unsure and every operational disposition.
- Source alignment: hit/recall against normalized annotated DOI/PMID/PMCID sets, with unresolved IDs explicit. This is annotation-relative retrieval coverage, not exhaustive literature recall.
- Availability and extraction completeness; selected passage/source hash and locator integrity. Gold key-passage lexical recovery, if implemented, is evidence-localization only, not semantic support.
- Runtime, CPU, peak memory where measured, logical bytes, model/tokenizer requests, measured/estimated token usage, failures and zero provider spend. Separate shared retrieval/generation/startup from marginal checking and reconstruction.

The native task unit is the question. Annotated shared-paper/version and duplicate-question components describe dependence after source reconciliation. Do not turn repeated calls, choices or source passages into independent questions. No nominal power guarantee follows from 199 questions. Chance and always-unsure controls must be labelled as executed controls or analytical expectations, rather than implying nonexistent model runs.

Do not score semantic entailment by exact citation matching, answer correctness or a model's confidence. Without a separately qualified semantic scorer, semantic source support remains unevaluated. Keep any expected gold-source list out of retrieval and generation.

## Ordered completion gates

1. Receipt/hash/schema/license qualification and projection isolation; exact public199 schedule.
2. Fictional native-contract, scorer, retrieval, model-transport and policy tests, including failures and output collisions.
3. Fresh local weight/runtime qualification and fictional bounded model smoke; measured capacity; final protocol/configuration/code freeze.
4. Actual question-only source acquisition and retained coverage, followed by exactly-once local candidate production into a fresh output.
5. Paired admission, native scoring and independent reconstruction against original rows and pinned outputs; no hidden denominator losses.
6. Results and limitations report, source/resource audit, documentation/memory update and timestamped local commit.

BG04 remains incomplete until these gates pass. BG05 Inspect follows; it does not start merely because acquisition succeeds. Further PaperQA2/OpenScholar-style semantic interventions are useful follow-on proposals, not additions to this frozen baseline.

Source reviews: [data feasibility](review-assets/tether-labbench-20261106/data-feasibility.md), [policy feasibility](review-assets/tether-labbench-20261106/policy-feasibility.md), [method feasibility](review-assets/tether-labbench-20261106/method-feasibility.md). The first two are being finalized alongside implementation; their current status is recorded in the stage checkpoint.
