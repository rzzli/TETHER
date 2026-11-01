# P09 release inventory review v2

Status: inventory complete; release qualification pending. V1 remains retained. This addendum closes the authorized test correctness issues and carries forward the package, cache, source-artifact, public-allowlist and rights inventory.

Three absent-Arrow skip sites now use the existing canonical source-audit reason. No skip whitelist was broadened. The third method-level case failed its new regression before correction. Its non-21.0.0 installed-Arrow branch remains unchanged and still cannot pass either core or full policy.

The POSIX peer issue was reproduced: 60 tests ran with 56 native-lock errors. A test-only context now injects fictional locking for existing nonsymlink files inside each test-owned temporary fixture. It cannot admit an outside, missing or empty inventory. Windows continues using native locks. Permanent regressions demonstrate that the unchanged native function still rejects simulated POSIX and is restored after the fictional context. No runtime or frozen P05 code changed.

Validation passed:

- 87 gate/source/peer tests on Windows, zero skips, 1.578 seconds. Log SHA256 `40e2b6e67e469edd67c8dd840f8ea344e99721e10fafac28a1485eda9f9eb632`.
- The entire 62-test peer module under simulated POSIX, zero skips, 0.578 seconds. Log SHA256 `036706e32e00fdd65ded7e14a39101201b1833ba90ba0bd36bd91ac429c924d8`.
- Earlier 69-test gate/contextual/dossier batch remains a separate retained pass. These batches overlap and are not additive independent evidence.

Current static discovery count is 1,971 methods: 1,911 directly declared class methods plus 60 dynamically installed peer cases in 152 modules. The six separately located P05 suites remain 199 methods. This inventory does not claim that a complete core/full gate or actual Linux suite has run.

The JSON binds all five changed test files, before/failure/after logs, 78 unchanged frozen P05 code anchors and 92 unchanged runtime payload hashes. Cached setuptools 84.0.0 completeness and all V1 release limitations remain applicable. Source-inclusive replay still requires the complete 137 originals and exact receipts, fixed twelve native units, every guard, all 38 outputs and 90 decisions.

Outstanding release work includes exact offline build/install validation, complete clean core/full lanes, explicitly qualified installed Windows source reconstruction, an explicit public file/hash allowlist, provider rights and separate rendering portability. Full old private-archive verification cannot be claimed after omitting or silently rewriting its sealed ancestors. Scientific validation, study independence, submission readiness and release approval remain unestablished.
