# Project reassessment: first ABI export-resolution failure

28 October 2026 UTC / 28 October Los Angeles. AI engineering progress assessment, not independent human scientific review. **The first fixed ABI attempt failed during export resolution, before version/default queries. Static evidence identifies a bridge DLL-owner mapping error. The qualified detached own-worker launch result remains valid in its scope; ABI, recognition, resources and scientific evaluation remain open. No failed attempt will be rerun or relabeled.**

## Actual evidence and static diagnosis

This checkpoint reads the [recovery plan](<Project Recovery and Evaluation Plan 2026-10-26.md>), [checklist](../TODO.md), prior [detached-launch assessment](<Project Progress Reassessment 2026-10-28 - Detached Launch.md>), retained actual failure and static export crosscheck. It launches no process/API/model or verifier and reads no protected clinical labels, biological answers or human submissions. All previous snapshots remain unchanged.

The [actual ABI failure verification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/DETACHED-ABI-V1-RESULT-VERIFICATION.md), JSON SHA `425a2e609f4e2ac6fb1170fbca1ecc66a637f5faa59635fc8175dabff084202a`, verifies all 147 current input pins, exactly 13 files, a 13-event journal chain and 298 lease records over 149 paths. All close outcomes, early receipt, primary failure, post-lease cleanup and terminal seal agree. Child PID 13360 exited 2/reaped after 0.188 seconds. Parent elapsed time is 0.656 seconds before the early receipt and 0.734 seconds before the terminal seal.

The child retains a valid `attempt.json`, `failure.json` and a two-row `result.partial.jsonl`: OpenMP preload reservation followed by `required_export_missing`. There is no finalized result, module inventory, version or default-parameter observation. Three raw Job samples contain empty, assigned and first-running states, with only the owned PID in the latter two. **No final Job sample exists in this nonzero-return path.** Stdout retains the 57-byte failure message with EOF false; further unretained output remains unknown. These are truthful gaps in a failed attempt, not evidence of successful final accounting or capture completeness.

The pinned source resolves all `Api` exports before emitting the module inventory and before calling either `llama_version()` or `llama_model_default_params()`. Zero invocations of those two explicit query APIs is therefore a source/control-flow inference; counters were not instrumented. The parent's one-call-each policy is intended scope, not actual usage measurement. Explicit dependency-load calls precede resolution, but their source ordering cannot substitute for an observed module census. DLL/CRT/OpenMP initialization effects remain possible.

The separate [static PE crosscheck](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-EXPORT-STATIC-CROSSCHECK-v1.json), SHA `64c0f7644360b0ddf2983db279ff92dd5e0f89afa34ca3aa4bb406501cb27ae8`, compares required source names with the exact pinned DLL export directories:

| Required group | Static finding |
|---|---|
| All 15 LLAMA names | Present in `llama.dll`, including `llama_version` and the default-parameter API. |
| Five GGML names | Correctly exported by `ggml.dll`: load, registration count/get and device count/get. |
| Other five GGML names | Exported by `ggml-base.dll`, but the old bridge asks `ggml.dll`: registration name/device count/device get and device name/type. |

The first source-ordered missing lookup is consequently `ggml_backend_reg_name`. That exact name is **source-plus-PE inference**, not a name reported by the child or a dynamic probe. The evidence supports a concrete owner-map correction; it does not prove callable ABI types/layouts, successful initialization or an API version value. Dropping requirements, searching arbitrary DLLs or trying another binary would not resolve the declared contract honestly.

## What remains accepted

The [detached own-worker qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.md) still passes its four predeclared cases on this host: 140 pins, 23 files, 61 journal events, 20 raw SDK snapshots and 284 lease records. It uses unchanged own EXE `0100ee6004531a41a28156385ad66fd5c0bded43c4840091a846573efe6d8e49`, with the exact constant-only detached SDK fork and creation flags `0x0008040C`. Its resources total 1 fits the predeclared resources-only range `[1, 2]`; quota 1816 has no unique internal-cause interpretation. The ABI target EXE is a different artifact, `9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696`, and its first experiment now remains failed. Neither SDK execution flag is changed in place.

The earlier hidden-console failures, current-run `conhost.exe` path/current-Job observations and [late IOCP queue warning](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/NATIVE-JOB-IOCP-V1-POST-REVIEW-WARNING.md) remain preserved. No old incident receives retrospective identity/causal attribution, and the consumed IOCP driver is not reused.

Accepted application software remains [TETHER 0.3.11](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json): 1,774 retained passing tests, 327 source/resource pins and ten matching preserved-version qualifications. Default dispatch is v2; new-v3 execution remains false. No application-runtime modification or new full-suite result is claimed by this source-only diagnostic work.

## Complete recovery status

