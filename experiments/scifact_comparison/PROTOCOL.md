# SC03 full-context SciFact comparison protocol

Prospective implementation specification after SC02 acceptance at commit
`6d5bc0d`. No SC03 predictions or scores have been examined. Production begins
only after fictional tests, source-inclusive preparation, runtime/controller
qualification and a separate manifest freeze pass. This document is copied into
that freeze; subsequent amendments require new labelled versions.

## Primary question and fixed comparison

Does the qualified MultiVerS `fever_sci` solver improve native SciFact verification
with exactly the five documents retrieved by the retained sparse baseline?
Use all **300** original development claims, in the retained DEV-FROZEN order,
and the exact ordered retrieval IDs for each. Claim text, titles and every
abstract sentence remain unchanged. Do not re-retrieve, select thresholds, train
or calibrate using these 300 claims. The comparator is the sealed baseline, not
a newly fitted approximation. External supervision differs between solvers.

Model and runtime: accepted SC02 checkpoint, tokenizer and dependency receipts;
FP32, batch one, eager attention, TF32 disabled, release-default
`force_rationale=false`, learned checkpoint thresholds. Maximum input length
4,096 tokens; overflow is an explicit failed pair, never silent truncation.
One model remains resident within each condition process. Each claim supplies
only its five documents rather than repeatedly scanning the entire corpus.

The worker reads a purpose-specific request file with only claim IDs/text and
document IDs/titles/sentences. It receives no reference labels, gold rationale
masks, native prefix caps or evaluation output. Access controls are trusted-code
input separation, not an OS security boundary against malicious same-user code.

## Five conditions, frozen order

Execute the complete primary condition first, then rationale-only, removal,
irrelevant-context and constructed-conflict conditions. Each schedules all300
claims and all1,500 original retrieved pairs. Retain applicability per pair;
do not drop claims without annotated retrieved evidence from reporting.

| Condition | Exact input rule | Interpretation |
|---|---|---|
| `primary` | Original claim, title and all sentences of each retained retrieved document. | Ordinary fixed-retrieval performance. |
| `rationale_only` | In each retrieved annotated document, keep the union of all annotated rationale sets, in original sentence order. Other retrieved documents remain unchanged. | Reference-informed sufficiency diagnostic; does not remove non-gold retrieval distractors or repair missing retrieval. |
| `evidence_removal` | Remove that same union from retrieved annotated documents. Other documents remain unchanged. Keep titles. | Reference-informed necessity diagnostic; titles and other sentences can still convey the claim. |
| `irrelevant_context` | Append exactly one fixed synthetic sentence to each original abstract: “In a fictional observatory, the blue telescope was stored beside an unused wooden cabinet.” | Sensitivity to this bounded unrelated addition, not general robustness to arbitrary distractors. |
| `constructed_conflict` | Append exactly one sentence to each original abstract: “For this constructed counterfactual, the following statement is false: {original claim}” | Sensitivity to explicit claim negation, not naturally occurring contradictory scientific evidence. No claim that every changed prediction is wrong. |

All transformed sentences carry an original source locator or a synthetic recipe
identifier. Deletion remaps the output's local sentence indices back to the exact
original indices. Synthetic additions have no original index or publication
identity; they cannot be admitted as genuine source sentences. Titles always
remain original. An abstract emptied by removal is `input_unavailable` for that
pair; retain its missing prediction and reason. Do not invent an NEI output or
insert placeholder prose merely to keep inference executable.

Unmodified pairs in reference-informed conditions are still executed and marked
`unchanged_no_annotated_evidence`; this measures the full fixed schedule without
mixing cached and new inference. Empty inputs count as scheduled but unexecuted
model calls. Each condition has the same per-pair length and time caps. An added
sentence that pushes an input over the cap makes that pair explicitly fail.

## Provenance and paired checking

