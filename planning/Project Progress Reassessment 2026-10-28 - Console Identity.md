# Project reassessment: console identity observation

28 October 2026 UTC / 28 October Los Angeles. AI engineering progress assessment, not independent human scientific review. **One bounded diagnostic now records an additional current Job member whose reported image path is `conhost.exe`. Launcher qualification remains failed. The next step is a separately reviewed detached-console policy experiment; target ABI, model execution and scientific gates remain held.**

## Checkpoint and actual evidence

This assessment reads the [recovery plan](<Project Recovery and Evaluation Plan 2026-10-26.md>), [checklist](../TODO.md), prior [native-canary assessment](<Project Progress Reassessment 2026-10-28 - Native Canary.md>), actual IOCP verification and retained source warnings. It does not rerun tests, workers, APIs, models or verifiers, and does not read protected clinical labels, biological answers or human submissions. Earlier checkpoints and failed attempts remain unchanged.

Accepted application software remains [TETHER 0.3.11](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json): 1,774 retained passing tests, 327 source/resource pins and ten matching preserved-version qualifications. Default dispatch remains v2; new-v3 execution remains false. This is pure generation-contract engineering acceptance, with native conformance unverified and whole-R09/whole-project completion false. No application-runtime change or new full-suite qualification is claimed here.

The [actual IOCP result verification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/NATIVE-JOB-IOCP-V1-RESULT-VERIFICATION.md), JSON SHA `25c648a168c5d836acb44e080ba8c4219c2d38068d15174ab35a92701d5beec5`, verifies 176 input pins, exactly 12 files, 49 journal events, eight raw SDK snapshots, ten PID metadata queries and 356 lease records over 178 paths. Early receipt, authoritative failure, post-lease close outcomes and terminal seal agree. The evidence reviewer coauthored the status-only sealer and separate pure metadata tests; this is not independent review of the entire diagnostic implementation.

The queue retained nine normal returns: two `NEW_PROCESS` packets, one `ACTIVE_PROCESS_ZERO` packet and six current-empty timeouts. Exact completion keys match. Before explicit owned-Job termination, separate query handles supplied these observations:

| Reported PID | Same-handle evidence |
|---|---|
| 19276 | `GetProcessId` matches; reported image path is the pinned own C++ worker; exact-Job membership true; zero-time wait returns timeout. Creation FILETIME `134376984869609582`. |
| 24584 | `GetProcessId` matches; reported image path is `C:\Windows\System32\conhost.exe`; exact-Job membership true; zero-time wait returns timeout. Creation FILETIME `134376984869709355`. |

The raw UTF-16 output buffers independently decode to those path strings. The secondary image file was not opened or hashed; a pathname is not a verified binary identity. Both exit FILETIME values remain explicitly undefined because the preceding waits were nonsignaled. The current same-handle PID and Job membership observations are strong evidence in this attempt, while historical notification identity, PID reuse before open, parentage and the internal creation/admission path remain unproven.

Raw pre-stop samples show total 2, active 2 and PIDs `[19276, 24584]`. Both `NEW_PROCESS` returns and metadata queries precede explicit termination in parent journal order. This establishes observation order, not kernel event timestamps or sole cause. Immediately after successful termination, the first sample shows active 0 and an empty PID list while both observer handles remain held; the held-after-reap and released-handle samples also show active 0. All four required stop boundaries, successful query-handle closes and completion-port close are retained.

The startup counter finding stopped the worker before the intended overflow capture cap: zero stdout/stderr bytes retained, exit 125/reaped, whole-case time 0.328 seconds. Parent elapsed time before the early receipt is 0.875 seconds; before the terminal seal, 0.937 seconds. The report's `diagnostic_completeness=true` concerns the required observation/cleanup records; its terminal outcome and qualification remain negative. No generic total-2 allowance or host whitelist follows. This run does not retroactively identify the unknown second associations in earlier Python/C++ attempts or explain the older active-2 observation.

## Source interpretation and late defect

The retained [console/Job source analysis](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/CONSOLE-HOST-JOB-SOURCE-ANALYSIS-v1.md) distinguishes hidden-console launch from console detachment. It finds a documented console-host mechanism consistent with the path observation, but no formal API guarantee explaining admission of that host despite the active-process limit of 1. The observed result must not be recast as a proven active-limit exception, a CRT cause, a binary audit or universal Windows behavior. Changing `/MD` to `/MT` is not justified by this evidence.

A [post-execution source warning](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/NATIVE-JOB-IOCP-V1-POST-REVIEW-WARNING.md) records a missed queue-attempt reservation defect. The author warning reached root after the once-only attempt had run. In frozen v1, `api.queue_call` executes before the call/packet row is committed. An exception or interruption after a possible dequeue can leave an unknown, uncounted attempt. The [pure counterexample](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/IOCP-QUEUE-ATTEMPT-GAP-v1.json), SHA `70f52b66aeace902a153eae8e60aa14f9988c31caa62d6839b2a56ef504fd3f6`, demonstrates two fake invocations consuming one final recorded slot.

