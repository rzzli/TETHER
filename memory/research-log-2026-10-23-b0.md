---
name: research-log-2026-10-23-b0
description: Resumed B0 origin execution, sealed membership and follow-up preparation correction
metadata:
  type: project
---

# B0 execution — October23

User requested continuation through remaining planned steps. Preserve that broad
goal; completion of a preparation stage does not complete the project.

Committed pre-dispatch origin request/code at9e40e15. Origin run completed at
data/benchmark/labels/registry-content-20261022/extraction-origin-v1; report SHA
32f1c86577342f7965a046b68ae61fbd8365a02b2736c803bb756daf39b46adf.
116 NCTs read twice exactly,41109B each;101source-absent/15unknown. Owned PostgreSQL
server stopped/55440closed. Total186.156s, source19.453s, Python-parent peak
114282496B; PostgreSQL peak unmeasured. No clinical labels or model calls.

Source-inclusive receipt reconstruction sealed32 origin-absent members at
membership-v1/membership.json SHA2dac62ca0c2b7fe37f8daa1c7da7b2b2ea7ada7e328c89830130c64cc5bf651d.
All128 screening dispositions:32selected,15unknown,12prior-pilot exclusions,
69eligible beyond cap. Anchor committed27c0b26 before follow-up preparation.

First source-only follow-up preparation failed before queries, retaining
requests-followup-v1: newer archive inspection receipts use archive_sha256/
archive_bytes instead of sha256/bytes. Real-format regression reproduced the
failure; archive loader now normalizes both complete layouts. Exact frozen origin
planed82b358... has a verification-only compatibility allowance using archived
code; new dispatch is strict and checks live executing-code hashes. Existing
origin output/membership are never rewritten.

New registry_content_evaluation module verifies follow-up receipt/source/code/
command semantics, audits each selected native envelope, separates April from
January, and applies90%/class feasibility rules without enabling training.
Eight root plus12 peer tests pass. Evaluator code is archived/pre-post checked.
Full752-test pre-amendment and756-test amendment suites passed; no new hosted CI.

Current boundary: follow-up preparation-v2 is revalidating original source bytes
and origin membership; no follow-up query has run. Root code must remain fixed
while this process is live. Peer identified two malformed-alias edge cases
(incomplete alternate pair, bool/int equality); current pinned source receipts
are unaffected, but these should be corrected with regressions before final new
request freeze. Preserve any v2 request as superseded, not as a failed extraction;
prepare freshv3 after code fix, never dispatch under stale code hashes.

Execution handles are observations, not durable proof of continued liveness:
last observed prepare-v2 unified exec session90070, PID29296. Re-poll the same
handle/check journal/process before deciding completion/failure; never restart
because an observation timed out. Full756-test validation session14052 completed.
Actual files/journals/results are authoritative on resume.

Next: finish the archive-loader edge guards, freeze/execute follow-up on sealed32,
audit all96 selected snapshot states and apply the finite decision; then harder
T6 top-one challenge. Proposed T6 needs a separate versioned cap1 contract shared
across baselines, role schemas, backend and verifier, exact source-only task
selection and sealed independent AI references before model outputs. No clinical
prediction, genetics features or T2–T5/H6 activation from operational states.
