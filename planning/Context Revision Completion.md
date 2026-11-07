---
title: Context revision completion
date: 2026-10-16
status: technically-complete-scientific-validation-open
tags: [TETHER, ingestion, t6, validation]
---

# Context revision completion

Normalization recipe **2.2** is implemented and the ten contemporary T6 dossiers are rebuilt and verified. Contract schema remains v2. The comparison confirms unchanged raw sources, hypothesis keys, observation IDs, original statements, source fields and physical row locators. All numerical prediction features remain empty and probabilities null.

Read [[data/benchmark/gold_evidence/context-revision-20261016T055518Z/comparison|the before/after comparison]] and [[runs/context-revision-20261016T055518Z/README|the ten revised dossiers]]. The [[planning/run-registry.json|run registry]] now selects this release; the original pilot and intermediate attempts remain retained.

## Implemented corrections

| Review finding | Implemented behavior | Evidence |
| --- | --- | --- |
| Literature context omitted | Preserve `textMiningSentences`, sections/offsets, `pmcIds` and `studyOverview` verbatim | New source audit and original-row recheck |
| Variant significance omitted | Preserve frozen `clinicalSignificances`; reject conflicting duplicates differing in this field | Regression tests and PCSK9 original rows |
| Source support could be mistaken for therapy support | Explicit resource-annotation scope and unassessed therapeutic relevance in sealed method/coverage and dossier presentation | All ten dossiers |
| Hypotheses lack subtype/mechanism qualifiers | Surface null subtype/population/regimen/endpoint and applicable biomarker/genotype qualifiers; infer no narrower case | Sealed coverage and dossier tables |
| Enrichment could exceed packet size | Compact canonical JSON; retain every record and the 64 MiB limit | Largest packet 45.46 MiB; explicit oversize regression |
| Need versioned reproducibility | Recipe version/projection/code hash/encoding in build report and bundle identity; pinned archived receipts | Build journal and public provenance |

Four regression tests first reproduced the gaps, then passed. Two further tests cover mutation rejection and oversized packets. Full validation passed **120 tests, zero failures/errors/skips**, required framework probes and installed-wheel dependency-free execution. Six targeted tests passed again after strengthening comparison checks. All ten production dossiers passed source-inclusive semantic verification. The new technical source audit checks **20 distinct rows**; the comparison separately rechecks all **20 originally reviewed rows**. The two audits can overlap and are not 40 independent observations.

## Measured production scope

| Measurement | Result |
| --- | ---: |
| Receipt-verified original files | 2,141 |
| Selected original bytes | 3,752,440,123 |
| Physical evidence rows scanned | 14,940,949 |
| Matching/accepted original rows | 14,207 |
| Normalized case records | 16,914 |
| Missing frozen inputs | 65 |
| Corrected build elapsed time | 48.56 seconds |
| Build process peak memory | 1.79 GiB |
| Packet bytes, all ten | 101,674,606 |
| Offline pilot elapsed time | 326.75 seconds |
| Pilot parent peak memory | 2.04 GiB |
| Pilot output bytes | 498,734,520 |
| Provider spending | $0 |

Pilot peak memory measures the parent verification/audit process, not the peak of every child. Build output size excludes originals, backups and some run artifacts; packet bytes measure packets only. Timing reflects this local cached run, not a throughput benchmark.

The original cutoff is `2026-10-12T01:43:05.987191+00:00`; the rebuilt cutoff is `2026-10-16T05:55:18.714527+00:00`. These are two contemporary builds from the same selected originals, not a historical reconstruction. No new acquisition, current-web backfill, live adapter, provider spending or download-monitor restart occurred.

## Retained intermediate attempt

The first enriched build and all ten runs completed, but strict comparison rejected source-ID changes introduced by normalizing Windows separators in the new manifest. Raw bytes were unchanged. The corrected manifest retains the original path spelling and archived receipt references; a fresh build and pilot restore exact baseline source identities. The earlier artifacts and failure record remain under `context-revision-20261016T054655Z`. This exposes a portability limitation of the existing literal-path source-ID recipe; do not rewrite pinned manifest paths without an explicit identity migration.

## Remaining boundaries and next work

Scientific interpretation remains unreviewed for the full dataset. AI review is development feedback, not independent gold. Article type and citation-chain meaning are not inferred from passages. Current ClinVar reconciliation and full current CFTR-label reconciliation remain open; their evaluator supplements were not imported. The 65 missing inputs remain missing.

No narrower HER2, FH, CFTR or neuropathy case was invented. Future specified qualifiers require a versioned hypothesis contract and new fingerprints before execution; coverage text alone cannot bind refined scientific scope. Historical AACT restoration, a complete regional QTL/GWAS/LD pilot, event counts/power and a controlled model comparison remain later gates. See [[Feasibility Gate Decision]].

Sanitized evidence: [[data/manifests/public/2026-10-16-context-revision.json|closeout manifest]] and [[data/manifests/public/2026-10-16-context-normalization.json|normalization registration]]. Detailed comparison rows remain ignored and evaluator-only. Catalog publication updates only `tether_normalized_packets` through the validated maintenance entry point after runs have sealed their effective policy.
