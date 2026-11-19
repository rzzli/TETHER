# Real-text retrieval and numerical claim attribution

These exposed development experiments use the existing TETHER rankers, the generated-response adapter, and an isolated research checker. A04 measures the retrieval of designated passages. A05 asks whether a specific numerical proposition is supported by the passages the model actually cites. A correct quotation can accompany an incorrect value.

## A04

Four cached CC BY Europe PMC articles supply the first 40 body paragraphs each. The roster pins original XML bytes. Preparation matches the download receipts, article identity, search metadata and XML permissions, then records authors, DOI where available, source URL and paragraph locator. The 85 remaining body paragraphs fall outside this selection. Original articles and actor files remain local. The bundled references identify whole paragraphs in their whitespace-normalized UTF-8 representation.

The pilot contains 20 single-paper questions, four cross-paper questions and six paired controls with the required article removed. The rankers share the source universe for each question, receive zero answer options, and can offer at most two records within 12,000 canonical request bytes. The reference designates particular supporting passages. Other passages could contain equivalent information. The six source-withheld questions have different candidate pools than their answerable counterparts.

| Real-text development measure | BM25 | Three-term overlap |
|---|---:|---:|
| Answerable questions with any designated passage | 24/24 | 21/24 |
| Answerable questions with every designated passage | 22/24 | 18/24 |
| Cross-paper questions with both designated passages | 2/4 | 0/4 |
| Designated complete paragraphs retrieved | 26/28 | 21/28 |
| Source-withheld questions receiving distractors | 6/6 | 5/6 |

All 60 rankings replayed under the contemporary research case. Across the 30 BM25 queries the ranker used 87,550 canonical bytes, versus 91,606 for the comparator. There were 28 unofferable query–paragraph appearances in each arm. All four selected articles were accessible and permitted. The broader archive's acquisition success rate cannot be inferred from this deliberately selected roster. An earlier pass used a fictional case envelope. Correcting its date and task preserved all 60 ordered passage selections and changed the byte totals. No answer generation or fallback occurred in either retrieval arm.

From the repository root with the engine installed, supply the retained Europe PMC collection and a fresh output directory. Preparation, ranking and scoring run as separate commands. Ranking reads the frozen actor file. Scoring opens the evaluator reference after the rankings exist.

```text
python -m experiments.passage_qualification.pilot prepare OUTPUT --collection COLLECTION
python -m experiments.passage_qualification.pilot rank OUTPUT
python -m experiments.passage_qualification.pilot evaluate OUTPUT
```

To verify a retained A04 run, reconstruct its inputs from the original XML,
replay the entire ordered schedule, and compare the resulting evaluation bytes:

```text
python -m experiments.passage_qualification.verify_retrieval OUTPUT COLLECTION
```

The frozen scorer tallies its two named arms and can ignore surplus rows from
another arm. The verification command checks every row against fresh rankings.
It preserves recorded timings for the score comparison. Elapsed time itself
cannot be independently reproduced.

## A05

The first batch used eight study-specific numerical questions and four source-withheld controls in both benign and hostile conditions. The conditions shared the question, source paragraph and model. A separate editorial note supplied either neutral text or an untrusted instruction. The model had no tools. Proposals were replayed through the adapter and checked against case-bound quotations. The research checker interpreted each complete numerical clause, including subject, measure, comparator, value and units. Independent source references scored the answers. Generated text had no write authority in the production selection ledger.

| First frozen batch | Benign | Hostile |
|---|---:|---:|
| Answerable cases yielding a supported correct answer | 2/8 | 4/8 |
| Scheduled cases resolved correctly after checking, including warranted abstention | 6/12 | 8/12 |
| No-answer cases where the model itself abstained | 4/4 | 3/4 |
| Source-correct percentage answers withheld by the strict format | 1 | 2 |
| Accepted answers off reference | 0 | 0 |

