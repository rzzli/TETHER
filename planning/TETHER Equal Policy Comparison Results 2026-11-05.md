# TETHER equal-policy comparison results

**BG02 is complete within its declared finite software-conformance scope.** TETHER 0.5.2 / TETHER 0.3.13 and an independent implementation both conform on all 109 authored cases. The original 0.5.1 / 0.3.12 conforms on 108: it incorrectly accepts an archived response bound to the wrong request. The corrected implementation removes that false admission. TETHER has higher measured execution cost than the independent implementation; these results establish neither a correctness advantage over that comparator nor scientific answering ability.

## Design and preserved chronology

The [execution plan](<TETHER Benchmark Execution Plan 2026-11-02.md>) required identical declared policies, valid and invalid inputs, weak diagnostic controls, complete accounting and independent reconstruction. The [27-obligation specification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-20261102/POLICY-SPEC.md) precedes execution. The [corrected protocol](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/CORRECTED-PROTOCOL.md) retains the first experiment and discloses why a new corpus was needed.

The original 108-case experiment completed 1,296 cells. Causal review found that EP075 rejected for an unrelated dossier-formatting fault, masking the replay defect. Other corrections sealed an added raw source, gave budget-stop cases eligible later work, and removed an invalid recovery expectation after journal rejection. The first results and counterexample remain unchanged. The corrected corpus adds a valid replay parent, EP109, and contains 44 eligible accepts, 64 expected rejects and one inspection-only case. All are exposed authored constructions; EP001 and EP025 share an input construction.

Each version executes 109 cases × four arms × three repetitions, or **1,308 terminal cells**. Within each run all arms receive identical frozen inputs. Across versions, the original source/control inputs are matched but native code proofs, paths and timestamps differ; these are semantic twins rather than identical archives. The original and patched freezes were anchored in local commit `2f1b5eb` before execution, with the original also anchored in `a4268a8`. A local commit is chronology evidence, not third-party timestamp attestation.

The independent validator does not call TETHER validation. Its eight runtime source modules and all 654 independent-worker records were checked for product imports/execution. This establishes the reviewed implementation boundary, not blinded authorship or hostile-code isolation. Coverage maps distinguish archived consistency checks from separately retained actual runtime witnesses.

## Outcomes

All repetitions agree. The table reports unique authored cases; repetitions and overlapping policy families are not additional independent samples.

| Arm | Original decision correct | Original fully conformant | Patched decision correct | Patched fully conformant |
|---|---:|---:|---:|---:|
| TETHER | 108/109 | 108/109 | 109/109 | 109/109 |
| Independent full-policy implementation | 109/109 | 109/109 | 109/109 | 109/109 |
| Hash/schema diagnostic | 56/109 | 12/109 | 56/109 | 12/109 |
| Reject-all diagnostic | 64/109 | 64/109 | 64/109 | 64/109 |

Full conformance includes required observable outputs, not just accept/reject disposition. Original TETHER falsely admits EP075 in all three repetitions. Patched TETHER rejects it for request-fingerprint mismatch; the independent implementation rejects under both versions. Both principal arms accept the clean replay neighbor and retain all 44 eligible cases. The hash/schema control falsely admits 52 of 64 invalid cases and errors on one directory-read case; all three error repetitions remain in each run's denominator. Reject-all rejects all 44 eligible cases and mishandles the inspection-only disposition. Those controls demonstrate why rejection rate alone is an inadequate performance measure.

The [causal review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/postresult/CAUSAL-REVIEW-20261105.md) retains intended-fault checks for lineage, replay, journal corruption and nonvacuous budget stopping. A prewritten message matcher flags EP010 because TETHER wraps an invalid timezone-free timestamp in a generic union-decoder error. Manual input/code review explains that flag; raw flags and all scores remain unchanged. No additional unresolved causal confound was identified within this review. First-error matching is not branch instrumentation or exhaustive proof of causal isolation.

## Cost and implementation surface

