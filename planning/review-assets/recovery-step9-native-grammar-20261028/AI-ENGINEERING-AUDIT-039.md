# AI engineering audit of the 0.3.9 integration

28 October 2026 UTC. Independent subagent code/evidence review, not independent
scientific assessment, human reference work or a rerun of the full suite. No
runtime, test, accepted evidence or original data was changed. Protected outcome
and human-answer payloads were not opened. No process, model/server or network
was dispatched by the audit probe.

## Finding

**P2 — Native transport duration is not reconciled with the child time budget.**
In `src/asof/study/native.py:334`, wrapper `elapsed_seconds` is checked only for
finite, nonnegative type/value. `verify_native_execution` in
`src/asof/study/native_interpretation.py:223` authenticates payload, provenance,
ownership, positive completion and measured token usage, but does not bound this
duration by the configured child budget. The generic study verifier separately
checks its report duration against that budget (`src/asof/study/session.py:774`),
without reconciling the native wrapper duration. The root composition then checks
the child report and journal timestamps (`src/asof/study/authority_four_arm.py:1448`).

The deterministic [pure component probe](NATIVE-DURATION-CONSISTENCY-PROBE.json)
uses cell00 of the accepted real-input simulated bundle. Both its original
0.016-second wrapper and an in-memory copy with `elapsed_seconds=9999.0` pass
`verify_native_execution`. All other wrapper/configuration/usage values stay
unchanged. The cell budget is 244.906 seconds, its retained report duration is
2.531 seconds, and the parent case limit is 300 seconds. The seven inspected
original artifacts remain byte-identical. The [probe implementation](probe_native_duration_consistency.py)
is retained.

This proves a component-level semantic consistency gap. It does **not** show that
the original run overran its deadline, bypassed dispatch enforcement or would
pass a complete externally anchored resealed-run replay; that full experiment was
not attempted. The runtime's original earlier-deadline enforcement remains
separate from verification of retained timing claims.

Before an actual-native experiment, add a regression and a separately versioned
fix to reconcile native duration with the allocated time and, where the complete
cell report is available, its measured elapsed duration. Preserve valid matching
0.3.9 verification and the accepted original artifacts. Do not silently amend its
historical acceptance or describe the existing archive as scientifically invalid.

## Evidence rechecked

The accepted manifest SHA is
`8a77c2eaba83dece672330b72c518a8f16f1417c9a14498b54686ac990b7815b`.
All 31 listed evidence hashes and 324 current source/resource/test pins match.
The preserved wheel matches the accepted wheel hash. The full validation report
and terminal log agree on 1,724 tests with zero failures/errors/skips, successful
required probes and dependency-free package/demo validation.

The default isolated installed report contains seven passing legacy families,
twelve interface preparations and the declared positive/negative invented wrapper
exercise. Optional installed replay and run-copy relocation reports have empty
guard lists and the declared original source/model roots. All eight preserved
matching-version checks have zero version-check and verification exit codes.
The actual-format qualification contains six actual offline tokenizer children,
six explicitly simulated native stages, two pure results and zero model/server
calls; its code accurately separates simulated usage. The controller reuses
source/history/capacity authority and original transport rather than duplicating
the scheduler. No other material acceptance-scope defect was identified in this
bounded inspection.

## Remaining gates and limits

The retained acceptance consistently labels this integration as engineering-only,
with native grammar, actual resource feasibility and scientific validation
unverified. The full sixteen-step plan and live TODO correctly keep R09 overall
and R10–R16 open. Pending human submissions are not replaced by these fixtures or
this AI review. The toolchain/bridge/source-build requirements in the separate
grammar workstream remain open. New model behavior, biological usefulness and
fresh-case qualifications were outside this audit.
