# TETHER original LitQA2 evaluation

**BG04's declared public-task measurement completed.** All 199 candidates are
sealed, source-inclusive replay passes, and native scores and source-identity
diagnostics agree with separately implemented reconstruction. The result is weak:
12/199 correct answers (6.03%), with 21 substantive answers and 178 unsure. All
candidates were admitted, so checking changed neither accuracy nor coverage.
This completes the measurement, not scientific or clinical qualification.

## Question and comparison

This experiment asks how one frozen local literature-answering route performs on
the original 199 public LitQA2 questions, and what a declared source-backed
admission policy changes for exactly those candidate bytes. It does not reproduce
the original paper's tool-free model condition. TETHER's source collection,
eligibility checks, grammar and transport are shared by both reporting arms;
the raw arm is the produced answer before the additional admission decision,
not a wholly TETHER-free workflow.

A filter cannot increase correct answers per scheduled question when candidate
bytes are fixed. It may reduce admitted errors, lose correct answers, or change
selective precision and coverage. Answer-key agreement, source identity and
scientific entailment are different outcomes. The experiment measures the first
two; it does not adjudicate whether a cited passage entails the answer.

The [frozen protocol](<TETHER LitQA2 Evaluation Protocol 2026-11-06.md>) and
[paired-comparison scope](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/stage/PAIRED-COMPARISON-SCOPE.md)
define these boundaries. The [original LAB-Bench paper](https://arxiv.org/html/2407.10362v1)
and [public dataset](https://huggingface.co/datasets/futurehouse/lab-bench)
define the upstream task. These public questions are exposed development assets,
not a private test or proof of absence from model training.

## Fixed inputs and execution

The original family was selected before candidate performance. The dataset is
pinned to Hugging Face revision `5c77cec648430f30611808808861eb86f81d5eaa` and the
original repository to `998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`. All 199 JSONL
rows reconcile with Parquet; two duplicate-distractor rows retain their original
indexed options. All choices, including the explicit unsure choice, use one
frozen shuffle. Answer keys, original source hints and privileged passages are
excluded from the answerer projection.

Question-only Europe PMC retrieval uses two fixed lexical queries, at most three
eligible full-text articles and eight passages per question. Each passage is
bounded at 1,000 UTF-8 bytes, selected text at 8,000 bytes in total per question,
and the full prompt at 14,000 bytes. The route selects
CC-BY/CC0 articles under the declared extraction policy. The contemporary input
availability cutoff is `2026-11-06T01:47:57.427510+00:00`, after collection.
Verified downloads establish a current availability bound, not historical access.
Reported publication dates remain separate.

Collection completed all 199 cases: 198 yielded eligible articles and one had an
empty source view. All 199 actual prompts fit; the maximum was 9,980 bytes.
Retrieving an article does not establish retrieval of the benchmark's annotated
source, decisive passage or relevant evidence. Missing sources may reflect
retrieval, access, licensing or extraction limits rather than biological absence.

The answerer uses the existing Qwen2.5-14B-Instruct Q4_K_M assets and pinned
llama.cpp runtime. It returns a zero-based visible answer index and captured
evidence IDs. Grammar, native parsing and provenance verification constrain the
interface; they do not decide answer correctness. Native transport and archived
replay qualified, but two attempts on the same unchanged fictional positive-answer
item, under evolving implementation, selected the wrong unsure option. They are
not independent capability samples. Prospective amendment A01 retained that failed semantic control
and allowed a descriptive weak-baseline measurement, without post-result tuning.
Prepared smoke03 was never dispatched. The historical failed attempts remain.

After collection closed, amendment A02 corrected two worker cache-root checks.
The original and corrected source bytes, failing regression and 97-test passing
gate were retained before benchmark inference. It changed no model, prompt,
question, source, option shuffle or scientific setting. The
[generation freeze](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/stage/generation-freeze-attempt02/GENERATION-FREEZE.json)
binds the prospective correction separately from the original collection freeze.

Generation performed 199 calls and 199 tokenizations with no unresolved calls or
automatic retries. Normal server cleanup is retained. The worker's input audit
recorded zero denied opens; this is a trusted-code audit hook, not an OS sandbox
or proof that public tasks were absent from pretraining. The generation-frozen code
is preserved through scoring and independent reconstruction.

## Native outcomes and source diagnostics

The independent reconstruction completed before viewing production scores. Its
externally anchored report is `e184cbaefa4ca767d0dcf0c55286b96ea768f624fd512d9585ec4aefe41f4fa0`.
The production scorer's complete source-inclusive replay and the separately
anchored primary comparison pass. All 199 original key permutations match the
prepared reference view; every candidate matches its native response and session.

| Quantity | Raw candidate | Same candidate after admission |
|---|---:|---:|
| Scheduled / produced | 199 / 199 | 199 / 199 admitted |
| Correct / all scheduled | 12 / 199 (6.03%) | 12 / 199 (6.03%) |
| Substantive answers / all scheduled | 21 / 199 (10.55%) | 21 / 199 (10.55%) |
| Correct / substantive answers | 12 / 21 (57.14%) | 12 / 21 (57.14%) |
| Incorrect substantive answers | 9 | 9 admitted |
| Valid unsure answers | 178 | 178 admitted |
| Operational failures / parse failures | 0 / 0 | 0 check errors |
| Correct answers lost to checking | — | 0 |

The 187 incorrect-and-admitted entries under the native answer-key convention
include 178 valid unsure responses. They are not 187 substantive false claims.
The policy neither increased accuracy nor rejected an answer in this run. High
admission does not demonstrate scientific accuracy, and 57.14% precision applies
only to the selected 21 substantive responses, not all 199 questions.

The independent analytical uniform-substantive-choice expectation is 24.43%
accuracy at 100% coverage. This is an unexecuted arithmetic reference with a
different coverage level, not a matched control or evidence of statistical
superiority. Always unsure yields zero accuracy and zero coverage. Exact shared
annotation strings/questions form 186 observed components in the reconstruction;
unresolved aliases and broader dependence prevent interpreting this as an
independent sample count. No confidence interval treats all 199 as independent.

The separate [DOI audit](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/operational-audit/SOURCE-DOI-REVIEW.md)
finds 10/205 annotated per-question DOI pairs (4.88%), covering 10/199 questions
(5.03%), in both retained articles and selected prompt sources. All 199 questions
have explicit DOI annotations. Independent article-front XML parsing confirms
the same hits: it supplies the missing metadata DOI for 42 of 538 retained
article instances without finding additional annotated sources. There are 406
selected article instances and 525 distinct retained PMCIDs; these are not
independent question observations.

Thus having some eligible text for 198 questions hides low annotated-source
coverage. Missing DOI metadata does not explain this particular gap. The audit
does not distinguish poor search from eligible-universe, access, licensing or
extraction restrictions, nor prove the annotated paper is the only source that
could answer a question. A selected paper identity does not establish that its
decisive passage was supplied. The primary scorer and independent audit agree on
DOI-pair and question-hit counts for every question in both source arms; the
independent parser does not reproduce the broader alias graph or independently
establish the 16-item resolved subset.
Only 16/205 annotation identifiers resolve through collected discovery metadata;
the secondary conditional recall of 10/16 (62.5%) is selected by that metadata
availability and must not replace the overall DOI recall of 10/205.

A [post hoc descriptive join](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/stage/SOURCE-ANSWER-CONTINGENCY-01.json)
compares selected-paper identity with answer outcomes:

| Selected annotated DOI | Questions | Correct | Wrong substantive | Unsure |
|---|---:|---:|---:|---:|
| Present | 10 | 6 | 2 | 2 |
| No observed hit | 189 | 6 | 7 | 176 |

This association supports investigating source access and retrieval. It does not
estimate the causal gain from improving either: question difficulty, access and
other factors differ between groups. Correct answers without an annotated-source
hit can arise from other evidence, prior knowledge or guessing; the join does not
identify which. Even when the paper is selected, four of ten responses are not
correct. Decisive-passage access and answer interpretation remain unmeasured
candidate failure points.

The strict JSON adapter counts malformed output as operational failure: incorrect
on all-scheduled accuracy and outside substantive precision/coverage. This differs
from upstream treatment of arbitrary returned strings. Undefined precision at
zero substantive coverage must remain explicitly undefined, even where a numeric
zero is retained for upstream convention compatibility. Analytical chance and
always-unsure controls are not executed arms and receive no invented runtimes.

## Cost and efficiency

The source collection made 995 HTTP attempts and received 141,355,700 known
response-body bytes, with zero unknown-transfer reservation. It selected
1,361,055 bytes of text. The 3,186-file collection inventory holds 189,016,148
product bytes. Supervised collection elapsed time was 2,052.406 seconds.
Response-body bytes exclude protocol overhead; product sizes are not physical I/O.

The supervised generation worker took 1,161.953 seconds. Native usage reports
443,470 input and 34,279 output tokens, with zero estimated unresolved usage and
$0 external-provider spending. The sampled native-process lifetime peak working
set reached 16,633,806,848 bytes; sampled current working set is a different
quantity. GPU memory, energy, hardware depreciation and labour costs were not
measured. Zero provider charges do not mean zero total cost.

The parent timer is captured before finalization. It excludes case recovery,
publication, inventory hashing and sealing; that finalization has no separate
deadline. There is no retained outer monotonic total-stage timer. Filesystem
chronology suggests about 29.4 minutes from the declared parent reservation to
seal modification time, but this is not an attested stopwatch measurement.
Do not substitute the worker's approximately 19.4 minutes for total latency.

A [read-only allocation probe](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/stage/READ-ALLOCATION-DIAGNOSTIC.md)
found that `proof()` requests 512 MiB reads even for tiny files. Five reads of a
36,668-byte source file took about 0.455 seconds with that cap versus 0.000719
seconds with a file-size bound in this local microprobe. The probe is not a
profile of the actual parent and does not assign an exact share of its runtime.
Frozen code was not changed to improve reported benchmark timing.

Marginal admission time is uninstrumented: source capture, transport, generation
and checking share per-case records. It cannot be inferred by subtracting broad
timers. The complete evaluator wrapper took 882.172 seconds and 817.953125 seconds
of controller CPU; its internal pre-publication timer is 881.797 seconds. That
includes source/model verification, candidate replay, scoring and output work,
not an isolated admission-check cost. Its reported process-lifetime peak working
set was 579,141,632 bytes, not incremental memory. It verified 9,112,208,256 unique
model/runtime/receipt bytes; this is not physical I/O. Blind native reconstruction
took 17.203 seconds but performs fewer obligations, so these times are not a
policy-equivalent speed comparison. The
[resource-scope record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/stage/RESOURCE-SCOPE-02.json)
states measurement scopes and unknowns.

## Retained artifacts and qualification

| Artifact | External SHA-256 |
|---|---|
| Preparation manifest | `7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b` |
| Collection manifest | `b75558de8fca5382729e42d7bd6adc9efabdb072791b0d75201aaff2280c47de` |
| Original freeze | `8172610c5637d7a952f80be8a2fe89d01a0c421d638ae254e30c76541886d6f7` |
| Generation amendment freeze | `4359d589205caec39085872cc72cd5799323e2285e0993b58405e7e70ccd2fe5` |
| Generation seal | `46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447` |
| Independent operational audit | `abcd5878cb83f1e7e481239e347952c9ae207ef47cf373d59977af3f69810576` |
| Blind native reconstruction | `e184cbaefa4ca767d0dcf0c55286b96ea768f624fd512d9585ec4aefe41f4fa0` |
| Independent DOI audit | `d8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7` |
| Primary evaluation seal | `118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f` |
| Native primary comparison | `0374f21ca3b7b49ba6810adc7cb316f960b2050c6e76630ce611986066e429a6` |
| Source primary comparison | `8b1bf151426afe91525b8783249f28cbe421ba8fa09b82206f15a2e550ffa764` |
| Completed resource scope | `8c39c654b6711e4c03c3ab4b1a476f65ede8f7277f46a0d19b3df665122c5218` |

Bulk originals and outputs remain in ignored `data/raw/labbench_public/` and
`data/benchmark/labbench/` directories. The
[stage checkpoint](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/STATUS.md) and
[execution state](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-labbench-20261106/EXECUTION-STATE.json)
identify the exact current attempts. Failed helper/qualification attempts remain
separate from actual generation outcomes. The operational auditor required a
separately tested amendment-proof reader correction and an exact-path invocation;
the DOI audit corrected a newline-preservation hash assumption. The native primary
comparison also uses a separately qualified reader for the evaluator's journal
seal format. Original helpers and failed attempts remain, and no production
candidate or frozen experiment module was changed for these corrections.

The maintained experiment gate passed 97 fictional tests. Separate reconstruction,
operational and DOI readers have their own retained controls; these counts are
not pooled into an independent scientific sample. Here, independent means a
separate implementation that does not import the corresponding production
scorer/auditor. These are AI-assisted engineering checks in the same project,
not independent human biological adjudication or a separate laboratory result.

The declared measurement establishes full schedule retention and replay under
the specified source policy. It shows low useful-answer yield and no incremental
scientific accuracy benefit from candidate filtering. Better retrieval, decisive
passage selection and answer interpretation require separately frozen capability
experiments; this run is not retuned. Equivalent-policy Inspect is the next
authorized stage. Broader synthesis, causal genetics and clinical utility remain
outside this experiment.
