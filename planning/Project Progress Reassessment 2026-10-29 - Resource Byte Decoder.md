# Project reassessment after the resource-byte primitive

29 October 2026 UTC. The pure Job-byte decoder and selected phase checks pass scoped acceptance. This completes another verifier component, while actual resource qualification, native execution and the whole project remain unfinished. The installed C++ tools already worked without restarting.

Root [acceptance](review-assets/recovery-step9-resource-bytes-20261029/CAPTURED-JOB-BYTES-SCOPED-ACCEPTANCE-v1.json), SHA `3e80ae97f6dac5b51c0d7fa7463f02735e288db5e7fa7a7e001a0f76a6893bf5`, binds source `fd655c8b...`, eight author methods and seven independent methods ([peer](review-assets/recovery-step9-resource-bytes-20261029/CAPTURED-JOB-BYTES-INDEPENDENT-PEER-v1.json), `39661d54...`). Sixteen literal captures and eighteen phase checks were frozen before implementation. Author tests include 29 mutations; independent tests add 49 vectors using separately authored integer-to-byte values, signed/unsigned fields, offsets, lengths, source-view discrepancies and nested mutation controls. No actual old snapshot is replayed.

The decoder handles 48-byte accounting and 136-byte allocated PID buffers. Only the returned view is defined: an empty PID result may return eight bytes and one PID sixteen. It requires enough returned bytes for every listed PID, rejects incomplete counts, and ignores unused slots as PIDs while retaining their raw evidence. Distinct signed64 times, unsigned32 counters and unsigned64 PID/tail values test field order and signedness. Failed/undefined queries, malformed windows and source-summary disagreement never become legal zero states. The phase function requires the immutable decoder-result type and distinguishes the selected empty, assigned, running-or-finished and finished tuples without treating sequential observations as atomic.

Every result retains `resource_qualified=False`. These tests do not prove PID ownership, OS enforcement, source provenance, memory limits/peaks, capture EOF, owned wait/exit/reaping, cleanup, the original owner clock or full archive consistency. An overall failed experiment can have a legal finished tuple. No native target, SDK, actual Job query, old CPU/GGUF/pack or original-source qualification occurred.

Earlier [bootstrap acceptance](review-assets/recovery-step9-verifier-adapters-20261029/VERIFIER-BOOTSTRAP-INTERFACES-SCOPED-ACCEPTANCE-v2.json), `9f221af4...`, retains 22 author methods and independent correction probes. [Journal acceptance](review-assets/recovery-step9-verifier-adapters-20261029/CAPTURED-JOURNAL-SCOPED-ACCEPTANCE-v2.json), `23f56d8c...`, retains ten author/seven peer methods, thirty fixtures and thirteen terminal regressions. Both preserve all seven earlier reproduced defects and their failed versions. The journal supports its exact old known-launched v7 policy; it supplies no future Unicode source policy or actual old-run requalification.

The native wire remains preparation. Independent [v2 design review](review-assets/recovery-step9-unicode-wire-20261029/UNICODE-WIRE-INDEPENDENT-DESIGN-REVIEW-v2.json), `7e491fb2...`, clears only literal framing specifications/fixtures. Native field enums, synthetic fragments, sizing envelopes and partial-history fixtures still need their own independent check. No complete pack, pack builder, runtime decoder, bridge, parent or protocol execution follows from design approval.

Archive design review is still active. The earlier proposal needed a separate post-terminal exception-marker rule; independent source inspection then found that the actual parent writes `execution/journal.jsonl` and root `parent-reservation.json`, rather than the proposed root journal locator. Correct the closed roster and reservation references before fixtures or code. Captured byte-graph closure must not be described as an actual directory scan, fresh original-file authority or successful publication return.

The consumed 189-case native profile remains failed with two unavailable natural partial-UTF8 slots. The independent whole-verification remains `INCOMPLETE_TIMEOUT`. No repeat or old payload pass occurred. Source-only acceptance does not repair either gate or qualify full-vocabulary masking, model usefulness or scientific results.

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
| R09 | Application 0.3.11 and scoped pure oracle/controller, fixtures, analyzer, bootstrap interfaces, captured-byte/v7 journal and Job-byte/phase primitive accepted. Actual archive/resource/source/profile/platform/entry/integration, native coverage, masks, integrated resources and usefulness remain unfinished. |
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

Accepted AsOf 0.3.11/default v2 remains unchanged: 1,774 retained passing full tests, 327 source/resource pins and ten matching preserved-version qualifications. No fresh full application test run is claimed for these private components. Optional Arrow remains 755 unchanged files plus five separately source-equivalent caches. Data/science remains 65 missing inputs, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and 0/12 jointly source-ready clinical cases. Numerical prediction features remain empty and probabilities null. Independent human reviews remain pending; provider spending is $0, and the downloader/stopped monitor remain untouched.

## Critical next step and order

1. Finish archive source-format review and a separately versioned corrected locator/marker/DAG contract. Freeze literal positive, consistent-negative and adversarial graph fixtures before implementing the captured-byte checker. Check every declared edge, conditional universe and authoritative marker; preserve post-seal negative/incomplete outcomes. No directory or fresh-source authority comes from serialized maps alone.
2. Independently check the exact Unicode framing closure and its synthetic fragments/rows. Close finite enums, harness nulls, source-stage/API deltas, observation-versus-geometry separation, fixed overhead and negative/partial histories within the frozen caps. Only then decide the next pure pack/parser/bridge source work; no actual payload or compiler access follows automatically.
3. Bind byte/phase decoding into the real resource checks: journal stages, owned creation/resume/wait, limit/peak observations, physical EOF/capture hashes/byte counts, exit/reaping, cleanup and failure/seal precedence. Keep undefined/non-atomic observations explicit and every standalone primitive's qualification flags false.
4. Finish the actual first-clock entry, closed captured-source loader, file/metadata/output ownership, exact role/call/event/capture graph and production-engine continuation. Preserve the original clock through imports, validation and sealing. Injected interfaces and byte fixtures do not implement these live boundaries. Review the finite actual roster before any dispatch or new original pass.
5. Separately qualify live file mechanics, the distinct once-only native coverage profile, full-vocabulary masking and integrated resources. Retain the 295.922/300-second no-inference warning. Versioned release integration needs regressions and installed/archive/relocation checks. Complete R08 and HR1–HR3 before R10, then H5 sizing/freeze before locked evaluation; clinical, genetics/LD, scoring, competitors and T2–T5/H6 keep their individual prerequisites.
