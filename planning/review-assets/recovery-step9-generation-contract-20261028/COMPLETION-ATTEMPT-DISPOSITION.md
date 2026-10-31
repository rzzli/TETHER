# Matching-version completion: seven retained plus three new results

28 October 2026 UTC. This is a verification-harness disposition, not scientific
or native-grammar acceptance. The original [primary attempt](FROZEN-VERIFIER-CHECKS.json)
remains `failed_or_incomplete`, with SHA256
`c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50`.
It passed seven versions, timed out at 0.3.8 and never dispatched the 0.3.9/0.3.10
replays. Its partial files and failure record are preserved.

The [prospective amendment](AMENDMENT-2-FROZEN-VERIFICATION-RECOVERY.md) corrected
the outer whole-process sizing after the [timer-scope diagnosis](FROZEN-TIMEOUT-DIAGNOSIS.md).
New 360-second verifier ceilings include setup and cleanup; they do not change
the 300-second scientific case budget or the existing inner replay deadlines.
The seven successful reports were rehashed and reused, never rerun.

Two unexecuted completion preparations remain preserved. Peer review found
exception-finalization and deadline paths that could misstate success or omit an
authoritative failure. The final v3 helper forces failed body status, conditions
publication on failure-free state, unconditionally attempts journal/lease cleanup
and rejects whole-child and post-lease aggregate overruns. Four in-memory stub
fault fixtures pass; these fixtures launched no actual children. Their final
[result](FROZEN-COMPLETION-v3-FAULT-RESULTS-final.json) binds the executed helper.

After root and independent AI engineering review of all 462 pins, the exact
[v3 protocol](FROZEN-COMPLETION-PROTOCOL-v3.json), SHA256
`75b44d1b2bfbafb7910d8e894d77dba550aae4970b1c5931bcaa9e7f6da34087`,
ran once under its [separate execution decision](FROZEN-COMPLETION-ROOT-EXECUTION-DECISION-v3.json).
All three metadata checks and three unchanged installed replay helpers passed.

| Replay | Whole-process seconds | Outcome |
|---|---:|---|
| 0.3.8 | 103.937 | Passed; PID 18780 reaped |
| 0.3.9 | 77.969 | Source-linked simulation/relocation verified; PID 30304 reaped |
| 0.3.10 | 78.157 | Source-linked simulation/relocation verified; PID 34496 reaped |

The completion parent exited zero after 262.937 seconds, including finalization.
Its failure marker is absent. All current 327 source pins and retained report
identities match. These observed timings do not establish a speed improvement,
worst-case bound or actual-inference feasibility; process peak memory was not
measured by this wrapper.

The new [combined qualification](FROZEN-VERIFIER-COMBINED.json), SHA256
`17afefc0ac2b83c76bc8974c68a366ea779379fb42199911c494da5967d9d5eb`,
explicitly binds seven retained successes and three declared completion successes.
It does not relabel the first attempt as passed. Completion failure markers
override that combined record. No model, tokenizer, native target, provider or
network work ran in this completion attempt. Older source/model-inclusive replay
does read its original authorized file proofs; it is not a model-free claim about
all previous project execution.

Final package acceptance still requires independent result verification and the
unchanged full, installed, corpus, wheel and preservation gates.