All 24 first attempts replayed. The batch took 89.4 seconds, consumed 20,933 input and 4,677 output tokens, and cost $0 in provider charges. **The first method failed** its fixed minimum of four useful answers per eight answerable cases in each condition. Seven of the 16 answerable attempts returned empty claims. Of ten literal-valid proposals, nine expressed a correct answer in ordinary numeric notation. Three of those nine included a redundant percent sign and were withheld. The tenth quoted a real percentage as the participant count of a different study. The checker withheld that proposal too. A reject-all policy would have avoided this error and delivered zero useful answers.

The offline scorer initially passed an argument positionally to a keyword-only API. The corrected scorer replayed the retained responses. The execution and decision thresholds stayed fixed. The strict-form and unit-aware reference counts are reported separately.

**Public comparison.** A receipt-checked replay of 1,500 cached MultiVerS claim–abstract outputs on 300 exposed SciFact development claims found explicit document annotations on 159 pairs. On those pairs the predicted label matched on 102, and the label plus at least one whole annotated rationale matched on 36. The model predicted support for 14 of 46 explicitly contradictory pairs. The remaining 1,341 pairs lacked a document-specific annotation. These counts describe a separate published-benchmark solver and measure a broader attribution problem than the numerical checker.

**Redesigned qualification.** Four other full-text papers supply eight source-linked windows. Each model input contains a measurement-bearing or irrelevant excerpt, a genuine competing passage, and an editorial note. Two source-missing question pairs have a same-paper passage about a different measurement or population. The other two supply a different article. The checker permits a redundant percent sign on percentage fields. It rejects changed values, incompatible units, mixed claims and unverified source text. The deterministic extractor receives the same sources and question and supplies a usefulness ceiling for these deliberately structured tasks. The preflight independently reconstructs each excerpt and offset from the original XML and tests the real adapter and ledger boundaries.

Each model protocol permits 24 first attempts with zero retries, downloads and provider spending. The preflight makes zero model calls. A fresh batch requires its own authorization. Neither development schedule measures therapeutic efficacy, general text entailment, or agent superiority.

**The redesigned run passed the frozen A05 gate.** Each column below represents
the same eight answerable questions and four no-answer controls. Only the
editorial note changed within a pair.

| Redesigned batch | Benign note | Hostile note |
|---|---:|---:|
| Supported correct answers on answerable questions | 8/8 | 8/8 |
| Model abstentions on no-answer questions | 4/4 | 4/4 |
| Unsupported claims accepted | 0 | 0 |
| Source-correct proposals rejected | 0 | 0 |
| Observed private-reference disclosures | 0 | 0 |

All 24 first attempts replayed. The run took 108.9 seconds and used 21,097
input and 5,511 output tokens with zero retries and $0 provider spending.
A separate check reconciled all 24 dispatch journals and raw responses with
the scoring records and traced every accepted value to the source XML.
All 14 adapter controls passed. The deterministic extractor also answered
16/16 and abstained on 8/8 across conditions. This qualifies the configured
model and checker for the named study measurements on these development cases.
The two batches used different papers, so the scores cannot attribute an
improvement to any one design change.

The retained protocol SHA-256 is
`65230b47b8cd99ce2e68ac89cd329a0733286036e4b9e591fe2ffd36a3b06810`.
The run report and scored evaluation have SHA-256 values
`2277258b17137ca29baed833335ffa873b69efd3ebe47d12e72f627775c2a298` and
`df4232d18fbf45f04c528819bc7ac96aea334b8378556a93684c9a3bf8784130`.

To reproduce the redesigned preflight from this local collection and the first
frozen batch, select a fresh directory. The first protocol supplies the pinned
local model/runtime identities. Preflight checks run without opening the model.

```text
python -m experiments.passage_qualification.excerpts prepare COLLECTION FIRST_FREEZE NEW_FREEZE
python -m experiments.passage_qualification.preflight NEW_FREEZE COLLECTION
```

The actor receives the article label, literal excerpt and editorial note.
The private reference file and support checker are read by the evaluator.
The deterministic comparison uses predeclared measurement names and parsing
rules specific to the selected articles. It establishes that the offered
material can answer the questions. A model reaching the same answers would
establish finite reporting capability on these tasks. A claim that a model
improves on extraction would require a different comparison.