Reconstruct the prepared corpus and query projections from the original
receipt-verified release. Join baseline retrieval through its externally anchored
receipt. Retain complete source hashes and exact document/rank/score identities.
Primary requests must be constructible without reference arguments. Diagnostic
preparation is a separate, explicitly reference-informed step.

Use the existing native SciFact shape, source-locator, request, configuration,
retrieval and candidate fingerprint checks. The external pretrained checkpoint
requires an explicit new model-provenance context: it must not masquerade as the
baseline's locally fitted sparse model or inherit fictitious fit claims. Reuse
the existing candidate checker after independently validating the new model
context; keep the historical validator and run bytes unchanged.

Primary predictions have paired raw/checked outcomes. The checker does not
rewrite predictions or judge entailment. Diagnostic synthetic text is kept in
separate experimental lineage and cannot become a genuine article citation.
All generated pair scores, local rationales, source-mapped rationales, input
fingerprints and incomplete dispositions are retained before evaluation.

## Execution and failures

Each condition uses a fresh reserved directory and a supervised owned worker.
Limits: **1,800 seconds per condition**, **120 seconds per claim** (up to five
pairs), 120 seconds per pair as an additional inner bound, one resident model,
14 GiB CUDA allocator cap and 2 GiB output allowance per condition. No paid calls.
These are ceilings, not predictions of resource use; final code qualification
must test their enforcement before production. Parent pre/post hashing and small
terminal writes are measured separately from the child deadline.

Write each pair's start, completion or failure before moving forward, and each
claim's result before recording its terminal event. Completed, active-failed,
unknown and never-started work remain distinct on timeout, interruption or
output failure. Never retry an uncertain call automatically. Length/empty-input
failures may be recorded per pair; unexpected model/runtime failures terminate
the worker with remaining schedule entries unexecuted. Any continuation requires
an explicit new frozen amendment preserving the prior attempt and exclusions.

Retain wall/CPU times, model-load interval, input tokens/bytes, completed calls,
process memory and observed CUDA allocations/reservations with their sampling
scope. Seal code, controls, effective inputs, installation authorities and
outputs; verify source stability at setup/finalization rather than rehashing the
entire model/environment for each pair.

## Analysis fixed before results

Primary endpoints are the four native metric families (document label,
document label+rationale, sentence selection and sentence label; each precision,
recall and F1), strict correct-and-admitted yield over all300, raw strict
correctness, coverage, substantive predictions, native NEI, failure and
policy-rejection counts. Report correct predictions rejected and incorrect
predictions admitted. Do not count failed execution placeholders as correct NEI.
Use the pinned official evaluator and a separate implementation to reconstruct
native sufficient statistics and strict per-case correctness.

Report primary-versus-baseline differences with a **10,000-replicate paired
component bootstrap**, seed **20261106**, percentile 95% intervals. Sample the
existing247 source/text components with replacement, including all member claims
each time; renumber duplicated claim IDs only inside the scorer projection.
Compute pooled precision/recall/F1 from resampled sufficient statistics, verifying
those statistics against the official scorer. No threshold selection or
significance-driven endpoint selection. These intervals describe this exposed
benchmark, not independent clinical generalization.

For diagnostics, compare pair labels/probabilities, original-index rationale
overlap, synthetic-sentence selection and NEI transitions to the corresponding
primary pair. Report applicability, missing/failed inputs and full scheduled
denominators. In reference-informed conditions, additionally report change in the
probability assigned to the **primary predicted class**, with class ordering
bound to the released decoder, on pairs observed in both conditions. Report
support/contradiction strata separately; do not interpret generic negation as a
guaranteed true counterfactual. Native performance remains the primary-condition
endpoint; interventions are evidence-use diagnostics with changed information,
not additional ordinary benchmark scores or proof of causal faithfulness.

## Completion gate

All declared conditions must have complete schedule accounting, retained inputs,
sealed outputs and independently reconstructed findings. Qualification-only
success does not complete SC03. Retain negative results and methodological
limits. Update the report, TODO and memory, commit and push, then begin SC04.
