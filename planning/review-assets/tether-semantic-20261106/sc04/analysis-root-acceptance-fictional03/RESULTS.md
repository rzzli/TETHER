# TETHER SC04 — fictional analysis qualification

**Fictional controls only. These are not benchmark performance results.**

The source-inclusive analysis and this root acceptance pass their declared technical checks. Scientific and clinical validity remain unestablished.

## What was compared

| Arm | Retrieval | Passage selection |
|---|---|---|
| L/O | Question-only lexical queries | Lexical selection |
| E/O | Model-expanded queries, with declared fallback | Lexical selection |
| L/R | Question-only lexical queries | Model ranking, with declared fallback |
| E/R | Model-expanded queries, with declared fallback | Model ranking, with declared fallback |
| Supplied source | Privileged annotated paper identities | Lexical selection |

The supplied-source diagnostic is not ordinary retrieval. All five arms use the same frozen answer producer. The older baseline has different acquisition time, prompt and allocation; it is a historical control.

## Answers across the full schedule

| Arm | Correct | Correct and admitted | Substantive answers | Raw accuracy | Substantive precision | Unsure | Operational failures | Rejected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L/O | 1/2 | 1/2 | 1/2 | 50.0% | 100.0% | 1 | 0 | 0 |
| E/O | 1/2 | 1/2 | 1/2 | 50.0% | 100.0% | 1 | 0 | 0 |
| L/R | 1/2 | 1/2 | 1/2 | 50.0% | 100.0% | 1 | 0 | 0 |
| E/R | 1/2 | 1/2 | 1/2 | 50.0% | 100.0% | 1 | 0 | 0 |
| supplied | 1/2 | 1/2 | 1/2 | 50.0% | 100.0% | 1 | 0 | 0 |

Operational failures remain in the accuracy and coverage denominators. An explicit unsure response is distinct from a malformed or unavailable result. Admission verifies the declared source obligations, not answer entailment.

## Paired effects

1 publication components group questions sharing annotated papers. Each primary contrast uses 10,000 paired component-bootstrap draws when uncertainty is estimable; question-level intervals are retained as sensitivity analyses.

| Contrast | Raw accuracy change (percentage points) | 95% component interval | Correct-and-admitted change | 95% component interval |
|---|---:|---|---:|---|
| expansion at lexical | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |
| ranking at lexical | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |
| combined vs lexical | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |
| interaction | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |
| marginal expansion | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |
| marginal ranking | +0.00 | undefined (one publication group) | +0.00 | undefined (one publication group) |

These are exploratory effects on an exposed development set. No threshold was fitted to these evaluated answers. All six contrasts are reported; intervention-available subsets are secondary and retained in RESULTS.json.

## Annotated paper coverage

The schedule contains 2 question–paper pairs and 1 distinct annotated papers. Identity matches do not establish decisive-passage recall or scientific support.

| Arm | Retained pair matches | Candidate-pool pair matches | Selected pair matches | Questions with any selected match | Questions with all annotated sources selected |
|---|---:|---:|---:|---:|---:|
| L/O | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| E/O | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| L/R | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| E/R | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| supplied | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

## Failures and interventions

| Arm | Answer status counts | Expansion failures | Ranking failures | No selected passage |
|---|---|---|---|---:|
| L/O | {'completed': 2} | {} | {} | 0 |
| E/O | {'completed': 2} | {} | {} | 0 |
| L/R | {'completed': 2} | {} | {} | 0 |
| E/R | {'completed': 2} | {} | {} | 0 |
| supplied | {'completed': 2} | {} | {} | 0 |

Diagnostic source decisions: `{}`. These counts describe resolution decisions, not mutually exclusive questions. Missing collection is not biological absence.

The frozen answer pipeline cannot gracefully finalize every over-capacity admission case: an overlong payload can abort before a model-cell capacity record. A completed run has passed its declared path; no broader capacity guarantee follows.

## Physical resources

| Run | Generation calls | Input tokens | Output tokens | HTTP attempts | Measured response bytes | Unknown-transfer upper bytes | Worker wall seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| primary | 14 | 3773 | 433 | 12 | 3836 | 0 | 46.109 |
| supplied | 2 | 619 | 86 | 2 | 815 | 0 | 14.078 |

Provider spending: **$0**. Shared expansion, ranking and collection can appear in multiple logical arm totals; those totals must not be summed as physical cost. Token reservations and measured usage are separate. Energy, GPU memory and aggregate machine memory were not measured.

Analysis worker: 13.000s; process peak working set: 162,369,536 bytes. This is a process peak, not whole-machine RAM.

## What acceptance establishes

- Externally anchored analysis receipt: `acfd87731d44ba1b632bd8b33c4f85ecf8547e256f5dd9300f3047bc94570816`.
- 425 sealed inventory entries and 49 journal chains checked.
- 130 qualified analysis source files matched.
- Original choices, reference keys, source annotations, complete denominators, all-five-arm accounting and paired arithmetic reconcile.
- The pinned analysis CLI performed raw native/source/lineage reconstruction. Root acceptance rechecks its bytes, joins and arithmetic.

**Not established:** untouched-test generalization, independent biological correctness, clinical benefit, calibrated clinical probabilities, or superiority to the original Virtual Biotech system.

[Acceptance record](ROOT-ACCEPTANCE.json) · [Reproduction instructions](REPRODUCE.md)
