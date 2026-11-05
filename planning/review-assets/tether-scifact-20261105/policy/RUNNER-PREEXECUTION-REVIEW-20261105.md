# Bounded native SciFact controller review

Review date: 2026-11-05. Scope: the newly written `run.py`, `worker.py`, and `runtime.py` joins to the qualified native policy, scorer, and execution protocol. This is a pre-execution review, not qualification of a real fitted model or a scored result. No production fitting, inference, or reference scoring was performed by this reviewer.

## Material findings

1. **Verified model bytes were reopened before prediction.** The worker originally checked both model files through `load_input`, then called a directory-based loader that reopened them. A consistent replacement between those reads could become the consumed model under the original recipe proofs. Root corrected this by adding `baseline.load_model_bytes` and passing the already verified buffers. The current worker visibly uses that API. The corrective regression and new source qualification remain root-owned; earlier 117-test evidence does not qualify this changed source.

2. **The runtime source bracket returned stale remaining stage time.** `Stage.boundary` computed the remaining budget before full runtime/package checks. A fictional source bracket consuming 20 seconds under a 10-second budget returned 10 seconds, permitting another dispatch. Recompute the remaining budget after the bracket and reject exhaustion before dispatch. Confirmed in `RUNNER-PREEXECUTION-PROBES-02.json` against stable run.py SHA `443f925d056ed52a5cd473929a0264f1da18b90937acc169f154c2cab0a29be7`. Runner owner notified.

3. **Worker records were internally checked but not reconciled with their submitted recipe.** `dispatch` accepted an internally sealed session with configuration k=20/threshold=.75 despite a submitted k=5/threshold=.25; its setup also declared a different mode and no inputs, and its query request declared ID 999 while scheduled cell 1 returned prediction ID 1. The later policy envelope is assembled by the controller, so it must not relabel contradictory worker requests as the intended configuration/query. Reconcile session configuration, setup input proofs/mode, and each query/configuration request against the submitted recipe and approved query view. The same retained fictional probe confirms this acceptance. Runner owner notified.

4. **Watchdog marker-write failure could disable enforcement; corrected.** The original watchdog wrote and fsynced `WATCHDOG-STOP.json` before `os._exit`. If that write failed, only the monitoring thread would terminate, leaving an observed per-call or memory breach running until the broader parent deadline. At root's request, this reviewer added two fictional subprocess regressions: an actual marker-open failure and an injected fsync failure. Both reproduced an incorrect successful child exit before correction (`red-watchdog-marker01.log`). Termination now runs in `finally` after attempted marker persistence. All eight runtime tests pass (`green-watchdog-marker01.log`, 1.060 seconds), including expected exit 124 for both new cases. This is component validation, not a production benchmark run.

5. **Two declared protocol boundaries were not implemented by the inspected controller.** Protocol section 8 specifies a separate reference-only scorer process, while tuning and final evaluation called the pinned evaluator inside the controller. Section 7 specifies 60 seconds per check cell, while the check loop had only the overall remaining-stage session budget. These require implementation or an explicit, reviewable protocol amendment before claiming the original boundaries are met. Root and runner owner notified. The scorer implementation's existing fictional correctness qualification does not establish subprocess isolation or a check-cell deadline.

## Wording correction

`FROZEN.json` described reference access as `trusted_controller_only_after_candidate_production`. Trusted preparation reconstruction already processes reference-containing archive members to establish projection and grouping. The correct distinction is that prediction receives no reference inputs, and reference **scoring** happens after the corresponding immutable candidates. Runner owner notified; this is not evidence that predictor workers consumed gold answers.

## Checks with no defect identified in this bounded pass

- Prediction recipes expose only numeric model files and a query-only product. They do not pass the full private preparation manifest, split/reference products, or raw mixed archive to prediction.
- Fit recipes name corpus, fit queries, and fit-only pair supervision; the model policy separately checks exact parent bytes and retained fit execution.
- Model/configuration and the full development schedule are frozen before the development dispatch. The declared nine tuning settings are selected by the predeclared metric/tie rule.
- `NativeSession` output reservation and controller job-path checks prevent automatic reuse of the same attempt; the controller does not retry worker calls.
- The controller retains scheduled cases on failure and keeps missing production separate from native empty-evidence predictions.
- The qualified subprocess supervisor supplies `tether_engine_result` for interruption and other retained failures. The controller's exception handling reads the correct attribute; the separate `.result` member on `EngineInterrupted` is not a defect here.
- Native measured resources retain null token/tokenizer/provider usage with the non-LLM reason and zero provider spending. Primary-product bytes are not physical I/O bytes or total stage storage.
- Python open auditing and polling are explicitly scoped to trusted worker behavior; no hostile-code or operating-system sandbox claim follows.

## Evidence and limits

`probe_runner_preexecution.py` uses fictional records and a synthetic clock only. `RUNNER-PREEXECUTION-PROBES-02.json` is the valid probe result and records unchanged source hashes before and after. Probe 01 is retained for traceability but its contradictory-request result contains a probe reporting `KeyError`; it must not be interpreted as a successful rejection by the implementation.

At this review checkpoint, the observed sources were:

| Source | SHA-256 |
|---|---|
| run.py | `443f925d056ed52a5cd473929a0264f1da18b90937acc169f154c2cab0a29be7` |
| worker.py, already corrected to consume captured model bytes | `2489fb6753878482cc5ce9b0ed88b6471339997dba02dfa00b453fde24888600` |
| runtime.py, before watchdog correction | `86cda170d03ae79ded18885345e0876dc6b02622399d1b81044c1409330571f6` |
| baseline.py, already exposing captured-byte loader | `ca3d9c034173fb647e91b81616f765e58880c518f9912a9a6358ad335472d92c` |

These are review checkpoints, not a single qualified source bundle. Owners are correcting files concurrently. Fresh combined tests and a stable source/runtime bracket are required before the real stage. The native adapter's existing component status remains scoped to its own policy tests and original-container admission; this review does not upgrade G4 or BG03 to complete.

The watchdog-corrected `runtime.py` is SHA `e5b07142927ab638504eae954610c0e9b3a2b2f53474191fb98e3e06deaf4ce2`; its eight-test file is SHA `9381d730dc277113e6139c496aa58d4844911a84f000ab4a1d57cac3928cc5f8`. Root owns subsequent whole-stage qualification. Source files are held stable after that correction.
