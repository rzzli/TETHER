# Windows replacement peer review

**Scoped pass with explicit contention failures.** Reviewed `serde.py` SHA-256
`fa910ce74c0766240eac3a64443b4b4baf7b6b64b064a1b028cda4ace66eb79c`.
The code changes only mutable JSON replacement: Windows-native errors 5/32/33
permit at most three replace attempts with 50/100 ms requested waits, using the
same staged/fsynced bytes. There is no destination deletion, permission change,
fallback copy, provider call or unbounded retry. An error code does not identify
the cause; this review does not diagnose the earlier full-gate errors.

Seven peer control families pass their declared safety contracts:

- A real Windows handle denying deletion produces native error 5; releasing it
  permits the second attempt. Both attempts use the same staged path and bytes.
  Mutating the caller's value after the first failure does not reserialize it.
- A persistently held handle fails after exactly three attempts and 150 ms
  requested sleep, preserving the original destination. Observed elapsed time is
  not a hard wall-time guarantee for filesystem calls or scheduling.
- Other native errors, errno-only denial, direct interruption and interruption
  during backoff do not trigger extra retries. A simulated non-Windows mode
  likewise does not retry; this is not native POSIX qualification.
- A cleanup failure preserves the primary I/O error or `KeyboardInterrupt` and
  attaches a diagnostic note. Its deliberately retained staged files remain in
  the ignored fictional output, rather than being represented as cleaned up.
- No-clobber publication still makes one `rename` attempt, never calls mutable
  replacement or backoff, and preserves the existing destination. `atomic.py`
  and `maintenance.py` match the earlier installed qualification byte hashes.
- All scheduled concurrent operations have observed terminal outcomes; each
  readable snapshot and final destination is a complete submitted JSON payload.
- A delayed older writer can replace a newer writer's complete value. Mutable
  `write_json` remains last-completing-writer-wins, **not compare-and-swap or a
  monotonic version store**. Callers requiring those properties need their own
  coordination; this retry does not provide it.

## Retained failed expectation and availability limit

The initial peer probe incorrectly required every contended mutable write to
succeed. Its real error 5 after the third attempt failed that assertion. Both
[the original probe](run_peer_v1.py) and
[its failed result](INITIAL-STRESS-RESULT.json) remain unchanged. The revised
probe records every distinct scheduled write and permits an explicit bounded
I/O failure while still requiring complete payloads and unchanged no-clobber
semantics. No retry limit or runtime source was changed to improve this result.

| Reader used during 4-writer contention | Scheduled writes | Completed | Explicit failures | Complete snapshots read | Reader I/O failures |
|---|---:|---:|---:|---:|---:|
| Native handle with read/write/delete sharing | 16 | 15 | 1 | 196 | 0 |
| Normal Python `Path.read_bytes()` open | 16 | 14 | 2 | 211 | 1 |

All three write failures were reported after three native-error-5 attempts;
neither mode left staging files in this run. These are small descriptive stress
outcomes, not an availability guarantee or an estimate of improvement over the
old implementation. The initial result did not retain full per-writer counts,
so it is not a quantitative baseline. Successful native sharing does not prove
the cause of failures in the original gate.

[PEER-REVIEW.json](PEER-REVIEW.json) pins both attempts, scripts and retained
results; [the revised output](peer-v2-console.json) is structurally identical to
its ignored `RESULTS.json`. No runtime or existing test was edited by this peer
review. **A clean full gate and fresh installed wheels remain required:** the
earlier installed attempt qualified the pre-retry source bytes and does not
qualify this changed candidate.
