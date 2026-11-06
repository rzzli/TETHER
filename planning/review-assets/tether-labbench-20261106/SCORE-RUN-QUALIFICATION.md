# Evaluator-only LitQA2 scoring stage qualification

`experiments/labbench/score_run.py` and its optional experiment tests are ready for the combined stage freeze. **Eleven fictional tests pass** in `score-run-green08.log`. No actual public-question candidate has been generated, scored or consulted by this qualification. No live model, network retrieval or reference oracle was used by these tests.

## Entry point and ordering

The API is `score_run(generation_root, expected_sealed_sha256, preparation_root, expected_preparation_manifest_sha256, output, deadline_seconds=3600)`. The CLI exposes the same names with hyphens through `python -m experiments.labbench.score_run`.

The evaluator reserves a new output directory, validates the externally anchored generation seal and frozen code, reconciles the complete ordered schedule with the source collection, verifies model/runtime originals once, and replays each candidate's original sources, request, generic StudySession and policy decision. Only after that sequence does it open the separately anchored preparation references and original annotation fields. No reference input is passed to the producer. Missing seals fail before reference access. Output collisions fail without overwriting; evaluation failures retain a terminal record.

A produced answer must be identical across the native session response, candidate artifact and raw/checked disposition. The evaluator recaptures source contexts through the real TETHER adapter and normalizes only the new mechanical capture timestamp; original availability, roles, parents, source text and request remain exact. The archived derived timestamp must agree with its original capture timestamp. Correct/wrong answer labels have no role in that replay. A valid answer cannot be relabeled as a parse failure. Operational failures retain their original all-scheduled positions.

Sealed partial generation remains `descriptive_partial`, with all tasks included. Scoring completion does not independently establish scientific or milestone acceptance. Unknown resource measurements remain unknown; model verification byte sizes are logical original sizes, not physical I/O. Shared collection/generation accounting and marginal evaluation costs are reported separately. No new model or retrieval call is made.

## Source alignment and controls

- Primary diagnostic: observed annotated-source identity hits divided by **all scheduled questions**. Missing/unresolvable annotation identities remain explicit.
- DOI-only diagnostic: every syntactically valid distinct annotated DOI per question enters the denominator, including DOIs absent from discovery metadata. This is identifier recall.
- Secondary diagnostic: conditional resolved-paper recall using retained DOI/PMID/PMCID crosswalks. Its report explicitly warns that discovery-based resolution is missing-not-at-random and can yield perfect conditional recall despite retrieval misses. Unresolved aliases never inflate the paper denominator; multiple-DOI conflicts remain unresolved.
- Retained full-text alignment and articles represented by selected prompt passages are separate. Selection for a prompt does not imply an unexecuted model received it. Shared identifiers, identical unresolved annotation pointers, verified alias components and whitespace-normalized duplicate questions define descriptive dependence components; residual dependence remains unknown.
- Random all-option/substantive-option and always-unsure controls are analytical and clearly marked **not executed**. Random precision is a ratio of expected counts, not a claim about expected finite-sample precision. No imaginary checker admissions are assigned to those controls.

The illustrative fixture has observed hits 1/3 and DOI recall 1/2 while conditional resolved-paper recall is 1. This deliberately demonstrates the resolution bias. No identity metric is called semantic entailment. Source inspection reads only original captured metadata, makes no posthoc network lookup, and retains field/path/hash provenance. Public aggregate reports do not expose answer indices, answer text or benchmark annotation values.

## Retained failures and regression evidence

- `score-run-red01.log`: missing new module before implementation.
- `score-run-green01.log`: retained initial syntax failure despite its filename; subsequent lower-level fixtures passed.
- `score-run-green06.log`: real fictional InputGraph/StudySession replay exposed a model prompt-ordering defect. Canonical request serialization reordered query fields while the inner prompt JSON preserved insertion order. The model owner added deterministic key ordering and a separate round-trip regression. `score-run-green07.log` then passed all eleven tests.
- `score-run-frozen-red01.log`: data-owner peer review found mutable-list comparisons against the frozen tuple schedules returned in production. Tests were changed to use actual frozen return shapes and reproduced two failures. All schedule joins now normalize ordered sequences consistently. **`score-run-green08.log` passes all eleven tests**.

The real-component pair fixture uses mocked fictional HTTP responses and a fake local transport, but actual source parsing, receipts, `InputGraph`, immutable capture, `StudySession`, `MCQVerifier`, hash-chain replay and policy decision comparison. It rejects a substituted candidate even when that candidate's local proof and disposition are resealed together. The controller partial-run fixture separately stubs already qualified producer/source/model verifiers; it is not represented as a complete pipeline test.

The data owner reviewed collector/scorer joins. Completed source cases supply original retrieval manifests and selected bindings; failed/interrupted/unexecuted grants remain unusable and stay on the schedule. Complete empty-source grants are valid states. Search metadata exceeding the declared hit limit does not enter the posthoc alias crosswalk.

## Final held hashes

| Artifact | SHA-256 |
|---|---|
| `experiments/labbench/score_run.py` | `bc51b34055af9d9d5a2a7a972c6b965d666be24af24b4afb4ca3cee42d36cd7e` |
| `experiments/labbench/tests/test_score_run.py` | `5798695a88eface4736c0c5e75b60b85b23444cd252c9d1ee38e121e86b8f668` |
| `score-run-green08.log` | `551b666c75d1e6a42e34c4f8609e113a6f2a859d1f36a9b417b6828cde7a062d` |

Actual execution, final native reference reconstruction and independent result analysis are later gates. The independent reconstruction must not import this scorer or producer helpers.
