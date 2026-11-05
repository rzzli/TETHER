# Corrected BG02 causal result review

The corrected comparison exposes the original replay defect and supports its narrow repair. Original TETHER 0.5.1 / AsOf 0.3.12 accepts the deliberately invalid recorded request in EP075 in all three repetitions. TETHER 0.5.2 / AsOf 0.3.13 rejects it specifically for request-fingerprint mismatch. The independent validator rejects it under both version configurations. The clean replay neighbor EP109 is accepted by both implementations under both versions. No additional unrelated-fault rejection was identified in this review.

Both runs retain **109 cases × four arms × three repetitions = 1,308 terminal cells**. The unchanged, previously qualified helper checked all result and raw-stream bindings and frozen bundle files/directories. The existing independent reconstructions are `reconstructed`, with 109 cases and 1,308 cells each. This supplemental review does not replace their numerical reconstruction. All 654 principal-arm rows per version were reviewed; first decisions and reasons are stable across repetitions. Comparing versions, the only changed principal decision or first-reason text is TETHER EP075.

| Implementation | Original decision / full conformance | Patched decision / full conformance |
|---|---:|---:|
| TETHER | 108/109; 108/109 | 109/109; 109/109 |
| Independent full-policy validator | 109/109; 109/109 | 109/109; 109/109 |
| Hash/schema diagnostic | 56/109; 12/109 | 56/109; 12/109 |
| Reject-all diagnostic | 64/109; 64/109 | 64/109; 64/109 |

These case counts repeat identically across three executions. They are finite exposed controls, not independent draws from deployment failures. The hash/schema control falsely admits 52 of the 64 rejection cases and errors on EP057 when it attempts to read a directory as a file; all three errors per run remain errors. Reject-all falsely rejects all 44 valid-acceptance cases and disagrees with the inspect-only case. Neither diagnostic is a substitute for the full-policy comparator.

## Causal controls

| Control | Actual retained evidence and interpretation |
|---|---|
| EP023 | The added source and its download receipt have matching byte hashes in both runs. TETHER reports observation lineage escaping the artifact; independent reports observation lineage escaping the packet. The old checksum confound is absent. The separately retained single-repair qualification checks its valid neighbor. |
| EP072 | Both genetics and perturbation are ready; both observation IDs are admitted. One genetics dispatch records measured input/output usage 2/2, no estimated usage, no selected observations, and an abstained null prediction. Perturbation coverage is `not_run_budget_exhausted`. All six principal rows per version agree. |
| EP097 | The corresponding local-fixture control also has both categories ready. One genetics dispatch records measured input/output usage 1/65, no estimated usage, and an abstained null prediction; perturbation is not run after budget exhaustion. All six principal rows per version agree. These controls make the retained no-later-work witness nonvacuous; they remain fictional archived executions, supplemented by the retained runtime tests. |
| EP075 | The replay entry contains 64 `f` characters while the actual dispatch request starts `4be711d8`. Earlier preflight checks retained the refreshed deterministic dossier and all seals. Original TETHER accepts; patched TETHER reports “Replay response does not match the request fingerprint”; independent reports “Replay/request fingerprint mismatch.” This is a real original-version failure, retained in the results. |
| EP109 | The replay entry equals the dispatch fingerprint. Both principal arms accept all repetitions under both versions, selecting `obs-1`, retaining the synthetic genetic feature 0.75, and reporting one call and scored synthetic output. Its probability is a fictional arithmetic check, not a clinical estimate. |
| EP077 | Both versions and principal arms reject the corrupted final chain hash: TETHER reports `Trace hash-chain failure`, independent `Journal chain mismatch`. The corrected oracle requires no recovery output on rejection. EP076 remains its valid inspection neighbor. |

## Retained automated flag and manual resolution

The helper flags TETHER EP010 in every repetition of both versions because its unchanged phrase map does not match `case.origin_at: invalid value for datetime.datetime | None`. The frozen recipe has one change: `origin_at` becomes the timezone-free `2024-06-30T23:59:59`. The decoder rejects naive datetimes and then wraps the failed datetime/null union branches in that generic message (`src/asof/serde.py`, lines 111–120 and 136–145). Independent reports `Timestamp requires timezone`. This supports the intended invalid-timestamp check. **The raw flags remain in both reports; no helper, oracle, score or run was changed to remove them.**

The independent feature errors for EP040–EP042 similarly name a shared qualification gate rather than the individual field. Their declared single mutations, valid parent and TETHER's specific reasons supply context; the error string alone does not establish field-level branch coverage. No unmatched causal warning remains unexplained within the reviewed scope.

## Retained records and limits

- [Original supplemental audit](ORIGINAL-CAUSAL-AUDIT-20261105.json): `fc938b79edfc67a55987b032e5d3a1faef29ef0b7cbe4cf66ad717c39a1e99dd`.
- [Patched supplemental audit](PATCHED-CAUSAL-AUDIT-20261105.json): `57ad2a4022a11c0ee432bda784daad7cd17f9c1b14e97612b521fe07d1c9efe2`.
- [Manual evidence record](MANUAL-CAUSAL-REVIEW-20261105.json): `214b774c60c77d5eb60834c902cec034309814a650f071663c0e88c0fbdc61fc`; pins both preflights, reconstructions, helper qualification and selected original records.
- [Predeclared review checklist](CHECKLIST.md) and [eight invented-outcome controls](QUALIFICATION-INVENTED-20261105.json) remain unchanged.

All 109 controls are exposed authored constructions. EP001/EP025 share their input construction, repetitions are not independent samples, and policy-family counts overlap. Matching first-error text is not branch instrumentation or proof that disabling one check admits every mutant. Within each version the arms share bytes; across versions the artifacts are semantic twins with different runtime proofs and paths. This review adds no scientific-validation, natural-prevalence, hidden-generalization or comparative-speed claim. Original failures and the preserved first 108-case experiment remain part of the evidence.
