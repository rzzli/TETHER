---
name: research-log-2026-10-17-phase3-linkage
description: Linked Phase 3 extraction, enrollment/dosing distinction and program-scope qualification
metadata:
  type: project
---

# Linked Phase 3 follow-up

Completed the next step from [[Program and Outcome Feasibility]]; see [[Phase 3 Linkage Follow-up]]. NCT06203210 was extracted with P01/P24 from the existing January 2025 restore in read-only mode. First posted 2024-01-12, actual enrollment start 2024-05-21, last update posted 2024-12-04. Enrollment is not first dosing. Combining enrollment with the retained August 1 announcement gives a qualified May 21–August 1 trial-dosing interval; exact dosing date/arm and historical announcement version remain unknown.

Phase 3 uses 12 mg/kg I-DXd every three weeks in second-line ES-SCLC. This overlaps P01's origin second-line stratum and selected dose; it does not equal every P01 arm/population. P24 origin SCLC cohort/stage remains unresolved and must not double-count the same development event. P01 later extension criteria and revised 2022 start date are retained separately from origin evidence.

Thirty source-field checks, 26 relevant tests and source-inclusive timing replay passed. Final output: `data/benchmark/cohorts/phase3-linkage-20261017T144828Z`; 38-file manifest anchored by `data/manifests/public/2026-10-17-phase3-linkage.json`. Server stopped; $0 spending; no new training labels or dataset download.

Next: freeze explicit program-equivalence/dose-selection/nested-population and shared-event rules before cohort expansion, then resolve origin stage and follow-up. Do not treat this already exposed case as untouched evaluation data.
