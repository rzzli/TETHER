# Optional Arrow environment: five changed generated caches

Read-only AI engineering diagnosis, 28 October 2026 UTC. The [complete record](OPTIONAL-ARROW-DIAGNOSIS.json) checks all 760 copied files and their original source copies. No PyArrow import, package-code execution, environment repair, receipt rewrite or acceptance run occurred.

**755 destination files remain byte-identical to the copy-time manifest. Exactly five generated CPython 3.11 caches differ:** `ipc`, `types`, `util`, `_generated_version` and `__init__`, all beneath `pyarrow/__pycache__/`. There are no missing or additional files. All 760 original source copies still match their recorded hashes. Python sources, native libraries/extensions and distribution metadata remain unchanged.

For each changed cache:

- Its entire marshal payload is byte-for-byte identical to a fresh compilation of the unchanged corresponding `.py` using that cache's recorded compiler filename, `dont_inherit=True`, and optimization zero. Compilation created code objects; none were executed.
- Old and new code objects recursively match in every compared field except compiler filename, including bytecode, constants, flags, names, locals, line tables and exception tables. Both original and current payloads separately match their source compilation.
- Timestamp-cache headers use the same CPython magic and flags zero. Each header matches its respective source timestamp and source size. The copied old header fails the destination source timestamp check.
- The compiler filename changes from the original token-aware environment to the new optional environment. That path is six characters longer, matching the six-byte increase in each serialized payload.

All 751 cryptographically hashed distribution `RECORD` entries verify; `RECORD` itself is unchanged. The five generated caches are absent from that distribution record. Their original hashes nevertheless remain valid **copy-time** observations and must not be discarded or relabeled as current hashes.

[build_installed.py](build_installed.py) copies bytes without preserving source mtimes, records the original hashes, then runs a successful isolated `import pyarrow` without disabling bytecode writes. The new source timestamps are 06:08:27–29 UTC; the cache writes cluster at 06:08:35 UTC. Timestamp invalidation, source recompilation and filename rebasing exactly explain the observed bytes. This is consistent with the explicit build/import sequence; file timestamps alone do not independently attest the writer process.

The original failed [v3 acceptance attempt](ROOT-ACCEPTANCE-ATTEMPT-v3.json) remains failed, and the optional environment and build receipt remain untouched. This diagnosis does not prove arbitrary cache changes harmless, qualify native-library ABI or scientific validity, or establish that all 760 destination bytes stayed unchanged.

Any prospective exception should identify these exact five paths, preserve both old/new hashes and source/compiler/header proofs, retain strict original hashes for the other 755 files, and fail on any additional change. An explicit root-approved derivation record and independent review are required before adapting acceptance. This report introduces no acceptance-policy change.
