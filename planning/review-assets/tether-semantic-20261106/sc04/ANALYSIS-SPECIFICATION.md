# SC04 analysis specification

Frozen before primary answer generation, while primary source collection is
running. This supplements the retained comparison protocol; it does not turn
the repeatedly exposed public development set into an untouched holdout.
No primary answer scores were inspected to choose these analyses.

## Complete denominators

Analyze the original199 question IDs, in original order, for every primary arm
L/O, E/O, L/R, E/R and the separately labelled supplied-source diagnostic.
Do not replace missing cases or substitute a later benchmark release. Report
scheduled, entered, complete, failed and unexecuted cases separately. A partial
phase may receive a recovery report but cannot close SC04's completion gate.

For each arm report both counts and fractions:

- Native raw accuracy: correctly selected released answer /199. Malformed,
  unavailable and unexecuted cases are incorrect in the all-scheduled denominator.
- Raw substantive coverage: valid non-unsure answers /199.
- Raw substantive precision: correct answers /valid non-unsure answers. Return
  null when no substantive answer exists; never silently report zero precision.
- Explicit unsure, parse/capacity/infrastructure failure and unavailable-input
  counts separately. An invalid result is not an explicit unsure answer.
- Correct-and-admitted yield: correct substantive answers accepted by the
  provenance check /199; corresponding checked coverage and precision.
- Raw correct answers rejected by policy, raw wrong answers accepted, and
  unchanged raw/checked answers. Provenance acceptance is not entailment.

The old199-question result is a historical baseline with different acquisition,
allocation and prompt. Do not attribute its difference to expansion/ranking alone.
The four new arms share the frozen answer producer and declared maximum budgets.

## Paired contrasts and uncertainty

Retain per-question paired outcomes. Report all of these contrasts, regardless
of direction: E/O minus L/O; L/R minus L/O; E/R minus L/O; the interaction
`(E/R - L/R) - (E/O - L/O)`; the marginal expansion effect averaging its two
ranking settings; and the marginal ranking effect averaging its two query
settings. Compute these for raw accuracy and correct-and-admitted yield.
Report precision/coverage separately so abstention cannot masquerade as accuracy.

Use10,000 deterministic bootstrap replicates with seed20261106. Questions sharing
any annotated DOI belong to the same connected component; resample those
components with replacement and keep paired arm outcomes together. Recompute
the ratio using the total number of questions in each replicate. Retain component
membership, sizes and counts. Also report ordinary paired-question bootstrap
intervals as a labelled sensitivity analysis. Use percentile95% intervals;
do not select a contrast because its interval excludes zero or describe this
exploratory family as confirmatory multiple-testing-controlled evidence.

No confidence threshold is fitted to these199 answer keys. Qualitative review
examples must state their selection rule and cannot change the primary outputs.

## Source access and evidence use

Reverify205 question–DOI pairs and190 unique annotated DOIs before scoring.
Report annotated-paper matches at retained-article, candidate-pool and selected-
passage levels, with all199 and all205 denominators. Also report the number of
questions for which all annotated papers, or any annotated paper, are present.

Use original metadata and article-front DOI fields for identity reconciliation.
Keep missing DOI, conflicting metadata/XML DOI and unresolved identity separate;
do not silently replace an incompatible metadata identifier. Annotated-paper
matching is not decisive-passage recall or proof of answer support. Record the
fixed extraction limits on figures, tables and supplements.

The supplied-source diagnostic reports exact DOI resolution, access/license
exclusions, truncated/ambiguous metadata, failed fulltext access, retained paper
and selected-text coverage. Report all199 accuracy and the eligible-source subset
separately. Privileged paper IDs are never counted as ordinary search success.
No annotation key passage enters either source selection or answering.

Report whether ranking changes selected passage membership/order, how many
correct answers become wrong or wrong become correct, and expansion/ranking
codec fallback rates. Available-intervention subsets are secondary to the full
declared cohorts. Do not infer causal error attribution from overlapping flags.

## Resources and reconstruction

Distinguish physical calls and transfers from logical per-arm charges. One
expansion is physically shared by E/O and E/R; each arm includes that call in its
logical resource accounting. Source collections are also shared between arms.
Do not sum logical arm totals and call the result physical spending.

Retain native token counts, reservations, unknown-transfer upper bounds, response
bytes, raw and selected text bytes, output bytes, stage/worker/server timing and
CPU/RAM samples. Report missing GPU/energy measurements as unknown. Provider
spending remains$0, which does not imply zero electricity or labour cost.

Independent analysis must reconstruct native choices and usage from original
responses and verify case joins against the released projection, then check
source identity and raw text against captured originals. The maintained replay
is necessary but is not itself the independent scientific scorer. Retain all
known fictional semantic failures and every failed engineering attempt.