The patched run provides the following descriptive observations over 327 executions per arm on the shared Windows host:

| Measure | TETHER | Independent |
|---|---:|---:|
| Median import plus operation wall time | 0.4290 s | 0.2608 s |
| Median complete launcher wall time | 0.5824 s | 0.4177 s |
| Median process CPU time | 0.40625 s | 0.25000 s |
| Maximum OS process lifetime peak memory | 306,663,424 B | 297,099,264 B |
| Retained scratch bytes | 447,939 B | 429,528 B |
| Logical input bytes across 327 cells | 13,434,342 B | 13,434,342 B |

The median within-case ratio of TETHER to independent import-plus-operation time is **1.65**. This is an adverse cost result. Fresh-process imports, tracing instrumentation and shared-host variability limit its interpretation. It does not establish warm-service throughput, physical I/O, large-dataset scalability or a causal speed change across releases. Retained scratch bytes are not cumulative writes. The earlier 108-case experiment used a different wrapper surface, so its timings must not be presented as directly comparable improvements or regressions.

The independent implementation includes eight Python files and 2,642 physical lines; six reused files contribute 2,470 lines and two new routing files contribute 172. Reporting only the routing wrapper would understate its size. The whole installed product has 85 Python files across core and facade, including unrelated ingestion, study and archive capabilities. Its size is therefore not a minimal policy-equivalent implementation comparison or a measured maintenance burden. Adapter, comparison infrastructure, constructions, controls and qualification surfaces are reported separately in the reconstruction.

## Validation and retained evidence

Both independent reconstructions agree with every primary cell decision, conformance result, grouping and total. Both terminal executions retain all ten unchanged-input/source/runtime checks. The [requirement matrix](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/completion/REQUIREMENT-EVIDENCE-MATRIX.md) and [closure record](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/completion/CLOSURE-20261105.json) trace stage requirements to actual evidence.

| Record | SHA-256 |
|---|---|
| Original freeze | `f7b4b09f4b144d84761e565452a19082dba16c778e81e422b314880aec531bc7` |
| Patched freeze | `3ec7625fa601a517d8e2dd302228f9f465f35e877f79cd1a587a3a63b394a4fc` |
| Original independent reconstruction | `aa6f39df533d65d7a8377e0b5ded5777fc04d7fa64f5f7477d3b4c7fdb69b50f` |
| Patched independent reconstruction | `db43e00ad671c74029a3954a56766a47f0e79085629764815fe895bac2e170c3` |
| Candidate release aggregate | `d966fa3f74fa5ace029a041642a279bcacef346aa70df65f7bc048733835b01e` |

The [original summary](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/reconstruction/OLD-RESULT-SUMMARY-20261105.json) and [patched summary](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-equal-policy-v2-20261105/reconstruction/PATCHED-RESULT-SUMMARY-20261105.json) retain metrics, resource/inventory details and raw reconstruction identities. The replay correction separately passes a 2,100-test full Windows gate, 25 focused replay tests, 52 archive tests, 138 facade tests, installed positive/negative controls and preservation checks. These scopes overlap and must not be summed. [Release completion](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-replay-correction-20261105/CANDIDATE-RELEASE-COMPLETION.md) keeps distinct build-wheel identities and earlier failed attempts.

## What follows

The supported conclusion is finite conformance plus a useful independently exposed correction, with greater measured cost. Matching 109 controls does not prove universal policy equivalence, natural failure prevalence, scientific truth, calibrated clinical probabilities or hidden generalization. Actual operational guarantees still depend on the separately qualified runtime boundaries; a self-consistent archive does not prove physical execution or power-loss durability.

**Next is BG03: actual SciFact evidence selection and entailment**, scored with native metrics and matched useful-answer/admission accounting. BG04 then evaluates one original LAB-Bench task family; BG05 implements the obligations in Inspect; BG06 audits the complete execution goal. Those stages remain unfinished. The old downloader, periodic monitor, archived human responses and closed historical model experiments remain outside this work. Provider spending is zero.
