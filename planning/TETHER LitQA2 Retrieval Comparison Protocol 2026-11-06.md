# TETHER LitQA2 retrieval comparison — SC04 prospective protocol

Status: implementation and fictional qualification. **Production is not frozen
or dispatched.** The final frame must pin this protocol, qualified code, model,
runtime, source policy, all 199 task identities, schedule and limits before
new benchmark inference. SC03 is complete. SC04 is incomplete.

## Question and schedule

Does question-only query expansion or relevance reranking improve eligible
source retrieval and scientific multiple-choice answering under common caps?
Execute all original 199 public LitQA2 questions, preserving their released
identities, task projections and fixed visible choice order. No development
answer is permitted in a query, retrieval, ranker or answer request. This is a
repeated, exposed public evaluation, not a private holdout.

| Arm | Search | Passage selection | Logical maximum model calls |
|---|---|---|---:|
| L/O | Original question-only lexical rule | Lexical overlap | 1 answer |
| E/O | Question-only expansion | Lexical overlap | 1 expansion + 1 answer |
| L/R | Original lexical rule | Model ranking | 1 rank + 1 answer |
| E/R | Same expansion result as E/O | Model ranking | 1 expansion + 1 rank + 1 answer |

Every arm has an equal ceiling of three model calls and 768 generated tokens,
two metadata requests and three article attempts per question. Unused allowance
is not consumed by dummy calls. Share expansion across E arms, retrieval within
each query branch, and rank results only where their entire input identity is
identical. Attribute shared costs to each consuming arm and separately report
unique physical calls; summing logical costs is not total hardware usage.

The archived 12/199 baseline remains a historical control. New acquisition time
and shared balanced allocation differ from that original first-query-priority
implementation; do not attribute that whole contrast to query expansion.

## Inputs, queries and sources

1. Reverify the original release, task projections, original-order 199 IDs and
   model/runtime acquisition receipt. Preserve all existing sealed artifacts.
2. Query generation sees exactly `{id, question}`. It never receives choices,
   annotation DOIs, key passages, reference answers or earlier scores.
3. Expansion emits exactly two lists of one to four distinct search terms.
   Each term has at most 80 ASCII letters, digits, spaces or hyphens. The first
   list is serialized as quoted terms joined with AND; the second uses OR.
   ASCII transliteration is explicit. Generated operators/URLs/DOIs cannot
   become an unvalidated search expression. Terms are treated as literal data.
4. Both search strategies use the common date, OA and CC-BY/CC0 filter. Exact
   cutoff and acquisition timestamps enter the freeze. At most ten metadata
   hits per query are retained. No assumed subscription or publisher scraping.
5. Alternate qualified candidates from the two query lists by rank and
   deduplicate PMC identity, then attempt the first three distinct articles.
   This allocation is shared across every new arm. Retain unsuccessful
   searches, duplicates, metadata/rights rejection and cap exclusions.
6. Validate metadata and article-specific XML identity and reuse rights before
   extraction. Keep original bytes, HTTP receipts, query provenance and exact
   source-to-paragraph mappings. Continue using the existing extraction scope:
   abstract/body paragraph text, excluding image content, supplemental files
   and table cells without paragraph markup. HTTP success alone is insufficient.
7. Seal both lexical and expanded retrieval branches before any final answers.
   A fresh acquisition can discover different papers; equal source eligibility
   does not mean equal realized documents.

Source restrictions are not negative biological evidence. Report unknown DOI,
license/identity conflicts, missing full text, parsing failures and unavailable
sections explicitly. The supplied-source diagnostic below cannot fill ordinary
retrieval gaps behind the scenes.

## Raw passages and ranking

Segment retained paragraphs into the same contiguous, UTF-8-bounded chunks of
at most 1,000 bytes used by the archived selector. Rank by unique question-token
overlap and original order. Build a common candidate pool of at most 16 complete
chunks and 10,000 text bytes. No option text is used for this pool.

O selects from that pool in lexical order. R receives question text and the
same complete pool, with stable short rank IDs. It must return an exact
permutation, with no duplicate, unoffered, missing or invented item. Both select
at most eight raw chunks and 8,000 bytes for answering. Preserve original
paragraph hashes, character ranges and source identities; a rank ID never
replaces the scientific citation identity. No generated summary or new evidence
text is introduced. Empty pools have an explicit no-ranking-call disposition.

The entire payload must fit the 14,000-byte prompt limit and exact tokenizer
reservation inside the 16,384-token context with output headroom. Unicode JSON
escaping and system instructions consume this allowance. Overcapacity is an
explicit failure, never silent text truncation.

## Model, failure and budget policy

