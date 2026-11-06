# TETHER benchmark comparison update

Reviewed 6 November 2026 UTC. This supplements the [earlier peer comparison](<TETHER benchmark priorities and methods.md>) with the completed SciFact result and three additional methodological peers. The practical priority is scientific answer quality under matched controls. Provenance machinery alone has not shown an accuracy advantage.

TETHER's independent full-policy comparison found equal conformance on 109 exposed constructions, with greater measured fresh-process cost for TETHER. Its native SciFact experiment produced and admitted all 300 public-development answers; 27 met the declared strict correctness criterion. Raw and checked official scores were identical. Retrieval recovered 159/209 annotated claim–document pairs, while only one evidence-bearing claim was strict-correct. This suggests a serious answer-selection/interpretation bottleneck, although retrieval misses and the strict evidence-set criterion also contribute. It does not prove that a better retriever would be useless. ([Equal-policy results](<../planning/TETHER Equal Policy Comparison Results 2026-11-05.md>), [SciFact results](<../planning/TETHER SciFact Native Evaluation Results 2026-11-05.md>))

For scale, always predicting insufficient evidence would match the 112 NEI cases
out of 300 (37.33%) under the strict case criterion, with zero evidence-retrieval
credit. This is a post hoc analytical control, **not an executed arm** or a useful
scientific verifier. The current 9% result is therefore weak even against this
trivial accuracy reference; the official evidence metrics must remain visible
alongside case accuracy. ([Retained SciFact analysis](<../planning/TETHER SciFact Native Evaluation Results 2026-11-05.md>))

## Benchmarks that answer different questions

| Benchmark or comparison | What it can demonstrate | Required outcome and main limitation | Priority |
|---|---|---|---|
| **SciFact** | Scientific claim verification with retrieved abstract evidence | Official label/rationale precision, recall and F1; strict correct-and-admitted/all scheduled. Completed baseline is weak: rationalized F1 0.087 and 9% strict correctness. Public dev is not a private test. | Completed baseline; use a separately frozen future experiment for improvements. |
| **Original LAB-Bench LitQA2** | Literature retrieval and biological factual answering | Completed public199 baseline:12correct,21substantive,178unsure; raw/check equal. Only10/199 questions have an annotated paper among selected sources. Reference answers/source hints were excluded from generation. | Completed weak baseline; improve retrieval/answering in a new frozen experiment. |
| **Inspect with equivalent policies** | Whether the same obligations are easier or cheaper to implement in an established runner | Matched conformance, failure accounting, source binding, cost and added policy code. Inspect is a framework, not a scientific benchmark. | Following LAB-Bench. |
| **ALCE** | Correctness and citation quality in generated answers | Native correctness and citation precision/recall with a qualified evaluator. Citation existence is insufficient. | After a useful answer generator is qualified. |
| **ScholarQABench** | Multi-paper scientific synthesis | Released questions, rubrics and citation evaluation are relevant to dossiers. Its automatic judge setup needs separate qualification and cost accounting; no new human panel is necessary to use existing released annotations. | Strong later synthesis benchmark. |
| **R2E** | Target-related retrieval and ranking | Native masked-gene ranking metrics with a frozen candidate universe. Clinical progression labels are not endpoint efficacy labels. | Domain-focused extension. |

