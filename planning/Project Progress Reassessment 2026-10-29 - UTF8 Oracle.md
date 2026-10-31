# Project reassessment: strict byte oracle accepted in scope

29 October 2026 UTC / 28 October Los Angeles. **The model-independent byte/chunk oracle now passes its frozen fixture, API and independent review gates. The failed actual-DLL recognition profile and expired whole-verification gate remain unchanged. No new native experiment, model read or application release occurred.**

## Evidence examined and result

This pass reconciles the [recovery plan](<Project Recovery and Evaluation Plan 2026-10-26.md>), [TODO](../TODO.md), [recognition disposition](<Project Progress Reassessment 2026-10-29 - Recognition Disposition.md>), [ordered source recovery plan](<R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md>), new frozen byte fixtures/reference/implementation, verifier design and memory. It distinguishes implementation acceptance, experiment qualification and scientific readiness.

The [frozen specification](review-assets/recovery-step9-utf8-oracle-20261029/UTF8-ORACLE-SPEC-v2.md) defines strict byte validity and exact chunk consumption, pending bytes, earliest error, EOF, absorbing error and typed request rules. The corpus has 107 fixtures, 167 steps, 354 supplied bytes, 14 literal scalar/encoding pairs and 29 declared interior cuts. It includes mixed complete/partial tails, malformed encodings, NUL/BOM preservation and separate ASCII JSON escape controls. The v1 fixture set and independent HOLD remain; v2 adds missing encoding strata before implementation. Five structural checks pass and the freeze precedes reference decoding and the adapter.

