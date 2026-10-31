"""Write measured correction closeout once every required operator check passes."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-duration-validation-20261028'


def load(path):return json.loads(Path(path).read_bytes())


full=load(CACHE/'full-validation.json');code=load(CACHE/'code-validation.json')
qualified=load(HERE/'SIMULATION-QUALIFICATION.json')
installed=load(HERE/'INSTALLED-REPLAY.json');relocated=load(HERE/'INSTALLED-RELOCATION.json')
assert full['status']==code['status']=='passed'
assert qualified['status']=='qualified_real_inputs_simulated_native_case'
assert installed['status']=='installed_native_simulation_replay_verified'
assert relocated['status']=='installed_native_simulation_relocation_verified'
result=qualified['result']
peak=qualified['peak_parent_working_set_bytes']
peak_text=f'{peak:,} bytes' if isinstance(peak,int) else 'Unavailable; PSAPI did not report a value'
text=f'''# Native duration consistency correction closeout

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

Full validation passes **{full['tests']['run']:,} tests**, zero failures/errors/skips,
with probes, PowerShell syntax and offline wheel/demo in {full['elapsed_seconds']:.3f}
seconds. All **{len(code['source_pins'])} code/resource/test pins** match before/after;
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
| Outer execution / same-environment replay | {qualified['execution_seconds']:.3f}s / {qualified['replay_seconds']:.3f}s |
| Installed source/model replay / guarded run-copy relocation | {installed['elapsed_seconds']:.3f}s / {relocated['elapsed_seconds']:.3f}s |
| Actual offline tokenizer children | 6 |
| Simulated stages / process / pure results | 6 / 1 / 2 |
| Actual model calls / servers | 0 / 0 |
| Reserved input / output tokens | {result['input_reserved']:,} / {result['output_reserved']:,} |
| Fixture-reported input / output usage | 384 / 384 |
| Parent peak working set including replay | {peak_text} |
| Run bundle | {qualified['retained_bundle_bytes']:,} bytes |
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
'''
with (HERE/'CLOSEOUT.md').open('x',encoding='utf-8') as stream:stream.write(text)
print('Measured correction closeout written')
