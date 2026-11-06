# Inspect integration interface and qualification checkpoint

This checkpoint describes new code under `experiments/inspect_policy/`. It does
not authorize the 109-case comparison or claim BG05 completion. Existing TETHER,
BG02, SciFact and LitQA2 sources and result artifacts remain unchanged.

## Balanced archive wrapper

`archive.execute_archive_case(row, output_root, *, validator=None)` is an
Inspect-free, standard-library wrapper. A row contains exactly `control_id`,
`bundle_root`, and `descriptor: {path, sha256, bytes}`. The descriptor path is
relative to the bundle. The caller reserves an empty output root; each case
exclusively reserves `output_root/control_id`. Input/output trees may not overlap.

The default validator is the existing in-process independent implementation.
The direct TETHER arm supplies its installed-reference validator explicitly.
The return contains the sealed `result`, `receipt` proof, `output` path and
`case_wall_seconds`/`case_cpu_seconds`. Case timing includes reservation, source
capture, validation and receipt publication; the result's `resources` contains
validator-call-only wall/CPU timing. Import and complete child timing remain
controller measurements. No file-byte quantity is labeled physical I/O.

The result retains schema version, control ID, completion/error/interruption
status, the complete native decision dictionary, error diagnostics,
implementation identity, descriptor proof and operation resources. The same
wrapper is used in all three arms. It does not import Inspect for direct arms.

`task.build_archive_task(rows, output_root, oracle_path, oracle_proof,
execute=None)` constructs the native Inspect Task/solver/scorer. The optional
trusted `execute(row, output_root)` callback lets the controller apply the same
per-case watchdog in every arm. It carries no oracle. The default is the common
wrapper, not a subprocess invocation of an old comparison worker.

Samples have empty targets. Expected outcomes are absent from inputs, metadata,
solver arguments and messages. The scorer lazily reads the external pinned
oracle only after matching the sealed case record and native output to the
sample ID. Decision and declared observable projections preserve missing versus
explicit null and compare declared dictionary subsets. Errors and unsupported
policies never become correct rejections. The controller's all-scheduled table
remains authoritative alongside Inspect's verdict-conditioned score.

## Live runtime interface

`runtime.build_runtime_task(rows, output_root, oracle_path, oracle_proof)` runs
the registered local `ScriptedProvider` through Inspect's actual `generate()`
path. These are scripted provider executions and fixture token counts, not
language-model capability, inference benchmarks or observed commercial billing.
Model and sample retries are explicitly zero; caching is disabled.

The extension owns private recursive evidence freezing, native source admission,
reservation before dispatch, complete request/configuration checks, claim
capabilities and conservative accounting. Mutable TaskState receives a copied
telemetry view only. The minimal native claim commit checks admitted fingerprints,
case/category/program eligibility and write-time availability, uses canonical
claim IDs, and can retain an exact reviewed prefix on an injected deadline.
Features with mismatched action/modality/tissue remain inapplicable while eligible
raw context can still be committed. This is not the full eight-specialist runner.

Hooks are non-authoritative telemetry. Required before/usage events are checked
before claims; an omitted required event rejects. An explicitly injected optional
hook exception after its durable before-event is reported as such, rather than
silently called a fully functioning callback. Events bind run, task/evaluation,
native sample UUID, epoch, control ID and reservation attempt.

The policy charges fully qualified responses using reported scripted usage.
Malformed/unqualified responses retain the prior conservative quote, even when
native logs expose separate observed counts. This follows the unchanged
EP-EXEC-02 convention. Fully valid overquote is measured and prevents later
dispatch. Unknown interrupted usage is never changed to measured zero.

`accounting.calls` counts durable `attempt_reserved` records: attempts to invoke
Inspect's generation workflow. It is not a physical-provider dispatch count.
`provider_entries` counts entry into the scripted provider guard, while
`provider_dispatches` counts requests that pass that guard. The deliberate
request-mutation control therefore records 1/1/0 respectively; temporal
preflight rejection records 0/0/0. This naming distinction must remain explicit
when comparing the archive's EP-JOURNAL-01 dispatch semantics. Each settled
attempt joins its reservation and request hash; interrupted attempts retain
their outstanding reservation and cannot automatically be dispatched again.

## Persistent witnesses, not yet executed at this checkpoint

`witnesses.prepare_witnesses(output)` constructs fresh invented native inputs,
16 task-only ordinary runtime rows and a separate prospective expected-field
oracle. It reads schema templates, not scored results or validator decisions.
The returned proofs are for the root to freeze before execution.

