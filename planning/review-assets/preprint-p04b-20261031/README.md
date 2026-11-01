# P04b fictional interface qualification

**Current outcome: verified negative; branch closed.** The once-only READY-v2
run made two calls: the two-fact control passed and the eight-fact control was
malformed on value/unknown-reason agreement. The [independent audit](RUN-AUDIT-v1.json)
verifies code, retained bytes, usage and cleanup. No retry or model scaling
follows. Continue with the [deterministic paper scope](<../../Project Progress Reassessment 2026-10-31 - Deterministic Paper Scope.md>).

## Retained preparation instructions

This is a small engineering qualification of one prompt revision. It is not a
scientific study, biological evaluation, or fresh cohort. Accepted P04 remains
**0 strict successes in 5 model calls**. Its code, protocol, outputs and grading
are unchanged. Preparation uses public interface code, the P04 protocol and the
sanitized structural diagnosis; no protected human/clinical artifacts, old
candidate values, real references or external data are inputs.

`PROTOCOL-DRAFT-v1.json` denies execution. It prospectively declares exactly two
new fictional originals, their value-free binding skeletons, deterministic typed
expected reports, and prompt hashes. They describe imaginary toy labels and
counts. The first requests two fields. The second requests eight fields,
including a float, Boolean, ordered array, object, native null and empty string.
Each `sha256` binds canonical JSON of the declared fictional original, and its
JSON locator points to `/rows/0`. All values come directly from that original.
Expected reports are separate deep copies and never enter a prompt.

The original `typed_facts_v1` adapter and reporting guide are retained. The only
guide addition enumerates the complete five-key nested source object, the JSON
and Parquet locator shapes, and the status/facts/reason invariant. No adapter
repair, source lookup, backfill, omitted binding insertion, old-output regrading,
new wire, grammar conversion, retry or fallback is provided.

The prospective schedule has two cells, in fixed order, each at most once and
plain stage only. A transport failure stops generation and preserves later cells
as unexecuted. Structural adaptation and fixture comparison occur only after
affirmative owned-server cleanup; a malformed response is preserved unchanged.
Consequently a structurally malformed first response may coexist with a second
already-completed call, since structural grading follows cleanup. A limit stop
is a transport failure and is never graded or rescued.

The existing model revision, all three weight shards, 52 runtime inputs and server
configuration remain pinned. The server is owned through `OwnedServer`, with the
existing P04 `ListenerEvidence` host-view PID/loopback check on `127.0.0.1:55591`.
The setup cap is 900 seconds; startup is 180 seconds. Each cell retains the
32,000 input-token, 8,000 output-token, 300-second and $0 budgets, narrowed to one
call with model output capped at **2048 tokens**, temperature zero and seed zero.
The HTTP timeout is reduced again after durable request retention. Prompt byte
upper bounds reserve context conservatively; expected-output byte counts do not
establish actual token feasibility.
The inherited HTTP timeout bounds socket operations; it does not independently
cancel a response body that keeps delivering bytes. The final wall-clock check
rejects a late completion, but this small controller adds no hard-cancellation
watchdog to the existing transport.

New outputs use an exclusive run directory, exclusive byte writes and the existing
fsynced hash journal, bounded to 8,256 events/8 MiB with 64 KiB event details.
Request/envelope/content bytes and hashes are retained. Usage is measured when
available; potentially dispatched calls with missing usage retain a separately
labelled conservative reservation. `actual_calls` counts transport dispatch or
potential dispatch, not server-confirmed inference. Memory and physical IO remain
explicitly unknown when uninstrumented. No failed or uncertain attempt is repeated.

Success requires both strict typed outputs to match the declared fictional
expected reports, including complete bindings, native value types and valid
status. A production success additionally requires a valid `receipt.json` with
`status=qualified`, matching report and terminal journal hashes, and **no
`failure-receipt.json`**. A provisional qualified report or terminal journal entry
alone is insufficient: publication failures invalidate it and close the branch.
Any failure closes this qualification branch. No result authorizes model scale
or establishes biological, clinical or research competence.

Offline verification, from `D:\Projects\drug_target_agents`:

```powershell
& 'D:\Projects\drug_target_agents\.venv\Scripts\python.exe' -B planning/review-assets/preprint-p04b-20261031/test_qualify_prompt.py
& 'D:\Projects\drug_target_agents\.venv\Scripts\python.exe' -B planning/review-assets/preprint-p04b-20261031/qualify_prompt.py
```

The tests use an explicit mock server and non-network opener with the real
`TypedReportingClient`; they do not start a server or make HTTP/model calls. Dry
qualification constructs the pinned server specification only. The two prompts
are 3,187 and 5,556 bytes; the complete expected reports are 826 and 2,733 bytes.

Before execution, review this code and freeze a new
READY protocol, with `execution_allowed=true`, exact code and environment pins,
and an independently retained hash. `code_bundle` must contain the P04 helper's
complete `code_inventory()` plus `qualify_prompt.py`; `environment` must match
its `capture_environment()`. Those fields are deliberately unset in DRAFT.
Production additionally requires the exact protocol hash, explicit `--execute`
and a new `runs/preprint-p04b-*` directory. No execution was performed during
this preparation.
