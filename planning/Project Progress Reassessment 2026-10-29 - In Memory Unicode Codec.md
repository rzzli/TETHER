# Project reassessment after the in-memory Unicode codec

29 October 2026 UTC. The corrected pure Unicode pack codec passes scoped acceptance. Archive-checker and actual file-port work remain incomplete; no new native experiment has run. R09 and the entire project remain unfinished. The installed C++ tools already worked without restarting.

Root [codec acceptance](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-unicode-codec-20261029/UNICODE-PACK-CODEC-SCOPED-ACCEPTANCE-v2.json), SHA `3455f28244a44ed17612d80b6d452430b1963100e08ca072233ca87f4e4a64d6`, binds source `8ff0d622...`, eleven author methods, three focused regression methods and eleven independent methods ([peer](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-unicode-codec-20261029/UNICODE-PACK-CODEC-INDEPENDENT-PEER-REVIEW-v2.json), `199157f7...`). Independent integer-to-byte reconstruction matches all 84 records, the 188-byte header and full 37,766-byte encoding. The complete new pack existed only in test memory; no runtime pack file was written.

Root independently found that v1 wrapped a callback UnicodeError as a data CodecError while copying an ID ([before evidence](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-unicode-codec-20261029/UNICODE-PACK-CODEC-CALLBACK-BEFORE-v2.json), `f0d6be2b...`). V2 moves the byte take outside the data-decoding exception handler. All 720 independent UnicodeError-family probes at 180 before/after ID-copy points preserve the original exception object; genuine invalid ASCII/UTF8 still produces the intended data error. V1, its original limited CLEAR, later HOLD and before/after evidence remain preserved. Pack bytes are unchanged: SHA `d2537df43e7e6e8113c4e08f0536c2e3a698bd274963ab71a4efced4fa32c8ab`.

The factory validates exact new captured source bytes and issues an ordinary immutable profile; it authenticates no original path or live source. The bounded codec enforces field types/counts/hashes, ordering, caps, truncation, duplicates and full consumption with required cooperative check callbacks. Runtime/profile/original-source qualification remains false. The pure decoder is not the native observation-trace validator, a bridge, parent or actual file preparation service.

[Wire preparation](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-unicode-wire-20261029/UNICODE-WIRE-FRAMING-SCOPED-ACCEPTANCE-v1.json), `79a61e59...`, separately accepts schemas, finite enums, 25 literal fragments, 22 rows and fourteen negative/partial histories. Size-only and isolated schedule examples are not complete valid traces. [Archive preparation](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-archive-bytes-20261029/CAPTURED-NATIVE-ARCHIVE-PREPARATION-ACCEPTANCE-v3.json), `629216db...`, accepts corrected source-format/locator/conditional-map expectations and 32 literal synthetic captures; expected graph outcomes were authored before checker code.

The first archive implementation exposed callback-error and child trailing-LF handling gaps before peer review. Its separate v2 passes ten author methods/all 32 baseline projections, but independent review holds it for two more concrete issues: a legitimate already-closed lease has null close_success, and a bounded huge interval integer raises OverflowError during numeric validation ([peer HOLD](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-archive-bytes-20261029/CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json), `1a48b0e0...`). A narrow v3 correction is authorized; preserve v1/v2 and every witness. Passing the existing fixture set does not complete this checker.

File-port design v2 has independently cleared its metadata-only drive-root correction ([peer](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-file-ports-20261029/FILE-PORTS-INDEPENDENT-DESIGN-REVIEW-v2.json), `d6c03181...`). It covers fourteen file APIs, declared Win64 layouts, namespace ownership versus readiness, raw return registration, known bytes before hashing, distinct file/search closers, quotas and publication order. There is no file-port implementation or live API qualification yet. Closed fake call/ownership/clock vectors must precede that source work.

Earlier source/pure byte-oracle, coverage-analyzer, bootstrap, journal and Job-byte/phase acceptances retain their scopes. No old CPU/GGUF/pack pass, actual archive replay, target/SDK/compiler invocation, new data download or provider spending occurred. The original 189-case profile remains failed; the original whole-check remains INCOMPLETE_TIMEOUT. No source acceptance repairs either or establishes scientific usefulness.

