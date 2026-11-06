# SC06 forward feasibility - not activation or an execution freeze

Read-only follow-up on 6 November 2026 while SC04 is active. No dataset, weights,
package, model inference or experiment was acquired, installed or executed.
SC06 must follow completion of SC04 and SC05. This note preserves the full
declared-family requirement; it does not replace it with a sample or smaller judge.

## Scope and data gate

The concrete recommendation remains **every record in the pinned released
`data/asqa_eval_gtr_top100.json` family**. The expected count is 948, supported by
a reproduction log in the official repository, but the archive has not been
acquired or counted locally. Do not hardcode 948 as verified or replace the family
with 948 sampled records. The exact ordered IDs, uniqueness, missing records and
GTR/DPR/oracle joins must be established from original bytes before the execution
freeze. [Official issue 4](https://github.com/princeton-nlp/ALCE/issues/4).

Pinned archive metadata:

- Repository revision: `334fa2e7dd32040c3fef931a123c4be1a81e91a0`.
- `ALCE-data.tar`: 451,297,280 bytes; upstream LFS SHA-256
  `eda837bf659a91b3648dc6e7ab6b17197664d93593857e8fdf3800b6aa6a98f0`.
- Source code revision: `246c476a4edfc564266b7346b6e29ef4861ae937`.

The official archive remains listed publicly, but its dataset viewer cannot
establish the split/count and there is no dataset card. A successful listing is
not a completed download or a rights determination. No archive/model asset was
found in the inspected project raw/cache directories. The E: model root contains
the existing Qwen 14B package only; this was a bounded location check, not a global
filesystem inventory. [Pinned archive listing](https://huggingface.co/datasets/princeton-nlp/ALCE-data/tree/334fa2e7dd32040c3fef931a123c4be1a81e91a0),
[dataset card/viewer](https://huggingface.co/datasets/princeton-nlp/ALCE-data).

## Input mapping and answer producer

The official example chooses two demonstrations and the first five GTR passages.
Its historical producer is GPT-3.5-turbo-0301. A local Qwen condition changes that
producer and must be labelled accordingly; it can still use the complete native
task and native metrics. [Pinned configuration](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/configs/asqa_turbo_shot2_ndoc5_gtr_default.yaml).

Use the released top 100 retrieval pool, avoiding a new Wikipedia index and its
retrieval-model dependency. Oracle ordering is evaluator-derived and cannot enter
the ordinary primary route. [Release instructions](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/README.md).

Recommended preparation requirements:

1. Inventory safe archive members and original row locators. Preserve every
   question, full original top 100 passage order, title/text bytes and available
   document identifiers. If stable passage IDs are absent, use an archive/member/
   row/document-index locator with a fingerprint rather than inventing a Wikipedia
   revision or paragraph coordinate.
2. Derive separate question/source and evaluator-reference views. Original long
   answers, disambiguated QA pairs, annotation knowledge and oracle fields must
   remain evaluator-only. Audit the released demonstration identities/text for
   evaluation overlap before freezing their use.
3. Map displayed citations `[1]`-`[5]` to exactly the five supplied passages,
   retaining their original top 100 indices. The evaluator-facing `docs` projection
   must represent those same supplied documents. Do not accidentally score a
   citation against an unshown passage at that index.
4. Qualify the existing Qwen/runtime for free-text cited answers in a new adapter;
   SC04's MCQ grammar and 256-token settings do not establish this capability.

The original runner defaults to 300 generated tokens, temperature 0.5 and seed 42,
and can shorten available output allowance when a prompt is too long. Its default
noninteractive route trims the stored document list to the selected passages.
Preserve those facts as the historical condition. A prospective local condition
should freeze its own exact tokenizer/context/output caps and retain overlength
or truncated outputs explicitly; never silently remove demonstrations, passages,
sentences or difficult questions to complete a prefix. [Pinned runner](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/run.py).

The citation instruction asks for factual claims supported by a minimal set of
one to three sources per sentence. Retain the original instruction and selected
demonstrations with their licenses/identities; adding a sentence cap would be a
declared changed-generation condition. [Pinned prompt](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/prompts/asqa_default.json).

## Native evaluation and a boundary defect

Required native ASQA evaluation includes STR-EM/STR-EM-HIT, ROUGE-Lsum, QA-EM/F1/Hit,
MAUVE and citation recall/precision. Pin tokenizers, sentence segmentation resources,
normalization, stochastic seeds and model revisions. Citation scoring uses the
TRUE T5-XXL model in BF16, a premise/hypothesis prompt and exact decoded entailment
label, with up to 10 generated tokens. Preserve sentence and citation denominators;
empty outputs are skipped by the native citation routine and need separate
all-scheduled accounting. [Pinned evaluator](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/eval.py).

**Native boundary to test:** citation parsing subtracts one from the bracketed
integer and checks only the upper document bound. Thus `[0]` can resolve to the
last document through Python's negative indexing. This is a source-level finding,
not an executed reproduction. Qualify zero, oversized, duplicate and malformed
citations on invented fixtures. Preserve native-compatible scores and report a
separate strict citation-validity check; do not quietly patch the published metric
and retain its name. [Evaluator citation loop](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/eval.py).

The full official ASQA command requests both QA and MAUVE. Their cost must be
budgeted; skipping them because AutoAIS already runs would narrow the recommended
native evaluation. Release defaults are distinct from any deliberately qualified
changed backend. [Official evaluation command](https://raw.githubusercontent.com/princeton-nlp/ALCE/246c476a4edfc564266b7346b6e29ef4861ae937/README.md).

## Native judge: plausible offload, no demonstrated fit

The retained metadata pins AutoAIS to
`google/t5_xxl_true_nli_mixture@aa6cfe1dd4257853bfdd772992045f41bfc14988`.
Its five source weight files total 45,492,657,356 bytes; the largest is 9,996,758,376
bytes. The prior review's index-derived BF16 tensor estimate is 22,812,037,120 bytes
(21.25 GiB), which exceeds this GPU's total memory before activations. These are
metadata/storage calculations, not loading or inference measurements.

Fresh read-only hardware observations at approximately
`2026-11-06T22:08:05+00:00`:

| Resource | Observed value |
|---|---:|
| GPU | NVIDIA GeForce RTX 5070 Ti; 16,303 MiB total; 14,858 MiB free at the GPU query |
| Physical host RAM | 34,188,681,216 bytes |
| Available host RAM | 15,865,110,528 bytes |
| Free D: | 1,677,770,510,336 bytes |
| Free E: | 1,682,540,056,576 bytes |

Availability varies with other work. Combined nominal RAM/VRAM is not proof of a
successful load: an FP32 shard can coexist with converted tensors, allocator buffers,
tokenizer/runtime state and activations. Current free host RAM makes naive loading
especially risky. No active model or unrelated process was stopped for this review.

The faithful first route is unchanged native BF16 weights with explicitly bounded
GPU/CPU placement and low-memory shard loading. Unload the answerer between
generation and evaluation. If necessary, qualify state-dictionary/disk offload or
a separately hashed derived BF16 representation whose tensors equal the native
casts. Neither changes the logical judge to a smaller model. Accelerate documents
GPU/CPU/disk placement, but that capability is not a local timing or peak-memory
guarantee. [Official large-model inference guidance](https://huggingface.co/docs/accelerate/usage_guides/big_modeling).

Quantization is not the first native-equivalent route. INT8/INT4 or replacing
T5-XXL with a smaller model changes the judge; it cannot silently discharge SC06's
native scoring requirement. Any changed evaluator requires explicit naming,
fixed-input comparison and limitations. Qualify token IDs, exact inputs/outputs,
entailment decisions, numeric stability, long premises, load peak and sustained
throughput before freezing complete-family budgets.

Additional retained model metadata: RoBERTa QA revision
`02bcd9fab9c9d84a346389074e0bcdf770c5141b`, 1,417,412,145-byte model; GPT2-large
revision `32b71b12589c2f8d625668d2335a01cac3249519`, 3,247,202,234-byte native PyTorch
file. Choose one weight format each and separate model lifetimes. The combined
original ALCE/AutoAIS/QA/GPT2 payload estimate is 50,608,569,015 bytes before
tokenizers, packages, expanded data, converted weights, offload files and outputs.
Provisioning100-150GB is a scenario, not a measured requirement or authorization
to download now. Existing drive capacity is adequate for that scenario.

## Full-family time and acceptance

With 948 records, one answer condition requires 948 generations. Raw and checked
identical outputs can share exactly bound semantic evaluations; this does not
create additional independent samples or a harness accuracy gain.

The prior feasibility calculation allows up to seven NLI evaluations per sentence
for a three-citation joint/individual/leave-one-out pattern. Eight sentences across
948 answers implies 53,088 NLI evaluations per answer condition. At 1/10 seconds
per evaluation, this is 14.75/147.5 hours, excluding generation, other metrics and
loading. Those are arithmetic scenarios, not throughput measurements or guaranteed
sentence bounds. Actual native branching and exact duplicates may reduce work.
Cache only identical frozen model/prompt/input computations with retained joins.

Before actual execution, freeze the full source family and endpoint set, qualify
the producer/judges on invented controls, and estimate from measured worst-case
length/load/throughput. After answers seal, enumerate sentence/citation work
without reference scores to establish the exact evaluation schedule. Timeouts
retain all incomplete cases; they do not justify declaring a completed family
from a convenient prefix. Native/scientific metric agreement, source mappings,
failure records, resource accounting and independent reconstruction remain gates.

## Rights, access and current blockers

ALCE code is MIT and the author provides a public data-download route. Its data
archive has no displayed standalone license card. The ASQA source repository has
Apache-2.0 code, but that is not by itself a verified grant covering every bundled
annotation and third-party passage. Wikipedia passage attribution and applicable
snapshot terms must remain explicit; do not bundle all source text under the
project's code license. [ALCE code license](https://github.com/princeton-nlp/ALCE/blob/246c476a4edfc564266b7346b6e29ef4861ae937/LICENSE),
[ASQA source repository](https://github.com/google-research/language),
[ASQA release documentation](https://github.com/google-research/language/tree/master/language/asqa).

The retained AutoAIS model metadata reports Apache-2.0; the new browser fetch of
its pinned README returned a tool retrieval error, not an observed authorization
denial. Do not relabel that as a credential requirement. No genuine authentication
or manual-configuration blocker is demonstrated now. Actual transfers, archive
rights/contents, native Windows loading, memory limits and complete-family runtime
are still unqualified. No smaller family or judge is substituted for those gates.

## Local evidence and hashes

Workspace root: `D:\Projects\drug_target_agents`. Freshly hashed retained files:

| Exact relative path | SHA-256 |
|---|---|
| `planning/TETHER Semantic Capability Execution Plan 2026-11-06.md` | `085ed3bb65c995db134946ad16773e25196f36933a800b7dfa4772c9da9ebbb7` |
| `planning/review-assets/tether-semantic-20261106/synthesis-feasibility/FEASIBILITY.md` | `c40f183479f89cc76856252c40293a7ed7e3c75dd7441f61505f843d6782c58f` |
| `planning/review-assets/tether-semantic-20261106/synthesis-feasibility/PUBLIC-METADATA.json` | `8226e5357de9894b1dbfa8e96393adc4ff8c2b286ec7493385510866e492fabb` |

Archive/checkpoint revisions, byte sizes and LFS hashes are retained metadata,
not local payload verification. Official source URLs above were read in this
follow-up, without saving new dataset/model payloads. SC06 remains unstarted.
