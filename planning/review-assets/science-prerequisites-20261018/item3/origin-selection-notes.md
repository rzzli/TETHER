# Origin selection seal and limits

January 2025 source-only selection and its immutable historical-mapping revision
passed. The fixed origin is 2025-01-01T00:00:00Z; the horizon remains
2026-01-01T00:00:00Z. No later AACT source or earlier cohort outcome labels were
read, and no endpoint data was queried or joined. The owned January 2025 PostgreSQL
server on port 55439 is stopped.

The final seal is
`data/benchmark/cohorts/science-origin-20250101-20261018T173340Z/mapping-r1/origin-freeze.json`,
SHA256 `8622c4896796489e0d34c9359ccdbc3a1ad0eb1778541e173e0ab34ff7cd26e8`.
It binds the original selection seal, all final program bytes, approved OT24.09
mapping projections, the reconstruction-method decision and archived official
provenance sources. Its parent selection seal is unchanged, SHA256
`2e1217ec2d6636ba02a0ade85489931a0da2330a6809d109345cac48237f3731`.

The January 2025 restore contains 520,688 studies. The source frame retains 203,147
phase-interventional studies from this same snapshot, including full eligibility,
design, experimental-arm/intervention links, conditions, original start precision,
phase/status and sponsors. It excludes outcomes/results and AACT calculated_values.
First and last public-posted dates both pass conservative pre-origin checks; their
maximum is December 27, 2024. Whole original date intervals determine actual-start
eligibility; imputed AACT days never refine partial dates. Mixed phases remain held.

15,018 studies pass trial-level phase/status/start screening. The selection retains
61,541 conditional experimental-arm/condition scopes across 12,941 distinct trials.
Study eligibility is preserved as study-level text, never silently assigned as
proven arm-specific population equivalence. Combination products/roles and multiple
conditions remain explicit review holds. Prior higher-phase searches consider all
source intervention roles conservatively; 11,955 scopes have verbatim-name alerts,
which do not automatically establish same-program prior phase.

Historical mapping uses only qualified OT24.09 projections with ChEMBL34 and
Ensembl112 lineage, available by September 19, 2024. Exact historical aliases uniquely
map all active product slots in 22,089 scopes; 18,580 scopes have resource target
annotations. There are 39,452 unmapped/ambiguous drug scopes and 42,961 scopes without
target annotations. These unknowns are retained, not filled from OT25.09,
HGNC2026 or ChEMBL35. Across retained scopes there are 1,605 unique mapped drug IDs,
816 resource target IDs and 3,697 lead-sponsor verbatim names. These are annotation
coverage/dependence counts, not independent scientific sample size.

Every one of the 61,541 parent IDs and unchanged scope/source fields matched its
mapping revision. All parent/final artifact hashes were independently rechecked.
The source build's 70 retained-row checks and a further 91 original-row projection
audits passed. The mapping run also rehashed each source row used for product alias
linkage. All 37 targeted origin/registry-scope/chronology regressions passed; 11 are
new origin tests. The final audit code and its report remain in the origin workspace.

The first attempt, `science-origin-20250101-20261018T173122Z`, failed before any
origin query. Native PowerShell Start-Process -Wait waited on the PostgreSQL
descendant tree. Its owned server was stopped, failure recorded, and a fresh
workspace used after changing to Start-Process Hidden -PassThru plus WaitForExit()
on the pg_ctl process alone. No failed workspace was overwritten or silently reused.

This is a mapping-input-qualified **reconstructed exploratory** universe. Exact
bulk-snapshot public availability, exact-origin registry completeness, biological
drug/target truth, same-program regimen/population equivalence and clinical outcomes
remain unestablished. The strict origin-date, complete-registry, clinical-locked and
clinical-ready flags remain false; qualified clinical programs remain zero. The
root must retain its explicit exploratory-route amendment before evaluator endpoint
restoration/assessment. This seal does not activate clinical evaluation or scoring.

The sanitized machine-readable proof is `origin-selection-report.json`; the
source-grounded availability decision is `origin-reconstructed-availability.md`.
