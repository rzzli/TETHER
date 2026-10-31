# Failed harmless-native v2 build: retained result verified

28 October 2026 UTC. **Verified compiler failure; no link or worker execution occurred.** This read-only review reran no compiler/helper/API and changed no original source/output.

Run: [r09-harmless-native-build-v2-20261028T205613Z](D:/Projects/drug_target_agents/data/cache/r09-harmless-native-build-v2-20261028T205613Z). Protocol SHA-256 `82e7e1e217a44e2b3118aeb0041f6e61e741a139589731a61b1b1bc1ab0cd469`; root decision `7554084e59bf05dbd5b1f684a754db1f6ee6a8ff756d4435ea6a063329d44b2f`.

- All212 unique input hashes/sizes match. Source v2 and its prepared copy are byte-identical at `c22e5b781a2beb1fb82c70382b036b608582dad19f60b36540f1bc51832d1f60`; checked ancestors are reparse-free.
- Exactly10 output files are present. All seven early-receipt outputs and all nine terminal-seal outputs match their hashes/sizes; the seal itself is the only file outside its inventory. Failed status, primary marker and context-cleanup record agree.
- All five journal events rehash correctly. One compiler attempt matches the approved argv, attempt file, report and terminal journal entry: PID7328, exit2, reaped, no timeout/cleanup error,0.578s within45s. `/MD`, `/W4` and `/WX` remain enabled. Captures retain complete2,340B stdout and1,156B stderr.
- Compiler diagnostics identify C4244 (`wchar_t`→`char` possible loss), promoted to errorC2220 under `/WX`. The instantiation points to own source line270: `std::string expected(expected_w.begin(), expected_w.end());`. The `/utf-8` source flag does not supply an explicit wide-to-UTF8 runtime conversion.
- No linker dispatch, object or executable artifact exists. Fixture/ABI EXE executions, target DLL loads, model reads and network requests remain zero in the retained source/report scope.

The cleanup context returned without error/deadline expiry, and its record binds the original failure and receipt. This is `ExitStack.close`/`stable_files` context outcome evidence, **not individual-handle close attestation**. The terminal records1.797s before sealing; a later total is not invented. Receipt SHA-256 is `bf9d19bf6816df4ad4e19d01c0407a9cbdd99cf8d706abfe7e5dddb40df49f5c`, terminal seal `594c3ccfab610e537cbb5c3f85890090381f81fd164ebad037658f077204f863`.

[Machine-readable verification](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-NATIVE-BUILD-V2-RESULT-VERIFICATION.json), SHA-256 `e5ea27f9e67561e84c2b04a2a7e6face657853fbb1a561205385568608a8988d`, retains the exact output proofs and findings. Original v2 source and failure remain immutable. A new explicit conversion correction requires a separately versioned build; it does not pass or repair this attempt. Native launch and ABI gates remain unqualified.
