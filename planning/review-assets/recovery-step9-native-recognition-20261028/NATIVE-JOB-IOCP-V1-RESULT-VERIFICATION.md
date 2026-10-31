# IOCP diagnostic v1 — retained negative result

AI engineering evidence verification, 2026-10-28 UTC. The reviewer coauthored the status-only sealer and separate pure metadata tests; this is not independent review of the whole implementation or scientific review. No API, worker, model or verifier was rerun.

**The diagnostic remains failed and establishes no launcher qualification.** The [verification JSON](NATIVE-JOB-IOCP-V1-RESULT-VERIFICATION.json), SHA-256 `25c648a168c5d836acb44e080ba8c4219c2d38068d15174ab35a92701d5beec5`, verifies all 176 current input pins, exactly 12 files, the 49-event journal chain, eight raw SDK snapshots and ten metadata-query results. All 356 lease records over 178 paths, owned close outcomes, early receipt, post-lease cleanup, authoritative failure and terminal seal agree.

The private queue retained nine normal returns: two `NEW_PROCESS` packets, one `ACTIVE_PROCESS_ZERO` packet and six current-empty timeouts. All packet keys match the fixed protocol key. Ten ordered queries cover two separately held handles:

| Reported PID | Same-handle observations before explicit stop |
|---|---|
| 19276 | `GetProcessId` matches; image path string is the pinned own worker; exact-Job membership is true; zero-time wait returns timeout. Creation FILETIME: `134376984869609582`. |
| 24584 | `GetProcessId` matches; image path string is `C:\Windows\System32\conhost.exe`; exact-Job membership is true; zero-time wait returns timeout. Creation FILETIME: `134376984869709355`. |

The raw UTF-16 buffers independently decode to these reported strings. Neither image path was opened or hashed by the observer or this review; the secondary string is not a verified binary identity. Both exit FILETIME values remain explicitly undefined because the preceding waits were not signaled. Historical notification identity remains unconfirmed; PID reuse before open remains a documented limit.

Raw pre-stop snapshots show total 2, active 2 and PIDs `[19276, 24584]`. Both `NEW_PROCESS` returns and metadata queries precede the owned-Job termination reservation in journal order. This locates parent observations, not kernel event times or creation cause. The first raw query after successful termination shows total 2, active 0 and an empty PID list while both observer handles are still held. The held-after-reap and released-handle snapshots also show active 0. Both query handles and the completion port closed successfully; all four required stop boundaries are retained.

The strict running counter finding stopped the attempt before the capture cap: stdout/stderr retained zero bytes, owned exit 125/reaped, whole-case time 0.328 seconds. Parent elapsed time before the early receipt is 0.875 seconds and before the terminal seal 0.937 seconds. `diagnostic_completeness=true` records the presence of the required bounded observation/cleanup records; the terminal outcome remains negative and no generic total-2 allowance follows. This one run supplies an additional current-Job-member identity observation. It does not retroactively identify the second association in earlier attempts or establish why it was created.

The frozen [source](diagnose_native_job_iocp_v1.py) retains a known reservation gap: the queue call occurs at line 156, while its count/row is appended at line 165. An exception after the underlying API returns but before the wrapper returns can leave an unknown call. This attempt has nine normally retained return rows, no observer error or interruption indication, and an explicit strict-counter stop; there is no evidence that the gap triggered here. These facts do not prove a general call-budget or interruption guarantee. The source and actual evidence remain unchanged; no automatic repeat is justified by this review.

The separately retained [component binding](IOCP-METADATA-FINAL-SOURCE-BINDING-v1.json) confirms that the final helper uses the query and Observer ASTs covered by the twelve pure adversarial tests. It does not qualify the untested real API paths. Target ABI, vocabulary, grammar, model and scientific gates remain open.
