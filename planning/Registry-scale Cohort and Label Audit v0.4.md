# Registry-scale development sizing and label audit

October 17, 2026. This completes the first registry-scale extraction and technical
label audit under the previously frozen v0.4 protocol. It does not validate a
clinical prediction benchmark. Training labels, probabilities, individual censoring
dates, scientific precision and recall remain unset.

## Measured result

The canonical workspace is
`data/benchmark/cohorts/registry-sizing-20261017T202655Z/`, with final products in
`cohort-v04/` and `audit-v04/`. Earlier sibling builds and extraction failures are
diagnostics, preserved in place. The public manifest binds the final artifacts.
The protocol SHA-256 remains
`5757670106359cbd007cc1dd9ed0b0acad44086852e81f4b2dd6494d79ac51cd`.

| Measure | Result |
| --- | ---: |
| Snapshot study observations | 232,722 |
| Distinct trial IDs in selected frames | 196,940 |
| Source frames | 5, origin January 2023 through January 2025 |
| Mapped origin program keys passing automatic role/date rules | 4,419 |
| Phase 1 origin programs | 980 |
| Phase 2 origin programs | 3,439 |
| Programs with recorded eligible next-phase study start | 27 |
| Programs with unresolved transitions | 41 |
| Programs without a recorded transition under this search | 4,351 |
| Candidate event/program links | 98 |
| Distinct recorded development events / next-trial IDs | 37 / 37 |
| Drugs / mapped targets | 1,039 / 745 |
| Programs with / without contemporary target mapping | 3,346 / 1,073 |
| Target–condition rollups | 9,532 |
| Product/source/event dependency components | 1,001 |
| Components with recorded events | 19 |
| Targets represented among recorded-event programs | 10 |
| Clinical training labels produced | 0 |

The 27 program results include 2 Phase 1→2 programs and 25 Phase 2→3 programs.
Their 37 distinct events comprise 2 and 35 events respectively. Multiple trials,
conditions and targets can share a drug/event; program counts are not independent
positive sample sizes. Target and sponsor cluster counts are separate descriptive
views, not an effective sample-size or power calculation.

The origin routing also retains 16,888 unresolved mapped keys, 5,338 keys with a
known prior higher phase, and 5,788 inactive keys. Completely unmapped interventions
cannot be counted as resolved drug programs. This is a conservative automatic subset,
not a prevalence estimate for the entire registry.

## What was checked

All 4,419 included programs and all 98 candidate event links passed checks against
their original frame rows. The audit rehashed 2,497 distinct original rows and scanned
all 232,722 source observations. It checks trial/arm identity, exact product aliases,
phase, start precision/type, posting bounds and explicit null training/censoring fields.
It does not establish true drug roles or equivalent clinical populations.
Three unresolved programs without incident event IDs (tenecteplase/stroke,
fruquintinib/rectal cancer and abelacimab/AF) have separate retained proofs of
late-disclosed possible pre-origin higher phases; they are not assigned negative labels.

The final stratified sample contains all 65 programs with candidate events plus
120 sampled programs without a recorded transition. Inclusion probabilities and
stratum populations are retained. Deterministic original-row annotations cover all
185. AI-assisted narrative notes cover 33 sampled programs and 88 distinct source
rows, with explicit source proofs. These are a purposive second annotation layer,
not independent scientific review. There are zero human annotations and no precision,
recall, kappa or minute-per-case estimate.

A relaxed intervention/condition search of the final 120 controls found no higher-phase
leads under its exact-alias search. A diagnostic predecessor sample had three controls
with 11 observed versions of Phase 4/estimated/comparator leads; those do not satisfy
the allowed 1→2/2→3 endpoint. The deterministic sample changed after composition
bugs changed the eligible pool. No endpoint or condition mapping was tuned to those
results. Neither search supplies an independent exhaustive recall denominator.

## Corrections made during source review

