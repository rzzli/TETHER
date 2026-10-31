# Finite converter harness review

AI engineering review, 2026-10-28 UTC (2026-10-27 America/Los_Angeles). This is a diagnostic-harness review, not an independent scientist review or native grammar qualification. Review was read-only except for this report and its audit metadata. No bridge, converter, tokenizer, model, server, network call or accepted framework test was run by this reviewer.

## V2 result: preserved failure before child creation

The exact reviewed v2 protocol is SHA-256 `30966db2bf9846f3280b3ff881e423cd66adeac175113157e326f196c034ed68`; the archived runner is SHA-256 `0a7ed19fc9b2ba450a4280efc153da2147ae5d96438a148e084818a8a2e6b1bf`. The original execution directory remains [preserved](../../../data/cache/r09-finite-converter-execution-20261028T041937Z/failure.json).

Independent inspection of the failure, parent attempt and hash-chain-validated journal establishes the following within the harness's retained evidence: zero subprocess audit dispatches, zero known spawned children, no PID, `spawn_succeeded: false`, empty stdout/stderr and no child-start event. There is no native result, terminal success report or receipt. The six-event journal ends in `build_failed`, with tip `ccbbabee8cc88504aff27af72435bc4cb6ed3bdc8deb85d41a209d2b5b3e54c5`. The `native_converter_dispatch` event records intent before `Popen`; it does not establish an actual process launch.

The shared once-only execution claim remains present. The failed protocol must not be rerun or its artifacts rewritten. These records provide no evidence about actual DLL ABI compatibility or converter behavior.

## Two harness defects

1. **DEVNULL blocked before launch.** The original guard treated Windows' NUL device as an unauthorized write. `Popen(..., stdin=DEVNULL)` opened that device before its subprocess audit event, triggering `RuntimeError: Writes limited to reserved diagnostic output`. The failure retains the denied `\\.\nul` path. The original static review did not identify this Windows setup interaction. The correction should permit only the exact NUL-device operation used for the child's stdin, retaining all other device/path restrictions; validate this through a harmless child rather than the native converter.

2. **Global deadline omitted final sealing.** In the archived runner, the final deadline check is at line 341; terminal-report/journal writing, inventory hashing and receipt publication follow at lines 346–355. The reported elapsed time is captured before that work. A deadline expiring during finalization could therefore produce a clean disposition with an earlier elapsed value. This is a source-level consistency defect; no observed 120-second overrun is claimed. Check the cooperative deadline during inventory and before/after publication, record finalization-inclusive elapsed time, and leave an authoritative failure marker/failed exit on overrun. This does not promise operating-system preemption of blocking filesystem operations.

## Required revised-protocol boundary

The author is preparing a separately named v3 protocol and fresh output/claim paths. Its exact runner/protocol hashes, narrow NUL exception, harmless-child regression evidence, deadline-failure behavior and dry run require review before root authorization. Do not transfer v2's execution claim or relabel its failure. Any native warning, timeout, incomplete capture, unsuccessful cleanup, ABI mismatch or conversion failure must close the finite gate negative before vocabulary loading. A clean converter return alone establishes neither grammar/EOG behavior, model quality, full-case budget fit nor scientific validity.

The initial static pass otherwise found no blocking issue in the fixed two-child allowlist, input/installed-software/native hash binding, exclusive output ownership, fail-closed diagnostic policy or exclusion of model/GGUF/server/vocabulary stages. These are bounded code-and-artifact conclusions, not an OS sandbox attestation.

## Verification performed

- Read and hashed the archived runner/protocol, failure, journal, parent attempt and empty captures; verified the journal using `asof.journal.read_chain` without execution or replay.
- Checked that the failure is a harness/setup failure preceding child creation, rather than a converter negative or a successful native call.
- Inspected the current prepared runner and effective protocol statically. Revised-protocol review is pending at this report's initial checkpoint.

Detailed hashes and verification facts are retained in [HARNESS-REVIEW-AUDIT.json](HARNESS-REVIEW-AUDIT.json).

## Frozen v3 follow-up: scoped clearance

The final static pass reviewed [v3 protocol](FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json) SHA-256 `a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0` and [v3 runner](run_finite_converter_probe_v3.py) SHA-256 `ff51edd0007c48a5c4be925f98020491e8ddac3fabe1b8e89e8c6a384567a817`. Its fresh output and once-only claim are separate from v2. The fixed stages remain one typed-JSON roundtrip and one schema conversion, at most two approved bridge processes, with no force option, automatic retry, vocabulary, GGUF, model or server stage.

H01 is addressed by an exception limited to the exact `os.devnull` string, `mode=None`, `O_RDWR | O_NOINHERIT` flags (130 on this interpreter), execute mode and an active child dispatch. Other paths and modes remain subject to the original write restrictions. The author-owned [three-case regression report](../../../data/cache/r09-converter-harness-v3-regressions-1793162150480679000/regression-report.json) passes with the exact current helper hash. It records one harmless Python child launched/reaped, three rejected unauthorized write operations, an inventory-expiry failure before receipt publication, and a post-receipt-expiry failure whose authoritative marker vetoes the receipt. These are synthetic harness checks; zero converter children were used. Earlier failed harmless-child attempts are preserved and are not native converter observations.

H02 is addressed in `finalize`: checks cover inventory traversal/hashing, receipt publication and seal-state publication. Finalization-inclusive elapsed time is returned; seal-state records its creation elapsed time. A late `failure.json` explicitly overrides any receipt or seal, and failure exits do not publish a qualified receipt hash. These are cooperative checks and cannot preempt a blocking operating-system operation.

The [exact-protocol dry-run report](../../../data/cache/r09-converter-dry-run-1793162263194648800/dry-run-report.json) binds v3 and records zero dispatches, spawned children, denied actions and native/model loads. Its report and journal were inspected, not rerun. The reported regressions and dry run are engineering evidence supplied by the author, independently checked against the current artifact hashes by this reviewer.

**No blocking finding remains for this exact bounded native diagnostic.** This clearance does not establish successful native execution. Actual ABI/roundtrip and conversion results remain for root's separately authorized once-only execution. A native warning or failure still closes the gate before vocabulary; even a clean converter return proves no grammar/EOG conformance, full-case timing fit, model quality or scientific validity. No accepted framework tests were rerun and no native execution was performed by this reviewer.
