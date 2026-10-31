# Harmless-worker qualification v2: role-correct terminal status

**Preparation only.** The new `qualify_harmless_launcher_v2.py` driver requires a
separately reviewed protocol and root decision before real SDK construction.
The frozen `abi_parent_launch_draft_v3.py` stays byte-identical at
`c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4`,
with its original constructor and `execute_draft` hard-disabled. No global flag
is toggled, including in pure tests.

The separate derived constructor copies the exact public SDK binding table,
checked against the original AST, and inherits the original methods. Before
binding, it requires the harmless protocol role, canonical base Python and
worker `dc388b9a83d11d76ed30403658ee31f8cbf91276ffeafca1b6f91f9b49eb9811`.
Its `create_suspended` override permits only the four exact protocol-bound
Python/worker argument vectors, once each. No compiled ABI executable, runtime
DLL path or alternate target can reach it. The original `OwnedLaunch`, capture, raw snapshot and lease methods are reused
unchanged. The separate `harmless_launch_seal_v2.py` contains the v3 post-cleanup
function with exactly one executable AST difference: its successful status is
`harmless_launch_qualification_passed`. Cleanup, hashing, deadline and failure
semantics are unchanged; the seal is never rewritten after publication.

## Four once-only cases

| Case | Intended observation | Required disposition |
|---|---|---|
| `resources` | 256 MiB process/Job commit limits reject a 384 MiB allocation; the worker's single descendant attempt reports quota error 1816. | Normal exit zero, exact worker/result markers, bounded capture and strict final Job accounting. |
| `overflow` | More than 64 KiB stdout. | Exact capture-cap trigger, 65,536 retained bytes and a larger observed lower bound; terminate/reap owned Job and process. |
| `sleep` | Worker sleeps for 120 seconds. | The six-second execution allowance expires; terminate/reap within the eight-second whole-case cap. |
| `suspended_abort` | Durable callback injects an exception after creation, membership, identity and limits checks, before resume reservation/call. | No ResumeThread attempt and no worker-started marker; terminate/reap the assigned suspended process. |

These intentional negative triggers are explicit case observations, not hidden
failures. Unexpected exceptions, missing markers, wrong quotas, capture errors,
accounting differences, incomplete cleanup or deadline overruns fail the case
and stop later cases with their unattempted modes retained. There is no retry,
alternate launcher or relaxed Job-accounting path.

## Execution boundary and evidence

Creation uses the unchanged public SDK `STARTUPINFOEXW` path: Job membership at
`CreateProcessW` via `PROC_THREAD_ATTRIBUTE_JOB_LIST`, exactly three inherited
stdio handles, hidden/suspended creation and one checked resume. Empty and
before-resume raw accounting/PID buffers are journaled before validation. Strict
identity and membership checks precede the sole resume. The suspended-abort
callback raises only after the accepted journal durably records its checkpoint.

The resources case preserves the v3 ordering: **after-wait finished accounting
and Job peaks are read while its thread/process handles are still held**, then
the unchanged owner cleanup closes them. A mismatch fails qualification with
the raw observation preserved; closing first is not a workaround. All expected
stop cases also retain a final snapshot before ordinary cleanup.

Bounds are **60 seconds globally, eight seconds per case including two seconds
reserved for cleanup, 256 MiB process and Job commit, active process limit one,
64 KiB per stream, sixteen Job PIDs and forty snapshots per case**. The four
primary workers are fixed; the resources worker additionally contains exactly
one intended-to-be-rejected canonical-Python descendant attempt. Scientific
case budgets, including the existing 300-second default, do not change.

The reviewed phase protocol is copied byte-identically to the newly reserved
output's `effective-protocol.json`, since the pinned worker accepts protocol
files only under `data/cache`. Both copies and frozen inputs remain leased
through child execution, input recheck and early receipt publication. The
accepted 0.3.11 journal is used. Always-run post-lease cleanup retains close
outcomes and a required terminal seal; primary, late and after-seal failure
markers veto earlier statuses. The qualification copy writes the harmless-role
success status directly. It does not claim an ABI observation or target execution.

Pins cover the driver/worker, frozen SDK/design/peer, six installed SDK headers,
accepted environment/wheel and 85 runtime resources, verified finite OS v3
evidence `fd38ecebâ€¦d78288`, and new pure checks. The prior unexplained active-two
record is preserved; no general containment claim follows from the later OS
observation. No GGUF, E-drive or benchmark payload is opened.

## Pure validation and remaining gate

Eight pure checks pass with zero real SDK constructions or children. They test
the exact copied binding table, rejection of non-harmless roles/targets and
synthetic configs, once-only arguments, unchanged disabled draft, all four
synthetic case paths using the real accepted journal and terminal seal, an injected original-lease close failure that vetoes early success, and exact
AST comparison of the sealer body after normalizing only its success literal.
Fake workers
and timing results are explicitly marked; no model or flag bypass is used.

`--prepare` freezes the protocol and header metadata without constructing a
Windows SDK API. Independent/root exact-hash review must precede any `--execute`.
Actual harmless results then need independent receipt, timing, ownership,
resource, raw accounting and cleanup review. This scope authorizes no ABI EXE,
target DLL, backend, vocabulary, model, context, grammar or inference execution.

## Preserved preparation history

The prior protocol `3dc46083457f44ab185477d8c03c7fc36e8a5f1a5a1e1465593cd09f17be3808`
and every original referenced driver/checker/design/proof/header path stay
unchanged and unexecuted. V2 uses distinct filenames. The first v2 pure check
found a missing closure alias and a docstring-preservation mismatch in the
copied sealer; its failed report and source snapshots remain as
`HARMLESS-LAUNCHER-PURE-CHECKS-v2-first.json` and the `_v2_first.py`/first-sealer
files. Both were corrected before protocol preparation. The final eight checks
pass, including an exact OSError/handle-100 assertion for the intentional late
Close failure. No first or corrected preparation created a real SDK worker.