The normative byte bounds come from [RFC 3629](https://www.rfc-editor.org/rfc/rfc3629.html). The reference uses the [Python 3.11 codec interface](https://docs.python.org/3.11/library/codecs.html#incrementaldecoder-objects), while consumption/error timing is the project's explicit contract. An initial reference incorrectly assumed CPython always diagnoses invalid prefixes at the earliest forbidden byte. Its failed proof remains. Narrow probes show delayed surrogate-prefix diagnosis. A bounded certificate rejects all 256 possible final continuation bytes for each of the two fixed problematic prefixes: 512 strict decodes, zero accepted. No fixtures were changed to accommodate the reference.

The [split reference](review-assets/recovery-step9-utf8-oracle-20261029/UTF8-ORACLE-SPLIT-REFERENCE-PROOF-v2.json), SHA `1a1c1e683d5e59a0901313fdb8946a0a3da10dc4d4c626bfd7f45895d87555e9`, therefore separates 104 direct CPython paths from three normative earliest-error/certificate paths. It does not claim 107 cases of identical incremental API behavior.

The independently authored [pure implementation](review-assets/recovery-step9-utf8-oracle-20261029/strict_utf8_oracle_v1.py), SHA `4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21`, uses no codecs, file access or native library. Seven implementation test methods pass, covering all fixture steps, strict argument/state precedence, ordinary API immutability and fresh serialization. Eleven additional controls detect deliberately corrupted comparator records; they are not an implementation mutation score. The first checker failed while preparing its report because a string path was passed to a Path-only helper. Its test outcome was not retained and is explicitly unknown; the corrected separately named checker passes with the oracle unchanged.

The [independent peer review](review-assets/recovery-step9-utf8-oracle-20261029/UTF8-ORACLE-IMPLEMENTATION-PEER-REVIEW-v1.json), SHA `37d59537f2c9fc8fabd6d9a143da5d2a8c6b034e6914a630ce1ae2fcd4390383`, checks source/API behavior, proof anchors and all 107 per-case state hashes against the independent split reference. The [scoped acceptance](review-assets/recovery-step9-utf8-oracle-20261029/UTF8-ORACLE-SCOPED-ACCEPTANCE-v1.json), SHA `1e0890b4d016a5cd00966107a72d2a9e9925cab606d51b519e6cdfa115512a4e`, accepts only this finite pure byte/chunk component.

Limits remain material. Cumulative decoded-history copying can become quadratic across many small feeds; production token-filtering performance is unqualified. Frozen snapshots protect ordinary API use, not hostile Python reflection. Source review shows the vendor's token-piece decoder has different preconditions/interface, including NUL-sentinel behavior and no final-EOF flag. No vendor extraction, C++ harness, actual DLL/vocabulary/EOG, full mask, inference or biological claim follows from this oracle.

## Verifier findings and work still in progress

The [retained timing analysis](review-assets/recovery-step9-verifier-recovery-20261029/VERIFIER-RECOVERY-TIMING-EVIDENCE-v1.json) locates 153.094 seconds before file-pass reservation and 5.562 seconds from reservation to fresh pass completion. The interval from that completion to the core audit endpoint is 134.000 seconds, but the core audit's start is unrecorded. These are endpoint intervals, not measured disk/hash/parser costs. The original 300-second gate stays incomplete; later reporting at 820.437 seconds did not finish it.

The [prospective orchestration contract](review-assets/recovery-step9-verifier-recovery-20261029/VERIFIER-RECOVERY-DESIGN-CONTRACT-v2.json), SHA `7bff14386239d908ca33fd1a11214e95d90010b312aed3d23ac07b9fd69e3c6f`, specifies one synchronous main-first 300-second clock, work deadline 295, five-second finalization reserve and all mandatory gates before complete status. Source is written before invocation; runtime validation is not moved outside its clock. Owner-local immutable captured bytes/indexes and live original leases replace repeated reconstruction, never fresh validation or proof requirements. Joint file/event admission is explicit: at most 256 originals and a bounded event allowance below 2,048.

This pipeline remains **draft, not accepted** at this checkpoint. Early peer review identified mutable captured context, lost unknown-read classification, missing late checker results, output-key validation ordering and terminal writes after unacknowledged/foreign reservation. The author is batching fixes with pure fault-injection evidence. No live file adapter, old original rehash, SDK construction or runtime dispatch is authorized by the design. A generic orchestration pass alone cannot qualify real archive/core checkers.

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
| R09 | Engineering through 0.3.11 and scoped pure strict-byte oracle accepted. Original native profile failed on coverage; external whole-check timed out. Verifier recovery is draft; actual coverage, masks, resources, integration and usefulness remain open. |
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

Accepted AsOf 0.3.11/default v2 remains unchanged: 1,774 retained passing full tests, 327 source/resource pins and ten matching preserved-version qualifications. No fresh full-suite run is claimed for private qualification assets. Optional Arrow remains 755 unchanged files plus five independently source-equivalent caches. Data summaries remain 65 missing inputs, nine exposed IL6R observations, 36 unqualified endpoint labels, 17/32 observable primary registry states and 0/12 jointly source-ready clinical cases. This pass rechecks no biological data or protected outcomes. Numerical prediction features remain empty and probabilities null. Human reviews remain pending; provider spending is $0. Downloader and stopped monitoring remain untouched.

## Critical next gates

1. **Finish the model-free verifier orchestration.** Preserve draft findings, fix ownership/unknown/late-return boundaries, and test with synthetic bytes, leases, clocks and sinks. Require reserve-before-inspect, all mandatory stages, exact-once closure, failure preservation, final seal and final original-clock check. Never write to foreign or unknown-owned output. Complete negative evidence is distinct from a passed source profile. Accept only the source/pure orchestration scope after independent exact review.
2. **Specify future adapter bindings separately.** Freeze the real identity/read/close and actual archive/core checker contracts before any source validation or original payload read. The generic scheduler must not accept serialized readiness flags or forged gate records. Any later real adapter needs source review and a concrete prospective protocol; the old payload pass and timeout will not be repeated or repaired.
3. **Preregister a distinct finite Unicode coverage experiment if needed.** Choose the complete corpus/strata and selector independently of inspected token IDs/merges, retain bounded token-piece/end-offset ledgers, and keep unavailable coverage a possible negative result. Pure byte correctness is not actual DLL/vocabulary behavior. Preserve the failed original 189-case profile and its exact two unavailable slots.
4. **Keep masks and integrated resources separate.** Singleton controls do not establish full-vocabulary masking. Retain the 295.922/300-second no-inference simulation and 16-pass/133.933-GiB logical hash estimate. Measure actual stages, including independent verification; do not infer costs from endpoint gaps or claim general streaming fit for this small oracle.
5. **Integrate and evaluate only qualified behavior.** A minimal versioned application change needs matching regression/archive/installed/relocation checks. R08 and HR1–HR3 precede R10; H5 sizing/freezing precedes locked R12. Later clinical/genetics/scorer/comparator/T2–T5/H6 requirements remain individual gates. Whole-project completion is unproven.
