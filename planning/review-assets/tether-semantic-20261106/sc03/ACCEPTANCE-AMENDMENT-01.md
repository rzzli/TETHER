# SC03 acceptance amendment 1: exact event coverage

Added during the frozen five-condition execution, before native scores or
scientific comparisons were calculated. No producer, model, input, output,
threshold, condition, metric or bootstrap setting changes.

The production auditor validates every expected pair/claim commit and the
receipt-bound journal chain, but does not reject every possible extra terminal
event. A retained fictional counterexample inserts and re-seals a contradictory
`pair_failed` event after a successful pair. The original auditor accepts that
fixture. The supplemental exact-order gate rejects it and passes five positive
and adverse controls. See [regression](extra-event-regression-attempt01/REGRESSION.json).

Final SC03 acceptance now requires **both** the original source-inclusive
auditor and [strict_events.py](strict_events.py). The latter reconstructs the
complete expected sequence from the frozen request schedule and retained pair
dispositions, including every start, terminal and commit. It also reconciles
the complete supervisor signal stream, per-claim deadlines and supervisor
observed-case counts. Unknown, extra, duplicate, contradictory or reordered
events fail acceptance. This is an added engineering check, not a change to
the scientific analysis or selection of successful cases.

The supplemental report captures post-execution hashes of every worker and
supervisor file, including the signal stream not listed individually in the
worker's scientific-output receipt. Such hashes establish observed bytes at
review time; they are not continuous host attestation or proof against a
malicious same-user rewrite of every authority.

The frozen auditor and running sources remain unchanged so their execution
fingerprints continue to verify. Its standalone `verified` status is
insufficient for stage acceptance. Require the supplemental report, independent
source/native/bootstrap reconstruction and final root acceptance as well.
