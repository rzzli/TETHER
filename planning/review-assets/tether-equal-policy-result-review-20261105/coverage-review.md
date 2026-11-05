# BG02 post-run case-quality review

The recorded decisions match all 108 frozen decision labels for both principal implementations, but that alone does not establish that every intended obligation was exercised. This review checked all 108 recipes and **648 retained TETHER/independent result files**, comparing original inputs with a separate in-memory application of the declared recipes and comparing rejection reasons and accepted observables. It ran no validator, producer, provider or corrected case and changed no frozen file.

The complete per-case review and retained result hashes are in [coverage-review.json](coverage-review.json), SHA-256 `699f2275b783e22bb7fa8ef4b62e088647535203b39fd5dc5cde048b61da5364`. [coverage_review.py](coverage_review.py) is the read-only checker. Detailed EP075, EP077 and weak-control diagnoses are assigned to a separate reviewer and must accompany this review before making a final comparison claim.

## Findings requiring a corrected corpus version

| Control | Finding | What the original result supports | Required next-version correction |
|---|---|---|---|
| EP023 | `unrelated-source` has all-zero source and receipt hashes, although its underlying source file exists. The source clone is created before sealing, and the sealer updates only the two original IDs. | Both implementations report the intended observation-lineage escape first. This is reached-check evidence, but the fixture has an additional accidental defect. | Seal the additional source and its receipt correctly, preserve the observation's escape from its packet lineage, and keep the expected rejection. |
| EP072, EP097 | Only genetics has eligible evidence. Every later planned category reports `no_observed_evidence`. | The archives retain measured overquote usage, null predictions, no accepted claims and `budget_exhausted`. Zero later dispatches alone is a vacuous prevention test because no later work is available. | Supply a second eligible category after genetics; retain the expectation of no later dispatch. Separately preserve runtime witnesses rather than attributing scheduler execution to the file validators. |
| EP001, EP025 | The two cases use identical input bytes and recipes, under different policy annotations. | The same valid input demonstrates ordinary admission and permission for new computation over old inputs. | Describe this as two obligation views of one construction; do not treat the pair as independent empirical samples. A replacement is optional and does not justify changing an oracle. |

The independent input reconstruction found exactly one unexpected document difference: EP023's snapshot. The other observed source-checksum mismatches are the deliberately corrupted originals in EP017 and EP066. The checker does not count intentional missing/directory/traversal sources as accidental construction defects.

## Rejection and acceptance review

Excluding EP075 and EP077, the **62 rejected controls** have reported reasons aligned with their intended faults in both implementations. Of these, 61 have no additional construction defect identified here; EP023 has the defect above. In particular, the semantic mutations in EP060–EP065 and EP068 reach source-proof, journal/ledger, accounting, feature, prediction, trace or admission-fingerprint checks rather than merely failing a stale output hash. The schema2 policy cases reach their declared grant, frame, transport, projection and presentation checks. Local request/response mutations reach the corresponding binding checks.

The 43 accepted controls return their frozen expected observables. This includes source exclusion rather than whole-run rejection, context retained with numerical features inapplicable, dependence-group aggregation/conflict, explicit scorer abstention, zero-call budget accounting and honest failed archives. EP059 is a valid source-inclusive archive acceptance control with an empty extra-observable oracle; it is not an independent scientific assessment of the scorer. EP076 returns the expected unresolved attempt and prohibition on redispatch. The other two cases remain subject to the separately assigned review.

Reported obligation IDs are not a normalized causal taxonomy: examples include EP011 (`WIRE` in the authored grouping versus `CASE` in the independent error), EP085 (`POLICY-02` versus `POLICY-01`) and EP108 (`PROCESS-01` versus `EXEC-01`). Their textual errors identify the intended invalid version, missing ancestor grant or invalid process bound. Per-family tables should be described as grouping by **authored obligation labels**, not as instrumentation proving that every listed branch executed.

Results are deterministic across repeats apart from one reported scratch-directory path for TETHER's accepted schema2 preparations EP078, EP083 and EP084. Decisions, reasons and scored observables do not vary. Complete returned JSON is identical across repetitions for the other 105 cases. Repeat measurements are not additional independent fault constructions.

## Causal and scope limits

This audit uses the materialized fault, the exact first returned reason, retained observables and source inspection. It is not instruction-level instrumentation or a counterfactual experiment proving that removal of exactly one check makes a mutant pass. Some deliberate semantic changes necessarily also make downstream predictions or presentation inconsistent; reaching the intended earlier check is evidence for that check but not for independent detection by every later check.

Preparation-only cases do not independently execute a scheduler. Archive verification uses executions already produced by TETHER with fictional backend responses. The independently implemented comparator checks those archives; it is not an independently executed scheduler or live model. Native local cases use an in-memory transport, not a language model. Runtime ordering, stopping, immutability and recovery behavior must retain their separate runtime qualification evidence.

No result from this finite corpus establishes biological validity, natural fault prevalence, clinical benefit, or general agent capability. Preserve the original 108-case results unchanged. Corrections should create a newly versioned corpus, retain the original oracle and outcomes as history, and mark post-result changes as exposed/post-hoc rather than held out.