| Item | Current status and remaining gate |
|---|---|
| R01 | Accepted scope, governance and exposure boundaries; no expanded scientific claim. |
| R02 | Accepted tested checkpoint and restoration inventory. |
| R03 | Accepted archive compatibility/relocation in scope; full data/model restoration and cross-platform guarantees remain separate. |
| R04 | Accepted reproduced core boundary/correctness fixes. |
| R05 | Accepted bounded capacity/interface preparation; stronger-model sufficiency remains unresolved. |
| R06 | Accepted reusable infrastructure slice. |
| R07 | Technical experiment closed negative: six responses, zero accepted contracts; independent human scientific assessment remains open. |
| R08 | Source/exposure mechanics partly accepted; no scientifically qualified fresh case or complete reviewer coverage. |
| R09 | Engineering accepted through 0.3.11; exact detached own-worker launch experiment passes. First ABI attempt failed on export ownership; version/default, document/EOG, resources, integration and scientific/native qualification remain open. |
| R10 | Timed independent human development pilot pending R08/R09 and human prerequisites. |
| R11 | H5 estimand, sample size, protocol amendment and preregistration/analysis freeze pending prerequisite evidence. |
| R12 | Locked H5 execution/report pending qualified mechanics, protocol and final panel. |
| R13 | Alternative clinical outcome source conditional and unqualified. |
| R14 | Predictors, causal genetics and scoring/calibration conditional and unqualified. |
| R15 | Original clinical comparisons and ablations conditional and pending. |
| R16 | Individually gated T2–T5/H6 extensions and reproducible release pending. |
| HR1 | Owner recruitment, domain matching, conflicts and exposure records pending. |
| HR2 | Two independent orientation submissions and measured workload remain pending. |
| HR3 | Fresh source-only references, qualified reviewer coverage and masked development ratings pending. |
| HR4 | Sized final panel and independent adjudication pending. |

Human status carries forward the owner's pending-review confirmation. Retained data limits remain 65 missing inputs, nine available observations in the exposed IL6R preparation, [36 unqualified endpoint labels](<Endpoint-specific Follow-up Feasibility 2026-10-21.md>), [17/32 observable primary registry states](<B0 Registry Content Feasibility 2026-10-22.md>) and [0/12 jointly source-ready clinical cases](<Source Readiness Closeout and T6 Quality Next Stage 2026-10-24.md>). Those aggregates were not recomputed from protected payloads here. Chronology, outcome adjudication, complete regional genetics/compatible LD, overlap, context and intervention direction remain scientific prerequisites. Numerical prediction features and clinical probabilities remain withheld. Provider spending remains $0.

## Critical next gates

1. **Turn the static owner diagnosis into a regression before any new build.** Compare all source-required exports and their exact DLL owners against the pinned PE metadata. Retain the old map's five failures and first source-ordered missing lookup, then require the prospective explicit five-plus-five GGML owner map and all 15 LLAMA names to pass. Reject fallback owner search and unsupported forwarders/changed identities. Emit bounded module/name lookup diagnostics in the new source. This uses static file parsing, not `LoadLibrary` or trial API calls; the failed bridge remains unchanged.

2. **Prepare a separately versioned corrected bridge and negative-path parent.** Review the minimal source delta and exact typed declarations, compile/link under a new bounded protocol/output and independently verify the new artifact. Preserve disabled recognition, the same detached SDK and fixed runtime closure. The prospective parent must retain a final Job observation and bounded drain outcome on nonzero return where obtainable, and explicit unknowns when not obtainable, while preserving the original child failure and cleanup errors. Add pure regression coverage for this branch rather than hiding incomplete EOF/final accounting. No original source, binary, receipt or failed result is repaired in place.

3. **Only after those gates, authorize one fresh corrected ABI experiment.** Bind the new executable, source/header/build proof, four required package DLLs, finite system candidates, qualified SDK, strict parser and fresh original-path leases. Retain exact total-1 accounting, commit/time/capture bounds, authoritative failure supplements and terminal seals. Observe version/defaults and typed layouts instead of inferring them from export presence. A positive source/static/build result is not runtime authorization; a fresh reviewed protocol and decision precede dispatch. Preserve DLL-initialization and module-inventory timing limits. No CPU registry/backend, model/GGUF, vocabulary, grammar, automatic retry or arbitrary alternative binary belongs in this ABI stage.

4. **Qualify native vocabulary/document/EOG behavior separately.** Use a reviewed actual ABI/version observation to bind the next recognition-enabled build. Review CPU registration and vocabulary-only loader controls; preserve original corpus bytes, the exact NUL harness exclusion and new authored fixtures as distinct evidence. Token-piece roundtrip, all EOG identifiers, negatives and prefixes require their own finite native results. Export availability alone qualifies none of these.

5. **Establish full-mask resources, then prospective 0.3.12 integration.** The retained simulation used 295.922/300 seconds without inference; the [resource-path review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/RESOURCE-PATH-REVIEW.md) derives 16 successful-path hash passes/about 133.933 GiB logical input, not physical I/O or a timing cause. Measure full-vocabulary masking/startup/token costs and correct prospectively while preserving canonical receipts, live original-path leases, fresh independent verification and the 300-second scientific budget. Only after conformance/resource evidence should v3 be connected under regression-first runtime tests, packaging, installed/relocated checks, matching old versions and new scoped acceptance. Default 0.3.11/v2 remains unchanged meanwhile.

6. **Complete fresh-case and independent human/scientific gates.** Finish R08 and HR1–HR3 before R10, then size/freeze H5 before locked R12 with its final panel. R13–R16 retain distinct clinical-data, genetics, scoring, comparator, endpoint and release prerequisites. Agents can prepare and review engineering/source evidence; they cannot provide independent human submissions or establish clinical validity by running a local model.

The next action is a static-regression and separately versioned correction gate, not another attempt of the failed ABI protocol. The project remains incomplete.
