"""Render measured engineering evidence, without turning simulation into science."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def load(name):return json.loads((HERE/name).read_bytes())


code=json.loads((ROOT/'data/cache/recovery-step9-native-validation-20261028/code-validation.json').read_bytes())
full=json.loads((ROOT/'data/cache/recovery-step9-native-validation-20261028/full-validation.json').read_bytes())
qualified=load('SIMULATION-QUALIFICATION.json')
installed=load('INSTALLED-REPLAY.json')
relocated=load('INSTALLED-RELOCATION.json')
assert code['status']==full['status']=='passed'
assert qualified['status']=='qualified_real_inputs_simulated_native_case'
assert installed['status']=='installed_native_simulation_replay_verified'
assert relocated['status']=='installed_native_simulation_relocation_verified'
result=qualified['result']
peak=qualified['peak_parent_working_set_bytes']
peak_text=f'{peak:,} bytes' if isinstance(peak,int) else 'Unavailable; PSAPI did not return a measurement'
text=f'''# Native adapter/controller engineering closeout

AsOf 0.3.9 implements the model-backed adapter and its mode in the existing
four-arm controller. Qualification here uses explicitly simulated process/HTTP
callbacks, actual approved offline tokenization and original receipt-verified
data. It establishes integration mechanics, not actual model behavior or science.
Engineering acceptance is recorded separately in `acceptance.json` once all
listed checks and immutable evidence have been rechecked.

## Changes and observed corrections

The one-use native adapter binds original-path v2 replies, exact token quotes,
approved model weights, payload/request fingerprints, ownership and earlier
deadlines. Explicit immutable launch/source capabilities and leases precede calls.
The existing controller shares source qualification, history, budgets, baselines,
cleanup, failure journals and sealing; recorded defaults are preserved.

Regression-first corrections cover parent expiry before spawn/after quote work,
native chronology, foreign wrapper attribution, separate simulation accounting,
root failure markers when accounting itself fails, and recovery of reported usage
after transport-close failure. Conservative journal reservations are not rewritten.
Original failing probes and fixture-harness corrections are retained in
[development findings](DEVELOPMENT-FINDINGS.md).

## Retained validation

- Full suite: **{full['tests']['run']:,} tests**, zero failures/errors/skips;
  {full['elapsed_seconds']:.3f} seconds. Probes, PowerShell syntax and offline
  dependency-free wheel/demo pass. All **{len(code['source_pins'])} pins** match
  before/after. Two protected outcome files were hashed only, not parsed.
- New regressions: 43 tests. Adapter/new-legacy component group: 53 passing;
  whole-case failure/mode/accounting group: 29 passing; later actual lineage
  admission integration: one passing; recorded-path regression group: eight passing.
- Default isolated installation: twelve synthetic interface preparations across
  three states, one invented native-wrapper acceptance, three negative wrapper
  cases, simulated accounting and all seven legacy archive families pass.
- All eight prior study releases (0.3.1–0.3.8) pass their preserved matching
  installed verifiers. Old outputs are not relabeled as new-version execution.
- Optional installed Arrow21 source/model-inclusive replay: **{installed['elapsed_seconds']:.3f}s**;
  run-bundle relocation: **{relocated['elapsed_seconds']:.3f}s**. All denied-access,
  dispatch and archived-code-execution guard lists are empty.

## Real-input simulated case and resources

The existing exposed IL6R/RA/inhibit/antibody case retains its original cutoff and
unspecified tissue. All five declared literature candidates are reconstructed;
one whole record is selected. Parent availability is nine observations; 65 inputs
remain missing. Incomplete collection is not biological absence. The inherited
genetic-study question's fit to these literature/resource annotations remains
scientifically unqualified; the source reports are fixture copying.

| Measurement | Observed |
|---|---:|
| Outer complete execution | {qualified['execution_seconds']:.3f}s |
| Same-environment read-only replay | {qualified['replay_seconds']:.3f}s |
| Actual offline tokenizer children | 6 |
| Simulated native stages / process | 6 / 1 |
| Actual model calls / servers / Python network requests | 0 / 0 / 0 |
| Pure results | 2 |
| Reserved input / output tokens | {result['input_reserved']:,} / {result['output_reserved']:,} |
| Fixture-reported input / output usage | 384 / 384 |
| Parent peak working set, including replay | {peak_text} |
| Retained run bundle | {qualified['retained_bundle_bytes']:,} bytes |
| Provider spending / new downloads | $0 / 0 |

Child peak memory and GPU peak were not measured. The actual model/server was
not loaded or launched. Python audit guards and fixed offline tokenizer arguments
do not constitute an OS-wide network attestation. An identical 36-file local
mirror of already approved model/runtime/acquisition files was hash-verified;
original sources, transport receipts, downloader and stopped monitor were untouched.

## Limits and next work

Run relocation requires caller-approved original source and model roots; it is
not independent raw/model restoration or a new backup. Verification is pure:
no server, tokenization, model call or archived helper executes. Fixture callbacks
are not imported by replay. Required source/model bytes and installed code are
rechecked independently of archived location strings.

Native grammar conversion/conformance and actual CPU/GPU/case-time feasibility
remain unverified. No real inference experiment ran. The next engineering gate
is [pinned grammar conformance](NEXT-GRAMMAR-GATE.md), then a separately declared
finite experiment if eligible. No permissive fallback, answer repair, automatic
retry or wider batch is authorized by this closeout. R07's negative disposition
and stop remain unchanged.

Independent human submissions are still pending. This work does not complete
source/question sufficiency, a fresh case frame, HR1–HR4, R10/R12, H5 superiority,
clinical labels/scoring, causal genetics or the original entire project.
'''
with (HERE/'CLOSEOUT.md').open('x',encoding='utf-8') as stream:stream.write(text)
print('Measured closeout written')
