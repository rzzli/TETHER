# SciFact native policy component qualification

**Component tests pass; the complete G4 integration gate remains pending.** The
native extension implements source and execution policy for SciFact without fake
target identifiers, LLM prompts or token usage. It does not judge scientific
support and does not claim the complete therapeutic schema-2/BG02 contract.

`experiments/scifact/tether_adapter.py` reuses TETHER's `InputGraph`, `Snapshot`,
catalog roles, immutable serialization, stable reads, atomic publication and
hash-chained journal. Original transport receipts remain unchanged. A separately
sealed canonical representation binds the original event and is admitted only
for trusted preparation. Logical member/field products and consumer purposes
are then verified through the separately qualified preparation adapter.

The native context is supervisor-private. It contains the full preparation
manifest and must not be passed into the answering worker. It verifies and
freezes corpus/query views once per bounded operation, validates model asset,
producer and dependency pins, and requires exact fitting/index parent byte
proofs. A retained fitting session must show the same consumed input hashes and
produced numeric assets. A new computation may use eligible older inputs;
held-out reference ancestors remain prohibited.

Each accepted candidate binds its request, configuration, model, prediction,
retrieved document hashes and exact selected sentence bytes. Both SUPPORT and
CONTRADICT may pass source policy for the same valid source: scientific
correctness remains the native evaluator's separate responsibility.

Native sessions reserve outputs before dispatch, prohibit repeated attempts,
retain measured accounting after commit failure, stop after failures or budget
breaches, and explicitly account unexecuted scheduled cells. Verification
reconciles schedule, journal, requests, candidate decisions, terminal states and
resources. Time checks are boundary checks; the owning process supervisor
provides deadline enforcement and monitored memory. Byte accounting concerns
the worker's primary products: numeric model assets during fitting and candidate
payloads during prediction. Journal/log overhead is separate. Token fields are
null with `not_applicable_non_llm`; provider spending is zero.

## Retained qualification

- `green10.log`: **35 fictional test methods pass**, zero failures/errors/skips.
  The current test file is `experiments/scifact/tests/test_scifact_policy.py`.
  Root moved the new benchmark tests out of the default dependency-free suite
  after this run; the historical log truthfully retains its then-current
  `tests.test_scifact_policy` import name. Root's subsequent combined bracket
  qualifies the new test location.
- `red-budgets01.log` reproduces acceptance of internally contradictory byte/time
  limits. Runtime and verification now reconcile the breach with the disposition.
- `red-model-lineage01.log` reproduces inadequate fitting-parent identity when
  only claim IDs/product names were bound. Exact product byte proofs and the
  retained fitting execution are now required.
- `red-empty-schedule01.log` reproduces verifier acceptance of a self-consistent
  empty schedule that the runtime rejected. Both now use the same nonempty,
  unique string schedule validation. The scoring peer's independent probe is
  retained separately.
- `ACTUAL-CONTAINER-ADMISSION-ATTEMPT02-20261105.json`: actual pinned public archive
  admission and fresh reverification pass using installed AsOf 0.3.13. The policy
  source bracket is unchanged; original receipt bytes remain unchanged. This
  checks the original container only, not a fitted model or benchmark answer.

The initial missing-module red test and all intermediate runs remain. The first
post-implementation run hit sandbox temporary-directory access errors; subsequent
runs use workspace TEMP/TMP. A later fast-session regression exposed Windows
`time.monotonic()` granularity; elapsed native session measurements now consistently
use high-resolution `time.perf_counter()`. No performance number was invented.

## Remaining integration and limits

The policy-layer candidate tests stub only the trusted preparation verifier to
isolate policy behavior; actual projection reconstruction has its own data tests.
The actual trained model, worker/controller integration, fresh source-inclusive
verification and all scheduled SciFact predictions remain root-owned later gates.
Passing these controls is not completion of BG03.

The declared fitting execution and audited code do not mathematically prove model
coefficients were learned correctly or prevent malicious same-user filesystem
access. Independent source replay and retained external receipt anchors are
still necessary. No benchmark answer, external expert response, live model call
or scientific performance claim was introduced by this component qualification.
