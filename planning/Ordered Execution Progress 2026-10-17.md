# Task 1: cohort and transition-label audit

Completed October 17, 2026 (local date). The original v0.4 cohort, labels and seals
are preserved. The v0.5 sensitivity protocol was frozen before the new ontology joins.

The fixed 4,419-program / 98-link audit found 1,330 programs with a unique exact
ontology mapping, 257 with ambiguous mappings and 2,832 unmapped. There are 41 exact
healthy-participant entries and 57 broad condition entries. Mapping alone does not
establish clinical diagnosis or eligibility: Open Targets includes phenotypes,
processes and measurements as well as diseases.
[Provider documentation](https://platform-docs.opentargets.org/disease-or-phenotype).

367 programs have prior-risk alerts. Four programs with recorded registry transitions
have alerts: psilocybin/TRD (estimated prior Phase 3), guselkumab/ulcerative colitis
(prior mixed Phase 2/3 under an exact synonym), lecanemab/Alzheimer disease (mixed-phase
and role-qualified prior records), and mazdutide/type 2 diabetes (estimated prior
Phase 3). An alert does not establish exclusion, experimental dosing or clinical
population equivalence. Hierarchy relations never become equivalent disease aliases.

All 98 original links retain matched-arm and separate study-wide context: route,
age words, setting, prior treatment, extension/regional context and non-drug partners.
The audit does not impute full eligibility, actual age bounds, dose/genotype equivalence
or arm-specific enrollment. Prior-risk projections were checked against original rows;
3,516 original source rows were rehashed. All 21 parent seal files passed streaming
hash verification. No training labels, recall or scientific accuracy were inferred.

Validation: eight new regression tests; full suite **194 tests, zero skips/failures/errors**,
required probes, PowerShell syntax and dependency-free installed-wheel demo passed.
See `task1-validation.json` and `task1-summary.json` in the evidence folder.
Canonical output: `data/benchmark/cohorts/registry-scope-20261018T025216Z`.
Anchor: `data/manifests/public/2026-10-17-registry-scope.json`.

Task 1 is complete for development cohort construction and source/scope auditing.
Independent scientific and locked-test evaluation remain Task 7. Task 2 follows:
measure dependent sample sizes, power scenarios and clinical feasibility using these
uncertainties. No new downloads, restored-server starts or model-provider calls.
