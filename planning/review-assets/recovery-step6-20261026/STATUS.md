# R06 implementation and validation

Status: frozen full validation passes **1,435 tests**, zero failures/errors/skips,
required probes and package/demo in 895.078 seconds. Source/resource pins and
protected outcome hashes remain unchanged. Final acceptance is recorded separately
in `acceptance.json`; the independent peer tests remain unchanged after fixes.

## Delivered

- Small packaged proof, owned-process and once-only study-session primitives.
- One consumer: the R05 diagnostic, with exact current/simplified payloads,
  distinct strict response contracts and authenticated versioned source-only
  resources. Real requests remain explicit caller inputs; no drive path is built
  into the new runtime.
- Recorded success and malformed-response failure smoke, usable from the installed
  wheel with repository tools/planning imports denied. No native execution mode.
- Explicit backend capabilities and trusted verifier protocol. Backend IDs are
  provenance only. Unresolved reservations are never automatically replayed.
- Version 0.3.0 in module/package/lockfile and a new CHANGELOG. Default runtime
  dependencies remain empty. Existing launchers, download worker and monitor
  remain unchanged.

## Corrections found during independent review

| Finding | Correction and regression |
|---|---|
| An earlier package member could change during later hashing | Recheck full byte proofs after inventory, including resources |
| Fallible post-spawn clock could leave false ownership metadata | Save the process handle and started/PID state immediately |
| Cleanup clock could replace an interruption | Record it as a secondary failure and preserve the primary exception/terminal record |
| Consumer resource IDs and proof IDs disagreed | Validate safe relative semantic IDs consistently; retain traversal/alias rejection |
| Capabilities/budgets and event order were not replayed | Reuse capacity admission in execution and verification; enforce complete event sequence |
| Adapter proof, conservative usage and retained bytes could contradict the run | Verify trusted adapter identity, full conservative reservation and exact captured byte counts |
| Report schema/kind could be resealed inconsistently | Validate report identity/status/schema along with run and accounting bindings |
| A stale package proof could consume a call before finalization | Verify package/resource proofs before backend use |
| Already-written request/config/response could change before finish | Reconcile files with accepted state and the durable journal before sealing |

Failures are retained under `data/cache/recovery-step6-*` and the independent helper
probe directory. The first finalization fix was inserted at the wrong call site,
which caused a focused AttributeError; its log is retained. The corrected insertion
passes all fifteen peer tests. No failed fixture became a successful model run.

## Current verification evidence

- Seventy-eight new study tests pass under stdlib trace with no skips, unchanged
  study sources and **2,001 / 2,075 executable lines covered (96.43%)**. This is
  CPython 3.11 line coverage, not branch coverage or a scientific accuracy metric.
- Scoped Ruff 0.8.6 formatting/lint passes for all new study modules/tests.
- Isolated installed 0.3.0 wheel smoke passes for a valid recorded cell and an
  intentionally invalid recorded cell. All seven legacy archive checks pass again
  under original-root, archived-execution, repository-import and network guards.
- Installed archive checks took 20.094 seconds with a 59,502,592-byte peak working
  set. That is verifier memory, not native model/GPU memory.
- Full regression/probe/package and complete source/resource pin results pass.
  R04's independent accepted full result remains 1,357 tests; it is not overwritten
  by R06. The source environment initially retained editable distribution metadata
  0.2.0 while module/repository/wheel versions were 0.3.0. An offline editable
  refresh aligns it, followed by the scoped study rerun because environment
  identity is part of the package proof. The installed wheel already used 0.3.0.

## Remaining gates

The owner confirmed on October 26 that human reviews are still pending. HR1–HR4
are not complete, and R07 scientific execution/acceptance remains held. The existing
mechanism orientation form does not establish genetics/MR expertise for the
prepared real genetic question. The stronger-model condition is unavailable; no
capacity conclusion follows from the available 14B model or payload checks.

No native model call, data acquisition, paid access, clinical-outcome content read,
old receipt rewrite, live-adapter activation or clinical/scorer/MR qualification is
introduced. Native ownership/memory/latency needs actual qualification later;
fake tests do not supply it. New study-format relocation is not yet part of the
legacy archive support matrix. Hosted CI and off-machine durability remain open
release gates. The full original project is unfinished.
