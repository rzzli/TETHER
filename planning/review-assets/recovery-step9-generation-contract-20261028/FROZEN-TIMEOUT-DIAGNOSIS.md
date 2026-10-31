# Frozen-verifier timeout: diagnosis and prospective recovery

28 October 2026 UTC. **The first attempt is terminal and failed.** It must not be
restarted or relabeled. Seven matching installed versions passed; 0.3.8 was killed
and reaped at its outer 60-second process cap. The 0.3.9 and 0.3.10 replay helpers
were never dispatched. Working 0.3.11 remains unaccepted; its passing full-source,
wheel and default-installed checks do not complete the ten-version gate.

The confirmed problem is a mismatch between the **whole-process timeout** and
the **late-start interval used as its timing basis**. I used the earlier helper's
reported legacy-restoration interval to size a cap covering its entire workflow.
That was the wrong comparison. The retained evidence does not establish a case
budget violation, infinite loop, scientific failure, v3 regression or OS-level
cause of timing variation. No helper execution, rerun, input change, download or
budget change occurred during this diagnosis.

## What the failed attempt establishes

The [terminal index](FROZEN-VERIFIER-CHECKS.json) reports
`failed_or_incomplete`; its retained [failure](../../../data/cache/r09-generation-frozen-20261028/failure.json)
is `TimeoutExpired`. The [progress log](../../../data/cache/r09-generation-frozen-20261028/progress.jsonl)
places 0.3.8 dispatch at aggregate 411.735 seconds and termination at 471.735
seconds: **60.000 seconds**. The 1,200-second aggregate ceiling was not exhausted.
The child record has PID 7576, return code 1, `timed_out: true`, `reaped: true`.
Its stdout and stderr are both empty; this helper prints its report only at the end.

All ten isolated metadata assertions passed before replay began. Observed process
intervals from dispatched/terminal progress events were:

| Version | Process seconds | Retained outcome |
|---|---:|---|
| 0.3.1 | 247.500 | Passed |
| 0.3.2 | 0.968 | Passed |
| 0.3.3 | 25.422 | Passed |
| 0.3.4 | 3.609 | Passed |
| 0.3.5 | 5.281 | Passed |
| 0.3.6 | 72.625 | Passed |
| 0.3.7 | 54.406 | Passed |
| 0.3.8 | 60.000 | Outer timeout; incomplete |
| 0.3.9 / 0.3.10 | Not observed | Replay not dispatched |

Read-only rehashing confirmed that all seven completed report hashes and their
helper/interpreter hashes still match the terminal index. All **327 frozen working
source pins** in the existing code-validation report also still match. These
seven successes can be retained as evidence without rerunning them.

## Timer scope and last durable stage

The unchanged [0.3.8 helper](../recovery-step9-interface-20261027/verify_installed.py)
executes study, baseline, comparison and retrieval smokes, then 12 v2 stage
preparations/validations. Only **after those operations**, at line 125, does it set
`started = time.monotonic()` for the seven restored legacy-family checks. Its
reported `elapsed_seconds` excludes the earlier workflow and Python setup.

| Retained successful workflow | Reported inner interval | Filesystem approximation of broader workflow |
|---|---:|---|
| Earlier 0.3.8 replay | 23.953 s | 02:59:12.575 directory creation →03:01:12.418 final report write: **119.843 s** |
| Current 0.3.11 default-installed verification | 21.906 s | 06:10:48.735 directory creation →06:12:40.537 final report write: **111.801 s** |

These broader intervals are **filesystem timestamp approximations**, not controlled
monotonic process measurements. They omit interpreter startup before directory
creation and cannot establish an exact prior wall time or identical work between
versions. They do demonstrate why the inner report cannot justify a 60-second
whole-process cap.

The failed 0.3.8 output contains fresh smoke artifacts: study directory creation
06:21:42.770 UTC, baseline 06:21:44.134, comparison 06:21:45.030 and retrieval
06:22:36.356. Its last durable point is the first retrieval consumer:
`retrieval-installed/cells/id_order_v1/journal.jsonl` records
`study_response_captured` and was last written at 06:22:42.491, adjacent to the
kill. The root journal records both retrieval preparations ready and the first
cell reserved. No final guarded verification report exists. This establishes
incomplete retrieval-smoke work before the late timer; it does not identify the
exact instruction executing when terminated or prove the remaining work would pass.

## Remaining-three recovery proposal — not execution authority

The unchanged 0.3.9 and 0.3.10 helpers each perform provenance setup and fresh
bundle copying **before** their timer, then exactly **one** top-level
`verify(..., deadline=started+299)` call. There are not two successive 299-second
top-level calls. Their installed `_verify` passes the same absolute deadline into
`_verify_bound`; its fallback deadline expression does not reset a supplied one.
The existing outer 150/180-second caps could undercut that declared verification
window even without setup. Their reports are not full-process sizing measurements.

1. Preserve the consumed attempt, marker, partial 0.3.8 folder, logs and seven
   successful reports. Freeze a new recovery decision and helper/protocol under
   distinct paths; do not edit existing helpers or output files.
2. Reuse the seven successful report anchors after fresh hash checks against the
   unchanged source/installed/helper pins. Identify only **0.3.8, 0.3.9 and 0.3.10**
   as unfinished; recheck their installed metadata before dispatch.
3. For root review, use **prospective whole-process ceilings of 360 seconds per
   remaining replay and 1,200 seconds aggregate**, retaining time for metadata,
   cleanup and sealing. This gives each 299-second inner verification window a
   separate setup/teardown allowance. For 0.3.8, it is a finite operational ceiling
   informed by the observed approximately 120-second workflow, not a proof of a
   worst-case bound: several smokes have their own case budgets. No new cap is
   activated by this note, and another timeout must remain a failure.
4. Run each unchanged helper once into a fresh version-specific output, sequentially,
   with bounded captures, durable attempts, measured full-process start/end times,
   owned-process kill/reap and no automatic retry. Keep the original input roots,
   fixture definitions and source/model-hash verification scope unchanged.
5. Only after all three pass and source pins still match, produce a new aggregate
   index binding the seven retained reports plus the three new reports, while
   explicitly retaining the original terminal failure. Root then decides acceptance.

These are pure-verification wrapper limits. **Scientific case `Budget.max_seconds`
remains 300**, and the existing inner verification deadlines, token/call/cost
limits, $0 spending and no-inference boundaries are unchanged.

Evidence anchors: terminal index
`c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50`;
failure `f1824a909e74a94a28de5562fbf40b4175e1e337890f0eaa3e792ab021805229`;
progress `d3d2f2c3bb65ac891ed83d3d3f5382c1417d0c5f7843aebbe759d058adbd9c10`;
unchanged 0.3.8 helper
`644bc6e2919bfa158c0ef774676629a74ca10a8cc905eac1173321b0b356535c`.
