# SC04 independent-analysis integration audit

Date: 6 November 2026. Scope: source review of the independent analysis modules,
comparison with the frozen SC04 protocol/specification and producer contracts,
and invented local probes. No production answers or reference scores were read;
no model or real HTTP request was dispatched. This is not final SC04 acceptance.

## Findings and disposition

| ID | Finding | Consequence and required treatment | Current disposition |
|---|---|---|---|
| IA01 | Answer admission constructs the bounded request before `pipeline.model_call`. A valid query with a long Unicode option raises `PayloadCapacityError` inside `capture()`, before the per-cell capacity handler is entered. Both primary and supplied admission use this order. | A production answer with an oversized rendered prompt terminates its phase. Do not claim that end-to-end answer capacity failures are gracefully retained as ordinary per-case abstentions. Preserve any failed attempt; any producer correction needs a new version/freeze and explicit qualification. Never alter or restart the live frozen producer to hide this condition. | **Reproduced; conditional production risk remains.** [Retained probe](CAPACITY-PROBE.json) and [reproducer](capacity_probe.py). No frozen producer change. |
| IA02 | The initial envelope reader checked the self-reported zero-denial count but did not reconstruct `io-audit.jsonl`. | It could not independently establish consistency between the completed-worker claim and captured Python file-access records, or check per-role input grants. | **Corrected and qualified.** `envelopes.py` now reconstructs exact execution/replay argv, original frame/job bindings, model bindings, per-role input lists, output writes and read-only code/runtime access; 34 envelope tests pass. |
| IA03 | The initial scientific summary retained expansion/ranking terminal status but dropped native failure class/reason and omitted the protocol's available-intervention subsets. | Codec failure, capacity and empty-pool unavailability could be conflated; a required secondary analysis was absent. | Parent has added native statuses/reasons and secondary common-subset analyses while retaining full-cohort primary denominators. Full integration qualification remains required. |
| IA04 | Initial logical accounting included only model calls/tokens, while its text implied shared source collection had also been charged. Raw/pool text quantities were missing. | Logical-versus-physical resource comparisons would be incomplete and the wording misleading. | Parent has added logical per-arm HTTP charges and original/pool text quantities. Full integration qualification remains required; summing logical charges must never become total physical spending. |
| IA05 | Component reconstruction alone does not verify the production pair's parent anchor, evaluator freeze chronology or actual native-score parity. | Calling only `reconstruct()` would not satisfy the full scientific acceptance gate. | The new analysis CLI now explicitly calls `verify_pair`, `inputs.verify(answer_started_at=...)` and native agreement. It still needs successful supervised fictional qualification and later full production execution. |

IA01's independent-reader consequence is intentional fail-closed behavior for
this frozen producer. A capacity-only isolated model-cell fixture has a null
request fingerprint. A successfully captured admission context has a nonnull
request fingerprint. These are not interchangeable contracts, and the complete
run reader must not manufacture a valid admission context to reconcile them.

## Verification performed here

The capacity probe changes only an invented answer option to 2,400 Greek alpha
characters. Its UTF-8 size remains below ordinary task input bounds, but ASCII
JSON escaping pushes the complete prompt above the frozen 14,000-byte limit.
The fixture supplies invented HTTP responses. `capture()` raises the expected
`PayloadCapacityError`; no model callback is entered. The report records the
actual frozen producer source hashes and preserves the failure outcome.

The envelope controls pass **34 tests in 11.233 seconds**, covering reconstructed
invented stage schedules, resealed contradictory accounting, missing/extra
journal events, source-body and native-usage substitutions, failed-transfer
uncertainty, wrong parent/configuration/chronology, unauthorized label reads,
writes to input/code paths, actual denied accesses, opaque file descriptors,
and incomplete audit tails. Both retained fictional controller roots and all
six phase I/O logs reconstruct. This test count belongs only to this component;
it is not the total project or production-analysis test count.

The independent scoring implementation preserves all scheduled cases, counts
operational failures separately from explicit unsure responses, and exposes
undefined substantive precision separately from the retained native zero-value
reporting convention. Source matching keeps the full question and annotated-DOI
pair denominators and never calls bibliographic matching answer entailment.
The paired bootstrap keeps all four arms together, resamples publication
components, and recomputes the denominator per draw. These source-review
observations do not substitute for the final native-agreement and production
artifact checks.

## Remaining limits

- Python-open auditing is not an OS sandbox. Existing file descriptors are
  opaque; code/runtime roots deliberately permit broad read access. Original
  `sys.prefix` and `sys.base_prefix` were not separately sealed. Reconciliation
  uses the current matching pinned interpreter's roots and reports this limit.
- The final run audit does not rehash the roughly 9 GB model assets. It checks
  the bound model/runtime receipt, configuration and native request/response
  identities; assets were verified by the producer before inference. This is
  not independent hardware or process-memory attestation.
- Timestamp consistency is evidence from the local clock, not trusted external
  chronology. The diagnostic frame commits to the completed primary receipt;
  separate verification must retain that complete parent chain.
- Full production results, final failure counts, every declared scientific
  summary and the retained results report remain prerequisites for SC04 closure.
  A passing fictional integration trial cannot complete that stage.

The implementation work here touched only new independent-analysis code/tests
and this audit folder. The primary producer, original receipts, download worker
and stopped monitor remain unchanged.