The actual run retains nine normal returns with no observer API-exception/interruption indication; there is no evidence that this latent path triggered there. That does not establish a general budget/interruption guarantee. The consumed source, review and result stay frozen. Before any future observer reuse, a separate version must durably reserve/count attempts before dispatch, retain unknown outcomes, conservatively charge possible packets and preserve cleanup. No IOCP replay is the next action, and this defect is not repaired by the proposed console-policy change.

## Complete recovery status

These 20 statuses preserve the controlling plan's scientific boundaries. Accepted R01–R06 scopes do not imply that original project hypotheses have passed.

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
| R09 | Engineering accepted through 0.3.11. Console identity adds bounded evidence; actual launcher qualification remains failed. Target ABI, document/EOG, resources, v3 runtime connection and scientific/native qualification remain incomplete. |
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

Human status carries forward the owner's pending-review confirmation; agents cannot complete independent human submissions. Data findings also remain retained aggregates, not a new payload audit: 65 missing inputs in the frozen manifest, nine available observations in the exposed IL6R preparation, [36 unqualified endpoint labels](<Endpoint-specific Follow-up Feasibility 2026-10-21.md>), [17/32 observable primary registry states](<B0 Registry Content Feasibility 2026-10-22.md>) and [0/12 jointly source-ready clinical cases](<Source Readiness Closeout and T6 Quality Next Stage 2026-10-24.md>). Clinical outcome adjudication, information chronology, complete regional genetics/compatible LD, cohort overlap, context and intervention direction still need qualification. Numerical prediction features and clinical probabilities remain withheld. Disk-space observations do not establish capacity for the whole inventory.

## Critical next step and ordered remainder

1. **Prepare an exact detached-console policy and fresh four-case protocol.** The smallest prospective change is a new, still-disabled SDK fork differing only in its fixed creation-flags constant: replace `CREATE_NO_WINDOW` with `DETACHED_PROCESS`, yielding `0x0008040C` while retaining suspended creation, extended startup information and a Unicode environment. Preserve frozen SDK v3, the same own EXE, JOB_LIST assignment at creation, the three-handle stdio list, identity checks, sole resume and all existing limits/leases/seals. Do not add Job-breakaway flags, an arbitrary flag interface, a conhost allowance or a generic counter waiver. Prove the constant-only source/AST delta and that journaled flags match the dispatched value. Source review, pure boundary tests, independent peer review of the policy and an exact execution decision must precede any attempt. A console-policy experiment tests a plausible remedy; it does not promise that the extra member cannot recur.

2. **Qualify that fixed launch policy once with all four harmless cases.** Use a new output directory/protocol and unchanged resources, overflow, timeout and suspended-abort requirements. Keep 60-second parent/eight-second cases, cleanup reserves, 256 MiB process/Job commit, active limit 1, bounded captures and raw-before-check accounting. Preserve the deliberate rejected-child resources expectation separately from generic total 1. Require every declared case and its independent terminal verification to pass before advancing. A failure stops; no automatic retry, observer replay, host filtering or retroactive relabeling of prior results. Capture/EOF/timeout behavior must be measured under the new policy rather than inferred from redirected handles.

3. **Only after harmless launch qualification, prepare the fixed target ABI observation.** The existing public-C bridge remains unexecuted. Bind exact executable/runtime DLLs, actual launch flags, source-inclusive proofs, typed layouts/defaults, version/module observations and owned cleanup. Keep CPU registry, backend, model paths, vocabulary and grammar outside this stage. A successful harmless policy does not qualify ABI or authorize a fallback.

4. **Qualify vocabulary, document and EOG behavior separately.** Bind the observed ABI/version and an explicitly enabled consumer. Preserve original wire documents, the exact NUL harness exclusion and newly authored fixtures as separate evidence. Token-piece byte roundtrip, all EOG identifiers, negatives and prefixes need native results. Pure grammar correctness is not model quality or full-vocabulary masking feasibility.

5. **Establish practical resource fit before integrated inference.** The retained simulation used 295.922/300 seconds without actual inference. The [resource-path review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-recognition-20261028/RESOURCE-PATH-REVIEW.md) derives 16 successful-path model hash passes/about 133.933 GiB logical input; it does not measure physical I/O or assign elapsed cost. Profile prospectively while preserving canonical receipts, live original-path leases and fresh independent verification. A larger scientific budget, serialized trust flag or retry-until-fast result does not establish fit.

6. **Finish runtime integration and the scientific/human workstreams.** Default v2 is unchanged; native conformance alone does not connect v3, validate interpretation or qualify fresh cases. Complete R08 and HR1–HR3 before R10, then size/freeze the H5 protocol before locked R12. R13–R16 retain their own clinical-data, genetics, scoring, comparison, task-endpoint and release gates. No paid access, new bulk download, active worker/monitor change or completed recruitment is implied. Provider spending remains $0.

The project has a better observed identity for this failed attempt and a bounded prospective experiment. It does not yet have a qualified native launcher or scientifically validated agent evaluation.
