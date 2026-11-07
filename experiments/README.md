# Evaluation and experiment code

These modules separate benchmark preparation, candidate generation, policy
checking and scoring. They are reusable experimental code, not bundled datasets,
model weights or claims of benchmark completion. Most require additional pinned
inputs or dependencies beyond the default offline demo.

| Module | Purpose |
|---|---|
| [equal_policy](equal_policy/) | Compare validator implementations under a shared declared policy |
| [equal_policy_v2](equal_policy_v2/) | Source-inclusive installed-run checking and independent reconstruction under that policy |
| [inspect_policy](inspect_policy/) | Implement and test corresponding controls within Inspect |
| [scifact](scifact/) | SciFact preparation, native metrics and bounded execution; [protocol](scifact/PROTOCOL.md) |
| [scifact_diagnostics](scifact_diagnostics/) | Reconstruct descriptive retrieval, selection, label and rationale errors |
| [scifact_multivers](scifact_multivers/) | Isolated full-context MultiVerS producer and source-based qualification |
| [scifact_multivers_transport](scifact_multivers_transport/) | Bounded, receipt-producing acquisition helper |
| [scifact_multivers_supervision](scifact_multivers_supervision/) | Owned-child supervision with deadlines and retained outcomes |
| [scifact_comparison](scifact_comparison/) | Fixed-retrieval full-context comparison; [protocol](scifact_comparison/PROTOCOL.md) |
| [labbench](labbench/) | LAB-Bench task contracts, source preparation and native scoring |
| [litqa_comparison](litqa_comparison/) | Declared LitQA retrieval/answering conditions and source-inclusive reconstruction |
| [litqa_supplied](litqa_supplied/) | Separately labelled supplied-source diagnostics |
| [litqa_analysis](litqa_analysis/) | Independent reconstruction and analysis of retained LitQA runs |

Pinned protocols are execution contracts and retain their exact bytes. Their
historical context does not authorize a new run or transfer prior qualification
to changed code. Relative links inside the original SciFact protocol retain its
original planning-directory context; use its
[original source location](https://github.com/rzzli/TETHER/blob/ea0222dfac7675c6388e336516f82bbcd828fff4/planning/TETHER%20SciFact%20Execution%20Protocol%202026-11-05.md)
when following those historical references. Read each module's CLI and tests before preparing a fresh input
manifest. Preserve every original, failed attempt and receipt; never silently
repeat an uncertain model call.

For direct navigation from the byte-pinned SciFact protocol, use the
[original benchmark plan](https://github.com/rzzli/TETHER/blob/ea0222dfac7675c6388e336516f82bbcd828fff4/planning/TETHER%20Benchmark%20Execution%20Plan%202026-11-02.md)
and [current session implementation](../src/tether_engine/study/session.py).
These replace its two historical relative cross-references for browsing; the
protocol bytes remain an unchanged execution input.

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
