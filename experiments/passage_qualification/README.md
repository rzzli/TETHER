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
