# Native duration consistency correction closeout

AsOf 0.3.10 corrects a reproduced metadata consistency gap in the native verifier.
The prior pure probe accepted a wrapper duration of 9,999 seconds against 244.906
seconds allocated and a child report of 2.531 seconds. No original execution overrun
or full externally anchored resealed-run bypass was demonstrated. The original
0.3.9 wheel, run and reports remain preserved.

## Correction and verification

The concrete helper requires a complete typed budget, finite nonnegative native
duration strictly below the allocated cap, and—where the controller has a validated
child report—native duration no greater than report duration plus the existing
absolute 1 µs rounding tolerance. Reaching the budget remains expired. Controller
finalization and root replay invoke the check before accepting the cell. Generic
session/recorded/legacy behavior is unchanged. Only the initializer version changes
among declared legacy semantic helpers.

Thirteen regression-first tests cover over/equal budget, zero/inside values,
missing/malformed evidence, absolute tolerance and a whole-case report-duration
failure that preserves accounting without a root receipt or retry. The initial
seven-test batch records 17 expected failures. Final targeted groups pass 75
native/controller tests and eight recorded regressions; the component group of 25 passes.
Ruff checks pass. See [development findings](DEVELOPMENT-FINDINGS.md).

Full validation passes **1,737 tests**, zero failures/errors/skips,
with probes, PowerShell syntax and offline wheel/demo in 2361.641
seconds. All **324 code/resource/test pins** match before/after;
two protected outcome files were hashed only. All nine previous study releases
pass their preserved matching installed verifiers. The new default installed
wheel passes seven legacy families, twelve interface preparations, native-wrapper
fixtures and eight duration-positive/negative cases. Optional Arrow21 replay is
separate; the default runtime remains dependency-free.

## Fresh same-input simulation

The separately declared current-version case requalifies the same exposed IL6R/
RA/inhibit/antibody inputs under unchanged budgets. Five original candidates are
qualified, one whole record selected, nine observations available and 65 inputs
missing. The original contemporary cutoff, unspecified tissue and missing context
remain unchanged. No independent source/question sufficiency is established.

| Measurement | Observed |
|---|---:|
| Outer execution / same-environment replay | 295.922s / 61.203s |
| Installed source/model replay / guarded run-copy relocation | 79.734s / 76.359s |
| Actual offline tokenizer children | 6 |
| Simulated stages / process / pure results | 6 / 1 / 2 |
| Actual model calls / servers | 0 / 0 |
| Reserved input / output tokens | 24,558 / 6,144 |
| Fixture-reported input / output usage | 384 / 384 |
| Parent peak working set including replay | 497,668,096 bytes |
| Run bundle | 999,354 bytes |
| Provider spending / model downloads | $0 / 0 |

All six wrapper/report/allocation comparisons are retained as numerical resource
records and pass. Installed guard lists are empty: no original-run access during
relocation, live repository imports, archived code execution, model/tokenizer
dispatch or network. Replay requires explicit original source/model roots; it
does not restore the full raw/model collection independently. Child/GPU peaks are
unmeasured. Simulation does not establish actual model startup/inference timing.

## Entire-project status and next major gate

This completes the stated correction engineering checks, subject to the separately
sealed acceptance.json. It completes neither whole R09 nor independent science.
The owner-installed C++ tools work without restart. A typed actual-DLL converter
bridge is being built but has not run. Finish a prospective bounded ABI/converter
protocol before native use; incomplete-conversion warnings or unsupported behavior
close that gate negative and stop before vocabulary initialization. Do not anchor/
repair the frozen schema or silently select a permissive grammar to get a pass.

Retain a new full-project reassessment and critical next-step review at this major
completion, linked through the [assessment index](../../Project%20Progress%20Reassessments.md).
Fresh sources/cases, independent human references, review workload, H5 sizing and
R10–R16 clinical/genetics/extensions remain governed by their own prerequisites.
Human reviews are pending; empty features/null probabilities and R07's negative
stop are unchanged. The downloader and stopped monitor were not touched.
