# B0 registry-content feasibility execution

Status: **in progress; origin request frozen, new result extraction not yet run**.

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
