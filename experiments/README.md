# Evaluation and experiment code

These modules separate benchmark preparation, candidate generation, policy
checking and scoring. They are reusable experimental code, not bundled datasets,
model weights or turnkey reproduction packages. Most require additional pinned
inputs or dependencies beyond the default offline demo.

**Status, 12 November 2026:** SciFact and LitQA measurements are completed,
repeatedly exposed development studies with mixed/negative results. ALCE is
frozen incomplete; Scholar/R2E expansion is deferred. No benchmark expansion
is the current next step. See the [result register](../docs/RESULTS.md).

| Module | Purpose |
|---|---|
| [temporal_audit](temporal_audit/) | Reproduce the descriptive evidence-release, endpoint and registry tables, and replay the selected Open Targets partitions |
| [equal_policy](equal_policy/) | Compare validator implementations under a shared declared policy |
| [equal_policy_v2](equal_policy_v2/) | Source-inclusive installed-run checking and independent reconstruction under that policy |
| [inspect_policy](inspect_policy/) | Implement and test corresponding controls within Inspect |
| [scifact](scifact/) | SciFact preparation, native metrics and bounded execution; [protocol](scifact/PROTOCOL.md) |
| [scifact_diagnostics](scifact_diagnostics/) | Reconstruct descriptive retrieval, selection, label and rationale errors |
| [scifact_multivers](scifact_multivers/) | Isolated full-context MultiVerS producer and source-based qualification |
| [scifact_multivers_transport](scifact_multivers_transport/) | Bounded, receipt-producing acquisition helper |
| [scifact_multivers_supervision](scifact_multivers_supervision/) | Owned-child supervision with deadlines and retained outcomes |
| [scifact_comparison](scifact_comparison/) | Fixed-retrieval full-context comparison; [protocol](scifact_comparison/PROTOCOL.md) |
| [scifact_calibration](scifact_calibration/) | Reserved-claim retrieval, bounded inference and fixed selective-answering calibration; development result retained |
| [labbench](labbench/) | LAB-Bench task contracts, source preparation and native scoring |
| [litqa_comparison](litqa_comparison/) | Declared LitQA retrieval/answering conditions and source-inclusive reconstruction |
| [litqa_supplied](litqa_supplied/) | Separately labelled supplied-source diagnostics |
| [litqa_recovery](litqa_recovery/) | Explicit continuation plans, source adoption and full-schedule answering after an audited interruption |
| [litqa_analysis](litqa_analysis/) | Independent reconstruction and analysis of retained LitQA runs |
| [litqa_refinement](litqa_refinement/) | Typed critique and repair; failed original condition preserved |
| [litqa_refinement_recovery](litqa_refinement_recovery/) | Historical recovery and accounting of completed, failed and untouched calls |
| [litqa_evidence_first](litqa_evidence_first/) | Completed separate development comparison; repair did not improve accuracy |
| [alce](alce/) and [alce_transport](alce_transport/) | Native metric controls and data/model preparation; full benchmark generation/scoring incomplete |

Pinned protocols are execution contracts and retain their exact bytes. Their
historical context does not authorize a new run or transfer prior qualification
to changed code. Use the maintained [SciFact navigation](scifact/PROTOCOL.md)
for its preserved protocol and current result scope.
Read each module's CLI and tests before preparing a fresh input
manifest. Preserve every original, failed attempt and receipt; never silently
repeat an uncertain model call.

Keep evaluation references out of candidate generation and report operational
failures separately from substantive answers. Scientific performance requires
complete declared schedules, matching native metrics and source-inclusive checks.
Passing invented regression fixtures alone does not establish performance.

For an older LitQA run whose producer sources have moved, the independent
reconstruction API accepts an explicit `source_archive={"path": ..., "sha256": ...}`.
Its externally anchored manifest must supply every original producer file with
the exact executed hash. Archived Python is read as data, never imported. Run,
input and receipt paths still retain their original identities; this option
does not relocate a run or authorize repeating an interrupted call.

The evaluator-input verifier also accepts a validated `native_scorer_archive`
when the frozen scorer source has moved. It checks the archive again when used
and preserves the original scorer proof. This verifies bytes; executing a changed
scorer additionally requires a separate equivalence check and behavior tests.

Recovery uses new version-two artifacts. Completed sources keep their original
receipts, uncertain transfers stay unknown, and only untouched source slots may
dispatch. A permanent parent reservation prevents a second output directory from
silently repeating collection. Answer contexts are checked for the entire schedule
before generation begins; failed and unexecuted slots remain in the denominator.
Component tests use fictional data. Production additionally requires a qualified
supervisor, model and source transition, frozen limits and independent replay.
