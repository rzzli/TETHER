# BG05 independent runtime reconstruction — actual attempt 01

**Result: PASS within the declared finite-witness scope.** All 19 logical cases remain on the schedule: 16 ordinary native Inspect cases, two interruption dispositions, and one logical ownership-race case executed by two native workers. No production run was repeated and no frozen producer or reconstruction source was changed.

The main result is [RUNTIME-RECONSTRUCTION.json](RUNTIME-RECONSTRUCTION.json), SHA256 `c1f3507eaa98e398c91bfaa7db9a851a09e5d9360e1612a2676257487dcf4f7b`. The separately retained [ORDINARY.json](ORDINARY.json), SHA256 `13911c542901cdef0fd049b41180b01093b2b4d8f484c4dc612c086a3db4426a`, equals the embedded ordinary result. The frozen independent readers perform the source, claim, accounting, native-log and synthetic arithmetic checks; [audit_outer.py](audit_outer.py) is postexecution analysis glue for the outer stage and process controls, not prospectively frozen producer code.

## What was checked

- The externally supplied freeze `532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5`, preparation `b17fdfba429a913cb5a12bd1d1c5e0388031066ed45d7e93fca6c931fa55077c`, and stage seal `92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f` match the consumed bytes. The stage-seal hash is a root postexecution external anchor; it was not independently captured during execution.
- All 9,451 pinned code/environment proofs, 176 prepared inputs, 23 sealed stage files and 124 witness output files passed their declared hash/inventory checks. A separate inventory audit by the data agent checks exact environment/preparation membership as well.
- All 16 ordinary cases match the frozen expected fields. Native sample IDs, callback identities, response contents, captured usage, policy accounting, receipts, source rows and committed claims reconcile. Native error samples remain represented even when Inspect does not score them.
- Nine committed claims across the ordinary cases and race winner join their original inputs. Five commit states independently reproduce all eight feature slots and the configured synthetic genetic-support calculation, including contribution/probability or explicit abstention. This is a deliberately narrow synthetic calculation, not an independent implementation of all therapeutic feature or eligibility rules.
- The interrupted call retains one dispatch and its unresolved reservation; the second scheduled case is unexecuted. The terminated owned child has a retained nonzero exit/reaping record. Re-reading the unfinished journal does not dispatch anything.
- In the controlled two-worker race, exactly one worker owns the output, exactly one dispatch occurs, the losing native sample reports `FileExistsError`, and the winner's native record and receipt reconcile.

## Outcomes and accounting

| Logical disposition | Count |
|---|---:|
| Completed | 4 |
| Budget exhausted | 3 |
| Error | 9 |
| Timeout | 1 |
| Interrupted, unresolved | 1 |
| Unexecuted | 1 |
| **All scheduled** | **19** |

These are the expected control outcomes, not 15 excluded or missing cases. For example, future program/scorer inputs cause zero dispatches, while the request-mutation case reserves an attempt and enters the provider boundary but dispatches zero times. The commit-prefix case retains its accepted prefix and an incomplete-run abstention.

Across all three groups there are **15 reserved workflow attempts, 15 provider-boundary entries and 14 scripted provider dispatches**. The 17 finalized policy records (ordinary 16 plus the race winner) contain measured usage of 71 input / 48 output tokens and unresolved-or-unqualified estimates of 160 input / 320 output tokens. The interrupted record separately retains another 20 / 40 token reservation. These categories are not collapsed into native counts: finalized native logs report 132 input / 88 output tokens, including counts from responses that did not qualify for policy admission. The malformed response's observed input count exceeds its quote, and that observation stays visible; a reservation is not proof of a universally valid upper bound. All usage is from scripted local fixtures, and provider cost is **$0**.

## Limits

The audit supports the specified finite runtime invariants and the archived conformance comparison. It does not demonstrate a complete eight-specialist therapeutic scheduler, positive review retries, scientific accuracy, general feature/scorer equivalence, real provider billing, arbitrary descendant containment, or power-loss recovery. General eligibility remains supplied by the reused independent validator. IX11 write-failure evidence is maintained component/mock qualification rather than an additional persisted native write-fault run. IX06 and IX08 establish the retained owned-child interruption and one controlled ownership race, not universal process/filesystem guarantees.

The retained [OUTER-01.log](OUTER-01.log) and [ORDINARY-01.log](ORDINARY-01.log) both report success. There was no actual-run audit failure to conceal or repair.