The original LAB-Bench release supports a public evaluation without importing newer LABBench2 tasks. The published 2024 model experiments were tool-free; a question-driven retrieval system is a tool-assisted public-task evaluation, not an exact reproduction of those model conditions. Its uncertainty option must be separated from timeout, malformed response and missing output. ([Original task paper](https://arxiv.org/html/2407.10362v1), [official dataset](https://huggingface.co/datasets/futurehouse/lab-bench))

Peer headline scores are context rather than matched controls. PaperQA2's authors
state that LitQA2 guided system design; OpenScholar introduces ScholarQABench
alongside its system. This does not invalidate either benchmark, but public task
exposure and co-development limit claims of independent generalization. Different
base models, source universes, tools and inference budgets also prevent assigning
a cross-paper score difference to TETHER's harness. A controlled method ablation
is more informative than subtracting published leaderboard numbers.
([PaperQA2](https://arxiv.org/abs/2409.13740), [OpenScholar](https://www.nature.com/articles/s41586-025-10072-4))

ALCE's released data and evaluation code provide a concrete citation test. ScholarQABench broadens the question from finding one answer to covering a literature question. The latter's repository exposes data, rubrics and evaluation scripts; code licensing does not automatically settle all incorporated-source and model rights. A local judge replacing its configured judge is a separate evaluation condition. ([ALCE](https://github.com/princeton-nlp/ALCE), [ScholarQABench](https://github.com/AkariAsai/ScholarQABench), [R2E release](https://github.com/BenevolentAI/r2e-evaluation-data))

ScholarQABench's reference work dates to July–September 2024. Its repository
warns that newer retrieved information changes comparability; the published v1
method recommends its OSDS or a publication cutoff no later than October 2024.
Freeze the benchmark/subset and evidence date together. A current-literature
variant is reasonable, but is a different condition against dated references.
([Dataset chronology and terms](https://github.com/AkariAsai/ScholarQABench), [published limitations](https://www.nature.com/articles/s41586-025-10072-4))

DbQA remains useful, but it requires product-by-product source qualification. Exact MSigDB 2023.2 files have a public distribution route, so a blanket claim that DbQA is account-blocked would be wrong. Full-family coverage, historical equivalence and all source terms remain unverified. LitQA2 is preferred for its fit to literature evidence and a uniform public retrieval route, rather than a claim that every DbQA source is inaccessible. ([Official MSigDB archive](https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2023.2.Hs/))

The general-runner comparison must reconcile denominators explicitly. Inspect
distinguishes a verdict, an execution error and an unscored result; its ordinary
accuracy excludes missing verdicts. Incorrect or malformed model answers can
still receive an incorrect verdict. TETHER's scheduled-case yield answers a
different question. Report both verdict-conditioned accuracy and useful answers
per scheduled task, with failures and unscored counts alongside them. Implement
the same convention in both runners before comparing numbers; this is not an
intrinsic inability of Inspect to support the desired policy. ([Inspect scoring policy](https://inspect.aisi.org.uk/scoring-policy.html))

Inspect already offers bounded execution, retained interrupted-run logs and
explicit retry artifacts, plus an agent-bridge execution contract that checks
tool proposals and arguments. Generic limits, traces and orchestration therefore
do not distinguish TETHER. The narrower contribution to test is its combination
of source-role policy, temporal ancestry and source-inclusive replay. Pin the
Inspect version and implement those obligations explicitly; neither a bare
Inspect run nor TETHER's smaller native-task adapter establishes full BG02 policy
equivalence. ([Tool execution contract](https://inspect.aisi.org.uk/agent-bridge.html#execution-contract), [limits](https://inspect.aisi.org.uk/setting-limits.html), [run logs](https://inspect.aisi.org.uk/eval-logs.html), [native adapter scope](../experiments/labbench/tether_adapter.py))

For LitQA2, explicitly report `accuracy = correct / scheduled`,
`precision = correct / substantive answers`, and
`coverage = substantive answers / scheduled`, retaining operational failures.
Precision is undefined when there are no substantive answers. The strict JSON
adapter's malformed-response convention differs from the original evaluator's
treatment of arbitrary returned strings, so publish that difference and the
parse-failure count rather than presenting all quantities as unchanged upstream
metrics. ([Native scoring contract](../experiments/labbench/evaluate.py), [frozen protocol](<../planning/TETHER LitQA2 Evaluation Protocol 2026-11-06.md>))

## Peer methods worth testing

**PaperQA2: query-conditioned evidence processing and citation traversal.** Its method combines dense chunk retrieval with relevance scoring/contextual summarization and traversal from retrieved papers. These are stronger scientific retrieval operations than TETHER's maintained literal-overlap selector. Importantly, the paper reports that weaker summarization models can hurt performance. This is a reason to compare raw passages against summaries, not assume that adding another model stage improves the answer. ([PaperQA2 methods and ablations](https://arxiv.org/html/2409.13740v1), [current selector](../src/asof/retrieval.py))

For TETHER, keep original spans alongside every generated summary and test raw passages, reranked passages and summaries at the same context and total compute budgets. Measure missed decisive information, altered qualifications and downstream answer accuracy. Citation traversal should begin from question-retrieved evidence, never evaluator-only source hints. Do not import popularity scores as scientific support weights.

This is an incremental proposal: the SciFact experiment already implements
TF–IDF retrieval and trained linear label/rationale classifiers, while the new
LitQA2 adapter provides question-driven Europe PMC search and lexical passage
selection. The missing additions are learned relevance reranking, controlled
evidence summarization and bounded citation traversal; “add retrieval” would
misdescribe the current project. ([SciFact baseline](../experiments/scifact/baseline.py), [LitQA2 retrieval](../experiments/labbench/retrieval.py))

**OpenScholar: retrieval refinement and answer repair.** OpenScholar uses retrieval/reranking, feedback-driven additional retrieval and a citation-verification step. Its February 2026 paper and released implementation are relevant scientific-synthesis peers. The full workflow is not equivalent to simply adding a reviewer role. ([Published method](https://www.nature.com/articles/s41586-025-10072-4), [implementation](https://github.com/AkariAsai/OpenScholar))

Test a fixed one-pass baseline, critique-only and one bounded repair with the same model and total resource cap. Retain both repaired errors and newly damaged correct answers. A model judging its own citations can share its original mistake; use benchmark annotations where available and disclose judge dependence elsewhere. The current TETHER structural review does not establish this capability.

**Self-RAG: learned decisions about retrieval and support.** Self-RAG trains a model to emit retrieval and critique signals as part of generation. It is not just a prompt telling a model to reflect. ([Original paper](https://arxiv.org/abs/2310.11511), [official code](https://github.com/AkariAsai/self-rag))

The transferable experiment is conditional retrieval and abstention against fixed retrieval under a matched budget. A prompt-based local approximation must be labelled as such. Training a reflection model is a larger, separate project. Calibrate any acceptance threshold on source-disjoint development groups; self-reported confidence alone is not a validated risk estimate.

**MultiVerS: joint scientific labels and rationales.** Full-document context with joint label/rationale learning directly addresses a capability that SciFact exposed as weak. This is a better targeted next semantic baseline than adding generic coordination agents. Qualify checkpoint provenance and training exposure before comparisons. ([MultiVerS](https://aclanthology.org/2022.findings-naacl.6/))

**ERASER: test whether evidence actually matters.** Remove decisive evidence, retain the rationale alone, and add irrelevant or contradictory context. These interventions can reveal correct answers produced despite unused or misleading evidence. TETHER already has evidence masks; the missing result is a qualified native answer experiment using them. Use ERASER's native metrics only when their required class scores and task assumptions are met. ([ERASER](https://aclanthology.org/2020.acl-main.408/))

## What would strengthen the paper most

1. **Separate filtering from producing better answers.** With identical frozen candidates, correct-and-admitted/all scheduled cannot exceed raw-correct/all scheduled: a filter cannot create correct answers. It can improve selective precision or reduce admitted errors, at a cost in coverage. Report correct answers rejected, semantic errors admitted, failure rates and cost. A separate retrieval/repair experiment is needed to test an increase in useful answers. The current SciFact admission rate of 100% is not an accuracy result.
2. **An error decomposition.** Separate missing source, missed passage, wrong interpretation, wrong MCQ choice and operational failure. Gold source recall is a diagnostic after sealing outputs; it must never guide retrieval during evaluation.
3. **A semantic intervention with a falsifiable benefit.** One repair or full-context semantic baseline should increase useful answers without hiding refusal, extra inference or harm. Keep the weak existing baseline fixed.
4. **A source-change stress test.** Use plausible outdated annotations, irrelevant but valid citations and contradictory source statements. Distinguish deliberately constructed controls from naturally observed errors and never infer natural error prevalence from the controls.
5. **A simpler-runner comparison.** The standalone architecture needs empirical justification against policy-complete Inspect, counting extension code and all dependencies. Faster hashes alone cannot establish equal scientific safeguards.

There is a consequential design alternative: retain TETHER's evidence-policy and
verification components as an extension to a maintained evaluation runner. If
equivalent-policy Inspect preserves the same failure records and source guarantees
with less custom orchestration, that would argue for reducing TETHER's standalone
runner surface. This is a decision criterion for BG05, not a result already
established by reading documentation or by the simpler-validator experiment.

No reviewed benchmark jointly validates therapeutic success, model-weight chronology, all source policies and scientific synthesis. The strongest defensible paper combines scoped engineering guarantees with measured scientific utility, and retains negative findings when a control adds cost without improving answers. Virtual Biotech's overlapping provenance and orchestration capabilities further weaken any novelty claim based only on agent roles or trace collection; its pinned baseline and current implementation must remain separate comparison targets. ([Earlier source-qualified comparison](<TETHER benchmark priorities and methods.md>))

LitQA2 is now complete in its declared public-task scope; equivalent-policy Inspect
and the final goal audit remain. PaperQA2/OpenScholar-style semantic improvements
and broader synthesis benchmarks are follow-on experiments, not silently added
requirements. No peer performance number is transferred to TETHER, and this
comparison does not replace the frozen SciFact result.

The completed LitQA2 run reinforces the distinction. Its97 maintained fictional
tests and source-inclusive replay pass, while the same answerable fictional item
failed in two semantic attempts under evolving implementation. A prospective
amendment retained that failure. All199 actual candidates are admitted;12/199 are
correct6.03%, with57.14% precision on only21 substantive answers and178 unsure.
No raw/checked accuracy or coverage difference is observed. Separate native and
source implementations agree. ([Protocol](<../planning/TETHER LitQA2 Evaluation Protocol 2026-11-06.md>),
[results and audits](<../planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md>))

Only10/205 annotated DOI pairs were retrieved and selected, covering10/199
questions. XML checks filled42 missing metadataDOIs without adding hits. In a
posthoc join, six of10 source-hit questions were answered correctly versus six
of189 without a hit. This supports investigating search/access and decisive
passage coverage, without estimating a causal improvement or establishing
that other papers cannot answer the question. The nine wrong substantive
answers also show why a valid cited source is insufficient. A controlled
retrieval/reranking or separately labelled supplied-source diagnostic is more
informative than adding generic agents. Source-license and availability limits
must be measured alongside retrieval quality. ([Retained analysis](<../planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md>))

The execution also exposed a concrete efficiency issue: fixed512MiB read caps
allocate large temporary buffers for tiny files. Its frozen controller finalizes
outside the worker deadline and omits that work from its pre-seal timer. These
limits are disclosed, not corrected retroactively. Native-score reconstruction
alone is cheaper than source-inclusive replay, but performs fewer obligations;
their timings are not an equal-policy comparison. ([Resource and allocation evidence](<../planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md>))
