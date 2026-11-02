# BG01 completed — TETHER 0.5.1 / AsOf 0.3.12

The three reproduced defects are corrected and locally qualified on Windows.
The [aggregate validation](VALIDATION.json) passes **742 checks**, binding the
complete test run, current source inventory, installed wheels, regressions,
reviewed archive-profile migrations and preserved older artifacts. This closes
BG01 only. The independent comparator and external benchmarks remain unexecuted.

## Corrections and acceptance

| Requirement | Implemented behavior | Retained evidence |
|---|---|---|
| CE01 report/input collisions | Reject receipt, queue and source aliases; publish a new complete report without replacement. | `ce01/VALIDATION.json`; 12 regression tests including Windows aliases and concurrent publication. |
| CE02 failed-call accounting | Preserve validated adapter-reported usage above reservation, stop later dispatch, and reconcile failed archives. Malformed counts remain unknown/estimated. | `ce02/`, `peer-ce02/`; red/green and old/new sealed-run controls. |
| CE03 unused raw inputs | Check receipt-derived availability for every supplied raw policy node, while retaining valid alternative availability bases. | `ce03/`, `peer-ce03/`; paired used/unused controls and older seals. |
| Windows replacement resilience | At most three replacements of the same staged bytes, 50/100 ms requested waits for native errors 5/32/33, and preservation of primary failures during cleanup. | `integration/windows-replace/VALIDATION.json`; 10 new, 72 related and 21 publication/maintenance tests. |
| Archived runs and versions | Preserve original wheels/runs and two reviewed executing-profile predecessors. No archived Python code is executed. | `archive-profile/`, `archive-profile-v2/`, `legacy-preservation/`; fresh 52-test archive scope and three old-run controls. |
| Final evidence completeness | Reject incomplete/concatenated unittest results and incomplete preservation inventories; bind full-driver JSON and exact committed preservation records. | `integration/aggregate-checker-peer/`; retained red witnesses and 39 passing controls. |

The complete [full gate](integration/full-gate-04.json) passes **2,020 tests with
zero failures, errors or skips**, required probes, PowerShell syntax and offline
packaging. It took **2,204.375 seconds**. The
[source bracket](integration/full-gate-04.source-bracket.json) confirms the
declared before/after/current input inventory is unchanged. The separate facade
suite passes **138 tests** in `integration/package-tests-02.log`. Focused scopes
overlap these totals and are not added together.

The current isolated installed qualification is
`data/cache/tether-051-installed-qualification-attempt02/QUALIFICATION.json`,
SHA256 `16fec5a9d5092fde373e72b0c7fa7eaa3b520750b515a82d908774e14d8c1f00`.
Its 14 commands cover wheel/source/installed equality, isolated imports,
externally anchored demos, source-inclusive policy verification and invalid
unused-input rejection before dispatch.

| Qualified local artifact | SHA256 |
|---|---|
| AsOf 0.3.12 wheel in installed attempt02 | `91926acf59cdec9c76af70ecc21d0a98ba0db77666113f1d3dfa9afb3dbd2d51` |
| TETHER 0.5.1 wheel in installed attempt02 | `c82267e7114700a417d759926e6b7216fc214ae824eddedd7d9af266d943aa2a` |
| Active executing archive profile | `645b1fb409b11f4d0e8d5d9e96e14f2b6302b1ecb5d03c64ddf5cfc8d683d016` |
| Aggregate validation | `1792d94ed55e806dc0f3fdcbf8c08684b899ad5ddd6c8e420bde4aba63a4b90d` |

## Retained failures and limits

Full-gate01 exposed a stale executing profile. Full-gate02/03 encountered distinct
Windows file-replacement access errors. These interrupted attempts, their logs
and manual terminal observations remain retained; they are not passes. The first
installed same-version candidate remains a separate artifact with different
hashes. No earlier record was promoted to cover the corrected bytes.

The peer stress review retains three explicit failures among 32 contended writes;
all readable snapshots were complete JSON. Bounded retry does not guarantee
availability, wall-clock completion or version ordering. Mutable writes remain
last-completing-writer-wins. The original access-error cause is unestablished.
No-clobber publication remains unchanged.

These are Windows/offline software checks, with $0 provider spending and no new
model, benchmark, clinical or biological evaluation. Linux execution, hostile
filesystem resistance and biological truth are not established. Original data,
scientific results, release artifacts, the downloader and stopped monitor remain
preserved. No public package publication or whole-project completion is implied.

Next is BG02: freeze the supported policy contract and independently expected
cases, implement a genuinely independent validator, and execute the equal-policy
comparison before SciFact, LAB-Bench and Inspect integration.
