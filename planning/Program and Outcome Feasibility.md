---
title: Program and Outcome Feasibility
date: 2026-10-17
status: completed-development-review-with-gates
tags: [asof, clinical-evaluation, feasibility]
---

# Program and outcome feasibility

The first WP1–WP4 development pass is complete. **Clinical training and a locked T1 benchmark remain no-go.** The next work is targeted resolution of the linked Phase 3 event and program identities, before broad cohort expansion.

This follows [[Updated Project Plan 2026-10-17]] and uses the sealed evidence in [[Clinical Long Session Progress]]. It is an AI-assisted, unblinded review of already exposed development cases, not independent scientific adjudication. No new patient-level data, database restoration, web acquisition, provider spending, model calls or runtime changes were needed.

## Retained outputs

- Review page: `data/benchmark/cohorts/program-outcome-feasibility-20261017T143507Z/Review.html`.
- Decision: `decision.md` in that directory.
- Frozen amended protocol, program register, original trial/arm links, mapping evidence, case dispositions, source reports, candidate events, follow-up assessments, ambiguities and cohort flow.
- Second-pass review, validation, test output, executed evaluator code and hash-chained build journal.
- Current pointer: `data/derived/active-program-feasibility.json`.
- Public anchor: `data/manifests/public/2026-10-17-program-outcome-feasibility.json`.
- Evidence-manifest SHA-256: `84cd52a1ca1c05e83b75aabd8550421356243fe6ca3c0b33efe139e71ad531bc`.

The artifact role is `evaluation_only`; it is not registered as an agent snapshot or promoted into the canonical T6 runs. The source-only evidence admission restrictions remain in force.

## Cohort accounting

| Measure | Count | Meaning |
| --- | ---: | --- |
| Frozen trial representatives | 24 | No omissions or outcome-driven replacements |
| Provisional origin phase/status passes | 5 | P01, P11, P12, P17, P21; further qualifications required |
| Unresolved arm activity / at-risk state | 4 | P02, P03, P07, P14 |
| Unresolved mixed-phase stage | 6 | P08, P09, P10, P15, P19, P24 |
| Excluded Phase 3 | 4 | P04, P06, P16, P18 |
| Excluded anchor role / closed arm | 4 | P05, P13, P20, P22 |
| Excluded not active at origin | 1 | P23, also Phase 3 |
| Candidate program scopes | 32 | 8 provisional-screen, 19 unresolved, 5 excluded scopes |
| Selected origin arm links | 41 | Dose groups may share a program scope |
| Unique selected drug / target anchors | 15 / 7 | Descriptive anchors, not adjudicated canonical identities |
| Related drug clusters among program candidates | 14 | Conservative shared-drug grouping, not independent sample count |
| Source reports / candidate events | 18 / 17 | MATCH J reports provisionally deduplicated |
| Report content | 8 full primary reports, 6 metadata/abstract, 4 unavailable | Transport success alone is insufficient |
| Within-window / preorigin / postendpoint / boundary-straddling report dates | 10 / 3 / 3 / 2 | Publication timing, not incident event timing |
| Candidate advancement report | 1 | P01; incident timing and scope remain qualified |
| Certified incident advancements | 0 | Not evidence that no advancement occurred |
| Certified historical program mappings | 0 | Local source identities exist; canonical historical qualification remains open |
| Individual censoring / training labels assigned | 0 / 0 | Registry presence is not complete event ascertainment |

The 24 purposive cases cannot estimate an unbiased population event rate or justify a power calculation. Unique IDs do not establish independence. The register separates P12 genotype scopes, P17 tumor/regimen scopes, P08 dose/expansion/combination scopes and P24 phase parts, while preserving uncertain overlap.

## Decisions and corrections

The amended primary endpoint is initiation of the next phase for a qualified drug/regimen and indication/population. Efficacy reporting, safety/benefit-risk dosing cessation and later administrative development decisions remain separate domains. A report date does not become a dosing date. An upper event-date bound alone cannot demonstrate that an event occurred after origin.

The P01 retained Merck announcement names IDeate-Lung02/NCT06203210 and reports first dosing by August 1, 2024. It supports a useful advancement lead, but does not alone provide the needed post-origin lower bound or adjudicated treatment-line equivalence. The retained page also reports modification in 2026; its 2024 publication metadata does not prove unchanged archived text.

P03's origin arm narrative describes pertuzumab/trastuzumab, while its intervention linkage also includes trastuzumab emtansine. P21 has a 14 mg intervention description versus 140 mg in the arm description. Both conflicts are retained without silent repair. P12's N1303K report is linked only to the matching genotype candidate and does not overwrite the origin endpoint hierarchy.

P14's earlier exclusion concerned a fresh efficacy endpoint. Existing results do not automatically remove a still-active program from a next-phase risk set. It is now unresolved for advancement rather than automatically excluded on that basis. Platform recruitment cannot establish an individual arm's activity; mixed-phase labels do not prove a completed prior phase. PMID 41051123 remains a population-mismatch rejection canary.

Intended action, modality and external canonical IDs are left unassigned where the retained mapping reference has not been certified as origin-eligible. Original intervention and arm text, namespace/version, retrospective mapping notes and source pointers remain available. This limits historical certification; it does not erase the source-qualified clinical identity.

## Verification and recovery

All 554 files across the three parent manifests passed their retained hashes (486 prior-session, 56 origin, 12 endpoint). The final package seals 23 files. Source-inclusive deterministic replay, journal-chain verification and original-input checks passed. **21 relevant tests passed**, including nine new evaluator regressions covering date precision, interval bounds, phase formats, anchor roles, duplicate reports, arm leakage, missing cases, historical certification, censoring, path integrity and no-clobber output reservation.

The first build caught a relative/absolute proof-path error and left its failure journal at `program-outcome-feasibility-20261017T142746Z`. A second build was retained at `program-outcome-feasibility-20261017T143428Z`; verification caught tuple/list equality after JSON serialization. Derived records are now normalized to their persisted representation. The final fresh build passed source-inclusive replay. Both earlier attempts remain available, and the frozen protocol bytes were preserved across recovery.

This phase did not rerun the entire runtime suite because it changed only evaluator utilities and documentation. The prior runtime test claims remain those of the previous completed batch. Technical reproducibility and AI consistency do not establish biological truth or independent gold.

## Next bounded work

Execution update: item 1 is complete in [[Phase 3 Linkage Follow-up]]. The registry start and overlapping P01 scope are now known; exact dosing and strict program/event certification remain qualified. Freeze the explicit program-equivalence rule before expansion.

1. Read NCT06203210 from the existing January 2025 restore, retaining actual start/date type, first posting and population fields. Compare P01/P24 regimen, treatment line and SCLC scope. Seek additional dated evidence only where it changes event qualification.
2. Resolve active phase and prior advancement for the provisional/mixed-stage units; address the two source discrepancies and only the historical mappings needed for those units.
3. Once an auditable advancement route and follow-up rule work, freeze an origin-only expansion protocol before inspecting expansion outcomes. Keep these exposed cases outside an untouched test set.
4. If that route remains impractical, proceed with contemporary T6 claim-support evaluation under a separate protocol. Historical MR, scorer training, competitor execution and broader tasks remain gated.

No immediate additional user download is required for the first item. January 2026 remains outside the frozen January 2025 endpoint. The old downloader, stopped monitor, canonical dossiers and sealed parent sessions remain unchanged.