Use the existing receipt-pinned Qwen2.5-14B-Instruct Q4_K_M and llama.cpp Vulkan
runtime. The same final MCQ prompt, model, option order and settings apply to
all arms and the supplied-source condition. Temperature zero, seed20261106,
maximum256 generated tokens per call, no implicit retries. A prompted local
ranker is not a trained cross-encoder or a reproduction of PaperQA2/Self-RAG.

Fictional qualification exposed an incorrect abstention under the archived
answer prompt. A prospective common prompt now presents the indexed options
once and explicitly permits direct passage-supported facts in invented examples.
The output contract and visible option order are unchanged. This prompt differs
from BG04, so the old baseline is additionally a historical prompt control.
The original supported-orb fixture still fails. The expanded set demonstrates
four other supported answers and three appropriate abstentions, not universal
reliability or a demonstrated prompt improvement. Keep this variant fixed for
every new arm; do not optimize it on benchmark answers.

Before production, execute fictional expansion, useful-passage/distractor
ranking and supported/unsupported MCQ controls. Keep actual semantic failures
separate from valid grammar, transport and replay. Do not use any of the 199
answer keys to tune prompts or thresholds. Preserve every qualification attempt.

Declare lexical fallback after an expansion or ranking parse/operational
failure; record its reason and consumed or uncertain call reservation. There
is no second model attempt. Invalid expansion uses the lexical query rule and
records that the intended intervention was unavailable. Invalid ranking uses
the original pool order. Infrastructure/integrity or interrupted-owned-process
failures stop the affected stage rather than silently continuing on untrusted
state. Fallback answers stay in the all-scheduled denominator with explicit
intervention-availability flags; also report available-intervention subsets.

Calls have a120-second absolute deadline including tokenization, inference and
retention. The provisional whole-stage ceilings are two hours for ordinary
collection, six hours for inference and two hours for finalization/reconstruction;
qualification must establish adequate headroom before these are frozen. Child
supervision and owned-process cleanup are mandatory. Journal reservations,
dispatch, bytes, usage and terminal outcomes as they occur. A timeout is never
permission to repeat a potentially executed call.

Ordinary collection has at most1,990 HTTP attempts, with1MiB metadata,
2MiB article and8MiB per-question/branch response caps. The ordinary factorial
schedule has at most1,393 unique model generations and356,608 generated tokens.
Record actual tokens, calls, wall/CPU time, memory measurement boundaries,
source/selected/output bytes and uncertain-transfer reservations separately.
Provider spending is$0; energy and labor are not thereby zero.

## Separate supplied-source diagnostic

After ordinary sources are sealed, resolve the190 distinct annotated DOI
identities through the qualified metadata route. The resolver receives only
the diagnostic question-to-DOI projection, no correct choice/key passage.
At most one metadata and one full-text attempt per DOI (380 HTTP attempts),
unless the exact already-captured article is reused with full receipt and
identity/rights verification. Preserve unavailable/ambiguous/restricted cases.

Use the same question-only lexical passage selector, final answer producer and
context caps for all199 questions. Supply annotated papers, not the annotated
key passages. This tests privileged paper identity; it is not ordinary search
performance or proof of answer entailment. At most199 additional generations
and50,944 generated tokens. Publish both all199 and eligible-source denominators.

## Scoring and acceptance

Freeze evaluator inputs separately from solver inputs. Reuse the released
native accuracy, substantive precision and coverage definitions; operational
failures, explicit unsure answers and policy rejections remain distinct.
Report all four arms and supplied-source diagnostics with exact counts, native
accuracy, correct-and-admitted yield and raw/checked pairing. The harness's
provenance checks do not establish semantic support.

Report annotated source availability and recall by question and DOI pair;
selected source identities; bounded text/extraction coverage; rank changes;
parse/operational/fallback counts; and actual/logical costs. Annotation paper
matching alone cannot be called decisive-passage recall. The current annotation
projection has205 question–DOI pairs, with193 single-source and six two-source
questions; reverify those counts before use.

Use paired question outcomes for the factorial contrasts. Retain dependence
groups for shared annotated publications and report uncertainty at that level
where constructible. Do not fit a selective threshold on the199 answers.
Independent reconstruction must start from original task/source bytes and
retained native responses, recompute allocation/pools/ranks/answers/usage and
native scores, and detect added or omitted events and outputs. Claims about
scientific improvement must follow observed performance, not successful replay.

Completion requires all199 cases accounted for in each declared arm, immutable
source and model bindings, qualified controls, resource/failure accounting,
independent reconstruction and a retained results report. A partial collection,
all-abstention shortcut or fictional smoke does not complete SC04. SC05–SC09
remain subsequent requirements of the active goal.
