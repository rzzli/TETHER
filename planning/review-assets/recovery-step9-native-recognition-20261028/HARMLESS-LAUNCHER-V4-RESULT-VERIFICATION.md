# Actual harmless-v4 result: retained failure verified

28 October 2026 UTC. **The v4 qualification remains failed. Resources satisfies its role-specific predicate; overflow retains an unexpected second lifetime association. Sleep and suspended-abort were not attempted. Native ABI remains held.** This read-only engineering review independently checks the retained result. The reviewer coauthored the inherited SDK draft, but did not author the v4 policy/driver or operate this run; no broader author-independent source-clearance claim is made.

The run is [r09-harmless-launcher-qualification-v4-20261028T202617Z](D:/Projects/drug_target_agents/data/cache/r09-harmless-launcher-qualification-v4-20261028T202617Z). Its exact protocol SHA-256 is `43dd462a3701c4abddc1196e345460277f85ac1e84d120154902d33ad95289f8`; root decision is `ace824856b3af8070e842020fa8dc10833310354cf559906edbee90ed67a8259`.

The [machine-readable verification](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-LAUNCHER-V4-RESULT-VERIFICATION.json), SHA-256 `42b8b38c6e582288d7f93b64663b2eb0482c033fd3ea44f7bc9d806c55af61a3`, retains all input/output pins, independently decoded raw samples and case/accounting checks.

## Integrity, ownership and failure persistence

- All **166** protocol input files still match their exact hashes/sizes. Checked input paths/ancestors have no symlink/reparse attribute. The effective protocol is byte-identical to the reviewed original.
- The output universe is exactly **17 files**. All14 early-receipt outputs and all16 terminal-seal outputs match; the only file outside the final inventory is the terminal seal itself. Its hashes bind the original receipt, primary failure and post-lease cleanup. No late/after-seal failure marker is present.
- All **30 journal events** have correct sequence, preceding hashes and canonical SHA-256. They retain two case reservations, two successful observed creation returns, suspended/JOB_LIST membership checks before Resume, one observed Resume count1 per case, each case report hash and the overall terminal failure.
- There are **168 unique leased paths**: the166 inputs, original protocol and effective protocol. Each has an initial admission and final recheck, yielding336 lease records. All validations match; all336 final close outcomes are observed closed without errors. The primary failure and failed receipt remain intact.
- The actual direct-worker identities38324/resources and32192/overflow match returned process/thread identities, canonical base interpreter, creation-time records and protocol-bound worker markers. Parent PPID was explicitly not queried; no PPID claim is inferred.

The final seal hash is `2a547f332a1732afbced83817093bb3ceaf774b586b11abc8b20a5e5b4950a75`; receipt `2ee304d1a54f0c3955b654c601189245839e4137d52ed4064602e925535bcac3`; cleanup `5d11b2c76ae26b2e4a22d957337d319c77e15c88496c6849362bc7f10d151573`. The primary error remains “Harmless case did not qualify: overflow.”

## Independent raw SDK decode

All eight accounting buffers decode as48 bytes containing four signed64-bit time fields and four DWORD counters; all eight PID buffers decode as136 bytes with returned lengths8/16 and bounded count/PID fields. Raw bytes agree with every stored decoded field, API result and error code. Query monotonic bounds are ordered.

| Case / stage | Total | Active | Terminated | Listed PIDs |
|---|---:|---:|---:|---|
| Resources / empty |0|0|0|none|
| Resources / before Resume |1|1|0|38324|
| Resources / running-first |1|1|0|38324|
| Resources / after wait |2|0|0|none|
| Overflow / empty |0|0|0|none|
| Overflow / before Resume |1|1|0|32192|
| Overflow / running-first |1|1|0|32192|
| Overflow / after wait |2|0|0|none|

**Resources:**0.734s, natural exit0, reaped, no cleanup errors. The complete marker/stdout/result agree on rejected384MiB allocation and exactly one intended rejected descendant attempt with WinError1816. The selected resources-only final2/0/0/empty predicate matches. Recorded peaks11,206,656B Job and9,973,760B process remain below their read-back256MiB limits; this review did not query those peaks live.

**Overflow:**1.000s, explicit expected cap exception, stopped exit125, reaped, no cleanup errors. Retained stdout is exactly65,536 `x` bytes; observed-at-least69,632 bytes and truncationtrue correctly preserve the cap event. EOFfalse leaves further bytes unknown and does not prove all intended73,728 bytes were written. Stderr retained/observed is0 with EOFfalse. The subsequent raw total2 contradicts the unchanged generic finaltotal1 expectation, and the case correctly stays failed.

## Unresolved scope

The pinned worker's overflow path writes stdout, sleeps and raises if not stopped; its planned `Popen` block belongs to resources. Therefore, the resources exception does not apply to overflow. The second lifetime count is a genuine retained counter change, not a decode mismatch. Its cause remains unresolved. Accounting can include failed associations; total2 alone does not prove another child ran user code, and a final empty list is not a complete lifetime census.

The record has no intermediate raw sample between the cap trigger and final post-termination observation that identifies when the extra lifetime association occurred. This review assigns no cause, relaxes no rule and makes no universal containment claim. The old active2 finding and all failed attempts remain preserved. The remaining modes have no case directories/reservations. No helper, probe, Windows API, native target, model, GGUF or formal verifier was rerun, and no source or retained artifact was modified.
