# SC03 method decisions before execution

These are prospective design notes while SC02 qualification is pending, not an activated experiment protocol or new benchmark result. Final input, code, model, environment, schedule and resource pins still require SC02 acceptance.

The primary comparison uses released `fever_sci` zero-shot with the original ordered five retrieved documents for each of all 300 SciFact development claims. The earlier trained sparse model remains fixed. The new solver's external supervision differs; any improvement belongs to the solver condition, not an isolated architecture effect or a claim that filtering creates correct answers. Fine-tuning is not selected by inspecting new development results. If added later, it requires a prospective separate fit/tune-only protocol and explicitly disclosed development exposure.

The experimental solver does not upgrade the production T6 specialist backend. New raw predictions must pass the declared native SciFact adapter under the same qualified obligations, with complete candidate fingerprints and source replay. Native SciFact results cannot establish therapeutic efficacy or clinical calibration.

## Evidence interventions

- **Primary:** unchanged claim, title and every original sentence in each retrieved abstract. No reference labels, rationale masks, source hints or gold-derived caps are supplied.
- **Rationale-only diagnostic:** reference-informed selection of annotated rationale sentences within retrieved annotated documents, with original sentence indices retained in the mapping. Alternative rationale sets require an explicit rule before execution. Its scores are reference-informed diagnostics, not retrieval performance.
- **Evidence-removal diagnostic:** remove the same declared rationale sentences while preserving the other source context. A change of answer can be appropriate when decisive information is removed. The native original-label accuracy is not a sufficient criterion for this condition.
- **Irrelevant-context diagnostic:** specify independent, labelled constructed distractors and fixed placement/token budgets. Preserve all original information and record any overflow as a failure rather than truncating away the intervention or evidence.
- **Conflicting-context diagnostic:** distinguish a constructed contradictory statement from naturally observed contradictory evidence. Stability is not automatically desirable: a solver should respond to relevant conflicting information. Report label/probability changes and uncertainty; do not label every changed answer wrong or treat synthetic contradictions as authentic publications.

All gold-derived masks and modifications belong in evaluator/diagnostic assets separate from primary inputs. Every transformed sentence has a source or an explicit synthetic origin. Changed text never inherits a false original-row fingerprint. The original corpus and schedule remain immutable, with intervention applicability and missingness retained for all 300 cases.

Where available, report class-score differences alongside labels and rationales. [ERASER](https://aclanthology.org/2020.acl-main.408/)-style sufficiency/comprehensiveness quantities require the declared class score and rationale assumptions; an intervention response alone is not causal evidence that a model's entire explanation is faithful. Claims without applicable annotated retrieved evidence remain in the schedule with an inapplicability flag, not silently dropped.

## Execution and analysis boundaries

Keep one model resident in a bounded worker to avoid repeated model/environment parsing. Verify input/model/code/environment identities at declared boundaries, cache only immutable accepted state, and retain per-pair start/completion/failure records and per-claim candidates. A worker failure leaves completed, partial and unexecuted cases distinguishable; no uncertain call is silently repeated.

Freeze condition order and total/per-case budgets before inference. Record input tokens, long-context failures, wall/CPU/GPU observations and admitted/abstained/failed counts. Report raw and checked native metrics and strict useful answers per all scheduled cases, plus correct answers rejected and incorrect answers admitted. Source-overlap dependence and repeated public-development exposure prevent treating 300 claims as a new untouched independent clinical sample.

The retained split manifest (SHA-256 `89c9bc916680411642f8b2bef66d5adb0ea1446655266b72d2062567b6bb05c8`) assigns these 300 development claims to 247 existing source/text components; the largest contains four development claims. This metadata-only check informs a prospective paired component-bootstrap uncertainty analysis. Resample the same components for compared conditions, recompute pooled native metrics, and freeze seed/replicate count in the actual protocol. Such intervals describe variability within this exposed benchmark and do not repair model-selection exposure or establish clinical generalization.