## Complete recovery status

| Item | Current status and remaining gate |
|---|---|
| R01 | Accepted scope, governance and exposure boundaries. |
| R02 | Accepted tested checkpoint and restoration inventory. |
| R03 | Accepted scoped archive compatibility/relocation; complete raw/model/host restoration separate. |
| R04 | Accepted reproduced core correctness fixes. |
| R05 | Accepted bounded diagnostic preparation; stronger-model sufficiency unresolved. |
| R06 | Accepted reusable infrastructure slice. |
| R07 | Technical diagnostic closed negative; independent human assessment pending. |
| R08 | Partial source/exposure preparation; no scientifically qualified fresh case. |
| R09 | Application 0.3.11 and scoped pure oracle/controller, fixtures/analyzer, bootstrap/journal, Job-byte primitive and in-memory Unicode codec accepted. Actual archive/resource/source/profile/platform/entry/integration, native coverage, masks, integrated resources and usefulness remain unfinished. |
| R10 | Independent human development pilot pending source, engineering and human prerequisites. |
| R11 | H5 estimand, power, amended protocol/preregistration and analysis freeze pending. |
| R12 | Locked H5 execution/report pending qualified mechanics, protocol and final panel. |
| R13 | Alternative clinical outcome source conditional and unqualified. |
| R14 | Regional genetics/compatible LD, causal features, predictors and scoring/calibration conditional and unqualified. |
| R15 | Original clinical comparisons and ablations conditional and pending. |
| R16 | Individually gated T2–T5/H6 extensions and reproducible release pending. |
| HR1 | Human recruitment, domain matching, conflicts and exposure records pending. |
| HR2 | Two independent orientation submissions and measured workload pending. |
| HR3 | Fresh source-only references, reviewer coverage and masked ratings pending. |
| HR4 | Sized final panel and independent adjudication pending. |

Accepted TETHER 0.3.11/default v2 remains unchanged: 1,774 retained passing full tests, 327 source/resource pins and ten matching preserved-version qualifications. No fresh full application test run is claimed for these private components. Optional Arrow remains 755 unchanged files plus five separately source-equivalent caches. Data/science remains 65 missing inputs, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and 0/12 jointly source-ready clinical cases. Numerical prediction features remain empty and probabilities null. Independent human reviews remain pending; provider spending is $0, and the downloader/stopped monitor remain untouched.

## Critical next step and order

1. Complete archive-v3's narrowly scoped nullable-close and noncoercing integer corrections, with regression-first evidence, fully rebound synthetic maps, callback identity controls and exact independent re-review. Keep original/directory/source/profile qualification false. Preserve every failure and avoid masking data faults with a broad outer exception catch.
2. Freeze file-port fake interface/call/clock/ownership/output vectors before implementing the minimal read/metadata/output source. Verify unknown/null returns, identity failure after acquisition, short/undefined reads and writes, uncertain distinct closes, namespace ownership before readiness, and final acknowledgment under the original clock. Design approval supplies no actual Win32 port or live authority.
3. Implement the separately specified complete Unicode observation-trace validator and native child/parent source after their exact expected traces freeze. Recompute geometry from full arrays and the fixed source population, keep native observations separate, reconcile stage/case/prefix/cleanup counters and retain all negative/partial unknowns. Do not reuse old189/six-prefix success constants or select favorable boundaries.
4. Integrate the real first-clock bootstrap, closed captured-source loader, fresh original leases, acyclic archive/resource/checker graph, output sink and production engine. Admit the actual role/call/event/capture roster before dispatch; all imports, reads, validation and sealing stay under the original clock. No serialized ready flag or accepted pure profile substitutes for that work.
5. Separately qualify file mechanics, a distinct once-only native coverage experiment, full-vocabulary masks and integrated resources. The 295.922/300-second no-inference warning remains. Versioned integration requires meaningful regressions and installed/archive/relocation checks. Complete R08 and HR1–HR3 before R10 and H5 sizing/freeze before locked evaluation; clinical, genetics/LD, calibration, competitors and T2–T5/H6 remain individually gated.
