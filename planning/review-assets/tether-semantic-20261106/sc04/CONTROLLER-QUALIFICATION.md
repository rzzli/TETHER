# SC04 controller qualification — technical pass, semantic failures retained

The original two-question, four-arm controller trial completed in
`data/cache/sc04-controller-qualification-attempt01`. Session 49444 exited with
code 0. No worker remains active from this trial. It used the pinned local model
and explicitly invented HTTP bodies; it made no public article requests and
evaluated no real benchmark questions. Provider spending was $0.

The executed code is retained at commit `92cdfd4`. Frame SHA256:
`e3bbb9ffa1407143c2f0f053bc98ed9749ca0234c0526fcbcbc609b7e7e990cf`.
Root receipt SHA256:
`8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0`.
The maintained replay accepts every phase. An independent standard-library
review passes **4,236 structural, source and native-response checks**, including
complete inventories, journal chains, exact tasks, source text, role separation,
native usage and successful process supervision. Its report is
[controller-review02/REVIEW.json](controller-review02/REVIEW.json), SHA256
`a443df7a2e04e0ec8849823c9cd2d0e0929a5755c048c16861eb37e731e56916`.

## What executed

| Phase | Scheduled units | Actual model calls | Worker elapsed seconds |
|---|---:|---:|---:|
| Question-only expansion | 2 | 2 | 12.672 |
| Lexical and expanded collection | 4 | 0 | 0.859 |
| Passage ranking | 4 | 4 | 13.281 |
| Four answering arms | 8 | 8 | 19.297 |

All calls completed without retries or truncated responses. Total measured
native usage was **3,773 input tokens and 433 output tokens**. Recorded peak
server working set was **9,444,311,040 bytes**; this is process RAM, not GPU
allocation. Separate resource samples and child supervision reports are retained.
Every owned model server stopped. Startup includes model asset verification;
these short cached runs are not production throughput estimates.

## Scientific limitations and decision

The Lumarin question is correct in all four arms. The Vesprine question
incorrectly selects insufficient information in all four arms despite citing
the supplied paragraph that directly reports reduced uptake. Thus **4/8 arm
answers match, representing 1/2 distinct questions**. These are correlated
repetitions, not eight independent validation questions. Two-passage pools also
do not establish ranking quality on a full sixteen-passage pool; the separate
retained model qualification includes that mechanics control.

The first reviewer conflated perfect fictional answer accuracy with controller
integrity and terminated at that assertion. Its failure and exact script remain
in `controller-review01/`. Review02 separates the technical result from the
semantic failure; it does not change candidates, rerun inference, or declare the
incorrect answers acceptable. The status is explicitly
`TECHNICAL_PASS_WITH_SEMANTIC_FAILURES`.

Proceed to the declared primary measurement with the already fixed prompts and
the same producer across arms. This is consistent with the execution plan's
separation of successful measurement from scientific improvement. The known false
abstention is a limitation to measure, not a reason to tune on benchmark answers
or discard cases. Prior model qualification also retained a false-abstention case.

## Engineering validation

**89/89** invented component controls pass in `component-controls-attempt15`,
including controller failure/capture handling, rejection of duplicate output,
invalid frames, different role projections, and changed packages. Attempt13's
four errors came from fixture code trying to overwrite exclusive published files;
the fixture correction and failed logs are retained. No production publisher was
weakened. Attempt14 also passed before additional server sampling was added.

The controller uses separate bounded processes for execution and replay, with
owned process trees, source pins, durable stage records and no automatic resume.
The independent reviewer is a separate implementation in this repository, not
an external human validation. Full199 production, supplied-source diagnosis,
scientific scoring and independent production reconstruction remain unfinished.