- Replaced correlated child-table queries with set-based joins and session-only
  hash-join settings. A retained query plan showed repeated scans caused by poor
  cardinality estimates. The remaining July and January extracts took about
  6 and 38 seconds. The three completed earlier extracts were reused after rehashing.
- Preserve original date precision, estimated→ACTUAL versions, actual-date/phase
  conflicts, late-disclosed prior advancement, withdrawn/ACTUAL contradictions,
  impossible actual-start/update chronology and unresolved later drug roles.
- Explicit additional-treatment and drug-cocktail text now prevents automatic
  single-product qualification. The baricitinib/prednisone and surufatinib/cocktail
  examples are retained. Unsupported active-product types are held rather than
  silently treated as Drug/Biological monotherapy.
- Mixed-condition platform studies with heterogeneous products remain unresolved.
  Combination products, background roles and alias ambiguities are not spread into
  separate component monotherapy labels.
- Added durable build accounting/failure records, code fingerprints, exclusive output
  reservation and source-inclusive auditing. Corrected an audit counter that counted
  empty lookup entries as controls with leads; its diagnostic report is superseded.

The final build took 141.95 seconds, with a measured peak working set of
263,344,128 bytes (~251 MiB). Frames occupy 719,992,409 bytes; canonical cohort
outputs including the SQLite index occupy 2,108,366,465 bytes. Audit outputs occupy
11,463,773 bytes. See the resource report for scope and measurement details.

## Interpretation limits and next decision

The exact-condition baseline can both miss synonyms and equate broad condition
entries spanning distinct diseases or populations. Lecanemab has pre-origin Phase 3
records under *early* Alzheimer wording that are not joined to the generic condition
key; its later dominantly inherited population differs too. Baricitinib's generic
skin-disease overlap is not disease equivalence. Tebentafusp spans metastatic and
adjuvant contexts; glucagon spans intranasal rescue and insulin-site augmentation.
Extension studies and regional bridging can generate a higher-phase NCT without
first pivotal advancement. Healthy-volunteer programs are present in the broad
registry rules and require an explicit clinical-scope decision before benchmark use.

Contemporary OT 25.09 aliases/targets remain evaluator-only oracle mappings for 2023.
No later clinical-phase, approval or outcome fields enter historical predictors.
Exact string matching, generic condition indexing, unlinked procedural/background
interventions and trial-wide versus arm-specific starts remain important limitations.
Preserve source encoding artefacts rather than silently repairing protected strings.

Next: freeze a separate condition-equivalence/clinical-scope sensitivity protocol,
audit prior advancement and population/regimen roles, then run dependency-aware power
scenarios using measured qualified events and explicit label-error assumptions.
The current counts alone support neither a T1 go decision nor a finding of infeasibility.
Independent adjudication, strict Tier B first dosing, historical predictor coverage,
model chronology, scorer training, live models and competitor runs remain later gates.

## Reproduction and recovery

See [the utility guide](../tools/feasibility/README.md) for commands. Do not restart a
live extraction or reuse an output directory. All five source servers are stopped.
No imports, original-archive rewrites, new acquisitions or provider-model calls occurred.
The original download worker and stopped periodic monitor were not changed.

The private repository is [rzzli/drug_target_agents](https://github.com/rzzli/drug_target_agents).
Windows/Linux core/full CI passed at both the baseline and registry code checkpoint
`f57c448` ([registry run](https://github.com/rzzli/drug_target_agents/actions/runs/39067876345)). Baseline recovery assets were downloaded
from private hosting, all 1,811 entries rehashed, a sealed milestone restored and the
Git bundle cloned/fsck-checked. The final registry release was downloaded and restored: all 146 files / 2.84 GB
of selected source artifacts rehashed, SQLite integrity and the 21-file milestone seal
passed, and the Git bundle cloned/fsck-checked. Evidence is recorded in [the milestone evidence index](review-assets/registry-sizing-20261017/README.md).
Full AACT ZIPs/dumps/database pages are outside these small-workspace recovery bundles;
do not claim a complete raw-data disaster-recovery copy.
