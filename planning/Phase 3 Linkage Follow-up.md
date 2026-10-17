---
title: Phase 3 Linkage Follow-up
date: 2026-10-17
status: completed-with-program-qualification-gates
tags: [asof, clinical-evaluation, aact, feasibility]
---

# Phase 3 linkage follow-up

The next bounded step from [[Program and Outcome Feasibility]] is complete. NCT06203210 was extracted from the existing January 2025 database together with P01/NCT05280470 and P24/NCT04145622. The missing registry start date is resolved, and the population/regimen relationship is now explicit. **No training label or therapeutic-success claim was added.**

## Findings

| Field | January 2025 observation | Interpretation |
| --- | --- | --- |
| Linked trial | NCT06203210, IDeate-Lung02 | Phase 3 I-DXd versus physician-choice chemotherapy |
| Status | Recruiting | Registry state, not efficacy |
| Actual study start | 2024-05-21 | First enrollment; not an exact first-dosing date |
| First posted | 2024-01-12 | First registry record, not evidence that dosing had begun |
| Last update posted | 2024-12-04 | Record-level date; not first publication of every field |
| Experimental regimen | I-DXd 12 mg/kg IV every three weeks | Matches P01's 12 mg/kg regimen, not both P01 dose arms |
| Disease and prior therapy | ES-SCLC; only one prior platinum-based systemic line | Second-line population overlapping P01's broader origin population |
| Dosing announcement | First participant dosed by 2024-08-01 | Exact date and first dosed randomized arm unspecified |

The actual-start field identifies first enrollment, as explained in [NIH NCATS guidance citing the ClinicalTrials.gov glossary](https://ncats.nih.gov/research/research-activities/ctsa/applicant-information/par-24-272-faq). Combining that lower bound with the retained sponsor announcement supports a **conditional trial-level dosing interval of May 21–August 1, 2024**. This inference assumes on-trial dosing follows enrollment and the retained dated announcement is accurate. It does not establish the exact dosing date or first dosing in the experimental arm.

The sponsor page retains an August 2024 publication date but also 2026 modification metadata. Its exact historical content version remains unverified. The registry dump establishes the reported information in the selected January 2025 version; publisher authenticity and exact archive public-availability time retain their earlier qualifications. The NIH definition was checked through the web tool as a methodological reference, not used as historical trial evidence.

## Program link and source changes

P01's **origin** description permits one to three previous therapy lines and explicitly identifies second-line strata. Its source alias connects ifinatamab deruxtecan and DS-7300a; the origin arm includes the 12 mg/kg regimen. Phase 3 is therefore a defensible overlapping development lead. It is not an identical whole-cohort eligibility set: the Phase 3 registry also specifies chemotherapy-free interval and other restrictions. Do not retroactively label the entire P01 population or both doses as having advanced.

P24 shares the drug-development lineage, but the retained origin record provides broad solid-tumor scope rather than an adjudicated SCLC cohort/stage. The same Phase 3 initiation must not become a second independent event just because P24 has another NCT identifier.

Two later changes are preserved separately:

- P01's January 2025 record includes an extension population requiring at least two prior therapy lines. This later restriction does not replace the origin description.
- P01's reported actual study start changes from June 17, 2022 in the origin record to March 9, 2022 in the endpoint record. Both remain snapshot-specific observations; neither original is overwritten.

P24's endpoint record says dose escalation is closed while expansion recruits. That later state cannot certify which stage was active at the 2023 origin.

## Retained evidence and checks

Output: `data/benchmark/cohorts/phase3-linkage-20261017T144828Z/`.

- `Review.html`: readable comparison and expandable original records.
- `assessment.json`, `timing-assessment.json`, `scope-comparison.json`: separate findings and qualifications.
- `source-checks.json`: 30 source-bound original-field checks.
- `extraction/`: exact query, three records, repeat-read output, read-only session validation, lifecycle logs and sealed extraction evidence.
- `decision.md`, `verification.json`, `test-results.txt`: decision, technical checks and 26 passing relevant tests.
- `evidence-manifest.json`: 38 sealed files, SHA-256 `0fe053721ee85e661eccc843b7c639458060058031e4fb27837b4cce1753e5b5`.
- Public anchor: `data/manifests/public/2026-10-17-phase3-linkage.json`.
- Current pointer: `data/derived/active-phase3-linkage.json`.

The 2.11 GB source dump was freshly hashed against the restoration anchor. Existing parent evidence was reverified. All three records were read twice with identical results, using read-only repeatable-read transactions. Their posting dates fall within the frozen endpoint; arm/intervention references and trial membership passed checks. Source-inclusive verification replays timing and checks original field values and the lifecycle journal without restarting the database.

The temporary server was stopped and its stopped state confirmed. Extraction and lifecycle work took 63.75 seconds, including source verification. No import, new dataset download, new credential, paid call, model execution or change to the downloader/monitor occurred. A separate optional raw NIH-page download was blocked by automatic approval review; the already-accessed official web reference and this limitation are retained, and no download retry was made. This does not affect the retained registry or sponsor source evidence.

## Decision and next work

Execution update: the program-equivalence rules are now frozen and applied in [[Program Advancement Rules v0.3]]. Origin arm/stage and risk qualification is the next bounded pass; the extraction documented here remains complete.

The temporal lead is stronger: Phase 3 enrollment is reported within the window and a conditional dosing interval is now bounded. Strict historical event certification, individual censoring and training eligibility remain unresolved.

The next bounded work is to **freeze program-equivalence rules for dose selection and nested populations before expanding the cohort**, using this exposed case as development material. State explicitly whether a phase transition within a previously represented stratum qualifies at the program level, how randomized-arm initiation is handled, and how multiple predecessor trials share one event. Do not silently amend the sealed protocol or promote its current zero-label dataset.

Then resolve origin arm activity/stage and follow-up for the provisional candidates, including the P03 regimen and P21 dose conflicts already retained. No further user download is immediately needed for these local checks. Broader origin-only enumeration, historical mapping completion and scorer training retain their separate gates. This remains AI-assisted unblinded development review, not independent scientific validation.
