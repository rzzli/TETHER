# SC07 forward feasibility - not activation or an execution freeze

Read-only preparation on 6 November 2026 while SC04 is active. No acquisition,
installation, model call, benchmark execution or source-code change was made.
The prospective recommendation is **the complete ScholarQA-Multi family**;
native quality evaluation is not yet qualified on this machine. The earlier
7B-judge suggestion is a separately labelled changed-evaluator condition, not a
way to claim native-judge equivalence silently. The published judge is the
preferred first qualification route; exact checkpoint reproduction is not an
additional requirement imposed by the authoritative SC07 plan.

## Family, annotations and source eligibility

The retained primary-source review identifies Multi108 and CS100 as complete
annotation-supported choices. Multi provides reference answers; CS provides
question-specific rubrics. Bio1451 and Neuro1308 support citation evaluation but
not released correctness labels. Counts remain documented expectations until
original bytes and unique IDs are checked. The recommendation is all records in
`data/scholarqa_multi/human_answers.json` at ScholarQABench revision
`95e6fc52b0a8a0ce0a74956029991e3bb00c38b9`, not 108 sampled records.
[Retained family review](../synthesis-feasibility/FEASIBILITY.md),
[official overview](https://allenai.org/blog/openscilm).

The release uses ODC-BY 1.0 for aggregate data and preserves constituent terms.
References/rubrics were created July-September 2024; later evidence changes
comparability. Multi's native endpoints are organization, coverage and relevance
on a five-point rubric, plus citation support. CS has a different rubric pipeline.
The README's Prometheus heading says CS, but its input path is Multi; freeze
resolved files and commands rather than copying that heading.
[Pinned release instructions](https://raw.githubusercontent.com/AkariAsai/ScholarQABench/95e6fc52b0a8a0ce0a74956029991e3bb00c38b9/README.md).

Source coverage remains **unverified for all 108 cases**, not zero evidence and
not an established incomplete fraction. The OpenScholar README links released
offline retrieval results. The linked Drive folder failed to render in the web
tool during this review; that is not evidence of an authentication requirement.
No file IDs, bytes, question joins, passage dates, rights or gold-independent
retrieval history were established. The supplied reference answers and their
cited papers cannot become a question-only source pool by changing folders.
[Official retrieval instructions](https://github.com/AkariAsai/OpenScholar),
[linked retrieval folder](https://drive.google.com/drive/folders/1lOloYPOveKesD-37lD4Dlju96tc0XIm9?usp=sharing).

An eligible pool must preserve question ID, retrieval request/configuration,
rank, paper identifier, title, publication/version dates, passage coordinates,
exact text hash and reuse terms. A retrieved paragraph is sufficient for a
paragraph-supported claim; it is not proof that the entire paper was collected.
Distinguish full text, abstract, excerpt, unavailable text and date uncertainty.
Document joins must not use candidate answers or reference citations. A frozen
public-paper collection is a possible declared source condition if the released
pool cannot be qualified; it is not an exact OpenScholar retrieval reproduction.
The full datastore is unnecessary for this narrower benchmark requirement.

## Native evaluators and resource gate

These are freshly checked entries in retained `PUBLIC-METADATA.json`, not locally
downloaded or loaded model files. Sizes count one selected checkpoint format.

| Evaluator | Revision | Checkpoint bytes | Consequence |
|---|---|---:|---|
| AttrScore FLAN-T5-XL | `bdd34a864dfec3d248b701ad2f725983f2d1236c` | 11,399,225,634 | Native citation judge; estimated BF16 tensors 5,962,706,944 B, runtime still unmeasured |
| Prometheus-BGB-8x7B | `154821124aa9a98acfa54fe43fa7360db31fbe0e` | 93,405,713,504 | Native organization/coverage; model-card license unresolved |
| Prometheus-8x7B | `2db013b60e3e91f7a06113e436410899768e8228` | 93,405,713,504 | Native relevance; Apache-2.0 metadata |
| Prometheus2-7B | `66ffb1fc20beebfb60a3964a957d9011723116c5` | 14,483,498,000 | Optional changed evaluator, never native equivalence |

The citation implementation uses AttrScore with literal `Attributable` output;
its TRUE/AutoAIS path is commented out. Do not reuse SC06's judge as though the
metrics were identical. Native citation precision/recall must preserve source
indices, sentence segmentation, multi-citation handling and actual denominators.
[Pinned citation implementation](https://raw.githubusercontent.com/AkariAsai/ScholarQABench/95e6fc52b0a8a0ce0a74956029991e3bb00c38b9/scripts/citation_correctness_eval.py).

The native quality recipe uses BGB for organization/coverage and the other 8x7B
model for relevance. Each exceeds 16 GB GPU plus 32 GB host RAM before working
memory. Unchanged BF16 disk offload is a possible engineering route, not a measured
feasible one. It needs an architecture-correct backend, preserved prompt/tokenizer,
reference/rubric handling, bounded loading, numerical controls and full-family
throughput estimation. Quantization changes numerical behavior and requires an
explicit condition; a 7B replacement changes the judge. The existing Windows
environment does not establish that the native vLLM invocation works.
[Native quality implementation](https://raw.githubusercontent.com/AkariAsai/ScholarQABench/95e6fc52b0a8a0ce0a74956029991e3bb00c38b9/scripts/prometheus_eval.py),
[retained model metadata](../synthesis-feasibility/PUBLIC-METADATA.json).

Two large judges plus AttrScore require 198,210,652,642 B of source weights;
tokenizers, two offload images, caches and backups are additional. A prospective
450-600 GB working allowance is an unmeasured scenario, not an acquisition cap.
Current disks appear sufficient for that scenario; throughput is the greater
uncertainty. Run evaluators sequentially after unloading the answer model.
For 108 answers, the three quality aspects require 324 judgments; two answer
conditions require 648, before citation calls or controls. A prospective
512-token judge-output cap means 165,888 tokens per answer condition. Do not
activate this cap until native completion/parse behavior is qualified. Counts
are arithmetic, not measured runtime.

## Smallest faithful qualification and execution route

1. After preceding stages, pin and verify every Multi record, question/reference
   separation, ordered IDs, code, rubric and terms. Inspect all joins without
   exposing reference answers to the generator.
2. Qualify a complete question-only retrieval pool; freeze a source cutoff and
   fulltext/excerpt/availability report for every case. Never drop unavailable
   cases to make coverage look complete.
3. First resolve BGB model rights and measure native BF16 offload with invented controls:
   unsupported addition, missing required content, irrelevant fluent answer,
   citation mismatch, reference copying, malformed output, truncation and longest
   permitted reference. Preserve controls and parsing failures. These are
   engineering checks, not human-judge agreement.
4. Freeze the local answer producer, evidence cap, output cap and full-family
   completion policy before answers. Existing Qwen is a candidate producer, not
   an OpenScholar reproduction. Reuse SC05 bounded repair only if its transport,
   budgeting and semantic behavior have passed; do not choose it from SC07 scores.
5. Generate all scheduled cases and independently reconstruct native citation and
   quality inputs/outputs. Report all-case missingness, native-scored denominators,
   raw/admitted results and paired changes with uncertainty. Separate source
   adequacy, judge reliability and scientific correctness claims.

CS100 is not a cheap native escape route: its configured GPT-4-turbo evaluator
needs a paid/API route, incompatible with the present $0 provider boundary.
Local CS judging would also be a changed condition. No expert recruitment is
needed. No manual credential blocker has been demonstrated for Multi; unresolved
source pool, rights and native memory/latency qualification are real gates.
If unchanged native evaluation cannot be qualified, report that gate rather than
silently declaring the stage complete with another judge. The plan requires a
qualified judge, the chosen released subset's full quality/citation endpoints,
all its cases and explicit evaluator dependence. Its parent comparison report
recognizes a replacement judge as a separate evaluation condition. Therefore a
genuinely unresolved native route can motivate a prospectively declared
alternative, with endpoint-specific qualification, the same reference/rubric
handling, full Multi coverage and clear changed-evaluator reporting. Smaller
size, lower cost or easier passing controls alone do not justify substitution.
Such a condition cannot inherit native-judge or published-score equivalence;
citation-only results, abstention-only outputs or a partial family cannot satisfy
the quality endpoint. No alternative is selected or authorized as qualified here.

## Local evidence and verification scope

At `2026-11-06T22:14:48.325269Z`, no Scholar/R2E/Prometheus/AttrScore-named direct
children were found under project `data/raw`, `data/cache`, `data/benchmark`, or
`E:\projects_data\drug_target_agents_data\{models,raw}`. This bounded filename
inspection is not a global absence proof. Hardware observations are retained in
[SC06's note](SC06-FEASIBILITY-NOTE.md): RTX 5070 Ti 16,303 MiB total and
34,188,681,216 B physical RAM, observed before this note. No live process changed.

Freshly hashed retained inputs (all paths relative to `D:\Projects\drug_target_agents`):

| Path | SHA-256 |
|---|---|
| `planning/TETHER Semantic Capability Execution Plan 2026-11-06.md` | `085ed3bb65c995db134946ad16773e25196f36933a800b7dfa4772c9da9ebbb7` |
| `planning/review-assets/tether-semantic-20261106/synthesis-feasibility/FEASIBILITY.md` | `c40f183479f89cc76856252c40293a7ed7e3c75dd7441f61505f843d6782c58f` |
| `planning/review-assets/tether-semantic-20261106/synthesis-feasibility/PUBLIC-METADATA.json` | `8226e5357de9894b1dbfa8e96393adc4ff8c2b286ec7493385510866e492fabb` |
| `planning/review-assets/tether-semantic-20261106/sc04/SC06-FEASIBILITY-NOTE.md` | `926286057b4037e4b5fe306d6fd8ef91835d1b11a4c8a97ef1d75715a415fb9e` |

The authoritative plan requires all chosen released cases, the stated quality
and citation endpoints, and a qualified explicitly identified judge. Exact
published-judge reproduction and a declared changed-evaluator condition have
different comparability. This clarification corrects an overstrict implication
in the earlier note; it neither activates SC07 nor reduces its required coverage.
