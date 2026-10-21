# Clinical-label readiness — October 21, 2026

The previously unexecuted reported-results input step is complete and independently
verified. **Clinical label qualification remains unresolved.** This is an exposed
development diagnostic of the original twelve trials, not a locked clinical test.
All36 original endpoint rows remain unresolved/null; no scientific gate was lifted.

## What changed

The old audit had inspected planned outcomes, design and follow-up metadata, but
had extracted zero reported-result rows. A separately versioned protocol now pins
the same twelve origin-selected trials and the January/April2026 AACT snapshots.
It queries six explicit tables: outcomes, result groups, analyses, analysis/group
links, counts and measurements. No trial was selected by result presence, status,
significance, date or favorable evidence. Planned and reported outcomes stay separate.

Both snapshots contain995 result-table rows:38 outcomes,180 result groups,
4 analyses,4 analysis/group links,161 counts and608 measurements. These are source
row occurrences, not patients or independent clinical events. Only NCT05064358 and
NCT06091956 have reported outcomes. January has7 eligible/5 held source versions;
the belantamab version is held, while the LPP version qualifies under the existing
reconstructed-date rule. April has12 eligible versions and both result-bearing
trials available for source review. Ten trials have no reported-result rows here;
that is neither a clinical failure nor proof that no external results exist.

Two identical read-only queries per snapshot, deterministic SQL regeneration,
schema/foreign-key/group checks, exact membership, source/code pins and complete
code archives passed independent terminal verification. Both owned servers stopped
and ports closed. Extraction took43.5 seconds. Original raw archives, old labels,
the downloader and stopped periodic monitor remain unchanged.

## Scientific findings

- **Belantamab:** the primary reported outcome concerns corneal safety; ORR is
  secondary. Result-arm IDs and ordinal names cannot establish equivalence to the
  selected origin DL3 regimen. Results therefore do not automatically supply an
  efficacy success/failure label for that selected program.
- **Deucravacitinib/LPP:** reported patient-response observations now have direct
  result-table support. Patient response definitions do not establish a prospective
  study-level success decision. Recorded primary/study completion dates are before
  origin; the June2025 posting is a disclosure date. The formal analysis/decision
  date remains unqualified, rather than being inferred from either completion or
  posting. No2025 clinical-event label or negative is assigned.
- **Risk-set mismatch:** the inherited blanket global higher-phase prior-risk gate
  is broader than selected-trial efficacy or dosing estimands. A first-ever
  advancement endpoint needs different risk evidence from a selected trial's
  efficacy decision. This is an explicit design issue; no old rule was waived
  retrospectively on the exposed cases.
- **Bounded public-source recovery:** additional primary-source searches did not
  establish a jointly qualified event/rule/scope. Access depth, publication/version
  dates and unavailable full texts remain explicit. Agent source review does not
  establish independently validated clinical truth.

The detailed review retains selected arm/outcome IDs, exact JSON pointers,
observed values, missingness and source-version eligibility under ignored
`data/benchmark/labels/clinical-label-feasibility-20261021/`.

## Correctness and verification

A regression reproduced acceptance of a nonempty negative-ascertainment dictionary
that explicitly said incomplete/unqualified. Structured negatives now require
literal qualified/complete declarations, bounded follow-up and retained evidence.
Legacy narrative strings remain readable with an explicit unverified-declaration
marker; passing a declaration contract never proves scientific completeness.

Independent adversarial tests additionally exposed noninteger foreign keys,
conflicting group codes and contradictory result-posting dates. These now fail or
stay quarantined. Missing fields remain missing; nominal p values are descriptive.
Rows/file caps fail explicitly, with no truncation. The file cap is checked after
query completion, not enforced as a streaming disk quota.

All577 full-suite tests pass with no skips; core validation runs577 tests with
58 expected ingestion skips. Required probes, packaging/demo and all four hosted
Windows/Linux jobs passed at4a57dd4. The initial full-validation attempt stopped
before tests because PowerShell7 was absent from this session. Its failure log is
retained; the successful run used a publisher-hash-verified portable runtime in
the project cache, using the [publisher's release and SHA256](https://github.com/PowerShell/PowerShell/releases/tag/v7.4.6),
without global installation or global PATH changes. No new
biological dataset was downloaded. Provider spending and model calls were both0.

## Next work within remaining Step1

1. Freeze endpoint-specific origin-risk and event definitions. Preserve original
   H1 clinical efficacy; keep registry advancement and experimental dosing separate.
2. Distinguish clinical observation, analysis/decision and first public disclosure.
   Any revised event estimand must be explicit and prospective for a new sample;
   it must not relabel the old36 or silently shift the event window.
3. Define an origin-only labelability sample using planned efficacy objectives,
   prospectively available decision rules, program scope and expected maturity.
   Choose deterministic membership before follow-up; never select for known results.
4. Extract the eligible old protocol/SAP and later results for that frozen sample,
   adjudicate scope/time/decision and negative ascertainment, and retain unknown,
   censored and competing states. Origin evidence gaps remain explicit.
5. Measure qualified classes and dependencies before any larger-cohort power or
   training decision. This twelve-case count cannot establish registry-wide
   prevalence, effective sample size or global infeasibility.

G03 historical predictors, G04 outcomes, G05 power, G06 genetics, G07 scoring and
clinical lock remain false. No clinical metric, probability, training, MR or
colocalization was introduced. Remaining Step2 historical predictors has not been
used to bypass the unresolved cohort/endpoint design in Step1.

## Retained evidence

Sanitized proof index: `planning/review-assets/clinical-label-readiness-20261021/`.
`readiness-report.json` pins the original labels, new extraction, independent
terminal validation, scientific review, bounded source recovery, contract findings
and full/core/hosted checks. The separate protocol is
`planning/protocols/clinical-label-readiness-v0.1.json`. Original proposals, freezes,
failed regressions and dated assessment reports remain preserved.
