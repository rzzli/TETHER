---
name: research-log-2026-11-02-benchmark-execution
description: Active authorized benchmark execution; three fixes implemented, full and installed qualification pending
metadata:
  type: project
updated: 2026-11-02
---

# Authorized benchmark execution

The owner activated the full sequential goal: three correctness fixes, an independent equal-policy validator comparison, SciFact, one LAB-Bench task family, and an actual Inspect-based implementation/comparison. Proceed without repeated confirmation, retain regular commits and explicit checkpoints, and keep the goal active until all stages are implemented and verified. The authority is [[TETHER Benchmark Execution Plan 2026-11-02]], tracked as BG01–BG06 in TODO. Earlier recommendation-only statements do not block this newly authorized work; closed historical model cells, source-reporting results, external-expert retirement and deferred owner declarations remain unchanged.

BG01 implementations are present as TETHER 0.5.1 with AsOf 0.3.12. CE01 protects receipt/queue/source paths and publishes fresh reports without replacement. CE02 carries validated over-reservation usage through measured failure, stops later dispatch and reconciles failed archives. CE03 checks download availability relationships for all supplied raw nodes through a shared pure helper. Focused/peer scopes pass:12 CE01 tests;12 CE02 plus122 related;9 CE03 plus85 related;138 complete facade tests. These overlap and are not summed. Old wheels/releases and the disabled monitor are separately preserved; no actual model or network call occurred.

The first full core gate was interrupted after14 errors/failures caused by the old archive dependency profile rejecting the three changed engine modules. It is terminal (session78654 exit1; no matching Python process), with rawlog/interruption record retained and no final driverJSON. Initial root commentary incorrectly reported no failures because it checked only final headers; the correction is explicit. The active profile is now separately versioned for0.3.12, with old bytes retained and exactly3pins changed/19unchanged;52 archive tests and3 relocated old controls pass. No archive Python guard was weakened.

Next: fresh full-gate02 through `planning/review-assets/tether-ce-fixes-20261102/integration/run_gate.py`, then isolated wheel qualification through `qualify_release.py`, then `check_stage.py` with all evidence. All paths must be fresh; inspect exact session/process/report state before resuming, never infer a live or terminal process from this memory alone. Current mutable state is `planning/review-assets/tether-ce-fixes-20261102/EXECUTION-STATE.json`. BG01 remains incomplete until those gates pass; BG02–BG05 are not started. Preserve the full objective rather than replacing benchmarks with parsers, gold-answer replay or a weaker-policy comparator.
