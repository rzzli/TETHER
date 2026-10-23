# B0 registry-content feasibility execution

Status, updated October23: **origin extraction and membership sealing complete;
follow-up preparation and final feasibility audit in progress**.

The [design](Clinical%20Validation%20Design%20and%20Data%20Feasibility%20Plan%202026-10-22.md)
and [B0 protocol](protocols/registry-content-feasibility-v0.1.json) define an exposed,
snapshot-state audit, not clinical success prediction. January2025 is the source
origin, January2026 the primary snapshot and April2026 a separate sensitivity.
The selected-member cap is32; the operational coverage threshold is90%.

## Prepared origin request

The original128 candidate order was reconstructed from historical origin data.
Both prior twelve-member packs remain exclusions. Their24 distinct IDs overlap
the candidate frame in12 records, leaving **116 origin result-state queries**.
Those116 are sorted for SQL only; subsequent membership selection retains the
original frozen order and uses origin information only. No selected roster is
represented by this request.

Plan: `data/benchmark/labels/registry-content-20261022/requests-origin-v1/plan.json`;
SHA256 `ed82b3583f70fd108ba52c96707d9f0dc59f63693acbd10784fb3f2c821078cf`.
The tracked [origin anchor](review-assets/registry-content-execution-20261022/origin-plan-anchor.json)
binds this exact plan, generated SQL, policy, schema manifest and executing code.
Archive/dump/technical-source hashes were checked during preparation. All earlier
clinical twelve-member runner guards remain unchanged.

## Implementation checks before dispatch

New B0 workflow and transport modules provide a separate source-inclusive entry
point with owned local-server lifecycle, read-only transactions, two exact reads,
monitored output limits, durable failures and no automatic retry. Source ancestry,
approved restore/runtime paths, candidate and exclusion packs, schemas and exact
query bytes are regenerated before execution. Transport polls output growth every
50ms, so a small overshoot is possible; oversized partial reads remain failures.

Independent adversarial receipt review initially reproduced eight accepted
forgeries. They concerned origin/follow-up identity, owned file locators, command
arguments/order, request fingerprint, archived code, lifecycle port and clinical
scope flags. Two later probes reproduced missing output-byte accounting checks.
All ten are corrected before real dispatch; their failing test outputs remain
retained. Further peer tests reject altered state proposals and differing repeated
source bytes. A previously green component test was not treated as evidence that
the broader receipt boundary was sound.

All **74 B0 tests** and **732 full project tests** pass, with no skips. Required
probes, PowerShell syntax and package/dependency-free demo checks pass. These are
fresh local checks, not a new hosted-CI result or scientific outcome validation.
The pre-dispatch peer independently checked48 named small/runtime/code/packet
pins, exact query/schema regeneration, candidate exclusions and preparation journal;
it did not repeat bulk archive hashes or inspect new outcomes.

## Remaining execution

1. Retain the pre-dispatch freeze in Git, execute origin-only reads once, and verify
   the complete extraction receipt against original/repeat bytes and command journal.
2. Reconstruct all128 screening dispositions and seal at most32 origin-absent
   members before any follow-up access. Unknowns and prevalent results are not replaced.
3. Prepare/freeze separate follow-up requests, execute January/April observations,
   then audit every selected state and retain native source pointers/coverage.
4. Measure resource use and missingness, apply the fixed coverage/class/stop rule,
   and record the finite feasibility decision before harder T6 work.

Clinical labels, numerical predictors, probabilities and scorer training remain
withheld. Full project completion is not claimed.

## October23 origin execution checkpoint

The origin request was committed at `9e40e15` before dispatch. It completed two
identical read-only extracts of116 NCTs:101 proposed `absent_in_snapshot`,15
`unknown`, and no proposed present states. These are registry-content states,
not efficacy labels or true event incidence. The complete extraction receipt,
source/code ancestry, native bytes, command arguments/accounting and lifecycle
were reconstructed before membership sealing.

The sealed roster has32 origin-absent members. All128 screen dispositions remain:
32selected,15origin-unknown,12excluded prior-pilot members and69eligible beyond cap.
No follow-up was used. The membership SHA256 is
`2dac62ca0c2b7fe37f8daa1c7da7b2b2ea7ada7e328c89830130c64cc5bf651d`;
the [tracked membership anchor](review-assets/registry-content-execution-20261022/origin-membership-anchor.json)
was committed at `27c0b26` before follow-up preparation.

The origin first read is41,109bytes, repeated exactly. Total runner time was
186.156seconds including source revalidation; source lifecycle/read time was
19.453seconds. Python-parent peak memory was114,282,496bytes. PostgreSQL peak
memory was not instrumented. The owned source server stopped cleanly and port55440
closed. Runtime provider spending and model calls were zero.

Follow-up preparation revalidates this source-bound seal and the separate
January/April2026 archive/restore identities. No follow-up has been dispatched at
this checkpoint. A new evaluator and20 synthetic/peer tests check source-order,
receipt, unknown, missingness-threshold and native-envelope audit behavior; its
full project validation and actual source acceptance remain separate checks.

## Follow-up preparation correction — October23

The first preparation stopped before any follow-up query: the newer archive
inspection receipts use `archive_sha256`/`archive_bytes`, whereas the older origin
receipt uses `sha256`/`bytes`. A real-format regression reproduced the assumption
failure. The loader now accepts the two explicit complete layouts, rejects missing
or conflicting identities and still verifies original archive/dump bytes. Failed
preparation, its journal and failing test output remain untouched.

The [compatibility amendment](protocols/registry-content-archive-compatibility-v0.1.json)
preserves verification of the exact archived origin execution after that loader
changes. Strict validation remains default; origin-receipt verification can use
only the original byte-pinned plan and its verified archived code. New dispatch
cannot use this exception and must match current executing-code pins. Old origin
outputs and membership are not rewritten. A fresh follow-up request is being
prepared;98 B0 regressions pass, including legacy-identity and strict-dispatch
checks. No follow-up results were accessed during either preparation attempt.

Before dispatch, peer review added two malformed-alias regressions. The parser
now rejects incomplete alternate identities and validates every supplied digest/
size type before equality (so boolean true cannot equal integer1). Both initially
failing probes now pass. The prepared v2 request is retained as superseded before
dispatch, with its preparation code copied unchanged. Fresh v3 request SHA256
`1d7bbd86e96eefe3c4908dc4b58858bd5b04351e88cbf06f289884f2fe7d9ba7`
binds the hardened code and the same membership. All100 B0 tests and758 full tests,
required probes, PowerShell syntax and packaged demo pass. Independent preflight
reconstructed the v3 plan, both source schemas and exact2187-byte SQL files, and
rehashes33 named small/runtime/code proofs. Bulk source verification was performed
by preparation and remains a runtime gate; the peer does not claim to repeat it.