`witness_worker.py --recipe PATH --recipe-sha256 SHA --work NEW_DIR` executes a
trusted recipe with exactly `rows`, `output_root`, `oracle_path`, and
`oracle_proof`. It retains native JSON logs and each source context, response,
journal, result and receipt, plus the complete scheduled list. Optional
`--start-gate PATH` is a bounded explicit concurrency-test barrier. The parent
owns process deadlines, output limits and cleanup. It never invokes resume or
retry commands. A Python audit hook permits the exact Windows stdlib asyncio
socketpair and denies other network operations; it is not an OS sandbox.

The 16 ordinary rows cover native positive execution, zero-budget and chronology
gates, request mutation, immutable copied state, provider error, timeout,
malformed response, valid overquote, optional/mandatory hook failures, bounded
claim prefix, duplicate/unoffered selection and wrong-category selection.
Actual child interruption, concurrent reservations and stdout/EOF supervision
are separately named process witnesses. Positive review retry remains archive
coverage only because the live configuration explicitly permits zero retries.

`process_witnesses.interruption(output, rows, oracle_path, oracle_proof)` owns
one native worker, observes its durable provider-dispatch event, terminates that
exact process, and retains the incomplete journal and full two-case disposition
list. `concurrent_reservation(output, row, oracle_path, oracle_proof)` releases
two native workers from one barrier and retains both native logs plus the sole
winning receipt. These functions reserve fresh output directories. They do not
claim arbitrary descendant-tree termination or universal filesystem race safety.

## Retained qualification and corrections so far

- `archive-projection-red01.log` reproduced full-map comparison incorrectly
  rejecting an oracle's declared feature subset. `archive-projection-green01.log`
  passes all four corrected projection controls.
- `evidence-tests01.log` passes five controls for two-claim completion, one-claim
  deadline prefix with null `run_incomplete` prediction, immutability, invalid
  selection, applicability and chronology.
- The independent `policy/REVIEW-PROBES-01.log` identified cross-case scorer
  substitution, incomplete generation-configuration checks, output inside an
  input tree and cross-step duplicate claims. The maintained five-control
  `boundary-tests01.log` and the unchanged independent probe's second run reject
  all four defects. Original evidence remains.
- `native-tests01.log` and `native-tests02.log` exposed timeout classification:
  Inspect 0.3.287's `_eval/task/run.py` catches a bare `TimeoutError`, warns and
  proceeds to scoring. `native-timeout-diagnostic01.log` retains the actual
  mismatch. The extension now raises an operational `RuntimeError` after sealing
  the original timeout record, preserving its `TimeoutError` cause;
  `native-timeout-green01.log` confirms native `sample.error` plus conservative
  usage. No Inspect package source changed.
- `native-tests03.log` passes 12 real Inspect lifecycle tests on disposable
  invented data. Upstream ResourceWarning/DeprecationWarning messages remain in
  the logs. These unit tests delete temporary artifacts and are not substitutes
  for the separately frozen persistent source-inclusive witness run.
- `runtime-process-tests01.log` passes both actual native-process controls in
  15.905 seconds: post-dispatch interruption retains unknown usage and an
  unexecuted second case; concurrent reservation permits exactly one provider
  dispatch and retains the losing native sample error. These qualification
  fixtures are temporary, separate from the forthcoming persistent run.
- `native-tests04.log` passes the 12 native lifecycle controls in 42.391 seconds,
  now including the explicit omitted-hook row used by the prepared persistent
  inputs. It preserves upstream warnings and does not replace the independent
  reconstruction requirement.

Rehearsal01's independent reconstruction completed before these prospective
additions were applied. Its previous `test_native.py` bytes are retained at
`../controller/code-rehearsal01/files/experiments/inspect_policy/tests/test_native.py`
with the original frozen SHA-256
`ff4f7d285ade50634295d2ebfc191ef30bf61403818f93fdc4aa6a9788b4c060`.
The live omitted-hook test now exercises the explicit frozen row stimulus
instead of monkeypatching a callback; the historical log is not relabeled.

The prepared persistent input root is
`data/cache/tether-inspect-runtime-witnesses-20261106-attempt01`.
Its `PREPARATION.json` SHA-256 is
`b17fdfba429a913cb5a12bd1d1c5e0388031066ed45d7e93fca6c931fa55077c`.
It binds 176 input files / 212,941 bytes, the 16 ordinary row expectations and
separate interruption/concurrency schedules. `prepare_runtime_inputs.py`
constructed these files without native execution. `run_process_witness.py`
provides the root-supervised one-shot entry for each process group, requiring
the external preparation hash and checking its complete inventory. Neither
entry point was executed on these retained inputs at this checkpoint.

This is an evolving component checkpoint. Later additions such as the persistent
worker and explicit omitted-hook stimulus require the final combined source
qualification before their current bytes can be called qualified. No prior test
log is relabeled as evidence for source that changed afterward.
