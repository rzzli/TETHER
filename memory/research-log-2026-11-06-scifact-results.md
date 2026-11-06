---
name: research-log-2026-11-06-scifact-results
description: Completed weak SciFact development result with preserved candidates and independently reconstructed scores; LAB-Bench is next
metadata:
  type: project
---

# SciFact completion and next benchmark

BG03 is complete in the declared native public-development scope. A real CPU
baseline was fit once, all nine prescribed settings were tuned, and the selected
k5/rationale-threshold0.25 was frozen before all300 dev predictions. Source-disjoint
supervision used380 fit/82 tune/69 reserved-calibration claims; the unlabelled
5,183-document retrieval corpus is shared. There were no producer retries,
failed cells or provider requests. Native source files remain unchanged.

All300 candidates passed the scoped provenance checks. Only27/300 were strict
correct (9%): SUPPORT1/124, CONTRADICT0/64, NEI26/112. Raw and checked native
F1 agree exactly: abstract-label .13506013; abstract-rationalized .08695652;
sentence-selection .07861991; sentence-label .04807692. This is weak answering,
with no semantic accuracy gain from checking. It is not proof that the other273
outputs are biological falsehoods; they fail the stated complete-case criterion.

Retrieval found159/209 annotated claim/document pairs (76.08%) and all gold
documents for147/188 nonempty-gold claims (78.19%). There are247 source/claim
components. Only one nonempty-gold case satisfies the strict criterion, so
retrieval alone is not the full problem. A clearly labelled post hoc arithmetic
reference notes that constant NEI would satisfy112/300 strict cases (37.33%) but
have zero evidence F1; no competing execution or cost is invented.

The actual stage took587.286744 seconds. Repeated runtime verification consumed
486.680 seconds across47 brackets; all named controller operations total500.203
seconds. Direct candidate checks total .270571 seconds, but checker setup/replay,
process overhead and phase brackets are additional. Exact marginal total and
physical disk I/O are not fully measured. Peak child lifetime working memory is
304,451,584 bytes. Shared setup costs are not all attributed to answer checking.

Independent reconstruction passed first attempt: all metrics, selections,
requests, candidate identities, source bindings, costs and denominators match.
It checks10,110 retrieved-document and12,777 returned-sentence bindings across
tune/dev. Root accepts1,601 stage outputs/36,570,027 bytes and72 reconstruction
outputs/1,261,321 bytes. All85 maintained core/facade sources and739 qualified
import caches remain unchanged. Integration148 and independent-reconstructor18
fictional tests pass; the completed22-process rehearsal and earlier failures
are retained. Final report review verifies24 metric cells,three strata and18 links.

Actual stage: data/benchmark/scifact/native-20261105T234805Z-attempt01.
Its closed exec session was76726; do not restart it. Stage receipt SHA256:
3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968.
Independent receipt:07e9d33fa0d8d989c458edd1a956b3a9e7b4701f5665e10e3fcdc0cf5fa30bed.
Root acceptance:planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json.

The report is [[TETHER SciFact Native Evaluation Results 2026-11-05]]. The sealed
2November paper is preserved; new benchmark material is supplemental pending the
remaining comparisons. These are public-development annotations, not private,
clinical, causally adjudicated or calibrated results. There is no new expert gate.

Next is BG04: select original LAB-Bench LitQA2 or DbQA by source/task feasibility
before examining model performance, then implement a real answering/scoring route
and matched checking. BG05 tests equivalent policy within Inspect; BG06 audits
the whole goal. Do not mark the overall goal complete before those stages pass.
Related: [[research-log-2026-11-05-scifact-components]],
[[research-log-2026-11-05-benchmark-priorities]], [[project-goals]].
