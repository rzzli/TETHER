# Own-C++ harmless qualification v1 — retained failure verification

AI engineering review, 2026-10-28 UTC. Read-only verification of retained evidence; no worker, Windows API or target-library call was repeated.

**The batch remains failed.** The [verification record](HARMLESS-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json), SHA-256 `939a78fca943ab19a7c3774ea08a9456882cdd0bd14986c5c228711b51df7f1f`, verifies all 135 input pins, 17 output files, five directories, the 30-event journal chain, eight raw SDK snapshots and 274 lease records covering 137 paths. Early receipt, post-lease cleanup, terminal seal and authoritative failure marker agree. All 137 initial owned leases closed successfully; the 137 final recheck leases were already closed. No cleanup errors were retained. Elapsed time before the terminal seal was 2.234 seconds.

| Case | Retained observation | Qualification |
|---|---|---|
| Resources, PID 16824 | Natural exit 0, reaped; 0.718 seconds. A 64 KiB allocation control succeeded and was released; the 384 MiB request failed with error 1455. One explicit descendant attempt failed with quota error 1816. Peak job commit was 2,248,704 bytes. Final raw counters were total 2, active 0, terminated 0, empty PID list. | Meets the explicit resource-only expectation. |
| Overflow, PID 29880 | Cap triggered; 65,536 stdout bytes retained, at least 69,632 observed. Exit 125, reaped; 0.954 seconds. Final raw counters were total 2, active 0, terminated 0, empty PID list. | Fails the unchanged generic total-1 expectation. |
| Sleep and suspended abort | No case directories or dispatch events. | Unattempted after overflow failure. |

Both cases had total 1, active 1 and only their exact owned PID in the before-resume and running snapshots. These raw buffers were decoded independently and match the recorded observations. The second lifetime association in overflow is unexplained. The final empty PID list does not identify its cause or prove that a second process ran user code.

The pinned [worker source](harmless_launch_worker_native_v3.cpp) has its overflow branch at lines 277–280; it writes the bounded payload and sleeps before a failure path. Its explicit descendant creation is in the separate resource function; overflow does not reach that call. This source fact does not prove the absence of hidden binary or operating-system behavior.

The compiled worker therefore did not resolve the earlier Python-worker anomaly. Resource-only total 2 is not a generic policy change. The next gate remains the separately scoped, bounded PID/accounting diagnostic declared in the [root decision](HARMLESS-NATIVE-QUALIFICATION-ROOT-DECISION-v1.json), before any target ABI experiment. No target DLL, model, vocabulary, grammar, protected answer or scientific conclusion was qualified by this attempt.