Authorized executions use the `excerpts execute` command with the frozen
directory, local assets directory and exact protocol SHA-256. It reserves one
attempt directory and reaps the local process on exit. Use the `audit` module
with the freeze directory, receipt-bound SciFact primary output directory,
development references JSONL and a fresh assessment directory to score the
retained responses without making another model call.

## Matched extraction comparison on eight additional papers

Each paper contributes two numerical questions with a supporting passage and
one repeat question with that passage withheld. Every case has two nonempty
paragraphs from its own paper. The model and deterministic extractor receive
the same question, text and span IDs. Some passages contain several
measurements or populations. The question specifies the requested field and
context and supplies zero answer choices.

The extractor uses one rule across papers. It looks for the question's context
terms in each offered passage, then looks for the field terms within five words
of a number in the same sentence. It requires exactly one candidate value and
one cited source. The question and offered passages are its only inputs.
The model uses the same cached Qwen2.5-14B-Instruct Q4_K_M setup as the A05
redesign, at temperature zero. Both methods earn credit for one correctly
reported number with the requested unit and a source-linked supporting quote.
A well-formed empty answer earns abstention credit on withheld cases.
Malformed responses and unsupported attempts stay in the scheduled denominator.

The papers were cached in the LAB-Bench collection. The freeze records an
identifier scan of retained prior evaluation rosters, actor inputs, requests
and exchanges. This measures prior project use visible in those records.
The questions and selected passages were constructed for this comparison.

The freeze uses the cached article collection, previous A05 protocol with
checked model asset identities, prior exposure audit, and source and question
roster in this directory. The local freeze contains the exact actor requests,
evaluator references, source hashes and protocol. The `verify` command
reconstructs the actor, references and source inventory from the original XML
and metadata. The offline `score` command checks each dispatch journal,
replays saved responses and applies the same scoring rule to both methods.

```text
python -m experiments.passage_qualification.matched_experiment prepare COLLECTION PREVIOUS_PROTOCOL EXPOSURE_AUDIT FREEZE
python -m experiments.passage_qualification.matched_experiment verify FREEZE COLLECTION --sha256 PROTOCOL_SHA256
python -m experiments.passage_qualification.matched_experiment score FREEZE COLLECTION NEW_REPORT --sha256 PROTOCOL_SHA256
```

| Frozen result | Qwen2.5-14B | Deterministic extractor |
|---|---:|---:|
| Supported answers, all answerable questions | **16/16** | **6/16** |
| Supported answers, counts | 7/7 | 5/7 |
| Supported answers, percentages | 9/9 | 1/9 |
| Warranted abstentions, supporting paragraph withheld | **8/8** | **8/8** |
| Wrong or unsupported responses | 0 | 0 |

The model supplied ten supported answers where the extractor abstained. Those
gains spanned six of eight papers. Both methods answered the other six and
abstained on all eight withheld controls. The 24 cases share eight articles
and include eight repeated questions. This is a descriptive result on a
purposive sample and one lexical comparator. It measures interpretation of
supplied paragraphs. Search and upstream ranking were outside this comparison.

The freeze found no PMCID or DOI matches in 6,765 retained project artifacts.
A follow-up search found no matches for 286 sampled 12-word passages in 6,763
prior input or exchange files. All 24 model attempts replayed with zero retries,
30,128 input tokens, 5,326 output tokens and $0 provider spending. The run took
350 seconds including local asset hashing and startup. The source inventory,
actor inputs and references reproduced from the cached originals. A second
offline score run reproduced the evaluation byte-for-byte.

Protocol SHA-256
`59f97092f594e96dc2b7474c229fc37a0dd55503eef5f8e9b7494b4cee644ac9`

Evaluation SHA-256
`c1a4d65a2347c8da693e563bc48f47e00e43b5b23cca79cfdcd8011baabbc358`
