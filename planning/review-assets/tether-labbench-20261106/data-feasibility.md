# BG04: original LAB-Bench source and task feasibility

Reviewed 2026-11-06 UTC, before benchmark candidate production or scoring. This note follows the active [execution plan](../../TETHER%20Benchmark%20Execution%20Plan%202026-11-02.md) and revises the retained [biomedical peer assessment](../../../research_notes/TETHER%20benchmark%20priorities%20and%20methods/biomedical.md). SciFact artifacts remain unchanged.

## Selection and scope

Select **all 199 public original LitQA2 questions**, subject to retained schema qualification, with question-only search and licensed full-text retrieval through Europe PMC. This selects a task family before performance; it does not select the easiest or most accessible questions. Missing, inaccessible or unsuccessfully retrieved evidence remains in the 199-case denominator. The resulting experiment is a contemporary, restricted-source, tool-enabled attempt at the original question/answer task. It is not a reproduction of the original paper's no-tool model baseline, a private test-set evaluation, or proof of uncontaminated model knowledge.

DbQA remains a useful follow-up. **Do not describe all its sources as account-blocked:** the official [MSigDB 2023.2 human release directory](https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2023.2.Hs/) exposes the exact C1/C3/C6/C7 artifact names used by several question families. The [MSigDB terms](https://www.gsea-msigdb.org/gsea/msigdb_license_terms.jsp) assign CC-BY 4.0 to these releases, with separately named restrictions for some other collections. No MSigDB files were acquired here. The remaining DbQA mixture includes historical database joins, variant interpretation, sequence matching and product-specific access/version uncertainty. Original Ensembl 110 data alone are not established substitutes for the MSigDB C1 memberships used to construct that subtask. LitQA2 was selected for a uniform public retrieval interface and relevance to evidence-grounded answering, not a claim that DbQA is impossible.

## Verified public pins and acquisition

| Asset | Pin / retained observation |
|---|---|
| Original HF dataset | [`futurehouse/lab-bench@5c77cec648430f30611808808861eb86f81d5eaa`](https://huggingface.co/datasets/futurehouse/lab-bench/tree/5c77cec648430f30611808808861eb86f81d5eaa); an exact available revision, not a claim that a cached page proves latest HEAD |
| LitQA2 Parquet | `LitQA2/train-00000-of-00001.parquet`, 99,737 bytes; SHA-256 `3e578fdaaa4728a77e884954dbf85ae0e3899791631a3be0838313b3e2334114`, matched against HF LFS metadata |
| Official code | [`Future-House/LAB-Bench@998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`](https://github.com/Future-House/LAB-Bench/tree/998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838) |
| Native JSONL | `LitQA2/litqa-v2-public.jsonl`, 200,640 bytes, 199 parsed rows and 199 distinct native IDs; pinned Git blob verified |
| Source/licensing files | Native task, evaluator, utilities, zero-shot wrapper, package metadata, README and LICENSE retained with Git-blob checks; HF README/LICENSE retained separately |
| Rights | Original dataset/repository declare CC-BY-SA 4.0; article rights remain separate. Retain attribution/license and identify modified projections |
| Acquisition | [Ignored original bundle](../../../data/raw/labbench_public/20261106-attempt01/ACQUISITION.json): 17 files, 719,061 downloaded bytes; no retries; receipt SHA-256 `620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd` |

The public HF splits are named `train`; this is a distribution label, not permission to fit a solver using the evaluated answer keys. The [dataset card](https://huggingface.co/datasets/futurehouse/lab-bench/blob/5c77cec648430f30611808808861eb86f81d5eaa/README.md) describes public/private partitions and a contamination canary. This experiment uses only the public set and cannot resolve prior model exposure. The smaller official JSONL is the stdlib preparation input; independently acquired Parquet is corroborating original evidence, not silently assumed byte-equivalent.

## Native inputs, hidden fields and scoring

The pinned [base instance and choice generator](https://github.com/Future-House/LAB-Bench/blob/998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838/labbench/utils.py) pass `id`, `question` and displayed choices to an agent. All choices, including the refusal option, are shuffled. Freeze one seeded permutation schedule for both arms; preserve the native `(A) ...` presentation. The correct option text is necessarily among the task-visible choices; its **identity as correct** is evaluator-only.

| Logical view | Fields / use |
|---|---|
| Predictor query | `id`, `question`, `choices` only; no hidden source metadata |
| References | `id`, zero-based `answer_index`, `unsure_index`; evaluator only |
| Private preparation provenance | Original line bindings, original metadata, source URLs, `ideal` marker, `key-passage`, `source`, `sources`, `is_opensource`, tag/version/subtask/canary, seed and permutation policy; never supplied to predictor |
| Retrieved evidence | Only documents found by a frozen query function of question text, with retained request/result/license/source bytes and hashes |

Source URLs and key passages are privileged even when the articles themselves are public. Per-question article fetching from `sources`, or building a pooled corpus from benchmark-listed sources, changes the retrieval task. Such a study must be explicitly described as a source-provided or oracle-corpus derivative. It is not this planned experiment. Deterministic shuffling supports replay, not secrecy: a party with the ideal-first input convention, seed and row order could reconstruct positions. Predictor input isolation therefore must exclude that information; no adversarial confidentiality claim follows.

The [native evaluator](https://github.com/Future-House/LAB-Bench/blob/998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838/labbench/evaluator.py) uses exact answer-letter equality. Accuracy is correct/all; precision is correct/non-refusal; coverage is non-refusal/all, with zero for empty denominators. An invalid non-refusal string is attempted and incorrect. Original row-loading can skip validation failures; the new controller must instead retain every scheduled failure explicitly and reconcile all 199 IDs. TETHER admission utility and source-support measurements are separate additional outcomes. Admission does not establish correctness.

## Source feasibility and rights probe

The live, nonbenchmark query `TITLE:"photosynthesis" AND OPEN_ACCESS:Y AND FIRST_PDATE:[2000-01-01 TO 2023-12-31]` returned a valid JSON search response through the official `www.ebi.ac.uk/europepmc/webservices/rest/search` endpoint. The first returned eligible article, `PMC10569730`, yielded full XML through `/PMC10569730/fullTextXML`, including a body of 62,970 text characters. Its metadata identifies CC-BY and its XML explicitly states Creative Commons Attribution. The [retained probe](../../../data/raw/labbench_public/20261106-attempt01/nonbenchmark-probe/summary.json) contains the request, response hashes and rights observations. No benchmark question, choice, source hint, answer or performance was used.

This verifies that one supported public route works; it does **not** establish the rate of finding adequate evidence for LitQA2. Europe PMC's [copyright guidance](https://dev.europepmc.org/Copyright) requires article-specific rights checks; its [developer documentation](https://dev.europepmc.org/RestfulWebService) provides supported programmatic interfaces. PMC likewise [distinguishes its reusable OA subset from merely readable articles](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/). The run should initially allow only explicitly confirmed CC-BY or CC0 full text, preserve attribution, and record missing/ambiguous/other licenses as unavailable. Use the supported API; do not scrape article webpages or infer that HTTP 200 confers reuse rights.

## Implementation requirements and a zero-cost producer

1. Validate the immutable originals, IDs, schema, duplicate choices and native count. Fail rather than skip malformed rows. Generate sealed query/reference/provenance products with field-level lineage; keep their purposes separate from the mixed physical container.
2. Qualify native MCQ permutations and scorer behavior on fictional cases. Freeze the full 199-case schedule, seed, model, parser, deadlines and budgets before benchmark retrieval or answering.
3. Use a deterministic question-only query policy, at most two variants and ten results per variant, and at most three eligible full-text documents per question. Bound every response and total runtime; retain HTTP status/body hashes, failed requests and unknown metadata. No automatic unbounded retries or reference-guided fallback. Freeze requests and actual responses so both arms share identical evidence.
4. An available local quantized model can answer the actual MCQ from its displayed question/options and retrieved passages at **$0 provider spend**, subject to local runtime/model qualification by the producer owner. No new weights, paid model calls or human review are prerequisites. A CPU lexical option/evidence ranker is a fallback modest baseline, not an expert semantic solver; its task capability would need fictional qualification before use. This note does not claim either producer has run or reached useful accuracy.
5. Compare the same immutable producer candidates without/with TETHER admission. Verify only declared structural/provenance/purpose constraints. Report native accuracy/precision/coverage, correct-and-admitted utility, false rejection, refusal, parsing/retrieval failures, evidence availability and producer/checker costs separately.
6. Perform source-inclusive independent reconstruction after freezing all predictions. Public exposure, limited OA coverage, index drift and model uncertainty remain explicit. Retrieval restricted to licensed sources is an affordance limit, not a reason to remove failed questions.

No benchmark retrieval, projection, answering, scoring, trained model, human adjudication or scientific performance result is claimed by this feasibility note. Acquisition and the unrelated endpoint probe are complete; implementation and controlled execution are next.
