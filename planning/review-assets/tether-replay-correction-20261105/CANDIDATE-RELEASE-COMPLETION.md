# TETHER 0.5.2 / AsOf 0.3.13 candidate release qualification

Recorded 2026-11-05 after the full gate terminated successfully. **Candidate release qualification: PASS.** This record covers the replay-verification correction, archive compatibility, packaging, and preservation checks. It does not declare the corrected BG02 comparison complete or establish scientific validity.

The finished-only aggregation is [RELEASE-AGGREGATE-FINAL01.json](RELEASE-AGGREGATE-FINAL01.json), SHA-256 `d966fa3f74fa5ace029a041642a279bcacef346aa70df65f7bc048733835b01e`. It was produced by checker SHA-256 `71ae52971d37376b73826b12d0373d8ac5a696b58d585ad08cc3627d33a3fc06`. The checker requires the final unittest count to be followed by unqualified `OK`; its retained invented-file red/green checks are described in [AGGREGATE-CHECKER-REVIEW.md](AGGREGATE-CHECKER-REVIEW.md).

| Qualified scope | Retained result |
|---|---|
| Full project gate | 2,100 tests; zero failures, errors, or skips; required probes, PowerShell syntax, offline packaging and dependency-free demo passed. Test execution took 2,176.468 seconds; the complete gate took 2,192.125 seconds. The 424-file source bracket matches the current checkout. |
| Focused replay correction | 25 tests passed; retained failing-first evidence and source fingerprints. |
| Archive compatibility | 52 tests passed; historical v1 byte-verification scope and valid historical v2 reconstruction preserved; invalid historical accounting still rejects. |
| TETHER facade | 138 tests passed with unchanged source and development-distribution metadata. |
| Installed candidate | Both wheels match current source/resource payloads and isolated installed payloads; 14 qualification commands have verified logs and expected exits. |
| Installed replay controls | A fictional eight-call replay verifies after removal of its copied original replay file. The retained EP075 counterexample rejects on source-inclusive core, archived-only core, and facade engine verification. Verification performs no backend dispatch. |
| Earlier experiment preservation | All 46 frozen source/evidence pins, 1,938 bundle files, 339 bundle directories, oracle/trusted-runtime anchors and old runtime pins remain unchanged. |
| Earlier installed release preservation | TETHER 0.5.1 / AsOf 0.3.12 qualification, wheel bytes, installed payloads and command logs remain unchanged. |

The focused, archive, facade and full-suite counts overlap. They are reported as separate qualification scopes and **must not be added** into a larger independent-test count. The checker self-tests are evidence-tool tests, not additional product tests.

## Exact wheel identities

The following retained wheels under `data/cache/tether-052-installed-qualification-attempt01/wheels/` are the artifacts used by the installed qualification and replay checks:

| Distribution and filename | SHA-256 |
|---|---|
| `asof_target_agents-0.3.13-py3-none-any.whl` | `b7446a71636841fe4ba96c0f94db6a42028d4358c6e452c843d0f7224c870ef2` |
| `tether_target_agents-0.5.2-py3-none-any.whl` | `8fa010170b5bff38fbc41cedaf877a0a2308edb2b649271a37fccf12f9822ac2` |

The full project gate made a separate temporary AsOf 0.3.13 wheel with SHA-256 `bb7392d1e30c2ea26f6470d87bac03eb7f621e67509ad076fa9ab8ec47edae34`. It is a separate build, not the installed-qualified wheel above. ZIP build timestamps can change a wheel's byte hash; this record does not claim byte reproducibility across these builds. The installed qualification directly checked its retained wheel package members against current sources and installed files.

## Completion evidence and limits

- Full-gate report: [integration/tether052-full-gate-03.json](integration/tether052-full-gate-03.json), SHA-256 `fd7247effe2b3a0f8186004c6a771b0fad5049fd558e8c1b29a5ec62d553bd3e`.
- Full-gate source bracket: [integration/tether052-full-gate-03.source-bracket.json](integration/tether052-full-gate-03.source-bracket.json), SHA-256 `2c6d428870cd4499943f27590aba0a6e40a325ef4787f771d1839d26b7c3aef6`.
- Full-gate raw log: [integration/tether052-full-gate-03.log](integration/tether052-full-gate-03.log), SHA-256 `7f855f96ca062bef39a5fa7d867a8b1a4a4a72ac4b323b20712b3b2d01215137`.
- Installed qualification: `data/cache/tether-052-installed-qualification-attempt01/QUALIFICATION.json`, SHA-256 `7486fc505eaff3351238b6c5d05c19d8e969eba8398753a72ac9670aff180315`.
- Installed replay index: [INSTALLED-REPLAY-VALIDATION.json](INSTALLED-REPLAY-VALIDATION.json), SHA-256 `3f99e17892ee6b67239548776538c3791de65e97841aca4a58391f40a294fcb6`.

The aggregate's `candidate_release_complete` is true and `bg02_scored_comparison_complete` is false. Earlier failed/partial qualification attempts remain retained. Original experiment results remain historical results of the old installed release. This qualification introduces no provider spending, new datasets, clinical evaluation, biological conclusions, or package publication. The final aggregation and this completion record changed no runtime source or frozen experiment artifacts.
